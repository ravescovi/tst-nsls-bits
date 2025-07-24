"""
TST NSLS-II Hardware Utilities

Hardware initialization and warmup procedures for TST beamline devices.
Based on the original tst-profile-collection 00-startup.py implementation.
"""

import logging
from typing import List, Any

logger = logging.getLogger(__name__)


def warmup_hdf5_plugins(detectors: List[Any]) -> None:
    """
    Warm-up the HDF5 plugins for detector devices.
    
    This is necessary when the corresponding IOC restarts - we have to trigger 
    one image for the HDF5 plugin to work correctly, otherwise we get file 
    writing errors.
    
    This function has been adapted from the original TST profile collection
    to work with ophyd_async devices in the BITS framework.
    
    Parameters
    ----------
    detectors : List[Any]
        List of detector devices with HDF5 plugins to warm up
        
    Notes
    -----
    This function checks if detectors have HDF5 plugins and whether they
    need warmup based on array_size values. Only detectors with zero
    height or width in array_size are warmed up.
    """
    logger.info("Starting HDF5 plugin warmup procedure")
    
    if not detectors:
        logger.warning("No detectors provided for HDF5 warmup")
        return
    
    warmed_count = 0
    skipped_count = 0
    
    for det in detectors:
        try:
            # Check if detector has HDF5 plugin
            if not hasattr(det, 'hdf5'):
                logger.debug(f"Detector {det.name} does not have HDF5 plugin, skipping")
                skipped_count += 1
                continue
            
            # Get current array size
            try:
                _array_size = det.hdf5.array_size.get()
                logger.debug(f"Detector {det.name} array_size: {_array_size}")
            except Exception as e:
                logger.warning(f"Could not get array_size for {det.name}: {e}")
                skipped_count += 1
                continue
            
            # Check if warmup is needed (array size has zero dimensions)
            needs_warmup = (
                hasattr(_array_size, 'height') and hasattr(_array_size, 'width') and
                (0 in [_array_size.height, _array_size.width])
            )
            
            if needs_warmup:
                logger.info(f"Warming up HDF5 plugin for {det.name} - array_size={_array_size}")
                print(f"\n  Warming up HDF5 plugin for {det.name} as the array_size={_array_size}...")
                
                try:
                    # Perform the warmup
                    det.hdf5.warmup()
                    
                    # Verify warmup was successful
                    new_array_size = det.hdf5.array_size.get()
                    logger.info(f"HDF5 warmup completed for {det.name} - new array_size={new_array_size}")
                    print(f"  Warming up HDF5 plugin for {det.name} is done. array_size={new_array_size}\n")
                    warmed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to warm up HDF5 plugin for {det.name}: {e}")
                    print(f"  ERROR: Failed to warm up HDF5 plugin for {det.name}: {e}\n")
                    
            else:
                logger.debug(f"HDF5 warmup not needed for {det.name} - array_size={_array_size}")
                print(f"\n  Warming up of the HDF5 plugin is not needed for {det.name} as the array_size={_array_size}.")
                skipped_count += 1
                
        except Exception as e:
            logger.error(f"Error processing detector {getattr(det, 'name', 'unknown')}: {e}")
            skipped_count += 1
    
    logger.info(f"HDF5 warmup completed: {warmed_count} warmed, {skipped_count} skipped")
    print(f"\nHDF5 warmup summary: {warmed_count} devices warmed up, {skipped_count} skipped")

