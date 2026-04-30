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
        return "37.7.0"


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
]

_LAZY_IMPORTS = {
    'ImageMergeWorker': ('privacyguard.workers', 'ImageMergeWorker'),
    'OCRWorker': ('privacyguard.workers', 'OCRWorker'),
    'WordWorker': ('privacyguard.workers', 'WordWorker'),
    'OCREngineManager': ('privacyguard.ocr', 'OCREngineManager'),
    'OCRResult': ('privacyguard.ocr', 'OCRResult'),
    'CharInfo': ('privacyguard.ocr', 'CharInfo'),
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
