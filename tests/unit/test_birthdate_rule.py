# -*- coding: utf-8 -*-
"""cp135 回归测试：出生年月预设规则（出生信息+日期整体遮罩）

覆盖：
1. 用户需求四种模式的正例：
   - 标签+日期：出生年月：1990年1月1日 / 出生年月日 / 出生日期 变体
   - 出生于+日期：出生于1990年1月1日 / 出生于1990年1月
   - 日期+出生：1990年1月1日出生 / 1990年1月出生
   - 日期+生：1990年12月11日生 / 1990年12月生（cp135 追加）
2. 日期格式变体：中文年月日（含/不含日）、分隔符式（1990-1-1 / 1990.1.1）
3. 负例（不误伤）：出生年月不详、纯日期、出生地、出生体重、生产/生效（"生"后接汉字）
4. DEFAULT_RULES / iter_unique_text_matches 集成
5. _ensure_birthdate_rule 老配置注入迁移（stub cfg，不触碰真实 config.json）
6. _upgrade_legacy_birthdate_rule 初版正则升级迁移
"""
import re
import unittest

try:
    from main import (
        BIRTHDATE_RULE_PATTERN, DEFAULT_RULES, _ensure_birthdate_rule,
        _upgrade_legacy_birthdate_rule, LEGACY_BIRTHDATE_RULE_PATTERN,
    )
    from privacyguard.ocr.text_pdf import iter_unique_text_matches
    HAS_DEPS = True
except Exception:  # pragma: no cover - PyQt6/依赖缺失时跳过
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "依赖未安装")
class TestBirthdateRulePositive(unittest.TestCase):
    """正例：应整体命中（标签/出生字样+日期一起遮）。"""

    def _match(self, text):
        m = re.search(BIRTHDATE_RULE_PATTERN, text)
        return m.group() if m else None

    def test_label_with_colon_full_date(self):
        # 用户原例 1：出生年月：1990年1月1日
        self.assertEqual(self._match("出生年月：1990年1月1日"), "出生年月：1990年1月1日")

    def test_label_with_ri_suffix(self):
        # 出生年月日变体
        self.assertEqual(self._match("出生年月日：1990年1月1日"), "出生年月日：1990年1月1日")

    def test_label_chusheng_riqi(self):
        # 出生日期变体（同类标签）
        self.assertEqual(self._match("出生日期：1990年1月1日"), "出生日期：1990年1月1日")

    def test_chushengyu_full_date(self):
        # 用户原例 2：出生于1990年1月1日
        self.assertEqual(self._match("出生于1990年1月1日"), "出生于1990年1月1日")

    def test_chushengyu_month_only(self):
        # 用户原例 3：出生于1990年1月
        self.assertEqual(self._match("出生于1990年1月"), "出生于1990年1月")

    def test_date_then_chusheng_full(self):
        # 用户原例 4：1990年1月1日出生
        self.assertEqual(self._match("1990年1月1日出生"), "1990年1月1日出生")

    def test_date_then_chusheng_month_only(self):
        # 用户原例 5：1990年1月出生
        self.assertEqual(self._match("1990年1月出生"), "1990年1月出生")

    def test_date_then_sheng_full(self):
        # cp135 追加（用户原例）：1990年12月11日生（日期+单"生"）
        self.assertEqual(self._match("1990年12月11日生"), "1990年12月11日生")

    def test_date_then_sheng_month_only(self):
        # 日期+单"生"，月级日期
        self.assertEqual(self._match("1990年12月生"), "1990年12月生")

    def test_date_then_sheng_in_context(self):
        # 嵌入当事人身份段："…1990年12月11日生，汉族…"（"生"后接标点）
        text = "张三，男，1990年12月11日生，汉族，住安徽省池州市。"
        self.assertEqual(self._match(text), "1990年12月11日生")

    def test_date_then_sheng_separator_style(self):
        # 分隔符式日期+单"生"
        self.assertEqual(self._match("1990-12-11生"), "1990-12-11生")
        self.assertEqual(self._match("1990.12.11生"), "1990.12.11生")

    def test_chusheng_with_place_no_regression(self):
        # 回归：完整"出生"后接地点仍整体命中（"出生于合肥市"句式）
        text = "张三于1990年1月1日出生于合肥市庐阳区。"
        self.assertEqual(self._match(text), "1990年1月1日出生")

    def test_halfwidth_colon_and_space(self):
        # 半角冒号 + 空格
        self.assertEqual(self._match("出生年月: 1990年1月1日"), "出生年月: 1990年1月1日")

    def test_separator_style_date(self):
        # 分隔符式日期：1990.1.1 / 1990-1-1
        self.assertEqual(self._match("出生于1990.1.1"), "出生于1990.1.1")
        self.assertEqual(self._match("1990-1-1出生"), "1990-1-1出生")

    def test_in_context_sentence(self):
        # 嵌入当事人身份段（法律文书高频句式）
        text = "原告张三，男，1970年3月5日出生，汉族，住安徽省池州市。"
        self.assertEqual(self._match(text), "1970年3月5日出生")

    def test_in_context_label(self):
        # 表格式字段
        text = "姓名：张三    出生年月：1965年12月    学历：本科"
        self.assertEqual(self._match(text), "出生年月：1965年12月")


