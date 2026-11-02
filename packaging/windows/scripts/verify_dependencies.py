#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency Verification Script for PrivacyGuard
Run this before building to ensure all required modules are installed
and properly collectable by PyInstaller.

Usage:
    python packaging/windows/scripts/verify_dependencies.py

Exit codes:
    0 - All dependencies OK
    1 - Missing dependencies or collect_all failures
"""

import sys
from typing import Tuple

# Required modules with their import names and pip package names
REQUIRED_MODULES = [
    # (import_name, pip_package_name, description)
    # cp114: 原生扩展模块（onnxruntime/cv2/fitz）必须在 PyQt6.QtWebEngineWidgets 之前检测，
    # 否则 Qt 自带的 DLL 与 onnxruntime 冲突导致 "DLL 初始化例程失败"
    ("onnxruntime", "onnxruntime", "ONNX runtime for OCR"),
    ("cv2", "opencv-python", "Image processing for OCR"),
    ("numpy", "numpy", "Numerical computing"),
    ("fitz", "PyMuPDF", "PDF processing"),
    ("bs4", "beautifulsoup4", "HTML parsing"),
    ("PyQt6", "PyQt6", "GUI framework"),
    ("PyQt6.QtWebEngineWidgets", "PyQt6-WebEngine", "Web engine for preview"),
    ("docx", "python-docx", "Word document processing"),
    ("mammoth", "mammoth", "Word to HTML conversion"),
    ("rapidocr", "rapidocr", "OCR engine (v3.x / PP-OCRv6)"),
    ("PIL", "pillow", "Image processing"),
    # cp113: 加密 Word 文档解密（懒导入于 privacyguard/utils/word_crypto.py）
    ("msoffcrypto", "msoffcrypto-tool", "Encrypted Word document decryption"),
    # cp114: RapidOCR 外部依赖（collect_all('rapidocr') 不收集这些，需单独声明）
    ("pyclipper", "pyclipper", "RapidOCR polygon clipping dependency"),
    ("shapely", "shapely", "RapidOCR geometry operations dependency"),
    ("omegaconf", "omegaconf", "RapidOCR configuration management dependency"),
    ("colorlog", "colorlog", "RapidOCR logging dependency"),
    ("six", "six", "RapidOCR compatibility dependency"),
    ("requests", "requests", "RapidOCR model download dependency"),
    # cp115: PyYAML —— omegaconf 运行时依赖（collect_all('omegaconf') 不含 yaml）
    ("yaml", "PyYAML", "YAML parser (omegaconf runtime dependency)"),
    # cp116: antlr4 —— omegaconf.grammar.gen 依赖（collect_all('omegaconf') 不含 antlr4）
    ("antlr4", "antlr4-python3-runtime", "ANTLR4 runtime (omegaconf grammar dependency)"),
    # cp115: psutil —— requirements.txt 声明，含平台二进制扩展
    ("psutil", "psutil", "System/process monitoring (onnxruntime transitive)"),
    # cp117: tqdm —— rapidocr 直接依赖（download_file.py:11 `from tqdm import tqdm`）
    ("tqdm", "tqdm", "Progress bar (rapidocr model download dependency)"),
    # cp117: cobble —— mammoth 依赖（mammoth -> cobble<0.2,>=0.1.3）
    ("cobble", "cobble", "Inflection lib (mammoth Word->HTML dependency)"),
]

# cp58: Modules that PyInstaller must collect_all correctly for OCR pipeline.
# If any of these return empty results, the packaged .exe will fail at runtime
# with ModuleNotFoundError or model/dll loading errors.
COLLECT_ALL_MODULES = [
    # (module_name, critical_for, expected_min_datas, expected_min_hidden)
    # bs4 - HTML parsing (mammoth dependency for Word preview)
    ("bs4", "Word HTML preview (mammoth parser)", 0, 0),
    # cv2 - image preprocessing in OCR pipeline
    ("cv2", "PDF OCR image preprocessing", 0, 0),
    # rapidocr - OCR engine (PP-OCRv6 models + runtime)
    ("rapidocr", "OCR engine (PP-OCRv6)", 1, 0),
    # onnxruntime - OCR model inference runtime
    ("onnxruntime", "OCR model inference", 0, 0),
    # numpy - required by cv2/rapidocr/onnxruntime
    ("numpy", "numpy 2.x core/_core compat", 0, 0),
    # cp113: msoffcrypto - 加密 Word 文档解密
    ("msoffcrypto", "Encrypted Word document decryption", 0, 0),
    # cp114: RapidOCR 外部依赖（collect_all('rapidocr') 不收集这些）
    ("pyclipper", "RapidOCR polygon clipping", 0, 0),
    ("shapely", "RapidOCR geometry operations", 0, 0),
    ("omegaconf", "RapidOCR config management", 0, 0),
    # cp115: PyYAML —— omegaconf 运行时依赖（collect_all('omegaconf') 不含 yaml）
    ("yaml", "YAML parser (omegaconf runtime)", 0, 0),
    # cp116: antlr4 —— omegaconf.grammar.gen 依赖（collect_all('omegaconf') 不含 antlr4）
    ("antlr4", "ANTLR4 runtime (omegaconf grammar)", 0, 0),
    # cp115: mammoth —— main.py:904 Word→HTML 预览转换
    ("mammoth", "Word to HTML conversion", 0, 0),
    # cp115: psutil —— 含平台二进制扩展
    ("psutil", "System/process monitoring", 0, 0),
    # cp117: tqdm —— rapidocr 直接依赖（download_file.py:11）
    ("tqdm", "Progress bar (rapidocr download)", 0, 0),
    # cp117: cobble —— mammoth 依赖
    ("cobble", "Inflection lib (mammoth dependency)", 0, 0),
]


def check_module(import_name: str) -> Tuple[bool, str]:
    """Check if a module can be imported."""
    try:
        __import__(import_name)
        return True, "OK"
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error: {e}"


def verify_dependencies() -> bool:
    """Verify all required dependencies are installed."""
    print("=" * 60)
    print("  PrivacyGuard Dependency Verification")
    print("=" * 60)
    print()

    missing = []
    errors = []

    print(f"{'Module':<35} {'Status':<10}")
    print("-" * 60)

    for import_name, pip_name, description in REQUIRED_MODULES:
        success, message = check_module(import_name)

        if success:
            print(f"{import_name:<35} {'OK':<10}")
        else:
            print(f"{import_name:<35} {'MISSING':<10}")
            missing.append((import_name, pip_name, description, message))

    print()
    print("=" * 60)

    if missing:
        print("  [ERROR] Missing dependencies detected!")
        print("=" * 60)
        print()
        print("Missing modules:")
        for import_name, pip_name, description, error in missing:
            print(f"  - {import_name} ({description})")
            print(f"    Install: pip install {pip_name}")
            print(f"    Error: {error}")
            print()

        print("To fix, run:")
        print("  pip install -r requirements.txt")
        print()
        return False
    else:
        print("  [OK] All dependencies verified!")
        print("=" * 60)
        print()
        return True


def check_collect_all(module_name: str, critical_for: str,
                      expected_min_datas: int = 0,
                      expected_min_hidden: int = 0) -> bool:
    """
    cp58: Check if a module can be properly collected by PyInstaller.

    collect_all returns (datas, binaries, hiddenimports). Empty results for
    OCR-related modules indicate the packaged .exe will fail at runtime with
    ModuleNotFoundError or model/DLL loading errors.
    """
    try:
        from PyInstaller.utils.hooks import collect_all
    except ImportError:
        print(f"  [SKIP] {module_name:<15} PyInstaller not installed")
        return True

    try:
        datas, binaries, hiddenimports = collect_all(module_name)
    except Exception as e:
        print(f"  [FAIL] {module_name:<15} collect_all raised: {type(e).__name__}: {e}")
        print(f"         critical for: {critical_for}")
        return False

    # Empty result check
    is_empty = (not datas) and (not binaries) and (not hiddenimports)
    if is_empty:
        print(f"  [WARN] {module_name:<15} collect_all returned all-empty (datas=0, binaries=0, hiddenimports=0)")
        print(f"         critical for: {critical_for}")
        print(f"         Hint: module may be missing from current environment, or path resolution failed")
        return False

    # Minimum expectation check
    if len(datas) < expected_min_datas:
        print(f"  [WARN] {module_name:<15} datas count {len(datas)} < expected {expected_min_datas}")
        print(f"         critical for: {critical_for}")
        print(f"         Hint: model/data files may be missing - reinstall {module_name}")
        return False

    if len(hiddenimports) < expected_min_hidden:
        print(f"  [WARN] {module_name:<15} hiddenimports count {len(hiddenimports)} < expected {expected_min_hidden}")
        print(f"         critical for: {critical_for}")
        return False

    print(f"  [OK]   {module_name:<15} datas={len(datas)} binaries={len(binaries)} hiddenimports={len(hiddenimports)}")
    return True


def check_pyinstaller_collectability() -> bool:
    """
    cp58: Check PyInstaller collect_all for all critical OCR modules.
    """
    print("=" * 60)
    print("  PyInstaller collect_all Verification (cp58)")
    print("=" * 60)
    print()

    try:
        from PyInstaller.utils.hooks import collect_all  # noqa: F401
    except ImportError:
        print("  [SKIP] PyInstaller not installed, skipping collectability check")
        print("         Install with: pip install pyinstaller")
        print()
        return True

    all_ok = True
    for module_name, critical_for, min_datas, min_hidden in COLLECT_ALL_MODULES:
        ok = check_collect_all(module_name, critical_for, min_datas, min_hidden)
        all_ok = all_ok and ok

    print()
    print("=" * 60)
    if all_ok:
        print("  [OK] All critical modules collectable by PyInstaller")
    else:
        print("  [FAIL] Some modules failed collect_all check")
        print("         The packaged .exe may fail at runtime.")
        print("         Fix: reinstall the failing module, e.g.")
        print("           pip install --force-reinstall rapidocr onnxruntime")
    print("=" * 60)
    print()
    return all_ok


def check_rapidocr_models() -> bool:
    """
    cp58: Verify that RapidOCR v3.x PP-OCRv6 model files are present.
    Missing model files cause silent OCR fallback to empty results.
    """
    print("=" * 60)
    print("  RapidOCR Model Files Verification (cp58)")
    print("=" * 60)
    print()

    try:
        import rapidocr
        import os
        rapidocr_path = os.path.dirname(rapidocr.__file__)
    except ImportError:
        print("  [SKIP] rapidocr not installed")
        print()
        return True

    # Common model file patterns for PP-OCRv4/v5/v6
    model_patterns = ['*.onnx', '*.onnx.txt']
    found_models = []
    for root, dirs, files in os.walk(rapidocr_path):
        for f in files:
            for pat in model_patterns:
                if f.endswith(pat.replace('*', '')):
                    found_models.append(os.path.relpath(os.path.join(root, f), rapidocr_path))

    if not found_models:
        print(f"  [FAIL] No .onnx model files found under {rapidocr_path}")
        print("         PP-OCRv6 models missing - OCR will silently return empty results")
        print("         Fix: pip install --force-reinstall rapidocr")
        print()
        return False

    print(f"  [OK]   Found {len(found_models)} model file(s) under rapidocr package")
    for m in found_models[:5]:
        print(f"         - {m}")
    if len(found_models) > 5:
        print(f"         ... and {len(found_models) - 5} more")
    print()
    return True


def main():
    """Main entry point."""
    # Check basic dependencies
    deps_ok = verify_dependencies()

    # cp58: Check PyInstaller collectability for OCR-critical modules
    collect_ok = True
    if deps_ok:
        collect_ok = check_pyinstaller_collectability()

    # cp58: Check RapidOCR model files are present
    models_ok = True
    if deps_ok:
        models_ok = check_rapidocr_models()

    # Exit with appropriate code
    if deps_ok and collect_ok and models_ok:
        print("Verification passed. Ready to build.")
        sys.exit(0)
    else:
        print("Verification failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
