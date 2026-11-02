# main.py 渐进式重构计划（已完成）

**制定日期**: 2026-08-01  
**完成日期**: 2026-08-01  
**最终结果**: main.py 16,702 → 9,287 行（-7,415 行，-44%）  
**回归验证**: 每步 385 项全绿，零行为变更  
**铁律**: 每步之后 385 项回归全绿，零行为变更，纯结构重构

## 执行记录（Git 提交链）

| 提交 | 阶段 | 内容 | 减少 |
|------|------|------|------|
| `d6cec35` | Phase 1 | 57 个自由函数 → `privacyguard/utils/helpers.py` | -1,372 |
| `51d6d55` | Phase 2 | 7 个 Dialog 类 → `privacyguard/ui/dialogs/` | -3,161 |
| `6c63024` | Phase 3 | 514 行内联 JS → `assets/js/word_preview_interactive.js` | -508 |
| `cf422fd` | Phase 4a | 7 个独立类 → workers/dialogs/widgets | -995 |
| `b7b9cd8` | Phase 4b | 27 个 Word 预览方法 → `WordPreviewMixin` | -794 |
| `4efdd5b` | Phase 4c | 22 个页面视图方法 → `PageViewMixin` | -585 |
| `0cb798c` | 修复 | WebViewBridge 延迟导入 NameError | — |
| `8bd4202` | 工程化 | CI 管道 + 依赖分离 + Mixin 接口契约 | — |
| `7491b32` | 审计修复 | 复盘审计发现 4 处 debug print，门控修复 | — |
| `64b7233` | 清理 | 移除 15MB+ 冗余文件（8 git-tracked + 物理垃圾） | -6,444 行 |

**回滚标签**: `pre-phase4`(6c63024) / `pre-phase4b`(90a3150)

## 后续规则（写入 AGENTS.md 铁律）

**新功能必须作为独立模块开发，禁止直接往 main.py 添加方法。**
详见 AGENTS.md "Architecture rules for new features" 章节。

---

## 总体原则

1. **每步一提交**：每个 Phase 完成后立即 git commit，形成独立回滚点
2. **先叶后根**：先提取无依赖的叶子模块，最后动 MainWindow 核心
3. **import 兼容**：main.py 中保留 `from privacyguard.xxx import *` 或显式导入，
   所有现有测试（直接 import main 的）不需要修改
4. **D1 铁律延续**：新提取的纯逻辑模块不依赖 Qt/GUI
5. **验证闭环**：每步执行 `compileall` + `unittest discover`，385 全绿才继续

---

## Phase 0: 准备工作

### 0.1 创建重构分支

```bash
git checkout -b refactor/main-decompose
```

所有重构在此分支进行，main 分支保持可发布状态。
每个 Phase 完成后 merge 回 main（或 squash merge）。

### 0.2 备份当前 main.py

```bash
cp main.py backups/main_py_pre_refactor_20260801.py
```

### 0.3 确认基线

```bash
venv_win/Scripts/python.exe -m compileall -q main.py privacyguard tests
venv_win/Scripts/python.exe -m unittest discover -s tests/unit
# 预期: Ran 385 tests ... OK (skipped=2)
```

### 0.4 识别 main.py 中的 import 依赖图

在提取前，用 AST 分析确认哪些自由函数被 MainWindow/Dialog 引用，
哪些仅被其他自由函数引用。这决定提取顺序。

---

## Phase 1: 提取自由函数（~1,300 行）

**风险**: 极低（纯函数，无 Qt 依赖，无状态）  
**预期减少**: main.py 从 16,672 → ~15,400 行

### 1.1 目标模块

创建 `privacyguard/utils/helpers.py`，收纳 main.py 第 291-1650 行的
全部自由函数（约 40 个）。

### 1.2 提取清单

