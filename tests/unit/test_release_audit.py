"""Adversarial regressions from the 2026-10-24 release audit."""

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
import numpy as np
from docx import Document
from PyQt6.QtCore import QRectF

from privacyguard.ocr.rapidocr import RapidOCREngine
from privacyguard.session_store import SessionStore
from privacyguard.ui.mixins.bookmark_mixin import BookmarkMixin
from privacyguard.utils.app_paths import default_config_path
from privacyguard.utils.exceptions import OCRInspectionError
from privacyguard.utils.helpers_bookmark import redact_toc_titles
from privacyguard.utils.helpers_pdf import build_result_doc_from_segments, crop_vertical_region_from_page
from privacyguard.utils.helpers_word_doc import iter_word_header_footer_paragraphs
from privacyguard.utils.pdf_regions import crop_page_hits
from privacyguard.workers.batch_replace_worker import WordBatchReplaceWorker
from privacyguard.workers.ocr_worker import OCRWorker
from privacyguard.workers.word_worker import WordWorker


class TestReleaseAudit(unittest.TestCase):
    def test_batch_decision_arriving_before_wait_is_not_lost(self):
        worker = WordBatchReplaceWorker([], [], "*")
        worker.provide_error_decision("stop")
        result = []
        thread = threading.Thread(target=lambda: result.append(worker._wait_for_error_decision()))
        thread.start()
        thread.join(0.3)
        if thread.is_alive():
            worker.provide_error_decision("stop")
            thread.join(1)
            self.fail("Early decision was cleared before wait")
        self.assertEqual(result, ["stop"])

    def test_bookmark_replacement_is_literal_not_backreference(self):
        self.assertEqual(redact_toc_titles([[1, "ALICE", 1]],
                         [{"find": "alice", "replace": r"C:\new\1"}]),
                         [[1, r"C:\new\1", 1]])

    def test_targeted_bookmark_terms_accumulate(self):
        class Harness(BookmarkMixin):
            bookmark_redact_enabled = True
        model = Harness()
        model.apply_targeted_terms_to_bookmarks(["Alice"], "*")
        model.apply_targeted_terms_to_bookmarks(["Bob"], "*")
        self.assertEqual({r["find"] for r in model._collect_active_toc_rules()}, {"Alice", "Bob"})

    def test_frozen_config_is_outside_bundle(self):
        home = Path(tempfile.gettempdir()) / "pguser"
        with patch("sys.frozen", True, create=True), patch("sys.platform", "darwin"), \
                patch("pathlib.Path.home", return_value=home):
            self.assertEqual(default_config_path(),
                             str(home / "Library/Application Support/PrivacyGuard/config.json"))

    def test_first_even_normal_headers_are_all_scanned(self):
        doc = Document()
        section = doc.sections[0]
        for name in ("header", "footer", "first_page_header", "first_page_footer",
                     "even_page_header", "even_page_footer"):
            getattr(section, name).paragraphs[0].text = name
        blocks = dict(iter_word_header_footer_paragraphs(doc))
        self.assertEqual(len(blocks), 6)
        self.assertEqual({p.text for p in blocks.values()},
                         {"header", "footer", "first_page_header", "first_page_footer",
                          "even_page_header", "even_page_footer"})

    def test_frozen_logs_do_not_modify_signed_bundle(self):
        from privacyguard.utils.logger import _resolve_log_dir
        home = Path(tempfile.gettempdir()) / "pguser"
        with patch("sys.frozen", True, create=True), patch("sys.platform", "darwin"), \
                patch("pathlib.Path.home", return_value=home):
            self.assertEqual(str(_resolve_log_dir()),
                             str(home / "Library/Application Support/PrivacyGuard/logs"))

    def test_word_exception_is_marked_incomplete(self):
        worker = WordWorker(None, {"p": {"text": "Alice", "ocr": [], "manual": []}}, [], "", "*")
        received = []
        worker.finished_signal.connect(received.append)
        with patch.object(worker, "_find_matches", side_effect=ValueError("synthetic")):
            worker.run()
        self.assertEqual(received[0]["__scan_meta__"]["error_type"], "ValueError")
        self.assertEqual(received[0]["__scan_meta__"]["processed_items"], 0)

    def test_model_failure_raises_instead_of_returning_empty(self):
        with patch.object(RapidOCREngine, "_shared_init_failed", True):
            with self.assertRaises(OCRInspectionError):
                RapidOCREngine().recognize(np.zeros((10, 10, 3), dtype=np.uint8))

    def test_ocr_uses_modified_snapshot_not_original_path(self):
        with fitz.open() as doc:
            doc.new_page().insert_text((50, 50), "PHONE 13812345678")
            pdf_bytes = doc.tobytes()
        worker = OCRWorker("nonexistent-original.pdf", [r"1[3-9]\d{9}"], False, "", 1.5, 0, 0,
                           pdf_bytes=pdf_bytes)
        errors, results = [], []
        worker.error_signal.connect(errors.append)
        worker.page_result_signal.connect(lambda n, hits: results.append((n, hits)))
        with patch.object(RapidOCREngine, "is_available", return_value=True):
            worker.run()
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0][1]), 1)

    def test_blank_pdf_page_is_not_an_ocr_failure(self):
        with fitz.open() as doc:
            doc.new_page()
            data = doc.tobytes()
        worker = OCRWorker("missing.pdf", [r"phone"], False, "", 1.5, 0, 0, pdf_bytes=data)
        errors = []
        worker.error_signal.connect(errors.append)
        with patch.object(RapidOCREngine, "is_available", return_value=True):
            worker.run()
        self.assertEqual(errors, [])

    def test_crop_keeps_and_shifts_masks(self):
        hit = {"rect": QRectF(10, 300, 50, 20), "rule": "phone", "replace_text": "*"}
        mapped = crop_page_hits({"ocr": [hit], "manual": [QRectF(10, 140, 20, 120)]},
                                150, 250, 200, 400)
        self.assertEqual(mapped["ocr"][0]["rect"], QRectF(10, 200, 50, 20))
        self.assertEqual(mapped["ocr"][0]["rule"], "phone")
        self.assertEqual(len(mapped["manual"]), 2)
        self.assertEqual(hit["rect"].y(), 300)

    def test_extract_has_no_secret_in_any_decoded_stream(self):
        with fitz.open() as src:
            p = src.new_page(width=200, height=400)
            p.insert_text((10, 50), "PUBLIC")
            p.insert_text((10, 250), "SECRET_OUTSIDE")
            with build_result_doc_from_segments(src, [[{"src_pno": 0, "y_min": 0, "y_max": 100}]]) as result:
                self._assert_no_secret(result, b"SECRET_OUTSIDE")
                self.assertIn("PUBLIC", result[0].get_text())
            self.assertIn("SECRET_OUTSIDE", src[0].get_text())

    def test_crop_has_no_discarded_text_in_any_decoded_stream(self):
        with fitz.open() as doc:
            p = doc.new_page(width=200, height=400)
            p.insert_text((10, 50), "PUBLIC")
            p.insert_text((10, 200), "SECRET_REMOVED")
            crop_vertical_region_from_page(doc, 0, 150, 250)
            self._assert_no_secret(doc, b"SECRET_REMOVED")

    def _assert_no_secret(self, doc, secret):
        with fitz.open(stream=doc.tobytes(garbage=2, clean=True), filetype="pdf") as saved:
            for xref in range(1, saved.xref_length()):
                if saved.xref_is_stream(xref):
                    stream = saved.xref_stream(xref)
                    self.assertNotIn(secret, stream)
                    self.assertNotIn(secret.hex().encode(), stream.lower())

    def test_malformed_draft_does_not_crash_load_or_prune(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.pdf"
            path.write_bytes(b"sample")
            store = SessionStore(os.path.join(tmp, "sessions"))
            store.save_draft(str(path), {})
            draft_path = Path(store._draft_path(str(path)))
            draft_path.write_text(json.dumps({"version": 1, "fingerprint": ["bad"]}))
            self.assertEqual(store.load_draft(str(path)), (None, None))
            draft_path.write_text('[]')
            self.assertEqual(len(store.list_drafts()), 1)

    def test_specs_never_embed_local_config(self):
        root = Path(__file__).resolve().parents[2]
        for rel in ("packaging/macos/config/PrivacyGuard.spec",
                    "packaging/windows/config/PrivacyGuard_windows.spec"):
            source = (root / rel).read_text(encoding="utf-8")
            self.assertNotIn("(os.path.join(project_root, 'config.json'), '.')", source)
            self.assertIn("config.json.template", source)


if __name__ == "__main__":
    unittest.main()
