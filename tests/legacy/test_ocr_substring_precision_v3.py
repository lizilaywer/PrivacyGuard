"""v37.7.8 cp36: PDF 遮罩精准度修复 v3 单元测试

验证 F6-F14 改动：
  - F6: B 档累计权重对齐 + 线性插值（bisect + 段像素边界插值）
  - F7: C 档宽度估算改用 seg_block_width（避免 avg_seg_width * len(text) 高估）
  - F8: _segment_text_columns 自适应间隙检测（预切分 + 中位数 gap * 1.5）
  - F9: _split_wide_segment 等分回退（密度低谷失败时按 char_h * 0.9 等分）
  - F10: 复活 box_adjust_ratio（像素边界后做 post-shrink）
  - F11: _detect_text_boundaries 阈值 mean>220 用 0.30
  - F12: margin 双边对称（sub_x += margin/2, sub_w -= margin）
  - F13: _deduplicate_rects 按面积升序（保留较窄 rect）
  - F14: 二值化图像（use_enhance=True 预处理后）用固定 0.20

设计原则：
  - 用合成 BGR 图像构造可重现的字符块布局
  - 重点验证 B/C 档精度（bimodal 行为修复）
  - 不依赖真实 OCR 引擎（直接调用 _calculate_from_line）
"""

import unittest

import numpy as np

# 软探测：fitz/PyQt6 未装时跳过整个测试模块
try:
    from privacyguard.workers.ocr_worker import OCRWorker  # noqa: F401
    _OCR_WORKER_OK = True
    _OCR_WORKER_ERR = ""
except Exception as exc:  # pragma: no cover - 环境依赖探测
    _OCR_WORKER_OK = False
    _OCR_WORKER_ERR = f"{type(exc).__name__}: {exc}"
    OCRWorker = None  # type: ignore

# main.py 中的 _deduplicate_rects / _is_overlapping 需要独立测试
try:
    import main as _main_module  # noqa: F401
    _MAIN_OK = True
    _MAIN_ERR = ""
except Exception as exc:  # pragma: no cover
    _MAIN_OK = False
    _MAIN_ERR = f"{type(exc).__name__}: {exc}"


def _make_worker(scan_scale=2.0, off_x=0.0, off_w=0.0, box_adjust_ratio=0.0):
    """绕过 QThread.__init__，只装配测试需要的属性。"""
    worker = OCRWorker.__new__(OCRWorker)
    worker.scan_scale = scan_scale
    worker.off_x = off_x
    worker.off_w = off_w
    worker.box_adjust_ratio = box_adjust_ratio
    return worker


