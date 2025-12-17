# 电力系统仿真示例
# Power System Simulation Examples

本目录包含使用 pycontroldae 进行电力系统仿真的完整示例。

This directory contains complete examples of power system simulation using pycontroldae.

## 📁 文件说明 / Files

### `power_system_fault_complete.py` ⭐ 推荐 / Recommended

**完整的单机无限大系统短路故障仿真（含励磁系统）**

**Complete SMIB Short Circuit Fault Simulation with Excitation System**

#### 系统组成 / System Components:

1. **同步发电机** (Synchronous Generator)
   - 三阶简化模型
   - 状态：功角 δ、角速度 ω、交轴暂态电势 E'q
   - 包含完整的摇摆方程和电磁暂态

2. **自动电压调节器 AVR** (Automatic Voltage Regulator)
   - 快速励磁系统
   - 高增益反馈控制
   - 带限幅保护

3. **故障模拟模块** (Fault Module)
   - 通过降低机端电压模拟三相短路
   - 可配置故障严重程度

#### 仿真场景 / Simulation Scenario:

- **t = 0 ~ 1.0s**: 系统稳态运行
- **t = 1.0s**: 三相短路故障发生，机端电压降至 0.2 p.u.
- **t = 1.15s**: 故障切除，电压恢复
- **t = 1.15 ~ 5.0s**: 系统恢复稳定

#### 主要特性展示 / Key Features Demonstrated:

✅ **Port API 连接** - 使用新的 Port 对象进行模块连接
```python
system.connect(avr.E_fd_out >> generator.E_fd)
system.connect(generator.V_terminal >> avr.V_t)
```

✅ **事件系统** - 时间触发的参数变化
```python
system.add_event(at_time(1.0, fault_occurrence))
system.add_event(at_time(1.15, fault_clearance))
```

✅ **数据探测器** - 灵活的信号监测
```python
probes = {
    "generator": DataProbe(
        variables=[str(generator.delta_deg), str(generator.omega)],
        names=["Power_Angle_deg", "Speed_Deviation_rad_s"]
    )
}
```

✅ **数据导出** - CSV 格式导出完整仿真数据

✅ **可视化** - Matplotlib 绘制专业图表

#### 运行方法 / How to Run:

```bash
python examples/power_system_fault_complete.py
```

#### 输出文件 / Output Files:

- `smib_avr_fault.csv` - 完整仿真数据（1000+ 时间点）
- `smib_avr_fault.png` - 包含4个子图的可视化结果：
  - (a) 发电机功角 δ
  - (b) 角速度偏差 ω
  - (c) 电磁功率与机械功率
  - (d) 机端电压与励磁电压

#### 预期结果 / Expected Results:

- ✅ 故障期间功角快速增加（30° → 34°）
- ✅ 故障期间机端电压骤降（1.0 → 0.2 p.u.）
- ✅ AVR 快速响应，励磁电压上升（2.0 → 4.9 p.u.）
- ✅ 故障切除后系统恢复稳定
- ✅ 系统保持同步稳定性

---

### `power_system_fault.py`

**基础版本（不含励磁系统）**

**Basic Version (Without Excitation System)**

这是一个简化版本，不包含 AVR，仅用于教学演示。推荐使用 `power_system_fault_complete.py`。

This is a simplified version without AVR, for educational purposes only. `power_system_fault_complete.py` is recommended.

---

## 🎓 技术要点 / Technical Highlights

### 1. 同步发电机建模 / Generator Modeling

使用标准的三阶模型（Third-Order Model）：

```python
# 摇摆方程 Swing Equation
D(delta) ~ omega
D(omega) ~ (P_m - P_e - D*omega) / (2*H)

# 暂态电势方程 Transient EMF Equation
D(E_q_prime) ~ (E_fd - E_q_prime - (X_d - X_d_prime)*I_d) / T_d0_prime

# 电磁功率 Electromagnetic Power
P_e = E_q_prime * V_inf * sin(delta) / (X_d_prime + X_e)
```

### 2. AVR 动态 / AVR Dynamics

```python
# 电压误差 Voltage Error
V_error = V_ref - V_t

# 励磁电压（带限幅）Field Voltage with Limiting
D(E_fd) ~ (K_a * V_error - E_fd) / T_a
```

### 3. 数值稳定性技巧 / Numerical Stability Tips

- ✅ 使用快速跟踪方程避免代数约束
- ✅ 使用 `tanh` 函数实现软限幅
- ✅ Rodas5 求解器处理刚性方程
- ✅ 合理的时间步长（dt = 0.005s）

---

## 📊 参数说明 / Parameter Description

### 发电机参数 / Generator Parameters

