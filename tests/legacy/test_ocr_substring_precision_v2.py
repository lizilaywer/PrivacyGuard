"""v37.7.8 cp35: PDF 遮罩精准度修复 v2 单元测试

验证 F1/F2/F3/F5 改动：
  - F1: _calculate_from_line 三档混合算法（A 精确 / B 段块权重 / C 像素收紧权重）
  - F2: _segment_text_columns 参数改用字符高度（gap_tolerance / min_seg_width / kernel_w）
  - F3: _split_wide_segment 超宽段二次切分
  - F5: _detect_text_boundaries 阈值自适应（基于对比度）

设计原则：
  - 用合成 BGR 图像构造可重现的字符块布局
  - 验证 sub_rect 落在预期像素范围内（容忍 ≤5pt 误差，含 margin/边界保护）
  - 不依赖真实 OCR 引擎（直接调用 _calculate_from_line）
"""

import unittest

import numpy as np

# 软探测：fitz/PyQt6 未装时跳过整个测试模块
try:
    from privacyguard.workers.ocr_worker import OCRWorker  # noqa: F401
    _OCR_WORKER_OK = True
    _OCR_WORKER_ERR = ""
except Exception as exc:  # pragma: no cover
    _OCR_WORKER_OK = False
    _OCR_WORKER_ERR = f"{type(exc).__name__}: {exc}"
    OCRWorker = None  # type: ignore


def _make_worker(scan_scale=2.0, off_x=0.0, off_w=0.0, box_adjust_ratio=0.0):
    """绕过 QThread.__init__，只装配测试需要的属性。"""
    worker = OCRWorker.__new__(OCRWorker)
    worker.scan_scale = scan_scale
    worker.off_x = off_x
    worker.off_w = off_w
    worker.box_adjust_ratio = box_adjust_ratio
    return worker


def _make_line_image_v2(width, height, char_blocks, gap, block_w, bg=255, fg=0):
    """构造合成 BGR 行图像：白色背景 + 黑色字符块（精确控制位置）。

    Args:
        width: 图像宽
        height: 图像高
        char_blocks: 字符块数量
        gap: 块之间的间隙（像素）
        block_w: 每个块的宽度（像素）

    Returns:
        (img, expected_segments): BGR 图像 + 预期字符块 (left, right) 列表
    """
    img = np.full((height, width, 3), bg, dtype=np.uint8)
    expected = []
    pos = gap  # 起始位置
    for i in range(char_blocks):
        x0 = pos
        x1 = x0 + block_w
        if x1 > width:
            break
        img[:, x0:x1, :] = fg
        expected.append((x0, x1 - 1))
        pos = x1 + gap
    return img, expected


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v2 测试")
class TestFSplitWideSegment(unittest.TestCase):
    """F3: 超宽段二次切分。"""

    def test_split_returns_two_subsegments_when_clear_gap_exists(self):
        """构造一个含明确低谷的超宽段，验证 _split_wide_segment 能切出 2 段。"""
        # 200x40 图像，前 80px 全黑，中间 20px 全白（密度低谷），后 80px 全黑
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 0:80, :] = 0      # 左半黑色块
        img[:, 100:180, :] = 0   # 右半黑色块
        worker = _make_worker()

        # _split_wide_segment 参数：(img, seg_left, seg_right, y_min, y_max, char_h)
        sub_segs = worker._split_wide_segment(img, 0, 200, 0, 40, 40)

        self.assertGreaterEqual(len(sub_segs), 2,
                                f"应切出 ≥2 段，实际 {len(sub_segs)}: {sub_segs}")
        # 第一段应在左半（0-80）
        self.assertLess(sub_segs[0][0], 80,
                        msg=f"第一段左边界={sub_segs[0][0]} 应在左半（<80）")
        # 最后一段应在右半（100-180）
        self.assertGreater(sub_segs[-1][1], 100,
                           msg=f"最后段右边界={sub_segs[-1][1]} 应在右半（>100）")

    def test_returns_empty_when_no_clear_gap(self):
        """整段均匀密度（无低谷），_split_wide_segment 应返回 []（无法切分）。"""
        img = np.full((40, 100, 3), 0, dtype=np.uint8)  # 全黑
        worker = _make_worker()

        sub_segs = worker._split_wide_segment(img, 0, 100, 0, 40, 40)
        self.assertEqual(sub_segs, [], f"均匀段不应被切分，实际 {sub_segs}")

    def test_returns_empty_for_too_narrow_segment(self):
        """段过窄（小于 char_h/4），切分后过滤掉过窄子段，结果 <2 段则返回 []。"""
        img = np.full((40, 5, 3), 0, dtype=np.uint8)  # 5px 宽全黑
        worker = _make_worker()

        sub_segs = worker._split_wide_segment(img, 0, 5, 0, 40, 40)
        self.assertEqual(sub_segs, [])


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v2 测试")
class TestF1TierA(unittest.TestCase):
    """F1 A 档：段数 == 文本长度 → 直接取段。"""

    def test_tier_a_returns_subrect_at_expected_segment(self):
        """3 段 + 3 字符 → A 档，match_span=(1,3) 应取后两段。"""
        img, expected = _make_line_image_v2(width=200, height=40,
                                              char_blocks=3, gap=20, block_w=30)
        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 1, 3, img_region=img)

        self.assertIsNotNone(rect)
        # 期望 sub_rect 覆盖 expected[1] 左边到 expected[2] 右边（PDF 点空间）
        expected_left_pdf = expected[1][0] / 2.0
        expected_right_pdf = expected[2][1] / 2.0
        self.assertAlmostEqual(rect.x(), expected_left_pdf, delta=5,
                                msg=f"A 档 x={rect.x()} 期望 {expected_left_pdf}")
        self.assertAlmostEqual(rect.x() + rect.width(), expected_right_pdf, delta=5,
                                msg=f"A 档 right={rect.x() + rect.width()} 期望 {expected_right_pdf}")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v2 测试")
