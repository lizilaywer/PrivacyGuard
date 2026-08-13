# Phase 2: PDF 增加银行卡/邮箱/财税实体识别与部分掩码 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 2-PDF
**Areas discussed:** Partial mask 写入策略, 新实体验证强度, Mask 模式切换粒度, PDF 元数据清除

---

## Partial mask 写入策略

### Q1: Partial mask 怎么写进 PDF？

| Option | Description | Selected |
|--------|-------------|----------|
| 销毁 + 矩形底色 + insert_text | 现有路径：apply_redactions 销毁底层文本+像素；add_redact_annot 画黑底色块；然后 page.insert_text() 在色块上写 partial mask 文字 | ✓ |
| 销毁 + insert_textbox 同区域文本重写 | 不画黑底色块，直接用 page.insert_textbox 覆盖原 rect 范围写 partial mask | |
| 加决策权给用户 | add_redact_annot 默认在 partial mask 路径下只在背景画黑底；FULL blackout 路径保持现在画黑框不写字 | |

**User's choice:** 销毁 + 矩形底色 + insert_text
**Notes:** 与现有代码 90% 复用；reverse-test pdftotext 拿不到原文。字体大小与原文一致需小心。

### Q2: Partial mask 文字的字体从哪里来？

| Option | Description | Selected |
|--------|-------------|----------|
| 源 page 字体匹配 | 文本层路径从 get_text("dict") 拿原文 font+size 同步插入 | |
| 全文档默认字体 | 用 PDF 默认 sans-serif + 估字号 | |
| 混合：文本层取源 font，OCR 路径用默认 | 按路径分支：文本层路径从 get_text("dict") 取最近 span 的 font+size；OCR / 占位 rect 路径用默认 sans-serif + 估字号 | ✓ |

**User's choice:** 混合：文本层取源 font，OCR 路径用默认
**Notes:** 两条路径需分别测。

### Q3: 邮箱的 mask （z****@qq.com）与原文长度可能不同，如何处理几何对齐？

| Option | Description | Selected |
|--------|-------------|----------|
| rect 跟 mask 长度走 | rect 宽度按 mask 字符数重算：原 13 字符原文与 12 字符 mask 出现 1 字符差。mask 写入居中于原 rect | ✓ |
| rect 沿用原文位置 | rect 位置与宽度全部跟原文（page_rect），mask 文字补 trailing 空格到原宽度 | |
| 按 entity type 策略表 | 按 entity_type 预定义 mask_length_deviation 容差表 | |

**User's choice:** rect 跟 mask 长度走
**Notes:** page_offset 维持原位置，不被 rect 宽度变化影响。

### Q4: Mask 模式表示（per-entity 关闭、per-document 关闭、全局）三者在什么状态？

| Option | Description | Selected |
|--------|-------------|----------|
| 全局 per-entity 总开关 + 文档级覆盖 | config.json.pii_settings 扩展为 per_entity_default 字典；保存时 mask_mode 决定每条 hit 的最终模式 | ✓ |
| PIIHit 增字段 + 运行时 toggled | PIIHit 增字段 mask_mode，默认为 partial；某文档运行时某个实体可被用户切换为 blackout | |
| 混合：全局 per-entity + 文档级批处理开关 | 全局 per-entity 默认：所有 hit 默认走该模式；保存时由 main_window 用 Save 前快速 toggle 临时为 'this_document_all_blackout' | |

**User's choice:** 全局 per-entity 总开关 + 文档级覆盖

---

## 新实体验证强度

### Q5: 银行卡识别 （NUM-04）：什么 Luhn + 什么上下文验证？

| Option | Description | Selected |
|--------|-------------|----------|
| Luhn 必过 + 6 位 BIN 词典白名单 + 上下文锚点 | 13-19 位数字，过 Luhn。同时以 BIN 前 6 位查内置 BIN 词典（1万+ 条），BIN 不命中直接 reject。另需上下文锥点 | ✓ |
| Luhn 必过 + BIN 词典白名单 | 仅 Luhn + BIN 词典，不加上下文锥点 | |
| Luhn 必过，上下文不校验 | 仅 Luhn， BIN 词典不加载 | |

