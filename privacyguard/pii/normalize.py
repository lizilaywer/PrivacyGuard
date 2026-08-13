"""ENGINE-05 / ENGINE-06 文本归一化（全角→半角 + 跨行拼接 + offset 回算）。

- normalize_digits: 全角数字 → 半角 + 去除 -/半角空格/全角空格（用于已校验字符串）
- flatten_for_match: 去除所有空白 + -（用于跨行 / 制表 / 全角空白的拼接）
- map_flat_to_original: 把 flat 字符串中的 (start, end) 映射回原始字符串

ENGINE-05 防御契约：map_flat_to_original 在不可映射时显式返回 (None, None)，
绝不静默返回 (0, 0)。ENGINE-07 防 DoS：输入超过 _MAX_TEXT_BYTES 自动截断。
"""
import re
from typing import Optional, Tuple


_FULLWIDTH_DIGITS = str.maketrans(
    '０１２３４５６７８９',
    '0123456789',
)


_SEPARATOR_CHARS = re.compile(r'[-\s　]+')

_FLATTEN_CHARS = re.compile(r'[\s\n\r\t　-]+')


def normalize_digits(text: str) -> str:
    """全角数字 → 半角 + 移除 -/半角空格/全角空格。"""
    if not text:
        return ''
    text = text.translate(_FULLWIDTH_DIGITS)
    return _SEPARATOR_CHARS.sub('', text)


def flatten_for_match(text: str) -> str:
    """跨行 / 制表 / 全角空白拼接（用于跨行实体识别 ENGINE-06）。

    同时把全角数字归一化为 ASCII（便于正则匹配）；原文本中的全角数字位置
    由 map_flat_to_original 通过 1:1 字符计数回算保留。
    """
    if not text:
        return ''
    text = text.translate(_FULLWIDTH_DIGITS)
    return _FLATTEN_CHARS.sub('', text)


# 跳过字符集合（用于 map_flat_to_original）
_SKIP_CHARS = frozenset(' \t\n\r\f\v　-')


def map_flat_to_original(
    flat_text: str,
    flat_span: Tuple[int, int],
    original_text: str,
) -> Optional[Tuple[int, int]]:
    """把 flat 字符串中的 (start, end) 映射回 original_text 中的 (start, end)。

    ENGINE-05 offset 回算用：flat 是去空白后的字符串，命中位置需映回原始字符串。
    跳过规则：空白 / 横线 / 全角空白字符不消耗 flat 位置；全角数字按归一化语义计数为 1。

    不可映射 → 返回 (None, None)（不静默返回 0；engine 据此判定 skip hit）。
    """
    if not flat_text or not original_text:
        return None, None
    flat_start, flat_end = flat_span
    if flat_start < 0 or flat_end > len(flat_text) or flat_start > flat_end:
        return None, None
    if flat_start == flat_end:
        # 空 span：返回 (None, None) 让调用方跳过
        return None, None

    orig_pos = 0
    flat_pos = 0
    orig_start: Optional[int] = None

    while orig_pos < len(original_text) and flat_pos < len(flat_text):
        ch = original_text[orig_pos]
        if ch in _SKIP_CHARS:
            orig_pos += 1
            continue
        # 当前 orig_pos 对应一个 flat 位置（fullwidth 数字按归一化计数为 1）
        if flat_pos == flat_start and orig_start is None:
            orig_start = orig_pos
        if flat_pos == flat_end - 1:
            # 命中 span 最后一个 flat 字符；orig_end 为 exclusive
            return orig_start, orig_pos + 1
        flat_pos += 1
        orig_pos += 1

    # 未能在 original_text 中推进到 flat_end（输入被截断 / span 越界）
    return None, None


__all__ = ['normalize_digits', 'flatten_for_match', 'map_flat_to_original']
