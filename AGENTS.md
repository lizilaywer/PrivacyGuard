# AGENTS.md

This file is the primary development guide for Codex and other coding agents working in this repository.

---

## Project Overview

**Project**: PrivacyGuard 脱敏卫士  
**Current Version**: v40.2.7
**Last Updated**: 2026-11-05
**Status**: 重置后正文/仅书签脱敏的导出状态修复；新增 15 项专项回归。当前仅更新源码，现有 macOS 便携包仍为 v40.2.5；剩余 Word/PDF 安全边界见 docs/current/RELEASE_AUDIT_20261024.md；v40.2.3 Windows 包仍不可分发。

PrivacyGuard is a Python + PyQt6 desktop application for intelligent redaction of PDF and Word documents.

Capability summary: PDF redaction (text search / image OCR / mixed PDF / manual box +
whole-doc targeted masking / seal & signature-fingerprint detection with warm-color gating),
page view (multi-page grid overview replacing dual-page mode; Ctrl+wheel column zoom with
release-to-cross boundary damping both ways; two-phase thumbnail rendering + per-frame render
queue for jank-free first entry; instant mask-color switching; click / Ctrl / Shift-range
selection; rotate/insert-blank/insert-file/delete pages with mask transform; fit-page returns to single-page
from any view), PDF encryption on export (AES-256 open/edit passwords, cp72),
open encrypted PDF/Word with password dialog (open/remove/change-password actions,
owner-restriction detection, cp72 lock-button state sharing, cp113;
encrypted PDF redaction fix — _pdf_auth_password decouples disk re-read auth from export
encryption, OCRWorker/save_pdf authenticate after fitz.open, _ensure_edit_permission prompts
owner password when MODIFY permission missing before redact/save, cp114),
full-document search sidebar (magnifier toolbar button; text-layer / scanned-page OCR with
session cache / Word block search; click-to-locate with flash highlight at word/line level,
cp81/82), undo/redo for mask edits and page-structure ops (snapshot stack depth 20,
doc-bytes snapshots restore deleted pages, Ctrl+Z/Y, cp83), overflow-adaptive toolbar
(dual-stretch layout, forced-narrow degradation when screen too small, cp84-86),
12 preset rules incl. USCC/plate/landline/passport/VIN/IP with checksum
re-validation (cp70), title-anchored person-name detection (cp_person_name: 34 builtin
law titles 被告人/原告/辩护人…, forward lead anchor with lookahead + reverse
姓名+作为/担任/系+称谓, connector-char split + legal-verb tail trim + not-name
prefix veto, discover-once-mask-page-wide, disabled-by-default zero-overhead,
config `redaction.person_name_titles` extensible, real-dossier 100% accuracy, v40.2.0),
redaction report on export (rule-classified summary + per-page detail,
exportable txt, cp87), session restore (crash-safe mask-progress drafts with structural
doc-bytes snapshots, cp88), trace cleaner (drafts/temp/preview-cache/logs with whitelist
realpath guard, cp90),
Word redaction (scan / rules / keyword inline replace / batch), Word dual preview with
highlight filtering, context-aware settings, drag & drop, content-driven dynamic minimum
window width (cp73), Win11 DWM titlebar coloring + app-wide font stack with Win10/macOS
fallbacks (cp78-80), dual-platform packaging,
extract/crop vertical region vector clipping (cp122 ExtractMixin/CropMixin, show_pdf_page
preserves text selectability; floating ExtractSidePanel with new/export/delete/move/replace/nav;
回炉打开 post-export reopen),
open encrypted PDF/Word with password dialog (cp113, open/remove/change-password actions,
owner-restriction detection, word_crypto OLE2 detect + msoffcrypto decrypt to temp),
PDF bookmark/TOC panel (cp_bookmark: toolbar bookmark icon PDF-only toggles a 280px left
`BookmarkSidePanel`; read/edit fitz TOC, click-to-jump, search filter, add/rename/delete
with context menu, sub-bookmarks & grouping; bookmark redaction reuses custom_keyword_rules
on titles with live preview + write-back on export; targeted-mask terms synced to titles;
config `redaction.bookmark_redact_enabled`),
security hardening v40.1.2 (log masking for hit strings, pdfsnap deletion on export,
symlink escape guard in trace cleaner, conservative permission failure, exception-hook
traceback downgrade to DEBUG).
Full capability detail: `docs/current/AGENT_CONTEXT.md`.

---

## Read First (pointer routing — do NOT read whole history files)

When resuming work, read only:

