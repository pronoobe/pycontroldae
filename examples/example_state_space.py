"""
Example: Using StateSpace Module

Demonstrates how to create and use state-space models for linear systems.
"""

import sys
sys.path.insert(0, '..')

import numpy as np
from pycontroldae.blocks import StateSpace, create_state_space

print("=" * 70)
print("StateSpace Module Examples")
print("=" * 70)
print()

# ==============================================================================
# Example 1: Simple Integrator
# ==============================================================================
print("Example 1: Simple Integrator")
print("-" * 70)
print("System: dx/dt = u, y = x")
print()

A = np.array([[0.0]])
B = np.array([[1.0]])
C = np.array([[1.0]])
D = np.array([[0.0]])

integrator = StateSpace(name="integrator", A=A, B=B, C=C, D=D)
integrator.build()

print(f"Created: {integrator}")
print(f"States: {integrator.get_state_vector()}")
print(f"Inputs: {integrator.get_input_vector()}")
print(f"Outputs: {integrator.get_output_vector()}")
print()

# ==============================================================================
# Example 2: First-Order Low-Pass Filter
# ==============================================================================
print("Example 2: First-Order Low-Pass Filter")
print("-" * 70)
print("Transfer function: H(s) = K / (τs + 1)")
print()

tau = 0.1  # Time constant (seconds)
K = 1.0    # DC gain

# State-space form: dx/dt = -x/τ + K/τ * u, y = x
A = np.array([[-1.0/tau]])
B = np.array([[K/tau]])
C = np.array([[1.0]])
D = np.array([[0.0]])

lpf = create_state_space(A, B, C, D, name="low_pass_filter")
lpf.build()

print(f"Created: {lpf}")
print(f"Time constant: {tau} s")
print(f"DC gain: {K}")
print(f"Cutoff frequency: {1/(2*np.pi*tau):.2f} Hz")
print()

# ==============================================================================
# Example 3: Mass-Spring-Damper System
# ==============================================================================
print("Example 3: Mass-Spring-Damper System")
print("-" * 70)
print("Equation: m*d2x/dt2 + c*dx/dt + k*x = F")
print()

m = 2.0   # Mass (kg)
c = 1.0   # Damping coefficient (N·s/m)
k = 10.0  # Spring constant (N/m)

# State variables: x1 = position, x2 = velocity
# dx1/dt = x2
# dx2/dt = -k/m * x1 - c/m * x2 + 1/m * F

A = np.array([
    [0.0,     1.0],
    [-k/m,   -c/m]
])
B = np.array([
    [0.0],
    [1.0/m]
])
C = np.array([[1.0, 0.0]])  # Output is position
D = np.array([[0.0]])

msd = StateSpace(name="mass_spring_damper", A=A, B=B, C=C, D=D,
                 initial_state=np.array([1.0, 0.0]))  # Initial displacement
msd.build()

omega_n = np.sqrt(k/m)  # Natural frequency
zeta = c / (2*np.sqrt(k*m))  # Damping ratio

print(f"Created: {msd}")
print(f"Mass: {m} kg")
print(f"Spring constant: {k} N/m")
print(f"Damping: {c} N·s/m")
print(f"Natural frequency: {omega_n:.3f} rad/s ({omega_n/(2*np.pi):.3f} Hz)")
print(f"Damping ratio: {zeta:.3f}")
if zeta < 1:
    print(f"System is underdamped (will oscillate)")
elif zeta == 1:
    print(f"System is critically damped")
else:
    print(f"System is overdamped")
print()

# ==============================================================================
# Example 4: Double Integrator (Position Control)
# ==============================================================================
print("Example 4: Double Integrator (Position Control)")
print("-" * 70)
print("System: d2x/dt2 = u")
print("State: [position, velocity]")
print()

# State variables: x1 = position, x2 = velocity
# dx1/dt = x2
# dx2/dt = u

