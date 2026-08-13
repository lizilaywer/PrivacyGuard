<!-- refreshed: 2026-08-10 -->
# Architecture

**Analysis Date:** 2026-08-10

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                      PyQt6 Desktop Runtime (QApplication)                 │
│                         `main.py`  (~12.6k LOC, monolithic)               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │  MainWindow    │  │  Dialogs       │  │  SinglePage    │               │
│  │  (QMainWindow) │  │  SettingsDialog│  │  Canvas        │               │
│  │  `main.py`     │  │  WordRule Dlg  │  │  (QLabel)      │               │
│  │  L4885         │  │  ImageList Dlg │  │  `main.py`     │               │
│  │                │  │  Feedback /    │  │  L4002         │               │
│  │                │  │  Donate Dialogs│  │                │               │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘               │
│           │  drag/drop / file open / toolbar / settings / batch flow      │
│           ▼                  ▼                    ▼                       │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                  Worker Subclasses (in main.py)                       │ │
│  │   OCRWorker (L4191)    WordWorker (L4358)   WordBatchReplaceWorker   │ │
│  │   = thin wrapper that delegates to `_ModularOCRWorker` etc.          │ │
│  └────────┬──────────────────────┬─────────────────────┬─────────────────┘ │
│           │                      │                     │                   │
│           ▼                      ▼                     ▼                   │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │            `privacyguard/`  (partially-extracted shared lib)          │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐      │ │
│  │  │ workers/   │  │ ocr/       │  │ utils/     │  │ core/, ui/ │      │ │
│  │  │ ocr_worker │  │ base, mgr  │  │ exceptions │  │ (placeholders) │ │
│  │  │ word_worker│  │ rapidocr   │  │ temp_mgr   │  │             │      │ │
│  │  │ image_merge│  │ text_pdf   │  │ security   │  │             │      │ │
│  │  └────────────┘  │ mixed_pdf  │  │ config     │  │             │      │ │
│  │                  └────────────┘  │ doc_conv   │  │             │      │ │
│  │                                  └────────────┘  │             │      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│           │                      │                     │                   │
│           ▼                      ▼                     ▼                   │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                       External Libraries                              │ │
│  │  PyMuPDF (fitz)  PyQt6 + WebEngine  python-docx  mammoth  RapidOCR   │ │
│  │  opencv-python  Pillow  numpy  BeautifulSoup  LibreOffice (subproc) │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Runtime entry / app bootstrap | `QApplication` setup, global exception hooks, icon load | `main.py:12478-12611` |
| `SimpleConfig` | Active runtime config loader backed by `config.json` | `main.py:98-165` |
| `MainWindow` | Top-level `QMainWindow`, workbench shell, mode dispatch (pdf / word / batch / image_merge), `setup_ui`, drag-and-drop, theme application | `main.py:4885` |
| `SettingsDialog` | Tabs for redaction rules, custom keywords, OCR adjustment, density | `main.py:1008` |
| `WordReplaceRulesDialog` | Multi-field rule editor (find/replace/regex/exact) with import/export | `main.py:2961` |
| `ImageListDialog` | Re-order image list before merging | `main.py:3198` |
| `FeedbackDialog` / `DonateDialog` | User support channels | `main.py:3323`, `main.py:3726` |
| `SinglePageCanvas` | PDF page rendering, mask color, manual rect drag | `main.py:4002` |
| `OCRWorker` (wrapper) | Thin subclass that injects `box_adjust_ratio` from config and delegates to modular worker | `main.py:4191` |
| `WordWorker` (wrapper) | Thin subclass that injects `DEFAULT_RULES` and delegates | `main.py:4358` |
| `WordBatchReplaceWorker` | Batch apply Word rules to many `.docx`/`.doc` files | `main.py:3806` |
| `WebViewBridge` | Python ↔ JavaScript bridge over `QWebChannel` for the Word preview | `main.py:4203` |
| `_ModularOCRWorker` (modular OCR) | Real OCR thread (text + image-block OCR, seal detection, box shrink) | `privacyguard/workers/ocr_worker.py:35` |
| `_ModularWordWorker` (modular Word) | Word smart-scan thread (paragraphs + tables) | `privacyguard/workers/word_worker.py:16` |
| `ImageMergeWorker` | Concatenate images into a single PDF | `privacyguard/workers/image_merge.py:13` |
| `BaseOCREngine` / `OCREngineManager` / `RapidOCREngine` | OCR abstraction layer; v37.4.0 collapses to a single RapidOCR engine | `privacyguard/ocr/base.py:30`, `privacyguard/ocr/manager.py:11`, `privacyguard/ocr/rapidocr.py:15` |
| `collect_text_pdf_hit_boxes` | Shared text-layer hit collector for text PDFs | `privacyguard/ocr/text_pdf.py:28` |
| `collect_image_block_ocr_hits` | Embedded image-block OCR with page-coordinate mapping for mixed PDFs | `privacyguard/ocr/mixed_pdf.py:76` |
| `TempFileManager` | Thread-safe temp file/dir registry with `atexit` cleanup | `privacyguard/utils/temp_manager.py:17` |
| `validate_safe_path` / `resource_path` | Path safety + PyInstaller resource path resolver | `privacyguard/utils/security.py:14`, `privacyguard/utils/security.py:110` |
| Exception hierarchy | `PrivacyAppError` and subclasses | `privacyguard/utils/exceptions.py:8` |
| `convert_doc_to_docx` | `.doc` → `.docx` via LibreOffice (with antiword fallback) | `privacyguard/utils/doc_converter.py:157` |
| `ConfigManager` (NOT runtime path) | Modular config class with validation; not currently active | `privacyguard/utils/config.py:128` |
| `Theme` | Light/dark color tokens, fonts, spacing | `theme.py:6` |
| `version.txt` | Single source of truth for the version string | `version.txt` |

