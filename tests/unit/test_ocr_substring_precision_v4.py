"""v37.7.9 cp37: PDF 遮罩精准度修复 v4 单元测试

验证 F16-F20 改动:
  - F16: B 档 _interp_pixel 用 segments[idx] 自身范围插值,不再跨 gap
  - F17: _segment_text_columns 入口先用 _detect_vertical_boundaries 收紧 y
  - F18: _detect_vertical_boundaries 跨多行 box 切单行
  - F19: RapidOCR 读取真实 confidence + 过滤低质量行
  - F20: _extract_roi_2x 辅助方法 + _calculate_from_line ROI 2x 放大

设计原则:
  - 用合成 BGR 图像构造可重现的字符块布局
  - 重点验证 F16 gap 修复(精确断言 delta=3pt)
  - 验证 F18 跨行 box 切单行
  - 验证 F20 ROI 放大坐标转换
  - 不依赖真实 OCR 引擎(直接调用内部方法)
"""

import unittest
from unittest.mock import patch

import numpy as np

# 软探测:fitz/PyQt6 未装时跳过整个测试模块
try:
    from privacyguard.workers.ocr_worker import OCRWorker  # noqa: F401
    _OCR_WORKER_OK = True
    _OCR_WORKER_ERR = ""
except Exception as exc:  # pragma: no cover - 环境依赖探测
    _OCR_WORKER_OK = False
    _OCR_WORKER_ERR = f"{type(exc).__name__}: {exc}"
    OCRWorker = None  # type: ignore

# RapidOCREngine 软探测
try:
    from privacyguard.ocr.rapidocr import RapidOCREngine
    from privacyguard.ocr.base import OCRResult
    _RAPIDOCR_OK = True
    _RAPIDOCR_ERR = ""
except Exception as exc:  # pragma: no cover
    _RAPIDOCR_OK = False
    _RAPIDOCR_ERR = f"{type(exc).__name__}: {exc}"
    RapidOCREngine = None  # type: ignore
    OCRResult = None  # type: ignore


def _make_worker(scan_scale=2.0, off_x=0.0, off_w=0.0, box_adjust_ratio=0.0):
    """绕过 QThread.__init__,只装配测试需要的属性。"""
    worker = OCRWorker.__new__(OCRWorker)
    worker.scan_scale = scan_scale
    worker.off_x = off_x
    worker.off_w = off_w
    worker.box_adjust_ratio = box_adjust_ratio
    return worker


def _make_line_image(width, height, char_blocks, gap, block_w, bg=255, fg=0):
    """构造合成 BGR 行图像:白色背景 + 黑色字符块(精确控制位置)。

    Returns:
        (img, expected_segments): BGR 图像 + 预期字符块 (left, right) 列表
    """
    img = np.full((height, width, 3), bg, dtype=np.uint8)
    expected = []
    pos = gap
    for i in range(char_blocks):
        x0 = pos
        x1 = x0 + block_w
        if x1 > width:
            break
        img[:, x0:x1, :] = fg
        expected.append((x0, x1 - 1))
        pos = x1 + gap
    return img, expected