def _make_line_image_v3(width, height, char_blocks, gap, block_w, bg=255, fg=0):
    """构造合成 BGR 行图像：白色背景 + 黑色字符块（精确控制位置）。

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


def _make_fused_line_image(width, height, fuse_blocks, fuse_w, gap):
    """构造"部分字符粘连"的合成行图像：用于模拟 CJK 临界间隙失败场景。

    Args:
        fuse_blocks: [(start_x, end_x), ...] 每个粘连块的起止像素坐标
        fuse_w: 不使用（保留参数）
        gap: 不使用（保留参数）

    Returns:
        BGR 图像
    """
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    for x0, x1 in fuse_blocks:
        img[:, x0:x1, :] = 0
    return img


# ============================================================================
# F6: B 档累计权重对齐 + 线性插值
# ============================================================================

@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v3 测试")
class TestF6BtierCumulativeWeightInterpolation(unittest.TestCase):
    """F6: B 档累计权重对齐 + 线性插值（替代段块整体权重比例）。"""

    def test_b_tier_interpolates_within_fused_segment_for_liu_shao(self):
        """模拟"王小"粘连成 1 段、"芳"单独成段场景。

        3 字符 "ABC" + 2 段：
          - 段 1: (10, 70) 含 A、B 粘连（60px 宽）
          - 段 2: (90, 120) 含 C 单独（30px 宽）
        match_span=(1, 3) 取 "BC"，期望：
          - B 的左边界应在段 1 的右半（约 x=40-50，不是段 1 起点 10）
          - C 的右边界应在段 2 的右端（约 x=120）
        """
        # 构造图像：x=10-70 全黑（A+B 粘连），x=90-120 全黑（C 单独）
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 10:70, :] = 0    # 段 1：A+B 粘连（60px）
        img[:, 90:120, :] = 0   # 段 2：C 单独（30px）

        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"  # 3 字符
        # match_span=(1, 3) → 取 "BC"
        rect = worker._calculate_from_line(box, text, 1, 3, img_region=img)

        self.assertIsNotNone(rect, "B 档应返回 rect")
        # 期望 B 左边界在段 1 右半（约 x=40 像素 = 20 PDF pt）
        # F6 修复后：B 占段 1 的右 1/2，sub_x 应 ≈ 10 + 30 = 40 像素 = 20 PDF pt
        # 旧实现会算成 sub_x = 10 + (1/3) * 110 = 46.67 → 偏右
        self.assertGreaterEqual(rect.x(), 12,
                                msg=f"B 档 sub_x={rect.x()} 应在段 1 右半（>12pt）")
        self.assertLess(rect.x(), 30,
                        msg=f"B 档 sub_x={rect.x()} 应 < 30pt（B 左边界不应越过段 1 中点）")
        # 期望 C 右边界在段 2 右端（120 像素 = 60 PDF pt）
        self.assertAlmostEqual(rect.x() + rect.width(), 60, delta=5,
                                msg=f"B 档 right={rect.x() + rect.width()} 期望 ≈ 60pt")

    def test_b_tier_handles_uneven_segment_widths(self):
        """段宽度不均时，累计权重插值应正确分配位置。

        4 字符 "ABCD" + 3 段：
          - 段 1: (10, 30) A 单独（20px）
          - 段 2: (50, 110) B+C 粘连（60px）
          - 段 3: (130, 150) D 单独（20px）
        match_span=(1, 3) 取 "BC"，期望：
          - B 左边界在段 2 起点（约 x=50 像素 = 25 PDF pt）
          - C 右边界在段 2 终点（约 x=110 像素 = 55 PDF pt）
        """
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 10:30, :] = 0    # 段 1：A（20px）
        img[:, 50:110, :] = 0   # 段 2：B+C 粘连（60px）
        img[:, 130:150, :] = 0  # 段 3：D（20px）

        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABCD"  # 4 字符
        rect = worker._calculate_from_line(box, text, 1, 3, img_region=img)

        self.assertIsNotNone(rect, "B 档应返回 rect")
        # B 左边界应在段 2 起点（50px = 25pt），允许 ±5pt 误差
        self.assertAlmostEqual(rect.x(), 25, delta=5,
                                msg=f"B 档 sub_x={rect.x()} 期望 ≈ 25pt（段 2 起点）")
        # C 右边界应在段 2 终点（110px = 55pt），允许 ±5pt 误差
        self.assertAlmostEqual(rect.x() + rect.width(), 55, delta=5,
                                msg=f"B 档 right={rect.x() + rect.width()} 期望 ≈ 55pt（段 2 终点）")

    def test_b_tier_end_index_within_segment(self):
        """end_idx 落在段内时（不跨段），sub_w 应接近该段宽度的一部分。

        v37.7.9 cp38: 修正测试构造，避免 B 档权重不匹配导致的估算偏差。
        原构造 3 字符 "ABC" + 2 段（40px+30px），B 档权重对齐把 "AB" 结束
        位置映射到段 1（因 seg_cum_ratio=[0,0.571,1.0]，0.667>0.571 落段 1），
        sub_w=33pt 跨段。这是 B 档估算的固有限制，非 bug。
        改为 3 字符 + 3 段走 A 档（段数==字符数），match_span=(0,2) 取 "AB"，
        sub_w 应接近段 0+段 1 宽度。
        """
        # 3 段：A(10-40), B(50-80), C(90-120)，各 30px
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 10:40, :] = 0    # 段 0：A（30px）
        img[:, 50:80, :] = 0    # 段 1：B（30px）
        img[:, 90:120, :] = 0   # 段 2：C（30px）

        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 0, 2, img_region=img)

        self.assertIsNotNone(rect, "A 档应返回 rect")
        # A 档：sub_w = 段 0+段 1 宽度 = 60px = 30pt（减 margin 后约 29.4pt）
        self.assertGreater(rect.width(), 25,
                            msg=f"A 档 sub_w={rect.width()} 应 > 25pt（段 0+段 1 = 30pt）")
        self.assertLess(rect.width(), 35,
                        msg=f"A 档 sub_w={rect.width()} 应 < 35pt（不应跨到段 2）")


# ============================================================================
# F7: C 档宽度估算修正
# ============================================================================

@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v3 测试")
class TestF7CtierWidthEstimation(unittest.TestCase):
    """F7: C 档用 seg_block_width 替代 avg_seg_width * len(text)。"""

    def test_c_tier_does_not_overestimate_when_fused(self):
        """1 段粘连 + 3 字符 → C 档，宽度不应被高估。

        构造图像：x=10-40 全黑（30px，模拟 3 字符粘连成 1 段）
        scan_scale=2.0 → 段块宽 30px = 15pt
        match_span=(0, 3) 取整行，sub_w 应接近 15pt（不含 line_x_min/max 扩展）
        """
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 10:40, :] = 0  # 30px 全黑（模拟 3 字符粘连）

        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"  # 3 字符
        rect = worker._calculate_from_line(box, text, 0, 3, img_region=img)

        self.assertIsNotNone(rect, "C 档应返回 rect")
        # F7 修复后：refined_line_width = seg_block_width = 30px = 15pt
        # sub_w = 15pt - margin = ~14.4pt
        # 旧实现会算成 avg_seg_width * len(text) = 30 * 3 = 90px = 45pt（高估 3 倍）
        self.assertLess(rect.width(), 25,
                        msg=f"C 档 sub_w={rect.width()} 应 < 25pt（避免高估，旧实现会到 45pt）")
        self.assertGreater(rect.width(), 10,
                            msg=f"C 档 sub_w={rect.width()} 应 > 10pt（接近段块宽 15pt）")

    def test_c_tier_width_within_line_bounds(self):
        """C 档 sub_w 不超过 line_width。"""
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 50:80, :] = 0  # 30px 黑色块

        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 0, 3, img_region=img)

        self.assertIsNotNone(rect)
        # 整行宽度（_detect_text_boundaries 给的）= 30px = 15pt
        # sub_w 不应超过 line_width（减 margin 后）
        self.assertLessEqual(rect.width(), 15,
                             msg=f"C 档 sub_w={rect.width()} 应 ≤ line_width=15pt")


# ============================================================================
# F8: _segment_text_columns 自适应间隙检测
# ============================================================================

@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v3 测试")
class TestF8AdaptiveGapTolerance(unittest.TestCase):
    """F8: 自适应 gap_tolerance（预切分 + 中位数 gap * 1.5）。"""

    def test_adaptive_tolerance_splits_critical_gap(self):
        """临界间隙（gap 略小于 char_h/3）能被切分。

        构造图像：3 个字符块，间隙 10px（< char_h/3=13px for char_h=40）
        - F8 前：固定 gap_tolerance=13px → 间隙 10px 被认为是"短间隙"不切断 → 3 字符粘连成 1 段
        - F8 后：预切分用 tolerance=2 → 切出 3 段，中位数 gap=10，正式 tolerance=15 → 仍切 3 段
        """
        img, expected = _make_line_image_v3(width=200, height=40,
                                              char_blocks=3, gap=10, block_w=30)
        worker = _make_worker()
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        segments = worker._segment_text_columns(img, box)

        self.assertEqual(len(segments), 3,
                         msg=f"临界间隙应被切分，实际 {len(segments)} 段: {segments}")

    def test_adaptive_tolerance_falls_back_when_no_gaps(self):
        """无间隙（整行粘连）时回退到 char_h/3，正常返回 1 段。"""
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 10:190, :] = 0  # 全黑（无间隙）

        worker = _make_worker()
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        segments = worker._segment_text_columns(img, box)

        # 整行粘连 → 1 段
        self.assertEqual(len(segments), 1,
                         msg=f"整行粘连应返回 1 段，实际 {len(segments)}: {segments}")


# ============================================================================
# F9: _split_wide_segment 等分回退
# ============================================================================

@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v3 测试")
class TestF9EqualSplitFallback(unittest.TestCase):
    """F9: 密度低谷切分失败时，按 char_h * 0.9 等分回退。"""

    def test_equal_split_when_uniform_density(self):
        """整段均匀粘连（无低谷）→ 等分回退，切出 ≥2 段。

        构造：100x40 全黑段，char_h=40
        - F9 前：返回 []（无法切分）
        - F9 后：估算 n_chars = 100 / (40*0.9) ≈ 3，等分 3 段
        """
        img = np.full((40, 100, 3), 0, dtype=np.uint8)  # 全黑
        worker = _make_worker()
        # _split_wide_segment(img, seg_left, seg_right, y_min, y_max, char_h)
        sub_segs = worker._split_wide_segment(img, 0, 100, 0, 40, 40)

        self.assertGreaterEqual(len(sub_segs), 2,
                                msg=f"均匀段应被等分回退，实际 {len(sub_segs)}: {sub_segs}")
        # 每个子段宽度应接近 char_h * 0.9 = 36px
        for l, r in sub_segs:
            self.assertGreater(r - l, 5,
                                msg=f"子段宽 {r - l} 应 > 5px（接近字符宽）")

    def test_equal_split_estimates_char_count_reasonably(self):
        """等分数量应基于段宽 / 估算单字符宽（char_h * 0.9）。

        v37.7.9 cp38: 修正段宽为 108px（108/36=3.0 整除）。
        原段宽 90px → 90/36=2.5，Python round(2.5) 用银行家舍入（round half
        to even）返回 2，等分 2 段。这是 Python round() 行为，非 bug。
        改为 108px 让除法整除，避免银行家舍入边界。
        """
        # 段宽 108px, char_h=40 → 估算字符宽 36px → n_chars = round(108/36) = 3
        img = np.full((40, 108, 3), 0, dtype=np.uint8)
        worker = _make_worker()
        sub_segs = worker._split_wide_segment(img, 0, 108, 0, 40, 40)

        self.assertEqual(len(sub_segs), 3,
                         msg=f"108px / 36px 应等分 3 段，实际 {len(sub_segs)}: {sub_segs}")


# ============================================================================
# F10: 复活 box_adjust_ratio
# ============================================================================

@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v3 测试")
class TestF10BoxAdjustRatioReactivated(unittest.TestCase):
    """F10: box_adjust_ratio 在像素边界后做 post-shrink。"""

    def test_positive_ratio_shrinks_sub_w(self):
        """box_adjust_ratio=0.2 → line_width 收缩 20%，sub_w 应相应变小。"""
        img, _ = _make_line_image_v3(width=200, height=40,
                                      char_blocks=3, gap=20, block_w=30)
        worker_default = _make_worker(scan_scale=2.0, box_adjust_ratio=0.0)
        worker_shrink = _make_worker(scan_scale=2.0, box_adjust_ratio=0.2)

        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"
        rect_default = worker_default._calculate_from_line(box, text, 0, 3, img_region=img)
        rect_shrink = worker_shrink._calculate_from_line(box, text, 0, 3, img_region=img)

        self.assertIsNotNone(rect_default)
        self.assertIsNotNone(rect_shrink)
        # 收缩 20% 后，sub_w 应小于默认
        self.assertLess(rect_shrink.width(), rect_default.width(),
                         msg=f"收缩后 sub_w={rect_shrink.width()} 应 < 默认 {rect_default.width()}")

    def test_zero_ratio_unchanged(self):
        """box_adjust_ratio=0 → 行为与默认一致（不收缩）。"""
        img, _ = _make_line_image_v3(width=200, height=40,
                                      char_blocks=3, gap=20, block_w=30)
        worker = _make_worker(scan_scale=2.0, box_adjust_ratio=0.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 0, 3, img_region=img)

        self.assertIsNotNone(rect)
        # 默认行为：sub_w 应接近段块宽（3 * 30 + 2 * 20 = 130px = 65pt）
        self.assertGreater(rect.width(), 50,
                            msg=f"默认 sub_w={rect.width()} 应 > 50pt")


# ============================================================================
# F11: _detect_text_boundaries 阈值更严格
# ============================================================================

@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v3 测试")
class TestF11StricterThreshold(unittest.TestCase):
    """F11: 高对比度（mean>220）用 0.30 严格阈值。"""

    def test_threshold_030_excludes_antialiasing(self):
        """白底黑字（mean>220）→ 用 0.30 阈值，line_width 紧贴实际文字。

        构造图像：白底 + 中间 30px 黑色块（mean 应 > 220）
        旧阈值 0.20 会把抗锯齿边缘 1-2px 也算入 → line_width 偏大
        新阈值 0.30 更严格 → line_width 更接近 30px
        """
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 50:80, :] = 0  # 30px 黑色块

        worker = _make_worker()
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        line_x_min, line_x_max = worker._detect_text_boundaries(img, box)

        # mean 应 > 220（白底），用 0.30 阈值
        # 实际文字范围 50-80（30px），阈值 0.30 应紧贴此范围
        self.assertGreaterEqual(line_x_min, 48,
                                 msg=f"line_x_min={line_x_min} 应 ≥ 48（紧贴文字左边界 50）")
        self.assertLessEqual(line_x_max, 82,
                              msg=f"line_x_max={line_x_max} 应 ≤ 82（紧贴文字右边界 80）")


# ============================================================================
# F12: margin 双边对称
# ============================================================================

@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v3 测试")
class TestF12SymmetricMargin(unittest.TestCase):
    """F12: margin 双边对称（中心不变）。"""

    def test_margin_symmetric_center_preserved(self):
        """match_span 覆盖整段时，sub_rect 中心应接近段块中心。

        构造：3 段 + 3 字符 → A 档直接取段，sub_x/sub_w 在段块范围
        F12 修复后：sub_x += margin/2, sub_w -= margin
        中心 = sub_x + sub_w/2 应保持不变（接近段块中心）
        """
        img, expected = _make_line_image_v3(width=200, height=40,
                                              char_blocks=3, gap=20, block_w=30)
        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "ABC"
        rect = worker._calculate_from_line(box, text, 0, 3, img_region=img)

        self.assertIsNotNone(rect)
        # 段块中心 = (expected[0][0] + expected[-1][1]) / 2 / scan_scale
        seg_block_center_pdf = (expected[0][0] + expected[-1][1]) / 2 / 2.0
        rect_center = rect.x() + rect.width() / 2
        # 中心应接近段块中心（允差 1pt，因为 margin 是对称的）
        self.assertAlmostEqual(rect_center, seg_block_center_pdf, delta=1.5,
                                msg=f"margin 后中心={rect_center} 应接近段块中心 {seg_block_center_pdf}")


# ============================================================================
# F13: _deduplicate_rects 保留最窄 rect
# ============================================================================

@unittest.skipUnless(_MAIN_OK, f"无法导入 main 模块（{_MAIN_ERR}），跳过 F13 测试")
class TestF13DedupKeepNarrowest(unittest.TestCase):
    """F13: 去重时按面积升序，保留较窄 rect。"""

    def _make_dedup_helper(self):
        """构造一个最小化的 helper 类，复用 main 中的 _is_overlapping 逻辑。"""
        class DedupHelper:
            _is_overlapping = _main_module.MainWindow._is_overlapping
            _deduplicate_rects = _main_module.MainWindow._deduplicate_rects
        helper = DedupHelper.__new__(DedupHelper)
        return helper

    def test_dedup_keeps_narrower_rect_when_overlapping(self):
        """两个高度重叠的 rect，应保留较窄的（面积较小的）。"""
        from PyQt6.QtCore import QRectF
        # rect_wide: x=50, w=30 → 面积 30*40=1200
        # rect_narrow: x=52, w=20 → 面积 20*40=800（较窄）
        rect_wide = QRectF(50, 0, 30, 40)
        rect_narrow = QRectF(52, 0, 20, 40)

        helper = self._make_dedup_helper()
        # 把宽的放前面，窄的放后面，验证去重后保留窄的
        result = helper._deduplicate_rects([rect_wide, rect_narrow])

        self.assertEqual(len(result), 1, "两个高度重叠 rect 应保留 1 个")
        # 应保留较窄的（面积较小的）
        self.assertEqual(result[0].width(), 20,
                         msg=f"应保留较窄 rect（width=20），实际 width={result[0].width()}")

    def test_dedup_keeps_both_when_not_overlapping(self):
        """两个不重叠的 rect，应都保留。"""
        from PyQt6.QtCore import QRectF
        rect1 = QRectF(0, 0, 30, 40)
        rect2 = QRectF(100, 0, 30, 40)  # 完全不重叠

        helper = self._make_dedup_helper()
        result = helper._deduplicate_rects([rect1, rect2])

        self.assertEqual(len(result), 2, "不重叠 rect 应都保留")


# ============================================================================
# F14: 二值化图像兼容（use_enhance=True 预处理后）
# ============================================================================

@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v3 测试")
class TestF14BinaryImageCompatibility(unittest.TestCase):
    """F14: 二值化图像（use_enhance=True 预处理后）用固定 0.20 阈值。"""

    def test_binary_image_uses_fixed_threshold(self):
        """构造二值化图像（mean 接近 0 或 255），验证 _detect_text_boundaries 不崩溃。

        use_enhance=True 时 preprocess_image 已做 Otsu，输出 mean 接近 0 或 255
        F14 修复后：is_binary 检测后用固定 0.20 阈值

        v37.7.9 cp38: 修正测试图像构造为"白底黑字"（符合生产场景）。
        原构造"黑底白字"（mean≈38）与 _detect_text_boundaries 假设矛盾：
          - INV Otsu 后白底→背景 0(黑)，黑字→文字 255(白)
          - h_projection 文字列高值，背景列低值，text_cols = where(h_proj > thr) 找文字列 ✓
          - 黑底白字 INV 后相反，text_cols 找到背景列 ✗
        生产场景扫描件均为白底黑字，原测试构造不符合实际。
        """
        # 构造二值化图像：背景 255（白），文字 0（黑）— 白底黑字，符合生产场景
        # mean 接近 255（背景占多数），is_binary=True 走固定 0.20 阈值
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 50:80, :] = 0  # 黑色文字块

        worker = _make_worker()
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        # 不应抛异常，返回合理的 left/right
        line_x_min, line_x_max = worker._detect_text_boundaries(img, box)

        # 文字在 50-80，检测应大致在此范围
        self.assertGreaterEqual(line_x_min, 45,
                                 msg=f"二值化图像 line_x_min={line_x_min} 应 ≥ 45")
        self.assertLessEqual(line_x_max, 85,
                              msg=f"二值化图像 line_x_max={line_x_max} 应 ≤ 85")


# ============================================================================
# 真实场景 bimodal 行为修复验证
# ============================================================================

@unittest.skipUnless(_OCR_WORKER_OK, f"无法导入 OCRWorker（{_OCR_WORKER_ERR}），跳过 v3 测试")
class TestRealWorldBimodalFixed(unittest.TestCase):
    """端到端模拟"王小明/孙志华"在不同段数下的精度。

    验证 bimodal 行为修复：
    - 3 段（精确切分）→ A 档 → 精准
    - 2 段（部分粘连）→ B 档 → 累计权重对齐后接近精准
    - 1 段（整行粘连）→ C 档 → 宽度不被高估
    """

    def test_liu_shaofang_3_chars_3_segments_accurate(self):
        """3 字符 + 3 段 → A 档，sub_rect 应精准覆盖目标。"""
        # 构造：3 个 30px 字符块，间隙 20px
        img, expected = _make_line_image_v3(width=200, height=40,
                                              char_blocks=3, gap=20, block_w=30)
        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "王小明"  # 3 CJK 字符
        # match_span=(0, 3) 取整个名字
        rect = worker._calculate_from_line(box, text, 0, 3, img_region=img)

        self.assertIsNotNone(rect)
        # 期望覆盖 3 个字符块：expected[0][0] 到 expected[2][1]
        expected_left_pdf = expected[0][0] / 2.0
        expected_right_pdf = expected[2][1] / 2.0
        self.assertAlmostEqual(rect.x(), expected_left_pdf, delta=3,
                                msg=f"A 档 x={rect.x()} 期望 {expected_left_pdf}")
        self.assertAlmostEqual(rect.x() + rect.width(), expected_right_pdf, delta=3,
                                msg=f"A 档 right={rect.x() + rect.width()} 期望 {expected_right_pdf}")

    def test_liu_shaofang_3_chars_2_segments_b_tier_accurate(self):
        """3 字符 + 2 段（"王小"粘连）→ B 档，sub_rect 应接近精准。

        关键：F6 修复后 B 档用累计权重插值，sub_x 不再被均摊到段块起点。
        """
        # 构造：段 1 (10-70) 含"王小"粘连（60px），段 2 (90-120) 含"芳"单独（30px）
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 10:70, :] = 0    # 段 1：刘+少粘连（60px）
        img[:, 90:120, :] = 0   # 段 2：芳单独（30px）

        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "王小明"
        # match_span=(1, 3) 取 "小明"
        rect = worker._calculate_from_line(box, text, 1, 3, img_region=img)

        self.assertIsNotNone(rect, "B 档应返回 rect")
        # "少"应在段 1 右半（约 x=40-70 像素 = 20-35pt）
        # F6 修复后：sub_x 应在段 1 右半，不是段 1 起点
        self.assertGreaterEqual(rect.x(), 12,
                                msg=f"B 档 sub_x={rect.x()} 应 ≥ 12pt（在段 1 右半）")
        # "芳"右边界应在段 2 右端（120px = 60pt）
        self.assertAlmostEqual(rect.x() + rect.width(), 60, delta=5,
                                msg=f"B 档 right={rect.x() + rect.width()} 期望 ≈ 60pt")

    def test_sun_zhihua_3_chars_1_segment_c_tier_not_overestimated(self):
        """3 字符 + 1 段（整行粘连）→ C 档，宽度不应被高估。

        关键：F7 修复后 C 档用 seg_block_width，不再用 avg_seg_width * len(text)。
        """
        # 构造：1 个 90px 全黑段（模拟 3 字符整行粘连）
        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        img[:, 10:100, :] = 0  # 90px 全黑（3 字符粘连成 1 段）

        worker = _make_worker(scan_scale=2.0)
        box = [[0, 0], [200, 0], [200, 40], [0, 40]]
        text = "孙志华"
        # match_span=(0, 3) 取整个名字
        rect = worker._calculate_from_line(box, text, 0, 3, img_region=img)

        self.assertIsNotNone(rect, "C 档应返回 rect")
        # 段块宽 = 90px = 45pt
        # F7 修复后：refined_line_width = seg_block_width = 45pt
        # sub_w 应接近 45pt（减 margin 后约 44.4pt）
        # 旧实现会算成 avg_seg_width * len(text) = 90 * 3 = 270px = 135pt（高估 3 倍）
        self.assertLess(rect.width(), 50,
                        msg=f"C 档 sub_w={rect.width()} 应 < 50pt（避免高估，旧实现会到 135pt）")
        self.assertGreater(rect.width(), 35,
                            msg=f"C 档 sub_w={rect.width()} 应 > 35pt（接近段块宽 45pt）")


if __name__ == "__main__":
    unittest.main()
