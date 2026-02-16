import sys
import os
import fitz  # PyMuPDF
import re
import cv2
import numpy as np
import time
import shutil
import atexit  # v36.2: 用于确保临时文件清理
import tempfile  # v36.2: 临时文件管理
from io import BytesIO
from rapidocr_onnxruntime import RapidOCR
from PIL import Image
from bs4 import BeautifulSoup

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QScrollArea, QMessageBox, QProgressBar, QFrame,
                             QDialog, QCheckBox, QGroupBox, QTextEdit, QSpinBox,
                             QRadioButton, QButtonGroup, QComboBox, QSizePolicy,
                             QTextBrowser, QLineEdit, QListWidget, QListWidgetItem,
                             QAbstractItemView)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QWheelEvent, QCursor, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF, QPointF, QSettings, QMutex, QMutexLocker, QObject, pyqtSlot, QSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

# 导入主题系统
from theme import Theme

# === 核心防崩溃设置 ===
cv2.setNumThreads(0)
os.environ["OMP_NUM_THREADS"] = "1"

# === 软件配置 ===
APP_NAME = "PrivacyGuard 脱敏卫士"
VERSION = "36.4 - Code Refactoring"

# === 常量定义 ===
MIN_RECT_WIDTH = 5           # 最小矩形宽度（像素）
PROGRESS_UPDATE_INTERVAL = 0.05  # 进度更新间隔（秒）
ZOOM_MIN = 0.5               # 最小缩放比例
ZOOM_MAX = 4.0               # 最大缩放比例
DEBUG_MODE = os.getenv('PRIVACYGUARD_DEBUG', 'False').lower() == 'true'  # 调试模式开关 (v33.1)

# === 默认规则库 ===
DEFAULT_RULES = {
    "身份证号": r"(?<!\d)([1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]|\d{15})(?!\d)",
    "手机号码": r"(?<!\d)(1[3-9]\d{9})(?!\d)",
    "日期时间": r"\d{4}[年\-\.]\d{1,2}[月\-\.]\d{1,2}[日]?",
    "电子邮箱": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "银行卡号": r"(?<!\d)([1-9]\d{12,18})(?!\d)"
}

# === 自定义异常类 ===
class PrivacyAppError(Exception):
    """基础异常类"""
    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion

    def user_message(self):
        msg = str(self)
        if self.suggestion:
            msg += f"\n\n建议：{self.suggestion}"
        return msg

class FileFormatError(PrivacyAppError):
    """文件格式错误"""
    pass

class ConversionError(PrivacyAppError):
    """文件转换失败"""
    pass

class MemoryLimitError(PrivacyAppError):
    """内存限制"""
    pass

class WorkerCancelledError(PrivacyAppError):
    """用户取消操作"""
    pass

# === 临时文件管理器 ===
class TempFileManager:
    """统一临时文件管理器，确保资源正确释放（v36.2: 安全加固版）

    安全特性:
    - 使用 atexit 注册退出清理钩子，确保程序退出时自动清理
    - 类级别注册表追踪所有实例
    - 使用具体异常类型处理删除错误 (OSError, IOError)
    - 防止临时文件泄露

    使用示例:
        manager = TempFileManager()
        temp_file = manager.create_temp_file(suffix='.pdf')
        temp_dir = manager.create_temp_dir()
        # 文件在程序退出时自动清理（无需手动调用 cleanup）
    """

    # 类级别注册表，跟踪所有实例
    _instances = []

    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []
        # 注册到类级别列表
        TempFileManager._instances.append(self)
        # 注册 atexit 清理（只注册一次）
        self._register_atexit()

    @classmethod
    def _register_atexit(cls):
        """注册 atexit 清理函数（只注册一次）"""
        if not hasattr(cls, '_atexit_registered'):
            atexit.register(cls._cleanup_all)
            cls._atexit_registered = True

    @classmethod
    def _cleanup_all(cls):
        """清理所有实例的临时文件"""
        for instance in list(cls._instances):
            try:
                instance.cleanup()
            except (OSError, IOError) as e:
                print(f"[TempFileManager] 清理实例失败: {e}")

    def create_temp_file(self, suffix='', content=None):
        """创建临时文件并追踪"""
        import tempfile
        temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        self.temp_files.append(temp.name)

        if content:
            temp.write(content)
            temp.close()

        return temp.name

    def create_temp_dir(self):
        """创建临时目录并追踪"""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        return temp_dir

    def cleanup(self):
        """清理所有临时文件和目录（v36.2: 使用具体异常类型）

        Returns:
            list: 清理过程中的错误列表
        """
        errors = []

        # 清理文件
        for f in self.temp_files[:]:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    self.temp_files.remove(f)
            except (OSError, IOError) as e:
                errors.append(f"清理文件失败 {f}: {e}")

        # 清理目录
        for d in self.temp_dirs[:]:
            try:
                if os.path.exists(d):
                    import shutil
                    shutil.rmtree(d)
                    self.temp_dirs.remove(d)
            except (OSError, IOError) as e:
                errors.append(f"清理目录失败 {d}: {e}")

        return errors

    def __del__(self):
        """析构时自动清理（作为后备）"""
        try:
            self.cleanup()
        except (OSError, IOError) as e:
            print(f"[TempFileManager] 析构清理失败: {e}")


def validate_safe_path(path, allowed_extensions=None):
    """验证文件路径安全（v36.2: 防止命令注入和路径遍历）

    安全特性:
    - 命令注入防护: 过滤危险字符 (; | & $ ` $( > < \n \r)
    - 路径遍历防护: 规范化路径并限制允许范围
    - 扩展名验证: 支持白名单机制

    Args:
        path: 要验证的路径
        allowed_extensions: 允许的扩展名列表，如 ['.pdf', '.doc']

    Returns:
        tuple: (is_safe: bool, error_msg: str or None)

    使用示例:
        is_safe, error_msg = validate_safe_path(file_path, allowed_extensions=['.doc'])
        if not is_safe:
            raise ConversionError("文件路径不安全", error_msg)
    """
    if not path:
        return False, "路径不能为空"

    # 检查路径长度
    if len(path) > 4096:
        return False, "路径过长"

    # 检查危险字符
    dangerous_chars = [';', '|', '&', '$', '`', '$(', '>', '<', '\n', '\r']
    for char in dangerous_chars:
        if char in path:
            return False, f"路径包含危险字符: {repr(char)}"

    # 规范化路径
    try:
        normalized = os.path.normpath(os.path.abspath(path))
    except (TypeError, ValueError, OSError) as e:
        return False, f"路径格式错误: {e}"

    # 检查路径遍历攻击
    # 获取系统临时目录和用户主目录作为允许范围
    temp_dir = os.path.normpath(os.path.abspath(os.path.expanduser("~")))
    if not normalized.startswith(temp_dir) and not any(
        normalized.startswith(os.path.normpath(os.path.abspath(p)))
        for p in [os.path.expanduser("~"), '/tmp', '/var/tmp', tempfile.gettempdir()]
    ):
        # 允许当前工作目录下的文件
        cwd = os.path.normpath(os.path.abspath('.'))
        if not normalized.startswith(cwd):
            return False, f"路径不在允许范围内: {normalized}"

    # 检查文件名部分
    basename = os.path.basename(normalized)
    if not basename or basename.startswith('.') or '..' in basename:
        return False, "无效的文件名"

    # 检查扩展名
    if allowed_extensions:
        ext = os.path.splitext(basename)[1].lower()
        if ext not in allowed_extensions:
            return False, f"不支持的文件类型: {ext}"

    return True, None

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# === 设置对话框 ===
class SettingsDialog(QDialog):
    def __init__(self, parent=None, current_rules=None, use_enhance=False, custom_keywords="", scan_level=2.0, offset_x=0, offset_w=0):
        super().__init__(parent)
        self.setWindowTitle("高级设置")
        self.resize(550, 700)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        self.selected_rules = []
        self.use_enhance = use_enhance
        self.custom_keywords = custom_keywords
        self.scan_level = scan_level
        self.offset_x = offset_x
        self.offset_w = offset_w
        
        layout = QVBoxLayout(self)

        # 1. 规则
        box_rules = QGroupBox("1. 通用规则")
        v_box = QVBoxLayout()
        self.checks = {}
        for name, pattern in DEFAULT_RULES.items():
            cb = QCheckBox(name)
            if current_rules and pattern in current_rules: cb.setChecked(True)
            elif not current_rules and name in ["身份证号", "手机号码"]: cb.setChecked(True)
            self.checks[name] = cb
            v_box.addWidget(cb)
        box_rules.setLayout(v_box)
        layout.addWidget(box_rules)

        # 2. 关键词
        box_custom = QGroupBox("2. 自定义关键词")
        v_custom = QVBoxLayout()
        self.txt_custom = QTextEdit()
        self.txt_custom.setPlaceholderText("例如：法院 张三 (支持多行)")
        self.txt_custom.setPlainText(custom_keywords)
        v_custom.addWidget(self.txt_custom)
        box_custom.setLayout(v_custom)
        layout.addWidget(box_custom)

        # 3. 精度与微调
        box_enhance = QGroupBox("3. 精度与微调")
        v_enhance = QVBoxLayout()
        
        h_precision = QHBoxLayout()
        h_precision.addWidget(QLabel("扫描模式:"))
        self.combo_precision = QComboBox()
        self.combo_precision.addItem("标准 (1.5x)", 1.5)
        self.combo_precision.addItem("高精 (2.0x 推荐)", 2.0)
        self.combo_precision.addItem("超精 (3.0x 最慢)", 3.0)
        idx = self.combo_precision.findData(scan_level)
        self.combo_precision.setCurrentIndex(idx if idx >=0 else 1)
        h_precision.addWidget(self.combo_precision)
        v_enhance.addLayout(h_precision)

        h_calibrate = QHBoxLayout()
        v_cal_1 = QVBoxLayout()
        v_cal_1.addWidget(QLabel("向左修正(px):"))
        self.spin_offset_x = QSpinBox()
        self.spin_offset_x.setRange(-20, 20)
        self.spin_offset_x.setValue(offset_x)
        v_cal_1.addWidget(self.spin_offset_x)
        
        v_cal_2 = QVBoxLayout()
        v_cal_2.addWidget(QLabel("宽度收缩(px):"))
        self.spin_offset_w = QSpinBox()
        self.spin_offset_w.setRange(-20, 20)
        self.spin_offset_w.setValue(offset_w)
        v_cal_2.addWidget(self.spin_offset_w)
        
        h_calibrate.addLayout(v_cal_1)
        h_calibrate.addLayout(v_cal_2)
        v_enhance.addLayout(h_calibrate)
        v_enhance.addWidget(QLabel("提示：仅对纯图片PDF生效"))
        
        self.cb_enhance = QCheckBox("开启图像增强 (仅针对手写体)")
        self.cb_enhance.setChecked(use_enhance)
        v_enhance.addWidget(self.cb_enhance)
        
        box_enhance.setLayout(v_enhance)
        layout.addWidget(box_enhance)

        btn_ok = QPushButton("保存设置")
        btn_ok.clicked.connect(self.save_settings)
        layout.addWidget(btn_ok)

    def save_settings(self):
        self.selected_rules = [DEFAULT_RULES[name] for name, cb in self.checks.items() if cb.isChecked()]
        self.use_enhance = self.cb_enhance.isChecked()
        self.custom_keywords = self.txt_custom.toPlainText().strip()
        self.scan_level = self.combo_precision.currentData()
        self.offset_x = self.spin_offset_x.value()
        self.offset_w = self.spin_offset_w.value()
        self.accept()

# === 图片排序对话框 ===
class ImageListDialog(QDialog):
    """图片排序对话框 - 支持拖拽调整图片顺序"""
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("调整图片顺序")
        self.resize(600, 500)
        self.image_paths = image_paths

        layout = QVBoxLayout(self)

        # 说明标签
        info_label = QLabel("拖拽缩略图调整图片顺序，完成后点击「确认合并」")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 缩略图列表（支持拖拽）
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(120, 120))
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        # 添加缩略图
        for path in image_paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            # 生成缩略图
            try:
                pixmap = QPixmap(path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio)
                item.setIcon(QIcon(pixmap))
            except Exception:
                # 如果缩略图生成失败，使用默认图标
                pass
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确认合并")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_ordered_paths(self):
        """获取排序后的图片路径"""
        paths = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            paths.append(item.data(Qt.ItemDataRole.UserRole))
        return paths

# === 配置常量 ===
FEEDBACK_URL = "https://fcnwakmkeuz7.feishu.cn/share/base/form/shrcnEM1JEbdIKzdB400egj9lHe"  # 飞书反馈表单

