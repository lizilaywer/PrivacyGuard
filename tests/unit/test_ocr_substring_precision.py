"""v37.7.8 cp34: OCR 子字符串遮罩精准度单元测试

验证 _segment_text_columns / _detect_vertical_boundaries / _calculate_from_line
三组改动的核心契约：

1. 像素级字符切分能正确数出合成图像里的字符块数与位置
2. _calculate_from_line 在切分匹配时按 match_span 取字符块
3. _calculate_from_line 在切分失败时退化为权重估算
4. sub_rect 永远不超出整行边界
5. margin 在不同 scan_scale 下行为可重复（PDF 点空间一致）
"""

import unittest

import numpy as np

# fitz (PyMuPDF) 是 OCRWorker 的运行时依赖；CI/纯单元环境可能未装。
# 这里做软探测：未装时跳过整个测试模块，而不是 ERROR。
try:
    from privacyguard.workers.ocr_worker import OCRWorker  # noqa: F401
    _OCR_WORKER_OK = True
    _OCR_WORKER_ERR = ""
except Exception as exc:  # pragma: no cover - 环境依赖探测
    _OCR_WORKER_OK = False
    _OCR_WORKER_ERR = f"{type(exc).__name__}: {exc}"
    OCRWorker = None  # type: ignore


def _make_worker(scan_scale=2.0, off_x=0.0, off_w=0.0, box_adjust_ratio=0.0):
    """绕过 QThread.__init__（不需要 QApplication），只装配测试需要的属性。"""
    worker = OCRWorker.__new__(OCRWorker)
    worker.scan_scale = scan_scale
    worker.off_x = off_x
    worker.off_w = off_w
    worker.box_adjust_ratio = box_adjust_ratio
    return worker


