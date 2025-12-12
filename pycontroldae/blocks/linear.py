"""
Linear System Blocks for pycontroldae

This module provides linear system representations:
- StateSpace: State-space representation (A, B, C, D matrices)

State-space form:
    dx/dt = A*x + B*u
    y = C*x + D*u

Where:
    x: State vector (n x 1)
    u: Input vector (m x 1)
    y: Output vector (p x 1)
    A: System matrix (n x n)
    B: Input matrix (n x m)
    C: Output matrix (p x n)
    D: Feedthrough matrix (p x m)
"""

import numpy as np
from typing import Optional
from ..core.module import Module
from ..core.backend import get_jl


class StateSpace(Module):
    """
    State-space representation of a linear time-invariant (LTI) system.

    Implements the continuous-time state-space model:
        dx/dt = A*x + B*u
        y = C*x + D*u

    Uses Julia ModelingToolkit array variables for efficient vectorized operations.

    Parameters:
        A: System matrix (n x n numpy array)
        B: Input matrix (n x m numpy array)
        C: Output matrix (p x n numpy array)
        D: Feedthrough matrix (p x m numpy array)

    Inputs:
        u[1], u[2], ..., u[m]: Input signals

    Outputs:
        y[1], y[2], ..., y[p]: Output signals

    States:
        x[1], x[2], ..., x[n]: Internal states

    Example:
        >>> # Simple integrator: dx/dt = u, y = x
        >>> A = np.array([[0.0]])
        >>> B = np.array([[1.0]])
        >>> C = np.array([[1.0]])
        >>> D = np.array([[0.0]])
        >>> integrator = StateSpace(name="int", A=A, B=B, C=C, D=D)
        >>>
        >>> # Second-order system
        >>> A = np.array([[0.0, 1.0], [-2.0, -3.0]])
        >>> B = np.array([[0.0], [1.0]])
        >>> C = np.array([[1.0, 0.0]])
        >>> D = np.array([[0.0]])
        >>> system = StateSpace(name="plant", A=A, B=B, C=C, D=D)
    """

    def __init__(
        self,
        name: str = "ss",
        A: Optional[np.ndarray] = None,
        B: Optional[np.ndarray] = None,
        C: Optional[np.ndarray] = None,
        D: Optional[np.ndarray] = None,
        initial_state: Optional[np.ndarray] = None
    ):
        """
        Initialize a StateSpace module.

        Args:
            name: Name of the module
            A: System matrix (n x n)
            B: Input matrix (n x m)
            C: Output matrix (p x n)
            D: Feedthrough matrix (p x m)
            initial_state: Initial state vector (n x 1), defaults to zeros

        Raises:
            ValueError: If matrices are None or have incompatible dimensions
        """
        # Validate inputs
        if A is None or B is None or C is None or D is None:
            raise ValueError("A, B, C, D matrices must all be provided")

        # Convert to numpy arrays
        A = np.asarray(A, dtype=float)
        B = np.asarray(B, dtype=float)
        C = np.asarray(C, dtype=float)
        D = np.asarray(D, dtype=float)

        # Get dimensions
        if A.ndim != 2 or A.shape[0] != A.shape[1]:
            raise ValueError(f"A must be square matrix, got shape {A.shape}")

        n = A.shape[0]  # Number of states

        if B.ndim == 1:
            B = B.reshape(-1, 1)
        if B.shape[0] != n:
            raise ValueError(f"B must have {n} rows to match A, got {B.shape}")
        m = B.shape[1]  # Number of inputs

        if C.ndim == 1:
            C = C.reshape(1, -1)
        if C.shape[1] != n:
            raise ValueError(f"C must have {n} columns to match A, got {C.shape}")
        p = C.shape[0]  # Number of outputs

        if D.ndim == 1:
            D = D.reshape(1, -1)
        if D.shape != (p, m):
            raise ValueError(f"D must be {p} x {m} to match C and B, got {D.shape}")

        # Store dimensions and matrices
        self.n_states = n
        self.n_inputs = m
        self.n_outputs = p
        self.A = A
        self.B = B
        self.C = C
        self.D = D

        # Initialize parent with appropriate I/O variables
        # For single input/output, use scalars; for multiple, use arrays
        input_var = "u" if m == 1 else None
        output_var = "y" if p == 1 else None
        super().__init__(name, input_var=input_var, output_var=output_var)

        # Set initial state
        if initial_state is None:
            self.initial_state = np.zeros(n)
        else:
            initial_state = np.asarray(initial_state, dtype=float).flatten()
            if len(initial_state) != n:
                raise ValueError(f"initial_state must have length {n}, got {len(initial_state)}")
            self.initial_state = initial_state

        # Add states for state vector x[1], x[2], ..., x[n]
        for i in range(n):
            self.add_state(f"x{i+1}", self.initial_state[i])

        # Add states for input vector u[1], u[2], ..., u[m]
        # NO equations for inputs - they get values from connections
        for i in range(m):
            self.add_state(f"u{i+1}", 0.0)

        # Add states for output vector y[1], y[2], ..., y[p]
        for i in range(p):
            self.add_state(f"y{i+1}", 0.0)

        # Build state equations: dx/dt = A*x + B*u
        # For each state i: D(x[i]) = sum_j(A[i,j]*x[j]) + sum_k(B[i,k]*u[k])
        for i in range(n):
            # A*x terms
            ax_terms = []
            for j in range(n):
                if abs(A[i, j]) > 1e-15:  # Skip near-zero terms
                    ax_terms.append(f"{A[i,j]} * x{j+1}")

            # B*u terms
            bu_terms = []
            for k in range(m):
                if abs(B[i, k]) > 1e-15:  # Skip near-zero terms
                    bu_terms.append(f"{B[i,k]} * u{k+1}")

            # Combine terms
            all_terms = ax_terms + bu_terms
            if not all_terms:
                # All zero, state doesn't change
                rhs = "0"
            else:
                rhs = " + ".join(all_terms)

            self.add_equation(f"D(x{i+1}) ~ {rhs}")

        # Build output equations: y = C*x + D*u
        # For each output i: y[i] = sum_j(C[i,j]*x[j]) + sum_k(D[i,k]*u[k])
        for i in range(p):
            # C*x terms
            cx_terms = []
            for j in range(n):
                if abs(C[i, j]) > 1e-15:
                    cx_terms.append(f"{C[i,j]} * x{j+1}")

            # D*u terms
            du_terms = []
            for k in range(m):
                if abs(D[i, k]) > 1e-15:
                    du_terms.append(f"{D[i,k]} * u{k+1}")

            # Combine terms
            all_terms = cx_terms + du_terms
            if not all_terms:
                rhs = "0"
            else:
                rhs = " + ".join(all_terms)

            # Output follows the algebraic equation with fast dynamics
            self.add_parameter(f"tau_y{i+1}", 0.001)  # Fast response
            self.add_equation(f"D(y{i+1}) ~ ({rhs} - y{i+1}) / tau_y{i+1}")

    def get_state_vector(self) -> list:
        """
        Get the list of state variable names.

        Returns:
            List of state variable names ['x1', 'x2', ..., 'xn']
        """
        return [f"x{i+1}" for i in range(self.n_states)]

    def get_input_vector(self) -> list:
        """
        Get the list of input variable names.

        Returns:
            List of input variable names ['u1', 'u2', ..., 'um']
        """
        return [f"u{i+1}" for i in range(self.n_inputs)]

    def get_output_vector(self) -> list:
        """
        Get the list of output variable names.

        Returns:
            List of output variable names ['y1', 'y2', ..., 'yp']
        """
        return [f"y{i+1}" for i in range(self.n_outputs)]

    def __repr__(self) -> str:
        """String representation of the StateSpace module."""
        return (
            f"StateSpace(name='{self.name}', "
            f"states={self.n_states}, inputs={self.n_inputs}, outputs={self.n_outputs})"
        )


def create_state_space(
    A: np.ndarray,
    B: np.ndarray,
    C: np.ndarray,
    D: np.ndarray,
    name: str = "ss",
    initial_state: Optional[np.ndarray] = None
) -> StateSpace:
    """
    Convenience function to create a StateSpace module.

    Args:
        A: System matrix (n x n)
        B: Input matrix (n x m)
        C: Output matrix (p x n)
        D: Feedthrough matrix (p x m)
        name: Name of the module
        initial_state: Initial state vector (n x 1)

    Returns:
        StateSpace module

    Example:
        >>> A = np.array([[0, 1], [-2, -3]])
        >>> B = np.array([[0], [1]])
        >>> C = np.array([[1, 0]])
        >>> D = np.array([[0]])
        >>> plant = create_state_space(A, B, C, D, name="plant")
    """
    return StateSpace(name=name, A=A, B=B, C=C, D=D, initial_state=initial_state)
