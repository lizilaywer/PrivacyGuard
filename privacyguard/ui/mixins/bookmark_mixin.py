# -*- coding: utf-8 -*-
"""cp_bookmark: MainWindow 书签协调逻辑（mixin）。

接口契约（需 MainWindow 提供的属性/方法）：
    属性：
        self.doc (fitz.Document | None): 当前打开的 PDF
        self.current_page (int): 当前页（0-based）
        self.bookmark_panel (BookmarkSidePanel): 书签面板实例
        self.btn_bookmark (QPushButton): 工具栏书签按钮
        self.toc_edited (list | None): 用户编辑后的 TOC 缓存（None=未编辑，用原 doc 的）
    方法：
        self.render_view(): 重渲染当前页（跳转后刷新）
        self._apply_fit_page(): 单页视图自适应重布局（面板切换后调用）
        self._relayout_page_grid(): 页面视图网格重布局
        self._set_info_bar_message(str): 状态栏提示

本 mixin 仅负责协调（读取 TOC / 跳转 / 增删改弹窗 / 缓存编辑），
所有 UI 控件本身在 BookmarkSidePanel 内。
"""
from PyQt6.QtWidgets import QInputDialog, QMessageBox
from PyQt6.QtCore import Qt, QTimer

from privacyguard.utils.helpers_bookmark import redact_toc_titles


