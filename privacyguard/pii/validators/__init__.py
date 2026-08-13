"""PrivacyGuard PII 验证器子包（NUM-01/02/03 + Phase 2 NUM-04/05/FIN-01..04 纯函数实现）。"""
from importlib import import_module


__all__ = [
    'validate_18_id',
    'validate_15_id',
    'upgrade_15_to_18',
    'compute_check_digit',
    'is_mobile_segment',
    'PHONE_PERSONAL_PREFIX_3',
    'PHONE_EXCLUDED_PREFIX_3',
    'PHONE_EXCLUDED_PREFIX_4',
    # Phase 2 (02-01-tracer) 新增
    'validate_uscc',
    'validate_bank_card',
    'validate_email',
    'is_public_suffix_email',
    'luhn_check',
    'load_bin_whitelist',
    'get_bin_whitelist',
    'set_bin_whitelist_for_test',
    'USCC_CHARSET',
    'USCC_WEIGHTS',
    'USCC_CATEGORY_CODES',
    'EMAIL_RE',
    'EMAIL_PUBLIC_SUFFIXES',
    'BANK_CARD_BIN_WHITELIST',
    # Phase 2 (02-02-engine-expansion) 新增 — FIN-02/03/04
    'validate_taxpayer_id_15',
    'has_vat_invoice_context',
    'has_bank_account_context',
    'VAT_INVOICE_CONTEXTS',
    'BANK_ACCOUNT_CONTEXTS',
]


_LAZY_IMPORTS = {
    'validate_18_id':           ('privacyguard.pii.validators.id_card', 'validate_18'),
    'validate_15_id':           ('privacyguard.pii.validators.id_card', 'validate_15'),
    'upgrade_15_to_18':         ('privacyguard.pii.validators.id_card', 'upgrade_15_to_18'),
    'compute_check_digit':      ('privacyguard.pii.validators.id_card', 'compute_check_digit'),
    'is_mobile_segment':        ('privacyguard.pii.validators.phone_segment', 'is_mobile_segment'),
    'PHONE_PERSONAL_PREFIX_3':  ('privacyguard.pii.validators.phone_segment', 'PHONE_PERSONAL_PREFIX_3'),
    'PHONE_EXCLUDED_PREFIX_3':  ('privacyguard.pii.validators.phone_segment', 'PHONE_EXCLUDED_PREFIX_3'),
    'PHONE_EXCLUDED_PREFIX_4':  ('privacyguard.pii.validators.phone_segment', 'PHONE_EXCLUDED_PREFIX_4'),
    # Phase 2 (02-01-tracer) — 3 new validators + constants + helpers
    'validate_uscc':            ('privacyguard.pii.validators.uscc', 'validate_uscc'),
    'USCC_CHARSET':             ('privacyguard.pii.validators.uscc', 'USCC_CHARSET'),
    'USCC_WEIGHTS':             ('privacyguard.pii.validators.uscc', 'USCC_WEIGHTS'),
    'USCC_CATEGORY_CODES':      ('privacyguard.pii.validators.uscc', 'USCC_CATEGORY_CODES'),
    'validate_bank_card':       ('privacyguard.pii.validators.bank_card', 'validate_bank_card'),
    'luhn_check':               ('privacyguard.pii.validators.bank_card', 'luhn_check'),
    'load_bin_whitelist':       ('privacyguard.pii.validators.bank_card', 'load_bin_whitelist'),
    'get_bin_whitelist':        ('privacyguard.pii.validators.bank_card', 'get_bin_whitelist'),
    'set_bin_whitelist_for_test': ('privacyguard.pii.validators.bank_card', 'set_bin_whitelist_for_test'),
    'BANK_CARD_BIN_WHITELIST':  ('privacyguard.pii.validators.bank_card', 'BANK_CARD_BIN_WHITELIST'),
    'validate_email':           ('privacyguard.pii.validators.email', 'validate_email'),
    'is_public_suffix_email':   ('privacyguard.pii.validators.email', 'is_public_suffix_email'),
    'EMAIL_RE':                 ('privacyguard.pii.validators.email', 'EMAIL_RE'),
    'EMAIL_PUBLIC_SUFFIXES':    ('privacyguard.pii.validators.email', 'EMAIL_PUBLIC_SUFFIXES'),
    # Phase 2 (02-02-engine-expansion) — 3 new validators / context helpers / constants
    'validate_taxpayer_id_15':  ('privacyguard.pii.validators.taxpayer_id', 'validate_taxpayer_id_15'),
    'has_vat_invoice_context':  ('privacyguard.pii.validators.vat_invoice', 'has_vat_invoice_context'),
    'has_bank_account_context': ('privacyguard.pii.validators.bank_account', 'has_bank_account_context'),
    'VAT_INVOICE_CONTEXTS':     ('privacyguard.pii.validators.vat_invoice', 'VAT_INVOICE_CONTEXTS'),
    'BANK_ACCOUNT_CONTEXTS':    ('privacyguard.pii.validators.bank_account', 'BANK_ACCOUNT_CONTEXTS'),
}


def __getattr__(name):
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_IMPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
