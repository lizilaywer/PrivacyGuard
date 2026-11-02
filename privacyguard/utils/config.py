"""
PrivacyGuard 配置管理模块

v37.0: 配置系统实现 - 支持 JSON 配置文件、热重载、向后兼容
"""

import json
import os
import threading
from typing import Any, Callable, Dict, List, Optional
import logging
from privacyguard.utils.app_paths import default_config_path

# cp118: 统一日志（替代模块内散落的 print）
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置错误基类"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误"""
    pass


class ConfigNotFoundError(ConfigError):
    """配置文件未找到"""
    pass


def _person_name_rule():
    """cp_person_name: 生成"称谓人名"规则的默认配置。

    pattern 由 privacyguard.ocr.person_name（纯 re 模块，零重型依赖，
    不触发 RapidOCR 懒加载链）动态生成——称谓全集交替 + 命名组 pgname。
    用户自定义 redaction.person_name_titles 时，main.py 启动会重生成并
    覆写 config.json 里的 pattern 值（_ensure_preset_rule）。
    """
    from privacyguard.ocr.person_name import build_person_name_pattern, DEFAULT_TITLES
    return {
        "pattern": build_person_name_pattern(DEFAULT_TITLES),
        "enabled": False,
        "description": "cp_person_name: 识别称谓词（被告人/原告/辩护人等）后的"
                       "人名并遮罩（发现即全页遮同名）；关闭时零开销。称谓词表"
                       "可在 redaction.person_name_titles 自定义",
    }


