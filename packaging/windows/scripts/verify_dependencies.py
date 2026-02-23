#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency Verification Script for PrivacyGuard
Run this before building to ensure all required modules are installed.

Usage:
    python packaging/windows/scripts/verify_dependencies.py

Exit codes:
    0 - All dependencies OK
    1 - Missing dependencies
"""

import sys
from typing import Tuple

# Required modules with their import names and pip package names
REQUIRED_MODULES = [
    # (import_name, pip_package_name, description)
    ("bs4", "beautifulsoup4", "HTML parsing"),
    ("PyQt6", "PyQt6", "GUI framework"),
    ("PyQt6.QtWebEngineWidgets", "PyQt6-WebEngine", "Web engine for preview"),
    ("fitz", "PyMuPDF", "PDF processing"),
    ("docx", "python-docx", "Word document processing"),
    ("mammoth", "mammoth", "Word to HTML conversion"),
    ("cv2", "opencv-python", "Image processing for OCR"),
    ("numpy", "numpy", "Numerical computing"),
    ("rapidocr_onnxruntime", "rapidocr-onnxruntime", "OCR engine"),
    ("onnxruntime", "onnxruntime", "ONNX runtime for OCR"),
    ("PIL", "pillow", "Image processing"),
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

def check_bs4_collectable() -> bool:
    """
    Check if bs4 can be collected by PyInstaller.
    This verifies that bs4 is properly installed in the current environment.
    """
    print("Checking PyInstaller collectability...")

    try:
        from PyInstaller.utils.hooks import collect_all

        # Try to collect bs4 module
        datas, binaries, hiddenimports = collect_all('bs4')

        if not datas and not hiddenimports:
            print("  [WARN] collect_all('bs4') returned empty results")
            print("  [HINT] bs4 may not be properly installed")
            return False

        print(f"  [OK] bs4 collectable: {len(datas)} datas, {len(hiddenimports)} hidden imports")
        return True
    except ImportError:
        print("  [SKIP] PyInstaller not installed, skipping collectability check")
        return True
    except Exception as e:
        print(f"  [WARN] Error checking bs4 collectability: {e}")
        return False

def main():
    """Main entry point."""
    # Check basic dependencies
    deps_ok = verify_dependencies()

    # Check PyInstaller collectability if deps are OK
    if deps_ok:
        check_bs4_collectable()

    # Exit with appropriate code
    if deps_ok:
        print("Verification passed. Ready to build.")
        sys.exit(0)
    else:
        print("Verification failed. Please install missing dependencies.")
        sys.exit(1)

if __name__ == "__main__":
    main()