## Pattern Overview

**Overall:** Hybrid monolithic UI + extracted shared library (single-process PyQt6 desktop app).

**Key Characteristics:**

- `main.py` is a 12,611-line **monolithic application entry**: it owns `MainWindow`, dialogs, the canvas widget, all `pyqtSignal`/`pyqtSlot` definitions, and JavaScript string literals embedded as Python constants (`_INTERACTIVE_JS_CODE`).
- `privacyguard/` is a **partially-extracted** package. Modules that hold heavy lifting (workers, OCR helpers, utilities) have been factored out. The UI layer (`privacyguard/ui/`) and a `privacyguard/core/` directory exist as **empty placeholders** (`__init__.py` only) — UI composition has not been migrated.
- **Thin-wrapper inheritance** at the worker boundary: `main.py` defines `OCRWorker(_ModularOCRWorker)` and `WordWorker(_ModularWordWorker)` solely to inject runtime-specific defaults (`box_adjust_ratio`, `DEFAULT_RULES`) and to preserve import-time ergonomics for callers that still reference them by short name.
- **Lazy import discipline**: `privacyguard/__init__.py` and `privacyguard/workers/__init__.py` implement `__getattr__` so that heavyweight modules (RapidOCR, QThread workers) are only imported on first attribute access. This keeps `import privacyguard` cheap and avoids loading native OCR DLLs unless OCR is actually exercised.
- **Single-engine OCR** (post v37.4.0): `OCREngineManager` deliberately keeps only `RapidOCREngine`. The abstract base class and dataclasses (`BaseOCREngine`, `OCRResult`, `CharInfo`) remain for future multi-engine support.
- **Two config sources**: runtime config is `SimpleConfig` in `main.py` (reads `config.json` directly); a richer `ConfigManager` exists at `privacyguard/utils/config.py` but is **not** the active runtime path.

## Layers

