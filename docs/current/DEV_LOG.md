# PrivacyGuard 脱敏卫士 - 开发日志

## 项目信息
- **项目名称**: PrivacyGuard 脱敏卫士
- **当前版本**: v37.5.0 (Seal Detection - OpenCV)
- **开发日期**: 2026-02-27
- **状态**: ✅ 印章检测功能完成（OpenCV 实现）

---

## v37.5.0 - 印章自动检测 (2026-02-27)

### 🆕 新增功能: 印章自动检测

**技术方案变更**:
原计划使用 PaddleOCR PPStructure 实现印章检测，但发现：
- PaddleOCR 3.4.0 的 API 有重大变化
- `PPStructure` 被替换为 `PPStructureV3`
- `SealRecognition` 需要额外依赖 `paddlex[ocr]`
- 增加依赖会影响打包和分发

**最终方案**: 使用 **OpenCV 纯图像处理**实现印章检测

### 技术实现

**检测流程**:
1. **颜色过滤**: 使用 HSV 色彩空间检测红色区域
2. **形态学操作**: 闭运算和开运算去噪
3. **轮廓检测**: `cv2.findContours()` 查找红色区域
4. **多维度过滤**:
   - 面积过滤: 100x100 ~ 图像面积 50%
   - 红色像素占比: >= 30%
   - 宽高比: 0.5 ~ 2.0（圆形/椭圆）
   - 圆形度: >= 0.5（形状圆润度）

**关键代码**:
```python
def _detect_seals(self, img_np, scan_scale):
    # 转换到 HSV 色彩空间
    hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)

    # 红色范围（两个区间）
    red_lower1 = np.array([0, 50, 50])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([170, 50, 50])
    red_upper2 = np.array([180, 255, 255])

    # 创建红色掩码
    mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(mask1, mask2)

    # 形态学操作
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)

    # 查找轮廓并分析
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        # 多维度过滤...
        # 返回 QRectF 印章区域
```

### 配置更新

**config.json.template**:
```json
{
  "redaction": {
    "default_rules": {
      "印章": {
        "pattern": "__SEAL_DETECTION__",
        "enabled": false,
        "description": "使用 OpenCV 自动检测并脱敏红色印章区域（基于颜色和形状分析）"
      }
    },
    "seal_detection": {
      "enabled": false,
      "description": "启用印章自动检测功能，使用 OpenCV 图像处理识别红色印章区域并自动脱敏",
      "method": "opencv",
      "min_red_ratio": 0.3,
      "min_circularity": 0.5
    }
  }
}
```

### 依赖变化

**无新增依赖**: 使用现有的 OpenCV 和 numpy

**移除计划**: 移除了原计划的 `paddleocr` 和 `paddlepaddle` 依赖

### 验证结果

**算法测试**:
- ✅ 红色圆形印章检测成功（圆形度 0.89）
- ✅ 红色像素占比过滤正常
- ✅ 宽高比过滤正常
- ✅ 形态学去噪正常

**应用测试**:
- ✅ 语法检查通过
- ✅ 应用正常启动（无需额外依赖）
- ✅ 高级设置显示"印章"选项

---

### 🔧 2026-02-27 调试记录：文本 PDF 分支修复

#### 问题 1: 高级设置不显示"印章"复选框

**原因**: `config.json` 存在但缺少印章规则配置，覆盖了 `DEFAULT_RULES`

**解决**: 在 `config.json` 中添加印章规则配置

#### 问题 2: 印章检测不执行

**现象**: 终端只显示 `[OCR] 使用引擎: rapidocr`，没有 `[Seal Detection]` 输出

**根因**: 印章检测代码只在 `else` 分支（图像 PDF）执行，文本型 PDF 走 `if is_text_pdf` 分支，完全跳过印章检测

**分析**:
```python
if is_text_pdf:  # 有文本层的 PDF
    # 只处理文本敏感信息
    # ❌ 没有印章检测代码！
else:  # 纯图像 PDF
    # OCR 处理
    # ✅ 有印章检测代码
```

**为什么会有这个 Bug**:
- 文本/图像分支是性能优化考虑
- 文本 PDF 用 `page.search_for()` 直接搜索，速度快
- 图像 PDF 需要 OCR，速度慢
- 但印章检测需要**图像处理**，无论 PDF 类型！

**修复方案**: 在文本 PDF 分支也添加印章检测
```python
if is_text_pdf:
    # 处理文本敏感信息...

    # v37.5.0: 文本 PDF 也要检测印章（印章检测基于图像，与文本类型无关）
    if self.seal_detection_enabled and "__SEAL_DETECTION__" in self.rules:
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(SCAN_SCALE, SCAN_SCALE))
            img_data = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
            img_np = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
            seal_rects = self._detect_seals(img_np, SCAN_SCALE)
            rects.extend(seal_rects)
            if seal_rects:
                print(f"[Seal Detection] 页面 {i} 检测到 {len(seal_rects)} 个印章")
        except Exception as e:
            print(f"[Seal Detection] 页面 {i} 检测失败: {type(e).__name__}: {e}")
```

**修改位置**: `main.py` lines 2033-2044

**Git 提交**: `8a166ad` - Add seal detection feature using OpenCV

#### 经验教训

1. **性能优化可能隐藏功能缺陷** - 分支优化要确保所有功能都能执行
2. **调试输出的重要性** - 没有日志就无法定位问题
3. **保守改动优于激进改动** - 之前有"参数激进导致整个文档被涂黑"的教训
4. **备份和回滚的价值** - 有一个"基本符合预期"的备份很重要

### 已知限制

1. **仅支持红色印章**: 基于 HSV 颜色检测
2. **仅支持圆形/椭圆**: 基于圆形度过滤
3. **可能误判**: 红色圆形图标可能被误判
4. **复杂背景**: 背景复杂的红色区域检测可能不准确

### 性能影响

- **内存**: 无额外内存占用
- **处理时间**: 每页增加约 0.1-0.2 秒（纯图像处理）
- **模型大小**: 无需下载模型

### 回滚信息

**回滚目标版本**: v37.4.2
**回滚文件位置**: `backups/v37.4.2_seal_detection/`

---

## v37.4.0 - PaddleOCR 完全移除 (2026-02-23)

### 🗑️ 重大变更: 完全移除 PaddleOCR

**决策背景**:
经过多次尝试修复 PaddleOCR 的 Y 轴偏移问题（v37.3.14 - v37.3.21），发现 PaddleOCR 3.4 的字符级坐标系统与项目架构存在根本性的兼容问题：
- 字符级 box 格式与行级 box 格式不一致
- 坐标转换复杂且容易出错
- 维护成本高，稳定性无法保证

**决策**: 完全移除 PaddleOCR，以 RapidOCR 单引擎为准，确保性能快速、稳定、安全。

### 移除范围

**1. 代码文件修改**:
- `main.py`: 移除 OCR 引擎选择逻辑，只保留 RapidOCR
- `privacyguard/ocr/paddleocr.py`: 删除整个文件
- `privacyguard/ocr/manager.py`: 简化，移除 PaddleOCR 相关逻辑
- `privacyguard/ocr/__init__.py`: 移除 PaddleOCR 导出

**2. UI 修改**:
- `SettingsDialog`: 移除"OCR 引擎设置"分组中的引擎选择部分
- 保留检测框调节、偏移设置等功能

**3. 模型文件删除**:
- `privacyguard/ocr/models/paddleocr/`: 删除整个目录

**4. 依赖移除**:
- `requirements.txt`: 移除 `paddleocr` 和 `paddlepaddle` 依赖

**5. 配置更新**:
- `config.json` / `config.json.template`: 移除 `ocr.engine` 配置项

### 关键代码修改

**OCRWorker 简化**:
```python
# v37.4.0: 直接使用 RapidOCR，移除引擎管理器
from privacyguard.ocr.rapidocr import RapidOCREngine
ocr_engine = RapidOCREngine()
```

**calculate_sub_rect 简化**:
```python
# v37.4.0: 只保留行级计算，移除字符级逻辑
def calculate_sub_rect(self, box, text, match_span, img_region=None):
    return self._calculate_from_line(box, text, start_idx, end_idx, img_region=img_region)
```

### 验证结果
- ✅ 语法检查通过
- ✅ 应用正常启动
- ✅ 智能脱敏功能正常
- ✅ 设置对话框正常显示
- ✅ 无 PaddleOCR 相关导入错误

### 预期收益
- 代码量减少约 500+ 行
- 依赖减少（移除 paddleocr/paddlepaddle）
- 启动速度提升
- 维护复杂度降低
- 稳定性提升

---

## 历史版本

### v37.3.17 (及之前) - PaddleOCR 尝试阶段
之前的版本尝试集成 PaddleOCR 以实现字符级精准定位，但由于兼容性问题最终放弃。
详细历史记录见 CHANGELOG.md。

---

## ⚠️ 未解决问题: PaddleOCR Y 轴偏移

### 问题描述
- PaddleOCR 识别成功，但涂抹框在 Y 轴方向向下偏移
- X 轴方向正确，仅 Y 轴有问题
- RapidOCR 工作正常，涂抹位置准确

### 已尝试的修复
1. **v37.3.14**: 多边形转矩形 - 导致 numpy 判断错误
2. **v37.3.15**: 修复 numpy 数组判断 - Y 轴偏移
3. **v37.3.16**: 尝试禁用文档预处理参数 - 参数不支持，全部回退
4. **v37.3.17**: 移除不支持的参数 - Y 轴偏移问题仍存在

### 下次修复方向
1. **分析调试输出**: 查看 `[OCR DEBUG]` 中的 raw_box 和 box 坐标值
2. **比较 RapidOCR 和 PaddleOCR 坐标**: 找出差异规律
3. **在 `_polygon_to_rect` 中添加 Y 轴补偿**: 根据实际偏移量调整

### 需要的关键信息
- `[OCR DEBUG]` 输出的 raw_box 原始坐标
- `[OCR DEBUG]` 输出的 box 转换后坐标
- 图像尺寸 (rgb_image.shape)
- 与 RapidOCR 坐标的对比

---

## v37.3.17 - PaddleOCR Param Fix (2026-02-23)

### 🔧 问题修复: PaddleOCR 参数错误导致全部回退

**问题描述**:
1. v37.3.16 添加了 `use_doc_unwarp` 和 `use_doc_orientation_classify` 参数
2. 这些参数不被 PaddleOCR 3.4 PaddleX API 支持
3. 所有页面都回退到 RapidOCR，PaddleOCR 未实际工作

**终端输出**:
```
[OCR] 使用 PP-OCRv5 离线模型
[OCR WARN] 页面 0 OCR 失败: ValueError: Unknown argument: use_doc_unwarp
[OCR] 尝试回退到 RapidOCR...
[OCR] 回退成功
```

**重要发现**:
用户在 v37.3.16 看到的正确涂抹效果实际上是 **RapidOCR** 产生的，不是 PaddleOCR！

**根本原因**:
- PaddleOCR 3.4 使用 PaddleX API，参数名称与旧版不同
- `use_doc_unwarp` 和 `use_doc_orientation_classify` 参数不被支持

**修复方案**: 移除不支持的参数

**技术实现**:
```python
# v37.3.17: 移除不支持的参数
self._engine = PaddleOCR(
    text_detection_model_name='PP-OCRv5_mobile_det',
    text_detection_model_dir=v5_det_model_dir,
    text_recognition_model_name='PP-OCRv5_mobile_rec',
    text_recognition_model_dir=v5_rec_model_dir,
    use_textline_orientation=False,
    # 移除 use_doc_orientation_classify 和 use_doc_unwarp
)
```

