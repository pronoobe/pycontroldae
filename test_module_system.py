"""
Test script for Module and System classes

This script tests the implementation of core/module.py and core/system.py
to ensure they correctly create Julia ODESystems and apply structural_simplify.
"""

import sys
sys.path.insert(0, '.')

from pycontroldae.core.module import Module
from pycontroldae.core.system import System

print("=" * 60)
print("Testing pycontroldae Module and System Classes")
print("=" * 60)
print()

# Test 1: Create a simple module
print("Test 1: Creating a simple module...")
try:
    simple_mod = Module("simple")
    simple_mod.add_state("x", 0.0)
    simple_mod.add_param("a", 1.0)
    simple_mod.add_equation("D(x) ~ -a*x")
    print(f"[PASS] Module created: {simple_mod}\n")
except Exception as e:
    print(f"[FAIL] Failed to create module: {e}\n")
    sys.exit(1)

# Test 2: Build the simple module
print("Test 2: Building the simple module...")
try:
    julia_sys = simple_mod.build()
    print(f"[PASS] Module built successfully")
    # Skip printing Julia object due to potential encoding issues on Windows
    print(f"       Julia system type: {type(julia_sys).__name__}\n")
except Exception as e:
    print(f"[FAIL] Failed to build module: {e}\n")
    sys.exit(1)

# Test 3: Create an RC circuit module
print("Test 3: Creating RC circuit module...")
try:
    rc = Module("rc_circuit")
    rc.add_state("V", 0.0)      # Voltage across capacitor
    rc.add_state("I", 0.0)      # Input current
    rc.add_param("R", 1000.0)   # Resistance in Ohms
    rc.add_param("C", 1e-6)     # Capacitance in Farads
    rc.add_equation("D(V) ~ (I - V/R)/C")
    print(f"[PASS] RC module created: {rc}\n")
except Exception as e:
    print(f"[FAIL] Failed to create RC module: {e}\n")
    sys.exit(1)

# Test 4: Create an input source module
print("Test 4: Creating input source module...")
try:
    input_src = Module("input_source")
    input_src.add_state("signal", 0.0)
    input_src.add_equation("D(signal) ~ 0")  # Constant signal
    print(f"[PASS] Input module created: {input_src}\n")
except Exception as e:
    print(f"[FAIL] Failed to create input module: {e}\n")
    sys.exit(1)

# Test 5: Create a system with single module (no connections)
print("Test 5: Creating system with single module...")
try:
    sys1 = System("single_module_system")
    sys1.add_module(simple_mod)
    print(f"[PASS] System created: {sys1}\n")
except Exception as e:
    print(f"[FAIL] Failed to create system: {e}\n")
    sys.exit(1)

# Test 6: Compile the single module system
print("Test 6: Compiling single module system...")
try:
    compiled1 = sys1.compile()
    print(f"[PASS] System compiled successfully")
    # Skip printing Julia object due to potential encoding issues on Windows
    print(f"       Compiled system type: {type(compiled1).__name__}\n")
except Exception as e:
    print(f"[FAIL] Failed to compile system: {e}\n")
    sys.exit(1)

# Test 7: Create a system with multiple modules and connections
print("Test 7: Creating system with connections...")
try:
    sys2 = System("connected_system")
    sys2.add_module(rc)
    sys2.add_module(input_src)
    sys2.connect("input_source.signal ~ rc_circuit.I")
    print(f"[PASS] Connected system created: {sys2}\n")
except Exception as e:
    print(f"[FAIL] Failed to create connected system: {e}\n")
    sys.exit(1)

# Test 8: Compile the connected system (with structural_simplify)
print("Test 8: Compiling connected system with structural_simplify...")
try:
    compiled2 = sys2.compile()
    print(f"[PASS] Connected system compiled successfully")
    # Skip printing Julia object due to potential encoding issues on Windows
    print(f"       Compiled system type: {type(compiled2).__name__}\n")
except Exception as e:
    print(f"[FAIL] Failed to compile connected system: {e}\n")
    sys.exit(1)

# Test 9: Test method chaining
print("Test 9: Testing method chaining...")
try:
    chained = (Module("chained")
               .add_state("y", 0.0)
               .add_param("b", 2.0)
               .add_equation("D(y) ~ -b*y"))
    chained_sys = chained.build()
    print(f"[PASS] Method chaining works: {chained}\n")
except Exception as e:
    print(f"[FAIL] Method chaining failed: {e}\n")
    sys.exit(1)

# Test 10: Test error handling - module with no states
print("Test 10: Testing error handling (no states)...")
try:
    bad_mod = Module("bad")
    bad_mod.add_equation("D(x) ~ 0")
    bad_mod.build()
    print(f"[FAIL] Should have raised ValueError for module with no states\n")
    sys.exit(1)
except ValueError as e:
    print(f"[PASS] Correctly raised ValueError: {e}\n")
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}\n")
    sys.exit(1)

# Test 11: Test error handling - module with no equations
print("Test 11: Testing error handling (no equations)...")
try:
    bad_mod2 = Module("bad2")
    bad_mod2.add_state("x", 0.0)
    bad_mod2.build()
    print(f"[FAIL] Should have raised ValueError for module with no equations\n")
    sys.exit(1)
except ValueError as e:
    print(f"[PASS] Correctly raised ValueError: {e}\n")
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}\n")
    sys.exit(1)

# Test 12: Test error handling - system with no modules
print("Test 12: Testing error handling (no modules)...")
try:
    empty_sys = System("empty")
    empty_sys.compile()
    print(f"[FAIL] Should have raised ValueError for system with no modules\n")
    sys.exit(1)
except ValueError as e:
    print(f"[PASS] Correctly raised ValueError: {e}\n")
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}\n")
    sys.exit(1)

print("=" * 60)
print("All tests passed! Module and System classes work correctly.")
print("=" * 60)
print()
print("Summary:")
print(f"  - Module class: [OK] States, Parameters, Equations")
print(f"  - Module.build(): [OK] Creates Julia ODESystem")
print(f"  - System class: [OK] Multiple modules, Connections")
print(f"  - System.compile(): [OK] structural_simplify applied")
print(f"  - Error handling: [OK] Proper validation")
print(f"  - Method chaining: [OK] Fluent API")
print()
