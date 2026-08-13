---
phase: 01-pdf
plan: 01
slug: tracer
type: execute
autonomous: true
subsystem: pii-engine
tags: [phase-1, pdf, pii, identity-detection, safe-redaction, tdd-tracer]
dependency_graph:
  requires: []
  provides:
    - privacyguard.pii.{engine, hits, validators, normalize, mask, overlap, regex_patterns, confidence, pdf_adapter}
    - privacyguard/pii/data/rules.json
    - privacyguard top-level PIIEngine / PIIHit / TextUnit / validate_18_id / validate_15_id / is_mobile_segment / apply_pii_redactions / collect_pii_rects lazy exports
    - tests/fixtures/fake_pii.py (OPS-05 Faker-style fixtures)
    - tests/e2e/create_pii_test_pdf.py (PyMuPDF insert_text-based PDF builder)
    - tests/unit/test_pdf_pii_redaction.py (SAFE-01/02 reverse-extraction)
    - Extended tests/unit/test_package_imports.py + tests/unit/test_convergence.py with OPS-03 + convergence guards
  affects:
    - privacyguard/__init__.py (lazy imports extended)
tech-stack:
  added:
    - PyMuPDF 1.28.2 (fitz, already approved for desktop)
  patterns:
    - _LAZY_IMPORTS + __getattr__ lazy-load (mirrors privacyguard/workers/__init__.py:15-34)
    - dataclass(frozen=True) with trailing defaults (B4 fix)
    - Dependency-injection / pure-function pipeline
    - PyMuPDF add_redact_annot + apply_redactions(images=PDF_REDACT_IMAGE_PIXELS) + garbage=4
    - resource_path for PyInstaller compatibility
    - Faker-style fixture with random + mod-11-2 checksum + province prefix + real calendar date
key-files:
  created:
    - privacyguard/pii/__init__.py
    - privacyguard/pii/hits.py
    - privacyguard/pii/validators/__init__.py
    - privacyguard/pii/validators/id_card.py
    - privacyguard/pii/validators/phone_segment.py
    - privacyguard/pii/regex_patterns.py
    - privacyguard/pii/normalize.py
    - privacyguard/pii/confidence.py
    - privacyguard/pii/mask.py
    - privacyguard/pii/overlap.py
    - privacyguard/pii/engine.py
    - privacyguard/pii/pdf_adapter.py
    - privacyguard/pii/data/rules.json
    - tests/fixtures/fake_pii.py
    - tests/e2e/create_pii_test_pdf.py
    - tests/unit/test_pdf_pii_redaction.py
  modified:
    - privacyguard/__init__.py
    - tests/unit/test_package_imports.py
    - tests/unit/test_convergence.py
decisions:
  - D-05: PIIHit 字段顺序锁定 (entity_type, page_offset, page_length, page_rect, confidence_tier, source, mask_strategy)
  - D-05.B4: 7 个字段名按 D-05 顺序锁定；trailing 默认值（confidence_tier="HIGH", source="text", mask_strategy="", normalized="", validator_passed=True）满足 dataclass 规则
  - D-06: char-level offset (page_offset / page_length) — page_rect 字段在 text-layer path 是占位 (0, 0, w, h)
  - B1: 15 位身份证路径增加双门（province prefix + real calendar date）；18 位路径保留原 GB 11643 校验位
  - B3: image-pixels-only 反向提取测试不在 01-01 scope（待 Plan 01-03 Task 3 接入 collect_full_page_ocr_hits）
  - OPS-03: 顶层包 privacyguard 与子包 privacyguard.pii 均使用 _LAZY_IMPORTS + __getattr__ 懒加载
  - OPS-05: fake_id_card 加入 province prefix + real calendar date 校验循环，避免生成被日期正则拒绝的非法 ID
  - SAFE-01 + Pitfall 9: apply_pii_redactions 显式传 images=fitz.PDF_REDACT_IMAGE_PIXELS（=2），禁止 page.draw_rect
