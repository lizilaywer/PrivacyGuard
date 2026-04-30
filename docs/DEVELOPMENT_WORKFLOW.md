# PrivacyGuard 开发工作流

> 本文档描述当前项目的实际开发与发布流程，已统一到 `version.txt` 作为唯一版本源。

---

## 当前基线

- 当前版本：`v37.7.4`
- 版本标识：`37.7.4 - Release Audit and Final Polish`
- 版本唯一来源：项目根目录 `version.txt`
- 当前主运行时入口：`main.py`

---

## 日常开发流程

### 1. 阅读当前状态

按下面顺序阅读：

1. `docs/current/STATUS.md`
2. `docs/current/DEV_LOG.md`
3. `docs/current/V38_UI_REFACTOR_PLAN.md`
4. `CHANGELOG.md`
5. `rollback_journal.md`
6. `CLAUDE.md`
7. `docs/guides/QUICK_START_FOR_CLAUDE_CODE.md`

### 2. 进入项目并运行

```bash
cd /Users/a49144/Desktop/codexhub/PrivacyGuardApp
python3 main.py
```

### 3. 修改前建立 checkpoint

- 在 `backups/iteration_checkpoints/` 下建立新 checkpoint
- 记录 `key_files_manifest.txt`
- 记录 `preflight_meta.json`
- 更新 `rollback_journal.md`

### 4. 修改后做最少验证

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

### 5. 更新文档

每次影响运行路径、版本、打包方案或恢复方式的改动，都要同步更新：

- `README.md`
- `PROJECT_INDEX.md`
- `CLAUDE.md`
- `CHANGELOG.md`
- `docs/current/STATUS.md`
- `docs/current/DEV_LOG.md`
- `docs/current/V38_UI_REFACTOR_PLAN.md`
- `rollback_journal.md`

---

## 版本管理

### 当前规则

- `version.txt` 是唯一版本源
- `main.py` 和 `privacyguard.__version__` 都从 `version.txt` 读取
- Windows 安装器默认版本与 EXE 版本资源要同步
- macOS spec 从 `version.txt` 动态读取版本
- 当前 packaging 文档以：
  - `docs/packaging/README.md`
  - `docs/packaging/windows-packaging-guide.md`
  - `docs/packaging/macos-packaging-guide.md`
  - `packaging/README.md`
  为准

### 更新版本的最少动作

1. 更新 `version.txt`
2. 如版本标识有变化，更新 `main.py` 中的展示字符串
3. 执行：

```bash
python3 packaging/windows/scripts/generate_version_info.py
```

4. 更新 active 文档和 `CHANGELOG.md`

---

## 跨平台开发原则

1. macOS 作为主要开发环境
2. Windows 主要负责打包与发布验证
3. 共享逻辑不要在 `main.py` 和 `privacyguard/*` 两边各写一份
4. 打包方案当前以 `docs/packaging/*` 为主说明

---

## 打包流程

### macOS

```bash
bash packaging/macos/scripts/build_complete.sh
```

### Windows

```cmd
packaging\windows\scripts\build_complete.bat
```

如需安装包：

```cmd
packaging\windows\scripts\3_build_with_setup.bat
```

---

## 常见问题

### 如何确认当前版本？

```bash
cat version.txt
```

### 如果遇到回归 bug，先看什么？

1. `docs/current/STATUS.md`
2. `rollback_journal.md`
3. `docs/current/PRIORITY_REMEDIATION_PLAN.md`

### 如果需要回滚，先做什么？

1. 找到目标 checkpoint
2. 阅读 `ROLLBACK_GUIDE.md`
3. 使用 `restore_checkpoint.sh` 或按 guide 手动恢复

---

## 当前建议

如果没有新 bug，下一轮优先做：

1. 每文件单独规则映射（Phase 2）
2. 批量规则集模板管理
3. 替换后预览按来源筛选高亮

最后更新：2026-03-10 00:42 +08:00
