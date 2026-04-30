================================================================================
                    PrivacyGuard Windows 打包脚本说明
================================================================================

当前发布基线：v37.7.4
版本来源：`version.txt`
输出目录：
- `dist/`
- `releases/windows/`

构建 EXE 前会自动执行：
- `generate_version_info.py`
- 同步生成 `packaging/windows/config/version_info.txt`
- 固定使用当前虚拟环境中的 `python -m PyInstaller`
- 固定使用项目内缓存：`build\.pyinstaller-cache`

--------------------------------------------------------------------------------
 1_init_environment.bat
--------------------------------------------------------------------------------
作用：初始化 Windows 打包环境（推荐首次执行）
- 检查 Python
- 创建 `venv_win`（若仅有 `venv` 也会兼容提示）
- 安装 requirements 和 PyInstaller

--------------------------------------------------------------------------------
 2_build_exe.bat
--------------------------------------------------------------------------------
作用：构建便携版（不生成安装器）
输出：
- `dist/PrivacyGuard/PrivacyGuard.exe`
- `dist/PrivacyGuard/launcher_wrapper.bat`
- `releases/windows/PrivacyGuard-<version>.exe.sha256`

--------------------------------------------------------------------------------
3_build_with_setup.bat
--------------------------------------------------------------------------------
作用：构建 EXE + 安装程序（需 Inno Setup）
输出：
- `dist/PrivacyGuard/PrivacyGuard.exe`
- `releases/windows/PrivacyGuard-<version>-Setup.exe`
- 对应 `.sha256`

说明：脚本会将 `version.txt` 版本通过 `/DMyAppVersion=<version>` 注入
`packaging/windows/config/PrivacyGuard_Setup.iss`，避免版本号漂移。

正式发布时：
- 便携版执行 `build_complete.bat`
- 安装版执行 `3_build_with_setup.bat`

--------------------------------------------------------------------------------
 4_create_installer_only.bat
--------------------------------------------------------------------------------
作用：基于已有 dist 结果，仅生成安装程序

--------------------------------------------------------------------------------
 build_complete.bat
--------------------------------------------------------------------------------
作用：完整构建（环境校验 + 构建 + 清理 + ZIP + SHA256）
输出：
- `releases/windows/PrivacyGuard-v<version>-Windows-Portable.zip`
- `releases/windows/PrivacyGuard-v<version>-Windows-Portable.zip.sha256`

--------------------------------------------------------------------------------
 其他脚本
--------------------------------------------------------------------------------
- `generate_version_info.py`：从 `version.txt` 生成 Windows EXE 版本资源
- `check_vcredist.bat`：VC++ 运行库检查
- `diagnose_onnxruntime.py`：onnxruntime 诊断
- `verify_dependencies.py`：构建前依赖校验
- `launcher_wrapper.bat`：发布目录默认启动入口

================================================================================
本轮同步说明
================================================================================

- 安装器构建时通过 `/DMyAppVersion=<version>` 从 `version.txt` 注入版本号
- 当前 EXE 版本资源：`37.7.4.0`
- PyInstaller 打包模块导入失败修复已纳入当前 Windows 打包链路说明
- 当前 Windows 打包脚本已统一改为使用当前环境中的 PyInstaller 和项目内缓存
- `scripts/` 目录已清理历史兼容与解除阻止脚本，仅保留当前正式主链与必要诊断工具
- 当前正式发布入口已收口为：
  - 便携版：`build_complete.bat`
  - 安装版：`3_build_with_setup.bat`

最后更新：2026-03-18
