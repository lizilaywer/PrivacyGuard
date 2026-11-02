# 后续优化路线图（Post-Remediation Roadmap）

最后更新：2026-08-14
当前基线版本：v40.1.5
回归基线：579（全绿；含路径安全 13 项入 CI + 迁移纯函数 19 项）
前置条件：P0–P3 整改计划（见 `PRIORITY_REMEDIATION_PLAN.md`）已全部完成并入库。

---

## 0. 现状基线（撰写本计划时直接核实）

| 维度 | 现状 | 结论 |
|------|------|------|
| main.py `print(` 残留 | 0 处 | P0-3 日志框架迁移彻底完成 |
| 高亮来源过滤（rule/manual/ocr） | `helpers_word_preview.py` 提供 + main.py:658 + word_preview_mixin.py 接入 | ✅ 已落地，AGENTS.md 已同步 |
| helpers.py 域拆分 | 5 个域模块（原垫片已删，消费方按域导入） | ✅ 已完成 |
| ocr_worker.py | 1163 行 | 超过千行阈值，cp96 已外提印章/签名算法，仍有拆分空间 |
| settings_dialog.py | 1046 行 | 略超千行，cp97 已拆 Layout/Actions Mixin |
| main.py | 9787 行（Python 计数；v40.0.0 起因提取/截去/书签增长 ~500 行） | 行数稳定，按版本节奏渐进优化 |
| docs/guides/ | USER_GUIDE（终端用户）+ CLAUDE_CODE_TIPS（agent）+ TESTING_GUIDE（开发） | ✅ 已补全 |
| per-file rule mapping | 未实现 | AGENTS.md 默认方向，待开发 |
| batch rule-set templates | 未实现 | AGENTS.md 默认方向，待开发 |
| 类型注解 | 新拆分 helpers_*.py 已有；老模块不全 | 渐进补齐空间 |
| 覆盖率统计 | 无 | 未接入 coverage |

**核心判断**：项目已过"修高危/拆大文件"阶段，进入"补文档/收敛结构/做功能增量/工程化"阶段。本计划不追求大拆分，按版本节奏渐进优化。

---

## 1. 资源与节奏假设

- **资源**：单人开发（用户本人，执业律师 + GUI 开发者），AI 辅助编码与审查。
- **可投入节奏**：每周约 6–10 小时。
- **工时单位**：本计划用"工时（h）"估算，1 人天 = 6h。
- **执行原则**：每个任务独立成 commit，遵循"执行 → 回归 510 → ruff → 复盘 → 提交"闭环；新功能按 AGENTS.md 铁律作为独立模块开发，禁止往 main.py 堆方法。

---

## 2. 优先级总览

| 优先级 | 主题 | 任务数 | 合计工时 | 风险 |
|--------|------|--------|----------|------|
| **P0** | 文档与可维护性基础 | 3 | ~11h | 低 |
| **P1** | 代码结构继续收敛 | 3 | ~13h + 持续 | 中 |
| **P2** | 功能增量（AGENTS.md 默认方向） | 2 | ~16h | 中 |
| **P3** | 工程化与质量基线 | 4 | ~16h + 可选 20h | 低–中 |

**推荐顺序**：P0 全部 → P1-3 → P1-1 → P2-1 → P2-2 → P1-2（持续）→ P3-1 → P3-2 → P3-3 → P3-4（可选）。

理由：P0 杠杆最高、风险最低，先清文档债与垫片债；P1-3 类型注解为后续 P2 功能开发提供安全网；P2 是用户可感知的功能增量；P3 是工程化长期投资。

---

## 3. P0 — 文档与可维护性基础（低风险高杠杆）

### P0-1 终端用户使用手册补全
- **现状**：`docs/guides/` 含 `USER_GUIDE.md`（终端用户向，cp100 已落地）、`CLAUDE_CODE_TIPS.md`（agent 向）、`TESTING_GUIDE.md`（开发向）。
- **任务**：新建 `docs/guides/USER_GUIDE.md`，覆盖 v37.8.11 全部功能：
  1. 安装与启动（Win/macOS venv、打包版）
  2. PDF 脱敏全流程：规则扫描 / 图片 OCR / 混合 PDF / 手动框 / 整文档定向遮罩 / 印章签名检测
  3. Word 脱敏全流程：规则替换 / 自定义关键词 / 批量替换 / 页眉页脚
  4. 页面视图：多页网格 / Ctrl+滚轮缩放 / 旋转插入删除 / 适合页面
  5. 全文搜索侧栏、撤销重做、会话恢复
  6. 导出加密（AES-256）、脱敏报告
  7. 设置中心、痕迹清理
- **验证**：文档步骤与 v37.8.11 实际 UI/行为逐项对齐；可被非技术用户照做完成一次完整脱敏。
- **工时**：~6h
- **检查点**：cp100

