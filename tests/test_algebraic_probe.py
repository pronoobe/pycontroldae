"""
测试probe对代数方程变量的支持
使用二阶系统 + 代数方程 y=2*x 进行验证
"""

import numpy as np
import matplotlib.pyplot as plt
from pycontroldae.core import Module, System, Simulator, DataProbe


class SecondOrderSystem(Module):
    """二阶系统"""
    def __init__(self, name):
        super().__init__(name)

        # 微分状态变量
        self.add_state("x", 1.0)     # 位置
        self.add_state("v", 0.0)     # 速度

        # 代数变量
        self.add_state("y", 0.0)     # y = 2*x (代数方程)

        # 参数
        self.add_param("omega", 2.0)  # 角频率
        self.add_param("zeta", 0.3)   # 阻尼比

        # 微分方程
        self.add_equation("D(x) ~ v")
        self.add_equation("D(v) ~ -omega^2 * x - 2*zeta*omega * v")

        # 代数方程: y = 2*x
        self.add_equation("0 ~ y - 2*x")


def test_algebraic_probe():
    """测试probe能否正确输出代数方程变量"""

    print("=" * 70)
    print("测试probe对代数方程变量的支持")
    print("=" * 70)

    # 创建系统
    system = System("test_algebraic")
    oscillator = SecondOrderSystem(name="osc")
    system.add_module(oscillator)

    print("\n系统配置:")
    print("  - 微分方程: D(x) = v")
    print("  - 微分方程: D(v) = -omega^2 * x - 2*zeta*omega * v")
    print("  - 代数方程: y = 2*x")
    print("  - 初始条件: x(0)=1.0, v(0)=0.0")

    # 编译系统
    print("\n编译系统...")
    system.compile()
    print("[OK] 编译完成")

    # 配置probe - 观察微分变量和代数变量
    print("\n配置DataProbe:")
    print("  - osc.x (微分状态)")
    print("  - osc.v (微分状态)")
    print("  - osc.y (代数变量, 应该 = 2*x)")

    probe = DataProbe(
        variables=["osc.x", "osc.v", "osc.y"],
        names=["x", "v", "y"],
        description="二阶系统测试"
    )

    # 仿真
    print("\n运行仿真...")
    simulator = Simulator(system)
    result = simulator.run(
        t_span=(0.0, 10.0),
        dt=0.01,
        solver="Rodas5",
        probes=probe
    )
    print("[OK] 仿真完成")

    # 检查结果
    print("\n检查结果:")
    print(f"  系统状态变量: {result.state_names}")

    if result.probe_data:
        probe_df = result.get_probe_dataframe()
        print(f"\n  Probe数据形状: {probe_df.shape}")
        print(f"  Probe列名: {list(probe_df.columns)}")

        # 提取数据
        t = probe_df['time'].values
        x = probe_df['x'].values
        v = probe_df['v'].values
        y = probe_df['y'].values

        # 验证代数约束 y = 2*x
        y_expected = 2 * x
        error = np.abs(y - y_expected)
        max_error = np.max(error)

        print(f"\n验证代数约束 y = 2*x:")
        print(f"  x的范围: [{np.min(x):.4f}, {np.max(x):.4f}]")
        print(f"  y的范围: [{np.min(y):.4f}, {np.max(y):.4f}]")
        print(f"  y是否全为0: {np.allclose(y, 0.0)}")
        print(f"  最大误差 |y - 2*x|: {max_error:.6e}")

        if np.allclose(y, 0.0):
            print("\n[ERROR] 问题确认: 代数变量y全为0，probe无法正确提取代数变量!")
        elif max_error < 1e-3:
            print("\n[OK] 代数约束满足: y = 2*x")
        else:
            print(f"\n[WARNING] 警告: 代数约束误差较大 (max_error={max_error:.6e})")

        # 绘图
        print("\n生成可视化...")
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        # x vs t
        axes[0, 0].plot(t, x, 'b-', linewidth=2, label='x')
        axes[0, 0].set_xlabel('Time (s)')
        axes[0, 0].set_ylabel('x')
        axes[0, 0].set_title('Position x vs Time')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].legend()

        # v vs t
        axes[0, 1].plot(t, v, 'r-', linewidth=2, label='v')
        axes[0, 1].set_xlabel('Time (s)')
        axes[0, 1].set_ylabel('v')
        axes[0, 1].set_title('Velocity v vs Time')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].legend()

        # y vs t (对比 2*x)
        axes[1, 0].plot(t, y, 'g-', linewidth=2, label='y (probe)')
        axes[1, 0].plot(t, y_expected, 'k--', linewidth=1, label='2*x (expected)')
        axes[1, 0].set_xlabel('Time (s)')
        axes[1, 0].set_ylabel('y')
        axes[1, 0].set_title('Algebraic Variable y vs Time')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].legend()

        # 误差
        axes[1, 1].plot(t, error, 'r-', linewidth=2)
        axes[1, 1].set_xlabel('Time (s)')
        axes[1, 1].set_ylabel('|y - 2*x|')
        axes[1, 1].set_title(f'Error (max={max_error:.2e})')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].set_yscale('log')

        plt.suptitle('Algebraic Variable Probe Test', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig('test_algebraic_probe.png', dpi=300, bbox_inches='tight')
        print("[OK] 图形已保存: test_algebraic_probe.png")
        # plt.show()

    else:
        print("[WARNING] 未找到probe数据")

    # 保存数据
    result.to_csv('test_algebraic_probe.csv', include_probes=True)
    print("[OK] 数据已保存: test_algebraic_probe.csv")

    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)

    return result


if __name__ == "__main__":
    result = test_algebraic_probe()
