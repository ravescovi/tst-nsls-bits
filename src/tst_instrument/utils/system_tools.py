"""
TST NSLS-II System Tools

System introspection, documentation generation, and diagnostic utilities
for the TST beamline BITS deployment.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import yaml
from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)


# def initialize_hardware_systems() -> None:
#     """
#     Initialize hardware systems for TST beamline operation.

#     This function can be extended to include other hardware initialization
#     procedures beyond HDF5 warmup.
#     """
#     logger.info("Initializing TST hardware systems")

#     # Future hardware initialization procedures can be added here
#     # Examples:
#     # - Motor homing procedures
#     # - Detector calibration checks
#     # - PandA configuration validation

#     logger.info("Hardware systems initialization completed")


def validate_device_connections(devices: List[Any]) -> dict:
    """
    Validate EPICS connections for a list of devices.

    Parameters
    ----------
    devices : List[Any]
        List of devices to validate

    Returns
    -------
    dict
        Dictionary with validation results:
        {
            'connected': [list of connected devices],
            'disconnected': [list of disconnected devices],
            'errors': [list of devices with errors]
        }
    """
    logger.info("Validating device connections")

    results = {"connected": [], "disconnected": [], "errors": []}

    for device in devices:
        try:
            device_name = getattr(device, "name", "unknown")
            logger.debug(f"Checking connection for device: {device_name}")

            # Check if device has a connection method/property
            if hasattr(device, "connected") and callable(device.connected):
                is_connected = device.connected()
            elif hasattr(device, "connected"):
                is_connected = device.connected
            else:
                logger.warning(f"Device {device_name} has no connection status method")
                results["errors"].append(device_name)
                continue

            if is_connected:
                results["connected"].append(device_name)
                logger.debug(f"Device {device_name} is connected")
            else:
                results["disconnected"].append(device_name)
                logger.warning(f"Device {device_name} is not connected")

        except Exception as e:
            device_name = getattr(device, "name", "unknown")
            logger.error(f"Error checking connection for {device_name}: {e}")
            results["errors"].append(device_name)

    logger.info(
        f"Connection validation completed: "
        f"{len(results['connected'])} connected, "
        f"{len(results['disconnected'])} disconnected, "
        f"{len(results['errors'])} errors"
    )

    return results


def generate_device_inventory() -> Dict[str, Any]:
    """
    Generate a comprehensive inventory of all devices in the system.

    Returns
    -------
    Dict[str, Any]
        Complete device inventory with metadata
    """
    logger.info("Generating device inventory")

    inventory = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "devices": {},
        "summary": {
            "total_devices": 0,
            "device_types": {},
            "connected_devices": 0,
            "mock_devices": 0,
        },
    }

    try:
        # Get all devices from oregistry
        all_devices = oregistry.all_devices

        for device in all_devices:
            try:
                device_name = device.name

                # Get device information
                device_info = {
                    "name": device_name,
                    "type": type(device).__name__,
                    "module": type(device).__module__,
                    "attributes": [],
                    "signals": [],
                    "components": [],
                    "status": "unknown",
                }

                # Analyze device attributes
                for attr_name in dir(device):
                    if not attr_name.startswith("_"):
                        try:
                            attr = getattr(device, attr_name)
                            if hasattr(attr, "read"):
                                device_info["signals"].append(attr_name)
                            elif hasattr(attr, "name"):
                                device_info["components"].append(attr_name)
                            else:
                                device_info["attributes"].append(attr_name)
                        except Exception:
                            # Skip attributes that can't be accessed
                            pass

                # Determine connection status
                try:
                    if hasattr(device, "connected"):
                        if callable(device.connected):
                            is_connected = device.connected()
                        else:
                            is_connected = device.connected
                        device_info["status"] = (
                            "connected" if is_connected else "disconnected"
                        )

                        if is_connected:
                            inventory["summary"]["connected_devices"] += 1
                    else:
                        device_info["status"] = "no_connection_info"
                except Exception:
                    device_info["status"] = "connection_check_failed"

                # Check if device is in mock mode
                device_info["mock_mode"] = (
                    os.environ.get("TST_MOCK_MODE", "NO") == "YES"
                    or os.environ.get("RUNNING_IN_NSLS2_CI", "NO") == "YES"
                )

                if device_info["mock_mode"]:
                    inventory["summary"]["mock_devices"] += 1

                # Add PV information for EPICS devices
                if hasattr(device, "prefix"):
                    device_info["pv_prefix"] = getattr(device, "prefix", None)

                inventory["devices"][device_name] = device_info

                # Update type summary
                device_type = device_info["type"]
                if device_type not in inventory["summary"]["device_types"]:
                    inventory["summary"]["device_types"][device_type] = 0
                inventory["summary"]["device_types"][device_type] += 1

                inventory["summary"]["total_devices"] += 1

            except Exception as e:
                logger.warning(f"Could not analyze device {device_name}: {e}")
                inventory["devices"][device_name] = {
                    "name": device_name,
                    "error": str(e),
                    "status": "analysis_failed",
                }

    except Exception as e:
        logger.error(f"Error generating device inventory: {e}")
        inventory["error"] = str(e)

    logger.info(
        f"Generated inventory for {inventory['summary']['total_devices']} devices"
    )
    return inventory


