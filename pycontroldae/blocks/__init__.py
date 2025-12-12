"""
Control System Building Blocks for pycontroldae

This package provides pre-built modules for common control system components:

Signal Sources (blocks.sources):
    - Step: Step function signal
    - Sin: Sinusoidal signal
    - Ramp: Linear ramp signal
    - Constant: Constant signal
    - Pulse: Periodic pulse signal

Basic Control Blocks (blocks.basic):
    - Gain: Proportional amplifier
    - Sum: Summing junction (adder/subtractor)
    - PID: PID controller
    - Integrator: Pure integrator
    - Derivative: Filtered derivative
    - Limiter: Signal saturation

Example:
    >>> from pycontroldae.blocks import Step, PID, Gain
    >>> from pycontroldae.core import System, Simulator
    >>>
    >>> # Create components
    >>> setpoint = Step(amplitude=1.0)
    >>> controller = PID(Kp=2.0, Ki=0.5, Kd=0.1)
    >>> plant = Gain(K=1.5)
    >>>
    >>> # Connect and simulate
    >>> system = System()
    >>> system.connect(setpoint >> controller >> plant)
    >>> system.compile()
"""

from .sources import (
    Step,
    Sin,
    Ramp,
    Constant,
    Pulse,
    create_step,
    create_sine,
    create_ramp
)

from .basic import (
    Gain,
    Sum,
    PID,
    Integrator,
    Derivative,
    Limiter,
    create_gain,
    create_sum,
    create_pid
)

from .linear import (
    StateSpace,
    create_state_space
)

__all__ = [
    # Signal sources
    'Step',
    'Sin',
    'Ramp',
    'Constant',
    'Pulse',
    'create_step',
    'create_sine',
    'create_ramp',

    # Basic control blocks
    'Gain',
    'Sum',
    'PID',
    'Integrator',
    'Derivative',
    'Limiter',
    'create_gain',
    'create_sum',
    'create_pid',

    # Linear systems
    'StateSpace',
    'create_state_space',
]
