"""
PrivacyGuard 工具模块

v36.5: 模块化拆分
v37.0: 添加配置系统
v37.7.3: 修复 PyInstaller 打包时的相对导入问题
v37.7.6: G2 — 添加 clear_word_core_properties 懒加载入口 (D-15 Word 子项)
"""

from importlib import import_module

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
    # Phase 3 (G2 Gap 4): Word core_properties 清除 helper
    'clear_word_core_properties',
]


_LAZY_IMPORTS = {
    'clear_word_core_properties': ('privacyguard.utils.word_props', 'clear_word_core_properties'),
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
