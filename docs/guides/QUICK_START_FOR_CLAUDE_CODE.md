# PrivacyGuard 项目 Claude Code 快速上手指南

> 本文档帮助 Claude Code 在下次开发时快速获取全局信息、理解项目进度，从而快速上手开发。

---

## 核心上下文文件

PrivacyGuard 项目已经配置了完善的上下文管理系统，Claude Code 只需读取以下关键文件即可快速理解项目：

### 必读文件（按优先级）

| 优先级 | 文件 | 内容 | 用途 |
|--------|------|------|------|
| ⭐⭐⭐ | `CLAUDE.md` | 项目架构、核心类、开发命令、关键实现细节 | Claude Code 的首要参考 |
| ⭐⭐⭐ | `docs/current/STATUS.md` | 当前版本、状态、最新修复 | 快速了解项目状态 |
| ⭐⭐ | `docs/current/DEV_LOG.md` | 详细开发日志、版本历史 | 了解开发进度 |
| ⭐⭐ | `CHANGELOG.md` | 版本更新记录 | 了解功能演进 |
| ⭐ | `config.json.template` | 配置系统结构 | 了解可配置项 |

### 推荐的首次对话 Prompt

```
请先阅读以下文件了解项目当前状态：
1. CLAUDE.md - 项目架构和开发指南
2. docs/current/STATUS.md - 当前版本状态
3. docs/current/DEV_LOG.md - 最新开发日志

然后告诉我：
- 当前版本号和项目状态
- 最近修复了什么问题
- 下一步计划做什么
```

---

## 项目关键信息速查

### 当前版本

- **版本号**: v37.5.0 (Seal Detection - OpenCV)
- **发布日期**: 2026-02-27
- **状态**: 功能完整 / 印章检测功能
- **OCR 引擎**: RapidOCR（单引擎架构，v37.4.0 移除 PaddleOCR）

### 核心架构

```
PrivacyApp/
├── main.py                 # 主程序 (~2600 行，单体架构)
├── theme.py                # 主题系统
├── config.json             # 用户配置
├── CLAUDE.md              # ⭐ Claude Code 必读
├── docs/
│   └── current/
│       ├── STATUS.md      # ⭐ 项目状态
│       ├── DEV_LOG.md     # ⭐ 开发日志
│       └── RECOVERY_GUIDE.md  # 恢复指南
├── packaging/              # 打包脚本
│   ├── windows/           # Windows 打包
│   └── macos/             # macOS 打包
└── backups/               # 版本备份
```

### 核心类

| 类名 | 用途 | 关键方法 |
|------|------|----------|
| `MainWindow` | 主 UI 控制器 | `_open_pdf`, `_open_word`, `run_ocr_scan` |
| `SinglePageCanvas` | PDF 页面渲染 | `paintEvent`, `add_manual_redaction` |
| `OCRWorker` | OCR 后台线程 | `run`, `_scan_page_ocr`, `_detect_seals` (v37.5.0) |
| `WordWorker` | Word 处理线程 | `run` |
| `WebViewBridge` | Python-JS 桥接 | `add_redaction`, `remove_redaction` |
| `ConfigManager` | 配置管理 | `get`, `set`, `reload` |

### 常用命令

```bash
# 激活虚拟环境
source venv/bin/activate  # macOS
venv\Scripts\activate     # Windows

# 运行应用
python main.py

# 语法检查
python -c "import ast; ast.parse(open('main.py').read()); print('OK')"

# 运行测试
python tests/scripts/test_stability.py

# 打包
packaging/windows/scripts/build_complete.bat  # Windows
./packaging/macos/scripts/build_complete.sh   # macOS
```

---

## 下次开发时的推荐工作流

### 步骤 1: 启动 Claude Code 并提供上下文

```bash
cd C:\Users\Admin\Desktop\claudecodehub\PrivacyApp
claude
```

### 步骤 2: 使用推荐的首次 Prompt（见上方）

### 步骤 3: 描述具体任务

```
我想要 [具体功能/修复描述]，请帮我：
1. 分析需要修改哪些文件
2. 设计实现方案
3. 编写代码
4. 测试验证
```

---

## 关键实现细节备忘

### PDF 处理流程

1. 用户打开 PDF → `MainWindow._open_pdf()`
2. 点击智能脱敏 → `MainWindow.run_ocr_scan()`
3. OCRWorker 扫描页面
4. 结果存储在 `self.page_data[page_num]`
5. 脱敏框在 `SinglePageCanvas.paintEvent()` 绘制

### Word 处理流程

1. 用户打开 Word → `MainWindow._open_word()`
2. mammoth 转换为 HTML
3. QWebEngineView 显示
4. WebViewBridge 处理交互
5. 三遍占位符替换策略避免 HTML 标签破坏

### 配置系统 (v37.0)

- JSON 配置文件：`config.json`
- 点分隔访问：`config.get("app.window.default_width")`
- 热重载：`config.reload()`

### 安全特性 (v36.2)

- 路径验证：`validate_safe_path()` 防止命令注入
- 临时文件管理：`TempFileManager` 自动清理
- 具体异常捕获：替代裸 `except Exception`

---

## 验证方法

### 功能测试

1. 打开 PDF 文件
2. 执行智能脱敏
3. 调整脱敏框
4. 保存并验证

### 打包验证

1. 运行 `build_complete.bat`
2. 解压生成的 ZIP
3. 运行 PrivacyGuard.exe
4. 测试完整功能流程

### 语法验证

```bash
python -c "import ast; ast.parse(open('main.py').read()); print('OK')"
python tests/scripts/test_stability.py
```

---

## 已知限制

| 问题 | 优先级 | 状态 |
|------|--------|------|
| 精确模式偶尔失败 (<5%) | LOW | 可接受，有全局模式备用 |
| 大文档性能延迟 (50+ 页) | LOW | 可接受 |

---

## 最近修复记录

### v37.5.0 (2026-02-27)
- 🆕 印章自动检测功能（OpenCV 实现）
- 🔧 修复：文本型 PDF 分支也执行印章检测
- 🔧 修复：config.json 缺少印章规则导致 UI 不显示复选框

### v37.4.0 (2026-02-23)
- 🗑️ 完全移除 PaddleOCR，统一使用 RapidOCR
- 代码量减少约 500+ 行

### v37.0.10 (2026-02-21)
- LibreOffice 路径检测修复
- 扫描模式配置调整（新增 1.0x 普通模式）

---

## 总结

要让 Claude Code 快速上手 PrivacyGuard 开发：

1. **始终保留 `CLAUDE.md`** - 这是 Claude Code 的核心参考文档
2. **维护 `docs/current/STATUS.md`** - 记录当前状态和最新变更
3. **更新 `docs/current/DEV_LOG.md`** - 记录每次开发的详细信息
4. **使用推荐的首次 Prompt** - 让 Claude Code 先读取关键文件

这套文档体系已经建立完善，只需按照推荐流程操作即可。
