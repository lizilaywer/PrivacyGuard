# Codebase Structure

**Analysis Date:** 2026-08-10

## Directory Layout

```
PrivacyGuard/
├── main.py                          # Monolithic PyQt6 runtime entry (~12.6k LOC)
├── theme.py                         # Light/dark theme tokens, fonts, spacing
├── version.txt                      # Single source of truth for version string
├── config.json                      # Active runtime config (JSON)
├── config.json.template             # Canonical config skeleton
├── requirements.txt                 # Pinned Python dependencies
│
├── privacyguard/                    # Partially-extracted shared library
│   ├── __init__.py                  # Lazy exports, __version__, eager utils
│   ├── core/                        # Reserved (empty)
│   │   └── __init__.py
│   ├── ocr/                         # OCR engine abstraction + helpers
│   │   ├── __init__.py              # Eager re-exports
│   │   ├── base.py                  # BaseOCREngine ABC, OCRResult, CharInfo dataclasses
│   │   ├── manager.py               # OCREngineManager (RapidOCR-only after v37.4.0)
│   │   ├── rapidocr.py              # RapidOCREngine concrete impl
│   │   ├── text_pdf.py              # collect_text_pdf_hit_boxes (shared)
│   │   └── mixed_pdf.py             # collect_image_block_ocr_hits (shared)
│   ├── ui/                          # Reserved (empty placeholder)
│   │   └── __init__.py
│   ├── utils/                       # Cross-cutting utilities
│   │   ├── __init__.py              # Eager re-exports
│   │   ├── exceptions.py            # PrivacyAppError hierarchy
│   │   ├── temp_manager.py          # Thread-safe TempFileManager
│   │   ├── security.py              # validate_safe_path, resource_path
│   │   ├── doc_converter.py         # .doc → .docx (LibreOffice + antiword fallback)
│   │   └── config.py                # ConfigManager (NOT runtime path)
│   └── workers/                     # QThread workers (lazy-loaded)
│       ├── __init__.py              # Lazy via __getattr__
│       ├── ocr_worker.py            # OCRWorker (text + image-block + seal detection)
│       ├── word_worker.py           # WordWorker (paragraphs + tables scan)
│       └── image_merge.py           # ImageMergeWorker (images → single PDF)
│
├── tests/                           # Test suite (79 baseline tests)
│   ├── unit/                        # unittest modules (10 files, primary regression net)
│   ├── integration/                 # Manual verification scripts (verify_scroll_fix, verify_word_format)
│   ├── e2e/                         # Test PDF generators (create_test_pdf.py)
│   ├── scripts/                     # Shell + ad-hoc test scripts
│   ├── samples/                     # Sample fixtures (PDFs, images)
│   └── reports/                     # Historical test reports (markdown)
│
├── docs/                            # Documentation (per-domain subfolders)
│   ├── current/                     # Live status, dev log, refactor plans, recovery guide
│   ├── diary/                       # Date-stamped dev diaries (cp checkpoints)
│   ├── features/                    # Feature specs + UI concept HTML
│   ├── guides/                      # CLAUDE Code tips, quick-start, testing guide
│   ├── marketing/                   # Promo materials, blog drafts
│   ├── packaging/                   # Windows / macOS packaging guides
│   ├── archive/                     # Frozen historical records (old_docs, v19/v22/v36.x)
│   ├── CODE_REVIEW_*.md             # Top-level code review reports
│   ├── CROSS_PLATFORM_GUIDE.md
│   ├── DEVELOPMENT_WORKFLOW.md
│   └── 合规性评估报告*.md
│
├── packaging/                       # PyInstaller build scripts and config
│   ├── README.md
│   ├── DUAL_OCR_PACKAGING.md
│   ├── macos/
│   │   ├── scripts/build_complete.sh
│   │   ├── assets/, config/, docs/
│   └── windows/
│       ├── scripts/build_complete.bat
│       ├── assets/, config/, docs/
│       └── archive/
│
├── scripts/                         # Repo-level utility scripts
│   ├── quick_start.sh
│   └── check_progress.py
│
├── assets/                          # Static branding + logo assets
│   ├── branding/v38/                # v38 icon set (SVG)
│   └── logo/                        # Source SVG, exports at 16–1024 px, per-platform packs
│       ├── source/
│       ├── export/{16,24,32,48,64,128,256,512,1024}/
│       ├── macos/, windows/, linux/, marketing/
│       └── generate_icons.py
│
├── user-guides/                     # End-user help (HTML manuals)
│
├── PDF/                             # Sample input documents (not source)
│
├── AGENTS.md                        # Multi-agent orchestration notes
├── PROJECT_INDEX.md                 # One-page project index
├── ROLLBACK_GUIDE.md                # Checkpoint rollback instructions
├── restore_checkpoint.sh            # Rollback helper script
├── rollback_journal.md              # Checkpoint journal (cp18, cp20, cp23, cp25, cp27, cp29, cp30, ...)
├── CHANGELOG.md                     # Versioned changelog (Chinese)
├── CLAUDE.md                        # Claude Code entry instructions
├── README.md / README_EN.md         # Top-level project readmes
├── LICENSE                          # License (35 KB)
├── check_syntax.py / run_test.py / simple_test.py / test_fix.py  # Ad-hoc helpers
├── clean_project.sh / clean_project.bat                            # Cleanup helpers
├── start_app.sh                                                   # Launch wrapper
├── *.html                                                       # Top-level HTML artifacts (product page, UI preview, manual)
└── .planning/                     # GSD planning artifacts (this directory lives here)
```

