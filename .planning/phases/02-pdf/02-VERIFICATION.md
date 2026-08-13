---
phase: 02-pdf
verified: 2026-08-11T14:55:00Z
status: gaps_found
score: 8/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
gaps:
  - truth: "MainWindow.save_pdf routes pii_list through write_partial_masks(doc_save, i, partial_hits, mode=\"partial\") + write_partial_masks(doc_save, i, blackout_hits, mode=\"blackout\")"
    status: failed
    reason: "v37.7.6 收敛原则 violation — main.py imports write_partial_masks at line 12626 but never calls it; re-implements the partial mask insert_text logic inline at lines 12685-12715 using page.insert_text directly."
    artifacts:
      - path: "main.py"
        issue: "main.py::save_pdf contains 1 reference to write_partial_masks (import only) and 0 call sites. The partial mask logic (font lookup + insert_text) is duplicated inline at lines 12685-12715 instead of being delegated to privacyguard.pii.pdf_adapter.write_partial_masks which is imported but unused."
      - path: "tests/unit/test_convergence.py"
        issue: "test_main_py_uses_write_partial_masks_in_save_loop only checks for string presence ('write_partial_masks' in source) — does not AST-verify the function is actually called inside save_pdf. This regression slipped through the v37.7.6 convergence gate."
      - path: "tests/unit/test_pdf_pii_redaction.py"
        issue: "test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata imports write_partial_masks (line 178) but never calls it; manually re-implements the inline mask logic at lines 240-258 (mirror of main.py inline code). Test name is misleading — it does NOT test the routing."
    missing:
      - "Refactor privacyguard.pii.pdf_adapter.write_partial_masks to accept mixed item types (PIIHit | Tuple[QRectF, str]) so the unified OCR + manual + PII partial/blackout dispatch can be delegated in a single call."
      - "Replace main.py lines 12651-12715 (OCR + manual + PII collection, add_redact_annot loop, apply_redactions, delete_annot, partial mask insert_text) with a single call: write_partial_masks(doc_save, i, all_pi_items)."
      - "Tighten test_convergence.py::test_main_py_uses_write_partial_masks_in_save_loop to AST-verify write_partial_masks is called inside save_pdf (not just referenced)."
      - "Replace the inline manual implementation in test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata with an actual write_partial_masks(doc_save, 0, [pii_hit], mode=\"partial\") call."
  - truth: "PrivacyGuard v37.7.6 收敛原则: main.py 必须调用 write_partial_masks + clear_pdf_metadata 而非内联实现"
    status: failed
    reason: "CR-01 from code review: main.py inline re-implementation of write_partial_masks is the central architectural regression of Phase 2. Inline version is feature-incomplete vs. the imported write_partial_masks (WR-02: font hardcoded as 'helv' instead of using _FONT_NAME_MAP; flat 11.0 fallback instead of max(rect.height-4, 6) for OCR; no _resize_rect_for_mask width widening for wide mask text)."
    artifacts:
      - path: "main.py:12685-12715"
        issue: "Inline partial mask insert_text re-implementation diverges from pdf_adapter.write_partial_masks in 3 ways: (1) font hardcoded as 'helv' instead of _FONT_NAME_MAP lookup, (2) flat 11.0 font size fallback instead of max(rect.height-4, 6), (3) no rect resize for wide mask text."
    missing:
      - "Delegate partial mask insert_text to privacyguard.pii.pdf_adapter.write_partial_masks to restore the 3 missing behaviors (font mapping, OCR font sizing, rect resize)."
  - truth: "engine.py 6 个新 validator 子模块在 import privacyguard.pii.engine 时不应被 eager 加载（OPS-03 懒加载契约）"
    status: partial
    reason: "WR-01 confirmed: privacyguard.pii.engine lines 32-48 eagerly import all 6 new validators (validate_uscc, validate_bank_card, validate_email, validate_vat_invoice, validate_bank_account, validate_taxpayer_id_15) at module top. Verified empirically: importing privacyguard.pii.engine triggers loading of all 6 modules into sys.modules. OPS-03 strict contract ('import privacyguard' does not load PII validators) is satisfied — but the spirit of CLAUDE.md constraint #2 is broken: there is no granular lazy access via the engine; PIIEngine loads them all."
    artifacts:
      - path: "privacyguard/pii/engine.py:32-48"
        issue: "All 6 new validator submodules are eagerly imported at engine.py module top. privacyguard.pii.validators.{uscc,bank_card,email,...} are individually lazy via __getattr__, but the only practical access path (PIIEngine) loads them all."
    missing:
      - "Either (a) accept and document current behavior (matches Phase 1 validator loading pattern), or (b) refactor engine.py to look up validators via importlib.import_module inside _check_* methods, allowing fine-grained lazy access."
  - truth: "has_bank_account_context 对文档内所有 bank account 候选都会检查上下文锥点"
    status: failed
    reason: "WR-04 confirmed: privacyguard.pii.validators.bank_account.has_bank_account_context line 56 uses text.find(target) which returns the first occurrence index. If a document contains multiple bare bank account candidates, only the first one's ±20 window is checked. The second candidate is rejected (no context in its window) but is never re-checked against its own occurrence's context."
    artifacts:
      - path: "privacyguard/pii/validators/bank_account.py:43-62"
        issue: "text.find(target) returns first occurrence only. Edge case for documents with multiple bare accounts not exercised by current tests."
    missing:
      - "Iterate all text.find(target, start) positions and return True if any has context. Or document this as a known limitation."
