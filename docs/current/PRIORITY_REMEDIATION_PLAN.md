# Priority Remediation Plan

最后更新：2026-03-11
当前基线版本：v37.7.4
适用范围：PrivacyGuard 当前主分支代码

## 执行状态

- `P1 -> P4` 已于 2026-03-09 执行完成。
- 验证检查点：`20260309_runtime_remediation_cp18_verified`
- 后续跟进热修复：`20260309_word_compare_bugfix_cp20_verified`
- 混合 PDF OCR 跟进热修复：`20260309_mixed_pdf_ocr_cp23_verified`
- 文档/打包发布同步：`20260309_release_sync_cp25_verified`
- Word 预览增量刷新热修复：`20260310_word_preview_highlight_cp27_verified`
- 本轮发布同步：`20260310_release_sync_cp29_verified`
- PyInstaller 打包导入失败跟进修复：`20260311_pyinstaller_packaging_fix_cp30_verified`
- 当前状态：本文件保留为“整改记录 + 下次类似问题的执行模板”，不再是待执行计划。

## 用法

下次继续修复时，优先直接阅读本文件，不必回看整段对话。

建议执行顺序：

1. 先做“实施前准备”
2. 按 `P1 -> P2 -> P3 -> P4` 顺序执行
3. 每完成一个优先级，先跑回归，再进入下一项
4. 不要并行改 `main.py` 和 `privacyguard/*` 的同类逻辑后不做统一，否则会继续漂移

## 本次审查结论摘要

当前项目不是“整体不可用”，但存在 2 个需要尽快处理的高优先级问题：

1. 运行时路径校验仍在使用不安全的前缀判断
2. `import privacyguard` 对 OCR 依赖耦合过重，环境不完整时会直接崩溃

除此之外，还有 2 类高价值优化：

1. 文本型 PDF 重复命中会重复追加矩形，影响正确性和性能
2. Word 预览每次全量重绘 HTML，长文档下性能会明显下降

## 实施前准备

### 1. 建立修复检查点

执行前先建立新的 checkpoint，避免和之前的 Word 替换迭代混淆。

推荐命名：

- `cp14_runtime_safety_start`
- `cp15_import_and_textpdf_fix`
- `cp16_word_preview_perf`
- `cp17_settings_version_cleanup`
- `cp18_full_regression_verified`

### 2. 修复前基线验证

在项目根目录执行：

```bash
git status --short
python3 -m unittest tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v
python3 -m compileall -q main.py privacyguard
```

### 3. 本轮修复涉及的核心文件

- `main.py`
- `privacyguard/__init__.py`
- `privacyguard/workers/ocr_worker.py`
- `privacyguard/utils/security.py`
- `privacyguard/utils/config.py`
- `tests/test_path_validation.py`
- `tests/unit/test_ocr_api.py`
- `tests/unit/test_word_replace_rules.py`
- 新增必要测试文件

## P1: 先修运行时安全和导入稳定性

目标：先解决“会出错/会崩/有安全边界问题”的部分。

### P1-1 路径校验统一到共享安全实现

问题：

- `main.py` 仍然保留一份旧版 `validate_safe_path()`
- 旧实现使用 `startswith()` 判断允许目录
- `privacyguard/utils/security.py` 已有更安全的 `commonpath()` 版本，但主流程未接入

要做的事：

1. 删除或停用 `main.py` 中重复实现的旧 `validate_safe_path()`
2. 统一改为导入并使用 `privacyguard.utils.security.validate_safe_path`
3. 全项目搜索同名实现，确保只保留一份活动实现
4. 补测试，覆盖目录前缀绕过场景

最少要覆盖的测试用例：

1. 合法家目录路径通过
2. 合法临时目录路径通过
3. `../` 路径遍历被拒绝
4. `/Users/name_evil/...` 不应被误判为 `/Users/name/...`
5. 文件名非法字符仍然被拒绝

完成标准：

1. 主程序和模块化路径校验逻辑只保留一份真实来源
2. 所有调用点都走共享实现
3. 新增路径前缀绕过测试并通过

### P1-2 修复 `import privacyguard` 的 OCR 依赖崩溃

