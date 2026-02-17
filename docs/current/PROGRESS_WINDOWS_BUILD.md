# Windows 打包进度记录

**创建时间**: 2026-02-13
**状态**: 待验证（需在 Windows 上重新打包测试）

---

## 问题描述

Windows 打包完成后，运行 `PrivacyGuard.exe` 出现以下错误：

```
ImportError: DLL load failed while importing onnxruntime_pybind11_state:
动态链接库(DLL)初始化例程失败。
```

**根本原因**:
1. onnxruntime 1.24.1 依赖 Visual C++ Redistributable 运行时库
2. PyInstaller 默认的 hook 没有正确收集所有 onnxruntime DLL 文件
3. 缺少必要的隐式导入配置

---

## 已完成的修改

### 修改文件: `packaging/windows/config/PrivacyGuard_windows.spec`

**1. 添加导入**
```python
from PyInstaller.utils.hooks import copy_metadata, collect_dynamic_libs, collect_data_files
```

**2. 添加 DLL 和数据文件收集**
```python
# 收集 onnxruntime 的动态库和数据文件
onnxruntime_binaries = collect_dynamic_libs('onnxruntime')
onnxruntime_datas = collect_data_files('onnxruntime')
```

**3. 更新 Analysis 配置**
```python
binaries=onnxruntime_binaries,  # 添加 onnxruntime DLL
datas=[
    (os.path.join(project_root, 'theme.py'), '.'),
] + onnxruntime_datas,  # 添加 onnxruntime 数据文件
```

**4. 添加完整的 onnxruntime 隐式导入链**
```python
# OCR - 完整导入链
'onnxruntime',
'onnxruntime.capi',
'onnxruntime.capi.onnxruntime_pybind11_state',
'onnxruntime.capi._pybind_state',
```

---

## 下一步操作（在 Windows 上执行）

### 1. 重新打包
```cmd
cd packaging\windows\scripts
build_windows.bat
```

### 2. 验证测试
- [ ] 应用启动正常
- [ ] OCR 功能正常
- [ ] 无 DLL 加载错误

---

## 备选方案

如果上述修改仍不能解决问题：

### 方案 B: 降级 onnxruntime
```txt
onnxruntime==1.16.3  # 更稳定的版本
```

### 方案 C: 使用 CPU 版本
```cmd
pip uninstall onnxruntime-gpu
pip install onnxruntime
```

### 方案 D: 手动复制 DLL
将以下文件手动复制到 dist 目录：
- `onnxruntime.dll`
- `msvcp140.dll`
- `vcruntime140.dll`

### 方案 E: 安装 VC++ Redistributable
确保 Windows 系统已安装最新版 Visual C++ Redistributable：
- 下载地址: https://aka.ms/vs/17/release/vc_redist.x64.exe

---

## 相关文件

| 文件 | 路径 |
|------|------|
| Spec 文件 | `packaging/windows/config/PrivacyGuard_windows.spec` |
| 构建脚本 | `packaging/windows/scripts/2_一键打包.bat` |
| 构建配置 | `packaging/windows/config/build_windows.py` |

---

## 依赖版本

- onnxruntime: 1.24.1
- rapidocr-onnxruntime: 1.2.3
- PyInstaller: (当前安装版本)

---

*此文件记录 Windows 打包问题的修复进度，请在验证后更新状态。*
