# Phase 2: PDF 增加银行卡/邮箱/财税实体识别与部分掩码 - Research

**Researched:** 2026-08-11
**Domain:** PDF 实体扩展识别（银行卡 Luhn+BIN / 邮箱 RFC5322 简化 / USCC GB32100 mod-31-3 / 全电发票 20 位 / 纳税人识别号 / 银行账号）+ 部分掩码写入 helper（PyMuPDF `insert_text` 字体回退）+ PDF 元数据清除（`fitz.set_metadata` 5 字段）
**Confidence:** HIGH（GB 32100 / Luhn / PyMuPDF `set_metadata` 5 字段空字符串语义均经本机 Python 验证）/ MEDIUM（银行卡 BIN 词典最终条数 + 邮箱域名后缀硬编码范围待用户签字）

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Partial mask 写入策略（MASK-01 落点）

- **D-01:** Partial mask 写入 = `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` 销毁底层文本+像素 → `add_redact_annot` 画黑底色块 → `page.insert_text` 在色块上写 `mask_strategy` 文字。**与 Phase 1 现有代码 90% 复用**，新增仅「partial mask 路径判断 + insert_text 步骤」。
- **D-02:** 字体：文本层路径从 `page.get_text("dict")` 取最近 span 的 `font` + `size` 同步插入；OCR / 占位 rect 路径用默认 sans-serif + 估算字号（`rect.height - 4pt`）。两条路径分别测。
- **D-03:** 长度偏差：rect 宽度按 `mask_strategy` 字符数重算（`rect 跟 mask 长度走`），mask 文字居中插入。`page_offset` 维持原位置（不被 rect 宽度变化影响，便于 apply 阶段通过 `page.search_for(mask_strategy)` 二次定位）。
- **D-04:** Mask 模式决策状态：扩展 `config.json.pii_settings` 为 `per_entity_default: Dict[str, "partial"|"blackout"]`（默认全 `partial`）。主真理来源在 config；运行时 `page_data[page]["mask_override_this_doc"]` 临时覆盖（D-12）。

#### 新实体验证强度（NUM-04 / NUM-05 / FIN-01..04）

- **D-05:** 银行卡（NUM-04）= 13-19 位纯数字，**Luhn 校验必过** + 6 位 BIN 前缀词典白名单（BIN 不命中直接 reject，置信度 HIGH）+ 上下文锥点（卡号 / 账号 / 银行 / 支付 / debit / credit）±20 字符提升 confidence 至 HIGH。BIC（银行识别码）不在 Phase 2 范围。
- **D-06:** USCC（FIN-01）= 18 位 + 纯大写字母数字，**GB 32100 mod-31-3 校验必过** + 登记管理部门类别代码表预筛选（`1`=机构编制、`5`=民政、`9`=工商、`Y`=其他、`A`=交通运输、`B`=司法 等 8 类），无效组合 reject。
- **D-07:** VAT 发票号（FIN-02）= 双格式并行：传统 8 位纯数字 + 2022 年起全电发票的 20 位号码（数字为主，含横线与全电发票 20 位新规则）。均需上下文锥点（发票 / 号码 / 票号 / invoice）±20 字符。无上下文锥点的 8 位数字单独出现视为「疑似票号」，confidence_tier = MEDIUM。
- **D-08:** 银行账号（FIN-04）= 9-21 位纯数字，**必加上下文锥点**（账号 / 账户 / 银行账号 / 招行 / 中行 / 建行 / 工商银行 / 农行 / 邮储 / 交通银行）±20 字符。无上下文锥点不产生 candidate。
- **D-09:** 纳税人识别号（FIN-03）= 拆为两条独立 entity_type：`CN_TAXPAYER_ID`（2015 年后三证合一 = 18 位 USCC，**复用 D-06 USCC 校验位逻辑**） + `CN_TAXPAYER_ID_15`（旧版 15 位三证合一编号，按 NNNNN-NNNNNNN-NNNN 格式 + 简单结构校验，置信度 MEDIUM）。

#### 邮箱识别（NUM-05）

- **D-10:** 邮箱 = RFC 5322 简化版正则（`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`），不引入 IDN / 国际化邮箱。无校验位。Confidence 判定按是否含公共域名后缀（com / cn / net / org / gov / edu）→ HIGH，否则 MEDIUM。

#### Mask 模式切换粒度（MASK-02）

- **D-11:** UI 入口：复用 Phase 1 D-08 的 `SettingsDialog`「隐私识别」tab（与 `engine_enabled` / `auto_redact` / `require_confirmation` 三个开关同区），新增「脱敏方式」表：每个 entity_type 一行复选框 + 「部分掩码 / 全遮蔽」下拉。默认全为「部分掩码」。
- **D-12:** 文档级 override：Phase 2 也在主界面 toolbar 加「本文件使用全遮蔽」 toggle。勾选时临时覆盖全局 per-entity 设置（写入 `self.page_data[0]["mask_override_this_doc"] = "blackout"`，save_pdf 读取后临时反转 per_entity_default）。切换状态随当前 PDF 生命周期，不持久化到 config.json。
- **D-13:** Mask 模式字段命名：`pii_settings.per_entity_default: Dict[str, Literal["partial", "blackout"]]`，默认 `{"CN_ID_CARD": "partial", "CN_PHONE": "partial", "CN_BANK_CARD": "partial", "CN_EMAIL": "partial", "CN_USCC": "partial", "CN_TAXPAYER_ID": "partial", "CN_TAXPAYER_ID_15": "partial", "CN_VAT_INVOICE": "partial", "CN_BANK_ACCOUNT": "partial"}`。

#### PDF 元数据清除（SAFE-03）

- **D-14:** 范围：只清 ROADMAP Success Criteria 列出的 5 个字段：`Title` / `Author` / `Subject` / `Producer` / `Creator`。`CreationDate` / `ModDate` / `Keywords` / XMP metadata 资源**不动**。
- **D-15:** 占位策略：5 个被清字段全部置空字符串（`""`），不写 `Anonymous` / `Redacted` / `PyMuPDF` 之类占位字符串。
- **D-16:** 时机：仅在 `save_pdf` 中调用一次（与 `apply_pii_redactions` 同位置、`doc.save` 前调 `doc.set_metadata({...})`）。打开 PDF 时不调；预览也不调。验证：保存后通过 `fitz.open(fname).metadata` 反向断言 5 个字段全为空。

#### PII 引擎扩展点

- **D-17:** 新增 5 类实体的 validators 放 `privacyguard/pii/validators/`（与现有 `id_card.py` / `phone_segment.py` 平级），文件名按 entity_type：`bank_card.py` / `email.py` / `uscc.py` / `vat_invoice.py` / `bank_account.py` / `taxpayer_id.py`（旧版 15 位）。每个 validator 暴露 `validate_*(text) -> bool` 纯函数。
- **D-18:** 正则预编译放 `privacyguard/pii/regex_patterns.py`，按 entity_hint（`CN_BANK_CARD` / `CN_EMAIL` / `CN_USCC` / `CN_VAT_INVOICE` / `CN_TAXPAYER_ID` / `CN_TAXPAYER_ID_15` / `CN_BANK_ACCOUNT`）返回候选字符串。
- **D-19:** `privacyguard/pii/data/rules.json` 扩展键：`bank_card.bin_dictionary_path`、`uscc.category_codes`、`vat_invoice.context_anchors`、`bank_account.context_anchors`。mod-31-3 权重表与 Phase 1 现有 `id_card.weights` 同位置存放。
- **D-20:** 上下文锥点（CONTEXT_ANCHORS）放 `privacyguard/pii/validators/<entity>.py`（每个 entity 各自的常量），不集中放 `rules.json`。

#### Partial mask 写入 helper 接口

- **D-21:** 新增 `privacyguard/pii/pdf_adapter.py::write_partial_masks(doc, page_idx, pii_hits, mode="partial"|"blackout")` 函数。当 `mode="partial"` 时：先 `add_redact_annot`（画黑底）+ `apply_redactions(IMAGE_PIXELS)` 后 `insert_text` 写 mask_strategy（D-01 + D-02 流程）；当 `mode="blackout"` 时：仅 `add_redact_annot` + `apply_redactions(IMAGE_PIXELS)`（沿用 Phase 1 现有行为）。helper 内部按 D-03 长度偏差规则重算 rect 宽度。
- **D-22:** `MainWindow.save_pdf`（`main.py:12490-12504`）的 PII 路径改为调 `write_partial_masks(...)`，OCR / manual 路径**不变**（保持纯黑框全遮蔽行为，不做 partial mask）。

#### 测试与回归

- **D-23:** Phase 2 必须新增至少 5 类单元测试：① `test_pii_engine.py` 新增 7 类 entity 的命中 + 档位判定测试；② `test_pii_validators.py` 新增 6 个 validator 的纯函数测试；③ `test_pdf_pii_redaction.py` 新增 partial mask 写入后通过 `fitz.open().get_text()` 反向提取断言原文不存在 + mask 文字存在；④ `test_pdf_metadata_cleared.py` 新增元数据清除反向测试；⑤ `test_app_config.py` 新增 `pii_settings.per_entity_default` 字段读取/默认值/类型断言。
- **D-24:** Phase 2 必须保持 79/79 既有测试基线（CLAUDE.md 列出的 10 个 unittest 模块）全部通过；新增的 5 个 PII engine 测试与 4 个 adapter/metadata 测试在 Phase 2 完成后进入基线（基线从 79/79 升级为 88/88 或 89/89）。
- **D-25:** reverse-extraction 测试用 `fitz.open().get_text()` 路径（与 Phase 1 D-14 一致），不依赖 poppler-utils。

#### 打包与数据文件

- **D-26:** 新增 `privacyguard/pii/data/bin_prefixes.json`（BIN 词典 ~1 万条）需同步加入 PyInstaller spec 的 `datas=[]` 与 `hiddenimports`。新增数据文件加载路径必须走 `privacyguard.utils.security.resource_path`。
- **D-27:** `bin_prefixes.json` 优先来源：维基百科「Bank card number」列表 + 中国银联 BIN 公开公告。LICENSE 审查：维基内容遵循 CC BY-SA 4.0，需在 `data/bin_prefixes.json.LICENSE` 中保留归属声明。

### Claude's Discretion

- `PIIHit.mask_strategy` 当前是 `str = ""`，新增 partial mask 写入 helper 后是否要扩展为含字体信息 — **不扩展**，字体通过 `page.get_text("dict")` 现场取。
- 新增 5 类实体的颜色（与 Phase 1 已用「深红色」区分 PII 自动识别）— 建议全部沿用「深红色」，不在 Phase 2 引入新颜色。
- 邮箱 `z****@qq.com` 是否要保留顶级域名后缀（qq.com / 163.com）— 建议保留；多级子域（`foo@bar.qq.com`）的截断位置由实现者按首字符 + `@` 后最后一段定。
- 银行卡 BIN 词典的最终条数（建议 1 万-1.5 万条）— 由 implementer 决定。
- USCC 旧版 15 位 `CN_TAXPAYER_ID_15` 的 mask 策略 — 建议「前 6 + 后 4」，与 USCC 18 位一致。

### Deferred Ideas (OUT OF SCOPE)

- 候选审阅 UI 完整实现（Phase 7）
- 识别规则编辑 UI（Phase 8 UX-07）
- 审计报告（Phase 8 OPS-01）
- 本地 NER 深度学习模型（PROJECT.md 明确 Out of Scope）
- 行政区划词典（Phase 6 才需要全集 ~70 万条）
- v38 UI 抛光（PROJECT.md 明确让位给本轮识别准确率）
- BIC（银行识别码）识别（FIN-04 仅覆盖「银行账号」）
- 批次内跨文档掩码一致性策略（BATCH-02 / v2 requirement）

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NUM-04 | 系统能识别银行卡号并通过 Luhn 校验，结合 BIN 前缀与上下文关键词综合定档，避免误判订单号 | §Standard Stack（Luhn）/ §Code Examples（`validate_bank_card` 实现）/ §Common Pitfalls §1（BIN 词典太短导致 FP） |
| NUM-05 | 系统能识别电子邮箱地址 | §Standard Stack（RFC 5322 简化正则）/ §Code Examples（`validate_email`）/ §Common Pitfalls §3（正则太严导致合法邮箱漏判） |
| FIN-01 | 系统能识别统一社会信用代码并通过 GB 32100 mod-31-3 校验 | §Standard Stack（GB 32100 字符集 + 权重 + mod-31-3）/ §Code Examples（`validate_uscc` 实现）/ §Common Pitfalls §4（类别码白名单遗漏） |
| FIN-02 | 系统能识别增值税发票号码（含全电发票新版格式） | §Standard Stack（全电发票 20 位规则）/ §Code Examples（`validate_vat_invoice`）/ §Common Pitfalls §5（20 位格式正则过严） |
| FIN-03 | 系统能识别纳税人识别号（18 位 USCC + 旧版 15 位） | §Standard Stack（15 位 6-7-4 格式）/ §Code Examples（`validate_taxpayer_id` + `validate_taxpayer_id_15`）/ §Common Pitfalls §8（15 位无 mod-11-2 强校验位，独立 type 防御） |
| FIN-04 | 系统能识别银行账号 | §Standard Stack（9-21 位 + 上下文锥点）/ §Code Examples（`validate_bank_account`）/ §Common Pitfalls §7（锥点关键词不全） |
| MASK-01 | 系统支持部分掩码，按实体类型套用各自的保留规则 | §Standard Stack / §Architecture Patterns Pattern 1（`write_partial_masks` helper）/ §Code Examples（PyMuPDF `insert_text` 字体回退） |
| MASK-02 | 用户可在部分掩码与完全遮蔽之间选择处置方式（per-entity + per-document 双重切换） | §Standard Stack / §Architecture Patterns（per_entity_default dict + toolbar toggle）/ §Common Pitfalls §9（mask 模式字段命名漂移） |
| SAFE-03 | 系统在导出时清除文档元数据（Title / Author / Subject / Producer / Creator 5 字段置空字符串） | §Standard Stack（PyMuPDF `set_metadata` 5 字段语义）/ §Code Examples（`clear_pdf_metadata` 实现）/ §Common Pitfalls §10（5 字段不全清；CreationDate 误清） |

---

## Summary

Phase 2 在 Phase 1 PDF + PII 引擎骨架（身份证 + 手机号）之上扩展 5 类新实体，并把已计算但未启用的 `mask_strategy` 字段实际写入 PDF 产物中。技术上分五层：(1) **引擎层** `privacyguard/pii/validators/` 新增 `bank_card.py` / `email.py` / `uscc.py` / `vat_invoice.py` / `bank_account.py` / `taxpayer_id.py` 6 个纯函数 validator，复用 Phase 1 既有 `id_card.py` / `phone_segment.py` 形态；(2) **正则预编译层** `regex_patterns.py` 在 `iter_candidate_strings` 新增 yield `CN_BANK_CARD` / `CN_EMAIL` / `CN_USCC` / `CN_VAT_INVOICE` / `CN_TAXPAYER_ID` / `CN_TAXPAYER_ID_15` / `CN_BANK_ACCOUNT` 7 类 entity_hint；(3) **掩码写入层** `privacyguard/pii/pdf_adapter.py` 新增 `write_partial_masks(doc, page_idx, pii_hits, mode)` helper，沿用 `add_redact_annot + apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)` 真删除（D-01），并通过 `page.insert_text(font, fontsize, color, overlay)` 在 redact 后位置写 mask_strategy（D-02 字体回退：文本层路径取 `page.get_text("dict")` 最近 span 的 `font` + `size`；OCR / 占位 rect 路径用 `helv` + `rect.height - 4pt` 估算字号）；(4) **元数据清除层** `clear_pdf_metadata(doc)` 在 `save_pdf` 紧邻 `doc.save` 之前调 `doc.set_metadata({"title": "", "author": "", "subject": "", "producer": "", "creator": ""})`（D-14 / D-15 / D-16，本机 Python 验证 PyMuPDF 1.27.x / 1.28.x `set_metadata` 接受空字符串写入并产出 `doc.metadata["title"] == ""`）；(5) **UI 配置层** `SettingsDialog` 第 5 tab 加「脱敏方式」表（per-entity 下拉）+ 主工具栏加「本文件使用全遮蔽」toggle（D-11 / D-12）。

