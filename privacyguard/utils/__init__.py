"""
PrivacyGuard 工具模块

v36.5: 模块化拆分
v37.0: 添加配置系统
"""

from .exceptions import (
    PrivacyAppError,
    ConversionError,
    FileFormatError,
    SecurityError,
    MemoryLimitError,
    WorkerCancelledError
)

from .temp_manager import TempFileManager

from .security import validate_safe_path, resource_path

from .config import (
    ConfigManager,
    ConfigError,
    ConfigValidationError,
    ConfigNotFoundError,
    DEFAULT_CONFIG,
    get_config,
    get_config_value
)

__all__ = [
    # 异常类
    'PrivacyAppError',
    'ConversionError',
    'FileFormatError',
    'SecurityError',
    'MemoryLimitError',
    'WorkerCancelledError',
    # 配置相关
    'ConfigManager',
    'ConfigError',
    'ConfigValidationError',
    'ConfigNotFoundError',
    'DEFAULT_CONFIG',
    'get_config',
    'get_config_value',
    # 工具类
    'TempFileManager',
    # 工具函数
    'validate_safe_path',
    'resource_path',
]
