# -*- coding: utf-8 -*-
"""cp123: 提取功能 Mixin —— 框选纵向区域累积提取到独立结果文档。

cp123 重构要点（相对 cp122-fix）：
- 按钮改 toggle（main.py 的 _on_extract_toggle 控制 enter/exit）
- 去掉 toolbar_edit_layout 的动态"新页/完成提取"按钮 → 改用右侧 ExtractSidePanel
- 所有片段可选可操作（左键点击右侧选中，不再只有最新片段可选）
- 导出弹窗统一（OK + 打开文档 + 显示详细信息/导出报告，仿 save_pdf）
- 支持多结果页查看（右侧工具栏翻页 + _extract_view_page）

接口契约（需 MainWindow 提供）：
    - self.doc, self.canvas_left, self.canvas_right, self.extract_side_panel
    - self._safe_canvas_update, self._safe_canvas_set_mask_color, self.current_color
    - self._set_info_bar_message
"""
import os

import fitz
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QPen
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from privacyguard.utils.helpers_pdf import build_result_doc_from_segments, build_extract_report
from privacyguard.utils.helpers_ui import open_path_in_system


class ExtractMixin:
    """cp123: 提取功能（纵向区域裁剪到独立结果文档，默认拼接当前页）。"""

    def enter_extract_mode(self):
        """进入提取模式：初始化片段模型 + 结果文档 + 右侧分屏 + 工具栏面板。"""
        if not self.doc:
            return
        # cp133: 防重入（重复调用会清空已提取片段）
        if getattr(self, "_extract_active", False):
            return
        # cp133: 退出页面视图（网格 canvas 无 vertical_select_mode，框选会失效）
        if getattr(self, "page_view_mode", False):
            self.set_page_view_mode(False)
        # 片段模型：[[片段dict,...], ...]，外层=结果页，内层=该页片段
        self._extract_segments = [[]]
        self._extract_selected = -1     # 选中片段的全局序号（-1=未选中）
        self._extract_view_page = 0     # 当前查看的结果页序号
        self._extract_active = True
        self._extract_result_doc = fitz.open()
        # 左侧纵向框选
        self.canvas_left.vertical_select_mode = True
        self.canvas_left.manual_replace_prompt = False
        try:
            self.canvas_left.vertical_region_selected.disconnect(self._on_extract_region_selected)
        except TypeError:
            pass
        self.canvas_left.vertical_region_selected.connect(self._on_extract_region_selected)
        # 右侧分屏 + 右键菜单 + 左键选中
        self.canvas_right.show()
        # cp129: 禁用右侧手动框选遮罩（提取模式下不解决脱敏问题，仅做提取）
        self.canvas_right.interaction_disabled = True
        self.canvas_right.manual_replace_prompt = False
        # cp123-fix: 右侧 size policy 与左侧对称（避免又小又偏上）
        from PyQt6.QtWidgets import QSizePolicy
        self.canvas_right.setSizePolicy(QSizePolicy.Policy.Expanding,
                                        QSizePolicy.Policy.Expanding)
        self.canvas_right.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.canvas_right.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        try:
            self.canvas_right.customContextMenuRequested.disconnect(self._on_extract_context_menu)
        except TypeError:
            pass
        self.canvas_right.customContextMenuRequested.connect(self._on_extract_context_menu)
        # cp123: 左键点击右侧 → 选中片段
        try:
            self.canvas_right.canvas_clicked.disconnect(self._on_extract_left_click)
        except TypeError:
            pass
        self.canvas_right.canvas_clicked.connect(self._on_extract_left_click)
        # cp130: 右侧滚轮翻结果文档页（临时断开原文档翻页，连到结果页切换）
        try:
            self.canvas_right.page_change_request.disconnect()
        except TypeError:
            pass
        self.canvas_right.page_change_request.connect(lambda d: self._change_view_page(1 if d > 0 else -1))
        # 右侧工具栏面板（信号在 main.py 面板创建时一次性连接，避免重复连接导致多次触发）
        # cp124/cp125: 浮动可拖动面板——用 centralWidget 做 parent（QMainWindow 本身会
        # 被 central widget 遮挡，v40.1.2 修复）。拖动后位置在会话内持久（_last_floating_pos），
        # exit 时清除记忆 → 重新进入恢复默认位置。
        panel = self.extract_side_panel
        panel.show_as_floating(self.centralWidget())
        panel.set_segment_actions_enabled(False)
        panel.set_page_nav_enabled(False, False)
        self._refresh_extract_preview()
        self._set_info_bar_message(
            "⬆ 提取模式：左侧拖拽纵向区域提取，默认拼接到当前结果页底部；"
            "右侧工具栏可新页/导出/删除/移序/替换")

    def exit_extract_mode(self):
        """退出提取模式：隐藏分屏 + 面板，清理状态。"""
        self._extract_active = False
        self.canvas_left.vertical_select_mode = False
        try:
            self.canvas_left.vertical_region_selected.disconnect(self._on_extract_region_selected)
        except TypeError:
            pass
        self.canvas_right.hide()
        # cp129: 恢复右侧交互（退出提取模式后可正常遮罩）
        self.canvas_right.interaction_disabled = False
        try:
            self.canvas_right.customContextMenuRequested.disconnect(self._on_extract_context_menu)
        except TypeError:
            pass
        try:
            self.canvas_right.canvas_clicked.disconnect(self._on_extract_left_click)
        except TypeError:
            pass
        # cp133: 清理替换模式残留（_on_extract_replace_selected 信号 + target）
        try:
            self.canvas_left.vertical_region_selected.disconnect(self._on_extract_replace_selected)
        except TypeError:
            pass
        self._extract_replace_target = None
        # cp130: 恢复右侧滚轮翻原文档页
        try:
            self.canvas_right.page_change_request.disconnect()
        except TypeError:
            pass
        self.canvas_right.page_change_request.connect(self.handle_page_change_request)
        self.extract_side_panel.hide()
        # cp125: 清除浮动面板记忆位置 → 下次进入恢复默认位置
        self.extract_side_panel._last_floating_pos = None
        doc = getattr(self, "_extract_result_doc", None)
        if doc is not None and not doc.is_closed:
            try:
                doc.close()
            except Exception:
                pass
        self._extract_result_doc = None
        self._extract_segments = None
        self._extract_selected = -1
        self._extract_view_page = 0

    # === 片段操作 ===

    def _flatten_segments(self):
        """展平片段为 [(page_idx, seg_idx_in_page, seg_dict)]。"""
        flat = []
        for p_idx, page_segs in enumerate(self._extract_segments or []):
            for s_idx, seg in enumerate(page_segs):
                flat.append((p_idx, s_idx, seg))
        return flat

    def _on_extract_region_selected(self, page_idx, y_min, y_max):
        """纵向框选完成：默认拼接到当前查看的结果页（或最后一个非空页）。"""
        if not self.doc or page_idx < 0 or page_idx >= len(self.doc):
            return
        if not self._extract_segments:
            return
        region_h = y_max - y_min
        seg = {"src_pno": page_idx, "y_min": float(y_min), "y_max": float(y_max),
               "label": f"P{page_idx+1}:{y_min:.0f}-{y_max:.0f}"}
        # 追加到最后一个结果页
        self._extract_segments[-1].append(seg)
        self._rebuild_result_doc()
        # 切到最后一页查看 + 选中新片段
        self._extract_view_page = max(0, len(self._extract_segments) - 1)
        flat = self._flatten_segments()
        if flat:
            self._extract_selected = len(flat) - 1
        self._refresh_extract_preview()
        total = sum(len(p) for p in self._extract_segments)
        self._set_info_bar_message(
            f"⬆ 已提取第 {page_idx+1} 页区域（高 {region_h:.0f}pt）→ "
            f"拼接到结果页 {len(self._extract_segments)}（共 {total} 片段）")

    def _start_new_result_page(self):
        """另起一个结果页。"""
        if not getattr(self, "_extract_active", False):
            return
        if self._extract_segments and self._extract_segments[-1]:
            self._extract_segments.append([])
            self._rebuild_result_doc()
            self._extract_selected = -1
            self._extract_view_page = len(self._extract_segments) - 1
            self._refresh_extract_preview()
            self._set_info_bar_message(
                f"📄 已另起结果页 {len(self._extract_segments)}，后续提取将拼接到此页")
        else:
            self._set_info_bar_message("当前结果页还是空的，请先提取内容再另起页")

    def _rebuild_result_doc(self):
        """根据 _extract_segments 重建结果文档。"""
        non_empty = [p for p in self._extract_segments if p]
        doc = getattr(self, "_extract_result_doc", None)
        if doc is not None and not doc.is_closed:
            try:
                doc.close()
            except Exception:
                pass
        if not non_empty:
            self._extract_result_doc = fitz.open()
            return
        try:
            self._extract_result_doc = build_result_doc_from_segments(self.doc, non_empty)
        except Exception as e:
            QMessageBox.warning(self, "重建结果失败", f"{type(e).__name__}: {e}")
            self._extract_result_doc = fitz.open()

    # === 选中片段操作（从右侧工具栏按钮触发）===

    def _delete_selected_segment(self):
        """删除当前选中的片段。"""
        if self._extract_selected < 0:
            return
        flat = self._flatten_segments()
        if self._extract_selected >= len(flat):
            return
        p_idx, s_idx, seg = flat[self._extract_selected]
        del self._extract_segments[p_idx][s_idx]
        self._extract_selected = -1
        self._rebuild_result_doc()
        self._refresh_extract_preview()
        self._set_info_bar_message(f"🗑 已删除片段（{seg['label']}）")

    def _move_selected_segment(self, direction):
        """上移(-1)/下移(+1)选中片段。"""
        if self._extract_selected < 0:
            return
        flat = self._flatten_segments()
        if self._extract_selected >= len(flat):
            return
        p_idx, s_idx, _ = flat[self._extract_selected]
        page_segs = self._extract_segments[p_idx]
        new_s = s_idx + direction
        if new_s < 0 or new_s >= len(page_segs):
            return
        page_segs[s_idx], page_segs[new_s] = page_segs[new_s], page_segs[s_idx]
        for gi, (pi, si, _) in enumerate(self._flatten_segments()):
            if pi == p_idx and si == new_s:
                self._extract_selected = gi
                break
        self._rebuild_result_doc()
        self._refresh_extract_preview()
        self._set_info_bar_message(
            f"↕ 已{'上移' if direction < 0 else '下移'}片段")

    def _replace_selected_segment(self):
        """重新提取替换：提示用户在左侧重新框选。"""
        if self._extract_selected < 0:
            return
        flat = self._flatten_segments()
        if self._extract_selected >= len(flat):
            return
        p_idx, s_idx = flat[self._extract_selected][:2]
        self._extract_replace_target = (p_idx, s_idx)
        self._extract_selected = -1
        self._refresh_extract_preview()
        self._set_info_bar_message(
            f"🔄 请在左侧拖拽新的纵向区域，将替换结果页 {p_idx+1} 第 {s_idx+1} 片")
        try:
            self.canvas_left.vertical_region_selected.disconnect(self._on_extract_region_selected)
        except TypeError:
            pass
        self.canvas_left.vertical_region_selected.connect(self._on_extract_replace_selected)

    def _on_extract_replace_selected(self, page_idx, y_min, y_max):
        """替换模式下的框选回调。"""
        target = getattr(self, "_extract_replace_target", None)
        if target is None:
            return
        p_idx, s_idx = target
        if p_idx < len(self._extract_segments) and s_idx < len(self._extract_segments[p_idx]):
            self._extract_segments[p_idx][s_idx] = {
                "src_pno": page_idx, "y_min": float(y_min), "y_max": float(y_max),
                "label": f"P{page_idx+1}:{y_min:.0f}-{y_max:.0f}",
            }
        self._extract_replace_target = None
        try:
            self.canvas_left.vertical_region_selected.disconnect(self._on_extract_replace_selected)
        except TypeError:
            pass
        self.canvas_left.vertical_region_selected.connect(self._on_extract_region_selected)
        self._rebuild_result_doc()
        self._refresh_extract_preview()
        self._set_info_bar_message(f"🔄 已替换片段（结果页 {p_idx+1} 第 {s_idx+1} 片）")

    # === 右侧预览渲染（含片段分隔线 + 选中高亮）===

    def _refresh_extract_preview(self):
        """刷新右侧预览：渲染当前查看页 + 片段分隔线 + 选中高亮 + 工具栏状态。"""
        doc = getattr(self, "_extract_result_doc", None)
        non_empty = [p for p in (self._extract_segments or []) if p]
        if doc is None or len(doc) == 0 or not non_empty:
            self._render_extract_empty()
            self.extract_side_panel.set_segment_actions_enabled(False)
            self.extract_side_panel.set_page_nav_enabled(False, False)
            return
        # 钳制查看页序号
        if self._extract_view_page >= len(non_empty):
            self._extract_view_page = len(non_empty) - 1
        page_idx = self._extract_view_page
        page = doc[page_idx]
        # cp123-fix: 右侧用与左侧一致的 zoom_level，保持左右对称（此前用 500/page_w 导致右侧偏小）
        zoom = float(getattr(self, "zoom_level", 1.0))
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride,
                          QImage.Format.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(qimg)
        except Exception:
            # cp133: 渲染失败（旋转页/加密等）降级到空状态，避免异常冒泡
            self._render_extract_empty()
            return
        self._draw_segment_overlays(pixmap, page_idx, zoom)
        self._safe_canvas_update(self.canvas_right, pixmap, zoom, [], [])
        # 确保超高时能滚动
        self.canvas_right.setMinimumHeight(pixmap.height())
        # 更新工具栏按钮状态
        self.extract_side_panel.set_segment_actions_enabled(self._extract_selected >= 0)
        self.extract_side_panel.set_page_nav_enabled(
            page_idx > 0, page_idx < len(non_empty) - 1)

    def _draw_segment_overlays(self, pixmap, result_page_idx, zoom):
        """绘制片段分隔线（虚线）+ 选中片段高亮边框。"""
        non_empty = [p for p in (self._extract_segments or []) if p]
        if result_page_idx >= len(non_empty):
            return
        page_segs = non_empty[result_page_idx]
        if not page_segs:
            return
        painter = QPainter(pixmap)
        try:
            cur_y = 0.0
            global_idx = sum(len(non_empty[i]) for i in range(result_page_idx))
            for s_i, seg in enumerate(page_segs):
                # 安全审计 v40.1.4（S2）：撤销/删页后片段可能引用越界页，跳过防 IndexError 闪退
                if not (0 <= seg.get("src_pno", -1) < len(self.doc)):
                    continue
                src_page = self.doc[seg["src_pno"]]
                sp_h = src_page.rect.height
                y0 = max(0.0, min(seg["y_min"], sp_h))
                y1 = max(0.0, min(seg["y_max"], sp_h))
                seg_h = y1 - y0
                y_top_screen = cur_y * zoom
                this_global = global_idx + s_i
                if this_global == self._extract_selected:
                    pen = QPen(QColor(0x2E, 0x90, 0xFA), 2)
                    painter.setPen(pen)
                    painter.drawRect(QRectF(1, y_top_screen + 1,
                                            pixmap.width() - 2, seg_h * zoom - 2))
                if s_i > 0:
                    pen = QPen(QColor(0x9C, 0xA3, 0xAF), 1, Qt.PenStyle.DashLine)
                    painter.setPen(pen)
                    painter.drawLine(QPointF(0, y_top_screen),
                                     QPointF(pixmap.width(), y_top_screen))
                cur_y += seg_h
        finally:
            painter.end()

    def _render_extract_empty(self):
        """渲染右侧空状态提示。

        cp123-fix-3: 空状态 pixmap 尺寸跟随左侧 canvas_left 当前 pixmap，
        使两侧视觉对称（此前固定 300×400 导致右侧明显偏小偏上）。
        """
        # 取左侧 canvas 的 pixmap 尺寸作为参考（对称基准）
        left_pm = self.canvas_left.pixmap()
        w = left_pm.width() if left_pm and not left_pm.isNull() else 400
        h = left_pm.height() if left_pm and not left_pm.isNull() else 560
        pm = QPixmap(w, h)
        pm.fill(QColor(0xF7, 0xF8, 0xFA))
        p = QPainter(pm)
        p.setPen(QColor(0x9C, 0xA3, 0xAF))
        f = QFont(); f.setPointSize(10); p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter,
                   "暂无提取内容\n\n在左侧拖拽纵向区域\n提取拼接此处")
        p.end()
        self._safe_canvas_update(self.canvas_right, pm, 1.0, [], [])
        self.canvas_right.setMinimumHeight(pm.height())

    # === 右侧点击选中 + 右键菜单 ===

    def _on_extract_right_click(self, pos):
        """右侧点击：根据 y 坐标选中对应片段（左键/右键共用）。"""
        doc = getattr(self, "_extract_result_doc", None)
        non_empty = [p for p in (self._extract_segments or []) if p]
        if doc is None or len(doc) == 0 or not non_empty:
            return
        page_idx = self._extract_view_page
        if page_idx >= len(non_empty):
            return
        page_segs = non_empty[page_idx]
        if not page_segs:
            return
        zoom = float(getattr(self, "zoom_level", 1.0))
        click_y_pdf = pos.y() / zoom
        cur_y = 0.0
        global_idx = sum(len(non_empty[i]) for i in range(page_idx))
        for s_i, seg in enumerate(page_segs):
            # 安全审计 v40.1.4（S2）：越界片段跳过（防 IndexError 闪退）
            if not (0 <= seg.get("src_pno", -1) < len(self.doc)):
                continue
            src_page = self.doc[seg["src_pno"]]
            sp_h = src_page.rect.height
            seg_h = max(0.0, min(seg["y_max"], sp_h)) - max(0.0, min(seg["y_min"], sp_h))
            if cur_y <= click_y_pdf < cur_y + seg_h:
                self._extract_selected = global_idx + s_i
                self._refresh_extract_preview()
                return
            cur_y += seg_h

    def _on_extract_left_click(self, pos):
        """cp123: 左键点击右侧结果页 → 选中片段（复用右键选中逻辑）。"""
        self._on_extract_right_click(pos)

    def _on_extract_context_menu(self, pos):
        """右侧右键菜单。"""
        self._on_extract_right_click(pos)
        if self._extract_selected < 0:
            return
        from PyQt6.QtWidgets import QMenu
        flat = self._flatten_segments()
        if self._extract_selected >= len(flat):
            return
        p_idx, s_idx, seg = flat[self._extract_selected]
        menu = QMenu(self.canvas_right)
        act_delete = menu.addAction(f"删除选中片段（{seg['label']}）")
        menu.addSeparator()
        act_up = menu.addAction("上移")
        act_down = menu.addAction("下移")
        menu.addSeparator()
        act_replace = menu.addAction("重新提取替换…")
        action = menu.exec(self.canvas_right.mapToGlobal(pos))
        if action == act_delete:
            self._delete_selected_segment()
        elif action == act_up:
            self._move_selected_segment(-1)
        elif action == act_down:
            self._move_selected_segment(1)
        elif action == act_replace:
            self._replace_selected_segment()

    def _change_view_page(self, delta):
        """切换查看的结果页（右侧工具栏翻页）。"""
        non_empty = [p for p in (self._extract_segments or []) if p]
        new_idx = self._extract_view_page + delta
        if 0 <= new_idx < len(non_empty):
            self._extract_view_page = new_idx
            self._extract_selected = -1
            self._refresh_extract_preview()

    # === 导出（统一弹窗：OK + 打开文档 + 显示详细信息/导出报告）===

    def _finish_extract(self):
        """导出提取结果（弹窗与 save_pdf 一致）。"""
        doc = getattr(self, "_extract_result_doc", None)
        if doc is None or len(doc) == 0:
            QMessageBox.information(self, "提示", "还没有提取任何内容。")
            return
        fname, _ = QFileDialog.getSaveFileName(
            self, "保存提取结果", "", "PDF Files (*.pdf)")
        if not fname:
            return
        try:
            doc.save(fname, garbage=4, deflate=True, clean=True)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"{type(e).__name__}: {e}")
            return
        # cp123: 统一弹窗（OK + 打开文档 + 详细信息/导出报告）
        report_text = build_extract_report(self._extract_segments, src_doc=self.doc)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("提取完成")
        box.setText(
            f"已提取 {len(doc)} 页内容保存到：\n{fname}\n\n"
            f"点\"显示详细信息\"可查看提取报告。")
        box.setDetailedText(report_text)
        btn_export_report = box.addButton("导出报告", QMessageBox.ButtonRole.ActionRole)
        btn_open_doc = box.addButton("打开文档", QMessageBox.ButtonRole.ActionRole)
        btn_reload = box.addButton("回炉打开", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_open_doc:
            ok, err = open_path_in_system(fname)
            if not ok:
                QMessageBox.warning(self, "打开失败", f"无法打开导出的文档：\n{err}")
        elif clicked is btn_reload:
            # cp128: 回炉打开——用本软件打开提取结果，继续脱敏（逻辑闭环）
            self._reload_extracted_file(fname)
        elif clicked is btn_export_report:
            report_fname = os.path.splitext(fname)[0] + "_提取报告.txt"
            try:
                with open(report_fname, "w", encoding="utf-8") as f:
                    f.write(report_text)
                QMessageBox.information(self, "报告已导出", f"提取报告已保存到：\n{report_fname}")
            except Exception as e:
                QMessageBox.warning(self, "导出报告失败", f"{type(e).__name__}: {e}")
        self._set_info_bar_message(f"⬆ 提取结果已保存：{os.path.basename(fname)}")

    def _reload_extracted_file(self, fname):
        """cp128: 回炉打开——退出提取模式后用本软件打开提取结果，继续脱敏。

        顺序很重要：先退出提取模式（取消 toggle、关闭 _extract_result_doc、
        隐藏浮动面板），再调 _open_pdf_file 打开新文件（避免 _extract_result_doc
        与重新打开的 doc 冲突，避免浮动面板残留）。
        """
        # 退出提取模式（含取消 toggle 按钮选中态，blockSignals 防回环）
        if hasattr(self, "btn_extract"):
            self.btn_extract.blockSignals(True)
            self.btn_extract.setChecked(False)
            self.btn_extract.blockSignals(False)
        self.exit_extract_mode()
        # 安全审计 v40.1.4（P2-2）：回炉打开走与常规打开一致的完整清理，
        # 防止上一文档的 _ocr_processed_pages/_search_ocr_cache/_targeted_toc_rules
        # 跨文档残留（绕过未扫描告警 / 污染搜索与书签预览）。
        try:
            self._cleanup_before_open()
            self._open_pdf_file(fname)
            self._set_info_bar_message(f"🔄 已回炉打开提取结果：{os.path.basename(fname)}，可继续脱敏")
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"回炉打开失败：{type(e).__name__}: {e}")
