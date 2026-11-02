# 架构说明 | PrivacyGuard 脱敏卫士

> 本文档描述 PrivacyGuard 的分层架构、模块职责、关键设计决策与扩展规则。
> 编码前必读 [AGENTS.md](AGENTS.md)（开发指南，单一事实来源）与 [CONTRIBUTING.md](CONTRIBUTING.md)（贡献流程）。

最后更新：2026-08-02 ｜ 当前基线：v37.8.11 ｜ main.py：9,271 行（已从 16,702 行重构 -44%）

---

## 1. 总体架构

PrivacyGuard 是单进程桌面应用，采用**协调器 + 共享模块包**的分层架构。

```
┌─────────────────────────────────────────────────────────────┐
│  main.py  —  MainWindow 协调器（9,271 行）                    │
│  ┌─────────────┬──────────────┬───────────────────────────┐ │
│  │ UI 构建/布局  │ 文件/模式协调  │ OCR 编排/撤销重做/会话草稿  │ │
│  └─────────────┴──────────────┴───────────────────────────┘ │
│         │ Mixin 接入            │ 实例化 + 信号接线           │
│         ▼                      ▼                            │
│  ┌──────────────┐       ┌──────────────┐                   │
│  │ PageViewMixin│       │ WebViewBridge│ JS-Python 桥接     │
│  │ WordPreview  │       └──────────────┘                   │
│  │ SettingsMixin│                                          │
│  └──────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  privacyguard/  —  共享模块包                                 │
│  ┌────────┬────────┬──────────┬──────────┬───────────────┐  │
│  │ utils  │   ui   │ workers  │   ocr    │ report/session │  │
│  │60 函数 │ widgets│ QThread  │ 引擎+算法 │ trace_cleaner │  │
│  │ config │ dialogs│ 信号通信  │ 懒加载    │               │  │
│  │security│ mixins │          │          │               │  │
│  └────────┴────────┴──────────┴──────────┴───────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  外部依赖：PyQt6 ｜ PyMuPDF ｜ RapidOCR ｜ OpenCV ｜ python-docx │
└─────────────────────────────────────────────────────────────┘
```

### 设计原则

1. **协调器不写算法**：`main.py` 只负责 UI 构建、布局、菜单/工具栏、快捷键、信号接线和模块调用编排
2. **新功能独立模块**：超过 50 行的非 UI 布局代码不应写在 `main.py`（见 §6 扩展规则）
3. **单一真实来源**：同类逻辑只保留一份活动实现，禁止 `main.py` 与 `privacyguard/*` 平行副本
4. **懒加载重依赖**：OCR 等重依赖延迟到真正使用时才初始化

---

## 2. 分层职责

### 2.1 表现层 — `main.py`

`MainWindow(PageViewMixin, WordPreviewMixin, QMainWindow)` 是应用主窗口协调器，职责：

| 职责域 | 说明 |
|--------|------|
| UI 构建 | 工具栏、密度布局、主题、响应式适配 |
| 流程协调 | 文件打开/关闭、PDF/Word 模式切换 |
| Worker 编排 | 实例化 OCRWorker/WordWorker，接线信号槽 |
| 状态管理 | 撤销重做栈、会话草稿、配置读写 |
| JS 桥接 | `WebViewBridge(QObject)` 处理 Word 预览交互 |

**铁律**：`main.py` 只允许新增信号接线、菜单/工具栏按钮、快捷键绑定、对独立模块的调用编排。

### 2.2 Mixin 层 — `privacyguard/ui/mixins/`

仅当功能与 MainWindow 状态深度耦合且无法用信号解耦时，才使用 Mixin。每个 Mixin 必须在类 docstring 写明接口契约（需要 MainWindow 提供哪些属性和方法）。

| Mixin | 方法数 | 职责 |
|-------|--------|------|
| `PageViewMixin` | 25 | PDF 页面视图、网格、旋转/插入空白页/插入文件/删除、缩放 |
| `WordPreviewMixin` | 27 | Word 双栏预览、高亮融合、增量刷新 |
| `SettingsLayoutMixin` | — | 设置对话框布局密度与响应式 |
| `SettingsActionsMixin` | — | 设置对话框规则/关键词/OCR 操作 |

### 2.3 共享模块层 — `privacyguard/`

详见 §3 模块清单。

### 2.4 外部依赖层

