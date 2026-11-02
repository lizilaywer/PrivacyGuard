"""开发者信息与反馈对话框"""
import os
import webbrowser

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QTextBrowser, QMessageBox, QApplication,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from theme import Theme
from privacyguard.utils.security import resource_path
from privacyguard import __version__ as VERSION, __app_name__ as APP_NAME

from privacyguard.ui.dialogs.donate_dialog import DonateDialog

# 默认反馈链接（config 不可用时的后备）
_DEFAULT_FEEDBACK_URL = "https://fcnwakmkeuz7.feishu.cn/share/base/form/shrcnEM1JEbdIKzdB400egj9lHe"


class FeedbackDialog(QDialog):
    """开发者信息与反馈对话框"""
    def __init__(self, parent=None, config=None):
        super().__init__(parent)

        # v37.4.1: 修复 Windows 深色模式下对话框显示问题
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        self.setWindowTitle("关于与反馈")
        # v37.0: 从配置读取窗口尺寸
        if config:
            dialog_width = config.get("app.window.dialog_feedback_width", 480)
            dialog_height = config.get("app.window.dialog_feedback_height", 600)
        else:
            dialog_width, dialog_height = 480, 600
        self.resize(dialog_width, dialog_height)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # 反馈链接
        self._feedback_url = (
            config.get("app.feedback_url", _DEFAULT_FEEDBACK_URL) if config
            else _DEFAULT_FEEDBACK_URL
        )

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

        # 微信公众号行
        wx_account = "池州有个汪律师"
        row1 = QHBoxLayout()
        wx_label = QLabel("微信公众号:")
        wx_label.setStyleSheet(f"color: {self.theme['text_secondary']};")
        row1.addWidget(wx_label)

        wx_account_label = QLabel(wx_account)
        wx_account_label.setStyleSheet(f"color: {self.theme['text']}; font-weight: 500;")
        wx_account_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row1.addWidget(wx_account_label)
        row1.addStretch()

        wx_qr_btn = QPushButton("扫码关注")
        wx_qr_btn.setFixedSize(70, 24)
        wx_qr_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['primary']};
                border: none;
                border-radius: 4px;
                font-size: 11px;
                color: white;
            }}
            QPushButton:hover {{
                background: #0056CC;
            }}
        """)
        wx_qr_btn.clicked.connect(self._show_wx_qrcode)
        row1.addWidget(wx_qr_btn)
        social_layout.addLayout(row1)

        # 其他平台行
        row2 = QHBoxLayout()
        platforms_label = QLabel("抖音/小红书/B站（同号）:")
        platforms_label.setStyleSheet(f"color: {self.theme['text_secondary']};")
        row2.addWidget(platforms_label)

        other_account = "池州有个汪律师"
        other_label = QLabel(other_account)
        other_label.setStyleSheet(f"color: {self.theme['text']}; font-weight: 500;")
        other_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row2.addWidget(other_label)
        row2.addStretch()

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
        copy_btn.clicked.connect(lambda checked, a=other_account: self._copy_to_clipboard(a))
        row2.addWidget(copy_btn)
        social_layout.addLayout(row2)

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

    def _show_wx_qrcode(self):
        """显示微信公众号二维码对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("关注微信公众号")
        dialog.setFixedSize(400, 480)
        dialog.setStyleSheet(f"""
            QDialog {{
                background: {self.theme['background']}
            }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        title = QLabel("扫码关注微信公众号")
        title.setStyleSheet(f"""
            color: {self.theme['text']};
            font-size: 16px;
            font-weight: bold;
            padding: 10px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 公众号名称
        name_label = QLabel("池州有个汪律师")
        name_label.setStyleSheet(f"""
            color: {self.theme['primary']};
            font-size: 18px;
            font-weight: bold;
            padding: 5px;
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # 二维码图片
        qr_path = resource_path(os.path.join("assets", "wx_qrcode.png"))
        if os.path.exists(qr_path):
            qr_label = QLabel()
            pixmap = QPixmap(qr_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                qr_label.setPixmap(scaled_pixmap)
                qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(qr_label)
            else:
                qr_label.setText("二维码加载失败")
                qr_label.setStyleSheet(f"color: {self.theme['text']};")
                layout.addWidget(qr_label)
        else:
            qr_label = QLabel("请添加微信公众号二维码图片至\nassets/wx_qrcode.png")
            qr_label.setStyleSheet(f"color: {self.theme['text']};")
            qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(qr_label)

        # 提示文字
        hint = QLabel("微信扫一扫，关注公众号获取更多AI工具")
        hint.setStyleSheet(f"""
            color: {self.theme['text_secondary']};
            font-size: 12px;
            padding: 10px;
        """)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(100, 32)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: #0056CC;
            }}
        """)
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()

    def _open_feedback(self):
        """打开反馈问卷链接"""
        webbrowser.open(self._feedback_url)

    def _open_manual(self):
        """打开使用手册链接"""
        webbrowser.open("https://fcnwakmkeuz7.feishu.cn/docx/M9ojdaGUAoRVv7x3NCAcxkxenUe?from=from_copylink")

    def _show_donate(self):
        """显示打赏二维码对话框"""
        dialog = DonateDialog(self)
        dialog.exec()