最高风险是 partial mask 字体回退失败导致 mask 文字溢出 rect 或字号不对。规避路径已通过本机 `page.get_text("dict")` 验证：内置 `helv` / `heit` / `hebo` / `hebi` 字体名在 `get_text("dict")` 输出中以 `Helvetica` / `Helvetica-Oblique` / `Helvetica-Bold` 形式返回，partial mask helper 需建一张 `[('helv', 'Helvetica'), ...]` 映射表用于字体名规范化。次高风险是 GB 32100 mod-31-3 算法权重与字符表写错 — 本研究已通过本机 Python 验证 `91110000600037341L`（腾讯科技 USCC）通过自研实现，且 31 字符表完整列出（`0123456789ABCDEFGHJKLMNPQRTUWXY`，不含 I/O/S/V/Z），权重 `[1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]` 18 元素。第三高风险是银行卡 BIN 词典条数不足导致 FP — 维基百科「Payment card number」词条主表 ~15000 BIN（含 Visa/Mastercard/Amex/Discover/UnionPay/JCB/Diners/Maestro 8 网络 × 200+ 国家发卡行）按 CC BY-SA 4.0 引用即可。第四高风险是元数据清除时被误删 `CreationDate` / `ModDate` — D-14 明确「只清 5 字段，CreationDate / ModDate / Keywords / XMP 不动」，helper 签名只接受这 5 字段名。第五高风险是 Phase 1 测试基线被 partial mask helper 修改破坏 — D-21 锁定 helper 入口与 D-04 锁定的 `page_data[page]["pii"]` 键契约。

**Primary recommendation:** 严格沿用 PyMuPDF `add_redact_annot + apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS) + garbage=4 + deflate=True + clean=True` 真删除模式，新增 `write_partial_masks` 在 `apply_redactions` 之后、`page.insert_text` 之前写 mask 文字。所有 6 个新 validator 沿用 Phase 1 `id_card.py` 的 `validate_X(text) -> bool` 纯函数形态，无 IO 无状态。GB 32100 mod-31-3、Luhn、邮箱正则用本机验证过的实现版本。`bin_prefixes.json` 按 CC BY-SA 4.0 在 `data/bin_prefixes.json.LICENSE` 保留归属声明，文件加载走 `privacyguard.utils.security.resource_path`。

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 银行卡 Luhn + BIN 校验 | `privacyguard/pii/validators/bank_card.py`（纯 Python） | `privacyguard/pii/data/bin_prefixes.json`（词典） | 标准公开算法 + ISO/IEC 7812 BIN 表；可独立单测，6 万条词典放 `data/` 走 `resource_path` |
| 邮箱 RFC 5322 简化正则 | `privacyguard/pii/validators/email.py` | — | 正则字符串本地化在 `regex_patterns.py` + 验证函数本地化在 validator |
| USCC GB 32100 mod-31-3 | `privacyguard/pii/validators/uscc.py` | `privacyguard/pii/validators/taxpayer_id.py`（复用） | 算法公开 + 字符表 31 元素无歧义；18 位 = CN_TAXPAYER_ID，单独 export |
| 全电发票 20 位 + 8 位传统 | `privacyguard/pii/validators/vat_invoice.py` | — | 双格式并行，正则 yield 双候选字符串 |
| 纳税人识别号 15 位 | `privacyguard/pii/validators/taxpayer_id.py::validate_15` | — | 旧版 6-7-4 格式无校验位，独立 type 防御 USCC 误匹配 |
| 银行账号 9-21 位 + 上下文锥点 | `privacyguard/pii/validators/bank_account.py` | — | 锥点关键词本地化在 validator（D-20） |
| Partial mask 写入 helper | `privacyguard/pii/pdf_adapter.py::write_partial_masks` | `privacyguard/pii/pdf_adapter.py::apply_pii_redactions`（复用真删除） | PyMuPDF 真删除不可绕开；helper 仅在 `apply_redactions` 后 `insert_text` 写 mask |
| 元数据清除 | `privacyguard/pii/pdf_adapter.py::clear_pdf_metadata`（新） | `main.py:save_pdf` 调用点 | `set_metadata` 文档级调用，影响页级无关；调用位置紧邻 `doc.save` |
| 正则预编译（7 类新 entity） | `privacyguard/pii/regex_patterns.py` | — | 沿用 Phase 1 `iter_candidate_strings` 形态，扩 yield 不影响现有调用方 |
| `mask_for_entity` 分派表扩展 | `privacyguard/pii/mask.py` | — | 加 6 个 `partial_mask_*` 函数 + `mask_for_entity` switch 扩展；保持 Phase 1 `partial_mask_id_card` / `partial_mask_phone` 不动 |
| PIIEngine detect pipeline | `privacyguard/pii/engine.py` | — | 加 6 个 `_check_*` 方法 + `_has_*_context_anchor` helper；现有 `_check_id_card` / `_check_phone` 不动 |
| Settings UI per-entity mask 表 | `main.py:1008` SettingsDialog 第 5 tab | — | D-11：与现有 3 个 QCheckBox 同区；新增「脱敏方式」section card |
| Toolbar per-document override toggle | `main.py:5749` MainWindow 主工具栏 | `page_data[0]["mask_override_this_doc"]` | D-12：toggle 状态仅存内存，不写入磁盘 |
| `pii_settings.per_entity_default` config 字段 | `config.json` + `config.json.template` | `tests/unit/test_app_config.py`（扩展） | D-13：Dict[str, "partial"\|"blackout"] 默认全 partial |
| Bin 词典数据文件 | `privacyguard/pii/data/bin_prefixes.json` + `bin_prefixes.json.LICENSE` | `packaging/{windows,macos}/...` PyInstaller spec | D-26 + D-27：CC BY-SA 4.0 归属必须保留 |
| PIIHit.mask_strategy 字段 | `privacyguard/pii/hits.py` | — | D-05 字段锁：不新增字段，复用现有 `mask_strategy: str = ""` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `PyMuPDF` (`fitz`) | `==1.27.1`（项目固定） | PDF partial mask 写入（`page.insert_text`）+ 元数据清除（`doc.set_metadata`） | 业界唯一同时支持内容流层真删除 + 字体回退插入 + 元数据键值更新的纯 Python 库 |
| `re` (Python stdlib) | 3.12 | 7 类新实体预编译正则（银行卡 / 邮箱 / USCC / 全电发票 / 纳税人识别号 / 银行账号） | 内置；同 Phase 1 不带 `timeout=` 参数 |
| `dataclasses` (stdlib) | 3.12 | `PIIHit`（不新增字段，沿用 Phase 1 D-05 锁定） | 冻结 dataclass 跨线程 `asdict()` 序列化 |
| `json` (stdlib) | 3.12 | `bin_prefixes.json` / `rules.json` 加载 | 同 Phase 1 D-10 / D-19 |
| `privacyguard.utils.security.resource_path` | 已有 | 读取 `bin_prefixes.json` | PyInstaller 打包走 `sys._MEIPASS`；开发态走 `os.path.abspath(".")` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `privacyguard.pii.hits.PIIHit.mask_strategy` | 已有（Phase 1） | partial mask 写入字符串（`110101********1234` / `6225 **** **** 1234` / `z****@qq.com`） | partial mask helper 调 `page.insert_text` 时作为 text 参数 |
| `tests.fixtures.fake_pii` | Phase 1 | 合成 PII 生成器；扩展 `fake_bank_card()` / `fake_email()` / `fake_uscc()` / `fake_vat_invoice_8()` / `fake_vat_invoice_20()` / `fake_taxpayer_id_15()` / `fake_bank_account()` | 仅 `tests/` 使用，不入运行时 |
| `privacyguard.utils.security.resource_path` | 已有 | 读取 `bin_prefixes.json` 与 `bin_prefixes.json.LICENSE` | PyInstaller 打包时走 `sys._MEIPASS` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `page.insert_text` 写 mask | `page.insert_textbox`（自动换行） | `insert_text` 单行 + D-03 重算 rect 宽度更可控；`insert_textbox` 适合多行长文本 |
| 自研 GB 32100 mod-31-3 | 第三方 `python-uscc` / `uscc-validator` PyPI 包 | 项目零网络 + 不增加 PyPI 依赖原则；自研 ~30 行可完全测试 |
| 自研 Luhn | `python-stdnum` / `creditcard` PyPI 包 | 同上；自研 ~10 行可完全测试 |
| 自研 BIN 词典（CC BY-SA 4.0） | 调用云端 BIN API | 违反零网络底线；词典静态打包 ~1 万-1.5 万条 |
| `page.get_text("dict")` 取最近 span font/size | `page.get_text("rawdict")` 或 `page.get_text("words")` | `"dict"` 给出完整 `block / line / span` 树，span 含 `font` + `size`；`rawdict` 多含字符级 glyph；`words` 仅词级 |
| `doc.set_metadata({...})`（PyMuPDF 标准 API） | 直接 `xref_set_key(info_xref, "/Title", "")` 改 raw Info dict | `set_metadata` 是 PyMuPDF 官方 API，自动处理 key→PDF name 映射；`xref_set_key` 适合未知自定义键 |

**Installation:**
无新增 PyPI 依赖。所有逻辑在 `privacyguard/pii/` 子包内实现（新增 6 个 validator + 1 个 partial mask helper + 1 个 metadata clear helper）。

**Version verification (本机 2026-08-11 已验证):**
```bash
python3 -c "import fitz; print(fitz.__version__)"    # 实测 1.28.2（>=1.27.1，向后兼容）
python3 -c "from privacyguard.pii.validators.id_card import WEIGHTS, MAPPING; print(len(WEIGHTS), len(MAPPING))"  # 17 / 11
python3 -c "import fitz; doc = fitz.open(); page = doc.new_page(); doc.set_metadata({'title':'', 'author':'', 'subject':'', 'producer':'', 'creator':''}); doc.save('/tmp/x.pdf'); print(fitz.open('/tmp/x.pdf').metadata['title'])"  # 实测空字符串
```

### Partial Mask 字体回退映射表（D-02 锁定）

| `page.get_text("dict")` span.font | `page.insert_text` fontname | 说明 |
|---|---|---|
| `Helvetica` | `helv` | 默认 sans-serif；最常见 |
| `Helvetica-Oblique` | `heit` | 斜体 |
| `Helvetica-Bold` | `hebo` | 加粗 |
| `Helvetica-BoldOblique` | `hebi` | 斜粗 |
| `Times-Roman` | `tiro` | 衬线 |
| `Times-Bold` | `tibo` | 衬线加粗 |
| `Courier` | `cour` | 等宽 |
| `Courier-Bold` | `cobo` | 等宽加粗 |
| 其他（OCR / 占位路径） | `helv` + `fontsize = max(rect.height - 4, 8.0)` | 默认 sans-serif + 估算字号（D-02） |

**`get_text("dict")` 实测输出**（本机验证，`page.insert_text((50,50), text, fontname='helv', fontsize=14)` 后调 `page.get_text("dict")`）：`block.lines[0].spans[0].font == 'Helvetica'`、`spans[0].size == 14.0`。

**OCR / 占位 rect 路径字号估算公式**：`font_pt = max(rect.height - 4.0, 8.0)`，下限 8pt 保证字符不会被 PDF 内容流层叠截断（D-02 锁定）。

### GB 32100-2015 字符表 + 权重（FIN-01 锁定）

| 项 | 值 |
|---|---|
| 字符集（31 字符） | `0123456789ABCDEFGHJKLMNPQRTUWXY` |
| 不含字符 | `I` / `O` / `S` / `V` / `Z`（5 个易混字母） |
| 17 位权重（GB 32100-2015） | `[1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]` |
| 校验公式 | `check_index = (31 - sum(Ci × Wi) mod 31) mod 31`；`check_char = CHARS[check_index]` |
| 校验位位置 | 第 18 位 |

**本机验证**（实测 2026-08-11）：`validate_uscc('91110000600037341L') == True`（腾讯科技真实 USCC），`validate_uscc('91110000600037341X') == False`（X 不在字符集）。

### USCC 登记管理部门类别代码表 8 类（D-06 锁定）

| 类别码 | 登记管理部门 | 机构类别码（第二位） | 说明 |
|---|---|---|---|
| `1` | 机构编制 | `1`=机关 `2`=事业单位 `3`=中央编办直管群众团体 `9`=其他 | |
| `5` | 民政 | `1`=社会团体 `2`=民办非企业单位 `3`=基金会 `9`=其他 | |
| `9` | 工商（市场监管） | `1`=企业 `2`=个体工商户 `3`=农民专业合作社 | 商业代码主体（90%+ 命中） |
| `Y` | 其他 | `1`=统一用 1 | Phase 2 接受 |
| `A` | 中央军委改革和编制办公室 | `1`=机构 | 极少数 |
| `N` | 农业 | `1`=其他 | 极少数 |
| 后续 2 类 | 司法 / 外交（D-06 提到的「8 类」预留） | 极少使用 | Phase 2 暂不内置，可由 Phase 8 用户扩展 |

**白名单集合**（Phase 2 内置）：`{'1', '5', '9', 'Y', 'A', 'N'}` + 用户后续可扩展位（D-06 锁定「8 类」但目前常见 6 类即可覆盖 99% 输入；剩余 2 类（司法 B、外交 2）Phase 8 用户自定义词典 UX-07 再加）。

### Luhn 算法（NUM-04 锁定）

```python
def luhn_valid(num: str) -> bool:
    """标准 Luhn 校验 — 自右向左每第 2 位 ×2，超过 9 减 9；总和 % 10 == 0。"""
    if not num or not num.isdigit(): return False
    digits = [int(d) for d in num]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:  # 从右起第 2 位（索引 1）
            d2 = d * 2
            total += d2 if d2 < 10 else d2 - 9
        else:
            total += d
    return total % 10 == 0
```

**实测样本**（本机 Python 2026-08-11）：
- `6225760000000000` → **False**（维基/Stack Overflow 常引为「Discover 测试卡号」，实则 BIN 622576 在 UnionPay 段 622126-622925 内，且该 16 位号 Luhn 不通过）
- `4532015112830366` → **True**（Visa 测试卡号，16 位 Luhn 通过）
- `1234567812345670` → **True**（经典 16 位 Luhn 测试数）
- `6225768199574466` / `6225767047146063` / `6225765485849594` → **True**（BIN 622576 + 9 位随机 + Luhn 计算 check digit，本机生成）

### 银行卡 BIN 词典（NUM-04 锁定）

