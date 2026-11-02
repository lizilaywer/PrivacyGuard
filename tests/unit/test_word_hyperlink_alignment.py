"""
W1 回归测试：Word 含超链接段落的脱敏 offset 对齐

背景：python-docx 中 para.text 包含超链接可见文字，但 para.runs 不含超链接内 run。
若扫描用 para.text 存 offset、替换用 run 拼接，含超链接段落会错位或静默漏脱。
本测试构造这种段落，验证敏感词仍被正确替换（旧实现会漏脱）。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from docx import Document
from docx.oxml import OxmlElement

import main


def _append_hyperlink_text(paragraph, text):
    """向段落追加一个 <w:hyperlink>（内含一个 run），其文字进入 para.text 但不进入 para.runs。"""
    hyperlink = OxmlElement("w:hyperlink")
    run = OxmlElement("w:r")
    run.append(OxmlElement("w:rPr"))
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


class TestWordHyperlinkAlignment(unittest.TestCase):
    def _build_paragraph_with_hyperlink(self):
        doc = Document()
        para = doc.add_paragraph()
        # 先放一段超链接文字（仅进入 para.text），再放普通 run（含敏感词）
        _append_hyperlink_text(para, "点击访问官网导航链接")
        para.add_run("联系人手机13800138000请保密")
        return doc, para

    def test_para_text_differs_from_run_concat(self):
        """前置条件：含超链接时 para.text 与 run 拼接必须不同，否则测试无意义。"""
        _, para = self._build_paragraph_with_hyperlink()
        self.assertNotEqual(para.text, main.paragraph_plain_text(para))
        self.assertIn("13800138000", para.text)
        self.assertIn("13800138000", main.paragraph_plain_text(para))

    def test_sensitive_text_redacted_with_run_concat_source(self):
        """使用 run 拼接文本源（修复后行为），敏感词应被正确替换。"""
        _, para = self._build_paragraph_with_hyperlink()

        source_text = main.paragraph_plain_text(para)
        rules = [{"enabled": True, "mode": "regex", "find": r"1[3-9]\d{9}", "replace": "[手机]"}]
        matches = main.build_word_rule_matches(source_text, rules, "[已脱敏]")
        self.assertTrue(matches, "应能在 run 拼接文本中命中手机号")

        main.replace_matches_in_paragraph(para, matches, text_offset=0,
                                          fallback_replacement_text="[已脱敏]")

        result = main.paragraph_plain_text(para)
        self.assertNotIn("13800138000", result, "手机号必须已被脱敏，不能残留")
        self.assertIn("[手机]", result)

    def test_old_paratext_source_would_leak(self):
        """反证：若沿用 para.text 作为 offset 源（旧实现），会因越界而静默漏脱。"""
        _, para = self._build_paragraph_with_hyperlink()

        # 旧实现：offset 基于 para.text（含超链接）
        old_source = para.text
        rules = [{"enabled": True, "mode": "regex", "find": r"1[3-9]\d{9}", "replace": "[手机]"}]
        matches = main.build_word_rule_matches(old_source, rules, "[已脱敏]")
        self.assertTrue(matches)

        # 替换仍基于 run 拼接 -> 越界跳过 -> 漏脱
        main.replace_matches_in_paragraph(para, matches, text_offset=0,
                                          fallback_replacement_text="[已脱敏]")
        leaked = main.paragraph_plain_text(para)
        self.assertIn("13800138000", leaked,
                      "旧实现应表现为漏脱（本断言用于固化 W1 的根因，证明修复必要性）")


if __name__ == "__main__":
    unittest.main()