**UI Layer (PyQt6 widgets & dialogs):**
- Purpose: Render the workbench, dialogs, canvas, and QWebEngineView for Word preview
- Location: `main.py` (top-level classes) and `theme.py`
- Contains: `MainWindow`, `SettingsDialog`, `WordReplaceRulesDialog`, `ImageListDialog`, `FeedbackDialog`, `DonateDialog`, `SinglePageCanvas`, `WebViewBridge`, the `_INTERACTIVE_JS_CODE` constant
- Depends on: `privacyguard.workers`, `privacyguard.ocr`, `privacyguard.utils`, `theme`, `PyQt6.*`
- Used by: `python3 main.py` entry point only

**Worker Layer (QThread-based background jobs):**
- Purpose: Long-running tasks off the GUI thread, communicating via `pyqtSignal`
- Location: `privacyguard/workers/` with thin wrappers in `main.py`
- Contains: `OCRWorker`, `WordWorker`, `ImageMergeWorker` (modular); `WordBatchReplaceWorker` (still lives in `main.py`)
- Depends on: `privacyguard.ocr`, `privacyguard.utils`, `PyQt6.QtCore`, `fitz`, `cv2`, `numpy`, `python-docx`
- Used by: `MainWindow` schedules scans / batch replaces; thin wrappers in `main.py` re-export them

**OCR Helper Layer (pure functions, no Qt):**
- Purpose: Reusable text-layer and image-block OCR logic with no Qt coupling
- Location: `privacyguard/ocr/`
- Contains: `base.py` (dataclasses + ABC), `rapidocr.py` (single engine), `manager.py` (singleton wrapper), `text_pdf.py` (text-layer hit collection), `mixed_pdf.py` (image-block OCR + page-coordinate mapping)
- Depends on: `fitz`, `cv2`, `numpy`, `rapidocr_onnxruntime`
- Used by: `privacyguard/workers/ocr_worker.py` and `main.py` (`collect_text_pdf_hit_boxes`, `collect_image_block_ocr_hits`)

**Utility Layer:**
- Purpose: Cross-cutting helpers (exceptions, temp files, path safety, DOC conversion, modular config)
- Location: `privacyguard/utils/`
- Contains: `exceptions.py`, `temp_manager.py`, `security.py`, `doc_converter.py`, `config.py` (inactive)
- Depends on: standard library, `python-docx`, LibreOffice subprocess
- Used by: both UI layer and worker layer

**Asset & Theme Layer:**
- Purpose: Styling tokens and branding assets
- Location: `theme.py`, `assets/`, `config.json`
- Contains: `Theme.LIGHT` / `Theme.DARK` dicts; branding icons under `assets/branding/v38/`; logo set under `assets/logo/`
- Depends on: nothing internal
- Used by: dialogs and the main window reference `Theme.LIGHT` / `Theme.DARK` directly

**Documentation / Build Layer:**
- Purpose: PyInstaller packaging, run scripts, dev guides
- Location: `packaging/`, `scripts/`, `docs/`
- Contains: macOS / Windows build scripts; release / diary / status / current / archive docs
- Depends on: nothing internal
- Used by: human operators and CI flows; `packaging/windows/scripts/build_complete.bat` and `packaging/macos/scripts/build_complete.sh`

## Data Flow

### Primary Request Path — Open & Redact a PDF

1. User drags file onto window or invokes open menu → `MainWindow.dragEnterEvent` / open-file handler (`main.py:5183`)
2. `MainWindow` dispatches by file extension to a mode (`pdf`, `word`, `batch`, `image_merge`); state set via `self.doc_type` / `self.current_ui_mode` (`main.py:4905`)
3. For PDF: page rendered to `SinglePageCanvas` (`main.py:4002`); user clicks "Scan" or auto-scan triggers `MainWindow._start_ocr_scan`
4. `MainWindow` instantiates `OCRWorker(pdf_path, rules, ...)` (the wrapper class) → constructor injects `box_adjust_ratio` from `SimpleConfig` and calls `_ModularOCRWorker.__init__` (`main.py:4191-4199`)
5. Worker thread: `_ModularOCRWorker.run` calls `collect_text_pdf_hit_boxes` for the text layer; iterates pages via `collect_image_block_ocr_hits` for embedded images; merges results with OCR local → page coordinate conversion (`privacyguard/workers/ocr_worker.py`, `privacyguard/ocr/text_pdf.py:28`, `privacyguard/ocr/mixed_pdf.py:76`)
6. Worker emits `page_result_signal(page_idx, rects)` per page; `MainWindow` updates `self.page_data[page_num] = {"ocr": [...], "manual": [...]}` (`main.py:4908`)
7. `MainWindow` repaints `SinglePageCanvas` with overlay rectangles (`SinglePageCanvas.paintEvent`, `main.py:4100`)
8. User triggers save → `MainWindow` writes redactions back into the PDF using `fitz` with redacted rectangles; for scanned-image hits, it stamps a colored rect on the rendered pixmap and re-inserts.

