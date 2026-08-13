---
phase: 03-word
plan: 03
type: execute
wave: 2
depends_on:
  - 03-02-worker-pii-integration
files_modified:
  - main.py (MOD — merge_word_matches_with_priority 扩展 pii_matches 形参 + _build_word_*_panel_updates 注入 + _save_word 不变)
  - tests/unit/test_word_preview_highlight.py (NEW)
  - tests/unit/test_convergence.py (MOD — 扩展 inline 守卫)
autonomous: true
requirements:
  - FMT-02
  - UX-01
  - UX-02
user_setup: []

estimate:
  tokens: 55000
  raw_tokens: 28000
  tasks: 3
  confidence: high

must_haves:
  truths:
    - merge_word_matches_with_priority 增加 pii_matches: Optional[List[PIIHit]] = None 形参; PII 命中并入 ocr ∪ pii 同层 (D-01); PII 在合并排序中按 confidence_tier + 来源加权胜出 (D-02)
    - PII 与 OCR 重叠时, PII 胜出 (校验位质量 > OCR 文本层) — D-02 锁定, 由 _append_candidates 先占先得 + 后追加 skip overlap 实现
    - PII 命中区间起止点若越界 (start<0 或 end>text_len 或 start>=end), _append_candidates 静默 drop, 不破坏 cp27 DOM patch 边界 (Pitfall 5 + D-17 不变量)
    - _build_word_original_panel_updates / _build_word_replaced_panel_updates 调 merge_word_matches_with_priority 时传入 pi_matches=word_data[key]["pii"], 双栏预览左/右栏 PII 命中渲染为 <mark class="pii-highlight"> + data-key/data-start/data-end + title 属性
    - main.py::_save_word 在 PII 接入前先在 _build_word_*_panel_updates 渲染端走通, _save_word 自身的 pii 接入推 Plan 4 (Wave 3) — 本 Plan 仅做渲染层, 不做真脱敏写入
    - main.py 不内联定义 collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx 三函数 (D-11 + test_convergence 守卫)
    - 282 既有测试 + Plan 1/2 新增测试保持通过 (D-16 + D-17)
  artifacts:
    - main.py:863 merge_word_matches_with_priority — 加 pii_matches=None 形参; _append_candidates 之后追加 _append_candidates([_pii_hit_to_match_dict(h) for h in pii_matches], "pii"); _pii_hit_to_match_dict helper 局部定义 (D-10: 复用 page_offset/page_length 字段存 char_offset/char_length)
    - main.py:11940 _build_word_original_panel_updates — ocr_matches=data.get("ocr", []) + pii_matches=data.get("pii", [])
    - main.py:11986 _build_word_replaced_panel_updates — 同样扩展
    - main.py:_build_word_original_preview_fragment (11954) — css_class 解析: 增 "pii-highlight" 分支 (source == "pii"); 复用现有 build_highlight_preview_segments; title 改 "[PII] {entity_type} · {confidence_tier}" 形态 (UI-SPEC §Copywriting Contract)
    - tests/unit/test_word_preview_highlight.py — TestMergeWithPii / TestPiiHighlightMarkup / TestMergePriorityPiiOverOCR / TestNoOverflowGuard 4 类
    - tests/unit/test_convergence.py — 增 TestPiiWordAdapterConvergence 类: test_main_py_does_not_inline_word_adapter_functions + test_pii_word_adapter_module_does_not_import_docx
  key_links:
    - merge_word_matches_with_priority(text, rules, default, manual=..., ocr=..., pii=...) → _append_candidates([pii_dict], "pii") → _range_overlaps 守 PII 胜出 (D-02)
    - _build_word_original_panel_updates → merge_word_matches_with_priority(..., pii_matches=word_data[key]["pii"]) → _build_word_original_preview_fragment → build_highlight_preview_segments → segments 渲染 pii-highlight mark
    - test_convergence → AST 扫描 main.py 源码: 不得含 "def collect_pii_word_hits(" / "def locate_pii_hits_in_paragraph(" / "def apply_pii_replacements_to_docx(" 三函数定义
