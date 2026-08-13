# Feature Research — Automatic PII Detection (Chinese-market focus)

**Domain:** Document redaction / DLP for personal information
**Project:** PrivacyGuard 脱敏卫士
**Researched:** 2026-08-10
**Confidence:** HIGH (Chinese PII conventions, masking patterns, redaction mechanics), MEDIUM (product UX conventions across enterprise DLP), LOW (some enterprise tool-specific UX details for Adobe/Purview/pdfSweep — only second-hand summaries found)

> Scope: how automatic sensitive-information detection features typically work in redaction/DLP products, what users expect, and what PrivacyGuard should / should-not build under its "pure local, zero-network" constraint. This feeds `FEATURES.md` of the requirements definition; the orchestrator uses the table-stakes/differentiator/anti-feature split and the per-entity masking conventions to seed phase scoping.

---

## 1. Entity Types — What's Table Stakes for a Chinese-Market Tool

### 1.1 Numbered identifiers (HIGH-confidence tier — regex + checksum)

These have a fixed format and a checksum, so detection is reliable; missing them = the tool is untrustworthy. Every credible Chinese-market tool covers them.

| Entity | Format | Validation | Tier | Source |
|---|---|---|---|---|
| 居民身份证号 | 18 位（前 17 位数字 + 末位 0-9/X），旧版 15 位（无校验位，需补全后再用 18 位校验） | GB 11643 / ISO 7064 MOD 11-2；权重 `[7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]`；校验码表 `[1,0,X,9,8,7,6,5,4,3,2]`；末位大小写 X 都需接受 | HIGH | CSDN ID checksum reference, Alibaba Cloud reference impl |
| 中国大陆手机号 | 11 位，`1[3-9]\d{9}`；段号 13x/14x/15x/17x/18x/19x 全覆盖；14x 含 140/144/146 等物联网段；旧系统可能有 10 位遗留 | 段号白名单 + 总长度 11 校验 | HIGH | 工信部公开段号分配、MIIT archive |
| 银行卡号 | 16–19 位（PCI DSS 4.0）；境内银联卡 16/19 位居多 | Luhn 校验 | HIGH | PCI DSS v4.0 |
| 邮箱地址 | RFC 5322 简化正则；中文邮箱后缀（中移动 139.com / 189.cn / 沃邮箱等）需扩展 TLD 表 | 字符级正则 + 域名校验 | HIGH | Presidio `EMAIL_ADDRESS` |
| IP 地址 | IPv4 + IPv6；中文文档里常出现的是 IPv4 | octet 范围 + 排除 0/127/255 边缘段 | MEDIUM | Presidio `IP_ADDRESS` |
| 统一社会信用代码 | 18 位，第 1 位登记管理部门代码 + 第 2 位机构类别 + 9 位登记管理机关行政区划码 + 9 位主体标识码（组织机构代码）+ 1 位校验码 | GB 32100 / ISO 7064 MOD 31-3（与 ISO 7064:1983 MOD 11-2 不同算法，不要混用） | HIGH | GB 32100-2015 |
| 增值税发票号 | 8 位数字 + 10/12 位发票代码；新版全电发票 20 位数电发票号码 | 长度 + 上下结构匹配 | HIGH | 财税行业惯例 |
| 车牌号 | 普通车牌 7 位 + 新能源 8 位；含省份简称 + 字母 + 字母/数字组合 | 省份简称锚点 + 字符结构 | MEDIUM | Presidio 中文 recognizer 社区实现 |

### 1.2 Contextual entities (MEDIUM/LOW confidence tier — keyword + dictionary)

These lack a fixed format; detection relies on dictionaries, surname anchors, and surrounding keywords. False-positive rate is inherently higher; must be surfaced as "candidate" rather than auto-applied.