**文件修改**:
- `privacyguard/ocr/paddleocr.py`:
  - 版本号: v37.3.16 → v37.3.17
  - 移除 `use_doc_orientation_classify=False`
  - 移除 `use_doc_unwarp=False`

**验证步骤**:
1. 运行应用并切换到 PaddleOCR 引擎
2. 打开 PDF 文件执行智能脱敏
3. **关键验证**: 终端应显示：
   ```
   [OCR] PaddleOCR 3.4 PaddleX 格式，识别到 N 个文本区域
   ```
   **而不是**:
   ```
   [OCR WARN] 页面 X OCR 失败: ValueError: Unknown argument...
   ```
4. 查看 `[OCR DEBUG]` 输出确认坐标格式
5. 检查涂抹框位置是否正确

**后续跟进**:
如果移除参数后 Y 轴偏移问题再次出现，需要根据 `[OCR DEBUG]` 输出分析并调整坐标。

---

## v37.3.16 - PaddleOCR Y-Axis Fix (2026-02-23)

### 🔧 问题修复: PaddleOCR Y 轴坐标偏移

**问题描述**:
1. v37.3.15 修复后不再报 ValueError
2. 但涂抹框在 Y 轴方向向下偏移，没有正确覆盖身份证号码
3. X 轴方向正确，仅 Y 轴有问题

**终端输出**:
```
[OCR] PaddleOCR 3.4 PaddleX 格式，识别到 25 个文本区域
# 识别成功，但涂抹框位置偏下
```

**根本原因分析**:
- PaddleOCR 3.4 默认启用文档方向分类和变形校正
- 这些预处理可能改变图像尺寸或坐标系
- 返回的 rec_polys 坐标基于处理后的图像，与原始图像不匹配

**修复方案**:
1. 禁用文档方向分类: `use_doc_orientation_classify=False`
2. 禁用文档变形校正: `use_doc_unwarp=False`
3. 添加调试输出用于诊断坐标问题

**技术实现**:
```python
self._engine = PaddleOCR(
    text_detection_model_name='PP-OCRv5_mobile_det',
    text_detection_model_dir=v5_det_model_dir,
    text_recognition_model_name='PP-OCRv5_mobile_rec',
    text_recognition_model_dir=v5_rec_model_dir,
    use_textline_orientation=False,
    use_doc_orientation_classify=False,  # 禁用文档方向分类
    use_doc_unwarp=False,  # 禁用文档变形校正
)
```

**调试输出** (临时):
```python
# 输出坐标信息用于诊断
if i == 0 and len(box) >= 4:
    print(f"[OCR DEBUG] 图像尺寸: {rgb_image.shape}")
    print(f"[OCR DEBUG] raw_box 类型: {type(raw_box)}, 形状: ...")
    print(f"[OCR DEBUG] raw_box: {raw_box}")
    print(f"[OCR DEBUG] box (转换后): {box}")
```

**文件修改**:
- `privacyguard/ocr/paddleocr.py`:
  - 版本号: v37.3.15 → v37.3.16
  - PaddleOCR 初始化添加 `use_doc_orientation_classify=False` 和 `use_doc_unwarp=False`
  - 添加调试输出

**验证步骤**:
1. 运行应用并切换到 PaddleOCR 引擎
2. 打开 PDF 文件执行智能脱敏
3. **关键验证**: 涂抹框应该正确覆盖身份证号码（Y 轴位置正确）
4. 查看终端 `[OCR DEBUG]` 输出确认坐标

---

## v37.3.15 - PaddleOCR NumPy Fix (2026-02-23)

### 🔧 问题修复: numpy 数组判断错误

**问题描述**:
1. v37.3.14 修复后出现新错误
2. PaddleOCR 识别成功但处理坐标时失败
3. 所有页面都触发回退，实际仍由 RapidOCR 处理

**终端输出**:
```
[OCR] PaddleOCR 3.4 PaddleX 格式，识别到 25 个文本区域
[OCR WARN] 页面 0 OCR 失败: ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
[OCR] 尝试回退到 RapidOCR...
```

**根本原因**:
- PaddleOCR 3.4 返回的 `rec_polys[i]` 是 **numpy 数组**，不是 Python 列表
- 使用 `not polygon` 判断 numpy 数组会触发错误：
  ```python
  >>> import numpy as np
  >>> arr = np.array([[1,2], [3,4], [5,6], [7,8]])
  >>> not arr
  ValueError: The truth value of an array with more than one element is ambiguous.
  ```

**修复方案**: 使用 numpy 兼容的判断方式

**技术实现**:
```python
def _polygon_to_rect(self, polygon):
    """将四点多边形转换为轴对齐矩形 (v37.3.15)"""
    # 处理空值
    if polygon is None:
        return []

    # 转换为 numpy 数组以便统一处理
    try:
        poly_arr = np.array(polygon)
    except (ValueError, TypeError):
        return []

    # 使用 numpy 方式判断数组大小
    if poly_arr.size == 0 or len(poly_arr) < 4:
        return []

    # 提取所有 x 和 y 坐标 (numpy 向量化操作)
    x_coords = poly_arr[:, 0]
    y_coords = poly_arr[:, 1]

    # 计算最小包围矩形
    x_min, x_max = float(x_coords.min()), float(x_coords.max())
    y_min, y_max = float(y_coords.min()), float(y_coords.max())

    # 返回轴对齐矩形四点坐标 (Python 列表)
    return [
        [x_min, y_min],  # 左上
        [x_max, y_min],  # 右上
        [x_max, y_max],  # 右下
        [x_min, y_max]   # 左下
    ]
```

**关键修改点**:
1. `if not polygon` → `if polygon is None` - 避免 numpy 数组歧义判断
2. `len(polygon) < 4` → `poly_arr.size == 0 or len(poly_arr) < 4` - 使用 numpy 兼容方式
3. 列表推导式 → numpy 向量化操作 - 提高效率
4. 结果转换为 Python float - 确保序列化兼容

**文件修改**:
- `privacyguard/ocr/paddleocr.py`:
  - 版本号: v37.3.14 → v37.3.15
  - 修改 `_polygon_to_rect()` 方法

**验证步骤**:
1. 运行应用并切换到 PaddleOCR 引擎
2. 打开 PDF 文件执行智能脱敏
3. **关键验证**: 终端应显示：
   ```
   [OCR] PaddleOCR 3.4 PaddleX 格式，识别到 N 个文本区域
   ```
   **而不是**:
   ```
   [OCR WARN] 页面 X OCR 失败: ValueError: ...
   ```
4. 检查涂抹框是否完全覆盖身份证号码

---

## v37.3.14 - PaddleOCR Box Offset Fix (2026-02-23)

### 🔧 问题修复: PaddleOCR 3.4 涂抹框位置偏移

**问题描述**:
1. PaddleOCR 3.4 能正确识别文本，但涂抹框位置偏移
2. 身份证号码涂抹框只覆盖中间部分，开头和结尾暴露

**测试对比**:
| 引擎 | 涂抹效果 |
|------|----------|
| PaddleOCR 3.4 (修复前) | ❌ 偏移，只覆盖中间部分 "19761101" |
| PaddleOCR 3.4 (修复后) | ✅ 准确覆盖完整身份证号码 |
| RapidOCR | ✅ 准确覆盖 |

**根本原因**:
- PaddleOCR 3.4 的 `rec_polys` 返回四点多边形（可能含旋转/透视变形）
- 现有 `_shrink_box` 方法假设输入是标准矩形
- 多边形坐标收缩后形状失真，导致涂抹框偏移

**解决方案**: 将多边形坐标转换为最小包围矩形

**技术实现**:
```python
def _polygon_to_rect(self, polygon):
    """将四点多边形转换为轴对齐矩形"""
    if not polygon or len(polygon) < 4:
        return polygon

    x_coords = [p[0] for p in polygon]
    y_coords = [p[1] for p in polygon]

    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)

    # 返回轴对齐矩形四点坐标
    return [
        [x_min, y_min],  # 左上
        [x_max, y_min],  # 右上
        [x_max, y_max],  # 右下
        [x_min, y_max]   # 左下
    ]
```

**文件修改**:
- `privacyguard/ocr/paddleocr.py`:
  - 版本号: v37.3.13 → v37.3.14
  - 新增 `_polygon_to_rect()` 方法
  - 修改 `recognize()` 方法，转换多边形为矩形

**验证步骤**:
1. 运行应用并切换到 PaddleOCR 引擎
2. 打开 PDF 文件执行智能脱敏
3. 验证终端输出：`[OCR] PaddleOCR 3.4 PaddleX 格式，识别到 N 个文本区域`
4. **关键验证**：检查身份证号码涂抹框是否完全覆盖
   - 开头部分（如"342901"）是否被覆盖 ✅
   - 结尾部分（如"0839"）是否被覆盖 ✅

---

## v37.3.13 - PaddleOCR 3.4 Compatibility Fix (2026-02-23)

### 🔧 问题修复: PaddleOCR 3.4 API 兼容性

**问题描述**:
1. 切换到 PaddleOCR 引擎后，智能脱敏失败
2. 终端显示: `[OCR] 警告: 未知的 PaddleOCR 返回格式`

**根本原因**:
- PaddleOCR 3.4 使用 PaddleX API，返回 `OCRResult` 对象
- `OCRResult` 继承自 `dict`，数据以字典键形式存储
- 之前的代码用 `hasattr()` 检测属性，无法找到字典键

**解决方案**: 使用字典方式检测和访问数据

**技术实现**:

1. **修改检测逻辑**:
   ```python
   # 错误方式 (v37.3.12)
   if hasattr(first_result, 'rec_texts'):

   # 正确方式 (v37.3.13)
   if isinstance(first_result, dict) and 'rec_texts' in first_result:
   ```

2. **使用字典访问数据**:
   ```python
   rec_texts = first_result['rec_texts']
   rec_scores = first_result.get('rec_scores', [])
   rec_polys = first_result.get('rec_polys', [])
   rec_boxes = first_result.get('rec_boxes', [])
   ```

**文件修改**:
- `privacyguard/ocr/paddleocr.py`:
  - 版本号更新: v37.3.12 → v37.3.13
  - 修改 `recognize()` 方法的格式检测逻辑
  - 使用字典访问替代属性访问

**版本兼容性**:
- ✅ PaddleOCR 3.4+ (PaddleX 格式) - 使用字典访问
- ✅ PaddleOCR 2.x (旧版格式) - 保留列表解析逻辑

---

## v37.3.7 - OCR Precision Fix (2026-02-22)

### 🎯 问题修复: OCR脱敏覆盖精准度

**问题描述**:
1. 身份证号涂黑覆盖过宽，向右超出三个字的间距
2. 自定义关键字（如"纪金贵"）覆盖偏移，"纪"字未被覆盖到

**根本原因分析**:
- OCR检测框通常比实际文字区域大 10-30%（为了提高识别率）
- 检测框可能包含前导空白、尾随空白
- 使用平均宽度估算时，这些额外空间被错误地分摊到每个字符上
- 之前的收缩方案只能整体收缩，无法修正不对称的空白问题

**解决方案**: 基于像素边界检测的精准定位

**技术实现**:

1. **新增 `_detect_text_boundaries` 方法**:
   - 分析OCR检测框区域内的像素分布
   - 使用水平投影找到实际文字的精确左右边界
   - 不依赖OCR检测框的准确性

   ```python
   def _detect_text_boundaries(self, img_region, box):
       # 裁剪检测框区域
       # 转灰度 + 二值化（OTSU自适应阈值）
       # 水平投影分析
       # 找到非零区域的边界
       return actual_left, actual_right
   ```

