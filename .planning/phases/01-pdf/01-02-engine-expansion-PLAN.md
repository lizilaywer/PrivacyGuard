---
phase: 01-pdf
plan: 02
slug: engine-expansion
type: execute
wave: 2
depends_on:
  - "01-01"
files_modified:
  - tests/unit/test_pii_validators.py
  - tests/unit/test_pii_engine.py
  - privacyguard/pii/validators/id_card.py
  - privacyguard/pii/validators/phone_segment.py
  - privacyguard/pii/normalize.py
  - privacyguard/pii/confidence.py
  - privacyguard/pii/mask.py
  - privacyguard/pii/overlap.py
  - privacyguard/pii/engine.py
autonomous: true
requirements:
  - ENGINE-03
  - ENGINE-04
  - ENGINE-05
  - ENGINE-06
  - ENGINE-07
  - NUM-01
  - NUM-02
  - NUM-03
user_setup: []

estimate:
  tokens: 55000
  raw_tokens: 27500
  tasks: 3
  confidence: medium

must_haves:
  truths:
    - validate_18 rejects 17-digit or 19-digit inputs (NUM-01 length gate).
    - validate_18 rejects inputs where last char is not 0-9/X/x (NUM-01 charset gate).
    - validate_18 rejects inputs where any of the first 17 chars is non-digit (NUM-01 digit gate).
    - upgrade_15_to_18 inserts '19' as century prefix producing a valid 18-digit body; validate_15 on the original 15-digit string returns True iff the upgraded 18-digit passes (NUM-01 sub-path).
    - upgrade_15_to_18 returns '' for non-15-digit input (defensive guard).
    - is_mobile_segment rejects 10-digit or 12-digit input (length gate).
    - is_mobile_segment rejects input not starting with '1' (NUM-03 leading-1 gate).
    - is_mobile_segment accepts every prefix in personal_prefix_3 table (NUM-03 whitelist) — test asserts True for a representative sample of ≥30 prefixes spanning 130/131/133/135/138/150/152/155/157/158/166/170/171/173/176/180/181/183/186/188/190/192/195/196/197/198/199.
    - is_mobile_segment rejects every prefix in excluded_prefix_3 and excluded_prefix_4 — test asserts False for 140/141/144/145/146/147/148/149/1349/1440/1740/1741 (NUM-03 IoT exclusion).
    - normalize_digits converts fullwidth digits ０-９ to ASCII 0-9 (ENGINE-05).
    - normalize_digits strips common separators - / space / fullwidth space (ENGINE-05).
    - flatten_for_match strips newlines / tabs / all whitespace (ENGINE-06 cross-line input).
    - map_flat_to_original returns (None, None) tuple when flat span cannot be mapped (defensive).
    - map_flat_to_original returns correct original span when flat text is the original with separators inserted (ENGINE-05 offset reverse-mapping) — also implements D-06 char-level offset back-mapping for OCR paths where `iter_ocr_lines` outputs are concatenated into one string and the regex match span must be mapped back to the original page text index.
    - PIIEngine.detect emits HIGH confidence for Faker-generated 18-digit ID + 11-digit personal mobile (ENGINE-03 HIGH tier).
    - PIIEngine.detect emits zero hits for Faker-generated IoT segment 140xxxxxxxx (NUM-03 + ENGINE-03 LOW tier absent).
    - PIIEngine.detect returns identical mask_strategy for two occurrences of the same normalized entity within a page (ENGINE-04 mask consistency).
    - PIIEngine.detect emits hits across newlines for an ID card split as "110101\n19900307\n8811" (ENGINE-06 cross-line).
    - PIIEngine.detect does NOT hang on a 200,000-character single page text (ENGINE-07 input-size defense; truncation / linear scan budget).
    - classify_hit returns HIGH iff (validator_passed AND regex_matched), MEDIUM iff regex_matched only, LOW otherwise (ENGINE-03 boundary test).
    - partial_mask_id_card produces "110101********8811" shape for "110101199003078811"; produces 18-char asterisk string for wrong-length input.
    - partial_mask_phone produces "138****5678" shape for "13812345678"; produces 11-char asterisk string for wrong-length input.
    - overlap.resolve deduplicates hits sharing (page_offset, page_length) keeping the validator_passed=True copy when both exist; sorts result by (page_offset, page_length) ascending.
  artifacts:
    - tests/unit/test_pii_validators.py (TestIdCardChecksum / TestIdCardUpgrade15To18 / TestIdCaseInsensitiveX / TestIdCardDefensive / TestPhoneSegment / TestIotExclusion / TestPhoneSegmentDefensive)
    - tests/unit/test_pii_engine.py (TestPIIHitSchema / TestEngineDetect / TestConfidenceTiers / TestMaskConsistency / TestNormalization / TestCrossBoundary / TestLargeDocumentNoBlock)
  key_links:
    - privacyguard/pii/engine.detect → privacyguard/pii/normalize.normalize_digits + flatten_for_match + map_flat_to_original (ENGINE-05/06 chain)
    - privacyguard/pii/engine._engine_cache[(entity_type, normalized)] → privacyguard/pii/mask.mask_for_entity (ENGINE-04 deterministic mask)
    - privacyguard/pii/overlap.resolve → privacyguard/pii/hits.PIIHit (page_offset, page_length) dedup key
    - privacyguard/pii/confidence.classify_hit → privacyguard/pii/engine.detect confidence_tier assignment
  prohibitions:
    - 不得在 PIIEngine.detect 中静默丢弃通过校验位的命中以"降低误报率"；一致性优先（ENGINE-04 consistency rule）
    - 不得在 validate_18 中跳过 17 位数字校验（仅检查末位校验码）—— 必须先校验前 17 位全数字（NUM-01 输入格式）
    - 不得在 upgrade_15_to_18 中假设任何特定世纪；只能使用 '19' 已知前缀（NUM-01 历史兼容）
    - 不得在 is_mobile_segment 中把 IoT 段（140/141/144/145/146/147/148/149）漏判为个人号段（NUM-03 IoT 排除）
    - 不得在 map_flat_to_original 中默默返回 0 而非 None —— 失败必须显式（ENGINE-05 防御）
    - 不得在 partial_mask_* 中省略长度校验后输出错误掩码（mask 输出对长度异常必须返回全 '*'）
    - 不得让 PIIEngine 在 200KB 单页文本上无限阻塞；必须保证线性输入长度 O(n)（ENGINE-07）
    - 不得在 overlap.resolve 中按"先到先得"丢失 validator_passed=True 的命中（dedup 优先级：校验通过优先）

