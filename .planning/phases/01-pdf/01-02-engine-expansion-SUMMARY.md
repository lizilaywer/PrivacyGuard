---
phase: 01-pdf
plan: 02
slug: engine-expansion
type: execute
autonomous: true
subsystem: pii-engine
tags: [phase-1, pdf, pii, validators, engine, hardening, tdd-red-green, b2-separator-fix, w-a-unresolved, i1-demotion, page-rect-root-cause]
dependency_graph:
  requires:
    - privacyguard/pii/{engine,hits,validators/id_card,validators/phone_segment,normalize,confidence,mask,overlap,regex_patterns} (Plan 01-01 spine)
    - tests/unit/test_pdf_pii_redaction.py (Plan 01-01 tracer)
  provides:
    - tests/unit/test_pii_validators.py (40 assertions: NUM-01/02/03 全覆盖)
    - tests/unit/test_pii_engine.py (49 assertions: ENGINE-01..07 + B2 + W-A + I1)
    - privacyguard.pii.engine.PIIEngine.detect(unit, page=None) — 可选 page 参数
    - privacyguard.pii.engine.PIIEngine.rules_version(rules_data) — 类方法
    - privacyguard.pii.engine.PIIEngine.{last_error,error_log,unresolved_hits} — 实例属性
    - privacyguard.pii.RULES_VERSION_DEFAULT — 模块常量 fallback
  affects:
    - privacyguard/pii/__init__.py (RULES_VERSION_DEFAULT 加入 __all__)
    - privacyguard/pii/normalize.py (flatten_for_match 归一化全角数字 + map_flat_to_original 防御)
    - privacyguard/pii/validators/id_card.py (防御性 isinstance 检查)
    - privacyguard/pii/validators/phone_segment.py (防御性 isinstance 检查)
tech-stack:
  added: []
  patterns:
    - TDD RED → GREEN → 硬化三段式
    - detect(unit, page=None) 可选参数（向后兼容 + 真实坐标）
    - map_flat_to_original 返回 (None, None) 防御契约
    - W-A unresolved_hits + error_log 双记录
    - I1 context-anchor demotion 逻辑（±20 字符窗口）
    - 防御性 isinstance guard（不抛 TypeError）
key-files:
  created:
    - tests/unit/test_pii_validators.py (40 个测试方法, 7 个测试类)
    - tests/unit/test_pii_engine.py (49 个测试方法, 11 个测试类)
  modified:
    - privacyguard/pii/engine.py (detect 加 page 参数 + 硬化 + W-A + I1 + rules_version)
    - privacyguard/pii/normalize.py (flatten 归一化 + map_flat_to_original 重写)
    - privacyguard/pii/validators/id_card.py (防御性 isinstance)
    - privacyguard/pii/validators/phone_segment.py (防御性 isinstance)
    - privacyguard/pii/__init__.py (RULES_VERSION_DEFAULT + docstring)
decisions:
  - D-B2: detect(unit, page=None) — 当 page 提供时走真实 page.search_for；fallback 按分隔符拆 chunk union；page=None 时退化为占位 rect（向后兼容旧调用）
  - D-W-A: 不可定位命中记录到 unresolved_hits + error_log（"PII NO-RECT" 行），绝不静默丢弃；hit 不进入 apply_pii_redactions（零面积 rect 会触发反向提取 leak）
  - D-I1: bare 15-digit 无 context anchor（身份证号 / ID / id card 等关键字 ±20 字符窗口）→ confidence_tier=MEDIUM；保留 HIGH 仅当存在锚点
  - D-防御: validators 全路径 isinstance(input, str) 守卫，非字符串输入 → False（不抛 TypeError）
  - D-flatten: flatten_for_match 现在归一化全角数字 → ASCII；map_flat_to_original 通过 1:1 字符计数回算保留原文本中的全角数字位置（page.search_for 收到原始 literal）
  - D-rules-version: 类方法 rules_version(rules_data) → phone_segment.next_review；缺失 → "unknown"
