# Phase 3: Word 文档接入识别引擎（双栏对比预览自动高亮） - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

在 Phase 1/2 已建好的 PDF + PII 引擎（已覆盖 9 类实体：身份证 18/15 位、手机号、银行卡、邮箱、USCC、VAT 发票号、纳税人识别号 18/15 位、银行账号）之上，把同一份 PII 引擎扩展到 Word 文档路径，让 Word 双栏对比预览自动高亮 PII 候选，并在保存 .docx 产物时按 `mask_strategy` 真脱敏（与 PDF 一致）。Word 处理路径接入识别引擎、识别候选在双栏对比预览中高亮（FMT-02），UX-01/UX-02 候选审阅列表在本阶段走最小可用形态（仅双栏预览高亮，不做完整侧栏审阅 UI）。

不在 Phase 3 范围（明确划线）：
- Excel / 图片文件接入 → Phase 4 / Phase 5
- 上下文型实体识别（姓名/机构/地址/业务敏感字段）→ Phase 6
- 候选审阅 UI 完整形态（按实体类型/来源筛选 + 分页）→ Phase 7
- 识别规则编辑 / 审计报告 / 真实文档基线 → Phase 8
- 批量 Word 替换（.doc/.docx）的每文件单独规则映射 — 当前开发现状由 CLAUDE.md 标识为后续 phase；Phase 3 仅保证单文件 Word 路径接入 PII，批量入口不强制接入（见 D-12）
- 切换到 `privacyguard/utils/config.py::ConfigManager` — 仍用 `SimpleConfig`（`main.py`）

</domain>

<decisions>
## Implementation Decisions

### 双栏预览合并优先级（G1）

- **D-01:** PII 命中并入"ocr 层"——`merge_word_matches_with_priority` 的优先级扩展为 `rule > manual > (ocr ∪ pii)`。原"ocr"层做最小改动：把 PII 命中作为"自动扫描"成员并入，合并函数仅扩展源，不改既有 rule/manual 分支。 — **Reversibility:** reversible — 单函数局部扩展，调用面不变。
- **D-02:** 同层（ocr ∪ pii）内部 PII 优先于 OCR：同一文本片段同时被 OCR 与 PII 命中时，PII 胜出（理由：PII 走过身份证 mod-11-2、Luhn、USCC mod-31-3 等校验位，质量高于 OCR 文本层原样命中）。合并函数对 `ocr_list + pii_list` 排序时按 `confidence_tier` 优先 + PII 来源加权。 — **Reversibility:** reversible — 排序键局部化在合并函数内。
- **D-03:** 重叠区 mask 文本走"分路径独立"：OCR 命中走纯黑框 `[已脱敏]`（保留 Phase 1 既有行为），PII 命中走 `partial_mask`（`110101********1234`），重叠区 PII partial_mask 胜出。 — **Reversibility:** reversible — `mask_for_entity` 分派表已存在（Phase 2 落地），扩展 word 端沿用同一表。

### Word 产物真脱敏（G3）

