---
phase: 01-pdf
plan: 03
slug: worker-and-ui
type: execute
autonomous: true
subsystem: pii-runtime
tags: [phase-1, pdf, pii, worker, ui, settings, offline, packaging, tdd-red-green, w-b, b3, b5, b6, c5, d-04, fmt-01, engine-08, cp30, w2]
dependency_graph:
  requires:
    - privacyguard/pii/{engine,hits,validators,pdf_adapter} (Plan 01-01 + 01-02 spine + B2/W-A hardening)
    - privacyguard/ocr/text_pdf.py + mixed_pdf.py (existing OCR paths)
    - privacyguard/workers/ocr_worker.py (OCR worker scaffold)
    - main.py OCRWorker compat layer + SettingsDialog scaffold
  provides:
    - privacyguard.ocr.full_page_ocr.{collect_full_page_ocr_hits,render_full_page_to_bgr} (D-03 library export)
    - privacyguard.workers.ocr_worker.OCRWorker.pii_signal (page_idx, [PIIHit.asdict, ...])
    - privacyguard.workers.ocr_worker.OCRWorker._get_pii_engine (cp30 lazy init)
    - privacyguard.workers.ocr_worker.OCRWorker._detect_pii_for_page (per-page detect)
    - main.py MainWindow.{pii_settings,_pii_data_lock,_on_pii_page_result}
    - main.py SinglePageCanvas.{main_window parameter,PII paint loop,defensive getattr guard}
    - main.py SettingsDialog "5 隐私识别" tab with 3 QCheckBox + scope label
    - config.json + config.json.template pii_settings block
    - PyInstaller parity: both specs contain privacyguard/pii/data datas + pii hiddenimports
  affects:
    - main.py (six UI sites + compat layer + settings tab + canvas paint)
    - config.json + config.json.template (pii_settings block)
    - tests/unit/test_app_config.py (extended with pii_settings round-trip tests)
    - tests/unit/test_full_page_ocr.py (new — 12 tests covering DI signature + worker wire)
    - tests/unit/test_pii_offline.py (new — ENGINE-08 500-page socket monkey-patch)
    - tests/unit/test_pdf_pii_pipeline.py (new — FMT-01 text + image-block + save-loop end-to-end)
    - packaging/windows/config/PrivacyGuard_windows.spec (datas + hiddenimports)
    - packaging/macos/config/PrivacyGuard.spec (datas + hiddenimports — B5)
    - packaging/macos/scripts/build_complete.sh (parity check for rules.json)
tech-stack:
  added: []
  patterns:
    - W-B / W2 reconciliation: full-page OCR fallback library export is dead-code for Phase 1;
      worker run loop uses existing line 397-398 promotion through collect_image_block_ocr_hits
    - cp30 懒加载: PIIEngine lazy import inside `_get_pii_engine()` (no eager top-level)
    - dataclass.asdict → PIIHit(**h) round-trip between worker thread and MainWindow slot
    - QMutex(QMutexLocker) pattern for page_data[page]["pii"] writes
    - dependency-injection DI for full_page_ocr (recognize_fn / calculate_rect_fn / render_fn)
    - PyInstaller datas + hiddenimports parity between Windows + macOS specs (B5)
key-files:
  created:
    - privacyguard/ocr/full_page_ocr.py (D-03 library export + dead-code docstring marker)
    - tests/unit/test_full_page_ocr.py (12 tests — DI signature + worker pii_signal)
    - tests/unit/test_pii_offline.py (ENGINE-08 socket monkey-patch + static import scan)
    - tests/unit/test_pdf_pii_pipeline.py (3 tests — text-layer + image-block + save-loop)
  modified:
    - privacyguard/ocr/__init__.py (re-export collect_full_page_ocr_hits + render_full_page_to_bgr)
    - privacyguard/workers/ocr_worker.py (pii_signal + lazy engine + detect method + run-loop wire)
    - main.py (six sites + compat layer B6 + canvas PII loop C5 + settings tab D-09)
    - config.json (pii_settings block)
    - config.json.template (pii_settings block)
    - tests/unit/test_app_config.py (2 new pii_settings round-trip tests)
    - packaging/windows/config/PrivacyGuard_windows.spec (datas + hiddenimports)
    - packaging/macos/config/PrivacyGuard.spec (datas + hiddenimports — B5)
    - packaging/macos/scripts/build_complete.sh (rules.json parity check)
