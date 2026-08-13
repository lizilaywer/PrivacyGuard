# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 本仓库 CLAUDE.md 默认使用中文撰写。后续 Claude Code 实例在本项目中工作时，请以本文档为准。

---

## 项目概览

**项目名称**：PrivacyGuard 脱敏卫士
**当前版本**：v37.7.6（版本标识：`37.7.6 - Full Convergence Remediation`）
**最后更新**：2026-05-16
**当前状态**：v37.7.6 全面重复实现收敛完成；P1-P4 修复全部完成；基线测试 79/79 通过

PrivacyGuard 是一个基于 Python + PyQt6 的桌面端智能文档脱敏工具，主要面向 PDF 与 Word 文档的隐私信息处理场景。

### 当前已具备的能力

- **PDF 脱敏**
  - 文字型 PDF：通过 PyMuPDF 文本层搜索命中
  - 图片型 PDF：通过 RapidOCR 识别扫描内容
  - 混合型 PDF：文本层命中 + 嵌入图片块 OCR 同步命中
  - 手动矩形框选脱敏
- **Word 脱敏**
  - 智能扫描识别
  - 手动精确 / 全局脱敏
  - 多字段替换规则（`exact` / `regex`）
  - 批量替换（支持 `.docx` / `.doc`）
- **Word 双栏对比预览**
  - 左栏：原文预览（含 OCR / 手动高亮）
  - 右栏：替换后预览（合并优先级 `rule > manual > ocr`）
- **交互能力**
  - 拖拽打开文件
  - 高级设置面板
  - 批量入口已并入“打开 / 拖拽”流程
- **跨平台打包**
  - Windows 与 macOS 平台的 PyInstaller 打包脚本

---

## 接手时先读这些（按顺序）

1. `docs/current/STATUS.md`
2. `docs/current/DEV_LOG.md`
3. `docs/current/V38_UI_REFACTOR_PLAN.md`
4. `CHANGELOG.md`
5. `rollback_journal.md`
6. `docs/current/PRIORITY_REMEDIATION_PLAN.md`
7. `docs/diary/20260309_2338_release_sync_diary.md`
8. `docs/diary/20260311_pyinstaller_packaging_fix_diary.md`

如果只是做轻量改动或 bug 修复，至少也要先看 `docs/current/STATUS.md`、`CHANGELOG.md` 和 `rollback_journal.md` 三份，再决定动手方向。

---

## 当前技术事实（不要违反）

### 主架构现状

- `main.py` 仍是活跃的运行时入口，且当前仍是单体文件。
- `privacyguard/` 子包已经承载了部分抽离出的共享模块与工作器，但 **运行时逻辑并未全部迁移完成**。
- 不要让 `main.py` 与 `privacyguard/*` 之间的逻辑重新出现分叉 / 重复实现（这是 v37.7.6 收敛工作的核心目标）。

### 版本号单一来源

- 版本号唯一来源：`version.txt`
- `main.py` 与 `privacyguard.__version__` 都从这里读取
- 任何打包配置（`packaging/`、`docs/packaging/`、版本资源）都必须与 `version.txt` 保持一致

### 当前生效的配置路径

- 运行时的实际配置类是 `main.py` 中的 `SimpleConfig`
- `privacyguard/utils/config.py` 里也存在模块化的 `ConfigManager` 工具，但 **除非已经显式切换过**，否则不要把它当作运行时配置路径
- 修改配置相关逻辑前，请先确认当前生效的是哪一条路径

### OCR 依赖的懒加载约束

- `privacyguard` 包导入必须保持 **懒加载**
- `RapidOCR` 只允许在实际执行 OCR 时才进行初始化
- **不要** 在 `privacyguard/__init__.py` 或 `privacyguard/workers/__init__.py` 中重新加入包级别的 eager import

### 混合型 PDF 的处理路径

混合型 PDF 既不是纯文字也不是纯扫描，必须按以下顺序处理：

1. 文本层命中收集
2. 通过 `page.get_text("dict")` 发现页面上的嵌入图片块
3. 对图片块做 OCR
4. 把 OCR 局部框坐标换算回页面坐标系
5. 与文本层命中合并后做去重

