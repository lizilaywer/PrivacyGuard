# Testing Patterns

**Analysis Date:** 2026-08-10

## Test Framework

**Runner:**
- Standard-library `unittest` — discovered and run via `python3 -m unittest`. There is no `pytest`, `pytest.ini`, or `tox.ini` in the repo.
- No `setup.cfg` or `pyproject.toml` test config — config is the test class layout itself plus `tests/unit/` as the canonical home for unittest TestCases.

**Assertion Library:**
- `unittest.TestCase` built-ins only. No `assert` rewriting, no `pytest.mark.parametrize`, no Hamcrest.
- Common assertions in this codebase: `self.assertEqual`, `self.assertTrue`, `self.assertFalse`, `self.assertIn`, `self.assertNotIn`, `self.assertNotRegex`, `self.assertIs`, `self.assertIsNotNone`, `self.assertIsNone`, `self.assertGreater`, `self.assertEqual(..., msg)` with an explanatory message string.

**Run Commands:**
```bash
# Run the full baseline (79/79) explicitly enumerated in CLAUDE.md
python3 -m unittest \
  tests.unit.test_mixed_pdf_ocr \
  tests.test_path_validation \
  tests.unit.test_ocr_api \
  tests.unit.test_package_imports \
  tests.unit.test_pdf_text_hit_dedup \
  tests.unit.test_app_config \
  tests.unit.test_word_replace_rules \
  tests.unit.test_batch_word_replace \
  tests.unit.test_config_alignment \
  tests.unit.test_fstring_safety \
  tests.unit.test_convergence \
  -v

# Run a single class
python3 -m unittest tests.unit.test_mixed_pdf_ocr -v

# Run a single method
python3 -m unittest tests.unit.test_mixed_pdf_ocr.TestMixedPdfOcr.test_collect_embedded_image_clip_rects_filters_duplicates_and_tiny_blocks -v

# Compile-check the project before testing
python3 -m compileall -q main.py privacyguard tests

# Lightweight CI sequence (compile + tests + smoke launch)
python3 -m compileall -q main.py privacyguard tests \
  && python3 -m unittest \
      tests.unit.test_mixed_pdf_ocr \
      tests.test_path_validation \
      tests.unit.test_ocr_api \
      tests.unit.test_package_imports \
      tests.unit.test_pdf_text_hit_dedup \
      tests.unit.test_app_config \
      tests.unit.test_word_replace_rules \
      tests.unit.test_batch_word_replace \
      tests.unit.test_config_alignment \
      tests.unit.test_fstring_safety \
      tests.unit.test_convergence \
      -v \
  && python3 main.py
```

## Test File Organization

**Location:**
- Unit tests: `tests/unit/test_<subject>.py` — must be discoverable as `tests.unit.test_<subject>`.
- Integration scripts (PyQt-touching / scroll-fix checks): `tests/integration/verify_*.py` — these are *script-style*, not `unittest.TestCase` subclasses.
- End-to-end helpers (PDF sample generators): `tests/e2e/create_test_pdf.py`.
- Legacy word-processor tests: `tests/scripts/test_word_processor.py` (kept for reference, not part of the baseline).
- Cross-cutting test that needs `sys.path.insert`: `tests/test_path_validation.py` at the `tests/` root.

**Naming:**
- Module: `test_<subject>.py`. Subjects observed: `test_mixed_pdf_ocr`, `test_ocr_api`, `test_package_imports`, `test_pdf_text_hit_dedup`, `test_app_config`, `test_word_replace_rules`, `test_batch_word_replace`, `test_config_alignment`, `test_fstring_safety`, `test_convergence`, `test_path_validation`, `test_stability` (legacy).
- Class: `Test<Subject>` (e.g. `TestMixedPdfOcr`, `TestWordReplaceRules`, `TestConfigAlignment`, `TestPrivacyGuardImports`, `TestVersionSource`).
- Method: `test_<expectation>_<condition>` (e.g. `test_collect_embedded_image_clip_rects_filters_duplicates_and_tiny_blocks`, `test_word_panel_update_script_targets_only_word_blocks`, `test_main_py_version_fallback_matches_current`).