decisions:
  - D-03 库导出 vs 调用方: full_page_ocr.py 是 Phase 1 library export；worker run loop 不直接调用
    （W-B）；现有 line 397-398 promotion through collect_image_block_ocr_hits 已是 full-page fallback。
    模块 docstring 以 "DEAD CODE — Phase 1 library export." 开头，避免误认为未接线路径。
  - D-04 pii_signal payload: (page_idx, [dataclasses.asdict(h) for h in hits]) — MainWindow slot
    反序列化回 PIIHit(**h) 并写入 page_data[page]["pii"]。QMutex + QMutexLocker 保护写入。
  - D-B5 macOS spec parity: 之前只有 windows spec 加了 datas，macOS spec 是 PyInstaller 真正读的源；
    已同步两条 hiddenimports + datas 项。
  - D-B6 OCRWorker compat layer: 之前签名没扩 pii_engine_enabled / pii_settings，调用方
    (start_ocr) 现在传这两个 kwargs，签名已扩展 + super().__init__ forward。
  - D-C5 canvas main_window 注入: SinglePageCanvas 签名加 main_window=None 默认值；防御性
    getattr guard 保护旧调用点。已 enumerate main.py 的所有 2 处实例化（canvas_left / canvas_right）
    改为 SinglePageCanvas(0, main_window=self) / SinglePageCanvas(1, main_window=self)。
  - D-CP30 打包: 两条 PyInstaller spec 都包含 (privacyguard/pii/data, privacyguard/pii/data) 数据
    + 7 个 privacyguard.pii.* hiddenimports；macOS build_complete.sh 加 rules.json 存在性 parity check。
  - D-I3 防平凡绿: 每个 test_pdf_pii_pipeline 子测试都有 pre-condition assert len(hits) >= N
    （text-layer >= 2, image-block >= 1），防止引擎空命中但测试通过的真空绿色。
  - D-W-A 不可定位: 引擎的 unresolved_hits + error_log 由 _on_ocr_finished_safe 槽消费；
    I2 PII engine error consumer（未在 Phase 1 实现；由 Phase 2 review queue 接管）。
metrics:
  duration: ~30 minutes
  completed_date: 2026-08-11
  tasks: 3
  commits: 4
  test_count_new: 21
  test_count_total: 198 baseline + Plan 01-01 + Plan 01-02 + Plan 01-03 (12 full_page_ocr + 2 pii_offline + 3 pdf_pii_pipeline + 2 app_config + 2 pii_engine already in 01-02)
status: complete

actuals:
  tokens: 31000
  tasks: 3
  commits: 4
---

# Phase 01 Plan 03: Worker + UI + Settings + Offline + Packaging — Summary

## One-liner

**把 PII 引擎接入 PrivacyGuard 运行时最后一公里 — collect_full_page_ocr_hits 库导出 + worker pii_signal + main.py UI 6 处接线 + config pii_settings + ENGINE-08 零网络守护 + 跨平台 PyInstaller datas parity。**

## What was built

### Task 1: full_page_ocr library + worker pii_signal

#### `privacyguard/ocr/full_page_ocr.py` (NEW)
- 模块 docstring 以 "DEAD CODE — Phase 1 library export." 开头（W2 reconciliation — 避免
  后续 reviewer 误认为未接线路径）。
- `render_full_page_to_bgr(page, scan_scale)`：try/except 包装，None on error。
- `collect_full_page_ocr_hits(page, scan_scale, recognize_fn, calculate_rect_fn, ...)`：
  D-03 DI 形态（与 collect_image_block_ocr_hits 同形），返回 [(x, y, w, h), ...]。
