---
gsd_state_version: 1.0
milestone: v37.7.6
milestone_name: milestone
status: shipped
stopped_at: Completed 03-G1-01-auto-scan-and-pii-compare-PLAN.md
last_updated: "2026-08-11T23:42:00.000Z"
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 12
  completed_plans: 12
current_phase_name: Word 文档接入识别引擎
---

# PrivacyGuard v38.x — Project State

**Project:** PrivacyGuard 脱敏卫士
**Milestone:** v38.x — Pure-local Chinese PII Recognition + Excel/Image Support
**Updated:** 2026-08-11

---

## Project Reference

**Core value**: 打开文档就自动列出所有敏感项，用户不用再手输关键词。如果自动识别不可靠，这一轮就等于没做。

**Active milestone**: v38.x — embed pure-local Chinese PII auto-recognition engine and extend format support to Excel + standalone images.

**Constraints (must not violate)**:

- 零网络依赖；识别全程在本地完成
- 新增共享逻辑一律放进 `privacyguard/`，不得在 `main.py` 再写一份实现（v37.7.6 收敛原则）
- OCR 与识别引擎保持懒加载，不得在包导入期初始化
- 任何新增模块必须同步验证 Windows / macOS PyInstaller 打包
- 79/79 测试基线保持通过

---

## Current Position

**Phase**: 2 shipped + 02-04 gap closure complete (2026-08-11)
**Cross-platform packaging verification**: complete (2026-08-11)
**Phase 3 Gap Closure (G1)**: G1-01 (auto-scan + pii compare + pii full reload) shipped (2026-08-11)
**Next action**: `/gsd-plan-phase 3` continues Phase 3 verification + Phase 4+ planning

**Progress**: 25% — 2 phases complete out of 8 planned.

---

## Performance Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Phases planned | 8 | 8 |
| Phases complete | 2 | 8 |
| Requirements mapped | 50 | 50 |
| Requirements coverage | 100% | 100% |
| Test baseline | 348/348 pass | 79/79+ pass (now 348/348) |
| Build artifacts | Windows + macOS (spec parity verified) | Windows + macOS (must include PII modules + dictionaries) |
| Active config path | `SimpleConfig` (`main.py`) | unchanged |
| Lazy-loading compliance | OPS-03 strict preserved | unchanged |

---
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01-pdf P01-02 | 45 | 3 tasks | 6 files |
| Phase 03 P04 | 28 | 4 tasks | 5 files |
| Phase 03 G1-01 | 15 | 3 tasks | 2 files (main.py + test) |

## Accumulated Context

### Decisions

- **识别引擎走纯本地规则路线**（regex + 校验位 + 词典 + 上下文锚点）— 不接云端 LLM（破坏"零网络"底线）；不引入 Presidio / spaCy（bundle weight 过大）；自研 `<50 KB Python` 引擎。
- **每个格式走"垂直 MVP 切片"**（PDF → Word → Excel → Image）— 而非横向"先做全部引擎再做全部格式"。这样能在第一个 phase 就端到端验证 PIIHit → 真脱敏的完整链路。
- **SAFE-01 / SAFE-02 在首个产生脱敏产物的切片（Phase 1）就必须就位** — 任何"假脱敏"都是灾难性失败。
- **Detection is format-independent**：一份 `PIIHit` 数据结构贯穿四格式；引擎无 Qt、无线程、无格式 I/O；apply 阶段才在 `DocumentAdapter` 边界做格式分支。
- **新数据存进现有 dict 的新 key**（`page_data[page]["pii"]` / `word_data[key]["pii"]`），不另起数据结构 — 守住 v37.7.6 收敛原则。
- **Excel 走 openpyxl**（唯一能 round-trip 保留公式/样式的库）；图片复用 RapidOCR + Pillow；不引入 xlrd（除非承诺 `.xls` 支持）。
- [Phase ?]: B2: detect(unit, page=None) — page 提供时走真实 page.search_for(original_substring)；fallback 按分隔符拆 chunk union
- [Phase ?]: W-A: 不可定位 hit 记录到 unresolved_hits + error_log（不静默丢弃）
- [Phase ?]: I1: bare 15-digit 无 context anchor → MEDIUM（避免订单号误识别）
- [Phase ?]: page_rect 根因修复：engine 内部通过 page 参数取真实坐标，调用方不再需要各自 page.search_for workaround（test_pdf_pii_redaction.py 保留 safety net）
- [Phase ?]: Word 保存默认 partial；文档级 override 通过独立 MainWindow 字段映射 blackout，并在打开新文档时复位。
- [Phase ?]: PII 必须在既有替换之后按当前段文本重新定位，避免掩码长度变化造成偏移错位。
- [Phase ?]: Windows 与 macOS spec 显式声明 privacyguard.pii.word_adapter；macOS 构建脚本保留 parity 证据。

