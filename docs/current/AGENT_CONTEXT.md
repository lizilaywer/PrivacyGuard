# Agent Context — 背景与历史（从 AGENTS.md 外移）

本文件承载根 AGENTS.md 外移的背景区块：完整能力清单、运行时数据结构、
检查点历史。按需查阅；关键安全约束仍保留在根 AGENTS.md。

---

## v40.2.5 增量约束（2026-10-24）

- 扫描修改过的 PDF 必须使用当前 doc 的不可变字节快照，禁止回读旧磁盘页序。
- 提取/截去不能只依赖 clip 隐藏原始流，复制入口为 `utils/pdf_regions.py`；截去通过 `crop_page_hits` 保留遮罩。
- 冻结配置/日志路径统一由 `utils/app_paths.py` 决定，禁止写 .app 或打包构建机 config.json。
- OCR 三模型走显式本地路径；模型失败不得返回“成功无命中”。
- macOS 便携入口 `build_portable.sh` + `check_macos_bundle.py`，兼容性以全包 Mach-O 为准。
- 现有 Word 遍历不覆盖所有 OOXML 特殊部件，PDF 导出不等于附件/元数据净化；详见 `RELEASE_AUDIT_20261024.md`。

## Current Active Capabilities (full detail)

- PDF redaction:
  - text PDF search via PyMuPDF
  - image PDF OCR via RapidOCR
  - mixed PDF redaction via text-layer search + embedded image-block OCR
  - manual rectangle redaction
  - manual-box OCR recognize + optional whole-doc masking (cp65: region text via text layer
    or RapidOCR clip OCR, `ManualRegionRedactDialog`, targeted scan reusing OCRWorker,
    hits appended to manual lists with >50% overlap dedup)
  - page view (cp67 “页面” toggle; cp68 replaces the removed dual-page mode): multi-page grid
    overview with lazy thumbnail render + LRU cache (60 pages) and two-phase rendering
    (fast scaled transition frames + 260ms debounced HQ re-render, page aspect cache);
    Ctrl+wheel adjusts columns with release-to-cross boundary damping both ways
    (0.45s gesture gap; single-page zoom-out below ZOOM_MIN enters the grid at 2 columns,
    grid zoom-in past 1 column returns to single page); click select / Ctrl multi-select /
    Shift range-select (anchor semantics, Ctrl+Shift unions) / double-click locate;
    left line-icon sidebar rotates (mask coords follow via `transform_hit_rect_for_rotation`),
    inserts blank page or external file (PDF/image, cp111) after selection, deletes selected
    pages (confirm, keep >=1) with `shift_page_data_for_insert/delete` reindexing; manual box
    redaction works inside the grid;
    fit-page (⛶) returns to single-page view from any view (deferred one frame after exit);
    ops set `_pdf_modified` so export uses `doc.tobytes()`.
    Rotated-page coordinate rule: canvases/page_data use display coords; save_pdf multiplies
    `derotation_matrix`; text hits / embedded image bboxes are converted with `rotation_matrix`
  - title-anchored person-name detection (称谓人名, cp_person_name v40.2.0):
    `privacyguard/ocr/person_name.py` pure-function engine, zero new deps; 34 builtin law
    titles (被告人/犯罪嫌疑人/原告/辩护人/证人/被害人/被告/上诉人/被上诉人/申请人/
    被申请人/异议人/答辩人/被答辩人 + legal extensions), longest-first alternation;
    forward anchor regex consumes only 称谓+分隔 (half/full colon + whitespace tolerated),
    person name asserted via lookahead (rejected candidates don't swallow later anchors —
    "被告人的辩护人王五" hits via nested 辩护人 anchor); candidate split = connector-char
    cut (李四及证人→李四) + legal-verb tail trim (张三到庭→张三, 34-term table) +
    not-name prefix veto (当庭/如实/认罪…) + first-char stop set (知被人提证由在将让就
    事同友邻亲哥姐弟妹母父妻夫战认 — all non-surnames); reverse structure
    "姓名+作为/担任/系+称谓" (陈绕奇作为保证人→陈绕奇) with leading-relation-word trim
    (同事陈绕奇→陈绕奇); discover-once-mask-page-wide semantics: text layer via
    search_for(name) all occurrences, OCR via block-level two-pass (collect names from
    all lines, then re-find as exact patterns), Word via collect-pass + per-item finditer;
    hits carry rule-name override "称谓人名" (content-based classify would miss — name
    substring has no title prefix); rule disabled by default = engine never invoked
    (zero overhead, user decision); titles extensible via config
    `redaction.person_name_titles` (empty = builtin set; pattern regenerated+synced into
    config.json at startup via `_ensure_preset_rule`); real 16-page litigation dossier
    measured 3/3 names 100% accuracy zero false positives — jieba/NER upgrade path
    intentionally NOT taken
  - seal detection (印章, `__SEAL_DETECTION__`): dual-pass CLOSE (3 ∪ round(9×scan_scale)) for broken rings,
    max_radius_pt=150, disc_fill strong signal; validated on real litigation PDF
  - signature+fingerprint detection (签名手印, `__SIGNATURE_DETECTION__`): fingerprint-anchored
    (red/pink primary, dark conservative), morphological filters, compact mask expansion 15%/15%/10%;
    cp69 dark-path hard gates: warm-color (ridge pixels mean(R)-mean(B)>=10 and R-G>=3, rejects
    neutral-gray printed chars) + holes threshold 12
