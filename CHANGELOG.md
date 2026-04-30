# PrivacyGuard 脱敏卫士 - 更新日志

本文档记录了 PrivacyGuard 脱敏卫士的所有重要更新。

---

## [Unreleased]

### 🔄 下一步

- 真机截图驱动的最后一轮观感抛光
- 正式发布前的 Windows / macOS 产物验收

---

## [37.7.4] - 2026-03-18

### 🚀 发布审查与版本同步

- 定义补丁版本：`v37.7.4`
- 版本标识更新为：`37.7.4 - Release Audit and Final Polish`
- 当前 active 文档、打包说明、恢复入口、项目索引已统一同步到 `v37.7.4`
- Windows 版本资源已重新生成并同步到 `37.7.4.0`
- Windows 安装器默认回退版本已同步到 `37.7.4`
- 当前主回归基线已统一到 `52/52`

### 🧹 运行时体验收口

- 修复首次从空首页点击“选择文件”前先清理资源导致的首页抖动
- 保留“已有文档时先清理”的原有逻辑，不影响后续再次打开文件的资源回收

### 🖼️ Word 预览稳定性与性能

- 修复带嵌入图片的 Word 文档可能空白、打不开的问题
- 嵌入图片预览改为落地临时资源目录加载，避免双栏 HTML 内联超大 `base64 data URI`
- 大文档首开性能得到改善，双栏预览资源重复膨胀问题已收口

### 📝 批量 Word 结果摘要增强

- 批量结果页左下角“本轮摘要”现在会展示：
  - 本次替换规则
  - 每条规则在各文档中的成功替换条数
- 结果摘要不再只显示文档总数和成功/失败数量

### ✅ 验证

- `python3 -m compileall -q main.py privacyguard tests packaging`
- 主回归：`52/52` 通过
- `python3 packaging/windows/scripts/generate_version_info.py`

---

## [37.7.3] - 2026-03-11

### 🐛 Bug 修复

#### PyInstaller 打包模块导入失败修复

**问题现象**：
- Windows 打包完成后，打开应用出现错误弹窗：`ModuleNotFoundError: No module named 'privacyguard.utils.security'`

**根因**：
- `privacyguard/utils/security.py` 第 56 行存在 f-string 语法错误
- Python 3.11 不允许在 f-string 的 `{}` 表达式中直接使用反斜杠
- 语法错误导致模块无法被导入，PyInstaller 的 `collect_submodules()` 返回空列表

**修复内容**：
- 修复 `privacyguard/utils/security.py` 中的 f-string 语法错误
- 将反斜杠先赋值给变量，再在 f-string 中使用
- 将 `privacyguard/__init__.py`、`privacyguard/utils/__init__.py`、`privacyguard/ocr/__init__.py` 中的相对导入改为绝对导入
- 优化 `packaging/windows/config/PrivacyGuard_windows.spec` 中的 hiddenimports 配置
- 添加 `packaging/windows/config/hook-privacyguard.py` hook 文件
- 添加 `packaging/windows/config/runtime_hook_privacyguard.py` 运行时 hook

**经验教训**：
- 仔细阅读打包日志，不要忽略任何 WARNING
- Python 3.11 对 f-string 的语法检查更严格
- 语法错误会导致模块无法导入，进而影响 PyInstaller 的模块检测

---

## [37.7.2] - 2026-03-10

### 📦 版本/文档/打包方案同步
- 定义补丁版本：`v37.7.2`
- 版本标识更新为：`37.7.2 - Word Preview Refresh Fix`
- active 文档、日志、恢复入口、快速上手文档已同步到当前基线
- `packaging/` 与 `docs/packaging/` 当前打包方案已同步到 `v37.7.2`
- Windows 默认安装器版本与 EXE 版本资源已同步到 `37.7.2`

### 🪲 Word 预览增量刷新修复
- **修复正文块误更新**：修复 Word 原文预览在“高级设置 -> 保存”后出现异常红色高亮的问题。
- **根因修正**：增量更新脚本改为只更新正文块容器，不再误更新带 `data-key` 的高亮 `<mark>` 节点，避免嵌套高亮和串位。
- **块标记补齐**：Word HTML 块映射统一增加 `data-word-block="1"` 标记，`BeautifulSoup` 和 regex fallback 两条路径都一致。
- **测试补充**：新增针对增量刷新选择器和 regex fallback 块标记的回归测试。

