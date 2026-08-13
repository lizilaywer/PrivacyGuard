# Phase 2: PDF 增加银行卡/邮箱/财税实体识别与部分掩码 - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

在 Phase 1 已建好的 PDF + PII 引擎（身份证 + 手机号）之上扩展识别 5 类新实体（银行卡、邮箱、USCC、VAT 发票号、纳税人识别号、银行账号），并把当前 PIIHit 已计算但**未被使用**的 `mask_strategy` 字段实际写入 PDF 产物中（partial mask）。同时按 SAFE-03 清除 PDF 文档元数据（Title / Author / Subject / Producer / Creator），并允许用户在 SettingsDialog「隐私识别」tab 与主界面 toolbar 切换「部分掩码 / 全遮蔽」处置方式。

不在 Phase 2 范围（明确划线）：
- Word / Excel / 图片格式扩展（Phase 3 / 4 / 5）
- 姓名 / 机构 / 地址 / 业务敏感字段识别（Phase 6）
- 候选审阅对话框 + 撤销栈（Phase 7）
- 识别规则编辑 UI / 审计报告 / 真实文档基线（Phase 8）
- 候选面板的「按来源筛选高亮」完全形态（CLAUDE.md 已注明归 Phase 7）

</domain>

<decisions>
## Implementation Decisions

### Partial mask 写入策略（MASK-01 落点）

- **D-01:** Partial mask 写入 = `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` 销毁底层文本+像素 → `add_redact_annot` 画黑底色块 → `page.insert_text` 在色块上写 `mask_strategy` 文字。**与 Phase 1 现有代码 90% 复用**，新增仅「partial mask 路径判断 + insert_text 步骤」。 — **Reversibility:** reversible — 沿用现有 add_redact_annot + apply_redactions 调用点，新增分支只影响命中处理。
- **D-02:** 字体：文本层路径从 `page.get_text("dict")` 取最近 span 的 `font` + `size` 同步插入；OCR / 占位 rect 路径用默认 sans-serif + 估算字号（`rect.height - 4pt`）。两条路径分别测。 — **Reversibility:** costly — 字体选择一旦固化到 partial mask 写入 helper，跨 entity type 共享；后续切换字体策略需同步修改 helper。
- **D-03:** 长度偏差：rect 宽度按 `mask_strategy` 字符数重算（`rect 跟 mask 长度走`），mask 文字居中插入。`page_offset` 维持原位置（不被 rect 宽度变化影响，便于 apply 阶段通过 `page.search_for(mask_strategy)` 二次定位）。 — **Reversibility:** reversible — 几何策略本地化在 helper 内。
- **D-04:** Mask 模式决策状态：扩展 `config.json.pii_settings` 为 `per_entity_default: Dict[str, "partial"|"blackout"]`（默认全 `partial`）。主真理来源在 config；运行时 `page_data[page]["mask_override_this_doc"]` 临时覆盖（D-12）。 — **Reversibility:** costly — `pii_settings` 字段名一旦被 SettingsDialog / main_window 引用，跨多处修改。

### 新实体验证强度（NUM-04 / NUM-05 / FIN-01..04）

