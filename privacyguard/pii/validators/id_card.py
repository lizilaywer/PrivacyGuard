"""身份证校验（GB 11643-1999 mod-11-2 + 15 位升级 + 15 位双门检查）。

NUM-01: 18 位 / 15 位居民身份证号
NUM-02: 末位 X / OCR 小写 x（校验前归一化为大写）

B1 second gate（15 位升级后）：province prefix + real calendar date。
仅 15→18 升级路径需要双门检查；18 位路径由 GB 11643 完整校验位保证。
"""
from typing import Final


WEIGHTS: Final = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
MAPPING: Final = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')


# B1 second gate: 1980-1999 年代身份证 行政区划码 2 位前缀（GB/T 2260 历史子集）
# 简化集合：覆盖所有 Phase 1 输入空间；Phase 6 ADV-01 引入完整 ~70 万条行政区划词典
_VALID_ADMIN_PREFIX_2: Final = frozenset({
    '11', '12', '13', '14', '15',
    '21', '22', '23',
    '31', '32', '33', '34', '35', '36', '37',
    '41', '42', '43', '44', '45', '46',
    '50', '51', '52', '53', '54',
    '61', '62', '63', '64', '65',
    '71', '81', '82',
})


def _is_leap_year(year: int) -> bool:
    """公历闰年。"""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _days_in_month(year: int, month: int) -> int:
    """月份天数（公历）。"""
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if month in (4, 6, 9, 11):
        return 30
    if month == 2:
        return 29 if _is_leap_year(year) else 28
    return 0


def compute_check_digit(body17: str) -> str:
    """根据前 17 位计算第 18 位校验码（GB 11643-1999 mod-11-2）。"""
    if not body17 or len(body17) != 17 or not body17.isdigit():
        return ''
    return MAPPING[sum(int(body17[i]) * WEIGHTS[i] for i in range(17)) % 11]


def validate_18(id_str) -> bool:
    """18 位身份证 mod-11-2 校验（NUM-01 / NUM-02 大小写 X）。

    防御性：对非字符串输入直接返回 False（不抛 TypeError）；长度 / 字符类型
    / 末位 [0-9Xx] 三层 gate；最后做 mod-11-2 校验。
    """
    if not isinstance(id_str, str):
        return False
    if not id_str or len(id_str) != 18:
        return False
    if not id_str[:17].isdigit():
        return False
    last = id_str[17]
    if last not in '0123456789Xx':
        return False
    return last.upper() == compute_check_digit(id_str[:17])


def upgrade_15_to_18(id15: str) -> str:
    """15 位旧号 → 18 位（NUM-01 子路径，世纪补 19）。"""
    if not id15 or len(id15) != 15 or not id15.isdigit():
        return ''
    body17 = id15[:6] + '19' + id15[6:]
    return body17 + compute_check_digit(body17)


def is_valid_admin_division_prefix_2(prefix2: str) -> bool:
    """B1 second gate: 行政区划码 2 位前缀合法性。"""
    return prefix2 in _VALID_ADMIN_PREFIX_2


def is_real_calendar_date(yy: int, mm: int, dd: int) -> bool:
    """B1 second gate: 公历日期合法性。

    yy: 年份后 2 位（15 位身份证用 19yy；18 位身份证用 19yy / 20xx）。
    """
    if mm < 1 or mm > 12:
        return False
    full_year = 1900 + yy if yy < 100 else yy
    if dd < 1 or dd > _days_in_month(full_year, mm):
        return False
    return True


def validate_15(id_str) -> bool:
    """15 位身份证验证（升级 + 双门 + 校验位）。

    防御性：非字符串输入 → False。
    流程：长度 / 数字 → upgrade_15_to_18 → 行政区划前缀 → 真实日历日期 → 校验位。
    """
    if not isinstance(id_str, str):
        return False
    if not id_str or len(id_str) != 15 or not id_str.isdigit():
        return False
    upgraded = upgrade_15_to_18(id_str)
    if not upgraded:
        return False
    # B1 second gate: 行政区划码 + 真实日历日期
    if not is_valid_admin_division_prefix_2(upgraded[:2]):
        return False
    yy = int(upgraded[8:10])
    mm = int(upgraded[10:12])
    dd = int(upgraded[12:14])
    if not is_real_calendar_date(yy, mm, dd):
        return False
    return validate_18(upgraded)


__all__ = [
    'WEIGHTS',
    'MAPPING',
    'compute_check_digit',
    'validate_18',
    'validate_15',
    'upgrade_15_to_18',
    'is_valid_admin_division_prefix_2',
    'is_real_calendar_date',
]