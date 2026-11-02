================================================================================
                    PrivacyGuard macOS 打包脚本说明
================================================================================

当前发布基线：v40.2.5
版本来源：`version.txt`
发布目录：`releases/macos/`

当前推荐便携入口：bash packaging/macos/scripts/build_portable.sh
环境：venv_macos_release/bin/python3（或 PRIVACYGUARD_PYTHON 显式指定）
产物：PrivacyGuard-<version>-macOS-arm64-portable.zip + .sha256 + validation.json
要求：Apple Silicon / macOS 14+，签名为 ad-hoc，未进行 Apple 公证。
此入口执行依赖/编译/全量单测、全包 Mach-O 系统版本与路径校验、签名验证。
以下 DMG/sign/notarize 内容为历史流程，不是本次便携包入口。

--------------------------------------------------------------------------------
 build_macos_app.sh
--------------------------------------------------------------------------------
作用：打包 `.app` 与 DMG，并生成 SHA256。
虚拟环境：优先 `venvmac`，兼容 `venv`。
执行方式：使用当前环境中的 `python3 -m PyInstaller`。
缓存目录：`build/.pyinstaller-cache`
主要输出：
- `dist/PrivacyGuard.app`
- `releases/macos/PrivacyGuard-<version>-macOS.dmg`
- `releases/macos/PrivacyGuard-<version>-macOS.dmg.sha256`

--------------------------------------------------------------------------------
 build_complete.sh
--------------------------------------------------------------------------------
作用：完整流程（清理、构建、校验、清理包体、签名、可选 DMG）。
虚拟环境：优先 `venvmac`，兼容 `venv`。
执行方式：使用当前环境中的 `python3 -m PyInstaller`。
缓存目录：`build/.pyinstaller-cache`
优先使用 `create-dmg` 生成美化 DMG；未安装时回退到 `hdiutil` 生成标准 DMG；若 DMG 仍失败，会保底复制 `.app` 到 `releases/macos/`。
主要输出：
- `releases/macos/PrivacyGuard-<version>-macOS.dmg`
- `releases/macos/PrivacyGuard-<version>-macOS.dmg.sha256`

--------------------------------------------------------------------------------
 sign_macos_app.sh
--------------------------------------------------------------------------------
作用：对 `.app` 签名（需开发者证书）
环境变量：
- `PRIVACYGUARD_CODESIGN_IDENTITY`

--------------------------------------------------------------------------------
 notarize_macos_app.sh
--------------------------------------------------------------------------------
作用：对 DMG 公证（需 Apple Developer 账号）
环境变量：
- `PRIVACYGUARD_NOTARY_PROFILE`
- 或 `PRIVACYGUARD_APPLE_ID` / `PRIVACYGUARD_APP_SPECIFIC_PASSWORD` / `PRIVACYGUARD_TEAM_ID`

================================================================================
推荐流程
================================================================================

基础发布：
1. `bash packaging/macos/scripts/build_complete.sh`

签名+公证：
1. `bash packaging/macos/scripts/build_macos_app.sh`
2. 配置并运行 `sign_macos_app.sh`
3. 配置并运行 `notarize_macos_app.sh`

本轮同步说明：
- macOS 打包脚本已统一改为使用当前环境中的 PyInstaller 和项目内缓存
- `build_complete.sh` 已验证到 `.app` 产物生成与发布目录回退
- 当前便携版本来源为 version.txt（v40.2.5），见本文件顶部新入口。
- 当前正式发布默认入口：`bash packaging/macos/scripts/build_complete.sh`
- 当前发布环境 venv_macos_release 使用 rapidocr==3.9.2，模型随包携带且运行时不自动下载。

最后更新：2026-10-24
