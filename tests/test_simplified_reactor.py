"""
简化的复杂系统测试 - 化学反应器多回路控制

展示功能：
1. 嵌套CompositeModule（温度和压力控制器）
2. MIMO StateSpace系统
3. 时间事件和连续事件
4. 前馈补偿
5. 多回路反馈控制
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from pycontroldae.blocks import (
    PID, Gain, Limiter, Sum,
    Step, Ramp, Sin,
    StateSpace, Integrator
)
from pycontroldae.core import System, Simulator, CompositeModule, at_time, when_condition

print("=" * 80)
print("化学反应器多回路控制测试（简化版）")
print("=" * 80)
print()

# ==============================================================================
# Part 1: 构建组合控制器
# ==============================================================================
print("PART 1: 构建嵌套CompositeModule")
print("-" * 80)

# 1.1 温度控制器（Composite: PID + Limiter）
print("\n[1.1] 温度控制器（CompositeModule）")
temp_controller = CompositeModule(name="temp_ctrl")

temp_pid = PID(name="temp_pid", Kp=3.0, Ki=0.8, Kd=0.3, integral_limit=100.0)
temp_limiter = Limiter(name="temp_lim", min_value=0.0, max_value=100.0)

temp_controller.add_module(temp_pid)
temp_controller.add_module(temp_limiter)
temp_controller.add_connection("temp_pid.output ~ temp_lim.input")
temp_controller.expose_input("error", "temp_pid.error")
temp_controller.expose_output("heating", "temp_lim.output")
print(f"      Created: {temp_controller}")

# 1.2 压力控制器（Composite: PID + Gain）
print("\n[1.2] 压力控制器（CompositeModule）")
press_controller = CompositeModule(name="press_ctrl")

press_pid = PID(name="press_pid", Kp=2.5, Ki=0.5, Kd=0.0, integral_limit=50.0)
press_gain = Gain(name="press_gain", K=0.8)

press_controller.add_module(press_pid)
press_controller.add_module(press_gain)
press_controller.add_connection("press_pid.output ~ press_gain.input")
press_controller.expose_input("error", "press_pid.error")
press_controller.expose_output("valve", "press_gain.output")
print(f"      Created: {press_controller}")

# 1.3 反应器MIMO模型
print("\n[1.3] 反应器动力学模型（StateSpace MIMO）")
A_reactor = np.array([
    [-0.5,  0.1,  0.05],  # Temperature dynamics
    [ 0.2, -0.8,  0.1 ],  # Pressure dynamics
    [ 0.05, 0.15, -1.0]   # Concentration dynamics
])

B_reactor = np.array([
    [1.0,  0.1],  # Heating and valve effect on temperature
    [0.2,  1.2],  # Heating and valve effect on pressure
    [0.1,  0.3]   # Heating and valve effect on concentration
])

C_reactor = np.array([
    [1.0, 0.0, 0.0],  # Temperature output
    [0.0, 1.0, 0.0]   # Pressure output
])

D_reactor = np.zeros((2, 2))

reactor_plant = StateSpace(
    name="reactor",
    A=A_reactor,
    B=B_reactor,
    C=C_reactor,
    D=D_reactor,
    initial_state=np.array([25.0, 5.0, 0.0])  # Initial: 25°C, 5 bar, 0 conc
)
print(f"      Created: {reactor_plant}")

# 1.4 前馈补偿器（Composite: Integrator + Gain）
print("\n[1.4] 前馈补偿器（CompositeModule）")
feedforward_comp = CompositeModule(name="feedforward")

ff_integrator = Integrator(name="ff_int", initial_value=0.0)
ff_gain = Gain(name="ff_gain", K=0.3)

feedforward_comp.add_module(ff_integrator)
feedforward_comp.add_module(ff_gain)
feedforward_comp.add_connection("ff_int.output ~ ff_gain.input")
feedforward_comp.expose_input("disturbance", "ff_int.input")
feedforward_comp.expose_output("compensation", "ff_gain.output")
print(f"      Created: {feedforward_comp}")

# 构建所有组合模块
print("\n[构建所有CompositeModule...]")
temp_controller.build()
print("  [OK] 温度控制器")
press_controller.build()
print("  [OK] 压力控制器")
reactor_plant.build()
print("  [OK] 反应器模型")
feedforward_comp.build()
print("  [OK] 前馈补偿器")
print("[SUCCESS] 所有组合模块构建成功!\n")

# ==============================================================================
# Part 2: 构建信号源
# ==============================================================================
print("\nPART 2: 构建参考信号和扰动")
print("-" * 80)

temp_setpoint = Step(name="temp_sp", amplitude=60.0, step_time=5.0)
temp_setpoint.set_output("signal")
temp_setpoint.build()
print("[2.1] 温度设定值: 60°C阶跃@t=5s")

press_setpoint = Ramp(name="press_sp", slope=0.5, start_time=2.0)
press_setpoint.set_output("signal")
press_setpoint.build()
print("[2.2] 压力设定值: 0.5 bar/s斜坡@t=2s")

disturbance = Sin(name="disturbance", amplitude=5.0, frequency=0.3)
disturbance.set_output("signal")
disturbance.build()
print("[2.3] 扰动信号: 正弦波 A=5.0, f=0.3 rad/s")
print("[SUCCESS] 信号源构建完成\n")

# ==============================================================================
# Part 3: 构建误差计算
# ==============================================================================
print("\nPART 3: 构建误差计算模块")
print("-" * 80)

temp_error_sum = Sum(name="temp_error", num_inputs=2, signs=[+1, -1])
temp_error_sum.build()
print("[3.1] 温度误差: SP - PV")

press_error_sum = Sum(name="press_error", num_inputs=2, signs=[+1, -1])
press_error_sum.build()
print("[3.2] 压力误差: SP - PV")

temp_control_sum = Sum(name="temp_control_sum", num_inputs=2, signs=[+1, +1])
temp_control_sum.build()
print("[3.3] 温度控制: FB + FF")
print("[SUCCESS] 误差计算模块完成\n")

# ==============================================================================
# Part 4: 组装系统
# ==============================================================================
print("\nPART 4: 组装完整系统")
print("-" * 80)

system = System("reactor_control")

modules = [
    temp_setpoint, press_setpoint, disturbance,
    temp_error_sum, press_error_sum, temp_control_sum,
    temp_controller, press_controller, feedforward_comp, reactor_plant
]

for mod in modules:
    system.add_module(mod)

print(f"[4.1] 添加了 {len(system.modules)} 个模块")

# ==============================================================================
# Part 5: 定义连接
# ==============================================================================
print("\nPART 5: 定义系统连接")
print("-" * 80)

connections = [
    "temp_sp.signal ~ temp_error.input1",
    "reactor.y1 ~ temp_error.input2",
    "temp_error.output ~ temp_ctrl.error",
    "temp_ctrl.heating ~ temp_control_sum.input1",
    "disturbance.signal ~ feedforward.disturbance",
    "feedforward.compensation ~ temp_control_sum.input2",
    "temp_control_sum.output ~ reactor.u1",
    "press_sp.signal ~ press_error.input1",
    "reactor.y2 ~ press_error.input2",
    "press_error.output ~ press_ctrl.error",
    "press_ctrl.valve ~ reactor.u2",
]

for conn in connections:
    system.connect(conn)

print(f"[5.1] 定义了 {len(system.connections)} 个连接")
print("[SUCCESS] 系统拓扑完成\n")

# ==============================================================================
# Part 6: 添加时间事件
# ==============================================================================
print("\nPART 6: 添加时间事件（增益调度）")
print("-" * 80)

def aggressive_temp_tuning(integrator):
    print("  [EVENT] t=15.0s: 激进温度调优")
    return {
        "temp_ctrl.temp_pid.Kp": 5.0,
        "temp_ctrl.temp_pid.Ki": 1.5,
        "temp_ctrl.temp_pid.Kd": 0.5
    }

system.add_event(at_time(15.0, aggressive_temp_tuning))
print("[6.1] 事件 @ t=15s: 增加温度控制器增益")

def conservative_press_tuning(integrator):
    print("  [EVENT] t=25.0s: 保守压力调优")
    return {
        "press_ctrl.press_pid.Kp": 1.5,
        "press_ctrl.press_pid.Ki": 0.3
    }

system.add_event(at_time(25.0, conservative_press_tuning))
print("[6.2] 事件 @ t=25s: 降低压力控制器增益")

def adjust_feedforward(integrator):
    print("  [EVENT] t=35.0s: 调整前馈增益")
    return {"feedforward.ff_gain.K": 0.5}

system.add_event(at_time(35.0, adjust_feedforward))
print("[6.3] 事件 @ t=35s: 增加前馈补偿增益")
print(f"[SUCCESS] {len(system.events)} 个时间事件\n")

# ==============================================================================
# Part 7: 添加连续事件
# ==============================================================================
print("\nPART 7: 添加连续事件（安全监控）")
print("-" * 80)

temp_high_limit = 75.0
event_flags = {"temp_high": False, "press_high": False}

def check_temp_high(u, t, integrator):
    return u[0] - temp_high_limit if len(u) > 0 else -1.0

def limit_heating(integrator):
    if not event_flags["temp_high"]:
        print(f"  [SAFETY] 温度超过 {temp_high_limit}°C! 限制加热")
        event_flags["temp_high"] = True
    return {"temp_ctrl.temp_lim.max_val": 50.0}

system.add_event(when_condition(check_temp_high, limit_heating, direction=1))
print(f"[7.1] 连续事件: 温度高限 ({temp_high_limit}°C)")

press_high_limit = 15.0

def check_press_high(u, t, integrator):
    return u[1] - press_high_limit if len(u) > 1 else -1.0

def reduce_press_gain(integrator):
    if not event_flags["press_high"]:
        print(f"  [SAFETY] 压力超过 {press_high_limit} bar! 降低增益")
        event_flags["press_high"] = True
    return {"press_ctrl.press_gain.K": 0.5}

system.add_event(when_condition(check_press_high, reduce_press_gain, direction=1))
print(f"[7.2] 连续事件: 压力高限 ({press_high_limit} bar)")
print(f"[SUCCESS] 总共 {len(system.events)} 个事件\n")

# ==============================================================================
# Part 8: 编译系统
# ==============================================================================
print("\nPART 8: 编译系统")
print("-" * 80)
print("应用 structural_simplify 进行DAE索引降低...")

try:
    compiled_system = system.compile()
    print("[SUCCESS] 系统编译成功!\n")
except Exception as e:
    print(f"[ERROR] 编译失败: {e}\n")
    sys.exit(1)

# ==============================================================================
# Part 9: 运行仿真
# ==============================================================================
print("\nPART 9: 运行仿真")
print("-" * 80)
print("时长: 0-50s, 求解器: Rodas5\n")

try:
    simulator = Simulator(system)
    times, values = simulator.run(
        t_span=(0.0, 50.0),
        dt=0.1,
        solver="Rodas5"
    )

    print(f"[SUCCESS] 仿真完成!")
    print(f"          时间点: {len(times)}")
    print(f"          状态数: {values.shape[1]}")
    print()
except Exception as e:
    print(f"[ERROR] 仿真失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Part 10: 可视化
# ==============================================================================
print("\nPART 10: 结果可视化")
print("-" * 80)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('化学反应器多回路控制 - CompositeModule演示', fontsize=14, fontweight='bold')

# 图1：所有状态
ax = axes[0, 0]
for i in range(min(10, values.shape[1])):
    ax.plot(times, values[:, i], label=f'State {i+1}', linewidth=1.2, alpha=0.8)
ax.axvline(x=5.0, color='r', linestyle='--', alpha=0.3, label='Temp SP')
ax.axvline(x=15.0, color='g', linestyle='--', alpha=0.3, label='Event 1')
ax.axvline(x=25.0, color='b', linestyle='--', alpha=0.3, label='Event 2')
ax.axvline(x=35.0, color='orange', linestyle='--', alpha=0.3, label='Event 3')
ax.set_xlabel('Time (s)')
ax.set_ylabel('State Values')
ax.set_title('系统状态演化')
ax.legend(fontsize=7, ncol=2)
ax.grid(True, alpha=0.3)

# 图2：主要状态
ax = axes[0, 1]
for i in range(min(6, values.shape[1])):
    ax.plot(times, values[:, i], linewidth=2, label=f'State {i+1}')
ax.set_xlabel('Time (s)')
ax.set_ylabel('State Values')
ax.set_title('主要状态详图')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# 图3：相平面
ax = axes[1, 0]
if values.shape[1] >= 2:
    ax.plot(values[:, 0], values[:, 1], linewidth=2, color='purple', alpha=0.7)
    ax.scatter(values[0, 0], values[0, 1], c='green', s=150, label='起点', zorder=5)
    ax.scatter(values[-1, 0], values[-1, 1], c='red', s=150, label='终点', zorder=5)
    ax.set_xlabel('State 1')
    ax.set_ylabel('State 2')
    ax.set_title('相空间轨迹')
    ax.legend()
    ax.grid(True, alpha=0.3)

# 图4：状态热图
ax = axes[1, 1]
im = ax.imshow(values.T[:min(15, values.shape[1]), :], aspect='auto', cmap='viridis', interpolation='nearest')
ax.set_xlabel('Time Index')
ax.set_ylabel('State Index')
ax.set_title('状态变量热图')
plt.colorbar(im, ax=ax)

plt.tight_layout()
plt.savefig('simplified_reactor_control.png', dpi=150)
print("[OK] 保存图像: simplified_reactor_control.png\n")

# ==============================================================================
# 总结
# ==============================================================================
print("=" * 80)
print("测试总结")
print("=" * 80)
print()
print("[OK] 所有功能成功演示!")
print()
print("演示的功能:")
print("  [OK] 嵌套CompositeModule（温度和压力控制器）")
print("  [OK] MIMO StateSpace模型（3状态，2输入，2输出）")
print("  [OK] 前馈补偿CompositeModule")
print("  [OK] 时间事件（3个增益调度事件）")
print("  [OK] 连续事件（2个安全限制事件）")
print("  [OK] 多回路反馈控制")
print("  [OK] 系统编译 structural_simplify")
print("  [OK] Rodas5求解器仿真")
print("  [OK] 事件驱动参数修改")
print()
print("系统统计:")
print(f"  模块: {len(system.modules)}")
print(f"  连接: {len(system.connections)}")
print(f"  事件: {len(system.events)}")
print(f"  状态: {values.shape[1]}")
print(f"  仿真点: {len(times)}")
print()
print("=" * 80)
print("测试完成成功!")
print("=" * 80)
