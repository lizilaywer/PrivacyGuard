# PrivacyGuard 脱敏卫士 - 全面修复与优化计划

**文档版本**: v1.0
**创建日期**: 2026-02-16
**计划周期**: 4 周

---

## 📊 项目现状概览

### 已完成的工作 ✅

| 版本 | 日期 | 内容 |
|------|------|------|
| v36.3 | 2026-02-16 | Word 文档显示空白修复 (热修复) |
| v36.2 | 2026-02-16 | 安全加固 (路径验证、错误处理、临时文件管理) |
| v36.1 | 2026-02-16 | FeedbackDialog 优化、LibreOffice 中文路径修复 |
| v36.0 | 2026-02-14 | Windows 深色模式修复、正式发布 |

### 代码统计

- **总行数**: 4,121 行
- **主要类**: 10 个
- **函数数量**: 120+
- **问题数量**: 40+ (按优先级分类)

---

## 🎯 修复计划总览

### 阶段划分

```
第 1 周: 紧急修复 (Critical - 稳定性)
第 2 周: 架构重构 (High - 可维护性)
第 3 周: 性能优化 (Medium - 效率)
第 4 周: 代码质量 (Low - 规范性)
```

---

## 📋 第 1 周：紧急修复 (Critical)

### 1.1 修复裸 except 子句 [P0]

**位置**:
- `main.py:125` (TempFileManager.cleanup)
- `main.py:180` (TempFileManager.cleanup)
- `main.py:4092` (_copy_run_format - 未使用的方法)
- `main.py:4101` (_copy_run_format)
- `main.py:4108` (_copy_run_format)

**问题**: 裸 `except:` 会捕获所有异常，包括 `SystemExit` 和 `KeyboardInterrupt`，导致程序无法正常退出。

**修复方案**:
```python
# 修复前
try:
    os.remove(f)
except:
    pass

# 修复后
try:
    os.remove(f)
except (OSError, IOError) as e:
    print(f"[清理] 删除文件失败: {f}, 错误: {e}")
```

**预计时间**: 2 小时
**验证**: 语法检查 + 运行测试

---

### 1.2 重构 _inject_interactive_html 巨型函数 [P0]

**位置**: `main.py:3371-3920` (555 行)

**问题**: 函数过长，包含大量内嵌 JavaScript，难以维护和测试。

**重构方案**:

```
_inject_interactive_html/
├── _ensure_html_document()     # 确保完整 HTML 结构
├── _inject_qwebchannel_js()    # 注入 QWebChannel
├── _inject_context_menu_js()   # 注入右键菜单脚本
├── _inject_scroll_restore_js() # 注入滚动恢复脚本
└── _get_base_styles()          # 获取基础 CSS
```

**新结构**:
```python
def _inject_interactive_html(self, html: str, scroll_restore: str = '') -> str:
    """注入 JavaScript 交互逻辑用于右键菜单和脱敏操作."""
    html = self._ensure_html_document(html)
    html = self._inject_qwebchannel_js(html)
    html = self._inject_context_menu_js(html)
    html = self._inject_scroll_restore_js(html, scroll_restore)
    return html
```

**预计时间**: 1 天
**验证**: 功能测试（右键菜单、滚动恢复、脱敏功能）

---

### 1.3 修复 OCRWorker 线程安全问题 [P0]

**位置**: `main.py:1041-1150`

**问题**:
- `results` 字典在多线程中共享，存在数据竞争
- UI 更新可能不在主线程执行

**修复方案**:
```python
class OCRWorker(QThread):
    # 现有信号...
    result_signal = pyqtSignal(int, list)  # page_num, rects

    def run(self):
        # ... 使用 result_signal 逐页发送结果
        for i in batch:
            rects = self._scan_page(i)
            self.result_signal.emit(i, rects)  # 安全地发送到主线程
```

**预计时间**: 4 小时
**验证**: 多文件 OCR 测试

---

### 1.4 修复资源泄露问题 [P0]

**位置**:
- `main.py:2033` - PDF 文档未正确关闭
- `main.py:782` - 图像资源未释放
- `main.py:2944` - mammoth 临时文件

**修复方案**:
```python
# PDF 文档使用上下文管理器
try:
    doc = fitz.open(fname)
    # ... 使用 doc
finally:
    doc.close()

# 图像资源使用 with 语句
with Image.open(img_path) as img:
    # ... 使用 img
```