| 函数 | 大致行号 | 依赖 | 备注 |
|------|---------|------|------|
| `normalize_rules` | ~291 | re, DEFAULT_RULES | 规则标准化 |
| `rects_overlap_ratio` | ~320 | 无 | 几何计算 |
| `build_search_snippet` | ~350 | 无 | 搜索片段 |
| `push_undo_snapshot` | ~691 | 无 | 已优化为 del 切片 |
| `resolve_word_preview_image_suffix` | ~699 | 无 | 后缀映射 |
| `snapshot_page_data` | ~620 | QRectF | 需 Qt 但纯函数 |
| `restore_page_data` | ~650 | QRectF | 同上 |
| `collect_text_hits` | ~1580 | re | 搜索命中 |
| `is_watermark_block` | ~1290 | re | 水印判定 |
| 其余 ~30 个 | 291-1650 | 混合 | 逐一确认 |

### 1.3 执行步骤

1. 创建 `privacyguard/utils/helpers.py`，写入文件头注释
2. 将函数逐个从 main.py 剪切到 helpers.py
3. 在 helpers.py 顶部添加必要 import（re, os, json 等）
4. 对于依赖 `DEFAULT_RULES` 的函数：将 `DEFAULT_RULES` 常量也移入
   helpers.py（或单独的 `privacyguard/utils/constants.py`）
5. 对于依赖 QRectF 的纯函数（snapshot/restore）：在 helpers.py 中
   `from PyQt6.QtCore import QRectF`（这是唯一允许的 Qt 依赖）
6. 在 main.py 顶部添加：
   ```python
   from privacyguard.utils.helpers import *
   ```
   或显式导入所有被引用的函数名
7. 在 `privacyguard/utils/__init__.py` 中添加 helpers 的导出

### 1.4 验证

```bash
venv_win/Scripts/python.exe -m compileall -q main.py privacyguard tests
venv_win/Scripts/python.exe -m unittest discover -s tests/unit
# 预期: 385 全绿
```

### 1.5 提交

```bash
git add -A && git commit -m "refactor: extract ~40 free functions to privacyguard/utils/helpers.py"
```

### 1.6 回滚

```bash
git revert HEAD
```

---

## Phase 2: 提取 Dialog 类（~4,000 行）

**风险**: 低（QDialog 子类，与 MainWindow 耦合点有限）  
**预期减少**: main.py 从 ~15,400 → ~11,400 行

### 2.1 目标结构

```
privacyguard/ui/
├── __init__.py
└── dialogs/
    ├── __init__.py
    ├── settings_dialog.py      # SettingsDialog (~2,200 行)
    ├── trace_clean_dialog.py   # TraceCleanDialog (~130 行)
    ├── word_rules_dialog.py    # WordReplaceRulesDialog (~250 行)
    ├── image_list_dialog.py    # ImageListDialog (~120 行)
    └── feedback_dialog.py      # FeedbackDialog + DonateDialog (~400 行)
```

### 2.2 提取顺序（按耦合度从低到高）

1. **ImageListDialog**（最独立，仅接收列表返回排序结果）
2. **FeedbackDialog / DonateDialog**（纯展示，无数据回传）
3. **TraceCleanDialog**（接收 items + allowed_roots，回调 on_cleaned）
4. **WordReplaceRulesDialog**（接收规则列表，返回编辑后规则）
5. **SettingsDialog**（最复杂，引用 config、DEFAULT_RULES、多个回调）

### 2.3 耦合处理策略

每个 Dialog 与 MainWindow 的交互通过以下方式解耦：

- **构造参数**：所有需要的数据通过 `__init__` 参数传入（已有模式）
- **信号**：Dialog 通过 pyqtSignal 通知结果（如 `rules_changed`）
- **回调函数**：对于需要调用 MainWindow 方法的场景（如 SettingsDialog
  的 `_open_trace_clean_dialog`），传入回调函数引用
- **config 对象**：通过构造参数传入 config 实例，不直接引用全局变量

### 2.4 SettingsDialog 特殊处理

