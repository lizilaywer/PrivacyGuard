@echo off
:: Use system default code page to avoid UTF-8 compatibility issues
chcp 936 > nul 2>&1
title PrivacyGuard Build
echo.
echo ========================================
echo   PrivacyGuard Build Script
echo ========================================
echo.

:: Get project path (from packaging/windows/scripts/ to project root)
set "PROJECT_DIR=%~dp0..\..\.."
cd /d "%PROJECT_DIR%" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to change to project directory: %PROJECT_DIR%
    pause
    exit /b 1
)

:: Configuration
set "APP_NAME=PrivacyGuard"
set "CONFIG_DIR=%~dp0..\config"

:: Read version from version.txt
set "VERSION="
for /f "usebackq tokens=*" %%a in ("%PROJECT_DIR%\version.txt") do (
    set "VERSION=%%a"
)
echo [INFO] Current version: %VERSION%
set "DIST_DIR=%PROJECT_DIR%\dist"
set "RELEASE_DIR=%PROJECT_DIR%\releases\windows"

echo [CHECK] Checking environment...
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: 1_setup_environment.bat
    pause
    exit /b 1
)

if not exist "%CONFIG_DIR%\PrivacyGuard_windows.spec" (
    echo [ERROR] Build configuration file not found!
    echo Please ensure packaging\windows\config\PrivacyGuard_windows.spec exists
    pause
    exit /b 1
)

echo [OK] Environment check passed
echo.

:: Activate virtual environment
call venv\Scripts\activate.bat

echo [1/4] Cleaning old builds...
if exist "%DIST_DIR%" (
    rmdir /s /q "%DIST_DIR%" 2>nul
    echo    Cleaned dist directory
)
if exist "build\build" (
    rmdir /s /q "build\build" 2>nul
    echo    Cleaned build cache
)
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
echo [OK] Cleanup complete
echo.

echo [2/4] Starting build (this may take 5-10 minutes)...
echo    Analyzing dependencies and building, please wait...
echo.

pyinstaller --clean --noconfirm "%CONFIG_DIR%\PrivacyGuard_windows.spec"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed! See error messages above.
    echo.
    echo Common issues:
    echo   1. Check if main.py has syntax errors
    echo   2. Check if all dependencies are installed
    echo   3. Review error messages above
    pause
    exit /b 1
)

echo [OK] Build complete
echo.

echo [3/4] Copying additional files...
if exist "%PROJECT_DIR%\LICENSE.txt" (
    copy "%PROJECT_DIR%\LICENSE.txt" "%DIST_DIR%\" >nul 2>&1
)
if exist "%PROJECT_DIR%\README.md" (
    copy "%PROJECT_DIR%\README.md" "%DIST_DIR%\" >nul 2>&1
)
echo [OK] Done
echo.

echo [4/4] Generating checksums...
if exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
    certutil -hashfile "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" SHA256 2>nul | findstr /v "CertUtil" | findstr /v "SHA256" > "%RELEASE_DIR%\%APP_NAME%-%VERSION%.exe.sha256"
) else if exist "%DIST_DIR%\%APP_NAME%.exe" (
    certutil -hashfile "%DIST_DIR%\%APP_NAME%.exe" SHA256 2>nul | findstr /v "CertUtil" | findstr /v "SHA256" > "%RELEASE_DIR%\%APP_NAME%-%VERSION%.exe.sha256"
)
echo [OK] Checksum generated
echo.

echo ========================================
echo   [OK] Build complete!
echo ========================================
echo.
echo [OUTPUT] Output files:
if exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo    %DIST_DIR%\%APP_NAME%.exe
    for %%I in ("%DIST_DIR%\%APP_NAME%.exe") do (
        echo    Size: %%~zI bytes
    )
) else if exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
    echo    %DIST_DIR%\%APP_NAME%\%APP_NAME%.exe
    for %%I in ("%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe") do (
        echo    Size: %%~zI bytes
    )
)
echo.
echo [TIP] You can test the application directly
echo.

:: Ask if user wants to test
set /p TEST_NOW="Run test now? (y/n): "
if /i "%TEST_NOW%"=="y" (
    echo.
    echo Starting PrivacyGuard...
    if exist "%DIST_DIR%\%APP_NAME%.exe" (
        start "" "%DIST_DIR%\%APP_NAME%.exe"
    ) else if exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
        start "" "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe"
    )
)

echo.
pause
