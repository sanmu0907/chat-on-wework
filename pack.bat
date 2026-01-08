@echo off
chcp 65001 >nul
echo ============================================================
echo   Dify-on-WeChat 项目打包工具 (Windows)
echo ============================================================
echo.

python pack.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 打包失败！
    pause
    exit /b 1
)

echo.
pause