class TestF1TierB(unittest.TestCase):
    """F1 B 档：段数与文本长度接近但不等 → 用段块做权重估算。"""

    def test_tier_b_uses_segment_block_for_weight_estimation(self):
        """4 段 + 6 字符（差 2，在 max(2, 30%*6)=2 范围内）→ B 档。

        构造 4 段均匀分布图像，text="ABCDEF"，match_span=(2,5) 取 "CDE"。
        B 档用段块 + 权重估算，权重比例 = (2/6, 3/6) = (0.333, 0.5)。
        """
        img, _ = _make_line_image_v2(width=300, height=40,
                                      char_blocks=4, gap=30, block_w=40)
        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [300, 0], [300, 40], [0, 40]]
        text = "ABCDEF"  # 6 字符，4 段 → B 档
        rect = worker._calculate_from_line(box, text, 2, 5, img_region=img)

        self.assertIsNotNone(rect, "B 档应返回非 None rect")
        # 段块大致范围：第一段 left=30，最后段 right=270
        # B 档用 seg_block_width + 权重比例
        # 检查 rect.x 在段块范围内（不超出 line_x_min/max）
        self.assertGreaterEqual(rect.x(), 0)
        self.assertLessEqual(rect.x() + rect.width(), 150)  # PDF 空间 = 300 / 2
        # 宽度应在合理范围（3 字符 / 6 字符 * 段块宽度）
        self.assertGreater(rect.width(), 10, msg=f"B 档 width={rect.width()} 过小")
        self.assertLess(rect.width(), 100, msg=f"B 档 width={rect.width()} 过大")

    def test_tier_b_does_not_purely_use_ocr_box(self):
        """B 档应用段块收紧，sub_rect 不应基于 OCR box 的全宽 300px。"""
        img, _ = _make_line_image_v2(width=300, height=40,
                                      char_blocks=4, gap=30, block_w=40)
        worker = _make_worker(scan_scale=2.0)
        # OCR box 故意比段块更宽
        box = [[-50, 0], [350, 0], [350, 40], [-50, 40]]
        text = "ABCDEF"  # 6 字符
        rect = worker._calculate_from_line(box, text, 2, 5, img_region=img)

        self.assertIsNotNone(rect)
        # 段块在 30-270（PDF 空间 15-135）
        # B 档应让 sub_rect 在段块附近，不应被 -50 或 350 拉走
        self.assertGreaterEqual(rect.x(), 0, msg=f"rect.x={rect.x()} 不应被 OCR box 左边 -50 拉走")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v2 测试")
