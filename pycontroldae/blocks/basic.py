"""
Basic Control Modules for pycontroldae - REDESIGNED

This module provides fundamental control system building blocks:
- Gain: Proportional gain (amplifier)
- Sum: Summing junction (adder/subtractor)
- PID: PID controller with standard form
- Integrator: Pure integrator
- Derivative: Derivative with filtering
- Limiter: Signal saturation

Key Design Principle:
- Input variables are ALGEBRAIC (no D(input) equations)
- Only true dynamic states have differential equations
- This prevents overconstraint when connecting modules

All blocks support connection operators (>> and <<) and work with CompositeModule.
"""

from typing import Optional, List
from ..core.module import Module


class Gain(Module):
    """
    Proportional gain (amplifier) block.

    Multiplies the input signal by a constant gain: output = K * input

    Parameters:
        - K: Gain value

    Input:
        - input: Input signal (algebraic variable)

    Output:
        - output: Output signal (K * input, algebraic)

    Example:
        >>> gain = Gain(K=2.5)
        >>> system.connect(sensor >> gain >> controller)
    """

    def __init__(self, name: str = "gain", K: float = 1.0):
        """
        Initialize a Gain block.

        Args:
            name: Name of the module
            K: Gain value
        """
        super().__init__(name, input_var="input", output_var="output")

        # States: input determined by connection, output tracks input
        self.add_state("input", 0.0)
        self.add_state("output", 0.0)

        # Parameters
        self.add_parameter("K", K)

        # Fast time constant for output response
        self.add_parameter("tau", 1e-6)  # Very fast: 1 microsecond

        # Equations
        # Input: NO equation - determined purely by connections

        # Output: Fast first-order tracking of K * input
        # This avoids algebraic loops while still being nearly instantaneous
        self.add_equation("D(output) ~ (K * input - output) / tau")


class Sum(Module):
    """
    Summing junction (adder/subtractor) block.

    Computes the weighted sum of multiple inputs: output = Σ(sign_i * input_i)

    By default, creates a 2-input summer. Use signs parameter to specify
    addition (+1) or subtraction (-1) for each input.

    Parameters:
        - signs: List of signs for each input (+1 or -1)

    Inputs:
        - input1, input2, ... : Input signals (algebraic)

    Output:
        - output: Sum of weighted inputs (algebraic)

    Example:
        >>> # Error signal: reference - measurement
        >>> summer = Sum(signs=[+1, -1])  # output = input1 - input2
        >>> system.connect(reference >> summer.set_input("input1"))
        >>> system.connect(measurement >> summer.set_input("input2"))
        >>> system.connect(summer >> controller)
    """

    def __init__(
        self,
        name: str = "sum",
        num_inputs: int = 2,
        signs: Optional[List[int]] = None
    ):
        """
        Initialize a Sum block.

        Args:
            name: Name of the module
            num_inputs: Number of inputs (default: 2)
            signs: List of signs for each input (+1 or -1).
                   If None, defaults to all +1
        """
        super().__init__(name, output_var="output")

        self.num_inputs = num_inputs

        # Set signs (default to all positive)
        if signs is None:
            self.signs = [1] * num_inputs
        else:
            if len(signs) != num_inputs:
                raise ValueError(
                    f"Length of signs ({len(signs)}) must match num_inputs ({num_inputs})"
                )
            self.signs = signs

        # States for inputs (all determined by connections)
        for i in range(num_inputs):
            self.add_state(f"input{i+1}", 0.0)
            # NO equation for inputs!

        # State for output
        self.add_state("output", 0.0)

        # Fast time constant
        self.add_parameter("tau", 1e-6)

        # Build the sum equation: output = sign1*input1 + sign2*input2 + ...
        terms = [
            f"{'+' if sign >= 0 else ''}{sign} * input{i+1}"
            for i, sign in enumerate(self.signs)
        ]
        sum_expr = " + ".join(terms)

        # Fast first-order tracking
        self.add_equation(f"D(output) ~ (({sum_expr}) - output) / tau")

    def set_input_connection(self, input_num: int) -> str:
        """
        Get the input variable name for a specific input number.

        Args:
            input_num: Input number (1-indexed)

        Returns:
            Input variable name

        Example:
            >>> summer = Sum(num_inputs=3)
            >>> # Connect to input 2
            >>> system.connect(f"source.output ~ summer.{summer.set_input_connection(2)}")
        """
        if input_num < 1 or input_num > self.num_inputs:
            raise ValueError(
                f"Input number must be between 1 and {self.num_inputs}"
            )
        return f"input{input_num}"


