---
phase: 02-pdf
plan: 04
slug: gap-closure
type: execute
wave: 2
completed_at: 2026-08-11
status: complete
---

# Phase 2 (02-pdf) — Gap Closure Summary

## 修复了什么

Phase 2 `02-VERIFICATION.md` 报告 4 个未关闭的验证失败（CR-01 / WR-01 / WR-03 / WR-04）。本计划 (02-04) 全部关闭。

| ID | 严重度 | 修复内容 |
|---|---|---|
| **CR-01** | critical | main.py::save_pdf 不再内联重写 `write_partial_masks`；改为单一委托调用 |
| **WR-01** | low | engine.py docstring 文档化 PIIEngine eager load 6 个新 validator 的接受理由 |
| **WR-03** | high | test_convergence.py AST-rewrite 检测 def save_pdf 内的 Call 节点；integration test 不再 inline mirror |
| **WR-04** | medium | has_bank_account_context 改为迭代所有 find() 位置；新增 5 个 regression 测试 |

---

## 关键改动

### CR-01 修复:write_partial_masks 接受混合 item 类型 + main.py 单一委托

**`privacyguard/pii/pdf_adapter.py`** — 重构 `write_partial_masks` 签名,接受 4 种混合 item 形态:
- `PIIHit` dataclass → 全局 mode 参数 (02-01 向后兼容路径)
- `fitz.Rect` → 全局 mode 参数
- `(x, y, w, h, mode)` 5-tuple → 每项 mode (OCR / manual / PII blackout)
- `(PIIHit, mode)` 2-tuple → 每项 mode + 从 hit 取 mask_strategy (PII partial)

新增 `PartialMaskItem` 类型别名 + `_resolve_font_for_rect_unified` helper(支持 _FONT_NAME_MAP、OCR 字号 fallback、rect 宽度重算)。

**`main.py`** — save_pdf 循环(原 12639-12715 行,~75 行内联实现)替换为 ~15 行:
```python
all_pi_items = []
for r in ocr_list + manual_list:
    all_pi_items.append((r.x(), r.y(), r.width(), r.height(), 'blackout'))
for hit in pii_list:
    if override == "blackout":
        all_pi_items.append((hit, 'blackout'))
    elif per_entity_default.get(hit.entity_type, "partial") == "partial":
        all_pi_items.append((hit, 'partial'))
    else:
        all_pi_items.append((hit, 'blackout'))
write_partial_masks(doc_save, i, all_pi_items)
```

D-22 不变量保持:每页 `apply_redactions()` 仅调用一次。

### WR-04 修复:has_bank_account_context 迭代所有位置

**`privacyguard/pii/validators/bank_account.py`** — `text.find(target)` (首次出现) 改为 while-loop `text.find(target, start)` (所有位置),任一 occurrence 的 ±window 包含锚点即返回 True。

### WR-03 修复:AST-verify + 真实调用

**`tests/unit/test_convergence.py`** — 旧版只检查 `'write_partial_masks' in source` 字符串存在,新版用 `ast.parse` + `ast.FunctionDef(name='save_pdf')` + `ast.Call(func.id=='write_partial_masks')` 强制要求函数在 save_pdf body 内被实际调用。import 不再算调用,这是 CR-01 漏过收敛门禁的根因。

**`tests/unit/test_pdf_pii_redaction.py`** — `test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata` 不再 inline mirror 重写 add_redact_annot + apply_redactions + insert_text,改为实际调用 `write_partial_masks(doc_save, 0, [(pii_hit, 'partial')])`。

### WR-01 修复:docstring 文档化

**`privacyguard/pii/engine.py`** — 模块 docstring 末尾追加 WR-01 acceptance note:说明 PIIEngine 是 6 个新 validator 的唯一访问路径,有意选择顶层 import 以保持代码简洁;OPS-03 严格契约不受影响 (`import privacyguard` 仍不触发任何 PII 模块加载);独立延迟访问路径经由 `privacyguard.pii.validators.__getattr__` 保留;未来可重构成 `importlib.import_module(...)` 形式。

---

## 文件改动清单

| 文件 | 增 | 减 | 净 |
|---|---|---|---|
| `main.py` | 28 | 56 | -28 |
| `privacyguard/pii/engine.py` | 10 | 0 | +10 |
| `privacyguard/pii/pdf_adapter.py` | 130 | 19 | +111 |
| `privacyguard/pii/validators/bank_account.py` | 14 | 10 | +4 |
| `tests/unit/test_convergence.py` | 41 | 15 | +26 |
| `tests/unit/test_pdf_pii_redaction.py` | 142 | 32 | +110 |
| `tests/unit/test_pii_validators.py` | 41 | 0 | +41 |
| `tests/unit/test_config_alignment.py` | 0 | 2 | -2 |
| `tests/unit/test_pii_engine.py` | 4 | 2 | +2 |
| `version.txt` | 1 | 1 | 0 |
| **总计** | **411** | **137** | **+274** |

注:`test_config_alignment.py` / `test_pii_engine.py` / `version.txt` 的修改不属于本计划范围,系同期用户手动改动(VAT 20 位 fixture 修复 + 版本号 `1.0.0`)。

---

## 测试结果

### 新增测试 (10 个)