### ✅ 测试
- `python3 packaging/windows/scripts/generate_version_info.py`：通过
- `python3 -m compileall -q main.py privacyguard tests`：通过
- 主回归：`28/28` 通过

---

## [37.7.1] - 2026-03-09

### 📦 发布同步
- 定义补丁版本：`v37.7.1`
- 版本标识更新为：`37.7.1 - Mixed PDF OCR Hotfix`
- active 文档、日志、快速入口、恢复指南已同步到当前基线
- `packaging/` 与 `docs/packaging/` 当前打包方案已同步到 `v37.7.1`
- Windows 默认安装器版本与 EXE 版本资源已同步

### 🖼️ 混合型 PDF OCR 热修复

- **修复混合页漏脱敏**：修复“同一页文本层能脱敏、嵌入图片 / 扫描区域漏脱敏”的问题。
- **混合扫描链路**：PDF 页面改为统一执行：
  - 文本层命中
  - 图片块 OCR 命中
  - 无文本层时回退整页 OCR
- **共享图片块逻辑**：新增 `privacyguard/ocr/mixed_pdf.py`，统一图片块提取、裁剪渲染、OCR 命中与坐标偏移。
- **双实现同步**：`main.py` 与 `privacyguard/workers/ocr_worker.py` 同步接入，避免主链和模块化 worker 再次漂移。

### 🔒 运行时安全与导入稳定性整改
- **路径校验统一**：`main.py` 不再保留旧版前缀判断，统一使用共享安全实现。
- **包级懒导入**：`privacyguard` 与 `privacyguard.workers` 改为懒导入，避免 `import privacyguard` 时因 OCR 依赖缺失直接崩溃。
- **OCR worker 延迟初始化**：RapidOCR 改为在真正执行 OCR 时初始化。

### ⚡ 文本型 PDF 与 Word 预览性能整改
- **文本 PDF 去重**：重复命中的同一字符串只搜索一次，避免重复追加相同矩形。
- **共享文本页实现**：新增 `privacyguard/ocr/text_pdf.py`，主程序与模块化 worker 共用。
- **Word 预览局部更新**：左右预览改为按 `data-key` 局部刷新，不再依赖整页重绘作为活动路径。
- **原文高亮改造**：左侧高亮改为分块构建，降低重复文本串位风险。
- **compare 空白热修复**：修复右侧“替换后预览”从空白页首次切入 compare 模式时不加载文档、导致整块空白的问题。

### 💾 配置与版本一致性
- **设置真正持久化**：`SimpleConfig` 新增 `save()`，设置对话框改为批量写入后统一落盘。
- **新增持久化项**：`redaction.custom_keywords`
- **版本来源统一**：应用主版本和包版本统一从 `version.txt` 读取。

### ✅ 测试
- 新增并通过：
  - 混合型 PDF 图片块 OCR 测试
  - 路径前缀绕过测试
  - `privacyguard` 安全导入测试
  - 文本型 PDF 去重测试
  - 配置保存测试
  - 原文高亮分段测试
  - compare 模式空白页 reload 判定测试
- 当前回归：`26/26` 通过

---

## [37.7.0] - 2026-03-02

### 🆕 Word 多字段替换与批量替换（Phase 1 落地）

#### 新增功能
- **多字段替换规则引擎**：支持 `exact/regex`、多规则启用开关、顺序执行、JSON 导入导出。
- **单文档替换规则弹窗**：保持原有规则弹窗交互，支持会话级规则编辑和应用。
- **批量替换流程**：支持 `.docx + .doc`，`.doc` 优先 LibreOffice 转换，失败回退 antiword。
- **批量进度与错误决策**：底部进度同步，失败可选“跳过继续/停止任务”。

#### 交互与 UI 改进
- **批量替换入口并入“打开/拖拽”**：
  - 当选择或拖拽 `>=2` 个 Word 文件时，自动进入批量替换流程。
  - 启动批量前会先弹出“替换规则设置”界面，避免强制先去高级设置。
- **高级设置整合**：
  - “统一替换文本”并入“2. 自定义关键词”右侧区域。
  - 新增“打开替换规则设置”入口按钮（复用原规则弹窗）。
- **Word 双栏预览优化**：
  - 顶部“原文预览/替换后预览”标题区改为紧凑头部，降低视觉拥挤。

