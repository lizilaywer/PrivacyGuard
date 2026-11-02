"""文档加密设置弹框（从 main.py 提取）。

cp72: 单弹框双密码（打开密码 + 编辑密码），加密在导出时写入。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QCheckBox, QPushButton,
)
from PyQt6.QtCore import Qt


class EncryptSettingsDialog(QDialog):
    """cp72: 文档加密设置弹框（单弹框双密码）。

    - 打开密码（user）：打开 PDF 时需输入；留空=打开无需密码
    - 编辑密码（owner）：限制他人编辑/复制/注释；留空=不限制权限
    加密在下次"导出"时随 PyMuPDF save 写入。
    """

    def __init__(self, parent=None, open_pw="", edit_pw=""):
        super().__init__(parent)
        self.setWindowTitle("文档加密")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(460)
        self._apply_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        lead = QLabel("为当前文档设置密码，加密将在点击“导出”保存时生效。两个密码均可留空。")
        lead.setWordWrap(True)
        layout.addWidget(lead)

        # 打开密码
        open_row = QHBoxLayout()
        open_row.setSpacing(8)
        open_row.addWidget(self._make_label("打开密码:", 88))
        self.input_open = QLineEdit(open_pw or "")
        self.input_open.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_open.setPlaceholderText("打开 PDF 时需输入（留空则无需）")
        open_row.addWidget(self.input_open)
        layout.addLayout(open_row)

        # 编辑密码
        edit_row = QHBoxLayout()
        edit_row.setSpacing(8)
        edit_row.addWidget(self._make_label("编辑密码:", 88))
        self.input_edit = QLineEdit(edit_pw or "")
        self.input_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_edit.setPlaceholderText("限制编辑/复制/注释（留空则不限制）")
        edit_row.addWidget(self.input_edit)
        layout.addLayout(edit_row)

        # 显示密码开关
        self.cb_show = QCheckBox("显示密码")
        self.cb_show.stateChanged.connect(self._toggle_echo)
        layout.addWidget(self.cb_show)

        hint = QLabel("说明：只设编辑密码时，任何人可打开但编辑/复制/注释受限（仍可打印）。"
                      "密码不会被保存，仅当前会话有效。")
        hint.setWordWrap(True)
        hint.setObjectName("encryptHint")
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("encryptCancel")
        btn_cancel.setMinimumHeight(34)
        btn_cancel.setMinimumWidth(96)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton("确定")
        btn_ok.setObjectName("encryptOk")
        btn_ok.setDefault(True)
        btn_ok.setMinimumHeight(34)
        btn_ok.setMinimumWidth(116)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _make_label(self, text, width):
        lbl = QLabel(text)
        lbl.setFixedWidth(width)
        return lbl

    def _toggle_echo(self):
        mode = QLineEdit.EchoMode.Normal if self.cb_show.isChecked() else QLineEdit.EchoMode.Password
        self.input_open.setEchoMode(mode)
        self.input_edit.setEchoMode(mode)

    def _apply_theme(self):
        from theme import Theme
        theme = Theme.LIGHT
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme["background"]}; }}
            QLabel {{ color: {theme["text"]}; background: transparent; }}
            QLabel#encryptHint {{ color: {theme["text_secondary"]}; font-size: 11px; }}
            QLineEdit {{
                background-color: #FFFFFF; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px;
            }}
            QCheckBox {{ color: {theme["text"]}; }}
            QPushButton {{ outline: none; }}
            QPushButton#encryptOk {{
                background-color: {theme["primary"]}; color: white; border: none;
                border-radius: 6px; padding: 6px 18px; font-weight: 600;
            }}
            QPushButton#encryptOk:hover {{ background-color: #0A84FF; }}
            QPushButton#encryptCancel {{
                background-color: #F2F2F7; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px 18px;
            }}
        """)

    @property
    def open_password(self):
        return self.input_open.text().strip()

    @property
    def edit_password(self):
        return self.input_edit.text().strip()
