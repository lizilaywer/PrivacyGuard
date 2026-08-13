---
phase: 02-pdf
plan: 01
slug: tracer
type: execute
wave: 1
depends_on: []
files_modified:
  - privacyguard/pii/validators/uscc.py
  - privacyguard/pii/validators/__init__.py
  - privacyguard/pii/validators/bank_card.py
  - privacyguard/pii/validators/email.py
  - privacyguard/pii/regex_patterns.py
  - privacyguard/pii/mask.py
  - privacyguard/pii/engine.py
  - privacyguard/pii/pdf_adapter.py
  - privacyguard/pii/data/rules.json
  - privacyguard/pii/__init__.py
  - privacyguard/__init__.py
  - tests/fixtures/fake_pii.py
  - tests/unit/test_pii_validators.py
  - tests/unit/test_pii_engine.py
  - tests/unit/test_pdf_pii_redaction.py
  - tests/unit/test_pdf_metadata_cleared.py
  - tests/unit/test_package_imports.py
  - tests/unit/test_convergence.py
autonomous: true
requirements:
  - FIN-01
  - MASK-01
  - SAFE-03
  - OPS-03
  - OPS-07
user_setup: []

estimate:
  tokens: 95000
  raw_tokens: 47500
  tasks: 5
  confidence: medium

must_haves:
  truths:
    - A synthetic PDF containing one valid 18-character USCC (e.g. 91110000600037341L) → `PIIEngine.detect` returns exactly one PIIHit with entity_type="CN_USCC", confidence_tier="HIGH", validator_passed=True, and mask_strategy starting with the first 6 characters of the USCC followed by asterisks.
    - `privacyguard.pii.pdf_adapter.write_partial_masks(doc, page_idx, hits, mode="partial")` after PyMuPDF真删除 writes a partial mask text string (e.g. "911100********XXXX") into the output PDF that is extractable by `fitz.open(out).get_text()`, while the original 18-character USCC characters are NOT extractable from the same output (SAFE-02 reverse-extraction).
    - `privacyguard.pii.pdf_adapter.clear_pdf_metadata(doc)` writes all 5 fields (title/author/subject/producer/creator) to empty string "" — verified by `fitz.open(out).metadata["title"] == ""` etc.; `CreationDate` / `ModDate` are NOT cleared (D-14 only 5 fields).
    - A USCC whose category code (first character) is "Z" (not in the 6-character whitelist {"1","5","9","Y","A","N"}) is rejected even if the mod-31-3 check digit passes (FIN-01 + D-06 category-code gate).
    - `import privacyguard` does NOT load `privacyguard.pii.validators.uscc`, `privacyguard.pii.validators.bank_card`, or `privacyguard.pii.validators.email` into sys.modules (OPS-03 lazy-load discipline extends to the 6 new validators).
    - Existing 79/79 baseline + Phase 1 16 new tests remain green (test_mixed_pdf_ocr / test_path_validation / test_ocr_api / test_package_imports / test_pdf_text_hit_dedup / test_app_config / test_word_replace_rules / test_batch_word_replace / test_config_alignment / test_fstring_safety / test_convergence + Phase 1 PII tests) — D-24 / OPS-07 baseline preservation.
    - main.py contains NO inline `class PIIHit` / `def detect_pii` / `def validate_uscc` / `def write_partial_masks` / `def clear_pdf_metadata` (v37.7.6 convergence enforced by TestPiiConvergence).
  artifacts:
    - privacyguard/pii/validators/uscc.py (USCC_CHARSET 31-char string, USCC_WEIGHTS 17-tuple, USCC_CATEGORY_CODES 6-char frozenset, compute_uscc_check_digit, validate_uscc)
    - privacyguard/pii/validators/bank_card.py (luhn_check, load_bin_whitelist + get_bin_whitelist singleton, validate_bank_card)
    - privacyguard/pii/validators/email.py (EMAIL_RE RFC 5322 simplified, EMAIL_PUBLIC_SUFFIXES frozenset, validate_email, is_public_suffix_email)
    - privacyguard/pii/validators/__init__.py extended (lazy _LAZY_IMPORTS + __all__ adds: validate_uscc, validate_bank_card, validate_email, has_vat_invoice_context, has_bank_account_context, USCC_CATEGORY_CODES, BANK_CARD_BIN_WHITELIST, EMAIL_PUBLIC_SUFFIXES, VAT_INVOICE_CONTEXTS, BANK_ACCOUNT_CONTEXTS)
    - privacyguard/pii/regex_patterns.py extended (iter_candidate_strings yields CN_BANK_CARD / CN_EMAIL / CN_USCC / CN_VAT_INVOICE / CN_TAXPAYER_ID_15 / CN_BANK_ACCOUNT; precompiled _BANK_CARD_RE / _EMAIL_RE / _USCC_RE / _VAT_INVOICE_8_RE / _VAT_INVOICE_20_RE / _TAXPAYER_ID_15_RE / _BANK_ACCOUNT_RE)
    - privacyguard/pii/mask.py extended (partial_mask_bank_card / partial_mask_email / partial_mask_uscc + mask_for_entity dispatches 6 new entity_types)
    - privacyguard/pii/engine.py extended (PIIEngine.detect routes the 6 new entity_hints to _check_bank_card / _check_email / _check_uscc / _check_vat_invoice / _check_taxpayer_id_15 / _check_bank_account)
    - privacyguard/pii/pdf_adapter.py extended (write_partial_masks + _FONT_NAME_MAP + _resolve_text_layer_font + _resolve_placeholder_font + clear_pdf_metadata)
    - privacyguard/pii/data/rules.json extended (bank_card / uscc / vat_invoice / bank_account schema sections)
    - privacyguard/pii/__init__.py extended (__all__ + _LAZY_IMPORTS adds 14 new symbols)
    - privacyguard/__init__.py extended (__all__ + _LAZY_IMPORTS forwards 14 new PII symbols)
    - tests/fixtures/fake_pii.py extended (fake_bank_card / fake_email / fake_uscc / fake_vat_invoice_8 / fake_vat_invoice_20 / fake_taxpayer_id_15 / fake_bank_account + _invalid_* variants)
    - tests/unit/test_pii_validators.py extended (TestBankCardLuhn / TestBankCardBin / TestEmail / TestUsccMod31 / TestUsccCategory test classes)
    - tests/unit/test_pii_engine.py extended (TestEngineBankCard / TestEngineEmail / TestEngineUscc test classes)
    - tests/unit/test_pdf_pii_redaction.py extended (TestPartialMaskWritesMaskText + TestPartialMaskDestroysOriginal test classes)
    - tests/unit/test_pdf_metadata_cleared.py (NEW file: TestPdfMetadataCleared 5-field reverse test)
    - tests/unit/test_package_imports.py extended (test_import_privacyguard_does_not_load_new_validators)
    - tests/unit/test_convergence.py extended (TestPiiConvergence new methods: test_main_py_no_inline_uscc_or_partial_mask)
  key_links:
    - privacyguard.pii.engine.detect → iter_candidate_strings (now yields 9 entity_hints) → _check_uscc → privacyguard.pii.validators.uscc.validate_uscc (FIN-01 validation gate)
    - privacyguard.pii.engine.detect → mask_for_entity → partial_mask_uscc (D-09 18-char mask: first 6 + 8 asterisks + last 4)
    - privacyguard.pii.pdf_adapter.write_partial_masks → page.add_redact_annot + apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS) + page.insert_text (D-01/D-02/D-21 SAFE-01 + MASK-01)
    - privacyguard.pii.pdf_adapter.clear_pdf_metadata → doc.set_metadata({title:'',author:'',subject:'',producer:'',creator:''}) (D-14/D-15/D-16 SAFE-03)
    - privacyguard.pii.validators.bank_card.load_bin_whitelist → privacyguard.utils.security.resource_path("privacyguard/pii/data/bin_prefixes.json") (D-26 cp30 discipline — for now returns empty set until 02-03 populates the JSON)
    - privacyguard.__init__._LAZY_IMPORTS → privacyguard.pii.validators.{uscc,bank_card,email,...} (OPS-03 lazy contract extends to 6 new validators)
    - MainWindow.save_pdf (deferred to 02-03) → write_partial_masks + clear_pdf_metadata (D-22 — 02-01 lands the helpers + tests, 02-03 wires into main.py)
  prohibitions:
    - 不得使用 `page.draw_rect(fill=(0,0,0))` 替代 `add_redact_annot + apply_redactions(IMAGE_PIXELS)` 真删除路径（行业头号失败模式；Phase 1 已禁用）
    - 不得在测试夹具或测试断言中写入真实 USCC / 银行卡号 / 邮箱 / 发票号；fake_pii.py 是唯一合成来源（OPS-05）
    - 不得在 main.py 内联 USCC 校验位函数、partial mask 写入 helper 或元数据清除 helper；6 个新 validator 与 write_partial_masks / clear_pdf_metadata 必须放在 `privacyguard/pii/validators/` 与 `privacyguard/pii/pdf_adapter.py`（v37.7.6 收敛原则）
    - 不得让 `privacyguard.pii.validators.{uscc,bank_card,email,...}` 在 `import privacyguard` 时被 eager 加载；必须经 `_LAZY_IMPORTS` + `__getattr__` 延迟加载（OPS-03 + cp30 教训）
    - 不得在 partial mask 写入 helper 内省略 `page.insert_text` 步骤（会变成全遮蔽，违反 MASK-01）
    - 不得在 `clear_pdf_metadata` 中填占位字符串 ("Anonymous" / "Redacted" / "PyMuPDF")，5 字段必须全部 `""`（D-15 锁定）
    - 不得在 `clear_pdf_metadata` 中触碰 `CreationDate` / `ModDate` / `Keywords` / XMP metadata；只清 5 字段（D-14 锁定）
    - 不得让 partial mask 字体回退导致 mask 文字溢出 rect；helper 必须按 mask_strategy 字符数重算 rect 宽度（D-03 锁定）
    - 不得让 USCC validator 接受 `category_code not in {"1","5","9","Y","A","N"}`（D-06 类别码白名单必须强制执行）
    - 不得让银行卡 validator 在 BIN 词典缺失时降级到"全量接受"；`validate_bank_card` 在 BIN 词典为空时必须返回 False（D-05 + D-26 锁定）

