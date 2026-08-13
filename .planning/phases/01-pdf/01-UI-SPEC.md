---
phase: 1
slug: pdf
status: approved
shadcn_initialized: false
preset: none
created: 2026-08-10
---

# Phase 1 — UI Design Contract

> Visual and interaction contract for Phase 1: PDF 自动识别身份证号与手机号并真脱敏.
> Tech stack: PyQt6 6.10.2 desktop app. No shadcn / no web. Theme tokens live in `theme.py`.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | PyQt6 (QWidget / QPainter / QSS) — shadcn not applicable |
| Preset | not applicable |
| Component library | PyQt6 standard widgets + `theme.py` QSS palette |
| Icon library | Existing `assets/branding/v38/*.svg` (load via `QIcon`); no new icon files this phase |
| Font | `theme.py:Theme.FONT_FAMILY` — `'Segoe UI Variable', 'Segoe UI', 'Microsoft YaHei UI', 'Microsoft YaHei', Arial, sans-serif` |
| Source of truth | `theme.py` (LIGHT/DARK dicts) — Phase 1 must NOT introduce a parallel palette |

---

## Spacing Scale

Reuse `theme.py` constants + 4-px-multiple scale for new components.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Tight icon gaps, line paddings inside chips |
| sm | 8px | Compact element spacing inside cards |
| md | 14px | `theme.SPACING_MEDIUM` — default element spacing (use this for new dialogs) |
| lg | 22px | `theme.SPACING_LARGE` — section padding |
| xl | 32px | Dialog outer margins |
| BORDER_RADIUS | 12px | `theme.BORDER_RADIUS` — frames, sidebars |
| BUTTON_RADIUS | 10px | `theme.BUTTON_RADIUS` — buttons, chips |

Exceptions:
- Status bar chip: min-height 22px (single-line text), horizontal padding 8px
- Touch target on `SinglePageCanvas` PII rects: hit-area expansion +2px already present in `pdf_to_screen` — reuse, do not add new touch-target rule

---

## Typography

Reuse `theme.py` font sizes. Phase 1 introduces NO new font sizes.

| Role | Size | Weight | Line Height | Source |
|------|------|--------|-------------|--------|
| Body / list item | 14px (`FONT_SIZE_NORMAL`) | Regular (400) | 1.5 | `theme.py` |
| Label / chip | 12px (`FONT_SIZE_SMALL`) | Regular (400) | 1.4 | `theme.py` |
| Heading / dialog title | 18px (`FONT_SIZE_LARGE`) | Semibold (600) | 1.3 | `theme.py` |

Weight scope: only `Regular (400)` and `Semibold (600)` are used. Do NOT introduce `Bold (700)` or `Light (300)`. Dialog titles in SettingsDialog already use existing `ObjectName`-based QSS — match that style.

---

## Color

All colors come from `theme.py` (`Theme.LIGHT` / `Theme.DARK`). Do NOT introduce new hex tokens.

| Role | Light hex | Dark hex | Usage |
|------|-----------|----------|-------|
| Dominant (60%) | `#FFFFFF` (surface) / `#F7F8FA` (background) | `#1E2836` / `#151C26` | Main window, dialog backgrounds |
| Secondary (30%) | `#F9FBFD` (info_bar) / `#F6F8FB` (scroll_area) | `#1E2A3B` / `#1A2330` | Side panels, info bar, scrolled areas |
| Accent (10%) | `#0F6CBD` (primary) | `#56A8FF` | Reserved for: SettingsDialog toggles when ON; "PII 自动识别已启用" status chip; "保存 PDF" button border |
| **NEW: PII highlight** | `#D64545` (danger, light) | `#FF6B6B` (danger, dark) | Reserved EXCLUSIVELY for: PII rect stroke + fill on `SinglePageCanvas`; status chip "识别引擎已停用" when OFF; confirmation dialog destructive button border |
| Destructive | `#D64545` (danger) | `#FF6B6B` | "立即脱敏" button in confirmation dialog (foreground color = `#FFFFFF`) |
| Success | `#0FA968` | `#34D399` | "识别完成" status chip when candidates > 0; "已确认全部脱敏" dialog accept button |

Accent reserved-for list (explicit, never "all interactive elements"):
1. SettingsDialog new "隐私识别" tab — toggle ON state visual cue
2. Status bar chip "PII 自动识别已启用"
3. SettingsDialog toggle switch track when enabled

