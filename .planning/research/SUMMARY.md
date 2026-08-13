# Project Research Summary

**Project:** PrivacyGuard 脱敏卫士（v37.7.6 → v38.x）
**Domain:** 纯本地桌面端文档脱敏工具（Python + PyQt6），从"用户告诉工具要脱什么"转向"工具自己看出该脱什么"
**Researched:** 2026-08-10
**Confidence:** HIGH（中文 PII 校验算法、PyMuPDF true redaction API、openpyxl 能力）/ MEDIUM（PyPI 具体 patch 版本号、企业 DLP 详细 UX）

## Executive Summary

PrivacyGuard 当前已稳定支撑 PDF（文字型/图片型/混合型）与 Word（智能扫描 + 手动 + 双栏对比）的脱敏，但**痛点不在 OCR 识别文字，而在系统不知道哪些文字是敏感信息**——漏一项即工具失效。本轮目标是嵌入**纯本地的中文 PII 自动识别引擎**，并把格式支持扩展到 Excel 与独立图片文件。

行业最佳实践收敛为一条明确路径：**两阶段 Mark → Apply 工作流**（Acrobat / Purview / pdfSweep 同款）+ **三级置信度处置**（HIGH 自动 / MEDIUM+LOW review queue）+ **中文 PII 校验位精度**（身份证 GB 11643 mod-11-2、银行卡 Luhn、统一社会信用代码 GB 32100 mod-31-3、手机号段号白名单）。云端 LLM 与本地大型 NER 模型被明确排除——前者破坏"零网络"产品底线，后者使打包体积与启动开销失控。

技术决策上**不走 Presidio / spaCy**：bundle weight（~900 MB 模型）+ 中文支持薄弱 + 我们要的是"字典+校验位+上下文锚点"而非 NER。Excel 走 `openpyxl`（唯一能 round-trip 保留公式/样式的库）；图片文件复用现有 RapidOCR + Pillow 链路；所有新逻辑放进 `privacyguard/`，避免 v37.7.6 已收敛掉的重复实现回潮。

最高风险是**假脱敏（fake redaction）**——黑框覆盖但底层文本仍可复制粘贴，这是脱敏工具的灾难性失败。规避路径已明确：PDF 必须走 `add_redact_annot + apply_redactions(text=True, images=REMOVE, graphics=REMOVE, garbage=4)`，且**每个格式的 Redactor 都要有"reverse-test"断言**（脱敏后反向提取验证原文不存在）。其他高优风险包括 Excel 11 个隐藏数据通道、身份证校验位算法细节（含 X 大小写）、手机号段号白名单维护、银行卡 Luhn 误杀业务号、OCR 字符混淆（0/O、1/l、全角半角）、跨边界（换行/cell）切断实体、跨文档部分掩码不一致、PyInstaller 新增数据文件导入回归（cp30 历史教训）、大文档阻塞 Qt 主线程、测试语料夹带真实 PII 变仓库为二次泄漏源。

## Key Findings

### Recommended Stack

**核心增量**：仅增加 1 个必选 PyPI 依赖（`openpyxl>=3.1.5,<3.2`）+ 1 个可选依赖（`xlrd==2.0.1` 仅当承诺 `.xls` 支持），其余能力全部 in-tree 实现。**关键决策**：自研 PII 引擎（regex + checksum + dictionary + context）拒绝 Presidio。

**Core technologies:**
- **openpyxl** — Excel `.xlsx` 读写；唯一能 round-trip 保留公式/样式/合并/条件格式的库；纯 Python，PyInstaller 已有官方 hook — 推荐
- **自研 PII 引擎**（`privacyguard/pii/`）— regex + 校验位 + 词典 + 上下文；体积 <50 KB Python 代码；vs Presidio 节省 ~900 MB — 推荐
- **自研校验位模块**（`privacyguard/pii/validators/`）— GB 11643 mod-11-2（身份证）/ Luhn（银行卡）/ GB 32100 mod-31-3（统一社会信用代码）；每个 ~30 行；替代 `id-validator` PyPI 单维护者包 — 推荐
- **自研词典 JSON**（`privacyguard/pii/dictionaries/`）— 百家姓、高频名、行政区划、机构关键词、上下文锚点；~260 KB 静态 JSON 烤进包 — 推荐
- **xlrd==2.0.1**（可选）— 遗留 `.xls` BIFF 读取；项目已停维护，仅在承诺 `.xls` 支持时引入 — 可选
- **Pillow + RapidOCR（已存在）** — 独立图片文件 OCR + EXIF 清除 + burn-in 验证 — 复用

