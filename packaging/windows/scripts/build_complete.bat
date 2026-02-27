@echo off
setlocal enabledelayedexpansion
:: Note: chcp 65001 can cause echo commands to fail silently on some systems
:: Using default codepage (936 for Chinese Windows) for better compatibility
chcp 936 > nul 2>&1
title PrivacyGuard Build

echo.
echo ========================================
echo   PrivacyGuard Windows Build Script
echo   Version: v37.5.0 (Seal Detection)
echo ========================================
echo.

:: Get project directory (simplified - avoid pushd/popd issues)
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%..\..\.."

:: Convert to absolute path using for loop
for %%i in ("%PROJECT_DIR%") do set "PROJECT_DIR=%%~fi"

:: Verify project directory exists
if not exist "%PROJECT_DIR%\main.py" (
    echo [ERROR] Cannot find project directory
    echo [HINT] Expected: %PROJECT_DIR%
    echo [HINT] Make sure script is in packaging\windows\scripts\
    pause
    exit /b 1
)
echo [OK] Project directory: %PROJECT_DIR%

set "APP_NAME=PrivacyGuard"

:: Convert all paths to absolute
for %%i in ("%SCRIPT_DIR%..\config") do set "CONFIG_DIR=%%~fi"
for %%i in ("%SCRIPT_DIR%..\assets") do set "ASSETS_DIR=%%~fi"
set "DIST_DIR=%PROJECT_DIR%\dist"
set "RELEASE_DIR=%PROJECT_DIR%\releases\windows"

:: ========== Phase 1: Environment Check ==========
echo [Phase 1/7] Environment check...

:: Check virtual environment (support both venv and venv_win)
set "VENV_PATH="
if exist "%PROJECT_DIR%\venv_win\Scripts\activate.bat" (
    set "VENV_PATH=%PROJECT_DIR%\venv_win"
) else if exist "%PROJECT_DIR%\venv\Scripts\activate.bat" (
    set "VENV_PATH=%PROJECT_DIR%\venv"
) else (
    echo [ERROR] Virtual environment not found
    echo [HINT] Run: packaging\windows\scripts\1_init_environment.bat
    echo [HINT] Expected: venv_win\Scripts\activate.bat or venv\Scripts\activate.bat
    pause
    exit /b 1
)
echo [OK] Found virtual environment: %VENV_PATH%

:: Debug: Show paths being checked
echo [DEBUG] PROJECT_DIR=%PROJECT_DIR%
echo [DEBUG] CONFIG_DIR=%CONFIG_DIR%
echo [DEBUG] ASSETS_DIR=%ASSETS_DIR%

:: Check version.txt
echo [DEBUG] Checking: %PROJECT_DIR%\version.txt
echo [DEBUG] Using dir to verify:
dir "%PROJECT_DIR%\version.txt" 2>&1
if not exist "%PROJECT_DIR%\version.txt" (
    echo [ERROR] version.txt not found - check path above
    echo [HINT] Create version.txt in project root
    pause
    exit /b 1
)
echo [OK] version.txt found

:: Read version
set "VERSION="
for /f "usebackq tokens=*" %%a in ("%PROJECT_DIR%\version.txt") do (
    set "VERSION=%%a"
)

:: Check spec file
echo [DEBUG] Checking: %CONFIG_DIR%\PrivacyGuard_windows.spec
if not exist "%CONFIG_DIR%\PrivacyGuard_windows.spec" (
    echo [ERROR] PyInstaller spec file not found
    echo [PATH] %CONFIG_DIR%\PrivacyGuard_windows.spec
    pause
    exit /b 1
)
echo [OK] spec file found

:: Check icon file
echo [DEBUG] Checking: %ASSETS_DIR%\icon.ico
if not exist "%ASSETS_DIR%\icon.ico" (
    echo [ERROR] Application icon not found
    echo [PATH] %ASSETS_DIR%\icon.ico
    pause
    exit /b 1
)
echo [OK] icon file found

:: Check main.py
if not exist "%PROJECT_DIR%\main.py" (
    echo [ERROR] main.py not found
    pause
    exit /b 1
)

:: Check assets directory
if not exist "%PROJECT_DIR%\assets" (
    echo [WARN] assets directory not found, donate QR code will not work
) else (
    echo [OK] assets directory exists
)

echo [INFO] App Name: %APP_NAME%
echo [INFO] Version: %VERSION%
echo [INFO] Project: %PROJECT_DIR%
echo [OK] Environment check passed
echo.

:: ========== Phase 2: Clean old builds ==========
echo [Phase 2/8] Cleaning old builds...
pushd "%PROJECT_DIR%"
if exist "%DIST_DIR%" (
    rmdir /s /q "%DIST_DIR%" 2>nul
    echo [OK] Deleted old dist/
)
if exist "build\build" (
    rmdir /s /q "build\build" 2>nul
    echo [OK] Deleted old build/
)
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
popd
echo.

:: ========== Phase 2.5: Verify dependencies ==========
echo [Phase 3/8] Verifying dependencies...
call "%VENV_PATH%\Scripts\activate.bat"
python "%SCRIPT_DIR%verify_dependencies.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency verification failed!
    echo [HINT] Run: pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] All dependencies verified
echo.

:: ========== Phase 3: Build executable ==========
echo [Phase 4/8] Building executable...
echo [INFO] This may take 5-15 minutes, please wait...
echo.

pushd "%PROJECT_DIR%"
call "%VENV_PATH%\Scripts\activate.bat"
pyinstaller --clean --noconfirm "%CONFIG_DIR%\PrivacyGuard_windows.spec"
popd

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed
    pause
    exit /b 1
)
echo [OK] Build complete
echo.

