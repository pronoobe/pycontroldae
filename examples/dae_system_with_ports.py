"""
含代数约束的N阶系统仿真示例
使用Port API和Module构建机电耦合系统

系统描述：
- 直流电机（电气子系统 + 机械子系统）
- 齿轮传动机构（代数约束）
- 负载惯量
- 总共6个状态 + 2个代数约束 = 8阶DAE系统
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import io
from pycontroldae.core import Module, CompositeModule, System, Simulator, DataProbe
from pycontroldae.blocks import Step
import matplotlib
try:
    matplotlib.use('TKAgg')
except:
    pass
plt.rcParams['font.sans-serif'] = ['SimHei', 'SimSun', 'Times New Roman']
plt.rcParams['axes.unicode_minus'] = True
plt.rcParams['font.size'] = 9.0
# Set UTF-8 encoding for output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class DCMotorElectric(Module):
    """
    直流电机电气子系统

    方程：
        L * di/dt = V - R*i - K_e*omega_m

    其中：
        i: 电枢电流 (A)
        V: 输入电压 (V)
        R: 电枢电阻 (Ohm)
        L: 电枢电感 (H)
        K_e: 反电动势常数 (V·s/rad)
        omega_m: 电机角速度 (rad/s)
    """

    def __init__(self, name, R=1.0, L=0.01, K_e=0.1):
        super().__init__(name)

        # 状态变量
        self.add_state("i", 0.0)  # 电枢电流

        # 参数
        self.add_param("R", R)  # 电阻
        self.add_param("L", L)  # 电感
        self.add_param("K_e", K_e)  # 反电动势常数

        # 输入变量（代数变量）
        self.add_state("V", 0.0)  # 输入电压（外部输入）
        self.add_state("omega_m", 0.0)  # 电机角速度（来自机械侧）

        # 输出变量（代数变量）
        self.add_state("i_out", 0.0)  # 电流输出给机械侧

        # 微分方程
        self.add_equation("D(i) ~ (V - R*i - K_e*omega_m) / L")

        # 代数约束（输出等于状态）
        self.add_equation("0 ~ i_out - i")

        # Port已经通过add_state自动创建，可以直接通过属性访问
        # self.voltage, self.omega_m, self.i_out 都已经可用


class DCMotorMechanical(Module):
    """
    直流电机机械子系统

    方程：
        J_m * domega_m/dt = T_m - b_m*omega_m - T_load
        T_m = K_t * i

    其中：
        omega_m: 电机角速度 (rad/s)
        J_m: 电机转动惯量 (kg·m²)
        b_m: 粘性摩擦系数 (N·m·s/rad)
        K_t: 转矩常数 (N·m/A)
        i: 电枢电流 (A)
        T_load: 负载转矩 (N·m)
    """

    def __init__(self, name, J_m=0.01, b_m=0.1, K_t=0.1):
        super().__init__(name)

        # 状态变量
        self.add_state("omega_m", 0.0)  # 电机角速度
        self.add_state("theta_m", 0.0)  # 电机角位置

        # 参数
        self.add_param("J_m", J_m)  # 转动惯量
        self.add_param("b_m", b_m)  # 粘性摩擦
        self.add_param("K_t", K_t)  # 转矩常数

        # 输入变量
        self.add_state("i", 0.0)  # 电流输入
        self.add_state("T_load", 0.0)  # 负载转矩

        # 输出变量（代数）
        self.add_state("omega_out", 0.0)
        self.add_state("theta_out", 0.0)

        # 电磁转矩
        self.add_state("T_m", 0.0)
        self.add_equation("0 ~ T_m - K_t * i")

        # 微分方程
        self.add_equation("D(omega_m) ~ (T_m - b_m*omega_m - T_load) / J_m")
        self.add_equation("D(theta_m) ~ omega_m")

        # 代数约束（输出）
        self.add_equation("0 ~ omega_out - omega_m")
        self.add_equation("0 ~ theta_out - theta_m")

        # Port已通过add_state自动创建


class GearBox(Module):
    """
    齿轮传动机构（纯代数约束）

    方程：
        omega_load = omega_motor / N  （速度关系）
        T_motor = T_load / N  （转矩关系）
        theta_load = theta_motor / N  （位置关系）

    其中：
        N: 齿轮比
    """

    def __init__(self, name, gear_ratio=10.0):
        super().__init__(name)

        # 参数
        self.add_param("N", gear_ratio)  # 齿轮比

        # 输入侧（电机侧）
        self.add_state("omega_motor", 0.0)
        self.add_state("theta_motor", 0.0)
        self.add_state("T_load_ref", 0.0)  # 反映到电机侧的转矩

        # 输出侧（负载侧）
        self.add_state("omega_load", 0.0)
        self.add_state("theta_load", 0.0)
        self.add_state("T_motor_req", 0.0)  # 电机需要的转矩

        # 代数约束：速度关系
        self.add_equation("0 ~ omega_load * N - omega_motor")

        # 代数约束：位置关系
        self.add_equation("0 ~ theta_load * N - theta_motor")

        # 代数约束：转矩关系（能量守恒）
        self.add_equation("0 ~ T_motor_req * N - T_load_ref")

        # Port已通过add_state自动创建


class LoadInertia(Module):
    """
    负载惯量

    方程：
        J_l * domega_l/dt = T_gear - b_l*omega_l - T_ext
    """

    def __init__(self, name, J_l=0.1, b_l=0.5):
        super().__init__(name)

        # 状态变量
        self.add_state("omega_l", 0.0)  # 负载角速度
        self.add_state("theta_l", 0.0)  # 负载角位置

        # 参数
        self.add_param("J_l", J_l)  # 负载惯量
        self.add_param("b_l", b_l)  # 负载摩擦

        # 输入
        self.add_state("T_gear", 0.0)  # 来自齿轮的转矩
        self.add_state("T_ext", 0.0)  # 外部负载转矩

        # 输出（代数）
        self.add_state("T_reaction", 0.0)  # 反作用转矩

        # 微分方程
        self.add_equation("D(omega_l) ~ (T_gear - b_l*omega_l - T_ext) / J_l")
        self.add_equation("D(theta_l) ~ omega_l")

        # 代数约束：反作用转矩等于作用转矩
        self.add_equation("0 ~ T_reaction - T_gear")

        # Port已通过add_state自动创建


class ConstantTorque(Module):
    """常值负载转矩"""

    def __init__(self, name, torque=0.0):
        super().__init__(name)

        self.add_param("T_const", torque)
        self.add_state("torque", 0.0)

        # 代数方程
        self.add_equation("0 ~ torque - T_const")

        # Port已通过add_state自动创建


def create_complete_drive_system():
    """创建完整的机电驱动系统"""

    print("=" * 70)
    print("构建含代数约束的机电耦合系统")
    print("=" * 70)

    # 创建系统
    system = System("electromechanical_drive")

    # 1. 电压源
    print("\n[1/6] 创建电压源...")
    voltage_source = Step(name="voltage", amplitude=24.0, step_time=0.0)
    voltage_source.set_output("signal")

    # 2. 电机电气侧
    print("[2/6] 创建电机电气子系统...")
    motor_electric = DCMotorElectric(
        name="motor_elec",
        R=1.0,      # 1 Ohm
        L=0.01,     # 10 mH
        K_e=0.1     # 反电动势常数
    )

    # 3. 电机机械侧
    print("[3/6] 创建电机机械子系统...")
    motor_mechanical = DCMotorMechanical(
        name="motor_mech",
        J_m=0.01,   # 电机惯量
        b_m=0.1,    # 电机摩擦
        K_t=0.1     # 转矩常数
    )

    # 4. 齿轮箱
    print("[4/6] 创建齿轮传动机构（代数约束）...")
    gearbox = GearBox(
        name="gear",
        gear_ratio=10.0  # 10:1减速比
    )

    # 5. 负载
    print("[5/6] 创建负载惯量...")
    load = LoadInertia(
        name="load",
        J_l=0.1,    # 负载惯量
        b_l=0.5     # 负载摩擦
    )

    # 6. 外部负载转矩
    print("[6/6] 创建外部负载...")
    external_torque = ConstantTorque(name="ext_load", torque=0.5)

    # 添加所有模块
    print("\n将所有模块添加到系统...")
    system.add_module(voltage_source)
    system.add_module(motor_electric)
    system.add_module(motor_mechanical)
    system.add_module(gearbox)
    system.add_module(load)
    system.add_module(external_torque)

    # 使用Port API连接（推荐方式）
    print("\n使用Port API建立连接...")
    print("  ├─ 电压源 -> 电机电气侧")
    system.connect(voltage_source.signal >> motor_electric.V)

    print("  ├─ 电机电气侧 <-> 电机机械侧（电流）")
    system.connect(motor_electric.i_out >> motor_mechanical.i)

    print("  ├─ 电机机械侧 -> 电机电气侧（速度反馈）")
    system.connect(motor_mechanical.omega_out >> motor_electric.omega_m)

    print("  ├─ 电机机械侧 -> 齿轮箱（速度和位置）")
    system.connect(motor_mechanical.omega_out >> gearbox.omega_motor)
    system.connect(motor_mechanical.theta_out >> gearbox.theta_motor)

    print("  ├─ 齿轮箱 -> 电机机械侧（负载转矩）")
    system.connect(gearbox.T_motor_req >> motor_mechanical.T_load)

    print("  ├─ 齿轮箱 -> 负载（转矩）")
    system.connect(gearbox.T_motor_req >> load.T_gear)

    print("  ├─ 负载 -> 齿轮箱（反作用转矩）")
    system.connect(load.T_reaction >> gearbox.T_load_ref)

    print("  └─ 外部负载 -> 负载")
    system.connect(external_torque.torque >> load.T_ext)

    print("\n" + "=" * 70)
    print("系统连接完成！")
    print("=" * 70)

    return system


def run_simulation():
    """运行仿真"""

    # 创建系统
    system = create_complete_drive_system()

    # 编译系统（自动调用structural_simplify简化DAE）
    print("\n编译系统（包含DAE简化）...")
    print("注意：系统包含代数约束，structural_simplify会自动处理...")
    system.compile()
    print("✓ 编译完成！DAE系统已简化为ODE")

    # 配置数据探针
    probes = {
        "电气": DataProbe(
            variables=[
                "motor_elec.i",
                "voltage.signal"
            ],
            names=["电流(A)", "电压(V)"],
            description="电气参数"
        ),
        "电机": DataProbe(
            variables=[
                "motor_mech.omega_m",
                "motor_mech.theta_m",
                "motor_mech.T_m"
            ],
            names=["电机转速(rad/s)", "电机位置(rad)", "电机转矩(Nm)"],
            description="电机参数"
        ),
        "负载": DataProbe(
            variables=[
                "load.omega_l",
                "load.theta_l"
            ],
            names=["负载转速(rad/s)", "负载位置(rad)"],
            description="负载参数"
        )
    }

    # 仿真参数
    t_span = (0.0, 5.0)
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
        solver="Rodas5",  # DAE求解器
        probes=probes
    )

    print("\n✓ 仿真完成！")

    # 打印统计信息
    result.print_summary()

    return result, probes


def plot_results(result, probes):
    """绘制结果"""

    print("\n生成可视化图表...")

    # 获取探针数据
    df_electric = result.get_probe_dataframe("电气")
    df_motor = result.get_probe_dataframe("电机")
    df_load = result.get_probe_dataframe("负载")

    # 创建图形
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))

    # 1. 电压和电流
    ax = axes[0, 0]
    ax.plot(df_electric['time'], df_electric['电压(V)'], 'b-', linewidth=2, label='输入电压')
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('电压 (V)', color='b')
    ax.tick_params(axis='y', labelcolor='b')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')

    ax2 = ax.twinx()
    ax2.plot(df_electric['time'], df_electric['电流(A)'], 'r-', linewidth=2, label='电枢电流')
    ax2.set_ylabel('电流 (A)', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.legend(loc='upper right')
    ax.set_title('电气参数', fontweight='bold', fontsize=12)

    # 2. 电机转速
    ax = axes[0, 1]
    ax.plot(df_motor['time'], df_motor['电机转速(rad/s)'], 'g-', linewidth=2, label='电机转速')
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('角速度 (rad/s)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title('电机角速度', fontweight='bold', fontsize=12)

    # 3. 电机位置
    ax = axes[1, 0]
    ax.plot(df_motor['time'], df_motor['电机位置(rad)'], 'b-', linewidth=2, label='电机位置')
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('角位置 (rad)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title('电机角位置', fontweight='bold', fontsize=12)

    # 4. 电机转矩
    ax = axes[1, 1]
    ax.plot(df_motor['time'], df_motor['电机转矩(Nm)'], 'r-', linewidth=2, label='电磁转矩')
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('转矩 (N·m)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title('电机电磁转矩', fontweight='bold', fontsize=12)

    # 5. 负载转速
    ax = axes[2, 0]
    ax.plot(df_load['time'], df_load['负载转速(rad/s)'], 'purple', linewidth=2, label='负载转速')
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('角速度 (rad/s)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title('负载角速度（经齿轮减速）', fontweight='bold', fontsize=12)

    # 6. 负载位置
    ax = axes[2, 1]
    ax.plot(df_load['time'], df_load['负载位置(rad)'], 'orange', linewidth=2, label='负载位置')
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('角位置 (rad)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_title('负载角位置', fontweight='bold', fontsize=12)

    plt.suptitle('机电耦合系统仿真结果 - 含代数约束的DAE系统',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()

    # 保存图形
    filename = 'dae_electromechanical_system.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"✓ 图形已保存: {filename}")

    plt.show()

    # 保存数据
    result.to_csv('dae_system_results.csv', include_probes=True)
    print(f"✓ 数据已保存: dae_system_results.csv")


def print_system_info():
    """打印系统信息"""

    print("\n" + "=" * 70)
    print("系统信息")
    print("=" * 70)
    print("""