- **D-05:** 银行卡（NUM-04）= 13-19 位纯数字，**Luhn 校验必过** + 6 位 BIN 前缀词典白名单（BIN 不命中直接 reject，置信度 HIGH）+ 上下文锥点（卡号 / 账号 / 银行 / 支付 / debit / credit）±20 字符提升 confidence 至 HIGH。BIC（银行识别码）不在 Phase 2 范围。 — **Reversibility:** costly — 验证规则一旦被 unit test + 端到端测试覆盖，规则调整会触发测试重写。
- **D-06:** USCC（FIN-01）= 18 位 + 纯大写字母数字，**GB 32100 mod-31-3 校验必过** + 登记管理部门类别代码表预筛选（`1`=机构编制、`5`=民政、`9`=工商、`Y`=其他、`A`=交通运输、`B`=司法 等 8 类），无效组合 reject。 — **Reversibility:** one-way — 登记管理部门类别代码表一旦写入 `rules.json` 并被单元测试覆盖，Phase 8 用户自定义词典 UX-07 会反向依赖这个表的结构。 — **Rationale:** Phase 8 用户可编辑 USCC 类别代码表，需从一开始就稳定 schema。
- **D-07:** VAT 发票号（FIN-02）= 双格式并行：传统 8 位纯数字 + 2022 年起全电发票的 20 位号码（数字为主，含横线与全电发票 20 位新规则）。均需上下文锥点（发票 / 号码 / 票号 / invoice）±20 字符。无上下文锥点的 8 位数字单独出现视为「疑似票号」，confidence_tier = MEDIUM。 — **Reversibility:** costly — 全电发票 20 位格式是国家税务总局 2022 公告，规则一旦锁定即为正本。
- **D-08:** 银行账号（FIN-04）= 9-21 位纯数字，**必加上下文锥点**（账号 / 账户 / 银行账号 / 招行 / 中行 / 建行 / 工商银行 / 农行 / 邮储 / 交通银行）±20 字符。无上下文锥点不产生 candidate。 — **Reversibility:** reversible — 上下文锥点关键词集合本地化在 helper 内。
- **D-09:** 纳税人识别号（FIN-03）= 拆为两条独立 entity_type：`CN_TAXPAYER_ID`（2015 年后三证合一 = 18 位 USCC，**复用 D-06 USCC 校验位逻辑**） + `CN_TAXPAYER_ID_15`（旧版 15 位三证合一编号，按 NNNNN-NNNNNNN-NNNN 格式 + 简单结构校验，置信度 MEDIUM）。 — **Reversibility:** one-way — entity_type 字符串一旦出现在 `PIIHit.entity_type` 与下游 `mask_for_entity` 分派表中，重命名会跨多处修改。 — **Rationale:** 15 位编号无 mod-11-2 之类的强校验位，独立 type 防止误用 USCC 校验。

### 邮箱识别（NUM-05）

- **D-10:** 邮箱 = RFC 5322 简化版正则（`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`），不引入 IDN / 国际化邮箱。无校验位。Confidence 判定按是否含公共域名后缀（com / cn / net / org / gov / edu）→ HIGH，否则 MEDIUM。 — **Reversibility:** reversible — 正则字符串本地化在 `regex_patterns.py`。

### Mask 模式切换粒度（MASK-02）

- **D-11:** UI 入口：复用 Phase 1 D-08 的 `SettingsDialog`「隐私识别」tab（与 `engine_enabled` / `auto_redact` / `require_confirmation` 三个开关同区），新增「脱敏方式」表：每个 entity_type 一行复选框 + 「部分掩码 / 全遮蔽」下拉。默认全为「部分掩码」。 — **Reversibility:** costly — SettingsDialog 5-tab 结构一旦扩展到第 6 个 widget，后续新增 tab 需重新对齐网格。
- **D-12:** 文档级 override：Phase 2 也在主界面 toolbar 加「本文件使用全遮蔽」 toggle。勾选时临时覆盖全局 per-entity 设置（写入 `self.page_data[0]["mask_override_this_doc"] = "blackout"`，save_pdf 读取后临时反转 per_entity_default）。切换状态随当前 PDF 生命周期，不持久化到 config.json。 — **Reversibility:** reversible — toggle 状态仅存在 `self.page_data`，不写入磁盘。
- **D-13:** Mask 模式字段命名：`pii_settings.per_entity_default: Dict[str, Literal["partial", "blackout"]]`，默认 `{"CN_ID_CARD": "partial", "CN_PHONE": "partial", "CN_BANK_CARD": "partial", "CN_EMAIL": "partial", "CN_USCC": "partial", "CN_TAXPAYER_ID": "partial", "CN_TAXPAYER_ID_15": "partial", "CN_VAT_INVOICE": "partial", "CN_BANK_ACCOUNT": "partial"}`。 — **Reversibility:** one-way — 字段命名一旦被 `config.json.template` / `tests/unit/test_app_config.py` 引用，重命名会触发跨多处修改。

### PDF 元数据清除（SAFE-03）