| 参数 | 值 | 说明 |
|------|-----|------|
| H | 3.5 s | 惯性时间常数 |
| D | 5.0 | 阻尼系数 |
| X_d | 1.6 p.u. | 直轴同步电抗 |
| X_q | 1.55 p.u. | 交轴同步电抗 |
| X_d' | 0.32 p.u. | 直轴暂态电抗 |
| T_d0' | 6.0 s | 直轴开路时间常数 |
| X_e | 0.4 p.u. | 外部电抗（线路） |

### AVR 参数 / AVR Parameters

| 参数 | 值 | 说明 |
|------|-----|------|
| K_a | 200.0 | AVR 增益 |
| T_a | 0.05 s | AVR 时间常数 |
| E_fd_max | 5.0 p.u. | 励磁上限 |
| E_fd_min | 0.0 p.u. | 励磁下限 |

---

## 🔧 自定义仿真 / Customization

### 改变故障严重程度 / Change Fault Severity

```python
# 更严重的故障 More severe fault
def fault_occurrence(integrator):
    return {"fault.V_fault_factor": 0.1}  # 降到 10%

# 较轻的故障 Less severe fault
def fault_occurrence(integrator):
    return {"fault.V_fault_factor": 0.5}  # 降到 50%
```

### 改变故障持续时间 / Change Fault Duration

```python
system.add_event(at_time(1.0, fault_occurrence))   # 故障发生
system.add_event(at_time(1.2, fault_clearance))    # 延长到 1.2s 切除
```

### 改变AVR增益 / Change AVR Gain

```python
avr = AVR(
    name="avr",
    K_a=400.0,  # 增加增益，更快响应
    T_a=0.02    # 减小时间常数
)
```

---

## 📚 扩展阅读 / Further Reading

### 电力系统稳定性 / Power System Stability

- **暂态稳定性** (Transient Stability)：短路故障后发电机能否保持同步
- **小干扰稳定性** (Small-Signal Stability)：小扰动下系统的阻尼特性
- **电压稳定性** (Voltage Stability)：系统维持可接受电压水平的能力

### 关键技术概念 / Key Technical Concepts

1. **功角方程** (Swing Equation):
   ```
   2H·dω/dt = P_m - P_e - D·ω
   dδ/dt = ω
   ```
   其中 H 为惯性时间常数，D 为阻尼系数

2. **暂态电势方程** (Transient EMF):
   ```
   T'_d0·dE'_q/dt = E_fd - E'_q - (X_d - X'_d)·I_d
   ```

3. **电磁功率** (Electromagnetic Power):
   ```
   P_e = E'_q · V · sin(δ) / (X'_d + X_e)
   ```

4. **AVR动态** (AVR Dynamics):
   ```
   T_a·dE_fd/dt = K_a·(V_ref - V_t) - E_fd
   ```

5. **变压器模型** (Transformer Model):
   ```
   V_secondary = n · V_primary
   ```
   其中 n 为变比（简化模型，忽略漏抗压降）

### 推荐文献 / Recommended References

1. Kundur, P. "Power System Stability and Control" (1994)
   - 电力系统稳定性分析的经典教材

2. Sauer, P. W., Pai, M. A. "Power System Dynamics and Stability" (1998)
   - 详细的数学建模和分析方法

3. Machowski, J., et al. "Power System Dynamics: Stability and Control" (2008)
   - 包含大量实际案例和仿真示例

4. IEEE Tutorial on "Power System Stabilizers"
   - PSS设计和调试指南

---

## ⚡ 性能说明 / Performance Notes

- **仿真时间**: ~10-15秒（包括 Julia 初始化）
- **数据点**: 1000+ 时间点
- **求解器**: Rodas5（自动步长控制）
- **精度**: 相对误差 < 1e-6

---

## 🐛 常见问题 / Troubleshooting

### Q: 仿真结果全是 0 或直线？
**A**: 检查以下几点：
1. ✅ 初始状态值是否合理（功角应在 20-50° 范围）
2. ✅ 是否包含励磁系统（AVR）
3. ✅ 故障事件是否正确触发
4. ✅ 机械功率和电磁功率是否匹配

### Q: 系统失稳怎么办？
**A**: 可能的解决方法：
1. 增加阻尼系数 D
2. 缩短故障持续时间
3. 减轻故障严重程度
4. 增加 AVR 增益

### Q: 仿真速度慢？
**A**: 优化建议：
1. 增大时间步长 dt（0.005 → 0.01）
2. 缩短仿真时间（5s → 3s）
3. 使用更快的求解器（Tsit5 for non-stiff）

---

---

### `power_system_ieee9bus_final.py` ⭐⭐⭐ 完整多机系统（最终版）/ Complete Multi-Machine System (Final)

**IEEE 9节点3机系统短路故障仿真 - 含变压器**

**IEEE 9-Bus 3-Machine System Short Circuit Fault Simulation - with Transformers**

#### 系统组成 / System Components:

