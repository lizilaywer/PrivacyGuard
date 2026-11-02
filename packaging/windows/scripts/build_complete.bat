@echo off
setlocal EnableExtensions DisableDelayedExpansion
title PrivacyGuard Windows Portable Build
for %%I in ("%~dp0..\..\..") do set "PROJECT_DIR=%%~fI"
set "PY=%PROJECT_DIR%\venv_win\Scripts\python.exe"
if defined PRIVACYGUARD_PYTHON set "PY=%PRIVACYGUARD_PYTHON%"
if not exist "%PY%" (
    echo [ERROR] Windows Python environment not found: "%PY%"
    echo [HINT] Run packaging\windows\scripts\1_init_environment.bat first.
    if not defined PRIVACYGUARD_NONINTERACTIVE pause
    exit /b 1
)
"%PY%" "%~dp0build_portable.py"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo [ERROR] Build failed. No validated portable release was produced.
if not defined PRIVACYGUARD_NONINTERACTIVE pause
exit /b %RESULT%
