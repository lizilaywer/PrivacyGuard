# PrivacyGuard Windows 打包指南

> 当前 active Windows 打包流程说明。本文档以 `packaging/windows/` 下现有脚本和配置为准。

---

## 当前发布基线

- 当前版本：`v37.7.4`
- 版本标识：`37.7.4 - Release Audit and Final Polish`
- 版本唯一来源：项目根目录 `version.txt`

---

## 快速开始

### 便携包

```cmd
cd C:\Users\YourName\Desktop\PrivacyGuardApp
packaging\windows\scripts\build_complete.bat
```

输出：

- `releases\windows\PrivacyGuard-v<version>-Windows-Portable.zip`
- `releases\windows\PrivacyGuard-v<version>-Windows-Portable.zip.sha256`

这是当前 **便携版正式发布入口**。

### 安装包

```cmd
cd C:\Users\YourName\Desktop\PrivacyGuardApp
packaging\windows\scripts\3_build_with_setup.bat
```

输出：

- `releases\windows\PrivacyGuard-<version>-Setup.exe`
- `releases\windows\PrivacyGuard-<version>-Setup.exe.sha256`

这是当前 **安装版正式发布入口**。

---

## 当前脚本分工

| 脚本 | 作用 |
|------|------|
| `1_init_environment.bat` | 初始化 Windows 打包环境，创建 `venv_win` |
| `2_build_exe.bat` | 构建标准 one-dir 便携版 |
| `3_build_with_setup.bat` | 构建便携版并生成安装包 |
| `4_create_installer_only.bat` | 基于已有 `dist/` 结果生成安装包 |
| `build_complete.bat` | 完整发布便携 ZIP |
| `verify_dependencies.py` | 构建前依赖校验 |
| `check_vcredist.bat` | VC++ 运行库检查 |
| `diagnose_onnxruntime.py` | onnxruntime 诊断 |
| `generate_version_info.py` | 从 `version.txt` 生成 Windows EXE 版本资源 |

---

## 构建前要求

- Windows 10/11 64 位
- Python 3.11+
- Inno Setup 6（仅安装包场景）
- Visual C++ Redistributable 2015-2022 x64

推荐初始化：

```cmd
packaging\windows\scripts\1_init_environment.bat
```

---

## 版本来源与版本资源

- `version.txt` 是唯一版本源
- 安装包版本通过 `/DMyAppVersion=<version>` 注入 `PrivacyGuard_Setup.iss`
- EXE 版本资源由 `packaging/windows/scripts/generate_version_info.py` 自动生成到：

```text
packaging/windows/config/version_info.txt
```

当前 `v37.7.4` 同步内容：

- `version_info.txt` 版本资源：`37.7.4.0`
- `PrivacyGuard_windows.spec` 补齐 `privacyguard` 相关 hiddenimports
- 新增 `hook-privacyguard.py` 与 `runtime_hook_privacyguard.py`
- 安装器构建仍通过 `/DMyAppVersion=<version>` 从 `version.txt` 注入版本号
- `PrivacyGuard_Setup.iss` 默认回退版本已同步到 `37.7.4`

## 当前打包执行约定

- 先激活当前虚拟环境，再通过 `python -m PyInstaller` 执行打包
- PyInstaller 缓存固定到项目内：

```text
build\.pyinstaller-cache
```

- 这样可以避免误用系统里其它 Python / PyInstaller，也能避免依赖用户目录下的全局缓存

---

## 推荐发布流程

### 一句话结论

- 如果你要发 **便携版**，执行：`build_complete.bat`
- 如果你要发 **安装版**，执行：`3_build_with_setup.bat`

### 发布便携 ZIP

1. 运行 `1_init_environment.bat`
2. 运行 `build_complete.bat`
3. 校验以下文件是否存在：
   - `releases/windows/PrivacyGuard-v<version>-Windows-Portable.zip`
   - `releases/windows/PrivacyGuard-v<version>-Windows-Portable.zip.sha256`
4. 解压后优先使用 `launcher_wrapper.bat` 启动一次

### 发布安装包

1. 安装 Inno Setup 6
2. 运行 `3_build_with_setup.bat`
3. 校验以下文件是否存在：
   - `releases/windows/PrivacyGuard-<version>-Setup.exe`
   - `releases/windows/PrivacyGuard-<version>-Setup.exe.sha256`

---

## 关键配置

### PyInstaller spec

- 标准 spec：`packaging/windows/config/PrivacyGuard_windows.spec`
- 历史增强 spec：`packaging/windows/config/PrivacyGuard_windows_v2.spec`（保留归档，不作为当前正式主链）

### Inno Setup

配置文件：

```text
packaging/windows/config/PrivacyGuard_Setup.iss
```

当前安装器策略：

- 64 位安装模式：`ArchitecturesAllowed=x64compatible`
- 64 位目录安装：`ArchitecturesInstallIn64BitMode=x64compatible`
- 开始菜单、桌面快捷方式默认走 `launcher_wrapper.bat`

---

## 本轮说明

- PyInstaller 打包模块导入失败修复直接影响 Windows 打包可用性
- 本轮 packaging 更新重点是：导入修复、版本资源、脚本执行环境统一、文档说明同步到当前基线
- 当前正式发布建议已收口，不再推荐从其它批处理脚本绕行：
  - 便携包：`build_complete.bat`
  - 安装包：`3_build_with_setup.bat`
- 2026-03-18 已在当前 macOS 开发机完成：
  - `generate_version_info.py`
  - `python3 -m compileall -q packaging`
  - Windows 脚本链 / spec / Inno Setup 配置 / 文档一致性复核
- 2026-03-18 已清理 `packaging/windows/scripts/` 下不再属于正式主链的历史兼容与解除阻止脚本
- 由于当前机器不是 Windows，本轮未实际执行：
  - `packaging\windows\scripts\build_complete.bat`
  - `packaging\windows\scripts\3_build_with_setup.bat`
- 对外发布前，仍需在 Windows 真机至少完成一次：
  - 便携包链路验证
  - 安装包链路验证

---

## 发布前检查清单

- `version.txt` 已更新
- `generate_version_info.py` 已成功执行
- `build_complete.bat` 或 `3_build_with_setup.bat` 已成功执行
- 产物和 `.sha256` 已生成
- 解压或安装后能成功启动 `PrivacyGuard`
- PDF / Word / OCR 基本流程至少手测一次

最后更新：2026-03-18