1. `docs/current/STATUS.md` — top/latest section only (current state)
2. `docs/current/DEV_LOG.md` — most recent entry only (last change context)

Then route by task type, on demand:

- Release/version sync → `CHANGELOG.md` (top entries), `version.txt`
- Rollback/recovery → `rollback_journal.md`, `ROLLBACK_GUIDE.md`
- UI refactor track → `docs/current/V38_UI_REFACTOR_PLAN.md`
- main.py decomposition → `docs/current/MAIN_PY_REFACTOR_PLAN.md`
- Remediation backlog → `docs/current/PRIORITY_REMEDIATION_PLAN.md`
- Background/history (capabilities, runtime data structures, checkpoints) → `docs/current/AGENT_CONTEXT.md`
- Packaging → `docs/packaging/README.md`
- Latest audit / portable artifact / known blind spots → `docs/current/RELEASE_AUDIT_20261024.md`

---

## Current Technical Reality (key constraints — keep in root)

### Main architecture

v37.8.11 重构后（2026-08-01），main.py 从 16,702 行降至 9,271 行（-44%）。
v40.0.0 起（提取/截去/书签/接线）main.py 增长至 9,787 行（仍为 UI 构建/协调逻辑）。
当前架构分层：

```
main.py (9,792 行；v40.1.4 含四维审计修复 + 主页重设计)
├── SimpleConfig — 运行时配置（模块级）
├── MainWindow(PageViewMixin, WordPreviewMixin, SettingsActionsMixin, CropMixin, ExtractMixin, BookmarkMixin, QMainWindow) — 主窗口协调器
│   ├── setup_ui / 工具栏 / 密度布局 / 主题 — UI 构建与响应式
│   ├── 文件打开/关闭 / 模式切换 — 核心流程协调
│   └── OCR 编排 / 撤销重做 / 会话草稿 / 提取截去 / 书签 — 运行时状态管理
├── WebViewBridge(QObject) — JS-Python 桥接
└── OCRWorker / WordWorker — 薄兼容包装器

privacyguard/
├── utils/helpers_{pdf,word_rules,word_doc,word_preview,ui,bookmark}.py — 共享纯函数按域拆 6 模块
├── ui/dialogs/ — 10 个 Dialog 类（Settings/TraceClean/WordRules/ImageList/PasswordOpen/ManualRegion/Encrypt/Feedback/Donate/...）
├── ui/widgets.py — SinglePageCanvas / PageGridScrollArea / ColorPickerOverlay
├── ui/panels/ — ExtractSidePanel / BookmarkSidePanel（独立 QWidget 子类，铁律规则3）
├── ui/mixins/ — PageViewMixin / WordPreviewMixin / SettingsLayoutMixin / SettingsActionsMixin / CropMixin / ExtractMixin / BookmarkMixin
├── workers/ — OCR / Word / 图片合并 / 批量替换 / 全文搜索
├── ocr/ — text_pdf / mixed_pdf / rapidocr 引擎
└── utils/ — config / security / doc_converter / temp_manager / exceptions / trace_cleaner

privacyguard/session_store.py — cp88 会话草稿（崩溃恢复）
privacyguard/word_crypto.py — cp113 加密 Word 检测/解密

assets/js/word_preview_interactive.js — Word 预览交互脚本（514 行）
assets/icons/ — SVG 图标（undo/redo/search/bookmark/lock/page_rotate/page_insert/page_extract/page_crop/fit_page/reset.svg 等）
```

### Architecture rules for new features（铁律）

**新功能必须作为独立模块开发，禁止直接往 main.py 添加方法。**

具体规则：

1. **新 Worker**（后台线程）→ 放入 `privacyguard/workers/xxx_worker.py`，
   通过 pyqtSignal 与 MainWindow 通信，MainWindow 仅负责实例化和接线。
2. **新 Dialog**（弹窗）→ 放入 `privacyguard/ui/dialogs/xxx_dialog.py`，
   通过构造参数接收数据、通过信号或属性返回结果。
3. **新 UI 面板/功能域**（如未来深度学习印章面板）→ 创建独立 QWidget 子类
   放入 `privacyguard/ui/panels/xxx_panel.py`，MainWindow 通过
   `layout.addWidget(panel)` 接入，通过信号交互。
4. **新纯逻辑**（算法/规则/转换）→ 放入 `privacyguard/utils/` 或
   `privacyguard/ocr/` 下对应模块，编写独立单元测试。
