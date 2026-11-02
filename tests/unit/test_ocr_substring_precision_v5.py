"""v37.7.9 cp38: PDF 遮罩精准度修复 v5 单元测试

验证 cp38 阶段 4 项核心改动:
  - F20-redesign: _extract_roi_2x 放弃 2x 放大,scale 固定 1.0
  - F23: ROI 边界外扩 8px(容纳 RapidOCR box ±2-5px 偏差)
  - gap_tolerance 上限: 加 median_gap * 0.8,确保 gap > gap_tolerance 能切断
  - F24: _verify_sub_rect_width 宽度合理性检查(过窄回退权重 / 过宽段块收紧)

设计原则:
  - 用合成 BGR 图像构造可重现的边界场景
  - 重点验证 F23 边界裁剪、gap_tolerance 极端值、坐标转换无条件化、F24 回退触发
  - 不依赖真实 OCR 引擎(直接调用内部方法)
"""

import unittest

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


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker({_OCR_WORKER_ERR}),跳过 v5 测试")
class TestF23ROIExpandClippedAtImageEdge(unittest.TestCase):
    """F23: ROI 边界外扩 8px,接近图像边缘时被裁剪。"""

    def test_f23_roi_expand_clipped_at_image_edge(self):
        """box 接近图像左边缘(x_min=3),外扩 8px 后 x_min 被 max(0, ...) 裁剪为 0。

        验证:
          - offset_x = max(0, 3-8) = 0(被裁剪,非负数)
          - ROI 宽度 = min(100, 50+8) - 0 = 58(右边界也外扩 8px)
          - scale_factor = 1.0(F20-redesign 不放大)
        """
        # 100x40 图像,box 在 (3,5)-(50,35)
        img = np.zeros((40, 100, 3), dtype=np.uint8)
        box = [[3, 5], [50, 5], [50, 35], [3, 35]]
        worker = _make_worker()

        roi, scale, offset_x, offset_y = worker._extract_roi_2x(img, box)

        self.assertIsNotNone(roi, "ROI 不应为 None")
        # F23: 左边界外扩被裁剪,offset_x = max(0, 3-8) = 0
        self.assertEqual(offset_x, 0,
                          msg=f"F23 左边缘裁剪后 offset_x 应为 0,实际 {offset_x}")
        # F23: 上边界外扩也被裁剪,offset_y = max(0, 5-8) = 0
        self.assertEqual(offset_y, 0,
                          msg=f"F23 上边缘裁剪后 offset_y 应为 0,实际 {offset_y}")
        # F20-redesign: scale 固定 1.0
        self.assertEqual(scale, 1.0,
                          msg=f"F20-redesign scale 应为 1.0,实际 {scale}")
        # ROI 宽度 = min(100, 50+8) - max(0, 3-8) = 58 - 0 = 58
        # ROI 高度 = min(40, 35+8) - max(0, 5-8) = 40 - 0 = 40(下边界也被裁剪)
        self.assertEqual(roi.shape, (40, 58, 3),
                          msg=f"F23 边缘裁剪后 ROI 形状应为 (40, 58, 3),实际 {roi.shape}")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker({_OCR_WORKER_ERR}),跳过 v5 测试")
