# PrivacyGuard 项目恢复指南

## 概述
本指南用于下次打开项目时，快速恢复到当前开发基线，而不是回到历史版本说明。

---

## 快速恢复

### 1. 进入项目目录

```bash
cd /Users/a49144/Desktop/codexhub/PrivacyGuardApp
```

### 2. 可选：激活虚拟环境

```bash
source venv/bin/activate
```

如果当前机器使用的是 `venvmac` 或 `venv_win`，按实际环境切换。

### 3. 启动应用

```bash
python3 main.py
```

### 4. 验证当前版本

```bash
cat version.txt
```

当前发布基线应为：`37.7.4`

---

## 下次接手优先阅读

1. `docs/current/STATUS.md`
2. `docs/current/DEV_LOG.md`
3. `CHANGELOG.md`
4. `rollback_journal.md`
5. `CLAUDE.md`
6. `docs/guides/QUICK_START_FOR_CLAUDE_CODE.md`
7. `docs/diary/20260309_2338_release_sync_diary.md`
8. `docs/diary/20260311_pyinstaller_packaging_fix_diary.md`

---

## 当前项目结构（最小必要）

```text
PrivacyGuard/
├── main.py
├── theme.py
├── version.txt
├── config.json
├── README.md
├── PROJECT_INDEX.md
├── CLAUDE.md
├── CHANGELOG.md
├── rollback_journal.md
├── restore_checkpoint.sh
├── docs/
│   ├── current/
│   ├── guides/
│   ├── packaging/
│   └── diary/
├── packaging/
│   ├── windows/
│   └── macos/
├── privacyguard/
├── tests/
├── backups/iteration_checkpoints/
└── releases/
```

---

## 当前回滚策略

### 推荐回滚入口

1. 查看 `rollback_journal.md`
2. 选择目标 checkpoint
3. 按 `ROLLBACK_GUIDE.md` 执行
4. 如需脚本恢复，使用 `restore_checkpoint.sh`

### 当前关键 checkpoint

- `20260309_runtime_remediation_cp18_verified`
- `20260309_word_compare_bugfix_cp20_verified`
- `20260309_mixed_pdf_ocr_cp23_verified`
- `20260309_release_sync_cp25_verified`
- `20260310_word_preview_highlight_cp27_verified`
- `20260310_release_sync_cp29_verified`
- `20260311_pyinstaller_packaging_fix_cp30_verified`

---

## 当前标准验证命令

```bash
python3 -m compileall -q main.py privacyguard tests
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

---

## 遇到问题时先确认

1. 当前版本是否是 `v37.7.4`
2. 问题发生在 PDF、Word，还是两者都有
3. 是否涉及首次操作、compare 切换、混合 PDF 图片区域，或 Word 高级设置保存后的预览刷新
4. 是否已经阅读 `docs/current/STATUS.md` 中最近一轮热修复说明

最后更新：2026-03-11
