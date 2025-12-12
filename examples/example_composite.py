"""
Examples: CompositeModule - Hierarchical System Composition

Demonstrates practical use cases for CompositeModule to build
reusable, modular control system components.
"""

import sys
sys.path.insert(0, '..')

from pycontroldae.blocks import PID, Gain, Limiter, Sum, Integrator
from pycontroldae.core import CompositeModule, create_composite

print("=" * 70)
print("CompositeModule Usage Examples")
print("=" * 70)
print()

# ==============================================================================
# Example 1: PID Controller with Anti-Windup
# ==============================================================================
print("Example 1: PID Controller with Anti-Windup")
print("-" * 70)
print("Create a reusable PID controller with output limiting")
print()

# Create composite PID with limiter
pid_antiwindup = CompositeModule(name="pid_with_limiter")

# Add components
pid = PID(name="pid", Kp=2.0, Ki=0.5, Kd=0.1)
limiter = Limiter(name="limiter", min_value=-10.0, max_value=10.0)

pid_antiwindup.add_module(pid)
pid_antiwindup.add_module(limiter)
pid_antiwindup.add_connection("pid.output ~ limiter.input")

# Expose clean interfaces
pid_antiwindup.expose_input("error", "pid.error")
pid_antiwindup.expose_output("control", "limiter.output")

pid_antiwindup.build()

print(f"Created: {pid_antiwindup}")
print(f"Interface:")
print(f"  Input: error (connects to internal PID)")
print(f"  Output: control (comes from limiter)")
print(f"  Internal: PID -> Limiter")
print()

# ==============================================================================
# Example 2: Cascaded Amplifier Chain
# ==============================================================================
print("Example 2: Cascaded Amplifier Chain")
print("-" * 70)
print("Multi-stage amplifier with configurable gain at each stage")
print()

# Using convenience function
amplifier_chain = create_composite(
    name="amplifier_chain",
    modules=[
        Gain(name="stage1", K=2.0),
        Gain(name="stage2", K=1.5),
        Gain(name="stage3", K=3.0)
    ],
    connections=[
        "stage1.output ~ stage2.input",
        "stage2.output ~ stage3.input"
    ],
    inputs={"signal_in": "stage1.input"},
    outputs={"signal_out": "stage3.output"}
)

amplifier_chain.build()

print(f"Created: {amplifier_chain}")
print(f"Total gain: 2.0 * 1.5 * 3.0 = 9.0")
print(f"Stages: input -> [2x] -> [1.5x] -> [3x] -> output")
print()

# ==============================================================================
# Example 3: Pre-filter with Controller
# ==============================================================================
print("Example 3: Pre-filtered Controller")
print("-" * 70)
print("Controller with low-pass filter on error signal")
print()

prefiltered_controller = CompositeModule(name="filtered_pid")

# Create components
error_filter = Gain(name="filter", K=0.8)  # Simple gain as example filter
controller = PID(name="pid", Kp=3.0, Ki=1.0, Kd=0.2)

prefiltered_controller.add_module(error_filter)
prefiltered_controller.add_module(controller)
prefiltered_controller.add_connection("filter.output ~ pid.error")

# Expose interfaces
prefiltered_controller.expose_input("error_raw", "filter.input")
prefiltered_controller.expose_output("control_signal", "pid.output")

prefiltered_controller.build()

print(f"Created: {prefiltered_controller}")
print(f"Signal flow: error_raw -> filter -> PID -> control_signal")
print()

# ==============================================================================
# Example 4: Feedback Loop (Error Computation)
# ==============================================================================
print("Example 4: Feedback Error Computer")
print("-" * 70)
print("Encapsulate error computation: error = reference - feedback")
print()

error_computer = CompositeModule(name="error_calc")

# Summer for error: error = reference - feedback
summer = Sum(name="sum", num_inputs=2, signs=[+1, -1])

error_computer.add_module(summer)

# Expose three interfaces
error_computer.expose_input("reference", "sum.input1")
error_computer.expose_input("feedback", "sum.input2")
error_computer.expose_output("error", "sum.output")

error_computer.build()

print(f"Created: {error_computer}")
print(f"Inputs: reference, feedback")
print(f"Output: error = reference - feedback")
print(f"Usage: Simplifies feedback loop connections")
print()

# ==============================================================================
# Example 5: Complete Control Loop as Composite
# ==============================================================================
print("Example 5: Complete Feedback Control Loop")
print("-" * 70)
print("Entire control loop encapsulated in one module")
print()

control_loop = CompositeModule(name="pid_feedback_loop")

# Create all components
ref_summer = Sum(name="error_sum", num_inputs=2, signs=[+1, -1])
controller_pid = PID(name="controller", Kp=2.0, Ki=0.5, Kd=0.1)
plant_model = Gain(name="plant", K=1.5)  # Simplified plant

control_loop.add_module(ref_summer)
control_loop.add_module(controller_pid)
control_loop.add_module(plant_model)

