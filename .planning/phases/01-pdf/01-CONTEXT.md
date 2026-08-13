# Phase 1: PDF 自动识别身份证号与手机号并真脱敏 - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

首个端到端垂直切片：用户打开任意 PDF（文字型 / 图片型 / 混合型 / 扫描型），工具自动扫描并标出 18 位 / 15 位身份证号与中国大陆手机号；导出后敏感内容在 PDF 文本层不可通过 `pdftotext` 或 `page.get_text()` 还原。识别与脱敏全程纯本地，UI 在 500 页规模下保持响应并可取消。

不在 Phase 1 范围（明确划线）：
- 银行卡 / 邮箱 / 财税票据识别 → Phase 2
- Word / Excel / 图片文件支持 → Phase 3 / 4 / 5
- 姓名 / 机构 / 地址 / 业务敏感字段识别 → Phase 6
- 候选审阅 UI / 撤销栈 → Phase 7
- 识别规则编辑 / 审计报告 / 跨平台打包验证 / 真实文档基线 → Phase 8

</domain>

<decisions>
## Implementation Decisions

### 识别路径与引擎架构

- **D-01:** OCR 三路径全纳入 Phase 1 — 文字层（PyMuPDF `page.get_text`）、混合型 PDF 嵌入图片块（`collect_image_block_ocr_hits`）、纯扫描型 PDF 的整页回退 OCR。三个路径汇入同一份 PII 引擎输出。 — **Reversibility:** costly — 三个路径任一遗漏都会让「打开任意 PDF」承诺落空；后续 phase 需要再补一个路径成本高于一次做齐。
- **D-02:** 新增 `privacyguard/pii/` 子包作为独立子系统（与 `privacyguard/ocr/` 平级），包含 `engine.py` / `rules.py` / `validators.py` / `hits.py` / `__init__.py` 懒加载入口。引擎无 Qt、无线程、无格式 I/O；apply 阶段由各 PDF 适配器边界处理。 — **Reversibility:** reversible — 子包边界清晰，后续 phase 可在同位置扩展。
- **D-03:** 新增纯函数 `collect_full_page_ocr_hits(page, recognize_fn, calculate_rect_fn)`，与现有 `collect_text_pdf_hit_boxes` / `collect_image_block_ocr_hits` 保持同一种 dependency-injection 形态（参考 `privacyguard/ocr/mixed_pdf.py:76` 的 `recognize_fn` / `calculate_rect_fn` / `clip_to_page_rect_fn` 注入点）。 — **Reversibility:** reversible — 仅新增一个纯函数，不动现有调用面。
- **D-04:** PII 引擎独立维护，**不动** `config.json.default_rules` 中的身份证 / 手机号 / 邮箱 / 银行卡 / 日期 / 印章正则，也不修改 `SimpleConfig` / `SettingsDialog` 已有的规则编辑 tab。两条规则集共存：现有 `default_rules` 仍由旧文本层 + 图片块 worker 消费；PII 引擎产出的命中通过新 `page_data[page]["pii"]` 键接入。 — **Reversibility:** reversible — 两套规则集各自独立，后续可选择性合并。

### 数据结构与契约

- **D-05:** PIIHit 定义为 `dataclass`：`entity_type: str`、`page_offset: int`、`page_length: int`、`page_rect: QRectF`、`confidence_tier: Literal["HIGH","MEDIUM","LOW"]`、`source: Literal["text","image_block","full_page_ocr"]`、`mask_strategy: str`。存进 `page_data[page_num]["pii"]`，与现有 `"ocr"` / `"manual"` 键并存。 — **Reversibility:** costly — dataclass 字段一旦在测试或下游消费者中固化，重命名/重构会触及多处；建议字段顺序与命名从一开始就稳定。
- **D-06:** 字符级 offset 采用「整页文本字符串偏移」（`page_offset` / `page_length`），而不是仅存 `QRectF`。OCR 路径输出的 offset 通过 `iter_ocr_lines` + 文本字符串拼接得到；文本层路径直接使用 `page.get_text()` 的字符串索引。 — **Reversibility:** reversible — offset 与 rect 通过同一构造路径产出，可同步回算。

