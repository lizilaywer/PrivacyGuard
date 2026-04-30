import builtins
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


class TestPrivacyGuardImports(unittest.TestCase):

    def test_import_privacyguard_without_rapidocr_runtime(self):
        cached = {
            name: module
            for name, module in list(sys.modules.items())
            if name == "privacyguard" or name.startswith("privacyguard.")
        }
        for name in list(cached):
            sys.modules.pop(name, None)

        original_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name.startswith("rapidocr_onnxruntime"):
                raise ImportError("blocked for import smoke test")
            return original_import(name, globals, locals, fromlist, level)

        try:
            with patch("builtins.__import__", side_effect=guarded_import):
                module = importlib.import_module("privacyguard")
        finally:
            for name in list(sys.modules):
                if name == "privacyguard" or name.startswith("privacyguard."):
                    sys.modules.pop(name, None)
            sys.modules.update(cached)

        self.assertTrue(hasattr(module, "validate_safe_path"))
        expected_version = (Path(__file__).resolve().parents[2] / "version.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(module.__version__, expected_version)
