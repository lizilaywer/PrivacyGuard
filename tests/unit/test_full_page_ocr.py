"""tests/unit/test_full_page_ocr.py — RED 契约。

D-03 / W-B:
- `collect_full_page_ocr_hits` 必须是 dependency-injection 形态（recognize_fn / calculate_rect_fn）。
- 必须返回 [(x, y, w, h), ...] 在页面坐标系（与 collect_image_block_ocr_hits 形态一致）。
- 渲染失败 / OCR 失败 / 空结果 → 返回 []（不抛）。
- `_ModularOCRWorker` 必须暴露 `pii_signal` 信号 + `pii_engine_enabled` / `pii_settings` __init__ 参数。
- Worker run loop 必须把 detect 结果路由进 pii_signal，但**不**直接调 `collect_full_page_ocr_hits`（W-B）。
"""
import inspect
import unittest
from unittest.mock import MagicMock, patch

import numpy as np


class TestCollectFullPageOcrHitsSignature(unittest.TestCase):
    """D-03 DI 形态契约（test(01-03) RED）。"""

    def test_module_is_dead_code_marked(self):
        """模块 docstring 必须以 'DEAD CODE — Phase 1 library export.' 开头（W2 reconciliation）。"""
        from privacyguard.ocr import full_page_ocr

        self.assertTrue(
            full_page_ocr.__doc__.startswith("DEAD CODE — Phase 1 library export."),
            "full_page_ocr.py 模块 docstring 必须以 'DEAD CODE — Phase 1 library export.' 开头；"
            "否则后续 reviewer 可能误以为这是未接线路径",
        )

    def test_render_full_page_to_bgr_returns_array(self):
        """render_full_page_to_bgr(page, scan_scale) 返回 numpy ndarray。"""
        from privacyguard.ocr.full_page_ocr import render_full_page_to_bgr

        fake_page = MagicMock()
        # 构造一个 100x100x3 的 pixmap png 字节流
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=100, height=100)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0), alpha=False)
        png_bytes = pix.tobytes("png")
        fake_page.get_pixmap.return_value.tobytes.return_value = png_bytes
        result = render_full_page_to_bgr(fake_page, 1.0)
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, "shape"))
        doc.close()

    def test_render_full_page_to_bgr_handles_exception(self):
        """render_full_page_to_bgr 出错 → None。"""
        from privacyguard.ocr.full_page_ocr import render_full_page_to_bgr

        fake_page = MagicMock()
        fake_page.get_pixmap.side_effect = RuntimeError("mocked pixmap failure")
        result = render_full_page_to_bgr(fake_page, 1.0)
        self.assertIsNone(result)


