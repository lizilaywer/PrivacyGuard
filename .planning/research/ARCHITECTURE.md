# Architecture — PII Engine + Format Handlers Integration

**Milestone:** PrivacyGuard v38.x — pure-local Chinese PII recognition + Excel/Image redaction
**Researched:** 2026-08-10
**Confidence:** HIGH (existing codebase well-mapped via `.planning/codebase/`); MEDIUM (Presidio architectural pattern is the reference, but we re-implement, not depend on it)
**Scope:** Architectural integration of a pluggable PII detection engine and three new format handlers (Excel, image, plus extending PDF/Word) into the existing PyQt6 monolith + `privacyguard/` shared package. Pure architecture — library choices are in `STACK.md`; feature scope is in `FEATURES.md`.

---

## 1. Architectural Goals (in priority order)

1. **Detection is format-independent.** A `PIIHit` produced by a PDF text-layer recognizer is structurally identical to one produced by an OCR recognizer, an Excel cell recognizer, or an image-file recognizer. The UI / masking layer never branches on format — only on `entity_type` + `confidence`.
2. **The detection engine is a library, not a worker.** It does not own Qt, threads, or signals. It is a pure-Python module that any worker (PDF/Word/Excel/Image/Batch) can call.
3. **New shared logic goes into `privacyguard/`.** The v37.7.6 convergence explicitly forbids re-implementing in `main.py`. Every component in this design lives under `privacyguard/pii/` (new) or extends an existing `privacyguard/ocr/` / `privacyguard/workers/` module.
4. **Lazy-loading contract is preserved.** `RapidOCR` stays lazy; the new image-file OCR wrapper inherits this. Dictionary JSON loads at module import (cheap, no native code); regex `re.compile` at module level (cheap).
5. **Existing hit dicts are extended, not replaced.** `page_data[page] = {"ocr": [...], "manual": [...]}` and `word_data[key] = {"text": ..., "ocr": [...], "manual": [...]}` gain a third slot `"pii": [...]` carrying `PIIHit[]`. Existing `ocr`/`manual` slots stay (they are not lost; they coexist). New code never reads through `ocr`/`manual` only — the `pii` slot is the canonical detection surface.
6. **Two-step Mark → Apply, like Acrobat / Presidio.** Detection produces `PIIHit[]` (the "mark" output). Applying redactions is a separate phase. The UI lets the user review between them, and the JSON `RedactionReport` records what was applied.

---

## 2. System Map (post-integration)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                      PyQt6 Desktop Runtime (QApplication)                     │
│                         `main.py`  (~12.6k LOC, monolithic)                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                   │
│  │  MainWindow    │  │  CandidateDlg  │  │  SinglePage    │                   │
│  │  (QMainWindow) │  │  (NEW — review │  │  Canvas        │                   │
│  │  L4885         │  │   queue panel) │  │  L4002         │                   │
│  │                │  │  (review queue │  │                │                   │
│  │                │  │   + per-hit    │  │                │                   │
│  │                │  │   override)    │  │                │                   │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘                   │
│           │                   │                   │                           │
│           ▼                   ▼                   ▼                           │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │            `privacyguard/`  (extended shared library)                 │    │
│  │                                                                       │    │
│  │   ┌───────────────────────────────────────────────────────────────┐   │    │
│  │   │  pii/   (NEW — pure-Python detection engine, no Qt coupling)  │   │    │
│  │   │  ├── types.py             PIIHit, DocumentLocation dataclasses│   │    │
│  │   │  ├── entities.py          Entity registry (CN_ID_CARD, ...)    │   │    │
│  │   │  ├── recognizers/         Pluggable recognizer ABC + impls    │   │    │
│  │   │  │   ├── base.py          Recognizer ABC, CandidateSpan        │   │    │
│  │   │  │   ├── regex.py         RegexRecognizer                      │   │    │
│  │   │  │   ├── checksum.py      ChecksumRecognizer (wraps validators)│   │    │
│  │   │  │   ├── dictionary.py     DictionaryRecognizer                 │   │    │
│  │   │  │   └── context.py       ContextAwareRecognizer (wraps any)   │   │    │
│  │   │  ├── validators/          In-house checksum algorithms         │   │    │
│  │   │  │   ├── id_card.py       GB 11643 MOD 11-2                    │   │    │
│  │   │  │   ├── bank_card.py     Luhn                                 │   │    │
│  │   │  │   └── uscc.py          GB 32100 MOD 31-3                    │   │    │
│  │   │  ├── dictionaries/        Static JSON (eager load ~260KB)      │   │    │
│  │   │  │   ├── surnames.json                                        │   │    │
│  │   │  │   ├── given_names.json                                      │   │    │
│  │   │  │   ├── admin_divisions.json                                  │   │    │
│  │   │  │   ├── org_keywords.json                                     │   │    │
│  │   │  │   └── context_anchors.json                                  │   │    │
│  │   │  ├── engine.py            Engine — orchestrates pipeline       │   │    │
│  │   │  ├── confidence.py        3-tier model (HIGH/MEDIUM/LOW)       │   │    │
│  │   │  ├── overlap.py           Span dedup + conflict resolution     │   │    │
│  │   │  ├── mask.py              Per-entity partial masking           │   │    │
│  │   │  └── report.py            PIIHit[] → JSON RedactionReport      │   │    │
│  │   └───────────────────────────────────────────────────────────────┘   │    │
│  │                                                                       │    │
│  │   ┌───────────────────────────────────────────────────────────────┐   │    │
│  │   │  formats/   (NEW — document adapter interface)                 │   │    │
│  │   │  ├── base.py              DocumentAdapter ABC                  │   │    │
│  │   │  │                        TextUnit, RedactionPlan dataclasses  │   │    │
│  │   │  ├── pdf_adapter.py       wraps text_pdf + mixed_pdf          │   │    │
│  │   │  ├── word_adapter.py      wraps word_worker helpers           │   │    │
│  │   │  ├── excel_adapter.py     NEW — openpyxl-based                │   │    │
│  │   │  └── image_adapter.py     NEW — Pillow + RapidOCR path        │   │    │
│  │   └───────────────────────────────────────────────────────────────┘   │    │
│  │                                                                       │    │
│  │   ┌─────────────────────────┐  ┌─────────────────────────────────┐    │    │
│  │   │ ocr/  (extended)        │  │ workers/  (extended)            │    │    │
│  │   │ base.py  manager.py     │  │ ocr_worker.py  word_worker.py    │    │    │
│  │   │ rapidocr.py             │  │ image_merge.py                  │    │    │
│  │   │ text_pdf.py (UNCHANGED) │  │ excel_worker.py  (NEW)          │    │    │
│  │   │ mixed_pdf.py (UNCHANGED)│  │ image_worker.py  (NEW)          │    │    │
│  │   │ image_ocr.py (NEW)      │  │ detection_worker.py (NEW)       │    │    │
│  │   └─────────────────────────┘  └─────────────────────────────────┘    │    │
│  │                                                                       │    │
│  │   ┌───────────────────────────────────────────────────────────────┐   │    │
│  │   │ utils/  (unchanged: exceptions, temp_manager, security, ...)  │   │    │
│  │   └───────────────────────────────────────────────────────────────┘   │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Reading the map:**
- The `pii/` subpackage is the new pure-Python brain. No Qt. No threading. No signals.
- The `formats/` subpackage is the new bridge layer between raw documents and the engine.
- Existing `ocr/`, `workers/`, `utils/` subpackages are extended in place; `ocr/text_pdf.py` and `ocr/mixed_pdf.py` are the untouched foundation for the PDF adapter.
- `main.py` adds thin wrappers and UI; it does not gain detection logic.

