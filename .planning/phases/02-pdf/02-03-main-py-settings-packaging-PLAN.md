---
phase: 02-pdf
plan: 03
slug: main-py-settings-packaging
type: execute
wave: 3
depends_on:
  - 02-02
files_modified:
  - privacyguard/pii/data/bin_prefixes.json
  - privacyguard/pii/data/bin_prefixes.json.LICENSE
  - main.py
  - config.json
  - config.json.template
  - tests/unit/test_app_config.py
  - tests/unit/test_package_imports.py
  - tests/unit/test_convergence.py
  - packaging/windows/config/PrivacyGuard_windows.spec
  - packaging/macos/config/PrivacyGuard.spec
  - packaging/macos/scripts/build_complete.sh
autonomous: true
requirements:
  - MASK-02
  - SAFE-03
  - OPS-03
  - OPS-04
  - OPS-07
user_setup: []

estimate:
  tokens: 105000
  raw_tokens: 52500
  tasks: 5
  confidence: medium

must_haves:
  truths:
    - `privacyguard/pii/data/bin_prefixes.json` contains >= 10000 unique 6-digit BIN prefixes; the file size is >= 150KB; `bin_prefixes.json.LICENSE` exists in the same directory and contains the strings "CC BY-SA 4.0" and "Wikipedia" (D-27 attribution).
    - `privacyguard.pii.validators.bank_card.get_bin_whitelist()` returns a frozenset containing at least 10000 6-digit strings (loaded from bin_prefixes.json via resource_path); the 02-01 test `test_valid_bin_in_whitelist_passes` now passes with `validate_bank_card(fake_bank_card(bin_prefix='622576'))` returning True (because 622576 is in the loaded whitelist).
    - `MainWindow.save_pdf` calls `clear_pdf_metadata(doc_save)` immediately before `doc_save.save(fname, ...)` — verified by reading the source at `main.py:12490-12504` region AND by an integration test that creates a PDF with all 5 metadata fields populated, opens it, calls the save loop, reopens the output, and asserts all 5 fields == "".
    - `MainWindow.save_pdf` routes `pii_list` through `write_partial_masks(doc_save, i, partial_hits, mode="partial")` and `write_partial_masks(doc_save, i, blackout_hits, mode="blackout")` based on `per_entity_default[hit.entity_type]` from `self.config.get("pii_settings.per_entity_default", {})`; with no override → all hits use `partial` mode; with `self.page_data[0]["mask_override_this_doc"] == "blackout"` → all hits use `blackout` mode.
    - `MainWindow.toolbar_pdf_layout` contains a new checkable toggle `self.btn_mask_override` with text "本文件全遮蔽" (D-12); toggling it writes `self.page_data[0]["mask_override_this_doc"] = "blackout"` or `None`.
    - `SettingsDialog` "5 隐私识别" tab contains a 9-row per-entity table where each row has a QCheckBox (entity enabled) + QComboBox with items ["部分掩码", "全遮蔽"]; 2 bottom buttons "全部设为全遮蔽" + "全部设为部分掩码" flip all 9 rows; saving persists `pii_settings.per_entity_default` to `self.config`.
    - `config.json` and `config.json.template` contain `pii_settings.per_entity_default` dict with all 9 keys (`CN_ID_CARD`, `CN_PHONE`, `CN_BANK_CARD`, `CN_EMAIL`, `CN_USCC`, `CN_TAXPAYER_ID`, `CN_TAXPAYER_ID_15`, `CN_VAT_INVOICE`, `CN_BANK_ACCOUNT`) — each default value `"partial"`.
    - `packaging/windows/config/PrivacyGuard_windows.spec` `hiddenimports` lists the 6 new validator modules (`privacyguard.pii.validators.bank_card`, `email`, `uscc`, `vat_invoice`, `bank_account`, `taxpayer_id`) and `datas` includes `privacyguard/pii/data/` (Phase 1 already had this; bin_prefixes.json ships automatically with the data directory).
    - `packaging/macos/config/PrivacyGuard.spec` and `packaging/macos/scripts/build_complete.sh` are parity-aligned with the Windows spec (B5 parity) — `bin_prefixes.json` presence is checked by the parity script.
    - All 02-01 + 02-02 + Phase 1 baselines still green; the full Phase 2 suite reaches ~131 tests passing.
  artifacts:
    - privacyguard/pii/data/bin_prefixes.json (>= 10000 unique 6-digit BIN prefixes, JSON array under key "bin_prefixes")
    - privacyguard/pii/data/bin_prefixes.json.LICENSE (CC BY-SA 4.0 attribution text with Wikipedia source URL)
    - main.py site 1: SettingsDialog box_pii (lines 1601-1700) extended with 9-row per-entity table + 一括黑 / 一括星 buttons (D-11)
    - main.py site 2: toolbar_pdf_layout (lines 5774-5788) extended with `btn_mask_override` checkable toggle (D-12)
    - main.py site 3: save_pdf PII path (lines 12490-12504) extended to call write_partial_masks (mode=partial|blackout per hit) + clear_pdf_metadata before doc.save (D-21 + D-22 + D-16)
    - main.py site 4: MainWindow.page_data init (line 4908 area) extended — mask_override_this_doc key cleared on new PDF open
    - config.json + config.json.template: `pii_settings.per_entity_default` dict with 9 keys + `pii_settings.scan_scope` extended to 9 entity types
    - tests/unit/test_app_config.py: new `test_simple_config_pii_settings_per_entity_default_round_trip` + `test_simple_config_pii_settings_per_entity_default_default` methods (D-23)
    - tests/unit/test_package_imports.py: new `test_bin_prefixes_json_loadable_via_resource_path` method
    - tests/unit/test_convergence.py: new `test_main_py_no_inline_partial_mask_writer` + `test_main_py_uses_write_partial_masks_in_save_loop` methods
    - packaging/windows/config/PrivacyGuard_windows.spec: 6 new hiddenimports (privacyguard.pii.validators.{bank_card,email,uscc,vat_invoice,bank_account,taxpayer_id}); datas parity preserved
    - packaging/macos/config/PrivacyGuard.spec: 6 new hiddenimports parity with Windows
    - packaging/macos/scripts/build_complete.sh: parity check extended to verify `bin_prefixes.json` exists in the frozen bundle
  key_links:
    - main.py:1008-1700 SettingsDialog box_pii → config.json.pii_settings.per_entity_default (D-11 UI persistence)
    - main.py:5774-5788 toolbar btn_mask_override → self.page_data[0]["mask_override_this_doc"] (D-12 in-memory override)
    - main.py:12490-12504 save_pdf → write_partial_masks(doc_save, i, hits, mode=...) + clear_pdf_metadata(doc_save) → doc.save() (D-22 + D-16 + D-21)
    - config.json.pii_settings.per_entity_default → SimpleConfig round-trip → SimpleConfig.get("pii_settings.per_entity_default", {}) in save_pdf (D-13 persistence)
    - privacyguard/pii/data/bin_prefixes.json → resource_path (cp30) → privacyguard.pii.validators.bank_card.get_bin_whitelist() (D-26 lazy load)
    - bin_prefixes.json.LICENSE → packaging/windows/PrivacyGuard_windows.spec datas → frozen bundle ships LICENSE alongside (D-27)
    - packaging/windows/PrivacyGuard_windows.spec + packaging/macos/PrivacyGuard.spec hiddenimports → 6 new validator modules loadable in frozen bundle (OPS-04 / B5 parity)
  prohibitions:
    - 不得在 SettingsDialog 之外的位置（main.py 的 save_pdf 路径 / 其他 dialog）实现 per-entity mask 模式选择（v37.7.6 收敛原则）
    - 不得让 mask_override_this_doc 键被写入 config.json（仅在 self.page_data 内存中存活，D-12 锁定）
    - 不得让 bank card validator 在 BIN 词典缺失时全量接受；bin_prefixes.json 必须存在（get_bin_whitelist 必须返回非空 frozenset，02-03 任务 1 强制）
    - 不得省略 bin_prefixes.json.LICENSE 的 CC BY-SA 4.0 归属声明（D-27 + cc-by-sa compliance）
    - 不得在 Windows / macOS spec 之间遗漏 6 个新 validator hiddenimports（B5 parity 强制）
    - 不得在 partial mask 写入 helper 内省略 page.insert_text（Phase 1 形态已锁定 + 02-01 测试覆盖）
    - 不得在 clear_pdf_metadata 中填占位字符串；helper 已锁定 5 字段全空（02-01 + SAFE-03）
    - 不得让 9 个 entity key 在 per_entity_default dict 中被重命名或省略（D-13 字段命名锁）
    - 不得让 build_complete.sh parity check 失败时继续构建（cp30 教训）
    - 不得让 PyInstaller frozen 启动报 FileNotFoundError: bin_prefixes.json（OPS-04 + D-26 + cp30 扩展）

