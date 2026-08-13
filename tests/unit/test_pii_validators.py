"""Phase 1 PII validators 单元测试（NUM-01 / NUM-02 / NUM-03 覆盖率）。

覆盖矩阵：
- NUM-01 18 位 + 15 位身份证号 GB 11643 mod-11-2 校验
- NUM-02 末位大小写 X 兼容（OCR 小写 x 归一化）
- NUM-03 中国大陆手机号段号白名单 + 14X IoT/卫星排除

B1 second gate（15 位升级后）：行政区划码 2 位前缀 + 真实日历日期。
"""
import unittest

from privacyguard.pii.validators.id_card import (
    compute_check_digit,
    is_real_calendar_date,
    is_valid_admin_division_prefix_2,
    upgrade_15_to_18,
    validate_15,
    validate_18,
)
from privacyguard.pii.validators.phone_segment import (
    PHONE_EXCLUDED_PREFIX_3,
    PHONE_EXCLUDED_PREFIX_4,
    PHONE_PERSONAL_PREFIX_3,
    is_mobile_segment,
)


# GB 11643-1999 标准样本：53010219200508011X
_GB_STD_18 = "53010219200508011X"
_GB_STD_18_INVALID = "530102192005080119"  # 校验位错误

# 真实合法 15 位（420106=湖北宜昌市，1969-09-01 真实日历）
_REAL_15 = "420106690901234"

# 真实合法 18 位（GB 标准样本升级版）
_REAL_18_FROM_15 = "420106196909012345"  # 占位，下面重新计算正确校验位


def _upgrade_with_check(id15: str) -> str:
    """手工升级 15 位并附加校验位（测试 helper）。"""
    body17 = id15[:6] + "19" + id15[6:]
    return body17 + compute_check_digit(body17)


_REAL_18_FROM_15 = _upgrade_with_check(_REAL_15)


class TestIdCardChecksum(unittest.TestCase):
    """NUM-01: 18 位 GB 11643 mod-11-2 校验位正向 + 反向。"""

    def test_valid_18_passes_checksum(self):
        self.assertTrue(validate_18(_GB_STD_18))

    def test_invalid_check_digit_fails(self):
        self.assertFalse(validate_18(_GB_STD_18_INVALID))

    def test_lowercase_x_accepted_via_upper(self):
        """NUM-02: OCR 输出的 'x' 经归一化后通过校验。"""
        self.assertTrue(validate_18(_GB_STD_18.replace("X", "x")))

    def test_corrupted_body_fails(self):
        """前 17 位含非数字必须 False。"""
        self.assertFalse(validate_18("53010A19200508011X"))

    def test_short_id_rejected(self):
        self.assertFalse(validate_18("123"))

    def test_long_id_rejected(self):
        self.assertFalse(validate_18("1" * 19))

    def test_empty_string_rejected(self):
        self.assertFalse(validate_18(""))

    def test_last_char_invalid_rejected(self):
        """NUM-02: 末位非 [0-9Xx] 必须 False。"""
        self.assertFalse(validate_18("53010219200508011Z"))

    def test_15_digit_input_rejected_by_validate_18(self):
        """validate_18 不接受 15 位（15 位由 validate_15 处理）。"""
        self.assertFalse(validate_18(_REAL_15))