class TestCollectFullPageOcrHits(unittest.TestCase):
    """D-03 整页 OCR 命中收集函数契约。"""

    def test_returns_list_on_render_failure(self):
        """渲染失败 → []（不抛）。"""
        from privacyguard.ocr.full_page_ocr import collect_full_page_ocr_hits

        fake_page = MagicMock()
        # 默认 render_fn 抛错
        with patch(
            "privacyguard.ocr.full_page_ocr.render_full_page_to_bgr",
            side_effect=RuntimeError("mocked render failure"),
        ):
            result = collect_full_page_ocr_hits(
                page=fake_page,
                scan_scale=2.0,
                recognize_fn=lambda img: [],
                calculate_rect_fn=lambda box, text, span, img: None,
            )
        self.assertEqual(result, [])

    def test_returns_list_on_recognize_failure(self):
        """OCR 失败 → []（不抛）。"""
        from privacyguard.ocr.full_page_ocr import (
            collect_full_page_ocr_hits,
            render_full_page_to_bgr,
        )

        fake_page = MagicMock()
        # 用一个真实 fitz page 让 render_fn 默认路径工作
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=200, height=200)
        # 把 fake_page 的 rect 设到真实 page 的 rect（用于 sx/sy 计算）
        fake_page.rect = page.rect

        def recognize_boom(_img):
            raise RuntimeError("mocked recognize failure")

        result = collect_full_page_ocr_hits(
            page=fake_page,
            scan_scale=1.0,
            recognize_fn=recognize_boom,
            calculate_rect_fn=lambda box, text, span, img: None,
        )
        self.assertEqual(result, [])
        doc.close()

    def test_returns_page_xy_tuples_for_ocr_lines(self):
        """OCR 返回有内容时 → 输出 (x, y, w, h) 元组（页面坐标）。"""
        from privacyguard.ocr.full_page_ocr import collect_full_page_ocr_hits

        import fitz
        doc = fitz.open()
        page = doc.new_page(width=200, height=200)

        # 注入一个真实可用的 render_fn，返回一个 100x100x3 的 BGR ndarray
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)

        def render_fn(_page, _scale):
            return fake_img

        # 模拟一个 OCR 行：box 是 [[x1,y1],...,[x4,y4]]，text 是字符串
        ocr_results = [
            ([[0, 0], [50, 0], [50, 20], [0, 20]], "13812345678"),
        ]

        def recognize_fn(_img):
            return ocr_results

        def calculate_rect_fn(box, text, span, img):
            # 返回 (x, y, w, h) 在 OCR 局部坐标系
            return (10.0, 5.0, 30.0, 15.0)

        result = collect_full_page_ocr_hits(
            page=page,
            scan_scale=1.0,
            recognize_fn=recognize_fn,
            calculate_rect_fn=calculate_rect_fn,
            render_fn=render_fn,
        )
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # 每个结果都是 4 元 tuple (x, y, w, h)
        for hit in result:
            self.assertEqual(len(hit), 4)
        doc.close()

    def test_skips_empty_text_lines(self):
        """OCR 行 text 为空 → 跳过（不调用 calculate_rect_fn）。"""
        from privacyguard.ocr.full_page_ocr import collect_full_page_ocr_hits

        import fitz
        doc = fitz.open()
        page = doc.new_page(width=200, height=200)

        called = []
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)

        def render_fn(_page, _scale):
            return fake_img

        def recognize_fn(_img):
            return [([[0, 0], [50, 0], [50, 20], [0, 20]], "")]

        def calculate_rect_fn(box, text, span, img):
            called.append(text)
            return (10.0, 5.0, 30.0, 15.0)

        result = collect_full_page_ocr_hits(
            page=page,
            scan_scale=1.0,
            recognize_fn=recognize_fn,
            calculate_rect_fn=calculate_rect_fn,
            render_fn=render_fn,
        )
        self.assertEqual(result, [])
        self.assertEqual(len(called), 0)
        doc.close()


class TestEagerReExport(unittest.TestCase):
    """__init__.py 必须立即 re-export collect_full_page_ocr_hits + render_full_page_to_bgr。"""

    def test_top_level_re_exports(self):
        from privacyguard.ocr import collect_full_page_ocr_hits, render_full_page_to_bgr

        self.assertTrue(callable(collect_full_page_ocr_hits))
        self.assertTrue(callable(render_full_page_to_bgr))


class TestModularOCRWorkerPIISignal(unittest.TestCase):
    """pii_signal + __init__ 扩展契约。"""

    def test_pii_engine_enabled_in_signature(self):
        """__init__ 必须包含 pii_engine_enabled: bool = False 默认值。"""
        from privacyguard.workers.ocr_worker import OCRWorker

        sig = inspect.signature(OCRWorker.__init__)
        self.assertIn("pii_engine_enabled", sig.parameters)
        self.assertIn("pii_settings", sig.parameters)

    def test_run_loop_uses_pii_signal(self):
        """run() 方法体内必须包含 pii_signal 调用（确认 D-04 wire 路径）。"""
        from privacyguard.workers.ocr_worker import OCRWorker

        src = inspect.getsource(OCRWorker.run)
        self.assertIn("pii_signal", src)
        self.assertIn("_detect_pii_for_page", src)

    def test_run_loop_does_not_invoke_collect_full_page_ocr_hits(self):
        """W-B: run loop 不得直接调 collect_full_page_ocr_hits（W2 reconciliation）。"""
        from privacyguard.workers.ocr_worker import OCRWorker

        src = inspect.getsource(OCRWorker.run)
        self.assertNotIn("collect_full_page_ocr_hits", src,
                         "Worker run loop 必须不直接调用 collect_full_page_ocr_hits；"
                         "full-page fallback 走 line 397-398 promotion through collect_image_block_ocr_hits（W2）")

    def test_run_loop_keeps_three_paths(self):
        """D-01: run loop 同时包含 text + image_block + PII 三路径。"""
        from privacyguard.workers.ocr_worker import OCRWorker

        src = inspect.getsource(OCRWorker.run)
        self.assertIn("collect_text_pdf_hit_boxes", src)
        self.assertIn("collect_image_block_ocr_hits", src)
        self.assertIn("PIIEngine", src)


if __name__ == "__main__":
    unittest.main()