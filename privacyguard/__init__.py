"""
PrivacyGuard 脱敏卫士

v36.5: 模块化重构版本
"""

__version__ = "37.0"
__app_name__ = "PrivacyGuard 脱敏卫士"

# 导出工具模块
from .utils import (
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

from .workers import ImageMergeWorker, OCRWorker, WordWorker

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
]
