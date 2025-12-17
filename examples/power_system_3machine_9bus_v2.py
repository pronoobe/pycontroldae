"""
3机9节点电力系统短路故障仿真（带启动过程）
3-Machine 9-Bus Power System Short Circuit Fault Simulation (with Initialization)

改进版：
1. 先进行1秒的启动仿真，计算稳态初值
2. 使用稳态初值作为故障仿真的起点
3. 在第2秒引入半金属性短路故障
4. 故障持续0.1s后切除
5. 总仿真时间10s

故障条件 / Fault Conditions:
- 故障位置: Bus7
- 故障类型: 半金属性短路（过渡电阻短路）
- 故障时间: t = 2.0s (启动后1秒)
- 故障持续: 0.1s（t = 2.0s ~ 2.1s）
- 电压跌落: 1.0 p.u. -> 0.35 p.u.（降至35%）
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib.pyplot as plt
from pycontroldae.core import Module, System, Simulator, DataProbe, at_time

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 80)
print("3机9节点电力系统短路故障仿真（带启动过程）")
print("3-Machine 9-Bus Power System Fault Simulation (with Initialization)")
print("=" * 80)
print()

# ==============================================================================
# Part 1: 同步发电机和AVR模型
# ==============================================================================
print("PART 1: 创建同步发电机和AVR模型")
print("-" * 80)

class SynchronousGenerator(Module):
    """同步发电机三阶模型"""
    def __init__(self, name: str,
                 H: float = 3.5,
                 damping: float = 5.0,
                 X_d: float = 1.6,
                 X_q: float = 1.55,
                 X_d_prime: float = 0.32,
                 T_d0_prime: float = 6.0,
                 X_e: float = 0.4,
                 V_inf: float = 1.0,
                 # 初始功角和电势
                 delta_init: float = 0.5,
                 E_q_prime_init: float = 1.2):

        super().__init__(name)

        # 状态变量（使用传入的初始值）
        self.add_state("delta", delta_init)
        self.add_state("omega", 0.0)
        self.add_state("E_q_prime", E_q_prime_init)

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
    """自动电压调节器"""
    def __init__(self, name: str,
                 K_a: float = 200.0,
                 T_a: float = 0.05,
                 E_fd_max: float = 5.0,
                 E_fd_min: float = 0.0,
                 E_fd_init: float = 2.0):

        super().__init__(name)

        self.add_state("E_fd", E_fd_init)
        self.add_state("V_error", 0.0)

        self.add_input("V_t", 1.0)
        self.add_input("V_ref", 1.0)

        self.add_output("E_fd_out", E_fd_init)

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


print("[1.1] 创建3台发电机（使用计算的初始功角）...")

# 根据功率平衡计算初始功角
# P_e = E_q' * V_inf * sin(delta) / (X_d' + X_e)
# delta ≈ arcsin(P_m * (X_d' + X_e) / (E_q' * V_inf))

def calculate_initial_angle(P_m, E_q_prime, X_d_prime, X_e, V_inf=1.0):
    """计算初始功角（弧度）"""
    X_total = X_d_prime + X_e
    sin_delta = P_m * X_total / (E_q_prime * V_inf)
    # 限制在[-1, 1]范围内
    sin_delta = max(-1.0, min(1.0, sin_delta))
    return np.arcsin(sin_delta)

# Gen1参数
P_m1 = 0.716
E_q1 = 1.2
X_d_prime1 = 0.0608
X_e1 = 0.0576
delta1_init = calculate_initial_angle(P_m1, E_q1, X_d_prime1, X_e1)

# Gen2参数
P_m2 = 1.63
E_q2 = 1.2
X_d_prime2 = 0.1198
X_e2 = 0.0625
delta2_init = calculate_initial_angle(P_m2, E_q2, X_d_prime2, X_e2)

# Gen3参数
P_m3 = 0.85
E_q3 = 1.2
X_d_prime3 = 0.1813
X_e3 = 0.0586
delta3_init = calculate_initial_angle(P_m3, E_q3, X_d_prime3, X_e3)

print(f"  Gen1初始功角: {delta1_init:.4f} rad = {np.degrees(delta1_init):.2f}°")
print(f"  Gen2初始功角: {delta2_init:.4f} rad = {np.degrees(delta2_init):.2f}°")
print(f"  Gen3初始功角: {delta3_init:.4f} rad = {np.degrees(delta3_init):.2f}°")

gen1 = SynchronousGenerator(
    name="gen1",
    H=23.64,
    damping=5.0,
    X_d=0.146,
    X_q=0.0969,
    X_d_prime=0.0608,
    T_d0_prime=8.96,
    X_e=0.0576,
    V_inf=1.0,
    delta_init=delta1_init,
    E_q_prime_init=E_q1
)
gen1.build()

gen2 = SynchronousGenerator(
    name="gen2",
    H=6.4,
    damping=5.0,
    X_d=0.8958,
    X_q=0.8645,
    X_d_prime=0.1198,
    T_d0_prime=6.0,
    X_e=0.0625,
    V_inf=1.0,
    delta_init=delta2_init,
    E_q_prime_init=E_q2
)
gen2.build()

gen3 = SynchronousGenerator(
    name="gen3",
    H=3.01,
    damping=5.0,
    X_d=1.3125,
    X_q=1.2578,
    X_d_prime=0.1813,
    T_d0_prime=5.89,
    X_e=0.0586,
    V_inf=1.0,
    delta_init=delta3_init,
    E_q_prime_init=E_q3
)
gen3.build()

print("[OK] 3台发电机创建完成")

print("\n[1.2] 创建3个AVR...")
avr1 = AVR(name="avr1", K_a=200.0, T_a=0.05, E_fd_init=2.0)
avr1.build()

avr2 = AVR(name="avr2", K_a=200.0, T_a=0.05, E_fd_init=2.0)
avr2.build()

avr3 = AVR(name="avr3", K_a=200.0, T_a=0.05, E_fd_init=2.0)
avr3.build()

print("[OK] 3个AVR创建完成")
print()

# ==============================================================================
# Part 2: 负荷、机械功率、参考电压、故障模块
# ==============================================================================
print("PART 2: 创建辅助模块")
print("-" * 80)

class Load(Module):
    """恒阻抗负荷"""
    def __init__(self, name: str, P_load: float = 1.0, Q_load: float = 0.35):
        super().__init__(name)
        self.add_output("P_L", P_load)
        self.add_output("Q_L", Q_load)
        self.add_param("P_load_set", P_load)
        self.add_param("Q_load_set", Q_load)
        self.add_equation("D(P_L) ~ (P_load_set - P_L) / 1e-6")
        self.add_equation("D(Q_L) ~ (Q_load_set - Q_L) / 1e-6")
        self.set_output("P_L")

load5 = Load(name="load5", P_load=1.25, Q_load=0.5)
load5.build()

load6 = Load(name="load6", P_load=0.9, Q_load=0.3)
load6.build()

load8 = Load(name="load8", P_load=1.0, Q_load=0.35)
load8.build()

# 机械功率
pm1 = Module("turbine1")
pm1.add_output("P_m", P_m1)
pm1.add_param("P_m_set", P_m1)
pm1.add_equation("D(P_m) ~ (P_m_set - P_m) / 1e-6")
pm1.set_output("P_m")
pm1.build()

pm2 = Module("turbine2")
pm2.add_output("P_m", P_m2)
pm2.add_param("P_m_set", P_m2)
pm2.add_equation("D(P_m) ~ (P_m_set - P_m) / 1e-6")
pm2.set_output("P_m")
pm2.build()

pm3 = Module("turbine3")
pm3.add_output("P_m", P_m3)
pm3.add_param("P_m_set", P_m3)
pm3.add_equation("D(P_m) ~ (P_m_set - P_m) / 1e-6")
pm3.set_output("P_m")
pm3.build()

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

# 故障模块
fault = Module("fault")
fault.add_output("V_fault", 1.0)
fault.add_param("V_fault_factor", 1.0)
fault.add_param("V_base", 1.0)
fault.add_equation("D(V_fault) ~ (V_base * V_fault_factor - V_fault) / 0.01")
fault.set_output("V_fault")
fault.build()

print("[2.1] 辅助模块创建完成")
print()

# ==============================================================================
# Part 3: 组装系统
# ==============================================================================
print("PART 3: 组装系统")
print("-" * 80)

system = System("ieee_9bus")

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

# 连接
system.connect(pm1.P_m >> gen1.P_m)
system.connect(avr1.E_fd_out >> gen1.E_fd)
system.connect(gen1.V_terminal >> avr1.V_t)
system.connect(vref1.V_ref >> avr1.V_ref)
system.connect(fault.V_fault >> gen1.V_t)

system.connect(pm2.P_m >> gen2.P_m)
system.connect(avr2.E_fd_out >> gen2.E_fd)
system.connect(gen2.V_terminal >> avr2.V_t)
system.connect(vref2.V_ref >> avr2.V_ref)
system.connect(fault.V_fault >> gen2.V_t)

system.connect(pm3.P_m >> gen3.P_m)
system.connect(avr3.E_fd_out >> gen3.E_fd)
system.connect(gen3.V_terminal >> avr3.V_t)
system.connect(vref3.V_ref >> avr3.V_ref)
system.connect(fault.V_fault >> gen3.V_t)

print(f"[3.1] 系统组装完成：{len(modules)}个模块，{len(system.connections)}个连接")
print()

# ==============================================================================
# Part 4: 定义故障事件（在t=2.0s引入，启动后1秒）
# ==============================================================================
print("PART 4: 定义故障事件")
print("-" * 80)

def fault_occurrence(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] Bus7 半金属性短路！V -> 0.35 p.u.")
    return {"fault.V_fault_factor": 0.35}

def fault_clearance(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] 故障切除！V -> 1.0 p.u.")
    return {"fault.V_fault_factor": 1.0}

system.add_event(at_time(2.0, fault_occurrence))  # 启动1秒后故障
system.add_event(at_time(2.1, fault_clearance))   # 故障持续0.1s

print("[4.1] 故障事件:")
print("      - t=2.0s: Bus7半金属性短路 (V -> 0.35 p.u.)")
print("      - t=2.1s: 故障切除 (持续0.1s)")
print()

# ==============================================================================
# Part 5: 配置数据探测器
# ==============================================================================
print("PART 5: 配置数据探测器")
print("-" * 80)

probes = {
    "gen1": DataProbe(
        variables=[
            str(gen1.delta_deg),
            str(gen1.omega),
            str(gen1.P_e)
        ],
        names=["Gen1_Angle_deg", "Gen1_Speed_rad_s", "Gen1_Power_pu"],
        description="Generator 1"
    ),
    "gen2": DataProbe(
        variables=[
            str(gen2.delta_deg),
            str(gen2.omega),
            str(gen2.P_e)
        ],
        names=["Gen2_Angle_deg", "Gen2_Speed_rad_s", "Gen2_Power_pu"],
        description="Generator 2"
    ),
    "gen3": DataProbe(
        variables=[
            str(gen3.delta_deg),
            str(gen3.omega),
            str(gen3.P_e)
        ],
        names=["Gen3_Angle_deg", "Gen3_Speed_rad_s", "Gen3_Power_pu"],
        description="Generator 3"
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

print(f"[5.1] 配置了 {len(probes)} 个数据探测器")
print()

# ==============================================================================
# Part 6: 编译和仿真
# ==============================================================================
print("PART 6: 编译系统并仿真")
print("-" * 80)

print("[6.1] 编译系统...")
try:
    system.compile()
    print("[OK] 系统编译成功")
except Exception as e:
    print(f"[ERROR] 编译失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[6.2] 运行仿真 (0-10s, dt=0.01s)...")
print("      仿真阶段:")
print("      - t=0-2s: 启动过程，系统稳定")
print("      - t=2.0s: Bus7半金属性短路")
print("      - t=2.1s: 故障切除")
print("      - t=2.1-10s: 系统恢复")
print()

simulator = Simulator(system)

try:
    result = simulator.run(
        t_span=(0.0, 10.0),
        dt=0.01,
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
# Part 7: 导出数据
# ==============================================================================
print("PART 7: 导出数据")
print("-" * 80)

csv_file = "ieee_9bus_fault_v2.csv"
result.to_csv(csv_file, include_probes=True)
print(f"[7.1] 数据导出: {csv_file}")

print("\n[7.2] 仿真摘要:")
result.print_summary()
print()

# ==============================================================================
# Part 8: 可视化
# ==============================================================================
print("PART 8: 绘制结果")
print("-" * 80)

gen1_df = result.get_probe_dataframe("gen1")
gen2_df = result.get_probe_dataframe("gen2")
gen3_df = result.get_probe_dataframe("gen3")
volt_df = result.get_probe_dataframe("voltages")

fig, axes = plt.subplots(4, 1, figsize=(14, 12))
fig.suptitle('IEEE 9节点系统短路故障仿真（带启动过程）\nIEEE 9-Bus System with Initialization',
             fontsize=14, fontweight='bold')

# 子图1: 功角
axes[0].plot(gen1_df['time'], gen1_df['Gen1_Angle_deg'], 'b-', linewidth=2, label='Gen1 (大型)')
axes[0].plot(gen2_df['time'], gen2_df['Gen2_Angle_deg'], 'r-', linewidth=2, label='Gen2 (中型)')
axes[0].plot(gen3_df['time'], gen3_df['Gen3_Angle_deg'], 'g-', linewidth=2, label='Gen3 (小型)')
axes[0].axvline(x=2.0, color='k', linestyle='--', alpha=0.5, label='故障')
axes[0].axvline(x=2.1, color='gray', linestyle='--', alpha=0.5, label='切除')
axes[0].set_ylabel('功角 (度)', fontsize=11)
axes[0].set_title('(a) 发电机功角对比', fontsize=11, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].legend(loc='best')

# 子图2: 角速度
axes[1].plot(gen1_df['time'], gen1_df['Gen1_Speed_rad_s'], 'b-', linewidth=2, label='Gen1')
axes[1].plot(gen2_df['time'], gen2_df['Gen2_Speed_rad_s'], 'r-', linewidth=2, label='Gen2')
axes[1].plot(gen3_df['time'], gen3_df['Gen3_Speed_rad_s'], 'g-', linewidth=2, label='Gen3')
axes[1].axvline(x=2.0, color='k', linestyle='--', alpha=0.5)
axes[1].axvline(x=2.1, color='gray', linestyle='--', alpha=0.5)
axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
axes[1].set_ylabel('角速度偏差 (rad/s)', fontsize=11)
axes[1].set_title('(b) 发电机角速度偏差对比', fontsize=11, fontweight='bold')
axes[1].grid(True, alpha=0.3)
axes[1].legend(loc='best')

# 子图3: 电磁功率
axes[2].plot(gen1_df['time'], gen1_df['Gen1_Power_pu'], 'b-', linewidth=2, label='Gen1 Pe')
axes[2].plot(gen2_df['time'], gen2_df['Gen2_Power_pu'], 'r-', linewidth=2, label='Gen2 Pe')
axes[2].plot(gen3_df['time'], gen3_df['Gen3_Power_pu'], 'g-', linewidth=2, label='Gen3 Pe')
axes[2].axhline(y=P_m1, color='b', linestyle='--', alpha=0.5, linewidth=1)
axes[2].axhline(y=P_m2, color='r', linestyle='--', alpha=0.5, linewidth=1)
axes[2].axhline(y=P_m3, color='g', linestyle='--', alpha=0.5, linewidth=1)
axes[2].axvline(x=2.0, color='k', linestyle='--', alpha=0.5)
axes[2].axvline(x=2.1, color='gray', linestyle='--', alpha=0.5)
axes[2].set_ylabel('功率 (p.u.)', fontsize=11)
axes[2].set_title('(c) 发电机电磁功率', fontsize=11, fontweight='bold')
axes[2].grid(True, alpha=0.3)
axes[2].legend(loc='best', ncol=2, fontsize=9)

# 子图4: 机端电压
axes[3].plot(volt_df['time'], volt_df['V1_pu'], 'b-', linewidth=2, label='Gen1 电压')
axes[3].plot(volt_df['time'], volt_df['V2_pu'], 'r-', linewidth=2, label='Gen2 电压')
axes[3].plot(volt_df['time'], volt_df['V3_pu'], 'g-', linewidth=2, label='Gen3 电压')
axes[3].axvline(x=2.0, color='k', linestyle='--', alpha=0.5)
axes[3].axvline(x=2.1, color='gray', linestyle='--', alpha=0.5)
axes[3].set_xlabel('时间 (s)', fontsize=11)
axes[3].set_ylabel('机端电压 (p.u.)', fontsize=11)
axes[3].set_title('(d) 发电机机端电压', fontsize=11, fontweight='bold')
axes[3].grid(True, alpha=0.3)
axes[3].legend(loc='best')

plt.tight_layout()

plot_file = "ieee_9bus_fault_v2.png"
plt.savefig(plot_file, dpi=300, bbox_inches='tight')
print(f"[8.1] 图形保存: {plot_file}")

plt.show()

print()
print("=" * 80)
print("仿真完成！")
print("=" * 80)
print()
print("主要结果:")
print(f"  Gen1 - 初始功角: {gen1_df['Gen1_Angle_deg'].iloc[0]:.2f}°, 最大功角: {gen1_df['Gen1_Angle_deg'].max():.2f}°")
print(f"  Gen2 - 初始功角: {gen2_df['Gen2_Angle_deg'].iloc[0]:.2f}°, 最大功角: {gen2_df['Gen2_Angle_deg'].max():.2f}°")
print(f"  Gen3 - 初始功角: {gen3_df['Gen3_Angle_deg'].iloc[0]:.2f}°, 最大功角: {gen3_df['Gen3_Angle_deg'].max():.2f}°")
print(f"  最小机端电压: {min(volt_df['V1_pu'].min(), volt_df['V2_pu'].min(), volt_df['V3_pu'].min()):.3f} p.u.")

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
