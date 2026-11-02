# -*- mode: python ; coding: utf-8 -*-
"""
PrivacyGuard macOS 应用打包配置
PyInstaller Spec 文件
"""

import os
import sys
from PyInstaller.utils.hooks import collect_all

# v40.2.3 修复：同步 Windows spec 的递归深度提升（onnxruntime 模块图分析
# 在默认递归上限下可能 RecursionError，Windows 侧已踩过坑）
sys.setrecursionlimit(sys.getrecursionlimit() * 5)

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
rapid_datas, rapid_binaries, rapid_hiddenimports = collect_all('rapidocr')
bs4_datas, bs4_binaries, bs4_hiddenimports = collect_all('bs4')
soupsieve_datas, soupsieve_binaries, soupsieve_hiddenimports = collect_all('soupsieve')
lxml_datas, lxml_binaries, lxml_hiddenimports = collect_all('lxml')

# cp114: numpy 2.x core/_core 兼容层（与 Windows spec 对齐）
from PyInstaller.utils.hooks import collect_submodules as _collect_submodules
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
numpy_submodules = _collect_submodules('numpy')
numpy_hiddenimports.extend(numpy_submodules)
numpy_compat_datas = []
try:
    import numpy as _numpy
    numpy_path = os.path.dirname(_numpy.__file__)
    for rel_name in ('core', '_core'):
        compat_path = os.path.join(numpy_path, rel_name)
        if os.path.exists(compat_path):
            numpy_compat_datas.append((compat_path, f'numpy/{rel_name}'))
            print(f"[INFO] Including numpy compatibility package: numpy/{rel_name}")
except Exception as exc:
    print(f"[WARN] Failed to collect numpy compatibility directories: {exc}")

# cp113: msoffcrypto（加密 Word 文档解密，懒导入于 word_crypto.py）
msoff_datas, msoff_binaries, msoff_hiddenimports = collect_all('msoffcrypto')

# cp114: 收集 RapidOCR 的全部外部依赖（collect_all('rapidocr') 只收集 rapidocr 自身子模块，
# 不收集 pyclipper/Shapely/omegaconf 等外部依赖 → 打包后 from rapidocr import RapidOCR 失败）
_rapidocr_dep_names = ['pyclipper', 'shapely', 'omegaconf', 'colorlog', 'six', 'requests']
rapidocr_dep_datas = []
rapidocr_dep_binaries = []
rapidocr_dep_hiddenimports = []
for _dep in _rapidocr_dep_names:
    try:
        _d, _b, _h = collect_all(_dep)
        rapidocr_dep_datas.extend(_d)
        rapidocr_dep_binaries.extend(_b)
        rapidocr_dep_hiddenimports.extend(_h)
        print(f"[INFO] Collected RapidOCR dependency: {_dep} ({len(_d)} datas, {len(_h)} hiddenimports)")
    except Exception as _e:
        print(f"[WARN] Failed to collect RapidOCR dependency '{_dep}': {_e}")

# cp115: PyYAML —— omegaconf（RapidOCR 依赖）运行时必须 import yaml，
# 但 collect_all('omegaconf') 返回的 22 个 hiddenimports 中不含 yaml，PyInstaller 也不会自动追踪，
# 缺失会导致打包后 from rapidocr import RapidOCR 时 omegaconf 加载失败
yaml_datas, yaml_binaries, yaml_hiddenimports = collect_all('yaml')
print(f"[INFO] Collected PyYAML: {len(yaml_datas)} datas, {len(yaml_hiddenimports)} hiddenimports")

# cp116: antlr4-python3-runtime —— omegaconf.grammar.gen.OmegaConfGrammarLexer
# 顶部 `from antlr4 import *`，但 collect_all('omegaconf') 不含 antlr4（外部依赖），
# PyInstaller 静态分析也未追踪到。这是打包后 "RapidOCR 引擎不可用" 的根因：
# rapidocr.main → from omegaconf import DictConfig → omegaconf 加载 grammar
# → `from antlr4 import *` → ModuleNotFoundError
antlr4_datas, antlr4_binaries, antlr4_hiddenimports = collect_all('antlr4')
print(f"[INFO] Collected antlr4: {len(antlr4_datas)} datas, {len(antlr4_hiddenimports)} hiddenimports")

