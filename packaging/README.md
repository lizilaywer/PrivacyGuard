# PrivacyGuard 打包目录说明（索引）

本目录只保留打包脚本、spec、安装程序配置和轻量索引。完整说明统一维护在：

- `docs/packaging/README.md`
- `docs/packaging/windows-packaging-guide.md`
- `docs/packaging/macos-packaging-guide.md`
- `packaging/OCR_PACKAGING.md`（RapidOCR 单引擎打包说明，含完整导入链与易漏点）

---

## 当前打包发布基线

- 当前应用版本：`v40.2.5`
- 版本标识：`40.2.5`
- 版本唯一来源：项目根目录 `version.txt`

---

## 当前约定

- Windows EXE 版本资源：`packaging/windows/scripts/generate_version_info.py` 在构建前自动生成（禁止手改 `version_info.txt`）
- Windows / macOS PyInstaller 统一绑定当前虚拟环境，并使用项目内缓存：
  - Windows 便携：`build/windows-portable/pyinstaller-cache`
  - macOS：`build/.pyinstaller-cache`
- Windows 主要产物：
  - `releases/windows/PrivacyGuard-v<version>-Windows-Portable.zip`
  - `releases/windows/PrivacyGuard-<version>-Setup.exe`
- macOS 主要产物：
  - `releases/macos/PrivacyGuard-<version>-macOS-arm64-portable.zip`（本次推荐，解压即得完整 `.app`）
  - 对应 `.sha256` 与 `-validation.json`
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
- `build_complete.bat` 调用 `build_portable.py`：全量回归 → 生成版本 → PyInstaller → 离线模型/VC++/架构/隐私校验 → 冻结程序自检 → ZIP CRC + SHA256；不再删除全部 build/dist，也不盲删冻结资源中的 .pyc
- `3_build_with_setup.bat`：EXE + Inno Setup 安装包

首次可双击根目录 `BUILD_WINDOWS_PORTABLE.bat`，要求 Windows Python 3.11 x64。
Windows 便携中间产物：`dist/windows-portable/PrivacyGuard`；旧安装器仍使用 `dist/PrivacyGuard`，不能混用。
2026-10-25 本机为 Mac，只生成 `Windows-BuildKit.zip` 源码资料包；尚未执行 Windows 原生构建。

```cmd
packaging\windows\scripts\build_complete.bat
```

### macOS

```bash
bash packaging/macos/scripts/build_portable.sh
```

便携构建使用独立 `venv_macos_release`，不依赖旧 `activate` 脚本。
旧 DMG 构建说明为历史入口，不代表本轮已复验签名/公证流程。

---

## 目录结构

```text
packaging/
├── README.md                       本索引
├── OCR_PACKAGING.md                RapidOCR 单引擎打包说明（含完整导入链）
├── windows/
│   ├── assets/icon.ico
│   ├── config/
│   │   ├── PrivacyGuard_windows.spec    主 spec（cp119 修复 pathex + 消除冗余清单）
│   │   ├── hook-privacyguard.py          PyInstaller hook（收集 privacyguard 子模块）
│   │   ├── runtime_hook_privacyguard.py  cp119: 仅注入 app_dir（不破坏相对导入）
│   │   ├── PrivacyGuard_Setup.iss        Inno Setup 配置
│   │   └── version_info.txt              生成文件（generate_version_info.py 产出）
│   ├── docs/WINDOWS_BUILD_GUIDE.md
│   └── scripts/                         构建/校验/诊断脚本
└── macos/
    ├── assets/PrivacyGuard.icns
    ├── config/
    │   ├── PrivacyGuard.spec             主 spec
    │   └── entitlements.plist
    ├── docs/MACOS_BUILD_GUIDE.md
    └── scripts/                         build/sign/notarize 脚本
```

---

## cp119 打包修复要点（2026-08-04）

修复打包后"RapidOCR 引擎不可用（attempted relative import with no known parent package）"的根因：

1. **runtime_hook 移除子包路径注入**：此前把 `privacyguard/ocr` 等子包目录插到 `sys.path[0]`，导致 `rapidocr.py:19` 的 `from .base import` 相对导入失败。PyInstaller PYZ 已包含完整包，只需 `app_dir`。
2. **spec pathex 移除子包目录**：仅保留 `project_root`。
3. **消除三处冗余的 privacyguard 子模块硬编码清单**：改用 `collect_submodules` 自动发现（48 子模块），保留单点硬编码回退。
4. **清理失效文件**：`diagnostic.spec`（引用已删除的 `_ocr_diagnostic.py`）、`windows/archive/`（过时 v2 spec + 2026-02 DLL 排查记录）、所有 `__pycache__`、`.DS_Store`。

最后同步：2026-08-04（cp119）
