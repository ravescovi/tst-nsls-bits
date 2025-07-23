"""
TST NSLS-II BITS Instrument Package.

This package provides the TST beamline instrument implementation with 
complete feature parity to the original profile collection.
"""

# Optional logging setup - only if apsbits is available
try:
    from apsbits.utils.logging_setup import configure_logging
    configure_logging()
except ImportError:
    # Fallback logging setup if apsbits not available
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