PII highlight (danger color) reserved-for list (explicit):
1. `SinglePageCanvas.paintEvent` PII rect stroke + light-alpha fill (see Visuals §"PII Rect Rendering")
2. Status bar chip "识别引擎已停用" (OFF state, paired with secondary background)
3. Confirmation dialog "立即脱敏" button (destructive CTA)

Color reuse rule: `#0F6CBD` (primary) MUST NOT appear on a PII rect. The PII highlight color MUST NOT appear on a settings toggle. This is the visual differentiator between "settings state" and "sensitive content".

---

## Copywriting Contract

All copy is Simplified Chinese (zh-CN), matching `main.py` convention.

| Element | Copy |
|---------|------|
| SettingsDialog new tab title | `5 隐私识别` |
| Tab lead label | `打开 PDF 后自动扫描身份证号与手机号，并在保存时真脱敏。所有匹配纯本地完成。` |
| Toggle 1 label | `启用隐私识别引擎` |
| Toggle 1 tooltip | `关闭后，PDF 打开时不再扫描敏感项。仅影响 PII 自动识别，不影响现有 OCR 与手动框选。` |
| Toggle 2 label | `扫描后自动真脱敏` |
| Toggle 2 tooltip | `HIGH 档命中直接进入脱敏列表，保存 PDF 时一次性真删除。关闭后命中仅高亮，需手动确认。` |
| Toggle 3 label | `HIGH 档命中需手动确认` |
| Toggle 3 tooltip | `开启后，HIGH 档命中弹出确认对话框，由您决定每条是否脱敏。仅在该确认路径下生效；关闭时按上方的"自动真脱敏"开关处理。` |
| Status chip ON | `PII 自动识别 已启用` (primary color foreground) |
| Status chip OFF | `识别引擎已停用` (danger color foreground on secondary background) |
| Status chip scanned-with-candidates | `已识别 N 项敏感内容` (success color foreground) |
| Status chip scanned-no-candidates | `扫描完成：未发现敏感内容` (text_secondary) |
| Progress stage 1 (queued) | `排队等待识别…` |
| Progress stage 2 (text-layer scan) | `扫描第 X / Y 页…` |
| Progress stage 3 (OCR fall-back) | `扫描件识别中（第 X / Y 页）…` |
| Progress stage 4 (applying) | `正在应用真脱敏…` |
| Progress stage 5 (done) | `识别完成：共 N 项敏感内容` |
| Confirmation dialog title | `发现 N 项 HIGH 档敏感内容` |
| Confirmation dialog body | `本次扫描在 PDF 中检测到 N 项高置信度敏感内容（身份证号 / 手机号）。请逐条确认是否脱敏；未确认的项将保持原样。` |
| Confirmation dialog column header | `类型 · 原文预览` |
| Confirmation dialog row format | `身份证号  ·  110101********1234…` (entity_type + masked preview, original text NOT shown in plain — show the suggested mask with ellipsis when longer) |
| Confirmation dialog primary CTA | `全部脱敏并保存` |
| Confirmation dialog secondary CTA | `仅脱敏选中的 N 项` |
| Confirmation dialog cancel CTA | `暂不脱敏（仅高亮）` |
| Confirmation dialog destructive edge case | When user toggles OFF `auto_redact` after seeing the dialog: `已切换为仅高亮模式，原确认结果保留为红色高亮。` (shown as info bar message, NOT as a separate dialog) |
| Error state (PDF open failure post-PII) | `文档打开成功，但隐私识别引擎初始化失败（{exception_class}）。请重新打开或前往设置关闭隐私识别。其他功能仍可正常使用。` |
| Error state (JSON rules file missing) | `无法加载识别规则（rules.json 缺失或被损坏）。已自动关闭隐私识别。` |

Tone rules (locked):
- Body copy addresses the user as 您 in tooltips/dialogs.
- Status chips use noun phrases, not imperative verbs.
- Copy NEVER includes `*` / `#` placeholder text outside of code-block demos.

---

## New Components Introduced

Phase 1 introduces exactly these UI surfaces. No other widgets.

