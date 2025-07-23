"""
TST NSLS-II Advanced Flyer Coordination

Advanced flyer implementations with sophisticated timing coordination,
based on the original scripts/panda-flyer-async.py research.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import AsyncGenerator, AsyncIterator, Dict, List, Optional, Sequence

from bluesky.protocols import Descriptor, StreamAsset
from event_model import ComposeStreamResourceBundle, compose_stream_resource
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    DetectorTrigger,
    DetectorWriter,
    HardwareTriggeredFlyable,
    SignalRW,
    StandardFlyer,
    TriggerInfo,
    TriggerLogic,
    observe_value,
)
from ophyd_async.core.detector import StandardDetector
from ophyd_async.core.device import DeviceCollector, DeviceVector
from ophyd_async.epics.advimba import VimbaDetector
from ophyd_async.fastcs.panda import HDFPanda

logger = logging.getLogger(__name__)


class TriggerState(str, Enum):
    """Enumeration of flyer trigger states for coordination."""
    
    NULL = "null"
    PREPARING = "preparing"
    STARTING = "starting"
    STOPPING = "stopping"
    COMPLETE = "complete"
    ERROR = "error"


class TSTTriggerLogic(TriggerLogic):
    """
    TST-specific trigger logic for advanced flyer coordination.
    
    Provides sophisticated timing coordination with state tracking,
    validation, and error recovery mechanisms.
    """

    def __init__(self, name: str = "tst_trigger_logic"):
        super().__init__()
        self.name = name
        self.state = TriggerState.NULL
        self._prepared_value: Optional[int] = None
        self._start_time: Optional[float] = None
        
    def trigger_info(self, value: int) -> TriggerInfo:
        """
        Generate trigger information for the specified number of points.
        
        Parameters
        ----------
        value : int
            Number of trigger points
            
        Returns
        -------
        TriggerInfo
            Trigger configuration with timing parameters
        """
        # Calculate timing parameters based on TST requirements
        deadtime = max(0.001, 0.1 / value)  # Minimum 1ms, adaptive based on points
        livetime = deadtime * 0.9  # 90% duty cycle
        
        return TriggerInfo(
            num=value,
            trigger=DetectorTrigger.constant_gate,
            deadtime=deadtime,
            livetime=livetime,
        )

    async def prepare(self, value: int) -> int:
        """
        Prepare the trigger logic for the specified number of points.
        
        Parameters
        ----------
        value : int
            Number of points to prepare for
            
        Returns
        -------
        int
            Confirmed number of points
        """
        logger.info(f"Preparing {self.name} trigger logic for {value} points")
        self.state = TriggerState.PREPARING
        
        try:
            # Validate input parameters
            if value <= 0:
                raise ValueError(f"Invalid number of points: {value}")
                
            # Store prepared configuration
            self._prepared_value = value
            
            # Simulate preparation time for hardware coordination
            await asyncio.sleep(0.01)
            
            logger.debug(f"Trigger logic preparation complete for {value} points")
            return value
            
        except Exception as e:
            self.state = TriggerState.ERROR
            logger.error(f"Trigger logic preparation failed: {e}")
            raise

    async def start(self) -> None:
        """Start the trigger sequence."""
        if self.state != TriggerState.PREPARING:
            raise RuntimeError(f"Cannot start from state {self.state}")
            
        logger.info(f"Starting {self.name} trigger sequence")
        self.state = TriggerState.STARTING
        self._start_time = time.monotonic()

    async def stop(self) -> None:
        """Stop the trigger sequence."""
        logger.info(f"Stopping {self.name} trigger sequence")
        self.state = TriggerState.STOPPING
        
        # Allow brief settling time
        await asyncio.sleep(0.001)
        
        self.state = TriggerState.COMPLETE
        
        if self._start_time is not None:
            duration = time.monotonic() - self._start_time
            logger.debug(f"Trigger sequence completed in {duration:.3f}s")


class TSTMantaFlyer(StandardFlyer):
    """
    Advanced Manta camera flyer with enhanced coordination.
    
    Provides sophisticated timing coordination, validation, and error recovery
    for Manta camera acquisitions in the TST beamline.
    """

    def __init__(
        self,
        detector: VimbaDetector,
        trigger_logic: Optional[TSTTriggerLogic] = None,
        name: str = "tst_manta_flyer",
    ):
        """
        Initialize TST Manta flyer.
        
        Parameters
        ----------
        detector : VimbaDetector
            The Manta detector to coordinate
        trigger_logic : TSTTriggerLogic, optional
            Custom trigger logic, creates default if None
        name : str
            Flyer device name
        """
        if trigger_logic is None:
            trigger_logic = TSTTriggerLogic(f"{name}_trigger_logic")
            
        super().__init__(trigger_logic=trigger_logic, name=name)
        self.detector = detector
        self._acquisition_count: Optional[int] = None
        
    async def prepare(self, value: int, **kwargs) -> None:
        """
        Prepare the Manta flyer for acquisition.
        
        Parameters
        ----------
        value : int
            Number of images to acquire
        **kwargs
            Additional preparation parameters
        """
        logger.info(f"Preparing {self.name} for {value} acquisitions")
        
        try:
            # Prepare the trigger logic
            await self.trigger_logic.prepare(value)
            
            # Configure detector for the acquisition
            self._acquisition_count = value
            
            # Set up detector parameters if available
            if hasattr(self.detector, 'hdf'):
                # Configure HDF5 capture count
                await self.detector.hdf.num_capture.set(value)
                logger.debug(f"Set detector capture count to {value}")
            
            logger.info(f"Manta flyer preparation complete for {value} acquisitions")
            
        except Exception as e:
            logger.error(f"Manta flyer preparation failed: {e}")
            raise

    async def kickoff(self) -> None:
        """Start the Manta flyer acquisition sequence."""
        if self._acquisition_count is None:
            raise RuntimeError("Flyer not prepared - call prepare() first")
            
        logger.info(f"Starting {self.name} acquisition sequence")
        
        try:
            # Start the trigger logic
            await self.trigger_logic.start()
            
            # Additional Manta-specific startup logic can go here
            logger.debug("Manta flyer kickoff complete")
            
        except Exception as e:
            logger.error(f"Manta flyer kickoff failed: {e}")
            raise

    async def complete(self) -> None:
        """Complete the Manta flyer acquisition sequence."""
        logger.info(f"Completing {self.name} acquisition")
        
        try:
            # Stop the trigger logic
            await self.trigger_logic.stop()
            
            # Reset acquisition state
            self._acquisition_count = None
            
            logger.info("Manta flyer acquisition complete")
            
        except Exception as e:
            logger.error(f"Manta flyer completion failed: {e}")
            raise


class TSTPandAFlyer(StandardFlyer):
    """
    Advanced PandA flyer with enhanced trigger coordination.
    
    Provides sophisticated PandA coordination with timing validation,
    capture configuration, and data streaming support.
    """

    def __init__(
        self,
        panda: HDFPanda,
        trigger_logic: Optional[TSTTriggerLogic] = None,
        name: str = "tst_panda_flyer",
    ):
        """
        Initialize TST PandA flyer.
        
        Parameters
        ----------
        panda : HDFPanda
            The PandA device to coordinate
        trigger_logic : TSTTriggerLogic, optional
            Custom trigger logic, creates default if None
        name : str
            Flyer device name
        """
        if trigger_logic is None:
            trigger_logic = TSTTriggerLogic(f"{name}_trigger_logic")
            
        super().__init__(trigger_logic=trigger_logic, name=name)
        self.panda = panda
        self._capture_count: Optional[int] = None
        self._selected_captures: List = []
        
    async def find_selected_captures(self) -> List:
        """
        Find all PandA signals configured for capture.
        
        Returns
        -------
        List
            List of selected capture signals
        """
        selected_captures = []
        
        try:
            # Iterate through PandA blocks to find enabled captures
            for name, block_type in dict(self.panda.children()).items():
                blocks_dict = {"1": block_type}
                if isinstance(block_type, DeviceVector):
                    blocks_dict = dict(block_type.children())
                    
                for number, block in blocks_dict.items():
                    for signal_name, signal in dict(block.children()).items():
                        if signal_name.endswith("_capture"):
                            try:
                                signal_val = await signal.get_value()
                                if hasattr(signal_val, 'value') and signal_val.value != "No":
                                    logger.debug(f"Found capture signal: {name}{number}.{signal_name}")
                                    selected_captures.append(signal)
                            except Exception as e:
                                logger.warning(f"Could not read capture signal {signal_name}: {e}")
                                
        except Exception as e:
            logger.error(f"Error finding selected captures: {e}")
            
        return selected_captures

    async def prepare(self, value: int, **kwargs) -> None:
        """
        Prepare the PandA flyer for acquisition.
        
        Parameters
        ----------
        value : int
            Number of points to capture
        **kwargs
            Additional preparation parameters
        """
        logger.info(f"Preparing {self.name} for {value} points")
        
        try:
            # Prepare the trigger logic
            await self.trigger_logic.prepare(value)
            
            # Find and validate capture configuration
            self._selected_captures = await self.find_selected_captures()
            logger.info(f"Found {len(self._selected_captures)} capture signals")
            
            # Configure PandA for the acquisition
            self._capture_count = value
            
            # Configure PandA parameters if available
            if hasattr(self.panda, 'pcap'):
                # Reset and configure PCAP
                await self.panda.pcap.arm.set(0)  # Ensure disarmed
                await asyncio.sleep(0.01)  # Brief settling time
                
            logger.info(f"PandA flyer preparation complete for {value} points")
            
        except Exception as e:
            logger.error(f"PandA flyer preparation failed: {e}")
            raise

    async def kickoff(self) -> None:
        """Start the PandA flyer acquisition sequence."""
        if self._capture_count is None:
            raise RuntimeError("Flyer not prepared - call prepare() first")
            
        logger.info(f"Starting {self.name} acquisition sequence")
        
        try:
            # Start the trigger logic
            await self.trigger_logic.start()
            
            # Arm the PandA for capture
            if hasattr(self.panda, 'pcap'):
                await self.panda.pcap.arm.set(1)
                logger.debug("PandA armed for capture")
            
            logger.debug("PandA flyer kickoff complete")
            
        except Exception as e:
            logger.error(f"PandA flyer kickoff failed: {e}")
            raise

    async def complete(self) -> None:
        """Complete the PandA flyer acquisition sequence."""
        logger.info(f"Completing {self.name} acquisition")
        
        try:
            # Disarm the PandA
            if hasattr(self.panda, 'pcap'):
                await self.panda.pcap.arm.set(0)
                logger.debug("PandA disarmed")
            
            # Stop the trigger logic
            await self.trigger_logic.stop()
            
            # Reset acquisition state
            self._capture_count = None
            self._selected_captures = []
            
            logger.info("PandA flyer acquisition complete")
            
        except Exception as e:
            logger.error(f"PandA flyer completion failed: {e}")
            raise


class TSTFlyerCoordinator:
    """
    Master coordinator for multiple TST flyers.
    
    Provides synchronized coordination of multiple flyers with timing
    validation, error recovery, and performance monitoring.
    """

    def __init__(self, name: str = "tst_flyer_coordinator"):
        """
        Initialize the flyer coordinator.
        
        Parameters
        ----------
        name : str
            Coordinator name for logging
        """
        self.name = name
        self.flyers: Dict[str, StandardFlyer] = {}
        self._coordination_state = TriggerState.NULL
        
    def add_flyer(self, name: str, flyer: StandardFlyer) -> None:
        """
        Add a flyer to the coordination group.
        
        Parameters
        ----------
        name : str
            Flyer identifier
        flyer : StandardFlyer
            Flyer device to add
        """
        self.flyers[name] = flyer
        logger.info(f"Added flyer '{name}' to coordinator")

    def remove_flyer(self, name: str) -> None:
        """
        Remove a flyer from the coordination group.
        
        Parameters
        ----------
        name : str
            Flyer identifier to remove
        """
        if name in self.flyers:
            del self.flyers[name]
            logger.info(f"Removed flyer '{name}' from coordinator")
        else:
            logger.warning(f"Flyer '{name}' not found in coordinator")

    async def prepare_all(self, value: int, **kwargs) -> None:
        """
        Prepare all flyers for coordinated acquisition.
        
        Parameters
        ----------
        value : int
            Number of points for acquisition
        **kwargs
            Additional preparation parameters
        """
        logger.info(f"Preparing {len(self.flyers)} flyers for coordinated acquisition")
        self._coordination_state = TriggerState.PREPARING
        
        try:
            # Prepare all flyers in parallel
            prepare_tasks = [
                flyer.prepare(value, **kwargs)
                for flyer in self.flyers.values()
            ]
            
            await asyncio.gather(*prepare_tasks)
            logger.info("All flyers prepared successfully")
            
        except Exception as e:
            self._coordination_state = TriggerState.ERROR
            logger.error(f"Flyer coordination preparation failed: {e}")
            raise

    async def kickoff_all(self) -> None:
        """Start all flyers in coordinated sequence."""
        if self._coordination_state != TriggerState.PREPARING:
            raise RuntimeError(f"Cannot kickoff from state {self._coordination_state}")
            
        logger.info("Starting coordinated flyer sequence")
        self._coordination_state = TriggerState.STARTING
        
        try:
            # Start all flyers in parallel
            kickoff_tasks = [
                flyer.kickoff()
                for flyer in self.flyers.values()
            ]
            
            await asyncio.gather(*kickoff_tasks)
            logger.info("All flyers started successfully")
            
        except Exception as e:
            self._coordination_state = TriggerState.ERROR
            logger.error(f"Coordinated flyer kickoff failed: {e}")
            raise

    async def complete_all(self) -> None:
        """Complete all flyers in coordinated sequence."""
        logger.info("Completing coordinated flyer sequence")
        self._coordination_state = TriggerState.STOPPING
        
        try:
            # Complete all flyers in parallel
            complete_tasks = [
                flyer.complete()
                for flyer in self.flyers.values()
            ]
            
            await asyncio.gather(*complete_tasks)
            
            self._coordination_state = TriggerState.COMPLETE
            logger.info("All flyers completed successfully")
            
        except Exception as e:
            self._coordination_state = TriggerState.ERROR
            logger.error(f"Coordinated flyer completion failed: {e}")
            raise

    async def abort_all(self) -> None:
        """Emergency abort all flyers."""
        logger.warning("Emergency abort requested for all flyers")
        
        # Attempt to complete all flyers even if some fail
        for name, flyer in self.flyers.items():
            try:
                await flyer.complete()
                logger.debug(f"Successfully aborted flyer '{name}'")
            except Exception as e:
                logger.error(f"Failed to abort flyer '{name}': {e}")
        
        self._coordination_state = TriggerState.ERROR