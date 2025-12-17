"""
Simple test without events - just run a basic PID control loop
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from pycontroldae.blocks import PID, Gain, Sum, Constant, Step, StateSpace
from pycontroldae.core import System, Simulator

print("=" * 60)
print("Simple PID Control Test (No Events)")
print("=" * 60)
print()

# Simple feedback control system
setpoint = Step(name="sp", amplitude=1.0, step_time=1.0)
setpoint.set_output("signal")

error_calc = Sum(name="error", num_inputs=2, signs=[+1, -1])

pid = PID(name="pid", Kp=2.0, Ki=0.5, Kd=0.1)

# Simple first-order plant: dx/dt = -x + u, y = x
A = np.array([[-1.0]])
B = np.array([[1.0]])
C = np.array([[1.0]])
D = np.array([[0.0]])
plant = StateSpace(name="plant", A=A, B=B, C=C, D=D)

# Build modules
print("Building modules...")
setpoint.build()
error_calc.build()
pid.build()
plant.build()
print("[OK] All modules built\n")

# Create system
print("Creating system...")
system = System("simple_pid")
system.add_module(setpoint)
system.add_module(error_calc)
system.add_module(pid)
system.add_module(plant)
print(f"[OK] Added {len(system.modules)} modules\n")

# Connect
print("Defining connections...")
system.connect("sp.signal ~ error.input1")
system.connect("plant.y1 ~ error.input2")
system.connect("error.output ~ pid.error")
system.connect("pid.output ~ plant.u1")
print(f"[OK] {len(system.connections)} connections\n")

# Compile
print("Compiling system...")
try:
    compiled = system.compile()
    print("[SUCCESS] System compiled!\n")
except Exception as e:
    print(f"[ERROR] Compilation failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Simulate
print("Running simulation (0-10s)...")
try:
    simulator = Simulator(system)
    times, values = simulator.run(
        t_span=(0.0, 10.0),
        dt=0.05,
        solver="Rodas5"
    )
    print(f"[SUCCESS] Simulation completed!")
    print(f"          Time points: {len(times)}")
    print(f"          States: {values.shape[1]}")
    print(f"          Final values: {values[-1, :5]}")
    print()
except Exception as e:
    print(f"[ERROR] Simulation failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
print("TEST PASSED!")
print("="  * 60)