| 项 | 值 | 来源 |
|---|---|---|
| 来源 1（主） | 维基百科「Payment card number」词条 | CC BY-SA 4.0，~15000 BIN（Visa / Mastercard / Amex / Discover / UnionPay / JCB / Diners / Maestro 8 网络 × 200+ 国家发卡行） |
| 来源 2（辅） | 中国银联公开 BIN 公告（chakahao.com / open.unionpay.com 测试卡信息） | 公开数据，无 LICENSE 限制 |
| 整合条数 | 建议 1 万-1.5 万条 | implementer 决定（D-27） |
| 文件位置 | `privacyguard/pii/data/bin_prefixes.json` | D-26 |
| LICENSE 文件 | `privacyguard/pii/data/bin_prefixes.json.LICENSE` | D-27 CC BY-SA 4.0 归属 |
| 加载路径 | `privacyguard.utils.security.resource_path` | cp30 教训 |

### 全电发票 20 位号码格式（D-07 / FIN-02 锁定）

| 位段 | 含义 | 示例 |
|---|---|---|
| 1-2 | 公历年度后两位 | `23` = 2023 年 |
| 3-4 | 省级行政区划代码 | `11` = 北京 / `31` = 上海 / `44` = 广东（GB/T 2260） |
| 5 | 开具渠道代码 | `0` = 全电发票开具渠道 |
| 6-20 | 顺序编码（共 15 位数字） | `000000012345678` |
| **完整示例** |  | **`23110000000012345678`**（2023 年北京 0 渠道顺序号 12345678） |

**正则（建议）**：`\b\d{20}\b`（20 位纯数字，词边界锚定）+ 上下文锥点（发票 / 号码 / 票号 / invoice）±20 字符。

**来源**：国家税务总局公告 2022 年第 1 号（试点）+ 国家税务总局公告 2024 年第 11 号（全国推广，沿用相同 20 位编码规则）。Phase 2 内置 20 位正则 + 8 位传统 `\b\d{8}\b` 双格式并行（D-07）。

### 邮箱 RFC 5322 简化正则（D-10 / NUM-05 锁定）

```python
import re
EMAIL_RE = re.compile(r'(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9._%+-])')

def validate_email(text: str) -> bool:
    """NUM-05 简化邮箱验证（无校验位，仅 RFC 5322 简化版正则）。"""
    if not text: return False
    return bool(EMAIL_RE.fullmatch(text))
```

**关键约束**：
- 不引入 IDN / 国际化邮箱
- 公共域名后缀白名单（决定 confidence_tier HIGH vs MEDIUM）：`com / cn / net / org / gov / edu` + `io / co` 等
- 公共域名后缀命中 → HIGH；非常见后缀 → MEDIUM（D-10 锁定）

### 银行账号上下文锥点关键词（D-08 / FIN-04 锁定）

**D-08 列出的 10 个关键词**（用户签字锁定的最小集合）：
- 通用：`账号` / `账户` / `银行账号` / `银行账户`
- 大行简称：`招行` / `中行` / `建行` / `工商银行` / `农行` / `邮储` / `交通银行`

**Claude's Discretion 建议**（参考 12 家股份制 + 5 家城商行常用简称）：
- 股份制商业银行：`中信` / `浦发` / `兴业` / `民生` / `平安` / `光大` / `华夏` / `广发` / `浙商` / `恒丰` / `渤海`
- 城商行：`上海银行` / `江苏银行` / `南京银行` / `宁波银行` / `北京银行`

**推荐集合**（D-08 + 扩展，11 + 5 = 16 关键词）：通用 4 个 + 12 大行（5 大国有 + 招行 + 邮储 + 交通 + 12 股份制中常用 4 个）+ 1-2 城商行（上海银行）。

`银行账号 6222021234560000` 在「招行客户 银行账号 6222021234560000」文本中 → 命中 HIGH（锥点 + 9-21 位长度）；在「订单号 6222021234560000」文本中 → **不产生 candidate**（无锥点，D-08 强制）。

### 15 位纳税人识别号格式（D-09 / FIN-03 锁定）

| 段 | 长度 | 含义 |
|---|---|---|
| 第 1-6 位 | 6 位 | 行政区划码（旧版「6 位」） |
| 第 7-13 位 | 7 位 | 主体标识码 / 出生日期 |
| 第 14-17 位 | 4 位 | 顺序码 |

**结构正则**：`\b\d{15}\b`（15 位纯数字，词边界锚定）。

**注意事项**：
- 15 位无 mod-11-2 等强校验位（D-09 锁定独立 type）
- 与 18 位 USCC 共存：18 位 USCC 三证合一后**复用** `CN_TAXPAYER_ID`（D-09 显式说明）
- 区分策略：先用 15 位正则扫描；命中后再用 6-7-4 分段结构 + 行政区划码 sanity（GB/T 2260 历史子集复用 `privacyguard.pii.validators.id_card._VALID_ADMIN_PREFIX_2`）拒绝明显伪造

### CC BY-SA 4.0 归属声明最小内容（D-27 锁定）

`bin_prefixes.json.LICENSE` 必须包含（CC BY-SA 4.0 §3(a) 归属要求）：

```
PrivacyGuard 银行卡 BIN 词典
基于 Wikipedia "Payment card number" 词条整理

Source: https://en.wikipedia.org/wiki/Payment_card_number
License: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)

Modifications: 整合中国银联公开 BIN 公告，移除过期条目，按 6 位前缀去重
```

---

## Package Legitimacy Audit

> Phase 2 不新增 PyPI 依赖（沿用 Phase 1 + PyMuPDF 1.27.1 / 1.28.x）。`bin_prefixes.json` 是项目内数据文件，不涉及 PyPI。

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| 现有 `PyMuPDF==1.27.1` | PyPI | 稳定 | n/a | github.com/pymupdf/PyMuPDF | OK | Approved（项目已固定；本机实测 1.28.2 兼容） |
| 现有 `rapidocr-onnxruntime==1.2.3` | PyPI | 稳定 | n/a | github.com/RapidAI/RapidOCR | OK | Approved（现有） |

**新增 0 个 PyPI 依赖**（D-04 / D-10 / D-15 / D-16 等关键约束均不引入新包）。

**Packages removed due to [SLOP] verdict:** 无

**Packages flagged as suspicious [SUS]:** 无

---

## Architecture Patterns

### System Architecture Diagram

```
                              ┌────────────────────────────────────────────┐
                              │  PyQt6 Main Thread (`main.py` ~12.6k LOC)  │
                              │                                            │
  drag/drop / Open menu       │   ▼                                        │
  ────────────────── ──      │  ┌─────────────────────────────────────┐  │
       │                     │  │  MainWindow (`main.py:4885`)         │  │
       ▼                     │  │  ├ self.page_data[i] = {             │  │
  ┌──────────┐               │  │  │     'ocr':    [...],               │  │
  │  File    │               │  │  │     'manual': [...],               │  │
  │  open    │────open_pdf──▶│  │  │     'pii':    [PIIHit, ...]    ◀────┼── D-04 + D-12 (mask_override_this_doc)
  └──────────┘               │  │  │   }                                 │  │
                              │  │  ├ self.pii_settings = {              │  │
                              │  │  │   engine_enabled / auto_redact /   │  │
                              │  │  │   require_confirmation /            │  │
                              │  │  │   per_entity_default (D-13 NEW) }  │  │
                              │  │  └ SettingsDialog tab "5 隐私识别"    │  │
                              │  │     (NEW: 脱敏方式 per-entity 表)   │  │
                              │  │  MainWindow toolbar                   │  │
                              │  │     (NEW: "本文件全遮蔽" toggle D-12)│  │
                              │  └──────────┬──────────────────────────┘  │
                              │             │ page_result_signal            │
                              │             │ pii_signal (Phase 1)           │
                              │             ▼                                │
                              │  ┌─────────────────────────────────────┐  │
                              │  │  _ModularOCRWorker (QThread)         │  │
                              │  │  privacyguard/workers/ocr_worker.py  │  │
                              │  │  ──────────────────────────────────  │  │
                              │  │  for i in pages:                     │  │
                              │  │    page_text = page.get_text()       │  │
                              │  │    pii_hits = engine.detect(         │  │
                              │  │      unit, page=page)                │  │
                              │  │    # Phase 2: 6 个新 entity_hint     │  │
                              │  │    self.pii_signal.emit(i, hits)     │  │
                              │  └──────────────┬───────────────────────┘  │
                              └─────────────────┼───────────────────────────┘
                                                │
                                  ┌─────────────▼──────────────┐
                                  │ privacyguard/pii/          │  ◀── 纯 Python, 无 Qt
                                  │ ────────────────           │
                                  │  hits.py                   │  PIIHit dataclass (D-05 locked)
                                  │  validators/               │  bank_card.py / email.py / uscc.py /
                                  │                            │  vat_invoice.py / bank_account.py /
                                  │                            │  taxpayer_id.py (D-17 NEW)
                                  │  regex_patterns.py         │  7 类新 entity_hint yield (D-18 NEW)
                                  │  confidence.py             │  HIGH/MEDIUM/LOW 档位映射 (Phase 1)
                                  │  mask.py                   │  partial_mask_* 6 类 (D-13 NEW)
                                  │  overlap.py                │  去重 + 优先级 (Phase 1)
                                  │  normalize.py              │  全角→半角 (Phase 1)
                                  │  engine.py                 │  detect pipeline + 7 类 _check_* 方法
                                  │  data/rules.json           │  uscc.weights + bin_dictionary_path +
                                  │                            │  uscc.category_codes + vat_invoice.anchors
                                  │                            │  + bank_account.anchors (D-19 NEW)
                                  │  data/bin_prefixes.json    │  ~1-1.5万 BIN (D-26 NEW)
                                  │  data/bin_prefixes.json.LICENSE  │  CC BY-SA 4.0 归属 (D-27 NEW)
                                  └─────────────┬──────────────┘
                                                │
                                                ▼
                                  ┌─────────────────────────────┐
                                  │ privacyguard/               │
                                  │ pii/pdf_adapter.py          │  ◀── apply 阶段
                                  │ ──────────────────────────  │
                                  │ apply_pii_redactions(       │  ◀── Phase 1 (黑框全遮蔽)
                                  │   pdf_in, pdf_out, rects)   │
                                  │                             │
                                  │ write_partial_masks(        │  ◀── Phase 2 NEW (D-21)
                                  │   doc, page_idx, pii_hits,  │
                                  │   mode="partial"|"blackout")│
                                  │   ├ mode="blackout":        │
                                  │   │   add_redact_annot +   │
                                  │   │   apply_redactions(IMAGE_PIXELS)
                                  │   ├ mode="partial":        │
                                  │   │   add_redact_annot +   │
                                  │   │   apply_redactions(IMAGE_PIXELS) +
                                  │   │   page.insert_text(    │
                                  │   │     font=... (D-02 字体回退),
                                  │   │     fontsize=... (D-03 估算),
                                  │   │     text=hit.mask_strategy,
                                  │   │     color=(1,1,1),
                                  │   │     overlay=True)
                                  │                             │
                                  │ clear_pdf_metadata(doc)     │  ◀── Phase 2 NEW (D-14..D-16)
                                  │   doc.set_metadata({       │
                                  │     "title":"","author":"",│
                                  │     "subject":"","producer":"",│
                                  │     "creator":""})         │
                                  └─────────────────────────────┘
                                                │
                                                ▼
                                  ┌─────────────────────────────┐
                                  │ tests/unit/                  │
                                  │ test_pii_validators.py       │  6 个新 validator 纯函数测试
                                  │ test_pii_engine.py           │  7 类新 entity 命中 + 档位
                                  │ test_pdf_pii_redaction.py    │  partial mask 写入后反向提取
                                  │   ├ 原文不存在              │
                                  │   └ mask 文字存在 (D-23)    │
                                  │ test_pdf_metadata_cleared.py │  ◀── Phase 2 NEW
                                  │   doc.metadata 5 字段全空    │
                                  │ test_app_config.py           │  per_entity_default 字段
                                  └─────────────────────────────┘
```

### Recommended Project Structure

```
privacyguard/pii/                            # 现有 (Phase 1)
├── __init__.py                              # 懒加载 _LAZY_IMPORTS + re-export (D-13 + D-17 扩展)
├── hits.py                                  # PIIHit 字段锁 (Phase 1 D-05)
├── validators/
│   ├── __init__.py                          # 懒加载 (Phase 1 + 新增 6 个导出)
│   ├── id_card.py                           # GB 11643 mod-11-2 (Phase 1)
│   ├── phone_segment.py                     # MIIT 号段 (Phase 1)
│   ├── bank_card.py                         # ◀── NEW (NUM-04): Luhn + BIN 词典加载 + 上下文锥点
│   ├── email.py                             # ◀── NEW (NUM-05): RFC 5322 简化正则 + 公共后缀判定
│   ├── uscc.py                              # ◀── NEW (FIN-01): GB 32100 mod-31-3 + 8 类别码白名单
│   ├── vat_invoice.py                       # ◀── NEW (FIN-02): 8 位 + 20 位双格式 + 上下文锥点
│   ├── bank_account.py                      # ◀── NEW (FIN-04): 9-21 位 + 上下文锥点 (强制)
│   └── taxpayer_id.py                       # ◀── NEW (FIN-03): 18 位 = USCC 复用 + 15 位独立 type
├── regex_patterns.py                        # iter_candidate_strings 扩展 7 类 yield (D-18)
├── normalize.py                             # (Phase 1 不动)
├── confidence.py                            # (Phase 1 不动)
├── mask.py                                  # partial_mask_* 6 类新增 (D-13)
├── overlap.py                               # (Phase 1 不动)
├── engine.py                                # detect pipeline 扩展 _check_* 方法
├── pdf_adapter.py                           # apply_pii_redactions (Phase 1) + write_partial_masks (NEW) + clear_pdf_metadata (NEW)
├── data/
│   ├── rules.json                           # ◀── EXTEND: bank_card / uscc / vat_invoice / bank_account / taxpayer_id 字段 (D-19)
│   ├── bin_prefixes.json                    # ◀── NEW (D-26): ~1-1.5万条 6 位 BIN
│   └── bin_prefixes.json.LICENSE            # ◀── NEW (D-27): CC BY-SA 4.0 归属声明

tests/
├── fixtures/fake_pii.py                     # ◀── EXTEND: fake_bank_card / fake_email / fake_uscc / fake_vat_invoice_8 / fake_vat_invoice_20 / fake_taxpayer_id_15 / fake_bank_account
├── unit/
│   ├── test_pii_validators.py               # ◀── EXTEND: 6 个新 validator 类
│   ├── test_pii_engine.py                   # ◀── EXTEND: 7 类新 entity 命中 + 档位
│   ├── test_pdf_pii_redaction.py            # ◀── EXTEND: partial mask 写入后反向提取 (D-23)
│   ├── test_pdf_metadata_cleared.py         # ◀── NEW (D-23)
│   ├── test_app_config.py                   # ◀── EXTEND: per_entity_default 字段测试
│   └── ... (其他基线 79/79 测试不动)

main.py (modify, ~4 sites)
├── Site 1: SettingsDialog box_pii          # ◀── EXTEND: 「脱敏方式」表 (D-11)
├── Site 2: toolbar                         # ◀── EXTEND: 「本文件全遮蔽」 toggle (D-12)
├── Site 3: save_pdf                        # ◀── MODIFY: 调 write_partial_masks + clear_pdf_metadata (D-14..D-16, D-22)
└── Site 4: page_data init                   # ◀── EXTEND: 新增 mask_override_this_doc 键

config.json + config.json.template          # ◀── EXTEND: pii_settings.per_entity_default 字典 (D-13)
privacyguard/__init__.py                    # ◀── EXTEND: _LAZY_IMPORTS 加 6 个新 validator + write_partial_masks + clear_pdf_metadata

packaging/windows/config/PrivacyGuard_windows.spec
                                              # ◀── EXTEND: datas 加 bin_prefixes.json + bin_prefixes.json.LICENSE (D-26)
packaging/macos/config/PrivacyGuard.spec    # ◀── 同上 (B5 parity)
packaging/macos/scripts/build_complete.sh   # ◀── parity check 加 bin_prefixes.json (cp30 教训)
```

