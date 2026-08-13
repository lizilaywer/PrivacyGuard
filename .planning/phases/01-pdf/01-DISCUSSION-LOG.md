# Phase 1: PDF 自动识别身份证号与手机号并真脱敏 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-10
**Phase:** 1-PDF 自动识别身份证号与手机号并真脱敏
**Areas discussed:** OCR 路径范围, 真脱敏触发方式, PII 引擎与 default_rules 关系, PIIHit 数据结构粒度, OCR 补充（扫描型整页 OCR）, PIIHit offset, PII 规则存储, 设置项位置

---

## OCR 路径范围（文字层 / 图片块 / 扫描型）

| Option | Description | Selected |
|--------|-------------|----------|
| 三者全纳 | 一次性覆盖文字层 + 嵌入图片块 + 扫描型 PDF 整页回退 OCR | ✓ |
| 仅文字层 + 图片块 | 利用现有 `collect_text_pdf_hit_boxes` / `collect_image_block_ocr_hits`，扫描型 PDF 留给后续 phase | |
| 仅文字层 | 最小范围，扫描件完全不动 | |

**User's choice:** 三者全纳
**Notes:** 与 Phase 1 success criteria 1「打开任意 PDF」一致；接受 Phase 1 工作量偏大的代价。

---

## 真脱敏触发方式（自动 vs 候选确认）

| Option | Description | Selected |
|--------|-------------|----------|
| 默认自动 + 设置项可切「先确认」 | 默认 HIGH 档自动真脱敏，SettingsDialog 增加「需手动确认」开关 | ✓ |
| 打开后展示候选列表，点选后真脱敏 | 弹候选面板，用户点选确认后再真脱敏 | |
| 打开后自动真脱敏，无候选 UI | 完全无 UI 改动，Phase 1 交付最快 | |

**User's choice:** 默认自动 + 设置项可切「先确认」
**Notes:** 默认路径不增加 UI 工作量；后续 Phase 7 的候选审阅 UI 会扩展「先确认」分支。

---

## PII 引擎与 config.json default_rules 的关系

| Option | Description | Selected |
|--------|-------------|----------|
| PII 引擎独立维护，default_rules 保留不变 | 两套规则集共存，互不干扰 | ✓ |
| PII 引擎取代 default_rules 的实体部分 | 取代身份证 / 手机号 / 邮箱 / 银行卡 / 日期，保留印章与自定义关键词 | |
| PII 引擎以 default_rules 为输入 | 复用现有正则 + 补全校验位 | |

**User's choice:** PII 引擎独立维护，default_rules 保留不变
**Notes:** 守住 v37.7.6 收敛原则（不动 SimpleConfig / SettingsDialog 已有规则 tab）；接受「两条规则集共存」带来的少量重复命中风险。

---

## PIIHit 数据结构粒度

| Option | Description | Selected |
|--------|-------------|----------|
| QRectF + 附加 dataclass | `dataclass(entity_type, page_offset, page_length, page_rect, confidence_tier, source, mask_strategy)` | ✓ |
| 仅 QRectF（与 ocr / manual 一致） | 只存 QRectF，附加属性以 tuple 顺序存放 | |
| dict[str, Any] 动态结构 | 无类型检查，灵活但不可控 | |

**User's choice:** QRectF + 附加 dataclass
**Notes:** 满足 ENGINE-02 要求；为 Phase 6 上下文识别 / Phase 8 审计报告保留扩展空间。

---

## OCR 补充（扫描型整页 OCR）

| Option | Description | Selected |
|--------|-------------|----------|
| 新增 `collect_full_page_ocr_hits` 纯函数 | 与 text_pdf / mixed_pdf 对齐，dependency-injection 形态 | ✓ |
| 不动，worker 内联实现 | 直接写在 ocr_worker 里，不抽取为共享函数 | |

**User's choice:** 新增 `collect_full_page_ocr_hits` 纯函数
**Notes:** 守住 v37.7.6 收敛原则。

---

## PIIHit offset（字符级偏移）

| Option | Description | Selected |
|--------|-------------|----------|
| page_offset / page_length 字符串偏移 | 存整页文本的字符串 offset | ✓ |
| 仅存 QRectF，不存字符串偏移 | 与现有 ocr / manual 键对齐 | |

**User's choice:** page_offset / page_length 字符串偏移
**Notes:** 为 Phase 6 上下文识别 / Phase 8 审计报告提供精确字符位置。

---

## PII 规则存储

| Option | Description | Selected |
|--------|-------------|----------|
| 外部 JSON 数据文件 | `privacyguard/pii/data/rules.json`，通过 `resource_path` 读取 | ✓ |
| 硬编码在 Python 模块 | dataclass 静态构造 | |

**User's choice:** 外部 JSON 数据文件
**Notes:** **偏离推荐选项**。用户理由：支持后续 Phase 8 UX-07「用户可维护识别规则」需求。已记录 cp30 打包风险（PyInstaller `datas` / `hiddenimports` 必须同步验证）。

---

## 设置项位置（「需手动确认」开关）

| Option | Description | Selected |
|--------|-------------|----------|
| 新增 pii_settings 字段，SettingsDialog 新增「隐私识别」tab | `engine_enabled` / `auto_redact` / `require_confirmation` 三个开关 | ✓ |
| 复用现有「高级设置」tab | 在现有 tab 内加 QCheckBox | |

**User's choice:** 新增 pii_settings 字段，SettingsDialog 新增「隐私识别」tab
**Notes:** 为 Phase 7 候选审阅 UI 保留 tab 扩展空间。

---

## Claude's Discretion

- PIIHit dataclass 字段顺序与默认值（`confidence_tier` 默认建议 `"HIGH"`）
- `iter_ocr_lines` 与 PII 引擎的对接函数命名
- `collect_full_page_ocr_hits` 的扫描比例默认值（建议 `1.5`）
- Phase 1 测试 PDF 生成器位置（建议 `tests/e2e/create_pii_test_pdf.py`）

---

## Deferred Ideas

- 每文件单独规则映射（让位给 Phase 1，归属后续 phase 复盘）
- Word 双栏预览的来源筛选高亮（属于 Phase 7 / Phase 8）
- 候选审阅对话框完整实现（Phase 7 主线）
- 识别规则编辑 UI（Phase 8 UX-07）
- 审计报告 JSON（Phase 8 OPS-01）
- 完整行政区划词典 ~70 万条（Phase 6 ADV-01）
- 本地 NER 深度学习模型（PROJECT.md 明确 Out of Scope）
- v38 UI 抛光（PROJECT.md 明确让位给本轮识别准确率）
