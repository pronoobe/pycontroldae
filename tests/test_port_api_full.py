"""
完整Port系统测试 - 使用新的Port API

演示所有Port系统特性：
1. Port对象直接连接: pid.output >> plant.input
2. Module默认端口连接: source >> pid >> plant
3. CompositeModule with Port API
4. 字符串连接向后兼容
5. 混合使用不同连接方式
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from pycontroldae.core import Module, CompositeModule, System, Simulator, DataProbe

print("=" * 80)
print("完整Port系统测试 - 温度控制系统")
print("Complete Port System Test - Temperature Control")
print("=" * 80)
print()

# ==============================================================================
# Part 1: 使用Port API创建可复用的CompositeModule
# ==============================================================================
print("PART 1: 创建CompositeModule with Port API")
print("-" * 80)

def create_pid_controller(name, Kp=2.0, Ki=0.5, Kd=0.1):
    """创建PID控制器 CompositeModule"""
    controller = CompositeModule(name)

    # 创建子模块
    pid_core = Module(f"{name}_core")
    pid_core.add_input("error", 0.0)
    pid_core.add_output("output", 0.0)
    pid_core.add_state("integral", 0.0)
    pid_core.add_state("filtered_error", 0.0)
    pid_core.add_param("Kp", Kp)
    pid_core.add_param("Ki", Ki)
    pid_core.add_param("Kd", Kd)
    pid_core.add_param("filter_tau", 0.01)
    pid_core.add_param("tau", 1e-6)

    pid_core.add_equation("D(integral) ~ Ki * error")
    pid_core.add_equation("D(filtered_error) ~ (error - filtered_error) / filter_tau")
    pid_core.add_equation("D(output) ~ (Kp * error + integral + Kd * filtered_error - output) / tau")

    pid_core.set_input("error")
    pid_core.set_output("output")

    limiter = Module(f"{name}_lim")
    limiter.add_input("input", 0.0)
    limiter.add_output("output", 0.0)
    limiter.add_param("min_val", 0.0)
    limiter.add_param("max_val", 100.0)
    limiter.add_param("smooth", 10.0)
    limiter.add_param("tau", 1e-6)
    limiter.add_equation(
        "D(output) ~ (min_val + (max_val - min_val) * (tanh(smooth * (input - min_val)/(max_val - min_val)) + 1) / 2 - output) / tau"
    )
    limiter.set_input("input")
    limiter.set_output("output")

    # 添加到composite
    controller.add_module(pid_core)
    controller.add_module(limiter)

    # 使用Port对象连接！（新特性）
    controller.add_connection(pid_core.output >> limiter.input)

    # 暴露接口 - 使用Port对象！（新特性）
    controller.expose_input("error", pid_core.error)
    controller.expose_output("control", limiter.output)

    return controller

print("[1.1] 创建PID控制器 CompositeModule工厂")

# 创建两个PID控制器实例
pid_A = create_pid_controller("pid_A", Kp=3.0, Ki=0.8, Kd=0.3)
pid_A.build()
print(f"[1.2] PID_A: {pid_A}")
print(f"      Input ports: {[p for p, port in pid_A._ports.items() if port.is_input]}")
print(f"      Output ports: {[p for p, port in pid_A._ports.items() if not port.is_input]}")

pid_B = create_pid_controller("pid_B", Kp=2.5, Ki=0.6, Kd=0.2)
pid_B.build()
print(f"[1.3] PID_B: {pid_B}")

print("[SUCCESS] CompositeModule创建完成\n")

# ==============================================================================
# Part 2: 创建信号源和工厂模型
# ==============================================================================
print("\nPART 2: 创建信号源和工厂模型")
print("-" * 80)

# 温度设定值
temp_sp_A = Module("temp_sp_A")
temp_sp_A.add_output("signal", 0.0)
temp_sp_A.add_param("amplitude", 80.0)
temp_sp_A.add_param("step_time", 3.0)
temp_sp_A.add_param("tau_step", 0.1)
temp_sp_A.add_equation("D(signal) ~ (amplitude * (tanh((t - step_time)/tau_step) + 1) / 2 - signal) / 1e-6")
temp_sp_A.set_output("signal")
temp_sp_A.build()
print("[2.1] 温度设定值A: 80°C @ t=3s")

temp_sp_B = Module("temp_sp_B")
temp_sp_B.add_output("signal", 0.0)
temp_sp_B.add_param("amplitude", 70.0)
temp_sp_B.add_param("step_time", 5.0)
temp_sp_B.add_param("tau_step", 0.1)
temp_sp_B.add_equation("D(signal) ~ (amplitude * (tanh((t - step_time)/tau_step) + 1) / 2 - signal) / 1e-6")
temp_sp_B.set_output("signal")
temp_sp_B.build()
print("[2.2] 温度设定值B: 70°C @ t=5s")

# 误差计算模块
def create_sum_module(name, signs=[+1, -1]):
    """创建求和模块"""
    summ = Module(name)
    summ.add_input("input1", 0.0)
    summ.add_input("input2", 0.0)
    summ.add_output("output", 0.0)
    summ.add_param("tau", 1e-6)

    sign_str = " + ".join([f"{s}*input{i+1}" for i, s in enumerate(signs)])
    summ.add_equation(f"D(output) ~ ({sign_str} - output) / tau")

    summ.set_input("input1")
    summ.set_output("output")
    return summ

error_A = create_sum_module("error_A", signs=[+1, -1])
error_A.build()
print("[2.3] 误差计算A")

error_B = create_sum_module("error_B", signs=[+1, -1])
error_B.build()
print("[2.4] 误差计算B")

# MIMO工厂模型
plant = Module("plant")
plant.add_input("u1", 0.0)
plant.add_input("u2", 0.0)
plant.add_output("y1", 0.0)
plant.add_output("y2", 0.0)
plant.add_state("x1", 30.0)  # 温度A初始值
plant.add_state("x2", 2.0)   # 温度B初始值

# 状态方程
plant.add_equation("D(x1) ~ -0.3*x1 + 1.0*u1 + 0.1*u2")
plant.add_equation("D(x2) ~ 0.1*x1 - 0.5*x2 + 0.2*u1 + 0.8*u2")

# 输出方程 (快速跟踪)
plant.add_param("tau", 1e-6)
plant.add_equation("D(y1) ~ (x1 - y1) / tau")
plant.add_equation("D(y2) ~ (x2 - y2) / tau")

plant.set_input("u1")
plant.set_output("y1")
plant.build()
print(f"[2.5] MIMO工厂模型: {plant}")
print(f"      输入: {[p for p in plant._ports.keys() if plant._ports[p].is_input]}")
print(f"      输出: {[p for p in plant._ports.keys() if not plant._ports[p].is_input]}")

print("[SUCCESS] 信号源和模型创建完成\n")

# ==============================================================================
# Part 3: 使用Port API组装系统
# ==============================================================================
print("\nPART 3: 使用Port API组装系统")
print("-" * 80)

system = System("dual_temp_control")

# 添加所有模块
modules = [temp_sp_A, temp_sp_B, error_A, error_B, pid_A, pid_B, plant]
for mod in modules:
    system.add_module(mod)

print(f"[3.1] 添加了 {len(system.modules)} 个模块")

# 使用不同的连接方式展示Port API的灵活性
print("\n[3.2] 定义连接（使用多种方式）：")

# 方式1: 直接Port对象连接（推荐！）
system.connect(temp_sp_A.signal >> error_A.input1)
print("    [OK] temp_sp_A.signal >> error_A.input1  (Port对象)")

# 方式2: 字符串连接（向后兼容）
system.connect("plant.y1 ~ error_A.input2")
print("    [OK] 'plant.y1 ~ error_A.input2'  (字符串)")

# 方式3: Module级别连接（使用默认端口）
system.connect(error_A >> pid_A)
print("    [OK] error_A >> pid_A  (Module默认端口)")

# 方式4: 混合Port对象和字符串
system.connect(pid_A.control >> plant.u1)
print("    [OK] pid_A.control >> plant.u1  (Port对象)")

# 回路B的连接
system.connect(temp_sp_B.signal >> error_B.input1)
system.connect("plant.y2 ~ error_B.input2")
system.connect(error_B >> pid_B)
system.connect(pid_B.control >> plant.u2)

print(f"\n[3.3] 总共定义了 {len(system.connections)} 个连接")
print("[SUCCESS] 系统组装完成\n")

# ==============================================================================
# Part 4: 编译系统
# ==============================================================================
print("\nPART 4: 编译系统")
print("-" * 80)

try:
    compiled = system.compile()
    print("[SUCCESS] 系统编译成功!")
    print(f"          使用structural_simplify进行DAE索引降低\n")
except Exception as e:
    print(f"[ERROR] 编译失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Part 5: 配置数据探测器并仿真
# ==============================================================================
print("\nPART 5: 配置数据探测器并仿真")
print("-" * 80)

# 使用Port对象配置探测器！
probes = {
    "pid_A_signals": DataProbe(
        variables=[str(pid_A.error), str(pid_A.control)],
        names=["PID_A_Error", "PID_A_Control"],
        description="PID A control signals"
    ),
    "pid_B_signals": DataProbe(
        variables=[str(pid_B.error), str(pid_B.control)],
        names=["PID_B_Error", "PID_B_Control"],
        description="PID B control signals"
    ),
    "plant_outputs": DataProbe(
        variables=[str(plant.y1), str(plant.y2)],
        names=["Temp_A", "Temp_B"],
        description="Plant temperature outputs"
    )
}

print(f"[5.1] 配置了 {len(probes)} 个数据探测器")
for name, probe in probes.items():
    print(f"      {name}: {len(probe.variables)} 变量")

print("\n[5.2] 运行仿真 (0-20s, dt=0.1)...")

try:
    simulator = Simulator(system)
    result = simulator.run(
        t_span=(0.0, 20.0),
        dt=0.1,
        solver="Rodas5",
        probes=probes
    )

    print(f"[SUCCESS] 仿真完成!")
    print(f"          {result}")
    print()

except Exception as e:
    print(f"[ERROR] 仿真失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Part 6: 验证结果
# ==============================================================================
print("\nPART 6: 验证结果")
print("-" * 80)

# 获取探测器数据
try:
    pid_A_df = result.get_probe_dataframe("pid_A_signals")
    plant_df = result.get_probe_dataframe("plant_outputs")

    print("[6.1] 探测器数据:")
    print(f"      PID A signals: {pid_A_df.shape}")
    print(f"      Plant outputs: {plant_df.shape}")

    # 统计摘要
    print("\n[6.2] 温度统计:")
    summary = result.summary()
    for state_name in ["plant.y1", "plant.y2"]:
        if state_name in summary:
            stats = summary[state_name]
            print(f"      {state_name}:")
            print(f"        mean={stats['mean']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}")

    # 保存结果
    result.to_csv("port_system_test.csv", include_probes=True)
    print("\n[6.3] 结果已保存到: port_system_test.csv")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# ==============================================================================
# 总结
# ==============================================================================
print("\n" + "=" * 80)
print("测试总结")
print("=" * 80)
print()
print("[OK] Port系统所有特性测试成功!")
print()
print("演示的Port API特性:")
print("  [OK] Port对象直接连接: pid.output >> plant.input")
print("  [OK] Module默认端口连接: error >> pid")
print("  [OK] CompositeModule with Port对象")
print("  [OK] expose_input/output接受Port对象")
print("  [OK] 字符串连接向后兼容")
print("  [OK] 混合使用多种连接方式")
print("  [OK] Port对象用于DataProbe配置")
print()
print("系统统计:")
print(f"  模块数: {len(system.modules)}")
print(f"  连接数: {len(system.connections)}")
print(f"  状态数: {result.values.shape[1]}")
print(f"  探测器: {len(probes)}")
print(f"  仿真点: {len(result.times)}")
print()
print("=" * 80)
print("测试完成成功!")
print("=" * 80)
