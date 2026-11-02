@echo off
setlocal EnableExtensions DisableDelayedExpansion
title PrivacyGuard Build Environment
for %%I in ("%~dp0..\..\..") do set "PROJECT_DIR=%%~fI"
pushd "%PROJECT_DIR%"
if errorlevel 1 exit /b 1
if not exist "main.py" goto failed
if exist "venv_win\Scripts\python.exe" goto install

echo [INFO] Creating a fresh Windows Python 3.11 x64 environment...
py -3.11 -c "import sys,struct; assert sys.platform == 'win32' and struct.calcsize('P') == 8" >nul 2>&1
if errorlevel 1 goto try_python
py -3.11 -m venv venv_win
if errorlevel 1 goto failed
goto install

:try_python
python -c "import sys,struct; assert sys.platform == 'win32' and sys.version_info[:2] == (3,11) and struct.calcsize('P') == 8" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Install Windows Python 3.11 x64 and enable Add Python to PATH.
    echo [HINT] https://www.python.org/downloads/windows/
    goto failed
)
python -m venv venv_win
if errorlevel 1 goto failed

:install
venv_win\Scripts\python.exe -c "import sys,struct; assert sys.platform == 'win32' and sys.version_info[:2] == (3,11) and struct.calcsize('P') == 8"
if errorlevel 1 (
    echo [ERROR] Existing venv_win is not a working Python 3.11 x64 environment.
    echo [HINT] Rename the old venv_win directory and run this script again.
    goto failed
)
venv_win\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto failed
venv_win\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
if errorlevel 1 goto failed
venv_win\Scripts\python.exe -m pip check
if errorlevel 1 goto failed
echo [OK] Build environment ready. Next: build_complete.bat
popd
if not defined PRIVACYGUARD_NONINTERACTIVE pause
exit /b 0

:failed
echo [ERROR] Environment initialization failed. Resolve the error above before building.
popd
if not defined PRIVACYGUARD_NONINTERACTIVE pause
exit /b 1