- **D-04:** Word 端保存 .docx 时**默认与 PDF 一致真脱敏**：PII 命中按 `mask_strategy` 实际写入产物。理由：Phase 1/2 的"识别即脱敏"是产品底线，"只高亮不写"会让 Word 端识别形同虚设；与 FMT-02 文字最小一致性也吻合（"识别候选在预览中高亮"是 UX 手段，不替代写入）。 — **Reversibility:** reversible — 调用点本地化在 `MainWindow.save_word` / 批量入口循环。
- **D-05:** 掩码模式双层配置：默认走 `pii_settings.per_entity_default`（Phase 2 D-13 已锁字段），文档级 override 通过 `self.word_data[0]["mask_override_this_doc"] = "partial" | "blackout"` 临时反转（与 Phase 2 D-12 PDF 同形态）。文档级 toggle 走主界面 toolbar，与 PDF 共用同一个 toggle 控件或紧邻摆放。 — **Reversibility:** costly — `mask_override_this_doc` 字段名一旦被 SettingsDialog 与 main_window 引用，跨多处修改。
- **D-06:** Word 真脱敏实现走"生成文本 + 外部调 Python-docx"路径：PIIHit 经 `locate_pii_hits_in_paragraph(hits, paragraph_text)` 拿到 `(hit, char_offset_in_paragraph_text)` 列表，调用方（`_ModularWordWorker` 之外或新 helper）拿 docx 文件 → 对其每一段按 G4-D 策略合并 run 后 `replace`。不在 `privacyguard/pii/word_adapter.py` 内 import python-docx，保持 Phase 1 "PII 引擎无 IO / 无格式 I/O" 原则。 — **Reversibility:** reversible — 边界清晰，import 仅一处。
- **D-07:** Python-docx 的 run 边界走"合并同段所有 run 后 replace"路径：`para.text` 是段内所有 run 字符串拼接的视图，`replace()` 默认按段内字符串匹配；PII 命中跨 run 时先调用 `paragraph._element.clear_content()` + 单 run 重建，保留段样式（`paragraph.style`）但不保留 run 内文字格式（粗体/斜体）。理由：保留段级样式 ≥ 失去 run 级格式；安全优先。 — **Reversibility:** reversible — 段样式保留与 run 重建本地化在 helper。

### Word 端 PII 命中位置定位（G4）

- **D-08:** PIIHit 仅作"内容描述"使用，WordAdapter 现场用 `hit.text` 在 `word_data[key]["text"]` 内做精确子串定位拿 `char_offset_in_paragraph_text`。理由：保持 Phase 1 D-05 PIIHit 字段锁（不增加字段、不重载 `page_offset` 语义），与 `privacyguard/pii/pdf_adapter.py::collect_pii_rects` 用 `page.search_for(raw_text)` 反向拿 QRectF 是同一范式。 — **Reversibility:** one-way — PIIHit 字段一旦锁，字段重命名/扩字段触发跨多处修改；本决策通过"adapter 现场换算"维持字段锁。 — **Rationale:** "Detection is format-independent" 原则要求一份 PIIHit 走四格式；adapter 边界做"内容→位置"换算是这一原则的标准实现。
- **D-09:** 同文本重复（`hit.text` 在同一段落出现多次）逐个展开为多个独立 PIIHit，每个 PIIHit 携带自己的 `char_offset`，所有出现位置均高亮均真脱敏。理由：用户期望所有敏感项都被处理，沉默丢失违反 Phase 1 D 决策"不可定位 hit 记录到 unresolved_hits + error_log（不静默丢弃）"。 — **Reversibility:** reversible — 展开逻辑本地化在 `locate_pii_hits_in_paragraph`。
- **D-10:** Word 端 PIIHit.source 复用 `"text"`（PIIHit.source 现有枚举 `Literal["text","image_block","full_page_ocr"]`，Word 文字层 = text 源）。PDF 文字层路径也用 `"text"`，Word 与 PDF 在 source 字段语义对齐。 — **Reversibility:** reversible — 枚举值复用，零修改。

### 模块归属与代码组织（G6）

- **D-11:** 新建 `privacyguard/pii/word_adapter.py`（与 `privacyguard/pii/pdf_adapter.py` 平级），提供对称三函数：
  - `collect_pii_word_hits(paragraph_text, engine: PIIEngine) -> List[PIIHit]`：复用 PII 引擎对单段文本识别
  - `locate_pii_hits_in_paragraph(hits: List[PIIHit], paragraph_text: str) -> List[Tuple[PIIHit, int]]`：用 `hit.text` 在段内精确子串定位，返回 `(hit, char_offset)`（D-09 多次展开）
  - `apply_pii_replacements_to_docx(docx_path: str, hit_locations: Dict[key, List[(PIIHit, int)]], mode: "partial"|"blackout")`：按段合并 run + replace（实际不在 word_adapter 内 import docx，签名只接 docx_path + hit_locations，由调用方持有 docx 句柄）
  - 文件内部**不** import `docx`（Python-docx）；调用方传入 `Document` 对象或 docx_path。理由：保持 Phase 1 "PII 引擎无 IO" 原则。
