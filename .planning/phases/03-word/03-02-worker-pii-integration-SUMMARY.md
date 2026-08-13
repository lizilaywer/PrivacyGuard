# Phase 3 Plan 02: _ModularWordWorker 接入 PII + word_data 字段扩展 Summary

**One-liner**: `_ModularWordWorker.__init__` 缓存 PIIEngine 实例; `run()` 段落 + 表格 cell 两路径写入 `word_data[key]['pii']`; `main.py:_open_word_docx` 初始化字典新增 `'pii': []` 键; 5 个 worker PII 端到端测试 + 既有 66 baseline 全部 PASS, 总计 301/301 通过 (D-17 + D-16 不变量).

---

## Overview

| Aspect | Value |
| --- | --- |
| Phase | 03-word (Word 文档接入识别引擎) |
| Plan | 03-02-worker-pii-integration (Wave 1 Pipeline) |
| Type | execute (autonomous) |
| Tasks | 2/2 |
| Duration | ~10 min (21:53 → 22:02 UTC+8) |
| Commits | 2 (3e75ffe feat, 01615ad test) |
| Test baseline | 301/301 pass (66 既有 + 5 新增 + 230 既有 Phase 1/2 单元) (D-16 不变量) |
| Files created | `tests/unit/test_word_worker_pii.py` (NEW, 181 lines) |
| Files modified | `privacyguard/workers/word_worker.py` (+9/-2), `main.py` (+4/-2) |
| Requirements covered | FMT-02 |
| Decisions enforced | D-12 (worker 接入 PII), D-11 (字段并存), D-15 #2 (worker PII 端到端测试), D-16 (基线守护), D-17 (word_replace_rules/batch_word_replace 不破坏) |

---

## Tasks Executed

### Task 1 (feat) — commit `3e75ffe`

**Files**: `privacyguard/workers/word_worker.py` (MOD), `main.py` (MOD)

`privacyguard/workers/word_worker.py` (3 处编辑):

1. `__init__` 末尾追加 PIIEngine 缓存 (Pitfall 8 性能纪律):
   ```python
   # [NEW D-12] PIIEngine 缓存 — 避免每段循环 import (Pitfall 8 性能纪律)
   from privacyguard.pii.engine import PIIEngine
   self._pii_engine = PIIEngine()
   ```
   实例化在 `__init__` 一次性完成, 跨段落 / 表格 cell 循环复用同一引擎.

2. `run()` 段落循环 (line 50-65) 在 `_find_matches` 写 `ocr` 之后追加:
   ```python
   # [NEW D-12] PII 扫描 — 复用 PIIEngine, 写入 "pii" 键
   from privacyguard.pii import collect_pii_word_hits
   self.word_data[key]['pii'] = collect_pii_word_hits(text, self._pii_engine)
   ```
   `from privacyguard.pii import collect_pii_word_hits` 走 `__init__.py:__getattr__`,
   首次访问触发 `privacyguard.pii.word_adapter` 模块加载 (Plan 1 OPS-03 纪律).

3. `run()` 表格 cell 循环 (line 67-86) 同样追加 (同一 `self._pii_engine` 实例共享).

