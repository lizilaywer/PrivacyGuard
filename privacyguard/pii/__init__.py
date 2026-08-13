"""PrivacyGuard PII 自动识别子系统（v38.x Phase 1+2）。

本包承载隐私信息自动识别的核心能力：
- 身份证号（中国大陆 18 位 GB 11643 + 15 位历史号）
- 手机号（中国大陆 MIIT 号段白名单 + IoT/卫星排除）
- USCC（统一社会信用代码 18 位 GB 32100 mod-31-3）
- 银行卡号（13-19 位 Luhn + 6 位 BIN 词典）
- 邮箱（RFC 5322 简化版）
- 文字层 + 图片块 + 整页 OCR 三路径接入（Plan 01-03 Task 1 接管 OCR）
- 真脱敏（PyMuPDF add_redact_annot + apply_redactions(IMAGE_PIXELS)）
- partial mask 写入（Phase 2 MASK-01）
- 元数据清除（Phase 2 SAFE-03）
- 纯本地识别（ENGINE-08 零网络）

懒加载入口：禁止在 `import privacyguard` 时拉起 privacyguard.pii.* 子模块。
新增 PII 子模块必须在 _LAZY_IMPORTS 注册；严禁顶层 `from privacyguard.pii.x import ...`。
"""
from importlib import import_module


# 默认规则版本（rules.json 缺失 / 解析失败时的 fallback）
RULES_VERSION_DEFAULT = "2026-Q1"


__all__ = [
    'PIIEngine',
    'PIIHit',
    'TextUnit',
    'validate_18_id',
    'validate_15_id',
    'upgrade_15_to_18',
    'compute_check_digit',
    'is_mobile_segment',
    'apply_pii_redactions',
    'collect_pii_rects',
    'PHONE_PERSONAL_PREFIX_3',
    'PHONE_EXCLUDED_PREFIX_3',
    'PHONE_EXCLUDED_PREFIX_4',
    'RULES_VERSION_DEFAULT',
    # Phase 2 (02-01-tracer) — validators + partial mask + adapter helpers + constants
    'validate_uscc',
    'validate_bank_card',
    'validate_email',
    'is_public_suffix_email',
    'luhn_check',
    'partial_mask_uscc',
    'partial_mask_bank_card',
    'partial_mask_email',
    'partial_mask_vat_invoice',
    'partial_mask_taxpayer_id_15',
    'partial_mask_bank_account',
    'write_partial_masks',
    'clear_pdf_metadata',
    'USCC_CHARSET',
    'USCC_WEIGHTS',
    'USCC_CATEGORY_CODES',
    'EMAIL_RE',
    'EMAIL_PUBLIC_SUFFIXES',
    'BANK_CARD_BIN_WHITELIST',
    # Phase 2 (02-02-engine-expansion) — 3 new validators + 2 context helpers + 2 context whiteslists
    'validate_taxpayer_id_15',
    'has_vat_invoice_context',
    'has_bank_account_context',
    'VAT_INVOICE_CONTEXTS',
    'BANK_ACCOUNT_CONTEXTS',
    # Phase 3 (03-word) — word_adapter 三函数 (D-13 公开导出)
    'collect_pii_word_hits',
    'locate_pii_hits_in_paragraph',
    'apply_pii_replacements_to_docx',
]  # noqa: E501


