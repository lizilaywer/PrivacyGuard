---
phase: 2
slug: pdf
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 来源：`02-RESEARCH.md` § Validation Architecture。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `unittest` (Python stdlib) — 仓库现有 11 个 `tests/unit/test_*.py` 全部基于 `unittest.TestCase`；Phase 1 完成后基线 79/79；Phase 2 完成后升级为 88/88 或 89/89（per D-24） |
| **Config file** | none — `unittest` 自动发现 |
| **Quick run command** | `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine -v` |
| **Full suite command** | `python3 -m compileall -q main.py privacyguard tests && python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_pipeline tests.unit.test_pdf_pii_redaction tests.unit.test_pii_offline -v` |
| **Estimated runtime** | quick ~5s · full ~60s |

---

## Sampling Rate

- **After every task commit:** `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine -v`
- **After every plan wave:** `python3 -m compileall -q main.py privacyguard tests && python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_pii_pipeline tests.unit.test_pii_offline tests.unit.test_package_imports tests.unit.test_convergence -v`
- **Before `/gsd-verify-work`:** Full suite green，含 79/79 既有基线 + Phase 2 新增测试
- **Max feedback latency:** 60 秒

---

## Per-Task Verification Map

> Task IDs 在 PLAN.md 生成后由 executor 回填第 1 列；Requirement / Test Type / Command 列已锁定。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | 02-01 | 0 | OPS-05 | T-2-FIX | 测试数据全部 Faker 合成；bin_prefixes.json LICENSE 归属已记录 | unit | `python3 -m unittest tests.unit.test_pii_validators -v` | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 0 | OPS-03 | T-2-LAZY | `import privacyguard` 不触发 `privacyguard.pii.validators.bank_card` 等 6 个新模块 | unit | `python3 -m unittest tests.unit.test_package_imports -v` | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 1 | NUM-04 | — | 银行卡 Luhn 必过 + 6 位 BIN 词典白名单命中 + 上下文锥点提升 HIGH | unit | `python3 -m unittest tests.unit.test_pii_validators.TestBankCardLuhn -v` | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 1 | NUM-04 | T-2-ORDER-FP | Luhn 通过但 BIN 不命中直接 reject（避免订单号误识别） | unit | `python3 -m unittest tests.unit.test_pii_validators.TestBankCardBinRejection -v` | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 1 | NUM-05 | — | 邮箱 RFC 5322 简化版识别；公共域名后缀 → HIGH，否则 MEDIUM | unit | `python3 -m unittest tests.unit.test_pii_validators.TestEmail -v` | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 1 | FIN-01 | — | USCC GB 32100 mod-31-3 必过；登记管理部门类别代码 8 字符白名单 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestUsccMod31 -v` | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 1 | FIN-02 | — | VAT 8 位传统号 + 全电发票 20 位号 + 上下文锥点 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestVatInvoice -v` | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 1 | FIN-03 | — | 15 位纳税人识别号独立 type CN_TAXPAYER_ID_15；结构校验 MEDIUM | unit | `python3 -m unittest tests.unit.test_pii_validators.TestTaxpayerId15 -v` | ❌ W0 | ⬜ pending |
| TBD | 02-01 | 1 | FIN-04 | — | 银行账号 9-21 位 + 上下文锥点必查；无锥点不产生 candidate | unit | `python3 -m unittest tests.unit.test_pii_validators.TestBankAccount -v` | ❌ W0 | ⬜ pending |
| TBD | 02-02 | 2 | ENGINE-01 | — | 6 个新 entity 自动扫描输出候选 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestEngineBankCard -v` | ❌ W0 | ⬜ pending |
| TBD | 02-02 | 2 | ENGINE-02 | — | 6 个新 entity 完整字段（entity_type / page_offset / page_rect / mask_strategy） | unit | `python3 -m unittest tests.unit.test_pii_engine.TestPIIHitSchema -v` | ❌ W0 | ⬜ pending |
| TBD | 02-02 | 2 | ENGINE-03 | — | HIGH 必 validator_passed；VAT 8 位无锥点 → MEDIUM；银行账号无锥点 reject | unit | `python3 -m unittest tests.unit.test_pii_engine.TestEngineConfidenceTiers -v` | ❌ W0 | ⬜ pending |
| TBD | 02-02 | 2 | ENGINE-04 | — | 同一银行卡 / 邮箱 / USCC 多实例掩码一致 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestMaskConsistency -v` | ❌ W0 | ⬜ pending |
| TBD | 02-02 | 2 | MASK-01 | — | partial mask 写入：`apply_redactions(IMAGE_PIXELS)` 销毁底层 + `page.insert_text` 写 mask_strategy | integration | `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` | ❌ W0 | ⬜ pending |
| TBD | 02-03 | 3 | SAFE-01 | T-2-FAKE | partial mask 写入后 `fitz.open(out).get_text()` 原文不可提取 | integration | `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` | ❌ W0 | ⬜ pending |
| TBD | 02-03 | 3 | SAFE-02 | T-2-FAKE | 反向断言：mask_strategy（如 `110101********1234`）写入 PDF 后能被 `page.get_text()` 看到 | integration | `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` | ❌ W0 | ⬜ pending |
| TBD | 02-03 | 3 | SAFE-03 | T-2-META | `doc.set_metadata()` 后 `doc.metadata["title/author/subject/producer/creator"]` 全空字符串 | integration | `python3 -m unittest tests.unit.test_pdf_metadata_cleared -v` | ❌ W0 | ⬜ pending |
| TBD | 02-03 | 3 | OPS-07 | — | 79/79 既有基线 + Phase 1 16 新增 + Phase 2 新增全部 green | regression | Full suite command above | ✅ 已有 | ⬜ pending |
| TBD | 02-03 | 3 | OPS-04 | T-2-PYINST | Windows / macOS PyInstaller spec `datas` + `hiddenimports` 包含 `bin_prefixes.json` 与 6 个新 validator | build | `bash -n packaging/macos/scripts/build_complete.sh && python3 -m compileall -q packaging` | ⚠️ 需扩展 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/fake_pii.py` — 扩展 `fake_bank_card()` / `fake_email()` / `fake_uscc()` / `fake_vat_invoice_8()` / `fake_vat_invoice_20()` / `fake_taxpayer_id_15()` / `fake_bank_account()` 合成 fixture（OPS-05：禁止真实 PII 入库）
- [ ] `privacyguard/pii/data/bin_prefixes.json` — ~1.2 万条 BIN 词典（CC BY-SA 4.0 LICENSE 引用）+ `bin_prefixes.json.LICENSE` 归属声明
- [ ] `privacyguard/pii/validators/bank_card.py` — Luhn + 6 位 BIN 词典白名单 + 上下文锥点提升 confidence
- [ ] `privacyguard/pii/validators/email.py` — RFC 5322 简化版 + 公共域名后缀档位
- [ ] `privacyguard/pii/validators/uscc.py` — GB 32100 mod-31-3 + 登记管理部门类别代码 8 字符表
- [ ] `privacyguard/pii/validators/vat_invoice.py` — 传统 8 位 + 全电发票 20 位 + 上下文锥点
- [ ] `privacyguard/pii/validators/taxpayer_id.py` — 15 位独立 type（CN_TAXPAYER_ID_15）
- [ ] `privacyguard/pii/validators/bank_account.py` — 9-21 位 + 上下文锥点必查
- [ ] `tests/unit/test_pii_validators.py` — 8 个新测试类（TestBankCardLuhn / TestBankCardBin / TestEmail / TestUsccMod31 / TestUsccCategory / TestVatInvoice / TestTaxpayerId15 / TestBankAccount）
- [ ] `tests/unit/test_pii_engine.py` — 6 个新测试类（TestEngineBankCard / TestEngineEmail / TestEngineUscc / TestEngineVatInvoice / TestEngineTaxpayerId15 / TestEngineBankAccount）
- [ ] `tests/unit/test_pdf_pii_redaction.py` — 扩展：`test_partial_mask_writes_mask_text`（mask_strategy 可提取）+ `test_partial_mask_destroys_original`（原文不可提取）+ `test_metadata_5_fields_cleared_on_save`
- [ ] `tests/unit/test_app_config.py` — 扩展 `pii_settings.per_entity_default` 字段读取/默认值/类型断言
- [ ] `tests/unit/test_package_imports.py` — 扩展：6 个新 validator 模块懒加载断言
- [ ] `tests/unit/test_convergence.py` — 扩展：main.py 不应内联 6 个新 entity 的检测函数
- [ ] `packaging/windows/config/PrivacyGuard_windows.spec` — datas + hiddenimports 同步（cp30 + D-26）
- [ ] `packaging/macos/config/PrivacyGuard.spec` + `build_complete.sh` — macOS 同步

*Phase 2 检测能力全部为新代码，Wave 0 不可跳过。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SettingsDialog "5 隐私识别" tab 新增「脱敏方式」表 9 行复选框 + 底部一括黑/括星按钮 | MASK-02 | PyQt6 widget 渲染 + 互斥逻辑无法在 headless unittest 中可靠断言 | `python3 main.py` → 打开设置 → 切到「隐私识别」tab → 看到 9 行 entity × partial/blackout 下拉；点底部「一括黑」/「一括星」按钮 → 确认 9 行同步翻转 |
| 主工具栏新增「本文件使用全遮蔽」toggle 立即生效 | MASK-02 | runtime UI 状态机无法在 unit test 中覆盖 | `python3 main.py` → 打开 PDF → 勾选「本文件使用全遮蔽」→ 当前 PDF 状态指示变「全遮蔽」；切到另一 PDF → toggle 回到关闭态（不持久化） |
| Partial mask 写入后，导出 PDF 在第三方阅读器中可读 `110101********1234` 形式 | MASK-01 | 第三方渲染器字体替换行为超出 PyMuPDF 断言范围 | 导出后用 Adobe Reader / 浏览器打开，框选脱敏区域，确认看到部分掩码文字（不是空白方块） |
| PDF 文档属性对话框显示 Title/Author/Subject/Producer/Creator 全空 | SAFE-03 | 第三方阅读器元数据面板 UI 行为超出 PyMuPDF 断言范围 | 导出后用 Adobe Reader → 文件 → 属性 → 描述，5 字段确认全空 |
| 500 页合成 PDF 扫描不阻塞 UI | ENGINE-07 | PyQt6 事件循环真机交互 | `python3 main.py` → 打开 500 页合成 PDF → 扫描中拖动窗口/滚动，确认不卡死 → 点击取消 |
| 银行卡 / 邮箱 / USCC / VAT 候选高亮框位置与原文对齐 | FMT-01 | 坐标换算正确性最终需肉眼确认 | `python3 main.py` → 打开含银行卡 + 邮箱 + USCC + VAT 票号的合成 PDF → 逐页目视核对高亮框覆盖 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] Bin prefix dictionary LICENSE attribution recorded in `bin_prefixes.json.LICENSE`
- [ ] All 9 ROADMAP-derived requirements mapped to at least one test
