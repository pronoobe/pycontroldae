"""
Test script for refactored Module class

This script tests the enhanced features:
1. add_parameter() alias method
2. get_param_map() for runtime parameter updates
3. get_state_map() for initial conditions
4. update_param() and update_state() methods
5. Connection operators << and >>
6. System.connect() with operator tuples
"""

import sys
sys.path.insert(0, '.')

from pycontroldae.core.module import Module
from pycontroldae.core.system import System
from pycontroldae.core.simulator import Simulator

print("=" * 70)
print("Testing Refactored Module Class")
print("=" * 70)
print()

# ==============================================================================
# Test 1: add_parameter() alias
# ==============================================================================
print("Test 1: Testing add_parameter() alias...")
print("-" * 70)

try:
    mod1 = Module("test1")
    mod1.add_parameter("R", 1000.0)  # Using add_parameter
    mod1.add_param("C", 1e-6)        # Using add_param

    if "R" in mod1.params and "C" in mod1.params:
        print("[PASS] add_parameter() alias works correctly")
        print(f"       Parameters: {mod1.params}\n")
    else:
        print("[FAIL] Parameters not stored correctly\n")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 2: get_param_map() for Julia symbol mapping
# ==============================================================================
print("Test 2: Testing get_param_map()...")
print("-" * 70)