threat_model:
  trust_boundaries:
    - {name: SettingsDialog UI input, description: untrusted user toggles per_entity_default; persisted to config.json via SimpleConfig.set}
    - {name: toolbar toggle state, description: in-memory only; not persisted to disk}
    - {name: save_pdf PII path → doc.save, description: PII hits flow from page_data through write_partial_masks (mask_strategy writes to PDF) + clear_pdf_metadata (5 fields zeroed); both must succeed before doc.save}
    - {name: bin_prefixes.json → bank_card validator, description: dictionary file is bundled with frozen PyInstaller app; resource_path must resolve correctly in dev + frozen modes (cp30 extension)}
    - {name: PyInstaller datas → frozen bundle, description: privacyguard/pii/data/ directory entry must include bin_prefixes.json + bin_prefixes.json.LICENSE + rules.json; missing LICENSE = CC BY-SA 4.0 violation}
  stride:
    - {id: T-2-PYINST, category: Denial of Service / Compliance, component: PyInstaller spec datas, severity: high, disposition: mitigate, mitigation: Windows + macOS spec datas entries explicitly include privacyguard/pii/data/; build_complete.sh parity check verifies bin_prefixes.json presence in frozen bundle (cp30 extension); test_package_imports.test_bin_prefixes_json_loadable_via_resource_path validates loadability in dev mode}
    - {id: T-2-BIN-LICENSE, category: Repudiation / Compliance, component: bin_prefixes.json.LICENSE, severity: medium, disposition: mitigate, mitigation: LICENSE file contains CC BY-SA 4.0 attribution with Wikipedia source URL; test_package_imports asserts the LICENSE file exists and contains both "CC BY-SA" and "Wikipedia" keywords; spec datas entry includes the .LICENSE sibling file automatically with the data directory}
    - {id: T-2-CONFIG-LOCK, category: Tampering, component: config.json.pii_settings.per_entity_default field naming, severity: medium, disposition: mitigate, mitigation: D-13 field name locked; test_app_config.test_simple_config_pii_settings_per_entity_default_round_trip verifies the 9 keys and default values; renaming the field requires synchronized edits in config.json + config.json.template + SimpleConfig.get path + tests}
    - {id: T-2-OVERRIDE-LEAK, category: Information Disclosure (cross-document), component: MainWindow.page_data["mask_override_this_doc"], severity: medium, disposition: mitigate, mitigation: D-12 explicit reset on new PDF open; toolbar toggle handler clears page_data[0]["mask_override_this_doc"] when opening a new document; tests/unit/test_package_imports + manual verification path}
    - {id: T-2-PII-WIRING, category: Information Disclosure, component: MainWindow.save_pdf PII path, severity: critical, disposition: mitigate, mitigation: write_partial_masks uses Phase 1 proven add_redact_annot + apply_redactions(IMAGE_PIXELS) path (02-01 already enforced); clear_pdf_metadata called once before doc.save; OCR / manual paths unchanged (D-22); live reverse-extraction test verifies SAFE-01/02}
    - {id: T-2-FIX-2, category: Information Disclosure / Compliance, component: tests/fixtures/fake_pii.py + tests/, severity: high, disposition: mitigate, mitigation: tests/samples/real_* gitignored; no real bank cards / USCC / VAT numbers in any test file; all synthesizers from 02-01 already verified to produce passing-checksum outputs only}

---

<objective>
Wire the Phase 2 engine into the live PrivacyGuard UI: ship the bin_prefixes.json data file with CC BY-SA 4.0 attribution, extend SettingsDialog with a 9-row per-entity partial/blackout table, add a toolbar mask_override toggle, modify MainWindow.save_pdf to call write_partial_masks + clear_pdf_metadata, persist per_entity_default via config.json, and extend Windows / macOS PyInstaller specs for the 6 new validator hiddenimports + bin_prefixes.json data file parity.
</objective>

<purpose>
After 02-01 + 02-02, the engine and 9 validators work in isolation. 02-03 is the wiring layer: ship the BIN data dictionary, expose per-entity mask mode in the user-visible settings UI, wire the partial mask + metadata clear helpers into the live save_pdf path, and ensure both PyInstaller platforms can load the new data + modules. Without 02-03, the Phase 2 engine has no user-visible effect — the user still gets full blackout and metadata is still leaking.
</purpose>

<output>
- bin_prefixes.json + bin_prefixes.json.LICENSE
- 9-row SettingsDialog per-entity table with bulk flip buttons
- Toolbar mask_override toggle
- MainWindow.save_pdf partial mask + metadata clear wiring
- config.json + config.json.template `pii_settings.per_entity_default` field
- Windows + macOS PyInstaller specs + build_complete.sh parity
- All ~131 tests passing
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
@.planning/phases/02-pdf/02-02-engine-expansion-PLAN.md
@.planning/codebase/STRUCTURE.md
@CLAUDE.md
@main.py:12490-12504 (Phase 1 save loop — modify PII path)
@main.py:1008-1700 (SettingsDialog box_pii — extend with per-entity table)
@main.py:5774-5788 (toolbar_pdf_layout — add mask_override toggle)
@main.py:4908 (page_data dict init)
@config.json (pii_settings block — extend with per_entity_default)
@config.json.template (same)
@packaging/windows/config/PrivacyGuard_windows.spec (datas + hiddenimports)
@packaging/macos/config/PrivacyGuard.spec (datas + hiddenimports)
@packaging/macos/scripts/build_complete.sh (parity check)
</context>

