"""Collapsible review UI; owns no document mutations or original text."""
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox,
                             QTreeWidget, QTreeWidgetItem, QPushButton)


class RedactionReviewPanel(QWidget):
    locate = pyqtSignal(object)
    decide = pyqtSignal(object, str)
    inspect_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from privacyguard.ui.office_style import apply_office_style
        apply_office_style(self)
        self.setMinimumWidth(280)
        layout = QVBoxLayout(self)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.inspect_button = QPushButton("本页补查（可选）")
        self.inspect_button.setToolTip("补查本页小字、二维码及文字层中的银行账号和发票号码。选中候选并点确认才添加遮罩。")
        self.inspect_button.clicked.connect(self.inspect_requested)
        layout.addWidget(self.inspect_button)
        self.filter = QComboBox()
        self.filter.addItems(["全部来源", "自动识别", "手工标记", "已排除"])
        self.filter.currentIndexChanged.connect(self._filter)
        layout.addWidget(self.filter)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["位置 / 类型", "状态"])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.currentItemChanged.connect(self._update_actions)
        self.tree.itemDoubleClicked.connect(lambda item, _col: self.locate.emit(item.data(0, Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.tree)
        row = QGridLayout()
        self.action_buttons = {}
        for index, (text, action) in enumerate((("定位", "locate"), ("确认", "confirmed"), ("排除此处", "excluded"), ("恢复遮罩", "restore"))):
            button = QPushButton(text)
            button.clicked.connect(lambda _checked=False, act=action: self._action(act))
            row.addWidget(button, index//2, index%2)
            self.action_buttons[action] = button
        layout.addLayout(row)
        note = QLabel("不展开原文。双击可定位；排除仅对此处生效。补查候选需点确认才遮罩。Ctrl+Z/Y 可撤销/重做。扫描期间暂停复核操作。")
        note.setWordWrap(True)
        layout.addWidget(note)

    def set_rows(self, rows, status):
        selected = self.tree.currentItem()
        old = selected.data(0, Qt.ItemDataRole.UserRole) if selected else None
        self.tree.clear()
        self.status.setText(status)
        for entry in rows:
            item = QTreeWidgetItem([entry["label"], {"pending": "待复核", "confirmed": "已确认", "excluded": "已排除", "checked": "已扫描", "unchecked": "未扫描", "stale": "已失效"}.get(entry["state"], "待复核")])
            item.setData(0, Qt.ItemDataRole.UserRole, entry)
            confidence = entry.get("confidence")
            reason = entry.get("reason")
            if reason:
                tooltip = reason + "。请定位后复核。"
            elif isinstance(confidence, (int, float)):
                tooltip = f"识别置信度：{confidence:.2f}（仍需人工复核）"
            else:
                tooltip = "该来源未提供可靠置信度，请定位后复核。"
            item.setToolTip(0, tooltip)
            self.tree.addTopLevelItem(item)
            if old and all(entry.get(key) == old.get(key) for key in ("page", "key", "source", "geometry", "match_key")):
                self.tree.setCurrentItem(item)
        self.tree.resizeColumnToContents(1)
        self._filter()
        self._update_actions()

    def _update_actions(self, *_args):
        if not hasattr(self, "action_buttons"):
            return
        item = self.tree.currentItem()
        row = item.data(0, Qt.ItemDataRole.UserRole) if item else {}
        if not self.tree.isEnabled():
            for button in self.action_buttons.values():
                button.setEnabled(False)
            return
        source, state = row.get("source"), row.get("state")
        self.action_buttons["locate"].setEnabled(bool(row))
        self.action_buttons["confirmed"].setEnabled(source in ("ocr", "candidate") and state == "pending")
        self.action_buttons["excluded"].setEnabled(source in ("ocr", "candidate") and state != "excluded")
        self.action_buttons["restore"].setEnabled(source == "ocr" and state == "excluded")

    def _filter(self):
        mode = self.filter.currentIndex()
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            row = item.data(0, Qt.ItemDataRole.UserRole)
            show = (mode == 0 or mode == 1 and row["source"] in ("ocr", "candidate", "rule") or
                    mode == 2 and row["source"] == "manual" or mode == 3 and row["state"] == "excluded")
            item.setHidden(not show)

    def _action(self, action):
        item = self.tree.currentItem()
        if item:
            row = item.data(0, Qt.ItemDataRole.UserRole)
            if action == "locate":
                self.locate.emit(row)
            else:
                self.decide.emit(row, action)