class TestIdCardUpgrade15To18(unittest.TestCase):
    """NUM-01: 15 位 → 18 位升级 + 双门（B1）守卫。"""

    def test_15_digit_upgrades_to_valid_18(self):
        upgraded = upgrade_15_to_18(_REAL_15)
        self.assertEqual(len(upgraded), 18)
        self.assertTrue(validate_18(upgraded))

    def test_15_digit_century_prefix_is_19(self):
        upgraded = upgrade_15_to_18("110101800101001")
        # 11=北京，01=市辖区，01=区，800101=1980-01-01，001=序
        self.assertTrue(upgraded.startswith("11010119"))

    def test_non_15_digit_returns_empty(self):
        self.assertEqual(upgrade_15_to_18("123"), "")

    def test_non_digit_15_rejected(self):
        self.assertEqual(upgrade_15_to_18("42010696090123A"), "")

    def test_validate_15_passes_for_valid_upgraded(self):
        self.assertTrue(validate_15(_REAL_15))

    def test_15_digit_invalid_province_prefix_rejected(self):
        """B1: '99' 不在行政区划白名单 → False。"""
        self.assertFalse(validate_15("990106800101001"))

    def test_15_digit_zero_province_prefix_rejected(self):
        """B1: '00' 不在白名单 → False（订单号 / 序列号常见前缀）。"""
        self.assertFalse(validate_15("000106800101001"))

    def test_15_digit_impossible_month_rejected(self):
        """B1: 月份 13 → False（不可能日历日期）。"""
        self.assertFalse(validate_15("420106801301001"))

    def test_15_digit_impossible_day_rejected(self):
        """B1: 日期 32 → False（不可能日历日期）。"""
        self.assertFalse(validate_15("420106800132001"))

    def test_15_digit_feb_30_rejected(self):
        """B1: 2 月 30 日 → False（公历不存在 2-30）。"""
        self.assertFalse(validate_15("420106800230001"))

    def test_is_valid_admin_division_prefix_2_whitelist(self):
        """B1: 行政区划前缀白名单（含 / 不含）。"""
        self.assertTrue(is_valid_admin_division_prefix_2("11"))  # 北京
        self.assertTrue(is_valid_admin_division_prefix_2("82"))  # 澳门
        self.assertFalse(is_valid_admin_division_prefix_2("00"))  # 非法
        self.assertFalse(is_valid_admin_division_prefix_2("90"))  # 非法
        self.assertFalse(is_valid_admin_division_prefix_2("99"))  # 非法

    def test_is_real_calendar_date_boundary(self):
        """B1: 真实日历日期边界（含闰年 / 月份边界 / 2-29 / 4-30）。"""
        self.assertTrue(is_real_calendar_date(85, 1, 1))    # 元旦
        # 1984（yy=84）是闰年，2-29 合法；1985（yy=85）非闰年，2-29 非法
        self.assertTrue(is_real_calendar_date(84, 2, 29))   # 1984 闰年
        self.assertFalse(is_real_calendar_date(85, 2, 29))  # 1985 非闰年
        self.assertFalse(is_real_calendar_date(85, 13, 1))  # 月份超界
        self.assertFalse(is_real_calendar_date(85, 1, 32))  # 日期超界
        # 4 月 30 天 → 4-30 合法
        self.assertTrue(is_real_calendar_date(85, 4, 30))
        # 4 月无 31 → 4-31 非法
        self.assertFalse(is_real_calendar_date(85, 4, 31))
        self.assertFalse(is_real_calendar_date(85, 2, 30))  # 2 月无 30


class TestIdCaseInsensitiveX(unittest.TestCase):
    """NUM-02: 末位 X / OCR 小写 x 全路径兼容。"""

    def test_uppercase_X_passes(self):
        self.assertTrue(validate_18(_GB_STD_18))

    def test_lowercase_x_passes(self):
        self.assertTrue(validate_18(_GB_STD_18.replace("X", "x")))

    def test_invalid_letter_rejected(self):
        self.assertFalse(validate_18("53010219200508011Y"))


class TestIdCardDefensive(unittest.TestCase):
    """NUM-01: 防御性输入（None / 非字符串 / 异常类型）。"""

    def test_none_rejected(self):
        self.assertFalse(validate_18(None))  # type: ignore[arg-type]

    def test_int_rejected(self):
        self.assertFalse(validate_18(123456789012345678))  # type: ignore[arg-type]


