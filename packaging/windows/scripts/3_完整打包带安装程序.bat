@echo off
:: Use system default code page to avoid UTF-8 compatibility issues
chcp 936 > nul 2>&1
title PrivacyGuard Full Build (with Installer)
echo.
echo ========================================
echo   PrivacyGuard Full Build Script
echo   (Generate exe + Installer)
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

echo [OK] Environment check passed
echo.

:: Activate virtual environment
call venv\Scripts\activate.bat

echo [Step 1/5] Cleaning old builds...
if exist "%DIST_DIR%" (
    rmdir /s /q "%DIST_DIR%" 2>nul
)
if exist "build\build" (
    rmdir /s /q "build\build" 2>nul
)
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
echo [OK] Cleanup complete
echo.

echo [Step 2/5] Building application...
echo    This may take 5-10 minutes, please wait...
echo.

pyinstaller --clean --noconfirm "%CONFIG_DIR%\PrivacyGuard_windows.spec"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [OK] Application build complete
echo.

echo [Step 3/5] Copying additional files...
if exist "%PROJECT_DIR%\LICENSE.txt" (
    copy "%PROJECT_DIR%\LICENSE.txt" "%DIST_DIR%\" >nul 2>&1
)
if exist "%PROJECT_DIR%\README.md" (
    copy "%PROJECT_DIR%\README.md" "%DIST_DIR%\" >nul 2>&1
)
echo [OK] Done
echo.

echo [Step 4/5] Generating portable version checksum...
if exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
    certutil -hashfile "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" SHA256 2>nul | findstr /v "CertUtil" | findstr /v "SHA256" > "%RELEASE_DIR%\%APP_NAME%-%VERSION%-portable.exe.sha256"
) else if exist "%DIST_DIR%\%APP_NAME%.exe" (
    certutil -hashfile "%DIST_DIR%\%APP_NAME%.exe" SHA256 2>nul | findstr /v "CertUtil" | findstr /v "SHA256" > "%RELEASE_DIR%\%APP_NAME%-%VERSION%-portable.exe.sha256"
)
echo [OK] Checksum generated
echo.

echo [Step 5/5] Creating installer...
echo    Checking Inno Setup...

:: Try to find Inno Setup from common locations
set "INNO_PATH="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "C:\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Inno Setup 6\ISCC.exe"
)

if not defined INNO_PATH (
    echo [WARNING] Inno Setup not found!
    echo.
    echo Please download and install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo Then run this script again.
    echo.
    echo [TIP] You can still use the portable version (dist\PrivacyGuard\PrivacyGuard.exe)
    pause
    exit /b 1
)

echo    Compiling installer...
"%INNO_PATH%" "%CONFIG_DIR%\PrivacyGuard_Setup.iss" /Q

if errorlevel 1 (
    echo [ERROR] Failed to create installer
    pause
    exit /b 1
)

echo [OK] Installer created
echo.

echo [BONUS] Generating installer checksum...
if exist "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe" (
    certutil -hashfile "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe" SHA256 2>nul | findstr /v "CertUtil" | findstr /v "SHA256" > "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe.sha256"
)
echo [OK] Done
echo.

echo ========================================
echo   [OK] Full build successful!
echo ========================================
echo.
echo [OUTPUT] Output files:
echo.
echo [Portable] - Run directly, no installation needed
if exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
    echo    %DIST_DIR%\%APP_NAME%\%APP_NAME%.exe
    for %%I in ("%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe") do (
        echo    Size: %%~zI bytes
    )
) else if exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo    %DIST_DIR%\%APP_NAME%.exe
    for %%I in ("%DIST_DIR%\%APP_NAME%.exe") do (
        echo    Size: %%~zI bytes
    )
)
echo    - Good for: Quick testing, USB portable use
echo.
echo [Installer] - With setup wizard
if exist "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe" (
    echo    %RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe
    for %%I in ("%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe") do (
        echo    Size: %%~zI bytes
    )
    echo    - Good for: Distribution to end users
)
echo.
echo [USAGE TIPS]:
echo    - For testing: Run dist\PrivacyGuard\PrivacyGuard.exe
    echo    - For distribution: Send releases\windows\PrivacyGuard-%VERSION%-Setup.exe
    echo    - For release: Upload both to GitHub Releases
echo.

:: Ask if user wants to open output directory
set /p OPEN_DIR="Open output directory? (y/n): "
if /i "%OPEN_DIR%"=="y" (
    start "" "%RELEASE_DIR%"
)

echo.
pause