# cp115: mammoth —— main.py:904 直接 import mammoth 用于 Word→HTML 预览转换，
# 必须显式 collect_all 以包含其内部数据文件（图片转换器等）
mammoth_datas, mammoth_binaries, mammoth_hiddenimports = collect_all('mammoth')
print(f"[INFO] Collected mammoth: {len(mammoth_datas)} datas, {len(mammoth_hiddenimports)} hiddenimports")

# cp115: psutil —— requirements.txt 声明的运行时依赖（onnxruntime 内存监控等可能间接使用），
# 含平台特定的二进制扩展，必须显式收集
psutil_datas, psutil_binaries, psutil_hiddenimports = collect_all('psutil')
print(f"[INFO] Collected psutil: {len(psutil_datas)} datas, {len(psutil_hiddenimports)} hiddenimports")

# cp117: tqdm —— rapidocr 直接依赖（rapidocr/utils/download_file.py:11 `from tqdm import tqdm`），
# RapidOCR() 初始化时加载 download_file 模块（校验/下载模型），tqdm 缺失会导致
# ModuleNotFoundError → 整条 rapidocr 导入链失败 → OCREngineUnavailableError。
# collect_all('rapidocr') 不含 tqdm（外部依赖），PyInstaller 也未追踪到。
tqdm_datas, tqdm_binaries, tqdm_hiddenimports = collect_all('tqdm')
print(f"[INFO] Collected tqdm: {len(tqdm_datas)} datas, {len(tqdm_hiddenimports)} hiddenimports")

# cp117: cobble —— mammoth 的依赖（mammoth -> cobble<0.2,>=0.1.3），Word→HTML 预览转换需要。
# 此前仅在 hiddenimports 中声明（纯 Python 包），但 collect_all 更稳妥（含 dist-info 元数据）。
cobble_datas, cobble_binaries, cobble_hiddenimports = collect_all('cobble')
print(f"[INFO] Collected cobble: {len(cobble_datas)} datas, {len(cobble_hiddenimports)} hiddenimports")

# 收集 privacyguard 包的所有子模块（修复 ModuleNotFoundError）
from PyInstaller.utils.hooks import collect_submodules
privacyguard_hiddenimports = collect_submodules('privacyguard')
print(f"[INFO] Collected {len(privacyguard_hiddenimports)} privacyguard submodules")

# v40.2.3 修复：config.json 是 git-ignored 的本地文件，新克隆/CI 构建时不存在，
# PyInstaller 对缺失 data 源直接 SystemExit——改为存在性守卫（运行时由
# config.json.template 回退初始化）。必须在 Analysis(...) 调用之前定义。
# Never distribute the builder's keywords, names, paths or other private settings.
_config_datas = []

