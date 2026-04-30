# -*- coding: utf-8 -*-
"""
PyInstaller hook for privacyguard package
强制包含所有子模块（修复 ModuleNotFoundError）
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 收集所有子模块
hiddenimports = collect_submodules('privacyguard')

# 如果 collect_submodules 返回空，手动添加所有子模块
if not hiddenimports:
    hiddenimports = [
        'privacyguard',
        'privacyguard.utils',
        'privacyguard.utils.security',
        'privacyguard.utils.config',
        'privacyguard.utils.exceptions',
        'privacyguard.utils.temp_manager',
        'privacyguard.ocr',
        'privacyguard.ocr.base',
        'privacyguard.ocr.manager',
        'privacyguard.ocr.rapidocr',
        'privacyguard.ocr.text_pdf',
        'privacyguard.ocr.mixed_pdf',
        'privacyguard.workers',
        'privacyguard.workers.ocr_worker',
        'privacyguard.workers.word_worker',
        'privacyguard.workers.image_merge',
        'privacyguard.core',
        'privacyguard.ui',
    ]

# 收集数据文件
datas = collect_data_files('privacyguard')

print(f"[HOOK] Collected {len(hiddenimports)} privacyguard hidden imports")
print(f"[HOOK] Collected {len(datas)} privacyguard data files")
