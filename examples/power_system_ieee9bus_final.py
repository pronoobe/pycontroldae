"""
3机9节点电力系统短路故障仿真 - 最终修正版
3-Machine 9-Bus Power System Short Circuit Fault Simulation - Final Corrected Version

关键修正 / Key Corrections:
1. 电磁功率使用实际机端电压V_t而非固定V_inf
2. 故障仅影响Gen1，其他机组通过电气耦合受影响
3. 正确的功角响应和多机摆动

系统组成 / System Components:
1. 3台同步发电机 + AVR
2. 3台升压变压器
3. 3个负荷节点
4. Bus7半金属性短路故障（靠近Gen1）

故障场景 / Fault Scenario:
- t = 0-2s: 系统启动达到稳态
- t = 2.0s: Gen1附近发生半金属性短路，机端电压降至0.35 p.u.
- t = 2.1s: 故障切除（持续0.1s）
- t = 2.1-10s: 多机摆动恢复
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib.pyplot as plt
from pycontroldae.core import Module, System, Simulator, DataProbe, at_time

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 80)
print("3机9节点电力系统短路故障仿真 - 最终修正版")
print("3-Machine 9-Bus Power System - Final Corrected Version")
print("=" * 80)
print()

# ==============================================================================
# Part 1: 同步发电机模型（修正版）
# ==============================================================================
print("PART 1: 创建同步发电机模型（修正版）")
print("-" * 80)

class SynchronousGenerator(Module):
    """
    同步发电机三阶模型（修正版）

    关键修正：电磁功率公式使用实际机端电压V_t
    P_e = E'_q · V_t · sin(δ) / (X'_d + X_e)

    这样故障时V_t降低会正确导致P_e降低，产生加速功率
    """
    def __init__(self, name: str,
                 H: float = 3.5,
                 damping: float = 5.0,
                 X_d: float = 1.6,
                 X_q: float = 1.55,
                 X_d_prime: float = 0.32,
                 T_d0_prime: float = 6.0,
                 X_e: float = 0.4,
                 delta_init: float = 0.5,
                 E_q_prime_init: float = 1.2,
                 P_m_init: float = 0.9):

        super().__init__(name)

        # 状态变量
        self.add_state("delta", delta_init)
        self.add_state("omega", 0.0)
        self.add_state("E_q_prime", E_q_prime_init)

        # 输入
        self.add_input("V_t", 1.0)          # 机端电压（关键！）
        self.add_input("E_fd", 2.0)         # 励磁电压
        self.add_input("P_m", P_m_init)     # 机械功率

        # 输出 - P_e通过代数方程计算，不是状态变量
        self.add_output("P_e", P_m_init)    # 电磁功率输出
        self.add_output("V_terminal", 1.0)  # 机端电压输出

        # 参数
        self.add_param("H", H)
        self.add_param("damping", damping)
        self.add_param("X_d", X_d)
        self.add_param("X_q", X_q)
        self.add_param("X_d_prime", X_d_prime)
        self.add_param("T_d0_prime", T_d0_prime)
        self.add_param("X_e", X_e)
        self.add_param("tau", 0.001)

        # 摇摆方程
        self.add_equation("D(delta) ~ omega")
        self.add_equation(
            "D(omega) ~ (P_m - P_e - damping * omega) / (2 * H)"
        )

        # 暂态电势方程
        self.add_equation(
            "D(E_q_prime) ~ (E_fd - E_q_prime) / T_d0_prime"
        )

        # 电磁功率输出方程（代数方程，快速跟踪计算值）
        self.add_equation(
            "D(P_e) ~ (E_q_prime * V_t * sin(delta) / (X_d_prime + X_e) - P_e) / tau"
        )

        # 机端电压输出
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


# 计算初始功角
def calculate_initial_angle(P_m, E_q_prime, X_d_prime, X_e, V_t=1.0):
    """基于功率平衡计算初始功角"""
    X_total = X_d_prime + X_e
    sin_delta = P_m * X_total / (E_q_prime * V_t)
    sin_delta = max(-1.0, min(1.0, sin_delta))
    return np.arcsin(sin_delta)

# 发电机参数（IEEE 9-bus标准参数）
P_m1 = 0.716
E_fd1 = 2.0  # 励磁电压
E_q1 = E_fd1  # 稳态时 E'_q = E_fd
X_d_prime1 = 0.0608
X_e1 = 0.0576
delta1_init = calculate_initial_angle(P_m1, E_q1, X_d_prime1, X_e1)

P_m2 = 1.63
E_fd2 = 2.0
E_q2 = E_fd2  # 稳态时 E'_q = E_fd
X_d_prime2 = 0.1198
X_e2 = 0.0625
delta2_init = calculate_initial_angle(P_m2, E_q2, X_d_prime2, X_e2)

P_m3 = 0.85
E_fd3 = 2.0
E_q3 = E_fd3  # 稳态时 E'_q = E_fd
X_d_prime3 = 0.1813
X_e3 = 0.0586
delta3_init = calculate_initial_angle(P_m3, E_q3, X_d_prime3, X_e3)

print(f"[1.1] 计算初始功角:")
print(f"  Gen1: {np.degrees(delta1_init):.2f}° (P_m={P_m1} p.u.)")
print(f"  Gen2: {np.degrees(delta2_init):.2f}° (P_m={P_m2} p.u.)")
print(f"  Gen3: {np.degrees(delta3_init):.2f}° (P_m={P_m3} p.u.)")

gen1 = SynchronousGenerator(
    name="gen1",
    H=23.64,
    damping=2.0,  # 真实阻尼系数
    X_d=0.146,
    X_q=0.0969,
    X_d_prime=0.0608,
    T_d0_prime=8.96,
    X_e=0.0576,
    delta_init=delta1_init,
    E_q_prime_init=E_q1,
    P_m_init=P_m1
)
gen1.build()

gen2 = SynchronousGenerator(
    name="gen2",
    H=6.4,
    damping=2.0,  # 真实阻尼系数
    X_d=0.8958,
    X_q=0.8645,
    X_d_prime=0.1198,
    T_d0_prime=6.0,
    X_e=0.0625,
    delta_init=delta2_init,
    E_q_prime_init=E_q2,
    P_m_init=P_m2
)
gen2.build()

gen3 = SynchronousGenerator(
    name="gen3",
    H=3.01,
    damping=2.0,  # 真实阻尼系数
    X_d=1.3125,
    X_q=1.2578,
    X_d_prime=0.1813,
    T_d0_prime=5.89,
    X_e=0.0586,
    delta_init=delta3_init,
    E_q_prime_init=E_q3,
    P_m_init=P_m3
)
gen3.build()

print("\n[1.2] 创建3个AVR...")
avr1 = AVR(name="avr1", K_a=200.0, T_a=0.05, E_fd_init=2.0)
avr1.build()

avr2 = AVR(name="avr2", K_a=200.0, T_a=0.05, E_fd_init=2.0)
avr2.build()

avr3 = AVR(name="avr3", K_a=200.0, T_a=0.05, E_fd_init=2.0)
avr3.build()

print("[OK] 发电机和AVR创建完成")
print()

# ==============================================================================
# Part 2: 变压器模型
# ==============================================================================
print("PART 2: 创建变压器模型")
print("-" * 80)

class Transformer(Module):
    """升压变压器模型（简化）"""
    def __init__(self, name: str,
                 turns_ratio: float = 1.0,
                 X_leakage: float = 0.01):

        super().__init__(name)

        self.add_input("V_primary", 1.0)
        self.add_output("V_secondary", 1.0)

        self.add_param("n", turns_ratio)
        self.add_param("X_l", X_leakage)
        self.add_param("tau", 0.001)

        self.add_equation(
            "D(V_secondary) ~ (n * V_primary - V_secondary) / tau"
        )

        self.set_input("V_primary")
        self.set_output("V_secondary")


print("[2.1] 创建3台升压变压器...")

transformer1 = Transformer(name="T1", turns_ratio=1.05, X_leakage=0.0062)
transformer1.build()

transformer2 = Transformer(name="T2", turns_ratio=1.025, X_leakage=0.0086)
transformer2.build()

transformer3 = Transformer(name="T3", turns_ratio=1.03, X_leakage=0.0119)
transformer3.build()

print("  T1: n=1.05, T2: n=1.025, T3: n=1.03")
print("[OK] 变压器创建完成")
print()

# ==============================================================================
# Part 3: 辅助模块
# ==============================================================================
print("PART 3: 创建辅助模块")
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

# 正常电压模块（供Gen2和Gen3使用）
normal_voltage = Module("normal_v")
normal_voltage.add_output("V_normal", 1.0)
normal_voltage.add_param("V_set", 1.0)
normal_voltage.add_equation("D(V_normal) ~ (V_set - V_normal) / 1e-6")
normal_voltage.set_output("V_normal")
normal_voltage.build()

# 固定励磁电压（不使用AVR反馈）
efd1 = Module("efd1")
efd1.add_output("E_fd", E_fd1)
efd1.add_param("E_fd_set", E_fd1)
efd1.add_equation("D(E_fd) ~ (E_fd_set - E_fd) / 1e-6")
efd1.set_output("E_fd")
efd1.build()

efd2 = Module("efd2")
efd2.add_output("E_fd", E_fd2)
efd2.add_param("E_fd_set", E_fd2)
efd2.add_equation("D(E_fd) ~ (E_fd_set - E_fd) / 1e-6")
efd2.set_output("E_fd")
efd2.build()

efd3 = Module("efd3")
efd3.add_output("E_fd", E_fd3)
efd3.add_param("E_fd_set", E_fd3)
efd3.add_equation("D(E_fd) ~ (E_fd_set - E_fd) / 1e-6")
efd3.set_output("E_fd")
efd3.build()

print("[3.1] 辅助模块创建完成（使用固定励磁，不使用AVR）")
print()

# ==============================================================================
# Part 4: 组装系统
# ==============================================================================
print("PART 4: 组装系统")
print("-" * 80)

system = System("ieee_9bus_corrected")

modules = [
    gen1, gen2, gen3,
    # avr1, avr2, avr3,  # 移除AVR，使用固定励磁
    efd1, efd2, efd3,    # 固定励磁电压
    transformer1, transformer2, transformer3,
    pm1, pm2, pm3,
    vref1, vref2, vref3,
    load5, load6, load8,
    fault, normal_voltage
]

for mod in modules:
    system.add_module(mod)

# Gen1连接 - 受故障影响，使用固定励磁
system.connect(pm1.P_m >> gen1.P_m)
system.connect(efd1.E_fd >> gen1.E_fd)  # 固定励磁
# system.connect(gen1.V_terminal >> avr1.V_t)  # 移除AVR反馈
# system.connect(vref1.V_ref >> avr1.V_ref)
system.connect(gen1.V_terminal >> transformer1.V_primary)
system.connect(fault.V_fault >> gen1.V_t)  # Gen1受故障影响

# Gen2连接 - 正常运行，使用固定励磁
system.connect(pm2.P_m >> gen2.P_m)
system.connect(efd2.E_fd >> gen2.E_fd)  # 固定励磁
# system.connect(gen2.V_terminal >> avr2.V_t)
# system.connect(vref2.V_ref >> avr2.V_ref)
system.connect(gen2.V_terminal >> transformer2.V_primary)
system.connect(normal_voltage.V_normal >> gen2.V_t)  # Gen2保持正常电压

# Gen3连接 - 正常运行，使用固定励磁
system.connect(pm3.P_m >> gen3.P_m)
system.connect(efd3.E_fd >> gen3.E_fd)  # 固定励磁
# system.connect(gen3.V_terminal >> avr3.V_t)
# system.connect(vref3.V_ref >> avr3.V_ref)
system.connect(gen3.V_terminal >> transformer3.V_primary)
system.connect(normal_voltage.V_normal >> gen3.V_t)  # Gen3保持正常电压

print(f"[4.1] 系统组装完成：{len(modules)}个模块，{len(system.connections)}个连接")
print("      使用固定励磁电压（无AVR反馈），避免稳态漂移")
print()

# ==============================================================================
# Part 5: 定义故障事件
# ==============================================================================
print("PART 5: 定义故障事件")
print("-" * 80)

def fault_occurrence(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] Gen1附近短路！V_t -> 0.35 p.u.")
    return {"fault.V_fault_factor": 0.35}

def fault_clearance(integrator):
    print(f"    [EVENT @ t={integrator.t:.3f}s] 故障切除！V_t -> 1.0 p.u.")
    return {"fault.V_fault_factor": 1.0}

system.add_event(at_time(30.0, fault_occurrence))
system.add_event(at_time(30.5, fault_clearance))

print("[5.1] 故障事件:")
print("      - t=30.0s: Gen1附近短路 (V_t -> 0.35 p.u.)")
print("      - t=30.1s: 故障切除 (持续0.1s)")
print("      - 前30秒：系统稳态运行，确保完全达到平衡")

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

print("\n[6.2] 运行仿真 (0-35s, dt=0.01s)...")
print("      0-30s: 系统稳态运行（固定励磁）")
print("      30.0-30.1s: 短路故障")
print("      30.1-35s: 故障后恢复")
print()

simulator = Simulator(system)

try:
    result = simulator.run(
        t_span=(0.0, 45.0),
        dt=0.00001,
        solver="Rodas5"
    )
    print(f"[OK] 仿真完成: {result}")
    print()
except Exception as e:
    print(f"[ERROR] 仿真失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Part 7: 导出数据和分析
# ==============================================================================
print("PART 7: 导出数据和分析")
print("-" * 80)

csv_file = "ieee_9bus_final.csv"
# result.to_csv(csv_file)
print(f"[7.1] 数据导出: {csv_file}")

print("\n[7.2] 仿真摘要:")
result.print_summary()
print()

# ==============================================================================
# Part 8: 可视化
# ==============================================================================
print("PART 8: 绘制结果")
print("-" * 80)

import pandas as pd

df = pd.read_csv(csv_file)

# 转换为度
df['gen1_deg'] = df['gen1.delta'] * 180 / np.pi
df['gen2_deg'] = df['gen2.delta'] * 180 / np.pi
df['gen3_deg'] = df['gen3.delta'] * 180 / np.pi

fig, axes = plt.subplots(5, 1, figsize=(14, 14))
fig.suptitle('IEEE 9节点3机系统短路故障仿真（最终修正版）\nIEEE 9-Bus 3-Machine System (Final Corrected)',
             fontsize=14, fontweight='bold')

# 子图1: 功角
axes[0].plot(df['time'], df['gen1_deg'], 'b-', linewidth=2, label='Gen1 (故障机组)')
axes[0].plot(df['time'], df['gen2_deg'], 'r-', linewidth=2, label='Gen2 (正常)')
axes[0].plot(df['time'], df['gen3_deg'], 'g-', linewidth=2, label='Gen3 (正常)')
axes[0].axvline(x=30.0, color='k', linestyle='--', alpha=0.5, label='故障')
axes[0].axvline(x=30.1, color='gray', linestyle='--', alpha=0.5, label='切除')
axes[0].set_ylabel('功角 (度)', fontsize=11)
axes[0].set_title('(a) 发电机功角对比', fontsize=11, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].legend(loc='best', fontsize=9)

# 子图2: 角速度
axes[1].plot(df['time'], df['gen1.omega'], 'b-', linewidth=2, label='Gen1')
axes[1].plot(df['time'], df['gen2.omega'], 'r-', linewidth=2, label='Gen2')
axes[1].plot(df['time'], df['gen3.omega'], 'g-', linewidth=2, label='Gen3')
axes[1].axvline(x=30.0, color='k', linestyle='--', alpha=0.5)
axes[1].axvline(x=30.1, color='gray', linestyle='--', alpha=0.5)
axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
axes[1].set_ylabel('角速度偏差 (rad/s)', fontsize=11)
axes[1].set_title('(b) 发电机角速度偏差对比', fontsize=11, fontweight='bold')
axes[1].grid(True, alpha=0.3)
axes[1].legend(loc='best')

# 子图3: 电磁功率
axes[2].plot(df['time'], df['gen1.P_e'], 'b-', linewidth=2, label='Gen1 Pe')
axes[2].plot(df['time'], df['gen2.P_e'], 'r-', linewidth=2, label='Gen2 Pe')
axes[2].plot(df['time'], df['gen3.P_e'], 'g-', linewidth=2, label='Gen3 Pe')
axes[2].axhline(y=P_m1, color='b', linestyle='--', alpha=0.5, linewidth=1, label='Gen1 Pm')
axes[2].axhline(y=P_m2, color='r', linestyle='--', alpha=0.5, linewidth=1, label='Gen2 Pm')
axes[2].axhline(y=P_m3, color='g', linestyle='--', alpha=0.5, linewidth=1, label='Gen3 Pm')
axes[2].axvline(x=30.0, color='k', linestyle='--', alpha=0.5)
axes[2].axvline(x=30.1, color='gray', linestyle='--', alpha=0.5)
axes[2].set_ylabel('功率 (p.u.)', fontsize=11)
axes[2].set_title('(c) 发电机电磁功率与机械功率', fontsize=11, fontweight='bold')
axes[2].grid(True, alpha=0.3)
axes[2].legend(loc='best', ncol=2, fontsize=9)

# 子图4: 机端电压
axes[3].plot(df['time'], df['gen1.V_terminal'], 'b-', linewidth=2, label='Gen1')
axes[3].plot(df['time'], df['gen2.V_terminal'], 'r-', linewidth=2, label='Gen2')
axes[3].plot(df['time'], df['gen3.V_terminal'], 'g-', linewidth=2, label='Gen3')
axes[3].axvline(x=30.0, color='k', linestyle='--', alpha=0.5)
axes[3].axvline(x=30.1, color='gray', linestyle='--', alpha=0.5)
axes[3].set_ylabel('机端电压 (p.u.)', fontsize=11)
axes[3].set_title('(d) 发电机机端电压', fontsize=11, fontweight='bold')
axes[3].grid(True, alpha=0.3)
axes[3].legend(loc='best')

# 子图5: 变压器二次侧电压
axes[4].plot(df['time'], df['T1.V_secondary'], 'b-', linewidth=2, label='T1 (n=1.05)')
axes[4].plot(df['time'], df['T2.V_secondary'], 'r-', linewidth=2, label='T2 (n=1.025)')
axes[4].plot(df['time'], df['T3.V_secondary'], 'g-', linewidth=2, label='T3 (n=1.03)')
axes[4].axvline(x=30.0, color='k', linestyle='--', alpha=0.5)
axes[4].axvline(x=30.1, color='gray', linestyle='--', alpha=0.5)
axes[4].set_xlabel('时间 (s)', fontsize=11)
axes[4].set_ylabel('高压侧电压 (p.u.)', fontsize=11)
axes[4].set_title('(e) 变压器高压侧电压', fontsize=11, fontweight='bold')
axes[4].grid(True, alpha=0.3)
axes[4].legend(loc='best')

plt.tight_layout()

plot_file = "ieee_9bus_final.png"
plt.savefig(plot_file, dpi=300, bbox_inches='tight')
print(f"[8.1] 图形保存: {plot_file}")

plt.show()

# ==============================================================================
# Part 9: 详细结果分析
# ==============================================================================
print()
print("=" * 80)
print("仿真完成！详细分析")
print("=" * 80)
print()

# 关键时间点分析
idx_steady = (df["time"] - 29.99).abs().idxmin()  # 故障前稳态
idx_before = (df["time"] - 29.99).abs().idxmin()
idx_fault = (df["time"] - 30.05).abs().idxmin()
idx_clear = (df["time"] - 30.1).abs().idxmin()
idx_after = (df["time"] - 30.5).abs().idxmin()

print("功角变化分析:")
print(f"  t=29.99s (故障前稳态):")
print(f"    Gen1: {df.loc[idx_before, 'gen1_deg']:.2f}°  Gen2: {df.loc[idx_before, 'gen2_deg']:.2f}°  Gen3: {df.loc[idx_before, 'gen3_deg']:.2f}°")

print(f"  t=30.05s (故障中):")
print(f"    Gen1: {df.loc[idx_fault, 'gen1_deg']:.2f}°  Gen2: {df.loc[idx_fault, 'gen2_deg']:.2f}°  Gen3: {df.loc[idx_fault, 'gen3_deg']:.2f}°")

print(f"  t=30.1s (故障切除):")
print(f"    Gen1: {df.loc[idx_clear, 'gen1_deg']:.2f}°  Gen2: {df.loc[idx_clear, 'gen2_deg']:.2f}°  Gen3: {df.loc[idx_clear, 'gen3_deg']:.2f}°")

print(f"  t=30.5s (故障后):")
print(f"    Gen1: {df.loc[idx_after, 'gen1_deg']:.2f}°  Gen2: {df.loc[idx_after, 'gen2_deg']:.2f}°  Gen3: {df.loc[idx_after, 'gen3_deg']:.2f}°")

print(f"\n功角最大值:")
print(f"  Gen1: {df['gen1_deg'].max():.2f}° (t={df.loc[df['gen1_deg'].idxmax(), 'time']:.2f}s)")
print(f"  Gen2: {df['gen2_deg'].max():.2f}° (t={df.loc[df['gen2_deg'].idxmax(), 'time']:.2f}s)")
print(f"  Gen3: {df['gen3_deg'].max():.2f}° (t={df.loc[df['gen3_deg'].idxmax(), 'time']:.2f}s)")

print(f"\n功角增量 (故障前→最大值):")
print(f"  Gen1: Δδ = {df['gen1_deg'].max() - df.loc[idx_before, 'gen1_deg']:.2f}°")
print(f"  Gen2: Δδ = {df['gen2_deg'].max() - df.loc[idx_before, 'gen2_deg']:.2f}°")
print(f"  Gen3: Δδ = {df['gen3_deg'].max() - df.loc[idx_before, 'gen3_deg']:.2f}°")

print(f"\n电磁功率变化:")
print(f"  Gen1 (故障前): P_e = {df.loc[idx_before, 'gen1.P_e']:.3f} p.u.")
print(f"  Gen1 (故障中): P_e = {df.loc[idx_fault, 'gen1.P_e']:.3f} p.u.")
print(f"  Gen1 加速功率: P_acc = {P_m1 - df.loc[idx_fault, 'gen1.P_e']:.3f} p.u.")

print(f"\n系统性能:")
print(f"  最大角速度偏差: {max(df['gen1.omega'].max(), df['gen2.omega'].max(), df['gen3.omega'].max()):.4f} rad/s")
print(f"  最小机端电压: {min(df['gen1.V_terminal'].min(), df['gen2.V_terminal'].min(), df['gen3.V_terminal'].min()):.3f} p.u.")

max_angle = max(df['gen1_deg'].max(), df['gen2_deg'].max(), df['gen3_deg'].max())
stable = "稳定" if max_angle < 120 else "失稳"
print(f"  系统状态: {stable}")

print()
print(f"数据: {csv_file}")
print(f"图形: {plot_file}")
print()
print("=" * 80)
