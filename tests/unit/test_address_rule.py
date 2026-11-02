# -*- coding: utf-8 -*-
"""cp135 回归测试：住址预设规则（住址/户籍地/住所地 + 地址整体遮罩）

覆盖：
1. 用户需求正例：标签（住址/户籍地/住所地）+ 地址遮到 栋/组/号/室/数字 为止；
   无标签纯地址（省+市+区县三级锚定）同样遮到终止符
2. 日期结构防误报：数字后紧跟年/月/日不命中（"庐江县2023年人口"）
3. 负例（不误伤）：户籍地不详、住所地待查明、无区县结构、案号、出生地、统计句
4. DEFAULT_RULES / iter_unique_text_matches 集成
5. _ensure_preset_rule 老配置注入迁移（stub cfg，不触碰真实 config.json）
"""
import re
import unittest

try:
    from main import ADDRESS_RULE_PATTERN, DEFAULT_RULES, _ensure_preset_rule
    from privacyguard.ocr.text_pdf import iter_unique_text_matches
    HAS_DEPS = True
except Exception:  # pragma: no cover - PyQt6/依赖缺失时跳过
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "依赖未安装")
class TestAddressRulePositive(unittest.TestCase):
    """正例：标签/行政区划锚定的地址整体命中。"""

    def _match(self, text):
        m = re.search(ADDRESS_RULE_PATTERN, text)
        return m.group() if m else None

    # --- 用户原始 5 例（带标签版） ---

    def test_label_zu_ending(self):
        # 用户例 1：住址：…川山组（组终止）
        self.assertEqual(self._match("住址：安徽省池州市贵池区牛头山镇川山组"),
                         "住址：安徽省池州市贵池区牛头山镇川山组")

    def test_label_number_ending(self):
        # 用户例 2：…岐山村111（数字终止）
        self.assertEqual(self._match("住址：安徽省池州市贵池区牛头山镇岐山村111"),
                         "住址：安徽省池州市贵池区牛头山镇岐山村111")

    def test_label_hao_ending(self):
        # 用户例 3：…东村17号（号终止）
        self.assertEqual(self._match("住址：安徽省池州市贵池区牛头山镇东村17号"),
                         "住址：安徽省池州市贵池区牛头山镇东村17号")

    def test_label_dong_ending(self):
        # 用户例 4：…川晚户112栋（栋终止）
        self.assertEqual(self._match("住址：安徽省池州市贵池区牛头山镇川晚户112栋"),
                         "住址：安徽省池州市贵池区牛头山镇川晚户112栋")

    def test_label_shi_ending(self):
        # 用户例 5：…川晚户112室（室终止）
        self.assertEqual(self._match("住址：安徽省池州市贵池区牛头山镇川晚户112室"),
                         "住址：安徽省池州市贵池区牛头山镇川晚户112室")

    # --- 用户原始 5 例（无标签纯地址版，省+市+区县锚定） ---

    def test_plain_zu_ending(self):
        self.assertEqual(self._match("安徽省池州市贵池区牛头山镇川山组"),
                         "安徽省池州市贵池区牛头山镇川山组")

    def test_plain_number_ending(self):
        self.assertEqual(self._match("安徽省池州市贵池区牛头山镇岐山村111"),
                         "安徽省池州市贵池区牛头山镇岐山村111")

    def test_plain_hao_ending(self):
        self.assertEqual(self._match("安徽省池州市贵池区牛头山镇东村17号"),
                         "安徽省池州市贵池区牛头山镇东村17号")

    def test_plain_dong_ending(self):
        self.assertEqual(self._match("安徽省池州市贵池区牛头山镇川晚户112栋"),
                         "安徽省池州市贵池区牛头山镇川晚户112栋")

    def test_plain_shi_ending(self):
        self.assertEqual(self._match("安徽省池州市贵池区牛头山镇川晚户112室"),
                         "安徽省池州市贵池区牛头山镇川晚户112室")

    # --- 标签变体 ---

    def test_huji_label(self):
        self.assertEqual(self._match("户籍地：安徽省合肥市庐阳区XX路88号"),
                         "户籍地：安徽省合肥市庐阳区XX路88号")

    def test_zhusuodi_label(self):
        self.assertEqual(self._match("住所地：浙江省杭州市西湖区文华路66栋2单元301室"),
                         "住所地：浙江省杭州市西湖区文华路66栋2单元301室")

    def test_halfwidth_colon_and_space(self):
        self.assertEqual(self._match("住址: 合肥市政务区东流路100号"),
                         "住址: 合肥市政务区东流路100号")

    def test_municipality_via_label(self):
        # 直辖市地址（无省头）走标签模式
        self.assertEqual(self._match("住址：北京市朝阳区建国路88号院3号"),
                         "住址：北京市朝阳区建国路88号院3号")

    def test_in_context_sentence(self):
        # 嵌入文书句子：只锚定"安徽省"起，前缀"被告住"不吃（cp135 穷举省头修复）
        text = "被告住安徽省池州市贵池区牛头山镇川山组，系农民。"
        self.assertEqual(self._match(text), "安徽省池州市贵池区牛头山镇川山组")

    def test_autonomous_region(self):
        # 自治区行政头（全称）
        self.assertEqual(self._match("户籍地：广西壮族自治区南宁市青秀区XX路5号"),
                         "户籍地：广西壮族自治区南宁市青秀区XX路5号")

    def test_plain_autonomous_region(self):
        # 无标签自治区纯地址
        self.assertEqual(self._match("内蒙古自治区呼和浩特市赛罕区XX街8号"),
                         "内蒙古自治区呼和浩特市赛罕区XX街8号")


