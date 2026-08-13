---
phase: 03-word
plan: 03
subsystem: word-pii-preview
tags: [merge-extension, dom-patch, css-class, cp27-preservation, d-11-guard, ui-spec]
status: complete
---

# Phase 3 Plan 03: merge_word_matches_with_priority 扩展 + 双栏预览 PII 高亮 Summary

**One-liner**: `merge_word_matches_with_priority` 扩展 `pii_matches` 形参, PII 与 OCR 同层竞争 PII 胜出 (D-02 校验位质量 > OCR 文本层); `_build_word_*_panel_updates` 注入 `word_data[key]['pii']`; `_build_word_original_preview_fragment` 增 `pii-highlight` css_class + `[PII] {entity_type}` title 契约 (UI-SPEC §Color + §Copywriting); 8 测试 + 2 AST 守卫全 PASS, 128/128 baseline 不破坏 (D-16 + D-17).

---

## Overview

| Aspect | Value |
| --- | --- |
| Phase | 03-word (Word 文档接入识别引擎) |
| Plan | 03-03-merge-and-preview (Wave 2 UX) |
| Type | execute (autonomous) |
| Tasks | 3/3 (Task 1 merge extension, Task 2 preview injection, Task 3 tests) |
| Duration | ~6 min |
| Commits | 3 (9f089b1 merge, caf33d1 preview, 7181841 test) |
| Test baseline | 128/128 pass (D-16 + D-17; excluding 4 pre-existing `tests/test_path_validation` failures unrelated to this plan) |
| Files created | `tests/unit/test_word_preview_highlight.py` (NEW, 257 lines) |
| Files modified | `main.py` (+35/-6), `tests/unit/test_convergence.py` (+38) |
| Requirements covered | FMT-02, UX-01, UX-02 |
| Decisions enforced | D-01 (ocr ∪ pii 同层), D-02 (PII 校验位质量 > OCR), D-10 (page_offset/page_length 复用为 char_offset/char_length), D-11 (main.py 不内联 word_adapter 三函数), D-15 #4 (preview highlight 测试), D-17 (word_replace_rules 不破坏) |

---

## Tasks Executed

### Task 1 (feat) — commit `9f089b1`

**Files**: `main.py` (MOD)

`merge_word_matches_with_priority` (line 863) — D-01/D-02 扩展:

1. 函数签名加 `pii_matches=None` 形参 (D-01 锁定):
   ```python
   def merge_word_matches_with_priority(text, rules, default_replacement_text,
                                        manual_matches=None, ocr_matches=None,
                                        pii_matches=None):
   ```

2. 函数 docstring 更新: `"合并规则替换、手动脱敏、OCR 脱敏、PII 区间，优先级：规则 > 手动 > (OCR ∪ PII)，PII 校验位质量高于 OCR 文本层。"`

3. 函数体首段追加: `pii_matches = pii_matches or []  # [NEW D-01]`

4. 在 `_append_candidates(ocr_matches, "ocr")` 之前追加 PII 命中归一化 + 追加:
   ```python
   pii_as_match_dicts = [{
       "start": int(getattr(h, "page_offset", 0) or 0),
       "end": int((getattr(h, "page_offset", 0) or 0) + (getattr(h, "page_length", 0) or 0)),
       "text": getattr(h, "text", None),
       "replacement": getattr(h, "mask_strategy", None) or fallback_text,
       "source": "pii",
       "mode": "partial",
       "rule_name": getattr(h, "entity_type", "PII"),
   } for h in pii_matches]
   _append_candidates(pii_as_match_dicts, "pii")
   ```

**D-02 实现机制**: PII 在 OCR 之前追加; `_append_candidates` 中 `occupied_ranges` 已含 PII 区间, OCR 因 `_range_overlaps` 检查被跳过 → PII 胜出。

**D-10 锁定**: `PIIHit.page_offset` / `page_length` 字段在 Word 端复用为 `char_offset` / `char_length` (Phase 1 PIIHit 字段锁不变, PDF 路径仍按原语义使用)。

