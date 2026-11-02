# -*- coding: utf-8 -*-
"""cp123: 提取模式右侧工具栏面板。

进入提取模式后显示在 canvas_layout 右侧（canvas_right 之右）的垂直工具列，
含新页/导出/删除/上移/下移/替换/上一页/下一页 等图标按钮。
样式与 pageOpsSidebar 一致（56px 宽，40×40 按钮，#F7FAFD 背景）。
"""
import os

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton

from privacyguard.utils.security import resource_path


class ExtractSidePanel(QFrame):
    """cp123: 提取模式右侧工具栏。

    信号（MainWindow 接线）：
        new_page_clicked / export_clicked / delete_clicked /
        move_up_clicked / move_down_clicked / replace_clicked /
        prev_page_clicked / next_page_clicked
    """

    new_page_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    delete_clicked = pyqtSignal()
    move_up_clicked = pyqtSignal()
    move_down_clicked = pyqtSignal()
    replace_clicked = pyqtSignal()
    prev_page_clicked = pyqtSignal()
    next_page_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("extractSidePanel")
        self.setFixedWidth(56)
        # cp124/cp125/cp126: 可拖动浮动面板（仅上下边缘空白区域可拖动）
        self._drag_offset = None  # 拖动偏移（None=未拖动）
        # cp125: 记住上次浮动位置（相对 parent），避免布局刷新重置
        self._last_floating_pos = None
        self.setMouseTracking(True)  # cp126: 追踪鼠标移动以动态切换光标
        sv = QVBoxLayout(self)
        sv.setContentsMargins(8, 10, 8, 10)
        sv.setSpacing(8)

        def _make_btn(icon_name, tooltip, signal):
            btn = QPushButton()
            btn.setIcon(QIcon(resource_path(os.path.join("assets", "icons", icon_name))))
            btn.setIconSize(QSize(22, 22))
            btn.setFixedSize(40, 40)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(signal.emit)
            sv.addWidget(btn)
            return btn

        # 片段管理组
        self.btn_new_page = _make_btn(
            "page_extract_new.svg", "新页：另起一个结果页（后续片段拼到新页）",
            self.new_page_clicked)
        self.btn_export = _make_btn(
            "page_extract_export.svg", "导出提取结果（保存为新 PDF）",
            self.export_clicked)
        sv.addSpacing(4)
        # 选中片段操作组（默认禁用，选中片段后启用）
        self.btn_delete = _make_btn(
            "page_extract_delete.svg", "删除选中片段",
            self.delete_clicked)
        self.btn_move_up = _make_btn(
            "page_extract_up.svg", "上移选中片段",
            self.move_up_clicked)
        self.btn_move_down = _make_btn(
            "page_extract_down.svg", "下移选中片段",
            self.move_down_clicked)
        self.btn_replace = _make_btn(
            "page_extract_replace.svg", "重新提取替换选中片段",
            self.replace_clicked)
        sv.addSpacing(4)
        # 结果页翻页组
        self.btn_prev_page = _make_btn(
            "page_rotate_left.svg", "上一结果页",
            self.prev_page_clicked)
        self.btn_next_page = _make_btn(
            "page_rotate_right.svg", "下一结果页",
            self.next_page_clicked)
        sv.addStretch()

        # 片段操作按钮默认禁用（需先选中片段）
        for btn in (self.btn_delete, self.btn_move_up,
                    self.btn_move_down, self.btn_replace):
            btn.setEnabled(False)
        # 翻页按钮默认禁用（需多结果页）
        self.btn_prev_page.setEnabled(False)
        self.btn_next_page.setEnabled(False)

        self.setStyleSheet("""
            QFrame#extractSidePanel {
                background: #F7FAFD; border: 1px solid #E4EBF3; border-radius: 10px;
            }
            QFrame#extractSidePanel QPushButton {
                border: none; background: transparent; border-radius: 8px; outline: none;
            }
            QFrame#extractSidePanel QPushButton:hover { background: #E8F0FE; }
            QFrame#extractSidePanel QPushButton:disabled { opacity: 0.35; }
        """)

    def set_segment_actions_enabled(self, enabled):
        """启用/禁用片段操作按钮（删除/上移/下移/替换）。"""
        for btn in (self.btn_delete, self.btn_move_up,
                    self.btn_move_down, self.btn_replace):
            btn.setEnabled(enabled)

    def set_page_nav_enabled(self, has_prev, has_next):
        """设置结果页翻页按钮启用态。"""
        self.btn_prev_page.setEnabled(has_prev)
        self.btn_next_page.setEnabled(has_next)

    # === cp124/cp125/cp126: 可拖动浮动面板 ===

    def _is_in_edge_zone(self, pos):
        """cp126: 判断点击位置是否在上下边缘空白区域（可拖动区）。

        按钮组的纵向范围取所有 QPushButton 的 [min_y, max_y+height]，
        点击 y 不在此范围（上方 margin 或下方 stretch）才算边缘。
        """
        btns = [b for b in self.findChildren(QPushButton)]
        if not btns:
            return True
        min_y = min(b.y() for b in btns)
        max_y = max(b.y() + b.height() for b in btns)
        y = pos.y()
        return y < min_y or y > max_y

    def mousePressEvent(self, event):
        """cp126: 仅在上下边缘空白区域按下才开始拖动。"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_in_edge_zone(event.position().toPoint()):
                self._drag_offset = event.position().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """拖动面板 / 动态切换光标。"""
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = self.mapToParent(event.position().toPoint()) - self._drag_offset
            parent = self.parent()
            if parent is not None:
                pw, ph = parent.width(), parent.height()
                new_x = max(0, min(new_pos.x(), pw - self.width()))
                new_y = max(0, min(new_pos.y(), ph - self.height()))
                self.move(new_x, new_y)
            else:
                self.move(new_pos)
            event.accept()
            return
        # cp126: 未拖动时根据是否在边缘区域动态切换光标
        if not event.buttons():
            if self._is_in_edge_zone(event.position().toPoint()):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """释放结束拖动。"""
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def show_as_floating(self, parent_widget, initial_pos=None):
        """cp124: 作为浮动面板显示在 parent_widget 上（脱离布局）。

        Args:
            parent_widget: 父窗口（QMainWindow，脱离 canvas 布局避免刷新重置位置）
            initial_pos: 初始位置（QPoint，相对 parent）；None=右上角默认
        """
        self.setParent(parent_widget)
        # v40.1.2 修复：setParent 后高度可能坍缩（只有 setFixedWidth，无高度约束），
        # adjustSize 让 QVBoxLayout 重算 sizeHint → 恢复完整高度显示全部按钮
        self.adjustSize()
        if self.height() < 100:
            # 兜底：如果 adjustSize 仍不够（极端情况），用 sizeHint 强制
            self.resize(self.sizeHint())
        # cp125: 优先用面板自己记忆的上次位置，其次用传入的 initial_pos，最后默认右上角
        if self._last_floating_pos is not None:
            self.move(self._last_floating_pos)
        elif initial_pos is not None:
            self.move(initial_pos)
        else:
            # cp127: 默认靠右侧边缘，垂直居中偏上（在操作台/工具栏之下，显示区域内）
            # y 取 parent 高度的 30%，避免太靠上超过操作台
            pw = parent_widget.width()
            ph = parent_widget.height()
            default_y = int(ph * 0.30)
            self.move(pw - self.width() - 20, default_y)
        self.raise_()
        self.show()

    def moveEvent(self, event):
        """cp125: 记住每次移动后的位置（相对 parent），用于布局刷新后恢复。"""
        super().moveEvent(event)
        if self.isVisible():
            self._last_floating_pos = self.pos()
