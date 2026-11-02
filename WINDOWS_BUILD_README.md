# Windows 便携版一键构建

版本：40.2.5。此资料包是完整构建输入，不是已经编译的 Windows 应用。

## 你只需这样做

1. 在 Windows 10/11 x64 电脑上安装 **Python 3.11 x64**，安装时勾选 **Add Python to PATH**。
2. 安装 Microsoft Visual C++ Redistributable 2015-2022 x64（电脑已有则不用重复安装）。
3. 把资料包完整解压到短路径，例如 `C:\PG_Build`。不要在 ZIP 内直接运行，不要复用从另一台电脑拷来的虚拟环境。
4. 双击根目录 **`BUILD_WINDOWS_PORTABLE.bat`**，等待窗口显示 `[OK] Release ZIP and SHA256`。首次会联网安装依赖，耗时取决于网速和电脑性能。

脚本自动完成：新建 `venv_win`、安装锁定依赖和构建工具、依赖一致性检查、语法检查、全量单元测试、生成 EXE 版本资源、PyInstaller 构建、模型/资源/运行库/架构检查、冻结程序离线自检、压缩和 SHA256。

**构建需要联网下载 Python 依赖；生成后的应用在本地离线运行。最终用户不需要 Python。**

## 成品在哪里

```text
releases\windows\PrivacyGuard-v40.2.5-Windows-Portable.zip
releases\windows\PrivacyGuard-v40.2.5-Windows-Portable.zip.sha256
releases\windows\PrivacyGuard-v40.2.5-Windows-Portable.validation.json
```

便携 ZIP 解压后运行 `PrivacyGuard\PrivacyGuard.exe`，也可运行同目录的 `launcher_wrapper.bat`。必须保留整个 `PrivacyGuard` 文件夹，包括 `_internal`，不能只拷一个 EXE。

发布前请在 Windows 上手工验证：含嵌入图片的 Word 打开/替换/导出，扫描 PDF 离线 OCR 和导出，正常关闭程序。自动自检通过不等于所有真实文档都没有边界问题。

## 遇到错误

- 看到 `[ERROR]` 就表示本次构建未通过，不要分发中间目录中的 EXE。保留窗口中**最早出现的错误**反馈排查。
- 如果提示旧 `venv_win` 无效，把旧目录重命名后重新运行。脚本不会擅自删除旧环境。
- 如果缺少 VC++ 运行库，安装 x64 版后重试。
- 如果同版本成品已经存在，先将已有 ZIP 和对应校验文件移到备份目录，再重新构建；脚本不覆盖旧成品。
- 构建脚本不会删除 macOS 包或安装版的输出目录。便携版使用 `build\windows-portable` 和 `dist\windows-portable`。
- 此包不含开发机的 `config.json`、日志、会话草稿、私人 PDF/Word 和虚拟环境。回归测试在没有本地配置时读取 `config.json.template`。

## 单独运行各步骤

```bat
packaging\windows\scripts\1_init_environment.bat
packaging\windows\scripts\build_complete.bat
```

详细说明：`docs/packaging/windows-packaging-guide.md`。

验证资料包内文件没有丢失或变化（可选）：

```bat
venv_win\Scripts\python.exe scripts\create_windows_buildkit.py --verify .
```

生成成品的 SHA256 可用 PowerShell 核对：

```powershell
Get-FileHash .\releases\windows\PrivacyGuard-v40.2.5-Windows-Portable.zip -Algorithm SHA256
```