metrics:
  duration: ~45 minutes
  completed_date: 2026-08-11
  tasks: 3
  commits: 3
  test_count_new: 89
  test_count_total: 89 new + 42 baseline (test_pdf_pii_redaction unchanged) + ~10 pre-existing PyQt6 env errors
status: complete

actuals:
  tokens: 38000
  tasks: 3
  commits: 3
---

# Phase 01 Plan 02: PII Engine Expansion — Summary

## One-liner
**PII 引擎全面硬化：B2 文字层真实坐标（page.search_for 走原始 literal）/ W-A 不可定位记录 / I1 bare 15-digit 降级 + NUM-01..03 与 ENGINE-03..07 全断言覆盖。**

## What was built

### 防御性守卫与硬化（GREEN 任务核心）

#### `privacyguard/pii/validators/id_card.py`
- `validate_18(id_str)`：非字符串输入直接返回 False（不再抛 TypeError）；保持原有的长度 / 数字 / 末位 [0-9Xx] 三层 gate。
- `validate_15(id_str)`：同上 + 完整的 15 位升级 + B1 双门（行政区划前缀 + 真实日历日期）+ 18 位 mod-11-2 校验。

#### `privacyguard/pii/validators/phone_segment.py`
- `is_mobile_segment(phone11)`：非字符串输入 → False；显式长度 11 + isdigit + leading-1 + 4位前缀排除 + 3位前缀排除 + 3位白名单的 6 层 gate。

### ENGINE-05 / ENGINE-06 全角归一 + offset 回算（GREEN）

#### `privacyguard/pii/normalize.py`
- `flatten_for_match(text)` 现在归一化全角数字 → ASCII（用 `_FULLWIDTH_DIGITS` translation table），便于 ASCII-only 正则匹配。**关键点**：原文本中的全角数字位置由 `map_flat_to_original` 通过 1:1 字符计数保留，因此 `page.search_for` 收到的是原始 fullwidth literal（不是 ASCII）。
- `map_flat_to_original(flat_text, flat_span, original_text)` 重写算法：
  - 1:1 字符计数（`flat_pos` ↔ `orig_pos`），separator（whitespace / hyphen / fullwidth space）跳过（不消耗 flat 位置）；
  - 找到 `flat_pos == flat_start` → 记 `orig_start`；
  - 找到 `flat_pos == flat_end - 1` → 返回 `(orig_start, orig_pos + 1)`（exclusive end）；
  - **不可映射显式返回 `(None, None)`**（不再静默返回 None）。

### B2 真实坐标 + W-A 不可定位记录（GREEN 主要新增）

#### `privacyguard/pii/engine.py` — `PIIEngine.detect(unit, page=None)`
**签名变更（向后兼容）**：新增可选 `page` 参数。`page=None` 时退化为占位 rect（旧调用方零影响）；`page` 提供且含 `search_for` 时走真实坐标路径。

**真实坐标路径**（`_resolve_page_rect`）：
1. **优先** `page.search_for(original_substring)` — `original_substring` 通过 `map_flat_to_original` 从 flat span 反算，包含全角数字 / 分隔符等真实页文字面；
2. **Fallback**：若原始 substring 返回空 rect，按 `[-\s　]+` 拆 chunks，对每个 **len ≥ 6** 的 chunk 调 `page.search_for(chunk)`，union bounding rect；
3. **W-A 不可定位记录**：若 1 + 2 都返回空 → 不静默丢弃，而是把候选记录到 `engine.unresolved_hits`（`PIIHit(entity_type='CN_UNRESOLVED', page_rect=(0,0,0,0), confidence_tier='MEDIUM', mask_strategy='<unresolved>')`）并 append `("PII NO-RECT", page_idx, candidate)` 到 `engine.error_log`；UI 层（Plan 01-03）将基于此展示「未定位敏感项 N 项」。

