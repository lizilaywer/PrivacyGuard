# -*- coding: utf-8 -*-
"""cp122 回归测试：提取 / 截去 纵向区域裁剪纯函数。

验证要点：
1. extract_vertical_region_to_page：提取区域为新页，尺寸正确，文字保留（矢量）
2. crop_vertical_region_from_page：截去后页数不变，高度缩短，上下拼接，文字保留
3. 旋转页（90°/180°）坐标经 derotation_matrix 转换后裁剪正确
4. 边界：高度 < 1pt 拒绝、越界钳制

注：测试用英文文字，避免 PyMuPDF 默认字体（bas14）不支持中文导致的渲染问题
（实际应用中文字由完整 PDF 提供，字体齐全）。
"""
import unittest

from privacyguard.utils.helpers_pdf import (
    extract_vertical_region_to_page,
    crop_vertical_region_from_page,
    build_result_doc_from_segments,
    build_extract_report,
)

try:
    import fitz  # noqa: F401
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


@unittest.skipUnless(HAS_FITZ, "PyMuPDF 未安装")
class TestExtractVerticalRegion(unittest.TestCase):
    """提取：把源页纵向区域提取为结果文档的新页。"""

    def _make_src_doc(self, w=200, h=400):
        """构造测试 PDF：上部 'TOPPART' @y=50、下部 'BOTPART' @y=350。"""
        doc = fitz.open()
        page = doc.new_page(width=w, height=h)
        page.insert_text((50, 50), "TOPPART", fontsize=20)
        page.insert_text((50, 350), "BOTPART", fontsize=20)
        return doc

    def test_extract_creates_new_page_with_correct_size(self):
        """提取区域 → 结果文档新增 1 页，尺寸 = 原宽 × 区域高。"""
        src = self._make_src_doc()  # 200×400
        result = fitz.open()
        idx = extract_vertical_region_to_page(result, src, 0, 0, 200)
        self.assertEqual(len(result), 1)
        self.assertEqual(idx, 0)
        new_page = result[0]
        self.assertAlmostEqual(new_page.rect.width, 200)
        self.assertAlmostEqual(new_page.rect.height, 200)

    def test_extract_preserves_text_vector(self):
        """提取区域文字保留为矢量（get_text 非空）。"""
        src = self._make_src_doc()
        result = fitz.open()
        # TOPPART 的 span bbox 约 (50, 28.5, ~140, 56)，提取 0~100 覆盖它
        extract_vertical_region_to_page(result, src, 0, 0, 100)
        text = result[0].get_text()
        self.assertIn("TOPPART", text)  # 矢量文字保留

    def test_extract_multiple_accumulate(self):
        """多次提取累积到同一结果文档（页数递增，各自文字保留）。"""
        src = self._make_src_doc()
        result = fitz.open()
        extract_vertical_region_to_page(result, src, 0, 0, 100)   # 含 TOPPART
        extract_vertical_region_to_page(result, src, 0, 300, 400)  # 含 BOTPART
        self.assertEqual(len(result), 2)
        self.assertIn("TOPPART", result[0].get_text())
        self.assertIn("BOTPART", result[1].get_text())

    def test_extract_too_small_raises(self):
        """提取高度 < 1pt 拒绝。"""
        src = self._make_src_doc()
        result = fitz.open()
        with self.assertRaises(ValueError):
            extract_vertical_region_to_page(result, src, 0, 50, 50.5)

    def test_extract_clamps_to_page_bounds(self):
        """y 越界时钳制到页面范围（不报错，高度按钳制后算）。"""
        src = self._make_src_doc(h=400)
        result = fitz.open()
        extract_vertical_region_to_page(result, src, 0, 300, 999)  # y_max 钳到 400
        self.assertAlmostEqual(result[0].rect.height, 100)  # 400-300