---

## 3. Component Boundaries

| Component | Responsibility | Talks To | File |
|---|---|---|---|
| `PIIHit` | Canonical detection record. Frozen dataclass. | n/a (data) | `privacyguard/pii/types.py` |
| `DocumentLocation` | Format-agnostic location pointer. Carries `doc_kind`, `page_index`, `data_key`, `sheet`, `cell`, `char_offset`, `rect` (page-pixels). | n/a (data) | `privacyguard/pii/types.py` |
| `EntityRegistry` | Declarative catalog of supported entity types. Defines regex, validator, dictionary, masking rule per entity. | `Recognizer`s | `privacyguard/pii/entities.py` |
| `Recognizer` (ABC) | Detects `CandidateSpan[]` from a single `TextUnit`. Pure function. | `Engine` | `privacyguard/pii/recognizers/base.py` |
| `RegexRecognizer` | Pattern-based detection. | `Engine` | `privacyguard/pii/recognizers/regex.py` |
| `ChecksumRecognizer` | Wraps `RegexRecognizer` and applies a validator (GB 11643 mod-11-2, Luhn, GB 32100 mod-31-3). Drops hits that fail checksum. | `Engine` | `privacyguard/pii/recognizers/checksum.py` |
| `DictionaryRecognizer` | Surname / admin-division / org-keyword matching with sliding-window scoring. | `Engine` | `privacyguard/pii/recognizers/dictionary.py` |
| `ContextAwareRecognizer` | Decorator over any `Recognizer` that scans a window around a candidate and bumps confidence based on context-anchor keywords. | `Engine` | `privacyguard/pii/recognizers/context.py` |
| `Engine` | Pipeline orchestrator. Runs registry of recognizers against `TextUnit`s, applies `overlap.py` dedup/conflict resolution, assigns confidence tier, computes `suggested_mask`. | `DocumentAdapter` (caller), `Recognizer`s | `privacyguard/pii/engine.py` |
| `overlap.py` | Span dedup (when two recognizers hit the same range); conflict resolution (prefer HIGH > MEDIUM > LOW; on equal tier, prefer more-specific entity). | `Engine` | `privacyguard/pii/overlap.py` |
| `mask.py` | `(entity_type, text, location) -> masked_text`. Per-type masking rules from §3 of `FEATURES.md`. | `Engine` (pre-compute `suggested_mask`), `DocumentAdapter` (apply) | `privacyguard/pii/mask.py` |
| `confidence.py` | Maps raw signals (checksum_passed, dictionary_match, context_match) to 3-tier bucket. | `Engine` | `privacyguard/pii/confidence.py` |
| `report.py` | `PIIHit[]` → JSON `RedactionReport` (file path, ruleset hash, per-entity counts, per-document timestamp). | `Engine`, `DetectionWorker` | `privacyguard/pii/report.py` |
| `DocumentAdapter` (ABC) | Format-specific bridge: `extract_text_units() -> Iterator[TextUnit]`, `apply_redactions(redactions, output_path)`. | `Engine` (consumes units), `main.py` (instantiates) | `privacyguard/formats/base.py` |
| `PdfAdapter` | Wraps existing `collect_text_pdf_hit_boxes` + `collect_image_block_ocr_hits`. Refactored to yield `TextUnit`s (not raw rects) and write redactions via PyMuPDF `add_redact_annot + apply_redactions` (no draw_rect). | `Engine` | `privacyguard/formats/pdf_adapter.py` |
| `WordAdapter` | Wraps existing `_ModularWordWorker` helpers. Yields `TextUnit`s keyed by `data-key`. Applies redactions via `python-docx` run-aware replacement (existing pattern at `main.py:951`). | `Engine` | `privacyguard/formats/word_adapter.py` |
| `ExcelAdapter` | NEW. `openpyxl` `iter_rows()` → `TextUnit`s keyed by sheet+cell. Applies redactions in-place via `cell.value = masked`, preserving formula/style/merge/conditional-format. Also scans hidden sheets, comments, defined names, doc properties. | `Engine` | `privacyguard/formats/excel_adapter.py` |
| `ImageAdapter` | NEW. Pillow Image → OCR → `TextUnit`s keyed by pixel rect. Applies redactions as Pillow burn-in rectangles. Runs **re-OCR verification** after burn-in to ensure no sensitive token survives. | `Engine`, `privacyguard/ocr/image_ocr.py` | `privacyguard/formats/image_adapter.py` |
| `image_ocr.py` | NEW. Wraps `RapidOCREngine.recognize()` for a Pillow Image (numpy conversion). RapidOCR import stays inside the function body (lazy). | `ImageAdapter` | `privacyguard/ocr/image_ocr.py` |
| `DetectionWorker` | NEW. `QThread` that drives `Engine` over a sequence of `TextUnit`s from a `DocumentAdapter`. Emits `hit_signal(unit_key, PIIHit[])`, `progress_signal(int)`, `finished_signal()`, `error_signal(str)`. Cancellation via `isInterruptionRequested()`. | `MainWindow` | `privacyguard/workers/detection_worker.py` |
| `ExcelWorker` | NEW. Specialised `DetectionWorker` for `.xlsx` (sheet-by-sheet chunked progress). | `MainWindow` | `privacyguard/workers/excel_worker.py` |
| `ImageWorker` | NEW. Specialised `DetectionWorker` for image files (Pillow load + RapidOCR + burn-in). | `MainWindow` | `privacyguard/workers/image_worker.py` |
| `CandidateDialog` | NEW. `QDialog` showing two-tier candidate list (HIGH auto-apply / MEDIUM+LOW review queue). Per-hit override, entity-type toggles, doc-level whitelist. | `MainWindow` | `main.py` (stays — UI is not migrating this milestone) |
| `RedactionReport` | JSON output. Per-document. Fields: file, ruleset_hash, hits[], applied[], errors[], timestamp. | `Engine` writes | emitted by `DetectionWorker.finished_signal` → `main.py` saves |

---

## 4. Data Flow

### 4.1 Canonical Detection Pipeline