@unittest.skipUnless(HAS_DEPS, "依赖未安装")
class TestBirthdateRuleNegative(unittest.TestCase):
    """负例：无日期邻接时不命中，避免误伤。"""

    def _match(self, text):
        m = re.search(BIRTHDATE_RULE_PATTERN, text)
        return m.group() if m else None

    def test_label_without_date(self):
        # 标签后无日期（"出生年月不详"）不命中
        self.assertIsNone(self._match("出生年月不详"))

    def test_label_unknown_value(self):
        self.assertIsNone(self._match("出生年月：不详"))

    def test_plain_date_no_birth(self):
        # 纯日期（落款等）不含"出生"字样，不命中（仍由"日期时间"规则处理）
        self.assertIsNone(self._match("本判决书落款日期2023年5月1日"))

    def test_birthplace(self):
        # 出生地（"出生"后跟"地"非日期/冒号）
        self.assertIsNone(self._match("出生地：安徽省池州市"))

    def test_birth_weight(self):
        # 出生体重（数字后无日期结构）
        self.assertIsNone(self._match("新生儿出生体重3500克"))

    def test_year_only_no_month(self):
        # 仅年份无月份，不构成完整日期
        self.assertIsNone(self._match("出生于1990年"))

    def test_sheng_production_not_matched(self):
        # cp135 模式④防误报："生"后接"产"（生产）不命中
        self.assertIsNone(self._match("该批次产品于2020年1月1日生产合格"))

    def test_sheng_effective_not_matched(self):
        # cp135 模式④防误报："生"后接"效"（生效）不命中（判决书高频句式）
        self.assertIsNone(self._match("本判决自2023年5月1日生效"))

    def test_idcard_number_not_matched(self):
        # 身份证号内嵌数字无"年/月"字样、无分隔符，不命中
        self.assertIsNone(self._match("身份证号340104199001010011"))


@unittest.skipUnless(HAS_DEPS, "依赖未安装")
class TestBirthdateRuleIntegration(unittest.TestCase):
    """集成：DEFAULT_RULES 注册 + 文本层命中收集。"""

    def test_registered_in_default_rules(self):
        # config.json（经 cp135 迁移注入）加载后 DEFAULT_RULES 应含此规则
        self.assertEqual(DEFAULT_RULES.get("出生年月"), BIRTHDATE_RULE_PATTERN)

    def test_iter_unique_text_matches_hit(self):
        text = "被告李四，女，1985年7月12日出生，住安徽省合肥市。"
        hits = list(iter_unique_text_matches(text, [BIRTHDATE_RULE_PATTERN]))
        self.assertIn("1985年7月12日出生", hits)

    def test_iter_unique_text_matches_no_hit(self):
        hits = list(iter_unique_text_matches("出生年月不详，详见卷宗。", [BIRTHDATE_RULE_PATTERN]))
        self.assertEqual(hits, [])

    def test_multiple_hits_deduped(self):
        # 同一命中串去重；两处不同出生信息各自命中
        text = "原告1970年3月5日出生，被告1985年7月12日出生。"
        hits = list(iter_unique_text_matches(text, [BIRTHDATE_RULE_PATTERN]))
        self.assertEqual(sorted(hits), ["1970年3月5日出生", "1985年7月12日出生"])