def _make_line_image(width, height, char_blocks, gap=20, block_w=30, bg=255, fg=0):
    """构造合成 BGR 行图像：白色背景 + 黑色字符块。

    Args:
        width: 图像宽
        height: 图像高
        char_blocks: 字符块数量
        gap: 块之间的间隙（含块宽，块间距 = gap - block_w）
        block_w: 每个块的宽度
        bg: 背景值
        fg: 前景值

    Returns:
        (img, expected_segments): BGR 图像 + 预期字符块 (left, right) 列表
    """
    img = np.full((height, width, 3), bg, dtype=np.uint8)
    expected = []
    # 从 gap 开始放，每个块 block_w 宽，块间距 gap
    for i in range(char_blocks):
        x0 = gap + i * (block_w + gap)
        x1 = x0 + block_w
        if x1 > width:
            break
        img[:, x0:x1, :] = fg
        expected.append((x0, x1 - 1))  # 像素投影通常右端取 -1（最后一列黑色像素）
    return img, expected


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过子字符串精准度测试")
class TestSegmentTextColumns(unittest.TestCase):
    """R1 修复：像素级字符切分。"""

    def test_three_distinct_blocks_returns_three_segments(self):
        img, expected = _make_line_image(width=200, height=40, char_blocks=3)
        worker = _make_worker()

        # box 覆盖整张图
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        segments = worker._segment_text_columns(img, box)

        self.assertEqual(len(segments), 3, f"期望 3 段，实际 {len(segments)}: {segments}")
        # 每段 left/right 应该接近 expected
        for got, exp in zip(segments, expected):
            self.assertAlmostEqual(got[0], exp[0], delta=3,
                                    msg=f"左边界偏差过大: got={got[0]} exp={exp[0]}")
            self.assertAlmostEqual(got[1], exp[1], delta=3,
                                    msg=f"右边界偏差过大: got={got[1]} exp={exp[1]}")

    def test_empty_image_returns_empty_list(self):
        img = np.full((40, 200, 3), 255, dtype=np.uint8)  # 全白
        worker = _make_worker()

        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        segments = worker._segment_text_columns(img, box)

        self.assertEqual(segments, [])

    def test_invalid_box_returns_empty(self):
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        worker = _make_worker()

        # x_min == x_max
        box = [[100, 0], [100, 0], [100, 40], [100, 40]]
        segments = worker._segment_text_columns(img, box)

        self.assertEqual(segments, [])


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过子字符串精准度测试")
class TestDetectVerticalBoundaries(unittest.TestCase):
    """R2 修复：y 方向边界检测。"""

    def test_tight_y_bounds_when_text_only_in_middle(self):
        # 200x100 图像，文字只在 y=40~60 之间
        img = np.full((100, 200, 3), 255, dtype=np.uint8)
        img[40:60, 50:150, :] = 0
        worker = _make_worker()

        box = [[0, 0], [200, 0], [200, 100], [0, 100]]
        top, bottom = worker._detect_vertical_boundaries(img, box)

        # 实际文字在 40-59（OTSU 后可能略偏，但应该接近）
        self.assertGreaterEqual(top, 35, f"top={top} 期望接近 40")
        self.assertLessEqual(top, 45, f"top={top} 期望接近 40")
        self.assertGreaterEqual(bottom, 55, f"bottom={bottom} 期望接近 60")
        self.assertLessEqual(bottom, 65, f"bottom={bottom} 期望接近 60")

    def test_empty_image_falls_back_to_box_y(self):
        img = np.full((100, 200, 3), 255, dtype=np.uint8)
        worker = _make_worker()

        box = [[0, 10], [200, 10], [200, 90], [0, 90]]
        top, bottom = worker._detect_vertical_boundaries(img, box)

        # 无文字 → 退回 box 范围
        self.assertEqual(top, 10)
        self.assertEqual(bottom, 90)


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过子字符串精准度测试")
class TestCalculateFromLineSegmentation(unittest.TestCase):
    """R1 修复：_calculate_from_line 在切分匹配时按 match_span 取字符块。"""

    def test_match_span_returns_subrect_close_to_expected_block(self):
        img, expected = _make_line_image(width=200, height=40, char_blocks=3)
        worker = _make_worker(scan_scale=2.0)

        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"  # 3 字符，匹配 3 段
        # match_span=(1,3) → 取第 1、2 段
        rect = worker._calculate_from_line(box, text, 1, 3, img_region=img)

        self.assertIsNotNone(rect, "rect 不应为 None")
        # 期望 sub_rect 大致覆盖 expected[1] 左边到 expected[2] 右边
        # 在 PDF 点空间（/ scan_scale=2.0）
        expected_left_pdf = expected[1][0] / 2.0
        expected_right_pdf = expected[2][1] / 2.0
        # 允许 5pt 偏差（含 margin 调整、投影边缘误差）
        self.assertAlmostEqual(rect.x(), expected_left_pdf, delta=5,
                                msg=f"x={rect.x()} 期望 {expected_left_pdf}")
        self.assertAlmostEqual(rect.x() + rect.width(), expected_right_pdf, delta=5,
                                msg=f"right={rect.x() + rect.width()} 期望 {expected_right_pdf}")

    def test_subrect_never_exceeds_line_bounds(self):
        """边界保护：sub_rect 不能超出整行边界。"""
        img, _ = _make_line_image(width=200, height=40, char_blocks=3)
        worker = _make_worker(scan_scale=2.0)

        box = [[10, 0], [190, 0], [190, 40], [10, 40]]
        text = "ABC"
        # 试图取整行
        rect = worker._calculate_from_line(box, text, 0, 3, img_region=img)

        self.assertIsNotNone(rect)
        # PDF 坐标系下的整行边界
        line_x_min_pdf = 10 / 2.0
        line_x_max_pdf = 190 / 2.0
        self.assertGreaterEqual(rect.x(), line_x_min_pdf - 0.1,
                                msg=f"sub_rect.x={rect.x()} 超出左边界 {line_x_min_pdf}")
        self.assertLessEqual(rect.x() + rect.width(), line_x_max_pdf + 0.1,
                              msg=f"sub_rect.right={rect.x() + rect.width()} 超出右边界 {line_x_max_pdf}")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过子字符串精准度测试")
