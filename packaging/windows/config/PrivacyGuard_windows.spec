# -*- mode: python ; coding: utf-8 -*-
"""
PrivacyGuard Windows Build Spec File
PyInstaller Configuration - Enhanced for onnxruntime stability
"""

import sys
sys.setrecursionlimit(sys.getrecursionlimit() * 5)  # 修复 onnxruntime 递归深度问题

import os
import glob
from PyInstaller.utils.hooks import (
    copy_metadata,
    collect_all,
    collect_dynamic_libs,
    collect_data_files,
    collect_submodules,
)

# 获取路径 - spec 文件位置: packaging/windows/config/
# 项目根目录: 上溯 3 层
current_dir = os.path.dirname(os.path.abspath(SPEC))  # packaging/windows/config
windows_dir = os.path.dirname(current_dir)              # packaging/windows
packaging_dir = os.path.dirname(windows_dir)            # packaging
project_root = os.path.dirname(packaging_dir)           # PrivacyApp (项目根目录)

block_cipher = None

# 收集 onnxruntime 所有文件（修复 DLL 加载失败）
onnx_datas, onnx_binaries, onnx_hiddenimports = collect_all('onnxruntime')
rapid_datas, rapid_binaries, rapid_hiddenimports = collect_all('rapidocr')

# 收集 numpy 完整模块（修复 numpy 2.x core/_core 兼容层缺失）
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
numpy_submodules = collect_submodules('numpy')
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

# 收集 bs4 (BeautifulSoup) 完整模块（修复 ModuleNotFoundError）
# 注意：PyPI 包名是 beautifulsoup4，但导入名是 bs4
bs4_datas, bs4_binaries, bs4_hiddenimports = collect_all('bs4')

# cp113: 收集 msoffcrypto（加密 Word 文档解密，懒导入于 word_crypto.py）
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
# PyInstaller 静态分析也未追踪到（omegaconf 按需加载 grammar）。这是打包后
# "RapidOCR 引擎不可用"的根因：rapidocr.main → from omegaconf import DictConfig
# → omegaconf 加载 grammar → `from antlr4 import *` → ModuleNotFoundError
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

# 验证 bs4 收集结果（如果返回空，说明模块未安装）
if not bs4_datas and not bs4_hiddenimports:
    print("[ERROR] collect_all('bs4') returned empty results!")
    print("[ERROR] This usually means beautifulsoup4 is not installed in the virtual environment.")
    print("[ERROR] Please run: pip install beautifulsoup4")
    print("[ERROR] Or: pip install -r requirements.txt")
    # 不要直接退出，让 PyInstaller 继续运行，但会在运行时失败
    # 这样用户可以看到完整的错误信息
else:
    print(f"[INFO] bs4 collected: {len(bs4_datas)} datas, {len(bs4_hiddenimports)} hidden imports")

# 额外确保所有 bs4 子模块被收集
bs4_submodules = collect_submodules('bs4')
bs4_hiddenimports.extend(bs4_submodules)
# 收集 soupsieve（bs4 的依赖）
soupsieve_datas, soupsieve_binaries, soupsieve_hiddenimports = collect_all('soupsieve')
bs4_datas.extend(soupsieve_datas)
bs4_binaries.extend(soupsieve_binaries)
bs4_hiddenimports.extend(soupsieve_hiddenimports)
# 收集 lxml（bs4 的解析器）
lxml_datas, lxml_binaries, lxml_hiddenimports = collect_all('lxml')
bs4_datas.extend(lxml_datas)
bs4_binaries.extend(lxml_binaries)
bs4_hiddenimports.extend(lxml_hiddenimports)

# 额外收集 onnxruntime 的动态库（关键修复）
extra_onnx_binaries = collect_dynamic_libs('onnxruntime')

# 收集 VC++ 运行时 DLL（关键：解决 DLL 初始化失败）
vcrt_binaries = []
import site

# 方法1: 从 site-packages 收集 onnxruntime 的 DLL
for site_path in site.getsitepackages():
    onnx_path = os.path.join(site_path, 'onnxruntime')
    if os.path.exists(onnx_path):
        for dll_pattern in ['*.dll', '*.pyd']:
            dlls = glob.glob(os.path.join(onnx_path, '**', dll_pattern), recursive=True)
            for dll in dlls:
                vcrt_binaries.append((dll, os.path.dirname(dll).replace(site_path, '').strip(os.sep)))