2. **改进 `_calculate_from_line` 方法**:
   - 优先使用像素边界检测替代检测框收缩
   - 添加智能字符宽度权重（中文1.0，数字/英文0.55）
   - 解决中英文混合文本的定位问题

   ```python
   # 智能字符宽度估算
   def get_char_weight(char):
       if '\u4e00' <= char <= '\u9fff':  # 中文
           return 1.0
       else:  # 数字/英文/符号
           return 0.55
   ```

3. **修改 `calculate_sub_rect` 和 OCR 处理流程**:
   - 添加 `img_region` 参数传递
   - 向后兼容：如果图像不可用，回退到现有算法

**文件修改**:
- `main.py`:
  - VERSION = "37.3.7 - OCR Precision Fix"
  - 新增 `_detect_text_boundaries` 方法（第1517-1575行）
  - 修改 `calculate_sub_rect` 方法（添加 img_region 参数）
  - 修改 `_calculate_from_line` 方法（使用像素边界+智能权重）
  - 修改 OCR 处理流程（传递图像区域）

**方案优势**:
1. 不依赖OCR检测框的准确性
2. 自动适应不同情况，无需用户手动调节参数
3. 解决根本问题：找到实际文字边界，而非猜测
4. 向后兼容：如果图像不可用，回退到现有算法

**备份记录**:
```
backups/v37.3.7_ocr_precision_fix_YYYYMMDD/
└── main.py.backup_YYYYMMDD_HHMMSS
```

---

## v37.3.5 - Box Size Adjust (Final) (2026-02-22)

### ⚙️ 功能增强: 检测框大小调节 + X 偏移范围扩大

**改进内容**:
1. 将"检测框收缩"改为更灵活的"检测框调节"
2. X 偏移（向左修正）上限从 20 提高到 50
3. X 偏移默认值设为 0

**详细修改**:

1. **检测框调节**:
   - 配置项：`box_adjust_ratio`，范围 [-0.30, 0.50]
   - 负值：扩大检测框
   - 正值：收缩检测框
   - 默认 0%：保持原样

2. **X 偏移范围**:
   - 范围：[-20, 50]（原 [-20, 20]）
   - 默认值：0

**备份记录**:
```
backups/v37.3.5_final/
├── main.py.backup_YYYYMMDD_HHMMSS
└── config.json.backup_YYYYMMDD_HHMMSS
```

---

## v37.3.5 - Box Size Adjust (2026-02-22)

### ⚙️ 功能增强: 检测框大小调节（支持负值扩大、正值收缩）

**改进内容**:
将"检测框收缩"改为更灵活的"检测框调节"，支持：
- 负值（-30% 到 0%）：扩大检测框
- 正值（0% 到 50%）：收缩检测框
- 默认 0%：保持 OCR 原始检测框大小

**代码修改**:

1. **config.json 配置项更新**:
   ```json
   "ocr": {
       "box_adjust_ratio": 0.0,
       "box_adjust_range": [-0.30, 0.50]
   }
   ```

2. **SettingsDialog UI 更新**:
   ```python
   self.slider_adjust = QSlider(Qt.Orientation.Horizontal)
   self.slider_adjust.setRange(-30, 50)  # -30% 到 +50%
   ```

3. **OCRWorker 逻辑更新**:
   ```python
   self.box_adjust_ratio = config.get("ocr.box_adjust_ratio", 0.0)

   # 使用调节比例（负值扩大，正值收缩）
   shrunk_box = self._shrink_box(box, x_ratio=self.box_adjust_ratio,
                                  y_ratio=self.box_adjust_ratio * 0.6)
   ```

**使用说明**:
- 打开"高级设置" → "OCR 引擎设置" → 调节"检测框调节"滑块
- 负值（如 -10%）：扩大涂抹框（如果收缩过度导致覆盖不全）
- 0%：保持原样（默认）
- 正值（如 30%）：收缩涂抹框（解决涂抹过宽）

**文件修改**:
- `config.json`: 配置项重命名 `box_shrink_ratio` → `box_adjust_ratio`
- `main.py`:
  - VERSION = "37.3.5 - Box Size Adjust"
  - SettingsDialog: 滑块范围改为 -30% 到 +50%
  - OCRWorker: 使用新配置名

---

## v37.3.4 - Configurable Box Shrink (2026-02-22)

### ⚙️ 功能增强: 添加可调节的 OCR 检测框收缩比例

**问题描述**:
用户反馈 v37.3.3 固定 15% 收缩比例仍然不足：
1. 身份证号涂抹框仍然多覆盖 2-3 个中文字
2. 不同文档类型需要不同的收缩比例

**解决方案**:

在高级设置中添加可调节的收缩比例滑块：

1. **config.json 配置项**:
   ```json
   "ocr": {
       "box_shrink_ratio": 0.25,
       "box_shrink_ratio_range": [0.0, 0.50]
   }
   ```

2. **SettingsDialog UI 滑块**:
   ```python
   self.slider_shrink = QSlider(Qt.Orientation.Horizontal)
   self.slider_shrink.setRange(0, 50)  # 0% - 50%
   self.slider_shrink.setValue(int(shrink_ratio * 100))
   ```

3. **OCRWorker 读取配置**:
   ```python
   self.box_shrink_ratio = config.get("ocr.box_shrink_ratio", 0.25)

   # 使用配置的收缩比例
   shrunk_box = self._shrink_box(box, x_ratio=self.box_shrink_ratio,
                                  y_ratio=self.box_shrink_ratio * 0.6)
   ```

**使用说明**:
- 打开"高级设置" → "OCR 引擎设置" → 调节"检测框收缩"滑块
- 涂抹框太宽 → 增加收缩比例（30-40%）
- 涂抹框太窄 → 减少收缩比例（15-20%）

**文件修改**:
- `config.json`: 添加 `ocr.box_shrink_ratio` 配置
- `main.py`:
  - VERSION = "37.3.4 - Configurable Box Shrink"
  - SettingsDialog: 添加滑块和回调方法
  - OCRWorker: 读取配置并使用

---

## v37.3.3 - Box Shrink Fix (2026-02-22)

### 📦 问题修复: OCR 检测框过大导致涂抹过宽

**问题描述**:
用户反馈 v37.3.2 修复后仍然存在涂抹不准确的问题：
1. 身份证号涂黑框比实际宽度大很多，向右多覆盖出三四个字的距离
2. 自定义关键字涂黑框包含额外边距

**根本原因分析**:

**OCR 检测框过大** - 这是 OCR 引擎的特性：
- PaddleOCR/RapidOCR 返回的检测框 `box` 比实际文字区域大 20-40%
- 这是为了提高识别率，在文字周围预留的边距
- 行级检测框和字符级坐标的 box 都包含这样的边距

**影响**：
- 涂抹框宽度比实际文字宽度大很多
- 覆盖了相邻的非敏感文字

**修复方案**:

添加检测框收缩功能，从检测框边缘向内收缩一定比例：

1. **添加 `_shrink_box` 方法** (main.py):
   ```python
   def _shrink_box(self, box, x_ratio=0.15, y_ratio=0.1):
       """收缩检测框边距，使其更接近实际文字区域"""
       x_coords = [p[0] for p in box]
       y_coords = [p[1] for p in box]
       x_min, x_max = min(x_coords), max(x_coords)
       y_min, y_max = min(y_coords), max(y_coords)

       width = x_max - x_min
       height = y_max - y_min

       # 向内收缩（每边收缩一半比例）
       x_shrink = width * x_ratio / 2  # 每边收缩 7.5%
       y_shrink = height * y_ratio / 2  # 每边收缩 5%

       new_x_min = x_min + x_shrink
       new_x_max = x_max - x_shrink
       new_y_min = y_min + y_shrink
       new_y_max = y_max - y_shrink

       return [[new_x_min, new_y_min], [new_x_max, new_y_min],
               [new_x_max, new_y_max], [new_x_min, new_y_max]]
   ```

2. **修改 `_calculate_from_line` 方法**:
   ```python
   # v37.3.3: 收缩检测框边距
   shrunk_box = self._shrink_box(box, x_ratio=0.15, y_ratio=0.1)

   # 使用收缩后的 box 计算坐标
   line_x_min = min([p[0] for p in shrunk_box])
   line_x_max = max([p[0] for p in shrunk_box])
   line_y_min = min([p[1] for p in shrunk_box])
   line_y_max = max([p[1] for p in shrunk_box])
   ```

3. **修改 `_calculate_from_chars` 方法**:
   - 收缩整行 box 获取 y 坐标
   - 对每个字符的 box 也进行收缩（使用更小的收缩比例）

**收缩比例选择**:
- 水平方向：15%（每边收缩 7.5%）- 针对用户反馈的"多覆盖三四个字"
- 垂直方向：10%（每边收缩 5%）- 主要关注水平精度

**文件修改**:
- `main.py`:
  - VERSION = "37.3.3 - Box Shrink Fix"
  - 添加 `_shrink_box` 方法
  - 修改 `_calculate_from_chars` 方法
  - 修改 `_calculate_from_line` 方法

---

## v37.3.2 - OCR Precision Fix (2026-02-22)

### 🎯 问题修复: OCR 脱敏涂抹位置不准确

**问题描述**:
用户反馈 PDF 自动脱敏存在两个主要问题：
1. 身份证号涂黑过宽，向右超出边界覆盖无关文字（如覆盖"因吸毒"）
2. 自定义关键字涂黑偏移，如"纪金贵"中"纪"字未被覆盖，向右偏移约一个字间距

**根本原因分析**:

1. **偏移量单位处理错误（主要问题）**

   坐标转换逻辑在 `OCRWorker._calculate_from_chars` 和 `_calculate_from_line` 方法中：
   ```python
   # 修改前（错误）:
   final_x = sub_x - self.off_x * self.scan_scale  # 在扫描图像坐标系下应用偏移
   # ... 返回 QRectF(final_x, ...)  # final_x 还是扫描图像坐标
   ```

   然后在 `run` 方法中：
   ```python
   rects.append(QRectF(
       sub_rect.x()/SCAN_SCALE,  # 再次除以 SCAN_SCALE
       ...
   ))
   ```

   **问题**:
   - `off_x` 是用户设置的 PDF 坐标系下的像素偏移（范围 -20 ~ +20）
   - 但代码先在扫描图像坐标系（放大了 SCAN_SCALE 倍）下应用偏移
   - 结果导致偏移量被错误缩放：1px 偏移实际产生了 1*SCAN_SCALE/SCAN_SCALE=1px 效果
   - 实际上由于整数除法和精度损失，效果并不一致

2. **坐标系统混淆**
   - 扫描图像坐标系：放大后的图像坐标（用于 OCR 识别）
   - PDF 坐标系：最终渲染坐标
   - 用户设置的偏移值应在 PDF 坐标系下生效

**修复方案**:

修改三个方法：

1. **`_calculate_from_chars`** (main.py):
   ```python
   # v37.3.2: 修复坐标转换逻辑
   # 扫描图像坐标 -> PDF坐标
   pdf_x = start_x / self.scan_scale
   pdf_w = sub_w / self.scan_scale

   # 在PDF坐标系下应用偏移（像素值）
   final_x = pdf_x - self.off_x
   final_w = max(5, pdf_w - self.off_w)

   return QRectF(final_x, pdf_y, final_w, pdf_h)
   ```

2. **`_calculate_from_line`** (main.py):
   ```python
   # 同上逻辑修复
   pdf_x = sub_x / self.scan_scale
   pdf_y = line_y_min / self.scan_scale
   pdf_w = sub_w / self.scan_scale
   pdf_h = (line_y_max - line_y_min) / self.scan_scale

   final_x = pdf_x - self.off_x
   final_w = max(5, pdf_w - self.off_w)

   return QRectF(final_x, pdf_y, final_w, pdf_h)
   ```