| Component | Type | Role |
|-----------|------|------|
| SettingsDialog "5 隐私识别" section card | `QFrame` (object name `settingsSectionCard`) added to existing SettingsDialog scroll area | Houses the three toggles + a 4th label "扫描范围（只读）" showing `身份证号 / 手机号` for Phase 1 (locked to two types per NUM-01..03) |
| PII confirmation dialog | `QDialog` (modal, `Qt.WindowModality.ApplicationModal`) shown only when `require_confirmation=true` AND HIGH hits present | Lists candidates with masked preview; primary/secondary/cancel CTA |
| Status bar PII chip | `QLabel` (object name `piiStatusChip`) embedded into existing `info_bar` | Surfaces ON/OFF/scanning/done states |
| `SinglePageCanvas` PII rendering | New third loop in `paintEvent` after `rects_ocr` / `rects_manual` | Draws PII rects with distinct stroke + label |
| Page-data carrier | Existing `page_data[page_num]["pii"]` key holding `List[PIIHit]` | New dataclass, no new top-level structure |

No new icons this phase. The status chip uses text only. The confirmation dialog reuses the existing dialog QSS (`_apply_dialog_theme` already exists on `SettingsDialog`).

---

## Visuals

### PII Rect Rendering (SinglePageCanvas)

Locked tokens (no other values allowed):

| Property | Light | Dark |
|----------|-------|------|
| Stroke color | `#D64545` (danger) | `#FF6B6B` (danger) |
| Stroke width | `2 px` (device pixels) | `2 px` |
| Fill color | `#D64545` @ alpha `0.18` | `#FF6B6B` @ alpha `0.22` |
| Label text color | `#FFFFFF` | `#151C26` |
| Label background | `#D64545` (solid) | `#FF6B6B` (solid) |
| Label font | 12px / Regular / `'Microsoft YaHei UI', sans-serif` | same |
| Label height | 16px (single line) | same |
| Label position | Anchored to top-left of rect, 2px outset | same |

Paint order in `paintEvent` (lock order, do not reorder):
1. `rects_ocr` (existing — `mask_color` brush, no pen)
2. `rects_manual` (existing — `mask_color` brush, no pen)
3. **`rects_pii` (NEW)** — draw fill first, then stroke on top, then label badge anchored at top-left corner of the rect.

Label text format per PII rect: `"ID"` for ID card hits, `"PHONE"` for phone hits. All uppercase ASCII, no entity_type ID strings. (Entity-type mapping is in PIIHit dataclass; the canvas displays the short label.)

Hit-test parity: PII rects are read-only on canvas this phase. Right-click delete loop in `SinglePageCanvas.mousePressEvent` MUST skip PII rects (do not delete them via canvas). Comment annotation in code: `# Phase 1: PII rects are read-only on canvas; deletion handled by Phase 7 review UI`.

### SettingsDialog "5 隐私识别" Card Layout

Follows existing `settingsSectionCard` pattern (no new QSS object). Inserted as the 5th `box_*` in `SettingsDialog.__init__` content layout, after the existing `box_ocr` card.

```
[card frame, padding 16/16/16/16, spacing 12]
  header (existing _create_settings_section_header helper)
    title: "5. 隐私识别"
    lead:   [see Copywriting §tab lead]
    summary label: live "[ON] 自动真脱敏 · 关闭确认弹窗" or similar status
  [spacing 14]
  toggle row 1: "启用隐私识别引擎"  [QCheckBox, default ON]
    tooltip: [see Copywriting]
  toggle row 2: "扫描后自动真脱敏"  [QCheckBox, default ON]
    tooltip: [see Copywriting]
    disabled when toggle 1 OFF
  toggle row 3: "HIGH 档命中需手动确认"  [QCheckBox, default OFF]
    tooltip: [see Copywriting]
    disabled when toggle 1 OFF or toggle 2 OFF
  [spacing 14]
  read-only label: "扫描范围（只读）：身份证号 / 手机号"
    font: 12px / text_secondary color
```

Layout uses `QVBoxLayout` with spacing 12 inside the card, matching existing cards.

### Confirmation Dialog (QMessageBox replacement)

Phase 1 uses a custom `QDialog`, NOT the standard `QMessageBox`, because we need a scrollable candidate list.

Dimensions: `min-width=480px`, `max-width=720px`, `max-height=560px`. Centered on parent.

```
┌─ 发现 N 项 HIGH 档敏感内容 ─────────────────────┐
│                                                │
│ 本次扫描在 PDF 中检测到 N 项高置信度敏感内容    │
│ （身份证号 / 手机号）。请逐条确认是否脱敏；    │
│ 未确认的项将保持原样。                          │
│                                                │
│ [spacing 14]                                    │
│ 类型 · 原文预览                                │
│ ┌────────────────────────────────────────────┐ │
│ │ [✓] 身份证号  ·  110101********1234…        │ │
│ │ [✓] 手机号    ·  138****5678…              │ │
│ │ [✓] 身份证号  ·  320101********0021…        │ │
│ │ ...                                          │ │
│ └────────────────────────────────────────────┘ │
│   QScrollArea, vertical only                    │
│                                                │
│ [spacing 14]                                    │
│ [全部脱敏并保存]   [仅脱敏选中的 N 项]   [取消] │
│                                                │
└────────────────────────────────────────────────┘
```

