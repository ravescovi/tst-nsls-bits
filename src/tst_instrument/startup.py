"""
Start Bluesky Data Acquisition sessions of all kinds.

Includes:

* Python script
* IPython console
* Jupyter notebook
* Bluesky queueserver
"""

# MOCK mode configuration
# Set to True for development/testing without hardware
MOCK_MODE = False

# Override MOCK mode from environment variables
import os

if os.environ.get("TST_MOCK_MODE", "NO").upper() == "YES":
    MOCK_MODE = True
if os.environ.get("RUNNING_IN_NSLS2_CI", "NO").upper() == "YES":
    MOCK_MODE = True

# Standard Library Imports
import logging
from pathlib import Path

from apsbits.core.best_effort_init import init_bec_peaks
from apsbits.core.catalog_init import init_catalog
from apsbits.core.instrument_init import make_devices
from apsbits.core.instrument_init import oregistry

# Core Functions
from apsbits.core.run_engine_init import init_RE

# Utility functions
# Note: APS-specific functions removed for NSLS-II deployment
# Configuration functions
from apsbits.utils.config_loaders import load_config
from apsbits.utils.helper_functions import register_bluesky_magics
from apsbits.utils.helper_functions import running_in_queueserver
from apsbits.utils.logging_setup import configure_logging

# Configuration block
# Get the path to the instrument package
# Load configuration to be used by the instrument.
instrument_path = Path(__file__).parent
iconfig_path = instrument_path / "configs" / "iconfig.yml"
iconfig = load_config(iconfig_path)

# Additional logging configuration
# only needed if using different logging setup
# from the one in the apsbits package
extra_logging_configs_path = instrument_path / "configs" / "extra_logging.yml"
configure_logging(extra_logging_configs_path=extra_logging_configs_path)


logger = logging.getLogger(__name__)
logger.info("Starting Instrument with iconfig: %s", iconfig_path)

# Discard oregistry items loaded above.
oregistry.clear()

# NSLS-II: No APS Data Management setup needed
# Data management handled by NSLS-II infrastructure

# Command-line tools, such as %wa, %ct, ...
register_bluesky_magics()

# Bluesky initialization block
# Instrument = ...
# oregistry = ...
# oregistry.clear()
bec, peaks = init_bec_peaks(iconfig)
cat = init_catalog(iconfig)
RE, sd = init_RE(iconfig, bec_instance=bec, cat_instance=cat)


# Optional Nexus callback block
# delete this block if not using Nexus
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    from tst_instrument.callbacks.nexus_data_file_writer import nxwriter_init

    nxwriter = nxwriter_init(RE)

# Optional SPEC callback block
# delete this block if not using SPEC
if iconfig.get("SPEC_DATA_FILES", {}).get("ENABLE", False):
    from tst_instrument.callbacks.spec_data_file_writer import init_specwriter_with_RE
    from tst_instrument.callbacks.spec_data_file_writer import newSpecFile  # noqa: F401
    from tst_instrument.callbacks.spec_data_file_writer import (
        spec_comment,  # noqa: F401
    )
    from tst_instrument.callbacks.spec_data_file_writer import specwriter  # noqa: F401

    init_specwriter_with_RE(RE)

# These imports must come after the above setup.
# Queue server block
if running_in_queueserver():
    ### To make all the standard plans available in QS, import by '*', otherwise import
    ### plan by plan.
    from apstools.plans import lineup2  # noqa: F401
    from bluesky.plans import *  # noqa: F403
else:
    # Import bluesky plans and stubs with prefixes set by common conventions.
    # The apstools plans and utils are imported by '*'.
    from apstools.plans import *  # noqa: F403
    from apstools.utils import *  # noqa: F403
    from bluesky import plan_stubs as bps  # noqa: F401
    from bluesky import plans as bp  # noqa: F401

# Import TST-specific plans and utilities
# ruff: noqa: E402
from tst_instrument.plans.sim_plans import sim_count_plan  # noqa: F401
from tst_instrument.plans.sim_plans import sim_print_plan  # noqa: F401
from tst_instrument.plans.sim_plans import sim_rel_scan_plan  # noqa: F401
from tst_instrument.plans.tomography_plans import _manta_collect_dark_flat  # noqa: F401
from tst_instrument.plans.tomography_plans import tomo_demo_async  # noqa: F401
from tst_instrument.plans.xas_plans import energy_calibration_plan  # noqa: F401
from tst_instrument.plans.xas_plans import xas_demo_async  # noqa: F401
from tst_instrument.utils.system_tools import (
    initialize_hardware_systems,  # do we need this?
)
from tst_instrument.utils.warmup_hdf5 import warmup_hdf5_plugins  # do we need this?

# Experiment specific logic, device and plan loading
RE(make_devices(clear=False, file="devices.yml"))  # Create the devices.

# NSLS-II: No APS subnet check needed - removed devices_aps_only.yml loading

# Initialize hardware systems
initialize_hardware_systems()

# Warm up HDF5 plugins for detectors with HDF5 capabilities
# Get detectors from oregistry and filter for those with HDF5 plugins
detectors_with_hdf5 = []
try:
    # Use oregistry.all_devices to get all devices
    all_devices = oregistry.all_devices
    for device in all_devices:
        try:
            if hasattr(device, "hdf5"):
                detectors_with_hdf5.append(device)
        except Exception as e:
            device_name = getattr(device, "name", "unknown")
            logger.debug(f"Could not check HDF5 capability for {device_name}: {e}")
except Exception as e:
    logger.warning(f"Could not access oregistry devices for HDF5 detection: {e}")

if detectors_with_hdf5:
    logger.info(
        f"Found {len(detectors_with_hdf5)} detectors with HDF5 plugins, warming up..."
    )
    try:
        warmup_hdf5_plugins(detectors_with_hdf5)
    except Exception as e:
        logger.warning(f"HDF5 warmup failed: {e}")
else:
    logger.info("No detectors with HDF5 plugins found")

logger.info("TST NSLS-II instrument startup completed successfully")