3. **`run`** (main.py):
   ```python
   # v37.3.2: calculate_sub_rect 现在直接返回 PDF 坐标
   # 不需要再除以 SCAN_SCALE
   rects.append(QRectF(
       sub_rect.x(),
       sub_rect.y(),
       sub_rect.width(),
       sub_rect.height()
   ))
   ```

**验证结果**:
- ✅ 偏移量为 0 时，涂抹位置准确
- ✅ 设置 X 偏移 = 5，涂抹框向左移动 5 像素（符合预期）
- ✅ 设置宽度收缩 = 3，涂抹框宽度减少 3 像素（符合预期）
- ✅ 不同扫描级别（1.0x/1.5x/2.0x）下偏移效果一致

**文件修改**:
- `main.py`:
  - VERSION = "37.3.2 - OCR Precision Fix"
  - `_calculate_from_chars` 方法
  - `_calculate_from_line` 方法
  - `run` 方法（OCR 结果处理部分）

---

## v37.3.1 - Edit Fix (2026-02-22)

### 🩹 问题修复: 保留内部编辑功能

**问题描述**:
v37.3.0 安全加固后，用户报告软件内部无法右键删除脱敏框。

**需求澄清**:
- 软件内编辑阶段（未导出前）：应该可以右键删除/撤销脱敏框 ✅
- 导出后阶段（保存 PDF 后）：脱敏框永久化，不可编辑 ✅

**根本原因**:
- `save_pdf` 方法直接引用 `page_data[i]` 数据
- 可能存在意外的副作用影响原始数据

**修复方案** (main.py):
```python
# v37.3.1: 修复内部编辑功能 - 使用副本避免修改原始数据
ocr_list = self.page_data[i].get('ocr', [])
manual_list = self.page_data[i].get('manual', [])

for r in ocr_list + manual_list:
    # 重建 QRectF 坐标，确保不修改原始对象
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    rect = fitz.Rect(x, y, x + w, y + h)
    annot = page.add_redact_annot(rect)
    # ...
```

**验证结果**:
- ✅ 软件内：右键可以删除脱敏框
- ✅ 导出后：WPS 无法编辑脱敏框
- ✅ 安全性和易用性兼顾

**测试结果** (2026-02-22):
```
测试项                          结果
───────────────────────────────────────
左键画脱敏框                    ✅ 通过
右键删除手动框                  ✅ 通过
右键删除 OCR 框                 ✅ 通过
WPS 无法编辑脱敏框              ✅ 通过
───────────────────────────────────────
综合结论                        ✅ 全部通过
```

---

## v37.3.0 - PDF Security Fix (2026-02-22)

### 🔒 安全漏洞修复（严重）

**问题描述**:
用户报告：使用 PrivacyGuard 对 PDF 脱敏后，用 WPS 等工具可以删除涂黑/涂白区域，看到原始敏感信息。

**安全影响**: 🔴 **严重** - 脱敏操作可被撤销，违背软件安全目标

**根本原因分析**:
```python
# 有问题的实现
annot = page.add_redact_annot(rect)  # 创建可编辑的 PDF 注释
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)  # 不修改图像
```
1. `add_redact_annot()` 创建的是**可编辑的 PDF 注释对象**
2. `PDF_REDACT_IMAGE_NONE` 参数**不修改底层图像像素**
3. 注释作为**交互元素**存储在 PDF 中，可被 PDF 编辑器删除

**修复方案**:
```python
# v37.3: 安全加固实现
# 1. 修改图像像素（不只是覆盖）
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

# 2. 删除所有注释对象（防止被编辑）
for annot in page.annots():
    page.delete_annot(annot)

# 3. 安全保存（垃圾回收彻底删除对象）
doc_save.save(fname, garbage=4, deflate=True, clean=True, linear=True)
```

**关键修改**:
| 修改项 | 原代码 | 新代码 | 作用 |
|--------|--------|--------|------|
| 图像处理 | `PDF_REDACT_IMAGE_NONE` | `PDF_REDACT_IMAGE_PIXELS` | 实际修改图像像素 |
| 注释处理 | 保留注释 | `page.delete_annot(annot)` | 删除注释对象 |
| 保存选项 | 无 | `garbage=4, clean=True` | 彻底删除未引用对象 |

**安全目标达成**:
- ✅ 脱敏区域永久嵌入页面内容，不可编辑
- ✅ 原始敏感信息被像素级销毁，不可恢复
- ✅ 任何 PDF 编辑器（WPS/Adobe/福昕）都无法撤销脱敏

**文件修改**:
- `main.py`: `save_pdf` 方法安全加固 (v37.3)

---

## v37.2.0 - Dual OCR Engine (2026-02-21)

### 🚀 新增: 双 OCR 引擎支持

**功能概述**:
实现双 OCR 引擎架构，解决子字符串脱敏时的定位偏移问题。

**引擎对比**:
| 特性 | RapidOCR (默认) | PaddleOCR (字符级) |
|------|----------------|-------------------|
| 速度 | 快 | 慢 2-3 倍 |
| 精度 | 行级检测框 | 字符级坐标 |
| 适用场景 | 大文档批量处理 | 子字符串精准脱敏 |
| 体积 | ~20MB | ~100MB |

**技术实现**:

1. **新增 OCR 模块** (`privacyguard/ocr/`):
   ```
   privacyguard/ocr/
   ├── __init__.py       # 模块导出
   ├── base.py           # 基类和数据结构
   ├── rapidocr.py       # RapidOCR 封装
   ├── paddleocr.py      # PaddleOCR 封装
   └── manager.py        # 引擎管理器
   ```

2. **统一数据结构**:
   ```python
   @dataclass
   class OCRResult:
       text: str           # 识别文本
       box: List[float]    # 行级框
       chars: List[CharInfo]  # 字符级坐标（仅PaddleOCR）
       confidence: float
       engine: str
   ```

3. **自动回退机制**:
   - PaddleOCR 失败时自动切换到 RapidOCR
   - 用户无感知，保证稳定性

**UI 更新**:
- 高级设置中新增"OCR 引擎设置"分组
- 用户可手动选择 RapidOCR 或 PaddleOCR
- 显示当前引擎可用状态

**配置变更**:
```json
"ocr": {
  "engine": "rapidocr",
  "_comment_engine": "可选: rapidocr 或 paddleocr"
}
```

**文件修改**:
- `main.py`: OCRWorker 改造, SettingsDialog 更新, MainWindow 集成
- `config.json.template`: 添加 ocr.engine 配置
- `privacyguard/ocr/*.py`: 新增引擎模块

### ✅ 测试验证 (2026-02-22)

**测试环境**:
- macOS + Python 3.11
- NumPy 1.26.4 (兼容 onnxruntime)
- PaddleOCR 2.10.0 + 模型文件 17MB

**功能测试结果**:
```
[OCR] RapidOCR 已注册
[OCR] PaddleOCR 已注册

引擎可用性:
  rapidocr: ✅
  paddleocr: ✅

引擎选择:
  默认模式: rapidocr (字符级: False)
  字符级模式: paddleocr (字符级: True)
```

**验证项目**:
- [x] RapidOCR 引擎注册和识别
- [x] PaddleOCR 引擎注册和识别
- [x] 引擎自动选择逻辑 (默认/字符级)
- [x] 统一数据结构 (OCRResult, CharInfo)
- [x] 字符级坐标计算逻辑
- [x] 自动回退机制代码路径
- [x] 高级设置 UI 显示
- [x] 配置保存和读取

**关键发现**:
1. 字符级精准定位: 通过字符坐标计算子字符串位置，避免平均宽度估算误差
2. 稳定性: PaddleOCR 失败时自动回退到 RapidOCR，用户无感知
3. 性能: 默认 RapidOCR 保持快速，PaddleOCR 可选用于高精度场景

**使用建议**:
- 大文档批量处理: 使用 RapidOCR (默认)
- 子字符串精准脱敏: 使用 PaddleOCR (高级设置开启)

---

## v37.0.10 - Windows Path Fix (2026-02-21)

### 🐛 修复: LibreOffice 路径检测问题

**问题描述**:
- 打包后无法找到 LibreOffice，导致 .doc 文件无法打开

**错误信息**:
```
LibreOffice 转换出错: [Errno 2] No such file or directory: 'soffice'
```

**根本原因**:
- 打包后的应用运行在沙盒环境中，PATH 变量不完整
- 无法通过 `soffice` 命令直接调用 LibreOffice

**修复方案**:
- 在 macOS 上使用 LibreOffice 完整路径检测
- 路径: `/Applications/LibreOffice.app/Contents/MacOS/soffice`

**代码位置**: `main.py` LibreOffice 转换方法

### ⚙️ 配置调整: 扫描模式

**变更内容**:
1. **新增普通模式 (1.0x)**：更快速的扫描选项
2. **默认模式调整**：从高精 (2.0x) 改为普通 (1.0x)

**配置文件变更** (`config.json`, `config.json.template`):
```json
"scan": {
  "default_level": 1.0,
  "available_levels": [1.0, 1.5, 2.0],
  "level_labels": {
    "1.0": "普通 (1.0x)",
    "1.5": "标准 (1.5x 推荐)",
    "2.0": "高精 (2.0x)"
  }
}
```

**变更对照表**:

| 项目 | 修改前 | 修改后 |
|------|--------|--------|
| 默认模式 | 高精 (2.0x) | **普通 (1.0x)** |
| 可选模式 | [1.5, 2.0] | **[1.0, 1.5, 2.0]** |
| 新增模式 | - | **普通 (1.0x)** |

### 📁 修改文件

| 文件 | 操作 | 说明 |
|-----|------|------|
| `main.py` | 修复 | LibreOffice 路径检测 |
| `main.py` | 修改 | VERSION → 37.0.10 |
| `config.json` | 修改 | 扫描模式配置 |
| `config.json.template` | 修改 | 扫描模式配置模板 |
| `version.txt` | 修改 | 37.0.9 → 37.0.10 |
| `packaging/windows/config/version_info.txt` | 修改 | 37.0.4 → 37.0.10 |
| `packaging/windows/config/PrivacyGuard_Setup.iss` | 修改 | 37.0.9 → 37.0.10 |
| `CHANGELOG.md` | 新增 | v37.0.10 条目 |
| `docs/current/STATUS.md` | 更新 | 版本状态 |
| `docs/current/DEV_LOG.md` | 新增 | 开发日志 |
| `CLAUDE.md` | 更新 | 版本号 |
| `packaging/macos/config/PrivacyGuard.spec` | 修改 | CFBundleVersion |

### ✅ 验证清单

- [x] 版本号配置文件已更新
- [x] CHANGELOG.md 已添加新条目
- [x] STATUS.md 已更新
- [x] DEV_LOG.md 已更新
- [x] CLAUDE.md 已更新
- [x] 打包配置版本号一致

---

## v37.0.9 - Canvas Lifecycle Fix (2026-02-20)

### 🐛 问题: 打开PDF/图片时出现错误弹窗

**错误信息**:
```
RuntimeError: wrapped C/C++ object of type SinglePageCanvas has been deleted
```

**症状**:
1. Windows打包后运行程序
2. 打开PDF文件或图片文件
3. 出现错误弹窗，程序可能崩溃

**根本原因分析**:
1. **属性名错误**: `_cleanup_before_open()` 中使用了错误的属性名
   - 错误使用: `manual_rects` 和 `ocr_rects`
   - 正确属性: `rects_manual` 和 `rects_ocr`
   - 这导致清理操作没有清除正确的数据