- PDF encryption on export (cp72): lock toolbar button left of 智能脱敏 (PDF/image modes only),
    `EncryptSettingsDialog` single dialog with open (user) + edit (owner) passwords, written as
    AES-256 via `build_encrypt_save_kwargs` merged into save_pdf kwargs; session-only passwords,
    reset in `_cleanup_before_open`
- open encrypted PDF/Word (cp113): `detect_pdf_password_state` (helpers_pdf) returns
    `{needs_user_pw, has_owner_restriction, permissions}`; encrypted PDF opens a
    `PasswordOpenDialog` (3 actions: open=keep password / remove=export unencrypted /
    change=re-open EncryptSettingsDialog) with retry-on-wrong-password; owner-restriction
    (openable but perms restricted) also prompts; authenticated password flows into the same
    `pdf_open_password`/`pdf_edit_password` shared with the cp72 lock button, so export uses
    `build_encrypt_save_kwargs` uniformly. Encrypted Word: `is_encrypted_docx` (OLE2 magic
    D0 CF 11 E0) gates `decrypt_docx_to_temp` (msoffcrypto lazy-import, writes to a
    temp_manager-tracked temp file keeping the original basename so preview/save read
    consistently; `converted_temp_file` cleanup reused); `PasswordOpenDialog` "change password"
    button disabled (python-docx cannot re-encrypt); `word_open_password` records the entered
    password only; info bar notes "export without password"
- cp114 encrypted PDF redaction fix: `_pdf_auth_password` field decoupled from export encryption
  settings — stores the password verified at open time for disk re-read authentication (OCR /
  save_pdf), so "remove password" action (clears `pdf_open_password` for unencrypted export)
  still allows OCR/save to re-authenticate the still-encrypted source file. `OCRWorker` gains
  `pdf_open_password` param, authenticates after `fitz.open` when `doc.needs_pass`; save_pdf
  both branches (tobytes stream / disk reopen) guard `needs_pass` + authenticate; insert-file
  prompts `QInputDialog` password for encrypted external PDFs. main.py `OCRWorker` wrapper class
  forwards `pdf_open_password` to `super().__init__()`. `_ensure_edit_permission()` detects
  missing `PDF_PERM_MODIFY` permission before redact/save and prompts `QInputDialog` for owner
  password; on success upgrades `_pdf_auth_password`; wired into `start_ocr` /
  `_start_targeted_mask_scan` / `save_pdf`