# === 反馈对话框 ===
class FeedbackDialog(QDialog):
    """开发者信息与反馈对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于与反馈")
        self.resize(480, 600)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # 获取当前主题
        self.theme = Theme.LIGHT if not parent or not hasattr(parent, 'is_dark') or not parent.is_dark else Theme.DARK

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # === 标题区域 ===
        title_layout = QHBoxLayout()
        logo_label = QLabel()
        logo_label.setFixedSize(64, 64)
        logo_label.setStyleSheet(f"""
            background: {self.theme['primary']};
            border-radius: 12px;
            color: white;
            font-size: 24px;
            font-weight: bold;
        """)
        logo_label.setText("PG")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(logo_label)

        title_info = QVBoxLayout()
        title_info.setSpacing(4)
        app_name = QLabel(APP_NAME)
        app_name.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {self.theme['text']};")
        version_label = QLabel(f"版本 {VERSION}")
        version_label.setStyleSheet(f"font-size: 12px; color: {self.theme['text_secondary']};")
        title_info.addWidget(app_name)
        title_info.addWidget(version_label)
        title_layout.addLayout(title_info)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # === 分隔线 ===
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet(f"background: {self.theme['border']}; max-height: 1px;")
        layout.addWidget(line1)

        # === 社交媒体账号 ===
        social_group = QGroupBox("关注开发者")
        social_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                color: {self.theme['text']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """)
        social_layout = QVBoxLayout(social_group)

        # 统一账号行
        account_name = "池州汪律的Ai 进化论"
        row = QHBoxLayout()
        platforms_label = QLabel("微信公众号/抖音/小红书/B站（同号）:")
        platforms_label.setStyleSheet(f"color: {self.theme['text_secondary']};")
        row.addWidget(platforms_label)

        account_label = QLabel(account_name)
        account_label.setStyleSheet(f"color: {self.theme['text']}; font-weight: 500;")
        account_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(account_label)
        row.addStretch()

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(50, 24)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['hover']};
                border: none;
                border-radius: 4px;
                font-size: 11px;
                color: {self.theme['text']};
            }}
            QPushButton:hover {{
                background: {self.theme['pressed']};
            }}
        """)
        copy_btn.clicked.connect(lambda checked, a=account_name: self._copy_to_clipboard(a))
        row.addWidget(copy_btn)
        social_layout.addLayout(row)

        layout.addWidget(social_group)

        # === 开发者简介 ===
        dev_group = QGroupBox("开发者简介")
        dev_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                color: {self.theme['text']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """)
        dev_layout = QVBoxLayout(dev_group)
        dev_intro = QLabel(
            "<b>汪立</b><br><br>"
            "安徽始信律师事务所执业律师<br>"
            "全栈律师 | 前教师 | 退伍军人<br><br>"
            "📧 邮箱: <a href='mailto:491445490@qq.com'>491445490@qq.com</a>"
        )
        dev_intro.setWordWrap(True)
        dev_intro.setTextFormat(Qt.TextFormat.RichText)
        dev_intro.setOpenExternalLinks(True)
        dev_intro.setStyleSheet(f"""
            color: {self.theme['text']};
            line-height: 1.6;
            font-size: 13px;
        """)
        dev_layout.addWidget(dev_intro)
        layout.addWidget(dev_group)

        # === 操作按钮 ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        feedback_btn = QPushButton("📝 反馈建议")
        feedback_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {Theme.adjust_color(self.theme['primary'], -20)};
            }}
        """)
        feedback_btn.clicked.connect(self._open_feedback)
        btn_layout.addWidget(feedback_btn)

        # 新增：使用手册按钮
        manual_btn = QPushButton("📖 使用手册")
        manual_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['info'] if 'info' in self.theme else '#17a2b8'};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {Theme.adjust_color(self.theme['info'] if 'info' in self.theme else '#17a2b8', -20)};
            }}
        """)
        manual_btn.clicked.connect(self._open_manual)
        btn_layout.addWidget(manual_btn)

        donate_btn = QPushButton("☕ 打赏支持")
        donate_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['success']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {Theme.adjust_color(self.theme['success'], -20)};
            }}
        """)
        donate_btn.clicked.connect(self._show_donate)
        btn_layout.addWidget(donate_btn)

        layout.addLayout(btn_layout)

        # === 分隔线 ===
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(f"background: {self.theme['border']}; max-height: 1px;")
        layout.addWidget(line2)

        # === 免责声明 ===
        disclaimer = QTextBrowser()
        disclaimer.setOpenExternalLinks(True)
        disclaimer.setMaximumHeight(160)
        disclaimer.setStyleSheet(f"""
            QTextBrowser {{
                background: {self.theme['surface']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                padding: 12px;
                color: {self.theme['text_secondary']};
                font-size: 11px;
            }}
        """)
        disclaimer.setHtml("""
            <p style="font-weight: bold; margin-bottom: 8px; color: #FF9500;">⚠️ 免责声明</p>
            <ol style="margin-left: 16px; line-height: 1.6;">
                <li>本软件免费仅供学习和个人使用，不构成任何法律建议。</li>
                <li>使用本软件进行文档脱敏处理后，用户需自行核实脱敏结果。</li>
                <li>开发者不对因使用本软件而产生的任何直接或间接损失承担责任。</li>
                <li>本软件不收集任何用户数据，所有处理均在本地完成。</li>
                <li>请勿将本软件用于任何违法用途，最终解释、修改权归汪立律师所有。</li>
            </ol>
        """)
        layout.addWidget(disclaimer)

        # === 关闭按钮 ===
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['hover']};
                color: {self.theme['text']};
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {self.theme['pressed']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # 显示复制成功提示
        if self.parent():
            QMessageBox.information(self.parent(), "复制成功", f"已复制: {text}")

    def _open_feedback(self):
        """打开反馈问卷链接"""
        import webbrowser
        webbrowser.open(FEEDBACK_URL)

    def _open_manual(self):
        """打开使用手册链接"""
        import webbrowser
        webbrowser.open("https://fcnwakmkeuz7.feishu.cn/docx/M9ojdaGUAoRVv7x3NCAcxkxenUe?from=from_copylink")

    def _show_donate(self):
        """显示打赏二维码对话框"""
        dialog = DonateDialog(self)
        dialog.exec()


# === 打赏对话框 ===
class DonateDialog(QDialog):
    """打赏二维码对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("打赏支持")
        self.resize(360, 440)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # 获取当前主题
        self.theme = Theme.LIGHT if not parent or not hasattr(parent, 'is_dark') or not parent.is_dark else Theme.DARK

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 感谢文字
        thanks_label = QLabel("感谢您的支持！")
        thanks_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.theme['text']};
        """)
        thanks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thanks_label)

        subtitle = QLabel("您的支持是我持续更新的动力 ❤️")
        subtitle.setStyleSheet(f"font-size: 13px; color: {self.theme['text_secondary']};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # 二维码图片
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_label.setFixedSize(260, 260)

        # 尝试加载二维码图片
        qr_path = resource_path(os.path.join("assets", "donate_qrcode.png"))
        if os.path.exists(qr_path):
            pixmap = QPixmap(qr_path)
            if not pixmap.isNull():
                qr_label.setPixmap(pixmap.scaled(240, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                qr_label.setText("二维码加载失败")
                qr_label.setStyleSheet(f"color: {self.theme['danger']}; font-size: 14px;")
        else:
            qr_label.setText("请添加二维码图片至\nassets/donate_qrcode.png")
            qr_label.setStyleSheet(f"""
                color: {self.theme['text_secondary']};
                font-size: 12px;
                background: {self.theme['hover']};
                border: 2px dashed {self.theme['border']};
                border-radius: 8px;
            """)

        layout.addWidget(qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 提示文字
        tip_label = QLabel("微信扫码打赏")
        tip_label.setStyleSheet(f"font-size: 13px; color: {self.theme['text_secondary']};")
        tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip_label)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {Theme.adjust_color(self.theme['primary'], -20)};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

# === 图片合并Worker线程 ===
class ImageMergeWorker(QThread):
    """图片合并为PDF的后台线程"""
    finished_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, image_paths, output_path):
        super().__init__()
        self.image_paths = image_paths
        self.output_path = output_path

    def run(self):
        """执行图片合并"""
        try:
            doc = fitz.open()  # 创建新PDF

            total = len(self.image_paths)
            for i, img_path in enumerate(self.image_paths):
                try:
                    # 1. 用Pillow打开图片（使用 with 确保资源释放）
                    with Image.open(img_path) as img:
                        # 2. 转换为RGB（如果需要）
                        if img.mode != 'RGB':
                            img = img.convert('RGB')

                        # 3. 创建PDF页面（保持原始尺寸）
                        page_rect = fitz.Rect(0, 0, img.width, img.height)
                        page = doc.new_page(width=img.width, height=img.height)

                        # 4. 将图片插入到页面（作为独立对象）
                        page.insert_image(page_rect, filename=img_path, overlay=True)

                    # 5. 进度更新
                    progress = int((i + 1) / total * 100)
                    self.progress_signal.emit(progress)

                except (IOError, OSError, ValueError) as e:
                    self.error_signal.emit(f"处理图片 {os.path.basename(img_path)} 失败: {str(e)}")
                    doc.close()
                    return

            # 6. 保存PDF
            doc.save(self.output_path)
            doc.close()
            self.finished_signal.emit(self.output_path)

        except (IOError, OSError, ValueError, RuntimeError) as e:
            self.error_signal.emit(f"合并失败: {str(e)}")

# === 单页画布 (完全复制 v7.0 的 PDFCanvas 实现) ===
class SinglePageCanvas(QLabel):
    # 保留信号以兼容双页模式
    rect_added = pyqtSignal(int, QRectF)
    rect_removed = pyqtSignal(int, int, bool)
    zoom_request = pyqtSignal(float)
    page_change_request = pyqtSignal(int)  # 翻页请求信号：正值=下一页，负值=上一页

    def __init__(self, page_index=0, parent=None):
        super().__init__(parent)
        # 完全复制 v7.0 的初始化
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setAutoFillBackground(True)

        self.page_index = page_index  # 新增：用于双页模式
        self.zoom_scale = 1.0
        self.rects_ocr = []
        self.rects_manual = []
        self.mask_color = QColor(0, 0, 0)

        self.drawing = False
        self.start_point = QPointF()
        self.current_rect = QRectF()

    def set_mask_color(self, color):
        """v7.0 方法"""
        self.mask_color = color
        self.update()

    def update_content(self, pixmap, scale, ocr_rects, manual_rects):
        """v7.0 方法 - 直接引用列表，不复制！"""
        self.setPixmap(pixmap)
        self.zoom_scale = scale
        self.rects_ocr = ocr_rects  # ← v7.0 直接引用，不复制
        self.rects_manual = manual_rects  # ← v7.0 直接引用，不复制
        self.update()

    # === v22.7: 完全回归 v7.0 - mousePressEvent 处理左右键 ===
    def mousePressEvent(self, event):
        """v7.0 风格：左键画框，右键删除"""
        if not self.pixmap():
            return

        # 左键画框
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_point = event.position()
            self.current_rect = QRectF(self.start_point, self.start_point)
            self.update()

        # 右键删除 (v7.0 风格)
        elif event.button() == Qt.MouseButton.RightButton:
            click_pos = event.position()
            if DEBUG_MODE:
                print(f"\n[DEBUG] === 右键点击 === 页面{self.page_index}, 位置({click_pos.x():.2f}, {click_pos.y():.2f})")
                print(f"[DEBUG] 手动框数量: {len(self.rects_manual)}, OCR框数量: {len(self.rects_ocr)}")

            deleted = False

            # 先删手动框（从后往前，优先删除上层）
            for i in range(len(self.rects_manual) - 1, -1, -1):
                screen_rect = self.pdf_to_screen(self.rects_manual[i])
                if DEBUG_MODE:
                    print(f"[DEBUG] 检查手动框[{i}]: {screen_rect}, contains={screen_rect.contains(click_pos)}")
                if screen_rect.contains(click_pos):
                    del self.rects_manual[i]
                    deleted = True
                    if DEBUG_MODE:
                        print(f"[DEBUG] ✓ 删除手动框[{i}]")
                    break

            # 再删 OCR 框
            if not deleted:
                for i in range(len(self.rects_ocr) - 1, -1, -1):
                    screen_rect = self.pdf_to_screen(self.rects_ocr[i])
                    if DEBUG_MODE:
                        print(f"[DEBUG] 检查OCR框[{i}]: {screen_rect}, contains={screen_rect.contains(click_pos)}")
                    if screen_rect.contains(click_pos):
                        del self.rects_ocr[i]
                        deleted = True
                        if DEBUG_MODE:
                            print(f"[DEBUG] ✓ 删除OCR框[{i}]")
                        break

            if deleted:
                self.update()
            else:
                if DEBUG_MODE:
                    print(f"[DEBUG] ✗ 未点击到任何矩形框")
            # 不需要 emit 信号！列表是共享引用，删除已经同步到主窗口

    def pdf_to_screen(self, rect):
        """v7.0 实现 - 带小的容错范围"""
        base_rect = QRectF(rect.x()*self.zoom_scale, rect.y()*self.zoom_scale,
                           rect.width()*self.zoom_scale, rect.height()*self.zoom_scale)
        # 扩展 2 像素容错范围，处理点击边界的情况
        return base_rect.adjusted(-2, -2, 2, 2)

    def paintEvent(self, event):
        """v7.0 实现"""
        super().paintEvent(event)
        if not self.pixmap(): return

        painter = QPainter(self)

        # 使用当前选中的颜色 (黑或白)
        painter.setBrush(self.mask_color)
        painter.setPen(Qt.PenStyle.NoPen)

        # 1. 绘制 AI 框
        for r in self.rects_ocr:
            sr = self.pdf_to_screen(r)
            painter.drawRect(sr)

        # 2. 绘制 手动框
        for r in self.rects_manual:
            sr = self.pdf_to_screen(r)
            painter.drawRect(sr)

        # 3. 绘制 拖拽框 (始终红色边框，提示用)
        if self.drawing and not self.current_rect.isEmpty():
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.current_rect)

    def mouseMoveEvent(self, event):
        """v7.0 实现"""
        if self.drawing and not self.start_point.isNull():
            current_pos = QPointF(event.position())
            self.current_rect = QRectF(self.start_point, current_pos).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        """v7.0 实现"""
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            if self.current_rect.width() > 5 and self.current_rect.height() > 5:
                real_rect = QRectF(
                    self.current_rect.x()/self.zoom_scale,
                    self.current_rect.y()/self.zoom_scale,
                    self.current_rect.width()/self.zoom_scale,
                    self.current_rect.height()/self.zoom_scale
                )
                # v7.0 直接添加到列表（列表是共享引用）
                self.rects_manual.append(real_rect)
            self.current_rect = QRectF()
            self.update()

    # v35.1: 增强滚轮事件 - 支持缩放和翻页
    def wheelEvent(self, event: QWheelEvent):
        modifiers = QApplication.keyboardModifiers()
        delta = event.angleDelta().y()

        # Ctrl/Cmd + 滚轮：缩放（保持原有功能）
        if modifiers == Qt.KeyboardModifier.ControlModifier or modifiers == Qt.KeyboardModifier.MetaModifier:
            event.accept()
            if delta > 0:
                self.zoom_request.emit(0.1)
            else:
                self.zoom_request.emit(-0.1)
        # Shift + 滚轮：快速翻页（一次2页）
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            event.accept()
            if delta < 0:  # 向下滚动 = 下一页
                self.page_change_request.emit(2)
            else:  # 向上滚动 = 上一页
                self.page_change_request.emit(-2)
        # 普通滚轮：触发翻页信号（由 MainWindow 判断滚动条位置）
        else:
            # 发送翻页请求信号，由 MainWindow 处理边缘检测
            if delta < 0:
                self.page_change_request.emit(1)
            else:
                self.page_change_request.emit(-1)
            # 同时传递给父类以支持正常滚动
            super().wheelEvent(event)

# === OCR 线程 (保持 v13 的防崩核心) ===
# 绝对不能用 v7 的 OCRWorker，否则打开文字版 PDF 会崩
class OCRWorker(QThread):
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int)
    page_result_signal = pyqtSignal(int, list)  # v36.4: 线程安全 - 逐页发送结果 (页码, 矩形列表)

    def __init__(self, pdf_path, rules, use_enhance, custom_keywords, scan_scale, off_x, off_w):
        super().__init__()
        # 不再加载整个文件到内存，只保存路径（v24 内存优化）
        self.pdf_path = pdf_path
        self.rules = rules
        self.use_enhance = use_enhance
        raw_keywords = custom_keywords.replace('\n', ' ').split()
        self.custom_keywords = [re.escape(k.strip()) for k in raw_keywords if k.strip()]
        self.scan_scale = scan_scale
        self.off_x = off_x
        self.off_w = off_w
        
    def preprocess_image(self, img_np):
        try:
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = np.ones((2, 2), np.uint8)
            enhanced = cv2.erode(binary, kernel, iterations=1)
            return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        except cv2.error as e:
            print(f"图像处理错误: {e}")
            return img_np

    def calculate_sub_rect(self, box, text, match_span):
        try:
            line_x_min = min([p[0] for p in box])
            line_x_max = max([p[0] for p in box])
            line_y_min = min([p[1] for p in box])
            line_y_max = max([p[1] for p in box])
            
            if len(text) == 0 or line_x_max <= line_x_min:
                return None
            avg_char_width = (line_x_max - line_x_min) / len(text)
            start_idx, end_idx = match_span
            
            sub_x = line_x_min + (start_idx * avg_char_width)
            sub_w = (end_idx - start_idx) * avg_char_width
            
            final_x = sub_x - self.off_x * self.scan_scale
            final_w = sub_w - self.off_w * self.scan_scale
            
            return QRectF(final_x, line_y_min, final_w, (line_y_max - line_y_min))
        except (ValueError, ZeroDivisionError, TypeError):
            return None

    def run(self):
        # v36.4: 使用信号槽机制替代共享字典，解决线程安全问题
        # 直接打开文件，不加载到内存（v24 内存优化）
        # 支持取消并保存部分结果（v36.3）
        doc = None
        try:
            doc = fitz.open(self.pdf_path)
            ocr_engine = None
            total = len(doc)
            SCAN_SCALE = self.scan_scale
            last_emit_time = 0

            # 分批处理：每 10 页一批，批次间释放资源（v24 批处理优化）
            batch_size = 10

            for batch_start in range(0, total, batch_size):
                if self.isInterruptionRequested():
                    break  # 退出循环，但保留已扫描结果

                batch_end = min(batch_start + batch_size, total)

                for i in range(batch_start, batch_end):
                    if self.isInterruptionRequested():
                        break  # 退出循环，但保留已扫描结果

                    page = doc[i]
                    rects = []

                    page_text = page.get_text()
                    is_text_pdf = len(page_text.strip()) > 20

                    if is_text_pdf:
                        all_patterns = self.rules + self.custom_keywords
                        for pat in all_patterns:
                            for match in re.finditer(pat, page_text, re.IGNORECASE):
                                found_str = match.group()
                                try:
                                    hits = page.search_for(found_str)
                                    if hits:
                                        for h in hits:
                                            safe_rect = QRectF(h.x0, h.y0, h.width, h.height)
                                            rects.append(safe_rect)
                                except RuntimeError as e:
                                    print(f"搜索文本错误: {e}")
                                    pass
                    else:
                        if ocr_engine is None:
                            ocr_engine = RapidOCR()

                        pix = page.get_pixmap(matrix=fitz.Matrix(SCAN_SCALE, SCAN_SCALE))
                        img_data = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
                        img_np = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

                        scan_img = self.preprocess_image(img_np) if self.use_enhance else img_np
                        ocr_result, _ = ocr_engine(scan_img)

                        if ocr_result:
                            for line in ocr_result:
                                box, text = line[0], line[1]
                                all_patterns = self.rules + self.custom_keywords
                                for pat in all_patterns:
                                    for match in re.finditer(pat, text, re.IGNORECASE):
                                        sub_rect = self.calculate_sub_rect(box, text, match.span())
                                        if sub_rect:
                                            rects.append(QRectF(
                                                sub_rect.x()/SCAN_SCALE,
                                                sub_rect.y()/SCAN_SCALE,
                                                sub_rect.width()/SCAN_SCALE,
                                                sub_rect.height()/SCAN_SCALE
                                            ))

                    # v36.4: 通过信号发送单页结果（线程安全）
                    self.page_result_signal.emit(i, rects)

                    # 背压控制 (防止 UI 线程崩溃)
                    current_progress = int((i+1)/total * 100)
                    current_time = time.time()
                    if current_time - last_emit_time > PROGRESS_UPDATE_INTERVAL or i == total - 1:
                        self.progress_signal.emit(current_progress)
                        last_emit_time = current_time

                # 批次间检查中断
                if self.isInterruptionRequested():
                    break  # 退出循环，但保留已扫描结果

                # 批次间清理：释放 OCR 引擎资源（v24 内存优化）
                if ocr_engine and batch_end < total:
                    del ocr_engine
                    ocr_engine = None
                    import gc
                    gc.collect()

            # v36.4: 发射空字典作为完成信号，实际结果已通过 page_result_signal 发送
            self.finished_signal.emit({})

        except (IOError, OSError, RuntimeError, ValueError) as e:
            print(f"OCR处理错误: {e}")
            self.finished_signal.emit({})
        finally:
            if doc:
                doc.close()

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
            print(f"警告: 键 '{key}' 不在 word_data 中")
            QMessageBox.warning(self.main_window, "添加失败", f"无法定位文本区域 (键: {key})")

    @pyqtSlot(str, str)
    def add_manual_redaction_global(self, key, selected_text):
        """添加全局手动脱敏（整篇相同文本）

        Args:
            key: 当前选中的 key（用于定位上下文）
            selected_text: 选中的文本
        """
        # 遍历所有 word_data，为每个包含该文本的位置添加脱敏
        for k, data in self.main_window.word_data.items():
            text = data['text']
            if not text:
                continue

            # 查找所有匹配位置
            import re
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
            target_item = None
            for i, item in enumerate(manual_list):
                if item['start'] == start and item['end'] == end:
                    target_item = item
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
            print(f"[撤销] 删除了 {count} 个全局脱敏: {text}")
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

# === Word 文档处理线程 ===
class WordWorker(QThread):
    """Word 文档智能脱敏线程"""
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int)

    def __init__(self, word_doc, word_data, rules, custom_keywords, replacement_text):
        super().__init__()
        self.word_doc = word_doc
        self.word_data = word_data
        self.rules = rules
        raw_keywords = custom_keywords.replace('\n', ' ').split()
        self.custom_keywords = [re.escape(k.strip()) for k in raw_keywords if k.strip()]
        self.replacement_text = replacement_text

    def run(self):
        """主处理流程 - 支持取消并保存进度（v36.3）"""
        try:
            # 统计总数（段落 + 表格单元格）
            total_paragraphs = len(self.word_doc.paragraphs)
            total_tables = len(self.word_doc.tables)
            total_cells = sum(len(table.rows) * len(table.columns) for table in self.word_doc.tables)
            total = total_paragraphs + total_cells
            processed = 0
            last_emit_time = 0

            # 处理段落
            for idx, para in enumerate(self.word_doc.paragraphs):
                if self.isInterruptionRequested():
                    break  # 保留已处理结果

                key = f'paragraph_{idx}'
                if key in self.word_data:
                    text = self.word_data[key]['text']
                    matches = self._find_matches(text)
                    self.word_data[key]['ocr'] = matches

                processed += 1
                self._emit_progress(processed, total, last_emit_time)
                last_emit_time = time.time()

            # 处理表格（仅在未取消时继续）
            if not self.isInterruptionRequested():
                for table_idx, table in enumerate(self.word_doc.tables):
                    if self.isInterruptionRequested():
                        break  # 保留已处理结果

                    for row_idx, row in enumerate(table.rows):
                        for cell_idx, cell in enumerate(row.cells):
                            key = f'table_{table_idx}_cell_{row_idx}_{cell_idx}'
                            if key in self.word_data:
                                text = self.word_data[key]['text']
                                matches = self._find_matches(text)
                                self.word_data[key]['ocr'] = matches

                            processed += 1
                            self._emit_progress(processed, total, last_emit_time)
                            last_emit_time = time.time()

            # 发射已扫描的结果（无论完成与否）
            self.finished_signal.emit(self.word_data)

        except Exception as e:
            print(f"Word扫描错误: {e}")
            # 出错时也返回已处理结果
            self.finished_signal.emit(self.word_data)

    def _emit_progress(self, processed, total, last_emit_time):
        """背压控制的进度更新"""
        current_progress = int(processed / total * 100)
        current_time = time.time()
        if current_time - last_emit_time > PROGRESS_UPDATE_INTERVAL or processed == total:
            self.progress_signal.emit(current_progress)

    def _find_matches(self, text):
        """查找匹配的敏感信息"""
        matches = []
        all_patterns = self.rules + self.custom_keywords

        for pattern in all_patterns:
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matches.append({
                        'pattern': pattern,
                        'rule_name': self._get_rule_name(pattern),
                        'start': match.start(),
                        'end': match.end(),
                        'text': match.group(),
                        'replacement': self.replacement_text
                    })
            except re.error:
                # 忽略无效的正则表达式
                pass

        return matches

    def _get_rule_name(self, pattern):
        """根据模式获取规则名称"""
        for name, pat in DEFAULT_RULES.items():
            if pat == pattern:
                return name
        return "自定义"

# === Word 预览交互式 JavaScript 代码常量 ===
# v36.4: 提取为常量，避免 _inject_interactive_html 函数过长
_INTERACTIVE_JS_CODE = r"""
<script>
    let pyBridge = null;
    let webChannelReady = false;

    document.addEventListener('DOMContentLoaded', function() {
        // 初始化 QWebChannel
        if (typeof qt !== 'undefined' && qt.webChannelTransport) {
            try {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    pyBridge = channel.objects.pyBridge;
                    if (pyBridge) {
                        webChannelReady = true;
                    }
                });
            } catch (e) {
                console.error('QWebChannel error:', e);
            }
        }
        setupContextMenu();
    });

    // v35.1: 备用右键位置（用于复杂 DOM 结构中 getSelection() 返回空值的情况）
    let lastContextMenuEvent = null;

    function setupContextMenu() {
        // v35.1: 使用捕获阶段监听（更可靠，在事件冒泡前捕获）
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            lastContextMenuEvent = {
                clientX: e.clientX,
                clientY: e.clientY,
                target: e.target
            };
            handleContextMenu(e);
        }, true);  // true = 捕获阶段

        // v35.1: mousedown 事件预先保存右键位置（备用方案）
        document.addEventListener('mousedown', function(e) {
            if (e.button === 2) {  // 右键
                lastContextMenuEvent = {
                    clientX: e.clientX,
                    clientY: e.clientY,
                    target: e.target
                };
            }
        }, true);

        document.addEventListener('click', function(e) {
            if (!e.target.closest('#redaction-menu')) {
                hideContextMenu();
            }
        });
    }

    // v35.1: 增强的右键菜单处理函数
    function handleContextMenu(e) {
        const target = e.target;
        let selection = window.getSelection();
        let selectedText = selection.toString().trim();

        // 查找点击的目标是否是手动脱敏标记或其内部元素
        let highlightElement = target.closest('.manual-highlight');

        // 点击手动脱敏标记
        if (highlightElement) {
            console.log('[ContextMenu] 点击了手动脱敏标记');
            showRemoveMenu(e.clientX, e.clientY, highlightElement);
            return;
        }

        // 选择了文本（主要路径）
        if (selectedText.length > 0) {
            console.log('[ContextMenu] 选择了文本:', selectedText.substring(0, 20));
            try {
                const range = selection.getRangeAt(0);
                showAddMenu(e.clientX, e.clientY, selection, selectedText);
            } catch (err) {
                console.warn('[ContextMenu] getRangeAt 失败，尝试备用方案:', err);
                // 备用方案：使用预先保存的位置
                if (lastContextMenuEvent) {
                    tryFallbackTextDetection(e, target);
                }
            }
            return;
        }

        // v35.1: 备用方案 - 尝试从点击位置获取文本
        console.log('[ContextMenu] getSelection() 为空，尝试备用检测');
        tryFallbackTextDetection(e, target);
    }

    // v35.1: 备用文本检测（当 window.getSelection() 失败时）
    function tryFallbackTextDetection(e, target) {
        // 方案1: 检查目标元素是否包含文本
        let textElement = target;

        // 向上查找包含 data-key 的文本块
        for (let i = 0; i < 10 && textElement; i++) {
            if (textElement.dataset && textElement.dataset.key) {
                console.log('[tryFallbackTextDetection] 找到 data-key 元素:', textElement.dataset.key);
                // 显示一个提示菜单（v36.1 安全修复：使用配置对象）
                const menu = createMenu([
                    { text: '请在文本上拖动选择后再右键', disabled: true }
                ]);
                positionMenu(menu, e.clientX, e.clientY);
                setTimeout(hideContextMenu, 2000);
                return;
            }
            textElement = textElement.parentNode;
        }

        // 未找到 data-key，显示提示
        console.warn('[tryFallbackTextDetection] 未找到有效的文本块');
    }

    function showRemoveMenu(x, y, element) {
        const key = element.dataset.key;
        const start = parseInt(element.dataset.start);
        const end = parseInt(element.dataset.end);

        console.log('[showRemoveMenu] key:', key, 'start:', start, 'end:', end);

        // v36.1 安全修复：使用配置对象替代 HTML 字符串
        const menu = createMenu([
            { text: '❌ 撤销脱敏', action: 'remove', key: key, start: start, end: end }
        ]);
        positionMenu(menu, x, y);
        attachMenuHandlers();
    }

    function showAddMenu(x, y, selection, selectedText) {
        const range = selection.getRangeAt(0);
        const textInfo = findTextPosition(selectedText, range);

        // 即使 textInfo 为 null 也不直接返回，使用全局模式
        let buttonConfigs = [];

        if (!textInfo || textInfo.mode === 'global' || textInfo.key === '__GLOBAL__') {
            // 降级到全局模式：只显示全文脱敏选项
            console.log('[showAddMenu] 使用全局降级模式');
            // v36.1 安全修复：使用配置对象替代 HTML 字符串
            buttonConfigs = [
                { text: '📄 全文脱敏此内容', action: 'add-global-only', textData: selectedText }
            ];
        } else {
            // 正常情况：提供精确和全局两种选项
            buttonConfigs = [
                { text: '🎯 选中区域添加脱敏', action: 'add-exact', key: textInfo.key, start: textInfo.start, end: textInfo.end, textData: selectedText },
                { text: '📄 整篇相同字节添加脱敏', action: 'add-global', key: textInfo.key, textData: selectedText }
            ];
        }

        const menu = createMenu(buttonConfigs);
        positionMenu(menu, x, y);
        attachMenuHandlers();
    }

    function attachMenuHandlers() {
        const menu = document.getElementById('redaction-menu');
        if (!menu) return;

        menu.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const action = this.dataset.action;
                const key = this.dataset.key;
                const start = parseInt(this.dataset.start);
                const end = parseInt(this.dataset.end);
                const text = this.dataset.text;

                if (action === 'remove') {
                    callRemove(key, start, end);
                } else if (action === 'add-exact') {
                    callAddExact(key, start, end, text);
                } else if (action === 'add-global') {
                    callAddGlobal(key, text);
                } else if (action === 'add-global-only') {
                    // 全局降级模式，不需要 key 参数
                    callAddGlobal(null, text);
                }
            });
        });
    }

    function callRemove(key, start, end) {
        console.log('[callRemove] 调用撤销: key=' + key + ' start=' + start + ' end=' + end);
        console.log('[callRemove] pyBridge=', pyBridge, 'webChannelReady=', webChannelReady);
        if (pyBridge && webChannelReady) {
            try {
                pyBridge.remove_manual_redaction(key, start, end);
                console.log('[callRemove] ✓ 撤销调用成功');
            } catch(e) {
                console.error('[callRemove] ✗ 撤销调用失败:', e);
            }
        } else {
            console.error('[callRemove] ✗ pyBridge 或 webChannel 未就绪');
        }
        hideContextMenu();
    }

    function callAddExact(key, start, end, text) {
        if (pyBridge && webChannelReady) {
            pyBridge.add_manual_redaction(key, start, end, text);
        }
        hideContextMenu();
        const selection = window.getSelection();
        selection.removeAllRanges();
    }

    function callAddGlobal(key, text) {
        console.log('[callAddGlobal] 调用全局脱敏: key=' + key + ', text=' + text?.substring(0, 30));
        if (pyBridge && webChannelReady) {
            // key 为 null 时表示纯全局模式
            pyBridge.add_manual_redaction_global(key || '', text);
        }
        hideContextMenu();
        const selection = window.getSelection();
        selection.removeAllRanges();
    }

    function findTextPosition(selectedText, range) {
        try {
            console.log('[findTextPosition] ========== 开始查找 ==========');
            console.log('[findTextPosition] 选中文本:', JSON.stringify(selectedText.substring(0, 50)));
            console.log('[findTextPosition] Range:', {
                startContainer: range.startContainer?.nodeName,
                startOffset: range.startOffset,
                endContainer: range.endContainer?.nodeName,
                endOffset: range.endOffset,
                text: range.toString().substring(0, 50)
            });

            let container = range.commonAncestorContainer;
            if (!container) {
                console.warn('[findTextPosition] ✗ 无 commonAncestorContainer，使用全局降级');
                return createGlobalFallbackResult(selectedText);
            }

            console.log('[findTextPosition] commonAncestorContainer:', container.nodeName, container.nodeType);

            // 如果是文本节点，获取其父元素
            if (container.nodeType === 3) {
                container = container.parentNode;
            }

            // 查找包含 data-key 的元素（向上遍历）
            let element = container;
            let maxIterations = 50;
            let iterations = 0;
            let foundKey = null;

            while (element && iterations < maxIterations) {
                iterations++;
                if (element.dataset && element.dataset.key) {
                    foundKey = element.dataset.key;
                    console.log('[findTextPosition] ✓ 找到 data-key:', foundKey);
                    break;
                }
                element = element.parentNode;
                if (element === document.body || element === document.documentElement) {
                    console.warn('[findTextPosition] 到达文档顶部，未找到 data-key，尝试文本内容定位');
                    break;  // 不返回 null，继续尝试其他方法
                }
            }

            // 方法 1: 精确计算（如果有 data-key）
            if (foundKey && element) {
                const key = foundKey;

                // === 方法 1a: 直接使用 Range 计算位置（最可靠）===
                try {
                    const textNodes = [];
                    const walker = document.createTreeWalker(
                        element,
                        NodeFilter.SHOW_TEXT,
                        {
                            acceptNode: function(node) {
                                // 接受所有非空文本节点
                                return NodeFilter.FILTER_ACCEPT;
                            }
                        }
                    );

                    let node;
                    while (node = walker.nextNode()) {
                        textNodes.push(node);
                    }

                    console.log('[findTextPosition] 找到', textNodes.length, '个文本节点');

                    // 打印所有文本节点信息
                    for (let i = 0; i < Math.min(textNodes.length, 10); i++) {
                        const tn = textNodes[i];
                        console.log(`[findTextPosition] 节点[${i}]:`, {
                            text: tn.textContent.substring(0, 30),
                            isStart: tn === range.startContainer,
                            isEnd: tn === range.endContainer
                        });
                    }

                    // 计算起始位置
                    let startOffset = 0;
                    let startFound = false;

                    // 特殊处理：如果 startContainer 是元素节点，找到它的第一个文本节点
                    let startContainer = range.startContainer;
                    if (startContainer.nodeType === 1) {  // 元素节点
                        console.log('[findTextPosition] startContainer 是元素节点，查找第一个文本子节点');
                        for (let i = 0; i < textNodes.length; i++) {
                            if (element.contains(textNodes[i]) || element === textNodes[i].parentNode) {
                                startContainer = textNodes[i];
                                break;
                            }
                        }
                    }

                    for (let i = 0; i < textNodes.length; i++) {
                        const tn = textNodes[i];
                        if (!startFound) {
                            if (tn === startContainer || (startContainer && tn.contains && tn.contains(startContainer))) {
                                startOffset += range.startOffset;
                                startFound = true;
                                console.log('[findTextPosition] ✓ 起始节点匹配, offset:', range.startOffset);
                            } else {
                                startOffset += tn.textContent.length;
                            }
                        }
                    }

                    // 计算结束位置
                    let endOffset = 0;
                    let endFound = false;

                    let endContainer = range.endContainer;
                    if (endContainer.nodeType === 1) {
                        console.log('[findTextPosition] endContainer 是元素节点，查找第一个文本子节点');
                        for (let i = 0; i < textNodes.length; i++) {
                            if (element.contains(textNodes[i]) || element === textNodes[i].parentNode) {
                                endContainer = textNodes[i];
                                break;
                            }
                        }
                    }

                    for (let i = 0; i < textNodes.length; i++) {
                        const tn = textNodes[i];
                        if (!endFound) {
                            if (tn === endContainer || (endContainer && tn.contains && tn.contains(endContainer))) {
                                endOffset += range.endOffset;
                                endFound = true;
                                console.log('[findTextPosition] ✓ 结束节点匹配, offset:', range.endOffset);
                            } else {
                                endOffset += tn.textContent.length;
                            }
                        }
                    }

                    console.log('[findTextPosition] Range 计算结果:', { startFound, endFound, startOffset, endOffset });

                    if (startFound && endFound && startOffset >= 0 && endOffset > startOffset) {
                        console.log('[findTextPosition] ✓✓✓ Range 计算成功 ✓✓✓');
                        return { key, start: startOffset, end: endOffset };
                    }
                } catch (e) {
                    console.error('[findTextPosition] Range 计算出错:', e);
                }

                // === 方法 1b: 文本匹配（后备）===
                console.log('[findTextPosition] 尝试文本匹配方法...');
                let originalText = '';
                if (element.dataset.originalText) {
                    // 安全解码：使用 DOMParser 替代 innerHTML，防止 XSS
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(element.dataset.originalText, 'text/html');
                    originalText = doc.body.textContent || '';
                    console.log('[findTextPosition] 原始文本长度:', originalText.length);
                }

                if (!originalText) {
                    originalText = element.textContent || '';
                }

                // 尝试直接匹配
                let foundStart = originalText.indexOf(selectedText);
                if (foundStart !== -1) {
                    console.log('[findTextPosition] ✓✓✓ 直接匹配成功 ✓✓✓');
                    return { key, start: foundStart, end: foundStart + selectedText.length };
                }

                // 尝试归一化匹配
                const normalizedSelected = selectedText.replace(/\s+/g, ' ').trim();
                const normalizedOriginal = originalText.replace(/\s+/g, ' ');
                foundStart = normalizedOriginal.indexOf(normalizedSelected);
                if (foundStart !== -1) {
                    console.log('[findTextPosition] ✓✓✓ 归一化匹配成功 ✓✓✓');
                    return { key, start: foundStart, end: foundStart + selectedText.length };
                }
            }

            // 方法 2: 文本内容定位（遍历所有 data-key 元素）
            console.log('[findTextPosition] 尝试文本内容定位方法...');
            const textResult = findPositionByTextContent(selectedText);
            if (textResult) {
                console.log('[findTextPosition] ✓✓✓ 文本内容定位成功 ✓✓✓');
                return textResult;
            }

            // 方法 3: 全局脱敏降级
            console.log('[findTextPosition] 所有精确方法失败，使用全局降级模式');
            return createGlobalFallbackResult(selectedText);

        } catch (e) {
            console.error('[findTextPosition] 异常:', e);
            return createGlobalFallbackResult(selectedText);
        }
    }

    function createGlobalFallbackResult(selectedText) {
        console.log('[findTextPosition] 创建全局降级结果，文本长度:', selectedText.length);
        return {
            key: '__GLOBAL__',
            start: 0,
            end: selectedText.length,
            mode: 'global',
            text: selectedText
        };
    }

    function findPositionByTextContent(selectedText) {
        // 遍历所有带有 data-key 的元素，查找包含选中文本的元素
        const elements = document.querySelectorAll('[data-key]');
        const normalizedSelected = selectedText.replace(/\s+/g, ' ').trim();

        for (const el of elements) {
            const key = el.dataset.key;
            if (!key || key === '__GLOBAL__') continue;

            let originalText = '';
            if (el.dataset.originalText) {
                // 安全解码：使用 DOMParser 替代 innerHTML，防止 XSS
                const parser = new DOMParser();
                const doc = parser.parseFromString(el.dataset.originalText, 'text/html');
                originalText = doc.body.textContent || '';
            } else {
                originalText = el.textContent || '';
            }

            const normalizedOriginal = originalText.replace(/\s+/g, ' ');
            const foundStart = normalizedOriginal.indexOf(normalizedSelected);

            if (foundStart !== -1) {
                console.log('[findTextPosition] 文本内容定位找到匹配，key:', key);
                return { key, start: foundStart, end: foundStart + selectedText.length };
            }
        }

        return null;
    }

    // v36.1 安全修复：使用 DOM 方法替代 innerHTML，防止 XSS
    function createMenu(buttonConfigs) {
        hideContextMenu();
        const menu = document.createElement('div');
        menu.id = 'redaction-menu';
        menu.style.cssText = 'position:fixed; background:white; border:1px solid #ddd; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.15); padding:8px 0; z-index:10000; min-width:150px;';

        const buttonStyle = 'display:block; width:100%; padding:8px 16px; border:none; background:none; text-align:left; cursor:pointer; font-size:14px; color:#333;';

        // 安全创建按钮元素，避免使用 innerHTML
        buttonConfigs.forEach(config => {
            const btn = document.createElement('button');
            btn.style.cssText = buttonStyle;
            btn.onmouseover = () => btn.style.backgroundColor = '#f5f5f5';
            btn.onmouseout = () => btn.style.backgroundColor = 'transparent';

            // 设置按钮文本（自动转义 HTML）
            btn.textContent = config.text || '';

            // 设置 data 属性
            if (config.action) btn.setAttribute('data-action', config.action);
            if (config.key !== undefined) btn.setAttribute('data-key', config.key);
            if (config.start !== undefined) btn.setAttribute('data-start', config.start);
            if (config.end !== undefined) btn.setAttribute('data-end', config.end);
            if (config.textData !== undefined) btn.setAttribute('data-text', config.textData);

            // 设置 disabled 状态
            if (config.disabled) {
                btn.disabled = true;
                btn.style.color = '#999';
                btn.style.cursor = 'default';
            }

            menu.appendChild(btn);
        });

        document.body.appendChild(menu);
        return menu;
    }

    function positionMenu(menu, x, y) {
        menu.style.display = 'block';
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
    }

    function hideContextMenu() {
        const menu = document.getElementById('redaction-menu');
        if (menu) menu.remove();
    }
