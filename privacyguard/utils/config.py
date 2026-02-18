"""
PrivacyGuard 配置管理模块

v37.0: 配置系统实现 - 支持 JSON 配置文件、热重载、向后兼容
"""

import json
import os
import threading
from typing import Any, Callable, Dict, List, Optional, Union
from pathlib import Path


class ConfigError(Exception):
    """配置错误基类"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误"""
    pass


class ConfigNotFoundError(ConfigError):
    """配置文件未找到"""
    pass


# 默认配置常量
DEFAULT_CONFIG = {
    "version": "1.0",
    "app": {
        "name": "PrivacyGuard 脱敏卫士",
        "window": {
            "default_width": 1300,
            "default_height": 900,
            "min_width": 900,
            "min_height": 600,
            "dialog_settings_width": 550,
            "dialog_settings_height": 700,
            "dialog_image_list_width": 600,
            "dialog_image_list_height": 500,
            "dialog_feedback_width": 480,
            "dialog_feedback_height": 600
        },
        "feedback_url": "https://fcnwakmkeuz7.feishu.cn/share/base/form/shrcnEM1JEbdIKzdB400egj9lHe"
    },
    "redaction": {
        "default_rules": {
            "身份证号": {
                "pattern": r"(?<!\d)([1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]|\d{15})(?!\d)",
                "enabled": True,
                "description": "匹配15位或18位身份证号码"
            },
            "手机号码": {
                "pattern": r"(?<!\d)(1[3-9]\d{9})(?!\d)",
                "enabled": True,
                "description": "匹配中国大陆手机号码"
            },
            "日期时间": {
                "pattern": r"\d{4}[年\-\.]\d{1,2}[月\-\.]\d{1,2}[日]?",
                "enabled": True,
                "description": "匹配日期格式"
            },
            "电子邮箱": {
                "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "enabled": True,
                "description": "匹配电子邮箱地址"
            },
            "银行卡号": {
                "pattern": r"(?<!\d)([1-9]\d{12,18})(?!\d)",
                "enabled": True,
                "description": "匹配13-19位银行卡号"
            }
        },
        "replacement_text": "[已脱敏]",
        "scan": {
            "default_level": 2.0,
            "available_levels": [1.5, 2.0, 3.0],
            "level_labels": {
                "1.5": "标准 (1.5x)",
                "2.0": "高精 (2.0x 推荐)",
                "3.0": "超精 (3.0x 最慢)"
            }
        },
        "offset": {
            "x_range": [-20, 20],
            "w_range": [-20, 20],
            "default_x": 0,
            "default_w": 0
        }
    },
    "ocr": {
        "min_rect_width": 5,
        "progress_update_interval": 0.05,
        "zoom_min": 0.5,
        "zoom_max": 4.0
    },
    "security": {
        "validate_paths": True,
        "allowed_extensions": [".pdf", ".doc", ".docx"]
    },
    "ui": {
        "theme": "auto",
        "animation_enabled": True,
        "show_tips": True
    },
    "advanced": {
        "debug_mode": False,
        "temp_cleanup_on_exit": True,
        "cv2_num_threads": 0,
        "omp_num_threads": 1
    }
}


