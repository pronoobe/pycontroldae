"""
Module Class for pycontroldae

This module provides the Module class which represents a modular component
in the control system. Each Module can have states, parameters, and equations,
and is compiled to a Julia ODESystem.

Enhanced features:
- Parameter and state default value tracking for runtime modification
- get_param_map() for dynamic parameter updates without recompilation
- Connection operators (<< and >>) for intuitive module composition
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from .backend import get_jl
from .port import Port, Connection


class Module:
    """
    A modular component that can be compiled to a Julia ODESystem.

    The Module class allows defining states, parameters, and differential equations
    in Python, which are then automatically translated to Julia ModelingToolkit syntax.

    Enhanced Features:
    - Stores default values for parameters and states
    - get_param_map() returns Julia symbol -> Python value mapping
    - Connection operators: a << b (a's input from b's output)
    - Connection operators: a >> b (a's output to b's input)

    Example:
        >>> rc = Module("RC")
        >>> rc.add_state("v", 0.0)  # Voltage across capacitor
        >>> rc.add_parameter("R", 1000.0)  # Resistance
        >>> rc.add_parameter("C", 1e-6)  # Capacitance
        >>> rc.add_equation("D(v) ~ (u - v) / (R * C)")
        >>> rc_sys = rc.build()
        >>>
        >>> # Get parameter map for runtime updates
        >>> param_map = rc.get_param_map()
        >>>
        >>> # Connect modules
        >>> input_module >> rc  # input's output to rc's input
        >>> # or equivalently: rc << input_module
    """

    def __init__(self, name: str, input_var: Optional[str] = None, output_var: Optional[str] = None):
        """
        Initialize a new Module.

        Args:
            name: The name of the module (will be used as the Julia ODESystem name)
            input_var: Optional name of the primary input variable (for connection operators)
            output_var: Optional name of the primary output variable (for connection operators)
        """
        self.name = name
        self._states: Dict[str, float] = {}  # {name: default_value}
        self._params: Dict[str, float] = {}  # {name: default_value}
        self._equations: List[str] = []
        self._julia_system: Optional[Any] = None

        # Port system
        self._ports: Dict[str, Port] = {}  # {port_name: Port}
        self._input_var: Optional[Port] = None  # Default input port
        self._output_var: Optional[Port] = None  # Default output port

        # If input/output var names provided, create ports (will be finalized in build)
        self._default_input_name = input_var
        self._default_output_name = output_var

        # Store Julia symbol references after build
        self._julia_state_symbols: Dict[str, Any] = {}
        self._julia_param_symbols: Dict[str, Any] = {}

    def add_state(self, name: str, default: float = 0.0) -> 'Module':
        """
        Add a state variable to this module.

        State variables are dynamically varying quantities (e.g., voltage, current, position).
        They will be created as Julia symbolic variables using @variables.
        Default values are stored and can be used as initial conditions.

        Args:
            name: Name of the state variable
            default: Default initial value for the state (stored in Python)

        Returns:
            self (for method chaining)

        Example:
            >>> module.add_state("position", 0.0)
            >>> module.add_state("velocity", 1.5)
        """
        self._states[name] = default
        # Auto-create port for state variables
        self._create_port(name, is_input=True)  # States can be inputs
        return self

    def add_param(self, name: str, default: float) -> 'Module':
        """
        Add a parameter to this module.

        Parameters are constants (e.g., resistance, capacitance, mass).
        They will be created as Julia parameters using @parameters.
        Default values are stored in Python and can be updated without recompilation.

        Args:
            name: Name of the parameter
            default: Default value for the parameter (stored in Python)

        Returns:
            self (for method chaining)

        Example:
            >>> module.add_param("mass", 1.0)
            >>> module.add_param("damping", 0.1)
        """
        self._params[name] = default
        return self

    def add_parameter(self, name: str, default: float) -> 'Module':
        """
        Alias for add_param() for consistency with design requirements.

        Parameters are constants (e.g., resistance, capacitance, mass).
        They will be created as Julia parameters using @parameters.
        Default values are stored in Python and can be updated without recompilation.

        Args:
            name: Name of the parameter
            default: Default value for the parameter (stored in Python)

        Returns:
            self (for method chaining)

        Example:
            >>> module.add_parameter("resistance", 1000.0)
        """
        return self.add_param(name, default)

    def add_equation(self, eq_str: str) -> 'Module':
        """
        Add a differential equation to this module.

        Equations should be written in Julia ModelingToolkit syntax.
        Use D(x) for derivatives and ~ for equality.

        Args:
            eq_str: Equation string (e.g., "D(x) ~ -a*x + u")

        Returns:
            self (for method chaining)

        Example:
            >>> module.add_equation("D(v) ~ (u - v) / (R * C)")
        """
        self._equations.append(eq_str)
        return self

    def _create_port(self, name: str, is_input: bool = True) -> Port:
        """
        Create a Port object for a variable.

        Args:
            name: Variable name
            is_input: True for input port, False for output port

        Returns:
            Created Port object
        """
        if name not in self._ports:
            port = Port(self, name, is_input=is_input)
            self._ports[name] = port
            # Set as attribute for direct access
            setattr(self, name, port)
        return self._ports[name]

    def add_input(self, name: str, default: float = 0.0) -> Port:
        """
        Add an input port to this module.

        Args:
            name: Input port name
            default: Default value

        Returns:
            Created Port object

        Example:
            >>> pid = Module("pid")
            >>> error_port = pid.add_input("error", 0.0)
            >>> # Can now connect: source.output >> pid.error
        """
        self.add_state(name, default)
        port = self._create_port(name, is_input=True)
        return port

    def add_output(self, name: str, default: float = 0.0) -> Port:
        """
        Add an output port to this module.

        Args:
            name: Output port name
            default: Default value

        Returns:
            Created Port object

        Example:
            >>> pid = Module("pid")
            >>> output_port = pid.add_output("output", 0.0)
            >>> # Can now connect: pid.output >> plant.input
        """
        self.add_state(name, default)
        port = self._create_port(name, is_input=False)
        return port

    def set_input(self, var_name: str) -> 'Module':
        """
        Set the primary input variable for this module.

        This is used by the connection operators (<< and >>).

        Args:
            var_name: Name of the input variable

        Returns:
            self (for method chaining)

        Example:
            >>> rc.set_input("I")  # Current input
        """
        self._default_input_name = var_name
        if var_name in self._ports:
            self._input_var = self._ports[var_name]
        return self

    def set_output(self, var_name: str) -> 'Module':
        """
        Set the primary output variable for this module.

        This is used by the connection operators (<< and >>).

        Args:
            var_name: Name of the output variable

        Returns:
            self (for method chaining)

        Example:
            >>> rc.set_output("V")  # Voltage output
        """
        self._default_output_name = var_name
        if var_name in self._ports:
            self._output_var = self._ports[var_name]
        return self

    def build(self) -> Any:
        """
        Build the Julia ODESystem from the module definition.

        This method:
        1. Creates symbolic variables in Julia using @variables
        2. Creates parameters in Julia using @parameters
        3. Stores references to Julia symbols for get_param_map()
        4. Constructs equations
        5. Creates and returns a Julia ODESystem object

        Returns:
            A Julia ODESystem object

        Raises:
            ValueError: If there are no states or equations defined
            RuntimeError: If Julia evaluation fails
        """
        # Validation
        if not self._states:
            raise ValueError(f"Module '{self.name}' has no states defined")
        if not self._equations:
            raise ValueError(f"Module '{self.name}' has no equations defined")

        jl = get_jl()

        try:
            # Create symbolic state variables
            # Format: @variables x(t) y(t) z(t)
            state_names = list(self._states.keys())
            states_decl = " ".join([f"{name}(t)" for name in state_names])
            jl.seval(f"@variables {states_decl}")

            # Store Julia state symbol references
            # After @variables x(t), the symbol is stored as 'x' with (t) being implicit
            # We store references to the base symbols for later use
            for state_name in state_names:
                # Access the variable directly by name (without (t))
                # But we need to store it as a callable that can be used in equations
                # Store the SymbolicUtils variable object
                jl.seval(f"_sym_{state_name}_{self.name} = {state_name}")
                self._julia_state_symbols[state_name] = jl.seval(
                    f"_sym_{state_name}_{self.name}"
                )

            # Create parameters
            # Format: @parameters R C L
            if self._params:
                param_names = list(self._params.keys())
                params_decl = " ".join(param_names)
                jl.seval(f"@parameters {params_decl}")

                # Store Julia parameter symbol references
                for param_name in param_names:
                    jl.seval(f"_sym_{param_name}_{self.name} = {param_name}")
                    self._julia_param_symbols[param_name] = jl.seval(
                        f"_sym_{param_name}_{self.name}"
                    )

            # Build equations array
            # Format: eqs = [D(x) ~ -a*x, D(y) ~ x - y]
            equations_str = ", ".join(self._equations)
            jl.seval(f"_eqs_{self.name} = [{equations_str}]")

            # Create ODESystem
            # Format: @named system_name = ODESystem(eqs, t)
            jl.seval(f"@named {self.name} = ODESystem(_eqs_{self.name}, t)")

            # Get the Julia system object
            self._julia_system = jl.seval(self.name)

            # Finalize default input/output ports
            if self._default_input_name and self._default_input_name in self._ports:
                self._input_var = self._ports[self._default_input_name]
            if self._default_output_name and self._default_output_name in self._ports:
                self._output_var = self._ports[self._default_output_name]

            return self._julia_system

        except Exception as e:
            raise RuntimeError(
                f"Failed to build Julia ODESystem for module '{self.name}': {e}"
            ) from e

    def get_param_map(self) -> Dict[str, float]:
        """
        Get a mapping of parameter names to their Python default values.

        This method returns a dictionary that maps parameter names (strings)
        to their current Python default values. This mapping can be used to
        update parameter values at runtime without recompiling the system.

        Returns:
            Dictionary mapping parameter names to Python values
            {param_name: python_value}

        Raises:
            RuntimeError: If build() has not been called yet

        Example:
            >>> rc = Module("RC")
            >>> rc.add_parameter("R", 1000.0).add_parameter("C", 1e-6)
            >>> rc.add_state("V").add_equation("D(V) ~ -V/(R*C)")
            >>> rc.build()
            >>>
            >>> # Get current parameter map
            >>> param_map = rc.get_param_map()  # {'R': 1000.0, 'C': 1e-6}
            >>>
            >>> # Update parameter value
            >>> rc.update_param("R", 2000.0)
            >>> updated_map = rc.get_param_map()  # R now maps to 2000.0
        """
        if self._julia_system is None:
            raise RuntimeError(
                f"Module '{self.name}' has not been built yet. Call build() first."
            )

        # Return mapping of parameter names to Python values
        return self._params.copy()

    def get_state_map(self) -> Dict[str, float]:
        """
        Get a mapping of state names to their Python default values.

        This method returns a dictionary that maps state names (strings)
        to their current Python default values (initial conditions).

        Returns:
            Dictionary mapping state names to Python values
            {state_name: python_value}

        Raises:
            RuntimeError: If build() has not been called yet

        Example:
            >>> module.add_state("x", 1.0).add_state("v", 0.5)
            >>> module.build()
            >>> state_map = module.get_state_map()  # {'x': 1.0, 'v': 0.5}
        """
        if self._julia_system is None:
            raise RuntimeError(
                f"Module '{self.name}' has not been built yet. Call build() first."
            )

        # Return mapping of state names to Python values
        return self._states.copy()

    def update_param(self, name: str, value: float) -> 'Module':
        """
        Update a parameter's default value (without recompilation).

        This updates the Python-side default value, which will be reflected
        in subsequent calls to get_param_map().

        Args:
            name: Name of the parameter to update
            value: New value for the parameter

        Returns:
            self (for method chaining)

        Raises:
            KeyError: If parameter does not exist

        Example:
            >>> rc.update_param("R", 2000.0)  # Change resistance
            >>> rc.update_param("C", 2e-6)     # Change capacitance
        """
        if name not in self._params:
            raise KeyError(f"Parameter '{name}' does not exist in module '{self.name}'")

        self._params[name] = value
        return self

    def update_state(self, name: str, value: float) -> 'Module':
        """
        Update a state's default initial value.

        This updates the Python-side default value, which will be used
        as the initial condition in subsequent simulations.

        Args:
            name: Name of the state to update
            value: New initial value for the state

        Returns:
            self (for method chaining)

        Raises:
            KeyError: If state does not exist

        Example:
            >>> module.update_state("position", 5.0)
        """
        if name not in self._states:
            raise KeyError(f"State '{name}' does not exist in module '{self.name}'")

        self._states[name] = value
        return self

    def __lshift__(self, other: Union['Module', Port]) -> Connection:
        """
        Connection operator: self << other

        Means: self's input comes from other's output
        Equivalent to: connect(other.output, self.input)

        Args:
            other: The source Module or Port

        Returns:
            Connection object

        Raises:
            ValueError: If input/output ports are not defined

        Example:
            >>> rc << input_source  # RC's input from input_source's output
            >>> # Or with explicit ports:
            >>> rc.input << source.output
        """
        # If other is a Module, get its default output port
        if isinstance(other, Module):
            if other._output_var is None:
                raise ValueError(
                    f"Module '{other.name}' has no default output port. "
                    f"Use set_output() or specify explicit port: {other.name}.port_name"
                )
            other_port = other._output_var
        elif isinstance(other, Port):
            other_port = other
        else:
            raise TypeError(f"Can only connect Module or Port, got {type(other)}")

        # Get self's default input port
        if self._input_var is None:
            raise ValueError(
                f"Module '{self.name}' has no default input port. "
                f"Use set_input() or specify explicit port: {self.name}.port_name"
            )

        # Create connection (other's output to self's input)
        return Connection(other_port, self._input_var)

    def __rshift__(self, other: Union['Module', Port]) -> Connection:
        """
        Connection operator: self >> other

        Means: self's output goes to other's input
        Equivalent to: connect(self.output, other.input)

        Args:
            other: The destination Module or Port

        Returns:
            Connection object

        Raises:
            ValueError: If input/output ports are not defined

        Example:
            >>> input_source >> rc  # input_source's output to RC's input
            >>> # Or with explicit ports:
            >>> source.output >> rc.input
        """
        # Get self's default output port
        if self._output_var is None:
            raise ValueError(
                f"Module '{self.name}' has no default output port. "
                f"Use set_output() or specify explicit port: {self.name}.port_name"
            )

        # If other is a Module, get its default input port
        if isinstance(other, Module):
            if other._input_var is None:
                raise ValueError(
                    f"Module '{other.name}' has no default input port. "
                    f"Use set_input() or specify explicit port: {other.name}.port_name"
                )
            other_port = other._input_var
        elif isinstance(other, Port):
            other_port = other
        else:
            raise TypeError(f"Can only connect Module or Port, got {type(other)}")

        # Create connection (self's output to other's input)
        return Connection(self._output_var, other_port)

    @property
    def julia_system(self) -> Any:
        """
        Get the built Julia ODESystem.

        Returns:
            The Julia ODESystem object

        Raises:
            RuntimeError: If build() has not been called yet
        """
        if self._julia_system is None:
            raise RuntimeError(
                f"Module '{self.name}' has not been built yet. Call build() first."
            )
        return self._julia_system

    @property
    def states(self) -> Dict[str, float]:
        """Get a copy of the states dictionary with default values."""
        return self._states.copy()

    @property
    def params(self) -> Dict[str, float]:
        """Get a copy of the parameters dictionary with default values."""
        return self._params.copy()

    @property
    def equations(self) -> List[str]:
        """Get a copy of the equations list."""
        return self._equations.copy()

    @property
    def input_var(self) -> Optional[str]:
        """Get the primary input variable name."""
        return self._input_var

    @property
    def output_var(self) -> Optional[str]:
        """Get the primary output variable name."""
        return self._output_var

    def __repr__(self) -> str:
        io_info = ""
        if self._input_var or self._output_var:
            io_parts = []
            if self._input_var:
                io_parts.append(f"in={self._input_var}")
            if self._output_var:
                io_parts.append(f"out={self._output_var}")
            io_info = ", " + ", ".join(io_parts)

        return (
            f"Module(name='{self.name}', "
            f"states={list(self._states.keys())}, "
            f"params={list(self._params.keys())}, "
            f"equations={len(self._equations)}{io_info})"
        )