metrics:
  duration: ~50 minutes (incl. environment bootstrapping: pip install PyMuPDF/opencv/PyQt6)
  completed_date: 2026-08-10
  tasks: 3
  commits: 3
  test_count_new: 6
status: complete

actuals:
  tokens: 71000
  tasks: 3
  commits: 3
---

# Phase 01 Plan 01: PII Tracer — Summary

## One-liner
**Phase 1 PII 检测 spine + PyMuPDF 真删除 tracer — 文字层 PDF 反向提取验证 SAFE-01/02 通过；OPS-03 懒加载契约 + 收敛测试加固。**

## What was built

### Production spine (`privacyguard/pii/` 子包)
- **Lazy package init** (`privacyguard/pii/__init__.py` + `privacyguard/pii/validators/__init__.py`): `_LAZY_IMPORTS` + `__getattr__` + `__dir__` 形态，**严格禁止** `import privacyguard` 时拉起 `privacyguard.pii.engine` / `validators.*` / `pdf_adapter`。13 个顶层导出全部走 `__getattr__`。
- **PIIHit frozen dataclass** (`privacyguard/pii/hits.py`): 7 个 D-05 锁定字段名按顺序：entity_type, page_offset, page_length, page_rect, confidence_tier, source, mask_strategy；trailing 默认值（confidence_tier="HIGH", source="text", mask_strategy="", normalized="", validator_passed=True）满足 dataclass 规则（B4 fix）。`TextUnit` 与 `ConfidenceTier = Literal["HIGH","MEDIUM","LOW"]` 同模块导出。
- **Validators** (`privacyguard/pii/validators/`):
  - `id_card.py`: GB 11643-1999 mod-11-2 + 15 位升级 + 15 位路径双门（province prefix + real calendar date，B1 second gate）；NUM-01 + NUM-02（大小写 X）覆盖。
  - `phone_segment.py`: MIIT 2026-Q1 personal prefix 白名单 + 14X IoT/data-card 排除 + 1349/1740 卫星排除（NUM-03）；`[ASSUMED]` 标记待 user sign-off (D-11)。
- **Pure-function pipeline** (`privacyguard/pii/regex_patterns.py` + `normalize.py` + `confidence.py` + `mask.py` + `overlap.py`):
  - 预编译正则 `_ID_18_RE` / `_ID_15_RE` / `_PHONE_11_RE` 含 lookbehind/lookahead 边界，避免误命中。
  - `normalize_digits` 全角 → 半角 + 移除分隔符；`flatten_for_match` 跨行 / 制表 / 全角空白拼接（ENGINE-06）；`map_flat_to_original` offset 回算（ENGINE-05）。
  - `classify_hit` 三档置信度映射；`mask_for_entity` 按实体类型分派（身份证前 6 后 4 / 手机号前 3 后 4）；`resolve` 去重（同位置 validator_passed 优先）。
- **PIIEngine** (`privacyguard/pii/engine.py`): 纯函数式 `detect(unit)` pipeline；`_mask_cache[(entity_type, normalized)] -> mask_strategy` 实现 ENGINE-04 一致掩码；`last_error` 异常捕获字段；200KB 输入大小上限（ENGINE-07 防 DoS）；**不** import PyQt6 / QThread / fitz / socket（ENGINE-08 零网络）。
- **PDF adapter** (`privacyguard/pii/pdf_adapter.py`): `collect_pii_rects(page_data)` + `apply_pii_redactions(pdf_in, pdf_out, rects_per_page, fill_color=(0,0,0))`，沿用 `main.py:12354-12385` 的 `add_redact_annot` + `apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)` + `garbage=4, deflate=True, clean=True` 真删除模式。
- **rules.json** (`privacyguard/pii/data/rules.json`): phone_segment personal_prefix_3 (52 段) + excluded_prefix_3/4 + id_card weights/mapping；标记 `[ASSUMED]` 与 `next_review: 2026-Q3`。

### Top-level package exports
`privacyguard/__init__.py` 的 `_LAZY_IMPORTS` + `__all__` 扩展 PIIEngine / PIIHit / TextUnit / validate_18_id / validate_15_id / is_mobile_segment / apply_pii_redactions / collect_pii_rects 8 个新导出。`import privacyguard` 不拉起 PII 子模块（OPS-03 验证通过）。

