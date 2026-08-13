---
phase: 03-word
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - privacyguard/pii/word_adapter.py (NEW)
  - privacyguard/pii/__init__.py (MOD — _LAZY_IMPORTS + __all__)
  - tests/unit/test_word_pii_adapter.py (NEW)
  - tests/unit/test_package_imports.py (MOD — extend lazy-load assertions)
autonomous: true
requirements:
  - FMT-02
user_setup: []

estimate:
  tokens: 55000
  raw_tokens: 28000
  tasks: 3
  confidence: high

must_haves:
  truths:
    - 用户从 privacyguard.pii 顶层访问 collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx 三个函数, 不在 `import privacyguard` 时拉起 word_adapter 模块（OPS-03 懒加载纪律）
    - 三函数纯函数, 不 import python-docx（D-11: 保持 PII 引擎无 IO 原则）, 通过 test_convergence 反向 AST 验证
    - 同文本重复（PII hit.text 在同一段落出现 N 次）逐个展开为 N 个独立 (hit, char_offset)（D-09）
    - locate_pii_hits_in_paragraph 在 paragraph_text 中用 paragraph_text.find(needle, start_offset) 顺序扫描, 字符偏移与 paragraph.text 视图一致（D-08 + D-09）
    - apply_pii_replacements_to_docx 接受 Document 对象（不接 docx_path）+ hit_locations dict + mode 形参, partial 模式走 mask_for_entity, blackout 模式写 "[已脱敏]"（D-03 + D-06 + D-07）
    - 段级 paragraph.style.name 在 replace 之后不变（段级样式保留; D-07 不变量）
    - 跨 run 命中（run0="张" + run1="三"）replace 后 hit 文本整体消失, 段内不再含有原始子串
  artifacts:
    - privacyguard/pii/word_adapter.py — collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx 三函数（~120 LOC）
    - privacyguard/pii/__init__.py — _LAZY_IMPORTS 注册 3 行（lines 110+）+ __all__ 增 3 项
    - tests/unit/test_word_pii_adapter.py — 4 个 TestClass（TestCollectPiiWordHits / TestLocatePiiHitsInParagraph / TestApplyPiiReplacementsToDocx / TestWordAdapterImportability）, ~200 LOC
    - tests/unit/test_package_imports.py — 增 2 个测试方法（test_import_privacyguard_does_not_load_word_adapter / test_collect_pii_word_hits_loads_word_adapter）
  key_links:
    - privacyguard.pii.word_adapter.collect_pii_word_hits → privacyguard.pii.engine.PIIEngine.detect （D-11 复用 Phase 1/2 既有管线）
    - privacyguard.pii.word_adapter.apply_pii_replacements_to_docx → privacyguard.pii.mask.mask_for_entity （D-03 mask 分派沿用）
    - privacyguard.pii.__init__._LAZY_IMPORTS['collect_pii_word_hits'] → privacyguard.pii.word_adapter.collect_pii_word_hits （OPS-03 懒加载入口）
    - tests/unit/test_package_imports.py::test_import_privacyguard_does_not_load_word_adapter — 守住 OPS-03 懒加载纪律回归
---

# Phase 3 — Plan 1: word_adapter 三函数 + 懒加载注册 (Wave 1 Foundation)

<objective>
新建 privacyguard/pii/word_adapter.py, 提供 collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx 三函数（与 pdf_adapter 对称形态; D-11）; 在 privacyguard/pii/__init__.py 的 _LAZY_IMPORTS 注册三函数（D-13）; 新建 tests/unit/test_word_pii_adapter.py 三函数纯函数测试（D-15 #1）; 扩展 tests/unit/test_package_imports.py 守住 OPS-03 懒加载纪律（D-13 + Pitfall 8）。

Purpose: Wave 1 Foundation —— Phase 3 的所有下游计划（worker 接入 / merge 函数扩展 / 真脱敏写入）都依赖本计划产出的三函数。必须先就位才能进入 Wave 2 / Wave 3 / Wave 4。
Output: 三函数实现 + 懒加载入口 + 三函数纯函数测试 + 懒加载纪律回归测试。
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
@privacyguard/pii/__init__.py
@privacyguard/pii/hits.py
@privacyguard/pii/engine.py
@privacyguard/pii/pdf_adapter.py
@privacyguard/pii/mask.py
@privacyguard/pii/confidence.py
@tests/unit/test_package_imports.py
@tests/unit/test_pdf_pii_redaction.py
@tests/unit/test_convergence.py
</context>

<tasks>

<!-- ============================================================ -->
<!-- Task 1: RED — 三函数 stub + 测试先行 -->
<!-- ============================================================ -->

