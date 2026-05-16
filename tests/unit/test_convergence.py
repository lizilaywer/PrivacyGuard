"""
v37.7.6: 重复实现收敛回归测试

验证 main.py 中的 Worker 和工具函数正确委托给共享模块，
不再保留独立的重复实现。
"""

import ast
import re
import unittest
from pathlib import Path

MAIN_PY = Path(__file__).resolve().parents[2] / "main.py"


class TestImageMergeWorkerConvergence(unittest.TestCase):
    """验证 ImageMergeWorker 使用共享模块，不再保留内联定义。"""

    def test_main_py_imports_shared_image_merge_worker(self):
        """main.py 应导入共享 ImageMergeWorker。"""
        source = MAIN_PY.read_text(encoding="utf-8")
        self.assertIn("from privacyguard.workers.image_merge import ImageMergeWorker",
                       source, "main.py 应从共享模块导入 ImageMergeWorker")

    def test_main_py_has_no_inline_image_merge_worker_class(self):
        """main.py 不应再包含内联的 ImageMergeWorker 类定义。"""
        source = MAIN_PY.read_text(encoding="utf-8")
        # 查找 "class ImageMergeWorker" 但不是导入行
        for i, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("class ImageMergeWorker"):
                # 允许注释掉的行
                self.fail(f"main.py 第 {i} 行仍包含内联 ImageMergeWorker 类定义")


class TestWordWorkerConvergence(unittest.TestCase):
    """验证 WordWorker 使用共享模块，仅保留薄兼容层。"""

    def test_main_py_imports_shared_word_worker(self):
        """main.py 应导入共享 WordWorker。"""
        source = MAIN_PY.read_text(encoding="utf-8")
        self.assertIn("from privacyguard.workers.word_worker import WordWorker",
                       source, "main.py 应从共享模块导入 WordWorker")

    def test_main_py_word_worker_is_thin_compat_layer(self):
        """main.py 中的 WordWorker 应仅为继承兼容层，不包含 run/_find_matches 等方法。"""
        source = MAIN_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "WordWorker":
                method_names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                # 兼容层只应有 __init__
                self.assertIn("__init__", method_names,
                             "WordWorker 兼容层应有 __init__")
                self.assertNotIn("run", method_names,
                                 "WordWorker 兼容层不应包含 run 方法")
                self.assertNotIn("_find_matches", method_names,
                                 "WordWorker 兼容层不应包含 _find_matches 方法")
                self.assertNotIn("_get_rule_name", method_names,
                                 "WordWorker 兼容层不应包含 _get_rule_name 方法")
                return
        self.fail("main.py 中未找到 WordWorker 类定义")


class TestDocConverterConvergence(unittest.TestCase):
    """验证 DOC 转换逻辑提取到共享模块。"""

    def test_shared_doc_converter_module_exists(self):
        """privacyguard/utils/doc_converter.py 应存在。"""
        path = Path(__file__).resolve().parents[2] / "privacyguard" / "utils" / "doc_converter.py"
        self.assertTrue(path.exists(), "共享 DOC 转换模块应存在")

    def test_shared_doc_converter_exports_key_functions(self):
        """共享模块应导出 convert_doc_to_docx, resolve_soffice_cmd 等函数。"""
        from privacyguard.utils.doc_converter import (
            convert_doc_to_docx,
            convert_with_libreoffice,
            convert_with_antiword,
            resolve_soffice_cmd,
        )
        self.assertTrue(callable(convert_doc_to_docx))
        self.assertTrue(callable(convert_with_libreoffice))
        self.assertTrue(callable(convert_with_antiword))
        self.assertTrue(callable(resolve_soffice_cmd))

    def test_main_py_imports_shared_doc_converter(self):
        """main.py 应导入共享 DOC 转换模块。"""
        source = MAIN_PY.read_text(encoding="utf-8")
        self.assertIn("from privacyguard.utils.doc_converter import",
                       source, "main.py 应导入共享 DOC 转换模块")

    def test_main_py_has_no_inline_resolve_soffice_cmd(self):
        """WordBatchReplaceWorker 不应再保留内联的 _resolve_soffice_cmd。"""
        source = MAIN_PY.read_text(encoding="utf-8")
        # 在 WordBatchReplaceWorker 内部不应有 _resolve_soffice_cmd 方法定义
        self.assertNotIn("def _resolve_soffice_cmd(self)", source,
                         "main.py 不应保留内联 _resolve_soffice_cmd 方法")


class TestVersionFallbackAlignment(unittest.TestCase):
    """验证版本回退值一致。"""

    def test_main_py_version_fallback_matches_current(self):
        """main.py 的 read_app_version() 回退值应为当前版本。"""
        from main import read_app_version
        version_txt = (Path(__file__).resolve().parents[2] / "version.txt").read_text(encoding="utf-8").strip()
        # 回退值等于当前版本（因为 version.txt 存在时不会用到回退值）
        # 但我们验证硬编码的回退值与 version.txt 一致
        source = MAIN_PY.read_text(encoding="utf-8")
        match = re.search(r'return "(\d+\.\d+\.\d+)"', source)
        self.assertTrue(match, "main.py 应包含版本回退值")
        fallback = match.group(1)
        self.assertEqual(fallback, version_txt,
                         f"版本回退值 {fallback} 应与 version.txt {version_txt} 一致")

    def test_privacyguard_init_version_fallback_matches_main(self):
        """privacyguard/__init__.py 的版本回退值应与 main.py 一致。"""
        init_path = Path(__file__).resolve().parents[2] / "privacyguard" / "__init__.py"
        init_source = init_path.read_text(encoding="utf-8")
        main_source = MAIN_PY.read_text(encoding="utf-8")
        main_match = re.search(r'return "(\d+\.\d+\.\d+)"', main_source)
        init_match = re.search(r'return "(\d+\.\d+\.\d+)"', init_source)
        self.assertTrue(main_match, "main.py 应包含版本回退值")
        self.assertTrue(init_match, "privacyguard/__init__.py 应包含版本回退值")
        self.assertEqual(main_match.group(1), init_match.group(1),
                         "两处版本回退值应一致")


if __name__ == "__main__":
    unittest.main()