- **D-14:** 范围：只清 ROADMAP Success Criteria 列出的 5 个字段：`Title` / `Author` / `Subject` / `Producer` / `Creator`。`CreationDate` / `ModDate` / `Keywords` / XMP metadata 资源**不动**。 — **Reversibility:** reversible — 调用 `doc.set_metadata({"title": "", "author": "", "subject": "", "producer": "", "creator": ""})` 即可；不调即可恢复。
- **D-15:** 占位策略：5 个被清字段全部置空字符串（`""`），不写 `Anonymous` / `Redacted` / `PyMuPDF` 之类占位字符串。 — **Reversibility:** reversible — 仅 5 行字符串。
- **D-16:** 时机：仅在 `save_pdf` 中调用一次（与 `apply_pii_redactions` 同位置、`doc.save` 前调 `doc.set_metadata({...})`）。打开 PDF 时不调；预览也不调。验证：保存后通过 `fitz.open(fname).metadata` 反向断言 5 个字段全为空。 — **Reversibility:** reversible — 调用点本地化在 `MainWindow.save_pdf`。

### PII 引擎扩展点

- **D-17:** 新增 5 类实体的 validators 放 `privacyguard/pii/validators/`（与现有 `id_card.py` / `phone_segment.py` 平级），文件名按 entity_type：`bank_card.py` / `email.py` / `uscc.py` / `vat_invoice.py` / `bank_account.py` / `taxpayer_id.py`（旧版 15 位）。每个 validator 暴露 `validate_*(text) -> bool` 纯函数，与 `validators/__init__.py` 现行导出风格保持一致。 — **Reversibility:** reversible — 子模块组织与 Phase 1 一致。
- **D-18:** 正则预编译放 `privacyguard/pii/regex_patterns.py`（与 Phase 1 现有 18/15 ID + 11 位 phone 平级），按 entity_hint（`CN_BANK_CARD` / `CN_EMAIL` / `CN_USCC` / `CN_VAT_INVOICE` / `CN_TAXPAYER_ID` / `CN_TAXPAYER_ID_15` / `CN_BANK_ACCOUNT`）返回候选字符串。 — **Reversibility:** reversible — `iter_candidate_strings` 是 generator，扩 yield 不影响现有调用方。
- **D-19:** `privacyguard/pii/data/rules.json` 扩展键：`bank_card.bin_dictionary_path`（指向 `privacyguard/pii/data/bin_prefixes.json`，6 位 BIN 词典）、`uscc.category_codes`（登记管理部门类别代码 8 字符数组）、`vat_invoice.context_anchors`（关键词列表）、`bank_account.context_anchors`（关键词列表）。mod-31-3 权重表与 Phase 1 现有 `id_card.weights` 同位置存放。 — **Reversibility:** costly — `rules.json` 字段一旦被 unit test 与 `tests/unit/test_app_config.py` 引用，跨多处修改。
- **D-20:** 上下文锥点（CONTEXT_ANCHORS）放 `privacyguard/pii/validators/<entity>.py`（每个 entity 各自的常量），不集中放 `rules.json`。原因：上下文锥点是 detection 规则一部分，跟 validator 绑定更紧。`rules.json` 仅放数据结构化的词典与权重表。 — **Reversibility:** reversible — 上下文锥点本地化在 validator。

### Partial mask 写入 helper 接口

- **D-21:** 新增 `privacyguard/pii/pdf_adapter.py::write_partial_masks(doc, page_idx, pii_hits, mode="partial"|"blackout")` 函数（与现有 `apply_pii_redactions` 平级）。当 `mode="partial"` 时：先 `add_redact_annot`（画黑底）+ `apply_redactions(IMAGE_PIXELS)` 后 `insert_text` 写 mask_strategy（D-01 + D-02 流程）；当 `mode="blackout"` 时：仅 `add_redact_annot` + `apply_redactions(IMAGE_PIXELS)`（沿用 Phase 1 现有行为）。helper 内部按 D-03 长度偏差规则重算 rect 宽度。 — **Reversibility:** reversible — 单一 helper，签名稳定即可。
- **D-22:** `MainWindow.save_pdf`（`main.py:12490-12504`）的 PII 路径改为调 `write_partial_masks(...)`，OCR / manual 路径**不变**（保持纯黑框全遮蔽行为，不做 partial mask）。 — **Reversibility:** reversible — `MainWindow` 边界修改一处。

### 测试与回归

