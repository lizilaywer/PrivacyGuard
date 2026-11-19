"""Synthetic hidden-object canaries and pixel-only object isolation."""
import tempfile
import unittest
from pathlib import Path

import fitz

from privacyguard.utils.export_transaction import ExportValidationError, save_verified_pdf
from privacyguard.utils.pdf_inventory import inventory_pdf
from privacyguard.utils.pdf_sanitize import prepare_pdf_output, verify_pdf_policy


class PdfHiddenExportTests(unittest.TestCase):
    def make_doc(self):
        doc = fitz.open()
        page = doc.new_page(width=300, height=400)
        page.insert_text((20, 30), "KEEP_VISIBLE")
        doc.set_metadata({"author": "AUTHOR_CANARY"})
        doc.set_xml_metadata('<x>XML_CANARY</x>')
        doc.embfile_add("ATTACH_CANARY.txt", b"ATTACH_CONTENT_CANARY")
        page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(20, 20, 80, 35), "uri": "mailto:LINK_CANARY@example.invalid"})
        # Reload link cache just as an actual opened input document would.
        reopened = fitz.open(stream=doc.tobytes(), filetype="pdf")
        doc.close()
        self.addCleanup(reopened.close)
        return reopened

    def test_inventory_is_text_free_and_preserve_is_unchanged(self):
        doc = self.make_doc()
        counts = inventory_pdf(doc)
        self.assertEqual(counts["attachments"], 1)
        self.assertEqual(counts["links"], 1)
        self.assertEqual(counts["xml"], 1)
        self.assertIs(prepare_pdf_output(doc), doc)
        self.assertIn("AUTHOR_CANARY", doc.metadata["author"])

    def test_sanitize_removes_canaries_and_keeps_visible_text(self):
        doc = self.make_doc()
        prepare_pdf_output(doc, "sanitize")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "clean.pdf"
            save_verified_pdf(doc, target, {"garbage": 4, "deflate": True}, {}, policy="sanitize")
            with fitz.open(target) as output:
                verify_pdf_policy(output, "sanitize")
                self.assertIn("KEEP_VISIBLE", output[0].get_text())
                self.assertEqual(output.embfile_count(), 0)
                self.assertEqual(output[0].get_links(), [])
                for xref in range(1, output.xref_length()):
                    self.assertNotIn("CANARY", output.xref_object(xref))

    def test_raster_rebuild_has_no_text_or_original_objects(self):
        doc = self.make_doc()
        doc[0].set_rotation(90)
        output = prepare_pdf_output(doc, "raster", dpi=144)
        self.addCleanup(output.close)
        self.assertEqual(output[0].rect, doc[0].rect)
        self.assertEqual(output[0].get_text(), "")
        verify_pdf_policy(output, "raster")
        before = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2), annots=False)
        after = output[0].get_pixmap(matrix=fitz.Matrix(2, 2), annots=False)
        self.assertEqual(before.samples, after.samples)
        self.assertEqual(doc.embfile_count(), 1)

    def test_complex_layers_block_sanitize(self):
        doc = self.make_doc()
        doc.add_ocg("LAYER_CANARY")
        with self.assertRaises(ExportValidationError):
            prepare_pdf_output(doc, "sanitize")

    def test_internal_bookmark_destinations_survive_cleaning(self):
        doc = self.make_doc()
        doc.set_toc([[1, "KEEP_BOOKMARK", 1]])
        prepare_pdf_output(doc, "sanitize")
        self.assertEqual(doc.get_toc(), [[1, "KEEP_BOOKMARK", 1]])

    def test_invisible_text_blocks_sanitize_and_raster_drops_it(self):
        doc = self.make_doc()
        doc[0].insert_text((20, 80), "HIDDEN_CANARY", render_mode=3)
        self.assertGreater(inventory_pdf(doc)["invisible"], 0)
        with self.assertRaises(ExportValidationError):
            prepare_pdf_output(doc, "sanitize")
        output = prepare_pdf_output(doc, "raster")
        self.addCleanup(output.close)
        self.assertEqual(output[0].get_text(), "")

    def test_pixel_budget_fails_without_partial_output(self):
        doc = fitz.open()
        self.addCleanup(doc.close)
        doc.new_page(width=10000, height=10000)
        with self.assertRaises(ExportValidationError):
            prepare_pdf_output(doc, "raster")

    def test_unknown_policy_fails(self):
        with self.assertRaises(ExportValidationError):
            prepare_pdf_output(self.make_doc(), "unknown")