**Bundle 影响：** ~4-5 MB 增量。无新原生依赖，无新模型文件，PyInstaller 流程仅需新增 `datas=[...]` 声明词典 JSON。

### Expected Features

**Must have (P1 表 stakes):**
- 号码类高置信度识别（身份证 mod11、手机号段号白名单、银行卡 Luhn、邮箱、URL、IPv4）— 漏一项即工具失效
- **PyMuPDF true redaction 包装**（`add_redact_annot + apply_redactions`，**禁止** `draw_rect`）— 假脱敏是行业头号灾难
- **部分掩码按实体类型定制**（身份证 `110101********1234` / 手机号 `138****5678` / 银行卡 `6225 **** **** 1234` / 邮箱 `z****@qq.com` / 姓名 `张*`）— 中文行业默认格式
- 两级候选列表 UI（HIGH 自动进脱敏；MEDIUM/LOW 进 review queue）— 行业标准 Mark → Apply 流程
- 假阳性控制：按实体类型开关 + 单实例忽略 + 文档级白名单 — 用户信任基础
- PDF 元数据清除（`set_metadata({})` + `garbage=4`）+ 文档属性扫描
- 单文件脱敏报告（JSON：源文件、实体清单含位置/类型/置信度/处置、规则版本、时间戳）

**Should have (P2 差异化):**
- 上下文型实体识别（姓名/机构/地址）— 词典 + 上下文锚点；LOW 候选
- Excel 全表散点扫描 + 11 个隐藏数据通道（含 hidden sheet / 批注 / definedNames / 共享字符串 / pivotCache / docProps / revisions / autoFilter / 数据验证 / 条件格式 / 外部链接）
- Excel 列名驱动升级（"身份证号"列整列同类）
- Excel 公式 + 样式 + 合并 + 命名区域保留（openpyxl `cell.value = masked`，`data_only=False`）
- Word OCR 路径接入识别结果
- 独立图片文件 OCR + EXIF 清除 + re-OCR 验证

**Defer (v2+ / Out of Scope):**
- 批量脱敏报告（多文件 CSV/Excel 汇总）
- 规则版本快照 + 完整操作日志（合规深化）
- 可点击报告跳原文位置（UI 投入大）
- 本地 NER 模型（`zh_core_web_trf` ~400 MB）— 仅在规则路线撞墙时单独立项评估
- CSV / PowerPoint 支持 — 本轮不选
- 哈希 / 令牌化脱敏 — 与"纯本地"约束冲突
- 合成替换（fake value）— 用户拿到的是真实文件不是测试样本

### Architecture Approach

**核心模式**：**Detection is format-independent** — 一份 `PIIHit` 数据结构贯穿 PDF/Word/Excel/Image 四个格式的识别→脱敏→审计全链路；格式分支只在 `DocumentAdapter.apply_redactions` 边界发生，引擎本身不知道也不需要知道格式。引擎是**纯 Python 库**（无 Qt、无线程、无信号），所有 worker 包装层负责把引擎结果送进现有 `page_data[page]["pii"]` / `word_data[key]["pii"]` 新槽位（**不是新数据结构，是现有 dict 增加 key**——守住 v37.7.6 收敛原则）。