- **W-B 验收硬条件：** `grep -c "collect_full_page_ocr_hits" privacyguard/workers/ocr_worker.py == 0`。

#### `privacyguard/ocr/__init__.py` (modified)
- 加 eager re-export: `from privacyguard.ocr.full_page_ocr import collect_full_page_ocr_hits, render_full_page_to_bgr`
- `__all__` 扩展。

#### `privacyguard/workers/ocr_worker.py` (modified)
- 新信号 `pii_signal = pyqtSignal(int, list)` 在 `error_signal` 后。
- `__init__` 扩展：`pii_engine_enabled: bool = False`, `pii_settings: dict = None`，存为
  `self.pii_engine_enabled` / `self._pii_settings` / `self._pii_engine = None`（cp30 懒加载）。
- `_get_pii_engine()`：try/except 包裹 `from privacyguard.pii.engine import PIIEngine` + 缓存。
- `_detect_pii_for_page(page, page_idx, page_text, page_rects)`：根据 page_text 是否 strip()
  设置 source（text 或 image_block），调 `engine.detect(unit, page=page)` 拿真实 OCR 框坐标，
  返回 `[dataclasses.asdict(h) for h in hits]`。失败时 print + 返回 []。
- run() 循环在 `page_result_signal.emit(i, rects)` 之后插入 `pii_hits = self._detect_pii_for_page(...)`，
  非空时 `self.pii_signal.emit(i, pii_hits)`。

### Task 2: main.py UI surfaces + config + tests

#### Site 1 (config read ~4892)
- `MainWindow.__init__` 从 `config.get("pii_settings.*")` 读取三个 bool
  （`engine_enabled` / `auto_redact` / `require_confirmation`），缺省 fallback 到 True/True/False。
- `_pii_data_lock = QMutex()`（v36.5 镜像 `_word_data_lock` 模式）。

#### Site 2 (page_data init ~10521)
- `page_data = {i: {'ocr': [], 'manual': [], 'pii': []} for i in range(total)}`（D-04 锁定）。

#### Site 3a (OCRWorker compat layer ~4191, B6)
- 签名加 `pii_engine_enabled: bool = False, pii_settings: dict = None`，`super().__init__`
  转发给 `_ModularOCRWorker`。

#### Site 3b (start_ocr ~11130)
- `OCRWorker(...)` 调用传 `pii_engine_enabled=self.pii_settings.get("engine_enabled", True)` +
  `pii_settings=self.pii_settings`。
- `self.worker.pii_signal.connect(self._on_pii_page_result)` 连接。

#### Site 4 (_on_pii_page_result ~11255)
- 新方法：lazy import `from privacyguard.pii.hits import PIIHit`，在 `QMutexLocker(self._pii_data_lock)`
  保护下写入 `self.page_data[page_num]["pii"] = [PIIHit(**h) for h in pii_hits]`，当前页时调 `render_view()`。

#### Site 5 (SinglePageCanvas.__init__ + paintEvent, C5)
- `__init__(self, page_index=0, parent=None, main_window=None)` — 加 `main_window` 参数。
- `canvas_left = SinglePageCanvas(0, main_window=self)` /
  `canvas_right = SinglePageCanvas(1, main_window=self)`（C5 — 全部实例化点）。
- `paintEvent` 在拖拽框 loop 后追加第四绘制循环：
  - `QPen(QColor("#D64545"), 2)` + `QBrush(QColor("#D64545")).setAlphaF(0.18)`；
  - 防御性 `getattr(self, 'main_window', None)` guard，无 main_window 时跳过；
  - 对每个 PIIHit 画边框 + 标签徽章（"ID" / "PHONE"），徽章背景纯 #D64545 + 白字。