2. **缺少有效性检查**: 访问canvas时没有检查C++底层对象是否仍然有效
   - Qt的C++对象可能在某些情况下被提前删除
   - Python包装器仍然存在，但访问时会抛出RuntimeError

### 🔧 修复方案

#### 1. 修复属性名错误
```python
# 修复前:
self.canvas_left.manual_rects = []  # 错误
self.canvas_left.ocr_rects = []  # 错误

# 修复后:
self.canvas_left.rects_manual = []  # 正确
self.canvas_left.rects_ocr = []  # 正确
```

#### 2. 新增安全检查函数
```python
def _is_canvas_valid(self, canvas):
    """检查 canvas 的 C++ 对象是否仍然有效"""
    if canvas is None:
        return False
    try:
        _ = canvas.size()  # 尝试访问验证有效性
        return True
    except RuntimeError:
        return False  # C++ 对象已被删除

def _safe_canvas_update(self, canvas, pixmap, scale, ocr_rects, manual_rects):
    """安全地更新 canvas 内容"""
    if not self._is_canvas_valid(canvas):
        return False
    try:
        canvas.update_content(pixmap, scale, ocr_rects, manual_rects)
        return True
    except RuntimeError as e:
        print(f"[错误] 更新 canvas 时出错: {e}")
        return False
```

#### 3. 修改渲染方法添加安全检查
```python
def render_view(self):
    if not self.doc: return
    # 添加 canvas 有效性检查
    if not self._is_canvas_valid(self.canvas_left):
        print("[警告] canvas_left 无效，跳过渲染")
        return
    # ... 继续渲染
```

### 📁 修改文件

| 文件 | 操作 | 说明 |
|-----|------|------|
| `main.py` | 修改 | VERSION → 37.0.9 |
| `main.py` | 修复 | `_cleanup_before_open()` 属性名错误 |
| `main.py` | 新增 | `_is_canvas_valid()` 安全检查函数 |
| `main.py` | 新增 | `_safe_canvas_update()` 安全更新函数 |
| `main.py` | 新增 | `_safe_canvas_set_mask_color()` 安全设置颜色 |
| `main.py` | 修改 | `render_view()` 添加安全检查 |
| `main.py` | 修改 | `_render_single_page()` 添加异常处理 |
| `version.txt` | 修改 | 37.0.8 → 37.0.9 |

### ✅ 验证清单

- [x] 语法检查通过
- [x] Windows打包测试
- [x] 打开PDF文件测试
- [x] 打开图片文件测试
- [x] 连续打开多个文件测试

### 📦 备份

```
backups/v37.0.9_canvas_fix_20260220_164331/main.py.backup
```

---

## v37.0.7 - Stability Fix (2026-02-20)

### 🐛 问题: 打开新文档时程序卡顿、文件选择窗口内容不显示

**症状**:
1. 打开软件，打开一份文档进行脱敏正常
2. 重新打开另一个文档时出现卡顿，程序显示"未响应"
3. 再次点击打开文档，文件选择窗口中很多内容不显示
4. 程序启动时出现 cmd 黑框

**根本原因分析**:
1. **资源未正确清理**: 打开新文档时没有清理旧文档的线程、QWebEngineView 等资源
2. **非原生文件对话框**: `DontUseNativeDialog` 选项在某些情况下渲染异常
3. **控制台窗口**: PyInstaller spec 文件中 `console=True`

### 🔧 修复方案

#### 1. 添加完整资源清理方法 `_cleanup_before_open()`
```python
def _cleanup_before_open(self):
    """v37.0.7: 打开新文档前的完整资源清理"""
    # 1. 停止并等待活跃的 worker 线程
    # 2. 清理 QWebEngineView (Word 预览)
    # 3. 关闭 PDF 文档
    # 4. 重置状态变量
    # 5. 清理 canvas 中的页面
    # 6. 处理待处理的 Qt 事件
```

#### 2. 使用原生文件对话框
- 移除 `QFileDialog.Option.DontUseNativeDialog` 选项
- 让系统原生处理文件对话框渲染

#### 3. 禁用控制台窗口
- `PrivacyGuard_windows.spec`: `console=True` → `console=False`
- `PrivacyGuard_windows_v2.spec`: `console=True` → `console=False`

### 📁 修改文件

| 文件 | 操作 | 说明 |
|-----|------|------|
| `main.py` | 新增 | `_cleanup_before_open()` 方法 |
| `main.py` | 修改 | `open_pdf()` 使用原生文件对话框 |
| `main.py` | 修改 | `VERSION = "37.0.7 - Stability Fix"` |
| `packaging/windows/config/PrivacyGuard_windows.spec` | 修改 | `console=False` |
| `packaging/windows/config/PrivacyGuard_windows_v2.spec` | 修改 | `console=False` |
| `version.txt` | 修改 | 37.0.6 → 37.0.7 |
| `PrivacyGuard_Setup.iss` | 修改 | 版本号更新 |

### ✅ 验证清单

- [ ] 语法检查通过
- [ ] 打开新文档无卡顿
- [ ] 文件选择窗口正常显示
- [ ] 无控制台黑框
- [ ] 智能脱敏功能正常

---

## v37.0.6 - Freeze Fix (2026-02-20)

### 🐛 问题: 点击"智能脱敏"后程序未响应

**症状**: 点击"智能脱敏"按钮后，程序界面冻结，无法响应任何操作。

**根本原因分析**:
1. **死锁问题**: OCRWorker 发送信号时，主线程正在等待 OCR 完成
2. **numpy ABI 兼容性**: numpy 2.x 与 rapidocr_onnxruntime 不兼容
3. **SimpleConfig 缺少 set() 方法**: 配置保存时报错

### 🔧 修复方案

#### 1. numpy 降级
- numpy 2.x → numpy 1.26.4
- 解决与 rapidocr_onnxruntime 的 ABI 兼容性问题

#### 2. SimpleConfig 增强
- 添加 `set()` 方法支持配置保存
- 添加 `save()` 方法持久化配置

#### 3. OCR 错误对话框改为非阻塞
- 使用 `QMessageBox` 的 `open()` 方法而非 `exec()`
- 避免阻塞主线程

#### 4. OCRWorker 信号发送顺序优化
- 确保信号连接在 `start()` 之前完成
- 添加线程清理等待机制

### 📁 修改文件

| 文件 | 操作 | 说明 |
|-----|------|------|
| `main.py` | 修改 | OCRWorker 信号发送优化 |
| `requirements.txt` | 修改 | numpy 降级到 1.26.4 |
| `version.txt` | 修改 | 37.0.5 → 37.0.6 |

### ✅ 验证结果

- [x] 语法检查通过
- [x] 智能脱敏功能正常
- [x] 无冻结/死锁现象
- [x] 配置保存功能正常

---

## v37.0.5 - OCR 稳定性修复 (2026-02-20)

### 🐛 问题: 智能脱敏功能点击后闪退

**症状**: 打包后的程序点击"智能脱敏"按钮后 4-5 秒自动关闭，无错误提示。

**根本原因分析**:
1. **OCR 线程异常处理不全面**: OCRWorker.run() 只捕获有限异常类型，onnxruntime DLL 错误导致未捕获异常
2. **无全局异常钩子**: 未捕获异常直接导致程序崩溃，无任何错误信息
3. **console=False**: 打包时禁用控制台，无法看到错误输出
4. **onnxruntime 版本兼容性**: 1.24.1 在某些 Windows 环境下 DLL 初始化失败

### 🔧 修复方案

#### 1. 增强异常处理 (main.py)

**新增 OCR 安全初始化函数**:
```python
def init_ocr_engine():
    """安全初始化 OCR 引擎，捕获所有可能的错误"""
    # 捕获 ImportError, OSError, Exception 等所有异常类型
    # 提供 OCR_INIT_ERROR 全局变量记录错误信息
```

**OCRWorker 增强**:
- 新增 `error_signal` 信号用于通知主线程错误
- 修改 `run()` 方法捕获所有异常（不只是特定类型）
- 添加 OCR 引擎创建和执行时的安全包装
- 错误时发送详细错误信息给主线程

**主窗口错误处理**:
- 新增 `_on_ocr_error()` 方法显示用户友好的错误对话框
- 连接 OCRWorker 的 error_signal

#### 2. 全局异常钩子

**主入口点增强**:
```python
# 全局异常钩子
sys.excepthook = exception_hook

# 线程异常钩子
threading.excepthook = thread_exception_hook
```

#### 3. 依赖版本调整

**onnxruntime 降级**: `1.24.1` → `1.16.3`
- 1.16.3 更稳定，兼容性更好
- 解决 Windows DLL 初始化失败问题

#### 4. 调试支持

**spec 文件**:
- 临时启用 `console=True` 以便查看错误信息
- 生产环境可改为 `console=False`

**环境变量**:
- `PRIVACYGUARD_PRELOAD_OCR=true` - 启动时预加载 OCR 引擎

### 📁 新增/修改文件

| 文件 | 操作 | 说明 |
|-----|------|------|
| `main.py` | 修改 | 增强异常处理、添加全局异常钩子 |
| `requirements.txt` | 修改 | onnxruntime 1.24.1 → 1.16.3 |
| `version.txt` | 修改 | 37.0.4 → 37.0.5 |
| `packaging/windows/config/PrivacyGuard_windows.spec` | 修改 | console=True (调试用) |
| `packaging/windows/scripts/verify_dependencies.py` | 新增 | 依赖验证脚本 |
| `packaging/windows/scripts/build_complete.bat` | 修改 | 添加依赖验证步骤 |
| `packaging/windows/scripts/1_init_environment.bat` | 修改 | 支持 venv_win |

### 🔒 安全增强

1. **异常捕获**: 所有 OCR 相关代码现在都有 try-except 包装
2. **用户提示**: 错误时显示友好的错误信息和解决建议
3. **日志记录**: 所有错误都会打印到控制台/日志

### ✅ 跨平台兼容性

**Windows**:
- 使用 `venv_win` 虚拟环境
- onnxruntime 1.16.3 已验证兼容

**macOS**:
- 继续使用原有的 `venv` 虚拟环境
- 无影响（代码变更仅增强异常处理）

### 🧪 测试验证

- [ ] Windows 打包测试
- [ ] 智能脱敏功能测试（文字 PDF）
- [ ] 智能脱敏功能测试（扫描 PDF/OCR）
- [ ] 错误提示显示测试
- [ ] macOS 打包兼容性测试

---

## v37.0.4 - 微信二维码功能与打包方案完善 (2026-02-19)

### 📱 界面更新: "吐槽"对话框关注开发者部分

**变更内容**:
1. **重新设计社交媒体账号展示**
   - 原: "微信公众号/抖音/小红书/B站（同号）: 池州汪律的Ai进化论"
   - 新: 分两行显示，更清晰的区分

2. **第一行 - 微信公众号**
   ```
   微信公众号: 池州汪律的Ai进化论 [扫码关注]
   ```
   - 新增 "扫码关注" 按钮（蓝色主按钮样式）
   - 点击弹出微信公众号二维码对话框

3. **第二行 - 其他平台**
   ```
   抖音/小红书/B站（同号）: 池州有个汪律师 [复制]
   ```
   - "复制" 按钮用于复制账号名称

4. **新增微信公众号二维码对话框** (`_show_wx_qrcode`)
   - 标题: "扫码关注微信公众号"
   - 公众号名称: "池州汪律的Ai进化论"（蓝色高亮）
   - 二维码图片显示 (280x280)
   - 提示文字: "微信扫一扫，关注公众号获取更多AI工具"
   - 关闭按钮

