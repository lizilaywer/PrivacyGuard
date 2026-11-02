# PrivacyGuard 测试指南

> 本文档描述 PrivacyGuard 的测试架构、执行方式与编写规范。
> 当前基线：v37.8.11 ｜ 回归：418 项（416 passed + 2 skipped）

最后更新：2026-08-01

---

## 1. 测试架构

### 1.1 目录结构

```
tests/
├── unit/               # 单元测试（参与 unittest discover，CI 与回归基线来源）
│   ├── test_luhn_validation.py
│   ├── test_seal_detection.py
│   ├── test_signature_detection.py
│   ├── test_mixed_pdf_ocr.py
│   ├── test_pdf_text_hit_dedup.py
│   ├── test_pdf_encrypt.py
│   ├── test_undo_redo.py
│   ├── test_redact_report.py
│   ├── test_session_store.py
│   ├── test_trace_cleaner.py
│   ├── test_logger.py             # v37.8.11 P0-3 统一日志框架
│   ├── test_worker_lifecycle.py   # v37.8.11 P2-3 Worker 线程生命周期
│   └── ...                        # 当前 418 项基线
├── legacy/              # 失效/陈旧测试（不参与 discover，仅保留历史）
├── scripts/             # 辅助测试脚本（不参与 discover）
├── e2e/                 # 端到端辅助脚本（不参与 discover）
└── integration/         # 集成验证脚本（不参与 discover）
```

### 1.2 测试框架

- **框架**：Python 标准库 `unittest`（不使用 pytest）
- **发现机制**：`unittest discover -s tests/unit`，新测试文件自动纳入，清单永不漂移
- **CI 平台**：`windows-latest`（GitHub Actions），`QT_QPA_PLATFORM=offscreen` 离屏运行

### 1.3 当前基线

| 指标 | 数值 |
|------|------|
| 总测试数 | 418 |
| 通过 | 416 |
| 跳过 | 2 |
| 基线版本 | v37.8.11 |

跳过的 2 项为 `test_real_pdf_seals_detected` 与 `test_real_pdf_black_fingerprint_detected`，依赖仓库内真实样本文件；样本缺失时自动 skip，印章/签名端到端语义由合成样本用例在任何机器上兑付。

---

## 2. 执行方式

### 2.1 全量回归（推荐）

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts/run_regression.ps1
```

```bash
# macOS / Linux
./scripts/run_regression.sh
```

脚本内部执行 `unittest discover -s tests/unit -v`，自动发现全部用例。

### 2.2 单模块执行

```powershell
# Windows
.\venv_win\Scripts\python.exe -m unittest tests.unit.test_seal_detection -v
```

```bash
# macOS
./venvmac/bin/python3 -m unittest tests.unit.test_seal_detection -v
```

### 2.3 语法检查

```powershell
.\venv_win\Scripts\python.exe -m compileall -q main.py privacyguard tests
```

### 2.4 静态检查（ruff）

```powershell
.\venv_win\Scripts\python.exe -m ruff check main.py privacyguard tests
```

ruff 配置见 `ruff.toml`（`select = ["E9", "F"]`，`ignore = ["F403", "F405"]`）。

---

## 3. CI 流水线

CI 定义在 `.github/workflows/ci.yml`，触发条件为 push/PR 到 `main` 分支：

| 步骤 | 命令 | 说明 |
|------|------|------|
| 依赖安装 | `pip install -r requirements.txt && pip install ruff` | 运行时依赖 + ruff |
| Ruff lint | `python -m ruff check main.py privacyguard tests` | 静态检查（P2-3 新增） |
| 编译检查 | `python -m compileall -q main.py privacyguard tests` | 语法检查 |
| 回归测试 | `python -m unittest discover -s tests/unit -v` | `QT_QPA_PLATFORM=offscreen` |
| 版本校验 | 版本一致性脚本 | version.txt → version_info.txt → main.py → __init__.py |

提交前请确保本地通过上述全部检查。

---

## 4. 测试编写规范

### 4.1 文件命名与放置

- 单元测试放 `tests/unit/test_<主题>.py`，会被 `discover` 自动纳入
- 文件名用下划线分隔：`test_pdf_encrypt.py`、`test_worker_lifecycle.py`
- 失效/陈旧测试归档到 `tests/legacy/`（不参与 discover）

### 4.2 Qt 依赖处理

需要 PyQt6 的测试用 offscreen 平台 + 模块级 QApplication 单例：

```python
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from PyQt6.QtWidgets import QApplication
    _APP = QApplication.instance() or QApplication([])  # 模块级持有，防 GC
    from privacyguard.workers import OCRWorker
    HAS_DEPS = True
except Exception:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "PyQt6 依赖不可用")
class TestXxx(unittest.TestCase):
    ...
