---
phase: 01-pdf
plan: 01
slug: tracer
type: execute
wave: 1
depends_on: []
files_modified:
  - privacyguard/pii/__init__.py
  - privacyguard/pii/hits.py
  - privacyguard/pii/validators/__init__.py
  - privacyguard/pii/validators/id_card.py
  - privacyguard/pii/validators/phone_segment.py
  - privacyguard/pii/regex_patterns.py
  - privacyguard/pii/normalize.py
  - privacyguard/pii/confidence.py
  - privacyguard/pii/mask.py
  - privacyguard/pii/overlap.py
  - privacyguard/pii/engine.py
  - privacyguard/pii/pdf_adapter.py
  - privacyguard/pii/data/rules.json
  - tests/fixtures/fake_pii.py
  - tests/e2e/create_pii_test_pdf.py
  - tests/unit/test_pdf_pii_redaction.py
  - privacyguard/__init__.py
  - tests/unit/test_package_imports.py
  - tests/unit/test_convergence.py
autonomous: true
requirements:
  - ENGINE-01
  - ENGINE-02
  - ENGINE-03
  - ENGINE-04
  - ENGINE-05
  - NUM-01
  - NUM-02
  - NUM-03
  - SAFE-01
  - SAFE-02
  - OPS-03
  - OPS-07
user_setup: []

estimate:
  tokens: 85000
  raw_tokens: 42500
  tasks: 3
  confidence: medium

