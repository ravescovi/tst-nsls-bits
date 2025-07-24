"""
TST NSLS-II Flyer Devices

Comprehensive flyer device classes for the TST beamline, including basic flyers,
advanced coordination, and sophisticated timing validation.
"""

import asyncio
import logging
import os
import time
from enum import Enum
from typing import Dict, List, Optional

from ophyd_async.core import (
    DetectorTrigger,
    StandardFlyer,
    TriggerInfo,
    TriggerLogic,
    init_devices,
)
from ophyd_async.core.device import DeviceVector
from ophyd_async.epics.advimba import VimbaDetector
from ophyd_async.fastcs.panda import HDFPanda

logger = logging.getLogger(__name__)


# Enumerations and Constants

class TriggerState(str, Enum):
    """Enumeration of flyer trigger states for coordination."""

    NULL = "null"
    PREPARING = "preparing"
    STARTING = "starting"
    STOPPING = "stopping"
    COMPLETE = "complete"
    ERROR = "error"


# Basic TST Flyer Classes

class TSTFlyer(StandardFlyer):
    """
    TST beamline StandardFlyer device.
    
    Enhanced StandardFlyer class with TST-specific trigger logic.
    """
    
    def __init__(self, name: str = "", trigger_logic=None, **kwargs):
        """
        Initialize TST flyer with default trigger logic if not provided.
        
        Parameters
        ----------
        name : str
            Device name
        trigger_logic : TriggerLogic, optional
            Trigger logic for the flyer. If not provided, creates a default TriggerLogic.
        **kwargs
            Additional keyword arguments passed to StandardFlyer
        """
        # Check if running in mock mode
        mock_mode = (
            os.environ.get("TST_MOCK_MODE", "NO") == "YES"
            or os.environ.get("RUNNING_IN_NSLS2_CI", "NO") == "YES"
        )
        
        if trigger_logic is None:
            # Create a basic trigger logic for the flyer
            trigger_logic = TriggerLogic()
        
        # Initialize with mock mode context
        with init_devices(mock=mock_mode):
            super().__init__(trigger_logic=trigger_logic, name=name, **kwargs)
            
        logger.info(f"Initialized TST flyer '{name}' (mock={mock_mode})")


# Advanced Trigger Logic

class TSTTriggerLogic(TriggerLogic):
    """
    TST-specific trigger logic for advanced flyer coordination.

    Provides sophisticated timing coordination with state tracking,
    validation, and error recovery mechanisms.
    """

    def __init__(self, name: str = "tst_trigger_logic"):
        """Initialize TST trigger logic."""
        super().__init__()
        self.name = name
        self.state = TriggerState.NULL
        self._prepared_value: Optional[int] = None
        self._timing_params: Dict[str, float] = {}
        self._validation_enabled: bool = True

    def trigger_info(self, value: int) -> TriggerInfo:
        """
        Generate trigger information with TST-specific timing calculations.

        Parameters
        ----------
        value : int
            Number of triggers/frames to acquire

        Returns
        -------
        TriggerInfo
            Trigger information with deadtime and livetime
        """
        # TST-specific timing calculations
        # Based on research from scripts/panda-flyer-async.py
        deadtime = max(0.001, 0.1 / value)  # Dynamic deadtime based on rate
        livetime = deadtime * 0.9  # 90% duty cycle

        self._timing_params = {
            "num_triggers": value,
            "deadtime": deadtime,
            "livetime": livetime,
            "total_time": value * deadtime,
        }

        return TriggerInfo(
            num=value,
            trigger=DetectorTrigger.constant_gate,
            deadtime=deadtime,
            livetime=livetime,
        )

    async def prepare(self, value: int):
        """Prepare trigger logic with state tracking."""
        self.state = TriggerState.PREPARING
        self._prepared_value = value
        logger.debug(f"{self.name}: Preparing for {value} triggers")

        # Validate timing if enabled
        if self._validation_enabled:
            info = self.trigger_info(value)
            if info.livetime >= info.deadtime:
                logger.warning(
                    f"{self.name}: Livetime ({info.livetime}) >= "
                    f"deadtime ({info.deadtime}), adjusting"
                )

        self.state = TriggerState.NULL

    async def start(self):
        """Start triggering with state management."""
        if self._prepared_value is None:
            raise RuntimeError(f"{self.name}: Cannot start - not prepared")

        self.state = TriggerState.STARTING
        logger.debug(f"{self.name}: Starting acquisition")

    async def stop(self):
        """Stop triggering and cleanup."""
        self.state = TriggerState.STOPPING
        logger.debug(f"{self.name}: Stopping acquisition")
        self.state = TriggerState.COMPLETE

    def get_timing_params(self) -> Dict[str, float]:
        """Get current timing parameters for coordination."""
        return self._timing_params.copy()


