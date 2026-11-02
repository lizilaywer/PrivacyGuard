# Windows 构建入口

基线：40.2.5；更新：2026-10-25。

- 完整说明：`docs/packaging/windows-packaging-guide.md`。
- 简明操作：根目录 `WINDOWS_BUILD_README.md`。
- 首次一键构建：根目录 `BUILD_WINDOWS_PORTABLE.bat`。
- 已有 Windows x64 环境：`packaging/windows/scripts/build_complete.bat`。
- 便携输出：`releases/windows/PrivacyGuard-v40.2.5-Windows-Portable.zip`。

当前 Mac 只生成构建资料包，Windows 成品须在 Windows 上构建验证。
旧安装器仍读取 `dist/PrivacyGuard`，与本轮便携 `dist/windows-portable` 分开。
