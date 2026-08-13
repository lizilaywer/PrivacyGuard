"""统一社会信用代码校验（FIN-01 + GB 32100-2015 mod-31-3）。

D-06 锁定：
- 18 位
- 登记管理部门类别代码白名单（6 字符：1=机构编制 / 5=民政 / 9=工商 / Y=其他 / A=交通运输 / N=新设）
- GB 32100 mod-31-3 校验位
- 字符集 = 数字 0-9 + 大写字母 A-Z 减去 I/O/S/V/Z 共 31 字符
"""
from typing import Final


# GB 32100-2015 mod-31-3 权重表（17 位 body 的权重）
USCC_WEIGHTS: Final = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)

# USCC 字符集：数字 0-9 + 大写字母 A-Z（去 I / O / S / V / Z 共 5 个）
# = 10 + 26 - 5 = 31 字符
USCC_CHARSET: Final = "0123456789ABCDEFGHJKLMNPQRTUWXY"

# D-06 类别代码白名单（6 字符）
USCC_CATEGORY_CODES: Final = frozenset({"1", "5", "9", "Y", "A", "N"})


def compute_uscc_check_digit(body17: str) -> str:
    """GB 32100-2015 mod-31-3 校验位计算。

    输入：body17（17 字符），输出：校验位字符（USCC_CHARSET 中的 1 个字符）。
    防御性：body17 不是 17 字符或含 charset 外字符 → 返回 ""。
    """
    if not isinstance(body17, str) or len(body17) != 17:
        return ""
    if any(c not in USCC_CHARSET for c in body17):
        return ""
    total = 0
    for i in range(17):
        total += USCC_CHARSET.index(body17[i]) * USCC_WEIGHTS[i]
    return USCC_CHARSET[(31 - total % 31) % 31]


def validate_uscc(code) -> bool:
    """USCC 校验：18 位 + 字符集 + 类别码白名单 + mod-31-3。

    防御性：非字符串输入直接返回 False（不抛 TypeError）。
    """
    if not isinstance(code, str):
        return False
    if len(code) != 18:
        return False
    # 字符集 gate
    if any(c not in USCC_CHARSET for c in code):
        return False
    # D-06 类别码 gate
    if code[0] not in USCC_CATEGORY_CODES:
        return False
    # mod-31-3 校验位
    expected_check = compute_uscc_check_digit(code[:17])
    if not expected_check:
        return False
    return code[17] == expected_check


__all__ = [
    "USCC_CHARSET",
    "USCC_WEIGHTS",
    "USCC_CATEGORY_CODES",
    "compute_uscc_check_digit",
    "validate_uscc",
]