- **D-12:** PII 检测在 `_ModularWordWorker.run()` 内执行（与现有规则匹配并行），命中写入 `word_data[key]["pii"] = [PIIHit, ...]`。批量 Word 替换入口（`MainWindow` 批处理循环）在 Phase 3 显式跳过 PII 扫描（避免大批量卡顿），批量入口的 PII 接入归属后续 phase（CLAUDE.md 标识的"每文件单独规则映射"方向）。 — **Reversibility:** reversible — worker 单点扩展；批量入口 skip 是单一开关。
- **D-13:** `privacyguard/pii/__init__.py` 的 `_LAZY_IMPORTS` 注册 `word_adapter` 模块的三个公开函数（与现有 `pdf_adapter.collect_pii_rects` / `apply_pii_redactions` 平级）。`from privacyguard.pii import collect_pii_word_hits` 走 `__getattr__` 延迟加载，包导入期不拉起 word_adapter。 — **Reversibility:** reversible — `_LAZY_IMPORTS` 是注册表，添加条目不改语义。

### PyInstaller 与打包

- **D-14:** 新增 `privacyguard/pii/word_adapter.py` 需同步验证 PyInstaller `hiddenimports`（Windows spec + macOS spec）。`word_adapter.py` 不引入新数据文件（D-11 三函数签名均无 JSON 资源依赖），打包侧改动仅 `hiddenimports` 加 `privacyguard.pii.word_adapter`。 — **Reversibility:** reversible — spec 文件清单条目级修改。

### 测试与回归

- **D-15:** Phase 3 必须新增至少 4 类单元测试：
  1. `tests/unit/test_word_pii_adapter.py` —— `collect_pii_word_hits` / `locate_pii_hits_in_paragraph` / `apply_pii_replacements_to_docx` 三函数纯函数测试（含跨 run、跨段落、同文本重复、boundary 边界用例）
  2. `tests/unit/test_word_worker_pii.py` —— `_ModularWordWorker.run()` 接入 PII 后，`word_data[key]["pii"]` 与 `ocr` 键并存且内容正确
  3. `tests/unit/test_word_pii_redaction.py` —— 端到端 reverse-extraction：用 python-docx 打开保存后的 .docx，断言原敏感字符串不存在、partial_mask 字符串存在、段样式保留
  4. `tests/unit/test_word_preview_highlight.py` —— 双栏预览 JS DOM patch 接收 `pii` 数据后高亮命中；`merge_word_matches_with_priority` 在 `ocr + pii` 输入下产出预期合并结果
- **D-16:** Phase 3 必须保持 282/282 既有测试基线（CLAUDE.md 列出的 10 + Phase 1 增量 + Phase 2 增量）全部通过；新增 4 个 PII word 测试在 Phase 3 完成后进入基线（基线从 282/282 升级约 295+/295+）。 — **Reversibility:** one-way — 测试基线一旦升级，向下兼容约束生效。
- **D-17:** `_ModularWordWorker.run()` 改动后必须保持 `tests/unit/test_word_replace_rules.py` + `tests/unit/test_batch_word_replace.py` 全部通过（Word 替换规则与批量替换路径不被 PII 接入破坏）。Word 双栏预览 DOM patch 改动后真机打开一个对比模式验证右栏不再整块空白（CLAUDE.md §接手时约束）。

### Claude's Discretion

- PII 命中在右栏预览中的**颜色**选择——Phase 1 已用深红色作 PDF 自动识别。Word 端建议复用深红色（同色系），不引入新色，避免双栏预览颜色过多导致视觉杂乱。如有偏好可后续调整。
- `collect_pii_word_hits` 的 entity 命中是否在调用方做 `confidence_tier` 二次过滤（LOW 档候选仅入候选列表、不进真脱敏）——建议复用 Phase 2 已有的 `classify_hit` 范式，HIGH/MEDIUM 真脱敏、LOW 仅高亮（与 FMT-02 文字"识别候选在预览中高亮"对齐）。
- `apply_pii_replacements_to_docx` 是否在跨段命中时仍按段合并 run——建议保持"按段合并 run"，跨段命中仅替换各段内对应子串（与"按段粒度脱敏"的产品预期一致）；跨段同文本重复按 D-09 逐个展开。
- `_ModularWordWorker.run()` 接入 PII 后是否仍允许取消——建议保留现有 `isInterruptionRequested()` 检查点（PII 检测期间可取消）。

