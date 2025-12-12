# StateSpace Module Implementation

## Overview

Successfully implemented the `StateSpace` module in `blocks/linear.py` that provides state-space representation for linear time-invariant (LTI) systems.

## Features

### Mathematical Form
The StateSpace module implements the continuous-time state-space model:

```
dx/dt = A*x + B*u  (state equation)
y = C*x + D*u      (output equation)
```

Where:
- `x`: State vector (n × 1)
- `u`: Input vector (m × 1)
- `y`: Output vector (p × 1)
- `A`: System matrix (n × n)
- `B`: Input matrix (n × m)
- `C`: Output matrix (p × n)
- `D`: Feedthrough matrix (p × m)

### Key Capabilities

1. **SISO and MIMO Support**
   - Single-input single-output (SISO) systems
   - Multi-input multi-output (MIMO) systems
   - Arbitrary dimensions (n states, m inputs, p outputs)

2. **Numpy Array Interface**
   - Accepts numpy arrays for A, B, C, D matrices
   - Automatic conversion to Julia ModelingToolkit equations
   - Handles matrix multiplication by expanding to scalar equations

3. **Dimension Validation**
   - Automatic checking of matrix dimensions
   - Clear error messages for incompatible dimensions
   - Validates A (square), B, C, D compatibility

4. **Initial State Specification**
   - Optional initial state vector
   - Defaults to zero initial state
   - Supports multi-dimensional initial conditions

5. **Efficiency Optimizations**
   - Skips near-zero terms (< 1e-15) in equations
   - Efficient handling of sparse matrices
   - Minimal equation generation

6. **Direct Feedthrough**
   - Supports non-zero D matrix
   - Proper handling of algebraic relationships

## Implementation Details

### Class Structure

```python
class StateSpace(Module):
    def __init__(
        self,
        name: str = "ss",
        A: Optional[np.ndarray] = None,
        B: Optional[np.ndarray] = None,
        C: Optional[np.ndarray] = None,
        D: Optional[np.ndarray] = None,
        initial_state: Optional[np.ndarray] = None
    )
```

### Internal Variables

For a system with n states, m inputs, p outputs:

**States:**
- `x1, x2, ..., xn`: Internal state variables
- `u1, u2, ..., um`: Input variables (set externally)
- `y1, y2, ..., yp`: Output variables

**Parameters:**
- `tau_y1, tau_y2, ..., tau_yp`: Fast time constants for output tracking (0.001s)

### Equation Generation

The module generates Julia ModelingToolkit equations by:

1. **State Equations**: For each state `xi`:
   ```
   D(xi) ~ sum(A[i,j] * xj) + sum(B[i,k] * uk)
   ```

2. **Output Equations**: For each output `yi`:
   ```
   D(yi) ~ (sum(C[i,j] * xj) + sum(D[i,k] * uk) - yi) / tau_yi
   ```

3. **Zero-Term Elimination**: Only includes terms where |coefficient| > 1e-15

### Helper Methods

```python
get_state_vector() -> list    # Returns ['x1', 'x2', ..., 'xn']
get_input_vector() -> list    # Returns ['u1', 'u2', ..., 'um']
get_output_vector() -> list   # Returns ['y1', 'y2', ..., 'yp']
```

## Usage Examples

### Example 1: Simple Integrator
```python
import numpy as np
from pycontroldae.blocks import StateSpace

A = np.array([[0.0]])
B = np.array([[1.0]])
C = np.array([[1.0]])
D = np.array([[0.0]])

integrator = StateSpace(name="int", A=A, B=B, C=C, D=D)
integrator.build()
```

### Example 2: Second-Order System
```python
# Mass-spring-damper: m*d²x/dt² + c*dx/dt + k*x = F
m = 1.0   # mass
c = 0.5   # damping
k = 4.0   # stiffness

A = np.array([[0.0, 1.0], [-k/m, -c/m]])
B = np.array([[0.0], [1.0/m]])
C = np.array([[1.0, 0.0]])  # position output
D = np.array([[0.0]])

msd = StateSpace(name="msd", A=A, B=B, C=C, D=D)
msd.build()
```