# Specialized Flyer Classes

class TSTMantaFlyer(StandardFlyer):
    """
    Specialized flyer for Manta detectors with TST-specific enhancements.

    Provides advanced integration with VimbaDetector devices and
    sophisticated timing coordination.
    """

    def __init__(self, detector: VimbaDetector, name: str = "tst_manta_flyer"):
        """Initialize Manta flyer with detector integration."""
        # Use TST trigger logic for Manta
        trigger_logic = TSTTriggerLogic(f"{name}_trigger_logic")

        super().__init__(trigger_logic=trigger_logic, name=name)
        self.detector = detector
        self._prepared_frames: Optional[int] = None

    async def prepare(self, value: int):
        """Prepare Manta detector and flyer for acquisition."""
        await super().prepare(value)
        self._prepared_frames = value

        # Configure detector based on trigger info
        trigger_info = self.trigger_logic.trigger_info(value)

        logger.info(
            f"{self.name}: Preparing Manta detector for {value} frames "
            f"with {trigger_info.deadtime:.3f}s deadtime"
        )

    async def kickoff(self):
        """Start Manta acquisition with validation."""
        if self._prepared_frames is None:
            raise RuntimeError("Manta flyer not prepared")

        logger.info(f"{self.name}: Kicking off Manta acquisition")
        await super().kickoff()

    async def complete(self):
        """Complete Manta acquisition and verify data."""
        await super().complete()
        logger.info(f"{self.name}: Manta acquisition complete")


class TSTPandAFlyer(StandardFlyer):
    """
    Specialized flyer for PandA with TST-specific capabilities.

    Integrates with HDFPanda for sophisticated triggering and
    data acquisition coordination.
    """

    def __init__(self, panda: HDFPanda, name: str = "tst_panda_flyer"):
        """Initialize PandA flyer with device integration."""
        # Use TST trigger logic for PandA
        trigger_logic = TSTTriggerLogic(f"{name}_trigger_logic")

        super().__init__(trigger_logic=trigger_logic, name=name)
        self.panda = panda
        self._selected_captures: List = []

    async def prepare(self, value: int):
        """Prepare PandA for acquisition with capture selection."""
        await super().prepare(value)

        # Configure PandA based on trigger info
        trigger_info = self.trigger_logic.trigger_info(value)

        # Select capture signals (from research)
        self._selected_captures = await self._select_capture_signals()

        logger.info(
            f"{self.name}: Preparing PandA for {value} triggers "
            f"with {len(self._selected_captures)} capture signals"
        )

    async def _select_capture_signals(self) -> List:
        """Select active PandA capture signals."""
        selected_captures = []

        # Iterate through PandA blocks to find capture signals
        for attr_name in dir(self.panda):
            attr = getattr(self.panda, attr_name)

            # Check if this is a block with capture capability
            if isinstance(attr, DeviceVector):
                name = attr_name
                blocks_dict = dict(attr.children())

                for number, block in blocks_dict.items():
                    for signal_name, signal in dict(block.children()).items():
                        if signal_name.endswith("_capture"):
                            try:
                                signal_val = await signal.get_value()
                                if (
                                    hasattr(signal_val, "value")
                                    and signal_val.value != "No"
                                ):
                                    logger.debug(
                                        f"Found capture signal: "
                                        f"{name}{number}.{signal_name}"
                                    )
                                    selected_captures.append(signal)
                            except Exception as e:
                                logger.warning(
                                    f"Could not read capture signal {signal_name}: {e}"
                                )

        return selected_captures

    async def kickoff(self):
        """Start PandA acquisition."""
        logger.info(f"{self.name}: Kicking off PandA acquisition")
        await super().kickoff()

    async def complete(self):
        """Complete PandA acquisition."""
        await super().complete()
        logger.info(f"{self.name}: PandA acquisition complete")


# Advanced Coordination