def _make_two_row_image(width, row_h=20, gap_between_rows=20, char_blocks_per_row=3,
                         block_w=30, gap_between_chars=10, bg=255, fg=0):
    """构造 2 行文字的合成图像,用于测试跨行 box 切单行。

    Returns:
        (img, row0_segs, row1_segs): 图像 + 行 0 段 + 行 1 段
    """
    height = row_h * 2 + gap_between_rows
    img = np.full((height, width, 3), bg, dtype=np.uint8)
    row0_segs = []
    row1_segs = []
    pos = gap_between_chars
    for i in range(char_blocks_per_row):
        x0 = pos
        x1 = x0 + block_w
        if x1 > width:
            break
        # 行 0: y=0 到 row_h
        img[0:row_h, x0:x1, :] = fg
        row0_segs.append((x0, x1 - 1))
        # 行 1: y=row_h+gap 到 row_h*2+gap
        img[row_h + gap_between_rows:row_h * 2 + gap_between_rows, x0:x1, :] = fg
        row1_segs.append((x0, x1 - 1))
        pos = x1 + gap_between_chars
    return img, row0_segs, row1_segs


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker({_OCR_WORKER_ERR}),跳过 v4 测试")
class TestF16GapSkippingFix(unittest.TestCase):
    """F16: B 档 _interp_pixel 不再跨 gap 插值。"""

    def test_b_tier_sub_x_falls_within_target_segment_not_cross_gap(self):
        """3 段 + 4 字符 → B 档。match_span=(2,4) 取后 2 字符。

        构造:3 个 30px 宽字符块,间隙 30px。
        segments = [(30,59), (90,119), (150,179)](像素空间)
        text="ABCD",match_span=(2,4) 取 CD
        char_cum_ratio = [0, 0.25, 0.5, 0.75, 1.0]
        seg_cum_ratio = [0, 0.333, 0.667, 1.0]
        target_start_ratio=0.5,落在段 1 内。
        新代码:插值范围 = segments[1] = [90, 119]
        原代码(bug):插值范围 = [r0=59, r1=119],跨 gap
        """
        img, expected = _make_line_image(width=300, height=40,
                                           char_blocks=3, gap=30, block_w=30)
        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [300, 0], [300, 40], [0, 40]]
        text = "ABCD"  # 4 字符,3 段 → B 档
        rect = worker._calculate_from_line(box, text, 2, 4, img_region=img)

        self.assertIsNotNone(rect, "B 档应返回非 None rect")
        # 段 1 PDF 范围:[45, 59.5]
        seg1_left_pdf = expected[1][0] / 2.0  # 45.0
        seg1_right_pdf = (expected[1][1] + 1) / 2.0  # 30 (block_w) → 60,但 expected 用 x1-1=59 → 29.5
        # expected[1] = (90, 119),left_pdf = 45, right_pdf = 60
        # sub_x 应在段 1 范围 [45, 60] 内,不跨 gap 到段 0 r0=29.5
        self.assertGreaterEqual(rect.x(), seg1_left_pdf - 3,
                                 msg=f"F16 sub_x={rect.x()} 应 ≥ 段 1 起点 {seg1_left_pdf - 3}(不跨 gap)")
        self.assertLessEqual(rect.x(), seg1_right_pdf + 3,
                              msg=f"F16 sub_x={rect.x()} 应 ≤ 段 1 终点 {seg1_right_pdf + 3}")

    def test_b_tier_sub_x_not_pulled_to_previous_segment_right(self):
        """验证 B 档 sub_x 不会被拉到上一段右边界(原 bug 行为)。

        构造:2 段 + 3 字符。match_span=(1,3) 取后 2 字符。
        segments = [(20,49), (70,99)],gap=20px
        text="ABC",match_span=(1,3)
        char_cum_ratio = [0, 0.333, 0.667, 1.0]
        seg_cum_ratio = [0, 0.5, 1.0]
        target_start_ratio=0.333,落在段 0 内(t=0.667)。
        新代码:插值 = 20 + 0.667*29 = 39.3 (段 0 内)
        原代码(bug):插值 = 20 + 0.667*29 = 39.3 (段 0 内,因为 idx=0)
        本测试验证 idx=1 时不被拉到段 0 r0。
        用 match_span=(2,3) 取最后 1 字符:
        target_start_ratio=0.667,落在段 1 内(t=0.334)。
        新代码:插值 = 70 + 0.334*29 = 79.7 (段 1 内)
        原代码(bug):插值 = 49 + 0.334*50 = 65.7 (跨 gap,接近段 0 r0=49)
        """
        img, expected = _make_line_image(width=200, height=40,
                                           char_blocks=2, gap=20, block_w=30)
        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"  # 3 字符,2 段 → B 档
        rect = worker._calculate_from_line(box, text, 2, 3, img_region=img)

        self.assertIsNotNone(rect)
        # 段 1 PDF 范围:[35, 50]
        seg1_left_pdf = expected[1][0] / 2.0  # 35.0
        # sub_x 应在段 1 内,不被拉到段 0 r0=24.5 附近
        self.assertGreaterEqual(rect.x(), seg1_left_pdf - 3,
                                 msg=f"F16 sub_x={rect.x()} 应在段 1 内,不应被拉到段 0 r0")
        self.assertLessEqual(rect.x(), 50.0,
                              msg=f"F16 sub_x={rect.x()} 不应超出段 1 右边界")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker({_OCR_WORKER_ERR}),跳过 v4 测试")