| Entity | Detection strategy | Tier |
|---|---|---|
| 中文姓名 | 姓氏词典（百家姓 ~500 常见姓）+ 后续 1–2 字名 + 上下文锚点（如 "先生/女士/同志/老师"） | LOW |
| 机构名（公司名） | 后缀词典（"有限公司/股份公司/集团/事务所/医院/学校/银行"等 100+ 行业后缀）+ 行政区划词典辅助 | LOW |
| 详细地址 | 行政区划锚点（省/市/区/县/路/街/号/楼/室）+ 6 级行政区划词典（最新统计用 2024 版区划代码 ~ 700K 条目） | LOW |
| 金额 | "¥/RMB/元/万元/人民币" 前缀 + 数字 + "整/角/分" | MEDIUM |
| 合同编号 / 项目代号 | 业务前缀词典（"合同号/项目编号/工单号"）+ 字母数字混合 | LOW |
| 内部工号 / 员工编号 | 业务锚点（"工号/员工编号/工号 ID"）+ 形态匹配 | LOW |

### 1.3 Anti-target entity list

Things users do NOT want flagged by default — would drown the signal:

- 日期（除非能识别出生日期并与身份证号关联）
- 普通英文姓名（除非处于英文段落）
- 公开公司全称（上市公司、行业领袖等可设白名单）
- 网址 / URL（除非能识别为内部系统 URL）
- 通用词汇如 "张三李四" 类的占位名（应在词典层排除）

---

## 2. Confidence Scoring & UX Patterns

### 2.1 Established product patterns

Surveyed: **Adobe Acrobat Pro Redact**, **Microsoft Purview DLP**, **iText pdfSweep**, **Microsoft Presidio**, **百度 / 阿里 / 华为云 DLP**。

| Pattern | How it works | Where used | Relevance to PrivacyGuard |
|---|---|---|---|
| **Two-step Mark → Apply** | "Mark" = visual highlight + reversible metadata; "Apply" = irreversible removal. Always a separate confirm step with a warning. | Acrobat, Foxit, pdf-redactor, PyMuPDF | **Strong — table stake**. User must see what will be removed before destruction. |
| **Per-entity confidence score** | 0.0–1.0 score returned per detection; consumer decides threshold. | Presidio, Purview custom SITs | **Strong — differentiator**. Presidio's `score` (default threshold 0.5–0.85 depending on entity) is the model to copy. |
| **High/Medium/Low bucket** | Coarser: 3-bucket triage instead of raw score; matches user mental model. | Purview DLP policies (High/Medium/Low), Foxit | **Strong — table stake** for end-user presentation; raw score still useful internally. |
| **Policy tips / review queue** | User can override false positives; override is logged and fed back to retune. | Purview, Adobe | **Adapt — defer**. Without multi-tenant policy, "review queue" reduces to a per-session "candidates" panel. |
| **Inline color-coded highlight** | Yellow = auto-applied safe (number with valid checksum), Orange = needs review (name/address), Red = definitely sensitive (user-flagged or keyword). | Acrobat, most redaction UIs | **Strong — table stake**. The visual is what users immediately recognize. |

### 2.2 Recommended UX (PrivacyGuard-specific)

Three-tier display with distinct actions:

| Bucket | Source | Visual | Default action | Override |
|---|---|---|---|---|
| HIGH (auto-apply) | Numbered entity with valid checksum (身份证 mod11, 银行卡 Luhn, 手机号段号白名单, 邮箱/URL 正则) | Yellow highlight, "✓" badge | Apply on save, no confirmation | User can exclude per-instance |
| MEDIUM (review queue) | Context-anchored entities (姓名, 机构名) | Orange highlight, "?" badge | Show in candidates list; user clicks to confirm | One-click toggle per-instance |
| LOW (keyword hit only) | Custom keyword / rule match | Blue highlight, "kw" badge | Apply only if rule is configured; otherwise leave intact | User configures which rules auto-apply |

---

## 3. Masking / Anonymization Strategies

### 3.1 Spectrum of techniques

