# Requirements: PrivacyGuard 脱敏卫士 (v38.x)

**Defined:** 2026-08-10
**Core Value:** 打开文档就自动列出所有敏感项，用户不用再手输关键词。

## v1 Requirements

### 识别引擎核心 (ENGINE)

- [x] **ENGINE-01**: 系统在文档打开后自动扫描全文并输出敏感项候选列表，无需用户预先输入关键词
- [x] **ENGINE-02**: 每条识别结果携带实体类型、精确字符起止位置、置信度档位、来源与建议掩码，供部分掩码与审计复用
- [x] **ENGINE-03**: 系统按 HIGH / MEDIUM / LOW 三档给识别结果评级，HIGH 档直接脱敏，MEDIUM 与 LOW 档进入待确认列表
- [x] **ENGINE-04**: 系统对同一实体的多次出现应用一致的掩码结果，避免跨实例拼接还原
- [x] **ENGINE-05**: 系统在匹配前统一归一化输入文本（全角转半角、剔除空格与分隔符），并把匹配位置映射回原始偏移
- [x] **ENGINE-06**: 系统能识别被换行、分栏或单元格边界切断的实体
- [x] **ENGINE-07**: 正则匹配设置执行超时保护，避免异常输入导致界面无响应
- [x] **ENGINE-08**: 识别引擎为纯本地执行，运行期无任何网络请求

### 号码类实体识别 (NUM)

- [x] **NUM-01**: 系统能识别 18 位与 15 位居民身份证号并通过 GB 11643 mod-11-2 校验位验证
- [x] **NUM-02**: 身份证识别正确处理末位大写 X，并对 OCR 输出的小写 x 标记为可疑而非直接判负
- [x] **NUM-03**: 系统能识别中国大陆手机号，依据号段白名单判定，并排除物联网与卫星专用号段
- [ ] **NUM-04**: 系统能识别银行卡号并通过 Luhn 校验，结合 BIN 前缀与上下文关键词综合定档，避免误判订单号
- [ ] **NUM-05**: 系统能识别电子邮箱地址

### 财税票据实体识别 (FIN)

- [ ] **FIN-01**: 系统能识别统一社会信用代码并通过 GB 32100 mod-31-3 校验
- [ ] **FIN-02**: 系统能识别增值税发票号码（含全电发票新版格式）
- [ ] **FIN-03**: 系统能识别纳税人识别号
- [ ] **FIN-04**: 系统能识别银行账号

### 上下文型实体识别 (CTX)

- [ ] **CTX-01**: 系统能基于姓氏词典与上下文锚点（先生/女士/姓名字段标签）识别中文人名，输出为待确认候选
- [ ] **CTX-02**: 系统能基于机构后缀词典（有限公司/集团/银行/医院等）识别机构名称，输出为待确认候选
- [ ] **CTX-03**: 系统能基于行政区划词典与地址成分词（省/市/区/县/路/街/号）识别详细地址，输出为待确认候选
- [ ] **CTX-04**: 系统能识别业务敏感字段（金额、合同编号、项目代号、内部工号），输出为待确认候选
- [ ] **CTX-05**: 上下文型识别强制要求锚点命中，无锚点的孤立短语不产生候选

### 脱敏执行与安全底线 (SAFE)

- [x] **SAFE-01**: PDF 脱敏通过 PyMuPDF 真删除流程执行，脱敏后原文本不可通过文本提取还原
- [x] **SAFE-02**: 每种格式的脱敏实现都有反向提取测试，断言脱敏后原始敏感内容在产物中不存在
- [ ] **SAFE-03**: 系统在导出时清除文档元数据（PDF 文档信息、Office 文档属性）
- [ ] **SAFE-04**: 系统在导出图片时清除 EXIF 信息（含 GPS 与设备标识）
- [ ] **SAFE-05**: 图片脱敏采用像素级重绘，并在导出后重新 OCR 验证敏感文字确已消失
- [ ] **SAFE-06**: Excel 脱敏覆盖隐藏工作表、隐藏行列、批注、定义名称、共享字符串、公式串、透视缓存、外部链接、文档属性、修订记录、自动筛选缓存等隐藏泄漏通道

### 掩码策略 (MASK)

- [ ] **MASK-01**: 系统支持部分掩码，按实体类型套用各自的保留规则（身份证保留前 6 后 4、手机号保留前 3 后 4、银行卡保留前 6 后 4、邮箱保留首字符与域名、姓名仅保留姓）
- [x] **MASK-02**: 用户可在部分掩码与完全遮蔽之间选择处置方式

### 格式支持 (FMT)

- [x] **FMT-01**: PDF 文字层与 OCR 路径接入识别引擎，识别结果并入现有页面命中数据而非另起结构
- [x] **FMT-02**: Word 处理路径接入识别引擎，识别候选在双栏对比预览中高亮
- [ ] **FMT-03**: 用户可打开 `.xlsx` 工作簿并对全表执行敏感信息扫描
- [ ] **FMT-04**: 系统在识别出整列同类型实体时提示按列批量处置
- [ ] **FMT-05**: Excel 脱敏写回后保留公式、单元格样式、合并区域与命名区域
- [ ] **FMT-06**: 用户可打开独立图片文件（JPG / PNG）并通过 OCR 执行敏感信息识别与脱敏

### 审阅交互与误报控制 (UX)

- [ ] **UX-01**: 用户可在候选审阅列表中查看所有待确认识别项，并逐条决定是否脱敏
- [ ] **UX-02**: 候选列表支持按实体类型与来源筛选，且在候选数量较多时分页展示
- [ ] **UX-03**: 用户可按实体类型开关识别能力
- [ ] **UX-04**: 用户可忽略单条识别结果而不影响同类型其他结果
- [ ] **UX-05**: 用户可维护文档级白名单，命中白名单的内容不再产生候选
- [ ] **UX-06**: 用户可撤销已自动应用的高置信度脱敏
- [ ] **UX-07**: 用户可在设置面板中增删改识别规则条目

