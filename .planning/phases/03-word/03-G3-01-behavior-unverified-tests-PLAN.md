---
phase: 03-word
plan: G3
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/unit/test_word_pii_redaction.py (MOD — 增 3 个 BU TestClass: BU-5 toggle 状态 / BU-6 多文档生命周期 / BU-7 取消保留部分结果)
  - tests/unit/test_word_package_imports.py (NEW — PyInstaller hiddenimports 静态 + 静态 parity check; BU-8 范围)
autonomous: true
gap_closure: true
requirements:
  - FMT-02
  - OPS-04
user_setup: []

estimate:
  tokens: 25000
  raw_tokens: 13000
  tasks: 3
  confidence: med

must_haves:
  truths:
    - _toggle_mask_override_this_doc 在 checked=True / checked=False 切换时 _word_mask_override_this_doc 字段正确转换 (BU-5; verification tests, not new functionality)
    - 打开第二个 Word 文档时, _word_mask_override_this_doc 字段从非 None 复位为 None (BU-6; verification tests, not new functionality)
    - WordWorker 在 PII 扫描中途被请求取消后, 已处理块的 word_data[key]['pii'] 字段仍保留已写入的 PIIHit 列表, 未处理块不被继续写入 (BU-7; verification tests, not new functionality)
    - PyInstaller hiddenimports 在 Windows/macOS spec 文件中静态包含 'privacyguard.pii.word_adapter' (BU-8 静态层; 真实 frozen build 仍需平台人工验收)
    - PyInstaller hiddenimports 同样静态包含 'privacyguard.utils.word_props' (G2 补强; cp30 同命名空间 parity 守卫, 跨计划交叉引用)
  artifacts:
    - tests/unit/test_word_pii_redaction.py — 增 3 个 BU TestClass (TestToggleMaskOverrideStateTransition / TestMultiDocumentLifecycleReset / TestWorkerCancellationPreservesPartialResults), 7 测试方法
    - tests/unit/test_word_package_imports.py (NEW) — BU-8 PyInstaller hiddenimports 静态 parity + 模块 import 验证
    - tests/unit/test_word_props.py (G2 范围, 跨计划交叉引用) — TestPackageImportsParity 静态 parity 守卫 (cp30 同命名空间)
  key_links:
    - main.py:_toggle_mask_override_this_doc → self._word_mask_override_this_doc (BU-5; 既有产品代码)
    - main.py:_open_word_docx → self._word_mask_override_this_doc = None (BU-6, Plan 04 已就位 line 10815)
    - privacyguard/workers/word_worker.py:isInterruptionRequested → PII 扫描中途 break (BU-7; 既有产品代码)
    - packaging/windows/config/PrivacyGuard_windows.spec / packaging/macos/config/PrivacyGuard.spec / build_complete.sh → 'privacyguard.pii.word_adapter' 静态条目 (BU-8)
    - 同一 spec/build script → 'privacyguard.utils.word_props' 静态条目 (G2 补强, cp30 同风险面)

# Gap Closure Plan G3: Behavior-Unverified 项 BU-5/6/7/8 (集成测试)

<objective>
关闭 VERIFICATION.md behavior_unverified_items 列表中的 4 个 PRESENT_BEHAVIOR_UNVERIFIED 项:
- BU-5: _toggle_mask_override_this_doc 切换状态在保存流程中的端到端行为验证
- BU-6: 多文档生命周期下 _word_mask_override_this_doc 复位行为验证
- BU-7: WordWorker 在 PII 扫描中途取消的保留行为验证
- BU-8: PyInstaller frozen 包 word_adapter 模块加载 (静态 + 平台人工验收文档)

新增 4 个 TestClass 共 ~7 个测试方法, 把"代码静态可见但行为未验证"的状态全部转为"自动化测试可验证"。BU-8 静态层 (spec 文件 parity) 通过新增 test_word_package_imports.py 自动化覆盖; 真实 Windows/macOS frozen build 启动仍保留为人工验收 (gap 文档化而非伪造)。

