"""Phase 2 (02-01-tracer) — SAFE-03 PDF 元数据清除反向测试。

D-14 / D-15 / D-16 锁定：
- 仅清 5 字段（title / author / subject / producer / creator），其他保留
- 5 字段全部置空字符串（不写 "Anonymous" / "Redacted" / "PyMuPDF" 等占位字符串）
- clear_pdf_metadata 在 doc.save() 前调用
"""
import os
import tempfile
import unittest

import fitz


class TestPdfMetadataCleared(unittest.TestCase):
    """SAFE-03: clear_pdf_metadata 清 5 字段 + 保留 CreationDate 等。"""

    def _build_pdf_with_metadata(self, in_pdf: str) -> None:
        """构造一个 5 字段均填敏感占位的合成 PDF。"""
        doc = fitz.open()
        doc.set_metadata({
            "title": "敏感标题",
            "author": "敏感作者",
            "subject": "敏感主题",
            "producer": "敏感生产者",
            "creator": "敏感创建者",
        })
        page = doc.new_page()
        page.insert_text((50, 100), "测试", fontsize=14)
        doc.save(in_pdf)
        doc.close()

    def test_metadata_5_fields_cleared(self):
        """5 字段全部清空字符串（不写占位字符串）。"""
        from privacyguard.pii.pdf_adapter import clear_pdf_metadata
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in_meta.pdf")
            out_pdf = os.path.join(tmp, "out_meta.pdf")
            self._build_pdf_with_metadata(in_pdf)

            # 模拟 save_pdf 流程：open → clear → save
            doc = fitz.open(in_pdf)
            try:
                clear_pdf_metadata(doc)
                doc.save(out_pdf, garbage=4, deflate=True, clean=True)
            finally:
                doc.close()

            # 反向断言
            with fitz.open(out_pdf) as out_doc:
                meta = out_doc.metadata
                for key in ("title", "author", "subject", "producer", "creator"):
                    self.assertEqual(
                        meta.get(key, ""),
                        "",
                        f"元数据 {key} 未清空: {meta.get(key)!r}",
                    )

    def test_metadata_creation_date_preserved(self):
        """CreationDate / ModDate 不应被 clear_pdf_metadata 清空（D-14 锁定）。

        测试策略：先显式设置 CreationDate 为一个固定值，clear 后断言仍保留。
        PyMuPDF set_metadata 不会清空未在 dict 中列出的字段（D-14 锁定）。
        """
        from privacyguard.pii.pdf_adapter import clear_pdf_metadata
        with tempfile.TemporaryDirectory() as tmp:
            step1_pdf = os.path.join(tmp, "step1.pdf")
            step2_pdf = os.path.join(tmp, "step2.pdf")
            out_pdf = os.path.join(tmp, "out_creation.pdf")
            self._build_pdf_with_metadata(step1_pdf)

            # Step 1: 显式设置 CreationDate 为固定值（先保存到 step2_pdf，避免同路径）
            fixed_creation = "D:20260101000000"
            doc = fitz.open(step1_pdf)
            try:
                doc.set_metadata({"creationDate": fixed_creation})
                doc.save(step2_pdf, garbage=4, deflate=True, clean=True)
            finally:
                doc.close()

            # Step 2: 重新打开并 clear
            doc = fitz.open(step2_pdf)
            try:
                clear_pdf_metadata(doc)
                doc.save(out_pdf, garbage=4, deflate=True, clean=True)
            finally:
                doc.close()

            with fitz.open(out_pdf) as out_doc:
                meta = out_doc.metadata
                # 5 字段已清空
                for key in ("title", "author", "subject", "producer", "creator"):
                    self.assertEqual(meta.get(key, ""), "",
                                     f"元数据 {key} 未清空: {meta.get(key)!r}")
                # creationDate 应保留（与 5 字段清空独立）
                creation = meta.get("creationDate", "")
                self.assertIn(
                    "2026", creation,
                    f"creationDate 应保留；实际 = {creation!r}",
                )

    def test_metadata_no_placeholder_strings(self):
        """D-15 锁定：不得写 'Anonymous' / 'Redacted' / 'PyMuPDF' 等占位字符串。"""
        from privacyguard.pii.pdf_adapter import clear_pdf_metadata
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in_placeholder.pdf")
            out_pdf = os.path.join(tmp, "out_placeholder.pdf")
            self._build_pdf_with_metadata(in_pdf)

            doc = fitz.open(in_pdf)
            try:
                clear_pdf_metadata(doc)
                doc.save(out_pdf, garbage=4, deflate=True, clean=True)
            finally:
                doc.close()

            with fitz.open(out_pdf) as out_doc:
                meta = out_doc.metadata
                for key in ("title", "author", "subject", "producer", "creator"):
                    val = meta.get(key, "")
                    self.assertNotIn(val, ("Anonymous", "Redacted", "PyMuPDF", "privacyguard"),
                                     f"元数据 {key} 写了占位字符串: {val!r}")


if __name__ == "__main__":
    unittest.main()
