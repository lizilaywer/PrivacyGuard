@echo off
:: PrivacyGuard Build Script (Enhanced for DLL issues)
chcp 65001 > nul 2>&1
title PrivacyGuard Build - Enhanced

echo.
echo ========================================
echo   PrivacyGuard Build Script (Enhanced)
echo   DLL Issue Fix Edition
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

:: Menu
echo.
echo 请选择构建选项:
echo.
echo  [1] 标准构建 (使用原始 spec)
echo  [2] 增强构建 (使用 v2 spec, 更适合解决 DLL 问题)
echo  [3] 运行诊断工具 (检查 onnxruntime 状态)
echo  [4] 运行 VC++ 安装检查
echo.
set /p BUILD_OPTION="选项 (1-4): "

if "%BUILD_OPTION%"=="3" (
    echo.
    echo [DIAGNOSTIC] Running onnxruntime diagnostic...
    call venv\Scripts\activate.bat
    python "%~dp0\diagnose_onnxruntime.py"
    pause
    exit /b 0
)

if "%BUILD_OPTION%"=="4" (
    echo.
    echo [CHECK] Running VC++ Redistributable check...
    call "%~dp0\check_vcredist.bat"
    pause
    exit /b 0
)

:: Select spec file
set "SPEC_FILE="
if "%BUILD_OPTION%"=="2" (
    set "SPEC_FILE=%CONFIG_DIR%\PrivacyGuard_windows_v2.spec"
    echo [INFO] Using ENHANCED spec (v2) for better DLL compatibility
) else (
    set "SPEC_FILE=%CONFIG_DIR%\PrivacyGuard_windows.spec"
    echo [INFO] Using STANDARD spec
)

if not exist "%SPEC_FILE%" (
    echo [ERROR] Spec file not found: %SPEC_FILE%
    pause
    exit /b 1
)

echo.
echo [CHECK] Checking environment...
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: 1_init_environment.bat
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

:: Check for VC++ runtime
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
        echo [CRITICAL] vcruntime140_1.dll is REQUIRED.
        echo.
        echo Please download and install:
        echo https://aka.ms/vs/17/release/vc_redist.x64.exe
        echo.
        echo The build will continue, but the app WILL fail to run.
        echo.
        pause
    )
) else (
    echo [OK] All required VC++ runtime files found
)
echo.

:: Additional diagnostic for v2 build
if "%BUILD_OPTION%"=="2" (
    echo [PRE-BUILD] Running pre-build diagnostic...
    python "%~dp0\diagnose_onnxruntime.py" > "%PROJECT_DIR%\dist\build_diagnostic.log" 2>&1
    echo [OK] Diagnostic log saved to dist\build_diagnostic.log
    echo.
)

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

echo [2/4] Building executable (5-15 minutes)...
echo    Using spec: %SPEC_FILE%
echo    Please wait...
echo.

pyinstaller --clean --noconfirm "%SPEC_FILE%"

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
    echo.
    echo [IMPORTANT] Files copied:
    echo    - launcher_wrapper.bat (recommended launcher)
    echo.
    if "%BUILD_OPTION%"=="2" (
        echo [NOTE] This is an ENHANCED build with:
        echo    - More detailed DLL collection
        echo    - Console window enabled for debugging
        echo    - Run launcher_wrapper.bat to test
    )
)
echo.

:: Ask to test
set /p TEST_NOW="Run test now? (y/n): "
if /i "%TEST_NOW%"=="y" (
    echo.
    echo Starting PrivacyGuard...
    if exist "%DIST_DIR%\%APP_NAME%\launcher_wrapper.bat" (
        start "" "%DIST_DIR%\%APP_NAME%\launcher_wrapper.bat"
    ) else (
        start "" "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe"
    )
)

echo.
pause
