"""
TST NSLS-II Detector Devices

Detector device classes for the TST beamline using ophyd_async.
"""

import logging

from ophyd_async.core import init_devices
from ophyd_async.epics.advimba import VimbaDetector

logger = logging.getLogger(__name__)

# TST detector configuration
# Based on original TST profile collection startup/15-manta.py


def create_tst_detectors(mock: bool = False):
    """
    Create TST beamline detectors.

    Parameters
    ----------
    mock : bool, optional
        If True, create simulated detectors. Default: False

    Returns
    -------
    dict
        Dictionary of detector objects
    """

    with init_devices(mock=mock):
        # Manta cameras for imaging
        manta1 = VimbaDetector("XF:31ID1-ES:1{Manta:1}", name="manta1")

        manta2 = VimbaDetector("XF:31ID1-ES:1{Manta:2}", name="manta2")

    detectors = {
        "manta1": manta1,
        "manta2": manta2,
    }

    logger.info(f"Created TST detectors (mock={mock}): {list(detectors.keys())}")
    return detectors