threat_model:
  trust_boundaries:
    - {name: PDF file input, description: untrusted .pdf file path crosses here; PyMuPDF parses arbitrary PDF bytes; partial mask write must NOT leave original USCC characters in output}
    - {name: Worker thread → MainWindow slot, description: cross-thread pyqtSignal carrying PIIHit list (worker thread untrusted; partial mask strategy travels via mask_strategy field — D-05 field lock preserved)}
    - {name: privacyguard.pii → filesystem, description: bin_prefixes.json read via resource_path; 02-03 lands the JSON, 02-01 must scaffold the load_bin_whitelist loader without crashing when JSON is absent}
    - {name: PyMuPDF apply_redactions → output PDF, description: writes content-stream-level removal; draw_rect would leak — write_partial_masks must use the proven add_redact_annot + apply_redactions(IMAGE_PIXELS) path}
    - {name: doc.set_metadata → PDF /Info dict, description: writes 5 metadata fields; helper must not write placeholder strings and must not touch CreationDate/ModDate/Keywords/XMP}
  stride:
    - {id: T-2-FAKE, category: Tampering / Information Disclosure, component: privacyguard.pii.pdf_adapter.write_partial_masks, severity: critical, disposition: mitigate, mitigation: strictly use page.add_redact_annot + page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS) before page.insert_text (D-01); test_pdf_pii_redaction.test_partial_mask_destroys_original asserts original USCC not extractable via fitz.open(out).get_text(); test_convergence.py scans for any draw_rect literal}
    - {id: T-2-META, category: Information Disclosure, component: privacyguard.pii.pdf_adapter.clear_pdf_metadata, severity: high, disposition: mitigate, mitigation: doc.set_metadata({title:'',author:'',subject:'',producer:'',creator:''}) only — 5 fields all empty string; test_pdf_metadata_cleared.TestPdfMetadataCleared asserts each of 5 fields == ""; helper signature hard-codes the 5 keys to prevent future drift}
    - {id: T-2-LAZY, category: Denial of Service / Import-time regression, component: privacyguard/pii/validators/__init__.py _LAZY_IMPORTS, severity: medium, disposition: mitigate, mitigation: __getattr__ lazy table extended; test_package_imports.assert_privacyguard_does_not_load_new_validators confirms bank_card / email / uscc not in sys.modules after import privacyguard}
    - {id: T-2-USCC-CATEGORY, category: Tampering, component: privacyguard.pii.validators.uscc.validate_uscc, severity: medium, disposition: mitigate, mitigation: USCC_CATEGORY_CODES frozenset {"1","5","9","Y","A","N"} as first character gate; TestUsccCategory.test_invalid_category_code_rejected asserts "Z11000000000000000" returns False}
    - {id: T-2-ORDER-FP, category: Information Disclosure (false positive), component: privacyguard.pii.validators.bank_card.validate_bank_card, severity: medium, disposition: mitigate, mitigation: Luhn + BIN 6-digit whitelist (from bin_prefixes.json via resource_path) + context anchor gate; 02-01 lands loader returning empty set when JSON absent (safe-fail), 02-03 populates the JSON; test_rejects_valid_luhn_without_bin asserts empty whitelist → False (deferred to 02-03 for full coverage)}
    - {id: T-2-BIN-LICENSE, category: Repudiation, severity: low, disposition: accept, rationale: 02-01 lands empty bin_prefixes.json + LICENSE file scaffold only; 02-03 populates the BIN data with full CC BY-SA 4.0 attribution}
    - {id: T-2-FIX, category: Information Disclosure / Compliance, component: tests/fixtures/fake_pii.py, severity: high, disposition: mitigate, mitigation: only Faker-style synthesizers (Luhn-loop + mod-31-3 loop + GB 32100 category whitelist) produce USCC/bank card/email; tests/samples/real_* gitignored; TestNoRealPiiInFixtures extended to scan for 18-char USCC literals and 13-19 digit Luhn-passing strings}
    - {id: T-2-MASK-GEO, category: Information Disclosure, component: partial mask text vs original span geometry, severity: medium, disposition: mitigate, mitigation: helper recomputes rect width as max(len(mask_text) * fontsize * 0.6, original_width) and centers insert_text; D-03 lock}
    - {id: T-2-PYINST, category: Denial of Service, component: PyInstaller datas entry for bin_prefixes.json, severity: low, disposition: accept, rationale: 02-03 lands spec datas parity; 02-01 lands the JSON file scaffold + empty LICENSE so spec addition is a one-line edit}

assumption_delta_decision:
  - noun_now_primary: privacyguard.pii.pdf_adapter (was a 65-LOC redaction-only module)
  - decision: add-alongside
  - rationale: Phase 2 adds two new functions to pdf_adapter (write_partial_masks + clear_pdf_metadata) without restructuring the existing Phase 1 apply_pii_redactions signature. Both functions reuse Phase 1 patterns (add_redact_annot + apply_redactions + garbage=4) and add only the insert_text step + the set_metadata call respectively.
  - what_would_force_promote: Phase 4 (Excel) or Phase 5 (Image) needs format-specific write helpers beyond PDF; then promote pdf_adapter to a format-dispatch helper with a per-format write_partial_masks / clear_metadata contract.
  - invariant_test_suggestion: tests/unit/test_convergence.py::TestPiiConvergence asserts `privacyguard/pii/pdf_adapter.py` exports `apply_pii_redactions`, `write_partial_masks`, `clear_pdf_metadata`; adding a new write helper requires updating this test (deliberate friction).

---

<objective>
Wire the thinnest end-to-end Phase 2 spine: open synthetic PDF → PIIEngine detects one valid 18-character USCC → write_partial_masks writes mask text "911100********XXXX" while destroying the original digits → clear_pdf_metadata clears 5 metadata fields → reverse-extraction proves the original digits are absent + mask text is present + metadata 5 fields are empty. This tracer proves the whole chain on the smallest possible input; subsequent plans expand entity coverage + UI + packaging.
</objective>

<purpose>
Phase 2 cannot ship without MASK-01 (partial mask write actually visible in output) and SAFE-03 (metadata 5 fields cleared). The tracer proves these two safety-critical write paths on one new entity (USCC, FIN-01) before subsequent plans extend to the remaining 5 new entities + the SettingsDialog UI + PyInstaller packaging. Tracer failure modes are caught here on the smallest possible input, not after 14 files have been touched.
</purpose>