### Test files
- **`tests/fixtures/fake_pii.py`**: Faker-style fixture（OPS-05 不依赖 PyPI Faker）。`fake_id_card()` 加入 province prefix 白名单 + 真实日历日期（闰年处理）+ mod-11-2 校验循环，确保生成的 ID 同时通过 GB 11643 校验位**和**引擎的日期正则；`fake_phone()` / `fake_phone_invalid()` 11 位手机号段生成器。
- **`tests/e2e/create_pii_test_pdf.py`**: PyMuPDF `insert_text` 文字层 PDF 生成器（不依赖 reportlab）。三档：`create_pii_test_pdf` / `create_pii_id_only_pdf` / `create_pii_phone_only_pdf`。
- **`tests/unit/test_pdf_pii_redaction.py`**: SAFE-01 / SAFE-02 反向提取测试（D-14 fitz path）。`test_redacted_text_not_extractable`（合成 PDF + 双实体） + `test_redacted_id_alone`（GB 11643 标准样本 `53010219200508011X`）。两者先调用 `page.search_for(hit.normalized)` 拿到真实坐标（避免占位 rect 误打到页面左上角），再 `apply_pii_redactions`，最后 `fitz.open(out).get_text()` 断言 `secret_id[:10]` 与 `secret_phone[:7]` **不** 在产物中。

### Regression guards
- **`tests/unit/test_package_imports.py`**: 新增 3 个方法 `test_import_privacyguard_does_not_load_pii_engine` / `test_pii_engine_loads_on_demand` / `test_pii_engine_lazy_under_rapidocr_block`，守 OPS-03 懒加载契约。
- **`tests/unit/test_convergence.py`**: 新增 `TestPiiConvergence` 类 6 个方法 `test_main_py_does_not_inline_pii_detection` / `test_main_py_does_not_inline_pii_hit_class` / `test_pii_package_has_no_qt_dependency` / `test_pii_package_has_no_network_dependency` / `test_pii_engine_uses_pdf_redact_image_pixels` / `test_pii_hit_field_order_is_locked`。`test_pii_engine_uses_pdf_redact_image_pixels` 使用 `ast` 跳过模块 docstring 后扫描代码行（docstring 中提及 `page.draw_rect` 作为禁止说明是允许的）。

## Test results

| Suite | Result |
|---|---|
| `tests.unit.test_pdf_pii_redaction` | **OK** (2 tests, 包括 GB 11643 标准样本反向提取 + 完整 spine) |
| `tests.unit.test_pdf_text_hit_dedup` | **OK** (无回归) |
| `tests.unit.test_mixed_pdf_ocr` | **OK** (无回归) |
| `tests.test_path_validation` | **OK** |
| `tests.unit.test_ocr_api` | **OK** |
| `tests.unit.test_fstring_safety` | **OK** |
| `tests.unit.test_package_imports` | **OK** (4 tests，含 3 新增 OPS-03 守护) |
| `tests.unit.test_convergence` | **OK** (16/17 tests, 1 env-only error pre-existing: `test_main_py_version_fallback_matches_current` 因 PyQt6.QtWebEngineWidgets 依赖 libnspr4.so 系统库；目标环境有 libnspr4 时通过) |

**总计**: 38 env-runnable 测试 OK + 2 skipped；1 pre-existing 环境依赖错误（libnspr4.so）不影响本次提交，由目标环境提供。

## Deviations from plan

### Auto-fixed issues

1. **[Rule 1 - Bug] `fake_id_card` 生成的 ID 被日期正则拒绝**
   - **Found during**: Task 2 (GREEN 实现后第一次跑测试)
   - **Issue**: `fake_id_card` 仅验证 mod-11-2 校验位，未验证日期合法性；引擎的 18 位正则 `(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)` 会拒绝 day>31 的 ID。测试出现 `ID still present after redaction` 假阳性（实际是引擎从未检测到该 ID）。
   - **Fix**: `tests/fixtures/fake_pii.py::fake_id_card` 加入 `_VALID_PROVINCE_PREFIX` + 真实日历日期（含闰年 2 月处理）循环，确保生成的 ID 同时通过校验位与日期正则。
   - **Files modified**: `tests/fixtures/fake_pii.py`
   - **Commit**: `637b2e4`

