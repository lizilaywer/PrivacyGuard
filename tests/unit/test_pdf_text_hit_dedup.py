from types import SimpleNamespace
import unittest

from privacyguard.ocr.text_pdf import (
    collect_text_pdf_hit_boxes,
    _merge_adjacent_same_line_rects,
)


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


def _rect(x0, y0, x1, y1):
    """构造类 fitz.Rect 对象（含 x0/y0/x1/y1/width/height）。"""
    return SimpleNamespace(x0=x0, y0=y0, x1=x1, y1=y1,
                           width=x1 - x0, height=y1 - y0)


class TestTextPdfHitDedup(unittest.TestCase):

    def test_repeated_text_only_searched_once(self):
        page = FakePage(
            "甲方与甲方签约，甲方联系电话。",
            {
                "甲方": [
                    _rect(1, 2, 4, 6),
                    _rect(5, 6, 12, 14),
                    _rect(9, 10, 20, 22),
                ]
            },
        )

        boxes = collect_text_pdf_hit_boxes(page, [r"甲方"])

        self.assertEqual(page.search_calls, ["甲方"])
        self.assertEqual(len(boxes), 3)

    def test_invalid_regex_is_ignored(self):
        page = FakePage("甲方", {"甲方": [_rect(1, 2, 4, 6)]})
        boxes = collect_text_pdf_hit_boxes(page, [r"(", r"甲方"])
        self.assertEqual(page.search_calls, ["甲方"])
        self.assertEqual(len(boxes), 1)

    def test_merge_per_char_rects_on_same_line(self):
        """v37.7.17 cp48: 同一匹配被 PyMuPDF 拆分为多个 per-span rect 时应合并为单个。

        场景：搜索"王小明"（3 字），若每个字符是独立 text span，
        PyMuPDF 会返回 3 个 rect（每个 ~27pt 宽，gap ~10pt）。
        合并后应为 1 个 ~101pt 宽的 rect，避免生成 3 个独立遮罩。
        """
        hits = [
            _rect(447.06, 275.20, 474.06, 302.20),  # 刘
            _rect(484.29, 275.20, 511.29, 302.20),  # 少
            _rect(521.52, 275.20, 548.52, 302.20),  # 芳
        ]
        merged = _merge_adjacent_same_line_rects(hits)
        self.assertEqual(len(merged), 1)
        m = merged[0]
        self.assertAlmostEqual(m.x0, 447.06, places=2)
        self.assertAlmostEqual(m.x1, 548.52, places=2)
        self.assertAlmostEqual(m.width, 101.46, places=2)

    def test_merge_does_not_combine_separate_matches_on_same_line(self):
        """同一行两个独立匹配不应被错误合并。

        场景：同一行出现两次"王小明"，gap 远大于字符宽度，
        应保留为 2 个独立 rect。
        """
        hits = [
            _rect(210.00, 853.20, 313.52, 885.20),  # 第 1 个匹配（完整 1 rect）
            _rect(471.09, 853.20, 574.61, 885.20),  # 第 2 个匹配（完整 1 rect，gap=158pt）
        ]
        merged = _merge_adjacent_same_line_rects(hits)
        self.assertEqual(len(merged), 2)

    def test_merge_does_not_combine_rects_on_different_lines(self):
        """不同行的 rect 不应被合并。"""
        hits = [
            _rect(100, 100, 130, 130),
            _rect(100, 200, 130, 230),
            _rect(100, 300, 130, 330),
        ]
        merged = _merge_adjacent_same_line_rects(hits)
        self.assertEqual(len(merged), 3)

    def test_merge_empty_and_single(self):
        """空列表和单元素列表应原样返回。"""
        self.assertEqual(_merge_adjacent_same_line_rects([]), [])
        self.assertEqual(len(_merge_adjacent_same_line_rects([_rect(1, 2, 3, 4)])), 1)

    def test_collect_text_pdf_hit_boxes_merges_per_char_split(self):
        """端到端：collect_text_pdf_hit_boxes 应将 3 个 per-char rect 合并为 1 个。"""
        page = FakePage(
            "王小明",
            {
                "王小明": [
                    _rect(447.06, 275.20, 474.06, 302.20),
                    _rect(484.29, 275.20, 511.29, 302.20),
                    _rect(521.52, 275.20, 548.52, 302.20),
                ]
            },
        )
        boxes = collect_text_pdf_hit_boxes(page, [r"王小明"])
        self.assertEqual(len(boxes), 1)
        # cp_person_name: 6 元组（追加 rule_override，普通规则为 None）
        x0, y0, w, h, found, rule_override = boxes[0]
        self.assertAlmostEqual(w, 101.46, places=2)
        self.assertEqual(found, "王小明")
        self.assertIsNone(rule_override)


# config.json 默认银行卡号正则（同时锁定 cp58 的 _is_bank_card_pattern 能识别带前缀 pattern）
_BANK_PATTERN = r"(?<!\d)([1-9]\d{12,18})(?!\d)"


class TestTextPdfBoxQuality(unittest.TestCase):
    """端到端锁定文本型 PDF 命中框采集的脱敏质量（Luhn / 身份证排除 / 印章哨兵）。"""

    def test_case_number_filtered_from_boxes(self):
        """cp55: 不满足 Luhn 的案件编号不应产生命中框，且不会去 search_for。"""
        page = FakePage(
            "案件编号13417202010172812结案。",
            {"13417202010172812": [_rect(10, 10, 120, 30)]},
        )
        boxes = collect_text_pdf_hit_boxes(page, [_BANK_PATTERN])
        self.assertEqual(boxes, [])
        self.assertEqual(page.search_calls, [])

    def test_valid_bank_card_produces_box(self):
        """满足 Luhn 的真实银行卡号应正常产生命中框。"""
        page = FakePage(
            "卡号4111111111111111有效。",
            {"4111111111111111": [_rect(10, 10, 120, 30)]},
        )
        boxes = collect_text_pdf_hit_boxes(page, [_BANK_PATTERN])
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0][4], "4111111111111111")

    def test_idcard_preserved_under_bank_pattern(self):
        """cp56: 18 位身份证号即使落入银行卡 pattern 数字区间，也不应被 Luhn 误伤。"""
        idcard = "110101199003077710"
        page = FakePage(
            f"身份证{idcard}。",
            {idcard: [_rect(10, 10, 150, 30)]},
        )
        boxes = collect_text_pdf_hit_boxes(page, [_BANK_PATTERN])
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0][4], idcard)

    def test_seal_sentinel_not_searched(self):
        """__SEAL_DETECTION__ 哨兵应被文本路径跳过，不当作字面量去搜索。"""
        page = FakePage("公章文本", {})
        boxes = collect_text_pdf_hit_boxes(page, ["__SEAL_DETECTION__"])
        self.assertEqual(boxes, [])
        self.assertEqual(page.search_calls, [])

    def test_overlapping_rects_not_merged(self):
        """重叠（负间隙）的 rect 不应被相邻合并处理（交由下游去重）。"""
        hits = [
            _rect(100, 100, 140, 130),
            _rect(120, 100, 160, 130),  # x0=120 < 前一个 x1=140 → gap=-20
        ]
        merged = _merge_adjacent_same_line_rects(hits)
        self.assertEqual(len(merged), 2)


if __name__ == "__main__":
    unittest.main()
