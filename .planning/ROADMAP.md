# PrivacyGuard v38.x — PII Auto-Recognition Roadmap

**Project:** PrivacyGuard 脱敏卫士
**Milestone:** v38.x — Pure-local Chinese PII Recognition + Excel/Image Support
**Defined:** 2026-08-10
**Granularity:** fine (8-12 phases)
**Mode:** MVP (vertical slices)

> 每一个 phase 都是一条端到端的垂直切片：从某种文档格式打开 → 自动识别 → 真脱敏 → 导出。
> SAFE-01 / SAFE-02 在首个产生脱敏产物的切片（Phase 1）就必须就位 —— 任何"假脱敏"都是灾难性失败。

---

## Phases

- [x] **Phase 1: PDF 自动识别身份证号与手机号并真脱敏** - 首个端到端垂直切片（PDF + 号码类 + true redaction） (completed 2026-08-11)
- [x] **Phase 2: PDF 增加银行卡/邮箱/财税实体识别与部分掩码** - 扩展 PDF 检测覆盖 + 按实体定制部分掩码 (completed 2026-08-11)
- [ ] **Phase 3: Word 文档接入识别引擎（双栏对比预览自动高亮）** - Word 格式垂直切片
- [ ] **Phase 4: Excel 工作簿支持（全表散点扫描 + 11 隐藏通道 + 列名驱动升级）** - Excel 格式垂直切片
- [ ] **Phase 5: 独立图片文件支持（OCR + 像素级重绘 + EXIF 清除 + re-OCR 验证）** - 图片文件垂直切片
- [ ] **Phase 6: 上下文型实体识别（姓名/机构/地址/业务敏感字段）** - LOW 档候选识别跨四格式落地
- [ ] **Phase 7: 候选审阅 UI（review queue + 实体类型开关 + 文档级白名单 + 撤销栈）** - 误报控制 UX
- [ ] **Phase 8: 识别规则编辑 + 审计报告 + 跨平台打包验证 + 真实文档准确率基线** - 工程保障收尾

---

## Phase Details

### Phase 1: PDF 自动识别身份证号与手机号并真脱敏

**Goal**: 用户打开任意 PDF，无需输入任何关键词，工具自动扫描并标出身份证号与手机号；导出后敏感内容在 PDF 文本层不可还原。
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: ENGINE-01, ENGINE-02, ENGINE-03, ENGINE-04, ENGINE-05, ENGINE-06, ENGINE-07, ENGINE-08, NUM-01, NUM-02, NUM-03, FMT-01, SAFE-01, SAFE-02, OPS-03, OPS-07
**Success Criteria** (what must be TRUE):

  1. User can open a PDF and the tool automatically surfaces all 18-digit and 15-digit ID cards and Mainland phone numbers as candidates without typing any keyword
  2. Exported PDF has truly redacted sensitive regions — `pdftotext` cannot extract the original numbers from redacted regions (verified by reverse-extraction test)
  3. ID card candidates pass GB 11643 mod-11-2 checksum; phone candidates pass the MIIT segment whitelist (个人号段白名单 + 排除 14X 物联网与卫星段)
  4. UI stays responsive while scanning a 500-page PDF; user can cancel mid-scan
  5. Network is unreachable during detection (no telemetry, no API calls)

**Plans**: 3/3 plans executed
**UI hint**: yes

Plans:
**Wave 1**

- [x] 01-01-tracer-PLAN.md — 端到端 spine：validators + engine + adapter + reverse-extraction tracer

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-engine-expansion-PLAN.md — NUM-01/02/03 + ENGINE-03..07 全覆盖（validators/engine/normalize/confidence/mask/overlap）

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-worker-and-ui-PLAN.md — worker pii_signal + main.py UI/settings/canvas/save_loop + config + offline + packaging

---

### Phase 2: PDF 增加银行卡/邮箱/财税实体识别与部分掩码

