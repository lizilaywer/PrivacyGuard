"""银行卡号校验（NUM-04 + ISO/IEC 7812 Luhn + 6 位 BIN 前缀词典）。

- Luhn 校验必过（标准 Luhn：从右数第 2 位起 ×2，>9 时减 9）
- 6 位 BIN 前缀词典白名单（从 bin_prefixes.json 加载，路径走 resource_path）
- 13-19 位纯数字长度区间
- BIN 词典缺失时（02-01 占位阶段）→ safe-fail 返回 False（D-26 锁定）

D-05 + D-26 锁定：BIN 词典为空时 validate_bank_card 必须返回 False（不得降级到
"全量接受"——这会破坏 Phase 1 测试用例的隔离）。
"""
import json
from typing import Final, FrozenSet, Optional


# 启动期从 bin_prefixes.json 加载的 BIN 前 6 位白名单（懒加载全局单例）
# 02-01 占位阶段为空 frozenset；02-03 注入真实数据
BANK_CARD_BIN_WHITELIST: Final = frozenset()


# 模块级单例缓存（首次 get_bin_whitelist 调用时填充）
_BIN_WHITELIST_CACHE: Optional[FrozenSet[str]] = None


def luhn_check(num) -> bool:
    """ISO/IEC 7812 Luhn 校验。

    标准 Luhn：从右数第 2 位起（即反序后 i%2==1），×2，>9 时减 9。
    防御性：非字符串 / 空 / 含非数字 → False。
    """
    if not isinstance(num, str):
        return False
    if not num or not num.isdigit():
        return False
    digits = [int(c) for c in num[::-1]]
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def load_bin_whitelist(json_path: Optional[str] = None) -> FrozenSet[str]:
    """从 bin_prefixes.json 加载 BIN 前 6 位白名单。

    json_path: 自定义路径；默认走 `privacyguard.utils.security.resource_path` 取
    `privacyguard/pii/data/bin_prefixes.json`（cp30 + D-26 教训：禁止
    `os.path.dirname(__file__)`，必须走 resource_path 才能在 PyInstaller frozen
    包下找到数据）。
    """
    from privacyguard.utils.security import resource_path
    if json_path is None:
        json_path = resource_path("privacyguard/pii/data/bin_prefixes.json")
    try:
        with open(json_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        # safe-fail（D-26 锁定）：JSON 缺失或无效 → 空 frozenset
        return frozenset()
    bin_list = data.get("bin_prefixes", [])
    if not isinstance(bin_list, list):
        return frozenset()
    return frozenset(str(b) for b in bin_list if isinstance(b, str))


def get_bin_whitelist() -> FrozenSet[str]:
    """获取 BIN 白名单（全局单例缓存）。

    第一次调用时通过 `load_bin_whitelist()` 加载；后续直接返回缓存值。
    若 JSON 缺失/无效 → 缓存空 frozenset（safe-fail）。
    """
    global _BIN_WHITELIST_CACHE
    if _BIN_WHITELIST_CACHE is None:
        _BIN_WHITELIST_CACHE = load_bin_whitelist()
    return _BIN_WHITELIST_CACHE


def set_bin_whitelist_for_test(value: FrozenSet[str]) -> None:
    """测试专用：手动注入 BIN 白名单（覆盖 cache）。

    Phase 2 在 02-01 占位阶段，JSON 文件未填充时，测试用例需要通过此函数
    注入临时白名单以验证 validate_bank_card 行为。
    """
    global _BIN_WHITELIST_CACHE
    _BIN_WHITELIST_CACHE = frozenset(value)


def validate_bank_card(card_num, bin_whitelist: Optional[FrozenSet[str]] = None) -> bool:
    """银行卡校验：13-19 位 + 纯数字 + Luhn + 6 位 BIN 白名单。

    Args:
        card_num: 银行卡号字符串（可含空格 / 连字符，会被剥除）
        bin_whitelist: 自定义 BIN 白名单；默认走 `get_bin_whitelist()` 全局缓存

    Returns:
        True 当且仅当所有 gate（长度 / 数字 / Luhn / BIN）全部通过

    D-05 / D-26 锁定：BIN 白名单为空时返回 False（不得降级为"全量接受"）。
    """
    if not isinstance(card_num, str):
        return False
    stripped = card_num.replace(" ", "").replace("-", "")
    if not stripped.isdigit():
        return False
    if not (13 <= len(stripped) <= 19):
        return False
    if not luhn_check(stripped):
        return False
    whitelist = bin_whitelist if bin_whitelist is not None else get_bin_whitelist()
    if not whitelist:
        # D-26 safe-fail：BIN 词典缺失 / 为空 → 不接受任何卡号
        return False
    return stripped[:6] in whitelist


__all__ = [
    "luhn_check",
    "load_bin_whitelist",
    "get_bin_whitelist",
    "set_bin_whitelist_for_test",
    "validate_bank_card",
    "BANK_CARD_BIN_WHITELIST",
]
