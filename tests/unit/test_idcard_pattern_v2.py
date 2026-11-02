"""v37.7.18 cp49: 验证收紧后的身份证号正则。

确保：
1. 真实身份证号（18/15 位）能正常匹配
2. 误识别场景（17 位无关数字串、案件号、电话拼接、含横线、非法地区码、非法月日等）不再匹配
3. main.py 与 config.json 与 privacyguard/utils/config.py 三处正则一致
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_config_json_pattern():
    config_path = ROOT / "config.json"
    if not config_path.exists():
        config_path = ROOT / "config.json.template"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["redaction"]["default_rules"]["身份证号"]["pattern"]


def _load_default_config_pattern():
    from privacyguard.utils.config import DEFAULT_CONFIG
    return DEFAULT_CONFIG["redaction"]["default_rules"]["身份证号"]["pattern"]


class TestIdCardPatternV2(unittest.TestCase):
    """v37.7.18 cp49: 身份证号正则收紧验证。"""

    @classmethod
    def setUpClass(cls):
        cls.config_json_pattern = _load_config_json_pattern()
        cls.default_config_pattern = _load_default_config_pattern()
        cls.config_json_re = re.compile(cls.config_json_pattern, re.IGNORECASE)
        cls.default_config_re = re.compile(cls.default_config_pattern, re.IGNORECASE)

    def test_three_pattern_sources_are_consistent(self):
        """main.py 内置 / config.json / DEFAULT_CONFIG 三处身份证号正则必须一致。"""
        # 跳过 PyQt6.QtWebEngineWidgets 不可用时的导入失败
        try:
            from main import DEFAULT_RULES
            main_pattern = DEFAULT_RULES.get("身份证号", "")
        except ImportError:
            self.skipTest("main.py 依赖 PyQt6.QtWebEngineWidgets，跳过此测试")
            return
        self.assertEqual(main_pattern, self.config_json_pattern,
            "main.py DEFAULT_RULES 与 config.json 中的身份证号正则不一致")
        self.assertEqual(self.default_config_pattern, self.config_json_pattern,
            "DEFAULT_CONFIG 与 config.json 中的身份证号正则不一致")

    def test_legacy_loose_15_branch_is_replaced(self):
        """旧宽松正则的 15 位分支 \\d{15} 必须已被替换。"""
        self.assertNotIn(r"\d{15}", self.config_json_pattern,
            "config.json 中仍包含旧宽松 15 位分支 \\d{15}")

    def _check(self, text, expected_count):
        """对两个正则源都做相同期望验证。"""
        self.assertEqual(
            len(self.config_json_re.findall(text)),
            expected_count,
            f"config.json 正则匹配 {text!r} 期望 {expected_count}，实际 {len(self.config_json_re.findall(text))}",
        )
        self.assertEqual(
            len(self.default_config_re.findall(text)),
            expected_count,
            f"DEFAULT_CONFIG 正则匹配 {text!r} 期望 {expected_count}，实际 {len(self.default_config_re.findall(text))}",
        )

    def test_real_18_digit_idcard_matches(self):
        """18 位真实身份证号应正常匹配。"""
        self._check("身份证号 342921197811302719 已登记", 1)
        self._check("110101199001012345", 1)
        self._check("11010119900101234X", 1)

    def test_real_15_digit_idcard_matches(self):
        """15 位旧版身份证号应正常匹配（保留兼容性）。"""
        self._check("老身份证 342921780130271", 1)
        self._check("110101800102345", 1)

    def test_17_digit_unrelated_digits_not_matched(self):
        """17 位无关数字串不应匹配（诊断中实际出现的 13417202010172812）。"""
        self._check("13417202010172812", 0)

    def test_phone_number_not_matched(self):
        """11 位手机号不应匹配。"""
        self._check("电话 13417202010", 0)

    def test_hyphen_separated_digits_not_matched(self):
        """含横线/连字符的数字串不应匹配（避免 OCR 把横线识别为 1 后误匹配）。"""
        self._check("342921-1978-1130-2719", 0)
        self._check("2024-01-17 案件", 0)

    def test_bank_card_number_not_matched(self):
        """13-19 位银行卡号不应匹配。"""
        self._check("6225750000000000", 0)  # 16 位
        self._check("6225750000000000000", 0)  # 19 位

    def test_unrelated_digit_strings_not_matched(self):
        """12/14/16/17 位无关数字串不应匹配。"""
        self._check("123456789012", 0)  # 12 位
        self._check("12345678901234", 0)  # 14 位
        self._check("1234567890123456", 0)  # 16 位
        self._check("12345678901234567", 0)  # 17 位

    def test_invalid_province_prefix_not_matched(self):
        """前缀 71/81/91 等未启用地区码不应匹配（旧正则会误匹配）。"""
        self._check("710101800102345", 0)  # 71 台湾未启用
        self._check("810101800102345", 0)  # 81 香港未启用
        self._check("910101800102345", 0)  # 91 不存在

    def test_invalid_month_not_matched(self):
        """月份 13/00 不应匹配。"""
        self._check("110101801330345", 0)  # 13 月
        self._check("110101800030345", 0)  # 00 月

    def test_invalid_day_not_matched(self):
        """日期 32/00 不应匹配。"""
        self._check("110101800132345", 0)  # 32 日
        self._check("110101800100345", 0)  # 00 日

    def test_idcard_in_text_context(self):
        """身份证号在中文上下文中应正常匹配。"""
        self._check("请将342921197811302719于明日提交", 1)


if __name__ == "__main__":
    unittest.main()
