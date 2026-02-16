# Critical 级别修复清单

**优先级**: P0 - 必须立即修复
**预计时间**: 2 天

---

## 1. 裸 except 子句修复 (2小时)

### 位置清单

| 行号 | 函数 | 当前代码 | 修复后 |
|------|------|----------|--------|
| 125 | cleanup | `except:` | `except (OSError, IOError):` |
| 180 | cleanup | `except:` | `except (OSError, IOError):` |
| 4092 | _copy_run_format | `except:` | `except (AttributeError, KeyError):` |
| 4101 | _copy_run_format | `except:` | `except (AttributeError, KeyError):` |
| 4108 | _copy_run_format | `except:` | `except (AttributeError, KeyError):` |

### 修复步骤

1. 读取每一行的上下文
2. 确定应该捕获的具体异常类型
3. 替换并添加日志记录

---

## 2. _inject_interactive_html 重构 (6小时)

### 目标

将 555 行函数拆分为 5 个小函数，每个 < 50 行。

### 拆分方案

```
原函数: _inject_interactive_html (555行)
├── _wrap_html_document (50行) - 包装成完整 HTML
├── _inject_qwebchannel (20行) - 注入 QWebChannel 脚本
├── _inject_interactive_js (300行) - 注入交互脚本
├── _inject_scroll_restore (30行) - 注入滚动恢复脚本
└── _combine_scripts (30行) - 组合所有脚本
```

### JavaScript 提取

将内嵌的 300 行 JavaScript 提取为独立字符串常量或模板文件。

---

## 3. 线程安全问题修复 (4小时)

### 问题分析

- OCRWorker 使用 `results` 字典共享数据
- 多线程写入可能导致数据竞争
- UI 更新可能不在主线程

### 修复方案

使用信号槽机制替代共享数据：

```python
# 添加新信号
result_signal = pyqtSignal(int, list)  # page_num, rects

# 在 run() 中发射信号
for i in batch:
    rects = self._scan_page(i)
    self.result_signal.emit(i, rects)
```

---

## 4. 资源泄露修复 (3小时)

### 文件句柄未关闭

| 位置 | 资源类型 | 修复方式 |
|------|----------|----------|
| 2033 | fitz.Document | try-finally |
| 782 | PIL.Image | with 语句 |
| 2944 | mammoth | 检查临时文件 |

### 修复示例

```python
# 修复前
doc = fitz.open(fname)
# ... 使用 ...
# 忘记关闭

# 修复后
doc = fitz.open(fname)
try:
    # ... 使用 ...
finally:
    doc.close()
```

---

## 验证清单

- [ ] 语法检查通过
- [ ] 所有测试通过
- [ ] 代码审查通过
- [ ] 功能测试通过

---

## 执行顺序

1. **上午**: 修复裸 except (低风险)
2. **下午**: 资源泄露修复 (中等风险)
3. **第2天上午**: 线程安全修复 (高风险，需要测试)
4. **第2天下午**: 重构 _inject_interactive_html (高风险，需要充分测试)

---

**开始时间**: 2026-02-17
**预计完成**: 2026-02-18
**负责人**: Claude