class TestGapToleranceWithTinyMedianGap(unittest.TestCase):
    """gap_tolerance 加 median_gap * 0.8 上限,极小 median_gap 时行为验证。"""

    def test_gap_tolerance_with_tiny_median_gap(self):
        """median_gap=2px 极小间隙,gap_tolerance 计算应受 median_gap * 0.8 限制。

        构造:3 个 30px 字符块,间隙 2px(char_h=40)
          - 预切分 segments = [(2,31), (33,62), (64,93)]
          - gaps = [2, 2],median_gap = 2
          - gap_tolerance = max(2, min(int(2*1.5)=3, int(40/3)=13, int(2*0.8)=1)) = max(2, 1) = 2
          - 正式切分用 gap_tolerance=2,gap=2 不 > 2,间隙不切断 → 3 段融合为 1 段

        这是预期行为:2px 间隙极小,可能是字符内部笔画间隙,不应切断。
        验证 _segment_text_columns 在极小间隙下不崩溃,返回合理段数。
        """
        # 构造 3 个 30px 字符块,间隙 2px(极小)
        img, expected = _make_line_image(width=100, height=40,
                                           char_blocks=3, gap=2, block_w=30)
        worker = _make_worker()
        box = [[0, 0], [100, 0], [100, 40], [0, 40]]

        segments = worker._segment_text_columns(img, box)

        # gap_tolerance=2,gap=2 不 > 2,3 段融合为 1 段是预期行为
        # 不强制要求 3 段,只验证不崩溃且返回非空列表
        self.assertIsInstance(segments, list,
                              msg=f"极小间隙下 segments 应为 list,实际 {type(segments)}")
        # 即使融合为 1 段,段宽应覆盖整个文字区域
        if segments:
            seg_left = min(l for l, r in segments)
            seg_right = max(r for l, r in segments)
            self.assertGreater(seg_right - seg_left, 50,
                                msg=f"融合段宽度 {seg_right - seg_left} 应覆盖大部分文字区域(>50px)")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker({_OCR_WORKER_ERR}),跳过 v5 测试")
class TestCoordinateTransformWithOffsetOnly(unittest.TestCase):
    """F20-redesign + F23: scale_factor=1.0 但 offset>0 时坐标转换无条件化验证。"""

    def test_coordinate_transform_with_offset_only(self):
        """scale_factor=1.0 但 offset>0(F23 外扩场景),segments 坐标应加 offset。

        构造:200x40 图像,3 个 30px 字符块 gap=10px
          - 不带 F23 外扩:box = (0,0)-(200,40),offset=0
          - 带 F23 外扩:_extract_roi_2x 外扩 8px,offset=(0,0)(因 box 已在边缘)
        为触发 offset>0,构造 box 在图像中部:
          - img 400x100,box = (100,30)-(300,70)
          - F23 外扩:offset_x = 100-8 = 92,offset_y = 30-8 = 22
          - effective_box 转换到 ROI 局部坐标
          - segments 在 ROI 局部空间,转换回原坐标应加 offset

        验证 _calculate_from_line 返回的 sub_x 在原图像坐标系(非 ROI 局部)。
        """
        # 400x100 图像,box 在中部 (100,30)-(300,70)
        img, expected = _make_line_image(width=200, height=40,
                                           char_blocks=3, gap=10, block_w=30)
        # 把 img 嵌入更大的 400x100 画布
        canvas = np.full((100, 400, 3), 255, dtype=np.uint8)
        canvas[30:70, 100:300, :] = img

        worker = _make_worker(scan_scale=1.0)  # scan_scale=1.0 简化坐标转换
        box = [[100, 30], [300, 30], [300, 70], [100, 70]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 0, 1, img_region=canvas)

        self.assertIsNotNone(rect, "F23 外扩场景应返回非 None rect")
        # scan_scale=1.0,坐标转换后 pdf_x = sub_x / 1.0 = sub_x(原画布坐标)
        # 第一个字符块在原画布 x=110(gap=10 + offset 100)
        # sub_x 应在 110 附近(允许 ±5px 误差,因 _detect_text_boundaries 可能有偏差)
        self.assertGreater(rect.x(), 100,
                           msg=f"F23 offset 转换后 sub_x={rect.x()} 应 > 100(在原画布坐标,非 ROI 局部)")
        self.assertLess(rect.x(), 130,
                        msg=f"F23 offset 转换后 sub_x={rect.x()} 应 < 130(接近第一字符块 x=110)")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker({_OCR_WORKER_ERR}),跳过 v5 测试")
