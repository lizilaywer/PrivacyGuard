"""
PrivacyGuard 工具模块

v36.5: 模块化拆分
v37.0: 添加配置系统
v37.7.3: 修复 PyInstaller 打包时的相对导入问题
"""

# 使用绝对导入（修复 PyInstaller 打包问题）
from privacyguard.utils.exceptions import (
    PrivacyAppError,
    ConversionError,
    FileFormatError,
    SecurityError,
    MemoryLimitError,
    WorkerCancelledError
)

from privacyguard.utils.temp_manager import TempFileManager

from privacyguard.utils.security import validate_safe_path, resource_path

from privacyguard.utils.config import (
    ConfigManager,
    ConfigError,
    ConfigValidationError,
    ConfigNotFoundError,
    DEFAULT_CONFIG,
    get_config,
    get_config_value
)

# v37.8.11 P0-3: 统一日志框架
from privacyguard.utils.logger import init_logging, get_logger, is_initialized

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
    # 日志（v37.8.11 P0-3）
    'init_logging',
    'get_logger',
    'is_initialized',
]