<tasks>

<task type="auto">
  <name>Ship bin_prefixes.json + bin_prefixes.json.LICENSE + verify validator now reads >= 10000 entries</name>
  <files>
    - privacyguard/pii/data/bin_prefixes.json
    - privacyguard/pii/data/bin_prefixes.json.LICENSE
    - tests/unit/test_package_imports.py
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 762-787 — bin_prefixes.json schema + LICENSE file format)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 245-254 — BIN dictionary source details; lines 316-328 — CC BY-SA 4.0 attribution minimum content)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 991-1009 — Pitfall 12 BIN dictionary size warning signs)
    - privacyguard/pii/validators/bank_card.py (02-01 load_bin_whitelist + get_bin_whitelist to verify loadability)
    - privacyguard/utils/security.py (resource_path for PyInstaller compat)
    - tests/unit/test_package_imports.py (existing test pattern for OPS-03)
  </read_first>
  <action>
    Create `privacyguard/pii/data/bin_prefixes.json` containing >= 10000 unique 6-digit BIN prefixes covering Visa / Mastercard / Amex / Discover / UnionPay / JCB / Diners / Maestro / 银联 8 networks. The data file MUST be a JSON object with the key `bin_prefixes` containing an array of 6-character string BINs.

    Build the file from public sources per 02-RESEARCH.md §Standard Stack "银行卡 BIN 词典":
    - Source 1 (primary): Wikipedia "Payment card number" article — public BIN list of ~12000+ entries covering 8 networks × 200+ issuing countries. CC BY-SA 4.0.
    - Source 2 (secondary): China UnionPay open announcements for 6-digit 银联 BIN ranges (chakahao.com / open.unionpay.com public test card info).
    - Dedup step: collapse to unique 6-digit prefixes (drop 7-digit / 8-digit expansions).
    - Final count target: 10000-15000 unique entries (D-27 + Claude's Discretion).
    - Encoding: UTF-8; line-delimited JSON is acceptable.

    Schema (exact form per 02-PATTERNS.md lines 768-783):
    ```json
    {
        "_comment": "银行卡 BIN 前缀词典（6 位 ISO/IEC 7812 BIN）",
        "_source": "Wikipedia 'Payment card number' (CC BY-SA 4.0) + 中国银联公开 BIN 公告",
        "_license": "CC BY-SA 4.0 — see bin_prefixes.json.LICENSE",
        "_count_target": "10,000-15,000",
        "bin_prefixes": [
            "414720", "414721", "414722",
            "510510", "510511", "552100",
            "622202", "622203", "622204",
            "... (~12000 entries total)"
        ]
    }
    ```

    Create `privacyguard/pii/data/bin_prefixes.json.LICENSE` with CC BY-SA 4.0 attribution (per 02-RESEARCH.md §CC BY-SA 4.0 归属声明最小内容):
    ```
    PrivacyGuard 银行卡 BIN 词典
    基于 Wikipedia "Payment card number" 词条整理

    Source: https://en.wikipedia.org/wiki/Payment_card_number
    License: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)

    Modifications: 整合中国银联公开 BIN 公告，移除过期条目，按 6 位前缀去重
    ```
    (Per 02-PATTERNS.md lines 319-328; minimum content to satisfy CC BY-SA 4.0 §3(a) attribution.)

    After both files exist, verify:
    - File size of `bin_prefixes.json` >= 150KB (Pitfall 12 warning sign check; 1 万条 ≈ 150KB).
    - `len(json.load(open("bin_prefixes.json"))["bin_prefixes"]) >= 10000` (count assertion).
    - All entries are exactly 6 characters (defensive check).
    - `bin_prefixes.json.LICENSE` exists and contains both "CC BY-SA" and "Wikipedia" substrings.

    Add `tests/unit/test_package_imports.py` new method `test_bin_prefixes_json_loadable_via_resource_path`:
    - Use `privacyguard.utils.security.resource_path("privacyguard/pii/data/bin_prefixes.json")` to resolve path.
    - Load JSON; assert `len(data["bin_prefixes"]) >= 10000`.
    - Assert all entries are 6-char strings.
    - Assert the LICENSE sibling file exists and contains both "CC BY-SA" and "Wikipedia".
  </action>
  <verify>
    <automated>python3 -c "import json, os; p = 'privacyguard/pii/data/bin_prefixes.json'; size_kb = os.path.getsize(p) / 1024; data = json.load(open(p, encoding='utf-8')); bins = data['bin_prefixes']; assert size_kb >= 150, f'file too small: {size_kb:.1f}KB'; assert len(bins) >= 10000, f'too few: {len(bins)}'; assert all(len(b) == 6 and b.isalnum() for b in bins); print(f'OK: {len(bins)} entries, {size_kb:.1f}KB'); lpath = 'privacyguard/pii/data/bin_prefixes.json.LICENSE'; lcontent = open(lpath, encoding='utf-8').read(); assert 'CC BY-SA' in lcontent and 'Wikipedia' in lcontent; print('LICENSE OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -c "import json; d=json.load(open('privacyguard/pii/data/bin_prefixes.json')); print(len(d['bin_prefixes']))"` prints a number >= 10000.
    - File size of `bin_prefixes.json` is >= 150KB.
    - `python3 -c "from privacyguard.pii.validators.bank_card import get_bin_whitelist; w = get_bin_whitelist(); print(len(w))"` prints a number >= 10000 (validates resource_path + JSON load path).
    - `python3 -c "from tests.fixtures.fake_pii import fake_bank_card; from privacyguard.pii.validators.bank_card import validate_bank_card; print(validate_bank_card(fake_bank_card(bin_prefix='622576')))"` prints `True` (02-01 test test_valid_bin_in_whitelist_passes now passes with the loaded whitelist).
    - `bin_prefixes.json.LICENSE` file exists and contains both "CC BY-SA" and "Wikipedia" substrings.
    - `python3 -m unittest tests.unit.test_package_imports.TestPrivacyGuardImports.test_bin_prefixes_json_loadable_via_resource_path -v` shows `OK`.
  </acceptance_criteria>
  <done>
    bin_prefixes.json contains >= 10000 unique 6-digit BIN prefixes (file size >= 150KB); bin_prefixes.json.LICENSE contains the required CC BY-SA 4.0 attribution; bank_card validator now resolves BINs from the loaded whitelist; test_package_imports new method green; Phase 1 + 02-01 + 02-02 baselines remain green.
  </done>
  <reversibility>rating="reversible" rationale="JSON data file + LICENSE text additions; deletion reverts cleanly."</reversibility>
</task>

<task type="auto" tdd="true">
  <name>Extend config.json + config.json.template with per_entity_default + 9-row SettingsDialog per-entity table + bulk flip buttons</name>
  <files>
    - config.json
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 962-1039 — SettingsDialog box_pii extension with 9-row ENTITY_MODE_ROWS + 一括黑/括星 buttons + save_settings persistence)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 1098-1143 — config.json + config.json.template pii_settings.per_entity_default + scan_scope 9-item extension)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 1578-1641 — test_app_config.py test_simple_config_pii_settings_per_entity_default_round_trip + _default methods)
    - config.json (current pii_settings block at lines 83-92 to extend)
    - config.json.template (current pii_settings block at lines 82-90 to extend)
    - main.py:1601-1700 (current SettingsDialog box_pii block — exact location to insert per-entity table)
    - main.py:1008 (SettingsDialog class to find the save_settings path)
    - tests/unit/test_app_config.py (existing test_simple_config_pii_settings_round_trip pattern to mirror)
  </read_first>
  <action>
    **config.json** — Extend the existing `pii_settings` block. Read the current file first to confirm its exact contents. Add `per_entity_default` dict + extend `scan_scope` to 9 entries:
    ```json
    "pii_settings": {
        "engine_enabled": true,
        "auto_redact": true,
        "require_confirmation": false,
        "scan_scope": [
            "CN_ID_CARD",
            "CN_PHONE",
            "CN_BANK_CARD",
            "CN_EMAIL",
            "CN_USCC",
            "CN_TAXPAYER_ID",
            "CN_TAXPAYER_ID_15",
            "CN_VAT_INVOICE",
            "CN_BANK_ACCOUNT"
        ],
        "per_entity_default": {
            "CN_ID_CARD": "partial",
            "CN_PHONE": "partial",
            "CN_BANK_CARD": "partial",
            "CN_EMAIL": "partial",
            "CN_USCC": "partial",
            "CN_TAXPAYER_ID": "partial",
            "CN_TAXPAYER_ID_15": "partial",
            "CN_VAT_INVOICE": "partial",
            "CN_BANK_ACCOUNT": "partial"
        },
        "_comment": "Phase 2 隐私识别引擎设置；D-13 锁定 per_entity_default 字段名"
    },
    ```
    Use Edit (scoped replacement) on the existing pii_settings block to add the two new fields while preserving the 3 existing ones. Do NOT use Write to overwrite the entire config.json (other sections contain user settings that must be preserved).

    **config.json.template** — Same extension applied identically. The template uses a fresh skeleton so Write is acceptable; but preserve all other sections verbatim.

    **main.py:1008-1700 SettingsDialog box_pii** — Extend the existing "5 隐私识别" section card with a 9-row per-entity table:
    - Define a module-level constant `PHASE2_ENTITY_MODE_ROWS = [("CN_ID_CARD", "身份证号"), ("CN_PHONE", "手机号"), ("CN_BANK_CARD", "银行卡"), ("CN_EMAIL", "邮箱"), ("CN_USCC", "统一社会信用代码"), ("CN_TAXPAYER_ID", "纳税人识别号 (18位)"), ("CN_TAXPAYER_ID_15", "纳税人识别号 (15位)"), ("CN_VAT_INVOICE", "增值税发票号"), ("CN_BANK_ACCOUNT", "银行账号")]` (9 rows in D-13 locked order).
    - After the existing 3 QCheckBox + the existing "扫描范围（只读）：身份证号 / 手机号" label, add a new section card body:
    ```python
    lbl_mode = QLabel("脱敏方式（每个实体类型独立设置）：")
    lbl_mode.setObjectName("settingsFieldLabel")
    v_pii.addWidget(lbl_mode)
    self.entity_mode_widgets = {}  # record per-entity QCheckBox + QComboBox references
    per_entity_default = self._load_per_entity_default()  # read from config
    for entity_type, label in PHASE2_ENTITY_MODE_ROWS:
        row = QHBoxLayout()
        cb = QCheckBox(f"启用 {label}")
        cb.setChecked(per_entity_default.get(f"{entity_type}_enabled", True))
        combo = QComboBox()
        combo.addItems(["部分掩码", "全遮蔽"])
        combo.setCurrentText("部分掩码" if per_entity_default.get(entity_type, "partial") == "partial" else "全遮蔽")
        combo.setEnabled(cb.isChecked())
        cb.toggled.connect(lambda checked, c=combo: c.setEnabled(checked))
        row.addWidget(cb)
        row.addWidget(combo, stretch=1)
        v_pii.addLayout(row)
        self.entity_mode_widgets[entity_type] = (cb, combo)
    v_pii.addSpacing(10)
    btn_bulk_layout = QHBoxLayout()
    btn_all_blackout = QPushButton("全部设为全遮蔽")
    btn_all_blackout.clicked.connect(self._bulk_set_entity_mode_blackout)
    btn_all_partial = QPushButton("全部设为部分掩码")
    btn_all_partial.clicked.connect(self._bulk_set_entity_mode_partial)
    btn_bulk_layout.addWidget(btn_all_blackout)
    btn_bulk_layout.addWidget(btn_all_partial)
    btn_bulk_layout.addStretch(1)
    v_pii.addLayout(btn_bulk_layout)
    # Update the read-only scope label to reflect 9 entity types
    lbl_scope.setText("扫描范围：9 类实体（身份证 / 手机 / 银行卡 / 邮箱 / USCC / 纳税人识别号 / VAT 发票号 / 银行账号）")
    ```
    Add 3 new methods to SettingsDialog:
    ```python
    def _load_per_entity_default(self) -> dict:
        if not self.config:
            return {entity: "partial" for entity, _ in PHASE2_ENTITY_MODE_ROWS}
        return self.config.get("pii_settings.per_entity_default", {}) or {}

    def _bulk_set_entity_mode_blackout(self):
        for entity_type, (cb, combo) in self.entity_mode_widgets.items():
            cb.setChecked(True)
            combo.setCurrentText("全遮蔽")

    def _bulk_set_entity_mode_partial(self):
        for entity_type, (cb, combo) in self.entity_mode_widgets.items():
            cb.setChecked(True)
            combo.setCurrentText("部分掩码")
    ```
    In the existing `save_settings` method, append:
    ```python
    per_entity_default_new = {}
    for entity_type, (cb, combo) in self.entity_mode_widgets.items():
        per_entity_default_new[entity_type] = "blackout" if combo.currentText() == "全遮蔽" else "partial"
    self.config.set("pii_settings.per_entity_default", per_entity_default_new, persist=False)
    ```
    (Do NOT remove the existing 3 save_settings lines for engine_enabled / auto_redact / require_confirmation.)

    **tests/unit/test_app_config.py** — Add 2 new test methods:
    - `test_simple_config_pii_settings_per_entity_default_round_trip`: open SimpleConfig with a temp file; set per_entity_default with all 9 keys (one set to "blackout" to test mixed values); save; reload; assert loaded dict has 9 keys + the "blackout" value preserved.
    - `test_simple_config_pii_settings_per_entity_default_default`: open SimpleConfig with empty config; assert `config.get("pii_settings.per_entity_default") is None` (no default; caller handles missing).

    After all edits, run `python3 -m unittest tests.unit.test_app_config -v` and confirm both new methods pass.
  </action>
  <verify>
    <automated>python3 -c "import json; c=json.load(open('config.json')); print(len(c['pii_settings']['per_entity_default']), len(c['pii_settings']['scan_scope']))" && python3 -c "import json; c=json.load(open('config.json.template')); print(len(c['pii_settings']['per_entity_default']), len(c['pii_settings']['scan_scope']))" && python3 -m unittest tests.unit.test_app_config -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -c "import json; c=json.load(open('config.json')); pe=c['pii_settings']['per_entity_default']; ss=c['pii_settings']['scan_scope']; print(len(pe), len(ss), all(pe[k]=='partial' for k in pe))"` prints `9 9 True` (per_entity_default has 9 keys, all "partial"; scan_scope has 9 entries).
    - `python3 -c "import json; c=json.load(open('config.json.template')); print(len(c['pii_settings']['per_entity_default']), len(c['pii_settings']['scan_scope']))"` prints `9 9`.
    - `python3 -m unittest tests.unit.test_app_config -v` shows both new test methods (`test_simple_config_pii_settings_per_entity_default_round_trip` + `test_simple_config_pii_settings_per_entity_default_default`) green AND the Phase 1 existing methods still green.
    - `python3 -m compileall -q main.py` exits 0 (SettingsDialog edits are syntactically clean — actual UI verification deferred to Task 5 human-verify checkpoint).
    - Live verification: `grep -c "PHASE2_ENTITY_MODE_ROWS" main.py` prints `>= 1`.
    - Live verification: `grep -c "_bulk_set_entity_mode_blackout" main.py` prints `>= 1`.
    - Live verification: `grep -c "per_entity_default" main.py` prints `>= 3` (definition + load + save).
    - Phase 1 + 02-01 + 02-02 baselines still green.
  </acceptance_criteria>
  <done>
    config.json + config.json.template now contain per_entity_default dict with 9 keys + scan_scope extended to 9 entity types; SettingsDialog "5 隐私识别" tab has a 9-row per-entity table with bulk flip buttons; save_settings persists per_entity_default; 2 new app_config tests green; Phase 1 + 02-01 + 02-02 baselines remain green.
  </done>
  <reversibility>rating="costly" rationale="D-13 field naming locked; SettingsDialog box_pii extended; reverting requires coordinated edits across config.json + config.json.template + main.py + tests/unit/test_app_config.py."</reversibility>
</task>

<task type="auto" tdd="true">
  <name>Toolbar mask_override toggle + MainWindow.save_pdf wiring + integration test</name>
  <files>
    - main.py
    - tests/unit/test_convergence.py
    - tests/unit/test_pdf_pii_redaction.py
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 891-954 — main.py:12490-12504 save_pdf PII path rewrite with write_partial_masks + clear_pdf_metadata)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 1058-1089 — toolbar btn_mask_override toggle + _toggle_mask_override_this_doc handler + page_data reset on open_pdf)
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 2167-2174 — convergence test extensions for write_partial_masks + clear_pdf_metadata)
    - main.py:12490-12504 (current save loop — exact location of PII path to modify)
    - main.py:5774-5788 (current toolbar_pdf_layout — exact location to add btn_mask_override)
    - main.py:4908 (page_data dict init — exact location to add mask_override_this_doc key reset)
    - main.py:1008 (SettingsDialog reference — already extended in Task 2)
    - privacyguard.pii.pdf_adapter.write_partial_masks + clear_pdf_metadata (02-01 functions to call)
    - tests/unit/test_pdf_pii_redaction.py (existing TestPartialMaskWritesMaskText + TestPdfPiiRedaction patterns to extend)
    - tests/unit/test_convergence.py (existing TestPiiConvergence to extend)
  </read_first>
  <action>
    **main.py toolbar (lines 5774-5788 area)** — Add a new checkable toggle in the `toolbar_pdf_layout` after the existing `rb_black` / `rb_white` toggles:
    ```python
    self.btn_mask_override = self.create_btn("本文件全遮蔽", self._toggle_mask_override_this_doc, style="toggle")
    self.btn_mask_override.setObjectName("toolbarToggleButton")
    self.btn_mask_override.setCheckable(True)
    self.btn_mask_override.setChecked(False)
    self.btn_mask_override.setToolTip("勾选后，当前 PDF 临时覆盖全局 per_entity 设置，强制全部 entity 走全遮蔽。切换状态随当前 PDF 生命周期，不持久化。")
    self.toolbar_pdf_layout.addWidget(self.btn_mask_override)


    def _toggle_mask_override_this_doc(self, checked: bool):
        """D-12: 写入 self.page_data[0]["mask_override_this_doc"] = "blackout" | None。"""
        if not self.page_data or 0 not in self.page_data:
            self.page_data = {0: {}} if not self.page_data else self.page_data
        self.page_data[0]["mask_override_this_doc"] = "blackout" if checked else None
    ```
    In the existing `_open_pdf` (or equivalent open path) reset the toggle: `self.btn_mask_override.setChecked(False)` (or similar path). Search main.py for the existing `self.page_data = {}` reset pattern and add the toggle reset immediately after.

    **main.py save_pdf (lines 12490-12504 area) — LOCKED REFACTOR STRUCTURE (warning #3 fix)** — The save loop MUST be refactored to the following single-pass unified approach (the "LOCKED refactor structure" block below). Do NOT use the earlier "call write_partial_masks separately for partial/blackout per page" approach (lines removed by this revision). PyMuPDF `page.apply_redactions()` is one-shot per page; calling it twice (once for OCR/manual and once inside write_partial_masks for PII) will fail at runtime. The LOCKED approach collects ALL rects (OCR + manual + PII partial + PII blackout) into one pass, calls `add_redact_annot` for each, calls `page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)` ONCE for the whole page, then iterates partial-mode items to insert mask text. This is the only path the executor should implement. The complete locked implementation is shown in the "LOCKED refactor structure" block below. Modify the PII path to call `write_partial_masks` + add `clear_pdf_metadata` call before `doc.save`. The current Phase 1 code iterates `ocr_list + manual_list + pii_list` and applies `add_redact_annot + apply_redactions(IMAGE_PIXELS)`. Phase 2 keeps `ocr_list + manual_list` paths EXACTLY as Phase 1 (D-22: OCR/manual stay full blackout) and rewires ONLY `pii_list`:

    The previous "competing alternative" approach (where `write_partial_masks` is called separately for partial/blackout paths and `page.apply_redactions` runs again afterward) was REMOVED in this revision because it calls `apply_redactions` twice on the same page, which PyMuPDF rejects at runtime. The single-pass approach below is the only safe implementation.

    **LOCKED refactor structure** (the only path the executor may implement):
    ```python
    # Phase 2 unified: call add_redact_annot for ALL rects (OCR + manual + PII partial/blackout)
    all_pi_rects = []  # collect (hit/rect_obj, mode) tuples
    for r in ocr_list + manual_list:
        all_pi_rects.append((r, "blackout"))  # legacy Phase 1 behavior
    for hit in pii_list:
        if override == "blackout":
            all_pi_rects.append((hit, "blackout"))
        elif per_entity_default.get(hit.entity_type, "partial") == "partial":
            all_pi_rects.append((hit, "partial"))
        else:
            all_pi_rects.append((hit, "blackout"))

    # First pass: add_redact_annot for all (regardless of mode)
    rects_to_apply = []
    for item, mode in all_pi_rects:
        if hasattr(item, "page_rect"):  # PIIHit dataclass
            x, y, w, h = item.page_rect
        else:  # QRectF (ocr/manual)
            x, y, w, h = item.x(), item.y(), item.width(), item.height()
        rect = fitz.Rect(x, y, x + w, y + h)
        annot = page.add_redact_annot(rect)
        annot.set_colors(stroke=fill_col, fill=fill_col)
        annot.update()
        rects_to_apply.append((rect, item, mode))

    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
    for annot in page.annots() or []:
        page.delete_annot(annot)

    # Second pass (partial mode only): insert mask text
    for rect, item, mode in rects_to_apply:
        if mode != "partial":
            continue
        if hasattr(item, "mask_strategy"):  # PIIHit
            mask_text = item.mask_strategy
        else:
            mask_text = ""  # ocr/manual never partial
        if not mask_text:
            continue
        font_size = 11.0
        try:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text") and "mask" not in span.get("text","").lower():
                            font_size = float(span.get("size", 11.0))
                            break
        except Exception:
            pass
        avg_char_w = font_size * 0.6
        text_w = len(mask_text) * avg_char_w + 4
        cx = (rect.x0 + rect.x1) / 2.0
        cy = (rect.y0 + rect.y1) / 2.0 - font_size / 3.0
        page.insert_text((cx - text_w / 2.0, cy), mask_text, fontsize=font_size, fontname="helv", color=(1.0, 1.0, 1.0))
    ```

    After the loop ends (all pages processed), immediately BEFORE `doc.save(...)`:
    ```python
    clear_pdf_metadata(doc_save)
    doc_save.save(fname, garbage=4, deflate=True, clean=True)
    ```

    The above is the **only acceptable implementation**. Any "call write_partial_masks separately for partial/blackout" approach is FORBIDDEN because it triggers PyMuPDF's `apply_redactions()` twice on the same page, which fails at runtime. Do NOT delegate the refactor approach to the implementer — the single-pass unified `add_redact_annot → apply_redactions → insert mask text for partial mode` path is locked.

    **tests/unit/test_pdf_pii_redaction.py** — Add a new integration test `test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata`:
    - Build a synthetic PDF with `fake_id_card()` text on page 0 + `doc.set_metadata({title:'X', author:'Y', subject:'Z', producer:'P', creator:'C'})`.
    - Save via the Phase 1 save loop contract (i.e. directly use `apply_pii_redactions` for a single page + call `clear_pdf_metadata` to simulate save_pdf behavior — the actual MainWindow.save_pdf is not directly callable from tests because it depends on MainWindow / QApplication).
    - Alternatively, mock the MainWindow.save_pdf behavior by reading the main.py source and asserting it contains the expected wiring (call `write_partial_masks` + `clear_pdf_metadata`).
    - Reverse-extract the output PDF; assert (a) original ID card first 10 chars NOT in text; (b) partial mask "110101********XXXX" IS in text; (c) `metadata["title"] == ""` for all 5 fields.

    **tests/unit/test_convergence.py** — Add new method `test_main_py_uses_write_partial_masks_in_save_loop`:
    - Read `MAIN_PY.read_text()`.
    - Assert `"write_partial_masks" in source` (the helper is called from save loop).
    - Assert `"clear_pdf_metadata" in source` (the helper is called before doc.save).
    - Assert `"mask_override_this_doc" in source` (D-12 toggle key).
    - Assert `"per_entity_default" in source` (D-13 config field name).
    - Assert `"def write_partial_masks(" not in source` (no inline impl in main.py).

    After all edits, run the full test command and confirm Phase 1 + 02-01 + 02-02 + new Task 3 tests all green.
  </action>
  <verify>
    <automated>python3 -m compileall -q main.py tests && python3 -m unittest tests.unit.test_convergence.TestPiiConvergence.test_main_py_uses_write_partial_masks_in_save_loop tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_metadata_cleared tests.unit.test_app_config -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m compileall -q main.py` exits 0 (no syntax errors from the save loop refactor).
    - `python3 -m unittest tests.unit.test_convergence -v` shows `test_main_py_uses_write_partial_masks_in_save_loop` green AND all existing convergence tests still green.
    - `python3 -m unittest tests.unit.test_pdf_pii_redaction.TestPartialMaskWritesMaskText -v` shows all existing methods green AND the new integration test method green.
    - `python3 -m unittest tests.unit.test_pdf_metadata_cleared.TestPdfMetadataCleared -v` shows all methods green.
    - Live: `grep -c "write_partial_masks" main.py` prints `>= 2` (import + call).
    - Live: `grep -c "clear_pdf_metadata" main.py` prints `>= 2` (import + call).
    - Live: `grep -c "mask_override_this_doc" main.py` prints `>= 3` (toggle handler + save loop read + reset on open).
    - Live: `grep -c "per_entity_default" main.py` prints `>= 3` (load + dispatch + save).
    - Full Phase 1 + 02-01 + 02-02 baselines (test_mixed_pdf_ocr / test_path_validation / test_ocr_api / test_package_imports / test_pdf_text_hit_dedup / test_app_config / test_word_replace_rules / test_batch_word_replace / test_config_alignment / test_fstring_safety / test_convergence / test_pii_validators / test_pii_engine / test_pdf_pii_redaction / test_pdf_metadata_cleared) all green.
  </acceptance_criteria>
  <done>
    Toolbar mask_override toggle added; MainWindow.save_pdf PII path rewired through write_partial_masks (partial + blackout modes per per_entity_default + mask_override_this_doc); clear_pdf_metadata called before doc.save; integration test green; convergence test enforces main.py uses the helpers (no inline implementations); full test baselines preserved.
  </done>
  <reversibility>rating="costly" rationale="Modifies MainWindow.save_pdf core path + adds toolbar widget + adds page_data key; reverting requires coordinated edits across main.py (~3 sites) + tests/unit/test_convergence.py + tests/unit/test_pdf_pii_redaction.py."</reversibility>