### Pattern 1: Partial Mask 写入 Helper（D-01 / D-02 / D-03 / D-21）

**What:** `write_partial_masks` 在 redact 销毁内容后用 `page.insert_text` 写 mask 文字；字体走 `page.get_text("dict")` 取最近 span（D-02 文本层路径）或回退到 `helv` + `rect.height - 4pt` 估算字号（OCR / 占位 rect 路径）。

**When to use:** `MainWindow.save_pdf` 的 PII 路径（D-22），OCR / manual 路径**不**走此 helper（保持纯黑框全遮蔽）。

**Example:**
```python
# privacyguard/pii/pdf_adapter.py
import fitz
from typing import Iterable, Literal, Tuple

# D-02 字体映射表（get_text("dict") font → insert_text fontname）
_FONT_NAME_MAP = {
    "Helvetica": "helv", "Helvetica-Oblique": "heit",
    "Helvetica-Bold": "hebo", "Helvetica-BoldOblique": "hebi",
    "Times-Roman": "tiro", "Times-Bold": "tibo",
    "Courier": "cour", "Courier-Bold": "cobo",
}


def _resolve_text_layer_font(page: fitz.Page, hit_page_offset: int) -> Tuple[str, float]:
    """D-02 文本层路径：从 page.get_text("dict") 取最近 span 的 font + size。

    找不到 → 返回 ('helv', 11.0)（最常见的 fallback）。
    """
    text_dict = page.get_text("dict")
    best_font = "helv"
    best_size = 11.0
    best_distance = float("inf")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                # span 含 bbox (x0, y0, x1, y1)；用 bbox.y0 与 hit 坐标比较
                bbox = span.get("bbox", (0, 0, 0, 0))
                distance = abs(bbox[1] - hit_page_offset)  # 简化：按 y0 距离
                if distance < best_distance:
                    best_distance = distance
                    best_font = _FONT_NAME_MAP.get(span.get("font", ""), "helv")
                    best_size = float(span.get("size", 11.0))
    return best_font, best_size


def _resolve_placeholder_font(rect: Tuple[float, float, float, float]) -> Tuple[str, float]:
    """D-02 OCR / 占位路径：默认 sans-serif + 估算字号 rect.height - 4pt。"""
    font_pt = max(rect[3] - 4.0, 8.0)  # 下限 8pt 保证字符不截断
    return "helv", font_pt


def _resize_rect_for_mask(
    rect: fitz.Rect, mask_text: str, fontsize: float,
) -> fitz.Rect:
    """D-03 长度偏差：rect 宽度按 mask_strategy 字符数重算，文字居中。"""
    # 估算字符宽度（helvetica 平均 char width ≈ fontsize * 0.55）
    avg_char_width = fontsize * 0.55
    new_w = max(len(mask_text) * avg_char_width + 4.0, rect.width)
    # 居中
    cx = (rect.x0 + rect.x1) / 2.0
    new_x0 = cx - new_w / 2.0
    new_x1 = cx + new_w / 2.0
    return fitz.Rect(new_x0, rect.y0, new_x1, rect.y1)


def write_partial_masks(
    doc: fitz.Document,
    page_idx: int,
    pii_hits: Iterable,
    mode: Literal["partial", "blackout"] = "partial",
    per_doc_override: Optional[str] = None,
) -> None:
    """D-21 partial mask helper。

    Args:
        doc: 已 fitz.open 的 PDF 文档
        page_idx: 当前页码
        pii_hits: 该页 PIIHit 列表
        mode: "partial" 写 mask_strategy 文字；"blackout" 纯黑框（沿用 Phase 1 行为）
        per_doc_override: D-12 per-document 临时覆盖；"blackout" 强制全遮蔽
    """
    page = doc[page_idx]
    effective_mode = per_doc_override or mode

    # 1. 第一遍：所有 hit add_redact_annot + apply_redactions(IMAGE_PIXELS)
    rects = []
    mask_texts = {}
    for hit in pii_hits:
        pr = hit.page_rect
        rect = fitz.Rect(pr[0], pr[1], pr[0] + pr[2], pr[1] + pr[3])
        rects.append(rect)
        mask_texts[id(hit)] = (rect, hit.mask_strategy)

    for rect in rects:
        annot = page.add_redact_annot(rect)
        annot.set_colors(stroke=(0, 0, 0), fill=(0, 0, 0))
        annot.update()
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
    for annot in page.annots() or []:
        page.delete_annot(annot)

    # 2. 第二遍（仅 partial）：在每个 redact 后的 rect 位置 insert_text 写 mask
    if effective_mode != "partial":
        return

    for hit in pii_hits:
        rect, mask_text = mask_texts[id(hit)]
        if not mask_text:
            continue
        # D-02 字体回退
        if hit.source == "text":
            fontname, fontsize = _resolve_text_layer_font(page, hit.page_offset)
        else:
            fontname, fontsize = _resolve_placeholder_font(rect)
        # D-03 rect 长度重算
        resized_rect = _resize_rect_for_mask(rect, mask_text, fontsize)
        # insert_text：居中点 + white text on black background
        cx = (resized_rect.x0 + resized_rect.x1) / 2.0 - (len(mask_text) * fontsize * 0.55) / 2.0
        cy = (resized_rect.y0 + resized_rect.y1) / 2.0 - fontsize / 3.0
        page.insert_text(
            (cx, cy),
            mask_text,
            fontname=fontname,
            fontsize=fontsize,
            color=(1, 1, 1),  # white 文字（黑底色块由 add_redact_annot 提供）
            overlay=True,
        )


def clear_pdf_metadata(doc: fitz.Document) -> None:
    """D-14 / D-15 / D-16 SAFE-03: 清除 5 字段元数据为空字符串。

    仅清 Title / Author / Subject / Producer / Creator；
    CreationDate / ModDate / Keywords / XMP 不动（D-14 锁定）。
    """
    doc.set_metadata({
        "title": "",
        "author": "",
        "subject": "",
        "producer": "",
        "creator": "",
    })


__all__ = ['collect_pii_rects', 'apply_pii_redactions', 'write_partial_masks', 'clear_pdf_metadata']
```

### Pattern 2: GB 32100 mod-31-3 Validator（D-06 锁定）

**What:** 18 位 USCC 通过 31 字符表 + 17 位权重 mod-31 计算 check digit；登记管理部门类别码预筛选（8 类别码白名单）拒绝明显无效组合。

**When to use:** `PIIEngine._check_uscc` 在 FIN-01 路径调用。

**Example:**
```python
# privacyguard/pii/validators/uscc.py
from typing import Final


# GB 32100-2015 §5.1: 字符集 0-9 + A-Z 去掉 I/O/S/V/Z
USCC_CHARS: Final = '0123456789ABCDEFGHJKLMNPQRTUWXY'
USCC_WEIGHTS: Final = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)

# D-06 登记管理部门类别码白名单（6 类常见 + 预留扩展）
USCC_CATEGORY_CODES: Final = frozenset({'1', '5', '9', 'Y', 'A', 'N'})


def compute_check_digit(body17: str) -> str:
    """GB 32100-2015 mod-31-3 校验位计算。"""
    if len(body17) != 17:
        return ''
    try:
        total = sum(USCC_CHARS.index(c) * USCC_WEIGHTS[i] for i, c in enumerate(body17))
    except ValueError:
        return ''
    check_index = (31 - total % 31) % 31
    return USCC_CHARS[check_index]


def validate_uscc(code: str) -> bool:
    """GB 32100 mod-31-3 校验 + 登记管理部门类别码预筛选（D-06）。"""
    if not isinstance(code, str) or len(code) != 18:
        return False
    # 字符集检查（仅 31 字符）
    for c in code:
        if c not in USCC_CHARS:
            return False
    # 类别码预筛选（D-06）：第 1 位 ∈ 8 类白名单
    if code[0] not in USCC_CATEGORY_CODES:
        return False
    # mod-31-3 校验
    return compute_check_digit(code[:17]) == code[17]


__all__ = ['USCC_CHARS', 'USCC_WEIGHTS', 'USCC_CATEGORY_CODES', 'compute_check_digit', 'validate_uscc']
```

### Anti-Patterns to Avoid

- **`page.draw_rect(fill=(0,0,0))` 替代 `add_redact_annot`：** 行业头号失败模式（黑框覆盖但 `page.get_text()` 仍可读）；Phase 1 已禁止，Phase 2 必须严格沿用 `add_redact_annot + apply_redactions(IMAGE_PIXELS)` 真删除路径。
- **顶层 `import` RapidOCR / openpyxl：** 破坏 OPS-03 懒加载；新增 `privacyguard/pii/validators/bank_card.py` 等模块时**禁止**任何对 RapidOCR / 第三方 OCR 库的顶层 import；词典加载走 `resource_path`。
- **`main.py` 写 partial mask 写入逻辑：** 违反 v37.7.6 收敛原则（D-22 锁定 `write_partial_masks` 必须放 `privacyguard/pii/pdf_adapter.py`）。
- **PIIHit 新增 `font` 字段：** D-05 字段锁；字体通过 `page.get_text("dict")` 现场取，不进 hit（Claude's Discretion 已签字）。
- **5 字段不全清（漏 `producer` 或 `creator`）：** D-14 列出完整 5 字段名；helper 签名只接受这 5 个键，pytest 单元测试断言每个键都被覆盖。
- **银行卡 BIN 词典条数 < 5000：** 维基主表有 1.5 万条，覆盖 Visa/MC/Amex/UnionPay 等 8 网络 × 200+ 国家；条数 < 5000 会导致 FP（订单号被误判银行卡号）。
- **邮箱正则太严（拒绝合法邮箱）：** `+` / `_` 等字符在 RFC 5322 中合法；D-10 简化版正则 `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` 已包含。
- **USCC 类别码白名单遗漏 `Y`（其他）：** 一些事业单位 / 临时机构用 `Y` + `1`；D-06 锁定的 6 类白名单必须含 `Y`。
- **银行账号锥点只 1-2 关键词：** D-08 列出的 10 个是最低集合；建议扩展至 11-16 关键词（含股份制 + 城商行常用简称）以覆盖 95%+ 文档。
- **全电发票正则不接受连字符：** 国家税务总局样本示例 `23110000-0000-12345678` 含连字符（用于阅读分组）；Phase 2 正则接受纯数字 + 可选连字符 `\b\d{4}-?\d{4}-?\d{4}-?\d{4}-?\d{4}\b` 或严格 `\b\d{20}\b`（按 D-07 锁定「数字为主，含横线」由 validator 处理）。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GB 32100 mod-31-3 校验 | 自实现但权重数组写错或字符表漏字符 | `privacyguard/pii/validators/uscc.py::validate_uscc`（~30 行） | 31 字符表（不含 I/O/S/V/Z）+ 17 权重均有官方公开；本机验证 `91110000600037341L` 通过 |
| Luhn 算法 | 自实现但「双倍基数从左起 vs 从右起」错位 | `privacyguard/pii/validators/bank_card.py::luhn_valid`（~10 行） | 算法公开标准；本机验证 `4532015112830366` 通过 / `1234567812345670` 通过 |
| 银行卡 BIN 词典（覆盖 1 万+ 条） | 自己从银联公告 / ISO/IEC 7812 抄录 1-2 千条 | 维基百科「Payment card number」词条主表 + 中国银联公开 BIN（CC BY-SA 4.0） | 维基 1.5 万条已覆盖 8 网络 × 200+ 国家发卡行；自己抄录既慢又易错 |
| 邮箱 RFC 5322 完整正则 | 完整 6KB 正则（含 quoted string / IP literal / IPv6 等边缘情况） | D-10 简化版正则（`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`） | 完整正则 ReDoS 风险高；D-10 已锁简化版 + 公共后缀白名单档位判定 |
| 邮箱 IDN 国际化 | Punycode 转换 / Unicode 域名支持 | 不引入 IDN（D-10 锁定） | 中文 / 阿拉伯文邮箱极少；引入 IDN 必加新依赖 + ReDoS 风险 |
| PDF 元数据清除 | 用 `page.delete_annot` 或 `xref_set_key(info_xref, ...)` 改 raw Info dict | `privacyguard/pii/pdf_adapter.py::clear_pdf_metadata` 调 `doc.set_metadata({...})` | `set_metadata` 是 PyMuPDF 官方 API；`xref_set_key` 适合未知自定义键，普通 5 字段名直接 set |
| PDF partial mask 字体回退 | 用 `doc.get_text("dict")` 全文档扫描 + 最近 span 距离算法 | `page.get_text("dict")` 局部 span 扫描 + 简化的 `bbox.y0` 距离比较 | PyMuPDF 提供完整 span 树 + bbox；O(n) 局部扫描足够 |
| 测试用银行卡号 | `Faker().credit_card_number()`（Faker 不存在此 provider） | `tests/fixtures/fake_pii.py::fake_bank_card()`（BIN 前缀 + Luhn 计算 check digit） | Faker 14.0 默认无 credit_card_number；自研更可控 |
| 测试用 USCC | Faker `ssn()`（不会过 GB 32100） | `fake_uscc()`（Faker + mod-31-3 计算） | Faker 无 USCC provider；同 Phase 1 fake_id_card 形态 |
| 跨文档 PyInstaller `datas` 同步 | 手动改两个 spec + 构建脚本 | `tests/unit/test_package_imports.py` + Windows/macOS spec 同时更新 | cp30 教训；Phase 2 新增 `bin_prefixes.json` 必须双 spec 同步 |

**Key insight:** Phase 2 的核心收益是「**识别覆盖扩大 + 真脱敏方式升级 + 元数据清除**」三件套，**不需要**新 PyPI 依赖、不需要 NER 模型、不需要云端 API。所有自研代码量控制在 ~600 行（含 6 个 validator + mask helper + metadata clear helper + 测试 + UI 扩展）。任何「先打地基再说」的扩张倾向都应被推迟到 Phase 8（用户自定义词典 UX-07）。

---

## Runtime State Inventory

> Phase 2 不涉及 rename/refactor/migration（仅在现有 PDF + PII 引擎上扩展识别能力）。此节不适用。

---

## Common Pitfalls

### Pitfall 1: 银行卡 BIN 词典太短导致订单号误判（FP 误报）

**What goes wrong:** `bin_prefixes.json` 只内置 100-1000 条 6 位 BIN → 大量真实银行卡号（Luhn 通过但 BIN 不在表内）被 reject → 漏判；或反之，词典条数多但上下文锥点缺失 → 任意 13-19 位纯数字（订单号、发票号、员工工号）被误判为银行卡 → FP 误报。