Purpose: VERIFICATION.md 把这 4 项标为 PRESENT_BEHAVIOR_UNVERIFIED, 是 Phase 3 留尾。集成测试就位后 Phase 3 进入"自动化可验证"状态, 避免 Phase 8 frozen build 阶段复测。
Output: tests/unit/test_word_pii_redaction.py 增 3 BU TestClass + tests/unit/test_word_package_imports.py 新建 BU-8 静态层。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/03-word/03-VERIFICATION.md
@.planning/phases/03-word/03-CONTEXT.md
@.planning/phases/03-word/03-02-worker-pii-integration-SUMMARY.md
@.planning/phases/03-word/03-04-save-and-packaging-SUMMARY.md

# Source of truth (executor MUST read these files before editing)
@main.py:_toggle_mask_override_this_doc (line 8798-8817)
@main.py:_open_word_docx (line 10797-10815, _word_mask_override_this_doc 复位点)
@privacyguard/workers/word_worker.py:_ModularWordWorker.run (line 34-99, isInterruptionRequested 检查点)
@packaging/windows/config/PrivacyGuard_windows.spec (line 138-172 privacyguard_hiddenimports)
@packaging/macos/config/PrivacyGuard.spec (line 108-110)
@packaging/macos/scripts/build_complete.sh (line 68-70 parity 注释)
@tests/unit/test_word_pii_redaction.py (现有 8 测试; G3 在末尾追加 BU TestClass)
</context>

<tasks>

<!-- ============================================================ -->
<!-- Task 1: BU-5 — _toggle_mask_override_this_doc 状态转换测试 -->
<!-- ============================================================ -->

<task type="auto" name="Task 1 (BU-5): _toggle_mask_override_this_doc 状态转换集成测试">
  <files>tests/unit/test_word_pii_redaction.py</files>
  <!-- verification tests, not new functionality: BU-5 是为既有产品代码 _toggle_mask_override_this_doc (main.py:8798-8817) 补行为测试; 不引入新功能, 不修改产品代码 -->
  <read_first>
    - main.py:8798-8817 — _toggle_mask_override_this_doc 既有实现 (PDF + Word 双路径写入)
    - main.py:12756-12757 — _save_word 读取 self._word_mask_override_this_doc 的位置 (Plan 04 已落地)
    - tests/unit/test_word_pii_redaction.py (现有 8 测试的 stub 形态; 沿用 build_word_preview_stub 范式)
  </read_first>
  <action>
    在 tests/unit/test_word_pii_redaction.py 末尾追加 TestToggleMaskOverrideStateTransition TestClass:

    ```python
    class TestToggleMaskOverrideStateTransition(unittest.TestCase):
        """BU-5: _toggle_mask_override_this_doc 切换状态在 Word 路径上的端到端行为验证。"""

        def _build_minimal_word_stub(self):
            """构造最小 MainWindow stub 用于测试 toggle 路径。"""
            # 沿用既有 build_word_preview_stub 范式 (test_word_replace_rules:32-54)
            # 此处只复制必要字段: word_data / _word_mask_override_this_doc / _toggle_mask_override_this_doc
            ...

        def test_toggle_to_checked_sets_blackout(self):
            """点击 toggle 到 checked=True: _word_mask_override_this_doc == "blackout" """
            stub = self._build_minimal_word_stub()
            stub._toggle_mask_override_this_doc(True)
            self.assertEqual(stub._word_mask_override_this_doc, "blackout")

        def test_toggle_to_unchecked_clears_to_none(self):
            """点击 toggle 到 checked=False: _word_mask_override_this_doc == None """
            stub = self._build_minimal_word_stub()
            stub._toggle_mask_override_this_doc(False)
            self.assertIsNone(stub._word_mask_override_this_doc)

        def test_toggle_round_trip(self):
            """checked=True → False 完整 round-trip: blackout → None"""
            stub = self._build_minimal_word_stub()
            stub._toggle_mask_override_this_doc(True)
            self.assertEqual(stub._word_mask_override_this_doc, "blackout")
            stub._toggle_mask_override_this_doc(False)
            self.assertIsNone(stub._word_mask_override_this_doc)
    ```

    关键约束:
    - 不依赖 Qt event loop (直接构造 stub, 不实例化 QMainWindow)
    - 沿用既有 build_word_preview_stub 范式 (test_word_replace_rules:32-54)
    - 测试 toggle 写入路径, 不测试 _save_word 读取路径 (Plan 04 已覆盖 _save_word 路径)
    - 不修改 main.py:_toggle_mask_override_this_doc 既有实现 (G3 是补测试, 不改产品代码)
  </action>
  <verify>
    <automated>python -m unittest tests.unit.test_word_pii_redaction.TestToggleMaskOverrideStateTransition -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_word_pii_redaction.py 末尾追加 TestToggleMaskOverrideStateTransition TestClass (grep -n 'class TestToggleMaskOverrideStateTransition' test_word_pii_redaction.py 至少 1 行命中)
    - 3 测试方法覆盖 checked=True / checked=False / round-trip 3 个状态转换 (BU-5 全覆盖)
    - 测试通过 MainWindow stub 直接调 _toggle_mask_override_this_doc, 不依赖 Qt
    - 测试不修改产品代码, 仅验证既有行为 (verification tests, not new functionality)
  </acceptance_criteria>
  <done>BU-5 闭合: _toggle_mask_override_this_doc 状态转换在 Word 路径上可被自动化测试验证 (既有产品代码的行为测试, 不引入新功能)。</done>
