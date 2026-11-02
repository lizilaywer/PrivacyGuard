# PrivacyGuard Windows 打包指南

当前版本：**40.2.5**，唯一版本源为根目录 `version.txt`。更新：2026-10-25。

## 一键构建便携版

要求：Windows 10/11 x64、Python **3.11 x64**、VC++ 2015-2022 x64 运行库。
首次构建联网安装依赖，生成后的应用离线使用，不要求用户安装 Python。

完整解压源码资料包至短路径后，双击根目录：

```bat
BUILD_WINDOWS_PORTABLE.bat
```

它依次调用环境初始化和正式便携入口。已有正确构建环境时，可单独执行：

```bat
packaging\windows\scripts\build_complete.bat
```

输出：

```text
dist/windows-portable/PrivacyGuard/PrivacyGuard.exe
releases/windows/PrivacyGuard-v40.2.5-Windows-Portable.zip
releases/windows/PrivacyGuard-v40.2.5-Windows-Portable.zip.sha256
releases/windows/PrivacyGuard-v40.2.5-Windows-Portable.validation.json
```

必须把整个 ZIP 分发给用户，不可单独分发 EXE。解压后运行 `PrivacyGuard.exe`
或同目录 `launcher_wrapper.bat`，保留 `_internal`。本流程不生成安装器。

## 正式便携构建门禁

`build_complete.bat` 调用同目录 `build_portable.py`，失败立即返回非零退出码：

1. 确认原生 Windows x64 Python，拒绝 Mac、32 位或 ARM64 原生解释器。
2. `pip check`、编译检查、自动发现并运行 `tests/unit` 全量回归。
3. 运行 `verify_dependencies.py` 和 `generate_version_info.py`；EXE 版本资源不手编。
4. 使用当前解释器 `python -m PyInstaller` 和标准 Windows spec 构建。
5. 检查 EXE/DLL/PYD 全部为 x64，版本、JS、配置模板及三个离线 OCR 模型齐全。
6. 要求三个 VC++ DLL 在根目录或 `_internal`，必要时从本机 System32 复制。
7. 拒绝私有 `config.json`、日志、草稿和符号链接混入成品。
8. 运行冻结程序 `--self-test`（含真实离线 OCR、含图 Word 转换/替换、窗口关闭），180 秒超时中止。
9. 再检查成品，ZIP 保留全部隐藏资源与 `_internal`，CRC 通过才发布，写 SHA256 和验证报告。

只清理本目标的 `dist/windows-portable/PrivacyGuard`，不会删除其他平台和安装版输出。
缓存和中间文件位于 `build/windows-portable`。已有同名发布 ZIP 时拒绝覆盖，请先备份移走。

## 干净构建资料包

`scripts/create_windows_buildkit.py` 从显式清单生成源码资料包，包含当前未提交的源码修复，
不使用可能漏掉修复的 `git archive HEAD`。排除虚拟环境、私人配置、PDF/Word 样本、
日志、会话草稿和历史产物。包内 `BUILD_INPUTS.json` 记录每个输入的 SHA256。

此资料包不是 Windows 成品；必须在 Windows 本机执行构建。macOS 无法用 PyInstaller
交叉构建 Windows EXE。2026-10-25 当前开发机仅验证了脚本单测、输入完整性和干净解压回归，
**未执行 Windows 原生 PyInstaller 构建，未宣称 Windows 成品已验证**。

说明入口：`WINDOWS_BUILD_README.md`。可选输入校验：

```bat
venv_win\Scripts\python.exe scripts\create_windows_buildkit.py --verify .
```

## 保留的其他脚本

| 脚本 | 用途 |
| --- | --- |
| `1_init_environment.bat` | 安装 Python 3.11 x64 的锁定依赖与构建工具 |
| `build_complete.bat` / `build_portable.py` | 正式便携 ZIP 发布入口 |
| `2_build_exe.bat` | 旧 one-dir 构建，输出仍为 `dist/PrivacyGuard`，不等于本轮校验发布流程 |
| `3_build_with_setup.bat` | 原安装器流程，需 Inno Setup 6，未在本轮实机验证 |
| `4_create_installer_only.bat` | 从旧布局已有 `dist/PrivacyGuard` 构建安装器 |
| `generate_version_info.py` | 从唯一版本源生成 EXE 资源 |
| `verify_dependencies.py` / `diagnose_onnxruntime.py` | 依赖检查与 OCR 诊断 |
| `launcher_wrapper.bat` | 检查包内/系统 VC++ DLL 后启动 |

安装器流程不读取 `dist/windows-portable`，不要将两套输出路径混用。安装版仍使用
`PrivacyGuard_Setup.iss` 和 `/DMyAppVersion=<version>`；本轮交付仅限便携构建资料包。

## 失败与验收

- `[ERROR]` 表示构建不通过，不要分发中间 EXE。保留最早错误排查。
- 旧虚拟环境失效时，重命名旧 `venv_win` 再运行；不直接复制 Mac 或另一台电脑的环境。
- Windows 构建后仍须手测：含图 Word、扫描/混合 PDF、导出、关闭和整包解压启动。
- 校验报告是自动门禁结果，不代表所有文档场景和安全边界已全面覆盖。
- 没有证书签名的 EXE 可能遇到 Windows SmartScreen 提示；不应通过关闭系统安全防护来解决。
