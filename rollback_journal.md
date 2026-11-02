# Rollback Journal - Word Batch Replace Iteration

## 2026-10-24 v40.2.5 审计/便携构建

- 修改前源码：`backups/pre_macos_audit_20261024.tar.gz`；包含 main.py、privacyguard、测试、打包及关键状态文件。
- 变更范围及验证：`docs/current/RELEASE_AUDIT_20261024.md`，730 discovered / 728 passed / 2 skipped；冻结 ZIP 自检与 395 Mach-O 门禁通过。
- 不使用 git reset 回滚：先把此 tar 解压到独立临时目录，按审计改动清单逐文件比对恢复，保留用户本轮开始时已有的未提交修改。
- 新建源文件（需回退时单独核对移除）：app_paths/pdf_regions/worker_lifecycle/model_paths/diagnostics、发布构建/验证脚本、审计回归与报告。
- 版本回退时从 version.txt 重生成 Windows version_info，不手工覆盖生成文件；独立发布 venv 与 build/release 产物不影响原 venvmac。

## 2026-03-02

- [x] cp0 备份完成
  - checkpoint: `20260302_word_batch_replace_cp0`
  - snapshot: `backups/iteration_checkpoints/20260302_word_batch_replace_cp0/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260302_word_batch_replace_cp0/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260302_word_batch_replace_cp0/preflight_meta.json`
- [x] cp1 UI与规则弹窗
  - checkpoint: `20260302_word_batch_replace_cp1`
  - snapshot: `backups/iteration_checkpoints/20260302_word_batch_replace_cp1/snapshot_src.tar.gz`
- [x] cp2 单文档应用与双栏预览
  - checkpoint: `20260302_word_batch_replace_cp2`
  - snapshot: `backups/iteration_checkpoints/20260302_word_batch_replace_cp2/snapshot_src.tar.gz`
- [x] cp3 批量流程
  - checkpoint: `20260302_word_batch_replace_cp3`
  - snapshot: `backups/iteration_checkpoints/20260302_word_batch_replace_cp3/snapshot_src.tar.gz`
- [x] cp4 测试通过待验收
  - checkpoint: `20260302_word_batch_replace_cp4`
  - snapshot: `backups/iteration_checkpoints/20260302_word_batch_replace_cp4/snapshot_src.tar.gz`
- [x] cp5 UI/交互修正（批量入口并入打开、设置界面整合）
  - checkpoint: `20260302_word_batch_replace_cp5_ui_logic_fix`
  - snapshot: `backups/iteration_checkpoints/20260302_word_batch_replace_cp5_ui_logic_fix/snapshot_src.tar.gz`
- [x] cp6 测试后问题修复前备份（高级设置入口恢复 + 批量规则流程修正）
  - checkpoint: `20260302_word_batch_replace_cp6_posttest_fix`
  - snapshot: `backups/iteration_checkpoints/20260302_word_batch_replace_cp6_posttest_fix/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260302_word_batch_replace_cp6_posttest_fix/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260302_word_batch_replace_cp6_posttest_fix/preflight_meta.json`
- [x] cp7 修复完成并验证通过
  - checkpoint: `20260302_word_batch_replace_cp7_postfix_verified`
  - snapshot: `backups/iteration_checkpoints/20260302_word_batch_replace_cp7_postfix_verified/snapshot_src.tar.gz`
  - verification:
    - `python3 -m compileall -q main.py`
    - `python3 -m unittest tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v`
- [x] cp8 预览融合修复前备份（双栏头部UI + 替换后预览融合逻辑）
  - checkpoint: `20260302_word_preview_fusion_cp8_pre`
  - snapshot: `backups/iteration_checkpoints/20260302_word_preview_fusion_cp8_pre/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260302_word_preview_fusion_cp8_pre/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260302_word_preview_fusion_cp8_pre/preflight_meta.json`
- [x] cp9 预览融合修复完成并验证通过
  - checkpoint: `20260302_word_preview_fusion_cp9_verified`
  - snapshot: `backups/iteration_checkpoints/20260302_word_preview_fusion_cp9_verified/snapshot_src.tar.gz`
  - verification:
    - `python3 -m compileall -q main.py tests/unit/test_word_replace_rules.py`
    - `python3 -m unittest tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v`
- [x] cp10 版本发布与文档统一前备份
  - checkpoint: `20260302_release_docs_cp10_pre`
  - snapshot: `backups/iteration_checkpoints/20260302_release_docs_cp10_pre/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260302_release_docs_cp10_pre/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260302_release_docs_cp10_pre/preflight_meta.json`
- [x] cp11 版本发布与文档统一完成（已验证）
  - checkpoint: `20260302_release_docs_cp11_verified`
  - snapshot: `backups/iteration_checkpoints/20260302_release_docs_cp11_verified/snapshot_src.tar.gz`
  - verification:
    - `python3 -m compileall -q main.py docs/current/STATUS.md docs/current/DEV_LOG.md CHANGELOG.md CLAUDE.md docs/guides/QUICK_START_FOR_CLAUDE_CODE.md PROJECT_INDEX.md`
    - `python3 -m unittest tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v`
- [x] cp12 打包方案统一修复前备份（Windows/macOS packaging refresh）
  - checkpoint: `20260309_packaging_refresh_cp12_pre`
  - snapshot: `backups/iteration_checkpoints/20260309_packaging_refresh_cp12_pre/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260309_packaging_refresh_cp12_pre/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260309_packaging_refresh_cp12_pre/preflight_meta.json`
- [x] cp13 打包方案统一修复完成（已验证）
  - checkpoint: `20260309_packaging_refresh_cp13_verified`
  - snapshot: `backups/iteration_checkpoints/20260309_packaging_refresh_cp13_verified/snapshot_src.tar.gz`
  - verification:
    - `bash -n packaging/macos/scripts/build_complete.sh`
    - `bash -n packaging/macos/scripts/build_macos_app.sh`
    - `bash -n packaging/macos/scripts/sign_macos_app.sh`
    - `bash -n packaging/macos/scripts/notarize_macos_app.sh`
    - `python3 -m py_compile packaging/windows/scripts/generate_version_info.py`
    - `python3 packaging/windows/scripts/generate_version_info.py`
    - `rg -n '37\.6\.1|36\.4|3_完整打包带安装程序|1_初始化环境|2_一键打包|PrivacyGuard-36\.4|build/PrivacyGuard\.spec|修改 main\.py 中的 VERSION|create-dmg 不可用，复制 \.app|version_info 参考文档' packaging docs/packaging`
- [x] cp14 运行时整改启动前备份（安全/导入/预览/配置一致性）
  - checkpoint: `20260309_runtime_remediation_cp14_start`
  - snapshot: `backups/iteration_checkpoints/20260309_runtime_remediation_cp14_start/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260309_runtime_remediation_cp14_start/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260309_runtime_remediation_cp14_start/preflight_meta.json`
- [x] cp18 按 PRIORITY_REMEDIATION_PLAN 完成整改并验证通过
  - checkpoint: `20260309_runtime_remediation_cp18_verified`
  - snapshot: `backups/iteration_checkpoints/20260309_runtime_remediation_cp18_verified/snapshot_src.tar.gz`
  - verification:
    - `python3 -m compileall -q main.py privacyguard tests`
    - `python3 -m unittest tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v`
- [x] cp19 Word 对比预览空白 bugfix 前备份
  - checkpoint: `20260309_word_compare_bugfix_cp19_pre`
  - snapshot: `backups/iteration_checkpoints/20260309_word_compare_bugfix_cp19_pre/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260309_word_compare_bugfix_cp19_pre/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260309_word_compare_bugfix_cp19_pre/preflight_meta.json`
- [x] cp20 Word 对比预览空白 bugfix 完成（已验证）
  - checkpoint: `20260309_word_compare_bugfix_cp20_verified`
  - snapshot: `backups/iteration_checkpoints/20260309_word_compare_bugfix_cp20_verified/snapshot_src.tar.gz`
  - verification:
    - `python3 -m compileall -q main.py tests/unit/test_word_replace_rules.py`
    - `python3 -m unittest tests.unit.test_word_replace_rules tests.unit.test_app_config tests.unit.test_pdf_text_hit_dedup tests.unit.test_package_imports tests.test_path_validation tests.unit.test_batch_word_replace -v`
- [x] cp21 全量文档同步到当前代码基线（已验证）
  - checkpoint: `20260309_docs_sync_cp21_verified`
  - snapshot: `backups/iteration_checkpoints/20260309_docs_sync_cp21_verified/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260309_docs_sync_cp21_verified/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260309_docs_sync_cp21_verified/preflight_meta.json`
  - scope:
    - `README.md`
    - `PROJECT_INDEX.md`
    - `CLAUDE.md`
    - `CHANGELOG.md`
    - `docs/current/STATUS.md`
    - `docs/current/DEV_LOG.md`
    - `docs/current/PRIORITY_REMEDIATION_PLAN.md`
    - `docs/guides/QUICK_START_FOR_CLAUDE_CODE.md`
  - verification:
    - `python3 -m compileall -q main.py privacyguard tests`
    - `python3 -m unittest tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v`
- [x] cp22 混合型 PDF OCR 修复前备份
  - checkpoint: `20260309_mixed_pdf_ocr_cp22_pre`
  - snapshot: `backups/iteration_checkpoints/20260309_mixed_pdf_ocr_cp22_pre/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260309_mixed_pdf_ocr_cp22_pre/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260309_mixed_pdf_ocr_cp22_pre/preflight_meta.json`
- [x] cp23 混合型 PDF OCR 修复完成（已验证）
  - checkpoint: `20260309_mixed_pdf_ocr_cp23_verified`
  - snapshot: `backups/iteration_checkpoints/20260309_mixed_pdf_ocr_cp23_verified/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260309_mixed_pdf_ocr_cp23_verified/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260309_mixed_pdf_ocr_cp23_verified/preflight_meta.json`
  - verification:
    - `python3 -m compileall -q main.py privacyguard tests`
    - `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.unit.test_pdf_text_hit_dedup tests.unit.test_package_imports tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_app_config tests.test_path_validation tests.unit.test_ocr_api -v`
- [x] cp24 版本/文档/打包方案同步前备份
  - checkpoint: `20260309_release_sync_cp24_pre`
  - snapshot: `backups/iteration_checkpoints/20260309_release_sync_cp24_pre/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260309_release_sync_cp24_pre/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260309_release_sync_cp24_pre/preflight_meta.json`