class TestF1TierC(unittest.TestCase):
    """F1 C 档：段数严重不匹配 → 像素收紧权重估算。"""

    def test_tier_c_uses_avg_seg_width_to_refine_line_width(self):
        """2 段 + 8 字符（差 6 > max(2, 30%*8)=2）→ C 档。

        C 档用 avg_seg_width * len(text) 修正 line_width。
        构造 2 个 30px 宽的段，间距 30px → 段块宽 90px。
        avg_seg_width = 30，estimated_text_width = 30 * 8 = 240。
        line_width = OCR box 宽（假设 300）。
        refined_line_width = min(300, max(240, 90)) = 240。
        """
        img, _ = _make_line_image_v2(width=300, height=40,
                                      char_blocks=2, gap=30, block_w=30)
        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [300, 0], [300, 40], [0, 40]]
        text = "ABCDEFGH"  # 8 字符
        rect = worker._calculate_from_line(box, text, 2, 5, img_region=img)

        self.assertIsNotNone(rect, "C 档应返回非 None rect")
        # match 3 字符 / 8 字符 = 0.375
        # refined_line_width ≈ 240px，sub_w_px ≈ 0.375 * 240 = 90px
        # PDF 空间 sub_w ≈ 90 / 2 = 45pt
        # 容忍较大误差，主要验证不走纯权重路径（OCR box 300px → sub_w 0.375*300/2=56pt）
        # C 档应让 sub_w < 纯权重估算的 56pt
        self.assertLess(rect.width(), 56,
                        msg=f"C 档 width={rect.width()} 应小于纯权重估算 56pt")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v2 测试")
class TestF2CharHeightBasedParams(unittest.TestCase):
    """F2: 切分参数改用字符高度。"""

    def test_segmentation_handles_normal_cjk_gaps(self):
        """构造典型 CJK 行图像（字高 40px，字符宽 30px，间隙 10px），验证段数 == 字符数。"""
        # 5 个字符块，每块 30px 宽，间隙 10px，字高 40px
        img, expected = _make_line_image_v2(width=300, height=40,
                                              char_blocks=5, gap=10, block_w=30)
        worker = _make_worker()
        box = [[0, 0], [300, 0], [300, 40], [0, 40]]

        segments = worker._segment_text_columns(img, box)

        # 5 个清晰字符块 → 应得到 5 段
        self.assertEqual(len(segments), 5,
                         f"应得 5 段，实际 {len(segments)}: {segments}")

    def test_segmentation_does_not_over_split_internal_strokes(self):
        """字符内部小间隙（<1/3 字高）不应被误切。"""
        # 构造一个 80px 宽的字符块，内部有 5px 间隙
        # 字高 40px → gap_tolerance = 40/3 ≈ 13px，5px 间隙应被忽略
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 30:70, :] = 0       # 左半字符
        img[:, 75:115, :] = 0      # 右半字符（5px 间隙）
        worker = _make_worker()
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]

        segments = worker._segment_text_columns(img, box)

        # 5px 间隙 < gap_tolerance(13) → 应被合并为 1 段，而非切成 2 段
        self.assertEqual(len(segments), 1,
                         msg=f"5px 内部间隙不应被切分，实际 {len(segments)} 段: {segments}")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v2 测试")
