"""
PrivacyGuard 脱敏卫士

v36.5: 模块化重构版本
v37.7.3: 修复 PyInstaller 打包时的相对导入问题
"""

from importlib import import_module
from pathlib import Path


def _read_version():
    version_file = Path(__file__).resolve().parent.parent / "version.txt"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "1.0.0"


__version__ = _read_version()
__app_name__ = "PrivacyGuard 脱敏卫士"

# 导出工具模块（使用绝对导入，修复 PyInstaller 打包问题）
from privacyguard.utils import (
    PrivacyAppError,
    ConversionError,
    FileFormatError,
    SecurityError,
    MemoryLimitError,
    WorkerCancelledError,
    TempFileManager,
    validate_safe_path,
    resource_path,
)

__all__ = [
    '__version__',
    '__app_name__',
    # 异常类
    'PrivacyAppError',
    'ConversionError',
    'FileFormatError',
    'SecurityError',
    'MemoryLimitError',
    'WorkerCancelledError',
    # 工具类
    'TempFileManager',
    # 工具函数
    'validate_safe_path',
    'resource_path',
    # Workers
    'ImageMergeWorker',
    'OCRWorker',
    'WordWorker',
    # OCR 模块
    'OCREngineManager',
    'OCRResult',
    'CharInfo',
    # Phase 1 PII 引擎（v38.x）
    'PIIEngine',
    'PIIHit',
    'TextUnit',
    'validate_18_id',
    'validate_15_id',
    'is_mobile_segment',
    'apply_pii_redactions',
    'collect_pii_rects',
    # Phase 2 (02-01-tracer) — partial mask + metadata clear + new validators
    'validate_uscc',
    'validate_bank_card',
    'validate_email',
    'is_public_suffix_email',
    'partial_mask_uscc',
    'partial_mask_bank_card',
    'partial_mask_email',
    'partial_mask_vat_invoice',
    'partial_mask_taxpayer_id_15',
    'partial_mask_bank_account',
    'write_partial_masks',
    'clear_pdf_metadata',
    # Phase 2 (02-02-engine-expansion) — 3 new top-level forwards
    'validate_taxpayer_id_15',
    'has_vat_invoice_context',
    'has_bank_account_context',
]

_LAZY_IMPORTS = {
    'ImageMergeWorker': ('privacyguard.workers', 'ImageMergeWorker'),
    'OCRWorker': ('privacyguard.workers', 'OCRWorker'),
    'WordWorker': ('privacyguard.workers', 'WordWorker'),
    'OCREngineManager': ('privacyguard.ocr', 'OCREngineManager'),
    'OCRResult': ('privacyguard.ocr', 'OCRResult'),
    'CharInfo': ('privacyguard.ocr', 'CharInfo'),
    # Phase 1 PII 引擎（v38.x）
    'PIIEngine': ('privacyguard.pii.engine', 'PIIEngine'),
    'PIIHit': ('privacyguard.pii.hits', 'PIIHit'),
    'TextUnit': ('privacyguard.pii.hits', 'TextUnit'),
    'validate_18_id': ('privacyguard.pii.validators', 'validate_18_id'),
    'validate_15_id': ('privacyguard.pii.validators', 'validate_15_id'),
    'is_mobile_segment': ('privacyguard.pii.validators', 'is_mobile_segment'),
    'apply_pii_redactions': ('privacyguard.pii.pdf_adapter', 'apply_pii_redactions'),
    'collect_pii_rects': ('privacyguard.pii.pdf_adapter', 'collect_pii_rects'),
    # Phase 2 (02-01-tracer) — top-level forwards
    'validate_uscc': ('privacyguard.pii', 'validate_uscc'),
    'validate_bank_card': ('privacyguard.pii', 'validate_bank_card'),
    'validate_email': ('privacyguard.pii', 'validate_email'),
    'is_public_suffix_email': ('privacyguard.pii', 'is_public_suffix_email'),
    'partial_mask_uscc': ('privacyguard.pii', 'partial_mask_uscc'),
    'partial_mask_bank_card': ('privacyguard.pii', 'partial_mask_bank_card'),
    'partial_mask_email': ('privacyguard.pii', 'partial_mask_email'),
    'partial_mask_vat_invoice': ('privacyguard.pii', 'partial_mask_vat_invoice'),
    'partial_mask_taxpayer_id_15': ('privacyguard.pii', 'partial_mask_taxpayer_id_15'),
    'partial_mask_bank_account': ('privacyguard.pii', 'partial_mask_bank_account'),
    'write_partial_masks': ('privacyguard.pii', 'write_partial_masks'),
    'clear_pdf_metadata': ('privacyguard.pii', 'clear_pdf_metadata'),
    # Phase 2 (02-02-engine-expansion) — 3 new top-level forwards
    'validate_taxpayer_id_15': ('privacyguard.pii', 'validate_taxpayer_id_15'),
    'has_vat_invoice_context': ('privacyguard.pii', 'has_vat_invoice_context'),
    'has_bank_account_context': ('privacyguard.pii', 'has_bank_account_context'),
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