class TestPhoneSegment(unittest.TestCase):
    """NUM-03: 中国大陆手机号段号白名单正向覆盖。"""

    def test_personal_segment_recognized(self):
        # 至少覆盖 30 个号段；每个接 8 位随机数字
        personal_prefixes = sorted(PHONE_PERSONAL_PREFIX_3)
        self.assertGreaterEqual(
            len(personal_prefixes),
            30,
            f"personal_prefix_3 仅有 {len(personal_prefixes)} 段，需 ≥30 段覆盖",
        )
        # 每个白名单前缀 + "12345678" 必须 True
        for prefix in personal_prefixes:
            phone = prefix + "12345678"
            self.assertTrue(
                is_mobile_segment(phone),
                f"个人号段 {prefix} 未被识别: {phone}",
            )


class TestIotExclusion(unittest.TestCase):
    """NUM-03: IoT / 数据卡 / 卫星段必须被排除。"""

    def test_iot_segment_excluded(self):
        for prefix in ("140", "141", "144", "145", "146", "147", "148", "149"):
            self.assertFalse(is_mobile_segment(prefix + "12345678"),
                             f"IoT 段 {prefix} 未被排除")

    def test_satellite_prefix_1349_excluded(self):
        self.assertFalse(is_mobile_segment("13491234567"))

    def test_satellite_prefix_1740_excluded(self):
        self.assertFalse(is_mobile_segment("17401234567"))

    def test_satellite_prefix_1741_excluded(self):
        self.assertFalse(is_mobile_segment("17411234567"))

    def test_data_card_prefix_145_excluded(self):
        self.assertFalse(is_mobile_segment("14512345678"))

    def test_non_leading_one_rejected(self):
        self.assertFalse(is_mobile_segment("23812345678"))

    def test_short_phone_rejected(self):
        self.assertFalse(is_mobile_segment("1381234567"))

    def test_long_phone_rejected(self):
        self.assertFalse(is_mobile_segment("138123456789"))

    def test_non_digit_phone_rejected(self):
        self.assertFalse(is_mobile_segment("1381234567A"))

    def test_empty_string_rejected(self):
        self.assertFalse(is_mobile_segment(""))


class TestPhoneSegmentDefensive(unittest.TestCase):
    """NUM-03: 防御性输入。"""

    def test_none_rejected(self):
        self.assertFalse(is_mobile_segment(None))  # type: ignore[arg-type]


class TestPhoneSegmentTables(unittest.TestCase):
    """NUM-03: 段号表常量完整性（IoT / 卫星前缀必须存在于 excluded sets）。"""

    def test_iot_3_digit_prefixes_present(self):
        for p in ("140", "141", "144", "145", "146", "147", "148", "149"):
            self.assertIn(p, PHONE_EXCLUDED_PREFIX_3,
                          f"IoT 段 {p} 必须在 PHONE_EXCLUDED_PREFIX_3")

    def test_satellite_4_digit_prefixes_present(self):
        for p in ("1349", "1440", "1740", "1741"):
            self.assertIn(p, PHONE_EXCLUDED_PREFIX_4,
                          f"卫星段 {p} 必须在 PHONE_EXCLUDED_PREFIX_4")


# ----------------------------------------------------------------------
# Phase 2 (02-01-tracer) — USCC / 银行卡 / 邮箱 validator 测试
# ----------------------------------------------------------------------

class TestBankCardLuhn(unittest.TestCase):
    """NUM-04: Luhn 校验位正向 / 反向 / 防御性。"""

    def test_luhn_standard_visa_passes(self):
        """Visa 测试卡号 4532015112830366 Luhn 通过。"""
        from privacyguard.pii.validators.bank_card import luhn_check
        self.assertTrue(luhn_check('4532015112830366'))

    def test_luhn_invalid_fails(self):
        """Luhn 校验失败样本 → False。"""
        from privacyguard.pii.validators.bank_card import luhn_check
        self.assertFalse(luhn_check('6222020000000000'))

    def test_luhn_non_digit_rejected(self):
        """非数字字符 → False。"""
        from privacyguard.pii.validators.bank_card import luhn_check
        self.assertFalse(luhn_check('622202000000000a'))

    def test_luhn_empty_rejected(self):
        """空字符串 → False。"""
        from privacyguard.pii.validators.bank_card import luhn_check
        self.assertFalse(luhn_check(''))

    def test_luhn_none_rejected(self):
        """None 输入 → False。"""
        from privacyguard.pii.validators.bank_card import luhn_check
        self.assertFalse(luhn_check(None))  # type: ignore[arg-type]


