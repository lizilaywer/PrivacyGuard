---
phase: 02-pdf
plan: 02
slug: engine-expansion
type: execute
wave: 2
depends_on:
  - 02-01
files_modified:
  - privacyguard/pii/validators/vat_invoice.py
  - privacyguard/pii/validators/bank_account.py
  - privacyguard/pii/validators/taxpayer_id.py
  - privacyguard/pii/validators/__init__.py
  - privacyguard/pii/engine.py
  - privacyguard/pii/__init__.py
  - privacyguard/__init__.py
  - tests/unit/test_pii_validators.py
  - tests/unit/test_pii_engine.py
autonomous: true
requirements:
  - NUM-04
  - NUM-05
  - FIN-02
  - FIN-03
  - FIN-04
  - MASK-01
user_setup: []

estimate:
  tokens: 75000
  raw_tokens: 37500
  tasks: 4
  confidence: medium

must_haves:
  truths:
    - A synthetic PDF containing one 8-character VAT invoice number with a context anchor (e.g. "发票 12345678") → `PIIEngine.detect` returns 1 PIIHit with entity_type="CN_VAT_INVOICE" and confidence_tier="HIGH".
    - A synthetic PDF containing one 20-character VAT invoice number (digital invoice 全电发票) with a context anchor (e.g. "全电发票号码 23110000000012345678") → `PIIEngine.detect` returns 1 PIIHit with entity_type="CN_VAT_INVOICE" and confidence_tier="HIGH"; mask_strategy shows first 2 + last 2 of the 20 digits.
    - A synthetic PDF containing one 15-character taxpayer ID number with a valid admin prefix → `PIIEngine.detect` returns 1 PIIHit with entity_type="CN_TAXPAYER_ID_15" and confidence_tier="MEDIUM" (D-09: no strong checksum for 15-digit).
    - A synthetic PDF containing one 9-21 digit bank account number with a context anchor (e.g. "账号 6222021234567890") → `PIIEngine.detect` returns 1 PIIHit with entity_type="CN_BANK_ACCOUNT" and confidence_tier="HIGH".
    - A bank account number WITHOUT any context anchor (e.g. plain "6222021234567890" with no surrounding "账号/账户/银行" keyword) → `PIIEngine.detect` returns ZERO hits (D-08 strict context-required).
    - `partial_mask_vat_invoice("12345678")` returns `"12****78"` (first 2 + last 2).
    - `partial_mask_bank_account("622202123456789012")` returns `"6222**********9012"` (first 4 + last 4).
    - `partial_mask_taxpayer_id_15("110101800101001")` returns `"110101*****1001"` (first 6 + last 4).
    - All 5 remaining new entity validators (vat_invoice / bank_account / taxpayer_id) are lazy-loaded via `_LAZY_IMPORTS` (OPS-03 contract preserved).
    - All 02-01 tests + Phase 1 baseline (79/79) still green; no regression.
  artifacts:
    - privacyguard/pii/validators/vat_invoice.py (validate_vat_invoice_8 + validate_vat_invoice_20 + has_vat_invoice_context + VAT_INVOICE_CONTEXTS frozenset)
    - privacyguard/pii/validators/bank_account.py (validate_bank_account + has_bank_account_context + BANK_ACCOUNT_CONTEXTS frozenset with 4 generic + 6 big-5 + 5 股份制 + 2 城商行 keywords per 02-PATTERNS.md lines 322-327)
    - privacyguard/pii/validators/taxpayer_id.py (validate_taxpayer_id_15 + _TAXPAYER_15_ADMIN_PREFIX frozenset with 33 province codes per 02-PATTERNS.md lines 280-286)
    - privacyguard/pii/validators/__init__.py extended (4 new _LAZY_IMPORTS: validate_taxpayer_id_15 / has_vat_invoice_context / has_bank_account_context + 3 context/whitelist constants)
    - privacyguard/pii/engine.py extended (3 stubbed _check_* methods become real: _check_vat_invoice / _check_taxpayer_id_15 / _check_bank_account)
    - privacyguard/pii/__init__.py extended (4 new lazy exports: validate_taxpayer_id_15 / has_vat_invoice_context / has_bank_account_context / VAT_INVOICE_CONTEXTS / BANK_ACCOUNT_CONTEXTS — 5 symbols)
    - privacyguard/__init__.py extended (forward exports of validate_taxpayer_id_15)
    - tests/unit/test_pii_validators.py extended (4 new test classes: TestVatInvoice / TestBankAccount / TestTaxpayerId15 / TestVatInvoiceContextAnchor)
    - tests/unit/test_pii_engine.py extended (4 new test classes: TestEngineVatInvoice / TestEngineTaxpayerId15 / TestEngineBankAccount / TestEngineBankAccountNoContextRejected)
  key_links:
    - privacyguard.pii.engine.detect → _check_vat_invoice → privacyguard.pii.validators.vat_invoice.validate_vat_invoice_8 / validate_vat_invoice_20 + has_vat_invoice_context (FIN-02 gate: context anchor required for 8-digit, optional for 20-digit which is structurally unique)
    - privacyguard.pii.engine.detect → _check_bank_account → privacyguard.pii.validators.bank_account.validate_bank_account + has_bank_account_context (FIN-04 gate: context anchor REQUIRED — reject if no anchor)
    - privacyguard.pii.engine.detect → _check_taxpayer_id_15 → privacyguard.pii.validators.taxpayer_id.validate_taxpayer_id_15 (FIN-03 gate: structure + admin prefix whitelist; no checksum)
    - privacyguard.pii.engine.detect → mask_for_entity → partial_mask_vat_invoice / partial_mask_bank_account / partial_mask_taxpayer_id_15 (MASK-01: partial mask per entity)
    - privacyguard/__init__._LAZY_IMPORTS → privacyguard.pii.validators.{vat_invoice,bank_account,taxpayer_id} (OPS-03 lazy contract)
  prohibitions:
    - 不得让 `_check_bank_account` 在无上下文锥点时仍生成 candidate（D-08 强制 reject）
    - 不得让 VAT 8 位无锥点的纯数字序列在 confidence_tier=HIGH 出现；必须 MEDIUM（D-07 锁定）
    - 不得让 `validate_taxpayer_id_15` 复用 USCC 的 mod-31-3 校验（15 位无强校验位，独立 type 防御误判）
    - 不得让 3 个新 validator 子模块在 `import privacyguard` 时被 eager 加载（OPS-03）
    - 不得在测试夹具中夹带真实 VAT 票号 / 银行账号 / 15 位税号；fake_* 是唯一合成来源（OPS-05）
    - 不得让 `mask_for_entity` 在新增 entity_type 时被遗忘而 fallback 到 `'*' * len`；3 个新 type 必须显式 dispatch

