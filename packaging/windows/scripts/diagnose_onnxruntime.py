#!/usr/bin/env python3
"""
诊断 onnxruntime DLL 依赖问题
在 Windows 打包环境中运行此脚本检查 DLL 状态
"""

import sys
import os
import subprocess

def print_section(title):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def check_python_version():
    print_section("Python 版本信息")
    print(f"Python: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"Platform: {sys.platform}")

def check_onnxruntime():
    print_section("onnxruntime 信息")
    try:
        import onnxruntime
        print(f"Version: {onnxruntime.__version__}")
        print(f"Location: {onnxruntime.__file__}")

        # 检查 capi 目录
        capi_dir = os.path.join(os.path.dirname(onnxruntime.__file__), 'capi')
        print(f"\nCAPI Directory: {capi_dir}")
        if os.path.exists(capi_dir):
            files = os.listdir(capi_dir)
            print(f"Files: {files}")

            # 检查关键 DLL
            pyd_files = [f for f in files if f.endswith('.pyd')]
            print(f"\nPYD files: {pyd_files}")

            for pyd in pyd_files:
                pyd_path = os.path.join(capi_dir, pyd)
                print(f"\n  Checking: {pyd}")
                print(f"    Size: {os.path.getsize(pyd_path)} bytes")

                # 尝试使用 dumpbin 检查依赖
                try:
                    result = subprocess.run(
                        ['dumpbin', '/dependents', pyd_path],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print(f"    Dependencies (dumpbin):")
                        for line in result.stdout.split('\n'):
                            if '.dll' in line.lower():
                                print(f"      {line.strip()}")
                except FileNotFoundError:
                    print("    (dumpbin not found - install Visual Studio)")
        else:
            print("ERROR: capi directory not found!")

    except ImportError as e:
        print(f"ERROR: Cannot import onnxruntime: {e}")

def check_vcredist():
    print_section("VC++ Redistributable 检查")

    system32 = os.path.join(os.environ.get('SYSTEMROOT', 'C:\\Windows'), 'System32')

    required_dlls = {
        'vcruntime140.dll': 'VC++ 2015-2019 Runtime',
        'vcruntime140_1.dll': 'VC++ 2019-2022 Runtime (CRITICAL for onnxruntime 1.16+)',
        'msvcp140.dll': 'C++ Standard Library',
        'msvcp140_1.dll': 'C++ Standard Library Extension 1',
        'msvcp140_2.dll': 'C++ Standard Library Extension 2',
    }

    all_found = True
    for dll, description in required_dlls.items():
        dll_path = os.path.join(system32, dll)
        if os.path.exists(dll_path):
            size = os.path.getsize(dll_path)
            version = get_file_version(dll_path)
            print(f"  ✓ {dll} ({description})")
            print(f"    Path: {dll_path}")
            print(f"    Size: {size} bytes")
            if version:
                print(f"    Version: {version}")
        else:
            print(f"  ✗ {dll} ({description}) - MISSING")
            all_found = False

    if not all_found:
        print("\n" + "!" * 50)
        print("WARNING: 某些必需的 VC++ DLL 缺失!")
        print("请下载并安装: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        print("!" * 50)

def get_file_version(file_path):
    """尝试获取文件版本信息"""
    try:
        import ctypes
        wapi = ctypes.windll.version
        filename = ctypes.c_char_p(file_path.encode('utf-8'))
        dwLen = wapi.GetFileVersionInfoSizeA(filename, None)
        if dwLen == 0:
            return None

        buf = ctypes.create_string_buffer(dwLen)
        wapi.GetFileVersionInfoA(filename, 0, dwLen, buf)

        uLen = ctypes.c_uint(0)
        lpBuffer = ctypes.c_char_p(None)
        wapi.VerQueryValueA(buf, b"\\VarFileInfo\\Translation", ctypes.byref(lpBuffer), ctypes.byref(uLen))

        if uLen.value == 0:
            return None

        # 读取版本信息
        lang_codepage = lpBuffer.value[:4]
        str_info_path = f"\\StringFileInfo\\{lang_codepage.hex().upper()}\\FileVersion".encode('ascii')

        ret = wapi.VerQueryValueA(buf, str_info_path, ctypes.byref(lpBuffer), ctypes.byref(uLen))
        if ret:
            return lpBuffer.value.decode('utf-8')
    except:
        pass
    return None

def check_import_chain():
    print_section("导入链测试")

    tests = [
        ("onnxruntime", "import onnxruntime"),
        ("onnxruntime.capi", "from onnxruntime import capi"),
        ("onnxruntime.capi._pybind_state", "from onnxruntime.capi import _pybind_state"),
        ("onnxruntime.capi.onnxruntime_pybind11_state", "from onnxruntime.capi import onnxruntime_pybind11_state"),
    ]

    for name, code in tests:
        try:
            exec(code)
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")

def test_inference():
    print_section("onnxruntime 推理测试")
    try:
        import onnxruntime as ort
        print(f"Available providers: {ort.get_available_providers()}")

        # 尝试创建一个简单的会话
        import numpy as np

        # 创建一个简单的 ONNX 模型（常量加法）
        # 这里我们只是测试运行时是否能加载
        sess_options = ort.SessionOptions()
        sess_options.log_severity_level = 0  # Verbose logging

        print("\n尝试创建 InferenceSession...")
        # 如果这里失败，说明 DLL 有问题
        print("Session options created successfully")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def suggest_fixes():
    print_section("建议的修复方案")

    print("""
1. 安装 VC++ Redistributable 2015-2022:
   https://aka.ms/vs/17/release/vc_redist.x64.exe

2. 如果已经安装但仍然失败，尝试修复安装:
   控制面板 -> 程序和功能 -> Microsoft Visual C++ Redistributable -> 修复

3. 对于 PyInstaller 打包问题:
   - 使用 diagnose_onnxruntime.py 确认所有 DLL 都存在
   - 尝试使用 PrivacyGuard_windows_v2.spec 重新打包
   - 确保打包环境和运行环境使用相同的 VC++ 版本

4. 如果问题仍然存在，尝试降级 onnxruntime:
   pip uninstall onnxruntime
   pip install onnxruntime==1.15.1

5. 使用 Dependency Walker 工具分析:
   https://github.com/lucasg/Dependencies
   分析 _pybind_state.pyd 的依赖链
""")

if __name__ == '__main__':
    print("PrivacyGuard onnxruntime 诊断工具")
    print(f"运行时间: {__import__('datetime').datetime.now()}")

    check_python_version()
    check_vcredist()
    check_onnxruntime()
    check_import_chain()
    test_inference()
    suggest_fixes()

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)