- **D-23:** Phase 2 必须新增至少 5 类单元测试：① `test_pii_engine.py` 新增 `CN_BANK_CARD` / `CN_EMAIL` / `CN_USCC` / `CN_VAT_INVOICE` / `CN_TAXPAYER_ID` / `CN_TAXPAYER_ID_15` / `CN_BANK_ACCOUNT` 的命中 + 档位判定测试（含 Luhn / mod-31-3 / 上下文锥点 / 边界用例）；② `test_pii_validators.py` 新增 6 个 validator 的纯函数测试；③ `test_pdf_pii_redaction.py` 新增 partial mask 写入后通过 `fitz.open().get_text()` 反向提取断言原文不存在 + mask 文字存在；④ `test_pdf_metadata_cleared.py` 新增元数据清除反向测试（`doc.metadata` 5 字段全空）；⑤ `test_app_config.py` 新增 `pii_settings.per_entity_default` 字段读取/默认值/类型断言。 — **Reversibility:** reversible — 新增测试文件，独立于 79/79 基线。
- **D-24:** Phase 2 必须保持 79/79 既有测试基线（CLAUDE.md 列出的 10 个 unittest 模块）全部通过；新增的 5 个 PII engine 测试与 4 个 adapter/metadata 测试在 Phase 2 完成后进入基线（基线从 79/79 升级为 88/88 或 89/89）。 — **Reversibility:** one-way — 测试基线一旦升级，向下兼容约束就生效。
- **D-25:** reverse-extraction 测试用 `fitz.open().get_text()` 路径（与 Phase 1 D-14 一致），不依赖 poppler-utils，避免 CI 上 poppler 缺失。 — **Reversibility:** reversible — 测试 helper 本地化。

### 打包与数据文件

- **D-26:** 新增 `privacyguard/pii/data/bin_prefixes.json`（BIN 词典 ~1 万条）需同步加入 PyInstaller spec 的 `datas=[]` 与 `hiddenimports`，与 Phase 1 D-10 + `cp30` 回归修复点保持一致。新增数据文件加载路径必须走 `privacyguard.utils.security.resource_path`，严禁 `os.path.dirname(__file__)`。 — **Reversibility:** one-way — 一旦 PyInstaller spec 写入 `datas=[]`，后续移除需同步改 spec 与 macOS/Windows 构建脚本。 — **Rationale:** cp30 修复过的 `privacyguard.utils.security` 导入失败回归需在 Phase 2 重新验证。
- **D-27:** `bin_prefixes.json` 优先来源：维基百科「Bank card number」列表 + 中国银联 BIN 公开公告。LICENSE 审查：维基内容遵循 CC BY-SA 4.0，需在 `data/bin_prefixes.json.LICENSE` 中保留归属声明。Phase 1 已记入 STATE.md Open Questions 的「词典文件 LICENSE 审查」在这里完成。 — **Reversibility:** costly — LICENSE 引用一旦被合入，更换来源需重审。

### Claude's Discretion

- `PIIHit.mask_strategy` 当前是 `str = ""`，新增 partial mask 写入 helper 后是否要扩展为含字体信息（如 `mask_strategy_with_font: Optional[str]`）— 建议**不扩展**，字体通过 `page.get_text("dict")` 现场取，hit 只承担文字。
- 新增 5 类实体的颜色（与 Phase 1 已用「深红色」区分 PII 自动识别）— 建议全部沿用「深红色」，不在 Phase 2 引入新颜色。
- 邮箱 `z****@qq.com` 是否要保留顶级域名后缀（qq.com / 163.com）— 建议保留（ROADMAP 例子明示）；多级子域（`foo@bar.qq.com`）的截断位置由实现者按首字符 + `@` 后最后一段定。
- 银行卡 BIN 词典的最终条数（建议 1 万-1.5 万条）— 由 implementer 决定，按维基 + 银联公开数据源整合。
- USCC 旧版 15 位 `CN_TAXPAYER_ID_15` 的 mask 策略（前 6 后 4？保留前 3？）— 建议「前 6 + 后 4」，与 USCC 18 位一致。

### Folded Todos