# Internal connections
control_loop.add_connection("error_sum.output ~ controller.error")
control_loop.add_connection("controller.output ~ plant.input")
control_loop.add_connection("plant.output ~ error_sum.input2")  # Feedback

# Expose only external interface
control_loop.expose_input("setpoint", "error_sum.input1")
control_loop.expose_output("process_value", "plant.output")

control_loop.build()

print(f"Created: {control_loop}")
print(f"External view:")
print(f"  Input: setpoint")
print(f"  Output: process_value")
print(f"Internal structure:")
print(f"  setpoint -> [error_sum] -> controller -> plant -> process_value")
print(f"                    ^                                      |")
print(f"                    +--------------------------------------+")
print()

# ==============================================================================
# Example 6: Nested Hierarchy
# ==============================================================================
print("Example 6: Hierarchical Composition")
print("-" * 70)
print("Nested composites for complex systems")
print()

# Inner: Two-stage amplifier
inner_amp = create_composite(
    name="dual_amp",
    modules=[
        Gain(name="amp_a", K=2.0),
        Gain(name="amp_b", K=2.0)
    ],
    connections=["amp_a.output ~ amp_b.input"],
    inputs={"in": "amp_a.input"},
    outputs={"out": "amp_b.output"}
)

# Outer: Inner + output limiter
protected_amplifier = CompositeModule(name="protected_amp")
output_limiter = Limiter(name="limiter", min_value=-5.0, max_value=5.0)

protected_amplifier.add_module(inner_amp)
protected_amplifier.add_module(output_limiter)
protected_amplifier.add_connection("dual_amp.out ~ limiter.input")

protected_amplifier.expose_input("signal", "dual_amp.in")
protected_amplifier.expose_output("limited_output", "limiter.output")

protected_amplifier.build()

print(f"Created: {protected_amplifier}")
print(f"Hierarchy:")
print(f"  Level 0: {protected_amplifier.name}")
print(f"    Level 1: {inner_amp.name} (composite)")
print(f"      Level 2: amp_a, amp_b (modules)")
print(f"    Level 1: limiter (module)")
print()

# ==============================================================================
# Example 7: MIMO System Encapsulation
# ==============================================================================
print("Example 7: Multi-Input Multi-Output System")
print("-" * 70)
print("Encapsulate MIMO dynamics")
print()

mimo_system = CompositeModule(name="coupled_system")

# Two parallel integrators with cross-coupling
integrator1 = Integrator(name="int1", initial_value=0.0)
integrator2 = Integrator(name="int2", initial_value=0.0)

# Coupling gains
coupling_12 = Gain(name="coupling_12", K=0.1)
coupling_21 = Gain(name="coupling_21", K=0.15)

# Summers for adding coupling
summer1 = Sum(name="sum1", num_inputs=2, signs=[+1, +1])
summer2 = Sum(name="sum2", num_inputs=2, signs=[+1, +1])

mimo_system.add_module(summer1)
mimo_system.add_module(summer2)
mimo_system.add_module(integrator1)
mimo_system.add_module(integrator2)
mimo_system.add_module(coupling_12)
mimo_system.add_module(coupling_21)

# Connections (simplified for demonstration)
mimo_system.add_connection("sum1.output ~ int1.input")
mimo_system.add_connection("sum2.output ~ int2.input")
mimo_system.add_connection("int1.output ~ coupling_12.input")
mimo_system.add_connection("int2.output ~ coupling_21.input")
mimo_system.add_connection("coupling_21.output ~ sum1.input2")
mimo_system.add_connection("coupling_12.output ~ sum2.input2")

# Multiple inputs and outputs
mimo_system.expose_input("u1", "sum1.input1")
mimo_system.expose_input("u2", "sum2.input1")
mimo_system.expose_output("y1", "int1.output")
mimo_system.expose_output("y2", "int2.output")

mimo_system.build()

print(f"Created: {mimo_system}")
print(f"Type: 2-input, 2-output coupled system")
print(f"Inputs: u1, u2")
print(f"Outputs: y1, y2")
print(f"Feature: Cross-coupling between channels")
print()

# ==============================================================================
# Summary
# ==============================================================================
print("=" * 70)
print("CompositeModule Use Cases Demonstrated")
print("=" * 70)
print()
print("Benefits:")
print("  - Modularity: Build complex systems from simple components")
print("  - Reusability: Create once, use anywhere")
print("  - Abstraction: Hide internal complexity")
print("  - Hierarchy: Nest composites for scalable design")
print("  - Clarity: Well-defined interfaces improve maintainability")
print()
print("Applications:")
print("  - Standard controller configurations (PID + anti-windup)")
print("  - Signal processing chains (filters, amplifiers)")
print("  - Complete feedback loops")
print("  - Multi-stage systems (cascades, hierarchies)")
print("  - MIMO coupled systems")
print()
print("Design Pattern:")
print("  1. Create CompositeModule")
print("  2. Add sub-modules (can be Module or CompositeModule)")
print("  3. Define internal connections")
print("  4. Expose input/output interfaces")
print("  5. Build and use like any Module")
print()
