"""
测试用户提出的情况 - 代数方程 y ~ k*x
"""
import numpy as np
from pycontroldae.core import Module, System, Simulator, DataProbe
from pycontroldae.blocks import Step


def SecondOrderDAE(name, zeta=0.2, wn=10.0, k=200.0):
    """
    二阶系统（DAE 形式）：
        x' = v
        v' = -2*zeta*wn*v - wn^2*x + u
        y  = k*x   （代数约束）
    """
    m = Module(name)

    # 状态
    m.add_state("x", 0.0)  # 位移
    m.add_state("v", 0.0)  # 速度

    # 代数变量
    m.add_state("y", 0.0)  # 输出
    m.add_state("u", 0.0)  # 输入信号

    # 参数
    m.add_param("zeta", zeta)
    m.add_param("wn", wn)
    m.add_param("k", k)

    # 微分方程
    m.add_equation("D(x) ~ v")
    m.add_equation("D(v) ~ -2*zeta*wn*v - wn^2*x + u")

    # 代数方程 - 用户使用的形式
    m.add_equation("y ~ k*x")

    return m


print("=" * 70)
print("测试用户案例: 代数方程 y ~ k*x")
print("=" * 70)

step = Step(name="step", amplitude=1.0, step_time=0.0)
step.set_output("signal")

# 创建系统
system = System("second_order_dae_demo")

# 创建被控对象
plant = SecondOrderDAE(name="plant", zeta=0.2, wn=10.0, k=2)

# 添加模块
system.add_module(step)
system.add_module(plant)

# 连接
system.connect("step.signal ~ plant.u")

print("\n编译系统...")
system.compile()
print("[OK] 编译完成")

# 配置probe
probe = DataProbe(
    variables=["plant.x", "plant.v", "plant.y"],
    names=["x", "v", "y"],
    description="Second order DAE states"
)

print("\n运行仿真...")
sim = Simulator(system)
result = sim.run(
    t_span=(0.0, 5.0),
    dt=0.01,
    params={"plant.zeta": 0.3},
    probes=probe
)
print("[OK] 仿真完成")

print("\n检查结果:")
print(f"  系统状态变量: {result.state_names}")

if result.probe_data:
    df = result.get_probe_dataframe()
    print(f"\n  Probe数据形状: {df.shape}")
    print(f"  Probe列名: {list(df.columns)}")

    # 检查数据
    x = df["x"].values
    v = df["v"].values
    y = df["y"].values

    # k = 2, 所以 y 应该等于 2*x
    y_expected = 2 * x
    error = np.abs(y - y_expected)
    max_error = np.max(error)

    print(f"\n验证代数约束 y = k*x (k=2):")
    print(f"  x的范围: [{np.min(x):.6f}, {np.max(x):.6f}]")
    print(f"  y的范围: [{np.min(y):.6f}, {np.max(y):.6f}]")
    print(f"  y是否全为0: {np.allclose(y, 0.0)}")
    print(f"  最大误差 |y - 2*x|: {max_error:.6e}")

    print(f"\n前10个时间点的数据:")
    print("  Time      x           v           y           2*x")
    for i in range(min(10, len(df))):
        t = df["time"].values[i]
        print(f"  {t:6.3f}   {x[i]:10.6f}  {v[i]:10.6f}  {y[i]:10.6f}  {y_expected[i]:10.6f}")

    if np.allclose(y, 0.0):
        print("\n[ERROR] 问题确认: 代数变量y全为0!")
    elif max_error < 1e-3:
        print("\n[OK] 代数约束满足: y = k*x")
    else:
        print(f"\n[WARNING] 代数约束误差较大: {max_error:.6e}")

    # 保存数据
    result.to_csv('test_user_case.csv', include_probes=True)
    print("\n[OK] 数据已保存: test_user_case.csv")
else:
    print("[WARNING] 未找到probe数据")

print("\n" + "=" * 70)
print("测试完成!")
print("=" * 70)
