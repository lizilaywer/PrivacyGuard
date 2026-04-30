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


if __name__ == "__main__":
    unittest.main()
