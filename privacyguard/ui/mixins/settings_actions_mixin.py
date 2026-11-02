"""SettingsActionsMixin: 设置对话框域操作方法（规则/关键词/OCR/导航/摘要）

v37.8.11 P1-3: 从 settings_dialog.py 提取，保持 SettingsDialog 类体积可控。

接口契约（SettingsDialog 须提供）：
- self.config / self.custom_keyword_rules / self.word_replace_rules
- self.rule_checkboxes / self.custom_keyword_table 等控件引用
- self.selected_rules / self.scan_level / self.offset_x / self.offset_w
- self.replacement_text / self.manual_replace_prompt
- _default_rules / available_levels / level_labels / x_range / w_range
"""

import json

from PyQt6.QtWidgets import QMessageBox, QFileDialog, QDialog

from privacyguard.utils.helpers_word_rules import (
    normalize_word_replace_rules,
    normalize_custom_keyword_rules,
)
from privacyguard.utils.helpers_ui import (
    build_settings_hero_tags,
    build_settings_nav_labels,
    format_signed_percent,
)


class SettingsActionsMixin:
    """设置对话框域操作方法组。"""

    def _on_adjust_changed(self, value):
        """v37.3.5: 检测框调节滑块值变化回调"""
        self.label_adjust_value.setText(f"{value}%")
        self._refresh_ocr_summary()

    def _apply_doc_context_visibility(self):
        """cp62: 按当前打开的文档类型隐藏逻辑上用不到的设置模块。"""
        context = self.doc_context
        if context not in ("pdf", "word"):
            return

        if context == "pdf":
            self.settings_right_field_card.setVisible(False)
            if len(self.settings_metric_cards) > 2:
                self.settings_metric_cards[2].setVisible(False)
            self.settings_custom_lead.setText("这里适合录入姓名、单位、案号等固定内容，命中后按遮罩/替换文本处理。")
            return

        # word：隐藏 OCR 专属模块（第 3、4 区块）与 PDF canvas 专属开关
        self.cb_manual_replace_prompt.setVisible(False)
        # v40.1.4 恢复：书签脱敏为 PDF 专属，Word 上下文一并隐藏
        if hasattr(self, "cb_bookmark_redact"):
            self.cb_bookmark_redact.setVisible(False)
        self.settings_left_field_note.setText(
            "每行一个关键词，Word 智能扫描命中后参与替换。\n"
            "带 |：优先使用该行替换文本，例如：原告|上诉人\n"
            '不带 |：使用右侧统一替换文本；"Word 替换规则设置"优先级最高。'
        )
        for section in self._settings_sections[2:]:
            section.setVisible(False)
        self._settings_sections = self._settings_sections[:2]
        for row in (3, 2):
            self.settings_nav.takeItem(row)
        for jump_btn in self.settings_quick_jump_buttons[2:]:
            jump_btn.setVisible(False)
        if len(self.settings_metric_cards) > 3:
            self.settings_metric_cards[3].setVisible(False)
        self.lbl_settings_advanced_tag.setVisible(False)
        self.settings_sidebar_note.setText('建议：第一次使用只改通用规则和关键词；Word 替换规则在"2 自定义关键词"里维护。')

    def _set_rule_checkbox_states(self, enabled_names):
        """批量更新规则勾选状态，避免多次触发联动刷新。"""
        enabled_names = set(enabled_names)
        for checkbox in self.checks.values():
            checkbox.blockSignals(True)
        try:
            for name, checkbox in self.checks.items():
                checkbox.setChecked(name in enabled_names)
        finally:
            for checkbox in self.checks.values():
                checkbox.blockSignals(False)
        self._refresh_rule_summary()

    def _apply_recommended_rules(self):
        """恢复首次使用推荐的通用规则勾选。"""
        self._set_rule_checkbox_states(self.recommended_rule_names)

    def _select_all_rules(self):
        """勾选全部通用规则。"""
        self._set_rule_checkbox_states(self.checks.keys())

    def _clear_all_rules(self):
        """清空所有通用规则勾选。"""
        self._set_rule_checkbox_states([])

    def _clear_custom_keywords(self):
        """v37.7.13 cp43: 清空自定义关键词文本框。"""
        if not hasattr(self, "txt_custom_rules"):
            return
        self.txt_custom_rules.clear()

    def _load_custom_keyword_rules_to_text(self):
        """v37.7.13 cp43: 将 custom_keyword_rules 加载到文本框。"""
        if not hasattr(self, "txt_custom_rules"):
            return
        lines = []
        for rule in self.custom_keyword_rules:
            if not rule.get("enabled", True):
                continue
            find_text = rule.get("find", "")
            replace_text = rule.get("replace", "")
            if not find_text:
                continue
            if replace_text:
                lines.append(f"{find_text}|{replace_text}")
            else:
                lines.append(find_text)
        self.txt_custom_rules.blockSignals(True)
        self.txt_custom_rules.setPlainText("\n".join(lines))
        self.txt_custom_rules.blockSignals(False)

    def _collect_custom_keyword_rules_from_table(self, silent=True):
        """v37.7.13 cp43: 从文本框收集规则列表。"""
        if not hasattr(self, "txt_custom_rules"):
            return []
        rules = []
        text = self.txt_custom_rules.toPlainText()
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                parts = line.split("|", 1)
                find_text = parts[0].strip()
                replace_text = parts[1].strip()
            else:
                find_text = line
                replace_text = ""
            if not find_text:
                continue
            rules.append({
                "enabled": True,
                "find": find_text,
                "replace": replace_text
            })
        return normalize_custom_keyword_rules(rules)

    def _import_custom_keyword_rules_json(self):
        """v37.7.13 cp43: 从 JSON 文件导入关键词规则到文本框。"""
        if not hasattr(self, "txt_custom_rules"):
            return
        fname, _ = QFileDialog.getOpenFileName(
            self, "导入关键词规则", "", "JSON 文件 (*.json)"
        )
        if not fname:
            return
        try:
            with open(fname, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                rules = data
            elif isinstance(data, dict):
                rules = data.get("rules", [])
            else:
                raise ValueError("JSON 根节点必须为数组或对象")
            self.custom_keyword_rules = normalize_custom_keyword_rules(rules)
            self._load_custom_keyword_rules_to_text()
            self._refresh_custom_summary()
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"读取或解析 JSON 失败：{e}")

    def _export_custom_keyword_rules_json(self):
        """v37.7.13 cp43: 从文本框导出关键词规则到 JSON 文件。"""
        if not hasattr(self, "txt_custom_rules"):
            return
        rules = self._collect_custom_keyword_rules_from_table(silent=True)
        fname, _ = QFileDialog.getSaveFileName(
            self, "导出关键词规则", "custom_keyword_rules.json", "JSON 文件 (*.json)"
        )
        if not fname:
            return
        try:
            with open(fname, "w", encoding="utf-8") as f:
                json.dump({"rules": rules}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"写入文件失败：{e}")

    def _reset_replacement_text(self):
        """恢复默认统一替换文本。"""
        self.input_replacement_text.setText(self.default_replacement_text)

    def _reset_precision_defaults(self):
        """恢复推荐的扫描与微调设置。"""
        # cp120 起默认扫描级别为 1.5（"标准 (1.5x 推荐)"），此前误写 2.0
        default_index = self.combo_precision.findData(1.5)
        if default_index >= 0:
            self.combo_precision.setCurrentIndex(default_index)
        self.spin_offset_x.setValue(0)
        self.spin_offset_w.setValue(0)
        self.cb_enhance.setChecked(False)
        self._refresh_precision_summary()

    def _reset_ocr_adjustment(self):
        """恢复 OCR 检测框默认调节值。"""
        self.slider_adjust.setValue(0)
        self._refresh_ocr_summary()

    def _scroll_to_settings_section(self, row):
        """左侧导航切换到对应设置区块。"""
        if getattr(self, "_settings_nav_syncing", False):
            return
        if row < 0 or row >= len(getattr(self, "_settings_sections", [])):
            return
        target = self._settings_sections[row]
        if not target or not hasattr(self, "content_scroll"):
            return
        self.content_scroll.verticalScrollBar().setValue(max(0, target.pos().y() - 8))

    def _sync_settings_nav_from_scroll(self, value):
        """滚动右侧内容时，同步高亮左侧设置导航。"""
        sections = getattr(self, "_settings_sections", [])
        if not sections or not hasattr(self, "settings_nav"):
            return

        scroll_bar = self.content_scroll.verticalScrollBar()
        # 滚动到底部时强制选中最后一项（scroll bar value 可能达不到最后一节的 y 坐标）
        if value >= scroll_bar.maximum():
            active_row = len(sections) - 1
        else:
            active_row = 0
            threshold = value + 24
            for index, section in enumerate(sections):
                if section and section.pos().y() <= threshold:
                    active_row = index
                else:
                    break

        if self.settings_nav.currentRow() == active_row:
            return

        self._settings_nav_syncing = True
        self.settings_nav.blockSignals(True)
        self.settings_nav.setCurrentRow(active_row)
        self.settings_nav.blockSignals(False)
        self._settings_nav_syncing = False

    def _refresh_settings_overview(self):
        """刷新设置页顶部配置概览。"""
        if not all(hasattr(self, attr) for attr in [
            "lbl_metric_rules", "lbl_metric_keywords", "lbl_metric_word_rules", "lbl_metric_ocr"
        ]):
            return

        enabled_rules = len([name for name, cb in self.checks.items() if cb.isChecked()]) if hasattr(self, "checks") else 0
        total_rules = len(self.checks) if hasattr(self, "checks") else 0
        rules = self._collect_custom_keyword_rules_from_table(silent=True) if hasattr(self, "_collect_custom_keyword_rules_from_table") else []
        keywords = [r["find"] for r in rules if r.get("enabled", True)]
        enabled_word_rules = len([r for r in self.word_replace_rules if r.get("enabled", True) and r.get("find")]) if hasattr(self, "word_replace_rules") else 0
        total_word_rules = len(self.word_replace_rules) if hasattr(self, "word_replace_rules") else 0
        adjust_value = self.slider_adjust.value() if hasattr(self, "slider_adjust") else 0
        scan_label = self.combo_precision.currentText().strip() if hasattr(self, "combo_precision") else "-"
        precision_is_default = True
        if hasattr(self, "combo_precision") and hasattr(self, "spin_offset_x") and hasattr(self, "spin_offset_w") and hasattr(self, "cb_enhance"):
            precision_is_default = (
                self.combo_precision.currentData() == 2.0
                and self.spin_offset_x.value() == 0
                and self.spin_offset_w.value() == 0
                and not self.cb_enhance.isChecked()
            )

        self.lbl_metric_rules.setText(f"{enabled_rules} / {total_rules} 已启用")
        self.lbl_metric_keywords.setText(f"{len(keywords)} 条关键词")
        self.lbl_metric_word_rules.setText(f"{enabled_word_rules} / {total_word_rules} 条规则")
        self.lbl_metric_ocr.setText(f"{adjust_value}% · {scan_label}")
        if hasattr(self, "lbl_settings_common_tag") and hasattr(self, "lbl_settings_advanced_tag"):
            common_tag, advanced_tag = build_settings_hero_tags(
                enabled_rules,
                len(keywords),
                enabled_word_rules,
                precision_is_default,
                adjust_value,
                scan_label,
            )
            self.lbl_settings_common_tag.setText(common_tag)
            self.lbl_settings_common_tag.setToolTip(common_tag)
            self.lbl_settings_advanced_tag.setText(advanced_tag)
            self.lbl_settings_advanced_tag.setToolTip(advanced_tag)
        self._refresh_settings_sidebar()

    def _refresh_settings_sidebar(self):
        """刷新左侧导航和侧栏摘要。"""
        if not hasattr(self, "settings_nav"):
            return

        enabled_rules = len([name for name, cb in self.checks.items() if cb.isChecked()]) if hasattr(self, "checks") else 0
        keyword_count = len([r for r in (self._collect_custom_keyword_rules_from_table(silent=True) if hasattr(self, "_collect_custom_keyword_rules_from_table") else []) if r.get("enabled", True)])
        precision_is_default = True
        if hasattr(self, "combo_precision") and hasattr(self, "spin_offset_x") and hasattr(self, "spin_offset_w") and hasattr(self, "cb_enhance"):
            precision_is_default = (
                self.combo_precision.currentData() == 2.0
                and self.spin_offset_x.value() == 0
                and self.spin_offset_w.value() == 0
                and not self.cb_enhance.isChecked()
            )
        adjust_value = self.slider_adjust.value() if hasattr(self, "slider_adjust") else 0

        nav_labels = build_settings_nav_labels(enabled_rules, keyword_count, precision_is_default, adjust_value)
        for index, text in enumerate(nav_labels):
            item = self.settings_nav.item(index)
            if item and item.text() != text:
                item.setText(text)

        if hasattr(self, "settings_sidebar_status"):
            if getattr(self, "doc_context", None) == "word":
                self.settings_sidebar_status.setText(
                    f"常用区：规则 {enabled_rules} 项、关键词 {keyword_count} 条。"
                )
            else:
                advanced_text = "扫描保持默认" if precision_is_default else "扫描参数已微调"
                self.settings_sidebar_status.setText(
                    f"常用区：规则 {enabled_rules} 项、关键词 {keyword_count} 条。\n"
                    f"高级区：{advanced_text} · OCR {format_signed_percent(adjust_value)}。"
                )

    def _refresh_word_rule_summary(self):
        enabled_count = len([r for r in self.word_replace_rules if r.get("enabled", True) and r.get("find")])
        total_count = len(self.word_replace_rules)
        self.lbl_word_rule_count.setText(
            f"当前规则：{enabled_count} 条启用 / {total_count} 条总计\n"
            '点击"打开替换规则设置"可进入原有替换规则弹窗。'
        )
        self._refresh_custom_summary()

    def _refresh_rule_summary(self):
        enabled_names = [name for name, cb in self.checks.items() if cb.isChecked()]
        enabled_count = len(enabled_names)
        preview = "、".join(enabled_names[:3]) if enabled_names else "当前未启用任何通用规则"
        if enabled_count > 3:
            preview = f"{preview} 等 {enabled_count} 项"
        self.lbl_rules_summary.setText(f"当前启用：{preview}")
        self._refresh_settings_overview()

    def _refresh_custom_summary(self):
        if not hasattr(self, "input_replacement_text") or not hasattr(self, "lbl_custom_summary"):
            return
        rules = self._collect_custom_keyword_rules_from_table(silent=True) if hasattr(self, "_collect_custom_keyword_rules_from_table") else []
        keyword_count = len([r for r in rules if r.get("enabled", True)])
        replace_count = len([r for r in rules if r.get("enabled", True) and r.get("replace")])
        replacement_preview = self.input_replacement_text.text().strip() or "[已脱敏]"
        enabled_rule_count = len([r for r in self.word_replace_rules if r.get("enabled", True) and r.get("find")])
        replace_hint = f" · 含替换文本 {replace_count} 条" if replace_count else ""
        if getattr(self, "doc_context", None) == "pdf":
            self.lbl_custom_summary.setText(
                f"自定义关键词 {keyword_count} 条{replace_hint}"
            )
        else:
            self.lbl_custom_summary.setText(
                f"自定义关键词 {keyword_count} 条{replace_hint} · 统一替换文本：{replacement_preview} · Word 规则：{enabled_rule_count} 条启用"
            )
        self._refresh_settings_overview()

    def _refresh_precision_summary(self):
        current_label = self.combo_precision.currentText().strip()
        enhance_text = "已开启图像增强" if self.cb_enhance.isChecked() else "图像增强关闭"
        self.lbl_precision_summary.setText(
            f"当前扫描模式：{current_label} · 向左修正 {self.spin_offset_x.value()} px · 宽度收缩 {self.spin_offset_w.value()} px · {enhance_text}"
        )
        self._refresh_settings_overview()

    def _refresh_ocr_summary(self):
        adjust_value = self.slider_adjust.value()
        if adjust_value < 0:
            trend = "扩大检测框"
        elif adjust_value > 0:
            trend = "收缩检测框"
        else:
            trend = "保持原始检测框"
        self.lbl_ocr_summary.setText(f"当前检测框调节：{adjust_value}% · {trend}")
        self._refresh_settings_overview()

    def _open_word_rules_editor(self):
        from privacyguard.ui.dialogs.word_replace_rules_dialog import WordReplaceRulesDialog  # 懒导入避免循环依赖
        default_text = self.input_replacement_text.text().strip() or "[已脱敏]"
        dlg = WordReplaceRulesDialog(
            self,
            rules=self.word_replace_rules,
            default_replacement_text=default_text,
            title="Word 替换规则设置",
            apply_text="应用规则"
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self.word_replace_rules = dlg.rules
        self.input_replacement_text.setText(dlg.default_replacement_text)
        self._refresh_word_rule_summary()

    def _open_trace_clean(self):
        """cp90: 打开清理使用痕迹对话框（数据源与白名单由主窗装配）。"""
        parent = self.parent()
        if parent is None or not hasattr(parent, "_open_trace_clean_dialog"):
            return
        parent._open_trace_clean_dialog(self)

    def save_settings(self):
        self.selected_rules = [self._default_rules[name] for name, cb in self.checks.items() if cb.isChecked()]
        self.use_enhance = self.cb_enhance.isChecked()
        # v37.7.13 cp43: 从表格收集规则 + 回读手动替换开关
        self.custom_keyword_rules = self._collect_custom_keyword_rules_from_table(silent=True)
        # 保留旧字符串字段用于向后兼容（仅 enabled+find 条目）
        self.custom_keywords = "\n".join(r["find"] for r in self.custom_keyword_rules if r.get("enabled", True))
        self.manual_replace_prompt = self.cb_manual_replace_prompt.isChecked() if hasattr(self, "cb_manual_replace_prompt") else False
        # v40.1.4 恢复：书签栏脱敏开关回读（cp_bookmark 原有，08a2c51 误删）
        self.bookmark_redact_enabled = self.cb_bookmark_redact.isChecked() if hasattr(self, "cb_bookmark_redact") else False
        self.scan_level = self.combo_precision.currentData()
        self.offset_x = self.spin_offset_x.value()
        self.offset_w = self.spin_offset_w.value()
        self.replacement_text = self.input_replacement_text.text().strip() or "[已脱敏]"
        self.word_replace_rules = normalize_word_replace_rules(self.word_replace_rules, self.replacement_text)

        # v37.4.0: 保存检测框调节比例
        self.box_adjust_ratio = self.slider_adjust.value() / 100.0

        # v37.0: 保存到配置文件
        if self.config:
            try:
                self.config.set("redaction.scan.default_level", self.scan_level, persist=False)
                self.config.set("redaction.offset.default_x", self.offset_x, persist=False)
                self.config.set("redaction.offset.default_w", self.offset_w, persist=False)
                self.config.set("redaction.custom_keywords", self.custom_keywords, persist=False)
                # v37.7.13 cp43: 持久化新字段
                self.config.set("redaction.custom_keyword_rules", self.custom_keyword_rules, persist=False)
                self.config.set("redaction.manual_replace_prompt", self.manual_replace_prompt, persist=False)
                # v40.1.4 恢复：持久化书签脱敏开关（cp_bookmark 原有，08a2c51 误删）
                self.config.set("redaction.bookmark_redact_enabled", self.bookmark_redact_enabled, persist=False)
                self.config.set("redaction.replacement_text", self.replacement_text, persist=False)
                self.config.set("ocr.box_adjust_ratio", self.box_adjust_ratio, persist=False)
                self.config.save()
            except Exception as e:
                import logging as _lg
                _lg.getLogger(__name__).warning("[设置] 保存配置失败: %s", type(e).__name__)

        self.accept()

