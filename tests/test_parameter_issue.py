"""
测试：参数 k 是否导致 probe 提取错误
"""
import numpy as np
from pycontroldae.core import Module, System, Simulator, DataProbe


class Test1_ConstantCoefficient(Module):
    """测试1: 硬编码常数 2"""
    def __init__(self, name):
        super().__init__(name)
        self.add_state("x", 1.0)
        self.add_state("v", 0.0)
        self.add_state("y", 0.0)

        self.add_equation("D(x) ~ v")
        self.add_equation("D(v) ~ -4*x")
        self.add_equation("y ~ 2*x")  # 硬编码 2


class Test2_ParameterCoefficient(Module):
    """测试2: 使用参数 k"""
    def __init__(self, name):
        super().__init__(name)
        self.add_state("x", 1.0)
        self.add_state("v", 0.0)
        self.add_state("y", 0.0)
        self.add_param("k", 2.0)

        self.add_equation("D(x) ~ v")
        self.add_equation("D(v) ~ -4*x")
        self.add_equation("y ~ k*x")  # 使用参数 k


print("=" * 70)
print("测试：参数是否导致 probe 提取错误")
print("=" * 70)

# 测试1: 硬编码常数
print("\n[测试1] 代数方程: y ~ 2*x (硬编码)")
sys1 = System("test1")
mod1 = Test1_ConstantCoefficient("m")
sys1.add_module(mod1)
sys1.compile()

probe1 = DataProbe(variables=["m.x", "m.y"], names=["x", "y"])
sim1 = Simulator(sys1)
result1 = sim1.run(t_span=(0.0, 2.0), dt=0.1, probes=probe1)

df1 = result1.get_probe_dataframe()
x1 = df1["x"].values
y1 = df1["y"].values
error1 = np.max(np.abs(y1 - 2*x1))

print(f"  y vs 2*x 误差: {error1:.6e}")
print(f"  结果: {'[OK] y = 2*x' if error1 < 1e-10 else '[ERROR] y != 2*x'}")

# 测试2: 参数k
print("\n[测试2] 代数方程: y ~ k*x (k=2, 参数)")
sys2 = System("test2")
mod2 = Test2_ParameterCoefficient("m")
sys2.add_module(mod2)
sys2.compile()

probe2 = DataProbe(variables=["m.x", "m.y"], names=["x", "y"])
sim2 = Simulator(sys2)
result2 = sim2.run(t_span=(0.0, 2.0), dt=0.1, probes=probe2)

df2 = result2.get_probe_dataframe()
x2 = df2["x"].values
y2 = df2["y"].values
error2 = np.max(np.abs(y2 - 2*x2))

print(f"  y vs 2*x 误差: {error2:.6e}")
print(f"  结果: {'[OK] y = 2*x' if error2 < 1e-10 else '[ERROR] y != 2*x'}")

# 检查 y 是否等于 x
error2_vs_x = np.max(np.abs(y2 - x2))
print(f"  y vs x 误差: {error2_vs_x:.6e}")
if error2_vs_x < 1e-10:
    print(f"  警告: y = x (参数 k 被忽略！)")

# 详细对比
print("\n详细数据对比 (前10个点):")
print("  Time    [Test1] x      y      2*x    |y-2*x|    [Test2] x      y      2*x    |y-2*x|")
for i in range(min(10, len(df1))):
    t = df1["time"].values[i]
    print(f"  {t:5.2f}   {x1[i]:8.5f} {y1[i]:8.5f} {2*x1[i]:8.5f} {np.abs(y1[i]-2*x1[i]):8.2e}   "
          f"{x2[i]:8.5f} {y2[i]:8.5f} {2*x2[i]:8.5f} {np.abs(y2[i]-2*x2[i]):8.2e}")

print("\n" + "=" * 70)
print("结论:")
if error1 < 1e-10 and error2 > 1e-3:
    print("[发现BUG] 当代数方程使用参数时，probe 提取错误！")
    print("  - y ~ 2*x (常数) --> 正确")
    print("  - y ~ k*x (参数 k=2) --> 错误")
elif error1 < 1e-10 and error2 < 1e-10:
    print("[OK] 两种方式都正确")
else:
    print("[异常] 两种方式都有问题")
print("=" * 70)
