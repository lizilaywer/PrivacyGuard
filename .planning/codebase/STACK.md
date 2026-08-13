# 技术栈 STACK

**Analysis Date:** 2026-08-10
**Scope:** 全仓库 (`/mnt/g/Project/PrivacyGuard`)

<!-- refreshed: 2026-08-10 -->

## 1. 语言与运行时

| 项 | 值 | 证据 |
|---|---|---|
| 主语言 | Python (100% 运行时代码) | `main.py`, `privacyguard/` |
| 本地解释器 | Python 3.12.13 | `python3 --version` |
| GUI 运行时 | Qt 6 (PyQt6 6.10.2) + QtWebEngine | `requirements.txt` |
| 辅助语言 | JavaScript（嵌入 QWebEngine 的 DOM patch 脚本）、HTML（预览/文档）、Batch/Shell（打包脚本） | `main.py`, `packaging/windows/scripts/*.bat`, `packaging/macos/scripts/*.sh` |
| 版本号唯一来源 | `37.7.6` | `version.txt`（由 `privacyguard/__init__.py:_read_version()` 读取） |

## 2. 应用形态

桌面单机应用（无服务端、无网络后端）。入口为单体文件 `main.py`（约 14,000+ 行），
共享逻辑逐步下沉到 `privacyguard/` 子包：

- `privacyguard/ocr/`（`base.py`, `manager.py`, `rapidocr.py`, `text_pdf.py`, `mixed_pdf.py`）
- `privacyguard/workers/`（`ocr_worker.py`, `word_worker.py`, `image_merge.py`）
- `privacyguard/utils/`（`config.py`, `doc_converter.py`, `security.py`, `temp_manager.py`, `exceptions.py`）
- `privacyguard/core/`、`privacyguard/ui/` 目前为空占位包
- `theme.py`：UI 主题常量（89 行）

## 3. 框架与核心依赖

来源：`requirements.txt`（全部为固定版本 pin，除 `onnxruntime` / `psutil` 使用 `>=`）

### GUI
- `PyQt6==6.10.2`, `PyQt6-Qt6==6.10.2`, `PyQt6_sip==13.11.0`
- `PyQt6-WebEngine==6.10.0`, `PyQt6-WebEngine-Qt6==6.10.2` — Word 双栏 HTML 预览渲染

### 文档处理
- `PyMuPDF==1.27.1`（`fitz`）— PDF 解析、文本层搜索、页面渲染、涂抹写回
- `python-docx==1.2.0` — DOCX 读写与替换
- `mammoth==1.11.0` + `cobble==0.1.4` — DOCX → HTML 预览转换
- `beautifulsoup4==4.14.3` — HTML 后处理（注入 `data-key`）
- `lxml==6.0.2` — docx/XML 底层解析

### OCR / 图像
- `rapidocr-onnxruntime==1.2.3` — 主 OCR 引擎（懒加载）
- `onnxruntime>=1.24.1` — 推理运行时
- `opencv-python==4.13.0.92`（`cv2`）— 图像预处理、印章（红色区域）检测
- `pillow==12.1.1`, `numpy==2.4.2`, `shapely==2.1.2`, `pyclipper==1.4.0`, `flatbuffers`, `protobuf`

### 其它
- `PyYAML==6.0.3`, `packaging==26.0`, `six`, `sympy`/`mpmath`, `typing_extensions`
- `psutil>=5.9.0` — 资源/内存监控
- `pyinstaller==6.18.0` — 打包
- `reportlab` — 仅测试夹具生成 PDF（`tests/e2e/create_test_pdf.py`），不在 requirements pin 内

## 4. 配置

| 文件 | 作用 |
|---|---|
| `config.json` | 运行时生效配置（勿手改结构） |
| `config.json.template` | 配置模板与字段说明 |
| `version.txt` | 版本号唯一来源 |

配置结构主键：`app`（窗口尺寸、`feedback_url`）、`redaction`（默认正则规则：身份证/手机号/日期/邮箱/银行卡/印章、`replacement_text`、扫描倍率、偏移、精准定位、印章检测）、`ocr`（最小框宽、缩放、检测框调节）、`security`（`validate_paths`、`allowed_extensions: .pdf/.doc/.docx`）、`ui`（主题/动画）、`advanced`（`debug_mode`、`cv2_num_threads`、`omp_num_threads`）。

**注意**：运行时实际配置类是 `main.py` 中的 `SimpleConfig`；`privacyguard/utils/config.py` 的 `ConfigManager`（533 行）存在但非当前生效路径。

## 5. 关键架构约束

- **懒加载**：`privacyguard/__init__.py` 与 `privacyguard/workers/__init__.py` 仅用 `importlib.import_module` 延迟导出；`RapidOCR` 只在 `privacyguard/ocr/rapidocr.py` 函数内部 import。
- **绝对导入**：包内统一使用 `from privacyguard.x import y`，为兼容 PyInstaller（见 `packaging/windows/config/hook-privacyguard.py`）。
- **路径安全**：`privacyguard/utils/security.py` 提供 `validate_safe_path()` 与 `resource_path()`。
- **临时文件**：统一走 `privacyguard/utils/temp_manager.py` 的 `TempFileManager`。
- **异常**：`privacyguard/utils/exceptions.py` 定义 `PrivacyAppError` 及子类。

## 6. 构建与打包

PyInstaller 6.18.0，双平台脚本：

- Windows：`packaging/windows/scripts/build_complete.bat`；spec `packaging/windows/config/PrivacyGuard_windows.spec`（及 `_v2`）；Inno Setup 安装包 `PrivacyGuard_Setup.iss`；版本资源 `version_info.txt` 由 `generate_version_info.py` 生成；hook / runtime hook 见 `hook-privacyguard.py`、`runtime_hook_privacyguard.py`；诊断脚本 `diagnose_onnxruntime.py`、`verify_dependencies.py`、`check_vcredist.bat`
- macOS：`packaging/macos/scripts/build_complete.sh`，签名/公证 `sign_macos_app.sh`、`notarize_macos_app.sh`，spec `packaging/macos/config/PrivacyGuard.spec`，`entitlements.plist`
- 文档：`packaging/README.md`、`packaging/DUAL_OCR_PACKAGING.md`、`docs/packaging/`

## 7. 测试

标准库 `unittest`，无 pytest 依赖。基线 79/79。

- `tests/unit/`：`test_mixed_pdf_ocr`, `test_ocr_api`, `test_package_imports`, `test_pdf_text_hit_dedup`, `test_app_config`, `test_word_replace_rules`, `test_batch_word_replace`, `test_config_alignment`, `test_fstring_safety`, `test_convergence`, `test_stability`
- `tests/test_path_validation.py`, `tests/integration/`, `tests/e2e/`, `tests/samples/`, `tests/reports/`
- 语法检查：`python3 -m compileall -q main.py privacyguard tests`，另有 `check_syntax.py`

## 8. 工具脚本

`start_app.sh`、`clean_project.sh` / `.bat`、`restore_checkpoint.sh`、`scripts/check_progress.py`、`scripts/quick_start.sh`、`run_test.py`、`simple_test.py`、`test_fix.py`

---
*Generated 2026-08-10*