```
test_two_occurrences_second_has_context_returns_true ............ ok
test_three_occurrences_only_last_has_context_returns_true ....... ok
test_two_occurrences_either_has_context_returns_true ............ ok
test_two_occurrences_neither_has_context_returns_false .......... ok
test_single_occurrence_no_context_still_returns_false ........... ok
test_pii_hit_branch_signature_still_importable .................. ok
test_tuple_form_partial_mask_item_exported ...................... ok
test_mixed_5tuple_dispatches_correctly .......................... ok
test_mixed_2tuple_partial_writes_mask_text ...................... ok
test_mixed_partial_and_blackout_in_one_call ..................... ok
```

### 回归测试

| 测试集 | 结果 |
|---|---|
| Phase 1 基线 (10 个 unittest 模块) | 全部通过 |
| Phase 2 测试 (`test_pii_*` / `test_pdf_*`) | 全部通过 |
| 272 baseline + 10 新增 = **282 OK** | 全部通过 |

注: `tests/test_path_validation.py` 中 4 个测试因 MSYS/Git-Bash 环境特性失败 (Windows 路径验证行为差异),与本次改动无关,系 pre-existing。

### 关键不变量验证

- **OPS-03 严格契约**: `import privacyguard` → 0 PII 模块加载 ✓
- **D-22 单次 apply**: write_partial_masks 内部循环外一次性调用 ✓
- **v37.7.6 收敛**: main.py 无内联 `def write_partial_masks(` / `def clear_pdf_metadata(` ✓
- **AST gate**: `save_pdf` 函数体内存在 `ast.Call` 到 `write_partial_masks` 和 `clear_pdf_metadata` ✓
- **PyMuPDF font mapping**: `_resolve_font_for_rect_unified` 使用 `_FONT_NAME_MAP` 查找字体 ✓

### Live grep 验证

```bash
$ grep -c "write_partial_masks" main.py    # → 5 (import + call + 3 docstring/comment)
$ grep -c "def write_partial_masks(" main.py  # → 0 (no inline impl)
$ grep -c "page.insert_text" main.py       # → 0 (no inline mask writing)
```

---

## 关键链接验证

- `MainWindow.save_pdf` (main.py:12630+) → `write_partial_masks(doc_save, i, all_pi_items)` (CR-01 fix; 恢复 _FONT_NAME_MAP + OCR 字号 fallback + rect resize)
- `write_partial_masks` (pdf_adapter.py) → 4-branch dispatch → 单次 `add_redact_annot` + `apply_redactions(IMAGE_PIXELS)` (D-22 不变量)
- `test_convergence.test_main_py_uses_write_partial_masks_in_save_loop` → `ast.parse(MAIN_PY)` → `ast.FunctionDef(name=save_pdf)` → `ast.Call(func.id==write_partial_masks)` (WR-03 fix)
- `test_pdf_pii_redaction.test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata` → 实际 `write_partial_masks(doc_save, 0, [(pii_hit, 'partial')])` (WR-03 fix)
- `has_bank_account_context` → while-loop `text.find(target, start)` → `any(ctx in window for ctx in BANK_ACCOUNT_CONTEXTS)` → True (WR-04 fix)

---

## Reversibility 评估

| 改动 | rating | 原因 |
|---|---|---|
| `write_partial_masks` 签名扩展 | costly | 调用方需同步更新,但 02-01 向后兼容路径保留 |
| `has_bank_account_context` body | reversible | 单一函数,逻辑本地化 |
| `main.py::save_pdf` 重构 | costly | 替换 ~75 行 → 单一委托,跨多处 import 路径 |
| `test_convergence.py` AST rewrite | reversible | 仅 test 文件 |
| `test_pdf_pii_redaction.py` 集成测试 | reversible | 仅 test 文件 |
| `engine.py` docstring | reversible | 文档注释 |

---

## Phase 2 状态更新

**修复前 (02-VERIFICATION):** gaps_found, 8/9 must-haves, 4 个未关闭 failures。
**修复后 (本计划):** 全部 4 个 failures 关闭,OPS-03 严格契约保持,272 baseline + 10 新增 = 282 tests OK。

Phase 2 现已满足 ship 标准:
- 9 个 entity types 端到端检测
- partial mask 写入 helper 单一委托 + 4-branch dispatch
- PDF metadata 5 字段清除
- SettingsDialog 9-row per-entity table + toolbar mask_override toggle
- PyInstaller spec parity (Windows + macOS hiddenimports + bin_prefixes.json datas)
- 79 → 88/89 → 272 → 282 测试基线

**Next**: Phase 2 可标记为 `complete`。后续可推进 Phase 3 (Word) 或 Phase 8 (打包验证) 等里程碑。

---

## Commit 信息

```
fix(02-04): close CR-01 + WR-01 + WR-03 + WR-04 from 02-VERIFICATION

- CR-01: write_partial_masks now accepts mixed item types (PIIHit |
  fitz.Rect | tuple); main.py::save_pdf delegates to single
  write_partial_masks call (no inline mirror). Restores
  _FONT_NAME_MAP font mapping, OCR font-size fallback, and rect
  resize.
- WR-01: engine.py module docstring documents that PIIEngine eagerly
  loads all 6 new validators and rationale for accepting this
  (option a).
- WR-03: test_convergence AST-rewrite detects Call node inside def
  save_pdf; test_pdf_pii_redaction integration test rewritten to
  actually call write_partial_masks.
- WR-04: has_bank_account_context iterates all text.find positions;
  TestBankAccountContextMultipleOccurrences covers 5 multi-occurrence
  cases.
```