## Directory Purposes

**`/` (project root):**
- Purpose: Python entry-point hosting — `main.py` runs from here
- Contains: Monolithic app, theme, version, config, requirements, top-level docs
- Key files: `main.py`, `theme.py`, `version.txt`, `config.json`, `requirements.txt`

**`privacyguard/`:**
- Purpose: Partially-extracted shared library (subset of original `main.py`)
- Contains: OCR abstraction, workers, utility helpers, reserved placeholders for future UI/core splits
- Key files: `privacyguard/__init__.py` (entry), `privacyguard/workers/ocr_worker.py`, `privacyguard/ocr/mixed_pdf.py`, `privacyguard/utils/temp_manager.py`

**`tests/`:**
- Purpose: Regression net and manual verifications
- Contains: `unit/` (10 unittest modules — the primary baseline), `integration/`, `e2e/`, `samples/`, `reports/`
- Key files: `tests/unit/test_mixed_pdf_ocr.py`, `tests/unit/test_package_imports.py`, `tests/unit/test_convergence.py`

**`docs/`:**
- Purpose: Human-facing project documentation, organized by lifecycle stage
- Contains: `current/` (live), `diary/` (checkpoint diaries), `features/`, `guides/`, `marketing/`, `packaging/`, `archive/`
- Key files: `docs/current/STATUS.md`, `docs/current/V38_UI_REFACTOR_PLAN.md`, `docs/diary/20260311_pyinstaller_packaging_fix_diary.md`

**`packaging/`:**
- Purpose: PyInstaller build infrastructure for Windows and macOS
- Contains: Build scripts (`scripts/build_complete.bat/sh`), per-platform asset/config/doc bundles
- Key files: `packaging/windows/scripts/build_complete.bat`, `packaging/macos/scripts/build_complete.sh`, `packaging/README.md`

**`scripts/`:**
- Purpose: Repo-level utilities (not build)
- Contains: Quick-start shell wrappers, progress checkers
- Key files: `scripts/quick_start.sh`, `scripts/check_progress.py`

**`assets/`:**
- Purpose: Branding and logo assets, versioned per app release
- Contains: `branding/v38/` SVG icons, `logo/` master + per-platform export packs
- Key files: `assets/logo/source/logo_master.svg`, `assets/logo/export/256/logo_default_256.png`, `assets/branding/v38/icon_pdf_redaction.svg`

**`user-guides/`:**
- Purpose: End-user manuals (HTML)
- Contains: User-facing HTML documents
- Key files: user manual HTMLs

## Key File Locations

**Entry Points:**
- `main.py` (lines 12478–12611): `if __name__ == "__main__":` block — QApplication bootstrap, exception hooks, `MainWindow` instantiation
- `privacyguard/__init__.py`: Package entry; lazy export surface for workers and OCR types
- `privacyguard/workers/__init__.py`: Lazy worker resolution via `__getattr__`

**Configuration:**
- `config.json`: Active runtime config (read by `SimpleConfig._load_config`)
- `config.json.template`: Canonical skeleton — copy to `config.json` to reset
- `privacyguard/utils/config.py`: `ConfigManager` class (inactive — see ARCHITECTURE.md)
- `version.txt`: Single source for `__version__` and the `VERSION` display string