| 依赖 | 用途 | 加载策略 |
|------|------|---------|
| PyQt6 | GUI 框架 + WebEngine（Word 预览） | 启动即加载 |
| PyMuPDF (fitz) | PDF 解析、文本搜索、遮罩、加密 | 按需 |
| RapidOCR (onnxruntime) | 图片/扫描件 OCR | **懒加载**，仅 OCR 执行时初始化 |
| OpenCV | 图像处理、印章/签名检测 | 按需 |
| python-docx / mammoth | Word 文档解析与改写 | 按需 |

---

## 3. 模块清单

### 3.1 `privacyguard/utils/` — 共享工具与纯函数

| 文件 | 职责 |
|------|------|
| `helpers_{pdf,word_rules,word_doc,word_preview,ui}.py` | 60 个共享纯函数按域拆为 5 模块（v37.8.11 P3-1；原 `helpers.py` 已移除） |
| `config.py` | `ConfigManager` 配置入口（共享实现，运行时可选用 `SimpleConfig`） |
| `security.py` | `validate_safe_path`（`commonpath` 安全实现）、`resource_path` |
| `doc_converter.py` | Word 文档格式转换 |
| `temp_manager.py` | `TempFileManager` 临时文件管理 |
| `exceptions.py` | 异常类层级（`PrivacyAppError` 基类及子类） |
| `logger.py` | 统一日志框架（`init_logging` / `get_logger`，控制台 + 文件滚动） |

### 3.2 `privacyguard/ocr/` — OCR 引擎与检测算法

| 文件 | 职责 |
|------|------|
| `base.py` | `BaseOCREngine` / `OCRResult` / `CharInfo` 抽象基类 |
| `manager.py` | `OCREngineManager` 引擎管理 |
| `rapidocr.py` | `RapidOCREngine`（懒加载，单引擎架构） |
| `text_pdf.py` | 文本型 PDF 命中收集、`box_adjust` 应用 |
| `mixed_pdf.py` | 混合 PDF：文本层 + 嵌入图片块 OCR |
| `seal_detection.py` | 印章检测（多特征评分融合，cp52，2026-08-01 从 ocr_worker 外提） |
| `signature_detection.py` | 签名手印检测（红/黑双路径 + 暖色门控，cp60） |

**懒加载契约**：`privacyguard/__init__.py` 通过 `__getattr__` 懒导入 Workers 与 OCR 引擎，`import privacyguard` 不依赖 OCR 运行环境。OCR 失败只在 OCR 真正被调用时暴露。

### 3.3 `privacyguard/workers/` — 后台线程

所有 Worker 继承 `QThread`，通过 `pyqtSignal` 与 MainWindow 通信，MainWindow 仅负责实例化和接线。

| 文件 | 职责 | 关键信号 |
|------|------|---------|
| `ocr_worker.py` | PDF OCR + 印章 + 签名检测（薄包装，算法在 `ocr/`） | `finished_signal` / `progress_signal` / `page_result_signal` / `error_signal` |
| `word_worker.py` | Word 智能脱敏 | `finished_signal` / `error_signal` |
| `batch_replace_worker.py` | 批量 Word 替换 | `progress_signal` / `finished_signal` |
| `search_worker.py` | 全文搜索（cp81，文本层/扫描页 OCR/Word 块搜索） | `result_signal` |
| `image_merge.py` | 多图合并 PDF | `finished_signal` |

### 3.4 `privacyguard/ui/` — UI 组件

| 文件/目录 | 职责 |
|----------|------|
| `widgets.py` | `SinglePageCanvas` / `PageGridScrollArea` / `ColorPickerOverlay` |
| `dialogs/` | 10 个 Dialog（Settings / TraceClean / WordReplaceRules / ImageList / Feedback / Donate / ManualRegion / Encrypt / PasswordOpen） |
| `mixins/` | 见 §2.2 |

### 3.5 顶层业务模块

| 文件 | 职责 |
|------|------|
| `report.py` | cp87 脱敏报告纯函数（规则分类 + 逐页详情） |
| `session_store.py` | cp88 会话恢复（崩溃安全的遮罩草稿 + doc-bytes 快照） |
| `trace_cleaner.py` | cp90 清理使用痕迹（草稿/临时/预览缓存/日志 + 白名单 realpath 守卫） |

---

## 4. 关键设计决策

### 4.1 版本源单一化

`version.txt` 是版本号唯一来源：

```
version.txt  ──►  main.py (read_app_version)
             ──►  privacyguard.__version__ (_read_version)
             ──►  packaging/windows/config/version_info.txt (generate_version_info.py 生成)
```

CI 流水线校验四处一致性，任一不一致将导致 CI 失败。禁止硬编码版本号、禁止手动编辑 `version_info.txt`。

