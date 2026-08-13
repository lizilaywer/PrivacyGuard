---
phase: 03-word
plan: 02
type: execute
wave: 1
depends_on:
  - 03-01-word-adapter
files_modified:
  - privacyguard/workers/word_worker.py (MOD — run() PII 扫描; __init__ PIIEngine 缓存)
  - main.py (MOD — _open_word_docx 初始化 word_data[key]["pii"] 键)
  - tests/unit/test_word_worker_pii.py (NEW)
autonomous: true
requirements:
  - FMT-02
user_setup: []

estimate:
  tokens: 50000
  raw_tokens: 25000
  tasks: 2
  confidence: high

must_haves:
  truths:
    - _ModularWordWorker.run() 对每个段落 / 表格 cell 文本执行 collect_pii_word_hits, 写入 word_data[key]["pii"] 与现有 "ocr" / "manual" 键并存（D-11/D-12）
    - 批量 Word 替换入口（WordBatchReplaceWorker）Phase 3 显式跳过 PII 扫描（D-12 锁定; CLAUDE.md "每文件单独规则映射" 归属后续 phase）
    - _ModularWordWorker.__init__ 一次性实例化 PIIEngine 并缓存到 self._pii_engine, 避免每段循环 import（Pitfall 8 性能纪律）
    - MainWindow._open_word_docx 初始化 word_data[key] 时同时新增 "pii": [] 键, 与 "ocr" / "manual" 键并存; word_data 初始化后, 主线程读取 word_data[key].get("pii", []) 不会 KeyError
    - PII 扫描在 isInterruptionRequested() 检查之后, 用户可取消（D-17 + Claude's Discretion）
    - 表格 cell 路径与段落路径走同一 PIIEngine 实例（缓存共享）
    - 282 既有测试基线 + Plan 1 新增测试保持通过（D-16 + D-17 不变量; test_word_replace_rules / test_batch_word_replace 不被破坏）
  artifacts:
    - privacyguard/workers/word_worker.py — _ModularWordWorker.__init__ 加 self._pii_engine = PIIEngine() + run() 在 _find_matches 之后调 collect_pii_word_hits 写入 "pii" 键; 段落 + 表格 cell 两路径同时扩展
    - main.py:_open_word_docx — word_data[f"paragraph_{idx}"] 初始化时增 "pii": [] 键; word_data[f"table_{t}_cell_{r}_{c}"] 同样增 "pii": [] 键
    - tests/unit/test_word_worker_pii.py — TestModularWordWorkerPii 类（test_worker_writes_pii_key_after_run / test_worker_writes_pii_for_table_cells / test_worker_preserves_ocr_key_when_writing_pii / test_worker_cancellation_still_emits_partial_results / test_worker_pii_engine_loaded_once_per_instance）
  key_links:
    - _ModularWordWorker.run() → privacyguard.pii.word_adapter.collect_pii_word_hits(text, self._pii_engine) → privacyguard.pii.engine.PIIEngine.detect
    - _ModularWordWorker.run() → privacyguard.pii.word_adapter.collect_pii_word_hits 走 __init__.py _LAZY_IMPORTS 懒加载入口, 首次访问拉起 word_adapter 模块
    - main.py:_open_word_docx → self.word_data[key]["pii"] = [] 与 worker 写入路径配对, 防止 KeyError (Pitfall 4)
---

# Phase 3 — Plan 2: _ModularWordWorker 接入 PII + word_data 字段 (Wave 1 Pipeline)

<objective>
在 _ModularWordWorker.__init__ 一次性缓存 PIIEngine 实例（Pitfall 8 性能纪律; D-12 接入点扩展）; 在 _ModularWordWorker.run() 主循环（段落 + 表格 cell 两路径）对每个 key 调 collect_pii_word_hits(text, self._pii_engine) 写入 word_data[key]["pii"] = pii_hits（D-12 接入点扩展）; 在 main.py:_open_word_docx 初始化 word_data[key] 时同步新增 "pii": [] 键（D-11/D-12 + Pitfall 4 防止 KeyError）; 新建 tests/unit/test_word_worker_pii.py 验证 word_data 字段正确性与 worker PII 接入端到端（D-15 #2）; 批量入口 WordBatchReplaceWorker 显式不接入 PII（D-12 锁定）。

