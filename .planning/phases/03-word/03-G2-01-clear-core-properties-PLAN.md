---
phase: 03-word
plan: G2
type: execute
wave: 1
depends_on: []
files_modified:
  - privacyguard/utils/word_props.py (NEW — clear_word_core_properties(doc, keys=None) helper)
  - privacyguard/utils/__init__.py (MOD — 暴露 clear_word_core_properties; 保持 lazy-load 纪律)
  - main.py (MOD — _save_word 调用 clear_word_core_properties; 与 Phase 2 PDF metadata clearing 对齐)
  - tests/unit/test_word_props.py (NEW — helper 单元测试 + main.py 集成测试)
autonomous: true
gap_closure: true
requirements:
  - FMT-02
user_setup: []

estimate:
  tokens: 30000
  raw_tokens: 15000
  tasks: 3
  confidence: high

must_haves:
  truths:
    - 保存 .docx 后, Document.core_properties.title/author/subject/comments/keywords 5 个核心属性被清空字符串 (与 Phase 2 PDF SAFE-03 D-15 策略对齐; 不使用 placeholder)
    - clear_word_core_properties 是纯函数 + 接受 Document 对象 (与 word_adapter 同形态, 不 import python-docx 在类型 hint 上); 调用方持有 Document 句柄
    - main.py:_save_word 在 body 真脱敏之后 + new_doc.save(fname) 之前调用 clear_word_core_properties (line 12837 save 之前)
    - PyInstaller hiddenimports 在 Windows/macOS spec 文件中静态包含 'privacyguard.utils.word_props' (cp30 教训; 静态层守卫)
  artifacts:
    - privacyguard/utils/word_props.py — clear_word_core_properties(doc, keys=None) helper (~30 LOC)
    - privacyguard/utils/__init__.py — _LAZY_IMPORTS 注册 clear_word_core_properties (与 pii 子包同形态的 lazy-load 纪律)
    - main.py:_save_word — 在 new_doc.save(fname) (line 12837) 之前调 clear_word_core_properties(new_doc); fallback 到 self.word_doc 若 executor 发现 in-place 改造
    - tests/unit/test_word_props.py — 6 个 TestClass (TestClearAllFiveProps / TestClearSpecificKeys / TestNoDocxImportInHelper / TestIntegrationWithSaveWord / TestReverseExtractionCoreProperties / TestPackageImportsParity) ~10 测试方法
  key_links:
    - main.py:_save_word (line 12755 new_doc = Document(temp_file); line 12837 new_doc.save(fname)) → clear_word_core_properties (Gap 4 fix; 在 body 脱敏 + save 之间)
    - clear_word_core_properties → Document.core_properties.title/author/subject/comments/keywords (python-docx 公开 API)
    - privacyguard.utils.word_props → python-docx Document (类型 hint forward reference "Document", 不在模块顶层 import)
    - Phase 2 PDF metadata clearing 参考 (privacyguard/pii/pdf_adapter.py 中等价的 metadata clear 路径; 命名空间沿用)
    - cp30 教训 → TestPackageImportsParity 静态 spec parity 守卫 (privacyguard.utils.word_props 与 privacyguard.pii.word_adapter 同 cp30 风险面)

# Gap Closure Plan G2: Word 文档 core_properties 清除 (Gap 4)

<objective>
关闭 VERIFICATION.md 暴露的 Gap 4: 保存 .docx 后 Document.core_properties (Title/Author/Subject/Comments/Keywords 五个标准属性) 必须被清空, 与 Phase 2 PDF SAFE-03 元数据清除策略对齐 (D-15 决策: 空字符串而非占位符)。新建 privacyguard/utils/word_props.py helper, 在 main.py:_save_word 的 body 真脱敏之后 + doc.save(fname) 之前调用, 同时新增 5 个单元测试覆盖 (5 属性全部清空 / 指定子集清空 / 空 doc 不报错 / helper 不 import docx / 与 _save_word 集成)。