None — discussion produced no todos to fold.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目规划与需求
- `.planning/PROJECT.md` — 项目核心价值（打开文档自动列敏感项）、Active Requirements 列表、Constraints（零网络 / 纯本地规则 / 不破坏 79 基线）
- `.planning/REQUIREMENTS.md` §NUM-04 / §NUM-05 / §FIN-01..04 / §MASK-01 / §MASK-02 / §SAFE-03 — Phase 2 覆盖的 9 个 v1 需求 acceptance criteria
- `.planning/ROADMAP.md` §Phase 2 — Success Criteria 四条（识别覆盖 / partial mask 默认 / 模式切换 / 元数据清除）
- `.planning/STATE.md` — Decisions 段落「Detection is format-independent / 新数据存进现有 dict 的新 key / 每个格式走垂直 MVP 切片」；Open Questions 段落「手机号段号白名单 / 行政区划词典打包策略 / 全电发票 20 位号码格式 / 词典文件 LICENSE 审查 / Excel 列头→实体类型映射 schema」

### 既有架构与代码地图
- `.planning/codebase/STRUCTURE.md` — 目录布局与「Where to Add New Code」指引
- `.planning/codebase/ARCHITECTURE.md` — 系统分层、Worker/OCR Helper/Utility 三层结构、Anti-Patterns（重复实现、`ConfigManager` 误用、eager import、绕过 worker 兼容层、`main.py` UI 堆积）
- `.planning/codebase/CONCERNS.md` — 已知 Bug、Performance Bottlenecks、Missing Critical Features
- `.planning/codebase/INTEGRATIONS.md` — PyMuPDF / python-docx / mammoth / RapidOCR / ONNXRuntime / OpenCV 集成现状

### Phase 1 既有决策与代码（必读）
- `.planning/phases/01-pdf/01-CONTEXT.md` — Phase 1 全部 D-01..D-14 决策（含子包组织 / 懒加载 / dataclass 字段锁定 / `pii_settings` 设计 / 真脱敏路径）
- `.planning/phases/01-pdf/01-VERIFICATION.md` — Phase 1 must-haves 16/16 验证基线
- `privacyguard/pii/__init__.py` — `_LAZY_IMPORTS` + `__getattr__` 懒加载范本（Phase 2 新增 entity 必须在 `_LAZY_IMPORTS` 注册）
- `privacyguard/pii/engine.py` — `PIIEngine` detect pipeline 完整实现（B2 / W-A / I1 已落地）
- `privacyguard/pii/regex_patterns.py` — `iter_candidate_strings` 生成器范本（Phase 2 新增 entity_hint 在此 yield）
- `privacyguard/pii/validators/id_card.py` — `validate_18` / `validate_15` 范本（Phase 2 新增 validator 沿用此形态）
- `privacyguard/pii/validators/phone_segment.py` — `is_mobile_segment` 范本（白名单 + 排除表结构）
- `privacyguard/pii/validators/__init__.py` — validators 子包导出（Phase 2 新增 validator 在此注册）
- `privacyguard/pii/hits.py` — `PIIHit` / `TextUnit` dataclass（D-05 字段顺序锁）
- `privacyguard/pii/mask.py` — `partial_mask_id_card` / `partial_mask_phone` / `mask_for_entity` 范本（Phase 2 新增 partial mask 沿用此形态）
- `privacyguard/pii/pdf_adapter.py` — `collect_pii_rects` / `apply_pii_redactions` 范本（Phase 2 新增 `write_partial_masks` 沿用此模块）
- `privacyguard/pii/data/rules.json` — `phone_segment` / `id_card` 数据键范本（Phase 2 扩展 `bank_card` / `uscc` / `vat_invoice` / `bank_account` 键）
- `privacyguard/pii/confidence.py` — `classify_hit` 档位判定范本
- `privacyguard/pii/normalize.py` — `flatten_for_match` / `map_flat_to_original` 范本
- `privacyguard/pii/overlap.py` — `resolve` 重叠消除范本

### 既有 main.py 接入点
- `main.py:12340-12395` — 现有 PDF 真脱敏写入循环（Phase 2 改为调 `write_partial_masks` helper）
- `main.py:12490-12504` — `save_pdf` 中 PII 命中处理（Phase 2 修改此处，OCR / manual 路径不变）
- `main.py:11377-11385` — `_PIIReceiveHandler` 反序列化 worker 发出的 dict 列表为 `PIIHit`
- `main.py:5031` — `_pii_data_lock` 写入保护
- `main.py:1008` — `SettingsDialog`（Phase 2 扩展「隐私识别」tab 加 per_entity 列表）
- `main.py:4191` — `_start_ocr_scan` 启动入口（Phase 2 PII 触发点保持 Phase 1 既有调用关系）
- `main.py:4908` — `MainWindow.page_data` 字典结构（Phase 2 新增 `mask_override_this_doc` 键）

