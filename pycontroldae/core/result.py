"""
Simulation Result Classes for pycontroldae

Provides rich data structures for accessing and exporting simulation results:
- SimulationResult: Main result container with export capabilities
- DataProbe: Variable observation configuration

Features:
- Flexible variable selection (states, outputs, parameters)
- Multiple export formats (DataFrame, CSV, NumPy)
- Time-series data access
- Statistical summaries
"""

import numpy as np
from typing import Optional, List, Dict, Union, Any
from pathlib import Path


class DataProbe:
    """
    Configuration for observing specific variables during simulation.

    A DataProbe specifies which variables to track and optionally provides
    custom names for them in the output.

    Parameters:
        variables: List of variable names to observe (e.g., ["module.state", "module.output"])
        names: Optional custom names for the variables in output (default: use variable names)
        description: Optional description of what this probe measures

    Example:
        >>> # Observe specific states
        >>> probe = DataProbe(
        ...     variables=["plant.x1", "plant.x2", "controller.output"],
        ...     names=["Position", "Velocity", "Control Signal"],
        ...     description="Main control loop variables"
        ... )
    """

    def __init__(
        self,
        variables: List[str],
        names: Optional[List[str]] = None,
        description: str = ""
    ):
        """
        Initialize a DataProbe.

        Args:
            variables: List of variable names to observe
            names: Optional custom names (must match length of variables)
            description: Optional description of the probe

        Raises:
            ValueError: If names length doesn't match variables length
        """
        if not variables:
            raise ValueError("DataProbe must have at least one variable")

        self.variables = variables

        if names is None:
            self.names = variables.copy()
        else:
            if len(names) != len(variables):
                raise ValueError(
                    f"Length of names ({len(names)}) must match "
                    f"length of variables ({len(variables)})"
                )
            self.names = names

        self.description = description

    def __repr__(self) -> str:
        return (
            f"DataProbe(variables={len(self.variables)}, "
            f"description='{self.description}')"
        )


