"""
Simple test script for backend.py

This script tests the Julia backend initialization and verifies that
ModelingToolkit and DifferentialEquations are properly loaded.
"""

import sys
sys.path.insert(0, '.')

from pycontroldae.core.backend import get_jl

print("=" * 60)
print("Testing pycontroldae Julia Backend")
print("=" * 60)
print()

# Test 1: Initialize Julia backend
print("Test 1: Initializing Julia backend...")
try:
    jl = get_jl()
    print("[PASS] Julia backend initialized successfully\n")
except Exception as e:
    print(f"[FAIL] Failed to initialize Julia backend: {e}\n")
    sys.exit(1)

# Test 2: Verify ModelingToolkit is loaded
print("Test 2: Verifying ModelingToolkit.jl is available...")
try:
    result = jl.seval("isdefined(Main, :ModelingToolkit)")
    if result:
        print("[PASS] ModelingToolkit is loaded\n")
    else:
        print("[FAIL] ModelingToolkit is not available\n")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] Error checking ModelingToolkit: {e}\n")
    sys.exit(1)

# Test 3: Verify DifferentialEquations is loaded
print("Test 3: Verifying DifferentialEquations.jl is available...")
try:
    result = jl.seval("isdefined(Main, :DifferentialEquations)")
    if result:
        print("[PASS] DifferentialEquations is loaded\n")
    else:
        print("[FAIL] DifferentialEquations is not available\n")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] Error checking DifferentialEquations: {e}\n")
    sys.exit(1)

# Test 4: Verify symbolic operators (t, D) are available
print("Test 4: Verifying symbolic operators (t, D) are available...")
try:
    t_defined = jl.seval("isdefined(Main, :t)")
    D_defined = jl.seval("isdefined(Main, :D)")
    if t_defined and D_defined:
        print("[PASS] Symbolic operators (t, D) are available\n")
    else:
        print(f"[FAIL] Symbolic operators missing: t={t_defined}, D={D_defined}\n")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] Error checking symbolic operators: {e}\n")
    sys.exit(1)

# Test 5: Create a simple symbolic variable
print("Test 5: Creating a simple symbolic variable...")
try:
    jl.seval("@variables x")
    print("[PASS] Successfully created symbolic variable\n")
except Exception as e:
    print(f"[FAIL] Failed to create symbolic variable: {e}\n")
    sys.exit(1)

# Test 6: Test singleton behavior
print("Test 6: Testing singleton pattern...")
try:
    jl2 = get_jl()
    if jl is jl2:
        print("[PASS] Singleton pattern working correctly\n")
    else:
        print("[FAIL] Multiple Julia instances created\n")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] Error testing singleton: {e}\n")
    sys.exit(1)

print("=" * 60)
print("All tests passed! Julia backend is working correctly.")
print("=" * 60)