**Structure:**
```
tests/
├── test_path_validation.py          # top-level unittest, sys.path-bootstraps repo root
├── e2e/
│   └── create_test_pdf.py           # reportlab fixture generator
├── integration/
│   ├── verify_scroll_fix.py         # AST-style assertion script
│   └── verify_word_format.py        # python-docx format-preservation script
├── scripts/
│   └── test_word_processor.py       # legacy unittest WordWorker tests
├── unit/
│   ├── test_app_config.py
│   ├── test_batch_word_replace.py
│   ├── test_config_alignment.py
│   ├── test_convergence.py
│   ├── test_fstring_safety.py
│   ├── test_mixed_pdf_ocr.py
│   ├── test_ocr_api.py
│   ├── test_package_imports.py
│   ├── test_pdf_text_hit_dedup.py
│   ├── test_stability.py            # legacy print-style runner
│   └── test_word_replace_rules.py
├── samples/                         # fixture PDFs/DOCXs shared by hand/manual runs
└── reports/                         # historical test logs (TEST_RESULTS.md etc.)
```

## Test Structure

**Suite Organization:**

```python
# tests/unit/test_mixed_pdf_ocr.py
import unittest
from types import SimpleNamespace

from privacyguard.ocr.mixed_pdf import (
    collect_embedded_image_clip_rects,
    collect_image_block_ocr_hits,
)


class FakeRect:
    """Minimal PyMuPDF Rect replacement used only by these tests."""
    def __init__(self, x, y, width, height):
        self._x, self._y, self._width, self._height = x, y, width, height
    def x(self): return self._x
    def y(self): return self._y
    def width(self): return self._width
    def height(self): return self._height


class TestMixedPdfOcr(unittest.TestCase):

    def test_collect_embedded_image_clip_rects_filters_duplicates_and_tiny_blocks(self):
        page_dict = {"blocks": [
            {"type": 0, "bbox": (0, 0, 100, 20)},
            {"type": 1, "bbox": (10, 20, 210, 120)},
            {"type": 1, "bbox": (10, 20, 210, 120)},  # duplicate
            {"type": 1, "bbox": (0, 0, 5, 5)},        # tiny
        ]}
        clip_rects = collect_embedded_image_clip_rects(page_dict)
        self.assertEqual(clip_rects, [(10.0, 20.0, 210.0, 120.0)])

    def test_collect_image_block_ocr_hits_offsets_rects_back_to_page_coordinates(self):
        # …inject recogniser/clip-renderer fakes via kwargs…
        self.assertEqual(hit_rects, [(112.0, 208.0, 40.0, 14.0)])


if __name__ == "__main__":
    unittest.main()
```

**Patterns:**
- Every unit-test module ends with the `if __name__ == "__main__": unittest.main()` guard so the file is runnable on its own (e.g. `python3 tests/unit/test_mixed_pdf_ocr.py`).
- Each `assertEqual`/`assertIn` carries a Chinese failure message that explains the *intent* of the assertion, e.g.:
  ```python
  self.assertEqual(fallback, version_txt,
      f"版本回退值 {fallback} 应与 version.txt {version_txt} 一致")
  self.assertIn("from privacyguard.workers.image_merge import ImageMergeWorker",
                source, "main.py 应从共享模块导入 ImageMergeWorker")
  ```
  Keep this style: failure messages should describe *what invariant broke*, not the literal diff.

## Mocking

**Framework:** `unittest.mock.patch` and `types.SimpleNamespace`. No `pytest-mock`, no `unittest.mock.MagicMock` for full objects — preferring `SimpleNamespace` keeps tests data-driven.

**Patterns:**

- **Patch at the import path**, not at the use site:
  ```python
  # tests/test_path_validation.py:18
  with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
      ok, msg = validate_safe_path(r"C:\Users\Admin\test.docx", [".doc", ".docx"])
  ```
  ```python
  # tests/unit/test_app_config.py:19
  with patch("main.Path.read_text", side_effect=OSError):
      self.assertEqual(read_app_version(), "37.7.6")
  ```

