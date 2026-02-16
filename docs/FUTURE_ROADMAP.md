# PrivacyGuard 未来开发路线图

> 本文档记录了 PrivacyGuard 项目的未来开发计划，供后续迭代参考

**创建日期**: 2026-02-15
**当前版本**: v36.0
**文档状态**: 规划中

---

## 一、Bug 修复（主要方向）

### 1.1 精确模式手动脱敏修复 [优先级: HIGH]

**问题描述**:
- 精确模式偶尔无法找到对应的 data-key 元素（失败率 <5%）
- BeautifulSoup 解析 HTML 时可能丢失文本节点信息

**代码位置**: `main.py:2507-2585` (`_highlight_exact_match` 方法)

**失败场景**:
- HTML 结构复杂，文本被分割成多个节点
- BeautifulSoup 解析时改变了原始结构
- data-key 属性在 HTML 转换过程中丢失

**修复方案**:
1. 改用 `lxml` 解析器（保留更多原始结构）
2. 添加备用查找策略（通过文本内容定位）
3. 失败时提示用户使用全局模式

**验证方法**:
- 准备包含特殊字符的 Word 测试文档
- 测试 10 次精确选择，成功率需 >95%
- 验证复杂嵌套结构（表格内的段落）

---

### 1.2 裸 except 块替换 [优先级: HIGH]

**问题描述**:
- 多处使用 `except: pass` 过于宽泛
- 可能掩盖重要错误，难以调试

**代码位置**:
| 行号 | 当前代码 | 修复方案 |
|------|----------|----------|
| 139 | `except: pass` | `except Exception as e: print(f"[清理警告] {e}")` |
| 1952 | `except: pass` | `except OSError as e: print(f"目录清理: {e}")` |
| 3388 | `except: pass` | `except (ValueError, AttributeError) as e: pass` |
| 3397 | `except: pass` | `except (ValueError, AttributeError) as e: pass` |
| 3404 | `except: pass` | `except (ValueError, AttributeError) as e: pass` |

---

### 1.3 临时文件清理增强 [优先级: MEDIUM]

**问题描述**:
- 目录清理逻辑不完整，非空目录会失败
- 异常被静默忽略

**代码位置**: `main.py:1941-1957`

**修复方案**:
1. 使用 `shutil.rmtree(..., ignore_errors=True)` 替代 `os.rmdir()`
2. 添加文件存在性检查
3. 记录清理失败的文件到日志

---

### 1.4 线程安全问题 [优先级: HIGH]

**问题描述**:
- `worker_lock = QMutex()` 创建了但未实际使用
- `active_worker` 访问无锁保护
- OCRWorker 和 WordWorker 并发执行时可能出现竞态条件

**代码位置**: `main.py:951`

**修复方案**:
```python
def start_ocr(self):
    with QMutexLocker(self.worker_lock):
        if self.active_worker is not None and self.active_worker.isRunning():
            QMessageBox.warning(self, "提示", "正在处理中，请稍候...")
            return
```

**验证方法**:
- 压力测试：快速连续点击扫描按钮 20 次
- 检查是否有线程警告或崩溃

---

## 二、性能优化（次要任务）

### 2.1 正则表达式预编译 [优先级: HIGH ROI]

**问题描述**:
- 每次循环都重新编译正则表达式
- 大文档扫描时性能损失明显

**代码位置**: `main.py:612-613` 及多处

**修复方案**:
```python
class OCRWorker(QThread):
    def __init__(self, ...):
        self.compiled_patterns = [
            re.compile(pat, re.IGNORECASE)
            for pat in self.rules + self.custom_keywords
        ]
```

**预期收益**: 扫描速度提升 15-30%

---

### 2.2 OCR 引擎生命周期管理 [优先级: MEDIUM]

**问题描述**:
- RapidOCR 创建开销大（加载 ONNX 模型）
- 频繁创建/销毁影响性能
- `gc.collect()` 在循环中调用效率低

**代码位置**: `main.py:585-664`

**修复方案**:
1. 将 OCR 引擎移到 `__init__` 作为实例变量
2. 使用单例模式延迟加载
3. 仅在窗口关闭时释放

---

### 2.3 PDF 渲染缓存 [优先级: MEDIUM]

**问题描述**:
- 每次缩放/翻页都重新渲染
- 无缓存机制

**代码位置**: `main.py:2019` (`_render_single_page`)