@unittest.skipUnless(HAS_DEPS, "依赖未安装")
class TestAddressRuleNegative(unittest.TestCase):
    """负例：无地址结构时不命中，避免误伤。"""

    def _match(self, text):
        m = re.search(ADDRESS_RULE_PATTERN, text)
        return m.group() if m else None

    def test_label_unknown(self):
        # 标签后无地址（"不详"）不命中
        self.assertIsNone(self._match("户籍地：不详"))

    def test_label_pending(self):
        self.assertIsNone(self._match("住所地：待查明"))

    def test_no_terminator(self):
        # 无终止符（栋/组/号/室/数字）不命中
        self.assertIsNone(self._match("住址：安徽省合肥市庐阳区政务区"))

    def test_plain_no_district(self):
        # 纯地址缺区县级（"安徽省合肥市"无后续结构）不命中
        self.assertIsNone(self._match("安徽省合肥市"))

    def test_statistics_sentence(self):
        # 统计句误报防护：无市/区县结构
        self.assertIsNone(self._match("安徽省2023年经济数据排名"))

    def test_case_number(self):
        # 案号不命中（无标签、无省市区结构）
        self.assertIsNone(self._match("案号(2023)皖17号"))

    def test_birthplace_label(self):
        # "出生地"非触发标签；省+市无区县不命中
        self.assertIsNone(self._match("出生地：安徽省池州市"))

    def test_date_sentence(self):
        # 日期句不命中
        self.assertIsNone(self._match("2023年5月1日于合肥市签订"))

    def test_year_after_district(self):
        # 日期结构防误报：数字后紧跟"年"不视为门牌号终止
        self.assertIsNone(self._match("安徽省合肥市庐江县2023年人口普查"))


@unittest.skipUnless(HAS_DEPS, "依赖未安装")
class TestAddressRuleIntegration(unittest.TestCase):
    """集成：DEFAULT_RULES 注册 + 文本层命中收集。"""

    def test_registered_in_default_rules(self):
        self.assertEqual(DEFAULT_RULES.get("住址"), ADDRESS_RULE_PATTERN)

    def test_iter_unique_text_matches_hit(self):
        text = "被告住安徽省池州市贵池区牛头山镇川晚户112栋，系农民。"
        hits = list(iter_unique_text_matches(text, [ADDRESS_RULE_PATTERN]))
        self.assertIn("安徽省池州市贵池区牛头山镇川晚户112栋", hits)

    def test_iter_unique_text_matches_no_hit(self):
        hits = list(iter_unique_text_matches("户籍地：不详，详见卷宗。", [ADDRESS_RULE_PATTERN]))
        self.assertEqual(hits, [])

    def test_multiple_hits(self):
        text = "原告住安徽省池州市贵池区牛头山镇川山组，被告住安徽省合肥市庐阳区XX路88号。"
        hits = list(iter_unique_text_matches(text, [ADDRESS_RULE_PATTERN]))
        self.assertEqual(sorted(hits), [
            "安徽省合肥市庐阳区XX路88号",
            "安徽省池州市贵池区牛头山镇川山组",
        ])


class _StubCfg:
    """_ensure_preset_rule 的 stub 配置对象（不触碰真实 config.json）。

    rules=None 模拟 get_redaction_rules 返回非 dict（真实 SimpleConfig
    恒返回 dict，此为理论防御分支）。
    """

    def __init__(self, rules=None):
        self._rules = rules
        self.set_calls = []

    def get_redaction_rules(self):
        return self._rules

    def set(self, key, value, persist=True):
        self.set_calls.append((key, value, persist))
        self._rules["住址"] = value


@unittest.skipUnless(HAS_DEPS, "依赖未安装")
class TestEnsureAddressRuleMigration(unittest.TestCase):
    """cp135 老配置注入迁移（通用函数）。"""

    def test_injects_when_missing(self):
        cfg = _StubCfg({"身份证号": {"pattern": "x", "enabled": True}})
        self.assertTrue(_ensure_preset_rule(
            cfg, "住址", ADDRESS_RULE_PATTERN, "desc"))
        self.assertEqual(len(cfg.set_calls), 1)
        key, value, persist = cfg.set_calls[0]
        self.assertEqual(key, "redaction.default_rules.住址")
        self.assertEqual(value["pattern"], ADDRESS_RULE_PATTERN)
        self.assertTrue(value["enabled"])
        self.assertTrue(persist)

    def test_no_overwrite_when_exists(self):
        # 用户已有同名规则（自定义或已注入）不覆盖
        custom = {"pattern": "自定义", "enabled": False}
        cfg = _StubCfg({"住址": custom})
        self.assertFalse(_ensure_preset_rule(
            cfg, "住址", ADDRESS_RULE_PATTERN, "desc"))
        self.assertEqual(cfg.set_calls, [])
        self.assertEqual(cfg._rules["住址"], custom)

    def test_none_cfg(self):
        self.assertFalse(_ensure_preset_rule(
            None, "住址", ADDRESS_RULE_PATTERN, "desc"))

    def test_non_dict_rules(self):
        self.assertFalse(_ensure_preset_rule(
            _StubCfg(rules=None), "住址", ADDRESS_RULE_PATTERN, "desc"))


if __name__ == "__main__":
    unittest.main()
