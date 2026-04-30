#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证 privacyguard 模块语法"""

import ast
import sys

files_to_check = [
    'privacyguard/__init__.py',
    'privacyguard/utils/__init__.py',
    'privacyguard/utils/security.py',
    'privacyguard/utils/config.py',
    'privacyguard/utils/exceptions.py',
    'privacyguard/utils/temp_manager.py',
    'privacyguard/ocr/__init__.py',
    'privacyguard/ocr/base.py',
    'privacyguard/ocr/manager.py',
    'privacyguard/ocr/rapidocr.py',
    'privacyguard/ocr/text_pdf.py',
    'privacyguard/ocr/mixed_pdf.py',
    'privacyguard/workers/__init__.py',
    'privacyguard/workers/ocr_worker.py',
    'privacyguard/workers/word_worker.py',
    'privacyguard/workers/image_merge.py',
]

errors = []
for filepath in files_to_check:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        print(f"[OK] {filepath}")
    except SyntaxError as e:
        errors.append((filepath, str(e)))
        print(f"[ERROR] {filepath}: {e}")
    except FileNotFoundError:
        print(f"[SKIP] {filepath}: File not found")

if errors:
    print(f"\nTotal errors: {len(errors)}")
    sys.exit(1)
else:
    print("\nAll files passed syntax check!")
    sys.exit(0)