**Goal**: 同一份 PDF 现在能识别银行卡、邮箱、统一社会信用代码、增值税发票号、纳税人识别号、银行账号等更多实体，并按实体类型套用部分掩码（保留关键片段）。
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: NUM-04, NUM-05, FIN-01, FIN-02, FIN-03, FIN-04, MASK-01, MASK-02, SAFE-03
**Success Criteria** (what must be TRUE):

  1. PDF scan surfaces bank card numbers, email addresses, USCC, VAT invoice numbers, taxpayer IDs, and bank account numbers as candidates
  2. ID card redaction appears as `110101********1234` (前 6 + 后 4), phone as `138****5678`, bank card as `6225 **** **** 1234`, email as `z****@qq.com` — partial masking is the default
  3. User can switch between partial masking and full blackout per entity type or per document
  4. Exported PDF has no original sensitive content in the text layer; document metadata (`Title` / `Author` / `Subject` / `Producer` / `Creator`) is cleared

**Plans**: 4/4 plans executed (01 / 02 / 03 / 04-gap-closure)
**UI hint**: no

Plans:

- [x] 02-01-tracer-PLAN.md — Tracer: USCC validator + partial mask write + metadata clear end-to-end (Wave 1)
- [x] 02-02-engine-expansion-PLAN.md — Engine expansion: VAT invoice + bank account + 15-digit taxpayer ID validators + 9-entity engine coverage (Wave 2)
- [x] 02-03-main-py-settings-packaging-PLAN.md — Ship bin dictionary (CC BY-SA 4.0) + SettingsDialog 9-row per-entity table + toolbar mask_override toggle + save_pdf wiring + PyInstaller parity (Wave 3)
- [x] 02-04-gap-closure-PLAN.md — Gap closure: CR-01 (main.py inline write_partial_masks → single delegation) + WR-01 (engine eager doc) + WR-03 (AST convergence gate) + WR-04 (bank_account multi-occurrence)

---

### Phase 3: Word 文档接入识别引擎（双栏对比预览自动高亮）

**Goal**: As a PrivacyGuard user, I want to open a Word document and automatically review PII candidates highlighted in both comparison panes, so that I can export a securely redacted document whose original sensitive content cannot be recovered.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: FMT-02, UX-01, UX-02
**Success Criteria** (what must be TRUE):

  1. Opening a Word doc automatically surfaces PII candidates without manually clicking "scan"
  2. Candidates highlight in both the original (left) and the masked (right) panes of the compare preview — incremental DOM patch (cp27) is preserved
  3. User can browse a per-block candidate list and confirm each entry before save; list filters by entity type and paginates when over 50 entries
  4. Exported Word doc retains paragraph/table formatting and no longer contains the original sensitive text in its body or document properties

**Plans**: 4/4 plans executed drafted (01 word_adapter / 02 worker-pii / 03 merge-and-preview / 04 save-and-packaging)
**UI hint**: yes

Plans:
**Wave 1**

- [x] 03-01-word-adapter-PLAN.md — Wave 1 Foundation: privacyguard/pii/word_adapter.py 三函数 + _LAZY_IMPORTS 注册 + 三函数纯函数测试 + test_package_imports 懒加载守卫扩展
- [x] 03-02-worker-pii-integration-PLAN.md — Wave 1 Pipeline: _ModularWordWorker.run() 接入 collect_pii_word_hits + word_data["pii"] 字段扩展 + worker PII 端到端测试 (批量入口显式 skip)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-03-merge-and-preview-PLAN.md — Wave 2 UX: merge_word_matches_with_priority pii_matches 形参 + 双栏预览 pii-highlight 渲染 + test_convergence inline 守卫扩展 + DOM patch 边界守护

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03-04-save-and-packaging-PLAN.md — Wave 3 Production: _save_word 接入 apply_pii_replacements_to_docx 真脱敏 + _word_mask_override_this_doc 字段 + toggle 双路径 + PyInstaller 跨平台 hiddenimports 同步 + reverse-extraction 端到端测试

