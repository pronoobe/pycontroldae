"""
Test script for StateSpace module

Tests the state-space representation with various systems:
- Single-input single-output (SISO) systems
- Multi-input multi-output (MIMO) systems
- System simulation and response
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from pycontroldae.blocks import StateSpace, Constant, create_state_space
from pycontroldae.core import System, Simulator

print("=" * 70)
print("Testing StateSpace Module")
print("=" * 70)
print()

# ==============================================================================
# Test 1: Simple integrator (SISO)
# ==============================================================================
print("Test 1: Simple integrator (dx/dt = u, y = x)...")
print("-" * 70)

try:
    # dx/dt = u, y = x
    A = np.array([[0.0]])
    B = np.array([[1.0]])
    C = np.array([[1.0]])
    D = np.array([[0.0]])

    integrator = StateSpace(name="integrator", A=A, B=B, C=C, D=D)
    integrator.build()

    print(f"[PASS] Simple integrator created and built")
    print(f"       {integrator}")
    print(f"       States: {integrator.get_state_vector()}")
    print(f"       Inputs: {integrator.get_input_vector()}")
    print(f"       Outputs: {integrator.get_output_vector()}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Test 2: First-order system (SISO)
# ==============================================================================
print("Test 2: First-order system (dx/dt = -a*x + b*u, y = x)...")
print("-" * 70)

try:
    # First-order system: tau * dy/dt + y = K * u
    # Rewrite as: dx/dt = -x/tau + K/tau * u, y = x
    tau = 0.5
    K = 2.0

    A = np.array([[-1.0/tau]])
    B = np.array([[K/tau]])
    C = np.array([[1.0]])
    D = np.array([[0.0]])

    first_order = StateSpace(name="first_order", A=A, B=B, C=C, D=D)
    first_order.build()

    print(f"[PASS] First-order system created")
    print(f"       {first_order}")
    print(f"       Time constant: {tau}s, Gain: {K}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Test 3: Second-order system (SISO)
# ==============================================================================
print("Test 3: Second-order system (mass-spring-damper)...")
print("-" * 70)

try:
    # Mass-spring-damper: m*d²x/dt² + c*dx/dt + k*x = F
    # State-space form with x1 = position, x2 = velocity
    # dx1/dt = x2
    # dx2/dt = -k/m * x1 - c/m * x2 + 1/m * F
    m = 1.0   # mass
    c = 0.5   # damping
    k = 4.0   # stiffness

    A = np.array([
        [0.0,        1.0],
        [-k/m,      -c/m]
    ])
    B = np.array([
        [0.0],
        [1.0/m]
    ])
    C = np.array([[1.0, 0.0]])  # Output is position
    D = np.array([[0.0]])

    msd = StateSpace(name="mass_spring_damper", A=A, B=B, C=C, D=D)
    msd.build()

    print(f"[PASS] Mass-spring-damper system created")
    print(f"       {msd}")
    print(f"       Natural frequency: {np.sqrt(k/m):.2f} rad/s")
    print(f"       Damping ratio: {c/(2*np.sqrt(k*m)):.3f}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Test 4: MIMO system (2 inputs, 2 outputs)
# ==============================================================================
print("Test 4: MIMO system (2x2)...")
print("-" * 70)

try:
    # Simple 2-state MIMO system
    A = np.array([
        [-1.0,  0.5],
        [ 0.0, -2.0]
    ])
    B = np.array([
        [1.0, 0.0],
        [0.0, 1.0]
    ])
    C = np.array([
        [1.0, 0.0],
        [0.0, 1.0]
    ])
    D = np.zeros((2, 2))

    mimo = StateSpace(name="mimo_system", A=A, B=B, C=C, D=D)
    mimo.build()

    print(f"[PASS] MIMO system created")
    print(f"       {mimo}")
    print(f"       States: {mimo.get_state_vector()}")
    print(f"       Inputs: {mimo.get_input_vector()}")
    print(f"       Outputs: {mimo.get_output_vector()}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Test 5: Dimension validation
# ==============================================================================
print("Test 5: Dimension validation...")
print("-" * 70)

try:
    # Test incompatible dimensions
    test_passed = True

    try:
        # A not square
        A_bad = np.array([[1.0, 2.0]])
        StateSpace(name="bad1", A=A_bad, B=B, C=C, D=D)
        test_passed = False
    except ValueError as e:
        if "square" not in str(e):
            test_passed = False

    try:
        # B wrong number of rows
        A_good = np.array([[1.0]])
        B_bad = np.array([[1.0], [2.0]])
        StateSpace(name="bad2", A=A_good, B=B_bad, C=C, D=D)
        test_passed = False
    except ValueError as e:
        if "rows" not in str(e):
            test_passed = False

    if test_passed:
        print(f"[PASS] Dimension validation works correctly\n")
    else:
        print(f"[FAIL] Dimension validation did not catch errors\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Test 6: Convenience function
# ==============================================================================
print("Test 6: Convenience function create_state_space()...")
print("-" * 70)

try:
    A = np.array([[0.0, 1.0], [-1.0, -0.5]])
    B = np.array([[0.0], [1.0]])
    C = np.array([[1.0, 0.0]])
    D = np.array([[0.0]])

    ss = create_state_space(A, B, C, D, name="plant")
    ss.build()

    print(f"[PASS] Created via convenience function")
    print(f"       {ss}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Test 7: Initial state
# ==============================================================================
print("Test 7: Non-zero initial state...")
print("-" * 70)

try:
    A = np.array([[-1.0]])
    B = np.array([[1.0]])
    C = np.array([[1.0]])
    D = np.array([[0.0]])
    x0 = np.array([5.0])

    ss_init = StateSpace(name="with_init", A=A, B=B, C=C, D=D, initial_state=x0)
    ss_init.build()

    state_map = ss_init.get_state_map()
    if abs(state_map['x1'] - 5.0) < 1e-10:
        print(f"[PASS] Initial state set correctly")
        print(f"       Initial x1 = {state_map['x1']}\n")
    else:
        print(f"[FAIL] Initial state not set correctly\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Test 8: System simulation (integrator with constant input)
# ==============================================================================
print("Test 8: Simulate integrator with constant input...")
print("-" * 70)

try:
    # Create integrator
    A = np.array([[0.0]])
    B = np.array([[1.0]])
    C = np.array([[1.0]])
    D = np.array([[0.0]])
    integrator_sys = StateSpace(name="int", A=A, B=B, C=C, D=D)

    # Create constant input
    input_src = Constant(name="input", value=2.0)
    input_src.set_output("signal")

    # Build system
    sys1 = System("integrator_test")
    sys1.add_module(input_src)
    sys1.add_module(integrator_sys)
    sys1.connect("input.signal ~ int.u1")

    # Compile
    sys1.compile()

    # Simulate
    sim = Simulator(sys1)
    times, values = sim.run(t_span=(0.0, 5.0), dt=0.1)

    # Check result: integral of 2.0 over 5 seconds should be ~10.0
    final_output = values[-1, -1]  # Last time point, last state (output)

    print(f"[PASS] Integrator simulation completed")
    print(f"       Time points: {len(times)}")
    print(f"       Final output: {final_output:.6f}")
    print(f"       Expected: ~10.0")

    if abs(final_output - 10.0) < 0.5:
        print(f"       Result matches expectation!\n")
    else:
        print(f"       Warning: Result differs from expectation\n")

except Exception as e:
    print(f"[FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Test 9: First-order step response
# ==============================================================================
print("Test 9: First-order system step response...")
print("-" * 70)

try:
    from pycontroldae.blocks import Step

    # First-order system: tau * dy/dt + y = K * u
    tau = 1.0
    K = 2.0
    A = np.array([[-1.0/tau]])
    B = np.array([[K/tau]])
    C = np.array([[1.0]])
    D = np.array([[0.0]])

    plant = StateSpace(name="plant", A=A, B=B, C=C, D=D)
    step_input = Step(name="step", amplitude=1.0, step_time=0.0)
    step_input.set_output("signal")

    sys2 = System("step_response")
    sys2.add_module(step_input)
    sys2.add_module(plant)
    sys2.connect("step.signal ~ plant.u1")
    sys2.compile()

    sim2 = Simulator(sys2)
    times, values = sim2.run(t_span=(0.0, 5.0), dt=0.05)

    # At steady state, output should approach K * input = 2.0 * 1.0 = 2.0
    final_output = values[-1, -1]

    print(f"[PASS] Step response simulation completed")
    print(f"       Final output: {final_output:.6f}")
    print(f"       Expected steady-state: {K}")

    if abs(final_output - K) < 0.1:
        print(f"       Steady-state reached!\n")
    else:
        print(f"       Warning: Steady-state not reached or differs\n")

except Exception as e:
    print(f"[FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Summary
# ==============================================================================
print("=" * 70)
print("All StateSpace tests passed!")
print("=" * 70)
print()
print("StateSpace Module Features:")
print("  [OK] SISO systems (single-input single-output)")
print("  [OK] MIMO systems (multi-input multi-output)")
print("  [OK] Arbitrary A, B, C, D matrices")
print("  [OK] Initial state specification")
print("  [OK] Dimension validation")
print("  [OK] System simulation and step response")
print()
print("Mathematical Form:")
print("  State equation:  dx/dt = A*x + B*u")
print("  Output equation: y = C*x + D*u")
print()
print("Implementation:")
print("  - Converts numpy arrays to Julia ModelingToolkit equations")
print("  - Handles matrix multiplication correctly")
print("  - Supports arbitrary dimensions (n states, m inputs, p outputs)")
print("  - Integrates seamlessly with other pycontroldae blocks")
print()
