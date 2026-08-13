"""PII 命中 partial mask 生成（D-05 mask_strategy 字段）。

Phase 1: partial_mask_id_card + partial_mask_phone
Phase 2 (02-01-tracer): 扩展 6 个 partial_mask_* 函数 — bank_card / email / uscc /
taxpayer_id_15 / vat_invoice / bank_account。

mask_for_entity: 按 entity_type 分派（统一入口）。
所有函数防御性：长度异常返回 '*' * len(text)（不抛 ValueError）。
"""


def partial_mask_id_card(normalized18: str) -> str:
    """身份证部分掩码（前 6 + 后 4）；长度非 18 时返回全掩。"""
    if not normalized18 or len(normalized18) != 18:
        return '*' * len(normalized18)
    return normalized18[:6] + '*' * 8 + normalized18[14:]


def partial_mask_phone(normalized11: str) -> str:
    """手机号部分掩码（前 3 + 后 4）；长度非 11 时返回全掩。"""
    if not normalized11 or len(normalized11) != 11:
        return '*' * len(normalized11)
    return normalized11[:3] + '*' * 4 + normalized11[7:]


# ----------------------------------------------------------------------
# Phase 2 (02-01-tracer) — 6 个新 partial_mask_*
# ----------------------------------------------------------------------

def partial_mask_bank_card(card: str) -> str:
    """银行卡部分掩码（前 4 + 后 4）；长度非 13-19 时返回全掩。"""
    if not card or not (13 <= len(card) <= 19):
        return '*' * len(card)
    return card[:4] + '*' * (len(card) - 8) + card[-4:]


def partial_mask_email(email: str) -> str:
    """邮箱部分掩码（u****@domain.tld 保留完整域名）。

    规则：local 部分保留首字符 + 4 个星号；domain 完整保留（保留顶级域名后缀）。
    示例：foo@qq.com → 'f****@qq.com'
    """
    if not email or '@' not in email:
        return '*' * len(email)
    local, _, domain = email.partition('@')
    if not local or not domain:
        return '*' * len(email)
    return local[0] + '****' + '@' + domain


def partial_mask_uscc(uscc: str) -> str:
    """USCC / 18 位纳税人识别号部分掩码（前 6 + 后 4，固定 18 字符）。"""
    if not uscc or len(uscc) != 18:
        return '*' * len(uscc)
    return uscc[:6] + '*' * 8 + uscc[14:]


def partial_mask_taxpayer_id_15(id15: str) -> str:
    """15 位旧版纳税人识别号（前 6 + 后 4；与 USCC 18 位一致）。

    固定 15 字符：6 + 5 + 4。
    """
    if not id15 or len(id15) != 15:
        return '*' * len(id15)
    return id15[:6] + '*' * 5 + id15[11:]


def partial_mask_vat_invoice(num: str) -> str:
    """VAT 发票号部分掩码（前 2 + 后 2）。"""
    if not num or len(num) < 4:
        return '*' * len(num)
    return num[:2] + '*' * (len(num) - 4) + num[-2:]


def partial_mask_bank_account(acct: str) -> str:
    """银行账号部分掩码（前 4 + 后 4）。"""
    if not acct or len(acct) < 8:
        return '*' * len(acct)
    return acct[:4] + '*' * (len(acct) - 8) + acct[-4:]


def mask_for_entity(entity_type: str, normalized_text: str) -> str:
    """按 entity_type 分派掩码策略（统一入口）。

    未知 entity → '*' * len(normalized_text) 全掩。
    """
    if entity_type == "CN_ID_CARD":
        return partial_mask_id_card(normalized_text)
    if entity_type == "CN_PHONE":
        return partial_mask_phone(normalized_text)
    # Phase 2 (02-01-tracer) — 6 new entities
    if entity_type == "CN_BANK_CARD":
        return partial_mask_bank_card(normalized_text)
    if entity_type == "CN_EMAIL":
        return partial_mask_email(normalized_text)
    if entity_type in ("CN_USCC", "CN_TAXPAYER_ID"):
        # 18 位三证合一复用 USCC mask
        return partial_mask_uscc(normalized_text)
    if entity_type == "CN_TAXPAYER_ID_15":
        return partial_mask_taxpayer_id_15(normalized_text)
    if entity_type == "CN_VAT_INVOICE":
        return partial_mask_vat_invoice(normalized_text)
    if entity_type == "CN_BANK_ACCOUNT":
        return partial_mask_bank_account(normalized_text)
    return '*' * len(normalized_text)


__all__ = [
    'partial_mask_id_card',
    'partial_mask_phone',
    # Phase 2 (02-01-tracer)
    'partial_mask_bank_card',
    'partial_mask_email',
    'partial_mask_uscc',
    'partial_mask_taxpayer_id_15',
    'partial_mask_vat_invoice',
    'partial_mask_bank_account',
    'mask_for_entity',
]
