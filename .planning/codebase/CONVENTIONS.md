# Coding Conventions

**Analysis Date:** 2026-08-10

## Naming Patterns

**Files:**
- Modules in `privacyguard/<area>/<module>.py` use `snake_case` (e.g. `privacyguard/ocr/mixed_pdf.py`, `privacyguard/utils/temp_manager.py`).
- Test modules use the `test_<subject>.py` pattern and live under `tests/unit/` for unit tests, `tests/integration/` for integration scripts, `tests/e2e/` for end-to-end helpers (e.g. `tests/unit/test_mixed_pdf_ocr.py`).
- Singleton entry module is the top-level `main.py`; it is intentionally large (the "active runtime monolith").

**Functions:**
- Public helpers use `snake_case` verbs: `validate_safe_path`, `collect_text_pdf_hit_boxes`, `render_pdf_clip_to_bgr`.
- Pure utility / shared helpers that accept the heavy machinery as parameters are prefixed with the verb describing the action (`compile_active_patterns`, `iter_unique_text_matches`, `iter_ocr_lines`).
- Private helpers are prefixed with a single underscore: `_wrap_html_document`, `_build_word_text_blocks`, `_calculate_from_line`.
- Worker lifecycle methods are `run`; the slot methods that emit progress or page results end with `_signal` (`finished_signal`, `progress_signal`, `error_signal`, `page_result_signal`).
- Constants are uppercase with underscores: `DEFAULT_CONFIG`, `PROGRESS_UPDATE_INTERVAL`, `WORD_PREVIEW_BLOCK_SELECTOR`.

**Variables:**
- Local variables: `snake_case` (e.g. `image_clip_rects`, `page_dict`, `scan_scale`).
- Module-level singletons store the instance in `_instance` with `_instance_lock` and `_initialized` (see `privacyguard/utils/config.py:148-158`).
- Boolean state variables are descriptive phrases: `isInterruptionRequested()`, `is_available()`, `use_enhance`.

**Types:**
- Classes use `PascalCase`: `SimpleConfig`, `WordWorker`, `OCRWorker`, `ImageMergeWorker`, `TempFileManager`, `ConfigManager`.
- Exception classes end with `Error`: `PrivacyAppError`, `ConversionError`, `SecurityError`, `MemoryLimitError`, `ConfigError`, `ConfigValidationError`, `ConfigNotFoundError`.
- Dataclasses (used in OCR layer): `CharInfo`, `OCRResult` — both use `@dataclass` decorator.
- Worker result signals are typed `pyqtSignal(<python-type>)` (e.g. `pyqtSignal(dict)`, `pyqtSignal(int, list)`).

## Code Style

**Formatting:**
- No project-level formatter config (no `.black`, `.ruff.toml`, or `.prettierrc` is checked in). Run `python3 -m compileall -q main.py privacyguard tests` to verify syntactic validity instead.
- 4-space indentation across all `.py` files.
- Maximum line length is not enforced; many `main.py` lines exceed 100 chars (intentional to keep `f""` CSS blocks intact).
- Encoding is declared explicitly in non-trivial scripts: `# -*- coding: utf-8 -*-` in `check_syntax.py`.

**Linting:**
- No formal linter configuration in repo. `check_syntax.py` performs `ast.parse()` on every shared module to catch syntax regressions.
- `tests/unit/test_fstring_safety.py` is a *custom lint-style test*: it scans `main.py` for unescaped CSS-style `{property: ...}` inside f-strings and fails if it finds any (because `f"...{...}..."` would raise `NameError` at runtime).

**Naming for tests vs. production:**
- Test method names use the `test_<expectation>` pattern with snake_case and may include context: `test_build_output_path_with_conflict`, `test_read_app_version_falls_back_to_current_release`, `test_word_panel_update_script_targets_only_word_blocks`.
- Module-level test classes prefix with `Test`: `TestMixedPdfOcr`, `TestWordReplaceRules`, `TestConfigAlignment`, `TestConvergence`.

## Import Organization

**Order:**
1. Standard library (`import os`, `import sys`, `import re`, `import json`, `import ast`, `import tempfile`, `import threading`).
2. Third-party packages (`from docx import Document`, `from PIL import Image`, `import fitz`, `import cv2`, `import numpy as np`, `from PyQt6.QtCore import QThread, pyqtSignal`).
3. First-party `privacyguard.*` modules.
4. Local / `main` modules (for tests only).

Example from `privacyguard/workers/ocr_worker.py:23-29`:

```python
from PyQt6.QtCore import QThread, pyqtSignal, QRectF
import re

from privacyguard.ocr.mixed_pdf import (
    collect_embedded_image_clip_rects,
    collect_image_block_ocr_hits,
)
from privacyguard.ocr.text_pdf import collect_text_pdf_hit_boxes
```

