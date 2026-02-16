# PrivacyGuard v36.2 安全加固说明

**版本**: v36.2
**日期**: 2026-02-16
**安全等级**: 基础安全加固

---

## 概述

本文档详细说明 PrivacyGuard v36.2 版本中实施的安全加固措施。这些改进主要针对命令注入、路径遍历、临时文件泄露和异常处理等常见安全问题。

---

## 安全改进清单

### 1. 路径验证 (Path Validation) ✅

#### 新增函数
```python
def validate_safe_path(path, allowed_extensions=None):
    """验证文件路径安全（v36.2: 防止命令注入和路径遍历）"""
    # 实现详见 main.py:167-219
```

#### 防护能力
- **命令注入防护**: 过滤危险字符
  - `;` - 命令分隔符
  - `|` - 管道符
  - `&` - 后台执行
  - `$`, `` ` ``, `$(` - 命令替换
  - `>`, `<` - 重定向
  - `\n`, `\r` - 换行符

- **路径遍历防护**:
  - 规范化路径 (`os.path.normpath`, `os.path.abspath`)
  - 限制允许的路径范围（用户目录、系统临时目录、当前工作目录）
  - 阻止 `..` 等相对路径逃逸

- **扩展名验证** (可选):
  - 白名单机制
  - 支持列表如 `['.doc', '.docx', '.pdf']`

#### 应用位置
| 方法 | 验证内容 | 位置 |
|------|---------|------|
| `_convert_with_libreoffice()` | `temp_doc_path` (`.doc`), `temp_dir` | main.py:2226-2233 |
| `_convert_with_antiword()` | `doc_path` (`.doc`) | main.py:2323-2326 |

#### 使用示例
```python
# 验证输入文件
is_safe, error_msg = validate_safe_path(temp_doc_path, allowed_extensions=['.doc'])
if not is_safe:
    raise ConversionError("文件路径不安全", error_msg)

# 验证临时目录
is_safe, error_msg = validate_safe_path(temp_dir)
if not is_safe:
    raise ConversionError("临时目录不安全", error_msg)
```

---

### 2. 临时文件管理 (TempFileManager) ✅

#### 类定义
```python
class TempFileManager:
    """v36.2: 增强版临时文件管理，使用 atexit 确保清理"""
    # 实现详见 main.py:126-164
```

#### 安全特性
- **atexit 清理**: 注册 `cleanup()` 方法到 `atexit`，确保程序退出时清理
- **全生命周期追踪**: 记录所有创建的临时文件和目录
- **安全删除**: 使用具体异常类型 (`OSError`, `IOError`) 处理删除错误

#### API
```python
# 创建管理器
manager = TempFileManager()

# 创建临时文件
temp_file = manager.create_temp_file(suffix='.pdf')

# 创建临时目录
temp_dir = manager.create_temp_dir()

# 手动清理（通常不需要，程序退出自动清理）
errors = manager.cleanup()
```

#### 清理触发时机
1. 程序正常退出
2. 程序异常退出（通过 atexit）
3. 手动调用 `cleanup()`

---

### 3. 错误处理完善 ✅

#### 改进原则
将裸 `except Exception` 替换为**具体异常类型**，防止：
- 意外捕获系统退出信号 (`SystemExit`, `KeyboardInterrupt`)
- 隐藏真正的错误
- 错误信息泄露敏感信息

#### 修改清单 (11 处)

| 位置 | 原异常 | 新异常 | 说明 |
|------|--------|--------|------|
| TempFileManager.cleanup() (文件) | `Exception` | `OSError, IOError` | 文件删除 |
| TempFileManager.cleanup() (目录) | `Exception` | `OSError, IOError` | 目录删除 |
| ImageMergeWorker (处理单图) | `Exception` | `IOError, OSError, ValueError` | 图片处理 |
| ImageMergeWorker (整体) | `Exception` | `IOError, OSError, ValueError, RuntimeError` | 合并处理 |
| OCRWorker.run() | `Exception` | `IOError, OSError, RuntimeError, ValueError` | OCR 扫描 |
| _open_file() | `Exception` | `IOError, OSError, ValueError` | 文件打开 |
| _open_word_docx() | `Exception` | `IOError, OSError, ValueError, KeyError` | Word 打开 |
| _open_word_doc() | `Exception` | `IOError, OSError, RuntimeError, ValueError` | .doc 转换 |
| _open_images_merge() | `Exception` | `IOError, OSError, ValueError, RuntimeError` | 图片合并 |
| _on_merge_finished() | `Exception` | `IOError, OSError, ValueError` | 保存合并 |
| render_word_preview() | `Exception` | `IOError, OSError, ValueError, RuntimeError` | 渲染预览 |
| _add_data_key_attributes() | `Exception` | `ImportError, AttributeError, TypeError, ValueError` | HTML 处理 |
| _highlight_exact_match() | `Exception` | `ImportError, AttributeError, TypeError, ValueError, IndexError` | 精确高亮 |
| _save_pdf() | `Exception` | `IOError, OSError, ValueError, RuntimeError` | PDF 保存 |
| _convert_with_libreoffice() | `Exception` | `OSError, IOError, RuntimeError, ValueError` | 转换处理 |
| _convert_with_antiword() | `Exception` | `OSError, IOError, RuntimeError, ValueError, ImportError` | 转换处理 |
| _save_word() | `Exception` | `OSError, IOError, RuntimeError, ValueError, KeyError, AttributeError` | Word 保存 |
| validate_safe_path() | `Exception` | `TypeError, ValueError, OSError` | 路径验证 |

#### 保留的裸 except（合理用法）

| 行号 | 位置 | 说明 |
|------|------|------|
| ~353 | QPixmap 缩略图 | UI 降级处理，使用默认图标 |
| ~1397 | 主题检测 | 非关键功能，默认浅色主题 |
| ~2442 | 临时文件清理 | 清理错误仅记录日志 |

---

### 4. 依赖安全审计 ✅

#### 审计工具
```bash
pip install pip-audit
pip-audit --local
```

#### 审计结果
- **状态**: ✅ 无已知漏洞
- **检查时间**: 2026-02-16
- **依赖数量**: 60+

#### 主要依赖版本
```
numpy==2.4.2
opencv-python==4.13.0.92
Pillow==12.1.1
PyMuPDF==1.27.1
PyQt6==6.10.2
python-docx==1.2.0
rapidocr-onnxruntime==1.2.3
```

#### 定期审计建议
```bash
# 每月运行一次
source venv/bin/activate
pip-audit --local --format markdown
```

---

## 验证方法

### 1. 语法检查
```bash
python -c "import ast; ast.parse(open('main.py').read()); print('✓ OK')"
```

### 2. 模块导入测试
```bash
python -c "
from PyQt6.QtWidgets import QApplication
import fitz
from docx import Document
import cv2
import numpy
print('✓ All imports OK')
"
```

### 3. 稳定性测试
```bash
python tests/scripts/test_stability.py
```

### 4. 安全功能验证
```bash
python -c "
import sys
sys.path.insert(0, '.')
with open('main.py') as f:
    content = f.read()

# 检查关键函数存在
assert 'def validate_safe_path' in content
assert 'class TempFileManager' in content
print('✓ Security functions present')

# 检查路径验证已应用
assert 'validate_safe_path(temp_doc_path' in content
assert 'validate_safe_path(doc_path' in content
print('✓ Path validation applied')
"
```

---

## 后续建议

### 短期 (v36.x)
1. **开发者简介完善**: 填充 FeedbackDialog 中的占位符
2. **用户文档更新**: 添加安全特性说明到用户手册
3. **测试覆盖**: 为安全函数添加单元测试

### 中期 (v37.0)
1. **输入验证强化**: 对所有用户输入添加验证
2. **日志审计**: 添加安全事件日志（文件打开、保存、转换）
3. **沙箱机制**: 考虑使用受限进程执行外部命令

### 长期
1. **代码签名**: macOS/Windows 应用签名
2. **漏洞响应流程**: 建立安全漏洞报告和处理机制
3. **定期审计**: 建立季度安全审计流程

---

## 参考文档

- [STATUS.md](current/STATUS.md) - 项目当前状态
- [DEV_LOG.md](current/DEV_LOG.md) - 开发日志
- [CLAUDE.md](../CLAUDE.md) - 开发指南
- [RECOVERY_GUIDE.md](current/RECOVERY_GUIDE.md) - 恢复指南

---

**最后更新**: 2026-02-16
**维护者**: Claude
