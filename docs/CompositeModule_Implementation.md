# CompositeModule Implementation - Hierarchical System Composition

## Overview

成功实现了 **CompositeModule** 类，支持将多个模块封装成单个具有明确输入/输出接口的复合模块。这使得可以构建层次化的、可重用的控制系统组件。

## 核心概念

### 什么是 CompositeModule？

CompositeModule 是一个特殊的 Module，它：
- 包含多个子模块（可以是 Module 或 CompositeModule）
- 定义子模块之间的内部连接
- 暴露明确的输入/输出接口
- 可以像普通 Module 一样使用

### 为什么需要 CompositeModule？

**问题**：在复杂系统中，直接连接大量基础模块会导致：
- 连接关系复杂，难以维护
- 重复的子系统需要重复定义
- 缺乏抽象层次，系统结构不清晰

**解决方案**：CompositeModule 提供：
- **模块化**：将相关模块组合成逻辑单元
- **可重用性**：定义一次，到处使用
- **抽象**：隐藏内部复杂性，只暴露必要接口
- **层次化**：支持嵌套，构建可扩展的系统架构

## 实现详情

### 文件

**pycontroldae/core/composite.py** (350行)

### 类结构

```python
class CompositeModule(Module):
    """继承自 Module，添加层次化组合能力"""

    def __init__(self, name: str, input_var=None, output_var=None)
    def add_module(self, module: Module) -> 'CompositeModule'
    def add_connection(self, connection: Union[str, Tuple]) -> 'CompositeModule'
    def expose_input(self, interface_name: str, internal_path: str) -> 'CompositeModule'
    def expose_output(self, interface_name: str, internal_path: str) -> 'CompositeModule'
    def build(self) -> Any
```

### 关键方法

#### 1. `add_module(module)` - 添加子模块

```python
composite.add_module(pid)
composite.add_module(limiter)
```

#### 2. `add_connection(connection)` - 定义内部连接

```python
composite.add_connection("pid.output ~ limiter.input")
# 或使用连接操作符
composite.add_connection(pid >> limiter)
```

#### 3. `expose_input(interface_name, internal_path)` - 暴露输入接口

```python
# 将 pid.error 暴露为外部的 "error" 接口
composite.expose_input("error", "pid.error")
```

外部模块现在可以连接到 `composite.error`，实际连接到内部的 `pid.error`。

#### 4. `expose_output(interface_name, internal_path)` - 暴露输出接口

```python
# 将 limiter.output 暴露为外部的 "control" 接口
composite.expose_output("control", "limiter.output")
```

外部模块可以从 `composite.control` 获取信号，实际来自 `limiter.output`。

#### 5. `build()` - 构建 Julia ODESystem

构建过程：
1. 构建所有子模块
2. 在 Julia 中创建接口变量（使用 `@variables`）
3. 创建接口映射方程（代数方程）
4. 组合所有子系统和连接
5. 返回层次化的 ODESystem

### 便利函数

```python
def create_composite(
    name: str,
    modules: List[Module],
    connections: List[str],
    inputs: Optional[Dict[str, str]] = None,
    outputs: Optional[Dict[str, str]] = None
) -> CompositeModule
```

一次性创建 CompositeModule：

```python
controller = create_composite(
    name="controller",
    modules=[pid, limiter],
    connections=["pid.output ~ limiter.input"],
    inputs={"error": "pid.error"},
    outputs={"control": "limiter.output"}
)
```

## 使用示例

### 示例 1：带限幅的 PID 控制器

```python
from pycontroldae.blocks import PID, Limiter
from pycontroldae.core import CompositeModule

# 创建复合模块
pid_limited = CompositeModule(name="pid_limited")

# 添加子模块
pid = PID(name="pid", Kp=2.0, Ki=0.5, Kd=0.1)
limiter = Limiter(name="limiter", min_value=-10.0, max_value=10.0)

pid_limited.add_module(pid)
pid_limited.add_module(limiter)

# 内部连接
pid_limited.add_connection("pid.output ~ limiter.input")

# 暴露接口
pid_limited.expose_input("error", "pid.error")
pid_limited.expose_output("control", "limiter.output")

# 构建
pid_limited.build()

# 现在可以像普通模块一样使用
system.connect(sensor >> pid_limited >> actuator)
```

### 示例 2：级联放大器链