### 真脱敏触发与设置

- **D-07:** 默认自动真脱敏：打开 PDF 后 PII 引擎在后台跑，HIGH 档命中直接以红色框显示在原位，用户点「保存」时一同真脱敏（沿用现有 `add_redact_annot + apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` 路径，`main.py:12364-12373`）。 — **Reversibility:** reversible — 默认行为可被 `pii_settings.require_confirmation` 切换。
- **D-08:** 新增 `config.json.pii_settings` 段（字段：`engine_enabled: bool = true`、`auto_redact: bool = true`、`require_confirmation: bool = false`），SettingsDialog 新增「隐私识别」tab 包含这三个开关。`require_confirmation = true` 时，HIGH 档命中先进入候选面板（Phase 7 占位，Phase 1 用最小可用确认对话框承载）。 — **Reversibility:** one-way — `pii_settings` 一旦被测试与 UI 引用，字段重命名会触发跨多处修改；建议 Phase 1 命名从一开始就稳定。
- **D-09:** `pii_settings` 改动需同步 `config.json.template` 与 `tests/unit/test_app_config.py`；新增的 SettingsDialog tab 不动现有 4 个 tab 结构。

### 规则存储与打包

- **D-10:** PII 引擎内部规则（身份证 / 手机号正则、段号白名单、置信度档位边界）存放在外部 JSON 数据文件 `privacyguard/pii/data/rules.json`，模块加载期通过 `privacyguard.utils.security.resource_path` 读取。 — **Reversibility:** one-way — 外部 JSON 资源一旦写入 PyInstaller spec 的 `datas=[]`，后续切回硬编码需同步改打包脚本；cp30 修复过的 `privacyguard.utils.security` 回归需要在 Phase 1 重新验证。 — **Rationale:** 用户选择外部 JSON 以支持后续 Phase 8 用户自定义词典导入 UX-07 的需求；需在 Phase 1 同步验证 Windows / macOS PyInstaller `datas` 与 `hiddenimports`。
- **D-11:** 手机号段号白名单在 Phase 1 实施前需要查 MIIT 最新公告交叉验证（166/198/199、190/192/196/197、虚拟运营商段、14X 物联网排除），验证完成后写入 `rules.json`。Phase 1 接受「暂用 2026-Q1 已知号段 + 14X 排除」基线；后续 phase 可热更新。

### 测试与验证

- **D-12:** Phase 1 必须新增至少 3 类单元测试：① `privacyguard/pii/validators.py` 的身份证 mod-11-2 校验（含大小写 X）与手机号段号白名单；② `privacyguard/pii/engine.py` 对合成 PDF 文本（身份证 + 手机号 + 噪声）的命中 + 档位判定；③ `tests/unit/test_pdf_pii_redaction.py` 通过 `pdftotext` / `page.get_text()` 反向提取断言敏感字符串消失。 — **Reversibility:** reversible — 新增测试文件，独立于 79/79 基线。
- **D-13:** Phase 1 必须保持 79/79 既有测试基线（CLAUDE.md 列出的 10 个 unittest 模块）全部通过，包括 `test_pdf_text_hit_dedup`（文字层去重逻辑不被破坏）、`test_mixed_pdf_ocr`（图片块 OCR 坐标换算）、`test_package_imports`（懒加载）、`test_convergence`（`main.py` / `privacyguard/*` 不分叉）。
- **D-14:** 反向提取测试使用 `pdftotext`（系统命令，poppler-utils 提供）或 `fitz.open().get_text()` 二选一；优先 `fitz` 路径以避免在 CI 上额外安装 poppler。若选 `pdftotext`，需在测试 skip 逻辑中检测命令可用性。

### Claude's Discretion

