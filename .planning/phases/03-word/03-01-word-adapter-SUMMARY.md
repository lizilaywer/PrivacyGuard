# Phase 3 Plan 01: word_adapter 三函数 + 懒加载注册 Summary

**One-liner**: 新建 `privacyguard/pii/word_adapter.py` 三函数 (collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx), 在 `privacyguard.pii._LAZY_IMPORTS` 注册三函数, 守住 OPS-03 懒加载纪律; 22 + 2 = 24 个新测试全 PASS, 296/296 既有+新增基线 (D-16) 全部通过.

---

## Overview

| Aspect | Value |
| --- | --- |
| Phase | 03-word (Word 文档接入识别引擎) |
| Plan | 03-01-word-adapter (Wave 1 Foundation) |
| Type | execute (autonomous) |
| Tasks | 3/3 (1 RED + 1 GREEN + 1 IMPROVE) |
| Duration | ~13 min (13:39 → 13:52 UTC) |
| Commits | 3 (b0210ba RED tests, 8f5eea4 GREEN impl, f9d83f2 IMPROVE lazy-load regression) |
| Test baseline | 296/296 pass (D-16 不变量; 排除 4 个 pre-existing path_validation 失败) |
| Files created | `privacyguard/pii/word_adapter.py` (NEW), `tests/unit/test_word_pii_adapter.py` (NEW) |
| Files modified | `privacyguard/pii/__init__.py` (3 lazy entries + 3 __all__ items), `tests/unit/test_package_imports.py` (2 regression tests) |
| Requirements covered | FMT-02 |
| Decisions enforced | D-11 (无 docx import), D-13 (懒加载注册), OPS-03 (懒加载纪律), D-05 (PIIHit 字段锁), D-08 (char_offset 视图对齐), D-09 (同文本重复展开), D-07 (段级样式保留) |

---

## Tasks Executed

### Task 1 (RED) — commit `b0210ba`

**Files**: `tests/unit/test_word_pii_adapter.py` (NEW, 456 lines)

- 4 TestClass: `TestCollectPiiWordHits` / `TestLocatePiiHitsInParagraph` /
  `TestApplyPiiReplacementsToDocx` / `TestWordAdapterImportability`
- 12 个 test method 覆盖 D-05 (PIIHit 字段锁), D-08 (paragraph_text.find 顺序扫描),
  D-09 (同文本重复 3 次展开), D-11 (禁用 docx top-level), D-13 (懒加载), D-07
  (段级 style 保留 + 跨 run 命中)
- 阶段产物: `python -m unittest tests.unit.test_word_pii_adapter` 触发
  `ModuleNotFoundError: No module named 'privacyguard.pii.word_adapter'` (RED 预期失败)

### Task 2 (GREEN) — commit `8f5eea4`

**Files**: `privacyguard/pii/word_adapter.py` (NEW), `privacyguard/pii/__init__.py` (MOD), `tests/unit/test_word_pii_adapter.py` (MOD)

`privacyguard/pii/word_adapter.py` (~280 LOC) — 三函数 + helpers:
- `collect_pii_word_hits(paragraph_text, engine) -> List[PIIHit]`: 复用 PIIEngine.detect,
  空/全空白文本返回 `[]`, 构造 `TextUnit(page_index=0, text=..., source='text')` 调 `engine.detect(unit)`.
- `locate_pii_hits_in_paragraph(hits, paragraph_text) -> List[Tuple[PIIHit, int]]`:
  按 (len, normalized) 短优先排序, `paragraph_text.find(needle, search_from)` 顺序扫描,
  同一 needle 多次出现逐个展开 (D-09); 找不到 break.
