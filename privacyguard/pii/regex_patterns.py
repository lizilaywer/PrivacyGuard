"""PII 候选字符串预编译正则（worker 多次复用）。

Phase 1: 18 位 / 15 位身份证 + 11 位手机号。
Phase 2 (02-01-tracer): 扩展 6 个 entity_hint — CN_BANK_CARD / CN_EMAIL / CN_USCC /
CN_VAT_INVOICE (8 + 20 位) / CN_TAXPAYER_ID_15 / CN_BANK_ACCOUNT。

具体段号 / 校验位判定走 `privacyguard.pii.validators.*`（mod-31-3 / mod-11-2 /
Luhn / GB 32100 / RFC 5322 等）。
"""
import re
from typing import Final, Iterator, Tuple


# 18 位（年份限制 19xx / 20xx；月份 / 日期合法性；末位 [0-9Xx]）
_ID_18_RE: Final = re.compile(
    r"(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)"
)
# 15 位（旧号，升级到 18 位后再校验）
_ID_15_RE: Final = re.compile(r"(?<!\d)([1-9]\d{14})(?!\d)")
# 11 位 1 开头的疑似手机号（具体段号判定走 validators.phone_segment）
_PHONE_11_RE: Final = re.compile(r"(?<!\d)(1\d{10})(?!\d)")


# Phase 2 (02-01-tracer) — 6 个新 entity_hint 正则
# NUM-04: 银行卡 — 13-19 位纯数字
_BANK_CARD_RE: Final = re.compile(r"(?<!\d)(\d{13,19})(?!\d)")
# NUM-05: 邮箱 — RFC 5322 简化版
_EMAIL_RE: Final = re.compile(
    r"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9._%+-])"
)
# FIN-01: USCC — 18 位（字符集 = 0-9 + 大写字母 A-Z 去 I/O/S/V/Z）
_USCC_RE: Final = re.compile(r"(?<![A-Z0-9])([0-9A-HJ-NPQRTUWXY]{18})(?![A-Z0-9])")
# FIN-02: VAT 发票号 — 8 位 + 20 位双格式
_VAT_INVOICE_8_RE: Final = re.compile(r"(?<!\d)(\d{8})(?!\d)")
_VAT_INVOICE_20_RE: Final = re.compile(r"(?<!\d)(\d{20})(?!\d)")
# FIN-03: 15 位旧版纳税人识别号（不以 0 开头；长度 15）
_TAXPAYER_ID_15_RE: Final = re.compile(r"(?<!\d)([1-9]\d{14})(?!\d)")
# FIN-04: 银行账号 — 9-21 位纯数字
_BANK_ACCOUNT_RE: Final = re.compile(r"(?<!\d)(\d{9,21})(?!\d)")


def iter_candidate_strings(text: str) -> Iterator[Tuple[str, Tuple[int, int], str]]:
    """按 entity_hint 顺序产出候选字符串（去重交给 engine.resolve）。

    产出 (candidate_text, (start, end), entity_hint) 元组。

    Phase 1 yield 顺序：CN_ID_CARD (18) → CN_ID_CARD (15) → CN_PHONE
    Phase 2 扩展（保留既有顺序 + 在尾追加 6 个新 entity_hint）：
        CN_BANK_CARD → CN_EMAIL → CN_USCC → CN_VAT_INVOICE (8 + 20) →
        CN_TAXPAYER_ID_15 → CN_BANK_ACCOUNT
    """
    for m in _ID_18_RE.finditer(text):
        yield m.group(0), m.span(), "CN_ID_CARD"
    for m in _ID_15_RE.finditer(text):
        yield m.group(0), m.span(), "CN_ID_CARD"
    for m in _PHONE_11_RE.finditer(text):
        yield m.group(0), m.span(), "CN_PHONE"

    # Phase 2 (02-01-tracer) — 6 new entity_hint
    for m in _BANK_CARD_RE.finditer(text):
        yield m.group(0), m.span(), "CN_BANK_CARD"
    for m in _EMAIL_RE.finditer(text):
        yield m.group(0), m.span(), "CN_EMAIL"
    for m in _USCC_RE.finditer(text):
        yield m.group(0), m.span(), "CN_USCC"
    # 02-02 (D-09 双 type 契约): 同一 18-位 USCC regex 第二次 yield，标志为 CN_TAXPAYER_ID。
    # engine._check_taxpayer_id 复用 validate_uscc，mask_strategy 与 CN_USCC 一致。
    for m in _USCC_RE.finditer(text):
        yield m.group(0), m.span(), "CN_TAXPAYER_ID"
    for m in _VAT_INVOICE_8_RE.finditer(text):
        yield m.group(0), m.span(), "CN_VAT_INVOICE"
    for m in _VAT_INVOICE_20_RE.finditer(text):
        yield m.group(0), m.span(), "CN_VAT_INVOICE"
    for m in _TAXPAYER_ID_15_RE.finditer(text):
        yield m.group(0), m.span(), "CN_TAXPAYER_ID_15"
    for m in _BANK_ACCOUNT_RE.finditer(text):
        yield m.group(0), m.span(), "CN_BANK_ACCOUNT"


__all__ = ['iter_candidate_strings']
