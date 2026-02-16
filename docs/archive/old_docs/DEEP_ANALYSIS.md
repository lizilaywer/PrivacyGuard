# 🔍 PrivacyApp 深度分析报告

**分析日期：** 2026-02-09
**项目版本：** v19.4
**分析者：** Claude Code

---

## 📊 项目现状概览

### ✅ 已完成功能
- PDF 导入和渲染
- OCR 智能脱敏（支持文字版和扫描版）
- 手动绘制矩形框
- 双页模式
- 缩放功能（滚轮和按钮）
- 导出脱敏后的 PDF
- 黑色/白色标记切换

### ❌ 核心问题
**右键点击删除功能完全失效**

---

## 🔬 根本原因分析

### 问题1: 右键点击无响应

#### 症状
```
✅ 鼠标悬停在涂黑区域时能变成手型
❌ 右键点击完全没有日志输出
❌ contextMenuEvent 未触发
❌ mousePressEvent 中右键分支未执行
```

#### 根本原因

**1. Qt 事件层次结构问题**
```
QScrollArea (滚动区域)
└── canvas_container (QWidget 容器)
    └── QHBoxLayout (布局管理器)
        └── SinglePageCanvas (QLabel) ← 右键事件被拦截
```

**问题点：**
- `QScrollArea` 默认会拦截某些鼠标事件
- `QLabel` 对于右键菜单有特殊处理机制
- 即使设置了 `PreventContextMenu`，事件可能仍未到达 canvas

**2. v19.4 修复为何失败？**
```python
# v19.4 的修复
self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

def contextMenuEvent(self, event):
    # 这个方法根本没有被调用！
```

**失败原因：**
- `PreventContextMenu` 只是阻止显示菜单
- 但不保证事件会传递到 `contextMenuEvent`
- 在复杂的控件层次中，事件可能被父组件拦截

#### 验证证据

从 `app_debug.log` 分析：
```
✓ 有左键点击日志（重复4次）
✗ 没有右键点击日志
✗ 没有 "contextMenuEvent 触发！" 日志
✓ 鼠标悬停能变手型（说明位置检测正确）
```

**结论：** 右键点击事件根本没到达 `SinglePageCanvas`

---

### 问题2: 左键点击触发4次

#### 症状
```
[DEBUG] mousePressEvent: button=LeftButton
[DEBUG] 左键按下，开始绘制
[DEBUG] 左键释放，结束绘制
[DEBUG] mousePressEvent: button=LeftButton  ← 重复
[DEBUG] 左键按下，开始绘制
...
```

#### 根本原因
**事件冒泡 (Event Bubbling)**

在 Qt 的父子控件关系中：
1. 事件先到达子控件
2. 如果子控件不 `accept()`，事件会向上传播
3. 父控件可能再次处理事件

**可能的原因：**
- `QHBoxLayout` 重复传递事件
- `QScrollArea` 在处理后再次传递
- 事件过滤器重复触发

---

### 问题3: "Unknown property filter"

#### 症状
```
Unknown property filter
Unknown property filter
...（重复47次）
```

#### 根本原因
**Qt 样式表与 macOS 不兼容**

```python
# main.py 第590行
btn.setStyleSheet(f"""
    QPushButton {{
        ...
    }}
    QPushButton:hover {{ filter: brightness(90%); }}  ← macOS 不支持
    """)
```

#### 影响
- ❌ 无功能影响
- ✅ 仅控制台警告
- 📊 影响日志可读性

---

## 🛠️ 修复方案

### 方案A: 事件过滤器（推荐）

**优点：**
- 不改变现有架构
- 可以精确控制事件流
- 便于调试

**实现：**
```python
class MainWindow(QMainWindow):
    def __init__(self):
        # ...
        self.scroll.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                # 手动传递给 canvas
                mapped_pos = self.scroll.mapFromScene(event.pos())
                self.canvas_left.handle_right_click(mapped_pos)
                return True  # 阻止默认处理
        return super().eventFilter(obj, event)
```

---

### 方案B: 改用 QWidget 作为画布

**优点：**
- QWidget 的事件处理更直接
- 没有 QLabel 的特殊行为

**缺点：**
- 需要重写绘制逻辑
- 工作量较大

---

### 方案C: 重写 mousePressEvent 和 event()

**核心思路：**
```python
class SinglePageCanvas(QLabel):
    def event(self, event):
        # 捕获所有事件类型
        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                self.contextMenuEvent(event)
                return True
        return super().event(event)
```

---

### 方案D: 使用 eventFilter + 全局监控

**最彻底的方案：**
```python
class SinglePageCanvas(QLabel):
    def __init__(self, ...):
        super().__init__(parent)
        self.installEventFilter(self)  # 监控自己的事件

    def eventFilter(self, obj, event):
        if obj == self and event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                print("[DEBUG] eventFilter 捕获右键点击")
                self.handle_right_click(event.pos())
                return True
        return super().eventFilter(obj, event)
```

---

## 📋 推荐实施步骤

### 第一步: 诊断（已完成）
- ✅ 分析日志
- ✅ 识别问题
- ✅ 确定根本原因

### 第二步: 实施方案D（推荐）
1. 在 `SinglePageCanvas` 中安装事件过滤器
2. 在 `eventFilter` 中捕获右键点击
3. 调用现有的删除逻辑
4. 添加详细日志

### 第三步: 测试
1. 验证右键点击是否响应
2. 验证删除功能是否正常
3. 验证其他功能是否受影响

### 第四步: 修复样式警告
移除 `filter` 属性或使用兼容方案

---

## 🎯 优先级

| 问题 | 优先级 | 复杂度 | 预计时间 |
|------|--------|--------|----------|
| 右键点击修复 | 🔴 高 | 中 | 30分钟 |
| 左键重复点击 | 🟡 中 | 低 | 15分钟 |
| 样式警告修复 | 🟢 低 | 低 | 5分钟 |

---

## 💡 其他发现

### 代码质量
- ✅ 异常处理完善
- ✅ 资源管理正确
- ✅ 调试日志详细
- ✅ 备份机制完整

### 架构评估
- ✅ 模块化良好
- ✅ 信号/槽使用正确
- ⚠️ 事件处理需要优化
- ✅ OCR 线程安全

---

## 📝 建议

### 短期（本次）
1. 修复右键点击功能
2. 减少左键重复触发
3. 修复样式警告

### 中期
1. 添加单元测试
2. 使用 `logging` 模块替代 `print`
3. 添加类型注解

### 长期
1. 重构事件处理架构
2. 添加性能监控
3. 用户设置持久化

---

**下一步：** 实施 v19.5 修复方案（方案D）
