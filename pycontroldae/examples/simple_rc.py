"""
Simple RC Circuit Example

This example demonstrates how to use pycontroldae to create a simple RC circuit
with an input source and compile it with structural_simplify.
"""

import sys
sys.path.insert(0, '.')

from pycontroldae.core.module import Module
from pycontroldae.core.system import System

print("=" * 60)
print("RC Circuit Example - pycontroldae")
print("=" * 60)
print()

# Define RC circuit module
print("Creating RC circuit module...")
rc = Module("rc_circuit")
rc.add_state("V", 0.0)      # Voltage across capacitor (V)
rc.add_state("I", 0.0)      # Input current (A)
rc.add_param("R", 1000.0)   # Resistance (Ohms)
rc.add_param("C", 1e-6)     # Capacitance (Farads)
rc.add_equation("D(V) ~ (I - V/R)/C")
print(f"  {rc}")
print()

# Define input source module
print("Creating input source module...")
input_src = Module("input_source")
input_src.add_state("signal", 1.0)  # Step input (1V)
input_src.add_equation("D(signal) ~ 0")  # Constant signal
print(f"  {input_src}")
print()

# Create system
print("Creating system...")
system = System("rc_system")
system.add_module(rc)
system.add_module(input_src)
system.connect("input_source.signal ~ rc_circuit.I")
print(f"  {system}")
print()

# Compile with structural_simplify
print("Compiling system (applying structural_simplify for DAE index reduction)...")
simplified_system = system.compile()
print(f"  Compiled successfully!")
print(f"  Type: {type(simplified_system).__name__}")
print()

print("=" * 60)
print("RC Circuit Example Complete!")
print("=" * 60)
print()
print("Key Features Demonstrated:")
print("  1. Module creation with states and parameters")
print("  2. Adding differential equations")
print("  3. Composing multiple modules into a system")
print("  4. Connecting module variables")
print("  5. Compiling with structural_simplify (DAE index reduction)")
print()
