"""Regression coverage for one rule and one replacement per full phrase."""

import unittest

import fitz
import numpy as np
from PyQt6.QtCore import QRectF

from privacyguard.ocr.mixed_pdf import collect_image_block_ocr_hits
from privacyguard.ocr.pdf_keyword_hits import collect_pdf_keyword_hits
from privacyguard.utils.helpers_bookmark import redact_toc_titles
from privacyguard.utils.helpers_pdf import effective_pdf_export_masks
from privacyguard.utils.helpers_word_preview import resolve_word_ocr_replacements
from privacyguard.utils.literal_keywords import compile_keyword_patterns, iter_keyword_matches
from privacyguard.workers.ocr_worker import OCRWorker
from privacyguard.workers.word_worker import WordWorker


class LiteralKeywordTests(unittest.TestCase):
    def setUp(self):
        self.rules = [{"find": "2025年", "replace": "2026", "enabled": True},
                      {"find": "年", "replace": "X", "enabled": False}]

    def test_same_literal_phrase_with_layout_spaces(self):
        text = "原2025 年 正2025年 留2026年 12025年 2025 年级"
        hits = list(iter_keyword_matches(text, compile_keyword_patterns(["2025年"])))
        self.assertEqual([text[s:e] for s, e, _ in hits], ["2025 年", "2025年", "2025 年"])
        self.assertEqual(list(iter_keyword_matches("2025\n年", compile_keyword_patterns(["2025年"]))), [])

    def test_worker_consumes_authoritative_rows_and_legacy_keeps_lines(self):
        worker = OCRWorker("", [], False, "2025\n年", 1, 0, 0, custom_keyword_rules=self.rules)
        self.assertEqual(list(worker.keyword_replace_map), ["2025年"])
        self.assertEqual(worker._lookup_replace("2025年"), "2026")
        old = OCRWorker("", [], False, "New York\nOther", 1, 0, 0)
        self.assertEqual(list(old.keyword_replace_map), ["New York", "Other"])

    def test_pdf_one_box_per_occurrence_even_across_fonts_and_rotations(self):
        with fitz.open() as pdf:
            page = pdf.new_page(width=450, height=260)
            page.insert_text((35, 55), "2025", fontsize=15)
            page.insert_text((71, 55), "年预算", fontsize=13, fontname="china-s")
            page.insert_text((35, 90), "2026 年预算", fontsize=14, fontname="china-s")
            page.insert_text((35, 120), "2025", fontsize=15)
            page.insert_text((220, 120), "年", fontsize=13, fontname="china-s")
            for angle in (0, 90, 180, 270):
                page.set_rotation(angle)
                hits = list(collect_pdf_keyword_hits(page, compile_keyword_patterns(["2025 年"])))
                self.assertEqual(len(hits), 1)
                rect, rule = hits[0]
                self.assertEqual(rule, "2025 年")
                original = rect * page.derotation_matrix
                self.assertEqual("".join(page.get_textbox(original).split()), "2025年")

    def test_mixed_ocr_never_matches_year_marker_independently(self):
        text = "2025 年预算与2026 年预算"
        box = [(0, 0), (110, 0), (110, 12), (0, 12)]
        image = np.array([0, 255], dtype=np.uint8)
        hits = collect_image_block_ocr_hits(
            object(), [], 1, lambda _image: [(box, text)],
            lambda _, line, span, _image: line[span[0]:span[1]], lambda literal, _clip: literal,
            render_clip_fn=lambda *_args: image, image_clip_rects=[(0, 0, 110, 20)],
            keyword_patterns=compile_keyword_patterns(["2025年"]),
        )
        self.assertEqual(hits, [("2025 年", "2025年", "自定义关键词")])

    def test_word_preview_uses_the_same_rule_for_the_complete_match(self):
        worker = WordWorker(None, {}, [], "2025\n年", "[已脱敏]", custom_keyword_rules=self.rules)
        text = "2025 年预算与2026年预算"
        hits = worker._find_matches(text)
        (hit,) = resolve_word_ocr_replacements(hits, self.rules, "[已脱敏]")
        self.assertEqual((hit["text"], hit["replacement"]), ("2025 年", "2026"))

    def test_bookmarks_match_whole_phrases_and_do_not_replace_inserted_text(self):
        toc = [[1, "2025 年预算与2026年预算", 1]]
        self.assertEqual(redact_toc_titles(toc, self.rules), [[1, "2026预算与2026年预算", 1]])
        rules = self.rules + [{"find": "2026", "replace": "原有年份"}]
        self.assertEqual(redact_toc_titles(toc, rules), [[1, "2026预算与原有年份年预算", 1]])

    def test_overlaid_manual_and_keyword_hits_export_once(self):
        shared = QRectF(20, 15, 35, 10)
        auto = {"rect": shared, "replace_text": "first"}
        manual = {"rect": QRectF(shared), "replace_text": "on top"}
        other = {"rect": QRectF(55, 15, 20, 10), "replace_text": "second position"}
        state = {0: {"ocr": [auto, other], "manual": [manual]}}
        self.assertEqual(effective_pdf_export_masks(state), {0: {"ocr": [other], "manual": [manual]}})
        self.assertEqual(state[0]["ocr"], [auto, other])
