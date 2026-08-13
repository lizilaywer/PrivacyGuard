"""增值税发票号校验（FIN-02 + D-07 双格式 + 上下文锥点）。

- 传统 8 位纯数字
- 全电发票 20 位（2022 年起国家税务总局公告 1 号）
- 上下文锥点（发票 / 号码 / 票号 / invoice）±20 字符必查

D-07: 8 位无上下文锥点单独出现 → confidence_tier = MEDIUM（不 reject，
保留"疑似票号"）；20 位与 8 位通过正则 yield 两次
（regex_patterns.py），engine 内按 hit 的 confidence 区分。
"""
from typing import Final


# VAT 上下文锥点白名单（含中英文 + 不同大小写 + 标点变体）
VAT_INVOICE_CONTEXTS: Final = frozenset({
    "发票", "号码", "票号", "invoice", "INVOICE", "Invoice",
    "增值税", "电子发票", "全电发票", "号码:", "号:",
})


def validate_vat_invoice_8(num8: str) -> bool:
    """传统 8 位增值税发票号校验。

    防御性：非字符串 / 非 8 位 / 含非数字 → False。
    """
    return isinstance(num8, str) and len(num8) == 8 and num8.isdigit()


def validate_vat_invoice_20(num20: str) -> bool:
    """全电发票 20 位号码校验（含横线 / 空格 / 年份分隔）。

    防御性：非字符串 / 剥离后非 20 位 / 含非数字 → False。
    """
    if not isinstance(num20, str):
        return False
    stripped = num20.replace("-", "").replace(" ", "")
    return len(stripped) == 20 and stripped.isdigit()


def has_vat_invoice_context(text: str, target: str, window: int = 20) -> bool:
    """target ±window 字符内是否存在 VAT 上下文锥点。

    Args:
        text: 完整页面文本
        target: 待测候选字符串（VAT 票号本身）
        window: 锥点判定窗口半径（默认 20 字符，±20 字符）

    Returns:
        True 当且仅当 text 内 target 附近存在 VAT_INVOICE_CONTEXTS 任一锥点。
    """
    if not text or not target:
        return False
    idx = text.find(target)
    if idx < 0:
        return False
    lo = max(0, idx - window)
    hi = min(len(text), idx + len(target) + window)
    window_text = text[lo:hi]
    return any(ctx in window_text for ctx in VAT_INVOICE_CONTEXTS)


__all__ = [
    "validate_vat_invoice_8",
    "validate_vat_invoice_20",
    "has_vat_invoice_context",
    "VAT_INVOICE_CONTEXTS",
]