**预计时间**: 3 小时
**验证**: 资源监控工具检查

---

## 📋 第 2 周：架构重构 (High)

### 2.1 拆分 MainWindow God Class [P1]

**现状**: MainWindow 类 2730 行，承担过多职责

**重构方案**:

```
controllers/
├── __init__.py
├── pdf_controller.py      # PDF 相关操作
├── word_controller.py     # Word 相关操作
└── file_converter.py      # 格式转换

ui/
├── __init__.py
├── main_window.py         # 主窗口（精简版）
├── canvas.py              # 单页画布
└── dialogs.py             # 对话框

utils/
├── __init__.py
├── temp_manager.py        # 临时文件管理
├── validators.py          # 验证函数
└── constants.py           # 常量定义
```

**预计时间**: 3 天
**验证**: 所有功能回归测试

---

### 2.2 重构过长函数 [P1]

| 函数 | 当前行数 | 目标 | 拆分方案 |
|------|---------|------|----------|
| `__init__` | 244 | <50 | 拆分为 setup_ui, setup_controller, setup_signals |
| `setup_ui` | 167 | <50 | 拆分为 setup_toolbar, setup_canvas, setup_progress |
| `render_word_preview` | 140 | <50 | 拆分为 convert_to_html, highlight_sensitive, inject_scripts |
| `_convert_with_libreoffice` | 132 | <50 | 使用策略模式，分离重试逻辑 |
| `_highlight_sensitive_info` | 126 | <50 | 提取辅助函数，减少嵌套 |

**预计时间**: 2 天
**验证**: 功能测试

---

### 2.3 简化复杂嵌套 [P1]

**位置**: `_highlight_sensitive_info` (6 层嵌套)

**修复方案**:
```python
def _highlight_sensitive_info(self, html: str) -> str:
    """高亮敏感信息 - 使用早期返回减少嵌套."""
    if not self.sensitive_words:
        return html

    for key, word_list in self.sensitive_words.items():
        html = self._highlight_word_group(html, key, word_list)

    return html

def _highlight_word_group(self, html: str, key: str, word_list: list) -> str:
    """高亮一组敏感词."""
    for word_info in word_list:
        if not self._should_highlight(word_info):
            continue

        html = self._apply_highlight(html, key, word_info)

    return html
```

**预计时间**: 1 天
**验证**: 高亮功能测试

---

## 📋 第 3 周：性能优化 (Medium)

### 3.1 优化 OCR 性能 [P2]

**位置**: `main.py:1054`, `main.py:1100-1110`

**优化方案**:
```python
def run(self):
    # 1. 预编译正则表达式
    all_patterns = [re.compile(p, re.IGNORECASE) for p in self.rules + self.custom_keywords]

    # 2. 批量处理改为流式处理
    for page_num in range(self.total_pages):
        if self._cancelled:
            break

        rects = self._scan_page_streaming(page_num, all_patterns)
        self.result_signal.emit(page_num, rects)

        # 每5页释放一次内存
        if page_num % 5 == 0:
            gc.collect()
```

**预计时间**: 1 天
**验证**: 性能基准测试

---

### 3.2 优化矩形去重算法 [P2]

**位置**: `main.py:2860-2880`

**当前复杂度**: O(n²)
**优化方案**: 使用空间索引
```python
def _deduplicate_rects(self, rects: list) -> list:
    """使用网格分桶优化去重."""
    if len(rects) < 100:  # 小列表使用简单算法
        return self._simple_dedup(rects)

    # 大列表使用网格索引
    grid = defaultdict(list)
    cell_size = 50  # 网格单元大小

    for rect in rects:
        key = (int(rect.x() / cell_size), int(rect.y() / cell_size))
        grid[key].append(rect)

    # 只在相邻网格中检查重叠
    deduped = []
    for rect in rects:
        if not self._has_overlap_in_grid(rect, grid, cell_size):
            deduped.append(rect)

    return deduped
```

**预计时间**: 4 小时
**验证**: 大文档 OCR 测试

---

### 3.3 缓存正则表达式 [P2]

**位置**: `main.py:1200`

**优化方案**:
```python
class MainWindow:
    def __init__(self):
        # ...
        self._pattern_cache = {}

    def _get_cached_pattern(self, text: str) -> re.Pattern:
        """获取缓存的正则表达式."""
        if text not in self._pattern_cache:
            self._pattern_cache[text] = re.compile(re.escape(text))
        return self._pattern_cache[text]
```