### Architectural Facts

- `main.py` (~12.6k LOC) 仍是活跃运行时入口；`privacyguard/` 子包已承载部分抽离的共享模块。
- 版本号唯一来源：`version.txt`（当前 `37.7.6`）。任何版本号改动必须同步：`version.txt` → `main.py` → `privacyguard/__version__` → `packaging/` → `CHANGELOG.md`。
- `SimpleConfig`（`main.py`）是当前生效配置；`privacyguard/utils/config.py::ConfigManager` **不是运行时路径**。
- 已有基线能力：PDF（文字/图片/混合 + 手动矩形）、Word（智能扫描 + 手动 + 双栏对比预览 + 批量替换）、高级设置面板、Windows/macOS PyInstaller 打包。
- 已知回归历史：`cp30` 修复过 `privacyguard.utils.security` 模块导入失败（PyInstaller）；新增模块时需同步验证 `datas` 与 `hiddenimports`。

### Open Questions / Research Flags

- **手机号段号白名单** — 需要 MIIT 最新公告交叉验证（166/198/199、190/192/196/197、虚拟运营商段、14X 物联网排除）→ Phase 1 实施前再确认
- **行政区划词典打包策略** — 全集 ~70 万条 vs 省市区分集 ~3500 条；Phase 6 才需要全集
- **全电发票 20 位号码格式** — 新版格式正则确认（Phase 2 末）
- **词典文件 LICENSE 审查** — `Chinese-Names-Corpus` / `sysloser/adcode` / `HALOSTAR/chinese_surnames` 兼容性确认（Phase 1 前）
- **`confidence.py` 是否暴露原始 0.0-1.0 score** — UX 决策，Phase 7 定
- **`RedactionReport` 是否捆绑原文件 SHA-256** — 合规价值 vs IO 成本，Phase 8 定
- **Excel 列头→实体类型映射 schema** — Phase 4 实施前定型

### Active Blockers

None — awaiting user approval of drafted roadmap to begin Phase 1 planning.

---

## Phase Tracking

### Phase 1: PDF 自动识别身份证号与手机号并真脱敏

- **Status**: ✅ Complete (shipped 2026-08-11)
- **Plans**: 3/3
- **Key deliverables**: `privacyguard/pii/` types + Engine + 校验位 + PdfAdapter；PyMuPDF `add_redact_annot + apply_redactions` 真删除；reverse-test 断言
- **First vertical slice** — proves the whole chain works end-to-end

### Phase 2: PDF 增加银行卡/邮箱/财税实体识别与部分掩码

- **Status**: ✅ Complete (shipped 2026-08-11) — 4/4 plans + 02-04 gap closure + cross-platform packaging verified
- **Plans**: 4/4 (02-01 tracer + 02-02 engine expansion + 02-03 main.py/settings/packaging + 02-04 gap closure)
- **Key deliverables**: 6 new validators (USCC / bank_card / email / VAT_invoice / bank_account / taxpayer_id_15), 9-entity engine, partial mask helper with 4-branch mixed dispatch, SettingsDialog 9-row per-entity table, toolbar mask_override toggle, PDF metadata clearing (5 fields), bin_prefixes.json (19,890 entries, CC BY-SA 4.0)
- **Test baseline**: 272/272 pass + 10 new from 02-04 = 282 OK
- **Ship commits**: 068cca3 (02-01) → 0b616a5 (02-02) → 8e48057 (02-03) → 8804f68 (02-04) → fd994ae (08 packaging verification)

### Phase 3: Word 文档接入识别引擎

