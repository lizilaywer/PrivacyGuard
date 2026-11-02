# PrivacyApp 项目深度审查报告

> 生成日期：2026-02-17
> 审查工具：Claude Code (Claude Opus 4.6)
> 项目版本：v36.4 - Code Refactoring

---

## 一、项目概况

| 项目属性 | 详情 |
|---------|------|
| **名称** | PrivacyGuard 脱敏卫士 |
| **版本** | v36.4 - Code Refactoring |
| **主文件** | main.py (~4177行) |
| **技术栈** | Python 3.11 + PyQt6 + PyMuPDF + RapidOCR |
| **架构** | 单体架构 (Monolithic) |

---

## 二、严重问题 (需要立即修复)

**未发现严重的安全漏洞或致命错误。**

项目在 v36.2 版本已经进行了安全加固，包括：
- [x] 路径验证防止命令注入 (`validate_safe_path`)
- [x] 临时文件自动清理 (`TempFileManager`)
- [x] 具体异常类型处理（已替换裸 `except Exception`）
- [x] JavaScript XSS 防护（使用 DOM 方法替代 innerHTML）

---

## 三、中等问题 (建议修复)

### 1. 单体架构导致维护困难

- `main.py` 约 4177 行代码，所有功能集中在一个文件
- 包含 UI、业务逻辑、线程处理、文件操作等多种职责

**建议**：考虑模块化拆分：

```
PrivacyApp/
├── main.py           # 入口文件
├── ui/
│   ├── main_window.py
│   ├── dialogs.py
│   └── theme.py
├── workers/
│   ├── ocr_worker.py
│   └── word_worker.py
├── utils/
│   ├── file_manager.py
│   └── validators.py
└── core/
    ├── pdf_handler.py
    └── word_handler.py
```

### 2. 依赖版本过于严格

`requirements.txt` 中所有依赖都锁定了精确版本，可能导致：
- 无法获取安全更新
- 在不同环境下的兼容性问题

**建议**：使用版本范围：

```txt
PyQt6>=6.10.0,<7.0.0
PyMuPDF>=1.25.0
python-docx>=1.0.0
```

### 3. 线程安全问题潜在风险

虽然 v36.4 已改用信号槽机制，但以下位置仍需注意：
- `main.py:1199-1220` - `add_manual_redaction_global` 中的字典遍历
- `main.py:1257-1268` - `remove_global_redaction` 中的列表修改

**建议**：考虑使用 `QMutexLocker` 保护共享数据访问。

### 4. 资源释放不完整

`main.py:2549-2551` - 打开新 PDF 前关闭旧文档：

```python
if self.doc:
    self.doc.close()
    self.doc = None
```

但如果用户频繁切换文件，`page_data` 字典中的旧数据未清理。

---

## 四、轻微问题 (可优化)

### 1. 代码风格不一致

- 变量命名混用：`lbl_page` (下划线) vs `canvas_left` (下划线)
- 方法命名：`_on_ocr_finished_safe` vs `ocr_finished` (私有/公有不统一)

### 2. 异常处理可改进

`main.py:1350-1352` - WordWorker 中的异常处理：

```python
except Exception as e:
    print(f"Word扫描错误: {e}")
    self.finished_signal.emit(self.word_data)
```

**建议**：使用日志模块替代 `print`，并记录堆栈信息。

### 3. JavaScript 代码过长

`main.py:1392-1904` - `_INTERACTIVE_JS_CODE` 约 512 行 JavaScript 代码嵌入 Python 字符串中，难以维护和调试。

**建议**：将 JavaScript 代码提取到独立的 `.js` 文件中。

### 4. 硬编码字符串

- `main.py:406` - 反馈 URL 硬编码
- `main.py:671` - 使用手册 URL 硬编码
- 多处 UI 文本硬编码（国际化困难）

### 5. 缺少类型注解

大部分方法没有类型注解，例如：

```python
def _deduplicate_rects(self, rects):  # 缺少类型注解
```

建议改为：

```python
def _deduplicate_rects(self, rects: list[QRectF]) -> list[QRectF]:
```

---

## 五、代码亮点

### 1. 安全设计优秀

```python
# main.py:184-246 - 路径验证函数设计完善
def validate_safe_path(path, allowed_extensions=None):
    # 命令注入防护
    dangerous_chars = [';', '|', '&', '$', '`', '$(', '>', '<', '\n', '\r']
    # 路径遍历防护
    # 扩展名白名单
```

### 2. 临时文件管理设计良好

```python
# main.py:85-182 - TempFileManager
# 使用 atexit 确保清理
# 类级别注册表追踪所有实例
```

### 3. 线程安全改进 (v36.4)

```python
# main.py:3384-3399 - 逐页发送结果，避免共享字典
self.worker.page_result_signal.connect(self._on_ocr_page_result)
```

### 4. 用户体验考虑周到

- 滚轮翻页支持（边缘检测）
- 键盘快捷键支持
- 取消扫描保留部分结果
- 滚动位置持久化

### 5. 文档完善

- `CLAUDE.md` 提供了详细的开发指南
- 代码注释详细，中英文结合
- 有完整的版本变更记录

---

## 六、代码质量评分

| 评估项 | 评分 | 说明 |
|-------|------|------|
| **安全性** | 9/10 | 安全措施完善，无明显漏洞 |
| **可维护性** | 6/10 | 单体架构，代码量大 |
| **健壮性** | 8/10 | 异常处理完善，线程安全改进 |
| **性能** | 7/10 | 有批处理优化，大文档支持良好 |
| **用户体验** | 9/10 | 功能完整，交互友好 |
| **文档** | 8/10 | 注释详细，开发文档完善 |

**综合评分：7.8/10** - 生产可用，有改进空间

---

## 七、改进建议优先级

| 优先级 | 建议 | 状态 |
|-------|------|------|
| **P0 (立即)** | 无严重问题 | - |
| **P1 (短期)** | 1. 添加日志系统替代 print | 待执行 |
| | 2. 修复资源释放不完整的问题 | 待执行 |
| **P2 (中期)** | 1. 模块化拆分代码 | 待执行 |
| | 2. 提取 JavaScript 到独立文件 | 待执行 |
| | 3. 添加类型注解 | 待执行 |
| **P3 (长期)** | 1. 国际化支持 | 待执行 |
| | 2. 单元测试覆盖 | 待执行 |
| | 3. CI/CD 集成 | 待执行 |

---

## 八、详细代码位置索引

### 需要关注的代码位置

| 文件 | 行号 | 问题描述 |
|-----|------|---------|
| main.py | 1199-1220 | 字典遍历时的线程安全 |
| main.py | 1257-1268 | 列表修改时的线程安全 |
| main.py | 1350-1352 | 异常处理需改进 |
| main.py | 1392-1904 | JavaScript 代码过长 |
| main.py | 2549-2551 | 资源释放不完整 |

### 优秀代码示例

| 文件 | 行号 | 说明 |
|-----|------|------|
| main.py | 85-182 | TempFileManager 设计优秀 |
| main.py | 184-246 | 路径验证安全设计 |
| main.py | 3384-3399 | 线程安全信号机制 |

---

## 九、结论

**PrivacyApp 是一个功能完善、设计合理的文档脱敏工具。** 代码质量较高，安全措施到位，适合生产环境使用。主要改进方向是模块化重构，以提高长期可维护性。

---

## 十、执行记录

> 此部分用于记录改进建议的执行情况

| 日期 | 执行内容 | 结果 |
|-----|---------|------|
| - | - | - |

---

*本报告由 Claude Code 自动生成，供开发参考使用。*
