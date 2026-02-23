@echo off
:: PrivacyGuard 紧急修复启动器
:: 如果打包后的应用因 DLL 问题无法启动，使用此脚本
chcp 65001 > nul 2>&1
title PrivacyGuard - Emergency Launcher

echo.
echo ========================================
echo   PrivacyGuard 紧急修复启动器
echo ========================================
echo.

set "APP_DIR=%~dp0"
set "DLL_COPIED=0"

:: 检查必需的 DLL
echo [CHECK] 检查系统 DLL...
echo.

set "VCRT140_1_MISSING=0"
set "VCRT140_MISSING=0"
set "MSVCP140_MISSING=0"

if not exist "C:\Windows\System32\vcruntime140_1.dll" (
    echo    [MISSING] vcruntime140_1.dll (必需)
    set "VCRT140_1_MISSING=1"
) else (
    echo    [OK] vcruntime140_1.dll
)

if not exist "C:\Windows\System32\vcruntime140.dll" (
    echo    [MISSING] vcruntime140.dll (必需)
    set "VCRT140_MISSING=1"
) else (
    echo    [OK] vcruntime140.dll
)

if not exist "C:\Windows\System32\msvcp140.dll" (
    echo    [MISSING] msvcp140.dll (必需)
    set "MSVCP140_MISSING=1"
) else (
    echo    [OK] msvcp140.dll
)

:: 如果有缺失，显示下载链接
if "%VCRT140_1_MISSING%"=="1" (
    echo.
    echo ========================================
    echo [CRITICAL] 缺少必需的 VC++ DLL 文件！
    echo ========================================
    echo.
    echo 请下载并安装以下组件：
    echo.
    echo Microsoft Visual C++ Redistributable 2015-2022
    echo https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    echo 安装完成后，请重新运行此脚本。
    echo.
    pause
    exit /b 1
)

:: 尝试复制 DLL 到应用目录
echo.
echo [FIX] 尝试复制 DLL 到应用目录...
echo.

if "%VCRT140_MISSING%"=="0" (
    copy "C:\Windows\System32\vcruntime140.dll" "%APP_DIR%" >nul 2>&1
    if errorlevel 0 (
        echo    [OK] 已复制 vcruntime140.dll
        set "DLL_COPIED=1"
    )
)

if "%VCRT140_1_MISSING%"=="0" (
    copy "C:\Windows\System32\vcruntime140_1.dll" "%APP_DIR%" >nul 2>&1
    if errorlevel 0 (
        echo    [OK] 已复制 vcruntime140_1.dll
        set "DLL_COPIED=1"
    )
)

if "%MSVCP140_MISSING%"=="0" (
    copy "C:\Windows\System32\msvcp140.dll" "%APP_DIR%" >nul 2>&1
    if errorlevel 0 (
        echo    [OK] 已复制 msvcp140.dll
        set "DLL_COPIED=1"
    )
)

:: 检查应用目录中是否已有 DLL
echo.
echo [CHECK] 检查应用目录中的 DLL...
if exist "%APP_DIR%\vcruntime140_1.dll" (
    echo    [OK] 应用目录包含 vcruntime140_1.dll
) else (
    echo    [WARN] 应用目录缺少 vcruntime140_1.dll
)

echo.
echo ========================================
echo   正在启动 PrivacyGuard...
echo ========================================
echo.

:: 启动应用
if exist "%APP_DIR%\PrivacyGuard.exe" (
    start "" "%APP_DIR%\PrivacyGuard.exe"
    echo [OK] PrivacyGuard 已启动
    echo.
    echo 如果应用仍然无法启动，请：
    echo 1. 确认已安装 VC++ Redistributable
    echo 2. 查看错误信息并反馈给开发团队
    echo.
    timeout /t 3 >nul
) else (
    echo [ERROR] 未找到 PrivacyGuard.exe
    echo.
    echo 请确保此脚本位于 PrivacyGuard 应用目录中。
    echo.
    pause
    exit /b 1
)
