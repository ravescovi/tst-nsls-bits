# TST Beamline Profile Collection

This `.profile/` directory contains references to the original TST profile collection startup files.

## Original Profile Collection

The original TST profile collection is available at:
- Repository: `nsls_deployments/tst-profile-collection/`
- Startup files: `nsls_deployments/tst-profile-collection/startup/`

## Key Files

### Original Startup Files:
- `00-startup.py` - Base startup configuration
- `03-providers.py` - Data providers setup
- `05-motors.py` - Motor device configurations
- `10-panda.py` - PandA box configuration
- `15-manta.py` - Manta camera setup
- `90-plans.py` - Bluesky plans
- `99-pvscan.py` - PV scanning utilities

### BITS Migration:
The BITS deployment has migrated these startup files into:
- Device configurations: `src/tst_instrument/configs/devices.yml`
- Device classes: `src/tst_instrument/devices/`
- Plan implementations: `src/tst_instrument/plans/`
- Startup script: `src/tst_instrument/startup.py`

## Usage

To reference the original profile collection:
```bash
# View original startup files
ls ../../../nsls_deployments/tst-profile-collection/startup/

# Compare with BITS implementation
ls src/tst_instrument/
```

## Testing

Both the original profile collection and BITS implementation can be tested:
- Original: Use the `startup/` files directly with IPython
- BITS: Use `test_devices.py`, `test_plans.py`, or `test.ipynb`
