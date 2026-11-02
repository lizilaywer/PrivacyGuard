"""cp62 回归测试：签名手印检测（_detect_signatures）

覆盖：
1. 红/粉手印合成用例（实心粉色椭圆 + 潦草笔画）应检出
2. 黑色手印（复印件）：脊线纹理合成用例应检出（阈值170 + 大核 + holes门控）
3. 防误报：灰色手写字（笔画不闭合，holes≈0）、纯文字行、实心黑块、空白页不应检出
4. 真实 PDF 端到端（王珍民事：黑手印；文件存在时执行）
"""
import os
import types
import unittest
import numpy as np

try:
    import cv2
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

# 真实黑手印样本（用户案卷，存在时跑端到端）
_WZ_PDF = r"c:\Users\49144\Desktop\2024-09-14王珍-非法经营-法院审理(一审)-——-——\1诉讼文书及证据材料\提取自王珍民事2024-11-25 10.26.pdf"


def make_pink_fingerprint(size=300, center=(150, 150), rx=45, ry=55):
    """粉色实心手印（红路径目标）：低饱和粉 + 深色笔画叠加。"""
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    cv2.ellipse(img, center, (rx, ry), 0, 0, 360, (200, 180, 245), -1)  # 粉(BGR)
    cv2.line(img, (center[0] - 40, center[1]), (center[0] + 40, center[1] - 10), (60, 60, 60), 3)
    return img


def make_gray_ridge_fingerprint(size=300, center=(150, 150), r=58):
    """偏红脊线手印（黑路径目标）：同心弧脊线，淡红印泥色（BGR红>蓝）。

    cp69: 真手印印泥即使偏淡也偏暖（R>B），用 (110,110,175) 体现 R-B≈65；
    脊线间距 5px、线宽 2px → 约 11 个同心环 → 封闭孔 ≥ 12（过 holes≥12 门控）。
    """
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    for rr in range(6, r, 5):
        cv2.ellipse(img, center, (rr, int(rr * 1.1)), 0, 0, 360, (110, 110, 175), 2)  # 淡红印泥(BGR)
    return img


def make_black_print_char(size=300):
    """cp69: 中性黑色印刷字（防误报）：笔画密集的“回字型”方块，

    模拟楷体/仿宋密集笔画字（警/醒/嫌等）：多层嵌套矩形能凑出多个封闭孔，
    但颜色是中性灰/黑（R≈G≈B），应被暖色门控排除。
    """
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    color = (90, 90, 90)  # 中性灰黑(BGR)，R-B=0
    for i, off in enumerate(range(0, 40, 8)):
        cv2.rectangle(img, (110 + off, 110 + off), (190 - off, 190 - off), color, 2)
    cv2.line(img, (110, 150), (190, 150), color, 2)
    cv2.line(img, (150, 110), (150, 190), color, 2)
    return img


def make_gray_handwriting(size=300):
    """灰色手写字（防误报）：几笔开放笔画，无封闭孔。"""
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    cv2.line(img, (100, 120), (200, 130), (150, 150, 150), 4)
    cv2.line(img, (120, 100), (140, 190), (150, 150, 150), 4)
    cv2.line(img, (170, 95), (160, 185), (150, 150, 150), 4)
    return img


def make_solid_black_block(size=300):
    """实心黑块（防误报，如已有遮罩）。"""
    img = np.full((size, size, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (200, 200), (0, 0, 0), -1)
    return img


@unittest.skipUnless(HAS_DEPS, "PyQt6 或 cv2 未安装")
class TestSignatureDetection(unittest.TestCase):
    def setUp(self):
        self.worker = types.SimpleNamespace()
        self.worker._detect_signatures = types.MethodType(
            OCRWorker._detect_signatures, self.worker)

    def test_pink_fingerprint_detected(self):
        """粉色实心手印应被红路径检出。"""
        rects = self.worker._detect_signatures(make_pink_fingerprint(), 1.5)
        self.assertGreaterEqual(len(rects), 1, "粉色手印应被检出")

    def test_gray_ridge_fingerprint_detected(self):
        """cp62/cp69: 偏红脊线手印（复印件）应被黑路径检出（holes≥12 + 暖色门控）。"""
        rects = self.worker._detect_signatures(make_gray_ridge_fingerprint(), 1.5)
        self.assertGreaterEqual(len(rects), 1, "偏红脊线手印应被检出")

    def test_black_print_char_not_detected(self):
        """cp69: 中性黑色印刷字（笔画密集但 R≈B）不应被暖色门控放过。"""
        rects = self.worker._detect_signatures(make_black_print_char(), 1.5)
        self.assertEqual(len(rects), 0, "中性黑色印刷字不应误报（非暖色）")

    def test_gray_handwriting_not_detected(self):
        """cp62: 灰色手写字（笔画不闭合 holes≈0）不应被黑路径误报。"""
        rects = self.worker._detect_signatures(make_gray_handwriting(), 1.5)
        self.assertEqual(len(rects), 0, "灰色手写字不应误报")

    def test_solid_black_block_not_detected(self):
        """实心黑块（密度≈1）不应被误报。"""
        rects = self.worker._detect_signatures(make_solid_black_block(), 1.5)
        self.assertEqual(len(rects), 0, "实心黑块不应误报")

    def test_blank_page_not_detected(self):
        """空白页不应有任何检出。"""
        blank = np.full((300, 300, 3), 255, dtype=np.uint8)
        rects = self.worker._detect_signatures(blank, 1.5)
        self.assertEqual(len(rects), 0)

    @unittest.skipUnless(HAS_FITZ and os.path.exists(_WZ_PDF),
                         "王珍样本 PDF 不存在或 fitz 未安装")
    def test_real_pdf_black_fingerprint_detected(self):
        """cp62: 真实复印件黑手印（王珍民事）端到端应检出且位置正确。"""
        doc = fitz.open(_WZ_PDF)
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)
        doc.close()
        rects = self.worker._detect_signatures(img, scan_scale=1.5)
        self.assertGreaterEqual(len(rects), 1, "真实黑手印应被检出")
        # 手印在页面右中下部（实测 pdf≈(376,494)，容差±60pt）
        hit = any(abs(r.x() - 376) < 60 and abs(r.y() - 494) < 60 for r in rects)
        self.assertTrue(hit, f"应命中真实手印位置，实际: "
                             f"{[(round(r.x()), round(r.y())) for r in rects]}")


if __name__ == "__main__":
    unittest.main()
