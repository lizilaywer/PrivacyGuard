"""
W2 回归测试：Word 页眉/页脚纳入脱敏范围

背景：旧实现打开/扫描/保存只覆盖 doc.paragraphs 与 doc.tables，
页眉页脚中的敏感信息（公司名、电话、密级等）会被完全漏脱。
本测试验证页眉页脚段落能被发现、扫描并正确替换。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from docx import Document

import main


class TestWordHeaderFooterRedaction(unittest.TestCase):
    def _build_doc_with_header_footer(self):
        doc = Document()
        section = doc.sections[0]

        # 解除继承，创建真实的页眉/页脚内容
        section.header.is_linked_to_previous = False
        section.footer.is_linked_to_previous = False

        section.header.paragraphs[0].add_run("页眉联系电话13800138000")
        section.footer.paragraphs[0].add_run("页脚备用电话13900139000")

        # 正文放一条普通文本作为对照
        doc.add_paragraph("正文手机13700137000")
        return doc

    def test_iter_discovers_header_and_footer(self):
        """页眉页脚段落应能被发现，且 key 前缀符合约定。"""
        doc = self._build_doc_with_header_footer()
        keys = [key for key, _ in main.iter_word_header_footer_paragraphs(doc)]
        self.assertTrue(any(k.startswith("header_") for k in keys),
                        f"应发现页眉段落，实际 keys={keys}")
        self.assertTrue(any(k.startswith("footer_") for k in keys),
                        f"应发现页脚段落，实际 keys={keys}")

    def test_header_footer_text_scanned_and_redacted(self):
        """页眉页脚敏感号码经扫描/替换后不得残留。"""
        doc = self._build_doc_with_header_footer()
        rules = [{"enabled": True, "mode": "regex", "find": r"1[3-9]\d{9}", "replace": "[手机]"}]

        for _key, para in main.iter_word_header_footer_paragraphs(doc):
            source = main.paragraph_plain_text(para)
            matches = main.build_word_rule_matches(source, rules, "[已脱敏]")
            if matches:
                main.replace_matches_in_paragraph(para, matches, text_offset=0,
                                                  fallback_replacement_text="[已脱敏]")

        header_text = main.paragraph_plain_text(doc.sections[0].header.paragraphs[0])
        footer_text = main.paragraph_plain_text(doc.sections[0].footer.paragraphs[0])
        self.assertNotIn("13800138000", header_text, "页眉手机号必须已脱敏")
        self.assertNotIn("13900139000", footer_text, "页脚手机号必须已脱敏")
        self.assertIn("[手机]", header_text)
        self.assertIn("[手机]", footer_text)

    def test_worker_scans_header_footer_keys(self):
        """WordWorker 应对 word_data 中的页眉页脚键生成 ocr 匹配（通用遍历）。"""
        from privacyguard.workers.word_worker import WordWorker

        word_data = {
            "paragraph_0": {"text": "正文手机13700137000", "ocr": [], "manual": []},
            "header_0_paragraph_0": {"text": "页眉联系电话13800138000", "ocr": [], "manual": []},
            "footer_0_paragraph_0": {"text": "页脚备用电话13900139000", "ocr": [], "manual": []},
        }

        worker = WordWorker(
            word_doc=None,
            word_data=word_data,
            rules=[r"1[3-9]\d{9}"],
            custom_keywords="",
            replacement_text="[已脱敏]",
        )

        results = {}

        def _capture(output):
            results.update(output)

        worker.finished_signal.connect(_capture)
        worker.run()  # 直接同步调用 run，避免起 QThread 事件循环

        self.assertTrue(results.get("header_0_paragraph_0", {}).get("ocr"),
                        "页眉键应被扫描出匹配")
        self.assertTrue(results.get("footer_0_paragraph_0", {}).get("ocr"),
                        "页脚键应被扫描出匹配")
        # W4：子线程只写本地副本，原始 word_data 不应被修改
        self.assertEqual(word_data["header_0_paragraph_0"]["ocr"], [],
                         "原始 word_data 不应被 worker 原地修改（W4）")


if __name__ == "__main__":
    unittest.main()