**User's choice:** Luhn 必过 + 6 位 BIN 词典白名单 + 上下文锚点（推荐）
**Notes:** 上下文锥点（卡号/账号/银行/支付）±20 字符提升 confidence 至 HIGH。

### Q6: USCC 识别 （FIN-01）：什么验证规则？

| Option | Description | Selected |
|--------|-------------|----------|
| GB 32100 mod-31-3 必过 | 18 位 + 纯大写字母数字，过 GB 32100 mod-31-3 | |
| mod-31-3 + 登记管理部门类别代码表 | 在 mod-31-3 基础上加上登记管理部门类别代码表 （1=机构编制、5=民政、9=工商、Y=其他、A=交通运输、B=司法）预筛选 | ✓ |
| mod-31-3 + 上下文锥点 | 在 mod-31-3 基础上要求上下文锥点（社会信用代码/信用代码/营业执照）±20字符 | |

**User's choice:** mod-31-3 + 登记管理部门类别代码表（推荐）

### Q7: VAT 发票号 + 纳税人识别号识别 （FIN-02 / FIN-03）：怎么拆？

| Option | Description | Selected |
|--------|-------------|----------|
| VAT 发票号 = 传统 8 位 + 全电发票 20 位 + 上下文锥点 | VAT 发票号：两种格式都支持 —— 传统 8 位纯数字发票号 + 2022 年起全电发票的 20 位号码。均需上下文锥点（发票/号码/票号）才进 candidate | ✓ |
| VAT 发票号 仅上下文锥点 | 只检 8 位传统 VAT（不考虑全电发票） | |
| 纳税人识别号 = 与 USCC 合并为一个 candidate type | 2015 年后三证合一 = USCC，旧版 15 位以独立 type CN_TAXPAYER_ID_15 处理 | ✓ |

**User's choice:** VAT 发票号 = 传统 8 位 + 全电发票 20 位 + 上下文锥点（推荐）+ 纳税人识别号 = 旧版 15 位独立 type（Q7 option 3 也选）

### Q8: 银行账号识别 （FIN-04）：无 mod-11-2 之类标准校验位，怎么处理？

| Option | Description | Selected |
|--------|-------------|----------|
| 9-21 位纯数字 + 上下文锥点必查 | 9-21 位纯数字（各行长度不统一），必加上下文锥点（账号/账户/银行账号）±20字符 | ✓ |
| 9-21 位纯数字，仅纯长度 | 仅以长度 + 纯数字判定 （9-21 位），无任何锥点 | |
| MEDIUM 档进候选列表（不默认脱敏） | 仅上下文锥点，但锥点 hit 后作为 MEDIUM 档 hit 进候选列表 | |

**User's choice:** 9-21 位纯数字 + 上下文锥点必查（推荐）

---

## Mask 模式切换粒度

### Q9: Mask 模式切换 UI 放哪？

| Option | Description | Selected |
|--------|-------------|----------|
| SettingsDialog 「隐私识别」tab 加列表 | 复用 Phase 1 D-08 的 「隐私识别」tab，新增「脱敏方式」表：5 个实体类型 + 「部分掩码/全遮蔽」 下拉 | ✓ |
| 主界面工具栏加 「本文件使用全遮蔽」 toggle | 勾选时临时 覆盖全局 per-entity 设置 | |
| 两个入口都做 | SettingsDialog 提供全局设置；主界面 toolbar 「本文件」 toggle 覆盖；同时在候选审阅弹层（Phase 7）按 hit 逐个可切 | |

**User's choice:** SettingsDialog 「隐私识别」tab 加列表（推荐）
**Notes:** D-12 toolbar 文档级 override 单独由 Q11 决策。

### Q10: SettingsDialog 表中 「部分掩码/全遮蔽」 的选项交互怎么设？

