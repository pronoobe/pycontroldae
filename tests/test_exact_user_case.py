"""
精确复现用户的测试案例
"""
import numpy as np
from pycontroldae.core import Module, System, Simulator, DataProbe
from pycontroldae.blocks import Step


def SecondOrderDAE(name, zeta=0.2, wn=10.0, k=200.0):
    """
    与用户测试完全相同的代码
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

    # 代数方程
    m.add_equation("y ~ k*x")

    return m


print("=" * 70)
print("精确复现用户测试案例")
print("=" * 70)

step = Step(name="step", amplitude=1.0, step_time=0.0)
step.set_output("signal")

# 创建系统
system = System("test_exact")

# 创建被控对象 - 注意 k=2
plant = SecondOrderDAE(name="plant", zeta=0.2, wn=10.0, k=2)

# 添加模块
system.add_module(step)
system.add_module(plant)

# 连接
system.connect("step.signal ~ plant.u")

print("\n编译系统...")
system.compile()
print("[OK] 编译完成")

# 检查Julia系统
from pycontroldae.core import get_jl
jl = get_jl()

print("\n[Julia系统信息]")
try:
    unknowns = jl.seval("unknowns(_simplified_test_exact)")
    print(f"  Unknowns: {len(unknowns)} 个")
    for i in range(len(unknowns)):
        var_str = jl.seval(f"string(unknowns(_simplified_test_exact)[{i+1}])")
        var_str = var_str.replace("₊", ".").replace("(t)", "")
        print(f"    - {var_str}")

    try:
        obs = jl.seval("observed(_simplified_test_exact)")
        print(f"  Observed: {len(obs)} 个")
        for i in range(min(len(obs), 3)):
            obs_str = jl.seval(f"string(observed(_simplified_test_exact)[{i+1}])")
            obs_str = obs_str.replace("₊", ".").replace("(t)", "")[:80]
            print(f"    - {obs_str}")
    except:
        print(f"  Observed: 无法获取")
except Exception as e:
    print(f"  错误: {e}")

# 配置probe
probe = DataProbe(
    variables=["plant.x", "plant.v", "plant.y"],
    names=["x", "v", "y"]
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

# 检查结果
df = result.get_probe_dataframe()
x = df["x"].values
y = df["y"].values

error_2x = np.max(np.abs(y - 2*x))
error_x = np.max(np.abs(y - x))

print("\n[结果分析]")
print(f"  系统状态: {result.state_names}")
print(f"  x 范围: [{np.min(x):.6f}, {np.max(x):.6f}]")
print(f"  y 范围: [{np.min(y):.6f}, {np.max(y):.6f}]")
print(f"  |y - 2*x| 最大误差: {error_2x:.6e}")
print(f"  |y - x| 最大误差: {error_x:.6e}")

if error_x < 1e-10:
    print("\n[ERROR] y = x (参数 k 被忽略！)")
elif error_2x < 1e-10:
    print("\n[OK] y = 2*x (正确)")
else:
    print("\n[WARNING] y 既不等于 x 也不等于 2*x")

# 详细数据
print("\n前10个数据点:")
print("  Time      x           v           y           2*x         y-x")
v_data = df["v"].values
for i in range(min(10, len(df))):
    t = df["time"].values[i]
    print(f"  {t:5.2f}   {x[i]:10.6f}  {v_data[i]:10.6f}  {y[i]:10.6f}  {2*x[i]:10.6f}  {y[i]-x[i]:10.6e}")

result.to_csv('test_exact_case.csv', include_probes=True)
print("\n[OK] 数据已保存: test_exact_case.csv")

print("\n" + "=" * 70)
