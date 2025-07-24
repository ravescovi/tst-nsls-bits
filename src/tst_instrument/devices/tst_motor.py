"""
TST NSLS-II Motor Device

Motor device class for the TST beamline.
"""

import logging
import os

from ophyd_async.core import init_devices
from ophyd_async.epics.motor import Motor

logger = logging.getLogger(__name__)


class TSTMotor(Motor):
    """
    TST beamline motor device.
    
    Enhanced Motor class with TST-specific configuration and behavior.
    All PV prefixes are configured in configs/devices.yml.
    """
    
    def __init__(self, prefix: str, name: str = "", labels=None, **kwargs):
        """
        Initialize TST motor.
        
        Parameters
        ----------
        prefix : str
            EPICS PV prefix for the motor
        name : str
            Device name
        labels : list, optional
            Device labels for categorization
        **kwargs
            Additional keyword arguments passed to Motor
        """
        # Check if running in mock mode
        mock_mode = (
            os.environ.get("TST_MOCK_MODE", "NO") == "YES"
            or os.environ.get("RUNNING_IN_NSLS2_CI", "NO") == "YES"
        )
        
        # Store labels for BITS framework
        self._labels = labels or []
        
        # Initialize with mock mode context
        with init_devices(mock=mock_mode):
            super().__init__(prefix, name=name, **kwargs)
            
        logger.info(
            f"Initialized TST motor '{name}' with prefix '{prefix}' "
            f"(mock={mock_mode})"
        )