```python
from pycontroldae.blocks import Gain
from pycontroldae.core import create_composite

amp_chain = create_composite(
    name="amp_chain",
    modules=[
        Gain(name="stage1", K=2.0),
        Gain(name="stage2", K=1.5),
        Gain(name="stage3", K=3.0)
    ],
    connections=[
        "stage1.output ~ stage2.input",
        "stage2.output ~ stage3.input"
    ],
    inputs={"in": "stage1.input"},
    outputs={"out": "stage3.output"}
)

# 总增益: 2.0 * 1.5 * 3.0 = 9.0
```

### 示例 3：嵌套层次

```python
# 内层：双级放大器
inner = CompositeModule(name="dual_amp")
inner.add_module(Gain(name="amp1", K=2.0))
inner.add_module(Gain(name="amp2", K=2.0))
inner.add_connection("amp1.output ~ amp2.input")
inner.expose_input("in", "amp1.input")
inner.expose_output("out", "amp2.output")

# 外层：内层 + 限幅器
outer = CompositeModule(name="protected")
limiter = Limiter(name="lim", min_value=-5, max_value=5)

outer.add_module(inner)  # 嵌套复合模块
outer.add_module(limiter)
outer.add_connection("dual_amp.out ~ lim.input")
outer.expose_input("signal", "dual_amp.in")
outer.expose_output("limited", "lim.output")

# 层次结构：
# outer
#   ├─ dual_amp (CompositeModule)
#   │    ├─ amp1 (Module)
#   │    └─ amp2 (Module)
#   └─ lim (Module)
```

### 示例 4：完整反馈回路

```python
from pycontroldae.blocks import PID, Gain, Sum

control_loop = CompositeModule(name="feedback_loop")

# 组件
error_sum = Sum(name="error", num_inputs=2, signs=[+1, -1])
controller = PID(name="pid", Kp=2.0, Ki=0.5, Kd=0.1)
plant = Gain(name="plant", K=1.5)

control_loop.add_module(error_sum)
control_loop.add_module(controller)
control_loop.add_module(plant)

# 连接
control_loop.add_connection("error.output ~ pid.error")
control_loop.add_connection("pid.output ~ plant.input")
control_loop.add_connection("plant.output ~ error.input2")  # 反馈

# 只暴露外部接口
control_loop.expose_input("setpoint", "error.input1")
control_loop.expose_output("output", "plant.output")

# 外部看来，这只是一个单输入单输出模块
# 内部结构完全隐藏
```

### 示例 5：MIMO 系统

```python
mimo = CompositeModule(name="mimo_system")

# 多个输入/输出
mimo.expose_input("u1", "module1.input1")
mimo.expose_input("u2", "module1.input2")
mimo.expose_output("y1", "module2.output1")
mimo.expose_output("y2", "module2.output2")
```

## 技术实现

### 接口映射机制

当暴露接口时，创建代数方程连接外部接口和内部变量：

```python
# 输入接口：
expose_input("error", "pid.error")
# 生成方程: pid.error ~ error

# 输出接口：
expose_output("control", "limiter.output")
# 生成方程: control ~ limiter.output
```

### Julia 编译过程

```julia
# 1. 创建接口变量
@variables error(t) control(t)

# 2. 创建接口映射方程
equations = [
    pid.error ~ error,      # 输入接口
    control ~ limiter.output # 输出接口
]

# 3. 组合系统
@named composite = ODESystem(equations, t; systems=[pid, limiter])
```

### 层次化命名

Julia 使用 `₊` 字符进行层次化命名：

```
composite₊pid₊error       # 复合模块中的 PID 误差
composite₊limiter₊output  # 复合模块中的限幅器输出
```

Python 中使用 `.` 表示：`composite.pid.error`

## 测试

**test_composite.py** - 所有 7 个测试通过：

1. ✓ 基本 CompositeModule 创建
2. ✓ PID 与限幅器组合
3. ✓ 使用 create_composite() 便利函数
4. ✓ 嵌套 CompositeModule（层次化）
5. ✓ 多输入多输出复合模块
6. ✓ 在 System 中使用 CompositeModule
7. ✓ 连接操作符 (>> 和 <<)

## 应用场景

### 控制系统

1. **标准控制器配置**
   - PID + 抗饱和
   - 带前馈的 PID
   - 级联控制器

2. **信号处理链**
   - 滤波器级联
   - 放大器链
   - 信号调理

3. **完整控制回路**
   - 反馈控制
   - 前馈-反馈组合
   - 多回路控制

### 系统架构

1. **层次化设计**
   - 子系统封装
   - 功能模块化
   - 清晰的抽象层次