- PIIHit dataclass 字段顺序与默认值（`confidence_tier` 默认 `"HIGH"` 还是 `"MEDIUM"`，建议 `HIGH` 因 Phase 1 全部走校验位严格路径）。
- `iter_ocr_lines` 与 PII 引擎的对接函数命名（建议 `pii_engine.recognize_lines(text_or_image) -> List[PIIHit]`）。
- `collect_full_page_ocr_hits` 的扫描比例默认值（与现有 `mixed_pdf.py` 对齐，建议 `1.5`）。
- Phase 1 测试 PDF 生成器位置（建议 `tests/e2e/create_pii_test_pdf.py`，与现有 `tests/e2e/create_test_pdf.py` 对齐）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目规划与需求
- `.planning/PROJECT.md` — 项目核心价值（打开文档自动列敏感项）、Active Requirements 列表、Constraints（零网络 / 纯本地规则 / 不破坏 79 基线）
- `.planning/REQUIREMENTS.md` — ENGINE-01..08、NUM-01..03、NUM-05、FMT-01、SAFE-01..02、OPS-03、OPS-07 的完整 acceptance criteria
- `.planning/ROADMAP.md` §Phase 1 — 首个端到端垂直切片定义、Success Criteria 五条
- `.planning/STATE.md` — Decisions 段落：「Detection is format-independent」「新数据存进现有 dict 的新 key」「每个格式走垂直 MVP 切片」；Open Questions 段落：手机号段号白名单、词典 LICENSE 审查

### 既有架构与代码地图
- `.planning/codebase/STRUCTURE.md` — 目录布局与「Where to Add New Code」指引
- `.planning/codebase/ARCHITECTURE.md` — 系统分层、Worker/OCR Helper/Utility 三层结构、Anti-Patterns（重复实现、`ConfigManager` 误用、eager import、绕过 worker 兼容层、`main.py` UI 堆积）
- `.planning/codebase/CONCERNS.md` — 已知 Bug（DOC 转换临时目录生命周期）、Performance Bottlenecks（OCR 渲染开销）、Missing Critical Features（每文件单独规则映射）、Test Coverage Gaps

### 核心实现参考（必读）
- `main.py:12340-12395` — 现有 PDF 真脱敏写入循环：`add_redact_annot` + `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` + `garbage=4` + `deflate=True` + `clean=True` 的完整模式；Phase 1 只需把 `pii_list` 并入 `ocr_list + manual_list`
- `main.py:4885-4926` — `MainWindow.page_data` / `word_data` / `_word_data_lock` / `worker_lock` 的状态结构
- `privacyguard/ocr/text_pdf.py:1-50` — `iter_unique_text_matches` + `collect_text_pdf_hit_boxes` 的纯函数形态（dependency-injection 模式）
- `privacyguard/ocr/mixed_pdf.py:76` — `collect_image_block_ocr_hits` 的 dependency-injection 形态（`recognize_fn` / `calculate_rect_fn` / `clip_to_page_rect_fn`），是 `collect_full_page_ocr_hits` 的范本
- `privacyguard/ocr/base.py:12-60` — `CharInfo` / `OCRResult` / `BaseOCREngine` dataclass + ABC 范本，是 PIIHit dataclass 的设计参考
- `privacyguard/workers/ocr_worker.py:35-447` — `_ModularOCRWorker` 线程结构、cancellation 检查、page_result_signal 发射模式
- `privacyguard/__init__.py:1-84` — `_LAZY_IMPORTS` + `__getattr__` 懒加载范本；新 `privacyguard.pii.*` 子包必须沿用同一模式
- `privacyguard/utils/security.py:110` — `resource_path` 用于 PyInstaller 资源解析；新 JSON 数据文件读取必须走这里

### 既有测试范本（必读）
- `tests/unit/test_pdf_text_hit_dedup.py:1-40` — 纯函数测试范本（FakePage 注入 + 去重断言）；`collect_full_page_ocr_hits` 与 PII 引擎测试沿用同一形态
- `tests/unit/test_mixed_pdf_ocr.py` — OCR 坐标换算与去重的强制回归测试
- `tests/unit/test_package_imports.py` — 懒加载 + PyInstaller 兼容性的强制回归测试（任何 `privacyguard.*` 新增模块必须保证通过）
- `tests/unit/test_convergence.py` — `main.py` / `privacyguard/*` 不分叉的强制回归测试

