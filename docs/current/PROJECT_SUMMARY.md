# PrivacyGuard 项目摘要

**当前版本：** v37.7.4  
**版本标识：** `37.7.4 - Release Audit and Final Polish`  
**最后更新：** 2026-03-18  
**当前状态：** 可发布；`v37.7.4` 运行基线稳定，v38 UI 改造代码层已完成，当前进入真机截图驱动抛光阶段

---

## 项目定位

PrivacyGuard 是一个基于 Python + PyQt6 的桌面文档脱敏工具，面向 PDF 与 Word 文档场景，提供 OCR 智能脱敏、手动精确脱敏、批量替换、以及可回滚的迭代开发流程。

---

## 当前能力边界

### PDF
- 文本型 PDF：文本层搜索脱敏
- 图片型 PDF：RapidOCR 脱敏
- 混合型 PDF：文本层 + 嵌入图片 / 扫描区域同步脱敏
- 手动画框脱敏

### Word
- 单文档智能脱敏
- 多字段替换规则（`exact / regex`）
- 批量替换（`.docx / .doc`）
- 手动精确 / 全局脱敏
- 左右双栏预览融合显示

### 工程能力
- 统一版本来源：`version.txt`
- 回滚检查点：`backups/iteration_checkpoints/`
- 回滚日志：`rollback_journal.md`
- Windows/macOS 打包方案已同步

---

## 2026-03-18 当前关键收敛

1. `v37.7.4` 运行基线保持稳定，主回归已提升到 `52/52`
2. v38 UI 改造代码层主线已完成：
   - 首页、PDF、Word、批量 Word、图片合并、高级设置已统一到同一套桌面级壳层语言
   - 宽窗口 / 全屏 / 超宽窗口响应式策略已接入主工作区与设置中心
3. Word 双栏对比已补齐滚动联动基础能力
4. 当前默认工作重心已从结构改造切换到真机截图驱动的细节抛光
5. 主文档、当前状态文档与协作文档已同步到 `2026-03-18` 口径

---

## 当前主要风险

1. `main.py` 仍然偏大，后续继续迭代时要避免与 `privacyguard/*` 逻辑漂移
2. Phase 2 的“每文件单独规则映射”尚未实现
3. Windows 真机 `100% / 125% / 150% / 175%` 缩放下仍建议继续做截图驱动细调

---

## 当前建议阅读顺序

1. `docs/current/STATUS.md`
2. `docs/current/DEV_LOG.md`
3. `docs/current/V38_UI_REFACTOR_PLAN.md`
4. `CHANGELOG.md`
5. `rollback_journal.md`
6. `CLAUDE.md`
7. `docs/guides/QUICK_START_FOR_CLAUDE_CODE.md`
8. `docs/diary/20260309_2338_release_sync_diary.md`
9. `docs/diary/20260311_pyinstaller_packaging_fix_diary.md`