_LAZY_IMPORTS = {
    'PIIEngine':                 ('privacyguard.pii.engine', 'PIIEngine'),
    'PIIHit':                    ('privacyguard.pii.hits', 'PIIHit'),
    'TextUnit':                  ('privacyguard.pii.hits', 'TextUnit'),
    'validate_18_id':            ('privacyguard.pii.validators', 'validate_18_id'),
    'validate_15_id':            ('privacyguard.pii.validators', 'validate_15_id'),
    'upgrade_15_to_18':          ('privacyguard.pii.validators', 'upgrade_15_to_18'),
    'compute_check_digit':       ('privacyguard.pii.validators', 'compute_check_digit'),
    'is_mobile_segment':         ('privacyguard.pii.validators', 'is_mobile_segment'),
    'PHONE_PERSONAL_PREFIX_3':   ('privacyguard.pii.validators', 'PHONE_PERSONAL_PREFIX_3'),
    'PHONE_EXCLUDED_PREFIX_3':   ('privacyguard.pii.validators', 'PHONE_EXCLUDED_PREFIX_3'),
    'PHONE_EXCLUDED_PREFIX_4':   ('privacyguard.pii.validators', 'PHONE_EXCLUDED_PREFIX_4'),
    'apply_pii_redactions':      ('privacyguard.pii.pdf_adapter', 'apply_pii_redactions'),
    'collect_pii_rects':         ('privacyguard.pii.pdf_adapter', 'collect_pii_rects'),
    # Phase 2 (02-01-tracer) — 13 new lazy exports
    'validate_uscc':             ('privacyguard.pii.validators', 'validate_uscc'),
    'validate_bank_card':        ('privacyguard.pii.validators', 'validate_bank_card'),
    'validate_email':            ('privacyguard.pii.validators', 'validate_email'),
    'is_public_suffix_email':    ('privacyguard.pii.validators', 'is_public_suffix_email'),
    'luhn_check':                ('privacyguard.pii.validators', 'luhn_check'),
    'USCC_CHARSET':              ('privacyguard.pii.validators', 'USCC_CHARSET'),
    'USCC_WEIGHTS':              ('privacyguard.pii.validators', 'USCC_WEIGHTS'),
    'USCC_CATEGORY_CODES':       ('privacyguard.pii.validators', 'USCC_CATEGORY_CODES'),
    'EMAIL_RE':                  ('privacyguard.pii.validators', 'EMAIL_RE'),
    'EMAIL_PUBLIC_SUFFIXES':     ('privacyguard.pii.validators', 'EMAIL_PUBLIC_SUFFIXES'),
    'BANK_CARD_BIN_WHITELIST':   ('privacyguard.pii.validators', 'BANK_CARD_BIN_WHITELIST'),
    'partial_mask_uscc':         ('privacyguard.pii.mask', 'partial_mask_uscc'),
    'partial_mask_bank_card':    ('privacyguard.pii.mask', 'partial_mask_bank_card'),
    'partial_mask_email':        ('privacyguard.pii.mask', 'partial_mask_email'),
    'partial_mask_vat_invoice':  ('privacyguard.pii.mask', 'partial_mask_vat_invoice'),
    'partial_mask_taxpayer_id_15': ('privacyguard.pii.mask', 'partial_mask_taxpayer_id_15'),
    'partial_mask_bank_account': ('privacyguard.pii.mask', 'partial_mask_bank_account'),
    'write_partial_masks':       ('privacyguard.pii.pdf_adapter', 'write_partial_masks'),
    'clear_pdf_metadata':        ('privacyguard.pii.pdf_adapter', 'clear_pdf_metadata'),
    # Phase 2 (02-02-engine-expansion) — 5 new lazy exports
    'validate_taxpayer_id_15':   ('privacyguard.pii.validators', 'validate_taxpayer_id_15'),
    'has_vat_invoice_context':   ('privacyguard.pii.validators', 'has_vat_invoice_context'),
    'has_bank_account_context':  ('privacyguard.pii.validators', 'has_bank_account_context'),
    'VAT_INVOICE_CONTEXTS':      ('privacyguard.pii.validators', 'VAT_INVOICE_CONTEXTS'),
    'BANK_ACCOUNT_CONTEXTS':     ('privacyguard.pii.validators', 'BANK_ACCOUNT_CONTEXTS'),
    # Phase 3 (03-word) — word_adapter 三函数 (D-13 + OPS-03 懒加载纪律)
    'collect_pii_word_hits':          ('privacyguard.pii.word_adapter', 'collect_pii_word_hits'),
    'locate_pii_hits_in_paragraph':   ('privacyguard.pii.word_adapter', 'locate_pii_hits_in_paragraph'),
    'apply_pii_replacements_to_docx': ('privacyguard.pii.word_adapter', 'apply_pii_replacements_to_docx'),
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
