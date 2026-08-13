"""邮箱识别（NUM-05 + RFC 5322 简化版正则）。

D-10 锁定：
- 不引入 IDN / 国际化邮箱（保持零网络 + 纯本地）
- 正则用 fullmatch（validator 是纯函数，输入即整段）
- 多级子域（foo@bar.qq.com）取最后一段作为 suffix
- 公共域名后缀（com / cn / net / org / gov / edu / io / co / ai / app）→ HIGH
"""
import re
from typing import Final


# D-10 公共域名后缀（用于 confidence 提升 HIGH）
EMAIL_PUBLIC_SUFFIXES: Final = frozenset({
    "com", "cn", "net", "org", "gov", "edu", "io", "co", "ai", "app",
})


# RFC 5322 简化版：local@domain.tld
# 边界用 (?<![A-Za-z0-9._%+-]) 和 (?![A-Za-z0-9._%+-]) 防止部分匹配
EMAIL_RE: Final = re.compile(
    r"\A(?![A-Za-z0-9._%+-]*\.{2})[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\Z"
)


def validate_email(text) -> bool:
    """RFC 5322 简化版邮箱格式校验（fullmatch）。

    防御性：非字符串 / 空 / 不匹配 → False。
    """
    if not isinstance(text, str):
        return False
    if not text:
        return False
    return bool(EMAIL_RE.fullmatch(text))


def is_public_suffix_email(text) -> bool:
    """是否为公共域名后缀邮箱（用于 confidence 提升 HIGH）。

    仅在 validate_email 通过的前提下检查最后一段 TLD 是否在 EMAIL_PUBLIC_SUFFIXES。
    """
    if not validate_email(text):
        return False
    _, _, domain = text.rpartition("@")
    if not domain:
        return False
    suffix = domain.rsplit(".", 1)[-1].lower()
    return suffix in EMAIL_PUBLIC_SUFFIXES


__all__ = [
    "EMAIL_RE",
    "EMAIL_PUBLIC_SUFFIXES",
    "validate_email",
    "is_public_suffix_email",
]