</task>

<task type="auto">
  <name>Sync Windows + macOS PyInstaller specs + build_complete.sh parity check for 6 new validators + bin_prefixes.json data file</name>
  <files>
    - packaging/windows/config/PrivacyGuard_windows.spec
    - packaging/macos/config/PrivacyGuard.spec
    - packaging/macos/scripts/build_complete.sh
  </files>
  <read_first>
    - .planning/phases/02-pdf/02-PATTERNS.md (lines 1649-1758 — PrivacyGuard_windows.spec + PrivacyGuard.spec datas + hiddenimports extension with 6 new validators)
    - .planning/phases/02-pdf/02-RESEARCH.md (lines 963-985 — cp30 extension: PyInstaller datas + parity check additions for bin_prefixes.json)
    - packaging/windows/config/PrivacyGuard_windows.spec:158-164 (Phase 1 hiddenimports block to extend)
    - packaging/windows/config/PrivacyGuard_windows.spec:194 (Phase 1 datas block; privacyguard/pii/data already included)
    - packaging/macos/config/PrivacyGuard.spec:46 (Phase 1 datas block)
    - packaging/macos/config/PrivacyGuard.spec:95-101 (Phase 1 hiddenimports block)
    - packaging/macos/scripts/build_complete.sh:141-145 (Phase 1 parity check for rules.json to extend for bin_prefixes.json)
    - tests/unit/test_package_imports.py (existing OPS-03 + test_bin_prefixes_json_loadable_via_resource_path from Task 1)
  </read_read_first>
  <action>
    Extend both PyInstaller specs with the 6 new validator hiddenimports (B5 parity) + extend the macOS parity check to verify `bin_prefixes.json` is present in the frozen bundle.

    **packaging/windows/config/PrivacyGuard_windows.spec** — Extend the `hiddenimports=[...]` block (lines 158-164 area) by appending 6 entries after the existing Phase 1 validators:
    ```python
    'privacyguard.pii.validators.bank_card',
    'privacyguard.pii.validators.email',
    'privacyguard.pii.validators.uscc',
    'privacyguard.pii.validators.vat_invoice',
    'privacyguard.pii.validators.bank_account',
    'privacyguard.pii.validators.taxpayer_id',
    ```
    The Phase 1 datas block already includes `(os.path.join(project_root, 'privacyguard', 'pii', 'data'), 'privacyguard/pii/data')` — this automatically bundles `bin_prefixes.json` + `bin_prefixes.json.LICENSE` + `rules.json`. No datas extension needed (verify the entry is present at line 194 area).

    **packaging/macos/config/PrivacyGuard.spec** — Apply the IDENTICAL 6-entry hiddenimports extension (B5 parity). Append the 6 lines after the Phase 1 validators (lines 95-101 area).

    **packaging/macos/scripts/build_complete.sh** — Extend the existing parity check (lines 141-145 area) to verify `bin_prefixes.json` is present in the frozen bundle alongside `rules.json`. Find the existing `test -f "$APP_PATH/Contents/Resources/privacyguard/pii/data/rules.json"` line and add immediately after:
    ```bash
    if [ -f "$APP_PATH/Contents/Resources/privacyguard/pii/data/bin_prefixes.json" ]; then
        echo "  [OK] bin_prefixes.json 存在"
    else
        echo "  [FAIL] bin_prefixes.json 缺失"
        exit 1
    fi
    ```
    (Mirror the exact style of the rules.json check — same indentation, same error semantics.)

    After all 3 files are modified, run:
    - `python3 -m compileall -q packaging/` exits 0 (Python syntax).
    - `bash -n packaging/macos/scripts/build_complete.sh` exits 0 (shell syntax).
    - `python3 -c "from privacyguard.utils.security import resource_path; import json; data = json.load(open(resource_path('privacyguard/pii/data/bin_prefixes.json'), encoding='utf-8')); print('OK', len(data['bin_prefixes']))"` prints `OK 10000+` (validates resource_path in dev mode — frozen mode validated by build script parity check).

    Live verification (cp30 discipline):
    - `grep -c "privacyguard.pii.validators.bank_card" packaging/windows/config/PrivacyGuard_windows.spec` prints `>= 1`.
    - `grep -c "privacyguard.pii.validators.bank_card" packaging/macos/config/PrivacyGuard.spec` prints `>= 1`.
    - `grep -c "bin_prefixes.json" packaging/macos/scripts/build_complete.sh` prints `>= 2` (the new check + maybe the data copy step if present).

    After all edits, the OPS-04 requirement is satisfied (cross-platform PyInstaller frozen bundle includes 6 new validator modules + bin_prefixes.json data + bin_prefixes.json.LICENSE).
  </action>
  <verify>
    <automated>python3 -m compileall -q packaging/ && bash -n packaging/macos/scripts/build_complete.sh && grep -c "privacyguard.pii.validators.bank_card" packaging/windows/config/PrivacyGuard_windows.spec packaging/macos/config/PrivacyGuard.spec && grep -c "bin_prefixes.json" packaging/macos/scripts/build_complete.sh</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -m compileall -q packaging/` exits 0.
    - `bash -n packaging/macos/scripts/build_complete.sh` exits 0 (shell syntax clean).
    - Both specs contain `'privacyguard.pii.validators.bank_card'` (and the other 5 new validator modules): `grep -c "privacyguard.pii.validators.bank_card" packaging/windows/config/PrivacyGuard_windows.spec packaging/macos/config/PrivacyGuard.spec` prints `1:1` or higher.
    - `packaging/macos/scripts/build_complete.sh` contains `bin_prefixes.json` check (count >= 2 including the new file existence test).
    - `python3 -c "from privacyguard.utils.security import resource_path; import json; data = json.load(open(resource_path('privacyguard/pii/data/bin_prefixes.json'), encoding='utf-8')); print('OK', len(data['bin_prefixes']))"` prints `OK` + a number >= 10000.
    - Phase 1 + 02-01 + 02-02 + Task 1+2+3 baselines still green.
  </acceptance_criteria>
  <done>
    Both PyInstaller specs include the 6 new validator hiddenimports (B5 parity); macOS build script parity check verifies bin_prefixes.json is present in the frozen bundle; data directory entry (Phase 1) auto-bundles bin_prefixes.json + LICENSE; resource_path loader resolves correctly in dev mode; full test suite remains green.
  </done>
  <reversibility>rating="costly" rationale="Adds 6 hiddenimports to both PyInstaller specs + parity check extension; reverting requires coordinated edits across 3 packaging files; downstream frozen bundle integrity depends on these entries."</reversibility>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Human verify: SettingsDialog 9-row per-entity table + toolbar toggle + saved PDF shows partial mask + cleared metadata</name>
  <how-to-verify>
    Launch the PrivacyGuard application via `python3 main.py`. Then:

    1. **SettingsDialog verification:** Open Settings (Settings button in toolbar). Navigate to "5 隐私识别" tab. Confirm the section card shows (a) the existing 3 checkboxes (启用隐私识别引擎 / 扫描后自动真脱敏 / HIGH 档命中需手动确认); (b) a new "脱敏方式（每个实体类型独立设置）：" label; (c) 9 rows, each with a "启用 {label}" checkbox + "部分掩码/全遮蔽" combo box (rows for: 身份证号 / 手机号 / 银行卡 / 邮箱 / 统一社会信用代码 / 纳税人识别号 (18位) / 纳税人识别号 (15位) / 增值税发票号 / 银行账号); (d) 2 buttons at the bottom: "全部设为全遮蔽" + "全部设为部分掩码"; (e) the read-only scope label updated to "扫描范围：9 类实体（身份证 / 手机 / 银行卡 / 邮箱 / USCC / 纳税人识别号 / VAT 发票号 / 银行账号）". Click the bulk buttons and verify all 9 combo boxes flip in sync.

    2. **Toolbar verification:** Open a PDF. Confirm the toolbar now contains a "本文件全遮蔽" toggle button. Click it → confirm the toggle button visually indicates pressed state.

    3. **Save + reverse-extract verification:** Open a PDF containing a 18-digit Chinese ID card (synthetic). Save the PDF via the menu. Open the saved PDF in Adobe Reader or a browser:
    - Confirm the document properties (File → Properties → Description) show empty Title / Author / Subject / Producer / Creator fields (SAFE-03).
    - Confirm the ID card region in the PDF shows a partial mask "110101********XXXX" (MASK-01) rather than a fully blacked-out rectangle.

    4. **PyInstaller frozen-bundle verification (optional but recommended):** On macOS: `cd /mnt/g/Project/PrivacyGuard && bash packaging/macos/scripts/build_complete.sh` → confirm the parity check at line 141+ prints `[OK] bin_prefixes.json 存在`. On Windows: run `packaging/windows/scripts/build_complete.bat` → confirm the same.

    Report any failures (missing widget, mask text not visible, metadata not cleared) with specific reproduction steps.
  </how-to-verify>
  <resume-signal>Type "approved" if all 4 verification steps pass (or step 4 is skipped on the developer workstation). If any verification step fails, paste the failure mode + screenshot.</resume-signal>
</task>

</tasks>

## Artifacts this phase produces

**Public dataclasses / classes / functions (created in 02-03):**
- (No new functions; 02-03 is wiring + data + UI + packaging only)
- New data file: `bin_prefixes.json` (>= 10000 BIN prefixes; D-26 + D-27)
- New attribution file: `bin_prefixes.json.LICENSE` (CC BY-SA 4.0; D-27)

**New files (created in 02-03):**
- `privacyguard/pii/data/bin_prefixes.json`
- `privacyguard/pii/data/bin_prefixes.json.LICENSE`

**Modified files (in 02-03):**
- `main.py` — 4 sites: SettingsDialog box_pii (per-entity table) + toolbar_pdf_layout (btn_mask_override toggle) + MainWindow.save_pdf (write_partial_masks + clear_pdf_metadata wiring) + page_data init (mask_override_this_doc key reset on new PDF open)
- `config.json` — pii_settings extended with per_entity_default dict (9 keys) + scan_scope extended to 9 entries
- `config.json.template` — same as config.json
- `packaging/windows/config/PrivacyGuard_windows.spec` — 6 new validator hiddenimports appended
- `packaging/macos/config/PrivacyGuard.spec` — 6 new validator hiddenimports appended (B5 parity)
- `packaging/macos/scripts/build_complete.sh` — parity check extended for bin_prefixes.json
- `tests/unit/test_app_config.py` — 2 new methods (test_simple_config_pii_settings_per_entity_default_round_trip + _default)
- `tests/unit/test_package_imports.py` — new test_bin_prefixes_json_loadable_via_resource_path method
- `tests/unit/test_convergence.py` — new test_main_py_uses_write_partial_masks_in_save_loop method
- `tests/unit/test_pdf_pii_redaction.py` — new test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata integration method

**Cross-plan deliverables (NOT in 02-03):**
- None — 02-03 completes the Phase 2 wiring. Phase 3 (Word) / Phase 4 (Excel) / Phase 5 (Image) are separate phases.

---

<verification>
After all tasks complete, the following command sequence must return all-green (Phase 1 baseline 79 + Phase 1 PII 16 + Phase 2 02-01 ~13 + 02-02 ~14 + 02-03 ~5 = ~127+ tests):

```
python3 -m compileall -q main.py privacyguard tests packaging \
  && bash -n packaging/macos/scripts/build_complete.sh \
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

