"""Rule editor additions. Contract: table, input_default_text, rule collectors.

Adds compact controls within the existing editor; batch plan is opt-in.
"""
from PyQt6.QtWidgets import QHBoxLayout, QComboBox, QPushButton, QCheckBox, QMessageBox, QFileDialog, QDialog, QTableWidgetItem
from privacyguard.utils.rule_templates import (preset_rules, read_template, write_template,
                                               consistent_rules, validate_file_plan)


class TemplateActionsMixin:
    def setup_template_controls(self, layout, file_paths=None):
        self.file_paths = list(file_paths or [])
        self.file_plan = None
        self.private_rule_mapping = False
        row = QHBoxLayout()
        self.template_choice = QComboBox()
        self.template_choice.addItems(["选择起始模板", "卷宗", "合同", "流水", "人事"])
        row.addWidget(self.template_choice)
        button = QPushButton("追加模板规则")
        button.clicked.connect(self.append_preset)
        row.addWidget(button)
        self.consistent_choice = QPushButton("生成精确词编号")
        self.consistent_choice.setToolTip("按输入的精确词生成当事人1、2…；同名是否同一人由您决定。不会自动关联简称，不保存还原表。")
        self.consistent_choice.clicked.connect(self.preview_consistent)
        row.addWidget(self.consistent_choice)
        self.per_file_choice = QCheckBox("逐文件设置")
        self.per_file_choice.setVisible(bool(self.file_paths))
        row.addWidget(self.per_file_choice)
        row.addStretch()
        layout.addLayout(row)

    def append_preset(self):
        choice = self.template_choice.currentText()
        if choice == "选择起始模板":
            return
        for rule in preset_rules(choice):
            self.add_rule_row(rule)
        QMessageBox.information(self, "模板已追加", "已追加手机号/证件号起始规则。请检查表格，并补充姓名、地址等需要处理的精确词；模板不能识别所有敏感信息。")

    def prepare_template_result(self, rules):
        if self.file_paths:
            mapping = {}
            if self.per_file_choice.isChecked():
                from privacyguard.ui.dialogs.batch_file_plan_dialog import BatchFilePlanDialog
                dialog = BatchFilePlanDialog(self.file_paths, rules, self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return None
                mapping = dialog.plan()
            self.file_plan = validate_file_plan(self.file_paths, mapping, rules)
        return rules

    def preview_consistent(self):
        rules, _default, errors = self._collect_rules_from_table(validate_regex=True)
        if errors:
            QMessageBox.warning(self, "请先填好规则", "\n".join(errors))
            return
        reply = QMessageBox.question(self, "精确词编号预览", "相同精确词会使用同一编号，软件不会判断同名是否同一人。生成后可在表格直接检查和修改。是否生成？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        numbered = consistent_rules(rules)
        replacements = {r["find"].casefold(): r["replace"] for r in numbered if r["enabled"] and r["mode"] == "exact"}
        for row in range(self.table.rowCount()):
            find = self.table.item(row, 2)
            mode = self.table.item(row, 1)
            if find and mode and mode.text().strip() == "exact" and find.text().strip().casefold() in replacements:
                self.table.setItem(row, 3, QTableWidgetItem(replacements[find.text().strip().casefold()]))
        self.private_rule_mapping = True

    def import_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入规则模板", "", "JSON 文件 (*.json)")
        if not path:
            return
        try:
            payload = read_template(path)
            self.input_default_text.setText(payload["default_replacement_text"])
            self.table.setRowCount(0)
            for rule in payload["rules"]:
                self.add_rule_row(rule)
            if not payload["rules"]:
                self.add_rule_row()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "模板未导入", str(error))

    def export_template(self):
        rules, default, errors = self._collect_rules_from_table(validate_regex=True)
        if errors:
            QMessageBox.warning(self, "无法导出", "\n".join(errors))
            return
        reply = QMessageBox.question(self, "模板可能包含原文", "模板会包含表格中填写的查找词和替换词。请妥善保管，不要把含真实姓名/号码的模板公开分享。是否继续？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存规则模板", "word_rules.json", "JSON 文件 (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            write_template(path, rules, default)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "模板未保存", str(error))
