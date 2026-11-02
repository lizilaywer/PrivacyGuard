"""
PrivacyGuard OCR 模块
提供统一的 OCR 接口 - v37.4.0: 单引擎架构（RapidOCR）
v37.7.3: 修复 PyInstaller 打包时的相对导入问题
v37.7.7: 改为懒加载，避免 import privacyguard.ocr 时拉起 manager/rapidocr 链
v37.8.11 P1-2: 印章/签名检测算法从 ocr_worker.py 外提到独立模块
"""

from importlib import import_module

__all__ = [
    'BaseOCREngine',
    'OCRResult',
    'CharInfo',
    'RapidOCREngine',
    'OCREngineManager',
    # v37.8.11 P1-2: 检测算法（从 ocr_worker.py 外提）
    'detect_seals',
    'detect_star_in_roi',
    'ocr_seal_region',
    'detect_signatures',
    'SEAL_KEYWORDS',
]

_LAZY_IMPORTS = {
    'BaseOCREngine': ('privacyguard.ocr.base', 'BaseOCREngine'),
    'OCRResult': ('privacyguard.ocr.base', 'OCRResult'),
    'CharInfo': ('privacyguard.ocr.base', 'CharInfo'),
    'RapidOCREngine': ('privacyguard.ocr.rapidocr', 'RapidOCREngine'),
    'OCREngineManager': ('privacyguard.ocr.manager', 'OCREngineManager'),
    # v37.8.11 P1-2: 检测算法
    'detect_seals': ('privacyguard.ocr.seal_detection', 'detect_seals'),
    'detect_star_in_roi': ('privacyguard.ocr.seal_detection', 'detect_star_in_roi'),
    'ocr_seal_region': ('privacyguard.ocr.seal_detection', 'ocr_seal_region'),
    'detect_signatures': ('privacyguard.ocr.signature_detection', 'detect_signatures'),
    'SEAL_KEYWORDS': ('privacyguard.ocr.seal_detection', 'SEAL_KEYWORDS'),
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