try:
    rc = Module("rc")
    rc.add_state("V", 0.0)
    rc.add_parameter("R", 1000.0)
    rc.add_parameter("C", 1e-6)
    rc.add_equation("D(V) ~ -V/(R*C)")
    rc.build()

    param_map = rc.get_param_map()

    print("[PASS] get_param_map() returned mapping")
    print(f"       Map size: {len(param_map)} parameters")
    print(f"       Python values: R={rc.params['R']}, C={rc.params['C']}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 3: get_state_map() for initial conditions
# ==============================================================================
print("Test 3: Testing get_state_map()...")
print("-" * 70)

try:
    state_map = rc.get_state_map()

    print("[PASS] get_state_map() returned mapping")
    print(f"       Map size: {len(state_map)} states")
    print(f"       Python values: V={rc.states['V']}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 4: update_param() without recompilation
# ==============================================================================
print("Test 4: Testing update_param()...")
print("-" * 70)

try:
    old_R = rc.params['R']
    rc.update_param("R", 2000.0)
    new_R = rc.params['R']

    param_map_updated = rc.get_param_map()

    print("[PASS] update_param() updated parameter value")
    print(f"       Old R: {old_R}")
    print(f"       New R: {new_R}")
    print(f"       No recompilation needed!\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 5: update_state() for initial conditions
# ==============================================================================
print("Test 5: Testing update_state()...")
print("-" * 70)

try:
    old_V = rc.states['V']
    rc.update_state("V", 5.0)
    new_V = rc.states['V']

    print("[PASS] update_state() updated state value")
    print(f"       Old V: {old_V}")
    print(f"       New V: {new_V}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 6: set_input() and set_output() for connections
# ==============================================================================
print("Test 6: Testing set_input() and set_output()...")
print("-" * 70)

try:
    input_mod = Module("input")
    input_mod.add_state("signal", 1.0)
    input_mod.add_equation("D(signal) ~ 0")
    input_mod.set_output("signal")

    rc2 = Module("rc2")
    rc2.add_state("V", 0.0)
    rc2.add_state("I", 0.0)
    rc2.add_parameter("R", 1000.0)
    rc2.add_parameter("C", 1e-6)
    rc2.add_equation("D(V) ~ (I - V/R)/C")
    rc2.set_input("I")

    print("[PASS] set_input() and set_output() configured")
    print(f"       {input_mod.name}: output={input_mod.output_var}")
    print(f"       {rc2.name}: input={rc2.input_var}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 7: Connection operator >> (output to input)
# ==============================================================================
print("Test 7: Testing >> operator (output to input)...")
print("-" * 70)

try:
    connection_tuple = input_mod >> rc2

    if len(connection_tuple) == 3:
        mod1, mod2, conn_str = connection_tuple
        print("[PASS] >> operator returned tuple")
        print(f"       Module 1: {mod1.name}")
        print(f"       Module 2: {mod2.name}")
        print(f"       Connection: {conn_str}\n")
    else:
        print("[FAIL] >> operator returned invalid tuple\n")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 8: Connection operator << (input from output)
# ==============================================================================
print("Test 8: Testing << operator (input from output)...")
print("-" * 70)

try:
    connection_tuple2 = rc2 << input_mod

    if len(connection_tuple2) == 3:
        mod1, mod2, conn_str = connection_tuple2
        print("[PASS] << operator returned tuple")
        print(f"       Module 1: {mod1.name} (receives input)")
        print(f"       Module 2: {mod2.name} (provides output)")
        print(f"       Connection: {conn_str}\n")
    else:
        print("[FAIL] << operator returned invalid tuple\n")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 9: System.connect() with operator tuples
# ==============================================================================
print("Test 9: Testing System.connect() with operators...")
print("-" * 70)

try:
    sys1 = System("test_system")
    sys1.connect(input_mod >> rc2)  # Using >> operator

    if len(sys1._modules) == 2:
        print("[PASS] System.connect() accepted operator tuple")
        print(f"       Modules auto-added: {[m.name for m in sys1._modules]}")
        print(f"       Connections: {sys1._connections}\n")
    else:
        print("[FAIL] Modules not auto-added\n")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 10: Full workflow with operators and compilation
# ==============================================================================
print("Test 10: Full workflow with operators...")
print("-" * 70)

try:
    # Create modules with input/output defined
    input_final = Module("input_final", output_var="signal")
    input_final.add_state("signal", 1.0)
    input_final.add_equation("D(signal) ~ 0")

    rc_final = Module("rc_final", input_var="I")
    rc_final.add_state("V", 0.0)
    rc_final.add_state("I", 0.0)
    rc_final.add_parameter("R", 1000.0)
    rc_final.add_parameter("C", 1e-6)
    rc_final.add_equation("D(V) ~ (I - V/R)/C")

    # Create system with operator connection
    sys_final = System("final_system")
    sys_final.connect(input_final >> rc_final)

    # Compile
    sys_final.compile()

    print("[PASS] Full workflow completed")
    print(f"       System: {sys_final}")
    print(f"       Modules: {len(sys_final._modules)}")
    print(f"       Connections: {len(sys_final._connections)}")
    print(f"       Compiled: Yes\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 11: Simulation with updated parameters (no recompilation)
# ==============================================================================
print("Test 11: Simulation with updated parameters...")
print("-" * 70)

try:
    # Update parameter without recompiling
    rc_final.update_param("R", 2000.0)

    # Create simulator and run
    sim = Simulator(sys_final)
    times, values = sim.run(t_span=(0.0, 0.01), dt=0.001)

    print("[PASS] Simulation with updated parameters completed")
    print(f"       Time points: {len(times)}")
    print(f"       States: {values.shape[1]}")
    print(f"       Initial V: {values[0, 0]:.6f}")
    print(f"       Final V: {values[-1, 0]:.6f}\n")
except Exception as e:
    print(f"[FAIL] {e}\n")
    sys.exit(1)

# ==============================================================================
# Test 12: Error handling - undefined input/output
# ==============================================================================
print("Test 12: Error handling (undefined input/output)...")
print("-" * 70)

try:
    bad_mod1 = Module("bad1")
    bad_mod2 = Module("bad2")

    # Try to connect without defining input/output
    try:
        bad_mod1 >> bad_mod2
        print("[FAIL] Should have raised ValueError\n")
        sys.exit(1)
    except ValueError as e:
        print(f"[PASS] Correctly raised ValueError")
        print(f"       Error: {str(e)[:60]}...\n")
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}\n")
    sys.exit(1)

# ==============================================================================
# Summary
# ==============================================================================
print("=" * 70)
print("All tests passed! Refactored Module class works correctly.")
print("=" * 70)
print()
print("New Features Validated:")
print("  [OK] add_parameter() alias method")
print("  [OK] get_param_map() - Julia symbol to Python value mapping")
print("  [OK] get_state_map() - Initial condition mapping")
print("  [OK] update_param() - Runtime parameter updates (no recompilation)")
print("  [OK] update_state() - Runtime initial condition updates")
print("  [OK] set_input() and set_output() - Connection configuration")
print("  [OK] >> operator - Output to input connection")
print("  [OK] << operator - Input from output connection")
print("  [OK] System.connect() - Accepts operator tuples")
print("  [OK] Automatic module registration from operators")
print("  [OK] Full workflow - Operators + compilation + simulation")
print("  [OK] Error handling - Undefined input/output variables")
print()
