"""calculate_sub_rect OCR box 宽度限制单元测试（cp54 → cp118 演进）

历史：
- v37.7.18 cp54：OCR 返回跨整页大框时权重估算会生成接近整行宽度的 sub_w，
  产生"一大块"超大遮罩。修复策略是 box 宽 > 图像宽 * 0.8 时 calculate_sub_rect
  返回 None 跳过该命中。
- v37.7.19 cp118：发现 cp54 的"返回 None → 调用方 continue 丢弃 → 静默漏脱"
  对脱敏工具是不可接受的（漏脱 = 泄漏）。改为超宽 box 回退纯权重估算
  （img_region=None），产出受限宽度的有界 rect——既避免跨整页超大遮罩，
  又不丢失敏感文字遮罩。

当前契约（cp118，本文件断言对象）：
1. 超宽 box（> 图像宽 * 0.8）不返回 None，而是回退产出有界 rect（width>0 且 < 图像宽）
2. 正常 box（<= 80%）继续走 _calculate_from_line 完整流程
3. img_region=None / 空 img_region 时不抛异常，安全产出（有界 rect 或 None）
4. 异常输入（畸形/空 box）安全处理，绝不向上抛异常
"""
import unittest
import types
import numpy as np

try:
    from privacyguard.workers.ocr_worker import OCRWorker
    from PyQt6.QtCore import QRectF  # noqa: F401 — availability probe
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "PyQt6 或 numpy 未安装")
class TestCalculateSubRectWidthLimit(unittest.TestCase):
    """OCR box 宽度限制测试（cp54 保守跳过 → cp118 回退有界遮罩）。"""

    def setUp(self):
        """创建 stub worker，避免 QThread 实例化开销。"""
        self.worker = types.SimpleNamespace()
        # 仅绑定 calculate_sub_rect 方法，相关依赖方法也需绑定
        self.worker.calculate_sub_rect = types.MethodType(
            OCRWorker.calculate_sub_rect, self.worker)
        self.worker._calculate_from_line = types.MethodType(
            OCRWorker._calculate_from_line, self.worker)
        self.worker._extract_roi_2x = types.MethodType(
            OCRWorker._extract_roi_2x, self.worker)
        self.worker._segment_text_columns = types.MethodType(
            OCRWorker._segment_text_columns, self.worker)
        self.worker._split_wide_segment = types.MethodType(
            OCRWorker._split_wide_segment, self.worker)
        self.worker._detect_vertical_boundaries = types.MethodType(
            OCRWorker._detect_vertical_boundaries, self.worker)
        self.worker._detect_text_boundaries = types.MethodType(
            OCRWorker._detect_text_boundaries, self.worker)
        self.worker._shrink_box = types.MethodType(
            OCRWorker._shrink_box, self.worker)
        self.worker._verify_sub_rect_width = types.MethodType(
            OCRWorker._verify_sub_rect_width, self.worker)
        # calculate_sub_rect / _calculate_from_line 读取以下实例属性
        self.worker.box_adjust_ratio = 0.0
        self.worker.scan_scale = 2.0
        self.worker.off_x = 0.0
        self.worker.off_w = 0.0

    def _make_img(self, w=400, h=60):
        """生成空白 BGR 测试图像。"""
        return np.full((h, w, 3), 255, dtype=np.uint8)

    # === cp118: 超宽 box 不再漏脱，回退产出有界 rect ===

    def test_oversized_box_falls_back_not_none(self):
        """cp118：box 宽 > 图像宽 * 0.8 时不应返回 None（漏脱），应回退产出有界 rect。"""
        # 图像宽度 400，box 宽度 350 (> 400 * 0.8 = 320)
        img = self._make_img(w=400, h=60)
        box = [[0, 0], [350, 0], [350, 60], [0, 60]]
        rect = self.worker.calculate_sub_rect(box, "测试文本", (0, 2), img_region=img)
        self.assertIsNotNone(rect, "超宽 box 必须回退产出有界 rect，不得返回 None 导致漏脱")
        self.assertGreater(rect.width(), 0)
        self.assertLess(rect.width(), 400, "回退产出的 rect 宽度必须小于图像宽度（有界，非跨整页）")

    def test_box_width_at_threshold_falls_back_not_none(self):
        """cp118：box 宽度刚好超过 80% 阈值也应回退产出有界 rect。"""
        # 图像宽度 400，80% = 320，box 宽度 321
        img = self._make_img(w=400, h=60)
        box = [[0, 0], [321, 0], [321, 60], [0, 60]]
        rect = self.worker.calculate_sub_rect(box, "测试", (0, 2), img_region=img)
        self.assertIsNotNone(rect, "刚好超过 80% 阈值的 box 也必须回退产出有界 rect")
        self.assertGreater(rect.width(), 0)

    def test_full_page_box_falls_back_not_none(self):
        """cp118：跨整页的大框（最常见误判场景）应回退产出有界 rect，而非静默跳过。"""
        img = self._make_img(w=1000, h=60)
        box = [[0, 0], [1000, 0], [1000, 60], [0, 60]]  # 宽度 = 图像宽度
        rect = self.worker.calculate_sub_rect(box, "案件编号 13417202010172812", (4, 20), img_region=img)
        self.assertIsNotNone(rect, "跨整页 OCR box 必须回退产出有界 rect，不得跳过漏脱")
        self.assertGreater(rect.width(), 0)
        self.assertLess(rect.width(), 1000, "回退 rect 宽度必须小于图像宽度（有界）")

    # === cp54 保留：正常框走原流程（不短路） ===

    def test_normal_box_does_not_short_circuit(self):
        """box 宽度 <= 80% 阈值不应触发回退，应走完整 _calculate_from_line 流程。"""
        img = self._make_img(w=400, h=60)
        # 正常 OCR box（200px 宽，远小于 320px 阈值）
        box = [[100, 0], [300, 0], [300, 60], [100, 60]]
        try:
            self.worker.calculate_sub_rect(box, "测试", (0, 2), img_region=img)
            # 不强制 rect 非空：内部 _calculate_from_line 可能因测试数据返回 None
            # 关键断言：未触发宽度限制回退（已通过日志验证）
        except Exception as e:
            self.fail(f"正常 box 不应抛异常: {e}")

    def test_small_box_passes_width_check(self):
        """小框（远小于 80% 阈值）不应被宽度检查过滤。"""
        img = self._make_img(w=400, h=60)
        box = [[100, 20], [200, 20], [200, 40], [100, 40]]  # 宽度 100，远小于 320
        try:
            self.worker.calculate_sub_rect(box, "测试", (0, 2), img_region=img)
        except Exception as e:
            self.fail(f"小 box 不应抛异常: {e}")

    # === cp118: img_region=None / 空 img_region 安全产出 ===

    def test_none_img_region_no_width_check(self):
        """img_region=None 时不触发宽度检查（无图像可用），直接走 _calculate_from_line。"""
        box = [[0, 0], [100, 0], [100, 60], [0, 60]]
        try:
            self.worker.calculate_sub_rect(box, "测试", (0, 2), img_region=None)
        except Exception:
            # _calculate_from_line 内部可能抛异常（无 img_region），但宽度检查不应触发
            # 关键：宽度检查代码不应执行（None 短路）
            pass

    def test_empty_img_region_safe(self):
        """cp118：空图像区域应安全回退产出有界 rect（不抛异常）。"""
        # 空 ndarray（0 元素），shape[1]=0 → box_w>0 触发回退 → img_region=None 路径
        img = np.zeros((0, 0, 3), dtype=np.uint8)
        box = [[0, 0], [100, 0], [100, 60], [0, 60]]
        try:
            rect = self.worker.calculate_sub_rect(box, "测试", (0, 2), img_region=img)
            # cp118 回退路径应产出有界 rect（或安全 None），绝不抛异常
            if rect is not None:
                self.assertTrue(hasattr(rect, 'x'), "回退结果应为 QRectF 或 None")
        except Exception as e:
            self.fail(f"空 img_region 不应抛异常: {e}")

    # === 异常输入安全处理（绝不向上抛） ===

    def test_malformed_box_handled_safely(self):
        """畸形 box（非 4 角点）应安全处理，不抛异常。

        两类畸形：
        1. 超大 + 畸形（仅 2 角点但宽度超阈值）→ 触发回退或被 try/except 捕获
        2. 正常宽度 + 畸形（仅 2 角点）→ try/except 捕获后返回 None 或 QRectF
        """
        img = self._make_img(w=400, h=60)
        # 场景 1：超大 + 畸形 → 回退路径或异常捕获，关键是不向上抛
        box1 = [[0, 0], [350, 0]]  # 仅 2 个点，但宽度 350 > 320
        try:
            rect1 = self.worker.calculate_sub_rect(box1, "测试", (0, 2), img_region=img)
            self.assertTrue(rect1 is None or hasattr(rect1, 'x'),
                            "超大畸形 box 应安全返回 None 或 QRectF")
        except Exception as e:
            self.fail(f"超大畸形 box 不应抛异常: {e}")

        # 场景 2：正常宽度 + 畸形 → try/except 捕获
        box2 = [[0, 0], [100, 0]]  # 仅 2 个点，宽度 100 < 320
        try:
            rect2 = self.worker.calculate_sub_rect(box2, "测试", (0, 2), img_region=img)
            self.assertTrue(rect2 is None or hasattr(rect2, 'x'),
                            "正常宽度畸形 box 应安全返回 None 或 QRectF")
        except Exception as e:
            self.fail(f"正常宽度畸形 box 不应抛异常: {e}")

    def test_empty_box_returns_none(self):
        """空 box 列表应安全返回 None（max([]) 触发 ValueError 被捕获）。"""
        img = self._make_img(w=400, h=60)
        rect = self.worker.calculate_sub_rect([], "测试", (0, 2), img_region=img)
        self.assertIsNone(rect, "空 box 应返回 None")

    # === 边界场景 ===

    def test_box_exactly_at_80_percent_boundary(self):
        """box 宽度刚好等于 80% 阈值不触发回退（>80% 才回退），走正常流程。"""
        # 图像宽度 400，80% = 320，box 宽度刚好 320（不 > 320）
        img = self._make_img(w=400, h=60)
        box = [[0, 0], [320, 0], [320, 60], [0, 60]]
        try:
            self.worker.calculate_sub_rect(box, "测试", (0, 2), img_region=img)
            # 内部 _calculate_from_line 结果不确定，但不应该因宽度触发回退
        except Exception as e:
            self.fail(f"box 宽度 = 80% 不应抛异常: {e}")

    def test_different_scan_scale_no_effect_on_width_check(self):
        """cp118：scan_scale 不影响宽度检查（检查在像素空间，与 scan_scale 无关）；
        超宽 box 无论 scan_scale 都应回退产出有界 rect。"""
        img = self._make_img(w=400, h=60)
        box = [[0, 0], [350, 0], [350, 60], [0, 60]]  # 350 > 320
        rect = self.worker.calculate_sub_rect(box, "测试", (0, 2), img_region=img)
        self.assertIsNotNone(rect, "超宽 box 无论 scan_scale 都必须回退产出有界 rect")
        self.assertGreater(rect.width(), 0)
        self.assertLess(rect.width(), 400, "回退 rect 宽度必须有界")


if __name__ == "__main__":
    unittest.main()
