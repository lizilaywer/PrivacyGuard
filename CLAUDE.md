# CLAUDE.md

This file is the primary development guide for Claude Code and other coding agents working in this repository.

---

## Project Overview

**Project**: PrivacyGuard 脱敏卫士  
**Current Version**: v37.7.4 (`37.7.4 - Release Audit and Final Polish`)  
**Last Updated**: 2026-03-18  
**Status**: Release-ready on the `v37.7.4` runtime baseline; the v38 UI refactor code layer is complete and current work has shifted to screenshot-driven polish

PrivacyGuard is a Python + PyQt6 desktop application for intelligent redaction of PDF and Word documents.

### Current active capabilities

- PDF redaction:
  - text PDF search via PyMuPDF
  - image PDF OCR via RapidOCR
  - mixed PDF redaction via text-layer search + embedded image-block OCR
  - manual rectangle redaction
- Word redaction:
  - intelligent scan
  - manual precise/global redaction
  - multi-field replacement rules (`exact` / `regex`)
  - batch replace for `.docx` / `.doc`
- Word dual preview:
  - left: original preview with OCR/manual highlights
  - right: merged replaced preview (`rule > manual > ocr`)
- Drag & drop open
- Windows and macOS packaging scripts

---

## Read First

When resuming work, read these files in order:

1. `docs/current/STATUS.md`
2. `docs/current/DEV_LOG.md`
3. `docs/current/V38_UI_REFACTOR_PLAN.md`
4. `CHANGELOG.md`
5. `rollback_journal.md`
6. `docs/current/PRIORITY_REMEDIATION_PLAN.md`
7. `docs/diary/20260309_2338_release_sync_diary.md`
8. `docs/diary/20260311_pyinstaller_packaging_fix_diary.md`

---

## Current Technical Reality

### Main architecture

- `main.py` is still the active runtime entry and remains monolithic.
- `privacyguard/` contains shared modules and partial extractions, but not all runtime logic has moved there.
- Avoid reintroducing drift between `main.py` and `privacyguard/*`.

### Version source

- Single source of truth: `version.txt`
- `main.py` and `privacyguard.__version__` both read from it
- Packaging defaults and version resources must stay aligned with `version.txt`

### Active config path

- Runtime currently uses `SimpleConfig` in `main.py`
- Shared config utilities also exist in `privacyguard/utils/config.py`
- Do not assume `ConfigManager` is the active runtime path unless you have explicitly switched the app over

### OCR dependency behavior

- `privacyguard` package import is now lazy
- `RapidOCR` must only initialize at actual OCR execution time
- Do not add package-level eager OCR imports back into `privacyguard/__init__.py` or `privacyguard/workers/__init__.py`

### Mixed PDF handling

- Mixed PDF pages must not be treated as text-only or scan-only.
- The active path is:
  1. text-layer hit collection
  2. embedded image block discovery via `page.get_text("dict")`
  3. image-block OCR
  4. local OCR box offset back into page coordinates
- Shared logic lives in `privacyguard/ocr/mixed_pdf.py`

---

## Key Runtime Data Structures

### PDF state

- `self.page_data[page_num] = {"ocr": [...], "manual": [...]}`

### Word state

- `self.word_data[key] = {"text": ..., "ocr": [...], "manual": [...], ...}`
- `self.word_replace_rules` stores session-level multi-field replacement rules

### Word preview model

The active path is:

1. DOCX -> HTML via `mammoth`
2. HTML tagged with `data-key`
3. Left panel updates by block with original-text highlight fragments
4. Right panel updates by block with merged replacement fragments
5. DOM is updated via keyed JavaScript patching instead of always doing full `setHtml()`

Important:

- compare mode may start with the right panel hidden or blank
- `cp20` added per-panel loaded-source tracking
- `cp27` restricted incremental DOM patching to actual word blocks and prevents highlight-node corruption
- when compare mode becomes active after an empty state, the right panel must reload the full document before applying partial updates

---

## Main Files

- `main.py` - active application runtime
- `theme.py` - UI theme definitions
- `version.txt` - single version source
- `config.json` - local runtime config
- `privacyguard/__init__.py` - package metadata + lazy exports
- `privacyguard/ocr/text_pdf.py` - shared text-PDF hit collection
- `privacyguard/ocr/mixed_pdf.py` - shared mixed-PDF image-block OCR helper
- `privacyguard/workers/ocr_worker.py` - modular OCR worker

---

## Common Commands

### Run app

```bash
cd /Users/a49144/Desktop/codexhub/PrivacyGuardApp
python3 main.py
```

### Compile check

```bash
python3 -m compileall -q main.py privacyguard tests
```

### Main regression suite

```bash
python3 -m unittest \
  tests.unit.test_mixed_pdf_ocr \
  tests.test_path_validation \
  tests.unit.test_ocr_api \
  tests.unit.test_package_imports \
  tests.unit.test_pdf_text_hit_dedup \
  tests.unit.test_app_config \
  tests.unit.test_word_replace_rules \
  tests.unit.test_batch_word_replace \
  -v
```

Current verified baseline: `52/52`.

### Version check

```bash
cat version.txt
```

---

## Packaging

Use the current packaging docs instead of old ad-hoc notes:

- `docs/packaging/README.md`
- `docs/packaging/windows-packaging-guide.md`
- `docs/packaging/macos-packaging-guide.md`
- `packaging/README.md`

Main commands:

```bash
# macOS
./packaging/macos/scripts/build_complete.sh

# Windows
packaging/windows/scripts/build_complete.bat
```

---

## Current Checkpoints

- `20260309_runtime_remediation_cp18_verified`
- `20260309_word_compare_bugfix_cp20_verified`
- `20260309_mixed_pdf_ocr_cp23_verified`
- `20260309_release_sync_cp25_verified`
- `20260310_word_preview_highlight_cp27_verified`
- `20260310_release_sync_cp29_verified`
- `20260311_pyinstaller_packaging_fix_cp30_verified`
- `v38_ui_refactor_cp31_20260313_140645`

Rollback references:

- `rollback_journal.md`
- `ROLLBACK_GUIDE.md`
- `restore_checkpoint.sh`

---

## Current Development Direction

Current default track:

1. screenshot-driven UI polish on top of the completed v38 code layer
2. Phase 2: per-file rule mapping for batch replace
3. batch rule-set templates
4. preview highlight filtering by source (`rule / manual / ocr`)

If the UI polish track is paused and no regressions are being fixed, default next feature work should be:

1. Phase 2: per-file rule mapping for batch replace
2. batch rule-set templates
3. preview highlight filtering by source (`rule / manual / ocr`)

If a regression appears in PDF OCR, prioritize checking:

1. text-layer vs image-block split
2. image clip extraction validity
3. OCR box offset back to page coordinates
4. deduplication after merged hits
