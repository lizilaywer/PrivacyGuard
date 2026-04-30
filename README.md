# PrivacyGuard 脱敏卫士
我这个比较懒，不会搞github，多多理解，哪天有空了 再好好研究，先传上去
可以关注公众号联系：池州汪律的AI进化论 ，或者抖音搜索：池州有个汪律师

软件预览图如下：
<img width="2422" height="1510" alt="软件截图预览_主页" src="https://github.com/user-attachments/assets/c93df112-8e24-4fb2-b236-3584a82d2e1f" />


b站可以看操作快闪视频了解：【跟上节奏，2分钟快闪带你看完零基础用AI开发出来的软件是什么样】
https://www.bilibili.com/video/BV1NPDYB4EP1?vd_source=53f4c6f7c7329987c843aa17df6c923b

> 基于 Python + PyQt6 的 PDF / Word 文档智能脱敏工具

**当前版本**: v37.7.4
**版本标识**: `37.7.4 - Release Audit and Final Polish`
**最后更新**: 2026-03-18
**当前状态**: 可发布，`v37.7.4` 运行基线稳定；v38 UI 改造代码层已完成，当前默认进入真机截图驱动的细节抛光阶段

[English](README_EN.md) | [License: GPL v3](LICENSE)

---

## 核心功能

- PDF 智能脱敏
  - 文字版 PDF：PyMuPDF 文本搜索
  - 图片版 PDF：RapidOCR
  - 混合型 PDF：文本层 + 嵌入图片 / 扫描区域同步脱敏
- Word 脱敏
  - `.docx` / `.doc`
  - 智能脱敏
  - 手动精确 / 全局脱敏
  - 多字段替换规则（`exact` / `regex`）
  - 批量替换
- 预览能力
  - 左侧原文预览
  - 右侧替换后预览
  - 规则替换 + 手动脱敏 + 智能脱敏融合显示
- 交互能力
  - 拖拽打开
  - 高级设置
  - 批量入口并入“打开/拖拽”

---

## 快速开始

```bash
cd /Users/a49144/Desktop/codexhub/PrivacyGuardApp
python3 main.py
```

### 语法检查

```bash
python3 -m compileall -q main.py privacyguard tests
```

### 主回归测试

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
  -v
```

当前基线：`52/52` 通过。

---

## 当前项目状态

### 已完成

1. Word 多字段替换与批量替换（Phase 1）
2. 批量入口并入“打开/拖拽”
3. 高级设置整合“统一替换文本”与“替换规则入口”
4. 替换后预览融合：规则替换 + 手动脱敏 + 智能脱敏
5. 运行时整改：
   - 路径校验统一
   - `privacyguard` OCR 懒导入
   - 文本型 PDF 去重
   - Word 预览局部 DOM 更新
   - 设置持久化与版本来源统一
6. 热修复：
   - 修复首次智能脱敏后右侧“替换后预览”可能整块空白
   - 修复混合型 PDF 中图片 / 扫描区域漏脱敏
   - 修复“高级设置保存后”原文预览异常红色高亮串位
   - 修复 Windows 打包后 `privacyguard.utils.security` 模块导入失败
7. 当前基线同步：
   - 版本号、文档、日志已统一到 `v37.7.4`
   - `packaging/` 与 `docs/packaging/` 当前说明已同步到当前基线
8. v38 UI 改造代码层收口：
   - 首页、PDF、Word、批量 Word、图片合并、高级设置已统一到同一套桌面级壳层语言
   - 主工作区与设置中心已接入宽窗口 / 全屏 / 超宽窗口响应式策略
   - Word 双栏对比已补齐联动滚动基础能力
   - 当前默认重点已从结构改造切换到真机截图驱动的最后一层观感抛光

### 下一步建议

1. 真机截图驱动的最后一层观感收边
2. 每文件单独规则映射（Phase 2）
3. 批量规则集模板管理
4. 替换后预览按来源筛选高亮

---

## 文档入口

下次继续开发，建议按这个顺序读：

1. `docs/current/STATUS.md`
2. `docs/current/DEV_LOG.md`
3. `docs/current/V38_UI_REFACTOR_PLAN.md`
4. `CHANGELOG.md`
5. `rollback_journal.md`
6. `CLAUDE.md`
7. `docs/guides/QUICK_START_FOR_CLAUDE_CODE.md`
8. `docs/diary/20260309_2338_release_sync_diary.md`
9. `docs/diary/20260311_pyinstaller_packaging_fix_diary.md`

---

## 打包文档

- `docs/packaging/README.md`
- `docs/packaging/windows-packaging-guide.md`
- `docs/packaging/macos-packaging-guide.md`
- `packaging/README.md`

---

## 回滚

当前关键检查点：

- `20260309_runtime_remediation_cp18_verified`
- `20260309_word_compare_bugfix_cp20_verified`
- `20260309_mixed_pdf_ocr_cp23_verified`
- `20260309_release_sync_cp25_verified`
- `20260310_word_preview_highlight_cp27_verified`
- `20260310_release_sync_cp29_verified`
- `20260311_pyinstaller_packaging_fix_cp30_verified`
- `v38_ui_refactor_cp31_20260313_140645`

参考：

- `rollback_journal.md`
- `ROLLBACK_GUIDE.md`
- `restore_checkpoint.sh`

## releases-打包好的便携包，下载可用
https://github.com/lizilaywer/PrivacyGuard/releases/tag/v37.7.4


关注与我这边比较不懂又懒的小律师交流吧！
![关注公众号](./assets/wx_qrcode.png)  