class TestF17F18VerticalTightening(unittest.TestCase):
    """F17 + F18: _segment_text_columns 用 _detect_vertical_boundaries 收紧 y,跨行 box 切单行。"""

    def test_detect_vertical_boundaries_returns_single_row_for_cross_row_box(self):
        """跨 2 行 box → _detect_vertical_boundaries 返回单行范围。

        构造 200x60 图像:行 0(y=0-20)+ 间隙(y=20-40)+ 行 1(y=40-60)
        OCR box 跨 2 行(y=0-60)
        F18 修复:返回最接近 box 中心的单行(行 0 或行 1)
        """
        img, row0_segs, row1_segs = _make_two_row_image(
            width=200, row_h=20, gap_between_rows=20, char_blocks_per_row=3,
            block_w=30, gap_between_chars=10)
        worker = _make_worker()
        # 跨 2 行 box
        box = [[0, 0], [200, 0], [200, 60], [0, 60]]

        top, bottom = worker._detect_vertical_boundaries(img, box)

        # F18:应返回单行范围(行 0:[0,20] 或 行 1:[40,60]),不跨 2 行
        in_row0 = top <= 5 and bottom >= 15 and bottom <= 25
        in_row1 = top >= 35 and top <= 45 and bottom >= 55
        self.assertTrue(in_row0 or in_row1,
                         msg=f"F18 跨行 box 应返回单行范围,top={top} bottom={bottom}")

    def test_segment_text_columns_uses_tightened_y_for_cross_row_box(self):
        """跨行 box → _segment_text_columns 收紧 y 后段切分正确。

        没有 F17 时:跨行 box 的 col_sum 会叠加 2 行,间隙被填充,段无法切断。
        有 F17:先用 _detect_vertical_boundaries 收紧到单行,再做段切分。
        """
        img, row0_segs, row1_segs = _make_two_row_image(
            width=200, row_h=20, gap_between_rows=20, char_blocks_per_row=3,
            block_w=30, gap_between_chars=10)
        worker = _make_worker()
        # 跨 2 行 box
        box = [[0, 0], [200, 0], [200, 60], [0, 60]]

        segments = worker._segment_text_columns(img, box)

        # 收紧后应能切出 3 段(单行的 3 个字符块)
        self.assertGreaterEqual(len(segments), 2,
                                 msg=f"F17 跨行 box 收紧 y 后应切出 ≥2 段,实际 {len(segments)}: {segments}")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker({_OCR_WORKER_ERR}),跳过 v4 测试")
