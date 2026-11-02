# -*- coding: utf-8 -*-
"""cp118 回归测试：审计修复稳定性（B1 rect_added 信号 / A5 image_merge Document 泄漏）。

B1: 纯遮罩路径（manual_replace_prompt 关闭）框选释放后应 emit rect_added，
    使主窗能触发 render_view + 撤销快照（此前仅 append 不 emit，撤销失效）。
A5: ImageMergeWorker 保存失败/取消时 PyMuPDF Document 必须被 close，
    不依赖 GC（此前 doc.save() 抛异常会跳过 doc.close() 导致泄漏）。
"""
import os
import shutil
import tempfile
import unittest

try:
    from PyQt6.QtCore import QPointF, QRectF, QEvent, Qt
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False

# cp65: main 模块依赖 QWebEngineWidgets，必须在任何 QApplication 创建前导入，
# 因此放在模块顶层（与 test_app_config.py 模式一致）。
try:
    from main import MainWindow
    HAS_MAIN = True
except Exception:  # pragma: no cover - 极端环境下 main 不可导入
    HAS_MAIN = False


@unittest.skipUnless(HAS_QT, "PyQt6 未安装")
class TestRectAddedSignal(unittest.TestCase):
    """B1: 纯遮罩路径补发 rect_added 信号。"""

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def _make_canvas(self):
        from privacyguard.ui.widgets import SinglePageCanvas
        canvas = SinglePageCanvas(page_index=2)
        canvas.zoom_scale = 1.0
        # 纯遮罩路径：关闭手动替换弹窗开关
        canvas.manual_replace_prompt = False
        return canvas

    def _release_event(self, pos):
        """构造一个左键释放的 QMouseEvent。"""
        return QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(pos),
            QPointF(pos),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

    def test_pure_mask_emits_rect_added(self):
        """纯遮罩框选释放后应 emit rect_added(page_index, real_rect)。"""
        canvas = self._make_canvas()
        received = []
        canvas.rect_added.connect(lambda idx, rect: received.append((idx, rect)))

        # 模拟一次有效框选：drawing=True + 合法 current_rect
        canvas.drawing = True
        canvas.start_point = QPointF(10, 10)
        canvas.current_rect = QRectF(10, 10, 40, 30)  # 宽高 > 5
        canvas.mouseReleaseEvent(self._release_event(QPointF(50, 40)))

        # 应收到一个信号，page_index=2，real_rect 按 zoom_scale=1.0 等比
        self.assertEqual(len(received), 1)
        idx, rect = received[0]
        self.assertEqual(idx, 2)
        self.assertAlmostEqual(rect.x(), 10)
        self.assertAlmostEqual(rect.y(), 10)
        self.assertAlmostEqual(rect.width(), 40)
        self.assertAlmostEqual(rect.height(), 30)
        # 同时应已 append 到 rects_manual
        self.assertEqual(len(canvas.rects_manual), 1)

    def test_prompt_mode_does_not_emit_rect_added(self):
        """开关开启时走 manual_region_prompt，不应 emit rect_added（保持原行为）。"""
        canvas = self._make_canvas()
        canvas.manual_replace_prompt = True  # 开关开启
        added = []
        prompted = []
        canvas.rect_added.connect(lambda idx, rect: added.append((idx, rect)))
        canvas.manual_region_prompt.connect(lambda rect: prompted.append(rect))

        canvas.drawing = True
        canvas.start_point = QPointF(0, 0)
        canvas.current_rect = QRectF(5, 5, 20, 20)
        canvas.mouseReleaseEvent(self._release_event(QPointF(25, 25)))

        self.assertEqual(len(added), 0)        # 不走 rect_added
        self.assertEqual(len(prompted), 1)     # 走 manual_region_prompt
        self.assertEqual(len(canvas.rects_manual), 0)  # 不直接 append


