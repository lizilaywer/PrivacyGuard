"""v37.7.13 cp43: 自定义关键词规则规范化与迁移测试。

直接从 privacyguard/utils/helpers_word_rules.py 文件读取函数源码并执行，
避免触发 PyQt6.QtWebEngineWidgets 等运行时依赖。
v37.8.11 P3-1: 函数已按域拆分至 helpers_word_rules.py（原 helpers.py 改为再导出垫片）。
"""

import ast
import unittest


def _load_funcs_from_helpers():
    """从 privacyguard/utils/helpers_word_rules.py 解析 normalize_custom_keyword_rules 和
    migrate_custom_keywords_to_rules 两个函数 AST 并执行返回。

    这两个纯函数不依赖任何外部模块，可独立执行。
    """
    import os
    helpers_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                "privacyguard", "utils", "helpers_word_rules.py")
    helpers_path = os.path.abspath(helpers_path)
    with open(helpers_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    namespace = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in (
            "normalize_custom_keyword_rules",
            "migrate_custom_keywords_to_rules",
        ):
            code = compile(ast.Module([node], []), helpers_path, "exec")
            exec(code, namespace)
    return namespace


_ns = _load_funcs_from_helpers()
normalize_custom_keyword_rules = _ns["normalize_custom_keyword_rules"]
migrate_custom_keywords_to_rules = _ns["migrate_custom_keywords_to_rules"]


class TestNormalizeCustomKeywordRules(unittest.TestCase):
    def test_valid_rules(self):
        """完整有效规则列表应原样规范化。"""
        rules = [
            {"enabled": True, "find": "孙志华", "replace": "孙某某"},
            {"enabled": False, "find": "王小明", "replace": ""},
        ]
        result = normalize_custom_keyword_rules(rules)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], {"enabled": True, "find": "孙志华", "replace": "孙某某"})
        self.assertEqual(result[1], {"enabled": False, "find": "王小明", "replace": ""})

    def test_missing_fields(self):
        """缺少 enabled/replace 字段应使用默认值。"""
        rules = [{"find": "张三"}]
        result = normalize_custom_keyword_rules(rules)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["enabled"], True)
        self.assertEqual(result[0]["find"], "张三")
        self.assertEqual(result[0]["replace"], "")

    def test_empty_find_dropped(self):
        """find 为空的条目应被丢弃。"""
        rules = [
            {"find": "", "replace": "xxx"},
            {"enabled": True, "find": "李四", "replace": "李x"},
            {"find": "   "},
        ]
        result = normalize_custom_keyword_rules(rules)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["find"], "李四")

    def test_replace_empty_means_pure_mask(self):
        """replace 为空字符串应保留（表示纯遮罩不叠加）。"""
        rules = [{"find": "王五", "replace": ""}]
        result = normalize_custom_keyword_rules(rules)
        self.assertEqual(result[0]["replace"], "")

    def test_non_dict_items_dropped(self):
        """非 dict 元素应被丢弃。"""
        rules = [
            "not a dict",
            {"find": "赵六", "replace": "赵x"},
            None,
            123,
        ]
        result = normalize_custom_keyword_rules(rules)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["find"], "赵六")

    def test_non_list_input_returns_empty(self):
        """非 list 输入应返回空列表。"""
        self.assertEqual(normalize_custom_keyword_rules(None), [])
        self.assertEqual(normalize_custom_keyword_rules("not a list"), [])
        self.assertEqual(normalize_custom_keyword_rules({"find": "x"}), [])

    def test_strip_whitespace(self):
        """find/replace 两端空格应被 strip。"""
        rules = [{"find": "  张三  ", "replace": "  张x  "}]
        result = normalize_custom_keyword_rules(rules)
        self.assertEqual(result[0]["find"], "张三")
        self.assertEqual(result[0]["replace"], "张x")


class TestMigrateCustomKeywordsToRules(unittest.TestCase):
    def test_normal_multiline_string(self):
        """正常的多行字符串应转为规则列表。"""
        old_str = "孙志华\n王小明\n张三"
        result = migrate_custom_keywords_to_rules(old_str)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {"enabled": True, "find": "孙志华", "replace": ""})
        self.assertEqual(result[1], {"enabled": True, "find": "王小明", "replace": ""})
        self.assertEqual(result[2], {"enabled": True, "find": "张三", "replace": ""})

    def test_empty_string_returns_empty(self):
        """空字符串应返回空列表。"""
        self.assertEqual(migrate_custom_keywords_to_rules(""), [])
        self.assertEqual(migrate_custom_keywords_to_rules("   "), [])
        self.assertEqual(migrate_custom_keywords_to_rules("\n\n"), [])

    def test_non_string_input_returns_empty(self):
        """非字符串输入应返回空列表。"""
        self.assertEqual(migrate_custom_keywords_to_rules(None), [])
        self.assertEqual(migrate_custom_keywords_to_rules(123), [])
        self.assertEqual(migrate_custom_keywords_to_rules([]), [])

    def test_lines_with_whitespace_stripped(self):
        """每行两端空格应被 strip。"""
        old_str = "  孙志华  \n  王小明\n\n  \n张三"
        result = migrate_custom_keywords_to_rules(old_str)
        self.assertEqual(len(result), 3)
        self.assertEqual([r["find"] for r in result], ["孙志华", "王小明", "张三"])

    def test_migrated_rules_have_empty_replace(self):
        """迁移后所有规则的 replace 必须为空字符串（纯遮罩模式）。"""
        old_str = "孙志华\n王小明"
        result = migrate_custom_keywords_to_rules(old_str)
        for rule in result:
            self.assertEqual(rule["replace"], "")


if __name__ == "__main__":
    unittest.main()
