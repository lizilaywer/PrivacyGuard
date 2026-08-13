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


class TestPiiConvergence(unittest.TestCase):
    """验证 PII 逻辑在 privacyguard.pii.* 内，main.py 不应重复实现。"""

    def test_main_py_does_not_inline_pii_detection(self):
        """main.py 不应包含内联 PII 检测函数（v37.7.6 收敛原则）。"""
        source = MAIN_PY.read_text(encoding="utf-8")
        self.assertNotIn("def detect_pii(self)", source,
                         "main.py 不应保留内联 PII 检测函数")
        self.assertNotIn("def validate_id_card(", source,
                         "main.py 不应保留内联身份证校验函数")

    def test_main_py_does_not_inline_pii_hit_class(self):
        """main.py 不应包含内联 PIIHit 类定义。"""
        source = MAIN_PY.read_text(encoding="utf-8")
        for i, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("class PIIHit"):
                self.fail(f"main.py 第 {i} 行仍包含内联 PIIHit 类定义: {stripped}")

    def test_pii_package_has_no_qt_dependency(self):
        """privacyguard/pii/*.py 不应 import PyQt6（保持纯 Python / 不引入 GUI 依赖）。"""
        pii_dir = Path(__file__).resolve().parents[2] / "privacyguard" / "pii"
        self.assertTrue(pii_dir.exists(), "privacyguard/pii 应存在")
        forbidden = ("PyQt6", "PyQt5", "QThread", "QObject", "pyqtSignal", "QWidget")
        for py_file in pii_dir.rglob("*.py"):
            # 跳过 __init__.py 的注释/文档字符串可能提及 Qt；只扫描 import / from 行
            source = py_file.read_text(encoding="utf-8")
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    for kw in forbidden:
                        if kw in stripped:
                            self.fail(
                                f"{py_file.relative_to(pii_dir.parent.parent)} 第 {i} 行含禁用的 Qt 依赖 '{kw}': {stripped}"
                            )

    def test_pii_package_has_no_network_dependency(self):
        """ENGINE-08: privacyguard/pii/*.py 不应 import 网络库（零网络）。"""
        pii_dir = Path(__file__).resolve().parents[2] / "privacyguard" / "pii"
        forbidden = ("urllib", "requests", "httpx", "socket", "aiohttp")
        for py_file in pii_dir.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    for kw in forbidden:
                        if kw in stripped:
                            self.fail(
                                f"{py_file.relative_to(pii_dir.parent.parent)} 第 {i} 行含禁用的网络依赖 '{kw}': {stripped}"
                            )

    def test_pii_engine_uses_pdf_redact_image_pixels(self):
        """SAFE-01: pdf_adapter.apply_pii_redactions 必须显式传 images=fitz.PDF_REDACT_IMAGE_PIXELS（=2）。"""
        adapter_path = Path(__file__).resolve().parents[2] / "privacyguard" / "pii" / "pdf_adapter.py"
        source = adapter_path.read_text(encoding="utf-8")
        self.assertIn(
            "PDF_REDACT_IMAGE_PIXELS",
            source,
            "apply_pii_redactions 必须显式传 images=fitz.PDF_REDACT_IMAGE_PIXELS（=2，非默认 0）",
        )
        # 仅扫描模块 docstring 之外的行；docstring 中允许提及 page.draw_rect 作为禁止说明
        # 通过 ast 提取 docstring 范围之外的代码行
        import ast as _ast
        tree = _ast.parse(source)
        doc_end = 0
        if tree.body and isinstance(tree.body[0], _ast.Expr) and isinstance(tree.body[0].value, _ast.Constant):
            doc_end = tree.body[0].end_lineno  # type: ignore[attr-defined]
        for i, line in enumerate(source.splitlines(), 1):
            if i <= doc_end:
                continue
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "page.draw_rect" in line:
                self.fail(
                    f"pdf_adapter.py 第 {i} 行调用了 page.draw_rect（假脱敏，违反 SAFE-01）: {stripped}"
                )

    def test_pii_hit_field_order_is_locked(self):
        """D-05: PIIHit 字段顺序锁定（entity_type, page_offset, page_length, page_rect, confidence_tier, source, mask_strategy）。"""
        import inspect
        from privacyguard.pii.hits import PIIHit
        sig = inspect.signature(PIIHit)
        names = list(sig.parameters.keys())
        expected = [
            'entity_type', 'page_offset', 'page_length', 'page_rect',
            'confidence_tier', 'source', 'mask_strategy',
        ]
        self.assertEqual(names[:7], expected,
                         f"PIIHit 前 7 字段顺序应为 {expected}，实际为 {names[:7]}")

    # ------------------------------------------------------------------
    # Phase 2 (02-01-tracer) — convergence 扩展
    # ------------------------------------------------------------------

    def test_main_py_does_not_inline_new_validators(self):
        """Phase 2: main.py 不应包含内联 USCC / 银行卡 / 邮箱 / partial mask / metadata clear 函数。"""
        source = MAIN_PY.read_text(encoding="utf-8")
        forbidden_patterns = [
            "def validate_uscc(",
            "def validate_bank_card(",
            "def validate_email(",
            "def write_partial_masks(",
            "def clear_pdf_metadata(",
        ]
        for pat in forbidden_patterns:
            self.assertNotIn(
                pat, source,
                f"main.py 不应保留内联 {pat} 实现（v37.7.6 收敛原则）",
            )

    def test_pii_package_no_inline_partial_mask_writer(self):
        """Phase 2: write_partial_masks + clear_pdf_metadata 必须在 pdf_adapter.py。"""
        from pathlib import Path as _Path
        pdf_adapter_path = _Path(__file__).resolve().parents[2] / "privacyguard" / "pii" / "pdf_adapter.py"
        source = pdf_adapter_path.read_text(encoding="utf-8")
        self.assertIn(
            "def write_partial_masks(", source,
            "write_partial_masks 必须在 pdf_adapter.py",
        )
        self.assertIn(
            "def clear_pdf_metadata(", source,
            "clear_pdf_metadata 必须在 pdf_adapter.py",
        )
        # 扫描 pii 子包其他 .py 文件 — write_partial_masks / clear_pdf_metadata 不应被定义在其他文件
        pii_dir = _Path(__file__).resolve().parents[2] / "privacyguard" / "pii"
        for py_file in pii_dir.rglob("*.py"):
            if py_file.name == "pdf_adapter.py":
                continue
            # 跳过 __init__.py 的 lazy import 注册条目
            other_source = py_file.read_text(encoding="utf-8")
            self.assertNotIn(
                "def write_partial_masks(", other_source,
                f"{py_file.relative_to(pii_dir.parent.parent)} 不应定义 write_partial_masks",
            )
            self.assertNotIn(
                "def clear_pdf_metadata(", other_source,
                f"{py_file.relative_to(pii_dir.parent.parent)} 不应定义 clear_pdf_metadata",
            )

    # ------------------------------------------------------------------
    # Phase 2 (02-03-main-py-settings-packaging) — main.py 必须调用 helpers
    # ------------------------------------------------------------------

    def test_main_py_uses_write_partial_masks_in_save_loop(self):
        """Phase 2 (02-04 WR-03 fix): main.py save_pdf 必须 AST-调用 write_partial_masks + clear_pdf_metadata。

        WR-03 fix: 旧版只检查字符串存在（'write_partial_masks' in source），无法区分
        import 与 call — CR-01 即因此漏过收敛门禁。新版用 ast.parse + ast.FunctionDef +
        ast.Call 双重检查，确认函数在 def save_pdf(...) body 内被实际调用（ast.Call 节点）。
        """
        import ast

        source = MAIN_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # 定位 def save_pdf
        save_pdf_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "save_pdf":
                save_pdf_func = node
                break
        self.assertIsNotNone(save_pdf_func, "main.py 必须定义 def save_pdf(...)")

        # 在 save_pdf body 内查找 ast.Call with func.id/attr == 'write_partial_masks'
        found_write = False
        found_clear = False
        for node in ast.walk(save_pdf_func):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "write_partial_masks":
                found_write = True
            elif isinstance(func, ast.Attribute) and func.attr == "write_partial_masks":
                found_write = True
            if isinstance(func, ast.Name) and func.id == "clear_pdf_metadata":
                found_clear = True
            elif isinstance(func, ast.Attribute) and func.attr == "clear_pdf_metadata":
                found_clear = True

        self.assertTrue(
            found_write,
            "main.py::save_pdf 必须调用 write_partial_masks（02-04 CR-01 fix；字符串存在性不足）",
        )
        self.assertTrue(
            found_clear,
            "main.py::save_pdf 必须调用 clear_pdf_metadata（02-04 SAFE-03）",
        )

        # D-12 / D-13 配置字段引用（保留向后兼容检查）
        self.assertIn(
            "mask_override_this_doc", source,
            "main.py 必须引用 mask_override_this_doc（D-12 toggle key）",
        )
        self.assertIn(
            "per_entity_default", source,
            "main.py 必须引用 per_entity_default（D-13 config field）",
        )
        # v37.7.6 收敛原则：main.py 不得内联 write_partial_masks / clear_pdf_metadata 实现
        self.assertNotIn(
            "def write_partial_masks(", source,
            "main.py 不得内联 write_partial_masks（v37.7.6 收敛原则）",
        )
        self.assertNotIn(
            "def clear_pdf_metadata(", source,
            "main.py 不得内联 clear_pdf_metadata（v37.7.6 收敛原则）",
        )


