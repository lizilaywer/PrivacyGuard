# -*- coding: utf-8 -*-
"""cp_person_name 三管线集成测试：文字层 PDF / OCR 图片块 / Word。

验证核心语义：
1. 只遮人名子串（不含称谓词）
2. "发现即全页遮"——同页/同块/全文档其他位置的同名一并遮
3. 命中携带规则名 override（"称谓人名"，防内容反查误分类）
4. 规则未传入时三管线行为与改动前完全一致（零回归）
"""
import unittest
from types import SimpleNamespace

from privacyguard.ocr.person_name import (
    build_person_name_pattern,
    DEFAULT_TITLES,
    PERSON_NAME_RULE_NAME,
)
from privacyguard.ocr.text_pdf import collect_text_pdf_hit_boxes
from privacyguard.ocr.mixed_pdf import collect_image_block_ocr_hits


class FakePage:
    """参照 test_pdf_text_hit_dedup 的 FakePage。"""

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
    return SimpleNamespace(x0=x0, y0=y0, x1=x1, y1=y1,
                           width=x1 - x0, height=y1 - y0)


class FakeRect:
    def __init__(self, x, y, width, height):
        self._x, self._y, self._w, self._h = x, y, width, height

    def x(self):
        return self._x

    def y(self):
        return self._y

    def width(self):
        return self._w

    def height(self):
        return self._h


PN_PATTERN = build_person_name_pattern(DEFAULT_TITLES)


class TestTextLayerPipeline(unittest.TestCase):
    """文字层 PDF：collect_text_pdf_hit_boxes。"""

    def test_masks_name_only_and_all_occurrences(self):
        """核心语义：只搜人名子串（不搜"被告人张三"整串）；
        search_for(人名) 返回该页所有同名位置 → 全页遮。"""
        page = FakePage(
            "被告人张三，男。张三于2024年到案，被害人李四指认张三。",
            {
                "张三": [_rect(10, 10, 40, 30), _rect(100, 10, 130, 30),
                        _rect(200, 10, 230, 30)],
                "李四": [_rect(150, 10, 180, 30)],
            },
        )
        boxes = collect_text_pdf_hit_boxes(page, [PN_PATTERN])

        # 只 search 人名子串，绝不 search 整串"被告人张三"
        self.assertIn("张三", page.search_calls)
        self.assertIn("李四", page.search_calls)
        self.assertNotIn("被告人张三", page.search_calls)

        # 张三 3 处（称谓处 + 2 处独立出现）+ 李四 1 处
        by_name = {}
        for x, y, w, h, found, rule in boxes:
            by_name.setdefault(found, []).append(rule)
        self.assertEqual(len(by_name.get("张三", [])), 3)
        self.assertEqual(len(by_name.get("李四", [])), 1)

        # 全部命中携带规则名 override
        for _x, _y, _w, _h, found, rule in boxes:
            self.assertEqual(rule, PERSON_NAME_RULE_NAME)

    def test_rejected_candidates_not_searched(self):
        """被否决的候选（"当庭供述"）不产生 search_for。"""
        page = FakePage("被告人当庭供述，自愿认罪。", {})
        boxes = collect_text_pdf_hit_boxes(page, [PN_PATTERN])
        self.assertEqual(boxes, [])
        self.assertEqual(page.search_calls, [])

    def test_person_pattern_mixed_with_regular(self):
        """称谓 pattern 与普通规则混传：普通规则不受影响。"""
        page = FakePage(
            "被告人张三，电话13812345678。",
            {"张三": [_rect(10, 10, 40, 30)],
             "13812345678": [_rect(60, 10, 160, 30)]},
        )
        boxes = collect_text_pdf_hit_boxes(page, [PN_PATTERN, r"1[3-9]\d{9}"])
        rules = {found: rule for _x, _y, _w, _h, found, rule in boxes}
        self.assertEqual(rules.get("张三"), PERSON_NAME_RULE_NAME)
        self.assertIsNone(rules.get("13812345678"))  # 普通规则 override=None

    def test_no_person_pattern_no_regression(self):
        """规则未传入时行为与改动前一致（override 全 None）。"""
        page = FakePage("甲方与甲方签约。", {"甲方": [_rect(1, 2, 4, 6)]})
        boxes = collect_text_pdf_hit_boxes(page, [r"甲方"])
        self.assertEqual(len(boxes), 1)
        self.assertIsNone(boxes[0][5])


