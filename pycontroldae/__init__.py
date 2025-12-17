"""
pycontroldae - Python Control System Modeling and Simulation Library

A powerful Python library for building, simulating, and analyzing control systems.
Combines Python's ease of use with Julia's high-performance computing capabilities.

Core Features:
- Modular design with hierarchical module system
- Rich control block library (PID, StateSpace, etc.)
- Advanced simulation with event system
- Flexible data export and analysis tools

Example:
    >>> from pycontroldae.blocks import PID, Step, StateSpace
    >>> from pycontroldae.core import System, Simulator
    >>> import numpy as np
    >>>
    >>> # Create a simple control system
    >>> setpoint = Step(name="sp", amplitude=10.0, step_time=0.0)
    >>> setpoint.set_output("signal")
    >>> pid = PID(name="pid", Kp=2.0, Ki=0.5, Kd=0.1)
    >>> plant = StateSpace(name="plant",
    ...                    A=np.array([[-1.0]]),
    ...                    B=np.array([[1.0]]),
    ...                    C=np.array([[1.0]]),
    ...                    D=np.array([[0.0]]))
    >>>
    >>> system = System("control_system")
    >>> system.add_module(setpoint)
    >>> system.add_module(pid)
    >>> system.add_module(plant)
    >>> system.connect("sp.signal ~ pid.error")
    >>> system.connect("pid.output ~ plant.u1")
    >>> system.compile()
    >>>
    >>> simulator = Simulator(system)
    >>> result = simulator.run(t_span=(0.0, 10.0), dt=0.1)
"""

__version__ = "0.1.0"
__author__ = "PyControlDAE Contributors"
__license__ = "MIT"

# Import main modules for easier access
from .core import (
    Module,
    CompositeModule,
    System,
    Simulator,
    SimulationResult,
    DataProbe,
    TimeEvent,
    ContinuousEvent,
    at_time,
    when_condition,
    get_jl,
)

from .blocks import (
    # Signal sources
    Step,
    Sin,
    Ramp,
    Constant,
    Pulse,
    # Basic control blocks
    Gain,
    Sum,
    PID,
    Integrator,
    Derivative,
    Limiter,
    # Linear systems
    StateSpace,
)

__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__license__',

    # Core classes
    'Module',
    'CompositeModule',
    'System',
    'Simulator',
    'SimulationResult',
    'DataProbe',

    # Events
    'TimeEvent',
    'ContinuousEvent',
    'at_time',
    'when_condition',

    # Julia backend
    'get_jl',

    # Signal sources
    'Step',
    'Sin',
    'Ramp',
    'Constant',
    'Pulse',

    # Basic control blocks
    'Gain',
    'Sum',
    'PID',
    'Integrator',
    'Derivative',
    'Limiter',

    # Linear systems
    'StateSpace',
]