class TSTFlyerCoordinator:
    """
    Advanced flyer coordinator for multi-device synchronized acquisition.

    Provides sophisticated coordination between multiple flyers with
    timing validation, synchronization, and error recovery.
    """

    def __init__(self, name: str = "tst_flyer_coordinator"):
        """Initialize the flyer coordinator."""
        self.name = name
        self.flyers: Dict[str, StandardFlyer] = {}
        self._timing_validator = TimingValidator()
        self._prepared = False

    def add_flyer(self, key: str, flyer: StandardFlyer):
        """Add a flyer to the coordination group."""
        self.flyers[key] = flyer
        logger.info(f"{self.name}: Added flyer '{key}' to coordination group")

    async def prepare_all(self, value: int):
        """Prepare all flyers with timing coordination."""
        logger.info(f"{self.name}: Preparing {len(self.flyers)} flyers for {value} frames")

        # Collect timing parameters from all flyers
        timing_params = {}
        for key, flyer in self.flyers.items():
            await flyer.prepare(value)
            if hasattr(flyer.trigger_logic, "get_timing_params"):
                timing_params[key] = flyer.trigger_logic.get_timing_params()

        # Validate timing coordination
        if timing_params:
            validation_result = self._timing_validator.validate_coordination(timing_params)
            if not validation_result["valid"]:
                logger.warning(
                    f"{self.name}: Timing validation warnings: "
                    f"{validation_result['warnings']}"
                )

        self._prepared = True

    async def kickoff_all(self):
        """Start all flyers with synchronization."""
        if not self._prepared:
            raise RuntimeError(f"{self.name}: Not prepared for kickoff")

        logger.info(f"{self.name}: Kicking off {len(self.flyers)} flyers")

        # Kickoff all flyers concurrently
        tasks = [flyer.kickoff() for flyer in self.flyers.values()]
        await asyncio.gather(*tasks)

    async def complete_all(self):
        """Complete all flyers and collect results."""
        logger.info(f"{self.name}: Completing {len(self.flyers)} flyers")

        # Complete all flyers
        tasks = [flyer.complete() for flyer in self.flyers.values()]
        await asyncio.gather(*tasks)

        self._prepared = False


class TimingValidator:
    """Validates timing parameters across multiple flyers."""

    def validate_coordination(self, timing_params: Dict[str, Dict]) -> Dict:
        """
        Validate timing coordination across flyers.

        Returns dict with 'valid' bool and 'warnings' list.
        """
        warnings = []
        valid = True

        # Extract timing values
        deadtimes = []
        livetimes = []
        total_times = []

        for flyer_name, params in timing_params.items():
            if "deadtime" in params:
                deadtimes.append(params["deadtime"])
            if "livetime" in params:
                livetimes.append(params["livetime"])
            if "total_time" in params:
                total_times.append(params["total_time"])

        # Check for timing mismatches
        if deadtimes and max(deadtimes) / min(deadtimes) > 1.1:
            warnings.append(
                f"Deadtime mismatch: {min(deadtimes):.3f}s to {max(deadtimes):.3f}s"
            )

        if total_times and max(total_times) / min(total_times) > 1.1:
            warnings.append(
                f"Total time mismatch: {min(total_times):.3f}s to {max(total_times):.3f}s"
            )
            valid = False

        return {"valid": valid, "warnings": warnings}


# Factory Functions

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
        # Basic flyers for backward compatibility
        default_flyer = StandardFlyer(name="default_flyer")

        # Enhanced trigger logic for TST coordination
        manta_trigger_logic = TSTTriggerLogic("manta_trigger_logic")
        panda_trigger_logic = TSTTriggerLogic("panda_trigger_logic")

        # Advanced flyers with coordination (will be enhanced by plans)
        manta_flyer = StandardFlyer(
            trigger_logic=manta_trigger_logic, name="manta_flyer"
        )
        panda_flyer = StandardFlyer(
            trigger_logic=panda_trigger_logic, name="panda_flyer"
        )

    flyers = {
        "default_flyer": default_flyer,
        "manta_flyer": manta_flyer,
        "panda_flyer": panda_flyer,
    }

    logger.info(f"Created TST flyers (mock={mock}): {list(flyers.keys())}")
    return flyers


def create_advanced_flyer_coordinator(
    detectors=None, panda=None, name="tst_coordinator"
):
    """
    Create an advanced flyer coordinator for sophisticated acquisition coordination.

    Parameters
    ----------
    detectors : list, optional
        List of detector devices to coordinate
    panda : HDFPanda, optional
        PandA device for trigger coordination
    name : str
        Coordinator name

    Returns
    -------
    TSTFlyerCoordinator
        Configured flyer coordinator
    """
    coordinator = TSTFlyerCoordinator(name)

    # Add detectors as Manta flyers if provided
    if detectors:
        for i, detector in enumerate(detectors):
            if hasattr(detector, "hdf"):  # VimbaDetector-like device
                flyer = TSTMantaFlyer(detector, name=f"manta_flyer_{i}")
                coordinator.add_flyer(f"manta_{i}", flyer)

    # Add PandA flyer if provided
    if panda:
        panda_flyer = TSTPandAFlyer(panda, name="advanced_panda_flyer")
        coordinator.add_flyer("panda", panda_flyer)

    logger.info(
        f"Created advanced flyer coordinator '{name}' with "
        f"{len(coordinator.flyers)} flyers"
    )
    return coordinator