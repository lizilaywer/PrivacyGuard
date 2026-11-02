# -*- coding: utf-8 -*-
"""cp_bookmark 回归：书签脱敏与数据转换纯函数。

覆盖 helpers_bookmark 全部函数：
- redact_toc_titles: 替换/删除规则、多规则组合、未命中保留、空输入边界
- find_bookmark_matches: 大小写不敏感、空查询、命中索引
- toc_to_tree_nodes / tree_nodes_to_toc: 往返一致性、多层级、异常 level
"""
import unittest

from privacyguard.utils.helpers_bookmark import (
    redact_toc_titles,
    find_bookmark_matches,
    toc_to_tree_nodes,
    tree_nodes_to_toc,
)


class TestRedactTocTitles(unittest.TestCase):
    """书签标题脱敏：替换与删除规则。"""

    def test_replace_rule_rewrites_title(self):
        """规则 find=记录 replace=下载 → 标题中'记录'改写为'下载'。"""
        toc = [[1, "讯问记录", 5], [1, "卷宗封面", 1]]
        rules = [{"enabled": True, "find": "记录", "replace": "下载"}]
        result = redact_toc_titles(toc, rules)
        self.assertEqual(result[0][1], "讯问下载")
        self.assertEqual(result[1][1], "卷宗封面")  # 未命中保留

    def test_empty_replace_deletes_substring(self):
        """规则 find=记录 replace='' → 删除'记录'子串（纯遮罩语义）。"""
        toc = [[1, "讯问记录附件", 5]]
        rules = [{"enabled": True, "find": "记录", "replace": ""}]
        result = redact_toc_titles(toc, rules)
        self.assertEqual(result[0][1], "讯问附件")

    def test_disabled_rule_skipped(self):
        """enabled=False 的规则不应用。"""
        toc = [[1, "讯问记录", 5]]
        rules = [{"enabled": False, "find": "记录", "replace": "下载"}]
        result = redact_toc_titles(toc, rules)
        self.assertEqual(result[0][1], "讯问记录")

    def test_multiple_rules_applied_sequentially(self):
        """多条规则顺序应用，先改写后的文本仍可被后续规则命中。"""
        toc = [[1, "张三的记录", 5]]
        rules = [
            {"enabled": True, "find": "张三", "replace": "张某某"},
            {"enabled": True, "find": "记录", "replace": "材料"},
        ]
        result = redact_toc_titles(toc, rules)
        self.assertEqual(result[0][1], "张某某的材料")

    def test_partial_match_substring(self):
        """子串匹配：'记录'命中'讯问记录原件'。"""
        toc = [[1, "讯问记录原件", 5]]
        rules = [{"enabled": True, "find": "记录", "replace": "X"}]
        result = redact_toc_titles(toc, rules)
        self.assertEqual(result[0][1], "讯问X原件")

    def test_preserves_level_and_page(self):
        """脱敏不改变 level/page。"""
        toc = [[1, "章一", 1], [2, "节记录", 2], [3, "条目", 3]]
        rules = [{"enabled": True, "find": "记录", "replace": ""}]
        result = redact_toc_titles(toc, rules)
        self.assertEqual([r[0] for r in result], [1, 2, 3])
        self.assertEqual([r[2] for r in result], [1, 2, 3])

    def test_does_not_mutate_input(self):
        """不修改入参 toc（返回新列表）。"""
        toc = [[1, "讯问记录", 5]]
        original = [list(e) for e in toc]
        redact_toc_titles(toc, [{"enabled": True, "find": "记录", "replace": "X"}])
        self.assertEqual(toc, original)

    def test_empty_toc_returns_empty(self):
        self.assertEqual(redact_toc_titles([], []), [])
        self.assertEqual(redact_toc_titles(None, []), [])

    def test_empty_rules_returns_copy(self):
        """无规则时返回 toc 副本（结构与内容不变）。"""
        toc = [[1, "章一", 1], [2, "节一", 2]]
        result = redact_toc_titles(toc, [])
        self.assertEqual(result, toc)
        self.assertIsNot(result, toc)  # 是副本不是同一对象

    def test_title_not_str_coerced(self):
        """title 非 str 时强制转换（防御异常数据）。"""
        toc = [[1, 12345, 5]]
        result = redact_toc_titles(toc, [{"enabled": True, "find": "3", "replace": "X"}])
        self.assertEqual(result[0][1], "12X45")

    def test_case_insensitive_match(self):
        """审计 A3：书签脱敏大小写不敏感，与正文路径（IGNORECASE）对齐。"""
        toc = [[1, "Zhang San 讯问", 5], [1, "zhang san 询问", 6]]
        rules = [{"enabled": True, "find": "zhang", "replace": "[姓名]"}]
        result = redact_toc_titles(toc, rules)
        self.assertEqual(result[0][1], "[姓名] San 讯问")
        self.assertEqual(result[1][1], "[姓名] san 询问")

    def test_replace_none_treated_as_empty(self):
        """审计 P2：_apply_rules_to_title 对 replace=None 防御（不抛 TypeError）。

        注：redact_toc_titles 经 normalize_custom_keyword_rules 会把 None 转成
        字符串 "None"（既有行为），所以这里直接测内部函数的防御层。
        """
        from privacyguard.utils.helpers_bookmark import _apply_rules_to_title
        result = _apply_rules_to_title("讯问记录", [{"find": "记录", "replace": None}])
        self.assertEqual(result, "讯问")

    def test_regex_metachar_in_find_escaped(self):
        """find 含正则元字符时应按字面匹配（re.escape）。"""
        toc = [[1, "价格(元)合计", 5]]
        rules = [{"enabled": True, "find": "(元)", "replace": "[单位]"}]
        result = redact_toc_titles(toc, rules)
        self.assertEqual(result[0][1], "价格[单位]合计")