**Major components:**
1. **`privacyguard/pii/`（新）** — 纯 Python 检测引擎：`PIIHit` / `DocumentLocation` / `ConfidenceTier` 数据类型；Recognizer ABC（Regex/Checksum/Dictionary/ContextAware）；validators（id_card / bank_card / uscc）；dictionaries JSON；Engine 编排器；overlap 去重；confidence 三档映射；mask 按实体定制掩码；report JSON 输出
2. **`privacyguard/formats/`（新）** — `DocumentAdapter` ABC + 四个 adapter：`pdf_adapter`（包装现有 `text_pdf.py` + `mixed_pdf.py`，apply 走 PyMuPDF true redaction）、`word_adapter`（包装现有 word worker）、`excel_adapter`（openpyxl 全表+11 通道）、`image_adapter`（Pillow burn-in + re-OCR 验证）
3. **`privacyguard/workers/`（扩展）** — 新增 `detection_worker.py` / `excel_worker.py` / `image_worker.py`；现有 `ocr_worker.py` / `word_worker.py` 扩展 `Engine.detect(unit)` 调用并 emit `hit_signal`
4. **`privacyguard/ocr/image_ocr.py`（新）** — Pillow → RapidOCR 包装，**RapidOCR 必须在函数体内 import**（守住 lazy-loading 约束）
5. **`main.py`（最小改动）** — 加 state attr（`excel_data` / `image_data` / `_pii_data_lock`）+ 新增 `CandidateDialog` + Settings "识别规则" 标签页 + worker 接线；**不加检测逻辑**（收敛原则）

**关键数据结构：** `PIIHit`（frozen dataclass）= `entity_type` + `DocumentLocation` + `text` + `confidence`(HIGH/MEDIUM/LOW enum) + `source` + `validator_passed` + `suggested_mask` + `normalized`。`DocumentLocation` 用单一 dataclass 承载四格式定位（`page_index` / `data_key` / `sheet_name`+`cell_coord` / `rect`），只填对应 `DocKind` 的字段。

### Critical Pitfalls

1. **假脱敏（Fake Redaction）** — 头号灾难，黑框覆盖但底层文本仍可 `pdftotext` 还原；Facebook 2022 / UK ICO 2021 / Ghislaine Maxwell 2021 都有真实事故；**规避**：PDF 必须 `add_redact_annot + apply_redactions`，且**每格式都有 reverse-test 断言**（脱敏后反向提取验证原文不存在）
2. **Excel 11 个隐藏数据通道漏扫** — 隐藏 sheet / 隐藏行列 / 批注 / definedNames / sharedStrings / 公式 / pivotCache / externalLinks / docProps / revisions / autoFilter；**规避**：建立"xlsx 11 通道扫描器"，每个通道独立测试；扫描阶段输出全量命中（含来源 `source: hidden_sheet|comment|defined_name|...`）
3. **身份证校验位算法 + X 大小写陷阱** — 权重 `[7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]` 必须写对；末位合法值仅大写 `X`，OCR 输出小写 `x` 需标 ambiguous；15 位旧格式需升级到 18 位再校验；**规避**：≥20 条断言样本（含 X、小写 x、15/18 位、边界生日）；mod 11 通过后还应校验 `MMDD` 日期合法性
4. **手机号段号静态化导致新号段漏判或物联网号误判** — 真正的陷阱是反过来：14X 物联网段（140/141/144/146/148/149）不应识别为个人手机号；**规避**：维护双白名单（个人号段 110-199）+ 排除列表（14X 物联网段、1740/1749 卫星段、部分虚拟运营商段）
5. **银行卡 Luhn 通过即信任 → 订单号/ISBN/机票号误杀** — 单维度 Luhn 缺上下文信号；**规避**：多信号联合 `confidence = w1*Luhn + w2*context_keyword + w3*BIN_prefix + w4*length_in_range`；维护 BIN 前缀库（62 银联 / 4 VISA / 5 MC / 35 JCB / 6 Discover）；分级处置
6. **跨边界实体被切断（line break / page break / cell）** — 身份证被表格换行拆成 `11010119900307\n8811`、银行卡 Excel cell 切碎；**规避**：引擎设计阶段就支持"跨行拼接匹配"模式（先 flatten `\s　` 再 regex，再把 flat offset 映回原始 offset）
7. **部分掩码一致性 → 跨文档关联攻击** — 同实体两份文档保留不同片段即可拼接还原；身份证前 6 位是行政区划、7-14 位是出生日期，本身就是准标识符；**规避**：引擎内置 `entity_normalizer`（同实体多实例同掩码）
8. **PyInstaller 新增数据文件/模块导入回归** — `datas` 未声明 → `FileNotFoundError`；`hiddenimports` 未声明 → `ModuleNotFoundError`；历史上 `privacyguard.utils.security` 导入失败（cp30）；**规避**：每阶段收尾前 Windows + macOS 双平台真机打包验证，不能只信 `compileall`
9. **大文档扫描阻塞 Qt 主线程 + ReDoS 雪崩** — 500 页 PDF 同步扫 → UI 卡死；嵌套量词正则 → 指数回溯；**规避**：所有扫描走 `QThread` worker；正则带 timeout（Python 3.11+ `re.finditer(..., timeout=0.5)`）；性能 smoke test 500 页 + 100 sheet
10. **测试语料里放真实个人数据 → 仓库变成数据泄漏源** — git 历史永久保留；**规避**：`tests/fixtures/fake_pii.py` 用 Faker 生成（Faker 输出不过 Luhn，需包一层"生成+校验"循环）；`.gitignore` 加 `tests/samples/real_*`
11. **全角/半角数字 + OCR 字符混淆（0/O、1/l/I、8/B）导致校验失败** — **规避**：所有输入经 `normalize_digits` 预处理（全角→半角 + 移除分隔符）；OCR 低置信度的 `OolI` 字符标 ambiguous 不直接当数字
12. **上下文型实体（姓名/机构/地址）缺乏锚点 → 大量假阳性** — **规避**：强制要求锚点关键词（`先生/女士` / `有限公司/集团/银行` / `省/市/区/县/路/街/号`）；内置词典 + 双向扫描

