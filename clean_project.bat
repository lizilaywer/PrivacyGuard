@echo off
:: PrivacyGuard 项目清理脚本 (Windows)
:: 清理临时文件，但保留旧备份
chcp 65001 > nul 2>&1
title PrivacyGuard 项目清理

echo.
echo ======================================
echo   PrivacyGuard 项目清理 (Windows)
echo ======================================
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo [INFO] 项目目录: %PROJECT_DIR%
echo.

:: 清理构建输出
echo [1/6] 清理构建输出...
if exist "dist" (
    rmdir /s /q "dist" 2>nul
    echo       [OK] 已删除 dist/
)
if exist "build" (
    rmdir /s /q "build" 2>nul
    echo       [OK] 已删除 build/
)
echo.

:: 清理 Python 缓存
echo [2/6] 清理 Python 缓存...
for /f "delims=" %%i in ('dir /s /b "__pycache__" 2^>nul') do (
    rmdir /s /q "%%i" 2>nul
)
for /f "delims=" %%i in ('dir /s /b "*.pyc" 2^>nul') do (
    del /f /q "%%i" 2>nul
)
for /f "delims=" %%i in ('dir /s /b "*.pyo" 2^>nul') do (
    del /f /q "%%i" 2>nul
)
echo       [OK] 已清理 __pycache__, *.pyc, *.pyo
echo.

:: 清理测试临时文件
echo [3/6] 清理测试临时文件...
if exist "tests\temp" (
    del /f /q "tests\temp\*" 2>nul
    echo       [OK] 已清理 tests\temp\
)
echo.

:: 清理日志文件
echo [4/6] 清理旧日志文件...
forfiles /p . /s /m *.log /d -7 /c "cmd /c del @path" 2>nul
echo       [OK] 已删除7天前的日志
echo.

:: 保留备份目录
echo [5/6] 检查备份目录...
if exist "backups" (
    for /f %%i in ('dir /b /ad "backups\v*" 2^>nul ^| find /c /v ""') do (
        echo       [OK] 保留所有备份目录（共 %%i 个版本备份）
    )
) else (
    echo       - 无备份目录
)
echo.

:: 统计项目大小
echo [6/6] 统计项目大小...
for /f "tokens=3" %%a in ('dir /s /-c 2^>nul ^| findstr "文件" ^| findstr "字节"') do (
    echo       项目总大小: %%a 字节
    goto :size_done
)
:size_done
echo.

echo ======================================
echo   清理完成！
echo ======================================
echo.
echo 注意: 以下目录被保留（按用户要求）:
echo   - backups\      (版本备份)
echo   - tests\        (测试文件)
echo   - docs\         (开发文档)
echo   - packaging\    (打包配置)
echo.
pause