class BookmarkMixin:
    """cp_bookmark: 书签功能的 MainWindow 协调层。"""

    # === 面板构建 / 切换 ===

    def _build_bookmark_panel(self):
        """构建书签面板（在 setup_ui 里调用，挂到 content_row 最左侧）。"""
        from privacyguard.ui.panels.bookmark_side_panel import BookmarkSidePanel
        panel = BookmarkSidePanel(self)
        panel.hide()  # 默认隐藏
        # 信号接线
        panel.bookmark_activated.connect(self._on_bookmark_activated)
        panel.toc_changed.connect(self._on_toc_changed)
        panel.request_add_bookmark.connect(self._add_bookmark_at_current)
        panel.request_add_sub_bookmark.connect(self._on_request_add_sub)
        panel.request_delete_bookmark.connect(self._on_request_delete)
        panel.request_rename_bookmark.connect(self._on_request_rename)
        return panel

    def toggle_bookmark_panel(self):
        """工具栏书签按钮：切换面板显示/隐藏（复刻 toggle_search_panel 模式）。"""
        if not getattr(self, "doc", None):
            QMessageBox.information(self, "提示", "请先打开 PDF 文档")
            return
        panel = getattr(self, "bookmark_panel", None)
        if panel is None:
            return
        show = not panel.isVisible()
        panel.setVisible(show)
        if show:
            # 首次展开若未加载过 TOC，触发加载
            if not getattr(self, "_toc_loaded", False):
                self._load_pdf_toc()
        # 切换后下一帧重布局受影响视图（与 search panel 对称）
        if getattr(self, "doc", None) and not getattr(self, "page_view_mode", False):
            QTimer.singleShot(0, self._apply_fit_page)
        elif getattr(self, "page_view_mode", False):
            QTimer.singleShot(0, self._relayout_page_grid)

    # === TOC 读取 / 缓存 ===

    def _load_pdf_toc(self):
        """从当前 doc 读取 TOC 到面板（应用当前脱敏开关/规则做预览）。

        cp_bookmark 预览：若开启"支持搜索识别书签栏"，面板显示脱敏后的标题；
        否则显示原始标题。原始 TOC 缓存在 self._toc_original 供刷新重算。
        """
        panel = getattr(self, "bookmark_panel", None)
        doc = getattr(self, "doc", None)
        if panel is None or doc is None:
            return
        try:
            toc = doc.get_toc(simple=True)
        except Exception:
            toc = []
        self._toc_original = toc  # 缓存原始 TOC（脱敏刷新的基线）
        display_toc = self._compute_display_toc(toc)
        panel.load_toc(display_toc)
        self.toc_edited = None  # 重置编辑缓存
        self._toc_loaded = True

    def _collect_active_toc_rules(self):
        """cp_bookmark: 收集当前所有生效的书签脱敏规则（预览/导出共用）。

        返回 custom_keyword_rules + _targeted_toc_rules 合并列表。
        这是预览与导出"所见即所导"的单一规则源，避免两边规则不一致导致泄漏。
        """
        rules = list(getattr(self, "custom_keyword_rules", []) or [])
        targeted = getattr(self, "_targeted_toc_rules", None)
        if isinstance(targeted, list):
            rules = rules + targeted
        return rules

    def _compute_display_toc(self, toc):
        """根据当前开关/规则计算应展示的 TOC（原始 or 脱敏后）。

        规则来源（开关开启时叠加，由 _collect_active_toc_rules 统一收集）：
          1. 高级设置的 custom_keyword_rules（持久规则）
          2. self._targeted_toc_rules（手动框选"全文遮罩"触发的临时规则）
        """
        if not toc:
            return []
        if not getattr(self, "bookmark_redact_enabled", False):
            return toc
        if not getattr(self, "_bookmark_redact_applied", False):
            # v40.1.4（用户反馈）：书签脱敏预览是动作驱动状态——未执行过
            # "智能脱敏/全文遮罩"时显示原始标题；仅改设置不动书签；
            # 重置文档清标志回到原始。导出回写不受此标志影响（按开关判断）。
            return toc
        rules = self._collect_active_toc_rules()
        if not rules:
            return toc
        return redact_toc_titles(toc, rules)

    def apply_targeted_terms_to_bookmarks(self, terms, replace_text):
        """cp_bookmark: 手动框选"全文遮罩"时，把识别词也应用到书签标题。

        仅当高级设置勾选了"支持搜索识别书签栏"时生效：把 terms 构造成
        find→replace 规则叠加到书签预览（与全文遮罩语义对称：页面正文遮罩 +
        书签标题替换/删除），并标记 toc_edited 以便导出时回写。
        """
        if not getattr(self, "bookmark_redact_enabled", False):
            return
        if not terms:
            return
        from privacyguard.utils.helpers_word_rules import build_targeted_keyword_rules
        self._targeted_toc_rules = list(getattr(self, "_targeted_toc_rules", []) or []) + build_targeted_keyword_rules(terms, replace_text)
        self._bookmark_redact_applied = True  # v40.1.4：全文遮罩=动作，置已应用
        # 基于原始 TOC 重算并刷新面板（手动框选触发的脱敏不弹确认框）
        panel = getattr(self, "bookmark_panel", None)
        if panel is None or not getattr(self, "_toc_loaded", False):
            return
        original = getattr(self, "_toc_original", [])
        display_toc = self._compute_display_toc(original)
        panel.load_toc(display_toc)
        self.toc_edited = True  # 标记：导出时回写脱敏后的 TOC

    def refresh_bookmark_preview(self, confirm_if_edited=True):
        """cp_bookmark: 重新计算脱敏预览并刷新面板。

        在开关切换 / 关键词规则变更后调用。若用户已手动编辑过书签，
        默认弹确认框（避免静默丢弃编辑）；confirm_if_edited=False 时直接刷新。
        """
        panel = getattr(self, "bookmark_panel", None)
        if panel is None or not getattr(self, "_toc_loaded", False):
            return
        if getattr(self, "toc_edited", None) and confirm_if_edited:
            confirm = QMessageBox.question(
                self, "刷新书签预览",
                "书签脱敏规则已变更。重新加载会丢失你在书签栏里的手动编辑，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if confirm != QMessageBox.StandardButton.Yes:
                return
        original = getattr(self, "_toc_original", [])
        # 安全审计 v40.1: 不清 _targeted_toc_rules——
        # 全文遮罩的临时规则代表用户已执行的操作，设置变更（如改扫描精度）
        # 不应让书签侧的脱敏效果静默丢失（否则导出会泄漏已遮罩的词）。
        # _targeted_toc_rules 只在 reset_document（重置）或文档关闭时清。
        display_toc = self._compute_display_toc(original)
        panel.load_toc(display_toc)
        self.toc_edited = None  # 刷新后重置编辑标记

    def _on_toc_changed(self):
        """面板内容变更 → 标记已编辑（导出时优先用编辑后的 TOC）。"""
        self.toc_edited = True  # 标记位：True 表示有未导出的编辑

    # === 跳转 ===

    def _safe_current_page_0based(self):
        """cp_bookmark 安全获取当前页（0-based），防御 current_page 为 None（文档关闭/Word 模式）。"""
        cp = getattr(self, "current_page", 0)
        if not isinstance(cp, int) or cp < 0:
            return 0
        return cp

    def _on_bookmark_activated(self, page):
        """单击书签 → 跳转到该页（page 为 1-based）。"""
        doc = getattr(self, "doc", None)
        # 防御：doc 关闭后 fitz 操作会崩（审计 P1 修复）
        if doc is None or page is None or getattr(doc, "is_closed", False):
            return
        try:
            total = len(doc)
        except Exception:
            return
        # page 是 1-based，转 0-based 并夹紧
        target = max(0, min(total - 1, page - 1))
        if target == self._safe_current_page_0based():
            return
        self.current_page = target
        if hasattr(self, "render_view"):
            self.render_view()
        if hasattr(self, "_set_info_bar_message"):
            self._set_info_bar_message(f"📍 跳转到第 {page} 页")

    def _sanitize_bookmark_title(self, title):
        """cp_bookmark 标题白名单化：剥离控制字符，限长（审计 C1 修复）。

        防止用户粘贴超长/含控制字符的标题破坏 PDF outline 或放大规则匹配开销。
        """
        if not isinstance(title, str):
            return ""
        import re as _re
        # 剥离 C0/C1 控制字符（保留 \t），限长 256
        cleaned = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", title).strip()
        return cleaned[:256]

    # === 增删改（弹窗取输入）===

    def _add_bookmark_at_current(self):
        """+ 按钮 / 右键"添加书签"：弹输入框取标题，加到当前页（根级）。"""
        doc = getattr(self, "doc", None)
        if doc is None or getattr(doc, "is_closed", False):
            return
        panel = getattr(self, "bookmark_panel", None)
        if panel is None:
            return
        cur_page_1based = self._safe_current_page_0based() + 1
        title, ok = QInputDialog.getText(
            self, "添加书签", f"书签标题（将指向第 {cur_page_1based} 页）:")
        if not ok:
            return
        title = self._sanitize_bookmark_title(title)
        if not title:
            return
        # 页码存 1-based（fitz TOC 约定）
        panel.add_bookmark_item(title, cur_page_1based, parent_item=None)

    def _on_request_add_sub(self, parent_item):
        """右键"添加子书签"：弹输入框，加为 parent_item 的子节点。"""
        doc = getattr(self, "doc", None)
        if doc is None or getattr(doc, "is_closed", False) or parent_item is None:
            return
        panel = getattr(self, "bookmark_panel", None)
        if panel is None:
            return
        raw_page = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(raw_page, int) or raw_page < 1:
            raw_page = self._safe_current_page_0based() + 1
        title, ok = QInputDialog.getText(
            self, "添加子书签",
            f"子书签标题（将指向第 {raw_page} 页，作为 \"{panel.get_item_title(parent_item)}\" 的子项）:")
        if not ok:
            return
        title = self._sanitize_bookmark_title(title)
        if not title:
            return
        panel.add_bookmark_item(title, raw_page, parent_item=parent_item)

    def _on_request_rename(self, item):
        """右键"重命名"：弹输入框预填当前标题。"""
        panel = getattr(self, "bookmark_panel", None)
        if panel is None or item is None:
            return
        old_title = panel.get_item_title(item)
        new_title, ok = QInputDialog.getText(
            self, "重命名书签", "新标题:", text=old_title)
        if not ok:
            return
        new_title = self._sanitize_bookmark_title(new_title)
        if not new_title:
            return
        panel.rename_item(item, new_title)

    def _on_request_delete(self, item):
        """右键"删除" / − 按钮：确认后删除。"""
        panel = getattr(self, "bookmark_panel", None)
        if panel is None or item is None:
            return
        title = panel.get_item_title(item)
        # 含子项时提示
        has_children = item.childCount() > 0
        msg = f"删除书签 \"{title}\"？" + (
            "\n\n注意：该项含子书签，将一并删除。" if has_children else "")
        confirm = QMessageBox.question(
            self, "删除书签", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes:
            return
        panel.delete_item(item)

    # === 文档关闭 / 切换清理 ===

    def _reset_bookmark_state(self):
        """文档关闭/切换时清理书签面板与缓存（在 close_file 类流程里调用）。"""
        panel = getattr(self, "bookmark_panel", None)
        if panel is not None:
            panel.hide()
            panel.clear()
        self.toc_edited = None
        self._toc_loaded = False
        self._toc_original = []
        self._targeted_toc_rules = None  # 手动框选"全文遮罩"触发的临时书签规则
        self._bookmark_redact_applied = False  # v40.1.4：换文档清"已应用"标志