### 既有测试范本（必读）
- `tests/unit/test_pii_engine.py` — `PIIEngine` detect 测试范本（Phase 2 新增 5 类 entity 的命中 / 档位 / 边界用例）
- `tests/unit/test_pii_validators.py` — 6 个 validator 纯函数测试范本
- `tests/unit/test_pdf_pii_redaction.py` — reverse-extraction 范本（Phase 2 扩展 partial mask 反向测试）
- `tests/unit/test_pdf_pii_pipeline.py` — 端到端 pipeline 测试范本
- `tests/unit/test_app_config.py` — `pii_settings` 字段读取测试（Phase 2 扩展 `per_entity_default` 字段）
- `tests/unit/test_convergence.py` — `main.py` / `privacyguard/*` 不分叉的强制回归
- `tests/unit/test_package_imports.py` — 懒加载 + PyInstaller 兼容性强制回归
- `tests/unit/test_pdf_text_hit_dedup.py` — 文字层去重强制回归
- `tests/unit/test_mixed_pdf_ocr.py` — OCR 坐标换算强制回归

### 配置与打包
- `config.json:19-82` — 现有 `redaction.default_rules`（Phase 2 不动）；`pii_settings` 字段位置与格式参考
- `config.json.template` — 同步新增 `per_entity_default` 字段
- `rollback_journal.md` cp30 条目 — `privacyguard.utils.security` 导入失败回归；新增 `bin_prefixes.json` 数据文件需同步验证 PyInstaller `datas` / `hiddenimports`
- `packaging/windows/config/PrivacyGuard_windows.spec` — Windows PyInstaller spec；新增 `bin_prefixes.json` 需加入 `datas`
- `packaging/macos/scripts/build_complete.sh` — macOS 构建脚本；同上
- `docs/packaging/windows-packaging-guide.md` — Windows 打包流程
- `docs/packaging/macos-packaging-guide.md` — macOS 打包流程

### CLAUDE.md 关键约束（必读）
- `CLAUDE.md` §当前生效的配置路径 — `SimpleConfig` 在 `main.py` 中仍是运行时配置；不切换到 `ConfigManager`
- `CLAUDE.md` §OCR 依赖的懒加载约束 — `privacyguard/` 包导入必须保持懒加载；新增 5 类 PII validator 必须遵守
- `CLAUDE.md` §主架构现状 — `main.py` 仍是单体，新逻辑放 `privacyguard/` 不放 `main.py`
- `CLAUDE.md` §版本号单一来源 — `version.txt`；Phase 2 完成时不改版本号（仅 Phase 2 内部交付），版本号升级在阶段合并时统一处理