def save_device_inventory(output_path: Optional[Path] = None) -> Path:
    """
    Generate and save device inventory to YAML file.

    Parameters
    ----------
    output_path : Path, optional
        Output file path, defaults to startup directory

    Returns
    -------
    Path
        Path to saved inventory file
    """
    if output_path is None:
        startup_dir = Path(__file__).parent.parent / "startup"
        output_path = startup_dir / "existing_plans_and_devices.yaml"

    inventory = generate_device_inventory()

    # Also get plan information
    plan_info = get_available_plans()
    inventory["plans"] = plan_info

    with open(output_path, "w") as f:
        yaml.dump(inventory, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Device inventory saved to {output_path}")
    return output_path


def get_available_plans() -> Dict[str, Any]:
    """
    Get information about available Bluesky plans.

    Returns
    -------
    Dict[str, Any]
        Available plans with metadata
    """
    plans = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "plans": {},
        "summary": {"total_plans": 0, "plan_categories": {}},
    }

    try:
        # Import plan modules to discover available plans
        from tst_instrument.plans import sim_plans
        from tst_instrument.plans import tomography_plans
        from tst_instrument.plans import xas_plans

        plan_modules = {
            "tomography": tomography_plans,
            "xas": xas_plans,
            "simulation": sim_plans,
        }

        for category, module in plan_modules.items():
            category_plans = []

            for attr_name in dir(module):
                if not attr_name.startswith("_"):
                    attr = getattr(module, attr_name)
                    if callable(attr) and hasattr(attr, "__doc__"):
                        plan_info = {
                            "name": attr_name,
                            "module": module.__name__,
                            "docstring": attr.__doc__,
                            "category": category,
                        }

                        # Try to get signature information
                        try:
                            import inspect

                            sig = inspect.signature(attr)
                            plan_info["signature"] = str(sig)
                            plan_info["parameters"] = list(sig.parameters.keys())
                        except Exception:
                            plan_info["signature"] = "unavailable"
                            plan_info["parameters"] = []

                        category_plans.append(plan_info)
                        plans["plans"][attr_name] = plan_info
                        plans["summary"]["total_plans"] += 1

            plans["summary"]["plan_categories"][category] = len(category_plans)

    except Exception as e:
        logger.error(f"Error getting available plans: {e}")
        plans["error"] = str(e)

    return plans