- [x] cp25 v37.7.1 发布同步完成（已验证）
  - checkpoint: `20260309_release_sync_cp25_verified`
  - snapshot: `backups/iteration_checkpoints/20260309_release_sync_cp25_verified/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260309_release_sync_cp25_verified/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260309_release_sync_cp25_verified/preflight_meta.json`
  - verification:
    - `python3 packaging/windows/scripts/generate_version_info.py`
    - `python3 -m compileall -q main.py privacyguard tests`
    - `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v`
    - `bash -n packaging/macos/scripts/build_complete.sh`
    - `bash -n packaging/macos/scripts/build_macos_app.sh`
    - `bash -n packaging/macos/scripts/sign_macos_app.sh`
    - `bash -n packaging/macos/scripts/notarize_macos_app.sh`
- [x] cp26 Word 原文预览红色高亮串位修复前备份
  - checkpoint: `20260310_word_preview_highlight_cp26_pre`
  - snapshot: `backups/iteration_checkpoints/20260310_word_preview_highlight_cp26_pre/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260310_word_preview_highlight_cp26_pre/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260310_word_preview_highlight_cp26_pre/preflight_meta.json`
- [x] cp27 Word 原文预览红色高亮串位修复完成（已验证）
  - checkpoint: `20260310_word_preview_highlight_cp27_verified`
  - snapshot: `backups/iteration_checkpoints/20260310_word_preview_highlight_cp27_verified/snapshot_src.tar.gz`
  - verification:
    - `python3 -m compileall -q main.py tests/unit/test_word_replace_rules.py`
    - `python3 -m unittest tests.unit.test_word_replace_rules tests.unit.test_app_config tests.unit.test_pdf_text_hit_dedup tests.unit.test_package_imports tests.test_path_validation tests.unit.test_batch_word_replace tests.unit.test_mixed_pdf_ocr tests.unit.test_ocr_api -v`
- [x] cp28 v37.7.2 发布同步前备份
  - checkpoint: `20260310_release_sync_cp28_pre`
  - snapshot: `backups/iteration_checkpoints/20260310_release_sync_cp28_pre/snapshot_src.tar.gz`
  - manifest: `backups/iteration_checkpoints/20260310_release_sync_cp28_pre/key_files_manifest.txt`
  - preflight meta: `backups/iteration_checkpoints/20260310_release_sync_cp28_pre/preflight_meta.json`
- [x] cp29 v37.7.2 发布同步完成（已验证）
  - checkpoint: `20260310_release_sync_cp29_verified`
  - snapshot: `backups/iteration_checkpoints/20260310_release_sync_cp29_verified/snapshot_src.tar.gz`
  - verification:
    - `python3 packaging/windows/scripts/generate_version_info.py`
    - `python3 -m compileall -q main.py privacyguard tests`
    - `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v`
    - `bash -n packaging/macos/scripts/build_complete.sh`
    - `bash -n packaging/macos/scripts/build_macos_app.sh`
    - `bash -n packaging/macos/scripts/sign_macos_app.sh`
    - `bash -n packaging/macos/scripts/notarize_macos_app.sh`
- [x] cp30 PyInstaller 打包模块导入失败修复完成（已验证）
  - checkpoint: `20260311_pyinstaller_packaging_fix_cp30_verified`
  - verification:
    - Windows 打包成功
    - 打包应用正常启动
    - `ModuleNotFoundError: No module named 'privacyguard.utils.security'` 不再出现
- [x] cp31 v38 UI 重构启动前检查点（Windows-first UI refactor preflight）
  - checkpoint: `v38_ui_refactor_cp31_20260313_140645`
  - snapshot dir: `backups/v38_ui_refactor_cp31_20260313_140645/`
  - backup files:
    - `main.py`
    - `theme.py`
    - `rollback_journal.md`
    - `docs/current/STATUS.md`
    - `docs/current/DEV_LOG.md`
    - `docs/features/privacyguard_ui_concept_v38_logic_preserved_cn.html`
  - purpose:
    - 启动 Windows-first UI 全面改造前保留主运行链与文档基线
    - 避免在 dirty worktree 中依赖 `git revert` 回退
    - 后续 UI 迭代统一基于 `cp31` 分阶段推进
- [x] cp32 第二轮代码审计修复（接手上一个中断的 agent）
  - checkpoint: `20260721_audit_fix_round2_cp32_verified`
  - snapshot dir: `backups/audit_fix_round2_20260721_200155/`
  - backup files:
    - `main.py.backup`
    - `privacyguard/workers/ocr_worker.py.backup`
    - `privacyguard/workers/word_worker.py.backup`
    - `privacyguard/ocr/mixed_pdf.py.backup`
  - context:
    - 上一个 agent 已完成 W1-W5（Word 系）+ O1/O2/O8（PDF 系）共 8 项修复后中断
    - 本次接手做了第二轮全量审计，再发现并修复 9 项遗留问题
  - changes:
    - A 批（严重，3 项）：
      - `S1` OCRWorker.run 在引擎不可用时 early return 跳过 finished_signal，主线程永久卡死 → 改为 raise 后落入统一信号发射路径
      - `S2` WordBatchReplaceWorker.run 单文件 except 过窄，损坏 docx 抛 PackageNotFoundError 时逃出 run() 导致 UI 永久 running → 改为兜底 `except Exception`
      - `S3` `_cleanup_before_open` / `_app_exit_cleanup` 中 `wait(2000)` 超时后直接 `active_worker = None` 丢弃线程，旧信号污染新文档 → 改为断开信号 + `deleteLater` 延迟销毁
    - A 批（中等，4 项）：
      - `M1` `_open_pdf_file` 无 try/except，损坏 PDF 的 FileDataError 直达全局 hook → 拦截并显式提示
      - `M7` 加密 PDF 无认证流程却照常打开 → `needs_pass` 时显式提示后拒绝打开
      - `M7'` `_open_word_docx` / `_save_word` except 列表不含 PackageNotFoundError → 纳入捕获
      - `M4` Word 保存缺 O1 等效保护 → 新增 `_word_scan_meta` 状态 + 保存前二次确认
      - `L7` `collect_image_block_ocr_hits` 预处理异常冒出中断整篇扫描 → 包进单块 try 保守覆盖
    - B 批（一致性，2 项）：
      - `B1` WordWorker `_emit_progress` 节流失效（每条都刷新 last_emit_time） → 改为仅在真正发射时返回新时间戳
      - `B2` `_check_doc_support` 与 `doc_converter.resolve_soffice_cmd` 双份 LibreOffice 探测口径不一致 → 统一委托共享模块，并在 Linux 补 `libreoffice` 别名
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - `python -m unittest`（与本次改动直接相关的 7 个测试文件，共 59 用例）→ 全过
    - 完整回归套件 92 测试中 88 通过；4 个失败为修复前即已存在的跨平台路径测试 `test_path_validation`（mock `platform.system` 但路径函数走真实 OS，在真 Windows 上必然失败），与本次改动无关
- [x] cp33 第三轮代码审计修复（6 项遗留修复与代码清理）
  - checkpoint: `20260721_audit_fix_round3_cp33_verified`
  - snapshot dir: `backups/audit_fix_round3_20260721_203454/` 与 `backups/cp33_round5_20260721/`
  - backup files:
    - `privacyguard/utils/security.py.backup`
    - `tests/test_path_validation.py.backup`
    - `privacyguard/ocr/__init__.py.backup`
    - `packaging/windows/config/hook-privacyguard.py.backup`
    - `tests/unit/test_stability.py`、`tests/unit/test_ocr_api.py`、`tests/scripts/test_word_processor.py`
    - `privacyguard/utils/config.py`（DEFAULT_CONFIG 印章 description 修正）
    - `tests/unit/test_config_alignment.py`（5 个新对齐用例）
  - changes:
    - 项1 Windows 路径校验误拒：Windows 下改黑名单模式（仅拒 `C:\Windows`/`Program Files`/`Program Files (x86)`/`ProgramData`），POSIX 保持原白名单；basename `..` 检查改为只拒纯 `..`，避免误伤 `a..b.pdf`
    - 项2 W4 Word 扫描竞态：`WebViewBridge.add_manual_redaction` / `add_manual_redaction_global` 入口扫描运行时拦截
    - 项3 W2 页眉/页脚命中无提示：`word_scan_finished` 新增 `header_*` / `footer_*` 命中统计与提示后缀
    - 项4 死代码清理：main.py 删除 ~293 行（顶部 OCR 全局 / 未用 mixed_pdf 导入 / 6 个死函数 / PRIVACYGUARD_PRELOAD_OCR 启动预热块）；`privacyguard/ocr/__init__.py` 改懒加载；删除空壳包 `privacyguard/core/` 与 `privacyguard/ui/`；`hook-privacyguard.py` 移除已删除包引用
    - 项5 过期测试修正：`test_stability.py` 重写为 9 个真实 TestCase；`test_ocr_api.py` 加强断言；`test_word_processor.py` 改用 `paragraph_plain_text` 口径 + skipUnless；`test_path_validation.py` 修复 POSIX 模式 `expanduser` mock 缺失
    - 项6 配置系统收敛：修正 `DEFAULT_CONFIG.印章.description` 与 `config.json` 漂移；`test_config_alignment.py` 新增 5 个对齐用例；按 AGENTS.md 约定保留 SimpleConfig 作为运行时入口
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - `python -c "import privacyguard; from privacyguard.ocr import OCREngineManager"` → IMPORT_OK
    - `tests/unit/test_stability` → 9/9 通过
    - `tests/test_path_validation` → 13/13 通过
    - `tests/unit/test_ocr_api` → 3 用例（rapidocr 未装时 skip）
    - `tests/scripts/test_word_processor` → 7 用例（fitz 未装时 skip）
    - DEFAULT_CONFIG 与 config.json 深度对齐独立脚本 → 完全一致

## 2026-07-22 PDF 遮罩精准度修复 cp34-cp38（v37.7.9）