Purpose: Phase 3 当前 SUCCESS Criterion 4 "Exported Word doc retains paragraph/table formatting and no longer contains the original sensitive text in its body or document properties" 中 "document properties" 部分处于 FAIL 状态 (VERIFICATION 表 line 47-49 标 BLOCKED)。独立 helper 模块保持 v37.7.6 收敛纪律 (新逻辑进 privacyguard/ 而非 main.py)。
Output: privacyguard/utils/word_props.py + main.py _save_word 接入 + 5 个单元测试。
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
@.planning/phases/03-word/03-04-save-and-packaging-SUMMARY.md

# Source of truth (executor MUST read these files before editing)
@main.py:_save_word (line 12698-12837, 与 Phase 3 Plan 04 摘要描述对应)
@privacyguard/pii/pdf_adapter.py (参考 Phase 2 metadata clearing 形态)
@privacyguard/utils/__init__.py (lazy-load 注册范本)
@privacyguard/utils/doc_converter.py (同 utils 命名空间下的 helper 范本)
@tests/unit/test_word_pii_redaction.py (与 _save_word 集成测试范本)
</context>

<tasks>

<!-- ============================================================ -->
<!-- Task 1: 创建 helper 模块 + 懒加载注册 -->
<!-- ============================================================ -->

<task type="tdd" name="Task 1 (TDD RED→GREEN→IMPROVE): 新建 privacyguard/utils/word_props.py helper + 懒加载注册 + 测试先行">
  <files>privacyguard/utils/word_props.py, privacyguard/utils/__init__.py, tests/unit/test_word_props.py</files>
  <behavior>
    - RED 测试 1: test_clear_default_five_properties — 调用 clear_word_core_properties(doc) 后, doc.core_properties.title/author/subject/comments/keywords 5 个字段全部等于 ""
    - RED 测试 2: test_clear_specific_keys_only_clears_those — 调用 clear_word_core_properties(doc, keys=("title",)) 后, 只有 title 被清空, author 等其余字段保持不变
    - RED 测试 3: test_clear_returns_count_of_cleared_fields — 函数返回 int, 等于实际写入清空字符串的字段数
    - RED 测试 4: test_clear_on_doc_without_core_properties_raises — 传入无 core_properties 属性的对象时, 抛 AttributeError (由 helper 自身在属性读取时抛)
    - RED 测试 5: test_no_docx_import_in_helper_at_runtime — importlib 加载 privacyguard.utils.word_props 时, sys.modules 不含 'docx' (TYPE_CHECKING 守卫生效)
  </behavior>
  <read_first>
    - privacyguard/utils/__init__.py (现有 lazy-load 注册范本, 找 doc_converter 等已有 helper 的注册形态)
    - privacyguard/utils/doc_converter.py (helper 模块结构范本)
    - privacyguard/pii/pdf_adapter.py (Phase 2 PDF metadata clearing 实现; 作为参考但不直接复制)
    - tests/unit/test_pdf_pii_redaction.py (Phase 2 reverse-extraction 测试范本)
    - CLAUDE.md (确认 privacyguard/ 是新共享逻辑归属; 不要把 helper 写在 main.py)
  </read_first>
  <action>
    TDD 顺序执行:

    **RED 步骤 (先写测试):**
    1. 新建 tests/unit/test_word_props.py, 写入 TestClearAllFiveProps / TestClearSpecificKeys 两个 TestClass 共 5 个测试方法 (RED 测试 1-5); 调用 from privacyguard.utils import clear_word_core_properties
    2. 运行测试: `python -m unittest tests.unit.test_word_props -v` — 必须全部 FAIL (ModuleNotFoundError 或 ImportError)
    3. 提交 RED: `test(03-G2): add failing tests for clear_word_core_properties`

    **GREEN 步骤 (最小实现):**
    4. 新建 privacyguard/utils/word_props.py (~30 LOC, 见下方完整实现):
       - TYPE_CHECKING 块守卫 docx import (runtime 不拉起 python-docx)
       - DEFAULT_KEYS = ("title", "author", "subject", "comments", "keywords")
       - clear_word_core_properties(doc, keys=None) -> int 实现: 遍历 keys, getattr(cp, key, None) 读取, 非 None 时 setattr(cp, key, ""), 返回 cleared 计数
    5. 修改 privacyguard/utils/__init__.py, 在 _LAZY_IMPORTS 字典追加 `'clear_word_core_properties': ('privacyguard.utils.word_props', 'clear_word_core_properties')`, __all__ 列表同步追加
    6. 运行测试: 必须全部 PASS
    7. 提交 GREEN: `feat(03-G2): implement clear_word_core_properties helper`

    **IMPROVE 步骤 (重构, 仅在需要时):**
    8. 检查 helper 是否有重复代码 / magic string / 可读性改进点; 若无明显改进则跳过此步
    9. 再次运行 `python -m unittest tests.unit.test_word_props -v` — 必须全部 PASS
    10. (可选) 提交 IMPROVE: `refactor(03-G2): clean up clear_word_core_properties`

    helper 完整实现:
    ```python
    """Word 文档元数据清除 (Phase 3 G2 Gap 4 / SAFE-03 Word 子项)。

    与 Phase 2 PDF metadata clearing 同策略: 清空 5 个标准 core_properties
    (Title / Author / Subject / Comments / Keywords), 设置为空字符串而非占位符
    (D-15: 占位符字符串仍可能在 audit 报告 / forensic 工具中被发现, 空字符串才是
    "完全清除" 语义)。调用方持有 python-docx Document 句柄传入 (与 word_adapter
    三函数同形态: 不在 helper 内 import python-docx, 仅 type hint forward ref)。

    公开 API:
    - clear_word_core_properties(doc, keys=None): 清空 Document.core_properties
      指定字段。keys=None 时清空 5 个标准字段 (D-15 默认集)。
    - DEFAULT_KEYS: 5 个标准字段名 tuple, 供外部扩展时复用。
    """

    from typing import Iterable, Optional, TYPE_CHECKING

    if TYPE_CHECKING:
        # 仅类型检查期; runtime 不 import python-docx
        from docx import Document  # noqa: F401

    DEFAULT_KEYS = ("title", "author", "subject", "comments", "keywords")


    def clear_word_core_properties(
        doc: "Document",
        keys: Optional[Iterable[str]] = None,
    ) -> int:
        """清空 doc.core_properties 指定字段; 返回清空字段数。

        Args:
            doc: python-docx Document (调用方持有句柄, 不在 helper 内 import docx)
            keys: 要清空的字段名 iterable; None 时使用 DEFAULT_KEYS
                  (title / author / subject / comments / keywords)

        Returns:
            int: 实际写入清空字符串的字段数 (Phase 3 G2 反向提取验证用)
        """
        target_keys = tuple(keys) if keys is not None else DEFAULT_KEYS
        cp = doc.core_properties
        cleared = 0
        for key in target_keys:
            try:
                current = getattr(cp, key, None)
            except Exception:
                continue
            if current is None:
                continue
            setattr(cp, key, "")
            cleared += 1
        return cleared
    ```

    privacyguard/utils/__init__.py 修改 (在 _LAZY_IMPORTS 末尾追加 + __all__ 同步):
    ```python
    'clear_word_core_properties': ('privacyguard.utils.word_props', 'clear_word_core_properties'),
    ```
    并在 __all__ 列表追加 'clear_word_core_properties' (与 privacyguard/pii/__init__.py 同形态)。

    关键约束:
    - 模块顶部不写 `from docx import Document`; 仅在 TYPE_CHECKING 块中写类型 import
      (Python runtime 不会执行 TYPE_CHECKING 块, 静态检查器才会; 与 word_adapter 同纪律)
    - 5 个标准字段是默认集 (D-15 策略); keys 形参允许外部传入子集
    - 返回清空字段数: 便于 _save_word 集成测试断言
    - 不修改 doc 其他属性 (subject / category / last_modified_by / revision / version / created / modified 不动)
    - TDD 顺序: RED 测试先 FAIL (ModuleNotFoundError) → GREEN 实现让测试 PASS → IMPROVE 重构 (若需要)
  </action>
  <verify>
    <automated>python -m unittest tests.unit.test_word_props -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_word_props.py 包含 5 个测试方法 (TestClearAllFiveProps 1 + TestClearSpecificKeys 1 + TestClearReturnsCount 1 + TestErrorHandling 1 + TestNoDocxImportAtRuntime 1)
    - RED 验证: 在 helper 实现前运行测试, 必须全部 FAIL (ModuleNotFoundError 或 ImportError; 不是 AssertionError 之外的 ERROR 即可)
    - GREEN 验证: helper + 懒加载注册完成后, 5 测试全部 PASS
    - privacyguard/utils/word_props.py 文件存在; clear_word_core_properties 函数定义齐全; DEFAULT_KEYS tuple 含 5 字段 (grep -n 'DEFAULT_KEYS' word_props.py 至少 1 行命中)
    - 文件 AST 扫描不包含运行时 docx import (grep -n -E '(from|import) docx' word_props.py 在 TYPE_CHECKING 块外应当无输出)
    - privacyguard/utils/__init__.py _LAZY_IMPORTS 包含 'clear_word_core_properties' key
    - privacyguard/utils/__init__.py __all__ 包含 'clear_word_core_properties' 字符串
    - 提交历史包含 RED commit (test) + GREEN commit (feat); IMPROVE 可选
  </acceptance_criteria>
  <done>word_props.py helper 模块就位 + 懒加载注册就位 + 5 个单元测试 RED→GREEN 全 PASS + TDD 提交历史完整。</done>