#### Site 6 (save_pdf ~12354)
- `ocr_list + manual_list + pii_list` 三组都喂给 `add_redact_annot`；
- pii_list 用 `hit.page_rect` tuple 路径（不同于 ocr_list / manual_list 的 QRectF 路径）；
- 单次 `page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)` 烘焙三组一起真删除。

#### Site 7 (SettingsDialog ~1601)
- 新增 `box_pii` QFrame + QVBoxLayout（`objectName=settingsSectionCard`），插在 `box_ocr` 之后；
- 三个 QCheckBox（`cb_pii_engine_enabled` / `cb_pii_auto_redact` / `cb_pii_require_confirm`）
  + 锁定 tooltip；
- 只读 QLabel "扫描范围（只读）：身份证号 / 手机号"（`objectName=settingsFieldNote`）；
- `_sync_pii_toggle_state` 把 cb_pii_auto_redact / cb_pii_require_confirm 在
  cb_pii_engine_enabled OFF 时灰掉；
- `_settings_sections` 扩展为 `[box_rules, box_custom, box_enhance, box_ocr, box_pii]`；
- `save_settings` 持久化三个 bool 到 `pii_settings.*`。

#### config.json + config.json.template
- 加 `pii_settings` 块（engine_enabled=true / auto_redact=true / require_confirmation=false
  / scan_scope=["CN_ID_CARD","CN_PHONE"] + _comment）。

#### tests/unit/test_app_config.py
- `test_simple_config_pii_settings_default`：空 config 时 `get()` 返回 None。
- `test_simple_config_pii_settings_round_trip`：三个 bool 完整往返。

### Task 3: ENGINE-08 + FMT-01 + PyInstaller

#### tests/unit/test_pii_offline.py (NEW)
- `TestPiiOffline.test_engine_makes_no_network_calls`：`socket.socket` monkey-patch +
  500 页 `engine.detect(unit)`，断言 `len(socket_calls) == 0`。
- `TestPrivacyGuardPiiNoTopLevelNetwork.test_no_requests_or_httpx_imports`：
  扫描 `privacyguard/pii/**/*.py`，禁止 `import requests` / `httpx` / `urllib.request`
  / `aiohttp` / `from requests/httpx/urllib/aiohttp import`。

#### tests/unit/test_pdf_pii_pipeline.py (NEW)
- `test_text_layer_pdf_full_pipeline`：synth PDF → detect → apply → reverse-extract，
  **I3 pre-condition** `assert len(hits) >= 2`。
- `test_image_block_pdf_full_pipeline`：`TextUnit(source='image_block')` 注入，
  **I3 pre-condition** `assert len(hits) >= 1`，验证引擎在 image_block 源下识别命中。
- `test_save_loop_piilist_included_in_redaction`：模拟 main.py:12354 save loop 中 pii_list
  合并路径，整段端到端反向提取敏感字符串消失。

#### packaging/windows/config/PrivacyGuard_windows.spec
- datas 加 `(os.path.join(project_root, 'privacyguard', 'pii', 'data'), 'privacyguard/pii/data')`。
- hiddenimports 加 `privacyguard.pii` + 7 个子模块（`.engine` / `.hits` / `.validators` /
  `.validators.id_card` / `.validators.phone_segment` / `.pdf_adapter`）。

#### packaging/macos/config/PrivacyGuard.spec (B5 critical fix)
- 同 datas + 同 hiddenimports 7 项（之前 macOS spec 漏改 — frozen macOS 启动会静默
  加载空白名单，`is_mobile_segment` 返回 False，phone detection 死亡，正是 cp30 回归类）。

#### packaging/macos/scripts/build_complete.sh
- 加 parity check：`test -f "$APP_PATH/Contents/Resources/privacyguard/pii/data/rules.json"`，
  缺失即 exit 1 + 报 "[FAIL] PII 引擎在 frozen 包中无法加载规则，手机号检测将静默失败"。

## Test results

