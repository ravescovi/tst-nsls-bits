"""
TST NSLS-II Device Creators

Device creator functions for BITS make_devices integration.
These creators handle ophyd_async device initialization properly.
"""

import logging
import os
from pathlib import Path
from ophyd_async.epics.motor import Motor
from ophyd_async.epics.advimba import VimbaDetector
from ophyd_async.fastcs.panda import HDFPanda
from ophyd_async.core import StandardFlyer, init_devices, StaticPathProvider, StaticFilenameProvider

logger = logging.getLogger(__name__)

# Check if running in mock mode (CI environment or explicit mock mode)
RUNNING_IN_MOCK_MODE = (
    os.environ.get("RUNNING_IN_NSLS2_CI", "NO") == "YES" or
    os.environ.get("TST_MOCK_MODE", "NO") == "YES"
)

def create_tst_motor(prefix: str, name: str, **kwargs):
    """
    Create a TST motor with proper ophyd_async initialization.
    
    Parameters
    ----------
    prefix : str
        EPICS PV prefix for the motor
    name : str
        Device name
    **kwargs
        Additional keyword arguments
        
    Returns
    -------
    Motor
        Configured motor device
    """
    with init_devices(mock=RUNNING_IN_MOCK_MODE):
        motor = Motor(prefix, name=name)
    
    logger.info(f"Created TST motor '{name}' with prefix '{prefix}' (mock={RUNNING_IN_MOCK_MODE})")
    return motor


def create_tst_detector(prefix: str, name: str, **kwargs):
    """
    Create a TST VimbaDetector with proper ophyd_async initialization.
    
    Parameters
    ----------
    prefix : str
        EPICS PV prefix for the detector
    name : str
        Device name
    **kwargs
        Additional keyword arguments including data_path
        
    Returns
    -------
    VimbaDetector
        Configured detector device
    """
    # Create path provider for detector data files
    data_path = kwargs.get('data_path', '/tmp/tst_data')
    filename_provider = StaticFilenameProvider(f"{name}_data")
    path_provider = StaticPathProvider(
        filename_provider=filename_provider,
        directory_path=Path(data_path)
    )
    
    with init_devices(mock=RUNNING_IN_MOCK_MODE):
        detector = VimbaDetector(prefix, path_provider=path_provider, name=name)
    
    logger.info(f"Created TST detector '{name}' with prefix '{prefix}' (mock={RUNNING_IN_MOCK_MODE})")
    return detector


def create_tst_panda(prefix: str, name: str, **kwargs):
    """
    Create a TST HDFPanda with proper ophyd_async initialization.
    
    Parameters
    ----------
    prefix : str
        EPICS PV prefix for the PandA
    name : str
        Device name
    **kwargs
        Additional keyword arguments including data_path
        
    Returns
    -------
    HDFPanda
        Configured PandA device
    """
    # Create path provider for PandA data files
    data_path = kwargs.get('data_path', '/tmp/tst_data')
    filename_provider = StaticFilenameProvider(f"{name}_data")
    path_provider = StaticPathProvider(
        filename_provider=filename_provider,
        directory_path=Path(data_path)
    )
    
    with init_devices(mock=RUNNING_IN_MOCK_MODE):
        panda = HDFPanda(prefix, path_provider=path_provider, name=name)
    
    logger.info(f"Created TST PandA '{name}' with prefix '{prefix}' (mock={RUNNING_IN_MOCK_MODE})")
    return panda


def create_tst_flyer(name: str, **kwargs):
    """
    Create a TST StandardFlyer with proper ophyd_async initialization.
    
    Note: StandardFlyer requires a trigger_logic parameter, but for TST
    this is typically handled by specific flyers like TriggerLogic.
    This creator provides a minimal implementation.
    
    Parameters
    ----------
    name : str
        Device name
    **kwargs
        Additional keyword arguments
        
    Returns
    -------
    StandardFlyer 
        Configured flyer device
    """
    # Import TriggerLogic for basic flyer functionality
    from ophyd_async.core import TriggerLogic, DetectorTrigger, TriggerInfo
    
    # Create a basic trigger logic for the flyer
    trigger_logic = TriggerLogic()
    
    with init_devices(mock=RUNNING_IN_MOCK_MODE):
        flyer = StandardFlyer(trigger_logic=trigger_logic, name=name)
    
    logger.info(f"Created TST flyer '{name}' (mock={RUNNING_IN_MOCK_MODE})")
    return flyer