</task>

<!-- ============================================================ -->
<!-- Task 2: main.py:_save_word 接入 clear_word_core_properties -->
<!-- ============================================================ -->

<task type="auto" name="Task 2: main.py:_save_word 在 body 真脱敏之后 + save 之前清除 core_properties">
  <files>main.py</files>
  <read_first>
    - main.py:_save_word 函数体 (line 12738-12837; Phase 3 Plan 04 已扩展, body 真脱敏 + replace_matches_in_paragraph 已就位)
    - main.py:12755 — Plan 04 SUMMARY 已确认 `_save_word` 内 Document 句柄变量名为 `new_doc = Document(temp_file)`, 后续段落/表格遍历 + `new_doc.save(fname)` (line 12837) 均使用此名 (cp30 教训: 不要假设 in-place 改造, Plan 04 实际使用 local handle `new_doc`)
    - main.py:12760-12784 — 段落循环内 `new_doc.paragraphs` 遍历 + `apply_pii_replacements_to_docx(new_doc, {key: locations}, mode=mode)` 调用形态 (Plan 04 已落地, helper 调用范本)
    - main.py:12787-12834 — 表格循环内 `new_doc.tables` 遍历 + 同形态 apply_pii 调用
    - main.py:12837 — `new_doc.save(fname)` 调用点 (clear_word_core_properties 必须在此之前调用)
    - .planning/phases/03-word/03-04-save-and-packaging-SUMMARY.md — line 118 确认 "word_adapter.py 继续不 import python-docx, 由 _save_word 持有 Document 句柄并注入 adapter"; 句柄名以 SUMMARY 描述 + 实际 main.py line 12755 双重验证为 `new_doc`
    - Phase 2 PDF metadata clearing 接入点 (参考命名空间命名 + 调用形态)
  </read_first>
  <action>
    修改 main.py:_save_word, 在 Plan 04 已落地的 PII 真脱敏调用之后 + doc.save(fname) 之前, 增加 clear_word_core_properties 调用:

    在 line ~12834 (doc.save(fname) 之前) 追加:
    ```python
    # Phase 3 (G2 Gap 4): 清空 .docx core_properties (Title / Author / Subject /
    # Comments / Keywords), 与 Phase 2 PDF SAFE-03 metadata clearing 同策略 (D-15: 空字符串而非占位符)
    # 复用 Phase 3 Plan 04 _save_word 局部 new_doc 句柄, 由调用方持有 Document 传入 helper
    try:
        from privacyguard.utils import clear_word_core_properties
        _cleared_count = clear_word_core_properties(new_doc)
        if hasattr(self, "logger"):
            self.logger.info(f"[word_props] cleared {_cleared_count} core_properties")
    except Exception as _gap4_exc:
        # metadata 清除失败不阻塞 save 流程 (PII 主体已脱敏, metadata 是次要防线); 记录但不抛错
        try:
            import logging
            logging.getLogger(__name__).warning(
                "clear_word_core_properties failed: %s", _gap4_exc
            )
        except Exception:
            pass
    ```

    关键约束:
    - 在 new_doc.save(fname) (line 12837) 之前调用 (而不是之后; python-docx 修改 core_properties 后 save 才生效)
    - 复用 Plan 04 已经在 _save_word 内持有的 new_doc 句柄 (与 word_adapter 同形态: 调用方持有 Document 传入 helper)
    - **句柄名 fallback**: 若 executor 在 main.py 中发现 _save_word 实际使用的是 `self.word_doc` (in-place 改造) 而非 `new_doc` (Plan 04 当前形态), 应改用 `clear_word_core_properties(self.word_doc)` 或该函数实际持有的 Document 变量名 (read_first 已通过 SUMMARY + line 12755 验证为 `new_doc`, 但保持 fallback 防御)
    - 用 try/except 包裹: helper 异常不阻塞 save (PII 主体已经过真脱敏, metadata 是次要防线)
    - 用 hasattr(self, "logger") 防御: 不强制依赖 MainWindow.logger 字段
    - 用 local import `from privacyguard.utils import clear_word_core_properties`: 触发 _LAZY_IMPORTS 懒加载, 与 OPS-03 纪律一致

    不动:
    - Plan 04 已落地的 PII locate/apply 真脱敏代码
    - doc.save(fname) 调用位置
    - _save_word 函数签名与返回值
    - Plan 03 已落地的 merge_word_matches_with_priority pii_matches 注入 (line ~12700 区域)
  </action>
  <verify>
    <automated>python -m unittest tests.unit.test_word_props.TestIntegrationWithSaveWord -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - main.py:_save_word 在 doc.save(fname) 之前包含 clear_word_core_properties 调用 (grep -n 'clear_word_core_properties' main.py 在 _save_word 函数体内至少 1 行命中)
    - 该调用被 try/except 包裹 (grep -n 'clear_word_core_properties failed' main.py 至少 1 行命中)
    - 测试 TestIntegrationWithSaveWord.test_save_word_clears_core_properties 通过合成 .docx (含 Title="秘密信息" + Author="原作者") 模拟 _save_word 全流程, 验证保存后 Document(in_path).core_properties.title == "" 且 author == ""
    - 336 既有测试基线保持通过 (D-16 不变量)
  </acceptance_criteria>
  <done>Gap 4 闭合: 保存 .docx 后 Document.core_properties 5 个标准属性被清空, 与 Phase 2 PDF metadata clearing 策略对齐。</done>