| Strategy | Description | Where used | Pros / Cons |
|---|---|---|---|
| **Full blackout (rectangle)** | Remove text/image, leave black rect. | Acrobat "Apply" default | Best for true redaction (when content is removed); visual only is catastrophic |
| **Partial masking (`*`)** | Keep prefix/suffix, mask middle. Format-preserving. | Chinese industry default (PIPL 实施后金融/政务/运营商标配) | Format-readable; preserves column structure in tables |
| **Synthetic replacement** | Replace with realistic but fake value (`13800001111` for a 手机号). | HIPAA Safe Harbor, some DLP products | Useful for dev/test data; risk if not properly disambiguated from real |
| **Hashing** | SHA-256 / bcrypt of the value, truncated. | Database DLP, tokenization | One-way; loses readability |
| **Tokenization** | Replace with a token that maps back via vault. | Enterprise DLP (Format-Preserving Tokenization) | Best for re-identification later; needs server-side vault (conflicts with "pure local") |
| **Suppression (drop)** | Remove the column / row entirely. | Excel "remove column" feature | Useful when an entire column is sensitive |

### 3.2 Chinese-market masking conventions (industry standard)

Validated against CSDN / SegmentFault / 博客园 / 知乎 / 阿里云 / 多个政务脱敏规范文章：

| 字段 | 标准格式 | 示例 | 备注 |
|---|---|---|---|
| 姓名 | 保留姓，名字全部掩码（单字名 1 字符、双字名 2 字符）；复姓保留复姓 | `张*` / `欧阳**` | 不可整列掩码成 `***`；保留姓便于核对 |
| 手机号 | 前 3 + 后 4，中间 4 位 `****` | `138****5678` | 11 位长度不可破坏，否则无法作为字符串回查 |
| 身份证号 | 前 6 位（地区码）+ 后 4 位，中间 8 位 `*`（18 位标准）；15 位旧号升级为 18 位后再脱敏 | `110101********1234` | 末位 X 必须原样保留（大小写都接受） |
| 银行卡号 | PCI DSS 标准：最多保留前 6 + 后 4；境内惯例常做前 4 + 后 4 | `6225 **** **** 1234` | 不可暴露 BIN（发卡行标识）；不可保留中间 8 位 |
| 邮箱 | 保留首字符 + `@` + 完整域名 | `z****@qq.com` | 域名部分不能掩码（影响邮件路由） |
| 地址 | 保留到区/街道级，详细门牌号掩码 | `北京市朝阳区****` | 不可整段掩码（失去定位意义） |
| 金额 | 保留量级，个位掩码 | `¥12,3**` | 金融场景下常用此格式做模糊披露 |

### 3.3 Implementation note for PrivacyGuard

- 默认策略：**partial masking**（partial_mask 函数是默认出口）
- 全 blackout：仅在用户显式选择 "整段覆盖" 时使用（PDF 文本层用 `add_redact_annot` + `apply_redactions`，**禁止**用 draw_rect 假装脱敏）
- 哈希 / 令牌化：**不实现** — 与纯本地约束冲突；纯本地无法提供可逆令牌仓库
- 合成替换：**不实现** — 用户拿到的是真实文件，不是测试样本

---

## 4. Excel / Spreadsheet Redaction — User Expectations

### 4.1 What users actually expect

Based on Excel handling patterns (Microsoft, Aliyun, Tencent DLP docs) and Excel 特有泄漏面 (Microsoft docs on Excel hidden data, OWASP spreadsheet leaks):

