# TST NSLS-II BITS Instrument Package

BITS instrument package for the TST (Test) beamline at NSLS-II (National Synchrotron Light Source II).

## Overview

This package provides Bluesky data acquisition capabilities for the TST beamline, including:
- Tomography data collection with PandA coordination
- X-ray Absorption Spectroscopy (XAS) scanning
- Manta camera integration for imaging
- Motor control for sample positioning
- Queue server support for automated measurements

## Installation

### Create and activate the BITS environment

```bash
export ENV_NAME=BITS_tst_env
conda create -y -n $ENV_NAME python=3.11
conda activate $ENV_NAME
pip install apsbits
```

### Install the TST instrument package

```bash
cd /path/to/tst-nsls-bits
pip install -e .
```

## Usage

### IPython Console with Profile

The recommended way to use the TST instrument is through a dedicated IPython profile:

```bash
# Create TST-specific profile
ipython profile create tst-nsls --ipython-dir="~/.ipython"

# Start TST session
conda activate BITS_tst_env
ipython --profile=tst-nsls
```

### Direct Import

Alternatively, you can import directly:

```python
from tst_instrument.startup import *
```

### Basic Usage

```python
# Check available devices
listobjects()

# Run simulation plans
RE(sim_print_plan())
RE(sim_count_plan())

# Run TST-specific plans (after device configuration)
RE(tomo_demo_async([manta1], panda1, num_images=21))
```

## Device Configuration

The TST beamline includes:
- **Rotation Motor**: `rot_motor` - Sample rotation stage
- **Manta Cameras**: `manta1`, `manta2` - Imaging detectors
- **PandA**: `panda1` - Trigger and coordination box
- **Flyers**: Coordinated acquisition between devices

## Queue Server

Start the queue server:

```bash
./src/tst_instrument_qserver/qs_host.sh restart
```

Monitor with the GUI:

```bash
queue-monitor &
```

## Plans

### Tomography Plans
- `tomo_demo_async()` - Tomography data collection
- `_manta_collect_dark_flat()` - Dark and flat field collection

### XAS Plans  
- `xas_demo_async()` - X-ray absorption spectroscopy scanning

### Simulation Plans
- `sim_print_plan()` - Basic test plan
- `sim_count_plan()` - Counting simulation
- `sim_rel_scan_plan()` - Relative scan simulation

## Configuration Files

- `configs/iconfig.yml` - Main instrument configuration
- `configs/devices.yml` - Device definitions and parameters
- `configs/extra_logging.yml` - Custom logging configuration

## Development

For development and testing:

```bash
pip install -e ".[dev]"
```

## Documentation

For detailed BITS documentation, see: https://bcda-aps.github.io/BITS/

## Support

For issues and questions:
- BITS Framework: https://github.com/BCDA-APS/BITS/issues
- TST Beamline: Contact beamline staff