- full-document search sidebar (cp81/82): magnifier toolbar button toggles right panel (320px,
    works beside single-page / page-view / Word views via content_row layout);
    `DocSearchWorker` searches a `doc.tobytes()` snapshot (page order matches rotate/delete/
    watermark state) — text-layer pages direct search, scanned pages RapidOCR with session
    per-page cache `{'text','spans'}`; Word searched synchronously from block texts;
    hits carry rects (text-layer `search_for` word-level, OCR line-level via spans lookup);
    clicking a result jumps to the page and flashes a translucent yellow highlight
    (`SinglePageCanvas.flash_rect`, scrolls to hit, 2.4s fade); Word scrolls by data-key + flash
- undo/redo (cp83): unified snapshot stack (depth 20) — pure fns `snapshot_page_data`/
    `restore_page_data` (QRectF↔tuple decoupled) + `push_undo_snapshot`; capture hooks at
    10 sites (mask add/remove incl. canvas right-click now emitting rect_removed; rotate/
    insert/delete pages with structural doc-bytes snapshot restored via fitz.open(stream));
    `_restoring_snapshot` re-entry guard; baseline on open, stacks cleared on new doc;
    btn_undo/btn_redo in edit group + Ctrl+Z / Ctrl+Y shortcuts; PDF/image modes only
- toolbar overflow architecture (cp84-86): dual stretch layout
    (left groups | stretch | zoom+nav | stretch | utility) keeps utility right-aligned and
    never clipped; forced-narrow degradation when content exceeds screen width
    (`_toolbar_forced_narrow`, reuses cp39/40 overflow menu, auto-release on wider screen);
    resize-to-fit fallback after setMinimumWidth; zoom/nav equal-width coupling removed
- preset rules (cp70): 12 total — idcard/phone/date/email/bankcard(Luhn) + USCC(mod31-3)/
    plate/landline (enabled) + passport/HK-Macao-TW permit/VIN(check digit)/IPv4 (disabled);
    `verify_hit_by_pattern` post-match checksum dispatch mounted symmetrically in
    text_pdf/mixed_pdf/word_worker; rule definitions synced across DEFAULT_RULES/config.json/
    DEFAULT_CONFIG; cp71 `apply_box_adjust_to_hit` applies box_adjust_ratio to text-layer hits
- Word redaction:
  - intelligent scan
  - manual precise/global redaction
  - multi-field replacement rules (`exact` / `regex`)
  - keyword inline replacement (`find|replace` lines; priority: word rules > inline > unified text,
    via `resolve_word_ocr_replacements` applied before every merge in preview and save)
  - batch replace for `.docx` / `.doc`
- Word dual preview:
  - left: original preview with OCR/manual highlights
  - right: merged replaced preview (`rule > manual > ocr`)
  - highlight filtering by source (rule / manual / ocr) via toolbar dropdown
- Context-aware advanced settings (`SettingsDialog.doc_context`): PDF/image hides the Word-replace
  card; Word hides precision & OCR-box sections and the manual-box replace toggle; keyword list
  stays visible in all contexts (Word scan also matches custom keywords)
- Drag & drop open
- Fixed default window 1300×900 (screen-clamped + centered, geometry not persisted)
- Windows and macOS packaging scripts

---

## Key Runtime Data Structures

### PDF state

- `self.page_data[page_num] = {"ocr": [...], "manual": [...]}`

### Word state

- `self.word_data[key] = {"text": ..., "ocr": [...], "manual": [...], ...}`
- `self.word_replace_rules` stores session-level multi-field replacement rules

### Word preview model

The active path is:

1. DOCX -> HTML via `mammoth`
2. HTML tagged with `data-key`
3. Left panel updates by block with original-text highlight fragments
4. Right panel updates by block with merged replacement fragments
5. DOM is updated via keyed JavaScript patching instead of always doing full `setHtml()`