</task>

<!-- ============================================================ -->
<!-- Task 2: BU-6/BU-7 — 多文档生命周期复位 + Worker 取消保留 -->
<!-- ============================================================ -->

<task type="auto" name="Task 2 (BU-6 + BU-7): 多文档复位 + Worker 取消保留集成测试">
  <files>tests/unit/test_word_pii_redaction.py</files>
  <!-- verification tests, not new functionality: BU-6/BU-7 是为既有产品代码 (_open_word_docx line 10815 复位 / _ModularWordWorker.run isInterruptionRequested 检查) 补行为测试; 不引入新功能, 不修改产品代码 -->
  <read_first>
    - main.py:10797-10815 — _open_word_docx 复位 self._word_mask_override_this_doc = None (Plan 04 已落地 line 10815)
    - privacyguard/workers/word_worker.py:34-99 — _ModularWordWorker.run() 主循环 (isInterruptionRequested 检查点在 line 50-51 / 67-70; Phase 3 Plan 02 已落地)
    - tests/unit/test_word_worker_pii.py — 既有 worker PII 测试 (test_worker_cancellation_still_emits_partial_results; Plan 02 已写; BU-7 需在此基础上补充 mid-scan 验证)
  </read_first>
  <action>
    在 tests/unit/test_word_pii_redaction.py 末尾追加 2 个 TestClass:

    TestClass 1: TestMultiDocumentLifecycleReset (BU-6 范围, 2 测试方法)

    ```python
    class TestMultiDocumentLifecycleReset(unittest.TestCase):
        """BU-6: 打开第二个 Word 文档时 _word_mask_override_this_doc 从非 None 复位为 None。"""

        def test_second_docx_open_resets_word_override(self):
            """打开 Doc A → 勾选全遮蔽 → 打开 Doc B → 断言 Doc B 从 None 开始"""
            # 沿用既有 build_word_preview_stub 范式, 用 in-memory Document() 模拟
            ...

        def test_second_docx_open_resets_word_override_after_unset(self):
            """打开 Doc A → 勾选全遮蔽 → 取消勾选 → 打开 Doc B → 断言 Doc B 仍从 None 开始"""
            ...
    ```

    TestClass 2: TestWorkerCancellationPreservesPartialResults (BU-7 范围, 2 测试方法)

    ```python
    class TestWorkerCancellationPreservesPartialResults(unittest.TestCase):
        """BU-7: WordWorker 在 PII 扫描中途取消后, 已处理块保留 word_data[key]['pii'] 字段。"""

        def test_cancellation_preserves_already_scanned_blocks(self):
            """构造多段落 docx; 前 N 段 run; 中途 requestInterruption; 验证前 N 段 word_data[key]['pii'] 类型为 list, 后 N 段未被写入 pii 字段"""
            # 沿用 test_word_worker_pii.py:29-45 _build_docx_with_paragraphs 范式
            ...

        def test_cancellation_emits_partial_results_not_crash(self):
            """中途取消不应让 worker 抛异常; word_data 结构完整 (无 KeyError)"""
            ...
    ```

    关键约束:
    - BU-6 测试不依赖 Qt (沿用既有 stub 范式); 调用 _open_word_docx 全流程或仅模拟其复位点
    - BU-7 测试用 QThread 子类同步调用 run() (沿用 test_word_worker_pii 既有范式); requestInterruption() 在循环中途触发
    - 不修改产品代码 (G3 是补测试, 不改既有行为)
    - 不引入新的 QThread 实例化 (用既有 _ModularWordWorker)
  </action>
  <verify>
    <automated>python -m unittest tests.unit.test_word_pii_redaction.TestMultiDocumentLifecycleReset tests.unit.test_word_pii_redaction.TestWorkerCancellationPreservesPartialResults -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_word_pii_redaction.py 末尾追加 TestMultiDocumentLifecycleReset TestClass (BU-6)
    - tests/unit/test_word_pii_redaction.py 末尾追加 TestWorkerCancellationPreservesPartialResults TestClass (BU-7)
    - 4 测试方法覆盖: BU-6 全遮蔽后开新文档复位 / BU-6 取消勾选后开新文档复位 / BU-7 中途取消前 N 段保留 / BU-7 中途取消不抛异常
    - 测试不修改产品代码, 仅验证既有行为 (verification tests, not new functionality; BU-6 验证 _open_word_docx 既有复位点 / BU-7 验证 _ModularWordWorker 既有 isInterruptionRequested 检查点)
    - 336 既有测试基线保持通过 (D-16 + D-17 不变量)
  </acceptance_criteria>
  <done>BU-6 + BU-7 闭合: 多文档生命周期复位 + Worker 取消保留行为可被自动化测试验证 (既有产品代码行为测试, 不引入新功能)。</done>