## Implications for Roadmap

建议 **5 个 Phase**，以"基础引擎先立 → 复用现有 PDF 路径 → 三个新格式适配器并行 → UI/审计/打包收尾"为依赖顺序。

### Phase 1：PII 引擎基础（纯 Python，无 Qt，无格式 I/O）

**Rationale：** 识别引擎的基石，所有格式适配器都依赖它。先立引擎能让后续 Phase 并行推进而无须回头改基础类型；纯 Python 无 UI 反馈快、blast radius 低。
**Delivers：** `privacyguard/pii/` 子包（types/entities/recognizers/validators/dictionaries/engine/confidence/overlap/mask/report）；自研校验位算法；自研词典 JSON（~260 KB）；HIGH/MEDIUM/LOW 三档置信度；按实体类型定制的部分掩码；JSON RedactionReport 输出。
**Avoids：** Pitfall 3/4/5/6/7/9/10/11/12。

### Phase 2：PDF 集成（包装现有 OCR 路径，最便宜端到端）

**Rationale：** PDF 已有 `text_pdf.py` + `mixed_pdf.py` + `_ModularOCRWorker`。新增 `PdfAdapter` 包装仅 ~150 行；用最小改动验证整条"识别→脱敏→审计"链路，作为 Phase 3 的参考实现。
**Delivers：** `privacyguard/formats/base.py`（`DocumentAdapter` ABC）+ `pdf_adapter.py`（PyMuPDF true redaction）；扩展 `_ModularOCRWorker.run`；`page_data[page]["pii"]` 新槽位；theme 三色 token。
**Avoids：** Pitfall 1（PDF 假脱敏 → reverse-test 断言 + 测试断言禁止 `draw_rect`）。

### Phase 3：Word + Excel + Image 三 Adapter 并行（C1/C2/C3）

**Rationale：** 三轨互相独立，可任意顺序开发。Word 最小增量（~250 行），Excel 是用户最期待的新能力（~600-800 行），Image 是 OCR 链路自然延伸（~200 行）。
**Delivers：** C1 `word_adapter.py` + word_data pii 槽位（不破坏 cp27 增量 DOM patch）；C2 `excel_adapter.py`（11 通道扫描 + openpyxl 全表 + 公式/样式/合并保留 + 列名驱动升级）+ `excel_worker.py` + `openpyxl` 依赖；C3 `image_ocr.py` + `image_adapter.py`（burn-in + re-OCR 验证 + EXIF 清除）。
**Avoids：** C2 → Pitfall 2（11 通道漏扫）；C3 → Pitfall 1（图片假脱敏 → 像素级重绘 + re-OCR）、RapidOCR 顶层 import。

