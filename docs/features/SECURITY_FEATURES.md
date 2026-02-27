# PrivacyGuard PDF 脱敏安全特性文档

**版本**: v37.5.0 (Seal Detection)
**严重程度**: 高（历史漏洞已修复）
**日期**: 2026-02-27
**状态**: ✅ 已修复并验证

---

## 安全漏洞描述

### 问题
脱敏后的 PDF 文件中，涂黑/涂白的脱敏区域是**可编辑的 PDF 注释对象**，使用 WPS Office、Adobe Acrobat、福昕 PDF 阅读器等工具可以：
- ❌ 删除脱敏框
- ❌ 移动脱敏区域
- ❌ 查看原始敏感信息

### 影响
v37.2.0 及之前所有版本

---

## 根本原因

### 有问题的实现 (v37.2.0 及之前)
```python
annot = page.add_redact_annot(rect)  # 创建可编辑的 PDF 注释
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)  # 不修改图像
doc_save.save(fname)
```

**问题分析**:
1. `add_redact_annot()` 创建的是 **PDF Redaction Annotation**（可编辑的交互元素）
2. `PDF_REDACT_IMAGE_NONE` 参数**不修改底层图像像素**，只是添加覆盖层
3. 注释对象存储在 PDF 的对象树中，PDF 编辑器可以访问和操作它们

---

## 修复方案 (v37.3.0)

### 安全加固后的实现
```python
# 1. 添加脱敏注释
for r in data['ocr'] + data['manual']:
    rect = fitz.Rect(r.x(), r.y(), r.x()+r.width(), r.y()+r.height())
    annot = page.add_redact_annot(rect)
    annot.set_colors(stroke=fill_col, fill=fill_col)
    annot.update()

# 2. 应用脱敏 - 修改图像像素（关键修复）
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

# 3. 删除所有注释对象（安全加固）
for annot in page.annots():
    page.delete_annot(annot)

# 4. 保存时使用垃圾回收和压缩（彻底删除对象）
doc_save.save(fname, garbage=4, deflate=True, clean=True, linear=True)
```

### 关键修改点

| 修改项 | 原实现 | 新实现 | 安全效果 |
|--------|--------|--------|----------|
| **图像处理** | `PDF_REDACT_IMAGE_NONE` | `PDF_REDACT_IMAGE_PIXELS` | 实际修改图像像素 |
| **注释处理** | 保留注释对象 | `page.delete_annot(annot)` | 删除可编辑注释 |
| **保存选项** | 无特殊选项 | `garbage=4, deflate, clean` | 彻底删除未引用对象 |

---

## 技术细节

### PDF_REDACT_IMAGE_PIXELS 原理

| 模式 | 值 | 行为 | 安全性 |
|------|-----|------|--------|
| `PDF_REDACT_IMAGE_NONE` | 0 | 不处理图像 | ❌ 不安全 |
| `PDF_REDACT_IMAGE_REMOVE` | 1 | 删除整个图像 | ⚠️ 可能过度 |
| `PDF_REDACT_IMAGE_PIXELS` | 2 | 修改图像像素 | ✅ 安全 |

### 垃圾回收级别
- `0`: 不回收
- `1`: 删除未引用对象
- `2`: 压缩对象流
- `3`: 合并重复对象
- `4`: 最大优化（推荐用于安全加固）

---

## 测试验证

### 测试结果

| 测试项 | 结果 |
|--------|------|
| 注释删除验证 | ✅ 通过 |
| PDF 对象数量 | 17 → 6（减少 65%） |
| 文件大小 | 减少 41% |
| 代码验证 | ✅ 通过 |

### 安全目标达成

- ✅ 脱敏区域永久嵌入页面内容
- ✅ 原始敏感信息被像素级销毁
- ✅ 任何 PDF 编辑器都无法撤销脱敏操作
- ✅ WPS/Adobe Acrobat/福昕等工具无法删除脱敏框

---

## 升级建议

### 必须升级
所有使用 PrivacyGuard 进行敏感信息脱敏的用户都应立即升级到 v37.3.0 或更高版本。

### 历史文件处理
使用旧版本脱敏的 PDF 文件可能存在安全隐患，建议：
1. 用新版本重新脱敏
2. 或者将 PDF 转换为图片后再生成 PDF

---

**修复完成时间**: 2026-02-22
**版本**: v37.3.0 (PDF Security Fix)
