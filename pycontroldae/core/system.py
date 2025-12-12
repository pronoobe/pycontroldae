"""
System Class for pycontroldae

This module provides the System class which orchestrates multiple Module objects,
manages connections between them, and compiles them into a simplified Julia ODESystem
using structural_simplify for automatic DAE index reduction.

Enhanced features:
- Support for connection operators (<<, >>) from Module class
- Event system for time-based and condition-based callbacks
"""

from typing import List, Any, Optional, Union, Tuple
from .backend import get_jl
from .module import Module
from .port import Port, Connection
from .events import TimeEvent, ContinuousEvent


class System:
    """
    A system that composes multiple modules with connections.

    The System class manages multiple Module objects, allows defining connections
    between them, and compiles everything into a single Julia ODESystem with
    automatic structural simplification for DAE index reduction.

    Enhanced Features:
    - Accepts connection tuples from Module operators (<<, >>)
    - Automatic module registration from connection operators

    Example:
        >>> rc = Module("rc").add_state("V", 0.0).add_param("R", 1000.0)
        >>> rc.add_param("C", 1e-6).add_equation("D(V) ~ (I - V/R)/C")
        >>>
        >>> input_src = Module("input").add_state("signal", 0.0)
        >>> input_src.add_equation("D(signal) ~ 0")
        >>>
        >>> sys = System("rc_system")
        >>> sys.add_module(rc).add_module(input_src)
        >>> sys.connect("input.signal ~ rc.I")
        >>> # Or use connection operators:
        >>> sys.connect(input_src >> rc)
        >>> simplified = sys.compile()
    """

    def __init__(self, name: str = "system"):
        """
        Initialize a new System.

        Args:
            name: The name of the system (default: "system")
        """
        self.name = name
        self._modules: List[Module] = []
        self._connections: List[str] = []
        self._compiled_system: Optional[Any] = None
        self._events: List[Union[TimeEvent, ContinuousEvent]] = []

    def add_module(self, module: Module) -> 'System':
        """
        Add a module to this system.

        Args:
            module: A Module instance to add to the system

        Returns:
            self (for method chaining)

        Raises:
            TypeError: If module is not a Module instance
        """
        if not isinstance(module, Module):
            raise TypeError(f"Expected Module instance, got {type(module)}")

        self._modules.append(module)
        return self

    def connect(self, connection: Union[str, Connection, Tuple[Module, Module, str]]) -> 'System':
        """
        Add a connection between module variables.

        This method accepts multiple formats:
        1. String-based: "mod1.output ~ mod2.input"
        2. Connection object: From port1 >> port2 or module1 >> module2
        3. Tuple from old operators: (module1, module2, connection_string) [deprecated]

        Args:
            connection: Connection string, Connection object, or tuple

        Returns:
            self (for method chaining)

        Raises:
            TypeError: If connection format is invalid

        Examples:
            >>> # String-based connection (backward compatible)
            >>> system.connect("input.signal ~ rc_circuit.I")
            >>>
            >>> # Using Port objects (new, recommended)
            >>> system.connect(input_module.output >> rc.input)
            >>>
            >>> # Using Module operators with default ports
            >>> system.connect(input_module >> rc)
            >>>
            >>> # Chaining connections
            >>> system.connect(source >> pid >> plant)
        """
        if isinstance(connection, str):
            # String-based connection (backward compatible)
            self._connections.append(connection)
        elif isinstance(connection, Connection):
            # New Port-based connection
            self._connections.append(connection.expr)
        elif isinstance(connection, tuple) and len(connection) == 3:
            # Old-style tuple from operators (deprecated but still supported)
            mod1, mod2, conn_str = connection

            # Automatically add modules if not already present
            if mod1 not in self._modules:
                self._modules.append(mod1)
            if mod2 not in self._modules:
                self._modules.append(mod2)

            # Add the connection string
            self._connections.append(conn_str)
        else:
            raise TypeError(
                f"Expected str, Connection, or tuple from Module operators, got {type(connection)}"
            )

        return self

    def add_event(self, event: Union[TimeEvent, ContinuousEvent]) -> 'System':
        """
        Add an event to the system.

        Events allow dynamic modification of system parameters during simulation.

        Args:
            event: A TimeEvent or ContinuousEvent instance

        Returns:
            self (for method chaining)

        Raises:
            TypeError: If event is not a valid event type

        Examples:
            >>> # Time-based event
            >>> from pycontroldae.core.events import at_time
            >>> def change_gain(integrator):
            ...     return {"pid.Kp": 5.0}
            >>> system.add_event(at_time(2.0, change_gain))
            >>>
            >>> # Condition-based event
            >>> from pycontroldae.core.events import when_condition
            >>> def check_threshold(u, t, integrator):
            ...     return u[0] - 10.0  # Trigger when state[0] > 10
            >>> def apply_limit(integrator):
            ...     return {"controller.output_limit": 5.0}
            >>> system.add_event(when_condition(check_threshold, apply_limit))
        """
        if not isinstance(event, (TimeEvent, ContinuousEvent)):
            raise TypeError(
                f"Expected TimeEvent or ContinuousEvent, got {type(event)}"
            )

        self._events.append(event)
        return self

    def clear_events(self) -> 'System':
        """
        Clear all registered events.

        Returns:
            self (for method chaining)
        """
        self._events = []
        return self

    @property
    def events(self) -> List[Union[TimeEvent, ContinuousEvent]]:
        """Get the list of registered events."""
        return self._events.copy()

    def compile(self) -> Any:
        """
        Compile the system into a simplified Julia ODESystem.

        This method:
        1. Builds all modules (if not already built)
        2. Composes all modules into a single system
        3. Applies structural_simplify (CRITICAL for DAE index reduction)
        4. Returns the simplified Julia ODESystem

        Returns:
            A simplified Julia ODESystem object

        Raises:
            ValueError: If no modules have been added
            RuntimeError: If composition or structural_simplify fails

        Note:
            structural_simplify is critical for:
            - DAE index reduction (converts high-index DAEs to lower-index/ODEs)
            - Algebraic elimination (removes purely algebraic equations)
            - Structural analysis (detects and resolves singularities)
            - Optimization (simplifies equations for faster solving)
        """
        # Validation
        if not self._modules:
            raise ValueError(f"System '{self.name}' has no modules added")

        jl = get_jl()

        try:
            # Build all modules if not already built
            for module in self._modules:
                if module._julia_system is None:
                    module.build()

            # Get Julia system names
            systems_str = ", ".join([mod.name for mod in self._modules])

            # Compose the system with or without connections
            if self._connections:
                # Build connections array
                connections_str = ", ".join(self._connections)
                jl.seval(f"_connections_{self.name} = [{connections_str}]")

                # Create composed system with connections
                compose_expr = (
                    f"@named {self.name} = ODESystem("
                    f"_connections_{self.name}, t; systems=[{systems_str}])"
                )
            else:
                # Create composed system without connections (use Equation[] for empty equation list)
                compose_expr = (
                    f"@named {self.name} = ODESystem(Equation[], t; systems=[{systems_str}])"
                )

            # Create the composed system
            jl.seval(compose_expr)

            # CRITICAL: Apply structural_simplify for DAE index reduction
            jl.seval(f"_simplified_{self.name} = structural_simplify({self.name})")

            # Retrieve and cache the simplified system
            self._compiled_system = jl.seval(f"_simplified_{self.name}")

            return self._compiled_system

        except Exception as e:
            # Provide helpful error messages
            if "connection" in str(e).lower():
                raise RuntimeError(
                    f"Failed to compose system '{self.name}': {e}\n"
                    f"Check that all module variables referenced in connections exist"
                ) from e
            elif "simplify" in str(e).lower():
                raise RuntimeError(
                    f"structural_simplify failed for system '{self.name}': {e}\n"
                    f"System may have structural singularities or unsolvable constraints"
                ) from e
            else:
                raise RuntimeError(
                    f"Failed to compile system '{self.name}': {e}"
                ) from e

    @property
    def compiled_system(self) -> Any:
        """
        Get the compiled simplified Julia ODESystem.

        Returns:
            The simplified Julia ODESystem object

        Raises:
            RuntimeError: If compile() has not been called yet
        """
        if self._compiled_system is None:
            raise RuntimeError(
                f"System '{self.name}' has not been compiled yet. Call compile() first."
            )
        return self._compiled_system

    @property
    def modules(self) -> List[Module]:
        """Get the list of modules."""
        return self._modules.copy()

    @property
    def connections(self) -> List[str]:
        """Get the list of connection expressions."""
        return self._connections.copy()

    def __repr__(self) -> str:
        return (
            f"System(name='{self.name}', "
            f"modules={len(self._modules)}, "
            f"connections={len(self._connections)})"
        )