</task>

<!-- ============================================================ -->
<!-- Task 3: BU-8 — PyInstaller hiddenimports 静态 parity 测试 -->
<!-- ============================================================ -->

<task type="tdd" name="Task 3 (BU-8, TDD RED→GREEN): PyInstaller hiddenimports 静态 parity 测试 + 平台验收文档化">
  <files>tests/unit/test_word_package_imports.py (NEW)</files>
  <behavior>
    - RED 测试 1: test_windows_spec_contains_word_adapter_hiddenimport — 读取 PrivacyGuard_windows.spec, 断言内容包含 'privacyguard.pii.word_adapter'; 在 spec 修复前必须 FAIL
    - RED 测试 2: test_macos_spec_contains_word_adapter_hiddenimport — 读取 PrivacyGuard.spec, 断言内容包含 'privacyguard.pii.word_adapter'
    - RED 测试 3: test_macos_build_script_references_word_adapter — 读取 build_complete.sh, 断言内容包含 'privacyguard.pii.word_adapter'
    - RED 测试 4: test_word_adapter_module_imports_without_error — import privacyguard.pii.word_adapter 后断言 collect_pii_word_hits/locate_pii_hits_in_paragraph/apply_pii_replacements_to_docx 三函数存在
    - GREEN 实现: 上述 4 测试全部 PASS (BU-8 spec parity 静态层守卫; 真实 frozen build 启动保留 Phase 8 平台人工验收)
  </behavior>
  <read_first>
    - packaging/windows/config/PrivacyGuard_windows.spec (line 138-172 privacyguard_hiddenimports.extend)
    - packaging/macos/config/PrivacyGuard.spec (line 108-110)
    - packaging/macos/scripts/build_complete.sh (line 68-70 parity 注释)
    - tests/unit/test_package_imports.py (现有懒加载 + PyInstaller 兼容性测试范本)
  </read_first>
  <action>
    TDD 顺序执行:

    **RED 步骤 (先写测试, 验证 spec parity 当前状态):**
    1. 新建 tests/unit/test_word_package_imports.py (内容见下方, 含 4 TestClass 共 7 测试方法):
       - TestWindowsSpecHiddenimports (1 测试): 验证 Windows spec 含 'privacyguard.pii.word_adapter'
       - TestMacosSpecHiddenimports (1 测试): 验证 macOS spec 含 'privacyguard.pii.word_adapter'
       - TestMacosBuildScriptParity (1 测试): 验证 macOS build_complete.sh 含 'privacyguard.pii.word_adapter'
       - TestModuleImportableAfterSpecValidation (4 测试): 验证 word_adapter 三函数可 import + 各自属性存在
    2. 运行测试: `python -m unittest tests.unit.test_word_package_imports -v` — spec parity 测试在 Plan 04 已落地 hiddenimports 的前提下应当 PASS (因为 Plan 04 commit 6c7cc54 已加); 若 FAIL 则 executor 需要补 spec 同步 (cp30 parity 守卫)
    3. 提交 RED: `test(03-G3): add BU-8 PyInstaller hiddenimports static parity tests` (若测试已 PASS 也提交; RED→GREEN 形式依然成立 — Plan 04 已写好 spec, 本任务落地静态测试守护)

    **GREEN 步骤 (确认守护就位):**
    4. 确认 4 TestClass 全部 PASS
    5. 提交 GREEN: `feat(03-G3): enable BU-8 hiddenimports parity regression guard`

    **IMPROVE 步骤:**
    6. (跳过, 本任务无重构)

    完整测试文件:
    ```python
    """Phase 3 (G3 BU-8): PyInstaller hiddenimports 静态 parity 测试。

    验证 privacyguard.pii.word_adapter 在:
    - Windows spec 文件 (PrivacyGuard_windows.spec)
    - macOS spec 文件 (PrivacyGuard.spec)
    - macOS 构建脚本 (build_complete.sh)
    中被显式注册, 避免 cp30 ModuleNotFoundError 回归。

    真实 frozen build 启动 (Windows / macOS) 仍需平台人工验收; 当前测试仅覆盖静态层。
    """

    import re
    import unittest
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parents[2]
    WIN_SPEC = REPO_ROOT / "packaging" / "windows" / "config" / "PrivacyGuard_windows.spec"
    MAC_SPEC = REPO_ROOT / "packaging" / "macos" / "config" / "PrivacyGuard.spec"
    MAC_BUILD_SCRIPT = REPO_ROOT / "packaging" / "macos" / "scripts" / "build_complete.sh"

    HIDDENIMPORT_MODULE = "privacyguard.pii.word_adapter"


    class TestWindowsSpecHiddenimports(unittest.TestCase):
        def test_windows_spec_contains_word_adapter_hiddenimport(self):
            self.assertTrue(WIN_SPEC.exists(), f"Windows spec not found: {WIN_SPEC}")
            content = WIN_SPEC.read_text(encoding="utf-8")
            self.assertIn(
                HIDDENIMPORT_MODULE, content,
                f"Windows spec 必须显式包含 {HIDDENIMPORT_MODULE} (cp30 教训)",
            )


    class TestMacosSpecHiddenimports(unittest.TestCase):
        def test_macos_spec_contains_word_adapter_hiddenimport(self):
            self.assertTrue(MAC_SPEC.exists(), f"macOS spec not found: {MAC_SPEC}")
            content = MAC_SPEC.read_text(encoding="utf-8")
            self.assertIn(
                HIDDENIMPORT_MODULE, content,
                f"macOS spec 必须显式包含 {HIDDENIMPORT_MODULE}",
            )


    class TestMacosBuildScriptParity(unittest.TestCase):
        def test_macos_build_script_references_word_adapter(self):
            self.assertTrue(MAC_BUILD_SCRIPT.exists())
            content = MAC_BUILD_SCRIPT.read_text(encoding="utf-8")
            self.assertIn(
                HIDDENIMPORT_MODULE, content,
                f"macOS build_complete.sh 必须提及 {HIDDENIMPORT_MODULE} (parity 注释或显式条目)",
            )


    class TestModuleImportableAfterSpecValidation(unittest.TestCase):
        """静态验证通过后, 验证 word_adapter 模块本身在 import 时不抛 ModuleNotFoundError。"""

        def test_word_adapter_module_imports_without_error(self):
            from privacyguard.pii import word_adapter  # noqa: F401
            self.assertTrue(hasattr(word_adapter, "collect_pii_word_hits"))
            self.assertTrue(hasattr(word_adapter, "locate_pii_hits_in_paragraph"))
            self.assertTrue(hasattr(word_adapter, "apply_pii_replacements_to_docx"))

        def test_collect_pii_word_hits_callable(self):
            from privacyguard.pii import word_adapter
            self.assertTrue(callable(word_adapter.collect_pii_word_hits))

        def test_locate_pii_hits_in_paragraph_callable(self):
            from privacyguard.pii import word_adapter
            self.assertTrue(callable(word_adapter.locate_pii_hits_in_paragraph))

        def test_apply_pii_replacements_to_docx_callable(self):
            from privacyguard.pii import word_adapter
            self.assertTrue(callable(word_adapter.apply_pii_replacements_to_docx))


    if __name__ == "__main__":
        unittest.main()
    ```

    关键约束:
    - 静态层验证 (spec 文件 + build script 字符串匹配), 不真正构建 frozen artifact
    - 测试用 Path.resolve().parents[2] 定位仓库根 (与既有 test_package_imports.py 同形态)
    - 真实 frozen build 启动仍需在 Phase 8 平台验收 (本测试不伪造)
    - 不修改产品代码; 仅做静态 parity check
    - TDD 顺序: RED 测试先落地 (Plan 04 已就位 hiddenimports, 测试应当 PASS) → GREEN 守护启用 → IMPROVE 跳过

    任务完成后的整体验证:
    - python -m unittest tests.unit.test_word_package_imports -v (BU-8 新测试 PASS)
    - python -m unittest tests.unit.test_word_pii_redaction -v (G3 既有 8 + G1 新增 5 + G3 新增 7 = 20 测试 PASS)
    - python -m unittest discover -s tests/unit -q (完整基线: 336 既有 + G1+G2+G3 新增 = 343+ 测试 PASS)
  </action>
  <verify>
    <automated>python -m unittest tests.unit.test_word_package_imports tests.unit.test_word_pii_redaction -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_word_package_imports.py 新建 (grep -n 'TestWindowsSpecHiddenimports' test_word_package_imports.py 至少 1 行命中)
    - RED 验证: 在 test 文件落地后立即运行, 必须有明确 PASS/FAIL 输出 (RED commit 提交记录完整)
    - GREEN 验证: 4 TestClass (TestWindowsSpecHiddenimports / TestMacosSpecHiddenimports / TestMacosBuildScriptParity / TestModuleImportableAfterSpecValidation) 共 7 测试方法全部 PASS
    - 3 个 spec / build script 文件均包含 'privacyguard.pii.word_adapter' 字符串 (Plan 04 已落地; G3 验证)
    - 真实 frozen build 启动保留为 Phase 8 平台验收 (gap 在 docstring 中明确说明)
    - 336 既有测试基线保持通过 (D-16 + D-17 不变量)
    - TDD 提交历史: RED commit (test) + GREEN commit (feat/guard) 完整
  </acceptance_criteria>
  <done>BU-8 静态层闭合: Windows/macOS spec parity 通过自动化测试守护; 真实 frozen build 启动保留为 Phase 8 平台人工验收。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| _toggle_mask_override_this_doc → _word_mask_override_this_doc | MainWindow 主线程属性写入; QAction toggle 信号同步触发 |
