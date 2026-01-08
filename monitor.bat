@echo off
chcp 65001 >nul
echo ========================================
echo   Dify-on-WeChat 实时日志监控
echo ========================================
echo.

REM 检查应用是否在运行
echo [检查] 应用运行状态...
wmic process where "commandline like '%%app.py%%' and (name='python.exe' or name='pythonw.exe')" get processid 2>nul | findstr /r "[0-9]" >nul
if %errorlevel% equ 0 (
    echo [运行中] 应用正在运行
) else (
    echo [未运行] 应用未运行
    echo.
    echo [提示] 建议先启动应用：
    echo   - 启动并监控: start_monitor.bat
    echo   - 仅启动:     start.bat
    echo.
    set /p choice="是否继续监控日志？(y/n): "
    if /i not "%choice%"=="y" exit /b 0
)

echo.

REM 检查日志文件
if not exist run.log (
    echo [错误] 未找到日志文件 run.log
    echo.
    echo 可能原因:
    echo   1. 应用还未启动过
    echo   2. 日志文件被删除
    echo   3. 当前目录不正确
    echo.
    pause
    exit /b 1
)

REM 显示日志文件信息
for %%F in (run.log) do set SIZE=%%~zF
set /a SIZE_KB=%SIZE% / 1024
echo [日志文件] run.log
echo [文件大小] %SIZE_KB% KB
for %%F in (run.log) do echo [最后修改] %%~tF
echo.

REM 开始实时监控
echo ========================================
echo   实时监控中...
echo   按 Ctrl+C 退出（应用继续运行）
echo ========================================
echo.

REM 实时监控日志（UTF-8编码，显示最后50行并持续跟踪）
powershell -Command "Get-Content run.log -Tail 50 -Wait -Encoding UTF8"
