@echo off
:: PrivacyGuard Build Script
chcp 65001 > nul 2>&1
title PrivacyGuard Build
echo.
echo ========================================
echo   PrivacyGuard Build Script
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

echo [CHECK] Checking environment...
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: 1_init_environment.bat
    pause
    exit /b 1
)

if not exist "%CONFIG_DIR%\PrivacyGuard_windows.spec" (
    echo [ERROR] Build configuration not found
    pause
    exit /b 1
)

echo [OK] Environment check passed
echo.

:: Activate virtual environment
call venv\Scripts\activate.bat

echo [PRE-CHECK] Checking VC++ Redistributable...
echo    (Required for onnxruntime/OCR functionality)
echo.

:: Check for VC++ runtime (包括 vcruntime140_1.dll)
set "VCRT_MISSING=0"
set "VCRT_MISSING_CRITICAL=0"

if not exist "C:\Windows\System32\vcruntime140.dll" (
    echo    [MISSING] vcruntime140.dll
    set "VCRT_MISSING=1"
)
if not exist "C:\Windows\System32\msvcp140.dll" (
    echo    [MISSING] msvcp140.dll
    set "VCRT_MISSING=1"
)
if not exist "C:\Windows\System32\vcruntime140_1.dll" (
    echo    [MISSING] vcruntime140_1.dll (CRITICAL for onnxruntime)
    set "VCRT_MISSING=1"
    set "VCRT_MISSING_CRITICAL=1"
)

if "%VCRT_MISSING%"=="1" (
    echo.
    echo [WARNING] VC++ Redistributable files are missing!
    echo.
    if "%VCRT_MISSING_CRITICAL%"=="1" (
        echo [CRITICAL] vcruntime140_1.dll is REQUIRED for OCR functionality.
        echo This DLL is part of the newer VC++ Redistributable package.
        echo.
    )
    echo Please download and install:
    echo https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    echo The build will continue, but the app may fail to run.
    echo.
    pause
) else (
    echo [OK] All required VC++ runtime files found
)
echo.

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

echo [2/4] Building executable (5-10 minutes)...
echo    Please wait...
echo.

pyinstaller --clean --noconfirm "%CONFIG_DIR%\PrivacyGuard_windows.spec"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo.
    echo Check error messages above
    pause
    exit /b 1
)

echo [OK] Build complete
echo.

echo [3/4] Copying files...
if exist "%PROJECT_DIR%\LICENSE.txt" (
    copy "%PROJECT_DIR%\LICENSE.txt" "%DIST_DIR%\%APP_NAME%\" >nul 2>&1
)
if exist "%PROJECT_DIR%\README.md" (
    copy "%PROJECT_DIR%\README.md" "%DIST_DIR%\%APP_NAME%\" >nul 2>&1
)
:: Copy launcher wrapper for DLL checking
copy "%~dp0launcher_wrapper.bat" "%DIST_DIR%\%APP_NAME%\" >nul 2>&1
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
echo Output:
if exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
    echo    %DIST_DIR%\%APP_NAME%\%APP_NAME%.exe
    for %%I in ("%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe") do (
        echo    Size: %%~zI bytes
    )
    echo    %DIST_DIR%\%APP_NAME%\launcher_wrapper.bat (recommended launcher)
) else if exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo    %DIST_DIR%\%APP_NAME%.exe
    for %%I in ("%DIST_DIR%\%APP_NAME%.exe") do (
        echo    Size: %%~zI bytes
    )
)
echo.

:: Ask to test
set /p TEST_NOW="Run test now? (y/n): "
if /i "%TEST_NOW%"=="y" (
    echo.
    echo Starting PrivacyGuard...
    :: Use launcher wrapper for DLL checking
    if exist "%DIST_DIR%\%APP_NAME%\launcher_wrapper.bat" (
        start "" "%DIST_DIR%\%APP_NAME%\launcher_wrapper.bat"
    ) else if exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
        start "" "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe"
    ) else if exist "%DIST_DIR%\%APP_NAME%.exe" (
        start "" "%DIST_DIR%\%APP_NAME%.exe"
    )
)

echo.
pause