threat_model:
  trust_boundaries:
    - {name: page text → engine.detect, description: untrusted text content; context anchor check happens AFTER length/format validation to avoid false positives on bare digit strings}
    - {name: bank account 9-21 digit string, description: ambiguous with order numbers / employee IDs / invoice numbers; bank_account context anchor gate prevents FP}
  stride:
    - {id: T-2-VAT-ANCHOR, category: Information Disclosure (false positive), component: privacyguard.pii.engine._check_vat_invoice, severity: medium, disposition: mitigate, mitigation: 8-digit VAT requires context anchor within ±20 chars; without anchor emit only as MEDIUM (D-07); 20-digit has natural structural uniqueness so anchor optional but recommended}
    - {id: T-2-BANK-ANCHOR, category: Information Disclosure (false positive), component: privacyguard.pii.engine._check_bank_account, severity: high, disposition: mitigate, mitigation: validate_bank_account returns False if has_bank_account_context check fails (no candidate emitted at all — D-08 strict); test_engine_bank_account_no_context_rejected asserts 0 hits}
    - {id: T-2-TAXPAYER-15, category: Tampering, component: privacyguard.pii.validators.taxpayer_id.validate_taxpayer_id_15, severity: medium, disposition: mitigate, mitigation: 15-digit path does NOT call validate_uscc; uses 33-element _TAXPAYER_15_ADMIN_PREFIX whitelist + 6-7-4 structure; no mod-31-3; confidence_tier=MEDIUM (D-09 locked)}
    - {id: T-2-ORDER-FP-2, category: Information Disclosure (false positive), component: privacyguard.pii.engine.detect overall, severity: medium, disposition: mitigate, mitigation: bank_account + VAT 8-digit both gated by context anchor; USCC + bank_card already gated by checksums + BIN; 15-digit taxpayer ID is MEDIUM (no auto-redact path) + admin prefix sanity}

---

<objective>
Extend the Phase 2 tracer with the 3 remaining new entity validators (VAT invoice, bank account, 15-digit taxpayer ID) and wire their detection into PIIEngine.detect. After this plan, the engine detects all 9 entity types (CN_ID_CARD / CN_PHONE / CN_BANK_CARD / CN_EMAIL / CN_USCC / CN_TAXPAYER_ID / CN_TAXPAYER_ID_15 / CN_VAT_INVOICE / CN_BANK_ACCOUNT) end-to-end.
</objective>

<purpose>
The 02-01 tracer proved the partial mask + metadata clear write paths on USCC. 02-02 extends the same proven chain to the remaining 5 new entities (NUM-04 bank card + NUM-05 email are already wired in 02-01; FIN-02 VAT + FIN-03 taxpayer ID + FIN-04 bank account land here). After 02-02 the engine is complete; 02-03 only adds SettingsDialog UI + toolbar toggle + bin_prefixes.json data + PyInstaller spec sync + main.py save loop rewiring.
</purpose>

