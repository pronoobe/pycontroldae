@echo off
REM ========================================
REM PyControlDAE v0.2.0 发布脚本
REM ========================================
echo.
echo ========================================
echo PyControlDAE v0.2.0 发布脚本
echo ========================================
echo.

REM 设置变量
set VERSION=0.2.0
set GITHUB_TOKEN=YOUR_GITHUB_TOKEN_HERE
set GITHUB_REPO=pronoobe/pycontroldae

echo [步骤 1/8] 检查Git状态...
git status

echo.
echo [步骤 2/8] 添加所有更改的文件...
git add .

echo.
echo [步骤 3/8] 创建提交...
git commit -m "Release v%VERSION%: Enhanced DAE support and improved DataProbe

Major Changes:
- Enhanced DAE system support with automatic simplification
- Fixed and improved DataProbe for DAE systems
- Added 4 new comprehensive examples
- Updated documentation (EN and CN)

New Features:
- Multi-strategy variable extraction in DataProbe
- Automatic handling of algebraic constraints
- Better error messages and fallback mechanisms

New Examples:
- dae_second_order_system.py - Double mass-spring-damper
- simple_dae_test.py - RLC circuit
- dae_system_with_ports.py - Electromechanical coupling
- second_order_damping.py - Damping ratio comparison

Documentation:
- Added Example 6 in README.md and README_CN.md
- Created DAE_SYSTEM_SUMMARY.md
- Created DATAPROBE_FIX_SUMMARY.md
- Created CHANGELOG.md"

if %ERRORLEVEL% NEQ 0 (
    echo 错误: Git commit 失败
    pause
    exit /b 1
)

echo.
echo [步骤 4/8] 创建Git标签...
git tag -a v%VERSION% -m "Version %VERSION%: Enhanced DAE Support and DataProbe Improvements"

if %ERRORLEVEL% NEQ 0 (
    echo 错误: 创建标签失败
    pause
    exit /b 1
)

echo.
echo [步骤 5/8] 推送到GitHub (main分支)...
git push https://%GITHUB_TOKEN%@github.com/%GITHUB_REPO%.git main

if %ERRORLEVEL% NEQ 0 (
    echo 错误: 推送main分支失败
    pause
    exit /b 1
)

echo.
echo [步骤 6/8] 推送标签到GitHub...
git push https://%GITHUB_TOKEN%@github.com/%GITHUB_REPO%.git v%VERSION%

if %ERRORLEVEL% NEQ 0 (
    echo 错误: 推送标签失败
    pause
    exit /b 1
)

echo.
echo [步骤 7/8] 构建Python包...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.egg-info rmdir /s /q *.egg-info

python -m pip install --upgrade build twine
python -m build

if %ERRORLEVEL% NEQ 0 (
    echo 错误: 构建包失败
    pause
    exit /b 1
)

echo.
echo [步骤 8/8] 上传到PyPI...
echo.
echo 现在需要上传到PyPI。
echo 请选择:
echo   1. 上传到PyPI (需要PyPI Token)
echo   2. 上传到TestPyPI (测试)
echo   3. 跳过上传
echo.
set /p PYPI_CHOICE="请选择 (1/2/3): "

if "%PYPI_CHOICE%"=="1" (
    echo.
    echo 正在上传到PyPI...
    echo 请输入PyPI Token:
    set /p PYPI_TOKEN="Token: "
    python -m twine upload dist/* -u __token__ -p %PYPI_TOKEN%

    if %ERRORLEVEL% NEQ 0 (
        echo 警告: 上传到PyPI失败
        echo 你可以稍后手动运行: python -m twine upload dist/*
    ) else (
        echo ✓ 成功上传到PyPI!
    )
) else if "%PYPI_CHOICE%"=="2" (
    echo.
    echo 正在上传到TestPyPI...
    echo 请输入TestPyPI Token:
    set /p TEST_PYPI_TOKEN="Token: "
    python -m twine upload --repository testpypi dist/* -u __token__ -p %TEST_PYPI_TOKEN%

    if %ERRORLEVEL% NEQ 0 (
        echo 警告: 上传到TestPyPI失败
    ) else (
        echo ✓ 成功上传到TestPyPI!
        echo 测试安装: pip install -i https://test.pypi.org/simple/ pycontroldae==%VERSION%
    )
) else (
    echo.
    echo 跳过PyPI上传。
    echo 稍后可以手动运行:
    echo   python -m twine upload dist/*
)

echo.
echo ========================================
echo 发布完成!
echo ========================================
echo.
echo 版本: %VERSION%
echo GitHub: https://github.com/%GITHUB_REPO%/releases/tag/v%VERSION%
echo.
echo 下一步:
echo 1. 在GitHub上创建Release页面
echo 2. 将CHANGELOG.md中的更新内容复制到Release Notes
echo 3. 附加示例文件和文档
echo.

pause