</task>

<!-- ============================================================ -->
<!-- Task 3: 行为测试 + Phase 1/2/3 baseline 守护 -->
<!-- ============================================================ -->

<task type="auto" name="Task 3: 行为测试 + PyInstaller hiddenimports 静态 parity + baseline 守护">
  <files>tests/unit/test_word_props.py</files>
  <read_first>
    - tests/unit/test_word_props.py (Task 1/2 已写的 5 测试方法)
    - tests/unit/test_word_pii_redaction.py (与 _save_word 集成测试范本)
    - tests/unit/test_pdf_pii_redaction.py (Phase 2 PDF metadata 清除测试范本; 复用 reverse-extraction 思路)
    - packaging/windows/config/PrivacyGuard_windows.spec (line 138-172 privacyguard_hiddenimports.extend; cp30 教训)
    - packaging/macos/config/PrivacyGuard.spec (line 108-110)
    - packaging/macos/scripts/build_complete.sh (line 68-70 parity 注释)
    - tests/unit/test_package_imports.py (现有懒加载 + PyInstaller 兼容性测试范本)
  </read_first>
  <action>
    **Part A: 补充 tests/unit/test_word_props.py 的集成测试 (Task 1 已有 helper 单元测试, Task 3 增 1 个 TestClass + 2 测试方法):**

    TestClass: TestReverseExtractionCoreProperties (新增 1 个 TestClass 含 2 测试方法)

    测试 1 (test_save_word_does_not_leak_pii_in_title):
    - 构造 Document() 含 Title="身份证 110101199001011234 内容"
    - 调用 _save_word 全流程 (模拟 MainWindow 测试 stub 路径)
    - 重新打开保存后的 .docx, 断言 Document.core_properties.title 不含原始身份证号
    - 断言 Document.core_properties.title == ""

    测试 2 (test_save_word_clears_all_five_standard_properties):
    - 构造 Document() 同时设置 title / author / subject / comments / keywords 5 字段, 每个字段含模拟 PII
    - 调用 _save_word 全流程
    - 断言 5 字段全部为 "" 且不含原始模拟 PII

    **Part B: PyInstaller hiddenimports 静态 parity (cp30 教训 — 新模块 privacyguard/utils/word_props.py 必须显式注册):**

    在 tests/unit/test_word_props.py 末尾追加 TestPackageImportsParity TestClass 含 3 个测试方法:

    测试 3 (test_windows_spec_contains_word_props_hiddenimport):
    - 读取 packaging/windows/config/PrivacyGuard_windows.spec 文件内容
    - 断言内容包含字符串 'privacyguard.utils.word_props'
    - 缺失时报错信息明示 cp30 ModuleNotFoundError 回归风险

    测试 4 (test_macos_spec_contains_word_props_hiddenimport):
    - 读取 packaging/macos/config/PrivacyGuard.spec 文件内容
    - 断言内容包含字符串 'privacyguard.utils.word_props'

    测试 5 (test_macos_build_script_references_word_props):
    - 读取 packaging/macos/scripts/build_complete.sh 文件内容
    - 断言内容包含字符串 'privacyguard.utils.word_props' (parity 注释或显式条目均可)

    关键约束 (Part B):
    - 静态字符串匹配即可 (cp30 教训: 同命名空间 `privacyguard.utils.*` 模块 frozen 导入回归; 真实 frozen build 启动仍保留 Phase 8 平台人工验收)
    - 测试用 Path(__file__).resolve().parents[2] 定位仓库根 (与既有 test_package_imports.py 同形态)
    - 3 个 spec / build script 文件均须包含 'privacyguard.utils.word_props' (G2 与 G3 BU-8 共用 cp30 parity 守卫; G3 BU-8 已覆盖 `privacyguard.pii.word_adapter`, G2 Part B 覆盖 `privacyguard.utils.word_props`, 两者互补)
    - 不修改产品代码; 仅做静态 parity check

    测试套件整体验证 (Phase 1/2/3 baseline 不破坏):
    - python -m unittest tests.unit.test_word_props tests.unit.test_word_pii_redaction tests.unit.test_word_pii_adapter tests.unit.test_word_worker_pii tests.unit.test_word_preview_highlight tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_convergence tests.unit.test_package_imports tests.unit.test_word_package_imports -v
    - 应当 336 既有测试 + G2 新增 ~7 helper 测试 + 2 集成测试 + 3 hiddenimports 测试 + G3 BU-8 静态测试 = ~348+ 测试全部 PASS
  </action>
  <verify>
    <automated>python -m unittest tests.unit.test_word_props tests.unit.test_word_pii_redaction tests.unit.test_convergence tests.unit.test_package_imports tests.unit.test_word_package_imports -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_word_props.py 包含 6 TestClass (TestClearAllFiveProps / TestClearSpecificKeys / TestNoDocxImportInHelper / TestIntegrationWithSaveWord / TestReverseExtractionCoreProperties / TestPackageImportsParity) 共 ~10 测试方法
    - test_save_word_does_not_leak_pii_in_title 验证 Title 字段不含原始 PII 且为空
    - test_save_word_clears_all_five_standard_properties 验证 5 字段全部清空
    - test_windows_spec_contains_word_props_hiddenimport 验证 Windows spec 包含 'privacyguard.utils.word_props' (cp30 静态守护)
    - test_macos_spec_contains_word_props_hiddenimport 验证 macOS spec 包含 'privacyguard.utils.word_props'
    - test_macos_build_script_references_word_props 验证 macOS build_complete.sh 包含 'privacyguard.utils.word_props' (parity 注释或条目)
    - 336 既有测试基线保持通过 (D-16 + D-17 不变量)
    - Phase 1/2 既有 metadata 清除路径 (PDF) 不被破坏 (Phase 2 SAFE-03 反向提取测试 PASS)
  </acceptance_criteria>
  <done>Gap 4 完全闭合 + 6 个 TestClass 覆盖 (helper 单元 / _save_word 集成 / reverse-extraction 端到端 / hiddenimports 静态 parity) + baseline 不破坏。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| main.py:_save_word → clear_word_core_properties | 调用方持有 new_doc Document 句柄传入; helper 仅做属性清除, 不做 I/O |