class TestFindBookmarkMatches(unittest.TestCase):
    """书签栏搜索匹配。"""

    def test_case_insensitive_match(self):
        toc = [[1, "Chapter One", 1], [1, "Chapter Two", 5]]
        matches = find_bookmark_matches(toc, "two")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], (1, "Chapter Two"))

    def test_chinese_substring_match(self):
        toc = [[1, "讯问记录", 5], [1, "卷宗封面", 1]]
        matches = find_bookmark_matches(toc, "记录")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0], 0)

    def test_multiple_matches_returned(self):
        toc = [[1, "记录一", 1], [1, "其他", 2], [2, "记录二", 3]]
        matches = find_bookmark_matches(toc, "记录")
        self.assertEqual([m[0] for m in matches], [0, 2])

    def test_empty_query_returns_empty(self):
        toc = [[1, "章", 1]]
        self.assertEqual(find_bookmark_matches(toc, ""), [])
        self.assertEqual(find_bookmark_matches(toc, "   "), [])

    def test_empty_toc_returns_empty(self):
        self.assertEqual(find_bookmark_matches([], "x"), [])
        self.assertEqual(find_bookmark_matches(None, "x"), [])


class TestTocTreeConversion(unittest.TestCase):
    """fitz TOC ↔ 嵌套树节点往返一致性。"""

    def test_roundtrip_preserves_flat_toc(self):
        """扁平 TOC（全 level=1）往返不变。"""
        toc = [[1, "章一", 1], [1, "章二", 2], [1, "章三", 3]]
        nodes = toc_to_tree_nodes(toc)
        result = tree_nodes_to_toc(nodes)
        self.assertEqual(result, toc)

    def test_roundtrip_preserves_nested_toc(self):
        """多层级 TOC 往返不变。"""
        toc = [
            [1, "第一编", 1],
            [2, "第一章", 2],
            [3, "第一节", 3],
            [2, "第二章", 5],
            [1, "第二编", 8],
        ]
        nodes = toc_to_tree_nodes(toc)
        result = tree_nodes_to_toc(nodes)
        self.assertEqual(result, toc)

    def test_tree_structure_correct(self):
        """层级关系正确：子节点归到最近的低 level 父节点。"""
        toc = [
            [1, "父A", 1],
            [2, "子A1", 2],
            [2, "子A2", 3],
            [1, "父B", 4],
        ]
        nodes = toc_to_tree_nodes(toc)
        self.assertEqual(len(nodes), 2)  # 两个根
        self.assertEqual(nodes[0]["title"], "父A")
        self.assertEqual(len(nodes[0]["children"]), 2)
        self.assertEqual(nodes[0]["children"][0]["title"], "子A1")
        self.assertEqual(nodes[1]["title"], "父B")
        self.assertEqual(len(nodes[1]["children"]), 0)

    def test_empty_toc_returns_empty(self):
        self.assertEqual(toc_to_tree_nodes([]), [])
        self.assertEqual(toc_to_tree_nodes(None), [])
        self.assertEqual(tree_nodes_to_toc([]), [])
        self.assertEqual(tree_nodes_to_toc(None), [])

    def test_abnormal_level_handled(self):
        """level 异常（跳级或非正）时尽量构建，不崩溃。"""
        # level 从 1 跳到 3（缺 2）
        toc = [[1, "根", 1], [3, "孙", 2]]
        nodes = toc_to_tree_nodes(toc)
        # 不崩溃即通过；孙应挂在根下（栈逻辑处理跳级）
        self.assertEqual(len(nodes), 1)


if __name__ == "__main__":
    unittest.main()