### Primary Request Path — Open & Replace in Word

1. Open `.docx`/`.doc` file → `MainWindow` calls `convert_doc_to_docx` (LibreOffice) if `.doc` (`privacyguard/utils/doc_converter.py:157`)
2. `mammoth` converts DOCX → HTML; HTML is loaded into `QWebEngineView` (`self.word_preview`) with each block annotated via `data-key`
3. User clicks "智能扫描" → `MainWindow` instantiates `WordWorker` (wrapper) which delegates to `_ModularWordWorker` (`privacyguard/workers/word_worker.py:16`)
4. Worker iterates `word_doc.paragraphs` and table cells, runs regex matches, writes into `self.word_data[key] = {"text": ..., "ocr": [...], "manual": [...]}` and emits `finished_signal`
5. For compare mode (`self.word_compare_mode = True`), `WebViewBridge` (`main.py:4203`) pushes JS snippets via `QWebChannel` that do per-`data-key` DOM patching (cp27) instead of full `setHtml` reloads; right-pane replacement highlights merge with priority `rule > manual > ocr` (`main.py:849` `merge_word_matches_with_priority`)
6. Save → `replace_matches_in_paragraph` rewrites `python-docx` runs in place (`main.py:951`)

### Batch Word Replace Path

1. User opens batch panel → adds multiple `.docx`/`.doc` files into `self.batch_selected_files` (`main.py:4913`)
2. `MainWindow` instantiates `WordBatchReplaceWorker(file_paths, rules, default_replacement_text)` (`main.py:3806`)
3. Worker iterates files; on `.doc` it calls `convert_doc_to_docx`; applies rules via `_apply_rules_to_document`; emits `progress_signal`
4. Per-file errors surface via `_wait_for_error_decision` for user to choose skip/retry/abort

### Image Merge Path

1. User picks images → `ImageListDialog.get_ordered_paths` returns re-ordered list (`main.py:3310`)
2. `MainWindow` schedules `ImageMergeWorker(image_paths, output_path)` (`privacyguard/workers/image_merge.py:13`)
3. Worker builds a fresh `fitz.open()` PDF and inserts each image at native resolution

**State Management:**

- `self.page_data`, `self.word_data`, `self.word_replace_rules`, `self.batch_*`, `self.image_merge_*` all live on `MainWindow` as plain attributes (`main.py:4908-4926`)
- `_word_data_lock = QMutex()` protects `word_data` against worker writes (`main.py:4918`)
- `self.temp_manager = TempFileManager()` registered with `atexit` for cleanup on exit (`main.py:4928-4932`)
- `QSettings("PrivacyGuard", "App")` stores window geometry (`main.py:4891`)

## Key Abstractions

**Worker Base Pattern (QThread + pyqtSignal):**
- Purpose: Off-thread long-running tasks with progress and result signals
- Examples: `privacyguard/workers/ocr_worker.py:35`, `privacyguard/workers/word_worker.py:16`, `privacyguard/workers/image_merge.py:13`
- Pattern: `class XxxWorker(QThread)` with `progress_signal = pyqtSignal(int)`, `finished_signal = pyqtSignal(...)`, `error_signal = pyqtSignal(str)`. Always check `self.isInterruptionRequested()` in loops to honor cancellation.

