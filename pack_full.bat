@echo off
chcp 65001 >nul
echo ============================================================
echo   Dify-on-WeChat 完整迁移打包工具
echo   Full Migration Packaging Tool
echo ============================================================
echo.
echo 此工具将打包所有配置和数据，用于迁移到另一台电脑
echo This tool will package ALL configs and data for migration
echo.
echo 警告：打包文件将包含敏感信息（API密钥等），请妥善保管！
echo WARNING: Package will contain sensitive data (API keys, etc.)
echo.

python pack_full.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 打包失败！
    pause
    exit /b 1
)

echo.
pause