| clear_word_core_properties → Document.core_properties | python-docx 公开 API; 修改 .title/.author/.subject/.comments/.keywords 字段 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-G2-01 | I (Information Disclosure) | Document.core_properties 残留原 PII | mitigate | helper 默认清空 5 字段为空字符串; tests 覆盖 reverse-extraction 验证 |
| T-G2-02 | T (Tampering) | helper 异常阻塞 _save_word 主流程 | mitigate | try/except 包裹, metadata 清除失败降级 (PII 主体已脱敏, metadata 是次要防线) |
| T-G2-03 | E (Elevation of Privilege) | helper 误 import python-docx 触发 eager load | mitigate | TYPE_CHECKING 块守卫; test_no_docx_import_in_helper_at_runtime 验证 |
| T-G2-04 | R (Repudiation) | metadata 清除失败被静默吃掉 | low | logging.warning 记录, 不弹窗不抛错 (与 G1 Task 1 错误降级路径一致) |

## Per-Task Security Verification

| Task | Threat Ref | Automated Check |
|------|------------|-----------------|
| Task 1 | T-G2-01 / T-G2-03 | test_clear_default_five_properties + test_no_docx_import_in_helper_at_runtime |
| Task 2 | T-G2-01 / T-G2-02 | test_save_word_clears_core_properties 验证 _save_word 集成 |
| Task 3 | T-G2-01 | test_save_word_does_not_leak_pii_in_title reverse-extraction |
</threat_model>