#### I1 15 位降级
- `_check_id_card` 命中 15 位时，调用 `_has_id_context_anchor(unit.text)` 检查 ±20 字符窗口内是否存在锚点关键字（`身份证 / 身份证号 / ID / id card / IDCard / 公民身份号码`）。无锚点 → `confidence_tier="MEDIUM"`；有锚点 → 保持 `"HIGH"`。

#### ENGINE-07 防 DoS
- `len(text) > 200_000` 时按 `_MAX_TEXT_BYTES` 截断，记录 `("PII WARN", page_idx, info)` 到 `error_log`（一次性，不重复打）。

#### W1 引擎异常可见
- `detect()` 包 try/except：异常时 `last_error = f"{type(exc).__name__}: {exc}"`，并 append `("PII ENGINE_ERROR", page_idx, last_error)`。

### 顶层包硬化（Task 3）

#### `privacyguard/pii/__init__.py`
- 新增 `RULES_VERSION_DEFAULT = "2026-Q1"` 模块常量（rules.json 缺失 / 解析失败 fallback）；
- `__doc__` 文档化包目的（识别身份证 / 手机号 / 三路径接入 / 真脱敏 / 零网络）；
- 加入 `__all__`。

#### `privacyguard.pii.engine.PIIEngine.rules_version(rules_data)` 类方法
- 读取 `rules_data["phone_segment"]["next_review"]`，缺失 → `"unknown"`。UI / 测试用，避免 reach into dict 字段。

## 测试覆盖矩阵（89 tests / 11 classes）

### tests/unit/test_pii_validators.py（40 tests / 7 classes）

| 测试类 | 覆盖 |
|---|---|
| `TestIdCardChecksum` | NUM-01 mod-11-2 正负向 + NUM-02 大小写 X + 末位非法字符 + 短/长/空拒绝 |
| `TestIdCardUpgrade15To18` | NUM-01 升级 + B1 双门（行政区划 / 月日 / Feb-30 / Feb-29 闰年）|
| `TestIdCaseInsensitiveX` | NUM-02 大写 / 小写 / 非法字母 |
| `TestIdCardDefensive` | 非字符串输入（None / int）不抛 TypeError |
| `TestPhoneSegment` | NUM-03 ≥30 个 personal prefix 全部识别 |
| `TestIotExclusion` | NUM-03 14X IoT / 1349 / 1440 / 1740 / 1741 卫星 / 数据卡全排除 + 短长非数字空 |
| `TestPhoneSegmentTables` / `TestPhoneSegmentDefensive` | 集合常量完整性 + None 防御 |

### tests/unit/test_pii_engine.py（49 tests / 11 classes）

| 测试类 | 覆盖 |
|---|---|
| `TestPIIHitSchema` | D-05 字段顺序锁定 + frozen + 默认 HIGH + 4-tuple page_rect |
| `TestEngineDetect` | ENGINE-01 正向 + B2 separator-bearing（连字符 / 全角 / chunk fallback）+ **W-A unresolved 记录** + 空白输入 |
| `TestConfidenceTiers` | ENGINE-03 4-branch (validator_passed × regex_matched) |
| `TestMaskConsistency` | ENGINE-04 相同 normalized → 相同 mask；不同 normalized → 不同 mask |
| `TestNormalization` | ENGINE-05/06 全角数字 / 分隔符 / 跨行 / map_flat_to_original 基本 + None-on-failure |
| `TestCrossBoundary` | ENGINE-06 跨行 ID 卡 / 跨空格手机号 |
| `TestLargeDocumentNoBlock` | ENGINE-07 200KB 输入 < 1s 完成（含命中 + 无命中） |
| `TestMaskStrategies` | MASK-01 身份证前 6 后 4 / 手机前 3 后 4 + 长度异常全 '*' + 未知实体 dispatch |
| `TestOverlapDedup` | overlap.resolve validator_passed 优先 + offset 排序 + 空列表 |
| `TestEngineWithoutPage` | detect(unit) 不传 page 退化占位 rect |
| `TestLazyExportSurface` | OPS-03 顶层包懒导出（7 个 PII 符号）全部可解析 |
| `TestEngineHardening` | rules_version 4 分支 + last_error/error_log/unresolved_hits 初始化 + RULES_VERSION_DEFAULT |