class TestF5AdaptiveThreshold(unittest.TestCase):
    """F5: _detect_text_boundaries 阈值自适应。"""

    def test_high_contrast_uses_strict_threshold(self):
        """高对比度（白底黑字 mean>200）应使用 0.20 阈值。

        构造一张抗锯齿边缘图像：主字符块 + 边缘 1 像素灰阶。
        0.20 阈值会过滤掉边缘 1 像素的低密度列，让 line_x_min 更紧。
        """
        img = np.full((40, 100, 3), 255, dtype=np.uint8)
        # 主字符块：30-70
        img[:, 30:70, :] = 0
        # 模拟抗锯齿：在 25-30 和 70-75 列加灰色像素（4 行）
        img[:4, 25:30, :] = 128
        img[:4, 70:75, :] = 128
        # mean 应该 > 200（白底占大多数）
        worker = _make_worker()
        box = [[0, 0], [100, 0], [100, 40], [0, 40]]

        left, right = worker._detect_text_boundaries(img, box)
        # 严格阈值下，left 应接近 30（不含 25-30 的抗锯齿）
        self.assertGreaterEqual(left, 28, msg=f"left={left} 应排除抗锯齿（≥28）")
        self.assertLessEqual(left, 32, msg=f"left={left} 应接近 30")

    def test_low_contrast_uses_lenient_threshold(self):
        """低对比度（mean<=200）应使用 0.12 阈值，避免漏掉淡字符。"""
        # 全图灰色背景（mean < 200），主字符稍深
        img = np.full((40, 100, 3), 180, dtype=np.uint8)
        img[:, 30:70, :] = 80  # 深灰字符
        worker = _make_worker()
        box = [[0, 0], [100, 0], [100, 40], [0, 40]]

        left, right = worker._detect_text_boundaries(img, box)
        # 宽松阈值下，应能检测到 30-70 的字符范围
        self.assertLessEqual(abs(left - 30), 3, msg=f"left={left} 应接近 30")
        self.assertLessEqual(abs(right - 69), 3, msg=f"right={right} 应接近 69")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v2 测试")
class TestRealisticChineseLine(unittest.TestCase):
    """真实场景：模拟 "原告王小明，男，汉族" 含标点的中文行。"""

    def test_match_keyword_lieshaofang_returns_correct_position(self):
        """模拟 9 字符中文行，match_span=(2,5) 取 "王小明"。

        构造：9 个 30px 宽字符块，间隙 10px，字高 40px。
        总宽 = 9 * 30 + 8 * 10 = 270 + 80 = 350px。
        match_span=(2,5) 取第 3-5 字符（"王小明"）。
        """
        img, expected = _make_line_image_v2(width=400, height=40,
                                              char_blocks=9, gap=10, block_w=30)
        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [400, 0], [400, 40], [0, 40]]
        text = "原告王小明，男，汉族"  # 9 字符
        # match_span=(2,5) 取 "王小明"
        rect = worker._calculate_from_line(box, text, 2, 5, img_region=img)

        self.assertIsNotNone(rect, "应返回非 None rect")
        # 期望 sub_rect 覆盖 expected[2] 左边到 expected[4] 右边（PDF 点空间）
        # expected[2] = (50, 79), expected[4] = (90, 119)
        # PDF 空间：left=25, right=59.5
        expected_left_pdf = expected[2][0] / 2.0
        expected_right_pdf = expected[4][1] / 2.0
        self.assertAlmostEqual(rect.x(), expected_left_pdf, delta=8,
                                msg=f"中文行 x={rect.x()} 期望 {expected_left_pdf}")
        self.assertAlmostEqual(rect.x() + rect.width(), expected_right_pdf, delta=8,
                                msg=f"中文行 right={rect.x() + rect.width()} 期望 {expected_right_pdf}")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v2 测试")
class TestCjkPlusDigitsLine(unittest.TestCase):
    """真实场景：模拟 "身份证号123456789012345" CJK + 数字混合行。"""

    def test_match_digit_part_returns_position_in_digit_region(self):
        """模拟 4 CJK + 15 数字 = 19 字符，match_span=(4,19) 取数字部分。

        CJK 字符（4 个）：30px 宽，间隙 10px
        数字（15 个）：18px 宽（窄），间隙 5px
        """
        img = np.full((40, 500, 3), 255, dtype=np.uint8)
        # 4 个 CJK：30-60, 70-100, 110-140, 150-180
        positions = []
        pos = 30
        for i in range(4):
            img[:, pos:pos + 30, :] = 0
            positions.append((pos, pos + 30 - 1))
            pos += 40  # 30 + 10 间隙
        # 15 个数字：宽 18px，间隙 5px
        for i in range(15):
            img[:, pos:pos + 18, :] = 0
            positions.append((pos, pos + 18 - 1))
            pos += 23  # 18 + 5 间隙

        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [500, 0], [500, 40], [0, 40]]
        text = "身份证号" + "123456789012345"  # 19 字符
        # match_span=(4,19) 取所有数字
        rect = worker._calculate_from_line(box, text, 4, 19, img_region=img)

        self.assertIsNotNone(rect, "应返回非 None rect")
        # 期望 sub_rect 从第 5 字符（数字开始）位置
        # 第 5 字符 left = 30 + 4*40 = 190
        # 最后字符 right = 190 + 15*23 - 5 = 190 + 345 - 5 = 530，但被 line_x_max=500 截断
        # PDF 空间：left = 190/2 = 95
        expected_left_pdf = positions[4][0] / 2.0
        self.assertAlmostEqual(rect.x(), expected_left_pdf, delta=15,
                                msg=f"CJK+数字 x={rect.x()} 期望 {expected_left_pdf}")
        # 宽度应较大（15 个数字）
        self.assertGreater(rect.width(), 50,
                            msg=f"15 字符数字应宽 > 50pt，实际 {rect.width()}")


