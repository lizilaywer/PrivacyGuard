# PrivacyGuard 打包文档总览

本目录是打包说明的主入口，和 `packaging/` 目录内的轻量索引保持同步。

---

## 当前打包基线

- 当前应用版本：`v40.2.5`
- 版本标识：`40.2.5`
- 版本唯一来源：项目根目录 `version.txt`

---

## 推荐阅读顺序

1. `docs/packaging/windows-packaging-guide.md`
2. `docs/packaging/macos-packaging-guide.md`
3. `packaging/OCR_PACKAGING.md`
4. `packaging/README.md`

---

## 平台约定

### Windows
- 推荐脚本：`packaging/windows/scripts/build_complete.bat`
- 首次一键构建：根目录 `BUILD_WINDOWS_PORTABLE.bat`，要求 Windows Python 3.11 x64
- 安装包脚本：`packaging/windows/scripts/3_build_with_setup.bat`
- EXE 版本资源由 `packaging/windows/scripts/generate_version_info.py` 自动生成
- 安装器默认版本在 `packaging/windows/config/PrivacyGuard_Setup.iss`
- 便携脚本通过 `python -m PyInstaller` 绑定当前虚拟环境，缓存位于 `build/windows-portable/pyinstaller-cache`
- 便携中间产物 `dist/windows-portable/PrivacyGuard`；旧安装器仍使用 `dist/PrivacyGuard`
- 门禁包含全量回归、版本/离线模型/x64 DLL/隐私检查、冻结自检和 ZIP CRC/SHA256
- Mac 提供 `Windows-BuildKit.zip` 源码资料包，Windows 可运行成品须在 Windows 执行构建，未宣称跨平台构建成功

### macOS
- 推荐便携构建：`packaging/macos/scripts/build_portable.sh`
- 发布环境：`venv_macos_release/bin/python3`，或显式设置 `PRIVACYGUARD_PYTHON`
- 目标：Apple Silicon arm64 / macOS 14+；全包 Mach-O 审核通过才产生 ZIP
- 当前自检与边界：`docs/current/RELEASE_AUDIT_20261024.md`
- 历史 DMG 脚本：`packaging/macos/scripts/build_complete.sh`（不作为本次 ZIP 发布入口）
- 简化构建脚本：`packaging/macos/scripts/build_macos_app.sh`
- 证书与公证凭据通过环境变量注入
- `packaging/macos/config/PrivacyGuard.spec` 从 `version.txt` 动态读取版本号
- 脚本通过 `python3 -m PyInstaller` 绑定当前虚拟环境，并使用 `build/.pyinstaller-cache`

---

## 产物目录约定

- Windows：`releases/windows/`
- macOS：`releases/macos/`
- 中间构建：`build/`, `dist/`

---

## 本轮同步说明

> 当前版本 `v37.8.11`（2026-08-01）。下方为 2026-03-18 `v37.7.4` 历史同步记录，保留作回溯；当前打包流程以 `version.txt` 为唯一版本源，由 `generate_version_info.py` 自动生成版本资源。

2026-03-18 的 `v37.7.4` 同步包含：

- Windows 安装器回退版本同步到 `37.7.4`
- Windows / macOS 打包脚本统一改为使用当前环境中的 PyInstaller
- Windows / macOS 打包脚本统一改为使用项目内 PyInstaller 缓存
- macOS 完整打包脚本已验证到 `.app` 生成与发布目录回退逻辑
- 当前机器上的实际验证结论：
  - macOS：`.app` 构建成功，已复制到 `releases/macos/PrivacyGuard.app`
  - macOS：当前环境缺少 `create-dmg`，`hdiutil` 本次未成功生成 DMG
  - Windows：脚本链与配置复核完成，但需在 Windows 真机执行 `build_complete.bat` / `3_build_with_setup.bat` 完成最终闭环

最后更新：2026-10-25（历史同步段落仅用于回溯）
