"""
TST NSLS-II HDFPanda Device

HDFPanda device class for the TST beamline.
"""

import logging
import os

from ophyd_async.core import init_devices
from ophyd_async.fastcs.panda import HDFPanda

from tst_instrument.utils.providers import get_tst_path_provider

logger = logging.getLogger(__name__)


class TSTPanda(HDFPanda):
    """
    TST beamline HDFPanda device.

    Enhanced HDFPanda class with TST-specific path provider and configuration.
    All PV prefixes are configured in configs/devices.yml.
    """

    def __init__(self, prefix: str, name: str = "", labels=None, **kwargs):
        """
        Initialize TST PandA with TST path provider.

        Parameters
        ----------
        prefix : str
            EPICS PV prefix for the PandA
        name : str
            Device name
        labels : list, optional
            Device labels for categorization
        **kwargs
            Additional keyword arguments passed to HDFPanda
        """
        # Check if running in mock mode
        mock_mode = (
            os.environ.get("TST_MOCK_MODE", "NO") == "YES"
            or os.environ.get("RUNNING_IN_NSLS2_CI", "NO") == "YES"
        )

        # Store labels for BITS framework
        self._labels = labels or []

        # Use TST path provider for NSLS-II compliant data organization
        path_provider = get_tst_path_provider(mock_mode=mock_mode)

        # Initialize with mock mode context
        with init_devices(mock=mock_mode):
            super().__init__(prefix, path_provider, name=name, **kwargs)

        logger.info(
            f"Initialized TST PandA '{name}' with prefix '{prefix}' "
            f"(mock={mock_mode})"
        )