```

### 4.3 资源清理

- 文件句柄、临时资源必须在 `tearDown` 或上下文管理器中关闭，避免 `ResourceWarning`
- 使用 `tempfile.TemporaryDirectory()` 管理临时文件
- Worker 测试中 `deleteLater()` 清理 QThread 对象

### 4.4 Worker 线程测试模式

- **实例化/信号/中断 API**：不需启动线程，直接验证类属性和方法存在性
- **同步 run()**：直接调用 `worker.run()`（不经过 `start()`），在同一线程内执行，无需事件循环
- **跨线程决策**：用 `threading.Thread` + `threading.Event` 测试 `provide_error_decision` 机制
- 参考实现：`tests/unit/test_worker_lifecycle.py`

### 4.5 真实样本测试

- 依赖真实文件（如真实印章 PDF）的测试必须提供合成样本兜底
- 样本缺失时用 `@unittest.skipUnless(os.path.exists(sample), "样本缺失")` 跳过
- 合成样本用例在任何机器上都能验证端到端语义

---

## 5. 测试覆盖范围

### 5.1 已覆盖的核心域

| 域 | 测试文件 | 覆盖内容 |
|----|---------|---------|
| 规则校验 | test_luhn_validation | Luhn 校验位算法 |
| 印章检测 | test_seal_detection | 多特征评分融合检测 |
| 签名手印 | test_signature_detection | 红/黑双路径 + 暖色门控 |
| 混合 PDF | test_mixed_pdf_ocr | 文本层 + 图片块 OCR |
| PDF 去重 | test_pdf_text_hit_dedup | 重复命中不重复追加 |
| PDF 加密 | test_pdf_encrypt | AES-256 加密导出 |
| 撤销重做 | test_undo_redo | 快照栈深度与恢复 |
| 脱敏报告 | test_redact_report | 规则分类 + 逐页详情 |
| 会话恢复 | test_session_store | 崩溃安全草稿 |
| 痕迹清理 | test_trace_cleaner | 白名单 realpath 守卫 |
| 日志框架 | test_logger | init_logging 幂等 + 文件滚动 |
| Worker 生命周期 | test_worker_lifecycle | 5 个 Worker 实例化/信号/中断/决策 |
| Word 规则 | test_word_replace_rules | exact/regex 多字段替换 |
| Word 批量 | test_batch_word_replace | 批量替换 + 冲突处理 |
| 配置 | test_app_config, test_config_alignment | 配置持久化与一致性 |
| 工具栏布局 | test_toolbar_layout | 溢出响应式 |
| 页面视图 | test_page_view_ops | 旋转/插入/删除 |
| 稳定性 | test_stability | 临时文件清理幂等 |
| 包导入 | test_package_imports | 无 OCR 依赖安全导入 |

### 5.2 手工验收清单

自动化测试外的手工验证场景见 `docs/current/PRIORITY_REMEDIATION_PLAN.md` "手工验收清单"节，覆盖：

- 安全与稳定性（非法路径拒绝、缺 OCR 依赖可用）
- PDF（重复姓名不重复遮罩、图片 OCR 不退化）
- Word（规则替换、智能脱敏、手动精确、撤回同步、长文档性能）
- 设置与版本（保存重启生效、版本一致性）

---

## 6. 性能基准

| 文件类型 | 页数 | 预期 OCR 时间 | 预期内存 |
|---------|------|-------------|---------|
| 文字版 PDF | 2 页 | < 2 秒 | ~150 MB |
| 文字版 PDF | 10 页 | < 5 秒 | ~200 MB |
| 扫描版 PDF | 2 页 | < 10 秒 | ~250 MB |
| 扫描版 PDF | 10 页 | < 30 秒 | ~400 MB |

---

## 7. 常见问题

### 如何确认当前版本？

```powershell
Get-Content version.txt
```

### 回归出现失败怎么办？

1. 阅读 `docs/current/STATUS.md` 顶部最新节
2. 检查 `docs/current/PRIORITY_REMEDIATION_PLAN.md` 是否有已知问题
3. 查看最新日志（`%TEMP%/privacyguard_logs/`）
4. 如需回滚，参考 `ROLLBACK_GUIDE.md`

### ruff 报错怎么办？

- `F401`（unused-import）：删除未用导入，或对 re-export 加 `# noqa: F401`
- `F821`（undefined-name）：补全缺失导入——这是真实缺陷，必须修复
- `F841`（unused-variable）：删除变量或改用 `_`
- `F403/F405`（star import）：已全局忽略，新代码不应新增 star import

### 如何添加新测试？

1. 在 `tests/unit/` 下创建 `test_<主题>.py`
2. 继承 `unittest.TestCase`
3. 如需 PyQt6，按 §4.2 处理 offscreen + QApplication
4. 方法名以 `test_` 开头
5. 运行 `scripts/run_regression.ps1` 验证
6. 新文件会被 `discover` 自动纳入，无需修改任何清单
