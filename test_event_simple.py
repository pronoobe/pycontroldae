"""
Simple test to debug event system
"""

import sys
sys.path.insert(0, '.')

from pycontroldae.blocks import Constant, Gain
from pycontroldae.core import System, Simulator, at_time

print("Testing event system...")

# Create simple system
input_src = Constant(name="input", value=1.0)
amp = Gain(name="amp", K=2.0)

# Build modules first
input_src.build()
amp.build()

# Create system
sys1 = System("test")
sys1.add_module(input_src)
sys1.add_module(amp)

# Manual connection
sys1.connect("input.signal ~ amp.input")

print(f"System: {sys1}")
print(f"Modules: {sys1.modules}")
print(f"Connections: {sys1.connections}")

# Add event
def change_gain(integrator):
    print("Event triggered!")
    return {"amp.K": 5.0}

sys1.add_event(at_time(2.0, change_gain))

print(f"Events: {sys1.events}")

# Compile
print("Compiling...")
sys1.compile()

print("Simulating...")
sim = Simulator(sys1)
times, values = sim.run(t_span=(0.0, 4.0), dt=0.1)

print(f"Success! Final output: {values[-1, -1]}")
