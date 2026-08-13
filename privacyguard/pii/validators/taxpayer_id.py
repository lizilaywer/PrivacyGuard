"""纳税人识别号校验（FIN-03 + D-09 双 type）。

- CN_TAXPAYER_ID: 2015 年后 18 位三证合一 = 复用 validators.uscc.validate_uscc
- CN_TAXPAYER_ID_15: 旧版 15 位 NNNNN-NNNNNNN-NNNN 格式（无强校验位，独立 type）

D-09: 15 位路径**不**复用 USCC 的 mod-31-3 校验；使用 33 省份行政编码白名单 +
6-7-4 结构双重 gate。confidence_tier 默认 = MEDIUM（无强校验位，防御误判）。
"""
from typing import Final


# 旧版 15 位纳税人识别号（2015 年前）行政编码前缀白名单（与 id_card 同步）
# 34 省份 + 直辖市 + 自治区，覆盖 Phase 1 输入空间
_TAXPAYER_15_ADMIN_PREFIX: Final = frozenset({
    '11', '12', '13', '14', '15',
    '21', '22', '23',
    '31', '32', '33', '34', '35', '36', '37',
    '41', '42', '43', '44', '45', '46',
    '50', '51', '52', '53', '54',
    '61', '62', '63', '64', '65',
    '71', '81', '82',
})


def validate_taxpayer_id_15(id15: str) -> bool:
    """15 位旧版纳税人识别号 — 无强校验位，仅格式 + 行政区划前缀。

    防御性：非字符串 / 非 15 位 / 含非数字 / 行政编码不在白名单 → False。

    Args:
        id15: 候选 15 位纳税人识别号（可含横线 / 空格）

    Returns:
        True 当且仅当剥离后为 15 位纯数字且前 2 位在 _TAXPAYER_15_ADMIN_PREFIX 内。
    """
    if not isinstance(id15, str):
        return False
    stripped = id15.replace("-", "").replace(" ", "")
    if len(stripped) != 15 or not stripped.isdigit():
        return False
    return stripped[:2] in _TAXPAYER_15_ADMIN_PREFIX


__all__ = [
    "validate_taxpayer_id_15",
    "_TAXPAYER_15_ADMIN_PREFIX",
]