class TestBankCardBin(unittest.TestCase):
    """NUM-04: 银行卡 BIN 白名单 + 上下文 + 长度 + Luhn 联检。"""

    def test_valid_bin_in_whitelist_passes(self):
        """BIN 在白名单 + Luhn 通过 → True。"""
        from privacyguard.pii.validators.bank_card import validate_bank_card
        # 6222021234567894 是 Luhn 校验通过的数字（BIN 622202）
        self.assertTrue(
            validate_bank_card('6222021234567894', bin_whitelist=frozenset({'622202'}))
        )

    def test_unknown_bin_rejected(self):
        """BIN 不在白名单 → False。"""
        from privacyguard.pii.validators.bank_card import validate_bank_card
        self.assertFalse(
            validate_bank_card('0000001234567890', bin_whitelist=frozenset({'622202'}))
        )

    def test_short_card_rejected(self):
        """长度 < 13 → False。"""
        from privacyguard.pii.validators.bank_card import validate_bank_card
        self.assertFalse(
            validate_bank_card('1234567890123', bin_whitelist=frozenset({'622202'}))
        )

    def test_invalid_luhn_rejected(self):
        """Luhn 失败 → False（即使 BIN 在白名单）。"""
        from privacyguard.pii.validators.bank_card import validate_bank_card
        self.assertFalse(
            validate_bank_card('6222020000000000', bin_whitelist=frozenset({'622202'}))
        )

    def test_non_string_rejected(self):
        """非字符串 → False。"""
        from privacyguard.pii.validators.bank_card import validate_bank_card
        self.assertFalse(validate_bank_card(1234567890123456))  # type: ignore[arg-type]


class TestEmail(unittest.TestCase):
    """NUM-05: 邮箱 RFC 5322 简化版正则 + 公共后缀分类。"""

    def test_valid_email_passes(self):
        """标准邮箱 → True。"""
        from privacyguard.pii.validators.email import validate_email
        self.assertTrue(validate_email('user@example.com'))

    def test_invalid_email_rejected(self):
        """无 @ 符号 → False。"""
        from privacyguard.pii.validators.email import validate_email
        self.assertFalse(validate_email('not-an-email'))

    def test_plus_alias_accepted(self):
        """+ 别名 → True。"""
        from privacyguard.pii.validators.email import validate_email
        self.assertTrue(validate_email('user+tag@example.com'))

    def test_public_tld_classified_high(self):
        """公共 .com 后缀 → is_public_suffix_email True。"""
        from privacyguard.pii.validators.email import is_public_suffix_email
        self.assertTrue(is_public_suffix_email('foo@qq.com'))

    def test_unknown_tld_classified_low(self):
        """未知后缀 → is_public_suffix_email False。"""
        from privacyguard.pii.validators.email import is_public_suffix_email
        self.assertFalse(is_public_suffix_email('foo@unknown-tld-xyz'))

    def test_email_public_suffixes_includes_common_tlds(self):
        """EMAIL_PUBLIC_SUFFIXES 包含 com / cn / net 等。"""
        from privacyguard.pii.validators.email import EMAIL_PUBLIC_SUFFIXES
        for tld in ('com', 'cn', 'net', 'org'):
            self.assertIn(tld, EMAIL_PUBLIC_SUFFIXES)


class TestUsccMod31(unittest.TestCase):
    """FIN-01: USCC mod-31-3 校验位 + 字符集 + 长度 + 防御性。"""

    def test_known_uscc_passes(self):
        """已知合法 USCC 样本 → True（91110000600037341L 是腾讯 USCC，本地验证过）。"""
        from privacyguard.pii.validators.uscc import validate_uscc
        self.assertTrue(validate_uscc('91110000600037341L'))

    def test_invalid_check_digit_fails(self):
        """校验位错 → False。"""
        from privacyguard.pii.validators.uscc import validate_uscc
        self.assertFalse(validate_uscc('911100006000373410'))

    def test_charset_rejects_IO_S_V_Z(self):
        """字符集外字符 (I/O/S/V/Z) → False。"""
        from privacyguard.pii.validators.uscc import validate_uscc
        # 含 I/O/S/V/Z 的 18 位 — charset 检查直接拒绝
        self.assertFalse(validate_uscc('91110000600037341I'))
        self.assertFalse(validate_uscc('91110000600037341Z'))

    def test_short_uscc_rejected(self):
        """长度 < 18 → False。"""
        from privacyguard.pii.validators.uscc import validate_uscc
        self.assertFalse(validate_uscc('9111000060003734'))

    def test_non_string_rejected(self):
        """非字符串 → False。"""
        from privacyguard.pii.validators.uscc import validate_uscc
        self.assertFalse(validate_uscc(None))  # type: ignore[arg-type]
        self.assertFalse(validate_uscc(12345))  # type: ignore[arg-type]

    def test_uscc_charset_size_is_31(self):
        """USCC_CHARSET 长度 = 31（数字 10 + 字母 26 - I/O/S/V/Z 5 = 31）。"""
        from privacyguard.pii.validators.uscc import USCC_CHARSET
        self.assertEqual(len(USCC_CHARSET), 31)

    def test_uscc_weights_size_is_17(self):
        """USCC_WEIGHTS 长度 = 17。"""
        from privacyguard.pii.validators.uscc import USCC_WEIGHTS
        self.assertEqual(len(USCC_WEIGHTS), 17)


class TestUsccCategory(unittest.TestCase):
    """FIN-01: USCC 类别代码白名单 — D-06 锁定。"""

    def test_category_code_z_rejected(self):
        """类别码 'Z' 不在白名单 → False（即使 mod-31-3 通过）。"""
        from privacyguard.pii.validators.uscc import validate_uscc
        self.assertFalse(validate_uscc('Z11000000000000000'))

    def test_all_6_categories_accepted(self):
        """6 个有效类别码全部接受（循环构造 → 验证通过）。"""
        from privacyguard.pii.validators.uscc import (
            USCC_CHARSET,
            compute_uscc_check_digit,
            validate_uscc,
        )
        for cat in ('1', '5', '9', 'Y', 'A', 'N'):
            body17 = cat + ''.join(USCC_CHARSET[1] for _ in range(16))  # 简化 body
            check = compute_uscc_check_digit(body17)
            full = body17 + check
            self.assertTrue(
                validate_uscc(full),
                f"类别码 {cat!r} 应被接受，但 validate_uscc({full!r}) 返回 False",
            )

    def test_category_whitelist_size_is_6(self):
        """USCC_CATEGORY_CODES 长度 = 6（D-06 锁定）。"""
        from privacyguard.pii.validators.uscc import USCC_CATEGORY_CODES
        self.assertEqual(len(USCC_CATEGORY_CODES), 6)

    def test_category_whitelist_contains_expected_codes(self):
        """USCC_CATEGORY_CODES 包含 '1'/'5'/'9'/'Y'/'A'/'N'。"""
        from privacyguard.pii.validators.uscc import USCC_CATEGORY_CODES
        for code in ('1', '5', '9', 'Y', 'A', 'N'):
            self.assertIn(code, USCC_CATEGORY_CODES)


# ----------------------------------------------------------------------
# Phase 2 (02-02-engine-expansion) — VAT 发票号 / 银行账号 / 15 位税号 validator
# ----------------------------------------------------------------------

