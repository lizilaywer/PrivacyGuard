---
phase: 03-word
plan: G1
type: execute
wave: 1
depends_on: []
files_modified:
  - main.py (MOD — _open_word_docx 启动 WordWorker / _has_word_replacement_candidates 增加 pii / _build_word_replaced_preview_html 注入 pii_matches)
  - tests/unit/test_word_pii_redaction.py (MOD — 增 3 个 PII 自动启动 + 双栏 compare mode + PII full reload 测试)
autonomous: true
gap_closure: true
requirements:
  - FMT-02
user_setup: []

estimate:
  tokens: 35000
  raw_tokens: 18000
  tasks: 3
  confidence: high

must_haves:
  truths:
    - 打开 .docx 文件后无需手动点击扫描, PII 扫描自动启动 (对应 VERIFICATION Gap 1: WordWorker not started on _open_word_docx)
    - 仅含 PII 命中（无 rules/manual/ocr）的 Word 文档能自动进入对比预览模式 (对应 VERIFICATION Gap 2: _has_word_replacement_candidates excludes pii)
    - 全量重载右栏 HTML 路径 (full reload) 包含 PII 命中掩码, 不只在增量 DOM patch 路径含 PII (对应 VERIFICATION Gap 3: _build_word_replaced_preview_html doesn't pass pii_matches)
  artifacts:
    - main.py:_open_word_docx — 在 word_data 初始化之后自动调用 self.start_ocr() (per Gap 1)
    - main.py:_has_word_replacement_candidates — 在 data.get("manual") or data.get("ocr") 之后追加 or data.get("pii") (per Gap 2)
    - main.py:_build_word_replaced_preview_html — line 10411-10417 在 ocr_matches 之后追加 pii_matches=self.word_data[key].get("pii", []) (per Gap 3)
    - tests/unit/test_word_pii_redaction.py — 增 3 个 TestClass (TestAutoPiiScanOnOpen / TestPiiOnlyDocumentEntersCompareMode / TestPiiFullReloadPreviewContainsMask)
  key_links:
    - _open_word_docx → start_ocr → _ModularWordWorker.run (Gap 1 fix 复用 Phase 1 既有路径)
    - _has_word_replacement_candidates → word_data[key]['pii'] (Gap 2; 与 existing ocr/manual 同形态)
    - _build_word_replaced_preview_html → merge_word_matches_with_priority(..., pii_matches=...) (Gap 3; 镜像 Plan 03-03 Task 2 增量 path 的注入方式)
    - main.py:11410-11419 start_ocr 既有路径 (Gap 1 fix 的代码样板; 不重写, 仅调用)

# Gap Closure Plan G1: WordWorker 自动启动 + compare-mode 包含 PII + full reload PII pass-through

<objective>
关闭 VERIFICATION.md 暴露的三个 hard gaps: (Gap 1) 打开 .docx 后必须自动启动 WordWorker 扫描 PII, 不再需要用户手动点击扫描按钮; (Gap 2) _has_word_replacement_candidates 必须把 PII 命中纳入对比模式触发条件, 否则仅含 PII 的文档不会进入双栏预览; (Gap 3) _build_word_replaced_preview_html 的全量重载路径 (line 10411-10417) 必须注入 pii_matches 参数, 否则右栏 full reload 后 PII 掩码丢失。本计划一次性闭合三处 main.py 表层编辑 + 三类行为测试, 恢复 Phase 3 的端到端 PII 双栏高亮链路。

Purpose: Phase 3 的核心承诺 "打开 Word 文档即自动列出 PII" 在 VERIFICATION 中被判定为 FAIL。三处编辑均为最小表层 main.py 改动, 不引入新模块、不破坏 336 既有测试基线 (D-16 不变量)。
Output: 三处 main.py 修改 + 三类新增行为测试 + 既有 336 测试基线保持通过。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-word/03-VERIFICATION.md
@.planning/phases/03-word/03-CONTEXT.md
@.planning/phases/03-word/03-01-word-adapter-SUMMARY.md
@.planning/phases/03-word/03-02-worker-pii-integration-SUMMARY.md
@.planning/phases/03-word/03-03-merge-and-preview-SUMMARY.md
@.planning/phases/03-word/03-04-save-and-packaging-SUMMARY.md

# Source of truth (executor MUST read these files before editing)
@main.py (lines 10300-10314, 10400-10420, 10795-10855, 11410-11419)
@privacyguard/workers/word_worker.py
@tests/unit/test_word_pii_redaction.py
</context>

<tasks>

<!-- ============================================================ -->
<!-- Task 1: Gap 1 — _open_word_docx 自动启动 WordWorker 扫描 PII -->
<!-- ============================================================ -->

<task type="auto" name="Task 1 (Gap 1): _open_word_docx 自动启动 WordWorker PII 扫描">
  <files>main.py</files>
  <read_first>
    - main.py:10795-10855 — _open_word_docx 既有 word_data 初始化路径 (含 'pii': [] 键, Phase 3 Plan 02 已落地)
    - main.py:11410-11419 — start_ocr() 既有实现 (Phase 1 既有的 OCR 启动路径, 启动 OCRWorker + WordWorker; 这是 Gap 1 fix 的样板)
    - main.py:10798-10815 — _open_word_docx 头部清理逻辑 (file_path / doc_type / word_doc 句柄初始化顺序, 用于确定 start_ocr() 调用插入点)
    - privacyguard/workers/word_worker.py — _ModularWordWorker.run() 既有 PII 扫描路径 (Phase 3 Plan 02 已落地 D-12)
  </read_first>
  <action>
    修改 main.py:_open_word_docx (line 10797-10855), 在 word_data 字典初始化完成 (line 10843 之后, 当前 plan 中已存在的 'pii': [] 键写入点) 之后、_reset_batch_session_state 等收尾调用之前, 自动启动 WordWorker PII 扫描。

    具体插入位置: 在 line 10843 之后 (self.word_data[key] = {'pii': [], ...} 收尾), line 10845 (扫描进度初始化) 之前; 同时在 try-except 的 try 子句末尾 (line 10855 之前) 增加 fallback 处理, 当 start_ocr 抛异常时不阻塞 UI 打开。

    实现方案 (最小改动, 不引入新线程管理):
    ```python
    # Phase 3 (G1 Gap 1): 打开 .docx 后自动启动 WordWorker PII 扫描, 无需用户手动点击扫描按钮
    # VERIFICATION.md Gap 1: WordWorker not started on _open_word_docx
    # 复用 Phase 1 既有 start_ocr() 路径, 该路径已正确启动 OCRWorker + WordWorker (含 Plan 02 落地的 D-12 PII 扫描)
    try:
        if hasattr(self, "start_ocr"):
            self.start_ocr()
    except Exception as _gap1_exc:
        # 自动启动失败不阻塞 UI 打开 (PII 扫描降级为手动点击); 记录但不弹出
        try:
            import logging
            logging.getLogger(__name__).warning(
                "auto PII scan on _open_word_docx failed: %s", _gap1_exc
            )
        except Exception:
            pass
    ```

    关键约束:
    - 不重写 start_ocr() 既有实现 (Phase 1 已经过验证); 仅在 _open_word_docx 末尾调用一次
    - 用 hasattr 防御: 如果 start_ocr 在某些 headless 测试场景下未定义, 不抛 AttributeError
    - 用 try/except 防御: 自动扫描异常不应阻塞 UI 打开流程 (与 D-12 worker 取消检查点 + Phase 1 错误降级路径一致)
    - 不引入新的 QThread 实例化代码: start_ocr() 内部已经负责 QThread 生命周期 (Phase 1 验证)

    不动:
    - start_ocr() 既有实现 (line 11410-11419 完整保留)
    - word_data 初始化 (line 10817-10843 已含 'pii': [] 键)
    - _reset_batch_session_state / _reset_word_preview_cache 等清理调用顺序
  </action>
  <verify>
    <automated>python -m unittest tests.unit.test_word_pii_redaction.TestAutoPiiScanOnOpen -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - main.py:_open_word_docx 在 word_data 初始化之后包含 self.start_ocr() 调用 (grep -n 'start_ocr' main.py 至少 1 行命中, 且该行位于 10795-10855 区间)
    - main.py:_open_word_docx 内的 start_ocr() 调用被 try/except 包裹 (grep -n 'auto PII scan on _open_word_docx failed' main.py 至少 1 行命中)
    - start_ocr() 既有函数体未被修改 (grep -n 'def start_ocr' main.py 行号保持 11410 附近不变)
    - 测试 TestAutoPiiScanOnOpen.test_open_docx_kicks_pii_pipeline 断言通过 MainWindow 测试 stub 调用 _open_word_docx 后, word_data[key]['pii'] 字段被填充 (PIIHit list 非空)
  </acceptance_criteria>
  <done>VERIFICATION.md Gap 1 闭合: 打开 .docx 后 PII 扫描自动启动, 无需用户手动点击扫描按钮 (D-12 链路完整)。</done>
</task>

<!-- ============================================================ -->
<!-- Task 2: Gap 2 — _has_word_replacement_candidates 纳入 PII -->
<!-- ============================================================ -->

<task type="auto" name="Task 2 (Gap 2): _has_word_replacement_candidates 把 PII 命中纳入判断">
  <files>main.py</files>
  <read_first>
    - main.py:10305-10314 — _has_word_replacement_candidates 既有实现 (Phase 1 既有逻辑, 仅检查 manual/ocr)
    - main.py:10819-10843 — word_data 字典结构 (每键含 'ocr' / 'manual' / 'pii' 三个候选字段)
    - privacyguard/workers/word_worker.py:_ModularWordWorker.run() — PII 命中写入 word_data[key]['pii'] 的代码路径 (Phase 3 Plan 02 落地)
  </read_first>
  <action>
    修改 main.py:_has_word_replacement_candidates (line 10305-10314), 在 `if data.get("manual") or data.get("ocr")` 判断之后追加 PII 检查:

    当前实现:
    ```python
    def _has_word_replacement_candidates(self):
        """是否存在可在右侧预览中展示的替换结果（规则/OCR/手动）。"""
        if self._has_enabled_word_replace_rules():
            return True
        for data in self.word_data.values():
            if not isinstance(data, dict):
                continue
            if data.get("manual") or data.get("ocr"):
                return True
        return False
    ```

    修改为 (在 line 10312 末尾追加 PII 条件):
    ```python
    def _has_word_replacement_candidates(self):
        """是否存在可在右侧预览中展示的替换结果（规则/OCR/手动/PII）。"""
        if self._has_enabled_word_replace_rules():
            return True
        for data in self.word_data.values():
            if not isinstance(data, dict):
                continue
            # [NEW G1 Gap 2] PII 命中也作为对比模式触发条件, 与 manual/ocr 同形态
            if data.get("manual") or data.get("ocr") or data.get("pii"):
                return True
        return False
    ```

    关键约束:
    - 单行扩展: 在现有 `or data.get("ocr")` 之后追加 `or data.get("pii")`
    - docstring 同步更新: 把 "规则/OCR/手动" 改为 "规则/OCR/手动/PII"
    - 保持 `_has_enabled_word_replace_rules()` 的早返回路径不变 (规则启用时不论 PII 都进入对比模式)
    - 保持 `isinstance(data, dict)` 防御 (避免 word_data[0] 等元数据键触发 AttributeError)

    不动:
    - 其他主方法 (_set_word_compare_mode / _build_word_* 等)
    - `_has_enabled_word_replace_rules` 实现
    - word_data 字典结构
  </action>
  <verify>
    <automated>python -m unittest tests.unit.test_word_pii_redaction.TestPiiOnlyDocumentEntersCompareMode -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - main.py:_has_word_replacement_candidates 在 data.get("ocr") 之后包含 data.get("pii") 检查 (grep -n 'data.get("pii")' main.py 在 _has_word_replacement_candidates 函数体内至少 1 行命中)
    - 函数 docstring 更新包含 "PII" 字样 (grep -n 'PII' main.py 在 _has_word_replacement_candidates 函数体内至少 1 行命中)
    - 测试 TestPiiOnlyDocumentEntersCompareMode.test_pii_only_returns_true 构造 word_data 含 PIIHit 列表 (无 manual/ocr/规则), 断言 _has_word_replacement_candidates() 返回 True
    - 测试 TestPiiOnlyDocumentEntersCompareMode.test_empty_returns_false 反向断言 (无 PII/manual/ocr/规则时返回 False)
  </acceptance_criteria>
  <done>VERIFICATION.md Gap 2 闭合: 仅含 PII 命中的 Word 文档能自动进入对比预览模式 (与 manual/ocr 命中同等待遇)。</done>
</task>

<!-- ============================================================ -->
<!-- Task 3: Gap 3 — _build_word_replaced_preview_html 注入 pii_matches -->
<!-- ============================================================ -->

<task type="auto" name="Task 3 (Gap 3): _build_word_replaced_preview_html 全量重载路径注入 pii_matches">
  <files>main.py, tests/unit/test_word_pii_redaction.py</files>
  <read_first>
    - main.py:10411-10417 — _build_word_replaced_preview_html 既有 merge 调用点 (缺 pii_matches 形参, 是 Gap 3 的修改位置)
    - main.py:11965-12035 — _build_word_*_panel_updates 增量更新路径 (Phase 3 Plan 03 已落地 pii_matches 注入; 这是 Gap 3 fix 的样板)
    - main.py:863 merge_word_matches_with_priority — D-01 锁定 pii_matches 形参签名 (Phase 3 Plan 03 已扩展)
  </read_first>
  <action>
    修改 main.py:_build_word_replaced_preview_html (line 10411-10417), 在 ocr_matches 之后追加 pii_matches 形参注入, 镜像 Plan 03 Task 2 (line 12024) 的写法。

    当前实现 (line 10411-10417):
    ```python
    merged_matches = merge_word_matches_with_priority(
        source_text,
        self.word_replace_rules,
        self.replacement_text,
        manual_matches=self.word_data[key].get("manual", []),
        ocr_matches=self.word_data[key].get("ocr", [])
    )
    ```

    修改为 (在 ocr_matches 之后追加一行):
    ```python
    merged_matches = merge_word_matches_with_priority(
        source_text,
        self.word_replace_rules,
        self.replacement_text,
        manual_matches=self.word_data[key].get("manual", []),
        ocr_matches=self.word_data[key].get("ocr", []),
        # [NEW G1 Gap 3] 全量重载路径同样注入 PII 命中 (与 Plan 03 增量路径 line 12024 对齐)
        pii_matches=self.word_data[key].get("pii", []),
    )
    ```

    关键约束:
    - 单行扩展: 在 ocr_matches 形参后追加 pii_matches 形参
    - 注释引用 G1 Gap 3 + Plan 03 line 12024 作为代码溯源
    - 不动 _build_word_original_preview_fragment (line 11985-12004 的 css_class="pii-highlight" 解析逻辑是 Plan 03 Task 2 的 css_class 渲染; 本 Gap 3 只修全量重载的 merge 调用)

    同时在 tests/unit/test_word_pii_redaction.py 末尾追加 TestPiiFullReloadPreviewContainsMask TestClass:

    测试 1 (test_pii_full_reload_includes_pii_mask_in_replaced_html):
    - 构造 MainWindow 测试 stub (沿用 test_word_pii_redaction 既有 stub 形态)
    - word_data[key] 含 {'pii': [PIIHit(CN_ID_CARD, page_offset=N, page_length=18, ...)], 'ocr': [], 'manual': []}
    - 调用 _build_word_replaced_preview_html(...)
    - 断言 returned HTML 含 partial mask 字符串 (如 "110101********1234") 或 blackout 占位 (如 "[已脱敏]")
    - 断言 returned HTML 不含原始身份证号

    测试 2 (test_pii_full_reload_with_ocr_collision_pii_wins):
    - word_data[key] 含 {'pii': [PIIHit(CN_ID_CARD, ...)], 'ocr': [{'start': N, 'end': N+18, 'replacement': '[OCR]', 'source': 'ocr'}], 'manual': []}
    - 调用 _build_word_replaced_preview_html(...)
    - 断言 returned HTML 含 partial mask 字符串 (D-02 PII > OCR); 不含 [OCR]

    关键约束 (测试):
    - 不依赖 Qt event loop (沿用既有 _build_docx_with_paragraphs / build_word_preview_stub 范式)
    - 不引入新的 docx fixtures (复用 test_word_pii_redaction 既有 helpers)
    - PIIHit 通过测试 helper 构造 (test_word_preview_highlight 既有 _make_pii_hit 范式)
    - 使用 self.assertIn / self.assertNotIn 验证 HTML 内容
  </action>
  <verify>
    <automated>python -m unittest tests.unit.test_word_pii_redaction -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - main.py:_build_word_replaced_preview_html 内的 merge_word_matches_with_priority 调用包含 pii_matches= 形参 (grep -n 'pii_matches=self.word_data\[key\].get("pii", \[\])' main.py 在 _build_word_replaced_preview_html 函数体内至少 1 行命中)
    - 该 pii_matches 形参与 ocr_matches 形参相邻 (行号差 <= 2)
    - tests/unit/test_word_pii_redaction.py 末尾追加 TestPiiFullReloadPreviewContainsMask TestClass (grep -n 'class TestPiiFullReloadPreviewContainsMask' test_word_pii_redaction.py 至少 1 行命中)
    - 测试 test_pii_full_reload_includes_pii_mask_in_replaced_html 断言 partial mask 在 HTML 中存在
    - 测试 test_pii_full_reload_with_ocr_collision_pii_wins 断言 PII > OCR (D-02 不变量)
    - 336 既有测试基线保持通过 (D-16 + D-17 不变量)
  </acceptance_criteria>
  <done>VERIFICATION.md Gap 3 闭合: 全量重载右栏 HTML 路径包含 PII 掩码, 与增量 DOM patch 路径行为一致 (Plan 03 line 12024 镜像扩展)。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| _open_word_docx → start_ocr | 既有 Phase 1 启动路径; 调用链在 MainWindow 主线程, start_ocr() 内部启动 QThread 子线程 (Phase 1 验证) |
| _has_word_replacement_candidates → word_data[key] | 主线程只读访问; 不修改 word_data; 不并发 |
| _build_word_replaced_preview_html → merge_word_matches_with_priority | 主线程只读访问; 输出 HTML 字符串, 不修改 word_data; 不并发 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-G1-01 | E (Elevation of Privilege) | _open_word_docx 异常 start_ocr 阻塞 UI | mitigate | try/except 包裹, 失败降级为手动扫描 + logging.warning (不弹错误对话框) |
| T-G1-02 | I (Information Disclosure) | PII-only 文档不进 compare mode | mitigate | Gap 2 fix 在 _has_word_replacement_candidates 同步 pii 字段; 测试覆盖 |
| T-G1-03 | T (Tampering) | full reload 路径 PII 缺失 | mitigate | Gap 3 fix 注入 pii_matches; 测试覆盖 |
| T-G1-04 | R (Repudiation) | 自动扫描异常被静默吃掉 | low | logging.warning 记录, 不弹窗不抛错 (与 Phase 1 worker 错误降级路径一致) |

## Per-Task Security Verification

| Task | Threat Ref | Automated Check |
|------|------------|-----------------|
| Task 1 | T-G1-01 / T-G1-04 | TestAutoPiiScanOnOpen 验证 start_ocr 调用且异常不阻塞 |
| Task 2 | T-G1-02 | TestPiiOnlyDocumentEntersCompareMode 验证 PII-only 返回 True |
| Task 3 | T-G1-03 | TestPiiFullReloadPreviewContainsMask 验证 mask 在 HTML 中 |
</threat_model>

<verification>
[总体 G1 验证]
- python -m unittest tests.unit.test_word_pii_redaction -v (G1 范围: 既有 8 测试 + 新增 5 测试 PASS)
- python -m unittest tests.unit.test_word_preview_highlight tests.unit.test_word_pii_adapter tests.unit.test_word_worker_pii tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_convergence tests.unit.test_package_imports -v (Phase 3 范围: 不破坏)
- python -m unittest discover -s tests/unit -q (完整基线: 336+ 测试全部 PASS; D-16 + D-17 不变量)
</verification>

<success_criteria>
[G1 完成判定]
1. main.py:_open_word_docx 自动调用 self.start_ocr() (Gap 1 fix)
2. main.py:_has_word_replacement_candidates 包含 data.get("pii") 检查 (Gap 2 fix)
3. main.py:_build_word_replaced_preview_html 注入 pii_matches 形参 (Gap 3 fix)
4. tests/unit/test_word_pii_redaction.py 增 5 个新测试方法 (3 TestClass), 全部 PASS
5. 336 既有测试基线保持通过 (D-16 + D-17 不变量)
6. start_ocr() 既有函数体未被修改 (Phase 1 不变量)
7. 合并函数 merge_word_matches_with_priority 在 3 处调用点 (_build_word_original_panel_updates / _build_word_replaced_panel_updates / _build_word_replaced_preview_html) 都注入 pii_matches 形参
</success_criteria>

<output>
Create .planning/phases/03-word/03-G1-01-auto-scan-and-pii-compare-SUMMARY.md when done
</output>

## Artifacts this phase produces

- main.py:_open_word_docx — 增 `try: self.start_ocr() except Exception: logging.warning` 块 (Gap 1)
- main.py:_has_word_replacement_candidates — 增 `or data.get("pii")` 子句 (Gap 2)
- main.py:_build_word_replaced_preview_html — 增 `pii_matches=self.word_data[key].get("pii", [])` 形参 (Gap 3)
- tests/unit/test_word_pii_redaction.py — 增 TestAutoPiiScanOnOpen / TestPiiOnlyDocumentEntersCompareMode / TestPiiFullReloadPreviewContainsMask 3 个 TestClass (5 测试方法)