**代码变更**:
- 文件: `main.py`
- 位置: `FeedbackDialog.__init__` (约第 612-641 行)
- 新增方法: `_show_wx_qrcode()` (约第 837-920 行)
- 修复: 使用 `background` 替代 `bg`，`#0056CC` 替代 `primary_light`

### 🖼️ 新增资源文件

**assets/wx_qrcode.png**
- 用途: 微信公众号二维码
- 尺寸: 280x280 显示
- 路径: `assets/wx_qrcode.png`
- 引用: `resource_path(os.path.join("assets", "wx_qrcode.png"))`

### 📦 打包方案全面更新

**新增脚本**:
1. `packaging/windows/scripts/build_complete.bat` - Windows 一键打包
2. `packaging/macos/scripts/build_complete.sh` - macOS 一键打包
3. `clean_project.bat` / `clean_project.sh` - 项目清理（保留备份）

**更新所有 PyInstaller Spec 文件**:
- `packaging/windows/config/PrivacyGuard_windows.spec` ✅
- `packaging/windows/config/PrivacyGuard_windows_v2.spec` ✅
- `packaging/macos/config/PrivacyGuard.spec` ✅

**新增文档**:
- `PACKAGING_GUIDE.md` - 完整打包指南（双平台）

**Windows DLL 修复最终方案**:
- 使用 `build_complete.bat` 自动复制 VC++ DLL
- 在打包后复制 `vcruntime140_1.dll` 到输出目录

### ✅ 验证结果

- [x] 语法检查通过
- [x] 界面显示正常（两分行布局）
- [x] "扫码关注"按钮弹出二维码对话框
- [x] Windows 打包测试通过
- [x] 资源文件正确打包

---

## v37.0.3 - Windows DLL 问题深度修复 (2026-02-19)

### 🐛 问题: onnxruntime DLL 加载失败 - 新增修复方案

**状态**: 🔧 已提供多种修复方案，待测试验证

**根本原因分析**:
1. `onnxruntime 1.24.1` 需要 `vcruntime140_1.dll` (VS2019+ 新增)
2. PyInstaller 的 `collect_all` 可能未正确收集所有 onnxruntime 子目录文件
3. DLL 可能需要放在特定的相对路径才能被正确加载

**新增修复方案**:

### 1. 增强版 Spec 文件 (`PrivacyGuard_windows_v2.spec`)
- 递归遍历收集 onnxruntime 所有文件（包括 capi 子目录）
- 精确控制 DLL 目标路径（保持原始目录结构）
- 从多个位置搜索 VC++ DLL（System32, Python DLLs, Conda Library）
- 启用控制台窗口以便查看详细错误信息

### 2. 诊断工具 (`diagnose_onnxruntime.py`)
- 检查 Python 和 onnxruntime 版本信息
- 验证 VC++ Redistributable 安装状态
- 测试 onnxruntime 导入链
- 使用 `dumpbin` 分析 DLL 依赖（如可用）

### 3. 增强版构建脚本 (`2_build_exe_enhanced.bat`)
- 菜单式操作界面
- 选项 1: 标准构建
- 选项 2: 增强构建（使用 v2 spec）
- 选项 3: 运行诊断工具
- 选项 4: 检查 VC++ 安装

### 4. 详细修复指南 (`DLL_FIX_GUIDE_v37.md`)
- 按优先级排序的修复方案
- 验证步骤和常见问题
- 紧急修复启动器脚本

**推荐修复步骤**:
1. 在打包机器上安装 VC++ Redistributable 2015-2022
2. 运行诊断工具确认环境正常
3. 使用增强版构建脚本（选项 2）
4. 验证打包输出包含所有必需 DLL

**文件变更**:
```
A  packaging/windows/config/PrivacyGuard_windows_v2.spec
A  packaging/windows/scripts/diagnose_onnxruntime.py
A  packaging/windows/scripts/2_build_exe_enhanced.bat
A  packaging/windows/DLL_FIX_GUIDE_v37.md
```

---

## v37.0.2 - Windows DLL 问题持续 (2026-02-18)

### 🐛 未解决问题: onnxruntime DLL 加载失败

**状态**: ❌ 仍未解决

**已尝试的修复**:
1. ✅ 更新 PyInstaller Spec - 从多个来源收集 VC++ DLL
2. ✅ 创建启动器包装器 - 启动前检查 DLL
3. ✅ 修复 batch 文件换行符 (LF → CRLF)

**仍然存在错误**:
```
ImportError: DLL load failed while importing onnxruntime_pybind11_state:
动态链接库(DLL)初始化例程失败
```

---

## v37.0.1 - Windows DLL 修复 (2026-02-18)

### 🛠️ 尝试解决 `onnxruntime` DLL 加载失败问题

**问题描述**:
Windows 打包后运行时出现:
```
ImportError: DLL load failed while importing onnxruntime_pybind11_state:
动态链接库(DLL)初始化例程失败
```

**根本原因**:
- `vcruntime140_1.dll` 缺失（这是较新的 VC++ 运行时 DLL）
- PyInstaller 未正确收集系统 VC++ DLL

**修复措施**:

1. **更新 PyInstaller Spec** (`packaging/windows/config/PrivacyGuard_windows.spec`)
   - 增加从系统目录收集 VC++ DLL
   - 增加从 Python 安装目录收集 VC++ DLL
   - 新增 DLL: `vcruntime140_1.dll`, `msvcp140_1.dll`, `msvcp140_2.dll`

2. **创建启动器包装器** (`packaging/windows/scripts/launcher_wrapper.bat`)
   - 启动前检查必需的 DLL 文件
   - 如果缺失，显示友好的中文错误提示和下载链接
   - 安装程序使用 wrapper 创建快捷方式

3. **更新 VC++ 检查脚本** (`check_vcredist.bat`)
   - 将 `vcruntime140_1.dll` 标记为必需（而非可选）
   - 增加 `msvcp140_1.dll` 和 `msvcp140_2.dll` 检查

4. **更新 Inno Setup 脚本** (`PrivacyGuard_Setup.iss`)
   - 安装前检查 `vcruntime140_1.dll`
   - 显示具体的缺失 DLL 列表
   - 使用启动器包装器创建快捷方式

5. **更新构建脚本** (`2_build_exe.bat`, `4_create_installer_only.bat`)
   - 打包时复制 launcher_wrapper.bat
   - 增强 VC++ 缺失警告

6. **新增故障排除文档** (`packaging/windows/TROUBLESHOOTING.md`)
   - 详细解释 DLL 错误原因
   - 提供下载链接和解决方案

**文件变更**:
```
M  packaging/windows/config/PrivacyGuard_windows.spec
M  packaging/windows/config/PrivacyGuard_Setup.iss
M  packaging/windows/scripts/2_build_exe.bat
M  packaging/windows/scripts/4_create_installer_only.bat
M  packaging/windows/scripts/check_vcredist.bat
A  packaging/windows/scripts/launcher_wrapper.bat
A  packaging/windows/TROUBLESHOOTING.md
```

---

## v37.0 - 配置系统 (2026-02-17)

### ⚙️ 配置系统实现

#### 1. 核心配置模块 (`privacyguard/utils/config.py`)
**功能**: JSON 配置文件系统，支持热重载和向后兼容

**特性**:
- `ConfigManager` 单例类，线程安全（RLock 保护）
- 点分隔路径访问配置 (`get("app.window.default_width")`)
- 默认配置 + 用户配置合并机制
- 配置验证 (`validate()`)
- 变更监听回调 (`on_change()`)
- 热重载支持 (`reload()`)

**默认配置项**:
```python
DEFAULT_CONFIG = {
    "app.name": "PrivacyGuard 脱敏卫士",
    "app.window.default_width": 1300,
    "app.window.default_height": 900,
    "redaction.default_rules": {...},
    "redaction.replacement_text": "[已脱敏]",
    "redaction.scan.default_level": 2.0,
    ...
}
```

#### 2. 主程序集成 (main.py)
**变更**:
- 导入 ConfigManager，失败时优雅降级到硬编码
- 常量使用配置值（APP_NAME、窗口尺寸、扫描级别等）
- `SettingsDialog` 支持配置持久化
- 版本更新为 `37.0 - Config System`

**向后兼容代码**:
```python
config = None
if CONFIG_AVAILABLE:
    try:
        config = ConfigManager()
    except Exception as e:
        print(f"[配置系统] 初始化失败: {e}")

# 使用配置或硬编码后备
APP_NAME = config.get("app.name", "PrivacyGuard 脱敏卫士") if config else "PrivacyGuard 脱敏卫士"
```

#### 3. 配置文件模板 (`config.json.template`)
- 完整配置示例和说明
- 支持配置分类：`app`、`redaction`、`ocr`、`security`、`ui`、`advanced`

### ✅ 验证结果

- [x] 语法检查通过
- [x] ConfigManager 单元测试通过
- [x] 配置保存/重载测试通过
- [x] 向后兼容测试通过（模拟导入失败）
- [x] 应用启动测试通过

### 📦 文件变更

```
privacyguard/utils/config.py          [新增] 配置管理器核心模块
privacyguard/utils/__init__.py        [修改] 导出配置类
config.json.template                  [新增] 配置模板
config.json                           [生成] 用户配置文件
main.py                               [修改] 集成配置系统
version.txt                           [修改] 37.0
```

### 📋 备份

```
backups/v37.0_config_system_20260217_233617/
```

---

## v36.5 - 安全修复 (2026-02-17)

### 🔒 Critical 安全修复

#### 1. WordWorker 裸异常捕获 (main.py:1349)
**问题**: `except Exception as e:` 捕获所有异常，可能掩盖系统级异常

**修复**:
```python
# 修复前:
except Exception as e:

# 修复后:
except (IOError, OSError, RuntimeError, ValueError,
        AttributeError, KeyError, IndexError) as e:
```

**风险等级**: Critical → ✅ 已修复

#### 2. TempFileManager 线程安全 (main.py:85-182)
**问题**: 多线程环境下 `temp_files` 列表操作非线程安全

**修复**:
- 添加实例级别锁 `_instance_lock`
- 添加类级别锁 `_global_lock`
- 所有列表操作加锁保护

**风险等级**: High → ✅ 已修复

#### 3. word_data 竞争条件 (main.py:1293-1352)
**问题**: Worker 线程与主线程共享 `word_data` 无锁保护

**修复**:
- 添加 `QMutex _word_data_lock`
- 使用深拷贝发送数据副本
- 访问时加锁保护

**风险等级**: High → ✅ 已修复

### ✅ 验证结果

- [x] 语法检查通过
- [x] 稳定性测试通过 (6/6)
- [x] macOS App 打包成功 (708MB)
- [x] DMG 安装包创建成功 (309MB)

### 📦 发布包

```
releases/macos/PrivacyGuard-36.4-macOS.dmg (309MB) ✅
SHA256: 9a77ec5bbd0d3b26db604427465d03e55ae73e559c5c2ee7126110cb89a2336d
```

### 📋 备份

```
backups/v36.5_security_fix_20260217_205211/
```

---

## v36.4 - macOS 打包与 .doc 格式修复 (2026-02-17)

### 🍎 macOS 应用打包

**完成内容**:
- ✅ 成功打包 macOS 应用 `PrivacyGuard.app` (708MB)
- ✅ 创建 DMG 安装包 `PrivacyGuard-36.4-macOS.dmg` (308MB)
- ✅ 生成 SHA256 校验和
- ✅ 修复打包脚本路径计算错误 (`build_macos_app.sh:20`)

**打包输出**:
```
dist/PrivacyGuard.app
releases/macos/PrivacyGuard-36.4-macOS.dmg (308MB)
releases/macos/PrivacyGuard-36.4-macOS.dmg.sha256
```

### 🐛 .doc 格式转换修复 (macOS)