class TestVatInvoice(unittest.TestCase):
    """FIN-02: 增值税发票号 8 位 / 20 位双格式 + 上下文锥点。"""

    def test_8_digit_passes(self):
        from privacyguard.pii.validators.vat_invoice import validate_vat_invoice_8
        self.assertTrue(validate_vat_invoice_8('12345678'))

    def test_8_digit_with_letters_rejected(self):
        from privacyguard.pii.validators.vat_invoice import validate_vat_invoice_8
        self.assertFalse(validate_vat_invoice_8('1234567a'))

    def test_20_digit_passes(self):
        from privacyguard.pii.validators.vat_invoice import validate_vat_invoice_20
        self.assertTrue(validate_vat_invoice_20('12345678901234567890'))

    def test_20_digit_with_hyphens_accepted(self):
        """20 位含横线/年份分隔 → 剥离后 → True。"""
        from privacyguard.pii.validators.vat_invoice import validate_vat_invoice_20
        self.assertTrue(validate_vat_invoice_20('1234-5678-9012-3456-7890'))

    def test_20_digit_wrong_length_rejected(self):
        from privacyguard.pii.validators.vat_invoice import validate_vat_invoice_20
        self.assertFalse(validate_vat_invoice_20('1234567890'))

    def test_non_string_rejected(self):
        from privacyguard.pii.validators.vat_invoice import validate_vat_invoice_8
        self.assertFalse(validate_vat_invoice_8(None))  # type: ignore[arg-type]
        self.assertFalse(validate_vat_invoice_8(12345678))  # type: ignore[arg-type]


class TestVatInvoiceContextAnchor(unittest.TestCase):
    """FIN-02: VAT 上下文锥点 window ±20 chars 检测。"""

    def test_context_anchor_zh(self):
        from privacyguard.pii.validators.vat_invoice import has_vat_invoice_context
        self.assertTrue(has_vat_invoice_context('发票号码 12345678', '12345678'))

    def test_context_anchor_en(self):
        from privacyguard.pii.validators.vat_invoice import has_vat_invoice_context
        self.assertTrue(has_vat_invoice_context('invoice number 12345678', '12345678'))

    def test_no_context_anchor_rejected(self):
        from privacyguard.pii.validators.vat_invoice import has_vat_invoice_context
        self.assertFalse(has_vat_invoice_context('random text 12345678', '12345678'))

    def test_context_anchor_full_width_dianzi_fapiao(self):
        """电子发票 anchor（覆盖中文 / 全数字混合）。"""
        from privacyguard.pii.validators.vat_invoice import has_vat_invoice_context
        self.assertTrue(has_vat_invoice_context('增值税电子发票 12345678', '12345678'))

    def test_context_window_boundary(self):
        """目标 anchor 距离 target > 20 chars 应判 False。"""
        from privacyguard.pii.validators.vat_invoice import has_vat_invoice_context
        long_padding = 'x' * 25
        self.assertFalse(has_vat_invoice_context(f'发票号码 {long_padding}12345678', '12345678'))


class TestTaxpayerId15(unittest.TestCase):
    """FIN-03: 15 位旧版纳税人识别号 — 无强校验位，仅格式 + 行政区划前缀白名单。"""

    def test_valid_15_with_admin_prefix(self):
        from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15
        self.assertTrue(validate_taxpayer_id_15('110101800101001'))

    def test_invalid_admin_prefix_rejected(self):
        """99 不在白名单 → False。"""
        from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15
        self.assertFalse(validate_taxpayer_id_15('990101800101001'))

    def test_short_id_rejected(self):
        from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15
        self.assertFalse(validate_taxpayer_id_15('123'))

    def test_with_hyphens_stripped(self):
        """含横线/年份分隔 → 剥离后 → True。"""
        from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15
        self.assertTrue(validate_taxpayer_id_15('110101-800101-001'))

    def test_does_not_use_uscc_checksum(self):
        """18 位 USCC 不能通过 15 位路径（D-09 双 type 防御误判）。"""
        from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15
        # '91110000600037341L' 是 18 位 USCC（含末尾 L 校验位）
        self.assertFalse(validate_taxpayer_id_15('91110000600037341L'))

    def test_non_string_rejected(self):
        from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15
        self.assertFalse(validate_taxpayer_id_15(None))  # type: ignore[arg-type]

    def test_all_33_admin_prefixes_accepted(self):
        """33 province 编码全部接受 prefix-only 9 位（前置 sanity check）。"""
        from privacyguard.pii.validators.taxpayer_id import (
            _TAXPAYER_15_ADMIN_PREFIX,
            validate_taxpayer_id_15,
        )
        # 33 个省份 2 位前缀
        expected = {
            '11', '12', '13', '14', '15',
            '21', '22', '23',
            '31', '32', '33', '34', '35', '36', '37',
            '41', '42', '43', '44', '45', '46',
            '50', '51', '52', '53', '54',
            '61', '62', '63', '64', '65',
            '71', '81', '82',
        }
        self.assertEqual(len(_TAXPAYER_15_ADMIN_PREFIX), 34)
        for prefix in expected:
            self.assertIn(prefix, _TAXPAYER_15_ADMIN_PREFIX)
        # 构造一个 admin prefix + 13 位 0 → validate 应通过
        for prefix in sorted(_TAXPAYER_15_ADMIN_PREFIX):
            candidate = prefix + '0' * 13
            self.assertTrue(
                validate_taxpayer_id_15(candidate),
                f"admin prefix {prefix} 应被接受，但 validate_taxpayer_id_15({candidate}) 返回 False",
            )


class TestBankAccount(unittest.TestCase):
    """FIN-04: 银行账号 — 9-21 位 + 必查上下文锥点。"""

    def test_18_digit_passes(self):
        from privacyguard.pii.validators.bank_account import validate_bank_account
        self.assertTrue(validate_bank_account('622202123456789012'))

    def test_short_account_rejected(self):
        """8 位低于 9-min → False。"""
        from privacyguard.pii.validators.bank_account import validate_bank_account
        self.assertFalse(validate_bank_account('12345678'))

    def test_long_account_rejected(self):
        """22 位高于 21-max → False。"""
        from privacyguard.pii.validators.bank_account import validate_bank_account
        self.assertFalse(validate_bank_account('1' * 22))

    def test_non_digit_rejected(self):
        from privacyguard.pii.validators.bank_account import validate_bank_account
        self.assertFalse(validate_bank_account('6222021234567890a'))

    def test_with_spaces_stripped(self):
        """含空格 → 剥离后 → 18 位 → True。"""
        from privacyguard.pii.validators.bank_account import validate_bank_account
        self.assertTrue(validate_bank_account('6222 0212 3456 7890 12'))

    def test_non_string_rejected(self):
        from privacyguard.pii.validators.bank_account import validate_bank_account
        self.assertFalse(validate_bank_account(None))  # type: ignore[arg-type]


class TestBankAccountContextAnchor(unittest.TestCase):
    """FIN-04: 银行账号上下文锥点 — D-08 必查。"""

    def test_context_anchor_zh_recognized(self):
        from privacyguard.pii.validators.bank_account import has_bank_account_context
        self.assertTrue(has_bank_account_context('账号 622202123456789012', '622202123456789012'))

    def test_context_anchor_bank_name_recognized(self):
        from privacyguard.pii.validators.bank_account import has_bank_account_context
        self.assertTrue(has_bank_account_context('工商银行 622202', '622202'))

    def test_no_context_anchor_rejected(self):
        from privacyguard.pii.validators.bank_account import has_bank_account_context
        self.assertFalse(has_bank_account_context('random 622202123456789012', '622202123456789012'))

    def test_all_context_keywords_present(self):
        """BANK_ACCOUNT_CONTEXTS 包含 4 generic + 至少 12 银行名关键词（≥17）。"""
        from privacyguard.pii.validators.bank_account import BANK_ACCOUNT_CONTEXTS
        generic = {'账号', '账户', '银行账号', '银行账户'}
        bank_names = {
            '工商银行', '农行', '中行', '建行', '邮储',
            '招行', '交通银行', '中信', '浦发', '兴业', '民生', '平安', '上海银行',
        }
        for kw in generic:
            self.assertIn(kw, BANK_ACCOUNT_CONTEXTS, f"BANK_ACCOUNT_CONTEXTS 缺少 generic {kw}")
        # 17 关键词（D-08 + Claude's Discretion 扩展）
        self.assertGreaterEqual(
            len(BANK_ACCOUNT_CONTEXTS), 17,
            f"BANK_ACCOUNT_CONTEXTS 仅 {len(BANK_ACCOUNT_CONTEXTS)} 条，需 ≥17",
        )
        for kw in bank_names:
            self.assertIn(kw, BANK_ACCOUNT_CONTEXTS, f"BANK_ACCOUNT_CONTEXTS 缺少 {kw}")