### 国家标准与公开数据源（research 阶段需查证）
- GB 32100-2015《法人和其他组织统一社会信用代码编码规则》— USCC 18 位编码 + mod-31-3 校验位 + 登记管理部门类别代码
- GB/T 7408-2005 / ISO 8601 — 日期时间格式（如适用）
- GB 11643-1999 — 身份证（Phase 1 已落地）
- ISO/IEC 7812 — 银行卡号（BIN 词典来源：维基百科「Bank card number」+ 中国银联公开公告）
- 国家税务总局公告 2022 年第 1 号 — 全电发票 20 位号码格式
- 工信部公开公告 — 手机号段号（Phase 1 已落地）
- 维基百科「Bank card number」— BIN 词典 1 万-1.5 万条，CC BY-SA 4.0 LICENSE 需保留归属

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PIIEngine`（`privacyguard/pii/engine.py:59`）** — 现有 detect pipeline：flatten → iter candidates → validate → resolve overlap。Phase 2 新增 5 类 entity 直接复用此管线，仅扩展 `iter_candidate_strings` yield 的 `entity_hint` 值。
- **`PIIHit`（`privacyguard/pii/hits.py:15`）** — D-05 字段锁：entity_type / page_offset / page_length / page_rect / confidence_tier / source / mask_strategy / normalized / validator_passed。Phase 2 新增 entity_type 字符串按 D-09 / D-10 等命名。
- **`apply_pii_redactions`（`privacyguard/pii/pdf_adapter.py:37`）** — 现有真脱敏调用范本：`add_redact_annot` + `set_colors` + `apply_redactions(IMAGE_PIXELS)` + `garbage=4 + deflate=True + clean=True`。Phase 2 `write_partial_masks` helper 沿用此范本。
- **`mask_for_entity`（`privacyguard/pii/mask.py:23`）** — 按 entity_type 分派掩码函数。Phase 2 扩展分支：`partial_mask_bank_card` / `partial_mask_email` / `partial_mask_uscc` / `partial_mask_vat_invoice` / `partial_mask_taxpayer_id` / `partial_mask_bank_account`。
- **`iter_candidate_strings`（`privacyguard/pii/regex_patterns.py:20`）** — generator：按 18/15 ID → phone 顺序 yield 候选。Phase 2 在此 yield 新增 5 类 entity_hint 候选。
- **`validators/__init__.py`** — 现有 `validate_18_id` / `validate_15_id` / `upgrade_15_to_18` / `compute_check_digit` / `is_mobile_segment` 导出。Phase 2 扩展：6 个新 validator（bank_card / email / uscc / vat_invoice / taxpayer_id / bank_account）。
- **`MainWindow.page_data`（`main.py:4908`）** — `page_data[page_num] = {"ocr": [...], "manual": [...], "pii": [PIIHit...]}`。Phase 2 新增 `mask_override_this_doc` 键（D-12）。
- **`_pii_data_lock`（`main.py:5031`）** — Phase 1 已有 PII 写入保护，Phase 2 沿用。
- **`tests/unit/test_pii_engine.py`（`tests/unit/test_pii_engine.py:1`）** — `TestPIIEngine` 类范本：测试 detect 主流程 + 各种边界。Phase 2 新增 `TestPIIEngineBankCard` / `TestPIIEngineEmail` / `TestPIIEngineUSCC` / `TestPIIEngineVATInvoice` / `TestPIIEngineTaxpayerID` / `TestPIIEngineBankAccount` 类。
- **`_LAZY_IMPORTS`（`privacyguard/pii/__init__.py:38`）** — Phase 1 已有 12 个导出项的懒加载注册。Phase 2 新增 6 个 validator 函数 + 6 个 partial mask 函数 + `write_partial_masks` + `clear_pdf_metadata` 注册。
- **`config.json.pii_settings`（Phase 1 D-08）** — 现有 3 字段：`engine_enabled` / `auto_redact` / `require_confirmation`。Phase 2 扩展为 4 字段：新增 `per_entity_default` 字典（D-13）。

### Established Patterns
- **Lazy-load discipline:** `privacyguard/__init__.py` 与 `privacyguard/workers/__init__.py` 用 `__getattr__` 延迟加载；Phase 2 新增 `privacyguard.pii.validators.<entity>` 子模块必须在自己的 `__init__.py` 中实现同一形态。
- **Pure-function validators:** `validate_18` / `validate_15` / `is_mobile_segment` 全部纯函数，无 IO / 无线程 / 无状态。Phase 2 6 个新 validator 沿用此形态。
- **Dependency-injection for OCR helpers:** Phase 1 已用。Phase 2 partial mask 写入 helper 也走同一形态（可选接收 `font_lookup_fn` / `text_size_estimator_fn` 注入点）。
- **Two-tier worker pattern:** `main.py` 中 `OCRWorker(_ModularOCRWorker)` 薄兼容层；Phase 2 不新增 worker，沿用 Phase 1 既有 PII worker。
- **Page data dict as single source of truth:** `page_data[page]["pii"]` 与现有 `ocr` / `manual` 键并存；Phase 2 新增 `mask_override_this_doc` 键遵守同一契约。
- **Reverse-extraction as safety net:** 真脱敏的最终验证必须由独立通道（`fitz.open().get_text()` 反向）确认；Phase 2 partial mask 写入后需反向断言原文不存在 + mask 文字存在（D-23）。
- **PIIHit frozen dataclass with field order lock:** Phase 1 D-05 锁定字段顺序；Phase 2 不新增字段。

### Integration Points
- **`MainWindow.save_pdf`（`main.py:12456`）** — 现有 PDF 保存流程；Phase 2 改 PII 路径为调 `write_partial_masks` helper，并新增 `doc.set_metadata({...})` 调 5 字段空字符串。
- **`SettingsDialog`（`main.py:1008`）** — 现有 5-tab 结构（含 Phase 1 D-08 新增的「隐私识别」tab）；Phase 2 在「隐私识别」tab 新增「脱敏方式」表（D-11）。
- **`MainWindow` toolbar** — Phase 2 新增「本文件使用全遮蔽」 toggle（`self.page_data[0]["mask_override_this_doc"]`）（D-12）。
- **`config.json` + `config.json.template`** — 同步新增 `pii_settings.per_entity_default` 字段。
- **`privacyguard/pii/data/rules.json`** — 扩展 `bank_card` / `uscc` / `vat_invoice` / `bank_account` 4 个键（D-19）。
- **`privacyguard/pii/data/bin_prefixes.json`** — 新增 BIN 词典文件（D-26 + D-27）。
- **`tests/unit/test_app_config.py`** — 新增 `pii_settings.per_entity_default` 字段读取/默认值/类型断言（D-23）。
- **`tests/unit/test_convergence.py`** — 沿用，Phase 2 不引入新的分叉风险。
- **`packaging/windows/config/PrivacyGuard_windows.spec`** + **`packaging/macos/scripts/build_complete.sh`** — 同步加入 `bin_prefixes.json` 到 `datas`（D-26）。

</code_context>

<specifics>
## Specific Ideas

- **JSON 数据文件位置：** `privacyguard/pii/data/bin_prefixes.json`（与现有 `rules.json` 同目录；Phase 1 建议的位置 `privacyguard/pii/data/rules.json` 已沿用，Phase 2 同位置扩展）。
- **USCC 旧版 15 位 vs 18 位三证合一：** 旧版 15 位格式 `NNNNN-NNNNNNN-NNNN` 是 2015 年前税务局 / 工商 / 质检三套号合并前的编号；2015 年后三证合一统一切换为 18 位 USCC。Phase 2 拆为两个 entity_type（`CN_TAXPAYER_ID` / `CN_TAXPAYER_ID_15`）独立处理。
- **全电发票 20 位号码格式：** 国家税务总局 2022 年公告第 1 号起推行的「全面数字化电子发票」。号码规则为 20 位数字 + 校验位（按 GB/T 7408），每年号码段由税务总局公告分配。Phase 2 实现需考虑 20 位号码与 8 位传统号共存。
- **银行卡 BIN 词典来源：** 维基百科「Bank card number」页面 + 中国银联公开 BIN 公告。维基遵循 CC BY-SA 4.0，需在 `data/bin_prefixes.json.LICENSE` 保留归属声明。整合后条数预计 1 万-1.5 万条。
- **partial mask 字体回退：** 当 `page.get_text("dict")` 在 mask 区域附近找不到 span（即该区域被分块、不含完整字符）时，回退到 PDF 默认 sans-serif 字体。字号按 `rect.height - 4pt` 估算（D-02）。
- **元数据清除与 fitz 兼容：** PyMuPDF `doc.set_metadata()` 是文档级调用，不影响 page 级；调用位置紧邻 `doc.save()`，避免影响中间状态（D-16）。

</specifics>

<deferred>
## Deferred Ideas

- **候选审阅 UI 完整实现** — Phase 7 主线（`page_data["mask_overrides"]` 单条 hit 切换的精细粒度归属 Phase 7）。
- **识别规则编辑 UI** — Phase 8 UX-07（用户自定义 BIN 词典 / USCC 类别代码表通过 Phase 8 的「识别规则」tab 编辑，Phase 2 仅写入内置数据）。
- **审计报告** — Phase 8 OPS-01（mask 模式决策状态可被审计报告消费，但 Phase 2 不实现）。
- **本地 NER 深度学习模型** — PROJECT.md 明确 Out of Scope。
- **行政区划词典** — Phase 6 才需要全集 ~70 万条；Phase 2 不引入。
- **v38 UI 抛光** — PROJECT.md 明确让位给本轮识别准确率。
- **BIC（银行识别码）识别** — FIN-04 仅覆盖「银行账号」，BIC（SWIFT Code）作为后续 phase 候选。
- **批次内跨文档掩码一致性策略** — BATCH-02 / v2 requirement；与 Phase 2 单文档范围正交。

---

*Phase: 2-PDF*
*Context gathered: 2026-08-11*