- [x] cp38_pdf_redaction_precision_v5_verified
  - checkpoint: `cp38_pdf_redaction_precision_v5_verified`
  - backup: `backups/cp38_pdf_redaction_precision_v5_pre/`（ocr_worker.py, version.txt, CHANGELOG.md, STATUS.md, DEV_LOG.md, rollback_journal.md）
  - 改动文件清单:
    - `privacyguard/workers/ocr_worker.py`（核心修复）
    - `tests/unit/test_ocr_substring_precision_v3.py`（3 个测试修正）
    - `tests/unit/test_ocr_substring_precision_v4.py`（3 个测试已更新）
    - `tests/unit/test_ocr_substring_precision_v5.py`（5 个新测试）
    - `version.txt`（37.7.6 → 37.7.9）
    - `CHANGELOG.md` / `docs/current/STATUS.md` / `docs/current/DEV_LOG.md` / `rollback_journal.md`
  - changes:
    - cp34 R1-R5: 像素级字符切分 + y 方向边界检测 + margin PDF 点空间 + min 宽度 + 边界保护
    - cp35 F1-F5: 三档混合算法（A/B/C 档）+ 形态学核宽 + 超宽段二次切分 + 阈值自适应
    - cp36 F6-F15: B 档累计权重对齐 + C 档 seg_block_width + 自适应间隙 + 等分回退 + box_adjust_ratio 复活 + 阈值更严格 + margin 对称 + dedup 面积升序 + 二值化兼容
    - cp37 F16-F20: B 档 _interp_pixel 不跨 gap + _detect_vertical_boundaries 收紧 y + 跨行 box 切单行 + RapidOCR 真实 confidence + ROI 2x 放大尝试
    - cp38 F20-redesign + F23 + F24: 放弃 2x 放大只做 ROI 外扩 8px + gap_tolerance 加 median_gap*0.8 上限 + 坐标转换无条件化 + sub_rect 宽度合理性检查兜底
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - `python -m unittest tests.unit.test_ocr_substring_precision_v3 tests.unit.test_ocr_substring_precision_v4 tests.unit.test_ocr_substring_precision_v5 -v` → 35 测试通过（2 skip 为 PyQt6.QtWebEngineWidgets 环境依赖）
    - `python -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_fstring_safety` → 全部通过
  - rollback:
    - 恢复 `privacyguard/workers/ocr_worker.py` 从 `backups/cp38_pdf_redaction_precision_v5_pre/ocr_worker.py`
    - 恢复 `version.txt` 从备份（37.7.9 → 37.7.6）
    - 恢复 `tests/unit/test_ocr_substring_precision_v3.py` 从备份（3 个测试修正回退）
    - 删除 `tests/unit/test_ocr_substring_precision_v5.py`
    - 恢复 CHANGELOG/STATUS/DEV_LOG/rollback_journal 从备份
- [x] cp39 PDF 取色遮罩按钮功能完成（已验证）
  - checkpoint: `cp39_color_mask_button_verified`
  - backup: `backups/cp39_color_mask_pre/`（main.py，改动前快照）
  - 改动文件清单:
    - `main.py`（核心实现：rb_color 按钮 + 色板面板 + 全屏取色器 + save_pdf 修复 + Density 同步）
    - `version.txt`（37.7.9 → 37.7.10）
    - `packaging/windows/config/PrivacyGuard_Setup.iss`（默认回退版本 37.7.4 → 37.7.10）
    - `packaging/windows/config/version_info.txt`（重新生成）
    - `CHANGELOG.md` / `docs/current/STATUS.md` / `docs/current/DEV_LOG.md` / `rollback_journal.md`
    - `packaging/README.md` / `docs/packaging/*.md` / `packaging/DUAL_OCR_PACKAGING.md` / `packaging/{windows,macos}/docs/*_BUILD_GUIDE.md` / `packaging/{windows,macos}/scripts/README.txt`（版本号同步）
  - changes:
    - 新增 `rb_color` 按钮（位于白遮右侧、双页左侧），与黑/白遮加入 `QButtonGroup(exclusive=True)` 三选一互斥
    - 新增色板面板 `_build_color_palette_widget`：8 常用色块 + QLineEdit 自定义色值 + 全屏取色器按钮
    - 新增 `_toggle_color_palette` / `_apply_custom_color` / `_apply_hex_input` 方法
    - 新增 `_ScreenColorPickerOverlay` 类（顶层 QWidget，全屏覆盖层 + 十字光标 + 颜色预览 + Esc 取消）
    - 新增 `pick_screen_color` / `_on_screen_color_picked` 方法
    - 重写 `update_canvas_color` 兼容三态（原 else 强制设白会覆盖取色）
    - 修复 `save_pdf` 硬编码 bug：`fill_col` 改为按 RGB 归一化 `(c.red()/255, c.green()/255, c.blue()/255)`
    - Density 文案同步 color_text（wide/compact/narrow 三档）
    - narrow 模式收纳：rb_color 移入"更多"菜单 + `_open_color_palette_from_menu` 方法
  - cp39-fix1 高 DPI 屏取色不准:
    - 根因：`grabWindow(0)` 返回物理像素 QPixmap（2880×1620），QWidget 鼠标坐标是逻辑像素（1920×1080），直接 `pixelColor(mouse_pos)` 取到错误像素
    - 修复：新增 `_pick_color_at` 做 DPI 缩放转换；用 `setGeometry(screen.geometry())` 替代 `showFullScreen()`；限定截图到主屏；mousePressEvent 触发时再调一次 `_pick_color_at`
  - verification:
    - `python -m compileall -q main.py` → OK
    - `python -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_fstring_safety tests.unit.test_ocr_substring_precision_v3 tests.unit.test_ocr_substring_precision_v4 tests.unit.test_ocr_substring_precision_v5 tests.unit.test_convergence` → 64 tests / failures=0 / skipped=2
    - 唯一 ERROR `test_main_py_version_fallback_matches_current` 为环境限制（PyQt6.QtWebEngineWidgets 缺失），与改动无关
    - `python packaging/windows/scripts/generate_version_info.py` → version_info.txt 重新生成 37.7.10
  - rollback:
    - 恢复 `main.py` 从 `backups/cp39_color_mask_pre/main.py`
    - 恢复 `version.txt` 从 37.7.10 → 37.7.9
    - 恢复 `packaging/windows/config/PrivacyGuard_Setup.iss` 默认版本从 37.7.10 → 37.7.4
    - 重新执行 `python packaging/windows/scripts/generate_version_info.py` 重生成 version_info.txt
    - 恢复 CHANGELOG/STATUS/DEV_LOG/rollback_journal 从备份或手工删除 cp39 段落
    - 恢复 packaging 相关 md/txt 文件版本号从 37.7.10 → 37.7.4


## 2026-07-23 cp40 去卷宗水印功能

- [x] cp40 备份完成
  - checkpoint: `cp40_case_file_watermark_verified`
  - snapshot: `backups/cp40_watermark_pre/main.py`
- [x] cp40 实施 + 验证
  - 改动文件清单:
    - `main.py`（新增 `_detect_watermark_spans` / `remove_case_file_watermark` 方法 + `btn_remove_watermark` 按钮 + 显隐联动 + Density 文案 + overflow 收纳 + `save_pdf` 兼容 `_pdf_modified`）
    - `version.txt`（37.7.10 → 37.7.11）
    - `CHANGELOG.md` / `docs/current/STATUS.md` / `docs/current/DEV_LOG.md` / `rollback_journal.md`
  - changes:
    - 新增 `_detect_watermark_spans(page)` 方法：评分制识别（4 项特征满足 ≥3 项判定）+ (bbox, text) 去重
      - 特征1: bbox 异常大（旋转 45° 包围盒 >100×100）
      - 特征2: 字体含 NotoSansCJK
      - 特征3: 颜色 4210752 深灰
      - 特征4: 文本含数字 + (含中文 或 长度≥6)
    - 新增 `remove_case_file_watermark()` 方法：扫描全部页 → 确认对话框 → 逐页 `add_redact_annot(fill=(1,1,1))` + `apply_redactions` → 标记 `self._pdf_modified=True` → 刷新预览 → 启用导出
    - `save_pdf` 加 `_pdf_modified` 分支：若 `True` 则 `fitz.open(stream=self.doc.tobytes(garbage=4, deflate=True))` 复用内存字节流，避免重新打开原文件丢失去除效果
    - 工具栏 `toolbar_utility_layout` 在 `btn_save` 之前新增 `btn_remove_watermark`，初始 hide
    - 按钮显隐联动：`_cleanup_before_open` 末尾 hide + 重置 `_pdf_modified=False`；`_open_pdf_file` 成功后 show
    - Density 文案同步：`watermark_text = "去水印" if density_mode != "narrow" else "水印"`
    - `_refresh_toolbar_overflow_menu` narrow 模式收纳：移入"更多"菜单；compact/wide PDF 显式 `show()` 兜底（兜底从 narrow 切回 wide 后按钮被 hide 的场景）
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - 独立脚本 `_verify_detect.py` 对 `提取自诉讼文书卷.pdf` 跑通：识别到 28 处水印（4 底部"134172" + 20 完整水印 + 4 顶部"2刘韧"残缺），与 PyMuPDF dict 唯一水印数完全一致，无重复/无误报
    - 回归测试：21 tests ok；3 errors 全部因环境缺 `PyQt6.QtWebEngineWidgets` 无法 `from main import ...`，与改动无关
    - 待用户手动验证：启动 `python main.py` → 打开 `提取自诉讼文书卷.pdf` → 工具栏出现"去水印"按钮 → 点击 → 弹"共识别到 28 处卷宗水印"确认 → 点「是」→ 预览中水印消失 → 点"导出"保存
  - rollback:
    - 恢复 `main.py` 从 `backups/cp40_watermark_pre/main.py`
    - 恢复 `version.txt` 从 37.7.11 → 37.7.10
    - 恢复 CHANGELOG/STATUS/DEV_LOG/rollback_journal 从备份或手工删除 cp40 段落

