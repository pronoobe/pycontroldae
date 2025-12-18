"""
Simulator Class for pycontroldae

This module provides the Simulator class which takes a compiled System,
creates an ODEProblem, solves it using Julia's DifferentialEquations.jl,
and converts the solution back to Python-friendly format (numpy arrays).

Enhanced features:
- Event support (TimeEvent and ContinuousEvent)
- Dynamic parameter modification during simulation
- Data probes for observing specific variables
- Rich SimulationResult objects with export capabilities
"""

from typing import Tuple, Dict, Any, Optional, List, Union
import numpy as np
from .backend import get_jl
from .system import System
from .events import TimeEvent, ContinuousEvent
from .result import SimulationResult, DataProbe
from .expression_parser import ObservedExpressionEvaluator


class Simulator:
    """
    A simulator that solves a compiled System and returns results in Python format.

    The Simulator class takes a compiled System, creates a Julia ODEProblem with
    initial conditions and parameter values, solves it using the Rodas5() solver
    (suitable for stiff/DAE systems), and converts the Julia Solution to numpy arrays.

    Example:
        >>> system = System("my_system")
        >>> # ... add modules, connect, compile ...
        >>> simplified = system.compile()
        >>>
        >>> sim = Simulator(system)
        >>> times, values = sim.run(t_span=(0.0, 1.0), dt=0.01)
        >>> print(f"Time points: {len(times)}")
        >>> print(f"State values shape: {values.shape}")
    """

    def __init__(self, system: System):
        """
        Initialize a Simulator for a given System.

        Args:
            system: A System instance (should be compiled before simulation)

        Raises:
            TypeError: If system is not a System instance
            RuntimeError: If the system has not been compiled yet
        """
        if not isinstance(system, System):
            raise TypeError(f"Expected System instance, got {type(system)}")

        # Check if system has been compiled
        if system._compiled_system is None:
            raise RuntimeError(
                f"System '{system.name}' has not been compiled yet. "
                "Call system.compile() before creating a Simulator."
            )

        self.system = system
        self._jl = get_jl()

    def run(
        self,
        t_span: Tuple[float, float],
        u0: Optional[Dict[str, float]] = None,
        params: Optional[Dict[str, float]] = None,
        dt: Optional[float] = None,
        solver: str = "Rodas5",
        probes: Optional[Union[DataProbe, List[DataProbe], Dict[str, DataProbe]]] = None,
        return_result: bool = True
    ) -> Union[SimulationResult, Tuple[np.ndarray, np.ndarray]]:
        """
        Run the simulation and return results.

        This method:
        1. Constructs initial conditions from module defaults or provided u0
        2. Constructs parameters from module defaults or provided params
        3. Creates a Julia ODEProblem
        4. Solves using the specified solver (default: Rodas5 for stiff/DAE systems)
        5. Extracts data from solution (including probe data if specified)
        6. Returns SimulationResult or raw numpy arrays

        Args:
            t_span: Time span tuple (t_start, t_end)
            u0: Optional dict of initial conditions {state_name: value}
                If not provided, uses defaults from module definitions
            params: Optional dict of parameter values {param_name: value}
                If not provided, uses defaults from module definitions
            dt: Optional time step for saving solution points
                If None, uses adaptive time stepping
            solver: Solver name (default: "Rodas5" for stiff/DAE systems)
                Other options: "Tsit5", "TRBDF2", "QNDF", etc.
            probes: Optional data probe(s) for observing specific variables:
                - Single DataProbe
                - List of DataProbe objects
                - Dict of {name: DataProbe}
            return_result: If True, return SimulationResult object (default)
                          If False, return raw (times, values) tuple for backward compatibility

        Returns:
            If return_result=True (default):
                SimulationResult object with export methods
            If return_result=False:
                Tuple of (times, values):
                    - times: 1D numpy array of time points
                    - values: 2D numpy array of state values

        Raises:
            ValueError: If t_span is invalid
            RuntimeError: If solving fails

        Example:
            >>> # Modern usage with SimulationResult
            >>> result = simulator.run(t_span=(0, 10), dt=0.1)
            >>> df = result.to_dataframe()
            >>> result.to_csv("output.csv")
            >>>
            >>> # With data probes
            >>> probe = DataProbe(
            ...     variables=["plant.x1", "controller.output"],
            ...     names=["Position", "Control"]
            ... )
            >>> result = simulator.run(t_span=(0, 10), probes=probe)
            >>> probe_df = result.get_probe_dataframe()
            >>>
            >>> # Backward compatible usage
            >>> times, values = simulator.run(t_span=(0, 10), return_result=False)
        """
        # Validate t_span
        if len(t_span) != 2:
            raise ValueError(f"t_span must be a tuple of (t_start, t_end), got {t_span}")
        if t_span[0] >= t_span[1]:
            raise ValueError(f"t_start must be less than t_end, got {t_span}")

        t_start, t_end = t_span

        try:
            # Get the compiled system
            julia_system = self.system._compiled_system

            # Store system reference in Julia for convenience
            sys_name = f"_sys_{self.system.name}"
            self._jl.seval(f"{sys_name} = _simplified_{self.system.name}")

            # Get unknowns and parameters from the simplified system
            self._jl.seval(f"_unknowns_{self.system.name} = unknowns({sys_name})")
            self._jl.seval(f"_params_{self.system.name} = parameters({sys_name})")

            # Build initial conditions
            # If u0 not provided, use defaults (zeros for now, as we can't easily extract defaults)
            if u0 is None:
                # Use defaults: build a map with zeros or module defaults
                u0_dict = {}
                for module in self.system._modules:
                    for state_name, default_val in module._states.items():
                        full_name = f"{module.name}.{state_name}"
                        u0_dict[full_name] = default_val
            else:
                u0_dict = u0

            # Build parameters - merge defaults with user-provided
            params_dict = {}
            # First, add all defaults
            for module in self.system._modules:
                for param_name, default_val in module._params.items():
                    full_name = f"{module.name}.{param_name}"
                    params_dict[full_name] = default_val

            # Then override with user-provided params
            if params is not None:
                params_dict.update(params)

            # Build u0 and params maps using Julia code that iterates through system variables
            # This is more robust than trying to construct variable names

            # Create Julia dictionary for u0 mapping (Python name -> value)
            self._jl.seval(f"_u0_dict_{self.system.name} = Dict()")
            for full_name, value in u0_dict.items():
                # Escape the name for Julia string
                self._jl.seval(
                    f"_u0_dict_{self.system.name}[\"{full_name}\"] = {value}"
                )

            # Create Julia dictionary for params mapping (Python name -> value)
            self._jl.seval(f"_params_dict_{self.system.name} = Dict()")
            for full_name, value in params_dict.items():
                self._jl.seval(
                    f"_params_dict_{self.system.name}[\"{full_name}\"] = {value}"
                )

            # Build u0 map by matching variable names
            # Julia code to iterate through unknowns and build the map
            build_u0_code = f"""
            _u0_map_{self.system.name} = Dict()
            for var in _unknowns_{self.system.name}
                var_str = string(var)
                # Remove (t) suffix if present
                var_name = replace(var_str, "(t)" => "")
                # Convert ₊ to . for Python-style naming
                python_name = replace(var_name, "₊" => ".")
                if haskey(_u0_dict_{self.system.name}, python_name)
                    _u0_map_{self.system.name}[var] = _u0_dict_{self.system.name}[python_name]
                else
                    # Default to 0 if not specified
                    _u0_map_{self.system.name}[var] = 0.0
                end
            end
            """
            self._jl.seval(build_u0_code)

            # Build params map similarly
            build_params_code = f"""
            _params_map_{self.system.name} = Dict()
            for param in _params_{self.system.name}
                param_str = string(param)
                # Convert ₊ to . for Python-style naming
                python_name = replace(param_str, "₊" => ".")
                if haskey(_params_dict_{self.system.name}, python_name)
                    _params_map_{self.system.name}[param] = _params_dict_{self.system.name}[python_name]
                else
                    # Default to 1 if not specified
                    _params_map_{self.system.name}[param] = 1.0
                end
            end
            """
            self._jl.seval(build_params_code)

            # Merge u0 and params into a single map for ODEProblem
            self._jl.seval(
                f"_combined_map_{self.system.name} = merge(_u0_map_{self.system.name}, _params_map_{self.system.name})"
            )

            # Create ODEProblem using modern API
            # Format: ODEProblem(system, combined_map, tspan)
            self._jl.seval(
                f"_prob_{self.system.name} = ODEProblem("
                f"{sys_name}, _combined_map_{self.system.name}, ({t_start}, {t_end}))"
            )

            # Build callbacks from registered events
            callbacks_list = []
            if self.system._events:
                callbacks_list = self._build_callbacks(self.system._events, self.system.name)

            # Solve the problem with specified solver and callbacks
            if callbacks_list:
                # Combine callbacks using CallbackSet
                callbacks_str = ", ".join(callbacks_list)
                self._jl.seval(
                    f"_callback_set_{self.system.name} = CallbackSet({callbacks_str})"
                )

                if dt is not None:
                    # Use saveat for fixed time steps with callbacks
                    solve_expr = (
                        f"_sol_{self.system.name} = solve("
                        f"_prob_{self.system.name}, {solver}(), "
                        f"callback=_callback_set_{self.system.name}, saveat={dt})"
                    )
                else:
                    # Adaptive time stepping with callbacks
                    solve_expr = (
                        f"_sol_{self.system.name} = solve("
                        f"_prob_{self.system.name}, {solver}(), "
                        f"callback=_callback_set_{self.system.name})"
                    )
            else:
                # No callbacks
                if dt is not None:
                    # Use saveat for fixed time steps
                    solve_expr = (
                        f"_sol_{self.system.name} = solve("
                        f"_prob_{self.system.name}, {solver}(), saveat={dt})"
                    )
                else:
                    # Adaptive time stepping
                    solve_expr = (
                        f"_sol_{self.system.name} = solve("
                        f"_prob_{self.system.name}, {solver}())"
                    )

            self._jl.seval(solve_expr)

            # Get the solution object
            solution = self._jl.seval(f"_sol_{self.system.name}")

            # Extract time points and values from Julia Solution
            # Solution.t gives time points, Solution.u gives state vectors
            times_jl = self._jl.seval(f"_sol_{self.system.name}.t")
            values_jl = self._jl.seval(f"_sol_{self.system.name}.u")

            # Convert to numpy arrays
            # times_jl is a Julia Vector{Float64}
            times = np.array(times_jl)

            # values_jl is a Julia Vector{Vector{Float64}} (vector of state vectors)
            # Convert to 2D numpy array: shape (n_timepoints, n_states)
            values_list = []
            for i in range(len(values_jl)):
                state_vector = np.array(values_jl[i])
                values_list.append(state_vector)

            values = np.array(values_list)

            # Get state names from the simplified system (Julia)
            try:
                # Get unknowns from the simplified system
                unknowns_jl = self._jl.seval(f"unknowns({sys_name})")
                state_names = []
                for i in range(len(unknowns_jl)):
                    var_str = self._jl.seval(f"string(unknowns({sys_name})[{i+1}])")
                    # Remove (t) suffix if present
                    if "(t)" in var_str:
                        var_str = var_str.replace("(t)", "")
                    # Convert ₊ to . for Python-style naming
                    var_str = var_str.replace("₊", ".")
                    state_names.append(var_str)
            except Exception:
                # Fallback: use generic names
                state_names = [f"state_{i}" for i in range(values.shape[1])]

            # Process probes if provided
            probe_data = {}
            if probes is not None:
                probe_data = self._extract_probe_data(
                    probes, times, values, state_names, sys_name, self.system.name, params_dict
                )

            # Return result based on return_result flag
            if return_result:
                # Create and return SimulationResult object
                return SimulationResult(
                    times=times,
                    values=values,
                    state_names=state_names,
                    probe_data=probe_data,
                    system_name=self.system.name,
                    solver=solver,
                    metadata={
                        't_span': t_span,
                        'dt': dt,
                        'n_events': len(self.system._events) if self.system._events else 0
                    }
                )
            else:
                # Backward compatible: return raw arrays
                return times, values

        except Exception as e:
            raise RuntimeError(
                f"Failed to simulate system '{self.system.name}': {e}\n"
                "Check that initial conditions and parameters are correctly specified."
            ) from e

    def _extract_probe_data(
        self,
        probes: Union[DataProbe, List[DataProbe], Dict[str, DataProbe]],
        times: np.ndarray,
        values: np.ndarray,
        state_names: List[str],
        sys_name: str,
        system_name: str,
        params_dict: Dict[str, float]
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """
        Extract data for specified probes from the Julia solution.

        Args:
            probes: DataProbe(s) specifying variables to extract
            times: Time vector
            values: State values array
            state_names: List of state names
            sys_name: Julia variable name for the system
            system_name: Python system name

        Returns:
            Dictionary of {probe_name: {variable_name: values}}
        """
        # Normalize probes to dictionary format
        if isinstance(probes, DataProbe):
            probes_dict = {"default": probes}
        elif isinstance(probes, list):
            probes_dict = {f"probe_{i}": probe for i, probe in enumerate(probes)}
        elif isinstance(probes, dict):
            probes_dict = probes
        else:
            raise TypeError(f"probes must be DataProbe, list, or dict, got {type(probes)}")

        probe_data = {}

        for probe_name, probe in probes_dict.items():
            probe_vars = {}

            for var_name, custom_name in zip(probe.variables, probe.names):
                try:
                    # First, try to get the observed equation RHS for this variable
                    # This will help us compute parametric expressions correctly
                    observed_rhs = self._get_observed_rhs(var_name, sys_name, system_name)

                    if observed_rhs is not None:
                        # Variable is an observed variable with an expression
                        # Try to evaluate it in Python to handle parameters correctly
                        print(f"Info: '{var_name}' is observed variable with RHS: {observed_rhs}")

                        try:
                            # Evaluate using Python expression parser
                            extracted_values = self._evaluate_observed_expression(
                                observed_rhs, times, values, state_names, params_dict
                            )
                            probe_vars[custom_name] = extracted_values
                            print(f"Info: Successfully evaluated '{var_name}' using Python expression parser")
                            continue  # Skip Julia extraction
                        except Exception as e:
                            print(f"Warning: Failed to evaluate observed expression in Python: {e}")
                            print(f"  Falling back to Julia extraction...")

                    # Convert Python variable name to Julia format (replace . with ₊)
                    julia_var_name = var_name.replace(".", "₊")

                    # Enhanced extraction code that searches in multiple locations
                    # Initialize the output variable globally first
                    self._jl.seval(f"_probe_values_{system_name} = Float64[]")

                    extract_code = f"""
                    let
                        # Get the symbolic variable
                        var_sym = Symbol("{julia_var_name}")

                        # Collect all possible variables from the system
                        # 1. Get unknowns (differential states after simplification)
                        sys_unknowns = unknowns({sys_name})

                        # 2. Get observables (algebraic variables and outputs)
                        sys_observables = try
                            observed({sys_name})
                        catch
                            []
                        end

                        # 3. Combine all variables
                        all_vars = vcat(sys_unknowns, sys_observables)

                        # Find matching variable (try multiple matching strategies)
                        target_var = nothing
                        is_observable = false

                        # Strategy 1: Exact match after removing (t) suffix
                        for v in all_vars
                            v_str = replace(string(v), "(t)" => "")
                            if Symbol(v_str) == var_sym
                                target_var = v
                                # Check if this is an observable
                                is_observable = v in sys_observables
                                break
                            end
                        end

                        # Strategy 2: Match with converted name (. to ₊)
                        if target_var === nothing
                            for v in all_vars
                                v_str = replace(string(v), "(t)" => "")
                                v_converted = replace(v_str, "₊" => ".")
                                if v_converted == "{var_name}"
                                    target_var = v
                                    is_observable = v in sys_observables
                                    break
                                end
                            end
                        end

                        # Strategy 3: Partial match (for simplified variable names)
                        if target_var === nothing
                            for v in all_vars
                                v_str = replace(string(v), "(t)" => "")
                                if contains(v_str, "{julia_var_name}") ||
                                   contains("{julia_var_name}", v_str)
                                    target_var = v
                                    is_observable = v in sys_observables
                                    break
                                end
                            end
                        end

                        # Extract values from solution
                        if target_var !== nothing
                            try
                                if is_observable
                                    # For observables, we need to compute them from the solution
                                    # Observables in ModelingToolkit are stored as Equation objects (lhs ~ rhs)
                                    # BUGFIX: Need to evaluate the RHS expression, not just extract LHS
                                    # because RHS may contain parameters (e.g., y ~ k*x where k is a parameter)

                                    # Get both lhs and rhs of the equation
                                    obs_lhs = target_var.lhs
                                    obs_rhs = target_var.rhs

                                    # Try to substitute values and evaluate the RHS expression
                                    try
                                        # Method 1: Manually substitute and evaluate RHS
                                        # Create a function to evaluate RHS at each time point
                                        global _probe_values_{system_name} = []
                                        for i in 1:length(_sol_{system_name}.t)
                                            # Get current state and parameters
                                            current_state = _sol_{system_name}.u[i]
                                            current_t = _sol_{system_name}.t[i]

                                            # Try to evaluate the RHS by substituting current values
                                            try
                                                # Use ModelingToolkit's substitute to evaluate RHS
                                                val = ModelingToolkit.substitute(obs_rhs,
                                                    ModelingToolkit.build_variable_subst_dict(_sol_{system_name}, i, _sol_{system_name}.prob.p))
                                                push!(_probe_values_{system_name}, val)
                                            catch
                                                # Fallback: just use lhs value
                                                val = _sol_{system_name}(current_t, idxs=obs_lhs)
                                                push!(_probe_values_{system_name}, val)
                                            end
                                        end
                                    catch e
                                        # Fallback: use original method (may be wrong for parametric observables)
                                        global _probe_values_{system_name} = [_sol_{system_name}(t, idxs=obs_lhs) for t in _sol_{system_name}.t]
                                    end
                                else
                                    # For unknowns (differential states), use direct indexing
                                    global _probe_values_{system_name} = [_sol_{system_name}[target_var, i] for i in 1:length(_sol_{system_name}.t)]
                                end
                            catch e
                                # Fallback: try alternative methods
                                try
                                    # Try using sol(t, idxs=var) for all variables
                                    global _probe_values_{system_name} = [_sol_{system_name}(t, idxs=target_var) for t in _sol_{system_name}.t]
                                catch e2
                                    # If that fails too, try to find in unknowns by index
                                    var_idx = findfirst(x -> x == target_var, sys_unknowns)
                                    if var_idx !== nothing
                                        global _probe_values_{system_name} = [_sol_{system_name}.u[i][var_idx] for i in 1:length(_sol_{system_name}.t)]
                                    else
                                        global _probe_values_{system_name} = zeros(length(_sol_{system_name}.t))
                                    end
                                end
                            end
                        else
                            # Variable not found after all strategies
                            global _probe_values_{system_name} = zeros(length(_sol_{system_name}.t))
                        end
                    end
                    """

                    self._jl.seval(extract_code)

                    # Get the extracted values
                    values_jl = self._jl.seval(f"_probe_values_{system_name}")
                    extracted_values = np.array(values_jl)

                    # Check if values are valid (not all zeros when they shouldn't be)
                    if np.allclose(extracted_values, 0.0) and var_name in state_names:
                        # Try direct extraction from values array if variable is in state_names
                        try:
                            idx = state_names.index(var_name)
                            extracted_values = values[:, idx].copy()
                            print(f"Info: Using direct state extraction for '{var_name}'")
                        except (ValueError, IndexError):
                            pass  # Keep zeros if direct extraction fails

                    probe_vars[custom_name] = extracted_values

                except Exception as e:
                    # If extraction fails, warn but continue
                    print(f"Warning: Failed to extract probe variable '{var_name}': {e}")
                    print(f"  Suggestion: Use result.state_names to see available variables")
                    # Fill with zeros
                    probe_vars[custom_name] = np.zeros(len(times))

            probe_data[probe_name] = probe_vars

        return probe_data

    def _build_callbacks(
        self,
        events: List[Union[TimeEvent, ContinuousEvent]],
        system_name: str
    ) -> List[str]:
        """
        Build Julia callbacks from Python events.

        Converts TimeEvent and ContinuousEvent objects into Julia PresetTimeCallback
        and ContinuousCallback objects.

        Args:
            events: List of event objects
            system_name: Name of the system (for unique Julia variable naming)

        Returns:
            List of Julia callback variable names

        Note:
            Python callbacks are stored in Julia via PythonCall.jl and invoked
            from Julia's callback functions.
        """
        callback_names = []

        for idx, event in enumerate(events):
            if isinstance(event, TimeEvent):
                # Build PresetTimeCallback
                callback_name = self._build_time_callback(event, idx, system_name)
                callback_names.append(callback_name)

            elif isinstance(event, ContinuousEvent):
                # Build ContinuousCallback
                callback_name = self._build_continuous_callback(event, idx, system_name)
                callback_names.append(callback_name)

        return callback_names

    def _build_time_callback(
        self,
        event: TimeEvent,
        idx: int,
        system_name: str
    ) -> str:
        """
        Build a Julia PresetTimeCallback from a TimeEvent.

        Args:
            event: TimeEvent instance
            idx: Index of the event (for unique naming)
            system_name: System name

        Returns:
            Julia variable name for the callback
        """
        callback_var = f"_time_callback_{system_name}_{idx}"

        # Store the Python callback function in Julia
        py_callback_var = f"_py_time_affect_{system_name}_{idx}"
        self._jl.seval(f"{py_callback_var} = pyimport(\"builtins\").None")

        # We need to pass the Python function to Julia
        # Use PythonCall to wrap the function
        import juliacall
        self._jl.seval(f"import PythonCall")

        # Create a wrapper function that stores parameter updates
        # Python callback returns dict of parameter changes
        self._jl.seval(f"""
        {py_callback_var} = nothing
        """)

        # Store the callback in a global Julia variable accessible from Python
        setattr(self._jl, f"_py_cb_{system_name}_{idx}", event.callback)

        # Create Julia affect function that calls the Python callback
        # and updates the integrator parameters
        affect_code = f"""
        function _affect_time_{system_name}_{idx}(integrator)
            # Call Python callback to get parameter updates
            py_callback = Main._py_cb_{system_name}_{idx}
            param_updates = PythonCall.pyconvert(Dict, py_callback(integrator))

            # Apply parameter updates
            for (param_name, new_value) in param_updates
                # Convert Python name (e.g., "module.param") to Julia symbol
                param_name_jl = replace(param_name, "." => "₊")
                param_sym = Symbol(param_name_jl)

                # Update the parameter using try-catch to handle missing parameters gracefully
                try
                    integrator.ps[param_sym] = new_value
                catch e
                    @warn "Failed to update parameter $param_name_jl: $e"
                end
            end
        end
        """
        self._jl.seval(affect_code)

        # Create PresetTimeCallback
        preset_callback_code = f"""
        {callback_var} = PresetTimeCallback(
            [{event.time}],
            _affect_time_{system_name}_{idx}
        )
        """
        self._jl.seval(preset_callback_code)

        return callback_var

    def _build_continuous_callback(
        self,
        event: ContinuousEvent,
        idx: int,
        system_name: str
    ) -> str:
        """
        Build a Julia ContinuousCallback from a ContinuousEvent.

        Args:
            event: ContinuousEvent instance
            idx: Index of the event (for unique naming)
            system_name: System name

        Returns:
            Julia variable name for the callback
        """
        callback_var = f"_continuous_callback_{system_name}_{idx}"

        # Store the Python callback functions in Julia-accessible variables
        setattr(self._jl, f"_py_cond_{system_name}_{idx}", event.condition)
        setattr(self._jl, f"_py_affect_{system_name}_{idx}", event.affect)

        # Create Julia condition function that calls the Python condition
        condition_code = f"""
        function _condition_{system_name}_{idx}(u, t, integrator)
            # Call Python condition function
            py_condition = Main._py_cond_{system_name}_{idx}
            result = PythonCall.pyconvert(Float64, py_condition(u, t, integrator))
            return result
        end
        """
        self._jl.seval(condition_code)

        # Create Julia affect function that calls the Python affect
        affect_code = f"""
        function _affect_{system_name}_{idx}(integrator)
            # Call Python affect function to get parameter updates
            py_affect = Main._py_affect_{system_name}_{idx}
            param_updates = PythonCall.pyconvert(Dict, py_affect(integrator))

            # Apply parameter updates
            for (param_name, new_value) in param_updates
                # Convert Python name to Julia symbol
                param_name_jl = replace(param_name, "." => "₊")
                param_sym = Symbol(param_name_jl)

                # Update the parameter using try-catch to handle missing parameters gracefully
                try
                    integrator.ps[param_sym] = new_value
                catch e
                    @warn "Failed to update parameter $param_name_jl: $e"
                end
            end
        end
        """
        self._jl.seval(affect_code)

        # Map direction to Julia notation
        # 0 = both, +1 = upcrossing, -1 = downcrossing
        if event.direction == 0:
            rootfind_str = "SciMLBase.RightRootFind"
        elif event.direction == 1:
            rootfind_str = "SciMLBase.LeftRootFind"
        else:  # -1
            rootfind_str = "SciMLBase.RightRootFind"

        # Create ContinuousCallback
        continuous_callback_code = f"""
        {callback_var} = ContinuousCallback(
            _condition_{system_name}_{idx},
            _affect_{system_name}_{idx},
            rootfind={rootfind_str}
        )
        """
        self._jl.seval(continuous_callback_code)

        return callback_var

    def run_to_dict(
        self,
        t_span: Tuple[float, float],
        u0: Optional[Dict[str, float]] = None,
        params: Optional[Dict[str, float]] = None,
        dt: Optional[float] = None,
        solver: str = "Rodas5"
    ) -> Dict[str, np.ndarray]:
        """
        Run simulation and return results as a dictionary with named states.

        This is a convenience wrapper around run() that returns a dictionary
        mapping state names to their time series.

        Args:
            t_span: Time span tuple (t_start, t_end)
            u0: Optional dict of initial conditions
            params: Optional dict of parameter values
            dt: Optional time step
            solver: Solver name (default: "Rodas5")

        Returns:
            Dictionary with:
                - "t": 1D numpy array of time points
                - state names: 1D numpy arrays of values for each state

        Example:
            >>> sim = Simulator(compiled_system)
            >>> results = sim.run_to_dict(t_span=(0.0, 10.0), dt=0.1)
            >>> print(results.keys())  # ['t', 'rc_circuit__V', 'rc_circuit__I', ...]
            >>> import matplotlib.pyplot as plt
            >>> plt.plot(results['t'], results['rc_circuit__V'])
        """
        times, values = self.run(t_span, u0, params, dt, solver)

        # Get state names from the simplified system
        try:
            # Get unknowns from the system
            sys_name = f"_sys_{self.system.name}"
            unknowns_jl = self._jl.seval(f"unknowns({sys_name})")

            # Extract state names and convert ₊ to _ to avoid encoding issues
            state_names = []
            for i in range(len(unknowns_jl)):
                var = unknowns_jl[i]
                # Convert Julia variable to string
                var_str = self._jl.seval(f"string(unknowns({sys_name})[{i+1}])")
                # Remove (t) suffix if present
                if "(t)" in var_str:
                    var_str = var_str.replace("(t)", "")
                # Convert ₊ to __ for Python compatibility (avoid Unicode encoding issues)
                var_str = var_str.replace("₊", "__")
                state_names.append(var_str)

        except Exception:
            # Fallback: use generic names
            state_names = [f"state_{i}" for i in range(values.shape[1])]

        # Build result dictionary
        result = {"t": times}
        for i, name in enumerate(state_names):
            result[name] = values[:, i]

        return result

    def _get_observed_rhs(self, var_name: str, sys_name: str, system_name: str) -> Optional[str]:
        """
        Get the RHS expression of an observed variable.

        Args:
            var_name: Python variable name (e.g., "plant.y")
            sys_name: Julia system variable name
            system_name: System name

        Returns:
            RHS expression string or None if not an observed variable
        """
        try:
            # Convert to Julia format
            julia_var_name = var_name.replace(".", "₊")

            # Try to find this variable in observed equations
            code = f"""
            let
                var_sym = Symbol("{julia_var_name}")
                obs = try
                    observed({sys_name})
                catch
                    []
                end

                result = ""
                for eq in obs
                    # Check if lhs matches
                    lhs_str = replace(string(eq.lhs), "(t)" => "")
                    if Symbol(lhs_str) == var_sym
                        # Found it! Get RHS
                        rhs_str = string(eq.rhs)
                        # Convert ₊ back to .
                        result = replace(rhs_str, "₊" => ".")
                        # Remove (t) suffix
                        result = replace(result, "(t)" => "")
                        break
                    end
                end
                result
            end
            """

            result = self._jl.seval(code)
            if result and len(result) > 0:
                return result
            return None
        except Exception as e:
            # Not an observed variable or error occurred
            return None

    def _evaluate_observed_expression(
        self,
        expression: str,
        times: np.ndarray,
        values: np.ndarray,
        state_names: List[str],
        params_dict: Dict[str, float]
    ) -> np.ndarray:
        """
        Evaluate an observed expression using Python.

        Args:
            expression: RHS expression (e.g., "plant.k*plant.x")
            times: Time vector
            values: State values array
            state_names: List of state names
            params_dict: Parameter dictionary

        Returns:
            Evaluated values as numpy array
        """
        # Build state_values dictionary
        state_values = {}
        for i, name in enumerate(state_names):
            state_values[name] = values[:, i]

        # Create evaluator
        evaluator = ObservedExpressionEvaluator(expression, state_names, params_dict)

        # Evaluate
        return evaluator.evaluate(state_values)

    def __repr__(self) -> str:
        return f"Simulator(system='{self.system.name}')"
