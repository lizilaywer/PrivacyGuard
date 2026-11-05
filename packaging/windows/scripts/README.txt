PrivacyGuard Windows 打包脚本说明
当前基线：40.2.7；更新：2026-11-05；版本唯一来源：version.txt。

首次打便携版：双击项目根目录 BUILD_WINDOWS_PORTABLE.bat。
已有环境：运行本目录 build_complete.bat。
要求 Windows 10/11 x64 + Python 3.11 x64 + VC++ 2015-2022 x64。

build_complete.bat 调用 build_portable.py：全量测试、版本资源生成、依赖检查、
原生 x64 构建、模型/运行库/版本校验、冻结自检、ZIP/CRC/SHA256/验证报告。
任一步失败立即停止，不把失败中间产物当成发布包。

产物：
  dist/windows-portable/PrivacyGuard/PrivacyGuard.exe
  releases/windows/PrivacyGuard-v40.2.7-Windows-Portable.zip
  releases/windows/PrivacyGuard-v40.2.7-Windows-Portable.zip.sha256
  releases/windows/PrivacyGuard-v40.2.7-Windows-Portable.validation.json
缓存：build/windows-portable。不会删除其他平台或安装版产物。

1_init_environment.bat：新建 venv_win 并安装 requirements.txt / requirements-dev.txt。
generate_version_info.py：生成 version_info.txt（40.2.7.0，禁止手编）。
launcher_wrapper.bat：允许包内 VC++ DLL，不再仅查系统目录。

保留旧流程：2_build_exe.bat、3_build_with_setup.bat、4_create_installer_only.bat，
仍使用 dist/PrivacyGuard。它们不是本轮便携发布入口，未实机验证安装器。

Windows 构建资料包只包含源码和资源，不是已编译的便携成品。
详细操作：项目根目录 WINDOWS_BUILD_README.md。
完整指南：docs/packaging/windows-packaging-guide.md。