| Expectation | Why | Complexity | Notes |
|---|---|---|---|
| **整表扫描** | 散点敏感信息无处不在，按列扫描漏掉跨列引用 | MEDIUM | openpyxl `iter_rows()` |
| **列名驱动升级** | 表头叫"身份证号"的列整列同类；表头叫"姓名"的列每行都可能是姓名 | HIGH | 列名 → 实体类型词典（"身份证/ID/IDCard/证件号/身份证号/身份证件"等） |
| **保留公式** | `=SUM(A1:A10)` 不能变成 `#REF!`；`data_only=False` 必须 | LOW | openpyxl 标准用法 |
| **保留样式** | 字体、填充、边框、合并、列宽行高、条件格式、数据验证 | LOW | openpyxl `cell.font/fill/border/alignment/number_format/protection` 在 `.value` 改变时自动保留 |
| **多 sheet 全部扫描** | 用户经常在一个工作簿里有"汇总 sheet + 明细 sheet"，明细里才有真敏感信息 | MEDIUM | `wb.worksheets` 全遍历 |
| **隐藏 sheet 是泄漏面** | "很常见"——隐藏 sheet 经常被遗忘 | MEDIUM | openpyxl `ws.sheet_state` 可见性查询；扫描时强制包含所有 sheet（不跳过 hidden / veryHidden） |
| **批注 / 注释** | 批注经常含敏感信息（"老李的身份证"），需清除或扫描 | LOW | openpyxl `cell.comment = None` 清空；或扫描 comment.text |
| **定义名称 / 命名区域** | Named ranges 引用地址常含敏感信息 | LOW | openpyxl `wb.defined_names.clear()` |
| **共享字符串 / SharedStrings** | 重复字符串去重表，可能残留旧值 | LOW | openpyxl 重保存自动 prune |
| **文档属性（作者 / 公司 / 最后修改者）** | 元数据常含真实姓名 / 内部路径 | LOW | openpyxl `wb.properties.creator/lastModifiedBy` 需清空或扫描 |
| **冻结窗格 / 打印标题 / 页眉页脚** | 页眉页脚可能重复敏感内容 | LOW | openpyxl `oddHeader/oddFooter` 字段 |
| **数据验证下拉列表** | 名单 / 部门列表 / 状态枚举常含敏感实体 | LOW | openpyxl `data_validations` 字段 |
| **条件格式规则** | 含敏感字符串的规则需扫描 | LOW | openpyxl `conditional_formatting` |

### 4.2 Excel-specific masking strategy

**不要**整列做 `***` / `保密` / 空字符串覆盖（破坏可读性和公式引用）。**要做**：

1. 散点敏感（身份证、手机号、邮箱、银行卡） → 按值用 partial masking
2. 整列同类（识别出列名 = "身份证号"） → 整列按 partial masking 模式脱敏（仍保留格式）
3. 整列全敏感（无法识别哪些行是真，哪些是测试数据） → 整列 partial masking（默认），并标记"已按列批量处理"供 review

---

## 5. False-Positive Management

| Mechanism | Description | Complexity | When to use |
|---|---|---|---|
| **按实体类型启用/禁用开关** | 用户可关闭"姓名识别"或"车牌识别"等单类 | LOW | 始终提供 |
| **最小置信度阈值** | 低于阈值的候选不进 review 队列 | LOW | 始终提供，默认值要谨慎（LOW=0.3 起步） |
| **白名单（精确匹配）** | 用户输入"这家公司不算敏感"，全文档不再命中 | LOW | 始终提供 |
| **白名单（正则）** | 用户输入正则，整个模式不再匹配 | LOW | 高级设置 |
| **上下文排除** | "在 `测试`/`示例`/`demo` 段落里的同类不报" | MEDIUM | 可选；用上下文窗口 + 否定词典 |
| **单实例取消** | review 队列里点 "忽略本次" | LOW | 始终提供（基本操作） |
| **频率阈值** | 同一字符串出现 N 次以上才报（过滤掉文档里反复出现的样板内容） | MEDIUM | 可选；防止"本公司 / 北京市 / 王伟"类的过曝 |
| **审计模式（仅标记不应用）** | 默认 dry-run，让用户先看一遍再决定 | LOW | 首次使用 / 试运行场景 |

---

## 6. Auditability