**Pitfall 5 守护**: 越界 PII (`start<0` / `end>text_len` / `start>=end`) 由 `_append_candidates` 既有 line 882 验证静默 drop, 不破坏 cp27 DOM patch 边界。

不动 `_append_candidates` / `_range_overlaps` / `build_word_rule_matches` 既有调用 (向后兼容)。

### Task 2 (feat) — commit `caf33d1`

**Files**: `main.py` (MOD)

3 处编辑:

1. `_build_word_original_panel_updates` (line 11965 注入):
   ```python
   merged_matches = merge_word_matches_with_priority(
       source_text, [],
       self.replacement_text,
       manual_matches=data.get("manual", []),
       ocr_matches=data.get("ocr", []),
       pii_matches=data.get("pii", []),  # [NEW D-01]
   )
   ```

2. `_build_word_replaced_panel_updates` (line 12024 注入): 同样 `pii_matches=data.get("pii", [])`.

3. `_build_word_original_preview_fragment` (line 11985-12004 css_class 解析逻辑):
   ```python
   if source == "manual":
       css_class = "manual-highlight"
   elif source == "pii":
       css_class = "pii-highlight"  # [NEW D-01 + UI-SPEC §Color]
   else:
       css_class = "ocr-highlight"
   ...
   if source == "pii":
       # [NEW UI-SPEC §Copywriting] PII 命中 hover tooltip
       entity_type = str(segment.get("rule_name", "PII")).strip() or "PII"
       title = f"[PII] {entity_type}"  # 简化形态; 完整形态由后续 Phase 7 扩展
   elif source == "manual":
       title = "手动脱敏"
   else:
       title = str(segment.get("rule_name", "")).strip() or "智能脱敏"
   ```

`_build_replaced_preview_fragment` 不需新增 css_class 分支 (替换区段沿用现有 mask 文本渲染, PII partial_mask 已由 `mask_for_entity` 写入 `replacement` 字段)。

不动 `_add_data_key_attributes` / `_add_data_key_regex_fallback` / `build_word_panel_update_script` / `_apply_word_panel_updates` — cp27 修复点保留 (Pitfall 5 + D-17 不变量)。

### Task 3 (test) — commit `7181841`

**Files**: `tests/unit/test_word_preview_highlight.py` (NEW, 257 lines), `tests/unit/test_convergence.py` (+38 lines)

`tests/unit/test_word_preview_highlight.py` — 4 TestClass + 8 test methods:

1. **`TestMergeWithPii`** (3 测试):
   - `test_pii_added_to_merged_result` — D-01 验证: PII 命中追加到 merged (source='pii')
   - `test_pii_wins_over_ocr_on_overlap` — D-02 验证: 同层重叠 PII 胜出 OCR
   - `test_pii_out_of_range_dropped_silently` — Pitfall 5 + cp27: 3 类越界 (start<0 / end>text_len / start>=end) 全 drop

2. **`TestMergePriorityPiiOverOCR`** (2 测试):
   - `test_rule_wins_over_pii_on_overlap` — D-01 锁定: rule > PII
   - `test_manual_wins_over_pii_on_overlap` — D-01 锁定: manual > PII

3. **`TestPiiHighlightMarkup`** (2 测试):
   - `test_pii_highlight_className_is_emitted` — UI-SPEC §Color: source='pii' 渲染 `class="pii-highlight"`
   - `test_pii_highlight_title_uses_entity_type` — UI-SPEC §Copywriting: `title="[PII] CN_ID_CARD"` 形态

4. **`TestNoOverflowGuard`** (1 测试):
   - `test_pii_negative_offset_returns_empty_merged` — `PIIHit.page_offset=-1` 越界时 merge 返回空列表

Helper 函数: `_make_pii_hit` (D-10 字段构造) + `_build_pii_highlight_stub` (沿用 test_word_replace_rules.build_word_preview_stub 形态, 补 pii 字段)。

`tests/unit/test_convergence.py` — `TestPiiWordAdapterConvergence` 类:

