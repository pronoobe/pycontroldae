"""
单机无限大系统短路故障仿真（完整版）
Single Machine Infinite Bus (SMIB) System with Short Circuit Fault Simulation (Complete Version)

包含：
1. 同步发电机（包含励磁系统）
2. 自动电压调节器 (AVR)
3. 短路故障仿真
4. 正确的稳态初始化
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib.pyplot as plt
from pycontroldae.core import Module, System, Simulator, DataProbe, at_time

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

print("=" * 80)
print("单机无限大系统短路故障仿真（完整版）")
print("SMIB Short Circuit Fault Simulation (Complete with AVR)")
print("=" * 80)
print()

# ==============================================================================
# Part 1: 同步发电机建模（简化三阶模型）
# ==============================================================================
print("PART 1: 创建同步发电机模型（三阶模型 + 励磁）")
print("-" * 80)

class SynchronousGenerator(Module):
    """
    同步发电机三阶模型

    状态变量:
    - delta: 功角 (rad)
    - omega: 角速度偏差 (rad/s，相对于同步速度)
    - E_q_prime: 交轴暂态电势 (p.u.)

    输入:
    - V_t: 机端电压幅值 (p.u.)
    - E_fd: 励磁电压 (p.u.)
    - P_m: 机械功率 (p.u.)
    """

    def __init__(self, name: str,
                 H: float = 3.5,           # 惯性时间常数 (s)
                 damping: float = 5.0,     # 阻尼系数
                 X_d: float = 1.6,         # 直轴同步电抗
                 X_q: float = 1.55,        # 交轴同步电抗
                 X_d_prime: float = 0.32,  # 直轴暂态电抗
                 T_d0_prime: float = 6.0,  # 直轴开路时间常数 (s)
                 X_e: float = 0.4,         # 外部电抗（线路）
                 V_inf: float = 1.0):      # 无限大母线电压

        super().__init__(name)

        # 状态变量
        self.add_state("delta", 0.6)       # 功角 (rad) ~34度
        self.add_state("omega", 0.0)       # 角速度偏差
        self.add_state("E_q_prime", 1.2)   # 交轴暂态电势

        # 输入
        self.add_input("V_t", 1.0)         # 机端电压（由AVR测量）
        self.add_input("E_fd", 2.0)        # 励磁电压（来自AVR）
        self.add_input("P_m", 0.9)         # 机械功率

        # 输出
        self.add_output("P_e", 0.9)        # 电磁功率
        self.add_output("delta_deg", 30.0) # 功角（度）
        self.add_output("V_terminal", 1.0) # 机端电压（反馈给AVR）

        # 参数
        self.add_param("H", H)
        self.add_param("damping", damping)
        self.add_param("X_d", X_d)
        self.add_param("X_q", X_q)
        self.add_param("X_d_prime", X_d_prime)
        self.add_param("T_d0_prime", T_d0_prime)
        self.add_param("X_e", X_e)
        self.add_param("V_inf", V_inf)
        self.add_param("omega_s", 314.159)  # 同步角速度
        self.add_param("tau", 0.001)        # 快速跟踪

        # 摇摆方程
        self.add_equation("D(delta) ~ omega")
        self.add_equation(
            "D(omega) ~ (P_m - P_e - damping * omega) / (2 * H)"
        )

        # 暂态电势方程
        # E_q' 动态
        self.add_equation(
            "D(E_q_prime) ~ (E_fd - E_q_prime - (X_d - X_d_prime) * (E_q_prime - V_inf * cos(delta)) / (X_d_prime + X_e)) / T_d0_prime"
        )

        # 电磁功率（简化公式）
        # P_e = E_q' * V_inf * sin(delta) / (X_d' + X_e)
        self.add_equation(
            "D(P_e) ~ (E_q_prime * V_inf * sin(delta) / (X_d_prime + X_e) - P_e) / tau"
        )

        # 功角（度）
        self.add_equation(
            "D(delta_deg) ~ (delta * 180 / 3.14159265 - delta_deg) / tau"
        )

        # 机端电压（简化）
        # V_t ≈ sqrt[(E_q' - X_e * I_q)^2 + (X_e * I_d)^2]
        # 更简单：V_t ≈ E_q' - X_e * P_e / E_q'
        self.add_equation(
            "D(V_terminal) ~ (V_t - V_terminal) / tau"
        )

        self.set_input("P_m")
        self.set_output("P_e")


print("[1.1] 创建同步发电机模型...")
generator = SynchronousGenerator(
    name="gen",
    H=3.5,
    damping=5.0,
    X_d=1.6,
    X_q=1.55,
    X_d_prime=0.32,
    T_d0_prime=6.0,
    X_e=0.4,
    V_inf=1.0
)
generator.build()
print(f"[OK] {generator}")
print()

# ==============================================================================
# Part 2: 自动电压调节器 (AVR)
# ==============================================================================
print("PART 2: 创建自动电压调节器 (AVR)")
print("-" * 80)

class AVR(Module):
    """
    简化的自动电压调节器

    输入:
    - V_t: 实际机端电压
    - V_ref: 参考电压

    输出:
    - E_fd: 励磁电压
    """

    def __init__(self, name: str,
                 K_a: float = 200.0,      # AVR增益
                 T_a: float = 0.05,       # AVR时间常数 (s)
                 E_fd_max: float = 5.0,   # 励磁电压上限
                 E_fd_min: float = 0.0):  # 励磁电压下限

        super().__init__(name)

        # 状态
        self.add_state("E_fd", 2.0)       # 励磁电压
        self.add_state("V_error", 0.0)    # 电压误差

        # 输入
        self.add_input("V_t", 1.0)        # 实际机端电压
        self.add_input("V_ref", 1.0)      # 参考电压

        # 输出
        self.add_output("E_fd_out", 2.0)  # 励磁电压输出

        # 参数
        self.add_param("K_a", K_a)
        self.add_param("T_a", T_a)
        self.add_param("E_fd_max", E_fd_max)
        self.add_param("E_fd_min", E_fd_min)
        self.add_param("tau", 0.001)

        # 电压误差
        self.add_equation("D(V_error) ~ (V_ref - V_t - V_error) / tau")

        # AVR动态（带限幅）
        # E_fd = K_a * V_error (限制在 [E_fd_min, E_fd_max])
        self.add_equation(
            "D(E_fd) ~ ((E_fd_min + (E_fd_max - E_fd_min) * (tanh(K_a * V_error / E_fd_max) + 1) / 2) - E_fd) / T_a"
        )

        # 输出跟踪
        self.add_equation("D(E_fd_out) ~ (E_fd - E_fd_out) / tau")

        self.set_input("V_t")
        self.set_output("E_fd_out")


print("[2.1] 创建AVR模型...")
avr = AVR(
    name="avr",
    K_a=200.0,
    T_a=0.05,
    E_fd_max=5.0,
    E_fd_min=0.0
)
avr.build()
print(f"[OK] {avr}")
print()

# ==============================================================================
# Part 3: 参考电压和机械功率
# ==============================================================================
print("PART 3: 创建参考信号")
print("-" * 80)

# 参考电压
v_ref = Module("v_ref")
v_ref.add_output("V_ref", 1.0)
v_ref.add_param("V_ref_set", 1.0)
v_ref.add_equation("D(V_ref) ~ (V_ref_set - V_ref) / 1e-6")
v_ref.set_output("V_ref")
v_ref.build()
print(f"[3.1] 参考电压: {v_ref}")

# 机械功率
p_mech = Module("turbine")
p_mech.add_output("P_m", 0.9)
p_mech.add_param("P_m_set", 0.9)
p_mech.add_equation("D(P_m) ~ (P_m_set - P_m) / 1e-6")
p_mech.set_output("P_m")
p_mech.build()
print(f"[3.2] 机械功率: {p_mech}")
print()

# ==============================================================================
# Part 4: 故障模块（改变机端电压）
# ==============================================================================
print("PART 4: 创建故障模块")
print("-" * 80)

# 故障通过降低机端电压来模拟
fault_module = Module("fault")
fault_module.add_output("V_t_fault", 1.0)  # 故障时的电压
fault_module.add_param("V_fault_factor", 1.0)  # 电压系数（1.0=正常，0.2=严重故障）
fault_module.add_param("V_base", 1.0)
fault_module.add_equation(
    "D(V_t_fault) ~ (V_base * V_fault_factor - V_t_fault) / 0.01"
)
fault_module.set_output("V_t_fault")
fault_module.build()
print(f"[4.1] 故障模块: {fault_module}")
print()

# ==============================================================================
# Part 5: 使用 Port API 组装系统
# ==============================================================================
print("PART 5: 使用 Port API 组装系统")
print("-" * 80)

system = System("smib_avr")

modules = [generator, avr, v_ref, p_mech, fault_module]
for mod in modules:
    system.add_module(mod)

print(f"[5.1] 添加了 {len(system.modules)} 个模块")
print("\n[5.2] 定义连接（Port API）：")

# 机械功率 -> 发电机
system.connect(p_mech.P_m >> generator.P_m)
print("    [OK] turbine.P_m >> gen.P_m")

# AVR -> 发电机
system.connect(avr.E_fd_out >> generator.E_fd)
print("    [OK] avr.E_fd_out >> gen.E_fd")

# 发电机 -> AVR（电压反馈）
system.connect(generator.V_terminal >> avr.V_t)
print("    [OK] gen.V_terminal >> avr.V_t")

# 参考电压 -> AVR
system.connect(v_ref.V_ref >> avr.V_ref)
print("    [OK] v_ref.V_ref >> avr.V_ref")

# 故障电压 -> 发电机
system.connect(fault_module.V_t_fault >> generator.V_t)
print("    [OK] fault.V_t_fault >> gen.V_t")

print(f"\n[5.3] 总共 {len(system.connections)} 个连接")
print()

# ==============================================================================
# Part 6: 定义短路故障事件
# ==============================================================================
print("PART 6: 定义短路故障事件")
print("-" * 80)

# 故障发生：t = 1.0s，电压降低到20%
def fault_occurrence(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] 三相短路故障！V_t -> 0.2 p.u.")
    return {"fault.V_fault_factor": 0.2}

# 故障切除：t = 1.15s，电压恢复
def fault_clearance(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] 故障切除！V_t -> 1.0 p.u.")
    return {"fault.V_fault_factor": 1.0}

system.add_event(at_time(1.0, fault_occurrence))
system.add_event(at_time(1.15, fault_clearance))

print("[6.1] 添加了 2 个事件:")
print("      - t=1.0s: 短路故障 (V_t -> 0.2 p.u.)")
print("      - t=1.15s: 故障切除 (V_t -> 1.0 p.u.)")
print()

# ==============================================================================
# Part 7: 配置数据探测器
# ==============================================================================
print("PART 7: 配置数据探测器")
print("-" * 80)

probes = {
    "generator": DataProbe(
        variables=[
            str(generator.delta_deg),
            str(generator.omega),
            str(generator.P_e)
        ],
        names=["Power_Angle_deg", "Speed_Deviation_rad_s", "Electrical_Power_pu"],
        description="Generator dynamics"
    ),
    "excitation": DataProbe(
        variables=[
            str(generator.V_terminal),
            str(avr.E_fd_out)
        ],
        names=["Terminal_Voltage_pu", "Field_Voltage_pu"],
        description="Excitation system"
    )
}

print(f"[7.1] 配置了 {len(probes)} 个探测器")
print()

# ==============================================================================
# Part 8: 编译和仿真
# ==============================================================================
print("PART 8: 编译系统并仿真")
print("-" * 80)

print("[8.1] 编译系统...")
try:
    system.compile()
    print("[OK] 系统编译成功")
except Exception as e:
    print(f"[ERROR] 编译失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[8.2] 运行仿真 (0-5s, dt=0.005s)...")

simulator = Simulator(system)

try:
    result = simulator.run(
        t_span=(0.0, 5.0),
        dt=0.005,
        solver="Rodas5",
        probes=probes
    )
    print(f"[OK] 仿真完成: {result}")
    print()
except Exception as e:
    print(f"[ERROR] 仿真失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Part 9: 导出数据
# ==============================================================================
print("PART 9: 导出数据")
print("-" * 80)

csv_file = "smib_avr_fault.csv"
result.to_csv(csv_file, include_probes=True)
print(f"[9.1] 数据导出: {csv_file}")

print("\n[9.2] 仿真摘要:")
result.print_summary()
print()

# ==============================================================================
# Part 10: 可视化
# ==============================================================================
print("PART 10: 绘制结果")
print("-" * 80)

gen_df = result.get_probe_dataframe("generator")
exc_df = result.get_probe_dataframe("excitation")

fig, axes = plt.subplots(4, 1, figsize=(12, 10))
fig.suptitle('单机无限大系统短路故障仿真（含AVR）\nSMIB Fault Simulation with AVR',
             fontsize=14, fontweight='bold')

# 功角
axes[0].plot(gen_df['time'], gen_df['Power_Angle_deg'], 'b-', linewidth=2)
axes[0].axvline(x=1.0, color='r', linestyle='--', alpha=0.7, label='故障')
axes[0].axvline(x=1.15, color='g', linestyle='--', alpha=0.7, label='切除')
axes[0].set_ylabel('功角 (度)', fontsize=11)
axes[0].set_title('(a) 发电机功角', fontsize=11, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].legend(loc='best')

# 角速度
axes[1].plot(gen_df['time'], gen_df['Speed_Deviation_rad_s'], 'r-', linewidth=2)
axes[1].axvline(x=1.0, color='r', linestyle='--', alpha=0.7)
axes[1].axvline(x=1.15, color='g', linestyle='--', alpha=0.7)
axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
axes[1].set_ylabel('角速度偏差 (rad/s)', fontsize=11)
axes[1].set_title('(b) 发电机角速度偏差', fontsize=11, fontweight='bold')
axes[1].grid(True, alpha=0.3)

# 功率
axes[2].plot(gen_df['time'], gen_df['Electrical_Power_pu'], 'g-', linewidth=2, label='电磁功率')
axes[2].axhline(y=0.9, color='b', linestyle='--', alpha=0.7, label='机械功率')
axes[2].axvline(x=1.0, color='r', linestyle='--', alpha=0.7)
axes[2].axvline(x=1.15, color='g', linestyle='--', alpha=0.7)
axes[2].set_ylabel('功率 (p.u.)', fontsize=11)
axes[2].set_title('(c) 发电机功率', fontsize=11, fontweight='bold')
axes[2].grid(True, alpha=0.3)
axes[2].legend(loc='best')

# 电压和励磁
ax3_1 = axes[3]
ax3_2 = ax3_1.twinx()

line1 = ax3_1.plot(exc_df['time'], exc_df['Terminal_Voltage_pu'], 'm-',
                   linewidth=2, label='机端电压')
line2 = ax3_2.plot(exc_df['time'], exc_df['Field_Voltage_pu'], 'c-',
                   linewidth=2, label='励磁电压')

ax3_1.axvline(x=1.0, color='r', linestyle='--', alpha=0.7)
ax3_1.axvline(x=1.15, color='g', linestyle='--', alpha=0.7)

ax3_1.set_xlabel('时间 (s)', fontsize=11)
ax3_1.set_ylabel('机端电压 (p.u.)', fontsize=11, color='m')
ax3_2.set_ylabel('励磁电压 (p.u.)', fontsize=11, color='c')
ax3_1.set_title('(d) 机端电压与励磁电压', fontsize=11, fontweight='bold')
ax3_1.grid(True, alpha=0.3)

lines = line1 + line2
labels = [l.get_label() for l in lines]
ax3_1.legend(lines, labels, loc='best')

plt.tight_layout()

plot_file = "smib_avr_fault.png"
plt.savefig(plot_file, dpi=300, bbox_inches='tight')
print(f"[10.1] 图形保存: {plot_file}")

plt.show()

print()
print("=" * 80)
print("仿真完成！")
print("=" * 80)
print()
print("主要结果:")
print(f"  - 初始功角: {gen_df['Power_Angle_deg'].iloc[0]:.2f}°")
print(f"  - 最大功角: {gen_df['Power_Angle_deg'].max():.2f}°")
print(f"  - 最小机端电压: {exc_df['Terminal_Voltage_pu'].min():.3f} p.u.")
print(f"  - 最大励磁电压: {exc_df['Field_Voltage_pu'].max():.2f} p.u.")
stable = "稳定" if gen_df['Power_Angle_deg'].max() < 120 else "失稳"
print(f"  - 系统状态: {stable}")
print()
print(f"数据: {csv_file}")
print(f"图形: {plot_file}")
print()
print("=" * 80)