| _open_word_docx → _word_mask_override_this_doc = None | 文档级生命周期复位; 每次打开新文档重置 |
| _ModularWordWorker.run → isInterruptionRequested | QThread 子线程扫描循环; 用户点击取消按钮时由主线程触发 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-G3-01 | T (Tampering) | toggle 状态在不同 path 间不一致 | mitigate | BU-5 测试覆盖 checked=True/False/round-trip 3 态 |
| T-G3-02 | I (Information Disclosure) | 第二个文档继承第一个文档的 blackout 状态 | mitigate | BU-6 测试覆盖多文档生命周期复位 |
| T-G3-03 | A (Availability) | Worker 取消导致 word_data 状态不一致 | mitigate | BU-7 测试覆盖已处理块保留 + 不抛异常 |
| T-G3-04 | E (Elevation of Privilege) | PyInstaller frozen 包缺 word_adapter hiddenimport | mitigate (static) / accept (platform) | BU-8 静态 spec parity; 真实 frozen build 人工验收 |

## Per-Task Security Verification

| Task | Threat Ref | Automated Check |
|------|------------|-----------------|
| Task 1 (BU-5) | T-G3-01 | TestToggleMaskOverrideStateTransition 3 测试方法 |
| Task 2 (BU-6) | T-G3-02 | TestMultiDocumentLifecycleReset 2 测试方法 |
| Task 2 (BU-7) | T-G3-03 | TestWorkerCancellationPreservesPartialResults 2 测试方法 |
| Task 3 (BU-8) | T-G3-04 | TestWindowsSpecHiddenimports + TestMacosSpecHiddenimports + TestMacosBuildScriptParity 3 静态测试 |
</threat_model>

