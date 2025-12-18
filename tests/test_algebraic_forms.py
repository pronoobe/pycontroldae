"""
对比测试两种代数方程的写法
"""
import numpy as np
from pycontroldae.core import Module, System, Simulator, DataProbe


class TestSystem1(Module):
    """使用 y ~ k*x 形式"""
    def __init__(self, name):
        super().__init__(name)
        self.add_state("x", 1.0)
        self.add_state("v", 0.0)
        self.add_state("y", 0.0)
        self.add_param("k", 2.0)
        self.add_param("omega", 2.0)
        self.add_param("zeta", 0.3)

        self.add_equation("D(x) ~ v")
        self.add_equation("D(v) ~ -omega^2 * x - 2*zeta*omega * v")
        self.add_equation("y ~ k*x")  # 形式1: y ~ k*x


class TestSystem2(Module):
    """使用 0 ~ y - k*x 形式"""
    def __init__(self, name):
        super().__init__(name)
        self.add_state("x", 1.0)
        self.add_state("v", 0.0)
        self.add_state("y", 0.0)
        self.add_param("k", 2.0)
        self.add_param("omega", 2.0)
        self.add_param("zeta", 0.3)

        self.add_equation("D(x) ~ v")
        self.add_equation("D(v) ~ -omega^2 * x - 2*zeta*omega * v")
        self.add_equation("0 ~ y - k*x")  # 形式2: 0 ~ y - k*x


print("=" * 70)
print("对比测试: 两种代数方程写法")
print("=" * 70)

# 测试系统1: y ~ k*x
print("\n[测试1] 使用代数方程: y ~ k*x")
system1 = System("test1")
sys1 = TestSystem1("sys")
system1.add_module(sys1)
system1.compile()

probe1 = DataProbe(
    variables=["sys.x", "sys.v", "sys.y"],
    names=["x", "v", "y"],
    description="Test1"
)

sim1 = Simulator(system1)
result1 = sim1.run(t_span=(0.0, 5.0), dt=0.1, probes=probe1)

df1 = result1.get_probe_dataframe()
x1 = df1["x"].values
y1 = df1["y"].values
error1 = np.abs(y1 - 2*x1)

print(f"  系统状态: {result1.state_names}")
print(f"  x的范围: [{np.min(x1):.6f}, {np.max(x1):.6f}]")
print(f"  y的范围: [{np.min(y1):.6f}, {np.max(y1):.6f}]")
print(f"  最大误差 |y - 2*x|: {np.max(error1):.6e}")

# 测试系统2: 0 ~ y - k*x
print("\n[测试2] 使用代数方程: 0 ~ y - k*x")
system2 = System("test2")
sys2 = TestSystem2("sys")
system2.add_module(sys2)
system2.compile()

probe2 = DataProbe(
    variables=["sys.x", "sys.v", "sys.y"],
    names=["x", "v", "y"],
    description="Test2"
)

sim2 = Simulator(system2)
result2 = sim2.run(t_span=(0.0, 5.0), dt=0.1, probes=probe2)

df2 = result2.get_probe_dataframe()
x2 = df2["x"].values
y2 = df2["y"].values
error2 = np.abs(y2 - 2*x2)

print(f"  系统状态: {result2.state_names}")
print(f"  x的范围: [{np.min(x2):.6f}, {np.max(x2):.6f}]")
print(f"  y的范围: [{np.min(y2):.6f}, {np.max(y2):.6f}]")
print(f"  最大误差 |y - 2*x|: {np.max(error2):.6e}")

# 对比前10个时间点
print("\n对比前10个时间点:")
print("  Time      [测试1] x      y      2*x    |误差|     [测试2] x      y      2*x    |误差|")
for i in range(min(10, len(df1))):
    t = df1["time"].values[i]
    print(f"  {t:5.2f}    {x1[i]:8.5f} {y1[i]:8.5f} {2*x1[i]:8.5f} {error1[i]:8.5f}    "
          f"{x2[i]:8.5f} {y2[i]:8.5f} {2*x2[i]:8.5f} {error2[i]:8.5f}")

# 结论
print("\n" + "=" * 70)
print("结论:")
if np.max(error1) > 1e-3:
    print("  [问题] 形式1 'y ~ k*x' 无法正确建立代数约束")
else:
    print("  [OK] 形式1 'y ~ k*x' 正确")

if np.max(error2) > 1e-3:
    print("  [问题] 形式2 '0 ~ y - k*x' 无法正确建立代数约束")
else:
    print("  [OK] 形式2 '0 ~ y - k*x' 正确")

print("\n建议: 使用 '0 ~ y - k*x' 形式来定义代数约束")
print("=" * 70)