5. **新 Mixin 方法组**（仅当功能与 MainWindow 状态深度耦合且无法用信号解耦时）
   → 放入 `privacyguard/ui/mixins/xxx_mixin.py`，在类 docstring 中
   写明接口契约（需要 MainWindow 提供哪些属性和方法）。

**判断标准**：如果你要写的代码超过 50 行且不是 UI 布局代码，
它几乎一定不应该直接写在 main.py 里。

**main.py 只允许新增**：信号接线（connect）、菜单/工具栏按钮创建、
快捷键绑定、以及对独立模块的调用编排。

### Version source（铁律）

- Single source of truth: `version.txt`
- `main.py` 和 `privacyguard.__version__` 均从 `version.txt` 动态读取，禁止硬编码版本号
- `packaging/windows/config/version_info.txt` 是**生成文件**，不是手动编辑的源文件
  - 升级版本后必须运行：`python packaging/windows/scripts/generate_version_info.py`
  - 禁止直接编辑 `version_info.txt`——它会被 `generate_version_info.py` 覆盖
- `README.md` 和 `packaging/*/scripts/README.txt` 中的版本号在升级后手动更新
  （CI 不验证文档中的版本号，但 PR review 时应检查）
- CI pipeline 包含版本一致性检查：version.txt → version_info.txt → main.py → privacyguard.__init__.py
  任一来源不一致将导致 CI 失败

### Active config path (config 双路径)

- Runtime currently uses `SimpleConfig` in `main.py`
- Shared config utilities also exist in `privacyguard/utils/config.py`
- Do not assume `ConfigManager` is the active runtime path unless you have explicitly switched the app over
- `config.json` is local runtime config (git-ignored); repo keeps `config.json.template` only,
  and `SimpleConfig` initializes `config.json` from the template on first start

### OCR dependency behavior (懒加载 OCR)

- `privacyguard` package import is now lazy
- `RapidOCR` must only initialize at actual OCR execution time
- Do not add package-level eager OCR imports back into `privacyguard/__init__.py` or `privacyguard/workers/__init__.py`

### Mixed PDF handling (混合 PDF 流程)

- Mixed PDF pages must not be treated as text-only or scan-only.
- The active path is:
  1. text-layer hit collection
  2. embedded image block discovery via `page.get_text("dict")`
  3. image-block OCR
  4. local OCR box offset back into page coordinates
- Shared logic lives in `privacyguard/ocr/mixed_pdf.py`

If a regression appears in PDF OCR, prioritize checking: text-layer vs image-block split,
image clip extraction validity, OCR box offset back to page coordinates, dedup after merged hits.

---

## Main Files

- `main.py` - active application runtime (9,787 lines; MainWindow + thin wrappers)
- `theme.py` - UI theme definitions
- `version.txt` - single version source
- `config.json.template` - repo config template (runtime `config.json` is git-ignored)
- `privacyguard/utils/helpers_{pdf,word_rules,word_doc,word_preview,ui}.py` - 57 shared free
  functions 按域拆为 5 模块；消费方直接按域导入（v37.8.11 P0-3 已移除 helpers.py 再导出垫片）
- `privacyguard/ui/dialogs/` - 10 Dialog classes (Settings/TraceClean/WordRules/ImageList/Feedback/Donate/ManualRegion/Encrypt/PasswordOpen)
- `privacyguard/ui/widgets.py` - SinglePageCanvas / PageGridScrollArea / ColorPickerOverlay
- `privacyguard/workers/` - OCR / Word / image-merge / batch-replace / search workers
- `privacyguard/ocr/text_pdf.py` / `mixed_pdf.py` - shared PDF hit collection / mixed-PDF OCR
- `privacyguard/utils/` - config, doc converter, exceptions, temp manager, security
- `assets/js/word_preview_interactive.js` - Word preview interactive JavaScript (Phase 3)

---

## Common Commands

All commands run from the repository root with the platform-matching virtualenv
interpreter: Windows `.\venv_win\Scripts\python.exe`, macOS `./venvmac/bin/python3`.

本轮独立 macOS 发布环境为 `./venv_macos_release/bin/python3`（原 venvmac 缺解释器，保留未删除）；
当前回归为 730 discovered / 728 passed / 2 skipped，下方旧版本数字仅作历史记录。

### Run app

```powershell
# Windows (PowerShell)          # macOS: ./venvmac/bin/python3 main.py
.\venv_win\Scripts\python.exe main.py
```

### Compile check

```powershell
# Windows (PowerShell)          # macOS: ./venvmac/bin/python3 -m compileall -q main.py privacyguard tests
.\venv_win\Scripts\python.exe -m compileall -q main.py privacyguard tests
```

