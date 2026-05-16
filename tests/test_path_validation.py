#!/usr/bin/env python3
"""路径安全校验单元测试（测试生产实现）。"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from privacyguard.utils.security import validate_safe_path


class TestPathValidation(unittest.TestCase):
    def test_windows_backslash_path_allowed_on_windows(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            ok, msg = validate_safe_path(r"C:\Users\Admin\test.docx", [".doc", ".docx"])
            self.assertTrue(ok, msg)

    def test_windows_backslash_path_rejected_on_non_windows(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Darwin"):
            ok, msg = validate_safe_path(r"C:\Users\Admin\test.docx", [".doc", ".docx"])
            self.assertFalse(ok)
            self.assertIn("危险字符", msg)

    def test_shell_metacharacters_rejected(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            for bad in [";", "|", "&", "$", "`", ">", "<"]:
                with self.subTest(bad=bad):
                    ok, _ = validate_safe_path(f"C:\\test{bad}x.doc", [".doc"])
                    self.assertFalse(ok)

    def test_url_encoded_sequence_rejected(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            ok, msg = validate_safe_path(r"C:\test%0a.doc", [".doc"])
            self.assertFalse(ok)
            self.assertIn("危险序列", msg)

    def test_extension_whitelist_case_insensitive(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            ok, msg = validate_safe_path(r"C:\Users\Admin\test.DOCX", [".doc", ".docx"])
            self.assertTrue(ok, msg)

    def test_outside_allowed_directory_rejected(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Darwin"):
            ok, msg = validate_safe_path("/etc/passwd")
            self.assertFalse(ok)
            self.assertIn("不在允许范围", msg)

    def test_temp_path_allowed(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Darwin"):
            temp_path = os.path.join(tempfile.gettempdir(), "privacyguard_test.docx")
            ok, msg = validate_safe_path(temp_path, [".docx"])
            self.assertTrue(ok, msg)

    def test_prefix_bypass_path_rejected(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Darwin"):
            fake_sibling = os.path.abspath(os.path.expanduser("~")) + "_evil/test.docx"
            ok, msg = validate_safe_path(fake_sibling, [".docx"])
            self.assertFalse(ok)
            self.assertIn("不在允许范围", msg)

    def test_main_py_uses_shared_validate_safe_path(self):
        """main.py 应直接使用共享实现，不保留本地副本。"""
        with open(os.path.join(ROOT, "main.py"), "r", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("from privacyguard.utils.security import validate_safe_path", source,
            "main.py 应从共享模块导入 validate_safe_path")
        self.assertNotRegex(source, r'def validate_safe_path\s*\(',
            "main.py 不应包含 validate_safe_path 的本地定义")

    def test_main_py_uses_shared_resource_path(self):
        """main.py 应使用共享 resource_path，不保留本地副本。"""
        with open(os.path.join(ROOT, "main.py"), "r", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("resource_path", source,
            "main.py 应引用 resource_path")
        lines = source.split('\n')
        local_defs = [l for l in lines if l.strip().startswith('def resource_path')]
        self.assertEqual(len(local_defs), 0,
            f"main.py 不应包含 resource_path 的本地定义，发现: {local_defs}")


if __name__ == "__main__":
    unittest.main()
