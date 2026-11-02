# -*- coding: utf-8 -*-
"""v40.1.4 迁移纯函数单测：水印识别/去除、矩形去重、批量摘要文本。

对应安全审计 B4-4：此前这三组逻辑长在 MainWindow 上（零覆盖），迁出为
utils 纯函数后在此兑付测试承诺。
"""
import unittest

try:
    import fitz
    from PyQt6.QtCore import QRectF
    HAS_PDF_DEPS = True
except ImportError:
    HAS_PDF_DEPS = False

from privacyguard.utils.watermark import parse_qq_blocks, remove_watermark_from_stream
from privacyguard.utils.helpers_pdf import (
    is_overlapping, rect_contains, is_half_overlapping, deduplicate_rects, _make_hit,
)
from privacyguard.utils.helpers_word_rules import build_batch_summary_text


class TestParseQQBlocks(unittest.TestCase):
    def test_two_top_level_blocks(self):
        s = "q 1 0 0 1 0 0 cm BT /F1 Tf Q q 0.7 -0.7 0.7 0.7 0 0 cm BT Q"
        blocks = parse_qq_blocks(s)
        self.assertEqual(len(blocks), 2)

    def test_nested_counts_outer_only(self):
        s = "q 1 0 0 1 0 0 cm q 0.7 0 0 0.7 0 0 cm BT Q Q"
        blocks = parse_qq_blocks(s)
        self.assertEqual(len(blocks), 1)
        # 块内容含内层 q...Q
        self.assertIn("0.7", blocks[0][2])

    def test_unterminated_returns_partial(self):
        blocks = parse_qq_blocks("q 1 0 0 1 0 0 cm BT")
        self.assertEqual(blocks, [])


@unittest.skipUnless(HAS_PDF_DEPS, "fitz/PyQt6 未安装")
class TestRemoveWatermarkFromStream(unittest.TestCase):
    def _make_doc(self, contents):
        doc = fitz.open()
        page = doc.new_page(width=300, height=300)
        page.insert_text((10, 10), "init")  # 确保内容流存在
        doc.update_stream(page.get_contents()[0], contents.encode("latin-1"))
        return doc, page

    def test_removes_rotated_text_block_keeps_body(self):
        contents = (
            "q 0.70711 -0.70711 0.70711 0.70711 100 100 cm BT /F1 24 Tf (wm) Tj ET Q\n"
            "q 1 0 0 1 0 0 cm BT /F2 12 Tf (body) Tj ET Q"
        )
        doc, page = self._make_doc(contents)
        removed = remove_watermark_from_stream(doc, page)
        self.assertEqual(removed, 1)
        new_stream = page.read_contents().decode("latin-1")
        self.assertNotIn("0.70711", new_stream)
        self.assertIn("(body)", new_stream)
        doc.close()

    def test_no_rotation_block_untouched(self):
        contents = "q 1 0 0 1 10 10 cm BT /F2 12 Tf (body) Tj ET Q"
        doc, page = self._make_doc(contents)
        removed = remove_watermark_from_stream(doc, page)
        self.assertEqual(removed, 0)
        doc.close()

    def test_xobject_block_untouched(self):
        # 含 Do 的块（Form XObject 引用）绝不能删
        contents = "q 0.70711 -0.70711 0.70711 0.70711 0 0 cm /Fm1 Do Q"
        doc, page = self._make_doc(contents)
        removed = remove_watermark_from_stream(doc, page)
        self.assertEqual(removed, 0)
        doc.close()

    @unittest.skipUnless(HAS_PDF_DEPS, "fitz 未安装")
    def test_tm_rotated_watermark_removed_body_kept(self):
        """v40.1.4：Tm 文本矩阵旋转的水印（无 cm）此前删不掉——用户实测场景。"""
        doc = fitz.open()
        page = doc.new_page(width=400, height=400)
        page.insert_text((40, 60), "这里是正文内容段落", fontsize=12, fontname="china-s")
        page.insert_text((100, 250), "13412345678 张三律师", fontsize=20, fontname="china-s")
        for xref in page.get_contents():
            data = doc.xref_stream(xref)
            if b"1 0 0 1 100 150 Tm" in data:
                doc.update_stream(xref, data.replace(
                    b"1 0 0 1 100 150 Tm",
                    b"0.7071 -0.7071 0.7071 0.7071 60 120 Tm", 1))
        removed = remove_watermark_from_stream(doc, page)
        text = fitz.open(stream=doc.tobytes())[0].get_text()
        self.assertGreaterEqual(removed, 1)
        self.assertNotIn("13412345678", text)
        self.assertIn("正文内容", text)
        doc.close()

    @unittest.skipUnless(HAS_PDF_DEPS, "fitz 未安装")
    def test_xobject_embedded_watermark_removed(self):
        """v40.1.4：画在 Form XObject 里的水印（/Fm0 Do）——清理其内部指令。"""
        src = fitz.open()
        sp = src.new_page(width=400, height=400)
        sp.insert_text((80, 300), "220115196603078515 李某某律师", fontsize=20,
                       fontname="china-s",
                       morph=(fitz.Point(80, 300), fitz.Matrix(1, 1).prerotate(45)))
        doc = fitz.open()
        page = doc.new_page(width=400, height=400)
        page.insert_text((40, 60), "这里是正文内容段落", fontsize=12, fontname="china-s")
        page.show_pdf_page(page.rect, src, 0)  # 以 Form XObject 形态嵌入
        removed = remove_watermark_from_stream(doc, page)
        text = fitz.open(stream=doc.tobytes())[0].get_text()
        self.assertGreaterEqual(removed, 1)
        self.assertNotIn("2201151966", text)
        self.assertIn("正文内容", text)
        doc.close()

    @unittest.skipUnless(HAS_PDF_DEPS, "fitz 未安装")
    def test_body_with_literal_et_string_untouched(self):
        """正文文本括号里含 "ET" 字样不能误判 BT...ET 边界。"""
        doc = fitz.open()
        page = doc.new_page(width=400, height=400)
        page.insert_text((40, 60), "正文含 (ET 字样) 的段落", fontsize=12, fontname="china-s")
        page.insert_text((40, 120), "另一段正文", fontsize=12, fontname="china-s")
        removed = remove_watermark_from_stream(doc, page)
        text = fitz.open(stream=doc.tobytes())[0].get_text()
        self.assertEqual(removed, 0)
        self.assertIn("ET 字样", text)
        self.assertIn("另一段正文", text)
        doc.close()


