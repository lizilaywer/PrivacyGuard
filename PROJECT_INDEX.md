# PrivacyGuard 项目文档索引

**当前基线版本**: v37.7.4
**最后更新**: 2026-03-18
**当前状态**: ✅ 可发布（`v37.7.4` 运行基线稳定；v38 UI 改造代码层已完成，当前默认进入真机截图驱动微调）
- **版本标识**: `37.7.4 - Release Audit and Final Polish`
- **当前重点**: v38 UI 改造代码层已收口，默认进入真机截图驱动抛光

---

## 1. 下次继续开发时先读这些

按下面顺序读取即可快速接上当前进度：

1. `docs/current/STATUS.md`
2. `docs/current/DEV_LOG.md`
3. `docs/current/V38_UI_REFACTOR_PLAN.md`
4. `CHANGELOG.md`
5. `rollback_journal.md`
6. `CLAUDE.md`
7. `docs/guides/QUICK_START_FOR_CLAUDE_CODE.md`
8. `docs/current/PRIORITY_REMEDIATION_PLAN.md`
9. `docs/diary/20260309_2338_release_sync_diary.md`
10. `docs/diary/20260311_pyinstaller_packaging_fix_diary.md`

---

## 2. 当前主文档（Single Source of Truth）

### 项目状态与日志

- `docs/current/STATUS.md`
- `docs/current/DEV_LOG.md`
- `CHANGELOG.md`
- `rollback_journal.md`

### 开发协作文档

- `CLAUDE.md`
- `docs/guides/QUICK_START_FOR_CLAUDE_CODE.md`
- `docs/current/PRIORITY_REMEDIATION_PLAN.md`
- `docs/current/RECOVERY_GUIDE.md`
- `docs/current/PROJECT_STRUCTURE.md`
- `docs/current/PROJECT_SUMMARY.md`

### 打包与发布

- `docs/packaging/README.md`
- `docs/packaging/windows-packaging-guide.md`
- `docs/packaging/macos-packaging-guide.md`
- `packaging/README.md`
- `packaging/windows/docs/WINDOWS_BUILD_GUIDE.md`
- `packaging/macos/docs/MACOS_BUILD_GUIDE.md`

### 日记与归档

- `docs/diary/20260309_2338_release_sync_diary.md`
- `docs/diary/20260302_1630_word_replace_fusion_release_diary.md`
- `docs/archive/`

---

## 3. 当前已完成的关键里程碑

1. Word 多字段替换与批量替换（Phase 1）
2. 批量入口并入“打开/拖拽”
3. 高级设置整合“统一替换文本”和“替换规则入口”
4. 右侧替换后预览融合：规则替换 + 手动脱敏 + 智能脱敏
5. 运行时整改：
   - 安全路径校验统一
   - `privacyguard` OCR 懒导入
   - 文本型 PDF 去重
   - Word 预览改为按 `data-key` 局部更新
   - 设置持久化与版本来源统一
6. compare 空白热修复
7. 混合型 PDF OCR 热修复：
   - 文本层命中 + 图片块 OCR 命中
   - 修复嵌入图片 / 扫描区域漏脱敏
8. 发布同步与 packaging 复核：
   - 版本统一到 `v37.7.4`
   - active 文档与打包方案已统一
   - packaging 脚本链、版本资源与说明文档已再次复核
   - 当前主回归基线已统一到 `52/52`
9. PyInstaller 打包修复：
   - 修复 `privacyguard.utils.security` 语法错误导致的模块导入失败
   - 补齐 `privacyguard` 相关 hiddenimports、hook 与 runtime hook
   - 当前 active 文档入口与工作目录路径已同步到 `v37.7.4`
10. v38 UI 改造代码层收口：
   - 首页、PDF、Word、批量 Word、图片合并、高级设置已统一到同一套桌面级壳层语言
   - 宽窗口 / 全屏 / 超宽窗口布局策略已接入主工作区与高级设置
   - 当前代码层主线已完成，默认转入真机截图驱动的细节抛光

---

## 4. 当前关键检查点

- `20260309_runtime_remediation_cp18_verified`
- `20260309_word_compare_bugfix_cp20_verified`
- `20260309_mixed_pdf_ocr_cp23_verified`
- `20260309_release_sync_cp25_verified`
- `20260310_word_preview_highlight_cp27_verified`
- `20260310_release_sync_cp29_verified`
- `20260311_pyinstaller_packaging_fix_cp30_verified` ✅
- `v38_ui_refactor_cp31_20260313_140645`

如需回滚，优先看：

- `rollback_journal.md`
- `ROLLBACK_GUIDE.md`
- `restore_checkpoint.sh`

---

## 5. 当前标准验证命令

```bash
cd /Users/a49144/Desktop/codexhub/PrivacyGuardApp
python3 -m compileall -q main.py privacyguard tests
python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v
python3 main.py
```

当前主回归基线：`52/52` 通过。

---

## 6. 当前下一步建议

如果没有新 bug，当前优先顺序是：

1. 真机截图驱动的 UI 细节抛光
2. 每文件单独规则映射（Phase 2）
3. 批量规则集模板管理
4. 替换后预览按来源筛选高亮

如果是回归问题，优先先看：

1. `docs/current/STATUS.md`
2. `rollback_journal.md`
3. `docs/current/PRIORITY_REMEDIATION_PLAN.md`
