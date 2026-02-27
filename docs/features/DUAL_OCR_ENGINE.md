# PrivacyGuard 双 OCR 引擎技术文档

**版本**: v37.2.0 (Dual OCR Engine)
**状态**: ⚠️ **已废弃** - v37.4.0 起完全移除 PaddleOCR，统一使用 RapidOCR
**日期**: 2026-02-22 → 废弃于 2026-02-23

> **注意**: 本文档仅用于历史参考。自 v37.4.0 起，项目已完全移除 PaddleOCR，统一使用 RapidOCR 单引擎架构。详见 `CHANGELOG.md` v37.4.0 条目。

---

### 问题背景

扫描型 PDF 子字符串脱敏时涂抹区域偏移（如 "Privacy" 在 "PrivacyGuard" 中定位不准）

### 解决方案

双 OCR 引擎架构：
- **RapidOCR** (默认): 速度快，行级检测框
- **PaddleOCR** (可选): 字符级精准坐标

### 成果

用户可在高级设置中选择 PaddleOCR，实现像素级精准子字符串定位

---

## 技术架构

### 目录结构

```
privacyguard/ocr/
├── __init__.py       # 模块导出
├── base.py           # OCRResult, CharInfo 数据结构
├── rapidocr.py       # RapidOCR 引擎封装
├── paddleocr.py      # PaddleOCR 引擎封装
└── manager.py        # OCREngineManager 引擎管理
```

### 双引擎架构

```
┌─────────────────────────────────────────┐
│         OCREngineManager                │
├─────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────┐  │
│  │  RapidOCR   │  │   PaddleOCR     │  │
│  │  (默认)     │  │   (字符级)      │  │
│  │  速度快     │  │   精度高        │  │
│  │  行级框     │  │   字符坐标      │  │
│  └─────────────┘  └─────────────────┘  │
│         ↑                    ↑          │
│         └────────┬───────────┘          │
│                  ▼                      │
│         Engine Selector                 │
│    prefer_char_level: bool              │
│    自动回退机制                         │
└─────────────────────────────────────────┘
```

### 统一数据结构

```python
@dataclass
class CharInfo:
    """单字符信息"""
    char: str
    box: List[List[float]]  # 四点坐标
    confidence: float

@dataclass
class OCRResult:
    """OCR 识别结果"""
    text: str           # 完整文本
    box: List[List[float]]  # 整行框
    chars: List[CharInfo]   # 字符列表（RapidOCR为空）
    confidence: float
    engine: str         # 来源引擎标识
```

---

## 性能对比

| 特性 | RapidOCR | PaddleOCR |
|------|----------|-----------|
| 速度 | 快 | 慢 2-3 倍 |
| 精度 | 行级检测框 | 字符级坐标 |
| 适用场景 | 大文档批量处理 | 子字符串精准脱敏 |
| 体积 | ~20MB | ~17MB (已内置) |
| 默认启用 | ✅ 是 | ❌ 需手动选择 |

---

## 使用指南

### 默认使用 (RapidOCR)
无需配置，保持原有使用方式

### 启用字符级 OCR (PaddleOCR)
1. 打开应用
2. 进入「高级设置」
3. 选择「OCR 引擎设置」
4. 选择「PaddleOCR (字符级 - 精度高)」
5. 保存设置
6. 扫描 PDF，子字符串脱敏更精准

### 配置项
```json
{
  "ocr": {
    "engine": "paddleocr"
  }
}
```

---

## 功能验证结果

| 功能项 | 状态 | 验证时间 |
|--------|------|----------|
| RapidOCR 引擎注册 | ✅ 通过 | 2026-02-22 |
| PaddleOCR 引擎注册 | ✅ 通过 | 2026-02-22 |
| 引擎自动选择逻辑 | ✅ 通过 | 2026-02-22 |
| 字符级坐标计算 | ✅ 通过 | 2026-02-22 |
| 自动回退机制 | ✅ 通过 | 2026-02-22 |
| 高级设置 UI | ✅ 通过 | 2026-02-22 |
| 配置持久化 | ✅ 通过 | 2026-02-22 |

**测试环境**:
- macOS + Python 3.11
- NumPy 1.26.4
- PaddleOCR 2.10.0 + 模型 17MB
- RapidOCR 1.2.3

---

## 实施阶段

### Phase 1: OCR 引擎模块 ✅
- 创建 `privacyguard/ocr/` 目录
- 实现统一的 `OCRResult` 数据结构
- 封装 RapidOCR 和 PaddleOCR 引擎

### Phase 2: OCRWorker 改造 ✅
- 添加 `use_char_level_ocr` 参数
- 支持字符级坐标计算 (`_calculate_from_chars`)
- 使用引擎管理器获取引擎

### Phase 3: UI 更新 ✅
- SettingsDialog 添加"OCR 引擎设置"分组
- 两个单选按钮：RapidOCR / PaddleOCR
- 可用性检测和提示

### Phase 4: 配置和集成 ✅
- `config.json.template` 添加 `ocr.engine`
- `requirements.txt` 添加依赖
- 文档更新

---

## 稳定性设计

1. **默认引擎不变**: RapidOCR 仍是默认
2. **自动回退**: PaddleOCR 失败时自动切换到 RapidOCR
3. **异常隔离**: 引擎错误不影响整体扫描流程
4. **延迟加载**: 引擎在首次使用时才初始化

---

## 文件变更清单

**新增文件**:
- `privacyguard/ocr/__init__.py`
- `privacyguard/ocr/base.py`
- `privacyguard/ocr/rapidocr.py`
- `privacyguard/ocr/paddleocr.py`
- `privacyguard/ocr/manager.py`

**修改文件**:
- `main.py` - OCRWorker, SettingsDialog, MainWindow
- `config.json.template` - 添加 ocr.engine 配置
- `requirements.txt` - 添加 paddleocr, paddlepaddle
- `docs/current/STATUS.md` - 添加 v37.2.0 条目
- `docs/current/DEV_LOG.md` - 添加开发日志

---

**完成时间**: 2026-02-22
**版本**: v37.2.0 (Dual OCR Engine)
**状态**: ✅ 已发布