<task type="tdd" name="Task 1 (RED): 创建三函数纯函数测试 stub, 验证初始失败">
  <files>tests/unit/test_word_pii_adapter.py</files>
  <read_first>
    - privacyguard/pii/hits.py (PIIHit 字段锁 D-05)
    - privacyguard/pii/engine.py (PIIEngine.detect 范本)
    - privacyguard/pii/pdf_adapter.py (collect_pii_rects 对称形态)
    - privacyguard/pii/__init__.py (现有 _LAZY_IMPORTS 范本)
    - tests/unit/test_pdf_pii_redaction.py (reverse-extraction 范本)
    - tests/unit/test_word_replace_rules.py (Word 测试范本)
  </read_first>
  <behavior>
    - Test 1 (collect_pii_word_hits): 空文本返回空列表; 含 18 位身份证号文本返回 1 条 entity_type="CN_ID_CARD" 命中; 多段混合身份证+手机号+邮箱返回多条按 entity 顺序
    - Test 2 (locate_pii_hits_in_paragraph): 单一命中返回 (hit, offset=5) char_offset; 同文本重复 3 次展开为 3 个 (hit, offset) D-09; 空 hits 列表返回空; 空 paragraph_text 返回空
    - Test 3 (apply_pii_replacements_to_docx): 含身份证号的段落 replace 后再开 Document, 段落不再含原身份证号; partial 模式产物含 "********"; blackout 模式产物含 "[已脱敏]"; 段级 style.name 在 replace 前后不变 D-07; 跨 run 命中（run0="110101" + run1="199001011234"）replace 后段内不再含子串
    - Test 4 (importability): from privacyguard.pii import collect_pii_word_hits 触发 word_adapter 模块加载; privacyguard.pii.word_adapter 模块源码不含 "from docx" / "import docx" 子串
  </behavior>
  <action>
    新建 tests/unit/test_word_pii_adapter.py（按 PATTERNS.md §tests/unit/test_word_pii_adapter.py 范式）。4 个 TestClass:
    - TestCollectPiiWordHits: test_empty_text_returns_empty_list / test_detects_id_card_in_paragraph / test_detects_multiple_entity_types
    - TestLocatePiiHitsInParagraph: test_locate_single_hit_returns_offset / test_locate_duplicate_text_expands_all_occurrences（D-09）/ test_locate_empty_inputs_return_empty
    - TestApplyPiiReplacementsToDocx: test_redacted_paragraph_loses_original_secret / test_partial_mode_writes_mask_text / test_blackout_mode_writes_brackets / test_paragraph_style_preserved_after_replace（D-07）/ test_replace_across_runs_replaces_full_substring
    - TestWordAdapterImportability: test_collect_pii_word_hits_triggers_word_adapter_module_loaded / test_word_adapter_source_does_not_import_docx

    测试用纯函数: collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx 全部 from privacyguard.pii.word_adapter import（直接路径, 避免与后续 _LAZY_IMPORTS 顺序耦合）。PIIEngine 实例化一次作为 class fixture。

    暂不实现 word_adapter.py —— 此阶段仅写测试, 让测试因为 ImportError 失败（RED 阶段产物）。在 Task 2 (GREEN) 才落地实现。

    测试结构用 unittest.TestCase; 断言用 self.assertEqual / self.assertIn / self.assertNotIn / self.assertGreater。
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_pii_adapter -v 2>&1 | head -30; echo "--- expected: ImportError because word_adapter.py not yet created ---"</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_word_pii_adapter.py 文件存在; 4 个 TestClass 全部定义; 全部测试方法名符合 behavior 列表
    - 文件以 `import unittest` 开头; collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx 均 `from privacyguard.pii.word_adapter import` 直接路径
    - 运行 `python3 -m unittest tests.unit.test_word_pii_adapter -v` 触发 ImportError (ModuleNotFoundError: privacyguard.pii.word_adapter) —— RED 阶段产物, 预期失败
    - 文件不调用 `from docx import Document` 在测试方法外（仅在 TestApplyPiiReplacementsToDocx 内使用, 因为测试需要构造 Document 实例验证）
  </acceptance_criteria>
  <done>RED 测试就位, 4 个 TestClass + 至少 10 个测试方法覆盖 D-05/D-08/D-09/D-11 全部行为约束; 运行触发 ImportError 失败。</done>
</task>

<!-- ============================================================ -->
<!-- Task 2: GREEN — 三函数实现 -->
<!-- ============================================================ -->

