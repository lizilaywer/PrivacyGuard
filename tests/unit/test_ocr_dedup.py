"""P2 跨源去重：dedup_page_rects 单元测试。

混合 PDF 中同一敏感文字可能同时被文本层 search_for 和图片块 OCR 命中，
产生重叠遮罩 + 报告计数虚高。dedup_page_rects 按 IoU>=0.5 抑制后到者。
"""
import unittest

try:
    from PyQt6.QtCore import QRectF
    from privacyguard.workers.ocr_worker import dedup_page_rects
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "PyQt6 或 ocr_worker 不可导入")
class TestDedupPageRects(unittest.TestCase):

    def _hit(self, x, y, w, h, rule="x"):
        return {'rect': QRectF(x, y, w, h), 'replace_text': '', 'rule': rule}

    def test_empty_and_single_passthrough(self):
        self.assertEqual(dedup_page_rects([]), [])
        one = [self._hit(0, 0, 10, 10)]
        self.assertEqual(dedup_page_rects(one), one)

    def test_high_overlap_suppressed(self):
        # 文本层命中与图 OCR 命中高度重叠（同一区域）→ 后到者被抑制
        a = self._hit(10, 10, 40, 20, rule="文本")
        b = self._hit(11, 10, 40, 20, rule="ocr")  # 与 a IoU > 0.5
        out = dedup_page_rects([a, b])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['rule'], "文本")  # 保留插入序先到者

    def test_non_overlapping_kept(self):
        a = self._hit(0, 0, 10, 10)
        b = self._hit(100, 100, 10, 10)
        out = dedup_page_rects([a, b])
        self.assertEqual(len(out), 2)

    def test_low_overlap_kept(self):
        # 轻微重叠（< 0.5）不抑制
        a = self._hit(0, 0, 20, 20)
        b = self._hit(18, 0, 20, 20)  # 重叠 2x20=40，并集 400+400-40=760，IoU≈0.05
        out = dedup_page_rects([a, b])
        self.assertEqual(len(out), 2)

    def test_preserves_insertion_order(self):
        a = self._hit(0, 0, 10, 10, "文本")
        b = self._hit(50, 50, 10, 10, "印章")
        c = self._hit(1, 1, 9, 9, "ocr")  # 与 a 高度重叠
        out = dedup_page_rects([a, b, c])
        self.assertEqual([h['rule'] for h in out], ["文本", "印章"])


if __name__ == "__main__":
    unittest.main()
