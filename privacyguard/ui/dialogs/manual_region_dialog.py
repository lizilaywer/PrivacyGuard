"""手动框选脱敏弹窗（从 main.py 提取）。

cp65: 识别文字（可编辑）+ 可选全文遮罩 + 替换文本。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QCheckBox, QLineEdit, QApplication,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6 import sip  # cp118: QTimer 回调守卫，防 modal 关闭后访问已删除控件


class ManualRegionRedactDialog(QDialog):
    """cp65: 手动框选脱敏弹窗：识别文字（可编辑）+ 可选全文遮罩 + 替换文本。

    开关"手动框选时输入替换文本"勾选时弹出：
    - 上方：OCR/文字层识别出的框选区域文字，可编辑修改
    - 右侧复选框（默认不勾选）：根据已识别的文字查找全文并遮罩
    - 下方：替换文本（与原有逻辑一致，留空=纯遮罩；若勾选全文遮罩，
      所有被遮罩区域同样叠加该文本）
    """

    def __init__(self, parent=None, recognized_text="", disable_search_all=False):
        """cp128: disable_search_all=True 时禁用并隐藏"全文遮罩"复选框（提取模式下用）。"""
        super().__init__(parent)
        self.setWindowTitle("手动框选脱敏")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(480)
        # cp65: 用户点"纯遮罩"按钮时置 True，调用方据此跳过全文遮罩并强制空替换文本
        self.pure_mask_only = False
        self._apply_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        lbl_text = QLabel("识别到的文字（可编辑修改）:")
        layout.addWidget(lbl_text)
        self.txt_recognized = QPlainTextEdit()
        self.txt_recognized.setPlainText(recognized_text or "")
        self.txt_recognized.setPlaceholderText("未识别到文字，可手动输入用于全文查找")
        self.txt_recognized.setMinimumHeight(84)
        self.txt_recognized.setMaximumHeight(150)
        layout.addWidget(self.txt_recognized)

        # cp74: 识别文字框下方小工具：去空白 / 复制
        text_tools_row = QHBoxLayout()
        text_tools_row.setSpacing(8)
        self.btn_strip_blank = QPushButton("去空白")
        self.btn_strip_blank.setObjectName("manualRegionMiniBtn")
        self.btn_strip_blank.setToolTip("去除识别文字中的所有空白（空格/制表符/换行）")
        self.btn_strip_blank.clicked.connect(self._strip_whitespace)
        text_tools_row.addWidget(self.btn_strip_blank)
        self.btn_copy_text = QPushButton("复制")
        self.btn_copy_text.setObjectName("manualRegionMiniBtn")
        self.btn_copy_text.setToolTip("复制识别框里的全部文字")
        self.btn_copy_text.clicked.connect(self._copy_text)
        text_tools_row.addWidget(self.btn_copy_text)
        self.btn_clear_text = QPushButton("清空")
        self.btn_clear_text.setObjectName("manualRegionMiniBtn")
        self.btn_clear_text.setToolTip("清空识别框里的全部文字")
        self.btn_clear_text.clicked.connect(self._clear_text)
        text_tools_row.addWidget(self.btn_clear_text)
        text_tools_row.addStretch()
        layout.addLayout(text_tools_row)

        search_row = QHBoxLayout()
        search_row.addStretch()
        self.cb_search_all = QCheckBox("根据已识别的文字查找全文并遮罩")
        self.cb_search_all.setChecked(False)
        # cp128: 提取模式下禁用全文遮罩（避免对原文档搜索造成逻辑混乱）
        if disable_search_all:
            self.cb_search_all.setEnabled(False)
            self.cb_search_all.setToolTip("提取模式下不可用（全文遮罩作用于原文档）")
        search_row.addWidget(self.cb_search_all)
        layout.addLayout(search_row)
        if disable_search_all:
            # 隐藏全文遮罩相关提示（提取模式下不显示）
            pass
        else:
            search_hint = QLabel(
                "勾选后：按上方文字（以你编辑后的为准）在整个 PDF 查找并遮罩所有出现位置；"
                "扫描件会自动逐页 OCR，耗时与智能扫描相当。"
            )
            search_hint.setWordWrap(True)
            search_hint.setObjectName("manualRegionHint")
            layout.addWidget(search_hint)

        replace_row = QHBoxLayout()
        replace_row.setSpacing(8)
        lbl_replace = QLabel("替换文本:")
        replace_row.addWidget(lbl_replace)
        self.input_replace = QLineEdit()
        self.input_replace.setPlaceholderText("输入遮罩后叠加的替换文本（留空=纯遮罩）")
        replace_row.addWidget(self.input_replace)
        layout.addLayout(replace_row)
        replace_hint = QLabel("若勾选了全文遮罩，所有被遮罩的区域都会叠加这个替换文本。")
        replace_hint.setWordWrap(True)
        replace_hint.setObjectName("manualRegionHint")
        layout.addWidget(replace_hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        # cp65: 最左端"纯遮罩"按钮——即便弹窗已开启，本次也只做纯遮罩
        # （清空替换文本 + 关闭全文遮罩 + 置标志后 accept）
        self.btn_pure_mask = QPushButton("纯遮罩")
        self.btn_pure_mask.setObjectName("manualRegionPureMask")
        self.btn_pure_mask.setToolTip("本次只遮罩框选区域，不叠加替换文本、不做全文遮罩")
        self.btn_pure_mask.setMinimumHeight(34)
        self.btn_pure_mask.setMinimumWidth(96)
        self.btn_pure_mask.clicked.connect(self._accept_pure_mask)
        btn_row.addWidget(self.btn_pure_mask)
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("manualRegionCancel")
        btn_cancel.setMinimumHeight(34)
        btn_cancel.setMinimumWidth(96)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton("确定")
        btn_ok.setObjectName("manualRegionOk")
        btn_ok.setDefault(True)
        btn_ok.setMinimumHeight(34)
        btn_ok.setMinimumWidth(116)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _apply_theme(self):
        """浅色主题，与其他对话框一致（防 Windows 深色模式发黑）。"""
        from theme import Theme
        theme = Theme.LIGHT
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme["background"]}; }}
            QLabel {{ color: {theme["text"]}; background: transparent; }}
            QLabel#manualRegionHint {{ color: {theme["text_secondary"]}; font-size: 11px; }}
            QPlainTextEdit, QLineEdit {{
                background-color: #FFFFFF; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px;
            }}
            QCheckBox {{ color: {theme["text"]}; }}
            QPushButton {{ outline: none; }}
            QPushButton#manualRegionOk {{
                background-color: {theme["primary"]}; color: white; border: none;
                border-radius: 6px; padding: 6px 18px; font-weight: 600;
            }}
            QPushButton#manualRegionOk:hover {{ background-color: #0A84FF; }}
            QPushButton#manualRegionCancel {{
                background-color: #F2F2F7; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px 18px;
            }}
            QPushButton#manualRegionPureMask {{
                background-color: #FFFFFF; color: {theme["text"]};
                border: 1px solid #C7C7CC; border-radius: 6px; padding: 6px 18px;
            }}
            QPushButton#manualRegionPureMask:hover {{ background-color: #F2F2F7; }}
            QPushButton#manualRegionMiniBtn {{
                background-color: #F2F2F7; color: {theme["text"]};
                border: 1px solid #D1D1D6; border-radius: 5px; padding: 3px 12px;
                font-size: 12px;
            }}
            QPushButton#manualRegionMiniBtn:hover {{ background-color: #E5E5EA; }}
        """)

    def _strip_whitespace(self):
        """cp74: 去除识别文字中的所有空白（空格/制表符/换行等）。"""
        import re as _re
        text = self.txt_recognized.toPlainText()
        cleaned = _re.sub(r"\s+", "", text)
        self.txt_recognized.setPlainText(cleaned)

    def _copy_text(self):
        """cp74: 复制识别框里的全部文字到剪贴板。"""
        text = self.txt_recognized.toPlainText()
        QApplication.clipboard().setText(text)
        self.btn_copy_text.setText("已复制")
        # cp118: QTimer 回调加 sip 守卫——modal 对话框在 1200ms 内关闭时，
        # btn_copy_text 的 C++ 对象可能已被销毁，直接访问会抛 RuntimeError（被 excepthook 捕获）
        def _restore_text():
            try:
                if sip.isdeleted(self.btn_copy_text):
                    return
            except Exception:
                return
            self.btn_copy_text.setText("复制")
        QTimer.singleShot(1200, _restore_text)

    def _clear_text(self):
        """清空识别框里的全部文字。"""
        self.txt_recognized.clear()

    def _accept_pure_mask(self):
        """cp65: 点"纯遮罩"按钮——接受对话框，但强制走纯遮罩路径。

        强制：清空替换文本、取消全文遮罩、置 pure_mask_only 标志。
        调用方据此跳过全文遮罩并使用空替换文本（仅遮罩框选区域）。
        """
        self.pure_mask_only = True
        self.input_replace.clear()
        self.cb_search_all.setChecked(False)
        self.accept()

    @property
    def recognized_text(self):
        return self.txt_recognized.toPlainText().strip()

    @property
    def search_whole_doc(self):
        return self.cb_search_all.isChecked()

    @property
    def replacement_text(self):
        return self.input_replace.text().strip()