<task type="auto" name="Task 2 (GREEN): 实现 word_adapter 三函数 + 懒加载注册">
  <files>privacyguard/pii/word_adapter.py, privacyguard/pii/__init__.py</files>
  <read_first>
    - tests/unit/test_word_pii_adapter.py (Task 1 刚写的 RED 测试 — 是实现契约)
    - privacyguard/pii/__init__.py (现有 _LAZY_IMPORTS 注册范本)
    - privacyguard/pii/hits.py (PIIHit dataclass)
    - privacyguard/pii/engine.py (PIIEngine.detect 范本, 130-211 行)
    - privacyguard/pii/mask.py (mask_for_entity 分派表)
    - privacyguard/pii/pdf_adapter.py (collect_pii_rects 范本, 50-64 行)
    - tests/unit/test_word_replace_rules.py (Word 测试 fixture)
    - tests/unit/test_pdf_pii_redaction.py (reverse-extraction 范本)
  </read_first>
  <action>
    新建 privacyguard/pii/word_adapter.py（按 PATTERNS.md §privacyguard/pii/word_adapter.py 范式）:
    - module docstring: 3 行说明三函数职责 + 1 行声明 "禁止在 adapter 内 import python-docx"
    - 三函数:
      1. `collect_pii_word_hits(paragraph_text: str, engine: PIIEngine) -> List[PIIHit]`: 空 / 全空白文本返回 []; 否则构造 TextUnit(page_index=0, text=paragraph_text, source="text") 调 engine.detect(unit); page 参数不传（D-10: 复用 source="text", 引擎内部 fallback 占位 rect, word_adapter 后续消费 hit.text 拿 char_offset）
      2. `locate_pii_hits_in_paragraph(hits: List[PIIHit], paragraph_text: str) -> List[Tuple[PIIHit, int]]`: 空 hits / 空 paragraph_text 返回 []; 按 (len(hit.text or ""), hit.text or "") 排序保证短优先; 每个 hit.text 用 paragraph_text.find(needle, search_from) 顺序扫描, 找到的 char_offset + 1 个 (hit, offset) 元组入列表, search_from 推进到 idx + len(needle); 找不到 break
      3. `apply_pii_replacements_to_docx(doc: "Document", hit_locations: Dict[str, List[Tuple[PIIHit, int]]], mode: Literal["partial", "blackout"] = "partial") -> None`: 遍历 doc.paragraphs + doc.tables 嵌套结构 yield (key, paragraph) 元组 (key 格式: paragraph_N / table_X_cell_Y_Z_p_N); 对每个 key 取 hits = hit_locations.get(key, []); 按 (start, end, replacement) 形态构造 matches 列表; 复用 main.py:965 replace_matches_in_paragraph 既有实现（直接 import `from main import replace_matches_in_paragraph` 是 v37.7.6 已接受的 one-way 跨层依赖, 测试 test_convergence 守 PII 包内不重复定义 — 不必 inline）
    - 文件顶部不 import `from docx import Document`; 只在 type hint 中写 "Document"（PEP 484 forward reference string）
    - 文件顶部 import: from typing import Dict, List, Literal, Tuple; from privacyguard.pii.hits import PIIHit; from privacyguard.pii.engine import PIIEngine（type hint 用, 不实例化）; 内部调 mask_for_entity 时本地 import `from privacyguard.pii.mask import mask_for_entity` 避免顶层拉起 mask 模块

    修改 privacyguard/pii/__init__.py:
    - 在 __all__ 列表末尾追加 3 行: 'collect_pii_word_hits' / 'locate_pii_hits_in_paragraph' / 'apply_pii_replacements_to_docx'
    - 在 _LAZY_IMPORTS 字典末尾追加 3 行 (按现有格式):
      ```
      'collect_pii_word_hits':          ('privacyguard.pii.word_adapter', 'collect_pii_word_hits'),
      'locate_pii_hits_in_paragraph':   ('privacyguard.pii.word_adapter', 'locate_pii_hits_in_paragraph'),
      'apply_pii_replacements_to_docx': ('privacyguard.pii.word_adapter', 'apply_pii_replacements_to_docx'),
      ```
    - 不改 __getattr__ / __dir__ —— 现有实现已通用支持任意 _LAZY_IMPORTS 条目
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v 2>&1 | tail -40</automated>
  </verify>
  <acceptance_criteria>
    - privacyguard/pii/word_adapter.py 文件存在; 三函数定义齐全 (collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx); type annotation 完整
    - 文件不含 `from docx` / `import docx` 子串 (grep -n -E '(from|import) docx' word_adapter.py 应当无输出)
    - privacyguard/pii/__init__.py 的 __all__ 包含 3 个新字符串; _LAZY_IMPORTS 包含 3 个新 key-value 对
    - 运行 `python3 -m unittest tests.unit.test_word_pii_adapter -v` 全部 PASS (GREEN 阶段产物)
    - 运行 `python3 -m unittest tests.unit.test_package_imports -v` 现有 4 测试仍 PASS (无回归; 还没扩测试)
    - `python3 -c "from privacyguard.pii import collect_pii_word_hits, locate_pii_hits_in_paragraph, apply_pii_replacements_to_docx; print('OK')"` 退出码 0 输出 OK
    - `python3 -c "import privacyguard; assert 'privacyguard.pii.word_adapter' not in __import__('sys').modules; print('OK')"` 退出码 0 输出 OK (懒加载纪律: import privacyguard 不拉起 word_adapter)
  </acceptance_criteria>
  <done>三函数实现就位 + 懒加载注册就位 + 测试全 GREEN (含 RED 测试)。</done>