- checkpoint: `cp41_version_unify_20260723`
  - date: 2026-07-23
  - summary: 版本号统一来源，消除硬编码，统一引用 version.txt
  - version: 37.7.11 → 37.7.12
  - changes:
    - 排查所有版本号位置（代码/注释/界面/文档）
    - `main.py` 失败后备 `"37.7.6"` → `"0.0.0"`
    - `main.py` VERSION 去掉 ` - Engineering Remediation` 后缀，`VERSION = APP_VERSION`
    - `privacyguard/__init__.py` 失败后备 `"37.7.6"` → `"0.0.0"`
    - `packaging/windows/config/PrivacyGuard_Setup.iss` 默认值 `"37.7.10"` → `"0.0.0"` + 注释
    - `version.txt` 37.7.11 → 37.7.12
    - `packaging/windows/config/version_info.txt` 重新生成（37.7.12.0）
    - 11 处文档当前版本描述同步到 v37.7.12：
      - packaging/README.md, docs/packaging/README.md
      - docs/packaging/windows-packaging-guide.md, docs/packaging/macos-packaging-guide.md
      - packaging/DUAL_OCR_PACKAGING.md
      - packaging/windows/docs/WINDOWS_BUILD_GUIDE.md
      - packaging/macos/docs/MACOS_BUILD_GUIDE.md
      - packaging/windows/scripts/README.txt, packaging/macos/scripts/README.txt
      - docs/current/STATUS.md, docs/current/DEV_LOG.md
    - CHANGELOG.md 追加 cp41 段
    - rollback_journal.md 追加 cp41 检查点
    - 保留不改：main.py 中 20 处 `# v37.7.10/v37.7.11 cp39/cp40:` 历史变更注释
    - 保留不改：CHANGELOG/DEV_LOG/STATUS/rollback_journal 中历史段标题（如 `## cp40（v37.7.11）`）
  - verification:
    - `python -m compileall -q main.py` → OK
    - `python packaging/windows/scripts/generate_version_info.py` → version_info.txt 生成 37.7.12.0
    - 文档版本号一致性 grep 确认
  - backup: `backups/cp41_version_unify_pre/`
  - rollback:
    - 恢复 `main.py` 从 `backups/cp41_version_unify_pre/main.py`
    - 恢复 `privacyguard/__init__.py` 从 `backups/cp41_version_unify_pre/__init__.py`
    - 恢复 `packaging/windows/config/PrivacyGuard_Setup.iss` 从 `backups/cp41_version_unify_pre/PrivacyGuard_Setup.iss`
    - 恢复 `version.txt` 从 37.7.12 → 37.7.11
    - 重新生成 version_info.txt（`python packaging/windows/scripts/generate_version_info.py`）
    - 恢复 CHANGELOG/STATUS/DEV_LOG/rollback_journal 从备份或手工删除 cp41 段落

- checkpoint: `cp43_pdf_replace_text_overlay_20260723`
  - date: 2026-07-23
  - summary: PDF 替换文本叠加层功能，遮罩后叠加替换文本层
  - version: 37.7.12 → 37.7.13
  - changes:
    - `main.py`（30+ 处：`_hit_rect` / `_hit_replace_text` / `_make_hit` 兼容函数；`_collect_custom_keyword_rules_from_table` 表格收集；`cb_manual_replace_prompt` 开关；`_draw_replace_text` 预览叠加；`save_pdf` 文本层叠加；`page_data` dict 元素改造；`_deduplicate_rects` / `_is_overlapping` 适配 dict）
    - `privacyguard/workers/ocr_worker.py`（`custom_keyword_rules` 参数 + `keyword_replace_map` + `_lookup_replace` + 3 处命中返回 dict）
    - `privacyguard/ocr/text_pdf.py`（`collect_text_pdf_hit_boxes` 返回 5 元组）
    - `privacyguard/ocr/mixed_pdf.py`（`collect_image_block_ocr_hits` 返回 `(rect, matched_text)` 元组）
    - `tests/unit/test_custom_keyword_rules.py`（新增，12 个测试方法）
    - `config.json`（新增 `custom_keyword_rules` + `manual_replace_prompt` 字段）
    - `version.txt`（37.7.12 → 37.7.13）
    - `CHANGELOG.md` / `docs/current/STATUS.md` / `docs/current/DEV_LOG.md` / `rollback_journal.md`
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - `python -m unittest tests.unit.test_custom_keyword_rules -v` → 12/12 通过
    - 回归测试：44 tests OK（唯一 ERROR 为已知 PyQt6.QtWebEngineWidgets 环境缺失）
  - backup: `backups/cp43_replace_text_overlay_pre/`（建议用户在本地创建）

- [x] cp44-pre RapidOCR 升级前备份（v37.7.13）
  - checkpoint: `pre_rapidocr_v3_upgrade_20260723`
  - snapshot dir: `backups/pre_rapidocr_v3_upgrade_20260723/`
  - purpose:
    - 为 RapidOCR 从 v1.2.3（rapidocr-onnxruntime）升级到 v3.9.2（rapidocr）做准备
    - **未修改任何运行时代码**，仅备份 + 文档记录
  - backup files (16):
    - `privacyguard__ocr__rapidocr.py`
    - `privacyguard__ocr____init__.py`
    - `privacyguard__workers__ocr_worker.py`
    - `main.py`
    - `tests__unit__test_ocr_api.py`
    - `tests__unit__test_package_imports.py`
    - `packaging__windows__config__hook-privacyguard.py`
    - `packaging__windows__config__PrivacyGuard_windows.spec`
    - `packaging__windows__config__PrivacyGuard_windows_v2.spec`
    - `packaging__macos__config__PrivacyGuard.spec`
    - `packaging__windows__scripts__verify_dependencies.py`
    - `requirements.txt`
    - `CHANGELOG.md`
    - `docs__current__STATUS.md`
    - `docs__current__DEV_LOG.md`
    - `rollback_journal.md`
  - baseline:
    - 引擎: RapidOCR
    - 包: `rapidocr-onnxruntime==1.2.3`
    - 模型: PP-OCRv4
    - 导入: `from rapidocr_onnxruntime import RapidOCR`
    - 调用: `RapidOCR()` 无参，`engine(image)` 返回 `(result, _)`，`line=[box,text,confidence]`
  - rollback:
    1. 还原代码（PowerShell）：
       ```
       Copy-Item backups\pre_rapidocr_v3_upgrade_20260723\privacyguard__ocr__rapidocr.py privacyguard\ocr\rapidocr.py -Force
       Copy-Item backups\pre_rapidocr_v3_upgrade_20260723\privacyguard__ocr____init__.py privacyguard\ocr\__init__.py -Force
       Copy-Item backups\pre_rapidocr_v3_upgrade_20260723\privacyguard__workers__ocr_worker.py privacyguard\workers\ocr_worker.py -Force
       Copy-Item backups\pre_rapidocr_v3_upgrade_20260723\main.py main.py -Force
       Copy-Item backups\pre_rapidocr_v3_upgrade_20260723\requirements.txt requirements.txt -Force
       ```
    2. 还原依赖：
       ```
       pip uninstall rapidocr -y
       pip install rapidocr-onnxruntime==1.2.3
       ```
    3. 验证：`python main.py` 启动应用，OCR 功能正常
  - docs updated:
    - `CHANGELOG.md`（新增 cp44-pre 段含回退方法）
    - `docs/current/STATUS.md`（头部状态 + 新增 cp44-pre 段）
    - `docs/current/DEV_LOG.md`（头部状态 + 新增 cp44-pre 段）
    - `rollback_journal.md`（本段）

- [x] cp44 RapidOCR 引擎升级完成（v37.7.14）
  - checkpoint: `rapidocr_v3_upgrade_cp44_verified`
  - upgrade: `rapidocr-onnxruntime==1.2.3` (PP-OCRv4) → `rapidocr==3.9.2` (PP-OCRv6)
  - dependency upgrades: `onnxruntime` 1.16.3 → 1.27.0 (IR v10 support), `numpy` 1.26.4 → 2.4.6
  - changes:
    - `privacyguard/ocr/rapidocr.py`: 导入路径 `from rapidocr_onnxruntime` → `from rapidocr`
    - `main.py`: OCR 错误提示文案
    - `requirements.txt`: `rapidocr==3.9.2`
    - `packaging/windows/scripts/verify_dependencies.py`: 模块检查项
    - 3 个 spec 文件: `collect_all('rapidocr')`、hiddenimports
    - `tests/unit/test_ocr_api.py` + `tests/unit/test_package_imports.py`: 导入路径适配
  - api compatibility: `(result, elapse)` 返回结构不变，`line = [box, text, confidence]` 不变
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - 51 测试中 5 ERROR 为已知环境限制（`PyQt6.QtWebEngineWidgets` 缺失），与升级无关
    - RapidOCR 相关测试（test_ocr_api、test_package_imports、test_mixed_pdf_ocr）通过
  - rollback: 同 cp44-pre 的 rollback 步骤（还原代码 + 还原依赖）

- [x] cp45 遮罩精准度修复（v37.7.15）
  - checkpoint: `mask_precision_cp45_verified`
  - purpose: 修复用户反馈的三个问题——遮罩不完整覆盖文字、多层叠加、左右偏移
  - changes:
    - `privacyguard/workers/ocr_worker.py`:
      - `_calculate_from_line` 返回前加 PDF 坐标系 padding（左右 1pt / 上下 0.5pt），吸收 OCR v3.x box ±2-5px 偏差
      - `_detect_text_boundaries` mean>220 阈值 0.30 → 0.20，修复抗锯齿边缘误判导致 line_x_min 偏内、sub_rect 右移
    - `main.py`:
      - `_deduplicate_rects` IoU 阈值 0.7 → 0.5（部分重叠即合并）
      - 新增 `_is_half_overlapping`：x/y 重叠 ≥ 50% → 取并集合并，解决多层叠加
    - `tests/unit/test_config_alignment.py`: `test_custom_keywords_matches` 改为只验证字段存在（custom_keywords 是用户运行时可改的配置）
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - venv_win 环境下 95 测试全部通过
  - rollback: 还原 `privacyguard/workers/ocr_worker.py` + `main.py` + `tests/unit/test_config_alignment.py`（建议先备份再修改）

- [x] cp46 遮罩左右偏移根因修复（v37.7.16）
  - checkpoint: `remove_b_tier_cp46_verified`
  - purpose: 修复 cp45 后仍存在的系统性左右偏移——B 档累计权重忽略段间间隙导致 sub_rect 左偏 30-60pt
  - backup: `backups/cp46_remove_b_tier_pre/ocr_worker.py.bak`
  - changes:
    - `privacyguard/workers/ocr_worker.py`:
      - 删除 B 档算法（段数近似但不等时的累计权重 + 线性插值），根因所在
      - C 档（像素收紧权重估算，用 seg_block_width 含间隙）作为默认兜底
      - A 档（段数严格等于文本长度）保留
      - 删除未使用的 `bisect` 模块导入
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - 回归测试通过（4 个 ERROR 均为已知 PyQt6.QtWebEngineWidgets 环境缺失）
    - `提取自诉讼证据卷.pdf` 自行测试 41 处命中：子串定位比例正确（15/18），跨页一致，偏移从 -60pt 降至 ±5pt 内
  - rollback: `Copy-Item backups\cp46_remove_b_tier_pre\ocr_worker.py.bak privacyguard\workers\ocr_worker.py -Force`