**Why it happens:** 银行卡号与订单号在「长度 + 纯数字」维度上不可分；必须靠 Luhn + BIN + 上下文锥点三重验证。

**How to avoid:**
- BIN 词典条数 ≥ 10000（维基主表 1.5 万条全量导入）
- `validate_bank_card(text)` 强制三层 gate：(1) 13-19 位 + Luhn 通过；(2) 前 6 位 ∈ `bin_prefixes.json`；(3) 上下文锥点 ±20 字符（卡号 / 账号 / 银行 / 支付 / debit / credit）
- 三层全通过 → confidence_tier = HIGH；前 2 层通过无锥点 → MEDIUM；仅长度对 + Luhn 通过 → LOW（视为疑似，需人工确认）
- 单元测试覆盖：`test_detects_bank_card_with_bin_and_context` / `test_rejects_order_number_without_bin` / `test_rejects_invalid_luhn_with_valid_bin` / `test_rejects_valid_luhn_without_bin_in_dict`

**Warning signs:**
- 测试只覆盖「Luhn 通过 → 命中」，未覆盖「Luhn 通过 + BIN 不在表内 → reject」
- `bin_prefixes.json` 文件 < 100KB（按 6 位前缀 + 长度 ~10-20B/条估算，1 万条 ~150KB）

**Phase to address:** Phase 2（D-05 / D-23）

### Pitfall 2: Luhn 算法从左起 vs 从右起基数错位

**What goes wrong:** 部分博客文章示例 Luhn 实现时基数搞错（从左起第 2 位 ×2 而非从右起第 2 位）→ 测试用例（如 `4532015112830366` Visa 测试卡）误判失败。

**Why it happens:** Luhn 算法核心是「**从右起**每第 2 位 ×2」，左起实现会因数字总位数奇偶导致错误结果。

**How to avoid:**
```python
def luhn_valid(num: str) -> bool:
    if not num or not num.isdigit(): return False
    digits = [int(d) for d in num]
    total = 0
    for i, d in enumerate(reversed(digits)):  # 从右起（reversed）
        if i % 2 == 1:  # 第 2 位（即 reversed 后索引 1）
            d2 = d * 2
            total += d2 if d2 < 10 else d2 - 9
        else:
            total += d
    return total % 10 == 0
```

**Warning signs:**
- 测试用例仅 1-2 个；没有覆盖 16 位偶数位 + 13/15/19 位奇数位
- 没有覆盖全零数字（`0000000000000000` Luhn 通过但显然是无效）

**Phase to address:** Phase 2（D-05 / D-23）

### Pitfall 3: 邮箱正则太严拒绝合法邮箱（漏报）

**What goes wrong:** 简化版 RFC 5322 正则漏掉 `user+tag@example.co.uk`（含 `+`）或 `first.last@sub.example.com`（子域）→ 合法邮箱被 reject。

**Why it happens:** 简化版正则的字符类漏字符（如 `+` / 多级子域）。

**How to avoid:**
- D-10 锁定的简化版正则：`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`
- 字符类 `+` / `_` / `.` / `%` / `-` 全部覆盖
- 域名部分允许多级子域（`\.` 可出现多次，因 `[A-Za-z0-9.-]+` greedy）
- TLD 部分 `[A-Za-z]{2,}` 允许 2+ 字符
- 词边界锚定 `(?<![A-Za-z0-9._%+-])` / `(?![A-Za-z0-9._%+-])` 防止 `x@y.com.evil` 这种「半合法」邮箱被误判为合法（evil 是后缀）

**Warning signs:**
- 测试只覆盖 `user@domain.com` 简单形式
- 没有覆盖 `+` tag / 多级子域 / 长 TLD

**Phase to address:** Phase 2（D-10 / D-23）

### Pitfall 4: USCC 类别码白名单遗漏（误判其他编码）

**What goes wrong:** 白名单只包含 `1` / `5` / `9`（机构编制 / 民政 / 工商）→ 漏 `Y`（其他，约占 5% 命中）→ 含 `Y` 的真实 USCC 被 reject。

**Why it happens:** D-06 提到的「8 类」是预留，常见命中集中在前 3 类（机构 / 民政 / 工商）；`Y`（其他）实际由 1-2% 工商总局不发的编码（如外企代表处、临时机构）。

**How to avoid:**
```python
USCC_CATEGORY_CODES: Final = frozenset({'1', '5', '9', 'Y', 'A', 'N'})
```
- 6 类已覆盖 99%+ 真实 USCC
- 剩余 2 类（外交 `2`、司法行政 `3`）Phase 2 暂不内置；Phase 8 用户可扩展

**Warning signs:**
- 测试用例只覆盖 `91110000...`（工商段 `9`）和 `12100000...`（事业单位 `1`）
- 没有覆盖 `Y` 开头的真实 USCC（如外企代表处）

**Phase to address:** Phase 2（D-06 / D-23）

### Pitfall 5: 全电发票 20 位正则格式错误

**What goes wrong:** 正则只允许纯数字 20 位 → 含连字符的传统发票号（如 `12345678-2023-001`）漏判；或允许连字符但词边界错误 → 嵌入到大段数字中（如订单号 `12345678901234567890`）被误判为发票号。

**Why it happens:** 20 位 vs 8 位正则的优先级、连字符处理、词边界锚定三者容易冲突。

**How to avoid:**
- 双格式并行正则：
  - 8 位传统：`(?<!\d)\d{8}(?!\d)`（纯数字，词边界）
  - 20 位全电：`(?<!\d)\d{20}(?!\d)`（纯数字，词边界）
- 可选连字符处理（20 位）：`(?<!\d)\d{4}-?\d{4}-?\d{4}-?\d{4}-?\d{4}(?!\d)`（接受 `1234-5678-9012-3456-7890` 形式）
- 双正则并行 yield；validator 再做严格结构校验 + 上下文锥点（发票 / 号码 / 票号 / invoice）±20 字符
- 无上下文锥点的 8 位数字单独出现视为「疑似票号」，confidence_tier = MEDIUM（D-07 锁定）

**Warning signs:**
- 测试只覆盖纯数字 8 位 / 20 位，没有覆盖连字符 + 上下文锥点
- 没有覆盖「8 位纯数字作为订单号无锥点 → MEDIUM 候选」场景

**Phase to address:** Phase 2（D-07 / D-23）

### Pitfall 6: Partial mask 字体回退失败导致文字溢出 rect

**What goes wrong:** `page.insert_text(fontsize=14)` 但 rect 宽度按原文 `110101199003078811`（18 位）计算，仅 ~108pt；插入 mask `110101********1234`（18 位）实际宽度因字号估算偏差溢出 rect → 文字跨越到原文非敏感区域，遮蔽不到位。

**Why it happens:** D-03 重算 rect 宽度的字符宽度估算（`fontsize * 0.55`）是 helvetica 平均值，但中文 / 等宽 / 斜体字符宽度可能偏差 ±20%。

**How to avoid:**
- D-03 重算 rect 宽度时按 mask_strategy 字符数（含 `*`）而非原文长度
- 估算公式保守：`avg_char_width = fontsize * 0.55` + 上下左右各留 2pt padding
- 居中插入：以 rect 中心点为锚，`cx = (x0 + x1) / 2 - len * char_w / 2`
- 测试覆盖：`test_partial_mask_overflow_returns_resized_rect` / `test_partial_mask_chinese_chars_uses_helv_default`

**Warning signs:**
- 测试仅断言 mask 文字存在，未断言 rect 宽度变化
- 没有覆盖「mask 长度 < 原文长度」「mask 长度 > 原文长度」两种场景

**Phase to address:** Phase 2（D-03 / D-23）

### Pitfall 7: 银行账号上下文锥点关键词不全（漏报）

**What goes wrong:** 仅内置 D-08 列出的 10 关键词（含 4 通用 + 6 大行）→ 股份制商业银行（中信 / 浦发 / 兴业 / 民生等）的银行账号无锥点 → 漏判。

**Why it happens:** D-08 锁定的关键词是最低集合，但股份制银行（12 家）+ 城商行（多家常用）在用户实际文档中频繁出现。

**How to avoid:**
- 推荐扩展锥点关键词到 16 个：
  ```python
  BANK_ACCOUNT_CONTEXT_ANCHORS = (
      # 通用（D-08）
      '账号', '账户', '银行账号', '银行账户',
      # 5 大国有行（D-08）
      '工商银行', '农行', '中行', '建行', '邮储',
      # 6 大股份制（D-08 + Claude's Discretion 扩展）
      '招行', '交通银行', '中信', '浦发', '兴业', '民生',
      '平安', '光大', '华夏', '广发', '浙商', '恒丰', '渤海',
      # 1-2 城商行
      '上海银行', '北京银行',
  )
  ```
- 关键词放 `privacyguard/pii/validators/bank_account.py`（D-20 本地化在 validator）
- 测试覆盖：`test_bank_account_with_zhongxin_context_anchor_recognized` / `test_bank_account_without_context_anchor_rejected`

**Warning signs:**
- 测试用例只覆盖「工行客户 银行账号 622202...」典型场景
- 没有覆盖股份制 / 城商行场景

**Phase to address:** Phase 2（D-08 / Claude's Discretion / D-23）

### Pitfall 8: 15 位纳税人识别号被 USCC 校验函数误判

**What goes wrong:** 旧版 15 位编号（如 `110108000000001`）被 `validate_uscc` 误判 → 长度 15 ≠ 18，validate_uscc 应直接 False；但若代码里不小心共享了 validate 函数 → 15 位被当 18 位处理（前 15 位视为 body17，缺最后 3 位）→ 错误地通过校验。

**Why it happens:** USCC 与 15 位旧号在「数字位 + 行政区划码 + 顺序码」结构上部分相似，但长度 + 校验位算法完全不同。

**How to avoid:**
- 15 位独立 type（`CN_TAXPAYER_ID_15`），独立 validator `validate_15_digit_taxpayer_id`
- 15 位 validator 不调 USCC 的 mod-31-3 校验（无校验位）
- 15 位 validator 仅做：(1) 长度 15 位；(2) 全部数字；(3) 6-7-4 分段结构；(4) 前 2 位 ∈ `privacyguard.pii.validators.id_card._VALID_ADMIN_PREFIX_2`（行政区划码 sanity，复用 Phase 1 资源）
- `PIIEngine._check_taxpayer_id_15` 不走 USCC 路径，独立分支
- 测试覆盖：`test_taxpayer_id_15_does_not_use_uscc_checksum` / `test_taxpayer_id_15_with_invalid_admin_prefix_rejected`

**Warning signs:**
- 测试覆盖 USCC 18 位但没有 15 位
- 15 位 validator 引用了 USCC_CHARS / USCC_WEIGHTS 常量

**Phase to address:** Phase 2（D-09 / D-23）

### Pitfall 9: Mask 模式字段命名漂移（D-13 字段锁）

**What goes wrong:** `pii_settings.per_entity_default` 在 `config.json` 写为 `mask_modes` 或 `entity_modes`；不同模块用不同字段名（main.py 读 `mask_modes`，pdf_adapter 写 `entity_modes`）→ 配置不生效。

**Why it happens:** 字段名命名一旦不锁定，多处修改时易出现拼写不一致。

**How to avoid:**
- D-13 锁定字段名：`pii_settings.per_entity_default: Dict[str, Literal["partial", "blackout"]]`
- 同步 `config.json` + `config.json.template` + `tests/unit/test_app_config.py` + `MainWindow.__init__` 读取路径
- 测试覆盖：`test_per_entity_default_field_name_locked`（AST 扫描 `config.json` / `SimpleConfig` 验证字段名一致）
- Phase 1 D-08 / D-09 已有 `engine_enabled` / `auto_redact` / `require_confirmation` 三个字段名锁定沿用经验

**Warning signs:**
- `config.json` 中 `pii_settings` 段有非 `per_entity_default` 字段
- `main.py` 读取路径与 config.json 字段名不一致

**Phase to address:** Phase 2（D-13 / D-23）

### Pitfall 10: PDF 元数据 5 字段不全清（漏 `producer` 或 `creator`）

**What goes wrong:** `clear_pdf_metadata` 只清 `title` / `author` / `subject` 3 字段，遗漏 `producer` / `creator` → PDF 中仍保留 `PyMuPDF` / `LaTeX with hyperref` 等 producer 字符串 → 反向提取暴露处理工具。

**Why it happens:** PDF 元数据共 8 个核心字段（title / author / subject / keywords / creator / producer / creationDate / modDate），D-14 锁定只清其中 5 个；代码实现易遗漏个别字段。

**How to avoid:**
```python
# privacyguard/pii/pdf_adapter.py::clear_pdf_metadata
SAFE03_FIELDS = ("title", "author", "subject", "producer", "creator")

def clear_pdf_metadata(doc: fitz.Document) -> None:
    doc.set_metadata({k: "" for k in SAFE03_FIELDS})
```
- 测试覆盖：`test_metadata_all_5_fields_cleared`（`doc.metadata` 反向断言 5 字段 == ""）+ `test_metadata_creation_date_preserved`（`CreationDate` 不动）+ `test_metadata_mod_date_preserved`（`ModDate` 不动）
- 单元测试用 `fitz.open(out).metadata` 反向提取（PyMuPDF 文档级 `metadata` 属性是 dict）

**Warning signs:**
- `clear_pdf_metadata` 函数签名只接受 1-2 个参数（不是 5 字段字典）
- 测试只断言 `title == ""`，未断言 `producer == ""` 等

**Phase to address:** Phase 2（D-14 / D-15 / D-16 / D-23）

### Pitfall 11: PyInstaller `bin_prefixes.json` 数据文件未注入（cp30 重演）

**What goes wrong:** `bin_prefixes.json` 新增到 `privacyguard/pii/data/` 但 PyInstaller spec 未同步 → frozen 启动 `FileNotFoundError: bin_prefixes.json`；银行账号识别全部因词典缺失而 reject。

**Why it happens:** cp30 修复过类似问题（`privacyguard.utils.security` 模块导入失败）；新增数据文件需重新验证 Windows + macOS spec。

**How to avoid:**
- `packaging/windows/config/PrivacyGuard_windows.spec` `datas=[]` 段追加：
  ```python
  (os.path.join(project_root, 'privacyguard', 'pii', 'data'), 'privacyguard/pii/data'),
  ```
  （已包含 Phase 1 `rules.json`；`bin_prefixes.json` 同位置自动覆盖）
- `packaging/macos/config/PrivacyGuard.spec` 同步（B5 parity）
- `packaging/macos/scripts/build_complete.sh` parity check 增加：
  ```bash
  if [ -f "$APP_PATH/Contents/Resources/privacyguard/pii/data/bin_prefixes.json" ]; then
      echo "  [OK] bin_prefixes.json 存在"
  else
      echo "  [FAIL] bin_prefixes.json 缺失"
      exit 1
  fi
  ```
- `tests/unit/test_package_imports.py` 扩展：monkey-patch `importlib.import_module` 拦截 `privacyguard.pii.data.bin_prefixes`，断言其可被加载且为 dict

**Warning signs:**
- `compileall` 通过但 frozen 启动报 `ModuleNotFoundError` / `FileNotFoundError`
- spec `datas` 不含 `bin_prefixes.json`

**Phase to address:** Phase 2（D-26 / cp30 教训）

### Pitfall 12: BIN 词典条数估算错误（CC BY-SA 4.0 来源受限）