- `apply_pii_replacements_to_docx(doc, hit_locations, mode='partial'|'blackout')`:
  - `_walk_paragraphs` 遍历 `doc.paragraphs` + 嵌套 `doc.tables`, key 格式
    `paragraph_N` / `table_X_row_Y_cell_Z_p_N`.
  - 局部 inline `_replace_matches_in_paragraph_local` + `_apply_range_to_runs_local`
    (避免 `from main import replace_matches_in_paragraph` 跨层依赖; 与 v37.7.6
    收敛原则一致).
  - partial mode: `mask_for_entity(hit.entity_type, hit.normalized)` → `"110101********1234"`.
  - blackout mode: 写 `"[已脱敏]"` 占位.
  - 段级 `paragraph.style.name` 在 replace 前后不变 (D-07); run 级格式可丢失
    (D-07 安全优先).
- **不 import python-docx**: 调用方持有 Document 句柄传入, Document 仅作 duck-typed
  attrs; type hint 字符串 forward ref (PEP 484).

`privacyguard/pii/__init__.py`:
- `_LAZY_IMPORTS` 新增 3 条:
  ```python
  'collect_pii_word_hits':          ('privacyguard.pii.word_adapter', 'collect_pii_word_hits'),
  'locate_pii_hits_in_paragraph':   ('privacyguard.pii.word_adapter', 'locate_pii_hits_in_paragraph'),
  'apply_pii_replacements_to_docx': ('privacyguard.pii.word_adapter', 'apply_pii_replacements_to_docx'),
  ```
- `__all__` 末尾追加 3 个公开导出 (D-13 公开 API).

`tests/unit/test_word_pii_adapter.py` (refactored):
- 22 个 test method 全 PASS (含 reverse-extraction disk round-trip + AST 验证
  word_adapter.py 无 `from docx` / `import docx`).

### Task 3 (IMPROVE) — commit `f9d83f2`

**Files**: `tests/unit/test_package_imports.py` (MOD)

- 沿用 Phase 1/2 `_snapshot_privacyguard_modules` / `_restore_privacyguard_modules` 范本.
- 新增 2 个 test method (D-13 + OPS-03 守护):
  - `test_import_privacyguard_does_not_load_word_adapter`: 验证 `import privacyguard`
    不拉起 `privacyguard.pii.word_adapter`.
  - `test_collect_pii_word_hits_loads_word_adapter`: 验证 `privacyguard.pii.collect_pii_word_hits`
    触发 word_adapter 模块加载 (D-13 _LAZY_IMPORTS).

---

## Deviations from Plan

### Plan-Locked Decisions Honored

- **D-11 (无 docx import)**: 严格遵守; word_adapter.py AST 扫描无 `from docx` /
  `import docx`. 测试用 AST 扫描而非字符串匹配, 排除 docstring 误触发.
- **D-13 (懒加载注册)**: 三函数经 `privacyguard.pii._LAZY_IMPORTS` 注册,
  `__all__` 同步追加 3 项.
- **D-05 (PIIHit 字段锁)**: 未扩展 PIIHit 字段; adapter 仅消费 `hit.normalized`
  (字面匹配段内文本), 写入 `hit_locations[key] = [(hit, char_offset)]`.
- **D-08 (char_offset 视图对齐)**: `paragraph_text.find(needle, search_from)`
  与 python-docx `Paragraph.text` 视图语义一致.
- **D-09 (同文本重复展开)**: 单 hit 多次出现逐个 yield `(hit, offset)` 元组,
  偏移严格递增.
- **D-07 (段级样式保留)**: `_replace_matches_in_paragraph_local` 仅修改 run.text,
  保留 paragraph.style; run 级格式丢失可接受.
- **OPS-03 (懒加载纪律)**: `import privacyguard` 不拉起 word_adapter;
  `test_collect_pii_word_hits_loads_word_adapter` 守回归.

### Auto-fixed Issues (within Task 2)

**1. [Rule 1 - 字段访问 bug] `hit.text` 不存在, 应使用 `hit.normalized`**
- **Found during**: Task 2 GREEN, 22 个 test method 中 10 个抛 `AttributeError: 'PIIHit' object has no attribute 'text'`
- **Issue**: 计划引用 `hit.text` (D-08 描述), 但 D-05 PIIHit 字段锁规定没有 `.text`
  字段 — 实际可用的是 `.normalized` (字面匹配段内文本, 与 phase 1 PDF 路径
  `hit.normalized in txt` 一致).