- Each row: `QCheckBox` (default checked) + 2 `QLabel`s (entity_type, masked preview)
- Primary CTA `全部脱敏并保存`: accent button (filled `#0F6CBD`, white text)
- Secondary CTA `仅脱敏选中的 N 项`: outline button (border `#0F6CBD`, primary text)
- Cancel CTA `暂不脱敏（仅高亮）`: tertiary button (text-only, text_secondary color, hover → `hover` background)
- All CTAs: `min-height=32px`, `min-width=88px`, font `14px / Regular`
- Dialog buttons row: `QHBoxLayout`, right-aligned, spacing 8

### Status Bar PII Chip

Single inline `QLabel` in the existing `info_bar`. Object name `piiStatusChip`. Position: left-aligned within info_bar, separated from OCR progress text by a fixed 12px gap (`QHBoxLayout` spacing).

Chip rendering (depending on state):

| State | Foreground | Background | Text |
|-------|-----------|-----------|------|
| engine OFF | danger color | info_bar (default) | `识别引擎已停用` |
| scanning (queued) | text_secondary | info_bar (default) | `排队等待识别…` |
| scanning (text layer) | text_secondary | info_bar (default) | `扫描第 X / Y 页…` |
| scanning (OCR fall-back) | text_secondary | info_bar (default) | `扫描件识别中（第 X / Y 页）…` |
| scanning (applying) | text_secondary | info_bar (default) | `正在应用真脱敏…` |
| done with N > 0 | success color | info_bar (default) | `已识别 N 项敏感内容` |
| done with N == 0 | text_secondary | info_bar (default) | `扫描完成：未发现敏感内容` |

Chip has no background fill, no border, no margin — it is plain colored text inside info_bar. No chip "pill" frame is drawn this phase. (Status chips with pill chrome are deferred to Phase 7.)

### Progress Bar Wiring

Existing `self.progress` (`QProgressBar`) wired to the OCR/PIIScan worker `progress_signal` (already connected at `main.py:11134`). Phase 1 emits integer percent values. No new progress bar introduced.

---

## Interaction Contract

| Trigger | Surface | Behavior |
|---------|---------|----------|
| User opens a PDF | `MainWindow.open_pdf` → `_start_ocr_scan` | Existing OCR scan starts. PII scan is triggered AFTER `page_result_signal` first page emits, on the same `OCRWorker` thread (no new thread — keeps OPS-03 lazy-load clean). Status chip transitions to scanning state. |
| PII scan completes per page | `page_result_signal` extended with `pii_list` payload | Hits appended to `page_data[page_num]["pii"]`. Canvas redraws if page is current. |
| PII scan completes for whole doc | Worker `finished_signal` | Status chip → done state. If `require_confirmation=true` AND any HIGH hit → confirmation dialog opens modally. |
| User clicks primary CTA in confirmation dialog | Dialog `accept()` | All PII hits marked confirmed; dialog closes; status chip → success. Save PDF flow continues with `pii_list` appended to redaction loop. |
| User clicks secondary CTA | Dialog `accept()` with selected-only subset | Selected PII hits confirmed, others dropped from final redaction. |
| User clicks cancel CTA | Dialog `reject()` | No PII hits are redacted. Status chip → `已识别 N 项敏感内容` (still success; user can later manually trigger save which respects the toggle). |
| User toggles `engine_enabled` OFF in SettingsDialog | Dialog `accepted()` | Existing config persistence path. On next PDF open, status chip starts in OFF state. PII scan is NOT triggered. |
| User toggles `require_confirmation` ON | Dialog `accepted()` | Next PDF open that finds HIGH hits will show confirmation dialog. |
| User right-clicks PII rect on canvas | `mousePressEvent` | No-op (Phase 1 read-only). Debug log only if `DEBUG_MODE`. |

---

## State Coverage