**Core Logic:**
- `main.py:4885`: `MainWindow` class (UI shell, mode dispatch, drag-and-drop, state)
- `main.py:4002`: `SinglePageCanvas` (PDF page widget with overlay rendering)
- `main.py:3806`: `WordBatchReplaceWorker` (still in `main.py`, not yet extracted)
- `main.py:4203`: `WebViewBridge` (Python ↔ JS bridge for Word preview)
- `privacyguard/workers/ocr_worker.py:35`: `_ModularOCRWorker` (real OCR thread)
- `privacyguard/workers/word_worker.py:16`: `_ModularWordWorker` (real Word scan thread)
- `privacyguard/workers/image_merge.py:13`: `ImageMergeWorker` (images → PDF)
- `privacyguard/ocr/mixed_pdf.py:76`: `collect_image_block_ocr_hits` (shared image-block OCR)
- `privacyguard/ocr/text_pdf.py:28`: `collect_text_pdf_hit_boxes` (shared text-layer hits)
- `privacyguard/utils/doc_converter.py:157`: `convert_doc_to_docx` (LibreOffice wrapper)

**Theme:**
- `theme.py:6`: `Theme` class with `LIGHT` / `DARK` dicts and layout constants
- `assets/branding/v38/`: v38 SVG icons referenced by the UI

