---
phase: 3
slug: word
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest (标准库；项目基线从 Phase 1/2 沿用) |
| **Config file** | 无（unittest 无配置文件；通过 `python3 -m unittest tests.unit.<module>` 调用） |
| **Quick run command** | `python3 -m unittest tests.unit.test_word_pii_adapter tests.unit.test_word_worker_pii tests.unit.test_word_preview_highlight -v` |
| **Full suite command** | `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence tests.unit.test_pii_engine tests.unit.test_pii_validators tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_pii_pipeline tests.unit.test_word_pii_adapter tests.unit.test_word_worker_pii tests.unit.test_word_pii_redaction tests.unit.test_word_preview_highlight -v` |
| **Estimated runtime** | ~30-60 秒（含 295+ 测试） |

---

## Sampling Rate

- **After every task commit:** Run quick run command（4 个 word PII 新增模块）
- **After every plan wave:** Run full suite command（含 Phase 1/2 + Phase 3 全部测试）
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~60 秒（19 个 unittest 模块）

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | FMT-02 | T-03-01 (PIIHit 字段锁) | collect_pii_word_hits 不扩 PIIHit 字段 | unit | `tests.unit.test_word_pii_adapter` | ✅ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | FMT-02 | T-03-02 (word_data 键缺失) | locate_pii_hits_in_paragraph 不修改 word_data 结构 | unit | `tests.unit.test_word_pii_adapter` | ✅ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | FMT-02 | — | apply_pii_replacements_to_docx 不 import docx | unit | `tests.unit.test_word_pii_adapter` | ✅ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | OPS-03 | — | privacyguard.pii.word_adapter 走 _LAZY_IMPORTS 懒加载 | unit | `tests.unit.test_package_imports` | ✅ | ⬜ pending |
| 03-02-01 | 02 | 2 | FMT-02 | T-03-04 (WordWorker 写时序) | word_data[key]["pii"] 与 ocr/manual 键并存、_word_data_lock 保护 | unit | `tests.unit.test_word_worker_pii` | ✅ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | FMT-02 | — | LOW 档候选按 Phase 2 classify_hit 范式过滤 | unit | `tests.unit.test_word_worker_pii` | ✅ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | FMT-02 | T-03-05 (cp27 DOM patch 边界) | merge_word_matches_with_priority 扩展 pii_matches 形参后右栏 DOM patch 不被破坏 | unit | `tests.unit.test_word_preview_highlight` | ✅ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | FMT-02 | — | leftPane data-key 节点保留，高亮不破坏原有结构 | unit | `tests.unit.test_word_preview_highlight` | ✅ W0 | ⬜ pending |
| 03-04-01 | 04 | 4 | FMT-02 | T-03-06 (Word 真脱敏安全) | apply_pii_replacements_to_docx 后 python-docx 重新打开，原敏感字符串不存在 | unit (reverse-extraction) | `tests.unit.test_word_pii_redaction` | ✅ W0 | ⬜ pending |
| 03-04-02 | 04 | 4 | FMT-02 | — | 段级样式保留（paragraph.style.name 不变） | unit | `tests.unit.test_word_pii_redaction` | ✅ W0 | ⬜ pending |
| 03-04-03 | 04 | 4 | FMT-02 | — | partial_mask 字符串在产物中可被搜索到 | unit | `tests.unit.test_word_pii_redaction` | ✅ W0 | ⬜ pending |
| 03-04-04 | 04 | 4 | OPS-04 | T-03-07 (PyInstaller cp30 回归) | privacyguard.pii.word_adapter 加入 hiddenimports | 打包 + 导入测试 | `tests.unit.test_package_imports` + `packaging/windows/scripts/build_complete.bat` 烟雾测试 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_word_pii_adapter.py` — `collect_pii_word_hits` / `locate_pii_hits_in_paragraph` / `apply_pii_replacements_to_docx` 三函数纯函数测试（边界用例 + 跨 run + 同文本重复展开）
- [ ] `tests/unit/test_word_worker_pii.py` — `_ModularWordWorker.run()` 接入 PII 后 `word_data[key]["pii"]` 与现有键并存测试
- [ ] `tests/unit/test_word_pii_redaction.py` — reverse-extraction 端到端测试（python-docx 重新打开后敏感字符串不存在、partial_mask 存在、段样式保留）
- [ ] `tests/unit/test_word_preview_highlight.py` — `merge_word_matches_with_priority` 扩展 `pii_matches` 形参后右栏合并测试
- [ ] `privacyguard/pii/word_adapter.py` ——Wave 0 stub（函数签名 + docstring + 显式 raise NotImplementedError 等待 Wave 1 实现）
- [ ] `privacyguard/pii/__init__.py` `_LAZY_IMPORTS` 注册 word_adapter 三函数

*Existing infrastructure covers 282/282 baseline; Wave 0 adds ~13 new tests → 295+ target.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 双栏预览真机显示 PII 命中 | FMT-02 | 涉及 QWebEngine DOM patch 视觉验证，需真机打开 Word 对比模式 | 1. 打开任意 Word 文档 2. 等 PII 扫描完成 3. 切换对比模式 4. 检查左栏 PII 高亮（深红色）、右栏 partial_mask 文本 5. 检查无空白面板 |
| .docx 产物格式保留 | FMT-02 | 段级样式保留需 Microsoft Word/LibreOffice 渲染验证 | 1. 用 PII 扫描后保存 .docx 2. 用 Microsoft Word 打开 3. 验证段落标题、列表、表格样式与原文一致 4. 验证敏感文本已被替换为 partial_mask |

*Note: Manual verification steps live in `/gsd-verify-work` UAT criteria; PyAutoGUI/QWebEngine 无法替代人工对双栏预览的视觉判断。*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending