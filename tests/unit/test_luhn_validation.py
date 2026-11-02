"""v37.7.19 cp58: Luhn 算法与银行卡号识别作用域单元测试

验证：
1. _is_valid_luhn 对真实银行卡号返回 True，对案件编号/日期串/电话拼接返回 False
2. _looks_like_idcard 准确识别 15/18 位身份证号，避免被 Luhn 校验误伤
3. _is_bank_card_pattern 精确限定 Luhn 校验仅对银行卡号正则生效，
   不影响用户自定义正则（如身份证、电话、邮箱）
4. _is_valid_luhn 对异常输入（空串/含字母/非字符串）安全返回 False，不抛异常
"""
import unittest

from privacyguard.ocr.text_pdf import (
    _is_valid_luhn,
    _looks_like_idcard,
    _is_bank_card_pattern,
)


class TestLuhnValidation(unittest.TestCase):
    """Luhn 算法核心实现验证。"""

    # === 有效银行卡号（Luhn 校验通过，均为公开测试卡号）===
    VALID_BANK_CARDS = [
        "4111111111111111",  # Visa 测试卡（16位）
        "4242424242424242",  # Visa 测试卡（16位）
        "5555555555554444",  # Mastercard 测试卡（16位）
        "378282246310005",   # Amex 测试卡（15位）
        "6011111111111117",  # Discover 测试卡（16位）
        "6200000000000005",  # UnionPay 测试卡（16位）
    ]

    # === 无效数字串（Luhn 校验不通过）===
    # 案件编号、日期串、电话拼接、统计号等不应被当作银行卡号
    INVALID_NUMBER_STRINGS = [
        "13417202010172812",   # 案件编号（用户实际反馈案例）
        "20260320153000",      # 日期时间串
        "20260320",            # 8 位日期
        "1391234567812",       # 电话拼接扩展
        "1234567890123",       # 顺序数字串
        "1111111111111",       # 全 1
        "9999999999999",       # 全 9
        "1234567890123456",    # 16 位顺序数
    ]

    def test_valid_bank_cards_pass_luhn(self):
        """真实银行卡号应通过 Luhn 校验。"""
        for card in self.VALID_BANK_CARDS:
            with self.subTest(card=card):
                self.assertTrue(
                    _is_valid_luhn(card),
                    f"有效银行卡号 {card} 应通过 Luhn 校验",
                )

    def test_invalid_number_strings_fail_luhn(self):
        """案件编号/日期串等非银行卡号应被 Luhn 校验过滤。"""
        for s in self.INVALID_NUMBER_STRINGS:
            with self.subTest(s=s):
                self.assertFalse(
                    _is_valid_luhn(s),
                    f"非银行卡号 '{s}' 应被 Luhn 校验过滤",
                )

    def test_luhn_safe_on_empty_string(self):
        """空串应安全返回 False，不抛异常。"""
        self.assertFalse(_is_valid_luhn(""))

    def test_luhn_safe_on_non_digit_chars(self):
        """含字母/符号的串应安全返回 False。"""
        self.assertFalse(_is_valid_luhn("abcd1234"))
        self.assertFalse(_is_valid_luhn("6222-0202-0001-1111-111"))
        self.assertFalse(_is_valid_luhn("6222 0202 0001 1111 111"))

    def test_luhn_safe_on_non_string_input(self):
        """非字符串输入应安全返回 False，不抛异常。"""
        self.assertFalse(_is_valid_luhn(None))
        self.assertFalse(_is_valid_luhn(6222020200011111111))
        self.assertFalse(_is_valid_luhn([]))

    def test_luhn_short_number(self):
        """短于 13 位的数字串应安全返回（虽非典型银行卡号，Luhn 算法仍可计算）。"""
        # 单位数 0 满足 Luhn，但调用方按长度过滤
        self.assertTrue(_is_valid_luhn("0"))
        # "18" → 1*2=2, 8 → sum=10 → 通过
        self.assertTrue(_is_valid_luhn("18"))


class TestIdCardExclusion(unittest.TestCase):
    """身份证号排除：避免被 Luhn 校验误伤。"""

    # === 真实身份证号格式（省级前缀 + 年月日）===
    VALID_IDCARDS_18 = [
        "340101199001010012",   # 18 位标准
        "110101199003072345",   # 北京
        "440101198512128888",   # 广东
        "510101200001015555",   # 四川
    ]
    VALID_IDCARDS_15 = [
        "340101900101001",   # 15 位（2 位年）
        "110101990301123",   # 北京 15 位
    ]

    # === 非身份证号格式 ===
    NON_IDCARDS = [
        "13417202010172812",   # 案件编号（不符合省级前缀+日期结构）
        "6222020200011111111", # 银行卡号
        "20260320153000",      # 日期时间串
        "123456789012345678",  # 顺序数字串（11 开头但年月日不合法）
    ]

    def test_valid_18_digit_idcards_recognized(self):
        """18 位身份证号应被 _looks_like_idcard 识别。"""
        for idc in self.VALID_IDCARDS_18:
            with self.subTest(idc=idc):
                self.assertTrue(
                    _looks_like_idcard(idc),
                    f"18 位身份证号 {idc} 应被识别为身份证号格式",
                )

    def test_valid_15_digit_idcards_recognized(self):
        """15 位身份证号应被 _looks_like_idcard 识别（避免被 Luhn 误伤）。"""
        for idc in self.VALID_IDCARDS_15:
            with self.subTest(idc=idc):
                self.assertTrue(
                    _looks_like_idcard(idc),
                    f"15 位身份证号 {idc} 应被识别为身份证号格式",
                )

    def test_non_idcards_not_recognized(self):
        """案件编号/银行卡号/日期串不应被识别为身份证号。"""
        for s in self.NON_IDCARDS:
            with self.subTest(s=s):
                self.assertFalse(
                    _looks_like_idcard(s),
                    f"'{s}' 不应被识别为身份证号格式",
                )

    def test_idcard_with_x_suffix_recognized(self):
        """末位为 X 的身份证号应被识别。"""
        self.assertTrue(_looks_like_idcard("34010119900101001X"))
        self.assertTrue(_looks_like_idcard("34010119900101001x"))

    def test_invalid_province_prefix_not_idcard(self):
        """非法省级前缀（如 16/19/24 开头）不应被识别为身份证号。"""
        self.assertFalse(_looks_like_idcard("160101199001010012"))
        self.assertFalse(_looks_like_idcard("190101199001010012"))
        self.assertFalse(_looks_like_idcard("240101199001010012"))

    def test_invalid_date_not_idcard(self):
        """非法月份/日期不应被识别为身份证号。"""
        self.assertFalse(_looks_like_idcard("340101199013010012"))  # 月 13
        self.assertFalse(_looks_like_idcard("340101199000010012"))  # 月 00
        self.assertFalse(_looks_like_idcard("340101199001320012"))  # 日 32
        self.assertFalse(_looks_like_idcard("340101199001000012"))  # 日 00


class TestBankCardPatternScope(unittest.TestCase):
    """Luhn 校验作用域：仅银行卡号 pattern 生效，避免过滤自定义正则。"""

    # === 银行卡号 pattern（应触发 Luhn 校验）===
    BANK_CARD_PATTERNS = [
        r"(?<!\d)([1-9]\d{12,18})(?!\d)",                 # config.json 默认
        r"[1-9]\d{12,18}",                                # 简化版
        r"\b[1-9]\d{14,18}\b",                            # 带字边界
        r"(?<!\d)[1-9]\d{15,18}(?!\d)",                   # 16-19 位
    ]

    # === 非银行卡号 pattern（不应触发 Luhn 校验）===
    NON_BANK_CARD_PATTERNS = [
        r"(?<!\d)(?:1[1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4]|6[1-5])\d{4}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)",  # 身份证
        r"(?<!\d)1[3-9]\d{9}(?!\d)",                     # 手机号
        r"\b\d{4}-\d{2}-\d{2}\b",                        # 日期
        r"[\w.+-]+@[\w-]+\.[\w.-]+",                     # 邮箱
        r"张三|李四",                                    # 自定义关键词
        r"\d{8}",                                        # 8 位数字（非银行卡）
        r"",                                              # 空 pattern
    ]

    def test_bank_card_patterns_detected(self):
        """银行卡号 pattern 应被 _is_bank_card_pattern 识别。"""
        for p in self.BANK_CARD_PATTERNS:
            with self.subTest(p=p):
                self.assertTrue(
                    _is_bank_card_pattern(p),
                    f"银行卡号 pattern '{p}' 应被识别",
                )

    def test_non_bank_card_patterns_not_detected(self):
        """非银行卡号 pattern 不应被 _is_bank_card_pattern 识别。"""
        for p in self.NON_BANK_CARD_PATTERNS:
            with self.subTest(p=p):
                self.assertFalse(
                    _is_bank_card_pattern(p),
                    f"非银行卡号 pattern '{p}' 不应被识别",
                )

    def test_pattern_scope_non_string_safe(self):
        """非字符串 pattern 应安全返回 False。"""
        self.assertFalse(_is_bank_card_pattern(None))
        self.assertFalse(_is_bank_card_pattern(123))
        self.assertFalse(_is_bank_card_pattern([]))
        self.assertFalse(_is_bank_card_pattern(b"[1-9]\\d{12,18}"))


class TestIterUniqueTextMatchesLuhn(unittest.TestCase):
    """iter_unique_text_matches 集成测试：Luhn 校验应过滤无效银行卡号。

    cp57 关键修复：仅对银行卡号 pattern 生效，不影响其他 pattern。
    """
    BANK_PATTERN = r"(?<!\d)([1-9]\d{12,18})(?!\d)"

    def test_bank_card_pattern_filters_invalid_luhn_numbers(self):
        """银行卡号 pattern 下，案件编号/日期串应被 Luhn 校验过滤。"""
        from privacyguard.ocr.text_pdf import iter_unique_text_matches
        text = "案件编号 13417202010172812 已立案"
        results = list(iter_unique_text_matches(text, [self.BANK_PATTERN]))
        self.assertNotIn(
            "13417202010172812",
            results,
            "案件编号应被 Luhn 校验过滤",
        )

    def test_bank_card_pattern_keeps_valid_luhn_numbers(self):
        """银行卡号 pattern 下，真实银行卡号应被保留。"""
        from privacyguard.ocr.text_pdf import iter_unique_text_matches
        valid_card = "4111111111111111"  # Visa 公开测试卡（Luhn 校验通过）
        text = f"账户 {valid_card} 收款"
        results = list(iter_unique_text_matches(text, [self.BANK_PATTERN]))
        self.assertIn(
            valid_card,
            results,
            "真实银行卡号应被保留",
        )

    def test_bank_card_pattern_keeps_idcards(self):
        """银行卡号 pattern 下，身份证号应被保留（_looks_like_idcard 排除 Luhn）。"""
        from privacyguard.ocr.text_pdf import iter_unique_text_matches
        idcard = "340101199001010012"
        text = f"身份证 {idcard}"
        results = list(iter_unique_text_matches(text, [self.BANK_PATTERN]))
        self.assertIn(
            idcard,
            results,
            "身份证号应被保留（不参与 Luhn 校验）",
        )

    def test_non_bank_card_pattern_not_filtered_by_luhn(self):
        """非银行卡号 pattern 不应触发 Luhn 校验。

        cp57 关键修复：避免用户自定义正则恰好匹配 13-19 位数字串时被误过滤。
        """
        from privacyguard.ocr.text_pdf import iter_unique_text_matches
        # 自定义 pattern 匹配 13-19 位数字串（非银行卡号 pattern）
        custom_pattern = r"\d{13,19}"
        case_number = "13417202010172812"
        text = f"案件编号 {case_number}"
        results = list(iter_unique_text_matches(text, [custom_pattern]))
        self.assertIn(
            case_number,
            results,
            "非银行卡号 pattern 不应触发 Luhn 校验",
        )

    def test_deduplication_still_works(self):
        """Luhn 校验后去重逻辑仍正常工作。"""
        from privacyguard.ocr.text_pdf import iter_unique_text_matches
        valid_card = "4111111111111111"  # Visa 公开测试卡
        text = f"{valid_card} {valid_card} {valid_card}"
        results = list(iter_unique_text_matches(text, [self.BANK_PATTERN]))
        self.assertEqual(
            len(results),
            1,
            "重复出现的银行卡号应被去重",
        )


if __name__ == "__main__":
    unittest.main()