class TestCalculateFromLineFallback(unittest.TestCase):
    """R1 兜底：切分失败时退化为权重估算。"""

    def test_fallback_to_weight_estimation_when_segments_dont_match_text_length(self):
        # 用一张只有 2 段的图，text 长度 5 → 切分不匹配 → 退化
        img, _ = _make_line_image(width=200, height=40, char_blocks=2)
        worker = _make_worker(scan_scale=2.0)

        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABCDE"  # 5 字符
        rect = worker._calculate_from_line(box, text, 1, 3, img_region=img)

        self.assertIsNotNone(rect, "兜底路径也应返回 rect")
        # _detect_text_boundaries 会把 line_width 收紧到实际文字范围（~79 像素而非 200）
        # match_weight / total_weight = 2/5 = 0.4，所以宽度应在 (79/2)*0.4 ≈ 15.8 附近
        # 容忍较大区间，主要验证兜底路径能运行
        self.assertGreater(rect.width(), 5,
                            msg=f"兜底宽度={rect.width()} 应 > 5")
        self.assertLess(rect.width(), 30,
                            msg=f"兜底宽度={rect.width()} 应 < 30（line_width 已被收紧）")

    def test_no_img_region_uses_shrink_box_path(self):
        """img_region=None 时走 _shrink_box 分支（box_adjust_ratio=0 时即原 box）。"""
        worker = _make_worker(scan_scale=1.0, box_adjust_ratio=0.0)

        box = [[10, 10], [110, 10], [110, 30], [10, 30]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 0, 2, img_region=None)

        self.assertIsNotNone(rect)
        # box_adjust_ratio=0 → shrunk_box == box → line_x_min=10, line_x_max=110
        # text 长度 3，match_span=(0,2) → sub_w = 2/3 * 100 ≈ 66.67
        self.assertGreater(rect.width(), 50, msg=f"sub_w={rect.width()} 应该 > 50")
        self.assertLess(rect.width(), 75, msg=f"sub_w={rect.width()} 应该 < 75")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过子字符串精准度测试")
class TestMarginUnitConsistency(unittest.TestCase):
    """R4 修复：margin 在不同 scan_scale 下 PDF 点空间一致。"""

    def test_margin_in_pdf_space_consistent_across_scan_scales(self):
        """相同 PDF 区域在不同 scan_scale 下，PDF 空间 sub_rect 应一致。"""
        # scan_scale=1.0：100x40 像素代表 100x40 PDF 点
        # scan_scale=2.0：200x80 像素代表 100x40 PDF 点（相同 PDF 区域，更高分辨率）
        img_s1 = np.zeros((40, 100, 3), dtype=np.uint8)
        box_s1 = [[0, 0], [100, 0], [100, 40], [0, 40]]
        img_s2 = np.zeros((80, 200, 3), dtype=np.uint8)
        box_s2 = [[0, 0], [200, 0], [200, 80], [0, 80]]
        text = "A"

        worker_s1 = _make_worker(scan_scale=1.0)
        worker_s2 = _make_worker(scan_scale=2.0)

        rect_s1 = worker_s1._calculate_from_line(box_s1, text, 0, 1, img_region=img_s1)
        rect_s2 = worker_s2._calculate_from_line(box_s2, text, 0, 1, img_region=img_s2)

        self.assertIsNotNone(rect_s1)
        self.assertIsNotNone(rect_s2)

        # 两个 worker 在 PDF 空间下的 sub_rect 应该非常接近（差异 ≤ 1pt）
        # 因为图像代表相同 PDF 区域，差异只来自像素舍入和 margin 转换
        self.assertAlmostEqual(rect_s1.x(), rect_s2.x(), delta=1.0,
                                msg=f"scan_scale=1/2 x 不一致: {rect_s1.x()} vs {rect_s2.x()}")
        self.assertAlmostEqual(rect_s1.width(), rect_s2.width(), delta=1.0,
                                msg=f"scan_scale=1/2 width 不一致: {rect_s1.width()} vs {rect_s2.width()}")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过子字符串精准度测试")
class TestMinWidthAfterFix(unittest.TestCase):
    """R5 修复：min 宽度从 5 改为 2.0。"""

    def test_min_width_is_2pt_not_5pt(self):
        """构造 match_span 取单字符，验证 final_w 接近真实字符块宽度而非被强制到 5pt。"""
        # 1 个字符块 = 30 px / scan_scale=2.0 = 15pt（减 margin 后约 14.4pt）
        # R5 修复后 min 宽度为 2pt，远小于真实宽度，应该返回真实宽度
        img, _ = _make_line_image(width=200, height=40, char_blocks=4)
        worker = _make_worker(scan_scale=2.0)

        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABCD"
        rect = worker._calculate_from_line(box, text, 1, 2, img_region=img)

        self.assertIsNotNone(rect)
        # 应该接近 15pt（真实字符块宽度），而不是 5pt（R5 修复前的最小值）
        self.assertGreater(rect.width(), 10,
                            msg=f"width={rect.width()} 应 > 10（接近真实字符块宽 ~15pt，而非 5pt）")
        self.assertLess(rect.width(), 20,
                            msg=f"width={rect.width()} 应 < 20（接近真实字符块宽 ~15pt）")


if __name__ == "__main__":
    unittest.main()