class TestF19RapidOCRConfidence(unittest.TestCase):
    """F19: RapidOCR 读取真实 confidence。"""

    @unittest.skipUnless(_RAPIDOCR_OK, f"无法导入 RapidOCREngine({_RAPIDOCR_ERR})")
    def test_rapidocr_reads_real_confidence_from_line_index_2(self):
        """RapidOCR line = (box, text, confidence),F19 读取 line[2] 而非硬编码 0.9。"""
        engine = RapidOCREngine.__new__(RapidOCREngine)
        engine._engine = None  # 跳过真实引擎初始化
        # cp58: __new__ 绕过 __init__,需手动设置 _init_failed 标志
        engine._init_failed = False

        # 模拟 RapidOCR 返回:(box, text, confidence)
        fake_box = [[0, 0], [100, 0], [100, 20], [0, 20]]
        fake_result = [
            (fake_box, "王小明", 0.85),
            (fake_box, "孙志华", 0.72),
        ]

        with patch.object(engine, '_engine') as mock_engine:
            mock_engine.return_value = (fake_result, None)
            results = engine.recognize(np.zeros((20, 100, 3), dtype=np.uint8))

        self.assertEqual(len(results), 2)
        self.assertAlmostEqual(results[0].confidence, 0.85, places=2,
                                 msg=f"F19 confidence 应为 0.85,实际 {results[0].confidence}")
        self.assertAlmostEqual(results[1].confidence, 0.72, places=2,
                                 msg=f"F19 confidence 应为 0.72,实际 {results[1].confidence}")

    @unittest.skipUnless(_RAPIDOCR_OK, f"无法导入 RapidOCREngine({_RAPIDOCR_ERR})")
    def test_rapidocr_falls_back_to_09_when_confidence_missing(self):
        """line 长度 < 3 或 line[2] 为 None 时,回退到默认 0.9。"""
        engine = RapidOCREngine.__new__(RapidOCREngine)
        engine._engine = None
        # cp58: __new__ 绕过 __init__,需手动设置 _init_failed 标志
        engine._init_failed = False

        fake_box = [[0, 0], [100, 0], [100, 20], [0, 20]]
        # 故意只返回 (box, text),无 confidence
        fake_result = [
            (fake_box, "测试"),
            (fake_box, "无置信度", None),
        ]

        with patch.object(engine, '_engine') as mock_engine:
            mock_engine.return_value = (fake_result, None)
            results = engine.recognize(np.zeros((20, 100, 3), dtype=np.uint8))

        self.assertEqual(len(results), 2)
        self.assertAlmostEqual(results[0].confidence, 0.9, places=2,
                                 msg="无 confidence 时应回退到 0.9")
        self.assertAlmostEqual(results[1].confidence, 0.9, places=2,
                                 msg="confidence=None 时应回退到 0.9")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker({_OCR_WORKER_ERR}),跳过 v4 测试")
class TestF20ROI2xUpscaling(unittest.TestCase):
    """F20: ROI 内部 2x 放大提升像素精度。"""

    def test_extract_roi_2x_returns_doubled_image_and_offset(self):
        """_extract_roi_2x 返回外扩后的 ROI + 偏移量。

        v37.7.9 cp38 F20-redesign: 放弃 2x 放大,scale 固定 1.0
        v37.7.9 cp38 F23: ROI 边界外扩 8px,offset 和 shape 相应变化
        """
        # 100x40 图像,box 在 (10,5)-(90,35) 范围
        img = np.zeros((40, 100, 3), dtype=np.uint8)
        box = [[10, 5], [90, 5], [90, 35], [10, 35]]
        worker = _make_worker()

        roi_2x, scale, offset_x, offset_y = worker._extract_roi_2x(img, box)

        self.assertIsNotNone(roi_2x, "ROI 不应为 None")
        # F20-redesign: scale 固定 1.0(不放大)
        self.assertEqual(scale, 1.0, msg=f"F20-redesign scale 应为 1.0,实际 {scale}")
        # F23: 外扩 8px,offset_x = max(0, 10-8) = 2
        self.assertEqual(offset_x, 2, msg=f"F23 外扩后 offset_x 应为 2,实际 {offset_x}")
        # F23: 外扩 8px,offset_y = max(0, 5-8) = 0
        self.assertEqual(offset_y, 0, msg=f"F23 外扩后 offset_y 应为 0,实际 {offset_y}")
        # F23: ROI 原尺寸 (90+8 - max(0,10-8)) x (35+8 - max(0,5-8)) = 96 x 40,不放大
        self.assertEqual(roi_2x.shape, (40, 96, 3),
                          msg=f"F23 外扩后 ROI 形状应为 (40, 96, 3),实际 {roi_2x.shape}")

    def test_extract_roi_2x_returns_none_for_invalid_box(self):
        """box 越界或面积为 0 时返回 None。

        v37.7.9 cp38 F23: 外扩 8px 后,零宽 box 会被扩展为 16px 宽 ROI,
        不再返回 None。改为测试完全越界场景。
        """
        img = np.zeros((40, 100, 3), dtype=np.uint8)
        worker = _make_worker()

        # box 完全在图像右侧之外(x_min=200 > img_width=100)
        box_oob = [[200, 0], [250, 0], [250, 40], [200, 40]]
        roi, scale, ox, oy = worker._extract_roi_2x(img, box_oob)
        self.assertIsNone(roi, "完全越界 box 应返回 None")

    def test_calculate_from_line_still_works_with_small_image(self):
        """F20 ROI 2x 放大后,_calculate_from_line 仍能正确返回 sub_rect。"""
        # 构造小尺寸图像(scan_scale=1.5 模拟默认场景)
        img, expected = _make_line_image(width=120, height=24,
                                           char_blocks=3, gap=8, block_w=20)
        worker = _make_worker(scan_scale=1.5)
        box = [[0, 0], [120, 0], [120, 24], [0, 24]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 1, 3, img_region=img)

        self.assertIsNotNone(rect, "ROI 2x 放大后应返回非 None rect")
        # 期望 sub_rect 覆盖 expected[1] 到 expected[2]
        expected_left_pdf = expected[1][0] / 1.5
        self.assertAlmostEqual(rect.x(), expected_left_pdf, delta=5,
                                msg=f"F20 sub_x={rect.x()} 期望接近 {expected_left_pdf}")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker({_OCR_WORKER_ERR}),跳过 v4 测试")
