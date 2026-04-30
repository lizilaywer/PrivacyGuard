# -*- coding: utf-8 -*-
"""
PyInstaller Runtime Hook for privacyguard
在运行时确保 privacyguard 模块路径正确
"""

import sys
import os

# 获取应用程序根目录（EXE 所在目录）
if getattr(sys, 'frozen', False):
    # 打包后的环境
    app_dir = os.path.dirname(sys.executable)
else:
    # 开发环境
    app_dir = os.path.dirname(os.path.abspath(__file__))

# 将 privacyguard 目录添加到 sys.path
privacyguard_paths = [
    app_dir,  # 根目录（包含 privacyguard 包）
    os.path.join(app_dir, 'privacyguard'),
    os.path.join(app_dir, 'privacyguard', 'utils'),
    os.path.join(app_dir, 'privacyguard', 'ocr'),
    os.path.join(app_dir, 'privacyguard', 'workers'),
]

for path in privacyguard_paths:
    if path not in sys.path and os.path.exists(path):
        sys.path.insert(0, path)

print(f"[RUNTIME HOOK] Added privacyguard paths to sys.path")
