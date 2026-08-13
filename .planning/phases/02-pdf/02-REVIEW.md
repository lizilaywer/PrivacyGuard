---
phase: 02-pdf
reviewed: 2026-08-11T14:55:00Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - config.json
  - config.json.template
  - main.py
  - packaging/macos/config/PrivacyGuard.spec
  - packaging/macos/scripts/build_complete.sh
  - packaging/windows/config/PrivacyGuard_windows.spec
  - privacyguard/__init__.py
  - privacyguard/pii/__init__.py
  - privacyguard/pii/data/bin_prefixes.json
  - privacyguard/pii/data/bin_prefixes.json.LICENSE
  - privacyguard/pii/data/rules.json
  - privacyguard/pii/engine.py
  - privacyguard/pii/mask.py
  - privacyguard/pii/overlap.py
  - privacyguard/pii/pdf_adapter.py
  - privacyguard/pii/regex_patterns.py
  - privacyguard/pii/validators/__init__.py
  - privacyguard/pii/validators/bank_account.py
  - privacyguard/pii/validators/bank_card.py
  - privacyguard/pii/validators/email.py
  - privacyguard/pii/validators/taxpayer_id.py
  - privacyguard/pii/validators/uscc.py
  - privacyguard/pii/validators/vat_invoice.py
  - tests/fixtures/fake_pii.py
  - tests/unit/test_app_config.py
  - tests/unit/test_convergence.py
  - tests/unit/test_package_imports.py
  - tests/unit/test_pdf_metadata_cleared.py
  - tests/unit/test_pdf_pii_redaction.py
  - tests/unit/test_pii_engine.py
  - tests/unit/test_pii_validators.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 02 (pdf): Code Review Report

**Reviewed:** 2026-08-11T14:55:00Z
**Depth:** standard
**Files Reviewed:** 34
**Status:** issues_found

## Summary

Phase 2 expands PrivacyGuard with 6 new PII entity types, partial mask writing, PDF metadata clearing, Settings UI 9-row table, toolbar mask_override toggle, and PyInstaller parity. The PII engine / validators / mask / pdf_adapter / overlap / regex_patterns modules are well-designed, defensive, and follow the v37.7.6 convergence principles internally. Tests pass (99/99 in the verified slice).

However, **`main.py::save_pdf` violates the v37.7.6 convergence discipline** by re-implementing the partial mask insert_text logic inline (lines 12685–12715) instead of delegating to the very function it imports (`privacyguard.pii.pdf_adapter.write_partial_masks`). This is the central architectural regression and must be fixed before ship.

Secondary concerns: the engine eagerly imports all 6 new validator submodules (weakens the lazy-loading spirit, though the strict contract is satisfied); the inline mask logic is feature-incomplete vs. `write_partial_masks` (no font-name match, no rect resize, no OCR font-size estimation); and the new "save_pdf routing" test re-implements the same inline logic instead of asserting that `write_partial_masks` is actually called.

## Critical Issues

### CR-01: `main.py::save_pdf` re-implements `write_partial_masks` inline — v37.7.6 收敛原则 violation

**File:** `main.py:12625-12715` (import at 12625; re-implementation at 12685-12715)
**Category:** convergence
**Issue:** `from privacyguard.pii.pdf_adapter import (write_partial_masks, clear_pdf_metadata)` is imported at line 12625-12628 but `write_partial_masks` is **never called anywhere in main.py**. Instead, the partial mask insert_text logic is duplicated inline (lines 12685-12715):
- Iterates `rects_for_partial`, picks items with `mode == "partial"`, looks up font size via `page.get_text("dict")` first non-"mask" span, computes `text_w` and `cx`/`cy`, calls `page.insert_text`.

CLAUDE.md constraint #3 (critical): *"v37.7.6 收敛原则：main.py 不得重新实现 PII detection / mask / metadata-clear 逻辑；必须只调用 privacyguard.pii.pdf_adapter.write_partial_masks + clear_pdf_metadata"*.

The D-22 single-pass refactor explanation (lines 12641-12648) is a legitimate constraint (`page.apply_redactions()` is one-shot per page), but the proper fix is to refactor `write_partial_masks` to accept a unified list of (item, mode) tuples (or accept QRectF + raw dict alongside PIIHit), **not** to inline the logic in main.py.