### P0-2 AGENTS.md 开发方向与行数同步
- **现状**：AGENTS.md "Current Development Direction" 仍把"preview highlight filtering by source"列为待办，实际已落地；main.py 行数记 9287，Python 实测 9271，描述陈旧会误导后续 agent。
- **任务**：
  1. 更新 AGENTS.md 默认方向：标记"高亮来源过滤"已完成；保留 per-file rule mapping / batch rule-set templates 为活跃方向。
  2. 同步 main.py 行数（9271，Python 计数；此前 PowerShell Measure-Object 少计为 8420）与拆分记录描述。
  3. 在本路线图与 PRIORITY_REMEDIATION_PLAN 之间建立交叉引用。
- **验证**：AGENTS.md 描述与代码现状逐条一致；CI 版本/文档检查不受影响。
- **工时**：~1h
- **检查点**：cp101

### P0-3 helpers.py 垫片消费方迁移
- **现状**：`helpers.py`（81 行）是再导出垫片，所有消费方仍 `from privacyguard.utils.helpers import X`。垫片长期存在会掩盖真实依赖关系，形成惰性兼容层。
- **任务**：逐消费方迁移到按域直接导入：
  - 第 1 批：`privacyguard/ui/mixins/*`、`privacyguard/ui/widgets.py`、`privacyguard/ui/dialogs/*`
  - 第 2 批：`privacyguard/workers/*`
  - 第 3 批：`main.py`
  - 全部迁移后删除 `helpers.py` 垫片（或保留空壳仅作向后兼容声明）
- **验证**：每批迁移后回归 510 全绿 + ruff 全绿；最终移除垫片后所有 import 正常。
- **风险**：迁移面广但机械，每批可独立验证，风险可控。
- **工时**：~4h（分 3 批）
- **检查点**：cp102

---

## 4. P1 — 代码结构继续收敛（中风险）

### P1-1 ocr_worker.py 进一步拆分评估与落地
- **现状**：1163 行（Python 计数），超过千行阈值。cp96 已外提印章/签名算法到 `ocr/` 模块。剩余可能含 OCR 编排流程 / 信号回调 / 结果聚合与去重。
- **任务**：
  1. 先做拆分评估：识别 OCR 编排、回调、结果聚合三个职责块，判断是否耦合过深不宜物理拆分。
  2. 若可拆：结果聚合/去重纯逻辑抽到 `privacyguard/ocr/result_aggregator.py`；编排流程抽 `OCRPipelineMixin` 或独立 `OCRPipeline` 类（遵循 AGENTS.md 铁律）。
  3. 若耦合过深：仅做内部方法分组与文档化，不强拆。
- **验证**：回归 418，重点验证 `test_mixed_pdf_ocr` / `test_seal_detection` / `test_signature_detection` / `test_pdf_text_hit_dedup`。
- **工时**：~5h
- **检查点**：cp103