threat_model:
  trust_boundaries:
    - {name: User-supplied PDF text → PIIEngine, description: text from PyMuPDF page.get_text() crosses here; potentially attacker-controlled content}
    - {name: normalize_digits input → regex engine, description: full-width digits / unicode separators may be controlled; regex still anchored}
  stride:
    - {id: T-02-REDOS, category: Denial of Service, component: PIIEngine.detect on long input, severity: low, disposition: mitigate, mitigation: regexes are anchored (?<!\d) ... (?!\d); test_large_document_no_block asserts 200KB string completes in <1s; no Python re timeout argument used (does not exist — RESEARCH §Pitfall 10)}
    - {id: T-02-XCASE, category: Tampering, component: validate_18 last-char handling, severity: medium, disposition: mitigate, mitigation: last.upper() normalizes before comparison; NUM-02 test asserts lowercase x accepted; defensive: rejects non [0-9Xx] chars}
    - {id: T-02-MASK-CONSIST, category: Information Disclosure, component: PIIEngine._engine_cache for repeated entities, severity: medium, disposition: mitigate, mitigation: _engine_cache keys on (entity_type, normalized) so two occurrences in same page share same mask; test_mask_consistency asserts identical strings}
    - {id: T-02-CROSSLINE, category: Tampering / false negative, component: flatten_for_match + map_flat_to_original, severity: medium, disposition: mitigate, mitigation: flatten strips [\s\n\r\t　-]+; map_flat_to_original walks character-by-character; test_cross_boundary covers three-line split ID card and fullwidth digits}
    - {id: T-02-OFFSET-MAP, category: Tampering, component: map_flat_to_original returning None silently, severity: low, disposition: mitigate, mitigation: function returns (None, None) and engine.detect skips hit (defensive guard against malformed text)}
    - {id: T-02-SILENT-NEG, category: Repudiation, component: classify_hit downgrading HIGH to MEDIUM for noise reduction, severity: medium, disposition: mitigate, mitigation: classify_hit only downgrades when validator_passed=False; engine never silently drops validator_passed=True hits; test_confidence_tiers boundary covers all three branches}

---

<objective>
Expand coverage of the PII engine / validators / mask / overlap / normalize to every NUM-01/02/03 and ENGINE-01..07 requirement, with one unit test class per requirement. Tests come first (RED); production code in Task 2 makes them GREEN. Task 3 hardens the input-length defense for ENGINE-07.
</objective>

<purpose>
The tracer (Plan 01-01) proved the spine works for one path. This plan broadens the contract coverage: it asserts every validator edge case, every confidence-tier branch, the cross-line recognition, the consistent-mask invariant, and the no-block-on-large-input guarantee. Without these tests, future plans cannot regress-safely extend the engine to more entity types (Phase 2+).
</purpose>

<output>
- tests/unit/test_pii_validators.py (NUM-01 / NUM-02 / NUM-03 coverage; ≥40 assertions)
- tests/unit/test_pii_engine.py (ENGINE-01..07 coverage; ≥30 assertions)
- Hardened privacyguard/pii/validators/id_card.py + phone_segment.py edge-case guards
- Hardened privacyguard/pii/normalize.py map_flat_to_original defensive (None, None) return
- Hardened privacyguard/pii/confidence.py classify_hit three-branch coverage
- Hardened privacyguard/pii/mask.py length-defensive partial masks
- Hardened privacyguard/pii/overlap.py validator_passed-priority dedup
- Hardened privacyguard/pii/engine.py ENGINE-04 cache + ENGINE-06 flatten integration
</output>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/01-pdf/01-CONTEXT.md
@.planning/phases/01-pdf/01-PATTERNS.md
@.planning/phases/01-pdf/01-VALIDATION.md
@.planning/phases/01-pdf/01-RESEARCH.md
@.planning/phases/01-pdf/01-UI-SPEC.md
@privacyguard/pii/validators/id_card.py
@privacyguard/pii/validators/phone_segment.py
@privacyguard/pii/normalize.py
@privacyguard/pii/confidence.py
@privacyguard/pii/mask.py
@privacyguard/pii/overlap.py
@privacyguard/pii/engine.py
@privacyguard/pii/hits.py
@privacyguard/pii/regex_patterns.py
@privacyguard/pii/data/rules.json
</context>

<tasks>

