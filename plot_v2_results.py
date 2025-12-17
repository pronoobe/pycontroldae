"""
绘制3机9节点系统仿真结果（从状态变量直接读取）
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 读取CSV数据
df = pd.read_csv('ieee_9bus_fault_v2.csv')

# 将弧度转换为度
df['gen1_angle_deg'] = df['gen1.delta'] * 180 / np.pi
df['gen2_angle_deg'] = df['gen2.delta'] * 180 / np.pi
df['gen3_angle_deg'] = df['gen3.delta'] * 180 / np.pi

fig, axes = plt.subplots(4, 1, figsize=(14, 12))
fig.suptitle('IEEE 9节点系统短路故障仿真（带启动过程）\nIEEE 9-Bus System with Initialization',
             fontsize=14, fontweight='bold')

# 子图1: 功角
axes[0].plot(df['time'], df['gen1_angle_deg'], 'b-', linewidth=2, label='Gen1 (大型)')
axes[0].plot(df['time'], df['gen2_angle_deg'], 'r-', linewidth=2, label='Gen2 (中型)')
axes[0].plot(df['time'], df['gen3_angle_deg'], 'g-', linewidth=2, label='Gen3 (小型)')
axes[0].axvline(x=2.0, color='k', linestyle='--', alpha=0.5, label='故障')
axes[0].axvline(x=2.1, color='gray', linestyle='--', alpha=0.5, label='切除')
axes[0].set_ylabel('功角 (度)', fontsize=11)
axes[0].set_title('(a) 发电机功角对比', fontsize=11, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].legend(loc='best')

# 子图2: 角速度
axes[1].plot(df['time'], df['gen1.omega'], 'b-', linewidth=2, label='Gen1')
axes[1].plot(df['time'], df['gen2.omega'], 'r-', linewidth=2, label='Gen2')
axes[1].plot(df['time'], df['gen3.omega'], 'g-', linewidth=2, label='Gen3')
axes[1].axvline(x=2.0, color='k', linestyle='--', alpha=0.5)
axes[1].axvline(x=2.1, color='gray', linestyle='--', alpha=0.5)
axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
axes[1].set_ylabel('角速度偏差 (rad/s)', fontsize=11)
axes[1].set_title('(b) 发电机角速度偏差对比', fontsize=11, fontweight='bold')
axes[1].grid(True, alpha=0.3)
axes[1].legend(loc='best')

# 子图3: 电磁功率
axes[2].plot(df['time'], df['gen1.P_e'], 'b-', linewidth=2, label='Gen1 Pe')
axes[2].plot(df['time'], df['gen2.P_e'], 'r-', linewidth=2, label='Gen2 Pe')
axes[2].plot(df['time'], df['gen3.P_e'], 'g-', linewidth=2, label='Gen3 Pe')
axes[2].axhline(y=0.716, color='b', linestyle='--', alpha=0.5, linewidth=1, label='Gen1 Pm')
axes[2].axhline(y=1.63, color='r', linestyle='--', alpha=0.5, linewidth=1, label='Gen2 Pm')
axes[2].axhline(y=0.85, color='g', linestyle='--', alpha=0.5, linewidth=1, label='Gen3 Pm')
axes[2].axvline(x=2.0, color='k', linestyle='--', alpha=0.5)
axes[2].axvline(x=2.1, color='gray', linestyle='--', alpha=0.5)
axes[2].set_ylabel('功率 (p.u.)', fontsize=11)
axes[2].set_title('(c) 发电机电磁功率', fontsize=11, fontweight='bold')
axes[2].grid(True, alpha=0.3)
axes[2].legend(loc='best', ncol=2, fontsize=9)

# 子图4: 机端电压
axes[3].plot(df['time'], df['gen1.V_terminal'], 'b-', linewidth=2, label='Gen1 电压')
axes[3].plot(df['time'], df['gen2.V_terminal'], 'r-', linewidth=2, label='Gen2 电压')
axes[3].plot(df['time'], df['gen3.V_terminal'], 'g-', linewidth=2, label='Gen3 电压')
axes[3].axvline(x=2.0, color='k', linestyle='--', alpha=0.5)
axes[3].axvline(x=2.1, color='gray', linestyle='--', alpha=0.5)
axes[3].set_xlabel('时间 (s)', fontsize=11)
axes[3].set_ylabel('机端电压 (p.u.)', fontsize=11)
axes[3].set_title('(d) 发电机机端电压', fontsize=11, fontweight='bold')
axes[3].grid(True, alpha=0.3)
axes[3].legend(loc='best')

plt.tight_layout()
plt.savefig('ieee_9bus_fault_v2_corrected.png', dpi=300, bbox_inches='tight')

print("=" * 80)
print("重新绘制完成！")
print("=" * 80)
print()
print("从状态变量直接读取的结果:")
print(f"  Gen1 - 初始功角: {df['gen1_angle_deg'].iloc[100]:.2f}°, 最大功角: {df['gen1_angle_deg'].max():.2f}°")
print(f"  Gen2 - 初始功角: {df['gen2_angle_deg'].iloc[100]:.2f}°, 最大功角: {df['gen2_angle_deg'].max():.2f}°")
print(f"  Gen3 - 初始功角: {df['gen3_angle_deg'].iloc[100]:.2f}°, 最大功角: {df['gen3_angle_deg'].max():.2f}°")
print(f"  Gen1 - 故障后最大角速度: {df['gen1.omega'].max():.4f} rad/s")
print(f"  Gen2 - 故障后最大角速度: {df['gen2.omega'].max():.4f} rad/s")
print(f"  Gen3 - 故障后最大角速度: {df['gen3.omega'].max():.4f} rad/s")
print(f"  最小机端电压: {min(df['gen1.V_terminal'].min(), df['gen2.V_terminal'].min(), df['gen3.V_terminal'].min()):.3f} p.u.")
print()
print("图形已保存: ieee_9bus_fault_v2_corrected.png")
print("=" * 80)

plt.show()