**预计时间**: 2 小时
**验证**: 性能分析

---

### 3.4 大文档分页处理 [P2]

**位置**: Word 预览渲染

**优化方案**:
```python
def render_word_preview(self, chunk_size: int = 1000):
    """分页渲染 Word 预览."""
    # 1. 先渲染前 chunk_size 个段落
    # 2. 后台线程加载剩余段落
    # 3. 使用虚拟滚动（virtual scrolling）
```

**预计时间**: 1 天
**验证**: 大 Word 文档测试

---

## 📋 第 4 周：代码质量 (Low)

### 4.1 提取硬编码配置 [P3]

**位置**: 多处

**新建文件**: `config.py`
```python
"""全局配置."""

class AppConfig:
    NAME = "PrivacyGuard 脱敏卫士"
    VERSION = "36.4"

class UIConfig:
    MIN_RECT_WIDTH = 5
    PROGRESS_UPDATE_INTERVAL = 0.05  # 秒
    ZOOM_MIN = 0.5
    ZOOM_MAX = 4.0

class OCRConfig:
    BATCH_SIZE = 10
    TIMEOUT = 60  # 秒

class ConversionConfig:
    LIBREOFFICE_TIMEOUT = 60
    ANTIWORD_TIMEOUT = 30

class SecurityConfig:
    ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg']
    DANGEROUS_CHARS = [';', '|', '&', '$', '`', '$(', '>', '<']
```

**预计时间**: 4 小时
**验证**: 所有功能正常

---

### 4.2 消除重复代码 [P3]

**位置**:
- 样式定义重复（3 处）
- 路径验证重复（2 处）
- 导入重复（多处）

**修复方案**:
```python
# 创建样式构建器
class StyleSheetBuilder:
    @staticmethod
    def group_box(theme: dict) -> str:
        return f"""
        QGroupBox {{
            font-weight: bold;
            color: {theme['text']};
            border: 1px solid {theme['border']};
            border-radius: 8px;
            margin-top: 12px;
            padding: 12px;
        }}
        """

# 创建路径验证装饰器
def require_safe_path(func):
    @wraps(func)
    def wrapper(self, path, *args, **kwargs):
        is_safe, error_msg = validate_safe_path(path)
        if not is_safe:
            raise ConversionError("路径不安全", error_msg)
        return func(self, path, *args, **kwargs)
    return wrapper
```

**预计时间**: 1 天
**验证**: 代码审查

---

### 4.3 删除未使用代码 [P3]

**位置**: `_copy_run_format` 方法 (4072-4115 行)

**操作**:
1. 确认方法未被调用
2. 删除方法
3. 检查其他未使用的导入和变量

**预计时间**: 2 小时
**验证**: 静态分析工具

---

### 4.4 添加类型注解 [P3]

**优先级函数**:
```python
def validate_safe_path(path: str, allowed_extensions: list[str] = None) -> tuple[bool, str]:
    ...

def _highlight_sensitive_info(self, html: str) -> str:
    ...
```

**预计时间**: 1 天
**验证**: mypy 静态检查

---

### 4.5 增强临时文件安全 [P3]

**位置**: `TempFileManager`

**优化方案**:
```python
def create_temp_file(self, suffix: str = '', content: bytes = None) -> str:
    """创建临时文件，设置严格权限."""
    temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)

    # 设置严格权限（仅所有者可读写）
    os.chmod(temp.name, 0o600)

    if content:
        temp.write(content)
    temp.close()

    self.temp_files.append(temp.name)
    return temp.name

def cleanup(self):
    """清理临时文件 - 避免 TOCTOU 竞态."""
    for f in self.temp_files:
        try:
            os.remove(f)  # 直接删除，不存在会抛出异常
        except FileNotFoundError:
            pass  # 文件已被删除
        except (OSError, IOError) as e:
            print(f"[清理] 删除失败: {f}, 错误: {e}")
