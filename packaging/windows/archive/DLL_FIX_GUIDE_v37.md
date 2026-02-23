# PrivacyGuard v37.0 Windows DLL 问题修复指南

## 问题概述

**错误信息**:
```
ImportError: DLL load failed while importing onnxruntime_pybind11_state:
动态链接库(DLL)初始化例程失败
```

**根本原因**: `onnxruntime 1.24.1` 需要 `vcruntime140_1.dll`，但 PyInstaller 可能未正确收集或该 DLL 在目标系统上缺失。

---

## 修复方案 (按优先级排序)

### 方案 1: 在打包机器上安装 VC++ Redistributable (推荐)

1. 下载并安装 VC++ Redistributable 2015-2022:
   ```
   https://aka.ms/vs/17/release/vc_redist.x64.exe
   ```

2. 安装完成后，重新运行打包脚本:
   ```cmd
   cd packaging\windows\scripts
   2_build_exe_enhanced.bat
   # 选择选项 2 (增强构建)
   ```

3. 验证 DLL 已被收集:
   ```cmd
   dir dist\PrivacyGuard\
   # 应该能看到 vcruntime140_1.dll
   ```

### 方案 2: 使用增强版构建脚本

1. 使用新的增强版构建脚本:
   ```cmd
   cd packaging\windows\scripts
   2_build_exe_enhanced.bat
   ```

2. 在菜单中选择:
   - `[3]` 先运行诊断工具，检查 DLL 状态
   - `[2]` 使用增强版 spec (v2) 构建

3. 增强版 spec 的改进:
   - 递归收集 onnxruntime 所有文件
   - 从多个位置搜索 VC++ DLL
   - 启用控制台窗口以查看错误信息
   - 更完整的 hidden imports

### 方案 3: 手动复制 DLL

如果自动收集失败，手动复制 DLL:

1. 找到 `vcruntime140_1.dll`:
   ```cmd
   dir C:\Windows\System32\vcruntime140_1.dll
   ```

2. 复制到打包输出目录:
   ```cmd
   copy C:\Windows\System32\vcruntime140_1.dll dist\PrivacyGuard\
   copy C:\Windows\System32\vcruntime140.dll dist\PrivacyGuard\
   copy C:\Windows\System32\msvcp140.dll dist\PrivacyGuard\
   ```

### 方案 4: 降级 onnxruntime

如果以上方案都失败，尝试使用旧版本 onnxruntime:

```cmd
venv\Scripts\activate
pip uninstall onnxruntime -y
pip install onnxruntime==1.15.1
```

然后重新打包。

---

## 验证步骤

### 1. 运行诊断工具

```cmd
venv\Scripts\activate
python packaging\windows\scripts\diagnose_onnxruntime.py
```

检查输出:
- ✓ 所有 VC++ DLL 都已找到
- ✓ onnxruntime 导入链正常
- ✓ 推理测试通过

### 2. 检查打包输出

```cmd
dir dist\PrivacyGuard\*.dll /w
```

确认以下文件存在:
- `vcruntime140.dll`
- `vcruntime140_1.dll` (关键)
- `msvcp140.dll`
- `onnxruntime_pybind11_state.pyd`

### 3. 测试运行

使用启动器包装器运行（会检查 DLL）:
```cmd
dist\PrivacyGuard\launcher_wrapper.bat
```

或直接运行（可以看到错误信息）:
```cmd
dist\PrivacyGuard\PrivacyGuard.exe
```

---

## 常见问题

### Q: 为什么 macOS 正常但 Windows 失败？

A: macOS 和 Windows 的依赖机制不同:
- macOS: 使用 .dylib，系统自带或 PyInstaller 能正确收集
- Windows: 使用 .dll，VC++ runtime 版本依赖严格，且 `vcruntime140_1.dll` 是 VS2019+ 新增的

### Q: 目标机器上也需要安装 VC++ Redistributable 吗？

A: 理论上不需要，如果打包时正确收集了 DLL。但如果收集失败，用户机器上需要有这些 DLL。

### Q: 如何确认是 DLL 问题还是其他问题？

A: 使用增强版 spec (v2) 构建，它会:
1. 启用控制台窗口显示详细错误
2. 生成诊断日志
3. 收集更多调试信息

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `PrivacyGuard_windows.spec` | 原始 spec 文件 |
| `PrivacyGuard_windows_v2.spec` | 增强版 spec，更好的 DLL 收集 |
| `2_build_exe.bat` | 原始构建脚本 |
| `2_build_exe_enhanced.bat` | 增强版构建脚本，带诊断选项 |
| `diagnose_onnxruntime.py` | 诊断工具，检查 DLL 状态 |
| `launcher_wrapper.bat` | 启动器，检查 DLL 后启动应用 |

---

## 紧急修复

如果需要在不重新打包的情况下修复，创建一个批处理文件:

```batch
@echo off
:: PrivacyGuard 紧急修复启动器
set "APP_DIR=%~dp0"

:: 检查 DLL
if not exist "C:\Windows\System32\vcruntime140_1.dll" (
    echo [ERROR] 缺少必需的 VC++ DLL
    echo.
    echo 请下载安装:
    echo https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    pause
    exit /b 1
)

:: 复制 DLL 到应用目录（临时解决方案）
copy "C:\Windows\System32\vcruntime140_1.dll" "%APP_DIR%" >nul 2>&1
copy "C:\Windows\System32\vcruntime140.dll" "%APP_DIR%" >nul 2>&1
copy "C:\Windows\System32\msvcp140.dll" "%APP_DIR%" >nul 2>&1

:: 启动应用
start "" "%APP_DIR%\PrivacyGuard.exe"
```

保存为 `emergency_launcher.bat` 放在应用目录。

---

## 联系支持

如果以上方案都无法解决问题:

1. 运行诊断工具并保存输出:
   ```cmd
   python packaging\windows\scripts\diagnose_onnxruntime.py > diagnostic_log.txt 2>&1
   ```

2. 收集以下信息:
   - Windows 版本 (`winver`)
   - Python 版本 (`python --version`)
   - 诊断日志

3. 提交 Issue 或联系开发团队。