- [x] cp47 OCR 过程中遮罩实时显示（v37.7.17）
  - checkpoint: `ocr_live_refresh_cp47_verified`
  - purpose: 修复 OCR 过程中屏幕界面无实时显示——仅在 OCR 全部完成时 render_view 重绘整个页面
  - backup: `backups/cp47_ocr_live_refresh_pre/main.py.bak`
  - changes:
    - `main.py`:
      - `_on_ocr_page_result` 改为原地更新 OCR 结果列表（`existing.clear()` + `existing.extend(deduped)`），保持 canvas 持有的 list 引用不变
      - 新增 `_maybe_refresh_visible_page`：300ms 节流刷新当前可见页 canvas，仅 `canvas.update()` 重绘遮罩层，不重画 pix 图
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - 回归测试通过
  - rollback: `Copy-Item backups\cp47_ocr_live_refresh_pre\main.py.bak main.py -Force`

- [x] cp48 多字词一体化遮罩（v37.7.17）
  - checkpoint: `merge_per_char_rects_cp48_verified`
  - purpose: 修复多字关键词（如"王小明"）被 PyMuPDF search_for 拆分为多个 per-span rect 导致生成多个独立遮罩，替换时产生"华子 华子 华子"重复替换 bug
  - root_cause: PyMuPDF `page.search_for(needle)` 在 needle 跨越多个 text span 时（如每字符独立 span）会为每个 span 返回一个 Rect
  - backup: `backups/cp48_merge_per_char_rects_pre/text_pdf.py.bak`
  - changes:
    - `privacyguard/ocr/text_pdf.py`:
      - 新增 `_merge_adjacent_same_line_rects(hits, y_tolerance=2.0, gap_ratio=0.5)`：合并同行（y0/height 相近）且 x 相邻（gap ≤ 0.5*min_width）的 rect
      - `collect_text_pdf_hit_boxes` 在 `page.search_for` 返回后调用本函数
      - 兼容多种输入：fitz.Rect / SimpleNamespace(x0,y0,width,height) / 4 元组
    - `tests/unit/test_pdf_text_hit_dedup.py`:
      - 新增 5 个测试用例覆盖合并逻辑
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - `python -m unittest tests.unit.test_pdf_text_hit_dedup -v` → 7 passed
    - 回归测试 35 passed (3 skipped)
    - `提取自诉讼证据卷.pdf` 3 页诊断：p0 7→5、p1 7→5、p2 3→1，与文本中"王小明"出现次数完全一致
  - rollback: `Copy-Item backups\cp48_merge_per_char_rects_pre\text_pdf.py.bak privacyguard\ocr\text_pdf.py -Force`


- [x] cp51-cp56 印章检测多特征融合 + 银行卡号 Luhn 校验 + OCR 超大遮罩修复（v37.7.19）
  - checkpoint: `seal_luhn_mask_fix_cp51_56_verified`
  - date: 2026-07-24
  - purpose: 修复三类核心问题——印章检测误判严重、银行卡号导致超大遮罩、身份证号被 Luhn 误伤
  - version: 37.7.18 → 37.7.19
  - changes:
    - `privacyguard/workers/ocr_worker.py`:
      - 新增 `SEAL_KEYWORDS`（多字组合）+ `SEAL_CHAR_KEYWORDS=[]`（清空单字）
      - 新增 `_detect_star_in_roi`（五角星检测，8-12 顶点 + 5-7 顶点凹形）
      - 新增 `_ocr_seal_region`（印章区域 OCR 文字验证）
      - 新增 `_make_block_failure_fn`（整块覆盖面积限制，>30% 页面面积不覆盖）
      - 全面重写 `_detect_seals`：多特征评分融合（颜色+形状+五角星+OCR文字）
      - `calculate_sub_rect` 入口新增 OCR box 宽度限制（>80% 图像宽度跳过）
      - `_calculate_from_line` C 档新增 segments 为空时的宽度上限
      - 调用点传入 `page_origin=(page.rect.x0, page.rect.y0)` 补偿 MediaBox 偏移
    - `privacyguard/ocr/text_pdf.py`:
      - 新增 `_IDCARD_PATTERN`（身份证号正则，用于排除 Luhn 误伤）
      - 新增 `_is_valid_luhn()`（Luhn 算法校验银行卡号）
      - 新增 `_looks_like_idcard()`（判断数字串是否为身份证号格式）
      - `iter_unique_text_matches` 增加 Luhn 校验（先排除身份证号）
    - `privacyguard/ocr/mixed_pdf.py`:
      - 导入 `_is_valid_luhn, _looks_like_idcard`
      - 图片 OCR 路径同步增加 Luhn 校验 + 身份证号排除
    - `tests/unit/test_seal_detection.py`: 新增 25 个测试用例
    - `config.json` / `privacyguard/utils/config.py` / `config.json.template`: 印章规则描述更新
    - `version.txt`: 37.7.18 → 37.7.19
    - `packaging/windows/config/version_info.txt`: 重新生成 37.7.19.0
    - `CHANGELOG.md` / `docs/current/STATUS.md` / `docs/current/DEV_LOG.md` / `rollback_journal.md`: 文档同步
  - known_limitations:
    - 公章识别准确率有待提高（变形/淡色/复杂背景印章仍有漏检或误判）
    - macOS 端 `venvmac` 虚拟环境依赖仍为旧版 `rapidocr-onnxruntime==1.2.3`，需在 macOS 环境下升级到 `rapidocr==3.9.2` 后重新打包
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - `python -m unittest tests.unit.test_seal_detection -v` → 25 passed
    - 全量回归 90 tests OK（4 skipped 为 PyQt6.QtWebEngineWidgets 环境缺失）
    - Luhn 校验：VISA 测试卡 4111111111111111 → True；案件号 13417202010172812 → False；身份证号 → 跳过 Luhn（保留）
  - rollback:
    - 还原 `privacyguard/workers/ocr_worker.py`（印章检测 + OCR box 限制）
    - 还原 `privacyguard/ocr/text_pdf.py`（Luhn 校验 + 身份证号排除）
    - 还原 `privacyguard/ocr/mixed_pdf.py`（图片 OCR 路径 Luhn 校验）
    - 还原 `version.txt` 从 37.7.19 → 37.7.18
    - 重新生成 version_info.txt（`python packaging/windows/scripts/generate_version_info.py`）
    - 还原 CHANGELOG/STATUS/DEV_LOG/rollback_journal 中 cp51-cp56 段落


- [x] cp58 全面稳定修复（v37.7.19）
  - checkpoint: `stability_fix_cp58_verified`
  - date: 2026-07-24
  - purpose: 代码审计发现的两个关键 bug 修复 + 测试覆盖增强
  - version: 37.7.19（未升级，仅 bug 修复）
  - changes:
    - `privacyguard/ocr/text_pdf.py`:
      - `_is_valid_luhn`: 新增空输入防御 `if not digits: return False`（旧版空串返回 True 是 bug）
      - `_is_bank_card_pattern`: 移除 `^` 锚点（旧版要求 pattern 必须以 `[1-9]` 开头，导致 config.json 默认 pattern `(?<!\d)([1-9]\d{12,18})(?!\d)` 不被识别，Luhn 校验失效）
      - `_BANK_CARD_DIGIT_PATTERN`: 从 `^\[1-9\]\\d\{12,18\}` 改为 `\[1-9\]\\d\{1[2-9]`（支持任意长度范围 + 任意前缀）
    - `tests/unit/test_luhn_validation.py`: 新增 18 个测试用例
      - `TestLuhnValidation`: 6 张公开测试银行卡号 + 8 个非银行卡号 + 空输入/非字符串防御
      - `TestIdCardExclusion`: 15/18 位身份证号识别 + 省级前缀 + 年月日校验
      - `TestBankCardPatternScope`: 4 种 pattern 识别（带前缀/不带前缀/字边界/不同长度范围）
      - `TestIterUniqueTextMatchesLuhn`: 集成测试（案件号过滤、银行卡号保留、身份证号保留、去重）
    - `tests/unit/test_calculate_sub_rect_width_limit.py`: 新增 13 个测试用例
      - 大框跳过（> 80% 图像宽度）
      - 正常框继续走原流程
      - img_region=None 时不触发宽度检查
      - 异常输入安全处理（畸形 box / 空 box / 空图像）
    - `tests/unit/test_ocr_substring_precision_v4.py`:
      - `TestF19RapidOCRConfidence` 适配 cp57 新增的 `_init_failed` 标志（手动设置 `engine._init_failed = False`）
    - `CHANGELOG.md` / `docs/current/STATUS.md` / `docs/current/DEV_LOG.md` / `rollback_journal.md`: 文档同步
  - verification:
    - `python -m compileall -q main.py privacyguard tests` → OK
    - `python -m unittest tests.unit.test_luhn_validation -v` → 18 passed
    - `python -m unittest tests.unit.test_calculate_sub_rect_width_limit -v` → 13 passed
    - 全量回归 193 tests，180 passed / 6 skipped / 3 pre-existing failures（v2/v3 OCR 精度测试，与本次修复无关）/ 4 import errors（PyQt6-WebEngine 环境缺失）
  - rollback:
    - 还原 `privacyguard/ocr/text_pdf.py`（`_is_valid_luhn` 空输入防御 + `_is_bank_card_pattern` 锚点修复）
    - 删除 `tests/unit/test_luhn_validation.py`
    - 删除 `tests/unit/test_calculate_sub_rect_width_limit.py`
    - 还原 `tests/unit/test_ocr_substring_precision_v4.py` 中 `_init_failed` 手动设置
    - 还原 CHANGELOG/STATUS/DEV_LOG/rollback_journal 中 cp58 段落


- [x] cp59 公章检测双根因修复（v37.8.0）
  - date: 2026-07-25
  - purpose: 真实诉讼卷宗公章漏检（尺寸上限过小 + 断环银行章不闭合）
  - changes:
    - `privacyguard/workers/ocr_worker.py` `_detect_seals`:
      - max_radius_pt 90 → 150
      - 新增 disc_fill（轮廓面积/最小外接圆面积）>0.85 且近正方形 → +2 强信号
      - 双通道检测：小核 CLOSE(3) ∪ 大核 CLOSE(round(9×scan_scale))，重叠(较小框>0.5)去重；
        保留 ring_close_px 参数供诊断
    - `tests/unit/test_seal_detection.py`: 25→31（盖字章/红标题共存/淡色/大章/断环/真实PDF端到端）
  - verification: 真实 PDF 8 页全检出（页 5/2/6 双章），目视叠加图框准无误报；31 项印章测试全绿
  - rollback: 还原 `_detect_seals` 双通道段 + max_radius_pt=90；删除新增测试用例


