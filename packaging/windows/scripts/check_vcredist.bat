@echo off
:: Check Visual C++ Redistributable
chcp 65001 > nul 2>&1
title Check VC++ Redistributable
echo.
echo ========================================
echo   Check Visual C++ Redistributable
echo ========================================
echo.

echo Checking for required VC++ runtime files...
echo.

set "MISSING=0"
set "MISSING_140_1=0"

:: Check for vcruntime140.dll
if exist "C:\Windows\System32\vcruntime140.dll" (
    echo [OK] vcruntime140.dll found
) else (
    echo [MISSING] vcruntime140.dll not found
    set "MISSING=1"
)

:: Check for msvcp140.dll
if exist "C:\Windows\System32\msvcp140.dll" (
    echo [OK] msvcp140.dll found
) else (
    echo [MISSING] msvcp140.dll not found
    set "MISSING=1"
)

:: Check for vcruntime140_1.dll (REQUIRED for onnxruntime)
if exist "C:\Windows\System32\vcruntime140_1.dll" (
    echo [OK] vcruntime140_1.dll found
) else (
    echo [MISSING] vcruntime140_1.dll not found (REQUIRED for OCR)
    set "MISSING=1"
    set "MISSING_140_1=1"
)

:: Check for msvcp140_1.dll (additional)
if exist "C:\Windows\System32\msvcp140_1.dll" (
    echo [OK] msvcp140_1.dll found
) else (
    echo [INFO] msvcp140_1.dll not found (may be optional)
)

:: Check for msvcp140_2.dll (additional)
if exist "C:\Windows\System32\msvcp140_2.dll" (
    echo [OK] msvcp140_2.dll found
) else (
    echo [INFO] msvcp140_2.dll not found (may be optional)
)

echo.

if "%MISSING%"=="1" (
    echo ========================================
    echo   [ERROR] VC++ Redistributable missing
echo ========================================
    echo.
    echo PrivacyGuard requires Visual C++ Redistributable.
    echo.
    if "%MISSING_140_1%"=="1" (
        echo IMPORTANT: vcruntime140_1.dll is REQUIRED for OCR functionality.
        echo This is a newer version of the runtime. Please update VC++ Redist.
        echo.
    )
    echo Download and install the latest VC++ Redistributable:
    echo https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    echo Alternative link:
    echo https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
    echo.
    echo After installation, restart PrivacyGuard.
    echo.
    pause
    exit /b 1
) else (
    echo ========================================
    echo   [OK] All required VC++ runtime files found
echo ========================================
    echo.
    echo You can now run PrivacyGuard.
    echo.
    exit /b 0
)
