"""
Second-order system damping simulation example
Demonstrates underdamped, critically damped, and overdamped system responses
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import io
from pycontroldae.blocks import StateSpace, Step
from pycontroldae.core import System, Simulator

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def create_second_order_system(name, omega_n, zeta):
    """
    创建二阶系统

    传递函数: H(s) = ω_n² / (s² + 2ζω_n·s + ω_n²)

    状态空间表示:
    dx1/dt = x2
    dx2/dt = -ω_n²·x1 - 2ζω_n·x2 + ω_n²·u

    参数:
        name: 系统名称
        omega_n: 自然频率 (rad/s)
        zeta: 阻尼比
    """
    # 状态矩阵
    A = np.array([
        [0.0, 1.0],
        [-omega_n**2, -2*zeta*omega_n]
    ])

    # 输入矩阵
    B = np.array([
        [0.0],
        [omega_n**2]
    ])

    # 输出矩阵 (输出位置 x1)
    C = np.array([[1.0, 0.0]])

    # 直接传递矩阵
    D = np.array([[0.0]])

    # 初始状态 [位置, 速度]
    initial_state = np.array([0.0, 0.0])

    return StateSpace(
        name=name,
        A=A, B=B, C=C, D=D,
        initial_state=initial_state
    )


def simulate_damping_systems():
    """仿真不同阻尼比的二阶系统"""

    # 系统参数
    omega_n = 2.0  # 自然频率 (rad/s)

    # 不同阻尼比
    damping_configs = [
        {"zeta": 0.1, "name": "欠阻尼 (ζ=0.1)", "color": "blue"},
        {"zeta": 0.4, "name": "欠阻尼 (ζ=0.4)", "color": "cyan"},
        {"zeta": 0.7, "name": "欠阻尼 (ζ=0.7)", "color": "green"},
        {"zeta": 1.0, "name": "临界阻尼 (ζ=1.0)", "color": "orange"},
        {"zeta": 2.0, "name": "过阻尼 (ζ=2.0)", "color": "red"},
    ]

    # 仿真时间
    t_span = (0.0, 10.0)
    dt = 0.01

    # 存储结果
    results = []

    print("=" * 60)
    print("二阶系统阻尼特性仿真")
    print("=" * 60)
    print(f"自然频率 ω_n = {omega_n} rad/s")
    print(f"阶跃输入幅值 = 1.0")
    print("-" * 60)

    # 对每个阻尼比进行仿真
    for i, config in enumerate(damping_configs):
        zeta = config["zeta"]
        label = config["name"]

        print(f"\n正在仿真: {label}")

        # 创建系统
        system_name = f"system_{i}"
        system = System(system_name)

        # 创建二阶系统模块
        plant = create_second_order_system(f"plant_{i}", omega_n, zeta)

        # 创建阶跃输入
        step_input = Step(name=f"input_{i}", amplitude=1.0, step_time=0.0)
        step_input.set_output("signal")

        # 添加模块
        system.add_module(plant)
        system.add_module(step_input)

        # 连接
        system.connect(f"input_{i}.signal ~ plant_{i}.u1")

        # 编译系统
        system.compile()

        # 创建仿真器并运行
        simulator = Simulator(system)
        result = simulator.run(t_span=t_span, dt=dt)

        # 保存结果
        results.append({
            "zeta": zeta,
            "label": label,
            "color": config["color"],
            "times": result.times,
            "output": result.get_state(f"plant_{i}.y1")
        })

        # 计算性能指标
        output = result.get_state(f"plant_{i}.y1")

        # 超调量 (如果有)
        max_val = np.max(output)
        overshoot = (max_val - 1.0) * 100 if max_val > 1.0 else 0.0

        # 稳态值
        steady_state = output[-1]

        # 上升时间 (10% 到 90%)
        idx_10 = np.argmax(output >= 0.1)
        idx_90 = np.argmax(output >= 0.9)
        rise_time = result.times[idx_90] - result.times[idx_10] if idx_90 > idx_10 else 0

        # 调节时间 (2% 误差带)
        settling_idx = len(output) - 1
        for j in range(len(output) - 1, 0, -1):
            if abs(output[j] - 1.0) > 0.02:
                settling_idx = j
                break
        settling_time = result.times[settling_idx]

        print(f"  超调量: {overshoot:.2f}%")
        print(f"  上升时间: {rise_time:.3f}s")
        print(f"  调节时间: {settling_time:.3f}s")
        print(f"  稳态值: {steady_state:.4f}")

    print("\n" + "=" * 60)
    print("仿真完成!")
    print("=" * 60)

    return results, damping_configs


def plot_results(results):
    """绘制仿真结果"""

    # 创建图形
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # 子图1: 阶跃响应
    ax1 = axes[0]
    for res in results:
        ax1.plot(res["times"], res["output"],
                label=res["label"],
                color=res["color"],
                linewidth=2)

    ax1.axhline(y=1.0, color='black', linestyle='--', linewidth=1, alpha=0.5, label='稳态值')
    ax1.axhline(y=1.02, color='gray', linestyle=':', linewidth=1, alpha=0.3)
    ax1.axhline(y=0.98, color='gray', linestyle=':', linewidth=1, alpha=0.3)
    ax1.fill_between([0, 10], 0.98, 1.02, color='gray', alpha=0.1, label='±2% 误差带')

    ax1.set_xlabel('时间 (s)', fontsize=12)
    ax1.set_ylabel('输出响应', fontsize=12)
    ax1.set_title('二阶系统阶跃响应 - 不同阻尼比', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=10)
    ax1.set_xlim([0, 10])
    ax1.set_ylim([-0.1, 1.8])

    # 子图2: 前5秒的详细响应
    ax2 = axes[1]
    for res in results:
        mask = res["times"] <= 5.0
        ax2.plot(res["times"][mask], res["output"][mask],
                label=res["label"],
                color=res["color"],
                linewidth=2,
                marker='o',
                markersize=3,
                markevery=20)

    ax2.axhline(y=1.0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax2.set_xlabel('时间 (s)', fontsize=12)
    ax2.set_ylabel('输出响应', fontsize=12)
    ax2.set_title('阶跃响应详细视图 (0-5秒)', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='best', fontsize=10)
    ax2.set_xlim([0, 5])

    plt.tight_layout()
    plt.savefig('second_order_damping_response.png', dpi=300, bbox_inches='tight')
    print("\n图形已保存为: second_order_damping_response.png")

    plt.show()


def plot_phase_portraits(results):
    """绘制相平面图"""

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    for idx, res in enumerate(results):
        ax = axes[idx]

        # 获取位置和速度数据 (需要重新仿真获取速度状态)
        # 这里我们通过数值微分近似速度
        position = res["output"]
        velocity = np.gradient(position, res["times"])

        # 绘制相轨迹
        ax.plot(position, velocity, color=res["color"], linewidth=2)
        ax.plot(position[0], velocity[0], 'go', markersize=10, label='起点')
        ax.plot(position[-1], velocity[-1], 'ro', markersize=10, label='终点')

        ax.set_xlabel('位置', fontsize=10)
        ax.set_ylabel('速度', fontsize=10)
        ax.set_title(res["label"], fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=8)
        ax.axhline(y=0, color='black', linewidth=0.5)
        ax.axvline(x=0, color='black', linewidth=0.5)

    # 删除多余的子图
    if len(results) < 6:
        for idx in range(len(results), 6):
            fig.delaxes(axes[idx])

    plt.suptitle('二阶系统相平面图 - 不同阻尼比', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig('second_order_phase_portraits.png', dpi=300, bbox_inches='tight')
    print("相平面图已保存为: second_order_phase_portraits.png")

    plt.show()


def print_theory():
    """打印理论说明"""

    print("\n" + "=" * 60)
    print("二阶系统理论说明")
    print("=" * 60)
    print("""
二阶系统标准传递函数:
    H(s) = ω_n² / (s² + 2ζω_n·s + ω_n²)

其中:
    ω_n - 自然频率 (natural frequency)
    ζ   - 阻尼比 (damping ratio)

阻尼比分类:
    ζ < 1  : 欠阻尼 (Underdamped)
             - 有振荡和超调
             - 响应快但可能不稳定

    ζ = 1  : 临界阻尼 (Critically Damped)
             - 最快的无超调响应
             - 理想的平衡状态

    ζ > 1  : 过阻尼 (Overdamped)
             - 无超调和振荡
             - 响应慢但平稳

性能指标:
    - 超调量 (Overshoot): (峰值 - 稳态值) / 稳态值 × 100%
    - 上升时间 (Rise Time): 从10%到90%稳态值的时间
    - 调节时间 (Settling Time): 进入±2%误差带的时间
    - 峰值时间 (Peak Time): 达到第一个峰值的时间
    """)
    print("=" * 60)


if __name__ == "__main__":
    # 打印理论说明
    print_theory()

    # 运行仿真
    results, configs = simulate_damping_systems()

    # 绘制结果
    plot_results(results)

    # 绘制相平面图
    plot_phase_portraits(results)

    print("\n所有仿真和可视化完成!")