| Suite | Result |
|---|---|
| `tests.unit.test_full_page_ocr` | **OK** (12 tests — DI signature, render/OCR failure paths, page_xy tuple shape, worker pii_signal wire, W-B no-call invariant, D-01 three-path convergence) |
| `tests.unit.test_app_config` | **OK** (含 2 个新 pii_settings round-trip 测试) |
| `tests.unit.test_pii_offline` | **OK** (2 tests — 500-page socket monkey-patch + 静态 import scan) |
| `tests.unit.test_pdf_pii_pipeline` | **OK** (3 tests — text-layer + image-block + save-loop pii_list merge 端到端) |
| `tests.unit.test_pii_validators` | **OK** (无回归) |
| `tests.unit.test_pii_engine` | **OK** (无回归) |
| `tests.unit.test_pdf_pii_redaction` | **OK** (无回归) |
| `tests.unit.test_mixed_pdf_ocr` | **OK** (无回归) |
| `tests.unit.test_pdf_text_hit_dedup` | **OK** (无回归) |
| `tests.unit.test_package_imports` | **OK** (5 tests — 懒加载契约保留) |
| `tests.unit.test_convergence` | **OK** (TestPiiConvergence 6 tests — main.py 不含内联 PII 检测 / PIIHit 类) |
| `tests.unit.test_fstring_safety` / `test_config_alignment` / `test_word_replace_rules` / `test_batch_word_replace` / `tests.test_path_validation` / `tests.unit.test_ocr_api` | **OK** (无回归) |

总计：**198 tests pass + 2 skipped**（之前 baseline 是 79 + Plan 01-01/02 + ~115）。

### 关键 acceptance criteria 自检

| 标准 | 结果 |
|---|---|
| `python3 -m compileall -q main.py privacyguard tests` | ✓ exit 0 |
| `from privacyguard.ocr import collect_full_page_ocr_hits, render_full_page_to_bgr` | ✓ OK |
| `from privacyguard.workers.ocr_worker import OCRWorker; pii_engine_enabled + pii_settings 在签名` | ✓ OK |
| `_ModularOCRWorker.run` 包含 `pii_signal` / `_detect_pii_for_page` / 三路径（D-01） | ✓ OK |
| `grep -c "collect_full_page_ocr_hits" privacyguard/workers/ocr_worker.py` | ✓ 0 (W-B) |
| `python3 -c "import main; print('OK')"` | ✓ OK |
| `from main import OCRWorker` 签名 11 个 params 含 `pii_engine_enabled` / `pii_settings` | ✓ OK |
| `config.json + config.json.template` 含 `pii_settings.{engine_enabled=true, auto_redact=true, require_confirmation=false, scan_scope=['CN_ID_CARD','CN_PHONE']}` | ✓ OK |
| `tests.unit.test_app_config.test_simple_config_pii_settings_default + test_simple_config_pii_settings_round_trip` | ✓ OK |
| `tests.unit.test_convergence.TestPiiConvergence` | ✓ 6/6 OK |
| `tests.unit.test_pii_offline` (500-page socket) | ✓ 0 socket calls |
| `tests.unit.test_pdf_pii_pipeline` (3 paths) | ✓ all reverse-extract clean |
| `packaging/windows/config/PrivacyGuard_windows.spec` 含 `privacyguard/pii/data` + `'privacyguard.pii.engine'` | ✓ OK |
| `packaging/macos/config/PrivacyGuard.spec` 含 `privacyguard/pii/data` + `'privacyguard.pii.engine'` | ✓ OK (B5 parity) |
| `packaging/macos/scripts/build_complete.sh` 含 `privacyguard/pii/data` (parity check) | ✓ OK |
| 79 baseline + Plan 01-01 + Plan 01-02 + Plan 01-03 全部 green | ✓ 198 tests pass |

## Deviations from plan

### Auto-fixed issues

