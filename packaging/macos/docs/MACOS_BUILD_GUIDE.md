# PrivacyGuard macOS 打包指南（目录内索引）

此文档保留在 `packaging/macos/docs/` 仅用于就地导航。  
macOS 打包完整指南统一维护在：

- `docs/packaging/macos-packaging-guide.md`

---

## 当前打包基线

- 当前版本：`v37.7.4`
- 版本来源：项目根目录 `version.txt`

---

## 常用脚本入口

- 打包应用：`packaging/macos/scripts/build_macos_app.sh`
- 签名应用：`packaging/macos/scripts/sign_macos_app.sh`
- 提交公证：`packaging/macos/scripts/notarize_macos_app.sh`
- 完整流程：`packaging/macos/scripts/build_complete.sh`

正式发布建议：

- 默认执行：`packaging/macos/scripts/build_complete.sh`
- 若只先产出 `.app` 再处理签名/公证，可用：`packaging/macos/scripts/build_macos_app.sh`

---

## 说明

- 详细参数、证书配置、公证流程请以 `docs/packaging/macos-packaging-guide.md` 为准。
- 本文件只保留最小索引，避免与主文档重复维护。
- 当前 active 打包说明已经统一到 `v37.7.4`。
- 当前 macOS 打包脚本统一通过 `python3 -m PyInstaller` 执行，并使用 `build/.pyinstaller-cache`。
- 2026-03-18 已在当前机器跑通到 `.app`；当前环境缺少 `create-dmg`，且 `hdiutil` 本次未成功生成 DMG，脚本已按回退逻辑复制 `releases/macos/PrivacyGuard.app`。

最后同步：2026-03-18
