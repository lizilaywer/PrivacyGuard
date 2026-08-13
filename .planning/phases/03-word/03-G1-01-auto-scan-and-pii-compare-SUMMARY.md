---
phase: 03-word
plan: G1-01
subsystem: word-pii-gap-closure
tags: [auto-scan, pii-compare-mode, pii-full-reload, verification-gaps]
requires:
  - phase: 03-word
    provides: word_adapter 三函数、worker PII 命中、Plan 03 增量路径 pii_matches 注入
provides:
  - 打开 .docx 后自动启动 WordWorker PII 扫描 (VERIFICATION Gap 1 fix)
  - _has_word_replacement_candidates 纳入 PII 命中 (VERIFICATION Gap 2 fix)
  - _build_word_replaced_preview_html 全量重载路径注入 pii_matches (VERIFICATION Gap 3 fix)
  - 3 个新 TestClass 覆盖 G1 全部 gap closure 行为
affects: [phase-03-word, phase-07-review-ux]
gap_closure: true
status: complete
actuals:
  tokens: 4140
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: ["最小表层 main.py 改动，不引入新模块", "AST 守护 + SimpleNamespace stub 双重验证修改正确性", "hasattr + try/except 防御式包裹 start_ocr() 调用，避免阻塞 UI"]
key-files:
  created: []
  modified:
    - main.py
    - tests/unit/test_word_pii_redaction.py
key-decisions:
  - "Gap 1 用 hasattr + try/except 防御 start_ocr() 调用，失败降级为手动扫描 + logging.warning，不弹错误对话框"
  - "Gap 2 在 data.get('manual') or data.get('ocr') 之后追加 or data.get('pii')，与既有 manual/ocr 命中同形态"
  - "Gap 3 镜像 Plan 03 line 12024 的增量 DOM patch 路径写法，保持全量重载与增量 patch 行为一致"
  - "AST 守护必须接受 ast.Attribute 调用 (self.start_ocr)，不能只匹配 ast.Name"
  - "测试 stub 使用 SimpleNamespace + MethodType 绑定，与既有 test_word_replace_rules.build_word_preview_stub 范式一致"
metrics:
  duration: "~15 min (3 tasks executed sequentially with TDD-style test additions)"
  completed: "2026-08-11"
---

# Phase 3 G1-01: Auto-Scan + PII Compare Mode + PII Full Reload Summary

**One-liner:** 闭合 VERIFICATION.md Gap 1/2/3 — 打开 .docx 自动启动 WordWorker + 仅 PII 文档进入对比模式 + 全量重载右栏 HTML 注入 pii_matches

## Tasks Executed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Gap 1: `_open_word_docx` 自动启动 WordWorker PII 扫描 | `4471968` | main.py (+16 行) |
| 2 | Gap 2: `_has_word_replacement_candidates` 纳入 PII | `9e152bd` | main.py (+3 / -2 行) |
| 3 | Gap 3: `_build_word_replaced_preview_html` 注入 pii_matches + 测试 | `ef4b1f1` | main.py (+4 / -1 行) + tests/unit/test_word_pii_redaction.py (+302 行) |

## What Was Built

### Gap 1 — 自动启动 WordWorker (main.py:10856-10870)

在 `_open_word_docx` 的 word_data 初始化完成之后、清理收尾之前，插入 try/except 包裹的 `self.start_ocr()` 调用：

```python
# Phase 3 (G1 Gap 1): 打开 .docx 后自动启动 WordWorker PII 扫描
try:
    if hasattr(self, "start_ocr"):
        self.start_ocr()
except Exception as _gap1_exc:
    try:
        import logging
        logging.getLogger(__name__).warning(
            "auto PII scan on _open_word_docx failed: %s", _gap1_exc
        )
    except Exception:
        pass
```

- 复用 Phase 1 既有 `start_ocr()` 路径，该路径已正确启动 OCRWorker + WordWorker
- `hasattr` 防御：headless 测试场景下 `start_ocr` 未定义时跳过
- `try/except` 防御：自动扫描异常不阻塞 UI 打开（降级为手动点击）
- `start_ocr()` 既有函数体（line 11389）保持不变（Phase 1 不变量）

### Gap 2 — `_has_word_replacement_candidates` 纳入 PII (main.py:10305-10315)

单行扩展：在 `data.get("manual") or data.get("ocr")` 之后追加 `or data.get("pii")`，docstring 同步更新：

```python
def _has_word_replacement_candidates(self):
    """是否存在可在右侧预览中展示的替换结果（规则/OCR/手动/PII）。"""
    if self._has_enabled_word_replace_rules():
        return True
    for data in self.word_data.values():
        if not isinstance(data, dict):
            continue
        # [NEW G1 Gap 2] PII 命中也作为对比模式触发条件
        if data.get("manual") or data.get("ocr") or data.get("pii"):
            return True
    return False
```

- `_has_enabled_word_replace_rules()` 早返回路径保持不变
- `isinstance(data, dict)` 防御保持不变

### Gap 3 — `_build_word_replaced_preview_html` 注入 pii_matches (main.py:10412-10420)