<verification>
[总体 G3 验证]
- python -m unittest tests.unit.test_word_pii_redaction -v (G3 范围: 既有 8 + G1 新增 5 + G3 新增 7 = 20 测试 PASS)
- python -m unittest tests.unit.test_word_package_imports -v (G3 BU-8 新测试 PASS)
- python -m unittest tests.unit.test_word_worker_pii -v (Plan 02 既有 PASS; 不破坏)
- python -m unittest discover -s tests/unit -q (完整基线: 336 既有 + G1+G2+G3 新增 = 343+ 测试 PASS; D-16 + D-17 不变量)
</verification>

<success_criteria>
[G3 完成判定]
1. tests/unit/test_word_pii_redaction.py 末尾追加 3 个 BU TestClass (BU-5 + BU-6 + BU-7), 共 7 测试方法 (verification tests, not new functionality)
2. tests/unit/test_word_package_imports.py 新建, 包含 4 TestClass, 7 测试方法 (BU-8 静态 parity; TDD RED→GREEN 提交完整)
3. _toggle_mask_override_this_doc 状态转换可被自动化验证 (BU-5)
4. 多文档生命周期 _word_mask_override_this_doc 复位可被自动化验证 (BU-6)
5. WordWorker 取消后已处理块保留 word_data[key]['pii'] 字段可被自动化验证 (BU-7)
6. PyInstaller spec / build script 静态 parity 可被自动化验证 (BU-8)
7. PyInstaller spec / build script 静态 parity 同样覆盖 'privacyguard.utils.word_props' (G2 补强, cp30 同风险面; 跨计划交叉引用)
8. 真实 frozen build 启动保留为 Phase 8 平台人工验收 (gap 文档化)
9. 336 既有测试基线保持通过 (D-16 + D-17 不变量)
10. Phase 3 不再含 PRESENT_BEHAVIOR_UNVERIFIED 项 (全部转 PRESENT_BEHAVIOR_VERIFIED 或 PLATFORM_GAP_DOCUMENTED)
</success_criteria>

<output>
Create .planning/phases/03-word/03-G3-01-behavior-unverified-tests-SUMMARY.md when done
</output>

## Artifacts this phase produces

- tests/unit/test_word_pii_redaction.py (MOD) — 3 new TestClass (TestToggleMaskOverrideStateTransition / TestMultiDocumentLifecycleReset / TestWorkerCancellationPreservesPartialResults), 7 new test methods total
- tests/unit/test_word_package_imports.py (NEW, ~80 LOC) — 4 TestClass (TestWindowsSpecHiddenimports / TestMacosSpecHiddenimports / TestMacosBuildScriptParity / TestModuleImportableAfterSpecValidation), ~7 test methods