</script>
"""

# === 主窗口 ===
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION} - Powered by li (汪立律师)")

        # 窗口尺寸设置：最小尺寸 + 默认尺寸
        self.setMinimumSize(900, 600)
        self.resize(1300, 900)

        # 窗口状态保存
        self.settings = QSettings("PrivacyGuard", "App")
        self._restore_window_state()

        self.doc = None
        self.word_doc = None  # Word 文档对象
        self.file_path = ""
        self.current_page = 0
        self.zoom_level = 1.0
        self.page_data = {}
        self.word_data = {}  # Word 文档数据结构
        self.doc_type = None  # 'pdf', 'docx', 'doc'
        self.replacement_text = "[已脱敏]"  # Word 替换文本
        self.active_rules = [DEFAULT_RULES["身份证号"], DEFAULT_RULES["手机号码"]]
        self.use_enhance = False
        self.custom_keywords = ""
        self.scan_level = 2.0
        self.current_color = QColor(0, 0, 0)

        self.offset_x = 0
        self.offset_w = 0
        self.dual_view = False

        # 预先创建 word_preview
        self.word_preview = None

        # 线程管理和临时文件管理（v24 稳定性优化）
        self.active_worker = None
        self.worker_lock = QMutex()
        self.temp_manager = TempFileManager()

        # 注册退出清理
        import atexit
        atexit.register(self._app_exit_cleanup)

        self.setup_ui()

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

        except Exception:
            # 检测失败，默认浅色
            return 'light'

    def _restore_window_state(self):
        """恢复窗口状态"""
        geometry = self.settings.value("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        """保存窗口状态并清理临时文件"""
        self._app_exit_cleanup()
        self.settings.setValue("window_geometry", self.saveGeometry())
        super().closeEvent(event)

    def resizeEvent(self, event):
        """窗口大小改变时自动重新适应页面"""
        super().resizeEvent(event)

        # 只在 PDF 模式且文档已加载时处理
        if not self.doc or self.current_page is None:
            return

        # 自动重新适应（保持页面完整显示）
        self.fit_page()

    def _app_exit_cleanup(self):
        """应用退出时的清理（v24 稳定性优化）"""
        # 取消正在运行的线程
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.requestInterruption()
            # 等待线程结束（最多 2 秒）
            self.active_worker.wait(2000)

        # 清理临时文件
        if hasattr(self, 'temp_manager'):
            self.temp_manager.cleanup()

        # 清理旧版临时文件
        self._cleanup_temp_file()

    # v22.4: 移除 eventFilter，直接在 SinglePageCanvas.mousePressEvent 中处理

    def setup_ui(self):
        # 信息栏
        info_bar = QLabel("📝 操作指引：1.导入PDF/Word → 2.设置规则 → 3.智能脱敏 → 4.涂黑/涂白 → 5.手动选取/画框脱敏 → 6.右键点击撤销 → 7.导出")
        info_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_bar.setFixedHeight(36)
        self.info_bar = info_bar  # 保存引用以便主题切换

        # 工具栏
        toolbar = QFrame()
        toolbar.setFixedHeight(56)
        self.toolbar = toolbar  # 保存引用

        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(16, 8, 16, 8)
        tb_layout.setSpacing(12)

        tb_layout.addWidget(self.create_btn("📂 打开", self.open_pdf))
        self.btn_settings = self.create_btn("⚙️ 高级设置", self.open_settings, style="secondary")
        tb_layout.addWidget(self.btn_settings)
        self.btn_scan = self.create_btn("🔍 智能脱敏", self.start_ocr, enabled=False, style="success")
        tb_layout.addWidget(self.btn_scan)

        tb_layout.addSpacing(10)
        self.rb_black = QRadioButton("⬛ 黑")
        self.rb_white = QRadioButton("⬜ 白")
        self.rb_black.setChecked(True)
        self.bg_color = QButtonGroup(self)
        self.bg_color.addButton(self.rb_black)
        self.bg_color.addButton(self.rb_white)
        self.rb_black.toggled.connect(self.update_canvas_color)
        self.rb_white.toggled.connect(self.update_canvas_color)
        tb_layout.addWidget(self.rb_black)
        tb_layout.addWidget(self.rb_white)

        tb_layout.addSpacing(10)
        self.cb_dual = QCheckBox("📖 双页")
        self.cb_dual.toggled.connect(self.toggle_dual_view)
        tb_layout.addWidget(self.cb_dual)

        self.btn_fit = self.create_btn("🔁 适应", self.fit_page)
        tb_layout.addWidget(self.btn_fit)

        tb_layout.addStretch()

        self.lbl_zoom = QLabel("100%")
        tb_layout.addWidget(self.create_btn("➖", self.zoom_out, style="icon"))
        tb_layout.addWidget(self.lbl_zoom)
        tb_layout.addWidget(self.create_btn("➕", self.zoom_in, style="icon"))
        tb_layout.addSpacing(15)

        tb_layout.addWidget(self.create_btn("⏮", self.go_first, style="icon"))
        tb_layout.addWidget(self.create_btn("◀", lambda: self.change_page(-1), style="icon"))
        self.lbl_page = QLabel("0 / 0")
        tb_layout.addWidget(self.lbl_page)
        tb_layout.addWidget(self.create_btn("▶", lambda: self.change_page(1 if not self.dual_view else 2), style="icon"))
        tb_layout.addWidget(self.create_btn("⏭", self.go_last, style="icon"))

        self.btn_save = self.create_btn("💾 导出", self.save_pdf, enabled=False)
        tb_layout.addWidget(self.btn_save)

        self.btn_feedback = self.create_btn("💬 吐槽", self.show_feedback, style="secondary")
        tb_layout.addWidget(self.btn_feedback)

        # Word 替换文本设置区域（仅在 Word 文档时显示）
        self.word_replacement_container = QWidget()
        word_repl_layout = QHBoxLayout(self.word_replacement_container)
        word_repl_layout.setContentsMargins(0, 0, 0, 0)
        word_repl_layout.setSpacing(8)

        word_repl_layout.addWidget(QLabel("替换文本:"))
        self.txt_replacement = QLineEdit()
        self.txt_replacement.setPlaceholderText("[已脱敏]")
        self.txt_replacement.setText(self.replacement_text)
        self.txt_replacement.setFixedWidth(150)
        self.txt_replacement.textChanged.connect(self._on_replacement_changed)
        word_repl_layout.addWidget(self.txt_replacement)

        tb_layout.addWidget(self.word_replacement_container)
        self.word_replacement_container.hide()  # 默认隐藏，打开 Word 文档时显示

        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(info_bar)
        layout.addWidget(toolbar)

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_style = f"background-color: {{0}}; border-radius: {Theme.BORDER_RADIUS}px;"

        # v22.9: 使用固定的 canvas_container，通过隐藏/显示实现单/双页切换
        self.canvas_left = SinglePageCanvas(0)
        self.canvas_right = SinglePageCanvas(1)

        # 容器始终作为 scroll 的 widget
        self.canvas_container = QWidget()
        self.canvas_layout = QHBoxLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(20, 20, 20, 20)
        self.canvas_layout.setSpacing(20)
        self.canvas_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_layout.addWidget(self.canvas_left)
        self.canvas_layout.addWidget(self.canvas_right)

        # 信号连接
        self.canvas_left.rect_added.connect(self.on_rect_added)
        self.canvas_left.rect_removed.connect(self.on_rect_removed)
        self.canvas_left.zoom_request.connect(self.handle_zoom_request)
        self.canvas_left.page_change_request.connect(self.handle_page_change_request)

        self.canvas_right.rect_added.connect(self.on_rect_added)
        self.canvas_right.rect_removed.connect(self.on_rect_removed)
        self.canvas_right.zoom_request.connect(self.handle_zoom_request)
        self.canvas_right.page_change_request.connect(self.handle_page_change_request)

        # 设置 canvas 大小策略
        for canvas in [self.canvas_left, self.canvas_right]:
            canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # 预先创建 Word 预览视图
        self.word_preview = QWebEngineView()
        self.bridge = None  # WebViewBridge 将在首次渲染时初始化

        # 创建主容器，包含 canvas_container 和 word_preview
        self.main_container = QWidget()
        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.canvas_container)
        self.main_layout.addWidget(self.word_preview)

        # 默认隐藏 Word 预览
        self.word_preview.hide()

        # 设置 container 为固定的 widget
        self.scroll.setWidget(self.main_container)
        # 默认单页模式：隐藏右页
        self.canvas_right.hide()

        layout.addWidget(self.scroll)

        # 进度条和取消按钮区域（v36.3: 添加取消按钮）
        progress_layout = QHBoxLayout()

        self.progress = QProgressBar()
        self.progress.setFixedHeight(24)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        progress_layout.addWidget(self.progress, stretch=1)

        # 取消扫描按钮（初始隐藏）
        self.btn_cancel_scan = QPushButton("取消")
        self.btn_cancel_scan.setFixedSize(60, 24)
        self.btn_cancel_scan.setToolTip("停止扫描并保留已扫描结果")
        self.btn_cancel_scan.clicked.connect(self.cancel_ocr_scan)
        self.btn_cancel_scan.setVisible(False)  # 初始隐藏
        progress_layout.addWidget(self.btn_cancel_scan)

        layout.addLayout(progress_layout)

        # 应用浅色主题样式
        self._apply_light_theme()

    def _apply_light_theme(self):
        """应用浅色主题样式（v35.1: Windows 强制浅色主题）"""
        import platform

        theme = Theme.LIGHT

        # 主窗口背景样式（确保整体色调统一）
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme["background"]};
            }}
            QWidget {{
                background-color: {theme["background"]};
            }}
        """)

        # 信息栏
        self.info_bar.setStyleSheet(f"""
            QLabel {{
                background-color: {theme["info_bar"]};
                color: {theme["text"]};
                padding: 8px;
                font-weight: 600;
                font-size: {Theme.FONT_SIZE_SMALL}px;
            }}
        """)

        # 工具栏
        self.toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {theme["surface"]};
                border-bottom: 1px solid {theme["border"]};
            }}
        """)

        # 滚动区域
        self.scroll.setStyleSheet(self.scroll_style.format(theme["scroll_area"]))

        # 标签文本颜色
        text_color = theme["text"]
        self.lbl_zoom.setStyleSheet(f"color: {text_color}; font-size: {Theme.FONT_SIZE_NORMAL}px;")
        self.lbl_page.setStyleSheet(f"color: {text_color}; font-size: {Theme.FONT_SIZE_NORMAL}px;")

        # 单选框和复选框
        color = theme["text"]
        style = f"color: {color}; font-size: {Theme.FONT_SIZE_NORMAL}px;"
        self.rb_black.setStyleSheet(style)
        self.rb_white.setStyleSheet(style)
        self.cb_dual.setStyleSheet(style)

        # 进度条
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E5E5EA;
                border: none;
                border-radius: 3px;
                color: #1D1D1F;
                font-weight: 600;
                font-size: 12px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007AFF, stop:1 #34C759);
                border-radius: 3px;
            }}
        """)

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

        # 应用样式
        btn.setStyleSheet(self._get_button_style(style))

        # 保存样式类型以便主题切换
        btn.setProperty("btn_style", style)

        return btn

    def _get_button_style(self, style_type):
        """获取按钮样式（浅色主题）"""
        theme = Theme.LIGHT

        styles = {
            "primary": f"""
                QPushButton {{
                    background-color: {theme["primary"]};
                    color: white;
                    border: none;
                    border-radius: {Theme.BUTTON_RADIUS}px;
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: {Theme.FONT_SIZE_NORMAL}px;
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
                    background-color: transparent;
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: {Theme.BUTTON_RADIUS}px;
                    padding: 8px 16px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {theme["surface"]};
                    border-color: {theme["primary"]};
                }}
            """,
            "success": f"""
                QPushButton {{
                    background-color: {theme["success"]};
                    color: white;
                    border: none;
                    border-radius: {Theme.BUTTON_RADIUS}px;
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: {Theme.FONT_SIZE_NORMAL}px;
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
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: {Theme.FONT_SIZE_NORMAL}px;
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
                    background-color: transparent;
                    color: {theme["text"]};
                    border: none;
                    border-radius: 6px;
                    padding: 6px;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    background-color: {theme["hover"]};
                }}
                QPushButton:pressed {{
                    background-color: {theme["pressed"]};
                }}
            """,
        }

        return styles.get(style_type, styles["primary"])

    def handle_zoom_request(self, delta):
        new_zoom = self.zoom_level + delta
        if new_zoom < ZOOM_MIN: new_zoom = ZOOM_MIN
        if new_zoom > ZOOM_MAX: new_zoom = ZOOM_MAX
        self.zoom_level = new_zoom
        self.render_view()

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

    def update_canvas_color(self):
        if self.rb_black.isChecked(): self.current_color = QColor(0,0,0)
        else: self.current_color = QColor(255,255,255)
        self.render_view()

    def open_settings(self):
        dlg = SettingsDialog(self, self.active_rules, self.use_enhance, self.custom_keywords, self.scan_level, self.offset_x, self.offset_w)
        if dlg.exec():
            self.active_rules = dlg.selected_rules
            self.use_enhance = dlg.use_enhance
            self.custom_keywords = dlg.custom_keywords
            self.scan_level = dlg.scan_level
            self.offset_x = dlg.offset_x
            self.offset_w = dlg.offset_w
            QMessageBox.information(self, "成功", "设置已保存")

    def show_feedback(self):
        """显示反馈与开发者信息对话框"""
        dlg = FeedbackDialog(self)
        dlg.exec()

    def _on_replacement_changed(self, text):
        """替换文本变化时的处理"""
        self.replacement_text = text if text.strip() else "[已脱敏]"

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
        return """
            QFileDialog {
                background-color: #FFFFFF;
                color: #1D1D1F;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QFileDialog QLabel { color: #1D1D1F; }
            /* 按钮使用系统默认样式，确保跨平台可读性 */
            /* macOS/Windows 会自动应用适合的按钮颜色 */
            QFileDialog QListView, QFileDialog QTreeView {
                background-color: #FFFFFF;
                color: #1D1D1F;
                border: 1px solid #D1D1D6;
            }
            QFileDialog QListView::item:selected, QFileDialog QTreeView::item:selected {
                background-color: #007AFF;
                color: white;
            }
            QFileDialog QComboBox {
                background-color: #FFFFFF;
                color: #1D1D1F;
                border: 1px solid #D1D1D6;
                padding: 4px;
            }
            QFileDialog QLineEdit {
                background-color: #FFFFFF;
                color: #1D1D1F;
                border: 1px solid #D1D1D6;
                padding: 4px;
            }
        """

    def open_pdf(self):
        """打开文件（支持图片多选）"""
        try:
            # 先清理临时文件
            self._cleanup_temp_file()

            # v36: 应用文件对话框样式
            app = QApplication.instance()
            original_style = app.styleSheet()
            app.setStyleSheet(self._get_file_dialog_style())

            try:
                fnames, _ = QFileDialog.getOpenFileNames(
                    self, "选择文件", "",
                    "支持的文件 (*.pdf *.doc *.docx *.jpg *.jpeg *.png *.bmp *.tiff)",
                    options=QFileDialog.Option.DontUseNativeDialog
                )
            finally:
                app.setStyleSheet(original_style)

            if not fnames:
                return

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
                # 多个文件，检查是否都是图片
                are_all_images = all(self.detect_file_type(f) == 'image' for f in fnames)
                if are_all_images:
                    self._open_images_merge(fnames)
                else:
                    QMessageBox.warning(self, "不支持的混合选择",
                        "当前只支持同时打开多个图片文件。\n\n"
                        "如需处理PDF/Word，请一次只选择一个文件。\n"
                        "如需合并多张图片，请只选择图片文件（JPG、PNG、BMP等）")
        except (IOError, OSError, ValueError, ConversionError) as e:
            QMessageBox.critical(self, "错误", f"打开文件失败: {str(e)}")

    def _open_pdf_file(self, fname):
        """内部方法：打开 PDF 文件"""
        # 关闭已打开的PDF文档（防止资源泄露）
        if self.doc:
            self.doc.close()
            self.doc = None

        self.file_path = fname
        self.doc = fitz.open(fname)
        self.doc_type = 'pdf'
        total = len(self.doc)
        self.page_data = {i: {'ocr': [], 'manual': []} for i in range(total)}
        self.current_page = 0
        self.word_doc = None
        self.word_data = {}
        self.btn_scan.setEnabled(True)
        self.btn_save.setEnabled(True)

        # 显示 PDF 特有控件
        self.cb_dual.show()
        self.rb_black.show()
        self.rb_white.show()
        self.btn_fit.show()
        self.lbl_zoom.show()

        # 隐藏 Word 替换文本控件
        self.word_replacement_container.hide()

        # 切换显示：显示 canvas，隐藏 Word 预览
        self.canvas_container.show()
        self.word_preview.hide()

        self.fit_page()

    def _open_word_docx(self, fname):
        """打开 DOCX 文件"""
        try:
            from docx import Document

            self.word_doc = Document(fname)
            self.file_path = fname
            self.doc_type = 'docx'
            self.doc = None  # 清空 PDF 文档对象
            self.page_data = {}

            # 初始化 word_data 结构
            self.word_data = {}
            for idx, para in enumerate(self.word_doc.paragraphs):
                self.word_data[f'paragraph_{idx}'] = {
                    'type': 'paragraph',
                    'index': idx,
                    'text': para.text,
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
                            'text': cell.text,
                            'ocr': [],
                            'manual': []
                        }

            # 启用按钮
            self.btn_scan.setEnabled(True)
            self.btn_save.setEnabled(True)

            # 隐藏 PDF 特有控件
            self.cb_dual.hide()
            self.rb_black.hide()
            self.rb_white.hide()
            self.btn_fit.hide()
            self.lbl_zoom.hide()

            # 显示 Word 替换文本控件
            self.word_replacement_container.show()

            # 显示 HTML 预览
            self.render_word_preview()

            # 更新信息
            self.info_bar.setText(f"📝 Word 文档: {os.path.basename(fname)} - {len(self.word_doc.paragraphs)} 个段落, {len(self.word_doc.tables)} 个表格")

        except (IOError, OSError, ValueError, KeyError) as e:
            QMessageBox.critical(self, "错误", f"打开 Word 文档失败: {str(e)}")

    def _open_word_doc(self, fname):
        """打开 .doc 文件（通过转换为 .docx）"""
        import shutil
        import subprocess
        import tempfile

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
                # 更新信息栏，显示原始文件名
                original_name = os.path.basename(fname)
                self.info_bar.setText(f"📝 Word 文档 (.doc 转换): {original_name} - {len(self.word_doc.paragraphs)} 个段落, {len(self.word_doc.tables)} 个表格")
        except (IOError, OSError, ValueError, RuntimeError) as e:
            QMessageBox.critical(self, "转换失败", f"无法转换 .doc 文件:\n{str(e)}")
        finally:
            QApplication.restoreOverrideCursor()

    def _check_doc_support(self):
        """检查系统是否支持 .doc 格式（v35.1: 增强跨平台检测）"""
        import shutil
        import platform

        system = platform.system()
        result = {
            'libreoffice': False,
            'antiword': False,
            'recommended': None
        }

        # 检查 LibreOffice
        if system == 'Darwin':  # macOS
            # 检查应用程序目录
            libreoffice_app = '/Applications/LibreOffice.app/Contents/MacOS/soffice'
            if os.path.exists(libreoffice_app):
                result['libreoffice'] = True
            # 也检查 PATH
            elif shutil.which('soffice'):
                result['libreoffice'] = True
        elif system == 'Windows':
            # Windows: 检查常见安装路径
            program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
            libreoffice_paths = [
                os.path.join(program_files, 'LibreOffice', 'program', 'soffice.exe'),
                os.path.join(program_files_x86, 'LibreOffice', 'program', 'soffice.exe'),
            ]
            for path in libreoffice_paths:
                if os.path.exists(path):
                    result['libreoffice'] = True
                    break
        else:  # Linux
            if shutil.which('soffice') or shutil.which('libreoffice'):
                result['libreoffice'] = True

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
        """转换 .doc 为 .docx"""
        import tempfile
        import subprocess

        if method == 'libreoffice':
            return self._convert_with_libreoffice(doc_path)
        elif method == 'antiword':
            return self._convert_with_antiword(doc_path)
        else:
            raise ValueError(f"不支持的转换方法: {method}")

    def _convert_with_libreoffice(self, doc_path, max_retries=2):
        """使用 LibreOffice 转换（v36.2: 增强诊断 + 安全验证）

        安全特性 (v36.2):
        - 使用 validate_safe_path() 验证临时文件路径
        - 使用 validate_safe_path() 验证临时目录
        - 使用具体异常类型处理错误

        Args:
            doc_path: 源 .doc 文件路径
            max_retries: 最大重试次数

        Returns:
            str: 转换后的 .docx 文件路径

        Raises:
            ConversionError: 转换失败时抛出
        """
        import subprocess
        import time
        import shutil as shutil_module
        import glob

        # 使用 TempFileManager 管理临时目录
        temp_dir = self.temp_manager.create_temp_dir()
        base_name = os.path.splitext(os.path.basename(doc_path))[0]

        # 将源文件复制到临时目录，确保路径为纯英文
        temp_doc_path = os.path.join(temp_dir, "source.doc")
        shutil_module.copy2(doc_path, temp_doc_path)

        print(f"[DOC转换] 原始路径: {doc_path}")
        print(f"[DOC转换] 临时路径: {temp_doc_path}")
        print(f"[DOC转换] 输出目录: {temp_dir}")

        # 验证输入文件
        if not os.path.exists(temp_doc_path):
            raise ConversionError("源文件复制失败", f"无法复制到: {temp_doc_path}")
        print(f"[DOC转换] 输入文件大小: {os.path.getsize(temp_doc_path)} bytes")

        # v36.2: 验证路径安全
        is_safe, error_msg = validate_safe_path(temp_doc_path, allowed_extensions=['.doc'])
        if not is_safe:
            raise ConversionError("文件路径不安全", error_msg)

        is_safe, error_msg = validate_safe_path(temp_dir)
        if not is_safe:
            raise ConversionError("临时目录不安全", error_msg)

        for attempt in range(max_retries + 1):
            try:
                print(f"[DOC转换] 尝试 {attempt + 1}/{max_retries + 1}...")

                cmd = [
                    'soffice',
                    '--headless',
                    '--convert-to', 'docx',
                    '--outdir', temp_dir,
                    temp_doc_path
                ]
                print(f"[DOC转换] 执行命令: {' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                print(f"[DOC转换] 返回码: {result.returncode}")
                if result.stdout:
                    print(f"[DOC转换] stdout: {result.stdout}")
                if result.stderr:
                    print(f"[DOC转换] stderr: {result.stderr}")

                # 列出临时目录内容
                files = glob.glob(os.path.join(temp_dir, '*'))
                print(f"[DOC转换] 目录内容: {[os.path.basename(f) for f in files]}")

                if result.returncode != 0:
                    raise subprocess.CalledProcessError(
                        result.returncode, cmd,
                        output=result.stdout, stderr=result.stderr
                    )

                # 检查输出文件
                docx_path = os.path.join(temp_dir, 'source.docx')
                if not os.path.exists(docx_path):
                    # 尝试原始文件名（兼容旧逻辑）
                    docx_path = os.path.join(temp_dir, base_name + '.docx')

                if not os.path.exists(docx_path):
                    raise ConversionError(
                        "转换失败，未生成输出文件",
                        f"目录内容: {[os.path.basename(f) for f in files]}"
                    )

                print(f"[DOC转换] 成功: {docx_path}")
                return docx_path

            except subprocess.TimeoutExpired:
                if attempt < max_retries:
                    print(f"[DOC转换] 超时，等待重试...")
                    time.sleep(2)
                    continue
                else:
                    raise ConversionError(
                        "转换超时（60秒）",
                        "请检查 LibreOffice 是否响应，或尝试重启应用"
                    )

            except subprocess.CalledProcessError as e:
                print(f"[DOC转换] 命令失败: {e}")
                if e.stderr:
                    print(f"[DOC转换] stderr: {e.stderr}")
                if attempt < max_retries:
                    print(f"[DOC转换] 等待重试...")
                    time.sleep(2)
                    continue
                else:
                    error_msg = e.stderr if e.stderr else "未知错误"
                    raise ConversionError(
                        f"LibreOffice 转换失败",
                        f"错误信息: {error_msg}\n\n请确保 LibreOffice 已正确安装"
                    )

            except (OSError, IOError, RuntimeError, ValueError) as e:
                raise ConversionError(
                    f"LibreOffice 转换出错: {str(e)}",
                    "请尝试在 Word 中手动另存为 .docx 格式"
                )

    def _convert_with_antiword(self, doc_path):
        """使用 antiword 提取文本并创建 .docx（v36.2: 安全验证版）

        安全特性 (v36.2):
        - 使用 validate_safe_path() 验证输入文件路径
        - 使用具体异常类型处理错误 (OSError, IOError, RuntimeError, ValueError, ImportError)

        Args:
            doc_path: 源 .doc 文件路径

        Returns:
            str: 转换后的 .docx 文件路径

        Raises:
            ConversionError: 转换失败时抛出
        """
        from docx import Document

        try:
            # v36.2: 验证路径安全
            is_safe, error_msg = validate_safe_path(doc_path, allowed_extensions=['.doc'])
            if not is_safe:
                raise ConversionError("文件路径不安全", error_msg)

            # 提取文本
            result = subprocess.run(['antiword', doc_path],
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise ConversionError("antiword 提取失败", "请检查 .doc 文件是否损坏")

            # 创建新的 docx
            doc = Document()
            for line in result.stdout.split('\n'):
                if line.strip():
                    doc.add_paragraph(line)

            # 使用 TempFileManager 管理临时文件
            temp_file = self.temp_manager.create_temp_file(suffix='.docx')
            doc.save(temp_file)
            return temp_file

        except subprocess.TimeoutExpired:
            raise ConversionError("提取超时", "请尝试使用 LibreOffice 转换")
        except FileNotFoundError:
            raise ConversionError(
                "未找到 antiword 命令",
                "请安装: brew install antiword\n或使用 LibreOffice 转换"
            )
        except (OSError, IOError, RuntimeError, ValueError, ImportError) as e:
            raise ConversionError(
                f"antiword 转换失败: {str(e)}",
                "请尝试使用 LibreOffice 转换或在 Word 中手动另存为 .docx"
            )

    def _open_images_merge(self, image_paths):
        """处理图片合并为PDF"""
        try:
            # 1. 让用户排序（如果是多张图片）
            if len(image_paths) > 1:
                dlg = ImageListDialog(image_paths, self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                image_paths = dlg.get_ordered_paths()

            # 2. 生成输出路径（在第一张图片所在目录）
            base_dir = os.path.dirname(image_paths[0])
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_filename = f"merged_{timestamp}.pdf"
            final_path = os.path.join(base_dir, output_filename)

            # 3. 创建临时文件
            temp_pdf = self.temp_manager.create_temp_file(suffix='.pdf')

            # 4. 启动Worker合并
            self.merge_worker = ImageMergeWorker(image_paths, temp_pdf)
            self.merge_worker.progress_signal.connect(self.progress.setValue)
            self.merge_worker.finished_signal.connect(lambda p: self._on_merge_finished(p, final_path))
            self.merge_worker.error_signal.connect(self._on_merge_error)
            self.merge_worker.start()

            self.info_bar.setText(f"正在合并 {len(image_paths)} 张图片...")

        except (IOError, OSError, ValueError, RuntimeError) as e:
            QMessageBox.critical(self, "错误", f"启动图片合并失败: {str(e)}")

    def _on_merge_finished(self, temp_pdf, final_path):
        """合并完成回调"""
        try:
            # 将临时文件移动到最终位置
            shutil.move(temp_pdf, final_path)
            self.info_bar.setText(f"✓ 合并完成: {final_path}")

            # 自动打开生成的PDF
            self._open_pdf_file(final_path)

        except (IOError, OSError, ValueError) as e:
            QMessageBox.critical(self, "错误", f"保存合并文件失败: {str(e)}")

    def _on_merge_error(self, error_msg):
        """合并错误回调"""
        self.info_bar.setText("✗ 合并失败")
        QMessageBox.critical(self, "合并失败", error_msg)

    def _cleanup_temp_file(self):
        """清理转换产生的临时文件（v36.1 安全修复：跨平台安全清理）"""
        import tempfile

        if hasattr(self, 'converted_temp_file') and self.converted_temp_file:
            try:
                if os.path.exists(self.converted_temp_file):
                    os.remove(self.converted_temp_file)
                    print(f"[清理] 已删除临时文件: {self.converted_temp_file}")

                # 清理临时目录（安全版本）
                temp_dir = os.path.dirname(self.converted_temp_file)

                # 获取系统临时目录（跨平台：Windows 返回 C:\Users\...\AppData\Local\Temp，macOS/Linux 返回 /tmp 或 /var/tmp）
                system_temp_dir = tempfile.gettempdir()

                # 规范化路径进行比较（处理大小写敏感/不敏感、路径分隔符等）
                norm_temp_dir = os.path.normcase(os.path.abspath(temp_dir))
                norm_system_temp = os.path.normcase(os.path.abspath(system_temp_dir))

                # 安全检查：只有当目录位于系统临时目录下，且不是系统临时目录本身时才删除
                if (norm_temp_dir.startswith(norm_system_temp + os.sep) and
                    norm_temp_dir != norm_system_temp):
                    try:
                        # 检查目录是否为空（防止误删文件）
                        if os.path.isdir(temp_dir) and not os.listdir(temp_dir):
                            os.rmdir(temp_dir)
                            print(f"[清理] 已删除空临时目录: {temp_dir}")
                        else:
                            print(f"[清理] 临时目录非空或不存在，跳过删除: {temp_dir}")
                    except OSError as e:
                        print(f"[清理] 删除临时目录时出错（可能是非空）: {temp_dir} - {e}")
                else:
                    print(f"[清理] 跳过非系统临时目录: {temp_dir}")

            except Exception as e:
                print(f"[清理] 清理临时文件时出错: {e}")
            finally:
                self.converted_temp_file = None

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

    def fit_page(self):
        """完整适应页面 - 根据窗口和页面尺寸动态计算缩放比例"""
        if not self.doc or self.current_page is None:
            return

        # 获取画布可用尺寸（减去边距）
        canvas_width = self.scroll.width() - 40  # 40px 边距
        canvas_height = self.scroll.height() - 40

        # 获取当前页面的实际尺寸（点单位）
        page = self.doc[self.current_page]
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height

        # 分别计算宽度和高度的缩放比例
        zoom_w = canvas_width / page_width
        zoom_h = canvas_height / page_height

        # 取较小值确保页面完整显示在窗口中
        self.zoom_level = min(zoom_w, zoom_h)

        # 限制在最大最小范围内 (v33.2: 允许突破 ZOOM_MIN 以完整显示)
        self.zoom_level = self.clamp_zoom(self.zoom_level, allow_below_min=True)

        # 重新渲染
        self.render_view()

    def render_view(self):
        if not self.doc: return
        self._render_single_page(self.canvas_left, self.current_page)
        if self.dual_view:
            if self.current_page + 1 < len(self.doc):
                self._render_single_page(self.canvas_right, self.current_page + 1)
                self.canvas_right.show()
            else:
                self.canvas_right.hide()
        
        total = len(self.doc)
        display = f"{self.current_page + 1}"
        if self.dual_view and self.current_page + 1 < total:
            display += f"-{self.current_page + 2}"
        self.lbl_page.setText(f"{display} / {total}")
        self.lbl_zoom.setText(f"{int(self.zoom_level * 100)}%")

    def _render_single_page(self, canvas, page_idx):
        """v7.0 风格渲染 - 直接传递列表引用"""
        page = self.doc[page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom_level, self.zoom_level))
        img_fmt = QImage.Format.Format_RGB888
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, img_fmt).copy()
        data = self.page_data[page_idx]
        canvas.update_content(QPixmap.fromImage(qimg), self.zoom_level, data['ocr'], data['manual'])
        canvas.set_mask_color(self.current_color)

    def on_rect_added(self, page_idx, rect):
        """由于使用共享列表引用，canvas 已直接修改列表，这里只需刷新视图"""
        # self.page_data[page_idx]['manual'].append(rect)  # 不需要，canvas 已经添加
        self.render_view()

    def on_rect_removed(self, page_idx, rect_idx, is_manual):
        """由于使用共享列表引用，canvas 已直接修改列表，这里只需刷新视图"""
        # if is_manual: del self.page_data[page_idx]['manual'][rect_idx]  # 不需要，canvas 已经删除
        # else: del self.page_data[page_idx]['ocr'][rect_idx]
        self.render_view()

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

    def start_ocr(self):
        """智能扫描 - 支持 PDF 和 Word（v24 线程安全改进）"""
        # 线程安全检查：防止重复启动
        if self.active_worker is not None:
            if self.active_worker.isRunning():
                QMessageBox.warning(self, "提示", "正在处理中，请稍候...")
                return

        self.info_bar.setText("🔍 正在扫描敏感信息...")
        self.btn_scan.setEnabled(False)
        self.btn_cancel_scan.setVisible(True)  # 显示取消按钮（v36.3）
        self.btn_cancel_scan.setEnabled(True)

        # PDF 处理
        if self.doc:
            self.worker = OCRWorker(self.file_path, self.active_rules, self.use_enhance, self.custom_keywords,
                                    self.scan_level, self.offset_x, self.offset_w)
            self.active_worker = self.worker  # 追踪线程
            self.worker.progress_signal.connect(self.progress.setValue)
            # v36.4: 使用线程安全的逐页结果信号
            self.worker.page_result_signal.connect(self._on_ocr_page_result)
            # 先连接原有的完成处理，再连接清理
            self.worker.finished_signal.connect(self._on_ocr_finished_safe)
            self.worker.finished_signal.connect(self._on_worker_finished)
            self.worker.start()
        # Word 处理
        elif self.word_doc:
            self.worker = WordWorker(self.word_doc, self.word_data, self.active_rules,
                                     self.custom_keywords, self.replacement_text)
            self.active_worker = self.worker  # 追踪线程
            self.worker.progress_signal.connect(self.progress.setValue)
            # 先连接原有的完成处理，再连接清理
            self.worker.finished_signal.connect(self.word_scan_finished)
            self.worker.finished_signal.connect(self._on_worker_finished)
            self.worker.start()

    def cancel_ocr_scan(self):
        """取消智能脱敏扫描（v36.3）"""
        if self.active_worker and self.active_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "确认取消",
                "确定要停止扫描吗？\n已扫描的进度将被保留。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.info_bar.setText("⏹️ 正在停止扫描...")
                self.btn_cancel_scan.setEnabled(False)  # 防止重复点击
                self.active_worker.requestInterruption()  # 请求中断
                # Worker会在完成后通过finished_signal通知主线程

    def _on_worker_finished(self):
        """工作线程完成后的清理（v36.3: 支持取消）"""
        was_cancelled = self.active_worker and self.active_worker.isInterruptionRequested()
        self.active_worker = None
        self.btn_scan.setEnabled(True)
        self.btn_cancel_scan.setVisible(False)  # 隐藏取消按钮
        self.btn_cancel_scan.setEnabled(True)

        if was_cancelled:
            self.info_bar.setText("⏹️ 扫描已取消，已保留部分结果")
        else:
            self.info_bar.setText("✅ 扫描完成！")

    def ocr_finished(self, results):
        """v23.1: 添加去重逻辑，解决重复矩形导致的点击2次问题；v36.3: 支持部分结果"""
        total_pages = len(self.page_data)
        scanned_pages = len(results)

        for page, rects in results.items():
            # 去重：移除重复或高度重叠的矩形
            deduped = self._deduplicate_rects(rects)
            self.page_data[page]['ocr'] = deduped
            if len(rects) != len(deduped):
                if DEBUG_MODE:
                    print(f"[DEBUG] 页面{page}: 去重前{len(rects)}个矩形, 去重后{len(deduped)}个")
        self.render_view()
        self.progress.setValue(0)

        # 判断是部分结果还是完整结果（v36.3）
        if scanned_pages < total_pages:
            QMessageBox.information(
                self,
                "扫描已取消",
                f"已扫描 {scanned_pages}/{total_pages} 页，\n部分结果已保留，可以继续编辑。"
            )
        else:
            QMessageBox.information(self, "完成", "智能扫描已完成！")

    # v36.4: 线程安全的 OCR 结果处理方法
    def _on_ocr_page_result(self, page_num: int, rects: list):
        """v36.4: 线程安全 - 接收单页 OCR 结果（在主线程执行）"""
        if page_num in self.page_data:
            # 去重：移除重复或高度重叠的矩形
            deduped = self._deduplicate_rects(rects)
            self.page_data[page_num]['ocr'] = deduped
            if DEBUG_MODE and len(rects) != len(deduped):
                print(f"[DEBUG] 页面{page_num}: 去重前{len(rects)}个矩形, 去重后{len(deduped)}个")

    def _on_ocr_finished_safe(self, _):
        """v36.4: 线程安全 - OCR 完成处理（在主线程执行）

        参数 _ 是空字典，保留以兼容信号签名
        """
        self.render_view()
        self.progress.setValue(0)

        # 统计已扫描的页面
        scanned_pages = sum(1 for p in self.page_data.values() if p['ocr'])
        total_pages = len(self.page_data)

        # 判断是部分结果还是完整结果
        if scanned_pages < total_pages:
            QMessageBox.information(
                self,
                "扫描已取消",
                f"已扫描 {scanned_pages}/{total_pages} 页，\n部分结果已保留，可以继续编辑。"
            )
        else:
            QMessageBox.information(self, "完成", "智能扫描已完成！")

    def _deduplicate_rects(self, rects):
        """移除重复或高度重叠的矩形"""
        if not rects:
            return rects

        # 按中心点坐标和尺寸排序，便于去重
        sorted_rects = sorted(rects, key=lambda r: (r.x(), r.y(), r.width(), r.height()))
        deduped = []

        for rect in sorted_rects:
            is_duplicate = False
            for existing in deduped:
                # 检查是否与已有矩形高度重叠（IoU > 0.7 或中心点距离 < 5 像素）
                if self._is_overlapping(rect, existing):
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduped.append(rect)

        return deduped

    def _is_overlapping(self, rect1, rect2, threshold=0.7):
        """检查两个矩形是否高度重叠"""
        # 计算交集
        x_left = max(rect1.x(), rect2.x())
        y_top = max(rect1.y(), rect2.y())
        x_right = min(rect1.x() + rect1.width(), rect2.x() + rect2.width())
        y_bottom = min(rect1.y() + rect1.height(), rect2.y() + rect2.height())

        if x_right < x_left or y_bottom < y_top:
            return False

        # 计算交集面积
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = rect1.width() * rect1.height()
        area2 = rect2.width() * rect2.height()

        # IoU > threshold 视为重复
        union = area1 + area2 - intersection
        iou = intersection / union if union > 0 else 0

        # 或者中心点距离 < 5 像素也视为重复
        center1_x = rect1.x() + rect1.width() / 2
        center1_y = rect1.y() + rect1.height() / 2
        center2_x = rect2.x() + rect2.width() / 2
        center2_y = rect2.y() + rect2.height() / 2
        distance = ((center1_x - center2_x)**2 + (center1_y - center2_y)**2)**0.5

        return iou > threshold or distance < 5

    def word_scan_finished(self, results):
        """Word 文档扫描完成（v36.3: 支持部分结果）"""
        total_items = len(self.word_data)
        processed_items = len([k for k, v in results.items() if v.get('ocr')])

        self.word_data = results
        self.render_word_preview()
        self.progress.setValue(0)

        # 统计扫描结果
        total_matches = sum(len(data['ocr']) for data in self.word_data.values())

        # 判断是部分结果还是完整结果（v36.3）
        if processed_items < total_items:
            QMessageBox.information(
                self,
                "扫描已取消",
                f"已处理 {processed_items}/{total_items} 个段落/单元格，\n部分结果已保留，可以继续编辑。"
            )
        else:
            QMessageBox.information(self, "完成", f"智能扫描已完成！\n共发现 {total_matches} 处敏感信息")

    def render_word_preview(self):
        """渲染 Word 文档预览（HTML）"""
        if not self.word_doc:
            return

        try:
            import mammoth

            # 改进: 不需要在 Python 端保存滚动位置
            # 使用 localStorage 在 JavaScript 端自动保存/恢复

            with open(self.file_path, 'rb') as docx_file:
                result = mammoth.convert_to_html(docx_file)
                html = result.value

            # 高亮显示敏感信息
            html = self._highlight_sensitive_info(html)

            # 注入交互式 HTML，并添加滚动恢复脚本（使用 localStorage 自动保存/恢复）
            # v33.1: 改进版本 - 添加 localStorage 可用性检测和内存降级策略
            scroll_restore = '''<script>
    (function() {
        const STORAGE_KEY = 'word_preview_scroll_pos';
        let memoryScrollPos = 0;

        // 检测 localStorage 是否可用（v33.1: 修复 data: URL 中的错误）
        function isLocalStorageAvailable() {
            try {
                const test = '__localStorage_test__';
                localStorage.setItem(test, test);
                localStorage.removeItem(test);
                return true;
            } catch (e) {
                return false;
            }
        }

        const useLocalStorage = isLocalStorageAvailable();

        // 保存滚动位置（v33.1: 静默失败，无错误日志）
        function saveScroll() {
            const scrollY = window.pageYOffset || document.documentElement?.scrollTop || document.body?.scrollTop || 0;
            memoryScrollPos = scrollY;
            if (useLocalStorage) {
                try {
                    localStorage.setItem(STORAGE_KEY, scrollY.toString());
                } catch (e) {
                    // 静默失败，使用内存变量作为降级策略
                }
            }
        }

        // 立即保存一次（页面加载时）
        saveScroll();

        // 恢复滚动位置（立即执行，无动画）
        function restoreScroll() {
            let savedPos = null;
            if (useLocalStorage) {
                try {
                    savedPos = localStorage.getItem(STORAGE_KEY);
                } catch (e) {
                    // 静默失败，使用内存变量
                }
            }
            if (!savedPos) {
                savedPos = memoryScrollPos.toString();
            }

            if (savedPos) {
                const targetY = parseInt(savedPos, 10);
                if (!isNaN(targetY) && targetY > 0) {
                    // 立即滚动，不等待
                    window.scrollTo(0, targetY);
                    // 二次确保（针对某些浏览器的延迟渲染）
                    setTimeout(function() {
                        window.scrollTo(0, targetY);
                    }, 10);
                }
            }
        }

        // 监听滚动事件（防抖）
        let scrollTimeout;
        window.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(saveScroll, 50);
        });

        // 页面卸载前保存（确保不丢失）
        window.addEventListener('beforeunload', saveScroll);

        // 页面可见性变化时保存（防止切换标签页时丢失）
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                saveScroll();
            }
        });

        // 页面加载时恢复（使用多重时机确保执行）
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', restoreScroll);
        }
        window.addEventListener('load', restoreScroll);
        // 最后的保险：使用 requestAnimationFrame
        requestAnimationFrame(restoreScroll);
    })();
    </script>'''
            html = self._inject_interactive_html(html, scroll_restore)

            # 切换显示：隐藏 canvas，显示 Word 预览
            self.canvas_container.hide()
            self.word_preview.show()

            # 设置 WebChannel（仅首次）
            if not hasattr(self, 'bridge') or self.bridge is None:
                channel = QWebChannel(self)
                self.bridge = WebViewBridge(self, self)
                channel.registerObject("pyBridge", self.bridge)
                self.word_preview.page().setWebChannel(channel)

            # 在重新渲染前保存当前滚动位置
            if hasattr(self, 'word_preview') and self.word_preview:
                scroll_save_js = """
                (function() {
                    const scrollY = window.pageYOffset || document.documentElement?.scrollTop || document.body?.scrollTop || 0;

                    try {
                        if (typeof localStorage !== 'undefined') {
                            localStorage.setItem('word_preview_scroll_pos', scrollY.toString());
                        }
                    } catch (e) {
                        console.warn('[SaveScroll] localStorage 不可用，使用内存存储');
                        window._memoryScrollPos = scrollY;
                    }
                    console.log('[SaveScroll] 保存滚动位置:', scrollY);
                    return scrollY;
                })();
                """
                # 使用回调等待执行完成
                def on_scroll_saved(scroll_pos):
                    # 保存成功后，再更新 HTML
                    self._saved_scroll_position = scroll_pos
                    self.word_preview.setHtml(html)

                self.word_preview.page().runJavaScript(scroll_save_js, on_scroll_saved)
            else:
                # 首次加载，直接设置 HTML
                self.word_preview.setHtml(html)

        except (IOError, OSError, ValueError, RuntimeError) as e:
            QMessageBox.critical(self, "错误", f"渲染预览失败: {str(e)}")

    def _add_data_key_attributes(self, html, text_blocks):
        """使用 BeautifulSoup 为文本块添加 data-key 属性

        Args:
            html: HTML 字符串
            text_blocks: 文本块字典 {key: {'text': 原始文本, 'escaped': 转义文本}}

        Returns:
            修改后的 HTML 字符串
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 支持的标签列表（扩展）
            target_tags = ['p', 'td', 'th', 'li', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a']

            for key, info in text_blocks.items():
                original_text = info['text']
                if not original_text or not original_text.strip():
                    continue

                # 归一化文本：将多个空白字符合并为单个空格
                normalized_original = ' '.join(original_text.split())

                for tag_name in target_tags:
                    for element in soup.find_all(tag_name):
                        # 跳过已经有 data-key 的元素
                        if element.get('data-key'):
                            continue

                        # 获取元素的文本内容并归一化
                        element_text = element.get_text()
                        normalized_element = ' '.join(element_text.split())

                        # 比较归一化后的文本
                        if normalized_original == normalized_element:
                            element['data-key'] = key
                            element['data-original-text'] = original_text
                            break

            return str(soup)

        except (ImportError, AttributeError, TypeError, ValueError) as e:
            print(f"[警告] BeautifulSoup 处理失败，使用正则表达式后备方案: {e}")
            return self._add_data_key_regex_fallback(html, text_blocks)

    def _add_data_key_regex_fallback(self, html, text_blocks):
        """使用正则表达式为文本块添加 data-key 属性（后备方案）

        Args:
            html: HTML 字符串
            text_blocks: 文本块字典

        Returns:
            修改后的 HTML 字符串
        """
        from html import escape as html_escape

        for key, info in text_blocks.items():
            original_text = info['text']
            escaped_text = html_escape(original_text)

            # 尝试各种 HTML 标签
            patterns = [
                (f'<p([^>]*)>({re.escape(escaped_text)})</p>', f'<p\\1 data-key="{key}">\\2</p>'),
                (f'<td([^>]*)>({re.escape(escaped_text)})</td>', f'<td\\1 data-key="{key}">\\2</td>'),
                (f'<li([^>]*)>({re.escape(escaped_text)})</li>', f'<li\\1 data-key="{key}">\\2</li>'),
                (f'<span([^>]*)>({re.escape(escaped_text)})</span>', f'<span\\1 data-key="{key}">\\2</span>'),
                (f'<div([^>]*)>({re.escape(escaped_text)})</div>', f'<div\\1 data-key="{key}">\\2</div>'),
            ]

            for pattern, replacement in patterns:
                if f'data-key="{key}"' not in html:
                    if re.search(pattern, html):
                        html = re.sub(pattern, replacement, html, count=1)
                        break

        return html

    def _highlight_exact_match(self, html, match):
        """使用 BeautifulSoup 精确高亮指定位置的文本

        Args:
            html: HTML 字符串
            match: 包含 key, start, end, text 的匹配信息

        Returns:
            修改后的 HTML 字符串
        """
        from bs4 import BeautifulSoup, NavigableString

        key = match['key']
        start = match['start']
        end = match['end']
        text = match['text']

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 找到对应的容器元素
            container = soup.find(attrs={'data-key': key})
            if not container:
                print(f"[警告] 未找到 data-key={key} 的元素")
                return html

            # 遍历所有文本节点，找到对应位置
            current_pos = 0
            for child in list(container.descendants):
                if isinstance(child, NavigableString) and not isinstance(child, str):
                    continue
                if isinstance(child, str):
                    node_text = str(child)
                    node_start = current_pos
                    node_end = current_pos + len(node_text)

                    # 检查目标范围是否在这个节点内
                    if start >= node_start and end <= node_end:
                        # 计算在当前节点内的相对位置
                        rel_start = start - node_start
                        rel_end = end - node_start

                        # 分割文本并插入 mark 标签
                        before = node_text[:rel_start]
                        highlighted = node_text[rel_start:rel_end]
                        after = node_text[rel_end:]

                        # 创建新的标记
                        mark_tag = soup.new_tag('mark')
                        mark_tag['class'] = 'manual-highlight'
                        mark_tag['data-key'] = key
                        mark_tag['data-start'] = start
                        mark_tag['data-end'] = end
                        mark_tag['style'] = 'background-color: #ff6b6b; color: #fff; display: inline; cursor: pointer; box-shadow: 0 0 0 1px #e03131; box-decoration-break: clone; -webkit-box-decoration-break: clone;'
                        mark_tag.string = highlighted

                        # 替换原文本节点
                        parent = child.parent
                        # 创建新的节点序列
                        new_nodes = []
                        if before:
                            new_nodes.append(NavigableString(before))
                        new_nodes.append(mark_tag)
                        if after:
                            new_nodes.append(NavigableString(after))

                        # 替换原节点
                        child.replace_with(*new_nodes)

                        return str(soup)

                    current_pos = node_end

            print(f"[警告] 精确模式未找到位置: key={key}, start={start}, end={end}")
            return html

        except (ImportError, AttributeError, TypeError, ValueError, IndexError) as e:
            print(f"[错误] 精确高亮失败: {e}")
            return html

    def _highlight_sensitive_info(self, html):
        """在 HTML 中高亮显示敏感信息（使用 JavaScript 进行高亮）"""
        import json
        from html import escape
        import re

        # 构建所有匹配数据的 JSON
        matches_data = []
        # 构建文本块数据（用于标记段落/单元格）
        text_blocks = {}

        for key, data in self.word_data.items():
            text = data['text']
            if not text:
                continue

            # 记录文本块信息
            text_blocks[key] = {
                'text': text,
                'escaped': escape(text)
            }

            # OCR 匹配
            for match in data['ocr']:
                matches_data.append({
                    'key': key,
                    'start': match['start'],
                    'end': match['end'],
                    'text': match['text'],
                    'type': 'ocr',
                    'rule_name': match.get('rule_name', 'OCR')
                })

            # 手动脱敏
            for match in data['manual']:
                matches_data.append({
                    'key': key,
                    'start': match['start'],
                    'end': match['end'],
                    'text': match['text'],
                    'type': 'manual',
                    'mode': match.get('mode', 'exact')  # 添加模式标识，默认为 exact
                })

        # === 新方法：直接在 HTML 字符串中进行高亮替换 ===
        from html import escape as html_escape

        # 按文本长度降序排序，先处理长的匹配
        matches_data.sort(key=lambda x: len(x['text']), reverse=True)

        # 分离精确模式和全局模式
        exact_matches = [m for m in matches_data if m.get('mode') == 'exact']
        global_matches = [m for m in matches_data if m.get('mode') != 'exact']

        # === 第一步：为所有文本块添加 data-key 属性（使用 BeautifulSoup 替代正则表达式）===
        html = self._add_data_key_attributes(html, text_blocks)

        # 处理全局模式匹配（OCR 和全局手动脱敏）
        # 去重：相同文本只处理一次
        processed_global_texts = set()
        for match in global_matches:
            text = match['text']
            if text in processed_global_texts:
                continue
            processed_global_texts.add(text)

            # 需要转义 HTML 特殊字符
            escaped_text = html_escape(text)
            is_ocr = match['type'] == 'ocr'

            # 构建替换标记
            if is_ocr:
                replacement = f'<mark class="ocr-highlight" data-key="{match["key"]}" data-start="{match["start"]}" data-end="{match["end"]}" title="{match.get("rule_name", "")}" style="background-color: #ffeb3b; color: #000; display: inline; box-decoration-break: clone; -webkit-box-decoration-break: clone;">{escaped_text}</mark>'
            else:
                replacement = f'<mark class="manual-highlight" data-key="{match["key"]}" data-start="{match["start"]}" data-end="{match["end"]}" style="background-color: #ff6b6b; color: #fff; display: inline; cursor: pointer; box-shadow: 0 0 0 1px #e03131; box-decoration-break: clone; -webkit-box-decoration-break: clone;">{escaped_text}</mark>'

            # 使用正则表达式替换所有匹配
            # 使用正向预查避免匹配已经在标记中的文本
            pattern = re.compile(re.escape(escaped_text) + r'(?![^<]*>)')
            html = pattern.sub(replacement, html)

        # 处理精确模式匹配（只高亮特定位置的文本）
        # 使用 BeautifulSoup 进行精确位置定位
        for match in exact_matches:
            html = self._highlight_exact_match(html, match)

        # 为了兼容性，仍然生成 matches_json（但不再用于高亮）
        matches_json = json.dumps(matches_data, ensure_ascii=False)
        text_blocks_json = json.dumps(text_blocks, ensure_ascii=False)

        # 添加简化版的 JavaScript 高亮脚本（仅用于调试）
        highlight_script = '''
        <script>
        (function() {
            console.log('[Highlight] HTML 预高亮已完成');
            // 高亮已在 Python 端完成，这里不需要再做
        })();
        </script>
        '''

        # 添加样式
        style = """
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 20px; line-height: 1.6; }
            mark.ocr-highlight { background-color: #ffeb3b; color: #000; display: inline; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
            mark.manual-highlight { background-color: #ff6b6b; color: #fff; display: inline; cursor: pointer; box-shadow: 0 0 0 1px #e03131; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
            mark.manual-highlight:hover { box-shadow: 0 0 0 1px #e03131, 0 0 4px rgba(225, 49, 49, 0.5); }
            table { border-collapse: collapse; width: 100%; margin: 10px 0; }
            td, th { border: 1px solid #ddd; padding: 8px; }
        </style>
        """

        # 插入样式和脚本
        if '<head>' in html:
            html = html.replace('<head>', '<head>' + style, 1)
        else:
            html = style + html

        # 在 </body> 前插入脚本，或者直接追加到末尾
        if '</body>' in html:
            html = html.replace('</body>', highlight_script + '</body>', 1)
        else:
            html = html + highlight_script

        return html

    def _inject_interactive_html(self, html, scroll_restore=''):
        """注入 JavaScript 交互逻辑用于右键菜单和脱敏操作

        v36.4: 重构为使用模块级常量 _INTERACTIVE_JS_CODE，简化函数逻辑

        Args:
            html: 要注入的 HTML
            scroll_restore: 滚动恢复脚本（可选）
        """
        # 包装 HTML 为完整文档（如果不是的话）
        html = self._wrap_html_document(html)

        # 注入脚本
        qwebchannel_js = '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'

        if '</head>' in html:
            html = html.replace('</head>', qwebchannel_js + _INTERACTIVE_JS_CODE + scroll_restore + '</head>')
        else:
            html = qwebchannel_js + _INTERACTIVE_JS_CODE + scroll_restore + html

        return html

    def _wrap_html_document(self, html):
        """将 HTML 包装成完整文档（如果不是完整文档的话）

        Args:
            html: 输入的 HTML 字符串

        Returns:
            完整的 HTML 文档字符串
        """
        is_full_document = '<html' in html.lower() or '<!doctype' in html.lower()

        if is_full_document:
            return html

        return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body {{ margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; }}
    img {{ max-width: 100%; height: auto; }}
    p {{ margin: 0 0 10px 0; }}
</style>
</head>
<body>
{html}
</body>
</html>'''

    def save_pdf(self):
        """保存脱敏后的文档 - 支持 PDF 和 Word"""
        # v36: 应用文件对话框样式
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
                doc_save = None
                try:
                    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    doc_save = fitz.open(self.file_path)
                    fill_col = (0, 0, 0) if self.current_color.name() == "#000000" else (1, 1, 1)
                    for i in range(len(doc_save)):
                        page = doc_save[i]
                        data = self.page_data[i]
                        for r in data['ocr'] + data['manual']:
                            rect = fitz.Rect(r.x(), r.y(), r.x()+r.width(), r.y()+r.height())
                            annot = page.add_redact_annot(rect)
                            annot.set_colors(stroke=fill_col, fill=fill_col)
                            annot.update()
                        # 使用保守方式：只涂抹，不删除图像
                        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                    doc_save.save(fname)
                    QApplication.restoreOverrideCursor()
                    QMessageBox.information(self, "成功", f"文件已保存至：\n{fname}")
                except (IOError, OSError, ValueError, RuntimeError) as e:
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

            # 遍历段落进行 run 级别的文本替换
            for para_idx, para in enumerate(new_doc.paragraphs):
                key = f'paragraph_{para_idx}'
                if key in self.word_data:
                    # 合并 OCR + Manual 脱敏
                    all_matches = []
                    all_matches.extend(self.word_data[key]['ocr'])
                    all_matches.extend(self.word_data[key]['manual'])

                    if all_matches:
                        self._replace_in_paragraph(para, all_matches)

            # 遍历表格进行 run 级别的文本替换
            for table_idx, table in enumerate(new_doc.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        key = f'table_{table_idx}_cell_{row_idx}_{cell_idx}'
                        if key in self.word_data:
                            # 合并 OCR + Manual 脱敏
                            all_matches = []
                            all_matches.extend(self.word_data[key]['ocr'])
                            all_matches.extend(self.word_data[key]['manual'])

                            if all_matches:
                                # 处理单元格内的所有段落
                                for para in cell.paragraphs:
                                    self._replace_in_paragraph(para, all_matches)

            # 保存文档
            new_doc.save(fname)

            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "成功", f"文件已保存至：\n{fname}")

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

        except (OSError, IOError, RuntimeError, ValueError, KeyError, AttributeError) as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self, "保存失败",
                f"保存 Word 文档时出错：\n{str(e)}\n\n"
                "请尝试：\n"
                "1. 重启应用\n"
                "2. 在 Word 中手动打开文件\n"
                "3. 导出错误日志以供分析"
            )

    def _replace_in_paragraph(self, para, matches):
        """在段落中进行文本替换，保持原有格式

        策略：遍历每个 run，如果 run 中包含敏感文本，则替换并保持格式
        """
        if not matches or not para.runs:
            return

        # 为每个匹配项建立替换映射
        replacements = {}
        for match in matches:
            replacements[match['text']] = match['replacement']

        # 遍历每个 run 进行替换
        for run in para.runs:
            original_text = run.text
            if not original_text:
                continue

            new_text = original_text
            for old_text, replacement in replacements.items():
                if old_text in new_text:
                    new_text = new_text.replace(old_text, replacement)

            # 只有文本变化时才更新
            if new_text != original_text:
                run.text = new_text

    def _copy_run_format(self, target_run, source_run):
        """复制 run 的所有格式属性

        Args:
            target_run: 目标 run
            source_run: 源 run
        """
        # 字体属性
        if source_run.bold is not None:
            target_run.bold = source_run.bold
        if source_run.italic is not None:
            target_run.italic = source_run.italic
        if source_run.underline is not None:
            target_run.underline = source_run.underline
        if source_run.strike is not None:
            target_run.strike = source_run.strike

        # 字体名称和大小
        if source_run.font.name:
            try:
                target_run.font.name = source_run.font.name
            except (AttributeError, TypeError) as e:
                print(f"[字体复制] 复制字体名称失败: {e}")
        if source_run.font.size:
            target_run.font.size = source_run.font.size

        # 颜色
        if source_run.font.color and source_run.font.color.rgb:
            try:
                target_run.font.color.rgb = source_run.font.color.rgb
            except (AttributeError, TypeError) as e:
                print(f"[字体复制] 复制字体颜色失败: {e}")

        # 高亮
        if source_run.font.highlight_color:
            try:
                target_run.font.highlight_color = source_run.font.highlight_color
            except (AttributeError, TypeError) as e:
                print(f"[字体复制] 复制高亮颜色失败: {e}")

        # 下标/上标
        if source_run.font.subscript:
            target_run.font.subscript = True
        if source_run.font.superscript:
            target_run.font.superscript = True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())