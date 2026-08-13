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

    def _snapshot_privacyguard_modules(self):
        """Snapshot privacyguard.* modules for restoration after a test."""
        return {
            name: module
            for name, module in list(sys.modules.items())
            if name == "privacyguard" or name.startswith("privacyguard.")
        }

    def _restore_privacyguard_modules(self, cached):
        for name in list(sys.modules):
            if name == "privacyguard" or name.startswith("privacyguard."):
                sys.modules.pop(name, None)
        sys.modules.update(cached)

    def test_import_privacyguard_does_not_load_pii_engine(self):
        """OPS-03: import privacyguard 不应触发 privacyguard.pii.engine 模块加载。"""
        cached = self._snapshot_privacyguard_modules()
        for name in list(cached):
            sys.modules.pop(name, None)
        try:
            module = importlib.import_module("privacyguard")
            # 触发 _LAZY_IMPORTS 中已有的导出（不应触发 pii.engine）
            _ = module.validate_safe_path
            self.assertNotIn(
                "privacyguard.pii.engine",
                sys.modules,
                "import privacyguard 不得触发 privacyguard.pii.engine",
            )
        finally:
            self._restore_privacyguard_modules(cached)

    def test_pii_engine_loads_on_demand(self):
        """OPS-03: 主动访问 PIIEngine 触发隐私包懒加载。"""
        cached = self._snapshot_privacyguard_modules()
        for name in list(cached):
            sys.modules.pop(name, None)
        try:
            module = importlib.import_module("privacyguard")
            self.assertNotIn("privacyguard.pii.engine", sys.modules)
            # 访问 PIIEngine 触发 _LAZY_IMPORTS
            _ = module.PIIEngine
            self.assertIn(
                "privacyguard.pii.engine",
                sys.modules,
                "访问 privacyguard.PIIEngine 后 privacyguard.pii.engine 应被加载",
            )
        finally:
            self._restore_privacyguard_modules(cached)

    def test_pii_engine_lazy_under_rapidocr_block(self):
        """PII 引擎不得触发 rapidocr_onnxruntime 依赖加载。"""
        cached = self._snapshot_privacyguard_modules()
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
                # PII 引擎不应触发 rapidocr 导入
                _ = module.PIIEngine
                self.assertIn("privacyguard.pii.engine", sys.modules)
        finally:
            self._restore_privacyguard_modules(cached)

    # ------------------------------------------------------------------
    # Phase 2 (02-01-tracer) — 3 new lazy-load assertions
    # ------------------------------------------------------------------

    def test_import_privacyguard_does_not_load_new_validators(self):
        """OPS-03 扩展：import privacyguard 不应触发 3 个新 validator 子模块加载。"""
        cached = self._snapshot_privacyguard_modules()
        for name in list(cached):
            sys.modules.pop(name, None)
        try:
            module = importlib.import_module("privacyguard")
            # 触发 Phase 1 已有的导出（不应触发新 validator 子模块）
            _ = module.validate_safe_path
            self.assertNotIn(
                "privacyguard.pii.validators.uscc",
                sys.modules,
                "import privacyguard 不得触发 privacyguard.pii.validators.uscc",
            )
            self.assertNotIn(
                "privacyguard.pii.validators.bank_card",
                sys.modules,
                "import privacyguard 不得触发 privacyguard.pii.validators.bank_card",
            )
            self.assertNotIn(
                "privacyguard.pii.validators.email",
                sys.modules,
                "import privacyguard 不得触发 privacyguard.pii.validators.email",
            )
        finally:
            self._restore_privacyguard_modules(cached)

    def test_partial_masks_loads_on_demand(self):
        """主动访问 write_partial_masks 触发 pdf_adapter 懒加载。"""
        cached = self._snapshot_privacyguard_modules()
        for name in list(cached):
            sys.modules.pop(name, None)
        try:
            module = importlib.import_module("privacyguard")
            self.assertNotIn("privacyguard.pii.pdf_adapter", sys.modules)
            # 访问 write_partial_masks 触发 _LAZY_IMPORTS
            _ = module.write_partial_masks
            self.assertIn(
                "privacyguard.pii.pdf_adapter",
                sys.modules,
                "访问 privacyguard.write_partial_masks 后 privacyguard.pii.pdf_adapter 应被加载",
            )
        finally:
            self._restore_privacyguard_modules(cached)

    def test_clear_pdf_metadata_loads_on_demand(self):
        """主动访问 clear_pdf_metadata 触发 pdf_adapter 懒加载。"""
        cached = self._snapshot_privacyguard_modules()
        for name in list(cached):
            sys.modules.pop(name, None)
        try:
            module = importlib.import_module("privacyguard")
            self.assertNotIn("privacyguard.pii.pdf_adapter", sys.modules)
            # 访问 clear_pdf_metadata 触发 _LAZY_IMPORTS
            _ = module.clear_pdf_metadata
            self.assertIn(
                "privacyguard.pii.pdf_adapter",
                sys.modules,
                "访问 privacyguard.clear_pdf_metadata 后 privacyguard.pii.pdf_adapter 应被加载",
            )
        finally:
            self._restore_privacyguard_modules(cached)

    # ------------------------------------------------------------------
    # Phase 2 (02-03-main-py-settings-packaging) — bin_prefixes.json + LICENSE
    # ------------------------------------------------------------------

    def test_bin_prefixes_json_loadable_via_resource_path(self):
        """OPS-03 / D-26: bin_prefixes.json 必须通过 resource_path 加载，包含 >= 10000 unique 6 位 BIN 前缀；LICENSE 文件存在并包含 CC BY-SA 与 Wikipedia 归属声明。"""
        from privacyguard.utils.security import resource_path
        json_path = resource_path("privacyguard/pii/data/bin_prefixes.json")
        self.assertTrue(os.path.exists(json_path), f"bin_prefixes.json 不存在：{json_path}")
        import json as _json
        with open(json_path, "r", encoding="utf-8") as fh:
            data = _json.load(fh)
        bins = data.get("bin_prefixes", [])
        self.assertIsInstance(bins, list, "bin_prefixes 必须为 list")
        self.assertGreaterEqual(len(bins), 10000, f"bin_prefixes 数量 < 10000：{len(bins)}")
        # 防御性：所有条目必须为 6 位字符串
        for b in bins:
            self.assertIsInstance(b, str, f"bin entry 非字符串：{b!r}")
            self.assertEqual(len(b), 6, f"bin entry 非 6 位：{b!r}")
            self.assertTrue(b.isalnum(), f"bin entry 非纯字母数字：{b!r}")
        # LICENSE 归属声明（D-27 + CC BY-SA 4.0 强制）
        license_path = os.path.join(os.path.dirname(json_path), "bin_prefixes.json.LICENSE")
        self.assertTrue(os.path.exists(license_path), f"LICENSE 文件不存在：{license_path}")
        with open(license_path, "r", encoding="utf-8") as fh:
            license_text = fh.read()
        self.assertIn("CC BY-SA", license_text, "LICENSE 必须包含 'CC BY-SA' 归属声明")
        self.assertIn("Wikipedia", license_text, "LICENSE 必须包含 'Wikipedia' 来源声明")

    # ------------------------------------------------------------------
    # Phase 3 (03-word) — word_adapter 三函数懒加载纪律
    # ------------------------------------------------------------------

    def test_import_privacyguard_does_not_load_word_adapter(self):
        """OPS-03: import privacyguard 不应触发 privacyguard.pii.word_adapter 模块加载。"""
        cached = self._snapshot_privacyguard_modules()
        for name in list(cached):
            sys.modules.pop(name, None)
        try:
            module = importlib.import_module("privacyguard")
            _ = module.validate_safe_path
            self.assertNotIn(
                "privacyguard.pii.word_adapter",
                sys.modules,
                "import privacyguard 不得触发 privacyguard.pii.word_adapter (OPS-03)",
            )
        finally:
            self._restore_privacyguard_modules(cached)

    def test_collect_pii_word_hits_loads_word_adapter(self):
        """OPS-03: 通过 privacyguard.pii.collect_pii_word_hits 触发 word_adapter 懒加载。"""
        cached = self._snapshot_privacyguard_modules()
        for name in list(cached):
            sys.modules.pop(name, None)
        try:
            module = importlib.import_module("privacyguard")
            _ = module.validate_safe_path
            self.assertNotIn("privacyguard.pii.word_adapter", sys.modules)
            pii_pkg = importlib.import_module("privacyguard.pii")
            _ = pii_pkg.collect_pii_word_hits
            self.assertIn(
                "privacyguard.pii.word_adapter",
                sys.modules,
                "通过 privacyguard.pii.collect_pii_word_hits 应触发 word_adapter 加载 (D-13)",
            )
        finally:
            self._restore_privacyguard_modules(cached)