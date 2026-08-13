---
phase: 03-word
plan: 04
subsystem: word-pii-save-packaging
tags: [python-docx, reverse-extraction, mask-override, pyinstaller, hiddenimports]
requires:
  - phase: 03-word
    provides: word_adapter 三函数、worker PII 命中、Word 预览合并与 pii-highlight
provides:
  - Word 单文档保存路径接入 PII 真脱敏
  - 文档级 partial/blackout override 与新文档生命周期复位
  - Windows/macOS PyInstaller word_adapter hiddenimports parity
  - Word reverse-extraction 与 _save_word AST 守卫测试
affects: [phase-03-word, phase-07-review-ux, phase-08-audit-packaging]
actuals:
  tokens: 2922
  tasks: 4
  commits: 5
tech-stack:
  added: []
  patterns: ["先执行既有 Word 替换，再基于当前段文本定位 PII，避免掩码长度变化造成偏移错位", "调用方持有 python-docx Document，word_adapter 保持无 docx import", "Windows/macOS spec 显式 hiddenimports parity"]
key-files:
  created:
    - tests/unit/test_word_pii_redaction.py
  modified:
    - main.py
    - packaging/windows/config/PrivacyGuard_windows.spec
    - packaging/macos/config/PrivacyGuard.spec
    - packaging/macos/scripts/build_complete.sh
key-decisions:
  - "Word 保存默认使用 partial 模式；文档级 override 为 blackout 时覆盖默认模式，且状态独立存储在 MainWindow 实例字段。"
  - "PII 在既有规则、手动、OCR 替换之后按当前段落文本重新定位；这是避免 replacement 长度变化破坏 char offset 的必要顺序。"
  - "macOS 构建脚本采用注释与 macOS spec 显式条目双重 parity 证据；实际 hiddenimport 列表位于 PrivacyGuard.spec。"
requirements-completed: [FMT-02, MASK-02, OPS-04]
coverage:
  - id: D1
    description: "Word 段落和表格段落保存时执行 PII partial/blackout 真脱敏"
    requirement: FMT-02
    verification:
      - kind: integration
        ref: "tests/unit/test_word_pii_redaction.py#TestWordPiiRedaction"
        status: pass
    human_judgment: false
  - id: D2
    description: "保存产物 reverse-extraction 不含原始身份证/手机号，并保留 partial mask 或 [已脱敏]"
    requirement: FMT-02
    verification:
      - kind: integration
        ref: "python -m unittest tests.unit.test_word_pii_redaction -v"
        status: pass
    human_judgment: false
  - id: D3
    description: "文档级 override 与新 Word 文档生命周期复位"
    requirement: MASK-02
    verification:
      - kind: unit
        ref: "main.py AST/source checks plus Word replacement regression suite"
        status: pass
    human_judgment: false
  - id: D4
    description: "Windows/macOS PyInstaller 配置显式包含 privacyguard.pii.word_adapter"
    requirement: OPS-04
    verification:
      - kind: other
        ref: "python -m py_compile packaging/windows/config/PrivacyGuard_windows.spec packaging/macos/config/PrivacyGuard.spec; bash -n packaging/macos/scripts/build_complete.sh"
        status: pass
    human_judgment: false
  - id: D5
    description: "最终冻结包启动与真实 Word UI 打开/保存仍需平台验收"
    verification: []
    human_judgment: true
    rationale: "当前环境未执行 Windows/macOS frozen build 或真实桌面 UI 操作；静态配置与单元测试不能替代平台验收。"
duration: 28min
completed: 2026-08-11
status: complete
---

# Phase 3 Plan 4: Word 保存真脱敏与跨平台打包 Summary

**Word .docx 保存路径现在执行 PII 真脱敏、支持文档级全遮蔽 override，并通过 Windows/macOS PyInstaller hiddenimports 与 reverse-extraction 守卫。**

## Performance

- **Duration:** 28 min（含验证与一次偏移顺序修复）
- **Started:** 2026-08-11T14:23:38Z
- **Completed:** 2026-08-11T14:51:44Z
- **Tasks:** 4
- **Files modified:** 5（其中 1 个新测试文件）

## Accomplishments

- `_save_word` 在段落和表格 cell 段落中调用 `locate_pii_hits_in_paragraph` 与 `apply_pii_replacements_to_docx`；默认 partial，override 为 blackout 时写入 `[已脱敏]`。
- `MainWindow` 新增独立 `_word_mask_override_this_doc` 字段；现有 toolbar toggle 同步写入 PDF 与 Word 状态，打开新 Word 文档时复位。
- Windows spec、macOS spec 与 macOS 构建脚本均记录 `privacyguard.pii.word_adapter` parity；cp30 的 security 模块收集链未被改动。
- 新增 8 个 Word reverse-extraction / AST 测试，验证原敏感字符串不可提取、partial mask、blackout、段落样式和生产接入点。

## Task Commits

