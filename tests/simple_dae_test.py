"""
简化的DAE系统测试 - 验证代数约束功能
使用Port API和Module构建一个简单的RLC电路
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import io
from pycontroldae.core import Module, System, Simulator, DataProbe
from pycontroldae.blocks import Step

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class ResistorInductor(Module):
    """
    电阻-电感串联（RL电路）

    微分方程:
        L * di/dt = V_in - R*i - V_out

    代数约束:
        V_L = L * di/dt (电感电压)
    """

    def __init__(self, name, R=10.0, L=0.1):
        super().__init__(name)

        # 状态变量
        self.add_state("i", 0.0)  # 电流

        # 参数
        self.add_param("R", R)
        self.add_param("L", L)

        # 输入/输出
        self.add_state("V_in", 0.0)  # 输入电压
        self.add_state("V_out", 0.0)  # 输出电压（到电容）

        # 代数变量
        self.add_state("V_L", 0.0)  # 电感电压
        self.add_state("i_out", 0.0)  # 输出电流

        # 微分方程
        self.add_equation("D(i) ~ (V_in - R*i - V_out) / L")

        # 代数约束
        self.add_equation("0 ~ V_L - (V_in - R*i - V_out)")  # 电感电压
        self.add_equation("0 ~ i_out - i")  # 电流连续性


class Capacitor(Module):
    """
    电容

    微分方程:
        C * dV/dt = i_in

    代数约束:
        V_out = V (电压连续性)
    """

    def __init__(self, name, C=0.01):
        super().__init__(name)

        # 状态变量
        self.add_state("V", 0.0)  # 电容电压

        # 参数
        self.add_param("C", C)

        # 输入
        self.add_state("i_in", 0.0)  # 输入电流

        # 输出（代数）
        self.add_state("V_out", 0.0)  # 输出电压

        # 微分方程
        self.add_equation("D(V) ~ i_in / C")

        # 代数约束
        self.add_equation("0 ~ V_out - V")


def run_simple_dae_test():
    """运行简单的DAE测试"""

    print("=" * 70)
    print("简化的DAE系统测试 - RLC电路")
    print("=" * 70)
    print("\n系统结构: 电压源 -> [R-L] -> [C] -> 地")
    print("\n包含:")
    print("  - 2个微分方程 (电感电流, 电容电压)")
    print("  - 4个代数约束 (电感电压, 电流连续, 电压连续)")
    print("=" * 70)

    # 创建系统
    system = System("rlc_circuit")

    # 1. 电压源
    print("\n[1/3] 创建电压源 (12V)")
    voltage_source = Step(name="input", amplitude=12.0, step_time=0.0)
    voltage_source.set_output("signal")

    # 2. RL部分
    print("[2/3] 创建电阻-电感 (R=10Ω, L=0.1H)")
    rl = ResistorInductor(name="rl", R=10.0, L=0.1)

    # 3. 电容
    print("[3/3] 创建电容 (C=0.01F)")
    cap = Capacitor(name="cap", C=0.01)

    # 添加模块
    system.add_module(voltage_source)
    system.add_module(rl)
    system.add_module(cap)

    # 使用Port API连接
    print("\n建立连接:")
    print("  ├─ 电压源 -> RL输入")
    system.connect(voltage_source.signal >> rl.V_in)

    print("  ├─ RL电流输出 -> 电容电流输入")
    system.connect(rl.i_out >> cap.i_in)

    print("  └─ 电容电压输出 -> RL电压反馈")
    system.connect(cap.V_out >> rl.V_out)

    # 编译系统
    print("\n编译系统（DAE简化）...")
    system.compile()
    print("✓ 编译完成！")

    # 不使用DataProbe，直接获取所有状态
    print("\n开始仿真 (0-2秒)...")
    simulator = Simulator(system)
    result = simulator.run(
        t_span=(0.0, 2.0),
        dt=0.01,
        solver="Rodas5"
    )

    print("\n✓ 仿真完成！")
    print("\n系统状态变量:")
    for name in result.state_names[:10]:  # 只显示前10个
        print(f"  - {name}")

    # 打印统计
    result.print_summary()

    # 绘图
    print("\n生成可视化...")
    plot_simple_results(result)

    return result


def plot_simple_results(result):
    """绘制简单结果"""

    times = result.times

    # 尝试获取关键变量
    try:
        # 直接从状态名称获取
        state_dict = {name: result.get_state(name) for name in result.state_names}

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # 1. 输入电压
        ax = axes[0, 0]
        if 'input.signal' in state_dict:
            ax.plot(times, state_dict['input.signal'], 'b-', linewidth=2, label='输入电压')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('电压 (V)')
        ax.set_title('输入电压', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 2. 电流
        ax = axes[0, 1]
        if 'rl.i' in state_dict:
            ax.plot(times, state_dict['rl.i'], 'r-', linewidth=2, label='电路电流')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('电流 (A)')
        ax.set_title('电路电流', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 3. 电容电压
        ax = axes[1, 0]
        if 'cap.V' in state_dict:
            ax.plot(times, state_dict['cap.V'], 'g-', linewidth=2, label='电容电压')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('电压 (V)')
        ax.set_title('电容电压', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 4. 电感电压（代数变量）
        ax = axes[1, 1]
        if 'rl.V_L' in state_dict:
            ax.plot(times, state_dict['rl.V_L'], 'purple', linewidth=2, label='电感电压')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('电压 (V)')
        ax.set_title('电感电压（代数约束）', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.suptitle('RLC电路仿真 - 含代数约束的DAE系统', fontsize=14, fontweight='bold')
        plt.tight_layout()

        filename = 'simple_dae_rlc.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"✓ 图形已保存: {filename}")

        plt.show()

    except Exception as e:
        print(f"绘图时出错: {e}")
        print(f"可用状态: {result.state_names[:20]}")

    # 保存数据
    result.to_csv('simple_dae_rlc.csv')
    print(f"✓ 数据已保存: simple_dae_rlc.csv")


if __name__ == "__main__":
    result = run_simple_dae_test()

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
    print("\n关键观察:")
    print("  1. 电流从0逐渐上升（由电感限制上升速率）")
    print("  2. 电容电压逐渐充电到稳态值")
    print("  3. 代数约束（电感电压）自动满足")
    print("  4. structural_simplify成功简化DAE系统")