**Wave 4 (Gap Closure)** *(blocked on Wave 3 completion)*

- [x] 03-G1-01-auto-scan-and-pii-compare-PLAN.md — Gap Closure: _open_word_docx 自动启动 WordWorker (Gap 1) + _has_word_replacement_candidates 纳入 PII (Gap 2) + _build_word_replaced_preview_html 注入 pii_matches (Gap 3) + 3 新 TestClass (12 测试方法)
- [x] 03-G2-01-clear-core-properties-PLAN.md — Gap Closure (Gap 4): privacyguard/utils/word_props.py 5 字段清空 helper + _save_word 在 new_doc.save(fname) 之前接入 + PyInstaller hiddenimports 静态 parity (cp30 防回归) + 6 TestClass (11 测试方法)

---

### Phase 4: Excel 工作簿支持（全表散点扫描 + 11 隐藏通道 + 列名驱动升级）

**Goal**: 用户打开 .xlsx 工作簿，工具扫描全部工作表（含隐藏工作表）、批注、定义名称、共享字符串、公式、透视缓存、外部链接、文档属性、修订记录、自动筛选缓存、条件格式、数据验证等所有数据通道；命中整列同类时主动提示按列批量处置。
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: FMT-03, FMT-04, FMT-05, SAFE-06, OPS-05
**Success Criteria** (what must be TRUE):

  1. User can open a .xlsx workbook; the tool scans all sheets (including hidden ones) plus comments, defined names, shared strings, formulas, pivot cache, external links, doc properties, revisions, auto-filter cache, conditional formats, and data validations
  2. When a column header maps to a known PII type (e.g. "身份证号", "手机号") and at least 60% of cells in that column contain matching entities, the tool prompts the user to apply a column-wide upgrade
  3. Saved workbook retains formulas, cell styles, merged ranges, and named ranges (no formatting regression)
  4. No real personal data appears in test fixtures — all test PII is Faker-generated

**Plans**: TBD
**UI hint**: yes

---

### Phase 5: 独立图片文件支持（OCR + 像素级重绘 + EXIF 清除 + re-OCR 验证）

**Goal**: 用户拖入 JPG / PNG / BMP 等独立图片文件，工具通过 OCR 识别敏感内容，以黑色像素重绘敏感区域，并在导出后再次 OCR 验证敏感字串确已消失；导出图片剥离 EXIF 元数据。
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: FMT-06, SAFE-04, SAFE-05
**Success Criteria** (what must be TRUE):

  1. User can drop a JPG / PNG / BMP image onto the window and the tool runs OCR + PII detection on it
  2. Saved image has sensitive regions burned out at the pixel level — no underlying text-layer remains in the image
  3. Tool re-OCRs the saved image after burn-in and asserts no PII candidate reappears (visible "verified clean" indicator in UI)
  4. Exported image has EXIF metadata (including GPS coordinates and device identifiers) stripped

**Plans**: TBD
**UI hint**: no

---

### Phase 6: 上下文型实体识别（姓名/机构/地址/业务敏感字段）

**Goal**: 引擎在 PDF / Word / Excel / Image 四种格式上都能输出基于词典 + 上下文锚点的姓名、机构名、详细地址、金额、合同编号等候选，全部标为 LOW 档待确认。
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: CTX-01, CTX-02, CTX-03, CTX-04, CTX-05
**Success Criteria** (what must be TRUE):

  1. PDF / Word / Excel scan surfaces Chinese personal names when a 姓氏词典 hit appears next to a context anchor (先生 / 女士 / 姓名 label)
  2. Scan surfaces organization names when an 机构后缀 anchor (有限公司 / 集团 / 银行 / 医院) is detected near a candidate
  3. Scan surfaces detailed addresses when admin-division tokens (省 / 市 / 区 / 县 / 路 / 街 / 号) appear
  4. Scan surfaces business-sensitive fields like amounts, contract numbers, project codes, and internal employee IDs
  5. All context-tier candidates require at least one anchor keyword; isolated dictionary hits without context never produce a candidate (CTX-05 hard constraint)