2. **可重用组件**
   - 标准控制器库
   - 通用信号处理模块
   - 行业标准配置

3. **MIMO 系统**
   - 耦合动力学
   - 多变量控制
   - 交叉通道补偿

## 优势

### 1. 模块化

- 将复杂系统分解为逻辑组件
- 每个组件职责清晰
- 易于理解和维护

### 2. 可重用性

- 定义一次，到处使用
- 构建标准组件库
- 加速系统开发

### 3. 抽象

- 隐藏内部实现细节
- 提供清晰的接口契约
- 降低系统复杂度

### 4. 层次化

- 支持任意深度嵌套
- 可扩展的架构
- 自然映射到物理系统结构

### 5. 兼容性

- 可以像普通 Module 使用
- 支持连接操作符
- 与现有 API 完全兼容

## 设计模式

### 标准流程

```python
# 1. 创建 CompositeModule
composite = CompositeModule(name="my_system")

# 2. 添加子模块
composite.add_module(module1)
composite.add_module(module2)

# 3. 定义内部连接
composite.add_connection("module1.output ~ module2.input")

# 4. 暴露接口
composite.expose_input("input", "module1.input")
composite.expose_output("output", "module2.output")

# 5. 构建并使用
composite.build()
system.connect(source >> composite >> sink)
```

### 最佳实践

1. **命名约定**
   - 使用描述性名称
   - 避免特殊字符和数字开头
   - 保持名称简洁

2. **接口设计**
   - 最小化暴露的接口数量
   - 使用清晰的接口名称
   - 文档化接口用途

3. **层次深度**
   - 合理控制嵌套深度（推荐 2-3 层）
   - 每层抽象应该有明确意义
   - 避免过度嵌套

4. **可测试性**
   - 每个复合模块独立可测试
   - 提供测试用例
   - 验证接口行为

## 局限性

1. **命名约束**
   - Julia 变量名不能以数字开头
   - 避免使用特殊字符

2. **循环依赖**
   - 需要小心处理反馈回路
   - 确保代数约束可解

3. **性能**
   - 深度嵌套可能影响编译时间
   - 对于非常大的系统，考虑扁平化

## 与其他功能的集成

### 与 System 集成

```python
# CompositeModule 可以添加到 System
system = System("main")
system.add_module(composite_controller)
system.add_module(plant)
system.connect(composite_controller >> plant)
```

### 与事件系统集成

```python
# 事件可以修改 CompositeModule 内部参数
def tune_pid(integrator):
    return {
        "controller.pid.Kp": 3.0,  # 访问嵌套参数
        "controller.limiter.max_val": 15.0
    }

system.add_event(at_time(5.0, tune_pid))
```

### 与 StateSpace 集成

```python
# CompositeModule 可以包含 StateSpace
composite = CompositeModule("system")
ss_plant = StateSpace(name="plant", A=A, B=B, C=C, D=D)
controller = PID(name="ctrl", Kp=1, Ki=0.1, Kd=0.05)

composite.add_module(controller)
composite.add_module(ss_plant)
composite.add_connection("ctrl.output ~ plant.u1")
```

## 未来增强

潜在改进：

1. **自动接口检测**
   - 自动识别未连接的端口
   - 建议接口暴露

2. **接口类型检查**
   - 验证连接兼容性
   - 类型安全

3. **可视化**
   - 生成系统结构图
   - 显示层次关系

4. **模板系统**
   - 参数化 CompositeModule
   - 标准模块库

5. **性能优化**
   - 缓存构建结果
   - 增量编译

## 文件清单

1. **pycontroldae/core/composite.py** (350行)
   - CompositeModule 类实现
   - create_composite() 便利函数

2. **pycontroldae/core/__init__.py** (已更新)
   - 导出 CompositeModule 和 create_composite

3. **test_composite.py** (395行)
   - 全面的测试套件
   - 7 个测试全部通过

4. **examples/example_composite.py** (315行)
   - 7 个实用示例
   - 涵盖各种使用场景

5. **docs/CompositeModule_Implementation.md** (本文档)
   - 完整的实现文档

## 总结

CompositeModule 为 pycontroldae 增加了强大的层次化组合能力，使得：

- ✓ 可以将多个模块封装为单一模块
- ✓ 支持明确的输入/输出接口定义
- ✓ 实现层次化的系统架构
- ✓ 提高代码可重用性和可维护性
- ✓ 与现有 API 完全兼容

这个功能完善了 pycontroldae 的模块化设计，为构建大规模、复杂的控制系统提供了基础。