**Testing:**
- `tests/unit/test_mixed_pdf_ocr.py`: Required regression for any OCR change
- `tests/unit/test_package_imports.py`: Required regression for any privacyguard import path change
- `tests/unit/test_convergence.py`: Required regression for any `main.py` / `privacyguard/*` drift
- `tests/unit/test_word_replace_rules.py`, `tests/unit/test_batch_word_replace.py`, `tests/unit/test_fstring_safety.py`: Required for Word changes
- `tests/unit/test_pdf_text_hit_dedup.py`, `tests/unit/test_ocr_api.py`: Required for OCR changes

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` — e.g., `ocr_worker.py`, `temp_manager.py`, `doc_converter.py`
- Test modules: `test_<area>.py` — e.g., `test_mixed_pdf_ocr.py`, `test_package_imports.py`
- Config templates: `*.json.template` for skeletons; `*.json` for live config
- Diary files: `YYYYMMDD[_HHMM]_<topic>.md` — e.g., `20260311_pyinstaller_packaging_fix_diary.md`
- Documentation: `UPPERCASE.md` for top-level reports (`STATUS.md`, `CHANGELOG.md`), `Title_Case.md` for guides

**Directories:**
- Package subdirectories: `snake_case` (e.g., `privacyguard/ocr/`, `privacyguard/workers/`)
- Documentation by lifecycle: `current/`, `diary/`, `archive/`
- Test layering: `unit/`, `integration/`, `e2e/`, `samples/`, `reports/`
- Reserved placeholders: `privacyguard/core/`, `privacyguard/ui/` (both empty `__init__.py` only)

**Python identifiers (observed in `main.py` and `privacyguard/`):**
- Classes: `PascalCase` (`MainWindow`, `OCRWorker`, `WordBatchReplaceWorker`, `TempFileManager`)
- Functions / methods: `snake_case` (`collect_text_pdf_hit_boxes`, `validate_safe_path`, `render_pdf_clip_to_bgr`)
- Module-level constants: `UPPER_SNAKE_CASE` (`DEFAULT_RULES`, `APP_NAME`, `VERSION`, `WORD_RULE_SCHEMA_VERSION`, `PROGRESS_UPDATE_INTERVAL`)
- Private helpers: leading underscore (`_ModularOCRWorker`, `_ModularWordWorker`, `_INTERACTIVE_JS_CODE`, `_shared_convert_doc_to_docx`)
- pyqtSignal names: `*_signal` suffix (`finished_signal`, `progress_signal`, `page_result_signal`, `error_signal`)

**Branching / commits:**
- Branch: `main` only
- Commit messages include a version prefix: `v37.7.6: ...` (Chinese summaries in recent history)

## Where to Add New Code

**New PDF redaction logic:**
- Shared helpers: extend `privacyguard/ocr/text_pdf.py` or `privacyguard/ocr/mixed_pdf.py`
- Worker-level OCR steps: extend `privacyguard/workers/ocr_worker.py` (preserve `cp23` coordinate conversion)
- UI rendering: keep adding to `SinglePageCanvas.paintEvent` in `main.py:4100` until the v38 UI refactor migrates it

**New Word redaction rule / preview logic:**
- Pure functions (no Qt): add to `main.py` near existing helpers (`normalize_word_replace_rules`, `apply_word_rules_to_text`, `merge_word_matches_with_priority` at lines 224, 358, 849)
- Worker changes: `privacyguard/workers/word_worker.py`
- New JavaScript snippets for the preview: append to `_INTERACTIVE_JS_CODE` in `main.py:4366` or to a new constant; remember per-`data-key` DOM patching (cp27) instead of full `setHtml`

**New dialog:**
- For now, add a new `QDialog` subclass in `main.py` alongside `SettingsDialog` (`main.py:1008`) or `WordReplaceRulesDialog` (`main.py:2961`)
- Long-term target: move into `privacyguard/ui/dialogs/` once that placeholder is fleshed out

**New shared utility (exceptions, paths, temp files, conversion):**
- Add to the appropriate `privacyguard/utils/*.py` file; **not** to `main.py`
- If a new exception type is needed, derive from `PrivacyAppError` (`privacyguard/utils/exceptions.py:8`) and re-export from `privacyguard/utils/__init__.py`

**New worker:**
- Add `privacyguard/workers/<name>_worker.py` with a `QThread` subclass
- Add to `_LAZY_IMPORTS` in both `privacyguard/__init__.py:61` and `privacyguard/workers/__init__.py:15`
- If `MainWindow` needs the worker to inject runtime config, add a thin wrapper in `main.py` (see the pattern at `main.py:4191` and `main.py:4358`)

**New test:**
- Unit tests for shared modules: `tests/unit/test_<module>.py` using `unittest`
- After adding, include the module in the baseline command listed in `CLAUDE.md`

**New branding / icon:**
- Icons: `assets/branding/v<version>/<icon_name>.svg`
- Logo: regenerate via `assets/logo/generate_icons.py` from `assets/logo/source/logo_master.svg`; per-platform packs under `assets/logo/{macos,windows,linux}/`

**New packaging step:**
- Windows: extend `packaging/windows/scripts/build_complete.bat` and add per-platform files under `packaging/windows/{assets,config,docs}/`
- macOS: extend `packaging/macos/scripts/build_complete.sh` and add files under `packaging/macos/{assets,config,docs}/`

**New docs:**
- Live status / plans: `docs/current/`
- Checkpoint work diary: `docs/diary/YYYYMMDD[_HHMM]_<topic>.md`
- Frozen records: `docs/archive/`

## Special Directories

**`.planning/`:**
- Purpose: GSD (Get-Shit-Done) planning artifacts
- Generated: by `/gsd-*` commands
- Committed: Yes — checked in
- Contents: `codebase/` (this analysis), `phases/`, `milestones/`, etc.

**`privacyguard/core/` and `privacyguard/ui/`:**
- Purpose: Reserved space for future migration of `MainWindow` and dialog code out of `main.py`
- Generated: No
- Committed: Yes (currently empty `__init__.py` only — placeholders, do not delete)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (by Python interpreter)
- Committed: No — listed in `.gitignore`

**`assets/logo/export/{16,24,32,48,64,128,256,512,1024}/`:**
- Purpose: Pre-rendered PNG logos at standard icon sizes
- Generated: Yes (by `assets/logo/generate_icons.py`)
- Committed: Yes (regeneration is supported but the committed versions are canonical)

**`packaging/windows/archive/`:**
- Purpose: Frozen Windows packaging artifacts from earlier release attempts
- Generated: No
- Committed: Yes (kept for forensics)

**`docs/archive/`:**
- Purpose: Historical frozen records (`old_docs/`, `v19_records/`, `v22_records/`, `v36.x/`)
- Generated: No
- Committed: Yes (do not edit; new docs go in `docs/current/`)

**`PDF/`:**
- Purpose: Sample input documents used during manual testing
- Generated: No
- Committed: Yes (treated as test fixtures; not source code)

**`tests/samples/`:**
- Purpose: Programmatic test fixtures (PDFs, images)
- Generated: Partially (some are checked in, some are produced by `tests/e2e/create_test_pdf.py`)
- Committed: Yes

---

*Structure analysis: 2026-08-10*