问题：

- `privacyguard/__init__.py` 会在导入时立即导入 `.workers`
- `privacyguard/workers/ocr_worker.py` 又在模块导入时直接导入 `RapidOCR`
- 导致未安装完整 OCR 依赖时，单纯 `import privacyguard` 就会失败

要做的事：

1. 把 `privacyguard/__init__.py` 改为轻量导出，不在包导入阶段强拉起 OCR worker
2. 把 `RapidOCR` 改成懒加载
3. 只有真正执行 OCR 时才初始化 OCR 引擎
4. 缺依赖时给出明确错误，不允许在 import 阶段直接崩

推荐实现：

1. `privacyguard/__init__.py` 只导出纯工具和元数据
2. 如确实需要导出 worker，使用懒导入方案，例如 `__getattr__`
3. `RapidOCR` 放到 `OCRWorker.__init__()` 或实际运行分支内导入

最少要覆盖的测试用例：

1. 在 mock 掉 `rapidocr_onnxruntime` 不可用的情况下，`import privacyguard` 仍可成功
2. 真正调用 OCR 时，缺依赖能够返回可读错误

完成标准：

1. `import privacyguard` 不再依赖 OCR 运行环境
2. OCR 失败只在 OCR 真正被调用时暴露

## P2: 修正确性问题，并顺手拿到第一波性能收益

目标：修复错误结果和不必要的重复计算。

### P2-1 修复文本型 PDF 重复命中重复追加矩形

问题：

- 文本型 PDF 扫描时，代码按正则匹配次数循环
- 但缓存的是整个 `page.search_for(found_str)` 结果集
- 同一个字符串重复出现时，会把同一批 `hits` 反复 append

直接后果：

1. 重复遮罩框
2. 导出结果风险增加
3. 页面越大、重复词越多，性能越差

要做的事：

1. 改为“每页每个唯一 `found_str` 只 search 和 append 一次”
2. 如果后续需要按出现次数精确映射位置，单独设计位置匹配逻辑，不要重复追加整批 hits
3. 同步修正 `main.py` 和 `privacyguard/workers/ocr_worker.py`，不要只修一处

最少要覆盖的测试用例：

1. 同一页同一关键词出现多次时，rect 数量不应指数级增长
2. 多个不同关键词同时存在时，结果仍正确

完成标准：

1. 重复文本不会生成重复矩形
2. 相关测试通过
3. `main.py` 与模块化 worker 逻辑保持一致

### P2-2 收敛重复实现，停止主程序和模块层继续漂移

问题：

- 当前 `main.py` 里仍保留大量活动逻辑
- `privacyguard/*` 下也有同类实现
- 已经发生安全修复不同步、OCR 逻辑不同步

要做的事：

1. 为路径校验、OCR 文本页处理、配置读取明确唯一真实实现
2. 主程序只负责 UI 和编排，不再保留平行算法副本
3. 统一搜索并标记“旧实现”“兼容层”“唯一入口”

完成标准：

1. 同一类逻辑只有一个主实现
2. 其他位置只做调用

## P3: 优先做 Word 预览性能整改

目标：解决长 Word 文档下预览卡顿和高亮串位风险。

### P3-1 停止右侧预览每次全量 `setHtml()`

问题：

- 当前右侧“替换后预览”每次刷新都重建整份 HTML
- `QWebEngineView.setHtml()` 会触发整页重新解析和布局

要做的事：

1. 保留稳定的 base html
2. 对变更块做增量更新，而不是整页重灌
3. 优先考虑通过 `data-key` 定位 DOM 节点后局部替换
4. 手动脱敏、OCR 脱敏、规则替换都走同一份“预览状态模型”

推荐实现：

1. 维护统一的 `preview_state`
2. 先计算每个 block 的最终显示文本和高亮来源
3. 前端只更新受影响 block

完成标准：

1. 单次手动脱敏/撤回不再触发整页重绘
2. 大文档下右侧预览响应显著改善

### P3-2 去掉 HTML 全局正则替换式高亮

问题：

