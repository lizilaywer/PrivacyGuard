"""设置对话框 - v37.0: 支持配置持久化"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QCheckBox, QComboBox, QSpinBox, QSlider,
    QScrollArea, QWidget, QGridLayout, QSizePolicy,
    QListWidget, QPlainTextEdit,
    QLineEdit, QApplication,
)
from PyQt6.QtCore import Qt

from theme import Theme
from privacyguard.utils.security import resource_path
from privacyguard.ui.mixins.settings_layout_mixin import SettingsLayoutMixin
from privacyguard.ui.mixins.settings_actions_mixin import SettingsActionsMixin
from privacyguard.utils.helpers_word_rules import (
    normalize_word_replace_rules,
    normalize_custom_keyword_rules,
    migrate_custom_keywords_to_rules,
)



class SettingsDialog(SettingsLayoutMixin, SettingsActionsMixin, QDialog):
    """设置对话框 - v37.0: 支持配置持久化"""

    def __init__(self, parent=None, current_rules=None, use_enhance=False, custom_keywords="",
                 scan_level=2.0, offset_x=0, offset_w=0, replacement_text="[已脱敏]",
                 word_replace_rules=None,
                 config_manager=None,
                 custom_keyword_rules=None,
                 manual_replace_prompt=False,
                 bookmark_redact_enabled=False,
                 doc_context=None,
                 default_rules=None):
        super().__init__(parent)
        self.config = config_manager
        # v40.1.4 修复：cp_bookmark 起 main.py open_settings 传 bookmark_redact_enabled=
        # 但本签名无此形参 → 设置对话框构造即 TypeError（打不开）。开关暂无独立 UI
        # 控件，值仅来自 config（redaction.bookmark_redact_enabled），此处透传保往返。
        self.bookmark_redact_enabled = bool(bookmark_redact_enabled)
        # DEFAULT_RULES: passed from caller (main.py module-level constant)
        self._default_rules = default_rules if default_rules is not None else {}
        # cp62: 当前打开的文档类型（'pdf'=PDF/图片、'word'=Word、None=未打开），
        # 用于按文档类型隐藏逻辑上用不到的设置模块
        self.doc_context = doc_context if doc_context in ("pdf", "word") else None
        # v37.7.13 cp43: 自定义关键词规则（持久化到 config.json）
        # custom_keywords 旧字符串字段保留作迁移源；新逻辑以 custom_keyword_rules 为准
        self.custom_keyword_rules = normalize_custom_keyword_rules(
            custom_keyword_rules if custom_keyword_rules else
            migrate_custom_keywords_to_rules(custom_keywords)
        )
        self.manual_replace_prompt = bool(manual_replace_prompt)

        # v37.4.1: 修复 Windows 深色模式下对话框显示问题
        # 设置窗口标志，确保对话框在深色系统主题下使用浅色样式
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        # v37.0: 从配置读取窗口尺寸，并结合当前屏幕做自适应约束
        if self.config:
            dialog_width = self.config.get("app.window.dialog_settings_width", 550)
            dialog_height = self.config.get("app.window.dialog_settings_height", 700)
        else:
            dialog_width, dialog_height = 550, 700

        self.setWindowTitle("高级设置")
        screen = QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            max_w = min(max(760, int(available.width() * 0.92)), available.width())
            max_h = min(max(620, int(available.height() * 0.90)), available.height())
            preferred_w = min(max_w, 1180)
            preferred_h = min(max_h, 900)
            min_w = min(900, max_w)
            min_h = min(680, max_h)
            width = max(min(min(max(dialog_width, 960), preferred_w), max_w), min_w)
            height = max(min(min(max(dialog_height, 760), preferred_h), max_h), min_h)
            self.resize(width, height)
            self.setMinimumSize(min_w, min_h)
            self.setMaximumSize(max_w, max_h)
        else:
            self.resize(980, 760)
            self.setMinimumSize(820, 620)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setSizeGripEnabled(True)
        self._settings_bound_window_handle = None

        # v37.4.1: 应用对话框主题样式
        self._apply_dialog_theme()

        self.selected_rules = []
        self.use_enhance = use_enhance
        self.custom_keywords = custom_keywords
        self.scan_level = scan_level
        self.offset_x = offset_x
        self.offset_w = offset_w
        self.replacement_text = replacement_text if isinstance(replacement_text, str) and replacement_text else "[已脱敏]"
        self.word_replace_rules = normalize_word_replace_rules(word_replace_rules or [], self.replacement_text)
        self.default_replacement_text = "[已脱敏]"
        self.recommended_rule_names = ["身份证号", "手机号码"]

        # v37.0: 从配置读取范围和标签
        # v37.7.18 cp50: 兜底默认值与 DEFAULT_CONFIG 对齐（1.0/1.5/2.0，默认 1.0）
        # 修复配置漂移：旧兜底为 1.5/2.0/3.0，与 config.json 不一致
        if self.config:
            offset_config = self.config.get("redaction.offset", {})
            x_range = offset_config.get("x_range", [-20, 20])
            w_range = offset_config.get("w_range", [-20, 20])
            scan_config = self.config.get("redaction.scan", {})
            available_levels = scan_config.get("available_levels", [1.0, 1.5, 2.0])
            level_labels = scan_config.get("level_labels", {
                "1.0": "普通 (1.0x)",
                "1.5": "标准 (1.5x 推荐)",
                "2.0": "高精 (2.0x)"
            })
        else:
            x_range = [-20, 20]
            w_range = [-20, 20]
            available_levels = [1.0, 1.5, 2.0]
            level_labels = {
                "1.0": "普通 (1.0x)",
                "1.5": "标准 (1.5x 推荐)",
                "2.0": "高精 (2.0x)"
            }

        self.x_range = x_range
        self.w_range = w_range
        self.available_levels = available_levels
        self.level_labels = level_labels

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(18, 16, 18, 18)
        outer_layout.setSpacing(14)

        hero = QFrame(self)
        hero.setObjectName("settingsHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(6)
        self.settings_hero_layout = hero_layout
        hero_title = QLabel("高级设置中心")
        hero_title.setObjectName("settingsTitle")
        self.settings_hero_title = hero_title
        hero_subtitle = QLabel("这里保存长期配置。PDF 的黑 / 白、单双页、缩放等即时操作，仍然放在主工作台里。")
        hero_subtitle.setObjectName("settingsSubtitle")
        hero_subtitle.setWordWrap(True)
        self.settings_hero_subtitle = hero_subtitle
        hero_layout.addWidget(hero_title)
        hero_layout.addWidget(hero_subtitle)
        hero_tag_layout = QHBoxLayout()
        hero_tag_layout.setSpacing(8)
        self.settings_hero_tag_layout = hero_tag_layout
        self.lbl_settings_common_tag = QLabel("常用设置：通用规则 / 关键词 / Word 替换")
        self.lbl_settings_common_tag.setObjectName("settingsHeroTag")
        self.lbl_settings_advanced_tag = QLabel("高级微调：扫描 / 覆盖 / OCR 检测框")
        self.lbl_settings_advanced_tag.setObjectName("settingsHeroTag")
        hero_tag_layout.addWidget(self.lbl_settings_common_tag)
        hero_tag_layout.addWidget(self.lbl_settings_advanced_tag)
        hero_tag_layout.addStretch()
        hero_layout.addLayout(hero_tag_layout)
        outer_layout.addWidget(hero)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)
        self.settings_body_layout = body_layout
        outer_layout.addLayout(body_layout, stretch=1)

        sidebar = QFrame(self)
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(236)
        self.settings_sidebar = sidebar
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)
        self.settings_sidebar_layout = sidebar_layout

        nav_hint = QLabel("设置导航")
        nav_hint.setObjectName("settingsHint")
        self.settings_nav_hint = nav_hint
        sidebar_layout.addWidget(nav_hint)
        nav_subtitle = QLabel("点击左侧即可快速跳转到对应模块。")
        nav_subtitle.setObjectName("settingsSidebarSubtle")
        nav_subtitle.setWordWrap(True)
        self.settings_nav_subtitle = nav_subtitle
        sidebar_layout.addWidget(nav_subtitle)
        sidebar_layout.addWidget(self._create_settings_divider())

        self.settings_nav = QListWidget()
        self.settings_nav.setObjectName("settingsNav")
        self.settings_nav.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._settings_nav_base_titles = ["1 通用规则", "2 自定义关键词", "3 扫描与微调", "4 OCR 检测框"]
        for title in self._settings_nav_base_titles:
            self.settings_nav.addItem(title)
        sidebar_layout.addWidget(self.settings_nav, stretch=1)

        sidebar_meta_card = QFrame()
        sidebar_meta_card.setObjectName("settingsSidebarMetaCard")
        self.settings_sidebar_meta_card = sidebar_meta_card
        sidebar_meta_layout = QVBoxLayout(sidebar_meta_card)
        sidebar_meta_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_meta_layout.setSpacing(10)
        sidebar_note = QLabel("建议：第一次使用只改规则和关键词；OCR 微调只在识别偏移时再调整。")
        sidebar_note.setWordWrap(True)
        sidebar_note.setObjectName("settingsSidebarNote")
        self.settings_sidebar_note = sidebar_note
        sidebar_meta_layout.addWidget(sidebar_note)
        sidebar_meta_layout.addWidget(self._create_settings_divider())
        self.settings_sidebar_status = QLabel("")
        self.settings_sidebar_status.setWordWrap(True)
        self.settings_sidebar_status.setObjectName("settingsSidebarStatus")
        sidebar_meta_layout.addWidget(self.settings_sidebar_status)
        sidebar_layout.addWidget(sidebar_meta_card)
        body_layout.addWidget(sidebar)

        content_scroll = QScrollArea(self)
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll = content_scroll

        content_widget = QWidget()
        self.content_widget = content_widget
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        overview_card = QFrame()
        overview_card.setObjectName("settingsOverview")
        self.settings_overview_card = overview_card
        overview_layout = QVBoxLayout(overview_card)
        overview_layout.setContentsMargins(18, 16, 18, 16)
        overview_layout.setSpacing(12)
        self.settings_overview_layout = overview_layout
        overview_title = QLabel("当前配置概览")
        overview_title.setObjectName("settingsOverviewTitle")
        self.settings_overview_title = overview_title
        overview_text = QLabel("先看这里，就能快速知道当前默认规则、关键词、Word 替换和 OCR 微调处于什么状态。")
        overview_text.setObjectName("settingsOverviewText")
        overview_text.setWordWrap(True)
        self.settings_overview_text = overview_text
        overview_layout.addWidget(overview_title)
        overview_layout.addWidget(overview_text)

        overview_metrics_layout = QGridLayout()
        overview_metrics_layout.setHorizontalSpacing(10)
        overview_metrics_layout.setVerticalSpacing(10)
        self.settings_overview_metrics_layout = overview_metrics_layout
        self.lbl_metric_rules = None
        self.lbl_metric_keywords = None
        self.lbl_metric_word_rules = None
        self.lbl_metric_ocr = None
        self.settings_metric_cards = []
        for key, title in [
            ("rules", "通用规则"),
            ("keywords", "自定义关键词"),
            ("word_rules", "Word 规则"),
            ("ocr", "OCR 调节"),
        ]:
            metric_card, metric_value = self._create_settings_metric_card(title)
            setattr(self, f"lbl_metric_{key}", metric_value)
            self.settings_metric_cards.append(metric_card)
            overview_metrics_layout.addWidget(metric_card, 0, len(self.settings_metric_cards) - 1)
        overview_layout.addLayout(overview_metrics_layout)

        overview_actions_layout = QGridLayout()
        overview_actions_layout.setHorizontalSpacing(8)
        overview_actions_layout.setVerticalSpacing(8)
        self.settings_overview_actions_layout = overview_actions_layout
        self._settings_quick_jump_titles = [
            ("去看通用规则", "通用规则"),
            ("去看关键词", "关键词"),
            ("去看扫描微调", "扫描微调"),
            ("去看 OCR", "OCR"),
        ]
        self.settings_quick_jump_buttons = []
        for row, (title, _short_title) in enumerate(self._settings_quick_jump_titles):
            jump_btn = QPushButton(title)
            jump_btn.setObjectName("settingsQuickJumpButton")
            jump_btn.clicked.connect(lambda _checked=False, target_row=row: self.settings_nav.setCurrentRow(target_row))
            jump_btn.setMinimumHeight(32)
            self.settings_quick_jump_buttons.append(jump_btn)
            overview_actions_layout.addWidget(jump_btn, 0, row)
        overview_layout.addLayout(overview_actions_layout)
        layout.addWidget(overview_card)

        # 1. 规则
        box_rules = QFrame()
        box_rules.setObjectName("settingsSectionCard")
        v_box = QVBoxLayout(box_rules)
        v_box.setContentsMargins(16, 16, 16, 16)
        v_box.setSpacing(12)
        rules_lead = QLabel("勾选后的规则会作为默认智能识别规则。第一次使用建议至少保留身份证号和手机号。")
        rules_lead.setObjectName("settingsSectionLead")
        rules_lead.setWordWrap(True)
        self.lbl_rules_summary = QLabel("")
        self.lbl_rules_summary.setObjectName("settingsSectionSummary")
        self.lbl_rules_summary.setWordWrap(True)
        v_box.addWidget(self._create_settings_section_header("1. 通用规则", rules_lead, self.lbl_rules_summary))
        rules_actions = QHBoxLayout()
        rules_actions.setSpacing(8)
        rules_actions.addWidget(self._create_settings_action_hint("快捷操作"))
        btn_rules_recommended = QPushButton("恢复推荐勾选")
        btn_rules_recommended.setObjectName("settingsInlineButton")
        btn_rules_recommended.clicked.connect(self._apply_recommended_rules)
        rules_actions.addWidget(btn_rules_recommended)
        btn_rules_all = QPushButton("全部勾选")
        btn_rules_all.setObjectName("settingsInlineButton")
        btn_rules_all.clicked.connect(self._select_all_rules)
        rules_actions.addWidget(btn_rules_all)
        btn_rules_clear = QPushButton("全部清空")
        btn_rules_clear.setObjectName("settingsInlineButton")
        btn_rules_clear.clicked.connect(self._clear_all_rules)
        rules_actions.addWidget(btn_rules_clear)
        rules_actions.addStretch()
        v_box.addLayout(rules_actions)
        rules_columns = QHBoxLayout()
        rules_columns.setSpacing(24)
        rules_left_col = QVBoxLayout()
        rules_left_col.setSpacing(6)
        rules_right_col = QVBoxLayout()
        rules_right_col.setSpacing(6)
        self.checks = {}
        rule_items = list(self._default_rules.items())
        split_index = (len(rule_items) + 1) // 2
        for index, (name, pattern) in enumerate(rule_items):
            cb = QCheckBox(name)
            if current_rules and pattern in current_rules: cb.setChecked(True)
            elif not current_rules and name in ["身份证号", "手机号码"]: cb.setChecked(True)
            self.checks[name] = cb
            cb.toggled.connect(self._refresh_rule_summary)
            if index < split_index:
                rules_left_col.addWidget(cb)
            else:
                rules_right_col.addWidget(cb)
        rules_left_col.addStretch()
        rules_right_col.addStretch()
        rules_columns.addLayout(rules_left_col, stretch=1)
        rules_columns.addLayout(rules_right_col, stretch=1)
        v_box.addLayout(rules_columns)
        layout.addWidget(box_rules)

        # 2. 关键词 + 统一替换文本 + Word 替换规则入口
        box_custom = QFrame()
        box_custom.setObjectName("settingsSectionCard")
        v_custom = QVBoxLayout(box_custom)
        v_custom.setContentsMargins(16, 16, 16, 16)
        v_custom.setSpacing(12)
        custom_lead = QLabel("这里适合录入姓名、单位、案号等固定内容；Word 替换规则适合更精细的定向替换。")
        custom_lead.setObjectName("settingsSectionLead")
        custom_lead.setWordWrap(True)
        self.settings_custom_lead = custom_lead
        self.lbl_custom_summary = QLabel("")
        self.lbl_custom_summary.setObjectName("settingsSectionSummary")
        self.lbl_custom_summary.setWordWrap(True)
        v_custom.addWidget(self._create_settings_section_header("2. 自定义关键词", custom_lead, self.lbl_custom_summary))
        custom_row = QGridLayout()
        custom_row.setHorizontalSpacing(28)
        custom_row.setVerticalSpacing(14)
        self.settings_custom_row = custom_row

        left_panel_widget = QFrame()
        left_panel_widget.setObjectName("settingsFieldCard")
        self.settings_left_field_card = left_panel_widget
        left_panel_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_panel = QVBoxLayout(left_panel_widget)
        left_panel.setContentsMargins(16, 16, 16, 16)
        left_panel.setSpacing(10)
        left_title = QLabel("关键词列表")
        left_title.setObjectName("settingsFieldTitle")
        left_note = QLabel("每行一个关键词。如需替换文本，用 | 分隔，例如：张三|张某某\n不带 | 表示纯遮罩不叠加替换文本。")
        left_note.setObjectName("settingsFieldNote")
        left_note.setWordWrap(True)
        self.settings_left_field_note = left_note
        left_panel.addWidget(left_title)
        left_panel.addWidget(left_note)
        left_panel.addWidget(self._create_settings_divider())
        custom_actions = QHBoxLayout()
        custom_actions.setSpacing(8)
        custom_actions.addWidget(self._create_settings_action_hint("快捷操作"))
        btn_import_kw = QPushButton("导入JSON")
        btn_import_kw.setObjectName("settingsInlineButton")
        btn_import_kw.clicked.connect(self._import_custom_keyword_rules_json)
        custom_actions.addWidget(btn_import_kw)
        btn_export_kw = QPushButton("导出JSON")
        btn_export_kw.setObjectName("settingsInlineButton")
        btn_export_kw.clicked.connect(self._export_custom_keyword_rules_json)
        custom_actions.addWidget(btn_export_kw)
        custom_actions.addStretch()
        left_panel.addLayout(custom_actions)
        # v37.7.13 cp43: 关键词文本框（每行 "find|replace"，无 | 表示纯遮罩）
        self.txt_custom_rules = QPlainTextEdit()
        self.txt_custom_rules.setMinimumHeight(160)
        self.txt_custom_rules.setPlaceholderText("每行一个关键词\n张三|张某某\n李四\n案号2024-001|案件XXX")
        left_panel.addWidget(self.txt_custom_rules)
        # 加载已有规则到文本框
        self._load_custom_keyword_rules_to_text()
        # 文本变更触发摘要刷新
        self.txt_custom_rules.textChanged.connect(self._refresh_custom_summary)
        # v40.1.4（用户反馈）：输入框正下方单行——左侧两个勾选框紧贴输入框
        # （去掉中间整行留白），右侧"清空"按钮顶部与第一个勾选框上沿平齐
        self.cb_manual_replace_prompt = QCheckBox("手动框选时输入替换文本（取消则纯遮罩）")
        self.cb_manual_replace_prompt.setChecked(self.manual_replace_prompt)
        self.cb_manual_replace_prompt.stateChanged.connect(self._refresh_custom_summary)
        # v40.1.4 恢复：书签栏脱敏开关（v40.1.0 cp_bookmark 原有，08a2c51 重写
        # 设置布局时随 prompt_row 简化被误删；Word 上下文隐藏见 settings_actions_mixin）
        self.cb_bookmark_redact = QCheckBox("支持搜索识别书签栏")
        self.cb_bookmark_redact.setChecked(self.bookmark_redact_enabled)
        self.cb_bookmark_redact.setToolTip(
            "勾选后：导出 PDF 时，把上方关键词规则应用到书签（目录）标题——\n"
            "设置了\"记录|下载\"则书签中\"记录\"改写为\"下载\"；\n"
            "仅设关键词（无替换文本）则从书签中删除该词。"
        )
        self.cb_bookmark_redact.stateChanged.connect(self._refresh_custom_summary)
        checks_box = QVBoxLayout()
        checks_box.setContentsMargins(0, 0, 0, 0)
        checks_box.setSpacing(8)
        checks_box.addWidget(self.cb_manual_replace_prompt)
        checks_box.addWidget(self.cb_bookmark_redact)
        # v40.1.4（用户反馈 #3）：一键清空关键词输入框（顶格与左侧勾选框上沿平齐）
        btn_clear_kw = QPushButton("清空")
        btn_clear_kw.setObjectName("settingsInlineButton")
        btn_clear_kw.setToolTip("清空上方关键词输入框的全部内容（需点\"确定\"才生效）")
        btn_clear_kw.clicked.connect(self.txt_custom_rules.clear)
        opts_row = QHBoxLayout()
        opts_row.setContentsMargins(0, 0, 0, 0)
        opts_row.setSpacing(8)
        opts_row.addLayout(checks_box, 1)
        opts_row.addWidget(btn_clear_kw, 0, Qt.AlignmentFlag.AlignTop)
        left_panel.addLayout(opts_row)
        custom_row.addWidget(left_panel_widget, 0, 0)

        right_panel_widget = QFrame()
        right_panel_widget.setObjectName("settingsFieldCard")
        right_panel_widget.setMinimumWidth(320)
        self.settings_right_field_card = right_panel_widget
        right_panel_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_panel = QVBoxLayout(right_panel_widget)
        right_panel.setContentsMargins(16, 16, 16, 16)
        right_panel.setSpacing(10)
        right_title = QLabel("Word 替换规则")
        right_title.setObjectName("settingsFieldTitle")
        right_note = QLabel("这里适合维护更精细的 exact / regex 替换规则，批量 Word 会直接复用。")
        right_note.setObjectName("settingsFieldNote")
        right_note.setWordWrap(True)
        right_panel.addWidget(right_title)
        right_panel.addWidget(right_note)
        right_panel.addWidget(self._create_settings_divider())
        replacement_row = QHBoxLayout()
        replacement_row.setSpacing(8)
        replacement_row.addWidget(self._create_settings_form_label("统一替换文本:", 102))
        self.input_replacement_text = QLineEdit(self.replacement_text)
        self.input_replacement_text.setPlaceholderText("[已脱敏]")
        self.input_replacement_text.setMinimumWidth(240)
        self.input_replacement_text.textChanged.connect(self._refresh_custom_summary)
        replacement_row.addWidget(self.input_replacement_text)
        right_panel.addLayout(replacement_row)
        replacement_actions = QHBoxLayout()
        replacement_actions.setSpacing(8)
        replacement_actions.addWidget(self._create_settings_action_hint("快捷操作"))
        btn_reset_replacement = QPushButton("恢复默认替换词")
        btn_reset_replacement.setObjectName("settingsInlineButton")
        btn_reset_replacement.clicked.connect(self._reset_replacement_text)
        replacement_actions.addWidget(btn_reset_replacement)
        replacement_actions.addStretch()
        right_panel.addLayout(replacement_actions)

        right_panel.addSpacing(8)
        right_panel.addWidget(self._create_settings_form_label("Word 替换规则:", 120))
        self.btn_edit_word_rules = QPushButton("打开替换规则设置")
        self.btn_edit_word_rules.clicked.connect(self._open_word_rules_editor)
        self.btn_edit_word_rules.setMinimumHeight(34)
        right_panel.addWidget(self.btn_edit_word_rules)

        self.lbl_word_rule_count = QLabel("")
        self.lbl_word_rule_count.setObjectName("settingsFieldNote")
        self.lbl_word_rule_count.setWordWrap(True)
        right_panel.addWidget(self.lbl_word_rule_count)
        word_rules_hint = QLabel("批量 Word 替换会直接复用这里的规则结构，不需要另外维护一套。")
        word_rules_hint.setWordWrap(True)
        word_rules_hint.setObjectName("settingsFieldNote")
        right_panel.addWidget(word_rules_hint)
        right_panel.addStretch()

        custom_row.addWidget(right_panel_widget, 0, 1)
        v_custom.addLayout(custom_row)
        layout.addWidget(box_custom)

        # 3. 精度与微调
        box_enhance = QFrame()
        box_enhance.setObjectName("settingsSectionCard")
        v_enhance = QVBoxLayout(box_enhance)
        v_enhance.setContentsMargins(16, 16, 16, 16)
        v_enhance.setSpacing(12)
        precision_lead = QLabel("只有当扫描偏移、覆盖范围不理想时再调整这里；默认设置更适合大多数文档。")
        precision_lead.setObjectName("settingsSectionLead")
        precision_lead.setWordWrap(True)
        self.lbl_precision_summary = QLabel("")
        self.lbl_precision_summary.setObjectName("settingsSectionSummary")
        self.lbl_precision_summary.setWordWrap(True)
        v_enhance.addWidget(self._create_settings_section_header("3. 精度与微调", precision_lead, self.lbl_precision_summary))
        precision_actions = QHBoxLayout()
        precision_actions.setSpacing(8)
        precision_actions.addWidget(self._create_settings_action_hint("快捷操作"))
        btn_reset_precision = QPushButton("恢复推荐值")
        btn_reset_precision.setObjectName("settingsInlineButton")
        btn_reset_precision.clicked.connect(self._reset_precision_defaults)
        precision_actions.addWidget(btn_reset_precision)
        precision_actions.addStretch()
        v_enhance.addLayout(precision_actions)

        precision_cards = QGridLayout()
        precision_cards.setHorizontalSpacing(16)
        precision_cards.setVerticalSpacing(14)
        self.settings_precision_cards_layout = precision_cards

        scan_card = QFrame()
        scan_card.setObjectName("settingsFieldCard")
        self.settings_scan_card = scan_card
        scan_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scan_card_layout = QVBoxLayout(scan_card)
        scan_card_layout.setContentsMargins(16, 16, 16, 16)
        scan_card_layout.setSpacing(10)
        scan_title = QLabel("扫描模式")
        scan_title.setObjectName("settingsFieldTitle")
        scan_note = QLabel("正常情况下保持默认即可。模式越高越细，但速度也会更慢。")
        scan_note.setObjectName("settingsFieldNote")
        scan_note.setWordWrap(True)
        scan_card_layout.addWidget(scan_title)
        scan_card_layout.addWidget(scan_note)
        scan_card_layout.addWidget(self._create_settings_divider())
        h_precision = QHBoxLayout()
        h_precision.addWidget(self._create_settings_form_label("当前模式:", 86))
        self.combo_precision = QComboBox()
        # v37.0: 从配置动态添加扫描级别选项
        for level in self.available_levels:
            label = self.level_labels.get(str(level), f"{level}x")
            self.combo_precision.addItem(label, level)
        idx = self.combo_precision.findData(scan_level)
        self.combo_precision.setCurrentIndex(idx if idx >=0 else 1)
        self.combo_precision.currentIndexChanged.connect(self._refresh_precision_summary)
        h_precision.addWidget(self.combo_precision)
        scan_card_layout.addLayout(h_precision)
        scan_card_layout.addStretch()
        precision_cards.addWidget(scan_card, 0, 0)

        calibrate_card = QFrame()
        calibrate_card.setObjectName("settingsFieldCard")
        self.settings_calibrate_card = calibrate_card
        calibrate_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        calibrate_card_layout = QVBoxLayout(calibrate_card)
        calibrate_card_layout.setContentsMargins(16, 16, 16, 16)
        calibrate_card_layout.setSpacing(10)
        calibrate_title = QLabel("覆盖微调")
        calibrate_title.setObjectName("settingsFieldTitle")
        calibrate_note = QLabel("只有在遮罩范围明显偏左、偏宽时再调，默认值更适合多数 PDF。")
        calibrate_note.setObjectName("settingsFieldNote")
        calibrate_note.setWordWrap(True)
        calibrate_card_layout.addWidget(calibrate_title)
        calibrate_card_layout.addWidget(calibrate_note)
        calibrate_card_layout.addWidget(self._create_settings_divider())
        h_calibrate = QHBoxLayout()
        v_cal_1 = QVBoxLayout()
        label_offset_x = QLabel("向左修正(pt):")
        label_offset_x.setObjectName("settingsFieldLabel")
        v_cal_1.addWidget(label_offset_x)
        self.spin_offset_x = QSpinBox()
        self.spin_offset_x.setRange(x_range[0], x_range[1])
        self.spin_offset_x.setValue(offset_x)
        self.spin_offset_x.valueChanged.connect(self._refresh_precision_summary)
        v_cal_1.addWidget(self.spin_offset_x)

        v_cal_2 = QVBoxLayout()
        label_offset_w = QLabel("宽度收缩(pt):")
        label_offset_w.setObjectName("settingsFieldLabel")
        v_cal_2.addWidget(label_offset_w)
        self.spin_offset_w = QSpinBox()
        self.spin_offset_w.setRange(w_range[0], w_range[1])
        self.spin_offset_w.setValue(offset_w)
        self.spin_offset_w.valueChanged.connect(self._refresh_precision_summary)
        v_cal_2.addWidget(self.spin_offset_w)

        h_calibrate.addLayout(v_cal_1)
        h_calibrate.addLayout(v_cal_2)
        calibrate_card_layout.addLayout(h_calibrate)
        calibrate_tip = QLabel("提示：对扫描区域 / 嵌入图片区域生效")
        calibrate_tip.setObjectName("settingsFieldNote")
        calibrate_tip.setWordWrap(True)
        calibrate_card_layout.addWidget(calibrate_tip)

        self.cb_enhance = QCheckBox("开启图像增强 (仅针对手写体)")
        self.cb_enhance.setChecked(use_enhance)
        self.cb_enhance.toggled.connect(self._refresh_precision_summary)
        calibrate_card_layout.addWidget(self.cb_enhance)
        calibrate_card_layout.addStretch()
        precision_cards.addWidget(calibrate_card, 0, 1)

        v_enhance.addLayout(precision_cards)
        layout.addWidget(box_enhance)

        # v37.4.0: 4. OCR 检测框调节（移除引擎选择，只保留 RapidOCR）
        box_ocr = QFrame()
        box_ocr.setObjectName("settingsSectionCard")
        v_ocr = QVBoxLayout(box_ocr)
        v_ocr.setContentsMargins(16, 16, 16, 16)
        v_ocr.setSpacing(12)
        ocr_lead = QLabel("检测框只在 OCR 结果偏大或偏小时再调。负值扩大框，正值收缩框，0 表示保持原样。")
        ocr_lead.setObjectName("settingsSectionLead")
        ocr_lead.setWordWrap(True)
        self.lbl_ocr_summary = QLabel("")
        self.lbl_ocr_summary.setObjectName("settingsSectionSummary")
        self.lbl_ocr_summary.setWordWrap(True)
        v_ocr.addWidget(self._create_settings_section_header("4. OCR 检测框调节", ocr_lead, self.lbl_ocr_summary))
        ocr_actions = QHBoxLayout()
        ocr_actions.setSpacing(8)
        ocr_actions.addWidget(self._create_settings_action_hint("快捷操作"))
        btn_reset_ocr = QPushButton("恢复 0%")
        btn_reset_ocr.setObjectName("settingsInlineButton")
        btn_reset_ocr.clicked.connect(self._reset_ocr_adjustment)
        ocr_actions.addWidget(btn_reset_ocr)
        ocr_actions.addStretch()
        v_ocr.addLayout(ocr_actions)

        adjust_card = QFrame()
        adjust_card.setObjectName("settingsFieldCard")
        self.settings_adjust_card = adjust_card
        adjust_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        adjust_card_layout = QVBoxLayout(adjust_card)
        adjust_card_layout.setContentsMargins(16, 16, 16, 16)
        adjust_card_layout.setSpacing(10)
        adjust_title = QLabel("检测框调节")
        adjust_title.setObjectName("settingsFieldTitle")
        adjust_note = QLabel("当 OCR 框偏大或偏小时再调。负值扩大，正值收缩。")
        adjust_note.setObjectName("settingsFieldNote")
        adjust_note.setWordWrap(True)
        adjust_card_layout.addWidget(adjust_title)
        adjust_note.setObjectName("settingsFieldNote")
        adjust_card_layout.addWidget(adjust_note)
        adjust_card_layout.addWidget(self._create_settings_divider())

        # v37.3.5: 检测框大小调节（支持负值扩大、正值收缩）
        h_adjust = QHBoxLayout()
        h_adjust.addWidget(self._create_settings_form_label("检测框调节:", 96))

        # 读取当前配置值（新配置名）
        adjust_ratio = self.config.get("ocr.box_adjust_ratio", 0.0) if self.config else 0.0

        # v37.7.18 cp50: 滑块范围动态读取 ocr.box_adjust_range 配置（修复死配置）
        box_adjust_range = self.config.get("ocr.box_adjust_range", [-0.3, 0.5]) if self.config else [-0.3, 0.5]
        slider_min = int(box_adjust_range[0] * 100)  # -0.3 -> -30
        slider_max = int(box_adjust_range[1] * 100)  # 0.5 -> 50

        self.slider_adjust = QSlider(Qt.Orientation.Horizontal)
        self.slider_adjust.setRange(slider_min, slider_max)
        self.slider_adjust.setValue(int(adjust_ratio * 100))
        self.slider_adjust.valueChanged.connect(self._on_adjust_changed)
        h_adjust.addWidget(self.slider_adjust)

        self.label_adjust_value = QLabel(f"{int(adjust_ratio * 100)}%")
        self.label_adjust_value.setMinimumWidth(40)
        h_adjust.addWidget(self.label_adjust_value)

        adjust_card_layout.addLayout(h_adjust)

        adjust_info = QLabel("提示：负值扩大，正值收缩，0保持原样（默认0%）")
        adjust_info.setObjectName("settingsFieldNote")
        adjust_info.setWordWrap(True)
        adjust_card_layout.addWidget(adjust_info)

        # 说明标签
        info_text = (
            "\n引擎说明：\n"
            "• RapidOCR：默认 OCR 引擎，速度快，适合大文档批量处理\n"
        )

        info = QLabel(info_text)
        info.setObjectName("settingsFieldNote")
        info.setWordWrap(True)
        adjust_card_layout.addWidget(info)
        v_ocr.addWidget(adjust_card)
        layout.addWidget(box_ocr)

        layout.addStretch(1)
        content_scroll.setWidget(content_widget)
        body_layout.addWidget(content_scroll, stretch=1)

        footer = QFrame(self)
        footer.setObjectName("settingsFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 14, 18, 14)
        footer_layout.setSpacing(12)
        self.settings_footer_layout = footer_layout

        footer_note = QLabel('修改完成后点击"保存设置"，取消不会影响当前已生效配置。')
        footer_note.setObjectName("settingsFooterNote")
        footer_note.setWordWrap(True)
        self.settings_footer_note = footer_note
        footer_layout.addWidget(footer_note, stretch=1)

        footer_actions = QHBoxLayout()
        footer_actions.setSpacing(10)
        # cp88/cp90: 清理使用痕迹（隐私清理入口，含草稿/临时文件/预览缓存/日志）
        btn_clear_drafts = QPushButton("清理使用痕迹")
        btn_clear_drafts.setObjectName("settingsSecondaryButton")
        btn_clear_drafts.setToolTip("清理本应用在本机留下的使用痕迹（脱敏草稿/临时文件/预览缓存/日志）")
        btn_clear_drafts.clicked.connect(self._open_trace_clean)
        btn_clear_drafts.setMinimumHeight(40)
        btn_clear_drafts.setMinimumWidth(130)
        footer_actions.addWidget(btn_clear_drafts)
        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("settingsSecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setMinimumWidth(116)
        self.btn_settings_cancel = btn_cancel
        footer_actions.addWidget(btn_cancel)

        btn_ok = QPushButton("保存设置")
        btn_ok.setObjectName("settingsPrimaryButton")
        btn_ok.clicked.connect(self.save_settings)
        btn_ok.setMinimumHeight(40)
        btn_ok.setMinimumWidth(164)
        self.btn_settings_save = btn_ok
        footer_actions.addWidget(btn_ok)
        footer_layout.addLayout(footer_actions)
        outer_layout.addWidget(footer)
        self._settings_sections = [box_rules, box_custom, box_enhance, box_ocr]
        self._settings_nav_syncing = False
        self.settings_nav.currentRowChanged.connect(self._scroll_to_settings_section)
        self.content_scroll.verticalScrollBar().valueChanged.connect(self._sync_settings_nav_from_scroll)
        self.settings_nav.setCurrentRow(0)
        self._apply_doc_context_visibility()
        self._refresh_word_rule_summary()
        self._refresh_rule_summary()
        self._refresh_precision_summary()
        self._refresh_ocr_summary()
        self._refresh_settings_layout_density()

    def _apply_dialog_theme(self):
        """应用对话框浅色主题样式（v37.4.1: 修复 Windows 深色模式显示问题）"""
        theme = Theme.LIGHT

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme["background"]};
                font-family: {Theme.FONT_FAMILY};
            }}
            QWidget {{
                background-color: {theme["background"]};
                color: {theme["text"]};
                font-family: {Theme.FONT_FAMILY};
            }}
            QFrame#settingsHero {{
                background-color: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 18px;
            }}
            QFrame#settingsOverview {{
                background-color: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 18px;
            }}
            QFrame#settingsMetricCard {{
                background-color: #F8FBFE;
                border: 1px solid {theme["border"]};
                border-radius: 12px;
            }}
            QLabel#settingsTitle {{
                color: {theme["text"]};
                font-size: 20px;
                font-weight: 700;
            }}
            QLabel#settingsOverviewTitle {{
                color: {theme["text"]};
                font-size: 16px;
                font-weight: 700;
            }}
            QLabel#settingsOverviewText {{
                color: {theme["text_secondary"]};
                font-size: 11px;
                line-height: 1.6;
            }}
            QLabel#settingsMetricLabel {{
                color: {theme["text_secondary"]};
                font-size: 11px;
                font-weight: 700;
            }}
            QLabel#settingsMetricValue {{
                color: {theme["text"]};
                font-size: 16px;
                font-weight: 700;
            }}
            QPushButton#settingsQuickJumpButton {{
                background-color: #FBFCFE;
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#settingsQuickJumpButton:hover {{
                background-color: {theme["hover"]};
                border-color: {theme["primary"]};
                color: {theme["primary"]};
            }}
            QLabel#settingsSubtitle {{
                color: {theme["text_secondary"]};
                font-size: 12px;
                line-height: 1.6;
            }}
            QLabel#settingsHeroTag {{
                color: {theme["primary"]};
                background-color: #E9F1FB;
                border: 1px solid {theme["border"]};
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            QFrame#settingsSidebar {{
                background-color: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 18px;
            }}
            QFrame#settingsSidebarMetaCard {{
                background-color: #FBFCFE;
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}
            QFrame#settingsFooter {{
                background-color: {theme["surface"]};
                border: 1px solid {theme["border"]};
                border-radius: 16px;
            }}
            QFrame#settingsFieldCard, QWidget#settingsInnerPanel {{
                background-color: #FBFCFE;
                border: 1px solid {theme["border"]};
                border-radius: 14px;
            }}
            QLabel#settingsHint {{
                color: {theme["text_secondary"]};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.05em;
            }}
            QLabel#settingsSidebarNote {{
                color: {theme["text_secondary"]};
                font-size: 11px;
                line-height: 1.6;
            }}
            QLabel#settingsSidebarSubtle {{
                color: {theme["text_secondary"]};
                font-size: 11px;
                line-height: 1.6;
            }}
            QLabel#settingsSidebarStatus {{
                color: {theme["text_secondary"]};
                background-color: #F8FBFE;
                border: 1px solid {theme["border"]};
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 11px;
                line-height: 1.6;
                font-weight: 600;
            }}
            QLabel#settingsFooterNote {{
                color: {theme["text_secondary"]};
                font-size: 11px;
                line-height: 1.6;
                padding-right: 8px;
            }}
            QLabel#settingsFieldTitle {{
                color: {theme["text"]};
                font-size: 12px;
                font-weight: 700;
            }}
            QLabel#settingsFieldLabel {{
                color: {theme["text"]};
                font-size: 11px;
                font-weight: 600;
            }}
            QLabel#settingsFieldNote {{
                color: {theme["text_secondary"]};
                font-size: 11px;
                line-height: 1.6;
            }}
            QFrame#settingsFieldDivider {{
                background-color: {theme["border"]};
                border: none;
            }}
            QLabel#settingsSectionLead {{
                color: {theme["text_secondary"]};
                font-size: 11px;
                line-height: 1.7;
            }}
            QLabel#settingsSectionSummary {{
                color: {theme["text_secondary"]};
                background-color: #F8FBFE;
                border: 1px solid {theme["border"]};
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 11px;
                font-weight: 600;
                line-height: 1.6;
            }}
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
                padding: 10px 12px;
                margin: 2px 0;
                color: {theme["text"]};
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
            QFrame#settingsSectionCard {{
                background-color: {theme["surface"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: 16px;
            }}
            QFrame#settingsSectionHeader {{
                background-color: transparent;
                border: none;
            }}
            QLabel#settingsSectionTitle {{
                color: {theme["primary"]};
                font-size: 15px;
                font-weight: 700;
                background-color: transparent;
            }}
            QLabel {{
                color: {theme["text"]};
                background-color: transparent;
            }}
            QCheckBox {{
                color: {theme['text']};
                background-color: transparent;
                spacing: 8px;
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 15px;
                height: 15px;
                border: 1.2px solid {theme['border']};
                border-radius: 3px;
                background-color: {theme['surface']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {theme['primary']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme['primary']};
                border-color: {theme['primary']};
                image: url("{resource_path('assets/check_white.svg').replace(chr(92), '/')}");
            }}
            QTextEdit {{
                background-color: {theme["surface"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                padding: 8px;
            }}
            QLineEdit {{
                background-color: {theme["surface"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 22px;
            }}
            QComboBox {{
                background-color: {theme["surface"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                padding: 6px;
                min-width: 100px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme["surface"]};
                color: {theme["text"]};
                selection-background-color: {theme["primary"]};
            }}
            QSpinBox {{
                background-color: {theme["surface"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                padding: 6px;
            }}
            QSlider {{
                background-color: transparent;
            }}
            QSlider::groove:horizontal {{
                border: none;
                height: 4px;
                background-color: {theme["border"]};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background-color: {theme["primary"]};
                border: none;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QPushButton {{
                background-color: {theme["primary"]};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {theme["primary"]};
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                background-color: {theme["pressed"]};
            }}
            QPushButton#settingsSecondaryButton {{
                background-color: #FBFCFE;
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                padding: 10px 18px;
            }}
            QPushButton#settingsSecondaryButton:hover {{
                background-color: {theme["hover"]};
                border-color: {theme["primary"]};
            }}
            QLabel#settingsActionHint {{
                color: {theme["text_secondary"]};
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton#settingsInlineButton {{
                background-color: #FBFCFE;
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                border-radius: 9px;
                padding: 7px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#settingsInlineButton:hover {{
                background-color: {theme["hover"]};
                border-color: {theme["primary"]};
                color: {theme["primary"]};
            }}
        """)