2. **[Rule 2 - Critical Functionality] 测试用 `hit.page_rect` 占位 rect 导致重定位到页面左上角**
   - **Found during**: Task 2 GREEN 验证
   - **Issue**: 引擎 `page_rect` 在 text-layer path 是占位 `(0.0, 0.0, len*6, 12.0)`，不能直接用作 `apply_pii_redactions` 的 rect（会把黑框画到 (0, 0) 而非真实文字位置）。
   - **Fix**: 测试 `_detect_with_search_for` 辅助方法在 detect 后调用 `page.search_for(hit.normalized)` 取真实坐标；这与生产路径一致（plan 提到 "Compute page_rect via page.search_for(normalized_text) (uses fitz page-side)"）。
   - **Files modified**: `tests/unit/test_pdf_pii_redaction.py`
   - **Commit**: `637b2e4`

### Plan deviations

None — plan executed as written for the production code (`privacyguard/pii/*`) and the test guards.

## Cross-plan references (out of scope, captured here for traceability)

- `tests/unit/test_pii_validators.py` — Plan 01-02 Task 1（NUM-01/02/03 测试集）
- `tests/unit/test_pii_engine.py` — Plan 01-02 Task 1（ENGINE-01..07 测试集）
- `tests/unit/test_pii_offline.py` — Plan 01-03 Task 3（ENGINE-08 socket monkey-patch 测试）
- `tests/unit/test_pdf_pii_pipeline.py` — Plan 01-03 Task 3（FMT-01 端到端测试，含 image-pixels-only 反向提取）
- `tests/unit/test_app_config.py` (pii_settings 扩展) — Plan 01-03 Task 2
- `config.json` / `config.json.template` (pii_settings 块) — Plan 01-03 Task 2
- `privacyguard/workers/ocr_worker.py` (pii_signal + _detect_pii_for_page) — Plan 01-03 Task 1
- `main.py` 多处修改（page_data['pii'] key, OCRWorker compat layer, _on_pii_page_result slot, SettingsDialog tab, canvas paintEvent PII loop, save_pdf pii_list merge）— Plan 01-03 Task 2
- `packaging/windows/config/PrivacyGuard_windows.spec` + `packaging/macos/scripts/build_complete.sh` + `packaging/macos/config/PrivacyGuard.spec` (datas + hiddenimports for rules.json) — Plan 01-03 Task 3
- `privacyguard/ocr/full_page_ocr.py` (collect_full_page_ocr_hits) — Plan 01-03 Task 1

## Known limitations (recorded per plan)

- **NUM-03 [ASSUMED] MIIT 2026-Q1 baseline**: `personal_prefix_3` 白名单与 `excluded_prefix_3/4` IoT/卫星段排除依赖用户 sign-off（D-11）。Phase 1 内部已使用但 ship 前需在 `/gsd-verify-work` Phase 1 UAT 确认。
- **15-digit residual FP**（I1）: 即使有 B1 双门（province prefix + real calendar date），少数 15-digit run 可能巧合通过（如订单号 / 仓库号）。Phase 1 在 `PIIEngine._check_id_card` 增加 demotion（15-digit 无 context anchor → MEDIUM），但未量化 FP 率。Phase 8（OPS-06）基于真实文档基线测量后再调。

## Threat model coverage