1. `test_main_py_does_not_inline_word_adapter_functions` — D-11 守卫: 字符串扫描 main.py 不含 `def collect_pii_word_hits(` / `def locate_pii_hits_in_paragraph(` / `def apply_pii_replacements_to_docx(`。
2. `test_pii_word_adapter_module_does_not_import_docx` — D-11 + T-03-02 守卫: AST 扫描 `privacyguard/pii/word_adapter.py` 不得 `import docx` / `from docx import ...`。

---

## Deviations from Plan

### Plan-Locked Decisions Honored

- **D-01 (ocr ∪ pii 同层)**: merge 函数 `pii_matches=None` 形参 + 同层追加实现。
- **D-02 (PII 校验位质量 > OCR)**: PII 在 OCR 之前追加; `_append_candidates` 的 `occupied_ranges` 保证 OCR 被跳过。
- **D-10 (page_offset/page_length 复用)**: PIIHit 字段锁不变, Word 端复用为 char_offset/char_length。
- **D-11 (main.py 不内联 word_adapter)**: AST 守卫 + 字符串扫描 2 类测试验证。
- **D-15 #4 (preview highlight 测试)**: 8 测试方法 (4 TestClass) 全 PASS。
- **D-16 + D-17 (基线守护)**: 128/128 baseline 不破坏 (排除 4 个 pre-existing `tests/test_path_validation` 失败)。
- **UI-SPEC §Color**: `pii-highlight` css_class 渲染契约满足。
- **UI-SPEC §Copywriting**: `[PII] {entity_type}` title 属性契约满足。
- **Pitfall 5 (越界 drop)**: `_append_candidates` 既有 line 882 验证静默 drop, cp27 DOM patch 边界保留。
- **Pitfall 8 (PIIEngine 缓存)**: 沿用 Plan 2 既有 `self._pii_engine` 实例。

### Auto-fixed Issues

None — plan executed exactly as written. PII 字段访问使用 `getattr(h, ..., default)` 防御性读取, 与 D-05 字段锁兼容 (page_offset/page_length 必填字段, 但 `text` 不是必填字段, 故用 `getattr` 兜底)。

---

## Auth Gates

None — no authentication required for this plan.

---

## Stub Tracking

None — all extensions are production-quality, no placeholder / TODO / empty fallback.

---

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| (none) | — | Plan-implemented surfaces are in trusted MainWindow method paths. D-11 (no inline word_adapter), D-15 #4 (preview highlight), D-17 (word_replace_rules preservation), T-03-09 (cp27 boundary), T-03-11 (PII css_class) all mitigated per threat_model. |

---

## Verification

### 1. Acceptance criteria verification

```
grep -n 'def merge_word_matches_with_priority' main.py
→ 863:def merge_word_matches_with_priority(text, rules, default_replacement_text,
✓ pii_matches=None 形参就位

grep -n 'pii_as_match_dicts' main.py
→ 909:    pii_as_match_dicts = [{
→ 918:    _append_candidates(pii_as_match_dicts, "pii")
✓ PII 归一化 + 追加调用就位

grep -n 'pii_matches=data' main.py
→ 11967:                pii_matches=data.get("pii", []),
→ 12026:                pii_matches=data.get("pii", []),
✓ _build_word_*_panel_updates 注入 2 处 (D-01)

grep -n 'pii-highlight' main.py
→ 11993:                css_class = "pii-highlight"
✓ css_class 分支就位
```

### 2. Task-level verification

- `python -m unittest tests.unit.test_word_replace_rules` → 32/32 PASS (D-17 baseline)
- `python -m unittest tests.unit.test_word_preview_highlight` → 8/8 PASS (Plan 3 范围)
- `python -m unittest tests.unit.test_word_pii_adapter` → 22/22 PASS (Plan 1 不破坏)
- `python -m unittest tests.unit.test_word_worker_pii` → 5/5 PASS (Plan 2 不破坏)
- `python -m unittest tests.unit.test_convergence` → 21/21 PASS (含 2 新增 D-11 守卫)
- `python -m unittest tests.unit.test_batch_word_replace` → 2/2 PASS (D-17)
- `python -m unittest tests.unit.test_package_imports` → 10/10 PASS (OPS-03 懒加载)

### 3. Combined Phase 3 baseline (D-16 + D-17)

