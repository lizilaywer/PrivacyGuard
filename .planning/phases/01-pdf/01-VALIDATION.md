---
phase: 1
slug: pdf
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 来源：`01-RESEARCH.md` § Validation Architecture。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `unittest` (Python stdlib) — 仓库现有 10 个 `tests/unit/test_*.py` 全部基于 `unittest.TestCase` |
| **Config file** | none — `unittest` 自动发现，无需额外框架安装 |
| **Quick run command** | `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine -v` |
| **Full suite command** | `python3 -m compileall -q main.py privacyguard tests && python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_pipeline tests.unit.test_pdf_pii_redaction tests.unit.test_pii_offline -v` |
| **Estimated runtime** | quick ~5s · full ~60s |

---

## Sampling Rate

- **After every task commit:** `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine -v`
- **After every plan wave:** `python3 -m compileall -q main.py privacyguard tests && python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_pii_pipeline tests.unit.test_pii_offline tests.unit.test_package_imports tests.unit.test_convergence -v`
- **Before `/gsd-verify-work`:** Full suite green，含 79/79 既有基线
- **Max feedback latency:** 60 秒

---

## Per-Task Verification Map

> Task IDs 在 PLAN.md 生成后由 executor 回填第 1 列；Requirement / Test Type / Command 列已锁定。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 0 | OPS-05 | — | 测试数据全部 Faker 合成，无真实 PII 入库 | unit | `python3 -m unittest tests.unit.test_pii_validators -v` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | NUM-01 | — | 18 位 ID 通过 GB 11643 mod-11-2；非法校验位拒绝 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestIdCardChecksum -v` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | NUM-01 | — | 15 位 ID 升级 18 位后校验 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestIdCardUpgrade15To18 -v` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | NUM-02 | — | 末位 `X`/`x` 大小写不敏感 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestIdCaseInsensitiveX -v` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | NUM-03 | — | 手机号段命中 MIIT 个人号段白名单 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestPhoneSegment -v` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | NUM-03 | T-1-FP | 14X 物联网/卫星段被排除（不产生候选） | unit | `python3 -m unittest tests.unit.test_pii_validators.TestIotExclusion -v` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | ENGINE-01 | — | 无关键词输入即自动输出全部候选 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestEngineDetect -v` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | ENGINE-02 | — | 每个 hit 含 entity_type/offset/tier/source/mask | unit | `python3 -m unittest tests.unit.test_pii_engine.TestPIIHitSchema -v` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | ENGINE-03 | — | HIGH/MEDIUM/LOW 三档判定正确 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestConfidenceTiers -v` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | ENGINE-04 | — | 同一实体多处出现掩码结果一致 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestMaskConsistency -v` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | ENGINE-05 | — | 全角数字转半角后 offset 可回算原文 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestNormalization -v` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | ENGINE-06 | — | 跨行 / 分栏断裂的号码仍被识别 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestCrossBoundary -v` | ❌ W0 | ⬜ pending |
| TBD | 03 | 3 | ENGINE-07 | — | 500 页扫描不阻塞 UI，可取消 | smoke | `python3 -m unittest tests.unit.test_pii_engine.TestLargeDocumentNoBlock -v` | ❌ W0 | ⬜ pending |
| TBD | 03 | 3 | ENGINE-08 | T-1-NET | 检测全程零出站 socket | unit (socket monkey-patch) | `python3 -m unittest tests.unit.test_pii_offline -v` | ❌ W0 | ⬜ pending |
| TBD | 03 | 3 | FMT-01 | — | PDF 文字层 + 嵌入图片 OCR 双通道接入检测 | integration | `python3 -m unittest tests.unit.test_pdf_pii_pipeline -v` | ❌ W0 | ⬜ pending |
| TBD | 04 | 4 | SAFE-01 | T-1-FAKE | `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` 真删除，非 `draw_rect` | integration | `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` | ❌ W0 | ⬜ pending |
| TBD | 04 | 4 | SAFE-02 | T-1-FAKE | 导出后 `page.get_text()` 反向提取不到原号码 | integration | `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` | ❌ W0 | ⬜ pending |
| TBD | 04 | 4 | OPS-03 | — | `import privacyguard` 不触发 `privacyguard.pii.engine` eager import | unit | `python3 -m unittest tests.unit.test_package_imports -v` | ✅ 需扩展 | ⬜ pending |
| TBD | 04 | 4 | OPS-07 | — | 79/79 既有基线全绿，无回归 | regression | `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence -v` | ✅ 已有 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/fake_pii.py` — `fake_id_card()` / `fake_phone()` Faker 合成 fixture（OPS-05：禁止真实 PII 入库）
- [ ] `tests/e2e/create_pii_test_pdf.py` — PyMuPDF `insert_text` 生成确定性测试 PDF（文字层 / 嵌入图片 / 跨行三种）
- [ ] `tests/unit/test_pii_validators.py` — NUM-01 / NUM-02 / NUM-03 stubs（≥ 20 断言样本）
- [ ] `tests/unit/test_pii_engine.py` — ENGINE-01..07 stubs
- [ ] `tests/unit/test_pdf_pii_pipeline.py` — FMT-01 端到端 stub
- [ ] `tests/unit/test_pdf_pii_redaction.py` — SAFE-01 / SAFE-02 反向提取 stub
- [ ] `tests/unit/test_pii_offline.py` — ENGINE-08 socket monkey-patch stub
- [ ] `tests/unit/test_package_imports.py` 扩展 — OPS-03 懒加载断言
- [ ] `tests/unit/test_convergence.py` 扩展 — `main.py` 不得顶层 import `privacyguard.pii.*`
- [ ] `tests/unit/test_app_config.py` 扩展 — `pii_settings` 默认值断言

*Phase 1 全部检测能力为新代码，Wave 0 不可跳过。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 500 页 PDF 扫描期间 UI 保持可交互、可点击「取消」 | ENGINE-07 | PyQt6 事件循环真机交互无法在 headless unittest 中可靠断言 | `python3 main.py` → 打开 500 页合成 PDF → 扫描中拖动窗口/滚动，确认不卡死 → 点击取消，确认 5s 内停止且无残留线程 |
| 候选高亮框在页面上的视觉位置与号码对齐 | FMT-01 / UI-SPEC | 坐标换算正确性最终需肉眼确认 | `python3 main.py` → 打开混合型测试 PDF → 逐页目视核对高亮框覆盖号码 |
| 导出 PDF 在外部阅读器（Adobe / 浏览器）中不可复制原号码 | SAFE-02 | 第三方渲染器行为超出 PyMuPDF 断言范围 | 导出后用浏览器打开，尝试框选复制脱敏区域，确认无法得到原号码 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
