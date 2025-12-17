"""
单机无限大系统短路故障仿真
Single Machine Infinite Bus (SMIB) System with Short Circuit Fault Simulation

演示 pycontroldae 在电力系统仿真中的应用：
1. 同步发电机建模（包含内部特性方程）
2. 短路故障仿真（通过事件系统改变故障电阻）
3. Port API 连接
4. 数据导出和可视化

Demonstrates pycontroldae for power system simulation:
1. Synchronous generator modeling (with internal dynamics)
2. Short circuit fault simulation (using event system)
3. Port-based connections
4. Data export and visualization
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib.pyplot as plt
from pycontroldae.core import Module, System, Simulator, DataProbe, at_time

print("=" * 80)
print("单机无限大系统短路故障仿真")
print("Single Machine Infinite Bus (SMIB) Short Circuit Fault Simulation")
print("=" * 80)
print()

# ==============================================================================
# Part 1: 同步发电机建模
# ==============================================================================
print("PART 1: 创建同步发电机模型")
print("-" * 80)

class SynchronousGenerator(Module):
    """
    同步发电机模型（简化暂态模型）

    状态变量:
    - delta: 功角 (rad)
    - omega: 角速度偏差 (rad/s)
    - E_q_prime: 交轴暂态电势 (p.u.)
    - E_d_prime: 直轴暂态电势 (p.u.)
    - I_d: 直轴电流 (p.u.)
    - I_q: 交轴电流 (p.u.)

    输入:
    - V_terminal: 机端电压 (p.u.)
    - theta_v: 机端电压相角 (rad)
    - P_m: 机械功率 (p.u.)

    参数:
    - H: 惯性时间常数 (s)
    - D: 阻尼系数
    - X_d: 直轴同步电抗 (p.u.)
    - X_q: 交轴同步电抗 (p.u.)
    - X_d_prime: 直轴暂态电抗 (p.u.)
    - T_d0_prime: 直轴开路暂态时间常数 (s)
    - E_fd: 励磁电压 (p.u.)
    """

    def __init__(self, name: str,
                 H: float = 5.0,        # 惯性时间常数
                 damping: float = 2.0,  # 阻尼系数
                 X_d: float = 1.8,      # 直轴同步电抗
                 X_q: float = 1.7,      # 交轴同步电抗
                 X_d_prime: float = 0.3,  # 直轴暂态电抗
                 T_d0_prime: float = 8.0, # 直轴开路暂态时间常数
                 E_fd: float = 1.8,     # 励磁电压
                 omega_0: float = 314.159):  # 同步角速度 (50Hz)

        super().__init__(name)

        # 状态变量
        self.add_state("delta", 0.5)      # 功角 (rad)
        self.add_state("omega", 0.0)      # 角速度偏差
        self.add_state("E_q_prime", 1.0)  # 交轴暂态电势
        self.add_state("E_d_prime", 0.0)  # 直轴暂态电势
        self.add_state("I_d", 0.0)        # 直轴电流
        self.add_state("I_q", 0.0)        # 交轴电流

        # 输入（机端条件）
        self.add_input("V_terminal", 1.0)  # 机端电压
        self.add_input("theta_v", 0.0)     # 机端电压相角
        self.add_input("P_m", 0.8)         # 机械功率

        # 输出
        self.add_output("P_e", 0.0)        # 电磁功率
        self.add_output("delta_deg", 0.0)  # 功角（度）

        # 参数
        self.add_param("H", H)
        self.add_param("damping", damping)
        self.add_param("X_d", X_d)
        self.add_param("X_q", X_q)
        self.add_param("X_d_prime", X_d_prime)
        self.add_param("T_d0_prime", T_d0_prime)
        self.add_param("E_fd", E_fd)
        self.add_param("omega_0", omega_0)
        self.add_param("tau_fast", 0.001)  # 快速跟踪时间常数

        # 摇摆方程
        # d(delta)/dt = omega
        self.add_equation("D(delta) ~ omega")

        # d(omega)/dt = (P_m - P_e - damping*omega) / (2*H)
        # 其中 P_e = E_q_prime * I_q + E_d_prime * I_d + (X_q - X_d_prime) * I_d * I_q
        self.add_equation(
            "D(omega) ~ (P_m - (E_q_prime * I_q + E_d_prime * I_d + (X_q - X_d_prime) * I_d * I_q) - damping * omega) / (2 * H)"
        )

        # 暂态电势方程
        # dE_q'/dt = (E_fd - E_q' - (X_d - X_d') * I_d) / T_d0'
        self.add_equation(
            "D(E_q_prime) ~ (E_fd - E_q_prime - (X_d - X_d_prime) * I_d) / T_d0_prime"
        )

        # 简化：假设 E_d' = 0（忽略直轴阻尼绕组）
        self.add_equation("D(E_d_prime) ~ -E_d_prime / 0.1")

        # 定子代数方程（通过快速微分近似）
        # V_d = -X_q * I_q
        # V_q = E_q' - X_d' * I_d
        # 其中 V_d = V_terminal * sin(delta - theta_v)
        #      V_q = V_terminal * cos(delta - theta_v)

        # I_d 计算: V_q = E_q' - X_d' * I_d
        # => I_d = (E_q' - V_q) / X_d' = (E_q' - V_terminal*cos(delta-theta_v)) / X_d'
        self.add_equation(
            "D(I_d) ~ ((E_q_prime - V_terminal * cos(delta - theta_v)) / X_d_prime - I_d) / tau_fast"
        )

        # I_q 计算: V_d = -X_q * I_q
        # => I_q = -V_d / X_q = -V_terminal*sin(delta-theta_v) / X_q
        self.add_equation(
            "D(I_q) ~ ((-V_terminal * sin(delta - theta_v)) / X_q - I_q) / tau_fast"
        )

        # 输出：电磁功率
        self.add_equation(
            "D(P_e) ~ (E_q_prime * I_q + E_d_prime * I_d + (X_q - X_d_prime) * I_d * I_q - P_e) / tau_fast"
        )

        # 输出：功角（度）
        self.add_equation(
            "D(delta_deg) ~ (delta * 180 / 3.14159 - delta_deg) / tau_fast"
        )

        # 设置默认端口
        self.set_input("P_m")
        self.set_output("P_e")

print("[1.1] 创建同步发电机模型...")
generator = SynchronousGenerator(
    name="gen",
    H=5.0,           # 惯性时间常数 5s
    damping=2.0,     # 阻尼系数
    X_d=1.8,         # 直轴同步电抗
    X_q=1.7,         # 交轴同步电抗
    X_d_prime=0.3,   # 直轴暂态电抗
    T_d0_prime=8.0,  # 直轴暂态时间常数
    E_fd=1.8         # 励磁电压
)
generator.build()
print(f"[OK] 同步发电机: {generator}")
print()

# ==============================================================================
# Part 2: 无限大母线和短路阻抗建模
# ==============================================================================
print("PART 2: 创建无限大母线和短路阻抗")
print("-" * 80)

# 无限大母线（恒定电压源）
infinite_bus = Module("infinite_bus")
infinite_bus.add_output("V_bus", 1.0)      # 母线电压 (p.u.)
infinite_bus.add_output("theta_bus", 0.0)  # 母线相角 (rad)
infinite_bus.add_param("V_nominal", 1.0)
infinite_bus.add_param("theta_nominal", 0.0)

# 恒定电压
infinite_bus.add_equation("D(V_bus) ~ (V_nominal - V_bus) / 1e-6")
infinite_bus.add_equation("D(theta_bus) ~ (theta_nominal - theta_bus) / 1e-6")

infinite_bus.set_output("V_bus")
infinite_bus.build()

print(f"[2.1] 无限大母线: {infinite_bus}")

# 短路故障电阻（初始值很大，故障时变小）
fault_resistance = Module("fault")
fault_resistance.add_output("R_fault", 1000.0)  # 故障电阻 (p.u.)
fault_resistance.add_param("R_value", 1000.0)   # 可变电阻值
fault_resistance.add_equation("D(R_fault) ~ (R_value - R_fault) / 0.01")  # 快速跟踪

fault_resistance.set_output("R_fault")
fault_resistance.build()

print(f"[2.2] 故障电阻模块: {fault_resistance}")

# 线路阻抗（连接发电机和母线）
transmission_line = Module("line")
transmission_line.add_input("V_bus", 1.0)         # 母线电压
transmission_line.add_input("theta_bus", 0.0)     # 母线相角
transmission_line.add_input("R_fault", 1000.0)    # 故障电阻

transmission_line.add_output("V_terminal", 1.0)   # 机端电压
transmission_line.add_output("theta_v", 0.0)      # 机端电压相角

transmission_line.add_param("X_line", 0.4)        # 线路电抗 (p.u.)
transmission_line.add_param("tau", 0.001)         # 快速时间常数

# 简化模型：机端电压受故障电阻影响
# V_terminal = V_bus * R_fault / (R_fault + X_line)（近似）
# 故障前 R_fault 很大，V_terminal ≈ V_bus
# 故障时 R_fault 很小，V_terminal 下降

transmission_line.add_equation(
    "D(V_terminal) ~ (V_bus * R_fault / (R_fault + X_line) - V_terminal) / tau"
)

# 相角传递（简化）
transmission_line.add_equation(
    "D(theta_v) ~ (theta_bus - theta_v) / tau"
)

transmission_line.set_input("V_bus")
transmission_line.set_output("V_terminal")
transmission_line.build()

print(f"[2.3] 输电线路模块: {transmission_line}")
print()

# ==============================================================================
# Part 3: 机械功率输入（恒定）
# ==============================================================================
print("PART 3: 创建机械功率输入")
print("-" * 80)

mechanical_power = Module("turbine")
mechanical_power.add_output("P_m", 0.8)  # 机械功率 (p.u.)
mechanical_power.add_param("P_m_set", 0.8)
mechanical_power.add_equation("D(P_m) ~ (P_m_set - P_m) / 1e-6")

mechanical_power.set_output("P_m")
mechanical_power.build()

print(f"[3.1] 机械功率: {mechanical_power}")
print()

# ==============================================================================
# Part 4: 使用 Port API 组装系统
# ==============================================================================
print("PART 4: 使用 Port API 组装系统")
print("-" * 80)

system = System("smib_fault")

# 添加所有模块
modules = [generator, infinite_bus, fault_resistance, transmission_line, mechanical_power]
for mod in modules:
    system.add_module(mod)

print(f"[4.1] 添加了 {len(system.modules)} 个模块")

# 使用 Port API 连接（展示新特性）
print("\n[4.2] 定义连接（使用 Port API）：")

# 机械功率 -> 发电机
system.connect(mechanical_power.P_m >> generator.P_m)
print("    [OK] turbine.P_m >> gen.P_m")

# 母线电压 -> 线路
system.connect(infinite_bus.V_bus >> transmission_line.V_bus)
system.connect(infinite_bus.theta_bus >> transmission_line.theta_bus)
print("    [OK] infinite_bus >> line (V_bus, theta_bus)")

# 故障电阻 -> 线路
system.connect(fault_resistance.R_fault >> transmission_line.R_fault)
print("    [OK] fault.R_fault >> line.R_fault")

# 线路机端电压 -> 发电机
system.connect(transmission_line.V_terminal >> generator.V_terminal)
system.connect(transmission_line.theta_v >> generator.theta_v)
print("    [OK] line >> gen (V_terminal, theta_v)")

print(f"\n[4.3] 总共定义了 {len(system.connections)} 个连接")
print()

# ==============================================================================
# Part 5: 定义短路故障事件
# ==============================================================================
print("PART 5: 定义短路故障事件")
print("-" * 80)

# 故障发生：t = 1.0s，电阻从 1000 p.u. 降为 0.01 p.u.
def fault_occurrence(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] 短路故障发生！R_fault: 1000 -> 0.01 p.u.")
    return {"fault.R_value": 0.01}

# 故障切除：t = 1.2s，电阻恢复到 1000 p.u.
def fault_clearance(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] 短路故障切除！R_fault: 0.01 -> 1000 p.u.")
    return {"fault.R_value": 1000.0}

system.add_event(at_time(1.0, fault_occurrence))
system.add_event(at_time(1.2, fault_clearance))

print("[5.1] 添加了 2 个时间事件:")
print("      - t=1.0s: 短路故障发生 (R_fault -> 0.01 p.u.)")
print("      - t=1.2s: 短路故障切除 (R_fault -> 1000 p.u.)")
print()

# ==============================================================================
# Part 6: 配置数据探测器
# ==============================================================================
print("PART 6: 配置数据探测器")
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
    "voltages": DataProbe(
        variables=[
            str(transmission_line.V_terminal),
            str(generator.E_q_prime)
        ],
        names=["Terminal_Voltage_pu", "Transient_EMF_pu"],
        description="Voltage variables"
    ),
    "fault": DataProbe(
        variables=[str(fault_resistance.R_fault)],
        names=["Fault_Resistance_pu"],
        description="Fault resistance"
    )
}

print(f"[6.1] 配置了 {len(probes)} 个数据探测器")
for name, probe in probes.items():
    print(f"      {name}: {len(probe.variables)} 变量")
print()

# ==============================================================================
# Part 7: 编译和仿真
# ==============================================================================
print("PART 7: 编译系统并运行仿真")
print("-" * 80)

print("[7.1] 编译系统...")
try:
    system.compile()
    print("[OK] 系统编译成功")
except Exception as e:
    print(f"[ERROR] 编译失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[7.2] 运行仿真 (0-5s, dt=0.001s)...")
print("      预期行为:")
print("      - t < 1.0s: 稳态运行")
print("      - t = 1.0s: 短路故障，功角摆动")
print("      - t = 1.2s: 故障切除，系统恢复")
print()

simulator = Simulator(system)

try:
    result = simulator.run(
        t_span=(0.0, 5.0),
        dt=0.001,
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
# Part 8: 导出数据
# ==============================================================================
print("PART 8: 导出数据")
print("-" * 80)

# 导出 CSV
csv_file = "smib_fault_simulation.csv"
result.to_csv(csv_file, include_probes=True)
print(f"[8.1] 数据已导出到: {csv_file}")

# 打印摘要
print("\n[8.2] 仿真结果摘要:")
result.print_summary()
print()

# ==============================================================================
# Part 9: 可视化
# ==============================================================================
print("PART 9: 绘制仿真结果")
print("-" * 80)

# 获取探测器数据
gen_df = result.get_probe_dataframe("generator")
volt_df = result.get_probe_dataframe("voltages")
fault_df = result.get_probe_dataframe("fault")

# 创建图形
fig, axes = plt.subplots(4, 1, figsize=(12, 10))
fig.suptitle('单机无限大系统短路故障仿真\nSMIB Short Circuit Fault Simulation',
             fontsize=14, fontweight='bold')

# 子图1: 功角
axes[0].plot(gen_df['time'], gen_df['Power_Angle_deg'], 'b-', linewidth=2)
axes[0].axvline(x=1.0, color='r', linestyle='--', alpha=0.7, label='Fault On')
axes[0].axvline(x=1.2, color='g', linestyle='--', alpha=0.7, label='Fault Clear')
axes[0].set_ylabel('Power Angle (deg)', fontsize=11)
axes[0].set_title('(a) Generator Power Angle', fontsize=11, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].legend(loc='best')

# 子图2: 角速度偏差
axes[1].plot(gen_df['time'], gen_df['Speed_Deviation_rad_s'], 'r-', linewidth=2)
axes[1].axvline(x=1.0, color='r', linestyle='--', alpha=0.7)
axes[1].axvline(x=1.2, color='g', linestyle='--', alpha=0.7)
axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
axes[1].set_ylabel('Speed Deviation (rad/s)', fontsize=11)
axes[1].set_title('(b) Generator Speed Deviation', fontsize=11, fontweight='bold')
axes[1].grid(True, alpha=0.3)

# 子图3: 功率
axes[2].plot(gen_df['time'], gen_df['Electrical_Power_pu'], 'g-', linewidth=2, label='P_e')
axes[2].axhline(y=0.8, color='b', linestyle='--', alpha=0.7, label='P_m')
axes[2].axvline(x=1.0, color='r', linestyle='--', alpha=0.7)
axes[2].axvline(x=1.2, color='g', linestyle='--', alpha=0.7)
axes[2].set_ylabel('Power (p.u.)', fontsize=11)
axes[2].set_title('(c) Electrical and Mechanical Power', fontsize=11, fontweight='bold')
axes[2].grid(True, alpha=0.3)
axes[2].legend(loc='best')

# 子图4: 机端电压
axes[3].plot(volt_df['time'], volt_df['Terminal_Voltage_pu'], 'm-', linewidth=2)
axes[3].axvline(x=1.0, color='r', linestyle='--', alpha=0.7)
axes[3].axvline(x=1.2, color='g', linestyle='--', alpha=0.7)
axes[3].set_xlabel('Time (s)', fontsize=11)
axes[3].set_ylabel('Terminal Voltage (p.u.)', fontsize=11)
axes[3].set_title('(d) Generator Terminal Voltage', fontsize=11, fontweight='bold')
axes[3].grid(True, alpha=0.3)

plt.tight_layout()

# 保存图形
plot_file = "smib_fault_simulation.png"
plt.savefig(plot_file, dpi=300, bbox_inches='tight')
print(f"[9.1] 图形已保存到: {plot_file}")

# 显示图形
plt.show()

print()
print("=" * 80)
print("仿真完成！")
print("=" * 80)
print()
print("主要结果:")
print("  - 稳态功角:", f"{gen_df['Power_Angle_deg'].iloc[0]:.2f}°")
print("  - 故障期间最大功角:", f"{gen_df['Power_Angle_deg'].max():.2f}°")
print("  - 故障期间最小机端电压:", f"{volt_df['Terminal_Voltage_pu'].min():.3f} p.u.")
print("  - 系统稳定性:", "稳定" if gen_df['Power_Angle_deg'].max() < 180 else "失稳")
print()
print(f"数据文件: {csv_file}")
print(f"图形文件: {plot_file}")
print()
print("=" * 80)
