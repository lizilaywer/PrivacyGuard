"""cp72 回归测试：文档加密参数构建（build_encrypt_save_kwargs）

覆盖：
1. 两者都空 → 空 dict（不加密）
2. 仅打开密码 → user_pw 设置、owner 回退、全权限
3. 仅编辑密码 → user_pw 空、owner 设置、受限权限
4. 两者都设 → 各自独立、受限权限
5. 空白/纯空格 strip 后视为空
"""
import unittest

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

from main import build_encrypt_save_kwargs


class TestBuildEncryptSaveKwargs(unittest.TestCase):
    def test_both_empty_returns_empty(self):
        self.assertEqual(build_encrypt_save_kwargs("", ""), {})
        self.assertEqual(build_encrypt_save_kwargs(None, None), {})
        self.assertEqual(build_encrypt_save_kwargs("   ", "  "), {})

    @unittest.skipUnless(HAS_FITZ, "fitz 未安装")
    def test_open_only(self):
        kw = build_encrypt_save_kwargs("open123", "")
        self.assertEqual(kw["encryption"], fitz.PDF_ENCRYPT_AES_256)
        self.assertEqual(kw["user_pw"], "open123")
        self.assertEqual(kw["owner_pw"], "open123")  # owner 回退到 open
        # 全权限：含 MODIFY / COPY
        self.assertTrue(kw["permissions"] & int(fitz.PDF_PERM_MODIFY))
        self.assertTrue(kw["permissions"] & int(fitz.PDF_PERM_COPY))

    @unittest.skipUnless(HAS_FITZ, "fitz 未安装")
    def test_edit_only(self):
        kw = build_encrypt_save_kwargs("", "edit456")
        self.assertEqual(kw["user_pw"], "")  # 打开无需密码
        self.assertEqual(kw["owner_pw"], "edit456")
        # 受限权限：不含 MODIFY / COPY，但含 PRINT
        self.assertFalse(kw["permissions"] & int(fitz.PDF_PERM_MODIFY))
        self.assertFalse(kw["permissions"] & int(fitz.PDF_PERM_COPY))
        self.assertTrue(kw["permissions"] & int(fitz.PDF_PERM_PRINT))

    @unittest.skipUnless(HAS_FITZ, "fitz 未安装")
    def test_both_set(self):
        kw = build_encrypt_save_kwargs("open123", "edit456")
        self.assertEqual(kw["user_pw"], "open123")
        self.assertEqual(kw["owner_pw"], "edit456")  # 各自独立，不回退
        # 有编辑密码 → 受限权限
        self.assertFalse(kw["permissions"] & int(fitz.PDF_PERM_MODIFY))

    @unittest.skipUnless(HAS_FITZ, "fitz 未安装")
    def test_strip_whitespace(self):
        kw = build_encrypt_save_kwargs("  open123  ", "")
        self.assertEqual(kw["user_pw"], "open123")


if __name__ == "__main__":
    unittest.main()
