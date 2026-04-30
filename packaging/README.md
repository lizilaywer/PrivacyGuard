# PrivacyGuard 打包目录说明（索引）

本目录只保留打包脚本、spec、安装程序配置和轻量索引。完整说明统一维护在：

- `docs/packaging/README.md`
- `docs/packaging/windows-packaging-guide.md`
- `docs/packaging/macos-packaging-guide.md`

---

## 当前打包发布基线

- 当前应用版本：`v37.7.4`
- 版本标识：`37.7.4 - Release Audit and Final Polish`
- 版本唯一来源：项目根目录 `version.txt`

---

## 当前约定

- Windows EXE 版本资源：`packaging/windows/scripts/generate_version_info.py` 在构建前自动生成
- Windows / macOS PyInstaller 统一绑定当前虚拟环境，并使用项目内缓存：
  - Windows：`build\.pyinstaller-cache`
  - macOS：`build/.pyinstaller-cache`
- Windows 主要产物：
  - `releases/windows/PrivacyGuard-v<version>-Windows-Portable.zip`
  - `releases/windows/PrivacyGuard-<version>-Setup.exe`
- macOS 主要产物：
  - `releases/macos/PrivacyGuard-<version>-macOS.dmg`
  - `releases/macos/PrivacyGuard-<version>-macOS.dmg.sha256`
  - 若当前环境无法完成 DMG 创建，脚本会保底复制 `releases/macos/PrivacyGuard.app`

---

## 推荐入口

### Windows

正式发布建议：

- 便携版：`packaging\windows\scripts\build_complete.bat`
- 安装版：`packaging\windows\scripts\3_build_with_setup.bat`

其中：
- `build_complete.bat` 用于生成便携 ZIP 与 `.sha256`
- `3_build_with_setup.bat` 用于生成安装包 `Setup.exe` 与 `.sha256`

```cmd
packaging\windows\scripts\build_complete.bat
```

如需安装包：

```cmd
packaging\windows\scripts\3_build_with_setup.bat
```

### macOS

正式发布建议：

- 默认执行：`bash packaging/macos/scripts/build_complete.sh`
- 若只需要 `.app` 或先做签名准备，可执行：`bash packaging/macos/scripts/build_macos_app.sh`

```bash
bash packaging/macos/scripts/build_complete.sh
```

---

## 目录说明

- `packaging/windows/`: Windows 打包脚本、PyInstaller spec、Inno Setup 配置
- `packaging/macos/`: macOS 打包脚本、签名、公证、entitlements 配置
- `packaging/DUAL_OCR_PACKAGING.md`: OCR 打包补充说明（文件名保留，内容按单 OCR 维护）

---

## 2026-03-18 本轮同步内容

- Windows 安装器默认回退版本已同步到 `37.7.4`
- Windows / macOS 打包脚本改为优先使用当前虚拟环境中的 `PyInstaller`
- Windows / macOS 打包脚本统一切换到项目内 PyInstaller 缓存目录，避免依赖用户目录全局缓存
- `packaging/windows/scripts/` 已清理不再属于正式主链的历史兼容与解除阻止脚本
- macOS `build_complete.sh` 现在会在缺少 `create-dmg` 时明确回退到 `hdiutil`，失败后保底复制 `.app` 到发布目录
- Windows 正式发布入口已明确收口为：
  - 便携版：`build_complete.bat`
  - 安装版：`3_build_with_setup.bat`
- 本轮已验证：
  - `packaging/windows/scripts/generate_version_info.py`
  - `python3 -m compileall -q packaging`
  - macOS 打包脚本语法检查
  - `packaging/macos/scripts/build_complete.sh` 完整执行到 `.app` 产物生成与发布目录回退
- 当前机器上的真实结果：
  - macOS：已实际生成 `releases/macos/PrivacyGuard.app`
  - macOS：当前环境缺少 `create-dmg`，且 `hdiutil` 本次未成功生成 DMG
  - Windows：已完成静态复核，但未在当前 macOS 机器上实际执行 `.bat` / Inno Setup

最后同步：2026-03-18
