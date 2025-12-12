# Design Doc: pycontroldae (Julia Backend MVP)

## 1. 目标
实现一个 Python 库，允许用户定义模块化控制系统，底层自动转译为 Julia 的 `ModelingToolkit.jl` 进行高性能 DAE 求解。

## 2. 核心技术栈
- **Frontend**: Python (User API)
- **Bridge**: `juliacall` (Python-Julia 互操作)
- **Backend**: Julia (`ModelingToolkit.jl`, `DifferentialEquations.jl`)

## 3. 目录结构
pycontroldae/
├── core/
│   ├── __init__.py
│   ├── backend.py      # 负责初始化 Julia 环境，加载 MTK 包
│   ├── module.py       # Python Module 基类 -> 映射为 Julia ODESystem
│   ├── system.py       # 负责将多个 Module + 连接 组装成顶层 System
│   └── simulator.py    # 负责将 System 转换为 Problem 并求解
├── examples/
│   └── simple_rc.py    # 测试用例
└── requirements.txt

## 4. 模块详细设计

### 4.1 `core/backend.py`
- 职责：单例模式。第一次调用时初始化 Julia 环境。
- 动作：
  - `from juliacall import Main as jl`
  - `jl.seval("using ModelingToolkit")`
  - `jl.seval("using DifferentialEquations")`
  - `jl.seval("using ModelingToolkit: t_nounits as t, D_nounits as D")`
- 提供一个 helper 函数 `get_jl()` 返回 `jl` 对象。

### 4.2 `core/module.py`
- 类 `Module`:
  - `__init__(self, name)`: 接受名字。
  - `add_state(name, default)`: 注册状态变量。
  - `add_param(name, default)`: 注册参数。
  - `add_equation(eq_str)`: 接受字符串形式的方程 (例如 "D(x) ~ -a*x + u").
  - `build()`:
    - 在 Julia 域中创建 `@variables`, `@parameters`。
    - 构造并返回一个 Julia `ODESystem` 对象。

### 4.3 `core/system.py`
- 类 `System`:
  - `add_module(module)`: 加入子模块。
  - `connect(src_module, src_var, dst_module, dst_var)`:
    - 生成 Julia 连接语句: `connect(sys1.var, sys2.var)`。
  - `compile()`:
    - 1. 组合所有子系统。
    - 2. 执行 `structural_simplify` (关键！自动处理 DAE index)。
    - 返回简化后的 Julia System。

### 4.4 `core/simulator.py`
- 类 `Simulator`:
  - `__init__(system)`
  - `run(t_span)`:
    - 构造 `ODEProblem`。
    - 调用 `solve(prob, Rodas5())` (适合刚性/DAE)。
    - 将 Julia 的 Solution 转回 Python 字典或 DataFrame 返回。

## 5. 阶段 A 验收标准 (MVP Demo)
能够运行 `examples/simple_rc.py`:
1. 定义一个 RC 电路（电阻 + 电容）。
2. 定义一个 Step 输入源。
3. 连接 Input -> RC。
4. 仿真并打印结果。