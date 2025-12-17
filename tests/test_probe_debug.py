"""
Debug script to understand probe extraction for algebraic variables
"""
import numpy as np
from pycontroldae.core import Module, System, Simulator, DataProbe
from pycontroldae.blocks import Step

# Create simple DAE system with one algebraic variable
class SimpleDAE(Module):
    """Simple system with differential and algebraic variables"""
    def __init__(self, name):
        super().__init__(name)

        # Differential state
        self.add_state("x", 0.0)

        # Algebraic variable
        self.add_state("y", 0.0)

        # Input
        self.add_state("u", 0.0)

        # Differential equation
        self.add_equation("D(x) ~ -x + u")

        # Algebraic constraint
        self.add_equation("0 ~ y - 2*x")  # y = 2*x

# Build system
system = System("test_dae")

input_signal = Step(name="input", amplitude=1.0, step_time=0.0)
input_signal.set_output("signal")

dae = SimpleDAE("dae")

system.add_module(input_signal)
system.add_module(dae)
system.connect(input_signal.signal >> dae.u)

# Compile
print("Compiling system...")
system.compile()

# Create probes for both differential and algebraic variables
probes = DataProbe(
    variables=["dae.x", "dae.y"],  # x is differential, y is algebraic
    names=["Differential_x", "Algebraic_y"]
)

# Simulate
print("Running simulation...")
simulator = Simulator(system)
result = simulator.run(
    t_span=(0.0, 5.0),
    dt=0.1,
    probes=probes
)

# Check results
print("\n=== Results ===")
print(f"State names: {result.state_names}")
print(f"\nProbe data keys: {list(result.probe_data.keys())}")

if 'default' in result.probe_data:
    probe_vars = result.probe_data['default']
    print(f"Probe variables: {list(probe_vars.keys())}")

    for var_name, var_values in probe_vars.items():
        print(f"\n{var_name}:")
        print(f"  First 10 values: {var_values[:10]}")
        print(f"  Mean: {np.mean(var_values):.6f}")
        print(f"  Std: {np.std(var_values):.6f}")
        print(f"  Min: {np.min(var_values):.6f}")
        print(f"  Max: {np.max(var_values):.6f}")

# Also check state values directly
print("\n=== Direct State Values ===")
for state_name in result.state_names:
    state_values = result.get_state(state_name)
    print(f"{state_name}: mean={np.mean(state_values):.6f}, max={np.max(state_values):.6f}")

print("\n=== Analysis ===")
print("If Algebraic_y is all zeros but Differential_x has values,")
print("then the probe extraction for algebraic variables is not working.")
print("Expected: Algebraic_y should be approximately 2 * Differential_x")