共享逻辑统一收敛在 `privacyguard/ocr/mixed_pdf.py`。

---

## 关键运行时数据结构

### PDF 状态

```python
self.page_data[page_num] = {"ocr": [...], "manual": [...]}
```

- `ocr`：当前页通过 OCR 识别得到的脱敏候选
- `manual`：用户手动框选出来的矩形脱敏区域

### Word 状态

```python
self.word_data[key] = {
    "text": ...,
    "ocr": [...],
    "manual": [...],
    # ...
}
self.word_replace_rules  # 会话级多字段替换规则
```

- `text`：当前 word 块的原始文本
- `ocr` / `manual`：分别记录 OCR 命中与手动命中
- `word_replace_rules`：跨 word 块共享的会话级规则集

### Word 预览模型（按 `data-key` 的局部更新）

当前实际生效的渲染路径：

1. DOCX → HTML（通过 `mammoth`）
2. 输出 HTML 时给每个 word 块打上 `data-key`
3. 左栏按 block 更新原文高亮片段
4. 右栏按 block 更新合并后的替换片段
5. **不再**总是用整页 `setHtml()`，而是走按 key 的 JavaScript DOM 局部 patch

需要注意的细节：

- 对比模式启动时，右栏可能是隐藏或空白的
- `cp20` 增加了“每个面板各自记录已加载源”的能力
- `cp27` 把增量 DOM patch 限制在真正的 word 块内，避免高亮节点被破坏
- 当对比模式从空状态进入活动状态时，右栏必须先重新加载完整文档，再应用局部更新

---

## 主要文件与模块

### 应用层

- `main.py`：当前活跃的应用运行时（仍然较大，注意不要随意拆分）
- `theme.py`：UI 主题与样式定义
- `version.txt`：版本号唯一来源
- `config.json`：本地运行时配置（不要手动改格式，模板在 `config.json.template`）

### `privacyguard/` 抽离出的模块（仅承担部分逻辑）

- `privacyguard/__init__.py`：包元数据 + 懒加载导出
- `privacyguard/ocr/text_pdf.py`：文字型 PDF 的命中收集（共享逻辑）
- `privacyguard/ocr/mixed_pdf.py`：混合型 PDF 的图片块 OCR 辅助（共享逻辑）
- `privacyguard/ocr/rapidocr.py`：RapidOCR 适配
- `privacyguard/ocr/manager.py`、`privacyguard/ocr/base.py`：OCR 抽象与管理
- `privacyguard/workers/ocr_worker.py`：OCR 工作线程
- `privacyguard/workers/word_worker.py`：Word 处理工作线程
- `privacyguard/workers/image_merge.py`：图片合并工作线程
- `privacyguard/utils/doc_converter.py`：`.doc` → `.docx` 转换工具
- `privacyguard/utils/config.py`：模块化的配置管理器（注意：当前 **不是运行时生效路径**）
- `privacyguard/utils/exceptions.py`：统一异常类型
- `privacyguard/utils/temp_manager.py`：统一临时文件管理
- `privacyguard/utils/security.py`：路径校验与 `resource_path` 工具

---

## 常用命令

### 启动应用

```bash
cd /mnt/g/Project/PrivacyGuard
python3 main.py
```

> README 中保留的 macOS 路径 `/Users/a49144/Desktop/codexhub/PrivacyGuardApp` 是历史路径，本仓库当前实际根目录为 `/mnt/g/Project/PrivacyGuard`。

### 语法编译检查

```bash
python3 -m compileall -q main.py privacyguard tests
```

### 主回归测试（基线 79/79）

```bash
python3 -m unittest \
  tests.unit.test_mixed_pdf_ocr \
  tests.test_path_validation \
  tests.unit.test_ocr_api \
  tests.unit.test_package_imports \
  tests.unit.test_pdf_text_hit_dedup \
  tests.unit.test_app_config \
  tests.unit.test_word_replace_rules \
  tests.unit.test_batch_word_replace \
  tests.unit.test_config_alignment \
  tests.unit.test_fstring_safety \
  tests.unit.test_convergence \
  -v
```

### 运行单个测试

