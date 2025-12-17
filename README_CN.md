# pycontroldae - Python控制系统建模与仿真库

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Julia](https://img.shields.io/badge/Julia-1.9+-purple.svg)](https://julialang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**pycontroldae** 是一个强大的Python库，用于构建、仿真和分析控制系统。它结合了Python的易用性和Julia的高性能计算能力，通过ModelingToolkit.jl实现自动微分代数方程（DAE）索引降低和符号化简。

## ✨ 核心特性

### 🎯 模块化设计
- **层次化模块系统**：使用`Module`类定义可复用的控制组件
- **CompositeModule封装**：将多个模块封装为复合模块，支持任意层级嵌套
- **灵活的Port连接方式**：Pythonic风格的`>>` / `<<`操作符，支持IDE自动补全
  - Port级别: `pid.output >> plant.input` (显式端口连接)
  - Module级别: `source >> pid >> plant` (使用默认端口)
  - 字符串: `"pid.output ~ plant.input"` (向后兼容)
- **自动DAE简化**：内置`structural_simplify`自动处理代数约束

### 📦 丰富的控制块库
- **控制器**：PID、PI、PD、Gain、Limiter
- **信号源**：Step、Ramp、Sin、Pulse、Constant
- **线性系统**：StateSpace（支持SISO和MIMO）
- **基础模块**：Sum、Integrator、Derivative
- **自定义模块**：轻松定义任意非线性动态系统

### 🔬 高级仿真功能
- **事件系统**：
  - `TimeEvent`：时间触发事件（增益调度、参数切换）
  - `ContinuousEvent`：连续条件触发事件（安全限制、状态监控）
- **数据探测器**：
  - 观测任意变量（包括嵌套模块内部变量）
  - 支持单个、列表、字典三种配置方式
  - 自定义变量名称
- **强大的求解器**：
  - Rodas5（推荐，适用于刚性/DAE系统）
  - Tsit5、TRBDF2、QNDF等多种求解器

### 📊 灵活的数据导出
- **NumPy数组**：`result.to_numpy()` - 原始数值数据
- **pandas DataFrame**：`result.to_dataframe()` - 数据科学工作流
- **CSV文件**：`result.to_csv()` - 外部工具集成
- **Python字典**：`result.to_dict()` - JSON序列化
- **探测器专用导出**：`result.get_probe_dataframe()`, `result.save_probe_csv()`

### 📈 数据分析工具
- **时间切片**：`result.slice_time(t_start, t_end)`
- **统计摘要**：`result.summary()` - 均值、标准差、最小值、最大值
- **状态提取**：`result.get_state(name)`, `result.get_states(names)`
- **格式化输出**：`result.print_summary()`

---

## 📥 安装

### 前置要求

- Python 3.8+
- Julia 1.9+（会自动安装）

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/pronoobe/pycontroldae.git
cd pycontroldae

# 安装依赖
pip install numpy pandas matplotlib

# 首次运行会自动安装Julia包（可能需要几分钟）
python -c "from pycontroldae.core import get_jl; get_jl()"
```

### 依赖的Julia包（自动安装）
- ModelingToolkit.jl - 符号建模和自动微分
- DifferentialEquations.jl - 高性能ODE/DAE求解器
- PythonCall.jl - Python-Julia无缝交互

---

## 🚀 快速开始

### 示例1：RC电路仿真

```python
from pycontroldae.blocks import StateSpace, Step
from pycontroldae.core import System, Simulator
import numpy as np

# 定义RC电路（一阶系统）
# dV/dt = (I - V/R)/C
R = 1000.0  # 欧姆
C = 1e-6    # 法拉
A = np.array([[-1/(R*C)]])
B = np.array([[1/C]])
C_mat = np.array([[1.0]])
D_mat = np.array([[0.0]])

rc_circuit = StateSpace(
    name="rc",
    A=A, B=B, C=C_mat, D=D_mat,
    initial_state=np.array([0.0])
)

# 输入信号：5V阶跃
input_signal = Step(name="input", amplitude=5.0, step_time=0.0)
input_signal.set_output("signal")

# 构建系统
system = System("rc_system")
system.add_module(rc_circuit)
system.add_module(input_signal)
system.connect("input.signal ~ rc.u1")

# 编译和仿真
system.compile()
simulator = Simulator(system)
result = simulator.run(t_span=(0.0, 0.01), dt=0.0001)

# 导出数据
df = result.to_dataframe()
result.to_csv("rc_circuit.csv")
result.print_summary()
```

### 示例2：PID温度控制

```python
from pycontroldae.blocks import PID, Gain, Sum, Step, StateSpace
from pycontroldae.core import System, Simulator, DataProbe
import numpy as np

# 创建模块
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

# 构建系统
system = System("temp_control")
for mod in [setpoint, error_calc, pid, plant]:
    system.add_module(mod)

# 定义连接
system.connect("sp.signal ~ error.input1")
system.connect("plant.y1 ~ error.input2")
system.connect("error.output ~ pid.error")
system.connect("pid.output ~ plant.u1")

# 配置数据探测器
probe = DataProbe(
    variables=["plant.y1", "pid.output", "error.output"],
    names=["Temperature", "Control_Signal", "Error"],
    description="Main control variables"
)

# 编译和仿真
system.compile()
simulator = Simulator(system)
result = simulator.run(
    t_span=(0.0, 20.0),
    dt=0.1,
    probes=probe
)

# 获取探测器数据
probe_df = result.get_probe_dataframe()
print(probe_df.head())

# 保存结果
result.to_csv("temp_control.csv", include_probes=True)
```

### 示例3：Port连接方式（推荐）

```python
from pycontroldae.blocks import PID, Limiter, StateSpace, Step, Sum
from pycontroldae.core import CompositeModule, System, Simulator, DataProbe
import numpy as np

# 使用Port API创建可复用的PID控制器CompositeModule
def create_pid_controller(name, Kp=2.0, Ki=0.5, Kd=0.1):
    controller = CompositeModule(name)

    # 创建子模块
    pid = PID(name=f"{name}_core", Kp=Kp, Ki=Ki, Kd=Kd)
    limiter = Limiter(name=f"{name}_lim", min_value=0.0, max_value=100.0)

    controller.add_module(pid)
    controller.add_module(limiter)

    # 使用Port对象连接（新特性！）
    controller.add_connection(pid.output >> limiter.input)

    # 使用Port对象暴露接口（新特性！）
    controller.expose_input("error", pid.error)
    controller.expose_output("control", limiter.output)

    return controller

# 创建系统组件
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

# 使用灵活的Port连接方式构建系统
system = System("temp_control")
for mod in [setpoint, error_calc, pid_ctrl, plant]:
    system.add_module(mod)

# 方式1：Port对Port连接（显式，支持IDE自动补全）
system.connect(setpoint.signal >> error_calc.input1)
system.connect(pid_ctrl.control >> plant.u1)

# 方式2：字符串连接（向后兼容）
system.connect("plant.y1 ~ error.input2")

# 方式3：Module级别连接（使用默认端口）
system.connect(error_calc >> pid_ctrl)

# 使用Port对象配置DataProbe
probe = DataProbe(
    variables=[str(plant.y1), str(pid_ctrl.control)],
    names=["Temperature", "Control"],
    description="Main signals"
)

# 仿真
system.compile()
simulator = Simulator(system)
result = simulator.run(t_span=(0.0, 20.0), dt=0.1, probes=probe)

# 分析
result.print_summary()
result.to_csv("temp_control_port_api.csv", include_probes=True)
```

**Port API的优势：**
- **IDE自动补全**：输入`pid.`即可看到所有可用端口
- **类型安全**：在Python层面捕获错误，而非Julia层面
- **重构友好**：重命名变量更有信心
- **更符合Python习惯**：对Python开发者更自然

### 示例4：CompositeModule封装（经典API）

```python
from pycontroldae.blocks import PID, Limiter
from pycontroldae.core import CompositeModule, System, Simulator

# 创建可复用的温度控制器
def create_temp_controller(name, Kp=3.0, Ki=0.8, Kd=0.3):
    controller = CompositeModule(name=name)

    pid = PID(name="pid", Kp=Kp, Ki=Ki, Kd=Kd, integral_limit=100.0)
    limiter = Limiter(name="lim", min_value=0.0, max_value=100.0)

    controller.add_module(pid)
    controller.add_module(limiter)
    controller.add_connection("pid.output ~ lim.input")

    # 暴露接口
    controller.expose_input("error", "pid.error")
    controller.expose_output("control", "lim.output")

    return controller

# 创建多个实例
ctrl_A = create_temp_controller("ctrl_A", Kp=3.0)
ctrl_B = create_temp_controller("ctrl_B", Kp=4.0)

# 构建并仿真...
ctrl_A.build()
ctrl_B.build()
```

### 示例5：事件系统

```python
from pycontroldae.core import at_time, when_condition

# 时间事件：t=10s时增加增益
def increase_gain(integrator):
    print("Increasing PID gain at t=10s")
    return {"pid.Kp": 5.0, "pid.Ki": 1.5}

system.add_event(at_time(10.0, increase_gain))

# 连续事件：温度超过80°C时限制输出
def check_high_temp(u, t, integrator):
    return u[0] - 80.0  # 零点检测

def limit_output(integrator):
    print("Temperature too high! Limiting output")
    return {"limiter.max_val": 50.0}

system.add_event(when_condition(check_high_temp, limit_output, direction=1))
```

---

## 📖 API详细文档

### 核心类

#### `Module`

定义基本控制模块的基类。

```python
class Module:
    def __init__(self, name: str)
    def add_state(self, name: str, default: float = 0.0) -> Module
    def add_param(self, name: str, default: float) -> Module
    def add_equation(self, eq_str: str) -> Module
    def build() -> Any  # 返回Julia ODESystem
```

**方法说明**：

- `add_state(name, default)`: 添加状态变量
  - `name`: 变量名（字符串）
  - `default`: 默认初始值
  - 返回`self`以支持链式调用

- `add_param(name, default)`: 添加参数
  - `name`: 参数名
  - `default`: 默认值

- `add_equation(eq_str)`: 添加微分方程
  - `eq_str`: Julia语法的方程字符串，例如`"D(x) ~ -k*x"`

- `build()`: 构建Julia ODESystem对象

**示例**：

```python
# 创建一阶系统
module = Module("first_order")
module.add_state("x", 0.0)
module.add_param("k", 1.0)
module.add_state("u", 0.0)  # 输入
module.add_equation("D(x) ~ -k*x + u")
module.build()
```

---

#### `CompositeModule`

封装多个模块为复合模块，支持嵌套。

```python
class CompositeModule(Module):
    def __init__(self, name: str)
    def add_module(self, module: Module) -> None
    def add_connection(self, connection: str) -> None
    def expose_input(self, external_name: str, internal_path: str) -> None
    def expose_output(self, external_name: str, internal_path: str) -> None
    def build() -> Any
```

**方法说明**：

- `add_module(module)`: 添加子模块（可以是Module或CompositeModule）

- `add_connection(connection)`: 定义内部连接
  - 格式：`"module1.output ~ module2.input"`

- `expose_input(external_name, internal_path)`: 暴露输入接口
  - `external_name`: 外部访问名称
  - `internal_path`: 内部模块路径，如`"pid.error"`

- `expose_output(external_name, internal_path)`: 暴露输出接口

**示例**：

```python
# 创建嵌套CompositeModule
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

**连接方法**：

```python
# 方式1：Port对Port连接（推荐 - IDE自动补全！）
system.connect(pid.output >> plant.input)

# 方式2：Module级别连接（使用默认端口）
source >> module1 >> module2 >> sink
# 等价于:
# system.connect(source.output >> module1.input)
# system.connect(module1.output >> module2.input)
# system.connect(module2.output >> sink.input)

# 方式3：字符串连接（向后兼容）
system.connect("source.output ~ module1.input")
```

**CompositeModule使用：**

```python
# Port连接内部模块（新特性！）
composite.add_connection(pid.output >> limiter.input)

# Port暴露接口（新特性！）
composite.expose_input("error", pid.error)
composite.expose_output("control", limiter.output)

# 字符串方式（仍然支持）
composite.add_connection("pid.output ~ limiter.input")
composite.expose_input("error", "pid.error")
composite.expose_output("control", "limiter.output")
```

---

#### `System`

组合多个模块并管理连接。

```python
class System:
    def __init__(self, name: str = "system")
    def add_module(self, module: Module) -> System
    def connect(self, connection_expr: str) -> System
    def add_event(self, event: Union[TimeEvent, ContinuousEvent]) -> None
    def compile() -> Any  # 返回简化的Julia ODESystem

    @property
    def modules(self) -> List[Module]

    @property
    def connections(self) -> List[str]

    @property
    def events(self) -> List[Union[TimeEvent, ContinuousEvent]]
```

**方法说明**：

- `add_module(module)`: 添加模块到系统

- `connect(connection_expr)`: 定义模块间连接
  - 接受多种格式:
    - **Port对象** (推荐): `system.connect(mod1.output >> mod2.input)`
    - **Module操作符**: `system.connect(mod1 >> mod2)` (使用默认端口)
    - **字符串**: `system.connect("module1.output ~ module2.input")` (向后兼容)

- `add_event(event)`: 添加事件（时间事件或连续事件）

- `compile()`: 编译系统
  - 自动调用所有模块的`build()`
  - 创建组合ODESystem
  - **关键**：应用`structural_simplify`进行DAE索引降低

**示例**：

```python
system = System("my_system")
system.add_module(module1)
system.add_module(module2)
system.connect("module1.output ~ module2.input")
compiled = system.compile()
```

---

#### `Simulator`

执行系统仿真并返回结果。

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

**参数说明**：

- `t_span`: 时间范围元组`(t_start, t_end)`

- `u0`: 初始条件字典，例如`{"module.state": value}`
  - 可选，默认使用模块定义的默认值

- `params`: 参数值字典，例如`{"module.param": value}`
  - 可选，默认使用模块定义的默认值

- `dt`: 保存解的时间步长
  - `None`：自适应时间步长
  - `float`：固定时间步长

- `solver`: 求解器名称
  - `"Rodas5"`：推荐，适用于刚性DAE系统
  - `"Tsit5"`：非刚性ODE
  - `"TRBDF2"`, `"QNDF"`：其他刚性求解器

- `probes`: 数据探测器
  - 单个`DataProbe`对象
  - `DataProbe`列表
  - `Dict[str, DataProbe]`（命名探测器）

- `return_result`: 是否返回`SimulationResult`对象
  - `True`（默认）：返回`SimulationResult`
  - `False`：返回`(times, values)`元组（向后兼容）

**返回值**：

- `SimulationResult`对象（当`return_result=True`）
- `(times, values)`元组（当`return_result=False`）

**示例**：

```python
simulator = Simulator(system)

# 基本用法
result = simulator.run(t_span=(0.0, 10.0), dt=0.1)

# 指定初始条件和参数
result = simulator.run(
    t_span=(0.0, 10.0),
    u0={"plant.x1": 25.0},
    params={"pid.Kp": 3.0},
    dt=0.1
)

# 使用探测器
probe = DataProbe(variables=["plant.y1", "pid.output"])
result = simulator.run(t_span=(0.0, 10.0), probes=probe)

# 向后兼容模式
times, values = simulator.run(t_span=(0.0, 10.0), return_result=False)
```

---

### 控制块

#### `PID`

PID控制器。

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

**参数**：
- `Kp`: 比例增益
- `Ki`: 积分增益
- `Kd`: 微分增益
- `integral_limit`: 积分饱和限制
- `derivative_filter`: 微分滤波时间常数

**接口**：
- 输入：`error`
- 输出：`output`

**示例**：

```python
pid = PID(name="controller", Kp=2.0, Ki=0.5, Kd=0.1)
pid.build()
```

---

#### `StateSpace`

线性状态空间模型。

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

**参数**：
- `A`: 状态矩阵（n×n）
- `B`: 输入矩阵（n×m）
- `C`: 输出矩阵（p×n）
- `D`: 直接传递矩阵（p×m）
- `initial_state`: 初始状态向量（长度n）

**接口**：
- 输入：`u1`, `u2`, ..., `um`（m个输入）
- 输出：`y1`, `y2`, ..., `yp`（p个输出）

**示例**：

```python
# SISO系统
A = np.array([[-1.0]])
B = np.array([[1.0]])
C = np.array([[1.0]])
D = np.array([[0.0]])
plant = StateSpace(name="plant", A=A, B=B, C=C, D=D)

# MIMO系统（2输入，2输出）
A = np.array([[-0.5, 0.1], [0.2, -0.8]])
B = np.array([[1.0, 0.1], [0.2, 1.0]])
C = np.array([[1.0, 0.0], [0.0, 1.0]])
D = np.zeros((2, 2))
plant = StateSpace(name="mimo_plant", A=A, B=B, C=C, D=D)
```

---

#### `Gain`

增益块。

```python
Gain(name: str, K: float = 1.0)
```

**接口**：
- 输入：`input`
- 输出：`output`（= K × input）

---

#### `Sum`

求和块。

```python
Sum(name: str, num_inputs: int = 2, signs: List[int] = None)
```

**参数**：
- `num_inputs`: 输入数量
- `signs`: 符号列表，例如`[+1, -1]`表示input1 - input2

**接口**：
- 输入：`input1`, `input2`, ..., `inputN`
- 输出：`output`（= sum(signs[i] × input[i])）

**示例**：

```python
# 误差计算：setpoint - measurement
error = Sum(name="error", num_inputs=2, signs=[+1, -1])
system.connect("setpoint.signal ~ error.input1")
system.connect("plant.y1 ~ error.input2")
```

---

#### `Limiter`

限幅器（饱和）。

```python
Limiter(name: str, min_value: float = -100.0, max_value: float = 100.0)
```

**接口**：
- 输入：`input`
- 输出：`output`（限制在[min_value, max_value]）

---

#### `Step`

阶跃信号。

```python
Step(name: str, amplitude: float = 1.0, step_time: float = 0.0)
```

**使用前需要调用**：

```python
step = Step(name="sp", amplitude=10.0, step_time=2.0)
step.set_output("signal")  # 必须！
step.build()
```

**接口**：
- 输出：`signal`

---

#### `Ramp`

斜坡信号。

```python
Ramp(name: str, slope: float = 1.0, start_time: float = 0.0)
```

**使用前需要调用**：

```python
ramp = Ramp(name="ref", slope=0.5, start_time=1.0)
ramp.set_output("signal")
ramp.build()
```

---

#### `Sin`

正弦波信号。

```python
Sin(name: str, amplitude: float = 1.0, frequency: float = 1.0, phase: float = 0.0)
```

**使用前需要调用**：

```python
sin_wave = Sin(name="disturbance", amplitude=5.0, frequency=0.3)
sin_wave.set_output("signal")
sin_wave.build()
```

---

#### `Integrator`

积分器。

```python
Integrator(name: str, initial_value: float = 0.0)
```

**接口**：
- 输入：`input`
- 输出：`output`（= ∫input dt）

---

### 事件系统

#### `TimeEvent` / `at_time`

时间触发事件。

```python
def at_time(time: float, callback: Callable) -> TimeEvent
```

**参数**：
- `time`: 触发时间
- `callback`: 回调函数，签名为`callback(integrator) -> Dict[str, float]`
  - 返回字典：`{"module.param": new_value}`

**示例**：

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

连续条件触发事件。

```python
def when_condition(
    condition: Callable,
    affect: Callable,
    direction: int = 0
) -> ContinuousEvent
```

**参数**：
- `condition`: 条件函数，签名为`condition(u, t, integrator) -> float`
  - 返回值过零时触发
- `affect`: 影响函数，签名为`affect(integrator) -> Dict[str, float]`
  - 返回参数更新字典
- `direction`: 零点检测方向
  - `0`: 双向（上穿和下穿都触发）
  - `1`: 上穿（condition从负到正）
  - `-1`: 下穿（condition从正到负）

**示例**：

```python
# 温度超过80°C时限制输出
def check_high_temp(u, t, integrator):
    return u[0] - 80.0  # u[0]是第一个状态变量

def limit_heating(integrator):
    print("Temperature limit exceeded!")
    return {"limiter.max_val": 50.0}

system.add_event(when_condition(
    check_high_temp,
    limit_heating,
    direction=1  # 仅上穿触发
))
```

---

### 数据探测器和结果

#### `DataProbe`

配置变量观测。

```python
class DataProbe:
    def __init__(
        self,
        variables: List[str],
        names: Optional[List[str]] = None,
        description: str = ""
    )
```

**参数**：
- `variables`: 要观测的变量列表，例如`["plant.y1", "pid.output"]`
- `names`: 自定义变量名称（可选）
- `description`: 探测器描述（可选）

**示例**：

```python
# 基本用法
probe = DataProbe(variables=["plant.y1", "pid.output"])

# 自定义名称
probe = DataProbe(
    variables=["plant.y1", "pid.output", "error.output"],
    names=["Temperature", "Control", "Error"],
    description="Main control loop"
)

# 多个探测器（列表）
probes = [
    DataProbe(variables=["pid.output"], names=["PID"]),
    DataProbe(variables=["plant.y1"], names=["Plant"])
]

# 命名探测器（字典）
probes = {
    "controller": DataProbe(variables=["pid.output", "pid.integral"]),
    "plant": DataProbe(variables=["plant.y1", "plant.x1"])
}

result = simulator.run(t_span=(0, 10), probes=probes)
```

---

#### `SimulationResult`

仿真结果容器。

```python
class SimulationResult:
    # 属性
    times: np.ndarray           # 时间向量
    values: np.ndarray          # 状态值矩阵 [n_times, n_states]
    state_names: List[str]      # 状态名称列表
    probe_data: Dict[str, Dict[str, np.ndarray]]  # 探测器数据
    system_name: str            # 系统名称
    solver: str                 # 求解器名称
    metadata: Dict[str, Any]    # 元数据
```

**主要方法**：

##### `to_numpy()`

导出为NumPy数组。

```python
def to_numpy(self) -> Tuple[np.ndarray, np.ndarray]
```

**返回**：`(times, values)` - 时间和状态值的NumPy数组

**示例**：

```python
times, values = result.to_numpy()
print(f"Shape: times={times.shape}, values={values.shape}")
```

---

##### `to_dict()`

导出为Python字典。

```python
def to_dict(self, include_probes: bool = True) -> Dict[str, Any]
```

**参数**：
- `include_probes`: 是否包含探测器数据

**返回**：包含时间、状态、元数据和探测器数据的字典

**示例**：

```python
data = result.to_dict(include_probes=True)
print(data.keys())  # ['time', 'metadata', 'state1', 'state2', ..., 'probes']

# JSON序列化
import json
with open("result.json", "w") as f:
    json.dump(data, f, indent=2)
```

---

##### `to_dataframe()`

导出为pandas DataFrame。

```python
def to_dataframe(self, include_probes: bool = False) -> pd.DataFrame
```

**参数**：
- `include_probes`: 是否包含探测器列

**返回**：pandas DataFrame，time作为一列

**示例**：

```python
# 仅状态
df = result.to_dataframe()
print(df.head())

# 包含探测器
df_full = result.to_dataframe(include_probes=True)
df_full.plot(x='time', y=['Temperature', 'Control'])
```

---

##### `to_csv()`

导出为CSV文件。

```python
def to_csv(
    self,
    filename: Union[str, Path],
    include_probes: bool = False,
    **kwargs
) -> None
```

**参数**：
- `filename`: 输出文件路径
- `include_probes`: 是否包含探测器数据
- `**kwargs`: 传递给`pandas.to_csv()`的额外参数

**示例**：

```python
result.to_csv("output.csv")
result.to_csv("output_with_probes.csv", include_probes=True, index=False)
```

---

##### `get_probe_dataframe()`

获取探测器数据的DataFrame。

```python
def get_probe_dataframe(self, probe_name: Optional[str] = None) -> pd.DataFrame
```

**参数**：
- `probe_name`: 探测器名称（None表示所有探测器）

**返回**：包含探测器数据的DataFrame

**示例**：

```python
# 获取特定探测器
df_control = result.get_probe_dataframe("controller")
print(df_control.columns)  # ['time', 'PID_Output', 'Integral', ...]

# 获取所有探测器
df_all = result.get_probe_dataframe()
```

---

##### `save_probe_csv()`

保存单个探测器数据为CSV。

```python
def save_probe_csv(
    self,
    probe_name: str,
    filename: Union[str, Path],
    **kwargs
) -> None
```

**示例**：

```python
result.save_probe_csv("controller", "controller_data.csv")
```

---

##### `get_state()`

获取单个状态的时间序列。

```python
def get_state(self, state_name: str) -> np.ndarray
```

**示例**：

```python
temp = result.get_state("plant.y1")
print(f"Temperature range: [{temp.min()}, {temp.max()}]")
```

---

##### `get_states()`

获取多个状态的时间序列。

```python
def get_states(self, state_names: List[str]) -> np.ndarray
```

**返回**：2D数组，shape为`[n_times, n_states]`

**示例**：

```python
outputs = result.get_states(["plant.y1", "plant.y2"])
print(outputs.shape)  # (n_times, 2)
```

---

##### `slice_time()`

创建时间切片的新结果对象。

```python
def slice_time(
    self,
    t_start: Optional[float] = None,
    t_end: Optional[float] = None
) -> SimulationResult
```

**示例**：

```python
# 获取t=5到t=15的数据
sliced = result.slice_time(t_start=5.0, t_end=15.0)
print(f"Original: {len(result.times)} points")
print(f"Sliced: {len(sliced.times)} points")
```

---

##### `summary()`

计算统计摘要。

```python
def summary(self) -> Dict[str, Dict[str, float]]
```

**返回**：每个状态的统计信息字典

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

**示例**：

```python
stats = result.summary()
print(stats['plant.y1'])
# {'mean': 75.2, 'std': 5.3, 'min': 25.0, 'max': 80.0, 'final': 79.8}
```

---

##### `print_summary()`

打印格式化的摘要信息。

```python
def print_summary(self) -> None
```

**示例**：

```python
result.print_summary()
```

**输出**：

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

## 🔧 高级用法

### 自定义非线性系统

```python
from pycontroldae.core import Module

# 创建Van der Pol振荡器
vdp = Module("vanderpol")
vdp.add_state("x", 0.0)
vdp.add_state("y", 1.0)
vdp.add_param("mu", 1.0)
vdp.add_equation("D(x) ~ y")
vdp.add_equation("D(y) ~ mu*(1 - x^2)*y - x")
vdp.build()

# 仿真
system = System("vdp_system")
system.add_module(vdp)
system.compile()

simulator = Simulator(system)
result = simulator.run(t_span=(0.0, 20.0), dt=0.1)
```

### 三层嵌套CompositeModule

```python
# 第一层：PID控制器
def create_pid_block(name, Kp, Ki, Kd):
    pid = CompositeModule(name)
    pid_core = PID(name="core", Kp=Kp, Ki=Ki, Kd=Kd)
    pid.add_module(pid_core)
    pid.expose_input("error", "core.error")
    pid.expose_output("output", "core.output")
    return pid

# 第二层：温度控制器（包含PID + 限幅器）
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

# 第三层：控制站（包含温度和流量控制器）
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

# 使用
station = create_control_station("my_station")
station.build()
```

### 多探测器协同分析

```python
# 定义多个命名探测器
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

# 仿真
result = simulator.run(t_span=(0, 30), dt=0.1, probes=probes)

# 分别导出每个探测器
result.save_probe_csv("controller", "controller.csv")
result.save_probe_csv("plant", "plant.csv")
result.save_probe_csv("setpoints", "setpoints.csv")

# 或合并到一个DataFrame
df = result.to_dataframe(include_probes=True)
print(df.columns)  # time, state1, state2, ..., controller.Control, plant.State, ...
```

---

## 🎓 教程和示例

项目包含完整的测试和示例文件：

- `test_data_probes.py` - 数据探测器全功能演示
- `test_complex_with_probes.py` - 多层CompositeModule复杂系统
- `test_simplified_reactor.py` - 化学反应器多回路控制
- `test_all_features.py` - 所有核心功能综合测试
- `test_nested_operators.py` - 嵌套模块和操作符测试

运行示例：

```bash
python test_data_probes.py
python test_complex_with_probes.py
```

---

## 📊 性能说明

### 求解器选择建议

| 系统类型 | 推荐求解器 | 说明 |
|---------|-----------|------|
| 刚性ODE | `Rodas5` | 默认，适用于大多数控制系统 |
| 非刚性ODE | `Tsit5` | 更快，适用于非刚性系统 |
| DAE系统 | `Rodas5` | 自动处理代数约束 |
| 高精度需求 | `QNDF` | 更高阶方法 |

### structural_simplify的重要性

`structural_simplify`是ModelingToolkit.jl的核心功能，自动执行：

1. **DAE索引降低**：将高指标DAE转换为低指标或ODE
2. **代数消元**：移除纯代数方程
3. **结构分析**：检测并解决结构奇异性
4. **方程优化**：简化方程结构以提高求解速度

**示例**：

```python
# 编译前：可能有100个方程（包括代数约束）
system.compile()
# 编译后：structural_simplify简化为20个微分方程

# 这使得求解器运行速度快10-100倍！
```

---

## 🐛 故障排查

### 常见错误1：`ExtraEquationsSystemException`

**原因**：系统过度约束（方程数 > 变量数）

**解决**：
- 确保使用了`system.compile()`（包含structural_simplify）
- 检查是否有重复的连接
- 验证信号源是否调用了`set_output()`

### 常见错误2：`MethodError: no method matching haskey`

**原因**：事件系统中的参数访问方式过时

**解决**：已在`simulator.py`中修复，使用try-catch直接设置参数

### 常见错误3：探测器变量未找到

**原因**：变量名称不匹配或变量在simplify后被消除

**解决**：
- 检查变量名拼写（区分大小写）
- 使用`result.state_names`查看可用状态
- 探测器失败会警告但不会崩溃（填充NaN）

### 常见错误4：初始条件/参数设置无效

**原因**：名称格式错误

**解决**：

```python
# 正确格式
u0 = {"module_name.state_name": value}
params = {"module_name.param_name": value}

# 错误格式
u0 = {"state_name": value}  # 缺少模块名
```

---

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 开发指南

- 所有新控制块应继承`Module`类
- 使用快速微分跟踪实现输出（参见`basic.py`）
- 输入变量不应有微分方程
- 添加完整的文档字符串和类型注解
- 编写测试验证功能

---

## 📄 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件

---

## 🙏 致谢

感谢以下项目的支持：

- **Julia** - 高性能科学计算语言
- **ModelingToolkit.jl** - 符号建模和自动微分
- **DifferentialEquations.jl** - 世界级ODE/DAE求解器
- **PythonCall.jl** - Python-Julia无缝桥接

---

## 📧 联系方式

- 项目主页：https://github.com/pronoobe/pycontroldae
- Issues：https://github.com/pronoobe/pycontroldae/issues

---

**pycontroldae** - 让控制系统建模变得简单而强大！ 🚀
