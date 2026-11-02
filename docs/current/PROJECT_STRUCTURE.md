# PrivacyGuard 当前项目结构说明

> 仅保留当前生效结构与路径，不再混用旧版目录命名和历史脚本名。

---

## 根目录关键文件

```text
PrivacyGuard/
├── main.py
├── theme.py
├── version.txt
├── config.json
├── config.json.template
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── ARCHITECTURE.md
├── CHANGELOG.md
├── rollback_journal.md
├── restore_checkpoint.sh
├── ROLLBACK_GUIDE.md
```

---

## 当前代码目录

```text
privacyguard/
├── __init__.py
├── report.py              # cp87 脱敏报告纯函数
├── session_store.py       # cp88 会话恢复
├── trace_cleaner.py       # cp90 清理使用痕迹
├── ocr/
│   ├── __init__.py
│   ├── base.py
│   ├── manager.py
│   ├── mixed_pdf.py       # 混合 PDF 文本层 + 图片块 OCR
│   ├── rapidocr.py        # RapidOCR 引擎（懒加载）
│   └── text_pdf.py        # 文本型 PDF 命中收集
├── ui/
│   ├── widgets.py         # SinglePageCanvas / PageGridScrollArea / ColorPickerOverlay
│   ├── dialogs/           # 9 个 Dialog（Settings/TraceClean/WordRules/ImageList/Feedback/Donate/ManualRegion/Encrypt）
│   └── mixins/            # PageViewMixin(22方法) / WordPreviewMixin(27方法)
├── utils/
│   ├── helpers_pdf.py         # PDF 命中/几何/页面（17 函数）
│   ├── helpers_word_rules.py  # Word 规则规范化/匹配（14 函数）
│   ├── helpers_word_doc.py    # Word docx 操作（7 函数）
│   ├── helpers_word_preview.py # Word 预览（6 函数 + 3 常量）
│   ├── helpers_ui.py          # UI 辅助（13 函数）
│   ├── config.py
│   ├── security.py        # validate_safe_path
│   ├── doc_converter.py
│   ├── temp_manager.py
│   └── exceptions.py
└── workers/
    ├── ocr_worker.py      # OCR + 印章 + 签名手印检测
    ├── word_worker.py
    ├── batch_replace_worker.py
    ├── search_worker.py   # cp81 全文搜索
    └── image_merge.py
```

说明：
- `main.py`（9,271 行）是活动运行时主入口，承载 MainWindow 协调逻辑；2026-08-01 完成渐进式重构（-44%）。
- `privacyguard/` 提供共享模块；新功能必须作为独立模块开发（见 AGENTS.md 架构铁律）。
- OCR 固定为 RapidOCR 单引擎，懒加载，`import privacyguard` 不依赖 OCR 运行环境。

---

## 文档目录

```text
docs/
├── current/
│   ├── STATUS.md
│   ├── DEV_LOG.md
│   ├── AGENT_CONTEXT.md
│   ├── OPTIMIZATION_ROADMAP.md
│   ├── PRIORITY_REMEDIATION_PLAN.md
│   ├── MAIN_PY_REFACTOR_PLAN.md
│   ├── V38_UI_REFACTOR_PLAN.md
│   ├── PROJECT_STRUCTURE.md
│   └── RELEASE_CHECKLIST.md
├── guides/
│   ├── USER_GUIDE.md
│   ├── CLAUDE_CODE_TIPS.md
│   └── TESTING_GUIDE.md
├── packaging/
│   ├── README.md
│   ├── windows-packaging-guide.md
│   └── macos-packaging-guide.md
├── diary/
└── archive/
```

---

## 打包目录

```text
packaging/
├── README.md
├── DUAL_OCR_PACKAGING.md
├── macos/
│   ├── assets/
│   ├── config/
│   ├── docs/
│   └── scripts/
└── windows/
    ├── archive/
    ├── assets/
    ├── config/
    ├── docs/
    └── scripts/
```

说明：
- 当前 active 打包说明以 `docs/packaging/*.md` 为主。
- `packaging/*/docs/*.md` 保留为目录内索引。
- Windows 默认版本资源由 `packaging/windows/scripts/generate_version_info.py` 自动生成。

---

## 构建与发布目录

```text
backups/iteration_checkpoints/
build/
dist/
releases/macos/
releases/windows/
```

---

## 当前版本信息

- **当前版本**: v37.8.11
- **版本标识**: `37.8.11`（安全审计修复 + main.py 重构 Phase 1-4c）
- **最后更新**: 2026-08-01
- **main.py 行数**: 9,271（已从 16,702 行重构 -44%）