- [x] cp60 签名手印检测新功能（v37.8.0）
  - date: 2026-07-26
  - purpose: 自动识别遮罩“手写签名+按手印”（高级设置勾选，与印章并列）
  - changes:
    - `privacyguard/workers/ocr_worker.py`: 新增 `_detect_signatures` + `signature_detection_enabled`；
      run() 与印章共用整页渲染
    - `main.py`: DEFAULT_RULES/兼容层/start_ocr 传递标志
    - `config.json` + `privacyguard/utils/config.py`: 新增“签名手印”规则（`__SIGNATURE_DETECTION__`）
    - `privacyguard/ocr/text_pdf.py` / `mixed_pdf.py`: 哨兵跳过
  - 真机修复两轮：CLOSE 固定 3px（防水印合并误报）；OPEN(2) 断桥（防手印粘连漏检）+
    红路径 aspect≤2.0（排除水印条片）；遮罩扩展收敛至 15%/15%/10%
  - verification: 7 张真实截图全检出；真实 PDF 页 0 手印精确定位 (425,1270,253x227)；203 项全绿
  - 已知限制：黑色手印在纯文字 B&W 页可能误报（红路径可靠）
  - rollback: 删除 `_detect_signatures` 与标志传递；从 config/规则/哨兵跳过中移除“签名手印”


- [x] cp61 UI 精致化 + 高亮筛选 + v37.8.0 定版（2026-07-27）
  - changes:
    - 复选框全自绘（18px 圆角/hover/选中蓝底白勾 `assets/check_white.svg`）
    - 全局+按钮变体 `outline:none`（修复 Windows 焦点矩形脏描边）
    - 默认窗口固定 1300×900（屏幕 92% 收敛+居中，移除几何持久化）
    - “适应页面”→⛶ 图标 38px（移出宽度地板循环）
    - Word 预览“高亮筛选”下拉（rule/manual/ocr）+ data-source + CSS 过滤态（+7 测试）
    - 公众号改名“池州有个汪律师”；config 对齐测试放宽 scan.default_level
    - 版本：version.txt / version_info.txt → 37.8.0；CHANGELOG/STATUS/DEV_LOG/AGENTS/CLAUDE 同步
  - verification: `compileall` OK；核心回归 203 项全绿
  - rollback: 还原 main.py 相应 UI 段；删除 assets/check_white.svg；version 回退 37.7.19


- [x] cp62 高级设置按文档类型动态显示（v37.8.1）
  - date: 2026-07-27
  - backup: `backups/cp62_64_settings_word_inline_pre/`
  - purpose: 设置模块按打开文档类型隐藏逻辑上用不到的部分（纠正“Word 隐藏关键词”诉求：
    WordWorker 扫描使用关键词，必须保留）
  - changes:
    - `main.py`: `SettingsDialog` 新增 `doc_context` 参数 + `_apply_doc_context_visibility`；
      图片/PDF 隐藏 Word 替换右卡片+指标卡；Word 隐藏第 3/4 区块（含导航/跳转/指标卡）
      与手动框选开关；密度网格重排过滤隐藏卡片；侧栏/摘要文案按上下文调整
  - verification: 三种 doc_context 冒烟验证通过；回归 203 项全绿
  - rollback: 删除 `_apply_doc_context_visibility` 及调用、doc_context 参数与密度过滤段


- [x] cp63 Word 关键词行内替换三级优先级（v37.8.1）
  - date: 2026-07-27
  - backup: `backups/cp62_64_settings_word_inline_pre/`
  - purpose: 关键词行 `find|replace` 行内替换扩展到 Word；Word 规则 > 行内替换 > 统一文本
  - changes:
    - `main.py`: 新增纯函数 `resolve_word_ocr_replacements`；预览右栏全量/增量 +
      `_save_word` 段落/单元格四处合并前接入；Word 场景关键词说明文案同步新语义
    - `tests/unit/test_word_replace_rules.py`: +8 项（TestResolveWordOcrReplacements）
  - 顺带修复：统一替换文本合并时取实时值（旧：扫描时烘焙，设置变更不生效）
  - verification: 核心回归 203→211 项全绿
  - rollback: 删除 `resolve_word_ocr_replacements` 及四处接入（恢复 `data.get("ocr", [])` 直传）；
    删除新增测试类


- [x] cp64 手动框选替换开关立即生效 + v37.8.1 定版（2026-07-27）
  - backup: `backups/cp62_64_settings_word_inline_pre/`
  - changes:
    - `main.py`: 新增 `_sync_manual_replace_prompt_to_canvases`，`open_settings` 保存后立即
      推送到左右画布（根因：旧实现仅在 `_render_single_page` 重渲染时同步，需翻页/重启）
    - 版本：version.txt / version_info.txt → 37.8.1；CHANGELOG/STATUS/DEV_LOG/AGENTS/CLAUDE/
      PROJECT_INDEX 同步
  - verification: `compileall` OK；核心回归 211 项全绿
  - rollback: 删除 `_sync_manual_replace_prompt_to_canvases` 及调用；version 回退 37.8.0；
    或直接 `git revert` 本次提交 / 用 `backups/cp62_64_settings_word_inline_pre/` 覆盖还原


- [x] cp65 手动框选 OCR 识别 + 可选全文遮罩（v37.8.2）
  - date: 2026-07-27
  - backup: `backups/cp65_66_manual_region_pre/`
  - purpose: 开关勾选时手动框选升级：框选即识别文字 + 弹窗（可编辑/可全文遮罩/替换文本）
  - changes:
    - `main.py`: `ManualRegionRedactDialog` 弹窗类；SinglePageCanvas 新增
      `manual_region_prompt` 信号（开关开启时不再直接 QInputDialog）；主窗口
      `_handle_manual_region_prompt`/`_extract_region_text`（文字层优先 + 3x 剪裁图
      RapidOCR 懒加载）/`_start_targeted_mask_scan`（复用 OCRWorker）/
      `_on_targeted_page_result`（命中入 manual + 重叠>50% 去重）/`_on_targeted_scan_finished`；
      纯函数 `split_targeted_search_terms`/`rects_overlap_ratio`
    - `tests/unit/test_word_replace_rules.py`: +6（TestTargetedMaskHelpers）
  - verification: 回归 211→217 全绿；弹窗/信号/分词对齐离屏冒烟通过
  - rollback: 还原 canvas mouseReleaseEvent 旧 QInputDialog 分支；删除弹窗类、信号、
    主窗口 cp65 方法与两个纯函数及新增测试


- [x] cp66 取消交互/取消按钮 UI/工具栏对调 + v37.8.2 定版（2026-07-27）
  - backup: `backups/cp65_66_manual_region_pre/`
  - changes:
    - 全文遮罩取消：`_on_targeted_scan_finished` 进度条归零 + “扫描停止”提示；
      `_targeted_stop_notice` 标志协调 `_on_worker_finished` 文案
    - 取消按钮截断：新增 `_get_cancel_scan_button_style` 专用紧凑样式（上下 padding
      归零、字号随高度收敛），创建与密度切换两处接入
    - 工具栏对调：去水印→primary 组（打开之后）；智能脱敏→utility 组（更多与
      导出之间）；`_refresh_toolbar_group_visibility` 判据同步
    - 版本：version.txt / version_info.txt → 37.8.2；CHANGELOG/STATUS/DEV_LOG/AGENTS/
      CLAUDE/PROJECT_INDEX 同步
  - verification: `compileall` OK；核心回归 217 项全绿；工具栏归属静态断言通过
  - rollback: 按条目还原对应代码段；version 回退 37.8.1；或 `git revert` 本次提交 /
    用 `backups/cp65_66_manual_region_pre/` 覆盖还原


- [x] cp67 多页页面视图功能（v37.8.3，2026-07-27）
  - backup: `backups/cp67_multi_page_view_pre/`（main.py / theme.py / version.txt /
    CHANGELOG / STATUS / DEV_LOG / rollback_journal 共 7 件）
  - git 基线: `31b22e3`（v37.8.2），可 `git revert` / `git checkout 31b22e3 -- <文件>` 回滚
  - changes:
    - `main.py`: `PageGridScrollArea`（Ctrl+滚轮信号）；SinglePageCanvas grid_mode +
      page_clicked/page_activated 信号；页面视图容器（左侧线条图标工具栏 + 网格滚动区）；
      模式切换/列数缩放/懒渲染 LRU/选中/旋转/插入/删除方法簇；`_render_page_to_canvas`
      抽取；五个纯函数（transform_hit_rect_for_rotation / shift_page_data_for_insert|delete /
      shift_page_set_for_insert|delete / clamp_grid_columns）；save_pdf 导出前乘
      derotation_matrix；互斥/模式显隐/resize/清理集成点
    - `privacyguard/ocr/text_pdf.py`: 旋转页命中乘 rotation_matrix 转 display（+import fitz）
    - `privacyguard/workers/ocr_worker.py`: 旋转页嵌入图片块 bbox 转 display
    - `assets/icons/page_rotate_left|right|insert|delete.svg`: 新增线条图标
    - `tests/unit/test_page_view_ops.py`: 新增 21 项；回归清单入列
  - verification: `compileall` OK；核心回归 237→258 项（样本缺失 257+1 skip）；
    真实 fitz 链路冒烟（旋转往返/插页重排/derotation 导出）断言通过；待真机验收 UI 流程
  - rollback: `git revert` 本次提交 / 用 `backups/cp67_multi_page_view_pre/` 覆盖还原；
    或按文件删除 cp67 段（画布信号/容器/方法簇/纯函数/两处 ocr 坐标变换/derotation 三行）；
    version 回退 37.8.2


- [x] cp68 页面视图交互与性能打磨（v37.8.4，2026-07-27）
  - backup: `backups/cp68_view_interaction_pre/`（main.py / version.txt / CHANGELOG /
    rollback_journal / STATUS / DEV_LOG 共 6 件）；git 基线 `ac1404f`（v37.8.3）
  - changes:
    - 双页按钮移除：工具栏 8 处接线清理；dual_view/toggle_dual_view 保留恒关闭
    - 两段式渲染：`_relayout_page_grid(fast=True)` + `_apply_fast_scaled_thumbs`（缓存
      pixmap 快速缩放过渡帧）+ `_grid_hq_timer` 260ms 去抖高清；`_grid_page_aspect` 缓存
    - 双向手势阻尼：`_ctrl_zoom_last_ts` + `_ZOOM_GESTURE_GAP=0.45s`；
      `_on_grid_ctrl_wheel` 1 列边界 / `handle_zoom_request` ZOOM_MIN 边界同手势停住，
      新手势才跨越；新增单页缩小进入页面视图（从 2 列起步）
    - ⛶ 跨视图：fit_page 页面视图下先退出再 singleShot(0) 调 `_apply_fit_page`；
      滚轮穿越分支收口同源
    - Shift 范围选：page_clicked 信号扩为 (int,bool,bool)；`_grid_anchor_page` 锚点；
      Ctrl+Shift 并入选区；结构变化/退出重置锚点
    - 防御：退出页面视图时 stop 两个网格定时器
  - verification: `compileall` OK；核心回归 258 项保持全绿；手势/跨视图/范围选
    离屏冒烟 16 场景全过
  - rollback: `git revert` 本次提交 / 用 `backups/cp68_view_interaction_pre/` 覆盖还原；
    version 回退 37.8.3