**OCR Engine Abstraction:**
- Purpose: Hide engine-specific output format behind a uniform dataclass
- Examples: `privacyguard/ocr/base.py:30` (ABC), `privacyguard/ocr/rapidocr.py:15` (concrete), `privacyguard/ocr/manager.py:11` (singleton)
- Pattern: `BaseOCREngine.recognize(image) -> List[OCRResult]`; `OCRResult` carries `text`, `box`, `chars`, `confidence`, `engine`. v37.4.0 keeps only `RapidOCR`; multi-engine support is reserved via the abstract base.

**Mixed-PDF Hit Collection:**
- Purpose: Per-page OCR of embedded image blocks with page-coordinate mapping
- Examples: `privacyguard/ocr/mixed_pdf.py:76` (`collect_image_block_ocr_hits`)
- Pattern: `collect_embedded_image_clip_rects(page_dict)` → `render_pdf_clip_to_bgr(page, clip_rect, scan_scale)` → `recognize_fn(scan_img)` → `iter_ocr_lines(ocr_results)` → `calculate_rect_fn(box, text, span, scan_img)` → `clip_to_page_rect_fn(local_rect, clip_rect)`. The OCR-local-to-page transform is the single shared step (cp23).

**Page Data Dictionary:**
- Purpose: Per-page redaction state for the PDF canvas
- Shape: `self.page_data[page_num] = {"ocr": [Rect, ...], "manual": [Rect, ...]}` (`main.py:4908`)
- Source-of-truth pattern: workers append via `page_result_signal`; `MainWindow` merges into the dict; `SinglePageCanvas.paintEvent` reads only.

**Word Data Dictionary:**
- Purpose: Per-block Word content + matches
- Shape: `self.word_data[key] = {"text": ..., "ocr": [...], "manual": [...]}` plus session-level `self.word_replace_rules` (`main.py:4915`, `main.py:4917`)
- Source-of-truth pattern: `WordWorker` writes via `finished_signal`; manual edits via `WebViewBridge` slots append to `manual`.

## Entry Points

**Application Entry (`main.py`):**
- Location: `main.py:12478-12611` (`if __name__ == "__main__":`)
- Triggers: `python3 main.py`
- Responsibilities:
  - Install global + threading exception hooks
  - Optionally preload OCR engine if `PRIVACYGUARD_PRELOAD_OCR=true`
  - Construct `QApplication`, set window icon from `assets/logo/export/256/logo_default_256.png`
  - Build and show `MainWindow`, run `app.exec()`

**Modular Package Entry (`privacyguard/__init__.py`):**
- Location: `privacyguard/__init__.py`
- Triggers: Any `import privacyguard`
- Responsibilities: Eager-load exception classes, `TempFileManager`, `validate_safe_path`, `resource_path`; lazy-load workers and OCR types via `__getattr__`; expose `__version__` read from `version.txt`

**Worker Package Entry (`privacyguard/workers/__init__.py`):**
- Location: `privacyguard/workers/__init__.py`
- Triggers: `import privacyguard.workers`
- Responsibilities: Pure lazy-load surface — every worker is resolved via `__getattr__` to keep native OCR / Qt threads unimported until first use.

**Build Entry:**
- Windows: `packaging/windows/scripts/build_complete.bat`
- macOS: `packaging/macos/scripts/build_complete.sh`
- Source: `main.py` is the PyInstaller target (`requirements.txt` pins `pyinstaller==6.18.0`)

## Architectural Constraints

- **Threading model:** Single Qt event loop on the main thread; long-running work runs on `QThread` subclasses (`OCRWorker`, `WordWorker`, `ImageMergeWorker`, `WordBatchReplaceWorker`). Cancellation is cooperative via `self.isInterruptionRequested()`. `_word_data_lock = QMutex()` (`main.py:4918`) is the only documented mutex; `TempFileManager` has its own `threading.Lock` (`privacyguard/utils/temp_manager.py:36`).
- **Global state:**
  - `config = SimpleConfig()` module-level singleton (`main.py:167`) — the active runtime config handle.
  - `DEFAULT_RULES` built from `config.get_redaction_rules()` (`main.py:212`) — module-level dict shared by `SettingsDialog`, `MainWindow.active_rules`, and `_ModularWordWorker`.
  - `APP_NAME` / `VERSION` constants read at import time (`main.py:175-176`).
  - `RapidOCR = None` + `OCR_INIT_ERROR` module-level placeholders used by `init_ocr_engine()` (`main.py:38-40`).