class TestRealWorldBimodalFixed(unittest.TestCase):
    """真实场景:模拟"王小明""孙志华"在跨行/低置信度场景下的精准遮罩。"""

    def test_liu_shaofang_in_single_row_precise_redaction(self):
        """模拟 "原告王小明,男,汉族" 10 字符行,match_span=(2,5) 取"王小明"。

        v37.7.9 cp38: 修正测试 - text 实际 10 字符(含 2 个英文逗号),
        char_blocks 与 text 长度匹配,段数 == 字符数走 A 档直接取段最精准。
        scan_scale=1.5(用户默认配置),F20 ROI 2x 放大 + F23 外扩 8px。
        """
        img, expected = _make_line_image(width=450, height=40,
                                           char_blocks=10, gap=10, block_w=30)
        worker = _make_worker(scan_scale=1.5)
        box = [[0, 0], [450, 0], [450, 40], [0, 40]]
        text = "原告王小明,男,汉族"  # 10 字符
        rect = worker._calculate_from_line(box, text, 2, 5, img_region=img)

        self.assertIsNotNone(rect)
        # 期望 sub_rect 覆盖 expected[2] (刘) 到 expected[4] (芳)
        expected_left_pdf = expected[2][0] / 1.5
        expected_right_pdf = (expected[4][1] + 1) / 1.5
        self.assertAlmostEqual(rect.x(), expected_left_pdf, delta=3,
                                msg=f"王小明 sub_x={rect.x()} 期望 {expected_left_pdf}")
        self.assertAlmostEqual(rect.x() + rect.width(), expected_right_pdf, delta=3,
                                msg=f"王小明 right={rect.x() + rect.width()} 期望 {expected_right_pdf}")

    def test_sun_zhihua_with_normal_scan_scale(self):
        """模拟 "被告孙志华,女" 7 字符行,match_span=(2,5) 取"孙志华"。

        scan_scale=1.5,F20 ROI 2x 放大后精度提升。
        """
        img, expected = _make_line_image(width=350, height=40,
                                           char_blocks=7, gap=10, block_w=30)
        worker = _make_worker(scan_scale=1.5)
        box = [[0, 0], [350, 0], [350, 40], [0, 40]]
        text = "被告孙志华,女"  # 7 字符
        rect = worker._calculate_from_line(box, text, 2, 5, img_region=img)

        self.assertIsNotNone(rect)
        expected_left_pdf = expected[2][0] / 1.5  # 50/1.5 = 33.3
        expected_right_pdf = (expected[4][1] + 1) / 1.5
        self.assertAlmostEqual(rect.x(), expected_left_pdf, delta=3,
                                msg=f"孙志华 sub_x={rect.x()} 期望 {expected_left_pdf}")
        self.assertAlmostEqual(rect.x() + rect.width(), expected_right_pdf, delta=3,
                                msg=f"孙志华 right={rect.x() + rect.width()} 期望 {expected_right_pdf}")


if __name__ == "__main__":
    unittest.main()