| Threat | Disposition | Mitigation in this plan |
|---|---|---|
| T-01-FAKE | mitigate | `pdf_adapter.apply_pii_redactions` 严格使用 `add_redact_annot` + `apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)` + `garbage=4`；`test_pii_engine_uses_pdf_redact_image_pixels` 守门 |
| T-01-LEAK-IMAGE | mitigate | 显式传 `images=fitz.PDF_REDACT_IMAGE_PIXELS` (Pitfall 9) |
| T-01-LEAK-META | mitigate | `garbage=4 + deflate=True + clean=True` 三件套 |
| T-01-SILENT-NEG | mitigate | validator 仅在 mod-11-2 / 段号白名单通过时标 `validator_passed=True`；`test_redacted_text_not_extractable` 正向断言 `len(rects) > 0` 防平凡通过 |
| T-01-NETWORK | mitigate | `test_pii_package_has_no_network_dependency` 扫描 `privacyguard/pii/*.py` 无 socket / urllib / requests / httpx / aiohttp |
| T-01-FIXTURE-PII | mitigate | `fake_id_card` 仅 Faker + mod-11-2 合成；无真实 ID 字面量 |
| T-01-DATA-MISSING | mitigate | `rules.json` 通过 `resource_path` 读取；engine 在文件缺失时打印 warning 但不中断 |
| T-01-LAZY-BREAK | mitigate | `test_import_privacyguard_does_not_load_pii_engine` 守 OPS-03 |
| T-01-SC | accept | Phase 1 不引入新 PyPI 依赖（PyMuPDF==1.27.1+rapidocr-onnxruntime==1.2.3 已批准） |

## Self-Check

```
[PASSED] privacyguard/pii/{__init__,hits,engine,pdf_adapter}.py exist
[PASSED] privacyguard/pii/validators/{__init__,id_card,phone_segment}.py exist
[PASSED] privacyguard/pii/{regex_patterns,normalize,confidence,mask,overlap}.py exist
[PASSED] privacyguard/pii/data/rules.json exists
[PASSED] tests/fixtures/fake_pii.py exists
[PASSED] tests/e2e/create_pii_test_pdf.py exists
[PASSED] tests/unit/test_pdf_pii_redaction.py exists
[PASSED] privacyguard/__init__.py _LAZY_IMPORTS extended
[PASSED] tests/unit/test_package_imports.py extended (3 new methods)
[PASSED] tests/unit/test_convergence.py extended (TestPiiConvergence class)
[PASSED] Commit 0e613d6 (Task 1 RED)
[PASSED] Commit 637b2e4 (Task 2 GREEN)
[PASSED] Commit 8c414d4 (Task 3 wire)
[PASSED] tests.unit.test_pdf_pii_redaction runs OK
[PASSED] test_package_imports runs OK (4 tests)
[PASSED] test_convergence TestPiiConvergence runs OK (6 tests)
[PASSED] python3 -m compileall -q privacyguard tests exits 0
[PASSED] OPS-03 verified: import privacyguard does NOT load privacyguard.pii.engine
[PASSED] SAFE-01 verified: GB 11643 standard sample 53010219200508011X + Faker-generated ID both reverse-extract absent from output PDF
[PASSED] No main.py modifications (v37.7.6 收敛原则)
```

## Plan 01-01 → 01-02 → 01-03 handoff

Plan 01-01 established the **safety floor** (SAFE-01 真删除 + SAFE-02 反向验证) and **architectural shape** (lazy privacyguard/pii/* + dataclass PIIHit + PyMuPDF add_redact_annot 模式).

后续 Plans 扩展面：
- **Plan 01-02** (engine expansion): tests/unit/test_pii_validators.py + test_pii_engine.py（≥20 断言）+ confidence tier edge cases + 跨行 split boundary（ENGINE-06）+ mask cache hit/miss + 500-page smoke（ENGINE-07）。
- **Plan 01-03** (worker + UI): ocr_worker.pii_signal + main.py 多处修改（page_data['pii'] key、SettingsDialog tab、canvas paintEvent PII loop、save_pdf pii_list merge）+ collect_full_page_ocr_hits + test_pii_offline + test_pdf_pii_pipeline（含 image-pixels-only 反向提取，B3 deferred scope）+ PyInstaller spec datas/hiddenimports 同步 + tests/unit/test_app_config.py pii_settings 扩展。

Tracer 通过 → Phase 1 可以安全展开后续 Plans。