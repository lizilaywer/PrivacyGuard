# PrivacyGuard v38 UI 重构执行方案

- 日期：2026-03-13（2026-03-18 已补执行状态）
- 基线版本：`v37.7.4`
- 当前检查点：`v38_ui_refactor_cp31_20260313_140645`
- 目标：在不牺牲现有功能和性能的前提下，把主界面和交互升级为更现代、Windows 友好、符合中国办公软件习惯的产品形态
- 当前执行状态：代码层主阶段已完成，默认进入真机截图驱动抛光

## 2026-03-18 执行结论

### 已完成

1. Phase A - Phase E 已全部落地到当前运行链
2. Windows 专项收尾代码层已完成：
   - 首页、PDF、Word、批量 Word、图片合并、高级设置已统一到同一套桌面级壳层语言
   - 宽窗口 / 全屏 / 超宽窗口策略已接入主工作区与设置中心
   - 工具栏、设置页、批量页、图片合并页都已补齐响应式密度逻辑
3. 当前运行基线仍保持 `v37.7.4`
4. 当前主回归基线已提升到 `52/52`

### 当前剩余工作

1. 真机截图驱动的小毛刺抛光
2. 若 UI 抛光阶段暂停，则恢复默认功能迭代主线：
   - Phase 2：每文件单独规则映射
   - 批量规则模板
   - 预览高亮按来源筛选

## 一、不能动错的底线

1. 保留 Python + PyQt6 主技术栈，不切到 Electron/Tauri。
2. 保留 `main.py` 作为当前活跃运行链，避免“设计稿改了，运行链断了”。
3. 保留 PDF 与 Word 两条业务链的差异：
   - PDF：页面级涂抹，主操作是黑/白遮罩、单双页、缩放翻页、手动画框、导出 PDF
   - Word：文本级替换，主操作是规则替换、智能匹配、手动精修、原文/替换后对比、导出 Word
4. 保留批量 Word 替换模式：
   - 多个 Word 文件拖入或多选后，直接进入批量规则流程
5. 保留 Word 对比预览，但允许用户主动隐藏右侧预览
6. PDF 的黑/白切换必须保持为主工具栏即时控件，不能收进设置
7. Windows 是主要目标环境，所有界面调整优先考虑：
   - `100% / 125% / 150% / 175%` DPI 缩放
   - `Segoe UI Variable / Segoe UI / 微软雅黑 UI` 字体链
   - 鼠标命中区、白底办公对比度、原生窗口行为

## 二、总策略

不做“一次性推翻重写”，而是做“运行链内分层重构”：

1. 先建立 Windows-first 的设计基线和模式切换基线
2. 再补足 Word 专属工具和比较视图显式控制
3. 再改主窗口壳层和工具栏层级
4. 最后重做设置中心和批量工作台表现

这样做的好处：

- 功能不会因 UI 重写而丢失
- 回归点更清晰
- 可以边改边验证 Windows 体验
- 用户现有使用路径不会突然全部失效

## 三、架构落点

### 1. 现阶段

继续以 `main.py` 为主运行链，但开始把 UI 相关能力收束到这些层：

- `theme.py`
  - 负责 Windows-first 设计基线
- `privacyguard/ui/`
  - 新增 UI 设计辅助模块、样式工具、模式定义
- `main.py`
  - 保留行为逻辑，但逐步减少散落在各处的样式和显隐判断

### 2. 中期目标

逐步形成以下结构：

- `privacyguard/ui/styles/`
- `privacyguard/ui/components/`
- `privacyguard/ui/panels/`
- `privacyguard/ui/views/`

说明：
- 第一阶段不强求完全迁移
- 只要新的 UI 逻辑已稳定，就逐步从 `main.py` 抽离

## 四、分阶段执行

### Phase A：安全启动

目标：
- 建立检查点
- 建立计划文档
- 明确 dirty worktree 下的回滚方式

执行：
- 新建 `cp31` 检查点
- 更新 `rollback_journal.md`
- 新建本计划文档

