#!/usr/bin/env python3
"""路径安全校验单元测试（测试生产实现）。"""

import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from privacyguard.utils.security import validate_safe_path


class TestPathValidation(unittest.TestCase):
    def test_windows_backslash_path_allowed_on_windows(self):
        # 走真实 Windows 路径校验：黑名单模式下跨盘符应放行
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            ok, msg = validate_safe_path(r"D:\Documents\test.docx", [".doc", ".docx"])
            self.assertTrue(ok, msg)

    def test_windows_unc_path_allowed_on_windows(self):
        # UNC 路径应放行
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            ok, msg = validate_safe_path(r"\\server\share\test.docx", [".docx"])
            self.assertTrue(ok, msg)

    def test_windows_system_directory_rejected_on_windows(self):
        # C:\Windows 与 Program Files 必须拒绝
        # 注：生产实现的黑名单匹配依赖 ntpath 语义，非 Windows 平台跑此用例
        # 需一并把 os.path 模拟为 ntpath（否则盘符路径被当相对路径，commonpath 失配）
        import ntpath
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"), \
             patch("os.path", ntpath):
            ok, msg = validate_safe_path(r"C:\Windows\System32\test.docx", [".docx"])
            self.assertFalse(ok)
            self.assertIn("受保护", msg)

    def test_windows_backslash_path_rejected_on_non_windows(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Darwin"):
            ok, msg = validate_safe_path(r"C:\Users\Admin\test.docx", [".doc", ".docx"])
            self.assertFalse(ok)
            self.assertIn("危险字符", msg)

    def test_shell_metacharacters_rejected(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            for bad in [";", "|", "&", "$", "`", ">", "<"]:
                with self.subTest(bad=bad):
                    ok, _ = validate_safe_path(f"D:\\test{bad}x.doc", [".doc"])
                    self.assertFalse(ok)

    def test_url_encoded_sequence_rejected(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            ok, msg = validate_safe_path(r"D:\test%0a.doc", [".doc"])
            self.assertFalse(ok)
            self.assertIn("危险序列", msg)

    def test_extension_whitelist_case_insensitive(self):
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            ok, msg = validate_safe_path(r"D:\Documents\test.DOCX", [".doc", ".docx"])
            self.assertTrue(ok, msg)

    def test_outside_allowed_directory_rejected(self):
        # 用 mock posixpath 让测试在 Windows 真机上也能验证 POSIX 白名单语义
        # 注意：必须 patch os.path.expanduser，否则 posixpath.expanduser("~")
        # 在 Windows 真机上会 import pwd 失败
        import posixpath
        with patch("privacyguard.utils.security.platform.system", return_value="Darwin"), \
             patch("privacyguard.utils.security.os.path", posixpath), \
             patch("privacyguard.utils.security.os.sep", "/"), \
             patch("privacyguard.utils.security.tempfile.gettempdir", return_value="/tmp"), \
             patch("privacyguard.utils.security.os.path.isdir", return_value=True), \
             patch("privacyguard.utils.security.os.path.expanduser", return_value="/home/testuser"):
            ok, msg = validate_safe_path("/etc/passwd")
            self.assertFalse(ok)
            self.assertIn("不在允许范围", msg)

    def test_temp_path_allowed(self):
        import posixpath
        with patch("privacyguard.utils.security.platform.system", return_value="Darwin"), \
             patch("privacyguard.utils.security.os.path", posixpath), \
             patch("privacyguard.utils.security.os.sep", "/"), \
             patch("privacyguard.utils.security.tempfile.gettempdir", return_value="/tmp"), \
             patch("privacyguard.utils.security.os.path.isdir", return_value=True), \
             patch("privacyguard.utils.security.os.path.expanduser", return_value="/home/testuser"):
            ok, msg = validate_safe_path("/tmp/privacyguard_test.docx", [".docx"])
            self.assertTrue(ok, msg)

    def test_prefix_bypass_path_rejected(self):
        # home_evil 不能绕过白名单 commonpath 检查
        import posixpath
        with patch("privacyguard.utils.security.platform.system", return_value="Darwin"), \
             patch("privacyguard.utils.security.os.path", posixpath), \
             patch("privacyguard.utils.security.os.sep", "/"), \
             patch("privacyguard.utils.security.tempfile.gettempdir", return_value="/tmp"), \
             patch("privacyguard.utils.security.os.path.isdir", return_value=True), \
             patch("privacyguard.utils.security.os.path.expanduser", return_value="/home/testuser"):
            ok, msg = validate_safe_path("/home/testuser_evil/test.docx", [".docx"])
            self.assertFalse(ok)
            self.assertIn("不在允许范围", msg)

    def test_dotdot_basename_still_allowed_for_legal_names(self):
        # a..b.pdf 是合法文件名不应被拒绝
        with patch("privacyguard.utils.security.platform.system", return_value="Windows"):
            ok, msg = validate_safe_path(r"D:\Documents\a..b.pdf", [".pdf"])
            self.assertTrue(ok, msg)

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
