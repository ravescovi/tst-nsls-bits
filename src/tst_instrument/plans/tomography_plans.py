"""
TST NSLS-II Tomography Plans

Tomography data collection plans for the TST beamline.
"""

import logging
from typing import List
from typing import Optional

import bluesky.plan_stubs as bps

# Import oregistry for device access
from apsbits.core.instrument_init import oregistry
from ophyd_async.core import DetectorTrigger
from ophyd_async.core import TriggerInfo
from ophyd_async.epics.motor import FlyMotorInfo

logger = logging.getLogger(__name__)

# Tomography constants from original TST implementation
COUNTS_PER_REVOLUTION = 8000
DEG_PER_REVOLUTION = 360
COUNTS_PER_DEG = COUNTS_PER_REVOLUTION / DEG_PER_REVOLUTION

DEFAULT_MD = {"title": "TST Tomography Scan"}


def tomo_demo_async(
    detectors: Optional[List] = None,
    panda=None,
    num_images: int = 21,
    scan_time: float = 9,
    start_deg: float = 0,
    exposure_time: Optional[float] = None,
    md: dict = DEFAULT_MD,
):
    """
    Tomography data collection plan with PandA coordination.

    Adapted from original TST 90-plans.py tomo_demo_async function.

    Parameters
    ----------
    detectors : List, optional
        List of detector objects. If None, uses [manta1] from oregistry
    num_images : int, optional
        Number of images to collect, by default 21
    scan_time : float, optional
        Total scan time in seconds, by default 9
    start_deg : float, optional
        Starting rotation angle in degrees, by default 0
    exposure_time : float, optional
        Exposure time per image. If None, calculated automatically.
    md : dict, optional
        Metadata dictionary

    Yields
    ------
    Msg
        Bluesky plan messages
    """
    logger.info(f"Starting tomography scan: {num_images} images over {scan_time}s")

    # Get devices from oregistry
    if detectors is None:
        detectors = [oregistry.find(name="manta1")]
    if panda is None:
        panda = oregistry.find(name="panda1")
    rot_motor = oregistry.find(name="rot_motor")

    # Get PandA pcomp block
    pcomp = panda.pcomp[1]

    # Calculate step parameters
    step_width_counts = COUNTS_PER_REVOLUTION / (2 * (num_images - 1))
    if int(step_width_counts) != round(step_width_counts, 5):
        raise ValueError(
            "The number of encoder counts per pulse is not an integer value!"
        )

    step_time = scan_time / num_images
    if exposure_time is not None:
        if exposure_time > step_time:
            raise RuntimeError(
                f"Your configured exposure time is longer than "
                f"the step size {step_time}"
            )
    else:
        exposure_time = step_time / 3

    # Setup device lists
    all_detectors = [*detectors, panda]
    all_devices = [*all_detectors, rot_motor]

    # Configure trigger information
    det_trigger_info = TriggerInfo(
        exposures_per_event=num_images,
        livetime=exposure_time,
        deadtime=0.001,
        trigger=DetectorTrigger.EDGE_TRIGGER,
    )

    panda_trigger_info = TriggerInfo(
        exposures_per_event=num_images,
        livetime=exposure_time,
        deadtime=0.001,
        trigger=DetectorTrigger.CONSTANT_GATE,
    )

    # Motor fly information
    rot_motor_fly_info = FlyMotorInfo(
        start_position=start_deg - 5,
        end_position=start_deg + DEG_PER_REVOLUTION / 2 + 5,
        time_for_move=scan_time,
    )

    # Calculate encoder parameters
    start_encoder = start_deg * COUNTS_PER_DEG
    width_in_counts = (180 / scan_time) * COUNTS_PER_DEG * exposure_time

    if width_in_counts > step_width_counts:
        raise RuntimeError(
            f"Your specified exposure time of {exposure_time}s is too long! "
            f"Calculated width: {width_in_counts}, Step size: {step_width_counts}"
        )

    print(f"Exposing camera for {width_in_counts} counts")

    # Enhanced metadata
    _md = {
        "plan_name": "tomo_demo_async",
        "beamline_id": "tst_nsls",
        "scan_type": "tomography",
        "num_images": num_images,
        "scan_time": scan_time,
        "start_deg": start_deg,
        "exposure_time": exposure_time,
        "detectors": [det.name for det in detectors],
        "motors": [rot_motor.name],
        **md,
    }

    # Set up the pcomp block
    yield from bps.mv(pcomp.start, int(start_encoder))
    yield from bps.mv(pcomp.step, step_width_counts)
    yield from bps.mv(pcomp.pulses, num_images)

    yield from bps.open_run(md=_md)

    # Stage all devices
    yield from bps.stage_all(*all_devices)

    # Prepare devices
    for det in detectors:
        yield from bps.prepare(det, det_trigger_info, group="prepare_all", wait=False)

    yield from bps.prepare(panda, panda_trigger_info, group="prepare_all", wait=False)
    yield from bps.prepare(
        rot_motor, rot_motor_fly_info, group="prepare_all", wait=False
    )

    yield from bps.wait(group="prepare_all")
    yield from bps.kickoff_all(*all_devices, wait=True)

    yield from bps.declare_stream(*all_detectors, name="tomo_stream")
    yield from bps.collect_while_completing(
        all_devices, all_detectors, flush_period=0.25, stream_name="tomo_stream"
    )

    yield from bps.unstage_all(*all_devices)
    yield from bps.close_run()

    # Report results
    panda_val = yield from bps.rd(panda.data.num_captured)
    print(f"{panda_val = } ")
    for det in detectors:
        manta_val = yield from bps.rd(det.fileio.num_captured)
        print(f"{det.name} = {manta_val} ")

    # Reset velocity
    yield from bps.mv(rot_motor.velocity, 180 / 2)

    logger.info("Tomography scan completed successfully")


def _manta_collect_dark_flat(
    detectors: Optional[List] = None,
    num_dark: int = 10,
    num_flat: int = 10,
    md: dict = DEFAULT_MD,
):
    """
    Collect dark and flat field images for tomography.

    Parameters
    ----------
    detectors : List, optional
        List of detector objects. If None, uses [manta1] from oregistry
    num_dark : int, optional
        Number of dark images to collect, by default 10
    num_flat : int, optional
        Number of flat images to collect, by default 10
    md : dict, optional
        Metadata dictionary

    Yields
    ------
    Msg
        Bluesky plan messages
    """
    logger.info(f"Collecting dark ({num_dark}) and flat ({num_flat}) images")

    # Get devices from oregistry
    if detectors is None:
        detectors = [oregistry.find(name="manta1")]

    _md = {
        "plan_name": "_manta_collect_dark_flat",
        "beamline_id": "tst_nsls",
        "scan_type": "calibration",
        "num_dark": num_dark,
        "num_flat": num_flat,
        "detectors": [det.name for det in detectors],
        **md,
    }

    yield from bps.open_run(md=_md)

    # Collect dark images (with beam blocked)
    print("Collecting dark images...")
    # TODO: Add shutter control when available
    for _ in range(num_dark):
        yield from bps.trigger_and_read(detectors, name="dark")

    # Collect flat images (with beam open, no sample)
    print("Collecting flat images...")
    # TODO: Add sample stage movement when available
    for _ in range(num_flat):
        yield from bps.trigger_and_read(detectors, name="flat")

    yield from bps.close_run()
    logger.info("Dark and flat collection completed")
