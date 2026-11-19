"""Alignment must improve eligible lines without losing legacy fallback paths."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from PyQt6.QtCore import QRectF

from privacyguard.ocr.base import OCRResult
from privacyguard.ocr.char_alignment import align_characters, character_sub_rect
from privacyguard.ocr.mixed_pdf import iter_ocr_lines, collect_image_block_ocr_hits
from privacyguard.ocr.rapidocr import RapidOCREngine
from privacyguard.workers.ocr_worker import OCRWorker


def box(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


class TestCharAlignment(unittest.TestCase):
    def setUp(self):
        self.text = "姓名 张三 138"
        self.line = box(0, 0, 140, 20)
        self.tokens = [(char, 0.99, box(i * 12, 0, i * 12 + 11, 20))
                       for i, char in enumerate(self.text) if not char.isspace()]
        self.chars = align_characters(self.text, self.line, self.tokens)

    def test_spaces_map_to_original_indices(self):
        self.assertEqual([c.start for c in self.chars], [0, 1, 3, 4, 6, 7, 8])

    def test_partial_match_uses_char_bounds_and_full_height(self):
        rect = character_sub_rect(self.line, self.text, self.chars, (3, 5), 2)
        self.assertAlmostEqual(rect[0], 16.9)
        self.assertEqual(rect[1], -0.5)
        self.assertAlmostEqual(rect[2], 13.7)
        self.assertEqual(rect[3], 11.0)

    def test_grouped_word_falls_back(self):
        self.assertEqual(align_characters("张三", self.line, [("张三", .99, self.line)]), [])

    def test_missing_character_falls_back(self):
        self.assertEqual(align_characters(self.text, self.line, self.tokens[:-1]), [])

    def test_changed_character_falls_back(self):
        tokens = list(self.tokens)
        tokens[0] = ("性", .99, tokens[0][2])
        self.assertEqual(align_characters(self.text, self.line, tokens), [])

    def test_wrong_row_falls_back(self):
        tokens = [(c, score, box(0, 100, 10, 120)) for c, score, _ in self.tokens]
        self.assertEqual(align_characters(self.text, self.line, tokens), [])

    def test_non_finite_geometry_falls_back(self):
        self.assertEqual(align_characters("a", self.line, [("a", .99, box(0, 0, float("nan"), 20))]), [])

    def test_non_finite_score_falls_back(self):
        self.assertEqual(align_characters("a", self.line, [("a", float("nan"), box(0, 0, 10, 20))]), [])

    def test_low_confidence_falls_back(self):
        self.chars[1].confidence = .4
        self.assertIsNone(character_sub_rect(self.line, self.text, self.chars, (3, 5), 2))

    def test_reversed_character_order_falls_back(self):
        self.chars[1].box = self.chars[0].box
        self.assertIsNone(character_sub_rect(self.line, self.text, self.chars, (3, 5), 2))

    def test_rotated_line_falls_back(self):
        self.assertIsNone(character_sub_rect(box(0, 0, 20, 140), self.text, self.chars, (3, 5), 2))

    def test_bad_span_falls_back(self):
        for span in ((-1, 2), (3, 30), (5, 3), (3, 3)):
            self.assertIsNone(character_sub_rect(self.line, self.text, self.chars, span, 2))

    def test_bad_scale_falls_back(self):
        for scale in (0, -1, float("nan")):
            self.assertIsNone(character_sub_rect(self.line, self.text, self.chars, (3, 5), scale))

    def test_legacy_iterator_still_returns_two_values(self):
        result = OCRResult(self.text, self.line, self.chars, .99, "rapidocr")
        self.assertEqual(list(iter_ocr_lines([result])), [(self.line, self.text)])

    def test_worker_preserves_explicit_geometry_settings(self):
        worker = OCRWorker("unused.pdf", [], False, "", 2, 1, 0)
        with patch.object(worker, "_calculate_from_line", return_value=QRectF(1, 2, 3, 4)) as legacy:
            self.assertEqual(worker.calculate_sub_rect(self.line, self.text, (3, 5), chars=self.chars),
                             QRectF(1, 2, 3, 4))
        legacy.assert_called_once()

    def test_worker_uses_legacy_when_chars_absent(self):
        worker = OCRWorker("unused.pdf", [], False, "", 2, 0, 0)
        with patch.object(worker, "_calculate_from_line", return_value=QRectF(1, 2, 3, 4)) as legacy:
            worker.calculate_sub_rect(self.line, self.text, (3, 5), chars=[])
        legacy.assert_called_once()

    def test_mixed_block_keeps_chars_and_offsets_once(self):
        result = OCRResult(self.text, self.line, self.chars, .99, "rapidocr")
        records = []
        hits = collect_image_block_ocr_hits(
            None, ["张三"], 2, lambda _img: [result],
            calculate_rect_fn=lambda *_: self.fail("Eligible characters should be used"),
            calculate_char_rect_fn=lambda b, t, span, _img, chars: QRectF(*character_sub_rect(b,t,chars,span,2)),
            clip_to_page_rect_fn=lambda r, clip: r.translated(clip[0], clip[1]),
            image_clip_rects=[(100, 200, 250, 230)],
            render_clip_fn=lambda *_: np.arange(200, dtype=np.uint8).reshape(10,20),
            ocr_char_lines_sink=records,
        )
        self.assertAlmostEqual(hits[0][0].x(), 116.9)
        self.assertEqual(hits[0][0].y(), 199.5)
        self.assertAlmostEqual(hits[0][0].width(), 13.7)
        self.assertEqual(records[0][3], self.chars)

    def test_engine_does_not_change_text_when_char_alignment_rejected(self):
        engine = RapidOCREngine()
        engine._engine = Mock(return_value=SimpleNamespace(
            boxes=[self.line], txts=[self.text], scores=[.91], word_results=[[]]))
        with patch.object(RapidOCREngine, '_shared_init_failed', False):
            result = engine.recognize(np.zeros((20, 140, 3), dtype=np.uint8))[0]
        self.assertEqual(result.text, self.text)
        self.assertEqual(result.chars, [])
        self.assertEqual(result.confidence, .91)

    def test_engine_switch_is_passed_under_shared_lock(self):
        engine = RapidOCREngine(enable_char_boxes=True)
        engine._engine = Mock(return_value=SimpleNamespace(
            boxes=[self.line], txts=[self.text], scores=[.91], word_results=[self.tokens]))
        with patch.object(RapidOCREngine, '_shared_init_failed', False):
            engine.recognize(np.zeros((20, 140, 3), dtype=np.uint8))
        self.assertTrue(engine._engine.call_args.kwargs['return_word_box'])

    def test_malformed_optional_word_results_keep_the_ocr_line(self):
        engine = RapidOCREngine(enable_char_boxes=True)
        engine._engine = Mock(return_value=SimpleNamespace(
            boxes=[self.line], txts=[self.text], scores=[.91], word_results=123))
        with patch.object(RapidOCREngine, '_shared_init_failed', False):
            result = engine.recognize(np.zeros((20,140,3),dtype=np.uint8))
        self.assertEqual(result[0].text,self.text)
        self.assertEqual(result[0].chars,[])

    def test_experimental_alignment_is_disabled_by_default(self):
        engine = RapidOCREngine()
        self.assertFalse(engine.enable_char_boxes)

    def test_stable_call_resets_shared_options_after_experiment(self):
        shared = Mock(return_value=SimpleNamespace(boxes=None, txts=None))
        shared.return_word_box = True
        shared.return_single_char_box = True
        engine = RapidOCREngine()
        with patch.object(RapidOCREngine, '_shared_engine', shared), \
                patch.object(RapidOCREngine, '_shared_init_failed', False):
            engine.recognize(np.zeros((20,140,3),dtype=np.uint8))
        self.assertFalse(shared.return_word_box)
        self.assertFalse(shared.return_single_char_box)


if __name__ == "__main__":
    unittest.main()