| Option | Description | Selected |
|--------|-------------|----------|
| 逐 entity 独立下拉 | 逐个 entity 类型 独立下拉选项：partial | blackout。默认全为 partial | |
| 逐 entity 复选框 + 底部一括黑/括星 | 逐个 entity 复选框 （启用/禁用识别）+ 底部一个 「全局一括黑/一括星」 toggle | ✓ |
| 逐 entity 下拉 + 顶部 "一括黑" 一键反转 | 逐个 entity 下拉 + 顶部一个 「全选 为全遮蔽」 一键反转按钮 | |

**User's choice:** 逐 entity 复选框 + 底部一括黑/括星

### Q11: 「本文件」 override 这个能力 Phase 2 要不要实现？

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 2 不实现 | Phase 2 只实现 「全局 per-entity」。「本文件覆盖」 标记为 Phase 7 候选审阅 UI 的项 | |
| Phase 2 也实现 toolbar 文档级 override | 在主界面 toolbar 增 「本文件使用全遮蔽」 toggle。勾选时 临时覆盖全局 per-entity 设置 | ✓ |
| 不做 UI，只预留接口 | 以 「feature flag」 形式预留接口 | |

**User's choice:** Phase 2 也实现 toolbar 文档级 override

---

## PDF 元数据清除

### Q12: 元数据清除范围？

| Option | Description | Selected |
|--------|-------------|----------|
| 只清 ROADMAP 列出的 5 个字段 | Title / Author / Subject / Producer / Creator。CreationDate / ModDate / Keywords 保留 | ✓ |
| 上述 5 个 + CreationDate + ModDate + Keywords | 共 8 个字段 | |
| 全清，仅留 PDF 版本号 | 调用 doc.set_metadata({}) 一次清空 所有元数据 | |

**User's choice:** 只清 ROADMAP 列出的 5 个字段（推荐）
**Notes:** 与 ROADMAP Success Criteria 完全对齐。

### Q13: 被清的字段写什么占位？

| Option | Description | Selected |
|--------|-------------|----------|
| 全空字符串 | 被清的 5 个字段全置空字符串 | ✓ |
| 「-」 单字符占位 | Title / Subject 置 「-」， Author 置 「Anonymous」，Producer 置 「PyMuPDF」 | |
| 默认加 PrivacyGuard Toolchain 标志占位 | Title/Subject 置 「Redacted」， Author 置 「Redacted by PrivacyGuard」 | |

**User's choice:** 全空字符串

### Q14: 元数据清除什么时机调用？

| Option | Description | Selected |
|--------|-------------|----------|
| 只保存时（与黑框脱敏同位置） | 只调一次：保存脱敏后 PDF 的时候。与 apply_pii_redactions 同位置、在 doc.save 前调 set_metadata | ✓ |
| 打开时也清一次 | 打开 PDF 时读取原元数据 + 准备覆盖表，保存时调 set_metadata 一起写 | |
| 在 apply_pii_redactions 内部统一处理 | 抽到 privacyguard.pii.pdf_adapter 里 new 函数 clear_pdf_metadata | |

**User's choice:** 只保存时（与黑框脱敏同位置，推荐）

---

## Claude's Discretion

- PIIHit 是否要扩展 mask_strategy 为含字体信息（建议不扩展，字体现场取）
- 新增 5 类实体在画布上的颜色（建议全沿用深红色）
- 邮箱 z****@qq.com 多级子域截断位置（按首字符 + @ 后最后一段）
- 银行卡 BIN 词典最终条数（建议 1 万-1.5 万条）
- USCC 旧版 15 位 CN_TAXPAYER_ID_15 的 mask 策略（建议前 6 + 后 4，与 18 位 USCC 一致）
- 邮箱正则严格度（RFC 5322 简化版，CAPTCHA-style）

## Deferred Ideas

- 候选审阅 UI 完整实现 — Phase 7
- 识别规则编辑 UI — Phase 8 UX-07
- 审计报告 — Phase 8 OPS-01
- 行政区划词典 — Phase 6
- BIC（银行识别码）识别 — 后续 phase 候选
- 批次内跨文档掩码一致性策略 — BATCH-02