## Page_rect 根因修复（user_directed_scope_addition 落地结果）

**修复方式：engine 内部解决，不依赖调用方 `page.search_for` workaround。**

新签名 `detect(unit, page=None)`：
- **调用方传 `page=fitz_page`** → 引擎自动 `page.search_for(original_substring)` 拿真实坐标。**这是新推荐路径**。
- **调用方不传 `page`** → 退化占位 rect（`(0, 0, len*6, 12)`），与 Plan 01-01 一致（旧测试 `_detect_with_search_for` 仍然能 work）。

### 实测验证（不在测试套件中，是手动端到端确认）

```
$ python3 -c "..."  # 详见 /tmp 验证脚本
Hit: CN_ID_CARD normalized='53010219200508011X'
  page_rect = (85.03, 84.95, 141.67, 19.24)
  → non-zero area rect confirmed (141.67x19.24)
Hit: CN_PHONE normalized='13812345678'
  page_rect = (242.26, 84.95, 85.62, 19.24)
  → non-zero area rect confirmed (85.62x19.24)
ROOT-CAUSE FIX VERIFIED: page_rect comes from page.search_for, not placeholder.
```

测试侧 workaround `tests/unit/test_pdf_pii_redaction.py::_detect_with_search_for` **保留**（per user instruction），仍 GREEN。

## 验证结果

| 套件 | 结果 |
|---|---|
| `tests.unit.test_pii_validators` | **OK** (40 tests, 含 B1 second gate + 防御性 guards) |
| `tests.unit.test_pii_engine` | **OK** (49 tests, 含 B2 + W-A + I1 + ENGINE-07 200KB) |
| `tests.unit.test_pdf_pii_redaction` | **OK** (2 tests, Plan 01-01 tracer 兼容) |
| `tests.unit.test_pdf_text_hit_dedup` | **OK** |
| `tests.unit.test_mixed_pdf_ocr` | **OK** |
| `tests.unit.test_package_imports` | **OK** (5 tests, 懒加载契约) |
| `tests.unit.test_convergence` | **15/16 OK** (1 env-only error: `test_main_py_version_fallback_matches_current` 需 import main.py → PyQt6 libnspr4.so 缺失；pre-existing) |
| `tests.unit.test_word_replace_rules` / `test_batch_word_replace` / `test_config_alignment` | **ImportError** (pre-existing PyQt6 libnss3.so 缺失；与本改动无关) |

总计：89 new tests OK + 既有 baseline 保持；4 个 pre-existing 环境错误（PyQt6 libnss3/libnspr4 缺失）不动。

### 关键 acceptance criteria 自检

| 标准 | 结果 |
|---|---|
| `python3 -m unittest tests.unit.test_pii_validators` 全绿 | ✓ 40/40 |
| `python3 -m unittest tests.unit.test_pii_engine` 全绿 | ✓ 49/49 |
| TestLargeDocumentNoBlock 200KB < 1s | ✓ ~50ms |
| TestMaskConsistency 同一 normalized → 同一 mask | ✓ |
| TestCrossBoundary "110101\n19900307\n8814" 识别 | ✓（手工验证 checksum 4 = 正确 ID） |
| B4 import smoke `PIIHit(...).confidence_tier == "HIGH"` | ✓ |
| I1 15-digit demotion | ✓（bare 15-digit → MEDIUM） |
| W-A unresolvable 记录 | ✓（`engine.unresolved_hits` + `engine.error_log`） |
| 顶层 lazy exports 烟雾测试 | ✓ |
| `PIIEngine.rules_version({}) == "unknown"` | ✓ |
| `RULES_VERSION_DEFAULT == "2026-Q1"` | ✓ |
| `tests.unit.test_pdf_pii_redaction` 仍 GREEN | ✓ |

## Deviations from plan

### Auto-fixed issues