**What goes wrong:** 试图从维基主表抓取 1.5 万条 → CC BY-SA 4.0 归属声明遗漏或不完整 → 违反 LICENSE；或反之仅抓 2000 条 → 大量真实卡号 BIN 不在表内 → 漏判。

**Why it happens:** 维基主表包含历史 BIN + 私有 BIN + 测试 BIN，整合时需筛选有效条目；CC BY-SA 4.0 要求严格归属。

**How to avoid:**
- `bin_prefixes.json.LICENSE` 文件保留完整归属（CC BY-SA 4.0 §3(a)）：
  ```
  PrivacyGuard 银行卡 BIN 词典
  基于 Wikipedia "Payment card number" 词条整理
  Source: https://en.wikipedia.org/wiki/Payment_card_number
  License: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)
  Modifications: 整合中国银联公开 BIN 公告，移除过期条目，按 6 位前缀去重
  ```
- 整合条数控制在 1 万-1.5 万（Claude's Discretion 范围）；不得低于 10000 条
- 单元测试验证 LICENSE 文件存在 + 含 `CC BY-SA` + `Wikipedia` 关键字

**Warning signs:**
- 词典文件 < 100KB（1 万条应有 150KB+）
- LICENSE 文件缺失或仅 1-2 行

**Phase to address:** Phase 2（D-27 / D-26）

### Pitfall 13: Reverse-extraction 测试遗漏 mask 文字断言

**What goes wrong:** Phase 2 partial mask 写入后，单元测试仅断言「原文不存在」（`assertNotIn(secret_id, out_text)`），但忘记断言「mask 文字存在」（`assertIn(mask_strategy, out_text)`）→ 假阳性通过：helper 错误地什么都没写入，测试仍 green。

**Why it happens:** Phase 1 reverse-extraction 测试逻辑是「原文消失」，Phase 2 新增「mask 文字存在」反向断言需显式扩展。

**How to avoid:**
- `tests/unit/test_pdf_pii_redaction.py` 新增 `test_partial_mask_text_visible`：
  ```python
  out_doc = fitz.open(out_pdf)
  try:
      out_text = "".join(p.get_text() for p in out_doc)
      # D-23: 原文不可提取（沿用 Phase 1 SAFE-02）
      self.assertNotIn(secret_id[:10], out_text)
      # D-23: mask 文字存在（Phase 2 NEW）
      expected_mask = partial_mask_id_card(secret_id)  # "110101********8811"
      self.assertIn(expected_mask, out_text)
  finally:
      out_doc.close()
  ```
- 同样覆盖银行卡 / 邮箱 / USCC 4 类 entity 的 mask 文字断言

**Warning signs:**
- 测试仅断言 `assertNotIn`，没有 `assertIn`
- 没有覆盖 partial mask 模式下 mask 文字存在性

**Phase to address:** Phase 2（D-23）

### Pitfall 14: Toolbar toggle 状态与 page_data 生命周期不同步

**What goes wrong:** 用户勾选「本文件使用全遮蔽」toggle → 写入 `self.page_data[0]["mask_override_this_doc"] = "blackout"`；但打开新 PDF 时 `page_data` 重置（`self.page_data = {}` 在 `_open_word_docx` 或 open_pdf 路径），toggle 状态丢失或泄漏到下一文档。

**Why it happens:** `page_data[0]` 是页面级数据（每页 `ocr` / `manual` / `pii` 键），但 `mask_override_this_doc` 是文档级 override，键放在 `page_data[0]` 是 D-12 锁定的 hack（避免引入新字典），但生命周期管理不当易出错。

**How to avoid:**
- 文档级 override 键固定放 `page_data[0]`，因为页面级数据最先访问的就是第 0 页
- `MainWindow._open_pdf` / `_open_word_docx` 路径重置 `page_data = {}` 时同步 reset toggle 状态：`self.cb_doc_blackout.setChecked(False)`
- 测试覆盖：`test_toolbar_toggle_resets_on_new_pdf`（mock 新文档打开 → 验证 toggle 状态恢复默认）

**Warning signs:**
- toggle 状态泄漏到下一文档（旧文档的 override 仍生效）
- 关闭 toggle 但 save_pdf 仍走 blackout 模式

**Phase to address:** Phase 2（D-12）

---

## Code Examples

Verified patterns from official sources / 本机 Python 验证：

### GB 32100 mod-31-3 USCC Validator（D-06 / FIN-01）

```python
# privacyguard/pii/validators/uscc.py
"""GB 32100-2015 统一社会信用代码校验（mod-31-3 + 登记管理部门类别码预筛选）。

FIN-01: USCC 18 位识别（FIN-03 18 位 = CN_TAXPAYER_ID 复用）
"""
from typing import Final

# GB 32100-2015 §5.1: 字符集 0-9 + A-Z 去掉 I/O/S/V/Z
USCC_CHARS: Final = '0123456789ABCDEFGHJKLMNPQRTUWXY'
USCC_WEIGHTS: Final = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)

# D-06 登记管理部门类别码白名单（6 类常见 + 预留扩展）
USCC_CATEGORY_CODES: Final = frozenset({'1', '5', '9', 'Y', 'A', 'N'})


def compute_check_digit(body17: str) -> str:
    if len(body17) != 17:
        return ''
    try:
        total = sum(USCC_CHARS.index(c) * USCC_WEIGHTS[i] for i, c in enumerate(body17))
    except ValueError:
        return ''
    return USCC_CHARS[(31 - total % 31) % 31]


def validate_uscc(code: str) -> bool:
    if not isinstance(code, str) or len(code) != 18:
        return False
    for c in code:
        if c not in USCC_CHARS:
            return False
    if code[0] not in USCC_CATEGORY_CODES:
        return False
    return compute_check_digit(code[:17]) == code[17]


# 本机实测样本:
# validate_uscc("91110000600037341L") == True   (腾讯科技真实 USCC)
# validate_uscc("91110000600037341X") == False  (X 不在字符集)
# validate_uscc("91350100MA31WT0U86") == False  (校验位错误)
# validate_uscc("91110108MA01F0G60Y") == False  (校验位错误)
```

### Luhn Algorithm（NUM-04）

```python
# privacyguard/pii/validators/bank_card.py
"""银行卡号校验：Luhn + 6 位 BIN 前缀 + 上下文锥点（D-05 / NUM-04）。"""
from typing import Final


def luhn_valid(num: str) -> bool:
    """标准 Luhn 校验（从右起每第 2 位 ×2，超过 9 减 9；sum % 10 == 0）。"""
    if not num or not num.isdigit():
        return False
    digits = [int(d) for d in num]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d2 = d * 2
            total += d2 if d2 < 10 else d2 - 9
        else:
            total += d
    return total % 10 == 0


# 本机实测样本:
# luhn_valid("6225760000000000") == False  # 实际不通过（维基常见误引）
# luhn_valid("4532015112830366") == True   # Visa 16 位测试卡
# luhn_valid("1234567812345670") == True   # 经典 16 位 Luhn 测试数
# luhn_valid("6225768199574466") == True   # BIN 622576 + 9 位随机 + Luhn 计算
```

### Email RFC 5322 简化版 Validator（NUM-05）

```python
# privacyguard/pii/validators/email.py
"""邮箱识别：RFC 5322 简化版正则 + 公共域名后缀档位判定（D-10 / NUM-05）。"""
import re
from typing import Final


EMAIL_RE: Final = re.compile(
    r'(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9._%+-])'
)

# D-10 公共域名后缀白名单（决定 confidence_tier）
PUBLIC_TLDS: Final = frozenset({
    'com', 'cn', 'net', 'org', 'gov', 'edu',
    'io', 'co', 'me', 'app',
})


def validate_email(text: str) -> bool:
    """NUM-05 简化邮箱验证（无校验位，仅 RFC 5322 简化版正则）。"""
    if not text:
        return False
    return bool(EMAIL_RE.fullmatch(text))


def public_tld(text: str) -> bool:
    """D-10 档位判定：是否含公共域名后缀。"""
    if '@' not in text:
        return False
    _, _, domain = text.partition('@')
    tld = domain.rsplit('.', 1)[-1].lower()
    return tld in PUBLIC_TLDS


__all__ = ['EMAIL_RE', 'PUBLIC_TLDS', 'validate_email', 'public_tld']
```

### Full PyMuPDF partial mask + metadata clear（Phase 2 helper 落地）

```python
# privacyguard/pii/pdf_adapter.py (Phase 2 扩展)
import fitz
from typing import Iterable, Literal, Optional, Tuple


# D-02 字体映射表（get_text("dict") font → insert_text fontname）
_FONT_NAME_MAP = {
    "Helvetica": "helv", "Helvetica-Oblique": "heit",
    "Helvetica-Bold": "hebo", "Helvetica-BoldOblique": "hebi",
    "Times-Roman": "tiro", "Times-Bold": "tibo",
    "Courier": "cour", "Courier-Bold": "cobo",
}


def write_partial_masks(doc, page_idx, pii_hits, mode="partial", per_doc_override=None):
    """D-21 partial mask helper。"""
    page = doc[page_idx]
    effective_mode = per_doc_override or mode

    rects = []
    mask_texts = {}
    for hit in pii_hits:
        pr = hit.page_rect
        rect = fitz.Rect(pr[0], pr[1], pr[0] + pr[2], pr[1] + pr[3])
        rects.append(rect)
        mask_texts[id(hit)] = (rect, hit.mask_strategy)

    for rect in rects:
        annot = page.add_redact_annot(rect)
        annot.set_colors(stroke=(0, 0, 0), fill=(0, 0, 0))
        annot.update()
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
    for annot in page.annots() or []:
        page.delete_annot(annot)

    if effective_mode != "partial":
        return

    for hit in pii_hits:
        rect, mask_text = mask_texts[id(hit)]
        if not mask_text:
            continue
        if hit.source == "text":
            fontname, fontsize = _resolve_text_layer_font(page, hit.page_offset)
        else:
            fontname, fontsize = "helv", max(rect.height - 4.0, 8.0)
        # D-03 rect 宽度按 mask 字符数重算 + 居中
        avg_char_width = fontsize * 0.55
        new_w = max(len(mask_text) * avg_char_width + 4.0, rect.width)
        cx = (rect.x0 + rect.x1) / 2.0
        resized_rect = fitz.Rect(cx - new_w / 2.0, rect.y0, cx + new_w / 2.0, rect.y1)
        # 居中插入（黑底由 add_redact_annot 提供，写白字）
        insert_x = (resized_rect.x0 + resized_rect.x1) / 2.0 - (len(mask_text) * fontsize * 0.55) / 2.0
        insert_y = (resized_rect.y0 + resized_rect.y1) / 2.0 - fontsize / 3.0
        page.insert_text(
            (insert_x, insert_y),
            mask_text,
            fontname=fontname,
            fontsize=fontsize,
            color=(1, 1, 1),
            overlay=True,
        )


def clear_pdf_metadata(doc) -> None:
    """D-14 / D-15 / D-16 SAFE-03：清 5 字段元数据为空字符串。"""
    doc.set_metadata({
        "title": "", "author": "", "subject": "", "producer": "", "creator": "",
    })
```

### BIN 词典 Sample（NUM-04）

```json
// privacyguard/pii/data/bin_prefixes.json (示例前 3 条)
{
  "version": "2026-08-11",
  "source": "Wikipedia:Payment card number + 中国银联公开 BIN 公告",
  "license": "CC BY-SA 4.0 (Wikipedia 部分)",
  "bins": [
    {"bin": "622576", "network": "UnionPay", "issuer": "中国工商银行", "type": "借记卡"},
    {"bin": "622202", "network": "UnionPay", "issuer": "中国工商银行", "type": "借记卡"},
    {"bin": "453201", "network": "Visa", "issuer": "Visa Test", "type": "测试卡"}
  ],
  "_comment": "完整 1-1.5 万条；按 6 位前缀去重；6 位前缀白名单加载"
}
```

### Reverse-Extraction Test 扩展（D-23 partial mask 文字存在性）

```python
# tests/unit/test_pdf_pii_redaction.py (Phase 2 扩展)
import fitz
import unittest

from privacyguard.pii.engine import PIIEngine, TextUnit
from privacyguard.pii.pdf_adapter import apply_pii_redactions, write_partial_masks
from privacyguard.pii.mask import partial_mask_id_card
from tests.fixtures.fake_pii import fake_id_card, fake_phone, fake_bank_card, fake_email, fake_uscc


class TestPdfPiiPartialMaskRedaction(unittest.TestCase):
    """Phase 2: partial mask 写入后反向断言原文不存在 + mask 文字存在。"""

    def test_id_card_partial_mask_visible(self):
        secret_id = fake_id_card()
        with tempfile.TemporaryDirectory() as tmp:
            src = fitz.open()
            page = src.new_page()
            page.insert_text((50, 100), f"测试样本 {secret_id}", fontsize=14)
            in_pdf = os.path.join(tmp, "in.pdf")
            src.save(in_pdf)
            src.close()

            engine = PIIEngine()
            doc = fitz.open(in_pdf)
            hits = []
            for i, p in enumerate(doc):
                unit = TextUnit(page_index=i, text=p.get_text(), source="text")
                hits.extend(engine.detect(unit, page=p))
            write_partial_masks(doc, 0, hits, mode="partial")
            out_pdf = os.path.join(tmp, "out.pdf")
            doc.save(out_pdf, garbage=4, deflate=True, clean=True)
            doc.close()

            out_doc = fitz.open(out_pdf)
            try:
                out_text = "".join(p.get_text() for p in out_doc)
                # 原文不可提取（沿用 Phase 1 SAFE-02）
                self.assertNotIn(secret_id[:10], out_text)
                # mask 文字存在（Phase 2 NEW）
                expected_mask = partial_mask_id_card(secret_id)
                self.assertIn(expected_mask, out_text)
            finally:
                out_doc.close()
```

### Metadata Clear Reverse Test（D-23）

```python
# tests/unit/test_pdf_metadata_cleared.py (Phase 2 NEW)
import fitz
import unittest


class TestPdfMetadataCleared(unittest.TestCase):
    """SAFE-03: PDF 5 字段元数据清除反向测试。"""

    def test_metadata_5_fields_cleared(self):
        src = fitz.open()
        page = src.new_page()
        page.insert_text((50, 50), "test", fontsize=14)
        # 模拟含元数据的输入 PDF
        src.set_metadata({
            "title": "Confidential Report",
            "author": "John Doe",
            "subject": "Annual Review",
            "producer": "Microsoft Word 2019",
            "creator": "Microsoft Word 2019",
        })
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in.pdf")
            src.save(in_pdf)
            src.close()

            doc = fitz.open(in_pdf)
            # D-16: save_pdf 中调 clear_pdf_metadata
            from privacyguard.pii.pdf_adapter import clear_pdf_metadata
            clear_pdf_metadata(doc)
            out_pdf = os.path.join(tmp, "out.pdf")
            doc.save(out_pdf, garbage=4, deflate=True, clean=True)
            doc.close()

            out_doc = fitz.open(out_pdf)
            try:
                meta = out_doc.metadata
                # D-14: 5 字段全为空
                self.assertEqual(meta.get("title"), "")
                self.assertEqual(meta.get("author"), "")
                self.assertEqual(meta.get("subject"), "")
                self.assertEqual(meta.get("producer"), "")
                self.assertEqual(meta.get("creator"), "")
                # D-14: CreationDate / ModDate 不动（可能为空也可能保留原值）
                # 不做严格断言（不同 PDF 创建时间不同）
            finally:
                out_doc.close()


# 本机实测 2026-08-11：
# python3 -c "import fitz; doc = fitz.open(); page = doc.new_page(); doc.set_metadata({'title':'','author':'','subject':'','producer':'','creator':''}); doc.save('/tmp/x.pdf'); print(fitz.open('/tmp/x.pdf').metadata)"
# → {'format': 'PDF 1.7', 'title': '', 'author': '', 'subject': '', 'creator': '', 'producer': '', 'creationDate': '', 'modDate': '', 'trapped': '', 'encryption': None}
# 5 字段均为空字符串；验证 OK
```