def validate_pv_connections() -> Dict[str, Any]:
    """
    Validate EPICS PV connections for all devices.

    Returns
    -------
    Dict[str, Any]
        PV connection validation results
    """
    logger.info("Validating PV connections")

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "connections": {},
        "summary": {
            "total_pvs": 0,
            "connected_pvs": 0,
            "disconnected_pvs": 0,
            "failed_checks": 0,
        },
    }

    try:
        # Get all devices from oregistry
        all_devices = oregistry.all_devices

        for device in all_devices:
            try:
                device_name = device.name

                # Check if device has PV information
                if hasattr(device, "prefix"):
                    pv_prefix = getattr(device, "prefix", None)
                    if pv_prefix:
                        connection_info = {
                            "device": device_name,
                            "pv_prefix": pv_prefix,
                            "status": "unknown",
                            "details": {},
                        }

                        # Try to check connection
                        try:
                            if hasattr(device, "connected"):
                                if callable(device.connected):
                                    is_connected = device.connected()
                                else:
                                    is_connected = device.connected

                                connection_info["status"] = (
                                    "connected" if is_connected else "disconnected"
                                )

                                if is_connected:
                                    results["summary"]["connected_pvs"] += 1
                                else:
                                    results["summary"]["disconnected_pvs"] += 1
                            else:
                                connection_info["status"] = "no_connection_method"
                                results["summary"]["failed_checks"] += 1

                        except Exception as e:
                            connection_info["status"] = "check_failed"
                            connection_info["error"] = str(e)
                            results["summary"]["failed_checks"] += 1

                        results["connections"][device_name] = connection_info
                        results["summary"]["total_pvs"] += 1

            except Exception as e:
                logger.warning(f"Could not check PV connection for {device_name}: {e}")
                results["connections"][device_name] = {
                    "device": device_name,
                    "error": str(e),
                    "status": "device_access_failed",
                }
                results["summary"]["failed_checks"] += 1

    except Exception as e:
        logger.error(f"Error validating PV connections: {e}")
        results["error"] = str(e)

    logger.info(f"Validated {results['summary']['total_pvs']} PV connections")
    return results


def benchmark_performance() -> Dict[str, Any]:
    """
    Benchmark system performance for key operations.

    Returns
    -------
    Dict[str, Any]
        Performance benchmark results
    """
    logger.info("Running performance benchmarks")

    benchmarks = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": {},
        "summary": {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "average_response_time": 0.0,
        },
    }

    response_times = []

    # Test 1: Oregistry access speed
    try:
        start_time = time.time()
        all_devices = oregistry.all_devices
        device_count = len(all_devices)
        end_time = time.time()

        response_time = end_time - start_time
        response_times.append(response_time)

        benchmarks["tests"]["oregistry_access"] = {
            "description": "Oregistry device list access",
            "response_time": response_time,
            "devices_found": device_count,
            "status": "passed",
        }
        benchmarks["summary"]["passed_tests"] += 1

    except Exception as e:
        benchmarks["tests"]["oregistry_access"] = {
            "description": "Oregistry device list access",
            "error": str(e),
            "status": "failed",
        }
        benchmarks["summary"]["failed_tests"] += 1

    # Test 2: Device access speed
    try:
        start_time = time.time()
        all_devices = oregistry.all_devices
        test_devices = all_devices[:5]  # Test first 5 devices

        for device in test_devices:
            try:
                # Just access the device, don't do anything expensive
                _ = type(device).__name__
            except Exception:
                pass  # Skip devices that can't be accessed

        end_time = time.time()
        response_time = end_time - start_time
        response_times.append(response_time)

        benchmarks["tests"]["device_access"] = {
            "description": f"Access {len(test_devices)} devices",
            "response_time": response_time,
            "devices_tested": len(test_devices),
            "status": "passed",
        }
        benchmarks["summary"]["passed_tests"] += 1

    except Exception as e:
        benchmarks["tests"]["device_access"] = {
            "description": "Device access test",
            "error": str(e),
            "status": "failed",
        }
        benchmarks["summary"]["failed_tests"] += 1

    # Test 3: Hardware warmup simulation
    try:
        start_time = time.time()

        # Simulate the hardware warmup process
        from tst_instrument.utils.warmup_hdf5 import warmup_hdf5_plugins

        # Get detectors for testing
        detectors = []
        all_devices = oregistry.all_devices

        for device in all_devices:
            try:
                if hasattr(device, "hdf5"):
                    detectors.append(device)
            except Exception:
                pass

        # Run warmup (in mock mode this should be fast)
        warmup_hdf5_plugins(detectors)

        end_time = time.time()
        response_time = end_time - start_time
        response_times.append(response_time)

        benchmarks["tests"]["hardware_warmup"] = {
            "description": f"HDF5 warmup for {len(detectors)} detectors",
            "response_time": response_time,
            "detectors_tested": len(detectors),
            "status": "passed",
        }
        benchmarks["summary"]["passed_tests"] += 1

    except Exception as e:
        benchmarks["tests"]["hardware_warmup"] = {
            "description": "Hardware warmup test",
            "error": str(e),
            "status": "failed",
        }
        benchmarks["summary"]["failed_tests"] += 1

    # Calculate summary statistics
    benchmarks["summary"]["total_tests"] = (
        benchmarks["summary"]["passed_tests"] + benchmarks["summary"]["failed_tests"]
    )

    if response_times:
        benchmarks["summary"]["average_response_time"] = sum(response_times) / len(
            response_times
        )
        benchmarks["summary"]["max_response_time"] = max(response_times)
        benchmarks["summary"]["min_response_time"] = min(response_times)

    logger.info(
        f"Performance benchmarks complete: "
        f"{benchmarks['summary']['passed_tests']}/"
        f"{benchmarks['summary']['total_tests']} passed"
    )
    return benchmarks