### Folded Todos

None — discussion produced no todos to fold.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目规划与需求
- `.planning/PROJECT.md` — 项目核心价值（打开文档自动列敏感项）、Constraints（零网络 / 纯本地规则 / 不破坏 79 基线 / 懒加载纪律 / `SimpleConfig` 在 `main.py`）
- `.planning/REQUIREMENTS.md` §FMT-02 / §UX-01 / §UX-02 / §OPS-03 / §OPS-07 — Phase 3 覆盖的 v1 需求 acceptance criteria
- `.planning/ROADMAP.md` §Phase 3 — Word 文档接入识别引擎；Success Criteria（双栏高亮 / 真脱敏与 PDF 一致 / 不破坏 282 测试基线 / PyInstaller 跨平台）
- `.planning/STATE.md` — Decisions 段落「Detection is format-independent / 新数据存进现有 dict 的新 key / 每个格式走垂直 MVP 切片」；Open Questions 段落

### Phase 1/2 既有决策（必读）
- `.planning/phases/01-pdf/01-CONTEXT.md` — PIIHit dataclass 字段锁（D-05）/ PII 引擎子包架构 / `pii_settings` 字段 / 真脱敏路径 / 懒加载纪律
- `.planning/phases/01-pdf/01-VERIFICATION.md` — Phase 1 must-haves 验证基线
- `.planning/phases/02-pdf/02-CONTEXT.md` — partial mask helper / `mask_for_entity` 分派表 / `pii_settings.per_entity_default` / `mask_override_this_doc` 文档级 override / PyInstaller datas 同步
- `.planning/phases/02-pdf/02-VERIFICATION.md` — Phase 2 must-haves 验证基线

### 核心实现参考（必读）
- `privacyguard/pii/__init__.py` — `_LAZY_IMPORTS` + `__getattr__` 懒加载范本；Phase 3 新增 word_adapter 函数必须在此注册
- `privacyguard/pii/engine.py` — `PIIEngine` detect pipeline；Phase 3 直接复用
- `privacyguard/pii/hits.py` — `PIIHit` / `TextUnit` dataclass（D-05 字段顺序锁，Phase 3 不扩字段）
- `privacyguard/pii/pdf_adapter.py` — `collect_pii_rects`（`page.search_for(raw_text)` 范本）/ `apply_pii_redactions` / `write_partial_masks`；Phase 3 word_adapter 对称范式
- `privacyguard/pii/mask.py` — `mask_for_entity` 分派表；Phase 3 word 端 mask 沿用
- `privacyguard/pii/data/rules.json` — Phase 1/2 已扩展 9 类 entity；Phase 3 不需扩展键

### Word 路径既有代码（必读）
- `privacyguard/workers/word_worker.py:34-180` — `_ModularWordWorker` 类（D-12 接入点）
- `privacyguard/workers/word_worker.py:108 _find_matches` — 现有规则匹配；Phase 3 新增 PII 检测阶段与它并行
- `main.py:863 merge_word_matches_with_priority` — 右栏合并优先级函数（D-01 扩展源）
- `main.py:10798-10830` — `word_data` schema 初始化（D-12 新增 `pii` 键）
- `main.py:11975-12360` — `_build_word_html_from_docx` 与 `data-key` 注入（cp27 修复点）
- `main.py:12237-12324` — BeautifulSoup / 正则注入 `data-key`（cp27 修复点）
- `main.py:12252-12360` — DOM patch 写入点（cp27 修复点）
- `main.py:11647-11700` — 双栏预览加载与增量 patch 调用点

