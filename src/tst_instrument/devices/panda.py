"""
TST NSLS-II PandA Devices

PandA box device classes for the TST beamline using ophyd_async.
"""

import logging
from ophyd_async.fastcs.panda import HDFPanda
from ophyd_async.core import init_devices

logger = logging.getLogger(__name__)

# TST PandA configuration
# Based on original TST profile collection startup/10-panda.py

def create_tst_panda(mock: bool = False):
    """
    Create TST beamline PandA device.
    
    Parameters
    ----------
    mock : bool, optional
        If True, create simulated PandA. Default: False
        
    Returns
    -------
    dict
        Dictionary of PandA objects
    """
    
    with init_devices(mock=mock):
        # PandA box for trigger coordination
        panda1 = HDFPanda(
            "XF:31ID1-ES:1{Panda:1}",
            name="panda1"
        )
    
    pandas = {
        'panda1': panda1,
    }
    
    logger.info(f"Created TST PandA devices (mock={mock}): {list(pandas.keys())}")
    return pandas