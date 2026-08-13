# PrivacyGuard 脱敏卫士

## What This Is

PrivacyGuard 是一个纯本地运行的桌面端文档脱敏工具（Python + PyQt6），面向需要处理 PDF、Word 等文档中隐私信息的个人与办公场景。当前版本 v37.7.6 已具备 PDF（文字型/图片型/混合型）与 Word 的脱敏能力、双栏对比预览和批量替换。

这一轮要做的是：**从"用户告诉工具要脱什么"转向"工具自己看出该脱什么"** —— 装上纯本地的敏感信息自动识别引擎，同时把文档格式支持扩展到 Excel 与图片文件，并新增部分掩码这种保留可读性的脱敏方式。

## Core Value

**打开文档就自动列出所有敏感项，用户不用再手输关键词。** 如果自动识别不可靠，这一轮就等于没做。

## Requirements

### Validated

<!-- 已在 v37.7.6 及之前版本交付并稳定运行的能力，来源：.planning/codebase/ -->

- ✓ 文字型 PDF 脱敏（PyMuPDF 文本层搜索命中） — existing
- ✓ 图片型 PDF 脱敏（RapidOCR 识别扫描内容） — existing
- ✓ 混合型 PDF 脱敏（文本层命中 + 嵌入图片块 OCR，坐标换算后合并去重） — existing
- ✓ PDF 手动矩形框选脱敏 — existing
- ✓ Word 智能扫描识别与手动精确 / 全局脱敏 — existing
- ✓ Word 多字段替换规则（`exact` / `regex`） — existing
- ✓ Word 批量替换（`.docx` / `.doc`，经 LibreOffice/antiword 转换） — existing
- ✓ Word 双栏对比预览（左原文 / 右替换后，优先级 `rule > manual > ocr`，按 `data-key` 局部 DOM patch） — existing
- ✓ 拖拽打开文件与批量入口 — existing
- ✓ 图片合并工作流 — existing
- ✓ 高级设置面板（脱敏规则、自定义关键词、OCR 调整、密度） — existing
- ✓ Windows / macOS PyInstaller 跨平台打包 — existing
- ✓ 零网络依赖（无后端、无数据库、无鉴权、无 webhook） — existing

### Active

<!-- 本轮目标。均为假设，交付并验证后才移入 Validated。 -->

- [ ] 纯本地敏感信息自动识别引擎：文档打开后自动扫描并列出敏感项候选
- [ ] 号码类实体高置信度识别（身份证号 mod11 校验、手机号、银行卡 Luhn 校验、邮箱）
- [ ] 财税/票据类实体识别（发票号、税号、营业执照号、银行账号）
- [ ] 上下文型实体识别（姓名、机构名、详细地址）——基于关键词锚点 + 内置词典，输出候选待确认
- [ ] 业务敏感字段识别（金额、合同编号、项目代号、内部工号）
- [ ] 分级置信度处置策略：高置信度直接脱敏，低置信度标为待确认候选
- [ ] 识别引擎输出精确字符位置（支持部分掩码所需的偏移量级定位）
- [ ] 识别规则可配置、可扩展（用户可自行增删规则条目）
- [ ] Excel 文档支持（`.xlsx` / `.xls`）：全表散点扫描
- [ ] Excel 列级智能升级：识别出整列同类型时按列批量处理
- [ ] 独立图片文件支持（JPG / PNG 等，走 OCR 路径）
- [ ] 部分掩码脱敏方式（如 `110101********1234`），按实体类型定制掩码规则
- [ ] 基于真实文档的识别准确率回归验证（召回率/误报率基线）

### Out of Scope