- **Parametric cases via `with self.subTest(...)`** when iterating over a list of failure inputs:
  ```python
  # tests/test_path_validation.py:30-33
  for bad in [";", "|", "&", "$", "`", ">", "<"]:
      with self.subTest(bad=bad):
          ok, _ = validate_safe_path(f"C:\\test{bad}x.doc", [".doc"])
          self.assertFalse(ok)
  ```

- **Inject callbacks** when the production code accepts them as parameters (preferred over monkey-patching globals). Example from `tests/unit/test_mixed_pdf_ocr.py:69-78`:
  ```python
  hit_rects = collect_image_block_ocr_hits(
      page,
      [r"1[3-9]\d{9}"],
      scan_scale=2.0,
      recognize_fn=recognize,
      calculate_rect_fn=calculate_rect,
      clip_to_page_rect_fn=offset_rect,
      render_clip_fn=render_clip,
      image_clip_rects=image_clip_rects,
  )
  ```

- **Guarded import blocking** for lazy-loading regression tests:
  ```python
  # tests/unit/test_package_imports.py:23-30
  def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
      if name.startswith("rapidocr_onnxruntime"):
          raise ImportError("blocked for import smoke test")
      return original_import(name, globals, locals, fromlist, level)

  with patch("builtins.__import__", side_effect=guarded_import):
      module = importlib.import_module("privacyguard")
  ```

- **AST-level assertions for "no duplicate implementation" tests**. `tests/unit/test_convergence.py` reads `main.py` as text and uses `ast.parse()` to inspect class definitions:
  ```python
  # tests/unit/test_convergence.py:45-62
  tree = ast.parse(source)
  for node in ast.walk(tree):
      if isinstance(node, ast.ClassDef) and node.name == "WordWorker":
          method_names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
          self.assertIn("__init__", method_names, "WordWorker 兼容层应有 __init__")
          self.assertNotIn("run", method_names,
                           "WordWorker 兼容层不应包含 run 方法")
          self.assertNotIn("_find_matches", method_names, …)
  ```

**What to Mock:**
- External dependencies: `platform.system`, `Path.read_text`, `builtins.__import__`, RapidOCR runtime.
- Callback collaborators passed by parameter (recognise/clip/calculate functions).
- File paths and temp directories (`tempfile.mkstemp`, `tempfile.TemporaryDirectory`).

**What NOT to Mock:**
- The shared privacyguard module under test — import the real one. Tests in `tests/unit/test_convergence.py:75-84` *verify* that the shared module exports its public API by importing it for real.
- The QApplication event loop or any PyQt widget — the project has no QApplication-driven unit tests; UI verification is done by manually running `python3 main.py` (see the smoke command in CLAUDE.md).

## Fixtures and Factories

**Test Data:**
- Inline dictionaries for tiny page dicts (e.g. `page_dict = {"blocks": [{"type": 1, "bbox": (10, 20, 210, 120)}]}` in `tests/unit/test_mixed_pdf_ocr.py:33-40`).
- Inline `SimpleNamespace` objects for fakes — `SimpleNamespace(x0=1, y0=2, width=3, height=4)` replaces PyMuPDF hit rects (`tests/unit/test_pdf_text_hit_dedup.py:27-32`).
- Custom `FakeRect` / `FakePage` classes are defined at module scope and reused across tests in the same file:
  ```python
  # tests/unit/test_pdf_text_hit_dedup.py:7-18
  class FakePage:
      def __init__(self, text, hits_by_text):
          self._text = text
          self._hits_by_text = hits_by_text
          self.search_calls = []

      def get_text(self):
          return self._text

      def search_for(self, text):
          self.search_calls.append(text)
          return self._hits_by_text.get(text, [])
  ```

- Stub `MainWindow` for WordWorker tests — use `SimpleNamespace` + `MethodType` to bind real methods onto a stub so private HTML builders are testable without spinning up PyQt:
  ```python
  # tests/unit/test_word_replace_rules.py:32-54
  def build_word_preview_stub():
      stub = SimpleNamespace(
          word_data={"paragraph_0": {"text": "甲方 张三", "manual": [], "ocr": []}},
          word_replace_rules=[{"enabled": True, "mode": "exact",
                               "find": "张三", "replace": "[姓名]"}],
          replacement_text="[已脱敏]",
          _word_base_html="<p>甲方 张三</p>",
      )
      stub._wrap_html_document = MethodType(MainWindow._wrap_html_document, stub)
      stub._build_word_text_blocks = MethodType(MainWindow._build_word_text_blocks, stub)
      # …
      return stub
  ```

- `tempfile.TemporaryDirectory()` and `tempfile.mkstemp(suffix=".json")` for filesystem-scoped tests, always cleaned up explicitly with `try/finally: os.remove(temp_path)` (see `tests/unit/test_app_config.py:23-40, 63-82` and `tests/unit/test_batch_word_replace.py:13-27`).

**Location:**
- Fixtures live **inside the test file** that uses them — there is no `tests/fixtures/` directory or `conftest.py`.
- Larger binary fixtures (real DOCX/PDF) live in `tests/samples/` and are referenced by hand/manual integration runs (e.g. `tests/samples/test_sample.pdf`, `tests/samples/test_word.docx`).

## Coverage

**Requirements:** Not enforced. There is no `.coveragerc`, no `coverage` configuration, and no CI threshold.

**View Coverage:**
- The project does not run coverage locally. The default verification path is just `python3 -m unittest …` (see CLAUDE.md).

## Test Types

**Unit Tests:**
- Scope: a single shared helper from `privacyguard/ocr/*`, `privacyguard/utils/*`, or a specific free function in `main.py`.
- Examples: `tests/unit/test_mixed_pdf_ocr.py`, `tests/unit/test_pdf_text_hit_dedup.py`, `tests/unit/test_batch_word_replace.py`, `tests/unit/test_word_replace_rules.py`.
- All unit tests must avoid importing PyQt widgets — `unittest` only.

**Integration Tests:**
- Scope: AST/source-level invariants of `main.py`, cross-module configuration alignment, and end-to-end Word replacement.
- Examples:
  - `tests/unit/test_convergence.py` — reads `main.py` text and asserts shared-module re-exports.
  - `tests/unit/test_config_alignment.py` — asserts `config.json` ↔ `DEFAULT_CONFIG` drift is impossible.
  - `tests/unit/test_app_config.py` — round-trips `SimpleConfig` and `ConfigManager` through real disk JSON files.
  - `tests/integration/verify_scroll_fix.py`, `tests/integration/verify_word_format.py` — script-style manual-runs (not unittest).

**E2E Tests:**
- Scope: none in the strict sense. The closest analogue is `tests/e2e/create_test_pdf.py` (a `reportlab`-driven generator used for manual UI smoke tests).
- The "real" end-to-end check is the manual launch `python3 main.py` after a passing baseline (see CLAUDE.md "轻量快速验证" snippet).

## Common Patterns

**Async Testing:**
- N/A. All code paths are synchronous w.r.t. the test runner — `QThread` workers are exercised indirectly through their underlying helpers (`collect_image_block_ocr_hits`, `_build_word_text_blocks`, `_apply_rules_to_document`), not by spinning up Qt.

**Error Testing:**
- Use the actual exception class (from `privacyguard.utils.exceptions`) when raising is expected, and `with self.assertRaises(SomeError): …`. For "did NOT raise / NOT in source" checks, prefer `assertNotIn`/`assertNotRegex` on the file content (as in `tests/test_path_validation.py:71-72` and `tests/unit/test_convergence.py:25-33, 96-97`).
- Skip tests cleanly when an optional dependency is missing:
  ```python
  # tests/unit/test_ocr_api.py:8-12
  def test_import_and_init(self):
      try:
          from rapidocr_onnxruntime import RapidOCR
      except ImportError:
          self.skipTest("rapidocr_onnxruntime 未安装")
      …
  ```

**Regression markers in names:**
- Tests added as part of a checkpoint (cp18, cp20, cp23, cp27, cp30, etc. — see `rollback_journal.md`) are referenced from `docs/current/PRIORITY_REMEDIATION_PLAN.md` and `CHANGELOG.md`. New regression tests should carry an explanatory docstring tying them to the checkpoint:
  ```python
  """
  v37.7.6: 重复实现收敛回归测试

  验证 main.py 中的 Worker 和工具函数正确委托给共享模块，
  不再保留独立的重复实现。
  """
  ```

## Test Discovery & Directory Notes

- `tests/unit/` is the canonical directory for baseline tests. New regression tests should be added here with a `test_<subject>.py` filename and pulled into the explicit list in `CLAUDE.md` under "主回归测试（基线 79/79）" — the baseline is an enumerated list, not auto-discovery.
- `tests/scripts/`, `tests/integration/`, and `tests/e2e/` are *not* part of the baseline; they exist for manual or historical reasons. Avoid adding required checks there unless they cannot live under `tests/unit/`.
- `tests/reports/` contains historical `TEST_*.md` files (test logs from older versions). They are read-only references — do not write new test results there; rely on stdout from `python3 -m unittest -v`.

## Adding a New Test (Cheat Sheet)

1. Create `tests/unit/test_<subject>.py`.
2. Use `import unittest`, define `class Test<Subject>(unittest.TestCase)`, end the file with `if __name__ == "__main__": unittest.main()`.
3. Inject collaborators via parameters when the production code accepts them; otherwise patch at the import path.
4. Use `SimpleNamespace` for lightweight fakes; only escalate to a full class (`FakePage`, `FakeRect`) when the production code calls multiple methods on the dependency.
5. For filesystem tests, prefer `tempfile.TemporaryDirectory()` or `tempfile.mkstemp()` + explicit `try/finally: os.remove(...)`.
6. Add an explanatory failure message to every `assertEqual/assertIn/assertNotIn`.
7. Update the `python3 -m unittest …` baseline command in `CLAUDE.md` (and any related `docs/current/PRIORITY_REMEDIATION_PLAN.md` entries) so the new test runs in the canonical sequence.

---

*Testing analysis: 2026-08-10*