@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v2 测试")
class TestBimodalBehaviorFixed(unittest.TestCase):
    """验证 cp35 修复了 bimodal 行为：段数不匹配时不再完全退化为纯权重估算。"""

    def test_partial_match_still_uses_pixel_info(self):
        """段数与文本长度差 2（在 B 档范围内），sub_rect 应基于段块而非 OCR box 全宽。"""
        # 构造 4 段 + 6 字符
        img, _ = _make_line_image_v2(width=300, height=40,
                                      char_blocks=4, gap=30, block_w=40)
        worker = _make_worker(scan_scale=2.0)
        # OCR box 故意比段块宽（左边多 50px，右边多 50px）
        box = [[-50, 0], [350, 0], [350, 40], [-50, 40]]
        text = "ABCDEF"
        rect = worker._calculate_from_line(box, text, 2, 5, img_region=img)

        self.assertIsNotNone(rect)
        # 段块：30 + 4*40 + 3*30 - 30 = 30 + 160 + 90 - 30 = 250? Let me recalc
        # Actually: 4 segments, each 40 wide, gap 30
        # seg1: 30-70, seg2: 100-140, seg3: 170-210, seg4: 240-280
        # seg_block_left = 30, seg_block_right = 280, seg_block_width = 250
        # B 档用 seg_block 做权重估算
        # prefix_weight/total = 2/6 (ASCII weights 0.55 each, but all equal so ratio = 2/6)
        # sub_x_px = 30 + (2/6) * 250 = 30 + 83.33 = 113.33
        # sub_w_px = (3/6) * 250 = 125
        # PDF: x = 113.33/2 = 56.67, w = 125/2 = 62.5
        # 验证 rect.x 不被 OCR box 拉到 -50
        self.assertGreater(rect.x(), 0,
                           msg=f"rect.x={rect.x()} 应基于段块（>0），不应被 OCR box 拉到负值")
        # 验证宽度合理
        self.assertGreater(rect.width(), 30,
                           msg=f"B 档 width={rect.width()} 应 > 30pt（基于段块）")

    def test_far_mismatch_uses_pixel_refined_weight(self):
        """段数与文本长度差很大（C 档），sub_rect 应被 avg_seg_width 收紧。"""
        # 构造 2 段 + 8 字符
        img, _ = _make_line_image_v2(width=400, height=40,
                                      char_blocks=2, gap=30, block_w=30)
        worker = _make_worker(scan_scale=2.0)
        # OCR box 故意比段块宽很多
        box = [[-100, 0], [500, 0], [500, 40], [-100, 40]]
        text = "ABCDEFGH"  # 8 字符，2 段（差 6 > max(2, 30%*8)=2）→ C 档
        rect = worker._calculate_from_line(box, text, 2, 5, img_region=img)

        self.assertIsNotNone(rect)
        # C 档用 avg_seg_width * len(text) 收紧 line_width
        # avg_seg_width = 30, len(text) = 8 → estimated_text_width = 240
        # 不应被 OCR box 全宽 600px 拉走
        # match 3 字符 → sub_w 应 ≈ (3/8) * 240 = 90px → PDF 45pt
        self.assertLess(rect.width(), 100,
                        msg=f"C 档 width={rect.width()} 应被 avg_seg_width 收紧（<100pt）")


if __name__ == "__main__":
    unittest.main()
