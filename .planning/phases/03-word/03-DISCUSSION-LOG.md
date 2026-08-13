# Phase 3: Word 文档接入识别引擎（双栏对比预览自动高亮） - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 3-Word 文档接入识别引擎（双栏对比预览自动高亮）
**Areas discussed:** G1 合并优先级, G3 是否写产物, G4 位置定位, G6 模块归属

---

## G1: 合并优先级（rule > manual > ocr 的扩展）

| Option | Description | Selected |
|--------|-------------|----------|
| (a) PII 入 ocr 层 | 合并为 `rule > manual > (ocr ∪ pii)`，合并函数改动最小 | ✓ |
| (b) PII 与 manual 同层 | 自动识别质量等同手动框选，优先级 `rule > manual > pii > ocr` | |
| (c) PII 比 manual 高 | 自动识别视为最强默认，优先级 `rule > pii > manual > ocr` | |

**User's choice:** (a) PII 入 ocr 层

---

## G1 (续问): 同层（ocr ∪ pii）谁胜

| Option | Description | Selected |
|--------|-------------|----------|
| (a) PII 优先于 OCR | 校验位质量高 | ✓ |
| (b) OCR 优先于 PII | 遵循"OCR 是现有层、PII 是新接入" | |
| (c) 行为路径不同 | PII 走 partial_mask、OCR 走黑框；仅高亮重叠时 PII 胜出 | |

**User's choice:** (a) PII 优先于 OCR

---

## G1 (续问): 重叠区 mask 来源

| Option | Description | Selected |
|--------|-------------|----------|
| (a) partial_mask | PII 胜出后走 `110101********1234` | |
| (b) 纯黑框 `[已脱敏]` | OCR + PII 合并后统一全遮蔽 | |
| (c) 分路径独立 — PII partial_mask、OCR 黑框、重叠 PII 胜 | 贴合 G1.2 优先级 | ✓ |

**User's choice:** (c) 分路径独立 PII 胜
**User's clarification:** 「图片型PDF文档使用OCR纯黑框，文本类使用 partial_mask」 — 语义映射到 Word 端：OCR/图片块类走黑框、PII 自动识别走 partial_mask。

---

## G3: Word 端保存 .docx 怎么处理

| Option | Description | Selected |
|--------|-------------|----------|
| (a) 仅高亮、产物不写 | FMT-02 字面贴合 | |
| (b) 默认与 PDF 一致真脱敏 | 与 Phase 1/2「识别即脱敏」产品底线一致 | ✓ |
| (c) 默认仅高亮 + toolbar override | Phase 2 D-12 形态 | |

**User's choice:** (b) 默认与 PDF 一致真脱敏

---

## G3 (续问): 掩码模式从哪来

| Option | Description | Selected |
|--------|-------------|----------|
| (a) 复用 `pii_settings.per_entity_default` | phase 3 不新增 UI | |
| (b) 仅 word_data toolbar override | 贴合 Phase 2 D-12 文档级 override | |
| (c) 双层都有 | per_entity_default 默认 + toolbar override 临时反转 | ✓ |

**User's choice:** (c) 双层都有

---

## G3 (续问): 真脱敏实现方式

| Option | Description | Selected |
|--------|-------------|----------|
| (a) 生成文本，外部调 Python-docx | 最小侵入 | ✓ |
| (b) `write_pii_replacements` helper 封装 | 与 `pdf_adapter.py` 形态一致 | |
| (c) 重生成 mammoth HTML 后回写 | mammoth 丢格式，不可用 | |

**User's choice:** (a) 生成文本，外部调 Python-docx

---

## G3 (续问): Python-docx run 边界

| Option | Description | Selected |
|--------|-------------|----------|
| (a) 合并同段所有 run 后 replace | 段级样式保留、run 级格式丢失 | ✓ |
| (b) 仅同 run 替换、跨 run 报警告 | 产物可能不完整 | |
| (c) 拆 run 后 replace | 实现复杂、需保留原 run 样式 | |

**User's choice:** (a) 合并 run 后 replace

---

## G4: PIIHit 字段锁 vs Word 无页面坐标