# 方法2: 从系统目录收集 VC++ 运行时 DLL（确保打包包含）
vc_dlls = [
    'vcruntime140.dll',
    'vcruntime140_1.dll',
    'msvcp140.dll',
    'msvcp140_1.dll',
    'msvcp140_2.dll',
]
system32_path = os.path.join(os.environ.get('SYSTEMROOT', 'C:\\Windows'), 'System32')
for dll_name in vc_dlls:
    dll_path = os.path.join(system32_path, dll_name)
    if os.path.exists(dll_path):
        vcrt_binaries.append((dll_path, '.'))
        print(f"[INFO] Including system DLL: {dll_name}")

# 方法3: 尝试从 Python 安装目录收集 VC++ DLL
import sysconfig
python_base = os.path.dirname(sys.executable)
for dll_name in vc_dlls:
    # 检查 DLLs 目录
    dll_path = os.path.join(python_base, 'DLLs', dll_name)
    if os.path.exists(dll_path):
        vcrt_binaries.append((dll_path, '.'))
        print(f"[INFO] Including Python DLLs: {dll_name}")
    # 检查 Library/bin 目录 (conda/miniconda)
    dll_path = os.path.join(python_base, 'Library', 'bin', dll_name)
    if os.path.exists(dll_path):
        vcrt_binaries.append((dll_path, '.'))
        print(f"[INFO] Including Library/bin DLL: {dll_name}")

# 收集 PyQt6 WebEngine 相关 DLL（可能缺失）
pyqt6_binaries = collect_dynamic_libs('PyQt6', destdir='PyQt6/Qt6/bin')

# 收集 privacyguard 包的所有子模块（修复 ModuleNotFoundError）
privacyguard_hiddenimports = collect_submodules('privacyguard')
print(f"[INFO] Collected {len(privacyguard_hiddenimports)} privacyguard submodules")

# 注意：不要使用 collect_all 收集 privacyguard 的数据文件！
# 这会导致 .py 文件被作为数据文件复制，而不是作为 Python 模块处理
# 从而破坏模块导入机制

# 手动添加所有 privacyguard 子模块（确保完整）
# cp114: 同步 v37.8.11 新增模块（seal_detection/signature_detection/logger/helpers_*/word_crypto/report/session_store/trace_cleaner/search_worker/batch_replace_worker/mixins/dialogs/widgets）
privacyguard_hiddenimports.extend([
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
])

# 去重
privacyguard_hiddenimports = list(set(privacyguard_hiddenimports))
print(f"[INFO] Total privacyguard hidden imports after dedup: {len(privacyguard_hiddenimports)}")

print(f"[INFO] Collected {len(onnx_binaries)} onnxruntime binaries")
print(f"[INFO] Collected {len(extra_onnx_binaries)} extra onnxruntime libs")
print(f"[INFO] Collected {len(vcrt_binaries)} VC++ runtime files")
print(f"[INFO] Collected {len(numpy_binaries)} numpy binaries")
print(f"[INFO] Collected {len(numpy_hiddenimports)} numpy hidden imports")
print(f"[INFO] Collected {len(numpy_compat_datas)} numpy compatibility data dirs")
print(f"[INFO] Collected {len(bs4_binaries)} bs4 related binaries")
print(f"[INFO] Collected {len(bs4_submodules)} bs4 submodules")
print(f"[INFO] Collected {len(lxml_hiddenimports)} lxml hiddenimports")
print(f"[INFO] Collected {len(privacyguard_hiddenimports)} privacyguard submodules")

# v40.2.3 修复：config.json 是 git-ignored 的本地文件，新克隆/CI 构建时不存在，
# PyInstaller 对缺失 data 源直接 SystemExit——改为存在性守卫（运行时由
# config.json.template 回退初始化，见 main.py _init_from_template）。
# 注意：必须在 Analysis(...) 调用之前定义（spec 是 Python，参数列表中不能放赋值）
# Never distribute the builder's keywords, names, paths or other private settings.
_config_datas = []