### P1-2 main.py 渐进优化（持续，按版本机会）
- **现状**：9271 行（Python 计数）。AGENTS.md 明确"后续不再做物理拆分，按版本节奏渐进优化"。
- **任务**：不做大拆分。按版本机会识别并抽离超 50 行的非 UI 编排逻辑到独立模块（Worker/Mixin/utils）。优先排查 main.py 中是否仍存在"平行算法副本"（P2-2 历史遗留：同类逻辑 main.py 与 privacyguard/* 各一份）。
- **验证**：每次抽离后回归 + compileall + ruff。
- **工时**：持续，按需（不单独计）
- **检查点**：随版本

### P1-3 类型注解补全 + mypy 渐进检查
- **现状**：新拆分 `helpers_*.py` 已有类型注解；老模块（`workers/ocr_worker.py`、`widgets.py`、`main.py`、`ocr/*`）注解不全。
- **任务**：
  1. 给 `privacyguard` 包公开 API 补类型注解（优先 `utils/` + `ocr/`）。
  2. 新增 `mypy.ini` 或 `pyproject.toml` mypy 配置，范围先限 `privacyguard/utils/` + `privacyguard/ocr/`，strict 渐进。
  3. 修复 mypy 报错。
- **验证**：`mypy privacyguard/utils privacyguard/ocr` 零 error；回归 418 全绿。
- **工时**：~8h
- **检查点**：cp104

---

## 5. P2 — 功能增量（AGENTS.md 默认方向）

### P2-1 批量替换逐文件规则映射（Phase 2 per-file rule mapping）
- **现状**：未实现。当前批量替换用统一规则集，无法逐文件指定不同规则子集。
- **任务**：
  1. 设计 per-file 规则映射配置结构（文件名 glob / 路径模式 → 规则子集 ID）。
  2. 改造 batch replace worker：按文件选择匹配的规则子集应用。
  3. UI：批量替换面板增加"逐文件规则"配置入口。
  4. 新增 `tests/unit/test_batch_per_file_rules.py`。
- **验证**：新测试通过；`test_batch_word_replace` 回归不退化；手工多文件批量替换按映射正确应用。
- **工时**：~10h
- **检查点**：cp105

### P2-2 批量规则集模板（batch rule-set templates）
- **现状**：未实现。
- **任务**：
  1. 预置规则集模板（如"民事卷宗""合同""银行流水""人事档案"），模板存 config。
  2. UI：设置中心或批量面板增加模板选择器，一键加载/覆盖当前规则集。
  3. 支持用户自定义模板保存/导出/导入。
  4. 新增模板加载/保存/应用测试。
- **验证**：模板加载/保存/应用测试通过；与 P2-1 per-file 映射可组合使用。
- **工时**：~6h
- **检查点**：cp106

> 注：原 AGENTS.md 第三项"preview highlight filtering by source"已落地，从本计划移除。

---

## 6. P3 — 工程化与质量基线

### P3-1 测试覆盖率统计与补强
- **现状**：418 用例但无覆盖率统计，审计提到覆盖缺口。
- **任务**：
  1. 接入 `coverage.py`，跑覆盖率报告（`coverage run -m unittest discover tests/unit` + `coverage report`）。
  2. 识别覆盖率 < 50% 的核心模块，优先 `security/`、`ocr/`、`utils/` 补测试。
  3. 产出覆盖率基线数据入库。
- **验证**：覆盖率报告产出；`security/` + `ocr/` 覆盖率 > 70%。
- **工时**：~8h
- **检查点**：cp107

### P3-2 CI 增强（mypy + coverage 门槛）
- **现状**：CI 已含版本一致性检查 + ruff E9/F + 回归。无类型检查、无覆盖率门槛。
- **任务**：
  1. CI 加 mypy 步骤（范围 `privacyguard/utils/` + `privacyguard/ocr/`）。
  2. CI 加 coverage 报告上传 + 核心模块 70% 门槛。
- **验证**：CI 流水线全绿；PR 可见覆盖率变化。
- **工时**：~3h
- **检查点**：cp108

### P3-3 性能基准与回归
- **现状**：无性能基准。Word 预览增量刷新已做但无量化对比；长文档/大 PDF 无基线数据。
- **任务**：
  1. 建立性能基准脚本（`tests/perf/`，不参与 discover）：长文档预览刷新、批量替换、大 PDF OCR。
  2. 记录基线数据，后续版本回归对比，防止性能退化无感知。
- **验证**：基准脚本可重复运行，数据入 `docs/current/PERF_BASELINE.md`。
- **工时**：~5h
- **检查点**：cp109

### P3-4 国际化基础设施（可选，长期）
- **现状**：全中文硬编码 UI。
- **任务**：评估是否需要 i18n（取决于开源后面向用户群）。若做：抽 `tr()` + `.ts` 文件，先中英双语。
- **验证**：中英文切换可用；UI 文案无硬编码。
- **工时**：~20h（大工程，建议延后至用户群明确后）
- **检查点**：cp110

---

## 7. 执行闭环（每个任务统一遵循）

1. **执行**：按任务描述实现，新功能遵循 AGENTS.md 铁律作为独立模块。
2. **回归**：`powershell -ExecutionPolicy Bypass -File scripts/run_regression.ps1`，必须 418 全绿（416+2 skip）。
3. **静态检查**：`ruff check` + `compileall` 零错误；P1-3 起加 `mypy`。
4. **复盘**：评估完成质量、效率、遗留问题，记录到 `DEV_LOG.md`。
5. **文档**：更新 `STATUS.md` / `DEV_LOG.md` / 本路线图状态标记。
6. **提交**：`type(Px-y): description (cpXX)` 格式，单任务单 commit。

---

## 8. 状态跟踪表

| 任务 | 优先级 | 工时 | 检查点 | 状态 |
|------|--------|------|--------|------|
| 终端用户使用手册 | P0 | 6h | cp100 | ✅ 完成 |
| AGENTS.md 开发方向与行数同步 | P0 | 1h | cp101 | ✅ 完成 |
| helpers.py 垫片消费方迁移 | P0 | 4h | cp102 | ✅ 完成 |
| ocr_worker.py 进一步拆分 | P1 | 5h | cp103 | ⏳ 待办 |
| main.py 渐进优化 | P1 | 持续 | 随版本 | ⏳ 待办 |
| 类型注解 + mypy 渐进 | P1 | 8h | cp104 | ⏳ 待办 |
| 批量替换逐文件规则映射 | P2 | 10h | cp105 | ⏳ 待办 |
| 批量规则集模板 | P2 | 6h | cp106 | ⏳ 待办 |
| 测试覆盖率统计与补强 | P3 | 8h | cp107 | ⏳ 待办 |
| CI 增强（mypy + coverage） | P3 | 3h | cp108 | ⏳ 待办 |
| 性能基准与回归 | P3 | 5h | cp109 | ⏳ 待办 |
| 国际化基础设施（可选） | P3 | 20h | cp110 | ⏳ 可选 |

---

## 9. 动态调整规则

- 每完成一个优先级，复盘实际工时 vs 估算，校准后续估算。
- 若 P2 功能增量在开发中暴露结构阻碍，回插 P1 任务先行收敛。
- 若用户群/产品定位变化（如决定商用或限定中文场景），P3-4 国际化优先级相应调整。
- 本路线图与 `PRIORITY_REMEDIATION_PLAN.md` 互为补充：前者面向未来增量，后者保留为历史整改记录模板。
