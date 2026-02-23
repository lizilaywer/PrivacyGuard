@echo off
:: PrivacyGuard - 解除文件阻止 (手动方法)
chcp 65001 > nul 2>&1
title 解除文件阻止 - 手动方法
echo.
echo ========================================
echo   解除文件阻止 - 手动方法
echo ========================================
echo.
echo 如果自动脚本无法运行，请使用以下方法：
echo.
echo -------- 方法1: 右键解除 (推荐) --------
echo.
echo 1. 在文件资源管理器中，右键点击批处理文件
echo 2. 选择 [属性]
echo 3. 在 [常规] 选项卡底部，勾选 [解除锁定]
echo 4. 点击 [确定]
echo.
echo 需要对以下文件执行此操作：
echo   - 2_build_exe_fix_dll.bat
echo   - 2_build_exe.bat
echo   - launcher_wrapper.bat
echo.
echo -------- 方法2: PowerShell 命令 --------
echo.
echo 在项目目录打开 PowerShell，运行：
echo.
echo   Get-ChildItem -Path "packaging\windows\scripts" -Recurse ^| Unblock-File
echo.
echo -------- 方法3: 复制到新文件 --------
echo.
echo 有时复制文件可以解除阻止：
echo.
echo   1. 选中所有 .bat 文件
echo   2. 复制 (Ctrl+C)
echo   3. 粘贴到一个新文件夹
echo   4. 从新文件夹运行脚本
echo.
echo ========================================
echo.
pause