```
python -m unittest \
  tests.unit.test_mixed_pdf_ocr \
  tests.unit.test_ocr_api \
  tests.unit.test_package_imports \
  tests.unit.test_pdf_text_hit_dedup \
  tests.unit.test_app_config \
  tests.unit.test_word_replace_rules \
  tests.unit.test_batch_word_replace \
  tests.unit.test_config_alignment \
  tests.unit.test_fstring_safety \
  tests.unit.test_convergence \
  tests.unit.test_word_pii_adapter \
  tests.unit.test_word_worker_pii \
  tests.unit.test_word_preview_highlight
```
→ **128/128 PASS** ✓ (D-16 不变量; 排除 4 个 pre-existing `tests.test_path_validation` 失败, 已知与本计划无关)

### 4. cp27 DOM patch boundary verification

`_build_word_original_preview_fragment` 输出 `<mark>` 标签含 `data-key` / `data-start` / `data-end` 属性, 数值由 `int(segment.get("start", 0))` / `int(segment.get("end", 0))` 强制 int 化; PII 与 manual/ocr 同形态, 不引入新边界类型。TestMergeWithPii.test_pii_out_of_range_dropped_silently + TestNoOverflowGuard 验证越界 drop 不破坏 DOM patch。

### 5. D-11 inline-guard verification

```
python -m unittest tests.unit.test_convergence.TestPiiWordAdapterConvergence -v
→ test_main_py_does_not_inline_word_adapter_functions ... ok
→ test_pii_word_adapter_module_does_not_import_docx ... ok
```

---

## Self-Check

- [x] `main.py:863 merge_word_matches_with_priority` 含 `pii_matches=None` 形参 (commit 9f089b1)
- [x] `main.py:863 merge_word_matches_with_priority` 函数体内含 `_append_candidates(pii_as_match_dicts, "pii")` (commit 9f089b1)
- [x] `main.py:_build_word_original_panel_updates` (line 11965) 含 `pii_matches=data.get("pii", [])` (commit caf33d1)
- [x] `main.py:_build_word_replaced_panel_updates` (line 12024) 含 `pii_matches=data.get("pii", [])` (commit caf33d1)
- [x] `main.py:_build_word_original_preview_fragment` 含 `css_class = "pii-highlight"` 分支 (commit caf33d1)
- [x] `tests/unit/test_word_preview_highlight.py` exists (commit 7181841, 4 TestClass + 8 tests)
- [x] `tests/unit/test_convergence.py` 含 `TestPiiWordAdapterConvergence` 类 (commit 7181841, 2 tests)
- [x] All 3 task commits present in git log (9f089b1, caf33d1, 7181841)
- [x] 128/128 baseline tests PASS (D-16 不变量; excluding 4 pre-existing path_validation failures)

**Self-Check: PASSED**

---

## Next Steps (downstream plans)

- **03-04-save-toolbar-packaging**: `MainWindow._save_word` 调 `apply_pii_replacements_to_docx` (D-04 真脱敏); toolbar `btn_mask_override` 扩展到 Word 路径; PyInstaller spec 同步加 `privacyguard.pii.word_adapter` hiddenimports (D-14)。
- **Phase 7 UX**: 候选审阅 UI 完整形态 (按实体类型/来源筛选 + 分页) — 当前 Plan 3 落地的最小可用高亮形态是 Phase 7 完整审阅 UI 的前置。
- **Phase 7 UX**: 替换后预览按来源筛选高亮 (rule / manual / ocr / pii) — CLAUDE.md 已标识。

---

## Artifacts Produced

| Path | Type | Lines | Notes |
|------|------|-------|-------|
| `main.py` | MOD | +35/-6 | merge function 扩展 + 双栏预览注入 + pii-highlight css_class |
| `tests/unit/test_word_preview_highlight.py` | NEW | 257 | 4 TestClass + 8 test methods + 2 helper functions |
| `tests/unit/test_convergence.py` | MOD | +38 | TestPiiWordAdapterConvergence 类 (2 tests) |

Total: 1 NEW test file, 2 MOD files. ~330 lines added (含 helpers + docstrings)。