### Phase B：Windows-first 视觉基线

目标：
- 先把视觉语言从旧的 Big Sur 倾向，调整成更适合 Windows 的办公软件风格

执行：
- 更新 `theme.py` 字体链、颜色、圆角、按钮密度
- 优化主窗口、工具栏、滚动区、进度条、对话框的基础样式
- 不改变核心业务流程

验收：
- 主界面观感明显更现代、更克制
- Windows 环境下字体、边框、留白更自然

### Phase C：模式感重构

目标：
- 让用户明确知道当前在做 PDF 还是 Word，避免混淆

执行：
- 增加主界面模式控制逻辑
- PDF 模式只显示 PDF 必要工具
- Word 模式显式显示：
  - `替换规则`
  - `对比预览开关`
- 批量 Word 启动时强化“规则模式”提示

验收：
- PDF 与 Word 工具不再互相干扰
- Word 的对比预览可以主动隐藏
- 批量 Word 流程更明确

### Phase D：主工作台重构

目标：
- 重做主工具栏和工作区层次，让“第一眼更简洁”

执行：
- 工具栏分段
- 信息栏改为更清楚的状态提示
- 预览区域外层壳统一
- 为 PDF/Word 分别优化工具布局

验收：
- 用户第一次打开时，不会被全部控件压住视线
- 高频控件留在眼前，低频控件后移

### Phase E：设置中心重构

目标：
- 把长表单式设置重构成分组明确的设置中心

执行：
- 通用规则
- 自定义关键词
- Word 替换规则入口
- 扫描与微调
- OCR 检测框调节

验收：
- 设置页更像“控制中心”，而不是“长长一页参数表”

## 五、Windows 优化专项

1. 暂不做自绘无边框窗口
   - 原因：容易破坏 Snap Layout、最大化、阴影、DPI 与输入法行为
2. 继续保留原生 PDF canvas
   - 原因：性能好，拖动画框稳定
3. Word 继续使用 `QWebEngineView`
   - 原因：当前预览链已经成熟，支持局部 DOM 更新
4. 强化模式显隐，而不是把所有控件都留在一排
5. 控件尺寸以鼠标操作优先
6. 字体与排版默认以 Windows 办公阅读为优先

## 六、回滚方案

### 1. 本轮前置回滚点

- `cp31`: `backups/v38_ui_refactor_cp31_20260313_140645/`

### 2. 回滚原则

1. 不使用 `git reset --hard`
2. dirty worktree 下按文件回滚
3. 如果 UI 改动波及运行链：
   - 先回退 `main.py`
   - 再回退 `theme.py`
   - 再回退文档记录

### 3. 最小回滚文件集

- `main.py`
- `theme.py`
- `rollback_journal.md`
- `docs/current/DEV_LOG.md`
- `docs/current/STATUS.md`

## 七、回归验证清单

每轮至少执行：

```bash
python3 -m compileall -q main.py privacyguard tests
python3 -m unittest \
  tests.unit.test_mixed_pdf_ocr \
  tests.test_path_validation \
  tests.unit.test_ocr_api \
  tests.unit.test_package_imports \
  tests.unit.test_pdf_text_hit_dedup \
  tests.unit.test_app_config \
  tests.unit.test_word_replace_rules \
  tests.unit.test_batch_word_replace \
  -v
```

重点人工验证：

1. 打开单个 PDF
2. 黑/白切换
3. 单/双页切换
4. 手动画框与右键撤销
5. 打开单个 Word
6. Word 替换规则入口
7. 对比预览显隐
8. 多 Word 拖入直达批量替换规则流程
9. `.doc` 转换提示
10. 多图合并 PDF 流程

## 八、当前执行顺序

本轮将先执行：

1. Phase A：检查点与记录
2. Phase B：Windows-first 视觉基线
3. Phase C：Word 专属工具与可隐藏对比预览

完成后再继续进入：

4. Phase D：主工作台重构
5. Phase E：设置中心重构
