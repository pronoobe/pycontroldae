"""
Port System for pycontroldae

Provides Port objects for type-safe, IDE-friendly connections between modules.

Features:
- Port objects represent module inputs/outputs
- Support >> and << operators for connections
- Enable IDE autocomplete and type checking
- Backward compatible with string-based connections
"""

from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .module import Module

class Port:
    """
    Represents an input or output port of a module.

    Ports enable type-safe connections between modules using >> and << operators.

    Attributes:
        module: The module this port belongs to
        name: Port name (e.g., "input", "output", "error")
        is_input: True if this is an input port, False for output

    Example:
        >>> pid = PID("pid", Kp=2.0, Ki=0.5, Kd=0.0)
        >>> plant = StateSpace("plant", A, B, C, D)
        >>>
        >>> # Connect using >> operator
        >>> pid.output >> plant.u1
        >>>
        >>> # Or using << operator
        >>> plant.u1 << pid.output
    """

    def __init__(self, module: 'Module', name: str, is_input: bool = True):
        """
        Initialize a Port.

        Args:
            module: The module this port belongs to
            name: Port name
            is_input: True for input port, False for output port
        """
        self.module = module
        self.name = name
        self.is_input = is_input
        self._full_name = None  # Lazy evaluation

    @property
    def full_name(self) -> str:
        """
        Get the full qualified name of this port.

        Returns:
            String like "module_name.port_name"
        """
        if self._full_name is None:
            self._full_name = f"{self.module.name}.{self.name}"
        return self._full_name

    def __rshift__(self, other: Union['Port', 'Module']) -> 'Connection':
        """
        Connect this port to another using >> operator.

        Args:
            other: Target Port or Module (will use default input)

        Returns:
            Connection object for chaining

        Example:
            >>> source.output >> pid.error
            >>> source.output >> pid  # Uses pid's default input
        """
        from .module import Module

        # Handle Module with default input
        if isinstance(other, Module):
            if other._input_var is None:
                raise ValueError(
                    f"Module '{other.name}' has no default input port. "
                    f"Use explicit port: {other.name}.port_name"
                )
            other = other._input_var

        if not isinstance(other, Port):
            raise TypeError(
                f"Can only connect Port to Port or Module, got {type(other)}"
            )

        # Create connection
        return Connection(self, other)

    def __lshift__(self, other: Union['Port', 'Module']) -> 'Connection':
        """
        Connect another port to this port using << operator.

        Args:
            other: Source Port or Module (will use default output)

        Returns:
            Connection object for chaining

        Example:
            >>> pid.error << source.output
            >>> pid << source  # Uses source's default output
        """
        from .module import Module

        # Handle Module with default output
        if isinstance(other, Module):
            if other._output_var is None:
                raise ValueError(
                    f"Module '{other.name}' has no default output port. "
                    f"Use explicit port: {other.name}.port_name"
                )
            other = other._output_var

        if not isinstance(other, Port):
            raise TypeError(
                f"Can only connect Port to Port or Module, got {type(other)}"
            )

        # Create connection (reversed direction)
        return Connection(other, self)

    def __str__(self) -> str:
        """String representation returns full qualified name."""
        return self.full_name

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        port_type = "input" if self.is_input else "output"
        return f"Port({port_type}: {self.full_name})"


class Connection:
    """
    Represents a connection between two ports.

    Connections are created by >> or << operators and can be chained.
    They are convertible to Julia connection strings.

    Attributes:
        source: Source Port
        target: Target Port

    Example:
        >>> conn = pid.output >> plant.u1
        >>> # Chain connections
        >>> conn >> controller.input
    """

    def __init__(self, source: Port, target: Port):
        """
        Initialize a Connection.

        Args:
            source: Source port
            target: Target port
        """
        if not isinstance(source, Port):
            raise TypeError(f"source must be Port, got {type(source)}")
        if not isinstance(target, Port):
            raise TypeError(f"target must be Port, got {type(target)}")

        self.source = source
        self.target = target

    @property
    def expr(self) -> str:
        """
        Get Julia connection expression.

        Returns:
            String like "module1.output ~ module2.input"
        """
        return f"{self.source.full_name} ~ {self.target.full_name}"

    def __rshift__(self, other: Union[Port, 'Module']) -> 'Connection':
        """
        Chain another connection using >> operator.

        Args:
            other: Next target Port or Module

        Returns:
            New Connection from previous target to new target

        Example:
            >>> source.output >> pid.error >> controller.input
        """
        from .module import Module

        # Handle Module with default input
        if isinstance(other, Module):
            if other._input_var is None:
                raise ValueError(
                    f"Module '{other.name}' has no default input port"
                )
            other = other._input_var

        if not isinstance(other, Port):
            raise TypeError(f"Can only chain to Port or Module, got {type(other)}")

        # Return new connection from current target to new target
        return Connection(self.target, other)

    def __lshift__(self, other: Union[Port, 'Module']) -> 'Connection':
        """
        Chain another connection using << operator (reversed).

        Args:
            other: Previous source Port or Module

        Returns:
            New Connection from new source to previous source

        Example:
            >>> plant.u1 << pid.output << error.output
        """
        from .module import Module

        # Handle Module with default output
        if isinstance(other, Module):
            if other._output_var is None:
                raise ValueError(
                    f"Module '{other.name}' has no default output port"
                )
            other = other._output_var

        if not isinstance(other, Port):
            raise TypeError(f"Can only chain to Port or Module, got {type(other)}")

        # Return new connection from new source to current source
        return Connection(other, self.source)

    def __str__(self) -> str:
        """String representation returns Julia expression."""
        return self.expr

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"Connection({self.source} >> {self.target})"
