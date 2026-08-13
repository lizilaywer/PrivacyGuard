"""合成 PII 生成器（OPS-05 严禁真实数据；random + mod-11-2 校验循环）。

Phase 1 不引入 Faker 依赖（环境探测结论：Faker 未在 requirements.txt），
改用 random.randint + 校验循环；与 Faker 兼容的接口形态。

模块加载策略：仅导入 stdlib；privacyguard.pii.validators.id_card 走懒加载
（保持隐私包在不触发时不被加载）。
"""
import random


# 行政区划码 2 位前缀白名单（与 privacyguard.pii.validators.id_card._VALID_ADMIN_PREFIX_2 同步）
_VALID_PROVINCE_PREFIX = (
    '11', '12', '13', '14', '15',
    '21', '22', '23',
    '31', '32', '33', '34', '35', '36', '37',
    '41', '42', '43', '44', '45', '46',
    '50', '51', '52', '53', '54',
    '61', '62', '63', '64', '65',
    '71', '81', '82',
)


def _is_leap_year(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _days_in_month(year: int, month: int) -> int:
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if month in (4, 6, 9, 11):
        return 30
    if month == 2:
        return 29 if _is_leap_year(year) else 28
    return 0


def _compute_check_digit(body17: str) -> str:
    """合成阶段独立计算 GB 11643 mod-11-2 校验位；不依赖 privacyguard.pii 包。"""
    weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    mapping = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')
    return mapping[sum(int(body17[i]) * weights[i] for i in range(17)) % 11]


def fake_id_card(year_lo: int = 90) -> str:
    """生成一个通过 mod-11-2 校验 + 日期合法 + 行政区划前缀合法的 18 位伪身份证号。

    year_lo: 出生年份后 2 位下限（默认 90 = 1990 年）；上限为 99。
    """
    while True:
        province = random.choice(_VALID_PROVINCE_PREFIX)
        city = ''.join(random.choice('0123456789') for _ in range(4))
        year_full = 1900 + random.randint(year_lo, 99)
        month = random.randint(1, 12)
        day = random.randint(1, _days_in_month(year_full, month))
        seq = ''.join(random.choice('0123456789') for _ in range(3))
        body17 = (
            province + city
            + f'{year_full:04d}'
            + f'{month:02d}{day:02d}'
            + seq
        )
        if len(body17) != 17:
            continue
        full = body17 + _compute_check_digit(body17)
        # 二次验证
        from privacyguard.pii.validators.id_card import validate_18
        if validate_18(full):
            return full


def fake_phone(seg: str = '138') -> str:
    """生成一个通过 is_mobile_segment 的伪手机号。"""
    return seg + ''.join(random.choice('0123456789') for _ in range(8))


def fake_phone_invalid() -> str:
    """生成一个 14X 物联网段（应被 is_mobile_segment 排除）。"""
    return '140' + ''.join(random.choice('0123456789') for _ in range(8))


def fake_phone_lowercase_tail() -> str:
    """占位辅助函数：保留扩展位，未来用于 NUM-02 小写 x 测试。"""
    raise NotImplementedError("OCR 小写 x 路径在 01-01 之外验证")


# ----------------------------------------------------------------------
# Phase 2 (02-01-tracer) — 新增 7 个 fake_* 合成器（OPS-05 严禁真实数据）
# ----------------------------------------------------------------------

def fake_bank_card(bin_prefix: str = '622576') -> str:
    """生成一个通过 Luhn + BIN 前缀词典的 16 位伪银行卡号。

    bin_prefix: 6 位 BIN 前缀（默认 '622576'；测试时可换其他已知 BIN）。
    循环生成直到 luhn_check 通过。
    """
    from privacyguard.pii.validators.bank_card import luhn_check
    while True:
        body = bin_prefix + ''.join(random.choice('0123456789') for _ in range(9))
        digits = [int(c) for c in body[::-1]]
        # 标准 Luhn（从右数第 2 位起 ×2）
        total = 0
        for i, d in enumerate(digits):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        check = (10 - total % 10) % 10
        full = body + str(check)
        if luhn_check(full):
            return full


def fake_bank_card_invalid_luhn() -> str:
    """Luhn 校验失败的银行卡号（应被 validate_bank_card 拒绝）。"""
    return "6222020000000000"  # 不通过 Luhn


def fake_email(local: str = None, tld: str = 'example.com') -> str:
    """生成一个通过 validate_email 的伪邮箱。"""
    if not local:
        local = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(8))
    return f"{local}@{tld}"


def fake_email_invalid() -> str:
    """格式不合法的伪邮箱（应被 validate_email 拒绝）。"""
    return "not-an-email"


def fake_uscc(category: str = '9') -> str:
    """生成一个通过 mod-31-3 + 类别代码白名单的 18 位伪 USCC。

    category: 'random' → 随机从 {'1','5','9','Y','A','N'} 选；否则固定。
    """
    from privacyguard.pii.validators.uscc import (
        USCC_CHARSET,
        compute_uscc_check_digit,
        validate_uscc,
    )
    valid_categories = ['1', '5', '9', 'Y', 'A', 'N']
    cat = random.choice(valid_categories) if category == 'random' else category
    # 循环生成直到 validate_uscc 通过（category gate + mod-31-3 一并通过）
    while True:
        body17 = cat + ''.join(random.choice(USCC_CHARSET) for _ in range(16))
        check = compute_uscc_check_digit(body17)
        if not check:
            continue
        full = body17 + check
        if validate_uscc(full):
            return full


def fake_uscc_invalid_category() -> str:
    """登记管理部门类别代码无效的伪 USCC（首字符 'Z' — 应被 validate_uscc 拒绝）。"""
    return "Z1100000000000000X"


def fake_vat_invoice_8() -> str:
    """生成 8 位纯数字的传统增值税发票号。"""
    return ''.join(random.choice('0123456789') for _ in range(8))


def fake_vat_invoice_20() -> str:
    """生成 20 位纯数字的全电发票号。"""
    return ''.join(random.choice('0123456789') for _ in range(20))


def fake_taxpayer_id_15() -> str:
    """生成 15 位旧版纳税人识别号（行政区划码 2 位 + 13 位数字）。

    行政区划前缀取自与 id_card 同步的有效省份集合。
    """
    province = random.choice(('11', '12', '13', '21', '31', '33', '44', '51', '61'))
    rest = ''.join(random.choice('0123456789') for _ in range(13))
    return province + rest


def fake_bank_account() -> str:
    """生成 18 位纯数字的银行账号（在 9-21 位范围内）。"""
    return ''.join(random.choice('0123456789') for _ in range(18))