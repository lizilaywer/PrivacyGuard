# -*- coding: utf-8 -*-
"""cp113: Word 文档加密检测与解密单元测试。

测试 privacyguard.utils.word_crypto:
- is_encrypted_docx: OLE2 / ZIP 魔数判定
- decrypt_docx_to_temp: 非加密文件抛 TypeError、密码正确解密、密码错误抛 ValueError
  （msoffcrypto 懒导入，用 sys.modules mock 注入假模块，避免依赖真实加密样本）
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from privacyguard.utils.word_crypto import is_encrypted_docx, decrypt_docx_to_temp


def _write_temp(data: bytes, suffix: str = ".docx") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(data)
    return path


class TestIsEncryptedDocx(unittest.TestCase):
    def test_ole2_magic_is_encrypted(self):
        path = _write_temp(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1OLE2 content")
        try:
            self.assertTrue(is_encrypted_docx(path))
        finally:
            os.remove(path)

    def test_zip_magic_not_encrypted(self):
        path = _write_temp(b"PK\x03\x04zip docx content")
        try:
            self.assertFalse(is_encrypted_docx(path))
        finally:
            os.remove(path)

    def test_missing_file_not_encrypted(self):
        self.assertFalse(is_encrypted_docx(os.path.join(tempfile.gettempdir(), "pgud_no_such_file.docx")))

    def test_empty_path_not_encrypted(self):
        self.assertFalse(is_encrypted_docx(""))

    def test_short_file_not_encrypted(self):
        path = _write_temp(b"PK")  # 不足 4 字节
        try:
            self.assertFalse(is_encrypted_docx(path))
        finally:
            os.remove(path)


class _FakeOfficeFile:
    """模拟 msoffcrypto.OfficeFile 行为。"""

    def __init__(self, in_fp, load_key_side_effect=None, decrypt_payload=b"decrypted docx bytes"):
        self._in_fp = in_fp
        self._load_key_side_effect = load_key_side_effect
        self._decrypt_payload = decrypt_payload

    def load_key(self, password=None):
        if self._load_key_side_effect is not None:
            raise self._load_key_side_effect

    def decrypt(self, out_fp):
        out_fp.write(self._decrypt_payload)


class TestDecryptDocxToTemp(unittest.TestCase):
    def test_non_encrypted_raises_type_error(self):
        path = _write_temp(b"PK\x03\x04zip content")
        out = path + ".out"
        try:
            with self.assertRaises(TypeError):
                decrypt_docx_to_temp(path, "pw", out)
        finally:
            os.remove(path)
            if os.path.exists(out):
                os.remove(out)

    def test_correct_password_decrypts(self):
        src = _write_temp(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1encrypted")
        out = src + ".out"
        try:
            fake_module = MagicMock()
            fake_module.OfficeFile = lambda in_fp: _FakeOfficeFile(in_fp)
            with patch.dict(sys.modules, {"msoffcrypto": fake_module}):
                result = decrypt_docx_to_temp(src, "correctpw", out)
            self.assertEqual(result, out)
            self.assertTrue(os.path.exists(out))
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"decrypted docx bytes")
        finally:
            for p in (src, out):
                if os.path.exists(p):
                    os.remove(p)

    def test_wrong_password_raises_value_error_and_cleans(self):
        src = _write_temp(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1encrypted")
        out = src + ".out"
        try:
            fake_module = MagicMock()
            fake_module.OfficeFile = lambda in_fp: _FakeOfficeFile(
                in_fp, load_key_side_effect=Exception("bad key"))
            with patch.dict(sys.modules, {"msoffcrypto": fake_module}):
                with self.assertRaises(ValueError):
                    decrypt_docx_to_temp(src, "wrongpw", out)
            # 半成品文件应被清理
            self.assertFalse(os.path.exists(out))
        finally:
            if os.path.exists(src):
                os.remove(src)

    def test_decrypt_creates_output_dir(self):
        src = _write_temp(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1encrypted")
        out_dir = os.path.join(tempfile.gettempdir(), "pgud_word_crypto_subdir")
        out = os.path.join(out_dir, "out.docx")
        try:
            fake_module = MagicMock()
            fake_module.OfficeFile = lambda in_fp: _FakeOfficeFile(in_fp)
            with patch.dict(sys.modules, {"msoffcrypto": fake_module}):
                result = decrypt_docx_to_temp(src, "pw", out)
            self.assertEqual(result, out)
            self.assertTrue(os.path.exists(out))
        finally:
            if os.path.exists(src):
                os.remove(src)
            if os.path.exists(out):
                os.remove(out)
            if os.path.isdir(out_dir):
                os.rmdir(out_dir)


if __name__ == "__main__":
    unittest.main()