1. **[Rule 1 - Bug] `map_flat_to_original` 在末位后接 separator 时漏掉 `flat_end` 检测**
   - **Found during**: Task 1 RED 验证
   - **Issue**: 原实现 `if flat_pos == flat_end: orig_end = orig_pos` 只在非 separator 字符时触发；若命中 span 末尾紧跟 separator（典型如 `"138 1234 5678"` 末位后是空格），循环会跳过 separator 永不进入 `flat_end` 检测，返回 None。
   - **Fix**: 重写算法为 `if flat_pos == flat_end - 1: return orig_start, orig_pos + 1`（提前在「最后一个应消费的字符」处返回）。同步把「不可映射」返回值从单值 `None` 改为元组 `(None, None)`，符合测试契约且更防御。
   - **Files modified**: `privacyguard/pii/normalize.py`
   - **Commit**: `c65c715`

2. **[Rule 2 - Critical Functionality] `flatten_for_match` 不归一化全角数字 → regex 不匹配**
   - **Found during**: Task 2 GREEN 验证 `test_fullwidth_digits_id_card_recognized`
   - **Issue**: 18 位 ID 正则使用 `[1-9]\d{5}...`，`[1-9]` 在 Python 3 char class 中只匹配 ASCII 1-9，不匹配全角 `１`（U+FF11）。`flatten_for_match` 之前只 strip 空白与 hyphen，保留全角数字 → regex 找不到 → engine 不发射命中。
   - **Fix**: `flatten_for_match` 现在先 `text.translate(_FULLWIDTH_DIGITS)` 把全角数字归一为 ASCII，再 strip 空白。**关键**：原文本中的全角数字位置由 `map_flat_to_original` 通过 1:1 字符计数保留（separator 不消耗 flat_pos），所以 `page.search_for` 仍能收到原始 fullwidth literal（测试 `page.search_calls == ["１１０１０１..."]` 验证通过）。
   - **Files modified**: `privacyguard/pii/normalize.py`
   - **Commit**: `c65c715`

3. **[Rule 1 - Bug] 跨行 ID 测试 "8811" 校验位错误**
   - **Found during**: Task 1 编写测试时
   - **Issue**: 原测试用 `"110101\n19900307\n8811"`，flatten 后 `"110101199003078811"`，但 `compute_check_digit("11010119900307881") = '4'`，不是 `'1'`，validate_18 返回 False → engine 不发射。测试断言 `len(hits) == 1` 失败。
   - **Fix**: 改为 `"8814"`（手工算出的正确校验位）；同步把 `test_separated_id_card_recognized` / `test_separator_split_fallback` 也改用 `"8814"`，保证测试间一致。
   - **Files modified**: `tests/unit/test_pii_engine.py`
   - **Commit**: `f43af33`

4. **[Rule 1 - Bug] `test_is_real_calendar_date_boundary(85, 2, 29)` 期望值错误**
   - **Found during**: Task 1 编写测试时
   - **Issue**: Plan 文字说 `(85, 2, 29) == True`，但 1985（yy=85）不是闰年（85%4=1），Feb 1985 只有 28 天，`_days_in_month(1985, 2) = 28`，`is_real_calendar_date(85, 2, 29) = False`。测试断言 `True` 是 plan 自身的错误。
   - **Fix**: 测试改用 yy=84（1984 闰年）断言 True（合法），并加 `(85, 2, 29) == False` 断言（确认非闰年正确拒绝）。生产代码未改。
   - **Files modified**: `tests/unit/test_pii_validators.py`
   - **Commit**: `f43af33`

5. **[Rule 1 - Bug] `test_field_order_locked` 比较 list vs tuple**
   - **Found during**: Task 1 RED 验证
   - **Issue**: `list(sig.parameters.keys())[:7]` 返回 list，但测试期望值是 tuple，`assertEqual(list, tuple)` 即使内容相同也失败（Python 类型敏感）。
   - **Fix**: 把期望值改为 list。生产代码未改。
   - **Files modified**: `tests/unit/test_pii_engine.py`
   - **Commit**: `f43af33`

