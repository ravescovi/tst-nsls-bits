#!/usr/bin/env python3

"""
TST NSLS-II PV Documentation Generator

Generate comprehensive PV documentation for the TST beamline BITS deployment.
Creates documentation similar to the original docs/all_pvs.md but with
enhanced formatting and system integration.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict

# Add the source directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from apsbits.core.instrument_init import oregistry
    from tst_instrument.utils.system_tools import generate_device_inventory
    from tst_instrument.utils.system_tools import validate_pv_connections
except ImportError as e:
    print(f"Error importing TST instrument modules: {e}")
    print(
        "Make sure you're running this script from an activated development environment"
    )
    sys.exit(1)

logger = logging.getLogger(__name__)


def collect_pv_information() -> Dict[str, Dict]:
    """
    Collect comprehensive PV information from all devices.

    Returns
    -------
    Dict[str, Dict]
        PV information organized by device
    """
    logger.info("Collecting PV information from devices")

    pv_info = {}

    for device_name in oregistry.keys():
        try:
            device = oregistry.find(name=device_name)

            device_pvs = {
                "name": device_name,
                "type": type(device).__name__,
                "prefix": getattr(device, "prefix", None),
                "pvs": [],
                "components": {},
                "status": "unknown",
            }

            # Get device prefix if available
            if hasattr(device, "prefix"):
                prefix = device.prefix
                device_pvs["prefix"] = prefix

                # Try to enumerate PVs based on device structure
                try:
                    # Check for common PV patterns
                    if hasattr(device, "_signals"):
                        for signal_name, signal in device._signals.items():
                            if hasattr(signal, "pvname"):
                                device_pvs["pvs"].append(
                                    {
                                        "signal": signal_name,
                                        "pv": signal.pvname,
                                        "type": type(signal).__name__,
                                    }
                                )

                    # Check for component devices with PVs
                    for attr_name in dir(device):
                        if not attr_name.startswith("_"):
                            try:
                                attr = getattr(device, attr_name)
                                if hasattr(attr, "prefix") and attr.prefix != prefix:
                                    device_pvs["components"][attr_name] = {
                                        "prefix": attr.prefix,
                                        "type": type(attr).__name__,
                                    }
                            except Exception:
                                pass

                except Exception as e:
                    logger.debug(f"Could not enumerate PVs for {device_name}: {e}")

            # Get connection status
            try:
                if hasattr(device, "connected"):
                    if callable(device.connected):
                        is_connected = device.connected()
                    else:
                        is_connected = device.connected
                    device_pvs["status"] = (
                        "connected" if is_connected else "disconnected"
                    )
            except Exception:
                device_pvs["status"] = "unknown"

            pv_info[device_name] = device_pvs

        except Exception as e:
            logger.warning(f"Could not collect PV info for {device_name}: {e}")
            pv_info[device_name] = {"name": device_name, "error": str(e)}

    logger.info(f"Collected PV information for {len(pv_info)} devices")
    return pv_info


def generate_pv_documentation(
    output_path: Path, include_validation: bool = True
) -> None:
    """
    Generate comprehensive PV documentation.

    Parameters
    ----------
    output_path : Path
        Output file path for documentation
    include_validation : bool
        Whether to include connection validation
    """
    logger.info(f"Generating PV documentation: {output_path}")

    # Collect data
    pv_info = collect_pv_information()
    device_inventory = generate_device_inventory()

    validation_results = None
    if include_validation:
        validation_results = validate_pv_connections()

    # Generate documentation
    with open(output_path, "w") as f:
        f.write("# TST NSLS-II BITS - PV Documentation\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Summary section
        f.write("## Summary\n\n")
        f.write(
            f"- **Total Devices**: {device_inventory['summary']['total_devices']}\n"
        )
        f.write(
            f"- **Connected Devices**: "
            f"{device_inventory['summary']['connected_devices']}\n"
        )
        devices = device_inventory["devices"]
        first_device = list(devices.keys())[0] if devices else None
        mock_mode = (
            devices.get(first_device, {}).get("mock_mode", "unknown")
            if first_device
            else "unknown"
        )
        f.write(f"- **Mock Mode**: {mock_mode}\n")

        if validation_results:
            f.write(f"- **Total PVs**: {validation_results['summary']['total_pvs']}\n")
            f.write(
                f"- **Connected PVs**: "
                f"{validation_results['summary']['connected_pvs']}\n"
            )
            f.write(
                f"- **Disconnected PVs**: "
                f"{validation_results['summary']['disconnected_pvs']}\n"
            )

        f.write("\n")

        # Device type breakdown
        f.write("## Device Types\n\n")
        for device_type, count in device_inventory["summary"]["device_types"].items():
            f.write(f"- **{device_type}**: {count} devices\n")
        f.write("\n")

        # Detailed device information
        f.write("## Device Details\n\n")

        for device_name, info in pv_info.items():
            if "error" in info:
                f.write(f"### {device_name} (ERROR)\n\n")
                f.write(f"**Error**: {info['error']}\n\n")
                continue

            f.write(f"### {device_name}\n\n")
            f.write(f"- **Type**: {info['type']}\n")
            f.write(f"- **Status**: {info['status']}\n")

            if info.get("prefix"):
                f.write(f"- **PV Prefix**: `{info['prefix']}`\n")

            f.write("\n")

            # List PVs if available
            if info.get("pvs"):
                f.write("#### Signals\n\n")
                f.write("| Signal | PV | Type |\n")
                f.write("|--------|----|----- |\n")
                for pv in info["pvs"]:
                    f.write(f"| {pv['signal']} | `{pv['pv']}` | {pv['type']} |\n")
                f.write("\n")

            # List components if available
            if info.get("components"):
                f.write("#### Components\n\n")
                f.write("| Component | Prefix | Type |\n")
                f.write("|-----------|--------|----- |\n")
                for comp_name, comp_info in info["components"].items():
                    f.write(
                        f"| {comp_name} | `{comp_info['prefix']}` | "
                        f"{comp_info['type']} |\n"
                    )
                f.write("\n")

        # Connection validation section
        if validation_results:
            f.write("## Connection Validation\n\n")
            f.write(f"Validation performed: {validation_results['timestamp']}\n\n")

            # Summary table
            f.write("### Summary\n\n")
            f.write("| Status | Count |\n")
            f.write("|--------|----- |\n")
            f.write(
                f"| Connected | "
                f"{validation_results['summary']['connected_pvs']} |\n"
            )
            pvs = validation_results["summary"]["disconnected_pvs"]
            f.write(f"| Disconnected | {pvs} |\n")
            f.write(
                f"| Failed Checks | "
                f"{validation_results['summary']['failed_checks']} |\n"
            )
            f.write("\n")

            # Detailed validation results
            f.write("### Detailed Results\n\n")
            for device_name, conn_info in validation_results["connections"].items():
                status_icon = {
                    "connected": "✅",
                    "disconnected": "❌",
                    "unknown": "❓",
                    "no_connection_method": "⚠️",
                    "check_failed": "🔥",
                }.get(conn_info["status"], "❓")

                f.write(
                    f"- **{device_name}** {status_icon} "
                    f"`{conn_info.get('pv_prefix', 'N/A')}` - "
                    f"{conn_info['status']}"
                )

                if "error" in conn_info:
                    f.write(f" ({conn_info['error']})")

                f.write("\n")

            f.write("\n")

        # Environment information
        f.write("## Environment Information\n\n")
        f.write("```console\n")
        devices = device_inventory["devices"]
        first_device = list(devices.keys())[0] if devices else None
        mock_mode = (
            devices.get(first_device, {}).get("mock_mode", "unknown")
            if first_device
            else "unknown"
        )
        f.write(f"TST_MOCK_MODE: {mock_mode}\n")
        f.write("```\n\n")

        # Footer
        f.write("---\n\n")
        f.write(
            "*This documentation was automatically generated by the "
            "TST NSLS-II BITS system.*\n"
        )
        repo_url = "https://github.com/ravescovi/tst-nsls-bits"
        f.write(
            f"*For more information, see the " f"[TST BITS Repository]({repo_url}).*\n"
        )

    logger.info(f"PV documentation generated: {output_path}")


def main():
    """Main entry point for PV documentation generator."""
    parser = argparse.ArgumentParser(
        description="Generate TST NSLS-II PV documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Generate in default location
  %(prog)s -o /path/to/pvs.md       # Specify output file
  %(prog)s --no-validation          # Skip connection validation
  %(prog)s -v                       # Verbose output
        """,
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "docs" / "all_pvs.md",
        help="Output file path (default: docs/all_pvs.md)",
    )

    parser.add_argument(
        "--no-validation",
        action="store_true",
        help="Skip PV connection validation (faster)",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        # Ensure output directory exists
        args.output.parent.mkdir(parents=True, exist_ok=True)

        # Generate documentation
        generate_pv_documentation(
            args.output, include_validation=not args.no_validation
        )

        print(f"✅ PV documentation generated: {args.output}")

    except Exception as e:
        logger.error(f"Failed to generate PV documentation: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
