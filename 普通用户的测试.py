import numpy as np
import matplotlib.pyplot as plt

from pycontroldae.core import Module, System, Simulator, DataProbe
from pycontroldae.blocks import Step
import matplotlib
try:
    matplotlib.use('TKAgg')
except:
    pass
plt.rcParams['font.sans-serif'] = ['SimHei', 'SimSun', 'Times New Roman']
plt.rcParams['axes.unicode_minus'] = True
plt.rcParams['font.size'] = 9.0

def SecondOrderDAE(name, zeta=0.2, wn=10.0, k=200.0):
    """
    二阶系统（DAE 形式）：
        x' = v
        v' = -2*zeta*wn*v - wn^2*x + u
        y  = k*x   （代数约束）
    """

    m = Module(name)

    # ===== 状态 =====
    m.add_state("x", 0.0)  # 位移
    m.add_state("v", 0.0)  # 速度

    # ===== 代数变量（无导数）=====
    m.add_state("y", 0.0)  # 输出
    m.add_state("u", 0.0)  # 输入信号

    # ===== 参数 =====
    m.add_param("zeta", zeta)
    m.add_param("wn", wn)
    m.add_param("k", k)

    # ===== 微分方程 =====
    m.add_equation("D(x) ~ v")
    m.add_equation("D(v) ~ -2*zeta*wn*v - wn^2*x + u")

    # ===== 代数方程 =====
    m.add_equation("y ~ k*x")

    return m


step = Step(
    name="step",
    amplitude=1.0,
    step_time=0.0
)

# 非常关键（很多库会踩坑）
step.set_output("signal")
# 创建系统
system = System("second_order_dae_demo")

# 创建被控对象
plant = SecondOrderDAE(
    name="plant",
    zeta=0.2,  # 初始阻尼
    wn=10.0,
    k=200.0
)

# 添加模块
system.add_module(step)
system.add_module(plant)

# 连接：u(t) -> plant.u
system.connect("step.signal ~ plant.u")

# 编译（自动 DAE 简化）
system.compile()

probe = DataProbe(
    variables=[
        "plant.x",
        "plant.v",
        "plant.y"
    ],
    names=[
        "x",
        "v",
        "y"
    ],
    description="Second order DAE states"
)
sim = Simulator(system)
zetas = [0.1, 0.3, 0.7, 1.0]

plt.figure(figsize=(8, 5))

for z in zetas:
    result = sim.run(
        t_span=(0.0, 5.0),
        dt=0.001,
        params={
            "plant.zeta": z
        },
        probes=probe
    )

    df = result.get_probe_dataframe()
    plt.plot(df["time"], df["x"], label=f"zeta = {z}")
    plt.plot(df["time"], df["y"], label=f"zeta = {z}")

plt.xlabel("Time (s)")
plt.ylabel("Displacement x")
plt.title("Second-order system with different damping ratios")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
