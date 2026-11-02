@echo off
setlocal EnableExtensions DisableDelayedExpansion
title PrivacyGuard Windows Portable Build
set "PRIVACYGUARD_NONINTERACTIVE=1"
pushd "%~dp0"
if errorlevel 1 exit /b 1
echo [1/2] Preparing Windows x64 Python and dependencies...
call packaging\windows\scripts\1_init_environment.bat
if errorlevel 1 goto failed
echo [2/2] Testing and building the portable release...
call packaging\windows\scripts\build_complete.bat
if errorlevel 1 goto failed
echo.
echo [OK] Release ZIP and SHA256: %CD%\releases\windows
popd
pause
exit /b 0
:failed
echo.
echo [ERROR] Build stopped. Read the first error above; no release is approved.
popd
pause
exit /b 1