不动 `isInterruptionRequested()` 检查点 (Claude's Discretion: 保留取消能力);
不动 `_find_matches` / `_emit_progress` / 既有字段 (D-12 锁定 worker 单点扩展).

`main.py:_open_word_docx` (line 10795-10821) word_data 初始化字典:

- `paragraph_N` 初始化字典在 `'manual': []` 之后追加 `'pii': []`
- `table_X_cell_Y_Z` 初始化字典同样追加 `'pii': []` (Pitfall 4 防 KeyError)

不动 `mask_override_this_doc` 路径 (Plan 4 才决定); 不动既有 `'type'/'index'/'text'/'ocr'/'manual'` 字段.

**锁定 D-12**: `WordBatchReplaceWorker` 在 Phase 3 不接入 PII 扫描, 既有代码保持不变.

### Task 2 (test) — commit `01615ad`

**Files**: `tests/unit/test_word_worker_pii.py` (NEW, 181 lines, 5 tests)

`TestModularWordWorkerPii` 类:

1. `test_worker_writes_pii_key_after_run`: 段落含身份证号 → 验证
   `word_data['paragraph_0']['pii']` 命中 `CN_ID_CARD`.
2. `test_worker_writes_pii_for_table_cells`: 表格 cell 含手机号 → 验证
   `word_data['table_0_cell_0_0']['pii']` 命中 `CN_PHONE`.
3. `test_worker_preserves_ocr_key_when_writing_pii`: run() 后 `ocr` 与 `pii`
   两键并存 (类型互不干扰, `id()` 不同).
4. `test_worker_cancellation_still_emits_partial_results`: 取消场景下已扫描
   key 的 `pii` 键类型仍为 `list`, 不抛 KeyError.
5. `test_worker_pii_engine_loaded_once_per_instance`: 2 个 WordWorker 实例的
   `_pii_engine` id 不同 (Pitfall 8 实例独立性), 且每个实例 run() 后命中非空.

辅助函数: `_build_docx_with_paragraphs`, `_build_docx_with_table_and_paragraphs`,
`_build_word_data_from_doc` (按 worker 期望 key 格式构造 word_data, 与
`main.py:_open_word_docx` 对齐).

测试用 PII 字符串: `tests.fixtures.fake_pii.fake_id_card()` /
`fake_phone()` (OPS-05 严禁真实数据).

---

## Deviations from Plan

### Plan-Locked Decisions Honored

- **D-12 (worker 接入 PII)**: `__init__` 缓存 PIIEngine + `run()` 两路径写 pii.
- **D-11 (字段并存)**: `'pii'` 与 `'ocr'/'manual'` 键并存, 不替换.
- **D-15 #2 (worker PII 端到端测试)**: 5 个测试方法全 PASS.
- **D-16 (基线守护)**: 既有 66 baseline + Phase 1/2 共 301 测试全部保持通过.
- **D-17 (word_replace_rules/batch_word_replace 不破坏)**: 两个测试文件 PASS.
- **Pitfall 4 (防 KeyError)**: `main.py` 初始化字典先于 worker 写入路径.
- **Pitfall 8 (PIIEngine 缓存)**: `__init__` 一次性实例化 + `self._pii_engine` 缓存.
- **OPS-03 (懒加载纪律)**: `from privacyguard.pii import collect_pii_word_hits`
  走 `__getattr__` 懒加载, 不污染 `import privacyguard` 入口.

### Auto-fixed Issues (within Task 2)

**1. [Rule 1 - 测试断言错误] test_worker_preserves_ocr_key_when_writing_pii 期望错误**
- **Found during**: Task 2 RED→GREEN, 首次运行 4/5 PASS, 1 FAIL
- **Issue**: 测试断言 `word_data['paragraph_0']['ocr']` 在 run() 后保留预填的
  1 个 hit, 但 `_find_matches()` 既有行为是**总是覆盖** `ocr` 键 (v36.5 行为,
  本计划不动). 预填 ocr 必然被覆盖为空 list.
- **Fix**: 改测试断言为 "run() 后 `ocr` 与 `pii` 两键并存 (类型 list, id 不同)";
  不再假设预填 ocr 被保留 (那是既有 v36.5 行为, 不在本计划变更范围).
- **Files modified**: `tests/unit/test_word_worker_pii.py`
- **Commit**: 01615ad (与 test 同 commit; 视为 TDD IMPROVE)

---

## Auth Gates

None — no authentication required for this plan.

---

## Stub Tracking

None — `self._pii_engine = PIIEngine()` 与 `collect_pii_word_hits` 调用均为
生产级真实实现, 无 placeholder / TODO / 空值兜底.

---

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| (none) | — | Plan-implemented surfaces are in trusted worker thread path; new `_pii_engine` cached instance + `word_data[key]['pii']` writes inherit existing v36.5 cancellation + thread-safe data-sharing semantics; T-03-05 (KeyError), T-03-06 (per-segment import), T-03-07 (batch entry false-positive) all mitigated per threat_model. |

---

## Verification

### 1. Acceptance criteria verification

- `grep -n '_pii_engine' privacyguard/workers/word_worker.py`:
  ```
  35:        self._pii_engine = PIIEngine()
  61:                    self.word_data[key]['pii'] = collect_pii_word_hits(text, self._pii_engine)
  82:                                self.word_data[key]['pii'] = collect_pii_word_hits(text, self._pii_engine)
  ```
  ≥ 3 行命中 (D-12 + Pitfall 8) ✓
- `grep -n "'pii': \[\]" main.py`:
  ```
  10751:        self.page_data = {i: {'ocr': [], 'manual': [], 'pii': []} for i in range(total)}
  10804:                    'pii': [],
  10820:                            'pii': [],
  ```
  `_open_word_docx` 函数范围内 2 处命中 (paragraph_N + table_X_cell_Y_Z) ✓
- `python -m unittest tests.unit.test_word_worker_pii -v` → 5/5 PASS ✓
- `python -m unittest tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` → 32 + 2 = 34 PASS (D-17) ✓
- `python -m unittest tests.unit.test_word_pii_adapter -v` → 22/22 PASS (Plan 1 不破坏) ✓
- `python -m unittest tests.unit.test_package_imports -v` → 10/10 PASS (懒加载纪律) ✓

### 2. D-16 baseline verification

```
python -m unittest tests.unit.test_mixed_pdf_ocr \
  tests.unit.test_ocr_api tests.unit.test_package_imports \
  tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config \
  tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace \
  tests.unit.test_config_alignment tests.unit.test_fstring_safety \
  tests.unit.test_convergence tests.unit.test_pii_engine \
  tests.unit.test_pii_validators tests.unit.test_pdf_pii_redaction \
  tests.unit.test_pdf_pii_pipeline tests.unit.test_word_pii_adapter \
  tests.unit.test_word_worker_pii
```
→ **301/301 PASS** ✓ (排除 4 个 pre-existing `tests.test_path_validation` 失败, 已知与本计划无关)

### 3. OPS-03 lazy-load discipline verification

- `from privacyguard.pii import collect_pii_word_hits` 走 `__getattr__`,
  首次访问触发 `privacyguard.pii.word_adapter` 模块加载, `import privacyguard`
  不拉起 word_adapter (Plan 1 OPS-03 纪律继承).

### 4. Smoke test (worker end-to-end)

```python
from docx import Document
from privacyguard.workers.word_worker import WordWorker
from tests.fixtures.fake_pii import fake_id_card

doc = Document()
doc.add_paragraph(f'测试段落 {fake_id_card()} 内容')
table = doc.add_table(rows=1, cols=1)
table.cell(0, 0).text = 'cell'

word_data = {...}  # paragraph_0 + table_0_cell_0_0
worker = WordWorker(doc, word_data, [], '', '[已脱敏]')
worker.run()
# → word_data['paragraph_0']['pii'] = [PIIHit(CN_ID_CARD, ...)]
# → word_data['table_0_cell_0_0']['pii'] = []
```
✓ PII 命中正确写入.

---

## Self-Check

- [x] `privacyguard/workers/word_worker.py` modified (commit 3e75ffe) — `_pii_engine` cache + PII writes
- [x] `main.py` modified (commit 3e75ffe) — `'pii': []` key in both paragraph + table_cell paths
- [x] `tests/unit/test_word_worker_pii.py` exists (commit 01615ad) — 5 tests, all PASS
- [x] Both task commits present in git log (3e75ffe feat, 01615ad test)
- [x] 301/301 baseline tests PASS (D-16 不变量; excluding 4 pre-existing path_validation failures)
- [x] `WordBatchReplaceWorker` 不接入 PII (D-12 锁定, 既有代码保持不变)

**Self-Check: PASSED**

---

## Next Steps (downstream plans)

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
| `privacyguard/workers/word_worker.py` | MOD | +9/-2 | `_pii_engine` cache + PII writes (段落 + 表格 cell) |
| `main.py` | MOD | +4/-2 | `'pii': []` key in both paragraph + table_cell paths |
| `tests/unit/test_word_worker_pii.py` | NEW | 181 | 5 test methods, 1 TestClass |

Total: 1 NEW test file, 2 MOD files. ~194 lines added.
