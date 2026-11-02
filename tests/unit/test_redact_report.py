# -*- coding: utf-8 -*-
"""cp87 回归测试：脱敏报告纯函数（privacyguard/report.py）。"""
import unittest

from privacyguard.report import (
    classify_hit_rule,
    summarize_page_data,
    build_redact_report,
)

RULE_PAIRS = [
    ("身份证号", r"(?<!\d)\d{17}[\dXx](?!\d)"),
    ("手机号码", r"(?<!\d)1[3-9]\d{9}(?!\d)"),
]


class TestClassifyHitRule(unittest.TestCase):
    def test_regex_match_returns_rule_name(self):
        self.assertEqual(classify_hit_rule("13812345678", RULE_PAIRS), "手机号码")
        self.assertEqual(classify_hit_rule("11010119900101123X", RULE_PAIRS), "身份证号")

    def test_first_match_wins(self):
        # 身份证在前，含身份证的文本先命中身份证
        self.assertEqual(classify_hit_rule("11010119900101123X", RULE_PAIRS), "身份证号")

    def test_custom_keyword_match(self):
        self.assertEqual(classify_hit_rule("张三", RULE_PAIRS, ["张三"]), "自定义关键词")
        # 包含关系也认
        self.assertEqual(classify_hit_rule("原告张三", RULE_PAIRS, ["张三"]), "自定义关键词")

    def test_fallback(self):
        self.assertEqual(classify_hit_rule("普通文本", RULE_PAIRS), "智能识别")
        self.assertEqual(classify_hit_rule("", RULE_PAIRS), "智能识别")
        self.assertEqual(classify_hit_rule(None, None), "智能识别")

    def test_invalid_pattern_skipped(self):
        pairs = [("坏规则", r"([")] + RULE_PAIRS
        self.assertEqual(classify_hit_rule("13812345678", pairs), "手机号码")


class TestSummarizeAndReport(unittest.TestCase):
    def _sample_page_data(self):
        return {
            0: {"ocr": [{"rect": None, "replace_text": "", "rule": "手机号码"},
                        {"rect": None, "replace_text": "", "rule": "手机号码"}],
                "manual": [{"rect": None, "replace_text": "X"}]},
            1: {"ocr": [], "manual": []},
            2: {"ocr": [{"rect": None, "replace_text": "", "rule": "印章"},
                        {"rect": None, "replace_text": ""}],  # 无 rule → 智能识别
                "manual": []},
        }

    def test_summarize_counts(self):
        total, rule_pages = summarize_page_data(self._sample_page_data())
        self.assertEqual(total, 5)
        self.assertEqual(rule_pages["手机号码"], {0: 2})
        self.assertEqual(rule_pages["手动遮罩"], {0: 1})
        self.assertEqual(rule_pages["印章"], {2: 1})
        self.assertEqual(rule_pages["智能识别"], {2: 1})

    def test_summarize_empty(self):
        total, rule_pages = summarize_page_data({})
        self.assertEqual(total, 0)
        self.assertEqual(rule_pages, {})

    def test_report_content(self):
        text = build_redact_report("卷三.pdf", 3, self._sample_page_data(),
                                   "D:/out/卷三_脱敏.pdf", encrypted=True,
                                   now_str="2026-07-27 15:30:00")
        self.assertIn("卷三.pdf（3 页）", text)
        self.assertIn("共遮罩 5 处", text)
        self.assertIn("手机号码 2 处（第 1 页）", text)   # 0基→1基
        self.assertIn("印章 1 处（第 3 页）", text)
        self.assertIn("加密：已启用", text)
        self.assertIn("逐页明细", text)
        self.assertIn("第 1 页：手机号码×2，手动遮罩×1", text)
        self.assertIn("2026-07-27 15:30:00", text)

    def test_report_empty(self):
        text = build_redact_report("a.pdf", 2, {}, "b.pdf",
                                   encrypted=False, now_str="t")
        self.assertIn("未包含任何遮罩", text)
        self.assertIn("加密：未启用", text)
        self.assertNotIn("逐页明细", text)


if __name__ == "__main__":
    unittest.main()
