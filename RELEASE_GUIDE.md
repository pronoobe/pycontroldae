# 发布 v0.2.0 指南

## 📦 已准备好的内容

所有文件已更新并准备好发布：

### ✅ 代码更新
- [x] DataProbe功能修复（`pycontroldae/core/simulator.py`）
- [x] 版本号更新到 0.2.0（`pyproject.toml`）

### ✅ 新增示例
- [x] `examples/dae_second_order_system.py` - 双质量弹簧阻尼系统
- [x] `examples/simple_dae_test.py` - 简单RLC电路
- [x] `examples/dae_system_with_ports.py` - 复杂机电耦合系统
- [x] `examples/second_order_damping.py` - 不同阻尼比对比

### ✅ 文档更新
- [x] README.md - 添加Example 6（英文）
- [x] README_CN.md - 添加Example 6（中文）
- [x] CHANGELOG.md - 版本更新日志
- [x] DAE_SYSTEM_SUMMARY.md - DAE系统详细总结
- [x] DATAPROBE_FIX_SUMMARY.md - DataProbe修复总结

### ✅ 发布脚本
- [x] `release_v0.2.0.bat` - 自动化发布脚本

---

## 🚀 如何发布

### 方法1：使用自动化脚本（推荐）

直接双击运行：
```
release_v0.2.0.bat
```

脚本会自动执行：
1. ✓ 添加所有更改的文件到Git
2. ✓ 创建提交（包含详细的更新说明）
3. ✓ 创建版本标签 v0.2.0
4. ✓ 推送代码到GitHub
5. ✓ 推送标签到GitHub
6. ✓ 构建Python包
7. ✓ 提示上传到PyPI（需要PyPI Token）

**注意**：脚本会提示你选择：
- 上传到PyPI（生产环境）
- 上传到TestPyPI（测试环境）
- 跳过上传（稍后手动上传）

### 方法2：手动步骤

如果你想手动控制每一步，按以下顺序执行：

#### 1. Git 提交和推送
```bash
# 添加文件
git add .

# 创建提交
git commit -m "Release v0.2.0: Enhanced DAE support and improved DataProbe"

# 创建标签
git tag -a v0.2.0 -m "Version 0.2.0"

# 推送到GitHub
git push https://YOUR_GITHUB_TOKEN@github.com/pronoobe/pycontroldae.git main
git push https://YOUR_GITHUB_TOKEN@github.com/pronoobe/pycontroldae.git v0.2.0
```

#### 2. 构建Python包
```bash
# 清理旧的构建文件
rmdir /s /q dist build *.egg-info 2>nul

# 安装构建工具
python -m pip install --upgrade build twine

# 构建包
python -m build
```

#### 3. 上传到PyPI
```bash
# 上传到PyPI（需要PyPI Token）
python -m twine upload dist/*

# 或者先上传到TestPyPI测试
python -m twine upload --repository testpypi dist/*
```

---

## 📝 发布后的任务

### 1. 在GitHub上创建Release
1. 访问：https://github.com/pronoobe/pycontroldae/releases/new
2. 选择标签：`v0.2.0`
3. Release标题：`v0.2.0 - Enhanced DAE Support and DataProbe Improvements`
4. 将 `CHANGELOG.md` 中 v0.2.0 的内容复制到说明中
5. 附加文件（可选）：
   - `DAE_SYSTEM_SUMMARY.md`
   - `DATAPROBE_FIX_SUMMARY.md`
   - 示例脚本的zip文件

### 2. 验证PyPI发布
访问：https://pypi.org/project/pycontroldae/

检查：
- 版本号显示为 0.2.0
- README正确显示
- 依赖项正确

### 3. 测试安装
在新环境中测试：
```bash
pip install pycontroldae==0.2.0

# 或从GitHub安装
pip install git+https://github.com/pronoobe/pycontroldae.git@v0.2.0
```

### 4. 运行示例验证
```bash
cd pycontroldae
python examples/dae_second_order_system.py
python examples/simple_dae_test.py
```

---

## 🔧 如果遇到问题

### GitHub推送失败
- 检查Token是否有效
- 确认有写权限
- 尝试使用SSH密钥代替Token

### PyPI上传失败
- 确认版本号未被使用
- 检查PyPI Token权限
- 先上传到TestPyPI测试

### 构建包失败
- 更新构建工具：`pip install --upgrade build setuptools wheel`
- 检查 `pyproject.toml` 语法
- 确保所有依赖已安装

---

## 📊 v0.2.0 更新摘要

### 主要改进
🎯 **DataProbe修复**
- 修复了DAE系统中变量提取的问题
- 支持同时搜索unknowns和observables
- 多策略匹配和自动fallback

🚀 **DAE系统增强**
- 自动处理代数约束
- structural_simplify自动简化
- 完整的示例和文档

📚 **文档完善**
- 新增4个示例程序
- 中英文文档同步更新
- 详细的DAE系统指南

### 新增文件
- `examples/dae_second_order_system.py`
- `examples/simple_dae_test.py`
- `examples/dae_system_with_ports.py`
- `examples/second_order_damping.py`
- `DAE_SYSTEM_SUMMARY.md`
- `DATAPROBE_FIX_SUMMARY.md`
- `CHANGELOG.md`

### 修改文件
- `pycontroldae/core/simulator.py` - DataProbe改进
- `pyproject.toml` - 版本号更新
- `README.md` - 添加Example 6
- `README_CN.md` - 添加Example 6（中文）

---

## ✅ 检查清单

发布前确认：
- [ ] 所有测试通过
- [ ] 示例程序运行正常
- [ ] 版本号已更新
- [ ] CHANGELOG已更新
- [ ] 文档已更新（中英文）
- [ ] Git提交信息清晰
- [ ] 已创建版本标签

发布后确认：
- [ ] GitHub代码已推送
- [ ] GitHub标签已推送
- [ ] PyPI包已上传
- [ ] GitHub Release已创建
- [ ] 新版本可以正常安装
- [ ] 示例可以正常运行

---

**准备好了吗？运行 `release_v0.2.0.bat` 开始发布！** 🚀