### 审计与工程保障 (OPS)

- [ ] **OPS-01**: 每次脱敏生成单文件 JSON 报告，记录源文件、实体清单（类型/位置/置信度/处置方式）、规则版本与时间戳
- [ ] **OPS-02**: 所有扫描与脱敏在工作线程中执行并上报进度，界面在处理大文档时保持响应
- [x] **OPS-03**: 识别引擎与词典数据保持懒加载，包导入期不初始化 OCR 引擎
- [x] **OPS-04**: 新增模块与词典数据文件在 Windows 与 macOS 打包产物中均可正常加载
- [ ] **OPS-05**: 测试语料使用合成数据生成，仓库不存放真实个人信息
- [ ] **OPS-06**: 基于真实文档建立识别准确率基线（召回率与误报率），并纳入回归验证
- [x] **OPS-07**: 现有 79/79 测试基线在改动后保持通过

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### 批量与报告深化 (BATCH)

- **BATCH-01**: 多文件批量脱敏汇总报告（CSV / Excel）
- **BATCH-02**: 批次内跨文档掩码一致性策略
- **BATCH-03**: 规则版本快照与完整操作日志
- **BATCH-04**: 报告条目可点击跳转原文位置

### 格式扩展 (EXT)

- **EXT-01**: 遗留 `.xls` 格式支持（依赖用户量调研结果决定引入 xlrd 或统一走 LibreOffice 转换）
- **EXT-02**: CSV 格式支持
- **EXT-03**: PowerPoint (.pptx) 格式支持

### 识别能力深化 (ADV)

- **ADV-01**: 完整行政区划词典（约 70 万条目）支持精细地址识别
- **ADV-02**: 用户自定义词典导入

## Out of Scope

| Feature | Reason |
|---------|--------|
| 云端 LLM API 做敏感信息判断 | 脱敏工具把原文传出去与产品初衷根本矛盾；零网络依赖是产品底线 |
| 本地 NER 深度学习模型 | 显著增大打包体积与启动开销；先验证规则路线能走多远，撞墙后再单独立项 |
| 哈希 / 令牌化脱敏 | 与纯本地单机使用场景不匹配，缺少令牌管理载体 |
| 合成值替换（fake value） | 用户拿到的是真实工作文件而非测试样本，替换成假数据会造成误用 |
| main.py 单体拆分重构 | 与本轮功能目标正交；新增共享逻辑一律进 privacyguard/，但不主动重构存量 |
| 切换到 privacyguard/utils/config.py 的 ConfigManager | 当前运行时配置路径是 main.py 的 SimpleConfig，本轮不做迁移 |
| v38 UI 抛光与批量每文件规则映射 | 原路线图方向，本轮让位给识别准确率这一更紧迫的痛点 |
| 仅绘制黑框而不删除底层内容的"视觉脱敏" | 行业已知灾难性失败模式，明确禁止 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENGINE-01 | Phase 1 | Complete |
| ENGINE-02 | Phase 1 | Complete |
| ENGINE-03 | Phase 1 | Complete |
| ENGINE-04 | Phase 1 | Complete |
| ENGINE-05 | Phase 1 | Complete |
| ENGINE-06 | Phase 1 | Complete |
| ENGINE-07 | Phase 1 | Complete |
| ENGINE-08 | Phase 1 | Complete |
| NUM-01 | Phase 1 | Complete |
| NUM-02 | Phase 1 | Complete |
| NUM-03 | Phase 1 | Complete |
| NUM-04 | Phase 2 | Pending |
| NUM-05 | Phase 2 | Pending |
| FIN-01 | Phase 2 | Pending |
| FIN-02 | Phase 2 | Pending |
| FIN-03 | Phase 2 | Pending |
| FIN-04 | Phase 2 | Pending |
| CTX-01 | Phase 6 | Pending |
| CTX-02 | Phase 6 | Pending |
| CTX-03 | Phase 6 | Pending |
| CTX-04 | Phase 6 | Pending |
| CTX-05 | Phase 6 | Pending |
| SAFE-01 | Phase 1 | Complete |
| SAFE-02 | Phase 1 | Complete |
| SAFE-03 | Phase 2 | Pending |
| SAFE-04 | Phase 5 | Pending |
| SAFE-05 | Phase 5 | Pending |
| SAFE-06 | Phase 4 | Pending |
| MASK-01 | Phase 2 | Pending |
| MASK-02 | Phase 2 | Complete |
| FMT-01 | Phase 1 | Complete |
| FMT-02 | Phase 3 | Complete |
| FMT-03 | Phase 4 | Pending |
| FMT-04 | Phase 4 | Pending |
| FMT-05 | Phase 4 | Pending |
| FMT-06 | Phase 5 | Pending |
| UX-01 | Phase 3 | Pending |
| UX-02 | Phase 3 | Pending |
| UX-03 | Phase 7 | Pending |
| UX-04 | Phase 7 | Pending |
| UX-05 | Phase 7 | Pending |
| UX-06 | Phase 7 | Pending |
| UX-07 | Phase 8 | Pending |
| OPS-01 | Phase 8 | Pending |
| OPS-02 | Phase 8 | Pending |
| OPS-03 | Phase 1 | Complete |
| OPS-04 | Phase 8 | Complete |
| OPS-05 | Phase 4 | Pending |
| OPS-06 | Phase 8 | Pending |
| OPS-07 | Phase 1 | Complete |

**Coverage:**

- v1 requirements: 50 total
- Mapped to phases: 50
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-10*
*Last updated: 2026-08-10 after roadmap creation*