### 既有测试范本（必读）
- `tests/unit/test_word_replace_rules.py` — Word 替换规则纯函数测试范本
- `tests/unit/test_batch_word_replace.py` — 批量 Word 替换测试范本
- `tests/unit/test_pii_engine.py` — PIIEngine 9 类 entity 命中测试
- `tests/unit/test_pii_validators.py` — validator 纯函数测试
- `tests/unit/test_pdf_pii_redaction.py` — reverse-extraction 测试范本（Phase 3 word 端沿用同一思路）
- `tests/unit/test_pdf_pii_pipeline.py` — 端到端 pipeline 测试
- `tests/unit/test_app_config.py` — `pii_settings` 字段读取测试
- `tests/unit/test_convergence.py` — `main.py` / `privacyguard/*` 不分叉强制回归
- `tests/unit/test_package_imports.py` — 懒加载 + PyInstaller 兼容性强制回归
- `tests/unit/test_pdf_text_hit_dedup.py` — 文字层去重强制回归
- `tests/unit/test_mixed_pdf_ocr.py` — OCR 坐标换算强制回归

### 配置与打包
- `config.json:19-82` — 现有 `redaction.default_rules`；`pii_settings` 已含 4 字段
- `config.json.template` — 同步新增字段的模板
- `rollback_journal.md` cp27（Word 预览 DOM patch 边界修复点）/ cp30（PyInstaller `privacyguard.utils.security` 导入回归）— Phase 3 双栏预览改动与新增模块都需回归验证
- `packaging/windows/config/PrivacyGuard_windows.spec` — Windows PyInstaller spec；新增 `privacyguard.pii.word_adapter` 需加入 `hiddenimports`
- `packaging/macos/scripts/build_complete.sh` — macOS 构建脚本；同上
- `docs/packaging/windows-packaging-guide.md` — Windows 打包流程
- `docs/packaging/macos-packaging-guide.md` — macOS 打包流程