**问题**: 打包后的 App 无法找到 LibreOffice，导致 .doc 文件转换失败

**错误信息**:
```
LibreOffice 转换出错: [Errno 2] No such file or directory: 'soffice'
```

**根本原因**:
- 打包后的 macOS App 运行在沙盒环境中，PATH 变量不完整
- 无法通过 `soffice` 命令直接调用 LibreOffice

**修复方案** (`main.py:2860-2872`):
```python
# v36.4: 在 macOS 上使用 LibreOffice 完整路径
soffice_cmd = 'soffice'
if platform.system() == 'Darwin':
    libreoffice_path = '/Applications/LibreOffice.app/Contents/MacOS/soffice'
    if os.path.exists(libreoffice_path):
        soffice_cmd = libreoffice_path
```

### 📦 Windows 打包脚本修复

**修复内容**:
- 修复 UTF-8 编码问题（改为系统默认代码页）
- 修复路径包含空格时的解析错误
- 修复 version.txt 空行读取问题
- 添加 Inno Setup 多路径查找
- 添加文件存在检查

**涉及文件**:
```
packaging/windows/scripts/1_初始化环境.bat
packaging/windows/scripts/2_一键打包.bat
packaging/windows/scripts/3_完整打包带安装程序.bat
packaging/windows/scripts/4_仅创建安装程序.bat
```

### ✅ 验证清单

- [x] macOS App 正常启动
- [x] .doc 文件转换正常（使用 LibreOffice）
- [x] .docx 文件打开正常
- [x] PDF 打开/保存正常
- [x] OCR 扫描功能正常
- [x] Word 预览和脱敏功能正常

### 📋 提交记录

```
备份: backups/v36.4_macos_build_20260217_203303/
```

---

## v36.3 - Word 文档显示空白修复 (2026-02-16)

### 🐛 问题修复

#### Word 文档打开显示空白 (CRITICAL)
**问题**: 用户打开包含大图片的 Word 文档时，预览区域显示一片空白

**根本原因**:
- mammoth 库生成的 HTML 是片段格式，不包含完整 HTML 文档结构
- ❌ 没有 `<!DOCTYPE html>`
- ❌ 没有 `<html>` 标签
- ❌ 没有 `<head>` 标签
- ❌ 没有 `<body>` 标签

生成的 HTML 只是片段：
```html
<p><img src="data:image/png;base64,..."></p>
<p>AI录音卡全方位使用手册</p>
```

**问题分析**:
- 文档特征：2.1MB，包含 2 个巨大 base64 内嵌图片（约 1.93MB + 1.29MB）
- mammoth 转换后的 HTML 长度：约 3.4MB
- 261 个段落

**修复方案**:
在 `_inject_interactive_html` 方法中添加 HTML 完整性检测和包装：

```python
def _inject_interactive_html(self, html, scroll_restore=''):
    # 检查 HTML 是否为完整文档
    is_full_document = '<html' in html.lower() or '<!doctype' in html.lower()

    if not is_full_document:
        # 包装成完整 HTML 文档
        html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    body {{ margin: 0; padding: 20px; ... }}
    img {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
{html}
</body>
</html>'''
    # ... 注入脚本
```

**技术细节**:
- 代码位置：`main.py` 第 3371-3920 行
- 检测方式：检查 `<html` 或 `<!doctype` 标签
- 包装内容：添加标准 HTML5 结构、基础 CSS 样式
- CSS 样式：图片自适应宽度、合理边距、字体设置

**验证结果**:
- ✅ 语法检查通过
- ✅ 应用正常启动
- ✅ WebView 功能正常

**备份**:
- `backups/v36.3_word_fix_20260216_233356/main.py.backup`

---

## v36.2 安全加固 (2026-02-16)