**修复方案**:
1. 添加 LRU 缓存（最多 5 页）
2. 使用 `QPixmapCache` 系统缓存
3. 预渲染相邻页面

**验证方法**: 翻页响应时间 <100ms

---

### 2.4 Word 处理优化 [优先级: LOW]

**问题描述**:
- BeautifulSoup 多次解析 O(n²) 复杂度
- 大量 JavaScript 注入增加 HTML 体积

**代码位置**: `main.py:2587-2599`

**修复方案**:
1. 合并多个正则表达式为单一模式
2. 使用 `re.finditer()` 一次扫描
3. 减少 BeautifulSoup 重复解析

---

### 2.5 大文档延迟分析

**现状**: 50+ 页文档处理延迟 <15 秒

**原因分析**:
- 批处理策略：每 10 页一批，每批都要重新创建 OCR 引擎
- 进度更新频率：每 50ms 发送一次信号
- 单线程 OCR 处理
- 批次间的垃圾回收开销

**优化建议**:
1. OCR 引擎持久化（避免每批重新创建）
2. 增大批处理大小（如 50 页一批）
3. 减少进度更新频率
4. 实现真正的并发 OCR 处理

---

## 三、UI/UX 改进（可选任务）

### 3.1 拖放文件支持

**当前状态**: 不支持拖放

**改进方案**:
```python
def __init__(self):
    self.setAcceptDrops(True)

def dragEnterEvent(self, event):
    if event.mimeData().hasUrls():
        event.accept()

def dropEvent(self, event):
    url = event.mimeData().urls()[0]
    file_path = url.toLocalFile()
    if file_path.endswith(('.pdf', '.docx', '.doc')):
        self._open_file(file_path)
```

---

### 3.2 扩展快捷键系统

**当前快捷键**:
- PageUp/PageDown: 翻页
- Home/End: 首页/尾页
- Ctrl/Cmd + +/-: 缩放

**建议添加**:
| 快捷键 | 功能 |
|--------|------|
| Ctrl+O | 打开文件 |
| Ctrl+S | 保存文件 |
| Ctrl+Z | 撤销 |
| Ctrl+R | 重新扫描 |
| Delete | 删除选中 |

---

### 3.3 增强进度反馈

**当前状态**: 仅显示百分比

**改进方案**:
- 添加剩余时间估算
- 显示当前处理的页码（如 "处理中: 第 15/50 页"）
- 添加取消按钮

---

### 3.4 主题系统增强

**当前状态**: 浅色/深色主题

**改进建议**:
1. 添加更多主题选项（蓝色系、绿色系）
2. 支持跟随系统主题
3. 添加主题切换平滑过渡动画

---

### 3.5 国际化支持

**当前状态**: 所有 UI 文本使用中文

**改进建议**:
1. 创建 `i18n.py` 模块
2. 使用 gettext 框架
3. 支持中英文切换

---

## 四、版本发布规划

| 版本 | 内容 | 预计时间 |
|------|------|----------|
| v36.1 | Bug 修复（阶段一） | 1-2 天 |
| v36.2 | 稳定性增强（阶段二） | +1-2 天 |
| v37.0 | 性能优化（阶段三） | +2-3 天 |
| v37.1 | UI/UX 改进（阶段四） | +1-2 天 |

**MVP（最小可行修复）**: 完成阶段一和阶段二，预计 2-4 天

---

## 五、风险评估

| 风险项 | 影响 | 可能性 | 缓解措施 |
|--------|------|--------|----------|
| 精确模式修复引入新 Bug | 高 | 中 | 充分回归测试 |
| QMutex 死锁 | 高 | 低 | 使用 QMutexLocker RAII |
| 性能优化影响稳定性 | 中 | 中 | 保留原代码作为回退 |
| OCR 引擎单例内存增长 | 中 | 低 | 添加定期清理机制 |

---

## 六、关键代码位置索引

| 功能模块 | 文件位置 |
|----------|----------|
| 精确模式高亮 | `main.py:2507-2585` |
| 全局模式高亮 | `main.py:2587-2700` |
| OCRWorker 类 | `main.py:531-673` |
| WordWorker 类 | `main.py:819-912` |
| TempFileManager | `main.py:83-140` |
| QMutex 初始化 | `main.py:951` |
| PDF 渲染 | `main.py:2019-2100` |
| Word 预览渲染 | `main.py:2275-2474` |
| 主题系统 | `theme.py` |

---

**最后更新**: 2026-02-15
**文档维护者**: Claude Code