A = np.array([
    [0.0, 1.0],
    [0.0, 0.0]
])
B = np.array([
    [0.0],
    [1.0]
])
C = np.array([
    [1.0, 0.0],  # Output 1: position
    [0.0, 1.0]   # Output 2: velocity
])
D = np.zeros((2, 1))

double_int = StateSpace(name="double_integrator", A=A, B=B, C=C, D=D)
double_int.build()

print(f"Created: {double_int}")
print(f"Number of outputs: {double_int.n_outputs} (position and velocity)")
print()

# ==============================================================================
# Example 5: DC Motor Model
# ==============================================================================
print("Example 5: DC Motor Model")
print("-" * 70)
print("Electrical: L*di/dt + R*i = V - K_e*w")
print("Mechanical: J*dw/dt + b*w = K_t*i")
print()

# Motor parameters
R = 1.0     # Armature resistance (Ohm)
L = 0.5     # Armature inductance (H)
K_e = 0.01  # Back-EMF constant (V*s/rad)
K_t = 0.01  # Torque constant (N*m/A)
J = 0.01    # Rotor inertia (kg*m^2)
b = 0.1     # Viscous friction (N*m*s/rad)

# State variables: x1 = current, x2 = angular velocity
# dx1/dt = -R/L * x1 - K_e/L * x2 + 1/L * V
# dx2/dt = K_t/J * x1 - b/J * x2

A = np.array([
    [-R/L,    -K_e/L],
    [K_t/J,   -b/J]
])
B = np.array([
    [1.0/L],
    [0.0]
])
C = np.array([
    [0.0, 1.0],  # Output 1: angular velocity
    [1.0, 0.0]   # Output 2: current
])
D = np.zeros((2, 1))

motor = StateSpace(name="dc_motor", A=A, B=B, C=C, D=D)
motor.build()

print(f"Created: {motor}")
print(f"Motor parameters:")
print(f"  Resistance: {R} Ohm")
print(f"  Inductance: {L} H")
print(f"  Torque constant: {K_t} N*m/A")
print(f"  Back-EMF constant: {K_e} V*s/rad")
print(f"  Inertia: {J} kg*m^2")
print(f"  Friction: {b} N*m*s/rad")
print()

# ==============================================================================
# Example 6: MIMO System (2x2)
# ==============================================================================
print("Example 6: MIMO System (2 inputs, 2 outputs)")
print("-" * 70)
print("Two coupled first-order systems")
print()

A = np.array([
    [-2.0,  0.5],
    [ 1.0, -3.0]
])
B = np.array([
    [1.0, 0.0],
    [0.0, 2.0]
])
C = np.array([
    [1.0, 0.0],
    [0.0, 1.0]
])
D = np.zeros((2, 2))

mimo = StateSpace(name="mimo_coupled", A=A, B=B, C=C, D=D)
mimo.build()

print(f"Created: {mimo}")
print(f"Coupling from state 2 to state 1: A[0,1] = {A[0,1]}")
print(f"Coupling from state 1 to state 2: A[1,0] = {A[1,0]}")
print()

# ==============================================================================
# Summary
# ==============================================================================
print("=" * 70)
print("Summary")
print("=" * 70)
print()
print("The StateSpace module allows you to define any linear time-invariant (LTI)")
print("system using state-space representation:")
print()
print("  dx/dt = A*x + B*u  (state equation)")
print("  y = C*x + D*u      (output equation)")
print()
print("Key features:")
print("  - Supports SISO and MIMO systems")
print("  - Accepts numpy arrays for A, B, C, D matrices")
print("  - Automatic dimension validation")
print("  - Optional initial state specification")
print("  - Efficient handling of sparse matrices")
print("  - Direct feedthrough via D matrix")
print()
print("Common applications:")
print("  - Mechanical systems (mass-spring-damper, pendulum)")
print("  - Electrical systems (RLC circuits, DC motors)")
print("  - Control systems (filters, compensators)")
print("  - Multi-input multi-output (MIMO) systems")
print()