<output>
- 3 new validators (vat_invoice.py / bank_account.py / taxpayer_id.py) — pure-function, lazy-loaded
- 3 _check_* methods become real (no longer stubbed return None)
- 4 new test classes in test_pii_validators.py
- 4 new test classes in test_pii_engine.py
- Lazy-load table at privacyguard/pii/__init__.py + privacyguard/__init__.py extended with 4 new symbols
- 02-01 + Phase 1 baseline all remain green
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
@.planning/phases/02-pdf/02-01-tracer-PLAN.md
@.planning/codebase/STRUCTURE.md
@CLAUDE.md
@privacyguard/pii/__init__.py
@privacyguard/pii/engine.py
@privacyguard/pii/validators/__init__.py
@privacyguard/pii/mask.py
@privacyguard/pii/regex_patterns.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>RED: write failing tests for vat_invoice / bank_account / taxpayer_id validators + engine integration</name>
  <files>
    - tests/unit/test_pii_validators.py
    - tests/unit/test_pii_engine.py
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 209-256 — vat_invoice.py exact validator pattern)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 265-296 — taxpayer_id.py validate_taxpayer_id_15 pattern with 33 admin prefixes)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 307-348 — bank_account.py validate_bank_account + has_bank_account_context pattern)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 257-268 — VAT 8位 / 20位 regex patterns verified locally; lines 301-309 — 15位 6-7-4 format)
    - tests/unit/test_pii_validators.py (existing TestUsccMod31 / TestBankCardLuhn class structures to mirror)
    - tests/unit/test_pii_engine.py (existing TestEngineUscc / TestEngineBankCard class structures to mirror)
    - privacyguard.pii.validators.__init__.py (existing 6 entries from 02-01 to extend)
  </read_first>
  <action>
    Append the following test classes to the existing `tests/unit/test_pii_validators.py` (do NOT delete existing Phase 1 / 02-01 tests):

    - `TestVatInvoice`: `test_8_digit_passes` (asserts `validate_vat_invoice_8('12345678') is True`); `test_8_digit_with_letters_rejected` (asserts `validate_vat_invoice_8('1234567a') is False`); `test_20_digit_passes` (asserts `validate_vat_invoice_20('12345678901234567890') is True`); `test_20_digit_with_hyphens_accepted` (asserts `validate_vat_invoice_20('1234-5678-9012-3456-7890') is True` — hyphens stripped); `test_20_digit_wrong_length_rejected` (asserts `validate_vat_invoice_20('1234567890') is False`); `test_non_string_rejected` (asserts `validate_vat_invoice_8(None) is False`); `test_context_anchor_zh` (asserts `has_vat_invoice_context('发票号码 12345678', '12345678') is True`); `test_context_anchor_en` (asserts `has_vat_invoice_context('invoice number 12345678', '12345678') is True`); `test_no_context_anchor_rejected` (asserts `has_vat_invoice_context('random text 12345678', '12345678') is False`).
    - `TestTaxpayerId15`: `test_valid_15_with_admin_prefix` (asserts `validate_taxpayer_id_15('110101800101001') is True`); `test_invalid_admin_prefix_rejected` (asserts `validate_taxpayer_id_15('990101800101001') is False` — 99 not in whitelist); `test_short_id_rejected` (asserts `validate_taxpayer_id_15('123') is False`); `test_with_hyphens_stripped` (asserts `validate_taxpayer_id_15('110101-800101-001') is True`); `test_does_not_use_uscc_checksum` (asserts `validate_taxpayer_id_15('91110000600037341L') is False` — 18-char USCC must not be valid as 15-digit taxpayer ID); `test_all_33_admin_prefixes_accepted` (loop over each province in {'11','12','13','14','15','21','22','23','31','32','33','34','35','36','37','41','42','43','44','45','46','50','51','52','53','54','61','62','63','64','65','71','81','82'}, assert prefix-only `f"{prefix}1234567890"` passes validate_taxpayer_id_15 — admin prefix whitelist sanity).
    - `TestBankAccount`: `test_18_digit_passes` (asserts `validate_bank_account('622202123456789012') is True`); `test_short_account_rejected` (asserts `validate_bank_account('12345678') is False` — 8 digits below 9-min); `test_long_account_rejected` (asserts `validate_bank_account('1' * 22) is False` — 22 digits above 21-max); `test_non_digit_rejected` (asserts `validate_bank_account('6222021234567890a') is False`); `test_context_anchor_zh_recognized` (asserts `has_bank_account_context('账号 622202123456789012', '622202123456789012') is True`); `test_context_anchor_bank_name_recognized` (asserts `has_bank_account_context('工商银行 622202', '622202') is True`); `test_no_context_anchor_rejected` (asserts `has_bank_account_context('random 622202123456789012', '622202123456789012') is False`); `test_all_context_keywords_present` (asserts each keyword in ['账号','账户','银行账号','银行账户','招行','中行','建行','工商银行','农行','邮储','交通银行'] is in BANK_ACCOUNT_CONTEXTS).

    Append the following test classes to `tests/unit/test_pii_engine.py`:
    - `TestEngineVatInvoice`: `test_detects_8_digit_with_zh_context` (TextUnit("发票号码 " + fake_vat_invoice_8(), "text") → 1 hit CN_VAT_INVOICE confidence_tier=HIGH); `test_detects_20_digit_with_full_context` (TextUnit("全电发票号码 " + fake_vat_invoice_20(), "text") → 1 hit CN_VAT_INVOICE confidence_tier=HIGH); `test_detects_20_digit_without_context_still_high` (TextUnit(fake_vat_invoice_20(), "text") → 1 hit CN_VAT_INVOICE confidence_tier=HIGH — warning #7 fix: locks 20-digit structural-uniqueness HIGH rule); `test_detects_8_digit_without_context_as_medium` (TextUnit(fake_vat_invoice_8(), "text") → 1 hit confidence_tier=MEDIUM — D-07).
    - `TestEngineTaxpayerId18` (NEW for warning #2 fix — D-09 双 type 契约): `test_detects_18_digit_as_cn_taxpayer_id` (TextUnit("三证合一 " + fake_uscc(), "text") → ≥1 PIIHit with entity_type="CN_TAXPAYER_ID" and confidence_tier=HIGH); `test_cn_uscc_and_cn_taxpayer_id_both_emitted` (TextUnit(fake_uscc(), "text") → 2 hits: one with entity_type="CN_USCC" and one with entity_type="CN_TAXPAYER_ID", both HIGH, both sharing the same mask_strategy).
    - `TestEngineTaxpayerId15`: `test_detects_15_digit_with_admin_prefix` (TextUnit("旧版税号 " + fake_taxpayer_id_15(), "text") → 1 hit CN_TAXPAYER_ID_15 confidence_tier=MEDIUM).
    - `TestEngineBankAccount`: `test_detects_with_zh_context` (TextUnit("银行账号 " + fake_bank_account(), "text") → 1 hit CN_BANK_ACCOUNT confidence_tier=HIGH); `test_rejects_without_context` (TextUnit(fake_bank_account(), "text") → 0 hits — D-08 strict); `test_rejects_short_account_even_with_context` (TextUnit("账号 12345678", "text") → 0 hits — too short).

    After all test files exist, run `python3 -m unittest tests.unit.test_pii_validators.TestVatInvoice tests.unit.test_pii_validators.TestTaxpayerId15 tests.unit.test_pii_validators.TestBankAccount tests.unit.test_pii_engine.TestEngineVatInvoice tests.unit.test_pii_engine.TestEngineTaxpayerId15 tests.unit.test_pii_engine.TestEngineBankAccount -v` and confirm all fail with `ModuleNotFoundError: No module named 'privacyguard.pii.validators.vat_invoice'` or `ModuleNotFoundError: No module named 'privacyguard.pii.validators.bank_account'` — RED state confirmed.

    This task writes NO production code under `privacyguard/pii/validators/` for vat_invoice/bank_account/taxpayer_id. The 3 modules do not yet exist; tests must fail with ModuleNotFoundError.
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_pii_validators.TestVatInvoice tests.unit.test_pii_validators.TestTaxpayerId15 tests.unit.test_pii_validators.TestBankAccount tests.unit.test_pii_engine.TestEngineVatInvoice tests.unit.test_pii_engine.TestEngineTaxpayerId15 tests.unit.test_pii_engine.TestEngineBankAccount -v 2>&1 | grep -E "(ModuleNotFoundError|ImportError|FAIL|ERROR)" | head -10</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m unittest tests.unit.test_pii_validators.TestVatInvoice -v` fails with ModuleNotFoundError pointing at `privacyguard.pii.validators.vat_invoice`.
    - `python3 -m unittest tests.unit.test_pii_validators.TestBankAccount -v` fails with ModuleNotFoundError pointing at `privacyguard.pii.validators.bank_account`.
    - `python3 -m unittest tests.unit.test_pii_validators.TestTaxpayerId15 -v` fails with ModuleNotFoundError pointing at `privacyguard.pii.validators.taxpayer_id`.
    - `python3 -m unittest tests.unit.test_pii_engine.TestEngineVatInvoice -v` fails with ModuleNotFoundError or AttributeError.
    - `python3 -m compileall -q tests/unit/test_pii_validators.py tests/unit/test_pii_engine.py` exits 0 (syntax green).
  </acceptance_criteria>
  <done>
    All 7 new test classes exist on disk; running them produces ModuleNotFoundError / ImportError / AttributeError (RED state); the test contracts for VAT / bank account / taxpayer ID validators + engine integration are in place so Task 2 has a verifiable GREEN target.
  </done>
  <reversibility>rating="reversible" rationale="Test additions only."</reversibility>
</task>

<task type="auto" tdd="true">
  <name>GREEN: implement vat_invoice.py + bank_account.py + taxpayer_id.py + extend validators/__init__.py + extend engine.py _check_* methods</name>
  <files>
    - privacyguard/pii/validators/vat_invoice.py
    - privacyguard/pii/validators/bank_account.py
    - privacyguard/pii/validators/taxpayer_id.py
    - privacyguard/pii/validators/__init__.py
    - privacyguard/pii/engine.py
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 209-256 — vat_invoice.py + D-07 context-anchor handling)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 265-296 — taxpayer_id.py validate_taxpayer_id_15 + 33 admin prefixes)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 307-348 — bank_account.py validate_bank_account + has_bank_account_context)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 357-398 — validators/__init__.py _LAZY_IMPORTS extension with the 4 new entries)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 257-268 — VAT 8位 + 20位 regex + format; lines 287-298 — bank account context anchor keywords + Claude's Discretion expansion to 16 keywords)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 301-309 — 15-digit taxpayer ID format)
    - privacyguard/pii/validators/id_card.py (Phase 1 reference for pure-function validator with frozen constants)
    - privacyguard/pii/validators/phone_segment.py (Phase 1 reference for white-list + is_* function pattern)
    - privacyguard/pii/validators/uscc.py (02-01 reference for the validator form with frozen constants + defensive checks)
    - privacyguard/pii/engine.py (Phase 1 reference for _check_id_card / _check_phone + dispatch; the 6 new _check_* methods are in 02-01, but only 3 are real; the 3 stubs are `_check_vat_invoice / _check_taxpayer_id_15 / _check_bank_account`)
  </read_first>
  <action>
    Implement the 3 remaining validators + extend engine._check_* methods to make Task 1's tests pass.

    **privacyguard/pii/validators/vat_invoice.py** — Mirror `validators/phone_segment.py` form. Module docstring "增值税发票号校验（FIN-02 + D-07 双格式 + 上下文锥点）". `VAT_INVOICE_CONTEXTS: Final = frozenset({"发票","号码","票号","invoice","INVOICE","Invoice","增值税","电子发票","全电发票","号码:","号:"})` (per 02-PATTERNS.md lines 226-229). Function `validate_vat_invoice_8(num8) -> bool`: `if not isinstance(num8, str) or len(num8) != 8 or not num8.isdigit(): return False`; return True. Function `validate_vat_invoice_20(num20) -> bool`: `if not isinstance(num20, str): return False`; `stripped = num20.replace("-","").replace(" ","")`; `if len(stripped) != 20 or not stripped.isdigit(): return False`; return True. Function `has_vat_invoice_context(text, target, window=20) -> bool`: `if not text or not target: return False`; `idx = text.find(target)`; `if idx < 0: return False`; `lo = max(0, idx - window); hi = min(len(text), idx + len(target) + window); window_text = text[lo:hi]`; return `any(ctx in window_text for ctx in VAT_INVOICE_CONTEXTS)`. `__all__ = ["validate_vat_invoice_8","validate_vat_invoice_20","has_vat_invoice_context","VAT_INVOICE_CONTEXTS"]`.

    **privacyguard/pii/validators/bank_account.py** — Mirror `validators/phone_segment.py` form. Module docstring "银行账号校验（FIN-04 + D-08 必查上下文锥点）". `BANK_ACCOUNT_CONTEXTS: Final = frozenset({...})` per 02-PATTERNS.md lines 322-327 + RESEARCH.md Claude's Discretion expansion: 4 generic (`账号`, `账户`, `银行账号`, `银行账户`) + 5 big-5 (`工商银行`, `农行`, `中行`, `建行`, `邮储`) + 7 股份制 (`招行`, `交通银行`, `中信`, `浦发`, `兴业`, `民生`, `平安`) + 1 城商行 (`上海银行`). Final keyword set: `{"账号","账户","银行账号","银行账户","工商银行","农行","中行","建行","邮储","招行","交通银行","中信","浦发","兴业","民生","平安","上海银行"}`. Function `validate_bank_account(account) -> bool`: `if not isinstance(account, str): return False`; `stripped = account.replace(" ","").replace("-","")`; `if not stripped.isdigit() or not (9 <= len(stripped) <= 21): return False`; return True. Function `has_bank_account_context(text, target, window=20) -> bool`: same form as vat_invoice has_* but checking BANK_ACCOUNT_CONTEXTS. `__all__ = ["validate_bank_account","has_bank_account_context","BANK_ACCOUNT_CONTEXTS"]`.

    **privacyguard/pii/validators/taxpayer_id.py** — Mirror `validators/id_card.py` form. Module docstring "纳税人识别号校验（FIN-03 + D-09 双 type）". `_TAXPAYER_15_ADMIN_PREFIX: Final = frozenset({"11","12","13","14","15","21","22","23","31","32","33","34","35","36","37","41","42","43","44","45","46","50","51","52","53","54","61","62","63","64","65","71","81","82"})` (33 codes per 02-PATTERNS.md lines 280-286). Function `validate_taxpayer_id_15(id15) -> bool`: `if not isinstance(id15, str): return False`; `stripped = id15.replace("-","").replace(" ","")`; `if len(stripped) != 15 or not stripped.isdigit(): return False`; return `stripped[:2] in _TAXPAYER_15_ADMIN_PREFIX`. (No mod-31-3 — D-09: 15 位 no strong checksum; the 18-bit CN_TAXPAYER_ID path uses validate_uscc directly in engine.py). `__all__ = ["validate_taxpayer_id_15","_TAXPAYER_15_ADMIN_PREFIX"]`.

    **privacyguard/pii/validators/__init__.py** — Append to `__all__`: `'validate_taxpayer_id_15','has_vat_invoice_context','has_bank_account_context','VAT_INVOICE_CONTEXTS','BANK_ACCOUNT_CONTEXTS'`. Append to `_LAZY_IMPORTS`:
    - `'validate_taxpayer_id_15': ('privacyguard.pii.validators.taxpayer_id', 'validate_taxpayer_id_15')`
    - `'has_vat_invoice_context': ('privacyguard.pii.validators.vat_invoice', 'has_vat_invoice_context')`
    - `'has_bank_account_context': ('privacyguard.pii.validators.bank_account', 'has_bank_account_context')`
    - `'VAT_INVOICE_CONTEXTS': ('privacyguard.pii.validators.vat_invoice', 'VAT_INVOICE_CONTEXTS')`
    - `'BANK_ACCOUNT_CONTEXTS': ('privacyguard.pii.validators.bank_account', 'BANK_ACCOUNT_CONTEXTS')`

    **privacyguard/pii/engine.py** — Replace the 3 stubbed `_check_*` methods from 02-01 with real implementations. Each method follows the Phase 1 `_check_id_card` form:
    - **NEW (warning #2 fix — D-09 双 type 契约)**: Extend `iter_candidate_strings` to yield a SECOND pass for the 18-bit USCC regex that emits `entity_hint="CN_TAXPAYER_ID"` (in addition to the existing `entity_hint="CN_USCC"` pass on the same regex). Add a thin `_check_taxpayer_id(self, unit, cand, normalized, flat_span, text, page)` method that re-uses `validate_uscc` (same 18-bit string, same GB 32100 mod-31-3 gate) and emits `PIIHit(entity_type="CN_TAXPAYER_ID", ...)`. The `partial_mask_uscc` function in `mask.py` already dispatches to `partial_mask_uscc` for both `CN_USCC` and `CN_TAXPAYER_ID` (verified at 02-01 line 301: `if entity_type in ("CN_USCC","CN_TAXPAYER_ID"): return partial_mask_uscc(...)`). This satisfies CONTEXT D-09: `CN_USCC` for general USCC detection, `CN_TAXPAYER_ID` for 纳税人识别号-shaped 18-bit hits. The 15-bit `CN_TAXPAYER_ID_15` remains independent (no mod-31-3 reuse) per D-09.
    - `_check_vat_invoice(self, unit, cand, normalized, flat_span, text, page)`: if not (validate_vat_invoice_8(normalized) or validate_vat_invoice_20(normalized)): return None; compute page_offset via map_flat_to_original; compute page_rect via page.search_for(normalized) if page else placeholder; has_anchor = has_vat_invoice_context(text, normalized); confidence_tier = "HIGH" if (validate_vat_invoice_20(normalized) or has_anchor) else "MEDIUM" (D-07: 8位 no anchor = MEDIUM, 20位 naturally unique gets HIGH regardless); mask_strategy = mask_for_entity("CN_VAT_INVOICE", normalized); return PIIHit(entity_type="CN_VAT_INVOICE", page_offset=page_offset, page_length=len(normalized), page_rect=page_rect, confidence_tier=confidence_tier, source=unit.source, mask_strategy=mask_strategy, normalized=normalized, validator_passed=True).
    - `_check_taxpayer_id_15(self, unit, cand, normalized, flat_span, text, page)`: if not validate_taxpayer_id_15(normalized): return None; confidence_tier = "MEDIUM" (D-09: no strong checksum); mask_strategy = mask_for_entity("CN_TAXPAYER_ID_15", normalized); return PIIHit(entity_type="CN_TAXPAYER_ID_15", page_offset=page_offset, page_length=len(normalized), page_rect=page_rect, confidence_tier="MEDIUM", source=unit.source, mask_strategy=mask_strategy, normalized=normalized, validator_passed=True).
    - `_check_bank_account(self, unit, cand, normalized, flat_span, text, page)`: if not validate_bank_account(normalized): return None; **STRICT context anchor gate (D-08)**: if not has_bank_account_context(text, normalized): return None (no candidate emitted); compute page_offset + page_rect; mask_strategy = mask_for_entity("CN_BANK_ACCOUNT", normalized); return PIIHit(entity_type="CN_BANK_ACCOUNT", page_offset=page_offset, page_length=len(normalized), page_rect=page_rect, confidence_tier="HIGH", source=unit.source, mask_strategy=mask_strategy, normalized=normalized, validator_passed=True).
    Add at module top imports: `from privacyguard.pii.validators.vat_invoice import validate_vat_invoice_8, validate_vat_invoice_20, has_vat_invoice_context`; `from privacyguard.pii.validators.bank_account import validate_bank_account, has_bank_account_context`; `from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15`.

    After all files exist, run the targeted test command from Task 1 and confirm GREEN. Run the full Phase 1 baseline + 02-01 + 02-02 to confirm no regression.
  </action>
  <verify>
    <automated>python3 -m compileall -q privacyguard/pii tests && python3 -m unittest tests.unit.test_pii_validators.TestVatInvoice tests.unit.test_pii_validators.TestTaxpayerId15 tests.unit.test_pii_validators.TestBankAccount tests.unit.test_pii_engine.TestEngineVatInvoice tests.unit.test_pii_engine.TestEngineTaxpayerId15 tests.unit.test_pii_engine.TestEngineBankAccount tests.unit.test_pii_validators.TestBankCardLuhn tests.unit.test_pii_validators.TestEmail tests.unit.test_pii_validators.TestUsccMod31 tests.unit.test_pii_engine.TestEngineUscc tests.unit.test_pdf_pii_redaction.TestPdfPiiRedaction tests.unit.test_pdf_metadata_cleared.TestPdfMetadataCleared -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m unittest tests.unit.test_pii_validators.TestVatInvoice tests.unit.test_pii_validators.TestTaxpayerId15 tests.unit.test_pii_validators.TestBankAccount -v` shows all test methods `OK`.
    - `python3 -m unittest tests.unit.test_pii_engine.TestEngineVatInvoice -v` shows `test_detects_8_digit_with_zh_context` + `test_detects_8_digit_without_context_as_medium` + `test_detects_20_digit_without_context_still_high` all `OK` — context anchor gate correctly demotes 8-digit-only to MEDIUM; 20-digit always HIGH per structural-uniqueness rule.
    - `python3 -m unittest tests.unit.test_pii_engine.TestEngineTaxpayerId18 -v` shows `test_detects_18_digit_as_cn_taxpayer_id` + `test_cn_uscc_and_cn_taxpayer_id_both_emitted` both `OK` — 18-bit USCC regex yields BOTH `CN_USCC` and `CN_TAXPAYER_ID` (D-09 双 type 契约, warning #2 fix).
    - `python3 -m unittest tests.unit.test_pii_engine.TestEngineBankAccount -v` shows `test_rejects_without_context` returning 0 hits (D-08 strict) AND `test_detects_with_zh_context` returning 1 hit CN_BANK_ACCOUNT.
    - `python3 -m unittest tests.unit.test_pii_validators.TestBankCardLuhn tests.unit.test_pii_validators.TestUsccMod31 tests.unit.test_pdf_pii_redaction.TestPartialMaskWritesMaskText tests.unit.test_pdf_metadata_cleared.TestPdfMetadataCleared -v` (all 02-01 tests) remain green.
    - Full Phase 1 baseline 79/79 still green.
    - `python3 -c "from privacyguard import validate_taxpayer_id_15, has_vat_invoice_context, has_bank_account_context; print('OK')"` prints `OK` (top-level lazy import works for the new symbols).
    - `python3 -c "import privacyguard, sys; assert 'privacyguard.pii.validators.vat_invoice' not in sys.modules; assert 'privacyguard.pii.validators.bank_account' not in sys.modules; assert 'privacyguard.pii.validators.taxpayer_id' not in sys.modules; privacyguard.validate_safe_path; assert 'privacyguard.pii.validators.vat_invoice' not in sys.modules; print('OK')"` prints `OK` (OPS-03 lazy contract extended).
  </acceptance_criteria>
  <done>
    All 7 RED tests from Task 1 now pass; 3 new validators (vat_invoice / bank_account / taxpayer_id) implemented and lazy-loaded; 3 previously-stubbed engine._check_* methods now real; bank account strict context anchor gate enforced (no candidate without anchor); VAT 8-digit without anchor correctly demoted to MEDIUM; full Phase 1 + 02-01 baselines remain green.
  </done>
  <reversibility>rating="costly" rationale="Adds 3 new public validators + 3 real _check_* methods + 5 new lazy exports. Reverting requires coordinated changes across validators/* + validators/__init__.py + privacyguard/pii/__init__.py + privacyguard/__init__.py + engine.py."</reversibility>
</task>

<task type="auto">
  <name>Extend privacyguard/pii/__init__.py + privacyguard/__init__.py lazy tables with the 5 new Phase 2 symbols</name>
  <files>
    - privacyguard/pii/__init__.py
    - privacyguard/__init__.py
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 791-848 — __init__.py + privacyguard/__init__.py _LAZY_IMPORTS extension)
    - privacyguard/pii/__init__.py (current state with 13 new entries from 02-01 to extend with 5 more)
    - privacyguard/__init__.py (current state with 8 new entries from 02-01 to extend with 1 more)
    - privacyguard/pii/validators/__init__.py (after Task 2 — 5 new _LAZY_IMPORTS entries)
  </read_first>
  <action>
    Extend the lazy-load tables with the 5 new symbols (validate_taxpayer_id_15 / has_vat_invoice_context / has_bank_account_context / VAT_INVOICE_CONTEXTS / BANK_ACCOUNT_CONTEXTS).

    In `privacyguard/pii/__init__.py`:
    - Append to `__all__` (after the 13 entries added in 02-01): `'validate_taxpayer_id_15','has_vat_invoice_context','has_bank_account_context','VAT_INVOICE_CONTEXTS','BANK_ACCOUNT_CONTEXTS'`.
    - Append to `_LAZY_IMPORTS` (after the 13 entries from 02-01):
      - `'validate_taxpayer_id_15': ('privacyguard.pii.validators', 'validate_taxpayer_id_15')`
      - `'has_vat_invoice_context': ('privacyguard.pii.validators', 'has_vat_invoice_context')`
      - `'has_bank_account_context': ('privacyguard.pii.validators', 'has_bank_account_context')`
      - `'VAT_INVOICE_CONTEXTS': ('privacyguard.pii.validators', 'VAT_INVOICE_CONTEXTS')`
      - `'BANK_ACCOUNT_CONTEXTS': ('privacyguard.pii.validators', 'BANK_ACCOUNT_CONTEXTS')`

    In `privacyguard/__init__.py`:
    - Append to `__all__`: `'validate_taxpayer_id_15','has_vat_invoice_context','has_bank_account_context'`.
    - Append to `_LAZY_IMPORTS`:
      - `'validate_taxpayer_id_15': ('privacyguard.pii', 'validate_taxpayer_id_15')`
      - `'has_vat_invoice_context': ('privacyguard.pii', 'has_vat_invoice_context')`
      - `'has_bank_account_context': ('privacyguard.pii', 'has_bank_account_context')`

    After edits, run `python3 -c "from privacyguard import validate_taxpayer_id_15, has_vat_invoice_context, has_bank_account_context; print('OK')"` to verify lazy import path resolves correctly.
  </action>
  <verify>
    <automated>python3 -m compileall -q privacyguard && python3 -c "from privacyguard import validate_taxpayer_id_15, has_vat_invoice_context, has_bank_account_context; print('OK')" && python3 -m unittest tests.unit.test_package_imports tests.unit.test_convergence tests.unit.test_pii_validators tests.unit.test_pii_engine -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -c "from privacyguard import validate_taxpayer_id_15, has_vat_invoice_context, has_bank_account_context; print('OK')"` prints `OK`.
    - `python3 -c "from privacyguard.pii.validators import BANK_ACCOUNT_CONTEXTS; print(len(BANK_ACCOUNT_CONTEXTS))"` prints a number >= 17 (per 02-PATTERNS.md + Claude's Discretion expansion).
    - `python3 -c "from privacyguard.pii.validators import VAT_INVOICE_CONTEXTS; print(len(VAT_INVOICE_CONTEXTS))"` prints a number >= 11.
    - `python3 -m unittest tests.unit.test_package_imports tests.unit.test_convergence tests.unit.test_pii_validators tests.unit.test_pii_engine -v` shows all green.
    - `python3 -m compileall -q privacyguard` exits 0.
    - Full Phase 1 baseline (test_mixed_pdf_ocr / test_path_validation / test_ocr_api / test_package_imports / test_pdf_text_hit_dedup / test_app_config / test_word_replace_rules / test_batch_word_replace / test_config_alignment / test_fstring_safety / test_convergence) still 79/79 green.
  </acceptance_criteria>
  <done>
    The 5 new Phase 2 symbols (validate_taxpayer_id_15 + 2 has_*_context + 2 *_CONTEXTS) are reachable via top-level `from privacyguard import ...` lazy access; OPS-03 lazy contract fully extended across the 6 new validators + their context anchor helpers + their whitelist constants; full test suite remains green.
  </done>
  <reversibility>rating="reversible" rationale="Lazy table additions only; removal reverts cleanly."</reversibility>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Human verify: confirm engine detects all 9 entity types via unit test green light + synthetic PDF live demo</name>
  <how-to-verify>
    Run the comprehensive live engine smoke from a Python REPL:
    ```python
    from privacyguard import PIIEngine, TextUnit
    from tests.fixtures.fake_pii import (
        fake_id_card, fake_phone, fake_bank_card, fake_email,
        fake_uscc, fake_vat_invoice_8, fake_vat_invoice_20,
        fake_taxpayer_id_15, fake_bank_account,
    )
    engine = PIIEngine()
    # Compose a text containing all 9 entity types with their context anchors
    text = (
        f"测试样本 身份证 {fake_id_card()} 手机 {fake_phone()} "
        f"卡号 {fake_bank_card()} 邮箱 {fake_email()} "
        f"统一信用代码 {fake_uscc()} "
        f"发票号码 {fake_vat_invoice_8()} 全电发票 {fake_vat_invoice_20()} "
        f"旧版税号 {fake_taxpayer_id_15()} "
        f"账号 {fake_bank_account()}"
    )
    hits = engine.detect(TextUnit(page_index=0, text=text, source="text"))
    print(f"hit count: {len(hits)}")
    for h in hits:
        print(f"  {h.entity_type} | tier={h.confidence_tier} | mask={h.mask_strategy}")
    ```

    Expected output: hit count >= 9 (one per entity type). Each entity_type in the printed list matches {CN_ID_CARD, CN_PHONE, CN_BANK_CARD, CN_EMAIL, CN_USCC, CN_VAT_INVOICE, CN_TAXPAYER_ID_15, CN_BANK_ACCOUNT}. CN_TAXPAYER_ID_15 should show tier=MEDIUM; all others HIGH (assuming bank_card has a known BIN — see 02-03 for full BIN whitelist population).
  </how-to-verify>
  <resume-signal>Type "approved" if hit count >= 9 and all 8 expected entity_types appear (CN_VAT_INVOICE may appear twice for 8+20 digits). If hit count is lower or types are missing, paste the printed hit list + which entity_types are missing.</resume-signal>
</task>

</tasks>

## Artifacts this phase produces

**Public dataclasses / classes / functions (created in 02-02):**
- `privacyguard.pii.validators.vat_invoice.validate_vat_invoice_8 / validate_vat_invoice_20 / has_vat_invoice_context / VAT_INVOICE_CONTEXTS`
- `privacyguard.pii.validators.bank_account.validate_bank_account / has_bank_account_context / BANK_ACCOUNT_CONTEXTS` (17 keywords per Claude's Discretion)
- `privacyguard.pii.validators.taxpayer_id.validate_taxpayer_id_15 / _TAXPAYER_15_ADMIN_PREFIX` (33 province codes)
- `privacyguard.pii.engine.PIIEngine._check_vat_invoice / _check_taxpayer_id_15 / _check_bank_account` (now real, no longer stubbed)
- `privacyguard.pii.__init__` lazy exports: `validate_taxpayer_id_15, has_vat_invoice_context, has_bank_account_context, VAT_INVOICE_CONTEXTS, BANK_ACCOUNT_CONTEXTS`
- `privacyguard.__init__` top-level lazy exports: `validate_taxpayer_id_15, has_vat_invoice_context, has_bank_account_context`

**New files (created in 02-02):**
- `privacyguard/pii/validators/vat_invoice.py`
- `privacyguard/pii/validators/bank_account.py`
- `privacyguard/pii/validators/taxpayer_id.py`

**Modified files (in 02-02):**
- `privacyguard/pii/validators/__init__.py` — 5 new _LAZY_IMPORTS + 5 new __all__ entries
- `privacyguard/pii/engine.py` — 3 _check_* methods now real (replace 02-01 stubs); 6 new imports at module top
- `privacyguard/pii/__init__.py` — 5 new lazy exports + _LAZY_IMPORTS entries
- `privacyguard/__init__.py` — 3 new top-level lazy exports + _LAZY_IMPORTS forwarding entries
- `tests/unit/test_pii_validators.py` — 3 new test classes (TestVatInvoice / TestTaxpayerId15 / TestBankAccount)
- `tests/unit/test_pii_engine.py` — 3 new test classes (TestEngineVatInvoice / TestEngineTaxpayerId15 / TestEngineBankAccount)

**Cross-plan deliverables (NOT in 02-02, deferred to 02-03):**
- `privacyguard/pii/data/bin_prefixes.json` (~1.2万条) + `.LICENSE` file — Plan 02-03
- `MainWindow.save_pdf` PII path rewiring + `clear_pdf_metadata` call site insertion — Plan 02-03
- `SettingsDialog` per-entity table + toolbar mask_override toggle — Plan 02-03
- `config.json` + `config.json.template` `pii_settings.per_entity_default` field — Plan 02-03
- `packaging/windows/config/PrivacyGuard_windows.spec` + `packaging/macos/config/PrivacyGuard.spec` datas + hiddenimports — Plan 02-03

---

<verification>
After all tasks complete, the following command sequence must return all-green (Phase 1 baseline 79 + Phase 1 PII 16 + Phase 2 02-01 ~13 + Phase 2 02-02 ~14 = ~122 tests):

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

Expected: ~122 tests all green.

**Engine-coverage verification:**
- 9 entity types all detectable: CN_ID_CARD / CN_PHONE / CN_BANK_CARD / CN_EMAIL / CN_USCC / CN_TAXPAYER_ID_15 / CN_VAT_INVOICE / CN_BANK_ACCOUNT (CN_TAXPAYER_ID 18-bit is the same code path as USCC)
- Bank account without context → 0 hits (D-08 strict)
- VAT 8-digit without context → MEDIUM tier (D-07)
- 15-digit taxpayer ID → MEDIUM tier (D-09 no strong checksum)
</verification>

<success_criteria>
- All 5 remaining new entity validators (vat_invoice / bank_account / taxpayer_id) implemented with proper format + context anchor / admin prefix / no-checksum gates.
- All 3 previously-stubbed `_check_*` engine methods are now real; the engine detects all 9 entity types end-to-end.
- Bank account strict context anchor gate enforced (no candidate without anchor; D-08).
- VAT 8-digit without anchor demoted to MEDIUM (D-07).
- 15-digit taxpayer ID always MEDIUM (D-09).
- All 02-01 + Phase 1 baselines remain green; no regression.
- 4 new test classes + 3 new test classes pass; ~122 tests total.
</success_criteria>

<output>
Create `.planning/phases/02-pdf/02-02-engine-expansion-SUMMARY.md` when done. Commit message: `feat(02-02): extend PII engine to 9 entity types (VAT + bank account + 15-digit taxpayer ID)`.
</output>
