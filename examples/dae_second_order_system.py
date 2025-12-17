"""
含代数约束的二阶系统仿真示例
双质量弹簧阻尼系统 - 使用Port API和Module

系统描述：
- 两个质量块（m1, m2）通过弹簧和阻尼器连接
- 弹簧力作为代数约束变量
- 外力作用在质量块1上
- 总共4个微分状态 + 2个代数约束 = 6阶DAE系统
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import io
from pycontroldae.core import Module, System, Simulator
from pycontroldae.blocks import Step

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class Mass(Module):
    """
    质量块模块

    微分方程：
        m * dv/dt = F_external + F_spring - F_damping
        dx/dt = v

    其中：
        x: 位置
        v: 速度
        m: 质量
        F_external: 外力
        F_spring: 弹簧力（来自连接）
        F_damping: 阻尼力
    """

    def __init__(self, name, mass=1.0, damping=0.1):
        super().__init__(name)

        # 状态变量
        self.add_state("x", 0.0)     # 位置
        self.add_state("v", 0.0)     # 速度

        # 参数
        self.add_param("m", mass)    # 质量
        self.add_param("b", damping) # 阻尼系数

        # 输入力（代数变量）
        self.add_state("F_ext", 0.0)    # 外部力
        self.add_state("F_spring", 0.0) # 弹簧力

        # 输出（代数约束）
        self.add_state("x_out", 0.0)    # 位置输出
        self.add_state("v_out", 0.0)    # 速度输出

        # 微分方程
        self.add_equation("D(v) ~ (F_ext + F_spring - b*v) / m")
        self.add_equation("D(x) ~ v")

        # 代数约束（输出等于状态）
        self.add_equation("0 ~ x_out - x")
        self.add_equation("0 ~ v_out - v")


class Spring(Module):
    """
    弹簧模块（纯代数约束）

    代数方程：
        F = -k * (x2 - x1)  （胡克定律）
        F1 = -F             （作用力）
        F2 = F              （反作用力）

    其中：
        k: 弹簧刚度
        x1, x2: 两端位置
        F: 弹簧内力
        F1, F2: 对两个质量块的作用力
    """

    def __init__(self, name, stiffness=10.0):
        super().__init__(name)

        # 参数
        self.add_param("k", stiffness)

        # 输入（位置）
        self.add_state("x1", 0.0)  # 左端位置
        self.add_state("x2", 0.0)  # 右端位置

        # 输出（力）
        self.add_state("F1", 0.0)  # 对质量1的力
        self.add_state("F2", 0.0)  # 对质量2的力

        # 内部代数变量
        self.add_state("F", 0.0)   # 弹簧内力

        # 代数约束
        self.add_equation("0 ~ F + k * (x2 - x1)")  # 弹簧力
        self.add_equation("0 ~ F1 + F")              # 作用力
        self.add_equation("0 ~ F2 - F")              # 反作用力


def create_double_mass_spring_system():
    """创建双质量弹簧系统"""

    print("=" * 70)
    print("构建含代数约束的二阶系统 - 双质量弹簧阻尼器")
    print("=" * 70)
    print("\n系统结构:")
    print("  外力 -> [质量1] --弹簧-- [质量2] --固定")
    print("\n系统参数:")
    print("  质量1: m1 = 1.0 kg,  阻尼 b1 = 0.2 N·s/m")
    print("  质量2: m2 = 2.0 kg,  阻尼 b2 = 0.3 N·s/m")
    print("  弹簧刚度: k = 20.0 N/m")
    print("  外力: F = 10.0 N (阶跃输入)")
    print("\n微分状态变量: 4个")
    print("  - m1.x, m1.v (质量1的位置和速度)")
    print("  - m2.x, m2.v (质量2的位置和速度)")
    print("\n代数约束: 多个")
    print("  - 弹簧力: F = -k*(x2-x1)")
    print("  - 输出连接约束")
    print("=" * 70)

    # 创建系统
    system = System("double_mass_spring")

    # 1. 外力输入
    print("\n[1/4] 创建外力源...")
    force_input = Step(name="force", amplitude=10.0, step_time=0.0)
    force_input.set_output("signal")

    # 2. 质量块1
    print("[2/4] 创建质量块1...")
    mass1 = Mass(name="m1", mass=1.0, damping=0.2)

    # 3. 质量块2
    print("[3/4] 创建质量块2...")
    mass2 = Mass(name="m2", mass=2.0, damping=0.3)

    # 4. 弹簧
    print("[4/4] 创建弹簧连接...")
    spring = Spring(name="spring", stiffness=20.0)

    # 添加模块
    system.add_module(force_input)
    system.add_module(mass1)
    system.add_module(mass2)
    system.add_module(spring)

    # 使用Port API连接
    print("\n建立连接:")
    print("  ├─ 外力 -> 质量1")
    system.connect(force_input.signal >> mass1.F_ext)

    print("  ├─ 质量1位置 -> 弹簧左端")
    system.connect(mass1.x_out >> spring.x1)

    print("  ├─ 质量2位置 -> 弹簧右端")
    system.connect(mass2.x_out >> spring.x2)

    print("  ├─ 弹簧力1 -> 质量1")
    system.connect(spring.F1 >> mass1.F_spring)

    print("  ├─ 弹簧力2 -> 质量2")
    system.connect(spring.F2 >> mass2.F_spring)

    # 质量2没有外力，设为0
    print("  └─ 质量2外力设为0")
    system.connect("0.0 ~ m2.F_ext")  # 使用字符串连接设置常数

    print("\n" + "=" * 70)
    print("系统连接完成！")
    print("=" * 70)

    return system


def run_simulation():
    """运行仿真"""

    # 创建系统
    system = create_double_mass_spring_system()

    # 编译系统
    print("\n编译系统（包含DAE简化）...")
    print("注意：系统包含代数约束，structural_simplify会自动处理...")
    system.compile()
    print("✓ 编译完成！DAE系统已简化为ODE")

    # 仿真参数
    t_span = (0.0, 10.0)
    dt = 0.01

    print(f"\n开始仿真...")
    print(f"  时间范围: {t_span[0]}s - {t_span[1]}s")
    print(f"  采样间隔: {dt}s")
    print(f"  求解器: Rodas5 (适用于DAE系统)")

    # 创建仿真器并运行
    simulator = Simulator(system)
    result = simulator.run(
        t_span=t_span,
        dt=dt,
        solver="Rodas5"
    )

    print("\n✓ 仿真完成！")

    # 打印统计信息
    result.print_summary()

    return result


def plot_results(result):
    """绘制结果"""

    print("\n生成可视化图表...")

    times = result.times

    # 获取状态数据
    try:
        m1_x = result.get_state("m1.x")
        m1_v = result.get_state("m1.v")
        m2_x = result.get_state("m2.x")
        m2_v = result.get_state("m2.v")
        force = result.get_state("force.signal")

        # 创建图形
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. 位置对比
        ax = axes[0, 0]
        ax.plot(times, m1_x, 'b-', linewidth=2, label='质量1位置')
        ax.plot(times, m2_x, 'r-', linewidth=2, label='质量2位置')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('位置 (m)')
        ax.set_title('两个质量块的位置', fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 2. 速度对比
        ax = axes[0, 1]
        ax.plot(times, m1_v, 'b-', linewidth=2, label='质量1速度')
        ax.plot(times, m2_v, 'r-', linewidth=2, label='质量2速度')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('速度 (m/s)')
        ax.set_title('两个质量块的速度', fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 3. 相对位移（弹簧伸长）
        ax = axes[1, 0]
        spring_displacement = m2_x - m1_x
        ax.plot(times, spring_displacement, 'g-', linewidth=2, label='弹簧伸长')
        ax.axhline(y=0, color='k', linestyle='--', linewidth=1, alpha=0.5)
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('相对位移 (m)')
        ax.set_title('弹簧伸长量 (x2 - x1)', fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 4. 相平面图
        ax = axes[1, 1]
        ax.plot(m1_x, m1_v, 'b-', linewidth=2, label='质量1', alpha=0.7)
        ax.plot(m2_x, m2_v, 'r-', linewidth=2, label='质量2', alpha=0.7)
        ax.plot(m1_x[0], m1_v[0], 'go', markersize=10, label='起点')
        ax.plot(m1_x[-1], m1_v[-1], 'ro', markersize=10, label='终点')
        ax.set_xlabel('位置 (m)')
        ax.set_ylabel('速度 (m/s)')
        ax.set_title('相平面图', fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.suptitle('双质量弹簧阻尼系统 - 含代数约束的DAE系统',
                     fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()

        # 保存图形
        filename = 'dae_double_mass_spring.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"✓ 图形已保存: {filename}")

        plt.show()

        # 分析结果
        print("\n" + "=" * 70)
        print("结果分析:")
        print("=" * 70)
        print(f"质量1最终位置: {m1_x[-1]:.4f} m")
        print(f"质量2最终位置: {m2_x[-1]:.4f} m")
        print(f"弹簧最终伸长: {spring_displacement[-1]:.4f} m")
        print(f"质量1最大位移: {np.max(m1_x):.4f} m")
        print(f"质量2最大位移: {np.max(m2_x):.4f} m")
        print(f"质量1最大速度: {np.max(np.abs(m1_v)):.4f} m/s")
        print(f"质量2最大速度: {np.max(np.abs(m2_v)):.4f} m/s")

        # 验证能量守恒（忽略阻尼损耗）
        # E = 0.5*m1*v1^2 + 0.5*m2*v2^2 + 0.5*k*(x2-x1)^2
        m1_val = 1.0
        m2_val = 2.0
        k_val = 20.0

        KE1 = 0.5 * m1_val * m1_v**2
        KE2 = 0.5 * m2_val * m2_v**2
        PE = 0.5 * k_val * spring_displacement**2
        total_energy = KE1 + KE2 + PE

        print(f"\n初始能量: {total_energy[0]:.4f} J")
        print(f"最终能量: {total_energy[-1]:.4f} J (由于阻尼而减少)")

    except Exception as e:
        print(f"绘图时出错: {e}")
        print(f"可用状态: {result.state_names}")

    # 保存数据
    result.to_csv('dae_double_mass_spring.csv')
    print(f"✓ 数据已保存: dae_double_mass_spring.csv")


def print_theory():
    """打印理论说明"""

    print("\n" + "=" * 70)
    print("理论说明 - 含代数约束的二阶系统")
    print("=" * 70)
    print("""
