"""SettingsLayoutMixin: 设置对话框布局/密度/响应式方法

v37.8.11 P1-3: 从 settings_dialog.py 提取，保持 SettingsDialog 类体积可控。

接口契约（SettingsDialog 须提供）：
- self.config / self.content_widget / self.settings_nav / self.settings_sidebar
- self.settings_body_layout / self.settings_hero_layout 等布局引用
- 各 section widget 引用（由 __init__ 创建）
"""

from PyQt6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QApplication,
)
from PyQt6.QtCore import QTimer

from privacyguard.utils.helpers_ui import resolve_settings_density_mode
from theme import Theme


class SettingsLayoutMixin:
    """设置对话框布局密度与响应式方法组。"""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_settings_layout_density()

    def showEvent(self, event):
        super().showEvent(event)
        self._bind_settings_window_handle_signals()
        QTimer.singleShot(0, self._refresh_settings_layout_density)

    def _get_settings_display_scale_factor(self):
        """返回设置窗口当前屏幕缩放，仅在 Windows 下生效。"""
        import platform

        if platform.system() != "Windows":
            return 1.0

        screen = None
        try:
            handle = self.windowHandle()
            if handle:
                screen = handle.screen()
        except Exception:
            screen = None

        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return 1.0

        try:
            scale = screen.logicalDotsPerInch() / 96.0
        except Exception:
            scale = 1.0

        return max(1.0, min(scale, 2.0))

    def _bind_settings_window_handle_signals(self):
        """绑定设置窗口跨屏信号，保证 DPI 切换后密度立即刷新。"""
        try:
            handle = self.windowHandle()
        except Exception:
            handle = None

        if handle is None or handle is self._settings_bound_window_handle:
            return

        try:
            handle.screenChanged.connect(self._on_settings_screen_changed)
        except Exception:
            pass
        self._settings_bound_window_handle = handle

    def _on_settings_screen_changed(self, _screen):
        """设置窗口切换屏幕后刷新密度。"""
        QTimer.singleShot(0, self._refresh_settings_layout_density)

    def _create_settings_metric_card(self, title):
        """创建设置页顶部概览指标卡。"""
        card = QFrame()
        card.setObjectName("settingsMetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("settingsMetricLabel")
        value_label = QLabel("--")
        value_label.setObjectName("settingsMetricValue")
        value_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addStretch()
        return card, value_label

    def _rebuild_settings_grid(self, layout, widgets, columns, stretches=None):
        """按列数重排设置页网格布局。"""
        if not layout:
            return
        while layout.count():
            layout.takeAt(0)

        max_slots = max(len(widgets), 4)
        for column in range(max_slots):
            layout.setColumnStretch(column, 0)
        for row in range(max_slots):
            layout.setRowStretch(row, 0)

        columns = max(1, columns)
        for index, widget in enumerate(widgets):
            row = index // columns
            column = index % columns
            layout.addWidget(widget, row, column)

        if stretches:
            for column, stretch in enumerate(stretches):
                layout.setColumnStretch(column, stretch)
        else:
            for column in range(columns):
                layout.setColumnStretch(column, 1)

    def _refresh_settings_layout_density(self):
        """按当前窗口宽度微调设置页整体比例。"""
        width = max(self.width(), 1)
        height = max(self.height(), 1)
        scale = self._get_settings_display_scale_factor()
        density_mode = resolve_settings_density_mode(width, height, scale)
        is_tall_window = height >= 980
        is_short_window = height <= 820
        is_very_wide_window = width >= 1620
        is_ultra_wide_window = width >= 1920
        is_cinema_wide_window = width >= 2140

        if density_mode == "wide":
            sidebar_width = 264
            body_spacing = 22
            hero_margins = (22, 18, 22, 18)
            overview_margins = (22, 18, 22, 18)
            footer_margins = (22, 14, 22, 14)
            hero_tag_spacing = 10
            metric_spacing = 12
            action_spacing = 10
            custom_spacing = 24
            precision_spacing = 18
            jump_min_width = 134
            quick_jump_compact = False
            overview_metric_columns = 4
            overview_action_columns = 4
            custom_columns = 2
            precision_columns = 2
            custom_stretches = (3, 2)
            precision_stretches = (1, 1)
            right_panel_max_width = 680
            right_panel_min_width = 430
            left_card_min_height = 348
            right_card_min_height = 348
            precision_card_min_height = 238
            adjust_card_min_height = 234
            cancel_min_width = 122
            save_min_width = 172
        elif density_mode == "roomy":
            sidebar_width = 248
            body_spacing = 18
            hero_margins = (18, 16, 18, 16)
            overview_margins = (18, 16, 18, 16)
            footer_margins = (18, 14, 18, 14)
            hero_tag_spacing = 8
            metric_spacing = 10
            action_spacing = 8
            custom_spacing = 22
            precision_spacing = 16
            jump_min_width = 124
            quick_jump_compact = False
            overview_metric_columns = 4
            overview_action_columns = 4
            custom_columns = 2
            precision_columns = 2
            custom_stretches = (3, 2)
            precision_stretches = (1, 1)
            right_panel_max_width = 620
            right_panel_min_width = 392
            left_card_min_height = 330
            right_card_min_height = 330
            precision_card_min_height = 224
            adjust_card_min_height = 220
            cancel_min_width = 116
            save_min_width = 164
        elif density_mode == "compact":
            sidebar_width = 232
            body_spacing = 16
            hero_margins = (16, 15, 16, 15)
            overview_margins = (16, 15, 16, 15)
            footer_margins = (16, 12, 16, 12)
            hero_tag_spacing = 8
            metric_spacing = 8
            action_spacing = 8
            custom_spacing = 18
            precision_spacing = 14
            jump_min_width = 114
            quick_jump_compact = False
            overview_metric_columns = 2
            overview_action_columns = 2
            custom_columns = 2
            precision_columns = 1
            custom_stretches = (7, 5)
            precision_stretches = (1,)
            right_panel_max_width = 540
            right_panel_min_width = 344
            left_card_min_height = 302
            right_card_min_height = 302
            precision_card_min_height = 208
            adjust_card_min_height = 204
            cancel_min_width = 112
            save_min_width = 156
        else:
            sidebar_width = 220
            body_spacing = 14
            hero_margins = (14, 14, 14, 14)
            overview_margins = (14, 14, 14, 14)
            footer_margins = (14, 12, 14, 12)
            hero_tag_spacing = 6
            metric_spacing = 8
            action_spacing = 6
            custom_spacing = 14
            precision_spacing = 12
            jump_min_width = 102
            quick_jump_compact = True
            overview_metric_columns = 2
            overview_action_columns = 2
            custom_columns = 1
            precision_columns = 1
            custom_stretches = (1,)
            precision_stretches = (1,)
            right_panel_max_width = 9999
            right_panel_min_width = 0
            left_card_min_height = 270
            right_card_min_height = 270
            precision_card_min_height = 194
            adjust_card_min_height = 194
            cancel_min_width = 108
            save_min_width = 148

        if scale >= 1.5:
            body_spacing += 2
            hero_tag_spacing += 1
            metric_spacing += 2
            action_spacing += 2
            custom_spacing += 2
            precision_spacing += 2
            jump_min_width += 6
            cancel_min_width += 8
            save_min_width += 10
            left_card_min_height += 14
            right_card_min_height += 14
            precision_card_min_height += 10
            adjust_card_min_height += 10
        elif scale >= 1.25:
            jump_min_width += 4
            cancel_min_width += 6
            save_min_width += 8
            left_card_min_height += 8
            right_card_min_height += 8
            precision_card_min_height += 6
            adjust_card_min_height += 6

        if is_tall_window:
            left_card_min_height += 18
            right_card_min_height += 18
            precision_card_min_height += 10
            adjust_card_min_height += 10
            hero_margins = (
                hero_margins[0] + 2,
                hero_margins[1] + 2,
                hero_margins[2] + 2,
                hero_margins[3] + 2,
            )
            overview_margins = (
                overview_margins[0] + 2,
                overview_margins[1] + 2,
                overview_margins[2] + 2,
                overview_margins[3] + 2,
            )
        elif is_short_window:
            body_spacing = max(12, body_spacing - 2)
            hero_tag_spacing = max(6, hero_tag_spacing - 1)
            metric_spacing = max(8, metric_spacing - 2)
            action_spacing = max(6, action_spacing - 2)
            custom_spacing = max(14, custom_spacing - 2)
            precision_spacing = max(12, precision_spacing - 2)
            left_card_min_height = max(270, left_card_min_height - 18)
            right_card_min_height = max(270, right_card_min_height - 18)
            precision_card_min_height = max(194, precision_card_min_height - 10)
            adjust_card_min_height = max(194, adjust_card_min_height - 10)
            footer_margins = (
                footer_margins[0],
                max(10, footer_margins[1] - 2),
                footer_margins[2],
                max(10, footer_margins[3] - 2),
            )

        if is_very_wide_window:
            sidebar_width += 10
            body_spacing += 2
            custom_spacing += 2
            precision_spacing += 2
            right_panel_max_width += 60 if right_panel_max_width < 9000 else 0
            right_panel_min_width += 24 if right_panel_min_width else 0
            left_card_min_height += 10
            right_card_min_height += 10
            precision_card_min_height += 8
            adjust_card_min_height += 8
            hero_margins = (
                hero_margins[0] + 2,
                hero_margins[1] + 2,
                hero_margins[2] + 2,
                hero_margins[3] + 2,
            )
            overview_margins = (
                overview_margins[0] + 2,
                overview_margins[1] + 2,
                overview_margins[2] + 2,
                overview_margins[3] + 2,
            )

        if is_ultra_wide_window:
            sidebar_width += 8
            body_spacing += 2
            hero_tag_spacing += 1
            metric_spacing += 2
            action_spacing += 2
            custom_spacing += 2
            precision_spacing += 2
            jump_min_width += 6
            right_panel_max_width += 80 if right_panel_max_width < 9000 else 0
            right_panel_min_width += 28 if right_panel_min_width else 0
            left_card_min_height += 10
            right_card_min_height += 10

        if is_cinema_wide_window:
            sidebar_width += 10
            body_spacing += 2
            hero_tag_spacing += 1
            metric_spacing += 2
            action_spacing += 2
            custom_spacing += 2
            precision_spacing += 2
            jump_min_width += 8
            right_panel_max_width += 120 if right_panel_max_width < 9000 else 0
            right_panel_min_width += 36 if right_panel_min_width else 0
            left_card_min_height += 10
            right_card_min_height += 10
            precision_card_min_height += 8
            adjust_card_min_height += 8
            hero_margins = (
                hero_margins[0] + 4,
                hero_margins[1] + 2,
                hero_margins[2] + 4,
                hero_margins[3] + 2,
            )
            overview_margins = (
                overview_margins[0] + 4,
                overview_margins[1] + 2,
                overview_margins[2] + 4,
                overview_margins[3] + 2,
            )

        quick_jump_height = 34 if scale >= 1.25 else 32
        footer_button_height = 42 if scale >= 1.25 else 40

        if hasattr(self, "settings_sidebar"):
            self.settings_sidebar.setFixedWidth(sidebar_width)
        if hasattr(self, "settings_body_layout"):
            self.settings_body_layout.setSpacing(body_spacing)
        if hasattr(self, "settings_hero_layout"):
            self.settings_hero_layout.setContentsMargins(*hero_margins)
        if hasattr(self, "settings_hero_tag_layout"):
            self.settings_hero_tag_layout.setSpacing(hero_tag_spacing)
        if hasattr(self, "settings_overview_layout"):
            self.settings_overview_layout.setContentsMargins(*overview_margins)
        if hasattr(self, "settings_overview_metrics_layout"):
            self.settings_overview_metrics_layout.setHorizontalSpacing(metric_spacing)
            self.settings_overview_metrics_layout.setVerticalSpacing(metric_spacing)
            visible_metric_cards = [card for card in self.settings_metric_cards if not card.isHidden()]
            self._rebuild_settings_grid(
                self.settings_overview_metrics_layout,
                visible_metric_cards,
                min(overview_metric_columns, max(1, len(visible_metric_cards))),
            )
        if hasattr(self, "settings_overview_actions_layout"):
            self.settings_overview_actions_layout.setHorizontalSpacing(action_spacing)
            self.settings_overview_actions_layout.setVerticalSpacing(action_spacing)
            visible_jump_buttons = [btn for btn in self.settings_quick_jump_buttons if not btn.isHidden()]
            self._rebuild_settings_grid(
                self.settings_overview_actions_layout,
                visible_jump_buttons,
                min(overview_action_columns, max(1, len(visible_jump_buttons))),
            )
        if hasattr(self, "settings_footer_layout"):
            self.settings_footer_layout.setContentsMargins(*footer_margins)
        for index, button in enumerate(getattr(self, "settings_quick_jump_buttons", [])):
            button.setMinimumWidth(jump_min_width)
            button.setMinimumHeight(quick_jump_height)
            button.setMaximumHeight(quick_jump_height)
            if hasattr(self, "_settings_quick_jump_titles") and index < len(self._settings_quick_jump_titles):
                full_title, short_title = self._settings_quick_jump_titles[index]
                button.setText(short_title if quick_jump_compact else full_title)
        if hasattr(self, "btn_settings_cancel"):
            self.btn_settings_cancel.setMinimumWidth(cancel_min_width)
            self.btn_settings_cancel.setMinimumHeight(footer_button_height)
            self.btn_settings_cancel.setMaximumHeight(footer_button_height)
        if hasattr(self, "btn_settings_save"):
            self.btn_settings_save.setMinimumWidth(save_min_width)
            self.btn_settings_save.setMinimumHeight(footer_button_height)
            self.btn_settings_save.setMaximumHeight(footer_button_height)
        if hasattr(self, "settings_overview_text"):
            overview_text_width = 920 if density_mode == "wide" else 860 if density_mode == "roomy" else 760 if density_mode == "compact" else 680
            if is_very_wide_window:
                overview_text_width += 80
            if is_ultra_wide_window:
                overview_text_width += 80
            if is_cinema_wide_window:
                overview_text_width += 120
            self.settings_overview_text.setMaximumWidth(overview_text_width)
        if hasattr(self, "settings_hero_subtitle"):
            hero_subtitle_width = 1000 if density_mode == "wide" else 930 if density_mode == "roomy" else 840 if density_mode == "compact" else 720
            if is_very_wide_window:
                hero_subtitle_width += 100
            if is_ultra_wide_window:
                hero_subtitle_width += 100
            if is_cinema_wide_window:
                hero_subtitle_width += 140
            self.settings_hero_subtitle.setMaximumWidth(hero_subtitle_width)
        if hasattr(self, "settings_custom_row"):
            self.settings_custom_row.setHorizontalSpacing(custom_spacing)
            self.settings_custom_row.setVerticalSpacing(max(12, custom_spacing - 8))
            custom_cards = [
                card for card in (self.settings_left_field_card, self.settings_right_field_card)
                if not card.isHidden()
            ]
            if len(custom_cards) < 2:
                custom_columns, custom_stretches = 1, (1,)
            self._rebuild_settings_grid(
                self.settings_custom_row,
                custom_cards,
                custom_columns,
                custom_stretches,
            )
        if hasattr(self, "settings_precision_cards_layout"):
            self.settings_precision_cards_layout.setHorizontalSpacing(precision_spacing)
            self.settings_precision_cards_layout.setVerticalSpacing(max(12, precision_spacing - 2))
            self._rebuild_settings_grid(
                self.settings_precision_cards_layout,
                [self.settings_scan_card, self.settings_calibrate_card],
                precision_columns,
                precision_stretches,
            )
        if hasattr(self, "settings_right_field_card"):
            self.settings_right_field_card.setMaximumWidth(right_panel_max_width)
            self.settings_right_field_card.setMinimumWidth(right_panel_min_width)
            self.settings_right_field_card.setMinimumHeight(right_card_min_height)
        if hasattr(self, "settings_left_field_card"):
            self.settings_left_field_card.setMinimumHeight(left_card_min_height)
        if hasattr(self, "settings_scan_card"):
            self.settings_scan_card.setMinimumHeight(precision_card_min_height)
        if hasattr(self, "settings_calibrate_card"):
            self.settings_calibrate_card.setMinimumHeight(precision_card_min_height)
        if hasattr(self, "settings_adjust_card"):
            self.settings_adjust_card.setMinimumHeight(adjust_card_min_height)
        self._apply_settings_density_styles(density_mode, scale, is_short_window)

    def _create_settings_section_title(self, title):
        """创建设置模块卡片内标题。"""
        title_label = QLabel(title)
        title_label.setObjectName("settingsSectionTitle")
        return title_label

    def _create_settings_section_header(self, title, lead_label, summary_label):
        """创建设置模块卡片内部统一头部。"""
        header = QFrame()
        header.setObjectName("settingsSectionHeader")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._create_settings_section_title(title))
        layout.addWidget(lead_label)
        layout.addWidget(summary_label)
        return header

    def _create_settings_action_hint(self, text):
        """创建设置分区内的轻量操作提示。"""
        hint = QLabel(text)
        hint.setObjectName("settingsActionHint")
        return hint

    def _create_settings_form_label(self, text, width=96):
        """创建设置子卡中的统一表单标签。"""
        label = QLabel(text)
        label.setObjectName("settingsFieldLabel")
        label.setFixedWidth(width)
        return label

    def _create_settings_divider(self):
        """创建设置子卡内的轻量分隔线。"""
        divider = QFrame()
        divider.setObjectName("settingsFieldDivider")
        divider.setMinimumHeight(1)
        divider.setMaximumHeight(1)
        return divider

    def _apply_settings_density_styles(self, density_mode, scale, is_short_window):
        """按当前设置页密度统一标题、说明、导航与按钮字级。"""
        theme = Theme.LIGHT
        if density_mode == "wide":
            hero_title_size = 21
            hero_subtitle_size = 13
            hero_tag_size = 12
            overview_title_size = 17
            overview_text_size = 12
            section_title_size = 16
            lead_size = 12
            summary_size = 12
            field_title_size = 13
            field_label_size = 12
            field_note_size = 12
            hint_size = 11
            nav_font_size = 12
            nav_padding_v = 12
            nav_padding_h = 14
            nav_margin_v = 3
            metric_label_size = 11
            metric_value_size = 17
            quick_jump_font_size = 12
            footer_note_size = 12
        elif density_mode == "roomy":
            hero_title_size = 20
            hero_subtitle_size = 12
            hero_tag_size = 11
            overview_title_size = 16
            overview_text_size = 11
            section_title_size = 15
            lead_size = 11
            summary_size = 11
            field_title_size = 12
            field_label_size = 11
            field_note_size = 11
            hint_size = 11
            nav_font_size = 12
            nav_padding_v = 11
            nav_padding_h = 13
            nav_margin_v = 2
            metric_label_size = 11
            metric_value_size = 16
            quick_jump_font_size = 12
            footer_note_size = 11
        elif density_mode == "compact":
            hero_title_size = 19
            hero_subtitle_size = 12
            hero_tag_size = 11
            overview_title_size = 15
            overview_text_size = 11
            section_title_size = 15
            lead_size = 11
            summary_size = 11
            field_title_size = 12
            field_label_size = 11
            field_note_size = 11
            hint_size = 10
            nav_font_size = 11
            nav_padding_v = 10
            nav_padding_h = 12
            nav_margin_v = 2
            metric_label_size = 11
            metric_value_size = 15
            quick_jump_font_size = 11
            footer_note_size = 11
        else:
            hero_title_size = 18
            hero_subtitle_size = 11
            hero_tag_size = 10
            overview_title_size = 15
            overview_text_size = 11
            section_title_size = 14
            lead_size = 11
            summary_size = 11
            field_title_size = 12
            field_label_size = 11
            field_note_size = 11
            hint_size = 10
            nav_font_size = 11
            nav_padding_v = 10
            nav_padding_h = 11
            nav_margin_v = 2
            metric_label_size = 10
            metric_value_size = 15
            quick_jump_font_size = 11
            footer_note_size = 11

        if scale >= 1.5:
            hero_title_size += 1
            hero_subtitle_size += 1
            overview_title_size += 1
            section_title_size += 1
            lead_size += 1
            summary_size += 1
            field_title_size += 1
            field_label_size += 1
            field_note_size += 1
            nav_font_size += 1
            metric_value_size += 1
            quick_jump_font_size += 1
            footer_note_size += 1
            nav_padding_v += 1
            nav_padding_h += 1
        elif scale >= 1.25:
            hero_subtitle_size += 1
            overview_text_size += 1
            lead_size += 1
            summary_size += 1
            field_note_size += 1
            nav_padding_h += 1

        if is_short_window:
            hero_title_size = max(18, hero_title_size - 1)
            hero_subtitle_size = max(11, hero_subtitle_size - 1)
            section_title_size = max(14, section_title_size - 1)
            lead_size = max(11, lead_size - 1)
            summary_size = max(11, summary_size - 1)
            nav_padding_v = max(9, nav_padding_v - 1)
            nav_margin_v = 1

        if hasattr(self, "settings_hero_title"):
            self.settings_hero_title.setStyleSheet(
                f"color: {theme['text']}; font-size: {hero_title_size}px; font-weight: 700;"
            )
        if hasattr(self, "settings_hero_subtitle"):
            self.settings_hero_subtitle.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {hero_subtitle_size}px; line-height: 1.6;"
            )
        for label in [getattr(self, "lbl_settings_common_tag", None), getattr(self, "lbl_settings_advanced_tag", None)]:
            if label:
                label.setStyleSheet(
                    f"color: {theme['primary']}; background-color: #E9F1FB; border: 1px solid {theme['border']}; "
                    f"border-radius: 10px; padding: 6px 10px; font-size: {hero_tag_size}px; font-weight: 700;"
                )
        if hasattr(self, "settings_overview_title"):
            self.settings_overview_title.setStyleSheet(
                f"color: {theme['text']}; font-size: {overview_title_size}px; font-weight: 700;"
            )
        if hasattr(self, "settings_overview_text"):
            self.settings_overview_text.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {overview_text_size}px; line-height: 1.6;"
            )
        if hasattr(self, "settings_nav_hint"):
            self.settings_nav_hint.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {hint_size}px; font-weight: 700; letter-spacing: 0.05em;"
            )
        if hasattr(self, "settings_nav_subtitle"):
            self.settings_nav_subtitle.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {field_note_size}px; line-height: 1.6;"
            )
        if hasattr(self, "settings_sidebar_note"):
            self.settings_sidebar_note.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {field_note_size}px; line-height: 1.6;"
            )
        if hasattr(self, "settings_sidebar_status"):
            self.settings_sidebar_status.setStyleSheet(
                f"color: {theme['text_secondary']}; background-color: #F8FBFE; border: 1px solid {theme['border']}; "
                f"border-radius: 10px; padding: 8px 10px; font-size: {field_note_size}px; line-height: 1.6; font-weight: 600;"
            )
        if hasattr(self, "settings_footer_note"):
            self.settings_footer_note.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {footer_note_size}px; line-height: 1.6; padding-right: 8px;"
            )
        if hasattr(self, "settings_nav"):
            self.settings_nav.setStyleSheet(
                f"""
                QListWidget#settingsNav {{
                    background-color: transparent;
                    border: none;
                    outline: none;
                    padding: 0;
                }}
                QListWidget#settingsNav::item {{
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 10px;
                    padding: {nav_padding_v}px {nav_padding_h}px;
                    margin: {nav_margin_v}px 0;
                    color: {theme["text"]};
                    font-size: {nav_font_size}px;
                    font-weight: 600;
                }}
                QListWidget#settingsNav::item:selected {{
                    background-color: {theme["hover"]};
                    border-color: {theme["border"]};
                    color: {theme["primary"]};
                }}
                QListWidget#settingsNav::item:hover {{
                    background-color: {theme["hover"]};
                }}
                """
            )
        for label in self.findChildren(QLabel, "settingsMetricLabel"):
            label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {metric_label_size}px; font-weight: 700;"
            )
        for label in self.findChildren(QLabel, "settingsMetricValue"):
            label.setStyleSheet(
                f"color: {theme['text']}; font-size: {metric_value_size}px; font-weight: 700;"
            )
        for label in self.findChildren(QLabel, "settingsSectionTitle"):
            label.setStyleSheet(
                f"color: {theme['primary']}; font-size: {section_title_size}px; font-weight: 700; background-color: transparent;"
            )
        for label in self.findChildren(QLabel, "settingsSectionLead"):
            label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {lead_size}px; line-height: 1.7;"
            )
        for label in self.findChildren(QLabel, "settingsSectionSummary"):
            label.setStyleSheet(
                f"color: {theme['text_secondary']}; background-color: #F8FBFE; border: 1px solid {theme['border']}; "
                f"border-radius: 10px; padding: 8px 12px; font-size: {summary_size}px; font-weight: 600; line-height: 1.6;"
            )
        for label in self.findChildren(QLabel, "settingsFieldTitle"):
            label.setStyleSheet(
                f"color: {theme['text']}; font-size: {field_title_size}px; font-weight: 700;"
            )
        for label in self.findChildren(QLabel, "settingsFieldLabel"):
            label.setStyleSheet(
                f"color: {theme['text']}; font-size: {field_label_size}px; font-weight: 600;"
            )
        for label in self.findChildren(QLabel, "settingsFieldNote"):
            label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {field_note_size}px; line-height: 1.6;"
            )
        for label in self.findChildren(QLabel, "settingsActionHint"):
            label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {hint_size}px; font-weight: 700; letter-spacing: 0.04em;"
            )
        for button in getattr(self, "settings_quick_jump_buttons", []):
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: #FBFCFE;
                    color: {theme["text"]};
                    border: 1px solid {theme["border"]};
                    border-radius: 10px;
                    padding: 8px 14px;
                    font-size: {quick_jump_font_size}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {theme["hover"]};
                    border-color: {theme["primary"]};
                    color: {theme["primary"]};
                }}
                """
            )

