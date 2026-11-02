# -*- coding: utf-8 -*-
"""打开加密文档时的密码输入对话框。

cp113: 用于打开受密码保护的 PDF / Word 文档。
- 密码输入框（EchoMode.Password）+ 显示密码复选框
- 三动作按钮：打开 / 打开并解除密码 / 打开并修改密码
- Word"修改密码"按钮禁用（python-docx 不支持加密保存）+ tooltip 说明
- 复用 EncryptSettingsDialog 的主题风格，保持视觉一致

返回约定（调用方读取）：
- 用户点任一动作按钮 → accept()，调用方读 password + action
- 用户点取消/关闭 → reject()，调用方视为放弃（action=""）
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QCheckBox, QPushButton,
)
from PyQt6.QtCore import Qt


class PasswordOpenDialog(QDialog):
    """cp113: 打开加密文档时输入密码 + 选择动作。

    Args:
        parent: 父窗口
        file_name: 待打开的文件名（仅用于展示）
        file_type: "pdf" 或 "word"，决定"修改密码"按钮是否可用
    """

    def __init__(self, parent=None, file_name="", file_type="pdf"):
        super().__init__(parent)
        self.setWindowTitle("输入密码")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(480)
        self._action = ""  # "open" / "remove" / "change" / ""（取消）
        self._file_type = file_type if file_type in ("pdf", "word") else "pdf"
        self._apply_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # 顶部提示
        type_label = "PDF" if self._file_type == "pdf" else "Word"
        lead = QLabel(f"{type_label} 文档「{file_name}」受密码保护，请输入密码。")
        lead.setWordWrap(True)
        layout.addWidget(lead)

        # 密码输入行
        pw_row = QHBoxLayout()
        pw_row.setSpacing(8)
        lbl = QLabel("密码:")
        lbl.setFixedWidth(56)
        pw_row.addWidget(lbl)
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setPlaceholderText("请输入打开密码")
        self.input_password.returnPressed.connect(self._trigger_open)
        pw_row.addWidget(self.input_password)
        layout.addLayout(pw_row)

        # 显示密码开关
        self.cb_show = QCheckBox("显示密码")
        self.cb_show.stateChanged.connect(self._toggle_echo)
        layout.addWidget(self.cb_show)

        # 说明文案
        if self._file_type == "word":
            hint_text = (
                "说明：Word 文档仅支持打开与解除密码，不支持修改密码"
                "（python-docx 无法加密保存）。导出时默认不带回密码。"
            )
        else:
            hint_text = (
                "说明：「打开」保留原密码（导出时用同密码加密）；"
                "「打开并解除密码」导出不加密；"
                "「打开并修改密码」可设置新密码（导出时用新密码）。"
            )
        hint = QLabel(hint_text)
        hint.setWordWrap(True)
        hint.setObjectName("pwOpenHint")
        layout.addWidget(hint)

        # 动作按钮区
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("pwOpenCancel")
        btn_cancel.setMinimumHeight(34)
        btn_cancel.setMinimumWidth(80)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()

        btn_change = QPushButton("打开并修改密码")
        btn_change.setObjectName("pwOpenChange")
        btn_change.setMinimumHeight(34)
        btn_change.setMinimumWidth(130)
        if self._file_type == "word":
            btn_change.setEnabled(False)
            btn_change.setToolTip("Word 不支持修改密码（python-docx 无法加密保存）")
        btn_change.clicked.connect(lambda: self._accept_with_action("change"))
        btn_row.addWidget(btn_change)

        btn_remove = QPushButton("打开并解除密码")
        btn_remove.setObjectName("pwOpenRemove")
        btn_remove.setMinimumHeight(34)
        btn_remove.setMinimumWidth(120)
        btn_remove.clicked.connect(lambda: self._accept_with_action("remove"))
        btn_row.addWidget(btn_remove)

        btn_open = QPushButton("打开")
        btn_open.setObjectName("pwOpenOk")
        btn_open.setDefault(True)
        btn_open.setMinimumHeight(34)
        btn_open.setMinimumWidth(96)
        btn_open.clicked.connect(lambda: self._accept_with_action("open"))
        btn_row.addWidget(btn_open)
        layout.addLayout(btn_row)

    def _accept_with_action(self, action):
        """点击动作按钮：记录 action 并 accept。"""
        self._action = action
        self.accept()

    def _trigger_open(self):
        """回车键触发默认"打开"动作。"""
        self._accept_with_action("open")

    def _toggle_echo(self):
        mode = QLineEdit.EchoMode.Normal if self.cb_show.isChecked() else QLineEdit.EchoMode.Password
        self.input_password.setEchoMode(mode)

    def _apply_theme(self):
        from theme import Theme
        theme = Theme.LIGHT
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme["background"]}; }}
            QLabel {{ color: {theme["text"]}; background: transparent; }}
            QLabel#pwOpenHint {{ color: {theme["text_secondary"]}; font-size: 11px; }}
            QLineEdit {{
                background-color: #FFFFFF; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px;
            }}
            QCheckBox {{ color: {theme["text"]}; }}
            QPushButton {{ outline: none; }}
            QPushButton#pwOpenOk {{
                background-color: {theme["primary"]}; color: white; border: none;
                border-radius: 6px; padding: 6px 18px; font-weight: 600;
            }}
            QPushButton#pwOpenOk:hover {{ background-color: #0A84FF; }}
            QPushButton#pwOpenRemove {{
                background-color: #FFFFFF; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px 14px;
            }}
            QPushButton#pwOpenRemove:hover {{ background-color: #F2F2F7; }}
            QPushButton#pwOpenChange {{
                background-color: #FFFFFF; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px 14px;
            }}
            QPushButton#pwOpenChange:hover {{ background-color: #F2F2F7; }}
            QPushButton#pwOpenChange:disabled {{
                color: #C7C7CC; border: 1px solid #E5E5EA;
            }}
            QPushButton#pwOpenCancel {{
                background-color: #F2F2F7; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px 14px;
            }}
        """)

    @property
    def password(self):
        return self.input_password.text().strip()

    @property
    def action(self):
        return self._action