#### 预览融合修复（关键）
- **替换后预览改为融合渲染**：右侧预览统一展示三类处理结果：
  - 规则替换
  - 手动脱敏
  - 智能脱敏
- **统一优先级**：`规则替换 > 手动脱敏 > 智能脱敏`。
- **统一高亮**：右侧预览对所有已替换字段使用一致高亮样式，且撤回后实时同步消失。

#### 稳定性与测试
- 新增规则分段融合单元测试，覆盖“规则+手动”组合替换分段输出。
- 本轮回归：路径安全、OCR API、Word 规则、Word 批量等测试通过。

---

## [37.6.0] - 2026-02-28

### 🎯 文件拖拽打开功能

#### 新增功能
- **拖拽打开文件**: 支持将文件从文件管理器拖拽到软件预览区域直接打开
- **视觉反馈**: 拖拽时预览区域边框变色（绿色=支持，红色=不支持）
- **多文件支持**: 支持同时拖拽多个图片文件自动合并为PDF
- **格式兼容**: 支持PDF、Word(.doc/.docx)、图片(.jpg/.png/.bmp/.tiff)

#### 技术实现
- 重写 PyQt6 拖拽事件处理方法 (`dragEnterEvent`, `dragMoveEvent`, `dropEvent`)
- `_update_drag_visual_feedback()` 实现动态边框颜色反馈
- `_handle_dropped_files()` 复用现有文件打开逻辑，确保行为一致
- 跨平台支持（macOS/Windows/Linux）

#### 使用方式
```
1. 打开文件管理器（Finder/资源管理器）
2. 选中要打开的文件
3. 拖拽文件到 PrivacyGuard 预览区域
4. 看到绿色边框时释放鼠标即可打开
```

---

## [37.6.1] - 2026-02-28

### 🔧 修复: Word文档拖拽后无法继续拖拽

#### 问题描述
- Word文档(.docx)拖拽打开后，无法再拖拽其他文件
- PDF和图片拖拽后可以继续拖拽其他文件

#### 根本原因
QWebEngineView（Word预览控件）默认会拦截拖拽事件，阻止事件传递到父窗口。

#### 解决方案
- 在 `render_word_preview()` 中添加 `self.word_preview.setAcceptDrops(False)`
- 禁用Word预览的拖拽接受，让事件穿透到MainWindow

---

## [37.5.0] - 2026-02-27

### 🆕 印章自动检测功能

#### 新增功能
- **印章自动检测**: 使用 OpenCV 图像处理自动检测 PDF 中的红色印章区域
- **高级设置选项**: 新增"印章"复选框，默认不勾选
- **智能过滤**: 基于颜色（红色）、形状（圆形度）、尺寸多维度过滤

#### 技术实现
- **纯 OpenCV 实现**: 无需额外依赖，使用现有的 OpenCV 和 numpy
- **HSV 颜色检测**: 检测红色区域（两个 HSV 区间）
- **形态学操作**: 闭运算和开运算去噪
- **轮廓分析**: 面积、宽高比、圆形度多重过滤
- **参数阈值**:
  - 红色像素占比: >= 30%
  - 圆形度: >= 0.5
  - 宽高比: 0.5 ~ 2.0

#### 配置更新
```json
{
  "redaction": {
    "default_rules": {
      "印章": {
        "pattern": "__SEAL_DETECTION__",
        "enabled": false,
        "description": "使用 OpenCV 自动检测并脱敏红色印章区域"
      }
    },
    "seal_detection": {
      "enabled": false,
      "method": "opencv",
      "min_red_ratio": 0.3,
      "min_circularity": 0.5
    }
  }
}
```

#### 性能影响
- **处理时间**: 每页增加约 0.1-0.2 秒
- **内存**: 无额外内存占用
- **模型大小**: 无需下载模型

#### 已知限制
- 仅支持红色印章
- 仅支持圆形/椭圆形印章
- 可能误判红色圆形图标

#### 🔧 Bug 修复 (2026-02-27)
- **关键修复**: 文本型 PDF 分支也执行印章检测
  - 之前印章检测只在图像 PDF 分支（`else`）执行
  - 现在文本 PDF 分支（`if is_text_pdf`）也会渲染图像并检测印章
  - 修复了勾选"印章"后某些 PDF 无法检测的问题

---

## [37.4.0] - 2026-02-23

### 🗑️ PaddleOCR 完全移除

