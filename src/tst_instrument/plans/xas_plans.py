"""
TST NSLS-II XAS Plans

X-ray Absorption Spectroscopy plans for the TST beamline.
"""

import datetime
import logging
from typing import Optional

import bluesky.plan_stubs as bps

# Import oregistry for device access
from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)

# XAS constants from original TST implementation
COUNTS_PER_REVOLUTION = 8000
DEG_PER_REVOLUTION = 360
COUNTS_PER_DEG = COUNTS_PER_REVOLUTION / DEG_PER_REVOLUTION

DEFAULT_MD = {"title": "TST XAS Scan"}


def xas_demo_async(
    npoints: int,
    total_time: float,
    start_e: float,
    end_e: float,
    detector: Optional[str] = "manta1",
    md: dict = DEFAULT_MD,
):
    """
    X-ray Absorption Spectroscopy scan with motor coordination.

    Adapted from original TST 90-plans.py xas_demo_async function.

    Parameters
    ----------
    npoints : int
        Number of data points to collect
    total_time : float
        Total scan time in seconds
    start_e : float
        Starting energy (or angle) value
    end_e : float
        Ending energy (or angle) value
    detector : str, optional
        Name of detector to use, by default "manta1"
    md : dict, optional
        Metadata dictionary

    Yields
    ------
    Msg
        Bluesky plan messages
    """
    logger.info(f"Starting XAS scan: {npoints} points from {start_e} to {end_e}")

    # Get devices from oregistry
    panda = oregistry.find(name="panda1")
    rot_motor = oregistry.find(name="rot_motor")

    # Create advanced flyer coordinator for sophisticated coordination
    from tst_instrument.devices.tst_flyer import create_advanced_flyer_coordinator

    # Create flyers dynamically (enhanced from original TST)
    detectors_list = [detector] if detector else []
    coordinator = create_advanced_flyer_coordinator(
        detectors=detectors_list, panda=panda, name="xas_coordinator"
    )

    # Get basic flyers for backward compatibility
    try:
        manta_flyer = oregistry.find(name="manta_flyer")
        panda_flyer = oregistry.find(name="panda_flyer")
    except Exception as e:
        logger.warning(f"Could not find basic flyers: {e}")
        manta_flyer = None
        panda_flyer = None

    # Get detector if specified
    if detector:
        detector = oregistry.find(name=detector)
    else:
        detector = None

    # Use energy values as degrees for motor positioning
    start_deg = start_e
    end_deg = end_e

    # Get PandA components
    panda_pcomp1 = panda.pcomp[1]
    # panda_pcap1 = panda.pcap  # Not used in this implementation
    panda_clock1 = panda.clock[1]

    # Timing calculations
    reset_time = 0.001  # 1 ms
    clock_period_ms = total_time * 1000 / npoints
    clock_width_ms = clock_period_ms - reset_time
    target_velocity = (end_deg - start_deg) / total_time

    # Position calculations
    pre_start_deg = 5.0  # degrees before start position
    pre_start_cnt = pre_start_deg * COUNTS_PER_DEG
    start_cnt = pre_start_cnt
    width_deg = end_deg - start_deg
    width_cnt = width_deg * COUNTS_PER_DEG

    print(f"{pre_start_cnt=}, {width_deg=}, {width_cnt=}")

    # Setup device lists
    panda_devices = [panda, panda_flyer]
    all_devices = panda_devices

    if detector:
        detector_devices = [detector, manta_flyer]
        all_devices = panda_devices + detector_devices

    # Enhanced metadata
    _md = {
        "plan_name": "xas_demo_async",
        "beamline_id": "tst_nsls",
        "scan_type": "xas",
        "npoints": npoints,
        "total_time": total_time,
        "start_energy": start_e,
        "end_energy": end_e,
        "target_velocity": target_velocity,
        "motors": [rot_motor.name],
        **md,
    }

    if detector:
        _md["detectors"] = [detector.name]

    # Move to starting position
    yield from bps.mv(rot_motor.velocity, 180 / 2)  # Fast move
    yield from bps.mv(rot_motor, start_deg - pre_start_deg)
    yield from bps.mv(rot_motor.velocity, target_velocity)  # Set scan velocity

    # Configure PandA
    yield from bps.mv(panda_pcomp1.enable, "ZERO")  # Disable pcomp
    yield from bps.mv(panda_pcomp1.start, int(start_cnt))
    yield from bps.mv(panda_pcomp1.width, int(width_cnt))

    # Configure clock
    yield from bps.mv(panda_clock1.period, clock_period_ms)
    yield from bps.mv(panda_clock1.period_units, "ms")
    yield from bps.mv(panda_clock1.width, clock_width_ms)
    yield from bps.mv(panda_clock1.width_units, "ms")

    print("Clock configured:", datetime.datetime.now().strftime("%H:%M:%S"))

    yield from bps.open_run(md=_md)
    print("Run opened:", datetime.datetime.now().strftime("%H:%M:%S"))

    # Stage all devices
    yield from bps.stage_all(*all_devices)
    print("Staging complete:", datetime.datetime.now().strftime("%H:%M:%S"))

    # Advanced flyer coordination preparation
    if len(coordinator.flyers) > 0:
        logger.info("Using advanced flyer coordinator for enhanced timing precision")
        yield from coordinator.prepare_all(npoints)
        print(
            "Advanced coordination preparation complete:",
            datetime.datetime.now().strftime("%H:%M:%S"),
        )

    # Prepare flyers and devices (backward compatibility)
    if detector and manta_flyer:
        yield from bps.mv(detector._writer.hdf.num_capture, npoints)
        yield from bps.prepare(manta_flyer, npoints, wait=True)
        yield from bps.prepare(detector, manta_flyer.trigger_info, wait=True)
        print(
            "Manta preparation complete:", datetime.datetime.now().strftime("%H:%M:%S")
        )

    if panda_flyer:
        yield from bps.prepare(panda_flyer, npoints, wait=True)
        yield from bps.prepare(panda, panda_flyer.trigger_info, wait=True)
        print(
            "PandA preparation complete:", datetime.datetime.now().strftime("%H:%M:%S")
        )

    # Advanced flyer coordination kickoff
    if len(coordinator.flyers) > 0:
        yield from coordinator.kickoff_all()
        print(
            "Advanced coordination kickoff complete:",
            datetime.datetime.now().strftime("%H:%M:%S"),
        )

    # Kickoff all devices
    for device in all_devices:
        yield from bps.kickoff(device)
    print("Kickoff complete:", datetime.datetime.now().strftime("%H:%M:%S"))

    # Enable pcomp and start motor movement
    yield from bps.mv(panda_pcomp1.enable, "ONE")
    yield from bps.mv(rot_motor, end_deg + pre_start_deg)  # Move beyond end
    print("Motor movement started:", datetime.datetime.now().strftime("%H:%M:%S"))

    # Complete PandA
    for flyer_or_panda in panda_devices:
        yield from bps.complete(flyer_or_panda, wait=True, group="complete_panda")
    print("PandA complete:", datetime.datetime.now().strftime("%H:%M:%S"))

    # Complete detector if present
    if detector:
        for flyer_or_det in detector_devices:
            yield from bps.complete(flyer_or_det, wait=True, group="complete_detector")
        print("Detector complete:", datetime.datetime.now().strftime("%H:%M:%S"))

    print("Acquisition complete:", datetime.datetime.now().strftime("%H:%M:%S"))

    # Wait for PandA completion and collect data
    done = False
    while not done:
        try:
            yield from bps.wait(group="complete_panda", timeout=0.5)
        except TimeoutError:
            pass
        else:
            done = True

        panda_stream_name = f"{panda.name}_stream"
        yield from bps.declare_stream(panda, name=panda_stream_name)
        yield from bps.collect(panda, name=panda_stream_name)

    print("PandA file saving complete")
    yield from bps.unstage_all(*panda_devices)
    yield from bps.mv(panda_pcomp1.enable, "ZERO")
    print("PandA unstaging complete")

    # Wait for detector completion if present
    done = False if detector else True
    while not done:
        try:
            yield from bps.wait(group="complete_detector", timeout=0.5)
        except TimeoutError:
            pass
        else:
            done = True

        detector_stream_name = f"{detector.name}_stream"
        yield from bps.declare_stream(detector, name=detector_stream_name)
        yield from bps.collect(detector, name=detector_stream_name)
        yield from bps.sleep(0.01)
        print("Detector HDF5 saved")

    yield from bps.close_run()

    # Report results
    panda_val = yield from bps.rd(panda.data.num_captured)
    print(f"{panda_val = }")

    if detector:
        manta_val = yield from bps.rd(detector._writer.hdf.num_captured)
        print(f"{manta_val = }")
        yield from bps.unstage_all(*detector_devices)

    # Reset velocity
    yield from bps.mv(rot_motor.velocity, 180 / 2)

    logger.info("XAS scan completed successfully")


