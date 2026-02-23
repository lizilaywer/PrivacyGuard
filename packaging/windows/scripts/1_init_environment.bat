@echo off
:: PrivacyGuard Environment Setup
chcp 65001 > nul 2>&1
title PrivacyGuard Environment Setup
echo.
echo ========================================
echo   PrivacyGuard Environment Setup
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

echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo.
    echo Please install Python 3.11 or higher:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%a in ('python --version') do set PYTHON_VERSION=%%a
echo [OK] Python version: %PYTHON_VERSION%
echo.

echo [2/5] Creating virtual environment (Windows: venv_win)...
if exist "venv_win\Scripts\activate.bat" (
    echo [INFO] Windows virtual environment (venv_win) already exists
) else if exist "venv\Scripts\activate.bat" (
    echo [WARN] Found venv (may be macOS-created), creating venv_win for Windows
    python -m venv venv_win
    if errorlevel 1 (
        echo [ERROR] Failed to create venv_win
        pause
        exit /b 1
    )
    echo [OK] Windows virtual environment (venv_win) created
) else (
    python -m venv venv_win
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment (venv_win) created
)
echo.

echo [3/5] Installing dependencies...
call venv_win\Scripts\activate.bat
python -m pip install --upgrade pip -q
echo    Installing packages (may take a few minutes)...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

echo [4/5] Installing PyInstaller...
pip install pyinstaller -q
echo [OK] PyInstaller installed
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
echo   [OK] Setup complete!
echo ========================================
echo.
echo Next steps:
echo   - 2_build_exe.bat        (Build executable)
echo   - 3_build_with_setup.bat (Build + installer)
echo.
pause