- **Lazy-loading boundary:** `privacyguard/__init__.py` and `privacyguard/workers/__init__.py` MUST keep `__getattr__`-based lazy resolution. `privacyguard/ocr/__init__.py` does eager imports (which is fine — the package import path is rare). Do not introduce eager imports at the package root that pull in native OCR DLLs.
- **Configuration path:** `SimpleConfig` in `main.py` is the active runtime config. `privacyguard/utils/config.py::ConfigManager` exists but is **not** wired into the runtime — do not treat it as the live source until a deliberate swap.
- **Version single-source:** `version.txt` (currently `37.7.6`) feeds `main.py::read_app_version()` and `privacyguard/__init__._read_version()`. Any version bump must update `version.txt` and verify both readers pick it up.
- **Circular imports:** The thin-wrapper classes in `main.py` (`OCRWorker`, `WordWorker`) import the modular classes at module top-level (`main.py:34-35`). The wrappers exist specifically to keep that import dependency one-directional (runtime → package, not package → runtime).
- **Empty placeholders:** `privacyguard/core/__init__.py` and `privacyguard/ui/__init__.py` are 0-byte files. They signal **reserved space** for future migration of `MainWindow` and dialogs out of `main.py`; they are not yet wired.
- **No online calls:** The app is offline; no telemetry. `config.json` is local-only.

## Anti-Patterns

### Re-implementing shared OCR logic inside `main.py`