**Plans**: TBD
**UI hint**: no

---

### Phase 7: 候选审阅 UI（review queue + 实体类型开关 + 文档级白名单 + 撤销栈）

**Goal**: 用户在候选审阅对话框中可逐条决定是否脱敏、可按实体类型与来源筛选、可忽略单条而不影响同类其他结果、可对整张文档设白名单、可撤销已自动应用的高置信度脱敏。
**Mode:** mvp
**Depends on**: Phase 1, Phase 3
**Requirements**: UX-03, UX-04, UX-05, UX-06
**Success Criteria** (what must be TRUE):

  1. Candidate review dialog shows all pending candidates with type, location, confidence tier, source, and proposed mask
  2. User can filter candidates by entity type and source; the list paginates when there are more than 50 entries
  3. User can toggle individual entity types on/off globally; toggling off one entity type stops producing new candidates of that type
  4. User can ignore a single candidate without affecting other candidates of the same type
  5. User can add a document-level whitelist; whitelisted substrings never produce candidates in that document
  6. User can undo any auto-applied high-confidence redaction after the fact (撤销栈)

**Plans**: TBD
**UI hint**: yes

---

### Phase 8: 识别规则编辑 + 审计报告 + 跨平台打包验证 + 真实文档准确率基线

**Goal**: 用户可在设置面板中维护自己的识别规则；每次脱敏都生成可审计的 JSON 报告；Windows / macOS 双平台 PyInstaller 打包都能正常加载新模块与词典数据；并基于真实文档建立识别准确率基线。
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: UX-07, OPS-01, OPS-02, OPS-04, OPS-06
**Success Criteria** (what must be TRUE):

  1. Settings panel has an "识别规则" tab where the user can add / remove / edit regex patterns, dictionary entries, and confidence thresholds
  2. Every redaction writes a JSON audit report alongside the output file containing source path, entity list (type / position / confidence / mask), ruleset version, and timestamp
  3. Scans and redactions run on a worker thread; UI stays interactive while processing a 500-page PDF or 100-sheet Excel
  4. PyInstaller-built packages on Windows and macOS both successfully import new `privacyguard.pii.*` modules and load dictionary JSON files (cp30 regression never reappears)
  5. Recall and false-positive rate are measured against a real-document test corpus and tracked in the regression suite

**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. PDF 自动识别身份证号与手机号并真脱敏 | 3/3 | Complete    | 2026-08-11 |
| 2. PDF 增加银行卡/邮箱/财税实体识别与部分掩码 | 4/4 | Complete    | 2026-08-11 |
| 3. Word 文档接入识别引擎 | 4/4 | In Progress|  |
| 4. Excel 工作簿支持 | 0/TBD | Not started | - |
| 5. 独立图片文件支持 | 0/TBD | Not started | - |
| 6. 上下文型实体识别 | 0/TBD | Not started | - |
| 7. 候选审阅 UI | 0/TBD | Not started | - |
| 8. 识别规则编辑 + 审计 + 打包 + 基线 | 0/TBD | Not started | - |

---

## Coverage Notes

- All v1 requirements mapped (50/50) — see `REQUIREMENTS.md` Traceability table.
- SAFE-01 / SAFE-02 land in Phase 1 (the first slice that produces any redacted output) — fake redaction is unacceptable per project pitfall #1.
- OPS-03 (lazy-loading guarantee) is enforced by Phase 1 and re-asserted at every subsequent phase boundary; OPS-04 (dual-platform packaging) is the explicit gate at Phase 8.
- New shared logic goes into `privacyguard/`, never `main.py` — the v37.7.6 convergence must not regress.

---

*Roadmap defined: 2026-08-10*
*Mode: MVP (vertical slices) — every phase delivers an end-to-end user-observable capability.*