class ConfigManager:
    """
    配置管理器单例类

    功能：
    - 加载和保存 JSON 配置文件
    - 默认配置 + 用户配置合并
    - 点分隔路径访问配置项
    - 配置验证
    - 变更监听回调
    - 线程安全

    用法：
        config = ConfigManager()  # 获取实例
        width = config.get("app.window.default_width", 1300)
        config.set("redaction.scan.default_level", 2.5, persist=True)
        rules = config.get_redaction_rules()
        config.reload()  # 热重载
    """

    _instance: Optional['ConfigManager'] = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> 'ConfigManager':
        """单例模式实现"""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认使用应用目录下的 config.json
        """
        if self._initialized:
            return

        self._lock = threading.RLock()
        self._config: Dict[str, Any] = {}
        self._callbacks: List[Callable[[str, Any, Any], None]] = []
        self._config_path: str = config_path or self._get_default_config_path()

        # 加载配置
        self._load_config()
        self._initialized = True

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 首先尝试应用目录
        app_dir = Path(__file__).parent.parent.parent
        config_path = app_dir / "config.json"

        # 如果应用目录不可写或不存在，使用用户目录
        try:
            if not os.access(app_dir, os.W_OK):
                raise PermissionError
        except (OSError, PermissionError):
            user_dir = Path.home() / ".privacyguard"
            user_dir.mkdir(exist_ok=True)
            config_path = user_dir / "config.json"

        return str(config_path)

    def _load_config(self) -> None:
        """加载配置文件，合并默认配置和用户配置"""
        with self._lock:
            # 从默认配置开始
            self._config = self._deep_copy(DEFAULT_CONFIG)

            # 如果配置文件存在，加载并合并
            if os.path.exists(self._config_path):
                try:
                    with open(self._config_path, 'r', encoding='utf-8') as f:
                        user_config = json.load(f)
                    self._merge_config(self._config, user_config)
                except json.JSONDecodeError as e:
                    print(f"[ConfigManager] 配置文件格式错误: {e}")
                    print(f"[ConfigManager] 使用默认配置")
                except Exception as e:
                    print(f"[ConfigManager] 加载配置文件失败: {e}")
                    print(f"[ConfigManager] 使用默认配置")

    def _deep_copy(self, obj: Any) -> Any:
        """深拷贝对象"""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        return obj

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """递归合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = self._deep_copy(value)

    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """获取嵌套配置值"""
        keys = path.split('.')
        current = config
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                raise KeyError(f"配置路径不存在: {path}")
            current = current[key]
        return current

    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> None:
        """设置嵌套配置值"""
        keys = path.split('.')
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def get(self, path: Optional[str] = None, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            path: 点分隔的配置路径，如 "app.window.default_width"
                  如果为 None，返回整个配置字典
            default: 默认值，当配置不存在时返回

        Returns:
            配置值或默认值
        """
        with self._lock:
            if path is None:
                return self._deep_copy(self._config)

            try:
                return self._get_nested_value(self._config, path)
            except KeyError:
                return default

    def set(self, path: str, value: Any, persist: bool = False) -> bool:
        """
        设置配置值

        Args:
            path: 点分隔的配置路径
            value: 新值
            persist: 是否立即保存到文件

        Returns:
            是否设置成功
        """
        with self._lock:
            old_value = self.get(path)
            try:
                self._set_nested_value(self._config, path, value)
                if persist:
                    self._save_config()
                # 触发回调
                self._notify_change(path, old_value, value)
                return True
            except Exception as e:
                print(f"[ConfigManager] 设置配置失败: {e}")
                return False

    def _save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self._config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ConfigManager] 保存配置文件失败: {e}")
            return False

    def save(self) -> bool:
        """手动保存配置到文件"""
        with self._lock:
            return self._save_config()

    def reload(self) -> bool:
        """
        重新加载配置文件（热重载）

        Returns:
            是否重载成功
        """
        with self._lock:
            try:
                old_config = self._deep_copy(self._config)
                self._load_config()
                # 触发所有变更回调
                self._notify_reload(old_config, self._config)
                return True
            except Exception as e:
                print(f"[ConfigManager] 重载配置失败: {e}")
                return False

    def on_change(self, callback: Callable[[str, Any, Any], None]) -> Callable:
        """
        注册配置变更回调

        Args:
            callback: 回调函数，接收 (path, old_value, new_value) 参数

        Returns:
            取消注册的函数
        """
        with self._lock:
            self._callbacks.append(callback)

        def unregister():
            with self._lock:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)

        return unregister

    def _notify_change(self, path: str, old_value: Any, new_value: Any) -> None:
        """触发配置变更回调"""
        for callback in self._callbacks:
            try:
                callback(path, old_value, new_value)
            except Exception as e:
                print(f"[ConfigManager] 回调执行错误: {e}")

    def _notify_reload(self, old_config: Dict, new_config: Dict) -> None:
        """通知所有配置重载"""
        # 简化为通知根路径变更
        for callback in self._callbacks:
            try:
                callback("", old_config, new_config)
            except Exception as e:
                print(f"[ConfigManager] 重载回调执行错误: {e}")

    def validate(self) -> List[str]:
        """
        验证配置有效性

        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []

        with self._lock:
            # 验证窗口尺寸
            window = self._config.get("app", {}).get("window", {})
            if window.get("default_width", 0) < window.get("min_width", 0):
                errors.append("app.window.default_width 必须 >= min_width")
            if window.get("default_height", 0) < window.get("min_height", 0):
                errors.append("app.window.default_height 必须 >= min_height")

            # 验证扫描级别
            scan = self._config.get("redaction", {}).get("scan", {})
            default_level = scan.get("default_level")
            available_levels = scan.get("available_levels", [])
            if default_level and available_levels:
                if default_level not in available_levels:
                    errors.append(f"redaction.scan.default_level {default_level} 不在可用列表中")

            # 验证偏移范围
            offset = self._config.get("redaction", {}).get("offset", {})
            x_range = offset.get("x_range", [-20, 20])
            w_range = offset.get("w_range", [-20, 20])
            if len(x_range) != 2 or x_range[0] > x_range[1]:
                errors.append("redaction.offset.x_range 格式错误")
            if len(w_range) != 2 or w_range[0] > w_range[1]:
                errors.append("redaction.offset.w_range 格式错误")

            # 验证脱敏规则
            rules = self._config.get("redaction", {}).get("default_rules", {})
            for name, rule in rules.items():
                if isinstance(rule, dict):
                    pattern = rule.get("pattern")
                    if not pattern:
                        errors.append(f"redaction.default_rules.{name}.pattern 不能为空")
                elif isinstance(rule, str):
                    # 旧格式兼容：直接是 pattern 字符串
                    if not rule:
                        errors.append(f"redaction.default_rules.{name} 不能为空")

        return errors

    def get_redaction_rules(self, enabled_only: bool = False) -> Dict[str, Any]:
        """
        获取脱敏规则

        Args:
            enabled_only: 是否只返回启用的规则

        Returns:
            规则字典，兼容新旧两种格式
        """
        with self._lock:
            rules = self._config.get("redaction", {}).get("default_rules", {})
            result = {}

            for name, rule in rules.items():
                if isinstance(rule, dict):
                    if enabled_only and not rule.get("enabled", True):
                        continue
                    result[name] = rule
                elif isinstance(rule, str):
                    # 旧格式兼容
                    if not enabled_only:
                        result[name] = {"pattern": rule, "enabled": True}
                else:
                    # 其他格式，尝试转换
                    if not enabled_only:
                        result[name] = {"pattern": str(rule), "enabled": True}

            return result

    def get_rule_pattern(self, rule_name: str) -> Optional[str]:
        """
        获取指定规则的 pattern

        Args:
            rule_name: 规则名称

        Returns:
            pattern 字符串，不存在返回 None
        """
        rules = self.get_redaction_rules()
        rule = rules.get(rule_name)
        if isinstance(rule, dict):
            return rule.get("pattern")
        elif isinstance(rule, str):
            return rule
        return None

    def update_redaction_rules(self, rules: Dict[str, Any], persist: bool = False) -> bool:
        """
        更新脱敏规则

        Args:
            rules: 新规则字典
            persist: 是否保存到文件

        Returns:
            是否更新成功
        """
        return self.set("redaction.default_rules", rules, persist=persist)

    def get_config_path(self) -> str:
        """获取当前配置文件路径"""
        return self._config_path

    def reset_to_default(self, persist: bool = True) -> bool:
        """
        重置为默认配置

        Args:
            persist: 是否保存到文件

        Returns:
            是否重置成功
        """
        with self._lock:
            old_config = self._deep_copy(self._config)
            self._config = self._deep_copy(DEFAULT_CONFIG)

            if persist:
                self._save_config()

            self._notify_reload(old_config, self._config)
            return True

    def export_template(self, template_path: str) -> bool:
        """
        导出配置模板

        Args:
            template_path: 模板文件路径

        Returns:
            是否导出成功
        """
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ConfigManager] 导出模板失败: {e}")
            return False


# 便捷函数
def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager(config_path)


def get_config_value(path: str, default: Any = None, config_path: Optional[str] = None) -> Any:
    """便捷函数：获取配置值"""
    config = ConfigManager(config_path)
    return config.get(path, default)
