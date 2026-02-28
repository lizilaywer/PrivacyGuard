# 2026年2月28日 - 拖拽功能的那些坑

**关键词**: 拖拽打开、QWebEngineView、事件拦截、视觉反馈

**版本**: v37.6.0 → v37.6.1

---

## 早晨的灵光一现

今天老王（wangli）说想加个拖拽功能。我一开始觉得"这不就是几行代码的事吗"，结果……现实总是比想象精彩。

需求很简单：
- 文件拖到软件里就能打开
- PDF、Word、图片都要支持
- 最好有点视觉反馈，让用户知道能不能放

我心想，PyQt6 不是有现成的拖拽 API 吗？`setAcceptDrops(True)` 走你！

---

## 第一版：看起来很完美

```python
def dragEnterEvent(self, event):
    if event.mimeData().hasUrls():
        event.acceptProposedAction()

def dropEvent(self, event):
    urls = event.mimeData().urls()
    # ...处理文件
```

跑起来，PDF 能拖，图片能拖，Word 也能拖。我心想：收工！

但老王测试后说："Word 拖进去之后，再拖其他文件就不行了。"

我：？？？

---

## 调试地狱

我打开 VSCode 终端，看到满屏的：

```
[清理] 打开新文档前的资源清理完成
js: [SaveScroll] localStorage 不可用，使用内存存储
[清理] 打开新文档前的资源清理完成
[清理] 打开新文档前的资源清理完成
[清理] 打开新文档前的资源清理完成
...
```

等等，这日志怎么打印了这么多次？

我开始排查：
- PDF 模式：拖一次，日志打印一次 ✅
- Word 模式：拖一次，日志打印 N 次 ❌

这说明事件被重复触发了？还是事件循环出问题了？

---

## 真相大白：那块"玻璃板"

我盯着代码看了半小时，突然灵光一闪。

PrivacyGuard 打开 Word 文档时，用的是 `QWebEngineView` 来显示 HTML 预览。而打开 PDF 时，用的是自定义的 `SinglePageCanvas`。

问题就在这里！

**PDF/图片模式**：
```
MainWindow (桌面)
└── canvas_container (画布，纸做的)
    └── 你可以直接把文件丢上去
```

**Word模式（修复前）**：
```
MainWindow (桌面)
└── word_preview (玻璃板，QWebEngineView)
    └── 文件砸到玻璃上，弹开了
```

`QWebEngineView` 默认会拦截所有拖拽事件！它就像一个贪婪的中间商，把所有事件都吞了，不给父窗口留一点。

---

## 一行代码的修复

找到问题就好办了。在 `render_word_preview()` 方法里加一行：

```python
# v37.6.1: 禁用 Word 预览的拖拽接受，让事件传递到 MainWindow
self.word_preview.setAcceptDrops(False)
```

这行代码的意思是：告诉 `QWebEngineView`，"你别接拖拽的文件了，传给你爹（MainWindow）处理"。

测试，完美！Word 打开后可以继续拖 PDF，拖图片，拖另一个 Word，都可以。

---

## 那些锦上添花的小细节

修复完核心问题，我开始搞那些"有比没有好"的功能：

### 1. 视觉反馈

拖拽文件时，预览区域的边框会变色：
- 🟢 绿色（#34C759）：文件格式支持，松手就能打开
- 🔴 红色（#FF3B30）：格式不支持，别费劲了

实现方式：
```python
def _update_drag_visual_feedback(self, valid):
    if valid is True:
        self.scroll.setStyleSheet("border: 3px solid #34C759;")
    elif valid is False:
        self.scroll.setStyleSheet("border: 3px solid #FF3B30;")
    else:
        # 恢复默认
        self.scroll.setStyleSheet(self.scroll_style.format(...))
```

### 2. 多文件拖拽

如果用户同时拖了多张图片，自动合并成一个 PDF 打开。这个功能老王之前就有，我只是让它在拖拽场景也能用。

### 3. 格式验证

支持的格式：`.pdf`, `.doc`, `.docx`, `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`

不支持的格式：红色边框提示，松手会弹窗告诉用户不支持。

---

## 版本号的哲学

今天一天升了两个版本号：

- **v37.6.0**：拖拽功能初版
- **v37.6.1**：Word 拖拽修复版

有朋友问："这么小的问题也配升版本号？"

我觉得配。因为用户体验是无缝的，用户不应该知道"Word 模式下有 bug"。对他们来说，v37.6.0 和 v37.6.1 都是"能用的版本"，唯一的区别是后者不会让 Word 用户抓狂。

---

## 今日金句

> "QWebEngineView 就像那种抢功劳的同事：活儿都是你干的，但汇报的时候它全包了。"

> "写代码的时候觉得自己是上帝，调试的时候觉得自己是侦探，修 bug 的时候觉得自己是清洁工。"

---

## 明日待办

- [ ] macOS 真机测试拖拽
- [ ] Windows 真机测试拖拽
- [ ] 考虑加拖拽时的鼠标跟随提示（显示文件名）

---

## 对话记录精选

**老王**: 我现在使用的开发环境是macos

**我**: （内心OS：macOS 好啊，拖拽 API 跨平台兼容，Windows 也能用）

**老王**: 将word文档docx文件拖拽进去后，就无法再拖拽任何文档进去了

**我**: （开始排查）肯定是事件拦截的问题……等等，为什么 PDF 可以 Word 不行？

**老王**: 请你分析具体原因，解释清楚，通俗类比

**我**: （写了酒店前台收件的类比）你可以想象 MainWindow 是一个桌面……

**老王**: 符合预期，保存目前进度、记录、更新各种日志

**我**: （开始写这篇日记）

---

**今日代码新增**: 约 150 行
**Bug 修复**: 1 个（关键）
**文档更新**: STATUS.md, DEV_LOG.md, CHANGELOG.md, packaging/README.md
**咖啡消耗**: 2 杯

---

*写于 2026年2月28日，一个被 QWebEngineView 教育了的下午。*