#### 决策背景
经过多次尝试修复 PaddleOCR 的 Y 轴偏移问题（v37.3.14 - v37.3.21），发现 PaddleOCR 3.4 的字符级坐标系统与项目架构存在根本性的兼容问题：
- 字符级 box 格式与行级 box 格式不一致
- 坐标转换复杂且容易出错
- 维护成本高，稳定性无法保证

**决策**: 完全移除 PaddleOCR，以 RapidOCR 单引擎为准，确保性能快速、稳定、安全。

#### 移除内容

**代码文件修改**:
- `main.py`: 移除 OCR 引擎选择逻辑，只保留 RapidOCR
- `privacyguard/ocr/paddleocr.py`: 删除整个文件
- `privacyguard/ocr/manager.py`: 简化为只管理 RapidOCR
- `privacyguard/ocr/__init__.py`: 移除 PaddleOCR 导出

**UI 修改**:
- `SettingsDialog`: 移除"OCR 引擎设置"分组中的引擎选择部分
- 保留检测框调节、偏移设置等功能

**模型文件删除**:
- `privacyguard/ocr/models/paddleocr/`: 删除整个目录

**依赖移除**:
- `requirements.txt`: 移除 `paddleocr` 和 `paddlepaddle` 依赖

**配置更新**:
- `config.json` / `config.json.template`: 移除 `ocr.engine` 配置项

#### 预期收益
- 代码量减少约 500+ 行
- 依赖减少（移除 paddleocr/paddlepaddle）
- 启动速度提升
- 维护复杂度降低
- 稳定性提升

---

## [37.0.10] - 2026-02-21

### 🔧 修复

#### LibreOffice 路径检测修复
- 修复打包后无法找到 LibreOffice 导致 .doc 文件无法打开的问题
- 在 macOS 上使用完整路径检测 `/Applications/LibreOffice.app/Contents/MacOS/soffice`

### ⚙️ 配置调整

#### 扫描模式配置
- **新增普通模式 (1.0x)**：更快速的扫描选项
- **默认模式调整**：从高精 (2.0x) 改为普通 (1.0x)

**配置变更** (`config.json`, `config.json.template`):
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

| 项目 | 修改前 | 修改后 |
|------|--------|--------|
| 默认模式 | 高精 (2.0x) | **普通 (1.0x)** |
| 可选模式 | [1.5, 2.0] | **[1.0, 1.5, 2.0]** |
| 新增模式 | - | **普通 (1.0x)** |

---

## [37.0.4] - 2026-02-19

### 📱 微信二维码功能更新

#### 界面改进
- **"吐槽"对话框 - 关注开发者部分重新设计**
  - 原单行显示改为两行清晰展示
  - 第一行: "微信公众号: 池州汪律的Ai进化论" + "扫码关注"按钮
  - 第二行: "抖音/小红书/B站（同号）: 池州有个汪律师" + "复制"按钮

- **新增微信公众号二维码对话框**
  - 点击"扫码关注"按钮弹出
  - 显示微信公众号二维码 (assets/wx_qrcode.png)
  - 提示文字: "微信扫一扫，关注公众号获取更多AI工具"

#### 资源文件
- 新增 `assets/wx_qrcode.png` (微信公众号二维码)
- 所有 PyInstaller spec 文件已更新包含新资源

### 📦 打包方案全面更新

#### 新增打包脚本
- `packaging/windows/scripts/build_complete.bat` - Windows 一键打包（含DLL自动复制）
- `packaging/macos/scripts/build_complete.sh` - macOS 一键打包（含DMG创建）
- `clean_project.bat` / `clean_project.sh` - 项目清理脚本（保留备份）

#### Windows DLL 问题最终解决方案
- 在打包后自动复制 VC++ DLL (`vcruntime140_1.dll` 等)
- 创建 `PACKAGING_GUIDE.md` 完整打包指南

#### 更新所有 PyInstaller Spec
- Windows: `PrivacyGuard_windows.spec`, `PrivacyGuard_windows_v2.spec`
- macOS: `PrivacyGuard.spec`
- 全部包含 `assets` 目录打包

#### 验证结果
- ✅ 语法检查通过
- ✅ 界面显示正常（两行布局）
- ✅ "扫码关注"按钮功能正常
- ✅ 资源文件正确打包

---

## [37.0] - 2026-02-17

### ⚙️ 配置系统

