"""
测试修复后的DataProbe功能
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import io
from pycontroldae.core import Module, System, Simulator, DataProbe
from pycontroldae.blocks import Step

# Set UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class Mass(Module):
    """质量块"""
    def __init__(self, name, mass=1.0, damping=0.1):
        super().__init__(name)
        self.add_state("x", 0.0)
        self.add_state("v", 0.0)
        self.add_param("m", mass)
        self.add_param("b", damping)
        self.add_state("F_ext", 0.0)
        self.add_state("F_spring", 0.0)
        self.add_state("x_out", 0.0)
        self.add_state("v_out", 0.0)
        self.add_equation("D(v) ~ (F_ext + F_spring - b*v) / m")
        self.add_equation("D(x) ~ v")
        self.add_equation("0 ~ x_out - x")
        self.add_equation("0 ~ v_out - v")


class Spring(Module):
    """弹簧（代数约束）"""
    def __init__(self, name, stiffness=10.0):
        super().__init__(name)
        self.add_param("k", stiffness)
        self.add_state("x1", 0.0)
        self.add_state("x2", 0.0)
        self.add_state("F1", 0.0)
        self.add_state("F2", 0.0)
        self.add_state("F", 0.0)
        self.add_equation("0 ~ F + k * (x2 - x1)")
        self.add_equation("0 ~ F1 + F")
        self.add_equation("0 ~ F2 - F")


def test_dataprobe_with_dae():
    """测试DataProbe在DAE系统中的功能"""

    print("=" * 70)
    print("测试修复后的DataProbe功能")
    print("=" * 70)

    # 创建系统
    system = System("test_probe")

    force = Step(name="force", amplitude=10.0, step_time=0.0)
    force.set_output("signal")

    m1 = Mass(name="m1", mass=1.0, damping=0.2)
    m2 = Mass(name="m2", mass=2.0, damping=0.3)
    spring = Spring(name="spring", stiffness=20.0)

    system.add_module(force)
    system.add_module(m1)
    system.add_module(m2)
    system.add_module(spring)

    # 连接
    system.connect(force.signal >> m1.F_ext)
    system.connect(m1.x_out >> spring.x1)
    system.connect(m2.x_out >> spring.x2)
    system.connect(spring.F1 >> m1.F_spring)
    system.connect(spring.F2 >> m2.F_spring)
    system.connect("0.0 ~ m2.F_ext")

    # 编译
    print("\n编译系统...")
    system.compile()
    print("✓ 编译完成")

    # 配置探针 - 测试各种类型的变量
    print("\n配置DataProbe...")
    print("  - 微分状态: m1.x, m1.v")
    print("  - 输出端口: m1.x_out, m1.v_out")
    print("  - 代数约束: spring.F")
    print("  - 输入信号: force.signal")

    probe = DataProbe(
        variables=[
            "m1.x",      # 微分状态
            "m1.v",      # 微分状态
            "m1.x_out",  # 代数输出
            "m1.v_out",  # 代数输出
            "spring.F",  # 代数约束（弹簧力）
            "force.signal"  # 输入信号
        ],
        names=[
            "质量1位置",
            "质量1速度",
            "质量1位置输出",
            "质量1速度输出",
            "弹簧力",
            "外力"
        ],
        description="测试探针"
    )

    # 仿真
    print("\n开始仿真...")
    simulator = Simulator(system)
    result = simulator.run(
        t_span=(0.0, 5.0),
        dt=0.01,
        solver="Rodas5",
        probes=probe
    )
    print("✓ 仿真完成")

    # 检查探针数据
    print("\n检查探针数据:")
    print(f"  可用状态: {result.state_names}")
    print(f"  探针数据: {list(result.probe_data.keys())}")

    if result.probe_data:
        probe_df = result.get_probe_dataframe()
        print(f"\n探针DataFrame形状: {probe_df.shape}")
        print(f"探针列名: {list(probe_df.columns)}")
        print(f"\n前5行数据:")
        print(probe_df.head())

        # 检查数据是否为零
        for col in probe_df.columns:
            if col != 'time':
                data = probe_df[col].values
                is_zero = np.allclose(data, 0.0)
                max_val = np.max(np.abs(data))
                print(f"  {col:20s}: {'全为0' if is_zero else f'最大值={max_val:.4f}'}")

        # 绘图
        print("\n生成可视化...")
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()

        for i, col in enumerate(probe_df.columns[1:]):  # Skip 'time'
            ax = axes[i]
            ax.plot(probe_df['time'], probe_df[col], linewidth=2)
            ax.set_xlabel('时间 (s)')
            ax.set_ylabel(col)
            ax.set_title(col, fontweight='bold')
            ax.grid(True, alpha=0.3)

        plt.suptitle('DataProbe测试结果 - 修复后', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig('dataprobe_test_fixed.png', dpi=300, bbox_inches='tight')
        print("✓ 图形已保存: dataprobe_test_fixed.png")
        plt.show()

    else:
        print("⚠ 未找到探针数据")

    # 保存数据
    result.to_csv('dataprobe_test_fixed.csv', include_probes=True)
    print("✓ 数据已保存: dataprobe_test_fixed.csv")

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)

    return result


if __name__ == "__main__":
    result = test_dataprobe_with_dae()