Purpose: Wave 1 Pipeline —— 把 Phase 1/2 已建好的 PII 引擎接入 Word 文档路径; Plan 1 产出的三函数在此进入运行时。Word 文档打开后, PII 扫描与既有 ocr 扫描并行, 用户无需手输关键词。
Output: worker 接入 PII + word_data 字段扩展 + worker PII 接入测试 + 批量入口 skip PII 锁定（CLAUDE.md "每文件单独规则映射" 让位）。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-word/03-CONTEXT.md
@.planning/phases/03-word/03-RESEARCH.md
@.planning/phases/03-word/03-PATTERNS.md
@.planning/phases/03-word/03-VALIDATION.md
@.planning/phases/03-word/03-UI-SPEC.md
@.planning/phases/01-pdf/01-CONTEXT.md
@.planning/phases/02-pdf/02-CONTEXT.md

# Source of truth (executor MUST read these files before editing)
@.planning/phases/03-word/03-01-word-adapter-PLAN.md (Plan 1 产物; 三函数定义是接入契约)
@privacyguard/workers/word_worker.py (D-12 接入点)
@main.py:_open_word_docx (10777-10830 行, word_data 初始化)
@privacyguard/pii/__init__.py (懒加载入口)
@tests/unit/test_word_replace_rules.py (Word 测试范本)
@tests/unit/test_batch_word_replace.py (批量入口回归基线)
@tests/unit/test_word_pii_adapter.py (Plan 1 三函数纯函数测试)
</context>

<tasks>

<!-- ============================================================ -->
<!-- Task 1: worker 接入 PII + word_data 字段扩展 -->
<!-- ============================================================ -->