#### 新增内容
- **JSON 配置文件系统** (`privacyguard/utils/config.py`)
  - `ConfigManager` 单例类，支持线程安全（RLock 保护）
  - 点分隔路径访问配置 (`get("app.window.default_width")`)
  - 默认配置 + 用户配置合并机制
  - 配置验证 (`validate()`) 和热重载支持 (`reload()`)
  - 向后兼容（配置模块失败时降级到硬编码）

- **配置文件结构** (`config.json`)
  - `app`: 应用名称、窗口尺寸、反馈URL
  - `redaction`: 脱敏规则、替换文本、扫描参数
  - `ocr`: OCR 精度、缩放范围
  - `security`: 路径验证、允许扩展名
  - `ui`: 主题、动画、提示
  - `advanced`: 调试模式、临时文件清理

- **主程序集成**
  - 导入 ConfigManager，失败时优雅降级
  - 常量使用配置值（APP_NAME、窗口尺寸、扫描级别等）
  - `SettingsDialog` 支持配置持久化
  - 版本更新为 `37.0 - Config System`

- **打包配置更新**
  - macOS spec 文件添加 privacyguard 包和 config 文件
  - Windows spec 文件添加 privacyguard 包和 config 文件
  - 更新 hiddenimports 包含所有隐私保护模块

#### 向后兼容
```python
# 配置加载失败时的降级处理
if config:
    APP_NAME = config.get("app.name", "PrivacyGuard 脱敏卫士")
else:
    APP_NAME = "PrivacyGuard 脱敏卫士"  # 硬编码后备
```

#### 验证清单
- ✅ 语法检查通过
- ✅ ConfigManager 单元测试通过
- ✅ 配置保存/重载测试通过
- ✅ 向后兼容测试通过
- ✅ 应用启动测试通过

---

## [36.4] - 2026-02-17

### 🍎 macOS 应用打包发布

#### 新增内容
- **macOS 应用打包** (`packaging/macos/`)
  - 成功打包 `PrivacyGuard.app` (708MB)
  - 创建 DMG 安装包 `PrivacyGuard-36.4-macOS.dmg` (308MB)
  - 生成 SHA256 校验和
  - 支持拖拽安装到 Applications

- **.doc 格式转换修复** (macOS)
  - 修复打包 App 中 PATH 不完整导致无法找到 LibreOffice 的问题
  - 添加 macOS 平台 LibreOffice 完整路径检测 (`/Applications/LibreOffice.app/Contents/MacOS/soffice`)
  - 影响范围: `main.py` `_convert_with_libreoffice()` 方法

### 🔧 代码重构与资源管理优化

#### 修复内容
- **PDF 文档资源管理** (`_open_pdf_file()`, `save_pdf()`)
  - 修复 `_open_pdf_file` 中打开新 PDF 时旧文档未关闭的问题
  - 修复 `save_pdf` 中 `doc_save` 在异常情况下未关闭的问题
  - 添加 try-finally 块确保文档始终正确关闭

- **代码重构** (`_inject_interactive_html()`)
  - 将 555 行的巨型函数拆分为小型函数
  - 提取 JavaScript 代码为模块级常量 `_INTERACTIVE_JS_CODE`
  - 新增 `_wrap_html_document()` 辅助方法处理 HTML 包装
  - 主函数从 ~555 行缩减至 ~21 行

### 📦 Windows 打包脚本修复

#### 修复内容
- 修复 UTF-8 编码问题（改为系统默认代码页）
- 修复路径包含空格时的解析错误
- 修复 version.txt 空行读取问题
- 添加 Inno Setup 多路径查找
- 添加文件存在检查

#### 验证清单
- ✅ 语法检查通过
- ✅ 应用正常启动
- ✅ PDF 打开/关闭正常
- ✅ Word 预览正常
- ✅ .doc 文件转换正常 (macOS + LibreOffice)
- ✅ macOS App 打包成功

---

## [36.3] - 2026-02-16

### 🐛 热修复：Word 文档显示空白问题

#### 修复内容
- **Word 文档显示空白** (`_inject_interactive_html()`)
  - 修复 mammoth 生成的 HTML 片段导致 QWebEngineView 显示空白的问题
  - 添加 HTML 完整性检测：检查 `<html` 或 `<!doctype` 标签
  - 自动将片段包装成完整 HTML5 文档结构
  - 添加基础 CSS 样式支持（图片自适应、合理边距）