### 配置与打包
- `config.json:19-82` — 现有 `redaction.default_rules` 五条规则（Phase 1 不动）；新增 `pii_settings` 字段位置与格式参考
- `config.json.template` — 同步新增字段的模板
- `rollback_journal.md` cp30 条目 — `privacyguard.utils.security` 导入失败回归；新增 JSON 资源文件需同步验证 PyInstaller `datas` / `hiddenimports`
- `packaging/windows/config/PrivacyGuard_windows.spec` — Windows PyInstaller spec；新增 JSON 数据文件需加入 `datas`
- `packaging/macos/scripts/build_complete.sh` — macOS 构建脚本；同上
- `docs/packaging/windows-packaging-guide.md` — Windows 打包流程
- `docs/packaging/macos-packaging-guide.md` — macOS 打包流程

### CLAUDE.md 关键约束（必读）
- `CLAUDE.md` §当前生效的配置路径 — `SimpleConfig` 在 `main.py` 中仍是运行时配置；不切换到 `ConfigManager`
- `CLAUDE.md` §OCR 依赖的懒加载约束 — `privacyguard/` 包导入必须保持懒加载；新增 PII 子包必须遵守
- `CLAUDE.md` §主架构现状 — `main.py` 仍是单体，新逻辑放 `privacyguard/` 不放 `main.py`
- `CLAUDE.md` §版本号单一来源 — `version.txt`；Phase 1 完成时不改版本号（仅 Phase 1 内部交付），版本号升级在阶段合并时统一处理

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `collect_text_pdf_hit_boxes(page, patterns, page_text=None)` (`privacyguard/ocr/text_pdf.py:28`) — 文字层唯一命中框收集纯函数；Phase 1 改造方向：第二个参数从 `patterns` 改为 `pii_engine: PIIEngine`，内部走 PII 引擎拿到 `List[PIIHit]`，再对每个命中调用 `page.search_for(raw_text)` 拿 QRectF。
- `collect_image_block_ocr_hits(...)` (`privacyguard/ocr/mixed_pdf.py:76`) — 图片块 OCR + 局部到页面坐标换算的范本；`collect_full_page_ocr_hits` 直接复用 `iter_ocr_lines` + `calculate_rect_fn` + `clip_to_page_rect_fn` 注入点。
- `_ModularOCRWorker.run()` (`privacyguard/workers/ocr_worker.py:347`) — 已有的逐页 `page_result_signal.emit(page_idx, rects)` 发射；Phase 1 增加 `pii_list` 字段，或另起 `pii_signal.emit(page_idx, [PIIHit, ...])`。
- `MainWindow.page_data` (`main.py:4908`) — 字典结构：`page_data[page_num] = {"ocr":[QRectF...], "manual":[QRectF...]}`；Phase 1 新增 `"pii":[PIIHit...]` 键，不改既有键。
- `MainWindow` PDF 保存循环 (`main.py:12354-12385`) — 已有的真脱敏循环；Phase 1 扩展为 `for r in ocr_list + manual_list + pii_list:`（`PIIHit.page_rect` 直接转 `fitz.Rect`）。
- `SinglePageCanvas.paintEvent` (`main.py:4100`) — 已有的高亮绘制循环；Phase 1 扩展绘制 PII 命中（颜色可与 `ocr` / `manual` 区分，例如紫色或深红色以表达「自动识别」）。
- `validate_safe_path` / `resource_path` (`privacyguard/utils/security.py`) — 新 JSON 数据文件读取路径必须走 `resource_path` 以兼容 PyInstaller。
- `tests/unit/test_pdf_text_hit_dedup.py` — FakePage 注入 + 纯函数断言范本；PII 引擎单元测试沿用。

