"""Word 多字段替换规则对话框（会话级规则，可导入/导出）"""
import json
import re

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt

from privacyguard.utils.helpers_word_rules import (
    normalize_word_replace_rules,
    validate_word_replace_rules,
)

WORD_RULE_SCHEMA_VERSION = 1


class WordReplaceRulesDialog(QDialog):
    """Word 多字段替换规则对话框（会话级规则，可导入/导出）。"""

    def __init__(self, parent=None, rules=None, default_replacement_text="[已脱敏]",
                 title="替换规则设置", apply_text="应用规则"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(780, 520)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.rules = normalize_word_replace_rules(rules or [], default_replacement_text)
        self.default_replacement_text = default_replacement_text if isinstance(default_replacement_text, str) and default_replacement_text else "[已脱敏]"

        main_layout = QVBoxLayout(self)

        header = QLabel("支持精确(exact)和正则(regex)两种模式。执行顺序：精确优先，其次正则；同模式按规则顺序。")
        header.setWordWrap(True)
        main_layout.addWidget(header)

        default_row = QHBoxLayout()
        default_row.addWidget(QLabel("默认替换文本:"))
        self.input_default_text = QLineEdit(self.default_replacement_text)
        self.input_default_text.setPlaceholderText("[已脱敏]")
        default_row.addWidget(self.input_default_text)
        main_layout.addLayout(default_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["启用", "模式(exact/regex)", "查找文本", "替换文本"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.table)

        row_btn_layout = QHBoxLayout()
        btn_add = QPushButton("新增规则")
        btn_del = QPushButton("删除规则")
        btn_up = QPushButton("上移")
        btn_down = QPushButton("下移")
        btn_import = QPushButton("导入JSON")
        btn_export = QPushButton("导出JSON")
        row_btn_layout.addWidget(btn_add)
        row_btn_layout.addWidget(btn_del)
        row_btn_layout.addWidget(btn_up)
        row_btn_layout.addWidget(btn_down)
        row_btn_layout.addStretch()
        row_btn_layout.addWidget(btn_import)
        row_btn_layout.addWidget(btn_export)
        main_layout.addLayout(row_btn_layout)

        btn_add.clicked.connect(self.add_rule_row)
        btn_del.clicked.connect(self.remove_selected_rule)
        btn_up.clicked.connect(lambda: self.move_selected_rule(-1))
        btn_down.clicked.connect(lambda: self.move_selected_rule(1))
        btn_import.clicked.connect(self.import_rules_json)
        btn_export.clicked.connect(self.export_rules_json)

        footer = QHBoxLayout()
        footer.addStretch()
        btn_cancel = QPushButton("取消")
        btn_apply = QPushButton(apply_text)
        footer.addWidget(btn_cancel)
        footer.addWidget(btn_apply)
        main_layout.addLayout(footer)

        btn_cancel.clicked.connect(self.reject)
        btn_apply.clicked.connect(self.apply_rules)

        for rule in self.rules:
            self.add_rule_row(rule)

        if self.table.rowCount() == 0:
            self.add_rule_row()

    def add_rule_row(self, rule=None):
        rule = rule or {"enabled": True, "mode": "exact", "find": "", "replace": ""}
        row = self.table.rowCount()
        self.table.insertRow(row)

        enabled_item = QTableWidgetItem()
        enabled_item.setFlags(
            Qt.ItemFlag.ItemIsEnabled |
            Qt.ItemFlag.ItemIsUserCheckable |
            Qt.ItemFlag.ItemIsSelectable
        )
        enabled_item.setCheckState(Qt.CheckState.Checked if rule.get("enabled", True) else Qt.CheckState.Unchecked)
        self.table.setItem(row, 0, enabled_item)

        mode = str(rule.get("mode", "exact")).strip().lower()
        if mode not in ("exact", "regex"):
            mode = "exact"
        self.table.setItem(row, 1, QTableWidgetItem(mode))
        self.table.setItem(row, 2, QTableWidgetItem(str(rule.get("find", ""))))
        self.table.setItem(row, 3, QTableWidgetItem(str(rule.get("replace", ""))))
        self.table.selectRow(row)

    def remove_selected_rule(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self.table.removeRow(row)
        if self.table.rowCount() == 0:
            self.add_rule_row()

    def move_selected_rule(self, direction):
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        target_row = current_row + direction
        if target_row < 0 or target_row >= self.table.rowCount():
            return

        current_data = []
        target_data = []
        for col in range(self.table.columnCount()):
            current_item = self.table.item(current_row, col)
            target_item = self.table.item(target_row, col)
            current_data.append(current_item.clone() if current_item else QTableWidgetItem())
            target_data.append(target_item.clone() if target_item else QTableWidgetItem())

        for col in range(self.table.columnCount()):
            self.table.setItem(current_row, col, target_data[col])
            self.table.setItem(target_row, col, current_data[col])

        self.table.selectRow(target_row)

    def _collect_rules_from_table(self, validate_regex=True):
        errors = []
        rules = []
        default_text = self.input_default_text.text().strip() or "[已脱敏]"

        for row in range(self.table.rowCount()):
            enabled_item = self.table.item(row, 0)
            mode_item = self.table.item(row, 1)
            find_item = self.table.item(row, 2)
            replace_item = self.table.item(row, 3)

            enabled = enabled_item is not None and enabled_item.checkState() == Qt.CheckState.Checked
            mode = mode_item.text().strip().lower() if mode_item else "exact"
            find_text = find_item.text().strip() if find_item else ""
            replace_text = replace_item.text() if replace_item else ""

            if mode not in ("exact", "regex"):
                errors.append(f"第 {row + 1} 行模式无效：{mode}（仅支持 exact/regex）")
                continue
            if enabled and not find_text:
                errors.append(f"第 {row + 1} 行查找文本不能为空")
                continue
            if enabled and mode == "regex" and validate_regex:
                try:
                    re.compile(find_text)
                except re.error as e:
                    errors.append(f"第 {row + 1} 行正则无效：{e}")
                    continue
            if not replace_text:
                replace_text = default_text

            rules.append({
                "enabled": enabled,
                "mode": mode,
                "find": find_text,
                "replace": replace_text
            })

        normalized = normalize_word_replace_rules(rules, default_text)
        return normalized, default_text, errors

    def apply_rules(self):
        rules, default_text, errors = self._collect_rules_from_table(validate_regex=True)
        if errors:
            QMessageBox.warning(self, "规则校验失败", "\n".join(errors))
            return

        self.rules = rules
        self.default_replacement_text = default_text
        self.accept()

    def import_rules_json(self):
        fname, _ = QFileDialog.getOpenFileName(self, "导入替换规则", "", "JSON 文件 (*.json)")
        if not fname:
            return

        try:
            with open(fname, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("JSON 根节点必须为对象")

            default_text = str(data.get("default_replacement_text", self.input_default_text.text().strip() or "[已脱敏]"))
            rules = data.get("rules", [])
            if not isinstance(rules, list):
                raise ValueError("rules 字段必须为数组")

            normalized = normalize_word_replace_rules(rules, default_text)

            self.input_default_text.setText(default_text)
            self.table.setRowCount(0)
            for rule in normalized:
                self.add_rule_row(rule)
            if self.table.rowCount() == 0:
                self.add_rule_row()

            # W5: 导入后立即校验非法正则，避免"已导入但运行时静默漏脱"
            regex_errors = validate_word_replace_rules(normalized)
            if regex_errors:
                detail = "\n".join(
                    f"第 {err['index'] + 1} 条正则无效：{err['find']} → {err['error']}"
                    for err in regex_errors
                )
                QMessageBox.warning(
                    self, "导入完成（含无效正则）",
                    f"已导入 {len(normalized)} 条规则，但以下正则无效，将不会生效，请修正后再应用：\n{detail}"
                )
            else:
                QMessageBox.information(self, "导入成功", f"已导入 {len(normalized)} 条规则")
        except (OSError, IOError, ValueError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "导入失败", f"无法导入规则文件：\n{e}")

    def export_rules_json(self):
        rules, default_text, errors = self._collect_rules_from_table(validate_regex=True)
        if errors:
            QMessageBox.warning(self, "无法导出", "\n".join(errors))
            return

        fname, _ = QFileDialog.getSaveFileName(self, "导出替换规则", "word_replace_rules.json", "JSON 文件 (*.json)")
        if not fname:
            return

        if not fname.lower().endswith(".json"):
            fname = fname + ".json"

        payload = {
            "version": WORD_RULE_SCHEMA_VERSION,
            "default_replacement_text": default_text,
            "rules": rules
        }
        try:
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"规则已导出到：\n{fname}")
        except (OSError, IOError, ValueError) as e:
            QMessageBox.critical(self, "导出失败", f"无法导出规则文件：\n{e}")