</task>

<!-- ============================================================ -->
<!-- Task 3: 懒加载纪律回归测试 + 基线守护 -->
<!-- ============================================================ -->

<task type="auto" name="Task 3 (IMPROVE): 扩展 test_package_imports.py 守住 OPS-03 懒加载纪律 + 282 基线守护">
  <files>tests/unit/test_package_imports.py</files>
  <read_first>
    - tests/unit/test_package_imports.py (现有 _snapshot_privacyguard_modules / _restore_privacyguard_modules 范本)
    - privacyguard/pii/__init__.py (Task 2 修改后的 _LAZY_IMPORTS)
    - tests/unit/test_word_pii_adapter.py (Task 2 后 GREEN 的测试, 验证 word_adapter 已存在)
  </read_first>
  <action>
    在 tests/unit/test_package_imports.py 末尾追加 2 个测试方法（按 PATTERNS.md §tests/unit/test_package_imports.py 范式）:
    1. test_import_privacyguard_does_not_load_word_adapter: 沿用现有 test_import_privacyguard_does_not_load_pii_engine 形态; 调用 self._snapshot_privacyguard_modules(); 清空 sys.modules 中 privacyguard.*; import privacyguard; assert 'privacyguard.pii.word_adapter' not in sys.modules; finally self._restore_privacyguard_modules(cached)
    2. test_collect_pii_word_hits_loads_word_adapter: 沿用现有 test_pii_engine_loads_on_demand 形态; 调用 _ = module.collect_pii_word_hits; assert 'privacyguard.pii.word_adapter' in sys.modules

    守住 OPS-03 懒加载纪律 (D-13 + Pitfall 8)。

    同时运行完整 Phase 1/2/3 word 基线测试, 确保 282 既有测试全部通过（D-16 不变量）:
    - `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence tests.unit.test_pii_engine tests.unit.test_pii_validators tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_pii_pipeline -v` —— 应全部 PASS
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_package_imports tests.unit.test_convergence tests.unit.test_pii_engine tests.unit.test_pii_validators tests.unit.test_word_pii_adapter -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_package_imports.py 末尾追加 2 个新方法; 现有方法未删除
    - 运行 `python3 -m unittest tests.unit.test_package_imports -v` 现有 4 测试 + 新增 2 测试全部 PASS (6/6)
    - 运行 `python3 -m unittest tests.unit.test_convergence -v` 全部 PASS (Phase 3 暂不引入 main.py inline 检查, 等 Plan 3 才扩展)
    - 运行 `python3 -m unittest tests.unit.test_pii_engine tests.unit.test_pii_validators tests.unit.test_word_pii_adapter -v` 全部 PASS
    - 282 既有测试基线保持通过（D-16 不变量验证）
  </acceptance_criteria>
  <done>OPS-03 懒加载纪律回归测试就位; 三函数纯函数测试全部 GREEN; 282 既有测试基线保持通过。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| text → adapter | 段落文本由调用方传入, 含可能 PII; word_adapter 仅做检测 / 定位, 不持久化 |