### Phase 4：Apply UX + 审计 + 打包门禁

**Rationale：** Phase 2/3 已能识别 + 真脱敏，但用户还需要"看一遍再确认 + 看到底脱了什么"。UI 集中在此阶段避免每加一个 format 都改 UI。
**Delivers：** `CandidateDialog`（review queue，HIGH auto-apply / MEDIUM+LOW review）+ per-hit override + 按来源/类型筛选；Settings "识别规则" 标签页；`RedactionReport` 接进 apply 阶段；PyInstaller spec 更新 `datas`；Windows + macOS 双平台真机打包验证。
**Avoids：** Pitfall 8（打包回归）、UX pitfalls（100+ 项一次性弹出 → 分页+筛选；高置信度无 undo → 撤销栈）。

### Phase 5（可选 / 后续）：上下文型实体深化 + 批量报告 + 跨文档一致性

**Rationale：** 上下文型识别依赖 Phase 1 号码类识别产出的 anchor 作种子；假阳性风险最高；需要更长真实文档回归。
**Delivers：** 词典+锚点的姓名/机构/地址识别；业务敏感字段（金额/合同编号/项目代号/工号）；批量脱敏 CSV 汇总；跨文档掩码一致性；行政区划词典打包策略评估。

### Phase Ordering Rationale

1. **依赖关系**：Phase 1 的 `Engine` + `PIIHit` 是所有 adapter 的输入；Phase 2 的 `DocumentAdapter` ABC 是 Phase 3 的样板；Phase 4 至少需要一个 adapter 落地才有 UI 闭环。
2. **架构收敛**：Phase 1 纯 Python 可独立单测；Phase 2-3 每个 adapter 遵循"extract_text_units + apply_redactions + reverse-test"三段式；Phase 4 UI 集中。
3. **风险分布**：Phase 1 最低；Phase 2 集中在 PyMuPDF 误用（规避路径清晰）；Phase 3 Excel 最高但 11 通道 schema 已明确；Phase 4 在打包回归（cp30 模板就位）。
4. **避免回潮**：每 Phase 收尾前双平台真机打包 + `test_convergence.py` 断言 `main.py` 不顶层导入 `privacyguard.pii.*`。

### Research Flags

**Needs `--research-phase`：**
- **Phase 3 C2（Excel）** — openpyxl 11 通道各 API 细节（`comments` / `defined_names` / `conditional_formatting` / `data_validations` / `external_links` / `pivotCache` / `revisions`）；列名驱动升级的"列头→实体类型"映射 schema
- **Phase 4（UI）** — PyQt6 review queue dialog 模式（分页 + 实时过滤 + 多选 + 信号槽）；Settings 动态 schema 与现有 config.json 兼容性

**Standard patterns（可跳过 research-phase）：**
- Phase 1 — 校验位算法公开（GB 11643 / GB 32100 / ISO 7812）、掩码格式行业默认、词典来源公开、架构借鉴 Presidio
- Phase 2 — 包装现有代码 ~150 行；PyMuPDF API 成熟且有公开事故案例对照
- Phase 3 C1（Word）— 最小增量，现有 worker 有清晰扩展点
- Phase 3 C3（Image）— 复用 RapidOCR + Pillow；re-OCR 验证模式从 PDF 平移
- Phase 5 — 词典+锚点方法本身成熟

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | openpyxl 是唯一满足 round-trip+formula+style 的库；in-house 引擎 vs Presidio 决策基于公开 bundle weight 与中文支持现状；自研校验位有公开标准文档 |
| Features | **MEDIUM-HIGH** | 中文 PII 校验位 + 行业掩码格式 + Mark/Apply 工作流为 HIGH（多源验证）；企业 DLP 具体 UX 细节为 MEDIUM（二手摘要） |
| Architecture | **HIGH** | 现有代码库已完整映射；Engine/Adapter 拆分直接借鉴 Presidio 公开架构；`DocumentLocation` 四格式最小公分母已穷举 |
| Pitfalls | **MEDIUM** | 格式校验算法 HIGH；社区共识（假脱敏 + Excel 11 通道 + ReDoS）HIGH；部分掩码重识别风险 MEDIUM（单源） |

