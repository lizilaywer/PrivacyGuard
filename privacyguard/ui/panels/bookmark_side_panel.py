# -*- coding: utf-8 -*-
"""cp_bookmark: PDF 书签栏左侧面板。

独立 QFrame 子类，承载书签的浏览/搜索/增删改/跳转交互。
通过信号与 MainWindow 解耦，不直接访问 MainWindow 状态。

布局（自上而下）：
    1. 标题行 "书签"
    2. 搜索框（过滤树，保留命中项的祖先链可见）
    3. 工具行：[+ 添加] [- 删除]
    4. QTreeWidget（核心，支持多层级、右键菜单、单击跳转）

数据契约：
    - load_toc(toc): 接收 fitz simple 格式 [[level, title, page], ...]
    - collect_toc() -> list: 收集当前树状态回 fitz TOC 格式（导出用）
    - 内部用 QTreeWidgetItem.setData(0, Qt.UserRole, page) 存页码
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QMenu,
)

from privacyguard.utils.helpers_bookmark import toc_to_tree_nodes, tree_nodes_to_toc


class BookmarkSidePanel(QFrame):
    """cp_bookmark: 书签栏左侧面板（搜索/增删改/跳转）。

    信号（MainWindow 接线）：
        bookmark_activated(int): 单击书签 → 跳转页码（1-based）
        toc_changed(): 用户编辑（增删改）后触发，MainWindow 据此缓存 self.toc_edited
        request_add_bookmark(): 点 + 按钮 → MainWindow 弹输入框取标题后回调 _add_bookmark
        request_add_sub_bookmark(object): 右键"添加子书签" → 传选中 item
        request_delete_bookmark(object): 右键"删除" / 点 − 按钮 → 传选中 item
        request_rename_bookmark(object): 右键"重命名" → 传选中 item
    """

    bookmark_activated = pyqtSignal(int)
    toc_changed = pyqtSignal()
    request_add_bookmark = pyqtSignal()
    request_add_sub_bookmark = pyqtSignal(object)
    request_delete_bookmark = pyqtSignal(object)
    request_rename_bookmark = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bookmarkSidePanel")
        self.setFixedWidth(280)
        self._build_ui()
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._apply_style()

    # === UI 构建 ===

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 标题行
        title = QLabel("书签")
        title.setObjectName("bookmarkTitle")
        layout.addWidget(title)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setObjectName("bookmarkSearch")
        self.search_input.setPlaceholderText("搜索书签…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_tree)
        layout.addWidget(self.search_input)

        # 工具行：[+ 添加] [- 删除]
        tool_row = QHBoxLayout()
        tool_row.setSpacing(6)
        self.btn_add = QPushButton("+ 添加")
        self.btn_add.setObjectName("bookmarkAddBtn")
        self.btn_add.setToolTip("添加书签到当前页")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.clicked.connect(self.request_add_bookmark.emit)
        tool_row.addWidget(self.btn_add)
        self.btn_del = QPushButton("− 删除")
        self.btn_del.setObjectName("bookmarkDelBtn")
        self.btn_del.setToolTip("删除选中书签")
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.clicked.connect(self._on_delete_clicked)
        tool_row.addWidget(self.btn_del)
        tool_row.addStretch()
        layout.addLayout(tool_row)

        # 树
        self.tree = QTreeWidget()
        self.tree.setObjectName("bookmarkTree")
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        self.tree.setUniformRowHeights(True)
        self.tree.setAnimated(True)
        self.tree.setAutoScroll(True)
        # 单击跳转
        self.tree.itemClicked.connect(self._on_item_clicked)
        # 右键菜单
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree, 1)

        # 空状态提示
        self.empty_label = QLabel("此 PDF 无书签\n点 “+ 添加” 创建")
        self.empty_label.setObjectName("bookmarkEmpty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()
        # v40.1.5（用户反馈）：stretch=1——树隐藏时接管剩余空间，
        # 头部（标题/搜索/按钮）始终钉在顶端，提示文字居中于余下区域
        layout.addWidget(self.empty_label, 1)

    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#bookmarkSidePanel {
                background: #F7FAFD; border: 1px solid #E4EBF3; border-radius: 10px;
            }
            QLabel#bookmarkTitle {
                color: #1D1D1F; font-size: 13px; font-weight: 600;
                background: transparent;
            }
            QLabel#bookmarkEmpty {
                color: #8E8E93; font-size: 12px; background: transparent;
                padding: 24px 0;
            }
            QLineEdit#bookmarkSearch {
                background: #FFFFFF; border: 1px solid #D1D1D6;
                border-radius: 6px; padding: 6px 8px; color: #1D1D1F;
            }
            QLineEdit#bookmarkSearch:focus { border: 1px solid #0A84FF; }
            QPushButton#bookmarkAddBtn, QPushButton#bookmarkDelBtn {
                background: #FFFFFF; border: 1px solid #C7C7CC;
                border-radius: 5px; padding: 4px 10px; color: #1D1D1F;
                font-size: 12px;
            }
            QPushButton#bookmarkAddBtn:hover, QPushButton#bookmarkDelBtn:hover {
                background: #F2F2F7;
            }
            QPushButton#bookmarkAddBtn:disabled, QPushButton#bookmarkDelBtn:disabled {
                opacity: 0.4;
            }
            QTreeWidget#bookmarkTree {
                background: #FFFFFF; border: 1px solid #E4EBF3;
                border-radius: 6px; outline: none;
            }
            QTreeWidget#bookmarkTree::item {
                padding: 4px 2px; color: #1D1D1F;
            }
            QTreeWidget#bookmarkTree::item:selected {
                background: #E8F0FE; color: #1D1D1F;
            }
            QTreeWidget#bookmarkTree::item:hover { background: #F2F7FF; }
        """)

    # === 数据加载 / 收集 ===

    def load_toc(self, toc):
        """加载 fitz TOC 到树。toc 为空时显示空状态。"""
        self.tree.clear()
        if not toc:
            self.empty_label.show()
            self.tree.hide()
            self.btn_del.setEnabled(False)
            return
        self.empty_label.hide()
        self.tree.show()
        nodes = toc_to_tree_nodes(toc)
        self._build_tree_items(nodes, self.tree.invisibleRootItem())
        self.tree.expandAll()
        self.btn_del.setEnabled(False)  # 无选中时禁用删除

    def _build_tree_items(self, nodes, parent_item):
        """递归构建 QTreeWidgetItem。"""
        for node in nodes:
            item = QTreeWidgetItem(parent_item)
            item.setText(0, node.get("title", ""))
            item.setData(0, Qt.ItemDataRole.UserRole, node.get("page", 1))
            if node.get("children"):
                self._build_tree_items(node["children"], item)

    def collect_toc(self):
        """收集当前树状态 → fitz TOC 格式 [[level, title, page], ...]。"""
        if self.tree.topLevelItemCount() == 0:
            return []
        nodes = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            child = root.child(i)
            nodes.append(self._item_to_node(child))
        return tree_nodes_to_toc(nodes)

    def _item_to_node(self, item):
        node = {
            "title": item.text(0),
            "page": item.data(0, Qt.ItemDataRole.UserRole) or 1,
            "children": [],
        }
        for i in range(item.childCount()):
            node["children"].append(self._item_to_node(item.child(i)))
        return node

    # === 交互回调 ===

    def _on_item_clicked(self, item, column):
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(page, int) and page >= 1:
            self.bookmark_activated.emit(page)
        self.btn_del.setEnabled(True)

    def _on_delete_clicked(self):
        item = self.tree.currentItem()
        if item is not None:
            self.request_delete_bookmark.emit(item)

    def _filter_tree(self, text):
        """搜索过滤：隐藏不匹配项，但保留命中项的祖先链可见。"""
        query = (text or "").strip().lower()
        if not query:
            # 清空搜索 → 全部显示
            it = QTreeWidgetItemIterator(self.tree)
            while it.value() is not None:
                it.value().setHidden(False)
                it += 1
            return
        # 先全部隐藏
        all_items = []
        it = QTreeWidgetItemIterator(self.tree)
        while it.value() is not None:
            all_items.append(it.value())
            it.value().setHidden(True)
            it += 1
        # 命中项 + 其祖先链显示
        for item in all_items:
            title = item.text(0).lower()
            if query in title:
                # 自己显示，祖先链显示
                cur = item
                while cur is not None:
                    cur.setHidden(False)
                    cur = cur.parent()

    def _show_context_menu(self, pos):
        """右键菜单：添加/添加子书签/重命名/删除/跳转。"""
        item = self.tree.itemAt(pos)
        menu = QMenu(self.tree)
        act_add = menu.addAction("添加书签")
        if item is not None:
            act_add_child = menu.addAction("添加子书签")
            menu.addSeparator()
            act_rename = menu.addAction("重命名书签")
            act_delete = menu.addAction("删除书签")
            menu.addSeparator()
            act_goto = menu.addAction("跳转到此页")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if item is None:
            # 无选中项时只允许添加
            if chosen is act_add:
                self.request_add_bookmark.emit()
            return
        if chosen is act_add:
            self.request_add_bookmark.emit()
        elif chosen is act_add_child:
            self.request_add_sub_bookmark.emit(item)
        elif chosen is act_rename:
            self.request_rename_bookmark.emit(item)
        elif chosen is act_delete:
            self.request_delete_bookmark.emit(item)
        elif chosen is act_goto:
            page = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(page, int) and page >= 1:
                self.bookmark_activated.emit(page)

    # === 外部调用的编辑操作（由 mixin 触发）===

    def add_bookmark_item(self, title, page, parent_item=None):
        """添加一个书签条目。

        parent_item=None → 加到根；否则加为 parent_item 的子节点。
        添加后自动选中并展开父节点，触发 toc_changed。
        """
        target_parent = parent_item if parent_item is not None else self.tree.invisibleRootItem()
        item = QTreeWidgetItem(target_parent)
        item.setText(0, title)
        item.setData(0, Qt.ItemDataRole.UserRole, page)
        self.tree.setCurrentItem(item)
        if parent_item is not None:
            parent_item.setExpanded(True)
        if self.tree.isHidden():
            self.tree.show()
            self.empty_label.hide()
        self.toc_changed.emit()

    def delete_item(self, item):
        """删除指定 item（含其子树）。"""
        if item is None:
            return
        parent = item.parent() or self.tree.invisibleRootItem()
        idx = parent.indexOfChild(item)
        if idx >= 0:
            parent.takeChild(idx)
        if self.tree.topLevelItemCount() == 0:
            self.empty_label.show()
            self.tree.hide()
            self.btn_del.setEnabled(False)
        self.toc_changed.emit()

    def rename_item(self, item, new_title):
        """重命名指定 item。"""
        if item is not None and isinstance(new_title, str) and new_title.strip():
            item.setText(0, new_title.strip())
            self.toc_changed.emit()

    def get_item_title(self, item):
        return item.text(0) if item is not None else ""

    def clear(self):
        """清空面板（文档关闭时调用）。"""
        self.tree.clear()
        self.search_input.clear()
        self.empty_label.hide()
        self.tree.show()
        self.btn_del.setEnabled(False)