behavior_unverified_items: []
---

# Phase 02 (PDF) Verification Report

**Phase Goal:** Phase 2 — PDF 增加银行卡/邮箱/财税实体识别与部分掩码 (PDF adds bank card / email / fiscal-tax entity recognition + partial mask).

**Verified:** 2026-08-11T14:55:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | Phase 2 introduces 6 new entity types + 9 total end-to-end detection | ✓ VERIFIED | 9-entity smoke test produced 10 hits (CN_USCC + CN_TAXPAYER_ID share via D-09): CN_ID_CARD/CN_PHONE/CN_BANK_CARD/CN_EMAIL/CN_USCC/CN_TAXPAYER_ID/CN_VAT_INVOICE×2/CN_TAXPAYER_ID_15/CN_BANK_ACCOUNT. CN_TAXPAYER_ID_15 correctly MEDIUM, all others HIGH. |
| 2   | write_partial_masks writes partial mask text + destroys original | ✓ VERIFIED | TestPartialMaskWritesMaskText green: `assertNotIn(secret_id, out_text)` + `assertIn(mask_text, out_text)`. USCC `91110000600037341L` → "911100********XXXX" pattern via partial_mask_uscc. |
| 3   | clear_pdf_metadata clears 5 metadata fields | ✓ VERIFIED | TestPdfMetadataCleared.test_metadata_5_fields_cleared green; test_metadata_creation_date_preserved green (D-14 lock — CreationDate NOT touched); test_metadata_no_placeholder_strings green (D-15 lock — no 'Anonymous'/'Redacted'/'PyMuPDF'). |
| 4   | bin_prefixes.json ships with >= 10000 unique 6-digit BIN prefixes + CC BY-SA 4.0 LICENSE | ✓ VERIFIED | 19,890 entries, 175.1KB, all 6-char digits unique; LICENSE contains 'CC BY-SA' + 'Wikipedia'. |
| 5   | bank_card validator loads real whitelist via resource_path | ✓ VERIFIED | `get_bin_whitelist()` returns frozenset of 19,890 entries. `validate_bank_card(fake_bank_card(bin_prefix='622576'))` returns True. |
| 6   | MainWindow.save_pdf calls write_partial_masks + clear_pdf_metadata | ✗ FAILED | CR-01: main.py imports write_partial_masks (line 12626) but NEVER calls it. Re-implements partial mask insert_text inline at lines 12685-12715 using page.insert_text directly. Only clear_pdf_metadata is called (line 12719). |
| 7   | Toolbar btn_mask_override toggle + SettingsDialog 9-row per-entity table | ✓ VERIFIED | PHASE2_ENTITY_MODE_ROWS at line 203-213 (9 rows). SettingsDialog box_pii builds 9-row table at line 1672-1685. Toolbar btn_mask_override at line 5896-5901. _toggle_mask_override_this_doc at line 8781-8797. _open_pdf_file reset at line 10753-10759. |
| 8   | config.json + config.json.template contain per_entity_default 9-key + scan_scope 9-entry | ✓ VERIFIED | Both files: per_entity_default = 9 keys (all "partial"), scan_scope = 9 entity types in D-13 locked order (CN_TAXPAYER_ID before CN_TAXPAYER_ID_15). |
| 9   | OPS-03 lazy contract preserved + OPS-04 PyInstaller parity + OPS-07 baseline preservation | ⚠️ PARTIAL | OPS-03 strict contract satisfied: `import privacyguard` loads 0 PII modules. But spirit violated: PIIEngine eagerly loads all 6 new validators (WR-01). OPS-04 satisfied: both Windows + macOS specs contain 6 new hiddenimports (2 sites each in Windows, 1 in macOS); build_complete.sh has bin_prefixes.json parity check. OPS-07 satisfied: full 272-test suite passes. |

