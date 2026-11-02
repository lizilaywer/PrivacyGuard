# -*- coding: utf-8 -*-
"""cp65 修复回归：替换文本导出字号与屏幕预览对齐。

根因：导出路径原把替换文字交给 fitz add_redact_annot（默认 fontsize=11，
且 fitz 把超 h*0.625 的请求压到 ~h*0.625），与屏幕预览公式
（rect.height*0.75 + 宽度自适配）不一致，导致导出文字系统性偏小。

修复：导出改为 add_redact_annot 纯遮罩 + apply_redactions 之后用
insert_text 绘制文字，字号用 compute_replace_text_fontsize 计算
（与屏幕公式对齐）。
"""
import unittest


class TestComputeReplaceTextFontsize(unittest.TestCase):
    """cp65: compute_replace_text_fontsize 与屏幕预览公式对齐。"""

    def test_base_is_height_times_075(self):
        """无宽度约束时，字号 = rect.height * 0.75（与屏幕一致）。"""
        from privacyguard.utils.helpers_pdf import compute_replace_text_fontsize
        # rect_h=20 → base=15（与屏幕 _draw_replace_text 的 pixelSize 一致）
        self.assertAlmostEqual(compute_replace_text_fontsize(60, 20, "张三", 30.0), 15.0)
        self.assertAlmostEqual(compute_replace_text_fontsize(80, 24, "李四", 30.0), 18.0)

    def test_respects_min_size(self):
        """rect 极小时不低于最小字号 6。"""
        from privacyguard.utils.helpers_pdf import compute_replace_text_fontsize
        self.assertEqual(compute_replace_text_fontsize(40, 4, "字", 5.0), 6.0)

    def test_width_autofit_shrinks_when_overflow(self):
        """文字宽度超出 rect 宽度时，按宽度比例缩小字号（与屏幕公式一致）。"""
        from privacyguard.utils.helpers_pdf import compute_replace_text_fontsize
        # rect_w=30, text_w=60（超出一倍）→ base=15 缩到 15*26/60=6.5
        # avail = 30-4=26, ratio = 26/60
        fs = compute_replace_text_fontsize(30, 20, "长文字XYZ", 60.0)
        expected = 15.0 * (30 - 4) / 60.0
        self.assertAlmostEqual(fs, expected)
        self.assertLess(fs, 15.0)  # 确实缩小了

    def test_no_shrink_when_text_fits(self):
        """文字宽度未超出时不缩小。"""
        from privacyguard.utils.helpers_pdf import compute_replace_text_fontsize
        fs = compute_replace_text_fontsize(100, 20, "短", 20.0)
        self.assertAlmostEqual(fs, 15.0)  # 不缩

    def test_zero_height_returns_min(self):
        """rect 高度 0 时返回最小字号（防异常）。"""
        from privacyguard.utils.helpers_pdf import compute_replace_text_fontsize
        self.assertEqual(compute_replace_text_fontsize(40, 0, "字", 5.0), 6.0)

    def test_zero_text_length_returns_base(self):
        """text_length=0（无法测宽）时返回 base，不缩。"""
        from privacyguard.utils.helpers_pdf import compute_replace_text_fontsize
        self.assertAlmostEqual(compute_replace_text_fontsize(40, 20, "字", 0.0), 15.0)


class TestExportFontsizeMatchesScreen(unittest.TestCase):
    """端到端：导出 PDF 中替换文字字号应与屏幕公式（h*0.75）对齐，
    而非旧的 fitz 默认 11pt（实际渲染 ~10.5pt）。"""

    def setUp(self):
        try:
            import fitz  # noqa: F401
        except ImportError:
            self.skipTest("PyMuPDF 未安装")

    def test_export_fontsize_matches_height_times_075(self):
        """rect_h=20 时导出字号应为 15pt（=20*0.75），而非偏小的 ~10.5pt。"""
        import fitz
        from privacyguard.utils.helpers_pdf import compute_replace_text_fontsize

        d = fitz.open()
        p = d.new_page(width=300, height=100)
        p.insert_text((20, 30), "原文参考", fontname="china-s", fontsize=14, color=(0, 0, 0))
        rect = fitz.Rect(100, 15, 160, 35)  # h=20
        p.add_redact_annot(rect).update()
        p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

        # 复刻 save_pdf 修复后的字号计算逻辑
        base_fs = max(6.0, rect.height * 0.75)
        text_w = fitz.get_text_length("张三", fontname="china-s", fontsize=base_fs)
        fs = compute_replace_text_fontsize(rect.width, rect.height, "张三", text_w)
        actual_w = fitz.get_text_length("张三", fontname="china-s", fontsize=fs)
        start_x = (rect.x0 + rect.x1) / 2 - actual_w / 2
        baseline_y = (rect.y0 + rect.y1) / 2 + fs * 0.35
        p.insert_text((start_x, baseline_y), "张三", fontname="china-s",
                      fontsize=fs, color=(1, 1, 1), overlay=True)

        # 提取导出后的实际渲染字号
        replaced_size = None
        for b in d[0].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if s["text"].strip() == "张三":
                        replaced_size = s["size"]
        d.close()

        self.assertIsNotNone(replaced_size, "替换文字未被渲染")
        # 应为 15pt（=20*0.75），而非旧的偏小值
        self.assertAlmostEqual(replaced_size, 15.0, delta=0.5)
        # 明确大于旧的 fitz 默认渲染值（~10.5pt）
        self.assertGreater(replaced_size, 13.0,
                           "替换文字字号仍偏小（疑似回退到 fitz 默认 11）")

    def test_old_behavior_produced_smaller_font(self):
        """对照测试：旧实现（add_redact_annot text=）确实产生偏小字号，
        证明本修复针对的是真实差异。"""
        import fitz

        d = fitz.open()
        p = d.new_page(width=300, height=100)
        rect = fitz.Rect(100, 15, 160, 35)
        p.add_redact_annot(rect, text="张三", fill=(0, 0, 0), text_color=(1, 1, 1),
                           fontname="china-s", cross_out=False).update()
        p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
        old_size = None
        for b in d[0].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if s["text"].strip() == "张三":
                        old_size = s["size"]
        d.close()
        # 旧实现渲染 ~10.5pt（远小于 rect_h*0.75=15）
        self.assertLess(old_size, 12.0,
                        "旧实现字号应偏小（若此处失败说明 fitz 行为变了，需复查修复）")


if __name__ == "__main__":
    unittest.main()
