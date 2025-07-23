"""
TST NSLS-II Flyer Devices

Flyer device classes for coordinated acquisition at the TST beamline.
"""

import logging
from ophyd_async.core import StandardFlyer, init_devices

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
        # Default flyer for standard operations
        default_flyer = StandardFlyer(name="default_flyer")
        
        # Manta flyer for camera coordination
        manta_flyer = StandardFlyer(name="manta_flyer")
        
        # PandA flyer for trigger coordination
        panda_flyer = StandardFlyer(name="panda_flyer")
    
    flyers = {
        'default_flyer': default_flyer,
        'manta_flyer': manta_flyer,
        'panda_flyer': panda_flyer,
    }
    
    logger.info(f"Created TST flyers (mock={mock}): {list(flyers.keys())}")
    return flyers