### 4.2 配置双路径

- 运行时当前使用 `main.py` 中的 `SimpleConfig`
- 共享配置工具另存于 `privacyguard/utils/config.py`（`ConfigManager`）
- 除非已显式切换，不要假设 `ConfigManager` 是活动运行路径
- `config.json` 是本地运行配置（git-ignore），仓库只保留 `config.json.template`，`SimpleConfig` 首次启动时从模板初始化

### 4.3 OCR 懒加载

- `privacyguard` 包导入是懒加载
- `RapidOCR` 只在实际 OCR 执行时初始化
- 禁止在 `privacyguard/__init__.py` 或 `privacyguard/workers/__init__.py` 添加包级 eager OCR 导入

### 4.4 混合 PDF 处理流程

混合 PDF 页面不能当作纯文本或纯扫描处理。活动路径：

1. 文本层命中收集
2. 通过 `page.get_text("dict")` 发现嵌入图片块
3. 图片块 OCR
4. 局部 OCR box 偏移回页面坐标

共享逻辑在 `privacyguard/ocr/mixed_pdf.py`。

**回归排查优先级**：文本层 vs 图片块切分、图片 clip 提取有效性、OCR box 偏移回页面坐标、合并后去重。

### 4.5 统一日志框架

v37.8.11 P0-3 引入 `privacyguard/utils/logger.py`：

- `init_logging()` 幂等初始化根 logger（控制台 + 文件双通道，按大小滚动）
- `get_logger(name)` 获取命名 logger
- 日志级别由 `PG_LOG_LEVEL` 环境变量控制
- 全项目 `print` 调试输出已替换为 `logger` 调用
- 日志目录解析见 `_resolve_log_dir()`

### 4.6 撤销重做

- 快照栈深度 20（`push_undo_snapshot`）
- doc-bytes 快照可恢复已删除页面
- `Ctrl+Z` / `Ctrl+Y` 触发
- 遮罩编辑与页面结构操作共享同一快照栈

---

## 5. 核心数据流

### 5.1 PDF 智能脱敏流程

```
用户打开 PDF
   │
   ▼
MainWindow 渲染页面（SinglePageCanvas / PageGridScrollArea）
   │
   ▼ 用户点击"智能脱敏"
   │
OCRWorker(QThread) 启动
   │
   ├─► 文本型页面：text_pdf.collect_text_pdf_hit_boxes
   │     └─► 规则正则匹配 → page.search_for → 命中矩形（去重）
   │
   ├─► 扫描/图片页面：preprocess_image → RapidOCR → _shrink_box → _detect_text_boundaries
   │
   ├─► 混合页面：mixed_pdf 文本层 + 图片块 OCR 合并
   │
   ├─► 印章检测：seal_detection.detect_seals（多特征评分）
   │
   └─► 签名手印检测：signature_detection.detect_signatures（暖色门控）
   │
   ▼ page_result_signal(页码, 矩形列表)
   │
MainWindow 接收 → 应用 box_adjust_ratio → 渲染遮罩 → 入撤销栈
   │
   ▼ 用户点击"导出"
   │
PyMuPDF 应用遮罩 + AES-256 加密 → 导出 PDF + 脱敏报告（report.py）
```

### 5.2 Word 脱敏流程

```
用户打开 .docx/.doc
   │
   ▼ doc_converter 转换 .doc → .docx
   │
WordPreviewMixin 渲染双栏（左原文 / 右替换后预览，QWebEngineView）
   │
   ▼ 用户选择规则替换 / 智能脱敏 / 手动精确
   │
WordWorker(QThread) 或同步处理
   │
   ├─► 规则匹配：helpers.build_word_rule_matches
   ├─► OCR 替换：helpers.resolve_word_ocr_replacements
   ├─► 优先级合并：helpers.merge_word_matches_with_priority
   └─► 应用到 docx：helpers.replace_matches_in_paragraph / cell
   │
   ▼ 增量更新右侧预览（data-key 定位 DOM，局部替换，非全量 setHtml）
   │
用户导出 → python-docx 保存 .docx
```

---

## 6. 扩展规则

新增功能时按类型选择放置位置（铁律，详见 [AGENTS.md](AGENTS.md)）：

### 6.1 新增 Worker

```python
# privacyguard/workers/xxx_worker.py
class XxxWorker(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, ...):
        super().__init__()
        ...

    def run(self):
        try:
            ...
            self.progress_signal.emit(percent)
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))
```