### CLAUDE.md 关键约束（必读）
- `CLAUDE.md` §当前生效的配置路径 — `SimpleConfig` 在 `main.py` 中仍是运行时配置；不切换到 `ConfigManager`
- `CLAUDE.md` §OCR / 识别引擎依赖的懒加载约束 — `privacyguard/` 包导入必须保持懒加载；新增 `privacyguard.pii.word_adapter` 必须沿用
- `CLAUDE.md` §主架构现状 — `main.py` 仍是单体，新逻辑放 `privacyguard/` 不放 `main.py`
- `CLAUDE.md` §版本号单一来源 — `version.txt`；Phase 3 完成时不改版本号（仅 Phase 3 内部交付），版本号升级在阶段合并时统一处理
- `CLAUDE.md` §当前开发方向 — Phase 3 完成后默认下一阶段仍是「每文件单独规则映射 / 批量规则集模板管理 / 替换后预览按来源筛选高亮」

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PIIEngine`（`privacyguard/pii/engine.py:59`）** — 现有 detect pipeline：flatten → iter candidates → validate → resolve overlap。Phase 3 直接复用，**零修改**。
- **`PIIHit`（`privacyguard/pii/hits.py:15`）** — D-05 字段锁：entity_type / page_offset / page_length / page_rect / confidence_tier / source / mask_strategy / normalized / validator_passed。Phase 3 不增字段、不重载语义。
- **`collect_pii_rects`（`privacyguard/pii/pdf_adapter.py`）** — `page.search_for(raw_text)` 反向拿 QRectF 范本；Phase 3 word_adapter 的 `locate_pii_hits_in_paragraph` 是同一范式的 word 端形态。
- **`apply_pii_redactions`（`privacyguard/pii/pdf_adapter.py:37`）** — 现有真脱敏调用范本；Phase 3 word_adapter 提供对称的 `apply_pii_replacements_to_docx`。
- **`mask_for_entity`（`privacyguard/pii/mask.py:23`）** — 按 entity_type 分派掩码函数；Phase 3 word 端沿用同一表。
- **`classify_hit`（`privacyguard/pii/confidence.py`）** — 档位判定范本；Phase 3 word 端沿用（Claude's Discretion 项）。
- **`_ModularWordWorker`（`privacyguard/workers/word_worker.py:11`）** — 现有逐段落/逐表格 cell 扫描的 QThread worker；D-12 接入点扩展。
- **`_find_matches`（`privacyguard/workers/word_worker.py:108`）** — 现有规则匹配；D-12 与 PII 检测并行。
- **`merge_word_matches_with_priority`（`main.py:863`）** — 现有右栏合并优先级函数；D-01 扩展源（ocr ∪ pii）。
- **`MainWindow.word_data`（`main.py:10798-10830`）** — `word_data[key] = {"type","text","ocr","manual",...}`；D-12 新增 `pii` 键。
- **`_word_data_lock`（`main.py:5153`）** — 现有写入保护；D-12 沿用。
- **`tests/unit/test_word_replace_rules.py`** — 范本；Phase 3 沿用 FakeDocument 形态。
- **`_LAZY_IMPORTS`（`privacyguard/pii/__init__.py:38`）** — 现有 12 个导出项；D-13 新增 word_adapter 三函数。
- **`pii_settings`（config.json）** — Phase 2 已含 4 字段（engine_enabled / auto_redact / require_confirmation / per_entity_default）；Phase 3 不新增全局字段。

### Established Patterns
- **Lazy-load discipline:** `privacyguard/__init__.py` 与 `privacyguard/workers/__init__.py` 用 `__getattr__` 延迟加载；新增 `privacyguard/pii/word_adapter` 必须在自己的引用点（`privacyguard/pii/__init__.py::_LAZY_IMPORTS`）注册，避免 `import privacyguard` 时拉起。
- **Pure-function adapter pattern:** `collect_*_hit_boxes` / `apply_pii_redactions` / `write_partial_masks` 全部纯函数 + dependency-injection；word_adapter 三函数沿用。
- **Detection is format-independent:** 一份 PIIHit 走四格式；adapter 边界做格式分支。word_adapter 是第二个 adapter 实现，与 pdf_adapter 形态对齐。
- **Two-tier worker pattern:** `main.py` 中 `OCRWorker(_ModularOCRWorker)` / `WordWorker(_ModularWordWorker)` 仅做薄兼容层；Phase 3 不新增 worker，沿用 Phase 1 既有 PII worker 设计。
- **Word data dict as single source of truth:** `word_data[key]["pii"]` 与现有 `ocr` / `manual` 键并存（D-12）；UI 与导出循环都从这一处读。
- **Reverse-extraction as safety net:** 真脱敏的最终验证必须由独立通道（`python-docx` 重开 .docx 后文本提取）确认敏感字符串不存在；D-15 测试 #3 沿用。
- **PIIHit frozen dataclass with field order lock:** Phase 1 D-05 锁定字段顺序；Phase 3 不扩字段、不重载语义（D-08）。
- **Document-level override pattern:** Phase 2 D-12 已确立 `mask_override_this_doc` 临时覆盖；Phase 3 word 端沿用同一字段名（D-05）。
- **`data-key` DOM patch 局部更新（cp27 修复点）:**` 右栏合并后按 key 局部 patch，左/右栏各自记录已加载源；Phase 3 新增 `pii` 数据按 key 增量 patch（D-15 测试 #4 验证）。

### Integration Points
- **`_ModularWordWorker.run()`（`privacyguard/workers/word_worker.py:34`）** — D-12 接入点：在 `_find_matches` 调用之后、`word_data[key]["ocr"]` 写入之后，增加 `pii_hits = collect_pii_word_hits(text, engine)` 与 `word_data[key]["pii"] = pii_hits`。
- **`merge_word_matches_with_priority`（`main.py:863`）** — D-01 扩展源：合并 `ocr_list + pii_list`。
- **`MainWindow.save_word`** — D-04 接入点：保存 .docx 前调 `apply_pii_replacements_to_docx(...)`。
- **`MainWindow` toolbar** — D-05 接入点：toolbar 加「本文件使用全遮蔽」toggle 控件（与 PDF 共用或紧邻摆放）。
- **`MainWindow._build_word_html_from_docx`（`main.py:5363`）** — 现有 HTML 构建；Phase 3 PII 数据通过同一 DOM patch 路径进入右栏（D-15 测试 #4 验证）。
- **`config.json` + `config.json.template`** — 同步：Phase 3 不新增全局 `pii_settings` 字段；如有新增文档级 override 字段则同步。
- **`privacyguard/pii/__init__.py`** — D-13 注册 word_adapter 三函数。
- **`packaging/windows/config/PrivacyGuard_windows.spec`** + **`packaging/macos/scripts/build_complete.sh`** — D-14 同步 `hiddenimports = [..., "privacyguard.pii.word_adapter"]`。
- **`tests/unit/test_convergence.py`** — 沿用，Phase 3 不引入新的分叉风险（D-12 word_worker.run 内改动仍受收敛检查保护）。