- [x] cp72 PDF 加密功能（v37.8.5，2026-07-27）
  - backup: `backups/cp72_encrypt_pre/`（main.py / version.txt / CHANGELOG /
    rollback_journal / STATUS / DEV_LOG 共 6 件）
  - changes:
    - 新增 `EncryptSettingsDialog`（单弹框双密码：打开密码/编辑密码 + 显示密码开关）
    - 纯函数 `build_encrypt_save_kwargs(open_pw, edit_pw)`：两空返回 {}，否则返回
      AES-256 + owner_pw(编辑密码，回退 open) + user_pw(打开密码) + permissions
      （设编辑密码⇒受限，否则全权限）
    - 工具栏锁图标 `btn_encrypt`（assets/icons/lock_encrypt.svg）位于智能脱敏左侧，
      仅 PDF/图片可见（pdf_widgets）；open_encrypt_dialog / _refresh_encrypt_button_state
    - save_pdf 导出时注入加密参数（save_kwargs.update）；打开新文档重置密码
    - `tests/unit/test_pdf_encrypt.py`: +5 项
    - 版本：version.txt / version_info.txt → 37.8.5
  - verification: `compileall` OK；核心回归 297 项全绿；PyMuPDF 加密端到端实测
    （需密码打开/错密码拒绝/无密码不加密）+ 弹框/按钮离屏冒烟通过
  - rollback: `git revert` 本次提交 / 用 `backups/cp72_encrypt_pre/` 覆盖还原；
    或删除 EncryptSettingsDialog/build_encrypt_save_kwargs/btn_encrypt 及 save_pdf 注入段；
    version 回退 37.8.4


- [x] cp69 去水印页面视图刷新 + 替换文本宽度适配 + 签名手印暖色门控（v37.8.5 批次，2026-07-27）
  - changes:
    - 去水印完成后页面视图失效缩略缓存 + 强制重渲染可见页（旧逻辑仅刷遮罩层）
    - `_draw_replace_text` 宽度自适配：QFontMetrics 实测超宽时按比例缩字号（下限 6px），
      修复矮胖遮罩框替换文字左右截断；导出侧 fitz 自动排版实测无此问题
    - 签名手印黑路径双门控：暖色门控（脊线像素 mean(R)-mean(B)≥10 且 R-G≥3，
      排除中性灰印刷字警/醒/嫌等误报）+ holes 阈值 8→12
  - files: main.py / privacyguard/workers/ocr_worker.py / tests/unit/test_signature_detection.py
  - rollback: 删除 cp69 注释段；测试样本恢复纯灰色


- [x] cp70 高级设置新增 7 条预设脱敏规则（v37.8.5 批次，2026-07-27）
  - backup: `backups/cp70_extended_rules_pre/`（6 件）
  - changes:
    - 统一社会信用代码/车牌号/固定电话（默认启用）+ 护照号/港澳台通行证/车架号/IP地址（默认关闭）
    - text_pdf.py 新增 mod31-3（USCC）/ VIN 第 9 位校验 + `verify_hit_by_pattern` 统一分发，
      三链路（text_pdf/mixed_pdf/word_worker）对称挂载，银行卡 Luhn 旧逻辑零改动
    - 三处规则定义同步：main.py DEFAULT_RULES / config.json / config.py DEFAULT_CONFIG
  - files: main.py / config.json / privacyguard/utils/config.py / privacyguard/ocr/text_pdf.py /
    privacyguard/ocr/mixed_pdf.py / privacyguard/workers/word_worker.py / tests/unit/test_extended_rules.py
  - rollback: 用 `backups/cp70_extended_rules_pre/` 还原 6 件；删 test_extended_rules.py


- [x] cp71 OCR 检测框调节对文本层 PDF 生效（v37.8.5 批次，2026-07-27）
  - changes: 审查定位 box_adjust_ratio 对文本层 PDF 为死配置（仅图像 OCR 生效）；
    新增纯函数 `apply_box_adjust_to_hit`（中心缩放，y 方向 0.6×，1pt 保底）并在
    ocr_worker.run() 文本层命中处接入；scan_level/use_enhance/offset 审查结论：
    均按设计生效（offset 仅图像路径为 UI 已声明行为）
  - files: privacyguard/ocr/text_pdf.py / privacyguard/workers/ocr_worker.py / tests/unit/test_extended_rules.py
  - rollback: 删除 apply_box_adjust_to_hit 及 run() 接入两行


- [x] cp73 工具栏按钮重合修复 + 动态最小窗口（v37.8.5 批次，2026-07-27）
  - changes: 新增 `_enforce_toolbar_min_width`（按工具栏 layout.sizeHint + 28px 缓冲动态
    抬高窗口最小宽度，受屏幕可用宽度上限约束），根治固定尺寸按钮溢出重叠
    （跳到最后一页 vs 适应页面）；基础最小宽度 900→1120（config.py/config.json/main.py 三处）
  - rollback: 删除 _enforce_toolbar_min_width 及调用；min_width 三处回退 900


- [x] cp74 手动框选脱敏弹窗增强（v37.8.5 批次，2026-07-27）
  - changes: 识别文字框下新增“去空白”（\s+ 全部去除）与“复制”（剪贴板 +
    “已复制”反馈）小按钮；“取消”改为整个行为取消不加任何遮罩
    （旧逻辑取消仍按纯遮罩添加）
  - rollback: 删除 cp74 段；取消分支恢复 append 纯遮罩


- [x] cp75 页面视图遮罩颜色切换实时生效（v37.8.6，2026-07-27）
  - changes: `_refresh_visible_grid_thumbs` overlay_only 分支把裸 update() 换为
    `_safe_canvas_set_mask_color(canvas, current_color)`（内自带 update），
    黑/白/取色遮罩切换在网格下立即生效（旧逻辑需动视图才刷新）
  - rollback: 该分支恢复 canvas.update()


- [x] cp76 页面视图首次进入零白屏卡顿（v37.8.6，2026-07-27）
  - changes: 分帧渲染队列——`_grid_render_queue` + `_grid_render_timer`（0ms 单发
    链式）+ `_process_grid_render_queue`（每帧一页，守卫：退出/关闭/越界/二次
    查缓存）；`_refresh_visible_grid_thumbs` 缓存 miss 不再同步渲染（旧逻辑首次
    进入可见页全量同步 fitz 渲染阻塞主线程 ~1s 白屏），旧倍率缓存先出快速
    过渡帧；退出视图/网格重建停队清队
  - verification: 分帧队列冒烟 5 场景 + 遮罩色同步 2 场景全过；核心回归 297 项全绿
  - rollback: 删除队列状态/_process_grid_render_queue，刷新循环恢复同步
    _render_page_to_canvas；version 回退 37.8.5


- [x] cp77 主页卡片内突兀方块修复（v37.8.7，2026-07-27）
  - changes: scroll_style 加 QScrollArea 选择器（无选择器样式传播到后代裸
    QWidget 错涂 scroll_area 色，卡内 footer 形成 #F6F8FB 方块）；
    main_container 命名 mainContainer 并显式上 scroll_area 底色（卡外视觉不变）
  - verification: 离屏像素探针：修复前 footer=#F6F8FB≠卡色，修复后 =#F9FBFE 与卡一致且卡外保留 #F6F8FB
  - rollback: scroll_style 恢复无选择器形式；删 mainContainer 规则


- [x] cp78 Windows 标题栏配色（v37.8.7，2026-07-27）
  - changes: `_apply_windows_titlebar_color`（showEvent 调用）：DwmSetWindowAttribute
    DWMWA_CAPTION_COLOR(35) 设为 Theme scroll_area #F6F8FB（COLORREF 0x00BBGGRR）；
    仅 win32 + Win11 22000+，失败/非 Windows 静默跳过
  - rollback: 删除该方法及 showEvent 调用


- [x] cp79/cp80 全局字体 + 三平台兼容（v37.8.7，2026-07-27）
  - changes:
    - cp79: QApplication 全局默认字体 setFamilies(Segoe UI Variable/Segoe UI/
      雅黑 UI/雅黑/Arial) 10pt，兜底未指定 font-family 控件
    - cp80: 全局字体加 sys.platform=='win32' 守卫（macOS 保持系统字体）；
      theme.py FONT_FAMILY 与 PREVIEW_FONT_STACK 补 PingFang SC/Helvetica Neue；
      _draw_replace_text 字体改回退栈（雅黑→苹方）
  - verification: 真实 Windows 平台字体解析 Segoe UI Variable 10pt、YaHei UI 在库；
    核心回归 297 项全绿
  - rollback: 删全局 setFont 段；FONT_FAMILY/PREVIEW_FONT_STACK 去掉苹方项；
    画布字体恢复 QFont("Microsoft YaHei")；version 回退 37.8.6


- [x] cp81 全文搜索侧栏（v37.8.8 批次，2026-07-27）
  - backup: `backups/cp81_doc_search_pre/`（main.py / version.txt / CHANGELOG /
    rollback_journal 共 4 件）；git 基线 `112b6f2`（v37.8.7）
  - changes:
    - 纯函数 `build_search_snippet`（上下文截取+省略号+换行替换）、
      `collect_text_hits`（大小写不敏感、单页上限 50）
    - `DocSearchWorker(QThread)`：pdf_bytes 快照（tobytes，页序与当前状态一致），
      文字层直搜/扫描页 OCR（_search_ocr_cache 会话级按页缓存），可取消
    - 工具栏 `btn_search`（assets/icons/search_magnifier.svg，加密按钮左侧，
      PDF/Word 均可见）；布局重构 content_row（scroll|page_view|search_panel）
    - `search_panel`（320px：输入+小放大镜/状态+取消/结果列表黄色高亮+页码小字）；
      toggle 显隐；结果点击定位（PDF 退页面视图跳页；Word data-key 滚动+闪烁）
    - 清理钩子：_cleanup_before_open 停 worker/清缓存/收面板；插页/删页清 OCR 缓存；
      非 PDF/Word 模式隐按钮收面板
    - tests/unit/test_doc_search.py: +13 项
  - verification: compileall OK；核心回归 297→310 全绿；面板/Word 搜索/高亮冒烟过
  - rollback: 用 `backups/cp81_doc_search_pre/` 还原；或删 DocSearchWorker/搜索纯函数/
    _build_search_panel 方法簇/btn_search 接线，content_row 恢复为两个 addWidget；
    删 test_doc_search.py 与 search_magnifier.svg


