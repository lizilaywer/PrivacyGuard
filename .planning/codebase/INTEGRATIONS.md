# 外部集成 INTEGRATIONS

**Analysis Date:** 2026-08-10
**Scope:** 全仓库 (`/mnt/g/Project/PrivacyGuard`)

<!-- refreshed: 2026-08-10 -->

## 概览

PrivacyGuard 是**纯本地桌面应用**：无后端服务、无数据库、无鉴权/身份提供方、无 webhook、无远程 API 调用。
外部集成集中在三类：**本地 OCR 引擎**、**本地文档转换外部程序**、**浏览器跳转的静态链接**。

## 1. OCR 引擎

| 引擎 | 集成方式 | 位置 |
|---|---|---|
| RapidOCR (ONNXRuntime) | Python 包 `rapidocr_onnxruntime`，进程内推理，模型随包分发 | `privacyguard/ocr/rapidocr.py` |

- 抽象层：`privacyguard/ocr/base.py`（`OCREngine` 抽象、`OCRResult`、`CharInfo`）
- 引擎管理：`privacyguard/ocr/manager.py`（`OCREngineManager`，为后续多引擎预留）
- 调用线程：`privacyguard/workers/ocr_worker.py`（474 行，QThread worker）
- **懒加载约束**：`from rapidocr_onnxruntime import RapidOCR` 只出现在 `privacyguard/ocr/rapidocr.py` 的函数体内（第 27、43 行），禁止提升到模块/包级别。
- 打包注意事项：`packaging/DUAL_OCR_PACKAGING.md`、`packaging/windows/scripts/diagnose_onnxruntime.py`

### PDF 命中路径
- 文字型：`privacyguard/ocr/text_pdf.py`（PyMuPDF 文本层搜索 + 去重）
- 混合型：`privacyguard/ocr/mixed_pdf.py`（`page.get_text("dict")` 找嵌入图片块 → 裁剪 OCR → 局部坐标换算回页面坐标 → 与文本层合并去重）
- 印章检测：OpenCV 红色区域 + 圆度分析（`config.json` 中 `redaction.seal_detection`，默认关闭）

## 2. 文档转换外部程序（.doc → .docx）

| 工具 | 调用方式 | 位置 |
|---|---|---|
| **LibreOffice** (`soffice`) | `subprocess` 无头转换，首选方案 | `privacyguard/utils/doc_converter.py:convert_with_libreoffice()` |
| **antiword** | 备选，仅提取纯文本（丢格式） | `main.py:10681`、`main.py:10615` 提示文案 |

路径探测 `resolve_soffice_cmd()`（`privacyguard/utils/doc_converter.py`）：
- macOS：`/Applications/LibreOffice.app/Contents/MacOS/soffice`
- Windows：`%ProgramFiles%\LibreOffice\program\soffice.exe`、`%ProgramFiles(x86)%\...`
- 兜底：`shutil.which("soffice")`

转换带重试（`max_retries=1`）与超时（默认 `timeout=90`），失败抛 `ConversionError`（`privacyguard/utils/exceptions.py`）。
`main.py:10650` 的能力探测返回 `{'libreoffice': bool, 'antiword': bool, 'recommended': ...}`，缺失时向用户展示安装指引（含 `brew install --cask libreoffice`、`apt/dnf/pacman` 命令）。

## 3. 操作系统集成

| 集成 | 用途 | 位置 |
|---|---|---|
| Windows 注册表 `winreg` | 读取 `AppsUseLightTheme` 判断系统深浅色主题 | `main.py:5011-5017` |
| `subprocess`（macOS） | 系统主题探测 | `main.py:5001-5011` |
| 拖拽打开文件 | Qt drag & drop | `main.py` |
| 临时目录 | `tempfile` + `TempFileManager` 统一清理（`advanced.temp_cleanup_on_exit`） | `privacyguard/utils/temp_manager.py` |
| `psutil` | 内存/资源监控，触发 `MemoryLimitError` | `main.py` |

## 4. 外部 URL（仅 `webbrowser.open`，无 API 调用）

| URL | 用途 | 位置 |
|---|---|---|
| `https://fcnwakmkeuz7.feishu.cn/share/base/form/shrcnEM1JEbdIKzdB400egj9lHe` | 飞书多维表格反馈表单（`config.json` → `app.feedback_url`） | `main.py:3320` |
| `https://fcnwakmkeuz7.feishu.cn/docx/M9ojdaGUAoRVv7x3NCAcxkxenUe` | 飞书在线用户手册 | `main.py:3717`, `main.py:9952` |
| `https://www.libreoffice.org/download/download/` | LibreOffice 下载指引（HTML 文案内链接） | `main.py:10712` |

均为用户主动点击后由系统浏览器打开，应用自身不发起 HTTP 请求。

## 5. 内嵌 Web 渲染

`PyQt6-WebEngine`（Chromium）用于 Word 双栏对比预览：

1. `mammoth` 将 DOCX 转 HTML
2. `beautifulsoup4` 为每个 word 块注入 `data-key`
3. 通过注入 JavaScript 对指定 `data-key` 节点做增量 DOM patch（而非整页 `setHtml()`）
4. 左栏原文高亮，右栏按 `rule > manual > ocr` 优先级合并展示

这是唯一的"Web"技术面，无网络访问、无远程资源加载。

## 6. 数据存储

无数据库。所有状态为进程内内存结构（`self.page_data`、`self.word_data`、`self.word_replace_rules`）
加上磁盘上的 `config.json`。输出文件由用户选择保存路径，受 `security.allowed_extensions`（`.pdf` / `.doc` / `.docx`）与 `validate_safe_path()` 约束。

## 7. 集成风险点

- LibreOffice / antiword 为**可选外部依赖**，未安装时 `.doc` 路径降级并提示用户安装。
- ONNXRuntime 在 Windows 打包后曾出现加载失败（需 VC++ 运行库，见 `packaging/windows/scripts/check_vcredist.bat`）。
- `privacyguard.utils.security` 在 PyInstaller 下曾导入失败，修复见 `rollback_journal.md` 的 `cp30` 条目。

---
*Generated 2026-08-10*
