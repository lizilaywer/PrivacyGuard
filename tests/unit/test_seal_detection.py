"""v37.7.18 cp52: 印章检测多特征融合算法单元测试

验证 _detect_seals 的检测准确性和误判排除能力：
- 红色/蓝色印章应被检测到
- 空白区域不应被误检
- 红色方块/长条不应被误检
- 五角星检测准确性

v52 新增测试：
- 坐标补偿（page_origin）：v52 关键 bug 修复
- 淡色印章检测（盖在文字上方/扫描褪色）
- 椭圆变形印章检测（扫描变形）
- 遮罩扩大覆盖（v52 expand 5% 替代旧版 shrink）
"""
import unittest
import types
import os
import numpy as np
import cv2

try:
    from privacyguard.workers.ocr_worker import OCRWorker
    from PyQt6.QtCore import QRectF  # noqa: F401 — availability probe
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

# 真实诉讼卷宗样本（每页都有公安局圆形公章，半径≈127pt，超旧 90pt 上限）
_REAL_PDF = os.path.join(os.path.dirname(__file__), "..", "..", "提取自诉讼文书卷三.pdf")


def make_star_points(center, outer_r, inner_r):
    """生成五角星顶点坐标（10 个点：5 外 + 5 内）"""
    points = []
    for i in range(10):
        angle = np.pi / 2 + i * np.pi / 5
        r = outer_r if i % 2 == 0 else inner_r
        points.append([int(center[0] + r * np.cos(angle)),
                       int(center[1] - r * np.sin(angle))])
    return np.array(points, dtype=np.int32)


