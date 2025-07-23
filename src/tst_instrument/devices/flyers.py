"""
TST NSLS-II Flyer Devices

Flyer device classes for coordinated acquisition at the TST beamline.
Enhanced with advanced coordination and timing validation.
"""

import logging

from ophyd_async.core import StandardFlyer
from ophyd_async.core import init_devices

from .advanced_flyers import TSTFlyerCoordinator
from .advanced_flyers import TSTMantaFlyer
from .advanced_flyers import TSTPandAFlyer
from .advanced_flyers import TSTTriggerLogic

logger = logging.getLogger(__name__)

# TST flyer configuration
# Based on original TST profile existing_plans_and_devices.yaml


def create_tst_flyers(mock: bool = False):
    """
    Create TST beamline flyer devices for coordinated acquisition.

    Parameters
    ----------
    mock : bool, optional
        If True, create simulated flyers. Default: False

    Returns
    -------
    dict
        Dictionary of flyer objects
    """

    with init_devices(mock=mock):
        # Basic flyers for backward compatibility
        default_flyer = StandardFlyer(name="default_flyer")

        # Enhanced trigger logic for TST coordination
        manta_trigger_logic = TSTTriggerLogic("manta_trigger_logic")
        panda_trigger_logic = TSTTriggerLogic("panda_trigger_logic")

        # Advanced flyers with coordination (will be enhanced by plans)
        manta_flyer = StandardFlyer(
            trigger_logic=manta_trigger_logic, name="manta_flyer"
        )
        panda_flyer = StandardFlyer(
            trigger_logic=panda_trigger_logic, name="panda_flyer"
        )

    flyers = {
        "default_flyer": default_flyer,
        "manta_flyer": manta_flyer,
        "panda_flyer": panda_flyer,
    }

    logger.info(f"Created TST flyers (mock={mock}): {list(flyers.keys())}")
    return flyers


def create_advanced_flyer_coordinator(
    detectors=None, panda=None, name="tst_coordinator"
):
    """
    Create an advanced flyer coordinator for sophisticated acquisition coordination.

    Parameters
    ----------
    detectors : list, optional
        List of detector devices to coordinate
    panda : HDFPanda, optional
        PandA device for trigger coordination
    name : str
        Coordinator name

    Returns
    -------
    TSTFlyerCoordinator
        Configured flyer coordinator
    """
    coordinator = TSTFlyerCoordinator(name)

    # Add detectors as Manta flyers if provided
    if detectors:
        for i, detector in enumerate(detectors):
            if hasattr(detector, "hdf"):  # VimbaDetector-like device
                flyer = TSTMantaFlyer(detector, name=f"manta_flyer_{i}")
                coordinator.add_flyer(f"manta_{i}", flyer)

    # Add PandA flyer if provided
    if panda:
        panda_flyer = TSTPandAFlyer(panda, name="advanced_panda_flyer")
        coordinator.add_flyer("panda", panda_flyer)

    logger.info(
        f"Created advanced flyer coordinator '{name}' with "
        f"{len(coordinator.flyers)} flyers"
    )
    return coordinator