class PID(Module):
    """
    PID Controller with standard form.

    Implements the standard PID control law:
        u(t) = Kp * e(t) + Ki * ∫e(τ)dτ + Kd * de(t)/dt

    Where:
        - e(t) = error signal (typically reference - measurement)
        - Kp = Proportional gain
        - Ki = Integral gain
        - Kd = Derivative gain

    The controller can also include:
        - Anti-windup: Limits the integral term
        - Derivative filtering: Low-pass filter on derivative term

    Parameters:
        - Kp: Proportional gain
        - Ki: Integral gain
        - Kd: Derivative gain
        - integral_limit: Anti-windup limit for integral term (optional)
        - derivative_filter_time: Time constant for derivative filter (optional)

    Input:
        - error: Error signal (reference - measurement) [algebraic]

    Output:
        - output: Control signal u(t) [algebraic]

    Internal States:
        - integral: Integral of error ∫e(τ)dτ [differential]
        - filtered_error: Filtered error for derivative [differential]

    Example:
        >>> # Create PID controller
        >>> pid = PID(name="pid", Kp=2.0, Ki=0.5, Kd=0.1)
        >>>
        >>> # Connect in feedback loop
        >>> system.connect(error_signal >> pid >> plant)
    """

    def __init__(
        self,
        name: str = "pid",
        Kp: float = 1.0,
        Ki: float = 0.0,
        Kd: float = 0.0,
        integral_limit: Optional[float] = None,
        derivative_filter_time: float = 0.01
    ):
        """
        Initialize a PID Controller.

        Args:
            name: Name of the module
            Kp: Proportional gain
            Ki: Integral gain
            Kd: Derivative gain
            integral_limit: Maximum absolute value for integral term (anti-windup)
            derivative_filter_time: Time constant for derivative filter (seconds)
        """
        super().__init__(name, input_var="error", output_var="output")

        # Parameters
        self.add_parameter("Kp", Kp)
        self.add_parameter("Ki", Ki)
        self.add_parameter("Kd", Kd)
        self.add_parameter("Td", derivative_filter_time)

        # States
        self.add_state("error", 0.0)              # Error input [NO equation - from connection]
        self.add_state("integral", 0.0)           # Integral of error [DIFFERENTIAL]
        self.add_state("filtered_error", 0.0)     # Filtered error [DIFFERENTIAL]
        self.add_state("output", 0.0)             # Control output [DIFFERENTIAL - fast tracking]

        # Store limits
        self.integral_limit = integral_limit

        # Parameters
        self.add_parameter("tau_out", 1e-6)  # Fast output response

        # Equations

        # 1. Error input: NO equation - determined by connections

        # 2. Integral term: D(integral) = Ki * error
        if integral_limit is not None:
            # With anti-windup: use smooth saturation to limit integral
            self.add_parameter("int_limit", integral_limit)
            # Smooth anti-windup: reduce integration rate as we approach the limit
            # D(integral) = Ki * error * (1 - (integral/limit)^2)
            self.add_equation(
                "D(integral) ~ Ki * error * (1 - (integral / int_limit)^2)"
            )
        else:
            # No anti-windup
            self.add_equation("D(integral) ~ Ki * error")

        # 3. Derivative term with filtering
        # First-order filter: D(filtered_error) = (error - filtered_error) / Td
        self.add_equation("D(filtered_error) ~ (error - filtered_error) / Td")

        # 4. PID output: u = Kp*e + integral + Kd*(e - filtered_error)/Td
        # Fast first-order tracking to avoid algebraic loops
        self.add_equation(
            "D(output) ~ (Kp * error + integral + Kd * (error - filtered_error) / Td - output) / tau_out"
        )

    def set_gains(self, Kp: Optional[float] = None, Ki: Optional[float] = None,
                  Kd: Optional[float] = None) -> 'PID':
        """
        Update PID gains without recompilation.

        Args:
            Kp: Proportional gain (optional)
            Ki: Integral gain (optional)
            Kd: Derivative gain (optional)

        Returns:
            self (for method chaining)

        Example:
            >>> pid.set_gains(Kp=3.0, Ki=0.8)
        """
        if Kp is not None:
            self.update_param("Kp", Kp)
        if Ki is not None:
            self.update_param("Ki", Ki)
        if Kd is not None:
            self.update_param("Kd", Kd)
        return self

    def get_gains(self) -> dict:
        """
        Get current PID gains.

        Returns:
            Dictionary with Kp, Ki, Kd values

        Example:
            >>> gains = pid.get_gains()
            >>> print(f"Kp={gains['Kp']}, Ki={gains['Ki']}, Kd={gains['Kd']}")
        """
        param_map = self.get_param_map()
        return {
            'Kp': param_map.get('Kp', 0.0),
            'Ki': param_map.get('Ki', 0.0),
            'Kd': param_map.get('Kd', 0.0)
        }