<output>
- 3 new validators (uscc, bank_card, email) — pure-function, lazy-loaded, no IO
- `iter_candidate_strings` extended to yield 6 new entity_hints (CN_BANK_CARD / CN_EMAIL / CN_USCC / CN_VAT_INVOICE / CN_TAXPAYER_ID_15 / CN_BANK_ACCOUNT)
- `mask_for_entity` dispatches 3 new entity_types to `partial_mask_*` helpers
- `PIIEngine.detect` extended with 3 new `_check_*` methods
- `write_partial_masks` + `clear_pdf_metadata` helpers in `privacyguard.pii.pdf_adapter`
- Extended test suites (validators, engine, redaction, package_imports, convergence) + NEW `tests/unit/test_pdf_metadata_cleared.py`
- All 14 new symbols registered in `_LAZY_IMPORTS` at both `privacyguard/pii/__init__.py` and `privacyguard/__init__.py` (OPS-03 lazy contract extended)
</output>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-pdf/02-CONTEXT.md
@.planning/phases/02-pdf/02-RESEARCH.md
@.planning/phases/02-pdf/02-PATTERNS.md
@.planning/phases/02-pdf/02-VALIDATION.md
@.planning/phases/01-pdf/01-PATTERNS.md
@.planning/phases/01-pdf/01-VERIFICATION.md
@.planning/phases/01-pdf/01-01-tracer-PLAN.md
@.planning/codebase/STRUCTURE.md
@CLAUDE.md
@privacyguard/pii/__init__.py
@privacyguard/pii/engine.py
@privacyguard/pii/mask.py
@privacyguard/pii/pdf_adapter.py
@privacyguard/pii/regex_patterns.py
@privacyguard/pii/validators/__init__.py
@main.py:12490-12504 (Phase 1 save loop — deferred to 02-03 for actual wire-in)
@tests/unit/test_pdf_pii_redaction.py
@tests/unit/test_pii_engine.py
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>RED: write failing tests for USCC validator, partial mask write, and metadata clear</name>
  <files>
    - tests/fixtures/fake_pii.py
    - tests/unit/test_pii_validators.py
    - tests/unit/test_pii_engine.py
    - tests/unit/test_pdf_pii_redaction.py
    - tests/unit/test_pdf_metadata_cleared.py
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 1240-1342 — test_pii_validators.py TestBankCardLuhn / TestBankCardBin / TestEmail / TestUsccMod31 patterns)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 1351-1448 — test_pii_engine.py TestEngineBankCard / TestEngineEmail / TestEngineUscc patterns)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 1456-1575 — test_pdf_pii_redaction.py TestPartialMaskWritesMaskText + test_metadata_5_fields_cleared_on_save patterns)
    - .planning/phases/02-pdf/02-VALIDATION.md (lines 41-65 — Per-Task Verification Map)
    - tests/unit/test_pii_validators.py:1-150 (existing TestIdCardChecksum / TestPhoneSegment classes for pattern reference)
    - tests/unit/test_pii_engine.py:1-200 (existing TestEngineDetect class for pattern reference)
    - tests/unit/test_pdf_pii_redaction.py:1-120 (existing TestPdfPiiRedaction for pattern reference)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 196-208 — GB 32100-2015 character table + weights verified locally; lines 1058-1107 — USCC validator code example)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 1178-1251 — full PyMuPDF partial mask + metadata clear example)
  </read_first>
  <action>
    Write five test files that exercise the END-TO-END Phase 2 spine on USCC. Do NOT implement production code in this task; the tests must FAIL when run.

    In `tests/fixtures/fake_pii.py`, append to the existing Phase 1 fake_id_card / fake_phone form. Add:
    - `fake_uscc(category='9')`: random pick category ∈ {'1','5','9','Y','A','N'}; 16 random chars from USCC_CHARSET ("0123456789ABCDEFGHJKLMNPQRTUWXY", 31 chars without I/O/S/V/Z) plus `compute_uscc_check_digit(body17)`; loop until `validate_uscc(full)` returns True (mod-31-3 verified). Import compute helper lazily from `privacyguard.pii.validators.uscc` inside the function — this triggers the lazy load at test runtime.
    - `fake_uscc_invalid_category()`: returns a fixed 18-char string starting with "Z" + 17 random USCC_CHARSET chars + Luhn-style check digit (used for negative tests; will fail validate_uscc on category gate regardless of check digit).
    - `fake_email(local=None, tld='example.com')`: `local = local or ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(6)); domain = tld; return f"{local}@{domain}"`.
    - `fake_bank_card(bin_prefix='622576')`: build a 16-digit string with bin_prefix + 9 random digits + Luhn check digit; loop until luhn_check(full) returns True. Import luhn_check lazily from `privacyguard.pii.validators.bank_card`.

    In `tests/unit/test_pii_validators.py`, append the following test classes (do NOT delete existing Phase 1 tests):
    - `TestBankCardLuhn`: `test_luhn_standard_visa_passes` (asserts `luhn_check('4532015112830366') is True`); `test_luhn_invalid_fails` (asserts `luhn_check('6222020000000000') is False`); `test_luhn_non_digit_rejected` (asserts `luhn_check('622202000000000a') is False`).
    - `TestBankCardBin`: `test_valid_bin_in_whitelist_passes` (asserts `validate_bank_card('6222021234567890', bin_whitelist=frozenset({'622202'})) is True`); `test_unknown_bin_rejected` (asserts `validate_bank_card('0000001234567890', bin_whitelist=frozenset({'622202'})) is False`); `test_short_card_rejected` (asserts `validate_bank_card('1234567890123', bin_whitelist=frozenset({'622202'}))` is False — 13 digits ok by length, but BIN check fails; test Luhn rejection: `test_invalid_luhn_rejected` asserts `validate_bank_card('6222020000000000', bin_whitelist=frozenset({'622202'}))` is False).
    - `TestEmail`: `test_valid_email_passes` (`'user@example.com' → True`); `test_invalid_email_rejected` (`'not-an-email' → False`); `test_plus_alias_accepted` (`'user+tag@example.com' → True`); `test_public_tld_classified_high` (`is_public_suffix_email('foo@qq.com') is True`); `test_unknown_tld_classified_low` (`is_public_suffix_email('foo@unknown-tld-xyz') is False`).
    - `TestUsccMod31`: `test_known_uscc_passes` (asserts `validate_uscc('91110000600037341L') is True` — Tencent USCC verified locally); `test_invalid_check_digit_fails` (asserts `validate_uscc('911100006000373410') is False`); `test_charset_rejects_IO_S_V_Z` (asserts `validate_uscc('91110000600037341I') is False`); `test_short_uscc_rejected` (asserts `validate_uscc('9111000060003734') is False`); `test_non_string_rejected` (asserts `validate_uscc(None) is False` and `validate_uscc(12345) is False`).
    - `TestUsccCategory`: `test_category_code_z_rejected` (asserts `validate_uscc('Z11000000000000000') is False`); `test_all_6_categories_accepted` (loop over each of {'1','5','9','Y','A','N'}, build a 17-char body + compute check digit, assert validate_uscc returns True); `test_category_whitelist_size_is_6` (asserts `len(USCC_CATEGORY_CODES) == 6`).

    In `tests/unit/test_pii_engine.py`, append:
    - `TestEngineUscc`: `test_detects_valid_uscc_in_text` (TextUnit("测试 {fake_uscc()}", "text") → at least one hit with entity_type == "CN_USCC" and confidence_tier == "HIGH"); `test_rejects_invalid_category` (TextUnit("测试 {fake_uscc_invalid_category()}", "text") → 0 hits).
    - `TestEngineBankCard`: `test_detects_known_bin_with_context` (TextUnit("卡号 {fake_bank_card()}", "text") + bin_whitelist injection → 1 hit CN_BANK_CARD); `test_luhn_failure_rejected` (TextUnit("卡号 6222020000000000", "text") → 0 hits even with whitelist).
    - `TestEngineEmail`: `test_detects_valid_email_with_context` (TextUnit("邮箱 {fake_email()}", "text") → 1 hit CN_EMAIL); `test_detects_email_without_context` (TextUnit("{fake_email()}", "text") → 1 hit CN_EMAIL; emails are always detected regardless of anchor).

    In `tests/unit/test_pdf_pii_redaction.py`, append a new class `TestPartialMaskWritesMaskText(unittest.TestCase)`:
    - `test_partial_mask_writes_mask_text_for_uscc`: build a synthetic PDF via `fitz.open() + page.insert_text((50,100), f"测试 USCC {uscc}", fontsize=14)`; open with `fitz.open`, iterate pages building TextUnit; run `engine.detect(unit, page=page)` to collect hits; call `write_partial_masks(doc, 0, hits, mode="partial")`; save with `garbage=4, deflate=True, clean=True`; reopen output, `get_text()` → assert `assertNotIn(uscc[:6], out_text)` (original first 6 chars destroyed) AND `assertIn(mask_strategy, out_text)` (mask text present — the partial mask must be visible).
    - `test_partial_mask_blackout_mode_destroys_only`: same setup but call `write_partial_masks(doc, 0, hits, mode="blackout")`; assert mask_strategy NOT in out_text AND uscc[:6] NOT in out_text (full blackout, no mask text).
    - `test_partial_mask_id_card_also_visible`: same setup but with fake_id_card() → assert mask text "110101********XXXX" visible in output and original id first 10 chars NOT in output.

    Create NEW file `tests/unit/test_pdf_metadata_cleared.py`:
    - `TestPdfMetadataCleared(unittest.TestCase)`: `test_metadata_5_fields_cleared` (create PDF with `doc.set_metadata({title:'Confidential', author:'Author', subject:'Subject', producer:'Producer', creator:'Creator'})`; open; call `clear_pdf_metadata(doc)`; save; reopen with `fitz.open(out)`; assert `meta.get('title') == ''` for each of 5 fields); `test_metadata_creation_date_preserved` (set creationDate indirectly by saving through PyMuPDF, then call clear; assert `meta.get('creationDate', '')` not affected — should be a non-empty D: string).

    After all test files exist, run `python3 -m unittest tests.unit.test_pii_validators.TestBankCardLuhn tests.unit.test_pii_validators.TestEmail tests.unit.test_pii_validators.TestUsccMod31 tests.unit.test_pii_engine.TestEngineUscc tests.unit.test_pdf_pii_redaction.TestPartialMaskWritesMaskText tests.unit.test_pdf_metadata_cleared.TestPdfMetadataCleared -v` and confirm all fail with `ModuleNotFoundError: No module named 'privacyguard.pii.validators.uscc'` (or `ModuleNotFoundError: No module named 'privacyguard.pii.pdf_adapter.write_partial_masks'`) — RED state confirmed.

    This task writes NO production code under `privacyguard/pii/`. Running the test command must produce `ModuleNotFoundError` or `ImportError` (RED state).
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_pii_validators.TestBankCardLuhn tests.unit.test_pii_validators.TestEmail tests.unit.test_pii_validators.TestUsccMod31 tests.unit.test_pii_engine.TestEngineUscc tests.unit.test_pdf_pii_redaction.TestPartialMaskWritesMaskText tests.unit.test_pdf_metadata_cleared.TestPdfMetadataCleared -v 2>&1 | grep -E "(ModuleNotFoundError|ImportError|FAIL|ERROR)" | head -10</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m unittest tests.unit.test_pii_validators.TestBankCardLuhn -v` fails with ModuleNotFoundError or ImportError pointing at `privacyguard.pii.validators.bank_card` or `privacyguard.pii.validators.uscc`.
    - `python3 -m unittest tests.unit.test_pdf_pii_redaction.TestPartialMaskWritesMaskText -v` fails with ModuleNotFoundError pointing at `privacyguard.pii.pdf_adapter.write_partial_masks` or `privacyguard.pii.validators.uscc`.
    - `python3 -m unittest tests.unit.test_pdf_metadata_cleared.TestPdfMetadataCleared -v` fails with ModuleNotFoundError pointing at `privacyguard.pii.pdf_adapter.clear_pdf_metadata`.
    - `python3 -c "from tests.fixtures.fake_pii import fake_email; print(fake_email())"` runs without ModuleNotFoundError (the lazy load inside fake_* functions will fail later, but the import statement itself must succeed — wrap individual calls in try/except in the test if needed).
    - `python3 -m compileall -q tests/fixtures/fake_pii.py tests/unit/test_pii_validators.py tests/unit/test_pii_engine.py tests/unit/test_pdf_pii_redaction.py tests/unit/test_pdf_metadata_cleared.py` exits 0 (syntax-only green).
  </acceptance_criteria>
  <done>
    All five test files exist on disk; running them produces ModuleNotFoundError / ImportError / AttributeError (RED state); the test contracts for USCC + bank card + email validators, partial mask write + metadata clear, and engine integration are in place so Task 2 has a verifiable GREEN target.
  </done>
  <reversibility>rating="reversible" rationale="Test files only; deletion reverts cleanly."</reversibility>
</task>

<task type="auto" tdd="true">
  <name>GREEN validators: implement uscc.py + bank_card.py + email.py + extend validators/__init__.py + extend regex_patterns.py + extend mask.py</name>
  <files>
    - privacyguard/pii/validators/uscc.py
    - privacyguard/pii/validators/bank_card.py
    - privacyguard/pii/validators/email.py
    - privacyguard/pii/validators/__init__.py
    - privacyguard/pii/regex_patterns.py
    - privacyguard/pii/mask.py
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 49-105 — bank_card.py luhn_check + validate_bank_card exact pattern)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 107-153 — email.py EMAIL_RE + validate_email exact pattern)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 155-201 — uscc.py USCC_CHARSET + USCC_WEIGHTS + validate_uscc exact pattern)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 357-398 — validators/__init__.py _LAZY_IMPORTS extension)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 405-464 — regex_patterns.py yield extension)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 468-560 — mask.py partial_mask_* functions + mask_for_entity dispatch extension)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 222-237 — Luhn algorithm verified locally; lines 272-281 — EMAIL_RE RFC 5322 simplified)
    - privacyguard/pii/validators/id_card.py (Phase 1 reference: pure-function validator with frozen constants)
    - privacyguard/pii/validators/phone_segment.py (Phase 1 reference: white-list constants + is_* function)
    - privacyguard/pii/regex_patterns.py (current 3-yield form to extend)
    - privacyguard/pii/mask.py (current 2-function form to extend)
    - privacyguard/pii/validators/__init__.py (Phase 1 lazy re-export pattern)
  </read_first>
  <action>
    Implement the 3 new validators + extend the regex/mask modules to make Task 1's tests pass (GREEN). Follow the exact templates cited in PATTERNS.md line ranges; do NOT improvise signatures.

    **privacyguard/pii/validators/uscc.py** — Mirror `privacyguard/pii/validators/id_card.py` form. Module docstring "统一社会信用代码校验（FIN-01 + GB 32100-2015 mod-31-3）". Define at module top (in this order): `USCC_CHARSET: Final = "0123456789ABCDEFGHJKLMNPQRTUWXY"` (31 chars; omit I/O/S/V/Z — verified locally); `USCC_WEIGHTS: Final = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)` (17 weights); `USCC_CATEGORY_CODES: Final = frozenset({"1","5","9","Y","A","N"})` (6 chars — D-06 locked). Function `compute_uscc_check_digit(body17: str) -> str`: returns `""` if body17 not exactly 17 chars; otherwise iterate `total = sum(USCC_CHARSET.index(body17[i]) * USCC_WEIGHTS[i] for i in range(17))`; return `USCC_CHARSET[(31 - total % 31) % 31]`. Function `validate_uscc(code) -> bool`: defensive `if not isinstance(code, str) or len(code) != 18: return False`; `if any(c not in USCC_CHARSET for c in code): return False`; `if code[0] not in USCC_CATEGORY_CODES: return False`; return `compute_uscc_check_digit(code[:17]) == code[17]`. `__all__ = ["USCC_CHARSET","USCC_WEIGHTS","USCC_CATEGORY_CODES","compute_uscc_check_digit","validate_uscc"]`.

    **privacyguard/pii/validators/bank_card.py** — Mirror `privacyguard/pii/validators/phone_segment.py` form. Module docstring "银行卡号校验（NUM-04 + Luhn + 6 位 BIN 词典 + 上下文锥点）". Module-level singleton: `_BIN_WHITELIST_CACHE: Optional[frozenset] = None`. Function `luhn_check(num: str) -> bool`: defensive `if not num or not num.isdigit(): return False`; `digits = [int(d) for d in num]`; iterate reversed digits, double every other digit starting at index 1 (i % 2 == 1 in reversed order); `d2 = d * 2; total += d2 if d2 < 10 else d2 - 9`; return `total % 10 == 0`. Function `load_bin_whitelist(json_path=None) -> frozenset`: if json_path is None, use `resource_path("privacyguard/pii/data/bin_prefixes.json")` (import lazily inside function to avoid top-level PyPI/circular deps); open file, `json.load`, extract `data.get("bin_prefixes", [])`, return frozenset. Function `get_bin_whitelist() -> frozenset`: global singleton — first call invokes `load_bin_whitelist()`, caches in `_BIN_WHITELIST_CACHE`, subsequent calls return cached value; if file missing/JSON invalid, cache an empty frozenset (safe-fail — D-26 02-03 will populate the JSON). Function `validate_bank_card(card_num, bin_whitelist=None) -> bool`: defensive `if not isinstance(card_num, str): return False`; `stripped = card_num.replace(" ","").replace("-","")`; `if not stripped.isdigit() or not (13 <= len(stripped) <= 19): return False`; `if not luhn_check(stripped): return False`; `whitelist = bin_whitelist or get_bin_whitelist()`; return `stripped[:6] in whitelist`. `__all__ = ["luhn_check","load_bin_whitelist","get_bin_whitelist","validate_bank_card","BANK_CARD_BIN_WHITELIST"]`.

    **privacyguard/pii/validators/email.py** — Mirror `phone_segment.py` form. Module docstring "邮箱识别（NUM-05 + RFC 5322 简化版正则）". Pre-compiled `EMAIL_RE: Final = re.compile(r"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9._%+-])")` (verified locally). `EMAIL_PUBLIC_SUFFIXES: Final = frozenset({"com","cn","net","org","gov","edu","io","co","ai","app"})` (D-10 locked). Function `validate_email(text) -> bool`: `if not isinstance(text, str) or not text: return False`; return `bool(EMAIL_RE.fullmatch(text))`. Function `is_public_suffix_email(text) -> bool`: `if not validate_email(text): return False`; `_, _, domain = text.partition('@"); suffix = domain.rsplit('.', 1)[-1].lower()`; return `suffix in EMAIL_PUBLIC_SUFFIXES`. `__all__ = ["EMAIL_RE","EMAIL_PUBLIC_SUFFIXES","validate_email","is_public_suffix_email"]`.

    **privacyguard/pii/validators/__init__.py** — Extend the existing Phase 1 lazy `_LAZY_IMPORTS` pattern. Append to `__all__`: `'validate_uscc','validate_bank_card','validate_email','has_vat_invoice_context','has_bank_account_context','BANK_CARD_BIN_WHITELIST','EMAIL_PUBLIC_SUFFIXES','USCC_CATEGORY_CODES','VAT_INVOICE_CONTEXTS','BANK_ACCOUNT_CONTEXTS'`. Append to `_LAZY_IMPORTS`:
    - `'validate_uscc': ('privacyguard.pii.validators.uscc', 'validate_uscc')`
    - `'validate_bank_card': ('privacyguard.pii.validators.bank_card', 'validate_bank_card')`
    - `'validate_email': ('privacyguard.pii.validators.email', 'validate_email')`
    - `'has_vat_invoice_context': ('privacyguard.pii.validators.vat_invoice', 'has_vat_invoice_context')`
    - `'has_bank_account_context': ('privacyguard.pii.validators.bank_account', 'has_bank_account_context')`
    - `'BANK_CARD_BIN_WHITELIST': ('privacyguard.pii.validators.bank_card', 'BANK_CARD_BIN_WHITELIST')`
    - `'EMAIL_PUBLIC_SUFFIXES': ('privacyguard.pii.validators.email', 'EMAIL_PUBLIC_SUFFIXES')`
    - `'USCC_CATEGORY_CODES': ('privacyguard.pii.validators.uscc', 'USCC_CATEGORY_CODES')`
    - `'VAT_INVOICE_CONTEXTS': ('privacyguard.pii.validators.vat_invoice', 'VAT_INVOICE_CONTEXTS')`
    - `'BANK_ACCOUNT_CONTEXTS': ('privacyguard.pii.validators.bank_account', 'BANK_ACCOUNT_CONTEXTS')`
    NOTE: For 02-01 (this plan), only `validate_uscc`, `validate_bank_card`, `validate_email`, `EMAIL_PUBLIC_SUFFIXES`, `USCC_CATEGORY_CODES`, `BANK_CARD_BIN_WHITELIST` need actual implementations. The remaining 4 entries (vat_invoice / bank_account context anchors) MUST also be added now per `02-PATTERNS.md` lines 357-398 — they will reference files (`vat_invoice.py` / `bank_account.py`) that 02-02 creates. For 02-01 only, register the `_LAZY_IMPORTS` entries pointing at modules that don't yet exist; this will fail ImportError until 02-02 lands. **Alternative:** defer adding the vat_invoice / bank_account _LAZY_IMPORTS entries until 02-02 lands — this is the preferred option for 02-01 to avoid ImportError at test time. Implementation: in 02-01, add ONLY the 6 entries for uscc/bank_card/email/USCC_CATEGORY_CODES/BANK_CARD_BIN_WHITELIST/EMAIL_PUBLIC_SUFFIXES; 02-02 adds the remaining 4.

    **privacyguard/pii/regex_patterns.py** — Extend the existing `iter_candidate_strings(text)`. Preserve the existing 3 yields (CN_ID_CARD × 2, CN_PHONE) in their original order. Append in this order (yield sequence is significant — USCC regex precedes phone because USCC contains digits/letters that may be substring of phone): for each new regex below, add `for m in <RE>.finditer(text): yield m.group(0), m.span(), <entity_hint>`. New regexes (all `Final` at module top):
    - `_BANK_CARD_RE: Final = re.compile(r"(?<!\d)(\d{13,19})(?!\d)")` → yields CN_BANK_CARD
    - `_EMAIL_RE: Final = re.compile(r"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9._%+-])")` → yields CN_EMAIL
    - `_USCC_RE: Final = re.compile(r"(?<![A-Z0-9])([0-9A-HJ-NPQRTUWXY]{18})(?![A-Z0-9])")` → yields CN_USCC (note: charset excludes I/O/S/V/Z, matching USCC_CHARSET)
    - `_VAT_INVOICE_8_RE: Final = re.compile(r"(?<!\d)(\d{8})(?!\d)")` → yields CN_VAT_INVOICE
    - `_VAT_INVOICE_20_RE: Final = re.compile(r"(?<!\d)(\d{20})(?!\d)")` → yields CN_VAT_INVOICE
    - `_TAXPAYER_ID_15_RE: Final = re.compile(r"(?<!\d)([1-9]\d{14})(?!\d)")` → yields CN_TAXPAYER_ID_15
    - `_BANK_ACCOUNT_RE: Final = re.compile(r"(?<!\d)(\d{9,21})(?!\d)")` → yields CN_BANK_ACCOUNT

    **privacyguard/pii/mask.py** — Extend the existing 2-function form. Add 6 new `partial_mask_*` functions preserving Phase 1 form (length-defensive `'*' * len(text)` on bad length):
    - `partial_mask_bank_card(card: str) -> str`: `if not card or not (13 <= len(card) <= 19): return '*' * len(card)`; return `card[:4] + '*' * (len(card) - 8) + card[-4:]` (per 02-PATTERNS.md line 497-500 — first 4 + last 4)
    - `partial_mask_email(email: str) -> str`: `if not email or '@' not in email: return '*' * len(email)`; `local, _, domain = email.partition('@')`; `if not local or not domain: return '*' * len(email)`; return `local[0] + '****' + '@' + domain` (preserves full domain; e.g. "u****@qq.com" — 02-PATTERNS.md line 503-510)
    - `partial_mask_uscc(uscc: str) -> str`: `if not uscc or len(uscc) != 18: return '*' * len(uscc)`; return `uscc[:6] + '*' * 8 + uscc[14:]` (same as partial_mask_id_card — 02-PATTERNS.md line 513-517)
    - `partial_mask_taxpayer_id_15(id15: str) -> str`: `if not id15 or len(id15) != 15: return '*' * len(id15)`; return `id15[:6] + '*' * 5 + id15[11:]` (D-09 Claude's Discretion: first 6 + last 4)
    - `partial_mask_vat_invoice(num: str) -> str`: `if not num or len(num) < 4: return '*' * len(num)`; return `num[:2] + '*' * (len(num) - 4) + num[-2:]` (first 2 + last 2)
    - `partial_mask_bank_account(acct: str) -> str`: `if not acct or len(acct) < 8: return '*' * len(acct)`; return `acct[:4] + '*' * (len(acct) - 8) + acct[-4:]` (first 4 + last 4)
    Extend `mask_for_entity(entity_type, normalized_text) -> str` with dispatch:
    ```python
    if entity_type == "CN_BANK_CARD": return partial_mask_bank_card(normalized_text)
    if entity_type == "CN_EMAIL": return partial_mask_email(normalized_text)
    if entity_type in ("CN_USCC","CN_TAXPAYER_ID"): return partial_mask_uscc(normalized_text)
    if entity_type == "CN_TAXPAYER_ID_15": return partial_mask_taxpayer_id_15(normalized_text)
    if entity_type == "CN_VAT_INVOICE": return partial_mask_vat_invoice(normalized_text)
    if entity_type == "CN_BANK_ACCOUNT": return partial_mask_bank_account(normalized_text)
    ```
    Update `__all__` to include all 6 new partial_mask_* functions.

    After all files exist, run the targeted test command from Task 1 and confirm GREEN for the validator + engine tests. The pdf_adapter + metadata tests will still fail (Task 3 addresses them). Then run the full baseline regression to confirm 79/79 + Phase 1 still green.
  </action>
  <verify>
    <automated>python3 -m compileall -q privacyguard/pii tests && python3 -m unittest tests.unit.test_pii_validators.TestBankCardLuhn tests.unit.test_pii_validators.TestEmail tests.unit.test_pii_validators.TestUsccMod31 tests.unit.test_pii_engine.TestEngineUscc tests.unit.test_pii_engine.TestEngineBankCard tests.unit.test_pii_engine.TestEngineEmail tests.unit.test_pdf_pii_redaction.TestPdfPiiRedaction -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m unittest tests.unit.test_pii_validators.TestBankCardLuhn tests.unit.test_pii_validators.TestEmail tests.unit.test_pii_validators.TestUsccMod31 -v` shows `OK` for all test methods (luhn_standard_visa_passes / valid_email_passes / known_uscc_passes etc.).
    - `python3 -m unittest tests.unit.test_pii_engine.TestEngineUscc -v` shows `OK` for `test_detects_valid_uscc_in_text` (PIIEngine emits CN_USCC hit for `f"测试 {fake_uscc()}"` text).
    - `python3 -m unittest tests.unit.test_pii_engine.TestEngineBankCard -v` shows `OK` for `test_luhn_failure_rejected` (engine correctly rejects 6222020000000000).
    - `python3 -m unittest tests.unit.test_pdf_pii_redaction.TestPdfPiiRedaction -v` (Phase 1 test) remains green — no regression.
    - `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence -v` (full Phase 1 79 baseline) all green.
    - `python3 -m compileall -q privacyguard/pii/validators` exits 0.
    - Live verification: `python3 -c "from privacyguard.pii.validators.uscc import validate_uscc, USCC_CATEGORY_CODES; print(validate_uscc('91110000600037341L'), len(USCC_CATEGORY_CODES))"` prints `True 6`.
    - Live verification: `python3 -c "from privacyguard.pii.validators.bank_card import luhn_check; print(luhn_check('4532015112830366'))"` prints `True`.
  </acceptance_criteria>
  <done>
    Three new validators (uscc + bank_card + email) exist; all Phase 1 validator tests + 3 new validator test classes + 3 new engine test classes pass; Phase 1 baseline + Phase 1 reverse-extraction test still green; the partial mask + metadata clear tests still fail as expected (waiting for Task 3).
  </done>
  <reversibility>rating="costly" rationale="Six partial_mask_* functions + 3 new validators + 7 new regex patterns extend core PII surface. Reverting requires coordinated changes across validators/__init__.py + privacyguard/pii/__init__.py + privacyguard/__init__.py + mask.py + regex_patterns.py + tests."</reversibility>
</task>

<task type="auto" tdd="true">
  <name>GREEN engine + adapter: extend PIIEngine.detect + write_partial_masks + clear_pdf_metadata + lazy-load tests</name>
  <files>
    - privacyguard/pii/engine.py
    - privacyguard/pii/pdf_adapter.py
    - privacyguard/pii/data/rules.json
    - privacyguard/pii/__init__.py
    - privacyguard/__init__.py
    - tests/unit/test_package_imports.py
    - tests/unit/test_convergence.py
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 567-691 — pdf_adapter.write_partial_masks + clear_pdf_metadata exact pattern)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 791-848 — privacyguard/pii/__init__.py + privacyguard/__init__.py _LAZY_IMPORTS extension)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 567-690 — write_partial_masks + clear_pdf_metadata full source pattern)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 508-653 — Pattern 1: Partial Mask Write with D-01/D-02/D-03 + Pattern 2: PDF Metadata Clear)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 178-194 — get_text("dict") font fallback mapping table)
    - privacyguard/pii/engine.py:103-149 (Phase 1 detect pipeline to extend; existing _check_id_card / _check_phone methods to mirror)
    - privacyguard/pii/pdf_adapter.py (existing 65-line file to extend; preserve apply_pii_redactions signature)
    - privacyguard/pii/data/rules.json (existing 2-key file to extend with bank_card/uscc/vat_invoice/bank_account schema)
    - privacyguard/pii/__init__.py:38-52 (existing _LAZY_IMPORTS to extend with 14 new symbols)
    - privacyguard/__init__.py:36-86 (existing top-level _LAZY_IMPORTS to extend)
    - tests/unit/test_package_imports.py:10-50 (existing test_import_privacyguard_does_not_load_pii_engine pattern to mirror)
    - tests/unit/test_convergence.py:36-62 (existing TestPiiConvergence pattern to mirror)
  </read_first>
  <action>
    Implement the engine extension + write_partial_masks + clear_pdf_metadata + lazy-load + convergence tests to make Task 1's remaining red tests pass.

    **privacyguard/pii/engine.py** — Extend the existing `PIIEngine.detect` dispatch to route the 6 new entity_hints. The current `detect` has an if/elif chain on `entity_hint == "CN_ID_CARD"` and `else: hit = self._check_phone(...)`. Extend with 6 new methods:
    - `_check_bank_card(unit, cand, normalized, flat_span, text, page)` → returns PIIHit with entity_type="CN_BANK_CARD" if `validate_bank_card(normalized)` passes; else None. Use `mask_for_entity("CN_BANK_CARD", normalized)`.
    - `_check_email(unit, cand, normalized, flat_span, text, page)` → returns PIIHit if `validate_email(normalized)` passes; else None. Confidence tier: HIGH if `is_public_suffix_email(normalized)` else MEDIUM (D-10).
    - `_check_uscc(unit, cand, normalized, flat_span, text, page)` → returns PIIHit if `validate_uscc(normalized)` passes; else None. Confidence tier always HIGH when validator passes (mod-31-3 is strong).
    - `_check_vat_invoice(unit, cand, normalized, flat_span, text, page)` → deferred to 02-02 (returns None for 02-01; yields placeholder hit to keep iter loop alive without crash). 02-01 only stubs `_check_vat_invoice` to return None.
    - `_check_taxpayer_id_15(unit, cand, normalized, flat_span, text, page)` → deferred to 02-02 (returns None).
    - `_check_bank_account(unit, cand, normalized, flat_span, text, page)` → deferred to 02-02 (returns None).
    Add the imports at module top: `from privacyguard.pii.validators.uscc import validate_uscc`; `from privacyguard.pii.validators.bank_card import validate_bank_card`; `from privacyguard.pii.validators.email import validate_email, is_public_suffix_email`.
    Update the `detect` method's if/elif chain (insert AFTER the existing CN_PHONE branch):
    ```python
    if entity_hint == "CN_BANK_CARD":
        hit = self._check_bank_card(unit, cand, normalized, flat_span, text, page)
    elif entity_hint == "CN_EMAIL":
        hit = self._check_email(unit, cand, normalized, flat_span, text, page)
    elif entity_hint == "CN_USCC":
        hit = self._check_uscc(unit, cand, normalized, flat_span, text, page)
    elif entity_hint == "CN_VAT_INVOICE":
        hit = self._check_vat_invoice(unit, cand, normalized, flat_span, text, page)
    elif entity_hint == "CN_TAXPAYER_ID_15":
        hit = self._check_taxpayer_id_15(unit, cand, normalized, flat_span, text, page)
    elif entity_hint == "CN_BANK_ACCOUNT":
        hit = self._check_bank_account(unit, cand, normalized, flat_span, text, page)
    else:
        hit = self._check_phone(unit, cand, normalized)  # existing
    ```
    Each `_check_*` method mirrors Phase 1's `_check_phone` form: defensive `if not X_validator(normalized): return None`; compute page_offset via `map_flat_to_original`; compute page_rect via `page.search_for(normalized)` if page provided else placeholder rect; return `PIIHit(entity_type=..., page_offset=..., page_length=..., page_rect=..., confidence_tier=..., source=unit.source, mask_strategy=mask_for_entity(...), normalized=normalized, validator_passed=True)`.

    **privacyguard/pii/pdf_adapter.py** — Append two new functions preserving the existing `apply_pii_redactions` signature. Add at module top a font-name map (verified locally): `_FONT_NAME_MAP: Dict[str, str] = {"Helvetica":"helv","Helvetica-Oblique":"heit","Helvetica-Bold":"hebo","Helvetica-BoldOblique":"hebi","Times-Roman":"tiro","Times-Bold":"tibo","Courier":"cour","Courier-Bold":"cobo"}`. Function `write_partial_masks(doc, page_idx, pii_hits, mode="partial")`: get `page = doc[page_idx]`; `fill_color = (0.0, 0.0, 0.0)`; first pass — for each hit, build `rect = fitz.Rect(pr[0], pr[1], pr[0]+pr[2], pr[1]+pr[3])` where `pr = hit.page_rect`; `annot = page.add_redact_annot(rect); annot.set_colors(stroke=fill_color, fill=fill_color); annot.update()`; then `page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)`; then `for annot in page.annots() or []: page.delete_annot(annot)`; if `mode == "blackout": return`; second pass (only partial mode) — for each hit, resolve font via `_resolve_font_for_rect(page, hit)`; build resized rect with `_resize_rect_for_mask(rect, hit.mask_strategy, font_size)`; compute `insert_x` / `insert_y` as center of resized rect minus half text width; `page.insert_text((insert_x, insert_y), hit.mask_strategy, fontsize=font_size, fontname=font_name, color=(1.0, 1.0, 1.0))` — color white on the black-fill background. Helper `_resolve_font_for_rect(page, hit)`: try `d = page.get_text("dict")`; iterate blocks/lines/spans; find span whose `bbox` y0 closest to `hit.page_offset` (or whose text contains `hit.normalized`); if found, return `(font_mapped, span_size)`; if NO span found (OCR / no-span branch — D-02 locked per CONTEXT D-02 + PATTERNS.md lines 670-675), return `("helv", float(max(hit.page_rect[3] - 4, 6)))` so the mask text scales to the redacted rect (NOT flat 11.0); floor of 6 prevents zero/negative size on degenerate rects; on any unexpected exception (rare — e.g., `get_text` failure) fall back to `("helv", 11.0)` as a true emergency default. Helper `_resize_rect_for_mask(rect, mask_text, fontsize)`: `avg_w = fontsize * 0.6`; `new_w = max(len(mask_text) * avg_w + 4.0, rect.width)`; center: `cx = (rect.x0 + rect.x1) / 2.0`; return `fitz.Rect(cx - new_w/2.0, rect.y0, cx + new_w/2.0, rect.y1)`.
    Function `clear_pdf_metadata(doc) -> None`: `doc.set_metadata({"title":"","author":"","subject":"","producer":"","creator":""})`. Single line — exactly 5 keys, all empty string (D-15).
    Update `__all__` to include `'write_partial_masks','clear_pdf_metadata'`.

    **privacyguard/pii/data/rules.json** — Append 4 new keys preserving the existing 2 (`phone_segment` / `id_card`). Schema (per 02-PATTERNS.md lines 715-754):
    ```json
    "bank_card": {
        "bin_dictionary_path": "privacyguard/pii/data/bin_prefixes.json",
        "luhn_required": true,
        "context_anchors": ["卡号","账号","银行","支付","debit","credit"],
        "context_window": 20,
        "length_range": [13, 19],
        "source": "ISO/IEC 7812 + 维基百科 Bank card number (CC BY-SA 4.0)",
        "last_verified": "2026-Q3",
        "next_review": "2026-Q4"
    },
    "uscc": {
        "weights": [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28],
        "charset": "0123456789ABCDEFGHJKLMNPQRTUWXY",
        "category_codes": ["1", "5", "9", "Y", "A", "N"],
        "standard": "GB 32100-2015"
    },
    "vat_invoice": {
        "context_anchors": ["发票","号码","票号","invoice","INVOICE","Invoice","增值税","电子发票","全电发票"],
        "context_window": 20,
        "length_8_required_anchor": true,
        "length_20_required_anchor": true,
        "source": "国家税务总局公告 2022 年第 1 号 + 传统 8 位票号",
        "last_verified": "2026-Q3"
    },
    "bank_account": {
        "context_anchors": ["账号","账户","银行账号","银行账户","招行","中行","建行","工商银行","农行","邮储","交通银行"],
        "context_window": 20,
        "context_required": true,
        "length_range": [9, 21],
        "source": "银行公开账户命名约定",
        "last_verified": "2026-Q3"
    }
    ```

    **privacyguard/pii/__init__.py** — Extend the existing Phase 1 `_LAZY_IMPORTS` (lines 38-52). Append to `__all__` (after line 34):
    `'validate_uscc','validate_bank_card','validate_email','has_vat_invoice_context','has_bank_account_context','partial_mask_uscc','partial_mask_bank_card','partial_mask_email','partial_mask_vat_invoice','partial_mask_taxpayer_id_15','partial_mask_bank_account','write_partial_masks','clear_pdf_metadata','BANK_CARD_BIN_WHITELIST','EMAIL_PUBLIC_SUFFIXES','USCC_CATEGORY_CODES','VAT_INVOICE_CONTEXTS','BANK_ACCOUNT_CONTEXTS'`.
    Append to `_LAZY_IMPORTS` (after line 51):
    - `'validate_uscc': ('privacyguard.pii.validators', 'validate_uscc')`
    - `'validate_bank_card': ('privacyguard.pii.validators', 'validate_bank_card')`
    - `'validate_email': ('privacyguard.pii.validators', 'validate_email')`
    - `'has_vat_invoice_context': ('privacyguard.pii.validators', 'has_vat_invoice_context')`
    - `'has_bank_account_context': ('privacyguard.pii.validators', 'has_bank_account_context')`
    - `'partial_mask_uscc': ('privacyguard.pii.mask', 'partial_mask_uscc')`
    - `'partial_mask_bank_card': ('privacyguard.pii.mask', 'partial_mask_bank_card')`
    - `'partial_mask_email': ('privacyguard.pii.mask', 'partial_mask_email')`
    - `'partial_mask_vat_invoice': ('privacyguard.pii.mask', 'partial_mask_vat_invoice')`
    - `'partial_mask_taxpayer_id_15': ('privacyguard.pii.mask', 'partial_mask_taxpayer_id_15')`
    - `'partial_mask_bank_account': ('privacyguard.pii.mask', 'partial_mask_bank_account')`
    - `'write_partial_masks': ('privacyguard.pii.pdf_adapter', 'write_partial_masks')`
    - `'clear_pdf_metadata': ('privacyguard.pii.pdf_adapter', 'clear_pdf_metadata')`
    - `'BANK_CARD_BIN_WHITELIST': ('privacyguard.pii.validators', 'BANK_CARD_BIN_WHITELIST')`
    - `'EMAIL_PUBLIC_SUFFIXES': ('privacyguard.pii.validators', 'EMAIL_PUBLIC_SUFFIXES')`
    - `'USCC_CATEGORY_CODES': ('privacyguard.pii.validators', 'USCC_CATEGORY_CODES')`
    - `'VAT_INVOICE_CONTEXTS': ('privacyguard.pii.validators', 'VAT_INVOICE_CONTEXTS')`
    - `'BANK_ACCOUNT_CONTEXTS': ('privacyguard.pii.validators', 'BANK_ACCOUNT_CONTEXTS')`
    **Note:** the `has_vat_invoice_context` / `has_bank_account_context` / `VAT_INVOICE_CONTEXTS` / `BANK_ACCOUNT_CONTEXTS` entries point to modules that 02-02 will create. To avoid ImportError on lazy access in 02-01, these 4 entries must be temporarily absent from `_LAZY_IMPORTS`. **Implementation strategy:** add ONLY the entries for uscc/bank_card/email + their constants (13 entries total); 02-02 adds the remaining 4. This is cleaner than having AttributeError fallbacks.

    **privacyguard/__init__.py** — Extend the existing `_LAZY_IMPORTS` similarly. Append to `__all__`:
    `'validate_uscc','validate_bank_card','validate_email','partial_mask_uscc','partial_mask_bank_card','partial_mask_email','partial_mask_vat_invoice','partial_mask_taxpayer_id_15','partial_mask_bank_account','write_partial_masks','clear_pdf_metadata'`.
    Append to `_LAZY_IMPORTS` (forwarding from privacyguard.pii subpackage):
    - `'validate_uscc': ('privacyguard.pii', 'validate_uscc')`
    - `'validate_bank_card': ('privacyguard.pii', 'validate_bank_card')`
    - `'validate_email': ('privacyguard.pii', 'validate_email')`
    - `'partial_mask_uscc': ('privacyguard.pii', 'partial_mask_uscc')`
    - `'partial_mask_bank_card': ('privacyguard.pii', 'partial_mask_bank_card')`
    - `'partial_mask_email': ('privacyguard.pii', 'partial_mask_email')`
    - `'write_partial_masks': ('privacyguard.pii', 'write_partial_masks')`
    - `'clear_pdf_metadata': ('privacyguard.pii', 'clear_pdf_metadata')`

    **tests/unit/test_package_imports.py** — Add a new test method inside `TestPrivacyGuardImports`:
    - `test_import_privacyguard_does_not_load_new_validators`: snapshot `sys.modules` filtered for `privacyguard.*`; pop them all; `importlib.import_module("privacyguard")`; touch `module.validate_safe_path`; assert `'privacyguard.pii.validators.uscc' not in sys.modules`; assert `'privacyguard.pii.validators.bank_card' not in sys.modules`; assert `'privacyguard.pii.validators.email' not in sys.modules`; restore sys.modules in finally.
    - `test_partial_masks_loads_on_demand`: snapshot; pop; `importlib.import_module("privacyguard")`; access `module.write_partial_masks`; assert `'privacyguard.pii.pdf_adapter' in sys.modules`.

    **tests/unit/test_convergence.py** — Add a new method inside `TestPiiConvergence`:
    - `test_main_py_does_not_inline_new_validators`: read `MAIN_PY.read_text()`; assert `"def validate_uscc(" not in source`; assert `"def validate_bank_card(" not in source`; assert `"def validate_email(" not in source`; assert `"def write_partial_masks(" not in source`; assert `"def clear_pdf_metadata(" not in source`.
    - `test_pii_package_no_inline_partial_mask_writer`: read all `privacyguard/pii/*.py` files; assert `"write_partial_masks" in <pdf_adapter.py>` and `"clear_pdf_metadata" in <pdf_adapter.py>`; assert no other PII file defines these functions.

    After all edits, run the full targeted test command from Task 1 PLUS Phase 1 baseline + Phase 1 PII tests; confirm all green.
  </action>
  <verify>
    <automated>python3 -m compileall -q main.py privacyguard tests && python3 -m unittest tests.unit.test_pii_validators.TestBankCardLuhn tests.unit.test_pii_validators.TestEmail tests.unit.test_pii_validators.TestUsccMod31 tests.unit.test_pii_engine.TestEngineUscc tests.unit.test_pdf_pii_redaction.TestPartialMaskWritesMaskText tests.unit.test_pdf_metadata_cleared.TestPdfMetadataCleared tests.unit.test_package_imports.TestPrivacyGuardImports tests.unit.test_convergence -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m unittest tests.unit.test_pdf_pii_redaction.TestPartialMaskWritesMaskText -v` shows `OK` for `test_partial_mask_writes_mask_text_for_uscc` — the partial mask text "911100********XXXX" is extractable AND the original 18-character USCC is NOT extractable.
    - OCR/placeholder rect path uses font size `max(hit.page_rect[3] - 4, 6)` (NOT flat 11.0) per CONTEXT D-02 / PATTERNS.md line 670-675; text-layer path uses `page.get_text("dict")` nearest span's `font + size` unchanged.
    - `python3 -m unittest tests.unit.test_pdf_metadata_cleared.TestPdfMetadataCleared -v` shows `OK` for `test_metadata_5_fields_cleared` — all 5 fields == "" after clear.
    - `python3 -m unittest tests.unit.test_pdf_pii_redaction.TestPartialMaskWritesMaskText.test_partial_mask_blackout_mode_destroys_only -v` shows `OK` — blackout mode leaves NO mask text AND destroys original.
    - `python3 -m unittest tests.unit.test_package_imports -v` shows all existing methods + the 2 new methods green.
    - `python3 -m unittest tests.unit.test_convergence -v` shows all existing classes + `TestPiiConvergence` extended methods green.
    - Full Phase 1 baseline (`tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence`) remains 79/79 green.
    - Live: `python3 -c "from privacyguard import write_partial_masks, clear_pdf_metadata; print('OK')"` prints `OK` (top-level lazy import works).
    - Live: `python3 -c "import privacyguard, sys; assert 'privacyguard.pii.pdf_adapter' not in sys.modules; assert 'privacyguard.pii.validators.uscc' not in sys.modules; privacyguard.validate_safe_path; assert 'privacyguard.pii.pdf_adapter' not in sys.modules; assert 'privacyguard.pii.validators.uscc' not in sys.modules; print('OK')"` prints `OK` (OPS-03 still enforced).
  </acceptance_criteria>
  <done>
    The 5 remaining RED tests from Task 1 now pass (partial mask + metadata clear + engine detect for USCC/bank card/email); Phase 1 baseline + Phase 1 PII tests remain green; OPS-03 lazy contract extended to the 6 new validators; convergence test ensures main.py contains no inline validator / partial mask / metadata clear implementations; pdf_adapter.py now exports write_partial_masks + clear_pdf_metadata + the existing apply_pii_redactions.
  </done>
  <reversibility>rating="costly" rationale="Adds two new public functions to pdf_adapter (write_partial_masks + clear_pdf_metadata) and 3 new _check_* methods to PIIEngine.detect. Reverting requires coordinated changes across engine.py + pdf_adapter.py + privacyguard/pii/__init__.py + privacyguard/__init__.py + 02-02 plan that depends on these."</reversibility>
</task>

<task type="auto">
  <name>Update tests/fixtures/fake_pii.py with 7 new fake_* functions + verify full pipeline</name>
  <files>
    - tests/fixtures/fake_pii.py
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 1153-1232 — fake_pii.py extension patterns with all 7 new fake_* functions + 2 invalid variants)
    - tests/fixtures/fake_pii.py (current Phase 1 fake_id_card / fake_phone / fake_phone_invalid form to mirror)
    - privacyguard.pii.validators.uscc.compute_uscc_check_digit (used by fake_uscc)
    - privacyguard.pii.validators.bank_card.luhn_check (used by fake_bank_card)
  </read_first>
  <action>
    Extend `tests/fixtures/fake_pii.py` with the full set of 7 new fake_* synthesizers (per 02-PATTERNS.md lines 1167-1232 — the spec has explicit function bodies). The functions must use loop-with-check (Faker + checksum compute) to ensure synthesized entities always pass their respective validators. Lazy-import the validators inside each function so this fixture module itself stays importable even before validators land.

    Append these functions to the existing `fake_pii.py`:
    - `fake_bank_card(bin_prefix='622576') -> str`: import `luhn_check` from `privacyguard.pii.validators.bank_card` inside function; `while True: body = bin_prefix + ''.join(random.choice('0123456789') for _ in range(9)); digits = [int(c) for c in body[::-1]]; total = sum(((d*2 if i%2==0 else d) - (9 if i%2==0 and d*2 > 9 else 0)) for i, d in enumerate(digits)); check = (10 - total%10) % 10; full = body + str(check); if luhn_check(full): return full`.
    - `fake_email(local=None, tld='example.com') -> str`: `local = local or ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(8)); return f"{local}@{tld}"`.
    - `fake_uscc(category='9') -> str`: import `USCC_CHARSET` + `compute_uscc_check_digit` + `validate_uscc` from `privacyguard.pii.validators.uscc`; `cat = random.choice(['1','5','9','Y','A','N']) if category == 'random' else category`; `while True: body17 = cat + ''.join(random.choice(USCC_CHARSET) for _ in range(16)); full = body17 + compute_uscc_check_digit(body17); if validate_uscc(full): return full`.
    - `fake_uscc_invalid_category() -> str`: returns the fixed string `"Z11000000000000000"` (category Z not in whitelist; any check digit).
    - `fake_vat_invoice_8() -> str`: returns `''.join(random.choice('0123456789') for _ in range(8))`.
    - `fake_vat_invoice_20() -> str`: returns `''.join(random.choice('0123456789') for _ in range(20))`.
    - `fake_taxpayer_id_15() -> str`: returns `random.choice(['11','12','31','33','44','51','61']) + ''.join(random.choice('0123456789') for _ in range(13))` (6-7-4 structure with valid admin prefix).
    - `fake_bank_account() -> str`: returns `''.join(random.choice('0123456789') for _ in range(18))` (18 digits within 9-21 range).

    Add `import random` at module top if not already present.

    Live smoke check after this task: `python3 -c "from tests.fixtures.fake_pii import fake_uscc, fake_email, fake_bank_card, fake_vat_invoice_8, fake_vat_invoice_20, fake_taxpayer_id_15, fake_bank_account; print(fake_uscc(), fake_email(), fake_bank_card(), fake_vat_invoice_8(), fake_vat_invoice_20(), fake_taxpayer_id_15(), fake_bank_account())"`. Each fake_* call must return a string; the synthesizers must NEVER hang (loop-with-check has finite expected iterations).
  </action>
  <verify>
    <automated>python3 -c "from tests.fixtures.fake_pii import fake_uscc, fake_email, fake_bank_card, fake_vat_invoice_8, fake_vat_invoice_20, fake_taxpayer_id_15, fake_bank_account; u = fake_uscc(); e = fake_email(); b = fake_bank_card(); v8 = fake_vat_invoice_8(); v20 = fake_vat_invoice_20(); t15 = fake_taxpayer_id_15(); ba = fake_bank_account(); print(len(u), len(e.split('@')[0]), len(b), len(v8), len(v20), len(t15), len(ba))"</automated>
  </verify>
  <acceptance_criteria>
    - Live command prints `18 8 16 8 20 15 18` (lengths of fake_uscc / local part / fake_bank_card / fake_vat_invoice_8 / fake_vat_invoice_20 / fake_taxpayer_id_15 / fake_bank_account).
    - `python3 -c "from privacyguard.pii.validators.uscc import validate_uscc; from tests.fixtures.fake_pii import fake_uscc; print(validate_uscc(fake_uscc()))"` prints `True` (synthesizer always passes validator).
    - `python3 -c "from privacyguard.pii.validators.bank_card import luhn_check; from tests.fixtures.fake_pii import fake_bank_card; print(luhn_check(fake_bank_card()))"` prints `True`.
    - `python3 -m compileall -q tests/fixtures/fake_pii.py` exits 0.
    - `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine.TestEngineUscc tests.unit.test_pii_engine.TestEngineBankCard tests.unit.test_pii_engine.TestEngineEmail -v` shows all green (no regression from fixture change).
  </acceptance_criteria>
  <done>
    7 new fake_* synthesizers + 2 invalid variants are available for all Phase 2 test suites; all validators pass on synthesized data; no infinite loops; existing Phase 1 fixtures (fake_id_card / fake_phone / fake_phone_invalid) unchanged.
  </done>
  <reversibility>rating="reversible" rationale="Test fixture additions only; removal reverts cleanly."</reversibility>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Human verify: open PrivacyGuard → check 9-entity scope label + main toolbar toggle wiring</name>
  <how-to-verify>
    Open the PrivacyGuard application via `python3 main.py`. Open Settings dialog, locate the "5. 隐私识别" tab card. Confirm the read-only label now reads "扫描范围：9 类实体（身份证 / 手机 / 银行卡 / 邮箱 / USCC / 纳税人识别号 / VAT 发票号 / 银行账号）" instead of the Phase 1 "身份证号 / 手机号". This confirms 02-01's downstream visibility contract lands cleanly even though the SettingsDialog per-entity table is in 02-03.

    (If the label still shows the Phase 1 form because 02-03 hasn't wired SettingsDialog yet, report "Settings scope label NOT yet updated" — this is expected at this stage; do NOT fail the verification.)

    For 02-01 verification, confirm the unit tests + reverse-extraction tests pass — the user-visible UI changes (per-entity table, toolbar toggle) ship in 02-03.
  </how-to-verify>
  <resume-signal>Type "approved" to confirm the 9-entity detection scope is correct (even if UI wiring is deferred to 02-03). If a unit test is red, paste the failing test name + traceback.</resume-signal>
</task>

</tasks>

## Artifacts this phase produces

**Public dataclasses / classes / functions (created in 02-01):**
- `privacyguard.pii.validators.uscc.compute_uscc_check_digit / validate_uscc / USCC_CHARSET / USCC_WEIGHTS / USCC_CATEGORY_CODES`
- `privacyguard.pii.validators.bank_card.luhn_check / load_bin_whitelist / get_bin_whitelist / validate_bank_card / BANK_CARD_BIN_WHITELIST`
- `privacyguard.pii.validators.email.validate_email / is_public_suffix_email / EMAIL_RE / EMAIL_PUBLIC_SUFFIXES`
- `privacyguard.pii.regex_patterns._BANK_CARD_RE / _EMAIL_RE / _USCC_RE / _VAT_INVOICE_8_RE / _VAT_INVOICE_20_RE / _TAXPAYER_ID_15_RE / _BANK_ACCOUNT_RE`
- `privacyguard.pii.mask.partial_mask_bank_card / partial_mask_email / partial_mask_uscc / partial_mask_taxpayer_id_15 / partial_mask_vat_invoice / partial_mask_bank_account`
- `privacyguard.pii.engine.PIIEngine._check_bank_card / _check_email / _check_uscc / _check_vat_invoice / _check_taxpayer_id_15 / _check_bank_account` (last 3 stubbed as `return None` until 02-02)
- `privacyguard.pii.pdf_adapter.write_partial_masks / _FONT_NAME_MAP / _resolve_font_for_rect / _resize_rect_for_mask / clear_pdf_metadata`
- `privacyguard.pii.__init__` lazy exports: `validate_uscc, validate_bank_card, validate_email, partial_mask_uscc, partial_mask_bank_card, partial_mask_email, write_partial_masks, clear_pdf_metadata, BANK_CARD_BIN_WHITELIST, EMAIL_PUBLIC_SUFFIXES, USCC_CATEGORY_CODES`
- `privacyguard.__init__` top-level lazy exports: same set forwarded from privacyguard.pii subpackage

**New files (created in 02-01):**
- `privacyguard/pii/validators/uscc.py`
- `privacyguard/pii/validators/bank_card.py`
- `privacyguard/pii/validators/email.py`
- `tests/unit/test_pdf_metadata_cleared.py`

**Modified files (in 02-01):**
- `privacyguard/pii/validators/__init__.py` — 6 new lazy exports (uscc / bank_card / email)
- `privacyguard/pii/regex_patterns.py` — 7 new regex constants + 7 new yields in iter_candidate_strings
- `privacyguard/pii/mask.py` — 6 new partial_mask_* functions + mask_for_entity extended dispatch
- `privacyguard/pii/engine.py` — 6 new _check_* methods (3 active, 3 stubbed)
- `privacyguard/pii/pdf_adapter.py` — write_partial_masks + clear_pdf_metadata helpers
- `privacyguard/pii/data/rules.json` — bank_card / uscc / vat_invoice / bank_account schema sections
- `privacyguard/pii/__init__.py` — 13 new lazy exports + _LAZY_IMPORTS entries
- `privacyguard/__init__.py` — 8 new top-level lazy exports + _LAZY_IMPORTS forwarding entries
- `tests/fixtures/fake_pii.py` — 7 new fake_* synthesizers + 2 invalid variants
- `tests/unit/test_pii_validators.py` — 5 new test classes (TestBankCardLuhn / TestBankCardBin / TestEmail / TestUsccMod31 / TestUsccCategory)
- `tests/unit/test_pii_engine.py` — 3 new test classes (TestEngineUscc / TestEngineBankCard / TestEngineEmail)
- `tests/unit/test_pdf_pii_redaction.py` — new TestPartialMaskWritesMaskText class with 3 test methods
- `tests/unit/test_package_imports.py` — 2 new methods (lazy-load + partial_masks_loads_on_demand)
- `tests/unit/test_convergence.py` — 2 new methods (test_main_py_does_not_inline_new_validators + test_pii_package_no_inline_partial_mask_writer)

**Cross-plan deliverables (NOT in 02-01, deferred to 02-02 / 02-03):**
- 3 remaining validators (vat_invoice.py / bank_account.py / taxpayer_id.py full impl) — Plan 02-02
- `_check_vat_invoice / _check_taxpayer_id_15 / _check_bank_account` actual logic (currently stubbed) — Plan 02-02
- `privacyguard/pii/data/bin_prefixes.json` (~1.2万条) + `.LICENSE` file with CC BY-SA 4.0 attribution — Plan 02-03
- `MainWindow.save_pdf` PII path rewiring + `clear_pdf_metadata` call site insertion — Plan 02-03
- `SettingsDialog` per-entity table + toolbar mask_override toggle — Plan 02-03
- `config.json` + `config.json.template` `pii_settings.per_entity_default` field — Plan 02-03
- `packaging/windows/config/PrivacyGuard_windows.spec` + `packaging/macos/config/PrivacyGuard.spec` datas + hiddenimports — Plan 02-03

---

<verification>
After all tasks complete, the following command sequence must return all-green (the Phase 1 baseline 79/79 is preserved; new Phase 2 tests added; total ~89):

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
      tests.unit.test_pii_validators \
      tests.unit.test_pii_engine \
      tests.unit.test_pdf_pii_redaction \
      tests.unit.test_pdf_metadata_cleared \
      -v
```

Expected: Phase 1 baseline (79 tests) + Phase 1 PII additions (16 tests) + Phase 2 02-01 additions (~13 new tests across validators + engine + pdf_pii_redaction + pdf_metadata_cleared) = ~108 tests all green.

**Tracer-specific verification:**
- USCC `91110000600037341L` → `validate_uscc() returns True`, `partial_mask_uscc() returns "911100********41L"` (or similar first-6 + last-4 form), `fitz.open(out).get_text()` after `write_partial_masks` contains the partial mask string but NOT the first 6 chars of original USCC.
- `doc.set_metadata({title:'X', author:'Y', ...})` → after `clear_pdf_metadata` + `doc.save()` + reopen → `metadata["title"] == ""` (and same for author/subject/producer/creator); `metadata.get("creationDate", "")` is NOT cleared (D-14).
</verification>

<success_criteria>
- Tracer proven on USCC: opening a synthetic PDF containing one 18-character USCC triggers PII detection, write_partial_masks writes a visible mask string in the output PDF while destroying the original 18 characters, and clear_pdf_metadata empties the 5 metadata fields. The reverse-extraction via `fitz.open(out).get_text()` proves both safety floors.
- 3 new validators (uscc + bank_card + email) implemented and unit-tested; uscc rejects Z-prefixed category code regardless of mod-31-3 check digit; bank_card rejects Luhn failures; email validates against RFC 5322 simplified regex with public-TLD classification.
- write_partial_masks + clear_pdf_metadata functions exist in `privacyguard/pii/pdf_adapter.py`; the existing `apply_pii_redactions` signature is preserved.
- OPS-03 lazy contract extended: `import privacyguard` does not load `privacyguard.pii.validators.uscc` / `bank_card` / `email` or `privacyguard.pii.pdf_adapter`.
- Existing 79/79 baseline + Phase 1 16 PII tests still green; no regression in test_mixed_pdf_ocr / test_pdf_text_hit_dedup / test_package_imports / test_convergence.
- main.py contains no inline USCC validator / bank card validator / email validator / write_partial_masks / clear_pdf_metadata; convergence test enforces this.
- All 9 Phase 2 requirement IDs (NUM-04 / NUM-05 / FIN-01..04 / MASK-01 / MASK-02 / SAFE-03) are accounted for across 02-01 + 02-02 + 02-03; 02-01 covers FIN-01 (USCC validator + detect) + MASK-01 (write_partial_masks) + SAFE-03 (clear_pdf_metadata) end-to-end.

**Accepted test-coverage debt (deferred to Phase 8 OPS-06 / audit phase):**
- Partial-mask reverse-extraction tests cover USCC + ID card only (2 of 9 entity types); remaining 7 entity types (CN_BANK_CARD / CN_EMAIL / CN_TAXPAYER_ID / CN_TAXPAYER_ID_15 / CN_VAT_INVOICE 8/20 digit / CN_BANK_ACCOUNT) rely on the unified `write_partial_masks` helper test for shape correctness. Phase 8 OPS-06 audit will add per-entity reverse-extraction coverage when the real-document baseline is built.
- `MainWindow.save_pdf` runtime integration test only validates via static source-text convergence assertions; QApplication-bound runtime tests are deferred. Phase 7 candidate review UI (which exercises the same save loop) will surface any save_pdf wiring bugs at integration time.
- VAT 20-digit without context anchor (asserted HIGH per D-07 structural-uniqueness) is covered in Plan 02-02 via `TestEngineVatInvoice.test_detects_20_digit_without_context_still_high`.
- Full-suite test command in PLAN.md verification blocks omits `tests.unit.test_pii_pipeline` / `test_pii_offline` / `test_full_page_ocr` (Phase 1 contract — covered by 01-VERIFICATION.md 16/16 pass + Phase 1 ship; re-execution would be redundant).
</success_criteria>

<output>
Create `.planning/phases/02-pdf/02-01-tracer-SUMMARY.md` when done. Commit message: `feat(02-01): partial mask write + metadata clear tracer on USCC`.
</output>