# 默认配置常量
DEFAULT_CONFIG = {
    "version": "1.0",
    "app": {
        "name": "PrivacyGuard 脱敏卫士",
        "window": {
            "default_width": 1300,
            "default_height": 900,
            "min_width": 1120,
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
                # v37.7.18 cp49: 收紧正则，避免误识别横线/无关数字串
                # - 18/15位均加省级前缀白名单（11-15/21-23/31-37/41-46/50-54/61-65）
                # - 月(01-12)+日(01-31) 结构校验
                "pattern": r"(?<!\d)((?:1[1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4]|6[1-5])\d{4}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]|(?:1[1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4]|6[1-5])\d{4}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3})(?!\d)",
                "enabled": True,
                "description": "匹配15位或18位身份证号码（v37.7.18 收紧：省级前缀+月日结构校验）"
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
            # cp135: 出生信息+日期整体遮罩（法律文书当事人身份段高频）
            # 四种模式：①"出生年月[日]？/出生日期：1990年1月1日"标签+日期整体遮
            # ②"出生于1990年1月1日" ③"1990年1月1日出生"（日期+出生）
            # ④"1990年12月11日生"（日期+单"生"；"生"后须非汉字，防"生产/生效"误报）
            # 仅当"出生/生"字样与日期邻接时命中，纯日期仍由"日期时间"规则处理
            "出生年月": {
                "pattern": (
                    r"(?:出生年月[日]?|出生日期|出生于?)\s*[:：]?\s*"
                    r"(?:\d{4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?|\d{4}[-./]\d{1,2}(?:[-./]\d{1,2})?)"
                    r"|(?:\d{4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?|\d{4}[-./]\d{1,2}(?:[-./]\d{1,2})?)"
                    r"\s*(?:出生|生(?![\u4e00-\u9fa5]))"
                ),
                "enabled": True,
                "description": "cp135: 出生信息+日期整体遮罩（出生年月：1990年1月1日 / 出生于1990年1月 / 1990年1月1日出生 / 1990年12月11日生）"
            },
            # cp135: 住址规则——住址/户籍地/住所地 标签+地址整体遮，或省+市+区县三级锚定的纯地址
            # 遮到终止符（栋/组/号/室 或数字）为止；数字后紧跟年/月/日（日期）不命中防误报
            # 行政头穷举 34 个省级行政区名（防止贪婪字符类吃掉地址前缀，如"被告住安徽省"）
            "住址": {
                "pattern": (
                    r"(?:住址|户籍地|住所地)\s*[:：]?\s*[\u4e00-\u9fa5A-Za-z\d]*(?:栋|组|号|室)"
                    r"|(?:住址|户籍地|住所地)\s*[:：]?\s*[\u4e00-\u9fa5A-Za-z\d]*\d+(?![年月日\d])"
                    r"|(?:(?:河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾)省|(?:内蒙古自治区|广西壮族自治区|西藏自治区|宁夏回族自治区|新疆维吾尔自治区))"
                    r"[\u4e00-\u9fa5]{2,12}市[\u4e00-\u9fa5]{2,12}(?:区|县|旗)[\u4e00-\u9fa5A-Za-z\d]*(?:栋|组|号|室)"
                    r"|(?:(?:河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾)省|(?:内蒙古自治区|广西壮族自治区|西藏自治区|宁夏回族自治区|新疆维吾尔自治区))"
                    r"[\u4e00-\u9fa5]{2,12}市[\u4e00-\u9fa5]{2,12}(?:区|县|旗)[\u4e00-\u9fa5A-Za-z\d]*\d+(?![年月日\d])"
                ),
                "enabled": True,
                "description": "cp135: 住址整体遮罩（住址/户籍地/住所地：… 或 省+市+区县 开头的地址，遮到 栋/组/号/室/数字 为止）"
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
            },
            # cp70: 新增预设规则（法律文书高频，正则+校验位控误报）
            "统一社会信用代码": {
                "pattern": r"(?<![0-9A-Za-z])[0-9A-HJ-NP-RTUWXY]{2}\d{6}[0-9A-HJ-NP-RTUWXY]{10}(?![0-9A-Za-z])",
                "enabled": True,
                "description": "cp70: 18位统一社会信用代码，命中后经mod31-3校验位二次校验"
            },
            "车牌号": {
                "pattern": r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]",
                "enabled": True,
                "description": "cp70: 中国车牌号（普通5位/新能源6位）"
            },
            "固定电话": {
                "pattern": r"(?<!\d)0\d{2,3}[-\s]?\d{7,8}(?:[-\s]?\d{1,4})?(?!\d)",
                "enabled": True,
                "description": "cp70: 固定电话/座机"
            },
            "护照号": {
                "pattern": r"(?<![A-Za-z0-9])[EGDSP]\d{8}(?![A-Za-z0-9])",
                "enabled": False,
                "description": "cp70: 中国护照号（涉外案件）；默认关闭"
            },
            "港澳台通行证": {
                "pattern": r"(?<![A-Za-z0-9])[CcWw]\d{8}(?![A-Za-z0-9])",
                "enabled": False,
                "description": "cp70: 港澳台通行证；默认关闭"
            },
            "车架号": {
                "pattern": r"(?<![A-Za-z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-Za-z0-9])",
                "enabled": False,
                "description": "cp70: 车架号VIN（17位），命中后经第9位校验位二次校验；默认关闭"
            },
            "IP地址": {
                "pattern": r"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?!\d)",
                "enabled": False,
                "description": "cp70: IPv4地址；默认关闭"
            },
            "印章": {
                "pattern": "__SEAL_DETECTION__",
                "enabled": False,
                "description": "v37.7.19 cp51-cp56: 多特征融合检测红/蓝印章（颜色+形状+五角星+OCR文字验证）。已知限制：公章识别准确率有待提高（变形/淡色/复杂背景印章仍有漏检或误判），后续版本考虑引入深度学习模型"
            },
            "签名手印": {
                "pattern": "__SIGNATURE_DETECTION__",
                "enabled": False,
                "description": "cp60: 自动检测并遮罩手写签名+按手印区域"
            },
            # cp_person_name: 诉讼文书称谓人名（阶段1 纯词表；关闭时引擎零开销）
            "称谓人名": _person_name_rule()
        },
        "replacement_text": "*",
        "custom_keywords": "卷\n执\n违",
        # v37.7.13 cp43: 自定义关键词替换规则（与 config.json 同步）
        "custom_keyword_rules": [
            {"enabled": True, "find": "卷", "replace": ""},
            {"enabled": True, "find": "执", "replace": ""},
            {"enabled": True, "find": "违", "replace": ""}
        ],
        "manual_replace_prompt": True,
        # cp_bookmark: 书签栏脱敏开关（勾选后导出时把关键词规则应用到 PDF 书签标题）
        "bookmark_redact_enabled": False,
        # cp_person_name: 自定义称谓词表（空=内置诉讼称谓全集；修改后重启生效）
        "person_name_titles": [],
        "scan": {
            # cp120: 默认从 1.0 提升到 1.5（与 UI "推荐" 标注一致）。
            # 1.0 渲染分辨率过低，OCR 文本检测模型会漏检小字/落款/特殊位置的文字
            # （实测：扫描件落款处"池州市祥瑞物业服务有限"在 1.0x 下整行漏检，
            # 1.5x/2.0x 均正常检测）。1.5x 性能开销可接受，准确性显著优于 1.0x。
            "default_level": 1.5,
            "available_levels": [1.0, 1.5, 2.0],
            "level_labels": {
                "1.0": "普通 (1.0x)",
                "1.5": "标准 (1.5x 推荐)",
                "2.0": "高精 (2.0x)"
            }
        },
        "offset": {
            "x_range": [-20, 50],
            "w_range": [-20, 20],
            "default_x": 0,
            "default_w": 0
        },
        "precise_locator": {
            # v37.7.18 cp50: 预留配置项
            # 当前 main.py 与 ocr_worker.py 未实际读取，仅由 test_config_alignment.py
            # 强制要求字段存在。若未来需要"精确定位器"特性（如字符级坐标对齐），
            # 在此启用；在此之前不要删除本字段以免破坏测试。
            "enabled": True
        }
    },
    "ocr": {
        "min_rect_width": 5,
        "progress_update_interval": 0.05,
        "zoom_min": 0.5,
        "zoom_max": 4.0,
        "box_adjust_ratio": 0.0,
        "box_adjust_range": [-0.3, 0.5]
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
        return default_config_path()

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
                    logger.warning("[ConfigManager] 配置文件格式错误: %s", e)
                    logger.warning("[ConfigManager] 使用默认配置")
                except Exception as e:
                    logger.warning("[ConfigManager] 加载配置文件失败: %s", e)
                    logger.warning("[ConfigManager] 使用默认配置")

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

    def set(self, path: str, value: Any, persist: bool = True) -> bool:
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
                logger.warning("[ConfigManager] 设置配置失败: %s", e)
                return False

    def _save_config(self) -> bool:
        """保存配置到文件（原子写入：先写临时文件再 os.replace，防止崩溃导致配置损坏）"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self._config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            # 原子写入：写临时文件 → os.replace 覆盖目标
            import tempfile as _tf
            fd, tmp_path = _tf.mkstemp(
                dir=config_dir or '.', suffix=".tmp", prefix="pg_config_")
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(self._config, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self._config_path)
            except Exception:
                # 写入或替换失败：清理临时文件
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
            return True
        except Exception as e:
            logger.warning("[ConfigManager] 保存配置文件失败: %s", e)
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
                logger.warning("[ConfigManager] 重载配置失败: %s", e)
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
                logger.warning("[ConfigManager] 回调执行错误: %s", e)

    def _notify_reload(self, old_config: Dict, new_config: Dict) -> None:
        """通知所有配置重载"""
        # 简化为通知根路径变更
        for callback in self._callbacks:
            try:
                callback("", old_config, new_config)
            except Exception as e:
                logger.warning("[ConfigManager] 重载回调执行错误: %s", e)

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

    def update_redaction_rules(self, rules: Dict[str, Any], persist: bool = True) -> bool:
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
            logger.warning("[ConfigManager] 导出模板失败: %s", e)
            return False


# 便捷函数
def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager(config_path)


def get_config_value(path: str, default: Any = None, config_path: Optional[str] = None) -> Any:
    """便捷函数：获取配置值"""
    config = ConfigManager(config_path)
    return config.get(path, default)
