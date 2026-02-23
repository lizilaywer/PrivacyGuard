# -*- mode: python ; coding: utf-8 -*-
"""
PrivacyGuard Windows Build Spec File
PyInstaller Configuration - Enhanced for onnxruntime stability
"""

import sys
sys.setrecursionlimit(sys.getrecursionlimit() * 5)  # 修复 onnxruntime 递归深度问题

import os
import glob
from PyInstaller.utils.hooks import copy_metadata, collect_all, collect_dynamic_libs

# 获取路径 - spec 文件位置: packaging/windows/config/
# 项目根目录: 上溯 3 层
current_dir = os.path.dirname(os.path.abspath(SPEC))  # packaging/windows/config
windows_dir = os.path.dirname(current_dir)              # packaging/windows
packaging_dir = os.path.dirname(windows_dir)            # packaging
project_root = os.path.dirname(packaging_dir)           # PrivacyApp (项目根目录)

block_cipher = None

# 收集 onnxruntime 所有文件（修复 DLL 加载失败）
onnx_datas, onnx_binaries, onnx_hiddenimports = collect_all('onnxruntime')
rapid_datas, rapid_binaries, rapid_hiddenimports = collect_all('rapidocr_onnxruntime')

# 收集 bs4 (BeautifulSoup) 完整模块（修复 ModuleNotFoundError）
# 注意：PyPI 包名是 beautifulsoup4，但导入名是 bs4
from PyInstaller.utils.hooks import collect_submodules
bs4_datas, bs4_binaries, bs4_hiddenimports = collect_all('bs4')

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

print(f"[INFO] Collected {len(onnx_binaries)} onnxruntime binaries")
print(f"[INFO] Collected {len(extra_onnx_binaries)} extra onnxruntime libs")
print(f"[INFO] Collected {len(vcrt_binaries)} VC++ runtime files")
print(f"[INFO] Collected {len(bs4_binaries)} bs4 related binaries")
print(f"[INFO] Collected {len(bs4_submodules)} bs4 submodules")
print(f"[INFO] Collected {len(lxml_hiddenimports)} lxml hiddenimports")

a = Analysis(
    [os.path.join(project_root, 'main.py')],  # main.py 在项目根目录
    pathex=[project_root, current_dir],
    binaries=onnx_binaries + rapid_binaries + extra_onnx_binaries + vcrt_binaries + pyqt6_binaries + bs4_binaries,
    datas=[
        # 包含主题文件
        (os.path.join(project_root, 'theme.py'), '.'),
        # 包含配置文件
        (os.path.join(project_root, 'config.json'), '.'),
        # 包含 assets 目录（二维码图片等）
        (os.path.join(project_root, 'assets'), 'assets'),
    ] + onnx_datas + rapid_datas + bs4_datas,
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
        'rapidocr_onnxruntime',
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
    ] + onnx_hiddenimports + rapid_hiddenimports + bs4_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    icon=os.path.join(windows_dir, 'assets', 'icon.ico'),
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
