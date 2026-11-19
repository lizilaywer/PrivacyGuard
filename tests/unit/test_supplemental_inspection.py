"""Opt-in candidate search, bounded inspection and mixed-PDF cache scope."""
import unittest
from unittest.mock import patch

import cv2
import fitz
import numpy as np

from privacyguard.ocr.base import OCRResult
from privacyguard.ocr.local_inspection import inspect_page
from privacyguard.ocr.search_content import bind_document_cache, cache_result
from privacyguard.utils.text_candidates import collect_search_hits, normalized_map
from privacyguard.workers.search_worker import DocSearchWorker


class FakeEngine:
    def is_available(self):
        return True
    def recognize(self, image):
        return [OCRResult("IMAGE_SECRET", [[10, 10], [100, 10], [100, 30], [10, 30]], [], .99, "fake")]


class SupplementalTests(unittest.TestCase):
    def make_pdf(self, rotate=0):
        doc = fitz.open()
        page = doc.new_page(width=300, height=400)
        page.insert_text((20, 30), "TEXT_SECRET")
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 80), False)
        pix.clear_with(255)
        page.insert_image(fitz.Rect(60, 100, 140, 180), pixmap=pix)
        page.set_rotation(rotate)
        raw = doc.tobytes()
        doc.close()
        return raw

    def test_normalized_search_maps_original_span_and_does_not_rewrite(self):
        text = "电话：１３８ ００１３-８０００；KEEP"
        hits = collect_search_hits(text, "13800138000", True)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][2], "１３８ ００１３-８０００")
        self.assertEqual(collect_search_hits(text, "13800138000"), [])
        self.assertIn("KEEP", text)

    def test_whitespace_runs_are_linear_and_word_spaces_preserved(self):
        result, offsets = normalized_map("1" + " "*100000 + "2 word space")
        self.assertEqual(result, "12 word space")
        self.assertEqual(offsets[1], 100001)

    def test_cache_invalidates_document_and_is_bounded(self):
        cache = {}
        bind_document_cache(cache, b"docA")
        cache_result(cache, 0, {"text": "SECRET", "spans": []})
        bind_document_cache(cache, b"docB")
        self.assertNotIn(0, cache)
        for index in range(10):
            cache_result(cache, index, {"text": "x"*600000, "spans": []})
        self.assertLessEqual(sum(len(value["text"])*2 for key,value in cache.items() if isinstance(key,int)), 8*1024*1024)

    def test_mixed_page_searches_image_despite_existing_text(self):
        for rotation in (0, 90, 180, 270):
            worker = DocSearchWorker(self.make_pdf(rotation), "IMAGE_SECRET", {})
            hits, done = [], []
            worker.hit_signal.connect(lambda *args: hits.append(args))
            worker.finished_signal.connect(done.append)
            with patch('privacyguard.ocr.rapidocr.RapidOCREngine', return_value=FakeEngine()):
                worker.run()
            self.assertEqual(done, [1])
            self.assertIsNotNone(hits[0][-1])
            x,y,w,h = hits[0][-1]
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)

    def test_ocr_error_is_not_reported_as_success_or_cached(self):
        worker = DocSearchWorker(self.make_pdf(), "SECRET", {})
        done, errors = [], []
        worker.finished_signal.connect(done.append)
        worker.error_signal.connect(errors.append)
        class Broken(FakeEngine):
            def recognize(self, image):
                raise RuntimeError("PRIVATE_INPUT_NOT_FOR_LOG")
        with patch('privacyguard.ocr.rapidocr.RapidOCREngine', return_value=Broken()):
            worker.run()
        self.assertFalse(done)
        self.assertEqual(len(errors), 1)
        self.assertNotIn("PRIVATE_INPUT", errors[0])
        self.assertNotIn(0, worker.ocr_cache)

    def test_small_text_inspection_returns_candidates_not_masks(self):
        with fitz.open(stream=self.make_pdf(), filetype="pdf") as doc:
            original = doc[0].get_text()
            candidates, status = inspect_page(doc[0], FakeEngine())
            self.assertGreater(len(candidates), 0)
            self.assertNotIn("IMAGE_SECRET", repr(candidates))
            self.assertEqual(doc[0].get_text(), original)
            self.assertTrue(status)

    def test_qr_detection_does_not_decode_or_expose_payload(self):
        encoder = cv2.QRCodeEncoder_create()
        pattern = encoder.encode("https://example.invalid/PRIVATE_QR_PAYLOAD")
        pattern = cv2.copyMakeBorder(pattern, 5,5,5,5, cv2.BORDER_CONSTANT, value=255)
        pattern = cv2.resize(pattern, (300,300), interpolation=cv2.INTER_NEAREST)
        class NoText(FakeEngine):
            def recognize(self, image):
                return []
        with fitz.open() as doc:
            page = doc.new_page(width=300,height=300)
            rgb = np.repeat(pattern[:,:,None],3,axis=2)
            pix = fitz.Pixmap(fitz.csRGB, 300,300, rgb.tobytes(), False)
            page.insert_image(fitz.Rect(30,30,270,270),pixmap=pix)
            candidates, _ = inspect_page(page, NoText())
            self.assertTrue(any(c["kind"] == "二维码图案候选" for c in candidates))
            self.assertNotIn("PRIVATE_QR_PAYLOAD", repr(candidates))

    def test_cancel_does_not_mark_complete(self):
        with fitz.open(stream=self.make_pdf(), filetype="pdf") as doc:
            candidates, status = inspect_page(doc[0], FakeEngine(), cancelled=lambda:True)
            self.assertEqual(candidates, [])
            self.assertIn("取消", status)