class _StubCfg:
    """_ensure_birthdate_rule 的 stub 配置对象（不触碰真实 config.json）。

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
        self._rules["出生年月"] = value


@unittest.skipUnless(HAS_DEPS, "依赖未安装")
class TestEnsureBirthdateRuleMigration(unittest.TestCase):
    """cp135 老配置注入迁移。"""

    def test_injects_when_missing(self):
        cfg = _StubCfg({"身份证号": {"pattern": "x", "enabled": True}})
        self.assertTrue(_ensure_birthdate_rule(cfg))
        self.assertEqual(len(cfg.set_calls), 1)
        key, value, persist = cfg.set_calls[0]
        self.assertEqual(key, "redaction.default_rules.出生年月")
        self.assertEqual(value["pattern"], BIRTHDATE_RULE_PATTERN)
        self.assertTrue(value["enabled"])
        self.assertTrue(persist)

    def test_no_overwrite_when_exists(self):
        # 用户已有同名规则（自定义或已注入）不覆盖
        custom = {"pattern": "自定义", "enabled": False}
        cfg = _StubCfg({"出生年月": custom})
        self.assertFalse(_ensure_birthdate_rule(cfg))
        self.assertEqual(cfg.set_calls, [])
        self.assertEqual(cfg._rules["出生年月"], custom)

    def test_none_cfg(self):
        self.assertFalse(_ensure_birthdate_rule(None))

    def test_non_dict_rules(self):
        self.assertFalse(_ensure_birthdate_rule(_StubCfg(rules=None)))


@unittest.skipUnless(HAS_DEPS, "依赖未安装")
class TestUpgradeLegacyBirthdateRule(unittest.TestCase):
    """cp135 初版正则升级迁移（新增 日期+单"生" 模式）。"""

    def _cfg_with_pattern(self, pattern):
        rules = {} if pattern is None else {
            "出生年月": {"pattern": pattern, "enabled": True, "description": "d"}}
        cfg = _StubCfg(rules)
        return cfg

    def test_upgrades_legacy_pattern(self):
        # 旧正则原值 → 升级为新正则
        cfg = self._cfg_with_pattern(LEGACY_BIRTHDATE_RULE_PATTERN)
        self.assertTrue(_upgrade_legacy_birthdate_rule(cfg))
        self.assertEqual(len(cfg.set_calls), 1)
        key, value, persist = cfg.set_calls[0]
        self.assertEqual(key, "redaction.default_rules.出生年月.pattern")
        self.assertEqual(value, BIRTHDATE_RULE_PATTERN)
        self.assertTrue(persist)

    def test_new_pattern_already_upgraded(self):
        # 已是新正则 → 不动
        cfg = self._cfg_with_pattern(BIRTHDATE_RULE_PATTERN)
        self.assertFalse(_upgrade_legacy_birthdate_rule(cfg))
        self.assertEqual(cfg.set_calls, [])

    def test_custom_pattern_untouched(self):
        # 用户自定义正则（非旧值非新值）→ 不动
        cfg = self._cfg_with_pattern("自定义正则")
        self.assertFalse(_upgrade_legacy_birthdate_rule(cfg))
        self.assertEqual(cfg.set_calls, [])

    def test_rule_missing(self):
        # 规则不存在（注入路径负责）→ 不动
        cfg = self._cfg_with_pattern(None)
        self.assertFalse(_upgrade_legacy_birthdate_rule(cfg))
        self.assertEqual(cfg.set_calls, [])

    def test_none_cfg(self):
        self.assertFalse(_upgrade_legacy_birthdate_rule(None))

    def test_non_dict_rules(self):
        self.assertFalse(_upgrade_legacy_birthdate_rule(_StubCfg(rules=None)))

    def test_legacy_and_new_patterns_differ(self):
        # 前置校验：新旧正则必须是不同字符串（防止常量复制错误导致升级失效）
        self.assertNotEqual(LEGACY_BIRTHDATE_RULE_PATTERN, BIRTHDATE_RULE_PATTERN)


if __name__ == "__main__":
    unittest.main()