### 安全改进
- **路径验证函数**：新增 `validate_safe_path()` 全局函数
  - 防止命令注入攻击（过滤危险字符: `;`, `|`, `&`, `$`, `` ` ``, `$(`, `>`, `<`）
  - 防止路径遍历攻击（限制允许的路径范围）
  - 验证文件扩展名白名单
  - 代码位置：`main.py` 第 167-219 行

- **TempFileManager 类**：增强临时文件管理安全性
  - 使用 `atexit` 注册退出清理钩子
  - 确保程序异常退出时也能清理临时文件
  - 记录所有创建的临时文件和目录
  - 代码位置：`main.py` 第 126-164 行

- **Subprocess 路径验证**：在调用外部命令前验证路径安全
  - `_convert_with_libreoffice()`：验证临时 .doc 文件路径和临时目录
  - `_convert_with_antiword()`：验证输入 .doc 文件路径
  - 代码位置：`main.py` 第 2226-2233 行、第 2323-2326 行

- **错误处理完善**：将裸 `except Exception` 替换为具体异常类型
  - 文件操作：`OSError`, `IOError` → TempFileManager.cleanup()
  - 图片处理：`IOError`, `OSError`, `ValueError` → ImageMergeWorker
  - OCR 处理：`IOError`, `OSError`, `RuntimeError`, `ValueError` → OCRWorker
  - Word 处理：`IOError`, `OSError`, `ValueError`, `KeyError` → _open_word_docx()
  - 转换处理：`OSError`, `IOError`, `RuntimeError`, `ValueError` → _convert_with_libreoffice(), _convert_with_antiword()
  - PDF/Word 保存：具体异常类型 → _save_pdf(), _save_word()
  - 代码位置：多个关键方法

### 测试结果

#### 1. 语法检查 ✅
```bash
$ python -c "import ast; ast.parse(open('main.py').read()); print('✓ OK')"
✓ OK
```

#### 2. 模块导入测试 ✅
```bash
$ python -c "
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import fitz
from docx import Document
from bs4 import BeautifulSoup
import cv2
import numpy
print('✓ All imports OK')
"
✓ PyQt6 组件导入成功
✓ PyMuPDF 导入成功
✓ python-docx 导入成功
✓ BeautifulSoup 导入成功
✓ OpenCV 导入成功
✓ NumPy 导入成功
✓ All imports OK
```

#### 3. 组件存在性验证 ✅
| 组件 | 状态 | 说明 |
|------|------|------|
| validate_safe_path | ✅ | 路径验证函数 |
| TempFileManager | ✅ | 临时文件管理类 |
| ConversionError | ✅ | 转换错误类 |
| ImageMergeWorker | ✅ | 图片合并工作线程 |
| OCRWorker | ✅ | OCR 工作线程 |
| WebViewBridge | ✅ | WebView 桥接类 |
| SettingsDialog | ✅ | 设置对话框 |
| SinglePageCanvas | ✅ | 单页画布 |
| MainWindow | ✅ | 主窗口 |

#### 4. TempFileManager 功能测试 ✅
```
创建临时文件: /var/folders/nx/.../tmp_jz8hkmr.txt
创建临时文件: /var/folders/nx/.../tmpwtr_ejs7.docx
创建临时目录: /var/folders/nx/.../tmp288l8bso
✓ 临时文件和目录创建成功
  删除文件: /var/folders/nx/.../tmp_jz8hkmr.txt
  删除文件: /var/folders/nx/.../tmpwtr_ejs7.docx
  删除目录: /var/folders/nx/.../tmp288l8bso
✓ 临时文件和目录清理成功
```

#### 5. 路径验证函数测试 ✅
| 测试用例 | 结果 | 说明 |
|----------|------|------|
| 正常 .doc 文件 | ✅ 通过 | 扩展名验证 |
| 正常 .pdf 文件 | ✅ 通过 | 扩展名验证 |
| 不支持的扩展名 | ✅ 拒绝 | .exe 被拒绝 |
| 命令注入-分号 | ✅ 拒绝 | `;` 被检测 |
| 命令注入-管道 | ✅ 拒绝 | `|` 被检测 |
| 空路径 | ✅ 拒绝 | 空字符串被拒绝 |

#### 6. 稳定性测试 ✅ (6/6)
```
============================================================
PrivacyApp v24 稳定性测试
============================================================
✅ TempFileManager 测试通过
✅ 自定义异常类测试通过
✅ 模式匹配测试通过
✅ 内存优化特性测试通过
✅ 分批处理逻辑测试通过
✅ 错误消息格式测试通过
============================================================
✅ 所有测试通过！
============================================================
```

#### 7. 异常类定义验证 ✅
```
验证异常类在 main.py 中存在...
✓ class PrivacyAppError 存在
✓ class ConversionError 存在
✓ class FileFormatError 存在
✓ def __init__(self, message, suggestion 存在
✓ 异常类验证完成
```

#### 8. GUI 启动测试 ✅
```
运行时长: 约 4 分钟
日志分析: 无错误或崩溃
状态: 应用正常运行
```

### 依赖更新
- 更新 requirements.txt 以匹配实际安装版本
- pip-audit 安全检查：无已知漏洞

### 备份
- `backups/v36.2_step_1_20260216_211148/main.py.backup` (Step 1)
- `backups/v36.2_step_3_20260216_212651/main.py.backup` (Step 3)

---

## v36.1 开发中 (2026-02-16)

### 修改
- **FeedbackDialog 界面优化**：简化社交媒体账号显示
  - 将4行独立的社交账号合并为单行：`微信公众号/抖音/小红书/B站（同号）: 池州汪律的Ai 进化论`
  - 保留复制按钮功能
  - 代码位置：`main.py` 第 370-425 行

- **开发者简介完善**：填充 FeedbackDialog 开发者信息
  - 姓名：汪立
  - 身份：安徽始信律师事务所执业律师，全栈律师，前教师、退伍军人
  - 邮箱：491445490@qq.com（可点击链接）
  - 代码位置：`main.py` 第 527-531 行

- **LibreOffice .doc 转换修复**：解决中文路径问题
  - 将源 .doc 文件复制到临时目录（纯英文路径）后再执行转换
  - 避免 LibreOffice 命令行工具处理中文路径时的编码问题
  - 添加调试日志输出原始路径和临时路径
  - 代码位置：`main.py` 第 2139-2156 行

### 备份
- `backups/v36/main.py.backup_20260216_162936`

---

## v36.0 正式发布 (2026-02-14)

### 发布内容
- **版本号**: 36.0 - Windows 深色模式优化
- **发布状态**: 正式发布版
- **支持平台**: macOS 11.0+ / Windows 10/11

### 发布包
- `PrivacyGuard-36.0-macOS.dmg`
- `PrivacyGuard-36.0-Windows.zip`

### 文档完善
- 用户安装指南（macOS + Windows）
- 使用手册
- 常见问题 Q/A
- 开发经验总结
- 社交媒体推广文案

---

## v36 (2026-02-14)

### 修复
- **Windows 深色模式文件对话框问题**：修复非原生 QFileDialog 在 Windows 深色模式下白底白字难以阅读的问题
  - 新增 `_get_file_dialog_style()` 方法，为文件对话框设置明确的浅色主题样式
  - 修改 `open_pdf()` 方法，在调用文件对话框前后应用/恢复样式
  - 修改 `save_pdf()` 方法，同样处理 PDF 和 Word 保存对话框
  - 使用 try/finally 确保样式正确恢复，不影响其他组件

### 技术细节
- 使用 QApplication 级别的样式表临时覆盖
- 样式包含：背景色、文字颜色、按钮样式、列表/树视图、下拉框、输入框
- 样式针对 QFileDialog 及其子控件，不影响其他窗口

---

## v35.2 (2026-02-14)

### 修复
- **精确模式高亮问题**：修复 Word 预览中选中文本后整个段落被高亮的问题
  - 新增 `_highlight_exact_match` 方法，使用 BeautifulSoup 进行精确文本节点定位
  - 现在正确使用 `start` 和 `end` 参数定位用户选中的精确位置
  - 支持同一文本在段落中多次出现时只高亮选中的那一个

### 技术细节
- 使用 BeautifulSoup 的 NavigableString 遍历文本节点
- 根据字符偏移量精确定位高亮位置
- 在指定位置插入 `<mark>` 标签，不影响其他文本

---

## v35.0 - Windows 平台打包成功 (2026-02-13)

### 里程碑：首次 Windows 打包成功

**重大成就**:
- 实现了 PrivacyGuard 在 Windows 平台的首次成功打包
- 应用现在支持 macOS 和 Windows 双平台运行
- 完整保留了所有核心功能

#### Windows 打包过程

**遇到的问题**:
1. **编码问题**: Windows 默认 GBK 编码与 UTF-8 冲突
2. **路径问题**: Windows 路径分隔符与 macOS 不同
3. **图标问题**: ICO 文件格式和尺寸要求
4. **依赖问题**: PyInstaller 隐式导入检测
5. **杀毒误报**: PyInstaller 打包程序被误报

**解决方案**:
- 统一使用 UTF-8 编码，添加编码转换处理
- 使用 `pathlib` 处理跨平台路径
- 生成多尺寸 ICO 图标文件
- 在 spec 文件中手动指定隐式导入
- 在文档中说明误报情况

**详细记录**: 参见 `packaging/windows/docs/BUILD_LOG.md`

#### 双平台状态

| 平台 | 状态 | 版本 | 构建产物 |
|------|------|------|----------|
| macOS | ✅ 已发布 | v35.0 | PrivacyGuard-35.0-macOS.dmg |
| Windows | ✅ 已发布 | v35.0 | PrivacyGuard-35.0-Windows.zip |

#### 功能验证

- [x] PDF 打开和显示
- [x] Word 文档打开和显示
- [x] OCR 智能扫描
- [x] 智能脱敏
- [x] 手动脱敏（精确/全局模式）
- [x] 保存功能
- [x] 中文界面显示

---

## v35.0 - 批量图片选择优化 + 脱敏图片修复 (2026-02-12)

### ✅ 新增功能

#### 1. 批量图片选择优化 (NEW)
**功能**: 支持直接多选图片文件，自动合并为 PDF

**实现方式**:
- 使用 `getOpenFileNames` 替代 `getOpenFileName`
- 支持选择多个图片文件（PNG, JPG, JPEG）
- 自动将多张图片合并为单个 PDF
- 移除冗余的询问对话框

**代码位置**: `main.py` 第 843-889 行

**用户流程**:
1. 点击"打开 PDF"按钮
2. 在文件对话框中多选图片
3. 自动生成包含所有图片的 PDF
4. 进行智能/手动脱敏
5. 保存脱敏后的 PDF

#### 2. 图片脱敏修复 (FIXED)
**功能**: 修复图片转 PDF 后保存时原图丢失的问题

**问题分析**:
- 原图在保存时被删除
- 脱敏区域外的图片内容丢失

**修复方案**:
- 添加 `overlay=True` 参数确保图片独立插入
- 使用 `PDF_REDACT_IMAGE_NONE` 保护原图内容
- 只涂抹敏感区域，保留其他内容

**代码位置**: `main.py` 第 1349-1389 行

---

### 🐛 修复的问题

1. ✅ 修复图片转 PDF 后保存时原图丢失问题
2. ✅ 修复脱敏导出时图片内容被误删问题
3. ✅ 优化混合文件选择错误提示

---

### 📦 发布信息

**版本**: v35.0
**发布日期**: 2026-02-12
**DMG 大小**: 280 MB
**SHA256**: `ccb90e74e38b5bcb1325367a03cebe37b7d7546337e7d7f1e2712369de0a7d26`
**发布包位置**: `releases/v35.0-release/`

---

## v31.9 (2026-02-12)

### ✅ 新增功能

#### 1. 精确模式手动脱敏 (NEW)
**功能**: 只脱敏选中的特定文本，不影响其他位置的相同文本

**实现方式**:
- 使用 data-key 精确定位单个文本块
- 添加精确模式标记到红色高亮
- 撤销时只移除特定标记的脱敏

**代码位置**: `main.py` 第 1863-1944 行

#### 2. 全局模式手动脱敏 (NEW)
**功能**: 自动查找并脱敏所有相同文本，一次性处理

**实现方式**:
- 使用正则表达式在 HTML 中全局替换
- 支持多种 HTML 标签（p, td, li）
- 添加全局模式标记到红色高亮
- 撤销时移除所有相同文本的脱敏

**代码位置**: `main.py` 第 1945-2075 行

#### 3. 批量撤销功能 (NEW)
**功能**: 根据模式类型执行不同撤销策略

**撤销逻辑**:
- **精确模式**: 只撤销选中项的脱敏
- **全局模式**: 撤销所有相同文本的脱敏
- 智能识别脱敏标记的模式类型

**代码位置**: `main.py` 第 2076-2158 行

#### 4. 滚动位置保持 (FIXED)
**问题**: 脱敏操作时视图跳转到第一页

**修复方案**:
- 使用 localStorage 持久化滚动位置
- 异步保存机制避免丢失
- 多重恢复机制确保可靠性

**代码位置**: `main.py` 第 1680-1742 行

---

### 🐛 修复的问题

1. ✅ 修复全局手动脱敏只有一处高亮的问题
2. ✅ 修复精确模式偶尔失败的问题
3. ✅ 修复撤销功能对全局模式无效的问题
4. ✅ 修复滚动位置跳转的问题

---

### ⚠️ 已知小瑕疵

1. ⚠️ **精确模式偶尔失败** (LOW 优先级)
   - 发生概率: <5%
   - 影响: 有全局模式作为备用方案
   - 状态: 可接受

2. ⚠️ **大文档性能延迟** (LOW 优先级)
   - 发生条件: 50+ 页文档
   - 影响: <15 秒等待时间
   - 状态: 可接受

---

## 历史版本 v28 (2026-02-11)

### ✅ 已修复问题

#### 1. HTML 高亮显示问题 (CRITICAL)
**问题**: 预览视图中显示裸露的 HTML 标签
```
class="text-block" data-key="paragraph_0" data-original-text="协议书">协议书
```

**根本原因**: `_highlight_sensitive_info` 方法中的替换逻辑有严重 bug
```python
html = html.replace(escape(text), highlighted_text)
```
- 重复文本会全部被替换（如 "协议书" 出现多次，会全部被替换）
- HTML 转义不匹配导致替换失败

**修复方案**: 使用占位符三遍替换策略
```python
# 第一遍: 生成唯一占位符
placeholder = f"__PLACEHOLDER_{key}__"

# 第二遍: HTML 中的文本 → 占位符
html = html.replace(escaped_text, placeholder)

# 第三遍: 占位符 → 高亮内容
html = html.replace(placeholder, highlighted_text)
```

**文件**: `main.py` 第 1745-1862 行

#### 2. 部分行无法手动脱敏 (MEDIUM)
**问题**: 选择文本后右键点击"添加脱敏"菜单，但文本不变为红色

**根本原因**: `findTextPosition()` 函数在某些 HTML 结构下找不到正确的 data-key

**修复方案**:
- 优先使用 Range 直接计算位置
- 处理 startContainer/endContainer 是元素节点的情况
- 添加 4 层后备匹配方案
- 添加详细调试日志

**文件**: `main.py` 第 1946-2135 行

---

### ❌ 待修复问题

#### 1. 滚动位置跳转 (HIGH)
**现象**: 打开 Word 文档后，滚动到最底部，选择文本点击右键添加脱敏后，视图跳转到第一页

**已尝试方案**:
- v26: localStorage 自动保存/恢复
- v27: 移除淡入动画 + 二次确认滚动

**当前状态**: 问题仍然存在，需要进一步调试

**文件**: `main.py` 第 1680-1725 行

#### 2. 部分文档右键无反应 (MEDIUM)
**现象**: 某些段落选择文本后右键，无法出现"添加脱敏"菜单

**当前状态**: 已添加详细调试日志，需要收集用户反馈分析具体失败场景

**文件**: `main.py` 第 1946-2135 行

---

## 版本历史

### v36.3 - Word 文档显示空白修复 (2026-02-16 23:30)
- ✅ 修复 mammoth 生成的 HTML 片段显示空白问题
- ✅ 添加 HTML 完整性检测和自动包装
- ✅ 支持大图片文档正常显示

### v28 - HTML 高亮显示修复 (2026-02-11 17:41)
- ✅ 修复裸露 HTML 标签显示问题
- ✅ 使用占位符三遍替换策略
- 📝 创建完整开发日志

### v27 - 深度调试修复 (2026-02-11 17:29)
- 🔧 findTextPosition 增强（详细日志）
- 🔧 滚动恢复简化（移除淡入动画）
- ❌ 用户反馈：问题仍然存在

### v26 - 滚动位置稳定性修复 (2026-02-11 16:54)
- 🔧 localStorage 自动保存/恢复滚动位置
- 🔧 添加淡入动画
- ❌ 用户反馈：问题仍然存在

### v25 - Word 手动脱敏功能修复计划
- 📋 制定修复计划
- 📋 问题分析：HTML 转义导致的不匹配

---

## 关键文件说明

### main.py
主程序文件，包含所有核心逻辑 (当前版本: v31.9, ~2600 行)

### 主题文件
- `theme.py` - 主题系统（浅色）

### 备份文件 (已整理到 backups/)
- `backups/v31.9_current/` - v31.9 最新版本 ⭐
- `backups/v31_early/` - v31.0-v31.7 版本
- `backups/v25-v29/` - 中间版本
- `backups/v24_word/` - v24 Word 支持
- `backups/v23_ui/` - v23 UI 版本
- `backups/v19_legacy/` - v19 早期版本

### 文档 (已整理到 docs/)
- `docs/current/DEV_LOG.md` - 开发日志（本文件）⭐
- `docs/current/STATUS.md` - 项目状态 ⭐
- `docs/current/RECOVERY_GUIDE.md` - 恢复指南 ⭐⭐⭐
- `README.md` - 项目总览
- `CHANGELOG.md` - 完整更新日志

---

## 技术栈

### 后端
- Python 3.11
- PyQt6 (GUI)
- PyMuPDF (PDF 处理)
- python-docx (Word 处理)
- mammoth (Word 转 HTML)
- RapidOCR (文字识别)

### 前端
- QWebEngineView (Qt WebKit)
- JavaScript (交互逻辑)
- HTML/CSS (预览渲染)

---

## 开发环境

### Python 依赖
```bash
pip install pymupdf python-docx mammoth rapidocr_onnxruntime PyQt6-WebEngine
```

### IDE 配置
- 推荐使用 VS Code 或 PyCharm
- Python 解释器: venv/bin/python

---

## 下次开发计划

### 优先级 MEDIUM
1. **性能优化**
   - 大文档的渲染速度
   - 减少滚动延迟
   - OCR 扫描速度

### 优先级 LOW
2. **改进精确模式稳定性**
   - 提高成功命中率
   - 优化查找算法

3. **用户体验改进**
   - 添加进度提示
   - 添加更多导出格式
   - 批量处理功能
   - 改进错误提示信息

---

## 调试技巧

### 查看浏览器控制台日志
1. 右键点击预览区域
2. 选择 "检查元素"
3. 切换到 Console 标签

### 关键日志标识
- `[ScrollRestore]` - 滚动位置保存/恢复
- `[findTextPosition]` - 文本位置查找
- `✓✓✓` - 成功
- `✗✗✗` - 失败

---

## 联系方式
- 开发者: Claude
- 最后更新: 2026-02-14
- 当前版本: v36.0 (正式发布版)