a = Analysis(
    [os.path.join(project_root, 'main.py')],  # main.py 在项目根目录
    # cp119 约定：pathex 仅 project_root（+spec 所在目录）。禁止把 privacyguard
    # 子目录加进来——子目录中的 rapidocr.py 会被 ModuleGraph 注册为顶层模块
    # "rapidocr"，顶掉 pip 安装的第三方 rapidocr 包（同名冲突），运行时
    # privacyguard.ocr.rapidocr 的相对导入在"无父包"上下文执行直接 ImportError
    # （v40.2.3 打包实测即崩于此；mac spec 一直是对的，本行对齐之）
    pathex=[project_root, current_dir],
    binaries=onnx_binaries + rapid_binaries + extra_onnx_binaries + vcrt_binaries + pyqt6_binaries + numpy_binaries + bs4_binaries + msoff_binaries + rapidocr_dep_binaries + yaml_binaries + antlr4_binaries + mammoth_binaries + psutil_binaries + tqdm_binaries + cobble_binaries,
    datas=[
        # 包含主题文件
        (os.path.join(project_root, 'theme.py'), '.'),
        # cp114: 配置模板作为回退（config.json 存在时由 _config_datas 打包）
        (os.path.join(project_root, 'config.json.template'), '.'),
        # cp114: 版本文件（main.py:read_app_version 从 __file__ 同级读取，打包后需在 bundle 根目录）
        (os.path.join(project_root, 'version.txt'), '.'),
        # 包含 assets 目录（二维码图片等）
        (os.path.join(project_root, 'assets'), 'assets'),
    ] + _config_datas + onnx_datas + rapid_datas + numpy_datas + numpy_compat_datas + bs4_datas + msoff_datas + rapidocr_dep_datas + yaml_datas + antlr4_datas + mammoth_datas + psutil_datas + tqdm_datas + cobble_datas + copy_metadata('numpy'),  # 注意：不要包含 privacyguard_datas_all！
    hiddenimports=[
        # PyQt6
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel',
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
        # OCR - onnxruntime 完整导入链（修复 DLL 加载失败）
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi._pybind_state',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        # 主题
        'theme',
        # 其他
        'PIL',
        'PIL._imaging',
        'docx',
        # bs4 (BeautifulSoup) - 完整导入链
        'bs4',
        'bs4.builder',
        'bs4.builder._htmlparser',
        'bs4.builder._lxml',
        'bs4.element',
        'soupsieve',
        # lxml（bs4 解析器）
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
    ] + onnx_hiddenimports + rapid_hiddenimports + numpy_hiddenimports + bs4_hiddenimports + msoff_hiddenimports + rapidocr_dep_hiddenimports + yaml_hiddenimports + antlr4_hiddenimports + mammoth_hiddenimports + psutil_hiddenimports + tqdm_hiddenimports + cobble_hiddenimports + privacyguard_hiddenimports,
    hookspath=[current_dir],  # 包含 hook-privacyguard.py
    hooksconfig={},
    runtime_hooks=[os.path.join(current_dir, 'runtime_hook_privacyguard.py')],  # 运行时添加 privacyguard 路径
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'pandas',
        'scipy',
        'IPython',
        # 排除 macOS 专用模块
        'PyQt6.QtMacExtras',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

# v40.2.5: 剔除 PyQt6 wheel 自带的旧版 VC++ 运行库（MSVCP140 14.26，2020）。
# PyInstaller 启动时把 Qt6\bin 加入 AddDllDirectory，旧版 CRT 一旦抢先加载，
# 与 _internal 根的系统新版（14.44）混装——onnxruntime pyd 的 DllMain 在旧 CRT
# 上初始化失败（错误 1114 "动态链接库初始化例程失败"），进程退出再崩
# 0xc0000005（事件日志指认 Faulting Module = Qt6\bin\MSVCP140.dll）。
# 统一使用 _internal 根已显式收集的系统新版 CRT，根除混装。
_crt_dll_names = {'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
                  'msvcp140_atomic_wait.dll', 'vcruntime140.dll',
                  'vcruntime140_1.dll', 'concrt140.dll'}
_crt_before = len(a.binaries)
a.binaries = [b for b in a.binaries if not (
    '/pyqt6/qt6/bin/' in ('/' + b[0].replace('\\', '/').lower())
    and b[0].replace('\\', '/').rsplit('/', 1)[-1].lower() in _crt_dll_names
)]
print(f"[INFO] Removed {_crt_before - len(a.binaries)} legacy VC++ CRT copies from PyQt6/Qt6/bin")

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
    upx=False,  # 禁用 UPX 压缩（可能导致 DLL 加载失败）
    console=False,  # v37.0.6: 禁用控制台窗口，正常发布版本
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, 'assets', 'logo', 'windows', 'app_icon.ico'),
    version=os.path.join(current_dir, 'version_info.txt'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,  # 禁用 UPX 压缩（可能导致 DLL 加载失败）
    upx_exclude=[],
    name='PrivacyGuard',
)
