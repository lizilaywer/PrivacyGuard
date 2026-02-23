@echo off
:: PrivacyGuard - 解除文件阻止工具
:: 解决 "Windows 安全中心阻止打开文件" 问题
chcp 65001 > nul 2>&1
title PrivacyGuard - 解除文件阻止

echo.
echo ========================================
echo   PrivacyGuard 解除文件阻止工具
echo ========================================
echo.
echo 此脚本将解除 Windows 对 PrivacyGuard 文件的阻止。
echo.

set "PROJECT_DIR=%~dp0\..\..\.."
cd /d "%PROJECT_DIR%" 2>nul
if errorlevel 1 (
    echo [ERROR] 无法切换到项目目录
    pause
    exit /b 1
)

echo [INFO] 项目目录: %PROJECT_DIR%
echo.

echo [1/4] 检查 PowerShell 可用性...
where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell 未找到
    pause
    exit /b 1
)
echo [OK] PowerShell 可用
echo.

echo [2/4] 解除批处理文件阻止...
echo    - packaging\windows\scripts\*.bat
echo    - packaging\windows\config\*.spec
powershell -Command "Get-ChildItem -Path '%PROJECT_DIR%\packaging\windows\scripts' -Recurse -File | Unblock-File -ErrorAction SilentlyContinue"
powershell -Command "Get-ChildItem -Path '%PROJECT_DIR%\packaging\windows\config' -Recurse -File | Unblock-File -ErrorAction SilentlyContinue"
echo [OK] 已解除脚本和配置文件阻止
echo.

echo [3/4] 解除项目根目录文件阻止...
echo    - *.py, *.txt, *.md
echo    - *.json, *.template
powershell -Command "Get-ChildItem -Path '%PROJECT_DIR%' -File -Include '*.py','*.txt','*.md','*.json','*.template' | Unblock-File -ErrorAction SilentlyContinue"
echo [OK] 已解除项目文件阻止
echo.

echo [4/4] 解除 privacyguard 包文件阻止...
if exist "%PROJECT_DIR%\privacyguard" (
    powershell -Command "Get-ChildItem -Path '%PROJECT_DIR%\privacyguard' -Recurse -File | Unblock-File -ErrorAction SilentlyContinue"
    echo [OK] 已解除 privacyguard 包文件阻止
) else (
    echo [SKIP] privacyguard 目录不存在
)
echo.

echo ========================================
echo   [OK] 所有文件已解除阻止
echo ========================================
echo.
echo 现在可以正常运行构建脚本了：
echo.
echo   方法1 - 自动复制DLL版本（推荐）:
echo     packaging\windows\scripts\2_build_exe_fix_dll.bat
echo.
echo   方法2 - 标准版本:
echo     packaging\windows\scripts\2_build_exe.bat
echo.
echo   方法3 - 增强版本（带诊断）:
echo     packaging\windows\scripts\2_build_exe_enhanced.bat
echo.
pause
