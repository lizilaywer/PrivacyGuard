# -*- coding: utf-8 -*-
"""
PyInstaller hook for privacyguard package
强制包含所有子模块（修复 ModuleNotFoundError）

cp58: 同时防御性收集 OCR 关键依赖（rapidocr/onnxruntime/cv2）的数据文件，
避免 .spec 中遗漏导致打包后 .exe 运行时缺少模型/DLL 而崩溃。
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 收集 privacyguard 所有子模块
hiddenimports = collect_submodules('privacyguard')

# 如果 collect_submodules 返回空，手动添加所有子模块
# cp114: 同步 v37.8.11 全部模块（含 seal_detection/signature_detection/logger/helpers_*/word_crypto/report/session_store/trace_cleaner/search_worker/batch_replace_worker/mixins/dialogs/widgets）
if not hiddenimports:
    hiddenimports = [
        'privacyguard',
        'privacyguard.utils',
        'privacyguard.utils.security',
        'privacyguard.utils.config',
        'privacyguard.utils.exceptions',
        'privacyguard.utils.temp_manager',
        'privacyguard.utils.logger',
        'privacyguard.utils.doc_converter',
        'privacyguard.utils.helpers_pdf',
        'privacyguard.utils.helpers_word_rules',
        'privacyguard.utils.helpers_word_doc',
        'privacyguard.utils.helpers_word_preview',
        'privacyguard.utils.helpers_ui',
        'privacyguard.utils.word_crypto',
        'privacyguard.ocr',
        'privacyguard.ocr.base',
        'privacyguard.ocr.manager',
        'privacyguard.ocr.rapidocr',
        'privacyguard.ocr.text_pdf',
        'privacyguard.ocr.mixed_pdf',
        'privacyguard.ocr.seal_detection',
        'privacyguard.ocr.signature_detection',
        'privacyguard.workers',
        'privacyguard.workers.ocr_worker',
        'privacyguard.workers.word_worker',
        'privacyguard.workers.image_merge',
        'privacyguard.workers.batch_replace_worker',
        'privacyguard.workers.search_worker',
        'privacyguard.ui',
        'privacyguard.ui.widgets',
        'privacyguard.ui.mixins',
        'privacyguard.ui.mixins.page_view_mixin',
        'privacyguard.ui.mixins.word_preview_mixin',
        'privacyguard.ui.dialogs',
        'privacyguard.report',
        'privacyguard.session_store',
        'privacyguard.trace_cleaner',
    ]

# 收集 privacyguard 数据文件
datas = collect_data_files('privacyguard')

# cp58: 防御性收集 OCR 关键依赖的数据文件
# .spec 中已使用 collect_all 收集 rapidocr/onnxruntime/cv2，这里作为兜底，
# 防止 .spec 漏配或被误删时打包产物缺少必要的 model/dll/data 文件。
# 使用 collect_data_files 而非 collect_all，避免与 .spec 中的 binaries 收集冲突。
for _mod in ('rapidocr', 'onnxruntime', 'cv2'):
    try:
        _datas, _hidden = collect_data_files(_mod), collect_submodules(_mod)
        if _datas:
            datas.extend(_datas)
        if _hidden:
            hiddenimports.extend(_hidden)
        print(f"[HOOK] { _mod }: +{len(_datas)} datas, +{len(_hidden)} hidden imports")
    except Exception as _e:
        # 单个模块收集失败不阻断打包，但需打印警告
        print(f"[HOOK WARN] collect_data_files('{_mod}') failed: {_e}")

# 去重（datas 中可能存在与 .spec 重复的项，PyInstaller 会自动处理）
hiddenimports = list(set(hiddenimports))

print(f"[HOOK] Collected {len(hiddenimports)} privacyguard hidden imports")
print(f"[HOOK] Collected {len(datas)} privacyguard data files")
