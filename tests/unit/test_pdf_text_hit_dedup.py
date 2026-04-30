from types import SimpleNamespace
import unittest

from privacyguard.ocr.text_pdf import collect_text_pdf_hit_boxes


class FakePage:
    def __init__(self, text, hits_by_text):
        self._text = text
        self._hits_by_text = hits_by_text
        self.search_calls = []

    def get_text(self):
        return self._text

    def search_for(self, text):
        self.search_calls.append(text)
        return self._hits_by_text.get(text, [])


class TestTextPdfHitDedup(unittest.TestCase):

    def test_repeated_text_only_searched_once(self):
        page = FakePage(
            "甲方与甲方签约，甲方联系电话。",
            {
                "甲方": [
                    SimpleNamespace(x0=1, y0=2, width=3, height=4),
                    SimpleNamespace(x0=5, y0=6, width=7, height=8),
                    SimpleNamespace(x0=9, y0=10, width=11, height=12),
                ]
            },
        )

        boxes = collect_text_pdf_hit_boxes(page, [r"甲方"])

        self.assertEqual(page.search_calls, ["甲方"])
        self.assertEqual(len(boxes), 3)

    def test_invalid_regex_is_ignored(self):
        page = FakePage("甲方", {"甲方": [SimpleNamespace(x0=1, y0=2, width=3, height=4)]})
        boxes = collect_text_pdf_hit_boxes(page, [r"(", r"甲方"])
        self.assertEqual(page.search_calls, ["甲方"])
        self.assertEqual(len(boxes), 1)