:: ========== Phase 4: Copy files ==========
echo [Phase 5/8] Copying files...

:: Copy VC++ DLLs
echo [INFO] Copying VC++ runtime DLLs...
for %%D in (vcruntime140_1.dll vcruntime140.dll msvcp140.dll) do (
    if exist "C:\Windows\System32\%%D" (
        copy "C:\Windows\System32\%%D" "%DIST_DIR%\%APP_NAME%\" >nul 2>&1
        echo   [OK] %%D
    ) else (
        echo   [WARN] %%D not found
    )
)

:: Copy launcher
copy "%~dp0launcher_wrapper.bat" "%DIST_DIR%\%APP_NAME%\" >nul 2>&1
echo   [OK] launcher_wrapper.bat

:: Copy documentation
if exist "%PROJECT_DIR%\LICENSE.txt" (
    copy "%PROJECT_DIR%\LICENSE.txt" "%DIST_DIR%\%APP_NAME%\" >nul 2>&1
    echo   [OK] LICENSE.txt
) else if exist "%PROJECT_DIR%\LICENSE" (
    copy "%PROJECT_DIR%\LICENSE" "%DIST_DIR%\%APP_NAME%\LICENSE.txt" >nul 2>&1
    echo   [OK] LICENSE
)
if exist "%PROJECT_DIR%\README.md" (
    copy "%PROJECT_DIR%\README.md" "%DIST_DIR%\%APP_NAME%\README.md" >nul 2>&1
    echo   [OK] README.md
)
echo.

:: ========== Phase 5: Clean build directory ==========
echo [Phase 6/8] Cleaning build directory...

:: Remove development files
for %%F in (.gitignore .project_info) do (
    if exist "%DIST_DIR%\%APP_NAME%\%%F" (
        del /f /q "%DIST_DIR%\%APP_NAME%\%%F" 2>nul
        echo   [CLEAN] Removed %%F
    )
)

:: Remove test files
if exist "%DIST_DIR%\%APP_NAME%\tests" (
    rmdir /s /q "%DIST_DIR%\%APP_NAME%\tests" 2>nul
    echo   [CLEAN] Removed tests/
)

:: Remove pip files
for %%D in (pip pip-egg-info) do (
    if exist "%DIST_DIR%\%APP_NAME%\%%D" (
        rmdir /s /q "%DIST_DIR%\%APP_NAME%\%%D" 2>nul
        echo   [CLEAN] Removed %%D/
    )
)

:: Remove .pyc and __pycache__
for /f "delims=" %%i in ('dir /s /b "%DIST_DIR%\%APP_NAME%\*.pyc" 2^>nul') do (
    del /f /q "%%i" 2>nul
)
for /f "delims=" %%i in ('dir /s /b "%DIST_DIR%\%APP_NAME%\__pycache__" 2^>nul') do (
    rmdir /s /q "%%i" 2>nul
)
echo   [CLEAN] Removed .pyc and __pycache__

echo [OK] Build directory cleaned
echo.

:: ========== Phase 6: Verify build ==========
echo [Phase 7/8] Verifying build...

set "VERIFY_FAIL=0"
for %%F in (PrivacyGuard.exe) do (
    if exist "%DIST_DIR%\%APP_NAME%\%%F" (
        echo   [OK] %%F exists
    ) else (
        echo   [FAIL] %%F not found
        set "VERIFY_FAIL=1"
    )
)

if exist "%DIST_DIR%\%APP_NAME%\assets\donate_qrcode.png" (
    echo   [OK] assets\donate_qrcode.png exists
) else (
    echo   [WARN] assets\donate_qrcode.png not found
)

if "%VERIFY_FAIL%"=="1" (
    echo [ERROR] Verification failed
    pause
    exit /b 1
)

echo [OK] Verification passed
echo.

:: ========== Phase 7: Create ZIP ==========
echo [Phase 8/8] Creating ZIP file...

pushd "%DIST_DIR%"
set "ZIP_NAME=%APP_NAME%-v%VERSION%-Windows-Portable.zip"

powershell -Command "Compress-Archive -Path '%APP_NAME%' -DestinationPath '%ZIP_NAME%' -Force"

if exist "%ZIP_NAME%" (
    move /y "%ZIP_NAME%" "%RELEASE_DIR%\" >nul 2>&1
    echo [OK] ZIP created: releases\windows\%ZIP_NAME%
) else (
    echo [WARN] ZIP creation may have failed
)

popd
echo.

:: Generate checksum
echo [INFO] Generating SHA256 checksum...
certutil -hashfile "%RELEASE_DIR%\%ZIP_NAME%" SHA256 2>nul | findstr /v "CertUtil" > "%RELEASE_DIR%\%ZIP_NAME%.sha256"
echo [OK] Checksum saved
echo.

:: ========== Complete ==========
echo ========================================
echo   [OK] Build complete
echo ========================================
echo.
echo Output files:
echo   - Portable: %RELEASE_DIR%\%ZIP_NAME%
echo   - Checksum: %RELEASE_DIR%\%ZIP_NAME%.sha256
echo.
echo Usage:
echo   1. Extract ZIP to any directory
echo   2. Run PrivacyGuard.exe or launcher_wrapper.bat
echo   3. No installation required
echo.

:: Ask to test
set /p TEST_NOW="Test run now? (y/n): "
if /i "%TEST_NOW%"=="y" (
    echo.
    echo [TEST] Starting application...
    start "" "%DIST_DIR%\%APP_NAME%\launcher_wrapper.bat"
)

echo.
pause