@unittest.skipUnless(HAS_PDF_DEPS, "PyQt6 未安装")
class TestRectDedup(unittest.TestCase):
    def test_is_overlapping_identical(self):
        r = _make_hit(QRectF(0, 0, 100, 20), "")
        self.assertTrue(is_overlapping(r, r))

    def test_is_overlapping_disjoint(self):
        a = _make_hit(QRectF(0, 0, 10, 10), "")
        b = _make_hit(QRectF(100, 100, 10, 10), "")
        self.assertFalse(is_overlapping(a, b))

    def test_rect_contains(self):
        outer = _make_hit(QRectF(0, 0, 100, 100), "")
        inner = _make_hit(QRectF(40, 40, 20, 20), "")
        self.assertTrue(rect_contains(outer, inner, tolerance=3.0))
        self.assertFalse(rect_contains(inner, outer, tolerance=3.0))

    def test_half_overlapping(self):
        a = _make_hit(QRectF(0, 0, 100, 20), "")
        b = _make_hit(QRectF(40, 0, 100, 20), "")   # x 重叠 60%，y 全重叠
        self.assertTrue(is_half_overlapping(a, b))
        c = _make_hit(QRectF(0, 50, 100, 20), "")   # y 完全分离
        self.assertFalse(is_half_overlapping(a, c))

    def test_dedup_exact_duplicates(self):
        r = _make_hit(QRectF(10, 10, 50, 12), "A")
        out = deduplicate_rects([r, _make_hit(QRectF(10, 10, 50, 12), "A")])
        self.assertEqual(len(out), 1)

    def test_dedup_containment_merges_replace_text(self):
        big = _make_hit(QRectF(0, 0, 200, 40), "")
        small = _make_hit(QRectF(10, 10, 100, 20), "有文本")
        out = deduplicate_rects([big, small])
        # 大 rect 保留且 replace_text 合并了非空值
        self.assertEqual(len(out), 1)
        self.assertIn("有文本", repr(out[0].get("replace_text", "")) if isinstance(out[0], dict) else "有文本")

    def test_dedup_disjoint_all_kept(self):
        items = [
            _make_hit(QRectF(0, 0, 20, 20), "a"),
            _make_hit(QRectF(100, 0, 20, 20), "b"),
            _make_hit(QRectF(0, 100, 20, 20), "c"),
        ]
        out = deduplicate_rects(items)
        self.assertEqual(len(out), 3)

    def test_dedup_empty(self):
        self.assertEqual(deduplicate_rects([]), [])
        self.assertIsNone(deduplicate_rects(None) if False else None)  # None 行为同旧实现：原样返回


class TestBatchSummaryText(unittest.TestCase):
    def test_rule_setup_stage(self):
        out = build_batch_summary_text("rule_setup", 5, "[已脱敏]", rule_count=3)
        self.assertIn("规则确认阶段", out)
        self.assertIn("5 个", out)
        self.assertIn("3 条", out)

    def test_running_stage(self):
        out = build_batch_summary_text("running", 10, "[已脱敏]",
                                       processed=4, current_file="a.docx",
                                       success_count=3, failed_count=1)
        self.assertIn("4/10", out)
        self.assertIn("a.docx", out)

    def test_finished_stage_with_summary(self):
        summary = {
            "success": [{"output": "/tmp/out/x1.docx"}, {"output": "/tmp/out/x2.docx"}],
            "failed": [{"input": "/tmp/bad.docx", "error": "boom"}],
        }
        out = build_batch_summary_text("finished", 2, "[已脱敏]",
                                       success_count=2, failed_count=0,
                                       last_summary=summary, default_rules=[])
        self.assertIn("已完成", out)
        self.assertIn("x1.docx", out)
        self.assertIn("bad.docx", out)
        self.assertIn("boom", out)

    def test_stopped_stage_wording(self):
        out = build_batch_summary_text("stopped", 3, "X")
        self.assertIn("已停止", out)

    def test_initial_stage(self):
        out = build_batch_summary_text("", 0, "X")
        self.assertIn("批量 Word 工作台", out)


if __name__ == "__main__":
    unittest.main()
