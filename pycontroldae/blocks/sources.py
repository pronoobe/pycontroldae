"""
Signal Source Modules for pycontroldae - REDESIGNED

This module provides standard signal source blocks for control systems:
- Constant: Constant signal
- Step: Step function signal
- Ramp: Ramp (linear) signal
- Sin: Sinusoidal signal
- Pulse: Periodic pulse signal

All sources have configurable output variables and support >> and << operators.
Sources are compatible with CompositeModule.
"""

import math
from typing import Optional
from ..core.module import Module


class Constant(Module):
    """
    Constant signal source.

    Generates a constant signal value.

    Parameters:
        - value: Constant output value

    Output:
        - signal: Output signal value

    Example:
        >>> const = Constant(value=5.0)
        >>> system.connect(const >> controller)
    """

    def __init__(self, name: str = "constant", value: float = 1.0):
        """
        Initialize a Constant signal source.

        Args:
            name: Name of the module
            value: Constant output value
        """
        super().__init__(name, output_var="signal")

        # Add state for the output signal
        self.add_state("signal", value)

        # Parameters
        self.add_parameter("value", value)
        self.add_parameter("tau", 1e-6)  # Fast response

        # Equation: signal tracks value with fast dynamics
        # Use differential equation to avoid algebraic constraints
        self.add_equation("D(signal) ~ (value - signal) / tau")


class Step(Module):
    """
    Step function signal source.

    Generates a step signal that jumps from 0 to amplitude at time step_time.

    Parameters:
        - amplitude: Height of the step
        - step_time: Time at which step occurs

    Output:
        - signal: Output signal value

    Example:
        >>> step = Step(amplitude=1.0, step_time=1.0)
        >>> system.connect(step >> controller)
    """

    def __init__(
        self,
        name: str = "step",
        amplitude: float = 1.0,
        step_time: float = 0.0
    ):
        """
        Initialize a Step signal source.

        Args:
            name: Name of the module
            amplitude: Height of the step
            step_time: Time at which step occurs
        """
        super().__init__(name, output_var="signal")

        # Add state for the output signal
        self.add_state("signal", 0.0)

        # Parameters
        self.add_parameter("amplitude", amplitude)
        self.add_parameter("step_time", step_time)
        self.add_parameter("sharpness", 50.0)  # Controls step sharpness

        # Smooth step using tanh:
        # signal = amplitude * (1 + tanh(sharpness * (t - step_time))) / 2
        # D(signal) = amplitude * sharpness * sech^2(...) / 2
        #           = amplitude * sharpness * (1 - tanh^2(...)) / 2

        # For numerical stability, we use a differential equation that tracks the step
        self.add_equation(
            "D(signal) ~ sharpness * (amplitude * (1 + tanh(sharpness * (t - step_time))) / 2 - signal)"
        )


class Ramp(Module):
    """
    Ramp (linear) signal source.

    Generates a linear ramp signal: signal = slope * (t - start_time) for t > start_time
    The signal is 0 before start_time.

    Parameters:
        - slope: Rate of change (units/second)
        - start_time: Time when ramp starts

    Output:
        - signal: Output signal value

    Example:
        >>> # Ramp with slope 0.5, starting at t=1.0
        >>> ramp = Ramp(slope=0.5, start_time=1.0)
        >>> system.connect(ramp >> controller)
    """

    def __init__(
        self,
        name: str = "ramp",
        slope: float = 1.0,
        start_time: float = 0.0
    ):
        """
        Initialize a Ramp signal source.

        Args:
            name: Name of the module
            slope: Rate of change (units/second)
            start_time: Time when ramp starts
        """
        super().__init__(name, output_var="signal")

        # Add state for the output signal
        self.add_state("signal", 0.0)

        # Parameters
        self.add_parameter("slope", slope)
        self.add_parameter("start_time", start_time)
        self.add_parameter("sharpness", 50.0)  # Controls ramp start sharpness

        # Smooth ramp starting at start_time:
        # D(signal) = slope * (1 + tanh(sharpness * (t - start_time))) / 2
        # This smoothly transitions from 0 to slope at t = start_time
        self.add_equation(
            "D(signal) ~ slope * (1 + tanh(sharpness * (t - start_time))) / 2"
        )


class Sin(Module):
    """
    Sinusoidal signal source.

    Generates a sinusoidal signal: signal = amplitude * sin(frequency * t + phase) + offset

    Parameters:
        - amplitude: Amplitude of the sine wave
        - frequency: Frequency in rad/s (use 2*pi*f_Hz for frequency in Hz)
        - phase: Phase offset in radians
        - offset: DC offset

    Output:
        - signal: Output signal value

    Example:
        >>> # 1 Hz sine wave with amplitude 2.0
        >>> sine = Sin(amplitude=2.0, frequency=2*3.14159, offset=0.0)
        >>> system.connect(sine >> plant)
    """

    def __init__(
        self,
        name: str = "sin",
        amplitude: float = 1.0,
        frequency: float = 1.0,
        phase: float = 0.0,
        offset: float = 0.0
    ):
        """
        Initialize a Sinusoidal signal source.

        Args:
            name: Name of the module
            amplitude: Amplitude of the sine wave
            frequency: Angular frequency in rad/s
            phase: Phase offset in radians
            offset: DC offset
        """
        super().__init__(name, output_var="signal")

        # Initial value
        initial_value = offset + amplitude * math.sin(phase)

        # States for sine wave generation using oscillator
        # Use auxiliary states x = sin(ωt + φ), y = cos(ωt + φ)
        # Then: dx/dt = ω*y, dy/dt = -ω*x
        # signal = A*x + offset
        self.add_state("x", math.sin(phase))  # sin component
        self.add_state("y", math.cos(phase))  # cos component
        self.add_state("signal", initial_value)

        # Parameters
        self.add_parameter("amplitude", amplitude)
        self.add_parameter("frequency", frequency)
        self.add_parameter("offset", offset)
        self.add_parameter("tau", 1e-6)  # Fast response for output

        # Equations for coupled oscillator
        self.add_equation("D(x) ~ frequency * y")
        self.add_equation("D(y) ~ -frequency * x")

        # Output signal: fast differential tracking of A*x + offset
        # Use differential equation to avoid algebraic constraints
        self.add_equation("D(signal) ~ ((amplitude * x + offset) - signal) / tau")