**Impact:** (1) Future changes to `write_partial_masks` (font matching, OCR font-size estimation, rect resize) will not reach production because main.py has its own copy. (2) The inline version is feature-incomplete vs. `write_partial_masks` (see WR-02). (3) The convergence test `test_convergence.py::test_main_py_uses_write_partial_masks_in_save_loop` only checks the **string** `"write_partial_masks"` is referenced — it does NOT verify the function is actually called, so this regression slipped through.

**Fix:**
- Refactor `privacyguard.pii.pdf_adapter.write_partial_masks` to accept mixed item types (PIIHit | tuple of (QRectF, mode)). Extend signature: `write_partial_masks(doc, page_idx, items: List[Union[PIIHit, Tuple[QRectF, str]]], ...)`.
- Replace main.py lines 12651-12715 (the OCR + manual + PII collection, add_redact_annot loop, apply_redactions, delete_annot, and partial mask insert_text) with a single call: `write_partial_masks(doc_save, i, all_pi_items)`.
- Tighten the convergence test to AST-verify that `write_partial_masks` is **called** (not just referenced) inside `save_pdf`.

## Warnings

### WR-01: `engine.py` eagerly imports all 6 new validator submodules

**File:** `privacyguard/pii/engine.py:32-48`
**Category:** lazy-loading
**Issue:** All 6 new validator submodules are eagerly imported at engine.py module top: `from privacyguard.pii.validators.uscc import validate_uscc`, `from privacyguard.pii.validators.bank_card import validate_bank_card`, `from privacyguard.pii.validators.email import ...`, `from privacyguard.pii.validators.vat_invoice import ...`, `from privacyguard.pii.validators.bank_account import ...`, `from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15`. Verified empirically: importing `privacyguard.pii.engine` triggers loading of all 6 modules into `sys.modules`.

The strict contract ("import privacyguard must not load PII validators") is satisfied, but the spirit of CLAUDE.md constraint #2 ("6 个新 validator 必须保持懒加载") is broken — there is no granular lazy access via the engine. `privacyguard.pii.validators.{uscc,bank_card,email,...}` are individually lazy via `__getattr__`, but the only practical access path (`PIIEngine`) loads them all.

**Impact:** Memory + import time penalty when PIIEngine is loaded (in production: triggered by OCR worker startup at `privacyguard/workers/ocr_worker.py:202`). All 6 new validators cannot be lazy-loaded independently.

**Fix:** Either (a) keep current behavior and document it (matches Phase 1 validator loading pattern), or (b) refactor engine.py to look up validators via `importlib.import_module` inside `_check_*` methods, allowing fine-grained lazy access.

### WR-02: Inline mask insert_text in main.py is feature-incomplete vs. `write_partial_masks`

**File:** `main.py:12693-12715`
**Category:** pymupdf
**Issue:** The inline implementation diverges from `privacyguard.pii.pdf_adapter.write_partial_masks` in 3 ways that affect production output:
1. **Font hardcoded as `"helv"`** — `pdf_adapter._resolve_font_for_rect` looks up the original span font via `_FONT_NAME_MAP` (Helvetica / Times-Roman / Courier mapped to helv/tiro/cour). The original Times or Courier face is lost in production output.
2. **No OCR fallback font-size** — Inline uses `font_size = 11.0` flat fallback. `pdf_adapter._resolve_font_for_rect` uses `max(float(hit.page_rect[3]) - 4.0, 6.0)` for OCR / placeholder rect paths. So OCR-sourced partial masks render at 11.0 instead of scaled-to-rect, often overflowing.
3. **No rect resize** — Inline inserts at the original rect center. `pdf_adapter._resize_rect_for_mask` widens the rect to `max(len(mask_text) * avg_w + 4.0, rect.width)` first, so mask text fits. Inline can overflow when mask text is wider than the original (e.g., 18-char USCC partial mask vs narrower original rect).

**Impact:** Production PDF masks look worse (wrong font, wrong size, can overflow rect). This regresses the Phase 2 MASK-01 deliverable for OCR-sourced and wide-mask cases.

**Fix:** Same fix as CR-01 — delegate to `write_partial_masks`. All three behaviors are already implemented in pdf_adapter.

