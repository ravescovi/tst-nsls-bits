"""
TST NSLS-II Motor Devices

Motor device classes for the TST beamline using ophyd_async.
"""

import logging
from ophyd_async.epics.motor import Motor
from ophyd_async.core import init_devices

logger = logging.getLogger(__name__)

# TST motor configuration
# Based on original TST profile collection startup/05-motors.py

def create_tst_motors(mock: bool = False):
    """
    Create TST beamline motors.
    
    Parameters
    ----------
    mock : bool, optional
        If True, create simulated motors. Default: False
        
    Returns
    -------
    dict
        Dictionary of motor objects
    """
    
    with init_devices(mock=mock):
        # Rotation motor for tomography
        rot_motor = Motor(
            "XF:31ID1-OP:1{CMT:1-Ax:Rot}Mtr", 
            name="rot_motor"
        )
    
    motors = {
        'rot_motor': rot_motor,
    }
    
    logger.info(f"Created TST motors (mock={mock}): {list(motors.keys())}")
    return motors