---

# Phase 3 — Plan 3: merge_word_matches_with_priority 扩展 + 双栏预览 PII 高亮 (Wave 2 UX)

<objective>
扩展 main.py:863 merge_word_matches_with_priority 函数签名加 pii_matches 形参, PII 命中并入 ocr ∪ pii 同层 (D-01); PII 与 OCR 重叠时 PII 胜出 (D-02 由 _append_candidates 后追加先得实现); 扩展 _build_word_original_panel_updates / _build_word_replaced_panel_updates 注入 pii_matches=word_data[key]["pii"]; 扩展 _build_word_original_preview_fragment 增加 pii-highlight css_class 渲染 (UI-SPEC §Copywriting); 新建 tests/unit/test_word_preview_highlight.py 验证 cp27 DOM patch 边界 + PII/css_class 渲染 + 合并优先级 (D-15 #4); 扩展 tests/unit/test_convergence.py 守卫 main.py 不内联 word_adapter 三函数 (D-11 + T-03-02)。

Purpose: Wave 2 UX —— Word 双栏对比预览的左栏 (原文) / 右栏 (替换后) 同时高亮 PII 命中; 用户不需手输关键词即可看到敏感项; cp27 修复点 (DOM patch 边界) 不被破坏; main.py 不再 inline PII 适配器逻辑 (v37.7.6 收敛原则守护)。
Output: merge 函数扩展 + 双栏预览 PII 高亮渲染 + 4 类新单元测试 + main.py inline 守卫扩展。
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
@.planning/phases/03-word/03-01-word-adapter-PLAN.md (Plan 1 word_adapter 三函数定义)
@.planning/phases/03-word/03-02-worker-pii-integration-PLAN.md (Plan 2 worker PII 接入 + word_data 字段)
@main.py:863 merge_word_matches_with_priority (现有 4 源签名)
@main.py:11940 _build_word_original_panel_updates (左栏渲染入口)
@main.py:11954 _build_word_original_preview_fragment (mark className 解析)
@main.py:11986 _build_word_replaced_panel_updates (右栏渲染入口)
@privacyguard/pii/hits.py (PIIHit 字段锁 D-05)
@privacyguard/pii/__init__.py (懒加载入口)
@tests/unit/test_word_replace_rules.py (Word 测试范本)
@tests/unit/test_convergence.py (现有 inline 守卫范本)
</context>

<tasks>

<!-- ============================================================ -->
<!-- Task 1: merge_word_matches_with_priority 扩展 pii_matches 形参 -->
<!-- ============================================================ -->

<task type="modify" name="Task 1: main.py:863 merge_word_matches_with_priority 扩展 pii_matches 形参">
  <files>main.py</files></read_first>
    - main.py:863-906 (现有 merge_word_matches_with_priority 函数全文件)
    - .planning/phases/03-word/03-CONTEXT.md D-01/D-02/D-10 锁定
    - privacyguard/pii/hits.py (PIIHit 字段锁 D-05: page_offset/page_length 字段复用)
    - tests/unit/test_word_replace_rules.py::test_merge_priority_rule_manual_ocr (现有 4 源合并测试范本)
  </read_first>
  <action>
    修改 main.py:863 merge_word_matches_with_priority 函数:
    1. 函数签名加形参: `def merge_word_matches_with_priority(text, rules, default_replacement_text, manual_matches=None, ocr_matches=None, pii_matches=None):` (D-01 锁定)
    2. 函数 docstring 更新: `"""合并规则替换、手动脱敏、OCR 脱敏、PII 区间，优先级：规则 > 手动 > (OCR ∪ PII)，PII 校验位质量高于 OCR 文本层。"""`
    3. 函数体首段追加: `pii_matches = pii_matches or []  # [NEW D-01]`
    4. 在 `_append_candidates(ocr_matches, "ocr")` 之后 (现有 line 904), 追加:
       ```python
       # [NEW D-01/D-02] PII 命中并入"ocr ∪ pii"层; PII 后追加, 因 _append_candidates 去重
       # (后追加胜出), PII 校验位质量 > OCR 文本层 (D-02)
       # D-10: PIIHit.page_offset / page_length 字段在 Word 端复用作 char_offset / char_length
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
    5. 不动既有 _append_candidates / _range_overlaps / build_word_rule_matches 调用 —— D-02 通过 "PII 在 ocr 之后追加" 让 PII 占位优先 (cp27 修复点保留; Pitfall 5 不变量)

    不在本 Task 修改 _save_word / _build_word_*_panel_updates 调用面 (留 Task 2 集中改渲染入口)。

    锁定 D-10: PIIHit.page_offset / page_length 字段在 Word 端复用为 char_offset / char_length。WordAdapter 消费完后立即丢弃 PIIHit (word_data["pii"] 是 in-memory, 不持久化); 主程序其他路径 (PDF / OCR) 仍按原语义使用 (Phase 1 D-05 字段锁不变)。
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_replace_rules tests.unit.test_word_preview_highlight tests.unit.test_convergence -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - main.py:863 函数签名包含 pii_matches=None 形参 (grep -n 'def merge_word_matches_with_priority' main.py)
    - main.py:863 函数体内 _append_candidates(ocr_matches, "ocr") 之后出现 _append_candidates(pii_as_match_dicts, "pii") 调用 (grep -n 'pii_as_match_dicts' main.py)
    - 既有 test_word_replace_rules::test_merge_priority_rule_manual_ocr 仍 PASS (4 源合并向后兼容)
    - PII 后追加确保重叠区 PII 胜出 (D-02 验证见 Task 3 测试)
    - 越界 PII (start<0 或 end>text_len) 由 _append_candidates 静默 drop (Pitfall 5 验证见 Task 3 测试)
  </acceptance_criteria>
  <done>merge_word_matches_with_priority 扩展就位, PII 后追加实现 D-02; 既有 test_word_replace_rules 4 源合并测试保持 PASS。</done>
</task>

<!-- ============================================================ -->
<!-- Task 2: 双栏预览 PII 渲染接入 -->
<!-- ============================================================ -->

<task type="modify" name="Task 2: _build_word_*_panel_updates 注入 pii_matches + pii-highlight css_class 渲染">
  <files>main.py</files></read_first>
    - main.py:11940-11952 _build_word_original_panel_updates (左栏入口)
    - main.py:11986-11998 _build_word_replaced_panel_updates (右栏入口)
    - main.py:11954-11984 _build_word_original_preview_fragment (mark className 解析逻辑)
    - .planning/phases/03-word/03-UI-SPEC.md §Color + §Copywriting (pii-highlight css_class + title 属性契约)
    - .planning/phases/03-word/03-CONTEXT.md D-01 + D-15 锁定
    - Plan 1 word_adapter 三函数 (D-11 接入契约)
  </read_first>
  <action>
    修改 main.py:11940 _build_word_original_panel_updates:
    - merge_word_matches_with_priority 调用增形参 `pii_matches=data.get("pii", [])` (D-01 注入; word_data 默认含 pii 键, Plan 2 已确保)

    修改 main.py:11986 _build_word_replaced_panel_updates:
    - 同样增 `pii_matches=data.get("pii", [])` 形参 (D-01 注入)

    修改 main.py:11971 _build_word_original_preview_fragment 内 css_class 解析逻辑 (现有 line 11971-11979 范围):
    ```python
    source = str(segment.get("source", "manual"))
    if source == "manual":
        css_class = "manual-highlight"
    elif source == "pii":
        css_class = "pii-highlight"  # [NEW D-01 + UI-SPEC §Color]
    else:
        css_class = "ocr-highlight"
    title = ...
    if source == "pii":
        # [NEW UI-SPEC §Copywriting] PII 命中 hover tooltip
        entity_type = str(segment.get("rule_name", "PII")).strip() or "PII"
        title = f"[PII] {entity_type}"  # 简化形态; 完整形态由后续 Phase 7 扩展
    elif source == "manual":
        title = "手动脱敏"
    else:
        title = str(segment.get("rule_name", "")).strip() or "智能脱敏"
    ```

    _build_replaced_preview_fragment 不需新增 css_class 分支 (替换区段沿用现有 mask 文本渲染, PII partial_mask 已由 mask_for_entity 写入 replacement 字段)。

    不动 _add_data_key_attributes / _add_data_key_regex_fallback / build_word_panel_update_script / _apply_word_panel_updates —— cp27 修复点保留 (Pitfall 5 + D-17 不变量)。
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_preview_highlight tests.unit.test_word_replace_rules tests.unit.test_word_worker_pii tests.unit.test_word_pii_adapter tests.unit.test_package_imports tests.unit.test_convergence -v 2>&1 | tail -40</automated>
  </verify>
  <acceptance_criteria>
    - main.py:11940 _build_word_original_panel_updates 调 merge_word_matches_with_priority 时含 `pii_matches=data.get("pii", [])` (grep -n 'pii_matches=data' main.py)
    - main.py:11986 _build_word_replaced_panel_updates 同样扩展 (grep -n 'pii_matches=data' main.py, 期望 ≥2 行)
    - main.py:11971 范围 css_class 解析逻辑含 "pii-highlight" 分支 (grep -n 'pii-highlight' main.py)
    - 运行 `python3 -m unittest tests.unit.test_word_preview_highlight -v` 4 TestClass 全 PASS (Task 3 落地后)
    - 运行 `python3 -m unittest tests.unit.test_word_replace_rules tests.unit.test_word_worker_pii tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v` 全部 PASS (D-17 + Plan 1/2 基线守护)
    - cp27 DOM patch 边界不被破坏 (data-key/data-start/data-end 数值合法)
  </acceptance_criteria>
  <done>双栏预览 PII 渲染就位; css_class="pii-highlight" + title "[PII] {entity_type}" 契约满足; 既有测试基线保持通过。</done>
</task>

<!-- ============================================================ -->
<!-- Task 3: 双栏预览 PII 渲染 + DOM patch 测试 + main.py inline 守卫扩展 -->
<!-- ============================================================ -->

<task type="auto" name="Task 3: 新建 test_word_preview_highlight.py + 扩展 test_convergence.py 守卫">
  <files>tests/unit/test_word_preview_highlight.py, tests/unit/test_convergence.py</files></read_first>
    - main.py:863 merge_word_matches_with_priority (Task 1 改后的 5 源签名)
    - main.py:11940-11998 双栏预览 (Task 2 改后的 pii_matches 注入 + pii-highlight className)
    - privacyguard/pii/hits.py (PIIHit 构造参数: entity_type / page_offset / page_length / page_rect / confidence_tier / source / mask_strategy / normalized / validator_passed)
    - tests/unit/test_word_replace_rules.py::test_merge_priority_rule_manual_ocr (4 源合并测试范本)
    - tests/unit/test_convergence.py (现有 inline 守卫范本)
  </read_first>
  <action>
    新建 tests/unit/test_word_preview_highlight.py (按 PATTERNS.md §tests/unit/test_word_preview_highlight.py 范式):
    - 4 个 TestClass:
      1. TestMergeWithPii (3 测试): test_pii_added_to_merged_result / test_pii_wins_over_ocr_on_overlap (D-02) / test_pii_out_of_range_dropped_silently (Pitfall 5 + cp27)
      2. TestMergePriorityPiiOverOCR (2 测试): test_rule_wins_over_pii_on_overlap / test_manual_wins_over_pii_on_overlap (验证 D-01 优先级: rule > manual > ocr ∪ pii; PII 仅在同层与 OCR 竞争时胜出)
      3. TestPiiHighlightMarkup (2 测试): 通过 stub 调用 _build_word_original_panel_updates (沿用 test_word_replace_rules.build_word_preview_stub 形态, 增加 word_data[key]["pii"] = [PIIHit]); 断言 fragment 含 'class="pii-highlight"' + 'title="[PII] CN_ID_CARD"' (UI-SPEC 契约)
      4. TestNoOverflowGuard (1 测试): 构造 PIIHit with page_offset=-1 (越界); 调 merge_word_matches_with_priority; 断言 merged 是空列表 (静默 drop)

    扩展 tests/unit/test_convergence.py (按 PATTERNS.md §tests/unit/test_convergence.py 范式):
    - 追加 TestPiiWordAdapterConvergence 类 (Phase 3 D-11 守卫):
      1. test_main_py_does_not_inline_word_adapter_functions: read_text main.py; forbidden = ["def collect_pii_word_hits(", "def locate_pii_hits_in_paragraph(", "def apply_pii_replacements_to_docx("]; assertNotIn each
      2. test_pii_word_adapter_module_does_not_import_docx: read_text privacyguard/pii/word_adapter.py; assertNotIn "from docx", "import docx"; 守 D-11 + T-03-02

    完整基线守护:
    - python3 -m unittest tests.unit.test_word_preview_highlight tests.unit.test_convergence tests.unit.test_word_replace_rules tests.unit.test_word_worker_pii tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v (6 联合 PASS)
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_preview_highlight tests.unit.test_convergence -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_word_preview_highlight.py 文件存在; 4 TestClass + ≥8 测试方法全 PASS (D-15 #4)
    - 测试覆盖: PII 命中并入 merged / PII 胜 OCR / 越界 drop / rule/manual 仍胜 PII / pii-highlight className + title 渲染 / 越界 PII 静默 drop
    - tests/unit/test_convergence.py 增 TestPiiWordAdapterConvergence 类, 2 测试方法 (test_main_py_does_not_inline_word_adapter_functions / test_pii_word_adapter_module_does_not_import_docx) 全 PASS
    - 运行 `python3 -m unittest tests.unit.test_word_preview_highlight tests.unit.test_convergence -v` 全部 PASS
    - 运行 `python3 -m unittest tests.unit.test_word_replace_rules tests.unit.test_word_worker_pii tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v` 全部 PASS (D-17 + Plan 1/2 基线)
    - 282 既有测试基线保持通过 (D-16)
  </acceptance_criteria>
  <done>双栏预览 PII 渲染测试 + main.py inline 守卫扩展就位; 8 测试全 PASS; 既有测试基线保持通过。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PIIHit (Phase 1 dataclass) → merge function | PIIHit.page_offset/page_length 字段在 Word 端复用作 char_offset/char_length (D-10); 主程序其他路径不受影响 |
| merge function → _append_candidates | _range_overlaps 守重叠区胜出规则 (rule > manual > pii > ocr); 越界静默 drop (cp27 修复点保留) |
| _build_word_*_panel_updates → HTML fragment | pii-highlight css_class + title 属性契约 (UI-SPEC §Color + §Copywriting); cp27 DOM patch 边界保留 |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-03-09 | T (Tampering) | PII 越界 char_offset 破坏 cp27 DOM patch mark data-start/data-end | high | mitigate | _append_candidates 既有 start<0/end>text_len 验证 (line 880-881); Task 3 TestNoOverflowGuard 守回归 |
| T-03-10 | I (Information Disclosure) | main.py inline PII 适配器逻辑, 绕过 _LAZY_IMPORTS 懒加载 + 重复实现回潮 (v37.7.6 收敛破坏) | medium | mitigate | D-11 锁定 + Task 3 test_convergence 增 AST 守卫 (test_main_py_does_not_inline_word_adapter_functions / test_pii_word_adapter_module_does_not_import_docx) |
| T-03-11 | S (Spoofing) | PII 命中颜色 / 视觉混乱, 用户无法分辨自动识别 vs 手动 vs OCR | low | mitigate | UI-SPEC §Color 锁定 #D64545/#FF6B6B; css_class="pii-highlight" 与 ocr-highlight/manual-highlight 三色区分 |
| T-03-12 | R (Repudiation) | PII 命中右栏 mask 文字未渲染, 用户看不到实际产物 | low | accept | mask_for_entity 在 merge function 内调用, mask 文字写入 replacement 字段; 右栏 build_replaced_preview_segments 沿用现有渲染; Task 3 TestPiiHighlightMarkup 验证左栏 markup, 右栏通过现有 test_word_replace_rules::test_replaced_preview_segments_merge_sources 间接验证 |

## Per-Task Security Verification

| Task | Threat Ref | Automated Check |
|------|------------|-----------------|
| Task 1 | T-03-09 | merge_word_matches_with_priority 扩展后, 既有 test_word_replace_rules 仍 PASS (向后兼容) |
| Task 2 | T-03-11 | grep 验证 pii-highlight className 注入 |
| Task 3 | T-03-09 / T-03-10 | test_word_preview_highlight 8 测试 PASS + test_convergence 增 2 守卫 PASS |
</threat_model>

<verification>
[总体 Plan 3 验证]
- python3 -m unittest tests.unit.test_word_preview_highlight -v (Plan 3 范围: 4 TestClass, ≥8 测试全 PASS)
- python3 -m unittest tests.unit.test_convergence -v (现有 + Plan 3 新增 2 守卫全 PASS)
- python3 -m unittest tests.unit.test_word_replace_rules tests.unit.test_word_worker_pii tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v (D-17 + Plan 1/2 基线)
- 282 既有测试基线保持通过 (D-16)
</verification>

<success_criteria>
[Plan 3 完成判定]
1. merge_word_matches_with_priority 加 pii_matches 形参 (D-01); PII 后追加实现 D-02; 越界 drop 守 cp27 (Pitfall 5)
2. _build_word_original_panel_updates / _build_word_replaced_panel_updates 注入 pii_matches=word_data[key]["pii"] (D-01)
3. _build_word_original_preview_fragment css_class 增 "pii-highlight" 分支 + title "[PII] {entity_type}" (UI-SPEC 契约)
4. tests/unit/test_word_preview_highlight.py 4 TestClass + ≥8 测试全 PASS (D-15 #4)
5. tests/unit/test_convergence.py 增 TestPiiWordAdapterConvergence 类, 2 测试方法 PASS (D-11 + T-03-02)
6. 282 既有测试 + Plan 1/2 新增测试保持通过 (D-16 + D-17)
7. cp27 DOM patch 边界不被破坏 (data-key/data-start/data-end 数值合法; TestNoOverflowGuard 验证)
</success_criteria>

<output>
后续执行产: .planning/phases/03-word/03-03-merge-and-preview-PLAN.md ✓ (this file) + .planning/phases/03-word/03-03-merge-and-preview-SUMMARY.md (在 Wave 2 完成后由 executor 写入)
</output>

## Artifacts this phase produces

- `main.py` (MOD) — `merge_word_matches_with_priority`: adds `pii_matches=None` parameter; after `_append_candidates(ocr_matches, "ocr")`, appends `_append_candidates(pii_as_match_dicts, "pii")` (D-02 PII wins on overlap via later append)
- `main.py` (MOD) — `_build_word_original_panel_updates` (line 11940): adds `pii_matches=data.get("pii", [])` kwarg
- `main.py` (MOD) — `_build_word_replaced_panel_updates` (line 11986): adds `pii_matches=data.get("pii", [])` kwarg
- `main.py` (MOD) — `_build_word_original_preview_fragment` (line 11954): adds `pii-highlight` css_class branch + `title="[PII] {entity_type}"` for source=="pii"
- `tests/unit/test_word_preview_highlight.py` (NEW) — classes `TestMergeWithPii`, `TestMergePriorityPiiOverOCR`, `TestPiiHighlightMarkup`, `TestNoOverflowGuard` with ≥8 test methods
- `tests/unit/test_convergence.py` (MOD) — adds class `TestPiiWordAdapterConvergence` with 2 test methods enforcing D-11 + T-03-02
