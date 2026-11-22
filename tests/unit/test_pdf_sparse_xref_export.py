"""Synthetic PDFs with unused xref slots and genuinely broken references."""

import tempfile
import unittest
from pathlib import Path

import fitz
from PyQt6.QtCore import QRectF

from privacyguard.diagnostics import synthetic_sparse_pdf
from privacyguard.utils.export_transaction import ExportValidationError, save_verified_pdf
from privacyguard.utils.pdf_inventory import inventory_pdf
from privacyguard.utils.pdf_sanitize import prepare_pdf_output
from privacyguard.utils.pdf_structure import pdf_export_error_message




class PdfSparseXrefExportTests(unittest.TestCase):
    def test_unused_slots_allow_checked_preserve_and_sanitize_exports(self):
        raw = synthetic_sparse_pdf()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            source.write_bytes(raw)
            for policy in ("preserve", "sanitize"):
                with self.subTest(policy=policy), fitz.open(source) as document:
                    self.assertEqual(inventory_pdf(document)["xml"], 1)
                    rect = document[0].search_for("TEST_SECRET")[0]
                    document[0].add_redact_annot(rect, fill=(0, 0, 0))
                    document[0].apply_redactions()
                    prepared = prepare_pdf_output(document, policy)
                    target = Path(directory) / f"{policy}.pdf"
                    masks = {0: {"ocr": [], "manual": [QRectF(rect.x0, rect.y0, rect.width, rect.height)]}}
                    save_verified_pdf(prepared, target, {"garbage": 2, "clean": True}, masks, source, policy)
                    with fitz.open(target) as exported:
                        self.assertNotIn("TEST_SECRET", exported[0].get_text())
                        self.assertIn("KEEP_VISIBLE", exported[0].get_text())
                        self.assertEqual(bool(exported.get_xml_metadata()), policy == "preserve")
            self.assertEqual(source.read_bytes(), raw)

    def test_missing_referenced_object_stops_inventory_even_if_page_loads(self):
        for explicitly_free in (False, True):
            raw = synthetic_sparse_pdf(reference_missing=True, explicitly_free=explicitly_free)
            with self.subTest(explicitly_free=explicitly_free), fitz.open(stream=raw, filetype="pdf") as document:
                self.assertEqual(len(document), 1)
                with self.assertRaisesRegex(ExportValidationError, "结构引用了一个无法读取的对象"):
                    inventory_pdf(document)

    def test_bad_temp_pdf_never_replaces_existing_output(self):
        class IncompleteWriter:
            def save(self, path, **_options):
                Path(path).write_bytes(synthetic_sparse_pdf(reference_missing=True))

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "output.pdf"
            target.write_bytes(b"existing export")
            with self.assertRaisesRegex(ExportValidationError, "结构引用了一个无法读取的对象"):
                save_verified_pdf(IncompleteWriter(), target, {}, {})
            self.assertEqual(target.read_bytes(), b"existing export")
            self.assertEqual(list(Path(directory).glob(".pg-export-*")), [])

    def test_user_message_never_includes_raw_xref_detail(self):
        error = RuntimeError("code=7: cannot find object in xref (12 0 R)")
        text = pdf_export_error_message(error)
        self.assertIn("导出已停止", text)
        self.assertNotIn("12 0 R", text)