- 当前有后备逻辑直接对整个 HTML 做全局替换
- 相同文本在多个块重复时，容易串位

要做的事：

1. 以 `data-key` 或 block id 为中心做高亮绑定
2. 不再以“纯文本全局替换 HTML”的方式插入标记
3. 精确模式和全局模式统一走 block 级别渲染

最少要覆盖的测试和手工场景：

1. 同一姓名在多个段落出现时，不串位
2. 规则替换、OCR、手动脱敏叠加时，高亮来源正确
3. 撤回后右侧预览同步恢复

完成标准：

1. 长文档渲染性能改善
2. 重复文本高亮不串位

## P4: 修产品一致性问题

目标：解决“用户看起来像保存了，其实没保存”和“版本信息不一致”。

### P4-1 明确并修复设置持久化策略

问题：

- 当前“保存设置”并不会持久化大多数设置
- 用户预期和实际行为不一致

要做的事：

1. 明确哪些设置应该跨重启持久化
2. 将这些设置统一 `persist=True`
3. 如果某些值只应该会话内生效，UI 文案必须明确说明
4. 检查是否应该切换到 `privacyguard/utils/config.py` 的统一配置入口

建议至少确认以下项：

1. 扫描级别
2. OCR 检测框调节比例
3. 偏移量
4. 统一替换文本
5. 自定义关键词

完成标准：

1. 用户点击“保存设置”后，关键设置重启后仍生效
2. 测试或手工验证有记录

### P4-2 统一版本来源

问题（历史背景，已于 2026-03-09 收敛）：

- `main.py` 曾与包元数据存在版本漂移
- 版本入口曾分散在代码与打包配置中

要做的事：

1. 明确单一版本源，优先建议用 `version.txt`
2. 所有代码、打包脚本、包元数据从同一来源读取
3. 清理硬编码版本号

完成标准：

1. 代码、包元数据、打包配置版本一致

## 推荐执行顺序

严格按下面顺序：

1. `P1-1` 路径校验统一
2. `P1-2` OCR 懒加载与安全导入
3. `P2-1` 文本型 PDF 去重
4. `P2-2` 收敛重复实现
5. `P3-1` Word 预览增量刷新
6. `P3-2` 去掉全局 HTML 正则高亮
7. `P4-1` 设置持久化
8. `P4-2` 版本来源统一

## 每个优先级完成后的回归命令

```bash
python3 -m unittest tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v
python3 -m compileall -q main.py privacyguard
```

## 需要补充的测试

优先新增以下测试：

1. `tests/test_path_validation.py`
   - 增加目录前缀绕过用例
2. 新增 `tests/unit/test_package_imports.py`
   - 验证无 OCR 依赖时包可安全导入
3. 新增 `tests/unit/test_pdf_text_hit_dedup.py`
   - 验证重复文本不会重复追加矩形
4. 视情况新增 `tests/unit/test_word_preview_state.py`
   - 验证预览状态合并与高亮来源

## 手工验收清单

### 安全与稳定性

1. 非法路径被拒绝
2. 合法家目录和临时目录路径通过
3. 缺少 OCR 依赖时，应用非 OCR 功能仍可打开

### PDF

1. 文本型 PDF 中重复姓名不会产生重复遮罩框
2. 图片型 PDF 现有 OCR 流程不退化

### Word

1. 单文档打开正常
2. 规则替换正常
3. 智能脱敏正常
4. 手动精确脱敏正常
5. 撤回后左右预览同步
6. 长文档预览不卡顿或明显改善

### 设置与版本

1. 保存设置后重启仍生效
2. UI 标题、包版本、打包版本一致

## 本文件的使用说明

下次如果要执行这轮整改，直接从本文件开始：

1. 先读“实施前准备”
2. 建 checkpoint
3. 按“推荐执行顺序”逐项完成
4. 每做完一项就跑“回归命令”
5. 最后补 `STATUS.md`、`DEV_LOG.md`、`CHANGELOG.md` 和 `rollback_journal.md`

如果时间有限，最低限度先完成：

1. `P1-1`
2. `P1-2`
3. `P2-1`

这 3 项修完，风险会先显著下降。