class TestBankAccountContextMultipleOccurrences(unittest.TestCase):
    """WR-04 fix (02-04): has_bank_account_context must check ALL find() positions, not just first."""

    def test_two_occurrences_second_has_context_returns_true(self):
        from privacyguard.pii.validators.bank_account import has_bank_account_context
        # 同一账号字符串出现两次:第一次裸出现（无锥点），第二次带'账号'锥点。
        # 第一次 occurrence 周围没有锥点，第二次 occurrence 周围有。
        # Buggy text.find(target) only checks first occurrence -> False.
        # Fixed version iterates find positions -> finds second with anchor -> True.
        target = "622202123456789012"
        # 第一次裸出现（无 '账号' 锥点）+ 第二次带 '账号' 锥点
        text = "X" * 60 + target + "Y" * 30 + "账号 " + target
        self.assertTrue(has_bank_account_context(text, target))

    def test_three_occurrences_only_last_has_context_returns_true(self):
        from privacyguard.pii.validators.bank_account import has_bank_account_context
        # 三次出现：前两次裸，第三次带锥点 — 必须扫描到第三次
        target = "622202123456789012"
        text = target + " " + target + " " + target + " 账号 "
        self.assertTrue(has_bank_account_context(text, target))

    def test_two_occurrences_either_has_context_returns_true(self):
        from privacyguard.pii.validators.bank_account import has_bank_account_context
        # 两个不同账号都有锥点（first has '账号', second has '账户'）
        text = "账号 622202123456789012 中间 账户 622202987654321098"
        self.assertTrue(has_bank_account_context(text, '622202123456789012'))
        self.assertTrue(has_bank_account_context(text, '622202987654321098'))

    def test_two_occurrences_neither_has_context_returns_false(self):
        from privacyguard.pii.validators.bank_account import has_bank_account_context
        # 同一账号出现两次都无锥点 — 应当 False
        target = "622202123456789012"
        text = target + " " + target + " 其他文本"
        self.assertFalse(has_bank_account_context(text, target))

    def test_single_occurrence_no_context_still_returns_false(self):
        """Backward-compat: existing single-occurrence behavior preserved."""
        from privacyguard.pii.validators.bank_account import has_bank_account_context
        self.assertFalse(has_bank_account_context('random 622202123456789012', '622202123456789012'))


class TestVatInvoiceContextConstants(unittest.TestCase):
    """FIN-02: VAT_INVOICE_CONTEXTS 包含必要关键词。"""

    def test_vat_invoice_contexts_includes_common_keywords(self):
        from privacyguard.pii.validators.vat_invoice import VAT_INVOICE_CONTEXTS
        for kw in ('发票', '号码', '票号', 'invoice', 'INVOICE', 'Invoice',
                   '增值税', '电子发票', '全电发票', '号码:', '号:'):
            self.assertIn(kw, VAT_INVOICE_CONTEXTS, f"VAT_INVOICE_CONTEXTS 缺少 {kw}")


if __name__ == "__main__":
    unittest.main()