`main.py` 仅负责实例化与 `connect` 信号槽。

### 6.2 新增 Dialog

```python
# privacyguard/ui/dialogs/xxx_dialog.py
class XxxDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        ...
    # 通过属性或信号返回结果
```

通过构造参数接收数据、通过信号或属性返回结果。

### 6.3 新增纯逻辑

放入 `privacyguard/utils/` 或 `privacyguard/ocr/`，编写独立单元测试 `tests/unit/test_xxx.py`。

### 6.4 新增 Mixin

仅当功能与 MainWindow 状态深度耦合且无法用信号解耦时使用。类 docstring 必须写明接口契约。

---

## 7. 测试架构

### 7.1 测试组织

```
tests/
├── unit/           # 单元测试（参与 unittest discover，CI 与回归基线来源）
│   ├── test_luhn_validation.py
│   ├── test_seal_detection.py
│   ├── test_mixed_pdf_ocr.py
│   ├── test_logger.py          # v37.8.11 新增
│   └── ...                     # 当前 418 项基线
└── legacy/          # 失效/陈旧测试（不参与 discover，仅保留历史）
```

### 7.2 执行方式

```powershell
# Windows 全量回归
powershell -ExecutionPolicy Bypass -File scripts/run_regression.ps1
# macOS / Linux
./scripts/run_regression.sh
```

`unittest discover` 自动发现 `tests/unit` 全部用例，新测试文件自动纳入，清单永不漂移。

### 7.3 基线说明

当前基线 `418`（v37.8.11）：

- 真实样本存在时：`418/418` 全绿
- 真实样本缺失时（典型干净检出）：`416 passed + 2 skipped`（跳过 `test_real_pdf_seals_detected` 与 `test_real_pdf_black_fingerprint_detected`，印章/签名端到端语义由合成样本用例兑付）

### 7.4 CI 流水线

`.github/workflows/ci.yml`（`windows-latest`）：

1. 依赖安装（`pip install -r requirements.txt`）
2. `compileall` 语法检查
3. `unittest discover -s tests/unit`（`QT_QPA_PLATFORM=offscreen`）
4. 版本一致性校验

---

## 8. 文档路由

按任务类型路由，不要回看整段历史：

| 任务 | 优先读 |
|------|--------|
| 恢复工作 | `docs/current/STATUS.md`（顶部）→ `docs/current/DEV_LOG.md`（最近一条） |
| 发布/版本同步 | `CHANGELOG.md`（顶部）→ `version.txt` |
| 回滚/恢复 | `rollback_journal.md` → `ROLLBACK_GUIDE.md` → `restore_checkpoint.sh` |
| UI 重构轨道 | `docs/current/V38_UI_REFACTOR_PLAN.md` |
| main.py 拆分 | `docs/current/MAIN_PY_REFACTOR_PLAN.md` |
| 整改待办与历史 | `docs/current/PRIORITY_REMEDIATION_PLAN.md` |
| 背景与运行时数据结构 | `docs/current/AGENT_CONTEXT.md` |
| 打包 | `docs/packaging/README.md` |
| 贡献流程 | [CONTRIBUTING.md](CONTRIBUTING.md) |

---

## 9. 架构演进记录

| 里程碑 | 时间 | 变更 |
|--------|------|------|
| v36.5 模块化拆分 | 2026-02 | 从 main.py 提取 `privacyguard/` 包 |
| v37.0 配置持久化 | 2026-02 | SettingsDialog 接入 ConfigManager |
| v37.7.x 高级特性上行 | 2026-03 | 印章/签名检测、CJK 字符权重、检测框收缩 |
| v37.8.11 安全审计 + 重构 | 2026-08-01 | main.py 16,702→9,287 行（-44%）；P0 安全 3 项 + P1 稳定 8 项 + P2 质量 2 项；印章/签名算法外提到 `ocr/`；settings_dialog 拆分为 Mixin；统一日志框架 |

完整拆分记录：`docs/current/MAIN_PY_REFACTOR_PLAN.md`。

---

## 10. 后续优化方向

1. 每文件单独规则映射（Phase 2，per-file rule mapping）
2. 批量规则集模板管理（batch rule-set templates）
3. 替换后预览按来源筛选高亮（rule / manual / ocr）
4. `helpers.py` 57 函数按域拆分（P3-1）
5. worker 线程生命周期测试补全 + ruff 纳入 CI（P2-3）

详见 `docs/current/PRIORITY_REMEDIATION_PLAN.md` 与 `docs/current/STATUS.md`。