### Established Patterns
- **Lazy-load discipline:** `privacyguard/__init__.py` 与 `privacyguard/workers/__init__.py` 用 `__getattr__` 延迟加载；新增 `privacyguard.pii` 子包必须在自己的 `__init__.py` 中实现同一形态，避免 `import privacyguard` 时拉起 PII 引擎或 JSON 资源。
- **Dependency-injection for OCR helpers:** `collect_*_hit_boxes` 函数都接收 `recognize_fn` / `calculate_rect_fn` / `clip_to_page_rect_fn` 注入；`collect_full_page_ocr_hits` 沿用同一形态。
- **Two-tier worker pattern:** `main.py` 中 `OCRWorker(_ModularOCRWorker)` / `WordWorker(_ModularWordWorker)` 仅做薄兼容层注入运行时配置；Phase 1 的 `PIIScanWorker` 若需运行时依赖（如 `pii_settings`），同样走薄兼容层。
- **Page data dict as single source of truth:** workers 通过 `page_result_signal` 写入 `MainWindow.page_data`；UI 与导出循环都从这一处读；Phase 1 的 PII 命中遵守同一契约（通过新键）。
- **Reverse-extraction as safety net:** 真脱敏的最终验证必须由独立通道（`pdftotext` 或 `fitz.get_text()` 反向）确认敏感字符串不存在；视觉脱敏（仅绘制黑框）已被项目明令禁止（PROJECT.md Out of Scope）。

### Integration Points
- `MainWindow._start_ocr_scan` (`main.py:4191` 附近) — 启动扫描的入口；Phase 1 在此触发 PII 引擎（并行或串行取决于性能预算，Phase 1 默认串行跟随 OCR 之后）。
- `MainWindow.open_pdf` (PDF 加载流程) — 打开 PDF 后自动触发 PII 扫描，与 OCR 扫描解耦但共用 worker thread pool 调度。
- `SettingsDialog` (`main.py:1008`) — 新增「隐私识别」tab 包含三个开关（`engine_enabled` / `auto_redact` / `require_confirmation`）。
- `config.json.template` — 同步新增 `pii_settings` 段。
- `tests/unit/test_app_config.py` — 新增 `pii_settings` 字段读取/默认值断言。
- `tests/unit/test_convergence.py` — 新增 `privacyguard.pii.*` 模块不在 `main.py` 中重复实现的断言。

</code_context>

<specifics>
## Specific Ideas

- **JSON 数据文件位置：** 建议 `privacyguard/pii/data/rules.json`（与 `privacyguard/ocr/` 平级，不放根目录，避免污染顶层命名空间）。
- **MIIT 段号白名单验证来源：** 参考工信部官方公告 + 中国信通院公开报告；Phase 1 实施前由 gsd-phase-researcher 验证一次并写入 `rules.json`。
- **身份证小写 x 处理（NUM-02）：** OCR 输出可能把 `X` 识别成小写 `x`，PII 引擎在 mod-11-2 校验前先做 `text.upper()` 归一化，但 `PIIHit.mask_strategy` 仍按原始大小写输出（避免改变用户原文）。
- **真脱敏与现有 `replacement_text` 的关系：** 现有 `config.json.replacement_text = "*"` 是为「黑框替换」服务的；Phase 1 的 PII 真脱敏沿用 `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` 的「像素级销毁」路径，不需要 `replacement_text`。
- **默认颜色：** 建议 PII 命中在画布上以**深红色**（区别于现有 `ocr` 用的浅色与 `manual` 用的蓝色）显示，让用户在视觉上一眼分辨「自动识别 vs 手动框选 vs OCR 文本层命中」。

</specifics>

<deferred>
## Deferred Ideas

- **每文件单独规则映射** — PROJECT.md / STATE.md 已明确让位给 Phase 1，归属后续 phase 复盘
- **批量 Word 替换的来源筛选高亮** — 属于 Word UI 抛光，归属 Phase 7 或 Phase 8
- **候选审阅对话框的完整实现** — Phase 7 主线；Phase 1 的 `require_confirmation=true` 走最小可用确认框（一个 QMessageBox + 列表）临时承载
- **识别规则编辑 UI** — Phase 8 UX-07
- **审计报告（JSON）** — Phase 8 OPS-01
- **完整行政区划词典 ~70 万条** — Phase 6 ADV-01；Phase 1 不引入
- **本地 NER 深度学习模型** — PROJECT.md 明确 Out of Scope
- **v38 UI 抛光** — PROJECT.md 明确让位给本轮识别准确率

</deferred>

---

*Phase: 1-PDF*
*Context gathered: 2026-08-10*