**What happens:** When a new OCR-related feature is added, contributors copy the "happy path" inline rather than reusing `collect_text_pdf_hit_boxes` / `collect_image_block_ocr_hits` from `privacyguard/ocr/`.
**Why it's wrong:** This is exactly the v37.7.6 drift that triggered the "Full Convergence Remediation" — duplicate implementations drift in behavior (different de-dup, different coordinate conversion) and silently regress text/image-block split logic.
**Do this instead:** Add the helper to `privacyguard/ocr/` (or extend `collect_image_block_ocr_hits`'s dependency-injection surface) and call it from both the worker and any `main.py` code path. See `privacyguard/ocr/mixed_pdf.py:76` for the established `recognize_fn` / `calculate_rect_fn` / `clip_to_page_rect_fn` injection points.

### Treating `privacyguard/utils/config.py::ConfigManager` as the runtime config

**What happens:** New code uses `ConfigManager` directly, assuming it is live.
**Why it's wrong:** The active runtime path is `main.py::SimpleConfig` (`main.py:98`). The two classes diverge on persistence keys and validation rules; mixing them yields inconsistent behavior.
**Do this instead:** Read/write config via `config = SimpleConfig()` (the module-level singleton in `main.py:167`). If you need the richer interface, migrate the runtime explicitly first and document the swap in `CHANGELOG.md` and `docs/current/STATUS.md`.

### Eager imports of heavy modules in `privacyguard/__init__.py` or `privacyguard/workers/__init__.py`

**What happens:** Someone adds `from privacyguard.workers.ocr_worker import OCRWorker` at the top of `privacyguard/__init__.py` for convenience.
**Why it's wrong:** This pulls `PyQt6.QtCore`, `cv2`, `fitz`, and eventually `rapidocr_onnxruntime` into every importer — including tests, the PyInstaller build, and any non-OCR code path. cp30 specifically fixed an earlier `privacyguard.utils.security` regression that crashed packaging when lazy-loading broke.
**Do this instead:** Extend `_LAZY_IMPORTS` in `privacyguard/__init__.py:61` and let `__getattr__` resolve the import on first use.

### Bypassing `_ModularOCRWorker` / `_ModularWordWorker` with a fresh inline `QThread`

**What happens:** A new PDF or Word flow creates an ad-hoc `QThread` subclass inside `main.py` to avoid "fighting" the wrapper classes.
**Why it's wrong:** Bypasses the `box_adjust_ratio` injection in `main.py:4195` (OCR wrapper) and the `DEFAULT_RULES` injection in `main.py:4363` (Word wrapper), causing silent regressions in production behavior.
**Do this instead:** Subclass the wrapper (`class MyOcrWorker(OCRWorker)`) so the injection chain still runs, or extend the modular worker and add a thin wrapper in `main.py` for it.

### Editing `main.py` to add new UI logic instead of using the `privacyguard/ui/` placeholder

**What happens:** Contributors pile more widgets, dialogs, and `setup_ui` code into the already-12.6k-line `main.py`.
**Why it's wrong:** Compounds the v38 UI refactor's blast radius (`docs/current/V38_UI_REFACTOR_PLAN.md`) and makes testing dialog logic without `QApplication` impossible.
**Do this instead:** Move widget classes into `privacyguard/ui/` when adding new ones; do not let `main.py` exceed current size.

## Error Handling

**Strategy:** Exception hierarchy rooted at `PrivacyAppError` (`privacyguard/utils/exceptions.py:8`) with subclasses `ConversionError`, `FileFormatError`, `SecurityError`, `MemoryLimitError`, `WorkerCancelledError`. Workers swallow most exceptions internally and emit `error_signal` so the UI can present a `QMessageBox`.

**Patterns:**

- Global `sys.excepthook` and `threading.excepthook` installed in `main.py:12479-12499` so uncaught exceptions show a user-facing `QMessageBox.critical` instead of a silent crash.
- Workers catch `(IOError, OSError, RuntimeError, ValueError, AttributeError, KeyError, IndexError)` and continue processing remaining work, emitting partial results with `__scan_meta__` (`privacyguard/workers/word_worker.py:89`, `privacyguard/workers/ocr_worker.py`).
- `validate_safe_path` returns `(is_safe: bool, error_msg: Optional[str])`; callers raise `SecurityError` on failure (`privacyguard/utils/security.py:14`).
- `TempFileManager.cleanup()` returns a list of `errors`; never raises on cleanup failure (`privacyguard/utils/temp_manager.py:92`).
- `init_ocr_engine` (`main.py:41`) catches `ImportError`, `OSError`, and `Exception` separately so each failure mode produces a specific diagnostic message.

## Cross-Cutting Concerns

**Logging:** `print()` with `[TAG]` prefixes throughout (e.g., `[OCR]`, `[OCR ERROR]`, `[MainWindow]`, `[FATAL ERROR]`). No logging framework; no log files. Stack traces printed via `traceback.print_exc()` for unexpected exceptions. `threading.excepthook` logs thread exceptions (`main.py:12490`).

**Validation:** Path validation via `validate_safe_path` before any file access; extension whitelist per call site. `SimpleConfig` reads `config.json` with try/except around `json.load` (`main.py:108-115`). `ConfigManager` provides schema validation (`privacyguard/utils/config.py`) but is not in the active path.

**Authentication:** None — the app is offline and operates only on local files selected by the user. There is no user account, no token, no remote endpoint.

**Configuration:** `config.json` at repo root, edited via the `SettingsDialog`. `config.json.template` ships as the canonical skeleton. Window geometry persisted via `QSettings("PrivacyGuard", "App")` (`main.py:4891`). Per-user state persists in OS-native QSettings storage; `QStandardPaths` defaults are used.

**Resource Resolution:** `resource_path(relative_path)` (`privacyguard/utils/security.py:110`) supports PyInstaller `sys._MEIPASS`. Application icon loaded from `assets/logo/export/256/logo_default_256.png` (`main.py:12523`).

**Threading / Cancellation:** All workers check `self.isInterruptionRequested()` per item; `MainWindow` calls `requestInterruption()` on the active worker before scheduling a new one. `self.worker_lock = QMutex()` (`main.py:4931`) serializes worker lifecycle changes.

---

*Architecture analysis: 2026-08-10*