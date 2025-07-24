"""
Simulators from ophyd
=====================

For development and testing only, provides plans.

.. autosummary::
    ~sim_count_plan
    ~sim_print_plan
    ~sim_rel_scan_plan
"""

import logging

from apsbits.core.instrument_init import oregistry
from bluesky import plan_stubs as bps
from bluesky import plans as bp

logger = logging.getLogger(__name__)
logger.bsdev(__file__)

DEFAULT_MD = {"title": "test run with simulator(s)"}


def sim_count_plan(detector=None, num: int = 1, imax: float = 10_000, md: dict = None):
    """Demonstrate the ``count()`` plan."""
    logger.debug("sim_count_plan()")
    
    if md is None:
        md = DEFAULT_MD
    
    # Use provided detector or get from oregistry
    if detector is None:
        try:
            detector = oregistry["sim_det"]
        except KeyError:
            logger.error("sim_det not found in oregistry")
            return
    
    # Set detector parameters if supported
    if hasattr(detector, 'Imax'):
        yield from bps.mv(detector.Imax, imax)
    
    yield from bp.count([detector], num=num, md=md)


def sim_print_plan(message: str = "This is a test."):
    """Demonstrate a ``print()`` plan stub (no data streams)."""
    logger.debug("sim_print_plan()")
    yield from bps.null()
    try:
        sim_det = oregistry["sim_det"]
        sim_motor = oregistry["sim_motor"]
        print(f"sim_print_plan(): {message}")
        print(f"sim_print_plan():  {sim_motor.position=}  {sim_det.read()=}.")
    except KeyError as e:
        print(f"sim_print_plan(): {message}")
        print(f"sim_print_plan(): Device not found: {e}")


def sim_rel_scan_plan(
    detector=None,
    motor=None,
    start: float = -2.5,
    stop: float = 2.5,
    num: int = 11,
    imax: float = 10_000,
    center: float = 0,
    sigma: float = 1,
    noise: str = "uniform",  # none poisson uniform
    md: dict = None,
):
    """Demonstrate the ``rel_scan()`` plan."""
    logger.debug("sim_rel_scan_plan()")
    
    if md is None:
        md = DEFAULT_MD
    
    # Use provided devices or get from oregistry
    if detector is None:
        try:
            detector = oregistry["sim_det"]
        except KeyError:
            logger.error("sim_det not found in oregistry")
            return
            
    if motor is None:
        try:
            motor = oregistry["sim_motor"]
        except KeyError:
            logger.error("sim_motor not found in oregistry")
            return
    # Configure detector if it has the required attributes
    if hasattr(detector, 'Imax'):
        # fmt: off
        yield from bps.mv(
            detector.Imax, imax,
            detector.center, center,
            detector.sigma, sigma,
            detector.noise, noise,
        )
        # fmt: on
        print(f"sim_rel_scan_plan(): {motor.position=}.")
        print(f"sim_rel_scan_plan(): {detector.read()=}.")
        print(f"sim_rel_scan_plan(): {detector.read_configuration()=}.")
        if hasattr(detector.noise, '_enum_strs'):
            print(f"sim_rel_scan_plan(): {detector.noise._enum_strs=}.")
    
    yield from bp.rel_scan([detector], motor, start, stop, num=num, md=md)