### WR-03: `test_pdf_pii_redaction.py::test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata` does not test the routing

**File:** `tests/unit/test_pdf_pii_redaction.py:168-284`
**Category:** test
**Issue:** The test name and docstring claim to verify "MainWindow.save_pdf routes PII through write_partial_masks + clear_pdf_metadata", but the test body:
- Imports `write_partial_masks` (line 178) but never calls it
- Manually re-implements the partial mask insert_text logic at lines 240-258 (mirror of the main.py inline code)
- Asserts only reverse-extraction results

This means the test passes as long as the inline logic is correct, regardless of whether `write_partial_masks` is actually called in production. The CR-01 regression is not caught by this test.

**Impact:** Future divergence between main.py and pdf_adapter will not be caught by this test.

**Fix:** Either (a) replace the test body with an actual call to `write_partial_masks(doc_save, 0, [pii_hit], mode="partial")` to verify the production helper works end-to-end, or (b) split into two tests — one for `write_partial_masks` routing, one for `clear_pdf_metadata` — and use Qt test harness for MainWindow.save_pdf invocation.

### WR-04: `has_bank_account_context` only checks the first occurrence

**File:** `privacyguard/pii/validators/bank_account.py:43-62`
**Category:** bug
**Issue:** `idx = text.find(target)` returns the first occurrence index. If a document contains two account candidates (e.g., "账号 123456789012345 备注 random 987654321098765"), the engine yields the first (123456789012345), but `has_bank_account_context` only inspects the ±20 window around the first match. The second candidate is rejected (no context in its window) but is never re-checked against the second occurrence's context.

In practice the regex `\d{9,21}` matches the longest contiguous run first, so multi-occurrence is uncommon. But the test coverage does not exercise this case.

**Impact:** Edge case for documents with multiple bare accounts. Not exercised by current tests.

**Fix:** Iterate all `text.find(target, start)` positions and return True if any has context. Or document this as a known limitation.

## Info

### IN-01: `_TAXPAYER_15_ADMIN_PREFIX` duplicates `_VALID_ADMIN_PREFIX_2` from id_card validator

**File:** `privacyguard/pii/validators/taxpayer_id.py:14-22`
**Category:** style
**Issue:** `_TAXPAYER_15_ADMIN_PREFIX` (34 entries) is identical to `_VALID_ADMIN_PREFIX_2` in `id_card.py`. Same for `_VALID_PROVINCE_PREFIX` in `tests/fixtures/fake_pii.py:13-21`. Three copies of the same data.

**Impact:** If the admin prefix list changes (e.g., new行政区划 in future), three files need to be updated in sync.

**Fix:** Move the prefix set to a shared constant in `privacyguard/pii/data/` or in `privacyguard/pii/validators/__init__.py`. Have `id_card`, `taxpayer_id`, and `fake_pii` import it.

### IN-02: `bin_prefixes.json._count_target` says 10,000-15,000 but file has 19,890 entries

**File:** `privacyguard/pii/data/bin_prefixes.json`
**Category:** comment
**Issue:** Metadata field `_count_target: "10,000-15,000"` is stale — actual count is 19,890 (verified valid: 6-char, all digits, all unique).

**Impact:** Documentation drift only.

**Fix:** Update `_count_target` to `"~20,000"` or remove the field.

### IN-03: `email.py` validator is case-sensitive on regex but `is_public_suffix_email` lowercases TLD

**File:** `privacyguard/pii/validators/email.py:21-23, 38-49`
**Category:** style
**Issue:** `EMAIL_RE` matches mixed case (`[A-Za-z]`), but the regex is not flagged `re.IGNORECASE`. `is_public_suffix_email` then calls `domain.rsplit(".", 1)[-1].lower()` to lowercase the TLD. Inconsistent: local part can be mixed case, but TLD match is case-insensitive. This is correct behavior, but not documented.

**Impact:** Behavior is correct (RFC 5322 §2.4 says local part IS case-sensitive, domain IS case-insensitive). Documentation gap.

**Fix:** Add comment to `EMAIL_RE` and `is_public_suffix_email` explaining the case semantics (local case-sensitive, domain case-insensitive per RFC 5322).

---

_Reviewed: 2026-08-11T14:55:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_