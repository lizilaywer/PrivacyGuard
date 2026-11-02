# -*- coding: utf-8 -*-
"""cp113: PDF 密码状态检测单元测试。

测试 privacyguard.utils.helpers_pdf.detect_pdf_password_state:
- 无密码 PDF: needs_user_pw=False, has_owner_restriction=False
- user password PDF: needs_user_pw=True
- owner restriction PDF（无 user pw，permissions 受限）: has_owner_restriction=True
- None / 异常输入: 返回安全默认
"""

import os
import tempfile
import unittest

import fitz

from privacyguard.utils.helpers_pdf import detect_pdf_password_state


class TestDetectPdfPasswordState(unittest.TestCase):
    def _make_pdf(self, path, user_pw="", owner_pw="", permissions=None):
        doc = fitz.open()
        doc.new_page()
        kwargs = {}
        if user_pw or owner_pw or permissions is not None:
            kwargs["encryption"] = fitz.PDF_ENCRYPT_AES_256
            if user_pw:
                kwargs["user_pw"] = user_pw
            if owner_pw:
                kwargs["owner_pw"] = owner_pw
            if permissions is not None:
                kwargs["permissions"] = permissions
        doc.save(path, **kwargs)
        doc.close()

    def _temp_path(self, suffix=".pdf"):
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        return path

    def test_no_password(self):
        path = self._temp_path()
        try:
            self._make_pdf(path)
            doc = fitz.open(path)
            try:
                state = detect_pdf_password_state(doc)
                self.assertFalse(state["needs_user_pw"])
                self.assertFalse(state["has_owner_restriction"])
            finally:
                doc.close()
        finally:
            os.remove(path)

    def test_user_password(self):
        path = self._temp_path()
        try:
            self._make_pdf(path, user_pw="secret")
            doc = fitz.open(path)
            try:
                state = detect_pdf_password_state(doc)
                self.assertTrue(state["needs_user_pw"])
                # user_pw 设置时 has_owner_restriction 应为 False（逻辑：not needs_user_pw and ...）
                self.assertFalse(state["has_owner_restriction"])
            finally:
                doc.close()
        finally:
            os.remove(path)

    def test_owner_restriction(self):
        path = self._temp_path()
        try:
            # 仅 owner_pw + 受限权限（无 user_pw）→ 打开无需密码但编辑/复制受限
            restricted = int(fitz.PDF_PERM_PRINT | fitz.PDF_PERM_ACCESSIBILITY)
            self._make_pdf(path, owner_pw="owner", permissions=restricted)
            doc = fitz.open(path)
            try:
                state = detect_pdf_password_state(doc)
                self.assertFalse(state["needs_user_pw"])
                self.assertTrue(state["has_owner_restriction"])
            finally:
                doc.close()
        finally:
            os.remove(path)

    def test_none_doc_safe_default(self):
        state = detect_pdf_password_state(None)
        self.assertFalse(state["needs_user_pw"])
        self.assertFalse(state["has_owner_restriction"])
        self.assertEqual(state["permissions"], 0)


if __name__ == "__main__":
    unittest.main()