SettingsDialog 是最复杂的（2,200 行），需要特别注意：

- 它引用了 `DEFAULT_RULES`（Phase 1 已移至 helpers/constants）
- 它引用了 `config`（SimpleConfig 实例）→ 通过构造参数传入
- 它的 `save_settings` 方法修改 `self.selected_rules` 等属性，
  MainWindow 在 `exec()` 后读取 → 保持不变（Dialog 属性访问模式）
- 它的 `_apply_dialog_theme` 方法（337 行 CSS）→ 随类一起移动
- 它的 `_refresh_settings_layout_density`（350 行）→ 随类一起移动

### 2.5 main.py 中的导入更新

```python
from privacyguard.ui.dialogs import (
    SettingsDialog, TraceCleanDialog, WordReplaceRulesDialog,
    ImageListDialog, FeedbackDialog, DonateDialog
)
```

### 2.6 验证

每个 Dialog 提取后立即验证（不要等全部提取完）：

```bash
venv_win/Scripts/python.exe -m compileall -q main.py privacyguard tests
venv_win/Scripts/python.exe -m unittest discover -s tests/unit
```

### 2.7 提交（每个 Dialog 一次或全部一次）

```bash
git commit -m "refactor: extract Dialog classes to privacyguard/ui/dialogs/"
```

---

## Phase 3: 外部化内联 JavaScript（~690 行）

**风险**: 低（字符串常量提取为文件，运行时行为不变）  
**预期减少**: main.py 从 ~11,400 → ~10,700 行（Python 行数）

### 3.1 目标结构

```
assets/js/
├── word_preview_interactive.js   # _INTERACTIVE_JS_CODE (~520 行)
└── word_scroll_sync.js           # 滚动同步脚本 (~170 行)
```

### 3.2 执行步骤

1. 创建 `assets/js/` 目录
2. 将 `_INTERACTIVE_JS_CODE` 字符串内容提取为
   `assets/js/word_preview_interactive.js`
3. 将滚动同步 JS 提取为 `assets/js/word_scroll_sync.js`
4. 在 main.py 中用 `resource_path` 加载：
   ```python
   def _load_js_asset(filename):
       path = resource_path(os.path.join("assets", "js", filename))
       with open(path, "r", encoding="utf-8") as f:
           return f.read()
   
   _INTERACTIVE_JS_CODE = _load_js_asset("word_preview_interactive.js")
   ```
5. 确保 PyInstaller spec 文件的 `datas` 包含 `assets/js/`

### 3.3 验证

- compileall 通过
- 回归 385 全绿
- 手动验证：打开 Word 文档，确认预览交互正常（高亮、手动脱敏点击）

### 3.4 提交

```bash
git commit -m "refactor: externalize inline JavaScript to assets/js/"
```

---

## Phase 4: MainWindow 功能域提取（长期，中等风险）

**风险**: 中等（涉及 MainWindow 内部状态和方法调用链）  
**预期减少**: MainWindow 从 ~10,000 → ~6,000 行  
**前置条件**: Phase 1-3 全部完成且稳定运行至少一个版本周期

### 4.1 提取目标（按优先级）

| 优先级 | 功能域 | 估计行数 | 目标模块 |
|--------|--------|---------|---------|
| 1 | 页面视图（网格/缩略图/选择） | ~1,500 | `privacyguard/ui/page_view.py` |
| 2 | 全文搜索面板 | ~800 | `privacyguard/ui/search_panel.py` |
| 3 | 撤销/重做系统 | ~400 | `privacyguard/ui/undo_manager.py` |
| 4 | PDF 加密导出 | ~300 | `privacyguard/ui/pdf_export.py` |
| 5 | 水印移除 | ~400 | `privacyguard/ui/watermark.py` |

### 4.2 提取模式

每个功能域提取为独立 QWidget/QObject 子类：