- **Fix**: word_adapter.py 改用 `getattr(hit, "normalized", "") or ""` 作为 needle
  源; 测试 `_make_hit` helper 同步注入 `normalized` 字段.
- **Files modified**: `privacyguard/pii/word_adapter.py` (locate + apply 路径),
  `tests/unit/test_word_pii_adapter.py` (所有 `_make_hit` factory)
- **Commit**: 8f5eea4 (与 GREEN 同步; 测试修复视为 TDD IMPROVE)

**2. [Rule 1 - test 期望偏移错误] `test_locate_three_duplicate_text_returns_three`**
- **Found during**: Task 2 GREEN, 最后一个失败 test
- **Issue**: 测试原文 `"X 110101Y 110101Z 110101W"` 的 `Y/Z/W` 单字符不是 needle
  的一部分, 实际偏移应为 [2, 10, 18] 而非 [2, 9, 16].
- **Fix**: 改为确定偏移构造 `"aa" + needle + "bb" + needle + "cc" + needle + "dd"`
  → 期望 offsets [2, 10, 18] (匹配 paragraph_text.find 实际行为).
- **Files modified**: `tests/unit/test_word_pii_adapter.py`
- **Commit**: 8f5eea4 (同 GREEN)

**3. [Rule 1 - 字符串匹配误判] `test_word_adapter_source_does_not_import_docx`**
- **Found during**: Task 2 GREEN, docstring 包含 "python-docx" 触发 `import docx` 子串匹配
- **Issue**: 子串匹配在 docstring / 注释中提及 "python-docx" 时误报.
- **Fix**: 改用 AST 扫描: `ast.parse` 后遍历 `tree.body`, 仅匹配 `ast.Import` /
  `ast.ImportFrom` 节点 (排除 docstring / comments).
- **Files modified**: `tests/unit/test_word_pii_adapter.py`
- **Commit**: 8f5eea4 (同 GREEN)

### Auto-fixed Issues (within Task 2 - 第二轮)

**4. [Rule 3 - __init__.py 误编辑] 第二次 Edit 误删 `_LAZY_IMPORTS = {` 行**
- **Found during**: Task 2 GREEN, 首次 Edit 之后运行测试触发
  `IndentationError: unexpected indent` on line 71
- **Issue**: `Edit` 工具的 `old_string` 模式在多匹配场景下未充分锚定,
  删除了 `_LAZY_IMPORTS = {` 这一行.
- **Fix**: 第三次 Edit 显式补回 `_LAZY_IMPORTS = {` 行 + 第一个 entry.
- **Files modified**: `privacyguard/pii/__init__.py`
- **Commit**: 8f5eea4 (同 GREEN)

---

## Auth Gates

None — no authentication required for this plan.

---

## Stub Tracking

None — all 3 functions are production-quality pure-function implementations.

---

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| (none) | — | Plan-implemented surfaces are in trusted PII module path; new word_adapter.py maintains D-11 (no docx import) and OPS-03 (lazy-load) invariants verified by automated tests. |

---

## Verification

### 1. RED phase verification (Task 1)
- `python -m unittest tests.unit.test_word_pii_adapter` → `ModuleNotFoundError: No module named 'privacyguard.pii.word_adapter'` ✓ (RED expected)

### 2. GREEN phase verification (Task 2)
- `python -m unittest tests.unit.test_word_pii_adapter` → 22/22 PASS ✓
- `python -m unittest tests.unit.test_package_imports` → 8/8 PASS (无回归) ✓
- `python -c "from privacyguard.pii import collect_pii_word_hits, locate_pii_hits_in_paragraph, apply_pii_replacements_to_docx; print('OK')"` → OK ✓
- `python -c "import privacyguard; assert 'privacyguard.pii.word_adapter' not in __import__('sys').modules; print('OK')"` → OK ✓ (OPS-03 懒加载)

