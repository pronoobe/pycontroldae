"""
Test script for Simulator class

This script tests the implementation of core/simulator.py to ensure it can:
1. Create an ODEProblem from a compiled system
2. Solve using Julia's solve() with Rodas5
3. Convert Julia Solution to Python numpy arrays
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from pycontroldae.core.module import Module
from pycontroldae.core.system import System
from pycontroldae.core.simulator import Simulator

print("=" * 60)
print("Testing pycontroldae Simulator Class")
print("=" * 60)
print()

# Test 1: Create a simple exponential decay system
print("Test 1: Creating simple exponential decay system...")
try:
    # dx/dt = -a*x, x(0) = 1.0, a = 1.0
    # Analytical solution: x(t) = exp(-t)
    decay = Module("decay")
    decay.add_state("x", 1.0)
    decay.add_param("a", 1.0)
    decay.add_equation("D(x) ~ -a*x")

    sys1 = System("decay_system")
    sys1.add_module(decay)
    sys1.compile()

    print(f"[PASS] System created and compiled: {sys1}\n")
except Exception as e:
    print(f"[FAIL] Failed to create system: {e}\n")
    sys.exit(1)

# Test 2: Create simulator
print("Test 2: Creating Simulator...")
try:
    sim1 = Simulator(sys1)
    print(f"[PASS] Simulator created: {sim1}\n")
except Exception as e:
    print(f"[FAIL] Failed to create simulator: {e}\n")
    sys.exit(1)

# Test 3: Run simulation with default parameters
print("Test 3: Running simulation (t=0 to t=5)...")
try:
    times, values = sim1.run(t_span=(0.0, 5.0), dt=0.1)
    print(f"[PASS] Simulation completed")
    print(f"       Time points: {len(times)}")
    print(f"       Values shape: {values.shape}")
    print(f"       Initial value: {values[0, 0]:.4f}")
    print(f"       Final value: {values[-1, 0]:.4f}")
    print(f"       Expected final: {np.exp(-5.0):.4f}\n")
except Exception as e:
    print(f"[FAIL] Failed to run simulation: {e}\n")
    sys.exit(1)

# Test 4: Verify solution accuracy (exponential decay)
print("Test 4: Verifying solution accuracy...")
try:
    # Analytical solution: x(t) = exp(-t)
    expected = np.exp(-times)
    error = np.abs(values[:, 0] - expected)
    max_error = np.max(error)

    if max_error < 1e-3:
        print(f"[PASS] Solution is accurate (max error: {max_error:.2e})\n")
    else:
        print(f"[FAIL] Solution has large error (max error: {max_error:.2e})\n")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] Failed to verify accuracy: {e}\n")
    sys.exit(1)

# Test 5: Run with custom initial conditions
print("Test 5: Running with custom initial conditions...")
try:
    times2, values2 = sim1.run(
        t_span=(0.0, 5.0),
        u0={"decay.x": 2.0},  # Start at x=2
        dt=0.1
    )
    print(f"[PASS] Simulation with custom u0 completed")
    print(f"       Initial value: {values2[0, 0]:.4f} (expected: 2.0)")
    print(f"       Final value: {values2[-1, 0]:.4f}")
    print(f"       Expected final: {2.0 * np.exp(-5.0):.4f}\n")
except Exception as e:
    print(f"[FAIL] Failed with custom u0: {e}\n")
    sys.exit(1)

# Test 6: Run with custom parameters
print("Test 6: Running with custom parameters...")
try:
    times3, values3 = sim1.run(
        t_span=(0.0, 5.0),
        params={"decay.a": 2.0},  # Faster decay
        dt=0.1
    )
    print(f"[PASS] Simulation with custom params completed")
    print(f"       Final value: {values3[-1, 0]:.4f}")
    print(f"       Expected final: {np.exp(-2.0 * 5.0):.4f}\n")
except Exception as e:
    print(f"[FAIL] Failed with custom params: {e}\n")
    sys.exit(1)

# Test 7: Create RC circuit system and simulate
print("Test 7: Creating and simulating RC circuit...")
try:
    rc = Module("rc")
    rc.add_state("V", 0.0)      # Voltage starts at 0
    rc.add_state("I", 1.0)      # Current input = 1A
    rc.add_param("R", 1000.0)   # 1kΩ
    rc.add_param("C", 1e-6)     # 1μF
    rc.add_equation("D(V) ~ (I - V/R)/C")

    input_mod = Module("input")
    input_mod.add_state("signal", 1.0)
    input_mod.add_equation("D(signal) ~ 0")

    sys2 = System("rc_system")
    sys2.add_module(rc)
    sys2.add_module(input_mod)
    sys2.connect("input.signal ~ rc.I")
    sys2.compile()

    sim2 = Simulator(sys2)
    times_rc, values_rc = sim2.run(t_span=(0.0, 0.01), dt=0.0001)

    print(f"[PASS] RC circuit simulation completed")
    print(f"       Time points: {len(times_rc)}")
    print(f"       States: {values_rc.shape[1]}")
    print(f"       Initial voltage: {values_rc[0, 0]:.4f}V")
    print(f"       Final voltage: {values_rc[-1, 0]:.4f}V\n")
except Exception as e:
    print(f"[FAIL] Failed RC circuit simulation: {e}\n")
    sys.exit(1)

# Test 8: Test run_to_dict method
print("Test 8: Testing run_to_dict method...")
try:
    result_dict = sim1.run_to_dict(t_span=(0.0, 5.0), dt=0.5)

    print(f"[PASS] run_to_dict completed")
    print(f"       Keys: {list(result_dict.keys())}")
    print(f"       Time points: {len(result_dict['t'])}")
    for key in result_dict:
        if key != 't':
            print(f"       {key}: shape {result_dict[key].shape}\n")
except Exception as e:
    print(f"[FAIL] Failed run_to_dict: {e}\n")
    sys.exit(1)

# Test 9: Test error handling - uncompiled system
print("Test 9: Testing error handling (uncompiled system)...")
try:
    bad_sys = System("bad")
    bad_mod = Module("m").add_state("x").add_equation("D(x) ~ 0")
    bad_sys.add_module(bad_mod)
    # Don't compile!

    sim_bad = Simulator(bad_sys)
    print(f"[FAIL] Should have raised error for uncompiled system\n")
    sys.exit(1)
except RuntimeError as e:
    print(f"[PASS] Correctly raised RuntimeError: {str(e)[:60]}...\n")
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}\n")
    sys.exit(1)

# Test 10: Test error handling - invalid t_span
print("Test 10: Testing error handling (invalid t_span)...")
try:
    times_bad, values_bad = sim1.run(t_span=(5.0, 0.0))  # t_start > t_end
    print(f"[FAIL] Should have raised error for invalid t_span\n")
    sys.exit(1)
except ValueError as e:
    print(f"[PASS] Correctly raised ValueError: {str(e)[:60]}...\n")
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}\n")
    sys.exit(1)

print("=" * 60)
print("All Simulator tests passed!")
print("=" * 60)
print()
print("Summary:")
print("  - Simulator creation: [OK]")
print("  - run() method: [OK] Returns (times, values) numpy arrays")
print("  - Custom initial conditions: [OK]")
print("  - Custom parameters: [OK]")
print("  - Solution accuracy: [OK] Matches analytical solution")
print("  - RC circuit simulation: [OK]")
print("  - run_to_dict() method: [OK] Returns dict with named states")
print("  - Error handling: [OK] Validates inputs")
print()
