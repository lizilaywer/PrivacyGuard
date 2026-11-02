import unittest
from types import SimpleNamespace

from privacyguard.ocr.mixed_pdf import (
    collect_embedded_image_clip_rects,
    collect_image_block_ocr_hits,
)


class FakeRect:
    def __init__(self, x, y, width, height):
        self._x = x
        self._y = y
        self._width = width
        self._height = height

    def x(self):
        return self._x

    def y(self):
        return self._y

    def width(self):
        return self._width

    def height(self):
        return self._height


class TestMixedPdfOcr(unittest.TestCase):

    def test_collect_embedded_image_clip_rects_filters_duplicates_and_tiny_blocks(self):
        page_dict = {
            "blocks": [
                {"type": 0, "bbox": (0, 0, 100, 20)},
                {"type": 1, "bbox": (10, 20, 210, 120)},
                {"type": 1, "bbox": (10, 20, 210, 120)},
                {"type": 1, "bbox": (0, 0, 5, 5)},
            ]
        }

        clip_rects = collect_embedded_image_clip_rects(page_dict)

        self.assertEqual(clip_rects, [(10.0, 20.0, 210.0, 120.0)])

    def test_collect_image_block_ocr_hits_offsets_rects_back_to_page_coordinates(self):
        rendered = []
        page = object()
        image_clip_rects = [(100.0, 200.0, 300.0, 320.0)]

        def render_clip(_page, clip_rect, _scan_scale):
            rendered.append(clip_rect)
            return SimpleNamespace(size=1)

        def recognize(_scan_img):
            return [SimpleNamespace(box=[[0, 0], [60, 0], [60, 20], [0, 20]], text="手机号 13812345678")]

        def calculate_rect(_box, _text, _span, _scan_img):
            return FakeRect(12.0, 8.0, 40.0, 14.0)

        def offset_rect(local_rect, clip_rect):
            return (
                local_rect.x() + clip_rect[0],
                local_rect.y() + clip_rect[1],
                local_rect.width(),
                local_rect.height(),
            )

        hit_rects = collect_image_block_ocr_hits(
            page,
            [r"1[3-9]\d{9}"],
            scan_scale=2.0,
            recognize_fn=recognize,
            calculate_rect_fn=calculate_rect,
            clip_to_page_rect_fn=offset_rect,
            render_clip_fn=render_clip,
            image_clip_rects=image_clip_rects,
        )

        self.assertEqual(rendered, image_clip_rects)
        # v37.7.13 cp43: 返回值改为 (page_rect, matched_text) 元组
        # cp_person_name: 追加第 3 元素 rule_override（普通规则命中为 None）
        self.assertEqual(hit_rects, [((112.0, 208.0, 40.0, 14.0), "13812345678", None)])

    def test_render_failure_triggers_conservative_full_block_cover(self):
        """O2: 图片块渲染失败时应保守整块覆盖，而非静默跳过。"""
        page = object()
        image_clip_rects = [(100.0, 200.0, 300.0, 320.0)]

        def render_clip(_page, _clip_rect, _scan_scale):
            raise RuntimeError("模拟渲染失败")

        def cover(clip_rect):
            return (clip_rect[0], clip_rect[1],
                    clip_rect[2] - clip_rect[0], clip_rect[3] - clip_rect[1])

        hit_rects = collect_image_block_ocr_hits(
            page,
            [r"1[3-9]\d{9}"],
            scan_scale=2.0,
            recognize_fn=lambda img: [],
            calculate_rect_fn=lambda *a: None,
            clip_to_page_rect_fn=lambda *a: None,
            render_clip_fn=render_clip,
            image_clip_rects=image_clip_rects,
            on_block_failure_fn=cover,
        )

        # 整块覆盖：宽 200、高 120，原点 (100,200)
        # v37.7.13 cp43: 失败覆盖块 matched_text 为空字符串
        # cp_person_name: 追加第 3 元素 rule_override
        self.assertEqual(hit_rects, [((100.0, 200.0, 200.0, 120.0), "", None)])

    def test_ocr_failure_triggers_conservative_full_block_cover(self):
        """O2: 图片块 OCR 抛异常时也应保守整块覆盖。"""
        page = object()
        image_clip_rects = [(0.0, 0.0, 50.0, 60.0)]

        def recognize(_img):
            raise ValueError("模拟 OCR 失败")

        hit_rects = collect_image_block_ocr_hits(
            page,
            [r"1[3-9]\d{9}"],
            scan_scale=2.0,
            recognize_fn=recognize,
            calculate_rect_fn=lambda *a: None,
            clip_to_page_rect_fn=lambda *a: None,
            render_clip_fn=lambda *a: SimpleNamespace(size=1),
            image_clip_rects=image_clip_rects,
            on_block_failure_fn=lambda cr: (cr[0], cr[1], cr[2] - cr[0], cr[3] - cr[1]),
        )

        # v37.7.13 cp43: 失败覆盖块 matched_text 为空字符串
        # cp_person_name: 追加第 3 元素 rule_override
        self.assertEqual(hit_rects, [((0.0, 0.0, 50.0, 60.0), "", None)])

    def test_failure_without_callback_skips_silently_backward_compatible(self):
        """未提供回调时保持旧行为（跳过），保障向后兼容。"""
        hit_rects = collect_image_block_ocr_hits(
            object(),
            [r"1[3-9]\d{9}"],
            scan_scale=2.0,
            recognize_fn=lambda img: [],
            calculate_rect_fn=lambda *a: None,
            clip_to_page_rect_fn=lambda *a: None,
            render_clip_fn=lambda *a: (_ for _ in ()).throw(RuntimeError("fail")),
            image_clip_rects=[(0.0, 0.0, 50.0, 60.0)],
        )
        self.assertEqual(hit_rects, [])

    def test_blank_render_triggers_conservative_cover(self):
        """v40.2.1: 损坏 XObject 渲染成纯色图 → 保守整块覆盖（防静默漏检）。"""
        import numpy as np

        def render_blank(_p, _c, _s):
            return np.full((60, 50, 3), 128, dtype=np.uint8)  # 纯灰无对比

        hit_rects = collect_image_block_ocr_hits(
            object(), [r"1[3-9]\d{9}"], scan_scale=2.0,
            recognize_fn=lambda img: [],
            calculate_rect_fn=lambda *a: None,
            clip_to_page_rect_fn=lambda *a: None,
            render_clip_fn=render_blank,
            image_clip_rects=[(0.0, 0.0, 50.0, 60.0)],
            on_block_failure_fn=lambda cr: (cr[0], cr[1], cr[2] - cr[0], cr[3] - cr[1]),
        )
        self.assertEqual(hit_rects, [((0.0, 0.0, 50.0, 60.0), "", None)])

    def test_normal_dynamic_range_render_not_covered(self):
        """v40.2.1: 正常文档图（有灰度对比）不触发空白覆盖。"""
        import numpy as np

        def render_normal(_p, _c, _s):
            arr = np.full((60, 50, 3), 200, dtype=np.uint8)
            arr[10:40, 5:45] = 40  # 黑字区域，动态范围大
            return arr

        calls = []

        def recognize(img):
            calls.append(1)
            return [SimpleNamespace(box=[[0, 0], [60, 0], [60, 20], [0, 20]], text="张三")]

        hit_rects = collect_image_block_ocr_hits(
            object(), [r"张三"], scan_scale=2.0,
            recognize_fn=recognize,
            calculate_rect_fn=lambda *a: FakeRect(1.0, 1.0, 30.0, 12.0),
            clip_to_page_rect_fn=lambda l, c: (l.x(), l.y(), l.width(), l.height()),
            render_clip_fn=render_normal,
            image_clip_rects=[(0.0, 0.0, 100.0, 60.0)],
        )
        self.assertTrue(calls)  # 正常图走 OCR 而非覆盖
        self.assertEqual(len(hit_rects), 1)

    def _run_bank_pattern_ocr(self, ocr_text):
        """辅助：用银行卡 pattern 对一段 OCR 文本跑图片块命中采集，返回 matched_text 列表。"""
        bank_pattern = r"(?<!\d)([1-9]\d{12,18})(?!\d)"

        def recognize(_img):
            return [SimpleNamespace(box=[[0, 0], [60, 0], [60, 20], [0, 20]], text=ocr_text)]

        hit_rects = collect_image_block_ocr_hits(
            object(),
            [bank_pattern],
            scan_scale=2.0,
            recognize_fn=recognize,
            calculate_rect_fn=lambda *a: FakeRect(1.0, 1.0, 30.0, 12.0),
            clip_to_page_rect_fn=lambda local, clip: (local.x(), local.y(), local.width(), local.height()),
            render_clip_fn=lambda *a: SimpleNamespace(size=1),
            image_clip_rects=[(0.0, 0.0, 100.0, 60.0)],
        )
        return [matched for _rect, matched, _rule in hit_rects]

    def test_case_number_filtered_in_image_ocr(self):
        """cp55: 图片 OCR 路径中不满足 Luhn 的案件编号应被过滤，不产生命中。"""
        matched = self._run_bank_pattern_ocr("编号 13417202010172812 结案")
        self.assertEqual(matched, [])

    def test_valid_bank_card_hit_in_image_ocr(self):
        """满足 Luhn 的银行卡号应在图片 OCR 路径产生命中。"""
        matched = self._run_bank_pattern_ocr("卡号 4111111111111111 有效")
        self.assertEqual(matched, ["4111111111111111"])


if __name__ == "__main__":
    unittest.main()