Expected: ~127+ tests all green.

**End-to-end Phase 2 verification:**
- Live engine demo: open a synthetic PDF containing all 9 entity types + their context anchors → PIIEngine.detect returns 9+ PIIHits.
- Live reverse-extraction demo: build PDF with fake_id_card + populated metadata → save via the (test-simulated) save_pdf flow → reopen → assert original ID NOT in text, mask text "110101********XXXX" IS in text, all 5 metadata fields == "".
- Live PyInstaller parity: `bash packaging/macos/scripts/build_complete.sh` → check passes for bin_prefixes.json.
</verification>

<success_criteria>
- bin_prefixes.json shipped with >= 10000 unique 6-digit BIN prefixes + CC BY-SA 4.0 LICENSE attribution.
- MainWindow.save_pdf rewires PII hits through write_partial_masks (per-entity partial/blackout based on per_entity_default config + mask_override_this_doc runtime override); OCR + manual paths unchanged.
- clear_pdf_metadata called before doc.save in save_pdf; all 5 metadata fields (title/author/subject/producer/creator) cleared to empty string.
- SettingsDialog "5 隐私识别" tab contains a 9-row per-entity table with QCheckBox + QComboBox; 2 bulk flip buttons; save_settings persists per_entity_default.
- Toolbar "本文件全遮蔽" toggle wired to self.page_data[0]["mask_override_this_doc"]; toggle resets on new PDF open.
- config.json + config.json.template contain pii_settings.per_entity_default dict with 9 keys.
- Both PyInstaller specs (Windows + macOS) include 6 new validator hiddenimports; build_complete.sh parity check verifies bin_prefixes.json in frozen bundle.
- Phase 1 baseline 79/79 + Phase 1 PII 16/16 + Phase 2 02-01/02-02/02-03 tests all green; OPS-03 lazy-load discipline preserved across the 9 new validators + their helpers.
- All 9 Phase 2 requirement IDs (NUM-04 / NUM-05 / FIN-01..04 / MASK-01 / MASK-02 / SAFE-03) verified end-to-end.
</success_criteria>

<output>
Create `.planning/phases/02-pdf/02-03-main-py-settings-packaging-SUMMARY.md` when done. Commit message: `feat(02-03): ship bin dictionary + SettingsDialog per-entity table + toolbar override + save_pdf partial mask + metadata clear + PyInstaller parity`.
</output>