@unittest.skipUnless(HAS_FITZ, "PyMuPDF 未安装")
class TestCropVerticalRegion(unittest.TestCase):
    """截去：从当前页挖掉纵向区域，上下拼接。"""

    def _make_doc(self, w=200, h=400):
        doc = fitz.open()
        page = doc.new_page(width=w, height=h)
        page.insert_text((50, 50), "TOPPART", fontsize=20)    # span 约 y=28~56
        page.insert_text((50, 200), "MIDPART", fontsize=20)   # span 约 y=178~206
        page.insert_text((50, 350), "BOTPART", fontsize=20)   # span 约 y=328~356
        return doc

    def test_crop_reduces_height_keeps_page_count(self):
        """截去中间区域 → 页数不变，高度 = 原高 - 截去高。"""
        doc = self._make_doc()  # 400 高
        self.assertEqual(len(doc), 1)
        new_h = crop_vertical_region_from_page(doc, 0, 150, 250)
        self.assertEqual(len(doc), 1)  # 页数不变
        self.assertAlmostEqual(new_h, 300)  # 400 - 100
        self.assertAlmostEqual(doc[0].rect.height, 300)

    def test_crop_preserves_top_and_bottom_text(self):
        """截去中部后，上部和下部文字保留，中部文字被挖掉。"""
        doc = self._make_doc()
        # MIDPART span 约 y=178~206，截去 150~250 覆盖它
        crop_vertical_region_from_page(doc, 0, 150, 250)
        text = doc[0].get_text()
        self.assertIn("TOPPART", text)
        self.assertIn("BOTPART", text)
        self.assertNotIn("MIDPART", text)

    def test_crop_all_raises(self):
        """截去整个页面（剩余高度为 0）拒绝。"""
        doc = self._make_doc(h=400)
        with self.assertRaises(ValueError):
            crop_vertical_region_from_page(doc, 0, 0, 400)  # top=0, bottom=0

    def test_crop_only_top(self):
        """只截去顶部（y_min=0）→ 仅保留下半部分。"""
        doc = self._make_doc(h=400)
        new_h = crop_vertical_region_from_page(doc, 0, 0, 150)
        self.assertAlmostEqual(new_h, 250)
        text = doc[0].get_text()
        self.assertNotIn("TOPPART", text)   # 顶部被截去
        self.assertIn("BOTPART", text)      # 底部保留


@unittest.skipUnless(HAS_FITZ, "PyMuPDF 未安装")
class TestRotatedPageCoordinates(unittest.TestCase):
    """旋转页坐标：display 坐标经 derotation_matrix 转换后裁剪正确。"""

    def _make_rotated_doc(self, rotation=90):
        doc = fitz.open()
        page = doc.new_page(width=200, height=400)
        page.insert_text((50, 50), "TOPPART", fontsize=20)
        page.insert_text((50, 350), "BOTPART", fontsize=20)
        page.set_rotation(rotation)
        return doc

    def test_extract_rotated_90(self):
        """90° 旋转页提取上半部分不报错（坐标转换正确）。"""
        doc = self._make_rotated_doc(90)
        result = fitz.open()
        try:
            extract_vertical_region_to_page(result, doc, 0, 0, 200)
            self.assertEqual(len(result), 1)
        except Exception as e:
            self.fail(f"旋转页提取不应报错: {type(e).__name__}: {e}")

    def test_crop_rotated_180(self):
        """180° 旋转页截去中部不报错，高度缩短。"""
        doc = self._make_rotated_doc(180)
        new_h = crop_vertical_region_from_page(doc, 0, 150, 250)
        self.assertAlmostEqual(new_h, 300)
        self.assertEqual(len(doc), 1)


