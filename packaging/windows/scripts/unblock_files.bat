@echo off
:: 解除 Windows 对文件的阻止
chcp 65001 > nul 2>&1
title Unblock PrivacyGuard Files
echo.
echo ========================================
echo   解除文件阻止工具
echo ========================================
echo.
echo 此脚本将解除 Windows 对 PrivacyGuard 文件的阻止。
echo.

set "PROJECT_DIR=%~dp0\..\..\.."
cd /d "%PROJECT_DIR%"

echo [1/3] 检查 PowerShell 可用性...
where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell 未找到
    pause
    exit /b 1
)
echo [OK] PowerShell 可用
echo.

echo [2/3] 解除批处理文件阻止...
powershell -Command "Get-ChildItem -Path '%PROJECT_DIR%\packaging\windows\scripts' -Recurse | Unblock-File"
powershell -Command "Get-ChildItem -Path '%PROJECT_DIR%\packaging\windows\config' -Recurse | Unblock-File"
echo [OK] 已解除脚本文件阻止
echo.

echo [3/3] 解除构建输出阻止（如果存在）...
if exist "%PROJECT_DIR%\dist" (
    powershell -Command "Get-ChildItem -Path '%PROJECT_DIR%\dist' -Recurse | Unblock-File"
    echo [OK] 已解除构建输出阻止
) else (
    echo [SKIP] 无构建输出目录
)
echo.

echo ========================================
echo   [OK] 所有文件已解除阻止
echo ========================================
echo.
echo 现在可以重新运行增强版构建脚本了：
echo   packaging\windows\scripts\2_build_exe_enhanced.bat
echo.
pause