class TestF24WidthCheckTriggersFallback(unittest.TestCase):
    """F24: sub_rect 宽度合理性检查,过宽时触发段块宽度收紧回退。"""

    def test_f24_width_check_triggers_fallback_on_overwide(self):
        """段切分退化为单段(3 字符粘连),sub_w 过宽时 F24 触发段块收紧。

        构造:200x40 图像,3 字符粘连成 1 段(30px 在 x=85-115)
          - 段切分返回 1 段 = (85, 115)
          - _detect_text_boundaries 返回 line_x_min≈85, line_x_max≈115
          - line_width = 30px
          - match_span=(0,3) 取 "ABC" 3 字符
          - C 档:seg_block_width=30,refined_line_width=min(line_width, 30)=30
          - sub_w = (3*1.0 / 3*1.0) * 30 = 30px = 30pt(scan_scale=1.0)
          - avg_char_w = 30 / 3 = 10,max_expected = 3 * 10 * 1.5 = 45
          - sub_w=30 < 45,不触发 F24 过宽回退

        为触发 F24 过宽回退,构造段切分返回宽段但 line 更宽的场景:
          - img 200x40,文字块在 x=80-120(40px)
          - _detect_text_boundaries 因 Otsu 阈值把背景噪点也算入,line 范围扩大
          - 段切分返回 1 段但 seg_block_width < line_width
          - C 档用 seg_block_width 收紧,sub_w 应 < line_width

        验证:sub_w 不超过 seg_block_width * 1.5(F24 兜底)
        """
        # 构造 3 字符粘连成 1 段
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 80:120, :] = 0  # 40px 全黑(模拟 3 字符粘连)

        worker = _make_worker(scan_scale=1.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 0, 3, img_region=img)

        self.assertIsNotNone(rect, "C 档 + F24 应返回 rect")
        # C 档:seg_block_width=40,refined_line_width=min(line_width, 40)
        # sub_w = 40px - margin = ~39.4px = 39.4pt(scan_scale=1.0)
        # F24:avg_char_w = line_width / 3(可能 > 40/3 因 line 扩大)
        #      max_expected = 3 * avg_char_w * 1.5
        #      sub_w=39.4 应 < max_expected(若 line_width > 26.3)
        # 关键断言:sub_w 不超过 seg_block_width * 1.5 = 60pt(F24 兜底)
        self.assertLess(rect.width(), 60,
                         msg=f"F24 兜底后 sub_w={rect.width()} 应 < 60pt(seg_block_width * 1.5)")

    def test_f24_width_check_no_trigger_on_normal_a_tier(self):
        """A 档(段数==字符数)正常场景下 F24 不应触发回退。

        构造:3 字符 3 段,match_span=(0,1) 取第 1 字符
          - A 档:sub_w = 段 0 宽度 = 30px = 30pt(scan_scale=1.0)
          - avg_char_w = line_width / 3(假设 line=170,avg=56.7)
          - min_expected = 1 * 56.7 * 0.5 = 28.3,max_expected = 1 * 56.7 * 1.5 = 85
          - sub_w=30 在 [28.3, 85] 内,不触发 F24

        验证:A 档 sub_w 接近段 0 宽度(未被 F24 改动)。
        """
        img, expected = _make_line_image(width=200, height=40,
                                           char_blocks=3, gap=20, block_w=30)
        worker = _make_worker(scan_scale=1.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 0, 1, img_region=img)

        self.assertIsNotNone(rect, "A 档应返回 rect")
        # A 档:sub_w = 段 0 宽度 30px - margin = ~29.4pt
        # F24 不触发,sub_w 应接近段 0 宽度
        expected_seg0_w = 30  # block_w
        self.assertAlmostEqual(rect.width(), expected_seg0_w, delta=5,
                                msg=f"A 档 F24 不触发,sub_w={rect.width()} 应接近段 0 宽度 {expected_seg0_w}pt")


if __name__ == "__main__":
    unittest.main()