**Overall confidence: HIGH** — 核心结论均有多源验证，可直接进入 phase 规划与执行。

### Gaps to Address

1. **MIIT 最新手机号段白名单完备性** — 166/198/199、190/192/196/197、虚拟运营商段、14X 物联网段（应排除）需权威清单交叉验证（Phase 1 前）
2. **行政区划词典打包策略** — ~700K 全集 vs 3500 条省市区分集取舍；Phase 1 仅需省市级，Phase 5 才需完整集
3. **全电发票 20 位号码格式** — 新版格式与正则确认（Phase 1 末）
4. **词典文件法律审查** — `Chinese-Names-Corpus` / `sysloser/adcode` LICENSE 兼容性（Phase 1 前）
5. **`.xls` 真实用户量调研** — 决定加 `xlrd` 还是统一走 LibreOffice 转换（Phase 3 C2 前）
6. **现有 `page_data` / `word_data` 扩展 `pii` 槽位的 79/79 基线回归** — Phase 1 实施时确认
7. **`confidence.py` 是否暴露原始 0.0–1.0 score** — UX 决策，Phase 4 定
8. **`RedactionReport` 是否捆绑原文件 SHA-256** — 合规价值 vs IO 成本，Phase 4 定

## Sources

### Primary（HIGH confidence）

- **PyMuPDF 官方文档**（pymupdf.io/landing-redact）— `add_redaction` / `apply_redactions(keep_text=False)` 真删除语义；GitHub issues #3257、#3863、#3375
- **openpyxl 官方文档**（openpyxl.readthedocs.io）— read/write with formatting preservation
- **GB 11643-1999 居民身份证** — 18 位 mod-11-2 算法 + 权重 + parity 表
- **GB 32100-2015 统一社会信用代码** — ISO 7064 MOD 31-3
- **PCI DSS v4.0** — 银行卡 Luhn + 16-19 位 + BIN 段
- **工信部公开段号分配**（2017-08 公告 166/198/199；2019-12 公告 190/192/196/197）
- **Microsoft Presidio 架构文档** — Engine / Recognizer / Registry / Anonymizer 结构借鉴
- **Microsoft Learn** — DLP 置信度分级、Excel 隐藏数据面、`remove-personal-info-from-workbook`
- **Adobe Acrobat Redaction** — Mark → Apply 两阶段工作流 + GDPR Art.30 / HIPAA §164.312(b)
- **pyinstaller-hooks-contrib hook-openpyxl.py** — PyInstaller 集成已验证
- **Python 3.11+ `re` 文档** — `re.finditer(..., timeout=)`

### Secondary（MEDIUM confidence）

- Presidio 中文 recognizer 社区实现（jokamjohn/id-validator、treasun1229/presidio_zh）
- Adobe / Purview / pdfSweep 具体 UX 细节（二手摘要）
- Wang et al., IEEE TrustCom 2023 — 部分掩码 PII 重识别风险
- OWASP ReDoS Guide + Semgrep 博客
- exceldemy.com/excel-hidden-data-leak — Excel 11 隐藏通道清单
- 中文 masking 行业惯例（CSDN / SegmentFault / 阿里云 / GB/T 35273-2020 间接引用）

### Tertiary（LOW confidence — 实施前再验证）

- Faker `zh_CN` locale — 假数据生成需包"生成+校验"循环
- `cpca`（chinese_province_city_area_mapper）— 行政区划词典
- Pillow 默认 strip EXIF；`piexif` GPS 选择性清除
- GitHub `sysloser/adcode`（2024-11-25）— 需法律审查
- GitHub `HALOSTAR/chinese_surnames` — 需验证内容质量与 LICENSE

---

*Research completed: 2026-08-10*
*Ready for roadmap: yes — 5 phases suggested, Phase 3 split into C1/C2/C3 parallel tracks, Phase 5 optional/deferred*
