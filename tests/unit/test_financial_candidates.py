"""Fixed synthetic coverage for scoped account and invoice review."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import fitz
from PyQt6.QtCore import QRectF

from privacyguard.ocr.financial_candidates import collect_financial_candidates
from privacyguard.ui.mixins.review_mixin import ReviewMixin
from privacyguard.utils.export_transaction import save_verified_pdf
from privacyguard.workers.inspection_worker import InspectionWorker


class FinancialCandidateTests(unittest.TestCase):
    def setUp(self):
        self.doc = fitz.open()
        self.addCleanup(self.doc.close)
        self.page = self.doc.new_page(width=600, height=800)

    def put(self, text, x=40, y=50, **options):
        self.page.insert_text((x, y), text, fontname="china-s", fontsize=12, **options)

    def found(self):
        results, limited = collect_financial_candidates(self.page)
        self.assertFalse(limited)
        return results

    def text_at(self, hit):
        x, y, w, h = hit["geometry"]
        rect = fitz.Rect(x, y, x + w, y + h) * self.page.derotation_matrix
        return self.page.get_textbox(rect).strip()

    def test_repeated_number_requires_its_own_label(self):
        self.put("银行账号：234567890123")
        self.put("订单编号：234567890123", y=85)
        self.put("开户帐号：234567890123", y=120)
        hits = self.found()
        self.assertEqual(len(hits), 2)
        self.assertGreater(hits[1]["geometry"][1] - hits[0]["geometry"][1], 60)
        for hit in hits:
            self.assertEqual(self.text_at(hit), "234567890123")
            self.assertEqual(hit["kind"], "银行账号候选")
            self.assertNotIn("234567890123", repr(hit))

    def test_invoice_formats_and_unrelated_numbers(self):
        self.put("发票号码：12345678")
        self.put("发票号: 12345678901234567890", y=80)
        self.put("物流编号：12345678901234567890", y=110)
        self.put("号码：12345678", y=140)
        self.put("发票号码：12345678A", y=170)
        self.put("发票号码：12345678.00", y=200)
        self.put("发票号码：123456789012345678901", y=230)
        self.assertEqual([self.text_at(hit) for hit in self.found()], [
            "12345678", "12345678901234567890",
        ])

    def test_fullwidth_separators_map_to_original_glyphs(self):
        number = "１２３４ ５６７８-９０１２"
        self.put("收款账号：" + number + "；公开备注")
        hit, = self.found()
        self.assertEqual(self.text_at(hit), number)
        self.assertNotIn("１２３４", repr(hit))
        self.assertIn("标签", hit["reason"])

    def test_invisible_and_transparent_spans_are_ignored(self):
        self.put("银行账号：234567890123", render_mode=3)
        self.put("发票号码：12345678", y=80, fill_opacity=0)
        self.assertEqual(self.found(), [])

    def test_different_table_columns_and_rows_are_never_joined(self):
        self.put("银行账号：")
        self.put("234567890123", x=260)
        self.put("发票号码：", y=100)
        self.put("12345678", y=120)
        self.put("开户账号：234567", y=150)
        self.put("890123", x=260, y=150)
        self.put("银行账号：234567890123 4567890", y=180)
        self.assertEqual(self.found(), [])

    def test_same_line_split_fonts_are_supported(self):
        self.put("发票号码：")
        self.page.insert_text((102, 50), "12345678", fontname="helv", fontsize=12)
        hit, = self.found()
        self.assertEqual(self.text_at(hit), "12345678")

    def test_each_page_rotation_maps_back_to_the_same_text(self):
        self.put("发票号码：12345678；公开备注")
        self.page.set_cropbox(fitz.Rect(12, 12, 580, 760))
        for angle in (0, 90, 180, 270):
            with self.subTest(angle=angle):
                self.page.set_rotation(angle)
                hit, = self.found()
                self.assertEqual(self.text_at(hit), "12345678")

    def test_cancellation_and_limits_do_not_claim_full_coverage(self):
        for index in range(45):
            self.put("发票号码：12345678", y=30 + 16 * index)
        cancelled, limited = collect_financial_candidates(self.page, lambda: True)
        self.assertEqual((cancelled, limited), ([], False))
        results, limited = collect_financial_candidates(self.page)
        self.assertTrue(limited)
        self.assertEqual(len(results), 40)

    def test_financial_candidates_survive_ocr_unavailable(self):
        self.put("发票号码：12345678")
        worker = InspectionWorker(self.doc.tobytes(), 0)
        results = []
        worker.result.connect(lambda *args: results.append(args))
        with patch("privacyguard.ocr.rapidocr.RapidOCREngine", side_effect=RuntimeError("PRIVATE")):
            worker.run()
        (index, hits, status), = results
        self.assertEqual(index, 0)
        self.assertEqual(len(hits), 1)
        self.assertIn("小字和二维码补查未完成", status)
        self.assertNotIn("PRIVATE", status)

    def test_deleted_page_candidate_is_discarded_before_confirmation(self):
        row = {"page": 1, "source": "candidate", "fingerprint": "previous page"}
        view = SimpleNamespace(doc=self.doc, page_data={0: {"manual": []}},
                               _source_revision=Mock(), _inspection_candidates=[row],
                               _set_info_bar_message=Mock(), refresh_review=Mock())
        self.assertFalse(ReviewMixin._inspection_page_current(view, row))
        self.assertEqual(view._inspection_candidates, [])
        self.assertEqual(view.page_data[0]["manual"], [])
        view.refresh_review.assert_called_once()

    def test_queued_worker_from_previous_document_cannot_replace_current_rows(self):
        old_worker = object()
        current_worker = object()
        current_row = {"page": 0, "reason": "current"}
        view = SimpleNamespace(sender=lambda: old_worker, active_worker=current_worker,
                               _inspection_fingerprint="current", _inspection_candidates=[current_row],
                               _inspection_status="current")
        ReviewMixin._receive_inspection(view, 1, [{"kind": "银行账号候选"}], "old")
        ReviewMixin._inspection_failed(view, "old failure")
        ReviewMixin._finish_inspection(view)
        self.assertEqual(view._inspection_candidates, [current_row])
        self.assertEqual(view._inspection_status, "current")
        self.assertIs(view.active_worker, current_worker)

    def test_verified_export_only_removes_chosen_position(self):
        self.put("银行账号：234567890123")
        self.put("订单编号：234567890123", y=85)
        self.put("发票号码：12345678", y=120)
        self.page.set_rotation(90)
        account, invoice = self.found()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, target = root / "source.pdf", root / "export.pdf"
            original = self.doc.tobytes()
            source.write_bytes(original)
            display = QRectF(*account["geometry"])
            area = fitz.Rect(display.left(), display.top(), display.right(), display.bottom())
            self.page.add_redact_annot(area * self.page.derotation_matrix, fill=(0, 0, 0))
            self.page.apply_redactions()
            save_verified_pdf(self.doc, target, {"garbage": 2, "clean": True},
                              {0: {"manual": [display]}}, source)
            with fitz.open(target) as exported:
                saved = exported[0]
                self.assertEqual(saved.get_text().count("234567890123"), 1)
                self.assertIn("订单编号", saved.get_text())
                self.assertIn("银行账号", saved.get_text())
                self.assertIn("12345678", saved.get_text())
                self.assertEqual(saved.get_textbox(area * saved.derotation_matrix).strip(), "")
            self.assertEqual(invoice["kind"], "发票号码候选")
            self.assertEqual(source.read_bytes(), original)