class SimulationResult:
    """
    Container for simulation results with export capabilities.

    Provides convenient access to simulation data with multiple export formats:
    - to_numpy(): Get raw NumPy arrays
    - to_dataframe(): Get pandas DataFrame (requires pandas)
    - to_csv(): Export to CSV file
    - to_dict(): Get Python dictionary

    Also provides statistical summaries and time-series slicing.

    Attributes:
        times: Time vector (1D NumPy array)
        values: State values (2D NumPy array, shape: [n_times, n_states])
        state_names: Names of all states in the system
        probe_data: Dictionary of probed variables {name: values}
        system_name: Name of the simulated system
        solver: Name of the solver used
        metadata: Additional simulation metadata

    Example:
        >>> result = simulator.run(t_span=(0, 10), dt=0.1)
        >>> df = result.to_dataframe()
        >>> result.to_csv("simulation_results.csv")
        >>> probe_df = result.get_probe_dataframe("control_signals")
    """

    def __init__(
        self,
        times: np.ndarray,
        values: np.ndarray,
        state_names: List[str],
        probe_data: Optional[Dict[str, Dict[str, np.ndarray]]] = None,
        system_name: str = "system",
        solver: str = "Rodas5",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a SimulationResult.

        Args:
            times: Time vector (1D array)
            values: State values (2D array, shape: [n_times, n_states])
            state_names: List of state variable names
            probe_data: Dictionary of probe results {probe_name: {var_name: values}}
            system_name: Name of the system
            solver: Solver name
            metadata: Additional metadata dictionary
        """
        self.times = times
        self.values = values
        self.state_names = state_names
        self.probe_data = probe_data or {}
        self.system_name = system_name
        self.solver = solver
        self.metadata = metadata or {}

        # Validate dimensions
        if len(times) != values.shape[0]:
            raise ValueError(
                f"Time vector length ({len(times)}) must match "
                f"first dimension of values ({values.shape[0]})"
            )

        if len(state_names) != values.shape[1]:
            raise ValueError(
                f"Number of state names ({len(state_names)}) must match "
                f"second dimension of values ({values.shape[1]})"
            )

    def __repr__(self) -> str:
        return (
            f"SimulationResult(system='{self.system_name}', "
            f"t=[{self.times[0]:.2f}, {self.times[-1]:.2f}], "
            f"points={len(self.times)}, states={len(self.state_names)}, "
            f"probes={len(self.probe_data)})"
        )

    def to_numpy(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Export results as NumPy arrays.

        Returns:
            Tuple of (times, values) as NumPy arrays

        Example:
            >>> times, values = result.to_numpy()
            >>> print(times.shape, values.shape)
        """
        return self.times.copy(), self.values.copy()

    def to_dict(self, include_probes: bool = True) -> Dict[str, Any]:
        """
        Export results as a Python dictionary.

        Args:
            include_probes: Whether to include probe data

        Returns:
            Dictionary with time, states, and optionally probe data

        Example:
            >>> data = result.to_dict()
            >>> print(data.keys())
        """
        result_dict = {
            'time': self.times.tolist(),
            'metadata': {
                'system_name': self.system_name,
                'solver': self.solver,
                'n_points': len(self.times),
                'n_states': len(self.state_names),
                **self.metadata
            }
        }

        # Add state data
        for i, name in enumerate(self.state_names):
            result_dict[name] = self.values[:, i].tolist()

        # Add probe data if requested
        if include_probes and self.probe_data:
            result_dict['probes'] = {}
            for probe_name, probe_vars in self.probe_data.items():
                result_dict['probes'][probe_name] = {
                    var_name: var_values.tolist()
                    for var_name, var_values in probe_vars.items()
                }

        return result_dict

    def to_dataframe(self, include_probes: bool = False):
        """
        Export results as a pandas DataFrame.

        Args:
            include_probes: Whether to include probe columns

        Returns:
            pandas DataFrame with time as index

        Raises:
            ImportError: If pandas is not installed

        Example:
            >>> df = result.to_dataframe()
            >>> df.plot(x='time', y=['state1', 'state2'])
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install with: pip install pandas"
            )

        # Create base dataframe with time and states
        data = {'time': self.times}
        for i, name in enumerate(self.state_names):
            data[name] = self.values[:, i]

        df = pd.DataFrame(data)

        # Add probe data if requested
        if include_probes and self.probe_data:
            for probe_name, probe_vars in self.probe_data.items():
                for var_name, var_values in probe_vars.items():
                    # Use probe_name as prefix if multiple probes
                    if len(self.probe_data) > 1:
                        col_name = f"{probe_name}.{var_name}"
                    else:
                        col_name = var_name
                    df[col_name] = var_values

        return df

    def get_probe_dataframe(self, probe_name: Optional[str] = None):
        """
        Get a DataFrame for a specific probe or all probes.

        Args:
            probe_name: Name of the probe (None for all probes)

        Returns:
            pandas DataFrame with probe data

        Raises:
            ImportError: If pandas is not installed
            ValueError: If probe_name doesn't exist

        Example:
            >>> df = result.get_probe_dataframe("control_signals")
            >>> print(df.columns)
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for get_probe_dataframe(). "
                "Install with: pip install pandas"
            )

        if not self.probe_data:
            raise ValueError("No probe data available")

        if probe_name is None:
            # Return all probe data
            data = {'time': self.times}
            for pname, probe_vars in self.probe_data.items():
                for var_name, var_values in probe_vars.items():
                    col_name = f"{pname}.{var_name}" if len(self.probe_data) > 1 else var_name
                    data[col_name] = var_values
            return pd.DataFrame(data)
        else:
            # Return specific probe data
            if probe_name not in self.probe_data:
                raise ValueError(
                    f"Probe '{probe_name}' not found. "
                    f"Available probes: {list(self.probe_data.keys())}"
                )

            data = {'time': self.times}
            for var_name, var_values in self.probe_data[probe_name].items():
                data[var_name] = var_values

            return pd.DataFrame(data)

    def to_csv(
        self,
        filename: Union[str, Path],
        include_probes: bool = False,
        **kwargs
    ) -> None:
        """
        Export results to a CSV file.

        Args:
            filename: Output CSV file path
            include_probes: Whether to include probe data
            **kwargs: Additional arguments passed to pandas.to_csv()

        Example:
            >>> result.to_csv("results.csv")
            >>> result.to_csv("results_with_probes.csv", include_probes=True, index=False)
        """
        df = self.to_dataframe(include_probes=include_probes)

        # Default to not including row indices
        if 'index' not in kwargs:
            kwargs['index'] = False

        df.to_csv(filename, **kwargs)

    def save_probe_csv(
        self,
        probe_name: str,
        filename: Union[str, Path],
        **kwargs
    ) -> None:
        """
        Save a specific probe's data to CSV.

        Args:
            probe_name: Name of the probe
            filename: Output CSV file path
            **kwargs: Additional arguments passed to pandas.to_csv()

        Example:
            >>> result.save_probe_csv("control_signals", "control_data.csv")
        """
        df = self.get_probe_dataframe(probe_name)

        if 'index' not in kwargs:
            kwargs['index'] = False

        df.to_csv(filename, **kwargs)

    def get_state(self, state_name: str) -> np.ndarray:
        """
        Get time series data for a specific state.

        Args:
            state_name: Name of the state variable

        Returns:
            NumPy array of state values over time

        Raises:
            ValueError: If state_name not found

        Example:
            >>> position = result.get_state("plant.x1")
            >>> velocity = result.get_state("plant.x2")
        """
        try:
            idx = self.state_names.index(state_name)
            return self.values[:, idx].copy()
        except ValueError:
            raise ValueError(
                f"State '{state_name}' not found. "
                f"Available states: {self.state_names}"
            )

    def get_states(self, state_names: List[str]) -> np.ndarray:
        """
        Get time series data for multiple states.

        Args:
            state_names: List of state variable names

        Returns:
            2D NumPy array of shape [n_times, n_states]

        Example:
            >>> data = result.get_states(["plant.x1", "plant.x2"])
            >>> print(data.shape)
        """
        indices = []
        for name in state_names:
            try:
                indices.append(self.state_names.index(name))
            except ValueError:
                raise ValueError(f"State '{name}' not found")

        return self.values[:, indices].copy()

    def slice_time(
        self,
        t_start: Optional[float] = None,
        t_end: Optional[float] = None
    ) -> 'SimulationResult':
        """
        Create a new SimulationResult with data in a time range.

        Args:
            t_start: Start time (None for beginning)
            t_end: End time (None for end)

        Returns:
            New SimulationResult with sliced data

        Example:
            >>> # Get data from t=5 to t=10
            >>> sliced = result.slice_time(t_start=5.0, t_end=10.0)
        """
        # Find time indices
        if t_start is None:
            start_idx = 0
        else:
            start_idx = np.searchsorted(self.times, t_start)

        if t_end is None:
            end_idx = len(self.times)
        else:
            end_idx = np.searchsorted(self.times, t_end)

        # Slice main data
        sliced_times = self.times[start_idx:end_idx]
        sliced_values = self.values[start_idx:end_idx, :]

        # Slice probe data
        sliced_probe_data = {}
        for probe_name, probe_vars in self.probe_data.items():
            sliced_probe_data[probe_name] = {
                var_name: var_values[start_idx:end_idx]
                for var_name, var_values in probe_vars.items()
            }

        # Create new result
        return SimulationResult(
            times=sliced_times,
            values=sliced_values,
            state_names=self.state_names.copy(),
            probe_data=sliced_probe_data,
            system_name=self.system_name,
            solver=self.solver,
            metadata={**self.metadata, 'sliced': True}
        )

    def summary(self) -> Dict[str, Any]:
        """
        Get statistical summary of the simulation results.

        Returns:
            Dictionary with statistics for each state

        Example:
            >>> stats = result.summary()
            >>> print(stats['plant.x1'])
        """
        summary_dict = {}

        for i, name in enumerate(self.state_names):
            data = self.values[:, i]
            summary_dict[name] = {
                'mean': float(np.mean(data)),
                'std': float(np.std(data)),
                'min': float(np.min(data)),
                'max': float(np.max(data)),
                'final': float(data[-1])
            }

        return summary_dict

    def print_summary(self) -> None:
        """
        Print a formatted summary of simulation results.

        Example:
            >>> result.print_summary()
        """
        print(f"Simulation Results: {self.system_name}")
        print(f"  Solver: {self.solver}")
        print(f"  Time span: [{self.times[0]:.2f}, {self.times[-1]:.2f}]")
        print(f"  Time points: {len(self.times)}")
        print(f"  States: {len(self.state_names)}")
        print(f"  Probes: {len(self.probe_data)}")
        print()

        if self.state_names:
            print("State Statistics (first 10):")
            summary = self.summary()
            for i, name in enumerate(self.state_names[:10]):
                stats = summary[name]
                print(
                    f"  {name:30s} "
                    f"mean={stats['mean']:8.3f} "
                    f"std={stats['std']:8.3f} "
                    f"range=[{stats['min']:8.3f}, {stats['max']:8.3f}]"
                )

            if len(self.state_names) > 10:
                print(f"  ... ({len(self.state_names) - 10} more states)")

        if self.probe_data:
            print()
            print("Probe Data:")
            for probe_name, probe_vars in self.probe_data.items():
                print(f"  {probe_name}: {len(probe_vars)} variables")
                for var_name in list(probe_vars.keys())[:5]:
                    print(f"    - {var_name}")
                if len(probe_vars) > 5:
                    print(f"    ... ({len(probe_vars) - 5} more)")