```python
# privacyguard/ui/page_view.py
class PageViewPanel(QWidget):
    """cp67: 多页网格视图面板"""
    
    page_selected = pyqtSignal(int)
    pages_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid_canvases = {}
        self._grid_pix_cache = {}
        # ... 原 MainWindow 中的页面视图相关属性
    
    # 原 MainWindow 中的 _build_page_view_container,
    # _render_grid_page, _on_grid_click 等方法移入此类
```

MainWindow 中保留一个实例引用：

```python
class MainWindow(QMainWindow):
    def __init__(self):
        # ...
        self.page_view_panel = PageViewPanel(self)
        self.page_view_panel.page_selected.connect(self._on_page_selected)
```

### 4.3 状态共享策略

MainWindow 与提取出的 Panel 之间共享的状态：

- **page_data**：通过属性访问器或信号传递
- **doc (fitz.Document)**：通过方法参数传入
- **mask_color / zoom_scale**：通过 setter 方法同步
- **undo/redo 栈**：UndoManager 独立管理，MainWindow 只触发

### 4.4 风险控制

- 每次只提取一个功能域
- 提取前创建 git tag（如 `pre-pageview-extract`）
- 提取后运行完整回归 + 手动冒烟测试
- 如果回归失败，立即 `git revert` 而非尝试修复

### 4.5 不提取的部分

以下保留在 MainWindow 中（核心协调逻辑）：

- `__init__` / `setup_ui`（UI 组装）
- 文件打开/关闭流程（`_open_pdf_file` / `_cleanup_before_open`）
- 模式切换（PDF/Word/Image 三态）
- 工具栏构建和密度管理（与全局布局强耦合）
- 快捷键绑定
- 拖放处理

---

## Phase 5: 清理与收尾

### 5.1 移除 main.py 中的兼容性导入

当所有测试不再直接 `from main import xxx` 时，移除 main.py 中的
`from privacyguard.utils.helpers import *` 等宽泛导入，改为显式导入。

### 5.2 更新测试导入

将测试中的 `from main import push_undo_snapshot` 改为
`from privacyguard.utils.helpers import push_undo_snapshot`。

### 5.3 更新 AGENTS.md

- 更新 Main Files 章节
- 更新架构描述
- 记录新的模块职责

### 5.4 合并回 main 分支

```bash
git checkout main
git merge refactor/main-decompose --no-ff
git tag v37.9.0-refactor
```

---

## 时间估算

| Phase | 工作量 | 风险 | 建议节奏 |
|-------|--------|------|---------|
| Phase 0 | 10 分钟 | 无 | 立即 |
| Phase 1 | 1-2 小时 | 极低 | 第一个工作日 |
| Phase 2 | 3-4 小时 | 低 | 分 2-3 次完成 |
| Phase 3 | 30 分钟 | 低 | 与 Phase 2 同日 |
| Phase 4 | 每个域 2-3 小时 | 中 | 每个版本周期提取一个 |
| Phase 5 | 30 分钟 | 低 | 全部完成后 |

**总计**: Phase 1-3 可在一天内完成（~6 小时），Phase 4 分散在后续 3-5 个版本中。

---

## 验证检查清单（每步必做）

- [ ] `compileall -q main.py privacyguard tests` 零错误
- [ ] `unittest discover -s tests/unit` → 385 全绿
- [ ] `python main.py` 能正常启动（不崩溃）
- [ ] 打开一个 PDF → 智能脱敏 → 导出（核心路径冒烟）
- [ ] git commit 成功

---

## 禁止事项

1. **不做行为变更**：重构期间不修 bug、不加功能、不改 UI
2. **不动 OCR 管线**：ocr_worker.py 的 1,571 行虽大，但与 main.py
   解耦良好，不在此次重构范围
3. **不动测试逻辑**：测试文件只做 import 路径更新，不改断言
4. **不引入新依赖**：不引入 dependency-injection 框架、不引入 ABC 抽象层
5. **不重命名公开 API**：函数名、类名、信号名保持不变
