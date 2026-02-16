# PrivacyApp 快速参考

**版本**: v23.3  
**更新**: 2026-02-11

---

## 重要代码位置

### main.py

| 功能 | 行号 | 说明 |
|------|------|------|
| 常量定义 | 22-40 | APP_NAME, VERSION, 默认规则等 |
| ZOOM_FIT_WIDTH | 31 | 自适应视图默认比例 (现在是 1.0) |
| SettingsDialog | 50-143 | 设置对话框 |
| SinglePageCanvas | 145-297 | 单页画布类 |
| OCRWorker | 299-433 | OCR 处理线程 |
| MainWindow.__init__ | 435-470 | 主窗口初始化 |
| MainWindow.setup_ui | 488-605 | UI 布局设置 |
| MainWindow.create_btn | 607-725 | 创建按钮方法 |
| MainWindow._get_button_style | 727-825 | 按钮样式生成 |
| MainWindow._apply_light_theme | 839-895 | 应用浅色主题 |
| MainWindow.open_pdf | 897-903 | 打开 PDF |
| MainWindow.fit_width | 915-917 | 适应宽度 |
| MainWindow.render_view | 919-931 | 渲染视图 |
| MainWindow.start_ocr | 981-987 | 开始 OCR |
| MainWindow.save_pdf | 1067-1089 | 保存 PDF |

---

## 重要常量

```python
# 窗口尺寸
MIN_WINDOW_SIZE = (900, 600)  # 最小尺寸
DEFAULT_WINDOW_SIZE = (1300, 900)  # 默认尺寸

# 缩放
ZOOM_MIN = 0.5       # 最小 50%
ZOOM_MAX = 4.0       # 最大 400%
ZOOM_FIT_WIDTH = 1.0 # 适应宽度 100% (v23.3 改为 1.0)

# 矩形
MIN_RECT_WIDTH = 5   # 最小矩形宽度

# 进度条
PROGRESS_HEIGHT = 24  # 进度条高度 (v23.3 改为 24)
```

---

## 默认规则

```python
DEFAULT_RULES = {
    "身份证号": r"(?<!\d)(\d{17}[\dXx]|\d{15})(?!\d)",
    "手机号码": r"(?<!\d)(1[3-9]\d{9})(?!\d)",
    "日期时间": r"\d{4}[年\-\.]\d{1,2}[月\-\.]\d{1,2}[日]?",
    "电子邮箱": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "银行卡号": r"(?<!\d)([1-9]\d{12,18})(?!\d)"
}
```

---

## 按钮样式类型

| 类型 | 用途 | 颜色 |
|------|------|------|
| `primary` | 主要操作 | 蓝色 #007AFF |
| `secondary` | 次要操作 | 透明 + 边框 |
| `success` | 成功操作 | 绿色 #34C759 |
| `danger` | 危险操作 | 红色 #FF3B30 |
| `icon` | 图标按钮 | 透明 |

---

## 主题常量 (theme.py)

```python
# 浅色主题
Theme.LIGHT = {
    "background": "#F5F5F7",    # 背景色
    "surface": "#FFFFFF",       # 表面色
    "primary": "#007AFF",       # 主色
    "success": "#34C759",       # 成功色
    "danger": "#FF3B30",        # 危险色
    "text": "#1D1D1F",          # 文字色
    "border": "#D1D1D6",        # 边框色
}

# 布局常量
Theme.BORDER_RADIUS = 10        # 对话框圆角
Theme.BUTTON_RADIUS = 8         # 按钮圆角
Theme.SPACING_SMALL = 6         # 小间距
Theme.SPACING_MEDIUM = 12       # 中间距
Theme.SPACING_LARGE = 20        # 大间距
```

---

## 常用修改

### 修改默认缩放
```python
# main.py 第 31 行
ZOOM_FIT_WIDTH = 1.0  # 改为你想要的值
```

### 修改窗口大小
```python
# main.py 第 453-454 行
self.setMinimumSize(900, 600)  # 最小尺寸
self.resize(1300, 900)         # 默认尺寸
```

### 修改进度条样式
```python
# main.py 第 876-895 行
def _apply_light_theme(self):
    # ... 修改进度条样式
    self.progress.setStyleSheet(...)
```

---

## 快速测试命令

```bash
# 进入项目目录
cd /Users/a49144/Desktop/临时coding/PrivacyApp

# 语法检查
python3 -m py_compile main.py

# 运行程序
python3 main.py

# 查看备份
ls -la main.py.backup_*

# 查看文件大小
ls -lh *.py *.md
```

---

## 备份文件命名规则

```
main.py.backup_v{版本号}_ui_{日期}_{时间}
```

示例:
- `main.py.backup_v23.3_ui_20260211_081152`

---

## 重要提示

1. **每次修改前创建备份**
   ```bash
   cp main.py main.py.backup_$(date +%Y%m%d_%H%M%S)
   ```

2. **修改后进行语法检查**
   ```bash
   python3 -m py_compile main.py
   ```

3. **测试所有功能**
   - PDF 导入/导出
   - 智能脱敏
   - 手动标记
   - 进度显示

---

## 版本对比

| 版本 | ZOOM_FIT_WIDTH | 进度条高度 | 主题切换 |
|------|----------------|------------|----------|
| v23.2 | 1.5 (150%) | 4px | 有 |
| v23.3 | 1.0 (100%) | 24px | 无 |

---

**下次继续开发时，先查看本文档！**