class TestOcrPipeline(unittest.TestCase):
    """OCR 图片块：collect_image_block_ocr_hits 块内两遍法。"""

    def _run(self, ocr_lines, patterns):
        spans = []

        def recognize(_img):
            return [SimpleNamespace(box=[[0, 0], [60, 0], [60, 20], [0, 20]], text=t)
                    for t in ocr_lines]

        def calculate_rect(_box, text, span, _scan_img):
            spans.append((text, span))
            return FakeRect(1.0, 1.0, 30.0, 12.0)

        hit_rects = collect_image_block_ocr_hits(
            object(), patterns, scan_scale=2.0,
            recognize_fn=recognize,
            calculate_rect_fn=calculate_rect,
            clip_to_page_rect_fn=lambda l, c: (l.x(), l.y(), l.width(), l.height()),
            render_clip_fn=lambda *a: SimpleNamespace(size=1),
            image_clip_rects=[(0.0, 0.0, 100.0, 60.0)],
        )
        return hit_rects, spans

    def test_two_pass_full_block_masking(self):
        """两遍法：第 1 行称谓发现"张三"后，第 2 行独立出现的"张三"也遮。"""
        hit_rects, _spans = self._run(
            ["被告人张三，男", "张三于2024年到案"],
            [PN_PATTERN],
        )
        matched = [m for _r, m, _rule in hit_rects]
        # 两行各命中一次"张三"（都是人名子串，不含称谓）
        self.assertEqual(matched.count("张三"), 2)
        for _r, m, rule in hit_rects:
            self.assertEqual(m, "张三")
            self.assertEqual(rule, PERSON_NAME_RULE_NAME)

    def test_rejected_line_no_hit(self):
        """否决行（"当庭供述"）不产生命中。"""
        hit_rects, _spans = self._run(["被告人当庭供述"], [PN_PATTERN])
        self.assertEqual(hit_rects, [])

    def test_regular_pattern_unaffected(self):
        """普通规则与称谓规则混传：互不干扰。"""
        hit_rects, _spans = self._run(
            ["被告人张三 13812345678"],
            [PN_PATTERN, r"1[3-9]\d{9}"],
        )
        rules = {m: rule for _r, m, rule in hit_rects}
        self.assertEqual(rules.get("张三"), PERSON_NAME_RULE_NAME)
        self.assertIsNone(rules.get("13812345678"))


class TestWordPipeline(unittest.TestCase):
    """Word：WordWorker._find_matches + 收集 pass。"""

    def _make_worker(self, rules):
        # 不启动 QThread，仅构造实例用其方法（与 test_word_replace_rules 同模式）
        from privacyguard.workers.word_worker import WordWorker
        return WordWorker(None, {}, rules, "", "[已脱敏]")

    def test_name_substring_and_global_masking(self):
        """称谓处命中人名子串（偏移指向人名）；收集 pass 的人名全条目遮。"""
        w = self._make_worker([PN_PATTERN])
        text = "被告人张三，男。张三于2024年到案。"
        matches = w._find_matches(text, person_names={"张三"})
        zhang = [m for m in matches if m["text"] == "张三"]
        # 称谓处 1 次 + 独立出现 1 次 = 2 次
        self.assertEqual(len(zhang), 2)
        for m in zhang:
            self.assertEqual(m["rule_name"], "称谓人名")
            self.assertEqual(text[m["start"]:m["end"]], "张三")
        # span 去重（无重复 start/end）
        spans = [(m["start"], m["end"]) for m in zhang]
        self.assertEqual(len(spans), len(set(spans)))

    def test_collect_pass(self):
        """收集 pass：跨条目收集人名集合。"""
        w = self._make_worker([PN_PATTERN])
        output = {
            "p1": {"text": "被告人张三到庭。"},
            "p2": {"text": "被害人李四陈述。"},
        }
        names = w._collect_person_names(output, list(output.keys()))
        self.assertEqual(names, {"张三", "李四"})

    def test_no_pattern_zero_overhead(self):
        """规则未启用：收集 pass 返回空集，_find_matches 无称谓分支。"""
        w = self._make_worker([r"1[3-9]\d{9}"])
        self.assertEqual(w._collect_person_names({}, []), set())
        matches = w._find_matches("被告人张三，男。", person_names=None)
        self.assertEqual(matches, [])


class TestBackfill(unittest.TestCase):
    """v40.2.3 文档级回填：后页锚定发现的人名，前页孤立出现处（签名行）补遮。"""

    def _make_real_worker(self):
        from privacyguard.workers.ocr_worker import OCRWorker
        return OCRWorker("nonexistent.pdf", [], False, "", 1.5, 0, 0)

    def test_backfill_covers_early_pages(self):
        """第 1 页孤立人名行（无锚点），后页锚定发现后回填第 1 页。"""
        import fitz as _fitz
        from PyQt6.QtCore import QRectF
        from privacyguard.ocr.person_name import PERSON_NAME_RULE_NAME

        doc = _fitz.open()
        p1 = doc.new_page()
        # china-s 字体（默认 helv 不支持中文，写入会变空内容）
        p1.insert_text(_fitz.Point(72, 72), "吴良富", fontname="china-s")
        doc.new_page()

        w = self._make_real_worker()
        w._pn_shared = {"吴良富"}
        w._pn_first_rects = {0: [], 1: [{'rect': QRectF(1, 1, 10, 10), 'replace_text': '', 'rule': PERSON_NAME_RULE_NAME}]}
        w._pn_text_cache = {0: "吴良富\n身份证复印件\n"}
        w._pn_lines_cache = {0: []}

        emitted = []
        w.page_result_signal.connect(lambda pno, rects: emitted.append((pno, rects)))
        w._pn_backfill(doc)
        doc.close()

        # 第 1 页被回填（孤立"吴良富"补遮），第 2 页无增量不重发
        self.assertEqual([p for p, _ in emitted], [0])
        pno, rects = emitted[0]
        self.assertTrue(any(r['rule'] == PERSON_NAME_RULE_NAME for r in rects))

    def test_backfill_skips_when_empty(self):
        import fitz as _fitz
        doc = _fitz.open()
        doc.new_page()
        w = self._make_real_worker()
        w._pn_shared = set()
        emitted = []
        w.page_result_signal.connect(lambda pno, rects: emitted.append(1))
        w._pn_backfill(doc)  # 空集合直接返回
        doc.close()
        self.assertEqual(emitted, [])


if __name__ == "__main__":
    unittest.main()
