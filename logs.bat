@echo off
chcp 65001 >nul
echo ========================================
echo   Dify-on-WeChat 日志查看
echo ========================================
echo.

if not exist run.log (
    echo [错误] 未找到日志文件 run.log
    echo.
    echo 可能原因:
    echo   1. 应用还未启动过
    echo   2. 日志文件被删除
    echo.
    pause
    exit /b 1
)

echo [信息] 显示最后 50 行日志
echo [提示] 按 Ctrl+C 可退出
echo.
echo ========================================
echo.

powershell -Command "Get-Content run.log -Tail 50 -Encoding UTF8"

echo.
echo ========================================
echo.
echo 实时查看日志请使用:
echo   powershell -Command "Get-Content run.log -Tail 50 -Wait -Encoding UTF8"
echo.
pause