### Main regression suite

cp87(D3) 起推荐直接用脚本（unittest discover 自动发现 tests/unit 全部用例，
新测试文件自动纳入，清单永不漂移）；当前基线 576（v40.1.4，全绿；含 13 项路径安全入 CI + 19 项迁移纯函数 + 2 项 star-import 守卫 + 7 项构造契约 [worker×6+设置对话框]）：

```bash
# Windows
powershell -ExecutionPolicy Bypass -File scripts/run_regression.ps1
# macOS / Linux
./scripts/run_regression.sh
```

陈旧失效测试已归档 `tests/legacy/`（不参与 discover）。手工模块清单（历史基线记录，仍可逐模块执行）：

```powershell
# Windows (PowerShell, 反引号续行)
# macOS: 相同模块清单，解释器换成 ./venvmac/bin/python3，续行符换成 \
.\venv_win\Scripts\python.exe -m unittest `
  tests.unit.test_luhn_validation `
  tests.unit.test_calculate_sub_rect_width_limit `
  tests.unit.test_seal_detection `
  tests.unit.test_signature_detection `
  tests.unit.test_mixed_pdf_ocr `
  tests.unit.test_pdf_text_hit_dedup `
  tests.unit.test_idcard_pattern_v2 `
  tests.unit.test_extended_rules `
  tests.unit.test_pdf_encrypt `
  tests.unit.test_doc_search `
  tests.unit.test_undo_redo `
  tests.unit.test_redact_report `
  tests.unit.test_session_store `
  tests.unit.test_trace_cleaner `
  tests.unit.test_toolbar_layout `
  tests.unit.test_custom_keyword_rules `
  tests.unit.test_targeted_mask_scan `
  tests.unit.test_word_replace_rules `
  tests.unit.test_word_hyperlink_alignment `
  tests.unit.test_word_header_footer_redaction `
  tests.unit.test_batch_word_replace `
  tests.unit.test_convergence `
  tests.unit.test_app_config `
  tests.unit.test_config_alignment `
  tests.unit.test_ocr_api `
  tests.unit.test_package_imports `
  tests.unit.test_fstring_safety `
  tests.unit.test_stability `
  tests.unit.test_page_view_ops `
  -v
```

Current verified baseline: `418` 项（v37.8.11，Windows venv_win 实测，`scripts/run_regression.ps1` discover 全量）：

- 项目根目录存在真实样本 `提取自诉讼文书卷三.pdf` 及王珍样本时：`418/418` 全绿。
- 真实样本缺失时（典型干净检出）：`416 passed + 2 skipped`（跳过
  `test_real_pdf_seals_detected` 与 `test_real_pdf_black_fingerprint_detected`；
  印章/签名端到端语义由仓库内合成样本用例在任何机器上兑付）。

### Version check

`version.txt`（Windows: `Get-Content version.txt` / macOS: `cat version.txt`）

---

## Packaging

Docs: `docs/packaging/README.md`, `docs/packaging/windows-packaging-guide.md`,
`docs/packaging/macos-packaging-guide.md`, `packaging/README.md`.

```bash
# macOS
./packaging/macos/scripts/build_portable.sh

# Windows
packaging/windows/scripts/build_complete.bat
```

---

## Current Development Direction

Default track: 1) 新功能按独立模块开发（见 Architecture rules）;
2) Phase 2 per-file rule mapping for batch replace; 3) batch rule-set templates。
（原第 4 项 "preview highlight filtering by source (rule/manual/ocr)" 已于 v37.8.11
落地：`privacyguard/utils/helpers_word_preview.py` 提供三函数，main.py 与
word_preview_mixin.py 已接入，从默认方向移除。）

**重构已完成（2026-08-01）**：main.py 16,702→9,271 行（-44%），
Phase 1-4c 全部落地，418 回归全绿。后续不再做物理拆分，
MainWindow 剩余代码为 UI 构建/布局/协调逻辑，按版本节奏渐进优化。
完整拆分记录：`docs/current/MAIN_PY_REFACTOR_PLAN.md`。

**后续优化路线图**：`docs/current/OPTIMIZATION_ROADMAP.md`（P0–P3 增量与工程化计划，
含垫片迁移、用户手册、类型注解、批量规则增强、覆盖率与性能基准等）。

Checkpoints & rollback references: `docs/current/AGENT_CONTEXT.md`, `rollback_journal.md`,
`ROLLBACK_GUIDE.md`, `restore_checkpoint.sh`.