def energy_calibration_plan(
    energy_points: list, motor: str = "rot_motor", md: dict = None
):
    """
    Energy calibration plan for XAS measurements.

    Parameters
    ----------
    energy_points : list
        List of energy values for calibration
    motor : str, optional
        Name of motor to use, by default "rot_motor"
    md : dict, optional
        Metadata dictionary

    Yields
    ------
    Msg
        Bluesky plan messages
    """
    logger.info(f"Starting energy calibration with {len(energy_points)} points")

    if md is None:
        md = DEFAULT_MD

    # Get motor from oregistry
    motor_device = oregistry.find(name=motor)

    _md = {
        "plan_name": "energy_calibration_plan",
        "beamline_id": "tst_nsls",
        "scan_type": "calibration",
        "energy_points": energy_points,
        "motors": [motor_device.name],
        **md,
    }

    yield from bps.open_run(md=_md)

    for i, energy in enumerate(energy_points):
        print(f"Calibration point {i+1}/{len(energy_points)}: {energy}")
        yield from bps.mv(motor_device, energy)
        yield from bps.trigger_and_read([motor_device], name="calibration")

    yield from bps.close_run()
    logger.info("Energy calibration completed")


# Note: make_decorator not needed for generator functions
# These are already proper Bluesky plans that yield messages