class Integrator(Module):
    """
    Pure integrator block.

    Computes the integral of the input signal: output = ∫input dt

    Parameters:
        - initial_value: Initial value of the integral

    Input:
        - input: Input signal [algebraic]

    Output:
        - output: Integral of input [differential state]

    Example:
        >>> integrator = Integrator(initial_value=0.0)
        >>> system.connect(velocity >> integrator)  # Get position from velocity
    """

    def __init__(self, name: str = "integrator", initial_value: float = 0.0):
        """
        Initialize an Integrator block.

        Args:
            name: Name of the module
            initial_value: Initial value of the integral
        """
        super().__init__(name, input_var="input", output_var="output")

        # States
        self.add_state("input", 0.0)                # Input [ALGEBRAIC]
        self.add_state("output", initial_value)     # Output [DIFFERENTIAL]

        # Equations
        # Input: no differential equation (algebraic)
        # Output: D(output) = input
        self.add_equation("D(output) ~ input")


class Derivative(Module):
    """
    Derivative block with filtering.

    Computes the filtered derivative of the input signal: output ≈ d(input)/dt

    Uses a first-order low-pass filter to avoid amplifying noise.

    Parameters:
        - filter_time: Time constant for derivative filter (seconds)

    Input:
        - input: Input signal [algebraic]

    Output:
        - output: Filtered derivative of input [algebraic]

    Internal States:
        - filtered_input: Filtered input [differential]

    Example:
        >>> derivative = Derivative(filter_time=0.01)
        >>> system.connect(position >> derivative)  # Get velocity from position
    """

    def __init__(self, name: str = "derivative", filter_time: float = 0.01):
        """
        Initialize a Derivative block.

        Args:
            name: Name of the module
            filter_time: Time constant for low-pass filter (seconds)
        """
        super().__init__(name, input_var="input", output_var="output")

        # States
        self.add_state("input", 0.0)              # Input [NO equation - from connection]
        self.add_state("filtered_input", 0.0)     # Filtered input [DIFFERENTIAL]
        self.add_state("output", 0.0)             # Output [DIFFERENTIAL - fast tracking]

        # Parameters
        self.add_parameter("Td", filter_time)
        self.add_parameter("tau_out", 1e-6)       # Fast output response

        # Equations
        # Input: NO equation - determined by connections

        # First-order filter on input
        self.add_equation("D(filtered_input) ~ (input - filtered_input) / Td")

        # Derivative output: fast first-order tracking of (input - filtered_input) / Td
        # This avoids algebraic loops while still being nearly instantaneous
        self.add_equation("D(output) ~ ((input - filtered_input) / Td - output) / tau_out")


class Limiter(Module):
    """
    Signal limiter (saturation) block.

    Limits the input signal to the range [min_value, max_value].

    Uses smooth saturation via tanh for numerical stability.

    Parameters:
        - min_value: Minimum output value
        - max_value: Maximum output value

    Input:
        - input: Input signal [algebraic]

    Output:
        - output: Limited signal [algebraic]

    Example:
        >>> limiter = Limiter(min_value=-10.0, max_value=10.0)
        >>> system.connect(controller >> limiter >> actuator)
    """

    def __init__(
        self,
        name: str = "limiter",
        min_value: float = -1.0,
        max_value: float = 1.0
    ):
        """
        Initialize a Limiter block.

        Args:
            name: Name of the module
            min_value: Minimum output value
            max_value: Maximum output value
        """
        super().__init__(name, input_var="input", output_var="output")

        # States
        self.add_state("input", 0.0)      # Input [NO equation - from connection]
        self.add_state("output", 0.0)     # Output [DIFFERENTIAL - fast tracking]

        # Parameters
        self.add_parameter("min_val", min_value)
        self.add_parameter("max_val", max_value)
        self.add_parameter("mid_val", (max_value + min_value) / 2)
        self.add_parameter("range_val", (max_value - min_value) / 2)
        self.add_parameter("tau", 1e-6)   # Fast response time

        # Equations
        # Input: NO equation - determined by connections

        # Smooth saturation using tanh with fast first-order tracking:
        # output tracks: mid + range * tanh((input - mid) / range)
        # This avoids algebraic loops while still being nearly instantaneous
        self.add_equation(
            "D(output) ~ ((mid_val + range_val * tanh((input - mid_val) / range_val)) - output) / tau"
        )


# Convenience functions
def create_gain(K: float, name: str = "gain") -> Gain:
    """Create a Gain block with specified gain."""
    return Gain(name=name, K=K)


def create_sum(num_inputs: int = 2, signs: Optional[List[int]] = None,
               name: str = "sum") -> Sum:
    """Create a Sum block with specified inputs and signs."""
    return Sum(name=name, num_inputs=num_inputs, signs=signs)


def create_pid(Kp: float = 1.0, Ki: float = 0.0, Kd: float = 0.0,
               name: str = "pid") -> PID:
    """Create a PID controller with specified gains."""
    return PID(name=name, Kp=Kp, Ki=Ki, Kd=Kd)