在 `merge_word_matches_with_priority` 调用的 `ocr_matches` 形参之后追加 `pii_matches` 形参，镜像 Plan 03 Task 2 line 12024 的写法：

```python
merged_matches = merge_word_matches_with_priority(
    source_text,
    self.word_replace_rules,
    self.replacement_text,
    manual_matches=self.word_data[key].get("manual", []),
    ocr_matches=self.word_data[key].get("ocr", []),
    # [NEW G1 Gap 3] 全量重载路径同样注入 PII 命中
    pii_matches=self.word_data[key].get("pii", []),
)
```

至此，3 处 `merge_word_matches_with_priority` 调用点（`_build_word_original_panel_updates` / `_build_word_replaced_panel_updates` / `_build_word_replaced_preview_html`）都已注入 `pii_matches` 形参。

## Tests Added (12 个新测试方法)

3 个新 TestClass 写入 `tests/unit/test_word_pii_redaction.py`：

### `TestAutoPiiScanOnOpen` (4 测试)
- `test_open_docx_function_exists` — AST 守护 `_open_word_docx` 存在
- `test_open_docx_calls_start_ocr` — AST 守护 Gap 1 fix（接受 `ast.Attribute` 调用）
- `test_start_ocr_call_is_guarded` — 验证 `start_ocr()` 包在 `try/except` 内
- `test_start_ocr_unchanged` — Phase 1 不变量（start_ocr 函数体未被改，含 OCRWorker/WordWorker 引用）

### `TestPiiOnlyDocumentEntersCompareMode` (4 测试)
- `test_function_exists` + `test_function_body_checks_pii_key` — AST 守护 Gap 2 fix
- `test_docstring_mentions_pii` — docstring 已包含 "PII" 字样
- `test_pii_only_returns_true_via_stub` — 运行时验证 PII-only → True
- `test_empty_returns_false_via_stub` — 反向断言
- `test_manual_still_returns_true` — 回归保护

### `TestPiiFullReloadPreviewContainsMask` (2 测试)
- `test_pii_full_reload_includes_pii_mask_in_replaced_html` — 验证 mask 出现且原文不出现
- `test_pii_full_reload_with_ocr_collision_pii_wins` — D-02 PII > OCR

## Verification Results

| Suite | Tests | Result |
|-------|-------|--------|
| `tests.unit.test_word_pii_redaction` (G1 范围, 含 8 既有 + 12 新) | 20 | PASS |
| Phase 3 范围 (test_word_preview_highlight / test_word_pii_adapter / test_word_worker_pii / test_word_replace_rules / test_batch_word_replace / test_convergence / test_package_imports / test_word_pii_redaction) | 120 | PASS |
| 完整单元测试 (`discover -s tests/unit`) | 348 | PASS |
| `compileall -q main.py privacyguard tests` | — | OK |

**Baseline invariant (D-16 + D-17):** 336 → 348 测试全部通过 (含 12 个新增 G1 测试方法)

## Deviations from Plan

**None - plan executed exactly as written.**

技术细节微调：
- 测试 AST 守护原本计划只匹配 `ast.Name`，但 `self.start_ocr()` 是 `ast.Attribute` 调用 — 调整为同时接受两种节点类型以匹配真实代码形态
- `_make_word_pii_hit` 沿用 `test_word_preview_highlight._make_pii_hit` 的 PIIHit 构造模式（page_offset/page_length 复用 D-10 存 char_offset/char_length）

## Acceptance Criteria

- [x] main.py:_open_word_docx 自动调用 self.start_ocr() — `grep -n 'self.start_ocr()' main.py` 命中 line 10864，位于 10797-10875 区间
- [x] start_ocr() 调用被 try/except 包裹 — `grep -n 'auto PII scan on _open_word_docx failed' main.py` 命中 line 10870
- [x] start_ocr() 既有函数体未被修改 — `def start_ocr` 仍在 line 11389，函数体含 OCRWorker/WordWorker 引用
- [x] main.py:_has_word_replacement_candidates 包含 data.get('pii') 检查 — line 10313 命中
- [x] docstring 已更新包含 "PII" 字样 — line 10306 docstring 含 "规则/OCR/手动/PII"
- [x] main.py:_build_word_replaced_preview_html 注入 pii_matches 形参 — line 10419 命中，与 ocr_matches 形参 (line 10417) 行号差 = 2
- [x] tests/unit/test_word_pii_redaction.py 末尾追加 3 个 TestClass — `grep -n 'class TestAuto\|class TestPiiOnly\|class TestPiiFullReload'` 命中 3 行
- [x] 348 测试基线全部通过 (D-16 + D-17 不变量)
- [x] merge_word_matches_with_priority 在 3 处调用点都已注入 pii_matches

## Self-Check

- [x] Files exist: main.py, tests/unit/test_word_pii_redaction.py
- [x] Commits exist: 4471968, 9e152bd, ef4b1f1 (verified via `git log --oneline`)
- [x] Test execution: 348/348 PASS
- [x] No new errors in `compileall` check
