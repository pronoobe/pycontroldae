"""
Minimal PID Test - Single Controller

Test if a single PID controller can be simulated.
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from pycontroldae.blocks import PID, Constant, Gain
from pycontroldae.core import System, Simulator

print("=" * 60)
print("Minimal PID Controller Test")
print("=" * 60)
print()

# Simple system: Setpoint -> Error Calc -> PID -> Plant
setpoint = Constant(name="sp", value=1.0)
setpoint.set_output("signal")

error_input = Constant(name="feedback", value=0.0)
error_input.set_output("signal")

pid = PID(name="pid", Kp=1.0, Ki=0.1, Kd=0.05)

plant = Gain(name="plant", K=1.0)

# Build
print("Building modules...")
setpoint.build()
error_input.build()
pid.build()
plant.build()
print("[OK] All modules built\n")

# Create system
print("Creating system...")
system = System("minimal_pid")
system.add_module(setpoint)
system.add_module(error_input)
system.add_module(pid)
system.add_module(plant)
print(f"[OK] Added {len(system.modules)} modules\n")

# Connect: just PID output to plant input
print("Connecting PID output to plant input...")
system.connect("pid.output ~ plant.input")
print(f"[OK] 1 connection defined\n")

# Compile
print("Compiling system...")
try:
    compiled = system.compile()
    print("[SUCCESS] System compiled!\n")
except Exception as e:
    print(f"[ERROR] Compilation failed:\n{e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Simulate
print("Running simulation...")
try:
    simulator = Simulator(system)
    times, values = simulator.run(
        t_span=(0.0, 10.0),
        dt=0.1,
        solver="Rodas5"
    )
    print(f"[SUCCESS] Simulation completed!")
    print(f"          Time points: {len(times)}")
    print(f"          States: {values.shape[1]}")
    print()
except Exception as e:
    print(f"[ERROR] Simulation failed:\n{e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
print("TEST PASSED!")
print("=" * 60)
