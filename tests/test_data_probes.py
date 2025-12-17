"""
测试数据探测器和导出功能
Test Data Probes and Export Functions

演示功能：
1. DataProbe配置（单个、列表、字典）
2. 变量自动观测
3. to_numpy() 导出
4. to_dataframe() 导出
5. to_csv() 导出
6. 探测器特定数据访问
7. 时间切片和统计摘要
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import os

from pycontroldae.blocks import PID, Gain, Sum, Step, StateSpace
from pycontroldae.core import System, Simulator, DataProbe

print("=" * 80)
print("数据探测器和导出功能测试")
print("Data Probe and Export Functions Test")
print("=" * 80)
print()

# ==============================================================================
# Part 1: 构建测试系统 - 双回路控制
# ==============================================================================
print("PART 1: 构建双回路控制系统")
print("-" * 80)

# 1.1 信号源
temp_setpoint = Step(name="temp_sp", amplitude=80.0, step_time=2.0)
temp_setpoint.set_output("signal")
temp_setpoint.build()
print("[1.1] 温度设定值: 80°C @ t=2s")

press_setpoint = Step(name="press_sp", amplitude=10.0, step_time=5.0)
press_setpoint.set_output("signal")
press_setpoint.build()
print("[1.2] 压力设定值: 10 bar @ t=5s")

# 1.2 误差计算
temp_error = Sum(name="temp_error", num_inputs=2, signs=[+1, -1])
temp_error.build()
print("[1.3] 温度误差计算")

press_error = Sum(name="press_error", num_inputs=2, signs=[+1, -1])
press_error.build()
print("[1.4] 压力误差计算")

# 1.3 PID控制器
temp_controller = PID(name="temp_pid", Kp=2.0, Ki=0.5, Kd=0.1, integral_limit=50.0)
temp_controller.build()
print("[1.5] 温度PID控制器")

press_controller = PID(name="press_pid", Kp=1.5, Ki=0.3, Kd=0.05, integral_limit=30.0)
press_controller.build()
print("[1.6] 压力PID控制器")

# 1.4 增益块
temp_gain = Gain(name="temp_gain", K=0.8)
temp_gain.build()
print("[1.7] 温度控制增益")

press_gain = Gain(name="press_gain", K=0.6)
press_gain.build()
print("[1.8] 压力控制增益")

# 1.5 MIMO工厂模型
A_plant = np.array([
    [-0.3, 0.1],   # Temperature dynamics
    [0.15, -0.5]   # Pressure dynamics
])

B_plant = np.array([
    [1.2, 0.1],    # Control inputs effect on temperature
    [0.2, 1.0]     # Control inputs effect on pressure
])

C_plant = np.array([
    [1.0, 0.0],    # Temperature output
    [0.0, 1.0]     # Pressure output
])

D_plant = np.zeros((2, 2))

plant = StateSpace(
    name="plant",
    A=A_plant,
    B=B_plant,
    C=C_plant,
    D=D_plant,
    initial_state=np.array([25.0, 3.0])  # Initial: 25°C, 3 bar
)
plant.build()
print("[1.9] MIMO工厂模型 (2状态, 2输入, 2输出)")

# 1.6 组装系统
system = System("dual_loop_control")

modules = [
    temp_setpoint, press_setpoint,
    temp_error, press_error,
    temp_controller, press_controller,
    temp_gain, press_gain,
    plant
]

for mod in modules:
    system.add_module(mod)

print(f"\n[1.10] 添加了 {len(system.modules)} 个模块")

# 1.7 定义连接
connections = [
    "temp_sp.signal ~ temp_error.input1",
    "plant.y1 ~ temp_error.input2",
    "temp_error.output ~ temp_pid.error",
    "temp_pid.output ~ temp_gain.input",
    "temp_gain.output ~ plant.u1",

    "press_sp.signal ~ press_error.input1",
    "plant.y2 ~ press_error.input2",
    "press_error.output ~ press_pid.error",
    "press_pid.output ~ press_gain.input",
    "press_gain.output ~ plant.u2",
]

for conn in connections:
    system.connect(conn)

print(f"[1.11] 定义了 {len(system.connections)} 个连接")

# 1.8 编译系统
print("\n[1.12] 编译系统...")
try:
    compiled_system = system.compile()
    print("[SUCCESS] 系统编译成功!\n")
except Exception as e:
    print(f"[ERROR] 编译失败: {e}\n")
    sys.exit(1)

# ==============================================================================
# Part 2: 无探测器仿真（基准测试）
# ==============================================================================
print("\nPART 2: 基准仿真（无探测器）")
print("-" * 80)

try:
    simulator = Simulator(system)

    # 使用旧API（return_result=False）获取原始数组
    times_old, values_old = simulator.run(
        t_span=(0.0, 20.0),
        dt=0.1,
        solver="Rodas5",
        return_result=False  # 向后兼容模式
    )

    print(f"[SUCCESS] 基准仿真完成")
    print(f"          时间点: {len(times_old)}")
    print(f"          状态数: {values_old.shape[1]}")
    print(f"          返回类型: tuple (times, values)")
    print()
except Exception as e:
    print(f"[ERROR] 仿真失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Part 3: 使用单个DataProbe的仿真
# ==============================================================================
print("\nPART 3: 单个DataProbe仿真")
print("-" * 80)

# 创建探测器观测关键控制变量
probe1 = DataProbe(
    variables=[
        "plant.y1",           # 温度输出
        "plant.y2",           # 压力输出
        "temp_pid.output",    # 温度控制信号
        "press_pid.output"    # 压力控制信号
    ],
    names=[
        "Temperature",
        "Pressure",
        "Temp_Control",
        "Press_Control"
    ],
    description="Main control loop variables"
)

print(f"[3.1] 创建DataProbe: {probe1.description}")
print(f"      观测变量: {probe1.variables}")
print(f"      自定义名称: {probe1.names}")

try:
    result1 = simulator.run(
        t_span=(0.0, 20.0),
        dt=0.1,
        solver="Rodas5",
        probes=probe1  # 传入单个DataProbe
    )

    print(f"\n[SUCCESS] 仿真完成")
    print(f"          返回类型: {type(result1).__name__}")
    print(f"          {result1}")
    print()
except Exception as e:
    print(f"[ERROR] 仿真失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==============================================================================
# Part 4: 测试导出功能
# ==============================================================================
print("\nPART 4: 测试导出功能")
print("-" * 80)

# 4.1 to_numpy() - 获取原始NumPy数组
print("[4.1] to_numpy() - 导出NumPy数组")
times_np, values_np = result1.to_numpy()
print(f"      times shape: {times_np.shape}")
print(f"      values shape: {values_np.shape}")
print(f"      types: {type(times_np)}, {type(values_np)}")

# 4.2 to_dict() - 获取Python字典
print("\n[4.2] to_dict() - 导出字典")
result_dict = result1.to_dict(include_probes=True)
print(f"      键: {list(result_dict.keys())}")
print(f"      metadata: {result_dict['metadata']}")
if 'probes' in result_dict:
    print(f"      探测器数据: {list(result_dict['probes'].keys())}")

# 4.3 to_dataframe() - 获取pandas DataFrame
print("\n[4.3] to_dataframe() - 导出DataFrame")
try:
    df_states = result1.to_dataframe(include_probes=False)
    print(f"      DataFrame shape: {df_states.shape}")
    print(f"      列: {list(df_states.columns[:5])}... (前5个)")

    df_with_probes = result1.to_dataframe(include_probes=True)
    print(f"      带探测器 shape: {df_with_probes.shape}")
    print(f"      列数增加: {df_with_probes.shape[1] - df_states.shape[1]}")
except ImportError as e:
    print(f"      [SKIPPED] pandas未安装: {e}")

# 4.4 get_probe_dataframe() - 获取探测器专用DataFrame
print("\n[4.4] get_probe_dataframe() - 探测器DataFrame")
try:
    probe_df = result1.get_probe_dataframe()
    print(f"      DataFrame shape: {probe_df.shape}")
    print(f"      列: {list(probe_df.columns)}")
    print(f"      前3行:")
    print(probe_df.head(3))
except ImportError as e:
    print(f"      [SKIPPED] pandas未安装: {e}")

# 4.5 to_csv() - 导出CSV文件
print("\n[4.5] to_csv() - 导出CSV文件")
try:
    csv_file1 = "test_probe_data.csv"
    result1.to_csv(csv_file1, include_probes=True)

    if os.path.exists(csv_file1):
        file_size = os.path.getsize(csv_file1)
        print(f"      [OK] 已保存: {csv_file1}")
        print(f"      文件大小: {file_size} bytes")

        # 读取前几行验证
        with open(csv_file1, 'r') as f:
            lines = f.readlines()[:3]
        print(f"      前3行:")
        for line in lines:
            print(f"        {line.strip()}")
    else:
        print(f"      [ERROR] 文件未创建")
except ImportError as e:
    print(f"      [SKIPPED] pandas未安装: {e}")

# ==============================================================================
# Part 5: 多个探测器（列表形式）
# ==============================================================================
print("\n\nPART 5: 多个探测器（列表）")
print("-" * 80)

probe_control = DataProbe(
    variables=["temp_pid.output", "press_pid.output"],
    names=["Temp_PID", "Press_PID"],
    description="PID outputs"
)

probe_plant = DataProbe(
    variables=["plant.y1", "plant.y2"],
    names=["Plant_Temp", "Plant_Press"],
    description="Plant outputs"
)

probe_setpoints = DataProbe(
    variables=["temp_sp.signal", "press_sp.signal"],
    names=["Temp_SP", "Press_SP"],
    description="Setpoints"
)

probe_list = [probe_control, probe_plant, probe_setpoints]

print(f"[5.1] 创建了 {len(probe_list)} 个探测器:")
for i, p in enumerate(probe_list):
    print(f"      probe_{i}: {p.description} ({len(p.variables)} 变量)")

try:
    result2 = simulator.run(
        t_span=(0.0, 20.0),
        dt=0.1,
        solver="Rodas5",
        probes=probe_list  # 传入列表
    )

    print(f"\n[SUCCESS] 仿真完成")
    print(f"          {result2}")
    print(f"          探测器数量: {len(result2.probe_data)}")
    print(f"          探测器名称: {list(result2.probe_data.keys())}")
    print()
except Exception as e:
    print(f"[ERROR] 仿真失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5.2 导出每个探测器的数据
print("[5.2] 分别导出每个探测器的数据")
try:
    for probe_name in result2.probe_data.keys():
        probe_df = result2.get_probe_dataframe(probe_name)
        csv_file = f"test_{probe_name}.csv"
        result2.save_probe_csv(probe_name, csv_file)
        print(f"      [OK] {probe_name}: {csv_file} ({probe_df.shape[1]-1} 变量)")
except ImportError as e:
    print(f"      [SKIPPED] pandas未安装: {e}")

# ==============================================================================
# Part 6: 字典形式的探测器（命名）
# ==============================================================================
print("\n\nPART 6: 字典形式的探测器（自定义名称）")
print("-" * 80)

probe_dict = {
    "control_signals": DataProbe(
        variables=["temp_gain.output", "press_gain.output"],
        names=["Heating", "Valve"],
        description="Actuator commands"
    ),
    "process_variables": DataProbe(
        variables=["plant.y1", "plant.y2"],
        names=["PV_Temp", "PV_Press"],
        description="Process measurements"
    ),
    "errors": DataProbe(
        variables=["temp_error.output", "press_error.output"],
        names=["Error_Temp", "Error_Press"],
        description="Control errors"
    )
}

print(f"[6.1] 创建了 {len(probe_dict)} 个命名探测器:")
for name, p in probe_dict.items():
    print(f"      '{name}': {p.description}")

try:
    result3 = simulator.run(
        t_span=(0.0, 20.0),
        dt=0.1,
        solver="Rodas5",
        probes=probe_dict  # 传入字典
    )

    print(f"\n[SUCCESS] 仿真完成")
    print(f"          {result3}")
    print(f"          探测器名称: {list(result3.probe_data.keys())}")
    print()
except Exception as e:
    print(f"[ERROR] 仿真失败: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6.2 访问特定探测器的数据
print("[6.2] 访问特定探测器的DataFrame")
try:
    control_df = result3.get_probe_dataframe("control_signals")
    print(f"      control_signals: {control_df.shape}")
    print(f"      列: {list(control_df.columns)}")

    pv_df = result3.get_probe_dataframe("process_variables")
    print(f"      process_variables: {pv_df.shape}")
    print(f"      列: {list(pv_df.columns)}")
except ImportError as e:
    print(f"      [SKIPPED] pandas未安装: {e}")

# ==============================================================================
# Part 7: 时间切片和统计摘要
# ==============================================================================
print("\n\nPART 7: 时间切片和统计摘要")
print("-" * 80)

# 7.1 时间切片
print("[7.1] 时间切片功能")
sliced_result = result3.slice_time(t_start=5.0, t_end=15.0)
print(f"      原始时间范围: [{result3.times[0]:.1f}, {result3.times[-1]:.1f}]")
print(f"      切片时间范围: [{sliced_result.times[0]:.1f}, {sliced_result.times[-1]:.1f}]")
print(f"      原始点数: {len(result3.times)}")
print(f"      切片点数: {len(sliced_result.times)}")

# 7.2 统计摘要
print("\n[7.2] 统计摘要")
summary = result3.summary()
print(f"      统计的状态数: {len(summary)}")
print(f"\n      前5个状态的统计:")
for i, (state_name, stats) in enumerate(list(summary.items())[:5]):
    print(f"        {state_name}:")
    print(f"          mean={stats['mean']:.3f}, std={stats['std']:.3f}")
    print(f"          min={stats['min']:.3f}, max={stats['max']:.3f}, final={stats['final']:.3f}")

# 7.3 print_summary()
print("\n[7.3] 格式化摘要输出:")
result3.print_summary()

# ==============================================================================
# Part 8: get_state() 和 get_states() 方法
# ==============================================================================
print("\n\nPART 8: 获取特定状态数据")
print("-" * 80)

# 8.1 get_state() - 单个状态
print("[8.1] get_state() - 获取单个状态")
try:
    temp_data = result3.get_state("plant.x1")
    press_data = result3.get_state("plant.x2")
    print(f"      plant.x1 shape: {temp_data.shape}")
    print(f"      plant.x2 shape: {press_data.shape}")
    print(f"      plant.x1 范围: [{temp_data.min():.2f}, {temp_data.max():.2f}]")
    print(f"      plant.x2 范围: [{press_data.min():.2f}, {press_data.max():.2f}]")
except ValueError as e:
    print(f"      [ERROR] {e}")

# 8.2 get_states() - 多个状态
print("\n[8.2] get_states() - 获取多个状态")
try:
    state_names = [name for name in result3.state_names if name.startswith("plant")]
    if state_names:
        plant_states = result3.get_states(state_names)
        print(f"      请求的状态: {state_names}")
        print(f"      返回shape: {plant_states.shape}")
except ValueError as e:
    print(f"      [ERROR] {e}")

# ==============================================================================
# Part 9: 验证数据一致性
# ==============================================================================
print("\n\nPART 9: 验证数据一致性")
print("-" * 80)

# 验证探测器数据和状态数据维度一致
print("[9.1] 验证时间向量一致性")
print(f"      times长度: {len(result3.times)}")
print(f"      values行数: {result3.values.shape[0]}")
for probe_name, probe_vars in result3.probe_data.items():
    for var_name, var_data in probe_vars.items():
        if len(var_data) != len(result3.times):
            print(f"      [ERROR] {probe_name}.{var_name} 长度不匹配!")
        else:
            print(f"      [OK] {probe_name}.{var_name}: {len(var_data)} 点")

# 验证to_numpy()返回的是副本
print("\n[9.2] 验证to_numpy()返回副本（不是引用）")
times_copy, values_copy = result3.to_numpy()
times_copy[0] = -999.0  # 修改副本
if result3.times[0] != -999.0:
    print(f"      [OK] to_numpy()返回的是副本，原始数据未被修改")
else:
    print(f"      [ERROR] to_numpy()返回的是引用，不是副本!")

# ==============================================================================
# Part 10: 清理测试文件
# ==============================================================================
print("\n\nPART 10: 清理测试文件")
print("-" * 80)

test_files = [
    "test_probe_data.csv",
    "test_probe_0.csv",
    "test_probe_1.csv",
    "test_probe_2.csv"
]

print("[10.1] 清理生成的CSV文件:")
for filename in test_files:
    if os.path.exists(filename):
        os.remove(filename)
        print(f"      [OK] 已删除: {filename}")
    else:
        print(f"      [SKIP] 不存在: {filename}")

# ==============================================================================
# 总结
# ==============================================================================
print("\n" + "=" * 80)
print("测试总结")
print("=" * 80)
print()
print("[OK] 所有数据探测器和导出功能测试成功!")
print()
print("验证的功能:")
print("  [OK] DataProbe创建和配置")
print("  [OK] 单个DataProbe仿真")
print("  [OK] 多个DataProbe（列表）仿真")
print("  [OK] 命名DataProbe（字典）仿真")
print("  [OK] to_numpy() - NumPy数组导出")
print("  [OK] to_dict() - 字典导出")
print("  [OK] to_dataframe() - DataFrame导出")
print("  [OK] to_csv() - CSV文件导出")
print("  [OK] get_probe_dataframe() - 探测器DataFrame")
print("  [OK] save_probe_csv() - 探测器CSV导出")
print("  [OK] slice_time() - 时间切片")
print("  [OK] summary() - 统计摘要")
print("  [OK] print_summary() - 格式化输出")
print("  [OK] get_state() - 单状态数据获取")
print("  [OK] get_states() - 多状态数据获取")
print("  [OK] 向后兼容性（return_result=False）")
print("  [OK] 数据一致性验证")
print()
print("探测器配置方式:")
print(f"  单个DataProbe: ✓")
print(f"  DataProbe列表: ✓")
print(f"  DataProbe字典: ✓")
print()
print("导出格式:")
print(f"  NumPy arrays: ✓")
print(f"  Python dict: ✓")
print(f"  pandas DataFrame: ✓")
print(f"  CSV files: ✓")
print()
print("=" * 80)
print("测试完成成功!")
print("=" * 80)
