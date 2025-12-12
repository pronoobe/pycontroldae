"""
Julia Backend Initialization Module

This module provides a singleton interface to the Julia environment.
It lazily initializes the Julia runtime and loads required packages on first use.

Note: The backend will automatically install ModelingToolkit and DifferentialEquations
Julia packages if they are not present. This may take 5-10 minutes on first run.
"""

from typing import Optional


class JuliaBackend:
    """
    Singleton class for managing Julia environment initialization.

    Ensures that Julia is initialized only once and provides access to the
    Julia Main module with ModelingToolkit and DifferentialEquations loaded.
    """

    _instance: Optional['JuliaBackend'] = None
    _jl = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the singleton (actual Julia init happens lazily)."""
        if not JuliaBackend._initialized:
            self._init_julia()
            JuliaBackend._initialized = True

    def _init_julia(self):
        """
        Initialize Julia environment and load required packages.

        This method:
        1. Imports juliacall and gets the Main module
        2. Installs required Julia packages (ModelingToolkit, DifferentialEquations) if needed
        3. Loads the packages
        4. Imports convenient aliases for time variable (t) and derivative operator (D)

        Note: Package installation may take 5-10 minutes on first run as these are large packages.
        """
        print("Initializing Julia backend...")

        try:
            from juliacall import Main as jl
            JuliaBackend._jl = jl
            print("Julia runtime loaded successfully.")

            # Install required packages if not already present
            print("\nChecking and installing required Julia packages...")
            print("This may take several minutes on first run...\n")

            jl.seval('import Pkg')
            jl.seval('Pkg.add(["ModelingToolkit", "DifferentialEquations"])')
            print("[PASS] Required packages installed/verified\n")

            # Load ModelingToolkit.jl
            print("Loading ModelingToolkit.jl...")
            jl.seval("using ModelingToolkit")
            print("[PASS] ModelingToolkit.jl loaded")

            # Load DifferentialEquations.jl
            print("Loading DifferentialEquations.jl...")
            jl.seval("using DifferentialEquations")
            print("[PASS] DifferentialEquations.jl loaded")

            # Import convenient time and derivative operators
            print("Importing symbolic operators (t, D)...")
            jl.seval("using ModelingToolkit: t_nounits as t, D_nounits as D")
            print("[PASS] Symbolic operators imported")

            print("\n" + "="*60)
            print("Julia backend initialization complete!")
            print("="*60 + "\n")

        except ImportError as e:
            raise ImportError(
                "Failed to import juliacall. "
                "Please install it with: pip install juliacall"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Julia backend: {e}\n"
                "This may be due to missing Julia installation or package issues."
            ) from e

    @property
    def jl(self):
        """Get the Julia Main module."""
        if JuliaBackend._jl is None:
            raise RuntimeError("Julia backend not initialized")
        return JuliaBackend._jl


# Module-level convenience function
def get_jl():
    """
    Get the Julia Main module with ModelingToolkit and DifferentialEquations loaded.

    This function ensures the Julia backend is initialized and returns the Julia
    Main module for use in other parts of the library.

    Returns:
        The Julia Main module (juliacall.Main)

    Example:
        >>> jl = get_jl()
        >>> jl.seval("println('Hello from Julia!')")
    """
    backend = JuliaBackend()
    return backend.jl
