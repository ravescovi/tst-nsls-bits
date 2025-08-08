"""
TST NSLS-II Path Providers

Path provider implementations for NSLS-II TST beamline data organization.
Based on the original tst-profile-collection 03-providers.py implementation.
"""

import os
from pathlib import Path

from nslsii.ophyd_async.providers import NSLS2PathProvider
from ophyd_async.core import PathInfo


class TSTPathProvider(NSLS2PathProvider):
    """
    TST-specific path provider for NSLS-II data organization.

    This provider generates proposal-aware directory paths following
    NSLS-II standards for the TST beamline.
    """

    def __init__(self, metadata_dict=None):
        """Initialize TST path provider with metadata."""
        if metadata_dict is None:
            # Default metadata for non-mock mode
            metadata_dict = {
                "proposal_id": "commissioning",
                "scan_id": 1,
                "beamline_id": "tst",
            }
        super().__init__(metadata_dict=metadata_dict)

    def get_beamline_proposals_dir(self):
        """
        Function that computes path to the proposals directory based on TLA env vars.

        Returns
        -------
        Path
            Path to the beamline proposals directory
        """
        beamline_tla = os.getenv(
            "ENDSTATION_ACRONYM", os.getenv("BEAMLINE_ACRONYM", "tst")
        ).lower()

        beamline_proposals_dir = Path(
            f"/nsls2/data1/{beamline_tla}/legacy/mock-proposals"
        )

        return beamline_proposals_dir

    def __call__(self, device_name: str = None) -> PathInfo:
        """
        Generate PathInfo for device data files.

        Parameters
        ----------
        device_name : str, optional
            Name of the device requesting path information

        Returns
        -------
        PathInfo
            Path information including directory, filename, and creation depth
        """
        directory_path = self.generate_directory_path(device_name=device_name)

        return PathInfo(
            directory_path=directory_path,
            filename=self._filename_provider(),
            create_dir_depth=-7,
        )


class TSTMockPathProvider(TSTPathProvider):
    """
    Mock version of TSTPathProvider for testing and development.

    Uses local temporary directories instead of NSLS-II network paths.
    """

    def __init__(self):
        """Initialize mock path provider with required metadata."""
        # Provide mock metadata for the parent constructor
        mock_metadata = {"proposal_id": "999999", "scan_id": 1, "beamline_id": "tst"}
        super().__init__(metadata_dict=mock_metadata)

    def get_beamline_proposals_dir(self):
        """
        Mock proposals directory for testing.

        Returns
        -------
        Path
            Path to mock proposals directory
        """
        # Use local directory for mock mode
        mock_base = Path.home() / "tst_mock_data"
        beamline_tla = os.getenv(
            "ENDSTATION_ACRONYM", os.getenv("BEAMLINE_ACRONYM", "tst")
        ).lower()

        return mock_base / beamline_tla / "proposals"

    def __call__(self, device_name: str = None) -> PathInfo:
        """
        Generate mock PathInfo for testing.

        Parameters
        ----------
        device_name : str, optional
            Name of the device requesting path information

        Returns
        -------
        PathInfo
            Mock path information for testing
        """
        directory_path = self.generate_directory_path(device_name=device_name)

        return PathInfo(
            directory_path=directory_path,
            filename=self._filename_provider(),
            create_dir_depth=3,  # Less restrictive for mock mode
        )


def get_tst_path_provider(mock_mode: bool = False) -> TSTPathProvider:
    """
    Factory function to get appropriate path provider.

    Parameters
    ----------
    mock_mode : bool, optional
        If True, return mock path provider for testing

    Returns
    -------
    TSTPathProvider
        Configured path provider instance
    """
    if mock_mode:
        return TSTMockPathProvider()
    else:
        # For real mode, use commissioning metadata as default
        metadata_dict = {
            "proposal_id": "commissioning",
            "scan_id": 1,
            "beamline_id": "tst",
            "cycle": "2025-2",
            "data_session": "pass-56789",  # TODO: Get this information from the RunEngine metadata
        }
        return TSTPathProvider(metadata_dict=metadata_dict)