**Path Aliases:**
- No `sys.path` aliases or `pyproject.toml` mapping; tests rely on `import os, sys; sys.path.insert(0, ROOT)` only in `tests/test_path_validation.py`. Other tests work because pytest-style module discovery runs from the repo root.
- Shared modules must always use *absolute* imports (e.g. `from privacyguard.ocr.base import BaseOCREngine`) to remain PyInstaller-friendly (see comment at `privacyguard/__init__.py:23-24`).

**Heavy / optional dependencies are imported lazily:**
- `rapidocr_onnxruntime` is imported inside `RapidOCREngine.recognize` and `RapidOCREngine.is_available` (`privacyguard/ocr/rapidocr.py:27,43`) to avoid forcing OCR at startup.
- Top-level package re-exports of workers/engines go through `__getattr__` + `_LAZY_IMPORTS` (`privacyguard/__init__.py:61-79`, `privacyguard/workers/__init__.py:15-30`). Never add eager `from privacyguard.workers import WordWorker` at package level — that defeats the lazy-loading guarantee.

## Error Handling

**Patterns:**

1. **Custom exception hierarchy rooted at `PrivacyAppError`** (`privacyguard/utils/exceptions.py`):
   ```python
   class PrivacyAppError(Exception):
       def __init__(self, message, suggestion=None):
           super().__init__(message)
           self.suggestion = suggestion
       def user_message(self):
           msg = str(self)
           if self.suggestion:
               msg += f"\n\n建议：{self.suggestion}"
           return msg

   class ConversionError(PrivacyAppError): pass
   class FileFormatError(PrivacyAppError): pass
   class SecurityError(PrivacyAppError): pass
   class MemoryLimitError(PrivacyAppError): pass
   class WorkerCancelledError(PrivacyAppError): pass
   ```
   Always raise these instead of bare `Exception` when the failure is user-actionable. The `suggestion` keyword feeds `user_message()` for UI display.

2. **Tuple-return validators.** `validate_safe_path` returns `(is_safe: bool, error_msg: Optional[str])` rather than raising; callers (e.g. `privacyguard/utils/doc_converter.py:63-67`) decide whether to raise `ConversionError`/`SecurityError`.

3. **Workers fail soft via `error_signal`.** Long-running `QThread` workers (`OCRWorker`, `ImageMergeWorker`) emit `error_signal.emit(str(msg)` instead of raising — see `privacyguard/workers/ocr_worker.py:463-473` and `privacyguard/workers/image_merge.py:49-60`. The signal is connected to the UI; the thread always exits cleanly via `finally:` cleanup.

4. **Catch-and-log with concrete exception types** for cleanup paths (preferred over bare `except Exception`):
   ```python
   # privacyguard/utils/temp_manager.py:113-126
   except (OSError, IOError) as e:
       errors.append(f"清理文件失败 {f}: {e}")
   ```
   Broad `except Exception` is reserved for genuinely fatal fallback paths (`TempFileManager.__del__` and `TempFileManager._cleanup_all`) where suppressing the failure is intentional.

5. **DOC conversion chains `ConversionError` explicitly.** `convert_doc_to_docx` (`privacyguard/utils/doc_converter.py:174-183`) catches `(OSError, IOError, RuntimeError, ValueError, ConversionError)` per backend and finally raises a single `ConversionError` summarising both LibreOffice and antiword failures.

6. **OCR helper swallows `re.error` silently.** Shared helpers like `compile_active_patterns` and `iter_unique_text_matches` skip invalid regex (`re.error`) with `continue` rather than raising — invalid rules must not break the whole scan.

## Logging

**Framework:** Plain `print()` — there is no `logging` module configured anywhere in `privacyguard/` or `tests/`.

**Patterns:**
- Bracket-prefixed tags make logs greppable:
  ```python
  print(f"[OCRWorker] 初始化, seal_detection_enabled={seal_detection_enabled}")
  print(f"[OCR] 使用引擎: {ocr_engine.name}")
  print(f"[Seal Detection] 页面 {i} 检测到 {len(seal_rects)} 个印章")
  print(f"[OCR ERROR] {error_msg}")
  print(f"[ConfigManager] 保存配置文件失败: {e}")
  ```
  Tags seen: `[OCR]`, `[OCR ERROR]`, `[OCRWorker]`, `[Seal Detection]`, `[WARN]`, `[DEBUG]`, `[ConfigManager]`, `[OCR WARN]`.

- Errors log `{type(e).__name__}: {e}` so the class name is preserved:
  ```python
  print(f"[OCR WARN] 裁剪图片区域失败: {type(exc).__name__}: {exc}")
  print(f"[Seal Detection] 页面 {i} 检测失败: {type(e).__name__}: {e}")
  ```

- When emitting worker errors, include the original exception class name in the string passed to `error_signal.emit(...)` so the UI can render actionable copy.

## Comments