| State | Surface | Behavior |
|-------|---------|----------|
| Engine OFF (initial) | Status chip | `识别引擎已停用` text only, danger foreground |
| Engine ON, idle (no PDF open) | Status chip | Empty (no chip text); chip widget hidden via `setVisible(False)` |
| Engine ON, PDF open, no candidates | Status chip + progress | Progress 100%; chip `扫描完成：未发现敏感内容` (text_secondary) |
| Engine ON, PDF open, candidates present, no confirmation | Status chip + progress | Progress 100%; chip `已识别 N 项敏感内容` (success) |
| Engine ON, PDF open, candidates present, confirmation ON | Status chip + dialog | Chip during scan; dialog blocks save until resolved |
| Engine ON, PDF open, scan cancelled mid-way | Status chip + progress | Existing `cancel_ocr_scan` flow; PII scan shares cancellation token; chip → `⏹️ 扫描已取消` (warning color, replaces in-flight stage copy) |
| Engine ON, PDF open, OCR fall-back (scanned PDF) | Status chip + progress | Chip shows `扫描件识别中（第 X / Y 页）…` while `collect_full_page_ocr_hits` runs |
| PDF open failure during PII init | Info bar | Error message per Copywriting contract; engine self-disables for current session |
| SettingsDialog open with engine toggled OFF | Toggle visual | Toggle shows unchecked; toggles 2 & 3 greyed out (existing `setEnabled(False)` style) |
| Confirmation dialog with N == 0 (defensive) | Dialog | Not opened; defensive guard |

No loading skeleton this phase — status chip text + existing `QProgressBar` already cover progress.

---

## Registry Safety

Not applicable — this is a PyQt6 desktop application with no third-party component registries. All UI primitives are PyQt6 built-ins. All icons come from `assets/branding/v38/` (existing project assets). All colors come from `theme.py` (existing project module).

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| n/a (PyQt6) | n/a | not applicable — no third-party UI registries involved |

If any future phase introduces an icon asset NOT in `assets/branding/v38/`, that asset must be added there first, and the safety gate must be re-run against the asset (file existence + readable SVG).

---

## Constraints Carried From Upstream (do not violate)

1. Lazy-load: `privacyguard.pii.*` modules import via `__getattr__` (matching `privacyguard/__init__.py:_LAZY_IMPORTS` pattern). No `import privacyguard.pii.engine` at module top-level anywhere outside `privacyguard.pii`.
2. Single config path: `pii_settings` lives in `config.json` consumed by `SimpleConfig`. Do NOT touch `privacyguard/utils/config.py::ConfigManager`.
3. Convergence: all shared logic goes into `privacyguard/`. No new OCR / PII / candidate-collection code in `main.py`.
4. Reverse-extraction verification (SAFE-02): the new reverse-extraction test uses `fitz.open(...).get_text()` (preferred over `pdftotext` per D-14).
5. Existing 79/79 test baseline (OPS-07): must pass after Phase 1 ships.

---

## UI Considerations

> Probed post-verification by ui-consideration-probe.cjs (Step 9.5 of /gsd-ui-phase).
> Shape-rooted UI **state** coverage for the Phase 1 surfaces. Empty-state and error-state
> **COPY** lives in `## Copywriting Contract` above — this section covers state coverage and
> REFERENCES those rows rather than restating the copy (de-dup).

**Applicable state considerations resolved:** 20 covered · 2 backstop · 0 unresolved.

### E1 — SettingsDialog "5 隐私识别" section card

| Category | Status | Resolution / Reason |
|----------|--------|---------------------|
| empty | ✅ covered | Settings card is a static form — toggles always render with their current `pii_settings` values; the read-only `扫描范围（只读）：身份证号 / 手机号` label is always present. No empty state. |
| loading | ✅ covered | SettingsDialog renders synchronously from `pii_settings` already loaded at MainWindow init; no async loading on this card. The existing MainWindow splash/progress path does not apply here. |
| error | ✅ covered | Existing config persistence error path (the SettingsDialog `accepted()` path that writes back to `config.json`) applies — Phase 1 does not introduce a new error surface. If `pii_settings` schema is malformed, the existing validator surfaces the error toast. |
| populated | ✅ covered | Header (`5. 隐私识别`) + 3 `QCheckBox` toggles + read-only `扫描范围` label render in normal happy-path per `## Visuals §SettingsDialog` layout diagram. |
| partial | ✅ covered | When toggle 1 (`启用隐私识别引擎`) is OFF, toggles 2 and 3 greyed out via existing `setEnabled(False)` style (referenced in layout diagram lines 187–192). |
| overflow | 🧪 backstop | Card sits inside existing SettingsDialog scroll area which already handles vertical overflow; held-out visual test at 720p confirms toggles remain reachable. { statement: "SettingsDialog scroll area handles overflow; visual test confirms reachability at 720p", verification: backstop } |
| zero-one-many | ✅ covered | Static form — the 3 toggles are fixed and the read-only label is fixed text; zero/one/many does not apply. |
| long-text | 🧪 backstop | Toggle labels and tooltips are bounded by the locked Copywriting rows; held-out visual test confirms no label clipping at 720p / 100% DPI. { statement: "Toggle labels and tooltips remain readable at 720p", verification: backstop } |

