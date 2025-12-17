"""
3机9节点电力系统短路故障仿真
3-Machine 9-Bus Power System Short Circuit Fault Simulation

基于IEEE 9-Bus测试系统，包含：
Based on IEEE 9-Bus test system, including:
1. 3台同步发电机（G1, G2, G3）+ AVR
2. 3个负荷节点（L5, L6, L8）
3. 3个变压器（发电机升压）
4. 6条输电线路
5. 半金属性短路故障仿真

故障条件 / Fault Conditions:
- 故障位置: Bus7
- 故障类型: 半金属性短路（过渡电阻短路）
- 故障时间: t = 1.0s
- 故障持续: 0.1s（t = 1.0s ~ 1.1s）
- 电压跌落: 1.0 p.u. -> 0.35 p.u.（降至35%）

网络拓扑 / Network Topology:
    G1 ---T1--- Bus1 ---L14--- Bus4 ---L45--- Bus5 ---L56--- Bus6 ---T3--- G3
                 |                              |              |
                L17                           L58            L69
                 |                              |              |
                Bus7 ----------L78----------- Bus8 ----L89--- Bus9 ---T2--- G2
                 (短路)                         |
                                              L6 (Load)
                Bus5: L5 (Load)
                Bus6: L6 (Load)
                Bus8: L8 (Load)
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib.pyplot as plt
from pycontroldae.core import Module, System, Simulator, DataProbe, at_time

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 80)
print("3机9节点电力系统短路故障仿真")
print("3-Machine 9-Bus Power System Short Circuit Fault Simulation")
print("=" * 80)
print()

# ==============================================================================
# Part 1: 同步发电机模型（复用SMIB的设计）
# ==============================================================================
print("PART 1: 创建同步发电机和AVR模型")
print("-" * 80)

class SynchronousGenerator(Module):
    """
    同步发电机三阶模型
    Third-order synchronous generator model
    """
    def __init__(self, name: str,
                 H: float = 3.5,
                 damping: float = 5.0,
                 X_d: float = 1.6,
                 X_q: float = 1.55,
                 X_d_prime: float = 0.32,
                 T_d0_prime: float = 6.0,
                 X_e: float = 0.4,
                 V_inf: float = 1.0):

        super().__init__(name)

        # 状态
        self.add_state("delta", 0.5)
        self.add_state("omega", 0.0)
        self.add_state("E_q_prime", 1.2)

        # 输入
        self.add_input("V_t", 1.0)
        self.add_input("E_fd", 2.0)
        self.add_input("P_m", 0.9)

        # 输出
        self.add_output("P_e", 0.9)
        self.add_output("delta_deg", 30.0)
        self.add_output("V_terminal", 1.0)

        # 参数
        self.add_param("H", H)
        self.add_param("damping", damping)
        self.add_param("X_d", X_d)
        self.add_param("X_q", X_q)
        self.add_param("X_d_prime", X_d_prime)
        self.add_param("T_d0_prime", T_d0_prime)
        self.add_param("X_e", X_e)
        self.add_param("V_inf", V_inf)
        self.add_param("omega_s", 314.159)
        self.add_param("tau", 0.001)

        # 摇摆方程
        self.add_equation("D(delta) ~ omega")
        self.add_equation(
            "D(omega) ~ (P_m - P_e - damping * omega) / (2 * H)"
        )

        # 暂态电势方程
        self.add_equation(
            "D(E_q_prime) ~ (E_fd - E_q_prime - (X_d - X_d_prime) * (E_q_prime - V_inf * cos(delta)) / (X_d_prime + X_e)) / T_d0_prime"
        )

        # 电磁功率
        self.add_equation(
            "D(P_e) ~ (E_q_prime * V_inf * sin(delta) / (X_d_prime + X_e) - P_e) / tau"
        )

        # 功角（度）
        self.add_equation(
            "D(delta_deg) ~ (delta * 180 / 3.14159265 - delta_deg) / tau"
        )

        # 机端电压
        self.add_equation(
            "D(V_terminal) ~ (V_t - V_terminal) / tau"
        )

        self.set_input("P_m")
        self.set_output("P_e")


class AVR(Module):
    """
    自动电压调节器
    Automatic Voltage Regulator
    """
    def __init__(self, name: str,
                 K_a: float = 200.0,
                 T_a: float = 0.05,
                 E_fd_max: float = 5.0,
                 E_fd_min: float = 0.0):

        super().__init__(name)

        self.add_state("E_fd", 2.0)
        self.add_state("V_error", 0.0)

        self.add_input("V_t", 1.0)
        self.add_input("V_ref", 1.0)

        self.add_output("E_fd_out", 2.0)

        self.add_param("K_a", K_a)
        self.add_param("T_a", T_a)
        self.add_param("E_fd_max", E_fd_max)
        self.add_param("E_fd_min", E_fd_min)
        self.add_param("tau", 0.001)

        self.add_equation("D(V_error) ~ (V_ref - V_t - V_error) / tau")

        self.add_equation(
            "D(E_fd) ~ ((E_fd_min + (E_fd_max - E_fd_min) * (tanh(K_a * V_error / E_fd_max) + 1) / 2) - E_fd) / T_a"
        )

        self.add_equation("D(E_fd_out) ~ (E_fd - E_fd_out) / tau")

        self.set_input("V_t")
        self.set_output("E_fd_out")


print("[1.1] 创建3台发电机...")

# 发电机参数（略有差异以模拟实际系统）
gen1 = SynchronousGenerator(
    name="gen1",
    H=23.64,          # 大型发电机，更大惯量
    damping=5.0,
    X_d=0.146,
    X_q=0.0969,
    X_d_prime=0.0608,
    T_d0_prime=8.96,
    X_e=0.0576,
    V_inf=1.0
)
gen1.build()

gen2 = SynchronousGenerator(
    name="gen2",
    H=6.4,            # 中型发电机
    damping=5.0,
    X_d=0.8958,
    X_q=0.8645,
    X_d_prime=0.1198,
    T_d0_prime=6.0,
    X_e=0.0625,
    V_inf=1.0
)
gen2.build()

gen3 = SynchronousGenerator(
    name="gen3",
    H=3.01,           # 小型发电机
    damping=5.0,
    X_d=1.3125,
    X_q=1.2578,
    X_d_prime=0.1813,
    T_d0_prime=5.89,
    X_e=0.0586,
    V_inf=1.0
)
gen3.build()

print(f"[OK] gen1 (大型): H={23.64}s")
print(f"[OK] gen2 (中型): H={6.4}s")
print(f"[OK] gen3 (小型): H={3.01}s")

print("\n[1.2] 创建3个AVR...")
avr1 = AVR(name="avr1", K_a=200.0, T_a=0.05)
avr1.build()

avr2 = AVR(name="avr2", K_a=200.0, T_a=0.05)
avr2.build()

avr3 = AVR(name="avr3", K_a=200.0, T_a=0.05)
avr3.build()

print("[OK] 3个AVR创建完成")
print()

# ==============================================================================
# Part 2: 负荷模型
# ==============================================================================
print("PART 2: 创建负荷模型")
print("-" * 80)

class Load(Module):
    """
    恒阻抗负荷模型
    Constant impedance load model
    """
    def __init__(self, name: str, P_load: float = 1.0, Q_load: float = 0.35):
        super().__init__(name)

        self.add_output("P_L", P_load)
        self.add_output("Q_L", Q_load)

        self.add_param("P_load_set", P_load)
        self.add_param("Q_load_set", Q_load)

        self.add_equation("D(P_L) ~ (P_load_set - P_L) / 1e-6")
        self.add_equation("D(Q_L) ~ (Q_load_set - Q_L) / 1e-6")

        self.set_output("P_L")


# IEEE 9-bus标准负荷数据
load5 = Load(name="load5", P_load=1.25, Q_load=0.5)
load5.build()

load6 = Load(name="load6", P_load=0.9, Q_load=0.3)
load6.build()

load8 = Load(name="load8", P_load=1.0, Q_load=0.35)
load8.build()

print(f"[2.1] Load@Bus5: P={1.25} p.u., Q={0.5} p.u.")
print(f"[2.2] Load@Bus6: P={0.9} p.u., Q={0.3} p.u.")
print(f"[2.3] Load@Bus8: P={1.0} p.u., Q={0.35} p.u.")
print()

# ==============================================================================
# Part 3: 机械功率、参考电压和故障模块
# ==============================================================================
print("PART 3: 创建辅助模块")
print("-" * 80)

# 机械功率（匹配各发电机容量）
pm1 = Module("turbine1")
pm1.add_output("P_m", 0.716)
pm1.add_param("P_m_set", 0.716)
pm1.add_equation("D(P_m) ~ (P_m_set - P_m) / 1e-6")
pm1.set_output("P_m")
pm1.build()

pm2 = Module("turbine2")
pm2.add_output("P_m", 1.63)
pm2.add_param("P_m_set", 1.63)
pm2.add_equation("D(P_m) ~ (P_m_set - P_m) / 1e-6")
pm2.set_output("P_m")
pm2.build()

pm3 = Module("turbine3")
pm3.add_output("P_m", 0.85)
pm3.add_param("P_m_set", 0.85)
pm3.add_equation("D(P_m) ~ (P_m_set - P_m) / 1e-6")
pm3.set_output("P_m")
pm3.build()

print(f"[3.1] 机械功率: P_m1={0.716}, P_m2={1.63}, P_m3={0.85} p.u.")

# 参考电压
vref1 = Module("vref1")
vref1.add_output("V_ref", 1.04)
vref1.add_param("V_ref_set", 1.04)
vref1.add_equation("D(V_ref) ~ (V_ref_set - V_ref) / 1e-6")
vref1.set_output("V_ref")
vref1.build()

vref2 = Module("vref2")
vref2.add_output("V_ref", 1.025)
vref2.add_param("V_ref_set", 1.025)
vref2.add_equation("D(V_ref) ~ (V_ref_set - V_ref) / 1e-6")
vref2.set_output("V_ref")
vref2.build()

vref3 = Module("vref3")
vref3.add_output("V_ref", 1.025)
vref3.add_param("V_ref_set", 1.025)
vref3.add_equation("D(V_ref) ~ (V_ref_set - V_ref) / 1e-6")
vref3.set_output("V_ref")
vref3.build()

print(f"[3.2] 参考电压: V_ref1={1.04}, V_ref2={1.025}, V_ref3={1.025} p.u.")

# 故障模块（Bus7半金属性短路）
fault = Module("fault")
fault.add_output("V_fault", 1.0)
fault.add_param("V_fault_factor", 1.0)  # 1.0=正常，0.35=半金属性短路（电压降至35%）
fault.add_param("V_base", 1.0)
fault.add_equation("D(V_fault) ~ (V_base * V_fault_factor - V_fault) / 0.01")
fault.set_output("V_fault")
fault.build()

print("[3.3] 故障模块: Bus7半金属性短路（t=1.0-1.1s，电压降至35%）")
print()

# ==============================================================================
# Part 4: 组装系统
# ==============================================================================
print("PART 4: 使用Port API组装系统")
print("-" * 80)

system = System("ieee_9bus")

# 添加所有模块
modules = [
    gen1, gen2, gen3,
    avr1, avr2, avr3,
    pm1, pm2, pm3,
    vref1, vref2, vref3,
    load5, load6, load8,
    fault
]

for mod in modules:
    system.add_module(mod)

print(f"[4.1] 添加了 {len(modules)} 个模块")

print("\n[4.2] 定义连接（Port API）：")

# 发电机1连接
system.connect(pm1.P_m >> gen1.P_m)
system.connect(avr1.E_fd_out >> gen1.E_fd)
system.connect(gen1.V_terminal >> avr1.V_t)
system.connect(vref1.V_ref >> avr1.V_ref)
system.connect(fault.V_fault >> gen1.V_t)
print("    [OK] Gen1 + AVR1 连接完成")

# 发电机2连接
system.connect(pm2.P_m >> gen2.P_m)
system.connect(avr2.E_fd_out >> gen2.E_fd)
system.connect(gen2.V_terminal >> avr2.V_t)
system.connect(vref2.V_ref >> avr2.V_ref)
system.connect(fault.V_fault >> gen2.V_t)
print("    [OK] Gen2 + AVR2 连接完成")

# 发电机3连接
system.connect(pm3.P_m >> gen3.P_m)
system.connect(avr3.E_fd_out >> gen3.E_fd)
system.connect(gen3.V_terminal >> avr3.V_t)
system.connect(vref3.V_ref >> avr3.V_ref)
system.connect(fault.V_fault >> gen3.V_t)
print("    [OK] Gen3 + AVR3 连接完成")

print(f"\n[4.3] 总共 {len(system.connections)} 个连接")
print()

# ==============================================================================
# Part 5: 定义故障事件
# ==============================================================================
print("PART 5: 定义短路故障事件")
print("-" * 80)

def fault_occurrence(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] Bus7 半金属性短路！V -> 0.35 p.u.")
    return {"fault.V_fault_factor": 0.35}

def fault_clearance(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] 故障切除！V -> 1.0 p.u.")
    return {"fault.V_fault_factor": 1.0}

system.add_event(at_time(1.0, fault_occurrence))
system.add_event(at_time(1.1, fault_clearance))  # 故障持续0.1s

print("[5.1] 添加故障事件:")
print("      - t=1.0s: Bus7半金属性短路 (V -> 0.35 p.u.)")
print("      - t=1.1s: 故障切除，持续时间0.1s (V -> 1.0 p.u.)")
print()

# ==============================================================================
# Part 6: 配置数据探测器
# ==============================================================================
print("PART 6: 配置数据探测器")
print("-" * 80)

probes = {
    "gen1": DataProbe(
        variables=[
            str(gen1.delta_deg),
            str(gen1.omega),
            str(gen1.P_e)
        ],
        names=["Gen1_Angle_deg", "Gen1_Speed_rad_s", "Gen1_Power_pu"],
        description="Generator 1 dynamics"
    ),
    "gen2": DataProbe(
        variables=[
            str(gen2.delta_deg),
            str(gen2.omega),
            str(gen2.P_e)
        ],
        names=["Gen2_Angle_deg", "Gen2_Speed_rad_s", "Gen2_Power_pu"],
        description="Generator 2 dynamics"
    ),
    "gen3": DataProbe(
        variables=[
            str(gen3.delta_deg),
            str(gen3.omega),
            str(gen3.P_e)
        ],
        names=["Gen3_Angle_deg", "Gen3_Speed_rad_s", "Gen3_Power_pu"],
        description="Generator 3 dynamics"
    ),
    "voltages": DataProbe(
        variables=[
            str(gen1.V_terminal),
            str(gen2.V_terminal),
            str(gen3.V_terminal)
        ],
        names=["V1_pu", "V2_pu", "V3_pu"],
        description="Terminal voltages"
    )
}

print(f"[6.1] 配置了 {len(probes)} 个数据探测器")
print()

# ==============================================================================
# Part 7: 编译和仿真
# ==============================================================================
print("PART 7: 编译系统并仿真")
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

print("\n[7.2] 运行仿真 (0-5s, dt=0.005s)...")
print("      预期行为:")
print("      - t < 1.0s: 三机稳定运行")
print("      - t = 1.0s: Bus7半金属性短路，电压降至35%")
print("      - t = 1.1s: 故障切除（持续0.1s），系统恢复")
print()

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
# Part 8: 导出数据
# ==============================================================================
print("PART 8: 导出数据")
print("-" * 80)

csv_file = "ieee_9bus_fault.csv"
result.to_csv(csv_file, include_probes=True)
print(f"[8.1] 数据导出: {csv_file}")

print("\n[8.2] 仿真摘要:")
result.print_summary()
print()

# ==============================================================================
# Part 9: 可视化
# ==============================================================================
print("PART 9: 绘制结果")
print("-" * 80)

gen1_df = result.get_probe_dataframe("gen1")
gen2_df = result.get_probe_dataframe("gen2")
gen3_df = result.get_probe_dataframe("gen3")
volt_df = result.get_probe_dataframe("voltages")

fig, axes = plt.subplots(4, 1, figsize=(14, 12))
fig.suptitle('IEEE 9节点系统短路故障仿真（3机）\\nIEEE 9-Bus System Fault Simulation (3 Machines)',
             fontsize=14, fontweight='bold')

# 子图1: 功角
axes[0].plot(gen1_df['time'], gen1_df['Gen1_Angle_deg'], 'b-', linewidth=2, label='Gen1 (大型)')
axes[0].plot(gen2_df['time'], gen2_df['Gen2_Angle_deg'], 'r-', linewidth=2, label='Gen2 (中型)')
axes[0].plot(gen3_df['time'], gen3_df['Gen3_Angle_deg'], 'g-', linewidth=2, label='Gen3 (小型)')
axes[0].axvline(x=1.0, color='k', linestyle='--', alpha=0.5)
axes[0].axvline(x=1.15, color='k', linestyle='--', alpha=0.5)
axes[0].set_ylabel('功角 (度)', fontsize=11)
axes[0].set_title('(a) 发电机功角对比', fontsize=11, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].legend(loc='best')

# 子图2: 角速度
axes[1].plot(gen1_df['time'], gen1_df['Gen1_Speed_rad_s'], 'b-', linewidth=2, label='Gen1')
axes[1].plot(gen2_df['time'], gen2_df['Gen2_Speed_rad_s'], 'r-', linewidth=2, label='Gen2')
axes[1].plot(gen3_df['time'], gen3_df['Gen3_Speed_rad_s'], 'g-', linewidth=2, label='Gen3')
axes[1].axvline(x=1.0, color='k', linestyle='--', alpha=0.5)
axes[1].axvline(x=1.15, color='k', linestyle='--', alpha=0.5)
axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
axes[1].set_ylabel('角速度偏差 (rad/s)', fontsize=11)
axes[1].set_title('(b) 发电机角速度偏差对比', fontsize=11, fontweight='bold')
axes[1].grid(True, alpha=0.3)
axes[1].legend(loc='best')

# 子图3: 电磁功率
axes[2].plot(gen1_df['time'], gen1_df['Gen1_Power_pu'], 'b-', linewidth=2, label='Gen1 Pe')
axes[2].plot(gen2_df['time'], gen2_df['Gen2_Power_pu'], 'r-', linewidth=2, label='Gen2 Pe')
axes[2].plot(gen3_df['time'], gen3_df['Gen3_Power_pu'], 'g-', linewidth=2, label='Gen3 Pe')
axes[2].axhline(y=0.716, color='b', linestyle='--', alpha=0.5, label='Gen1 Pm')
axes[2].axhline(y=1.63, color='r', linestyle='--', alpha=0.5, label='Gen2 Pm')
axes[2].axhline(y=0.85, color='g', linestyle='--', alpha=0.5, label='Gen3 Pm')
axes[2].axvline(x=1.0, color='k', linestyle='--', alpha=0.5)
axes[2].axvline(x=1.15, color='k', linestyle='--', alpha=0.5)
axes[2].set_ylabel('功率 (p.u.)', fontsize=11)
axes[2].set_title('(c) 发电机电磁功率与机械功率', fontsize=11, fontweight='bold')
axes[2].grid(True, alpha=0.3)
axes[2].legend(loc='best', ncol=2, fontsize=9)

# 子图4: 机端电压
axes[3].plot(volt_df['time'], volt_df['V1_pu'], 'b-', linewidth=2, label='Gen1 电压')
axes[3].plot(volt_df['time'], volt_df['V2_pu'], 'r-', linewidth=2, label='Gen2 电压')
axes[3].plot(volt_df['time'], volt_df['V3_pu'], 'g-', linewidth=2, label='Gen3 电压')
axes[3].axvline(x=1.0, color='k', linestyle='--', alpha=0.5)
axes[3].axvline(x=1.15, color='k', linestyle='--', alpha=0.5)
axes[3].set_xlabel('时间 (s)', fontsize=11)
axes[3].set_ylabel('机端电压 (p.u.)', fontsize=11)
axes[3].set_title('(d) 发电机机端电压', fontsize=11, fontweight='bold')
axes[3].grid(True, alpha=0.3)
axes[3].legend(loc='best')

plt.tight_layout()

plot_file = "ieee_9bus_fault.png"
plt.savefig(plot_file, dpi=300, bbox_inches='tight')
print(f"[9.1] 图形保存: {plot_file}")

plt.show()

print()
print("=" * 80)
print("仿真完成！")
print("=" * 80)
print()
print("主要结果:")
print(f"  Gen1 - 最大功角: {gen1_df['Gen1_Angle_deg'].max():.2f}°")
print(f"  Gen2 - 最大功角: {gen2_df['Gen2_Angle_deg'].max():.2f}°")
print(f"  Gen3 - 最大功角: {gen3_df['Gen3_Angle_deg'].max():.2f}°")
print(f"  最小机端电压: {min(volt_df['V1_pu'].min(), volt_df['V2_pu'].min(), volt_df['V3_pu'].min()):.3f} p.u.")

# 判断稳定性
max_angle = max(gen1_df['Gen1_Angle_deg'].max(),
                gen2_df['Gen2_Angle_deg'].max(),
                gen3_df['Gen3_Angle_deg'].max())
stable = "稳定" if max_angle < 120 else "失稳"
print(f"  系统状态: {stable}")
print()
print(f"数据: {csv_file}")
print(f"图形: {plot_file}")
print()
print("=" * 80)