1. **Task 1: `_save_word` 接入 PII 真脱敏** - `7408fb6` (feat)
2. **Task 2: 文档级 override 字段、toggle 双路径与生命周期复位** - `a264d2c` (feat)
3. **Task 3: Windows/macOS hiddenimports parity** - `6c7cc54` (chore)
4. **Task 4: reverse-extraction 与 AST 守卫测试** - `4998758` (test)

**补充修复提交：** `4b67678` (fix) — 先执行既有替换，再按当前段文本重新定位 PII，修复 partial mask 长度变化可能造成的偏移错位。

## Files Created/Modified

- `main.py` - 保存路径、文档级 override 初始化/写入/复位。
- `packaging/windows/config/PrivacyGuard_windows.spec` - 显式加入 Word adapter hiddenimport。
- `packaging/macos/config/PrivacyGuard.spec` - 显式加入 Word adapter hiddenimport。
- `packaging/macos/scripts/build_complete.sh` - 标记 macOS spec 与 Windows 的 parity 约束。
- `tests/unit/test_word_pii_redaction.py` - 端到端 docx reverse-extraction 与 `_save_word` AST 测试。

## Decisions Made

- Word 默认 partial 模式与 PII adapter 的 `mask_for_entity` 分派一致；toolbar 的 checked 状态统一映射为 blackout。
- PII 定位必须基于执行既有替换后的当前段文本；不能复用原始 `source_text` 偏移。
- `word_adapter.py` 继续不 import python-docx，由 `_save_word` 持有 Document 句柄并注入 adapter。
- macOS 的真实 hiddenimports 清单位于 `packaging/macos/config/PrivacyGuard.spec`；构建脚本保留 parity 注释而不伪造不存在的数组。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 修复 PII 与既有替换顺序导致的偏移错位**
- **Found during:** Task 1（`_save_word` 接入）
- **Issue:** partial mask 可能改变字符串长度；若先执行 PII，再按原始偏移执行规则、手动或 OCR 替换，后续区间会错位，导致错误替换或漏替换。
- **Fix:** 段落与表格 cell 均先执行既有替换，再对当前 `para.text` 调用 `locate_pii_hits_in_paragraph`，最后调用 adapter。
- **Files modified:** `main.py`
- **Verification:** 64 个 Word/adapter/replacement 测试通过；完整 `tests/unit` 336/336 通过。
- **Committed in:** `4b67678`

**Total deviations:** 1 auto-fixed（Rule 1: 1）
**Impact on plan:** 必要的正确性修复；未扩大架构范围，且强化了 SAFE-02 真脱敏链路。

## Issues Encountered

- GitHub code search query因 API 查询语法不兼容返回 HTTP 422；未引入外部代码，改用现有仓库范本与 python-docx 官方文档完成实现核对。
- 运行环境中 `python3` 不是可用命令，使用项目现有等价命令 `python` 完成全部验证。
- 未在当前环境执行 Windows/macOS frozen build；已通过 spec Python 语法、macOS shell 语法、hiddenimports parity 与懒加载回归，平台实际打包保留给人工验收。

## User Setup Required

None - no external service configuration required.

## Known Stubs

None in files created or modified by this plan. Existing UI placeholder branches in `main.py` are unrelated to this plan and were not changed.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: data-redaction | `main.py` | `_save_word` writes masked text into the exported DOCX; reverse-extraction tests verify original PII is not present. |
| threat_flag: packaging-import | `packaging/windows/config/PrivacyGuard_windows.spec` / `packaging/macos/config/PrivacyGuard.spec` | New lazy-loaded adapter is an explicit frozen-package import surface; both platforms list it. |

## Verification

- `python -m unittest tests.unit.test_word_pii_redaction tests.unit.test_word_pii_adapter tests.unit.test_word_worker_pii tests.unit.test_word_preview_highlight tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_convergence tests.unit.test_package_imports -v` — **108/108 PASS**.
- `python -m unittest discover -s tests/unit -q` — **336/336 PASS**.
- `python -m compileall -q main.py privacyguard tests packaging` — PASS.
- `python -m py_compile packaging/windows/config/PrivacyGuard_windows.spec packaging/macos/config/PrivacyGuard.spec` — PASS.
- `bash -n packaging/macos/scripts/build_complete.sh` — PASS.
- Static parity check found `privacyguard.pii.word_adapter` in Windows spec, macOS spec, and macOS build script — PASS.
- `tests.unit.test_package_imports` — **10/10 PASS**, including lazy-load and on-demand adapter checks.

## Self-Check: PASSED

- SUMMARY 文件存在。
- Task commits `7408fb6`, `a264d2c`, `6c7cc54`, `4b67678`, `4998758` 均存在于 git history。
- 336/336 完整单元测试通过。

## Next Phase Readiness

- Phase 3 Word production slice is code-complete and regression-green.
- Remaining manual gate: build and launch frozen artifacts on Windows and macOS, then open a real `.docx`, inspect both preview panes, toggle `本文件全遮蔽`, save, and verify the exported file.
- Phase 7 can build the full candidate review UI on top of `word_data[key]['pii']` and the existing `pii-highlight` preview source.

---
*Phase: 03-word*
*Completed: 2026-08-11*