```text
Document file
   │
   ▼
DocumentAdapter.extract_text_units(path)
   │  yields TextUnit(document_id, location, text)
   ▼
DetectionWorker.run()  [QThread]
   │
   │  for each unit:
   │     Engine.detect(unit)
   │        │
   │        │  registry = [ Regex, Checksum, Dictionary, ContextAware ] per entity
   │        │  for each Recognizer:
   │        │     recognizer.recognize(unit) -> CandidateSpan[]
   │        │        │
   │        │        ▼
   │        │     ChecksumRecognizer drops spans where validator fails
   │        ▼
   │     overlap.resolve(spans[]) -> deduped CandidateSpan[]
   │        │
   │        ▼
   │     confidence.assign(spans[]) -> PIIHit[] with tier
   │        │
   │        ▼
   │     mask.suggest(entity_type, span.text, location) -> suggested_mask
   │        │
   │        ▼
   │     emit hit_signal(unit_key, PIIHit[])
   ▼
MainWindow.page_data[page]["pii"] = [...]  (or word_data[key]["pii"] / excel_unit_map)
```

### 4.2 Apply Phase (separate from detection)

```text
MainWindow receives finished_signal (or user clicks "Apply")
   │
   ▼
DocumentAdapter.apply_redactions(path, [(location, mask)], output_path)
   │
   │  PDF  → fitz add_redact_annot + apply_redactions (text/images/graphics remove, garbage=4, deflate)
   │  Word → python-docx run-aware text replacement (existing main.py:951 pattern)
   │  Excel→ openpyxl cell.value = masked (formula/style preserved automatically)
   │  Image→ Pillow ImageDraw.rectangle black-fill, flatten, save
   ▼
Verification pass (mandatory):
   │  PDF  → re-extract text in redacted region; assert empty
   │  Excel→ re-load xlsx and assert cell.value contains no sensitive token
   │  Image→ re-OCR via image_ocr.py; assert no sensitive token reappears
   │  Word → re-scan via WordWorker; assert no hit
   ▼
RedactionReport.write_json(output_path + ".report.json")
```

### 4.3 Format → Adapter → Worker Mapping

| Format | Adapter | Worker | Detection invocation | Apply invocation |
|---|---|---|---|---|
| PDF (text) | `PdfAdapter.extract_text_units` calls `collect_text_pdf_hit_boxes` | `_ModularOCRWorker` extended to also call `Engine.detect(unit)` per page | inline in worker run() | `apply_redactions` → fitz `add_redact_annot + apply_redactions` |
| PDF (image-block) | `PdfAdapter.extract_text_units` calls `collect_image_block_ocr_hits` | same as above | inline in worker run() after OCR | same |
| Word (DOCX) | `WordAdapter.extract_text_units` iterates paragraphs+tables (key by `data-key`) | `_ModularWordWorker` extended | inline after DOCX load | run-aware replacement |
| Word (DOC) | pre-converted via `convert_doc_to_docx` (`privacyguard/utils/doc_converter.py:157`) | same as DOCX | same | same |
| Excel (XLSX) | `ExcelAdapter.extract_text_units` iterates `iter_rows()` for all sheets incl. hidden | `ExcelWorker` (new, sheet-by-sheet progress) | per-sheet batch | `cell.value = masked` |
| Image (JPG/PNG/BMP) | `ImageAdapter.extract_text_units` runs `image_ocr.py` per image | `ImageWorker` (new) | per-image | Pillow burn-in |

---

## 5. Detection Data Model (the unifying struct)

The keystone is `PIIHit`. It is the **only** structure the UI / masking layer ever consumes. Different recognizers and different formats produce it; the downstream pipeline does not care which produced it.

```python
# privacyguard/pii/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, Literal

class ConfidenceTier(str, Enum):
    HIGH = "HIGH"      # checksum passes + format matches (auto-apply)
    MEDIUM = "MEDIUM"  # format matches only (review queue)
    LOW = "LOW"        # context-only, name/address candidate (review queue)

class DocKind(str, Enum):
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    IMAGE = "image"

@dataclass(frozen=True)
class DocumentLocation:
    """Format-agnostic location pointer. One field per kind; the rest are None."""
    doc_kind: DocKind
    page_index: Optional[int] = None        # PDF
    data_key: Optional[str] = None          # Word (the block data-key from mammoth)
    sheet_name: Optional[str] = None        # Excel
    cell_coord: Optional[str] = None        # Excel ("A1", "B12", etc.)
    char_offset: int = 0                   # char offset within the unit text
    rect: Optional[Tuple[float, float, float, float]] = None  # page-pixels (PDF) or unit coords

@dataclass(frozen=True)
class PIIHit:
    entity_type: str                       # "CN_ID_CARD", "CN_PHONE", "CN_NAME", ...
    location: DocumentLocation
    text: str                              # original matched text
    confidence: ConfidenceTier
    source: Literal["regex", "checksum", "dictionary", "context"]
    validator_passed: bool                 # checksum / dictionary / context all matched?
    suggested_mask: str                    # pre-computed by mask.py per entity type
    normalized: Optional[str] = None       # for cross-document consistency (e.g. phone spacing removed)

@dataclass
class TextUnit:
    """One atomic piece of text produced by a DocumentAdapter."""
    unit_id: str                           # stable per-document-unique key
    text: str                              # the text itself
    location: DocumentLocation
    meta: dict = field(default_factory=dict)  # OCR confidence, page pixel rect, etc.
```

### 5.1 Reconciliation with existing hit structures

| Existing | New extension | Where it lives |
|---|---|---|
| `self.page_data[page] = {"ocr": [...], "manual": [...]}` | add `"pii": [PIIHit, ...]` | `main.py:4908` (unchanged shape; new key) |
| `self.word_data[key] = {"text": ..., "ocr": [...], "manual": [...]}` | add `"pii": [PIIHit, ...]` | `main.py:4915` (unchanged shape; new key) |
| (no existing Excel dict — NEW) | `self.excel_data[(sheet, cell)] = {"text": ..., "pii": [...]}` | added in `main.py` near existing state block at `main.py:4908-4926` |
| (no existing image dict — NEW) | `self.image_data[image_path] = {"ocr_text": ..., "pii": [...]}` | added in same block |

**Hard rule:** new code reads `pii` for both rendering and applying. The `ocr`/`manual` slots are kept only as legacy compatibility for the existing keyword/manual-rect flows. New auto-detection never writes into `ocr`/`manual`. This avoids the v37.7.6 drift pattern.

### 5.2 Why a `PIIHit` is not the same as the existing `OCRResult` / `Rect`