- **Status**: 🚧 In progress (3 plans shipped: 03-01 → 03-04, plus G1-01 gap closure)
- **Plans**: 6 / 6 (03-01 word-adapter, 03-02 worker-pii-integration, 03-03 merge-and-preview, 03-04 save-and-packaging, 03-G1-01 auto-scan-and-pii-compare, 03-G2-01 clear-core-properties)
- **Depends on**: Phase 1, Phase 2 (now complete)
- **VERIFICATION**: gaps_found (Gap 1/2/3 closed by G1-01; Gap 4 core_properties sanitization closed by G2-01 (2026-08-12); Gap 5 candidate review UI remains — explicitly deferred to Phase 7)

### Phase 3: Word 文档接入识别引擎

- **Status**: Not started
- **Plans**: 0 / TBD
- **Depends on**: Phase 1

### Phase 4: Excel 工作簿支持

- **Status**: Not started
- **Plans**: 0 / TBD
- **Depends on**: Phase 1

### Phase 5: 独立图片文件支持

- **Status**: Not started
- **Plans**: 0 / TBD
- **Depends on**: Phase 1

### Phase 6: 上下文型实体识别

- **Status**: Not started
- **Plans**: 0 / TBD
- **Depends on**: Phase 1

### Phase 7: 候选审阅 UI

- **Status**: Not started
- **Plans**: 0 / TBD
- **Depends on**: Phase 1, Phase 3

### Phase 8: 识别规则编辑 + 审计 + 打包 + 基线

- **Status**: Not started
- **Plans**: 0 / TBD
- **Depends on**: Phase 1

---

## Ship Status

**Phase 1 PR:** https://github.com/lizilaywer/PrivacyGuard/pull/3
**Branch:** `gsd/phase-1-pdf` (fork: rendermay/PrivacyGuard) → `main`
**Phase 2 status:** 4 plans + 02-04 gap closure + 08 cross-platform packaging verification complete
**Latest commits on branch:**

- `fd994ae` docs(08): cross-platform packaging verification for Phase 2 + 02-04
- `8804f68` fix(02-04): close CR-01 + WR-01 + WR-03 + WR-04 from 02-VERIFICATION
- `a8ab75d` docs(02): add phase verification — gaps_found (CR-01 blocker)
- `4765cbb` feat(02-03): PyInstaller spec parity — 6 new validator hiddenimports + bin_prefixes.json parity check
- `f04deca` feat(02-03): toolbar btn_mask_override + save_pdf single-pass unified redaction + integration test
- `00aba9e` feat(02-03): SettingsDialog per-entity table (9 rows) + bulk flip buttons + per_entity_default persist
- `6e48057` feat(02-03): ship bin_prefixes.json (19,890 BINs) + CC BY-SA LICENSE + validator loadability test
- `0b616a5` feat(02-02): GREEN — 3 new validators (VAT/bank account/15-digit taxpayer ID) + 4 real _check_* methods + D-09 双 type 契约
- `068cca3` feat(02-01): engine detect routes 6 new entities + write_partial_masks + clear_pdf_metadata
- `69d5534` docs(01): ship phase 1 — PR lizilaywer/PrivacyGuard#3 [ci skip]

**Phase 2 ready to push** for review/PR.

## Session Continuity

**Last session:** 2026-08-11T23:42:00.000Z
**Stopped at:** Completed 03-G1-01-auto-scan-and-pii-compare-PLAN.md
**Resume file:** None

**Last session**: 2026-08-11 — Phase 3 G1-01 gap closure shipped (Gap 1/2/3 closed).
**Last action**: `ef4b1f1` fix(03-G1-01): inject pii_matches in _build_word_replaced_preview_html (Gap 3) + tests; `9e152bd` fix(03-G1-01): include PII in _has_word_replacement_candidates (Gap 2); `4471968` fix(03-G1-01): auto-start WordWorker PII scan on _open_word_docx (Gap 1).
**Test baseline**: 348/348 pass (was 336, +12 new tests in TestAutoPiiScanOnOpen / TestPiiOnlyDocumentEntersCompareMode / TestPiiFullReloadPreviewContainsMask).
**Resume instructions**: `/gsd-verify-work 3` to re-verify Phase 3 with G1 gaps closed, or `/gsd-plan-phase 4` for Excel support.

---

*State file — refresh after every phase transition.*