@unittest.skipUnless(HAS_FITZ, "PyMuPDF 未安装")
class TestBuildResultFromSegments(unittest.TestCase):
    """cp122-fix: 片段模型构建结果文档（同页多片段拼接 + 删除/移序重建）。"""

    def _make_src(self):
        """2 页源文档：P0 上部 TOPP/下部 BOTP；P1 上部 TOP1/下部 BOT1。"""
        doc = fitz.open()
        p0 = doc.new_page(width=200, height=400)
        p0.insert_text((50, 50), "TOPP", fontsize=20)
        p0.insert_text((50, 350), "BOTP", fontsize=20)
        p1 = doc.new_page(width=200, height=400)
        p1.insert_text((50, 50), "TOP1", fontsize=20)
        p1.insert_text((50, 350), "BOT1", fontsize=20)
        return doc

    def test_single_page_two_segments_concat(self):
        """同一结果页拼接 2 片段：高度=和，文字都在。"""
        src = self._make_src()
        segments = [[
            {"src_pno": 0, "y_min": 0, "y_max": 100},
            {"src_pno": 1, "y_min": 300, "y_max": 400},
        ]]
        result = build_result_doc_from_segments(src, segments)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0].rect.height, 200)  # 100+100
        text = result[0].get_text()
        self.assertIn("TOPP", text)
        self.assertIn("BOT1", text)

    def test_multiple_result_pages(self):
        """2 个结果页（各 1 片段）：结果文档 2 页。"""
        src = self._make_src()
        segments = [
            [{"src_pno": 0, "y_min": 0, "y_max": 100}],
            [{"src_pno": 1, "y_min": 0, "y_max": 100}],
        ]
        result = build_result_doc_from_segments(src, segments)
        self.assertEqual(len(result), 2)

    def test_delete_segment_rebuild(self):
        """删除中间片段后重建：页数/高度/文字正确。"""
        src = self._make_src()
        segments = [[
            {"src_pno": 0, "y_min": 0, "y_max": 100},
            {"src_pno": 1, "y_min": 300, "y_max": 400},
        ]]
        # 模拟删除第 1 片段（index 0）
        del segments[0][0]
        result = build_result_doc_from_segments(src, segments)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0].rect.height, 100)  # 只剩第2片
        self.assertIn("BOT1", result[0].get_text())
        self.assertNotIn("TOPP", result[0].get_text())

    def test_reorder_segments_rebuild(self):
        """片段顺序调换后重建：文字顺序跟随。"""
        src = self._make_src()
        seg_a = {"src_pno": 0, "y_min": 0, "y_max": 100}
        seg_b = {"src_pno": 1, "y_min": 300, "y_max": 400}
        # 原序 [a, b] → 调换 [b, a]
        segments = [[seg_b, seg_a]]
        result = build_result_doc_from_segments(src, segments)
        # 用 span y 坐标判断顺序：b(BOT1) 应在上半，a(TOPP) 在下半
        spans = []
        for b in result[0].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    spans.append((s["bbox"][1], s["text"]))
        spans.sort()
        self.assertEqual(len(spans), 2)
        self.assertIn("BOT1", spans[0][1])  # 上方是 BOT1（原 seg_b）
        self.assertIn("TOPP", spans[1][1])  # 下方是 TOPP（原 seg_a）

    def test_empty_segments_returns_empty_doc(self):
        """空片段列表 → 空文档。"""
        src = self._make_src()
        result = build_result_doc_from_segments(src, [])
        self.assertEqual(len(result), 0)

    def test_too_small_segment_raises(self):
        """片段高度 < 1pt 拒绝。"""
        src = self._make_src()
        segments = [[{"src_pno": 0, "y_min": 50, "y_max": 50.5}]]
        with self.assertRaises(ValueError):
            build_result_doc_from_segments(src, segments)


@unittest.skipUnless(HAS_FITZ, "PyMuPDF 未安装")
class TestBuildExtractReport(unittest.TestCase):
    """cp123: build_extract_report 提取报告文本生成。"""

    def test_empty_segments(self):
        """空片段 → 无提取内容提示。"""
        text = build_extract_report([])
        self.assertIn("无提取内容", text)

    def test_single_page_single_segment(self):
        """单页单片段：含页码 + y范围 + 高度。"""
        segments = [[{"src_pno": 2, "y_min": 312, "y_max": 480}]]
        text = build_extract_report(segments)
        self.assertIn("结果页 1", text)
        self.assertIn("原文档第 3 页", text)  # src_pno=2 → 第3页
        self.assertIn("312.0", text)
        self.assertIn("480.0", text)
        self.assertIn("共 1 页，1 个片段", text)

    def test_multi_page_multi_segment(self):
        """多页多片段：各页/片段都列出。"""
        segments = [
            [{"src_pno": 0, "y_min": 0, "y_max": 100},
             {"src_pno": 1, "y_min": 300, "y_max": 400}],
            [{"src_pno": 2, "y_min": 50, "y_max": 150}],
        ]
        text = build_extract_report(segments)
        self.assertIn("结果页 1", text)
        self.assertIn("结果页 2", text)
        self.assertIn("片段 1", text)
        self.assertIn("片段 2", text)
        self.assertIn("共 2 页，3 个片段", text)

    def test_clamps_with_src_doc(self):
        """传 src_doc 时 y 钳制到源页边界。"""
        doc = fitz.open()
        doc.new_page(width=200, height=400)
        segments = [[{"src_pno": 0, "y_min": 0, "y_max": 999}]]
        text = build_extract_report(segments, src_doc=doc)
        # y_max 钳到 400
        self.assertIn("400.0", text)
        self.assertNotIn("999", text)


if __name__ == "__main__":
    unittest.main()
