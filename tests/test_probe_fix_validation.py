"""
验证 DataProbe 修复 - 完整测试
"""
import numpy as np
from pycontroldae.core import Module, System, Simulator, DataProbe
from pycontroldae.blocks import Step


def create_test_system(k_value=2.0):
    """创建测试系统"""
    class Plant(Module):
        def __init__(self, name, k=2.0):
            super().__init__(name)
            self.add_state("x", 0.0)
            self.add_state("v", 0.0)
            self.add_state("y", 0.0)  # 代数变量
            self.add_state("u", 0.0)
            self.add_param("k", k)
            self.add_param("zeta", 0.2)
            self.add_param("wn", 10.0)

            self.add_equation("D(x) ~ v")
            self.add_equation("D(v) ~ -2*zeta*wn*v - wn^2*x + u")
            self.add_equation("y ~ k*x")  # 使用参数的代数方程

    step = Step(name="step", amplitude=1.0, step_time=0.0)
    step.set_output("signal")

    system = System("test_fix")
    plant = Plant(name="plant", k=k_value)

    system.add_module(step)
    system.add_module(plant)
    system.connect("step.signal ~ plant.u")

    return system


print("=" * 70)
print("DataProbe 修复验证测试")
print("=" * 70)

# 测试1: k=2
print("\n[测试1] k=2 的情况")
sys1 = create_test_system(k_value=2.0)
sys1.compile()

probe1 = DataProbe(
    variables=["plant.x", "plant.y"],
    names=["x", "y"]
)

sim1 = Simulator(sys1)
result1 = sim1.run(t_span=(0.0, 2.0), dt=0.01, probes=probe1)

df1 = result1.get_probe_dataframe()
x1 = df1["x"].values
y1 = df1["y"].values

error1 = np.max(np.abs(y1 - 2*x1))
print(f"  期望: y = 2*x")
print(f"  实际误差 |y - 2*x|: {error1:.6e}")
print(f"  结果: {'[OK] 正确' if error1 < 1e-10 else '[FAILED] 错误'}")

# 测试2: k=3.5
print("\n[测试2] k=3.5 的情况")
sys2 = create_test_system(k_value=3.5)
sys2.compile()

probe2 = DataProbe(
    variables=["plant.x", "plant.y"],
    names=["x", "y"]
)

sim2 = Simulator(sys2)
result2 = sim2.run(t_span=(0.0, 2.0), dt=0.01, probes=probe2)

df2 = result2.get_probe_dataframe()
x2 = df2["x"].values
y2 = df2["y"].values

error2 = np.max(np.abs(y2 - 3.5*x2))
print(f"  期望: y = 3.5*x")
print(f"  实际误差 |y - 3.5*x|: {error2:.6e}")
print(f"  结果: {'[OK] 正确' if error2 < 1e-10 else '[FAILED] 错误'}")

# 测试3: 复杂表达式 y ~ k*(x + v)
print("\n[测试3] 复杂表达式 y ~ k*(x + v)")

class ComplexPlant(Module):
    def __init__(self, name, k=2.0):
        super().__init__(name)
        self.add_state("x", 1.0)
        self.add_state("v", 0.0)
        self.add_state("y", 0.0)
        self.add_param("k", k)

        self.add_equation("D(x) ~ v")
        self.add_equation("D(v) ~ -4*x")
        self.add_equation("y ~ k*(x + v)")  # 更复杂的表达式

sys3 = System("test3")
plant3 = ComplexPlant("plant", k=2.5)
sys3.add_module(plant3)
sys3.compile()

probe3 = DataProbe(
    variables=["plant.x", "plant.v", "plant.y"],
    names=["x", "v", "y"]
)

sim3 = Simulator(sys3)
result3 = sim3.run(t_span=(0.0, 2.0), dt=0.01, probes=probe3)

df3 = result3.get_probe_dataframe()
x3 = df3["x"].values
v3 = df3["v"].values
y3 = df3["y"].values

error3 = np.max(np.abs(y3 - 2.5*(x3 + v3)))
print(f"  期望: y = 2.5*(x + v)")
print(f"  实际误差 |y - 2.5*(x+v)|: {error3:.6e}")
print(f"  结果: {'[OK] 正确' if error3 < 1e-10 else '[FAILED] 错误'}")

# 总结
print("\n" + "=" * 70)
print("测试总结:")
all_passed = (error1 < 1e-10) and (error2 < 1e-10) and (error3 < 1e-10)
if all_passed:
    print("  [SUCCESS] 所有测试通过! DataProbe 修复成功!")
    print("  含参数的代数方程现在可以正确提取了。")
else:
    print("  [FAILED] 部分测试失败")
    if error1 >= 1e-10:
        print(f"    - 测试1失败 (误差={error1:.2e})")
    if error2 >= 1e-10:
        print(f"    - 测试2失败 (误差={error2:.2e})")
    if error3 >= 1e-10:
        print(f"    - 测试3失败 (误差={error3:.2e})")

print("=" * 70)