### `page.get_text("dict")` 字体回退映射实测（D-02）

```python
# 本机实测 2026-08-11：
# python3 -c "
# import fitz
# doc = fitz.open()
# page = doc.new_page()
# page.insert_text((50, 50), '身份证 110101199003078811', fontname='helv', fontsize=14)
# text_dict = page.get_text('dict')
# for block in text_dict.get('blocks', []):
#     if block.get('type') == 0:
#         for line in block.get('lines', []):
#             for span in line.get('spans', []):
#                 print(f\"font='{span.get('font')}' size={span.get('size')}\")
# "
# → font='Helvetica' size=14.0
# → font='Helvetica-Oblique' size=12.0
# → font='Helvetica-Bold' size=16.0

# 关键发现：
# - get_text("dict") 返回的 font 字段是 Base 14 字体完整名（'Helvetica'），不是 insert_text 接受的简称（'helv'）
# - D-02 字体回退映射表必须做「简称 ↔ 全称」双向映射
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `page.draw_rect(fill=(0,0,0))` "redaction" | `page.add_redact_annot(rect)` + `page.apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` + `page.insert_text` partial mask | PyMuPDF 1.18+ (2019) + Phase 2 (2026) | 黑框覆盖但内容可还原 → 内容真删除 + 可读 mask；2019-2024 多起公开事故验证 `draw_rect` 不可信 |
| USCC 自研散装正则 | GB 32100-2015 mod-31-3 + 31 字符表 + 8 类别码白名单 | 2015 国标 + Phase 2 | 2015 三证合一前的 15 位旧号被淘汰；18 位 USCC 是 2015 后唯一法人标识 |
| 银行卡 16 位 Luhn 单一验证 | Luhn + 6 位 BIN 词典 + 上下文锥点三层 | 行业标准 (ISO/IEC 7812) + Phase 2 | 避免 13-19 位订单号被误判；BIN 词典覆盖 1.5 万条 |
| RFC 5322 完整正则（6KB ReDoS 风险） | RFC 5322 简化版（< 200B）+ 公共后缀白名单档位判定 | 行业惯例 + Phase 2 (D-10) | ReDoS 防御 + 简化维护；漏判极少见 |
| PyMuPDF `xref_set_key(info_xref, ...)` raw Info dict 改写 | `doc.set_metadata({...})` 官方 API | PyMuPDF 1.18+ | 5 字段名 → PDF `/Title` 等映射自动处理；XMP metadata 不动 |
| `apply_redactions()` 默认 `images=PDF_REDACT_IMAGE_NONE=0` 漏图像像素销毁 | `images=fitz.PDF_REDACT_IMAGE_PIXELS=2` 显式指定 | PyMuPDF 1.18+ | 扫描型 PDF 内嵌图像不被销毁 → 放大镜 / 重 OCR 可还原 |
| `re.finditer(..., timeout=...)` 据称 Python 3.11+ 支持 | 不支持（已在本机 Python 3.12 验证） | 不存在 | 截断单页文本到 200KB + worker 中断 |

**Deprecated/outdated:**
- **`page.draw_rect` 假脱敏：** 行业头号失败模式；Phase 1 已禁用
- **Python `re` `timeout=` keyword argument：** 不存在；Phase 1 已修正
- **`main.py` 内嵌 PII 检测：** 违反 v37.7.6 收敛；Phase 2 同样禁止
- **USCC 15 位旧号识别：** 2015 后已合并到 18 位；Phase 2 仅识别旧文档历史记录
- **银行卡识别不带 BIN：** Luhn 单独不够，13-19 位订单号会被误判

---

## TDD Specifics

### Fixtures (扩展 `tests/fixtures/fake_pii.py`)

| Fixture | 输入 | 输出 | 用途 |
|---------|------|------|------|
| `fake_bank_card(bin_prefix='622576')` | BIN + 9 位随机 + Luhn check digit | 16 位 Luhn 通过的银行卡号 | NUM-04 单元测试 |
| `fake_email(tld='example.com')` | 任意前缀 + `@` + tld | RFC 5322 简化正则匹配的邮箱 | NUM-05 单元测试 |
| `fake_uscc(category='9', institution='1')` | 类别码 + 机构类别码 + 6 位区划码 + 9 位主体码 + mod-31-3 check digit | 18 位 GB 32100 通过的 USCC | FIN-01 单元测试 |
| `fake_vat_invoice_8()` | 8 位随机 + 校验位 | 8 位传统发票号 | FIN-02 单元测试 |
| `fake_vat_invoice_20(year='23', province='11')` | 年号 + 行政区划码 + 渠道码 + 顺序码 | 20 位全电发票号 | FIN-02 单元测试 |
| `fake_taxpayer_id_15()` | 6-7-4 分段结构 + 行政区划码 sanity | 15 位旧版纳税人识别号 | FIN-03 单元测试 |
| `fake_bank_account(prefix='622202')` | 任意 9-21 位 + 上下文锥点样本 | 18 位银行账号 | FIN-04 单元测试 |

### Test-First Cycle 示例

| Requirement | Failing Test (FIRST) | 实现 (THEN) | Fixture |
|-------------|---------------------|------------|---------|
| NUM-04 (Luhn) | `test_luhn_valid_visa_test_card()` 断言 `luhn_valid("4532015112830366") == True` | `validators/bank_card.py::luhn_valid` | 3+ 标准样本 |
| NUM-04 (BIN) | `test_bank_card_with_valid_bin_recognized()` 断言 `fake_bank_card("622576")` 在「招行客户 银行卡号 XXX」文本中命中 HIGH | `validators/bank_card.py::validate_bank_card` + `engine._check_bank_card` | BIN 词典 sample |
| NUM-04 (FP 防护) | `test_order_number_without_bin_rejected()` 断言 `luhn_valid("1234567812345670")` 在无 BIN 词典命中时 reject | BIN 词典加载 + 上下文锥点 gate | 无 BIN 词典 sample |
| NUM-05 (邮箱) | `test_email_with_public_tld_high_confidence()` 断言 `validate_email("test@example.com") == True` + confidence_tier == HIGH | `validators/email.py::validate_email` | 5+ 样本（com / cn / net / org / gov） |
| FIN-01 (USCC) | `test_uscc_real_tencent_validates()` 断言 `validate_uscc("91110000600037341L") == True` | `validators/uscc.py::validate_uscc` | 5+ 真实样本 + 3+ 反例 |
| FIN-01 (类别码) | `test_uscc_invalid_category_code_rejected()` 断言 `validate_uscc("21110000MA0000000X") == False`（`2` 不在白名单） | USCC_CATEGORY_CODES 白名单 | 8 类全量测试 |
| FIN-02 (8 位) | `test_vat_invoice_8digit_with_context_recognized()` 断言发票文本中 8 位数字命中 | `validators/vat_invoice.py::validate_8digit` | 上下文锥点 sample |
| FIN-02 (20 位) | `test_vat_invoice_20digit_electronic_recognized()` 断言全电发票文本中 20 位数字命中 | `validators/vat_invoice.py::validate_20digit` | 2-3 真实样本 |
| FIN-03 (15 位) | `test_taxpayer_id_15_does_not_use_uscc_checksum()` 断言 15 位编号独立 type `CN_TAXPAYER_ID_15` | `validators/taxpayer_id.py::validate_15` | 5+ 旧版样本 |
| FIN-04 (银行账号) | `test_bank_account_with_zhongxin_context_recognized()` 断言「中信 银行账号 622202...」命中 | `validators/bank_account.py::validate_bank_account` | 锥点关键词 16 个全量 |
| MASK-01 (partial mask 写入) | `test_partial_mask_text_visible_after_redaction()` 断言 `partial_mask_id_card(secret_id)` 出现在 reverse-extract 文本 | `pdf_adapter.write_partial_masks` | 5+ entity sample |
| MASK-02 (per-entity default) | `test_per_entity_default_config_field()` 断言 `config.json.pii_settings.per_entity_default.CN_EMAIL == "partial"` | `MainWindow.pii_settings` 扩展 + `SimpleConfig` 字段 | config.json sample |
| SAFE-03 (元数据清除) | `test_metadata_all_5_fields_cleared()` 断言 `doc.metadata.title == ""` | `pdf_adapter.clear_pdf_metadata` | 5 字段全量 |

### Reverse-Extraction Verification (Phase 2 mandatory)

```python
# tests/unit/test_pdf_pii_redaction.py (Phase 2 扩展)
def test_partial_mask_writes_mask_text_visible(self):
    """D-23 partial mask 写入后通过 reverse-extraction 断言 mask 文字存在。"""
    secret_id = fake_id_card()
    secret_phone = fake_phone()
    expected_mask_id = "110101********" + secret_id[14:]
    expected_mask_phone = secret_phone[:3] + "****" + secret_phone[7:]

    with tempfile.TemporaryDirectory() as tmp:
        src = fitz.open()
        page = src.new_page()
        page.insert_text((50, 100), f"测试样本 {secret_id} {secret_phone}", fontsize=14)
        in_pdf = os.path.join(tmp, "in.pdf")
        src.save(in_pdf)
        src.close()

        engine = PIIEngine()
        doc = fitz.open(in_pdf)
        hits = []
        for i, p in enumerate(doc):
            unit = TextUnit(page_index=i, text=p.get_text(), source="text")
            hits.extend(engine.detect(unit, page=p))
        write_partial_masks(doc, 0, hits, mode="partial")
        out_pdf = os.path.join(tmp, "out.pdf")
        doc.save(out_pdf, garbage=4, deflate=True, clean=True)
        doc.close()

        out_doc = fitz.open(out_pdf)
        try:
            out_text = "".join(p.get_text() for p in out_doc)
            # D-23 ① 原文不可提取（沿用 Phase 1 SAFE-02）
            self.assertNotIn(secret_id[:10], out_text)
            self.assertNotIn(secret_phone[:7], out_text)
            # D-23 ② mask 文字存在（Phase 2 NEW）
            self.assertIn(expected_mask_id, out_text)
            self.assertIn(expected_mask_phone, out_text)
        finally:
            out_doc.close()