| adapter → mask_for_entity | hit.normalized 经 mask_for_entity 分派表产出 mask 字符串; mask_for_entity 是 Phase 2 既有的纯函数, 信任其内部逻辑 |
| adapter → replace_matches_in_paragraph | main.py:965 既有实现; 跨层 one-way 依赖 (privacyguard → main) 是 v37.7.6 已接受模式 |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-03-01 | T (Tampering) | locate_pii_hits_in_paragraph char_offset 错位 | medium | mitigate | D-09 顺序展开 + paragraph_text.find() 与 paragraph.text 视图语义对齐 (Python-docx 文档保证); test_word_pii_adapter::test_replace_across_runs_replaces_full_substring 跨 run 验证 |
| T-03-02 | I (Information Disclosure) | word_adapter 不当 import python-docx 触发 eager import | high | mitigate | D-11 锁定禁止 import docx; Task 2 grep 验证; Task 3 守 test_package_imports 懒加载; Plan 3 才在 test_convergence 加 inline 检查 |
| T-03-03 | R (Repudiation) | 段级样式丢失 run 级格式 (粗体/斜体) 用户不可见 | low | accept | D-07 锁定: 段级样式保留 ≥ run 级格式丢失; 产物已写入 (真脱敏底线 > 格式完美); test_word_pii_adapter::test_paragraph_style_preserved_after_replace 守段级不变 |
| T-03-04 | E (Elevation of Privilege) | 批量入口误接入 PII 扫描 | medium | accept (deferred) | Plan 2 在 _ModularWordWorker.run() 单点扩展, 不触及 WordBatchReplaceWorker; D-12 锁定批量入口 skip; test_batch_word_replace 守回归 |
| T-03-SC | T (Tampering) | PyInstaller frozen 包 word_adapter ModuleNotFoundError | high | mitigate | D-14 锁定 hiddenimports; Plan 4 才显式在 PrivacyGuard_windows.spec / build_complete.sh 增 'privacyguard.pii.word_adapter'; 当前 Plan 1 用 test_package_imports 单元代理 |

## Per-Task Security Verification

| Task | Threat Ref | Automated Check |
|------|------------|-----------------|
| Task 1 | T-03-01 / T-03-02 | RED 测试就位 (失败) |
| Task 2 | T-03-01 / T-03-02 / T-03-03 | grep 验证 word_adapter.py 无 docx import; GREEN 测试 PASS |
| Task 3 | T-03-02 | test_package_imports 增 2 测试 PASS |
</threat_model>

<verification>
[总体 Phase 1 / 3 word PII adapter 验证]
- python3 -m unittest tests.unit.test_word_pii_adapter -v (Plan 1 范围: 4 TestClass 全 PASS)
- python3 -m unittest tests.unit.test_package_imports -v (Plan 1 范围: 6 测试全 PASS, 含新增 2 个)
- python3 -m unittest tests.unit.test_convergence -v (Plan 1 范围: 现有全部 PASS, 暂不扩展)
- python3 -m unittest tests.unit.test_pii_engine tests.unit.test_pii_validators -v (Phase 1/2 既有 PASS, 282 基线守护)
- 282 既有测试基线保持通过 (D-16 不变量)
</verification>

<success_criteria>
[Plan 1 完成判定]
1. privacyguard/pii/word_adapter.py 存在且三函数实现齐全 (D-11)
2. privacyguard/pii/__init__.py _LAZY_IMPORTS 注册 3 行 + __all__ 增 3 项 (D-13)
3. tests/unit/test_word_pii_adapter.py 4 TestClass + ≥10 测试方法全 PASS (D-15 #1)
4. tests/unit/test_package_imports.py 增 2 测试方法, 6/6 PASS (OPS-03 + Pitfall 8 守护)
5. 282 既有测试基线保持通过 (D-16)
6. word_adapter.py 文件不含 `from docx` / `import docx` 子串 (D-11 + T-03-02)
7. `import privacyguard` 不触发 word_adapter 模块加载 (OPS-03 懒加载)
8. 主动访问 collect_pii_word_hits 触发 word_adapter 加载 (OPS-03 主动)
</success_criteria>

<output>
Create .planning/phases/03-word/03-01-word-adapter-PLAN.md ✓ (this file)
后续执行产: .planning/phases/03-word/03-01-word-adapter-SUMMARY.md (在 Wave 1 完成后由 executor 写入)
</output>

## Artifacts this phase produces

- `privacyguard/pii/word_adapter.py` (NEW) — functions: `collect_pii_word_hits`, `locate_pii_hits_in_paragraph`, `apply_pii_replacements_to_docx`
- `privacyguard/pii/__init__.py` (MOD) — `_LAZY_IMPORTS` dict + `__all__` list: 3 new entries each
- `tests/unit/test_word_pii_adapter.py` (NEW) — classes: `TestCollectPiiWordHits`, `TestLocatePiiHitsInParagraph`, `TestApplyPiiReplacementsToDocx`, `TestWordAdapterImportability`
- `tests/unit/test_package_imports.py` (MOD) — methods: `test_import_privacyguard_does_not_load_word_adapter`, `test_collect_pii_word_hits_loads_word_adapter`
