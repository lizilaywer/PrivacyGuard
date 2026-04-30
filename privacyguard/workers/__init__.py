"""
PrivacyGuard Workers 模块

v36.5: 模块化拆分
"""

from importlib import import_module

__all__ = [
    'ImageMergeWorker',
    'OCRWorker',
    'WordWorker',
]

_LAZY_IMPORTS = {
    'ImageMergeWorker': ('privacyguard.workers.image_merge', 'ImageMergeWorker'),
    'OCRWorker': ('privacyguard.workers.ocr_worker', 'OCRWorker'),
    'WordWorker': ('privacyguard.workers.word_worker', 'WordWorker'),
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
