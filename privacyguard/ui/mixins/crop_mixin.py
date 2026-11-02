# -*- coding: utf-8 -*-
"""cp122: 截去功能 Mixin —— 从当前页挖掉纵向区域，上下部分自动拼接。

接口契约（需 MainWindow 提供）：
    - self.doc: fitz.Document（当前 PDF 文档）
    - self.current_page: int（当前页码）
    - self.canvas_left: SinglePageCanvas（主画布，用于纵向框选）
    - self._capture_undo_state(structural=True): 结构变更撤销快照
    - self._invalidate_grid_cache(page_idx): 失效网格缩略图缓存
    - self._rebuild_page_grid(): 重建页面网格
    - self.render_view(): 刷新单页/双页视图
    - self.btn_save: QPushButton（导出按钮，截去后启用）
    - self._set_info_bar_message(msg): 信息栏提示
    - self._pdf_modified: bool（文档修改标志）

交互流程：
    1. enter_crop_mode() → canvas_left 进入纵向框选模式，信息栏提示
    2. 用户拖拽框选 → canvas 发 vertical_region_selected 信号
    3. _on_crop_region_selected() → 确认对话框 → 执行截去 → 刷新 + 撤销快照
    4. exit_crop_mode() → 退出纵向框选模式
"""
from PyQt6.QtWidgets import QMessageBox

from privacyguard.utils.helpers_pdf import crop_vertical_region_from_page
from privacyguard.utils.pdf_regions import crop_page_hits


class CropMixin:
    """cp122: 截去功能（纵向区域裁剪，上下拼接，保持矢量）。"""

    def enter_crop_mode(self):
        """进入截去模式：canvas_left 切到纵向框选。

        cp123: 互斥由 main.py 的 _on_crop_toggle 处理（取消提取按钮选中 +
        调 exit_extract_mode），此处只负责截去模式自身的初始化。
        """
        if not self.doc:
            return
        # cp133: 防重入
        if getattr(self, "_crop_active", False):
            return
        # cp133: 退出页面视图（网格 canvas 无 vertical_select_mode，框选会失效）
        if getattr(self, "page_view_mode", False):
            self.set_page_view_mode(False)
        self._crop_active = True
        self.canvas_left.vertical_select_mode = True
        # 确保不在手动遮罩框选模式（互斥）
        self.canvas_left.manual_replace_prompt = False
        # 接线信号（幂等：先断开再连接，避免重复）
        try:
            self.canvas_left.vertical_region_selected.disconnect(self._on_crop_region_selected)
        except TypeError:
            pass
        self.canvas_left.vertical_region_selected.connect(self._on_crop_region_selected)
        self._set_info_bar_message("✂ 截去模式：在页面上拖拽选择要截去的纵向区域（上下边界）")

    def exit_crop_mode(self):
        """退出截去模式。"""
        self._crop_active = False
        self.canvas_left.vertical_select_mode = False
        try:
            self.canvas_left.vertical_region_selected.disconnect(self._on_crop_region_selected)
        except TypeError:
            pass

    def _on_crop_region_selected(self, page_idx, y_min, y_max):
        """纵向框选完成：确认后执行截去。"""
        if not self.doc or page_idx < 0 or page_idx >= len(self.doc):
            return
        if self._structural_ops_locked_by_scan():
            return
        page_h = max(1, self.doc[page_idx].rect.height)
        mapped_hits = crop_page_hits(self.page_data.get(page_idx), y_min, y_max,
                                    self.doc[page_idx].rect.width, page_h)
        region_r = y_max - y_min
        reply = QMessageBox.question(
            self, "确认截去",
            f"将截去第 {page_idx + 1} 页的纵向区域（高 {region_r:.0f}pt，"
            f"占该页 {region_r / page_h * 100:.0f}%），\n"
            f"上下部分自动拼接，保持原始矢量内容。\n确定继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            new_h = crop_vertical_region_from_page(self.doc, page_idx, y_min, y_max)
        except ValueError as e:
            QMessageBox.warning(self, "截去失败", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "截去失败", f"{type(e).__name__}: {e}")
            return
        # Retained content must retain its masks, including masks crossing the cut.
        self.page_data[page_idx] = mapped_hits
        getattr(self, '_ocr_processed_pages', set()).discard(page_idx)
        if hasattr(self, '_search_ocr_cache'):
            self._search_ocr_cache.clear()
        # 更新状态
        self._pdf_modified = True
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(True)
        # 失效该页缓存（页面尺寸已变）+ 刷新视图
        self._invalidate_grid_cache(page_idx)
        if getattr(self, "page_view_mode", False):
            self._rebuild_page_grid()
        else:
            self.render_view()
        self._set_info_bar_message(
            f"✂ 已截去第 {page_idx + 1} 页区域（新页高 {new_h:.0f}pt），导出时生效")
        # cp133: 只在变更后记一次快照（与旋转/删除等结构操作一致；before 快照由撤销栈自然提供）
        # cp133-fix: 此前误调用两次导致撤销栈压入两份相同快照，用户需按 Ctrl+Z 两次才能
        # 撤销一次截去；删除重复调用。
        self._capture_undo_state(structural=True)
