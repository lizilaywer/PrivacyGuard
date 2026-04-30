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
        self.assertEqual(hit_rects, [(112.0, 208.0, 40.0, 14.0)])


if __name__ == "__main__":
    unittest.main()