class TestPiiWordAdapterConvergence(unittest.TestCase):
    """Phase 3 (03-03-merge-and-preview) — main.py 不应内联 word_adapter 三函数 (D-11)."""

    def test_main_py_does_not_inline_word_adapter_functions(self):
        """D-11: collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx 三函数
        必须在 privacyguard.pii.word_adapter, main.py 不得内联.
        """
        source = MAIN_PY.read_text(encoding="utf-8")
        forbidden = [
            "def collect_pii_word_hits(",
            "def locate_pii_hits_in_paragraph(",
            "def apply_pii_replacements_to_docx(",
        ]
        for pat in forbidden:
            self.assertNotIn(
                pat, source,
                f"main.py 不应保留内联 {pat}（D-11 + v37.7.6 收敛原则）",
            )

    def test_pii_word_adapter_module_does_not_import_docx(self):
        """D-11 + T-03-02: privacyguard/pii/word_adapter.py 源码不得 import docx (AST 扫描)."""
        import ast
        path = Path(__file__).resolve().parents[2] / "privacyguard" / "pii" / "word_adapter.py"
        self.assertTrue(path.exists(), "privacyguard/pii/word_adapter.py 应存在 (Plan 1 落地)")
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "docx" or alias.name.startswith("docx."):
                        bad.append((node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module == "docx" or (node.module and node.module.startswith("docx.")):
                    bad.append((node.lineno, node.module))
        self.assertEqual(bad, [], f"word_adapter.py 不得 import docx (D-11); 实际: {bad}")


if __name__ == "__main__":
    unittest.main()