def generate_system_report() -> Dict[str, Any]:
    """
    Generate a comprehensive system report.

    Returns
    -------
    Dict[str, Any]
        Complete system report
    """
    logger.info("Generating comprehensive system report")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "system_info": {
            "python_version": os.sys.version,
            "platform": os.sys.platform,
            "environment_variables": {
                "TST_MOCK_MODE": os.environ.get("TST_MOCK_MODE", "NO"),
                "RUNNING_IN_NSLS2_CI": os.environ.get("RUNNING_IN_NSLS2_CI", "NO"),
                "BEAMLINE_ACRONYM": os.environ.get("BEAMLINE_ACRONYM", "unknown"),
                "ENDSTATION_ACRONYM": os.environ.get("ENDSTATION_ACRONYM", "unknown"),
            },
        },
    }

    try:
        # Add device inventory
        logger.info("Adding device inventory to report")
        report["device_inventory"] = generate_device_inventory()

        # Add plan information
        logger.info("Adding plan information to report")
        report["plan_information"] = get_available_plans()

        # Add PV connection validation
        logger.info("Adding PV validation to report")
        report["pv_validation"] = validate_pv_connections()

        # Add performance benchmarks
        logger.info("Adding performance benchmarks to report")
        report["performance_benchmarks"] = benchmark_performance()

        # Add summary statistics
        report["summary"] = {
            "total_devices": report["device_inventory"]["summary"]["total_devices"],
            "connected_devices": report["device_inventory"]["summary"][
                "connected_devices"
            ],
            "total_plans": report["plan_information"]["summary"]["total_plans"],
            "connected_pvs": report["pv_validation"]["summary"]["connected_pvs"],
            "benchmark_score": (
                f"{report['performance_benchmarks']['summary']['passed_tests']}/"
                f"{report['performance_benchmarks']['summary']['total_tests']}"
            ),
        }

    except Exception as e:
        logger.error(f"Error generating system report: {e}")
        report["error"] = str(e)

    logger.info("System report generation complete")
    return report


def save_system_report(output_path: Optional[Path] = None) -> Path:
    """
    Generate and save comprehensive system report.

    Parameters
    ----------
    output_path : Path, optional
        Output file path, defaults to startup directory

    Returns
    -------
    Path
        Path to saved report file
    """
    if output_path is None:
        startup_dir = Path(__file__).parent.parent / "startup"
        output_path = startup_dir / "system_report.yaml"

    report = generate_system_report()

    with open(output_path, "w") as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False)

    logger.info(f"System report saved to {output_path}")
    return output_path