<task type="tdd">
  <name>RED — write validators + engine + normalization test stubs (failing)</name>
  <files>
    - tests/unit/test_pii_validators.py
    - tests/unit/test_pii_engine.py
  </files>
  <read_first>
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 1094-1146 — test_pii_validators.py structure)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 1150-1195 — test_pii_engine.py structure)
    - .planning/phases/01-pdf/01-VALIDATION.md (lines 45-60 — Per-Task Verification Map for NUM-01..03 + ENGINE-01..07)
    - .planning/phases/01-pdf/01-RESEARCH.md (lines 1041-1063 — TDD Specifics / per-requirement test cases)
    - privacyguard/pii/validators/id_card.py (current implementation from Plan 01-01)
    - privacyguard/pii/validators/phone_segment.py (current implementation from Plan 01-01)
    - privacyguard/pii/engine.py (current implementation from Plan 01-01)
  </read_first>
  <action>
    Write two test files that exhaustively assert every validator / engine / normalization edge case. Do NOT modify production code; running these tests after Task 1 alone must produce failures (RED state — mostly because some edge cases like negative guards, three-branch tier coverage, and 200KB input defense are NOT yet implemented).

    In `tests/unit/test_pii_validators.py`:

    - `TestIdCardChecksum`:
      - `test_valid_18_passes_checksum`: `validate_18("53010219200508011X") == True` (GB 11643-1999 standard sample, RESEARCH §Pitfall 3).
      - `test_invalid_check_digit_fails`: `validate_18("530102192005080119") == False`.
      - `test_lowercase_x_accepted_via_upper`: `validate_18("53010219200508011x") == True` (NUM-02).
      - `test_corrupted_body_fails`: `validate_18("53010A19200508011X") == False` (non-digit in first 17).
      - `test_short_id_rejected`: `validate_18("123") == False`.
      - `test_long_id_rejected`: `validate_18("1" * 19) == False`.
      - `test_empty_string_rejected`: `validate_18("") == False`.
      - `test_last_char_invalid_rejected`: `validate_18("53010219200508011Z") == False`.
      - `test_15_digit_input_rejected_by_validate_18`: `validate_18("420106960901234") == False` (15-digit handled by validate_15 only).

    - `TestIdCardUpgrade15To18`:
      - `test_15_digit_upgrades_to_valid_18`: `upgrade_15_to_18("420106960901234")` returns 18-char string and `validate_18(upgraded) == True`.
      - `test_15_digit_century_prefix_is_19`: `upgrade_15_to_18("110101800101001").startswith("11010119") == True` (NUM-01 historical).
      - `test_non_15_digit_returns_empty`: `upgrade_15_to_18("123")` returns `''`.
      - `test_non_digit_15_rejected`: `upgrade_15_to_18("42010696090123A")` returns `''`.
      - `test_validate_15_passes_for_valid_upgraded`: `validate_15("420106960901234") == True`.
      - **B1 second-gate negative tests** (new — guards against silently auto-redacting order numbers / tracking numbers / serial numbers):
        - `test_15_digit_invalid_province_prefix_rejected`: `validate_15("990106800101001") == False` (prefix `99` is not in the GB/T 2260 valid province set — order numbers / serial numbers often start with `00`, `90`, `99`, etc.).
        - `test_15_digit_zero_province_prefix_rejected`: `validate_15("000106800101001") == False` (prefix `00` not valid).
        - `test_15_digit_impossible_month_rejected`: build a 15-digit run whose upgrade-to-18 contains month `13` in `YYMMDD` position (e.g. `420106801301001` upgrades to `42010619801301001`); assert `validate_15(...) == False`. Confirms `is_real_calendar_date` second gate works.
        - `test_15_digit_impossible_day_rejected`: build a 15-digit run whose upgrade-to-18 contains day `32` in `YYMMDD` position (e.g. `420106800132001` upgrades to `42010619800132001`); assert `validate_15(...) == False`. Confirms day-of-month validation works.
        - `test_15_digit_feb_30_rejected`: a run whose date falls on Feb 30 (impossible calendar date); assert `validate_15(...) == False`. Confirms month-aware day count.
        - `test_is_valid_admin_division_prefix_2_whitelist`: parametrized-style loop asserting `is_valid_admin_division_prefix_2("11") == True`, `"82") == True`, `"00") == False`, `"90") == False`, `"99") == False`.
        - `test_is_real_calendar_date_boundary`: assert `is_real_calendar_date(85, 1, 1) == True`; `is_real_calendar_date(85, 2, 29) == True` (1985 not leap; 1984 leap would be, but `85` is not divisible by 4); `is_real_calendar_date(85, 13, 1) == False`; `is_real_calendar_date(85, 1, 32) == False`; `is_real_calendar_date(85, 4, 31) == True` (April has 30 days — actually False; April has 30 days); `is_real_calendar_date(85, 2, 30) == False`.
      - **Reconciliation note:** `validate_15` is no longer `True` for any 15-digit run whose upgrade passes mod-11-2. The previous always-True contract is removed. Plan 01-01 must_haves.truths entry "PIIEngine.detect emits HIGH for Faker-generated 18-digit ID" still holds (18-digit path); for 15-digit, the test `test_detects_15_digit_via_upgrade` in TestEngineDetect below must use a real 15-digit run with a valid province prefix + real calendar date, not a synthetic random run.

    - `TestPhoneSegment`:
      - `test_personal_segment_recognized`: parametrized-style loop asserting `is_mobile_segment` True for ≥30 prefixes: 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 150, 151, 152, 153, 155, 156, 157, 158, 159, 166, 170, 171, 173, 176, 180, 181, 183, 186, 188, 190, 192, 195, 196, 197, 198, 199. Each followed by 8 random digits.

    - `TestIotExclusion`:
      - `test_iot_segment_excluded`: `is_mobile_segment("140" + "12345678") == False`; same for 141, 144, 145, 146, 147, 148, 149.
      - `test_satellite_prefix_excluded`: `is_mobile_segment("13491234567") == False` (4-digit prefix match).
      - `test_satellite_prefix_1740_excluded`: `is_mobile_segment("17401234567") == False`.
      - `test_satellite_prefix_1741_excluded`: `is_mobile_segment("17411234567") == False`.
      - `test_data_card_segment_excluded`: `is_mobile_segment("14512345678") == False` (data card excluded per MIIT).
      - `test_non_leading_one_rejected`: `is_mobile_segment("23812345678") == False`.
      - `test_short_phone_rejected`: `is_mobile_segment("1381234567") == False` (10 digits).
      - `test_long_phone_rejected`: `is_mobile_segment("138123456789") == False` (12 digits).
      - `test_non_digit_phone_rejected`: `is_mobile_segment("1381234567A") == False`.
      - `test_empty_string_rejected`: `is_mobile_segment("") == False`.

    In `tests/unit/test_pii_engine.py`:

    - `TestPIIHitSchema`:
      - `test_field_order_locked`: `inspect.signature(PIIHit).parameters.keys()` first 7 are exactly `("entity_type","page_offset","page_length","page_rect","confidence_tier","source","mask_strategy")` (D-05 lock).
      - `test_default_confidence_tier_is_high`: when constructing PIIHit directly with required fields, default `confidence_tier="HIGH"` works (Claude's Discretion, locked here).
      - `test_dataclass_is_frozen`: `setattr(hit, "entity_type", "OTHER")` raises `dataclasses.FrozenInstanceError`.
      - `test_page_rect_is_4_tuple`: `hit.page_rect` is a 4-tuple of floats.

    - `TestEngineDetect`:
      - `test_detects_valid_id_card`: `TextUnit(0, "张三 53010219200508011X 已婚", "text")` → 1 hit with entity_type=CN_ID_CARD, validator_passed=True, confidence_tier=HIGH.
      - `test_detects_valid_phone`: `TextUnit(0, "联系 13812345678", "text")` → 1 hit with entity_type=CN_PHONE.
      - `test_rejects_iot_phone`: `TextUnit(0, "设备 14012345678", "text")` → 0 hits.
      - `test_rejects_invalid_id_check_digit`: `TextUnit(0, "bad 530102192005080119 here", "text")` → 0 hits.
      - `test_detects_15_digit_via_upgrade`: `TextUnit(0, "old 420106960901234 here", "text")` → 1 hit. NOTE: 420106 is a valid Beijing province prefix and 1969-09-01 is a real calendar date, so the B1 second gate passes. **I1 demotion:** when the 15-digit candidate has NO context anchor within ±20 characters (this test text contains `old` and `here` — no `身份证` / `ID` / `公民身份号码` keyword), the hit is demoted to `confidence_tier="MEDIUM"` per the I1 demotion logic in `PIIEngine._check_id_card`. Add a follow-up assertion: `self.assertEqual(hits[0].confidence_tier, "MEDIUM")` (this is the Phase 1 FP mitigation for bare 15-digit matches).
      - `test_empty_text_returns_no_hits`: `TextUnit(0, "", "text")` → 0 hits.
      - `test_whitespace_only_returns_no_hits`: `TextUnit(0, "   \n\t  ", "text")` → 0 hits.
      - **B2 separator-bearing input tests** (NEW — guards against zero-area rect leak from `page.search_for` on separator-stripped text):
        - `test_separated_id_card_recognized`: engine.detect produces a PIIHit for `"订单 110101-19900307-8811 备注"`. The hit's `page_rect` MUST be non-zero-area (width × height > 0; fixture wraps the same call against a `FakePage` whose `search_for` is called with the ORIGINAL span `"110101-19900307-8811"` — i.e. the literal as it appears on the page, not the flattened `"110101199003078811"`). The `FakePage` records `search_calls` so the test asserts `assertEqual(page.search_calls, ["110101-19900307-8811"])`. Same shape as `tests/unit/test_pdf_text_hit_dedup.py` FakePage pattern.
        - `test_fullwidth_digits_id_card_recognized`: engine.detect on `"测试 １１０１０１１９６７０３０７８８１１ 备注"` produces a hit whose rect comes from `page.search_for` called with the ORIGINAL fullwidth literal (not the ASCII-flattened version).
        - `test_separator_split_fallback`: when the original-span search returns empty (e.g. PyMuPDF cannot match `"110101-19900307-8811"` because the page is laid out with the digit groups on separate visual lines), engine.detect splits the original span on `[-\s　]+` and unions per-chunk rects via `page.search_for(chunk) for chunk in chunks`; the hit's `page_rect` is the bounding union, not zero-area. The fixture FakePage returns empty for the joined span and per-chunk rects for `"110101"`, `"19900307"`, `"8811"`; the test asserts the union rect matches the expected bounding box.
        - **W-A — unresolvable hit is recorded not dropped:** when BOTH `page.search_for(original)` AND all per-chunk searches return zero rects, the engine MUST record the candidate in `engine.unresolved_hits` AND log a `("PII NO-RECT", page_idx, candidate_string)` row in `engine.error_log` AND emit zero hits in the returned list. Test asserts: returned `hits == []` (no redactable hit); `len(engine.unresolved_hits) == 1` (the candidate is recorded); the unresolved entry contains the original substring; `len(engine.error_log) == 1` and the row matches the contract. This is W-A — silent drop is exactly the failure class the phase exists to prevent. The user must see "未定位敏感项 N 项" in the UI (wired in Plan 01-03).

    - `TestConfidenceTiers`:
      - `test_high_when_validator_passes_and_regex_matches`: PIIEngine._check_id_card returns confidence_tier=HIGH for valid 18-digit sample.
      - `test_medium_when_regex_matches_but_validator_fails`: validator_failed → confidence_tier=MEDIUM only if ENGINE-03 spec says so (NOTE: current `classify_hit` returns LOW when regex_matched=False, MEDIUM when regex_matched=True and validator_passed=False; assert this exact contract).
      - `test_low_otherwise`: assert classify_hit(False, False, ...) == "LOW".
      - `test_classify_hit_branches`: parametrized over (validator_passed, regex_matched) covering all 4 input combinations; assert expected tier.

    - `TestMaskConsistency`:
      - `test_same_normalized_yields_same_mask`: build a PIIEngine; detect `TextUnit(0, "张三 13812345678 联系人 13812345678 备选 13812345678", "text")`; assert all 3 hits share identical `mask_strategy` value (ENGINE-04).
      - `test_different_normalized_yields_different_mask`: detect two different phone numbers 13812345678 / 13912345678; assert different mask_strategy values.

    - `TestNormalization`:
      - `test_fullwidth_digits_normalized_to_ascii`: `normalize_digits("１２３") == "123"`.
      - `test_separators_stripped`: `normalize_digits("1-3 8 1 2 3 4 5 6 7 8") == "13812345678"` (hyphens + spaces removed).
      - `test_fullwidth_space_stripped`: `normalize_digits("138　12345678") == "13812345678"`.
      - `test_flatten_strips_newlines`: `flatten_for_match("110101\n19900307\n8811") == "110101199003078811"`.
      - `test_flatten_strips_tabs`: `flatten_for_match("138\t12345678") == "13812345678"`.
      - `test_map_flat_to_original_basic`: `map_flat_to_original("13812345678", (3, 7), "138 1234 5678")` returns original indices that span "1234".
      - `test_map_flat_to_original_returns_none_when_unmappable`: short flat_text with span beyond length returns `(None, None)`.

    - `TestCrossBoundary`:
      - `test_id_card_across_newlines_recognized`: `TextUnit(0, "110101\n19900307\n8811", "text")` → 1 hit (the ID card spans newlines, ENGINE-06).
      - `test_phone_across_space_recognized`: `TextUnit(0, "联系 138 1234 5678", "text")` → 1 hit (ENGINE-06 with space split).

    - `TestLargeDocumentNoBlock`:
      - `test_200kb_text_completes_quickly`: build 200,000-char string with random text + 3 ID cards embedded; assert `engine.detect(unit)` returns within 1 second (use `time.perf_counter`).
      - `test_long_text_with_no_hits_returns_empty_quickly`: same 200KB string without any ID/phone; assert detect returns `[]` within 1 second.

    After writing both files, run `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine -v` and confirm at least some tests FAIL — specifically the negative-guard tests (defensive empty string, non-digit chars), the 15-digit upgrade path, the confidence-tier branches, the cross-boundary test, and the 200KB large-document test. The tracer path tests (positive 18-digit, positive phone) should already pass from Plan 01-01.
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine -v 2>&1 | grep -E "(FAIL|ok|OK)" | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - Both test files compile: `python3 -m compileall -q tests/unit/test_pii_validators.py tests/unit/test_pii_engine.py` exits 0.
    - Running the test files produces at least 6 RED state failures (the defensive guards, 15-digit upgrade, confidence-tier MEDIUM branch, cross-boundary, 200KB defense) — proves tests are not all tautologically green.
    - The validator positive tests (TestIdCardChecksum.test_valid_18_passes_checksum, TestPhoneSegment.test_personal_segment_recognized) already pass from Plan 01-01 implementation.
    - Test file imports use the existing PII modules from `privacyguard.pii.*` lazy package — no duplicated logic.
  </acceptance_criteria>
  <done>
    Both test files exist on disk; running them shows RED state on the newly-added edge-case tests; existing positive tests remain green. Test contract in place for Task 2 to harden.
  </done>
  <reversibility>rating="reversible" rationale="Test files only; deletion or simplification reverts cleanly."</reversibility>
</task>

<task type="tdd">
  <name>GREEN — harden validators + engine + normalize + confidence + mask + overlap</name>
  <files>
    - privacyguard/pii/validators/id_card.py
    - privacyguard/pii/validators/phone_segment.py
    - privacyguard/pii/normalize.py
    - privacyguard/pii/confidence.py
    - privacyguard/pii/mask.py
    - privacyguard/pii/overlap.py
    - privacyguard/pii/engine.py
  </files>
  <read_first>
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 189-238 — id_card.py Pitfall 3 defensive guards)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 244-286 — phone_segment.py exhaustive prefix tables)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 324-374 — normalize.py map_flat_to_original None-on-failure defensive)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 378-401 — confidence.py four-branch classify_hit)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 405-434 — mask.py length-defensive partial masks)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 438-462 — overlap.py validator_passed-priority dedup)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 466-535 — engine.py ENGINE-04 cache + ENGINE-06 flatten integration)
    - .planning/phases/01-pdf/01-RESEARCH.md (lines 738-776 — Pitfall 10 re timeout absence)
  </read_first>
  <action>
    Harden each module to make Task 1's RED tests turn GREEN. Do NOT rename public symbols (D-05 PIIHit schema + D-02 package boundary one-way).

    **privacyguard/pii/validators/id_card.py**:
    - Add defensive guards to `validate_18`: explicit length check `len(id_str) == 18`, explicit `id_str[:17].isdigit()`, explicit last char in `'0123456789Xx'`, then `last.upper() == compute_check_digit(id_str[:17])`.
    - Harden `upgrade_15_to_18`: empty-input guard, length check, digit check, then `body17 = id15[:6] + '19' + id15[6:]` and `body17 + compute_check_digit(body17)`.
    - **B1 second-gate additions:**
      - `is_valid_admin_division_prefix_2(prefix2: str) -> bool`: accepts `"11","12","13","14","15","21","22","23","31","32","33","34","35","36","37","41","42","43","44","45","46","50","51","52","53","54","61","62","63","64","65","71","81","82"`. Returns False for `"00"`, `"90"`–`"99"`, or any prefix not in the whitelist. Backed by `frozenset` for O(1) lookup.
      - `is_real_calendar_date(yy: int, mm: int, dd: int) -> bool`: validates month 1-12; day 1 to `calendar.monthrange(1900 + yy, mm)[1]` (handles Feb leap years). Returns False for out-of-range inputs.
    - `validate_15(id_str)`: empty/length/digit guard → `upgrade_15_to_18` → if empty: False → `is_valid_admin_division_prefix_2(upgraded[:2])` → if False: False → `is_real_calendar_date(int(upgraded[8:10]), int(upgraded[10:12]), int(upgraded[12:14]))` → if False: False → `validate_18(upgraded)`.

    **privacyguard/pii/validators/phone_segment.py**:
    - Add explicit length-11 check before any prefix logic.
    - Add `phone11.isdigit()` check.
    - Add `phone11.startswith('1')` check.
    - Check `PHONE_EXCLUDED_PREFIX_4` before prefix-3 (since 1349 etc. could otherwise pass prefix-3 check `134` is not in personal whitelist, but explicit 4-digit check ensures future prefix expansion).
    - Check `PHONE_EXCLUDED_PREFIX_3` before `PHONE_PERSONAL_PREFIX_3` membership.
    - The 4-digit prefixes in EXCLUDED_PREFIX_4 — verify against current implementation; if not exhaustive add `1740`, `1741`, `1440`, `1349` (already present per PATTERNS.md line 271).
    - Add a smoke comment indicating the `[ASSUMED]` baseline — Phase 2+ adds MIIT quarterly review process.

    **privacyguard/pii/normalize.py**:
    - `normalize_digits(text)`: ensure `_SEPARATOR_CHARS` regex is `r'[-\s　]+'` (fullwidth space U+3000 explicitly).
    - `flatten_for_match(text)`: regex `r'[\s\n\r\t　-]+'` strips all whitespace + hyphens (ENGINE-06 cross-line).
    - `map_flat_to_original(flat_text, flat_span, original_text)`:
      - Walk `original_text` char by char maintaining `flat_pos` (which flat char we've consumed) and `orig_pos` (which original char we're at).
      - For each original char, if it's a separator (whitespace / hyphen / fullwidth space) skip it (no flat_pos advance).
      - If fullwidth digit, treat as equivalent to ASCII digit (advance flat_pos by 1).
      - When `flat_pos == flat_start`, record `orig_start`.
      - When `flat_pos == flat_end`, record `orig_end`.
      - If loop ends without finding both, return `(None, None)` (NOT 0 — defensive guard prevents silent mis-mapping).
      - Otherwise return `(orig_start, orig_end)`.

    **privacyguard/pii/confidence.py**:
    - `classify_hit(validator_passed, regex_matched, source) -> ConfidenceTier`:
      - If `validator_passed and regex_matched`: return "HIGH".
      - If `regex_matched` (but not validator_passed): return "MEDIUM".
      - Otherwise: return "LOW".
    - The `source` parameter is currently unused in tier assignment; keep as part of signature for Phase 2+ context-aware tiering.

    **privacyguard/pii/mask.py**:
    - `partial_mask_id_card(normalized)`: if `len(normalized) != 18`, return `'*' * len(normalized)` (defensive); else `normalized[:6] + '*' * 8 + normalized[14:]`.
    - `partial_mask_phone(normalized)`: if `len(normalized) != 11`, return `'*' * len(normalized)`; else `normalized[:3] + '*' * 4 + normalized[7:]`.
    - `mask_for_entity(entity_type, normalized)`: dispatch by entity_type; default `'*' * len(normalized)`.

    **privacyguard/pii/overlap.py**:
    - `resolve(hits: List[PIIHit]) -> List[PIIHit]`:
      - Build dict keyed by `(page_offset, page_length)`.
      - On collision: keep `validator_passed=True` over False; if both same validator_passed, keep first encountered.
      - Return sorted by `(page_offset, page_length)`.

    **privacyguard/pii/engine.py**:
    - Add internal cache: `self._mask_cache: Dict[Tuple[str, str], str] = {}`.
    - Add instance attribute: `self.last_error: Optional[str] = None` — reset to None at the top of `detect()`; set to `f"{type(exc).__name__}: {exc}"` in any except branch (W1 — engine failures must be observable to the UI, not swallowed into stdout).
    - Add class attribute `DEFAULT_TEXT_PAGE: Any` placeholder; actual page is passed per call.
    - In `_check_id_card` and `_check_phone`:
      - For each candidate: run validator; if validator_passed, compute `mask = self._mask_cache.get((entity_type, normalized))` else `mask_for_entity(entity_type, normalized)`; cache the result.
      - This guarantees ENGINE-04 consistency across multiple hits within the same engine instance.
    - In `detect()`:
      - For text-layer source: **B2 fix — preserve the safe pattern from `privacyguard/ocr/text_pdf.py:36-38`.** DO NOT call `page.search_for(normalized_text)` directly (the normalized text has separators / fullwidth digits stripped, so PyMuPDF cannot match the original page literal). Instead:
        1. Compute `orig_span = map_flat_to_original(flat_text, m.span(), text)` — this returns the original (start, end) indices in `text`.
        2. Extract `original_substring = text[orig_start:orig_end]`.
        3. Call `page.search_for(original_substring)` to get candidate rects.
        4. **Fallback when original returns empty rects:** split `original_substring` on `[-\s　]+` to get `chunks`. For each `chunk` with length ≥ 6 (avoid noise), call `page.search_for(chunk)`. If any chunk returns non-empty rects, union their bounding rects (min x0/y0, max x1/y1) into one `QRectF`.
        5. **Zero-area / unresolvable guard (W-A):** if the union is empty OR has width 0 OR height 0 (degenerate rect), the hit IS NOT silently dropped. Instead: append a copy of the PIIHit to `self.unresolved_hits` with `confidence_tier="MEDIUM"` and a special `source` value `"unresolved"` (or carry the original `source` but flag via `mask_strategy` set to `"<unresolved>"`); also append a row to `self.error_log` as `("PII NO-RECT", page_idx, candidate_string)`. This ensures the engine DETECTED PII but failed to locate it on the page — that fact must be visible to the user, not vanish. Phase 01-03 wires the UI surface: `MainWindow._on_pii_engine_error` slot reads `engine.unresolved_hits` + `engine.error_log` after each `detect()` call and surfaces to the status chip per UI-SPEC §Copywriting (info bar message: "未定位敏感项 N 项，请人工确认" + "识别引擎初始化失败（{exception_class}）。请重新打开或前往设置关闭隐私识别。" for engine errors). The hit is still NOT passed to `apply_pii_redactions` (zero-area rect → do not redact at origin, that's the original silent-leak path); the user manually handles them or accepts the false-clean export. W-A contract: unresolvable hits are recorded AND surfaced, never silently dropped.
        6. If both paths fail (no rect at all), same as step 5 — record as unresolved + log, do not emit as a redactable hit.
      - For OCR source (`source != "text"`): page_rect comes from the OCR box mapping (set by the OCR worker; the engine trusts the rect passed in via TextUnit — Phase 1 OCR path handled in Plan 01-03).
      - Wrap detect body in try/except for any unexpected exception; on exception, **set `self.last_error = f"{type(exc).__name__}: {exc}"`**, **emit a sentinel return `[PIIHit(entity_type="__ENGINE_ERROR__", ...)]`** OR (preferred) append the error info to a side-channel `self.error_log: List[Tuple[int, str]]` and return hits without the engine-error sentinel. The chosen path is the side-channel `error_log`; the UI / worker reads `engine.last_error` after each `detect()` call and surfaces to the info bar per UI-SPEC §Copywriting error row: "文档打开成功，但隐私识别引擎初始化失败（{exception_class}）。请重新打开或前往设置关闭隐私识别。其他功能仍可正常使用。" (W1 — visible to user, not stdout-only.)
      - **Defensive input cap**: at the top of `detect()`, if `len(text) > 200_000`, truncate to first 200_000 chars and print a one-time-per-engine `[PII WARN] 单页文本超过 200,000 字符，截断以保护 UI 响应`. This guards ENGINE-07 input-size DoS without depending on a non-existent Python re timeout parameter.

    After all edits, run the combined test command:
    `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine -v`
    All previously-RED tests must now be GREEN.
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_text_hit_dedup tests.unit.test_mixed_pdf_ocr tests.unit.test_package_imports tests.unit.test_convergence -v 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m unittest tests.unit.test_pii_validators -v` shows ALL test methods green (TestIdCardChecksum / TestIdCardUpgrade15To18 / TestPhoneSegment / TestIotExclusion / TestIdCardDefensive classes).
    - `python3 -m unittest tests.unit.test_pii_engine -v` shows ALL test methods green (TestPIIHitSchema / TestEngineDetect / TestConfidenceTiers / TestMaskConsistency / TestNormalization / TestCrossBoundary / TestLargeDocumentNoBlock classes).
    - The TestLargeDocumentNoBlock 200KB test completes within 1s (ENGINE-07 input-size defense).
    - The TestMaskConsistency test confirms repeated same normalized entity produces identical mask_strategy.
    - The TestCrossBoundary test confirms cross-newline ID card "110101\n19900307\n8811" is detected as one CN_ID_CARD hit.
    - **B4 import smoke test:** `python3 -c "from privacyguard.pii.hits import PIIHit; h = PIIHit('CN_ID_CARD', 0, 18, (0.0, 0.0, 18.0, 1.0)); print(h.confidence_tier)"` prints `HIGH` without `TypeError`. This is the canonical regression guard for the B4 dataclass-definition bug (defaulted field followed by required field).
    - **I1 15-digit demotion:** `python3 -m unittest tests.unit.test_pii_engine.TestEngineDetect.test_detects_15_digit_via_upgrade -v` green with `confidence_tier == "MEDIUM"` (bare 15-digit without context anchor — `old` / `here` are not anchors).
    - **W-A unresolvable hit recorded:** `python3 -m unittest tests.unit.test_pii_engine.TestEngineDetect.test_zero_area_rect_is_skipped_not_silently_emitted -v` green; after the call, `engine.unresolved_hits` contains the candidate and `engine.error_log` contains the `("PII NO-RECT", ...)` row.
    - `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` (Plan 01-01 tracer test) still green — no regression in end-to-end spine.
    - Existing 79/79 baseline remains green (test_mixed_pdf_ocr / test_path_validation / test_ocr_api / test_package_imports / test_pdf_text_hit_dedup / test_app_config / test_word_replace_rules / test_batch_word_replace / test_config_alignment / test_fstring_safety / test_convergence all pass).
  </acceptance_criteria>
  <done>
    Every NUM-01..03 and ENGINE-01..07 requirement is covered by a passing unit test. The PII engine has defensive guards against malformed input (length, charset, IoT prefixes) and is hardened against 200KB+ single-page text without crashing the worker. mask_strategy is consistent across repeated entities within a single engine instance. Cross-line ID cards are recognized via flatten + map_flat_to_original.
  </done>
  <reversibility>rating="costly" rationale="Hardens module internals; PIIHit schema, package boundary, and validator/normalize function signatures are already locked one-way. Reverting would require coordinated test rewrites across 4+ plans.</reversibility>
</task>

<task type="auto">
  <name>Harden privacyguard.pii private surface + add rule-version self-check</name>
  <files>
    - privacyguard/pii/engine.py
    - privacyguard/pii/__init__.py
  </files>
  <read_first>
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 466-535 — engine.py structure)
    - .planning/phases/01-pdf/01-PATTERNS.md (lines 52-92 — __init__.py lazy pattern)
    - .planning/phases/01-pdf/01-RESEARCH.md (lines 1136-1191 — Validation Architecture)
  </read_first>
  <action>
    Add two small hardening hooks without changing public API:
    1. In `privacyguard/pii/engine.py`, add a class method `PIIEngine.rules_version(cls, rules_data: dict) -> str` returning `rules_data.get("phone_segment", {}).get("next_review", "unknown")` so the UI / test suite can display "下次复审 2026-Q3" without reaching into the dict directly.
    2. In `privacyguard/pii/__init__.py`, add `__doc__` string summarizing the package purpose and a `RULES_VERSION_DEFAULT = "2026-Q1"` constant for fallback when rules.json is unreadable.
    3. Add a smoke assertion at the bottom of test_pii_engine.py that exercises the public lazy import surface — `from privacyguard import PIIEngine, PIIHit, TextUnit, validate_18_id, is_mobile_segment, apply_pii_redactions` — and confirms none of them raise AttributeError. This guards against accidental removal of the lazy export table.

    Run the combined verification command and confirm 79 baseline + all new tests remain green.
  </action>
  <verify>
    <automated>python3 -c "from privacyguard import PIIEngine, PIIHit, TextUnit, validate_18_id, is_mobile_segment, apply_pii_redactions, collect_pii_rects; print('lazy exports OK')" && python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_text_hit_dedup tests.unit.test_mixed_pdf_ocr tests.unit.test_package_imports tests.unit.test_convergence tests.unit.test_app_config -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -c "from privacyguard import PIIEngine, PIIHit, TextUnit, validate_18_id, is_mobile_segment, apply_pii_redactions, collect_pii_rects; print('OK')"` prints OK without AttributeError.
    - `python3 -c "from privacyguard.pii.engine import PIIEngine; print(PIIEngine.rules_version({}))"` prints "unknown" (graceful fallback).
    - `python3 -c "from privacyguard.pii import RULES_VERSION_DEFAULT; print(RULES_VERSION_DEFAULT)"` prints "2026-Q1".
    - Full combined test command returns green for all suites.
  </acceptance_criteria>
  <done>
    Phase 1 engine package is fully hardened with comprehensive test coverage and a stable lazy export surface. Plan 01-03 (worker integration + offline test) can proceed.
  </done>
  <reversibility>rating="reversible" rationale="Adds two small public hooks; removal is straightforward. No public API renaming."</reversibility>
</task>

</tasks>

## Artifacts this phase produces

Plan 01-02 produces test coverage and engine hardening — no new package files. The hardened internals land in:

**Hardened public symbols (modified in 01-02):**
- `privacyguard.pii.validators.id_card.validate_15` — now applies B1 second gate (province prefix + real calendar date) before trusting mod-11-2.
- `privacyguard.pii.validators.id_card.is_valid_admin_division_prefix_2(prefix2)` — NEW public helper for the province prefix check.
- `privacyguard.pii.validators.id_card.is_real_calendar_date(yy, mm, dd)` — NEW public helper for the date validity check.
- `privacyguard.pii.validators.phone_segment.is_mobile_segment` — hardened with explicit length/digit/leading-1/excluded-4-before-excluded-3 prefix ordering.
- `privacyguard.pii.normalize.map_flat_to_original` — hardened to return `(None, None)` on mapping failure (defensive, never silent 0).
- `privacyguard.pii.confidence.classify_hit` — three-branch contract enforced.
- `privacyguard.pii.mask.partial_mask_id_card / partial_mask_phone` — length-defensive: wrong-length input returns `'*' * len(input)`.
- `privacyguard.pii.overlap.resolve` — validator_passed priority over first-encountered.
- `privacyguard.pii.engine.PIIEngine._mask_cache` — `(entity_type, normalized) -> mask_strategy` for ENGINE-04.
- `privacyguard.pii.engine.PIIEngine.last_error: Optional[str]` — NEW instance attribute (W1).
- `privacyguard.pii.engine.PIIEngine.error_log: List[Tuple[Tuple[str, ...], int, str]]` — NEW instance attribute (W1, per-page error record; W-A also logs `("PII NO-RECT", page_idx, candidate)` rows here).
- `privacyguard.pii.engine.PIIEngine.unresolved_hits: List[PIIHit]` — NEW instance attribute (W-A); PIIHit copies that the engine DETECTED but failed to locate on the page (zero-area / no-rect); surfaced to UI in 01-03.
- `privacyguard.pii.engine.PIIEngine.rules_version(rules_data)` — NEW classmethod returning rules_data.get("phone_segment", {}).get("next_review", "unknown").
- `privacyguard.pii.engine.PIIEngine.detect` — B2 fix: page.search_for called with ORIGINAL span text (preserves text_pdf.py:36-38 pattern); separator-split fallback for chunked union rects; zero-area rect guard (skip, not emit at origin).
- `privacyguard.pii.engine.PIIEngine.detect` — 200KB input cap (ENGINE-07).
- `privacyguard.pii.__init__.RULES_VERSION_DEFAULT = "2026-Q1"` — NEW module constant.
- `privacyguard.pii.hits.PIIHit.confidence_tier` default `"HIGH"` — B4 resolution (default value, order unchanged).

**New test files (created in 01-02):**
- `tests/unit/test_pii_validators.py` — TestIdCardChecksum / TestIdCardUpgrade15To18 (with B1 negative tests) / TestIdCaseInsensitiveX / TestPhoneSegment / TestIotExclusion / TestIdCardDefensive / TestPhoneSegmentDefensive.
- `tests/unit/test_pii_engine.py` — TestPIIHitSchema / TestEngineDetect (with B2 separator tests) / TestConfidenceTiers / TestMaskConsistency / TestNormalization / TestCrossBoundary / TestLargeDocumentNoBlock.

**Modified files (in 01-02):**
- `privacyguard/pii/validators/id_card.py` — added second gate + 2 new public helpers.
- `privacyguard/pii/validators/phone_segment.py` — hardened.
- `privacyguard/pii/normalize.py` — defensive None-return.
- `privacyguard/pii/confidence.py` — contract clarification.
- `privacyguard/pii/mask.py` — length defensive.
- `privacyguard/pii/overlap.py` — validator_passed priority.
- `privacyguard/pii/engine.py` — mask cache, last_error, error_log, rules_version, B2 page.search_for fix, 200KB cap.
- `privacyguard/pii/__init__.py` — added RULES_VERSION_DEFAULT constant.

---

<verification>
After all three tasks, the following per-test-class commands (matching `01-VALIDATION.md` Per-Task Verification Map) must each return all-green. The combined-suite command below is the convenience invocation (C4 — per-class commands are authoritative; combined is equivalent):

Per-class:
```
python3 -m unittest tests.unit.test_pii_validators.TestIdCardChecksum -v
python3 -m unittest tests.unit.test_pii_validators.TestIdCardUpgrade15To18 -v
python3 -m unittest tests.unit.test_pii_validators.TestIdCaseInsensitiveX -v
python3 -m unittest tests.unit.test_pii_validators.TestPhoneSegment -v
python3 -m unittest tests.unit.test_pii_validators.TestIotExclusion -v
python3 -m unittest tests.unit.test_pii_engine.TestPIIHitSchema -v
python3 -m unittest tests.unit.test_pii_engine.TestEngineDetect -v
python3 -m unittest tests.unit.test_pii_engine.TestConfidenceTiers -v
python3 -m unittest tests.unit.test_pii_engine.TestMaskConsistency -v
python3 -m unittest tests.unit.test_pii_engine.TestNormalization -v
python3 -m unittest tests.unit.test_pii_engine.TestCrossBoundary -v
python3 -m unittest tests.unit.test_pii_engine.TestLargeDocumentNoBlock -v
```

Combined-suite (equivalent — C4 clarification):
```
python3 -m compileall -q privacyguard tests \
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
      tests.unit.test_pii_validators \
      tests.unit.test_pii_engine \
      -v
```

Expected: ≥79 baseline + ≥2 reverse-extraction + ≥40 validator assertions (including B1 negative tests) + ≥30 engine assertions (including B2 separator tests) all green.
</verification>

<success_criteria>
- Every NUM-01 / NUM-02 / NUM-03 requirement covered by an explicit unit test, including all IoT exclusions.
- Every ENGINE-03 (HIGH/MEDIUM/LOW three-branch) / ENGINE-04 (mask consistency) / ENGINE-05 (fullwidth + offset reverse-map) / ENGINE-06 (cross-line) / ENGINE-07 (200KB input-size defense) covered by a passing test.
- Phase 1 spine (Plan 01-01 tracer) remains green; no regression in end-to-end reverse-extraction.
- 79/79 baseline preserved.
- privacyguard.pii public lazy export surface is stable and smoke-tested.
</success_criteria>

<output>
Create `.planning/phases/01-pdf/01-02-engine-expansion-SUMMARY.md` when done. Commit message: `feat(01-02): validator + engine hardening with full NUM-01..03 and ENGINE-03..07 coverage`.
</output>