"""Regression checks for export availability after resetting and scanning a PDF."""

import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

import fitz
from PyQt6.QtCore import QRectF

from main import MainWindow, QMessageBox, _make_hit


class TestScanExportState(unittest.TestCase):
    def setUp(self):
        doc = fitz.open()
        doc.new_page()
        doc.new_page()
        doc.set_toc([[1, "SECRET_NAME", 1]])
        self.addCleanup(lambda: self.model.doc.close())
        self.model = SimpleNamespace(
            doc=doc, word_doc=None, page_data={
                0: {"ocr": [], "manual": []}, 1: {"ocr": [], "manual": []}},
            current_page=0, _pdf_modified=False, _restoring_snapshot=False,
            _undo_stack=[], _redo_stack=[], _UNDO_MAX=20, page_view_mode=False,
            _search_ocr_cache={}, _ocr_processed_pages=set(),
            _draft_timer=Mock(), _flush_session_draft=Mock(),
            _spill_oversized_undo_bytes=Mock(), _sweep_undo_spill_files=Mock(),
            _refresh_undo_redo_buttons=Mock(), _invalidate_grid_cache=Mock(),
            render_view=Mock(), _set_info_bar_message=Mock(),
            _maybe_refresh_visible_page=Mock(), _sync_ui_mode=Mock(),
            btn_save=Mock(), btn_scan=Mock(), btn_cancel_scan=Mock(), progress=Mock(),
            active_worker=None, _pending_error_msg=None, _targeted_hit_count=0,
            bookmark_redact_enabled=True, bookmark_panel=Mock(),
            custom_keyword_rules=[{"enabled": True, "find": "SECRET_NAME", "replace": "REDACTED"}],
        )
        for name in (
            "_build_undo_snapshot", "_apply_snapshot", "_refresh_derived_state_after_restore",
            "_capture_undo_state", "_load_pdf_toc", "_compute_display_toc",
            "_collect_active_toc_rules", "refresh_bookmark_preview",
            "_enable_export_for_bookmark_redaction",
        ):
            setattr(self.model, name, MethodType(getattr(MainWindow, name), self.model))
        MainWindow._seed_undo_baseline(self.model)
        self.reset()

    def reset(self):
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            MainWindow.reset_document(self.model)
        self.model.btn_save.setEnabled.assert_called_with(False)
        self.model.btn_save.reset_mock()

    def finish(self):
        with patch.object(QMessageBox, "information"):
            MainWindow._on_ocr_finished_safe(self.model, {})
        MainWindow._on_worker_finished(self.model)

    def scan_empty_pages(self):
        for page in self.model.page_data:
            MainWindow._on_ocr_page_result(self.model, page, [])

    def test_bookmark_only_change_enables_export_after_reset(self):
        self.scan_empty_pages()
        self.finish()
        self.model.bookmark_panel.load_toc.assert_called_with([[1, "REDACTED", 1]])
        self.model.btn_save.setEnabled.assert_called_with(True)
        self.assertEqual(self.model.doc.get_toc(), [[1, "SECRET_NAME", 1]])

    def test_unopened_bookmark_panel_does_not_block_export(self):
        self.model._toc_loaded = False
        self.scan_empty_pages()
        self.finish()
        self.model.btn_save.setEnabled.assert_called_with(True)

    def test_no_matching_bookmark_keeps_export_disabled(self):
        self.model.custom_keyword_rules[0]["find"] = "ABSENT"
        self.scan_empty_pages()
        self.finish()
        self.model.btn_save.setEnabled.assert_not_called()

    def test_disabled_bookmark_redaction_keeps_export_disabled(self):
        self.model.bookmark_redact_enabled = False
        self.scan_empty_pages()
        self.finish()
        self.model.btn_save.setEnabled.assert_not_called()

    def test_identical_replacement_is_not_a_change(self):
        self.model.custom_keyword_rules[0]["replace"] = "SECRET_NAME"
        self.scan_empty_pages()
        self.finish()
        self.model.btn_save.setEnabled.assert_not_called()

    def test_disabled_rule_keeps_export_disabled(self):
        self.model.custom_keyword_rules[0]["enabled"] = False
        self.scan_empty_pages()
        self.finish()
        self.model.btn_save.setEnabled.assert_not_called()

    def test_targeted_bookmark_rules_use_the_same_export_state(self):
        self.model._targeted_toc_rules = self.model.custom_keyword_rules
        self.model.custom_keyword_rules = []
        self.scan_empty_pages()
        self.finish()
        self.model.btn_save.setEnabled.assert_called_with(True)

    def test_retained_user_edits_are_the_export_source(self):
        self.model.toc_edited = True
        self.model.bookmark_panel.collect_toc.return_value = [[1, "PUBLIC", 1]]
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.finish()
        self.model.bookmark_panel.collect_toc.assert_called_once()
        self.model.btn_save.setEnabled.assert_not_called()

    def test_bookmark_read_error_does_not_enable_export(self):
        with patch.object(self.model.doc, "get_toc", side_effect=RuntimeError("synthetic")):
            self.finish()
        self.model.btn_save.setEnabled.assert_not_called()

    def test_empty_toc_keeps_export_disabled(self):
        self.model.doc.set_toc([])
        self.model._load_pdf_toc()
        self.scan_empty_pages()
        self.finish()
        self.model.btn_save.setEnabled.assert_not_called()

    def test_cancelled_scan_does_not_apply_bookmark_redaction(self):
        self.model.active_worker = Mock()
        self.model.active_worker.isRunning.return_value = False
        self.model.active_worker.isInterruptionRequested.return_value = True
        self.finish()
        self.model.btn_save.setEnabled.assert_not_called()
        self.assertFalse(self.model._bookmark_redact_applied)

    def test_failed_scan_does_not_apply_bookmark_redaction(self):
        self.model._pending_error_msg = "synthetic failure"
        with patch("main.QTimer.singleShot"):
            self.finish()
        self.model.btn_save.setEnabled.assert_not_called()
        self.assertFalse(self.model._bookmark_redact_applied)

    def test_body_hit_enables_export_and_later_empty_page_keeps_it(self):
        self.model.bookmark_redact_enabled = False
        hit = _make_hit(QRectF(10, 20, 50, 12), "*")
        shared = self.model.page_data[0]["ocr"]
        MainWindow._on_ocr_page_result(self.model, 0, [hit, hit])
        MainWindow._on_ocr_page_result(self.model, 1, [])
        self.finish()
        self.model.btn_save.setEnabled.assert_called_once_with(True)
        self.assertIs(self.model.page_data[0]["ocr"], shared)
        self.assertEqual(len(shared), 1)

    def test_targeted_hit_enables_export_without_duplicates(self):
        hit = _make_hit(QRectF(10, 20, 50, 12), "*")
        MainWindow._on_targeted_page_result(self.model, 0, [hit, hit])
        MainWindow._on_targeted_page_result(self.model, 0, [hit])
        self.model.btn_save.setEnabled.assert_called_once_with(True)
        self.assertEqual(len(self.model.page_data[0]["manual"]), 1)

    def test_reset_after_bookmark_scan_disables_export_again(self):
        self.scan_empty_pages()
        self.finish()
        self.model.btn_save.setEnabled.assert_called_with(True)
        self.reset()
        self.model.bookmark_panel.load_toc.assert_called_with([[1, "SECRET_NAME", 1]])
        self.assertFalse(self.model._bookmark_redact_applied)


if __name__ == "__main__":
    unittest.main()