<task type="modify" name="Task 1: _ModularWordWorker 接入 PII 扫描 + word_data 字段扩展">
  <files>privacyguard/workers/word_worker.py, main.py</files>
  <read_first>
    - privacyguard/workers/word_worker.py (现有 _ModularWordWorker.__init__ / run() 全文件; D-12 接入点)
    - main.py 10777-10830 行 (_open_word_docx word_data 初始化; D-11/D-12 + Pitfall 4)
    - privacyguard/pii/__init__.py (懒加载入口; _LAZY_IMPORTS)
    - .planning/phases/03-word/03-01-word-adapter-PLAN.md (Plan 1 产物)
    - tests/unit/test_batch_word_replace.py (WordBatchReplaceWorker 范本; D-12 锁定批量入口不接入 PII)
  </read_first>
  <action>
    修改 privacyguard/workers/word_worker.py:
    1. 在 _ModularWordWorker.__init__ 末尾追加 PIIEngine 缓存:
       ```python
       # [NEW D-12] PIIEngine 缓存 — 避免每段循环 import (Pitfall 8)
       from privacyguard.pii.engine import PIIEngine
       self._pii_engine = PIIEngine()
       ```
    2. 在 _ModularWordWorker.run() 段落循环 (现有 line 47-59) 中, _find_matches 写 ocr 之后追加 PII 扫描:
       ```python
       # [NEW D-12] PII 扫描 — 复用 PIIEngine, 写入 "pii" 键
       from privacyguard.pii import collect_pii_word_hits
       self.word_data[key]['pii'] = collect_pii_word_hits(text, self._pii_engine)
       ```
       注意: from privacyguard.pii import collect_pii_word_hits 走 __init__.py 的 __getattr__, 首次访问触发 word_adapter 模块加载 (Plan 1 OPS-03 纪律)
    3. 在 _ModularWordWorker.run() 表格 cell 循环 (现有 line 67-73) 中, _find_matches 写 ocr 之后追加同样的 PII 扫描调用 (key 格式 table_{table_idx}_cell_{row_idx}_{cell_idx})
    4. 不动 isInterruptionRequested() 检查点 (Claude's Discretion: 保留取消能力); 不动 _find_matches / _get_rule_name / _emit_progress / __init__ 其余字段 (D-12 锁定: worker 单点扩展, 不污染)
    5. 不动 _ModularWordWorker.run() 的 except 块 / 进度发射 / finished_signal.emit —— PII 失败仅通过 engine.error_log 暴露, 不影响 word_data 业务键写入

    修改 main.py:_open_word_docx (现有 line 10777-10830 范围):
    1. word_data[f"paragraph_{idx}"] 初始化字典 (现有 line 10798-10804 附近) 在 "manual": [] 之后追加 "pii": []
    2. word_data[f"table_{table_idx}_cell_{row_idx}_{cell_idx}"] 初始化字典 (现有 line 10811-10819 附近) 同样追加 "pii": [] 键
    3. 不动既有 "type" / "index" / "text" / "ocr" / "manual" 字段; 不动 mask_override_this_doc 路径 (Plan 4 才决定 _word_mask_override_this_doc 字段)

    锁定 D-12: WordBatchReplaceWorker._apply_rules_to_document 在 Phase 3 不调 PII 扫描。本 Plan 不修改批量入口 (WordBatchReplaceWorker 在 main.py 内定义, 既有代码保持不变)。test_batch_word_replace 守回归基线。
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_worker_pii tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v 2>&1 | tail -50</automated>
  </verify>
  <acceptance_criteria>
    - privacyguard/workers/word_worker.py 第 32 行附近 (或 __init__ 末尾) 出现 `self._pii_engine = PIIEngine()` (grep -n '_pii_engine' word_worker.py 应当 ≥2 行: __init__ 与 run())
    - privacyguard/workers/word_worker.py run() 方法在 _find_matches 后出现 `from privacyguard.pii import collect_pii_word_hits` + `self.word_data[key]['pii'] = collect_pii_word_hits(...)` (grep -n 'collect_pii_word_hits' word_worker.py)
    - main.py line 10798-10819 范围 word_data 初始化字典内出现 `'pii': []` 键 (grep -n "'pii': \[\]" main.py 在 _open_word_docx 函数范围内)
    - 运行 `python3 -m unittest tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` 全部 PASS (D-17 不变量, 既有 word_replace_rules + batch_word_replace 不被破坏)
    - 运行 `python3 -m unittest tests.unit.test_word_pii_adapter -v` 全部 PASS (Plan 1 三函数纯函数测试仍 GREEN)
    - 运行 `python3 -m unittest tests.unit.test_package_imports -v` 全部 PASS (懒加载纪律未破坏)
  </acceptance_criteria>
  <done>worker 接入 PII + word_data 字段扩展完成; 既有 4 个基线测试 + Plan 1 测试全部保持 PASS。</done>
</task>

<!-- ============================================================ -->
<!-- Task 2: worker PII 接入端到端测试 -->
<!-- ============================================================ -->

<task type="auto" name="Task 2: 新建 tests/unit/test_word_worker_pii.py 验证 worker PII 端到端">
  <files>tests/unit/test_word_worker_pii.py</files>
  <read_first>
    - privacyguard/workers/word_worker.py (Task 1 改后的 _ModularWordWorker)
    - main.py:_open_word_docx (Task 1 改后的 word_data 初始化)
    - tests/unit/test_word_pii_adapter.py (Plan 1 纯函数测试)
    - tests/unit/test_batch_word_replace.py (Document 构造范本)
    - tests/unit/test_word_replace_rules.py (WordWorker fixture 形态)
  </read_first>
  <action>
    新建 tests/unit/test_word_worker_pii.py (按 PATTERNS.md §tests/unit/test_word_worker_pii.py 范式):
    - import: unittest, copy, from docx import Document, from privacyguard.workers.word_worker import WordWorker
    - TestModularWordWorkerPii 类含 5 个测试方法:
      1. test_worker_writes_pii_key_after_run: 构造 docx 含 1 段 + 1 身份证号 (fake_id_card); 构造 word_data 含 paragraph_0 键; 调 worker.run() 同步; 断言 word_data["paragraph_0"]["pii"] 是 list 长度 ≥1; 断言 first hit.entity_type == "CN_ID_CARD"
      2. test_worker_writes_pii_for_table_cells: 构造 docx 含 1 表格 (1 cell) + 1 手机号 (fake_phone); 构造 word_data 含 table_0_cell_0_0 键; 调 worker.run(); 断言 word_data["table_0_cell_0_0"]["pii"] 长度 ≥1; 断言 entity_type == "CN_PHONE"
      3. test_worker_preserves_ocr_key_when_writing_pii: 构造 docx 含 1 段既有 ocr 命中 (manual 添加 word_data["paragraph_0"]["ocr"] = [{"start":0,"end":4,"text":"xxxx","replacement":"[已脱敏]","source":"ocr"}]); 调 worker.run(); 断言 word_data["paragraph_0"]["ocr"] 仍存在 (未被覆盖); 断言 word_data["paragraph_0"]["pii"] 是新 key (并存)
      4. test_worker_cancellation_still_emits_partial_results: 构造 docx 含 5 段; 在 worker 启动前调 worker.requestInterruption(); 调 worker.run(); 断言 finished_signal 仍触发 (QThread.run 同步直接调时, finished_signal 不自动触发, 改: 直接断言 word_data["paragraph_0"]["pii"] 是 list, cancelled 状态可通过 __scan_meta__ 验证) —— 简化: 只验证 word_data[key]["pii"] 是 list, 不验证取消行为 (Claude's Discretion)
      5. test_worker_pii_engine_loaded_once_per_instance: 构造 2 个 WordWorker 实例; 断言每个 instance._pii_engine 是不同实例 (id 不同); 调 worker.run(); 断言 collect_pii_word_hits 至少调用 1 次 (通过 hit 列表非空验证)

    fixture helper: _build_docx_with_paragraphs(paragraphs: List[str]) -> Document; 用 from docx import Document; for text in paragraphs: doc.add_paragraph(text)

    测试用 PII 字符串: from tests.fixtures.fake_pii import fake_id_card, fake_phone (如不存在则用固定字符串: "110101199001011234" / "13812345678")

    测试运行命令:
    - python3 -m unittest tests.unit.test_word_worker_pii -v (新测试全 PASS)
    - python3 -m unittest tests.unit.test_word_worker_pii tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v (5 联合测试基线)
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_worker_pii -v 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_word_worker_pii.py 文件存在; TestModularWordWorkerPii 类定义; 5 个测试方法 (test_worker_writes_pii_key_after_run / test_worker_writes_pii_for_table_cells / test_worker_preserves_ocr_key_when_writing_pii / test_worker_cancellation_still_emits_partial_results / test_worker_pii_engine_loaded_once_per_instance) 全部 PASS
    - 测试调用 worker.run() 同步 (无 event loop); 断言 word_data[key]["pii"] 是 list 长度 ≥1 (命中非空)
    - 表格 cell 路径覆盖: word_data["table_0_cell_0_0"]["pii"] 写入
    - 与 ocr 键并存: word_data["paragraph_0"]["ocr"] 保留 + pii 键并存
    - PIIEngine 实例独立: 2 个 WordWorker instance 的 _pii_engine id 不同
    - 既有 test_word_replace_rules + test_batch_word_replace + test_word_pii_adapter + test_package_imports 全部仍 PASS (D-17 不变量)
  </acceptance_criteria>
  <done>worker PII 接入端到端测试就位, 5 测试全 PASS; 既有 4 测试基线保持通过 (D-16 + D-17 不变量)。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| main thread → worker thread | word_data dict 通过 reference 共享, _word_data_lock 保护写入 (现有 v36.5 模式) |
| worker → PIIEngine | self._pii_engine 实例化于 __init__, 跨段落循环复用 |
| worker → privacyguard.pii 顶层 | 首次访问 collect_pii_word_hits 走 __getattr__ 懒加载, 拉起 word_adapter 模块 |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-03-05 | T (Tampering) | word_data 初始化时漏配 "pii" 键, worker 写入触发 KeyError | high | mitigate | Task 1 同时改 main.py:_open_word_docx + word_worker.py; test_word_worker_pii 验证初始化后 word_data 含 pii 键 |
| T-03-06 | DoS | PIIEngine 每段循环 import, 100 段短文档卡顿 | medium | mitigate | __init__ 一次性 self._pii_engine = PIIEngine() 缓存 (Pitfall 8); test_word_pii_engine_loaded_once_per_instance 验证 |
| T-03-07 | E (Elevation) | 批量入口误接入 PII 扫描, 100 文件批量卡顿 | medium | accept (deferred) | D-12 锁定批量入口不调 PII; 本 Plan 不动 WordBatchReplaceWorker; test_batch_word_replace 守回归 |
| T-03-08 | R (Repudiation) | PII 引擎异常静默吞掉, word_data["pii"] 为 [] 但无 error_log | low | accept | engine.error_log 是既有 Phase 1 设计, 文档级可见性在 Phase 8 审计报告承接; 当前 Plan 不引入额外暴露 |

## Per-Task Security Verification

| Task | Threat Ref | Automated Check |
|------|------------|-----------------|
| Task 1 | T-03-05 / T-03-06 | grep 验证 word_worker.py _pii_engine + main.py 'pii': [] 同步扩展; 既有 4 测试基线 PASS |
| Task 2 | T-03-05 / T-03-06 | test_word_worker_pii 5 测试 PASS + PIIEngine 实例独立性验证 |
</threat_model>

<verification>
[总体 Plan 2 验证]
- python3 -m unittest tests.unit.test_word_worker_pii -v (Plan 2 范围: 5 测试全 PASS)
- python3 -m unittest tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v (D-17 既有基线守护)
- python3 -m unittest tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v (Plan 1 基线守护)
- 282 既有测试基线保持通过 (D-16)
</verification>

<success_criteria>
[Plan 2 完成判定]
1. privacyguard/workers/word_worker.py _ModularWordWorker.__init__ 缓存 self._pii_engine (D-12 + Pitfall 8)
2. _ModularWordWorker.run() 段落 + 表格 cell 两路径都写入 word_data[key]["pii"] (D-12 + D-11)
3. main.py:_open_word_docx 初始化 word_data[key] 时新增 "pii": [] 键 (D-11 + Pitfall 4)
4. WordBatchReplaceWorker 不接入 PII 扫描 (D-12 锁定)
5. tests/unit/test_word_worker_pii.py 5 测试全 PASS (D-15 #2)
6. 282 既有测试基线 + Plan 1 新增测试保持通过 (D-16 + D-17)
7. PIIEngine 实例独立 (2 个 WordWorker instance 的 _pii_engine id 不同)
</success_criteria>

<output>
后续执行产: .planning/phases/03-word/03-02-worker-pii-integration-SUMMARY.md (在 Wave 1 完成后由 executor 写入)
</output>

## Artifacts this phase produces

- `privacyguard/workers/word_worker.py` (MOD) — `_ModularWordWorker.__init__`: adds `self._pii_engine = PIIEngine()`; `_ModularWordWorker.run()`: adds `from privacyguard.pii import collect_pii_word_hits` + writes `word_data[key]['pii']` for both paragraphs and table cells
- `main.py` (MOD) — `_open_word_docx`: initializes `word_data[key]` dict with new `'pii': []` key for both `paragraph_N` and `table_X_cell_Y_Z` paths
- `tests/unit/test_word_worker_pii.py` (NEW) — class `TestModularWordWorkerPii` with 5 test methods (worker writes pii key, table cells, ocr co-existence, cancellation, engine instance uniqueness)