1. **[Rule 1 - Bug] `test_returns_page_xy_tuples_for_ocr_lines` 用 MagicMock.page 导致 cv2.imdecode 失败**
   - **Found during**: Task 1 GREEN 验证
   - **Issue**: 用 `MagicMock` 构造 fake_page 时，`fake_page.get_pixmap(...)` 返回 MagicMock；
     默认 render_fn (`render_full_page_to_bgr`) 调 `np.frombuffer(pix.tobytes("png"))` 会抛 TypeError，
     返回 None → `img_bgr is None` → `collect_full_page_ocr_hits` 返回 [] → 测试断言 `len > 0` 失败。
   - **Fix**: 测试改用真实 fitz page 配合注入 `render_fn=lambda p,s: np.zeros((100,100,3), uint8)`，
     让 render path 不走默认 MagicMock 链。生产代码未改。
   - **Files modified**: `tests/unit/test_full_page_ocr.py`
   - **Commit**: `ef47f45`

2. **[Rule 1 - Bug] `_ModularOCRWorker` 类名错误 —— 实际是 `OCRWorker`**
   - **Found during**: Task 1 RED 验证
   - **Issue**: PATTERNS.md / PLAN.md 写的是 `_ModularOCRWorker`，但 `privacyguard/workers/ocr_worker.py`
     的实际类名是 `OCRWorker(QThread)`（在 main.py 内部用 `from privacyguard.workers.ocr_worker import
     OCRWorker as _ModularOCRWorker` 别名）。
   - **Fix**: 测试用 `OCRWorker`（实际类名）；production wire 一致（`OCRWorker(...)` + `OCRWorker.__init__`
     + `OCRWorker.run`）。PATTERNS.md 后续 reviewer 可作 doc-only 更新（不在 Plan scope）。
   - **Files modified**: `tests/unit/test_full_page_ocr.py`
   - **Commit**: `ef47f45`

### Plan deviations

None — Tasks 1 + 2 + 3 all executed as written. The 165 unrelated dirty files
（CHANGELOG.md / README.md / v38 SVG assets / AGENTS.md / .planning/config.json 等）按指令
**未触碰**，只 stage 了 plan `files_modified` 列表中的文件。

## Cross-plan references

- Phase 1 完成 — 所有 3 个 plans（tracer / engine expansion / worker + UI）已 ship。
- Phase 2+ 接手点：
  - `pii_settings.scan_scope` 当前锁定为 `["CN_ID_CARD","CN_PHONE"]` —— Phase 2 扩展时
    应先扩 `privacyguard.pii.validators` 子模块再加 scan_scope 项（同步）。
  - `engine.last_error` / `engine.error_log` / `engine.unresolved_hits` 的 UI consumer
    （I2 — `_on_pii_engine_error` 槽）未在 Phase 1 实现；Phase 2 review queue 接管。
  - `_sync_pii_toggle_state` 是 Phase 1 最小 UX；Phase 7 review queue 提供完整 toggle semantics。

## Threat model coverage

| Threat | Disposition | Mitigation in this plan |
|---|---|---|
| T-03-FAKE | mitigate | save_pdf pii_list merge 走 add_redact_annot + apply_redactions(IMAGE_PIXELS) — 与 ocr/manual 同路径；test_pdf_pii_pipeline 端到端覆盖 |
| T-03-NETWORK | mitigate | test_pii_offline 500-page socket monkey-patch + 静态 import scan |
| T-03-LAZY-BREAK | mitigate | `_get_pii_engine` 懒加载（cp30 discipline）；test_package_imports 守 `import privacyguard` 不拉起 pii.engine |
| T-03-PYINSTALLER-MISS | mitigate | 两条 PyInstaller spec 都包含 (privacyguard/pii/data, privacyguard/pii/data) + 7 个 hiddenimports；build_complete.sh parity check |
| T-03-THREAD-RACE | mitigate | `_pii_data_lock = QMutex()` + QMutexLocker 保护 page_data[page]["pii"] 写入（与 _word_data_lock 同模式） |
| T-03-CONFIRM-SKIP | accept | Phase 1 最小 UX；Phase 7 review queue 接管 |
| T-03-PDF-PATH | mitigate | 现有 validate_safe_path 守门（cp30） |

