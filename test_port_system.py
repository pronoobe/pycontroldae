"""
Port System Simple Test

Tests the new Port-based connection system with a simple example.
"""

import sys
sys.path.insert(0, '.')

from pycontroldae.core import Module, System, Simulator

print("=" * 80)
print("Port System Test - Simple RC Circuit")
print("=" * 80)
print()

# Create RC circuit module
rc = Module("rc_circuit")
rc.add_input("I", 0.0)  # Input current - creates Port automatically
rc.add_output("V", 0.0)  # Output voltage - creates Port automatically
rc.add_param("R", 1000.0)
rc.add_param("C", 1e-6)
rc.add_equation("D(V) ~ (I - V/R)/C")
rc.set_input("I")  # Set default input port
rc.set_output("V")  # Set default output port

# Create input source
input_src = Module("input")
input_src.add_output("signal", 0.0)
input_src.add_equation("D(signal) ~ 0")  # Constant input
input_src.set_output("signal")  # Set as default output

# Build modules
rc.build()
input_src.build()

print("[1] Created modules:")
print(f"    RC circuit: {rc}")
print(f"      Ports: {list(rc._ports.keys())}")
print(f"      Default input: {rc._input_var}")
print(f"      Default output: {rc._output_var}")
print(f"    Input source: {input_src}")
print(f"      Ports: {list(input_src._ports.keys())}")
print(f"      Default output: {input_src._output_var}")
print()

# Test 1: Port object connection
print("[2] Test Port-based connection:")
print(f"    Connection: input_src.signal >> rc.I")

connection = input_src.signal >> rc.I
print(f"    Result type: {type(connection)}")
print(f"    Result: {connection}")
print(f"    Connection expr: {connection.expr}")
print()

# Test 2: Module-level connection (using default ports)
print("[3] Test Module-level connection:")
print(f"    Connection: input_src >> rc")

try:
    connection2 = input_src >> rc
    print(f"    Result type: {type(connection2)}")
    print(f"    Result: {connection2}")
    print(f"    Connection expr: {connection2.expr}")
except Exception as e:
    print(f"    [ERROR] {e}")
print()

# Test 3: Create system with Port connections
print("[4] Create system with Port connections:")

system = System("rc_system")
system.add_module(rc)
system.add_module(input_src)

# Use Port-based connection
system.connect(input_src.signal >> rc.I)

print(f"    Modules: {len(system.modules)}")
print(f"    Connections: {system.connections}")
print()

# Test 4: Compile and simulate
print("[5] Compile and simulate:")

try:
    compiled = system.compile()
    print(f"    [OK] System compiled successfully")

    simulator = Simulator(system)
    result = simulator.run(
        t_span=(0.0, 0.01),
        u0={"input.signal": 5.0},  # 5V input
        dt=0.0001,
        return_result=False
    )

    times, values = result
    print(f"    [OK] Simulation completed")
    print(f"          Time points: {len(times)}")
    print(f"          States: {values.shape[1]}")
    print(f"          Final voltage: {values[-1, 0]:.4f}V")
    print()

except Exception as e:
    print(f"    [ERROR] {e}")
    import traceback
    traceback.print_exc()
    print()

print("=" * 80)
print("Port System Test Completed!")
print("=" * 80)
