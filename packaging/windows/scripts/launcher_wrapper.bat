@echo off
:: PrivacyGuard Launcher Wrapper
:: Checks for VC++ runtime before launching the application
chcp 65001 > nul 2>&1
title PrivacyGuard

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

:: Check for required DLLs
set "MISSING_DLL="
set "MISSING_CRITICAL=0"

if not exist "C:\Windows\System32\vcruntime140.dll" (
    set "MISSING_DLL=vcruntime140.dll"
)
if not exist "C:\Windows\System32\vcruntime140_1.dll" (
    set "MISSING_DLL=vcruntime140_1.dll"
    set "MISSING_CRITICAL=1"
)
if not exist "C:\Windows\System32\msvcp140.dll" (
    set "MISSING_DLL=msvcp140.dll"
)

if not "%MISSING_DLL%"=="" (
    echo.
    echo ========================================
    echo   PrivacyGuard - Missing Dependencies
    echo ========================================
    echo.
    echo ERROR: Required system libraries are missing.
    echo.
    if "%MISSING_CRITICAL%"=="1" (
        echo The file vcruntime140_1.dll is REQUIRED for OCR functionality.
        echo This is part of the Visual C++ Redistributable package.
        echo.
    )
    echo Please download and install:
    echo https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    echo Alternative: Search for "Visual C++ Redistributable" at:
    echo https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
    echo.
    echo After installation, restart PrivacyGuard.
    echo.
    pause
    exit /b 1
)

:: Launch the application
start "" "%~dp0PrivacyGuard.exe" %*
