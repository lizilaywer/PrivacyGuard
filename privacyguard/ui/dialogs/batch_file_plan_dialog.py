"""Explicit per-file selection, no filename heuristics or inherited state."""
import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QDialogButtonBox, QHeaderView, QPushButton)
from privacyguard.utils.rule_templates import canonical_file, preset_rules


class BatchFilePlanDialog(QDialog):
    def __init__(self, files, common_rules, parent=None):
        super().__init__(parent)
        from privacyguard.ui.office_style import apply_office_style
        apply_office_style(self)
        self.files = list(files)
        self.common_rules = common_rules
        self.custom_rules = {}
        self.setWindowTitle("逐文件规则计划")
        self.resize(650, 430)
        layout = QVBoxLayout(self)
        note = QLabel("默认每个文件使用当前规则。可单独选择起始模板或跳过；模板仅覆盖手机号/证件号，请按实际文书补充姓名等精确词。")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = QTableWidget(len(files), 3)
        self.table.setHorizontalHeaderLabels(["文件", "本文件规则", "调整"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for row, path in enumerate(files):
            item = QTableWidgetItem(os.path.basename(path))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, item)
            combo = QComboBox()
            combo.addItems(["当前规则", "卷宗", "合同", "流水", "人事", "自定义", "跳过此文件"])
            self.table.setCellWidget(row, 1, combo)
            button = QPushButton("调整规则")
            button.clicked.connect(lambda _checked=False, index=row: self.edit_row(index))
            self.table.setCellWidget(row, 2, button)
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def plan(self):
        mapping = {}
        for row, path in enumerate(self.files):
            choice = self.table.cellWidget(row, 1).currentText()
            mapping[canonical_file(path)] = self.rules_for_row(row, choice)
        return mapping

    def rules_for_row(self, row, choice=None):
        choice = choice or self.table.cellWidget(row, 1).currentText()
        if choice == "跳过此文件":
            return None
        if choice == "当前规则":
            return self.common_rules
        if choice == "自定义":
            return self.custom_rules.get(row, self.common_rules)
        return preset_rules(choice)

    def edit_row(self, row):
        from privacyguard.ui.dialogs.word_replace_rules_dialog import WordReplaceRulesDialog
        editor = WordReplaceRulesDialog(self, rules=self.rules_for_row(row) or [],
                                       title="本文件规则：" + os.path.basename(self.files[row]))
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.custom_rules[row] = editor.rules
            self.table.cellWidget(row, 1).setCurrentText("自定义")