| Feature | Why expected | Complexity | Notes |
|---|---|---|---|
| **脱敏报告（per-document）** | 合规要求（PIPL / GDPR / HIPAA）；事后审计、举证 | MEDIUM | JSON / Markdown 输出：源文件、检测到的实体清单（含位置、类型、置信度、处置策略）、脱敏规则版本、时间戳、操作者 |
| **脱敏报告（批量）** | 批量处理必须输出汇总表 | MEDIUM | CSV / Excel 导出：每个文件的检测数、脱敏数、规则命中数 |
| **规则版本快照** | 出问题时能复现"当时用了哪版规则" | LOW | 把规则集哈希写到报告头 |
| **可复核原始命中** | 用户点击报告里一条 → 跳到原文位置（PDF 跳页码 + bbox；Word 跳段落） | HIGH | 关联到原文位置（识别引擎必须输出精确字符偏移） |
| **撤销 / 重做** | 用户发现漏脱 / 误脱，要能回滚 | MEDIUM | 必须保留未脱敏原文副本到临时目录（用现有的 `temp_manager`） |
| **操作日志（用户行为）** | 谁在什么时间用什么规则处理了什么文件 | LOW | session log，写本地 JSON |

---

## 7. Catastrophic Anti-Features (Documented Failure Modes)

These must be explicitly avoided. Each is a real, documented failure pattern in the industry.

### 7.1 The "black box" redaction (HIGH severity)

**What goes wrong:** Tool draws a filled black rectangle on top of sensitive text; underlying text remains in the PDF content stream and is trivially recoverable via `pdftotext` / `Page.get_text()` / select-and-copy.

**Real-world incidents:**
- Facebook 2022 court filings: 内部战略文档 "redacted" black bar, 文本可恢复
- UK ICO 2021: 虐童嫌疑人名单 "redacted", 名字仍可恢复
- UK MoD 2018: 阿富汗翻译身份泄露
- Ghislaine Maxwell 2021: 法庭文件"redacted"，姓名可恢复

**Correct approach (must use):** PyMuPDF `add_redact_annot()` + `apply_redactions()` with `images=PDF_REDACT_IMAGE_REMOVE, graphics=PDF_REDACT_GRAPHICS_REMOVE, text=True` + `garbage=4, deflate=True` save. This actually deletes the text operators from the content stream.

**Verification step (must include in pipeline):** `Page.get_text("words")` after redaction should return nothing in the redacted region. Add this as an automated check in the test suite.

### 7.2 The "metadata leaks" redaction (HIGH severity)

