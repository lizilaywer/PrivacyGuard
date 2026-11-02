"""打赏二维码对话框"""
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from theme import Theme
from privacyguard.utils.security import resource_path


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
