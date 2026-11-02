# -*- coding: utf-8 -*-
"""
PyInstaller Runtime Hook for privacyguard

cp119 重大修复：移除子包目录（privacyguard/utils, /ocr, /workers）的 sys.path 注入。
此前把这些子包目录插到 sys.path[0]，会导致 Python 把子包内的 .py 文件当作
顶层裸模块加载，从而破坏相对导入（rapidocr.py:19 `from .base import` 报
"attempted relative import with no known parent package"），表现为打包后
"RapidOCR 引擎不可用"。

PyInstaller 的 PYZ 已将 privacyguard 作为完整包（含 __init__.py 与全部子模块）
打入 bundle，app_dir 本就在 sys.path 中，无需也无法通过注入子包目录来"帮忙"——
那只会破坏包的 __path__ 上下文。这里仅保留 app_dir（开发态兼容），其余全部删除。
"""

import sys
import os

if getattr(sys, 'frozen', False):
    # 打包后：EXE 所在目录已在 sys.path，此处仅为显式保证（幂等）
    app_dir = os.path.dirname(sys.executable)
else:
    # 开发环境（此 hook 一般不在开发态运行，保留兜底）
    app_dir = os.path.dirname(os.path.abspath(__file__))

if app_dir not in sys.path:
    sys.path.insert(0, app_dir)
