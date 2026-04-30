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
├── PROJECT_INDEX.md
├── AGENTS.md
├── CLAUDE.md
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
├── ocr/
│   ├── __init__.py
│   ├── base.py
│   ├── manager.py
│   ├── mixed_pdf.py
│   ├── rapidocr.py
│   └── text_pdf.py
├── utils/
└── workers/
```

说明：
- `main.py` 仍是活动运行时主入口。
- `privacyguard/` 提供共享模块，但并未完全替代 `main.py`。
- v38 UI 改造代码层仍主要落在 `main.py` 中，包含首页、主工作区和高级设置的响应式壳层逻辑。
- OCR 当前固定为 RapidOCR 单引擎。

---

## 文档目录

```text
docs/
├── current/
│   ├── STATUS.md
│   ├── DEV_LOG.md
│   ├── V38_UI_REFACTOR_PLAN.md
│   ├── PRIORITY_REMEDIATION_PLAN.md
│   ├── PROJECT_STRUCTURE.md
│   ├── PROJECT_SUMMARY.md
│   └── RECOVERY_GUIDE.md
├── guides/
│   ├── QUICK_START_FOR_CLAUDE_CODE.md
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

- **当前版本**: v37.7.4
- **版本标识**: `37.7.4 - Release Audit and Final Polish`
- **最后更新**: 2026-03-18