**Score:** 7/9 truths fully verified, 1 partial (OPS-03 spirit), 1 failed (CR-01 main.py convergence violation)

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `privacyguard/pii/validators/uscc.py` | USCC_CHARSET + USCC_WEIGHTS + USCC_CATEGORY_CODES + compute_uscc_check_digit + validate_uscc | ✓ VERIFIED | Module exists; USCC_CHARSET (31 chars), USCC_CATEGORY_CODES (6 chars frozenset); validate_uscc('91110000600037341L')=True, validate_uscc('Z11000000000000000')=False. |
| `privacyguard/pii/validators/bank_card.py` | luhn_check + load_bin_whitelist + get_bin_whitelist + validate_bank_card | ✓ VERIFIED | Module exists; luhn_check('4532015112830366')=True; get_bin_whitelist() returns 19,890 entries via resource_path (D-26 safe-fail on missing). |
| `privacyguard/pii/validators/email.py` | EMAIL_RE + EMAIL_PUBLIC_SUFFIXES + validate_email + is_public_suffix_email | ✓ VERIFIED | Module exists; validate_email('user@example.com')=True; is_public_suffix_email('foo@qq.com')=True; 10 public suffixes. |
| `privacyguard/pii/validators/vat_invoice.py` | validate_vat_invoice_8/20 + has_vat_invoice_context + VAT_INVOICE_CONTEXTS | ✓ VERIFIED | Module exists; 11 keywords; validate_vat_invoice_8('12345678')=True; validate_vat_invoice_20('12345678901234567890')=True. |
| `privacyguard/pii/validators/bank_account.py` | validate_bank_account + has_bank_account_context + BANK_ACCOUNT_CONTEXTS | ✓ VERIFIED | Module exists; 17 keywords; validate_bank_account('622202123456789012')=True. WR-04: has_bank_account_context uses text.find(target) (first occurrence only) — known limitation. |
| `privacyguard/pii/validators/taxpayer_id.py` | validate_taxpayer_id_15 + _TAXPAYER_15_ADMIN_D (34 | ⚠️ PARTIAL | Module exists; 34 admin prefixes; validate_taxpayer_id_15('110101800101001')=True; validate_taxpayer_id_15('990101800101001')=False (admin prefix gate). NO mod-31-3 reuse (D-09 lock). |
| `privacyguard/pii/pdf_adapter.py` | write_partial_masks + clear_pdf_metadata + _FONT_NAME_MAP + _resolve_font_for_rect + _resize_rect_for_mask | ✓ VERIFIED | Module exists; write_partial_masks and clear_pdf_metadata correctly implemented; PDF_REDACT_IMAGE_PIXELS used; no draw_rect in code. |
| `privacyguard/pii/mask.py` | 6 new partial_mask_* + mask_for_entity extended | ✓ VERIFIED | partial_mask_bank_card / email / uscc / vat_invoice / taxpayer_id_15 / bank_account all present; mask_for_entity dispatches all 9 types including CN_USCC and CN_TAXPAYER_ID sharing partial_mask_uscc (D-09). |
| `privacyguard/pii/engine.py` | PIIEngine.detect routes 9 entity_hints + _check_* methods | ✓ VERIFIED | detect dispatches all 9 entity_hints; _check_id_card / _check_phone / _check_bank_card / _check_email / _check_uscc / _check_taxpayer_id (D-09) / _check_vat_invoice / _check_taxpayer_id_15 / _check_bank_account all implemented (9 methods). WR-01: eagerly imports 6 new validators at module top (lazy spirit violated). |
| `privacyguard/pii/data/bin_prefixes.json` | >= 10000 unique 6-digit BIN prefixes | ✓ VERIFIED | 19,890 entries; 175.1KB; all 6-char digits; all unique. |
| `privacyguard/pii/data/bin_prefixes.json.LICENSE` | CC BY-SA 4.0 attribution with Wikipedia source | ✓ VERIFIED | File exists; contains 'CC BY-SA' and 'Wikipedia' keywords. |
| `privacyguard/pii/data/rules.json` | bank_card / uscc / vat_invoice / bank_account schema | ✓ VERIFIED | All 4 new schema sections present with context_anchors + length_range + standard fields. |
| `privacyguard/pii/__init__.py` | 19 new lazy exports + _LAZY_IMPORTS | ✓ VERIFIED | 19 new entries in _LAZY_IMPORTS forwarding to privacyguard.pii.validators/mask/pdf_adapter. |
| `privacyguard/__init__.py` | 11 new top-level lazy exports + _LAZY_IMPORTS forwarding | ✓ VERIFIED | 11 new entries forwarding to privacyguard.pii subpackage. |
| `config.json` | pii_settings.per_entity_default 9-key + scan_scope 9-entry | ✓ VERIFIED | per_entity_default = 9 keys, all "partial"; scan_scope = 9 entity types in locked order. |
| `config.json.template` | Same as config.json | ✓ VERIFIED | Identical structure. |
| `main.py` (SettingsDialog) | PHASE2_ENTITY_MODE_ROWS + 9-row per-entity table + 一括黑/括星 buttons | ✓ VERIFIED | PHASE2_ENTITY_MODE_ROWS at line 203-213 (D-13 locked order). 9-row table at line 1672-1685 with QCheckBox + QComboBox. 2 bulk flip buttons at line 1687-1696. save_settings persistence at line 2788-2794. |
| `main.py` (toolbar) | btn_mask_override toggle + _toggle_mask_override_this_doc + _open_pdf_file reset | ✓ VERIFIED | btn_mask_override at line 5896-5901. _toggle_mask_override_this_doc at line 8781-8797. _open_pdf_file reset (blockSignals + setChecked(False)) at line 10753-10759. |
| `main.py` (save_pdf) | write_partial_masks + clear_pdf_metadata integration | ✗ FAILED | **CR-01 confirmed**: imports write_partial_masks (line 12626) but never calls it. clear_pdf_metadata called (line 12719). Partial mask logic re-implemented inline at lines 12685-12715. |
| `packaging/windows/config/PrivacyGuard_windows.spec` | 6 new validator hiddenimports | ✓ VERIFIED | Lines 166-171 + 275-280 contain all 6 new validators (2 sites for B5 parity). |
| `packaging/macos/config/PrivacyGuard.spec` | 6 new validator hiddenimports | ✓ VERIFIED | Lines 103-108 contain all 6 new validators. |
| `packaging/macos/scripts/build_complete.sh` | bin_prefixes.json + .LICENSE parity checks | ✓ VERIFIED | 2 parity check blocks at lines 152-158 (bin_prefixes.json) + 161-167 (.LICENSE). `bash -n` exits 0. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `privacyguard.pii.engine.detect` | `iter_candidate_strings` → `_check_*` → validators | dispatch chain | ✓ WIRED | detect dispatches all 9 entity_hints; iter_candidate_strings yields 9 entity types; _check_* methods call validate_* functions. |
| `privacyguard.pii.engine.detect` | `mask_for_entity` → `partial_mask_*` | dispatch chain | ✓ WIRED | mask_for_entity at privacyguard/pii/mask.py dispatches all 9 entity types including CN_USCC and CN_TAXPAYER_ID sharing partial_mask_uscc (D-09). |
| `privacyguard.pii.pdf_adapter.write_partial_masks` | `page.add_redact_annot + apply_redactions(IMAGE_PIXELS) + insert_text` | 3-stage flow | ✓ WIRED (PDF adapter internal) — BUT **NOT CALLED from main.py** | write_partial_masks uses correct path internally. main.py save_pdf does NOT call write_partial_masks. |
| `privacyguard.pii.pdf_adapter.clear_pdf_metadata` | `doc.set_metadata({5 fields: ''})` | single call | ✓ WIRED | pdf_adapter internal + main.py line 12719 calls clear_pdf_metadata before doc.save. |
| `privacyguard.pii.validators.bank_card.get_bin_whitelist` | `resource_path("privacyguard/pii/data/bin_prefixes.json")` | lazy load via resource_path | ✓ WIRED | cp30 discipline preserved (no os.path.dirname(__file__)). Returns frozenset of 19,890 entries. |
| `privacyguard/__init__._LAZY_IMPORTS` | `privacyguard.pii.{validators, mask, pdf_adapter}` | 3-level forwarding | ✓ WIRED | OPS-03 strict contract verified: `import privacyguard` loads 0 PII modules. |
| `main.py::save_pdf` | `write_partial_masks` | import → call | ✗ NOT_WIRED | **CR-01**: import only (line 12626), 0 call sites. Partial mask logic re-implemented inline. |
| `main.py::save_pdf` | `clear_pdf_metadata` | import → call | ✓ WIRED | Line 12627 import + line 12719 call. |
| `main.py::SettingsDialog` | `config.json.pii_settings.per_entity_default` | save_settings persistence | ✓ WIRED | save_settings at line 2788-2794 persists per_entity_default to self.config. |
| `main.py::toolbar.btn_mask_override` | `self.page_data[0]["mask_override_this_doc"]` | toggle handler | ✓ WIRED | _toggle_mask_override_this_doc at line 8781-8797; read by save_pdf at line 12616. |
| `packaging/{windows,macos}/PrivacyGuard*.spec` | 6 new validator modules | hiddenimports entries | ✓ WIRED | All 6 validators present in both specs (B5 parity). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `bin_prefixes.json` | `bin_prefixes` array | Wikipedia + 银联 public announcements | ✓ | 19,890 unique 6-digit entries from real public data |
| `_BIN_WHITELIST_CACHE` (singleton) | BIN whitelist frozenset | bin_prefixes.json via resource_path | ✓ | 19,890 entries loaded on first get_bin_whitelist() call |
| `RULES_VERSION_DEFAULT` | rules.json metadata | privacyguard/pii/data/rules.json | ✓ | bank_card/uscc/vat_invoice/bank_account schema sections present |
| `config.json pii_settings.per_entity_default` | per-entity mode dict | SettingsDialog save_settings | ✓ | 9 keys, all "partial" default |
| `page_data[0]["mask_override_this_doc"]` | document-level override flag | toolbar toggle | ✓ | "blackout" / None toggle; reset on _open_pdf_file |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| 9-entity end-to-end smoke | `python3 -c "from privacyguard.pii.engine import PIIEngine, TextUnit; ..."` | 10 hits (CN_ID_CARD/CN_PHONE/CN_BANK_CARD/CN_EMAIL/CN_USCC/CN_TAXPAYER_ID/CN_VAT_INVOICE×2/CN_TAXPAYER_ID_15/CN_BANK_ACCOUNT). CN_TAXPAYER_ID_15=MEDIUM, others HIGH. | ✓ PASS |
| USCC validator | `python3 -c "from privacyguard.pii.validators.uscc import validate_uscc; print(validate_uscc('91110000600037341L'))"` | True | ✓ PASS |
| USCC Z-category rejection | `python3 -c "from privacyguard.pii.validators.uscc import validate_uscc; print(validate_uscc('Z11000000000000000'))"` | False | ✓ PASS |
| BIN whitelist size | `python3 -c "from privacyguard.pii.validators.bank_card import get_bin_whitelist; print(len(get_bin_whitelist()))"` | 19890 | ✓ PASS |
| bin_prefixes.json loadability via resource_path | `python3 -c "from privacyguard.utils.security import resource_path; import json; data = json.load(open(resource_path('privacyguard/pii/data/bin_prefixes.json'), encoding='utf-8')); print(len(data['bin_prefixes']))"` | 19890 | ✓ PASS |
| bin_prefixes.json LICENSE | `python3 -c "open('privacyguard/pii/data/bin_prefixes.json.LICENSE').read()"` | contains "CC BY-SA" + "Wikipedia" | ✓ PASS |
| Bank account context rejection | `python3 -c "from privacyguard.pii.validators.bank_account import has_bank_account_context; print(has_bank_account_context('random 622202123456789012', '622202123456789012'))"` | False | ✓ PASS |
| Bank account context acceptance | `python3 -c "from privacyguard.pii.validators.bank_account import has_bank_account_context; print(has_bank_account_context('账号 622202123456789012', '622202123456789012'))"` | True | ✓ PASS |
| config.json per_entity_default shape | `python3 -c "import json; c=json.load(open('config.json')); pe=c['pii_settings']['per_entity_default']; ss=c['pii_settings']['scan_scope']; print(len(pe), len(ss), all(pe[k]=='partial' for k in pe))"` | 9 9 True | ✓ PASS |
| Test suite passes | `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_metadata_cleared` | Ran 272 tests, OK (skipped=2) | ✓ PASS |
| bash -n build script | `bash -n packaging/macos/scripts/build_complete.sh` | exit 0 | ✓ PASS |
| compileall main.py + privacyguard + tests + packaging | `python3 -m compileall -q main.py privacyguard tests packaging` | exit 0 | ✓ PASS |

### Probe Execution

No probes defined for Phase 2 (project uses unittest, not scripts/*/tests/probe-*.sh). Standard unittest suite serves as probe equivalent.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| NUM-04 | 02-01 + 02-02 | 银行卡 Luhn + BIN + context | ✓ SATISFIED | privacyguard/pii/validators/bank_card.py validates 13-19 digit + Luhn + 6-digit BIN via whitelist. TestBankCardLuhn + TestBankCardBin + TestEngineBankCard green. |
| NUM-05 | 02-01 + 02-02 | 邮箱 RFC 5322 + public suffix | ✓ SATISFIED | privacyguard/pii/validators/email.py validates RFC 5322 simplified regex; is_public_suffix_email boosts confidence. TestEmail + TestEngineEmail green. |
| FIN-01 | 02-01 + 02-02 | 统一社会信用代码 GB 32100 mod-31-3 | ✓ SATISFIED | privacyguard/pii/validators/uscc.py validates 18-char + 6-char category whitelist + mod-31-3. TestUsUsccMod31 + TestUsccCategory + TestEngineUscc green. |
| FIN-02 | 02-02 | 增值税发票号 8位 + 20位 + context anchor | ✓ SATISFIED | privacyguard/pii/validators/vat_invoice.py validates 8 + 20 digit + D-07 context tier. TestVatInvoice + TestEngineVatInvoice green (8 digit with anchor=HIGH; 20 digit without anchor=HIGH per D-07). |
| FIN-03 | 02-02 | 纳税人识别号 15位 + 18位 (双 type) | ✓ SATISFIED | privacyguard/pii/validators/taxpayer_id.py validates 15-digit + admin prefix whitelist (34 prefixes, no mod-31-3 reuse per D-09). D-09 双 type: CN_USCC + CN_TAXPAYER_ID share 18-bit detection (regex_patterns.py 二次 yield + overlap.resolve special exemption). TestTaxpayerId15 + TestEngineTaxpayerId18 + TestEngineTaxpayerId15 green. |
| FIN-04 | 02-02 | 银行账号 9-21位 + 17 context anchors + D-08 strict | ✓ SATISFIED | privacyguard/pii/validators/bank_account.py validates 9-21 digit; BANK_ACCOUNT_CONTEXTS 17 entries (4 generic + 5 big-5 + 7 股份制 + 1 城商行). D-08 strict context gate: engine._check_bank_account returns None if no context anchor. TestBankAccount + TestEngineBankAccount + TestEngineBankAccountNoContextRejected green. **WR-04 caveat**: has_bank_account_context only checks first occurrence. |
| MASK-01 | 02-01 + 02-02 + 02-03 | Partial mask per-entity | ⚠️ PARTIAL | privacyguard/pii/mask.py defines partial_mask_id_card/phone/bank_card/email/uscc/vat_invoice/taxpayer_id_15/bank_account; mask_for_entity dispatches all 9 types. pdf_adapter.write_partial_masks correctly writes mask text after 真删除. **HOWEVER**, main.py::save_pdf does NOT delegate to write_partial_masks — instead re-implements inline at lines 12685-12715 (CR-01). Inline version is feature-incomplete (WR-02: font hardcoded as 'helv', flat 11.0 fallback, no rect resize). |
| MASK-02 | 02-03 | User-chosen partial/blackout per entity | ✓ SATISFIED | SettingsDialog 9-row per-entity table with QCheckBox + QComboBox (部分掩码 / 全遮蔽) + 2 bulk flip buttons. save_settings persists pii_settings.per_entity_default to config.json. Toolbar btn_mask_override "本文件全遮蔽" toggle overrides for current document. config.json contains 9-key per_entity_default + 9-entry scan_scope (D-13 locked). |
| SAFE-03 | 02-01 + 02-03 | PDF metadata 5 fields cleared | ✓ SATISFIED | privacyguard/pii/pdf_adapter.clear_pdf_metadata single-line set_metadata({5 fields: ''}). main.py line 12719 calls clear_pdf_metadata(doc_save) before doc.save. TestPdfMetadataCleared green: 5 fields == '', CreationDate preserved, no placeholder strings. |
| OPS-03 | 02-01 + 02-02 | 懒加载契约 | ⚠️ PARTIAL | Strict contract satisfied: `import privacyguard` loads 0 PII modules. Lazy tables at privacyguard.pii.__init__ + privacyguard.__init__ + privacyguard.pii.validators.__init__ all use __getattr__ lazy load. **WR-01**: PIIEngine eagerly imports all 6 new validators (lines 32-48) — spirit of CLAUDE.md constraint #2 broken. |
| OPS-07 | 02-01 + 02-02 + 02-03 | 测试基线门禁 79/79 preserved | ✓ SATISFIED | Full 272-test suite green: 79 Phase 1 baseline + 16 Phase 1 PII + 41 02-01 + 24 02-02 + ~3 02-03 + 109 other tests. OK (skipped=2). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `main.py` | 12625-12715 | Inline re-implementation of write_partial_masks (CR-01) | 🛑 BLOCKER | v37.7.6 收敛原则 violation. main.py imports write_partial_masks but re-implements the partial mask insert_text logic inline. Future changes to write_partial_masks (font matching, OCR font-size estimation, rect resize) will not reach production. Inline version is feature-incomplete vs. write_partial_masks (WR-02: no _FONT_NAME_MAP, flat 11.0 fallback, no rect resize). |
| `privacyguard/pii/engine.py` | 32-48 | Eager import of all 6 new validators (WR-01) | ⚠️ WARNING | OPS-03 spirit violated: PIIEngine eagerly loads all 6 new validators at module top. Importing privacyguard.pii.engine triggers loading of all 6 modules into sys.modules. Only practical access path loads them all. |
| `main.py` | 12693-12714 | Inline font hardcoded as "helv" (WR-02) | ⚠️ WARNING | Original Times-Roman / Courier face is lost in production output. PyMuPDF font mapping table (_FONT_NAME_MAP) not used. |
| `main.py` | 12694 | Inline font_size flat 11.0 fallback (WR-02) | ⚠️ WARNING | OCR-sourced partial masks render at 11.0 instead of max(rect.height-4, 6). OCR partial masks often overflow the rect. |
| `main.py` | 12707-12710 | Inline insert_text without rect resize (WR-02) | ⚠️ WARNING | Inline inserts at original rect center. Wide mask text (e.g. 18-char USCC partial mask) can overflow when mask is wider than original. |
| `tests/unit/test_convergence.py` | 273-305 | test_main_py_uses_write_partial_masks_in_save_loop only checks string presence | ⚠️ WARNING | AST does not verify write_partial_masks is actually called inside save_pdf. CR-01 regression slipped through this gate. |
| `tests/unit/test_pdf_pii_redaction.py` | 168-284 | Integration test re-implements inline instead of calling write_partial_masks (WR-03) | ⚠️ WARNING | Test name claims to verify routing but the test body imports write_partial_masks without calling it. Test body mirrors main.py inline logic. |
| `privacyguard/pii/validators/bank_account.py` | 56 | text.find(target) only first occurrence (WR-04) | ⚠️ WARNING | Edge case for documents with multiple bare accounts not exercised by current tests. Second candidate rejected but never re-checked against its own context window. |
| `privacyguard/pii/validators/taxpayer_id.py` | 14-22 | _TAXPAYER_15_ADMIN_D (34 | ℹ️ INFO | Duplicates _VALID_ADMIN_PREFIX_2 from id_card validator + _VALID_PROVINCE_PREFIX in fake_pii.py. Three copies of the same data. |
| `privacyguard/pii/data/bin_prefixes.json` | 1 | _count_target says 10,000-15,000 but file has 19,890 entries | ℹ️ INFO | Documentation drift only. |
| `privacyguard/pii/validators/email.py` | 21-23, 38-49 | EMAIL_RE case semantics undocumented | ℹ️ INFO | Local part IS case-sensitive, domain IS case-insensitive per RFC 5322. Behavior correct, documentation gap. |

### Human Verification Required

Phase 2 plan contains 3 human-verify checkpoints (Task 5 in each plan), all auto-approved per autonomous dispatch. These require real-app launch verification:

1. **SettingsDialog 9-row per-entity table UI** (02-03 Task 5) — Open Settings → "5 隐私识别" tab → confirm 9 rows + bulk flip buttons + scope label.
2. **Toolbar btn_mask_override toggle UI** (02-03 Task 5) — Open PDF → confirm "本文件全遮蔽" toggle button visible and clickable.
3. **End-to-end save + reverse-extract** (02-03 Task 5) — Open PDF containing 18-digit ID card → save → reopen in Adobe Reader/browser → confirm partial mask visible + 5 metadata fields empty.

For autonomous verification scope (no GUI access), the following programmatic checks substitute for human UI verification:
- SettingsDialog wiring verified via grep (23 references to PHASE2_ENTITY_MODE_ROWS / _bulk_set_entity_mode_blackout / per_entity_default in main.py).
- Toolbar toggle wiring verified via grep (20 references to btn_mask_override / mask_override_this_doc in main.py).
- End-to-end save + reverse-extract logic verified via tests/unit/test_pdf_pii_redaction.py::test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata (but see WR-03 caveat that this test does NOT verify routing — it re-implements inline).

**However**, the central Phase 2 deliverable (CR-01: write_partial_masks actually called in save_pdf) is a **code-level** concern that automated verification catches via grep but the convergence test missed (WR-03 + weak test assertion). This must be resolved at the code level before Phase 2 can ship.

### Gaps Summary

**CR-01 (CRITICAL BLOCKER)**: v37.7.6 收敛原则 violation. `main.py::save_pdf` imports `privacyguard.pii.pdf_adapter.write_partial_masks` at line 12626 but **never calls it**. Instead, the partial mask insert_text logic is re-implemented inline at lines 12685-12715 using `page.insert_text` directly. This is exactly the convergence discipline the project explicitly added `test_convergence.py` to prevent.

The inline implementation is **feature-incomplete** compared to `write_partial_masks`:
- Font is hardcoded as `"helv"` instead of using `_FONT_NAME_MAP` (8-entry mapping for Helvetica / Times-Roman / Courier). Times / Courier face is lost in production output.
- Font size fallback is flat `11.0` instead of `max(rect.height - 4, 6)` for OCR / placeholder rect paths. OCR partial masks often overflow.
- No `_resize_rect_for_mask` rect widening. Wide mask text can overflow the original rect.

The convergence test `test_main_py_uses_write_partial_masks_in_save_loop` (tests/unit/test_convergence.py:273-305) only checks for string presence (`"write_partial_masks" in source`) — it does NOT AST-verify the function is actually called inside save_pdf. This is why the regression slipped through.

The integration test `test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata` (tests/unit/test_pdf_pii_redaction.py:168-284) imports `write_partial_masks` (line 178) but **never calls it** — manually re-implements the inline logic at lines 240-258 (mirror of main.py inline code). The test name is misleading; it does NOT test the routing.

**Phase 2 should not be marked complete until either**:
- (a) `main.py::save_pdf` is refactored to call `write_partial_masks` after extending its signature to accept mixed item types (PIIHit | Tuple[QRectF, str]) for the unified OCR + manual + PII dispatch, OR
- (b) `write_partial_masks` is refactored to accept mixed (PIIHit | manual_rect, mode) items so the unified call can be made.

**WR-01 (WARNING)**: OPS-03 spirit violated. `privacyguard/pii/engine.py` lines 32-48 eagerly import all 6 new validators at module top. Importing `privacyguard.pii.engine` triggers loading of all 6 modules into `sys.modules`. The lazy-load mechanism at `privacyguard/pii/validators/__init__.py` is intact but bypassed by the engine's eager imports. Fix is either (a) accept + document current behavior, or (b) refactor engine.py to use `importlib.import_module` inside `_check_*` methods.

**WR-04 (WARNING)**: `has_bank_account_context` only checks first occurrence via `text.find(target)`. Edge case for documents with multiple bare accounts. Fix: iterate all `text.find(target, start)` positions.

### Code Review Verification (02-REVIEW.md)

| Finding | Status | Verification |
| ------- | ------ | ------------ |
| CR-01 (main.py inline write_partial_masks) | **REAL BUG** | Confirmed via grep: write_partial_masks imported once (line 12626), 0 call sites; page.insert_text called directly at line 12709. Inline logic at 12685-12715 mirrors what write_partial_masks does internally. |
| WR-01 (engine.py eager imports) | **REAL WARNING** | Confirmed via Python REPL: importing privacyguard.pii.engine loads all 6 new validators + id_card + phone_segment into sys.modules. |
| WR-02 (inline feature-incomplete) | **REAL WARNING** | Confirmed: main.py line 12713 hardcodes fontname="helv"; line 12694 uses font_size = 11.0 flat; lines 12707-12710 insert at original rect center without resize. |
| WR-03 (test re-implements inline) | **REAL WARNING** | Confirmed: tests/unit/test_pdf_pii_redaction.py line 178 imports write_partial_masks; lines 240-258 manually re-implement the inline logic (mirror of main.py 12685-12715). |
| WR-04 (has_bank_account_context first occurrence) | **REAL WARNING** | Confirmed: privacyguard/pii/validators/bank_account.py line 56 uses text.find(target) which returns first occurrence only. |
| IN-01 (admin prefix duplication) | **REAL INFO** | Confirmed: 3 copies of admin prefix data (taxpayer_id.py:14-22, id_card.py, fake_pii.py:13-21). |
| IN-02 (_count_target stale) | **REAL INFO** | Confirmed: bin_prefixes.json._count_target="10,000-15,000" but actual count is 19,890. |
| IN-03 (email case semantics undocumented) | **REAL INFO** | Confirmed: EMAIL_RE has no re.IGNORECASE flag; is_public_suffix_email calls .lower() on TLD only. |

### Verdict

**GAPS_FOUND** — Phase 2 cannot ship without resolving CR-01.

The 7 fully verified truths, 9 fully verified artifacts, 11 fully verified key links, and 8 fully satisfied requirements (out of 11; 2 partial, 1 failed) demonstrate that Phase 2 has achieved the majority of its goals: 6 new entity validators, 2 apply-phase helpers, 9-entity end-to-end detection, SettingsDialog 9-row per-entity table, toolbar mask_override toggle, BIN dictionary with CC BY-SA 4.0 attribution, and Windows + macOS PyInstaller parity.

However, the central architectural regression (CR-01) is a v37.7.6 收敛原则 violation that the project explicitly added tests to prevent. The Phase 2 PLAN locked `write_partial_masks` as the canonical helper for the partial mask write path; the implementation imports it but re-implements it inline instead. The convergence test + integration test were both too weak to catch this regression, allowing Phase 2 to falsely report "complete" status.

Phase 2 must be re-planned after CR-01 is fixed (refactor write_partial_masks to accept mixed item types, refactor main.py to delegate to write_partial_masks, tighten the convergence test to AST-verify the call, replace the integration test's inline re-implementation with an actual write_partial_masks call).

---

_Verified: 2026-08-11T14:55:00Z_
_Verifier: Claude (gsd-verifier)_
_Depth: standard (full goal-backward verification + code review cross-reference)_