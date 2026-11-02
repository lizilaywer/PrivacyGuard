"""Page view / multi-page grid methods extracted from MainWindow.

This module defines PageViewMixin, a pure method-container mixin.
MainWindow inherits from it to gain all page-grid overview, thumbnail
rendering, page selection, and page-structure operation methods.

All self.xxx references resolve to MainWindow attributes at runtime.
"""

import os
import time

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFrame, QPushButton,
    QLabel, QGridLayout, QMessageBox, QFileDialog,
    QInputDialog, QLineEdit,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QRectF, QRect, QSize, QTimer

from privacyguard.utils.security import resource_path
from privacyguard.ui.widgets import PageGridScrollArea, SinglePageCanvas
from privacyguard.utils.helpers_pdf import (
    _hit_rect,
    transform_hit_rect_for_rotation,
    shift_page_data_for_insert,
    shift_page_data_for_delete,
    shift_page_set_for_insert,
    shift_page_set_for_delete,
    clamp_grid_columns,
)
from privacyguard.utils.logger import get_logger

logger = get_logger(__name__)


class PageViewMixin:
    """Mixin providing page-grid overview and page-structure operations.

    Interface contract — MainWindow must provide these attributes/methods:

    Attributes (set in MainWindow.__init__ or setup_ui):
        doc: fitz.Document | None — 当前打开的 PDF 文档
        page_data: dict — 每页遮罩数据 {page_idx: {ocr: [...], manual: [...]}}
        current_page: int — 当前页索引
        page_view_mode: bool — 是否处于多页网格视图
        grid_columns: int — 网格列数
        mask_color: str — 当前遮罩颜色
        _grid_canvases: dict — 页面画布缓存
        _grid_pix_cache: dict — 缩略图像素缓存
        _grid_selected: set — 选中页面集合
        _grid_render_queue: list — 渲染队列

    Methods (defined in MainWindow):
        _capture_undo_state(structural=False) — 压入撤销快照
        _set_info_bar_message(msg) — 状态栏消息
        _clear_info_bar_message() — 清除状态栏
        render_view() — 重绘当前单页视图
        _render_page_to_canvas(canvas, page_idx, zoom) — 渲染指定页到画布
        on_rect_removed(page_idx, rect_idx, is_manual) — 遮罩移除回调
        _handle_manual_region_prompt(canvas, rect) — 手动框选弹窗
        _toggle_dual_toolbar(visible) — 切换双栏工具栏
        clamp_zoom(zoom) -> float — 限制缩放范围
    """

    def _build_page_view_container(self):
        """cp67: 构建页面视图容器：左侧线条图标页面操作工具栏 + 多页网格滚动区。"""
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(10)

        sidebar = QFrame()
        sidebar.setObjectName("pageOpsSidebar")
        sidebar.setFixedWidth(56)
        self.page_ops_sidebar = sidebar
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(8, 10, 8, 10)
        sv.setSpacing(8)

        def _make_op_btn(icon_name, tooltip, handler):
            btn = QPushButton()
            btn.setIcon(QIcon(resource_path(os.path.join("assets", "icons", icon_name))))
            btn.setIconSize(QSize(22, 22))
            btn.setFixedSize(40, 40)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(handler)
            btn.setEnabled(False)
            sv.addWidget(btn)
            return btn

        self.btn_page_rotate_left = _make_op_btn(
            "page_rotate_left.svg", "左转 90°（逆时针，遮罩跟随旋转）",
            lambda: self._rotate_selected_pages(-90))
        self.btn_page_rotate_right = _make_op_btn(
            "page_rotate_right.svg", "右转 90°（顺时针，遮罩跟随旋转）",
            lambda: self._rotate_selected_pages(90))
        self.btn_page_insert = _make_op_btn(
            "page_insert.svg", "在选中页之后插入空白页",
            self._insert_blank_page_after_selected)
        self.btn_page_insert_file = _make_op_btn(
            "page_insert_file.svg", "在选中页之后插入文件（PDF / 图片）",
            self._insert_file_after_selected)
        self.btn_page_delete = _make_op_btn(
            "page_delete.svg", "删除选中页（不可撤销，需确认）",
            self._delete_selected_pages)
        sv.addStretch()
        row.addWidget(sidebar)

        self.page_grid_scroll = PageGridScrollArea()
        self.page_grid_scroll.setWidgetResizable(True)
        self.page_grid_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.page_grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.page_grid_content = QWidget()
        self.page_grid_content.setObjectName("pageGridContent")
        self.page_grid_layout = QGridLayout(self.page_grid_content)
        self.page_grid_layout.setContentsMargins(14, 14, 14, 14)
        self.page_grid_layout.setHorizontalSpacing(14)
        self.page_grid_layout.setVerticalSpacing(14)
        self.page_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.page_grid_scroll.setWidget(self.page_grid_content)
        self.page_grid_scroll.ctrl_wheel.connect(self._on_grid_ctrl_wheel)
        self.page_grid_scroll.verticalScrollBar().valueChanged.connect(
            lambda _v: self._grid_refresh_timer.start())
        row.addWidget(self.page_grid_scroll, 1)

        container.setStyleSheet("""
            QFrame#pageOpsSidebar {
                background: #F7FAFD; border: 1px solid #E4EBF3; border-radius: 10px;
            }
            QFrame#pageOpsSidebar QPushButton {
                border: none; background: transparent; border-radius: 8px; outline: none;
            }
            QFrame#pageOpsSidebar QPushButton:hover { background: #E8F0FE; }
            QFrame#pageOpsSidebar QPushButton:pressed { background: #D8E6FB; }
            QWidget#pageGridContent { background: #EDF1F6; }
            QFrame#pageGridCard {
                background: #FFFFFF; border: 1px solid #D9E2EC; border-radius: 8px;
            }
            QFrame#pageGridCard[selected="true"] {
                border: 2px solid #007AFF; background: #F5F9FF;
            }
            QLabel#pageGridPageLabel {
                color: #6E6E73; font-size: 11px; background: transparent;
            }
        """)
        return container

    def _toggle_page_view_toolbar(self, checked=False):
        """cp67: 工具栏"页面"按钮入口。"""
        self.set_page_view_mode(bool(checked))

    def set_page_view_mode(self, enabled):
        """cp67: 进入/退出页面视图（多页网格总览），与单页/双页视图互斥。"""
        enabled = bool(enabled) and bool(self.doc)
        if hasattr(self, "cb_page_view") and self.cb_page_view.isChecked() != enabled:
            self.cb_page_view.blockSignals(True)
            self.cb_page_view.setChecked(enabled)
            self.cb_page_view.blockSignals(False)
        if enabled == self.page_view_mode:
            return
        self.page_view_mode = enabled
        if enabled:
            # 与双页互斥
            if self.dual_view:
                self._toggle_dual_toolbar(False)
            self.scroll.hide()
            self.page_view_container.show()
            self._set_info_bar_message("📄 页面视图：Ctrl+滚轮调每行页数，单击选中（Ctrl 多选），双击回单页")
            self._rebuild_page_grid()
        else:
            self.page_view_container.hide()
            self.scroll.show()
            self.grid_selected_pages.clear()
            self._grid_anchor_page = None
            # cp68: 停掉 pending 的网格刷新定时器（刷新函数自身也有 page_view_mode 守卫，双重防御）
            self._grid_refresh_timer.stop()
            self._grid_hq_timer.stop()
            # cp76: 停止分帧渲染队列
            self._grid_render_timer.stop()
            self._grid_render_queue = []
            self._clear_info_bar_message()
            if self.doc:
                self.render_view()
        self._refresh_page_ops_buttons()

    def _on_grid_ctrl_wheel(self, step):
        """cp67: Ctrl+滚轮调节列数。

        cp68 手势阻尼：同一滚轮手势内放大到 1 列后继续放大停在边界不切换；
        松开 Ctrl / 停止滚动（超过 _ZOOM_GESTURE_GAP）后的新手势再放大，才跨越
        分界切回单页视图。
        cp68 性能：列数变化用缓存 pixmap 快速缩放出过渡帧，停止滚动后去抖高清重渲染。
        """
        if not self.page_view_mode:
            return
        now = time.time()
        new_gesture = (now - self._ctrl_zoom_last_ts) > self._ZOOM_GESTURE_GAP
        self._ctrl_zoom_last_ts = now
        if step > 0 and self.grid_columns <= 1:
            if new_gesture:
                # 新手势跨越分界：退回单页视图并适应页面
                # cp68: fit_page 内统一处理"退出页面视图 + 下一帧自适应"时序
                self.fit_page()
            return
        viewport_w = self.page_grid_scroll.viewport().width()
        new_cols = clamp_grid_columns(self.grid_columns - step, viewport_w, self._GRID_MIN_THUMB)
        if new_cols != self.grid_columns:
            self.grid_columns = new_cols
            self._relayout_page_grid(fast=True)

    def _grid_thumb_width(self):
        """cp67: 按当前列数计算单页缩略宽度（px）。"""
        viewport_w = max(240, self.page_grid_scroll.viewport().width())
        cols = max(1, self.grid_columns)
        spacing = 14
        card_w = (viewport_w - 28 - spacing * (cols - 1) - 6) // cols
        return max(110, int(card_w) - 14)

    def _rebuild_page_grid(self):
        """cp67: 重建页面网格卡片（打开新文档/页数变化后调用）。"""
        while self.page_grid_layout.count():
            item = self.page_grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._grid_canvases.clear()
        self._grid_cards.clear()
        self._invalidate_grid_cache()
        # cp76: canvas 已重建，丢弃旧分帧渲染队列
        self._grid_render_timer.stop()
        self._grid_render_queue = []
        # cp68: 页面结构可能变化，纵横比缓存与 Shift 范围选锚点同步失效
        self._grid_page_aspects.clear()
        self._grid_anchor_page = None
        if not self.doc:
            return
        total = len(self.doc)
        self.grid_selected_pages = {p for p in self.grid_selected_pages if 0 <= p < total}
        for idx in range(total):
            card = QFrame()
            card.setObjectName("pageGridCard")
            card.setProperty("selected", idx in self.grid_selected_pages)
            cv = QVBoxLayout(card)
            cv.setContentsMargins(6, 6, 6, 4)
            cv.setSpacing(3)
            canvas = SinglePageCanvas(idx)
            canvas.grid_mode = True
            canvas.page_clicked.connect(self._on_grid_page_clicked)
            canvas.page_activated.connect(self._on_grid_page_activated)
            canvas.rect_removed.connect(self.on_rect_removed)
            # cp65 手动框选识别流程在网格内同样可用（页码取 canvas.page_index）
            canvas.manual_region_prompt.connect(
                lambda rect, c=canvas: self._handle_manual_region_prompt(c, rect))
            cv.addWidget(canvas, 0, Qt.AlignmentFlag.AlignHCenter)
            page_lbl = QLabel(str(idx + 1))
            page_lbl.setObjectName("pageGridPageLabel")
            page_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(page_lbl)
            self._grid_canvases[idx] = canvas
            self._grid_cards[idx] = card
        self._relayout_page_grid()
        self._refresh_page_ops_buttons()

    def _grid_page_aspect(self, idx):
        """cp68: 页面纵横比（display 坐标），带缓存避免重排时全量 fitz 访问。"""
        aspect = self._grid_page_aspects.get(idx)
        if aspect is None:
            try:
                rect = self.doc[idx].rect
                aspect = rect.height / max(1.0, rect.width)
            except Exception:
                aspect = 1.414
            self._grid_page_aspects[idx] = aspect
        return aspect

    def _relayout_page_grid(self, fast=False):
        """cp67: 按当前列数重排卡片并重设占位尺寸，随后刷新可见缩略。

        cp68: fast=True（滚轮连续缩放）时用缓存 pixmap 快速缩放出过渡帧，
        去抖后再高清重渲染；避免每步滚轮都走 fitz 渲染导致卡顿。
        """
        if not self.doc or not self._grid_cards:
            return
        viewport_w = self.page_grid_scroll.viewport().width()
        self.grid_columns = clamp_grid_columns(self.grid_columns, viewport_w, self._GRID_MIN_THUMB)
        cols = self.grid_columns
        thumb_w = self._grid_thumb_width()
        for idx in sorted(self._grid_cards):
            card = self._grid_cards[idx]
            canvas = self._grid_canvases.get(idx)
            if canvas is not None:
                aspect = self._grid_page_aspect(idx)
                canvas.setFixedSize(thumb_w, max(48, int(thumb_w * aspect)))
            self.page_grid_layout.addWidget(card, idx // cols, idx % cols)
        self._update_grid_selection_styles()
        if fast:
            self._apply_fast_scaled_thumbs(thumb_w)
            self._grid_hq_timer.start()
        else:
            self._grid_refresh_timer.start()

    def _apply_fast_scaled_thumbs(self, thumb_w):
        """cp68: 列数缩放过渡帧：用已缓存 pixmap 快速缩放到新宽度。

        zoom_scale 同步设为新宽对应的 zoom，遮罩层坐标随之对齐；
        高清重渲染由 _grid_hq_timer 去抖触发。
        """
        if not self.page_view_mode or not self.doc:
            return
        viewport = self.page_grid_scroll.viewport()
        top = self.page_grid_scroll.verticalScrollBar().value()
        visible = QRect(0, top - viewport.height(), viewport.width() + 200,
                        viewport.height() * 3)
        for idx, canvas in self._grid_canvases.items():
            card = self._grid_cards.get(idx)
            if card is None or not card.geometry().intersects(visible):
                continue
            cached = self._grid_pix_cache.get(idx)
            entry = self.page_data.get(idx)
            if cached is None or entry is None or not self._is_canvas_valid(canvas):
                continue
            src_pixmap = cached[1]
            if src_pixmap is None or src_pixmap.isNull():
                continue
            scaled = src_pixmap.scaledToWidth(thumb_w, Qt.TransformationMode.FastTransformation)
            try:
                zoom = min(2.0, thumb_w / max(1.0, self.doc[idx].rect.width))
            except Exception:
                continue
            self._safe_canvas_update(canvas, scaled, zoom, entry['ocr'], entry['manual'])
            canvas.setFixedSize(scaled.size())

    def _refresh_visible_grid_thumbs(self, overlay_only=False):
        """cp67: 懒渲染可见区域（±一屏余量）的页面缩略图。

        overlay_only=True 时不重画 pixmap，仅 update() 重绘遮罩层（共享列表已变）。
        """
        if not self.page_view_mode or not self.doc or not self._grid_canvases:
            return
        viewport = self.page_grid_scroll.viewport()
        top = self.page_grid_scroll.verticalScrollBar().value()
        visible = QRect(0, top - viewport.height(), viewport.width() + 200,
                        viewport.height() * 3)
        thumb_w = self._grid_thumb_width()
        render_queue = []  # cp76: 本次可见且需高清渲染的页（分帧处理）
        for idx, canvas in self._grid_canvases.items():
            card = self._grid_cards.get(idx)
            if card is None or not card.geometry().intersects(visible):
                continue
            if overlay_only:
                pix = canvas.pixmap() if self._is_canvas_valid(canvas) else None
                if pix is not None and not pix.isNull():
                    # cp75: 遮罩色可能刚切换（黑/白/取色），overlay 重绘前同步到网格
                    # canvas（set_mask_color 内部自带 update()，与单页路径对称；
                    # 旧逻辑仅 update() 导致切色后页面视图不实时生效）
                    self._safe_canvas_set_mask_color(canvas, self.current_color)
                continue
            entry = self.page_data.get(idx)
            if entry is None:
                continue
            try:
                zoom = min(2.0, thumb_w / max(1.0, self.doc[idx].rect.width))
            except Exception:
                continue
            pixmap = None
            cached = self._grid_pix_cache.get(idx)
            if cached is not None and abs(cached[0] - zoom) < 1e-4:
                pixmap = cached[1]
                self._safe_canvas_update(canvas, pixmap, zoom, entry['ocr'], entry['manual'])
                self._safe_canvas_set_mask_color(canvas, self.current_color)
                canvas.manual_replace_prompt = self.manual_replace_prompt
                if self._is_canvas_valid(canvas):
                    canvas.setFixedSize(pixmap.size())
            else:
                # cp76: 缓存 miss 不再同步渲染（多页连续 fitz 高清渲染阻塞主线程
                # 造成白屏卡顿）：有旧 zoom 缓存先快速缩放出过渡帧（遮罩 zoom 同步
                # 保对齐），高清渲染排队分帧处理
                if cached is not None and self._is_canvas_valid(canvas):
                    fast_pix = cached[1].scaledToWidth(
                        thumb_w, Qt.TransformationMode.FastTransformation)
                    fast_zoom = fast_pix.width() / max(1.0, self.doc[idx].rect.width)
                    self._safe_canvas_update(canvas, fast_pix, fast_zoom,
                                             entry['ocr'], entry['manual'])
                    self._safe_canvas_set_mask_color(canvas, self.current_color)
                    canvas.setFixedSize(fast_pix.size())
                render_queue.append(idx)
        if not overlay_only:
            # cp76: 重建队列（而非追加），避免多次触发重复排队/残留陈旧页码
            self._grid_render_queue = render_queue
            if render_queue:
                self._grid_render_timer.start()

    def _process_grid_render_queue(self):
        """cp76: 分帧渲染网格缩略图：每帧一页，渲染完继续排下一帧。

        守卫：退出页面视图/文档关闭/队列空时自然终止；页码越界或 canvas
        已重建时跳过该页；渲染前二次检查缓存（可能已被其它路径渲染）。
        """
        if not self.page_view_mode or not self.doc or not self._grid_render_queue:
            self._grid_render_queue = []
            return
        idx = self._grid_render_queue.pop(0)
        canvas = self._grid_canvases.get(idx)
        entry = self.page_data.get(idx)
        try:
            total = len(self.doc)
        except Exception:
            total = 0
        if canvas is not None and entry is not None and 0 <= idx < total:
            thumb_w = self._grid_thumb_width()
            try:
                zoom = min(2.0, thumb_w / max(1.0, self.doc[idx].rect.width))
            except Exception:
                zoom = None
            if zoom:
                cached = self._grid_pix_cache.get(idx)
                if cached is None or abs(cached[0] - zoom) >= 1e-4:
                    pixmap = self._render_page_to_canvas(canvas, idx, zoom)
                    if pixmap is not None:
                        self._grid_cache_put(idx, zoom, pixmap)
                        if self._is_canvas_valid(canvas):
                            canvas.setFixedSize(pixmap.size())
        if self._grid_render_queue:
            self._grid_render_timer.start()

    def _grid_cache_put(self, idx, zoom, pixmap):
        """cp67: 缩略图 LRU 缓存写入。"""
        if idx in self._grid_pix_cache:
            try:
                self._grid_cache_order.remove(idx)
            except ValueError:
                pass
        self._grid_pix_cache[idx] = (zoom, pixmap)
        self._grid_cache_order.append(idx)
        while len(self._grid_cache_order) > self._GRID_CACHE_MAX:
            old = self._grid_cache_order.pop(0)
            self._grid_pix_cache.pop(old, None)

    def _invalidate_grid_cache(self, page_idx=None):
        """cp67: 失效缩略图缓存（页面操作/重建后调用）。"""
        if page_idx is None:
            self._grid_pix_cache.clear()
            self._grid_cache_order.clear()
        else:
            self._grid_pix_cache.pop(page_idx, None)
            try:
                self._grid_cache_order.remove(page_idx)
            except ValueError:
                pass

    def _on_grid_page_clicked(self, page_idx, ctrl, shift):
        """cp67: 网格单击选中（Ctrl 多选切换）。

        cp68: Shift 范围选——以最近一次非 Shift 点击为锚点，Shift+点击选中锚点到
        当前页之间（含两端）的全部页；Ctrl+Shift 则把该范围并入已有选区。
        """
        anchor = getattr(self, "_grid_anchor_page", None)
        if shift and anchor is not None and self.doc is not None:
            total = len(self.doc)
            lo = max(0, min(anchor, page_idx))
            hi = min(total - 1, max(anchor, page_idx))
            range_pages = set(range(lo, hi + 1))
            if ctrl:
                self.grid_selected_pages |= range_pages
            else:
                self.grid_selected_pages = range_pages
            # 锚点保持不变（与资源管理器惯例一致，便于连续 Shift 调整范围）
        elif ctrl:
            if page_idx in self.grid_selected_pages:
                self.grid_selected_pages.discard(page_idx)
            else:
                self.grid_selected_pages.add(page_idx)
            self._grid_anchor_page = page_idx
        else:
            self.grid_selected_pages = {page_idx}
            self._grid_anchor_page = page_idx
        self._update_grid_selection_styles()
        self._refresh_page_ops_buttons()

    def _on_grid_page_activated(self, page_idx):
        """cp67: 网格双击 → 回单页视图并定位到该页。"""
        if self.doc:
            self.current_page = max(0, min(page_idx, len(self.doc) - 1))
        self.set_page_view_mode(False)

    def _update_grid_selection_styles(self):
        """cp67: 同步选中描边样式。"""
        for idx, card in self._grid_cards.items():
            selected = idx in self.grid_selected_pages
            if bool(card.property("selected")) != selected:
                card.setProperty("selected", selected)
                card.style().unpolish(card)
                card.style().polish(card)

    def _refresh_page_ops_buttons(self):
        """cp67: 页面操作按钮启用态 = 页面视图中且有选中页。"""
        has_sel = bool(self.grid_selected_pages) and self.page_view_mode
        for name in ("btn_page_rotate_left", "btn_page_rotate_right",
                     "btn_page_insert", "btn_page_insert_file", "btn_page_delete"):
            btn = getattr(self, name, None)
            if btn is not None:
                btn.setEnabled(has_sel)

    def _structural_ops_locked_by_scan(self):
        """v40.1.4（S3）：OCR 扫描进行中禁止页面结构操作。

        worker 按打开时的旧结构逐页回报页码；扫描中旋转/插页/删页会让后续
        结果按旧页码写入新结构（错遮+漏遮，静默发生）。Word 侧早有同款防线
        （扫描中拒绝手动操作），PDF 侧此前缺失。
        契约：MainWindow 提供 active_worker（OCRWorker | None）。
        """
        worker = getattr(self, "active_worker", None)
        if worker is not None and getattr(worker, "isRunning", lambda: False)():
            QMessageBox.information(
                self, "操作暂不可用",
                "智能扫描正在进行中，请等待完成后再进行页面结构操作"
                "（旋转 / 插入 / 删除页），否则扫描结果可能写错页。")
            return True
        return False

    def _rotate_selected_pages(self, delta_deg):
        """cp67: 选中页旋转 ±90°，已有遮罩坐标跟随变换（display 坐标系）。"""
        if not self.doc or not self.grid_selected_pages:
            return
        if self._structural_ops_locked_by_scan():
            return
        for idx in sorted(self.grid_selected_pages):
            if idx >= len(self.doc):
                continue
            try:
                page = self.doc[idx]
                old_w, old_h = page.rect.width, page.rect.height
                page.set_rotation((page.rotation + delta_deg) % 360)
            except Exception as e:
                logger.warning("[cp67] 页面旋转失败: %s", type(e).__name__)
                continue
            entry = self.page_data.get(idx)
            if entry:
                for key in ('ocr', 'manual'):
                    hits = entry.get(key, [])
                    for i, item in enumerate(hits):
                        rect = _hit_rect(item)
                        if rect is None:
                            continue
                        nx, ny, nw, nh = transform_hit_rect_for_rotation(
                            rect.x(), rect.y(), rect.width(), rect.height(),
                            old_w, old_h, delta_deg)
                        new_rect = QRectF(nx, ny, nw, nh)
                        if isinstance(item, dict):
                            hits[i] = dict(item, rect=new_rect)
                        else:
                            hits[i] = new_rect
            self._invalidate_grid_cache(idx)
            # cp68: 旋转后宽高互换，纵横比缓存失效
            self._grid_page_aspects.pop(idx, None)
        self._pdf_modified = True
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(True)
        self._relayout_page_grid()
        self._set_info_bar_message(f"↺ 已旋转 {len(self.grid_selected_pages)} 页，导出时生效")
        self._capture_undo_state(structural=True)  # cp83: 页面旋转后结构快照

    def _insert_blank_page_after_selected(self):
        """cp67: 在选中页（多选取最大页码）之后插入空白页，页码数据同步重排。"""
        if not self.doc or not self.grid_selected_pages:
            return
        if self._structural_ops_locked_by_scan():
            return
        anchor = max(p for p in self.grid_selected_pages if p < len(self.doc))
        try:
            ref_rect = self.doc[anchor].rect
            insert_at = anchor + 1
            self.doc.new_page(pno=insert_at, width=ref_rect.width, height=ref_rect.height)
        except Exception as e:
            QMessageBox.warning(self, "插入失败", f"插入空白页失败：{type(e).__name__}: {e}")
            return
        self.page_data = shift_page_data_for_insert(self.page_data, insert_at)
        self._ocr_processed_pages = shift_page_set_for_insert(
            getattr(self, '_ocr_processed_pages', set()) or set(), insert_at)
        self.grid_selected_pages = shift_page_set_for_insert(self.grid_selected_pages, insert_at)
        self._pdf_modified = True
        # cp81: 页序变化，搜索 OCR 文本缓存页码失效
        self._search_ocr_cache.clear()
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(True)
        self._rebuild_page_grid()
        self._set_info_bar_message(f"➕ 已在第 {anchor + 1} 页后插入空白页，导出时生效")
        self._capture_undo_state(structural=True)  # cp83: 插入空白页后结构快照

    def _insert_file_after_selected(self):
        """cp111: 在选中页之后插入文件（PDF / 图片）作为新页面，页码数据同步重排。"""
        if not self.doc or not self.grid_selected_pages:
            return
        if self._structural_ops_locked_by_scan():
            return
        anchor = max(p for p in self.grid_selected_pages if p < len(self.doc))
        fnames, _ = QFileDialog.getOpenFileNames(
            self, "选择要插入的文件（PDF 或图片）", "",
            "可插入文件 (*.pdf *.jpg *.jpeg *.png *.bmp *.tiff *.tif)")
        if not fnames:
            return
        insert_at = anchor + 1
        inserted_count = 0
        failed = []
        for fname in fnames:
            ftype = self.detect_file_type(fname)
            try:
                if ftype == 'pdf':
                    n = self._insert_pdf_pages_at(fname, insert_at)
                elif ftype == 'image':
                    n = self._insert_image_as_page_at(fname, insert_at)
                else:
                    failed.append(os.path.basename(fname))
                    continue
            except Exception as e:
                logger.error("[cp111] 插入文件 %s 失败: %s: %s", fname, type(e).__name__, e)
                failed.append(os.path.basename(fname))
                continue
            # 每个新页位置执行 shift（按插入顺序递增 insert_at），与单页插入语义一致
            for _ in range(n):
                self.page_data = shift_page_data_for_insert(self.page_data, insert_at)
                self._ocr_processed_pages = shift_page_set_for_insert(
                    getattr(self, '_ocr_processed_pages', set()) or set(), insert_at)
                self.grid_selected_pages = shift_page_set_for_insert(self.grid_selected_pages, insert_at)
                insert_at += 1
            inserted_count += n
        if inserted_count == 0:
            QMessageBox.warning(self, "插入失败", "没有文件被成功插入。" + (
                f"失败：{', '.join(failed)}" if failed else ""))
            return
        self._search_ocr_cache.clear()
        self._pdf_modified = True
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(True)
        self._rebuild_page_grid()
        msg = f"📎 已在第 {anchor + 1} 页后插入 {inserted_count} 页，导出时生效"
        if failed:
            msg += f"（{len(failed)} 个文件失败）"
        self._set_info_bar_message(msg)
        self._capture_undo_state(structural=True)  # cp111: 插入文件后结构快照

    def _insert_pdf_pages_at(self, pdf_path, start_at):
        """cp111: 把指定 PDF 的全部页面插入到 self.doc 的 start_at 位置，返回插入页数。

        cp114: 若源 PDF 加密，弹密码框认证后再插入；用户取消返回 0。
        """
        import fitz
        src = fitz.open(pdf_path)
        # cp114: 加密 PDF 需 authenticate 才能读取页面内容供 insert_pdf
        if src.needs_pass:
            file_name = os.path.basename(pdf_path)
            while True:
                pw, ok = QInputDialog.getText(
                    self, "加密 PDF",
                    f"{file_name} 已加密，请输入打开密码：",
                    echo=QLineEdit.EchoMode.Password,
                )
                if not ok or not pw:
                    src.close()
                    return 0  # 用户取消
                if src.authenticate(pw) > 0:
                    break
                QMessageBox.warning(self, "密码错误", "密码不正确，请重试。")
        try:
            n = len(src)
            self.doc.insert_pdf(src, start_at=start_at)
            return n
        finally:
            src.close()

    def _insert_image_as_page_at(self, img_path, start_at):
        """cp111: 把单张图片作为新页插入到 self.doc 的 start_at 位置，返回 1。"""
        import io
        import fitz
        from PIL import Image
        with Image.open(img_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            png_bytes = buf.getvalue()
            w, h = img.width, img.height
        page = self.doc.new_page(pno=start_at, width=w, height=h)
        page.insert_image(fitz.Rect(0, 0, w, h), stream=png_bytes, overlay=True)
        return 1

    def _delete_selected_pages(self):
        """cp67: 删除选中页（二次确认，至少保留 1 页），页码数据同步重排。"""
        if not self.doc or not self.grid_selected_pages:
            return
        if self._structural_ops_locked_by_scan():
            return
        total = len(self.doc)
        selected = sorted(p for p in self.grid_selected_pages if 0 <= p < total)
        if not selected:
            return
        if len(selected) >= total:
            QMessageBox.warning(self, "提示", "不能删除全部页面，至少需保留 1 页。")
            return
        preview = "、".join(str(p + 1) for p in selected[:10]) + (" 等" if len(selected) > 10 else "")
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除选中的 {len(selected)} 页（第 {preview} 页）吗？\n"
            "导出时生效；可通过 Ctrl+Z 撤销（依赖结构快照）。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            for idx in reversed(selected):
                self.doc.delete_page(idx)
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除页面时出错：{type(e).__name__}: {e}")
            self._rebuild_page_grid()
            return
        self.page_data = shift_page_data_for_delete(self.page_data, selected)
        self._ocr_processed_pages = shift_page_set_for_delete(
            getattr(self, '_ocr_processed_pages', set()) or set(), selected)
        self.grid_selected_pages.clear()
        self.current_page = max(0, min(self.current_page, len(self.doc) - 1))
        self._pdf_modified = True
        # cp81: 页序变化，搜索 OCR 文本缓存页码失效
        self._search_ocr_cache.clear()
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(True)
        self._rebuild_page_grid()
        self._set_info_bar_message(f"🗑 已删除 {len(selected)} 页，导出时生效")
        self._capture_undo_state(structural=True)  # cp83: 删除页面后结构快照

    def fit_page(self):
        """完整适应页面 - 根据窗口和页面尺寸动态计算缩放比例。

        cp68: 无论当前处于页面视图还是单页视图，点击"适应页面"都回到单页视图
        并按窗口大小自适应。页面视图下 self.scroll 处于隐藏态，需先退回单页视图，
        待布局在下一帧完成 show 后再计算缩放（否则读到过时的画布尺寸）。
        """
        if not self.doc or self.current_page is None:
            return
        if getattr(self, "page_view_mode", False):
            self.set_page_view_mode(False)
            QTimer.singleShot(0, self._apply_fit_page)
            return
        self._apply_fit_page()

    def _apply_fit_page(self):
        """cp68: 单页视图下按窗口尺寸计算并应用自适应缩放（fit_page 的计算核心）。"""
        if not self.doc or self.current_page is None:
            return
        # 获取画布可用尺寸（减去边距）
        canvas_width = self.scroll.width() - 40  # 40px 边距
        canvas_height = self.scroll.height() - 40

        # 获取当前页面的实际尺寸（点单位）
        page = self.doc[self.current_page]
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height

        # 分别计算宽度和高度的缩放比例
        zoom_w = canvas_width / page_width
        zoom_h = canvas_height / page_height

        # 取较小值确保页面完整显示在窗口中
        self.zoom_level = min(zoom_w, zoom_h)

        # 限制在最大最小范围内 (v33.2: 允许突破 ZOOM_MIN 以完整显示)
        self.zoom_level = self.clamp_zoom(self.zoom_level, allow_below_min=True)

        # 重新渲染
        self.render_view()