- `OCRResult` (`privacyguard/ocr/base.py:30`) is engine output: raw text + box + chars + confidence. It is **input to** detection, not the detection itself.
- `Rect` (used in `page_data[page]["ocr"]`) is a pixel rectangle. It carries no text and no entity semantics.
- `PIIHit` is the **interpreted** detection: text + entity + confidence tier + masked suggestion + location. The fact that it is a frozen dataclass with an enum tier makes it cheap to dedup, serialise to JSON, and reason about in tests.

### 5.3 Why a `DocumentLocation` does not leak the format

The dataclass has fields for every kind (`page_index`, `data_key`, `sheet_name`, `cell_coord`) but only the one matching `doc_kind` is populated. Downstream code branches on `doc_kind` only at the *apply* boundary (the adapter), never inside the engine. This is the same pattern Presidio uses (their `RecognizerResult` carries a per-format score, but the framework itself is format-agnostic).

---

## 6. Location Addressing — Uniform Model

| Format | Unit | Location fields populated | Example |
|---|---|---|---|
| PDF (text layer) | page | `page_index`, `char_offset`, `rect` | `{doc_kind: PDF, page_index: 3, char_offset: 412, rect: (120.0, 240.5, 280.0, 256.0)}` |
| PDF (image-block) | image-block in page | `page_index`, `char_offset` (relative to OCR'd text), `rect` (OCR local rect → page coords) | `{doc_kind: PDF, page_index: 3, char_offset: 0, rect: (200.0, 300.0, 350.0, 320.0)}` |
| Word (paragraph) | paragraph | `data_key` (the mammoth block key), `char_offset` | `{doc_kind: WORD, data_key: "p_12_0", char_offset: 7}` |
| Word (table cell) | cell paragraph | `data_key`, `char_offset` | `{doc_kind: WORD, data_key: "tbl_2_r3_c1_p0", char_offset: 14}` |
| Excel (cell) | cell | `sheet_name`, `cell_coord` (`"B12"`), `char_offset` (within cell text) | `{doc_kind: EXCEL, sheet_name: "员工信息", cell_coord: "B12", char_offset: 0}` |
| Image | whole-image OCR'd region | `rect` (pixel coords) | `{doc_kind: IMAGE, rect: (40, 80, 220, 110)}` |

**Apply-side branching table** (lives in `DocumentAdapter.apply_redactions`, never in the engine):

| `doc_kind` | Apply operation |
|---|---|
| `PDF` | `page.add_redact_annot(rect)` + `apply_redactions(images=PDF_REDACT_IMAGE_REMOVE, graphics=PDF_REDACT_GRAPHICS_REMOVE, text=True, garbage=4, deflate=True)` (NEVER `draw_rect`) |
| `WORD` | `python-docx` run-aware replacement (existing pattern at `main.py:951`) |
| `EXCEL` | `ws[cell_coord] = masked` (formula/style/merge auto-preserved by openpyxl) |
| `IMAGE` | `ImageDraw.rectangle(rect, fill="black")` + flatten + save |

The `DocumentAdapter` subclass dispatches; `Engine` never sees the difference.

---

## 7. Recognizer Pipeline — Detail

```text
Registry (per entity type):
   regex:   pattern -> candidate spans
   checksum:pattern + validator function (id_card_mod11, luhn, uscc_mod31_3) -> candidate spans
   dictionary: surname/given_name/admin_division/org_keyword lookup -> candidate spans
   context:  context-keyword window ±N chars around candidate -> bumps tier

Pipeline order (per TextUnit, per entity):
   1. RegexRecognizer.recognize(unit)  -> CandidateSpan[]
   2. ChecksumRecognizer.recognize(unit)  -> filters step 1 (or generates own); drops on validator fail
   3. DictionaryRecognizer.recognize(unit)  -> CandidateSpan[]
   4. For each candidate span (regex + checksum + dictionary):
        ContextAwareRecognizer.scan_window(unit, span, ±N chars)  -> bump tier if anchor keyword found
   5. overlap.resolve(all_spans)  -> dedup identical/overlapping ranges; pick winner by tier then specificity
   6. confidence.assign(span)  -> HIGH / MEDIUM / LOW
   7. mask.suggest(entity_type, span.text, location)  -> suggested_mask string

Tier assignment rules (in privacyguard/pii/confidence.py):
   HIGH   = validator_passed AND format-strict regex
            (身份证 mod11 / 银行卡 Luhn / 统一社会信用代码 mod31-3 / 手机号段号白名单 / 邮箱格式 / IP 段号)
   MEDIUM = format-strict regex but no validator available
            (车号 / URL / IPv6)
   LOW    = dictionary match OR context-anchor match
            (中文姓名 / 机构名 / 详细地址 / 金额 / 合同编号)

Conflict resolution (in privacyguard/pii/overlap.py):
   - Two spans overlap: keep the one with higher tier; on tie, keep the longer match;
     on tie, keep the more-specific entity (e.g. CN_ID_CARD wins over CN_NUMBER)
   - Two spans are identical: dedup; keep one with higher validator_passed
```

**Key Presidio parallel** (we borrow the structure, not the code):

| Presidio concept | Our equivalent |
|---|---|
| `AnalyzerEngine` | `Engine` (`privacyguard/pii/engine.py`) |
| `EntityRecognizer` (ABC) | `Recognizer` (ABC) (`privacyguard/pii/recognizers/base.py`) |
| `Pattern` + `PatternRecognizer` | `RegexRecognizer` |
| `PatternRecognizer` + custom `validate()` | `ChecksumRecognizer` |
| `AnalyzerEngineRegistry` | `EntityRegistry` (`privacyguard/pii/entities.py`) |
| `RecognizerResult` (score + entity_type + start/end) | `PIIHit` (adds: tier, source, suggested_mask, location) |
| `AnonymizerEngine` + `Operator` + `OperatorConfig` | `mask.py` + `DocumentAdapter.apply_redactions` (apply is split out of the engine itself) |
| `AnalyzeRequest` (text + entities + language) | `TextUnit` (text + location + meta) |

The split is deliberate: Presidio bundles analysis and anonymisation into the same engine; we split them so a `DocumentAdapter` can mediate the apply step (because apply is format-specific and engine-agnostic). This matches our constraint that `Engine` has no Qt and no format knowledge.

---

## 8. Threading & Progress

### 8.1 Where detection runs

| Path | Worker (QThread) | What it does |
|---|---|---|
| PDF open → auto-scan | existing `_ModularOCRWorker` (`privacyguard/workers/ocr_worker.py:35`) extended | for each page: `PdfAdapter.extract_text_units` → `Engine.detect(unit)` → emit `hit_signal(page_idx, [PIIHit])` → MainWindow appends into `page_data[page]["pii"]` |
| Word open → "智能扫描" | existing `_ModularWordWorker` (`privacyguard/workers/word_worker.py:16`) extended | same shape; per `data-key` units |
| Excel open → scan | NEW `ExcelWorker` (`privacyguard/workers/excel_worker.py`) | chunks at sheet boundary; emits `progress_signal(sheet_idx, total_sheets)` |
| Image file drop → scan | NEW `ImageWorker` (`privacyguard/workers/image_worker.py`) | one image per worker run; RapidOCR lazily initialised inside the worker (not in module import) |
| Generic detection pass over existing `page_data` / `word_data` units (refresh, re-scan after rule edit) | NEW `DetectionWorker` (`privacyguard/workers/detection_worker.py`) | wraps `Engine`; takes a generator of `TextUnit`s and emits `hit_signal(unit_id, [PIIHit])` |

### 8.2 Cancellation & locks

- Every new worker follows the existing `isInterruptionRequested()` pattern (see `_ModularOCRWorker.run` in `privacyguard/workers/ocr_worker.py`).
- `MainWindow` calls `requestInterruption()` before scheduling a new worker (existing pattern at `main.py:4931` via `self.worker_lock = QMutex()`).
- A new `_pii_data_lock = QMutex()` is added alongside `_word_data_lock` (`main.py:4918`) to serialise writes into `page_data[page]["pii"]` from the worker.

### 8.3 UI responsiveness on large workbooks

- `ExcelWorker` chunks by sheet (not by row). For a 50-sheet workbook, each sheet is a single chunk of progress; `progress_signal(int)` reports `int(sheet_idx * 100 / total_sheets)`.
- Within a sheet, progress reports every N rows (default 100) to avoid signal storm.
- The candidate-dialog window has a "Cancel" button bound to `worker.requestInterruption()` (mirrors the existing batch-replace pattern at `main.py:3806`).

### 8.4 Signal conventions

All new workers emit the standard quartet:

```python
hit_signal = pyqtSignal(str, list)        # unit_id, PIIHit[] (as dict for cross-thread)
progress_signal = pyqtSignal(int)         # percent 0..100
finished_signal = pyqtSignal(str, list)   # doc_id, all_hits[]
error_signal = pyqtSignal(str)            # error message
```

`PIIHit` is not `QObject`-safe across threads, so workers emit the dataclass as a `dict` (via `dataclasses.asdict`) and the receiving slot reconstructs it. This avoids registering Qt metaclasses for our data types.

---

## 9. Lazy Loading — Carry Forward

The v37.7.6 contract: nothing that pulls native OCR DLLs or heavy model files loads at `import privacyguard` time.

| Module | Loading behaviour | Reason |
|---|---|---|
| `privacyguard/pii/__init__.py` | eager (re-exports `PIIHit`, `DocumentLocation`, `Engine`) | pure-Python; cheap |
| `privacyguard/pii/dictionaries/__init__.py` | eager (`json.load` at module import, ~260KB total) | small JSON; no native code; fast |
| `privacyguard/pii/regex_engine.py` (or inline in `regex.py`) | `re.compile` at module level | fast, no IO |
| `privacyguard/pii/validators/*.py` | eager (pure functions) | no IO |
| `privacyguard/ocr/image_ocr.py` | `from rapidocr_onnxruntime import RapidOCR` **inside `recognize(image)` function body**, not at module top | HARD constraint — same as existing `privacyguard/ocr/rapidocr.py` |
| `privacyguard/workers/detection_worker.py` | lazy via `__getattr__` in `privacyguard/workers/__init__.py` `_LAZY_IMPORTS` | matches existing pattern (`privacyguard/workers/__init__.py:15`) |
| `privacyguard/workers/excel_worker.py` | lazy via `_LAZY_IMPORTS` | new entry |
| `privacyguard/workers/image_worker.py` | lazy via `_LAZY_IMPORTS` | new entry |
| `privacyguard/formats/excel_adapter.py` | eager top-level `import openpyxl` is OK (no native code, pure-Python); but the adapter module itself is only imported when `ExcelAdapter` is instantiated | openpyxl is safe to import eagerly; no harm in lazy anyway |
| `privacyguard/formats/image_adapter.py` | eager top-level `from PIL import Image` is OK; `image_ocr` import stays inside `extract_text_units` | Pillow is already pinned |

**Verification:** add an assertion to `tests/unit/test_package_imports.py` that `import privacyguard; import privacyguard.workers; import privacyguard.ocr` does NOT trigger `import rapidocr_onnxruntime`. This is the same pattern cp30 already enforced for `privacyguard.utils.security`.

---

## 10. Integration Points with Existing Code

Each integration point references a real file path and indicates the change type.

| Integration site | Existing file / line | Change |
|---|---|---|
| Package surface | `privacyguard/__init__.py:61` (`_LAZY_IMPORTS` table) | append new keys: `Engine`, `PIIHit`, `DocumentLocation`, `ExcelAdapter`, `ImageAdapter`, `ExcelWorker`, `ImageWorker`, `DetectionWorker` |
| Worker surface | `privacyguard/workers/__init__.py:15` (`_LAZY_IMPORTS`) | same; ensure new workers are lazy |
| OCR text-PDF helper | `privacyguard/ocr/text_pdf.py:28` (`collect_text_pdf_hit_boxes`) | unchanged — wrapped by `PdfAdapter.extract_text_units` |
| OCR mixed-PDF helper | `privacyguard/ocr/mixed_pdf.py:76` (`collect_image_block_ocr_hits`) | unchanged — wrapped by `PdfAdapter.extract_text_units` |
| OCR word worker | `privacyguard/workers/word_worker.py:16` (`_ModularWordWorker`) | extend `run()` to also call `Engine.detect(unit)` after scan; emit `hit_signal` per `data-key` |
| OCR pdf worker | `privacyguard/workers/ocr_worker.py:35` (`_ModularOCRWorker`) | extend `run()` to also call `Engine.detect(unit)` per page after existing OCR step |
| Main window state | `main.py:4908` (`self.page_data` init) | add `"pii": []` to default dict literal |
| Main window state | `main.py:4915` (`self.word_data` init) | add `"pii": []` to default dict literal |
| Main window state | `main.py:4908-4926` (state block) | add new attrs `self.excel_data`, `self.image_data`, `self._pii_data_lock` |
| Main window state | `main.py:4918` (`_word_data_lock`) | mirror pattern for `_pii_data_lock` |
| Worker wiring | `main.py:4191` (`OCRWorker` wrapper) | unchanged — extends modular worker; wrapper still injects `box_adjust_ratio` |
| Worker wiring | `main.py:4358` (`WordWorker` wrapper) | unchanged |
| Worker wiring | `main.py:3806` (`WordBatchReplaceWorker`) | unchanged for this milestone (batch apply stays on existing rules) |
| Existing keyword/manual flow | `main.py` keyword matching inline (multiple sites) | unchanged — legacy; new auto-detect does not touch it |
| Existing canvas | `main.py:4100` (`SinglePageCanvas.paintEvent`) | unchanged rendering; new `pii` hits re-use the same colour palette via a new `pii_highlight_color` token in `theme.py` |
| Theme | `theme.py:6` (`Theme` class) | add 3 colour tokens: `pii_high_color` (HIGH tier yellow), `pii_review_color` (MEDIUM orange), `pii_candidate_color` (LOW blue) |
| Settings dialog | `main.py:1008` (`SettingsDialog`) | add tab "识别规则" — entity-type toggles, threshold slider, doc-level whitelist editor |
| PyInstaller spec | `packaging/windows/scripts/build_complete.bat` + `packaging/macos/scripts/build_complete.sh` | add `datas=[("privacyguard/pii/dictionaries/*.json", "privacyguard/pii/dictionaries")]` and verify no new hiddenimport |
| Test baseline | `tests/unit/test_<name>.py` (10 existing files) | required: add `tests/unit/test_pii_engine.py`, `tests/unit/test_pii_validators.py`, `tests/unit/test_pii_mask.py`, `tests/unit/test_excel_adapter.py`, `tests/unit/test_image_adapter.py`, `tests/unit/test_format_location.py` |
| `tests/unit/test_package_imports.py` | current test | extend to assert `import privacyguard` does NOT pull `openpyxl` or `rapidocr_onnxruntime` at top level (lazy guarantee) |
| `tests/unit/test_convergence.py` | current test | extend assertion that `main.py` does not import from `privacyguard.pii.*` at top level — engine stays pure |
| Version | `version.txt` + `main.py::read_app_version()` + `privacyguard/__init__._read_version()` | bump once per phase |

---

## 11. Build Order (Dependency Reasoning)

The phases below are the natural build order. Items within a phase can be parallelised (e.g., Phase A.3 validators are independent of each other).

### Phase A — Foundation (no UI, no Qt, no format-specific code)

| Sub-step | Depends on | File(s) created | Independent? |
|---|---|---|---|
| A.1 `PIIHit`, `DocumentLocation`, `TextUnit`, `ConfidenceTier`, `DocKind` | nothing | `privacyguard/pii/types.py` | yes |
| A.2 `Recognizer` ABC + `CandidateSpan` dataclass | A.1 | `privacyguard/pii/recognizers/base.py` | yes |
| A.3 Validators (in parallel): `id_card.py` (GB 11643 mod-11-2), `bank_card.py` (Luhn), `uscc.py` (GB 32100 mod-31-3) | nothing (pure math) | `privacyguard/pii/validators/*.py` | yes — all three parallelisable |
| A.4 `RegexRecognizer`, `ChecksumRecognizer`, `DictionaryRecognizer`, `ContextAwareRecognizer` | A.1, A.2, A.3 | `privacyguard/pii/recognizers/*.py` | yes (one per file) |
| A.5 Dictionaries JSON (surnames, given_names, admin_divisions, org_keywords, context_anchors) | nothing | `privacyguard/pii/dictionaries/*.json` | yes — data-only |
| A.6 `overlap.py` (span dedup + conflict resolution) | A.1, A.2 | `privacyguard/pii/overlap.py` | yes |
| A.7 `confidence.py` (3-tier assignment) | A.1, A.3 | `privacyguard/pii/confidence.py` | yes |
| A.8 `mask.py` (per-entity masking) | A.1 | `privacyguard/pii/mask.py` | yes |
| A.9 `Engine` (orchestrator) | A.1–A.8 | `privacyguard/pii/engine.py` | NO — depends on all of the above |
| A.10 `entity registry` (`entities.py`) | A.3, A.5, A.8 | `privacyguard/pii/entities.py` | after A.3/A.5/A.8 |
| A.11 `report.py` (RedactionReport dataclass + JSON writer) | A.1 | `privacyguard/pii/report.py` | yes |
| A.12 Unit tests for Phase A | each step | `tests/unit/test_pii_validators.py`, `test_pii_engine.py`, `test_pii_mask.py`, `test_pii_overlap.py`, `test_confidence.py` | parallelisable after their target modules |

**Exit criterion for Phase A:** `Engine.detect(TextUnit("foo", "11010119800101003X", DocumentLocation(DocKind.PDF, page_index=0, char_offset=0)))` returns `[PIIHit(entity_type="CN_ID_CARD", confidence=HIGH, validator_passed=True, suggested_mask="110101********003X", ...)]`. No Qt. No format I/O.

### Phase B — PDF Integration (extends existing path)

| Sub-step | Depends on | File(s) created/modified | Notes |
|---|---|---|---|
| B.1 `DocumentAdapter` ABC + `RedactionPlan` dataclass | A.1 | `privacyguard/formats/base.py` | also defines the unit/apply contract |
| B.2 `PdfAdapter.extract_text_units` (wraps `collect_text_pdf_hit_boxes` + `collect_image_block_ocr_hits`) | A, `privacyguard/ocr/text_pdf.py:28`, `privacyguard/ocr/mixed_pdf.py:76` | `privacyguard/formats/pdf_adapter.py` | yields `TextUnit`s, not raw rects |
| B.3 `PdfAdapter.apply_redactions` (PyMuPDF `add_redact_annot + apply_redactions`) | B.2 | same file | NO draw_rect — see anti-feature in `FEATURES.md` §7.1 |
| B.4 Verification step (`Page.get_text("words")` after redact returns nothing in redacted region) | B.3 | helper in `pdf_adapter.py` | automated in pipeline |
| B.5 Extend `_ModularOCRWorker.run` to call `Engine.detect(unit)` after existing scan, append to `page_data[page]["pii"]` | A, B.2 | `privacyguard/workers/ocr_worker.py:35` | per-page |
| B.6 Wire `hit_signal` → `MainWindow` slot that appends into `page_data` | B.5 | new slot in `MainWindow` (`main.py:4885` region) | |
| B.7 Theme tokens `pii_high_color` / `pii_review_color` / `pii_candidate_color` | nothing | `theme.py:6` | |
| B.8 Tests: `test_pdf_pii_pipeline.py` (round-trip with known ID card / phone number in a synthetic PDF) | B.1–B.6 | `tests/unit/` | |

### Phase C — Word + Excel + Image Adapters (parallel after B.1, A)

Phase C splits into three independent tracks that can be parallelised:

| Track | Depends on | Files | Independent of |
|---|---|---|---|
| **C1 — WordAdapter** | A, B.1 | `privacyguard/formats/word_adapter.py` + extend `privacyguard/workers/word_worker.py:16` to call `Engine.detect(unit)` per `data-key` + emit `hit_signal` | C2, C3 |
| **C2 — ExcelAdapter** | A, B.1, `openpyxl` (new dep) | `privacyguard/formats/excel_adapter.py` + new `privacyguard/workers/excel_worker.py` + new state attrs in `main.py` | C1, C3 |
| **C3 — ImageAdapter** | A, B.1, `privacyguard/ocr/image_ocr.py` (new) | `privacyguard/ocr/image_ocr.py` (RapidOCR lazy inside fn) + `privacyguard/formats/image_adapter.py` + new `privacyguard/workers/image_worker.py` | C1, C2 |

C2 sub-tasks (the only track with state-shape changes):
- C2.1 `openpyxl` install (one-line `pip install "openpyxl>=3.1.5,<3.2"` in `requirements.txt`)
- C2.2 `ExcelAdapter.extract_text_units` — `iter_rows()` across all sheets incl. hidden; yields `TextUnit` per non-empty cell
- C2.3 `ExcelAdapter.apply_redactions` — write `cell.value = masked`; preserve `data_only=False` for formula retention; also clear `wb.properties.creator / lastModifiedBy`, scan `defined_names`, scan `comments`
- C2.4 `ExcelWorker` — sheet-by-sheet chunked progress
- C2.5 State attrs `self.excel_data`, `self._pii_data_lock` in `main.py:4908-4926`

C3 sub-tasks:
- C3.1 `image_ocr.py` — wraps `RapidOCREngine.recognize()` for Pillow Image; RapidOCR import stays inside `recognize()`
- C3.2 `ImageAdapter.extract_text_units` — runs OCR per image; yields `TextUnit` per detected line
- C3.3 `ImageAdapter.apply_redactions` — Pillow `ImageDraw.rectangle` black-fill + flatten + save; re-OCR verification pass
- C3.4 `ImageWorker` — one image per run; emits `hit_signal(image_path, [PIIHit])`

### Phase D — Apply UX + Audit + Packaging

| Sub-step | Depends on | File(s) | Notes |
|---|---|---|---|
| D.1 `CandidateDialog` (review queue UI) | B.6 (or C1.6 / C2.6 / C3.5) | `main.py` (stays for now per architectural constraint — UI not migrating this milestone) | two-panel: HIGH auto-apply / MEDIUM+LOW review |
| D.2 Per-hit override (toggle a single hit from auto-apply to skip) | D.1 | same | persisted in session; included in `RedactionReport` |
| D.3 Entity-type toggles + doc-level whitelist editor | D.1 | `SettingsDialog` tab "识别规则" (`main.py:1008`) | |
| D.4 `RedactionReport` writer wired into apply phase | A.11 | `privacyguard/pii/report.py` + `MainWindow.finished_signal` slot | JSON output per document |
| D.5 PyInstaller spec update | C2.1 (openpyxl), A.5 (dictionaries) | `packaging/windows/scripts/build_complete.bat`, `packaging/macos/scripts/build_complete.sh` | add `datas=[("privacyguard/pii/dictionaries/*.json", "privacyguard/pii/dictionaries")]` |
| D.6 Cross-platform packaging smoke test | D.5 | run `build_complete.bat` on Windows; `build_complete.sh` on macOS | required by CLAUDE.md "any new module must verify packaging" |

### Phase parallelism summary

```text
Phase A (all sub-steps except A.9 engine, which waits for A.1–A.8)  ── fully parallel ──
                                       │
Phase B (PDF)  ────────────────────────┤
                                       ├──  can start as soon as A.9 + B.1 done
                                       │
Phase C1 (Word) ◀──── independent ─────┤
Phase C2 (Excel) ◀──── independent ────┤── can start in parallel
Phase C3 (Image) ◀──── independent ────┤
                                       │
Phase D (UI / Apply / Packaging) ──────┴── starts after at least one of B/C tracks lands
```

### Phase independence cheat-sheet

- **Validators (A.3) are the most isolated pieces** — pure math, no imports beyond stdlib. They can be developed and tested in a single sitting without any other Phase A piece.
- **Dictionaries (A.5) are pure data** — JSON files, can be sourced and versioned independently.
- **Masking (A.8) is pure-Python string ops** — independent of validators and recognizers; can be developed and tested as soon as the entity-type list (A.10's inputs) is agreed.
- **The PDF adapter (Phase B) is the cheapest integration** — it wraps existing helpers (`text_pdf.py`, `mixed_pdf.py`) that already work. New code = ~150 lines of `PdfAdapter`.
- **The Excel adapter (C2) is the longest pure-integration** — column-header inference, formula preservation, hidden-sheet inclusion. Estimate ~600–800 lines.
- **The Image adapter (C3) reuses the existing RapidOCR stack** — new code = ~200 lines.
- **The Word adapter (C1) is the smallest delta** — Word is already DOCX-text-flow; the engine plugs into the existing paragraph iteration loop. Estimate ~250 lines.

---

## 12. Concrete File Paths (summary of all new / modified files)

### New files

```
privacyguard/pii/
  __init__.py
  types.py
  entities.py
  engine.py
  confidence.py
  overlap.py
  mask.py
  report.py
  recognizers/
    __init__.py
    base.py
    regex.py
    checksum.py
    dictionary.py
    context.py
  validators/
    __init__.py
    id_card.py
    bank_card.py
    uscc.py
  dictionaries/
    __init__.py
    surnames.json
    given_names.json
    admin_divisions.json
    org_keywords.json
    context_anchors.json

privacyguard/formats/
  __init__.py
  base.py
  pdf_adapter.py
  word_adapter.py
  excel_adapter.py
  image_adapter.py

privacyguard/ocr/
  image_ocr.py

privacyguard/workers/
  detection_worker.py
  excel_worker.py
  image_worker.py

tests/unit/
  test_pii_types.py
  test_pii_validators.py
  test_pii_overlap.py
  test_pii_confidence.py
  test_pii_mask.py
  test_pii_engine.py
  test_pii_report.py
  test_format_location.py
  test_pdf_pii_pipeline.py
  test_word_pii_pipeline.py
  test_excel_pii_pipeline.py
  test_image_pii_pipeline.py
```

### Modified files (minimal-surface changes)

```
main.py
  - Add state attrs (excel_data, image_data, _pii_data_lock)  [near line 4908-4926]
  - Add "pii": [] default to page_data and word_data initialisation
  - Add new MainWindow slot for hit_signal append
  - Add CandidateDialog class
  - Add "识别规则" tab to SettingsDialog  [near line 1008]
  - Add Worker wiring for ExcelWorker / ImageWorker / DetectionWorker

theme.py
  - Add pii_high_color / pii_review_color / pii_candidate_color

privacyguard/__init__.py
  - Append to _LAZY_IMPORTS table  [line 61]
  - Optionally: top-level re-export of PIIHit, DocumentLocation, Engine (cheap)

privacyguard/workers/__init__.py
  - Append to _LAZY_IMPORTS  [line 15]

privacyguard/workers/ocr_worker.py
  - _ModularOCRWorker.run: after existing OCR pass, call Engine.detect(unit) per page; emit hit_signal

privacyguard/workers/word_worker.py
  - _ModularWordWorker.run: after existing scan, call Engine.detect(unit) per data-key; emit hit_signal

requirements.txt
  - Add openpyxl>=3.1.5,<3.2

tests/unit/test_package_imports.py
  - Assert: import privacyguard does NOT pull rapidocr_onnxruntime or openpyxl at top level

tests/unit/test_convergence.py
  - Assert: main.py does NOT import from privacyguard.pii.* at top level

packaging/windows/scripts/build_complete.bat
  - Add datas=[("privacyguard/pii/dictionaries/*.json", "privacyguard/pii/dictionaries")]

packaging/macos/scripts/build_complete.sh
  - Same datas entry

version.txt
  - Bump once per phase (37.7.6 -> 38.0.0 -> 38.1.0 ...)
```

---

## 13. Anti-Patterns Specific to This Design

(These complement, not duplicate, the anti-patterns already documented in `.planning/codebase/ARCHITECTURE.md`.)

### 13.1 Recreating a "pii_hits" dict separate from `page_data` / `word_data`

**What goes wrong:** A new code path builds `self.pii_hits = []` at the `MainWindow` level instead of appending into `page_data[page]["pii"]` / `word_data[key]["pii"]`. Two parallel state trees drift immediately — one has the redactions, the other has the rendering.
**Why it's wrong:** Splits source-of-truth. Render code reads one dict, apply code reads another, they disagree on what to mask.
**Instead:** Always append into the existing `page_data` / `word_data` dict's `"pii"` key. New formats get new dicts (`excel_data`, `image_data`) but each follows the same shape: `{"text"|"ocr_text": ..., "pii": [PIIHit, ...]}`.

### 13.2 Calling `Engine.detect` on the main thread

**What goes wrong:** A "quick scan" path inlines `Engine.detect(unit)` directly into a slot connected to a button click. On a 500-page PDF, the UI freezes for seconds.
**Why it's wrong:** The whole point of the QThread worker layer is to keep the UI responsive. Detection is CPU-bound (regex + JSON dict lookups + validators).
**Instead:** All detection goes through a worker. The candidate-dialog can show "Scanning..." with a progress bar bound to the worker's `progress_signal`. The user can cancel via `requestInterruption()`.

### 13.3 Using `draw_rect` to "redact" a PDF

**What goes wrong:** A new apply path does `page.draw_rect(rect, color="black")` instead of `page.add_redact_annot(rect)` + `apply_redactions(...)`.
**Why it's wrong:** This is the documented catastrophic failure mode (`FEATURES.md` §7.1) — the underlying text remains extractable via `pdftotext`. Privacy tool ships a vulnerability.
**Instead:** `PdfAdapter.apply_redactions` exclusively uses `add_redact_annot + apply_redactions(text=True, images=PDF_REDACT_IMAGE_REMOVE, graphics=PDF_REDACT_GRAPHICS_REMOVE, garbage=4, deflate=True)`. The verification step `Page.get_text("words")` after redaction returns nothing in the redacted region — this assertion is enforced by `tests/unit/test_pdf_pii_pipeline.py`.

### 13.4 Importing `RapidOCR` at the top of `image_ocr.py` or `image_adapter.py`

**What goes wrong:** New convenience imports `from rapidocr_onnxruntime import RapidOCR` at module top so the adapter module is "ready to use".
**Why it's wrong:** Breaks the lazy-loading contract (`CLAUDE.md` hard constraint; cp30 regression). Every `import privacyguard` would pull native OCR DLLs.
**Instead:** Import inside the function body. Mirror the existing `privacyguard/ocr/rapidocr.py` pattern.

### 13.5 Re-running detection on every apply

**What goes wrong:** `DocumentAdapter.apply_redactions` re-runs detection on the file to "make sure nothing changed".
**Why it's wrong:** Doubles CPU cost; also re-introduces non-determinism (different runs may yield different candidate sets for context-tier entities).
**Instead:** Apply consumes the `PIIHit[]` that was already produced and confirmed in the UI phase. If the user edited the file, they must re-scan — the UI makes this explicit.

### 13.6 Treating Excel columns as a single TextUnit

**What goes wrong:** `ExcelAdapter.extract_text_units` yields one `TextUnit` per column (concatenating all cells).
**Why it's wrong:** Loses per-cell char offsets; partial masking requires cell-level granularity. Column-name inference (Phase C2 sub-feature) needs to know which column header a cell belongs to.
**Instead:** One `TextUnit` per non-empty cell, with `location.sheet_name + location.cell_coord + location.char_offset`. Column inference happens at a higher level (post-detection).

---

## 14. Roadmap Implications (handoff to phase planning)

- **Phase A (foundation) has no UI surface, no Qt, no format I/O.** It is pure-Python code with high test coverage. Good candidate for the first vertical slice — fast feedback, low blast radius.
- **Phase B (PDF) is the cheapest end-to-end integration** because the existing OCR helpers already produce per-page text. Adding `Engine.detect(unit)` inside `_ModularOCRWorker.run` is a few dozen lines.
- **Phase C tracks (C1 Word / C2 Excel / C3 Image) are mutually independent** and can ship in any order. Phase C1 (Word) is the smallest delta. Phase C2 (Excel) is the most user-visible new capability. Phase C3 (Image) is the natural continuation of the existing OCR pipeline.
- **Phase D (UI/Audit/Packaging) is downstream of at least one C track** and can be split: D.1 (CandidateDialog) needs B.6; D.3 (Settings tab) needs A.10; D.5 (packaging) needs at least C2 because openpyxl changes the bundle shape.
- **Phase A's validators (A.3) are the highest-ROI standalone deliverable.** They are 30 lines each, have public test vectors, and unblock the engine's HIGH-confidence tier. They are a natural "first commit" before the bigger pieces land.
- **Phase A's masking (A.8) is the second-highest-ROI standalone deliverable.** Pure-Python string ops, fully testable, and ships user-visible value (partial masking) even before the detection pipeline is fully wired.
- **The current `main.py` state block (`main.py:4908-4926`) and theme (`theme.py:6`) are the only required UI-layer edits** until Phase D's `CandidateDialog` lands. This keeps the v37.7.6 convergence guarantee (new shared logic in `privacyguard/`, not `main.py`) intact for the core engine work.

---

## 15. Open Questions (for per-phase research later)

- Exact length of the engine's registry — how many entity types ship in v1 vs. Phase 2 — is a Phase A scoping question.
- Whether `confidence.py` should also expose a raw 0.0–1.0 score (Presidio style) in addition to the 3-tier bucket — UX decision, can defer.
- Whether `RedactionReport` should also bundle the original file's SHA-256 for audit trail — small, but adds IO cost; defer to D.4.
- Whether the Excel column-header inference belongs in the adapter or as a separate `ColumnInferenceEngine` — defer to Phase C2 design.

---

*Architecture research for: PrivacyGuard v38.x — PII engine + format handler integration*
*Researched: 2026-08-10*
*Hand-off to: phase planner*