**When to Comment:**
- Module docstrings summarise purpose and reference the version that introduced the module:
  ```python
  """
  安全验证工具

  v36.5: 模块化拆分，从 main.py 提取
  v37.7.3: 修复 f-string 中的反斜杠语法错误
  """
  ```
- Inline `# v3X.Y: ...` markers are used to attach rationale to individual lines (e.g. `# v37.7.3: 修复 f-string 中不能使用反斜杠的语法错误`).
- Block comments inside functions explain non-obvious decisions (e.g. the CJK weighting rationale in `privacyguard/workers/ocr_worker.py:303-312`).

**JSDoc/TSDoc:**
- Python uses PEP 257 docstrings (triple-quoted) — not type annotations on docstrings.
- Public functions and classes carry `Args:` / `Returns:` / `Raises:` sections in `privacyguard/utils/security.py`, `privacyguard/utils/doc_converter.py`, `privacyguard/ocr/base.py`, `privacyguard/utils/config.py`. Follow the same format for new shared helpers.

## Function Design

**Size:** Shared helpers in `privacyguard/ocr/` and `privacyguard/utils/` are kept small (<120 lines each). `privacyguard/workers/ocr_worker.py` is the deliberate exception (474 lines) because the OCR pipeline needs to be in one file for PyInstaller — split it only if a true boundary appears.

**Parameters:**
- Prefer passing collaborators (recogniser, callback, page) explicitly when the function is shared/tested. Example from `privacyguard/ocr/mixed_pdf.py:76-87`:
  ```python
  def collect_image_block_ocr_hits(
      page, patterns, scan_scale,
      recognize_fn, calculate_rect_fn, clip_to_page_rect_fn,
      preprocess_fn=None, page_dict=None,
      render_clip_fn=None, image_clip_rects=None,
  ):
  ```
  This lets `tests/unit/test_mixed_pdf_ocr.py:69-78` inject fakes without monkey-patching.

**Return Values:**
- Validators return `(bool, str|None)` tuples.
- Pure helpers (`collect_text_pdf_hit_boxes`, `collect_embedded_image_clip_rects`) return lists of tuples `(x0, y0, x1, y1)`.
- Functions that may fail return `None` (e.g. `calculate_sub_rect` returns `None` on division errors).
- Workers return values through signals only — never through a method return.

## Module Design

**Exports:**
- Each subpackage has a `__init__.py` that re-exports the public surface (`from privacyguard.utils import (...)`).
- Heavy modules use lazy re-exports (`__getattr__`) when the dependency is optional (RapidOCR-based engines, OCR/Image/Word workers).

**Barrel Files:**
- `privacyguard/__init__.py`, `privacyguard/utils/__init__.py`, `privacyguard/ocr/__init__.py`, and `privacyguard/workers/__init__.py` are the official barrels.
- Do **not** create additional barrels inside `privacyguard/core/` or `privacyguard/ui/` — those directories are reserved for future work and are currently empty (`core/__init__.py`, `ui/__init__.py` are both empty placeholders).

**Module placement rules (canonical targets):**
- Path validators, temp managers, custom exceptions, doc-conversion utilities, and config helpers belong in `privacyguard/utils/`.
- OCR helpers (text PDF, mixed PDF, base/rapidocr/manager) belong in `privacyguard/ocr/`.
- Long-running `QThread` workers belong in `privacyguard/workers/`.
- `main.py` is allowed to keep high-level orchestration and PyQt wiring, but **shared logic must move to `privacyguard/*` modules** to avoid the v37.7.6 "duplicate implementation" regression. Tests in `tests/unit/test_convergence.py` enforce this.

## Threading & Concurrency

- `QThread` subclasses declare signals at class level (`finished_signal = pyqtSignal(dict)`). Always suffix with `_signal` and never shadow PyQt's reserved `finished` / `progress` names.
- Cooperative cancellation via `self.isInterruptionRequested()` at loop start, never via thread termination primitives (`privacyguard/workers/ocr_worker.py:376-383, 456-457`).
- Backpressure: emit progress no faster than `PROGRESS_UPDATE_INTERVAL` seconds (default `0.05` — see `privacyguard/workers/ocr_worker.py:32`, `privacyguard/workers/word_worker.py:13`).

## Type Hints

- `privacyguard/ocr/base.py` and `privacyguard/ocr/manager.py` use full hints (`def recognize(self, image: np.ndarray) -> List[OCRResult]:`).
- `privacyguard/utils/config.py` uses hints for public APIs (`def get(self, path: Optional[str] = None, default: Any = None) -> Any:`).
- `privacyguard/workers/*.py` and `main.py` deliberately omit hints on Qt-style callbacks to avoid forward-reference noise. Follow the pattern: hints where the file is primarily a shared library, no hints where the file is a PyQt glue layer.

---

*Convention analysis: 2026-08-10*