### Example 3: MIMO System
```python
# 2-input, 2-output coupled system
A = np.array([[-1.0, 0.5], [0.0, -2.0]])
B = np.array([[1.0, 0.0], [0.0, 1.0]])
C = np.array([[1.0, 0.0], [0.0, 1.0]])
D = np.zeros((2, 2))

mimo = StateSpace(name="mimo", A=A, B=B, C=C, D=D)
mimo.build()
```

### Example 4: Initial State
```python
# System with non-zero initial condition
A = np.array([[-1.0]])
B = np.array([[1.0]])
C = np.array([[1.0]])
D = np.array([[0.0]])
x0 = np.array([5.0])

ss = StateSpace(name="with_init", A=A, B=B, C=C, D=D, initial_state=x0)
ss.build()
```

### Example 5: Convenience Function
```python
from pycontroldae.blocks import create_state_space

A = np.array([[0, 1], [-1, -0.5]])
B = np.array([[0], [1]])
C = np.array([[1, 0]])
D = np.array([[0]])

plant = create_state_space(A, B, C, D, name="plant")
```

## Testing

Created comprehensive test suite in `test_state_space_simple.py`:

### Test Coverage
1. ✓ Simple integrator (SISO)
2. ✓ First-order system (SISO)
3. ✓ Second-order system (mass-spring-damper)
4. ✓ MIMO system (2×2)
5. ✓ Dimension validation
6. ✓ Convenience function
7. ✓ Non-zero initial state
8. ✓ Sparse matrices
9. ✓ Multi-state initial conditions
10. ✓ Feedthrough (non-zero D matrix)

All tests pass successfully.

## Files Created/Modified

1. **pycontroldae/blocks/linear.py** (268 lines)
   - StateSpace class implementation
   - create_state_space convenience function

2. **pycontroldae/blocks/__init__.py**
   - Added StateSpace and create_state_space exports

3. **test_state_space_simple.py** (416 lines)
   - Comprehensive test suite for StateSpace module

4. **examples/example_state_space.py** (252 lines)
   - Real-world examples:
     - Simple integrator
     - Low-pass filter
     - Mass-spring-damper
     - Double integrator
     - DC motor model
     - MIMO coupled system

## Integration with pycontroldae

The StateSpace module integrates seamlessly with the existing pycontroldae framework:

- Inherits from `Module` base class
- Supports connection operators (`>>` and `<<`)
- Compatible with `System` and `Simulator`
- Works with all signal sources and control blocks
- Uses get_param_map() for runtime parameter access
- Follows same build() pattern as other modules

## Common Applications

1. **Mechanical Systems**
   - Mass-spring-damper systems
   - Robotic manipulators
   - Vehicle dynamics

2. **Electrical Systems**
   - RLC circuits
   - DC motors
   - Power converters

3. **Control Systems**
   - State observers
   - Kalman filters
   - LQR/LQG controllers

4. **MIMO Systems**
   - Multi-variable processes
   - Coupled systems
   - Decentralized control

## Technical Notes

### Matrix Multiplication Handling

Instead of using Julia's array variables directly, the implementation expands matrix operations into scalar equations:

```julia
# Instead of: D(x) ~ A*x + B*u
# Generates:  D(x[i]) ~ A[i,1]*x[1] + A[i,2]*x[2] + ... + B[i,1]*u[1] + ...
```

This approach:
- Avoids array variable complexity in ModelingToolkit
- Provides explicit scalar equations for solver
- Enables automatic differentiation
- Works with structural_simplify

### Output Dynamics

Outputs use fast first-order dynamics (tau = 0.001s) to track the algebraic output equation:

```julia
D(y[i]) ~ (C[i,:]*x + D[i,:]*u - y[i]) / tau
```

This converts the algebraic constraint into a differential equation that:
- Is compatible with ODE solvers
- Tracks the true output very quickly
- Avoids DAE index issues
- Maintains numerical stability

## Future Enhancements

Potential improvements:
1. Add pole placement / eigenvalue analysis methods
2. Support for discrete-time systems
3. Transfer function to state-space conversion
4. State-space to transfer function conversion
5. Controllability/observability checks
6. State-space transformations (similarity transforms)
7. Model reduction capabilities

## Conclusion

The StateSpace module provides a powerful and flexible way to define linear systems in pycontroldae using standard state-space representation. It handles SISO and MIMO systems, validates dimensions, and integrates seamlessly with the existing framework.
