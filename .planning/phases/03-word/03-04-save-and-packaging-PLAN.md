---
phase: 03-word
plan: 04
type: execute
wave: 3
depends_on:
  - 03-03-merge-and-preview
files_modified:
  - main.py (MOD — _save_word 接入 apply_pii_replacements_to_docx; _toggle_mask_override_this_doc 扩展 Word 路径; _word_mask_override_this_doc 字段; _open_word_docx 重置字段)
  - packaging/windows/config/PrivacyGuard_windows.spec (MOD — hiddenimports 增 'privacyguard.pii.word_adapter')
  - packaging/macos/scripts/build_complete.sh (MOD — macOS hiddenimports 同步)
  - tests/unit/test_word_pii_redaction.py (NEW)
autonomous: true
requirements:
  - FMT-02
  - MASK-02
  - OPS-04
user_setup: []

estimate:
  tokens: 60000
  raw_tokens: 30000
  tasks: 4
  confidence: high

must_haves:
  truths:
    - main.py::_save_word 真脱敏阶段对每个段落 / 表格 cell 调 locate_pii_hits_in_paragraph 拿 (hit, char_offset) 列表, 调 apply_pii_replacements_to_docx(doc, hit_locations_per_key, mode) 真脱敏; 产物 .docx 用 python-docx 重新打开后, 原始敏感字符串不存在 (D-04 + D-06 + SAFE-02 反向提取验证)
    - apply_pii_replacements_to_docx partial 模式产物含 partial_mask 字符串 (如 "110101********1234"); blackout 模式产物含 "[已脱敏]" (D-03 + D-06)
    - privacyguard/pii/word_adapter.py 不 import python-docx; apply_pii_replacements_to_docx 接收 Document 对象由调用方持有; 字脱敏路径走"生成文本 + 外部调 Python-docx" (D-06 + D-11)
    - main.py::_toggle_mask_override_this_doc 同时写 PDF + Word 路径: self.page_data[0]["mask_override_this_doc"] + self._word_mask_override_this_doc (D-05)
    - self._word_mask_override_this_doc 是 MainWindow 独立 instance attr (不污染 word_data 业务键空间, Pitfall 6 + RESEARCH Open Q #1); _save_word 读 getattr(self, "_word_mask_override_this_doc", None); "blackout" 模式覆盖 per_entity_default
    - _open_word_docx 重置 self._word_mask_override_this_doc = None (新文档加载复位)
    - PyInstaller Windows spec privacyguard_hiddenimports.extend([...]) 列表新增 'privacyguard.pii.word_adapter' (D-14 + cp30 回归预防); macOS build script 同步 (Phase 2 02-03 parity verified)
    - 282 既有测试 + Plan 1/2/3 新增测试保持通过 (D-16 + D-17 不变量)
  artifacts:
    - main.py::_save_word (line 12700) — 段落循环 + 表格 cell 循环各扩展: collect pii_hits = data.get("pii", []); locate locations = locate_pii_hits_in_paragraph(pii_hits, source_text); if locations: apply_pii_replacements_to_docx(new_doc, {key: locations}, mode); 段落循环调用替换既有 replace_matches_in_paragraph 之前; cell 循环同理
    - main.py::_toggle_mask_override_this_doc (line 8781) — 在 self.page_data[0] 设置后追加 self._word_mask_override_this_doc = "blackout" if checked else None
    - main.py:_open_word_docx (line 10777) — 函数末尾追加 self._word_mask_override_this_doc = None (新文档重置)
    - main.py:MainWindow.__init__ (line 5896 附近) — btn_mask_override 创建后追加 self._word_mask_override_this_doc = None (字段初始化)
    - packaging/windows/config/PrivacyGuard_windows.spec line 172 后 — 增 `'privacyguard.pii.word_adapter',` (D-14)
    - packaging/macos/scripts/build_complete.sh — 同步 (Phase 2 02-03 parity verified pattern)
    - tests/unit/test_word_pii_redaction.py — TestWordPiiRedaction 端到端 reverse-extraction 测试 (D-15 #3): test_redacted_docx_does_not_contain_original_secret / test_partial_mask_id_card_visible_in_output / test_partial_mask_phone_visible_in_output / test_blackout_mode_replaces_with_brackets / test_paragraph_style_preserved_after_save (D-07) / test_save_word_invokes_apply_pii_replacements (AST check)
  key_links:
    - main.py::_save_word → privacyguard.pii.word_adapter.locate_pii_hits_in_paragraph → apply_pii_replacements_to_docx → mask_for_entity (partial 模式) / "[已脱敏]" (blackout 模式)
    - main.py::_toggle_mask_override_this_doc → self._word_mask_override_this_doc (Mode 字段) → main.py::_save_word 读取 → mode 形参 (D-05)
    - _open_word_docx → self._word_mask_override_this_doc = None (生命周期重置)
    - PrivacyGuard_windows.spec → privacyguard.pii.word_adapter hiddenimports → PyInstaller frozen 启动 (cp30 回归预防)
---

# Phase 3 — Plan 4: _save_word 真脱敏 + 文档级 override + PyInstaller 同步 (Wave 3 Production)

<objective>
扩展 main.py::_save_word 真脱敏阶段接入 locate_pii_hits_in_paragraph + apply_pii_replacements_to_docx (D-04); MainWindow 加 self._word_mask_override_this_doc 独立 instance attr (D-05 + RESEARCH Open Q #1); _toggle_mask_override_this_doc 同时写 PDF + Word 路径 (D-05 + 复用现有 btn_mask_override 控件); _open_word_docx 重置 _word_mask_override_this_doc = None (新文档生命周期); PyInstaller Windows spec + macOS build script hiddenimports 增 'privacyguard.pii.word_adapter' (D-14 + cp30 回归预防); 新建 tests/unit/test_word_pii_redaction.py 端到端 reverse-extraction 测试 (D-15 #3 + SAFE-02 反向提取验证)。

Purpose: Wave 3 Production —— Word 文档保存时 PII 命中按 mask_strategy 真脱敏; 与 PDF 端 "识别即脱敏" 一致 (Phase 1/2 决策); 用户在工具栏 toggle 全遮蔽模式时, Word 端也跟随; PyInstaller 跨平台打包不破坏 cp30 已修复的 privacyguard.utils.security 导入回归。
Output: 真脱敏接入 + 文档级 override 字段 + toggle 双路径 + 跨平台 hiddenimports 同步 + reverse-extraction 端到端测试。
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
@.planning/phases/03-word/03-02-worker-pii-integration-PLAN.md (Plan 2 worker PII 接入)
@.planning/phases/03-word/03-03-merge-and-preview-PLAN.md (Plan 3 双栏预览 PII 渲染)
@main.py:12700 _save_word (现有 OCR + Manual 替换流程; D-04 接入点)
@main.py:8781 _toggle_mask_override_this_doc (现有 PDF toggle handler; D-05 扩展点)
@main.py:10777 _open_word_docx (现有 word_data 初始化; D-05 重置点)
@main.py:5896 btn_mask_override (现有 PDF toolbar 控件; D-05 复用)
@packaging/windows/config/PrivacyGuard_windows.spec:130-172 (hiddenimports 列表; D-14 同步点)
@packaging/macos/scripts/build_complete.sh (macOS 平行; D-14 同步点)
@tests/unit/test_pdf_pii_redaction.py (reverse-extraction 范本; D-15 #3 沿用)
@tests/unit/test_batch_word_replace.py (WordBatchReplaceWorker 范本; D-17 守护)
@tests/unit/test_convergence.py (现有 inline 守卫; Plan 3 已扩展)
</context>

<tasks>

<!-- ============================================================ -->
<!-- Task 1: _save_word 真脱敏接入 PII -->
<!-- ============================================================ -->

<task type="modify" name="Task 1: main.py::_save_word 接入 apply_pii_replacements_to_docx 真脱敏 PII 命中">
  <files>main.py</files></read_first>
    - main.py:12700-12795 _save_word (现有 OCR/Manual 替换流程; D-04 接入点)
    - main.py:12716-12734 (段落循环) / 12737-12767 (表格 cell 循环)
    - .planning/phases/03-word/03-01-word-adapter-PLAN.md (Plan 1 三函数定义)
    - .planning/phases/03-word/03-CONTEXT.md D-04 锁定 (Word 端默认与 PDF 一致真脱敏)
    - privacyguard/pii/__init__.py (懒加载入口: locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx)
    - privacyguard/pii/mask.py (mask_for_entity 分派表)
    - tests/unit/test_batch_word_replace.py (_apply_rules_to_document 范本)
  </read_first>
  <action>
    修改 main.py::_save_word (line 12700):
    1. 函数顶部 (line 12704 附近 from docx import Document 之后) 追加 PII 适配器 import:
       ```python
       from privacyguard.pii import (
           locate_pii_hits_in_paragraph,
           apply_pii_replacements_to_docx,
       )
       ```
       (D-11 锁定: 在 main.py 持有 Document 句柄并传入 adapter; 不在 adapter 内 import python-docx; Plan 1 test_convergence 已守 inline 禁止)
    2. 函数体顶部 (line 12714 之前) 计算 mode:
       ```python
       # [NEW D-05] 文档级 mask_override 读取 (Pitfall 6 + RESEARCH Open Q #1)
       override = getattr(self, "_word_mask_override_this_doc", None)
       mode = override if override in ("partial", "blackout") else "partial"
       ```
       默认 partial (与 Phase 2 D-13 per_entity_default 决策一致); toolbar 切换 blackout 时 mode 跟随
    3. 段落循环 (现有 line 12716-12734): 在 replace_matches_in_paragraph 之前追加 PII 真脱敏:
       ```python
       # [NEW D-04] PII 真脱敏 — 与 PDF 一致
       pii_hits = data.get("pii", [])
       if pii_hits:
           locations = locate_pii_hits_in_paragraph(pii_hits, source_text)
           if locations:
               apply_pii_replacements_to_docx(
                   new_doc, {key: locations}, mode=mode
               )
       ```
       (D-04: PII 真脱敏独立于 rule/manual 替换流程; 段级样式保留 D-07 由 apply_pii_replacements_to_docx 复用 replace_matches_in_paragraph 既有跨 run 处理)
    4. 表格 cell 循环 (现有 line 12737-12767): 同样在 replace_matches_in_paragraph 之前追加 PII 真脱敏; 但 cell 内有多段, 需对每段都构造 hit_locations 字典 (key 格式: table_X_cell_Y_Z_p_N —— 与 _walk_paragraphs 范本对齐; 见 Plan 1 word_adapter 三函数 _walk_paragraphs helper); 或者改为对整个 cell 一次性 apply (按 cell.text 合并各段后整体 replace)

    简化决策: 对 cell 内每段 (cell.paragraphs 列表) 走独立 apply_pii_replacements_to_docx 调用, 每次只传该段 key + locations (避免跨段合并导致 char_offset 漂移; D-09 锁定按段处理)
    5. 不动既有 replace_matches_in_paragraph 调用 (rule + manual + ocr 路径保持); 不动 QMessageBox / 异常处理 / shutil 临时文件管理
    6. 不动 self.file_path / self.word_data / self.word_replace_rules (D-04 单点扩展, 不污染既有 save 流程)
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_pii_redaction tests.unit.test_batch_word_replace tests.unit.test_word_replace_rules -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - main.py:12700 _save_word 函数顶部出现 `from privacyguard.pii import (locate_pii_hits_in_paragraph, apply_pii_replacements_to_docx,)` (grep -n 'locate_pii_hits_in_paragraph\|apply_pii_replacements_to_docx' main.py)
    - main.py:12700 _save_word 段落循环内出现 `apply_pii_replacements_to_docx(new_doc, {key: locations}, mode=mode)` 调用 (grep -n 'apply_pii_replacements_to_docx(new_doc' main.py)
    - 既有 test_batch_word_replace + test_word_replace_rules 仍 PASS (D-17 不变量, 既有 word_replace_rules + batch_word_replace 不被破坏)
    - test_word_pii_redaction 端到端 reverse-extraction 测试 (Task 4) 验证产物 .docx 不含原敏感字符串
  </acceptance_criteria>
  <done>_save_word 真脱敏接入 PII 就位; 既有 word_replace_rules + batch_word_replace 路径不被破坏。</done>
</task>

<!-- ============================================================ -->
<!-- Task 2: 文档级 override 字段 + toggle 双路径 -->
<!-- =========================================================== -->

<task type="modify" name="Task 2: _word_mask_override_this_doc 字段初始化 + toggle handler 扩展 + _open_word_docx 重置">
  <files>main.py</files></read_first>
    - main.py:5896 btn_mask_override (现有 PDF toolbar 控件)
    - main.py:8781 _toggle_mask_override_this_doc (现有 PDF toggle handler; D-05 扩展点)
    - main.py:10777 _open_word_docx (现有 word_data 初始化; D-05 重置点)
    - main.py:MainWindow.__init__ (字段初始化入口)
    - .planning/phases/03-word/03-CONTEXT.md D-05 锁定 (独立字段, 不污染 word_data)
    - .planning/phases/03-word/03-RESEARCH.md Open Q #1 resolution (独立 attr 而非 word_data[0])
    - .planning/phases/03-word/03-PATTERNS.md §_word_mask_override_this_doc 字段
  </read_first>
  <action>
    修改 main.py:MainWindow.__init__ (line 5896 btn_mask_override 创建行附近):
    - 在 btn_mask_override 创建后追加字段初始化:
      ```python
      # [NEW D-05] Word 端文档级 mask_override 独立字段 (Pitfall 6 + RESEARCH Open Q #1)
      self._word_mask_override_this_doc = None
      ```

    修改 main.py:_toggle_mask_override_this_doc (line 8781):
    - 在函数体末尾 (line 8797 DEBUG_MODE print 之后) 追加 Word 路径:
      ```python
      # [NEW D-05] Word 路径: 独立字段, 不污染 word_data 业务键空间 (Pitfall 6)
      self._word_mask_override_this_doc = "blackout" if checked else None
      if DEBUG_MODE:
          print(f"[PII OVERRIDE] _word_mask_override_this_doc = {self._word_mask_override_this_doc}")
      ```

    修改 main.py:_open_word_docx (line 10777):
    - 在函数末尾 (word_data 初始化完成后) 追加:
      ```python
      # [NEW D-05] 新文档加载时重置 Word 文档级 mask_override
      self._word_mask_override_this_doc = None
      ```

    锁定 D-05:
    - self._word_mask_override_this_doc 是独立 instance attr, 不在 word_data 业务键空间 (Pitfall 6 解决 word_data 多键结构与 page_data 单页结构不同的问题)
    - 读取点: _save_word 用 getattr(self, "_word_mask_override_this_doc", None)
    - 写入点: _toggle_mask_override_this_doc
    - 重置点: _open_word_docx
    - 视觉契约: btn_mask_override 与 PDF 共用同一 widget (UI-SPEC §Component Inventory #2 锁定; 与 PDF 紧邻摆放 8px 间距)
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_pii_redaction tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - main.py MainWindow.__init__ line 5896 附近出现 `self._word_mask_override_this_doc = None` (grep -n '_word_mask_override_this_doc' main.py, 期望 ≥3 行: __init__ / _toggle / _save_word read / _open_word_docx reset)
    - main.py:_toggle_mask_override_this_doc 函数体出现 `self._word_mask_override_this_doc = "blackout" if checked else None` (grep -n '_word_mask_override_this_doc = "blackout"' main.py)
    - main.py:_open_word_docx 函数体出现重置 (grep -n 'self._word_mask_override_this_doc = None' main.py 在 _open_word_docx 范围)
    - 既有 test_word_replace_rules + test_batch_word_replace 仍 PASS (D-17)
    - test_word_pii_redaction 端到端 reverse-extraction 测试 (Task 4) 验证 blackout 模式产物含 "[已脱敏]"
  </acceptance_criteria>
  <done>_word_mask_override_this_doc 字段就位; toggle 双路径就位; _open_word_docx 重置就位; 既有测试基线保持通过。</done>
</task>

<!-- ============================================================ -->
<!-- Task 3: PyInstaller 跨平台 hiddenimports 同步 -->
<!-- ============================================================ -->

<task type="modify" name="Task 3: PrivacyGuard_windows.spec + macOS build script hiddenimports 增 word_adapter">
  <files>packaging/windows/config/PrivacyGuard_windows.spec, packaging/macos/scripts/build_complete.sh</files></read_first>
    - packaging/windows/config/PrivacyGuard_windows.spec:130-172 (现有 hiddenimports 列表; D-14 同步点)
    - packaging/macos/scripts/build_complete.sh (macOS 平行; Phase 2 02-03 parity verified)
    - rollback_journal.md cp30 条目 (privacyguard.utils.security 导入回归; D-14 + Pitfall 7 预防)
    - .planning/phases/03-word/03-CONTEXT.md D-14 锁定 (PyInstaller hiddenimports 同步)
    - .planning/phases/03-word/03-PATTERNS.md §packaging/windows/config/PrivacyGuard_windows.spec 扩展范式
  </read_first>
  <action>
    修改 packaging/windows/config/PrivacyGuard_windows.spec:
    - 在 line 172 (现有最后一个 hiddenimports 条目 `'privacyguard.pii.validators.taxpayer_id',` 之后, 闭合 `])` 之前) 追加:
      ```python
      # Phase 3 (03-word): word_adapter 三函数模块 (D-14)
      'privacyguard.pii.word_adapter',
      ```

    修改 packaging/macos/scripts/build_complete.sh:
    - 找到现有 hiddenimports 数组 (Phase 2 02-03 parity verified; 应含 6 个 validator 条目)
    - 追加新条目: `privacyguard.pii.word_adapter` (具体行追加位置与 Windows spec 平行; 若 macOS 用不同语法如 HIDDENIMPORTS+=("...") 或类似, 沿用现有写法)
    - 如 macOS build script 不存在显式 hiddenimports 列表 (因 macOS 可能走 collect_submodules 自动扫描), 在该文件加注释行 `# Phase 3 word_adapter added to PrivacyGuard_windows.spec line 172 (D-14 parity)`

    锁定 D-14:
    - 零新数据文件 (word_adapter 三函数无 JSON 资源依赖)
    - 改动仅 spec 文本编辑, 触发重新 build 时 frozen exe 可正确导入 privacyguard.pii.word_adapter
    - cp30 回归预防: collect_submodules('privacyguard') 已自动扫描子模块, 但项目惯例显式列出所有 privacyguard 子模块 (Phase 2 02-03 parity 验证模式); Phase 3 沿用
  </action>
  <verify>
    <automated>grep -n 'privacyguard.pii.word_adapter' "G:/Project/PrivacyGuard/packaging/windows/config/PrivacyGuard_windows.spec" "G:/Project/PrivacyGuard/packaging/macos/scripts/build_complete.sh" 2>&1 | head -10; echo "--- expected: ≥2 lines (Windows spec + macOS script) ---"</automated>
  </verify>
  <acceptance_criteria>
    - packaging/windows/config/PrivacyGuard_windows.spec line 172 附近出现 `'privacyguard.pii.word_adapter',` (grep -n 'privacyguard.pii.word_adapter' PrivacyGuard_windows.spec)
    - packaging/macos/scripts/build_complete.sh 出现 `privacyguard.pii.word_adapter` (grep -n 'privacyguard.pii.word_adapter' build_complete.sh) 或显式注释行 (# Phase 3 word_adapter added)
    - spec 文件 Python 语法合法 (括号闭合; 不破坏现有 extend 列表结构)
    - test_package_imports 6 测试仍 PASS (Plan 1 扩展的懒加载纪律不被 spec 改动影响)
    - 282 既有测试 + Plan 1/2/3 新增测试保持通过 (D-16)
  </acceptance_criteria>
  <done>PyInstaller 跨平台 hiddenimports 同步就位; cp30 回归预防; Windows + macOS spec 文件均含 'privacyguard.pii.word_adapter' 条目。</done>
</task>

<!-- ============================================================ -->
<!-- Task 4: reverse-extraction 端到端测试 -->
<!-- ============================================================ -->

<task type="auto" name="Task 4: 新建 test_word_pii_redaction.py 端到端 reverse-extraction + AST 验证 _save_word 调用">
  <files>tests/unit/test_word_pii_redaction.py</files></read_first>
    - main.py::_save_word (Task 1 改后的真脱敏接入)
    - .planning/phases/03-word/03-01-word-adapter-PLAN.md (Plan 1 三函数)
    - tests/unit/test_pdf_pii_redaction.py (reverse-extraction 范本)
    - tests/unit/test_convergence.py::TestPiiWordAdapterConvergence (Plan 3 守卫范本)
    - privacyguard/pii/mask.py (mask_for_entity 分派表; partial_mask_id_card / partial_mask_phone 等)
    - privacyguard/pii/hits.py (PIIHit dataclass)
  </read_first>
  <action>
    新建 tests/unit/test_word_pii_redaction.py (按 PATTERNS.md §tests/unit/test_word_pii_redaction.py 范式):
    - import: unittest, os, tempfile, ast, from pathlib import Path, from docx import Document, from privacyguard.pii.engine import PIIEngine, from privacyguard.pii.word_adapter import (collect_pii_word_hits, locate_pii_hits_in_paragraph, apply_pii_replacements_to_docx), from tests.fixtures.fake_pii import fake_id_card, fake_phone (如不存在用固定字符串)
    - TestWordPiiRedaction 类含 5 个测试方法:
      1. test_redacted_docx_does_not_contain_original_secret: 构造 docx 含段落 + 身份证号 (fake_id_card); 调三函数 pipeline; 保存 out.docx; python-docx 重开 out.docx; 断言原身份证号 (secret_id) not in paragraph.text
      2. test_partial_mask_id_card_visible_in_output: 同上构造; 断言 partial mask 字符串 (如 "110101********1234") in paragraph.text (D-03 partial 模式)
      3. test_partial_mask_phone_visible_in_output: 构造含手机号 (fake_phone); 断言 partial mask (如 "138****5678") in paragraph.text
      4. test_blackout_mode_replaces_with_brackets: 构造 docx; 调三函数但 mode="blackout"; 断言产物段落含 "[已脱敏]" 且不含原手机号 (D-03 blackout 模式)
      5. test_paragraph_style_preserved_after_save (D-07): 构造 docx with style=Heading 1; 调三函数; 重开; 断言 paragraph.style.name == "Heading 1"

    TestSaveWordCallsPiiAdapter 类 (AST 验证 D-04 落地):
    - test_main_py_save_word_calls_apply_pii_replacements: read_text main.py; ast.parse; 找到 def _save_word(...); ast.walk find ast.Call with func.attr == "apply_pii_replacements_to_docx"; assertTrue found (D-04 验证)
    - test_main_py_save_word_calls_locate_pii_hits_in_paragraph: 类似, func.attr == "locate_pii_hits_in_paragraph"

    完整基线守护:
    - python3 -m unittest tests.unit.test_word_pii_redaction tests.unit.test_batch_word_replace tests.unit.test_word_replace_rules tests.unit.test_word_preview_highlight tests.unit.test_convergence tests.unit.test_word_worker_pii tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v (8 联合测试 PASS)
  </action>
  <verify>
    <automated>python3 -m unittest tests.unit.test_word_pii_redaction -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - tests/unit/test_word_pii_redaction.py 文件存在; TestWordPiiRedaction + TestSaveWordCallsPiiAdapter 2 类, ≥7 测试方法全 PASS (D-15 #3 + D-04 验证)
    - 测试覆盖: reverse-extraction 不含原敏感字符串 / partial_mask 字符串存在 / blackout 模式含 [已脱敏] / 段级样式保留 / AST 验证 _save_word 调用 adapter
    - 既有 test_batch_word_replace + test_word_replace_rules + test_word_preview_highlight + test_convergence + test_word_worker_pii + test_word_pii_adapter + test_package_imports 全部仍 PASS (D-17 + Plan 1/2/3 基线)
    - 282 既有测试基线保持通过 (D-16); 新测试 4 类合计约 13 个 (Plan 1: 10 + Plan 2: 5 + Plan 3: 8 + Plan 4: 7 = 30 新测试; 基线 282 → 312+)
  </acceptance_criteria>
  <done>reverse-extraction 端到端测试就位; 7 测试全 PASS; 既有 7 测试基线 + Plan 1/2/3 新增测试保持通过 (D-16 + D-17); Phase 3 测试基线从 282 升级到 312+。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| _save_word → word_adapter | main.py 持有 Document 句柄并传入 adapter; adapter 不 import docx (D-11 锁定) |
| _save_word → mask_for_entity | partial 模式调 mask_for_entity 分派表; blackout 模式写 "[已脱敏]" |
| _toggle_mask_override_this_doc → _word_mask_override_this_doc | 独立 instance attr (Pitfall 6); PDF + Word 路径同时写 |
| PyInstaller frozen exe → privacyguard.pii.word_adapter | hiddenimports 显式声明 (cp30 回归预防) |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-03-13 | T (Tampering) | _save_word PII 真脱敏路径漏配, 产物仍含原敏感字符串 | critical | mitigate | D-04 + D-15 #3 端到端 reverse-extraction; test_word_pii_redaction::test_redacted_docx_does_not_contain_original_secret 守; AST 验证 _save_word 调用 adapter |
| T-03-14 | I (Information Disclosure) | mask_override 字段污染 word_data 业务键空间, 触发 word_data[0] 误读 | medium | mitigate | D-05 锁定独立 attr; Plan 3 test_word_pii_adapter 验证 word_data 字段; Task 2 grep 验证 self._word_mask_override_this_doc 是 instance attr |
| T-03-15 | E (Elevation of Privilege) | PyInstaller frozen exe 启动报 ModuleNotFoundError: privacyguard.pii.word_adapter (cp30 回归) | high | mitigate | D-14 锁定 hiddenimports; Task 3 spec 同步; test_package_imports::test_import_privacyguard_does_not_load_word_adapter 单元代理 |
| T-03-16 | DoS | 跨 run 命中 replace 触发无限循环或段样式丢失 | medium | mitigate | D-07 锁定: 复用 apply_range_to_runs / replace_matches_in_paragraph 既有跨 run 处理; test_word_pii_redaction::test_paragraph_style_preserved_after_save 守段级样式 |

## Per-Task Security Verification

| Task | Threat Ref | Automated Check |
|------|------------|-----------------|
| Task 1 | T-03-13 | grep 验证 _save_word 调 apply_pii_replacements_to_docx; test_word_pii_redaction reverse-extraction PASS |
| Task 2 | T-03-14 | grep 验证 _word_mask_override_this_doc 是 instance attr; 既有 test_word_replace_rules / test_batch_word_replace 仍 PASS |
| Task 3 | T-03-15 | grep 验证 Windows + macOS spec 均含 'privacyguard.pii.word_adapter' |
| Task 4 | T-03-13 / T-03-16 | test_word_pii_redaction 7 测试全 PASS (含 reverse-extraction + 段样式保留 + AST 验证) |
</threat_model>

<verification>
[总体 Plan 4 验证]
- python3 -m unittest tests.unit.test_word_pii_redaction -v (Plan 4 范围: 2 TestClass, ≥7 测试全 PASS)
- python3 -m unittest tests.unit.test_batch_word_replace tests.unit.test_word_replace_rules -v (D-17 既有基线)
- python3 -m unittest tests.unit.test_word_preview_highlight tests.unit.test_convergence -v (Plan 3 基线)
- python3 -m unittest tests.unit.test_word_worker_pii tests.unit.test_word_pii_adapter -v (Plan 1/2 基线)
- python3 -m unittest tests.unit.test_package_imports -v (OPS-03 懒加载纪律)
- 282 既有测试基线保持通过 (D-16); 约 30 新测试加入, 基线 282 → 312+
- grep 验证 packaging/{windows,macos} 均含 privacyguard.pii.word_adapter (D-14)
</verification>

<success_criteria>
[Plan 4 完成判定]
1. _save_word 接入 apply_pii_replacements_to_docx 真脱敏 (D-04); reverse-extraction 端到端测试 PASS (D-15 #3)
2. self._word_mask_override_this_doc 独立 instance attr (D-05 + RESEARCH Open Q #1); _toggle 双路径扩展; _open_word_docx 重置
3. PyInstaller Windows spec + macOS build script hiddenimports 增 'privacyguard.pii.word_adapter' (D-14 + cp30 回归预防)
4. tests/unit/test_word_pii_redaction.py 2 TestClass + ≥7 测试全 PASS (D-15 #3 + D-04 AST 验证)
5. 282 既有测试 + Plan 1/2/3 新增测试保持通过 (D-16 + D-17)
6. partial / blackout 模式产物正确 (D-03): partial 含 partial_mask 字符串; blackout 含 "[已脱敏]"
7. 段级 paragraph.style.name 在 save 之后不变 (D-07)
8. Phase 3 测试基线从 282 升级到 312+ (D-16)
</success_criteria>

<output>
后续执行产: .planning/phases/03-word/03-04-save-and-packaging-SUMMARY.md (在 Wave 3 完成后由 executor 写入)
</output>

## Artifacts this phase produces

- `main.py` (MOD) — `_save_word` (line 12700): imports `locate_pii_hits_in_paragraph` + `apply_pii_replacements_to_docx`; computes `mode` from `_word_mask_override_this_doc`; paragraph + table cell loops call `apply_pii_replacements_to_docx(new_doc, {key: locations}, mode=mode)`
- `main.py` (MOD) — `_toggle_mask_override_this_doc` (line 8781): appends `self._word_mask_override_this_doc = "blackout" if checked else None`
- `main.py` (MOD) — `_open_word_docx` (line 10777): appends `self._word_mask_override_this_doc = None` (new doc reset)
- `main.py` (MOD) — `MainWindow.__init__` (around line 5896): appends `self._word_mask_override_this_doc = None` (field init)
- `packaging/windows/config/PrivacyGuard_windows.spec` (MOD) — line 172: appends `'privacyguard.pii.word_adapter',`
- `packaging/macos/scripts/build_complete.sh` (MOD) — appends `privacyguard.pii.word_adapter` to hiddenimports list (D-14 + macOS parity)
- `tests/unit/test_word_pii_redaction.py` (NEW) — classes `TestWordPiiRedaction` (5 tests: reverse-extraction, partial mask id/phone, blackout mode, paragraph style preserved), `TestSaveWordCallsPiiAdapter` (2 tests: AST verification of `_save_word` calling `apply_pii_replacements_to_docx` + `locate_pii_hits_in_paragraph`)