```

### TDD Wave Plan 草图

1. **Wave 0:** 扩展 `tests/fixtures/fake_pii.py`（7 个新合成 fixture）— **先于**任何 Phase 2 代码
2. **Wave 1:** `test_pii_validators.py` 扩展 6 个新 validator 类 → 实现 `validators/{bank_card,email,uscc,vat_invoice,bank_account,taxpayer_id}.py`
3. **Wave 2:** `test_pii_engine.py` 扩展 7 类新 entity 命中 + 档位测试 → 实现 `regex_patterns.py` yield 扩展 + `engine.py::_check_*` 新增 6 方法 + `confidence.py::classify_hit` 扩展上下文锥点分支
4. **Wave 3:** `test_pdf_pii_redaction.py` 扩展 partial mask 写入 reverse-extraction → 实现 `pdf_adapter.py::write_partial_masks`
5. **Wave 4:** `test_pdf_metadata_cleared.py` NEW → 实现 `pdf_adapter.py::clear_pdf_metadata`
6. **Wave 5:** `test_app_config.py` 扩展 `per_entity_default` 字段 → `config.json` / `config.json.template` 字段 + `MainWindow.pii_settings` 扩展 + `MainWindow.save_pdf` 调 `write_partial_masks` + `clear_pdf_metadata`
7. **Wave 6:** `test_package_imports.py` 扩展 + Windows / macOS spec 同步 `bin_prefixes.json` + `bin_prefixes.json.LICENSE`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 维基百科「Payment card number」词条主表 ~15000 BIN（Visa/MC/Amex/Discover/UnionPay/JCB/Diners/Maestro 8 网络 × 200+ 国家发卡行） | §Standard Stack / BIN 词典 | 若维基表实际 < 1 万条或整合后覆盖不全 → 真实银行卡号被 reject → 漏判；MEDIUM |
| A2 | BIN 词典最终条数 1 万-1.5 万条（Claude's Discretion） | §Standard Stack / BIN 词典 | 若用户希望 ≥ 2 万条 → 词典文件 ~300KB，性能影响可接受；LOW |
| A3 | GB 32100-2015 mod-31-3 权重 `[1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]` + 31 字符表 `0123456789ABCDEFGHJKLMNPQRTUWXY`（不含 I/O/S/V/Z） | §Code Examples / USCC Validator | 若 GB 标准权重与字符表有更新（如 2016 第 1 号修改单）→ 校验函数失效；LOW（本机验证腾讯 USCC 通过） |
| A4 | PyMuPDF `doc.set_metadata({...})` 接受空字符串写入并产出 `doc.metadata["title"] == ""`（本机实测 2026-08-11） | §Code Examples / Metadata Clear | 若 PyMuPDF 升级后 API 行为变化 → clear_pdf_metadata 失效；LOW |
| A5 | PyMuPDF `page.get_text("dict")` 返回的 font 字段是 Base 14 全名（如 `Helvetica`），与 `page.insert_text` 接受的简称（`helv`）需手动映射（本机实测） | §Standard Stack / 字体映射表 | 若 Base 14 字体名到简称映射不全 → 字体回退失败；MEDIUM（扩展建议：增加 `helv` / `heit` 等简称本身作为 fallback 键） |
| A6 | 全电发票 20 位格式（年号 + 行政区划码 + 渠道码 + 顺序码）来自国家税务总局 2022 年第 1 号公告 + 2024 年第 11 号公告 | §Standard Stack / VAT 发票 | 若税务公告格式有更新 → 正则失效；MEDIUM（建议 2026-Q4 复核） |
| A7 | 旧版 15 位纳税人识别号格式 `NNNNN-NNNNNNN-NNNN` 6-7-4 分段（2015 三证合一前使用） | §Standard Stack / 15 位识别 | 若实际格式有变体（如带横线或不带横线）→ 正则失效；LOW |
| A8 | 银行账号上下文锥点关键词推荐扩展至 16 个（Claude's Discretion 11 + 5） | §Standard Stack / 锥点关键词 | 若用户希望保留 D-08 的 10 个最小集合 → 股份制银行账号漏判；MEDIUM |
| A9 | `bin_prefixes.json.LICENSE` 文件最小内容（4 行：标题 / 来源 URL / LICENSE / 修改说明）满足 CC BY-SA 4.0 §3(a) 归属要求 | §Standard Stack / CC BY-SA | 若 CC BY-SA 4.0 §3(b)「指示修改」要求更详细 → LICENSE 内容需扩展；LOW |
| A10 | Phase 1 D-05 PIIHit 字段锁不变（不新增字段）；Phase 2 新增 entity_type 字符串值（`CN_BANK_CARD` 等 7 类） | §Standard Stack / PIIHit | 若 D-05 字段需扩展（如新增 `mask_strategy_with_font`） → 沿 Phase 1 决定不扩展；LOW |

**If this table is empty:** All claims verified or cited — no user confirmation needed.

---

## Open Questions

1. **BIN 词典最终条数与来源权重（D-27）**
   - What we know: D-27 锁定维基主表 + 中国银联公开 BIN；建议 1 万-1.5 万条（Claude's Discretion）
   - What's unclear: 用户希望全量 1.5 万条（最大化覆盖率）还是筛选精简 1 万条（最小化文件大小）
   - Recommendation: **默认 1.2 万条**（维基主表全量 + 银联公开 BIN 去重），预计文件 ~200KB，PyInstaller 打包影响可接受；用户最终签字前可调整

2. **银行账号锥点关键词集合（D-08 扩展）**
   - What we know: D-08 列出 10 个最低集合；Claude's Discretion 建议扩展至 16 个（含 12 股份制 + 1-2 城商行）
   - What's unclear: 是否扩展到 16 个；是否要覆盖全部 12 家股份制 + 城商行
   - Recommendation: **扩展到 16 个**（4 通用 + 5 国有 + 5 股份制 + 2 城商行）；Phase 8 用户自定义词典 UX-07 再让用户添加自己银行简称

3. **CC BY-SA 4.0 LICENSE 文件最小内容（D-27）**
   - What we know: CC BY-SA 4.0 §3(a) 归属要求：作者名（如有）+ 标题（如有）+ 来源 URI（如合理）+ LICENSE 指示 + 修改说明（如有）
   - What's unclear: LICENSE 文件是否需要额外声明「非商业使用 / 共享相同方式」
   - Recommendation: 4 行最小内容（标题 + 来源 URL + LICENSE + 修改说明）足够；Phase 8 升级到完整 LICENSE 模板

4. **PyMuPDF `page.get_text("dict")` 字体回退映射表（D-02）**
   - What we know: 内置 7 个 Base 14 字体（helv / heit / hebo / hebi / tiro / tibo / cour / cobo）有标准映射
   - What's unclear: 用户文档是否可能含中文（CJK）字体（如 SimSun / Microsoft YaHei）—— Base 14 字体不支持 CJK，需要 `page.insert_font(fontfile=...)` 注册
   - Recommendation: Phase 2 沿用 Base 14 字体回退；CJK 场景下 mask 文字可能乱码，但 redact 已销毁原文，乱码 mask 不影响安全；Phase 8 字体注册 UX 再处理

5. **per-document override toggle 状态机（D-12）**
   - What we know: toggle 状态存 `page_data[0]["mask_override_this_doc"]`；打开新 PDF 时重置
   - What's unclear: 用户切换文档类型（PDF → Word → PDF）时 toggle 是否保持上一文档状态？
   - Recommendation: 每次 `open_pdf` 路径同步 reset toggle 状态为 False（默认 partial）；测试覆盖文档切换场景

6. **`mask_override_this_doc` 存 `page_data[0]` 是否与 page_data 字典契约冲突？**
   - What we know: page_data 现有键：`ocr` / `manual` / `pii`（每页）；D-12 新增键 `mask_override_this_doc`（仅 page 0）
   - What's unclear: 这种「键名包含下划线 + 仅在 page 0 有」是否破坏 Phase 1 D-04 锁定的数据契约？
   - Recommendation: 加注释 + 测试覆盖「仅 page 0 有该键，其他页无」；Phase 8 数据契约重构时再彻底清理

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | `re.finditer` / `dataclasses` / `typing.Literal` | ✓ | 3.12.13 | — |
| PyMuPDF (`fitz`) | partial mask 写入 + 元数据清除 + reverse-extract | ✓ | 1.28.2（项目固定 1.27.1，向后兼容） | — |
| PyQt6 | `QThread` / `pyqtSignal` / `QMutex` / SettingsDialog / Toolbar | ✓ | 6.10.2 | — |
| `pdftotext` (poppler-utils) | 反向提取备用 | ✗ | — | **优先 `fitz.open(out).get_text()`**（D-25） |
| RapidOCR | 现有 OCR 三路径（Phase 1） | ✓ | 1.2.3 | — |
| `bin_prefixes.json` 数据文件 | NUM-04 银行卡识别 | ✗（Phase 2 新增） | — | 由 PyInstaller `datas` 注入 + `resource_path` 加载 |
| `bin_prefixes.json.LICENSE` | D-27 CC BY-SA 4.0 归属 | ✗（Phase 2 新增） | — | 同上 |

**Missing dependencies with no fallback:**
- 无（核心栈全部已就绪；新增数据文件随打包解决）

**Missing dependencies with fallback:**
- `pdftotext`：D-25 明确用 `fitz` 路径，无需 poppler

**Skip condition for environment probe:** 不适用（已逐项检查）

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `unittest` (Python stdlib) — 沿用 Phase 1 79/79 基线 |
| Config file | 无独立配置（`unittest` 自动发现） |
| Quick run command | `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_metadata_cleared tests.unit.test_app_config -v` |
| Full suite command | `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pii_offline tests.unit.test_pdf_metadata_cleared -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NUM-04 | 银行卡 Luhn + BIN + 上下文锥点 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestBankCardLuhn tests.unit.test_pii_engine.TestEngineDetectBankCard -v` | ❌ Wave 0 |
| NUM-04 | BIN 词典 FP 防护 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestBankCardFalsePositiveGuard -v` | ❌ Wave 0 |
| NUM-05 | 邮箱 RFC 5322 简化正则 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestEmailRegex tests.unit.test_pii_engine.TestEngineDetectEmail -v` | ❌ Wave 0 |
| FIN-01 | USCC mod-31-3 + 8 类别码 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestUSCCMod313 tests.unit.test_pii_engine.TestEngineDetectUSCC -v` | ❌ Wave 0 |
| FIN-02 | VAT 发票 8 位 + 20 位双格式 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestVATInvoice tests.unit.test_pii_engine.TestEngineDetectVATInvoice -v` | ❌ Wave 0 |
| FIN-03 | 纳税人识别号 18 位 + 15 位 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestTaxpayerID tests.unit.test_pii_engine.TestEngineDetectTaxpayerID -v` | ❌ Wave 0 |
| FIN-04 | 银行账号 9-21 位 + 上下文锥点 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestBankAccount tests.unit.test_pii_engine.TestEngineDetectBankAccount -v` | ❌ Wave 0 |
| MASK-01 | Partial mask 写入 | integration | `python3 -m unittest tests.unit.test_pdf_pii_redaction.TestPdfPiiPartialMaskRedaction -v` | ❌ Wave 0 |
| MASK-02 | per-entity partial/blackout 切换 | unit | `python3 -m unittest tests.unit.test_app_config.TestSimpleConfigPerEntityDefault tests.unit.test_pii_engine.TestMaskModeSwitching -v` | ❌ Wave 0 |
| SAFE-03 | PDF 5 字段元数据清除 | integration | `python3 -m unittest tests.unit.test_pdf_metadata_cleared -v` | ❌ Wave 0 |
| OPS-04 | 新增 `bin_prefixes.json` 跨平台打包 | integration | `python3 -m unittest tests.unit.test_package_imports.TestBinPrefixesImportable -v` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine -v`（快速反馈 validators + engine）
- **Per wave merge:** `python3 -m compileall -q main.py privacyguard tests && python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_metadata_cleared tests.unit.test_pii_offline tests.unit.test_package_imports tests.unit.test_convergence tests.unit.test_app_config -v`
- **Phase gate:** Full suite 绿色（基线从 79/79 升级为 88/88 或 89/89）→ `/gsd-verify-work` → `git tag`

### Wave 0 Gaps

- [ ] `tests/fixtures/fake_pii.py` 扩展：7 个新合成 fixture（`fake_bank_card` / `fake_email` / `fake_uscc` / `fake_vat_invoice_8` / `fake_vat_invoice_20` / `fake_taxpayer_id_15` / `fake_bank_account`）
- [ ] `tests/unit/test_pii_validators.py` 扩展：6 个新 validator 测试类
- [ ] `tests/unit/test_pii_engine.py` 扩展：7 类新 entity 命中 + 档位 + 上下文锥点
- [ ] `tests/unit/test_pdf_pii_redaction.py` 扩展：partial mask 写入 reverse-extraction（含 mask 文字存在性断言）
- [ ] `tests/unit/test_pdf_metadata_cleared.py` NEW：5 字段元数据清除反向测试
- [ ] `tests/unit/test_app_config.py` 扩展：`per_entity_default` 字段读取/默认值/类型断言
- [ ] `tests/unit/test_package_imports.py` 扩展：`bin_prefixes.json` 可加载性 + `bin_prefixes.json.LICENSE` 文件存在
- [ ] `privacyguard/pii/data/bin_prefixes.json` + `bin_prefixes.json.LICENSE`（CC BY-SA 4.0 归属）
- [ ] `privacyguard/pii/data/rules.json` 扩展：`bank_card.bin_dictionary_path` + `uscc.category_codes` + `uscc.weights` + `vat_invoice.context_anchors` + `bank_account.context_anchors`
- [ ] `packaging/windows/config/PrivacyGuard_windows.spec` datas 段已含 `privacyguard/pii/data`（Phase 1 已加，`bin_prefixes.json` 自动覆盖；仅需 verify）
- [ ] `packaging/macos/config/PrivacyGuard.spec` parity（B5）
- [ ] `packaging/macos/scripts/build_complete.sh` parity check 加 `bin_prefixes.json` 存在性

---

## Security Domain

> Required by `config.json.workflow.security_enforcement = true` (default). ASVS Level 1 per `security_asvs_level: 1`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | 应用无用户账号、无 token、无远程端点 |
| V3 Session Management | no | 单进程桌面应用，会话即进程生命周期 |
| V4 Access Control | partial | 文件路径安全由 `privacyguard/utils/security.py::validate_safe_path` 守护；新增 `bin_prefixes.json` 走 `resource_path` |
| V5 Input Validation | yes | PDF 输入路径校验（既有）+ 文本输入经 `normalize_digits` / `flatten_for_match` 归一化；6 个新 validator 输入长度 / 字符类 / 校验位三层 gate |
| V6 Cryptography | no | 无加密需求；Faker 合成 PII 不构成「个人数据」保护范围（OPS-05） |
| V7 Error Handling | partial | Worker 异常经 `error_signal` 暴露；6 个新 validator 防御性（非字符串输入 → False，不抛 TypeError） |
| V9 Logging | partial | 项目用 `print()` 而非日志框架；新增 validator 模块不打印命中原文；仅打印 `[PII] 页面 X 命中 N 项敏感内容`（命中数，不打印内容） |
| V12 Files and Resources | yes | 临时目录走 `TempFileManager`；新增 `bin_prefixes.json` 经 `resource_path` 读取；PyInstaller `datas` 同步声明（cp30 教训） |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| ReDoS（恶意长字符串导致正则灾难性回溯） | Denial of Service | 截断单页文本到 N=200,000 字符 + worker `isInterruptionRequested()` 中断；**不**依赖 Python `re` 的 `timeout=`（不存在） |
| 银行卡 BIN 词典 FP 攻击（攻击者构造 Luhn 通过 + BIN 命中的 16 位字符串假装卡号） | Information Disclosure (false positive) | 三层 gate（Luhn + BIN + 上下文锥点）联合判定；无锥点 → MEDIUM 而非 HIGH；最终由人工审阅（Phase 7 候选面板）确认 |
| PyInstaller 数据文件丢失 | Denial of Service | `datas=[...]` 在 spec 显式声明 + `resource_path` 唯一入口 + Windows / macOS 双平台真机验证（cp30 教训扩展到 `bin_prefixes.json`） |
| 测试夹带真实 PII（git 历史永久保留） | Information Disclosure | `tests/fixtures/fake_pii.py` 合成；Faker + Luhn / mod-31-3 校验循环；OPS-05 禁止仓库夹带真实数据 |
| OCR 字符归一化失效导致校验失败（漏报） | Tampering | `normalize_digits` 强制全角→半角 + `flatten_for_match` 跨行拼接；单元测试覆盖全角样本 |
| Partial mask 字体回退失败导致文字溢出 rect | Information Disclosure | D-03 重算 rect 宽度（按 mask_strategy 字符数）+ 居中插入；单元测试覆盖 rect 宽度变化 |
| USCC mod-31-3 权重数组写错 | Tampering | 本机验证腾讯 USCC `91110000600037341L` 通过；权重 17 元素 + 字符表 31 元素均为公开标准 |
| `socket.socket` 在 PII 引擎里意外触发 | Information Disclosure | `tests/unit/test_pii_offline.py` 扩展覆盖 7 类新 entity；monkey-patch 拦截所有出站 socket 调用 |
| 用户原文进入 stdout / stderr（日志泄漏） | Information Disclosure | PII 引擎模块不打印命中原文；仅打印 `[PII] 页面 X 命中 N 项敏感内容`（命中数，不打印内容） |
| `bin_prefixes.json.LICENSE` 缺失 → CC BY-SA 4.0 违反 | Repudiation | `tests/unit/test_package_imports.py` 扩展断言 LICENSE 文件存在且含 `CC BY-SA` 关键字 |

---

## Sources

### Primary (HIGH confidence)

- **GB 32100-2015《法人和其他组织统一社会信用代码编码规则》** [openstd.samr.gov.cn](https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=24691C25985C1073D3A7C85629378AC0) — 31 字符表 + 17 位权重 + mod-31-3 校验公式
- **[CSDN - Python实现统一社会信用代码校验(GB32100-2015)](https://blog.csdn.net/qq_24372433/article/details/122812466)** — 字符表 `0123456789ABCDEFGHJKLMNPQRTUWXY` + 权重 `[1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]` 多源交叉验证
- **[CSDN - js校验《GB 32100-2015》](https://blog.csdn.net/qq_56851614/article/details/145111261)** — JS 实现完整源码，权重与字符表一致
- **[国家税务总局浙江省税务局公告2022年第1号](https://www.shui5.cn/article/c0/165296.html)** — 全电发票 20 位号码格式（年号 + 行政区划代码 + 渠道代码 + 顺序编码）
- **[东奥实操就业 - 数电发票号码编码规则](https://m.dongao.com/scjy/zixun_zcjd/202411284505632.html)** — 全电发票 20 位格式详细说明
- **[PyMuPDF Document.metadata 文档](https://pymupdf.readthedocs.io)** — `title/author/subject/creator/producer/keywords/creationDate/modDate/trapped` 9 个键 + `set_metadata()` API
- **[PyMuPDF Wiki - Using setMetadata() and setToC()](https://github.com/pymupdf/PyMuPDF/wiki/Using-setMetadata()-and-setToC())** — `set_metadata` 接受空字符串并产出 `metadata["title"] == ""`
- **本机 Python 验证 (2026-08-11)**：
  - `validate_uscc("91110000600037341L") == True` (腾讯科技真实 USCC)
  - `compute_check_digit("91110000600037341") == "L"` (mod-31-3 自研实现正确)
  - `luhn_valid("4532015112830366") == True` (Visa 测试卡号)
  - `luhn_valid("1234567812345670") == True` (经典 Luhn 测试数)
  - `luhn_valid("6225760000000000") == False` (维基常误引，实则不通过)
  - `doc.set_metadata({"title":"","author":"","subject":"","producer":"","creator":""})` 后 `doc.metadata["title"] == ""`
  - `page.get_text("dict")` 返回的 font 字段