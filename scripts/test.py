#!/usr/bin/env python3
"""
TST NSLS-II Test Script

Test script that demonstrates:
- Importing TST startup
- Listing all devices via oregistry
- Listing available plans
- Running mock plans
"""

import sys
import os

# Set mock mode for testing
os.environ["TST_MOCK_MODE"] = "YES"

print("=" * 80)
print("TST NSLS-II BITS Test Script")
print("=" * 80)

# Import the TST startup
print("\n1. Importing TST startup...")
try:
    from tst_instrument.startup import *
    print("✓ Successfully imported TST startup")
except Exception as e:
    print(f"✗ Error importing startup: {e}")
    sys.exit(1)

# List all devices from oregistry
print("\n2. Listing all devices from oregistry:")
print("-" * 40)
try:
    # Use oregistry.all_devices to get all devices
    all_devices = oregistry.all_devices
    device_list = [(device.name, device) for device in all_devices]
    
    print(f"Total devices found: {len(device_list)}")
    for device_name, device in device_list:
        device_type = type(device).__name__
        print(f"  - {device_name:<20} ({device_type})")
        
        # Show additional info for TST devices
        if hasattr(device, 'prefix'):
            print(f"    PV prefix: {device.prefix}")
except Exception as e:
    print(f"✗ Error listing devices: {e}")

# List available plans
print("\n3. Listing available plans:")
print("-" * 40)
try:
    # Get all available plans
    plan_names = []
    
    # Standard Bluesky plans
    from bluesky import plans as bp
    for attr_name in dir(bp):
        if not attr_name.startswith('_') and callable(getattr(bp, attr_name)):
            plan_names.append(f"bp.{attr_name}")
    
    # TST-specific plans
    tst_plans = [
        "sim_count_plan",
        "sim_print_plan", 
        "sim_rel_scan_plan",
        "tomo_demo_async",
        "xas_demo_async",
        "energy_calibration_plan",
    ]
    
    print(f"Standard Bluesky plans: {len(plan_names)}")
    print(f"TST-specific plans: {len(tst_plans)}")
    print("\nTST Plans:")
    for plan in tst_plans:
        print(f"  - {plan}")
except Exception as e:
    print(f"✗ Error listing plans: {e}")

# Run some mock plans
print("\n4. Running mock plans:")
print("-" * 40)

# Test 1: Simple print plan
print("\nTest 1: Running sim_print_plan...")
try:
    RE(sim_print_plan("Hello from TST BITS!"))
    print("✓ sim_print_plan completed successfully")
except Exception as e:
    print(f"✗ Error running sim_print_plan: {e}")

# Test 2: Count plan with simulated detector
print("\nTest 2: Running sim_count_plan...")
try:
    # Use the simulated detector
    sim_det = oregistry.find(name="sim_det")
    RE(sim_count_plan(sim_det, num=3))
    print("✓ sim_count_plan completed successfully")
except Exception as e:
    print(f"✗ Error running sim_count_plan: {e}")

# Test 3: Relative scan with simulated motor and detector
print("\nTest 3: Running sim_rel_scan_plan...")
try:
    sim_motor = oregistry.find(name="sim_motor")
    sim_det = oregistry.find(name="sim_det")
    RE(sim_rel_scan_plan(sim_det, sim_motor, -1, 1, 5))
    print("✓ sim_rel_scan_plan completed successfully")
except Exception as e:
    print(f"✗ Error running sim_rel_scan_plan: {e}")

# Test 4: Energy calibration plan (mock)
print("\nTest 4: Running energy_calibration_plan...")
try:
    energy_points = [8000, 8500, 9000, 9500, 10000]
    RE(energy_calibration_plan(energy_points, motor="rot_motor"))
    print("✓ energy_calibration_plan completed successfully")
except Exception as e:
    print(f"✗ Error running energy_calibration_plan: {e}")

# Show run engine state
print("\n5. Run Engine State:")
print("-" * 40)
try:
    print(f"Run Engine state: {RE.state}")
    print(f"Current run UID: {RE.md.get('scan_id', 'N/A')}")
    print(f"Metadata keys: {list(RE.md.keys())[:10]}...")  # Show first 10 keys
except Exception as e:
    print(f"✗ Error accessing RE state: {e}")

# Summary
print("\n" + "=" * 80)
print("TST BITS Test Script Complete!")
print("=" * 80)

# Check if running in interactive mode
if hasattr(sys, 'ps1'):
    print("\nYou are now in interactive mode. Available objects:")
    print("  - RE: Run Engine")
    print("  - oregistry: Device registry")
    print("  - All TST devices and plans")
    print("\nTry: RE(sim_count_plan(sim_det, num=5))")