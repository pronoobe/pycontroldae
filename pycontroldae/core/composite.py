"""
CompositeModule Class for pycontroldae

This module provides the CompositeModule class which allows encapsulating
multiple modules with internal connections into a single module with
well-defined input/output interfaces.

CompositeModule acts like a regular Module but contains a hierarchical
structure of sub-modules, enabling:
- Modular design and reusability
- Hierarchical system composition
- Clean interface abstraction
- Encapsulation of complex subsystems
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from .module import Module
from .port import Port, Connection
from .backend import get_jl


class CompositeModule(Module):
    """
    A composite module that encapsulates multiple sub-modules with internal connections.

    CompositeModule extends Module to support hierarchical composition. It contains:
    - Multiple sub-modules (can be Module or CompositeModule instances)
    - Internal connections between sub-modules
    - Input/output interface mappings (which internal signals are exposed)

    The CompositeModule compiles to a single Julia ODESystem with hierarchical naming,
    and can be used anywhere a regular Module is used.

    Example:
        >>> # Create a PID controller with anti-windup as a composite module
        >>> pid_with_antiwindup = CompositeModule("pid_antiwindup")
        >>>
        >>> # Add sub-modules
        >>> pid = PID(name="pid", Kp=1.0, Ki=0.1, Kd=0.05)
        >>> limiter = Limiter(name="limiter", min_value=-10, max_value=10)
        >>>
        >>> pid_with_antiwindup.add_module(pid)
        >>> pid_with_antiwindup.add_module(limiter)
        >>>
        >>> # Define internal connections
        >>> pid_with_antiwindup.add_connection("pid.output ~ limiter.input")
        >>>
        >>> # Expose interfaces
        >>> pid_with_antiwindup.expose_input("error", "pid.error")
        >>> pid_with_antiwindup.expose_output("control", "limiter.output")
        >>>
        >>> # Now use it like a regular module
        >>> system.connect(sensor >> pid_with_antiwindup >> actuator)
    """

    def __init__(self, name: str, input_var: Optional[str] = None, output_var: Optional[str] = None):
        """
        Initialize a CompositeModule.

        Args:
            name: Name of the composite module
            input_var: Optional default input interface name
            output_var: Optional default output interface name
        """
        super().__init__(name, input_var, output_var)

        # Sub-modules and connections
        self._modules: List[Module] = []
        self._connections: List[str] = []

        # Interface mappings: external_name -> internal_path
        self._input_interfaces: Dict[str, str] = {}
        self._output_interfaces: Dict[str, str] = {}

        # Track if we've been built
        self._is_built = False

    def add_module(self, module: Module) -> 'CompositeModule':
        """
        Add a sub-module to this composite module.

        Args:
            module: A Module or CompositeModule instance to add

        Returns:
            self (for method chaining)

        Example:
            >>> composite.add_module(pid)
            >>> composite.add_module(plant)
        """
        if not isinstance(module, Module):
            raise TypeError(f"Expected Module instance, got {type(module)}")

        self._modules.append(module)
        return self

    def add_connection(self, connection: Union[str, Connection, Tuple[Module, Module, str]]) -> 'CompositeModule':
        """
        Add an internal connection between sub-modules.

        Args:
            connection: Connection string, Connection object, or tuple from operators

        Returns:
            self (for method chaining)

        Example:
            >>> # String-based
            >>> composite.add_connection("pid.output ~ plant.input")
            >>> # Port-based (new)
            >>> composite.add_connection(pid.output >> plant.input)
            >>> # Module operators
            >>> composite.add_connection(pid >> plant)
        """
        if isinstance(connection, str):
            self._connections.append(connection)
        elif isinstance(connection, Connection):
            # New Port-based connection
            self._connections.append(connection.expr)
        elif isinstance(connection, tuple) and len(connection) == 3:
            mod1, mod2, conn_str = connection

            # Automatically add modules if not present
            if mod1 not in self._modules:
                self._modules.append(mod1)
            if mod2 not in self._modules:
                self._modules.append(mod2)

            self._connections.append(conn_str)
        else:
            raise TypeError(f"Expected str, Connection, or tuple, got {type(connection)}")

        return self

    def expose_input(self, interface_name: str, internal_path: Union[str, Port]) -> 'CompositeModule':
        """
        Expose an internal variable as an input interface.

        This creates a mapping from an external interface name to an internal
        sub-module variable. When another module connects to this composite
        module's input, the connection is forwarded to the internal variable.

        Args:
            interface_name: External name for this input
            internal_path: Internal path (string "submodule.variable" or Port object)

        Returns:
            self (for method chaining)

        Example:
            >>> # Using string path (backward compatible)
            >>> composite.expose_input("error", "pid.error")
            >>>
            >>> # Using Port object (new, recommended)
            >>> composite.expose_input("error", pid.error)
            >>>
            >>> # Now external modules can connect to it
            >>> system.connect("sensor.output ~ composite.error")
            >>> # Or: sensor.output >> composite.error
        """
        # Convert Port to string path if necessary
        if isinstance(internal_path, Port):
            internal_path = str(internal_path)

        self._input_interfaces[interface_name] = internal_path

        # Create port for this interface
        if interface_name not in self._states:
            self.add_state(interface_name, 0.0)

        # Create and set as default input port if not already set
        port = self._create_port(interface_name, is_input=True)
        if self._input_var is None:
            self._input_var = port

        return self

    def expose_output(self, interface_name: str, internal_path: Union[str, Port]) -> 'CompositeModule':
        """
        Expose an internal variable as an output interface.

        This creates a mapping from an external interface name to an internal
        sub-module variable. When this composite module connects to another
        module, the connection uses the internal variable.

        Args:
            interface_name: External name for this output
            internal_path: Internal path (string "submodule.variable" or Port object)

        Returns:
            self (for method chaining)

        Example:
            >>> # Using string path (backward compatible)
            >>> composite.expose_output("control", "limiter.output")
            >>>
            >>> # Using Port object (new, recommended)
            >>> composite.expose_output("control", limiter.output)
            >>>
            >>> # Now this composite can connect to other modules
            >>> system.connect("composite.control ~ actuator.input")
            >>> # Or: composite.control >> actuator.input
        """
        # Convert Port to string path if necessary
        if isinstance(internal_path, Port):
            internal_path = str(internal_path)

        self._output_interfaces[interface_name] = internal_path

        # Create port for this interface
        if interface_name not in self._states:
            self.add_state(interface_name, 0.0)

        # Create and set as default output port if not already set
        port = self._create_port(interface_name, is_input=False)
        if self._output_var is None:
            self._output_var = port

        return self

    def build(self) -> Any:
        """
        Build the composite module into a Julia ODESystem.

        This method:
        1. Builds all sub-modules
        2. Creates interface variables in Julia
        3. Creates internal connections between sub-modules
        4. Creates interface connections (input/output mappings)
        5. Composes everything into a hierarchical ODESystem

        Returns:
            Julia ODESystem representing this composite module

        Raises:
            ValueError: If no sub-modules or if interfaces are invalid
            RuntimeError: If compilation fails
        """
        if self._is_built:
            return self._julia_system

        if not self._modules:
            raise ValueError(f"CompositeModule '{self.name}' has no sub-modules")

        jl = get_jl()

        try:
            # Build all sub-modules
            for module in self._modules:
                if module._julia_system is None:
                    module.build()

            # Create Julia symbolic variables for interface states
            # Collect all interface names
            interface_vars = set(self._input_interfaces.keys()) | set(self._output_interfaces.keys())

            if interface_vars:
                # Create @variables for interface states
                vars_str = " ".join([f"{var}(t)" for var in interface_vars])
                jl.seval(f"@variables {vars_str}")

            # Create interface connection equations
            # These are algebraic equations that map external interfaces to internal variables
            interface_equations = []

            # Input interfaces: internal_variable ~ external_interface
            for ext_name, int_path in self._input_interfaces.items():
                # The internal path should connect to the external interface
                interface_equations.append(f"{int_path} ~ {ext_name}")

            # Output interfaces: external_interface ~ internal_variable
            for ext_name, int_path in self._output_interfaces.items():
                # The external interface mirrors the internal value
                interface_equations.append(f"{ext_name} ~ {int_path}")

            # Combine internal connections and interface mappings
            all_connections = self._connections + interface_equations

            # Get Julia system names for sub-modules
            systems_str = ", ".join([mod.name for mod in self._modules])

            # Create the composite system
            if all_connections:
                connections_str = ", ".join(all_connections)
                jl.seval(f"_connections_{self.name} = [{connections_str}]")

                compose_expr = (
                    f"@named {self.name} = ODESystem("
                    f"_connections_{self.name}, t; systems=[{systems_str}])"
                )
            else:
                compose_expr = (
                    f"@named {self.name} = ODESystem(Equation[], t; systems=[{systems_str}])"
                )

            jl.seval(compose_expr)

            # Retrieve the Julia system
            self._julia_system = jl.seval(self.name)
            self._is_built = True

            return self._julia_system

        except Exception as e:
            raise RuntimeError(
                f"Failed to build CompositeModule '{self.name}': {e}\n"
                "Check that all sub-modules are valid and connections reference existing variables."
            ) from e

    def get_modules(self) -> List[Module]:
        """Get the list of sub-modules."""
        return self._modules.copy()

    def get_connections(self) -> List[str]:
        """Get the list of internal connections."""
        return self._connections.copy()

    def get_input_interfaces(self) -> Dict[str, str]:
        """Get the input interface mappings."""
        return self._input_interfaces.copy()

    def get_output_interfaces(self) -> Dict[str, str]:
        """Get the output interface mappings."""
        return self._output_interfaces.copy()

    def __repr__(self) -> str:
        return (
            f"CompositeModule(name='{self.name}', "
            f"modules={len(self._modules)}, "
            f"connections={len(self._connections)}, "
            f"inputs={list(self._input_interfaces.keys())}, "
            f"outputs={list(self._output_interfaces.keys())})"
        )


# Convenience function for creating composite modules

def create_composite(
    name: str,
    modules: List[Module],
    connections: List[str],
    inputs: Optional[Dict[str, str]] = None,
    outputs: Optional[Dict[str, str]] = None
) -> CompositeModule:
    """
    Convenience function to create a CompositeModule.

    Args:
        name: Name of the composite module
        modules: List of sub-modules
        connections: List of internal connection strings
        inputs: Dict mapping interface names to internal paths
        outputs: Dict mapping interface names to internal paths

    Returns:
        Configured CompositeModule

    Example:
        >>> pid = PID(name="pid", Kp=1.0, Ki=0.1, Kd=0.05)
        >>> limiter = Limiter(name="lim", min_value=-10, max_value=10)
        >>>
        >>> controller = create_composite(
        ...     name="controller",
        ...     modules=[pid, limiter],
        ...     connections=["pid.output ~ lim.input"],
        ...     inputs={"error": "pid.error"},
        ...     outputs={"control": "lim.output"}
        ... )
    """
    composite = CompositeModule(name)

    # Add modules
    for module in modules:
        composite.add_module(module)

    # Add connections
    for conn in connections:
        composite.add_connection(conn)

    # Expose inputs
    if inputs:
        for ext_name, int_path in inputs.items():
            composite.expose_input(ext_name, int_path)

    # Expose outputs
    if outputs:
        for ext_name, int_path in outputs.items():
            composite.expose_output(ext_name, int_path)

    return composite