### E2 — PII confirmation QDialog

| Category | Status | Resolution / Reason |
|----------|--------|---------------------|
| empty | ✅ covered | Dialog does NOT open when `N == 0` — defensive guard documented in `## State Coverage` row "Confirmation dialog with N == 0 (defensive)". The dialog is only shown when `require_confirmation=true` AND HIGH hits are present. |
| loading | 🧪 backstop | Dialog appears AFTER scan completion (status chip → done state first, then dialog opens modally); no in-dialog spinner needed. Held-out visual test confirms the dialog opens synchronously post-scan with no perceived lag. { statement: "Dialog opens after scan completes with no perceived lag", verification: backstop } |
| error | ✅ covered | Engine init failure handled per Copywriting `§Error state (PDF open failure post-PII)` — engine self-disables for the current session. The confirmation dialog is unreachable when the engine has self-disabled, so no in-dialog error path is needed. |
| populated | ✅ covered | `QScrollArea` of checkbox rows + 3-button row render per `## Visuals §Confirmation Dialog` ASCII mockup (lines 207–227). Primary/secondary/cancel CTAs right-aligned with 8px spacing. |
| partial | ✅ covered | User can uncheck individual rows; secondary CTA copy `仅脱敏选中的 N 项` documents the partial-selection behavior. Per Copywriting row "Confirmation dialog row format" each row's `QCheckBox` defaults to checked. |
| overflow | ✅ covered | `QScrollArea` with vertical-only scroll specified in layout diagram; `max-height=560px` and `min-width=480px / max-width=720px` bounds ensure the dialog never overflows the parent viewport. |
| zero-one-many | ✅ covered | Copy uses plural `N 项` form consistently (Copywriting rows "Confirmation dialog title" / "body" / "secondary CTA"); the `N == 0` case is prevented by the defensive guard. |
| long-text | ✅ covered | Masked preview already truncates with `…` per Copywriting row "Confirmation dialog row format"; entity_type labels are bounded by the 2 supported Phase 1 types. |

### E3 — Status bar piiStatusChip

| Category | Status | Resolution / Reason |
|----------|--------|---------------------|
| overflow | ✅ covered | Chip is plain colored text inside existing `info_bar` `QHBoxLayout` — truncates at parent layout boundary (existing info_bar behavior). No pill chrome added per `## Visuals §Status Bar PII Chip` line 252 ("No chip 'pill' frame is drawn this phase"). |
| long-text | ✅ covered | Scan-stage copy bounded by `扫描第 X / Y 页…` format where X/Y are integers; `Y` ≤ page count bounded by Phase 1 success criteria #4 ("UI stays responsive while scanning a 500-page PDF"). Worst-case string `扫描第 500 / 500 页…` is well within info_bar width at default DPI. |

### E4 — SinglePageCanvas PII rendering

| Category | Status | Resolution / Reason |
|----------|--------|---------------------|
| overflow | ✅ covered | PII rects render via the new third paint loop in `paintEvent` per `## Visuals §PII Rect Rendering` — many rects simply draw more rects, no layout overflow concept on a `QWidget` canvas. Existing `pdf_to_screen` hit-area math handles zoom-level scaling. |
| long-text | ✅ covered | PII label text is fixed ASCII `ID` or `PHONE` (per `## Visuals §PII Rect Rendering` line 170); no long-text risk on the label badge. |

---

**Probe provenance:** ui-consideration-probe.cjs @ /home/rende/.claude/gsd-core/bin/lib/ui-consideration-probe.cjs · elements heredoc @ /tmp/ui-probe-elements-xz6WLq.json · 2026-08-10.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS (N/A — PyQt6; explicit not-applicable note required)

**Approval:** approved 2026-08-10 (gsd-ui-checker: 5/6 PASS + 1 non-blocking FLAG on Spacing; ui-consideration probe: 20 covered / 2 backstop / 0 unresolved)