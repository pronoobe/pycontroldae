"""
Core modules for pycontroldae

Exports the main classes for building and simulating control systems.
"""

from .backend import JuliaBackend, get_jl
from .module import Module
from .port import Port, Connection
from .composite import CompositeModule, create_composite
from .system import System
from .simulator import Simulator
from .events import TimeEvent, ContinuousEvent, at_time, when_condition
from .result import SimulationResult, DataProbe

__all__ = [
    'JuliaBackend',
    'get_jl',
    'Module',
    'Port',
    'Connection',
    'CompositeModule',
    'create_composite',
    'System',
    'Simulator',
    'TimeEvent',
    'ContinuousEvent',
    'at_time',
    'when_condition',
    'SimulationResult',
    'DataProbe',
]