must_haves:
  truths:
    - A synthetic PDF containing one 18-digit Chinese ID card (Faker-generated, mod-11-2 valid) opened through PIIEngine.detect returns exactly one PIIHit with entity_type="CN_ID_CARD", confidence_tier="HIGH", validator_passed=True.
    - Exported PDF produced via privacyguard.pii.pdf_adapter.apply_pii_redactions contains zero instances of the ID card's first 10 digits when re-extracted via fitz.open(out).get_text() — i.e. 真删除 (SAFE-01 + SAFE-02). The reverse-extraction MUST use the `fitz` path (`fitz.open(out).get_text()`) per D-14 — not `pdftotext` / poppler-utils — so the test runs in any CI environment without requiring poppler installation; `pdftotext` is reserved for human verification only.
    - validate_18_id on a GB 11643-1999 standard sample "53010219200508011X" returns True and on a corrupted check-digit "530102192005080119" returns False (NUM-01).
    - validate_18_id on the same number with OCR-style lowercase tail "53010219200508011x" returns True (NUM-02 — case-insensitive X).
    - is_mobile_segment("19912345678") returns True (5G MIIT segment) while is_mobile_segment("14012345678") returns False (IoT exclusion NUM-03).
    - PIIHit dataclass fields, in order, are entity_type, page_offset, page_length, page_rect, confidence_tier, source, mask_strategy (D-05 locked, no rename) AND the page_offset / page_length pair carries a char-level offset into the page text string — not just a QRectF (D-06 char-level offset contract). OCR paths recover the offset by joining `iter_ocr_lines` outputs into one string and aligning back to the original via `map_flat_to_original`; text-layer paths use `page.get_text()` string indices directly.
    - import privacyguard does not load privacyguard.pii.engine into sys.modules (OPS-03 lazy-load contract preserved).
    - Existing 79/79 baseline (test_mixed_pdf_ocr / test_path_validation / test_ocr_api / test_package_imports / test_pdf_text_hit_dedup / test_app_config / test_word_replace_rules / test_batch_word_replace / test_config_alignment / test_fstring_safety / test_convergence) remains green after this plan lands (D-13 baseline preservation).
    - main.py contains no inline `class PIIHit` / `def detect_pii` / `def validate_id_card(` (convergence test, v37.7.6 rule).
    - SettingsDialog "5 隐私识别" tab visible in UI when SettingsDialog opened (UI-SPEC §E1 populated state).
    - SettingsDialog tab carries three QCheckBox with locked labels: "启用隐私识别引擎" / "扫描后自动真脱敏" / "HIGH 档命中需手动确认" plus a read-only "扫描范围（只读）：身份证号 / 手机号" label (UI-SPEC §Copywriting).
    - PII rects on SinglePageCanvas render in third paint loop with stroke color #D64545 (light) / #FF6B6B (dark) and label badges "ID" or "PHONE" anchored top-left (UI-SPEC §PII Rect Rendering).
    - PII status chip on info_bar shows one of the locked copy rows: "识别引擎已停用" / "PII 自动识别 已启用" / "已识别 N 项敏感内容" / "扫描完成：未发现敏感内容" / "扫描第 X / Y 页…" (UI-SPEC §Status Bar PII Chip).
    - Confirmation QDialog appears modally when require_confirmation=true AND HIGH hits present, with three CTAs "全部脱敏并保存" / "仅脱敏选中的 N 项" / "暂不脱敏（仅高亮）" (UI-SPEC §Confirmation Dialog).
    - PDF save loop merges pii_list alongside ocr_list + manual_list and applies PyMuPDF add_redact_annot + apply_redactions(images=PDF_REDACT_IMAGE_PIXELS) so PII rects are truly deleted (D-04 + SAFE-01 + D-07 default auto-redaction: HIGH-tier hits enter the redaction list automatically and are destroyed on save unless `pii_settings.require_confirmation` is enabled, in which case the user is prompted via the confirmation dialog).
    - PyInstaller spec datas contains (privacyguard/pii/data, privacyguard/pii/data) and hiddenimports contains privacyguard.pii.* modules so frozen launches can load rules.json (D-10 + OPS-03).
    - collect_full_page_ocr_hits is invoked in _ModularOCRWorker.run when page text is empty AND page contains image blocks, producing a page_rect tuple per OCR hit (D-03 dependency-injection).
    - A 500-page synthetic scan finishes in <60s and emits at least one progress_signal so UI stays responsive (Success Criteria #4 + ENGINE-07).
    - monkey-patching socket.socket and running engine.detect over 500 pages produces zero recorded socket calls (ENGINE-08 zero-network).
  artifacts:
    - privacyguard/pii/__init__.py (lazy _LAZY_IMPORTS + __getattr__ + __all__; 8 exports: PIIEngine / PIIHit / TextUnit / validate_18_id / validate_15_id / is_mobile_segment / apply_pii_redactions / collect_pii_rects)
    - privacyguard/pii/hits.py (PIIHit dataclass frozen=True; 7 D-05 field names in D-05 order, with trailing defaults: confidence_tier="HIGH", source="text", mask_strategy="", normalized="", validator_passed=True — B4 fix) — carries D-06 char-level offset fields (page_offset / page_length)
    - privacyguard/pii/validators/__init__.py (lazy re-export of id_card + phone_segment validators)
    - privacyguard/pii/validators/id_card.py (WEIGHTS tuple, MAPPING tuple, compute_check_digit, validate_18, validate_15, upgrade_15_to_18, is_valid_admin_division_prefix_2, is_real_calendar_date — B1 second gate for 15-digit path)
    - privacyguard/pii/validators/phone_segment.py (PHONE_PERSONAL_PREFIX_3, PHONE_EXCLUDED_PREFIX_3, PHONE_EXCLUDED_PREFIX_4, is_mobile_segment)
    - privacyguard/pii/regex_patterns.py (_ID_18_RE, _ID_15_RE, _PHONE_11_RE, iter_candidate_strings)
    - privacyguard/pii/normalize.py (normalize_digits, flatten_for_match, map_flat_to_original with defensive (None,None) on failure)
    - privacyguard/pii/confidence.py (ConfidenceTier Literal, classify_hit)
    - privacyguard/pii/mask.py (partial_mask_id_card, partial_mask_phone, mask_for_entity — length-defensive)
    - privacyguard/pii/overlap.py (resolve by page_offset+page_length dedup with validator_passed priority)
    - privacyguard/pii/engine.py (TextUnit re-export, PIIEngine.detect pipeline, _engine_cache for ENGINE-04 mask consistency, 200KB input-size cap, last_error attribute)
    - privacyguard/pii/pdf_adapter.py (collect_pii_rects, apply_pii_redactions using PyMuPDF add_redact_annot + apply_redactions(images=PDF_REDACT_IMAGE_PIXELS) + garbage=4)
    - privacyguard/pii/data/rules.json (phone_segment.personal_prefix_3 / excluded_prefix_3 / excluded_prefix_4 + id_card.weights + id_card.mapping + last_verified + next_review)
    - tests/fixtures/fake_pii.py (fake_id_card / fake_phone / fake_phone_invalid)
    - tests/e2e/create_pii_test_pdf.py (create_pii_test_pdf via fitz insert_text)
    - tests/unit/test_pdf_pii_redaction.py (text-layer reverse-extraction test only; image-pixels case deferred to Plan 01-03 per B3) — D-12 class 3 (SAFE-02 reverse-extraction via fitz path per D-14)
    - tests/unit/test_package_imports.py (extended with pii lazy-load assertion + pii_engine_loads_on_demand + pii_engine_lazy_under_rapidocr_block)
    - tests/unit/test_convergence.py (extended with TestPiiConvergence: no-inline-PIIHit-in-main.py assertion + pii-package-has-no-qt-dependency assertion)
    - privacyguard/__init__.py (_LAZY_IMPORTS extended with PIIEngine / PIIHit / TextUnit / validate_18_id / validate_15_id / is_mobile_segment / apply_pii_redactions / collect_pii_rects)

    ### Cross-plan reference index (NOT produced by this plan)

    For traceability only — these files land in Plans 01-02 / 01-03, not here. The `artifacts` block above strictly enumerates what THIS plan produces:

    | Cross-plan deliverable | Producer plan |
    |----------------------|---------------|
    | `privacyguard/ocr/full_page_ocr.py` | Plan 01-03 Task 1 |
    | `tests/unit/test_pii_validators.py` | Plan 01-02 Task 1 |
    | `tests/unit/test_pii_engine.py` | Plan 01-02 Task 1 |
    | `tests/unit/test_pdf_pii_pipeline.py` | Plan 01-03 Task 3 |
    | `tests/unit/test_pii_offline.py` | Plan 01-03 Task 3 |
    | `tests/unit/test_app_config.py` (pii_settings extension) | Plan 01-03 Task 2 |
    | `config.json` + `config.json.template` (pii_settings block) | Plan 01-03 Task 2 |
    | `privacyguard/workers/ocr_worker.py` (pii_signal + _detect_pii_for_page) | Plan 01-03 Task 1 |
    | `main.py` (page_data 'pii' key, OCRWorker compat layer Site 3a, _on_pii_page_result slot, SettingsDialog tab, canvas paintEvent PII loop, save_pdf pii_list merge) | Plan 01-03 Task 2 |
    | `packaging/windows/config/PrivacyGuard_windows.spec` + `packaging/macos/scripts/build_complete.sh` + `packaging/macos/config/PrivacyGuard.spec` | Plan 01-03 Task 3 |

    ### Known Limitations (I1 / D-11)

    - **15-digit residual FP:** after the B1 second gate (province prefix + real calendar date), a 15-digit run that coincidentally satisfies both is still a possible business-data SKU. Phase 1 ships the `PIIEngine._check_id_card` demotion logic (bare 15-digit without context anchor → MEDIUM) but does not measure the residual FP rate. Phase 8's real-document accuracy baseline (OPS-06) will measure and either tighten the demotion heuristic or add context anchors.
    - **NUM-03 [ASSUMED] MIIT 2026-Q1 baseline:** see the user sign-off gate above; this remains a pre-ship checklist item.
  key_links:
    - privacyguard/pii/engine.detect(TextUnit) → privacyguard/pii/validators/{id_card,phone_segment} (NUM-01/02/03 validation gate before hit emission)
    - privacyguard/pii/pdf_adapter.apply_pii_redactions → fitz.add_redact_annot + fitz.apply_redactions(images=PDF_REDACT_IMAGE_PIXELS) → doc.save(garbage=4, deflate=True, clean=True) (SAFE-01)
    - privacyguard/__init__._LAZY_IMPORTS → privacyguard.pii.{engine,hits,validators} (OPS-03 lazy contract)
    - privacyguard/workers/ocr_worker._detect_pii_for_page → privacyguard/pii/engine.detect → pii_signal.emit(page_idx, [dataclasses.asdict(h) for h in hits]) → MainWindow._on_pii_page_result → page_data[page_num]["pii"] (D-04 + D-05)
    - MainWindow.save_pdf → for r in ocr_list + manual_list + pii_list: add_redact_annot + apply_redactions(IMAGE_PIXELS) (D-04 + SAFE-01)
    - privacyguard/utils/security.resource_path("privacyguard/pii/data/rules.json") → read rules_data at engine init (D-10 + cp30 regression)
  prohibitions:
    - 不得使用 page.draw_rect(fill=(0,0,0)) 或任何仅在内容流顶层画矩形的方式替代真删除（禁止假脱敏）
    - 不得因追求误报率优化而静默丢弃通过校验位/段号白名单的高置信度命中而改写为 MEDIUM/LOW（consistency）
    - 不得在测试夹具或测试断言中写入真实身份证号 / 手机号；fake_pii.py 是唯一合成来源（OPS-05）
    - 不得在识别引擎代码路径中触发 socket.socket / urllib / requests / httpx；ENGINE-08 由 test_pii_offline.py monkey-patch 守护
    - 不得在 main.py 中重复实现 PIIHit / detect_pii / validate_id_card / is_mobile_segment（v37.7.6 收敛原则，由 test_convergence.py 守护）
    - 不得在 privacyguard/__init__.py 或 privacyguard/workers/__init__.py 顶层 import privacyguard.pii.engine / .hits / .validators（OPS-03 懒加载契约）
    - 不得在 PII 引擎内部向 stdout/stderr 打印命中原文；仅打印脱敏后计数或 anonymized 计数（V9 日志泄漏）

threat_model:
  trust_boundaries:
    - {name: PDF file input, description: untrusted .pdf file path crosses here; PyMuPDF parses arbitrary PDF bytes}
    - {name: Worker thread → MainWindow slot, description: cross-thread pyqtSignal carrying PIIHit list (worker thread untrusted; MainWindow slot must not leak to other connections)}
    - {name: privacyguard.pii → filesystem, description: rules.json read via resource_path; PyInstaller frozen lookup must resolve to sys._MEIPASS/privacyguard/pii/data/rules.json}
    - {name: PyMuPDF apply_redactions → output PDF, description: writes content-stream-level removal; bypass via draw_rect would leak}
  stride:
    - {id: T-01-FAKE, category: Tampering / Information Disclosure, component: privacyguard/pii/pdf_adapter.apply_pii_redactions, severity: critical, disposition: mitigate, mitigation: strictly use page.add_redact_annot + page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS) + doc.save(garbage=4, deflate=True, clean=True); test_pdf_pii_redaction.py reverse-extraction asserts sensitive substrings absent; test_convergence.py scans main.py for draw_rect / fill= literal}
    - {id: T-01-LEAK-IMAGE, category: Information Disclosure, component: apply_redactions default images arg, severity: high, disposition: mitigate, mitigation: always pass images=fitz.PDF_REDACT_IMAGE_PIXELS (=2) explicitly; Pitfall 9; assert via reverse-extraction of an image-block-only PDF}
    - {id: T-01-LEAK-META, category: Information Disclosure, component: doc.save flags, severity: medium, disposition: mitigate, mitigation: garbage=4 + deflate=True + clean=True sweep metadata and orphaned objects after redaction}
    - {id: T-01-SILENT-NEG, category: Tampering / Repudiation, category_long: silent false negative, component: PIIEngine.detect validator gate, severity: high, disposition: mitigate, mitigation: validators only mark validator_passed=True when mod-11-2 / segment whitelist passes; MEDIUM tier only emitted for regex hits with explicit reason; test_pii_engine.py covers NEGATIVE cases (corrupted check digit, IoT segment, short ID)}
    - {id: T-01-NETWORK, category: Information Disclosure, component: privacyguard.pii import graph, severity: high, disposition: mitigate, mitigation: privacyguard.pii imports stdlib only; test_pii_offline.py monkey-patches socket.socket and asserts zero calls across 500-page scan; reviews for requests / urllib / httpx forbidden in privacyguard/pii/*.py}
    - {id: T-01-FIXTURE-PII, category: Information Disclosure / Compliance, component: tests/fixtures/fake_pii.py + tests/e2e/, severity: high, disposition: mitigate, mitigation: only Faker + mod-11-2 generator produces IDs; tests/samples/real_* gitignored; CI guard scans tests/ for 18-digit / 11-digit-with-MIIT-prefix literals (test_pii_engine.TestNoRealPiiInFixtures)}
    - {id: T-01-DATA-MISSING, category: Denial of Service, component: privacyguard/pii/data/rules.json, severity: medium, disposition: mitigate, mitigation: resource_path lookup; PyInstaller spec datas entry ensures file ships; engine fallback to hardcoded frozenset if JSON missing + warning print}
    - {id: T-01-LAZY-BREAK, category: Denial of Service / Import-time regression, component: privacyguard/__init__.py _LAZY_IMPORTS, severity: medium, disposition: mitigate, mitigation: _LAZY_IMPORTS + __getattr__ pattern; test_package_imports.py asserts privacyguard.pii.engine not in sys.modules after import privacyguard}
    - {id: T-01-SC, category: Supply Chain, component: package legitimacy gate, severity: low, disposition: accept, rationale: Phase 1 introduces zero new PyPI dependencies (PyMuPDF==1.27.1 + rapidocr-onnxruntime==1.2.3 already pinned and approved); RESEARCH §Package Legitimacy Audit closed}

assumption_delta_decision:
  - noun_now_primary: PIIHit (a generalized page-hit record)
  - decision: add-alongside
  - rationale: The phase adds a new sibling key `page_data[page]["pii"]` (D-04) without restructuring the existing two-key dict (`ocr` / `manual`). Existing `ocr` / `manual` slots remain QRectF lists consumed by current save loop and SinglePageCanvas; PIIHit is a separate dataclass consumed by new pii engine + new canvas render loop + new save loop branch.
  - what_would_force_promote: Phase 4 (Excel) or Phase 5 (Image) needs more hit-shape variants; then promote to a single `PageHit` record with optional `hit_kind: Literal["ocr","manual","pii","excel_cell","image_pixel"]` discriminator and a `coords` field union.
  - invariant_test_suggestion: tests/unit/test_convergence.py::TestPageDataShape asserts `page_data[i].keys() ⊇ {"ocr","manual","pii"}` and that adding a 4th key requires updating this test (a deliberate friction point).
---

<objective>
Wire the thin end-to-end Phase 1 spine — open synthetic PDF → PII engine detects one 18-digit ID card in text layer → PyMuPDF 真删除 → reverse-extraction proves the number is gone. This plan is the tracer; every later plan expands on top of this proven path.
</objective>

<purpose>
Phase 1 cannot ship without SAFE-01/SAFE-02 (真删除). The tracer proves the entire chain (validator → engine → adapter → output PDF) on the smallest possible input, so subsequent plans (worker wiring, UI, settings, OCR fallback) can expand without re-validating the safety floor.

**File count note (C6):** This plan lists 19 files in `files_modified`, above the 15-file soft threshold. This is the cost of bootstrapping the entire `privacyguard/pii/` subsystem (validators + dataclass + normalize + mask + engine + adapter + rules.json + test fixtures + privacyguard/__init__.py + 2 test extensions) inside a single tracer plan. Splitting this across two plans would force the tracer to span waves and lose its end-to-end verification contract.
</purpose>

<output>
- privacyguard/pii/ package skeleton (lazy _LAZY_IMPORTS mirroring privacyguard/workers/__init__.py:7-34)
- PIIHit frozen dataclass (D-05 locked field order)
- Validators (id_card.py GB 11643 mod-11-2 + phone_segment.py MIIT whitelist with IoT exclusion)
- Pure-Python detection pipeline (engine.py: TextUnit → PIIEngine.detect → List[PIIHit])
- PyMuPDF apply_pii_redactions (privacyguard/pii/pdf_adapter.py, exact pattern from main.py:12354-12385)
- rules.json data file via resource_path
- Faker fixture (tests/fixtures/fake_pii.py, OPS-05)
- Synthetic PDF builder (tests/e2e/create_pii_test_pdf.py)
- Reverse-extraction integration test (tests/unit/test_pdf_pii_redaction.py)
- privacyguard/__init__.py _LAZY_IMPORTS extended (PIIEngine / PIIHit / validate_18_id / is_mobile_segment / TextUnit)
- test_package_imports.py + test_convergence.py extended to enforce OPS-03 + convergence
</output>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-pdf/01-CONTEXT.md
@.planning/phases/01-pdf/01-PATTERNS.md
@.planning/phases/01-pdf/01-VALIDATION.md
@.planning/phases/01-pdf/01-RESEARCH.md
@.planning/phases/01-pdf/01-UI-SPEC.md
@.planning/phases/01-pdf/COVERAGE.md
@CLAUDE.md
@privacyguard/__init__.py
@privacyguard/workers/__init__.py
@privacyguard/ocr/mixed_pdf.py
@privacyguard/ocr/text_pdf.py
@main.py
@tests/unit/test_pdf_text_hit_dedup.py
@tests/unit/test_package_imports.py
@tests/unit/test_convergence.py
</context>

## Flagged Assumptions (spec-less probe)

The spec-less probe classified all 16 phase requirements as `unresolved / unclassified`. Per §A of `specless-probe-fallback.md`, no row is silently dropped. Every row is surfaced below with its chosen resolution. Where ROADMAP Success Criteria or `01-VALIDATION.md` Per-Task Verification Map supplies a defensible checkable criterion, it is also authored into `must_haves.truths` above.

| Req ID | Status | Resolution | Authored into must_haves.truths? |
|--------|--------|------------|----------------------------------|
| ENGINE-01 | surfaced | Authored: "synthetic PDF... returns exactly one PIIHit" | yes |
| ENGINE-02 | surfaced | Authored: "PIIHit dataclass fields in order entity_type, page_offset, page_length, page_rect, confidence_tier, source, mask_strategy" | yes |
| ENGINE-03 | surfaced | Authored: confidence_tier HIGH when validator_passed; classify_hit maps validator_passed × regex_matched → tier | yes |
| ENGINE-04 | surfaced | Authored: PIIEngine._engine_cache uses (entity_type, normalized) hash so repeated hits get same mask | yes |
| ENGINE-05 | surfaced | Authored: normalize_digits + map_flat_to_original reverse-map asserted in test_pii_engine.TestNormalization | yes |
| ENGINE-06 | surfaced | Authored: test_pii_engine.TestCrossBoundary exercises ID card split across three newline-joined lines | yes (in plan 01-02 expansion) |
| ENGINE-07 | surfaced | Authored: smoke TestLargeDocumentNoBlock passes 500-page synthetic scan in <60s with progress_signal emission | yes (in plan 01-02/01-03 expansion) |
| ENGINE-08 | surfaced | Authored: test_pii_offline.py monkey-patches socket.socket and asserts zero calls | yes |
| NUM-01 | surfaced | Authored: validate_18("53010219200508011X") == True; upgrade_15_to_18 standard sample | yes |
| NUM-02 | surfaced | Authored: validate_18 lowercase tail x accepted via last.upper() | yes |
| NUM-03 | surfaced | Authored: is_mobile_segment 199/192/166/162/165/167 True; 140/141/144 IoT False; **[ASSUMED]** MIIT 2026-Q1 baseline pending user final sign-off per D-11 | yes (with [ASSUMED] note) |
| FMT-01 | surfaced | Authored: PDF text layer + image block + full-page OCR all funnel into PIIEngine; verified in test_pdf_pii_pipeline.py | yes (in plan 01-02 expansion) |
| SAFE-01 | surfaced | Authored: test_pdf_pii_redaction reverse-extracts sensitive substrings; asserts apply_redactions(IMAGE_PIXELS) pattern | yes |
| SAFE-02 | surfaced | Authored: same reverse-extraction test asserts fitz.open(out).get_text() contains no original digits | yes |
| OPS-03 | surfaced | Authored: test_package_imports.py extension asserts privacyguard.pii.engine not in sys.modules after import privacyguard | yes |
| OPS-07 | surfaced | Authored: full 79/79 baseline regression command runs green after plan lands | yes |

No silent drops (§C equality holds: 16 surfaced = 16). NUM-03 carries `[ASSUMED]` flag for the MIIT 2026-Q1 segment baseline; this is the only conditional assumption requiring explicit user sign-off before Phase 1 ships (D-11).

<tasks>

<task type="tracer" tdd="true">
  <name>Tracer — RED reverse-extraction test (fail without implementation)</name>
  <files>
    - tests/fixtures/fake_pii.py
    - tests/e2e/create_pii_test_pdf.py
    - tests/unit/test_pdf_pii_redaction.py
  </files>
  <read_first>
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 1019-1090 — fake_pii.py + create_pii_test_pdf.py patterns)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 1199-1248 — test_pdf_pii_redaction.py reverse-extraction pattern)
    - .planning/phases/01-pdf/01-VALIDATION.md (lines 41-65 — Per-Task Verification Map for SAFE-01/02)
    - tests/unit/test_pdf_text_hit_dedup.py (FakePage / FakeRect style, lines 1-40)
    - tests/e2e/create_test_pdf.py (existing reportlab-based test PDF generator)
  </read_first>
  <action>
    Write three test files that exercise the END-TO-END spine (synthetic PDF → PIIEngine → pdf_adapter.apply_pii_redactions → fitz reverse-extraction asserts sensitive substrings absent). Do NOT implement production code in this task; the test must FAIL when run.

    In `tests/fixtures/fake_pii.py`:
    - Define `fake_id_card()` that uses `random.randint` (digits 0-9, body17) loop until `validate_18(body17 + compute_check_digit(body17))` returns True (do not depend on Faker PyPI package per Environment Availability).
    - Define `fake_phone(seg='138')` returning 11 digits with seg prefix.
    - Define `fake_phone_invalid()` returning `140` + 8 random digits (must be rejected by is_mobile_segment per NUM-03 IoT exclusion).
    - Import validators from `privacyguard.pii.validators.id_card` (this triggers lazy import).

    In `tests/e2e/create_pii_test_pdf.py`:
    - Mirror `tests/e2e/create_test_pdf.py` style but use PyMuPDF `fitz.open()` + `page.insert_text((x, y), text, fontsize=14)` (no reportlab dependency).
    - `create_pii_test_pdf(output_path)` inserts text "测试样本 身份证 {fake_id_card()} 手机 {fake_phone()}" at (50, 100) and "跨行样本\n110101\n19900307\n8811" at (50, 130) (the second one is for ENGINE-06 cross-line and may be removed in 01-01 if scope tight — see Plan 01-02 expansion).
    - Returns the output_path.

    In `tests/unit/test_pdf_pii_redaction.py`:
    - Class `TestPdfPiiRedaction.test_redacted_text_not_extractable`: builds a PDF with `fake_id_card()` + `fake_phone()`, opens it with `fitz.open`, iterates pages building `pii_engine.detect(unit)`, calls `apply_pii_redactions(in_pdf, out_pdf, rects_per_page)`, then `fitz.open(out_pdf).get_text()` and asserts `secret_id[:10]` NOT in out_text + `secret_phone[:7]` NOT in out_text. This is the SAFE-02 reverse-extraction assertion. Add a positive pre-assertion: `assert len(pdf_hits) >= 2` BEFORE calling `apply_pii_redactions` so that an empty-detect run fails loudly (B3 — the test must not be vacuously green against an implementation that returns zero hits).
    - **B3 scope decision:** the image-pixels-only / scanned-PDF reverse-extraction test is OUT OF SCOPE for the 01-01 tracer and is moved to Plan 01-03 Task 3 (`tests/unit/test_pdf_pii_pipeline.py::test_image_block_pdf_full_pipeline`). Rationale: an image-only PDF has empty `page.get_text()` so the 01-01 tracer's text-layer detect path produces zero hits, and a zero-hit reverse-extraction trivially passes — making the test green against a broken implementation. The image-pixels case requires the full-page OCR path (collect_full_page_ocr_hits from Plan 01-03 Task 1) to produce at least one detect hit from pixel data before redaction, then reverse-extraction can be a meaningful assertion. Plan 01-01 tracer covers the text-layer path only.
    - Both tests use `tempfile.TemporaryDirectory()` to avoid leaking fixture files; `fake_*` only — no hard-coded ID strings.

    This task writes NO production code under `privacyguard/pii/`; running `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` after this task must produce `ModuleNotFoundError: No module named 'privacyguard.pii'` (RED state).
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_pdf_pii_redaction -v 2>&1 | grep -E "(ModuleNotFoundError|ImportError|FAIL|ERROR)" | head -5</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` fails with `ModuleNotFoundError: No module named 'privacyguard.pii'` (RED state confirmed).
    - `python3 -c "from tests.fixtures.fake_pii import fake_id_card; print(fake_id_card())"` prints an 18-digit string (sanity, even if validation import fails — wrap in try/except in test).
    - `python3 -m compileall -q tests/fixtures/fake_pii.py tests/e2e/create_pii_test_pdf.py tests/unit/test_pdf_pii_redaction.py` exits 0 (syntax-only green for new test files).
    - The test file imports `from privacyguard.pii.engine import PIIEngine` and `from privacyguard.pii.pdf_adapter import apply_pii_redactions` — these imports must currently fail (proving the test is RED for the right reason).
  </acceptance_criteria>
  <done>
    All three test files exist on disk; running them produces an import failure or assertion error (RED state); the test contract is in place so subsequent Task 2 has a verifiable green target.
  </done>
  <reversibility>rating="reversible" rationale="Test files only; deletion reverts cleanly."</reversibility>
</task>

<task type="tracer" tdd="true">
  <name>Tracer — GREEN implementation (production spine wired end-to-end)</name>
  <files>
    - privacyguard/pii/__init__.py
    - privacyguard/pii/hits.py
    - privacyguard/pii/validators/__init__.py
    - privacyguard/pii/validators/id_card.py
    - privacyguard/pii/validators/phone_segment.py
    - privacyguard/pii/regex_patterns.py
    - privacyguard/pii/normalize.py
    - privacyguard/pii/confidence.py
    - privacyguard/pii/mask.py
    - privacyguard/pii/overlap.py
    - privacyguard/pii/engine.py
    - privacyguard/pii/pdf_adapter.py
    - privacyguard/pii/data/rules.json
  </files>
  <read_first>
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 52-186 — package lazy-init template mirroring privacyguard/workers/__init__.py:7-34)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 98-135 — PIIHit frozen dataclass with D-05 field order)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 189-238 — id_card.py validate_18 / validate_15 / upgrade_15_to_18 with Pitfall 3 WEIGHTS + MAPPING parity)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 244-286 — phone_segment.py frozenset with 14X IoT exclusion per NUM-03)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 292-320 — regex_patterns.py compile-only pattern with re.IGNORECASE)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 324-374 — normalize.py normalize_digits + flatten_for_match + map_flat_to_original)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 378-401 — confidence.py classify_hit HIGH/MEDIUM/LOW)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 405-434 — mask.py partial_mask_id_card / partial_mask_phone)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 438-462 — overlap.py resolve dedup)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 466-535 — engine.py PIIEngine.detect pipeline)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 541-589 — pdf_adapter.py apply_pii_redactions mirroring main.py:12354-12385)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 595-622 — rules.json schema + resource_path usage per D-10)
    - privacyguard/utils/security.py:110 (resource_path for PyInstaller compatibility)
    - main.py:12354-12385 (PyMuPDF add_redact_annot + apply_redactions(IMAGE_PIXELS) + garbage=4 production-verified call pattern)
  </read_first>
  <action>
    Implement the production spine that makes Task 1's reverse-extraction test pass (GREEN). Follow the exact templates cited in PATTERNS.md line ranges; do NOT improvise names or signatures.

    **privacyguard/pii/__init__.py** — Mirror `privacyguard/workers/__init__.py:7-34` (the `_LAZY_IMPORTS` + `__getattr__` + `__dir__` pattern). Top-level module docstring: "PrivacyGuard PII 自动识别子系统（v38.x Phase 1）". `__all__` exposes: PIIEngine, PIIHit, TextUnit, validate_18_id, validate_15_id, upgrade_15_to_18, compute_check_digit, is_mobile_segment, apply_pii_redactions, collect_pii_rects, PHONE_PERSONAL_PREFIX_3, PHONE_EXCLUDED_PREFIX_3, PHONE_EXCLUDED_PREFIX_4. `_LAZY_IMPORTS` maps each name to `(module_path, attr_name)` tuples. NO top-level `from privacyguard.pii.engine import PIIEngine` — OPS-03.

    **privacyguard/pii/hits.py** — `PIIHit` is `@dataclass(frozen=True)`. The 7 D-05-locked field NAMES appear in the D-05 order; default values are placed on the trailing fields to satisfy Python's "non-default argument cannot follow default argument" rule (B4 fatal — `TypeError: non-default argument 'source' follows default argument 'confidence_tier'` was confirmed by live construction). The chosen layout (option (a) — apply defaults to the trailing fields) is:

    ```python
    @dataclass(frozen=True)
    class PIIHit:
        entity_type: str                                                              # required (D-05 1)
        page_offset: int                                                              # required (D-05 2)
        page_length: int                                                              # required (D-05 3)
        page_rect: Tuple[float, float, float, float]                                  # required (D-05 4)
        confidence_tier: str = "HIGH"                                                 # default "HIGH" (D-05 5; Claude's Discretion)
        source: str = "text"                                                          # default "text" (D-05 6)
        mask_strategy: str = ""                                                       # default "" (D-05 7; engine populates)
        normalized: str = ""                                                          # default ""
        validator_passed: bool = True                                                 # default True
    ```

    **B4 resolution rationale:** Python's `@dataclass` requires that once a default appears, ALL subsequent fields have defaults. Putting a default on `confidence_tier` (the 5th field) while `source` and `mask_strategy` remained required was a syntax error at class-definition time. The fix gives all three trailing D-05 fields defaults that match their natural "engine populates this" meaning (`confidence_tier` defaults to HIGH per Claude's Discretion, `source` defaults to "text" since OCR paths in Phase 1 only matter when the engine is called via the worker, `mask_strategy` defaults to empty string since callers using the dataclass directly may not have computed the mask yet). This keeps the 7 field NAMES in D-05 order (locked) while satisfying Python's dataclass rule. `test_field_order_locked` in 01-02 still passes (names + order intact); `test_default_confidence_tier_is_high` still passes (constructing with only the 4 required fields yields `confidence_tier == "HIGH"`). Use `Tuple` from typing (NOT `tuple` lowercase — keeps frozen hashability strict). Also define `TextUnit` dataclass (page_index: int, text: str, source: str) and `ConfidenceTier = Literal["HIGH","MEDIUM","LOW"]`. **Acceptance criterion (B4 import smoke test):** `python3 -c "from privacyguard.pii.hits import PIIHit; h = PIIHit('CN_ID_CARD', 0, 18, (0.0, 0.0, 18.0, 1.0)); print(h.confidence_tier)"` prints `HIGH` without `TypeError`. This guards against the dataclass-definition regression class.

    **privacyguard/pii/validators/__init__.py** — Same lazy `_LAZY_IMPORTS` pattern; `__all__` = ["validate_18_id","validate_15_id","upgrade_15_to_18","compute_check_digit","is_mobile_segment","PHONE_PERSONAL_PREFIX_3","PHONE_EXCLUDED_PREFIX_3","PHONE_EXCLUDED_PREFIX_4"]. Maps to id_card.py + phone_segment.py.

    **privacyguard/pii/validators/id_card.py** — `WEIGHTS: Final = (7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2)`, `MAPPING: Final = ('1','0','X','9','8','7','6','5','4','3','2')`. Functions: `compute_check_digit(body17: str) -> str`, `validate_18(id_str: str) -> bool` (NUM-01 + NUM-02 via `last.upper()`), `upgrade_15_to_18(id15: str) -> str`, `validate_15(id_str: str) -> bool`, **`is_valid_admin_division_prefix_2(prefix2: str) -> bool`** (NEW — B1 second gate), **`is_real_calendar_date(yy: int, mm: int, dd: int) -> bool`** (NEW — B1 second gate).

    **B1 second gate for 15-digit path:** A bare 15-digit run whose upgrade-to-18 passes mod-11-2 is NOT enough — that contract accepts order numbers, tracking numbers, and serial numbers whose embedded digits happen to satisfy mod-11-2. The 15-digit validator must additionally enforce (a) `body17[0:2]` (the 行政区划码 province prefix after upgrade) is in the valid province set `{11,12,13,14,15,21,22,23,31,32,33,34,35,36,37,41,42,43,44,45,46,50,51,52,53,54,61,62,63,64,65,71,81,82}` (GB/T 2260 historical 1980s-1990s mapping; if first 2 digits are 00 or 90+ the run is rejected); (b) the embedded 6-digit birth date `YYMMDD` in `body17[6:12]` is a real calendar date (month 1-12, day 1 to days_in_month(yy+1900, mm)). The 18-digit path does NOT need this gate (GB 11643 already covers province prefix + date in the issued ID itself; the gate is specifically needed for the 15-digit synthetic-upgrade path).

    `validate_15(id_str)` calls `upgrade_15_to_18`; if empty returned, return False; then check `is_valid_admin_division_prefix_2(upgraded[:2])` — if False, return False; then check `is_real_calendar_date(int(upgraded[8:10]), int(upgraded[10:12]), int(upgraded[12:14]))` — if False, return False; then return `validate_18(upgraded)`. `validate_18` keeps its existing 18-digit contract (mod-11-2 + uppercase X). NOTE: `MAPPING[0] == '1'` (NOT `'0'` — Pitfall 3 reverse parity).

    **I1 — residual false-positive guard for 15-digit:** even with the B1 second gate (valid province prefix + real calendar date), a 15-digit run that coincidentally satisfies both may still be a business-data SKU (e.g. an order number or warehouse ID starting with `42010619801301001`). Mitigation: in `PIIEngine._check_id_card` (NOT in `validate_15` — the validator stays binary True/False), if the candidate was a 15-digit run AND has NO context anchor (no `身份证` / `ID` / `公民身份号码` / `证件` keyword within ±20 characters in the page text), demote `confidence_tier` from `"HIGH"` to `"MEDIUM"`. This routes bare 15-digit matches through the `require_confirmation=true` path or visual review rather than auto-redacting. Phase 1 ships this demotion; Phase 2 may re-promote to HIGH when the FP rate is measured on real documents. This residual FP rate is recorded as a known Phase-1 limitation in `must_haves.truths` §"Known Limitations" below.

    **privacyguard/pii/validators/phone_segment.py** — `PHONE_PERSONAL_PREFIX_3` frozenset (NUM-03 personal mobile segments per 2026-Q1 MIIT baseline, `[ASSUMED]` pending user sign-off), `PHONE_EXCLUDED_PREFIX_3` (140/141/144/145/146/147/148/149 IoT + data card), `PHONE_EXCLUDED_PREFIX_4` (1349/1440/1740/1741 satellite). `is_mobile_segment(phone11: str) -> bool` rejects non-digit, wrong length, non-`1`-leading, excluded prefix 4 first then prefix 3, then requires prefix 3 in personal whitelist.

    **privacyguard/pii/regex_patterns.py** — `_ID_18_RE = re.compile(r"(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)")`; `_ID_15_RE = re.compile(r"(?<!\d)([1-9]\d{14})(?!\d)")`; `_PHONE_11_RE = re.compile(r"(?<!\d)(1\d{10})(?!\d)")`. `iter_candidate_strings(text)` yields `(cand, span, entity_hint)` tuples for each regex.

    **privacyguard/pii/normalize.py** — `normalize_digits(text)` translates `'０１２３４５６７８９'` → `'0123456789'` via `str.maketrans`, then strips `[- / 全角空格]` via regex `r'[-\s　]+'`. `flatten_for_match(text)` strips all `[\s\n\r\t　-]+` (ENGINE-06 cross-line). `map_flat_to_original(flat_text, flat_span, original_text)` walks character-by-character mapping flat index back to original index, accounting for separator + fullwidth translation (ENGINE-05 offset back-mapping).

    **privacyguard/pii/confidence.py** — `ConfidenceTier = Literal["HIGH","MEDIUM","LOW"]`; `classify_hit(validator_passed, regex_matched, source) -> ConfidenceTier` returns HIGH only when validator_passed AND regex_matched; MEDIUM when regex_matched only; LOW otherwise (ENGINE-03).

    **privacyguard/pii/mask.py** — `partial_mask_id_card(normalized18)`: returns `normalized18[:6] + '*' * 8 + normalized18[14:]` (e.g. `"110101********8811"`). `partial_mask_phone(normalized11)`: returns `normalized11[:3] + '*' * 4 + normalized11[7:]` (e.g. `"138****5678"`). `mask_for_entity(entity_type, normalized_text)` dispatches by entity_type; default is `'*' * len(normalized_text)`.

    **privacyguard/pii/overlap.py** — `resolve(hits: List[PIIHit]) -> List[PIIHit]` dedups by `(page_offset, page_length)`; prefers `validator_passed=True` over False; returns sorted by `(page_offset, page_length)`.

    **privacyguard/pii/engine.py** — `TextUnit(page_index, text, source)` dataclass (re-export of hits.TextUnit for ergonomic import). `PIIEngine` class:
    - `__init__(self, rules_data=None)`: reads `privacyguard.utils.security.resource_path("privacyguard/pii/data/rules.json")` if rules_data is None; falls back to `{}` if file missing (with `print("[PII WARN] rules.json 缺失或损坏，使用内置默认")`); caches nothing beyond the rules_data dict.
    - `detect(self, unit: TextUnit) -> List[PIIHit]`: flatten text → `iter_candidate_strings(flat)` → for each candidate, call `_check_id_card` or `_check_phone` which returns PIIHit or None (None = validator_failed). Compute `page_offset` via `map_flat_to_original`, compute `page_rect` via `page.search_for(normalized_text)` (uses fitz page-side; for OCR source it uses passed-in rect mapping). Apply `mask_for_entity`. Cache `(entity_type, normalized) -> mask_strategy` for ENGINE-04 consistency. Return `resolve(hits)`.
    - Internal `_mask_cache: Dict[Tuple[str,str], str] = {}` per-instance.
    - No fitz import at module top-level (lazy inside detect path) — actually import fitz is fine since this is a desktop app, but PIIEngine is pure Python without PyQt6 / QThread import.

    **privacyguard/pii/pdf_adapter.py** — `collect_pii_rects(page_data_for_doc)`: walks `page_data.items()`, for each hit in `data.get("pii", [])` extracts `r = hit.page_rect` (4-tuple) and yields `(page_idx, fitz.Rect(r[0], r[1], r[0]+r[2], r[1]+r[3]))`. `apply_pii_redactions(pdf_in, pdf_out, rects_per_page, fill_color=(0,0,0))`: opens with `fitz.open(pdf_in)`, for each page adds `page.add_redact_annot(rect)` + `annot.set_colors(stroke=fill_color, fill=fill_color)` + `annot.update()`; then `page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)` (NOT default 0 — Pitfall 9); then `page.delete_annot(annot)` for any leftover annotation; then `doc.save(pdf_out, garbage=4, deflate=True, clean=True)`. Wrap in `try/finally` to ensure `doc.close()`. EXACT pattern from main.py:12354-12385.

    **privacyguard/pii/data/rules.json** — JSON schema: `{ "phone_segment": { "personal_prefix_3": [list of 3-digit strings], "excluded_prefix_3": ["140","141","144","145","146","147","148","149"], "excluded_prefix_4": ["1349","1440","1740","1741"], "source": "MIIT 2017-08 / 2019-12 号段核发公告 + 工信部公开物联网号段清单", "last_verified": "2026-Q1", "next_review": "2026-Q3" }, "id_card": { "weights": [7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2], "mapping": ["1","0","X","9","8","7","6","5","4","3","2"], "standard": "GB 11643-1999" } }`. The `personal_prefix_3` list must contain all the segments enumerated in PATTERNS.md lines 256-264.

    After all files exist, run `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` and confirm GREEN (test passes). Then run the full 79/79 baseline:
    `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence -v` and confirm 79 + new tests all green.
  </action>
  <verify>
    <automated>python3 -m compileall -q privacyguard/pii tests && python3 -m unittest tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_text_hit_dedup tests.unit.test_package_imports tests.unit.test_convergence tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety -v 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` shows `OK` for both test methods (test_redacted_text_not_extractable + test_image_pixels_destroyed).
    - Reverse-extraction assertion holds: `assertNotIn(secret_id[:10], out_text)` and `assertNotIn(secret_phone[:7], out_text)` both pass.
    - `python3 -m unittest tests.unit.test_pdf_text_hit_dedup -v` remains green (no regression in existing OCR text hit dedup).
    - `python3 -m unittest tests.unit.test_mixed_pdf_ocr -v` remains green (no regression in image-block OCR coordinate conversion).
    - `python3 -m unittest tests.unit.test_package_imports -v` remains green (lazy-load contract preserved — Phase 1 module additions don't eagerly load).
    - `python3 -m unittest tests.unit.test_convergence -v` remains green (no inline reimplementation).
    - `python3 -m compileall -q privacyguard/pii` exits 0.
    - The compiled `privacyguard/pii/pdf_adapter.pyc` references `fitz.PDF_REDACT_IMAGE_PIXELS` (Pitfall 9 mitigation, not default `PDF_REDACT_IMAGE_NONE = 0`).
  </acceptance_criteria>
  <done>
    Tracer verified end-to-end: synthetic PDF containing a Faker-generated 18-digit ID card + 11-digit mobile phone → PIIEngine.detect returns one PIIHit per entity → pdf_adapter.apply_pii_redactions writes an output PDF whose fitz.get_text() does NOT contain the original digits (SAFE-01 + SAFE-02). All 79 baseline tests still pass. Privacy package is fully lazy-loaded.
  </done>
  <reversibility>rating="costly" rationale="Introduces the privacyguard/pii/ package boundary (D-02), PIIHit field schema (D-05 one-way), and page_data[page]["pii"] contract (D-04 one-way). Reverting requires coordinated changes in main.py + workers + tests; do not revert mid-phase.</reversibility>
</task>

<task type="auto">
  <name>Wire privacyguard/__init__.py exports + extend lazy-load + convergence tests</name>
  <files>
    - privacyguard/__init__.py
    - tests/unit/test_package_imports.py
    - tests/unit/test_convergence.py
  </files>
  <read_first>
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 691-728 — privacyguard/__init__.py _LAZY_IMPORTS extension)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 1295-1345 — test_package_imports.py extension for OPS-03)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 1349-1386 — test_convergence.py TestPiiConvergence extension)
    - privacyguard/__init__.py (current _LAZY_IMPORTS at lines 61-68)
    - tests/unit/test_package_imports.py (lines 10-39 for pattern reference)
    - tests/unit/test_convergence.py (lines 16-33 for TestImageMergeWorkerConvergence pattern)
  </read_first>
  <action>
    Wire the new PII symbols into the top-level privacyguard package lazy table and extend the regression tests.

    **privacyguard/__init__.py**:
    - Append to `__all__` (after line 58): `'PIIEngine'`, `'PIIHit'`, `'TextUnit'`, `'validate_18_id'`, `'validate_15_id'`, `'is_mobile_segment'`, `'apply_pii_redactions'`, `'collect_pii_rects'`.
    - Append to `_LAZY_IMPORTS` (after line 67):
      - `'PIIEngine': ('privacyguard.pii.engine', 'PIIEngine')`
      - `'PIIHit': ('privacyguard.pii.hits', 'PIIHit')`
      - `'TextUnit': ('privacyguard.pii.hits', 'TextUnit')`
      - `'validate_18_id': ('privacyguard.pii.validators', 'validate_18_id')`
      - `'validate_15_id': ('privacyguard.pii.validators', 'validate_15_id')`
      - `'is_mobile_segment': ('privacyguard.pii.validators', 'is_mobile_segment')`
      - `'apply_pii_redactions': ('privacyguard.pii.pdf_adapter', 'apply_pii_redactions')`
      - `'collect_pii_rects': ('privacyguard.pii.pdf_adapter', 'collect_pii_rects')`
    - The existing `__getattr__` and `__dir__` already handle these correctly; no other changes needed.

    **tests/unit/test_package_imports.py**:
    - Add a new method `test_import_privacyguard_does_not_load_pii_engine` inside `TestPrivacyGuardImports`:
      - Snapshot current `sys.modules` for `privacyguard.*`.
      - Pop them all.
      - `importlib.import_module("privacyguard")`.
      - Touch one already-defined export (`module.validate_safe_path`).
      - Assert `'privacyguard.pii.engine' not in sys.modules`.
      - Restore the original sys.modules snapshot in `finally`.
    - Add another method `test_pii_engine_loads_on_demand`: snapshot, pop, `importlib.import_module("privacyguard")`, then access `module.PIIEngine` (touches _LAZY_IMPORTS path), then assert `'privacyguard.pii.engine' in sys.modules` (lazy load worked).
    - Add `test_pii_engine_lazy_under_rapidocr_block`: combine the rapidocr-blocked `__import__` patch with the pii import; assert no `rapidocr_onnxruntime` import is required (proves privacyguard.pii has no eager OCR dependency).

    **tests/unit/test_convergence.py**:
    - Add new class `TestPiiConvergence(unittest.TestCase)` with three methods:
      - `test_main_py_does_not_inline_pii_detection`: read main.py source; assert `"def detect_pii(self)" not in source`, `"def validate_id_card(" not in source`, `"class PIIHit" not in source` (no inline implementations).
      - `test_main_py_imports_pii_via_privacyguard_package`: read main.py source; assert `"from privacyguard.pii" in source` OR `"from privacyguard import PIIEngine" in source` OR `"from privacyguard import PIIHit" in source` (consumers go through the lazy entry, not direct module import).
      - `test_pii_package_has_no_qt_dependency`: read all `privacyguard/pii/*.py` files (excluding `__init__.py` and `data/`); assert none of them import `PyQt6` / `PyQt5` / `QThread` / `QObject` (engine stays pure Python per D-02).

    After all edits, run `python3 -m unittest tests.unit.test_package_imports tests.unit.test_convergence -v` to verify the new test methods pass. Then run the full baseline to confirm no regression.
  </action>
  <verify>
    <automated>python3 -m compileall -q privacyguard tests && python3 -m unittest tests.unit.test_package_imports tests.unit.test_convergence tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -c "from privacyguard import PIIEngine, PIIHit, TextUnit, validate_18_id, is_mobile_segment, apply_pii_redactions, collect_pii_rects; print('OK')"` prints `OK`.
    - `python3 -c "import privacyguard, sys; assert 'privacyguard.pii.engine' not in sys.modules; privacyguard.validate_safe_path; assert 'privacyguard.pii.engine' not in sys.modules; print('OK')"` prints `OK` (OPS-03 still enforced).
    - `python3 -c "import privacyguard; from privacyguard import PIIEngine; import sys; assert 'privacyguard.pii.engine' in sys.modules; print('OK')"` prints `OK` (lazy load works).
    - `python3 -m unittest tests.unit.test_package_imports -v` shows all four test methods green (the existing one + the three new ones).
    - `python3 -m unittest tests.unit.test_convergence -v` shows the existing TestImageMergeWorkerConvergence / TestWordWorkerConvergence / TestDocConverterConvergence / TestVersionFallbackAlignment tests still green, plus the new TestPiiConvergence class with all three methods green.
    - The 79/79 baseline remains at 79/79 + 2 new reverse-extraction tests + ≥1 new lazy-load test + ≥3 new convergence tests, all green.
  </acceptance_criteria>
  <done>
    privacyguard top-level package exposes PIIEngine / PIIHit / TextUnit / validators / adapter functions through the existing _LAZY_IMPORTS mechanism; importing privacyguard does NOT eagerly load privacyguard.pii.engine; main.py contains no inline PII implementations; the lazy-load contract and convergence contract are codified as automated regression tests. Tracer phase complete.
  </done>
  <reversibility>rating="one-way" rationale="privacyguard/__init__.py _LAZY_IMPORTS additions are referenced by all later plans (01-02..01-05) and by the PII engine export surface. Renaming the export names would force synchronized edits across the package + 4 plans of consumers. Lock the names from this point forward.</reversibility>
</task>

</tasks>

## Artifacts this phase produces

The phase-level artifact list is distributed across all three plans. Plan 01-01 produces:

**Public dataclasses / classes / functions (created in 01-01):**
- `privacyguard.pii.hits.PIIHit` — `@dataclass(frozen=True)` with 7 named fields in D-05 order: `entity_type`, `page_offset`, `page_length`, `page_rect`, `confidence_tier`, `source`, `mask_strategy`; defaults `confidence_tier="HIGH"`, `normalized=""`, `validator_passed=True` (B4 resolution).
- `privacyguard.pii.hits.TextUnit` — `(page_index: int, text: str, source: str)` dataclass.
- `privacyguard.pii.hits.ConfidenceTier` — `Literal["HIGH","MEDIUM","LOW"]`.
- `privacyguard.pii.engine.TextUnit` — re-export from hits.
- `privacyguard.pii.engine.PIIEngine` — class with `__init__(rules_data=None)` + `detect(unit: TextUnit) -> List[PIIHit]` + classmethod `rules_version(rules_data)`.
- `privacyguard.pii.engine.PIIEngine.last_error: Optional[str]` — surfaced exception capture (W1).
- `privacyguard.pii.validators.id_card.compute_check_digit / validate_18 / validate_15 / upgrade_15_to_18 / is_valid_admin_division_prefix_2 / is_real_calendar_date`.
- `privacyguard.pii.validators.phone_segment.is_mobile_segment / PHONE_PERSONAL_PREFIX_3 / PHONE_EXCLUDED_PREFIX_3 / PHONE_EXCLUDED_PREFIX_4`.
- `privacyguard.pii.regex_patterns.iter_candidate_strings` + private `_ID_18_RE / _ID_15_RE / _PHONE_11_RE`.
- `privacyguard.pii.normalize.normalize_digits / flatten_for_match / map_flat_to_original`.
- `privacyguard.pii.confidence.classify_hit`.
- `privacyguard.pii.mask.partial_mask_id_card / partial_mask_phone / mask_for_entity`.
- `privacyguard.pii.overlap.resolve`.
- `privacyguard.pii.pdf_adapter.collect_pii_rects / apply_pii_redactions`.
- `privacyguard.__init__` lazy exports: `PIIEngine`, `PIIHit`, `TextUnit`, `validate_18_id`, `validate_15_id`, `is_mobile_segment`, `apply_pii_redactions`, `collect_pii_rects`.

**New files (created in 01-01):**
- `privacyguard/pii/__init__.py`, `privacyguard/pii/hits.py`, `privacyguard/pii/validators/__init__.py`, `privacyguard/pii/validators/id_card.py`, `privacyguard/pii/validators/phone_segment.py`, `privacyguard/pii/regex_patterns.py`, `privacyguard/pii/normalize.py`, `privacyguard/pii/confidence.py`, `privacyguard/pii/mask.py`, `privacyguard/pii/overlap.py`, `privacyguard/pii/engine.py`, `privacyguard/pii/pdf_adapter.py`, `privacyguard/pii/data/rules.json`.
- `tests/fixtures/fake_pii.py`, `tests/e2e/create_pii_test_pdf.py`.
- `tests/unit/test_pdf_pii_redaction.py` (text-layer reverse-extraction only; image-layer in 01-03 per B3).

**Modified files (in 01-01):**
- `privacyguard/__init__.py` — `_LAZY_IMPORTS` extended.
- `tests/unit/test_package_imports.py` — three new methods.
- `tests/unit/test_convergence.py` — `TestPiiConvergence` class.

**Cross-plan artifacts (NOT produced in 01-01):** see `must_haves.artifacts` §"Cross-plan deliverables" above for the full reference index; those land in Plans 01-02 and 01-03.

**User sign-off gate (C3 — NUM-03 [ASSUMED]):** Before any production build that ships to a user, the user MUST confirm the MIIT 2026-Q1 baseline in `privacyguard/pii/data/rules.json` is acceptable. Specifically:
- `personal_prefix_3` list (the 50+ segment entries per RESEARCH §Pitfall 4 / PATTERNS.md lines 256-264).
- `excluded_prefix_3` (140/141/144/145/146/147/148/149 IoT + data card).
- `excluded_prefix_4` (1349/1440/1740/1741 satellite).
- `next_review` field (`"2026-Q3"`).
This is a Phase-1 pre-ship checklist item, gated by `/gsd-verify-work` Phase 1 UAT. Until confirmed, the field carries `[ASSUMED]` in all plans. Plan 01-03 Task 3 ships a one-line reminder in the verification SUMMARY: "NUM-03 [ASSUMED] MIIT baseline requires user sign-off before tagged release".

---

<verification>
After all three tasks complete, the following command sequence must return all-green:

```
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
      tests.unit.test_pdf_pii_redaction \
      -v
```

Expected: ≥79 baseline tests + ≥2 new tests = all green. SAFE-01/02 verified via the two new reverse-extraction tests. OPS-03 verified via the extended test_package_imports. Convergence verified via the extended test_convergence. Engine smoke runnable via `python3 -c "from privacyguard import PIIEngine; e = PIIEngine(); from privacyguard.pii.hits import TextUnit; print(e.detect(TextUnit(0, '张三 53010219200508011X 已婚', 'text')))"`.
</verification>

<success_criteria>
- Tracer proven: opening a synthetic PDF containing one 18-digit Chinese ID card triggers PII detection, PyMuPDF 真删除, and reverse-extraction confirms the digits are no longer in the output PDF.
- Validator spine (NUM-01 / NUM-02 / NUM-03) proven: mod-11-2 + 15→18 upgrade + case-insensitive X + MIIT whitelist + 14X IoT exclusion.
- PIIHit dataclass with D-05 locked field order exists, frozen, used by engine + adapter + UI consumption.
- privacyguard.pii package is lazy-loaded; `import privacyguard` does not pull in privacyguard.pii.engine.
- main.py contains no inline PIIHit / detect_pii / validate_id_card; convergence test enforces this.
- Existing 79/79 baseline remains green; no regression in test_mixed_pdf_ocr / test_pdf_text_hit_dedup / test_package_imports / test_convergence.
- All 16 requirement IDs are accounted for in either this plan or its successors; no requirement is silently dropped.
</success_criteria>

<output>
Create `.planning/phases/01-pdf/01-01-tracer-SUMMARY.md` when done. Commit message: `feat(01-01): PII detection spine + reverse-extraction tracer`.
</output>