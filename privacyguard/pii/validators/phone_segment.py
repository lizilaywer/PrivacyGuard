"""中国大陆手机号段判定（NUM-03）。

排除 14X 物联网 / 卫星 / 数据卡号段（MIIT 公开清单 + 工信部 2017-08 / 2019-12 号段核发公告）。
[ASSUMED] 2026-Q1 基线；Phase 1 ship 前需用户 sign-off（D-11）。
"""
from typing import Final


# NUM-03: 三大运营商 + 广电 + 虚拟运营商 个人号段
PHONE_PERSONAL_PREFIX_3: Final = frozenset({
    '130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
    '150', '151', '152', '153', '155', '156', '157', '158', '159',
    '162', '165', '166', '167',
    '170', '171', '172', '173', '175', '176', '177', '178',
    '180', '181', '182', '183', '184', '185', '186', '187', '188', '189',
    '190', '191', '192', '193', '195', '196', '197', '198', '199',
})


# 排除 3 位前缀：14X 物联网 / 数据卡
PHONE_EXCLUDED_PREFIX_3: Final = frozenset({
    '140', '141', '144', '145', '146', '147', '148', '149',
})


# 排除 4 位前缀：卫星 / 物联专用
PHONE_EXCLUDED_PREFIX_4: Final = frozenset({
    '1349', '1440', '1740', '1741',
})


def is_mobile_segment(phone11) -> bool:
    """中国大陆手机号判定。

    返回 True 当且仅当：
    - 长度为 11
    - 全部为数字
    - 以 '1' 开头
    - 前 4 位不在 excluded_4 集合（卫星 / 数据卡专用）
    - 前 3 位不在 excluded_3 集合（IoT 物联）
    - 前 3 位在 personal_prefix_3 白名单内

    防御性：非字符串输入 → False（不抛 TypeError）。
    """
    if not isinstance(phone11, str):
        return False
    if not phone11 or len(phone11) != 11 or not phone11.isdigit():
        return False
    if not phone11.startswith('1'):
        return False
    if phone11[:4] in PHONE_EXCLUDED_PREFIX_4:
        return False
    if phone11[:3] in PHONE_EXCLUDED_PREFIX_3:
        return False
    return phone11[:3] in PHONE_PERSONAL_PREFIX_3


__all__ = [
    'PHONE_PERSONAL_PREFIX_3',
    'PHONE_EXCLUDED_PREFIX_3',
    'PHONE_EXCLUDED_PREFIX_4',
    'is_mobile_segment',
]