**What goes wrong:** User redacts the visible text but PDF metadata (Author, Title, XMP, revision history, embedded fonts' glyph data, JavaScript, form fields, bookmarks, comments) still contains the sensitive info.

**Correct approach:** `doc.set_metadata({})`, `doc.xref_get_key(-1, "Author")` to inspect, strip with `garbage=4`. Excel equivalent: clear `wb.properties.creator / lastModifiedBy / title / subject / keywords` and clear defined names.

### 7.3 The "OCR-then-redact-text" mistake (HIGH severity)

**What goes wrong:** PDF has an OCR layer "behind" the image. Redaction only operates on the rasterized image; the OCR'd text in the hidden text layer survives.

**Correct approach:** For image-based PDFs, either redact at the image level (re-render the page as raster, draw the mask, strip OCR text layer) or detect both layers and process both.

### 7.4 Cloud-LLM detection (BLOCKER for PrivacyGuard)

**What goes wrong:** Tool sends the document to a remote LLM endpoint for "AI detection"; the sensitive data is now on someone else's server, and the original privacy violation (exposing the document) is worse than the leakage it was trying to prevent.

**Hard rule:** PrivacyGuard's product constraint is "纯本地" — never implement, never propose as a fallback. Reject even "anonymized" cloud calls.

### 7.5 Full local NER deep-learning model (DEFERRABLE, not catastrophic)

**Why avoid now:** `zh_core_web_trf` (spaCy Chinese transformer) is ~400 MB; adding it triples install / packaging size; cold start is 5–10s. The PROJECT.md decision is to validate rule-line first.

**When to revisit:** If rule-line proves inadequate for 姓名 / 机构 / 地址 after real-document testing, evaluate `zh_core_web_sm` (~ 50 MB) or `zh_core_web_md` (~ 100 MB) as a fallback. Do NOT add without a separate milestone-level decision.

### 7.6 Drawing rectangles via annotation (HIGH severity)

Same as 7.1 — annotation ≠ redaction. The PyMuPDF redaction API exists precisely to make this mistake impossible; use it exclusively for PDF.

### 7.7 CSV support (OUT OF SCOPE this round)

Reasoning: CSV is a leak vector (no schema enforcement, encoding quirks, no "table" semantics for column-name inference). Adding it now muddies the Excel strategy. Defer to a later milestone if requested.

### 7.8 PowerPoint support (OUT OF SCOPE this round)

Reasoning: PPTX redaction is its own complex topic (speaker notes, embedded media, animations); defer.

---

## 8. Feature Dependency Graph

```
[Chinese PII rule engine v1] (身份证/手机号/银行卡/邮箱/URL/IP — regex + checksum)
        │
        ├──requires──> [识别结果 schema: entity + position + confidence]
        │                       │
        │                       ├──requires──> [partial masking per entity type]
        │                       │                       │
        │                       │                       └──requires──> [PyMuPDF true redaction API]
        │                       │                       │
        │                       │                       └──requires──> [python-docx run-aware replacement]
        │                       │
        │                       └──requires──> [Two-tier HIGH/MEDIUM candidate list UI]
        │
        └──enhances──> [Excel column-header inference] (列名 → 实体类型映射)
                                │
                                └──requires──> [openpyxl 全表扫描 + hidden sheet inclusion]
                                                       │
                                                       ├──requires──> [defined names / comments / metadata 扫描]
                                                       │
                                                       └──requires──> [公式保留写入 + 样式保留]

[EXIF stripping for images] ──requires──> [Pillow / piexif] ──enhances──> [image OCR redaction]

[Detection log / 脱敏报告] ──requires──> [识别结果 schema] ──requires──> [temp_manager for 原文件保留]
```

Key ordering observations:

1. **识别 schema (entity+position+confidence)** is the keystone — partial masking, audit report, and review queue all require it.
2. **PyMuPDF true redaction API** must be wrapped before any PDF detection feature can claim to be "safe".
3. **Excel column-header inference** is downstream of the basic engine — it uses entity detection results to decide column-level bulk handling.
4. **EXIF stripping** is independent but uses the existing OCR pipeline.

---

## 9. MVP Recommendation

### 9.1 Phase 1 (must-have for the milestone)

- [ ] **基础规则引擎**: 身份证 mod11 / 手机号段号 / 银行卡 Luhn / 邮箱 / URL / IPv4 / 统一社会信用代码 mod31-3 — HIGH 置信度层
- [ ] **PDF 文字层接入识别结果**: PyMuPDF 文本层搜索 + 字符偏移回传
- [ ] **PDF OCR 路径接入识别结果**: RapidOCR 命中 + 局部框坐标换算（已有 mixed_pdf.py 扩展）
- [ ] **PyMuPDF true redaction 包装**: add_redact_annot + apply_redactions，禁止 draw_rect
- [ ] **Partial masking per entity type**: 按 3.2 表格实现掩码函数
- [ ] **Two-tier candidate list UI**: HIGH 自动进脱敏；MEDIUM/LOW 进 review 面板
- [ ] **False-positive 控制**: 按实体类型启用/禁用、单实例忽略、文档级白名单
- [ ] **PDF 元数据清除**: set_metadata({}) + 文档属性扫描
- [ ] **脱敏报告 per-document**: JSON 输出（含位置 / 类型 / 置信度 / 处置）

### 9.2 Phase 2 (after Phase 1 validated)

- [ ] **上下文型实体（姓名/机构/地址）**: 词典 + 上下文锚点，输出 LOW 候选
- [ ] **Excel 全表扫描 + 列名驱动升级**
- [ ] **Excel 公式 + 样式 + 合并保留**
- [ ] **Excel 隐藏 sheet / 批注 / 定义名称 / 共享字符串 扫描**
- [ ] **Word OCR 路径接入识别结果**（Word 已是 docx 文本流，但扫描件需 OCR）
- [ ] **独立图片文件 OCR + EXIF 清除**

### 9.3 Defer (v2+)

- [ ] **批量报告（多文件汇总 CSV/Excel）** — Phase 1 单文件报告足够 MVP；批量汇总待用
- [ ] **规则版本快照 / 操作日志** — 合规深化，按需追加
- [ ] **可点击报告跳原文位置** — UI 投入大，等核心识别稳定后再做
- [ ] **本地 NER 模型回退** — 仅在规则路线撞墙时评估
- [ ] **CSV / PowerPoint 支持** — 不在本轮范围

---

## 10. Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| 基础规则引擎（号码类 + 校验位） | HIGH | MEDIUM | **P1** |
| PDF true redaction (PyMuPDF) | HIGH | LOW | **P1** |
| Partial masking per entity type | HIGH | LOW | **P1** |
| Two-tier candidate UI | HIGH | MEDIUM | **P1** |
| False-positive 控制（开关 + 忽略 + 白名单） | HIGH | LOW | **P1** |
| PDF 元数据清除 | HIGH | LOW | **P1** |
| 单文件脱敏报告 | MEDIUM | LOW | **P1** |
| 上下文型实体（姓名/机构/地址） | HIGH | HIGH | **P2** |
| Excel 全表扫描 | HIGH | MEDIUM | **P2** |
| Excel 列名驱动升级 | MEDIUM | HIGH | **P2** |
| Excel 公式/样式/合并保留 | HIGH | LOW | **P2** |
| Excel 隐藏数据面扫描 | HIGH | MEDIUM | **P2** |
| 图片 OCR + EXIF 清除 | MEDIUM | MEDIUM | **P2** |
| Word OCR 路径 | LOW | LOW | **P2** |
| 批量脱敏报告 | MEDIUM | LOW | **P3** |
| 规则版本快照 | LOW | LOW | **P3** |
| 可点击报告跳原文位置 | MEDIUM | HIGH | **P3** |
| 本地 NER 模型回退 | MEDIUM | HIGH | **P3** |
| 上下文排除（test/demo 段落跳过） | LOW | MEDIUM | **P3** |
| 频率阈值（样板内容过滤） | LOW | MEDIUM | **P3** |

**Priority key:**
- P1: must-have for milestone validation
- P2: should-have, add in Phase 2
- P3: nice-to-have, future

---

## 11. Competitor / Reference Mapping

| Capability | Adobe Acrobat | Microsoft Purview | iText pdfSweep | Presidio | Chinese 桌面脱敏工具 (典型) | PrivacyGuard 计划 |
|---|---|---|---|---|---|---|
| 自动发现实体 | 关键字 + 简单 pattern | SIT 库 200+ | 自带 pattern + 自定义 | analyzer + 自定义 recognizer | 关键字为主，少量正则 | 规则引擎 v1 + 词典锚点 |
| 置信度评分 | 无显式评分 | High/Med/Low bucket | 无 | 0.0–1.0 score | 无 | 三档 bucket + 原始 score |
| 自动应用 vs 候选 | Mark → Apply 两步 | 自动应用 + override | 自动应用 | 由 consumer 决定 | 自动 | HIGH 自动；MEDIUM/LOW 候选 |
| 校验位验证 | 信用卡 Luhn、SSN 形式 | 各类 SIT 自带 | 信用卡 Luhn | CREDIT_CARD Luhn | 偶有 | 必带：身份证 mod11、手机号段号、银行卡 Luhn、统一社会信用代码 mod31-3 |
| 部分掩码 | 不支持（仅覆盖） | 按 SIT 模板 | replace / mask operator | mask / replace / hash | partial masking 是中国默认 | 默认 partial masking |
| Excel 列名驱动 | 无 | 部分（SIT 上下文） | 不涉及 | analyzer 可加 context | 无 | Phase 2 |
| 真实移除 PDF 文本 | Apply Redactions | 是 | `pdfSweep.removeText()` | N/A（纯文本） | 参差不齐 | PyMuPDF `apply_redactions` |
| 元数据清除 | 是 | 是 | 是 | N/A | 部分 | `set_metadata({})` + 文档属性 |
| 审计报告 | 标记清单 | 活动浏览器 / 警报 | 无 | 无 | 偶有 | JSON per-document |
| 纯本地 | 否（云订阅） | 否（云服务） | 自托管 | 自托管 | 大多数是 | 是（产品底线） |

**PrivacyGuard 的差异化定位**：在"纯本地、零网络、桌面端、零云订阅"这条赛道上，把中文 PII 校验位精度 + 真实 PDF 移除 + Excel 列名驱动 + per-document 审计报告做到位。这恰好是 Adobe（云）/ Purview（云）/ Presidio（自托管但英文优先）覆盖不到的小生境。

---

## 12. Sources & Confidence

| Topic | Source | Confidence |
|---|---|---|
| 身份证 mod11 校验位算法 | CSDN 博客、Alibaba Cloud reference、vvk/id-card | HIGH |
| 手机号段号历史与正则 | 工信部公开段号分配（间接）、社区 regex 库 | HIGH（结构）/ MEDIUM（最新段号完备性） |
| 银行卡 Luhn + 16–19 位 + PCI DSS 限制 | PCI DSS v4.0 摘要 | HIGH |
| 统一社会信用代码 mod31-3 | GB 32100-2015（间接）、中文社区引用 | HIGH |
| Chinese masking 行业惯例 | CSDN / SegmentFault / 博客园 / 知乎 / 阿里云 / 政务脱敏规范文章 | HIGH |
| Adobe Acrobat Mark/Apply 工作流 | Adobe 官方文档（间接） | HIGH |
| Microsoft Purview SIT High/Med/Low 置信度 | Microsoft Learn 文档（间接） | HIGH |
| Presidio analyzer + 中文 recognizer | microsoft/presidio GitHub Issue #1284、treasun1229/presidio_zh、官方 docs | HIGH |
| PyMuPDF true redaction API | pymupdf.io/landing-redact、PyMuPDF 文档、Foxit 博客真实事故案例 | HIGH |
| PDF "black box" 灾难性失败 | Foxit blog（2025）、公开事故：Facebook 2022、UK ICO 2021、UK MoD 2018、Ghislaine Maxwell 2021 | HIGH |
| openpyxl 公式/样式/合并保留 | openpyxl 文档、中文 Zhihu 教程 | HIGH |
| Excel 隐藏 sheet / 批注 / 定义名称 泄漏 | openpyxl 文档、Microsoft Learn on Excel hidden data | HIGH |
| Pillow + piexif EXIF 清除 | Pillow / piexif 文档、Stack Overflow | HIGH |
| 正则 ReDoS 风险 | python/cpython CVE-2018-1060/1061、Python-Markdown commit | HIGH |
| iText pdfSweep 细节 | 官方 iText 文档（仅找到间接引用，未直接抓取） | MEDIUM |
| Adobe / Purview 具体 UX 细节 | 二手摘要，未访问官方产品文档原页面 | MEDIUM |

### Gaps to address in phase-specific research later

- 最新 MIIT 段号白名单（166/199/198 等是否完整） — Phase 1 实施前需补一次定向搜索
- 统一社会信用代码 9 位登记管理机关行政区划码词典 — 需要单独的 GB 数据集评估
- 行政区划词典（最新 2024 版 ~ 700K 条目） — Phase 2 上下文型实体前必须确定数据源和打包策略
- 增值税发票号（全电发票 20 位版本）的最新格式 — Phase 1 末尾确认
- 真实事故中"红头文件"等中文特殊文档格式的 OCR 识别难度 — Phase 2 验收前确认

---

*Feature research for PrivacyGuard 自动敏感信息识别 + 多格式支持*
*Researched: 2026-08-10*
