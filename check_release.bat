@echo off
REM ========================================
REM 发布前检查脚本
REM ========================================
echo.
echo ========================================
echo PyControlDAE v0.2.0 发布前检查
echo ========================================
echo.

set ALL_OK=1

echo [检查 1/8] 检查版本号...
findstr /C:"version = \"0.2.0\"" pyproject.toml >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ 版本号正确: 0.2.0
) else (
    echo ✗ 版本号不正确
    set ALL_OK=0
)

echo.
echo [检查 2/8] 检查新增示例文件...
set MISSING_FILES=0
if not exist "examples\dae_second_order_system.py" (
    echo ✗ 缺少: examples\dae_second_order_system.py
    set MISSING_FILES=1
    set ALL_OK=0
)
if not exist "examples\simple_dae_test.py" (
    echo ✗ 缺少: examples\simple_dae_test.py
    set MISSING_FILES=1
    set ALL_OK=0
)
if not exist "examples\second_order_damping.py" (
    echo ✗ 缺少: examples\second_order_damping.py
    set MISSING_FILES=1
    set ALL_OK=0
)
if %MISSING_FILES% EQU 0 (
    echo ✓ 所有示例文件存在
)

echo.
echo [检查 3/8] 检查文档文件...
set MISSING_DOCS=0
if not exist "CHANGELOG.md" (
    echo ✗ 缺少: CHANGELOG.md
    set MISSING_DOCS=1
    set ALL_OK=0
)
if not exist "DAE_SYSTEM_SUMMARY.md" (
    echo ✗ 缺少: DAE_SYSTEM_SUMMARY.md
    set MISSING_DOCS=1
    set ALL_OK=0
)
if not exist "DATAPROBE_FIX_SUMMARY.md" (
    echo ✗ 缺少: DATAPROBE_FIX_SUMMARY.md
    set MISSING_DOCS=1
    set ALL_OK=0
)
if %MISSING_DOCS% EQU 0 (
    echo ✓ 所有文档文件存在
)

echo.
echo [检查 4/8] 检查README更新...
findstr /C:"示例6：含代数约束的DAE系统" README_CN.md >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ 中文README已更新（包含Example 6）
) else (
    echo ✗ 中文README未更新
    set ALL_OK=0
)

findstr /C:"Example 6: DAE Systems with Algebraic Constraints" README.md >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ 英文README已更新（包含Example 6）
) else (
    echo ✗ 英文README未更新
    set ALL_OK=0
)

echo.
echo [检查 5/8] 检查DataProbe修复...
findstr /C:"observed" pycontroldae\core\simulator.py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ DataProbe代码已更新
) else (
    echo ✗ DataProbe代码未更新
    set ALL_OK=0
)

echo.
echo [检查 6/8] 检查Git状态...
git status --porcelain >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Git可用
    echo.
    echo 未提交的更改:
    git status --short
) else (
    echo ✗ Git不可用
    set ALL_OK=0
)

echo.
echo [检查 7/8] 测试Python环境...
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python --version
    echo ✓ Python可用
) else (
    echo ✗ Python不可用
    set ALL_OK=0
)

echo.
echo [检查 8/8] 检查必要的Python包...
python -c "import numpy, pandas, matplotlib" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ 基础依赖已安装（numpy, pandas, matplotlib）
) else (
    echo ⚠ 部分依赖未安装
    echo   运行: pip install numpy pandas matplotlib
)

python -c "import build, twine" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ 构建工具已安装（build, twine）
) else (
    echo ⚠ 构建工具未安装
    echo   运行: pip install build twine
)

echo.
echo ========================================
echo 检查结果
echo ========================================

if %ALL_OK% EQU 1 (
    echo.
    echo ✓✓✓ 所有检查通过！准备发布 ✓✓✓
    echo.
    echo 下一步:
    echo   运行 release_v0.2.0.bat 开始发布
    echo.
) else (
    echo.
    echo ✗✗✗ 有问题需要修复 ✗✗✗
    echo.
    echo 请修复上述问题后再运行发布脚本
    echo.
)

pause
