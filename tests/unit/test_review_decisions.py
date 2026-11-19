"""Review decisions never silently become an unscoped allowlist."""
import tempfile
import unittest
from pathlib import Path

import fitz
from PyQt6.QtCore import QRectF

from privacyguard.utils.review_decisions import (geometry, page_fingerprint, pdf_review_hits,
    word_match_key, word_review_hits, WordReviewStore, valid_pdf_decisions)
from privacyguard.utils.helpers_pdf import snapshot_page_data, restore_page_data
from privacyguard.session_store import SessionStore


class ReviewDecisionsTests(unittest.TestCase):
    def hit(self, x=10):
        return {"rect": QRectF(x, 10, 40, 10), "replace_text": ""}

    def test_pdf_exclusion_exact_geometry_and_fingerprint_only(self):
        first, second = self.hit(), self.hit(100)
        entry = {"_review": [{"geometry": geometry(first), "state": "excluded", "fingerprint": "same"}]}
        self.assertEqual(pdf_review_hits(entry, [first, second], "same"), [second])
        self.assertEqual(pdf_review_hits(entry, [first, second], "changed"), [first, second])

    def test_pixel_change_invalidates_fingerprint(self):
        doc = fitz.open()
        self.addCleanup(doc.close)
        page = doc.new_page()
        before = page_fingerprint(page)
        page.insert_text((40, 40), "changed")
        self.assertNotEqual(before, page_fingerprint(page))

    def test_invisible_ocr_text_change_invalidates_visual_decision(self):
        doc = fitz.open()
        self.addCleanup(doc.close)
        page = doc.new_page()
        page.insert_text((40,40), "PUBLIC")
        before = page_fingerprint(page)
        pixels = page.get_pixmap().samples
        page.insert_text((40,80), "NEW_HIDDEN_SECRET", render_mode=3)
        self.assertEqual(pixels, page.get_pixmap().samples)
        self.assertNotEqual(before, page_fingerprint(page))

    def test_pdf_review_roundtrips_undo_and_disk_draft(self):
        hit = self.hit()
        decision = {"geometry": geometry(hit), "state": "excluded", "fingerprint": "test"}
        data = {0: {"ocr": [], "manual": [], "_review": [decision]}}
        snapshot = snapshot_page_data(data)
        restored = restore_page_data(snapshot)
        self.assertEqual(restored[0]["_review"], [decision])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            source.write_bytes(b"synthetic")
            store = SessionStore(str(Path(directory) / "sessions"))
            self.assertTrue(store.save_draft(str(source), snapshot))
            draft, _ = store.load_draft(str(source))
            self.assertEqual(restore_page_data(draft["page_data"])[0]["_review"], [decision])

    def test_corrupt_review_entries_ignored(self):
        self.assertEqual(valid_pdf_decisions([None, {}, {"geometry": [0, 0, float("nan"), 3], "state": "excluded"}]), [])

    def test_word_exclusion_does_not_cover_another_occurrence(self):
        first = {"start": 0, "end": 6, "text": "SECRET"}
        second = {"start": 10, "end": 16, "text": "SECRET"}
        entry = {"_review": {word_match_key(first): "excluded"}}
        self.assertEqual(word_review_hits(entry, [first, second]), [second])
        self.assertIn(word_match_key(first), entry["_review_removed"])

    def test_word_store_has_no_original_text_and_rejects_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.docx"
            source.write_bytes(b"synthetic source")
            store = WordReviewStore(str(source), directory)
            match = {"start": 0, "end": 6, "text": "SECRET"}
            data = {"paragraph_0": {"_review": {word_match_key(match): "excluded"}}}
            store.save(data)
            self.assertEqual(store.load(), {"paragraph_0": data["paragraph_0"]["_review"]})
            self.assertNotIn("SECRET", store.path.read_text())
            source.write_bytes(b"another source")
            self.assertEqual(store.load(), {})