- **云端 LLM API 做敏感信息判断** — 脱敏工具把原文传出去与产品初衷根本矛盾；零网络依赖是产品底线
- **本地 NER 深度学习模型** — 会显著增大打包体积与启动开销，规则引擎优先；若规则路线在姓名/机构识别上确实撞墙，再单独立项评估
- **CSV 格式支持** — 本轮未选择，可后续按需追加
- **PowerPoint (.pptx) 支持** — 本轮未选择，可后续按需追加
- **main.py 单体拆分重构** — 与本轮功能目标正交；新增共享逻辑一律放进 `privacyguard/`，避免债务扩大，但不主动重构存量
- **切换到 `privacyguard/utils/config.py` 的 ConfigManager** — 当前运行时配置路径是 `main.py` 的 `SimpleConfig`，本轮不做迁移
- **v38 UI 抛光与批量每文件规则映射** — 原路线图上的方向，本轮让位给识别准确率这一更紧迫的痛点

## Context

**当前代码库状态**（详见 `.planning/codebase/`）：

- `main.py` 约 12.6k 行，仍是活跃的单体运行时入口；`privacyguard/` 子包已承载部分抽离的共享模块与工作器，但迁移未完成
- 技术栈：Python 3.12 / PyQt6 6.10.2 + QtWebEngine；文档链 PyMuPDF + python-docx + mammoth；图像链 RapidOCR + ONNXRuntime + OpenCV
- 版本号唯一来源 `version.txt`；配置为 `config.json` + `main.py` 中的 `SimpleConfig`
- OCR 必须保持懒加载，`RapidOCR` 只在实际执行 OCR 时初始化，不得在包 `__init__.py` 中 eager import
- 测试基线：unittest 79/79 通过
- 已知技术债：单体 main.py、双配置路径并存、打包易出现模块导入回归（参考 `rollback_journal.md` 的 `cp30`）

**问题来源：**

用户实际使用中最痛的不是 OCR 认不出字（OCR 层表现可接受），而是**字认出来了但系统不知道它是敏感信息** —— 现有流程依赖用户手输关键词或正则，想漏一个就漏一个。脱敏工具漏一项即失效，因此这是当前优先级最高的缺口。

**验证条件：** 用户手上有真实文档可用于验证识别准确率，不必依赖合成样本。

## Constraints

- **Security**: 零网络依赖，识别全程在本地完成 — 脱敏工具外传原文自相矛盾，这是产品底线
- **Tech stack**: 纯本地规则引擎（正则 + 校验位 + 上下文关键词 + 内置词典） — 可解释、无额外依赖、速度快、打包体积可控
- **Compatibility**: 不得破坏现有 PDF / Word 脱敏路径与 79/79 测试基线 — 存量能力是用户已依赖的价值
- **Architecture**: 新增共享逻辑必须放入 `privacyguard/`，不得在 `main.py` 再写一份实现 — v37.7.6 已完成重复实现收敛，不能回潮
- **Performance**: OCR 与识别引擎保持懒加载，不得在包导入期初始化 — 影响应用启动速度与打包正确性
- **Packaging**: 任何新增模块必须同步验证 Windows / macOS PyInstaller 打包 — 历史上出现过 `privacyguard.utils.security` 导入失败回归

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 本轮聚焦识别准确率，而非 v38 UI 抛光 | 漏识别直接导致工具失效，是最高优先级痛点 | — Pending |
| 识别引擎走纯本地规则路线，不接云端 LLM | 脱敏工具外传原文与产品初衷矛盾；零网络依赖是底线 | — Pending |
| 分级置信度：高置信度直接脱敏，低置信度待确认 | 号码类有校验位可靠，姓名/机构类无固定格式必须人工兜底 | — Pending |
| Excel 采用"全表扫描 + 列级智能升级"混合策略 | 表格既有散点敏感信息，也有整列同类型场景，单一策略覆盖不全 | — Pending |
| 表格脱敏采用部分掩码而非整体遮蔽 | 保留格式可读性，便于核对；同时要求识别引擎输出精确字符偏移 | — Pending |
| 暂不引入本地 NER 模型 | 打包体积与启动开销代价高；先验证规则路线能走多远 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-10 after initialization*