Important:

- compare mode may start with the right panel hidden or blank
- `cp20` added per-panel loaded-source tracking
- `cp27` restricted incremental DOM patching to actual word blocks and prevents highlight-node corruption
- when compare mode becomes active after an empty state, the right panel must reload the full document before applying partial updates

---

## Current Checkpoints

- `20260309_runtime_remediation_cp18_verified`
- `20260309_word_compare_bugfix_cp20_verified`
- `20260309_mixed_pdf_ocr_cp23_verified`
- `20260309_release_sync_cp25_verified`
- `20260310_word_preview_highlight_cp27_verified`
- `20260310_release_sync_cp29_verified`
- `20260311_pyinstaller_packaging_fix_cp30_verified`
- `v38_ui_refactor_cp31_20260313_140645`
- `seal_luhn_mask_fix_cp51_56_verified`（v37.7.19 印章检测 + Luhn 校验）
- `stability_fix_cp58_verified`（v37.7.19 全面稳定修复 + 31 个新增测试）
- `cp59` 公章双根因修复（v37.8.0：max_radius 150 + 双通道 CLOSE + disc_fill）
- `cp60` 签名手印检测新功能（v37.8.0）
- `cp61` UI 精致化 + 高亮筛选 + v37.8.0 定版
- `cp62` 高级设置按文档类型动态显示（v37.8.1）
- `cp63` Word 关键词行内替换三级优先级（v37.8.1）
- `cp64` 手动框选替换开关立即生效 + v37.8.1 定版（备份 `backups/cp62_64_settings_word_inline_pre/`）
- `cp65` 手动框选 OCR 识别 + 可选全文遮罩（v37.8.2）
- `cp66` 取消交互/取消按钮 UI/工具栏对调 + v37.8.2 定版（备份 `backups/cp65_66_manual_region_pre/`）
- `cp67` 页面视图多页网格 + 页面旋转/插入/删除 + 旋转页坐标系适配 + v37.8.3 定版（备份 `backups/cp67_multi_page_view_pre/`）
- `cp68` 页面视图交互与性能打磨（双页按钮移除/两段式渲染/双向手势阻尼/⛶ 跨视图/Shift 范围选）+ v37.8.4 定版（备份 `backups/cp68_view_interaction_pre/`）
- `cp69` 去水印页面视图刷新 + 替换文字宽度适配 + 签名手印暖色门控（R-B≥10 且 R-G≥3，holes 8→12，排除楷体/仿宋印刷字误报）
- `cp70` 高级设置新增 7 条预设规则（USCC mod31-3/VIN 第 9 位校验，verify_hit_by_pattern 三链路对称挂载；备份 `backups/cp70_extended_rules_pre/`）
- `cp71` box_adjust_ratio 对文本层 PDF 生效（apply_box_adjust_to_hit 中心缩放）；OCR 参数生效性全链路审查
- `cp72` PDF 加密（EncryptSettingsDialog 双密码/锁图标按钮/导出 AES-256/build_encrypt_save_kwargs；备份 `backups/cp72_encrypt_pre/`）
- `cp73` 工具栏按钮重合修复（_enforce_toolbar_min_width 动态最小窗口；min_width 900→1120）
- `cp74` 手动框选弹窗增强（去空白/复制小按钮；取消=整个行为取消不遮罩）+ v37.8.5 定版
- `cp75` 页面视图遮罩色切换实时生效（overlay 刷新前同步 mask_color）
- `cp76` 页面视图首次进入零白屏（分帧渲染队列 _grid_render_queue/_process_grid_render_queue，每帧一页；退出/重建守卫清队）+ v37.8.6 定版
- `cp77` 主页卡内突兀方块修复（scroll_style 加 QScrollArea 选择器阻断无选择器样式向后代传播；mainContainer 显式接管卡外 scroll_area 底色）
- `cp78` Windows 标题栏 DWM 配色（_apply_windows_titlebar_color，DWMWA_CAPTION_COLOR=35 → scroll_area 色；仅 Win11 22000+，失败静默）
- `cp79` 全局默认字体（QApplication.setFont，Segoe UI Variable/Segoe UI/雅黑 UI 回退栈 10pt）
- `cp80` 三平台兼容（字体 win32 守卫，macOS 保持系统字体；FONT_FAMILY/PREVIEW_FONT_STACK 补苹方；画布替换文字字体回退栈）+ v37.8.7 定版
- `cp81` 全文搜索侧栏（btn_search 放大镜按钮/右侧 320px 面板/DocSearchWorker tobytes 快照+OCR 会话缓存/Word 同步搜/content_row 布局重构；备份 `backups/cp81_doc_search_pre/`）
- `cp82` 搜索命中高亮定位（hit_signal 携 rect：文字层 search_for 词级/OCR spans 行级；SinglePageCanvas.flash_rect 闪烁层 + 滚动到命中行 + 2.4s 淡出）+ v37.8.8 定版
- `cp83` 撤销/恢复（状态快照栈深 20：纯函数 snapshot/restore/push + 方法簇；遮罩 5 处+结构 3 处接入，structural 存 doc.tobytes 可还原删页；btn_undo/redo + Ctrl+Z/Y；备份 `backups/cp83_undo_redo_pre/`）
- `cp84-86` 工具栏拥挤/重叠根治（cp86 根因：单 stretch 留白堆中部、右侧被顶出窗口 → 双 stretch 留白均分 utility 贴右；cp85 溢出强制 narrow 降档+resize 兜底；cp84 edit 组语义分组；删 zoom/nav 强制同宽）+ v37.8.9 定版
- `cp87` 脱敏报告（privacyguard/report.py 纯函数；命中携 rule 四处+rule_name_pairs 链；save_pdf 弹窗 setDetailedText+导出报告；D3 run_regression 脚本/discover/tests 补 __init__.py/陈旧测试归档 tests/legacy）
- `cp88` 会话恢复（privacyguard/session_store.py 指纹匹配/轻重分离 JSON+pdfsnap；_capture_undo_state 钩 5s 节流，结构变更立即落盘；_open_pdf_file 提示恢复；备份 cp88_session_restore_pre）
- `cp89` 工程健康（仓库审计无未跟踪赘物；test_toolbar_layout 锁 cp84-86；RELEASE_CHECKLIST.md 定版六步含打 tag）
- `cp90` 清理使用痕迹（temp_manager pgud_ 前缀+残留识别；trace_cleaner.py 白名单 realpath 硬约束+pending 往返纯函数；TraceCleanDialog 四类痕迹；__main__ 启动早期清 WebEngine pending；备份 cp90_trace_clean_pre）+ v37.8.10 定版
- `cp111` 页面视图插入文件（PDF/图片插入选中页后；page_insert_file.svg；_insert_pdf_pages_at/_insert_image_as_page_at；结构快照+网格刷新）
- `cp112` 导出弹窗打开文档按钮（helpers_ui.open_path_in_system 跨平台；PDF/Word 弹窗按钮顺序：导出报告 | 打开文档 | OK）
- `cp113` 加密文档打开与密码管理（PasswordOpenDialog 三动作；detect_pdf_password_state；word_crypto 解密；_pdf_auth_password 与锁按钮共享；msoffcrypto-tool 依赖）
- `cp114` 加密 PDF 脱敏修复（_pdf_auth_password 磁盘重读认证与导出加密解耦；OCRWorker pdf_open_password 参数 + authenticate；save_pdf 两分支守卫；插入加密 PDF 弹密码框；OCRWorker 包装层转发参数；_ensure_edit_permission 编辑权限弹窗接入三处入口）

Rollback references:

- `rollback_journal.md`
- `ROLLBACK_GUIDE.md`
- `restore_checkpoint.sh`