</code_context>

<specifics>
## Specific Ideas

- **word_adapter 三函数命名：** `collect_pii_word_hits` / `locate_pii_hits_in_paragraph` / `apply_pii_replacements_to_docx`，与 `pdf_adapter.collect_pii_rects` / `apply_pii_redactions` / `write_partial_masks` 命名风格一致；测试文件 `test_word_pii_adapter.py` 与 `test_pdf_pii_redaction.py` 命名一致。
- **位置定位策略选择理由：** Phase 1 D-05 字段锁 + "Detection is format-independent" 原则双重约束下，最稳的策略是 PIIHit 仅作内容描述、adapter 边界做"内容→位置"换算。Word 端用 `paragraph.text.find(hit.text, start_offset)` 顺序扫描（类似 PDF `page.search_for` 的反向定位）拿 char_offset；同文本重复按 D-09 逐个展开。
- **run 合并后样式保留：** Python-docx 的 `paragraph._element.clear_content()` 后重建 run，会丢失原 run 内文字格式（粗体/斜体/字体）。D-07 决策保留段级样式（`paragraph.style`）、不保留 run 级格式。理由：保留段级样式 ≥ 失去 run 级格式；真脱敏产品底线高于格式完美。
- **批量入口 skip 策略：** Phase 3 在批量 Word 替换入口显式 skip PII 扫描，避免大批量卡顿（D-12）。批量入口的 PII 接入归属后续 phase（CLAUDE.md 标识"每文件单独规则映射"方向）。
- **PII 命中颜色：** Phase 1 PDF 端用深红色作自动识别；Phase 3 建议 word 端复用深红色（同色系），不引入新色。如有偏好可后续调整（Claude's Discretion）。
- **PII 真脱敏与现有 word_replace_rules 的关系：** 现有 word_replace_rules 是用户手输关键词/正则的会话级规则（Phase 1 前已存在）；PII 引擎是 Phase 1/2 新建的规则引擎。两套规则集独立——PII 命中写入 `word_data[key]["pii"]`，与 word_replace_rules 命中的"rule"层在 D-01 合并优先级下共存。
- **G3 默认与 PDF 一致的依据：** Phase 1/2 决策"识别即脱敏"是产品底线；Word 端只高亮不写会让识别形同虚设；FMT-02 文字"识别候选在预览中高亮"是 UX 手段，与产物真脱敏不互斥。

</specifics>

<deferred>
## Deferred Ideas

- **候选审阅 UI 完整形态（按实体类型/来源筛选 + 分页）** — Phase 7 UX-01/UX-02 主线；Phase 3 仅做双栏预览高亮。
- **识别规则编辑 UI** — Phase 8 UX-07
- **审计报告（JSON）** — Phase 8 OPS-01
- **完整行政区划词典 ~70 万条** — Phase 6 ADV-01；Phase 3 不引入
- **本地 NER 深度学习模型** — PROJECT.md 明确 Out of Scope
- **v38 UI 抛光与批量 Word 每文件单独规则映射** — PROJECT.md / CLAUDE.md 明确让位/归属后续 phase
- **批量 Word 替换入口的 PII 接入** — D-12 在 Phase 3 显式 skip；归属后续 phase
- **Word 端替换后预览按来源筛选高亮（rule / manual / ocr / pii）** — Phase 7 后续功能；CLAUDE.md 已标识
- **BIC（SWIFT Code）识别** — Phase 2 已 deferred；Phase 3 不引入
- **跨段同文本重复的合并策略优化** — 当前 D-09 逐个展开；如未来需要按段聚合可单独优化

</deferred>

---

*Phase: 3-Word*
*Context gathered: 2026-08-11*