### 3. IMPROVE phase verification (Task 3)
- `python -m unittest tests.unit.test_package_imports` → 10/10 PASS (8 原有 + 2 新) ✓
- `python -m unittest tests.unit.test_convergence` → 19/19 PASS (无回归) ✓
- 完整 Phase 1/2/3 word baseline: `python -m unittest tests.unit.test_mixed_pdf_ocr tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence tests.unit.test_pii_engine tests.unit.test_pii_validators tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_pii_pipeline tests.unit.test_word_pii_adapter` → **296/296 PASS** ✓ (D-16 不变量)
- 4 pre-existing `tests.test_path_validation` 失败与本计划无关 (回归测试可见,
  stash 本计划改动后仍然失败)

### 4. D-11 docx import discipline verification
- `python -c "import ast; tree = ast.parse(open('privacyguard/pii/word_adapter.py').read()); bad = [n.lineno for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)) and (n.module == 'docx' or (isinstance(n, ast.Import) and any(a.name == 'docx' or a.name.startswith('docx.') for a in n.names)))]; assert not bad, bad; print('OK')"` → OK ✓ (AST 扫描无 docx import)

### 5. D-13 lazy-load discipline verification
- `python -c "import sys; [sys.modules.pop(n, None) for n in list(sys.modules) if n.startswith('privacyguard')]; import privacyguard; assert 'privacyguard.pii.word_adapter' not in sys.modules; import privacyguard.pii; _ = privacyguard.pii.collect_pii_word_hits; assert 'privacyguard.pii.word_adapter' in sys.modules; print('OK')"` → OK ✓

---

## Self-Check

- [x] `privacyguard/pii/word_adapter.py` exists (created in commit 8f5eea4)
- [x] `tests/unit/test_word_pii_adapter.py` exists (created in commit b0210ba, modified 8f5eea4)
- [x] `privacyguard/pii/__init__.py` contains 3 new `_LAZY_IMPORTS` entries (commit 8f5eea4)
- [x] `privacyguard/pii/__init__.py` contains 3 new `__all__` entries (commit 8f5eea4)
- [x] `tests/unit/test_package_imports.py` contains 2 new test methods (commit f9d83f2)
- [x] All 3 task commits present in git log (b0210ba, 8f5eea4, f9d83f2)
- [x] 296/296 baseline tests PASS (D-16)

**Self-Check: PASSED**

---

## Next Steps (downstream plans)

- **03-02-word-worker**: `_ModularWordWorker.run()` 内 D-12 接入 PII 检测,
  `word_data[key]["pii"]` 写入, 复用 `collect_pii_word_hits`.
- **03-03-merge-preview**: `main.py:863 merge_word_matches_with_priority` 扩展
  `pii_matches` 形参; `merge_word_matches_with_priority(..., pii_matches=...)`
  在 `ocr ∪ pii` 层内 PII 优先 (D-02); DOM patch 走 `data-key` 局部更新 (cp27 修复点).
- **03-04-save-toolbar-packaging**: `MainWindow._save_word` 调
  `apply_pii_replacements_to_docx` (D-04 真脱敏); toolbar `btn_mask_override`
  扩展到 Word 路径; PyInstaller spec 同步加 `privacyguard.pii.word_adapter`
  hiddenimports (D-14).

---

## Artifacts Produced

| Path | Type | Lines | Notes |
|------|------|-------|-------|
| `privacyguard/pii/word_adapter.py` | NEW | ~280 | 3 functions + 5 helpers |
| `tests/unit/test_word_pii_adapter.py` | NEW | ~390 | 22 test methods, 4 TestClass |
| `privacyguard/pii/__init__.py` | MOD | +6 lines | 3 _LAZY_IMPORTS + 3 __all__ |
| `tests/unit/test_package_imports.py` | MOD | +40 lines | 2 regression tests |

Total: 1 NEW module, 1 NEW test file, 2 MOD files. ~716 lines added.
