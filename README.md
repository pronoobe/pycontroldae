# pycontroldae - Python Control System Modeling and Simulation Library

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Julia](https://img.shields.io/badge/Julia-1.9+-purple.svg)](https://julialang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**pycontroldae** is a powerful Python library for building, simulating, and analyzing control systems. It combines Python's ease of use with Julia's high-performance computing capabilities, leveraging ModelingToolkit.jl for automatic differential-algebraic equation (DAE) index reduction and symbolic simplification.

## ✨ Core Features

### 🎯 Modular Design
- **Hierarchical Module System**: Define reusable control components using the `Module` class
- **CompositeModule Encapsulation**: Combine multiple modules into composite modules with arbitrary nesting levels
- **Flexible Port-Based Connections**: Pythonic `>>` / `<<` operators with IDE autocomplete support
  - Port-level: `pid.output >> plant.input` (explicit port connections)
  - Module-level: `source >> pid >> plant` (using default ports)
  - String-based: `"pid.output ~ plant.input"` (backward compatible)
- **Automatic DAE Simplification**: Built-in `structural_simplify` automatically handles algebraic constraints

### 📦 Rich Control Block Library
- **Controllers**: PID, PI, PD, Gain, Limiter
- **Signal Sources**: Step, Ramp, Sin, Pulse, Constant
- **Linear Systems**: StateSpace (supports both SISO and MIMO)
- **Basic Modules**: Sum, Integrator, Derivative
- **Custom Modules**: Easily define arbitrary nonlinear dynamic systems

### 🔬 Advanced Simulation Features
- **Event System**:
  - `TimeEvent`: Time-triggered events (gain scheduling, parameter switching)
  - `ContinuousEvent`: Continuous condition-triggered events (safety limits, state monitoring)
- **Data Probes**:
  - Observe arbitrary variables (including nested module internals)
  - Supports single, list, and dictionary configurations
  - Custom variable naming
- **Powerful Solvers**:
  - Rodas5 (recommended for stiff/DAE systems)
  - Tsit5, TRBDF2, QNDF, and more

### 📊 Flexible Data Export
- **NumPy Arrays**: `result.to_numpy()` - Raw numerical data
- **pandas DataFrame**: `result.to_dataframe()` - Data science workflows
- **CSV Files**: `result.to_csv()` - External tool integration
- **Python Dictionary**: `result.to_dict()` - JSON serialization
- **Probe-specific Export**: `result.get_probe_dataframe()`, `result.save_probe_csv()`

### 📈 Data Analysis Tools
- **Time Slicing**: `result.slice_time(t_start, t_end)`
- **Statistical Summary**: `result.summary()` - mean, std, min, max
- **State Extraction**: `result.get_state(name)`, `result.get_states(names)`
- **Formatted Output**: `result.print_summary()`

---

## 📥 Installation

### Prerequisites

- Python 3.8+
- Julia 1.9+ (will be installed automatically)

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/pronoobe/pycontroldae.git
cd pycontroldae

# Install dependencies
pip install numpy pandas matplotlib

# First run will automatically install Julia packages (may take a few minutes)
python -c "from pycontroldae.core import get_jl; get_jl()"
```

### Julia Package Dependencies (Auto-installed)
- ModelingToolkit.jl - Symbolic modeling and automatic differentiation
- DifferentialEquations.jl - High-performance ODE/DAE solvers
- PythonCall.jl - Seamless Python-Julia interoperability

---

## 🚀 Quick Start

### Example 1: RC Circuit Simulation

```python
from pycontroldae.blocks import StateSpace, Step
from pycontroldae.core import System, Simulator
import numpy as np

# Define RC circuit (first-order system)
# dV/dt = (I - V/R)/C
R = 1000.0  # Ohms
C = 1e-6    # Farads
A = np.array([[-1/(R*C)]])
B = np.array([[1/C]])
C_mat = np.array([[1.0]])
D_mat = np.array([[0.0]])

rc_circuit = StateSpace(
    name="rc",
    A=A, B=B, C=C_mat, D=D_mat,
    initial_state=np.array([0.0])
)

# Input signal: 5V step
input_signal = Step(name="input", amplitude=5.0, step_time=0.0)
input_signal.set_output("signal")

# Build system
system = System("rc_system")
system.add_module(rc_circuit)
system.add_module(input_signal)
# Use Port API for connections (recommended)
system.connect(input_signal.signal >> rc_circuit.u1)

# Compile and simulate
system.compile()
simulator = Simulator(system)
result = simulator.run(t_span=(0.0, 0.01), dt=0.0001)

# Export data
df = result.to_dataframe()
result.to_csv("rc_circuit.csv")
result.print_summary()
```

### Example 2: PID Temperature Control

```python
from pycontroldae.blocks import PID, Gain, Sum, Step, StateSpace
from pycontroldae.core import System, Simulator, DataProbe
import numpy as np

# Create modules
setpoint = Step(name="sp", amplitude=80.0, step_time=2.0)
setpoint.set_output("signal")

error_calc = Sum(name="error", num_inputs=2, signs=[+1, -1])

pid = PID(name="pid", Kp=2.0, Ki=0.5, Kd=0.1, integral_limit=50.0)

plant = StateSpace(
    name="plant",
    A=np.array([[-0.3]]),
    B=np.array([[1.0]]),
    C=np.array([[1.0]]),
    D=np.array([[0.0]]),
    initial_state=np.array([25.0])
)

# Build system
system = System("temp_control")
for mod in [setpoint, error_calc, pid, plant]:
    system.add_module(mod)

# Define connections using Port API (recommended)
system.connect(setpoint.signal >> error_calc.input1)
system.connect(plant.y1 >> error_calc.input2)
system.connect(error_calc.output >> pid.error)
system.connect(pid.output >> plant.u1)

# Configure data probe
probe = DataProbe(
    variables=["plant.y1", "pid.output", "error.output"],
    names=["Temperature", "Control_Signal", "Error"],
    description="Main control variables"
)

# Compile and simulate
system.compile()
simulator = Simulator(system)
result = simulator.run(
    t_span=(0.0, 20.0),
    dt=0.1,
    probes=probe
)

# Get probe data
probe_df = result.get_probe_dataframe()
print(probe_df.head())

# Save results
result.to_csv("temp_control.csv", include_probes=True)
```

### Example 3: Port-Based Connections (Recommended)

```python
from pycontroldae.blocks import PID, Limiter, StateSpace, Step, Sum
from pycontroldae.core import CompositeModule, System, Simulator, DataProbe
import numpy as np

# Create a reusable PID controller CompositeModule using Port API
def create_pid_controller(name, Kp=2.0, Ki=0.5, Kd=0.1):
    controller = CompositeModule(name)

    # Create sub-modules
    pid = PID(name=f"{name}_core", Kp=Kp, Ki=Ki, Kd=Kd)
    limiter = Limiter(name=f"{name}_lim", min_value=0.0, max_value=100.0)

    controller.add_module(pid)
    controller.add_module(limiter)

    # Connect using Port objects (NEW!)
    controller.add_connection(pid.output >> limiter.input)

    # Expose interfaces using Port objects (NEW!)
    controller.expose_input("error", pid.error)
    controller.expose_output("control", limiter.output)

    return controller

# Create system components
setpoint = Step(name="sp", amplitude=80.0, step_time=2.0)
setpoint.set_output("signal")

error_calc = Sum(name="error", num_inputs=2, signs=[+1, -1])
pid_ctrl = create_pid_controller("pid", Kp=3.0, Ki=0.8, Kd=0.3)

plant = StateSpace(
    name="plant",
    A=np.array([[-0.3]]),
    B=np.array([[1.0]]),
    C=np.array([[1.0]]),
    D=np.array([[0.0]]),
    initial_state=np.array([25.0])
)

# Build system with flexible Port-based connections
system = System("temp_control")
for mod in [setpoint, error_calc, pid_ctrl, plant]:
    system.add_module(mod)

# Method 1: Port-to-Port connections (explicit, with IDE autocomplete)
system.connect(setpoint.signal >> error_calc.input1)
system.connect(pid_ctrl.control >> plant.u1)

# Method 2: String-based connections (backward compatible)
system.connect("plant.y1 ~ error.input2")

# Method 3: Module-level connections (using default ports)
system.connect(error_calc >> pid_ctrl)

# Configure DataProbe using Port objects
probe = DataProbe(
    variables=[str(plant.y1), str(pid_ctrl.control)],
    names=["Temperature", "Control"],
    description="Main signals"
)

# Simulate
system.compile()
simulator = Simulator(system)
result = simulator.run(t_span=(0.0, 20.0), dt=0.1, probes=probe)

# Analyze
result.print_summary()
result.to_csv("temp_control_port_api.csv", include_probes=True)
```

**Benefits of Port API:**
- **IDE Autocomplete**: Type `pid.` and see all available ports
- **Type Safety**: Catch errors at Python level, not Julia level
- **Refactoring-Friendly**: Rename variables with confidence
- **More Pythonic**: Feels natural to Python developers

### Example 4: CompositeModule Encapsulation (Classic API)

```python
from pycontroldae.blocks import PID, Limiter
from pycontroldae.core import CompositeModule, System, Simulator

# Create reusable temperature controller
def create_temp_controller(name, Kp=3.0, Ki=0.8, Kd=0.3):
    controller = CompositeModule(name=name)

    pid = PID(name="pid", Kp=Kp, Ki=Ki, Kd=Kd, integral_limit=100.0)
    limiter = Limiter(name="lim", min_value=0.0, max_value=100.0)

    controller.add_module(pid)
    controller.add_module(limiter)
    controller.add_connection("pid.output ~ lim.input")

    # Expose interfaces
    controller.expose_input("error", "pid.error")
    controller.expose_output("control", "lim.output")

    return controller

# Create multiple instances
ctrl_A = create_temp_controller("ctrl_A", Kp=3.0)
ctrl_B = create_temp_controller("ctrl_B", Kp=4.0)

# Build and simulate...
ctrl_A.build()
ctrl_B.build()
```

### Example 5: Event System

```python
from pycontroldae.core import at_time, when_condition

# Time event: Increase gain at t=10s
def increase_gain(integrator):
    print("Increasing PID gain at t=10s")
    return {"pid.Kp": 5.0, "pid.Ki": 1.5}

system.add_event(at_time(10.0, increase_gain))

# Continuous event: Limit output when temperature exceeds 80°C
def check_high_temp(u, t, integrator):
    return u[0] - 80.0  # Zero-crossing detection

def limit_output(integrator):
    print("Temperature too high! Limiting output")
    return {"limiter.max_val": 50.0}

system.add_event(when_condition(check_high_temp, limit_output, direction=1))
```

### Example 6: DAE Systems with Algebraic Constraints

```python
from pycontroldae.core import Module, System, Simulator
from pycontroldae.blocks import Step
import matplotlib.pyplot as plt

# Define Mass module
class Mass(Module):
    """Mass block with position, velocity, and force inputs"""
    def __init__(self, name, mass=1.0, damping=0.1):
        super().__init__(name)

        # States
        self.add_state("x", 0.0)     # Position
        self.add_state("v", 0.0)     # Velocity

        # Parameters
        self.add_param("m", mass)
        self.add_param("b", damping)

        # Inputs (algebraic)
        self.add_state("F_ext", 0.0)
        self.add_state("F_spring", 0.0)

        # Outputs (algebraic constraints)
        self.add_state("x_out", 0.0)
        self.add_state("v_out", 0.0)

        # Differential equations
        self.add_equation("D(v) ~ (F_ext + F_spring - b*v) / m")
        self.add_equation("D(x) ~ v")

        # Algebraic constraints
        self.add_equation("0 ~ x_out - x")
        self.add_equation("0 ~ v_out - v")

# Define Spring module (pure algebraic)
class Spring(Module):
    """Spring with algebraic force constraint"""
    def __init__(self, name, stiffness=10.0):
        super().__init__(name)

        self.add_param("k", stiffness)

        # Inputs
        self.add_state("x1", 0.0)
        self.add_state("x2", 0.0)

        # Outputs
        self.add_state("F1", 0.0)
        self.add_state("F2", 0.0)
        self.add_state("F", 0.0)

        # Algebraic constraints (Hooke's law)
        self.add_equation("0 ~ F + k * (x2 - x1)")
        self.add_equation("0 ~ F1 + F")
        self.add_equation("0 ~ F2 - F")

# Build double-mass spring system
system = System("double_mass_spring")

force_input = Step(name="force", amplitude=10.0, step_time=0.0)
force_input.set_output("signal")

mass1 = Mass(name="m1", mass=1.0, damping=0.2)
mass2 = Mass(name="m2", mass=2.0, damping=0.3)
spring = Spring(name="spring", stiffness=20.0)

system.add_module(force_input)
system.add_module(mass1)
system.add_module(mass2)
system.add_module(spring)

# Use Port API for connections
system.connect(force_input.signal >> mass1.F_ext)
system.connect(mass1.x_out >> spring.x1)
system.connect(mass2.x_out >> spring.x2)
system.connect(spring.F1 >> mass1.F_spring)
system.connect(spring.F2 >> mass2.F_spring)
system.connect("0.0 ~ m2.F_ext")  # No external force on mass2

# Compile with automatic DAE simplification
system.compile()  # structural_simplify handles algebraic constraints

# Simulate
simulator = Simulator(system)
result = simulator.run(t_span=(0.0, 10.0), dt=0.01, solver="Rodas5")

# Plot results
times = result.times
m1_x = result.get_state("m1.x")
m2_x = result.get_state("m2.x")

plt.plot(times, m1_x, label='Mass 1')
plt.plot(times, m2_x, label='Mass 2')
plt.plot(times, m2_x - m1_x, label='Spring displacement')
plt.xlabel('Time (s)')
plt.ylabel('Position (m)')
plt.legend()
plt.show()
```

**Key Points about DAE Systems:**

1. **Differential States**: Variables with time derivatives (`D(x)`, `D(v)`)
2. **Algebraic Variables**: Variables defined by algebraic constraints (`0 ~ F + k*(x2-x1)`)
3. **Automatic Simplification**: `structural_simplify` automatically:
   - Eliminates algebraic variables
   - Reduces DAE index
   - Generates minimal ODE system
4. **Port-Based Connections**: Use `>>` operator for clean, type-safe module connections
5. **Recommended Solver**: Use `Rodas5` for DAE/stiff systems

**System Structure:**
```
Original: 4 differential equations + multiple algebraic constraints (DAE)
After structural_simplify: 4 differential equations (ODE)
```

The library automatically handles the complex mathematics of DAE-to-ODE conversion, allowing you to focus on system modeling.

---

## 📖 Detailed API Documentation

### Core Classes

#### `Module`

Base class for defining basic control modules.

```python
class Module:
    def __init__(self, name: str)
    def add_state(self, name: str, default: float = 0.0) -> Module
    def add_param(self, name: str, default: float) -> Module
    def add_equation(self, eq_str: str) -> Module
    def build() -> Any  # Returns Julia ODESystem
```

**Method Descriptions**:

- `add_state(name, default)`: Add a state variable
  - `name`: Variable name (string)
  - `default`: Default initial value
  - Returns `self` for method chaining

- `add_param(name, default)`: Add a parameter
  - `name`: Parameter name
  - `default`: Default value

- `add_equation(eq_str)`: Add a differential equation
  - `eq_str`: Equation string in Julia syntax, e.g., `"D(x) ~ -k*x"`

- `build()`: Build Julia ODESystem object

**Example**:

```python
# Create first-order system
module = Module("first_order")
module.add_state("x", 0.0)
module.add_param("k", 1.0)
module.add_state("u", 0.0)  # Input
module.add_equation("D(x) ~ -k*x + u")
module.build()
```

---

#### `CompositeModule`

Encapsulate multiple modules as a composite module with nesting support.

```python
class CompositeModule(Module):
    def __init__(self, name: str)
    def add_module(self, module: Module) -> None
    def add_connection(self, connection: str) -> None
    def expose_input(self, external_name: str, internal_path: str) -> None
    def expose_output(self, external_name: str, internal_path: str) -> None
    def build() -> Any
```

**Method Descriptions**:

- `add_module(module)`: Add a sub-module (can be Module or CompositeModule)

- `add_connection(connection)`: Define internal connection
  - Format: `"module1.output ~ module2.input"`

- `expose_input(external_name, internal_path)`: Expose input interface
  - `external_name`: External access name
  - `internal_path`: Internal module path, e.g., `"pid.error"`

- `expose_output(external_name, internal_path)`: Expose output interface

**Example**:

```python
# Create nested CompositeModule
outer = CompositeModule("outer")
inner = CompositeModule("inner")

pid = PID(name="pid", Kp=2.0, Ki=0.5, Kd=0.0)
gain = Gain(name="gain", K=0.8)

inner.add_module(pid)
inner.add_module(gain)
inner.add_connection("pid.output ~ gain.input")
inner.expose_input("error", "pid.error")
inner.expose_output("control", "gain.output")

outer.add_module(inner)
outer.expose_input("error", "inner.error")
outer.expose_output("control", "inner.control")

outer.build()
```

**Connection Methods**:

```python
# Method 1: Port-to-Port connections (Recommended - IDE autocomplete!)
system.connect(pid.output >> plant.input)

# Method 2: Module-level connections (using default ports)
source >> module1 >> module2 >> sink
# Equivalent to:
# system.connect(source.output >> module1.input)
# system.connect(module1.output >> module2.input)
# system.connect(module2.output >> sink.input)

# Method 3: String-based connections (backward compatible)
system.connect("source.output ~ module1.input")
```

**For CompositeModule:**

```python
# Port-based internal connections (NEW!)
composite.add_connection(pid.output >> limiter.input)

# Port-based interface exposure (NEW!)
composite.expose_input("error", pid.error)
composite.expose_output("control", limiter.output)

# String-based (still supported)
composite.add_connection("pid.output ~ limiter.input")
composite.expose_input("error", "pid.error")
composite.expose_output("control", "limiter.output")
```

---

#### `System`

Compose multiple modules and manage connections.

```python
class System:
    def __init__(self, name: str = "system")
    def add_module(self, module: Module) -> System
    def connect(self, connection_expr: str) -> System
    def add_event(self, event: Union[TimeEvent, ContinuousEvent]) -> None
    def compile() -> Any  # Returns simplified Julia ODESystem

    @property
    def modules(self) -> List[Module]

    @property
    def connections(self) -> List[str]

    @property
    def events(self) -> List[Union[TimeEvent, ContinuousEvent]]
```

**Method Descriptions**:

- `add_module(module)`: Add module to system

- `connect(connection_expr)`: Define inter-module connection
  - Accepts multiple formats:
    - **Port objects** (recommended): `system.connect(mod1.output >> mod2.input)`
    - **Module operators**: `system.connect(mod1 >> mod2)` (uses default ports)
    - **String-based**: `system.connect("module1.output ~ module2.input")` (backward compatible)

- `add_event(event)`: Add event (time event or continuous event)

- `compile()`: Compile system
  - Automatically calls `build()` on all modules
  - Creates composed ODESystem
  - **Critical**: Applies `structural_simplify` for DAE index reduction

**Example**:

```python
system = System("my_system")
system.add_module(module1)
system.add_module(module2)
system.connect("module1.output ~ module2.input")
compiled = system.compile()
```

---

#### `Simulator`

Execute system simulation and return results.

```python
class Simulator:
    def __init__(self, system: System)

    def run(
        self,
        t_span: Tuple[float, float],
        u0: Optional[Dict[str, float]] = None,
        params: Optional[Dict[str, float]] = None,
        dt: Optional[float] = None,
        solver: str = "Rodas5",
        probes: Optional[Union[DataProbe, List[DataProbe], Dict[str, DataProbe]]] = None,
        return_result: bool = True
    ) -> Union[SimulationResult, Tuple[np.ndarray, np.ndarray]]
```

**Parameter Descriptions**:

- `t_span`: Time range tuple `(t_start, t_end)`

- `u0`: Initial conditions dictionary, e.g., `{"module.state": value}`
  - Optional, defaults to module-defined defaults

- `params`: Parameter values dictionary, e.g., `{"module.param": value}`
  - Optional, defaults to module-defined defaults

- `dt`: Time step for saving solution
  - `None`: Adaptive time stepping
  - `float`: Fixed time step

- `solver`: Solver name
  - `"Rodas5"`: Recommended for stiff DAE systems
  - `"Tsit5"`: Non-stiff ODEs
  - `"TRBDF2"`, `"QNDF"`: Other stiff solvers

- `probes`: Data probes
  - Single `DataProbe` object
  - List of `DataProbe` objects
  - `Dict[str, DataProbe]` (named probes)

- `return_result`: Whether to return `SimulationResult` object
  - `True` (default): Returns `SimulationResult`
  - `False`: Returns `(times, values)` tuple (backward compatible)

**Return Value**:

- `SimulationResult` object (when `return_result=True`)
- `(times, values)` tuple (when `return_result=False`)

**Example**:

```python
simulator = Simulator(system)

# Basic usage
result = simulator.run(t_span=(0.0, 10.0), dt=0.1)

# Specify initial conditions and parameters
result = simulator.run(
    t_span=(0.0, 10.0),
    u0={"plant.x1": 25.0},
    params={"pid.Kp": 3.0},
    dt=0.1
)

# Use probes
probe = DataProbe(variables=["plant.y1", "pid.output"])
result = simulator.run(t_span=(0.0, 10.0), probes=probe)

# Backward compatible mode
times, values = simulator.run(t_span=(0.0, 10.0), return_result=False)
```

---

### Control Blocks

#### `PID`

PID controller.

```python
PID(
    name: str,
    Kp: float = 1.0,
    Ki: float = 0.0,
    Kd: float = 0.0,
    integral_limit: float = 100.0,
    derivative_filter: float = 0.01
)
```

**Parameters**:
- `Kp`: Proportional gain
- `Ki`: Integral gain
- `Kd`: Derivative gain
- `integral_limit`: Integral saturation limit
- `derivative_filter`: Derivative filter time constant

**Interfaces**:
- Input: `error`
- Output: `output`

**Example**:

```python
pid = PID(name="controller", Kp=2.0, Ki=0.5, Kd=0.1)
pid.build()
```

---

#### `StateSpace`

Linear state-space model.

```python
StateSpace(
    name: str,
    A: np.ndarray,
    B: np.ndarray,
    C: np.ndarray,
    D: np.ndarray,
    initial_state: Optional[np.ndarray] = None
)
```

**Parameters**:
- `A`: State matrix (n×n)
- `B`: Input matrix (n×m)
- `C`: Output matrix (p×n)
- `D`: Feedthrough matrix (p×m)
- `initial_state`: Initial state vector (length n)

**Interfaces**:
- Inputs: `u1`, `u2`, ..., `um` (m inputs)
- Outputs: `y1`, `y2`, ..., `yp` (p outputs)

**Example**:

```python
# SISO system
A = np.array([[-1.0]])
B = np.array([[1.0]])
C = np.array([[1.0]])
D = np.array([[0.0]])
plant = StateSpace(name="plant", A=A, B=B, C=C, D=D)

# MIMO system (2 inputs, 2 outputs)
A = np.array([[-0.5, 0.1], [0.2, -0.8]])
B = np.array([[1.0, 0.1], [0.2, 1.0]])
C = np.array([[1.0, 0.0], [0.0, 1.0]])
D = np.zeros((2, 2))
plant = StateSpace(name="mimo_plant", A=A, B=B, C=C, D=D)
```

---

#### `Gain`

Gain block.

```python
Gain(name: str, K: float = 1.0)
```

**Interfaces**:
- Input: `input`
- Output: `output` (= K × input)

---

#### `Sum`

Summation block.

```python
Sum(name: str, num_inputs: int = 2, signs: List[int] = None)
```

**Parameters**:
- `num_inputs`: Number of inputs
- `signs`: Sign list, e.g., `[+1, -1]` for input1 - input2

**Interfaces**:
- Inputs: `input1`, `input2`, ..., `inputN`
- Output: `output` (= sum(signs[i] × input[i]))

**Example**:

```python
# Error calculation: setpoint - measurement
error = Sum(name="error", num_inputs=2, signs=[+1, -1])
system.connect("setpoint.signal ~ error.input1")
system.connect("plant.y1 ~ error.input2")
```

---

#### `Limiter`

Saturation limiter.

```python
Limiter(name: str, min_value: float = -100.0, max_value: float = 100.0)
```

**Interfaces**:
- Input: `input`
- Output: `output` (limited to [min_value, max_value])

---

#### `Step`

Step signal.

```python
Step(name: str, amplitude: float = 1.0, step_time: float = 0.0)
```

**Must call before use**:

```python
step = Step(name="sp", amplitude=10.0, step_time=2.0)
step.set_output("signal")  # Required!
step.build()
```

**Interfaces**:
- Output: `signal`

---

#### `Ramp`

Ramp signal.

```python
Ramp(name: str, slope: float = 1.0, start_time: float = 0.0)
```

**Must call before use**:

```python
ramp = Ramp(name="ref", slope=0.5, start_time=1.0)
ramp.set_output("signal")
ramp.build()
```

---

#### `Sin`

Sinusoidal signal.

```python
Sin(name: str, amplitude: float = 1.0, frequency: float = 1.0, phase: float = 0.0)
```

**Must call before use**:

```python
sin_wave = Sin(name="disturbance", amplitude=5.0, frequency=0.3)
sin_wave.set_output("signal")
sin_wave.build()
```

---

#### `Integrator`

Integrator block.

```python
Integrator(name: str, initial_value: float = 0.0)
```

**Interfaces**:
- Input: `input`
- Output: `output` (= ∫input dt)

---

### Event System

#### `TimeEvent` / `at_time`

Time-triggered event.

```python
def at_time(time: float, callback: Callable) -> TimeEvent
```

**Parameters**:
- `time`: Trigger time
- `callback`: Callback function with signature `callback(integrator) -> Dict[str, float]`
  - Returns dictionary: `{"module.param": new_value}`

**Example**:

```python
def increase_gain(integrator):
    print("Switching to aggressive tuning")
    return {
        "pid.Kp": 5.0,
        "pid.Ki": 1.5,
        "pid.Kd": 0.8
    }

system.add_event(at_time(10.0, increase_gain))
```

---

#### `ContinuousEvent` / `when_condition`

Continuous condition-triggered event.

```python
def when_condition(
    condition: Callable,
    affect: Callable,
    direction: int = 0
) -> ContinuousEvent
```

**Parameters**:
- `condition`: Condition function with signature `condition(u, t, integrator) -> float`
  - Triggers when return value crosses zero
- `affect`: Effect function with signature `affect(integrator) -> Dict[str, float]`
  - Returns parameter update dictionary
- `direction`: Zero-crossing direction
  - `0`: Both directions (up-crossing and down-crossing)
  - `1`: Up-crossing (condition goes from negative to positive)
  - `-1`: Down-crossing (condition goes from positive to negative)

**Example**:

```python
# Limit output when temperature exceeds 80°C
def check_high_temp(u, t, integrator):
    return u[0] - 80.0  # u[0] is first state variable

def limit_heating(integrator):
    print("Temperature limit exceeded!")
    return {"limiter.max_val": 50.0}

system.add_event(when_condition(
    check_high_temp,
    limit_heating,
    direction=1  # Only trigger on up-crossing
))
```

---

### Data Probes and Results

#### `DataProbe`

Configure variable observation.

```python
class DataProbe:
    def __init__(
        self,
        variables: List[str],
        names: Optional[List[str]] = None,
        description: str = ""
    )
```

**Parameters**:
- `variables`: List of variables to observe, e.g., `["plant.y1", "pid.output"]`
- `names`: Custom variable names (optional)
- `description`: Probe description (optional)

**Example**:

```python
# Basic usage
probe = DataProbe(variables=["plant.y1", "pid.output"])

# Custom names
probe = DataProbe(
    variables=["plant.y1", "pid.output", "error.output"],
    names=["Temperature", "Control", "Error"],
    description="Main control loop"
)

# Multiple probes (list)
probes = [
    DataProbe(variables=["pid.output"], names=["PID"]),
    DataProbe(variables=["plant.y1"], names=["Plant"])
]

# Named probes (dictionary)
probes = {
    "controller": DataProbe(variables=["pid.output", "pid.integral"]),
    "plant": DataProbe(variables=["plant.y1", "plant.x1"])
}

result = simulator.run(t_span=(0, 10), probes=probes)
```

---

#### `SimulationResult`

Simulation result container.

```python
class SimulationResult:
    # Attributes
    times: np.ndarray           # Time vector
    values: np.ndarray          # State values matrix [n_times, n_states]
    state_names: List[str]      # State name list
    probe_data: Dict[str, Dict[str, np.ndarray]]  # Probe data
    system_name: str            # System name
    solver: str                 # Solver name
    metadata: Dict[str, Any]    # Metadata
```

**Main Methods**:

##### `to_numpy()`

Export as NumPy arrays.

```python
def to_numpy(self) -> Tuple[np.ndarray, np.ndarray]
```

**Returns**: `(times, values)` - Time and state values as NumPy arrays

**Example**:

```python
times, values = result.to_numpy()
print(f"Shape: times={times.shape}, values={values.shape}")
```

---

##### `to_dict()`

Export as Python dictionary.

```python
def to_dict(self, include_probes: bool = True) -> Dict[str, Any]
```

**Parameters**:
- `include_probes`: Whether to include probe data

**Returns**: Dictionary containing time, states, metadata, and probe data

**Example**:

```python
data = result.to_dict(include_probes=True)
print(data.keys())  # ['time', 'metadata', 'state1', 'state2', ..., 'probes']

# JSON serialization
import json
with open("result.json", "w") as f:
    json.dump(data, f, indent=2)
```

---

##### `to_dataframe()`

Export as pandas DataFrame.

```python
def to_dataframe(self, include_probes: bool = False) -> pd.DataFrame
```

**Parameters**:
- `include_probes`: Whether to include probe columns

**Returns**: pandas DataFrame with time as a column

**Example**:

```python
# States only
df = result.to_dataframe()
print(df.head())

# Include probes
df_full = result.to_dataframe(include_probes=True)
df_full.plot(x='time', y=['Temperature', 'Control'])
```

---

##### `to_csv()`

Export to CSV file.

```python
def to_csv(
    self,
    filename: Union[str, Path],
    include_probes: bool = False,
    **kwargs
) -> None
```

**Parameters**:
- `filename`: Output file path
- `include_probes`: Whether to include probe data
- `**kwargs`: Additional arguments passed to `pandas.to_csv()`

**Example**:

```python
result.to_csv("output.csv")
result.to_csv("output_with_probes.csv", include_probes=True, index=False)
```

---

##### `get_probe_dataframe()`

Get DataFrame for probe data.

```python
def get_probe_dataframe(self, probe_name: Optional[str] = None) -> pd.DataFrame
```

**Parameters**:
- `probe_name`: Probe name (None for all probes)

**Returns**: DataFrame containing probe data

**Example**:

```python
# Get specific probe
df_control = result.get_probe_dataframe("controller")
print(df_control.columns)  # ['time', 'PID_Output', 'Integral', ...]

# Get all probes
df_all = result.get_probe_dataframe()
```

---

##### `save_probe_csv()`

Save individual probe data to CSV.

```python
def save_probe_csv(
    self,
    probe_name: str,
    filename: Union[str, Path],
    **kwargs
) -> None
```

**Example**:

```python
result.save_probe_csv("controller", "controller_data.csv")
```

---

##### `get_state()`

Get time series for a single state.

```python
def get_state(self, state_name: str) -> np.ndarray
```

**Example**:

```python
temp = result.get_state("plant.y1")
print(f"Temperature range: [{temp.min()}, {temp.max()}]")
```

---

##### `get_states()`

Get time series for multiple states.

```python
def get_states(self, state_names: List[str]) -> np.ndarray
```

**Returns**: 2D array with shape `[n_times, n_states]`

**Example**:

```python
outputs = result.get_states(["plant.y1", "plant.y2"])
print(outputs.shape)  # (n_times, 2)
```

---

##### `slice_time()`

Create new result object with time slice.

```python
def slice_time(
    self,
    t_start: Optional[float] = None,
    t_end: Optional[float] = None
) -> SimulationResult
```

**Example**:

```python
# Get data from t=5 to t=15
sliced = result.slice_time(t_start=5.0, t_end=15.0)
print(f"Original: {len(result.times)} points")
print(f"Sliced: {len(sliced.times)} points")
```

---

##### `summary()`

Compute statistical summary.

```python
def summary(self) -> Dict[str, Dict[str, float]]
```

**Returns**: Dictionary of statistics for each state

```python
{
    'state_name': {
        'mean': ...,
        'std': ...,
        'min': ...,
        'max': ...,
        'final': ...
    },
    ...
}
```

**Example**:

```python
stats = result.summary()
print(stats['plant.y1'])
# {'mean': 75.2, 'std': 5.3, 'min': 25.0, 'max': 80.0, 'final': 79.8}
```

---

##### `print_summary()`

Print formatted summary information.

```python
def print_summary(self) -> None
```

**Example**:

```python
result.print_summary()
```

**Output**:

```
Simulation Results: my_system
  Solver: Rodas5
  Time span: [0.00, 10.00]
  Time points: 101
  States: 8
  Probes: 2

State Statistics (first 10):
  plant.y1                       mean=  75.234 std=   5.321 range=[  25.000,   80.000]
  pid.output                     mean=  45.123 std=  12.456 range=[ -10.000,   98.000]
  ...

Probe Data:
  controller: 3 variables
    - PID_Output
    - Integral
    - Error
```

---

## 🔧 Advanced Usage

### Custom Nonlinear Systems

```python
from pycontroldae.core import Module

# Create Van der Pol oscillator
vdp = Module("vanderpol")
vdp.add_state("x", 0.0)
vdp.add_state("y", 1.0)
vdp.add_param("mu", 1.0)
vdp.add_equation("D(x) ~ y")
vdp.add_equation("D(y) ~ mu*(1 - x^2)*y - x")
vdp.build()

# Simulate
system = System("vdp_system")
system.add_module(vdp)
system.compile()

simulator = Simulator(system)
result = simulator.run(t_span=(0.0, 20.0), dt=0.1)
```

### Three-Level Nested CompositeModule

```python
# Level 1: PID controller
def create_pid_block(name, Kp, Ki, Kd):
    pid = CompositeModule(name)
    pid_core = PID(name="core", Kp=Kp, Ki=Ki, Kd=Kd)
    pid.add_module(pid_core)
    pid.expose_input("error", "core.error")
    pid.expose_output("output", "core.output")
    return pid

# Level 2: Temperature controller (contains PID + Limiter)
def create_temp_controller(name, Kp, Ki, Kd):
    ctrl = CompositeModule(name)
    pid = create_pid_block("pid", Kp, Ki, Kd)
    limiter = Limiter(name="lim", min_value=0, max_value=100)

    ctrl.add_module(pid)
    ctrl.add_module(limiter)
    ctrl.add_connection("pid.output ~ lim.input")
    ctrl.expose_input("error", "pid.error")
    ctrl.expose_output("control", "lim.output")
    return ctrl

# Level 3: Control station (contains temperature and flow controllers)
def create_control_station(name):
    station = CompositeModule(name)
    temp_ctrl = create_temp_controller("temp", Kp=3, Ki=0.8, Kd=0.3)
    flow_ctrl = create_temp_controller("flow", Kp=2, Ki=0.5, Kd=0.0)

    station.add_module(temp_ctrl)
    station.add_module(flow_ctrl)
    station.expose_input("temp_error", "temp.error")
    station.expose_input("flow_error", "flow.error")
    station.expose_output("heating", "temp.control")
    station.expose_output("valve", "flow.control")
    return station

# Use
station = create_control_station("my_station")
station.build()
```

### Multi-Probe Coordinated Analysis

```python
# Define multiple named probes
probes = {
    "controller": DataProbe(
        variables=["pid.output", "pid.integral", "pid.filtered_error"],
        names=["Control", "Integral", "Derivative"],
        description="PID internal signals"
    ),
    "plant": DataProbe(
        variables=["plant.x1", "plant.y1"],
        names=["State", "Output"],
        description="Plant variables"
    ),
    "setpoints": DataProbe(
        variables=["sp.signal", "error.output"],
        names=["Setpoint", "Error"],
        description="Reference tracking"
    )
}

# Simulate
result = simulator.run(t_span=(0, 30), dt=0.1, probes=probes)

# Export each probe separately
result.save_probe_csv("controller", "controller.csv")
result.save_probe_csv("plant", "plant.csv")
result.save_probe_csv("setpoints", "setpoints.csv")

# Or merge into one DataFrame
df = result.to_dataframe(include_probes=True)
print(df.columns)  # time, state1, state2, ..., controller.Control, plant.State, ...
```

---

## 🎓 Tutorials and Examples

The project includes complete test and example files:

- `test_data_probes.py` - Full data probe feature demonstration
- `test_complex_with_probes.py` - Multi-layer CompositeModule complex system
- `test_simplified_reactor.py` - Chemical reactor multi-loop control
- `test_all_features.py` - Comprehensive core feature test
- `test_nested_operators.py` - Nested module and operator test

Run examples:

```bash
python test_data_probes.py
python test_complex_with_probes.py
```

---

## 📊 Performance Notes

### Solver Selection Guidelines

| System Type | Recommended Solver | Notes |
|-------------|-------------------|-------|
| Stiff ODEs | `Rodas5` | Default, suitable for most control systems |
| Non-stiff ODEs | `Tsit5` | Faster for non-stiff systems |
| DAE Systems | `Rodas5` | Automatically handles algebraic constraints |
| High Precision | `QNDF` | Higher-order method |

### Importance of structural_simplify

`structural_simplify` is a core feature of ModelingToolkit.jl that automatically performs:

1. **DAE Index Reduction**: Converts high-index DAEs to low-index or ODEs
2. **Algebraic Elimination**: Removes purely algebraic equations
3. **Structural Analysis**: Detects and resolves structural singularities
4. **Equation Optimization**: Simplifies equation structure for faster solving

**Example**:

```python
# Before compilation: May have 100 equations (including algebraic constraints)
system.compile()
# After compilation: structural_simplify reduces to 20 differential equations

# This makes solver run 10-100x faster!
```

---

## 🐛 Troubleshooting

### Common Error 1: `ExtraEquationsSystemException`

**Cause**: System is over-constrained (more equations than variables)

**Solution**:
- Ensure you use `system.compile()` (includes structural_simplify)
- Check for duplicate connections
- Verify signal sources called `set_output()`

### Common Error 2: `MethodError: no method matching haskey`

**Cause**: Outdated parameter access method in event system

**Solution**: Already fixed in `simulator.py` using try-catch for direct parameter setting

### Common Error 3: Probe variable not found

**Cause**: Variable name mismatch or variable eliminated after simplify

**Solution**:
- Check variable name spelling (case-sensitive)
- Use `result.state_names` to view available states
- Probe failures warn but don't crash (fills with NaN)

### Common Error 4: Invalid initial conditions/parameters

**Cause**: Incorrect name format

**Solution**:

```python
# Correct format
u0 = {"module_name.state_name": value}
params = {"module_name.param_name": value}

# Incorrect format
u0 = {"state_name": value}  # Missing module name
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- All new control blocks should inherit from `Module` class
- Use fast differential tracking for outputs (see `basic.py`)
- Input variables should not have differential equations
- Add complete docstrings and type annotations
- Write tests to verify functionality

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

Thanks to the following projects for their support:

- **Julia** - High-performance scientific computing language
- **ModelingToolkit.jl** - Symbolic modeling and automatic differentiation
- **DifferentialEquations.jl** - World-class ODE/DAE solver suite
- **PythonCall.jl** - Seamless Python-Julia interoperability

---

## 📧 Contact

- Project Homepage: https://github.com/pronoobe/pycontroldae
- Issues: https://github.com/pronoobe/pycontroldae/issues

---

**pycontroldae** - Making control system modeling simple and powerful! 🚀