#### 技术细节
- **问题根源**: mammoth 库生成的 HTML 是片段格式，不含 `<html>`, `<head>`, `<body>` 等标签
- **影响范围**: 所有使用 mammoth 转换的 Word 文档，尤其是包含大图片（>1MB）的文档
- **修复位置**: `main.py` 第 3371-3920 行 (`_inject_interactive_html` 方法)

#### 测试验证
- ✅ 语法检查通过
- ✅ 应用正常启动
- ✅ WebView 功能正常

---

## [36.2] - 2026-02-16

### 🔒 安全加固版本

#### 安全改进
- **路径验证函数** (`validate_safe_path()`)
  - 新增全局路径验证函数 (main.py:167-219)
  - 防护命令注入攻击（过滤危险字符: `;`, `|`, `&`, `$`, `` ` ``, `$(`, `>`, `<`）
  - 防护路径遍历攻击（限制允许的路径范围）
  - 支持文件扩展名白名单验证
  - 应用到 `_convert_with_libreoffice()` 和 `_convert_with_antiword()`

- **临时文件管理增强** (`TempFileManager`)
  - 使用 `atexit` 注册退出清理钩子
  - 确保程序异常退出时也能清理临时文件
  - 记录所有创建的临时文件和目录

- **错误处理完善**
  - 11 处关键位置的裸 `except Exception` 替换为具体异常类型
  - 文件操作: `OSError`, `IOError`
  - 图片处理: `IOError`, `OSError`, `ValueError`
  - OCR 处理: `IOError`, `OSError`, `RuntimeError`, `ValueError`
  - Word 处理: `IOError`, `OSError`, `ValueError`, `KeyError`
  - 转换处理: `OSError`, `IOError`, `RuntimeError`, `ValueError`

- **依赖安全审计**
  - 使用 `pip-audit` 检查依赖安全漏洞
  - 结果: 无已知漏洞
  - 更新 `requirements.txt` 到实际安装版本

#### 测试验证
- 语法检查通过
- 模块导入测试通过 (PyQt6, PyMuPDF, python-docx, OpenCV, Pillow)
- 稳定性测试通过 (6/6)
- 异常类定义验证通过
- GUI 启动测试通过

#### 其他改进
- **开发者简介完善**
  - 开发者: 汪立（安徽始信律师事务所执业律师）
  - 身份: 全栈律师 | 前教师 | 退伍军人
  - 邮箱: 491445490@qq.com（可点击链接）
  - 位置: FeedbackDialog 第 527-531 行

#### 文档更新
- 新增 `docs/security-hardening.md` 安全加固详细说明
- 更新 `docs/current/STATUS.md` 为正式发布状态
- 更新 `docs/current/DEV_LOG.md` 开发日志
- 更新 `CLAUDE.md` 开发指南（版本号和安全章节）

---

## [37.0] - 2026-02-16

### 🚀 重大改进：内存管理、线程安全与性能优化

#### 改进
- **OCR内存管理** (v37)
  - 保证OCR引擎在所有情况下正确清理
  - 添加内存分析支持（通过 PRIVACYGUARD_MEMORY_PROFILE 环境变量）
  - 使用 try-finally-finally 确保OCR引擎在每批次后释放
  - 删除循环内的 `import gc`，改为顶层导入

- **错误处理** (v37)
  - OCR异常现在会显示用户友好的错误对话框
  - 添加结构化日志记录到 `logs/privacyguard.log`
  - 添加 `error_signal` 信号用于异常传播

- **线程安全** (v37)
  - Word预览添加操作队列和防抖机制
  - 使用 QMutex 和 QMutexLocker 保护共享状态
  - 防止快速操作导致的竞态条件

- **性能优化** (v37)
  - HTML高亮添加30秒超时保护
  - 大文档分批处理（>100个匹配时）
  - 正则表达式模式缓存
  - 每5批次让出事件循环，保持UI响应

#### 新增
- **日志系统** (v37)
  - 添加 `setup_logging()` 函数
  - 日志文件位置：`logs/privacyguard.log`
  - 支持 DEBUG 和 INFO 级别

#### 依赖更新
- 添加 `psutil>=5.9.0`（可选，用于内存分析）

---

## [36.0] - 2026-02-16

### 📝 开发维护更新

#### 开发记录
- **UI 优化尝试与回滚** (2026-02-16)
  - 尝试优化按钮样式和界面布局
  - 发现效果不佳，已回滚至 v36.0 正式版本
  - 保留原有稳定 UI 设计

#### 备份
- 创建 `main.py.backup_v36.0_final_20260216_172414`
- 创建 `theme.py.backup_v36.0_final_20260216_172414`

---

## [36.0] - 2026-02-14

### 🎉 正式发布版本

#### 修复
- **🪟 Windows 深色模式文件对话框修复**
  - 修复非原生 QFileDialog 在 Windows 深色模式下白底白字难以阅读的问题
  - 新增 `_get_file_dialog_style()` 方法为文件对话框设置浅色主题
  - 使用 try/finally 确保样式正确恢复

#### 技术细节
- 使用 QApplication 级别的样式表临时覆盖
- 样式包含：背景色、文字颜色、按钮样式、列表/树视图、下拉框、输入框
- 样式针对 QFileDialog 及其子控件，不影响其他窗口

#### 发布信息
- **版本**: 36.0 (正式发布版)
- **支持平台**: macOS 11.0+, Windows 10/11
- **发布包**: `releases/v36.0-release/`

---

## [35.0] - 2026-02-12 (macOS) / 2026-02-13 (Windows)

### 🎉 重大更新：批量图片选择 + 脱敏图片修复 + Windows 平台支持

#### 新增功能
- **📸 批量图片选择**
  - 支持在文件对话框中多选图片
  - 自动将多张图片合并为单个 PDF
  - 移除冗余的询问步骤，提升用户体验

- **🪟 Windows 平台支持** (NEW)
  - 首次实现 Windows 平台打包成功
  - 支持 Windows 10/11
  - 完整的功能支持（PDF、Word、OCR、手动脱敏）

#### 改进
- 简化文件选择流程（直接多选，无需询问）
- 图片转 PDF 后脱敏不再丢失原图
- 优化脱敏算法，只涂抹敏感区域
- 跨平台路径处理优化

#### 修复
- ✅ 修复图片转 PDF 后保存时原图丢失的问题
- ✅ 修复脱敏导出时图片内容被误删的问题
- ✅ 优化混合文件选择错误提示
- ✅ 修复 Windows 平台编码问题
- ✅ 修复 Windows 平台路径问题

#### 技术细节
- 使用 `getOpenFileNames` 支持多选
- 添加 `overlay=True` 确保图片独立插入
- 使用 `PDF_REDACT_IMAGE_NONE` 保护原图内容
- Windows 打包使用 PyInstaller 6.x
- 统一使用 UTF-8 编码处理

#### 发布信息
- **版本**: 35.0
- **macOS DMG 大小**: 280 MB
- **macOS SHA256**: `ccb90e74e38b5bcb1325367a03cebe37b7d7546337e7d7f1e2712369de0a7d26`
- **Windows ZIP 大小**: ~75 MB
- **支持平台**: macOS 11.0+, Windows 10/11

---

## [33.0] - 2026-02-12

### 🎯 重大更新：自适应视图系统

#### 核心功能
- **📐 真正的自适应计算**
  - 根据窗口和页面尺寸动态计算缩放比例
  - 支持任意尺寸页面完整显示
  - 自动限制缩放范围（0.5-4.0）

- **🔄 窗口大小改变自动适应**
  - 新增 `resizeEvent()` 事件监听
  - 拖动窗口边缘时自动重新调整
  - 保持页面完整显示

#### 改进
- 重构 `fit_width()` 为 `fit_page()` 实现完整适应
- 修复 JavaScript 字符串使用原始字符串（消除 SyntaxWarning）
- 优化缩放计算算法（取宽高较小值确保完整显示）

#### 修复
- ✅ 修复固定 100% 缩放无法适应大页面的问题
- ✅ 修复窗口改变时不自动调整的问题
- ✅ 修复 `scroll_area` 属性名错误（应为 `scroll`）
- ✅ 修复所有 `fit_width` 引用遗漏
- ✅ 消除 Python SyntaxWarning（`\s` 转义问题）

#### 技术细节
```python
# 动态适应算法
zoom_w = canvas_width / page_width
zoom_h = canvas_height / page_height
self.zoom_level = min(zoom_w, zoom_h)  # 确保完整显示
```

#### 测试结果
- ✅ 小页面（A4）适应正常
- ✅ 大页面完整显示
- ✅ 横向页面正确适应
- ✅ 窗口调整自动响应
- ✅ 缩放范围限制有效

---

## [31.9] - 2026-02-12

### 🎉 重大更新：双模式手动脱敏系统

#### 新增功能
- **🎯 精确模式手动脱敏**
  - 只脱敏选中的特定文本
  - 不影响其他位置的相同文本
  - 精确控制，避免过度脱敏

- **📄 全局模式手动脱敏**
  - 自动查找并脱敏所有相同文本
  - 一次性处理，效率高
  - 支持批量撤销

- **🔄 批量撤销功能**
  - 全局模式：一键撤销所有相同文本的脱敏
  - 精确模式：单独撤销选中项
  - 智能识别模式类型

- **📍 滚动位置保持**
  - 脱敏操作时保持在当前位置
  - 使用 localStorage 持久化
  - 异步保存机制 + 多重恢复确保可靠性

#### 改进
- 完全重构高亮显示机制（Python 端处理）
- 为所有文本块添加 data-key 标识
- 优化右键菜单交互逻辑
- 改进撤销功能的用户体验
- 添加详细的调试日志

#### 修复
- ✅ 修复全局手动脱敏只有一处高亮的问题
- ✅ 修复精确模式偶尔失败的问题
- ✅ 修复撤销功能对全局模式无效的问题
- ✅ 修复滚动位置跳转的问题

#### 技术细节
- 使用正则表达式在 HTML 中直接替换
- 支持多种 HTML 标签（p, td, li）
- 异步保存滚动位置避免丢失
- 改进 data-key 标记的容错性

#### 已知问题
- 精确模式在极少数情况下可能失败（<5%，有全局模式备用）
- 超大文档（50+页）可能有轻微延迟（<15秒）

---

## [31.8] - 2026-02-11

### 新增功能
- **全局手动脱敏功能**
  - 自动查找并脱敏所有相同文本

### 修复
- 修复只有一处高亮的问题

---

## [31.0 - 31.7] - 2026-02-11

### 改进
- Python 高亮代码显示
- 队列处理优化
- data-key 标记改进
- 高亮修复功能增强

---

## [30.3] - 2026-02-11

### 新增功能
- Ultra Compact Highlighting 高亮方案
- Word 文档实时预览
- 手动脱敏功能（基础版）
- 右键菜单交互

### 改进
- 优化高亮宽度和间距
- 改进滚动恢复机制
- 提升 UI 响应速度

---

## [29.0] - 2026-02-11

### 改进
- 深度修复

---

## [28.0] - 2026-02-11

### 修复
- **HTML 高亮显示问题** (CRITICAL)
  - 预览视图不再显示裸露的 HTML 标签
  - 使用占位符三遍替换策略

### 改进
- 改进 findTextPosition 函数
- 添加详细调试日志

---

## [27.0] - 2026-02-11

### 改进
- findTextPosition 增强（详细日志）
- 滚动恢复简化（移除淡入动画）

---

## [26.0] - 2026-02-11

### 新增功能
- localStorage 自动保存/恢复滚动位置
- 页面可见性监听

---

## [25.0] - 2026-02-11

### 改进
- Word 手动脱敏功能修复
- 问题分析：HTML 转义导致的不匹配

---

## [24.0] - 2026-02-11

### 新增功能
- **Word 文档支持**
  - 支持 .docx 和 .doc 格式
  - LibreOffice 转换支持
  - 系统环境检测

### 改进
- 使用 mammoth 进行 HTML 转换
- 优化表格处理逻辑
- 改进错误提示

---

## [23.3] - 2026-02-11

### 改进
- 自适应视图默认改为 100%
- 进度条显示百分比，更醒目
- 移除深色主题，简化界面

---

## [23.2] - 2026-02-11

### 新增功能
- 主题系统（浅色/深色）
- 窗口状态管理
- 按钮样式系统
- UI 组件现代化

---

## 历史版本

### [19.x] - 早期版本
- 基础 PDF 脱敏功能
- OCR 智能识别
- 手动标记功能
- 双页模式
- 缩放功能

---

## 版本命名规则

- **主版本号**：重大架构变更或新功能
- **次版本号**：功能改进
- **修订号**：bug 修复和小改进

---

## 即将发布

### [32.0] - 计划中
- 性能优化（大文档支持）
- 批量文档处理
- 更多导出格式
- 云存储集成

---

**最后更新**: 2026-03-18
**当前版本**: v37.7.4 (Release Audit and Final Polish)