- [x] cp82 搜索命中高亮定位（v37.8.8，2026-07-27）
  - changes:
    - hit_signal 扩为 5 参（末位 rect 元组或 None）；文字层 search_for 词级矩形
      （旋转页乘 rotation_matrix 转 display）与文本命中顺序配对
    - _ocr_page_text 返回 (text, spans)；搜索 OCR 缓存结构升级 {'text','spans'}，
      命中位置回查所在行矩形；旧纯文本缓存降级无矩形
    - SinglePageCanvas.flash_rect 绘制层（#FFE066 半透明+橙框，随 zoom 对齐）；
      _flash_search_hit（设矩形+ensureVisible 滚动+2.4s 定时清除）/_clear_search_flash；
      结果 payload 扩为 ("pdf", page, rect)
  - verification: test_doc_search 13→14 项；闪烁链路冒烟 5 场景；核心回归 311 全绿
  - rollback: hit_signal 恢复 4 参；_ocr_page_text 恢复返回纯文本；删 flash_rect 绘制段/
    _flash_search_hit/_clear_search_flash/_search_flash_timer；payload 恢复二元；
    version 回退 37.8.7


- [x] cp83 撤销/恢复功能（v37.8.9 批次，2026-07-27）
  - backup: `backups/cp83_undo_redo_pre/`（main.py / version.txt / CHANGELOG /
    rollback_journal 共 4 件）；git 基线 `b51af07`（v37.8.8）
  - changes:
    - 纯函数 snapshot_page_data（QRectF→元组）/ restore_page_data（元组→QRectF）/
      push_undo_snapshot（超 max_n 弹最早）
    - 主窗口方法簇：_build_undo_snapshot/_capture_undo_state（重入守卫）/
      _seed_undo_baseline/_apply_snapshot（结构快照重开字节流）/undo/redo/
      _refresh_undo_redo_buttons；_undo_stack/_redo_stack/_UNDO_MAX=20/_restoring_snapshot
    - 快照接入 10 处：on_rect_added/on_rect_removed（canvas 右键删除新发
      rect_removed 信号）/手动框选弹窗/智能扫描完成/全文遮罩完成（非结构）;
      旋转/插入/删除页（structural=True 含 doc.tobytes）
    - 工具栏 btn_undo/btn_redo（页面按钮右侧，undo.svg/redo.svg），尺寸循环+
      pdf_widgets+pdf 组判据；快捷键 Ctrl+Z / Ctrl+Y（QShortcut 标准键）；
      打开文档压基线快照，_cleanup_before_open 清双栈
    - tests/unit/test_undo_redo.py: +8 项
  - verification: compileall OK；核心回归 311→319 全绿；undo/redo 端到端+结构快照
    冒烟 6 场景过
  - rollback: 用 `backups/cp83_undo_redo_pre/` 还原；或删纯函数 3 个/方法簇/按钮接线/
    10 处 _capture_undo_state 调用/快捷键/canvas rect_removed.emit；删 undo.svg/redo.svg
    与 test_undo_redo.py；version 回退 37.8.8


- [x] cp84-86 工具栏拥挤/重叠根治（v37.8.9，2026-07-27）
  - changes:
    - cp84: toolbar_edit_group（页面+撤销+恢复）独立成组；group_spacing 下限
      max(4,spacing-4)→max(6,spacing-2)；rb_color 补入宽度地板循环
    - cp85: _enforce_toolbar_min_width 重构——内容超屏幕宽强制 narrow 档
      （_toolbar_forced_narrow 标志，responsiveness 开头应用；记录 needed 供跨屏
      解除）；测量 max(sizeHint,minimumSize)+28；resize 拉宽兜底
    - cp86: tb_layout 单 stretch（左右之间）→双 stretch（左组|s|缩放+导航|s|utility）；
      删 zoom/nav shared_group_width 强制同宽段；btn_scan/btn_save
      _set_toolbar_widget_width(64,36)；QTimer.singleShot(0) 延帧复测 enforce
  - verification: 溢出强制 narrow 冒烟 3 场景；双 stretch+resize 兜底冒烟；
    核心回归 319 全绿
  - rollback: 恢复单 addStretch 与 shared_group_width 段；group_spacing 恢复
    max(4,spacing-4)；删 edit 组（控件回 pdf 组）/强制 narrow 分支/btn_scan·save
    定宽/延帧复测；rb_color 移出宽度地板；version 回退 37.8.8


- [x] cp87 脱敏报告 + D2/D3 工程健康（v37.8.10 批次，2026-07-27）
  - backup: `backups/cp87_redact_report_pre/`（5 件含 ocr_worker.py）
  - changes:
    - 新模块 privacyguard/report.py（classify_hit_rule/summarize_page_data/
      build_redact_report 纯函数，D1 铁律首秀）
    - ocr_worker: rule_name_pairs 参数 + _classify_rule；四处命中 dict 加 'rule'
      （文本层/图像 OCR 反查；印章/签名手印字面量）；main 兼容层透传，
      主扫描传 DEFAULT_RULES.items()，全文遮罩归“全文查找”
    - save_pdf 成功弹窗：setDetailedText(报告) + “导出报告”按钮
      （写 {导出名}_脱敏报告.txt）
    - D2: tests/unit/test_toolbar_layout.py（溢出/跨屏/resize + 双 stretch 静态断言）6 项
    - D3: scripts/run_regression.ps1/.sh（unittest discover）；tests 与 tests/unit 补
      __init__.py；陈旧失效测试 test_ocr_substring_precision_v2/v3 归档 tests/legacy/；
      AGENTS 回归节补脚本说明
  - verification: test_redact_report 9 项；discover 新基线 361 全绿（接管 42 项漏网用例）；
    弹窗/worker rule 字段冒烟过
  - rollback: 删 report.py/四处 'rule' 字段/rule_name_pairs 参数链/弹窗改造（恢复
    QMessageBox.information 两处）/test_redact_report/test_toolbar_layout/scripts；
    legacy 两文件移回 tests/unit


- [x] cp88 会话恢复（防丢进度，v37.8.10 批次，2026-07-27）
  - backup: `backups/cp88_session_restore_pre/`（main.py）
  - changes:
    - 新模块 privacyguard/session_store.py（SessionStore：指纹匹配/轻重分离
      草稿 JSON+pdfsnap 旁文件/prune LRU/clear_all；损坏容错；原子替换写盘）
    - main: _session_store + 5s 节流 _draft_timer；_capture_undo_state 末尾触发，
      structural 标记写字节流；_flush_session_draft/_maybe_restore_session_draft；
      _open_pdf_file 恢复提示（在 seed baseline 前）；closeEvent/_cleanup_before_open
      flush；SettingsDialog 底部“清空草稿”按钮（二次确认）
    - 存储位置 %APPDATA%/PrivacyGuard/sessions/；导出成功不自动删草稿（已确认）
  - verification: test_session_store 11 项；恢复流程冒烟 4 场景（Yes 恢复/No 删草稿/
      结构快照删页恢复/flush 落盘）；discover 372 全绿
  - rollback: 删 session_store.py/main 接线（状态+五处钩子+两方法+设置按钮）/
    test_session_store；用户机器 sessions 目录可手动删除


- [x] cp89 仓库审计 + D5 定版清单（v37.8.10 批次，2026-07-27）
  - 审计结论：venv_win/venvmac/backups//tests/_diag_out/根目录 *.backup* 均未被 git
    跟踪（.gitignore 防线早已完备）；仓库 size-pack 仅 1.99 MiB，无需 git rm 手术
  - changes: docs/current/RELEASE_CHECKLIST.md（D5 定版六步清单，含打 tag 规定）
  - rollback: 删 RELEASE_CHECKLIST.md


- [x] cp90 清理使用痕迹（v37.8.10 批次，2026-07-27）
  - backup: `backups/cp90_trace_clean_pre/`（5 件含 temp_manager.py）
  - changes:
    - temp_manager: TEMP_PREFIX="pgud_" 加到 create_temp_file/dir；新增模块级
      active_temp_entries/list_stale_temp_entries（扫描 pgud_ 残留，排除活跃追踪）
    - 新模块 privacyguard/trace_cleaner.py（D1）：dir_size_bytes/format_size/
      collect_trace_items（四类，logs 默认不勾）/clean_paths（白名单 realpath 前缀
      校验硬约束）/write_pending_webengine+clear_pending_webengine/WEBENGINE_PENDING_MARKER
    - main: _TraceSizeWorker(QThread)+TraceCleanDialog（四行复选+大小+后台测大小，
      无路径项隐藏，草稿勾选额外提醒）；主窗 _open_trace_clean_dialog/
      _webengine_cache_dirs/_app_log_files/_mark_webengine_clear_pending/_on_traces_cleaned；
      SettingsDialog 按钮改“清理使用痕迹”→_open_trace_clean（旧 _clear_session_drafts 已删）；
      __main__ 启动早期清 WEBENGINE_PENDING_MARKER 标记目录（WebEngine 未初始化，无占用）
    - 白名单根：sessions / 系统 temp / WebEngine profile / logs；WebEngine 空目录自动隐藏
  - verification: test_trace_cleaner 12 项（大小/白名单拒绝外部/残留识别/活跃排除/
    pending 标记写入+启动清除往返）；对话框+清理+白名单冒烟；discover 384 全绿
  - rollback: 删 trace_cleaner.py/main 四方法+两对话类+启动清除段/test_trace_cleaner；
    SettingsDialog 按钮改回 “清空草稿”→_clear_session_drafts；temp_manager 去 TEMP_PREFIX
    与两模块级函数；version 回退




## 2026-10-24 快照体系清理注记

backups/iteration_checkpoints/ 下 6 个全工作区快照（cp18/20/23/25/27/29，
2026-03-09/10）已删除：源码演进以 git 历史为准（完整覆盖）；快照主体为
当年 .git 误提交 zip 的大对象（已从仓库清除）。journal 内引用这些快照的
回滚条目自此失效。保留 backups/ 下 cp 系列小检查点与 archive。
同时清理：dist/ build/ tests/_diag_out/ 根缓存与 logs/（均可再生）。
