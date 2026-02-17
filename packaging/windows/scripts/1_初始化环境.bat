@echo off
:: 使用系统默认代码页，避免 UTF-8 兼容性问题
chcp 936 > nul 2>&1
title PrivacyGuard Environment Setup
echo.
echo ========================================
echo   PrivacyGuard Environment Setup
echo ========================================
echo.

:: 获取项目路径 (从 packaging/windows/scripts/ 到项目根目录)
set "PROJECT_DIR=%~dp0..\..\.."
cd /d "%PROJECT_DIR%" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to change to project directory: %PROJECT_DIR%
    pause
    exit /b 1
)

echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo.
    echo Please install Python 3.11 or higher:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%a in ('python --version') do set PYTHON_VERSION=%%a
echo [OK] Python version: %PYTHON_VERSION%
echo.

echo [2/5] Creating virtual environment...
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment already exists, skipping creation
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully
)
echo.

echo [3/5] Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat

:: 升级 pip
python -m pip install --upgrade pip -q

echo    Installing packages (this may take a few minutes)...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully
echo.

echo [4/5] Installing PyInstaller...
pip install pyinstaller -q
echo [OK] PyInstaller installed successfully
echo.

echo [5/5] Checking project files...
if not exist "main.py" (
    echo [ERROR] main.py not found
    pause
    exit /b 1
)
echo [OK] Project files check passed
echo.

echo ========================================
echo   [OK] Environment setup complete!
echo ========================================
echo.
echo You can now run build scripts:
echo   - 2_build_exe.bat        (Build executable only)
echo   - 3_build_with_setup.bat (Build executable + installer)
echo.
pause