class TestImageMergeDocumentRelease(unittest.TestCase):
    """A5: ImageMergeWorker 在保存失败/取消时正确 close Document。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pg_im_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_images(self, n=2):
        """用 Pillow 生成 n 张最小 PNG。"""
        from PIL import Image
        paths = []
        for i in range(n):
            p = os.path.join(self.tmp, f"img_{i}.png")
            Image.new("RGB", (8, 8), (i * 30, 0, 0)).save(p)
            paths.append(p)
        return paths

    def test_save_failure_does_not_leak_document(self):
        """输出到不存在/不可写的路径，save 抛异常后 Document 应被 close。

        验证手段：异常后 worker 正常结束（不崩溃），且无残留异常；
        进一步用 fitz 验证目标文件未生成（确认走了失败路径）。
        """
        from privacyguard.workers.image_merge import ImageMergeWorker
        bad_output = os.path.join(self.tmp, "no_such_dir", "out.pdf")
        worker = ImageMergeWorker(self._make_images(2), bad_output)

        # 用 monkeypatch 计数 doc.close 调用，确认 finally 执行
        import fitz
        closes = []
        orig_close = fitz.Document.close
        try:
            def spy_close(self_doc):
                closes.append(True)
                return orig_close(self_doc)
            fitz.Document.close = spy_close

            worker.run()  # 同步执行（不 start 线程）
        finally:
            fitz.Document.close = orig_close

        # 走了失败路径：输出文件不存在
        self.assertFalse(os.path.exists(bad_output))
        # finally 中 doc.close 被调用（至少一次：创建后必 close）
        self.assertGreaterEqual(len(closes), 1)

    def test_success_emits_finished_and_closes(self):
        """正常合并：finished 信号 + Document 被 close。"""
        from privacyguard.workers.image_merge import ImageMergeWorker
        import fitz

        output = os.path.join(self.tmp, "ok.pdf")
        finished = []
        worker = ImageMergeWorker(self._make_images(3), output)
        worker.finished_signal.connect(lambda p: finished.append(p))

        closes = []
        orig_close = fitz.Document.close
        try:
            fitz.Document.close = lambda self_doc: (closes.append(True), orig_close(self_doc))[1]
            worker.run()
        finally:
            fitz.Document.close = orig_close

        self.assertEqual(len(finished), 1)
        self.assertEqual(finished[0], output)
        self.assertTrue(os.path.exists(output))
        self.assertGreaterEqual(len(closes), 1)


class TestTextLayerOffsetConsistency(unittest.TestCase):
    """A4: 文本层路径应用 off_x/off_w 的偏移公式应与图像路径一致。

    修复点在 ocr_worker.run() 文本循环内，此处验证所用的偏移公式语义：
        x' = x - off_x ; w' = max(2.0, w - off_w)
    与 calculate_sub_rect 图像路径（875-876 行）保持一致。
    默认 off_x=off_w=0 时不改变原坐标（向后兼容）。
    """

    def _apply_text_offset(self, x, w, off_x, off_w):
        """复刻 ocr_worker 文本路径的 off_x/off_w 应用逻辑（cp118）。"""
        if off_x or off_w:
            x = x - off_x
            w = max(2.0, w - off_w)
        return x, w

    def test_zero_offset_noop(self):
        """默认 off_x=off_w=0 时不改变坐标（向后兼容）。"""
        self.assertEqual(self._apply_text_offset(10, 20, 0, 0), (10, 20))

    def test_off_x_shifts_left(self):
        """off_x 正值使 x 左移（与图像路径 final_x = pdf_x - off_x 一致）。"""
        x, w = self._apply_text_offset(50, 20, 5, 0)
        self.assertAlmostEqual(x, 45)
        self.assertEqual(w, 20)  # off_w=0 宽度不变

    def test_off_w_shrinks_width_with_floor(self):
        """off_w 正值收缩宽度，且不低于 2.0pt 兜底（与图像路径 max(2.0, ...) 一致）。"""
        x, w = self._apply_text_offset(50, 20, 0, 8)
        self.assertEqual(x, 50)
        self.assertAlmostEqual(w, 12)
        # 宽度兜底：off_w 超过 (w - 2.0) 时回到 2.0
        x2, w2 = self._apply_text_offset(50, 5, 0, 100)
        self.assertEqual(w2, 2.0)

    def test_combined_offset(self):
        """off_x + off_w 同时作用。"""
        x, w = self._apply_text_offset(100, 40, 3, 10)
        self.assertAlmostEqual(x, 97)
        self.assertAlmostEqual(w, 30)


class TestOcrWideBoxFallback(unittest.TestCase):
    """A1: OCR box 超宽（> img 80%）时不再 return None 漏脱，而是回退纯权重估算。"""

    def _make_worker(self):
        from privacyguard.workers.ocr_worker import OCRWorker
        worker = OCRWorker.__new__(OCRWorker)
        worker.scan_scale = 2.0
        worker.off_x = 0.0
        worker.off_w = 0.0
        worker.box_adjust_ratio = 0.0
        return worker

    def test_wide_box_no_longer_returns_none(self):
        """A1 核心：box 宽度超过图像 80% 时 calculate_sub_rect 不应返回 None。

        修复前（cp54）：超宽 return None -> 调用处 continue 丢弃 -> 静默漏脱。
        修复后（cp118）：回退纯权重估算（effective_img_region=None），产出受限宽度的 rect。
        """
        import numpy as np
        worker = self._make_worker()
        # 图像宽 100px，box 宽 90px（>80%）触发回退
        img = np.full((40, 100, 3), 255, dtype=np.uint8)
        box = [[5, 5], [95, 5], [95, 35], [5, 35]]  # 宽 90 > 80
        text = "张三丰"
        rect = worker.calculate_sub_rect(box, text, (0, 1), img_region=img)
        # 关键断言：不再返回 None（不漏脱）
        self.assertIsNotNone(rect)
        # 且产出的是一个有限、宽度合理的 rect（不产生超大遮罩）
        self.assertGreater(rect.width(), 0)
        self.assertTrue(rect.width() < 100)  # 不会跨整图

    def test_normal_box_still_uses_pixel_path(self):
        """对照：正常宽度 box 仍走像素路径（行为不变）。"""
        import numpy as np
        worker = self._make_worker()
        # 图像宽 200px，box 宽 60px（<80%），不触发回退
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        box = [[70, 5], [130, 5], [130, 35], [70, 35]]
        text = "张三丰"
        rect = worker.calculate_sub_rect(box, text, (0, 1), img_region=img)
        self.assertIsNotNone(rect)
        self.assertGreater(rect.width(), 0)


class TestLookupReplacePriority(unittest.TestCase):
    """B3: _lookup_replace 子串匹配按 len(find_kw) 降序，长词优先。"""

    def _make_worker(self, mapping):
        """构造只装好 keyword_replace_map 的轻量 worker（跳过完整 __init__）。"""
        from privacyguard.workers.ocr_worker import OCRWorker
        worker = OCRWorker.__new__(OCRWorker)  # 不调用 __init__
        worker.keyword_replace_map = dict(mapping)
        return worker

    def test_exact_match_takes_priority(self):
        """精确匹配优先于子串匹配（原有行为不变）。"""
        w = self._make_worker({"张三": "ZS", "张三丰": "ZSF"})
        self.assertEqual(w._lookup_replace("张三丰"), "ZSF")  # 精确匹配

    def test_substring_long_keyword_wins(self):
        """B3: matched_text 含多关键词子串时，长词优先。

        场景：matched_text="张三丰的事"，dict 含 "张三"(短) 和 "张三丰"(长)。
        修复前按插入序，若 "张三" 在前会错误返回它的替换词。
        """
        # 故意把短词放前面，验证修复后仍命中长词
        w = self._make_worker({"张三": "ZS", "张三丰": "ZSF"})
        self.assertEqual(w._lookup_replace("张三丰的事"), "ZSF")

    def test_substring_only_short_available(self):
        """只有短词匹配时正常返回短词替换。"""
        w = self._make_worker({"张三": "ZS", "李四": "LS"})
        self.assertEqual(w._lookup_replace("张三的报告"), "ZS")

    def test_no_match_returns_empty(self):
        """无匹配返回空字符串（纯遮罩）。"""
        w = self._make_worker({"张三": "ZS"})
        self.assertEqual(w._lookup_replace("李四"), "")

    def test_empty_map_returns_empty(self):
        """空映射或空文本返回空。"""
        w = self._make_worker({})
        self.assertEqual(w._lookup_replace("任何"), "")
        w2 = self._make_worker({"张三": "ZS"})
        self.assertEqual(w2._lookup_replace(""), "")


@unittest.skipUnless(HAS_QT and HAS_MAIN, "PyQt6 或 main 模块不可用")
class TestManualReplacePromptGridSync(unittest.TestCase):
    """cp65 回归：网格画布 manual_replace_prompt 属性同步。

    修复的根因：页面视图下决定是否弹窗的唯一判断点在
    widgets.SinglePageCanvas.mouseReleaseEvent 的 getattr(self,
    "manual_replace_prompt", False)。但网格画布的该属性在 3 处未被同步：
      1) 画布创建时（_build_page_grid）
      2) 缓存 miss 分支（_refresh_visible_grid_thumbs）
      3) 设置保存后的 _sync_manual_replace_prompt_to_canvases
    导致用户反馈的两个现象：
      - 取消勾选不实时生效（设置保存后网格画布仍持旧值）
      - 页面视图勾选了但手动框选不弹窗（缓存 miss 画布属性恒为 False）
    """

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def _make_canvas(self):
        from privacyguard.ui.widgets import SinglePageCanvas
        c = SinglePageCanvas(page_index=0)
        # 模拟 _build_page_grid 的初始化环境：grid_mode + 信号连接前的属性
        return c

    def test_canvas_default_is_false(self):
        """未同步前画布默认值应为 False（这是 bug 的源头）。"""
        c = self._make_canvas()
        self.assertIs(c.manual_replace_prompt, False)

    def test_sync_method_covers_grid_canvases(self):
        """_sync_manual_replace_prompt_to_canvases 必须覆盖 _grid_canvases。

        用一个最小 fake 替身调用绑定的未绑定方法，避免实例化整个 MainWindow。
        """

        class FakeCanvas:
            def __init__(self):
                self.manual_replace_prompt = False
                self._valid = True

        left = FakeCanvas()
        right = FakeCanvas()
        g0, g1 = FakeCanvas(), FakeCanvas()

        class FakeMain:
            manual_replace_prompt = True  # 用户在设置里勾选了

            def _is_canvas_valid(self, c):
                return getattr(c, "_valid", False)

        fake = FakeMain()
        fake.canvas_left = left
        fake.canvas_right = right
        fake._grid_canvases = {0: g0, 1: g1}

        # 调用真实方法（用 fake 作为 self）
        MainWindow._sync_manual_replace_prompt_to_canvases(fake)

        # 单/双页画布应同步
        self.assertTrue(left.manual_replace_prompt)
        self.assertTrue(right.manual_replace_prompt)
        # 网格画布也必须同步（这是本次修复点）
        self.assertTrue(g0.manual_replace_prompt, "网格画布未被同步（bug 复现）")
        self.assertTrue(g1.manual_replace_prompt)

        # 切换关闭后再次同步应实时反映
        fake.manual_replace_prompt = False
        MainWindow._sync_manual_replace_prompt_to_canvases(fake)
        self.assertFalse(g0.manual_replace_prompt)
        self.assertFalse(g1.manual_replace_prompt)

    def test_no_grid_canvases_attr_does_not_crash(self):
        """_grid_canvases 属性不存在（非页面视图/旧实例）时不应崩溃。"""

        class FakeMain:
            manual_replace_prompt = True

            def _is_canvas_valid(self, c):
                return True

        fake = FakeMain()
        fake.canvas_left = None
        fake.canvas_right = None
        # 故意不设置 _grid_canvases
        MainWindow._sync_manual_replace_prompt_to_canvases(fake)  # 不抛异常即通过


if __name__ == "__main__":
    unittest.main()