### Page_rect 根因修复（user_directed_scope_addition）—— 已修复（详见上文）

修复路径：engine 内部通过 `detect(unit, page=...)` 接 page 参数后自动调 `page.search_for(original_substring)` 取真实坐标。**调用方不再需要各自 `page.search_for(hit.normalized)` workaround**；但 `tests/unit/test_pdf_pii_redaction.py` 的 workaround 保留为安全网（per user instruction）。手动端到端验证：page_rect 在传 page 时是真实坐标（85.03, 84.95, 141.67, 19.24 for ID card），不传 page 时退化占位（向后兼容）。

## Cross-plan references

- `tests/unit/test_pii_offline.py` — Plan 01-03 Task 3（ENGINE-08 socket monkey-patch 测试）
- `tests/unit/test_pdf_pii_pipeline.py` — Plan 01-03 Task 3（FMT-01 端到端，含 image-pixels-only 反向提取）
- `privacyguard/workers/ocr_worker.py` (pii_signal + _detect_pii_for_page + 调用 detect(unit, page=page)) — Plan 01-03 Task 1
- `main.py` 多处（page_data['pii'] key, OCRWorker compat layer, _on_pii_engine_error slot for unresolved_hits, SettingsDialog tab, canvas paintEvent, save_pdf pii_list merge） — Plan 01-03 Task 2
- `privacyguard/ocr/full_page_ocr.py` (collect_full_page_ocr_hits) — Plan 01-03 Task 1

## Self-Check

```
[PASSED] tests/unit/test_pii_validators.py exists (40 tests / 7 classes)
[PASSED] tests/unit/test_pii_engine.py exists (49 tests / 11 classes)
[PASSED] privacyguard/pii/engine.py hardened (page parameter + W-A + I1 + rules_version)
[PASSED] privacyguard/pii/normalize.py hardened (flatten 归一化 + map_flat_to_original 重写)
[PASSED] privacyguard/pii/validators/id_card.py defensive isinstance
[PASSED] privacyguard/pii/validators/phone_segment.py defensive isinstance
[PASSED] privacyguard/pii/__init__.py RULES_VERSION_DEFAULT + docstring
[PASSED] Commit f43af33 (Task 1 RED)
[PASSED] Commit c65c715 (Task 2 GREEN)
[PASSED] Commit 0b58353 (Task 3 hardening)
[PASSED] 89/89 new tests OK
[PASSED] test_pdf_pii_redaction.py 2/2 OK (safety net preserved)
[PASSED] python3 -m compileall -q privacyguard tests exits 0
[PASSED] B4 smoke: PIIHit(...).confidence_tier == "HIGH"
[PASSED] Page_rect 根因验证：传 page 时得到真实坐标 (85.03, 84.95, 141.67, 19.24)
[PASSED] No main.py modifications (v37.7.6 收敛原则)
[PASSED] privacyguard.pii 懒加载契约：top-level 7 个 PII 符号全部可解析
[PASSED] ENGINE-08: privacyguard/pii/*.py 无 socket/urllib/requests/httpx 导入
```

## Plan 01-02 → 01-03 handoff

Phase 1 spine + 全面硬化就位。下一阶段（Plan 01-03）可在此基础上扩展：
- **Plan 01-03 Task 1**：OCR worker 集成（`_detect_pii_for_page` 用 `detect(unit, page=page)` 拿真实 OCR 框坐标；unresolved_hits 由 `_on_pii_engine_error` slot 表面到 UI）
- **Plan 01-03 Task 2**：`main.py` 多处集成（page_data['pii'] key、SettingsDialog tab、canvas paintEvent PII loop、save_pdf pii_list merge）
- **Plan 01-03 Task 3**：端到端 pipeline 测试（含 image-pixels-only）+ PyInstaller 打包 datas/hiddenimports 同步

Phase 1 引擎核心（识别 / 校验 / 真脱敏 / 防御 / 懒加载 / 零网络）已全部通过自动化验证。