def make_red_seal_image(size=300, radius=60, center=None):
    """生成红色圆形印章测试图（环形 + 五角星）"""
    if center is None:
        center = (size // 2, size // 2)
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    # 红色圆环（厚度 5 以抵抗形态学 OPEN 操作）
    cv2.circle(img, center, radius, (0, 0, 200), 5)
    # 内部五角星
    star_pts = make_star_points(center, outer_r=radius // 3, inner_r=radius // 7)
    cv2.fillPoly(img, [star_pts], (0, 0, 200))
    return img


def make_faded_red_seal_image(size=300, radius=60, center=None, fade=0.5):
    """生成淡色红章（模拟盖在文字上方的半透明印章）"""
    if center is None:
        center = (size // 2, size // 2)
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    # fade=0.5 表示颜色减半（半透明效果）
    red_val = int(200 * fade)
    cv2.circle(img, center, radius, (0, 0, red_val), 5)
    star_pts = make_star_points(center, outer_r=radius // 3, inner_r=radius // 7)
    cv2.fillPoly(img, [star_pts], (0, 0, red_val))
    return img


def make_oval_seal_image(size=300, radius_x=80, radius_y=50, center=None):
    """生成椭圆变形印章（模拟扫描变形的圆章）"""
    if center is None:
        center = (size // 2, size // 2)
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    # 椭圆环（不同 x/y 半径模拟变形）
    cv2.ellipse(img, center, (radius_x, radius_y), 0, 0, 360, (0, 0, 200), 5)
    # 五角星（也变形）
    star_pts = make_star_points(center, outer_r=min(radius_x, radius_y) // 3,
                                inner_r=min(radius_x, radius_y) // 7)
    cv2.fillPoly(img, [star_pts], (0, 0, 200))
    return img


def make_blue_seal_image(size=300, radius=60, center=None):
    """生成蓝色圆形印章测试图"""
    if center is None:
        center = (size // 2, size // 2)
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    cv2.circle(img, center, radius, (200, 0, 0), 5)  # BGR: 蓝色
    star_pts = make_star_points(center, outer_r=radius // 3, inner_r=radius // 7)
    cv2.fillPoly(img, [star_pts], (200, 0, 0))
    return img


def make_blank_image(size=300):
    """生成纯白空白图像"""
    return np.full((size, size, 3), 255, dtype=np.uint8)


def make_red_solid_square_image(size=300, side=120):
    """生成红色实心方块"""
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (size // 2 - side // 2, size // 2 - side // 2),
                   (size // 2 + side // 2, size // 2 + side // 2), (0, 0, 200), -1)
    return img


def make_red_hollow_square_image(size=300, side=120):
    """生成红色空心方块（仅边框）"""
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (size // 2 - side // 2, size // 2 - side // 2),
                   (size // 2 + side // 2, size // 2 + side // 2), (0, 0, 200), 5)
    return img


def make_red_rect_image(size=300, w=200, h=30):
    """生成红色长条"""
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (size // 2 - w // 2, size // 2 - h // 2),
                   (size // 2 + w // 2, size // 2 + h // 2), (0, 0, 200), -1)
    return img


def make_red_seal_over_text_image(size=300, radius=60, center=None):
    """生成盖在黑色文字上的红色印章（模拟“盖在复杂文字背景上”）。

    黑色文字不进入红/蓝颜色掩模，不应干扰印章检测。
    """
    if center is None:
        center = (size // 2, size // 2)
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    # 黑色文字噪声（横向多行）
    for ty in range(center[1] - 40, center[1] + 40, 12):
        cv2.putText(img, "text sample line", (center[0] - 70, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    # 红色印章（环形+五角星）盖在文字上
    cv2.circle(img, center, radius, (0, 0, 200), 5)
    star_pts = make_star_points(center, outer_r=radius // 3, inner_r=radius // 7)
    cv2.fillPoly(img, [star_pts], (0, 0, 200))
    return img


def make_seal_with_red_title_image(size=400, seal_center=None):
    """生成同页同时含红色标题长条 + 真实印章的图像。

    红色标题（aspect 极大）应被基础过滤排除，仅印章应被检测。
    """
    if seal_center is None:
        seal_center = (200, 260)
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    # 红色标题长条（顶部，aspect 约 12，应被排除）
    cv2.rectangle(img, (50, 30), (350, 55), (0, 0, 200), -1)
    # 真实印章（下方）
    cv2.circle(img, seal_center, 60, (0, 0, 200), 5)
    star_pts = make_star_points(seal_center, outer_r=20, inner_r=8)
    cv2.fillPoly(img, [star_pts], (0, 0, 200))
    return img


def make_large_ring_seal(size=560, radius=210, center=None):
    """大尺寸纯环印章（无五角星），半径超旧 90pt 上限。

    用于回归：cp59 提高 max_radius + 圆盘充实度信号，
    确保大公章不再因“过大”被误弃（真实诉讼卷宗的典型失效场景）。
    """
    if center is None:
        center = (size // 2, size // 2)
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    cv2.circle(img, center, radius, (0, 0, 200), 6)
    # 环形文字（小实心块模拟）
    tr = radius - 20
    for deg in range(0, 360, 20):
        a = np.deg2rad(deg)
        px = int(center[0] + tr * np.cos(a))
        py = int(center[1] - tr * np.sin(a))
        cv2.rectangle(img, (px - 5, py - 6), (px + 5, py + 6), (0, 0, 200), -1)
    return img


def make_broken_ring_seal(size=520, radius=170, center=None, seg_deg=14, gap_deg=4):
    """断环大印章（墨迹不均，外环多处小缺口）+ 五角星。

    模拟真实银行章：外环由多段短弧组成，段间留小缺口（单缺口远小于大核）。
    小核 CLOSE=3 无法桥接→pass1 漏检；大核 pass2 桥接后检出。
    """
    if center is None:
        center = (size // 2, size // 2)
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    for start in range(0, 360, seg_deg):
        cv2.ellipse(img, center, (radius, radius), 0,
                    start, start + seg_deg - gap_deg, (0, 0, 200), 6)
    star = make_star_points(center, radius // 3, radius // 7)
    cv2.fillPoly(img, [star], (0, 0, 200))
    return img


def make_synthetic_seal_pdf():
    """内存合成印章样本 PDF（不含任何真实个人信息，不落盘）。

    复现真实诉讼卷宗的检测语义：每页 ≥1 章，且至少两页 ≥2 章（含断环章）。
    图像按 px/2 = pt 嵌入，配合 Matrix(2,2) 渲染 + scan_scale=2.0，
    使检测器看到的像素与图像级回归的已验证参数一致：
    大环章 r=210px→98.4pt、断环章 r=170px→83.3pt、带星红章 r=60px→29.4pt，
    均在 min/max_radius_pt (12/150) 检测区间内。
    """
    def _png_bytes(img):
        ok, buf = cv2.imencode(".png", img)
        assert ok
        return buf.tobytes()

    doc = fitz.open()
    # 页 1：单枚大环公章（半径超旧 90pt 上限的典型失效场景）
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(40, 60, 320, 340),
                      stream=_png_bytes(make_large_ring_seal(size=560, radius=210)))
    # 页 2：断环银行章 + 带五角星红章（双印章页）
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(40, 60, 300, 320),
                      stream=_png_bytes(make_broken_ring_seal(size=520, radius=170)))
    page.insert_image(fitz.Rect(360, 480, 510, 630),
                      stream=_png_bytes(make_red_seal_image(size=300, radius=60)))
    # 页 3：大环章 + 断环章（第二个双印章页，锁定断环修复）
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(40, 40, 320, 320),
                      stream=_png_bytes(make_large_ring_seal(size=560, radius=210)))
    page.insert_image(fitz.Rect(330, 500, 590, 760),
                      stream=_png_bytes(make_broken_ring_seal(size=520, radius=170)))
    return doc


@unittest.skipUnless(HAS_DEPS, "PyQt6 或 cv2 未安装")
class TestSealDetection(unittest.TestCase):
    """v37.7.18 cp52: 印章检测多特征融合算法测试"""

    def setUp(self):
        """创建 stub worker（避免 QThread 实例化开销）"""
        self.worker = types.SimpleNamespace()
        self.worker._detect_star_in_roi = types.MethodType(
            OCRWorker._detect_star_in_roi, self.worker)
        self.worker._ocr_seal_region = types.MethodType(
            OCRWorker._ocr_seal_region, self.worker)
        self.worker._detect_seals = types.MethodType(
            OCRWorker._detect_seals, self.worker)
        # v53: 绑定整块覆盖回调工厂方法
        self.worker._make_block_failure_fn = types.MethodType(
            OCRWorker._make_block_failure_fn, self.worker)

    # === 正向检测 ===

    def test_red_seal_with_star_detected(self):
        """红色印章（环形+五角星）应被检测到。"""
        img = make_red_seal_image(radius=60)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "红色印章（含五角星）应被检测到")

    def test_blue_seal_with_star_detected(self):
        """蓝色印章应被检测到（旧版完全缺失蓝色检测）。"""
        img = make_blue_seal_image(radius=60)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "蓝色印章应被检测到")

    def test_red_seal_no_star_high_circularity_detected(self):
        """无五角星的纯环印章，在高圆形度下应被检测到。"""
        img = np.full((300, 300, 3), 255, dtype=np.uint8)
        cv2.circle(img, (150, 150), 60, (0, 0, 200), 5)  # 仅圆环，无星
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        # v52 评分：circularity>0.7(+1) + circularity>0.85(+1) + aspect_ratio(+1) = 3 ✓
        self.assertGreater(len(rects), 0, "高圆形度纯环印章应被检测到")

    # === v52 新增：淡色印章 ===

    def test_faded_red_seal_detected(self):
        """淡色红章（模拟半透明/扫描褪色）应被检测到。

        v52 核心场景：印章盖在文字上方时颜色偏淡，
        旧版 S/V≥80 阈值会漏检，v52 降到 40。
        """
        img = make_faded_red_seal_image(radius=60, fade=0.4)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "淡色红章应被检测到（v52 放宽 HSV 阈值）")

    def test_faded_red_seal_mild_fade_detected(self):
        """轻度淡色红章（fade=0.6）应被检测到。"""
        img = make_faded_red_seal_image(radius=60, fade=0.6)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "轻度淡色红章应被检测到")

    # === v52 新增：椭圆变形印章 ===

    def test_oval_seal_detected(self):
        """椭圆变形印章应被检测到。

        v52 核心场景：扫描变形导致圆形变椭圆，
        旧版 aspect_ratio [0.7,1.4] 过严，v52 放宽到 [0.5,2.0]。
        """
        img = make_oval_seal_image(radius_x=80, radius_y=55)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "椭圆变形印章应被检测到")

    def test_oval_seal_extreme_deformation_detected(self):
        """严重变形椭圆印章应被检测到（aspect_ratio 1.6）。"""
        img = make_oval_seal_image(radius_x=80, radius_y=50)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "严重椭圆变形印章应被检测到")

    # === 误判排除 ===

    def test_blank_image_not_detected(self):
        """纯白空白图像不应检测到任何印章（核心 bug：旧版误判大量空白）。"""
        img = make_blank_image()
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertEqual(len(rects), 0, "空白图像不应误检为印章")

    def test_red_solid_square_not_detected(self):
        """红色实心方块不应被检测为印章（color_ratio > 0.7 被基础过滤排除）。"""
        img = make_red_solid_square_image(side=120)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertEqual(len(rects), 0, "红色实心方块不应误检为印章")

    def test_red_hollow_square_not_detected(self):
        """红色空心方块不应被检测为印章（circularity 不足且无验证信号）。"""
        img = make_red_hollow_square_image(side=120)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        # 方块 circularity ≈ π/4 ≈ 0.785
        # v52 评分：circularity>0.7(+1) + aspect_ratio(+1) = 2 < 3 → 排除
        self.assertEqual(len(rects), 0, "红色空心方块不应误检为印章")

    def test_red_rect_not_detected(self):
        """红色长条不应被检测为印章（aspect ratio > 2.0 被基础过滤排除）。"""
        img = make_red_rect_image(w=200, h=30)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertEqual(len(rects), 0, "红色长条不应误检为印章")

    def test_small_red_circle_not_detected(self):
        """过小的红色圆不应被检测为印章（面积不足）。"""
        img = np.full((300, 300, 3), 255, dtype=np.uint8)
        cv2.circle(img, (150, 150), 10, (0, 0, 200), 3)  # 半径仅 10px
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertEqual(len(rects), 0, "过小红色圆不应误检为印章")

    # === 五角星检测 ===

    def test_star_detected_in_mask(self):
        """五角星图案应被 _detect_star_in_roi 检测到。"""
        size = 120
        mask = np.zeros((size, size), dtype=np.uint8)
        star_pts = make_star_points((60, 60), outer_r=35, inner_r=14)
        cv2.fillPoly(mask, [star_pts], 255)
        result = self.worker._detect_star_in_roi(mask)
        self.assertTrue(result, "五角星应被检测到")

    def test_circle_not_star(self):
        """实心圆形不应被误判为五角星。"""
        size = 120
        mask = np.zeros((size, size), dtype=np.uint8)
        cv2.circle(mask, (60, 60), 40, 255, -1)  # 实心圆
        result = self.worker._detect_star_in_roi(mask)
        self.assertFalse(result, "圆形不应被误判为五角星")

    def test_square_not_star(self):
        """方形不应被误判为五角星。"""
        size = 120
        mask = np.zeros((size, size), dtype=np.uint8)
        cv2.rectangle(mask, (20, 20), (100, 100), 255, -1)
        result = self.worker._detect_star_in_roi(mask)
        self.assertFalse(result, "方形不应被误判为五角星")

    # === 遮罩位置准确性 ===

    def test_seal_mask_within_image_bounds(self):
        """印章遮罩位置应在合理范围内。"""
        img = make_red_seal_image(size=300, radius=60, center=(150, 150))
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "应检测到印章")
        r = rects[0]
        # 遮罩应在 PDF 坐标系内（300px / 2.0 = 150pt）
        self.assertGreater(r.x(), 0, "遮罩 x 应 > 0")
        self.assertGreater(r.y(), 0, "遮罩 y 应 > 0")
        self.assertLess(r.x() + r.width(), 150, "遮罩右边界应 < 150pt")
        self.assertLess(r.y() + r.height(), 150, "遮罩下边界应 < 150pt")
        # 印章直径 120px / 2.0 = 60pt，遮罩宽度应接近此值
        self.assertGreater(r.width(), 30, "遮罩宽度应 > 30pt")
        self.assertGreater(r.height(), 30, "遮罩高度应 > 30pt")

    def test_seal_mask_size_reasonable(self):
        """印章遮罩大小不应远超实际印章尺寸。"""
        img = make_red_seal_image(size=300, radius=60, center=(150, 150))
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0)
        r = rects[0]
        # 印章直径 120px → 60pt，v52 扩大 5% 后约 63pt，不应超过 80pt
        self.assertLess(r.width(), 80, "遮罩宽度不应远超印章直径")
        self.assertLess(r.height(), 80, "遮罩高度不应远超印章直径")

    # === v52 新增：坐标补偿 ===

    def test_page_origin_offset_compensated(self):
        """v52 关键修复：page_origin 偏移应被正确补偿。

        模拟 PDF MediaBox 偏移 (50, 50) 的场景：
        - 印章在图像 (150, 150) 像素位置（scan_scale=2.0）
        - 旧版：pdf_x = 150/2 = 75（错误，未加 origin）
        - v52：pdf_x = 150/2 + 50 = 125（正确）
        """
        img = make_red_seal_image(size=300, radius=60, center=(150, 150))
        # 不带 origin
        rects_no_origin = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        # 带 origin (50, 50)
        rects_with_origin = self.worker._detect_seals(
            img, scan_scale=2.0, ocr_engine=None, page_origin=(50.0, 50.0)
        )
        self.assertEqual(len(rects_no_origin), len(rects_with_origin),
                         "page_origin 不应影响检测数量")
        if rects_no_origin and rects_with_origin:
            r1 = rects_no_origin[0]
            r2 = rects_with_origin[0]
            # 坐标应恰好相差 (50, 50)
            self.assertAlmostEqual(r2.x() - r1.x(), 50.0, places=1,
                                   msg="page_origin.x 应被补偿到遮罩 x 坐标")
            self.assertAlmostEqual(r2.y() - r1.y(), 50.0, places=1,
                                   msg="page_origin.y 应被补偿到遮罩 y 坐标")
            # 宽高不应受影响
            self.assertAlmostEqual(r2.width(), r1.width(), places=1,
                                   msg="page_origin 不应影响遮罩宽度")
            self.assertAlmostEqual(r2.height(), r1.height(), places=1,
                                   msg="page_origin 不应影响遮罩高度")

    def test_page_origin_zero_default(self):
        """page_origin 默认值 (0,0) 时行为应与不传一致。"""
        img = make_red_seal_image(radius=60)
        r1 = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        r2 = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None,
                                       page_origin=(0.0, 0.0))
        self.assertEqual(len(r1), len(r2), "默认 origin 应与 (0,0) 一致")
        if r1 and r2:
            self.assertAlmostEqual(r1[0].x(), r2[0].x(), places=2)

    # === v52 新增：遮罩扩大覆盖 ===

    def test_mask_expanded_to_cover_edges(self):
        """v52 修复：遮罩应扩大 5% 覆盖印章边缘，旧版 shrink 反而让遮罩更小。

        验证：v52 遮罩宽度应 >= boundingRect 宽度（不收缩）。
        """
        img = make_red_seal_image(size=300, radius=60, center=(150, 150))
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0)
        r = rects[0]
        # 印章 boundingRect 约 120x120px，扫描后 120px / 2.0 = 60pt
        # v52 扩大 5% 后约 63pt，旧版 shrink 5% 后约 57pt
        # 这里验证遮罩宽度 >= 55pt（排除旧版 shrink 行为）
        self.assertGreaterEqual(r.width(), 55,
                                "v52 遮罩应扩大覆盖，不应收缩")

    # === v53 新增：红色文字行不应误判 ===

    def test_red_text_line_not_detected(self):
        """v53 关键修复：红色文字行不应被误判为印章。

        场景：扫描页红色标题"人民法院判决书"
        旧版问题：OCR 识别出"院"字命中单字关键词 → +3 分 → 误判
        v53 修复：去除单字关键词，且 OCR 关键词命中时要求 circularity > 0.5
        """
        # 模拟红色文字行（长条形，circularity 低）
        img = np.full((300, 300, 3), 255, dtype=np.uint8)
        # 红色文字模拟（横向排列的红色像素块，长宽比大，circularity 低）
        cv2.rectangle(img, (50, 140), (250, 160), (0, 0, 200), -1)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        # 长条 aspect_ratio = 200/20 = 10 > 2.0，被基础过滤排除
        self.assertEqual(len(rects), 0, "红色文字行不应误判为印章")

    def test_red_title_block_not_detected_without_circle(self):
        """v53: 红色标题块（非圆形）即使 OCR 能识别出文字也不应误判。"""
        # 模拟红色标题块（接近正方形但 circularity 低）
        img = np.full((300, 300, 3), 255, dtype=np.uint8)
        # 红色实心矩形 80x40（aspect_ratio=2.0 边界）
        cv2.rectangle(img, (110, 130), (190, 170), (0, 0, 200), -1)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        # aspect_ratio = 80/40 = 2.0，刚好在边界
        # color_ratio 会很高（实心），被基础过滤排除
        self.assertEqual(len(rects), 0, "红色标题块不应误判为印章")

    # === v53 新增：整块覆盖面积限制 ===

    def test_block_failure_fn_limits_large_coverage(self):
        """v53 关键修复：整块覆盖回调应限制大面积覆盖。

        场景：扫描件整页作为 clip_rect，OCR 失败时
        旧版：生成覆盖整页的大矩形 → "一大块"遮罩
        v53：超过页面面积 30% 时不覆盖
        """
        # 模拟 fitz.Page rect
        class FakeRect:
            x0, y0, x1, y1 = 0, 0, 595, 842  # A4 页面大小

        fn = self.worker._make_block_failure_fn(FakeRect())

        # 小块（10% 页面面积）→ 应覆盖
        small_clip = (0, 0, 187, 268)  # 约 31% 面积，边界测试
        result = fn(small_clip)
        # 187*268 / (595*842) = 50116 / 500990 ≈ 10%
        # 改用更小的值确保 < 30%
        small_clip = (0, 0, 100, 100)  # 10000 / 500990 ≈ 2%
        result = fn(small_clip)
        self.assertIsNotNone(result, "小面积图片块应正常覆盖")

        # 整页（100% 页面面积）→ 不应覆盖
        full_page = (0, 0, 595, 842)
        from privacyguard.utils.exceptions import OCRInspectionError
        with self.assertRaises(OCRInspectionError):
            fn(full_page)

        # 超过 30% 页面面积 → 不应覆盖
        large_clip = (0, 0, 400, 400)  # 160000 / 500990 ≈ 32%
        with self.assertRaises(OCRInspectionError):
            fn(large_clip)

    def test_block_failure_fn_small_block_covered(self):
        """v53: 小面积图片块失败时应正常覆盖（保留原保守脱敏逻辑）。"""
        class FakeRect:
            x0, y0, x1, y1 = 0, 0, 595, 842

        fn = self.worker._make_block_failure_fn(FakeRect())
        # 小图片块（如嵌入图片 50x60pt）
        small_clip = (100, 200, 150, 260)
        result = fn(small_clip)
        self.assertIsNotNone(result, "小面积图片块应正常覆盖")
        self.assertEqual(result.x(), 100)
        self.assertEqual(result.y(), 200)
        self.assertEqual(result.width(), 50)
        self.assertEqual(result.height(), 60)

    # === OCR 文字验证 ===

    def test_ocr_none_returns_empty(self):
        """ocr_engine=None 时 _ocr_seal_region 应返回空字符串。"""
        img = np.full((60, 60, 3), 200, dtype=np.uint8)
        result = self.worker._ocr_seal_region(img, None)
        self.assertEqual(result, "", "无 OCR 引擎时应返回空字符串")

    # === 复杂背景：盖在文字上 / 与红色标题共存 ===

    def test_red_seal_over_black_text_detected(self):
        """盖在黑色文字背景上的红色印章仍应被检测到（黑字不入颜色掩模）。"""
        img = make_red_seal_over_text_image(radius=60)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "盖在文字背景上的印章应被检测到")

    def test_seal_coexists_with_red_title_only_seal_detected(self):
        """同页共存红色标题长条与真实印章时，标题不应误判。"""
        img = make_seal_with_red_title_image()
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        # 标题 aspect 约 12 > 2.0 被基础过滤；印章应被检测
        self.assertEqual(len(rects), 1, "应仅检测到印章，红色标题不应误判")

    def test_very_faint_seal_detected(self):
        """极淡红章（fade=0.3）仍应被检测到（红通道饱和度保持，V 仍≥阈值）。"""
        img = make_faded_red_seal_image(radius=60, fade=0.3)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "极淡红章（fade=0.3）应被检测到")

    # === cp59: 大尺寸公章（真实诉讼卷宗失效场景）===

    def test_large_seal_over_size_cap_detected(self):
        """cp59: 半径超旧 90pt 上限的大公章应被检测到（旧版因 max_area 误弃）。"""
        # size 560, radius 210, scan_scale=2.0 → r_pt=105 > 90（旧上限）
        img = make_large_ring_seal(size=560, radius=210)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "半径超 90pt 的大公章应被检测到")

    def test_broken_ring_seal_detected(self):
        """cp59: 断环大印章（墨迹不均，外环多缺口）应由双通道大核桥接后检出。"""
        img = make_broken_ring_seal(size=520, radius=170, seg_deg=14, gap_deg=4)
        rects = self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)
        self.assertGreater(len(rects), 0, "断环大印章（如银行章）应被检测到")

    @unittest.skipUnless(HAS_FITZ, "fitz 未安装")
    def test_synthetic_pdf_seals_detected(self):
        """合成样本 PDF 端到端：每页均应检到公章，双印章页应检出 2 个。

        不依赖仓库外真实样本，任何机器均可复现；断言语义与
        test_real_pdf_seals_detected 一致（锁定 cp59 大章/断环章修复）。
        """
        doc = make_synthetic_seal_pdf()
        counts = []
        for i in range(len(doc)):
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)
            counts.append(len(self.worker._detect_seals(img, scan_scale=2.0, ocr_engine=None)))
        doc.close()
        self.assertTrue(all(c >= 1 for c in counts),
                        f"合成样本每页均应检到公章，实际每页={counts}")
        self.assertGreaterEqual(sum(1 for c in counts if c >= 2), 2,
                                f"至少两页应检出双印章（含断环章），实际每页={counts}")

    @unittest.skipUnless(HAS_FITZ and os.path.exists(_REAL_PDF),
                         "真实样本 PDF 不存在或 fitz 未安装")
    def test_real_pdf_seals_detected(self):
        """cp59: 真实诉讼卷宗每页公章应被检测到；含银行章的页应检出 2 个。"""
        doc = fitz.open(_REAL_PDF)
        counts = []
        for i in range(len(doc)):
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)
            counts.append(len(self.worker._detect_seals(img, scan_scale=1.5, ocr_engine=None)))
        doc.close()
        # 每页至少 1 个印章
        self.assertTrue(all(c >= 1 for c in counts),
                        f"每页均应检到公章，实际每页={counts}")
        # 至少有两页含双印章（银行章/厂监章 + 公安局章），锁定断环银行章修复
        self.assertGreaterEqual(sum(1 for c in counts if c >= 2), 2,
                                f"至少两页应检出双印章（含断环银行章），实际每页={counts}")


if __name__ == "__main__":
    unittest.main()