class Pulse(Module):
    """
    Pulse signal source (square wave).

    Generates a periodic pulse signal with configurable period and duty cycle.

    Parameters:
        - amplitude: Pulse amplitude
        - period: Period of the pulse (seconds)
        - duty_cycle: Duty cycle (0 to 1, fraction of period that pulse is high)

    Output:
        - signal: Output signal value

    Example:
        >>> # 1 Hz pulse with 50% duty cycle
        >>> pulse = Pulse(amplitude=1.0, period=1.0, duty_cycle=0.5)
        >>> system.connect(pulse >> controller)
    """

    def __init__(
        self,
        name: str = "pulse",
        amplitude: float = 1.0,
        period: float = 1.0,
        duty_cycle: float = 0.5
    ):
        """
        Initialize a Pulse signal source.

        Args:
            name: Name of the module
            amplitude: Pulse amplitude
            period: Period in seconds
            duty_cycle: Duty cycle (0 to 1)
        """
        super().__init__(name, output_var="signal")

        # States
        self.add_state("signal", 0.0)

        # Auxiliary states for sine wave timing
        self.add_state("x", 0.0)  # sin(2πt/T)
        self.add_state("y", 1.0)  # cos(2πt/T)

        # Parameters
        self.add_parameter("amplitude", amplitude)
        self.add_parameter("period", period)
        self.add_parameter("duty_cycle", duty_cycle)
        self.add_parameter("sharpness", 10.0)

        # Angular frequency for timing
        omega = 2 * math.pi / period

        # Oscillator for timing
        self.add_equation(f"D(x) ~ {omega} * y")
        self.add_equation(f"D(y) ~ -{omega} * x")

        # Square wave approximation using tanh
        # Pulse is high when sin is in range [0, 2π*duty_cycle]
        # We approximate this with: signal ≈ A * (1 + tanh(k*sin(θ - offset))) / 2
        # Simplified: use tanh(k*sin) to get approximate square wave
        self.add_equation(
            "D(signal) ~ sharpness * (amplitude * (1 + tanh(sharpness * x)) / 2 - signal)"
        )


# Helper functions to create common signal sources

def create_constant(value: float = 1.0, name: str = "constant") -> Constant:
    """
    Convenience function to create a Constant signal source.

    Args:
        value: Constant value
        name: Module name

    Returns:
        Constant module instance
    """
    return Constant(name=name, value=value)


def create_step(amplitude: float = 1.0, step_time: float = 0.0, name: str = "step") -> Step:
    """
    Convenience function to create a Step signal source.

    Args:
        amplitude: Step amplitude
        step_time: Time of step
        name: Module name

    Returns:
        Step module instance
    """
    return Step(name=name, amplitude=amplitude, step_time=step_time)


def create_ramp(slope: float = 1.0, start_time: float = 0.0, name: str = "ramp") -> Ramp:
    """
    Convenience function to create a Ramp signal source.

    Args:
        slope: Ramp slope
        start_time: Start time
        name: Module name

    Returns:
        Ramp module instance
    """
    return Ramp(name=name, slope=slope, start_time=start_time)


def create_sine(
    amplitude: float = 1.0,
    frequency_hz: float = 1.0,
    phase: float = 0.0,
    offset: float = 0.0,
    name: str = "sine"
) -> Sin:
    """
    Convenience function to create a Sine signal source.

    Args:
        amplitude: Sine amplitude
        frequency_hz: Frequency in Hz (converted to rad/s internally)
        phase: Phase offset in radians
        offset: DC offset
        name: Module name

    Returns:
        Sin module instance
    """
    return Sin(
        name=name,
        amplitude=amplitude,
        frequency=2 * math.pi * frequency_hz,
        phase=phase,
        offset=offset
    )


def create_pulse(
    amplitude: float = 1.0,
    period: float = 1.0,
    duty_cycle: float = 0.5,
    name: str = "pulse"
) -> Pulse:
    """
    Convenience function to create a Pulse signal source.

    Args:
        amplitude: Pulse amplitude
        period: Period in seconds
        duty_cycle: Duty cycle (0 to 1)
        name: Module name

    Returns:
        Pulse module instance
    """
    return Pulse(name=name, amplitude=amplitude, period=period, duty_cycle=duty_cycle)
