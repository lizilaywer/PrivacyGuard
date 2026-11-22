"""Review operations with position-scoped persistence and existing PDF undo.

MainWindow contract: doc, page_data, word_doc, word_data, file_path,
active_worker, current_page, _session_store; render_view/render_word_preview,
_capture_undo_state, _set_info_bar_message, btn_save/btn_undo/btn_redo.
New document opens call reset_review(); no worker touches review widgets.
"""
import copy
import json

import fitz
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtWidgets import QDockWidget, QMessageBox

from privacyguard.ui.panels.redaction_review_panel import RedactionReviewPanel
from privacyguard.utils.export_transaction import ExportValidationError
from privacyguard.utils.review_decisions import (geometry, page_fingerprint, word_match_key,
                                                 WordReviewStore)


class ReviewMixin:
    def setup_review(self):
        self.review_panel = RedactionReviewPanel(self)
        self.review_dock = QDockWidget("脱敏复核", self)
        self.review_dock.setObjectName("redactionReviewDock")
        self.review_dock.setWidget(self.review_panel)
        self.review_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.review_dock)
        self.review_dock.hide()
        self.review_panel.locate.connect(self.review_locate)
        self.review_panel.decide.connect(self.review_decide)
        self.review_panel.inspect_requested.connect(self.start_page_inspection)
        self._review_timer = QTimer(self)
        self._review_timer.setInterval(1000)
        self._review_timer.timeout.connect(self.refresh_review)
        self.review_dock.visibilityChanged.connect(lambda visible: self._review_timer.start() if visible else self._review_timer.stop())
        self.review_dock.visibilityChanged.connect(self._review_layout_changed)
        self.review_dock.topLevelChanged.connect(self._review_layout_changed)
        self.reset_review()

    def reset_review(self):
        self._word_review_undo = []
        self._word_review_redo = []
        self._word_review_store = None
        self._review_pdf_fingerprints = {}
        self._review_signature = None
        self._inspection_candidates = []
        self._inspection_fingerprint = None
        self._inspection_status = ""
        self._rule_review_cache = (None, [])
        self._rule_review_failed = None
        if hasattr(self, "review_dock"):
            self.review_dock.hide()

    def _review_layout_changed(self, *_args):
        QTimer.singleShot(0, self._refresh_toolbar_responsiveness)
        QTimer.singleShot(60, self._enforce_toolbar_min_width)

    def load_word_review(self):
        self.reset_review()
        self._word_review_store = WordReviewStore(getattr(self, "_word_input_source_path", None) or self.file_path, self._session_store.base_dir)
        for key, decisions in self._word_review_store.load().items():
            if key in self.word_data:
                self.word_data[key]["_review"] = decisions
        self.refresh_word_review_buttons()

    def toggle_review(self):
        self.refresh_review()
        self.review_dock.setVisible(not self.review_dock.isVisible())

    def review_busy(self):
        worker = getattr(self, "active_worker", None)
        return worker is not None and worker.isRunning()

    def refresh_review(self):
        if not hasattr(self, "review_panel"):
            return
        busy = self.review_busy()
        self.review_panel.tree.setEnabled(not busy)
        self.review_panel.inspect_button.setEnabled(not busy and self.doc is not None)
        rows = []
        if self.doc is not None:
            for page, entry in self.page_data.items():
                scanned = page in getattr(self, "_ocr_processed_pages", set())
                rows.append({"page": page, "source": "status", "state": "checked" if scanned else "unchecked",
                             "label": f"第 {page+1} 页 · " + ("已扫描" if entry.get("ocr") else "已扫描，零命中") if scanned else f"第 {page+1} 页 · 未扫描/未完成"})
                decisions = {tuple(d["geometry"]): d for d in entry.get("_review", []) if not d.get("stale")}
                for source in ("ocr", "manual"):
                    for index, hit in enumerate(entry.get(source, [])):
                        decision = decisions.get(tuple(geometry(hit)), {}) if source == "ocr" else {}
                        rows.append({"page": page, "source": source, "index": index, "geometry": geometry(hit),
                                     "label": f"第 {page+1} 页 · " + (hit.get("rule_name", "自动识别") if isinstance(hit, dict) and source == "ocr" else "手工标记" if source == "manual" else "自动识别"),
                                     "state": "confirmed" if source == "manual" else decision.get("state", "pending")})
                for decision in entry.get("_review", []):
                    if decision.get("state") == "excluded":
                        stale = decision.get("stale", False)
                        rows.append({"page": page, "source": "status" if stale else "ocr", "geometry": decision["geometry"], "state": "stale" if stale else "excluded", "label": f"第 {page+1} 页 · " + ("原排除已失效，请重新复核" if stale else "已排除位置")})
            processed = len(getattr(self, "_ocr_processed_pages", set()))
            status = f"扫描进度：{processed}/{len(self.page_data)} 页；零命中页与未扫描页分开计数。"
        elif self.word_doc is not None:
            try:
                rows.extend(self.word_rule_review_rows())
                rule_error = ""
            except RuntimeError:
                rule_error = "\n规则复核未完成，请简化正则后重试。"
            for key, entry in self.word_data.items():
                for source in ("ocr", "manual"):
                    for index, hit in enumerate(entry.get(source, [])):
                        state = entry.get("_review", {}).get(word_match_key(hit), "pending")
                        rows.append({"key": key, "source": source, "index": index, "match_key": word_match_key(hit), "state": state,
                                     "label": entry.get("label", key) + " · " + ("自动识别" if source == "ocr" else "手工标记")})
                for key_match, state in entry.get("_review", {}).items():
                    if state == "excluded" and not any(r.get("key") == key and r.get("match_key") == key_match for r in rows):
                        rows.append({"key": key, "match_key": key_match, "source": "ocr", "state": state, "label": entry.get("label", key) + " · 已排除位置"})
            meta = getattr(self, "_word_scan_meta", None) or {}
            status = f'扫描块：{meta.get("scanned_blocks", 0)}/{len(self.word_data)}；' + ("扫描未完成" if meta.get("was_cancelled", True) else "扫描完成")
            status += rule_error
        else:
            status = "打开 PDF 或 Word 后可复核。"
        if busy:
            status += "\n正在扫描，请完成后复核。"
        rows.extend(self._inspection_candidates)
        if self._inspection_status:
            status += "\n" + self._inspection_status
        if len(rows) > 5000:
            status += f"\n本清单显示前 5000/{len(rows)} 项；其余可在页面复核。"
        signature = repr((rows[:5000], status))
        if signature != self._review_signature:
            self._review_signature = signature
            self.review_panel.set_rows(rows[:5000], status)

    def review_locate(self, row):
        if self.review_busy():
            return
        if row["source"] == "candidate" and not self._inspection_page_current(row):
            return
        if self.doc is not None and "page" in row:
            self.current_page = row["page"]
            if getattr(self, "page_view_mode", False):
                self.set_page_view_mode(False)
            self.render_view()
            if row.get("geometry"):
                self._flash_search_hit(row["geometry"])
            self._set_info_bar_message(f'已定位第 {self.current_page+1} 页，请核对选定位置。')
        elif self.word_doc is not None and "key" in row:
            key = json.dumps(row["key"], ensure_ascii=True)
            script = f"Array.from(document.querySelectorAll('[data-key]')).find(e=>e.dataset.key==={key})?.scrollIntoView({{block:'center'}});"
            self.word_preview.page().runJavaScript(script)

    def review_decide(self, row, state):
        if self.review_busy() or state not in ("confirmed", "excluded", "restore"):
            return
        if row["source"] in ("status", "rule"):
            return
        if row["source"] == "candidate":
            if not self._inspection_page_current(row):
                return
            if state == "confirmed":
                self.page_data[row["page"]]["manual"].append({"rect": QRectF(*row["geometry"]), "replace_text": ""})
                self._capture_undo_state()
                self.btn_save.setEnabled(True)
                self.render_view()
            if state in ("confirmed", "excluded"):
                self._inspection_candidates.remove(row)
                self.refresh_review()
            return
        if row["source"] == "manual" and state == "confirmed":
            return  # user-created masks already represent an explicit choice
        if row["source"] == "manual" and state == "excluded":
            QMessageBox.information(self, "手工标记", "手工标记请在页面上右键删除；复核清单不会批量撤销手工标记。")
            return
        if state == "excluded":
            if self.word_doc is not None:
                match = self.word_data.get(row.get("key"), {}).get("ocr", [])
                selected = next((hit for hit in match if word_match_key(hit) == row.get("match_key")), None)
                try:
                    rule_rows = self.word_rule_review_rows()
                except RuntimeError:
                    QMessageBox.warning(self, "规则未完成", "请先简化或修正规则，再排除识别结果。")
                    return
                if selected and any(r["key"] == row["key"] and r["span"][0] < selected["end"] and r["span"][1] > selected["start"] for r in rule_rows):
                    QMessageBox.information(self, "此处同时有替换规则", "此处还会被明确的替换规则处理。请先到规则设置中调整，避免排除识别后仍被规则替换。")
                    return
            reply = QMessageBox.question(self, "仅排除此处", "只移除这处自动识别遮罩，其他手工标记或规则仍然有效。确认该识别无需脱敏？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        if self.doc is not None:
            entry = self.page_data.get(row["page"])
            if entry is None:
                return
            try:
                fingerprint = page_fingerprint(self.doc[row["page"]])
            except (ValueError, RuntimeError, OSError):
                QMessageBox.warning(self, "未改变复核判断", "无法核对页面内容，请重新打开文档后再复核。")
                return
            decisions = entry.setdefault("_review", [])
            prior = next((d for d in decisions if d["geometry"] == row["geometry"]), None)
            hit = next((h for h in entry.get(row["source"], []) if geometry(h) == row["geometry"]), None)
            if hit is None and state != "restore":
                return
            if state == "restore":
                if prior is None or prior.get("state") != "excluded":
                    return
                entry["ocr"].append({"rect": QRectF(*prior["geometry"]), "replace_text": prior.get("replace_text", "")})
                decisions.remove(prior)
            else:
                if prior:
                    decisions.remove(prior)
                decisions.append({"geometry": row["geometry"], "state": state,
                                  "fingerprint": fingerprint,
                                  "replace_text": hit.get("replace_text", "") if isinstance(hit, dict) else ""})
                if state == "excluded":
                    entry["ocr"].remove(hit)
            self._capture_undo_state()
            self.render_view()
        elif self.word_doc is not None:
            entry = self.word_data.get(row.get("key"))
            if entry is None:
                return
            self.capture_word_change()
            if state == "restore":
                entry.setdefault("_review", {}).pop(row["match_key"], None)
                removed = entry.get("_review_removed", {}).pop(row["match_key"], None)
                if removed:
                    entry["ocr"].append(removed)
                else:
                    self._set_info_bar_message("已恢复自动识别资格，请再次智能脱敏以恢复此处遮罩。")
            else:
                entry.setdefault("_review", {})[row["match_key"]] = state
                if state == "excluded":
                    entry.setdefault("_review_removed", {}).update({word_match_key(h): h for h in entry["ocr"] if word_match_key(h) == row["match_key"]})
                    entry["ocr"][:] = [h for h in entry["ocr"] if word_match_key(h) != row["match_key"]]
            self.persist_word_review()
            self.render_word_preview()
            self.refresh_word_review_buttons()
        self.btn_save.setEnabled(True)
        self.refresh_review()

    def persist_word_review(self):
        try:
            if self._word_review_store:
                self._word_review_store.save(self.word_data)
        except (OSError, ValueError, RuntimeError):
            self._set_info_bar_message("复核判断仅保留在本次会话，草稿写入失败。")

    def word_review_undo(self, redo=False):
        source = self._word_review_redo if redo else self._word_review_undo
        target = self._word_review_undo if redo else self._word_review_redo
        if not source or self.review_busy():
            return
        target.append({"data": copy.deepcopy(self.word_data), "meta": copy.deepcopy(getattr(self, "_word_scan_meta", None))})
        snapshot = source.pop()
        self.word_data = snapshot["data"]
        self._word_scan_meta = snapshot["meta"]
        self.persist_word_review()
        self.render_word_preview()
        self.refresh_word_review_buttons()
        self.refresh_review()

    def refresh_word_review_buttons(self):
        self.btn_undo.setEnabled(bool(getattr(self, "_word_review_undo", [])))
        self.btn_redo.setEnabled(bool(getattr(self, "_word_review_redo", [])))

    def word_rule_review_rows(self):
        from privacyguard.utils.helpers_word_rules import build_word_rule_matches
        key = (id(self.word_data), repr(self.word_replace_rules), self.replacement_text)
        if self._rule_review_failed == key:
            raise RuntimeError("Rule review incomplete")
        if self._rule_review_cache[0] != key:
            rows = []
            for block_key, entry in self.word_data.items():
                try:
                    matches = build_word_rule_matches(entry.get("text", ""), self.word_replace_rules, self.replacement_text)
                except RuntimeError:
                    self._rule_review_failed = key
                    raise
                for match in matches:
                    rows.append({"key": block_key, "source": "rule", "state": "confirmed", "span": [match["start"], match["end"]],
                                 "match_key": word_match_key(match), "label": entry.get("label", block_key) + " · 规则替换（规则设置修改）"})
            self._rule_review_cache = key, rows
        return self._rule_review_cache[1]

    def capture_word_change(self):
        self._word_review_undo.append({"data": copy.deepcopy(self.word_data), "meta": copy.deepcopy(getattr(self, "_word_scan_meta", None))})
        del self._word_review_undo[:-20]
        self._word_review_redo.clear()
        self.refresh_word_review_buttons()

    def _inspection_page_current(self, row):
        if row not in self._inspection_candidates or self.doc is None:
            return False
        index = row["page"]
        try:
            self._source_revision.verify()
            if index in self.page_data and 0 <= index < len(self.doc):
                if page_fingerprint(self.doc[index]) == row["fingerprint"]:
                    return True
        except (OSError, ValueError, RuntimeError, fitz.mupdf.FzErrorBase):
            pass
        self._inspection_candidates.remove(row)
        self._set_info_bar_message("原件或页面已变化，请重新打开或补查。")
        self.refresh_review()
        return False

    def start_page_inspection(self):
        if self.doc is None or self.review_busy() or not self._ensure_edit_permission():
            return
        from privacyguard.workers.inspection_worker import InspectionWorker
        try:
            self._source_revision.verify()
            fingerprint = page_fingerprint(self.doc[self.current_page])
            worker = InspectionWorker(self.doc.tobytes(), self.current_page, self)
        except ExportValidationError as error:
            self._set_info_bar_message(str(error))
            return
        except (IndexError, ValueError, RuntimeError, fitz.mupdf.FzErrorBase):
            self._set_info_bar_message("无法创建补查快照，请重试。")
            return
        self._inspection_candidates = []
        self._inspection_fingerprint = fingerprint
        self._inspection_status = "正在补查当前页，只生成候选，不自动遮罩。"
        self.active_worker = worker
        self.active_task_type = "inspection"
        self.btn_scan.setEnabled(False)
        self.btn_cancel_scan.setVisible(True)
        self.btn_cancel_scan.setEnabled(True)
        worker.result.connect(self._receive_inspection)
        worker.failed.connect(self._inspection_failed)
        worker.finished.connect(self._finish_inspection)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self.refresh_review()

    def _receive_inspection(self, page, candidates, status):
        if self.sender() is not self.active_worker or self._inspection_fingerprint is None:
            return
        self._inspection_candidates = [dict(c, page=page, source="candidate", state="pending",
                                           label=f'第 {page+1} 页 · 补查{c["kind"]}',
                                           fingerprint=self._inspection_fingerprint) for c in candidates]
        self._inspection_status = status

    def _inspection_failed(self, message):
        if self.sender() is self.active_worker:
            self._inspection_status = message

    def _finish_inspection(self):
        if self.sender() is not self.active_worker:
            return
        self.active_worker = None
        self.active_task_type = None
        self.btn_scan.setEnabled(True)
        self.btn_cancel_scan.hide()
        self.refresh_review()