1. **3台同步发电机** (3 Synchronous Generators)
   - Gen1: 大型发电机 (H=23.64s, P_m=0.716 p.u., δ₀=4.0°)
   - Gen2: 中型发电机 (H=6.4s, P_m=1.63 p.u., δ₀=9.8°)
   - Gen3: 小型发电机 (H=3.01s, P_m=0.85 p.u., δ₀=9.8°)

2. **3个自动电压调节器** (3 AVRs)
   - 高增益反馈控制 (K_a=200)
   - 快速时间常数 (T_a=0.05s)
   - 励磁电压限幅保护

3. **3台升压变压器** (3 Step-up Transformers) ⭐ 新增
   - T1: 变比 n=1.05, 漏抗 X_l=0.0062 p.u.
   - T2: 变比 n=1.025, 漏抗 X_l=0.0086 p.u.
   - T3: 变比 n=1.03, 漏抗 X_l=0.0119 p.u.
   - 考虑绕组电阻和电压变换

4. **3个负荷节点** (3 Load Buses)
   - Load@Bus5: P=1.25, Q=0.5 p.u.
   - Load@Bus6: P=0.9, Q=0.3 p.u.
   - Load@Bus8: P=1.0, Q=0.35 p.u.

5. **故障模拟** (Fault Module)
   - Bus7半金属性短路（过渡电阻短路）
   - 故障时间: t = 2.0s (启动后)
   - 故障持续: 0.1s
   - 电压跌落至 0.35 p.u.（35%）

#### 仿真场景 / Simulation Scenario:

- **t = 0 ~ 2.0s**: 启动过程，系统达到稳态
- **t = 2.0s**: Bus7 半金属性短路，电压降至 0.35 p.u.
- **t = 2.1s**: 故障切除（持续0.1s），电压恢复
- **t = 2.1 ~ 10.0s**: 多机振荡与恢复

#### 关键改进 / Key Improvements:

✅ **正确的初始功角计算**：基于功率平衡方程 P_e = E'_q·V·sin(δ)/(X'_d+X_e)

✅ **启动过程**：前2秒让系统达到稳态，避免初始瞬态

✅ **变压器模型**：包含变比、漏抗、绕组电阻

✅ **物理真实性**：大惯量机组摆动小，小惯量机组摆动大

✅ **长时间仿真**：10秒仿真时间，观察完整恢复过程

#### 运行方法 / How to Run:

```bash
python examples/power_system_ieee9bus_final.py
```

#### 输出文件 / Output Files:

- `ieee_9bus_final.csv` - 完整仿真数据（1000+时间点，46个状态变量）
- `ieee_9bus_final.png` - 5子图可视化：
  - (a) 3台发电机功角对比
  - (b) 3台发电机角速度偏差对比
  - (c) 电磁功率与机械功率
  - (d) 发电机机端电压
  - (e) **变压器高压侧电压** ⭐ 新增

#### 预期结果 / Expected Results:

- ✅ Gen1初始功角 ≈ 4°，最大功角 ≈ 4-5°（大惯量）
- ✅ Gen2初始功角 ≈ 10°，最大功角 ≈ 14-15°（中惯量）
- ✅ Gen3初始功角 ≈ 10°，最大功角 ≈ 10-11°（小惯量）
- ✅ 变压器电压随机端电压波动，升压比例正确
- ✅ 故障期间电压骤降，AVR快速响应
- ✅ 故障切除后系统恢复稳定
- ✅ **系统保持同步稳定性**

#### 主要特性 / Key Features:

- ✅ 多机系统建模（3台发电机，不同容量）
- ✅ 独立的AVR励磁控制
- ✅ **升压变压器模型（变比+漏抗）** ⭐ 新增
- ✅ 负荷模型（恒阻抗）
- ✅ 机组参数差异化（大中小型发电机）
- ✅ 半金属性短路故障
- ✅ 启动过程和稳态初始化
- ✅ 多机振荡分析
- ✅ 系统稳定性评估

---

### `power_system_3machine_9bus.py` 简化版 / Simplified Version

基础的3机9节点系统（不含变压器和启动过程），建议使用最终版 `power_system_ieee9bus_final.py`。

Basic 3-machine 9-bus system (without transformers and initialization), recommend using final version `power_system_ieee9bus_final.py`.

---

## 💡 下一步 / Next Steps

1. **网络拓扑**: 完善输电线路和变压器模型
2. **负荷动态**: 添加动态负荷模型（感应电动机）
3. **PSS**: 加入电力系统稳定器
4. **继电保护**: 模拟保护动作和断路器
5. **新能源**: 添加风电、光伏模型

---

## 📧 联系方式 / Contact

如有问题或建议，请提交 Issue:
https://github.com/pronoobe/pycontroldae/issues

For questions or suggestions, please submit an Issue:
https://github.com/pronoobe/pycontroldae/issues

---

**pycontroldae** - 让电力系统仿真更简单！

**pycontroldae** - Making Power System Simulation Simple!
