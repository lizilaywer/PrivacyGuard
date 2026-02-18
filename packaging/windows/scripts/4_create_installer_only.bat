@echo off
:: PrivacyGuard Create Installer Only
chcp 65001 > nul 2>&1
title PrivacyGuard Create Installer
echo.
echo ========================================
echo   Create Installer from Existing exe
echo ========================================
echo.

:: Get project directory
set "PROJECT_DIR=%~dp0\..\..\.."
cd /d "%PROJECT_DIR%" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to change to project directory
    pause
    exit /b 1
)

:: Configuration
set "APP_NAME=PrivacyGuard"
set "CONFIG_DIR=%~dp0\..\config"

:: Read version
set "VERSION="
for /f "usebackq tokens=*" %%a in ("%PROJECT_DIR%\version.txt") do (
    set "VERSION=%%a"
)
echo [INFO] Version: %VERSION%
set "DIST_DIR=%PROJECT_DIR%\dist"
set "RELEASE_DIR=%PROJECT_DIR%\releases\windows"

echo [CHECK] Checking for existing exe...
set "EXE_FOUND="
if exist "%DIST_DIR%\%APP_NAME%.exe" set "EXE_FOUND=1"
if exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" set "EXE_FOUND=1"

if not defined EXE_FOUND (
    echo [ERROR] exe not found in %DIST_DIR%
    echo.
    echo Please run "2_build_exe.bat" or "3_build_with_setup.bat" first
    pause
    exit /b 1
)

echo [OK] Found existing application
echo.

:: Ensure launcher wrapper exists
echo [CHECK] Checking launcher wrapper...
if not exist "%DIST_DIR%\%APP_NAME%\launcher_wrapper.bat" (
    echo    Creating launcher wrapper...
    copy "%~dp0launcher_wrapper.bat" "%DIST_DIR%\%APP_NAME%\" >nul 2>&1
    echo [OK] Launcher wrapper copied
) else (
    echo [OK] Launcher wrapper exists
)
echo.

echo [CHECK] Checking Inno Setup...

:: Find Inno Setup
set "INNO_PATH="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "C:\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Inno Setup 6\ISCC.exe"
)

if not defined INNO_PATH (
    echo [ERROR] Inno Setup not found
    echo.
    echo Please install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

echo [OK] Inno Setup found
echo.

echo [Step 1/2] Creating installer...
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

echo    Compiling...
"%INNO_PATH%" "%CONFIG_DIR%\PrivacyGuard_Setup.iss" /Q

if errorlevel 1 (
    echo [ERROR] Failed to create installer
    pause
    exit /b 1
)

echo [OK] Installer created
echo.

echo [Step 2/2] Generating checksum...
if exist "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe" (
    certutil -hashfile "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe" SHA256 2>nul | findstr /v "CertUtil" | findstr /v "SHA256" > "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe.sha256"
)
echo [OK] Done
echo.

echo ========================================
echo   [OK] Installer created successfully
echo ========================================
echo.
echo Output:
if exist "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe" (
    echo    %RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe
    for %%I in ("%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe") do (
        echo    Size: %%~zI bytes
    )
) else (
    echo    [WARNING] Installer file not found
)
echo.
pause
