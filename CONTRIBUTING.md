# 贡献指南 | PrivacyGuard 脱敏卫士

> 欢迎为 PrivacyGuard 贡献代码、文档或问题反馈。本文档说明开发环境、代码规范、提交规范与发布流程。
> 任何编码前，请先阅读 [AGENTS.md](AGENTS.md)（项目开发指南，单一事实来源）。

最后更新：2026-11-02 ｜ 当前基线：v40.2.5 ｜ Windows 回归：741（738 passed + 3 skipped）；详见 [本轮审查](docs/current/REPOSITORY_AUDIT_20261102.md)。

---

## 1. 项目定位

PrivacyGuard 是基于 Python + PyQt6 的 PDF / Word 文档智能脱敏桌面工具，采用 GPL v3 许可证。

- 主运行入口：`main.py`（MainWindow 协调器）
- 共享模块包：`privacyguard/`（utils / ui / workers / ocr）
- 版本唯一来源：`version.txt`

详细架构说明见 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 2. 开发环境准备

### 2.1 克隆与依赖

```powershell
git clone https://github.com/lizilaywer/PrivacyGuard.git
cd PrivacyGuard
python -m venv venv_win
.\venv_win\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2.2 平台约定

| 平台 | 解释器 | 主要用途 |
|------|--------|----------|
| Windows | `.\venv_win\Scripts\python.exe` | 主要开发 + 打包发布 |
| macOS | `./venv_macos_release/bin/python3` | 开发验证 + 打包发布 |

跨平台共享逻辑禁止在 `main.py` 与 `privacyguard/*` 各写一份，必须收敛到 `privacyguard/` 模块。

### 2.3 启动应用

```powershell
# Windows
.\venv_win\Scripts\python.exe main.py
# macOS
./venv_macos_release/bin/python3 main.py
```

---

## 3. 代码架构铁律（必读）

> 完整规则见 [AGENTS.md](AGENTS.md#architecture-rules-for-new-features铁律)。

**核心原则：新功能必须作为独立模块开发，禁止直接往 `main.py` 添加方法。**

判断标准：超过 50 行的非 UI 布局代码，几乎一定不应直接写在 `main.py` 里。

| 新增类型 | 放置位置 | 通信方式 |
|---------|---------|---------|
| 后台 Worker（线程） | `privacyguard/workers/xxx_worker.py` | `pyqtSignal` |
| 弹窗 Dialog | `privacyguard/ui/dialogs/xxx_dialog.py` | 构造参数 / 信号 / 属性 |
| UI 面板 / 功能域 | `privacyguard/ui/panels/xxx_panel.py` | `layout.addWidget()` + 信号 |
| 纯逻辑（算法/规则/转换） | `privacyguard/utils/` 或 `privacyguard/ocr/` | 独立单元测试 |
| Mixin 方法组（深度耦合 MainWindow） | `privacyguard/ui/mixins/xxx_mixin.py` | 类 docstring 写明接口契约 |

`main.py` 仅允许新增：信号接线（`connect`）、菜单/工具栏按钮创建、快捷键绑定、对独立模块的调用编排。

---

## 4. 开发流程

### 4.1 修改前：阅读当前状态

按下面顺序读，只读最新一节，避免回看整段历史：

1. `docs/current/STATUS.md`（顶部最新节）
2. `docs/current/DEV_LOG.md`（最近一条）
3. `docs/current/PRIORITY_REMEDIATION_PLAN.md`（待办与历史记录）
4. [AGENTS.md](AGENTS.md)

### 4.2 修改前：建立 checkpoint

在 `backups/iteration_checkpoints/` 下建立新 checkpoint，记录 `key_files_manifest.txt` 与 `preflight_meta.json`，并更新 `rollback_journal.md`。回滚参考 `ROLLBACK_GUIDE.md`。

### 4.3 修改后：最小验证

```powershell
# 语法检查
.\venv_win\Scripts\python.exe -m compileall -q main.py privacyguard tests

# 全量回归（unittest discover 自动发现 tests/unit，新测试文件自动纳入）
powershell -ExecutionPolicy Bypass -File scripts/run_regression.ps1
```

当前 Windows 基线：`741`（738 passed + 3 skipped）。两项依赖未公开真实样本，另一项在 Windows 跳过符号链接创建；这不代表对应路径已经实机验证。

### 4.4 修改后：更新文档

每次影响运行路径、版本、打包方案或恢复方式的改动，都要同步更新：

- `README.md` ｜ `AGENTS.md`
- `CHANGELOG.md` ｜ `docs/current/STATUS.md` ｜ `docs/current/DEV_LOG.md`
- `rollback_journal.md`（如建了 checkpoint）

---

## 5. 测试规范

### 5.1 测试组织

- 单元测试：`tests/unit/`（参与 `unittest discover`，是 CI 与回归基线的来源）
- 失效/陈旧测试：`tests/legacy/`（不参与 discover，仅保留历史）
- 测试脚本：`scripts/run_regression.ps1`（Windows）｜ `scripts/run_regression.sh`（macOS/Linux）

### 5.2 新增测试要求

- 新功能或 bug 修复必须配套单元测试，放入 `tests/unit/test_xxx.py`
- 测试文件命名 `test_<主题>.py`，会被 `discover -s tests/unit` 自动纳入
- 涉及真实样本（如真实印章/签名 PDF）的测试必须提供合成样本兜底，保证干净检出机器上不 skip 即可验证语义
- 文件句柄、临时资源必须在 teardown 关闭，避免 `ResourceWarning`

### 5.3 CI 流水线

CI 定义在 `.github/workflows/ci.yml`，运行于 `windows-latest`，包含：

1. 依赖安装
2. `compileall` 语法检查
3. `unittest discover -s tests/unit`（`QT_QPA_PLATFORM=offscreen`）
4. 版本一致性校验（`version.txt` → `version_info.txt` → `main.py` → `privacyguard/__init__.py`）

提交前请确保本地通过上述检查。

---

## 6. 提交规范

### 6.1 提交信息格式

遵循 Conventional Commits 风格（参考最近提交）：

```
<type>(<scope>): <简短描述>

<可选正文，说明 why 与主要变更>
```

常用 `type`：

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | bug 修复 |
| `refactor` | 重构（不改外部行为） |
| `docs` | 文档变更 |
| `test` | 测试新增/修改 |
| `chore` | 构建/工具/配置 |
| `perf` | 性能优化 |

`scope` 示例：`P0-3` / `P1-2` / `readme` / `index` / `settings` / `ocr` 等，对应任务标识或模块名。

### 6.2 示例

```
feat(P0-3): introduce unified logging framework (cp95)
refactor(P1-2): extract seal/signature detection from ocr_worker to ocr/ modules (cp96)
docs(P2-1): sync PRIORITY_REMEDIATION_PLAN status markers
fix: settings nav highlight not updating on scroll to bottom (OCR section)
```

### 6.3 提交安全规则

- 不要提交 `config.json`（运行时本地配置，已 git-ignore）
- 不要提交 `.env`、凭证文件、大型二进制
- 不要使用 `git add -A` / `git add .`，按文件名添加
- 不要 `--no-verify` 跳过钩子，除非用户明确要求
- 不要 amend 已推送的提交，新建提交

---

## 7. 版本管理

### 7.1 单一版本源

`version.txt` 是唯一版本源。`main.py` 和 `privacyguard.__version__` 均从该文件动态读取，禁止硬编码版本号。

### 7.2 升级版本的最少动作

1. 修改 `version.txt`
2. 运行 `python packaging/windows/scripts/generate_version_info.py` 重新生成 `version_info.txt`（**禁止手动编辑** `version_info.txt`，它会被脚本覆盖）
3. 手动更新 `README.md` 与 `packaging/*/scripts/README.txt` 中的版本号
4. 更新 `CHANGELOG.md`
5. CI 会校验四处版本一致性，任一不一致将导致 CI 失败

---

## 8. Pull Request 流程

1. 从 `main` 拉取最新代码，创建特性分支：`feat/<简述>` / `fix/<简述>`
2. 完成开发并通过本地回归（`scripts/run_regression.ps1`）
3. 确认文档已同步（见 §4.4）
4. 提交清晰规范的 commit message（见 §6）
5. 推送分支并创建 PR，标题与描述遵循模板：

   ```markdown
   ## Summary
   - <1-3 条要点>

   ## Test plan
   - [ ] 本地 compileall 通过
   - [ ] 本地 run_regression 基线对齐（418）
   - [ ] 相关功能手工验证
   ```

6. 等待 CI 通过，回应 review 意见

---

## 9. 问题反馈与联系

- Bug / 功能建议：通过 GitHub Issues 提交，附版本号、复现步骤、错误日志
- 抖音 / 小红书 / 微信公众号：池州有个汪律师

提交 Issue 时请附：

1. PrivacyGuard 版本号（`version.txt` 内容）
2. 操作系统与 Python 版本
3. 复现步骤与预期/实际行为
4. 错误日志（`%TEMP%/privacyguard_logs/` 下的最新日志，见 `privacyguard/utils/logger.py`）

---

## 10. 行为准则

本项目遵循 GPL v3 开源精神，欢迎善意、建设性的交流。对反馈保持耐心，对代码保持严谨。
