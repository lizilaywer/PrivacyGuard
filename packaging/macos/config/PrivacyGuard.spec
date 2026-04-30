# -*- mode: python ; coding: utf-8 -*-
"""
PrivacyGuard macOS 应用打包配置
PyInstaller Spec 文件
"""

import os
from PyInstaller.utils.hooks import collect_all

# 获取路径 - spec 文件位置: packaging/macos/config/
# 项目根目录: 上溯 3 层
current_dir = os.path.dirname(os.path.abspath(SPEC))  # packaging/macos/config
macos_dir = os.path.dirname(current_dir)               # packaging/macos
packaging_dir = os.path.dirname(macos_dir)             # packaging
project_root = os.path.dirname(packaging_dir)          # PrivacyApp (项目根目录)

block_cipher = None
version_file = os.path.join(project_root, 'version.txt')
with open(version_file, 'r', encoding='utf-8') as fh:
    app_version = fh.read().strip() or '0.0.0'

# collect_all 返回三元组: (datas, binaries, hiddenimports)
onnx_datas, onnx_binaries, onnx_hiddenimports = collect_all('onnxruntime')
rapid_datas, rapid_binaries, rapid_hiddenimports = collect_all('rapidocr_onnxruntime')
bs4_datas, bs4_binaries, bs4_hiddenimports = collect_all('bs4')
soupsieve_datas, soupsieve_binaries, soupsieve_hiddenimports = collect_all('soupsieve')
lxml_datas, lxml_binaries, lxml_hiddenimports = collect_all('lxml')

# 收集 privacyguard 包的所有子模块（修复 ModuleNotFoundError）
from PyInstaller.utils.hooks import collect_submodules
privacyguard_hiddenimports = collect_submodules('privacyguard')
print(f"[INFO] Collected {len(privacyguard_hiddenimports)} privacyguard submodules")

a = Analysis(
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root, current_dir],
    binaries=onnx_binaries + rapid_binaries + bs4_binaries + soupsieve_binaries + lxml_binaries,
    datas=[
        # 包含主题文件
        (os.path.join(project_root, 'theme.py'), '.'),
        # 包含配置文件
        (os.path.join(project_root, 'config.json'), '.'),
        # 包含 assets 目录（二维码图片等）
        (os.path.join(project_root, 'assets'), 'assets'),
    ] + onnx_datas + rapid_datas + bs4_datas + soupsieve_datas + lxml_datas,
    hiddenimports=[
        # PyQt6 相关
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel',
        'PyQt6.QtWebEngineCore',
        # 核心依赖
        'cv2',
        'fitz',  # PyMuPDF
        'numpy',
        'rapidocr_onnxruntime',
        # OCR 相关
        'onnxruntime',
        # 主题系统
        'theme',
        # 其他可能的隐藏导入
        'PIL',
        'PIL._imaging',
        'docx',
        'bs4',
        'bs4.builder',
        'bs4.element',
        'soupsieve',
        'lxml',
        'lxml.etree',
        # privacyguard 包（修复 ModuleNotFoundError）
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
    ] + onnx_hiddenimports + rapid_hiddenimports + bs4_hiddenimports + soupsieve_hiddenimports + lxml_hiddenimports + privacyguard_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'pandas',
        'scipy',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

# 过滤掉不需要的共享库
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PrivacyGuard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PrivacyGuard',
)

app = BUNDLE(
    coll,
    name='PrivacyGuard.app',
    icon=os.path.join(project_root, 'assets', 'logo', 'macos', 'AppIcon.icns'),
    bundle_identifier='com.privacyguard.app',
    info_plist={
        'CFBundleName': 'PrivacyGuard',
        'CFBundleDisplayName': 'PrivacyGuard 脱敏卫士',
        'CFBundleVersion': app_version,
        'CFBundleShortVersionString': app_version,
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'CFBundleExecutable': 'PrivacyGuard',
        'CFBundleIdentifier': 'com.privacyguard.app',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeExtensions': ['pdf', 'PDF'],
                'CFBundleTypeName': 'PDF Document',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate'
            },
            {
                'CFBundleTypeExtensions': ['docx', 'DOCX'],
                'CFBundleTypeName': 'Word Document',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate'
            },
            {
                'CFBundleTypeExtensions': ['doc', 'DOC'],
                'CFBundleTypeName': 'Word Document (Legacy)',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate'
            },
            {
                'CFBundleTypeExtensions': ['png', 'PNG', 'jpg', 'JPG', 'jpeg', 'JPEG'],
                'CFBundleTypeName': 'Image',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate'
            }
        ],
        'NSCameraUsageDescription': '需要访问摄像头以进行实时脱敏处理',
        'NSPhotoLibraryUsageDescription': '需要访问相册以进行脱敏处理',
    },
)