```bash
# 运行某一个具体测试类
python3 -m unittest tests.unit.test_mixed_pdf_ocr -v

# 运行某一个具体测试方法
python3 -m unittest tests.unit.test_mixed_pdf_ocr.TestMixedPdfOCR.test_something -v
```

### 查看版本号

```bash
cat version.txt
```

### 轻量快速验证（启动 + 编译 + 单元测试）

```bash
cd /mnt/g/Project/PrivacyGuard
python3 -m compileall -q main.py privacyguard tests \
  && python3 -m unittest \
      tests.unit.test_mixed_pdf_ocr \
      tests.test_path_validation \
      tests.unit.test_ocr_api \
      tests.unit.test_package_imports \
      tests.unit.test_pdf_text_hit_dedup \
      tests.unit.test_app_config \
      tests.unit.test_word_replace_rules \
      tests.unit.test_batch_word_replace \
      tests.unit.test_config_alignment \
      tests.unit.test_fstring_safety \
      tests.unit.test_convergence \
      -v \
  && python3 main.py
```

---

## 打包

打包相关文档以 `docs/packaging/` 为准，不要再用旧的临时笔记：

- `docs/packaging/README.md`
- `docs/packaging/windows-packaging-guide.md`
- `docs/packaging/macos-packaging-guide.md`
- `packaging/README.md`

主要打包命令：

```bash
# macOS
./packaging/macos/scripts/build_complete.sh

# Windows
packaging/windows/scripts/build_complete.bat
```

> Windows 打包历史上出现过 `privacyguard.utils.security` 模块导入失败的回归，修复点在 `cp30`，遇到类似问题先翻 `rollback_journal.md` 中 `cp30` 的条目。

---

## 当前已建立的检查点

- `20260309_runtime_remediation_cp18_verified`
- `20260309_word_compare_bugfix_cp20_verified`
- `20260309_mixed_pdf_ocr_cp23_verified`
- `20260309_release_sync_cp25_verified`
- `20260310_word_preview_highlight_cp27_verified`
- `20260310_release_sync_cp29_verified`
- `20260311_pyinstaller_packaging_fix_cp30_verified`
- `v38_ui_refactor_cp31_20260313_140645`

回滚参考：

- `rollback_journal.md`
- `ROLLBACK_GUIDE.md`
- `restore_checkpoint.sh`

---

## 当前开发方向

默认主轨道：

1. 在已完成 v38 代码层之上做截图驱动的 UI 细节抛光
2. Phase 2：批量替换支持“每文件单独规则映射”
3. 批量规则集模板管理
4. 替换后预览按来源筛选高亮（`rule / manual / ocr`）

如果 UI 抛光轨道暂时暂停、并且也没有回归需要修，默认下一阶段工作：

1. Phase 2：每文件单独规则映射
2. 批量规则集模板管理
3. 替换后预览按来源筛选高亮

如果 PDF OCR 出现回归，优先检查这四点：

1. 文本层 vs 图片块是否被正确分流
2. 图片裁剪（image clip）提取是否有效
3. OCR 局部框是否正确换算回页面坐标
4. 合并后的命中是否做了去重

---

## 给后续 Claude 实例的提醒

- 仓库是个人开发者项目，沟通请保持简洁、可执行，不要堆砌套话。
- `main.py` 当前仍然是单体，但 `privacyguard/` 已经在做有意识的拆分；如果你的改动属于“共享逻辑”，优先放进 `privacyguard/`，避免在 `main.py` 再写一份实现导致 v37.7.6 已经收敛掉的重复问题回潮。
- OCR 路径改动后必须跑 `tests.unit.test_mixed_pdf_ocr`、`tests.unit.test_pdf_text_hit_dedup`、`tests.unit.test_ocr_api`、`tests.unit.test_package_imports`，确保懒加载 / 去重 / 坐标换算三件事没有被破坏。
- Word 双栏预览改动后必须跑 `tests.unit.test_word_replace_rules`、`tests.unit.test_batch_word_replace`、`tests.unit.test_fstring_safety`，并真机打开一个对比模式验证右栏不再整块空白。
- 任何版本号相关改动都需要同步：`version.txt` → `main.py` → `privacyguard/__version__` → `packaging/` → `docs/packaging/` → `CHANGELOG.md`。