| Option | Description | Selected |
|--------|-------------|----------|
| (a) 字段语义重载 | `page_offset` = char_offset、`page_rect` = None；需详细 docstring | |
| (b) PIIHit 仅内容，adapter 现场定位 | 与 `pdf_adapter.collect_pii_rects` 用 `page.search_for(raw_text)` 同范式 | ✓ |
| (c) 新增 `WordPIIHit(PIIHit)` 子类 | 破坏"Detection is format-independent"原则 | |

**User's choice:** 你来决定 (Claude's discretion)
**Claude's decision:** (b) PIIHit 仅内容描述，WordAdapter 现场用 `hit.text` 在 `paragraph_text` 中精确子串定位拿 `char_offset_in_paragraph_text`。理由：保持 Phase 1 D-05 PIIHit 字段锁 + 与 `pdf_adapter.collect_pii_rects` 范式对齐。

---

## G4 (续问): 同文本重复怎么办

| Option | Description | Selected |
|--------|-------------|----------|
| (a) 一一展开为多个独立 PIIHit | 所有出现位置均高亮均真脱敏 | ✓ |
| (b) 去重仅亮首处 | 实现简单、漏亮 | |
| (c) 亮首处 + 警告 | 让用户知道有遗漏 | |

**User's choice:** (a) 一一展开

---

## G4 (续问): source 字段 Word 端用什么

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `source = text` | 复用现有枚举，Word 文字层 = text 源 | ✓ |
| (b) `source = word_text` | 区分但需扩展枚举 | |
| (c) `source = word_paragraph` | 语义更准但需扩展枚举 | |

**User's choice:** (a) `source = text`

---

## G6: Word 适配器放哪里

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `privacyguard/pii/word_adapter.py` | 与 `pdf_adapter.py` 平级，最贴合"Detection is format-independent" | ✓ |
| (b) `privacyguard/word/` 子包 | 按格式划分子隔离，破坏"垂直 MVP 切片" | |
| (c) 不新文件，直接在 `word_worker.py` 调引擎 | 耦合度高 | |

**User's choice:** (a) `privacyguard/pii/word_adapter.py`

---

## G6 (续问): 提供哪些函数

| Option | Description | Selected |
|--------|-------------|----------|
| (a) 对称三函数（`collect_pii_word_hits` / `locate_pii_hits_in_paragraph` / `apply_pii_replacements_to_docx`） | 与 `pdf_adapter` 形态一致 | ✓ |
| (b) 只做检测定位、产物交给 `main.py` | word_adapter 保持纯函数 | |
| (c) `WordRedactionAdapter` 类封装 | OO 风格但与现有函数式接口不一致 | |

**User's choice:** (a) 对称三函数

---

## G6 (续问): word_adapter 是否 import python-docx

| Option | Description | Selected |
|--------|-------------|----------|
| (a) 不 import docx、外部传 Paragraph | 保持"引擎无 IO"原则 | ✓ |
| (b) 内 import docx、adapter 自主访问 | 紧凑但耦合 IO | |
| (c) 分两半：定位纯函数 / 写产物走 docx | 拆 helper | |

**User's choice:** (a) 不 import docx

---

## G6 (续问): PII 检测在哪个线程

| Option | Description | Selected |
|--------|-------------|----------|
| (a) 接入 `_ModularWordWorker.run()` | 与规则匹配并行；worker 职责单一 | ✓ |
| (b) 独立 `_PIIScanWorker` | 多一个线程类 | |
| (c) 跟随 OCR 路径独立 signal | 不与 ocr 合并 | |

**User's choice:** (a) 接入 `_ModularWordWorker.run()`

---

## Claude's Discretion

- PII 命中在右栏预览中的颜色 — 建议复用 PDF 端深红色，不引入新色
- `collect_pii_word_hits` 是否对 LOW 档候选做二次过滤 — 建议复用 Phase 2 `classify_hit` 范式
- `apply_pii_replacements_to_docx` 是否按段合并 run 处理跨段命中 — 建议按段粒度脱敏
- `_ModularWordWorker.run()` 接入 PII 后是否保留取消检查点 — 建议保留

## Deferred Ideas

- 候选审阅 UI 完整形态 → Phase 7
- 识别规则编辑 UI → Phase 8
- 审计报告 → Phase 8
- 行政区划词典全集 → Phase 6
- v38 UI 抛光 → 后续 phase
- 批量 Word 替换入口 PII 接入 → 后续 phase
- Word 端按来源筛选高亮 → Phase 7

---

*Phase: 3-Word*
*Discussion completed: 2026-08-11*