【系统模型】
双质量弹簧阻尼系统：

    F_ext -> [m1]---spring(k)---[m2]---固定端
             (b1)              (b2)

【微分方程】（4个二阶系统状态）
  质量1:
    dx1/dt = v1
    m1 * dv1/dt = F_ext + F_spring - b1*v1

  质量2:
    dx2/dt = v2
    m2 * dv2/dt = F_spring' - b2*v2

【代数约束】
  弹簧力（胡克定律）:
    F_spring = -k * (x2 - x1)
    F_spring' = -F_spring  （牛顿第三定律）

  端口连接约束:
    输出位置 = 内部位置
    输出速度 = 内部速度

【系统特点】
  ✓ 标准的二阶系统（质量-弹簧-阻尼）
  ✓ 包含真实的代数约束（弹簧力）
  ✓ 使用Port API进行模块化连接
  ✓ structural_simplify自动消除代数变量
  ✓ DAE系统自动简化为ODE求解

【物理意义】
  - 弹簧力是代数变量，瞬时满足胡克定律
  - 质量块的运动由牛顿第二定律决定
  - 系统最终达到平衡状态
  - 阻尼导致能量逐渐耗散

【DAE vs ODE】
  原始系统: 4个微分方程 + 多个代数约束 (DAE)
  简化后: 4个微分方程 (ODE)

  structural_simplify自动:
    1. 消除代数变量
    2. 替换约束方程
    3. 生成最小ODE系统
""")
    print("=" * 70)


if __name__ == "__main__":
    # 打印理论说明
    print_theory()

    # 运行仿真
    result = run_simulation()

    # 绘制结果
    plot_results(result)

    print("\n" + "=" * 70)
    print("仿真完成！")
    print("=" * 70)