本示例展示了一个含代数约束的6阶DAE系统：

【系统结构】
  电压源 -> [电机电气侧] <-电流-> [电机机械侧] -> [齿轮箱] -> [负载]
                ↑                      ↓
                └──────速度反馈─────────┘

【微分方程】(6个)
  1. 电枢电流:      L·di/dt = V - R·i - Ke·ωm
  2. 电机角速度:    Jm·dωm/dt = Tm - bm·ωm - Tload
  3. 电机角位置:    dθm/dt = ωm
  4. 负载角速度:    Jl·dωl/dt = Tgear - bl·ωl - Text
  5. 负载角位置:    dθl/dt = ωl

【代数约束】(多个)
  1. 电磁转矩:      Tm = Kt·i
  2. 齿轮速度关系:   ωl = ωm/N
  3. 齿轮位置关系:   θl = θm/N
  4. 齿轮转矩关系:   Tm_req = Tl_ref/N
  5. 端口连接约束:   多个端口间的代数连接

【系统特点】
  ✓ 使用Module类自定义组件
  ✓ 使用Port API进行模块化连接
  ✓ 包含真实的代数约束（齿轮传动、电磁耦合）
  ✓ structural_simplify自动简化DAE为ODE
  ✓ 展示机电耦合的完整动态特性

【参数设置】
  电机电阻:   R = 1.0 Ω
  电机电感:   L = 0.01 H
  电机惯量:   Jm = 0.01 kg·m²
  负载惯量:   Jl = 0.1 kg·m²
  齿轮比:     N = 10:1
  输入电压:   V = 24 V
  外部负载:   Text = 0.5 N·m
""")
    print("=" * 70)


if __name__ == "__main__":
    # 打印系统信息
    print_system_info()

    # 运行仿真
    result, probes = run_simulation()

    # 绘制结果
    plot_results(result, probes)

    print("\n" + "=" * 70)
    print("仿真完成！")
    print("=" * 70)