a = Analysis(
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root, current_dir],
    binaries=onnx_binaries + rapid_binaries + bs4_binaries + soupsieve_binaries + lxml_binaries + numpy_binaries + msoff_binaries + rapidocr_dep_binaries + yaml_binaries + antlr4_binaries + mammoth_binaries + psutil_binaries + tqdm_binaries + cobble_binaries,
    datas=[
        # 包含主题文件
        (os.path.join(project_root, 'theme.py'), '.'),
        # cp114: 配置模板作为回退（config.json 存在时由 _config_datas 打包）
        (os.path.join(project_root, 'config.json.template'), '.'),
        # cp114: 版本文件（main.py:read_app_version 从 __file__ 同级读取，打包后需在 bundle 根目录）
        (os.path.join(project_root, 'version.txt'), '.'),
        # 包含 assets 目录（二维码图片等）
        (os.path.join(project_root, 'assets'), 'assets'),
    ] + _config_datas + onnx_datas + rapid_datas + bs4_datas + soupsieve_datas + lxml_datas + numpy_datas + numpy_compat_datas + msoff_datas + rapidocr_dep_datas + yaml_datas + antlr4_datas + mammoth_datas + psutil_datas + tqdm_datas + cobble_datas,
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
        'numpy.core',
        'numpy.core._exceptions',
        'numpy.core.multiarray',
        'numpy._core',
        'numpy._core._exceptions',
        'numpy._core.multiarray',
        'numpy._core._multiarray_umath',
        'numpy.linalg',
        'numpy.random',
        'numpy.random._pickle',
        'rapidocr',
        # OCR 相关
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi._pybind_state',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        # 主题系统
        'theme',
        # 其他可能的隐藏导入
        'PIL',
        'PIL._imaging',
        'docx',
        'mammoth',
        'bs4',
        'bs4.builder',
        'bs4.builder._htmlparser',
        'bs4.builder._lxml',
        'bs4.element',
        'soupsieve',
        'lxml',
        'lxml.etree',
        'lxml._elementpath',
        # cp113: msoffcrypto（加密 Word 文档解密，懒导入于 word_crypto.py）
        'msoffcrypto',
        # privacyguard 包（修复 ModuleNotFoundError）
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
        # cp114: RapidOCR 外部依赖（collect_all 已收集，额外声明确保 PyInstaller 分析链覆盖）
        'pyclipper',
        'shapely',
        'shapely.geometry',
        'omegaconf',
        'colorlog',
        'six',
        'requests',
        # cp115: PyYAML（omegaconf 运行时依赖，collect_all('omegaconf') 不含 yaml）
        'yaml',
        # cp116: antlr4（omegaconf.grammar.gen 依赖，collect_all('omegaconf') 不含 antlr4）
        'antlr4',
        'antlr4.atn',
        'antlr4.dfa',
        'antlr4.error',
        'antlr4.tree',
        'antlr4.xpath',
        # cp115: mammoth（main.py:904 Word→HTML 预览转换）
        'mammoth',
        # cp115: psutil（requirements.txt 声明，含平台二进制扩展）
        'psutil',
        # cp117: tqdm（rapidocr 直接依赖，download_file.py:11 `from tqdm import tqdm`）
        'tqdm',
        # cp117: cobble（mammoth 依赖，Word→HTML 预览转换需要）
        'cobble',
        'cobble.inflection',
        # cp115: 传递依赖防御性声明（均无 PyInstaller 内置 hook，防止动态导入遗漏）
        'flatbuffers',  # onnxruntime 模型序列化
        'sympy',        # onnxruntime 形状推理
        'sympy.core',
        'mpmath',       # sympy 依赖
        'packaging',    # 通用版本解析
        'typing_extensions',  # 类型兼容层
    ] + onnx_hiddenimports + rapid_hiddenimports + bs4_hiddenimports + soupsieve_hiddenimports + lxml_hiddenimports + numpy_hiddenimports + msoff_hiddenimports + rapidocr_dep_hiddenimports + yaml_hiddenimports + antlr4_hiddenimports + mammoth_hiddenimports + psutil_hiddenimports + tqdm_hiddenimports + cobble_hiddenimports + privacyguard_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'pandas',
        'scipy',
        'IPython',
        # GUI app does not use Tcl/Tk or terminal line editing. Homebrew copies
        # of these optional libraries may require the builder's newest macOS.
        'tkinter', '_tkinter', 'turtle', 'readline',
        # decimal.py falls back to stdlib _pydecimal; avoid a host libmpdec link.
        '_decimal',
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
        # v40.2.3 修正：依赖链实际要求（onnxruntime/numpy 的 arm64 wheel 为
        # macosx_14_0，PyQt6-Qt6 为 macosx_11_0）——取最严的 14.0；
        # 且当前仅支持 Apple Silicon（arm64 wheel）
        'LSMinimumSystemVersion': '14.0',
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