## Self-Check

```
[PASSED] privacyguard/ocr/full_page_ocr.py exists with dead-code marker
[PASSED] privacyguard/ocr/__init__.py re-exports collect_full_page_ocr_hits + render_full_page_to_bgr
[PASSED] privacyguard/workers/ocr_worker.py has pii_signal + pii_engine_enabled + pii_settings
[PASSED] _ModularOCRWorker.run emits pii_signal after page_result_signal (D-04 wire)
[PASSED] W-B: grep -c "collect_full_page_ocr_hits" privacyguard/workers/ocr_worker.py == 0
[PASSED] main.py Site 1: pii_settings dict + _pii_data_lock
[PASSED] main.py Site 2: page_data has 'pii' key alongside 'ocr'/'manual'
[PASSED] main.py Site 3a: OCRWorker compat signature extended (B6)
[PASSED] main.py Site 3b: start_ocr wires pii_signal + pii_engine_enabled + pii_settings
[PASSED] main.py Site 4: _on_pii_page_result slot with PIIHit(**h) deserialization
[PASSED] main.py Site 5: SinglePageCanvas paintEvent PII loop + main_window injection (C5)
[PASSED] main.py Site 6: save_pdf pii_list merge with apply_redactions(IMAGE_PIXELS)
[PASSED] main.py Site 7: SettingsDialog "5 隐私识别" tab + 3 QCheckBox + scope label
[PASSED] config.json + config.json.template pii_settings block
[PASSED] tests/unit/test_app_config.py extended with pii_settings round-trip tests
[PASSED] tests/unit/test_full_page_ocr.py (12 tests)
[PASSED] tests/unit/test_pii_offline.py (2 tests: 500-page socket + static import scan)
[PASSED] tests/unit/test_pdf_pii_pipeline.py (3 tests: text-layer + image-block + save-loop)
[PASSED] packaging/windows/config/PrivacyGuard_windows.spec has privacyguard/pii/data datas + 7 hiddenimports
[PASSED] packaging/macos/config/PrivacyGuard.spec has privacyguard/pii/data datas + 7 hiddenimports (B5)
[PASSED] packaging/macos/scripts/build_complete.sh has rules.json parity check
[PASSED] Commit ef47f45 (Task 1 RED tests)
[PASSED] Commit f68ee89 (Task 1 GREEN impl)
[PASSED] Commit eb182bd (Task 2 GREEN: main.py UI + config + app_config tests)
[PASSED] Commit 0b97363 (Task 3 GREEN: ENGINE-08 + FMT-01 + PyInstaller)
[PASSED] 198 tests pass (79 baseline + Plan 01-01 + Plan 01-02 + Plan 01-03 = 21 new)
[PASSED] python3 -m compileall -q main.py privacyguard tests exits 0
[PASSED] python3 -c "import main; print('OK')"
[PASSED] v37.7.6 收敛原则 — main.py 没有内联 PII 检测实现（test_convergence 6/6 OK）
[PASSED] OPS-03 懒加载契约保留 — test_package_imports OK
[PASSED] ENGINE-08: privacyguard/pii/*.py 无 socket / requests / httpx / urllib / aiohttp 导入
[PASSED] PyInstaller B5 parity: windows + macOS specs 都包含 rules.json datas + pii.engine hiddenimports
```

## Phase 1 → Phase 2 handoff

Phase 1 spine + 引擎硬化 + worker 集成 + UI 接线 + 零网络守护 + 跨平台打包全部就位。
198 个测试全部 green，PyInstaller 打包双向 parity，懒加载契约保留。

Phase 2 接手点：
- 批量替换支持"每文件单独规则映射"
- 批量规则集模板管理
- 替换后预览按来源筛选高亮（rule / manual / ocr / pii）
- `_on_pii_engine_error` 槽消费 `engine.last_error` / `error_log` / `unresolved_hits`（I2）