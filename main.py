import sys
import os
import fitz  # PyMuPDF
import re
import cv2
import numpy as np
import time
import shutil
import threading  # v36.5: 线程锁支持
import atexit  # v36.2: 用于确保临时文件清理
import tempfile  # v36.2: 临时文件管理
import traceback  # v37.0.5: 异常追踪
from pathlib import Path
from bs4 import BeautifulSoup
from privacyguard.utils.security import validate_safe_path, resource_path
from privacyguard.utils.exceptions import (
    ConversionError,
)
# v37.8.11 P0-3: 统一日志框架，替代散落的 print 调试输出
from privacyguard.utils.logger import init_logging, get_logger, _resolve_log_dir

logger = get_logger("main")
from privacyguard.utils.temp_manager import TempFileManager
from privacyguard.utils.app_paths import default_config_path, resource_root
from privacyguard.utils.worker_lifecycle import defer_close_for_workers
from privacyguard.workers.image_merge import ImageMergeWorker
from privacyguard.workers.word_worker import WordWorker as _ModularWordWorker
from privacyguard.workers.ocr_worker import OCRWorker as _ModularOCRWorker
from privacyguard.utils.doc_converter import convert_doc_to_docx as _shared_convert_doc_to_docx
from privacyguard.report import build_redact_report  # cp87: 脱敏报告纯函数
from privacyguard.session_store import SessionStore  # cp88: 会话草稿存储
from privacyguard.utils.watermark import (  # v40.1.4: 水印纯函数（自 MainWindow 迁出）
    detect_watermark_spans, remove_watermark_from_stream)

from docx.opc.exceptions import PackageNotFoundError
from zipfile import BadZipFile  # cp113: 加密 docx（OLE2 容器）被 python-docx 当 ZIP 解析时抛此
from datetime import datetime  # cp87: 报告时间戳

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QGridLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QScrollArea, QMessageBox, QProgressBar, QFrame,
                             QDialog, QButtonGroup, QSizePolicy,
                             QTextBrowser, QLineEdit, QListWidget, QListWidgetItem,
                             QAbstractItemView, QTableWidget, QMenu,
                             QTableWidgetItem, QHeaderView)
from PyQt6.QtGui import QPixmap, QImage, QColor, QCursor, QIcon, QDesktopServices, QFont, QShortcut, QKeySequence, QPainter
from PyQt6.QtCore import (Qt, QRectF, QPoint, QMutex, QMutexLocker, QObject, pyqtSlot,
                          QSize, QTimer, QUrl, pyqtSignal, QThread, QEvent)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6 import sip

# 导入主题系统
from theme import Theme

# v37.0.4: 简化配置系统 - 直接从 JSON 文件加载
import json
import html  # cp81: 搜索结果片段 HTML 转义


def read_app_version():
    """从统一版本文件读取基础版本号。

    version.txt 是版本号唯一来源。失败时返回 "0.0.0" 而非具体旧版本号，
    避免硬编码的过期版本号误导（界面/标题栏会显示明显的 0.0.0 提示读取失败）。
    """
    version_file = Path(__file__).resolve().parent / "version.txt"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"

class SimpleConfig:
    """简化配置管理器 - 直接从 config.json 读取"""

    def __init__(self, config_path=None):
        self._config = {}
        self._config_path = config_path if config_path is not None else default_config_path()
        self._load_config()

    def _load_config(self):
        """加载配置文件（缺失时先从仓库模板初始化）"""
        try:
            if not os.path.exists(self._config_path):
                self._init_from_template()
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.error("[配置系统] 加载配置失败: %s", e)

    def _init_from_template(self):
        """config.json 缺失时从 config.json.template 生成本地配置

        运行时配置不入库（.gitignore 已忽略 config.json），
        仓库内只保留不含用户数据的模板。
        """
        template_path = self._config_path + '.template'
        if not os.path.exists(template_path):
            template_path = str(resource_root() / 'config.json.template')
        try:
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                template.pop('_comment', None)
                self._config = template
                self.save()
                logger.info("[配置系统] 已从 config.json.template 初始化本地配置")
        except (OSError, IOError, json.JSONDecodeError, TypeError) as e:
            logger.error("[配置系统] 从模板初始化配置失败: %s", e)

    def save(self):
        """将当前配置写回磁盘（原子写 + 0600 权限）。

        安全审计 v40.1.4：config.json 含 custom_keyword_rules（用户要抹掉的
        当事人姓名/案号等明文），收紧为 0600；tmp+replace 防写半截损坏。
        """
        tmp = self._config_path + ".tmp"
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self._config_path)), mode=0o700, exist_ok=True)
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self._config_path)
            return True
        except (OSError, IOError, TypeError) as e:
            logger.error("[配置系统] 保存配置失败: %s", e)
            try:
                os.remove(tmp)
            except OSError:
                pass
            return False

    def get(self, key, default=None):
        """获取配置值（支持点分隔路径）"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key, value, persist=True):
        """设置配置值（支持点分隔路径）

        Args:
            key: 配置键，支持点分隔路径
            value: 配置值
            persist: 是否立即保存到文件
        """
        keys = key.split('.')
        config = self._config
        # 遍历到倒数第二层，创建缺失的字典
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            elif not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        # 设置最终值
        config[keys[-1]] = value

        # 保存到文件
        if persist:
            self.save()

    def get_redaction_rules(self):
        """获取脱敏规则"""
        return self.get('redaction.default_rules', {})

# v37.7.18 cp49: 收紧身份证号正则（修复误识别横线/无关数字串）
# 旧正则 15 位分支 \d{15} 过于宽松，任何 15 位连续数字（案件号/统计号/电话拼接等）都被误匹配
# 新正则加省级前缀白名单 + 月(01-12)+日(01-31) 结构校验
IDCARD_PATTERN_V2 = (
    r"(?<!\d)("
    # 18位：省级前缀白名单 + 4位市县码 + 19XX/20XX + 月日 + 3位顺序 + 校验位
    r"(?:1[1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4]|6[1-5])\d{4}(?:19|20)\d{2}"
    r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]"
    r"|"
    # 15位：省级前缀白名单 + 4位市县码 + 2位年 + 月日 + 3位顺序
    r"(?:1[1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4]|6[1-5])\d{4}\d{2}"
    r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}"
    r")(?!\d)"
)
# 旧宽松正则（用于检测并自动迁移）
IDCARD_PATTERN_LEGACY = r"(?<!\d)([1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]|\d{15})(?!\d)"


def _migrate_legacy_idcard_pattern(cfg):
    """v37.7.18 cp49: 检测并升级 config.json 中的旧宽松身份证号正则。

    旧正则 15 位分支 \\d{15} 过于宽松，会误识别案件号、统计号、电话拼接等
    15 位连续数字串为身份证号。检测到旧正则时自动替换为 V2 严格版本并写回。

    Args:
        cfg: SimpleConfig 实例

    Returns:
        bool: 是否执行了升级
    """
    if not cfg:
        return False
    try:
        rules = cfg.get_redaction_rules()
        if not isinstance(rules, dict):
            return False
        rule = rules.get("身份证号")
        if not isinstance(rule, dict):
            return False
        pattern = rule.get("pattern", "")
        if pattern == IDCARD_PATTERN_LEGACY:
            cfg.set("redaction.default_rules.身份证号.pattern", IDCARD_PATTERN_V2,
                    persist=True)
            logger.info("[配置迁移] 身份证号正则已升级为 V2 严格版本（cp49）")
            return True
    except Exception as e:
        logger.error("[配置迁移] 身份证号正则升级失败: %s", e)
    return False


# cp135: "出生年月"预设规则正则——出生信息+日期整体遮罩（法律文书当事人身份段高频）
# 四种命中模式：
#   ① 标签+日期："出生年月：1990年1月1日" / "出生年月日：1990年1月1日" / "出生日期：1990年1月1日"
#   ② 出生于+日期："出生于1990年1月1日" / "出生于1990年1月"
#   ③ 日期+出生："1990年1月1日出生" / "1990年1月出生"
#   ④ 日期+生："1990年12月11日生" / "1990年12月生"（cp135 追加，法律文书高频简写）
# 日期支持中文式（1990年1月1日/1990年1月）与分隔符式（1990-1-1/1990.1.1）；
# 仅当"出生/生"字样与日期邻接时命中——纯日期（如落款"2023年5月1日"）仍由"日期时间"规则
# 单独处理，标签后无日期（如"出生年月不详"）不命中，避免误伤。
# 模式④防误报：单"生"后必须紧跟非汉字（标点/空白/结尾），否则视为"生产/生效/生态"等
# 词干不命中；完整"出生"无此限制（"1990年1月1日出生于合肥市"仍整体命中）。
BIRTHDATE_RULE_PATTERN = (
    r"(?:出生年月[日]?|出生日期|出生于?)\s*[:：]?\s*"
    r"(?:\d{4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?|\d{4}[-./]\d{1,2}(?:[-./]\d{1,2})?)"
    r"|(?:\d{4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?|\d{4}[-./]\d{1,2}(?:[-./]\d{1,2})?)"
    r"\s*(?:出生|生(?![\u4e00-\u9fa5]))"
)

# cp135 初版"出生年月"正则（无 ④ 日期+单"生" 模式）——用于识别已注入旧规则的
# config.json 并原地升级（见 _upgrade_legacy_birthdate_rule）
LEGACY_BIRTHDATE_RULE_PATTERN = (
    r"(?:出生年月[日]?|出生日期|出生于?)\s*[:：]?\s*"
    r"(?:\d{4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?|\d{4}[-./]\d{1,2}(?:[-./]\d{1,2})?)"
    r"|(?:\d{4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?|\d{4}[-./]\d{1,2}(?:[-./]\d{1,2})?)\s*出生"
)


def _ensure_birthdate_rule(cfg):
    """cp135: 向老 config.json 注入"出生年月"预设规则（薄包装，见 _ensure_preset_rule）。"""
    return _ensure_preset_rule(cfg, "出生年月", BIRTHDATE_RULE_PATTERN,
                               "cp135: 出生信息+日期整体遮罩（出生年月：1990年1月1日 / 出生于1990年1月 / 1990年1月1日出生 / 1990年12月11日生）")


# cp135: "住址"预设规则正则——住址/户籍地/住所地 标签+地址整体遮，或省+市+区县纯地址
# 命中模式：
#   ① 标签+地址："住址：/户籍地：/住所地：" 后的地址串，遮到终止符（栋/组/号/室）为止
#      例："住址：安徽省池州市贵池区牛头山镇川山组" → 整串遮罩
#   ② 标签+数字结尾："住址：…岐山村111"（无栋组号室，以数字终止）
#   ③④ 无标签纯地址：省+市+区县 三级行政区划锚定（防"安徽省2023年统计"类误报），
#      同样遮到终止符或数字为止。例："安徽省池州市贵池区牛头山镇东村17号"
# 防误报设计：
#   - 数字终止符后紧跟 年/月/日（日期结构）不命中："庐江县2023年人口" 不误伤
#   - 标签后无地址内容（"户籍地：不详"/"住所地：待查明"）不命中
#   - 行政头穷举 34 个省级行政区名（贪婪字符类 [\u4e00-\u9fa5]{2,10}省 会吃掉
#     地址前缀——"被告住安徽省"会被连"被告住"一起遮；穷举后只锚定"安徽省"起）
#   - 直辖市地址（无省级行政头，如"北京市朝阳区…"）走标签模式①②
ADDRESS_RULE_PATTERN = (
    r"(?:住址|户籍地|住所地)\s*[:：]?\s*[\u4e00-\u9fa5A-Za-z\d]*(?:栋|组|号|室)"
    r"|(?:住址|户籍地|住所地)\s*[:：]?\s*[\u4e00-\u9fa5A-Za-z\d]*\d+(?![年月日\d])"
    r"|(?:(?:河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾)省|(?:内蒙古自治区|广西壮族自治区|西藏自治区|宁夏回族自治区|新疆维吾尔自治区))"
    r"[\u4e00-\u9fa5]{2,12}市[\u4e00-\u9fa5]{2,12}(?:区|县|旗)[\u4e00-\u9fa5A-Za-z\d]*(?:栋|组|号|室)"
    r"|(?:(?:河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|台湾)省|(?:内蒙古自治区|广西壮族自治区|西藏自治区|宁夏回族自治区|新疆维吾尔自治区))"
    r"[\u4e00-\u9fa5]{2,12}市[\u4e00-\u9fa5]{2,12}(?:区|县|旗)[\u4e00-\u9fa5A-Za-z\d]*\d+(?![年月日\d])"
)


def _ensure_preset_rule(cfg, rule_name, pattern, description, enabled=True):
    """cp135: 向老 config.json 注入新增预设规则（通用）。

    config.json 是运行时持久文件（git-ignored），新增预设规则不会自动出现在
    已有配置中；参照 _migrate_legacy_idcard_pattern 模式，启动时检测缺失则补写。
    用户已自定义过同名规则（含手动删除后重建）则不覆盖。

    Args:
        cfg: SimpleConfig 实例
        rule_name: 规则名（redaction.default_rules 下的键）
        pattern: 正则字符串
        description: 规则描述
        enabled: 注入时的默认启用状态（cp_person_name 称谓人名默认 False）

    Returns:
        bool: 是否执行了注入
    """
    if not cfg:
        return False
    try:
        rules = cfg.get_redaction_rules()
        if not isinstance(rules, dict):
            return False
        if rule_name in rules:
            return False
        cfg.set(f"redaction.default_rules.{rule_name}", {
            "pattern": pattern,
            "enabled": enabled,
            "description": description,
        }, persist=True)
        logger.info("[配置迁移] 已注入新预设规则「%s」（cp135）", rule_name)
        return True
    except Exception as e:
        logger.error("[配置迁移] 注入预设规则「%s」失败: %s", rule_name, e)
        return False


def _upgrade_legacy_birthdate_rule(cfg):
    """cp135: 升级已注入旧版"出生年月"正则的 config.json（新增 日期+单"生" 模式）。

    cp135 初版注入的正则缺"1990年12月11日生"（日期+单"生"）模式；已运行过初版的
    config.json 中仍是旧正则（_ensure_preset_rule 只补缺失不覆盖）。此处按旧正则
    原值识别并原地升级；用户自定义过正则（既非旧值也非新值）则不动。

    Args:
        cfg: SimpleConfig 实例

    Returns:
        bool: 是否执行了升级
    """
    if not cfg:
        return False
    try:
        rules = cfg.get_redaction_rules()
        if not isinstance(rules, dict):
            return False
        cur = rules.get("出生年月")
        if not isinstance(cur, dict):
            return False
        if cur.get("pattern") != LEGACY_BIRTHDATE_RULE_PATTERN:
            return False
        cfg.set("redaction.default_rules.出生年月.pattern",
                BIRTHDATE_RULE_PATTERN, persist=True)
        logger.info("[配置迁移] 已升级预设规则「出生年月」正则（cp135：新增 日期+生 模式）")
        return True
    except Exception as e:
        logger.error("[配置迁移] 升级出生年月规则失败: %s", e)
        return False


# 初始化配置
config = SimpleConfig()
# v37.7.18 cp49: 自动迁移旧宽松身份证号正则
_migrate_legacy_idcard_pattern(config)
# cp135: 新增"出生年月"/"住址"预设规则，老 config.json 注入（详见函数注释）
_ensure_birthdate_rule(config)
# cp135: 初版注入的"出生年月"正则升级（新增 日期+单"生" 模式），须在 DEFAULT_RULES 构建前
_upgrade_legacy_birthdate_rule(config)
_ensure_preset_rule(config, "住址", ADDRESS_RULE_PATTERN,
                    "cp135: 住址整体遮罩（住址/户籍地/住所地：… 或 省+市+区县 开头的地址，遮到 栋/组/号/室/数字 为止）")

# cp_person_name: 称谓人名规则——pattern 由词表生成（用户自定义 titles 时重生成覆写）。
# 默认关闭（enabled=False）：关闭时称谓引擎零开销（pattern 不进 active_rules）。
from privacyguard.ocr.person_name import build_person_name_pattern, DEFAULT_TITLES  # noqa: E402

def _current_person_name_pattern(cfg):
    titles = cfg.get("redaction.person_name_titles", []) if cfg else []
    titles = [t for t in (titles or []) if isinstance(t, str) and t.strip()]
    return build_person_name_pattern(titles if titles else DEFAULT_TITLES)

_PERSON_NAME_DESC = (
    "cp_person_name: 识别称谓词（被告人/原告/辩护人等）后的人名并遮罩"
    "（发现即全页遮同名）；关闭时零开销。称谓词表可在 redaction.person_name_titles 自定义"
)
_ensure_preset_rule(config, "称谓人名", _current_person_name_pattern(config),
                    _PERSON_NAME_DESC, enabled=False)
# 已有规则的 pattern 与当前词表生成的值不一致（用户改了 titles 或内置词表升级）→ 覆写同步。
# enabled 状态不动（尊重用户的勾选偏好）。
try:
    _rules_check = config.get_redaction_rules() if config else {}
    if isinstance(_rules_check, dict) and "称谓人名" in _rules_check:
        _pn_cur = _rules_check["称谓人名"].get("pattern") if isinstance(_rules_check["称谓人名"], dict) else None
        _pn_new = _current_person_name_pattern(config)
        if _pn_cur != _pn_new:
            config.set("redaction.default_rules.称谓人名.pattern", _pn_new, persist=True)
            logger.info("[配置迁移] 已同步「称谓人名」pattern（词表变更，cp_person_name）")
except Exception as e:
    logger.error("[配置迁移] 同步称谓人名 pattern 失败: %s", type(e).__name__)

# === 核心防崩溃设置 ===
cv2.setNumThreads(0)
os.environ["OMP_NUM_THREADS"] = "1"
# v40.2.1: 抑制 MuPDF 对 PDF 文件自身缺陷的 stderr 刷屏（如扫描件常见的
# "cannot find XObject resource"）——文件固有问题无法修复，刷屏掩盖有效日志；
# 真正的渲染失败由 mixed_pdf 的空白检测+保守覆盖日志兜底
import fitz as _fitz_for_quiet  # noqa: E402
_fitz_for_quiet.TOOLS.mupdf_display_errors(False)

# === 软件配置 ===
# v37.0: 从配置读取，失败时使用硬编码后备
APP_NAME = config.get("app.name", "PrivacyGuard 脱敏卫士") if config else "PrivacyGuard 脱敏卫士"
APP_VERSION = read_app_version()
# VERSION 直接等于纯版本号，不再附加描述性后缀
# 版本号唯一来源是 version.txt，所有界面显示引用此变量
VERSION = APP_VERSION
PREVIEW_FONT_STACK = '"Segoe UI Variable", "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif'
from privacyguard.utils.helpers_pdf import *  # noqa: F401, F403 — v37.8.11 P0-3: helpers 按域拆分，5 模块 star import 等价原 helpers.*
from privacyguard.utils.helpers_word_rules import *  # noqa: F401, F403
from privacyguard.utils.helpers_word_doc import *  # noqa: F401, F403
from privacyguard.utils.helpers_word_preview import *  # noqa: F401, F403
from privacyguard.utils.helpers_ui import *  # noqa: F401, F403
from privacyguard.utils.helpers_bookmark import *  # noqa: F401, F403 — cp_bookmark: 书签脱敏/转换
from privacyguard.ui.mixins import (  # Phase 2+: Word/PageView/Settings/Crop/Extract/Bookmark mixins
    WordPreviewMixin, PageViewMixin, SettingsActionsMixin,
    CropMixin, ExtractMixin, BookmarkMixin,
)
WORD_PREVIEW_BROKEN_IMAGE_DATA_URI = (
    "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
)

# === 常量定义 ===
# v37.0: 从配置读取，失败时使用硬编码后备
MIN_RECT_WIDTH = config.get("ocr.min_rect_width", 5) if config else 5
PROGRESS_UPDATE_INTERVAL = config.get("ocr.progress_update_interval", 0.05) if config else 0.05
ZOOM_MIN = config.get("ocr.zoom_min", 0.5) if config else 0.5
ZOOM_MAX = config.get("ocr.zoom_max", 4.0) if config else 4.0
DEBUG_MODE = os.getenv('PRIVACYGUARD_DEBUG', 'False').lower() == 'true' if not config else config.get("advanced.debug_mode", False)

# === 默认规则库 ===
# v37.0: 从配置读取，支持新旧两种格式
if config:
    _rules_from_config = config.get_redaction_rules()
    DEFAULT_RULES = {}
    for name, rule in _rules_from_config.items():
        if isinstance(rule, dict):
            DEFAULT_RULES[name] = rule.get("pattern", "")
        else:
            DEFAULT_RULES[name] = str(rule)
else:
    DEFAULT_RULES = {
        # v37.7.18 cp49: 收紧身份证号正则，避免误识别横线/无关数字串
        # - 旧正则 15 位分支为 \d{15}，任何 15 位连续数字（案件号/统计号/电话拼接等）都被误匹配
        # - 新正则加省级前缀白名单（11-15/21-23/31-37/41-46/50-54/61-65）+ 月(01-12)+日(01-31) 结构校验
        # - 18 位也追加省级前缀校验（旧版仅校验年份 19/20 开头，前缀 7-9 等非法地区码也会匹配）
        "身份证号": r"(?<!\d)((?:1[1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4]|6[1-5])\d{4}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]|(?:1[1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4]|6[1-5])\d{4}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3})(?!\d)",
        "手机号码": r"(?<!\d)(1[3-9]\d{9})(?!\d)",
        "日期时间": r"\d{4}[年\-\.]\d{1,2}[月\-\.]\d{1,2}[日]?",
        # cp135: 出生信息+日期整体遮罩（正则与 config.py DEFAULT_CONFIG 保持一致）
        "出生年月": BIRTHDATE_RULE_PATTERN,
        # cp135: 住址整体遮罩（正则与 config.py DEFAULT_CONFIG 保持一致）
        "住址": ADDRESS_RULE_PATTERN,
        "电子邮箱": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "银行卡号": r"(?<!\d)([1-9]\d{12,18})(?!\d)",
        # cp70: 新增预设规则（法律文书高频，正则+校验位控误报）
        # 统一社会信用代码：18 位，字符集不含 IOZSV，mod 31-3 校验位（verify_hit_by_pattern 二次校验）
        "统一社会信用代码": r"(?<![0-9A-Za-z])[0-9A-HJ-NP-RTUWXY]{2}\d{6}[0-9A-HJ-NP-RTUWXY]{10}(?![0-9A-Za-z])",
        # 车牌号：省份简称 + 字母 + 5 位（普通）或 6 位（新能源）
        "车牌号": r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]",
        # 固定电话/座机：区号(0 开头 3-4 位) + 分隔 + 7-8 位号码，可选分机
        "固定电话": r"(?<!\d)0\d{2,3}[-\s]?\d{7,8}(?:[-\s]?\d{1,4})?(?!\d)",
        # 护照号：普通(E/G) + 8 位 或 因公(D/S/P) + 8 位
        "护照号": r"(?<![A-Za-z0-9])[EGDSP]\d{8}(?![A-Za-z0-9])",
        # 港澳台通行证：往来港澳(C+8位) / 往来台湾(部分含字母)
        "港澳台通行证": r"(?<![A-Za-z0-9])[CcWw]\d{8}(?![A-Za-z0-9])",
        # 车架号 VIN：17 位，字符集不含 IOQ，第 9 位校验位（verify_hit_by_pattern 二次校验）
        "车架号": r"(?<![A-Za-z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-Za-z0-9])",
        # IP 地址（IPv4）：四段 0-255
        "IP地址": r"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?!\d)",
        "印章": "__SEAL_DETECTION__",  # v37.5.0: 印章检测特殊标记
        "签名手印": "__SIGNATURE_DETECTION__",  # cp60: 手写签名+按手印检测特殊标记
        # cp_person_name: 称谓人名（config 缺失时的后备；pattern 与 config.py DEFAULT_CONFIG 同源生成）
        "称谓人名": build_person_name_pattern(DEFAULT_TITLES),
    }

WORD_RULE_SCHEMA_VERSION = 1



# === Phase 2: Dialog classes extracted to privacyguard/ui/dialogs/ ===
from privacyguard.ui.dialogs import (
    SettingsDialog,
    TraceCleanDialog,
    WordReplaceRulesDialog,
    ImageListDialog,
    FeedbackDialog,
    DonateDialog,
    ManualRegionRedactDialog,
    EncryptSettingsDialog,
    PasswordOpenDialog,
)

# === Phase 2: Worker classes extracted to privacyguard/workers/ ===
from privacyguard.workers.batch_replace_worker import WordBatchReplaceWorker
from privacyguard.workers.search_worker import DocSearchWorker

# === Phase 2: UI widget classes extracted to privacyguard/ui/widgets.py ===
from privacyguard.ui.widgets import (
    _ScreenColorPickerOverlay,
    SinglePageCanvas,
)
import privacyguard.ui.widgets as _ui_widgets_module

# === 配置常量 ===
# v37.0: 从配置读取，失败时使用硬编码后备
FEEDBACK_URL = config.get('app.feedback_url', 'https://fcnwakmkeuz7.feishu.cn/share/base/form/shrcnEM1JEbdIKzdB400egj9lHe') if config else 'https://fcnwakmkeuz7.feishu.cn/share/base/form/shrcnEM1JEbdIKzdB400egj9lHe'

# Sync DEBUG_MODE to extracted widgets module
_ui_widgets_module.DEBUG_MODE = DEBUG_MODE

# === OCR 线程 ===
# v37.7.6: 改为使用模块化 OCRWorker，自动注入 box_adjust_ratio
class OCRWorker(_ModularOCRWorker):
    """OCR 处理线程（兼容层：自动注入 config 中的 box_adjust_ratio）"""

    def __init__(self, pdf_path, rules, use_enhance, custom_keywords, scan_scale, off_x, off_w,
                 use_char_level_ocr: bool = False, seal_detection_enabled: bool = False,
                 custom_keyword_rules: list = None, signature_detection_enabled: bool = False,
                 rule_name_pairs: list = None, pdf_open_password: str = "", parent=None,
                 pdf_bytes=None):
        box_adjust_ratio = config.get("ocr.box_adjust_ratio", 0.0) if config else 0.0
        super().__init__(pdf_path, rules, use_enhance, custom_keywords, scan_scale, off_x, off_w,
                         use_char_level_ocr=use_char_level_ocr,
                         seal_detection_enabled=seal_detection_enabled,
                         box_adjust_ratio=box_adjust_ratio,
                         custom_keyword_rules=custom_keyword_rules,
                         signature_detection_enabled=signature_detection_enabled,
                         rule_name_pairs=rule_name_pairs,
                         pdf_open_password=pdf_open_password,
                         pdf_bytes=pdf_bytes,
                         parent=parent)

# === v40.1.4（F3 性能）：手动框选区域 OCR 后台线程 ===
class _RegionOCRWorker(QThread):
    """框选区域小图 OCR 后台识别（防主线程冻结 0.1-1.5s）。

    输入是主线程已渲染好的 BGR numpy 数组（fitz Document 非线程安全，
    渲染留在主线程；模型推理占大头，移到这里）。引擎走 RapidOCREngine
    类级单例（与扫描/搜索共用一份模型，无二次加载）。
    """

    finished_ok = pyqtSignal(str)
    failed = pyqtSignal()

    def __init__(self, img_bgr, parent=None):
        super().__init__(parent)
        self._img = img_bgr

    def run(self):
        try:
            from privacyguard.ocr.rapidocr import RapidOCREngine
            engine = RapidOCREngine()
            if not engine.is_available():
                self.failed.emit()
                return
            results = engine.recognize(self._img) or []

            def _reading_order(res):
                try:
                    xs = [p[0] for p in res.box]
                    ys = [p[1] for p in res.box]
                    return (min(ys), min(xs))
                except (TypeError, ValueError, IndexError):
                    return (0.0, 0.0)

            lines = [r.text for r in sorted(results, key=_reading_order)
                     if getattr(r, "text", "")]
            self.finished_ok.emit("\n".join(lines).strip())
        except Exception as e:
            logger.error("[cp65] 区域 OCR 后台识别失败: %s: %s", type(e).__name__, e)
            self.failed.emit()


# === 安全审计 v40.1.4（A1）：Word 预览导航白名单页 ===
class NoExternalNavWebPage(QWebEnginePage):
    """仅允许本地上下文导航的 QWebEnginePage。

    拒绝一切远程导航（http/https 等）——防止文档内嵌链接点击或重定向把
    QWebEngineView 带到远程站点（外联泄露 + pyBridge 桥跨页面暴露）。
    与 sanitize 剥离外链 href、CSP meta 构成三道防线。
    """

    _ALLOWED_SCHEMES = frozenset({"file", "about", "qrc", "data"})

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        try:
            scheme = url.scheme().lower()
        except Exception:
            return False
        if scheme in self._ALLOWED_SCHEMES:
            return True
        logger.warning("[Word预览] 已拦截远程导航（scheme=%s）", scheme)
        return False


# === WebView Bridge：Python 与 JavaScript 通信 ===
class WebViewBridge(QObject):
    """Python 与 JavaScript 通信的桥梁"""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self._scroll_position = 0  # 保存的滚动位置
        self._pending_scroll_restore = False  # 是否有待恢复的滚动位置

    @pyqtSlot(str, int, int, str)
    def add_manual_redaction(self, key, start, end, selected_text):
        """添加精确手动脱敏（仅选中区域）

        Args:
            key: word_data 中的键（如 paragraph_0）
            start: 起始位置
            end: 结束位置
            selected_text: 被选中的文本
        """
        # W4: 扫描运行时整体替换 word_data 会丢失用户在此期间添加的手动
        # 脱敏，并可能因并发写触发 RuntimeError。扫描期间直接拒绝手动操作。
        if (self.main_window.active_worker is not None
                and self.main_window.active_worker.isRunning()
                and getattr(self.main_window, 'doc_type', None) == 'docx'):
            QMessageBox.information(
                self.main_window, "扫描进行中",
                "智能扫描正在进行中，请等待扫描完成后再添加手动脱敏。"
            )
            return

        if key in self.main_window.word_data:
            # 检查重叠
            for existing in self.main_window.word_data[key]['manual']:
                if not (end <= existing['start'] or start >= existing['end']):
                    # 存在重叠，显示提示
                    QMessageBox.warning(self.main_window, "无法添加", "该区域与已有脱敏区域重叠")
                    return

            self.main_window.word_data[key]['manual'].append({
                'start': start,
                'end': end,
                'text': selected_text,
                'replacement': self.main_window.replacement_text,
                'mode': 'exact'  # 精确模式：只高亮选中区域
            })
            self.main_window.render_word_preview()
        else:
            # 添加调试日志
            logger.warning("键 '%s' 不在 word_data 中", key)
            QMessageBox.warning(self.main_window, "添加失败", f"无法定位文本区域 (键: {key})")

    @pyqtSlot(str, str)
    def add_manual_redaction_global(self, key, selected_text):
        """添加全局手动脱敏（整篇相同文本）

        Args:
            key: 当前选中的 key（用于定位上下文）
            selected_text: 选中的文本
        """
        # W4: 同 add_manual_redaction，扫描期间拒绝以避免竞态
        if (self.main_window.active_worker is not None
                and self.main_window.active_worker.isRunning()
                and getattr(self.main_window, 'doc_type', None) == 'docx'):
            QMessageBox.information(
                self.main_window, "扫描进行中",
                "智能扫描正在进行中，请等待扫描完成后再添加手动脱敏。"
            )
            return

        # 遍历所有 word_data，为每个包含该文本的位置添加脱敏
        for k, data in self.main_window.word_data.items():
            text = data['text']
            if not text:
                continue

            # 查找所有匹配位置
            pattern = re.escape(selected_text)
            for match in re.finditer(pattern, text):
                start = match.start()
                end = match.end()

                # 检查是否与已有脱敏重叠
                overlap = False
                for existing in data['manual']:
                    if not (end <= existing['start'] or start >= existing['end']):
                        overlap = True
                        break

                if not overlap:
                    data['manual'].append({
                        'start': start,
                        'end': end,
                        'text': selected_text,
                        'replacement': self.main_window.replacement_text,
                        'mode': 'global'  # 全局模式：高亮所有相同文本
                    })

        self.main_window.render_word_preview()

    @pyqtSlot(str, int, int)
    def remove_manual_redaction(self, key, start, end):
        """删除手动脱敏

        Args:
            key: word_data 中的键
            start: 起始位置
            end: 结束位置
        """
        if key in self.main_window.word_data:
            manual_list = self.main_window.word_data[key]['manual']
            # 查找要删除的项
            for i, item in enumerate(manual_list):
                if item['start'] == start and item['end'] == end:
                    # 检查是否是全局模式
                    if item.get('mode') == 'global':
                        # 全局模式：删除所有相同文本的脱敏
                        text_to_remove = item['text']
                        self.remove_global_redaction(text_to_remove)
                    else:
                        # 精确模式：只删除当前项
                        manual_list.pop(i)
                        self.main_window.render_word_preview()
                    return

    def remove_global_redaction(self, text):
        """删除所有全局模式的脱敏（批量撤销）

        Args:
            text: 要删除的文本
        """
        count = 0
        for key, data in self.main_window.word_data.items():
            manual_list = data['manual']
            # 从后往前删除，避免索引问题
            for i in range(len(manual_list) - 1, -1, -1):
                item = manual_list[i]
                if item.get('mode') == 'global' and item['text'] == text:
                    manual_list.pop(i)
                    count += 1

        if count > 0:
            # 安全审计 v40.1: 不记录脱敏原文，只记数量+首尾掩码
            _m = text[:1] + "***" + text[-1:] if isinstance(text, str) and len(text) > 2 else "***"
            logger.info("[撤销] 删除了 %s 个全局脱敏(len=%d %s)", count, len(text) if isinstance(text, str) else 0, _m)
            self.main_window.render_word_preview()

    def get_scroll_position(self):
        """获取当前保存的滚动位置"""
        return self._scroll_position

    def set_scroll_position(self, position):
        """设置要恢复的滚动位置"""
        self._scroll_position = position
        self._pending_scroll_restore = True

    def clear_pending_scroll_restore(self):
        """清除待恢复标志"""
        self._pending_scroll_restore = False

    def has_pending_scroll_restore(self):
        """检查是否有待恢复的滚动位置"""
        return self._pending_scroll_restore

    @pyqtSlot(str, float)
    def report_word_preview_scroll(self, panel_id, ratio):
        """接收 Word 双栏预览滚动比例并同步到另一侧。"""
        try:
            panel = str(panel_id or "").strip().lower()
            ratio_value = float(ratio)
        except (TypeError, ValueError):
            return
        self.main_window._sync_word_compare_scroll(panel, ratio_value)

# === Word 文档处理线程 ===
# v37.7.6: 改为使用模块化 WordWorker，补充 default_rules 参数
class WordWorker(_ModularWordWorker):
    """Word 文档智能脱敏线程（兼容层：自动注入 DEFAULT_RULES）"""

    def __init__(self, word_doc, word_data, rules, custom_keywords, replacement_text, parent=None):
        super().__init__(word_doc, word_data, rules, custom_keywords,
                         replacement_text, default_rules=DEFAULT_RULES, parent=parent)

# === Word 预览交互式 JavaScript 代码常量 ===
# v36.4: 提取为常量; v37.8.11 Phase 3: 外部化为 assets/js/ 文件
def _load_js_asset(filename):
    """从 assets/js/ 加载 JavaScript 资源文件。"""
    _path = resource_path(os.path.join('assets', 'js', filename))
    with open(_path, 'r', encoding='utf-8') as _f:
        return _f.read()

_INTERACTIVE_JS_CODE = _load_js_asset('word_preview_interactive.js')


# === 主窗口 ===
class MainWindow(PageViewMixin, WordPreviewMixin, SettingsActionsMixin, CropMixin, ExtractMixin, BookmarkMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION} - Powered by li (汪立律师)")

        # v37.0: 从配置读取窗口尺寸，失败时使用硬编码后备
        # v37.2.0: 读取 OCR 引擎配置
        if config:
            min_width = config.get("app.window.min_width", 900)
            min_height = config.get("app.window.min_height", 600)
            default_width = config.get("app.window.default_width", 1300)
            default_height = config.get("app.window.default_height", 900)
            self.replacement_text = config.get("redaction.replacement_text", "[已脱敏]")
            # v37.7.18 cp50: 兜底默认值与 DEFAULT_CONFIG 对齐（默认 1.0）
            self.scan_level = config.get("redaction.scan.default_level", 1.0)
            self.offset_x = config.get("redaction.offset.default_x", 0)
            self.offset_w = config.get("redaction.offset.default_w", 0)
            self.custom_keywords = config.get("redaction.custom_keywords", "")
            # v37.7.13 cp43: 加载关键词规则列表 + 手动替换开关
            self.custom_keyword_rules = config.get("redaction.custom_keyword_rules", [])
            self.manual_replace_prompt = config.get("redaction.manual_replace_prompt", False)
            # cp_bookmark: 书签栏脱敏开关
            self.bookmark_redact_enabled = config.get("redaction.bookmark_redact_enabled", False)
            # v37.4.0: 移除 OCR 引擎配置，只使用 RapidOCR
        else:
            min_width, min_height = 1120, 600
            default_width, default_height = 1300, 900
            self.replacement_text = "[已脱敏]"
            # v37.7.18 cp50: 无 config 兜底与 DEFAULT_CONFIG 一致（默认 1.0）
            self.scan_level = 1.0
            self.offset_x = 0
            self.offset_w = 0
            self.custom_keywords = ""
            self.custom_keyword_rules = []
            self.manual_replace_prompt = False
            self.bookmark_redact_enabled = False

        # 窗口尺寸设置：最小尺寸 + 默认尺寸
        # cp73: 记录基础最小宽度作为地板，运行时按工具栏内容动态抬高
        self._base_min_window_width = min_width
        self.setMinimumSize(min_width, min_height)
        self.resize(default_width, default_height)

        # cp61: 固定默认尺寸（屏幕收敛+居中），不再持久化/恢复窗口几何
        self._restore_window_state()

        self.doc = None
        # cp_bookmark: 书签编辑缓存（None=未编辑用原文档TOC；True=有未导出编辑）
        self.toc_edited = None
        # v40.1.4（用户反馈）：书签脱敏预览的动作状态——仅在智能脱敏/全文遮罩
        # 执行后为 True；设置变更不影响，重置文档/换文档清回 False（显示原始标题）
        self._bookmark_redact_applied = False
        self._toc_loaded = False
        self._toc_original = []  # 从 PDF 读取的原始 TOC（脱敏预览的基线）
        self._targeted_toc_rules = None  # 手动框选"全文遮罩"触发的临时书签规则
        self.word_doc = None  # Word 文档对象
        self.file_path = ""
        self.current_page = 0
        self.zoom_level = 1.0
        self.page_data = {}
        self._ocr_processed_pages = set()  # OCR 实际处理过的页（用于准确完成状态提示）
        self.word_data = {}  # Word 文档数据结构
        self.word_replace_rules = []  # 会话级多字段替换规则
        self.word_compare_mode = False  # Word 预览是否开启原文/替换后对比
        self.word_compare_user_hidden = False  # 用户主动隐藏右侧对比预览
        self._word_data_lock = QMutex()  # v36.5: 保护 word_data 线程安全
        self.doc_type = None  # 'pdf', 'docx', 'doc'
        self.current_ui_mode = "idle"  # idle / pdf / word / batch / image_merge
        self.batch_stage = "idle"  # idle / rule_setup / running / finished / stopped
        self.batch_selected_files = []
        self.batch_total_files = 0
        self.batch_processed_files = 0
        self.batch_success_count = 0
        self.batch_failed_count = 0
        self.batch_current_file = ""
        self.batch_last_summary = None
        self.batch_result_filter_mode = "all"
        self.image_merge_in_progress = False
        self.image_merge_total_images = 0
        self.info_bar_message = ""
        self.toolbar_density_mode = "wide"
        self._bound_window_handle = None
        self._button_density_metrics = {}
        self.active_rules = [DEFAULT_RULES.get("身份证号", ""), DEFAULT_RULES.get("手机号码", "")]
        self.use_enhance = False
        self.current_color = QColor(0, 0, 0)
        self.dual_view = False
        # cp72: 文档加密密码（仅会话级，不持久化），导出时生效
        self.pdf_open_password = ""
        self.pdf_edit_password = ""
        # cp114: 磁盘重读认证密码——与导出加密设置解耦。
        # 用户在 PasswordOpenDialog 选择"解除"时 pdf_open_password 清空（导出不加密），
        # 但原文件仍加密，OCR/save_pdf 从磁盘重读仍需此密码认证。
        self._pdf_auth_password = ""
        # cp113: Word 打开密码（仅解密用，python-docx 不支持重新加密保存）
        self.word_open_password = ""
        # cp81: 全文搜索状态（扫描页 OCR 文本会话级缓存 + worker 句柄）
        self._search_ocr_cache = {}
        self._search_worker = None
        self._search_hit_count = 0
        self._search_stop_notice = False
        # cp82: 搜索命中闪烁高亮清除定时器（2.4s 后自动消失，重复点击重启）
        self._search_flash_timer = QTimer(self)
        self._search_flash_timer.setSingleShot(True)
        self._search_flash_timer.setInterval(2400)
        self._search_flash_timer.timeout.connect(self._clear_search_flash)
        # cp83: 撤销/恢复状态快照栈（全文档统一，深 20）
        self._undo_stack = []
        self._redo_stack = []
        self._UNDO_MAX = 20
        # v40.1.4（F2 内存）：结构快照字节流的内存预算（192MB）。超预算时最旧的
        # 字节流落盘（mkstemp 0600），撤销时读回——大 PDF 撤销栈不再 GB 级驻留。
        self._UNDO_BYTES_BUDGET = 192 * 1024 * 1024
        self._undo_spill_files = set()  # 落盘文件注册表（清扫用）
        self._restoring_snapshot = False  # 重入守卫：恢复快照时不再捕捉
        # cp88: 会话草稿（防崩溃/误关丢进度）：5s 节流自动保存
        self._session_store = SessionStore()
        self._draft_timer = QTimer(self)
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(5000)
        self._draft_timer.timeout.connect(self._flush_session_draft)
        self._draft_pdf_bytes_pending = False  # 结构变更待写字节流标记
        # cp67: 页面视图（多页网格总览）状态
        self.page_view_mode = False
        self.grid_columns = 3
        self.grid_selected_pages = set()
        self._grid_canvases = {}
        self._grid_cards = {}
        self._grid_pix_cache = {}          # page_idx -> (zoom, QPixmap)，LRU 上限见 _GRID_CACHE_MAX
        self._grid_cache_order = []        # LRU 顺序
        self._grid_refresh_timer = QTimer(self)
        self._grid_refresh_timer.setSingleShot(True)
        self._grid_refresh_timer.setInterval(60)
        self._grid_refresh_timer.timeout.connect(lambda: self._refresh_visible_grid_thumbs())
        # cp68: 列数缩放的高清重渲染去抖（过渡帧用缓存 pixmap 快速缩放，停止滚动后再高清）
        self._grid_hq_timer = QTimer(self)
        self._grid_hq_timer.setSingleShot(True)
        self._grid_hq_timer.setInterval(260)
        self._grid_hq_timer.timeout.connect(lambda: self._refresh_visible_grid_thumbs())
        # cp68: 页面纵横比缓存（避免每次重排全量 fitz 访问）
        self._grid_page_aspects = {}
        # cp76: 网格缩略图分帧渲染队列——首次进入页面视图时可见页全部同步
        # fitz 高清渲染会阻塞主线程 ~1s（白屏卡顿）；改为每帧渲染一页，
        # 网格骨架立现、页面内容逐个浮现，UI 全程可响应
        self._grid_render_queue = []
        self._grid_render_timer = QTimer(self)
        self._grid_render_timer.setSingleShot(True)
        self._grid_render_timer.setInterval(0)
        self._grid_render_timer.timeout.connect(self._process_grid_render_queue)
        # cp68: Ctrl+滚轮手势时间戳（跨视图共用）：间隔超过阈值视为新手势，
        # 缩放到边界后需“松手再滚”才允许跨越单页/页面视图分界
        self._ctrl_zoom_last_ts = 0.0
        # cp68: Shift 范围选择锚点（最近一次非 Shift 点击的页码）
        self._grid_anchor_page = None

        # 预先创建 word_preview
        self.word_preview = None
        self.word_preview_replaced = None
        # 预览高亮按来源筛选状态（默认全部显示）
        self._preview_highlight_sources = list(HIGHLIGHT_FILTER_SOURCES)
        self.bridge = None
        self.word_web_channel = None
        self._word_scroll_sync_timer = QTimer(self)
        self._word_scroll_sync_timer.setInterval(160)
        self._word_scroll_sync_timer.timeout.connect(self._poll_word_compare_scroll_sync)
        self._word_scroll_sync_polling = False
        self._word_scroll_sync_last_ratios = {"original": None, "replaced": None}
        self._word_scroll_sync_pending_target = None
        self._word_scroll_sync_pending_ratio = None
        self._word_scroll_sync_generation = 0
        self._word_preview_assets_dir = None
        self._word_preview_assets_base_url = QUrl()
        self._reset_word_preview_cache()

        # 线程管理和临时文件管理（v24 稳定性优化）
        self.active_worker = None
        self.batch_worker = None
        self.active_task_type = None  # 'scan', 'batch_replace'
        self.worker_lock = QMutex()
        self.temp_manager = TempFileManager()

        # 注册退出清理
        atexit.register(self._app_exit_cleanup)

        self.setup_ui()

        # v37.6.0: 启用拖拽支持
        self.setAcceptDrops(True)
        self._drag_active = False  # 拖拽状态标记
        self._drag_valid = False   # 拖拽文件是否有效

    def _detect_system_theme(self):
        """检测系统主题（v35.1 新增）

        Returns:
            str: 'light' 或 'dark'
        """
        import platform

        system = platform.system()

        try:
            if system == 'Darwin':  # macOS
                import subprocess
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and 'Dark' in result.stdout:
                    return 'dark'
                return 'light'

            elif system == 'Windows':
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return 'light' if value == 1 else 'dark'

            else:  # Linux
                import os
                gtk_theme = os.environ.get('GTK_THEME', '').lower()
                if 'dark' in gtk_theme:
                    return 'dark'
                return 'light'

        except (OSError, IOError, KeyError, ValueError, ImportError) as e:
            # 检测失败（注册表读取错误、环境变量异常等），默认浅色
            logger.warning("[MainWindow] 主题检测失败: %s", e)
            return 'light'

    def _restore_window_state(self):
        """cp61: 每次启动固定使用默认窗口尺寸（不再恢复上次几何）。

        默认尺寸来自 config（1300x900），按屏幕可用区域 92% 收敛（小屏笔记本不溢出）
        并居中显示；启动后用户仍可自由拉伸窗口。
        """
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        w = min(self.width(), int(avail.width() * 0.92))
        h = min(self.height(), int(avail.height() * 0.92))
        self.resize(w, h)
        self.move(avail.x() + (avail.width() - w) // 2,
                  avail.y() + (avail.height() - h) // 2)

    def closeEvent(self, event):
        """保存窗口状态并清理临时文件"""
        if defer_close_for_workers(self, event):
            return
        # cp88: 退出前 flush 会话草稿（未到节流时间的变更不丢）
        if getattr(self, "_draft_timer", None) is not None and self._draft_timer.isActive():
            self._draft_timer.stop()
            self._flush_session_draft()
        self._app_exit_cleanup()
        super().closeEvent(event)

    def showEvent(self, event):
        """首次显示和重新显示窗口时，补绑屏幕缩放监听。"""
        super().showEvent(event)
        self._bind_window_handle_signals()
        # cp78: Windows 原生标题栏配色与主页背景统一（需窗口句柄就绪后设置）
        self._apply_windows_titlebar_color()
        QTimer.singleShot(0, self._refresh_toolbar_responsiveness)

    def _apply_windows_titlebar_color(self):
        """cp78: 把 Windows 11 原生标题栏颜色设为主页背景色（scroll_area #F6F8FB）。

        系统默认浅蓝标题栏（#EFF4F9）与应用背景色差突兀。用 DWM API
        DWMWA_CAPTION_COLOR(35) 统一；仅 Windows 11 build 22000+ 支持，
        Win10/调用失败时静默保持系统默认。COLORREF 格式为 0x00BBGGRR。
        """
        if sys.platform != "win32" or getattr(self, "_titlebar_colored", False):
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            hex_color = Theme.LIGHT["scroll_area"].lstrip("#")
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            colorref = ctypes.c_int((b << 16) | (g << 8) | r)
            DWMWA_CAPTION_COLOR = 35
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR,
                ctypes.byref(colorref), ctypes.sizeof(colorref))
            if res == 0:
                self._titlebar_colored = True
        except Exception:
            # 非 Win11 / dwmapi 不可用：保持系统默认标题栏
            pass

    def resizeEvent(self, event):
        """窗口大小改变时自动重新适应页面"""
        super().resizeEvent(event)

        if hasattr(self, "toolbar"):
            self._refresh_toolbar_responsiveness()

        # 只在 PDF 模式且文档已加载时处理
        if not self.doc or self.current_page is None:
            return

        # cp67: 页面视图模式下窗口变化 → 重排网格（节流），不做单页 fit
        if getattr(self, "page_view_mode", False):
            QTimer.singleShot(80, self._relayout_page_grid)
            return

        # 自动重新适应（保持页面完整显示）
        self.fit_page()

    def _bind_window_handle_signals(self):
        """绑定窗口句柄相关信号，便于跨屏和 DPI 切换时收口工具栏。"""
        try:
            handle = self.windowHandle()
        except Exception:
            handle = None

        if handle is None or handle is self._bound_window_handle:
            return

        try:
            handle.screenChanged.connect(self._on_window_screen_changed)
        except Exception:
            pass
        self._bound_window_handle = handle

    def _on_window_screen_changed(self, _screen):
        """窗口切换到不同屏幕时，重新计算工具栏密度。"""
        QTimer.singleShot(0, self._refresh_toolbar_responsiveness)

    def _reset_word_preview_cache(self):
        """重置 Word 预览缓存与待应用的局部更新状态。"""
        if hasattr(self, "_word_scroll_sync_timer"):
            self._invalidate_word_scroll_sync()
        self._cleanup_word_preview_assets_dir()
        self._word_base_html = None
        self._word_html_source_path = None
        self._word_tagged_html = None
        self._word_preview_document_html = None
        self._word_replaced_document_html = None
        self._word_replaced_html = None
        self._pending_word_preview_blocks = None
        self._pending_word_replaced_blocks = None
        self._word_preview_ready = False
        self._word_replaced_ready = False
        self._word_preview_loaded_source_path = None
        self._word_replaced_loaded_source_path = None
        self._word_preview_target_source_path = None
        self._word_replaced_target_source_path = None
        self._word_preview_assets_base_url = QUrl()

    def _cleanup_word_preview_assets_dir(self):
        """清理当前 Word 预览图片临时目录。"""
        asset_dir = getattr(self, "_word_preview_assets_dir", None)
        if not asset_dir:
            return

        try:
            if os.path.isdir(asset_dir):
                shutil.rmtree(asset_dir, ignore_errors=True)
        except Exception as e:
            logger.warning("[清理] 删除 Word 预览图片目录失败: %s", e)

        temp_manager = getattr(self, "temp_manager", None)
        instance_lock = getattr(temp_manager, "_instance_lock", None)
        temp_dirs = getattr(temp_manager, "temp_dirs", None)
        if temp_manager is not None and instance_lock is not None and isinstance(temp_dirs, list):
            try:
                with instance_lock:
                    if asset_dir in temp_dirs:
                        temp_dirs.remove(asset_dir)
            except Exception:
                pass

        self._word_preview_assets_dir = None

    def _create_word_preview_asset_dir(self):
        """创建当前 Word 预览使用的图片资源目录。"""
        self._cleanup_word_preview_assets_dir()
        if hasattr(self, "temp_manager") and self.temp_manager is not None:
            asset_dir = self.temp_manager.create_temp_dir()
        else:
            asset_dir = tempfile.mkdtemp(prefix="pg_word_preview_")
        self._word_preview_assets_dir = asset_dir
        self._word_preview_assets_base_url = QUrl.fromLocalFile(os.path.join(asset_dir, ""))
        return asset_dir

    def _build_word_html_from_docx(self, docx_path):
        """将 DOCX 转成 HTML，并把嵌入图片提取到临时目录。"""
        import mammoth

        asset_dir = self._create_word_preview_asset_dir()
        image_counter = {"value": 0}

        def convert_image_to_file(image):
            image_counter["value"] += 1
            suffix = resolve_word_preview_image_suffix(getattr(image, "content_type", ""))
            image_name = f"word_image_{image_counter['value']:04d}{suffix}"
            target_path = os.path.join(asset_dir, image_name)
            try:
                with image.open() as image_source, open(target_path, "wb") as output_file:
                    shutil.copyfileobj(image_source, output_file)
                return {
                    "src": image_name,
                    "loading": "lazy",
                    "decoding": "async",
                }
            except Exception as e:
                logger.warning("[Word预览] 提取嵌入图片失败: %s", e)
                return {
                    "src": WORD_PREVIEW_BROKEN_IMAGE_DATA_URI,
                    "loading": "lazy",
                    "decoding": "async",
                    "data-pg-image-error": "1",
                }

        with open(docx_path, "rb") as docx_file:
            result = mammoth.convert_to_html(
                docx_file,
                convert_image=mammoth.images.img_element(convert_image_to_file),
            )

        if getattr(result, "messages", None):
            for message in result.messages:
                logger.info("[Word预览] Mammoth: %s", message)
        # P1-3: 对 mammoth 输出做白名单消毒，防止恶意文档经 mammoth 反射未转义内容
        # 注入脚本（file:// 上下文 + pyBridge 可移除遮罩 = 漏脱风险）。
        # 消毒发生在 mammoth 输出阶段；可信交互 JS 在下游 _inject_interactive_html 注入，不受影响。
        from privacyguard.utils.html_sanitize import sanitize_preview_html
        return sanitize_preview_html(result.value)

    # ============== v37.6.0: 拖拽打开文件功能 ==============

    def dragEnterEvent(self, event):
        """拖拽进入事件 - 验证文件类型并提供视觉反馈"""
        self._drag_active = True
        self._drag_valid = False

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()

            # 验证所有文件
            valid_exts = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
            all_valid = True
            file_count = 0

            for url in urls:
                if url.isLocalFile():
                    file_count += 1
                    path = url.toLocalFile().lower()
                    if not any(path.endswith(ext) for ext in valid_exts):
                        all_valid = False
                        break

            # 必须有文件且都有效
            if file_count > 0 and all_valid:
                self._drag_valid = True
                event.acceptProposedAction()
                self._update_drag_visual_feedback(True)
            else:
                # 有文件但格式不支持
                if file_count > 0:
                    event.ignore()
                    self._update_drag_visual_feedback(False)
                else:
                    event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖拽移动事件 - 持续反馈"""
        if self._drag_active and event.mimeData().hasUrls():
            # 检查鼠标位置是否在预览区域
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            if self._is_in_preview_area(pos):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """拖拽离开事件 - 清除视觉反馈"""
        self._drag_active = False
        self._drag_valid = False
        self._update_drag_visual_feedback(None)

    def dropEvent(self, event):
        """拖放事件 - 处理文件"""
        self._drag_active = False
        self._update_drag_visual_feedback(None)

        if not event.mimeData().hasUrls():
            event.ignore()
            return

        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]

        if not file_paths:
            QMessageBox.warning(self, "无效文件", "只支持本地文件拖拽")
            event.ignore()
            return

        # 调用处理逻辑
        self._handle_dropped_files(file_paths)
        event.acceptProposedAction()

    def _is_in_preview_area(self, pos):
        """检查坐标是否在预览区域内"""
        # pos 是 MainWindow 坐标，转换到 scroll 局部坐标后做命中测试
        map_pos = self.scroll.mapFrom(self, pos)
        return self.scroll.rect().contains(map_pos)

    def _update_drag_visual_feedback(self, valid):
        """更新拖拽视觉反馈

        Args:
            valid: True(有效), False(无效), None(清除)
        """
        if valid is True:
            # 有效文件 - 绿色边框提示
            self.scroll.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {Theme.LIGHT["scroll_area"]};
                    border-radius: {Theme.BORDER_RADIUS}px;
                    border: 3px solid #34C759;
                }}
            """)
        elif valid is False:
            # 无效文件 - 红色边框提示
            self.scroll.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {Theme.LIGHT["scroll_area"]};
                    border-radius: {Theme.BORDER_RADIUS}px;
                    border: 3px solid #FF3B30;
                }}
            """)
        else:
            # 清除 - 恢复默认
            self.scroll.setStyleSheet(self.scroll_style.format(Theme.LIGHT["scroll_area"]))

    def _handle_dropped_files(self, file_paths):
        """处理拖拽的文件

        Args:
            file_paths: 文件路径列表
        """
        # 清理之前的状态
        self._cleanup_before_open()
        self._cleanup_temp_file()

        if len(file_paths) == 1:
            # 单个文件
            fname = file_paths[0]
            doc_type = self.detect_file_type(fname)

            try:
                if doc_type == 'pdf':
                    self._open_pdf_file(fname)
                elif doc_type == 'docx':
                    self._open_word_docx(fname)
                elif doc_type == 'doc':
                    self._open_word_doc(fname)
                elif doc_type == 'image':
                    self._open_images_merge([fname])
                else:
                    QMessageBox.warning(
                        self, "不支持的格式",
                        f"文件: {os.path.basename(fname)}\n\n"
                        f"请选择 PDF、Word 文档或图片文件"
                    )
            except (IOError, OSError, ValueError, ConversionError) as e:
                QMessageBox.critical(self, "错误", f"打开文件失败: {str(e)}")
        else:
            # 多个文件：支持图片合并或 Word 批量替换
            are_all_images = all(self.detect_file_type(f) == 'image' for f in file_paths)
            are_all_words = all(self.detect_file_type(f) in ('docx', 'doc') for f in file_paths)
            if are_all_images:
                try:
                    self._open_images_merge(file_paths)
                except (IOError, OSError, ValueError, ConversionError) as e:
                    QMessageBox.critical(self, "错误", f"合并图片失败: {str(e)}")
            elif are_all_words:
                self.start_batch_replace(file_paths=file_paths)
            else:
                QMessageBox.warning(
                    self, "不支持的混合拖拽",
                    "同时拖拽多个文件时，仅支持两种场景：\n"
                    "1. 全部是图片（自动合并为PDF）\n"
                    "2. 全部是Word（自动启动批量替换）"
                )

    def _show_drag_tooltip(self, file_paths, valid):
        """显示拖拽文件提示信息（可选增强）

        Args:
            file_paths: 文件路径列表
            valid: 是否有效
        """
        if not file_paths:
            return

        if len(file_paths) == 1:
            fname = os.path.basename(file_paths[0])
            doc_type = self.detect_file_type(file_paths[0])
            type_names = {
                'pdf': 'PDF 文档',
                'docx': 'Word 文档',
                'doc': 'Word 文档(旧版)',
                'image': '图片文件',
                'unknown': '未知格式'
            }
            tooltip = f"{fname}\n类型: {type_names.get(doc_type, '未知')}"
        else:
            tooltip = f"共 {len(file_paths)} 个文件"
            if valid:
                tooltip += "\n将合并为 PDF"
            else:
                tooltip += "\n格式不支持"

        # 使用 QToolTip 显示
        from PyQt6.QtWidgets import QToolTip
        QToolTip.showText(QCursor.pos(), tooltip)

    # ============== 拖拽功能结束 ==============

    def _cleanup_before_open(self):
        """v37.0.6: 打开新文档前的完整资源清理

        解决问题：
        - 打开新文档时卡顿/未响应
        - 文件选择窗口内容不显示
        """
        self._invalidate_word_scroll_sync()
        self._stop_worker_safely(getattr(self, '_region_ocr_worker', None), label="框选识别线程")
        # cp67: 退出页面视图（新文档/新模式不继承旧网格）
        if getattr(self, "page_view_mode", False):
            self.set_page_view_mode(False)
        # cp72: 重置加密密码，避免跨文档串密码
        self.pdf_open_password = ""
        self.pdf_edit_password = ""
        # cp114: 重置磁盘重读认证密码
        self._pdf_auth_password = ""
        # cp113: 重置 Word 打开密码
        self.word_open_password = ""
        if hasattr(self, "btn_encrypt"):
            self._refresh_encrypt_button_state()
        # cp81: 搜索状态重置：停 worker、清 OCR 缓存、收面板清结果
        if self._search_worker is not None and self._search_worker.isRunning():
            self._search_worker.requestInterruption()
            self._search_worker.wait(2000)
        self._search_worker = None
        # P1-6: 停止进行中的图片合并线程，并递增 generation；
        # 陈旧合并完成时 _on_merge_finished 检测 generation 不匹配，不再自动覆盖新文档。
        self._merge_generation = getattr(self, "_merge_generation", 0) + 1
        _merge_w = getattr(self, "merge_worker", None)
        if _merge_w is not None and _merge_w.isRunning():
            _merge_w.requestInterruption()
            _merge_w.wait(2000)
        self.merge_worker = None
        self._search_ocr_cache.clear()
        if hasattr(self, "search_panel"):
            self.search_panel.hide()
            self.search_results_list.clear()
            self.lbl_search_status.setText("")
            self.btn_search_cancel.hide()
        # cp_bookmark: 重置书签面板与编辑缓存
        if hasattr(self, "bookmark_panel"):
            self._reset_bookmark_state()
        # cp83: 清空撤销/恢复双栈并禁用按钮
        # cp88: 换文档前先 flush 旧文档未落盘的草稿变更
        if getattr(self, "_draft_timer", None) is not None and self._draft_timer.isActive():
            self._draft_timer.stop()
            self._flush_session_draft()
        self._undo_stack = []
        self._redo_stack = []
        self._refresh_undo_redo_buttons()
        self._sweep_undo_spill_files()  # v40.1.4（F2）：清栈后删除全部落盘快照
        # 1. 停止并等待活跃的 worker 线程
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.requestInterruption()
            # 等待线程结束（最多 2 秒）
            if not self.active_worker.wait(2000):
                # O4: 超时仍存活的线程直接丢弃会与新文档并发：
                # 其 page_result_signal/finished_signal 会落进新文档的
                # page_data/word_data 造成跨文档脱敏框污染。先断开全部信号，
                # 保留引用延迟销毁，待其自然结束后 deleteLater。
                logger.warning("[WARN] 旧扫描线程超时未结束，断开信号延迟销毁")
                stale_worker = self.active_worker
                try:
                    stale_worker.disconnect()
                except TypeError:
                    pass
                stale_worker.finished.connect(stale_worker.deleteLater)
            self.active_worker = None

        # 2. 清理 QWebEngineView（Word 预览）
        # QWebEngineView 占用大量资源，需要正确清理
        if hasattr(self, 'word_preview') and self.word_preview:
            try:
                # 停止加载
                self.word_preview.stop()
                # 清空内容
                self.word_preview.setHtml('')
                # 隐藏
                self.word_preview.hide()
            except Exception as e:
                logger.warning("[清理] 清理 word_preview 时出错: %s", e)
        if hasattr(self, 'word_preview_replaced') and self.word_preview_replaced:
            try:
                self.word_preview_replaced.stop()
                self.word_preview_replaced.setHtml('')
                self.word_preview_replaced.hide()
            except Exception as e:
                logger.warning("[清理] 清理 word_preview_replaced 时出错: %s", e)

        # 3. 关闭 PDF 文档
        if self.doc:
            # cp133: 关闭 doc 前先退出提取/截去模式（否则 _extract_result_doc 引用已关 doc → 崩溃）
            if getattr(self, "_extract_active", False):
                if hasattr(self, "btn_extract"):
                    self.btn_extract.blockSignals(True)
                    self.btn_extract.setChecked(False)
                    self.btn_extract.blockSignals(False)
                self.exit_extract_mode()
            if getattr(self, "_crop_active", False):
                if hasattr(self, "btn_crop"):
                    self.btn_crop.blockSignals(True)
                    self.btn_crop.setChecked(False)
                    self.btn_crop.blockSignals(False)
                self.exit_crop_mode()
            try:
                self.doc.close()
            except Exception as e:
                logger.warning("[清理] 关闭 PDF 文档时出错: %s", e)
            self.doc = None

        # 4. 重置状态变量
        self.word_doc = None
        self.word_data = {}
        self._reset_word_preview_cache()
        self.page_data = {}
        self._ocr_processed_pages = set()
        self.current_page = None
        self.doc_type = None
        self.file_path = None
        self.word_compare_mode = False
        self.word_compare_user_hidden = False
        self.image_merge_in_progress = False
        self.image_merge_total_images = 0
        self._reset_batch_session_state()
        # v37.7.11 cp40: 重置 PDF 修改标记 + 隐藏去水印按钮
        # （打开新文档时一律隐藏，仅 _open_pdf_file 成功后重新显示）
        self._pdf_modified = False
        if hasattr(self, "btn_remove_watermark"):
            self.btn_remove_watermark.hide()
        self._clear_info_bar_message()

        # 5. v37.0.8: 重置 canvas 显示状态（不删除固定实例）
        # canvas_left 和 canvas_right 是固定实例，在 setup_ui() 中创建
        # 只需清除显示内容，不需要删除
        # v37.0.9: 修复属性名错误 - 使用正确的 rects_manual 和 rects_ocr
        if hasattr(self, 'canvas_left') and self.canvas_left:
            try:
                # 检查 C++ 对象是否仍然有效
                _ = self.canvas_left.size()  # 如果对象已删除，这里会抛出异常
                self.canvas_left.clear()  # 清除显示
                self.canvas_left.page_index = 0  # 重置页面索引
                self.canvas_left.rects_manual = []  # 清除手动脱敏区域（正确的属性名）
                self.canvas_left.rects_ocr = []  # 清除 OCR 区域（正确的属性名）
            except RuntimeError:
                logger.debug("[清理] canvas_left 的 C++ 对象已被删除，跳过清理")

        if hasattr(self, 'canvas_right') and self.canvas_right:
            try:
                _ = self.canvas_right.size()
                self.canvas_right.clear()
                self.canvas_right.page_index = 1
                self.canvas_right.rects_manual = []
                self.canvas_right.rects_ocr = []
            except RuntimeError:
                logger.debug("[清理] canvas_right 的 C++ 对象已被删除，跳过清理")

        if hasattr(self, 'word_compare_container') and self.word_compare_container:
            self.word_compare_container.hide()
        if hasattr(self, 'canvas_container') and self.canvas_container:
            self.canvas_container.show()

        # 6. 处理待处理的 Qt 事件，确保 UI 响应
        QApplication.processEvents()
        self._sync_ui_mode()

        logger.debug("[清理] 打开新文档前的资源清理完成")

    def _has_active_open_context(self):
        """判断当前是否已有活跃文档/任务，需要在打开新文件前先做清理。"""
        return bool(
            self.doc
            or self.word_doc
            or self.file_path
            or self.doc_type
            or self.page_data
            or self.word_data
            or self.image_merge_in_progress
            or (self.batch_stage != "idle" and self.batch_selected_files)
            or self.current_ui_mode != "idle"
        )

    def _is_canvas_valid(self, canvas):
        """v37.0.9: 检查 canvas 的 C++ 对象是否仍然有效"""
        if canvas is None:
            return False
        try:
            # 尝试访问一个简单的属性来验证对象是否有效
            _ = canvas.size()
            return True
        except RuntimeError:
            # C++ 对象已被删除
            return False

    def _safe_canvas_update(self, canvas, pixmap, scale, ocr_rects, manual_rects):
        """v37.0.9: 安全地更新 canvas 内容"""
        if not self._is_canvas_valid(canvas):
            logger.warning("[警告] canvas 无效，跳过更新")
            return False
        try:
            canvas.update_content(pixmap, scale, ocr_rects, manual_rects)
            return True
        except RuntimeError as e:
            logger.error("[错误] 更新 canvas 时出错: %s", e)
            return False

    def _safe_canvas_set_mask_color(self, canvas, color):
        """v37.0.9: 安全地设置 canvas 遮罩颜色"""
        if not self._is_canvas_valid(canvas):
            return False
        try:
            canvas.set_mask_color(color)
            return True
        except RuntimeError as e:
            logger.error("[错误] 设置 canvas 颜色时出错: %s", e)
            return False

    def _is_word_web_view_valid(self, web_view):
        """判断 Word 预览 WebView 是否仍然可用。"""
        if web_view is None:
            return False
        # 安全修复: sip.isdeleted 调用全部纳入 try，防止 C++ 对象损坏时 RuntimeError
        try:
            if sip.isdeleted(web_view):
                return False
            page = web_view.page()
            if page is None or sip.isdeleted(page):
                return False
            _ = web_view.isHidden()
            return True
        except RuntimeError:
            return False

    def _invalidate_word_scroll_sync(self):
        """停用并失效当前 Word 双栏滚动同步链，避免异步回调撞上已销毁对象。"""
        if hasattr(self, "_word_scroll_sync_timer"):
            self._word_scroll_sync_timer.stop()
        self._word_scroll_sync_polling = False
        self._word_scroll_sync_pending_target = None
        self._word_scroll_sync_pending_ratio = None
        self._word_scroll_sync_last_ratios = {"original": None, "replaced": None}
        self._word_scroll_sync_generation += 1

    def _stop_worker_safely(self, worker, timeout_ms=2000, label="worker"):
        """统一安全停止后台 worker：请求中断 → 等待 → 超时则断开信号延迟销毁。

        用于 _cleanup_before_open / _app_exit_cleanup，避免线程在 UI 销毁后
        仍发射信号落到已删除的 Qt 对象上（QThread: Destroyed while still running
        导致退出崩溃）。
        """
        if worker is None or sip.isdeleted(worker) or not worker.isRunning():
            return
        worker.requestInterruption()
        if worker.wait(timeout_ms):
            return
        # 超时未结束：断开全部信号，保留引用延迟销毁，待其自然结束 deleteLater
        logger.warning("[WARN] %s 超时未结束，断开信号延迟销毁", label)
        try:
            worker.disconnect()
        except TypeError:
            pass
        try:
            worker.finished.connect(worker.deleteLater)
        except (TypeError, RuntimeError):
            pass

    def _app_exit_cleanup(self):
        """应用退出时的清理（v24 稳定性优化；P1-5: 覆盖 search/merge worker；P2: 幂等+关闭 doc）"""
        # P2 幂等：closeEvent 与 atexit 都会调用本方法，第二次起直接返回
        if getattr(self, "_exit_cleaned", False):
            return
        self._exit_cleaned = True
        self._invalidate_word_scroll_sync()
        # P1-5: 停止所有可能仍在运行的后台线程（不仅 active_worker）。
        # search/merge worker 不在 active_worker 里，退出时若仍在运行会触发
        # "QThread: Destroyed while thread is still running" 退出崩溃。
        self._stop_worker_safely(self.active_worker, label="扫描线程")
        self._stop_worker_safely(getattr(self, "_search_worker", None), label="搜索线程")
        self._stop_worker_safely(getattr(self, "merge_worker", None), label="合并线程")
        self._stop_worker_safely(getattr(self, "_region_ocr_worker", None), label="框选识别线程")
        self.active_worker = None
        self._search_worker = None
        # P2: 显式关闭 fitz.Document，避免依赖 GC __del__（teardown 时序敏感，
        # 尤其当 worker 线程也曾引用 fitz 时）
        _doc = getattr(self, "doc", None)
        if _doc is not None:
            try:
                if not _doc.is_closed:
                    _doc.close()
            except Exception as e:
                logger.debug("[清理] 关闭 doc 出错（可忽略）: %s", type(e).__name__)
        # 清理临时文件
        if hasattr(self, 'temp_manager'):
            self.temp_manager.cleanup()

        # 清理旧版临时文件
        self._cleanup_temp_file()

    # v22.4: 移除 eventFilter，直接在 SinglePageCanvas.mousePressEvent 中处理

    def setup_ui(self):
        # 统一上下文条：文档上下文 + 临时任务提示
        self.default_info_bar_text = "📝 支持直接拖拽导入，系统会按文件类型自动进入 PDF 脱敏、Word 替换、批量 Word 或图片合并。"
        self.workbench_panel = QFrame()
        self.workbench_panel.setObjectName("workbenchPanel")
        workbench_layout = QVBoxLayout(self.workbench_panel)
        workbench_layout.setContentsMargins(16, 10, 16, 10)
        workbench_layout.setSpacing(4)
        self.workbench_layout = workbench_layout

        context_top_layout = QHBoxLayout()
        context_top_layout.setSpacing(14)
        context_top_layout.setContentsMargins(0, 0, 0, 0)
        self.context_top_layout = context_top_layout
        workbench_text = QVBoxLayout()
        workbench_text.setContentsMargins(0, 0, 0, 0)
        workbench_text.setSpacing(4)
        self.workbench_text_layout = workbench_text

        self.lbl_workbench_title = QLabel("欢迎使用 PrivacyGuard")
        self.lbl_workbench_title.setObjectName("workbenchTitle")
        self.lbl_workbench_subtitle = QLabel("拖拽或打开文件即可开始处理。")
        self.lbl_workbench_subtitle.setObjectName("workbenchSubtitle")
        self.lbl_workbench_subtitle.setWordWrap(True)
        workbench_text.addWidget(self.lbl_workbench_title)
        workbench_text.addWidget(self.lbl_workbench_subtitle)

        self.lbl_workbench_focus = QLabel("开始")
        self.lbl_workbench_focus.setObjectName("workbenchFocus")
        self.btn_workbench_feedback = self.create_btn("使用/反馈", self.show_feedback, style="secondary")
        self.btn_workbench_feedback.hide()

        context_top_layout.addLayout(workbench_text, stretch=1)
        context_top_layout.addWidget(self.btn_workbench_feedback, alignment=Qt.AlignmentFlag.AlignVCenter)
        context_top_layout.addWidget(self.lbl_workbench_focus, alignment=Qt.AlignmentFlag.AlignVCenter)
        workbench_layout.addLayout(context_top_layout)

        workbench_guidance_layout = QGridLayout()
        workbench_guidance_layout.setHorizontalSpacing(8)
        workbench_guidance_layout.setVerticalSpacing(8)
        workbench_guidance_layout.setContentsMargins(0, 0, 0, 0)
        workbench_guidance_layout.setColumnStretch(0, 1)
        workbench_guidance_layout.setColumnStretch(1, 1)
        self.workbench_guidance_layout = workbench_guidance_layout
        self.workbench_guidance_labels = []
        for index in range(4):
            guidance_label = QLabel("")
            guidance_label.setObjectName("workbenchHintTag")
            guidance_label.setWordWrap(True)
            guidance_label.hide()
            row = index // 2
            col = index % 2
            workbench_guidance_layout.addWidget(guidance_label, row, col)
            self.workbench_guidance_labels.append(guidance_label)
        workbench_layout.addLayout(workbench_guidance_layout)

        self.info_bar = QLabel(self.default_info_bar_text)
        self.info_bar.setObjectName("contextMessage")
        self.info_bar.setWordWrap(True)
        self.info_bar.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        workbench_layout.addWidget(self.info_bar)

        # 工具栏
        toolbar = QFrame()
        toolbar.setObjectName("toolbarRoot")
        toolbar.setFixedHeight(54)
        self.toolbar = toolbar  # 保存引用

        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(16, 7, 16, 7)
        tb_layout.setSpacing(10)
        self.toolbar_layout = tb_layout

        self.toolbar_primary_group, self.toolbar_primary_layout = self._create_toolbar_group("toolbarGroupStrong")
        tb_layout.addWidget(self.toolbar_primary_group)
        self.btn_open = self.create_btn("打开", self.open_pdf)
        self.toolbar_primary_layout.addWidget(self.btn_open)

        self.toolbar_word_group, self.toolbar_word_layout = self._create_toolbar_group()
        tb_layout.addWidget(self.toolbar_word_group)
        self.btn_settings = self.create_btn("", self.open_settings, style="icon",
                                            tooltip="高级设置：脱敏规则 / 关键词 / 功能开关")
        self.btn_settings.setObjectName("toolbarSettingsButton")
        self.btn_settings.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "settings_gear.svg"))))
        self.toolbar_word_layout.addWidget(self.btn_settings)
        # v40.1.4（用户反馈）：去水印固定放"高级设置"右侧（原在左上主操作组，
        # v40.0 工具栏变挤后 narrow 模式被收进"更多"菜单，用户找不到）。
        # 仅 PDF 模式显示；narrow 不再收纳（见 _refresh_toolbar_overflow_menu）。
        self.btn_remove_watermark = self.create_btn(
            "去水印", self.remove_case_file_watermark, style="secondary",
            tooltip="去除电子卷宗律师证号水印"
        )
        self.btn_remove_watermark.hide()
        self.toolbar_word_layout.addWidget(self.btn_remove_watermark)
        self.btn_compare_toggle = self.create_btn("对比预览", self.toggle_word_compare_preview, style="secondary")
        self.toolbar_word_layout.addWidget(self.btn_compare_toggle)
        # 预览高亮按来源筛选（规则/手动/智能），下拉菜单式多选
        self.btn_highlight_filter = self.create_btn(
            "高亮筛选", lambda: None, style="secondary",
            tooltip="按来源显示/隐藏预览高亮（规则替换/手动脱敏/智能脱敏）"
        )
        self._highlight_filter_menu = QMenu(self)
        self._highlight_filter_actions = {}
        for _src, _label in (("rule", "规则替换"), ("manual", "手动脱敏"), ("ocr", "智能脱敏")):
            _act = self._highlight_filter_menu.addAction(_label)
            _act.setCheckable(True)
            _act.setChecked(True)
            _act.toggled.connect(
                lambda checked, s=_src: self.toggle_preview_highlight_source(s, checked)
            )
            self._highlight_filter_actions[_src] = _act
        self.btn_highlight_filter.setMenu(self._highlight_filter_menu)
        self.toolbar_word_layout.addWidget(self.btn_highlight_filter)

        self.toolbar_pdf_group, self.toolbar_pdf_layout = self._create_toolbar_group()
        tb_layout.addWidget(self.toolbar_pdf_group)
        # v40.1.4（用户反馈 #5）：黑/白/取色遮罩改图标按钮（tooltip 说明含义）
        self.rb_black = self.create_btn("", self.update_canvas_color, style="toggle",
                                        tooltip="黑遮罩：用黑色涂抹命中区域")
        self.rb_black.setObjectName("toolbarToggleButton")
        self.rb_black.setCheckable(True)
        self.rb_black.setChecked(True)
        self.rb_black.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "mask_black.svg"))))
        self.rb_white = self.create_btn("", self.update_canvas_color, style="toggle",
                                        tooltip="白遮罩：用白色涂抹命中区域")
        self.rb_white.setObjectName("toolbarToggleButton")
        self.rb_white.setCheckable(True)
        self.rb_white.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "mask_white.svg"))))
        # v37.7.10 cp39: 取色遮罩按钮（与黑/白遮互斥，点击展开色板面板）
        self.rb_color = self.create_btn("", self._toggle_color_palette, style="toggle",
                                        tooltip="取色遮罩：自选任意颜色涂抹")
        self.rb_color.setObjectName("toolbarToggleButton")
        self.rb_color.setCheckable(True)
        self.rb_color.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "mask_color.svg"))))
        self.bg_color = QButtonGroup(self)
        self.bg_color.setExclusive(True)
        self.bg_color.addButton(self.rb_black)
        self.bg_color.addButton(self.rb_white)
        self.bg_color.addButton(self.rb_color)
        self.toolbar_pdf_layout.addWidget(self.rb_black)
        self.toolbar_pdf_layout.addWidget(self.rb_white)
        self.toolbar_pdf_layout.addWidget(self.rb_color)

        # cp68: “双页”按钮已移除（页面视图功能覆盖其用途）；dual_view 内部机制保留便于回滚
        # cp67: 页面视图（多页网格总览）切换按钮
        # cp84/cp85: 页面+撤销+恢复独立成“视图/编辑”组，与遮罩色组拉开组间距
        self.toolbar_edit_group, self.toolbar_edit_layout = self._create_toolbar_group()
        tb_layout.addWidget(self.toolbar_edit_group)
        self.cb_page_view = self.create_btn("", self._toggle_page_view_toolbar, style="toggle",
                                            tooltip="页面视图：多页总览（Ctrl/⌘+滚轮调节每行页数）")
        self.cb_page_view.setObjectName("toolbarToggleButton")
        self.cb_page_view.setCheckable(True)
        self.cb_page_view.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "page_view_grid.svg"))))
        self.toolbar_edit_layout.addWidget(self.cb_page_view)

        # cp83: 撤销/恢复按钮（页面按钮右侧，线条图标）
        self.btn_undo = self.create_btn("", self.undo, style="icon", tooltip="撤销上一步 (Ctrl+Z)")
        self.btn_undo.setObjectName("toolbarUndoButton")
        self.btn_undo.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "undo.svg"))))
        self.btn_undo.setEnabled(False)
        self.toolbar_edit_layout.addWidget(self.btn_undo)
        # cp121: 重置按钮（撤销/恢复之间，圆形回环箭头）——恢复到打开时初始状态
        self.btn_reset = self.create_btn("", self.reset_document, style="icon",
                                         tooltip="重置文档：清除所有遮罩与编辑，恢复到刚打开时的状态")
        self.btn_reset.setObjectName("toolbarResetButton")
        self.btn_reset.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "reset.svg"))))
        self.btn_reset.setEnabled(False)
        self.toolbar_edit_layout.addWidget(self.btn_reset)
        self.btn_redo = self.create_btn("", self.redo, style="icon", tooltip="恢复到上一步 (Ctrl+Y)")
        self.btn_redo.setObjectName("toolbarRedoButton")
        self.btn_redo.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "redo.svg"))))
        self.btn_redo.setEnabled(False)
        self.toolbar_edit_layout.addWidget(self.btn_redo)
        # cp123: 提取/截去按钮（toggle 互斥）
        self.btn_extract = self.create_btn("", lambda c: self._on_extract_toggle(c), style="toggle",
                                           tooltip="提取：框选纵向区域裁剪到独立结果文档")
        self.btn_extract.setObjectName("toolbarExtractButton")
        self.btn_extract.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "page_extract.svg"))))
        self.btn_extract.setCheckable(True)
        self.btn_extract.setEnabled(False)
        self.toolbar_edit_layout.addWidget(self.btn_extract)
        self.btn_crop = self.create_btn("", lambda c: self._on_crop_toggle(c), style="toggle",
                                        tooltip="截去：框选纵向区域从当前页挖掉并上下拼接")
        self.btn_crop.setObjectName("toolbarCropButton")
        self.btn_crop.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "page_crop.svg"))))
        self.btn_crop.setCheckable(True)
        self.btn_crop.setEnabled(False)
        self.toolbar_edit_layout.addWidget(self.btn_crop)

        self.btn_fit = self.create_btn("⛶", self.fit_page, style="icon",
                                       tooltip="适应页面（按窗口大小缩放）")
        self.toolbar_pdf_layout.addWidget(self.btn_fit)
        self.btn_fit.hide()

        # cp86: 左侧操作组与右侧 utility 之间的伸缩项（吸收左半留白）
        tb_layout.addStretch(1)

        # v40.1.6（用户反馈）：缩放/翻页控制作为嵌入式底部状态栏，
        # 融入 previewWorkspaceCard 卡片底缘（顶部细分隔线、透明底），
        # 不再悬浮遮挡文档内容；按钮为工具栏风格（无边框、hover 淡蓝）。
        # 回滚备份：backups/main.py.pre_bottombar_20260818_201449
        self.doc_bottom_bar = QWidget()
        self.doc_bottom_bar.setObjectName("docBottomBar")
        self.doc_bottom_bar.setFixedHeight(21)  # v40.1.5：按钮 20 + 顶线 1，三压
        _bb = QHBoxLayout(self.doc_bottom_bar)
        _bb.setContentsMargins(16, 0, 16, 0)
        _bb.setSpacing(2)
        _mini_qss = """
            QPushButton {
                background: transparent; color: #4A5568;
                border: none; border-radius: 4px;
                padding: 0px; min-width: 0px; min-height: 0px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: rgba(37, 99, 235, 0.08); color: #2563EB; }
            QPushButton:pressed { background-color: rgba(37, 99, 235, 0.14); }
            QPushButton:disabled { color: #B8C0CC; background: transparent; }
        """
        def _mk_mini(text, func, tooltip, w=26, h=20):
            b = QPushButton(text)
            b.clicked.connect(func)
            b.setFixedSize(w, h)
            b.setToolTip(tooltip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(_mini_qss)
            return b
        self.lbl_zoom = QLabel("100%")
        # v40.1.5（用户反馈）：标签与按钮同高（24）强制同一中线，字号对齐按钮观感
        self.lbl_zoom.setFixedHeight(20)
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        # v40.1.5（用户反馈）：数字上移 4px 与按钮字形基线对齐
        self.lbl_zoom.setContentsMargins(0, -6, 0, 6)
        self.lbl_zoom.setStyleSheet("font-size: 11px; color: #66707E; background: transparent; min-width: 40px;")
        self.btn_zoom_out = _mk_mini("−", self.zoom_out, "缩小预览")
        self.btn_zoom_in = _mk_mini("+", self.zoom_in, "放大预览")
        self.btn_go_first = _mk_mini("⏮", self.go_first, "跳到第一页", w=28)
        self.btn_prev_page = _mk_mini("‹", lambda: self.change_page(-1), "上一页", w=28)
        self.lbl_page = QLabel("0 / 0")
        self.lbl_page.setFixedHeight(20)
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        self.lbl_page.setContentsMargins(0, -6, 0, 6)
        self.lbl_page.setStyleSheet("font-size: 11px; color: #66707E; background: transparent; min-width: 52px;")
        self.btn_next_page = _mk_mini("›", lambda: self.change_page(1 if not self.dual_view else 2), "下一页", w=28)
        self.btn_go_last = _mk_mini("⏭", self.go_last, "跳到最后一页", w=28)
        # 居中控制组：缩放 − 分隔线 − 翻页，整体作为嵌入状态栏的视觉中心
        _bb.addStretch(1)
        _bb.addWidget(self.btn_zoom_out)
        _bb.addWidget(self.lbl_zoom)
        _bb.addWidget(self.btn_zoom_in)
        _sep = QFrame()
        _sep.setFrameShape(QFrame.Shape.VLine)
        _sep.setStyleSheet("color: #DDE3EB; background: #DDE3EB; max-width: 1px; max-height: 14px;")
        _bb.addSpacing(10)
        _bb.addWidget(_sep)
        _bb.addSpacing(10)
        _bb.addWidget(self.btn_go_first)
        _bb.addWidget(self.btn_prev_page)
        _bb.addWidget(self.lbl_page)
        _bb.addWidget(self.btn_next_page)
        _bb.addWidget(self.btn_go_last)
        _bb.addStretch(1)
        # v40.1.5：迁至 content_row 同层持久条（浅底 + 顶线），页面视图下不再被连坐隐藏
        self.doc_bottom_bar.setStyleSheet(
            "#docBottomBar { background-color: #F7F9FC; border-top: 1px solid #E2E7EF; }")
        self.doc_bottom_bar.hide()

        # cp86: 中部与右侧 utility（搜索/加密/智能脱敏/导出）之间的伸缩项：
        # 吸收右半留白，使 utility 组始终贴右且不会被先裁切（左侧组优先让位）
        tb_layout.addStretch(1)

        self.toolbar_utility_group, self.toolbar_utility_layout = self._create_toolbar_group("toolbarUtilityGroup")
        tb_layout.addWidget(self.toolbar_utility_group)
        self.btn_fit_utility = self.create_btn("⛶", self.fit_page, style="icon",
                                               tooltip="适应页面（按窗口大小缩放）")
        self.btn_fit_utility.hide()
        self.toolbar_utility_layout.addWidget(self.btn_fit_utility)
        self.btn_feedback = self.create_btn("使用/反馈", self.show_feedback, style="secondary")
        self.toolbar_utility_layout.addWidget(self.btn_feedback)
        self.btn_more = self.create_btn("更多", self._show_toolbar_more_menu, style="secondary")
        self.btn_more.setObjectName("toolbarMoreButton")
        self.toolbar_more_menu = QMenu(self)
        self.btn_more.hide()
        self.toolbar_utility_layout.addWidget(self.btn_more)
        # cp81: 搜索按钮（放大镜图标），位于加密按钮左侧；PDF/Word 模式均可见
        self.btn_search = self.create_btn("", self.toggle_search_panel, style="icon",
                                          tooltip="搜索：全文查找文字（扫描件自动 OCR）")
        self.btn_search.setObjectName("toolbarSearchButton")
        self.btn_search.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "search_magnifier.svg"))))
        self.toolbar_utility_layout.addWidget(self.btn_search)
        # cp_bookmark: 书签按钮（书签图标），切换左侧书签面板；仅 PDF 模式有意义
        self.btn_bookmark = self.create_btn("", self.toggle_bookmark_panel, style="icon",
                                            tooltip="书签：查看/编辑 PDF 目录（跳转/增删改）")
        self.btn_bookmark.setObjectName("toolbarBookmarkButton")
        self.btn_bookmark.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "bookmark.svg"))))
        self.toolbar_utility_layout.addWidget(self.btn_bookmark)
        # cp72: 加密按钮（锁图标），位于“智能脱敏”左侧；仅 PDF/图片模式可见
        self.btn_encrypt = self.create_btn("", self.open_encrypt_dialog, style="icon",
                                           tooltip="加密：为导出的 PDF 设置打开/编辑密码")
        self.btn_encrypt.setObjectName("toolbarEncryptButton")
        self.btn_encrypt.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "lock_encrypt.svg"))))
        self.toolbar_utility_layout.addWidget(self.btn_encrypt)
        # cp66: 位置对调：智能脱敏移入右侧 utility 组（原去水印位置：更多之后、导出之前）
        self.btn_scan = self.create_btn("智能脱敏", self.start_ocr, enabled=False, style="success")
        self.toolbar_utility_layout.addWidget(self.btn_scan)
        self.btn_save = self.create_btn("导出", self.save_pdf, enabled=False)
        self.toolbar_utility_layout.addWidget(self.btn_save)
        self._apply_native_toolbar_icons()

        # cp83: 撤销/恢复快捷键（Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z）
        self._sc_undo = QShortcut(QKeySequence.StandardKey.Undo, self)
        self._sc_undo.activated.connect(self.undo)
        self._sc_redo = QShortcut(QKeySequence.StandardKey.Redo, self)
        self._sc_redo.activated.connect(self.redo)

        main = QWidget()
        main.setObjectName("appRoot")
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.workbench_panel)
        layout.addWidget(toolbar)

        # v37.7.10 cp39: 取色遮罩色板面板（内联展开，初始隐藏）
        # 点击 rb_color 按钮后展开，提供常用色块 + 自定义色值输入 + 全屏取色器
        self.color_palette_widget = self._build_color_palette_widget()
        self.color_palette_widget.hide()
        layout.addWidget(self.color_palette_widget)

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        # cp77: scroll 样式必须带 QScrollArea 选择器——无选择器样式会传播到所有
        # 后代裸 QWidget（如主页 idle_start_footer），把它们错涂成 scroll_area 色，
        # 在 #F9FBFE 卡片内形成突兀的 #F6F8FB 方块；卡外底色由 mainContainer 规则承接
        self.scroll_style = (
            "QScrollArea {{ background-color: {0}; "
            "border-radius: " + str(Theme.BORDER_RADIUS) + "px; "
            "border: none; }}"
        )

        # v22.9: 使用固定的 canvas_container，通过隐藏/显示实现单/双页切换
        self.canvas_left = SinglePageCanvas(0)
        self.canvas_right = SinglePageCanvas(1)

        # cp123 接线修复：实例化 ExtractSidePanel 并一次性连接信号。
        # 此前缺失此初始化导致 enter_extract_mode() 调用 self.extract_side_panel 时
        # 抛 AttributeError，提取功能完全不可用。
        from privacyguard.ui.panels import ExtractSidePanel
        self.extract_side_panel = ExtractSidePanel(self)
        self.extract_side_panel.hide()
        self.extract_side_panel.new_page_clicked.connect(self._start_new_result_page)
        self.extract_side_panel.export_clicked.connect(self._finish_extract)
        self.extract_side_panel.delete_clicked.connect(self._delete_selected_segment)
        self.extract_side_panel.move_up_clicked.connect(lambda: self._move_selected_segment(-1))
        self.extract_side_panel.move_down_clicked.connect(lambda: self._move_selected_segment(1))
        self.extract_side_panel.replace_clicked.connect(self._replace_selected_segment)
        self.extract_side_panel.prev_page_clicked.connect(lambda: self._change_view_page(-1))
        self.extract_side_panel.next_page_clicked.connect(lambda: self._change_view_page(1))

        # 容器始终作为 scroll 的 widget
        self.canvas_container = QWidget()
        self.pdf_workspace_outer_layout = QVBoxLayout(self.canvas_container)
        self.pdf_workspace_outer_layout.setContentsMargins(14, 10, 14, 16)
        self.pdf_workspace_outer_layout.setSpacing(0)
        self.pdf_workspace_shell = QFrame()
        self.pdf_workspace_shell.setObjectName("previewWorkspaceCard")
        self.pdf_workspace_shell.setMaximumWidth(1940)
        self.pdf_workspace_shell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        pdf_workspace_shell_layout = QVBoxLayout(self.pdf_workspace_shell)
        # 底部边距 0：状态栏自身高 32，顶部分隔线即卡片底缘分界
        pdf_workspace_shell_layout.setContentsMargins(8, 8, 8, 0)
        pdf_workspace_shell_layout.setSpacing(0)
        self.pdf_workspace_shell_layout = pdf_workspace_shell_layout
        self.pdf_stage_content = QWidget()
        self.pdf_stage_content.setObjectName("previewStage")
        self.canvas_layout = QHBoxLayout(self.pdf_stage_content)
        self.canvas_layout.setContentsMargins(10, 10, 10, 10)
        self.canvas_layout.setSpacing(12)
        self.canvas_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.canvas_left.setObjectName("pdfPageCanvas")
        self.canvas_right.setObjectName("pdfPageCanvas")
        self.canvas_layout.addWidget(self.canvas_left)
        self.canvas_layout.addWidget(self.canvas_right)
        pdf_workspace_shell_layout.addWidget(self.pdf_stage_content, 1)
        pdf_workspace_row_layout = QHBoxLayout()
        pdf_workspace_row_layout.setContentsMargins(0, 0, 0, 0)
        pdf_workspace_row_layout.setSpacing(0)
        pdf_workspace_row_layout.addStretch(1)
        pdf_workspace_row_layout.addWidget(self.pdf_workspace_shell, 18)
        pdf_workspace_row_layout.addStretch(1)
        # cp123: 提取模式右侧工具栏加到布局（缺失则面板显示不全/提取交互异常）
        pdf_workspace_row_layout.addWidget(self.extract_side_panel)
        self.pdf_workspace_row_layout = pdf_workspace_row_layout
        self.pdf_workspace_outer_layout.addLayout(pdf_workspace_row_layout, 1)

        # 信号连接
        self.canvas_left.rect_added.connect(self.on_rect_added)
        self.canvas_left.rect_removed.connect(self.on_rect_removed)
        self.canvas_left.zoom_request.connect(self.handle_zoom_request)
        self.canvas_left.page_change_request.connect(self.handle_page_change_request)
        # cp65: 手动框选替换开关开启时的识别+弹窗流程
        self.canvas_left.manual_region_prompt.connect(
            lambda rect: self._handle_manual_region_prompt(self.canvas_left, rect))

        self.canvas_right.rect_added.connect(self.on_rect_added)
        self.canvas_right.rect_removed.connect(self.on_rect_removed)
        self.canvas_right.zoom_request.connect(self.handle_zoom_request)
        self.canvas_right.page_change_request.connect(self.handle_page_change_request)
        self.canvas_right.manual_region_prompt.connect(
            lambda rect: self._handle_manual_region_prompt(self.canvas_right, rect))

        # 设置 canvas 大小策略
        for canvas in [self.canvas_left, self.canvas_right]:
            canvas.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        # 预先创建 Word 预览视图（左：原文，右：替换后）
        self.word_preview = QWebEngineView()
        self.word_preview_replaced = QWebEngineView()
        # 安全审计 v40.1.4（A1）：换用导航白名单页，拒绝远程导航
        for _pv in (self.word_preview, self.word_preview_replaced):
            _pv.setPage(NoExternalNavWebPage(_pv))
        # P1-3: WebEngine 硬化——禁止 file:// 页面经 JS 访问其他 file:// 资源，
        # 收窄恶意脚本的攻击面（XSS 首道防线为 mammoth 输出白名单消毒）。
        try:
            from PyQt6.QtWebEngineCore import QWebEngineSettings
            for _pv in (self.word_preview, self.word_preview_replaced):
                _pv.settings().setAttribute(
                    QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False)
        except Exception as e:
            logger.warning("[Word预览] WebEngine 本地访问加固失败（不影响功能）: %s", type(e).__name__)
        self.word_preview_replaced.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.word_preview.loadFinished.connect(self._on_word_preview_load_finished)
        self.word_preview_replaced.loadFinished.connect(self._on_word_replaced_load_finished)

        self.idle_workspace_container = QWidget()
        idle_outer_layout = QVBoxLayout(self.idle_workspace_container)
        idle_outer_layout.setContentsMargins(30, 20, 30, 30)
        idle_outer_layout.setSpacing(0)
        self.idle_outer_layout = idle_outer_layout

        idle_card = QFrame()
        idle_card.setObjectName("workspaceCard")
        idle_card.setMaximumWidth(16777215)  # 跟随窗口填满，均衡边距由 idle_outer_layout 提供
        idle_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.idle_card = idle_card
        idle_card_layout = QVBoxLayout(idle_card)
        idle_card_layout.setContentsMargins(28, 26, 28, 26)
        idle_card_layout.setSpacing(16)
        self.idle_card_layout = idle_card_layout

        idle_hero_panel = QFrame()
        idle_hero_panel.setObjectName("idleHeroPanel")
        idle_hero_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        idle_hero_layout = QVBoxLayout(idle_hero_panel)
        idle_hero_layout.setContentsMargins(0, 0, 0, 0)
        idle_hero_layout.setSpacing(12)
        self.idle_hero_panel = idle_hero_panel
        self.idle_hero_layout = idle_hero_layout

        idle_title_row_layout = QHBoxLayout()
        idle_title_row_layout.setContentsMargins(0, 0, 0, 0)
        idle_title_row_layout.setSpacing(18)
        self.idle_title_row_layout = idle_title_row_layout

        idle_headline_layout = QVBoxLayout()
        idle_headline_layout.setContentsMargins(0, 0, 0, 0)
        idle_headline_layout.setSpacing(6)
        self.idle_headline_layout = idle_headline_layout

        idle_title = QLabel("选择开始方式")
        idle_title.setObjectName("workspaceTitle")
        idle_subtitle = QLabel("打开或拖拽文件，系统会自动进入对应模式。所有处理本地完成，文档不出本机。")
        idle_subtitle.setObjectName("workspaceSubtitle")
        idle_subtitle.setWordWrap(True)
        idle_headline_layout.addWidget(idle_title)
        idle_headline_layout.addWidget(idle_subtitle)

        # 徽章行（标题下方，纯文字避免 emoji 跨平台差异）
        idle_badge_row_layout = QHBoxLayout()
        idle_badge_row_layout.setContentsMargins(0, 4, 0, 0)
        idle_badge_row_layout.setSpacing(8)
        self.idle_badge_row_layout = idle_badge_row_layout
        self.lbl_idle_offline_badge = QLabel("本地离线")
        self.lbl_idle_offline_badge.setObjectName("idleHeroBadge")
        self.lbl_idle_auto_badge = QLabel("自动分流")
        self.lbl_idle_auto_badge.setObjectName("idleHeroBadge")
        self.lbl_idle_safe_badge = QLabel("智能 + 手动")
        self.lbl_idle_safe_badge.setObjectName("idleHeroBadge")
        idle_badge_row_layout.addWidget(self.lbl_idle_offline_badge)
        idle_badge_row_layout.addWidget(self.lbl_idle_auto_badge)
        idle_badge_row_layout.addWidget(self.lbl_idle_safe_badge)
        idle_badge_row_layout.addStretch()
        idle_headline_layout.addLayout(idle_badge_row_layout)

        # 右侧弹性留白（盾牌图标圈已按用户反馈移除）；tools_layout 保留供密度切换引用
        idle_title_tools_layout = QVBoxLayout()
        idle_title_tools_layout.setContentsMargins(0, 0, 0, 0)
        idle_title_tools_layout.setSpacing(8)
        self.idle_title_tools_layout = idle_title_tools_layout
        idle_title_tools_layout.addStretch(1)

        idle_title_row_layout.addLayout(idle_headline_layout, stretch=1)
        idle_title_row_layout.addLayout(idle_title_tools_layout)
        idle_hero_layout.addLayout(idle_title_row_layout)

        idle_action_panel = QFrame()
        idle_action_panel.setObjectName("idleActionPanel")
        idle_action_panel_layout = QVBoxLayout(idle_action_panel)
        idle_action_panel_layout.setContentsMargins(0, 0, 0, 0)
        idle_action_panel_layout.setSpacing(8)
        self.idle_action_panel = idle_action_panel
        self.idle_action_panel_layout = idle_action_panel_layout

        idle_action_buttons_layout = QGridLayout()
        idle_action_buttons_layout.setContentsMargins(0, 0, 0, 0)
        idle_action_buttons_layout.setHorizontalSpacing(16)
        idle_action_buttons_layout.setVerticalSpacing(12)
        idle_action_buttons_layout.setColumnStretch(0, 1)
        idle_action_buttons_layout.setColumnStretch(1, 1)
        self.idle_action_buttons_layout = idle_action_buttons_layout

        self.idle_start_card = QFrame()
        self.idle_start_card.setObjectName("idleStartCard")
        idle_start_layout = QHBoxLayout(self.idle_start_card)
        idle_start_layout.setContentsMargins(22, 20, 22, 20)
        idle_start_layout.setSpacing(18)
        self.idle_start_layout = idle_start_layout

        # 左：导入图标圈（醒目视觉焦点）
        self.lbl_idle_start_icon = QLabel("↑")
        self.lbl_idle_start_icon.setObjectName("idleStartIcon")
        self.lbl_idle_start_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 中：标题 + 说明
        idle_start_text_box = QVBoxLayout()
        idle_start_text_box.setContentsMargins(0, 0, 0, 0)
        idle_start_text_box.setSpacing(5)
        self.idle_start_text_box = idle_start_text_box
        self.lbl_idle_start_title = QLabel("把文件拖到这里，或点击选择")
        self.lbl_idle_start_title.setObjectName("idleStartTitle")
        self.lbl_idle_start_text = QLabel("系统会按文件类型自动进入对应模式。")
        self.lbl_idle_start_text.setObjectName("idleStartText")
        self.lbl_idle_start_text.setWordWrap(True)
        self.lbl_idle_drop_hint = QLabel("支持 PDF · Word（.docx/.doc）· 图片（jpg/png/…）　|　多选拖入可触发批量")
        self.lbl_idle_drop_hint.setObjectName("idleDropHint")
        self.lbl_idle_drop_hint.setWordWrap(True)
        idle_start_text_box.addWidget(self.lbl_idle_start_title)
        idle_start_text_box.addWidget(self.lbl_idle_start_text)
        idle_start_text_box.addWidget(self.lbl_idle_drop_hint)
        idle_start_text_box.addStretch(1)

        # 右：主按钮（放大）
        self.btn_idle_open = self.create_btn("选择文件", self.open_pdf)
        self.btn_idle_open.setObjectName("idlePrimaryActionButton")
        self.btn_idle_open.setProperty("btn_style", "idle_primary")
        self.btn_idle_open.setStyleSheet(self._get_button_style("idle_primary"))
        self.btn_idle_open.setMinimumHeight(46)
        self.btn_idle_open.setMinimumWidth(170)

        # 保留 footer 控件引用（外部兼容），新布局不再使用它
        self.idle_start_footer = QWidget()
        self.idle_start_footer_layout = QVBoxLayout(self.idle_start_footer)

        idle_start_layout.addWidget(self.lbl_idle_start_icon)
        idle_start_layout.addLayout(idle_start_text_box, stretch=1)
        idle_start_layout.addWidget(self.btn_idle_open, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.idle_support_card = QFrame()
        self.idle_support_card.setObjectName("idleSupportCard")
        idle_support_layout = QHBoxLayout(self.idle_support_card)
        idle_support_layout.setContentsMargins(18, 16, 18, 16)
        idle_support_layout.setSpacing(14)
        self.lbl_idle_support_title = QLabel("开发者与支持")
        self.lbl_idle_support_title.setObjectName("idleSupportTitle")
        self.lbl_idle_support_text = QLabel("汪立 · 安徽始信律师事务所执业律师")
        self.lbl_idle_support_text.setObjectName("idleSupportText")
        self.lbl_idle_support_text.setWordWrap(True)
        self.lbl_idle_support_meta = QLabel("全栈律师｜前教师｜退伍军人")
        self.lbl_idle_support_meta.setObjectName("idleSupportMeta")
        self.lbl_idle_support_email = QLabel("<a href='mailto:491445490@qq.com'>491445490@qq.com</a>")
        self.lbl_idle_support_email.setObjectName("idleSupportEmail")
        self.lbl_idle_support_email.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_idle_support_email.setOpenExternalLinks(True)
        self.lbl_idle_support_note = QLabel("遇到问题、想看手册或支持更新，都可以直接从这里进入。")
        self.lbl_idle_support_note.setObjectName("idleSupportNote")
        self.lbl_idle_support_note.setWordWrap(True)
        idle_support_actions_layout = QGridLayout()
        idle_support_actions_layout.setContentsMargins(0, 0, 0, 0)
        idle_support_actions_layout.setHorizontalSpacing(8)
        idle_support_actions_layout.setVerticalSpacing(10)
        # 不设列 stretch：按钮按内容宽度排布，整体向左靠拢
        self.idle_support_actions_layout = idle_support_actions_layout
        self.btn_idle_feedback = self.create_btn("反馈建议", self._open_feedback, style="primary")
        self.btn_idle_feedback.setObjectName("idleFeedbackActionButton")
        self.btn_idle_feedback.setProperty("btn_style", "primary")
        self.btn_idle_feedback.setStyleSheet(self._get_button_style("primary"))
        self.btn_idle_manual = self.create_btn("使用手册", self._open_manual, style="secondary")
        self.btn_idle_manual.setObjectName("idleManualActionButton")
        self.btn_idle_manual.setProperty("btn_style", "secondary")
        self.btn_idle_manual.setStyleSheet(self._get_button_style("secondary"))
        self.btn_idle_donate = self.create_btn("打赏支持", self._show_donate, style="success")
        self.btn_idle_donate.setObjectName("idleDonateActionButton")
        self.btn_idle_donate.setProperty("btn_style", "success")
        self.btn_idle_donate.setStyleSheet(self._get_button_style("success"))
        # 左：文字信息 + 动作按钮（向左靠拢）
        idle_support_left_layout = QVBoxLayout()
        idle_support_left_layout.setContentsMargins(0, 0, 0, 0)
        idle_support_left_layout.setSpacing(8)
        idle_support_left_layout.addWidget(self.lbl_idle_support_title)
        idle_support_left_layout.addWidget(self.lbl_idle_support_text)
        idle_support_left_layout.addWidget(self.lbl_idle_support_meta)
        idle_support_left_layout.addWidget(self.lbl_idle_support_email)
        idle_support_left_layout.addWidget(self.lbl_idle_support_note)
        idle_support_left_layout.addStretch(1)
        idle_support_left_layout.addLayout(idle_support_actions_layout)

        # 右：微信二维码 + 关注提示（垂直居中）
        idle_support_qr_box = QVBoxLayout()
        idle_support_qr_box.setContentsMargins(0, 0, 0, 0)
        idle_support_qr_box.setSpacing(4)
        self.lbl_idle_support_qr = QLabel()
        self.lbl_idle_support_qr.setObjectName("idleSupportQr")
        self.lbl_idle_support_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _qr_pixmap = QPixmap(resource_path(os.path.join("assets", "wx_qrcode.png")))
        if not _qr_pixmap.isNull():
            # 白底二维码合成到卡片底色上，消除白色背景圈（白色×底色=底色，码点不变）
            _qr_canvas = QPixmap(_qr_pixmap.size())
            _qr_canvas.fill(QColor("#F9FBFE"))
            _qr_painter = QPainter(_qr_canvas)
            _qr_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
            _qr_painter.drawPixmap(0, 0, _qr_pixmap)
            _qr_painter.end()
            self.lbl_idle_support_qr.setPixmap(
                _qr_canvas.scaled(
                    128, 128,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.lbl_idle_support_qr.setText("二维码缺失")
        self.lbl_idle_support_qr_caption = QLabel("扫一扫添加开发者微信公众号")
        self.lbl_idle_support_qr_caption.setObjectName("idleSupportQrCaption")
        self.lbl_idle_support_qr_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        idle_support_qr_box.addStretch(1)
        idle_support_qr_box.addWidget(self.lbl_idle_support_qr)
        idle_support_qr_box.addWidget(self.lbl_idle_support_qr_caption)
        idle_support_qr_box.addStretch(1)

        idle_support_layout.addLayout(idle_support_left_layout, stretch=1)
        idle_support_layout.addLayout(idle_support_qr_box)
        # 主操作卡占满整行（突出第一焦点）；支持卡移至页面底部弱化
        idle_action_buttons_layout.addWidget(self.idle_start_card, 0, 0, 1, 2)
        idle_action_panel_layout.addLayout(idle_action_buttons_layout)
        idle_hero_layout.addWidget(idle_action_panel)
        idle_card_layout.addWidget(idle_hero_panel)

        idle_flow_panel = QFrame()
        idle_flow_panel.setObjectName("idleFlowPanel")
        idle_flow_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        idle_flow_layout = QHBoxLayout(idle_flow_panel)
        idle_flow_layout.setContentsMargins(0, 2, 0, 0)
        idle_flow_layout.setSpacing(10)
        self.idle_flow_panel = idle_flow_panel
        self.idle_flow_layout = idle_flow_layout

        self.lbl_idle_tip = QLabel("推荐流程")
        self.lbl_idle_tip.setObjectName("idleFlowTitle")
        idle_flow_layout.addWidget(self.lbl_idle_tip)

        workflow_layout = QHBoxLayout()
        workflow_layout.setSpacing(10)
        self.workflow_layout = workflow_layout
        self.workflow_step_labels = []
        _FLOW_STEPS = [
            ("1", "导入文件", "打开 / 拖拽，自动分流"),
            ("2", "脱敏处理", "智能识别 / 手动框选 / 规则替换"),
            ("3", "导出结果", "AES-256 加密 + 脱敏报告"),
        ]
        for _i, (_num, _title, _sub) in enumerate(_FLOW_STEPS):
            _step_widget = QWidget()
            _step_layout = QHBoxLayout(_step_widget)
            _step_layout.setContentsMargins(0, 0, 0, 0)
            _step_layout.setSpacing(9)
            _num_label = QLabel(_num)
            _num_label.setObjectName("workflowStepNum")
            _num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if _i == 0:
                _num_label.setProperty("flowActive", True)
            _text_box = QVBoxLayout()
            _text_box.setContentsMargins(0, 0, 0, 0)
            _text_box.setSpacing(0)
            _t = QLabel(_title)
            _t.setObjectName("workflowStepTitle")
            _s = QLabel(_sub)
            _s.setObjectName("workflowStepSub")
            _text_box.addWidget(_t)
            _text_box.addWidget(_s)
            _step_layout.addWidget(_num_label)
            _step_layout.addLayout(_text_box)
            self.workflow_step_labels.append(_step_widget)  # 保留 list（外部按长度引用）
            workflow_layout.addWidget(_step_widget)
            if _i < len(_FLOW_STEPS) - 1:
                _arrow = QLabel("›")
                _arrow.setObjectName("workflowArrow")
                _arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                workflow_layout.addWidget(_arrow)
        workflow_layout.addStretch()
        idle_flow_layout.addLayout(workflow_layout, stretch=1)
        # flow 面板延后到“四大功能”之后再加入 idle_card_layout（见下方），此处暂不 add

        idle_section_panel = QFrame()
        idle_section_panel.setObjectName("idleSectionPanel")
        idle_section_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        idle_section_layout = QVBoxLayout(idle_section_panel)
        idle_section_layout.setContentsMargins(0, 0, 0, 0)
        idle_section_layout.setSpacing(10)
        self.idle_section_panel = idle_section_panel
        self.idle_section_layout = idle_section_layout

        idle_section_header_layout = QHBoxLayout()
        idle_section_header_layout.setContentsMargins(0, 0, 0, 0)
        idle_section_header_layout.setSpacing(8)
        self.idle_section_header_layout = idle_section_header_layout

        self.lbl_idle_section = QLabel("四大功能")
        self.lbl_idle_section.setObjectName("idleSectionLabel")
        self.lbl_idle_section_hint = QLabel("按文件类型自动进入")
        self.lbl_idle_section_hint.setObjectName("idleSectionHint")
        idle_section_header_layout.addWidget(self.lbl_idle_section)
        idle_section_header_layout.addStretch()
        idle_section_header_layout.addWidget(self.lbl_idle_section_hint)
        idle_section_layout.addLayout(idle_section_header_layout)

        route_specs = [
            ("PDF 脱敏", "单文档", "打开 PDF，智能脱敏或手动画框。", "pdf"),
            ("Word 替换", "单文档", "打开 Word，替换并对比预览。", "word"),
            ("批量 Word", "批量处理", "导入多份 Word，确认规则后批量执行。", "batch"),
            ("图片合并 PDF", "图片工具", "导入图片，排序后生成 PDF。", "image"),
        ]

        idle_routes_container = QWidget()
        idle_routes_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        idle_routes_layout = QGridLayout(idle_routes_container)
        idle_routes_layout.setContentsMargins(0, 0, 0, 0)
        idle_routes_layout.setHorizontalSpacing(16)
        idle_routes_layout.setVerticalSpacing(16)
        idle_routes_layout.setColumnStretch(0, 1)
        idle_routes_layout.setColumnStretch(1, 1)
        self.idle_routes_container = idle_routes_container
        self.idle_routes_layout = idle_routes_layout
        self.idle_route_cards = []
        for index, (title_text, meta_text, desc_text, accent_key) in enumerate(route_specs):
            route_card = QFrame()
            route_card.setObjectName("routeCard")
            route_card.setProperty("routeTone", accent_key)
            route_card.setMinimumHeight(84)
            route_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self.idle_route_cards.append(route_card)
            route_card_layout = QVBoxLayout(route_card)
            route_card_layout.setContentsMargins(16, 14, 16, 14)
            route_card_layout.setSpacing(8)
            route_head_layout = QHBoxLayout()
            route_head_layout.setContentsMargins(0, 0, 0, 0)
            route_head_layout.setSpacing(10)
            # 彩色图标容器（按类型着色，字母标识跨平台稳定）
            _route_icon_text = {"pdf": "PDF", "word": "W", "batch": "批", "image": "图"}.get(accent_key, "·")
            route_icon = QLabel(_route_icon_text)
            route_icon.setObjectName("routeCardIcon")
            route_icon.setProperty("routeTone", accent_key)
            route_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            route_title = QLabel(title_text)
            route_title.setObjectName("routeCardTitle")
            route_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
            route_title.setContentsMargins(0, 6, 0, 0)
            route_title.setIndent(-6)
            route_meta = QLabel(meta_text)
            route_meta.setObjectName("routeCardMeta")
            route_meta.setProperty("routeTone", accent_key)
            route_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
            route_desc = QLabel(desc_text)
            route_desc.setObjectName("routeCardText")
            route_desc.setWordWrap(True)
            route_desc.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            _title_box = QVBoxLayout()
            _title_box.setContentsMargins(0, 0, 0, 0)
            _title_box.setSpacing(0)
            _title_box.addWidget(route_title)
            _title_box.addStretch(1)
            _title_box.addWidget(route_desc)
            route_head_layout.addWidget(route_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
            route_head_layout.addLayout(_title_box, stretch=1)
            route_head_layout.addWidget(route_meta, alignment=Qt.AlignmentFlag.AlignVCenter)
            route_card_layout.addStretch(1)
            route_card_layout.addLayout(route_head_layout)
            route_card_layout.addStretch(1)
            idle_routes_layout.addWidget(route_card, index // 2, index % 2)
        idle_section_layout.addWidget(idle_routes_container, 0)
        idle_card_layout.addWidget(idle_flow_panel)
        # 四大功能置于推荐流程之后（按用户反馈调换：四大功能下移到最下方功能区）
        idle_card_layout.addWidget(idle_section_panel)
        idle_card_layout.addWidget(self.idle_support_card)

        idle_card_row_layout = QHBoxLayout()
        idle_card_row_layout.setContentsMargins(0, 0, 0, 0)
        idle_card_row_layout.setSpacing(0)
        idle_card_row_layout.addWidget(idle_card)
        self.idle_card_row_layout = idle_card_row_layout
        idle_outer_layout.addLayout(idle_card_row_layout, 1)

        self.batch_workspace_container = QWidget()
        batch_outer_layout = QVBoxLayout(self.batch_workspace_container)
        batch_outer_layout.setContentsMargins(26, 24, 26, 28)
        batch_outer_layout.setSpacing(0)
        self.batch_outer_layout = batch_outer_layout

        batch_card = QFrame()
        batch_card.setObjectName("batchWorkspaceCard")
        batch_card.setMaximumWidth(1500)
        batch_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.batch_card = batch_card
        batch_card_layout = QVBoxLayout(batch_card)
        batch_card_layout.setContentsMargins(28, 24, 28, 24)
        batch_card_layout.setSpacing(14)
        self.batch_card_layout = batch_card_layout

        batch_header_layout = QHBoxLayout()
        batch_header_layout.setSpacing(12)
        self.batch_header_layout = batch_header_layout
        batch_header_text = QVBoxLayout()
        batch_header_text.setSpacing(4)
        self.batch_header_text_layout = batch_header_text
        self.lbl_batch_title = QLabel("批量 Word 工作台")
        self.lbl_batch_title.setObjectName("batchTitle")
        self.lbl_batch_subtitle = QLabel("先确认文档替换规则，再执行批量替换。处理中可以停止，已完成文件会保留。")
        self.lbl_batch_subtitle.setObjectName("batchSubtitle")
        self.lbl_batch_subtitle.setWordWrap(True)
        batch_header_text.addWidget(self.lbl_batch_title)
        batch_header_text.addWidget(self.lbl_batch_subtitle)
        self.lbl_batch_stage_badge = QLabel("等待开始")
        self.lbl_batch_stage_badge.setObjectName("batchStageBadge")
        batch_header_layout.addLayout(batch_header_text, stretch=1)
        batch_header_layout.addWidget(self.lbl_batch_stage_badge, alignment=Qt.AlignmentFlag.AlignTop)
        batch_card_layout.addLayout(batch_header_layout)

        self.lbl_batch_meta = QLabel("批量模式会优先进入规则确认，再进入执行。")
        self.lbl_batch_meta.setObjectName("batchMeta")
        self.lbl_batch_meta.setWordWrap(True)
        batch_card_layout.addWidget(self.lbl_batch_meta)

        batch_stage_layout = QGridLayout()
        batch_stage_layout.setContentsMargins(0, 0, 0, 0)
        batch_stage_layout.setHorizontalSpacing(12)
        batch_stage_layout.setVerticalSpacing(12)
        self.batch_stage_layout = batch_stage_layout
        self.batch_stage_cards = []
        for title_text, note_text in [
            ("1 规则确认", "先核对文档数量、统一替换文本和 Word 规则。"),
            ("2 执行替换", "系统逐个处理文档，支持跳过异常文件。"),
            ("3 查看结果", "处理结束后集中查看成功、失败和输出结果。"),
        ]:
            step_card = QFrame()
            step_card.setObjectName("batchStepCard")
            step_layout = QVBoxLayout(step_card)
            step_layout.setContentsMargins(14, 12, 14, 12)
            step_layout.setSpacing(4)
            step_title = QLabel(title_text)
            step_title.setObjectName("batchStepTitle")
            step_note = QLabel(note_text)
            step_note.setObjectName("batchStepNote")
            step_note.setWordWrap(True)
            step_layout.addWidget(step_title)
            step_layout.addWidget(step_note)
            self.batch_stage_cards.append((step_card, step_title, step_note))
        self._rebuild_batch_stage_layout("wide")
        batch_card_layout.addLayout(batch_stage_layout)

        batch_metrics_layout = QGridLayout()
        batch_metrics_layout.setContentsMargins(0, 0, 0, 0)
        batch_metrics_layout.setHorizontalSpacing(10)
        batch_metrics_layout.setVerticalSpacing(10)
        self.batch_metrics_layout = batch_metrics_layout
        self.batch_metric_cards = []
        self.lbl_batch_metric_files = None
        self.lbl_batch_metric_files_note = None
        self.lbl_batch_metric_rules = None
        self.lbl_batch_metric_rules_note = None
        self.lbl_batch_metric_progress = None
        self.lbl_batch_metric_progress_note = None
        self.lbl_batch_metric_result = None
        self.lbl_batch_metric_result_note = None
        for key, title_text in [
            ("files", "已选文档"),
            ("rules", "启用规则"),
            ("progress", "当前进度"),
            ("result", "执行结果"),
        ]:
            metric_card, metric_value, metric_note = self._create_batch_metric_card(title_text)
            setattr(self, f"lbl_batch_metric_{key}", metric_value)
            setattr(self, f"lbl_batch_metric_{key}_note", metric_note)
            self.batch_metric_cards.append(metric_card)
        self._rebuild_batch_metrics_layout("wide")
        batch_card_layout.addLayout(batch_metrics_layout)

        batch_actions_layout = QGridLayout()
        batch_actions_layout.setContentsMargins(0, 2, 0, 0)
        batch_actions_layout.setHorizontalSpacing(10)
        batch_actions_layout.setVerticalSpacing(10)
        self.batch_actions_layout = batch_actions_layout
        self.btn_batch_edit_rules = self.create_btn("重新设置规则", self._reopen_batch_rule_setup, style="secondary")
        self.btn_batch_pick_files = self.create_btn("重新选择文档", self._start_batch_replace_from_workspace, style="secondary")
        self.btn_batch_retry_failed = self.create_btn("仅重试失败文档", self._retry_failed_batch_files, style="secondary")
        self.btn_batch_open_output = self.create_btn("打开输出位置", self._open_batch_output_location, style="secondary")
        self.batch_action_buttons = [
            self.btn_batch_edit_rules,
            self.btn_batch_pick_files,
            self.btn_batch_retry_failed,
            self.btn_batch_open_output,
        ]
        self._rebuild_batch_action_layout("wide")
        batch_card_layout.addLayout(batch_actions_layout)

        self.lbl_batch_current_file = QLabel("当前文件：尚未开始")
        self.lbl_batch_current_file.setObjectName("batchCurrentFile")
        self.lbl_batch_current_file.setWordWrap(True)
        batch_card_layout.addWidget(self.lbl_batch_current_file)

        batch_detail_layout = QGridLayout()
        batch_detail_layout.setContentsMargins(0, 0, 0, 0)
        batch_detail_layout.setHorizontalSpacing(14)
        batch_detail_layout.setVerticalSpacing(14)
        self.batch_detail_layout = batch_detail_layout

        self.batch_summary_section = QFrame()
        self.batch_summary_section.setObjectName("batchDetailSection")
        self.batch_summary_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        batch_summary_section_layout = QVBoxLayout(self.batch_summary_section)
        batch_summary_section_layout.setContentsMargins(0, 0, 0, 0)
        batch_summary_section_layout.setSpacing(8)
        self.batch_summary_section_layout = batch_summary_section_layout
        self.lbl_batch_summary_hint = QLabel("本轮摘要")
        self.lbl_batch_summary_hint.setObjectName("batchSectionLabel")
        batch_summary_section_layout.addWidget(self.lbl_batch_summary_hint)

        self.batch_summary_browser = QTextBrowser()
        self.batch_summary_browser.setObjectName("batchSummaryBrowser")
        self.batch_summary_browser.setOpenExternalLinks(False)
        self.batch_summary_browser.setMinimumHeight(148)
        self.batch_summary_browser.setMaximumHeight(220)
        self.batch_summary_browser.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        batch_summary_section_layout.addWidget(self.batch_summary_browser)

        self.batch_result_section = QFrame()
        self.batch_result_section.setObjectName("batchDetailSection")
        self.batch_result_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        batch_result_section_layout = QVBoxLayout(self.batch_result_section)
        batch_result_section_layout.setContentsMargins(0, 0, 0, 0)
        batch_result_section_layout.setSpacing(8)
        self.batch_result_section_layout = batch_result_section_layout
        self.lbl_batch_result_hint = QLabel("结果清单")
        self.lbl_batch_result_hint.setObjectName("batchSectionLabel")

        batch_result_toolbar = QHBoxLayout()
        batch_result_toolbar.setSpacing(8)
        batch_result_toolbar.setContentsMargins(0, 0, 0, 0)
        batch_result_toolbar.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.batch_result_toolbar = batch_result_toolbar
        self.lbl_batch_result_meta = QLabel("结果计数：等待本轮结果")
        self.lbl_batch_result_meta.setObjectName("batchResultMeta")
        self.lbl_batch_result_meta.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        batch_result_toolbar.addWidget(self.lbl_batch_result_meta, stretch=1)
        self.btn_batch_filter_all = QPushButton("全部")
        self.btn_batch_filter_success = QPushButton("仅成功")
        self.btn_batch_filter_failed = QPushButton("仅失败")
        for filter_mode, button in [
            ("all", self.btn_batch_filter_all),
            ("success", self.btn_batch_filter_success),
            ("failed", self.btn_batch_filter_failed),
        ]:
            button.setObjectName("batchFilterButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAutoDefault(False)
            button.setDefault(False)
            button.clicked.connect(lambda _checked=False, mode=filter_mode: self._set_batch_result_filter_mode(mode))
            batch_result_toolbar.addWidget(button)
        batch_result_header_layout = QHBoxLayout()
        batch_result_header_layout.setContentsMargins(0, 0, 0, 0)
        batch_result_header_layout.setSpacing(12)
        batch_result_header_layout.addWidget(self.lbl_batch_result_hint, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)
        batch_result_header_layout.addLayout(batch_result_toolbar, stretch=2)
        self.batch_result_header_layout = batch_result_header_layout
        batch_result_section_layout.addLayout(batch_result_header_layout)

        self.batch_result_table = QTableWidget(0, 4)
        self.batch_result_table.setObjectName("batchResultTable")
        self.batch_result_table.setHorizontalHeaderLabels(["状态", "输入文档", "结果说明", "操作"])
        self.batch_result_table.verticalHeader().setVisible(False)
        self.batch_result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.batch_result_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.batch_result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.batch_result_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.batch_result_table.setAlternatingRowColors(False)
        self.batch_result_table.setShowGrid(False)
        self.batch_result_table.setWordWrap(True)
        self.batch_result_table.setMinimumHeight(196)
        self.batch_result_table.setMaximumHeight(280)
        batch_header = self.batch_result_table.horizontalHeader()
        batch_header.setHighlightSections(False)
        batch_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        batch_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        batch_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        batch_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        if self.batch_result_table.horizontalHeaderItem(0):
            self.batch_result_table.horizontalHeaderItem(0).setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
        if self.batch_result_table.horizontalHeaderItem(3):
            self.batch_result_table.horizontalHeaderItem(3).setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
        self.batch_result_table.cellDoubleClicked.connect(self._open_batch_result_row)
        batch_result_section_layout.addWidget(self.batch_result_table)

        self.batch_log_section = QFrame()
        self.batch_log_section.setObjectName("batchDetailSection")
        self.batch_log_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        batch_log_section_layout = QVBoxLayout(self.batch_log_section)
        batch_log_section_layout.setContentsMargins(0, 0, 0, 0)
        batch_log_section_layout.setSpacing(8)
        self.batch_log_section_layout = batch_log_section_layout
        self.lbl_batch_log_hint = QLabel("处理动态")
        self.lbl_batch_log_hint.setObjectName("batchSectionLabel")
        batch_log_section_layout.addWidget(self.lbl_batch_log_hint)

        self.batch_log_list = QListWidget()
        self.batch_log_list.setObjectName("batchLogList")
        self.batch_log_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.batch_log_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.batch_log_list.setAlternatingRowColors(False)
        self.batch_log_list.setMinimumHeight(260)
        batch_log_section_layout.addWidget(self.batch_log_list)

        self._rebuild_batch_detail_layout("wide")
        batch_card_layout.addLayout(batch_detail_layout, stretch=1)

        batch_card_row_layout = QHBoxLayout()
        batch_card_row_layout.setContentsMargins(0, 0, 0, 0)
        batch_card_row_layout.setSpacing(0)
        batch_card_row_layout.addStretch(1)
        batch_card_row_layout.addWidget(batch_card, 10)
        batch_card_row_layout.addStretch(1)
        self.batch_card_row_layout = batch_card_row_layout
        batch_outer_layout.addLayout(batch_card_row_layout)
        batch_outer_layout.addStretch(1)

        self.merge_workspace_container = QWidget()
        merge_outer_layout = QVBoxLayout(self.merge_workspace_container)
        merge_outer_layout.setContentsMargins(26, 24, 26, 28)
        merge_outer_layout.setSpacing(0)
        self.merge_outer_layout = merge_outer_layout

        merge_card = QFrame()
        merge_card.setObjectName("mergeWorkspaceCard")
        merge_card.setMaximumWidth(1500)
        merge_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.merge_card = merge_card
        merge_card_layout = QVBoxLayout(merge_card)
        merge_card_layout.setContentsMargins(28, 24, 28, 24)
        merge_card_layout.setSpacing(14)
        self.merge_card_layout = merge_card_layout
        merge_header_layout = QHBoxLayout()
        merge_header_layout.setSpacing(12)
        self.merge_header_layout = merge_header_layout
        merge_header_text = QVBoxLayout()
        merge_header_text.setSpacing(4)
        self.merge_header_text_layout = merge_header_text
        self.lbl_merge_title = QLabel("图片正在合并为 PDF")
        self.lbl_merge_title.setObjectName("workspaceTitle")
        self.lbl_merge_subtitle = QLabel("系统会先按当前顺序生成 PDF，完成后自动进入 PDF 脱敏工作台。")
        self.lbl_merge_subtitle.setObjectName("workspaceSubtitle")
        self.lbl_merge_subtitle.setWordWrap(True)
        merge_header_text.addWidget(self.lbl_merge_title)
        merge_header_text.addWidget(self.lbl_merge_subtitle)
        self.lbl_merge_stage_badge = QLabel("等待开始")
        self.lbl_merge_stage_badge.setObjectName("batchStageBadge")
        merge_header_layout.addLayout(merge_header_text, stretch=1)
        merge_header_layout.addWidget(self.lbl_merge_stage_badge, alignment=Qt.AlignmentFlag.AlignTop)
        self.lbl_merge_meta = QLabel("当前还没有开始合并。")
        self.lbl_merge_meta.setObjectName("workspaceHint")
        self.lbl_merge_meta.setWordWrap(True)
        merge_card_layout.addLayout(merge_header_layout)
        merge_card_layout.addWidget(self.lbl_merge_meta)

        merge_stage_layout = QGridLayout()
        merge_stage_layout.setContentsMargins(0, 0, 0, 0)
        merge_stage_layout.setHorizontalSpacing(12)
        merge_stage_layout.setVerticalSpacing(12)
        self.merge_stage_layout = merge_stage_layout
        self.merge_stage_cards = []
        for title_text, note_text in [
            ("1 整理顺序", "按当前拖入顺序准备图片，确认后开始生成 PDF。"),
            ("2 合并 PDF", "系统将图片依次写入 PDF，并同步显示当前进度。"),
            ("3 进入工作台", "合并完成后自动打开生成的 PDF，继续进入脱敏工作台。"),
        ]:
            step_card = QFrame()
            step_card.setObjectName("batchStepCard")
            step_layout = QVBoxLayout(step_card)
            step_layout.setContentsMargins(14, 12, 14, 12)
            step_layout.setSpacing(4)
            step_title = QLabel(title_text)
            step_title.setObjectName("batchStepTitle")
            step_note = QLabel(note_text)
            step_note.setObjectName("batchStepNote")
            step_note.setWordWrap(True)
            step_layout.addWidget(step_title)
            step_layout.addWidget(step_note)
            self.merge_stage_cards.append((step_card, step_title, step_note))
        self._rebuild_merge_stage_layout("wide")
        merge_card_layout.addLayout(merge_stage_layout)

        merge_metrics_layout = QGridLayout()
        merge_metrics_layout.setContentsMargins(0, 0, 0, 0)
        merge_metrics_layout.setHorizontalSpacing(10)
        merge_metrics_layout.setVerticalSpacing(10)
        self.merge_metrics_layout = merge_metrics_layout
        self.merge_metric_cards = []
        self.lbl_merge_metric_images = None
        self.lbl_merge_metric_images_note = None
        self.lbl_merge_metric_status = None
        self.lbl_merge_metric_status_note = None
        self.lbl_merge_metric_next = None
        self.lbl_merge_metric_next_note = None
        for key, title_text in [
            ("images", "待合并图片"),
            ("status", "当前状态"),
            ("next", "后续动作"),
        ]:
            metric_card, metric_value, metric_note = self._create_batch_metric_card(title_text)
            setattr(self, f"lbl_merge_metric_{key}", metric_value)
            setattr(self, f"lbl_merge_metric_{key}_note", metric_note)
            self.merge_metric_cards.append(metric_card)
        self._rebuild_merge_metrics_layout("wide")
        merge_card_layout.addLayout(merge_metrics_layout)
        merge_card_row_layout = QHBoxLayout()
        merge_card_row_layout.setContentsMargins(0, 0, 0, 0)
        merge_card_row_layout.setSpacing(0)
        merge_card_row_layout.addStretch(1)
        merge_card_row_layout.addWidget(merge_card, 10)
        merge_card_row_layout.addStretch(1)
        self.merge_card_row_layout = merge_card_row_layout
        merge_outer_layout.addLayout(merge_card_row_layout)
        merge_outer_layout.addStretch(1)

        self.word_compare_container = QWidget()
        word_compare_outer_layout = QVBoxLayout(self.word_compare_container)
        word_compare_outer_layout.setContentsMargins(14, 10, 14, 16)
        word_compare_outer_layout.setSpacing(0)
        self.word_compare_outer_layout = word_compare_outer_layout

        self.word_workspace_shell = QFrame()
        self.word_workspace_shell.setObjectName("previewWorkspaceCard")
        self.word_workspace_shell.setMaximumWidth(1940)
        self.word_workspace_shell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        word_workspace_shell_layout = QVBoxLayout(self.word_workspace_shell)
        word_workspace_shell_layout.setContentsMargins(8, 8, 8, 8)
        word_workspace_shell_layout.setSpacing(6)
        self.word_workspace_shell_layout = word_workspace_shell_layout

        self.word_compare_header = QFrame()
        self.word_compare_header.setObjectName("wordCompareHeader")
        self.word_compare_header.setFixedHeight(28)
        word_header_layout = QHBoxLayout(self.word_compare_header)
        word_header_layout.setContentsMargins(0, 0, 0, 0)
        word_header_layout.setSpacing(12)
        self.word_header_layout = word_header_layout

        self.lbl_word_original_header = QLabel("原文预览")
        self.lbl_word_original_header.setObjectName("wordCompareLabel")
        self.lbl_word_original_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_header_divider = QFrame()
        self.word_header_divider.setFrameShape(QFrame.Shape.NoFrame)
        self.word_header_divider.setFixedWidth(12)
        self.lbl_word_replaced_header = QLabel("替换后预览")
        self.lbl_word_replaced_header.setObjectName("wordCompareLabel")
        self.lbl_word_replaced_header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        word_header_layout.addWidget(self.lbl_word_original_header, stretch=1)
        word_header_layout.addWidget(self.word_header_divider)
        word_header_layout.addWidget(self.lbl_word_replaced_header, stretch=1)
        word_workspace_shell_layout.addWidget(self.word_compare_header)

        self.word_compare_content = QWidget()
        self.word_compare_content.setObjectName("previewStage")
        word_compare_layout = QHBoxLayout(self.word_compare_content)
        word_compare_layout.setContentsMargins(0, 0, 0, 0)
        word_compare_layout.setSpacing(8)
        self.word_compare_layout = word_compare_layout

        self.word_preview_original_panel = QWidget()
        self.word_preview_original_panel.setObjectName("wordPreviewShell")
        self.word_preview_original_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        original_panel_layout = QVBoxLayout(self.word_preview_original_panel)
        original_panel_layout.setContentsMargins(1, 1, 1, 1)
        original_panel_layout.setSpacing(0)
        self.original_panel_layout = original_panel_layout
        original_panel_layout.addWidget(self.word_preview)

        self.word_preview_replaced_panel = QWidget()
        self.word_preview_replaced_panel.setObjectName("wordPreviewShell")
        self.word_preview_replaced_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        replaced_panel_layout = QVBoxLayout(self.word_preview_replaced_panel)
        replaced_panel_layout.setContentsMargins(1, 1, 1, 1)
        replaced_panel_layout.setSpacing(0)
        self.replaced_panel_layout = replaced_panel_layout
        replaced_panel_layout.addWidget(self.word_preview_replaced)

        word_compare_layout.addWidget(self.word_preview_original_panel, stretch=1)
        word_compare_layout.addWidget(self.word_preview_replaced_panel, stretch=1)
        word_workspace_shell_layout.addWidget(self.word_compare_content, stretch=1)
        word_workspace_row_layout = QHBoxLayout()
        word_workspace_row_layout.setContentsMargins(0, 0, 0, 0)
        word_workspace_row_layout.setSpacing(0)
        word_workspace_row_layout.addStretch(1)
        word_workspace_row_layout.addWidget(self.word_workspace_shell, 18)
        word_workspace_row_layout.addStretch(1)
        self.word_workspace_row_layout = word_workspace_row_layout
        word_compare_outer_layout.addLayout(word_workspace_row_layout, 1)

        # 创建主容器，包含 canvas_container 和 word_compare_container
        self.main_container = QWidget()
        # cp77: 命名并显式上 scroll_area 底色（接替此前无选择器样式的传播供色），
        # 卡外/画布周围底色不变，而卡片内裸 QWidget 恢复透出卡片自身颜色
        self.main_container.setObjectName("mainContainer")
        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.idle_workspace_container)
        self.main_layout.addWidget(self.batch_workspace_container)
        self.main_layout.addWidget(self.merge_workspace_container)
        self.main_layout.addWidget(self.canvas_container)
        self.main_layout.addWidget(self.word_compare_container)

        # 默认隐藏 Word 预览容器
        self.batch_workspace_container.hide()
        self.merge_workspace_container.hide()
        self.word_compare_container.hide()
        self.word_preview_replaced_panel.hide()
        self.word_preview.hide()
        self.word_preview_replaced.hide()

        # 设置 container 为固定的 widget
        self.scroll.setWidget(self.main_container)
        # v40.1.5（用户反馈）：应用级事件过滤器——macOS 触控板双指捏合缩放。
        # NativeGesture 的派发目标随焦点漂移（QLabel 画布无焦点收不到），
        # qApp 级拦截保证无论发给谁都能收到。
        QApplication.instance().installEventFilter(self)
        # 默认单页模式：隐藏右页
        self.canvas_right.hide()

        # cp81: 中央内容水平行：[书签面板 | 单页 scroll | 页面视图容器 | 右侧搜索面板]
        # cp_bookmark: 左侧书签面板（默认隐藏，工具栏书签按钮切换）
        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)
        self.bookmark_panel = self._build_bookmark_panel()
        content_row.addWidget(self.bookmark_panel, 0)
        content_row.addWidget(self.scroll, 1)

        # cp67: 页面视图容器（左侧页面操作工具栏 + 多页网格滚动区），与 self.scroll 互斥显示
        self.page_view_container = self._build_page_view_container()
        self.page_view_container.hide()
        content_row.addWidget(self.page_view_container, 1)

        # cp81: 右侧搜索面板（默认隐藏，工具栏放大镜按钮切换）
        self.search_panel = self._build_search_panel()
        self.search_panel.hide()
        content_row.addWidget(self.search_panel, 0)

        # v40.1.5：持久 PDF 显示区——content_row（单页 scroll / 页面视图容器互斥切换
        # 都在其内）与底部控制条同层；scroll.hide() 不再连坐隐藏底条
        pdf_area_holder = QWidget()
        _pdf_area_layout = QVBoxLayout(pdf_area_holder)
        _pdf_area_layout.setContentsMargins(0, 0, 0, 0)
        _pdf_area_layout.setSpacing(0)
        _pdf_area_layout.addLayout(content_row, 1)
        _pdf_area_layout.addWidget(self.doc_bottom_bar)
        self.pdf_area_holder = pdf_area_holder
        layout.addWidget(pdf_area_holder, 1)

        # 进度条和取消按钮区域（v36.3: 添加取消按钮）
        self.progress_shell = QWidget()
        progress_layout = QHBoxLayout(self.progress_shell)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(24)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        progress_layout.addWidget(self.progress, stretch=1)

        # 取消扫描按钮（初始隐藏）
        self.btn_cancel_scan = QPushButton("取消")
        self.btn_cancel_scan.setFixedSize(60, 24)
        # cp66: 专用紧凑样式，避免通用按钮 padding 在 24px 固定高度内裁切文字
        self.btn_cancel_scan.setStyleSheet(self._get_cancel_scan_button_style(24))
        self.btn_cancel_scan.setToolTip("停止扫描并保留已扫描结果")
        self.btn_cancel_scan.clicked.connect(self.cancel_ocr_scan)
        self.btn_cancel_scan.setVisible(False)  # 初始隐藏
        progress_layout.addWidget(self.btn_cancel_scan)

        layout.addWidget(self.progress_shell)

        # 应用浅色主题样式
        self._apply_light_theme()
        self._sync_ui_mode()

    def _apply_light_theme(self):
        """应用浅色主题样式（v35.1: Windows 强制浅色主题）"""

        theme = Theme.LIGHT

        # 主窗口背景样式（确保整体色调统一）
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme["background"]};
                color: {theme["text"]};
                font-family: {Theme.FONT_FAMILY};
            }}
            QWidget#appRoot {{
                background-color: {theme["background"]};
                color: {theme["text"]};
                font-family: {Theme.FONT_FAMILY};
            }}
            QLabel {{
                background-color: transparent;
                color: {theme["text"]};
            }}
            QPushButton {{
                outline: none;
            }}
            QToolButton {{
                outline: none;
            }}
        """)

        # 统一上下文条
        if hasattr(self, "workbench_panel"):
            self.workbench_panel.setStyleSheet(
                f"""
                QFrame#workbenchPanel {{
                    background-color: {theme["surface"]};
                    border-bottom: 1px solid {theme["border"]};
                }}
                QLabel#workbenchTitle {{
                    color: {theme["text"]};
                    font-size: 16px;
                    font-weight: 700;
                    background-color: transparent;
                }}
                QLabel#workbenchSubtitle {{
                    color: {theme["text_secondary"]};
                    font-size: 11px;
                    line-height: 1.4;
                    background-color: transparent;
                }}
                QLabel#workbenchFocus {{
                    background-color: #E9F1FB;
                    color: {theme["primary"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 14px;
                    padding: 5px 12px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QLabel#workbenchHintTag {{
                    background-color: #FBFCFE;
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 10px;
                    padding: 7px 12px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QLabel#contextMessage {{
                    background-color: {theme["info_bar"]};
                    color: {theme["text_secondary"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 10px;
                    padding: 7px 12px;
                    font-weight: 600;
                    font-size: {Theme.FONT_SIZE_SMALL}px;
                }}
                """
            )

        # 工具栏
        self.toolbar.setStyleSheet(f"""
            QFrame#toolbarRoot {{
                background-color: {theme["surface"]};
                border-bottom: 1px solid {theme["border"]};
            }}
            QFrame#toolbarGroup, QFrame#toolbarGroupStrong, QFrame#toolbarUtilityGroup {{
                background-color: transparent;
                border: none;
            }}
            QFrame#toolbarUtilityGroup {{
                background-color: transparent;
                border: none;
            }}
            QFrame#toolbarDivider {{
                background-color: {theme["border"]};
                border: none;
                margin-top: 6px;
                margin-bottom: 6px;
            }}
        """)

        if hasattr(self, "lbl_mode_badge"):
            self.lbl_mode_badge.setStyleSheet(
                f"""
                QLabel#modeBadge {{
                    background-color: {theme["hover"]};
                    color: {theme["primary"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 14px;
                    padding: 6px 12px;
                    font-size: {Theme.FONT_SIZE_SMALL}px;
                    font-weight: 700;
                }}
                """
            )
        if hasattr(self, "main_container"):
            self.main_container.setStyleSheet(
                f"""
                QWidget#mainContainer {{
                    background-color: {theme["scroll_area"]};
                }}
                QFrame#workspaceCard {{
                    background-color: {theme["surface"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 18px;
                }}
                QFrame#batchWorkspaceCard, QFrame#mergeWorkspaceCard {{
                    background-color: {theme["surface"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 18px;
                }}
                QFrame#batchDetailSection {{
                    background-color: #FBFCFE;
                    border: 1px solid {theme["border"]};
                    border-radius: 16px;
                }}
                QFrame#previewWorkspaceCard {{
                    background-color: #FBFCFE;
                    border: none;
                    border-radius: 18px;
                }}
                QWidget#previewStage {{
                    background-color: transparent;
                    border: none;
                }}
                QWidget#wordPreviewShell {{
                    background-color: #FFFFFF;
                    border: 1px solid {theme["border"]};
                    border-radius: 15px;
                }}
                QLabel#pdfPageCanvas {{
                    background-color: transparent;
                    border: none;
                    border-radius: 0px;
                }}
                QLabel#workspaceTitle, QLabel#batchTitle {{
                    color: {theme["text"]};
                    font-size: 20px;
                    font-weight: 700;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#workspaceSubtitle, QLabel#batchSubtitle {{
                    color: {theme["text_secondary"]};
                    font-size: 12px;
                    line-height: 1.7;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#workspaceLead {{
                    color: {theme["text_secondary"]};
                    font-size: 12px;
                    font-weight: 600;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#workspaceHint, QLabel#batchMeta, QLabel#batchCurrentFile {{
                    color: {theme["text"]};
                    font-size: 12px;
                    line-height: 1.7;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleSectionLabel {{
                    color: {theme["text"]};
                    font-size: 13px;
                    font-weight: 700;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleSectionHint {{
                    color: {theme["text_secondary"]};
                    font-size: 11px;
                    font-weight: 600;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleHeroBadge {{
                    color: {theme["primary"]};
                    background-color: #E9F1FB;
                    border: 1px solid {theme["border"]};
                    border-radius: 9px;
                    padding: 4px 9px;
                    font-size: 10px;
                    font-weight: 700;
                }}
                QLabel#routeCardIcon {{
                    color: #FFFFFF;
                    border-radius: 9px;
                    min-width: 40px; max-width: 40px;
                    min-height: 40px; max-height: 40px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QLabel#routeCardIcon[routeTone="pdf"] {{ background-color: #D64545; }}
                QLabel#routeCardIcon[routeTone="word"] {{ background-color: #2563EB; }}
                QLabel#routeCardIcon[routeTone="batch"] {{ background-color: #B54708; }}
                QLabel#routeCardIcon[routeTone="image"] {{ background-color: #15803D; }}
                QLabel#workflowStepNum {{
                    color: #667085;
                    background-color: #EFF2F6;
                    border: 1px solid #E4E7EC;
                    border-radius: 14px;
                    min-width: 28px; max-width: 28px;
                    min-height: 28px; max-height: 28px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QLabel#workflowStepNum[flowActive="true"] {{
                    color: #FFFFFF;
                    background-color: {theme["primary"]};
                    border: 1px solid {theme["primary"]};
                }}
                QLabel#workflowStepTitle {{
                    color: {theme["text"]};
                    font-size: 12px;
                    font-weight: 600;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#workflowStepSub {{
                    color: #667085;
                    font-size: 10.5px;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#workflowArrow {{
                    color: #CBD5E1;
                    font-size: 22px;
                    font-weight: 700;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QFrame#idleHeroPanel {{
                    background-color: transparent;
                    border: none;
                }}
                QFrame#idleSectionPanel {{
                    background-color: transparent;
                    border: none;
                }}
                QFrame#idleFlowPanel {{
                    background-color: transparent;
                    border: none;
                }}
                QLabel#idleFlowTitle {{
                    color: {theme["text_secondary"]};
                    font-size: 11px;
                    font-weight: 700;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QFrame#idleActionPanel {{
                    background-color: transparent;
                    border: none;
                }}
                QFrame#idleSupportCard {{
                    background-color: #F9FBFE;
                    border: 1px solid {theme["border"]};
                    border-radius: 14px;
                }}
                QFrame#idleStartCard {{
                    background-color: #EFF4FE;
                    border: 2px solid {theme["primary"]};
                    border-radius: 14px;
                }}
                QLabel#idleStartIcon {{
                    color: #FFFFFF;
                    background-color: {theme["primary"]};
                    border-radius: 28px;
                    min-width: 56px; max-width: 56px;
                    min-height: 56px; max-height: 56px;
                    font-size: 28px;
                    font-weight: 700;
                }}
                QLabel#idleStartTitle {{
                    color: {theme["text"]};
                    font-size: 16px;
                    font-weight: 700;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleStartText {{
                    color: {theme["text_secondary"]};
                    font-size: 11px;
                    line-height: 1.6;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleDropHint {{
                    color: {theme["text_secondary"]};
                    font-size: 11px;
                    font-weight: 600;
                    line-height: 1.6;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleSupportTitle {{
                    color: {theme["text"]};
                    font-size: 13px;
                    font-weight: 700;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleSupportText {{
                    color: {theme["text"]};
                    font-size: 12px;
                    font-weight: 600;
                    line-height: 1.5;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleSupportMeta {{
                    color: {theme["text_secondary"]};
                    font-size: 11px;
                    font-weight: 600;
                    line-height: 1.5;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleSupportEmail {{
                    color: {theme["primary"]};
                    font-size: 11px;
                    font-weight: 600;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleSupportNote {{
                    color: {theme["text_secondary"]};
                    font-size: 11px;
                    line-height: 1.6;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleSupportQr {{
                    background-color: #F9FBFE;
                    border: none;
                    padding: 0;
                }}
                QLabel#idleSupportQrCaption {{
                    color: {theme["text_secondary"]};
                    font-size: 10px;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QFrame#batchStepCard, QFrame#batchMetricCard {{
                    background-color: #FCFDFF;
                    border: 1px solid {theme["border"]};
                    border-radius: 15px;
                }}
                QLabel#batchStepTitle {{
                    color: {theme["text"]};
                    font-size: 12px;
                    font-weight: 700;
                    background-color: transparent;
                }}
                QLabel#batchStepNote, QLabel#batchMetricNote {{
                    color: {theme["text_secondary"]};
                    font-size: 11px;
                    line-height: 1.6;
                    background-color: transparent;
                }}
                QLabel#batchMetricTitle {{
                    color: {theme["text_secondary"]};
                    font-size: 11px;
                    font-weight: 700;
                    background-color: transparent;
                }}
                QLabel#batchMetricValue {{
                    color: {theme["text"]};
                    font-size: 18px;
                    font-weight: 700;
                    background-color: transparent;
                }}
                QFrame#routeCard {{
                    background-color: #FCFDFF;
                    border: 1px solid {theme["border"]};
                    border-radius: 16px;
                }}
                QFrame#routeCard[routeTone="pdf"] {{
                    background-color: #F7FBFF;
                    border-color: #D7E8F8;
                }}
                QFrame#routeCard[routeTone="word"] {{
                    background-color: #F6FBF8;
                    border-color: #D9EEE3;
                }}
                QFrame#routeCard[routeTone="batch"] {{
                    background-color: #FFF9F2;
                    border-color: #F1E1C7;
                }}
                QFrame#routeCard[routeTone="image"] {{
                    background-color: #F8FAFC;
                    border-color: #E0E7EF;
                }}
                QLabel#routeCardTitle {{
                    color: {theme["text"]};
                    font-size: 13px;
                    font-weight: 700;
                    background-color: transparent;
                    border: none;
                }}
                QLabel#routeCardMeta {{
                    color: {theme["text_secondary"]};
                    background-color: {theme["hover"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 9px;
                    padding: 3px 8px;
                    min-width: 56px;
                    font-size: 10px;
                    font-weight: 700;
                }}
                QLabel#routeCardMeta[routeTone="pdf"] {{
                    color: #1177CC;
                    background-color: #E9F3FD;
                    border-color: #D5E8FA;
                }}
                QLabel#routeCardMeta[routeTone="word"] {{
                    color: #1B9263;
                    background-color: #EAF6F0;
                    border-color: #D8EDE2;
                }}
                QLabel#routeCardMeta[routeTone="batch"] {{
                    color: #B56A1C;
                    background-color: #FFF2E3;
                    border-color: #F1DEC3;
                }}
                QLabel#routeCardMeta[routeTone="image"] {{
                    color: #5B6B7A;
                    background-color: #EEF3F8;
                    border-color: #DEE7F0;
                }}
                QLabel#routeCardText {{
                    color: {theme["text_secondary"]};
                    font-size: 10px;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
                QLabel#batchStageBadge {{
                    background-color: #FFF6EA;
                    color: {theme["warning"]};
                    border: 1px solid #F0DFC4;
                    border-radius: 14px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QLabel#batchLogHint, QLabel#batchSectionLabel {{
                    color: {theme["text_secondary"]};
                    font-size: 12px;
                    font-weight: 700;
                    background-color: transparent;
                }}
                QLabel#batchResultMeta {{
                    color: {theme["text_secondary"]};
                    font-size: 12px;
                    font-weight: 600;
                    background-color: transparent;
                }}
                QTableWidget#batchResultTable {{
                    background-color: #FFFFFF;
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 15px;
                    gridline-color: transparent;
                    padding: 6px;
                }}
                QTableWidget#batchResultTable::item {{
                    padding: 10px 12px;
                    border-bottom: 1px solid #E9EEF5;
                }}
                QTableWidget#batchResultTable QHeaderView::section {{
                    background-color: #F7FAFD;
                    color: {theme["text_secondary"]};
                    border: none;
                    border-bottom: 1px solid {theme["border"]};
                    padding: 8px 10px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QListWidget#batchLogList {{
                    background-color: #FFFFFF;
                    border: 1px solid {theme["border"]};
                    border-radius: 15px;
                    padding: 6px;
                    outline: none;
                }}
                QListWidget#batchLogList::item {{
                    padding: 10px 12px;
                    border-bottom: 1px solid #E9EEF5;
                    color: {theme["text"]};
                }}
                QListWidget#batchLogList::item:selected {{
                    background-color: transparent;
                    color: {theme["text"]};
                }}
                QTextBrowser#batchSummaryBrowser {{
                    background-color: #FFFFFF;
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 15px;
                    padding: 12px;
                    font-size: 12px;
                    line-height: 1.7;
                }}
                """
            )

        # 滚动区域
        self.scroll.setStyleSheet(self.scroll_style.format(theme["scroll_area"]))

        # Word 双栏预览头部（紧凑样式）
        if hasattr(self, "word_compare_header"):
            self.word_compare_header.setStyleSheet("""
                QFrame#wordCompareHeader {
                    background-color: transparent;
                    border: none;
                }
            """)
        if hasattr(self, "lbl_word_original_header"):
            self.lbl_word_original_header.setStyleSheet(
                f"""
                QLabel#wordCompareLabel {{
                    color: {theme['text_secondary']};
                    background-color: #F7FAFD;
                    border: 1px solid {theme["border"]};
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                """
            )
        if hasattr(self, "lbl_word_replaced_header"):
            self.lbl_word_replaced_header.setStyleSheet(
                f"""
                QLabel#wordCompareLabel {{
                    color: {theme['text_secondary']};
                    background-color: #F7FAFD;
                    border: 1px solid {theme["border"]};
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                """
            )
        if hasattr(self, "word_header_divider"):
            self.word_header_divider.setStyleSheet("background-color: transparent; border: none;")

        # 标签文本颜色
        text_color = theme["text"]
        toolbar_meta_style = f"""
            QLabel#toolbarMeta {{
                color: {text_color};
                background-color: {theme["hover"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 700;
                min-width: 54px;
            }}
        """
        self.lbl_zoom.setStyleSheet(toolbar_meta_style)
        self.lbl_page.setStyleSheet(toolbar_meta_style)

        for toggle_btn in [self.rb_black, self.rb_white, self.cb_page_view]:
            self._apply_button_variant(toggle_btn, "toggle")

        self._refresh_toolbar_more_button_style()

        # 进度条
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #E5E5EA;
                border: none;
                border-radius: 3px;
                color: #1D1D1F;
                font-weight: 600;
                font-size: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007AFF, stop:1 #34C759);
                border-radius: 3px;
            }
        """)
        self._refresh_mode_badge()
        self._refresh_word_compare_toggle()
        self._refresh_workbench_context()

    def _refresh_toolbar_more_button_style(self):
        """刷新更多按钮样式，保持响应式和隐藏菜单箭头逻辑一致。"""
        if not hasattr(self, "btn_more"):
            return
        self.btn_more.setStyleSheet(
            self._get_button_style("secondary") +
            """
            QPushButton#toolbarMoreButton {
                padding-right: 16px;
            }
            QPushButton#toolbarMoreButton::menu-indicator {
                image: none;
                width: 0px;
                height: 0px;
            }
            """
        )

    def _apply_native_toolbar_icons(self):
        """为导航按钮应用 Qt 原生图标，提升 Windows 下的一致性。"""
        if not hasattr(self, "btn_go_first"):
            return

        style = self.style()
        icon_map = [
            # v40.1.5：导航四按钮已迁底部迷你条（自带字符图标），不再套原生图标
        ]
        for button, standard_icon in icon_map:
            button.setIcon(style.standardIcon(standard_icon))
            button.setText("")

    def _set_status_badge_style(self, label, fg, bg):
        """为轻量状态标签设置统一的胶囊样式。"""
        if not label:
            return
        badge_font_size = getattr(self, "_status_badge_font_size", 12)
        label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {Theme.LIGHT["border"]};
                border-radius: 14px;
                padding: 6px 12px;
                font-size: {badge_font_size}px;
                font-weight: 700;
            }}
            """
        )

    def _set_info_bar_message(self, message):
        """设置顶部临时任务提示；空值时按当前模式决定是否隐藏。"""
        self.info_bar_message = str(message).strip() if message else ""
        self._refresh_info_bar_visibility()

    def _clear_info_bar_message(self):
        """清空顶部临时任务提示。"""
        self.info_bar_message = ""
        self._refresh_info_bar_visibility()

    def _refresh_info_bar_visibility(self):
        """避免顶部提示条与工作台摘要重复。"""
        if not hasattr(self, "info_bar"):
            return

        if self.current_ui_mode == "idle":
            if self.info_bar_message:
                self.info_bar.setText(self.info_bar_message)
                self.info_bar.setVisible(True)
            else:
                self.info_bar.setVisible(False)
            return

        if self.info_bar_message:
            self.info_bar.setText(self.info_bar_message)
            self.info_bar.setVisible(True)
        else:
            self.info_bar.setVisible(False)

    def _rebuild_idle_action_layout(self, density_mode):
        """让首页主动作与支持入口在桌面端双列，窄窗口再收成单列。"""
        if not hasattr(self, "idle_action_buttons_layout"):
            return

        layout = self.idle_action_buttons_layout
        while layout.count():
            layout.takeAt(0)

        if density_mode == "narrow":
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 0)
            layout.addWidget(self.idle_start_card, 0, 0)
            layout.addWidget(self.idle_support_card, 1, 0)
        else:
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 1)
            layout.addWidget(self.idle_start_card, 0, 0)
            layout.addWidget(self.idle_support_card, 0, 1)

    def _rebuild_idle_support_actions_layout(self, density_mode):
        """重排首页支持区动作按钮，横排左对齐，窄窗口改为 2+1。"""
        if not hasattr(self, "idle_support_actions_layout"):
            return

        layout = self.idle_support_actions_layout
        while layout.count():
            layout.takeAt(0)

        buttons = [
            getattr(self, "btn_idle_feedback", None),
            getattr(self, "btn_idle_manual", None),
            getattr(self, "btn_idle_donate", None),
        ]
        buttons = [button for button in buttons if button]
        if not buttons:
            return

        for column in range(3):
            layout.setColumnStretch(column, 0)

        if density_mode == "narrow":
            # 窄窗口 2+1 换行，仍保持左对齐
            layout.addWidget(buttons[0], 0, 0)
            if len(buttons) > 1:
                layout.addWidget(buttons[1], 0, 1)
            if len(buttons) > 2:
                layout.addWidget(buttons[2], 1, 0)
        else:
            for index, button in enumerate(buttons):
                layout.addWidget(button, 0, index)

    def _rebuild_idle_route_layout(self, density_mode):
        """重排首页入口卡，保证桌面端严格 2x2 对齐。"""
        if not hasattr(self, "idle_routes_layout"):
            return

        layout = self.idle_routes_layout
        while layout.count():
            layout.takeAt(0)

        if density_mode == "narrow":
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 0)
            for row in range(max(1, len(getattr(self, "idle_route_cards", [])) + 1)):
                layout.setRowStretch(row, 0)
            for index, route_card in enumerate(getattr(self, "idle_route_cards", [])):
                layout.addWidget(route_card, index, 0)
        else:
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 1)
            layout.setRowStretch(0, 0)
            layout.setRowStretch(1, 0)
            for index, route_card in enumerate(getattr(self, "idle_route_cards", [])):
                layout.addWidget(route_card, index // 2, index % 2)

    def _rebuild_batch_action_layout(self, density_mode):
        """重排批量页动作区，宽窗口横排，中窗口两列，窄窗口单列。"""
        if not hasattr(self, "batch_actions_layout"):
            return

        layout = self.batch_actions_layout
        while layout.count():
            layout.takeAt(0)

        buttons = list(getattr(self, "batch_action_buttons", []))
        if not buttons:
            return

        for column in range(max(4, len(buttons))):
            layout.setColumnStretch(column, 0)
        for row in range(max(4, len(buttons))):
            layout.setRowStretch(row, 0)

        if density_mode == "narrow":
            layout.setColumnStretch(0, 1)
            for index, button in enumerate(buttons):
                layout.addWidget(button, index, 0)
        elif density_mode == "compact":
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 1)
            for index, button in enumerate(buttons):
                layout.addWidget(button, index // 2, index % 2)
        else:
            for column in range(len(buttons)):
                layout.setColumnStretch(column, 1)
            for index, button in enumerate(buttons):
                layout.addWidget(button, 0, index)

    def _rebuild_batch_stage_layout(self, density_mode):
        """重排批量页阶段卡，桌面端横排，中窗口两列，窄窗口单列。"""
        if not hasattr(self, "batch_stage_layout"):
            return

        layout = self.batch_stage_layout
        while layout.count():
            layout.takeAt(0)

        cards = list(getattr(self, "batch_stage_cards", []))
        if not cards:
            return

        if density_mode == "narrow":
            columns = 1
        elif density_mode == "compact":
            columns = 2
        else:
            columns = 3

        for column in range(max(columns, len(cards))):
            layout.setColumnStretch(column, 0)
        for row in range(len(cards)):
            layout.setRowStretch(row, 0)

        for index, (frame, _title_label, _note_label) in enumerate(cards):
            row = index // columns
            column = index % columns
            layout.addWidget(frame, row, column)

        for column in range(columns):
            layout.setColumnStretch(column, 1)

    def _rebuild_batch_metrics_layout(self, density_mode):
        """重排批量页指标卡，宽窗口四列，中窗口两列，窄窗口单列。"""
        if not hasattr(self, "batch_metrics_layout"):
            return

        layout = self.batch_metrics_layout
        while layout.count():
            layout.takeAt(0)

        cards = list(getattr(self, "batch_metric_cards", []))
        if not cards:
            return

        if density_mode == "narrow":
            columns = 1
        elif density_mode == "compact":
            columns = 2
        else:
            columns = 4

        for column in range(max(columns, len(cards))):
            layout.setColumnStretch(column, 0)
        for row in range(len(cards)):
            layout.setRowStretch(row, 0)

        for index, card in enumerate(cards):
            row = index // columns
            column = index % columns
            layout.addWidget(card, row, column)

        for column in range(columns):
            layout.setColumnStretch(column, 1)

    def _rebuild_merge_stage_layout(self, density_mode):
        """重排图片合并阶段卡，桌面端横排，中窗口两列，窄窗口单列。"""
        if not hasattr(self, "merge_stage_layout"):
            return

        layout = self.merge_stage_layout
        while layout.count():
            layout.takeAt(0)

        cards = list(getattr(self, "merge_stage_cards", []))
        if not cards:
            return

        if density_mode == "narrow":
            columns = 1
        elif density_mode == "compact":
            columns = 2
        else:
            columns = 3

        for column in range(max(columns, len(cards))):
            layout.setColumnStretch(column, 0)
        for row in range(len(cards)):
            layout.setRowStretch(row, 0)

        for index, (frame, _title_label, _note_label) in enumerate(cards):
            row = index // columns
            column = index % columns
            layout.addWidget(frame, row, column)

        for column in range(columns):
            layout.setColumnStretch(column, 1)

    def _rebuild_merge_metrics_layout(self, density_mode):
        """重排图片合并指标卡，宽窗口三列，中窗口两列，窄窗口单列。"""
        if not hasattr(self, "merge_metrics_layout"):
            return

        layout = self.merge_metrics_layout
        while layout.count():
            layout.takeAt(0)

        cards = list(getattr(self, "merge_metric_cards", []))
        if not cards:
            return

        if density_mode == "narrow":
            columns = 1
        elif density_mode == "compact":
            columns = 2
        else:
            columns = 3

        for column in range(max(columns, len(cards))):
            layout.setColumnStretch(column, 0)
        for row in range(len(cards)):
            layout.setRowStretch(row, 0)

        for index, card in enumerate(cards):
            row = index // columns
            column = index % columns
            layout.addWidget(card, row, column)

        for column in range(columns):
            layout.setColumnStretch(column, 1)

    def _rebuild_batch_detail_layout(self, density_mode):
        """重排批量页摘要/结果/日志区，宽窗口双区，窄窗口单列。"""
        if not hasattr(self, "batch_detail_layout"):
            return

        layout = self.batch_detail_layout
        while layout.count():
            layout.takeAt(0)

        summary_section = getattr(self, "batch_summary_section", None)
        result_section = getattr(self, "batch_result_section", None)
        log_section = getattr(self, "batch_log_section", None)
        if not summary_section or not result_section or not log_section:
            return

        for column in range(3):
            layout.setColumnStretch(column, 0)
        for row in range(3):
            layout.setRowStretch(row, 0)

        if density_mode == "narrow":
            layout.setHorizontalSpacing(0)
            layout.setVerticalSpacing(12)
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 0)
            layout.addWidget(summary_section, 0, 0)
            layout.addWidget(result_section, 1, 0)
            layout.addWidget(log_section, 2, 0)
            layout.setRowStretch(0, 0)
            layout.setRowStretch(1, 1)
            layout.setRowStretch(2, 1)
        elif density_mode == "compact":
            layout.setHorizontalSpacing(12)
            layout.setVerticalSpacing(12)
            layout.setColumnStretch(0, 11)
            layout.setColumnStretch(1, 13)
            layout.addWidget(summary_section, 0, 0)
            layout.addWidget(result_section, 0, 1)
            layout.addWidget(log_section, 1, 0, 1, 2)
            layout.setRowStretch(0, 1)
            layout.setRowStretch(1, 1)
        else:
            layout.setHorizontalSpacing(14 if density_mode == "wide" else 12)
            layout.setVerticalSpacing(14 if density_mode == "wide" else 12)
            layout.setColumnStretch(0, 8)
            layout.setColumnStretch(1, 18)
            layout.addWidget(summary_section, 0, 0)
            layout.addWidget(log_section, 1, 0)
            layout.addWidget(result_section, 0, 1, 2, 1)
            layout.setRowStretch(0, 0)
            layout.setRowStretch(1, 1)

    def _get_display_scale_factor(self):
        """返回当前显示环境的缩放因子，主要用于 Windows DPI 收口。"""
        import platform

        if platform.system() != "Windows":
            return 1.0

        screen = None
        try:
            handle = self.windowHandle()
            if handle:
                screen = handle.screen()
        except Exception:
            screen = None

        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return 1.0

        try:
            scale = screen.logicalDotsPerInch() / 96.0
        except Exception:
            scale = 1.0

        return max(1.0, min(scale, 2.0))

    def _refresh_windows_density_metrics(self, density_mode):
        """按 Windows DPI 和当前工具栏密度收口高度、间距与命中区。"""
        if not hasattr(self, "toolbar") or not hasattr(self, "toolbar_layout"):
            return

        scale = self._get_display_scale_factor()
        theme = Theme.LIGHT

        if scale >= 1.5:
            toolbar_height = 68
            button_height = 40
            side_margin = 12
            vertical_margin = 8
            spacing = 7
            workbench_h_margin = 16
            workbench_v_margin = 11
            title_font_size = 17
            subtitle_font_size = 12
            chip_font_size = 12
            meta_font_size = 12
            workflow_font_size = 12
            compare_header_height = 34
            compare_header_font_size = 12
            progress_height = 28
            cancel_width = 72
            batch_result_row_height = 48
        elif scale >= 1.25:
            toolbar_height = 64
            button_height = 38
            side_margin = 14
            vertical_margin = 8
            spacing = 8
            workbench_h_margin = 17
            workbench_v_margin = 11
            title_font_size = 16
            subtitle_font_size = 12
            chip_font_size = 12
            meta_font_size = 12
            workflow_font_size = 11
            compare_header_height = 32
            compare_header_font_size = 12
            progress_height = 26
            cancel_width = 68
            batch_result_row_height = 44
        else:
            toolbar_height = 58
            button_height = 36
            side_margin = 16
            vertical_margin = 7
            spacing = 10
            workbench_h_margin = 18
            workbench_v_margin = 12
            title_font_size = 16
            subtitle_font_size = 11
            chip_font_size = 11
            meta_font_size = 12
            workflow_font_size = 11
            compare_header_height = 30
            compare_header_font_size = 12
            progress_height = 24
            cancel_width = 60
            batch_result_row_height = 40

        current_mode = getattr(self, "current_ui_mode", "idle")

        logical_height = max(760, self.height())
        logical_width = max(1200, self.width())
        is_tall_workspace_window = logical_height >= 980
        is_short_workspace_window = logical_height <= 760
        is_very_wide_workspace_window = logical_width >= 1760
        is_ultra_wide_workspace_window = logical_width >= 2140
        is_cinema_wide_workspace_window = logical_width >= 2460
        is_workspace_mode = current_mode in {"pdf", "word", "batch", "image_merge"}

        if density_mode == "narrow":
            side_margin = max(10, side_margin - 2)
            spacing = max(6, spacing - 1)
            title_font_size = max(15, title_font_size - 1)
        elif density_mode == "compact":
            side_margin = max(11, side_margin - 1)
            spacing = max(7, spacing - 1)

        if scale >= 1.5:
            toolbar_height += 2
            button_height += 2
            progress_height += 2
            batch_result_row_height += 2
        elif scale >= 1.25:
            toolbar_height += 1
            button_height += 1

        if is_tall_workspace_window:
            toolbar_height += 2
            vertical_margin += 1
            spacing += 1
            title_font_size += 1
            subtitle_font_size += 1 if scale >= 1.25 else 0
        elif is_short_workspace_window:
            toolbar_height = max(56, toolbar_height - 2)
            button_height = max(34, button_height - 1)
            vertical_margin = max(6, vertical_margin - 1)
            spacing = max(6, spacing - 1)
            workbench_v_margin = max(10, workbench_v_margin - 1)

        is_pdf_like_mode = current_mode in {"pdf", "image_merge"}

        if current_mode == "idle":
            toolbar_height = max(42, toolbar_height - 10)
            vertical_margin = max(5, vertical_margin - 2)
            spacing = max(6, spacing - 1)
        elif is_pdf_like_mode:
            toolbar_height += 4
            vertical_margin += 1

        self._workflow_step_font_size = workflow_font_size
        self._status_badge_font_size = chip_font_size
        self._toolbar_meta_font_size = meta_font_size
        self._button_density_metrics = {
            "button_font_size": 14 if scale >= 1.5 else 13,
            "button_padding_v": 8 if scale >= 1.5 else 7,
            "button_padding_h": 15 if scale >= 1.5 else 14,
            "icon_font_size": 16 if scale >= 1.25 else 14,
            "icon_padding_v": 5 if scale >= 1.25 else 4,
            "icon_padding_h": 10 if scale >= 1.25 else 8,
            "icon_min": 34 if scale >= 1.5 else (32 if scale >= 1.25 else 28),
        }
        if density_mode == "narrow":
            self._button_density_metrics["button_padding_h"] = max(12, self._button_density_metrics["button_padding_h"] - 2)
        elif density_mode == "compact":
            self._button_density_metrics["button_padding_h"] = max(13, self._button_density_metrics["button_padding_h"] - 1)

        toolbar_bottom_margin = vertical_margin + (4 if is_pdf_like_mode else (2 if current_mode != "idle" else 1))
        toolbar_extra_height = 5 if is_pdf_like_mode else (2 if current_mode != "idle" else 0)
        self.toolbar.setFixedHeight(toolbar_height + toolbar_extra_height)
        self.toolbar_layout.setContentsMargins(side_margin, vertical_margin, side_margin, toolbar_bottom_margin)
        self.toolbar_layout.setSpacing(max(10, spacing + 1))

        group_spacing = max(6, spacing - 2)  # cp84: 组内间距下限 4→6（避免按钮拥挤）
        group_margin_h = 0
        group_margin_v = 2 if is_pdf_like_mode else 1
        utility_spacing = group_spacing
        for group_layout in [
            getattr(self, "toolbar_primary_layout", None),
            getattr(self, "toolbar_word_layout", None),
            getattr(self, "toolbar_pdf_layout", None),
            getattr(self, "toolbar_edit_layout", None),
        ]:
            if group_layout:
                group_layout.setContentsMargins(group_margin_h, group_margin_v, group_margin_h, group_margin_v)
                group_layout.setSpacing(group_spacing)
        if hasattr(self, "toolbar_utility_layout"):
            self.toolbar_utility_layout.setContentsMargins(0, group_margin_v, 0, group_margin_v)
            self.toolbar_utility_layout.setSpacing(utility_spacing)

        if hasattr(self, "workbench_layout"):
            self.workbench_layout.setContentsMargins(workbench_h_margin, workbench_v_margin, workbench_h_margin, workbench_v_margin)
            self.workbench_layout.setSpacing(6 if density_mode == "wide" else 5)
        if hasattr(self, "context_top_layout"):
            self.context_top_layout.setSpacing(14 if density_mode == "wide" else 10)
        if hasattr(self, "workbench_text_layout"):
            self.workbench_text_layout.setSpacing(4 if density_mode == "wide" else 3)

        workspace_stage_margin = 14 if density_mode == "wide" else (10 if density_mode == "compact" else 8)
        workspace_stage_top_margin = 10 if density_mode == "wide" else (8 if density_mode == "compact" else 6)
        # v40.1.5（用户反馈）：卡片下缘距压到最小——底条紧贴工作区卡片，
        # 中间显示区域最大化（原 16/14/10 的留白整段收回）
        workspace_stage_bottom_margin = 4 if density_mode == "wide" else (3 if density_mode == "compact" else 2)
        preview_shell_padding = 8 if density_mode == "wide" else (6 if density_mode == "compact" else 5)
        preview_content_padding = 10 if density_mode == "wide" else (8 if density_mode == "compact" else 6)
        preview_content_spacing = 12 if density_mode == "wide" else (10 if density_mode == "compact" else 8)
        compare_header_gap = 10 if density_mode == "wide" else 8
        batch_card_padding_h = 28 if density_mode == "wide" else (24 if density_mode == "compact" else 20)
        batch_card_padding_v = 24 if density_mode == "wide" else (20 if density_mode == "compact" else 18)
        batch_detail_padding_h = 18 if density_mode == "wide" else (16 if density_mode == "compact" else 14)
        batch_detail_padding_v = 16 if density_mode == "wide" else (14 if density_mode == "compact" else 12)
        batch_section_gap = 14 if density_mode == "wide" else (12 if density_mode == "compact" else 10)
        batch_minor_gap = 10 if density_mode == "wide" else (8 if density_mode == "compact" else 6)
        if is_workspace_mode:
            workspace_stage_margin = max(4, workspace_stage_margin - 6)
            workspace_stage_bottom_margin = max(2, workspace_stage_bottom_margin - 1)
        if is_very_wide_workspace_window:
            workspace_stage_margin = max(2, workspace_stage_margin - 2)
            batch_card_padding_h = max(20, batch_card_padding_h - 2)
            batch_detail_padding_h = max(14, batch_detail_padding_h - 1)
        if is_ultra_wide_workspace_window:
            workspace_stage_margin = max(2, workspace_stage_margin - 2)
            preview_shell_padding = max(3, preview_shell_padding - 1)
            preview_content_padding = max(4, preview_content_padding - 1)
            batch_card_padding_h = max(18, batch_card_padding_h - 2)
            batch_section_gap = max(10, batch_section_gap - 1)
        if is_cinema_wide_workspace_window:
            workspace_stage_margin = max(1, workspace_stage_margin - 1)
            preview_shell_padding = max(3, preview_shell_padding - 1)
            preview_content_padding = max(4, preview_content_padding - 1)
            batch_card_padding_h = max(16, batch_card_padding_h - 2)
            batch_detail_padding_h = max(12, batch_detail_padding_h - 1)
            batch_section_gap = max(9, batch_section_gap - 1)
        if is_workspace_mode and is_very_wide_workspace_window:
            workbench_h_margin = max(14, workbench_h_margin - 2)
        if is_workspace_mode and is_ultra_wide_workspace_window:
            workbench_h_margin = max(12, workbench_h_margin - 2)
        if is_workspace_mode and is_cinema_wide_workspace_window:
            workbench_h_margin = max(10, workbench_h_margin - 2)
        if getattr(self, "current_ui_mode", "idle") in {"pdf", "word"}:
            workspace_stage_top_margin = max(4, workspace_stage_top_margin - 2)
            preview_shell_padding = max(4, preview_shell_padding - 1)
            preview_content_padding = max(5, preview_content_padding - 2)
        if getattr(self, "current_ui_mode", "idle") == "pdf":
            workspace_stage_top_margin = max(3, workspace_stage_top_margin - 1)
            preview_shell_padding = max(3, preview_shell_padding - 1)
            preview_content_padding = max(4, preview_content_padding - 1)
        if is_tall_workspace_window and getattr(self, "current_ui_mode", "idle") in {"pdf", "word"}:
            workspace_stage_top_margin = max(2, workspace_stage_top_margin - 1)
            workspace_stage_bottom_margin = max(6, workspace_stage_bottom_margin - 2)
            preview_shell_padding = max(3, preview_shell_padding - 1)
            preview_content_padding = max(4, preview_content_padding - 1)
            preview_content_spacing = max(8, preview_content_spacing - 1)
        if is_tall_workspace_window and getattr(self, "current_ui_mode", "idle") == "batch":
            workspace_stage_top_margin = max(4, workspace_stage_top_margin - 1)
            workspace_stage_bottom_margin = max(8, workspace_stage_bottom_margin - 2)
            batch_card_padding_v = max(18, batch_card_padding_v - 2)
            batch_section_gap = max(10, batch_section_gap - 2)
        preview_top_padding = max(4, preview_content_padding - 1)
        if hasattr(self, "pdf_workspace_outer_layout"):
            self.pdf_workspace_outer_layout.setContentsMargins(
                workspace_stage_margin,
                workspace_stage_top_margin,
                workspace_stage_margin,
                workspace_stage_bottom_margin,
            )
        if hasattr(self, "word_compare_outer_layout"):
            self.word_compare_outer_layout.setContentsMargins(
                workspace_stage_margin,
                workspace_stage_top_margin,
                workspace_stage_margin,
                workspace_stage_bottom_margin,
            )
        if hasattr(self, "batch_outer_layout"):
            self.batch_outer_layout.setContentsMargins(
                workspace_stage_margin,
                workspace_stage_top_margin,
                workspace_stage_margin,
                workspace_stage_bottom_margin,
            )
        if hasattr(self, "merge_outer_layout"):
            self.merge_outer_layout.setContentsMargins(
                workspace_stage_margin,
                workspace_stage_top_margin,
                workspace_stage_margin,
                workspace_stage_bottom_margin,
            )
        preview_shell_cap = 2560 if density_mode == "wide" else (2240 if density_mode == "compact" else 1680)
        preview_shell_min = 1040
        if getattr(self, "current_ui_mode", "idle") == "word" and getattr(self, "word_compare_mode", False):
            preview_shell_cap = 2580 if density_mode == "wide" else (2260 if density_mode == "compact" else 1760)
            preview_shell_min = 1420 if density_mode == "wide" else (1220 if density_mode == "compact" else 980)
        elif getattr(self, "current_ui_mode", "idle") == "word" and not getattr(self, "word_compare_mode", False):
            preview_shell_cap = 2580 if density_mode == "wide" else (2220 if density_mode == "compact" else 1700)
            preview_shell_min = 1360 if density_mode == "wide" else (1160 if density_mode == "compact" else 940)
        elif getattr(self, "current_ui_mode", "idle") == "pdf":
            preview_shell_cap = 2600 if density_mode == "wide" else (2280 if density_mode == "compact" else 1760)
        if is_ultra_wide_workspace_window:
            preview_shell_cap += 140
        elif is_very_wide_workspace_window:
            preview_shell_cap += 80
        if is_cinema_wide_workspace_window:
            preview_shell_cap += 220
        preview_shell_width = min(
            preview_shell_cap,
            max(preview_shell_min, logical_width - (workspace_stage_margin * 2) - 8),
        )
        workspace_card_width = min(
            2280 if density_mode == "wide" else (1980 if density_mode == "compact" else 1500),
            max(1040, logical_width - (workspace_stage_margin * 2) - 16),
        )
        if is_ultra_wide_workspace_window:
            workspace_card_width = min(workspace_card_width + 140, logical_width - (workspace_stage_margin * 2) - 8)
        elif is_very_wide_workspace_window:
            workspace_card_width = min(workspace_card_width + 80, logical_width - (workspace_stage_margin * 2) - 8)
        if is_cinema_wide_workspace_window:
            workspace_card_width = min(workspace_card_width + 220, logical_width - (workspace_stage_margin * 2) - 8)
        if hasattr(self, "pdf_workspace_shell"):
            self.pdf_workspace_shell.setMaximumWidth(preview_shell_width)
        if hasattr(self, "pdf_workspace_row_layout"):
            center_stretch = 28 if density_mode == "wide" else (22 if density_mode == "compact" else 16)
            if is_very_wide_workspace_window:
                center_stretch += 4
            if is_ultra_wide_workspace_window:
                center_stretch += 2
            if is_cinema_wide_workspace_window:
                center_stretch += 4
            side_stretch = 0 if is_ultra_wide_workspace_window else 1
            self.pdf_workspace_row_layout.setStretch(0, side_stretch)
            self.pdf_workspace_row_layout.setStretch(1, center_stretch)
            self.pdf_workspace_row_layout.setStretch(2, side_stretch)
        if hasattr(self, "pdf_workspace_shell_layout"):
            self.pdf_workspace_shell_layout.setContentsMargins(
                preview_shell_padding,
                preview_shell_padding,
                preview_shell_padding,
                preview_shell_padding,
            )
        if hasattr(self, "word_workspace_shell"):
            self.word_workspace_shell.setMaximumWidth(preview_shell_width)
        if hasattr(self, "word_workspace_row_layout"):
            center_stretch = 28 if density_mode == "wide" else (22 if density_mode == "compact" else 16)
            if is_very_wide_workspace_window:
                center_stretch += 4
            if is_ultra_wide_workspace_window:
                center_stretch += 2
            if is_cinema_wide_workspace_window:
                center_stretch += 4
            side_stretch = 0 if is_ultra_wide_workspace_window else 1
            self.word_workspace_row_layout.setStretch(0, side_stretch)
            self.word_workspace_row_layout.setStretch(1, center_stretch)
            self.word_workspace_row_layout.setStretch(2, side_stretch)
        if hasattr(self, "word_workspace_shell_layout"):
            self.word_workspace_shell_layout.setContentsMargins(
                preview_shell_padding,
                preview_shell_padding,
                preview_shell_padding,
                preview_shell_padding,
            )
            self.word_workspace_shell_layout.setSpacing(max(4, batch_minor_gap - 3))
        if hasattr(self, "batch_card"):
            self.batch_card.setMaximumWidth(workspace_card_width)
            self.batch_card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding if is_tall_workspace_window else QSizePolicy.Policy.Maximum,
            )
        if hasattr(self, "batch_card_row_layout"):
            center_stretch = 18 if density_mode == "wide" else (14 if density_mode == "compact" else 10)
            if is_very_wide_workspace_window:
                center_stretch += 3
            if is_ultra_wide_workspace_window:
                center_stretch += 1
            if is_cinema_wide_workspace_window:
                center_stretch += 3
            side_stretch = 0 if is_ultra_wide_workspace_window else 1
            self.batch_card_row_layout.setStretch(0, side_stretch)
            self.batch_card_row_layout.setStretch(1, center_stretch)
            self.batch_card_row_layout.setStretch(2, side_stretch)
        if hasattr(self, "batch_card_layout"):
            self.batch_card_layout.setContentsMargins(
                batch_card_padding_h,
                batch_card_padding_v,
                batch_card_padding_h,
                batch_card_padding_v,
            )
            self.batch_card_layout.setSpacing(batch_section_gap)
        batch_left_rail_width = 380 if density_mode == "wide" else (350 if density_mode == "compact" else 16777215)
        if is_cinema_wide_workspace_window and batch_left_rail_width < 16777215:
            batch_left_rail_width = max(340, batch_left_rail_width - 20)
        if hasattr(self, "batch_summary_section"):
            self.batch_summary_section.setMaximumWidth(batch_left_rail_width)
            self.batch_summary_section.setMinimumWidth(0 if density_mode == "narrow" else max(280, batch_left_rail_width - 70))
        if hasattr(self, "batch_log_section"):
            self.batch_log_section.setMaximumWidth(batch_left_rail_width)
            self.batch_log_section.setMinimumWidth(0 if density_mode == "narrow" else max(280, batch_left_rail_width - 70))
        if hasattr(self, "batch_result_section"):
            self.batch_result_section.setMaximumWidth(16777215)
            batch_result_min_width = 0 if density_mode == "narrow" else (840 if density_mode == "wide" else 700)
            if is_cinema_wide_workspace_window and batch_result_min_width:
                batch_result_min_width += 140
            self.batch_result_section.setMinimumWidth(batch_result_min_width)
        if hasattr(self, "merge_card"):
            self.merge_card.setMaximumWidth(workspace_card_width)
            self.merge_card.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding if is_tall_workspace_window else QSizePolicy.Policy.Maximum,
            )
        if hasattr(self, "merge_card_layout"):
            self.merge_card_layout.setContentsMargins(
                batch_card_padding_h,
                batch_card_padding_v,
                batch_card_padding_h,
                batch_card_padding_v,
            )
            self.merge_card_layout.setSpacing(batch_section_gap)
        if hasattr(self, "merge_card_row_layout"):
            center_stretch = 14 if density_mode == "wide" else (12 if density_mode == "compact" else 8)
            if is_very_wide_workspace_window:
                center_stretch += 2
            if is_ultra_wide_workspace_window:
                center_stretch += 1
            if is_cinema_wide_workspace_window:
                center_stretch += 3
            side_stretch = 0 if is_ultra_wide_workspace_window else 1
            self.merge_card_row_layout.setStretch(0, side_stretch)
            self.merge_card_row_layout.setStretch(1, center_stretch)
            self.merge_card_row_layout.setStretch(2, side_stretch)
        if hasattr(self, "idle_outer_layout"):
            idle_side_margin = max(14, side_margin + (6 if is_very_wide_workspace_window else 8))
            if is_ultra_wide_workspace_window:
                idle_side_margin = max(12, idle_side_margin - 2)
            self.idle_outer_layout.setContentsMargins(idle_side_margin, 14, idle_side_margin, 26)
        if hasattr(self, "idle_card_layout"):
            idle_card_margin = 28 if density_mode == "wide" else (24 if density_mode == "compact" else 20)
            self.idle_card_layout.setContentsMargins(idle_card_margin, idle_card_margin - 4, idle_card_margin, idle_card_margin - 6)
            self.idle_card_layout.setSpacing(14 if density_mode == "wide" else 11)
        if hasattr(self, "idle_card"):
            self.idle_card.setMaximumWidth(16777215)  # 跟随窗口填满，均衡边距由 idle_outer_layout 控制
        if hasattr(self, "idle_hero_panel"):
            self.idle_hero_panel.setMaximumWidth(16777215)
        if hasattr(self, "idle_hero_layout"):
            self.idle_hero_layout.setSpacing(12 if density_mode == "wide" else 10)
        if hasattr(self, "idle_flow_panel"):
            self.idle_flow_panel.setMaximumWidth(16777215)
        if hasattr(self, "idle_section_panel"):
            self.idle_section_panel.setMaximumWidth(16777215)
        if hasattr(self, "idle_section_layout"):
            self.idle_section_layout.setSpacing(10 if density_mode == "wide" else 8)
        if hasattr(self, "idle_action_panel_layout"):
            self.idle_action_panel_layout.setContentsMargins(0, 2, 0, 2)
            self.idle_action_panel_layout.setSpacing(10 if density_mode == "wide" else 8)
        if hasattr(self, "idle_title_row_layout"):
            self.idle_title_row_layout.setSpacing(18 if density_mode == "wide" else 12)
        if hasattr(self, "idle_title_tools_layout"):
            self.idle_title_tools_layout.setSpacing(8 if density_mode == "wide" else 6)
        if hasattr(self, "idle_badge_row_layout"):
            self.idle_badge_row_layout.setSpacing(8 if density_mode == "wide" else 6)
        if hasattr(self, "idle_utility_row_layout"):
            self.idle_utility_row_layout.setSpacing(8 if density_mode == "wide" else 6)
        if hasattr(self, "idle_action_buttons_layout"):
            self.idle_action_buttons_layout.setHorizontalSpacing(16 if density_mode == "wide" else 12)
            self.idle_action_buttons_layout.setVerticalSpacing(10 if density_mode == "narrow" else 0)
        if hasattr(self, "idle_flow_layout"):
            self.idle_flow_layout.setContentsMargins(0, 2, 0, 0)
            self.idle_flow_layout.setSpacing(12 if density_mode == "wide" else 9)
        if hasattr(self, "idle_routes_layout"):
            self.idle_routes_layout.setHorizontalSpacing(16 if density_mode == "wide" else 12)
            self.idle_routes_layout.setVerticalSpacing(12 if density_mode == "wide" else 10)
        self._rebuild_idle_action_layout(density_mode)
        self._rebuild_idle_route_layout(density_mode)
        self._rebuild_batch_stage_layout(density_mode)
        self._rebuild_batch_metrics_layout(density_mode)
        self._rebuild_batch_action_layout(density_mode)
        self._rebuild_batch_detail_layout(density_mode)
        self._rebuild_merge_stage_layout(density_mode)
        self._rebuild_merge_metrics_layout(density_mode)
        for route_card in getattr(self, "idle_route_cards", []):
            route_card_height = 126 if density_mode == "wide" else (114 if density_mode == "compact" else 102)
            route_card.setMinimumHeight(route_card_height)
            route_card.setMaximumHeight(route_card_height + 18)
        if hasattr(self, "canvas_layout"):
            self.canvas_layout.setContentsMargins(
                preview_content_padding,
                preview_top_padding,
                preview_content_padding,
                preview_content_padding,
            )
            self.canvas_layout.setSpacing(preview_content_spacing)
        if hasattr(self, "word_compare_layout"):
            self.word_compare_layout.setContentsMargins(0, 0, 0, 0)
            self.word_compare_layout.setSpacing(max(4, preview_content_spacing - 5))
        if hasattr(self, "word_compare_header"):
            self.word_compare_header.setFixedHeight(compare_header_height)
        if hasattr(self, "word_header_layout"):
            self.word_header_layout.setSpacing(compare_header_gap)
            self.word_header_layout.setContentsMargins(0, 0, 0, 1)
        if hasattr(self, "original_panel_layout"):
            self.original_panel_layout.setContentsMargins(0, 0, 0, 0)
        if hasattr(self, "replaced_panel_layout"):
            self.replaced_panel_layout.setContentsMargins(0, 0, 0, 0)
        if hasattr(self, "batch_header_layout"):
            self.batch_header_layout.setContentsMargins(0, 0, 0, 2)
            self.batch_header_layout.setSpacing(batch_section_gap - 2)
        if hasattr(self, "batch_header_text_layout"):
            self.batch_header_text_layout.setSpacing(max(3, batch_minor_gap - 4))
        if hasattr(self, "batch_stage_layout"):
            self.batch_stage_layout.setContentsMargins(0, 0, 0, 0)
            self.batch_stage_layout.setHorizontalSpacing(batch_minor_gap + 2)
            self.batch_stage_layout.setVerticalSpacing(batch_minor_gap + 2)
        if hasattr(self, "batch_metrics_layout"):
            self.batch_metrics_layout.setContentsMargins(0, 0, 0, 0)
            self.batch_metrics_layout.setHorizontalSpacing(batch_minor_gap)
            self.batch_metrics_layout.setVerticalSpacing(batch_minor_gap)
        if hasattr(self, "merge_header_layout"):
            self.merge_header_layout.setContentsMargins(0, 0, 0, 2)
            self.merge_header_layout.setSpacing(batch_section_gap - 2)
        if hasattr(self, "merge_header_text_layout"):
            self.merge_header_text_layout.setSpacing(max(3, batch_minor_gap - 4))
        if hasattr(self, "merge_stage_layout"):
            self.merge_stage_layout.setContentsMargins(0, 0, 0, 0)
            self.merge_stage_layout.setHorizontalSpacing(batch_minor_gap + 2)
            self.merge_stage_layout.setVerticalSpacing(batch_minor_gap + 2)
        if hasattr(self, "merge_metrics_layout"):
            self.merge_metrics_layout.setContentsMargins(0, 0, 0, 0)
            self.merge_metrics_layout.setHorizontalSpacing(batch_minor_gap)
            self.merge_metrics_layout.setVerticalSpacing(batch_minor_gap)
        if hasattr(self, "batch_actions_layout"):
            self.batch_actions_layout.setContentsMargins(0, 2, 0, 0)
            self.batch_actions_layout.setHorizontalSpacing(batch_minor_gap)
            self.batch_actions_layout.setVerticalSpacing(batch_minor_gap)
        if hasattr(self, "batch_summary_section_layout"):
            self.batch_summary_section_layout.setContentsMargins(
                batch_detail_padding_h,
                batch_detail_padding_v,
                batch_detail_padding_h,
                batch_detail_padding_v,
            )
            self.batch_summary_section_layout.setSpacing(batch_minor_gap)
        if hasattr(self, "batch_result_section_layout"):
            self.batch_result_section_layout.setContentsMargins(
                batch_detail_padding_h,
                batch_detail_padding_v,
                batch_detail_padding_h,
                batch_detail_padding_v,
            )
            self.batch_result_section_layout.setSpacing(batch_minor_gap)
        if hasattr(self, "batch_log_section_layout"):
            self.batch_log_section_layout.setContentsMargins(
                batch_detail_padding_h,
                batch_detail_padding_v,
                batch_detail_padding_h,
                batch_detail_padding_v,
            )
            self.batch_log_section_layout.setSpacing(batch_minor_gap)
        if hasattr(self, "batch_result_toolbar"):
            self.batch_result_toolbar.setSpacing(max(6, batch_minor_gap - 1))
            self.batch_result_toolbar.setContentsMargins(0, 1, 0, 2)
            self.batch_result_toolbar.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        if hasattr(self, "batch_result_header_layout"):
            self.batch_result_header_layout.setContentsMargins(0, 0, 0, 0)
            self.batch_result_header_layout.setSpacing(batch_minor_gap + 4)
        if hasattr(self, "batch_summary_browser"):
            self.batch_summary_browser.setMinimumHeight(118 if density_mode == "wide" else (110 if density_mode == "compact" else 104))
            summary_max_height = 172 if density_mode == "wide" else (164 if density_mode == "compact" else 154)
            if is_tall_workspace_window:
                summary_max_height += 16
            self.batch_summary_browser.setMaximumHeight(summary_max_height)
        if hasattr(self, "batch_result_table"):
            result_min_height = 300 if density_mode == "wide" else (250 if density_mode == "compact" else 196)
            if is_tall_workspace_window:
                result_min_height += 40 if density_mode == "wide" else 28
            self.batch_result_table.setMinimumHeight(result_min_height)
            self.batch_result_table.setMaximumHeight(16777215)
            self.batch_result_table.setColumnWidth(0, 88 if density_mode == "wide" else (82 if density_mode == "compact" else 76))
            self.batch_result_table.setColumnWidth(3, 104 if density_mode == "wide" else (96 if density_mode == "compact" else 88))
        if hasattr(self, "batch_log_list"):
            log_min_height = 184 if density_mode == "wide" else (172 if density_mode == "compact" else 156)
            if is_tall_workspace_window:
                log_min_height += 24 if density_mode == "wide" else 18
            self.batch_log_list.setMinimumHeight(log_min_height)
            self.batch_log_list.setMaximumHeight(16777215)
        merge_metric_min_height = 108 if density_mode == "wide" else (100 if density_mode == "compact" else 94)
        for merge_card in getattr(self, "merge_metric_cards", []):
            if merge_card:
                merge_card.setMinimumHeight(merge_metric_min_height)
                merge_card.setMaximumHeight(16777215)

        icon_button_size = button_height
        for icon_btn in [
            getattr(self, "btn_encrypt", None),  # cp72: 加密锁图标按钮与导航图标同尺寸
            getattr(self, "btn_search", None),   # cp81: 搜索放大镜图标按钮同尺寸
            getattr(self, "btn_undo", None),     # cp83: 撤销/恢复图标按钮同尺寸
            getattr(self, "btn_redo", None),
            getattr(self, "btn_bookmark", None),  # v40.1.4（#7）：书签图标纳入统一尺寸
            getattr(self, "btn_reset", None),     # v40.1.4（用户反馈）：全图标按钮统一方形
            getattr(self, "btn_fit", None),
            getattr(self, "btn_fit_utility", None),
            getattr(self, "btn_extract", None),  # v40.1.5（用户反馈）：提取/截去与其他图标统一
            getattr(self, "btn_crop", None),
        ]:
            if icon_btn:
                icon_btn.setFixedSize(icon_button_size, icon_button_size)
                icon_btn.setIconSize(QSize(max(14, icon_button_size - 14), max(14, icon_button_size - 14)))

        # v40.1.4（用户反馈 #5/#7）：遮罩/页面视图图标开关统一方形尺寸（防挤压重叠）
        for toggle_btn in (
            getattr(self, "rb_black", None), getattr(self, "rb_white", None),
            getattr(self, "rb_color", None), getattr(self, "cb_page_view", None),
        ):
            if toggle_btn:
                toggle_btn.setFixedSize(icon_button_size, icon_button_size)
                # v40.1.4（用户反馈）：与标准图标按钮同比例（-14），全工具栏字形统一
                toggle_btn.setIconSize(QSize(max(14, icon_button_size - 14), max(14, icon_button_size - 14)))

        # v40.1.4（用户反馈）：设置齿轮按钮与相邻文字按钮上下严格平齐（同
        # button_height），左右向内收窄（宽=高-6），齿轮图标缩一档不显大
        _btn_st = getattr(self, "btn_settings", None)
        if _btn_st is not None:
            _st_h = button_height
            # v40.1.4（用户反馈）：齿轮做小——宽度收窄（-10）+ 图标缩档，高与其他平齐
            _btn_st.setFixedSize(max(22, _st_h - 10), _st_h)
            _btn_st.setIconSize(QSize(max(12, _st_h - 18), max(12, _st_h - 18)))


        control_height = button_height
        group_height = control_height + (7 if is_pdf_like_mode else 4)


        for button in [
            getattr(self, "btn_open", None),
            getattr(self, "btn_remove_watermark", None),  # v40.1.4（用户反馈）：去水印与其他同高
            getattr(self, "btn_scan", None),
            getattr(self, "btn_idle_open", None),
            getattr(self, "btn_idle_feedback", None),
            getattr(self, "btn_idle_manual", None),
            getattr(self, "btn_idle_donate", None),
            getattr(self, "btn_compare_toggle", None),
            getattr(self, "rb_black", None),
            getattr(self, "rb_white", None),
            getattr(self, "cb_page_view", None),
            getattr(self, "btn_fit", None),
            getattr(self, "btn_fit_utility", None),
            getattr(self, "btn_settings", None),
            getattr(self, "btn_feedback", None),
            getattr(self, "btn_workbench_feedback", None),
            getattr(self, "btn_more", None),
            getattr(self, "btn_save", None),
            getattr(self, "btn_cancel_scan", None),  # v40.1.4（用户反馈）：取消按钮与其他同高
            getattr(self, "btn_extract", None),   # v40.1.5：提取/截去同高
            getattr(self, "btn_crop", None),
        ]:
            if button:
                button.setMinimumHeight(control_height)
                button.setMaximumHeight(control_height)


        for group in [
            getattr(self, "toolbar_primary_group", None),
            getattr(self, "toolbar_word_group", None),
            getattr(self, "toolbar_pdf_group", None),
            getattr(self, "toolbar_utility_group", None),
        ]:
            if group:
                group.setMinimumHeight(group_height)
                group.setMaximumHeight(group_height)

        idle_action_width = 220 if density_mode == "wide" else (190 if density_mode == "compact" else 160)
        if hasattr(self, "btn_idle_open"):
            idle_primary_height = control_height + 4
            self.btn_idle_open.setMinimumWidth(idle_action_width)
            self.btn_idle_open.setMaximumWidth(16777215 if density_mode != "narrow" else idle_action_width)
            self.btn_idle_open.setMinimumHeight(idle_primary_height)
            self.btn_idle_open.setMaximumHeight(idle_primary_height)
        if hasattr(self, "idle_start_card"):
            start_min_height = idle_primary_height + (78 if density_mode == "wide" else (72 if density_mode == "compact" else 84))
            self.idle_start_card.setMinimumHeight(start_min_height)
            self.idle_start_card.setMaximumHeight(16777215)
        if hasattr(self, "idle_start_footer_layout"):
            self.idle_start_footer_layout.setSpacing(8 if density_mode == "wide" else 6)
        if hasattr(self, "btn_idle_feedback"):
            idle_secondary_height = control_height + 4
            idle_support_action_width = 120 if density_mode == "wide" else (108 if density_mode == "compact" else 100)
            self.btn_idle_feedback.setMinimumWidth(idle_support_action_width)
            self.btn_idle_feedback.setMaximumWidth(16777215 if density_mode != "narrow" else idle_action_width)
            self.btn_idle_feedback.setMinimumHeight(idle_secondary_height)
            self.btn_idle_feedback.setMaximumHeight(idle_secondary_height)
        for button in [getattr(self, "btn_idle_manual", None), getattr(self, "btn_idle_donate", None)]:
            if button:
                idle_secondary_height = control_height + 4
                idle_support_action_width = 120 if density_mode == "wide" else (108 if density_mode == "compact" else 100)
                button.setMinimumWidth(idle_support_action_width)
                button.setMaximumWidth(16777215 if density_mode != "narrow" else idle_action_width)
                button.setMinimumHeight(idle_secondary_height)
                button.setMaximumHeight(idle_secondary_height)
        if hasattr(self, "idle_support_card"):
            support_min_height = idle_primary_height + (92 if density_mode == "wide" else (88 if density_mode == "compact" else 108))
            self.idle_support_card.setMinimumHeight(support_min_height)
            self.idle_support_card.setMaximumHeight(16777215)

        for label in [getattr(self, "lbl_zoom", None), getattr(self, "lbl_page", None)]:
            if label:
                label.setMinimumHeight(control_height)
                label.setMaximumHeight(control_height)
                label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                label.setStyleSheet(
                    f"""
                    QLabel#toolbarMeta {{
                        color: {theme["text"]};
                        background-color: {theme["hover"]};
                        border: 1px solid {theme["border"]};
                        border-radius: 9px;
                        padding: 4px 10px;
                        font-size: {meta_font_size}px;
                        font-weight: 700;
                        min-width: 54px;
                    }}
                    """
                )
        if hasattr(self, "lbl_batch_result_meta"):
            self.lbl_batch_result_meta.setMinimumHeight(max(28, control_height - 4))
            self.lbl_batch_result_meta.setMaximumHeight(max(28, control_height - 4))
        if hasattr(self, "lbl_batch_result_hint"):
            self.lbl_batch_result_hint.setMinimumHeight(max(28, control_height - 4))
            self.lbl_batch_result_hint.setMaximumHeight(max(28, control_height - 4))
        batch_filter_height = max(30, control_height - 4)
        for button in [
            getattr(self, "btn_batch_filter_all", None),
            getattr(self, "btn_batch_filter_success", None),
            getattr(self, "btn_batch_filter_failed", None),
        ]:
            if button:
                button.setMinimumHeight(batch_filter_height)
                button.setMaximumHeight(batch_filter_height)
                button.setMinimumWidth(86 if density_mode == "wide" else (78 if density_mode == "compact" else 72))
        batch_filter_height = max(28, control_height - 4)
        batch_filter_width = 96 if density_mode == "wide" else (88 if density_mode == "compact" else 80)
        for button in [
            getattr(self, "btn_batch_filter_all", None),
            getattr(self, "btn_batch_filter_success", None),
            getattr(self, "btn_batch_filter_failed", None),
        ]:
            if button:
                button.setMinimumHeight(batch_filter_height)
                button.setMaximumHeight(batch_filter_height)
                button.setMinimumWidth(batch_filter_width)
        batch_action_width = 168 if density_mode == "wide" else (154 if density_mode == "compact" else 140)
        for button in getattr(self, "batch_action_buttons", []):
            if button:
                button.setMinimumWidth(batch_action_width)

        if hasattr(self, "lbl_workbench_title"):
            self.lbl_workbench_title.setStyleSheet(
                f"color: {theme['text']}; font-size: {title_font_size}px; font-weight: 700; background-color: transparent;"
            )
        for label in [getattr(self, "lbl_batch_title", None), getattr(self, "lbl_merge_title", None)]:
            if label:
                label.setStyleSheet(
                    f"color: {theme['text']}; font-size: {title_font_size + 3}px; font-weight: 700; background-color: transparent;"
                )
        for label in [
            getattr(self, "lbl_workbench_subtitle", None),
            getattr(self, "lbl_batch_subtitle", None),
            getattr(self, "lbl_merge_subtitle", None),
        ]:
            if label:
                label.setStyleSheet(
                    f"color: {theme['text_secondary']}; font-size: {subtitle_font_size}px; line-height: 1.7; background-color: transparent;"
                )
        for label in [
            getattr(self, "lbl_batch_meta", None),
            getattr(self, "lbl_batch_current_file", None),
            getattr(self, "lbl_merge_meta", None),
            getattr(self, "lbl_idle_tip", None),
            getattr(self, "lbl_idle_drop_hint", None),
        ]:
            if label:
                label.setStyleSheet(
                    f"color: {theme['text_secondary'] if label in (getattr(self, 'lbl_idle_tip', None), getattr(self, 'lbl_idle_drop_hint', None)) else theme['text']}; font-size: {subtitle_font_size}px; line-height: 1.7; background-color: transparent;"
                )
        if hasattr(self, "lbl_idle_section"):
            self.lbl_idle_section.setStyleSheet(
                f"color: {theme['text']}; font-size: {max(12, title_font_size - 1)}px; font-weight: 700; background-color: transparent;"
            )
        if hasattr(self, "lbl_idle_section_hint"):
            self.lbl_idle_section_hint.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {max(10, subtitle_font_size - 1)}px; font-weight: 600; background-color: transparent;"
            )
        for label in [getattr(self, "lbl_idle_offline_badge", None), getattr(self, "lbl_idle_auto_badge", None)]:
            if label:
                label.setStyleSheet(
                    f"color: {theme['primary']}; background-color: #E9F1FB; border: 1px solid {theme['border']}; border-radius: 9px; padding: 4px 9px; font-size: {max(10, subtitle_font_size - 1)}px; font-weight: 700;"
                )
        if hasattr(self, "lbl_idle_section_hint"):
            self.lbl_idle_section_hint.setVisible(density_mode != "narrow")
        if hasattr(self, "lbl_idle_auto_badge"):
            self.lbl_idle_auto_badge.setVisible(density_mode == "wide")
        if hasattr(self, "lbl_idle_drop_hint"):
            self.lbl_idle_drop_hint.setText(
                "支持直接拖拽到窗口，系统会自动分流" if density_mode == "wide"
                else ("支持直接拖拽到窗口" if density_mode == "compact" else "支持拖拽到窗口")
            )
        if hasattr(self, "lbl_idle_start_title"):
            self.lbl_idle_start_title.setStyleSheet(
                f"color: {theme['text']}; font-size: {max(12, title_font_size - 1)}px; font-weight: 700; background-color: transparent;"
            )
        if hasattr(self, "lbl_idle_start_text"):
            self.lbl_idle_start_text.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {max(10, subtitle_font_size - 1)}px; line-height: 1.6; background-color: transparent;"
            )
        if hasattr(self, "lbl_idle_support_text"):
            self.lbl_idle_support_text.setStyleSheet(
                f"color: {theme['text']}; font-size: {max(11, subtitle_font_size)}px; font-weight: 600; line-height: 1.5; background-color: transparent;"
            )
        if hasattr(self, "lbl_idle_support_meta"):
            self.lbl_idle_support_meta.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {max(10, subtitle_font_size - 1)}px; font-weight: 600; line-height: 1.5; background-color: transparent;"
            )
        if hasattr(self, "lbl_idle_support_email"):
            self.lbl_idle_support_email.setStyleSheet(
                f"color: {theme['primary']}; font-size: {max(10, subtitle_font_size - 1)}px; font-weight: 600; background-color: transparent;"
            )
        if hasattr(self, "lbl_idle_support_note"):
            self.lbl_idle_support_note.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {max(10, subtitle_font_size - 1)}px; line-height: 1.6; background-color: transparent;"
            )
        if hasattr(self, "btn_idle_settings"):
            self.btn_idle_settings.setMinimumHeight(control_height)
            self.btn_idle_settings.setMaximumHeight(control_height)
            self.btn_idle_settings.setMinimumWidth(112 if density_mode == "wide" else 96)
        if hasattr(self, "btn_idle_feedback"):
            self.btn_idle_feedback.setMinimumHeight(control_height)
            self.btn_idle_feedback.setMaximumHeight(control_height)
            self.btn_idle_feedback.setMinimumWidth(112 if density_mode == "wide" else 96)
        if hasattr(self, "btn_idle_manual"):
            self.btn_idle_manual.setMinimumHeight(control_height)
            self.btn_idle_manual.setMaximumHeight(control_height)
            self.btn_idle_manual.setMinimumWidth(112 if density_mode == "wide" else 96)
        if hasattr(self, "btn_idle_donate"):
            self.btn_idle_donate.setMinimumHeight(control_height)
            self.btn_idle_donate.setMaximumHeight(control_height)
            self.btn_idle_donate.setMinimumWidth(112 if density_mode == "wide" else 96)
        if hasattr(self, "btn_workbench_feedback"):
            self.btn_workbench_feedback.setMinimumHeight(control_height)
            self.btn_workbench_feedback.setMaximumHeight(control_height)
            self.btn_workbench_feedback.setMinimumWidth(112 if density_mode == "wide" else 96)
        if hasattr(self, "lbl_workbench_focus"):
            self.lbl_workbench_focus.setStyleSheet(
                f"""
                QLabel#workbenchFocus {{
                    background-color: #E9F1FB;
                    color: {theme["primary"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 14px;
                    padding: 6px 12px;
                    font-size: {chip_font_size}px;
                    font-weight: 700;
                }}
                """
            )
        for label in getattr(self, "workbench_guidance_labels", []):
            label.setStyleSheet(
                f"""
                QLabel#workbenchHintTag {{
                    background-color: #FBFCFE;
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 10px;
                    padding: 7px 12px;
                    font-size: {chip_font_size}px;
                    font-weight: 700;
                }}
                """
            )
        if hasattr(self, "info_bar"):
            self.info_bar.setStyleSheet(
                f"""
                QLabel#contextMessage {{
                    background-color: {theme["info_bar"]};
                    color: {theme["text_secondary"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-weight: 600;
                    font-size: {subtitle_font_size}px;
                }}
                """
            )
        for label in [getattr(self, "lbl_word_original_header", None), getattr(self, "lbl_word_replaced_header", None)]:
            if label:
                label.setStyleSheet(
                    f"""
                    QLabel#wordCompareLabel {{
                        color: {theme['text_secondary']};
                        background-color: {theme['hover']};
                        border: 1px solid {theme['border']};
                        border-radius: 10px;
                        padding: 3px 10px;
                        font-size: {max(11, compare_header_font_size - 1)}px;
                        font-weight: 600;
                    }}
                    """
                )
        for label in [
            getattr(self, "lbl_batch_log_hint", None),
            getattr(self, "lbl_batch_summary_hint", None),
            getattr(self, "lbl_batch_result_hint", None),
        ]:
            if label:
                label.setStyleSheet(
                    f"color: {theme['text_secondary']}; font-size: {subtitle_font_size}px; font-weight: 700; background-color: transparent;"
                )
        if hasattr(self, "batch_summary_browser"):
            self.batch_summary_browser.setStyleSheet(
                f"""
                QTextBrowser#batchSummaryBrowser {{
                    background-color: #FCFDFF;
                    color: {theme["text"]};
                    border: 1px solid #E4EBF3;
                    border-radius: 15px;
                    padding: 12px;
                    font-size: {subtitle_font_size}px;
                    line-height: 1.7;
                }}
                """
            )
        if hasattr(self, "batch_result_table"):
            self.batch_result_table.setStyleSheet(
                f"""
                QTableWidget#batchResultTable {{
                    background-color: {theme["surface"]};
                    color: {theme["text"]};
                    border: 1px solid #E4EBF3;
                    border-radius: 15px;
                    gridline-color: transparent;
                    padding: 6px;
                    font-size: {subtitle_font_size}px;
                }}
                QTableWidget#batchResultTable::item {{
                    padding: 8px 10px;
                    border-bottom: 1px solid #E9EEF5;
                }}
                QTableWidget#batchResultTable QHeaderView::section {{
                    background-color: #F7FAFD;
                    color: {theme["text_secondary"]};
                    border: none;
                    border-bottom: 1px solid #E4EBF3;
                    padding: 8px 10px;
                    font-size: {max(11, subtitle_font_size - 1)}px;
                    font-weight: 700;
                }}
                """
            )
            self.batch_result_table.verticalHeader().setDefaultSectionSize(batch_result_row_height)
            self.batch_result_table.horizontalHeader().setFixedHeight(batch_result_row_height - 2)
        if hasattr(self, "lbl_batch_result_meta"):
            self.lbl_batch_result_meta.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {max(11, subtitle_font_size - 1)}px; font-weight: 600; background-color: transparent;"
            )
        if hasattr(self, "progress"):
            self.progress.setFixedHeight(progress_height)
        if hasattr(self, "btn_cancel_scan"):
            self.btn_cancel_scan.setFixedSize(cancel_width, progress_height)
            # cp66: 随密度同步专用紧凑样式（通用 secondary 样式会裁切文字）
            self.btn_cancel_scan.setStyleSheet(self._get_cancel_scan_button_style(progress_height))

        self._refresh_batch_result_filter_buttons()
        self._refresh_button_density_styles()
        self._rebuild_idle_support_actions_layout(density_mode)

    def _refresh_button_density_styles(self):
        """在 DPI 或密度切换后，重新应用所有按钮的字体和内边距。"""
        for button in self.findChildren(QPushButton):
            style_type = button.property("btn_style")
            if not style_type:
                continue
            if button is getattr(self, "btn_more", None):
                continue
            button.setStyleSheet(self._get_button_style(style_type))

        self._refresh_toolbar_more_button_style()
        self._apply_native_toolbar_icons()

    def _refresh_toolbar_group_visibility(self):
        """按当前模式和响应式显隐，收口工具栏分组容器。"""
        group_map = [
            (getattr(self, "toolbar_primary_group", None), [getattr(self, "btn_open", None)]),
            (getattr(self, "toolbar_word_group", None), [getattr(self, "btn_settings", None), getattr(self, "btn_remove_watermark", None), getattr(self, "btn_compare_toggle", None)]),
            (getattr(self, "toolbar_pdf_group", None), [getattr(self, "rb_black", None), getattr(self, "rb_white", None)]),
            (getattr(self, "toolbar_edit_group", None), [getattr(self, "cb_page_view", None), getattr(self, "btn_undo", None), getattr(self, "btn_redo", None)]),
            (getattr(self, "toolbar_utility_group", None), [getattr(self, "btn_fit_utility", None), getattr(self, "btn_feedback", None), getattr(self, "btn_more", None), getattr(self, "btn_search", None), getattr(self, "btn_encrypt", None), getattr(self, "btn_scan", None), getattr(self, "btn_save", None)]),
        ]

        for group, widgets in group_map:
            if not group:
                continue
            group.setVisible(any(widget and not widget.isHidden() for widget in widgets))

    def _set_toolbar_widget_width(self, widget, min_width=0, extra=28):
        """根据当前文案为工具栏控件设置稳定宽度，避免文字被硬挤压。"""
        if not widget or not hasattr(widget, "fontMetrics"):
            return

        text = widget.text() if hasattr(widget, "text") else ""
        metrics = widget.fontMetrics()
        text_width = metrics.horizontalAdvance(text) + extra
        hint_width = 0
        try:
            widget.ensurePolished()
            hint_width = widget.sizeHint().width()
        except Exception:
            hint_width = 0

        if widget.objectName() == "toolbarMoreButton":
            hint_width += 12

        width = max(text_width, hint_width)
        width = max(width, min_width)
        widget.setMinimumWidth(width)
        widget.setMaximumWidth(width)

    def _set_toolbar_group_width(self, group, width=None):
        """为工具栏分组设置统一外宽；传 None 时恢复内容驱动宽度。"""
        if not group:
            return
        if width is None:
            group.setMinimumWidth(0)
            group.setMaximumWidth(16777215)
            return
        group.setMinimumWidth(width)
        group.setMaximumWidth(width)

    def _refresh_toolbar_overflow_menu(self, is_pdf, is_word, density_mode):
        """把低频动作收进更多菜单，避免窄窗口时挤爆工具栏。"""
        if not hasattr(self, "toolbar_more_menu"):
            return

        self.toolbar_more_menu.clear()
        has_item = False

        if is_word and not self.btn_compare_toggle.isVisible():
            compare_text = "打开对比预览"
            if self.word_doc and self._has_word_replacement_candidates():
                compare_text = "显示对比预览" if self.word_compare_user_hidden else "隐藏对比预览"
            compare_action = self.toolbar_more_menu.addAction(compare_text, self.toggle_word_compare_preview)
            compare_action.setEnabled(bool(self.word_doc) and self._has_word_replacement_candidates())
            has_item = True

        if is_pdf and not getattr(self, "btn_fit_utility", None).isVisible():
            self.toolbar_more_menu.addAction("适应页面", self.fit_page)
            has_item = True

        if is_pdf and density_mode == "narrow":
            if has_item:
                self.toolbar_more_menu.addSeparator()
            # v40.1.4（用户反馈）：去水印固定在"高级设置"右侧，narrow 不再收进
            # "更多"菜单——按 is_pdf 显隐（与 compact/wide 一致）
            if hasattr(self, "btn_remove_watermark"):
                self.btn_remove_watermark.setVisible(is_pdf)
            has_item = True
        # v40.1.4（用户反馈 #5）：取色遮罩常驻工具栏（此前 narrow 被收进"更多"
        # 菜单导致"按钮不见了"）——所有密度模式统一按 is_pdf 显隐，与黑/白遮罩同排
        if hasattr(self, "rb_color"):
            self.rb_color.setVisible(is_pdf)
            if not is_pdf and hasattr(self, "color_palette_widget"):
                self.color_palette_widget.hide()
            # v37.7.11 cp40: compact/wide 模式显隐去水印按钮
            # PDF 模式显式 show（兜底从 narrow 切回 wide/compact 后按钮被 hide 过的场景）
            if hasattr(self, "btn_remove_watermark"):
                if is_pdf:
                    self.btn_remove_watermark.show()
                else:
                    self.btn_remove_watermark.hide()

        self.btn_more.setVisible(has_item)

    def _show_toolbar_more_menu(self):
        """在按钮下方手动弹出更多菜单，避免系统菜单箭头把按钮布局挤坏。"""
        if not hasattr(self, "toolbar_more_menu") or self.toolbar_more_menu.isEmpty():
            return
        source_btn = self.sender()
        if not isinstance(source_btn, QPushButton):
            source_btn = getattr(self, "btn_more", None)
        if not source_btn or not source_btn.isVisible():
            return

        popup_pos = source_btn.mapToGlobal(source_btn.rect().bottomLeft())
        self.toolbar_more_menu.popup(popup_pos)

    def _toggle_dual_toolbar(self, checked=False):
        """工具栏双页按钮入口，保持按钮状态和画布状态同步。"""
        checked = bool(checked)
        # cp67: 双页与页面视图互斥
        if checked and getattr(self, "page_view_mode", False):
            self.set_page_view_mode(False)
        if hasattr(self, "cb_dual") and self.cb_dual.isChecked() != checked:
            self.cb_dual.setChecked(checked)
        self.toggle_dual_view(checked)
        self._refresh_toolbar_responsiveness()
        self._refresh_workbench_context()

    def _refresh_toolbar_responsiveness(self):
        """根据窗口宽度做工具栏响应式降级，保证缩放时仍可读。"""
        if not hasattr(self, "toolbar"):
            return

        width = self.width() or self.toolbar.width()
        # Qt 返回的是逻辑像素宽度，这里不再额外按屏幕缩放除一次，
        # 否则 Retina / Windows 高缩放下会被过早判成窄布局。
        effective_width = width
        scale = self._get_display_scale_factor()
        density_height = self.height() if scale > 1.0 else 0
        mode = self.current_ui_mode
        is_idle = mode == "idle"
        is_pdf = mode == "pdf"
        is_word = mode == "word"
        is_image_merge = mode == "image_merge"
        has_mode_results = self._has_pdf_redactions() if is_pdf else (self._has_word_replacement_candidates() if is_word else False)
        enabled_word_rules = self._count_enabled_word_rules() if is_word else 0

        density_mode = resolve_workspace_density_mode(mode, effective_width, density_height, scale)
        # cp85: 屏幕装不下工具栏内容时强制 narrow 档（缩文案+收纳低频按钮），
        # 由 _enforce_toolbar_min_width 置位；窗口变宽到容纳自然档位内容时自动解除
        if getattr(self, "_toolbar_forced_narrow", False):
            if density_mode == "narrow":
                self._toolbar_forced_narrow = False  # 自然档已是 narrow，标志冗余
            else:
                density_mode = "narrow"

        self.toolbar_density_mode = density_mode
        self._refresh_windows_density_metrics(density_mode)
        label_config = build_toolbar_mode_labels(
            mode,
            density_mode,
            has_results=has_mode_results,
            enabled_word_rules=enabled_word_rules,
        )

        self.btn_open.setText(label_config["open_text"])
        self.btn_scan.setText(label_config["scan_text"])
        self.btn_open.setToolTip(label_config["open_tooltip"])
        self.btn_scan.setToolTip(label_config["scan_tooltip"])

        # v40.1.4（用户反馈 #4/#5）：黑/白/取色遮罩、页面视图、高级设置均为
        # 纯图标按钮（不再随密度切换文字），tooltip 说明含义——节省工具栏空间
        self.rb_black.setText("")
        self.rb_white.setText("")
        self.rb_color.setText("")
        self.rb_color.setToolTip("取色遮罩：自选任意颜色涂抹")
        if hasattr(self, "cb_page_view"):
            self.cb_page_view.setText("")
        # v37.7.11 cp40: 去水印按钮文案随密度调整
        if hasattr(self, "btn_remove_watermark"):
            watermark_text = "去水印" if density_mode != "narrow" else "水印"
            self.btn_remove_watermark.setText(watermark_text)
        self.btn_settings.setText("")
        self.btn_feedback.setText("使用/反馈")
        self.btn_workbench_feedback.setText("使用/反馈")
        self.btn_save.setText(label_config["save_text"])
        self.btn_more.setText("更多")
        self.rb_black.setToolTip("使用黑色遮罩涂抹")
        self.rb_white.setToolTip("使用白色遮罩涂抹")
        if hasattr(self, "cb_page_view"):
            self.cb_page_view.setToolTip("页面视图：多页总览，Ctrl/⌘+滚轮调节每行页数")
        self.btn_fit.setToolTip("按窗口大小适应页面")
        self.btn_fit_utility.setToolTip("按窗口大小适应页面")
        self.btn_settings.setToolTip("高级设置：脱敏规则 / 关键词 / 功能开关")
        self.btn_feedback.setToolTip("查看使用说明或提交反馈")
        self.btn_workbench_feedback.setToolTip("查看使用说明或提交反馈")
        self.btn_save.setToolTip(label_config["save_tooltip"])
        self.btn_more.setToolTip("显示收纳的操作")

        self.btn_settings.setVisible(not is_idle)
        self.btn_feedback.setVisible((not is_idle) and not (is_pdf or is_image_merge))
        self.btn_workbench_feedback.setVisible(is_pdf or is_image_merge)
        self.btn_fit.setVisible(False)
        self.btn_fit_utility.setVisible(is_pdf)
        self.btn_compare_toggle.setVisible(is_word and density_mode != "narrow")
        self.btn_highlight_filter.setVisible(is_word and density_mode != "narrow")


        self._refresh_toolbar_overflow_menu(is_pdf, is_word, density_mode)

        if density_mode == "wide":
            text_button_floor = 82
            utility_button_floor = 98
            compare_button_floor = 104
            more_button_floor = 76
        elif density_mode == "compact":
            text_button_floor = 74
            utility_button_floor = 90
            compare_button_floor = 94
            more_button_floor = 70
        else:
            text_button_floor = 68
            utility_button_floor = 82
            compare_button_floor = 84
            more_button_floor = 64

        if scale >= 1.5:
            text_button_floor += 8
            utility_button_floor += 10
            compare_button_floor += 10
            more_button_floor += 8
        elif scale >= 1.25:
            text_button_floor += 4
            utility_button_floor += 6
            compare_button_floor += 6
            more_button_floor += 4

        # v40.1.4（用户反馈）：btn_settings 已改纯图标按钮，移出文字按钮宽度下限
        # 循环——此前 utility_button_floor(~98px)+extra 把它撑成大空盒盖过紧凑尺寸
        for button in [self.btn_open, self.btn_scan, self.btn_compare_toggle,
                       self.btn_feedback, self.btn_more, self.btn_save]:
            if button.isVisible():
                if button is self.btn_feedback:
                    min_width = utility_button_floor
                    extra = 40
                elif button is self.btn_compare_toggle:
                    min_width = compare_button_floor
                    extra = 34
                elif button is self.btn_more:
                    min_width = more_button_floor
                    extra = 34
                else:
                    min_width = text_button_floor
                    extra = 30
                self._set_toolbar_widget_width(button, min_width=min_width, extra=extra)

        # cp61: 适应页面为纯图标按钮，固定紧凑宽度（不进文字按钮宽度地板循环）
        if self.btn_fit_utility.isVisible():
            self.btn_fit_utility.setFixedWidth(38)

        for toggle in [self.rb_black, self.rb_white, self.rb_color, self.cb_page_view]:
            if toggle.isVisible():
                self._set_toolbar_widget_width(toggle, min_width=52, extra=28)

        # v40.1.5：lbl_zoom/lbl_page 已迁底部迷你条（自定宽），工具栏宽度逻辑不再涉及


        # cp86: 智能脱敏/导出设稳定固定宽（随当前文案），防布局挤压重叠且
        # 使 sizeHint 测量准确参与溢出判定
        for action_btn in [getattr(self, "btn_scan", None), getattr(self, "btn_save", None)]:
            if action_btn is not None and action_btn.isVisible():
                self._set_toolbar_widget_width(action_btn, min_width=64, extra=36)

        self._refresh_toolbar_group_visibility()
        self._enforce_toolbar_min_width()
        # v40.1.5：尺寸定稿后同步提取/截去（此刻撤销按钮已是最终 46×38）
        self._sync_extract_crop_size()
        # cp86: 延帧复测一次——setText/固定宽后同帧 sizeHint 可能未及重算，
        # 布局激活后再校验溢出/最小宽（enforce 幂等，重复调用无副作用）
        QTimer.singleShot(0, self._enforce_toolbar_min_width)
        QTimer.singleShot(0, self._sync_extract_crop_size)

    def _enforce_toolbar_min_width(self):
        """cp73: 根据工具栏内容实际宽度动态设定窗口最小宽度。

        根因：工具栏为 QHBoxLayout，按钮多为固定尺寸；当窗口宽度小于内容
        总宽时，Qt 无法压缩固定按钮，会产生重叠。此处把窗口最小宽度抬到
        工具栏内容所需（含缓冲）。

        cp85: 屏幕可用宽度装不下内容时（min 被屏幕上限截断仍会重叠），
        自适应把低频按钮（使用/反馈 → 去水印）折叠进“更多”菜单；
        宽度恢复后自动展开。另外设 min 后若当前窗口仍窄于目标，主动 resize 拉宽。
        """
        try:
            layout = getattr(self, "toolbar_layout", None)
            if layout is None:
                return

            # 屏幕可用宽度
            avail = 0
            try:
                screen = self.screen()
                if screen is not None:
                    avail = screen.availableGeometry().width()
            except Exception:
                avail = 0

            def _content_needed():
                # sizeHint 与 minimumSize 取大者，防低估；+28 组间缓冲
                sh = layout.sizeHint().width()
                ms = layout.minimumSize().width()
                return max(sh, ms) + 28

            needed = _content_needed()
            if needed <= 28:
                return

            # cp85: 内容超出屏幕可用宽度 → 强制降到 narrow 档重刷一次
            # （narrow 档会缩文案 + 收纳取色/去水印/首末页进“更多”菜单），
            # 防止固定宽按钮在屏幕上限内仍装不下而重叠；标志防递归
            if avail > 0 and needed > avail - 20:
                if not getattr(self, "_toolbar_forced_narrow", False):
                    self._toolbar_forced_narrow = True
                    self._toolbar_forced_narrow_needed = needed  # 自然档需求，供跨屏解除判据
                    self._refresh_toolbar_responsiveness()
                    return
            elif (getattr(self, "_toolbar_forced_narrow", False)
                    and avail - 20 >= getattr(self, "_toolbar_forced_narrow_needed", 10**9)):
                # 换到更宽屏幕/缩放变化，自然档内容已可容纳 → 解除强制并重刷
                self._toolbar_forced_narrow = False
                self._refresh_toolbar_responsiveness()
                return

            base_floor = getattr(self, "_base_min_window_width", 1100)
            target = max(base_floor, needed)
            if avail > 0:
                target = min(target, avail - 20)
            if int(target) != self.minimumWidth():
                self.setMinimumWidth(int(target))
            # cp85: setMinimumWidth 对已最大化/异常状态窗口可能不触发放大，主动拉宽兜底
            if not self.isMaximized() and self.width() < int(target):
                self.resize(int(target), self.height())
        except Exception:
            pass

    def _refresh_workbench_guidance(self, guidance_items):
        """刷新主工作台顶部的下一步引导标签。当前版本默认隐藏，保持上下文条简洁。"""
        if not hasattr(self, "workbench_guidance_labels"):
            return
        for label in self.workbench_guidance_labels:
            label.hide()

    def _refresh_workflow_steps(self, active_index):
        """刷新主页 3 步流程的高亮。

        v40.1.4 修复：v40.1.3 主页重设计后步骤控件为 workflowStepNum/Title/Sub，
        旧实现按 QLabel#workflowStep 设样式匹配不到任何控件（高亮静默失效）。
        现改为对数字圆圈设 flowActive 属性并 repolish，让 QSS 的
        workflowStepNum[flowActive="true"] 真正生效。
        """
        steps = getattr(self, "workflow_step_labels", None) or []
        for index, step_widget in enumerate(steps):
            if step_widget is None:
                continue
            num_label = step_widget.findChild(QLabel, "workflowStepNum")
            if num_label is None:
                continue
            is_active = index == active_index
            if bool(num_label.property("flowActive")) != is_active:
                num_label.setProperty("flowActive", "true" if is_active else "false")
                num_label.style().unpolish(num_label)
                num_label.style().polish(num_label)

    def _create_batch_metric_card(self, title):
        """创建批量 Word 工作台指标卡。"""
        card = QFrame()
        card.setObjectName("batchMetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("batchMetricTitle")
        value_label = QLabel("--")
        value_label.setObjectName("batchMetricValue")
        value_label.setWordWrap(True)
        note_label = QLabel("")
        note_label.setObjectName("batchMetricNote")
        note_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(note_label)
        layout.addStretch()
        return card, value_label, note_label

    def _set_batch_step_style(self, frame, title_label, note_label, state, accent_fg=None, accent_bg=None):
        """按当前批量阶段刷新流程卡片样式。"""
        color_map = {
            "pending": (Theme.LIGHT["text_secondary"], "#FBFCFE", Theme.LIGHT["border"]),
            "active": (Theme.LIGHT["primary"], "#E9F1FB", Theme.LIGHT["primary"]),
            "done": (Theme.LIGHT["success"], "#EAF8F1", Theme.LIGHT["success"]),
        }
        fg, bg, border = color_map.get(state, color_map["pending"])
        if accent_fg and accent_bg and state == "active":
            fg = accent_fg
            bg = accent_bg
            border = accent_fg

        frame.setStyleSheet(
            f"""
            QFrame#batchStepCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            """
        )
        title_label.setStyleSheet(
            f"""
            QLabel#batchStepTitle {{
                color: {fg};
                font-size: 12px;
                font-weight: 700;
                background-color: transparent;
            }}
            """
        )
        note_label.setStyleSheet(
            f"""
            QLabel#batchStepNote {{
                color: {Theme.LIGHT["text_secondary"]};
                font-size: 11px;
                line-height: 1.6;
                background-color: transparent;
            }}
            """
        )

    def _build_batch_summary_text(self, total_selected, replacement_preview):
        """构建批量 Word 工作台摘要文本。

        v40.1.4：纯文本拼装已迁 helpers_word_rules.build_batch_summary_text
        （可独立单测），此处仅收集 MainWindow 状态做适配。
        """
        return build_batch_summary_text(
            self.batch_stage, total_selected, replacement_preview,
            rule_count=self._count_enabled_word_rules(),
            processed=min(self.batch_processed_files, total_selected) if total_selected else 0,
            current_file=self.batch_current_file or "",
            success_count=self.batch_success_count,
            failed_count=self.batch_failed_count,
            last_summary=self.batch_last_summary,
            default_rules=self.word_replace_rules,
        )

    def _count_enabled_general_rules(self):
        """统计启用的通用规则数量。"""
        return len([rule for rule in self.active_rules if isinstance(rule, str) and rule])

    def _count_enabled_word_rules(self):
        """统计启用的 Word 替换规则数量。"""
        normalized = normalize_word_replace_rules(self.word_replace_rules, self.replacement_text)
        return len([item for item in normalized if item.get("enabled", True) and item.get("find")])

    def _has_pdf_redactions(self):
        """当前 PDF 是否已有智能/手动涂抹结果。"""
        return any(data.get("ocr") or data.get("manual") for data in self.page_data.values())

    def _has_word_redactions(self):
        """当前 Word 是否已有智能/手动脱敏结果。"""
        return any(data.get("ocr") or data.get("manual") for data in self.word_data.values())

    def _reset_batch_session_state(self):
        """重置批量 Word 工作台状态。"""
        self.batch_stage = "idle"
        self.batch_selected_files = []
        self.batch_total_files = 0
        self.batch_processed_files = 0
        self.batch_success_count = 0
        self.batch_failed_count = 0
        self.batch_current_file = ""
        self.batch_last_summary = None
        self.batch_result_filter_mode = "all"
        if hasattr(self, "batch_log_list"):
            self.batch_log_list.clear()

    def _append_batch_log(self, text, level="info"):
        """向批量工作台追加一条最近动态。"""
        if not hasattr(self, "batch_log_list") or not text:
            return

        color_map = {
            "info": Theme.LIGHT["text"],
            "success": Theme.LIGHT["success"],
            "warning": Theme.LIGHT["warning"],
            "error": Theme.LIGHT["danger"],
        }

        item = QListWidgetItem(text)
        item.setForeground(QColor(color_map.get(level, Theme.LIGHT["text"])))
        self.batch_log_list.insertItem(0, item)
        while self.batch_log_list.count() > 30:
            self.batch_log_list.takeItem(self.batch_log_list.count() - 1)

    def _reopen_batch_rule_setup(self):
        """用当前已选文档重新进入批量规则确认。"""
        file_paths = list(self.batch_selected_files) if self.batch_selected_files else None
        self.start_batch_replace(file_paths=file_paths)

    def _start_batch_replace_from_workspace(self):
        """从批量工作台重新选择文件。"""
        self.start_batch_replace()

    def _get_batch_failed_inputs(self):
        """提取本轮批量替换失败的输入文件。"""
        summary = self.batch_last_summary if isinstance(self.batch_last_summary, dict) else {}
        failed_items = summary.get("failed", []) if isinstance(summary, dict) else []
        return [item.get("input") for item in failed_items if isinstance(item, dict) and item.get("input")]

    def _get_batch_success_outputs(self):
        """提取本轮批量替换成功输出文件。"""
        summary = self.batch_last_summary if isinstance(self.batch_last_summary, dict) else {}
        success_items = summary.get("success", []) if isinstance(summary, dict) else []
        return [item.get("output") for item in success_items if isinstance(item, dict) and item.get("output")]

    def _retry_failed_batch_files(self):
        """仅重试本轮失败的批量 Word 文档。"""
        failed_files = self._get_batch_failed_inputs()
        if not failed_files:
            QMessageBox.information(self, "提示", "当前没有可重试的失败文档。")
            return
        self.start_batch_replace(file_paths=failed_files)

    def _open_batch_output_location(self):
        """打开本轮批量替换的输出位置。"""
        output_files = self._get_batch_success_outputs()
        if not output_files:
            QMessageBox.information(self, "提示", "当前还没有可打开的输出文件。")
            return

        first_output = output_files[0]
        target_dir = os.path.dirname(first_output) or os.path.dirname(os.path.abspath(first_output))
        if not target_dir or not os.path.isdir(target_dir):
            QMessageBox.warning(self, "提示", "输出目录不存在，可能已被移动或删除。")
            return

        if not QDesktopServices.openUrl(QUrl.fromLocalFile(target_dir)):
            QMessageBox.warning(self, "提示", "无法打开输出目录，请手动前往对应路径查看。")

    def _get_batch_filter_button_style(self, active=False):
        """返回批量结果筛选按钮样式。"""
        theme = Theme.LIGHT
        metrics = getattr(self, "_button_density_metrics", {}) or {}
        font_size = metrics.get("button_font_size", 13) - 1
        padding_v = max(5, metrics.get("button_padding_v", 7) - 2)
        padding_h = max(10, metrics.get("button_padding_h", 14) - 2)
        border_radius = 11

        if active:
            return f"""
                QPushButton {{
                    background-color: #EAF2FC;
                    color: {theme["primary"]};
                    border: 1px solid #B9D3F2;
                    border-radius: {border_radius}px;
                    padding: {padding_v}px {padding_h}px;
                    font-size: {font_size}px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: #E3EEF9;
                    border-color: #AFCBEC;
                }}
                QPushButton:disabled {{
                    background-color: #F0F4F9;
                    color: {theme["text_secondary"]};
                    border-color: {theme["border"]};
                }}
            """

        return f"""
            QPushButton {{
                background-color: #FCFDFF;
                color: {theme["text"]};
                border: 1px solid #E2EAF3;
                border-radius: {border_radius}px;
                padding: {padding_v}px {padding_h}px;
                font-size: {font_size}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #F6FAFE;
                border-color: #C7D8EA;
            }}
            QPushButton:disabled {{
                background-color: #F5F7FA;
                color: {theme["text_secondary"]};
                border-color: {theme["border"]};
            }}
        """

    def _refresh_batch_result_filter_buttons(self):
        """刷新批量结果筛选按钮样式与可用性。"""
        all_rows = build_batch_result_rows(self.batch_last_summary) if self.batch_stage in ("finished", "stopped") else []
        counts = summarize_batch_result_rows(all_rows)
        labels = build_batch_filter_labels(counts, show_counts=self.batch_stage in ("finished", "stopped"))
        buttons = [
            ("all", getattr(self, "btn_batch_filter_all", None)),
            ("success", getattr(self, "btn_batch_filter_success", None)),
            ("failed", getattr(self, "btn_batch_filter_failed", None)),
        ]
        enable_filters = self.batch_stage in ("finished", "stopped") and bool(all_rows)
        for mode, button in buttons:
            if not button:
                continue
            button.setText(labels.get(mode, button.text()))
            button.setEnabled(enable_filters)
            button.setCursor(Qt.CursorShape.PointingHandCursor if enable_filters else Qt.CursorShape.ArrowCursor)
            button.setStyleSheet(self._get_batch_filter_button_style(active=self.batch_result_filter_mode == mode))

    def _set_batch_result_filter_mode(self, mode):
        """切换批量结果筛选模式。"""
        if mode not in {"all", "success", "failed"}:
            mode = "all"
        self.batch_result_filter_mode = mode
        self._refresh_batch_result_filter_buttons()
        self._populate_batch_result_table()

    def _populate_batch_result_table(self):
        """将本轮批量结果表格化展示。"""
        if not hasattr(self, "batch_result_table"):
            return

        table = self.batch_result_table
        all_rows = []
        if self.batch_stage in ("finished", "stopped"):
            all_rows = build_batch_result_rows(self.batch_last_summary)

        result_counts = summarize_batch_result_rows(all_rows)
        if hasattr(self, "lbl_batch_result_meta"):
            if self.batch_stage in ("finished", "stopped"):
                self.lbl_batch_result_meta.setText(
                    f"结果计数：共 {result_counts['total']} 条 · 成功 {result_counts['success']} · 失败 {result_counts['failed']}"
                )
            else:
                self.lbl_batch_result_meta.setText("结果计数：等待本轮结果")
        self._refresh_batch_result_filter_buttons()

        rows = filter_batch_result_rows(all_rows, self.batch_result_filter_mode)

        if not rows:
            placeholder_map = {
                "rule_setup": ("等待开始", "当前还在规则确认阶段", "开始执行后这里会列出每个文档的结果", "先确认规则"),
                "running": ("执行中", "系统正在批量处理文档", "本轮结束后这里会集中列出成功与失败明细", "处理中"),
                "finished": ("已完成", "当前没有可展示的结果行", "如果这轮没有生成结果，请检查日志和弹窗", "查看日志"),
                "stopped": ("已停止", "当前没有可展示的结果行", "可以重试失败文档，或者重新选择文件再执行", "查看日志"),
                "idle": ("待执行", "尚未进入批量模式", "选择多个 Word 文档后，这里会展示完整结果清单", "等待开始"),
            }
            if self.batch_stage in ("finished", "stopped") and all_rows:
                status, document, detail, action = (
                    "筛选为空",
                    "当前筛选条件下没有结果",
                    "你可以切回“全部”，或者改看成功 / 失败结果。",
                    "切换筛选",
                )
            else:
                status, document, detail, action = placeholder_map.get(self.batch_stage, placeholder_map["idle"])
            rows = [{
                "status": status,
                "status_key": "placeholder",
                "document": document,
                "detail": detail,
                "action": action,
                "open_path": "",
                "fallback_dir": "",
            }]

        table.clearContents()
        table.setRowCount(len(rows))

        status_colors = {
            "success": Theme.LIGHT["success"],
            "failed": Theme.LIGHT["danger"],
            "placeholder": Theme.LIGHT["text_secondary"],
        }
        status_backgrounds = {
            "success": "#EAF8F1",
            "failed": "#FDECEC",
            "placeholder": "#F4F7FB",
        }

        for row_index, row_data in enumerate(rows):
            status_item = QTableWidgetItem(row_data.get("status", ""))
            status_item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            status_item.setForeground(QColor(status_colors.get(row_data.get("status_key"), Theme.LIGHT["text"])))
            status_item.setBackground(QColor(status_backgrounds.get(row_data.get("status_key"), "#FBFCFE")))
            status_font = status_item.font()
            status_font.setBold(True)
            status_item.setFont(status_font)
            status_item.setData(Qt.ItemDataRole.UserRole, row_data)

            document_item = QTableWidgetItem(row_data.get("document", ""))
            document_item.setToolTip(row_data.get("open_path", "") or row_data.get("document", ""))

            detail_item = QTableWidgetItem(row_data.get("detail", ""))
            detail_tooltip = row_data.get("detail", "")
            if row_data.get("open_path"):
                detail_tooltip = f"{detail_tooltip}\n{row_data.get('open_path')}"
            detail_item.setToolTip(detail_tooltip.strip())

            action_item = QTableWidgetItem(row_data.get("action", ""))
            action_item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))

            if row_data.get("status_key") == "placeholder":
                placeholder_flags = Qt.ItemFlag.ItemIsEnabled
                for item in [status_item, document_item, detail_item, action_item]:
                    item.setFlags(placeholder_flags)

            table.setItem(row_index, 0, status_item)
            table.setItem(row_index, 1, document_item)
            table.setItem(row_index, 2, detail_item)
            table.setItem(row_index, 3, action_item)

        table.resizeRowsToContents()

    def _open_batch_result_row(self, row, _column):
        """双击批量结果行：成功打开输出，失败定位源文档。"""
        if not hasattr(self, "batch_result_table"):
            return

        row_item = self.batch_result_table.item(row, 0)
        row_data = row_item.data(Qt.ItemDataRole.UserRole) if row_item else None
        if not isinstance(row_data, dict) or row_data.get("status_key") == "placeholder":
            return

        open_path = row_data.get("open_path", "")
        fallback_dir = row_data.get("fallback_dir", "")
        document_name = row_data.get("document", "所选文档")

        if open_path and os.path.exists(open_path):
            if QDesktopServices.openUrl(QUrl.fromLocalFile(open_path)):
                return
        if fallback_dir and os.path.isdir(fallback_dir):
            if QDesktopServices.openUrl(QUrl.fromLocalFile(fallback_dir)):
                return

        QMessageBox.warning(self, "提示", f"无法打开 {document_name} 对应的结果路径，请检查文件是否仍然存在。")

    def _refresh_batch_workspace(self):
        """刷新批量 Word 工作台文案。"""
        if not hasattr(self, "lbl_batch_title"):
            return

        stage_map = {
            "idle": ("批量 Word 工作台", "等待开始", Theme.LIGHT["secondary"], Theme.LIGHT["hover"]),
            "rule_setup": ("批量 Word 文档替换规则模式", "规则确认中", Theme.LIGHT["warning"], "#FFF3E6"),
            "running": ("批量 Word 替换执行模式", "执行中", Theme.LIGHT["primary"], "#E9F1FB"),
            "finished": ("批量 Word 替换结果", "已完成", Theme.LIGHT["success"], "#EAF8F1"),
            "stopped": ("批量 Word 替换结果", "已停止", Theme.LIGHT["danger"], "#FDECEC"),
        }
        title, badge_text, badge_fg, badge_bg = stage_map.get(
            self.batch_stage,
            stage_map["idle"],
        )

        self.lbl_batch_title.setText(title)
        self._set_status_badge_style(self.lbl_batch_stage_badge, badge_fg, badge_bg)
        self.lbl_batch_stage_badge.setText(badge_text)

        total_selected = self.batch_total_files or len(self.batch_selected_files)
        rule_count = self._count_enabled_word_rules()
        replacement_preview = self.replacement_text if isinstance(self.replacement_text, str) and self.replacement_text else "[已脱敏]"
        processed = min(self.batch_processed_files, total_selected) if total_selected else 0
        failed_inputs = self._get_batch_failed_inputs()
        success_outputs = self._get_batch_success_outputs()
        summary_parts = []

        if total_selected:
            summary_parts.append(f"已选文档 {total_selected} 个")
        if rule_count:
            summary_parts.append(f"启用规则 {rule_count} 条")
        summary_parts.append(f"统一替换文本：{replacement_preview}")

        if self.batch_stage == "rule_setup":
            subtitle = "先确认文档替换规则，再开始批量替换。这个阶段不会改动原文件。"
        elif self.batch_stage == "running":
            subtitle = "系统正在逐个处理文档。遇到问题时可以跳过当前文件，或者直接停止任务。"
        elif self.batch_stage in ("finished", "stopped"):
            subtitle = "这一轮批量任务已经结束。你可以查看结果摘要，也可以直接重新选择文件再跑一轮。"
            summary_parts.append(f"成功 {self.batch_success_count} 个")
            summary_parts.append(f"失败 {self.batch_failed_count} 个")
        else:
            subtitle = "批量模式会先进入规则确认，再进入执行。适合多个 Word 文档使用同一套替换规则。"

        self.lbl_batch_subtitle.setText(subtitle)
        self.lbl_batch_meta.setText(" · ".join(summary_parts))

        stage_index_map = {
            "idle": 0,
            "rule_setup": 0,
            "running": 1,
            "finished": 2,
            "stopped": 2,
        }
        active_index = stage_index_map.get(self.batch_stage, 0)
        active_fg = Theme.LIGHT["danger"] if self.batch_stage == "stopped" else None
        active_bg = "#FDECEC" if self.batch_stage == "stopped" else None
        if hasattr(self, "batch_stage_cards"):
            for index, (frame, title_label, note_label) in enumerate(self.batch_stage_cards):
                if index < active_index:
                    state = "done"
                elif index == active_index:
                    state = "active"
                else:
                    state = "pending"
                self._set_batch_step_style(frame, title_label, note_label, state, accent_fg=active_fg, accent_bg=active_bg)

        if hasattr(self, "lbl_batch_metric_files"):
            self.lbl_batch_metric_files.setText(f"{total_selected}" if total_selected else "--")
            self.lbl_batch_metric_files_note.setText("本轮已载入的 Word 文档数量")
        if hasattr(self, "lbl_batch_metric_rules"):
            self.lbl_batch_metric_rules.setText(f"{rule_count}" if rule_count else "--")
            self.lbl_batch_metric_rules_note.setText(f"统一替换文本：{replacement_preview}")
        if hasattr(self, "lbl_batch_metric_progress"):
            progress_value = f"{processed}/{total_selected}" if total_selected else "--"
            progress_note = "规则确认完成后开始执行"
            if self.batch_stage == "running":
                progress_note = f"成功 {self.batch_success_count} · 失败 {self.batch_failed_count}"
            elif self.batch_stage in ("finished", "stopped"):
                progress_note = f"{badge_text} · 全部文件已结束本轮处理"
            self.lbl_batch_metric_progress.setText(progress_value)
            self.lbl_batch_metric_progress_note.setText(progress_note)
        if hasattr(self, "lbl_batch_metric_result"):
            if self.batch_stage in ("finished", "stopped", "running"):
                result_value = f"{self.batch_success_count} / {self.batch_failed_count}"
                result_note = "成功 / 失败"
            else:
                result_value = "待执行"
                result_note = "开始后这里会汇总结果"
            self.lbl_batch_metric_result.setText(result_value)
            self.lbl_batch_metric_result_note.setText(result_note)

        if self.batch_current_file:
            self.lbl_batch_current_file.setText(f"当前文件：{self.batch_current_file}")
        elif total_selected:
            self.lbl_batch_current_file.setText("当前文件：等待开始处理")
        else:
            self.lbl_batch_current_file.setText("当前文件：尚未选择批量文档")

        if hasattr(self, "batch_summary_browser"):
            self.batch_summary_browser.setPlainText(self._build_batch_summary_text(total_selected, replacement_preview))
        if hasattr(self, "lbl_batch_result_hint"):
            if self.batch_stage in ("finished", "stopped"):
                self.lbl_batch_result_hint.setText("结果清单（双击成功行可打开输出，双击失败行可定位原文件）")
            elif self.batch_stage == "running":
                self.lbl_batch_result_hint.setText("结果清单（处理中，完成后这里会列出每个文档）")
            else:
                self.lbl_batch_result_hint.setText("结果清单")
        self._populate_batch_result_table()

        self.btn_batch_edit_rules.setEnabled(bool(self.batch_selected_files) and self.active_task_type != "batch_replace")
        self.btn_batch_pick_files.setEnabled(self.active_task_type != "batch_replace")
        show_result_actions = self.batch_stage in ("finished", "stopped")
        self.btn_batch_retry_failed.setVisible(show_result_actions)
        self.btn_batch_open_output.setVisible(show_result_actions)
        self.btn_batch_retry_failed.setEnabled(bool(failed_inputs) and self.active_task_type != "batch_replace")
        self.btn_batch_open_output.setEnabled(bool(success_outputs) and self.active_task_type != "batch_replace")

    def _refresh_merge_workspace(self):
        """刷新图片合并模式提示。"""
        if not hasattr(self, "lbl_merge_meta"):
            return

        total_images = self.image_merge_total_images
        in_progress = self.image_merge_in_progress and total_images > 0

        if in_progress:
            self.lbl_merge_title.setText("图片正在合并为 PDF")
            self.lbl_merge_subtitle.setText("系统会按当前顺序生成 PDF，完成后自动进入 PDF 脱敏工作台。")
            self.lbl_merge_meta.setText(
                f"当前共 {total_images} 张图片。合并完成后会自动打开生成的 PDF，继续进入 PDF 脱敏流程。"
            )
            self._set_status_badge_style(self.lbl_merge_stage_badge, Theme.LIGHT["primary"], "#E9F1FB")
            self.lbl_merge_stage_badge.setText("合并中")
            stage_states = ["done", "active", "pending"]
            if hasattr(self, "lbl_merge_metric_images"):
                self.lbl_merge_metric_images.setText(str(total_images))
                self.lbl_merge_metric_images_note.setText("当前已载入待合并的图片数量")
            if hasattr(self, "lbl_merge_metric_status"):
                self.lbl_merge_metric_status.setText("进行中")
                self.lbl_merge_metric_status_note.setText("底部进度条会同步显示合并进度")
            if hasattr(self, "lbl_merge_metric_next"):
                self.lbl_merge_metric_next.setText("PDF 脱敏")
                self.lbl_merge_metric_next_note.setText("完成后自动进入 PDF 脱敏工作台")
        else:
            self.lbl_merge_title.setText("图片合并为 PDF")
            self.lbl_merge_subtitle.setText("系统会先整理图片顺序，再生成 PDF 并自动打开工作台。")
            self.lbl_merge_meta.setText("当前还没有开始合并。")
            self._set_status_badge_style(self.lbl_merge_stage_badge, Theme.LIGHT["warning"], "#FFF3E6")
            self.lbl_merge_stage_badge.setText("等待开始")
            stage_states = ["active", "pending", "pending"]
            if hasattr(self, "lbl_merge_metric_images"):
                self.lbl_merge_metric_images.setText(str(total_images) if total_images else "--")
                self.lbl_merge_metric_images_note.setText("拖入多张图片后会自动进入该工作台")
            if hasattr(self, "lbl_merge_metric_status"):
                self.lbl_merge_metric_status.setText("未开始")
                self.lbl_merge_metric_status_note.setText("当前尚未开始合并图片")
            if hasattr(self, "lbl_merge_metric_next"):
                self.lbl_merge_metric_next.setText("等待图片")
                self.lbl_merge_metric_next_note.setText("拖入图片后开始合并并进入 PDF 工作台")

        for index, state in enumerate(stage_states):
            if index < len(getattr(self, "merge_stage_cards", [])):
                frame, title_label, note_label = self.merge_stage_cards[index]
                self._set_batch_step_style(frame, title_label, note_label, state)

    def _on_extract_toggle(self, checked):
        """cp123: 提取按钮 toggle 处理：进入/退出提取模式（含互斥 + 退出确认）。"""
        if checked:
            # 互斥：取消截去按钮选中
            self.btn_crop.blockSignals(True)
            self.btn_crop.setChecked(False)
            self.btn_crop.blockSignals(False)
            if getattr(self, "_crop_active", False):
                self.exit_crop_mode()
            self.enter_extract_mode()
        else:
            # 退出前检查未保存
            if self._extract_has_unsaved():
                reply = QMessageBox.question(
                    self, "退出提取模式",
                    "当前有未导出的提取内容，退出后将丢失。\n确定退出？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    # 取消退出：恢复选中态
                    self.btn_extract.blockSignals(True)
                    self.btn_extract.setChecked(True)
                    self.btn_extract.blockSignals(False)
                    return
            self.exit_extract_mode()

    def _on_crop_toggle(self, checked):
        """cp123: 截去按钮 toggle 处理：进入/退出截去模式（含互斥 + 退出确认）。"""
        if checked:
            # 互斥：取消提取按钮选中
            self.btn_extract.blockSignals(True)
            self.btn_extract.setChecked(False)
            self.btn_extract.blockSignals(False)
            if getattr(self, "_extract_active", False):
                self.exit_extract_mode()
            self.enter_crop_mode()
        else:
            self.exit_crop_mode()

    def _extract_has_unsaved(self):
        """cp123: 提取模式是否有未导出的内容（供退出确认判断）。"""
        segs = getattr(self, "_extract_segments", None)
        return bool(segs and any(p for p in segs))

    def _refresh_workbench_context(self):
        """刷新主工作台标题、步骤和下一步提示。"""
        if not hasattr(self, "lbl_workbench_title"):
            return

        mode = self.current_ui_mode
        active_step = 0
        focus_text = "第 1 步"
        focus_fg = Theme.LIGHT["primary"]
        focus_bg = "#E9F1FB"
        guidance_items = build_workbench_guidance("idle")
        show_focus_badge = mode != "idle"
        show_workbench_subtitle = mode != "idle"

        if mode == "pdf" and self.doc:
            total_pages = len(self.doc)
            current_page = (self.current_page + 1) if self.current_page is not None else 0
            has_results = self._has_pdf_redactions()
            active_step = 3 if has_results else 2
            focus_text = "PDF 脱敏"
            show_focus_badge = False
            self.lbl_workbench_title.setText("PDF 脱敏工作台")
            self.lbl_workbench_subtitle.setText(
                f"{os.path.basename(self.file_path or '')} · {current_page} / {total_pages} 页 · 黑 / 白即时切换"
            )
            guidance_items = build_workbench_guidance("pdf", has_results=has_results)
        elif mode == "word" and self.word_doc:
            paragraph_count = len(self.word_doc.paragraphs)
            table_count = len(self.word_doc.tables)
            has_results = self._has_word_redactions() or self._count_enabled_word_rules() > 0
            active_step = 3 if has_results else 2
            focus_text = "Word 替换"
            focus_fg = Theme.LIGHT["success"]
            focus_bg = "#EAF8F1"
            show_focus_badge = False
            compare_status = "已开启" if self.word_compare_mode else "已隐藏"
            self.lbl_workbench_title.setText("Word 替换工作台")
            self.lbl_workbench_subtitle.setText(
                f"{os.path.basename(self.file_path or '')} · 段落 {paragraph_count} · 表格 {table_count} · 对比 {compare_status}"
            )
            guidance_items = build_workbench_guidance("word", has_results=has_results, compare_mode=self.word_compare_mode)
        elif mode == "batch":
            if self.batch_stage == "running":
                active_step = 2
                focus_text = "批量执行中"
                focus_fg = Theme.LIGHT["primary"]
                focus_bg = "#E9F1FB"
                summary_text = (
                    f"已选 {self.batch_total_files or len(self.batch_selected_files)} 个文档 · "
                    f"成功 {self.batch_success_count} · 失败 {self.batch_failed_count}"
                )
            elif self.batch_stage in ("finished", "stopped"):
                active_step = 4
                focus_text = "批量结果"
                focus_fg = Theme.LIGHT["success"] if self.batch_stage == "finished" else Theme.LIGHT["danger"]
                focus_bg = "#EAF8F1" if self.batch_stage == "finished" else "#FDECEC"
                summary_text = (
                    f"已选 {self.batch_total_files or len(self.batch_selected_files)} 个文档 · "
                    f"成功 {self.batch_success_count} · 失败 {self.batch_failed_count}"
                )
            else:
                active_step = 1
                focus_text = "规则确认"
                focus_fg = Theme.LIGHT["warning"]
                focus_bg = "#FFF3E6"
                summary_text = (
                    f"已选 {self.batch_total_files or len(self.batch_selected_files)} 个文档 · "
                    f"启用规则 {self._count_enabled_word_rules()} 条"
                )

            self.lbl_workbench_title.setText("批量 Word 工作台")
            self.lbl_workbench_subtitle.setText(summary_text)
            guidance_items = build_workbench_guidance("batch", batch_stage=self.batch_stage)
        elif mode == "image_merge":
            active_step = 2
            focus_text = "图片合并"
            self.lbl_workbench_title.setText("图片合并为 PDF")
            self.lbl_workbench_subtitle.setText(f"当前待合并图片：{self.image_merge_total_images} 张 · 完成后自动进入 PDF 脱敏模式")
            guidance_items = build_workbench_guidance("image_merge")
        else:
            self.lbl_workbench_title.setText("欢迎使用 PrivacyGuard")
            self.lbl_workbench_subtitle.setText("拖拽或打开文件即可开始处理。")

        self.lbl_workbench_focus.setText(focus_text)
        self._set_status_badge_style(self.lbl_workbench_focus, focus_fg, focus_bg)
        self.lbl_workbench_focus.setVisible(show_focus_badge)
        self.lbl_workbench_subtitle.setVisible(show_workbench_subtitle)
        self._refresh_workbench_guidance(guidance_items)
        self._refresh_workflow_steps(active_step)
        self._refresh_batch_workspace()
        self._refresh_merge_workspace()

    def _apply_button_variant(self, btn, style_type):
        """根据当前主题为已创建按钮切换样式。"""
        if not btn:
            return
        btn.setProperty("btn_style", style_type)
        btn.setStyleSheet(self._get_button_style(style_type))

    def _refresh_mode_badge(self):
        """刷新顶部模式标识，让用户一眼知道当前在处理什么。"""
        if not hasattr(self, "lbl_mode_badge"):
            return

        mode_map = {
            "idle": ("等待导入", Theme.LIGHT["secondary"], Theme.LIGHT["hover"]),
            "pdf": ("PDF 脱敏模式", Theme.LIGHT["primary"], "#E9F1FB"),
            "word": ("Word 替换模式", Theme.LIGHT["success"], "#EAF8F1"),
            "batch": ("批量 Word 替换", Theme.LIGHT["warning"], "#FFF3E6"),
            "image_merge": ("图片合并中", Theme.LIGHT["primary"], "#E9F1FB"),
        }
        text, fg, bg = mode_map.get(
            self.current_ui_mode,
            ("等待导入", Theme.LIGHT["secondary"], Theme.LIGHT["hover"]),
        )
        self.lbl_mode_badge.setText(text)
        self.lbl_mode_badge.setStyleSheet(
            f"""
            QLabel#modeBadge {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {Theme.LIGHT["border"]};
                border-radius: 14px;
                padding: 6px 12px;
                font-size: {Theme.FONT_SIZE_SMALL}px;
                font-weight: 700;
            }}
            """
        )

    def _set_ui_mode(self, mode):
        """集中管理不同业务模式下的工具显隐，避免 PDF / Word 控件混杂。"""
        self.current_ui_mode = mode
        is_idle = mode == "idle"
        is_pdf = mode == "pdf"
        is_word = mode == "word"
        is_batch = mode == "batch"
        is_image_merge = mode == "image_merge"

        pdf_widgets = [
            self.rb_black, self.rb_white, self.btn_fit_utility,
            self.cb_page_view,
            self.btn_undo, self.btn_redo,  # cp83: 撤销/恢复仅 PDF/图片模式
            self.btn_encrypt,  # cp72: 加密仅 PDF/图片模式可用（Word 隐藏）
        ]
        for widget in pdf_widgets:
            widget.setVisible(is_pdf)
        # v40.1.6：缩放/翻页已迁卡片底缘嵌入状态栏——由本方法整体控制（单一显隐源）
        if hasattr(self, "doc_bottom_bar"):
            self.doc_bottom_bar.setVisible(is_pdf)
        self.btn_fit.setVisible(False)
        # cp67: 非 PDF 模式强制退出页面视图
        if not is_pdf and getattr(self, "page_view_mode", False):
            self.set_page_view_mode(False)

        word_widgets = [self.btn_compare_toggle]
        for widget in word_widgets:
            widget.setVisible(is_word)

        show_scan = is_pdf or is_word
        show_save = is_pdf or is_word
        self.btn_open.setVisible(not is_idle)
        self.btn_scan.setVisible(show_scan)
        self.btn_save.setVisible(show_save)
        # cp122: 提取/截去按钮仅在 PDF 模式可见，启用需有文档
        if hasattr(self, "btn_extract"):
            self.btn_extract.setVisible(is_pdf)
            self.btn_extract.setEnabled(is_pdf and self.doc is not None
                                        and self.doc_type == 'pdf')
        if hasattr(self, "btn_crop"):
            self.btn_crop.setVisible(is_pdf)
            self.btn_crop.setEnabled(is_pdf and self.doc is not None
                                     and self.doc_type == 'pdf')
        # cp81: 搜索按钮 PDF/Word 均可用；切模式时非目标模式自动收起面板
        self.btn_search.setVisible(is_pdf or is_word)
        if not (is_pdf or is_word) and hasattr(self, "search_panel"):
            self.search_panel.hide()
        # cp_bookmark: 书签按钮仅 PDF 模式可见；切模式时收起面板
        if hasattr(self, "btn_bookmark"):
            self.btn_bookmark.setVisible(is_pdf)
        if not is_pdf and hasattr(self, "bookmark_panel"):
            self.bookmark_panel.hide()

        if is_batch:
            self.btn_scan.setVisible(False)
            self.btn_save.setVisible(False)

        if is_idle:
            self.btn_scan.setVisible(False)
            self.btn_save.setVisible(False)

        if hasattr(self, "idle_workspace_container"):
            self.idle_workspace_container.setVisible(is_idle)
        if hasattr(self, "batch_workspace_container"):
            self.batch_workspace_container.setVisible(is_batch)
        if hasattr(self, "merge_workspace_container"):
            self.merge_workspace_container.setVisible(is_image_merge)
        if hasattr(self, "canvas_container"):
            self.canvas_container.setVisible(is_pdf)
        if hasattr(self, "word_compare_container"):
            self.word_compare_container.setVisible(is_word)
        if hasattr(self, "workbench_panel"):
            self.workbench_panel.setVisible(not is_idle)
        if hasattr(self, "toolbar"):
            self.toolbar.setVisible(not is_idle)
        if hasattr(self, "progress_shell"):
            # v40.1.5（用户反馈）：进度条区不常驻——仅任务进行时出现（start 时 show、
            # 完成时 hide），平时彻底不占底部空间（此前非空闲常驻 ~24px 空条）
            self.progress_shell.setVisible(False)

        self._refresh_mode_badge()
        self._refresh_word_compare_toggle()
        self._refresh_toolbar_responsiveness()
        self._refresh_workbench_context()
        self._refresh_info_bar_visibility()

    def eventFilter(self, obj, event):
        """v40.1.5：macOS 触控板双指捏合缩放（Windows 为 Ctrl+滚轮）。

        Qt 把捏合派发为 QNativeGestureEvent（不进 wheelEvent），且派发目标
        随焦点漂移——qApp 级过滤器统一拦截：单页/双页视图走 handle_zoom_request
        （与 Ctrl+滚轮同路径，含边界阻尼与页面视图切换语义）；页面视图内
        捏合调列数（与 Ctrl+滚轮一致）。仅 PDF 模式生效。
        """
        if (event.type() == QEvent.Type.NativeGesture
                and self.doc is not None
                and getattr(self, "current_ui_mode", "") == "pdf"):
            try:
                # PyQt6 枚举成员名随版本为全称 ZoomNativeGesture（旧文档写 Zoom），
                # 两名兼容取用；此前 AttributeError 被吞导致捏合无声失效
                _zoom = getattr(Qt.NativeGestureType, "ZoomNativeGesture",
                                getattr(Qt.NativeGestureType, "Zoom", None))
                if _zoom is not None and event.gestureType() == _zoom:
                    # v40.1.5 根因修复：本版 PyQt6 的 delta() 返回 QPointF（触点
                    # 位移对象，非数值，bool 为 False → 静默跳过）；真实捏合增量
                    # 在 value()（实测 0.07/事件量级）
                    delta = event.value()
                    if delta:
                        if getattr(self, "page_view_mode", False):
                            self._on_grid_ctrl_wheel(1 if delta > 0 else -1)
                        else:
                            self.handle_zoom_request(max(-0.5, min(0.5, delta * 2.0)))
                        return True
            except Exception as e:
                logger.warning("[手势] 捏合缩放处理异常: %s", type(e).__name__)
        return super().eventFilter(obj, event)

    def _sync_extract_crop_size(self):
        """v40.1.5（用户反馈）：提取/截去与撤销/重做逐像素同规格。

        参考尺寸（如 46×38）来自撤销按钮在全部尺寸逻辑（含 QSS 最小宽、
        enforce 复测）之后的实测值——须在密度函数末尾及延帧复测后调用。
        """
        ref = getattr(self, "btn_undo", None)
        if ref is None or ref.width() <= 0:
            return
        for name in ("btn_extract", "btn_crop"):
            b = getattr(self, name, None)
            if b is not None:
                b.setMinimumSize(ref.width(), ref.height())
                b.setMaximumSize(ref.width(), ref.height())

    def _sync_ui_mode(self):
        """根据当前运行状态推导界面模式。"""
        if self.active_task_type == "batch_replace":
            self._set_ui_mode("batch")
        elif self.image_merge_in_progress:
            self._set_ui_mode("image_merge")
        elif self.doc:
            self._set_ui_mode("pdf")
        elif self.word_doc:
            self._set_ui_mode("word")
        elif self.batch_stage != "idle" and self.batch_selected_files:
            self._set_ui_mode("batch")
        else:
            self._set_ui_mode("idle")

    def _refresh_word_compare_toggle(self):
        """刷新 Word 对比预览按钮状态。"""
        if not hasattr(self, "btn_compare_toggle"):
            return

        if not self.word_doc:
            self.btn_compare_toggle.setEnabled(False)
            self.btn_compare_toggle.setText("对比预览")
            self.btn_compare_toggle.setToolTip("请先打开 Word 文档")
            self._apply_button_variant(self.btn_compare_toggle, "secondary")
            self._refresh_toolbar_responsiveness()
            return

        has_candidates = self._has_word_replacement_candidates()
        self.btn_compare_toggle.setEnabled(has_candidates)
        if not has_candidates:
            self.btn_compare_toggle.setText(
                "对比预览（暂无结果）" if self.toolbar_density_mode == "wide" else "暂无对比"
            )
            self.btn_compare_toggle.setToolTip("设置替换规则或执行智能替换后，可查看对比预览")
            self._apply_button_variant(self.btn_compare_toggle, "secondary")
            self._refresh_toolbar_responsiveness()
            return

        if self.word_compare_user_hidden:
            self.btn_compare_toggle.setText(
                "显示对比预览" if self.toolbar_density_mode == "wide" else "显示对比"
            )
            self.btn_compare_toggle.setToolTip("显示右侧替换后预览")
            self._apply_button_variant(self.btn_compare_toggle, "secondary")
        else:
            self.btn_compare_toggle.setText(
                "隐藏对比预览" if self.toolbar_density_mode == "wide" else "隐藏对比"
            )
            self.btn_compare_toggle.setToolTip("隐藏右侧替换后预览")
            self._apply_button_variant(self.btn_compare_toggle, "primary")
        self._refresh_toolbar_responsiveness()

    def toggle_word_compare_preview(self):
        """允许用户主动隐藏或恢复 Word 右侧对比预览。"""
        if not self.word_doc:
            QMessageBox.information(self, "提示", "请先打开 Word 文档。")
            return

        if not self._has_word_replacement_candidates():
            QMessageBox.information(
                self,
                "提示",
                "当前还没有可对比的替换结果。\n请先设置替换规则或执行智能脱敏。"
            )
            self._refresh_word_compare_toggle()
            return

        self.word_compare_user_hidden = not self.word_compare_user_hidden
        self.render_word_preview()
        self._refresh_word_compare_toggle()

    def create_btn(self, text, func, enabled=True, style="primary", width=None, tooltip=""):
        """创建现代化按钮

        Args:
            text: 按钮文本
            func: 点击回调
            enabled: 是否启用
            style: 样式类型 (primary, secondary, success, danger, icon)
            width: 固定宽度（可选）
            tooltip: 工具提示
        """
        btn = QPushButton(text)
        btn.clicked.connect(func)
        btn.setEnabled(enabled)
        if tooltip:
            btn.setToolTip(tooltip)
        if width:
            btn.setFixedWidth(width)

        # 设置游标
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoDefault(False)
        btn.setDefault(False)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # 应用样式
        btn.setStyleSheet(self._get_button_style(style))

        # 保存样式类型以便主题切换
        btn.setProperty("btn_style", style)

        return btn

    def _create_toolbar_group(self, object_name="toolbarGroup"):
        """创建工具栏分组容器，降低一整排独立按钮的视觉噪音。"""
        group = QFrame()
        group.setObjectName(object_name)
        layout = QHBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        return group, layout

    def _create_toolbar_divider(self):
        divider = QFrame()
        divider.setObjectName("toolbarDivider")
        divider.setFixedWidth(1)
        divider.setMinimumHeight(24)
        return divider

    def _get_cancel_scan_button_style(self, height):
        """cp66: 进度条右侧“取消”按钮专用紧凑样式。

        按钮与进度条同高（24-28px 固定），通用 secondary 样式的上下
        padding（≈4-7px）叠加 13px 字号会超出固定高度，导致“取消”二字
        上下被裁切；此处上下 padding 归零、字号随高度收敛，保证垂直居中完整显示。
        """
        theme = Theme.LIGHT
        font_size = 12 if height <= 26 else 13
        radius = min(Theme.BUTTON_RADIUS, max(4, height // 2))
        return f"""
            QPushButton {{
                background-color: #FBFCFE;
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: {radius}px;
                padding: 0px 8px;
                font-size: {font_size}px;
                font-weight: 600;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {theme["hover"]};
                border-color: {theme["primary"]};
            }}
            QPushButton:disabled {{
                background-color: #F5F7FA;
                color: {theme["text_secondary"]};
                border-color: {theme["border"]};
            }}
        """

    def _get_button_style(self, style_type):
        """获取按钮样式（浅色主题）"""
        theme = Theme.LIGHT
        metrics = getattr(self, "_button_density_metrics", {}) or {}
        button_font_size = metrics.get("button_font_size", 13)
        button_padding_v = metrics.get("button_padding_v", 7)
        button_padding_h = metrics.get("button_padding_h", 14)
        icon_font_size = metrics.get("icon_font_size", 14)
        icon_padding_v = metrics.get("icon_padding_v", 4)
        icon_padding_h = metrics.get("icon_padding_h", 8)
        icon_min = metrics.get("icon_min", 28)

        styles = {
            "primary": f"""
                QPushButton {{
                    background-color: {theme["primary"]};
                    color: white;
                    border: none;
                    border-radius: {Theme.BUTTON_RADIUS}px;
                    padding: {button_padding_v}px {button_padding_h}px;
                    font-weight: 600;
                    font-size: {button_font_size}px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.adjust_color(theme["primary"], -15)};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.adjust_color(theme["primary"], -25)};
                }}
                QPushButton:disabled {{
                    background-color: {theme["border"]};
                    color: {theme["text_secondary"]};
                }}
            """,
            "secondary": f"""
                QPushButton {{
                    background-color: #FBFCFE;
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: {Theme.BUTTON_RADIUS}px;
                    padding: {button_padding_v}px {button_padding_h}px;
                    font-size: {button_font_size}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {theme["hover"]};
                    border-color: {theme["primary"]};
                }}
                QPushButton:disabled {{
                    background-color: #F5F7FA;
                    color: {theme["text_secondary"]};
                    border-color: {theme["border"]};
                }}
            """,
            "idle_primary": f"""
                QPushButton {{
                    background-color: {theme["primary"]};
                    color: white;
                    border: none;
                    border-radius: 14px;
                    padding: {button_padding_v + 2}px {button_padding_h + 6}px;
                    font-size: {max(button_font_size, 14)}px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: {Theme.adjust_color(theme["primary"], -12)};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.adjust_color(theme["primary"], -22)};
                }}
                QPushButton:disabled {{
                    background-color: {theme["border"]};
                    color: {theme["text_secondary"]};
                }}
            """,
            "idle_secondary": f"""
                QPushButton {{
                    background-color: #F5F8FC;
                    color: {theme["text"]};
                    border: 1px solid #D7E2EE;
                    border-radius: 14px;
                    padding: {button_padding_v + 2}px {button_padding_h + 4}px;
                    font-size: {max(button_font_size, 14)}px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: #EEF4FA;
                    border-color: #C9D9EA;
                }}
                QPushButton:pressed {{
                    background-color: #E6EEF7;
                    border-color: #C1D2E4;
                }}
                QPushButton:disabled {{
                    background-color: #F5F7FA;
                    color: {theme["text_secondary"]};
                    border-color: {theme["border"]};
                }}
            """,
            "success": f"""
                QPushButton {{
                    background-color: {theme["success"]};
                    color: white;
                    border: none;
                    border-radius: {Theme.BUTTON_RADIUS}px;
                    padding: {button_padding_v}px {button_padding_h}px;
                    font-weight: 600;
                    font-size: {button_font_size}px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.adjust_color(theme["success"], -15)};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.adjust_color(theme["success"], -25)};
                }}
                QPushButton:disabled {{
                    background-color: {theme["border"]};
                    color: {theme["text_secondary"]};
                }}
            """,
            "danger": f"""
                QPushButton {{
                    background-color: {theme["danger"]};
                    color: white;
                    border: none;
                    border-radius: {Theme.BUTTON_RADIUS}px;
                    padding: {button_padding_v + 1}px {button_padding_h + 2}px;
                    font-weight: 600;
                    font-size: {max(button_font_size, Theme.FONT_SIZE_NORMAL)}px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.adjust_color(theme["danger"], -15)};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.adjust_color(theme["danger"], -25)};
                }}
            """,
            "icon": f"""
                QPushButton {{
                    background-color: #FBFCFE;
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 8px;
                    padding: {icon_padding_v}px {icon_padding_h}px;
                    min-width: {icon_min}px;
                    min-height: {icon_min}px;
                    font-size: {icon_font_size}px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: {theme["hover"]};
                    border-color: {theme["primary"]};
                }}
                QPushButton:pressed {{
                    background-color: {theme["pressed"]};
                }}
                QPushButton:disabled {{
                    background-color: #F5F7FA;
                    color: {theme["text_secondary"]};
                    border-color: {theme["border"]};
                }}
            """,
            "toggle": f"""
                QPushButton {{
                    background-color: #FBFCFE;
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 9px;
                    padding: {button_padding_v}px {button_padding_h}px;
                    font-size: {button_font_size}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {theme["hover"]};
                    border-color: {theme["primary"]};
                }}
                QPushButton:checked {{
                    background-color: #E9F1FB;
                    color: {theme["primary"]};
                    border-color: #B8D0EA;
                }}
                QPushButton:pressed {{
                    background-color: {theme["pressed"]};
                }}
                QPushButton:disabled {{
                    background-color: #F5F7FA;
                    color: {theme["text_secondary"]};
                    border-color: {theme["border"]};
                }}
            """,
        }

        # cp61: outline:none 抑制 Windows 焦点矩形框（焦点框不随圆角，
        # 表现为“描边与按钮不匹配/大小不等/毛边”），对所有按钮变体统一生效
        return styles.get(style_type, styles["primary"]) + "\nQPushButton { outline: none; }"

    def handle_zoom_request(self, delta):
        """单页视图缩放。

        cp68: 新增“缩小进入页面视图”路径，带手势阻尼——同一滚轮手势内缩小到
        最小比例后停在边界；松开 Ctrl / 停止滚动后的新手势再缩小，才跨越分界
        进入页面（多页网格）视图。
        """
        now = time.time()
        new_gesture = (now - self._ctrl_zoom_last_ts) > self._ZOOM_GESTURE_GAP
        self._ctrl_zoom_last_ts = now
        # cp68: 单页视图下已到最小比例仍缩小 → 边界阻尼 + 新手势进入页面视图
        # cp131: 提取/截去模式下禁止进入页面视图（会破坏模式上下文）
        if (delta < 0 and self.doc and not getattr(self, "page_view_mode", False)
                and self.zoom_level <= ZOOM_MIN + 1e-6
                and not getattr(self, "_extract_active", False)
                and not getattr(self, "_crop_active", False)):
            if new_gesture:
                # 从单页缩小进入：从 2 列起步（刚越过 1 列分界）
                if self.grid_columns <= 1:
                    self.grid_columns = 2
                self.set_page_view_mode(True)
            return
        new_zoom = self.zoom_level + delta
        if new_zoom < ZOOM_MIN: new_zoom = ZOOM_MIN
        if new_zoom > ZOOM_MAX: new_zoom = ZOOM_MAX
        self.zoom_level = new_zoom
        self.render_view()
        # cp131: 提取模式下缩放后同步刷新右侧结果预览（用新的 zoom_level 重渲染）
        if getattr(self, "_extract_active", False) and hasattr(self, "_refresh_extract_preview"):
            self._refresh_extract_preview()

    def toggle_dual_view(self, checked):
        """
        v22.9: 简化的单/双页切换 - 保持 canvas_container 为固定 widget
        只隐藏/显示内部的 canvas
        """
        self.dual_view = checked

        if checked:
            # 双页模式：显示两个 canvas
            self.canvas_right.show()
        else:
            # 单页模式：只显示 left canvas
            self.canvas_right.hide()

        self.render_view()

    def _build_color_palette_widget(self):
        """构造取色遮罩的色板面板（初始隐藏，由 rb_color 切换显示）。

        v37.7.10 cp39: 内联展开在 toolbar 与 scroll 之间，包含：
          - 8 个常用色色块（22×22）
          - 自定义色值输入 QLineEdit + 应用按钮（支持 #RRGGBB + 回车）
          - 全屏取色器按钮
        """
        panel = QFrame()
        panel.setObjectName("colorPalettePanel")
        panel.setStyleSheet(
            "#colorPalettePanel {"
            " background-color: #FFFFFF;"
            " border: 1px solid #D0D0D0;"
            " border-radius: 8px;"
            " margin: 4px 8px;"
            "}"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(10, 8, 10, 8)
        panel_layout.setSpacing(6)

        # 常用色色板
        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(6)
        self._color_swatch_buttons = []
        common_colors = [
            ("#000000", "黑"),
            ("#FFFFFF", "白"),
            ("#C81E1E", "红"),
            ("#505050", "深灰"),
            ("#B4B4B4", "浅灰"),
            ("#14285A", "深蓝"),
            ("#1E5028", "暗绿"),
            ("#C8781E", "橙"),
        ]
        for hex_code, name in common_colors:
            swatch = QPushButton()
            swatch.setFixedSize(22, 22)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.setToolTip(f"{name} {hex_code}")
            # 用 % 格式化避免 f-string CSS 花括号误判（test_fstring_safety）
            swatch.setStyleSheet(
                "QPushButton { background-color: %s; border: 1px solid #888;"
                " border-radius: 4px; }"
                "QPushButton:hover { border: 2px solid #1A73E8; }" % hex_code
            )
            swatch.clicked.connect(lambda _, c=hex_code: self._apply_custom_color(QColor(c)))
            swatch_row.addWidget(swatch)
            self._color_swatch_buttons.append(swatch)
        swatch_row.addStretch()
        panel_layout.addLayout(swatch_row)

        # 自定义色值输入行
        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        input_row.addWidget(QLabel("自定义:"))
        self.color_hex_input = QLineEdit()
        self.color_hex_input.setPlaceholderText("#RRGGBB")
        self.color_hex_input.setMaxLength(7)
        self.color_hex_input.returnPressed.connect(self._apply_hex_input)
        input_row.addWidget(self.color_hex_input)
        apply_btn = self.create_btn("应用", self._apply_hex_input, style="secondary")
        input_row.addWidget(apply_btn)
        panel_layout.addLayout(input_row)

        # 全屏取色器
        picker_row = QHBoxLayout()
        picker_row.setSpacing(6)
        self.btn_screen_picker = self.create_btn(
            "全屏取色", self.pick_screen_color, style="secondary",
            tooltip="点击屏幕任意位置取色"
        )
        picker_row.addWidget(self.btn_screen_picker)
        picker_row.addStretch()
        panel_layout.addLayout(picker_row)

        return panel

    def _apply_hex_input(self):
        """从 color_hex_input 读取色值并应用（带格式校验）。"""
        text = self.color_hex_input.text().strip()
        if not re.match(r"^#[0-9A-Fa-f]{6}$", text):
            self.color_hex_input.setToolTip("格式错误，请输入 #RRGGBB（如 #FF8800）")
            return
        self._apply_custom_color(QColor(text))

    def _toggle_color_palette(self):
        """rb_color 按钮切换：展开/收起色板面板。

        v37.7.12 cp42: 再次点击已展开的 rb_color 按钮收起面板。
        QButtonGroup 互斥模式下已选中的按钮再点击不会取消选中，
        因此根据面板当前可见性切换，而不是依赖 isChecked()。
        """
        if not hasattr(self, "color_palette_widget"):
            return
        if self.color_palette_widget.isVisible():
            # 面板已可见 → 收起（保留 current_color 不变）
            self.color_palette_widget.setVisible(False)
        else:
            # 面板不可见 → 展开
            self.color_palette_widget.setVisible(True)
            self.rb_color.setChecked(True)
            cur = self.current_color
            if cur and cur.isValid():
                self.color_hex_input.setText(cur.name().upper())

    def _apply_custom_color(self, color):
        """应用自定义颜色作为遮罩色（色板点击 / hex 输入 / 全屏取色 共用入口）。"""
        if not color or not color.isValid():
            return
        self.current_color = color
        # 确保 rb_color 处于选中态（与黑/白遮互斥由 QButtonGroup 自动处理）
        self.rb_color.setChecked(True)
        # 同步输入框显示
        self.color_hex_input.setText(color.name().upper())
        self.render_view()

    def pick_screen_color(self):
        """启动全屏取色：截取主屏 → 全屏覆盖层 → 点击取色 → 应用。

        v37.7.10 cp39-fix1:
          - 用 screen.geometry() 限定截图范围，避免跨屏导致坐标错位
          - 用 setGeometry 而非 showFullScreen，保证窗口大小与截图一致
          - mousePressEvent 取色时再做一次坐标缩放，确保取到正确像素
        """
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.geometry()
        # 只截取主屏区域（grabWindow 第一个参数 0 = 整个虚拟桌面，
        # 用 x/y/w/h 限定到主屏 geometry，避免多屏截图导致窗口大于屏幕）
        screenshot = screen.grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())
        if screenshot.isNull():
            return
        # 临时隐藏色板面板，避免覆盖层上方有遮挡
        if hasattr(self, "color_palette_widget"):
            self.color_palette_widget.hide()
        self._color_picker_overlay = _ScreenColorPickerOverlay(
            screenshot, on_picked=self._on_screen_color_picked, parent=None
        )
        # setGeometry 而非 showFullScreen：
        # showFullScreen 会与 setFixedSize 冲突，且在多屏场景下行为不稳定
        self._color_picker_overlay.setGeometry(geo)
        self._color_picker_overlay.show()

    def _on_screen_color_picked(self, color):
        """全屏取色回调：应用取到的颜色并恢复色板面板。"""
        self._apply_custom_color(color)
        if hasattr(self, "color_palette_widget"):
            self.color_palette_widget.show()

    def update_canvas_color(self):
        """切换遮罩颜色（黑/白遮按钮互斥触发）。

        v37.7.10 cp39: rb_color 的颜色由色板面板单独设置，
        点击 rb_color 时不在此处覆盖 current_color，避免重置色板选择。
        v37.7.12 cp42: 切到黑/白遮时收起色板面板，避免面板悬空。
        """
        if self.rb_black.isChecked():
            self.current_color = QColor(0, 0, 0)
        elif self.rb_white.isChecked():
            self.current_color = QColor(255, 255, 255)
        # rb_color 的颜色由 _apply_custom_color 设置
        # v37.7.12 cp42: 切到黑/白遮时收起色板面板
        if hasattr(self, "color_palette_widget"):
            self.color_palette_widget.setVisible(False)
        self.render_view()

    def open_settings(self):
        # v37.0: 传递配置管理器以支持配置持久化
        # v37.4.0: 移除 OCR 引擎选择，只保留 RapidOCR

        # cp62: 按当前打开的文档类型隐藏用不到的设置模块（图片已合并为 PDF，归入 pdf）
        doc_context = "word" if self.word_doc else ("pdf" if self.doc else None)
        dlg = SettingsDialog(self, self.active_rules, self.use_enhance, self.custom_keywords,
                            self.scan_level, self.offset_x, self.offset_w, self.replacement_text,
                            self.word_replace_rules,
                            config_manager=config,
                            custom_keyword_rules=self.custom_keyword_rules,
                            manual_replace_prompt=self.manual_replace_prompt,
                            bookmark_redact_enabled=self.bookmark_redact_enabled,
                            doc_context=doc_context,
                            default_rules=DEFAULT_RULES)
        if dlg.exec():
            self.active_rules = dlg.selected_rules
            self.use_enhance = dlg.use_enhance
            self.custom_keywords = dlg.custom_keywords
            # v37.7.13 cp43: 回读新字段
            self.custom_keyword_rules = dlg.custom_keyword_rules
            self.manual_replace_prompt = dlg.manual_replace_prompt
            # cp_bookmark: 回读书签脱敏开关
            self.bookmark_redact_enabled = getattr(dlg, "bookmark_redact_enabled", False)
            self.scan_level = dlg.scan_level
            self.offset_x = dlg.offset_x
            self.offset_w = dlg.offset_w
            self.replacement_text = dlg.replacement_text
            self.word_replace_rules = dlg.word_replace_rules
            # cp64: 手动框选替换开关立即同步到已创建的画布（无需重渲染/重启）
            self._sync_manual_replace_prompt_to_canvases()
            # v40.1.4（用户反馈 #1）：设置变更不再自动应用到书签——书签脱敏
            # 跟随"智能脱敏"动作生效（见 _on_worker_finished），仅改设置不动书签
            if self.word_doc:
                if not self._has_word_replacement_candidates():
                    self.word_compare_user_hidden = False
                self.render_word_preview()
            else:
                self._refresh_workbench_context()
            self._clear_info_bar_message()
            msg = self.create_message_box(self, QMessageBox.Icon.Information, "成功", "设置已保存")
            msg.exec()

    def _sync_manual_replace_prompt_to_canvases(self):
        """cp64: 把手动框选替换开关立即同步到已创建的 PDF 画布。

        根因：canvas.manual_replace_prompt 原本只在 _render_single_page 重渲染时同步，
        而设置保存后 PDF 场景不触发重渲染，旧画布一直持有过期值，
        导致勾选/取消后需要翻页或重启才生效。

        cp65 扩展：单/双页之外，页面视图（网格）画布同样要在切换设置时立即同步，
        否则网格画布会一直保留创建时的旧值直到下次重渲染。
        """
        for canvas in (getattr(self, "canvas_left", None), getattr(self, "canvas_right", None)):
            if canvas is not None and self._is_canvas_valid(canvas):
                canvas.manual_replace_prompt = self.manual_replace_prompt
        # cp65: 页面视图网格画布一并同步
        grid_canvases = getattr(self, "_grid_canvases", None)
        if grid_canvases:
            for canvas in grid_canvases.values():
                if canvas is not None and self._is_canvas_valid(canvas):
                    canvas.manual_replace_prompt = self.manual_replace_prompt

    def show_feedback(self):
        """显示反馈与开发者信息对话框"""
        dlg = FeedbackDialog(self, config=config)
        dlg.exec()

    def _open_feedback(self):
        """从主窗口直接打开反馈问卷链接。"""
        import webbrowser
        webbrowser.open(FEEDBACK_URL)

    def _open_manual(self):
        """从主窗口直接打开使用手册链接。"""
        import webbrowser
        webbrowser.open("https://fcnwakmkeuz7.feishu.cn/docx/M9ojdaGUAoRVv7x3NCAcxkxenUe?from=from_copylink")

    def _show_donate(self):
        """从主窗口直接打开打赏支持对话框。"""
        dialog = DonateDialog(self)
        dialog.exec()

    def open_encrypt_dialog(self):
        """cp72: 打开加密设置弹框，设定打开/编辑密码（导出时生效）。"""
        if not self.doc or (hasattr(self.doc, "is_closed") and self.doc.is_closed):
            QMessageBox.information(self, "提示", "请先打开 PDF 或图片文件")
            return
        dlg = EncryptSettingsDialog(self, open_pw=self.pdf_open_password,
                                    edit_pw=self.pdf_edit_password)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.pdf_open_password = dlg.open_password
        self.pdf_edit_password = dlg.edit_password
        self._refresh_encrypt_button_state()
        if self.pdf_open_password or self.pdf_edit_password:
            self._set_info_bar_message("🔒 已配置加密，将在点击“导出”保存时生效")
        else:
            self._set_info_bar_message("🔓 已清除加密密码，导出为普通 PDF")

    def _refresh_encrypt_button_state(self):
        """cp72: 根据是否已配置密码刷新加密按钮视觉激活态与 tooltip。"""
        btn = getattr(self, "btn_encrypt", None)
        if btn is None:
            return
        active = bool(self.pdf_open_password or self.pdf_edit_password)
        btn.setProperty("encryptActive", active)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        if active:
            parts = []
            if self.pdf_open_password:
                parts.append("打开密码")
            if self.pdf_edit_password:
                parts.append("编辑密码")
            btn.setToolTip("已配置加密（" + "、".join(parts) + "），导出时生效；点击可修改")
        else:
            btn.setToolTip("加密：为导出的 PDF 设置打开/编辑密码")

    @staticmethod
    def create_message_box(parent, icon, title, text, buttons=QMessageBox.StandardButton.Ok, default_button=QMessageBox.StandardButton.Ok):
        """创建带有浅色主题样式的消息框（v37.4.1: 修复 Windows 深色模式显示问题）

        Args:
            parent: 父窗口
            icon: QMessageBox.Icon 类型
            title: 标题
            text: 内容文本
            buttons: 按钮类型
            default_button: 默认按钮

        Returns:
            QMessageBox: 配置好的消息框实例
        """
        msg = QMessageBox(parent)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        msg.setDefaultButton(default_button)

        # 设置窗口标志，防止 Windows 强制应用深色模式
        msg.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        # 应用浅色主题样式
        from theme import Theme
        theme = Theme.LIGHT
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {theme["background"]};
            }}
            QMessageBox QLabel {{
                color: {theme["text"]};
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {theme["primary"]};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {theme["primary"]};
                opacity: 0.9;
            }}
        """)

        return msg

    def _on_replacement_changed(self, text):
        """替换文本变化时的处理"""
        self.replacement_text = text if text.strip() else "[已脱敏]"

    def open_word_replace_rules(self):
        """打开 Word 多字段替换规则设置。"""
        if not self.word_doc:
            QMessageBox.information(self, "提示", "请先打开 Word 文档。")
            return

        dlg = WordReplaceRulesDialog(
            self,
            rules=self.word_replace_rules,
            default_replacement_text=self.replacement_text,
            title="Word 替换规则设置",
            apply_text="应用规则"
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self.word_replace_rules = dlg.rules
        self.replacement_text = dlg.default_replacement_text

        if not self._has_word_replacement_candidates():
            self.word_compare_user_hidden = False
            self._set_word_compare_mode(False)
            self.render_word_preview()
            QMessageBox.information(self, "提示", "当前无可预览的替换结果，已恢复单栏预览。")
            return

        self.render_word_preview()
        self._refresh_word_compare_toggle()
        self._refresh_workbench_context()
        self._set_info_bar_message("🧩 替换后预览已同步展示：规则替换 + 智能脱敏 + 手动脱敏")

    def _has_enabled_word_replace_rules(self):
        normalized = normalize_word_replace_rules(self.word_replace_rules, self.replacement_text)
        return any(item.get("enabled", True) and item.get("find") for item in normalized)

    def _has_word_replacement_candidates(self):
        """是否存在可在右侧预览中展示的替换结果（规则/OCR/手动）。"""
        if self._has_enabled_word_replace_rules():
            return True
        for data in self.word_data.values():
            if not isinstance(data, dict):
                continue
            if data.get("manual") or data.get("ocr"):
                return True
        return False

    def _set_word_compare_mode(self, enabled):
        """切换 Word 单栏/双栏预览。"""
        self.word_compare_mode = bool(enabled) and bool(self.word_doc)
        self.canvas_container.hide()
        self.word_compare_container.show()

        if self.word_compare_mode:
            if hasattr(self, "word_compare_header"):
                self.word_compare_header.show()
            if hasattr(self, "lbl_word_original_header"):
                self.lbl_word_original_header.setText("原文预览")
            if hasattr(self, "lbl_word_replaced_header"):
                self.lbl_word_replaced_header.show()
            if hasattr(self, "word_header_divider"):
                self.word_header_divider.show()
            self.word_preview_replaced_panel.show()
            self.word_preview_replaced.show()
            if hasattr(self, "word_compare_layout"):
                self.word_compare_layout.setStretch(0, 1)
                self.word_compare_layout.setStretch(1, 1)
        else:
            if hasattr(self, "word_compare_header"):
                self.word_compare_header.hide()
            if hasattr(self, "lbl_word_original_header"):
                self.lbl_word_original_header.setText("文档预览")
            if hasattr(self, "lbl_word_replaced_header"):
                self.lbl_word_replaced_header.hide()
            if hasattr(self, "word_header_divider"):
                self.word_header_divider.hide()
            self.word_preview_replaced_panel.hide()
            self.word_preview_replaced.hide()
            if hasattr(self, "word_compare_layout"):
                self.word_compare_layout.setStretch(0, 1)
                self.word_compare_layout.setStretch(1, 0)

        self._configure_word_scroll_sync_panels()

    def _build_replaced_preview_fragment(self, source_text, merged_matches):
        """根据合并后的匹配区间构建右侧预览片段（统一高亮样式）。"""
        from html import escape as html_escape

        source_label_map = {
            "rule": "规则替换",
            "manual": "手动脱敏",
            "ocr": "智能脱敏"
        }
        segments = build_replaced_preview_segments(source_text, merged_matches, self.replacement_text)
        fragment_parts = []

        for segment in segments:
            value = segment.get("value", "")
            if value is None:
                value = ""
            if not isinstance(value, str):
                value = str(value)
            escaped_value = html_escape(value).replace("\n", "<br/>")

            if segment.get("type") != "replacement":
                fragment_parts.append(escaped_value)
                continue

            source = str(segment.get("source", "rule"))
            title = source_label_map.get(source, "文本替换")
            rule_name = str(segment.get("rule_name", "")).strip()
            if rule_name:
                title = f"{title} ({rule_name})"

            title_attr = html_escape(title)
            source_attr = html_escape(source)
            fragment_parts.append(
                f'<mark class="replace-preview-highlight" data-source="{source_attr}" title="{title_attr}">{escaped_value}</mark>'
            )

        return "".join(fragment_parts)

    def _build_word_replaced_preview_html(self, base_html):
        """构建替换后 HTML（右侧只读预览）。"""
        if not base_html:
            return ""

        text_blocks = {}
        for key, data in self.word_data.items():
            text = data.get("text", "")
            if text:
                # P2: 移除误导性的 "escaped" 字段（原值为未转义原文且从不被读取）
                text_blocks[key] = {"text": text}

        try:
            html = self._add_data_key_attributes(base_html, text_blocks)
            soup = BeautifulSoup(html, "html.parser")
            for element in soup.find_all(attrs={"data-key": True}):
                key = element.get("data-key")
                if not key or key not in self.word_data:
                    continue

                source_text = self.word_data[key].get("text", "")
                merged_matches = merge_word_matches_with_priority(
                    source_text,
                    self.word_replace_rules,
                    self.replacement_text,
                    manual_matches=self.word_data[key].get("manual", []),
                    # cp63: 关键词行内替换（find|replace）优先于统一替换文本
                    ocr_matches=resolve_word_ocr_replacements(
                        self.word_data[key].get("ocr", []),
                        getattr(self, "custom_keyword_rules", None),
                        self.replacement_text
                    )
                )
                if not merged_matches:
                    continue

                replaced_fragment = self._build_replaced_preview_fragment(source_text, merged_matches)
                element.clear()
                fragment_soup = BeautifulSoup(replaced_fragment, "html.parser")
                children = list(fragment_soup.contents)
                if children:
                    for child in children:
                        element.append(child)
                else:
                    element.append(source_text)

            replaced_html = self._wrap_html_document(str(soup))
            style = f"""
            <style>
                body {{ font-family: {PREVIEW_FONT_STACK}; padding: 20px; line-height: 1.6; }}
                p:empty {{ display: none; margin: 0; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                td, th {{ border: 1px solid #ddd; padding: 8px; }}
                mark.replace-preview-highlight {{
                    background-color: #ffd666;
                    color: #2b1f00;
                    border-radius: 3px;
                    padding: 0 2px;
                    box-decoration-break: clone;
                    -webkit-box-decoration-break: clone;
                    box-shadow: inset 0 -1px 0 rgba(43, 31, 0, 0.20);
                }}
            </style>
            """
            if "<head>" in replaced_html:
                replaced_html = replaced_html.replace("<head>", "<head>" + style, 1)
            else:
                replaced_html = style + replaced_html
            return replaced_html
        except (TypeError, ValueError, AttributeError, RuntimeError) as e:
            logger.error("[WordReplacePreview] 构建替换预览失败: %s", e)
            return self._wrap_html_document(base_html)

    def start_batch_replace(self, file_paths=None):
        """启动 Word 批量替换（支持 .docx + .doc）。"""
        if self.active_worker is not None and self.active_worker.isRunning():
            QMessageBox.warning(self, "提示", "当前有任务正在执行，请稍候。")
            return

        files = list(file_paths or [])
        if not files:
            app = QApplication.instance()
            original_style = app.styleSheet()
            app.setStyleSheet(self._get_file_dialog_style())
            try:
                files, _ = QFileDialog.getOpenFileNames(
                    self,
                    "选择要批量替换的 Word 文件",
                    "",
                    "Word 文档 (*.docx *.doc)"
                )
            finally:
                app.setStyleSheet(original_style)

        if not files:
            return

        self.batch_selected_files = list(files)
        self.batch_total_files = len(files)
        self.batch_processed_files = 0
        self.batch_success_count = 0
        self.batch_failed_count = 0
        self.batch_current_file = ""
        self.batch_last_summary = None
        self.batch_stage = "rule_setup"
        if hasattr(self, "batch_log_list"):
            self.batch_log_list.clear()
        self._append_batch_log(f"已载入 {len(files)} 个 Word 文档，等待确认批量替换规则。", "info")
        self._clear_info_bar_message()
        self._set_ui_mode("batch")
        rules_dlg = WordReplaceRulesDialog(
            self,
            rules=self.word_replace_rules,
            default_replacement_text=self.replacement_text,
            title="Word 批量替换规则设置",
            apply_text="开始批量替换"
        )
        if rules_dlg.exec() != QDialog.DialogCode.Accepted:
            self._clear_info_bar_message()
            self._reset_batch_session_state()
            self._sync_ui_mode()
            return

        self.word_replace_rules = rules_dlg.rules
        self.replacement_text = rules_dlg.default_replacement_text
        normalized_rules = normalize_word_replace_rules(self.word_replace_rules, self.replacement_text)
        if not any(item.get("enabled", True) and item.get("find") for item in normalized_rules):
            QMessageBox.warning(self, "提示", "请至少启用一条 Word 替换规则后再开始批量替换。")
            self.batch_stage = "rule_setup"
            self._append_batch_log("当前未启用任何规则，批量替换尚未开始。", "warning")
            self._set_ui_mode("batch")
            return

        self.progress.setValue(0)
        self.btn_cancel_scan.setVisible(True)
        if hasattr(self, "progress_shell"):
            self.progress_shell.show()
        self.btn_cancel_scan.setEnabled(True)
        self._set_info_bar_message(f"📚 批量替换准备中... 共 {len(files)} 个文件")
        self.batch_stage = "running"
        self._append_batch_log(
            f"开始执行批量替换：共 {len(files)} 个文件，启用 {self._count_enabled_word_rules()} 条规则。",
            "info"
        )

        self.batch_worker = WordBatchReplaceWorker(files, normalized_rules, self.replacement_text, parent=self)
        self.active_worker = self.batch_worker
        self.active_task_type = "batch_replace"
        self._sync_ui_mode()

        self.batch_worker.progress_signal.connect(self._on_batch_replace_progress)
        self.batch_worker.file_done_signal.connect(self._on_batch_replace_file_done)
        self.batch_worker.file_error_signal.connect(self._on_batch_replace_file_error)
        self.batch_worker.finished_signal.connect(self._on_batch_replace_finished)
        self.batch_worker.start()

    def _on_batch_replace_progress(self, processed, total, current_file):
        percent = int(processed / total * 100) if total > 0 else 0
        self.batch_processed_files = processed
        self.batch_total_files = total
        self.batch_current_file = os.path.basename(current_file) if current_file else ""
        self.progress.setValue(percent)
        self._set_info_bar_message(f"📚 批量替换进行中: {processed}/{total} - {current_file}")
        self._refresh_workbench_context()

    def _on_batch_replace_file_done(self, input_path, output_path):
        self.batch_success_count += 1
        self.batch_current_file = os.path.basename(input_path)
        self._append_batch_log(
            f"已完成：{os.path.basename(input_path)} -> {os.path.basename(output_path)}",
            "success"
        )
        self._refresh_workbench_context()
        logger.info("[BatchReplace] 完成: %s -> %s", input_path, output_path)

    def _on_batch_replace_file_error(self, index, input_path, error_msg):
        if not self.batch_worker:
            return

        self.batch_failed_count += 1
        self.batch_current_file = os.path.basename(input_path)
        self._append_batch_log(
            f"处理失败：{os.path.basename(input_path)} - {error_msg}",
            "error"
        )
        self._refresh_workbench_context()

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("批量替换出错")
        msg.setText(
            f"文件处理失败（{index + 1}）：\n{os.path.basename(input_path)}\n\n"
            f"错误：{error_msg}\n\n"
            "是否跳过该文件继续处理？"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Abort)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        yes_btn = msg.button(QMessageBox.StandardButton.Yes)
        abort_btn = msg.button(QMessageBox.StandardButton.Abort)
        if yes_btn:
            yes_btn.setText("跳过继续")
        if abort_btn:
            abort_btn.setText("停止任务")

        choice = msg.exec()
        decision = "skip" if choice == QMessageBox.StandardButton.Yes else "stop"
        if decision == "skip":
            self._append_batch_log(f"已跳过：{os.path.basename(input_path)}，继续处理后续文档。", "warning")
        else:
            self._append_batch_log("用户选择停止批量任务，正在安全结束当前流程。", "warning")
        self.batch_worker.provide_error_decision(decision)

    def _on_batch_replace_finished(self, summary):
        self.active_worker = None
        self.batch_worker = None
        self.active_task_type = None
        self.btn_cancel_scan.setVisible(False)
        self.btn_cancel_scan.setEnabled(True)
        self.progress.setValue(0)

        total = int(summary.get("total", 0))
        success = summary.get("success", [])
        failed = summary.get("failed", [])
        stopped = bool(summary.get("stopped", False))
        success_count = len(success)
        failed_count = len(failed)
        self.batch_total_files = total
        self.batch_processed_files = total
        self.batch_success_count = success_count
        self.batch_failed_count = failed_count
        self.batch_last_summary = summary
        self.batch_current_file = ""
        self.batch_stage = "stopped" if stopped else "finished"

        status_text = "已停止" if stopped else "已完成"
        self._set_info_bar_message(f"📚 批量替换{status_text}: 成功 {success_count} / 失败 {failed_count}")
        self._append_batch_log(
            f"批量替换{status_text}：成功 {success_count} 个，失败 {failed_count} 个。",
            "warning" if stopped else "success"
        )
        self._sync_ui_mode()

        lines = [
            f"批量替换{status_text}",
            f"总文件数: {total}",
            f"成功: {success_count}",
            f"失败: {failed_count}"
        ]

        if success:
            lines.append("")
            lines.append("成功输出（最多显示 10 条）:")
            for item in success[:10]:
                lines.append(f"- {item.get('output', '')}")
            if len(success) > 10:
                lines.append(f"... 其余 {len(success) - 10} 条已省略")

        if failed:
            lines.append("")
            lines.append("失败详情（最多显示 10 条）:")
            for item in failed[:10]:
                lines.append(f"- {os.path.basename(item.get('input', ''))}: {item.get('error', '')}")
            if len(failed) > 10:
                lines.append(f"... 其余 {len(failed) - 10} 条已省略")

        QMessageBox.information(self, "批量替换结果", "\n".join(lines))

    def detect_file_type(self, fname):
        """检测文件类型"""
        ext = os.path.splitext(fname)[1].lower()
        if ext == '.pdf':
            return 'pdf'
        elif ext == '.docx':
            return 'docx'
        elif ext == '.doc':
            return 'doc'
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            return 'image'
        else:
            return 'unknown'

    def _get_file_dialog_style(self):
        """获取文件对话框样式（v36.2: 使用系统默认按钮样式确保跨平台可读性）"""
        return f"""
            QFileDialog {{
                background-color: #FFFFFF;
                color: #1D1D1F;
                font-family: {Theme.FONT_FAMILY};
                font-size: 12px;
            }}
            QFileDialog QLabel {{ color: #1D1D1F; }}
            /* 按钮使用系统默认样式，确保跨平台可读性 */
            /* macOS/Windows 会自动应用适合的按钮颜色 */
            QFileDialog QListView, QFileDialog QTreeView {{
                background-color: #FFFFFF;
                color: #1D1D1F;
                border: 1px solid #D1D1D6;
            }}
            QFileDialog QListView::item:selected, QFileDialog QTreeView::item:selected {{
                background-color: #007AFF;
                color: white;
            }}
            QFileDialog QComboBox {{
                background-color: #FFFFFF;
                color: #1D1D1F;
                border: 1px solid #D1D1D6;
                padding: 4px;
            }}
            QFileDialog QLineEdit {{
                background-color: #FFFFFF;
                color: #1D1D1F;
                border: 1px solid #D1D1D6;
                padding: 4px;
            }}
        """

    def open_pdf(self):
        """打开文件（支持图片多选和多 Word 批量替换）"""
        try:
            has_active_context = self._has_active_open_context()

            # 已有文档/任务时，保持原有清理策略，避免新旧上下文互相污染。
            if has_active_context:
                self._cleanup_before_open()
                self._cleanup_temp_file()

            # v37.0.6: 使用原生文件对话框，更稳定
            # 不使用 DontUseNativeDialog，让系统处理渲染
            fnames, _ = QFileDialog.getOpenFileNames(
                self, "选择文件", "",
                "支持的文件 (*.pdf *.doc *.docx *.jpg *.jpeg *.png *.bmp *.tiff)"
            )

            if not fnames:
                return

            # 首次从空首页打开文件时，推迟到真正选中文件后再做清理，
            # 避免文件对话框弹出前触发首页抖动/重排。
            if not has_active_context:
                self._cleanup_before_open()
                self._cleanup_temp_file()

            # 根据选择数量处理
            if len(fnames) == 1:
                # 单个文件，按原有逻辑处理
                fname = fnames[0]
                doc_type = self.detect_file_type(fname)
                if doc_type == 'pdf':
                    self._open_pdf_file(fname)
                elif doc_type == 'docx':
                    self._open_word_docx(fname)
                elif doc_type == 'doc':
                    self._open_word_doc(fname)
                elif doc_type == 'image':
                    self._open_images_merge([fname])
                else:
                    QMessageBox.warning(self, "不支持的格式", "请选择 PDF、Word 文档或图片文件")
            else:
                # 多个文件：支持图片合并或 Word 批量替换
                are_all_images = all(self.detect_file_type(f) == 'image' for f in fnames)
                are_all_words = all(self.detect_file_type(f) in ('doc', 'docx') for f in fnames)
                if are_all_images:
                    self._open_images_merge(fnames)
                elif are_all_words:
                    self.start_batch_replace(file_paths=fnames)
                else:
                    QMessageBox.warning(self, "不支持的混合选择",
                        "同时选择多个文件时，仅支持两种场景：\n"
                        "1. 全部是图片（自动合并为PDF）\n"
                        "2. 全部是Word（自动启动批量替换）")
        except (IOError, OSError, ValueError, ConversionError) as e:
            QMessageBox.critical(self, "错误", f"打开文件失败: {str(e)}")

    def remove_case_file_watermark(self):
        """v37.7.11 cp40: 去除电子卷宗 PDF 中的律师证号+姓名水印。

        采用 PDF 内容流编辑方式（非遮罩覆盖）：
          1. 校验已打开 PDF
          2. 扫描所有页识别水印 span（rawdict 评分制，用于统计确认）
          3. 弹确认对话框显示数量与示例文本
          4. 逐页读取内容流，删除含旋转矩阵 0.70711 -0.70711 0.70711 0.70711 的
             q...Q 绘制指令块（水印用旋转 45° 矩阵 + NotoSansCJK 字体，
             正文用其他字体/不旋转，删除水印块不影响正文）
          5. 标记 self._pdf_modified=True，刷新预览，启用导出按钮
          6. 不自动保存：用户需手动点「导出」写盘

        优势：真正从内容流删除水印绘制指令，不留白色块，不影响与水印重叠的正文。
        """
        if not self.doc or (hasattr(self.doc, "is_closed") and self.doc.is_closed):
            QMessageBox.information(self, "提示", "请先打开 PDF 文件")
            return
        if self.doc_type != 'pdf':
            QMessageBox.information(self, "提示", "去水印功能仅支持 PDF 文件")
            return

        # 扫描所有页（用于确认对话框统计）
        all_watermarks = []
        try:
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                wms = detect_watermark_spans(page)
                for wm in wms:
                    wm["page_num"] = page_num
                all_watermarks.extend(wms)
        except Exception as e:
            QMessageBox.critical(self, "扫描失败", f"扫描水印时出错：{e}")
            return

        if not all_watermarks:
            QMessageBox.information(
                self, "未发现水印",
                "未在当前 PDF 中识别到卷宗水印。\n\n"
                "本功能针对文字层水印（律师证号+姓名斜排），"
                "扫描件图片水印不适用。"
            )
            return

        # 确认对话框
        sample = all_watermarks[0].get("text", "")
        affected_pages = sorted({wm["page_num"] for wm in all_watermarks})
        reply = QMessageBox.question(
            self, "确认去除水印",
            f"共识别到 {len(all_watermarks)} 处卷宗水印"
            f"（跨 {len(affected_pages)} 页，共 {self.doc.page_count} 页）。\n"
            f"示例水印文本：{sample!r}\n\n"
            f"点击「是」将从内容流删除水印绘制指令（非遮罩，不留白块，不影响正文），不可撤销。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 逐页编辑内容流删除水印
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            total_removed = 0
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                removed = remove_watermark_from_stream(self.doc, page)
                total_removed += removed
            self._pdf_modified = True
            QApplication.restoreOverrideCursor()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "去除失败", f"去除水印时出错：{e}")
            return

        # 刷新预览 + 启用导出
        try:
            # cp69: 页面视图下缩略缓存持有去水印前的旧渲染，
            # 需失效缓存并强制重渲染可见页（render_view 在该模式下仅刷遮罩层）
            if getattr(self, "page_view_mode", False):
                self._invalidate_grid_cache()
                self._refresh_visible_grid_thumbs()
            else:
                self.render_view()
        except Exception:
            pass
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(True)
        if total_removed == 0:
            QMessageBox.warning(
                self, "未能去除",
                f"识别到 {len(all_watermarks)} 处水印，但未能定位其绘制指令，本次未修改文档。\n\n"
                f"此类水印可能以图片或特殊编码绘制，当前版本暂不支持去除。\n"
                f"文档内容未受影响。"
            )
            return
        QMessageBox.information(
            self, "完成",
            f"已从内容流删除 {total_removed} 个水印绘制块"
            f"（覆盖 {len(all_watermarks)} 处水印）。\n\n"
            f"请点击「导出」保存修改后的 PDF。"
        )

    def _authenticate_pdf_on_open(self, fname, state):
        """cp113: 打开加密 PDF 时弹密码框验证，按动作设置导出加密状态。

        与锁按钮共享 pdf_open_password/pdf_edit_password：用户在此选择"打开"
        保留原密码、"解除"清空密码、"修改"弹新密码框，导出时统一通过
        build_encrypt_save_kwargs 写入。

        Args:
            fname: 文件路径（仅用于展示文件名）
            state: detect_pdf_password_state 返回的 dict

        Returns:
            bool: True 表示继续打开（已认证，或 owner 限制下用户取消=保留限制打开）；
                  False 表示用户取消且文档需打开密码，应放弃打开。
        """
        needs_user_pw = state["needs_user_pw"]
        file_name = os.path.basename(fname)
        while True:
            dlg = PasswordOpenDialog(self, file_name=file_name, file_type="pdf")
            if dlg.exec() != QDialog.DialogCode.Accepted:
                # 用户取消
                if needs_user_pw:
                    self.doc.close()
                    self.doc = None
                    return False
                # owner restriction：保留限制直接打开
                return True
            pw = dlg.password
            # fitz.authenticate 返回权限位（>0 成功，0 失败）
            if self.doc.authenticate(pw) <= 0:
                QMessageBox.warning(self, "密码错误", "密码不正确，请重试。")
                continue
            # 验证成功，按 action 设置导出加密状态
            action = dlg.action
            # cp114: 无论何种动作，pw 已通过 authenticate 验证，
            # 原文件仍加密，后续 OCR/save_pdf 从磁盘重读需此密码认证
            self._pdf_auth_password = pw
            if action == "open":
                self.pdf_open_password = pw
                self.pdf_edit_password = ""
            elif action == "remove":
                self.pdf_open_password = ""
                self.pdf_edit_password = ""
            elif action == "change":
                new_dlg = EncryptSettingsDialog(self)
                if new_dlg.exec() == QDialog.DialogCode.Accepted:
                    self.pdf_open_password = new_dlg.open_password
                    self.pdf_edit_password = new_dlg.edit_password
                else:
                    # 取消修改则保留原密码
                    self.pdf_open_password = pw
                    self.pdf_edit_password = ""
            break
        self._refresh_encrypt_button_state()
        return True

    def _open_pdf_file(self, fname):
        """内部方法：打开 PDF 文件"""
        # 关闭已打开的PDF文档（防止资源泄露）
        if self.doc:
            self.doc.close()
            self.doc = None

        self.image_merge_in_progress = False
        self.image_merge_total_images = 0
        self._reset_batch_session_state()
        self._clear_info_bar_message()
        self.file_path = fname
        # 安全修复: 打开 PDF 前校验路径安全性（防注入/遍历）
        _safe, _err = validate_safe_path(fname, allowed_extensions=['.pdf'])
        if not _safe:
            self.doc = None
            QMessageBox.critical(
                self, "路径不安全",
                f"文件路径未通过安全校验：\n{_err}"
            )
            return
        # O5: fitz.open 对损坏 PDF 抛 FileDataError（继承 RuntimeError），
        # 上层捕获列表不含该类型会直达全局 exception_hook。此处统一拦截并提示。
        try:
            self.doc = fitz.open(fname)
        except Exception as e:
            self.doc = None
            QMessageBox.critical(
                self, "打开失败",
                f"PDF 文件无法打开：{os.path.basename(fname)}\n\n"
                f"{type(e).__name__}: {e}\n\n"
                "文件可能已损坏或不是有效的 PDF。"
            )
            return

        # cp113: 加密 PDF 支持——检测密码状态，弹密码框验证，按动作设置导出加密状态
        state = detect_pdf_password_state(self.doc)
        if state["needs_user_pw"] or state["has_owner_restriction"]:
            if not self._authenticate_pdf_on_open(fname, state):
                return  # 需打开密码且用户取消 → 放弃打开

        self.doc_type = 'pdf'
        total = len(self.doc)
        self.page_data = {i: {'ocr': [], 'manual': []} for i in range(total)}
        self.current_page = 0
        self.word_doc = None
        self.word_data = {}
        self.word_compare_mode = False
        self.word_compare_user_hidden = False
        self.btn_scan.setEnabled(True)
        self.btn_save.setEnabled(True)

        # 切换显示：显示 canvas，隐藏 Word 预览
        self.canvas_container.show()
        self.word_compare_container.hide()
        self.word_preview.hide()
        self.word_preview_replaced.hide()
        self._sync_ui_mode()

        # v37.7.11 cp40: PDF 打开成功后显示去水印按钮（仅文字 PDF 含律师证号水印，扫描件无）
        if hasattr(self, "btn_remove_watermark"):
            self.btn_remove_watermark.show()

        self.fit_page()
        # cp_bookmark: 预加载 TOC（若面板已展开则立即显示，否则首次展开时再用）
        self._load_pdf_toc()
        # cp88: 检查并提示恢复未完成的脱敏进度（在撤销基线之前，恢复后状态即基线）
        self._maybe_restore_session_draft()
        # cp83: PDF/图片加载完成后压入基线快照（首次撤销有底）
        self._seed_undo_baseline()

    def _decrypt_word_for_open(self, fname):
        """cp113: 弹密码框解密加密 docx，返回 (load_path, password, action)。

        解密临时文件写入 temp_manager 追踪的临时目录，保留原 basename
        （使预览/保存读取一致、标题显示原文件名），并复用 converted_temp_file
        清理机制（_cleanup_temp_file 会在下次打开/退出时清理）。

        Args:
            fname: 加密 docx 原始路径

        Returns:
            (load_path, password, action):
              load_path=None 表示用户取消；否则为解密后的临时 docx 路径。
              action 为 PasswordOpenDialog 返回的动作（"open"/"remove"）。
        """
        from privacyguard.utils.word_crypto import decrypt_docx_to_temp

        # 先清理上一次的转换/解密临时文件，避免堆积
        self._cleanup_temp_file()
        temp_dir = self.temp_manager.create_temp_dir()
        base_name = os.path.basename(fname)
        output_path = os.path.join(temp_dir, base_name)

        while True:
            dlg = PasswordOpenDialog(self, file_name=base_name, file_type="word")
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return None, "", ""  # 用户取消
            pw = dlg.password
            try:
                decrypt_docx_to_temp(fname, pw, output_path)
            except ValueError:
                QMessageBox.warning(self, "密码错误", "密码不正确，请重试。")
                continue
            except (OSError, TypeError) as e:
                QMessageBox.critical(self, "解密失败", f"Word 文档解密失败：{e}")
                return None, "", ""
            # 解密成功：登记到 converted_temp_file 以复用清理机制
            self.converted_temp_file = output_path
            return output_path, pw, dlg.action

    def _open_word_docx(self, fname):
        """打开 DOCX 文件"""
        try:
            from docx import Document
            from privacyguard.utils.word_crypto import is_encrypted_docx

            # cp113: 加密 docx 先弹密码框解密到临时文件（保留原 basename，供预览/保存读取）
            word_pw = ""
            word_action = ""
            load_path = fname
            if is_encrypted_docx(fname):
                load_path, word_pw, word_action = self._decrypt_word_for_open(fname)
                if load_path is None:
                    return  # 用户取消

            # 打开新文件时失效缓存，避免复用旧 HTML
            self._reset_word_preview_cache()
            self.image_merge_in_progress = False
            self.image_merge_total_images = 0
            self._reset_batch_session_state()
            self.word_compare_mode = False
            self.word_compare_user_hidden = False
            self.word_doc = Document(load_path)
            self.file_path = load_path  # cp113: 加密文档指向解密临时文件，预览/保存读取一致
            self.word_open_password = word_pw
            self.doc_type = 'docx'
            self.doc = None  # 清空 PDF 文档对象
            self.page_data = {}
            self._word_scan_meta = None  # W8: 新文档重置扫描状态，避免沿用旧文档的完成标记

            # 初始化 word_data 结构
            self.word_data = {}
            for idx, para in enumerate(self.word_doc.paragraphs):
                self.word_data[f'paragraph_{idx}'] = {
                    'type': 'paragraph',
                    'index': idx,
                    'text': paragraph_plain_text(para),
                    'ocr': [],
                    'manual': []
                }

            # 扫描表格
            for table_idx, table in enumerate(self.word_doc.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        key = f'table_{table_idx}_cell_{row_idx}_{cell_idx}'
                        self.word_data[key] = {
                            'type': 'table_cell',
                            'table': table_idx,
                            'row': row_idx,
                            'cell': cell_idx,
                            'text': cell_plain_text(cell),
                            'ocr': [],
                            'manual': []
                        }

            # W2: 页眉/页脚也纳入脱敏范围（常见泄漏点：密级标注、单位名、作者）
            for key, para in iter_word_header_footer_paragraphs(self.word_doc):
                self.word_data[key] = {
                    'type': 'header_footer_paragraph',
                    'text': paragraph_plain_text(para),
                    'ocr': [],
                    'manual': []
                }
            for key, cell in iter_word_header_footer_cells(self.word_doc):
                self.word_data[key] = {
                    'type': 'header_footer_cell',
                    'text': cell_plain_text(cell),
                    'ocr': [],
                    'manual': []
                }

            # 启用按钮
            self.btn_scan.setEnabled(True)
            self.btn_save.setEnabled(True)

            # 根据规则与现有脱敏结果决定是否默认显示双栏预览
            self.word_compare_mode = self._has_word_replacement_candidates()
            self._sync_ui_mode()

            # 显示 HTML 预览
            self.render_word_preview()

            self._clear_info_bar_message()
            # cp113: 加密 Word 打开提示（python-docx 不支持加密保存，导出均不带密码）
            if word_action == "remove":
                self._set_info_bar_message("🔓 Word 已解除密码，导出时不带密码")
            elif word_action == "open":
                self._set_info_bar_message(
                    "ℹ️ Word 已打开。导出时不带密码（python-docx 不支持加密保存）"
                )

        except (IOError, OSError, ValueError, KeyError, PackageNotFoundError, BadZipFile) as e:
            # W7: 损坏/伪装 docx 抛 PackageNotFoundError；加密 docx 已在上方提前处理
            QMessageBox.critical(self, "错误", f"打开 Word 文档失败: {str(e)}")

    def _open_word_doc(self, fname):
        """打开 .doc 文件（通过转换为 .docx）"""

        # 检查系统支持（v35.1: 使用增强的跨平台检测）
        support_info = self._check_doc_support()
        method = support_info['recommended']

        if not method:
            # 无可用工具，显示安装指南
            self._show_doc_install_guide()
            return

        # 显示格式限制提示
        tool_name = "LibreOffice" if method == 'libreoffice' else "antiword"
        reply = QMessageBox.question(
            self,
            "格式提示",
            f".doc 是旧版 Word 格式，将使用 {tool_name} 转换。\n\n"
            f"{'（antiword 只保留纯文本，会丢失格式）' if method == 'antiword' else '转换后可能丢失部分格式。'}\n\n"
            "建议先在 Word 中另存为 .docx 格式以获得最佳效果。\n\n"
            "是否继续转换？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # 转换并打开
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            docx_path = self._convert_doc_to_docx(fname, method)
            if docx_path:
                # 使用转换后的文件打开
                self.converted_temp_file = docx_path  # 保存临时文件路径以便后续清理
                self._open_word_docx(docx_path)
                self._set_info_bar_message("📝 已完成 .doc 转换，现已进入 Word 替换工作台。")
        except (IOError, OSError, ValueError, RuntimeError) as e:
            QMessageBox.critical(self, "转换失败", f"无法转换 .doc 文件:\n{str(e)}")
        finally:
            QApplication.restoreOverrideCursor()

    def _check_doc_support(self):
        """检查系统是否支持 .doc 格式（v35.1: 增强跨平台检测）"""
        import shutil

        result = {
            'libreoffice': False,
            'antiword': False,
            'recommended': None
        }

        # W10: LibreOffice 探测统一委托 doc_converter.resolve_soffice_cmd，
        # 消除 main.py 与 doc_converter.py 双份探测逻辑口径不一致（Linux 别名、
        # macOS PATH 兜底）导致的"UI 判定与转换器实际能力分叉"问题。
        try:
            from privacyguard.utils.doc_converter import resolve_soffice_cmd
            resolved = resolve_soffice_cmd()
            if os.path.isabs(resolved):
                result['libreoffice'] = os.path.exists(resolved)
            else:
                result['libreoffice'] = shutil.which(resolved) is not None
        except Exception:
            result['libreoffice'] = False

        # 检查 antiword
        if shutil.which('antiword'):
            result['antiword'] = True

        # 确定推荐方案
        if result['libreoffice']:
            result['recommended'] = 'libreoffice'
        elif result['antiword']:
            result['recommended'] = 'antiword'

        return result

    def _show_doc_install_guide(self):
        """显示 .doc 转换工具安装指南（v35.1 新增）"""
        import platform
        system = platform.system()

        if system == 'Darwin':  # macOS
            guide = """
<h3>安装 LibreOffice（推荐）</h3>
<p>在终端执行：</p>
<code style="background:#f5f5f5;padding:8px;display:block;">brew install --cask libreoffice</code>

<h4 style="margin-top:16px;">或使用轻量级方案 antiword</h4>
<p>在终端执行：</p>
<code style="background:#f5f5f5;padding:8px;display:block;">brew install antiword</code>
<p style="color:#666;margin-top:8px;">注：antiword 只能提取纯文本，会丢失格式</p>
"""
        elif system == 'Windows':
            guide = """
<h3>安装 LibreOffice（推荐）</h3>
<p>请从官网下载安装：</p>
<a href="https://www.libreoffice.org/download/download/">https://www.libreoffice.org/download/</a>
<p style="margin-top:8px;">选择 Windows 版本下载并安装</p>

<h4 style="margin-top:16px;">安装后重启本软件即可</h4>
"""
        else:  # Linux
            guide = """
<h3>安装 LibreOffice（推荐）</h3>
<p>根据您的发行版执行：</p>
<code style="background:#f5f5f5;padding:8px;display:block;">
# Debian/Ubuntu
sudo apt install libreoffice

# Fedora
sudo dnf install libreoffice

# Arch Linux
sudo pacman -S libreoffice
</code>

<h4 style="margin-top:16px;">或使用轻量级方案 antiword</h4>
<code style="background:#f5f5f5;padding:8px;display:block;">
# Debian/Ubuntu
sudo apt install antiword

# Fedora
sudo dnf install antiword
</code>
<p style="color:#666;margin-top:8px;">注：antiword 只能提取纯文本，会丢失格式</p>
"""

        msg = QMessageBox(self)
        msg.setWindowTitle("缺少 .doc 转换工具")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(guide)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("""
            QMessageBox {
                min-width: 450px;
            }
            QLabel {
                min-width: 400px;
            }
        """)
        msg.exec()

    def _convert_doc_to_docx(self, doc_path, method='libreoffice'):
        """v37.7.6: 委托给共享转换模块。"""
        from privacyguard.utils.doc_converter import (
            convert_with_antiword,
        )
        try:
            if method == 'libreoffice':
                docx_path, temp_dir = _shared_convert_doc_to_docx(doc_path)
                self.converted_temp_file = docx_path
                # P1-1: 跟踪转换目录（含原始 source.doc），供 _cleanup_temp_file 完整清理，
                # 避免未脱敏原文永久滞留系统临时目录。
                self.converted_temp_dir = temp_dir
                return docx_path
            elif method == 'antiword':
                temp_dir = self.temp_manager.create_temp_dir()
                return convert_with_antiword(doc_path, temp_dir=temp_dir)
            else:
                raise ValueError(f"不支持的转换方法: {method}")
        except ConversionError:
            raise
        except (OSError, IOError, RuntimeError, ValueError) as e:
            raise ConversionError(f"转换出错: {e}", "请尝试在 Word 中手动另存为 .docx 格式")

    def _open_images_merge(self, image_paths):
        """处理图片合并为PDF"""
        try:
            self.image_merge_in_progress = True
            self.image_merge_total_images = len(image_paths)
            self._set_ui_mode("image_merge")
            # 1. 让用户排序（如果是多张图片）
            if len(image_paths) > 1:
                dlg = ImageListDialog(image_paths, self, config=config)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    self.image_merge_in_progress = False
                    self.image_merge_total_images = 0
                    self._sync_ui_mode()
                    return
                image_paths = dlg.get_ordered_paths()
                self.image_merge_total_images = len(image_paths)

            # 2. 生成输出路径（在第一张图片所在目录）
            base_dir = os.path.dirname(image_paths[0])
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_filename = f"merged_{timestamp}.pdf"
            final_path = os.path.join(base_dir, output_filename)

            # 3. 创建临时文件
            temp_pdf = self.temp_manager.create_temp_file(suffix='.pdf')

            # 4. 启动Worker合并
            # P1-6: 每次启动合并递增 generation 并捕获，回调据此判断是否陈旧
            self._merge_generation = getattr(self, "_merge_generation", 0) + 1
            _merge_gen = self._merge_generation
            self.merge_worker = ImageMergeWorker(image_paths, temp_pdf, parent=self)
            self.merge_worker.progress_signal.connect(self.progress.setValue)
            self.merge_worker.finished_signal.connect(
                lambda p, g=_merge_gen: self._on_merge_finished(p, final_path, g))
            self.merge_worker.error_signal.connect(self._on_merge_error)
            self.merge_worker.start()

            self._set_info_bar_message(f"正在合并 {len(image_paths)} 张图片...")
            self._refresh_workbench_context()

        except (IOError, OSError, ValueError, RuntimeError) as e:
            self.image_merge_in_progress = False
            self.image_merge_total_images = 0
            self._sync_ui_mode()
            QMessageBox.critical(self, "错误", f"启动图片合并失败: {str(e)}")

    def _on_merge_finished(self, temp_pdf, final_path, generation):
        """合并完成回调（P1-6: generation 守卫防止陈旧合并覆盖用户新打开的文档）"""
        try:
            # P1-6: 若合并进行期间用户打开了别的文件或发起新合并（generation 已变），
            # 不自动覆盖当前文档，仅清理临时文件后返回。
            if generation != getattr(self, "_merge_generation", 0):
                logger.info("[merge] 陈旧合并完成（generation 已变），仅清理临时文件不自动打开")
                try:
                    if temp_pdf and os.path.exists(temp_pdf):
                        os.remove(temp_pdf)
                except OSError:
                    pass
                return
            # P2: worker 取消时发空路径——仅重置 UI 状态，不移动/打开/报错
            if not temp_pdf:
                self.image_merge_in_progress = False
                self.image_merge_total_images = 0
                self._set_info_bar_message("已取消图片合并")
                self._sync_ui_mode()
                return
            # 将临时文件移动到最终位置
            shutil.move(temp_pdf, final_path)
            self._set_info_bar_message(f"✓ 合并完成: {final_path}")
            self.image_merge_in_progress = False

            # 自动打开生成的PDF
            self._open_pdf_file(final_path)

        except (IOError, OSError, ValueError) as e:
            self.image_merge_in_progress = False
            self.image_merge_total_images = 0
            QMessageBox.critical(self, "错误", f"保存合并文件失败: {str(e)}")

    def _on_merge_error(self, error_msg):
        """合并错误回调"""
        self.image_merge_in_progress = False
        self.image_merge_total_images = 0
        self._set_info_bar_message("✗ 合并失败")
        self._sync_ui_mode()
        QMessageBox.critical(self, "合并失败", error_msg)

    def _cleanup_temp_file(self):
        """清理转换产生的临时文件（v36.1 安全修复：跨平台安全清理）"""
        import tempfile

        if hasattr(self, 'converted_temp_file') and self.converted_temp_file:
            try:
                # P1-1: 优先清理已跟踪的转换目录（含原始 source.doc + 输出 source.docx）。
                # 旧实现仅当目录为空才 rmdir，导致原始未脱敏 .doc 永久滞留系统临时目录，
                # 对脱敏工具是核心保密失败。改为 rmtree 整个 own-temp 目录彻底清理。
                temp_dir = getattr(self, 'converted_temp_dir', None) or os.path.dirname(self.converted_temp_file)

                # 获取系统临时目录（跨平台：Windows 返回 C:\Users\...\AppData\Local\Temp，macOS/Linux 返回 /tmp 或 /var/tmp）
                system_temp_dir = tempfile.gettempdir()

                # 规范化路径进行比较（处理大小写敏感/不敏感、路径分隔符等）
                norm_temp_dir = os.path.normcase(os.path.abspath(temp_dir))
                norm_system_temp = os.path.normcase(os.path.abspath(system_temp_dir))

                # 安全检查：只有当目录位于系统临时目录下，且不是系统临时目录本身时才删除
                if (norm_temp_dir.startswith(norm_system_temp + os.sep) and
                    norm_temp_dir != norm_system_temp):
                    try:
                        if os.path.isdir(temp_dir):
                            # rmtree 整个目录：同时删除 source.doc 原件与 source.docx 输出，
                            # 彻底消除未脱敏原文残留（脱敏工具的核心保密要求）
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            logger.debug("[清理] 已删除转换临时目录: %s", temp_dir)
                    except OSError as e:
                        logger.warning("[清理] 删除转换临时目录出错: %s - %s", temp_dir, e)
                else:
                    logger.debug("[清理] 跳过非系统临时目录: %s", temp_dir)

            except Exception as e:
                logger.error("[清理] 清理临时文件时出错: %s", e)
            finally:
                self.converted_temp_file = None
                self.converted_temp_dir = None

    def clamp_zoom(self, zoom, allow_below_min=False):
        """
        将缩放值限制在有效范围内 (v33.2)

        Args:
            zoom: 缩放值
            allow_below_min: 是否允许低于 ZOOM_MIN (用于自适应模式)
        """
        if allow_below_min:
            # 自适应模式：允许更小的缩放比例以完整显示页面
            return min(ZOOM_MAX, zoom)
        else:
            # 手动模式：保持正常限制，防止过小
            return max(ZOOM_MIN, min(ZOOM_MAX, zoom))

    # === cp67: 页面视图（多页网格总览）===

    _GRID_CACHE_MAX = 60  # 缩略图 LRU 缓存上限（防大文档内存膨胀）
    _GRID_MIN_THUMB = 160  # 单页缩略最小宽度（列数上限由此推导）
    _ZOOM_GESTURE_GAP = 0.45  # cp68: Ctrl+滚轮手势分割间隔（秒），超过即视为新手势

    # === cp81: 全文搜索侧栏 ===

    def _build_search_panel(self):
        """cp81: 构建右侧搜索面板（输入框+搜索按钮 / 状态行 / 结果列表）。"""
        panel = QFrame()
        panel.setObjectName("searchPanel")
        panel.setFixedWidth(320)
        v = QVBoxLayout(panel)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入要搜索的文字")
        self.search_input.returnPressed.connect(self.start_doc_search)
        row.addWidget(self.search_input, 1)
        self.btn_search_go = QPushButton()
        self.btn_search_go.setObjectName("searchGoButton")
        self.btn_search_go.setIcon(QIcon(resource_path(os.path.join("assets", "icons", "search_magnifier.svg"))))
        self.btn_search_go.setFixedSize(32, 32)
        self.btn_search_go.setToolTip("开始搜索")
        self.btn_search_go.clicked.connect(self.start_doc_search)
        row.addWidget(self.btn_search_go)
        v.addLayout(row)

        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.lbl_search_status = QLabel("")
        self.lbl_search_status.setObjectName("searchStatusLabel")
        self.lbl_search_status.setWordWrap(True)
        status_row.addWidget(self.lbl_search_status, 1)
        self.btn_search_cancel = QPushButton("取消")
        self.btn_search_cancel.setObjectName("searchCancelButton")
        self.btn_search_cancel.setFixedSize(52, 24)
        self.btn_search_cancel.clicked.connect(self._cancel_doc_search)
        self.btn_search_cancel.hide()
        status_row.addWidget(self.btn_search_cancel)
        v.addLayout(status_row)

        self.search_results_list = QListWidget()
        self.search_results_list.setObjectName("searchResultsList")
        self.search_results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.search_results_list.itemClicked.connect(self._on_search_result_clicked)
        v.addWidget(self.search_results_list, 1)

        from theme import Theme as _T
        theme = _T.LIGHT
        panel.setStyleSheet(f"""
            QFrame#searchPanel {{
                background-color: #FFFFFF;
                border-left: 1px solid {theme["border"]};
            }}
            QLineEdit {{
                background-color: #FFFFFF; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px;
            }}
            QPushButton#searchGoButton {{
                background-color: {theme["hover"]}; border: 1px solid {theme["border"]};
                border-radius: 6px; outline: none;
            }}
            QPushButton#searchGoButton:hover {{ background-color: {theme["pressed"]}; }}
            QLabel#searchStatusLabel {{
                color: {theme["text_secondary"]}; font-size: 11px; background: transparent;
            }}
            QPushButton#searchCancelButton {{
                background-color: #F2F2F7; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 5px;
                padding: 0; font-size: 11px; outline: none;
            }}
            QListWidget#searchResultsList {{
                background-color: #FFFFFF; border: 1px solid {theme["border"]};
                border-radius: 8px; outline: none;
            }}
            QListWidget#searchResultsList::item {{
                border-bottom: 1px solid #EEF1F5; padding: 2px;
            }}
            QListWidget#searchResultsList::item:hover {{ background-color: {theme["hover"]}; }}
            QListWidget#searchResultsList::item:selected {{
                background-color: {theme["pressed"]}; color: {theme["text"]};
            }}
        """)
        return panel

    def toggle_search_panel(self):
        """cp81: 工具栏放大镜按钮：切换右侧搜索面板显示/隐藏。"""
        if not self.doc and not self.word_doc:
            QMessageBox.information(self, "提示", "请先打开 PDF、图片或 Word 文档")
            return
        show = not self.search_panel.isVisible()
        self.search_panel.setVisible(show)
        if show:
            self.search_input.setFocus()
        # 单页视图下面板开关改变可用宽度，下一帧重新自适应
        if self.doc and not getattr(self, "page_view_mode", False):
            QTimer.singleShot(0, self._apply_fit_page)
        elif getattr(self, "page_view_mode", False):
            QTimer.singleShot(0, self._relayout_page_grid)

    def start_doc_search(self):
        """cp81: 执行全文搜索（PDF 走 worker；Word 内存文本同步搜）。"""
        keyword = self.search_input.text().strip()
        if not keyword:
            self.lbl_search_status.setText("请输入搜索文字")
            return
        if self._search_worker is not None and self._search_worker.isRunning():
            QMessageBox.information(self, "提示", "搜索进行中，请先取消或等待完成")
            return
        self.search_results_list.clear()

        if self.word_doc:
            # Word：内存块文本同步搜索（快，无需线程）
            total = 0
            for key, entry in (self.word_data or {}).items():
                text = (entry or {}).get("text", "") or ""
                for _idx, before, kw_text, after in collect_text_hits(text, keyword):
                    self._append_search_result(("word", key), before, kw_text, after, "段落")
                    total += 1
            self.lbl_search_status.setText(f"找到 {total} 处" if total else "未找到匹配内容")
            return

        if not self.doc:
            return
        # PDF：tobytes 快照交给 worker（与旋转/删页/去水印后状态一致）
        try:
            pdf_bytes = self.doc.tobytes()
        except Exception as e:
            self.lbl_search_status.setText(f"文档快照失败：{e}")
            return
        self.lbl_search_status.setText("正在搜索…")
        self.btn_search_cancel.show()
        self._search_hit_count = 0
        worker = DocSearchWorker(pdf_bytes, keyword, self._search_ocr_cache, parent=self)
        worker.progress_signal.connect(self._on_search_progress)
        worker.hit_signal.connect(self._on_search_hit)
        worker.finished_signal.connect(self._on_search_finished)
        worker.error_signal.connect(self._on_search_error)
        self._search_worker = worker
        worker.start()

    def _cancel_doc_search(self):
        """cp81: 取消搜索（沿用取消交互规范：状态显示搜索停止）。"""
        if self._search_worker is not None and self._search_worker.isRunning():
            self._search_worker.requestInterruption()
            # cp132: 等 worker 退出，防止 QThread 析构时仍在运行导致闪退
            self._search_worker.wait(3000)
            self._search_stop_notice = True

    def _on_search_progress(self, cur, total):
        self.lbl_search_status.setText(f"正在搜索 第 {cur}/{total} 页…（扫描页需 OCR 识别）")

    def _on_search_hit(self, page_idx, before, kw_text, after, rect_t):
        self._search_hit_count += 1
        # cp82: payload 携带命中矩形，点击时高亮定位
        self._append_search_result(("pdf", page_idx, rect_t), before, kw_text, after,
                                   f"第 {page_idx + 1} 页")

    def _on_search_finished(self, total_hits):
        self.btn_search_cancel.hide()
        if getattr(self, "_search_stop_notice", False):
            self._search_stop_notice = False
            self.lbl_search_status.setText(f"搜索停止（已找到 {total_hits} 处）")
        else:
            self.lbl_search_status.setText(f"找到 {total_hits} 处" if total_hits else "未找到匹配内容")
        self._search_worker = None

    def _on_search_error(self, msg):
        self.btn_search_cancel.hide()
        self.lbl_search_status.setText(f"搜索出错：{msg}")
        self._search_worker = None

    def _append_search_result(self, payload, before, kw_text, after, loc_text):
        """cp81: 向结果列表追加一行：黄色高亮片段 + 底部页码/位置小字。"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, payload)
        widget = QWidget()
        wl = QVBoxLayout(widget)
        wl.setContentsMargins(8, 6, 8, 6)
        wl.setSpacing(2)
        snippet = QLabel(
            f"{html.escape(before)}"
            f"<span style='background-color:#FFE066;'>{html.escape(kw_text)}</span>"
            f"{html.escape(after)}"
        )
        snippet.setTextFormat(Qt.TextFormat.RichText)
        snippet.setWordWrap(True)
        snippet.setStyleSheet("color: #18212F; font-size: 12px; background: transparent;")
        wl.addWidget(snippet)
        loc = QLabel(loc_text)
        loc.setStyleSheet("color: #8A94A3; font-size: 10px; background: transparent;")
        wl.addWidget(loc)
        item.setSizeHint(widget.sizeHint())
        self.search_results_list.addItem(item)
        self.search_results_list.setItemWidget(item, widget)

    def _on_search_result_clicked(self, item):
        """cp81: 点击结果定位：PDF 跳页+命中位置闪烁高亮；Word 按 data-key 滚动+闪烁。"""
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not payload:
            return
        kind = payload[0]
        if kind == "pdf" and self.doc:
            page_idx = max(0, min(int(payload[1]), len(self.doc) - 1))
            rect_t = payload[2] if len(payload) > 2 else None
            if getattr(self, "page_view_mode", False):
                self.set_page_view_mode(False)
            self.current_page = page_idx
            self.render_view()
            self._set_info_bar_message(f"🔍 已定位到第 {page_idx + 1} 页")
            # cp82: 命中位置半透明黄色闪烁 + 滚动到命中行
            self._flash_search_hit(rect_t)
        elif kind == "word" and self.word_preview is not None:
            target = payload[1]
            # key 经 json.dumps 转为 JS 字符串字面量（含引号），拼接属性选择器
            key_js = json.dumps(str(target))
            js = (
                "(function(){"
                f"var el=document.querySelector('[data-key=\"'+{key_js}+'\"]');"
                "if(el){el.scrollIntoView({behavior:'smooth',block:'center'});"
                "var old=el.style.backgroundColor;"
                "el.style.transition='background-color 1.2s';"
                "el.style.backgroundColor='#FFE066';"
                "setTimeout(function(){el.style.backgroundColor=old;},1400);}"
                "})();"
            )
            try:
                self.word_preview.page().runJavaScript(js)
            except Exception as e:
                logger.warning("[cp81] Word 定位失败: %s", e)

    def _flash_search_hit(self, rect_t):
        """cp82: 在单页画布上闪烁显示搜索命中矩形并滚动到该位置。

        rect_t 为 (x, y, w, h) PDF display 坐标元组；None 时仅跳页不高亮
        （如 OCR 行矩形缺失/旧缓存降级）。高亮 2.4s 后自动消失。
        """
        if not rect_t:
            return
        canvas = self.canvas_left
        if not self._is_canvas_valid(canvas):
            return
        flash = QRectF(rect_t[0], rect_t[1], rect_t[2], rect_t[3])
        # 命中矩形外扩少许，视觉上更醒目
        flash.adjust(-2, -2, 2, 2)
        canvas.flash_rect = flash
        canvas.update()
        # 滚动到命中位置（canvas 坐标 → 内容容器坐标）
        try:
            zs = canvas.zoom_scale or 1.0
            cx = int((flash.x() + flash.width() / 2) * zs)
            cy = int((flash.y() + flash.height() / 2) * zs)
            pt = canvas.mapTo(self.main_container, QPoint(cx, cy))
            self.scroll.ensureVisible(pt.x(), pt.y(), 120,
                                      max(120, self.scroll.viewport().height() // 3))
        except Exception as e:
            logger.warning("[cp82] 命中滚动定位失败: %s", e)
        # 定时清除（重复点击重启计时）
        self._search_flash_timer.start()

    def _clear_search_flash(self):
        """cp82: 清除搜索命中闪烁高亮。"""
        for canvas in (getattr(self, "canvas_left", None), getattr(self, "canvas_right", None)):
            if canvas is not None and self._is_canvas_valid(canvas) and canvas.flash_rect is not None:
                canvas.flash_rect = None
                canvas.update()

    # === cp83: 撤销/恢复 ===

    def _build_undo_snapshot(self, structural):
        """cp83: 构造一份当前状态快照。structural=True 时含 doc 字节流。

        安全审计 v40.1.4（S1）：mask-only 快照（structural=False）继承栈中最近
        结构快照的 pdf_bytes 引用——遮罩变更必然发生在某次结构快照之后、下一次
        结构变更之前，字节引用与当时 doc 结构严格一致。此前 mask-only 快照不带
        字节流，撤销跨结构快照落到 mask-only 快照时 doc 保持新结构而 page_data
        回到旧结构（页数不齐/遮罩整体错位一页，错遮+漏遮）。bytes 不可变，
        引用复用零拷贝、零额外内存。
        """
        pdf_bytes = None
        if structural and self.doc is not None and not self.doc.is_closed:
            try:
                new_bytes = self.doc.tobytes()
            except Exception as e:
                logger.error("[cp83] doc.tobytes 失败: %s: %s", type(e).__name__, e)
                new_bytes = None
            # P2 内存优化：若与栈顶快照字节流完全相同（长度预检 O(1) 后才 memcmp），
            # 复用同一引用，避免大 PDF 下最多 20 份重复字节流驻留。
            if new_bytes is not None and self._undo_stack:
                prev_bytes = self._undo_stack[-1].get("pdf_bytes")
                if (prev_bytes is not None and len(prev_bytes) == len(new_bytes)
                        and prev_bytes == new_bytes):
                    pdf_bytes = prev_bytes
                else:
                    pdf_bytes = new_bytes
            else:
                pdf_bytes = new_bytes
        elif not structural:
            # S1 修复：继承最近结构快照的字节引用（见 docstring）
            for prev in reversed(self._undo_stack):
                prev_bytes = prev.get("pdf_bytes")
                if prev_bytes is not None:
                    pdf_bytes = prev_bytes
                    break
        return {
            "page_data": snapshot_page_data(self.page_data),
            "pdf_bytes": pdf_bytes,
            "current_page": self.current_page,
            "pdf_modified": getattr(self, "_pdf_modified", False),
        }

    def _capture_undo_state(self, structural=False):
        """cp83: 变更完成后压入快照，清空 redo 栈。

        重入守卫：_apply_snapshot 期间产生的变更不再捕捉。
        仅 PDF 模式（self.doc 存在）生效。
        """
        if self._restoring_snapshot or self.doc is None:
            return
        snap = self._build_undo_snapshot(structural)
        push_undo_snapshot(self._undo_stack, snap, self._UNDO_MAX)
        self._redo_stack.clear()
        self._refresh_undo_redo_buttons()
        # v40.1.4（F2）：压栈后做内存预算检查 + 落盘文件清扫（淘汰快照的文件删除）
        self._spill_oversized_undo_bytes()
        self._sweep_undo_spill_files()
        # cp88: 遮罩变更后节流写会话草稿；结构变更（旋转/插入/删除页）不可重建，
        # 按 Spec 立即落盘字节流（不等节流窗口，避免崩溃窗口内丢结构快照）
        if structural:
            self._draft_pdf_bytes_pending = True
            self._draft_timer.stop()
            # v40.1.4（性能 #8）：复用快照刚算出的字节流——此前这里会让
            # _flush_session_draft 再做一次 doc.tobytes() 全档序列化
            #（同一变更两次 tobytes + 主线程同步写盘，大文档冻结 0.5-1s）。
            self._flush_session_draft(pdf_bytes=snap.get("pdf_bytes"))
        else:
            self._draft_timer.start()

    def _spill_oversized_undo_bytes(self):
        """v40.1.4（F2 内存）：撤销栈字节流总量超预算时，把最旧的结构字节流落盘。

        mask-only 快照与结构快照共享同一 bytes 引用（S1 修复），故按"引用身份"
        整组转换：同引用的全部快照一并改为磁盘路径，内存才真正释放。
        落盘走 tempfile.mkstemp（POSIX 0600），最近 2 组字节流始终常驻内存，
        保证近期撤销步骤零磁盘 IO。
        """
        try:
            budget = getattr(self, "_UNDO_BYTES_BUDGET", 192 * 1024 * 1024)
            groups = {}   # id(bytes) -> {"bytes": bytes, "snaps": [snap...]}
            order = []    # 首次出现顺序（undo 栈底 → 栈顶 → redo 栈）
            for stack in (self._undo_stack, self._redo_stack):
                for snap in stack:
                    b = snap.get("pdf_bytes")
                    if b is None:
                        continue
                    key = id(b)
                    if key not in groups:
                        groups[key] = {"bytes": b, "snaps": []}
                        order.append(key)
                    groups[key]["snaps"].append(snap)
            total = sum(len(g["bytes"]) for g in groups.values())
            if total <= budget or len(order) <= 2:
                return
            import tempfile
            spilled = 0
            for key in order:
                if total <= budget or len(order) - spilled <= 2:
                    break
                g = groups[key]
                try:
                    fd, path = tempfile.mkstemp(prefix="pgundo_", suffix=".pdf")
                    with os.fdopen(fd, "wb") as f:
                        f.write(g["bytes"])
                except OSError:
                    continue  # 写盘失败保底留在内存（宁可占内存不丢撤销能力）
                for snap in g["snaps"]:
                    snap["pdf_bytes"] = None
                    snap["pdf_spill_path"] = path
                self._undo_spill_files.add(path)
                total -= len(g["bytes"])
                spilled += 1
        except Exception as e:
            logger.warning("[undo] 快照落盘检查失败: %s", type(e).__name__)

    def _sweep_undo_spill_files(self):
        """删除不再被任何快照引用的落盘文件（栈淘汰/清栈/重置后调用）。"""
        registry = getattr(self, "_undo_spill_files", None)
        if not registry:
            return
        referenced = set()
        for stack in (self._undo_stack, self._redo_stack):
            for snap in stack:
                p = snap.get("pdf_spill_path")
                if p:
                    referenced.add(p)
        for p in list(registry - referenced):
            try:
                os.remove(p)
            except OSError:
                pass
            registry.discard(p)

    def _seed_undo_baseline(self):
        """cp83: 打开文档/扫描完成后压入基线快照（保证首次撤销有底）。"""
        if self.doc is None:
            return
        self._undo_stack = [self._build_undo_snapshot(structural=True)]
        self._redo_stack = []
        self._refresh_undo_redo_buttons()
        self._sweep_undo_spill_files()  # v40.1.4（F2）：旧栈引用的落盘文件清理

    def _apply_snapshot(self, snap):
        """cp83: 恢复到指定快照（页面结构+遮罩+当前页）。"""
        if not snap:
            return
        self._restoring_snapshot = True
        structure_changed = False
        try:
            # 结构快照：重开字节流恢复页面（旋转/插入/删除回退）
            pdf_bytes = snap.get("pdf_bytes")
            if pdf_bytes is None and snap.get("pdf_spill_path"):
                # v40.1.4（F2）：超预算被落盘的字节流，应用时读回（0600 临时文件）
                try:
                    with open(snap["pdf_spill_path"], "rb") as f:
                        pdf_bytes = f.read()
                except OSError as e:
                    logger.error("[undo] 读取落盘快照失败: %s", type(e).__name__)
                    pdf_bytes = None
            if pdf_bytes:
                try:
                    new_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    old_doc = self.doc
                    self.doc = new_doc
                    if old_doc is not None and not old_doc.is_closed:
                        try:
                            old_doc.close()
                        except Exception:
                            pass
                    self._invalidate_grid_cache()
                    self._search_ocr_cache.clear()
                    structure_changed = True
                except Exception as e:
                    logger.error("[cp83] 快照重开文档失败: %s: %s", type(e).__name__, e)
            # 遮罩重建
            self.page_data = restore_page_data(snap.get("page_data"))
            self._pdf_modified = snap.get("pdf_modified", False)
            total = len(self.doc) if self.doc else 0
            self.current_page = max(0, min(snap.get("current_page", 0), max(0, total - 1)))
            if getattr(self, "_pdf_modified", False) and hasattr(self, "btn_save"):
                self.btn_save.setEnabled(True)
            # 安全审计 v40.1.4（P2-1）：结构恢复后刷新派生状态——
            # OCR 已扫页集 / 书签 TOC / 搜索结果都持有旧结构页码，不同步会
            # 让 O1 未扫描告警失真、书签导出回写陈旧页码、搜索定位错页。
            if structure_changed:
                self._refresh_derived_state_after_restore()
            # 重建视图
            if getattr(self, "page_view_mode", False):
                self._rebuild_page_grid()
            else:
                self.render_view()
        finally:
            self._restoring_snapshot = False
        self._refresh_undo_redo_buttons()

    def _refresh_derived_state_after_restore(self):
        """v40.1.4（P2-1）：结构恢复（undo/redo/重置）后同步派生状态。

        ① _ocr_processed_pages：按恢复后的 page_data 重建（有 ocr 命中的页）。
        近似值——"扫描过但零命中"的页不计入，可能让 O1 告警偏保守（宁可多提示
        也不静默放行未扫描导出）；旧集合的页码在新结构下无意义，必须丢弃。
        ② 书签 TOC：重读 doc，防止书签面板残留旧结构页码（导出回写错页/中止）。
        ③ 搜索结果：清空旧结构条目（定位/高亮错位）。
        """
        try:
            processed = set()
            for pn, entry in (self.page_data or {}).items():
                try:
                    if isinstance(entry, dict) and entry.get("ocr"):
                        processed.add(int(pn))
                except (TypeError, ValueError):
                    continue
            self._ocr_processed_pages = processed
        except Exception:
            self._ocr_processed_pages = set()
        try:
            if hasattr(self, "_load_pdf_toc"):
                self._load_pdf_toc()
        except Exception as e:
            logger.warning("[undo] 结构恢复后刷新书签失败: %s", type(e).__name__)
        try:
            worker = getattr(self, "_search_worker", None)
            if worker is not None and worker.isRunning():
                worker.requestInterruption()
                worker.wait(2000)
            self._search_worker = None
            if hasattr(self, "search_results_list"):
                self.search_results_list.clear()
            if hasattr(self, "lbl_search_status"):
                self.lbl_search_status.setText("")
        except Exception:
            pass

    def undo(self):
        """cp83: 撤销上一步。栈顶为当前状态，弹出后恢复上一个。"""
        if len(self._undo_stack) < 2:
            return
        current = self._undo_stack.pop()
        self._redo_stack.append(current)
        # 安全修复: 用 del 切片替代 pop(0) 循环
        if len(self._redo_stack) > self._UNDO_MAX:
            del self._redo_stack[:len(self._redo_stack) - self._UNDO_MAX]
        self._apply_snapshot(self._undo_stack[-1])
        self._set_info_bar_message("↶ 已撤销上一步")

    def redo(self):
        """cp83: 恢复到上一步（重做）。"""
        if not self._redo_stack:
            return
        snap = self._redo_stack.pop()
        push_undo_snapshot(self._undo_stack, snap, self._UNDO_MAX)
        self._apply_snapshot(snap)
        self._sweep_undo_spill_files()
        self._set_info_bar_message("↷ 已恢复到上一步")

    def reset_document(self):
        """cp121: 重置文档——恢复到刚打开时的初始状态（清除所有遮罩与编辑）。

        _undo_stack[0] 是文档加载完成时 _seed_undo_baseline 压入的基线快照
        （无任何遮罩/编辑），恢复到它即可。恢复后重新 seed 栈（基线成为唯一快照），
        清空 redo，与刚打开文档时的状态完全一致。

        cp_bookmark: 书签栏的用户编辑（增删改/重命名）与手动框选全文遮罩触发的
        临时脱敏规则也一并清除——重新从 doc 读取原始 TOC 刷新面板，
        行为与"重新打开文档"完全一致。
        """
        if self.doc is None or not self._undo_stack:
            return
        # 弹出确认对话框（重置不可通过 redo 找回）
        reply = QMessageBox.question(
            self, "重置文档",
            "将清除当前文档的所有遮罩与编辑，恢复到刚打开时的状态。\n确定继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        # v40.1.4（用户反馈）：重置 = 完整回到初始状态——先退出提取/截去模式，
        # 防止其持有的旧结构片段/预览在重置后错位
        if getattr(self, "_extract_active", False):
            try:
                if hasattr(self, "btn_extract"):
                    self.btn_extract.blockSignals(True)
                    self.btn_extract.setChecked(False)
                    self.btn_extract.blockSignals(False)
                self.exit_extract_mode()
            except Exception:
                pass
        if getattr(self, "_crop_active", False):
            try:
                if hasattr(self, "btn_crop"):
                    self.btn_crop.blockSignals(True)
                    self.btn_crop.setChecked(False)
                    self.btn_crop.blockSignals(False)
                self.exit_crop_mode()
            except Exception:
                pass
        baseline = self._undo_stack[0]
        self._apply_snapshot(baseline)
        # 重新 seed：基线成为唯一快照，清空 redo
        self._undo_stack = [baseline]
        self._redo_stack = []
        self._refresh_undo_redo_buttons()
        # cp_bookmark: 重置书签状态——清临时脱敏规则 + 从 doc 重读原始 TOC 刷新面板
        # （等价于"重新打开文档"：用户的手动编辑 toc_edited / 全文遮罩临时脱敏全部丢弃；
        # v40.1.4 去掉 _toc_loaded 门控——面板存在即强制重读，杜绝残留被替换的标题）
        self._targeted_toc_rules = None
        # v40.1.4（用户反馈）：重置清"书签脱敏已应用"标志——显示计算
        # 据此回到原始标题（此前勾选还开着时重置后仍显示脱敏标题）
        self._bookmark_redact_applied = False
        if hasattr(self, "_load_pdf_toc"):
            try:
                self._load_pdf_toc()
            except Exception as e:
                logger.warning("[重置] 刷新书签面板失败: %s", type(e).__name__)
        # v40.1.4：导出按钮回落禁用（基线无修改），会话草稿一并清除
        # （否则崩溃恢复会把已重置掉的遮罩/结构草稿又带回来）
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(False)
        try:
            if getattr(self, "file_path", None):
                self._session_store.delete_draft(self.file_path)
        except Exception:
            pass
        self._set_info_bar_message("↺ 已重置到初始状态")

    def _refresh_undo_redo_buttons(self):
        """cp83/cp121: 按栈状态启用/禁用撤销/恢复/重置按钮。"""
        if hasattr(self, "btn_undo"):
            self.btn_undo.setEnabled(len(self._undo_stack) >= 2)
        if hasattr(self, "btn_redo"):
            self.btn_redo.setEnabled(bool(self._redo_stack))
        # cp121: 重置按钮——有文档且栈里不止基线（有可清除的编辑）时启用
        if hasattr(self, "btn_reset"):
            self.btn_reset.setEnabled(self.doc is not None and len(self._undo_stack) >= 2)

    # === cp88: 会话草稿（防丢进度） ===

    def _flush_session_draft(self, pdf_bytes=None):
        """cp88: 把当前遮罩进度写入草稿（轻量 JSON；结构变更时附带字节流）。

        v40.1.4（性能 #8）：pdf_bytes 可由调用方传入（_capture_undo_state 刚算出
        的快照字节流直接复用），避免同一变更做两次 doc.tobytes() 全档序列化。
        """
        if self.doc is None or not self.file_path or self.doc_type != 'pdf':
            return
        try:
            if pdf_bytes is None and self._draft_pdf_bytes_pending and not self.doc.is_closed:
                try:
                    pdf_bytes = self.doc.tobytes()
                except Exception as e:
                    logger.error("[cp88] 结构快照字节流失败: %s: %s", type(e).__name__, e)
            c = self.current_color
            self._session_store.save_draft(
                self.file_path,
                snapshot_page_data(self.page_data),
                current_page=self.current_page,
                mask_color=(c.red(), c.green(), c.blue()),
                pdf_modified=getattr(self, "_pdf_modified", False),
                pdf_bytes=pdf_bytes,
            )
            self._draft_pdf_bytes_pending = False
            self._session_store.prune_drafts(keep=20)
        except Exception as e:
            # 草稿保存失败不影响主流程
            logger.warning("[cp88] 草稿保存异常: %s: %s", type(e).__name__, e)

    def _maybe_restore_session_draft(self):
        """cp88: 打开 PDF 后检查草稿，提示恢复/放弃。

        返回是否执行了恢复（供调用方决定是否重建撤销基线）。
        """
        try:
            draft, match = self._session_store.load_draft(self.file_path)
        except Exception as e:
            logger.warning("[cp88] 草稿读取异常: %s: %s", type(e).__name__, e)
            return False
        if not draft:
            return False
        total_masks = sum(
            len(entry.get(k, [])) for entry in draft["page_data"].values()
            for k in ("ocr", "manual"))
        if total_masks <= 0 and not draft.get("pdf_modified"):
            return False
        saved_str = datetime.fromtimestamp(draft.get("saved_at", 0)).strftime("%m-%d %H:%M")
        warn = "" if match == "exact" else "\n\n⚠ 原文件已变化，恢复后遮罩位置可能错位。"
        reply = QMessageBox.question(
            self, "发现未完成的脱敏进度",
            f"检测到该文档未完成的脱敏进度（{total_masks} 处遮罩，保存于 {saved_str}）。\n\n"
            f"是否恢复？{warn}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if reply != QMessageBox.StandardButton.Yes:
            self._session_store.delete_draft(self.file_path)
            return False
        # 结构快照：先换 doc
        if draft.get("pdf_snap"):
            snap_bytes = self._session_store.load_pdf_snap(self.file_path)
            if snap_bytes:
                try:
                    new_doc = fitz.open(stream=snap_bytes, filetype="pdf")
                    old_doc = self.doc
                    self.doc = new_doc
                    if old_doc is not None and not old_doc.is_closed:
                        old_doc.close()
                    self._invalidate_grid_cache()
                except Exception as e:
                    logger.error("[cp88] 结构快照恢复失败: %s: %s", type(e).__name__, e)
        # 遮罩重建（补齐缺页条目，保持 page_data 全页覆盖不变式）
        restored = restore_page_data(draft["page_data"])
        total = len(self.doc) if self.doc else 0
        self.page_data = {i: restored.get(i, {"ocr": [], "manual": []}) for i in range(total)}
        self._pdf_modified = bool(draft.get("pdf_modified", False))
        self.current_page = max(0, min(draft.get("current_page", 0), max(0, total - 1)))
        mc = draft.get("mask_color") or [0, 0, 0]
        try:
            self.current_color = QColor(int(mc[0]), int(mc[1]), int(mc[2]))
        except (ValueError, TypeError, IndexError):
            pass
        self.render_view()
        self._set_info_bar_message(f"↩ 已恢复脱敏进度（{total_masks} 处遮罩）")
        return True

    # === cp90: 清理使用痕迹 ===

    def _webengine_cache_dirs(self):
        """cp90: WebEngine 预览缓存目录（运行时动态获取，不硬编码）。"""
        dirs = []
        try:
            from PyQt6.QtWebEngineCore import QWebEngineProfile
            prof = QWebEngineProfile.defaultProfile()
            for p in (prof.cachePath(), prof.persistentStoragePath()):
                if p and os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
        except Exception as e:
            logger.warning("[cp90] 获取 WebEngine 缓存目录失败: %s: %s", type(e).__name__, e)
        return dirs

    def _app_log_files(self):
        """cp90: 应用日志文件列表（logs/*.log）。"""
        log_dir = str(_resolve_log_dir())
        out = []
        try:
            for name in os.listdir(log_dir):
                if name.endswith(".log"):
                    out.append(os.path.join(log_dir, name))
        except OSError:
            pass
        return out, log_dir

    def _open_trace_clean_dialog(self, parent_dialog=None):
        """cp90: 装配痕迹数据源与白名单并弹出对话框。"""
        from privacyguard.trace_cleaner import collect_trace_items
        from privacyguard.utils.temp_manager import list_stale_temp_entries, active_temp_entries
        import tempfile
        sessions_dir = self._session_store.base_dir
        # temp：崩溃残留 + 当前活跃追踪（导出完成后可安全清）
        temp_entries = list(set(list_stale_temp_entries()) | active_temp_entries())
        web_dirs = self._webengine_cache_dirs()
        log_files, log_dir = self._app_log_files()
        items = collect_trace_items(sessions_dir=sessions_dir, temp_entries=temp_entries,
                                    web_cache_dirs=web_dirs, log_files=log_files)
        # 白名单根：仅应用自有目录（sessions / 系统 temp / WebEngine profile / logs）
        allowed_roots = [sessions_dir, tempfile.gettempdir(), log_dir] + web_dirs
        self._trace_allowed_roots = allowed_roots
        # cp118 接线修复：传 main_window=self，否则从设置窗口进入时
        # parent_dialog=SettingsDialog，TraceCleanDialog 的 _main_window 回退到
        # SettingsDialog，_mark_webengine_clear_pending / _on_traces_cleaned 静默跳过。
        dlg = TraceCleanDialog(parent_dialog or self, items, allowed_roots,
                              main_window=self)
        dlg.exec()

    def _mark_webengine_clear_pending(self):
        """cp90: WebEngine 缓存被占用时写 pending 标记，下次启动早期清除。"""
        from privacyguard.trace_cleaner import WEBENGINE_PENDING_MARKER, write_pending_webengine
        marker = os.path.join(self._session_store.base_dir, WEBENGINE_PENDING_MARKER)
        write_pending_webengine(marker, self._webengine_cache_dirs())

    def _on_traces_cleaned(self, cleaned_keys):
        """cp90: 痕迹清理后的状态同步（草稿被清时重置相关运行态）。"""
        if "sessions" in (cleaned_keys or []):
            # 当前文档草稿已随目录被清，停掉待写计时器避免重建
            if getattr(self, "_draft_timer", None) is not None:
                self._draft_timer.stop()
            self._draft_pdf_bytes_pending = False

    def render_view(self):
        if not self.doc: return
        # cp67: 页面视图模式下只刷新网格遮罩层（共享列表已变，无需重画页面 pixmap）
        if getattr(self, "page_view_mode", False):
            self._refresh_visible_grid_thumbs(overlay_only=True)
            total = len(self.doc)
            self.lbl_page.setText(f"{self.current_page + 1} / {total}")
            return
        # v37.0.9: 添加 canvas 有效性检查
        if not self._is_canvas_valid(self.canvas_left):
            logger.warning("[警告] canvas_left 无效，跳过渲染")
            return
        self._render_single_page(self.canvas_left, self.current_page)
        if self.dual_view:
            if self.current_page + 1 < len(self.doc):
                if self._is_canvas_valid(self.canvas_right):
                    self._render_single_page(self.canvas_right, self.current_page + 1)
                    self.canvas_right.show()
            else:
                if self._is_canvas_valid(self.canvas_right):
                    self.canvas_right.hide()

        total = len(self.doc)
        display = f"{self.current_page + 1}"
        if self.dual_view and self.current_page + 1 < total:
            display += f"-{self.current_page + 2}"
        self.lbl_page.setText(f"{display} / {total}")
        self.lbl_zoom.setText(f"{int(self.zoom_level * 100)}%")
        self._refresh_toolbar_responsiveness()
        self._refresh_workbench_context()

    def _render_page_to_canvas(self, canvas, page_idx, zoom):
        """cp67: 参数化 zoom 的页面渲染核心（单页视图与页面视图网格共用）。

        Returns:
            QPixmap | None: 渲染成功返回 pixmap（供网格缓存），失败返回 None
        """
        if not self._is_canvas_valid(canvas):
            return None
        try:
            # cp122-fix 接线修复：同步 canvas.page_index 供 vertical_region_selected
            # 信号使用。此前缺失此赋值导致截去/提取跨页时信号始终发射 page_idx=0，
            # 截去/提取错误地作用在第 1 页。修复行在重构中丢失，此处补回。
            canvas.page_index = page_idx
            page = self.doc[page_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img_fmt = QImage.Format.Format_RGB888
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, img_fmt).copy()
            data = self.page_data.get(page_idx)
            if data is None:
                return None
            pixmap = QPixmap.fromImage(qimg)
            # 使用安全的更新方法（共享列表引用）
            self._safe_canvas_update(canvas, pixmap, zoom, data['ocr'], data['manual'])
            self._safe_canvas_set_mask_color(canvas, self.current_color)
            # v37.7.13 cp43: 同步手动替换开关到 canvas
            canvas.manual_replace_prompt = self.manual_replace_prompt
            return pixmap
        except RuntimeError as e:
            logger.error("[错误] 渲染页面 %s 时出错: %s", page_idx, e)
        except Exception as e:
            logger.error("[错误] 渲染页面 %s 时发生意外错误: %s", page_idx, e)
        return None

    def _render_single_page(self, canvas, page_idx):
        """v7.0 风格渲染 - 直接传递列表引用
        v37.0.9: 添加异常处理防止 canvas 被删除后崩溃
        cp67: 核心抽取到 _render_page_to_canvas（参数化 zoom，与网格共用）
        """
        self._render_page_to_canvas(canvas, page_idx, self.zoom_level)

    def on_rect_added(self, page_idx, rect):
        """由于使用共享列表引用，canvas 已直接修改列表，这里只需刷新视图"""
        # self.page_data[page_idx]['manual'].append(rect)  # 不需要，canvas 已经添加
        self.render_view()
        self._capture_undo_state()  # cp83: 框选添加遮罩后快照

    def on_rect_removed(self, page_idx, rect_idx, is_manual):
        """由于使用共享列表引用，canvas 已直接修改列表，这里只需刷新视图"""
        # if is_manual: del self.page_data[page_idx]['manual'][rect_idx]  # 不需要，canvas 已经删除
        # else: del self.page_data[page_idx]['ocr'][rect_idx]
        self.render_view()
        self._capture_undo_state()  # cp83: 右键删除遮罩后快照

    def change_page(self, delta):
        if not self.doc: return
        step = 2 if self.dual_view else 1
        new_page = self.current_page + (delta * step)
        if new_page < 0: new_page = 0
        if new_page >= len(self.doc): return
        self.current_page = new_page
        self.render_view()
        self.scroll.verticalScrollBar().setValue(0)

    def go_first(self):
        if not self.doc: return
        self.current_page = 0
        self.render_view()
        self.scroll.verticalScrollBar().setValue(0)

    def go_last(self):
        if not self.doc: return
        self.current_page = len(self.doc) - 1
        if self.dual_view and self.current_page % 2 != 0: self.current_page -= 1
        self.render_view()
        self.scroll.verticalScrollBar().setValue(0)

    def handle_page_change_request(self, delta):
        """处理滚轮翻页请求（v35.1 新增）

        Args:
            delta: 翻页数量，正值=向后翻页，负值=向前翻页
                   1/-1 = 普通滚轮（需检测边缘）
                   2/-2 = Shift+滚轮（快速翻页）
        """
        if not self.doc:
            return

        # 快速翻页（Shift+滚轮）：直接翻页，不检测边缘
        if abs(delta) >= 2:
            self.change_page(1 if delta > 0 else -1)
            return

        # 普通滚轮：检测滚动条位置，只在边缘时翻页
        scroll_bar = self.scroll.verticalScrollBar()
        at_top = scroll_bar.value() <= scroll_bar.minimum() + 10
        at_bottom = scroll_bar.value() >= scroll_bar.maximum() - 10

        # 向上滚动且在顶部 → 上一页
        if delta < 0 and at_top and self.current_page > 0:
            self.change_page(-1)
            # 翻页后滚动到底部，便于连续向上翻页
            QApplication.processEvents()
            scroll_bar.setValue(scroll_bar.maximum())
        # 向下滚动且在底部 → 下一页
        elif delta > 0 and at_bottom and self.current_page < len(self.doc) - 1:
            self.change_page(1)
            # 翻页后滚动到顶部
            scroll_bar.setValue(0)

    def keyPressEvent(self, event):
        """键盘快捷键处理（v35.1 新增）

        快捷键列表：
        - PageUp: 上一页
        - PageDown: 下一页
        - Home: 首页
        - End: 尾页
        - Space/Shift+Space: 翻页
        - Ctrl/Cmd + +/-: 缩放
        - Ctrl/Cmd + 0: 适应页面
        """
        key = event.key()
        modifiers = event.modifiers()

        # PageUp: 上一页
        if key == Qt.Key.Key_PageUp:
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.change_page(-5)  # Shift+PageUp 快速翻页
            else:
                self.change_page(-1)
        # PageDown: 下一页
        elif key == Qt.Key.Key_PageDown:
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.change_page(5)  # Shift+PageDown 快速翻页
            else:
                self.change_page(1)
        # Home: 首页
        elif key == Qt.Key.Key_Home:
            self.go_first()
        # End: 尾页
        elif key == Qt.Key.Key_End:
            self.go_last()
        # Space: 下一页（Shift+Space: 上一页）
        elif key == Qt.Key.Key_Space:
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.change_page(-1)
            else:
                self.change_page(1)
        # Ctrl/Cmd + Plus: 放大
        elif key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal:
            if modifiers in [Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.MetaModifier]:
                self.zoom_in()
            else:
                super().keyPressEvent(event)
        # Ctrl/Cmd + Minus: 缩小
        elif key == Qt.Key.Key_Minus:
            if modifiers in [Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.MetaModifier]:
                self.zoom_out()
            else:
                super().keyPressEvent(event)
        # Ctrl/Cmd + 0: 重置缩放
        elif key == Qt.Key.Key_0:
            if modifiers in [Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.MetaModifier]:
                self.zoom_level = 1.0
                self.render_view()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def zoom_in(self):
        self.handle_zoom_request(0.25)

    def zoom_out(self):
        self.handle_zoom_request(-0.25)

    # === cp65: 手动框选识别 + 可选全文遮罩 ===

    def _handle_manual_region_prompt(self, canvas, rect):
        """cp65: 手动框选（开关开启）→ 识别框选文字 → 弹窗（可编辑/可全文遮罩/替换文本）。

        cp74: 点“取消”视为整个行为取消——不添加任何遮罩（旧逻辑会按纯遮罩添加）。
        """
        if not self.doc:
            return
        # cp133: 提取/截去模式下不应触发脱敏弹窗（右侧 interaction_disabled 已挡，
        # 但网格 canvas 路径仍可能触发，与"提取只提取不脱敏"语义冲突）
        if getattr(self, "_extract_active", False) or getattr(self, "_crop_active", False):
            return
        # cp67: 网格 canvas 携带真实页码；单/双页 canvas 按 current_page 推导
        if getattr(canvas, "grid_mode", False):
            page_idx = canvas.page_index
        else:
            page_idx = self.current_page + (1 if canvas is self.canvas_right else 0)
        if page_idx >= len(self.doc):
            page_idx = self.current_page

        # v40.1.4（F3 性能）：文字层直取（快）在主线程完成；无文字层时的
        # OCR 模型推理（首次含引擎加载约 0.9-1.5s）移入后台线程，完成后
        # 再弹编辑对话框——框选扫描件不再冻结界面。
        kind, payload = self._prepare_region_text(page_idx, rect)
        if kind == "text":
            self._continue_manual_region_prompt(canvas, rect, page_idx, payload)
            return
        if kind == "ocr":
            prior = getattr(self, "_region_ocr_worker", None)
            # v40.1.5 修复：worker 已 deleteLater 后 C++ 对象销毁，裸调 isRunning()
            # 抛 RuntimeError（真机框选复现）——sip.isdeleted 先检，已销毁视为空闲
            if prior is not None and not sip.isdeleted(prior) and prior.isRunning():
                self._set_info_bar_message("正在识别上一个框选区域，请稍候…")
                return
            self._set_info_bar_message("🔍 正在识别框选区域文字…")
            worker = _RegionOCRWorker(payload, parent=self)
            self._region_ocr_worker = worker

            def _on_region_ocr_ok(text):
                self._clear_info_bar_message()
                self._continue_manual_region_prompt(canvas, rect, page_idx, text)

            def _on_region_ocr_fail():
                self._clear_info_bar_message()
                self._continue_manual_region_prompt(canvas, rect, page_idx, "")

            worker.finished_ok.connect(_on_region_ocr_ok)
            worker.failed.connect(_on_region_ocr_fail)
            worker.finished.connect(worker.deleteLater)
            worker.start()
            return
        self._continue_manual_region_prompt(canvas, rect, page_idx, "")

    def _continue_manual_region_prompt(self, canvas, rect, page_idx, recognized):
        """cp65 后半段：识别完成后弹窗（可编辑/可全文遮罩/替换文本）。

        cp74: 点“取消”视为整个行为取消——不添加任何遮罩（旧逻辑会按纯遮罩添加）。
        """
        if not self.doc:
            return
        # 后台 OCR 期间文档可能已切换/页数变化，重新校验
        if page_idx >= len(self.doc):
            page_idx = min(page_idx, max(0, len(self.doc) - 1))

        # cp128: 提取模式下禁用全文遮罩（避免对原文档搜索造成逻辑混乱）
        dlg = ManualRegionRedactDialog(self, recognized_text=recognized,
                                       disable_search_all=getattr(self, "_extract_active", False))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            # cp74: 取消 = 整个行为取消，不添加任何遮罩
            self._set_info_bar_message("已取消手动框选脱敏")
            return

        # cp65: 点"纯遮罩"按钮→仅遮罩框选区域，不叠加替换文本、不做全文遮罩
        if getattr(dlg, "pure_mask_only", False):
            canvas.rects_manual.append(_make_hit(rect, ""))
            self.render_view()
            if hasattr(self, "btn_save"):
                self.btn_save.setEnabled(True)
            self._capture_undo_state()  # cp83: 立即快照
            return

        replace_text = dlg.replacement_text
        canvas.rects_manual.append(_make_hit(rect, replace_text))
        self.render_view()
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(True)

        if dlg.search_whole_doc:
            terms = split_targeted_search_terms(dlg.recognized_text)
            if not terms:
                QMessageBox.information(self, "提示", "识别文字为空，无法全文查找。已仅遮罩框选区域。")
                self._capture_undo_state()  # cp83: 仅框选遮罩，立即快照
                return
            # 全文遮罩：快照由 targeted scan 完成后统一捕捉（避免双快照）
            self._start_targeted_mask_scan(terms, replace_text, page_idx, rect)
        else:
            self._capture_undo_state()  # cp83: 仅框选遮罩，立即快照

    def _prepare_region_text(self, page_idx, rect):
        """cp65/v40.1.4（F3）：框选区域文字提取的准备阶段（主线程，轻量）。

        Args:
            page_idx: 文档页码
            rect: QRectF（PDF 点坐标）

        Returns:
            ("text", str) — 文字层直接命中，无需 OCR
            ("ocr", np.ndarray) — 无文字层，返回已渲染的 BGR 图（交后台线程推理）
            ("none", "") — 区域无效，直接按空文本继续
        """
        try:
            page = self.doc[page_idx]
            clip = fitz.Rect(rect.x(), rect.y(),
                             rect.x() + rect.width(), rect.y() + rect.height()) & page.rect
            if clip.is_empty or clip.width < 2 or clip.height < 2:
                return ("none", "")
            # 优先文字层
            # cp67: get_text(clip=) 吃未旋转坐标；旋转页需把 display 框选坐标反变换
            text_clip = clip
            if getattr(page, "rotation", 0):
                text_clip = (clip * page.derotation_matrix).normalize()
            text = (page.get_text("text", clip=text_clip) or "").strip()
            if text:
                return ("text", text)
            # 无文字层（扫描件/图片区域）：3x 渲染剪裁图（渲染留主线程——
            # fitz Document 非线程安全；模型推理交 _RegionOCRWorker）
            pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0), clip=clip)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n >= 4:
                img = img[:, :, :3]
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return ("ocr", img_bgr)
        except Exception as e:
            logger.error("[cp65] 区域文字提取失败: %s: %s", type(e).__name__, e)
            return ("none", "")

    def _start_targeted_mask_scan(self, terms, replace_text, origin_page, origin_rect):
        """cp65: 按识别文字全文查找并遮罩。

        复用 OCRWorker 管线（文字层秒搜 + 扫描页逐页 OCR），但命中结果进
        manual 列表（可右键单个撤销），不覆盖已有的智能扫描 OCR 结果。
        """
        if self.active_worker is not None and self.active_worker.isRunning():
            QMessageBox.warning(self, "提示", "正在处理其他任务，请稍候再使用全文遮罩。\n本次已仅遮罩框选区域。")
            return

        # cp114: 加密 PDF 若缺编辑权限，弹窗输入 owner 密码解锁
        if self.doc and not self._ensure_edit_permission():
            self._set_info_bar_message("⏹️ 已取消——需要编辑密码")
            return

        self._targeted_origin_page = origin_page
        self._targeted_origin_rect = QRectF(origin_rect)
        self._targeted_hit_count = 0
        preview = format_targeted_terms_preview(terms)
        self._set_info_bar_message(f"🔍 正在全文查找并遮罩：{preview}")
        self.btn_scan.setEnabled(False)
        self.btn_cancel_scan.setVisible(True)
        if hasattr(self, "progress_shell"):
            self.progress_shell.show()
        self.btn_cancel_scan.setEnabled(True)
        self.active_task_type = "scan"

        keyword_rules = build_targeted_keyword_rules(terms, replace_text)
        # cp_bookmark: 若开启"支持搜索识别书签栏"，把识别词同步应用到书签标题
        # （与全文遮罩语义对称：页面正文遮罩 + 书签标题替换/删除）
        self.apply_targeted_terms_to_bookmarks(terms, replace_text)
        self.worker = OCRWorker(self.file_path, [], self.use_enhance, "\n".join(terms),
                                self.scan_level, self.offset_x, self.offset_w,
                                custom_keyword_rules=keyword_rules,
                                # cp87: 全文查找遮罩命中统一归类“全文查找”
                                rule_name_pairs=[("全文查找", ".")],
                                # cp114: 加密 PDF 重读认证
                                pdf_open_password=self._pdf_auth_password,
                                pdf_bytes=self.doc.tobytes() if self._pdf_modified else None,
                                parent=self)
        self.active_worker = self.worker
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.page_result_signal.connect(self._on_targeted_page_result)
        self.worker.error_signal.connect(self._on_ocr_error)
        self.worker.finished_signal.connect(self._on_targeted_scan_finished)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.start()

    def _on_targeted_page_result(self, page_num: int, rects: list):
        """cp65: 全文遮罩命中逐页并入 manual 列表（不覆盖已有 OCR 结果）。

        与原框选区域及已有 manual 命中重叠 >50% 的跳过，避免重复遮罩。
        """
        if page_num not in self.page_data:
            return
        manual_list = self.page_data[page_num]['manual']
        existing_rects = [_hit_rect(item) for item in manual_list]
        if page_num == getattr(self, "_targeted_origin_page", None):
            origin_rect = getattr(self, "_targeted_origin_rect", None)
            if origin_rect is not None:
                existing_rects.append(origin_rect)
        accepted = merge_targeted_hits(deduplicate_rects(rects), existing_rects)
        manual_list.extend(accepted)
        self._targeted_hit_count += len(accepted)
        self._maybe_refresh_visible_page(page_num)

    def _on_targeted_scan_finished(self, _result):
        """cp65: 全文遮罩结束（完成/取消）：复位进度条、刷新视图并提示结果。

        cp66: 进度条归零（与 _on_ocr_finished_safe 一致），避免取消后停留在
        中断时的百分比；取消与完成分别提示。
        """
        self.render_view()
        if getattr(self, '_pending_error_msg', None):
            return
        # cp66: 进度条归零，恢复常态
        self.progress.setValue(0)
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(True)
        self._capture_undo_state()  # cp83: 全文遮罩完成后快照
        count = getattr(self, "_targeted_hit_count", 0)
        was_cancelled = self.active_worker is not None and self.active_worker.isInterruptionRequested()
        if was_cancelled:
            self._set_info_bar_message("⏹️ 扫描停止")
            # cp66: 后连接的 _on_worker_finished 会覆盖信息栏文案，
            # 置标志让其在取消分支改显“扫描停止”，保证最终展示一致
            self._targeted_stop_notice = True
            QMessageBox.information(
                self, "扫描停止",
                f"全文查找已停止，已扫描部分新增 {count} 处遮罩并保留。\n"
                "如有误遮罩，可在页面上右键单个遮罩进行撤销。"
            )
            return
        QMessageBox.information(
            self, "全文遮罩完成",
            f"已根据识别文字在全文新增 {count} 处遮罩（不含原框选区域）。\n"
            "如有误遮罩，可在页面上右键单个遮罩进行撤销。"
        )

    def _ensure_edit_permission(self):
        """cp114: 脱敏/保存前检测编辑权限，若受限弹窗输入 owner 密码解锁。

        PDF 可设有 user password（打开）+ owner password（编辑）。用户用 user
        password 打开后 permissions 可能缺 MODIFY 位。PyMuPDF 虽不强制权限，
        但部分加密 PDF 在 user 认证下 add_redact_annot/apply_redactions 行为
        异常。此方法检测缺失 MODIFY 权限时弹 QInputDialog 输入 owner 密码，
        认证成功且获 MODIFY 权限则更新 _pdf_auth_password。

        Returns:
            True: 可继续脱敏/保存（已有权限或 owner 密码解锁成功）
            False: 用户取消，应中止操作
        """
        if not self.doc or (hasattr(self.doc, "is_closed") and self.doc.is_closed):
            return True
        import fitz
        try:
            perms = int(self.doc.permissions)
        except Exception:
            # 安全审计 v40.1: 无法判断权限时保守失败（而非放行）——
            # 畸形/特殊加密 PDF 可能在这里抛错，放行会绕过 owner 密码弹窗，
            # 让缺权限的脱敏操作静默进行（可能产出不完整结果）。
            # 保守路径：走下方缺 MODIFY 权限的弹窗流程，让用户决定。
            perms = 0
        if perms & fitz.PDF_PERM_MODIFY:
            return True  # 已有修改权限，无需弹窗

        # 缺 MODIFY 权限——弹窗输入 owner 密码
        file_name = os.path.basename(self.file_path) if self.file_path else "文档"
        from PyQt6.QtWidgets import QInputDialog, QLineEdit
        while True:
            pw, ok = QInputDialog.getText(
                self, "需要编辑密码",
                f"{file_name} 受编辑密码保护，\n执行脱敏/保存需输入编辑（owner）密码：",
                echo=QLineEdit.EchoMode.Password,
            )
            if not ok or not pw:
                return False  # 用户取消
            if self.doc.authenticate(pw) > 0:
                try:
                    new_perms = int(self.doc.permissions)
                except Exception:
                    new_perms = 0
                if new_perms & fitz.PDF_PERM_MODIFY:
                    self._pdf_auth_password = pw
                    return True
                QMessageBox.warning(self, "权限不足",
                                    "该密码未授予编辑权限，请输入 owner（编辑）密码。")
                continue
            QMessageBox.warning(self, "密码错误", "密码不正确，请重试。")

    def start_ocr(self):
        """智能扫描 - 支持 PDF 和 Word（v37.0.5: 增强错误处理）"""
        # 线程安全检查：防止重复启动
        if self.active_worker is not None:
            if self.active_worker.isRunning():
                QMessageBox.warning(self, "提示", "正在处理中，请稍候...")
                return

        # Permission cancellation must not leave scan controls in a running state.
        if self.doc and not self._ensure_edit_permission():
            self._set_info_bar_message("⏹️ 已取消——需要编辑密码")
            return

        self._set_info_bar_message("🔍 正在扫描敏感信息...")
        self.btn_scan.setEnabled(False)
        self.btn_cancel_scan.setVisible(True)  # 显示取消按钮（v36.3）
        if hasattr(self, "progress_shell"):
            self.progress_shell.show()
        self.btn_cancel_scan.setEnabled(True)
        self.active_task_type = "scan"

        # PDF 处理
        if self.doc:
            # v37.5.0: 检测是否启用印章检测
            seal_detection_enabled = "__SEAL_DETECTION__" in self.active_rules
            # cp60: 检测是否启用签名手印检测
            signature_detection_enabled = "__SIGNATURE_DETECTION__" in self.active_rules
            if DEBUG_MODE:
                logger.debug("[OCR] active_rules: %s", self.active_rules)
                logger.debug("[OCR] 印章检测启用: %s, 签名手印检测启用: %s", seal_detection_enabled, signature_detection_enabled)
            self._ocr_processed_pages = set()
            # v37.4.0: 只使用 RapidOCR，移除 use_char_level_ocr 参数
            self.worker = OCRWorker(self.file_path, self.active_rules, self.use_enhance, self.custom_keywords,
                                    self.scan_level, self.offset_x, self.offset_w,
                                    seal_detection_enabled=seal_detection_enabled,
                                    custom_keyword_rules=self.custom_keyword_rules,
                                    signature_detection_enabled=signature_detection_enabled,
                                    # cp87: 规则名反查表，命中项携 rule 供脱敏报告分类
                                    rule_name_pairs=list(DEFAULT_RULES.items()),
                                    # cp114: 加密 PDF 重读认证
                                    pdf_open_password=self._pdf_auth_password,
                                    pdf_bytes=self.doc.tobytes() if self._pdf_modified else None,
                                    parent=self)
            self.active_worker = self.worker  # 追踪线程
            self.worker.progress_signal.connect(self.progress.setValue)
            # v36.4: 使用线程安全的逐页结果信号
            self.worker.page_result_signal.connect(self._on_ocr_page_result)
            # v37.0.5: 连接错误信号
            self.worker.error_signal.connect(self._on_ocr_error)
            # 先连接原有的完成处理，再连接清理
            self.worker.finished_signal.connect(self._on_ocr_finished_safe)
            self.worker.finished_signal.connect(self._on_worker_finished)
            self.worker.start()
            # v40.1.4（用户反馈·实时）：点击"智能脱敏"即时刷新书签脱敏预览——
            # 书签标题的脱敏规则此刻已确定（高级设置关键词），不等整个扫描跑完
            # 才变化；与全文遮罩的即时应用语义一致。取消扫描同样保留（与页面
            # 遮罩"已保留部分结果"语义对称）。
            if getattr(self, "bookmark_redact_enabled", False):
                self._bookmark_redact_applied = True
                try:
                    self.refresh_bookmark_preview()
                except Exception as e:
                    logger.warning("[书签] 扫描开始时刷新预览失败: %s", type(e).__name__)
        # Word 处理
        elif self.word_doc:
            self.worker = WordWorker(self.word_doc, self.word_data, self.active_rules,
                                     self.custom_keywords, self.replacement_text, parent=self)
            self.active_worker = self.worker  # 追踪线程
            self.worker.progress_signal.connect(self.progress.setValue)
            # 先连接原有的完成处理，再连接清理
            self.worker.finished_signal.connect(self.word_scan_finished)
            self.worker.finished_signal.connect(self._on_worker_finished)
            self.worker.start()

    def cancel_ocr_scan(self):
        """取消智能脱敏扫描（v36.3）"""
        if self.active_worker and self.active_worker.isRunning():
            if self.active_task_type == "batch_replace":
                title = "确认停止"
                text = "确定要停止批量替换吗？\n已完成的文件会被保留。"
            else:
                title = "确认取消"
                text = "确定要停止扫描吗？\n已扫描的进度将被保留。"
            reply = QMessageBox.question(
                self,
                title,
                text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                if self.active_task_type == "batch_replace":
                    self._set_info_bar_message("⏹️ 正在停止批量替换...")
                    self._append_batch_log("收到停止指令，正在安全结束批量任务。", "warning")
                else:
                    self._set_info_bar_message("⏹️ 正在停止扫描...")
                self.btn_cancel_scan.setEnabled(False)  # 防止重复点击
                self.active_worker.requestInterruption()  # 请求中断
                if self.active_task_type == "batch_replace" and hasattr(self, "batch_worker") and self.batch_worker:
                    self.batch_worker.provide_error_decision("stop")
                # Worker会在完成后通过finished_signal通知主线程

    def _on_worker_finished(self):
        """v37.0.6: 工作线程完成后的清理 + 延迟错误显示"""
        # v37.0.6: 等待线程完全终止，防止死锁
        finished_worker = self.active_worker
        if finished_worker and finished_worker.isRunning():
            if not finished_worker.wait(3000):  # 最多等待 3 秒
                # v40.2.3: 超时未退（大文档回填期）→ 断连防信号落入下次扫描
                # （复用 _app_exit_cleanup 的兜底写法），并延迟销毁
                logger.warning("[Worker] 完成等待超时，断开信号延迟销毁")
                try:
                    finished_worker.disconnect()
                except TypeError:
                    pass
        if finished_worker is not None:
            # v40.2.3: 退休 worker 延迟销毁——此前 worker 作为 MainWindow 的
            # Qt child 永不释放，v40.2.3 起每个都带着回填缓存（10-60MB 级），
            # 多次扫描会累积滞留
            if finished_worker.isRunning():
                finished_worker.finished.connect(finished_worker.deleteLater)
            else:
                finished_worker.deleteLater()

        was_cancelled = self.active_worker and self.active_worker.isInterruptionRequested()
        word_incomplete = bool(self.word_doc and getattr(self, '_word_scan_meta', None)
                               and self._word_scan_meta.get('was_cancelled'))
        self.active_worker = None
        self.active_task_type = None
        self.btn_scan.setEnabled(True)
        self.btn_cancel_scan.setVisible(False)  # 隐藏取消按钮
        if hasattr(self, "progress_shell"):
            self.progress_shell.hide()
        self.btn_cancel_scan.setEnabled(True)
        self._sync_ui_mode()

        if word_incomplete:
            self._set_info_bar_message("⚠️ Word 扫描未完整完成，请复核后再导出")
        elif was_cancelled:
            # cp66: 全文遮罩取消时按用户预期显示“扫描停止”
            if getattr(self, "_targeted_stop_notice", False):
                self._targeted_stop_notice = False
                self._set_info_bar_message("⏹️ 扫描停止")
            else:
                self._set_info_bar_message("⏹️ 扫描已取消，已保留部分结果")
        elif not getattr(self, '_pending_error_msg', None):
            self._set_info_bar_message("✅ 扫描完成！")
            # v40.1.4（用户反馈 #1）：书签脱敏跟随"智能脱敏"动作生效——
            # 开关开启时扫描完成刷新书签预览；仅改设置不再自动应用（可经重置还原）
            if getattr(self, "bookmark_redact_enabled", False) and self.doc is not None:
                self._bookmark_redact_applied = True  # 动作驱动：面板未开过也置位
                try:
                    self.refresh_bookmark_preview()
                except Exception as e:
                    logger.warning("[书签] 扫描后刷新预览失败: %s", type(e).__name__)

        # v37.0.6: 线程清理完成后，延迟显示错误对话框（非阻塞）
        if hasattr(self, '_pending_error_msg') and self._pending_error_msg:
            error_msg = self._pending_error_msg
            self._pending_error_msg = None
            QTimer.singleShot(100, lambda: self._show_deferred_error(error_msg))

    def _show_deferred_error(self, error_msg: str):
        """v37.0.6: 安全显示错误对话框（在线程清理完成后调用）"""
        QMessageBox.critical(
            self,
            "OCR 错误",
            f"智能脱敏遇到问题：\n\n{error_msg}\n\n"
            "可能的解决方案：\n"
            "1. 重新安装 OCR 依赖: pip install rapidocr\n"
            "2. 安装 Visual C++ 运行库（Windows）\n"
            "3. 如果是扫描版 PDF，请尝试使用文本版 PDF"
        )

    # v37.0.6: 非阻塞 OCR 错误处理
    def _on_ocr_error(self, error_msg: str):
        """v37.0.6: 非阻塞处理 OCR 错误（存储错误，延迟到线程清理后显示）"""
        logger.error("[OCR ERROR] 扫描失败（详情仅在当前会话弹窗显示）")
        self._set_info_bar_message(f"❌ OCR 错误: {error_msg[:50]}...")
        # v37.0.6: 存储错误消息，延迟到线程清理完成后显示
        # 避免在模态对话框阻塞主线程时形成死锁
        self._pending_error_msg = error_msg

    # v36.4: 线程安全的 OCR 结果处理方法
    def _on_ocr_page_result(self, page_num: int, rects: list):
        """v36.4: 线程安全 - 接收单页 OCR 结果（在主线程执行）

        v37.7.17 cp47: 原地更新 ocr 列表保持 canvas 引用（canvas.rects_ocr 直接引用此 list），
        节流刷新当前可见页 canvas 让遮罩实时显示，节约资源（不重画 pix 图）。
        """
        self._ocr_processed_pages.add(page_num)
        if page_num in self.page_data:
            # 去重：移除重复或高度重叠的矩形
            deduped = deduplicate_rects(rects)
            # cp47: 原地更新 list，保持 canvas 持有的引用不变
            existing = self.page_data[page_num]['ocr']
            existing.clear()
            existing.extend(deduped)
            if DEBUG_MODE and len(rects) != len(deduped):
                logger.debug("[DEBUG] 页面%s: 去重前%s个矩形, 去重后%s个", page_num, len(rects), len(deduped))
            # cp47: 节流刷新当前可见页 canvas
            self._maybe_refresh_visible_page(page_num)

    def _maybe_refresh_visible_page(self, page_num: int):
        """v37.7.17 cp47: OCR 过程中节流刷新当前可见页 canvas。

        原地更新 ocr list 后，canvas 持有的引用自动看到新数据，只需 canvas.update()
        重绘遮罩层（不重画 pix 图），节约资源。节流间隔 300ms 避免频繁重绘；
        OCR 完成时 _on_ocr_finished_safe 会做最终 render_view()。
        """
        now = time.time()
        if now - getattr(self, '_ocr_live_refresh_ts', 0.0) < 0.3:
            return
        if not self.doc or self.current_page is None:
            return
        # cp67: 页面视图模式下刷新对应网格缩略 canvas（共享列表，仅重绘遮罩层）
        if getattr(self, "page_view_mode", False):
            grid_canvas = self._grid_canvases.get(page_num)
            if grid_canvas is not None and self._is_canvas_valid(grid_canvas):
                pix = grid_canvas.pixmap()
                if pix is not None and not pix.isNull():
                    grid_canvas.update()
                    self._ocr_live_refresh_ts = now
            return
        canvas = None
        if page_num == self.current_page:
            canvas = self.canvas_left
        elif self.dual_view and self.current_page + 1 == page_num and self.current_page + 1 < len(self.doc):
            canvas = self.canvas_right
        if canvas is not None and self._is_canvas_valid(canvas):
            canvas.update()
            self._ocr_live_refresh_ts = now

    def _on_ocr_finished_safe(self, _):
        """v36.4: 线程安全 - OCR 完成处理（在主线程执行）

        参数 _ 是空字典，保留以兼容信号签名
        """
        self.render_view()
        self.progress.setValue(0)
        if getattr(self, '_pending_error_msg', None):
            return

        # 统计已扫描的页面
        scanned_pages = len(self._ocr_processed_pages) if self._ocr_processed_pages else 0
        total_pages = len(self.page_data)
        was_cancelled = self.active_worker is not None and self.active_worker.isInterruptionRequested()
        self._capture_undo_state()  # cp83: 智能扫描完成/取消后快照（部分结果也可撤销）

        # 判断是部分结果还是完整结果（以取消状态为准，避免“无命中=已取消”误判）
        if was_cancelled:
            QMessageBox.information(
                self,
                "扫描已取消",
                f"已扫描 {scanned_pages}/{total_pages} 页，\n部分结果已保留，可以继续编辑。"
            )
        else:
            QMessageBox.information(self, "完成", "智能扫描已完成！")

    def word_scan_finished(self, results):
        """Word 文档扫描完成（v36.5: 线程安全）"""
        results_copy = dict(results)
        scan_meta = results_copy.pop('__scan_meta__', None)

        # v36.5: 使用锁保护 word_data 访问
        with QMutexLocker(self._word_data_lock):
            total_items = len(self.word_data)
            if scan_meta:
                processed_items = int(scan_meta.get('processed_items', total_items))
                total_from_meta = int(scan_meta.get('total_items', total_items))
                if total_from_meta > 0:
                    total_items = total_from_meta
            else:
                processed_items = total_items

            self.word_data = results_copy

            # 统计扫描结果
            total_matches = sum(len(data['ocr']) for data in self.word_data.values())
            # W2: mammoth 不转换页眉页脚，预览中不可见也不可手动脱敏，
            # 在完成提示中明示其命中数量，避免"预览看不到但保存被脱"的误命中无感知
            header_footer_matches = sum(
                len(data.get('ocr', []))
                for key, data in self.word_data.items()
                if isinstance(key, str) and key.startswith(('header_', 'footer_', 'first_page_', 'even_page_'))
            )

        self.render_word_preview()
        self.progress.setValue(0)

        was_cancelled = False
        if scan_meta is not None:
            was_cancelled = bool(scan_meta.get('cancelled', False) or scan_meta.get('error_type')
                                 or processed_items < total_items)
        elif self.active_worker is not None:
            was_cancelled = self.active_worker.isInterruptionRequested()

        # W8: 持久化扫描完成状态，供 Word 保存时按 O1 等效逻辑做二次确认
        self._word_scan_meta = {
            'was_cancelled': bool(was_cancelled),
            'scanned_blocks': processed_items,
            'total_blocks': total_items,
        }

        # W2: 构造页眉页脚提示后缀
        hf_hint = ""
        if header_footer_matches > 0:
            hf_hint = (
                f"\n\n其中页眉/页脚命中 {header_footer_matches} 处"
                "（不在预览中显示，保存时将一并脱敏）"
            )

        # 判断是部分结果还是完整结果（以取消状态为准）
        if scan_meta and scan_meta.get('error_type'):
            QMessageBox.warning(self, "扫描未完成",
                                f"Word 扫描中断（{scan_meta['error_type']}），仅处理 "
                                f"{processed_items}/{total_items} 个块。请复核后再导出。")
        elif was_cancelled:
            QMessageBox.information(
                self,
                "扫描已取消",
                f"已处理 {processed_items}/{total_items} 个段落/单元格，\n部分结果已保留，可以继续编辑。{hf_hint}"
            )
        else:
            QMessageBox.information(
                self, "完成",
                f"智能扫描已完成！\n共发现 {total_matches} 处敏感信息。{hf_hint}"
            )

    def save_pdf(self):
        """保存脱敏后的文档 - 支持 PDF 和 Word - v37.3: 安全加固，脱敏区域永久化"""
        # v36: 应用文件对话框样式
        # v37.3: PDF 脱敏安全加固 - 脱敏区域永久嵌入，不可编辑
        app = QApplication.instance()
        original_style = app.styleSheet()

        # PDF 保存
        if self.doc:
            app.setStyleSheet(self._get_file_dialog_style())
            try:
                fname, _ = QFileDialog.getSaveFileName(self, "保存 PDF", "", "PDF Files (*.pdf)")
            finally:
                app.setStyleSheet(original_style)

            if fname:
                # cp114: 加密 PDF 若缺编辑权限，弹窗输入 owner 密码解锁
                if not self._ensure_edit_permission():
                    return
                # O1: 扫描完整性校验 —— 若曾启动智能扫描但未覆盖全部页面，
                # 未扫描页可能仍含未脱敏的敏感信息，必须警告并二次确认，避免“以为脱了其实没脱”。
                total_pages = len(self.page_data)
                scanned_pages = len(getattr(self, '_ocr_processed_pages', set()) or set())
                scan_incomplete = scanned_pages < total_pages
                if scan_incomplete:
                    reply = QMessageBox.warning(
                        self,
                        "扫描未完成",
                        f"智能扫描仅覆盖 {scanned_pages}/{total_pages} 页，\n"
                        f"未扫描页面可能仍含未脱敏的敏感信息。\n\n"
                        f"确定仍要保存吗？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return

                doc_save = None
                try:
                    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    # v37.7.11 cp40: 若已被去水印修改过，直接复用 self.doc 的字节流，
                    # 避免重新打开原文件导致水印去除效果丢失
                    if getattr(self, "_pdf_modified", False) and self.doc and not self.doc.is_closed:
                        # v40.1.4（性能 #9）：plain tobytes——此处只是把修改过的 doc 快照成
                        # 新 Document 供脱敏，未引用对象的清除由下方最终 save(garbage=2) 完成，
                        # 此处 garbage=4 全档多轮压缩纯耗时（实测 200 页多花 ~2.4s）。
                        doc_save = fitz.open(stream=self.doc.tobytes(), filetype="pdf")
                        # cp114: tobytes() 默认产出解密字节流，防御性处理——
                        # 若个别 fitz 版本保留加密则用认证密码解锁
                        if doc_save.needs_pass and self._pdf_auth_password:
                            doc_save.authenticate(self._pdf_auth_password)
                    else:
                        doc_save = fitz.open(self.file_path)
                        # cp114: 加密 PDF 从磁盘重开需 authenticate 才能添加脱敏注释，
                        # 否则 add_redact_annot / apply_redactions 会失败
                        if doc_save.needs_pass:
                            if not self._pdf_auth_password or doc_save.authenticate(self._pdf_auth_password) <= 0:
                                raise RuntimeError(
                                    "文档加密密码错误，无法保存脱敏结果。\n"
                                    "请重新打开文档并输入正确密码。"
                                )
                    # v37.7.10 cp39: 按 current_color 实际 RGB 归一化（fitz fill 接受 0-1 浮点元组）
                    c = self.current_color
                    fill_col = (c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0)

                    for i in range(len(doc_save)):
                        page = doc_save[i]

                        # v37.3.1: 修复内部编辑功能 - 使用副本避免修改原始数据
                        # 从 page_data 中获取脱敏区域列表（O8: .get 兜底，避免缺页时 KeyError）
                        page_entry = self.page_data.get(i, {})
                        ocr_list = page_entry.get('ocr', [])
                        manual_list = page_entry.get('manual', [])

                        # 1. 添加脱敏注释
                        # v37.3.1: 重建 QRectF 确保不修改原始对象
                        # v37.7.13 cp43: 兼容 dict 元素 + 叠加替换文本层
                        # cp65 修复: 替换文字改用 insert_text 精确控制字号，
                        # 与屏幕预览公式（rect.height*0.75 + 宽度自适配）对齐。
                        # 旧实现把 text 交给 add_redact_annot，fitz 默认 fontsize=11
                        # 且把超 h*0.625 的请求压到 ~h*0.625，导致导出系统性偏小。
                        pending_text_layers = []  # [(rect, text, text_color), ...]
                        for r_item in ocr_list + manual_list:
                            rect_obj = _hit_rect(r_item)
                            replace_text = _hit_replace_text(r_item)
                            # 从 QRectF 提取坐标并重建，避免引用问题
                            x, y, w, h = rect_obj.x(), rect_obj.y(), rect_obj.width(), rect_obj.height()
                            rect = fitz.Rect(x, y, x + w, y + h)
                            # cp67: page_data 坐标是旋转后的 display 坐标系，而
                            # add_redact_annot 吃未旋转坐标；页面被旋转过时需乘
                            # derotation_matrix 反变换（rotation=0 时为单位阵，零影响）
                            if page.rotation:
                                rect = (rect * page.derotation_matrix).normalize()

                            # 统一走纯遮罩 annot；带替换文字的在 apply_redactions
                            # 之后用 insert_text 精确绘制（字号与屏幕对齐）
                            annot = page.add_redact_annot(rect)
                            annot.set_colors(stroke=fill_col, fill=fill_col)
                            annot.update()
                            if replace_text:
                                # 对比色：黑遮罩用白字，其余用黑字
                                cr, cg, cb = int(fill_col[0]*255), int(fill_col[1]*255), int(fill_col[2]*255)
                                lightness = (cr + cg + cb) / 3
                                text_color = (1, 1, 1) if lightness < 128 else (0, 0, 0)
                                pending_text_layers.append((rect, replace_text, text_color))

                        # v37.3: 安全加固 - 修改图像像素，彻底销毁原始内容
                        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

                        # cp65 修复: apply_redactions 之后绘制替换文字层。
                        # 字号 = rect.height*0.75 + 宽度自适配（compute_replace_text_fontsize），
                        # 与屏幕 widgets._draw_replace_text 完全对齐，导出不再偏小。
                        for rect, replace_text, text_color in pending_text_layers:
                            base_fs = max(6.0, rect.height * 0.75)
                            try:
                                text_w = fitz.get_text_length(
                                    replace_text, fontname="china-s", fontsize=base_fs)
                            except Exception:
                                text_w = 0.0
                            fs = compute_replace_text_fontsize(
                                rect.width, rect.height, replace_text, text_w)
                            # 水平居中：按文字宽度左移
                            try:
                                actual_w = fitz.get_text_length(
                                    replace_text, fontname="china-s", fontsize=fs)
                            except Exception:
                                actual_w = text_w * (fs / base_fs if base_fs else 1)
                            start_x = (rect.x0 + rect.x1) / 2 - actual_w / 2
                            # 垂直居中：baseline = 矩形垂直中心 + 字号*0.35
                            # （中文字 ascent 约占字号 0.35，经验值，与屏幕 AlignCenter 视觉一致）
                            baseline_y = (rect.y0 + rect.y1) / 2 + fs * 0.35
                            try:
                                page.insert_text(
                                    (start_x, baseline_y), replace_text,
                                    fontname="china-s", fontsize=fs,
                                    color=text_color, overlay=True)
                            except Exception:
                                pass  # 字体不可用时降级：不画文字，仅纯遮罩（安全）

                        # v37.3: 安全加固 - 删除所有注释对象，防止被 PDF 编辑器修改
                        for annot in page.annots():
                            page.delete_annot(annot)

                    # cp_bookmark: 书签脱敏 + 用户编辑回写
                    # 安全原则（审计 A1/A2/B1 修复）：
                    #   1. 规则源统一走 _collect_active_toc_rules（custom + targeted），
                    #      保证"面板所见 = 导出所写"，避免 targeted 规则漏应用致泄漏；
                    #   2. 脱敏失败必须中止导出（脱敏工具宁可失败不可漏脱）；
                    #   3. 用户删除全部书签时显式 set_toc([]) 尊重删除意图；
                    #   4. 异常日志不打印可能含敏感标题的 message。
                    try:
                        if getattr(self, "toc_edited", None) and hasattr(self, "bookmark_panel"):
                            edited_toc = self.bookmark_panel.collect_toc()
                            # edited_toc 为空也是合法状态（用户删光书签）→ 显式清空
                            doc_save.set_toc(edited_toc)
                        if getattr(self, "bookmark_redact_enabled", False):
                            toc = doc_save.get_toc(simple=True)
                            if toc:
                                # 复用预览的统一规则源，保证所见即所导
                                new_toc = redact_toc_titles(toc, self._collect_active_toc_rules())
                                doc_save.set_toc(new_toc)
                    except Exception as e:
                        # 脱敏失败：绝不能继续导出（否则可能泄漏未脱敏书签）
                        logger.error("[书签] 导出时书签处理失败: %s", type(e).__name__)
                        try:
                            doc_save.close()
                        except Exception:
                            pass
                        QApplication.restoreOverrideCursor()
                        QMessageBox.critical(
                            self, "导出失败",
                            "书签脱敏处理时出错，为防止泄漏未脱敏内容，导出已中止。\n"
                            f"错误类型：{type(e).__name__}\n"
                            "可尝试关闭书签脱敏开关后重试，或检查 PDF 书签是否损坏。")
                        return

                    # v37.3: 安全加固 - 垃圾回收+压缩彻底删除未引用对象
                    # v40.1.4（性能 #9）：garbage 4→2——apply_redactions 已在像素级销毁
                    # 被遮内容，garbage=2（去重+清除未引用对象）即可保证脱敏对象不残留；
                    # garbage=4 的多轮深度压缩对安全性无增益，200 页文档多花约 2.4s。
                    # cp72: 若已配置加密密码，随 save 一并写入 AES-256 加密
                    save_kwargs = {"garbage": 2, "deflate": True, "clean": True}
                    encrypt_kwargs = build_encrypt_save_kwargs(
                        self.pdf_open_password, self.pdf_edit_password)
                    save_kwargs.update(encrypt_kwargs)
                    doc_save.save(fname, **save_kwargs)
                    encrypted = bool(encrypt_kwargs)

                    # 安全审计 v40.1: 导出成功后删除该文件的会话草稿（含未脱敏原文 pdfsnap）。
                    # 用户已完成脱敏导出，草稿（崩溃恢复用）不再需要，及时清理避免原文残留。
                    if self.file_path and hasattr(self, "_session_store"):
                        try:
                            self._session_store.delete_draft(self.file_path)
                        except Exception:
                            pass  # 草稿删除失败不影响导出成功

                    QApplication.restoreOverrideCursor()
                    enc_note = "\n\n✅ 已加密（打开/编辑密码已写入）" if encrypted else ""
                    if scan_incomplete:
                        body = (
                            f"文件已保存至：\n{fname}{enc_note}\n\n"
                            f"注意：仅 {scanned_pages}/{total_pages} 页经过智能扫描，"
                            f"未扫描页面未做智能脱敏，请自行确认其安全性。"
                        )
                        title = "已保存"
                    else:
                        body = f"文件已安全保存至：\n{fname}{enc_note}"
                        title = "成功"
                    # cp87: 弹窗附脱敏报告（“显示详细信息”原地展开）+ 导出报告按钮
                    report_text = build_redact_report(
                        os.path.basename(self.file_path or ""),
                        total_pages,
                        self.page_data,
                        fname,
                        encrypted=encrypted,
                        now_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    box = QMessageBox(self)
                    box.setIcon(QMessageBox.Icon.Information)
                    box.setWindowTitle(title)
                    box.setText(body + "\n\n点“显示详细信息”可查看脱敏报告。")
                    box.setDetailedText(report_text)
                    btn_export_report = box.addButton("导出报告", QMessageBox.ButtonRole.ActionRole)
                    btn_open_doc = box.addButton("打开文档", QMessageBox.ButtonRole.ActionRole)
                    box.addButton(QMessageBox.StandardButton.Ok)
                    box.exec()
                    clicked = box.clickedButton()
                    if clicked is btn_export_report:
                        report_path = os.path.splitext(fname)[0] + "_脱敏报告.txt"
                        try:
                            with open(report_path, "w", encoding="utf-8") as rf:
                                rf.write(report_text)
                            self._set_info_bar_message(f"📄 脱敏报告已导出：{os.path.basename(report_path)}")
                        except OSError as re_err:
                            QMessageBox.critical(self, "报告导出失败", str(re_err))
                    elif clicked is btn_open_doc:
                        ok, err = open_path_in_system(fname)
                        if not ok:
                            QMessageBox.warning(self, "打开失败", f"无法打开导出的文档：\n{err}")
                except (IOError, OSError, ValueError, RuntimeError, KeyError) as e:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.critical(self, "失败", str(e))
                finally:
                    if doc_save:
                        doc_save.close()
        # Word 保存
        elif self.word_doc:
            app.setStyleSheet(self._get_file_dialog_style())
            try:
                fname, _ = QFileDialog.getSaveFileName(self, "保存 Word", "", "Word 文档 (*.docx)")
            finally:
                app.setStyleSheet(original_style)

            if fname:
                # W8: 与 PDF 保存的 O1 对齐——扫描未运行或被取消时，
                # 文档可能仍有未扫描块，保存前二次确认，避免"误以为已完整脱敏"
                scan_meta = getattr(self, '_word_scan_meta', None)
                if scan_meta is None or scan_meta.get('was_cancelled'):
                    if scan_meta is None:
                        warn_msg = "当前文档尚未执行过智能扫描。\n\n未扫描的内容可能含有敏感信息，保存后不会对其做智能脱敏。\n\n是否仍要继续保存？"
                    else:
                        scanned = scan_meta.get('scanned_blocks', 0)
                        total = scan_meta.get('total_blocks', 0)
                        warn_msg = (
                            f"智能扫描曾被取消，仅完成 {scanned}/{total} 个块。\n\n"
                            f"未扫描的内容可能含有敏感信息，保存后不会对其做智能脱敏。\n\n"
                            f"是否仍要继续保存？"
                        )
                    reply = QMessageBox.question(
                        self, "扫描不完整", warn_msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                self._save_word(fname)

    def _save_word(self, fname):
        """保存 Word 文档 - v24 改进版：详细错误处理 + 使用 TempFileManager + 合并 OCR 和 Manual 脱敏"""
        try:
            import shutil
            from docx import Document

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            # 使用 TempFileManager 管理临时文件
            temp_file = self.temp_manager.create_temp_file()
            shutil.copy2(self.file_path, temp_file)

            # 打开副本进行修改
            new_doc = Document(temp_file)

            def _apply_saved_matches_to_para(key, para):
                data = self.word_data.get(key)
                if not data:
                    return
                merged = merge_word_matches_with_priority(
                    data.get("text", ""),
                    self.word_replace_rules,
                    self.replacement_text,
                    manual_matches=data.get("manual", []),
                    # cp63: 保存与预览同源：关键词行内替换优先于统一替换文本
                    ocr_matches=resolve_word_ocr_replacements(
                        data.get("ocr", []),
                        getattr(self, "custom_keyword_rules", None),
                        self.replacement_text
                    )
                )
                if merged:
                    replace_matches_in_paragraph(
                        para, merged, text_offset=0,
                        fallback_replacement_text=self.replacement_text
                    )

            def _apply_saved_matches_to_cell(key, cell):
                data = self.word_data.get(key)
                if not data:
                    return
                merged = merge_word_matches_with_priority(
                    data.get("text", ""),
                    self.word_replace_rules,
                    self.replacement_text,
                    manual_matches=data.get("manual", []),
                    # cp63: 保存与预览同源：关键词行内替换优先于统一替换文本
                    ocr_matches=resolve_word_ocr_replacements(
                        data.get("ocr", []),
                        getattr(self, "custom_keyword_rules", None),
                        self.replacement_text
                    )
                )
                replace_matches_in_cell(cell, merged, self.replacement_text)

            # 遍历段落进行 run 级别的文本替换
            for para_idx, para in enumerate(new_doc.paragraphs):
                _apply_saved_matches_to_para(f'paragraph_{para_idx}', para)

            # 遍历表格进行 run 级别的文本替换
            for table_idx, table in enumerate(new_doc.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        key = f'table_{table_idx}_cell_{row_idx}_{cell_idx}'
                        _apply_saved_matches_to_cell(key, cell)

            # W2: 页眉/页脚的段落与表格单元格（与打开时共用 key 方案）
            for key, para in iter_word_header_footer_paragraphs(new_doc):
                _apply_saved_matches_to_para(key, para)
            for key, cell in iter_word_header_footer_cells(new_doc):
                _apply_saved_matches_to_cell(key, cell)

            # 保存文档
            new_doc.save(fname)

            QApplication.restoreOverrideCursor()
            box_w = QMessageBox(self)
            box_w.setIcon(QMessageBox.Icon.Information)
            box_w.setWindowTitle("成功")
            box_w.setText(f"文件已保存至：\n{fname}")
            btn_open_doc_w = box_w.addButton("打开文档", QMessageBox.ButtonRole.ActionRole)
            box_w.addButton(QMessageBox.StandardButton.Ok)
            box_w.exec()
            if box_w.clickedButton() is btn_open_doc_w:
                ok, err = open_path_in_system(fname)
                if not ok:
                    QMessageBox.warning(self, "打开失败", f"无法打开导出的文档：\n{err}")

        except PermissionError:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self, "保存失败",
                f"没有写入权限：\n{fname}\n\n"
                "建议：\n"
                "1. 检查文件是否被其他程序打开\n"
                "2. 检查文件夹权限\n"
                "3. 尝试保存到其他位置"
            )

        except (OSError, IOError, RuntimeError, ValueError, KeyError, AttributeError, PackageNotFoundError) as e:
            # W7: 保存时模板 docx 损坏抛 PackageNotFoundError，纳入捕获避免直达全局 hook
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self, "保存失败",
                f"保存 Word 文档时出错：\n{str(e)}\n\n"
                "请尝试：\n"
                "1. 重启应用\n"
                "2. 在 Word 中手动打开文件\n"
                "3. 导出错误日志以供分析"
            )

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from privacyguard.diagnostics import run_self_test
        sys.exit(run_self_test(MainWindow))
    # v37.8.11 P0-3: 初始化统一日志框架（幂等，控制台+文件双通道）
    init_logging()

    # v37.0.5: 全局异常钩子，防止未捕获异常导致崩溃
    def exception_hook(exc_type, exc_value, exc_traceback):
        """全局异常处理器"""
        # 安全审计 v40.1: 完整 traceback（含源码行）只记 DEBUG；
        # ERROR 只记类型名（exc_value 可能含文件路径，不记到持久化日志）
        logger.error("[FATAL ERROR] 未捕获的异常: %s", exc_type.__name__)
        logger.debug("[FATAL ERROR] 详情:\n%s",
                     ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

        # 尝试显示错误对话框（弹窗只在本次会话显示，不持久化）
        try:
            if QApplication.instance():
                QMessageBox.critical(
                    None,
                    "程序错误",
                    f"程序遇到未预期的错误：\n\n{exc_type.__name__}\n\n"
                    "请将此错误反馈给开发者（详见日志）。"
                )
        except Exception:
            pass

        # 调用默认异常处理器
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = exception_hook

    # v37.0.5: 线程异常钩子
    def thread_exception_hook(args):
        """线程异常处理器"""
        # 安全审计 v40.1: traceback 降 debug，ERROR 只记类型名
        logger.error("[THREAD ERROR] 线程异常: %s", args.exc_type.__name__)
        logger.debug("[THREAD ERROR] 详情:\n%s",
                     ''.join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))

    threading.excepthook = thread_exception_hook

    # OCR 引擎的懒加载由 OCRWorker 在实际扫描时负责，启动时不再预热

    app = QApplication(sys.argv)

    # cp90: WebEngine 缓存延迟清除——上次退出时被占用未能删，此时 WebEngine
    # 尚未初始化（MainWindow 未构造），无占用，可安全删除
    # 安全修复: 传入 allowed_roots 白名单，防止标记文件被篡改后注入任意路径
    try:
        from privacyguard.trace_cleaner import WEBENGINE_PENDING_MARKER, clear_pending_webengine
        # 与 SessionStore 默认目录一致（避免提前实例化主窗）
        from privacyguard.session_store import _default_base_dir as _sess_default
        _sess_dir = _sess_default()
        _marker = os.path.join(_sess_dir, WEBENGINE_PENDING_MARKER)
        # 白名单根：sessions dir + temp + QtWebEngine 缓存基目录（不导入 QtWebEngine）
        import tempfile as _tf
        _webengine_roots = []
        _local_app = os.environ.get("LOCALAPPDATA", "")
        if _local_app:
            _webengine_roots.append(os.path.join(_local_app, "QtWebEngine"))
        _appdata = os.environ.get("APPDATA", "")
        if _appdata:
            _webengine_roots.append(os.path.join(_appdata, "QtWebEngine"))
        _cleared = clear_pending_webengine(_marker, allowed_roots=[
            _sess_dir, _tf.gettempdir(),
        ] + _webengine_roots)
        if _cleared:
            logger.info("[cp90] 已在启动时清除上次占用的预览缓存（%s 项）", _cleared)
    except Exception as _e:
        logger.warning("[cp90] 启动清除预览缓存跳过: %s: %s", type(_e).__name__, _e)

    # cp79: 全局默认字体——Qt 在 Windows 的默认字体是 "MS Shell Dlg 2"(9pt)，
    # 中文回退宋体系观感发虚，且与样式表里的雅黑混杂。统一为
    # Segoe UI（西文/数字）+ 微软雅黑 UI（中文）回退栈；所有未显式指定
    # font-family 的控件（行内样式/菜单/弹窗/tooltip）全部自动兜底继承。
    # cp80: 仅 Windows（Win10 无 Segoe UI Variable 自动回退 Segoe UI）；
    # macOS 保持 Qt 默认系统字体（SF/苹方 13pt），强设 Segoe/雅黑栈会
    # 落到 Arial 且 10pt 在 mac 偏小。
    if sys.platform == "win32":
        _ui_font = QFont()
        _ui_font.setFamilies(["Segoe UI Variable", "Segoe UI",
                              "Microsoft YaHei UI", "Microsoft YaHei", "Arial"])
        _ui_font.setPointSize(10)
        app.setFont(_ui_font)
    
    # 设置应用图标
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'logo', 'export', '256', 'logo_default_256.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        logger.info("应用图标已加载: %s", icon_path)
    else:
        logger.warning("应用图标未找到: %s", icon_path)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