<verification>
[总体 G2 验证]
- python -m unittest tests.unit.test_word_props -v (G2 范围: 7 测试 PASS)
- python -m unittest tests.unit.test_word_pii_redaction -v (Phase 3 Plan 04 范围不破坏)
- python -m unittest tests.unit.test_convergence tests.unit.test_package_imports -v (OPS-03 + D-11 守卫不破坏)
- python -m unittest discover -s tests/unit -q (完整基线: 336+ 测试全部 PASS; D-16 + D-17 不变量)
</verification>

<success_criteria>
[G2 完成判定]
1. privacyguard/utils/word_props.py 存在且 clear_word_core_properties 函数实现齐全
2. privacyguard/utils/__init__.py _LAZY_IMPORTS + __all__ 注册就位
3. main.py:_save_word 在 new_doc.save(fname) (line 12837) 之前调 clear_word_core_properties(new_doc)
4. tests/unit/test_word_props.py 包含 6 TestClass, ~10 测试方法全 PASS
5. 保存 .docx 后 core_properties.title/author/subject/comments/keywords 5 字段全部为空字符串
6. helper 不在 runtime import python-docx (TYPE_CHECKING 守卫生效)
7. PyInstaller hiddenimports 在 Windows/macOS spec + build_complete.sh 静态包含 'privacyguard.utils.word_props' (cp30 parity 守护)
8. 336 既有测试基线保持通过 (D-16 + D-17 不变量)
9. Phase 2 PDF metadata clearing 不被破坏 (SAFE-03 反向提取测试 PASS)
10. TDD 提交历史完整: RED commit (test) + GREEN commit (feat); IMPROVE 可选
</success_criteria>

<output>
Create .planning/phases/03-word/03-G2-01-clear-core-properties-SUMMARY.md when done
</output>

## Artifacts this phase produces

- privacyguard/utils/word_props.py (NEW, ~30 LOC) — function: `clear_word_core_properties(doc, keys=None) -> int`; constant: `DEFAULT_KEYS = ("title", "author", "subject", "comments", "keywords")`
- privacyguard/utils/__init__.py (MOD) — `_LAZY_IMPORTS` dict + `__all__` list: 1 new entry each
- main.py:_save_word (MOD) — 增加 `try: clear_word_core_properties(new_doc) except Exception: logging.warning` 块 (在 doc.save(fname) 之前)
- tests/unit/test_word_props.py (NEW, ~150 LOC) — 5 TestClass: `TestClearAllFiveProps`, `TestClearSpecificKeys`, `TestNoDocxImportInHelper`, `TestIntegrationWithSaveWord`, `TestReverseExtractionCoreProperties`