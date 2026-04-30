# PrivacyGuard 打包文档总览

本目录是打包说明的主入口，和 `packaging/` 目录内的轻量索引保持同步。

---

## 当前打包基线

- 当前应用版本：`v37.7.4`
- 版本标识：`37.7.4 - Release Audit and Final Polish`
- 版本唯一来源：项目根目录 `version.txt`

---

## 推荐阅读顺序

1. `docs/packaging/windows-packaging-guide.md`
2. `docs/packaging/macos-packaging-guide.md`
3. `packaging/DUAL_OCR_PACKAGING.md`
4. `packaging/README.md`

---

## 平台约定

### Windows
- 推荐脚本：`packaging/windows/scripts/build_complete.bat`
- 安装包脚本：`packaging/windows/scripts/3_build_with_setup.bat`
- EXE 版本资源由 `packaging/windows/scripts/generate_version_info.py` 自动生成
- 安装器默认版本在 `packaging/windows/config/PrivacyGuard_Setup.iss`
- 脚本通过 `python -m PyInstaller` 绑定当前虚拟环境，并使用 `build\.pyinstaller-cache`

### macOS
- 推荐脚本：`packaging/macos/scripts/build_complete.sh`
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

2026-03-18 的 `v37.7.4` 同步包含：

- Windows 安装器回退版本同步到 `37.7.4`
- Windows / macOS 打包脚本统一改为使用当前环境中的 PyInstaller
- Windows / macOS 打包脚本统一改为使用项目内 PyInstaller 缓存
- macOS 完整打包脚本已验证到 `.app` 生成与发布目录回退逻辑
- 当前机器上的实际验证结论：
  - macOS：`.app` 构建成功，已复制到 `releases/macos/PrivacyGuard.app`
  - macOS：当前环境缺少 `create-dmg`，`hdiutil` 本次未成功生成 DMG
  - Windows：脚本链与配置复核完成，但需在 Windows 真机执行 `build_complete.bat` / `3_build_with_setup.bat` 完成最终闭环

最后更新：2026-03-18