```

**预计时间**: 2 小时
**验证**: 安全测试

---

## 📅 详细时间表

### 第 1 周：紧急修复

| 日期 | 任务 | 负责人 | 产出 |
|------|------|--------|------|
| 周一 | 修复裸 except | Claude | PR #1 |
| 周二 | 重构 _inject_interactive_html | Claude | PR #2 |
| 周三 | 修复线程安全问题 | Claude | PR #3 |
| 周四 | 修复资源泄露 | Claude | PR #4 |
| 周五 | 代码审查 + 测试 | Claude | 测试报告 |

### 第 2 周：架构重构

| 日期 | 任务 | 负责人 | 产出 |
|------|------|--------|------|
| 周一 | 拆分 MainWindow - 第 1 部分 | Claude | PR #5 |
| 周二 | 拆分 MainWindow - 第 2 部分 | Claude | PR #6 |
| 周三 | 重构过长函数 | Claude | PR #7 |
| 周四 | 简化复杂嵌套 | Claude | PR #8 |
| 周五 | 集成测试 | Claude | 测试报告 |

### 第 3 周：性能优化

| 日期 | 任务 | 负责人 | 产出 |
|------|------|--------|------|
| 周一 | OCR 性能优化 | Claude | PR #9 |
| 周二 | 矩形去重优化 | Claude | PR #10 |
| 周三 | 缓存正则表达式 | Claude | PR #11 |
| 周四 | 大文档分页 | Claude | PR #12 |
| 周五 | 性能基准测试 | Claude | 性能报告 |

### 第 4 周：代码质量

| 日期 | 任务 | 负责人 | 产出 |
|------|------|--------|------|
| 周一 | 提取硬编码配置 | Claude | PR #13 |
| 周二 | 消除重复代码 | Claude | PR #14 |
| 周三 | 删除未使用代码 | Claude | PR #15 |
| 周四 | 添加类型注解 | Claude | PR #16 |
| 周五 | 增强临时文件安全 | Claude | PR #17 |

---

## 🧪 测试计划

### 单元测试

```python
# tests/unit/test_validators.py
def test_validate_safe_path():
    assert validate_safe_path('/safe/path.pdf')[0] is True
    assert validate_safe_path('/unsafe/path;rm -rf')[0] is False

# tests/unit/test_temp_manager.py
def test_temp_file_cleanup():
    manager = TempFileManager()
    temp_file = manager.create_temp_file()
    assert os.path.exists(temp_file)
    manager.cleanup()
    assert not os.path.exists(temp_file)
```

### 集成测试

```python
# tests/integration/test_word_preview.py
def test_word_preview_with_large_images():
    # 打开大图片 Word 文档
    # 验证内容正常显示
    pass

def test_ocr_with_cancellation():
    # 启动 OCR
    # 点击取消
    # 验证资源正确释放
    pass
```

### 性能测试

```python
# tests/performance/test_ocr_speed.py
def test_ocr_100_pages():
    # 测试 100 页 PDF 的 OCR 速度
    # 基准: < 30 秒
    pass
```

---

## 📊 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 重构引入新 Bug | 中 | 高 | 完善的测试覆盖，小步提交 |
| 性能优化无效 | 低 | 中 | 基准测试，量化指标 |
| 进度延误 | 中 | 中 | 每周检查点，优先级调整 |
| 兼容性问题 | 低 | 高 | 多平台测试，回滚计划 |

---

## 🔄 回滚计划

每个 PR 合并前创建备份：
```bash
# 创建备份
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp main.py "backups/v36.4_repair_${TIMESTAMP}/main.py.backup"

# 如果需要回滚
cp "backups/v36.4_repair_${TIMESTAMP}/main.py.backup" main.py
```

---

## 📈 成功指标

### 定量指标

| 指标 | 当前 | 目标 | 测量方式 |
|------|------|------|----------|
| 代码行数 | 4121 | < 3500 | cloc |
| 平均函数长度 | 35 | < 20 | radon |
| 裸 except 数量 | 5 | 0 | grep |
| 单元测试覆盖率 | 0% | > 30% | pytest-cov |
| OCR 速度 (100页) | ? | < 30s | 计时 |

### 定性指标

- [ ] 代码可读性显著提升
- [ ] 新功能开发效率提高
- [ ] Bug 修复时间缩短
- [ ] 团队协作更顺畅

---

## 📝 待办清单

### 立即执行 (本周)
- [ ] 创建 feature 分支
- [ ] 修复裸 except 子句
- [ ] 创建详细测试用例

### 短期 (下周)
- [ ] 重构 MainWindow
- [ ] 拆分过长函数

### 中期 (本月)
- [ ] 性能优化
- [ ] 添加测试覆盖

### 长期 (下月)
- [ ] 持续集成
- [ ] 自动化测试

---

**最后更新**: 2026-02-16
**下次审查**: 2026-02-23
**文档维护**: Claude
