"""Offline, synthetic-data smoke checks available in frozen builds."""

import json
import re
import socket
import tempfile
from pathlib import Path
from unittest.mock import patch


def synthetic_sparse_pdf(*, reference_missing=False, explicitly_free=False):
    """Object 12 is absent, but item 13 makes it part of the numeric range."""
    data = bytearray(b"%PDF-1.4\n")
    offsets = {}

    def add(number, value):
        offsets[number] = len(data)
        data.extend(f"{number} 0 obj\n".encode() + value + b"\nendobj\n")

    add(1, b"<< /Type /Catalog /Pages 2 0 R /Metadata 13 0 R >>")
    add(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    contents = b"[5 0 R 12 0 R]" if reference_missing else b"5 0 R"
    add(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 400] "
           b"/Resources << /Font << /F1 4 0 R >> >> /Contents " + contents + b" >>")
    add(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    stream = b"BT /F1 12 Tf 20 350 Td (TEST_SECRET) Tj 0 -30 Td (KEEP_VISIBLE) Tj ET"
    add(5, b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
    xml = b"<metadata>XML_TEST_CANARY</metadata>"
    add(13, b"<< /Type /Metadata /Subtype /XML /Length %d >>\nstream\n%s\nendstream" % (len(xml), xml))
    xref = len(data)
    data.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for number in range(1, 6):
        data.extend(f"{offsets[number]:010d} 00000 n \n".encode())
    if explicitly_free:
        data.extend(b"6 7\n" + b"0000000000 00000 f \n" * 7)
    data.extend(f"13 1\n{offsets[13]:010d} 00000 n \ntrailer\n"
                f"<< /Size 14 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


def run_self_test(window_factory=None, report_path=None):
    import cv2
    import fitz
    import mammoth
    import numpy as np
    import pyexpat
    from decimal import Decimal
    from docx import Document
    from PIL import Image
    from PyQt6.QtWidgets import QApplication
    from privacyguard import __version__
    from privacyguard.ocr.rapidocr import RapidOCREngine
    from privacyguard.utils.app_paths import resource_root
    from privacyguard.utils.helpers_pdf import build_result_doc_from_segments
    from privacyguard.utils.helpers_word_rules import build_word_rule_matches
    from privacyguard.utils.helpers_word_doc import replace_matches_in_paragraph

    checks = {}
    report = {"status": "failed", "version": __version__, "checks": checks}
    try:
        # No network is permitted, including an implicit first-use model download.
        with patch.object(socket.socket, "connect", side_effect=RuntimeError("Network forbidden in self-test")):
            parser = pyexpat.ParserCreate()
            parser.Parse("<document>ok</document>", True)
            checks["xml"] = True
            checks["decimal"] = Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
            with tempfile.TemporaryDirectory(prefix="pg_selftest_") as tmp:
                root = Path(tmp)
                image = root / "embedded.png"
                Image.new("RGB", (40, 30), "blue").save(image)
                doc = Document()
                doc.add_paragraph("PHONE 13812345678")
                doc.add_picture(str(image))
                path = root / "embedded.docx"
                doc.save(path)
                with path.open("rb") as handle:
                    converted = mammoth.convert_to_html(handle).value
                if "<img" not in converted or "13812345678" not in converted:
                    raise AssertionError("Embedded-image Word conversion failed")
                matches = build_word_rule_matches(doc.paragraphs[0].text,
                          [{"enabled": True, "mode": "exact", "find": "13812345678", "replace": "*"}], "*")
                replace_matches_in_paragraph(doc.paragraphs[0], matches)
                doc.save(root / "redacted.docx")
                if "13812345678" in Document(root / "redacted.docx").paragraphs[0].text:
                    raise AssertionError("Word export replacement failed")
                checks["docx_image_preview_and_replace"] = True
                with fitz.open() as pdf:
                    p = pdf.new_page(width=300, height=400)
                    p.insert_text((10, 40), "PUBLIC")
                    p.insert_text((10, 250), "SECRET_OUTSIDE")
                    with build_result_doc_from_segments(pdf, [[{"src_pno": 0, "y_min": 0, "y_max": 100}]]) as result:
                        raw = result.tobytes(garbage=2, clean=True)
                        with fitz.open(stream=raw, filetype="pdf") as saved:
                            secret = b"SECRET_OUTSIDE".hex().encode()
                            for xref in range(1, saved.xref_length()):
                                if saved.xref_is_stream(xref) and secret in saved.xref_stream(xref).lower():
                                    raise AssertionError("Extracted PDF retained hidden source")
                checks["pdf_vector_region_security"] = True
                from privacyguard.utils.guarded_regex import find_spans, _service
                if find_spans(r"1[3-9]\d{9}", "PHONE 13812345678") != [[6,17]]:
                    raise AssertionError("Isolated regex process failed")
                _service.close()
                checks["isolated_regex_worker"] = True
                from privacyguard.utils.word_parts import apply_word_rules
                from privacyguard.utils.export_transaction import save_verified_docx, save_verified_pdf
                rich = Document()
                rich.add_paragraph("SECRET KEEP")
                rich.core_properties.author = "SECRET"
                apply_word_rules(rich, [{"enabled":True,"mode":"exact","find":"SECRET","replace":"REMOVED"}], "REMOVED")
                save_verified_docx(rich, root/"verified.docx")
                if "SECRET" in Document(root/"verified.docx").core_properties.author:
                    raise AssertionError("Word property redaction failed")
                from privacyguard.utils.pdf_sanitize import prepare_pdf_output
                with fitz.open() as hidden_pdf:
                    hidden_pdf.new_page().insert_text((20,40), "KEEP")
                    hidden_pdf.embfile_add("hidden.txt", b"SECRET_ATTACHMENT")
                    rebuilt = prepare_pdf_output(hidden_pdf, "raster")
                    try:
                        save_verified_pdf(rebuilt, root/"raster.pdf", {"garbage":4}, {}, policy="raster")
                    finally:
                        rebuilt.close()
                checks["verified_word_and_pixel_pdf_exports"] = True
                from privacyguard.utils.pdf_inventory import inventory_pdf
                from privacyguard.utils.export_transaction import ExportValidationError
                with fitz.open(stream=synthetic_sparse_pdf(), filetype="pdf") as sparse:
                    if inventory_pdf(sparse)["xml"] != 1:
                        raise AssertionError("Sparse PDF inventory lost attached metadata")
                    page = sparse[0]
                    region = page.search_for("TEST_SECRET")[0]
                    page.add_redact_annot(region, fill=(0, 0, 0))
                    page.apply_redactions()
                    from PyQt6.QtCore import QRectF
                    masks = {0: {"manual": [QRectF(region.x0, region.y0, region.width, region.height)]}}
                    prepare_pdf_output(sparse, "sanitize")
                    target = root / "sparse-verified.pdf"
                    save_verified_pdf(sparse, target, {"garbage": 2, "clean": True}, masks, policy="sanitize")
                    with fitz.open(target) as saved:
                        text = saved[0].get_text()
                        if "TEST_SECRET" in text or "KEEP_VISIBLE" not in text or saved.get_xml_metadata():
                            raise AssertionError("Sparse PDF export verification failed")
                with fitz.open(stream=synthetic_sparse_pdf(reference_missing=True), filetype="pdf") as incomplete:
                    try:
                        inventory_pdf(incomplete)
                    except ExportValidationError:
                        pass
                    else:
                        raise AssertionError("Missing referenced PDF object was ignored")
                checks["sparse_pdf_export_and_broken_reference_guard"] = True
                from privacyguard.utils.document_source import SourceRevision
                source = root / "reviewed.pdf"
                source.write_bytes(synthetic_sparse_pdf())
                revision = SourceRevision.capture(source)
                output = root / "existing.pdf"
                output.write_bytes(b"previous export")
                with fitz.open(stream=source.read_bytes(), filetype="pdf") as reviewed:
                    with fitz.open() as replacement:
                        replacement.new_page()
                        replacement.save(source)
                    try:
                        save_verified_pdf(reviewed, output, {"garbage": 2, "clean": True}, {}, source,
                                          source_revision=revision)
                    except ExportValidationError as exc:
                        if "原件在打开后已更新" not in str(exc):
                            raise
                    else:
                        raise AssertionError("Changed source was accepted")
                if output.read_bytes() != b"previous export" or any(root.glob(".pg-export-*")):
                    raise AssertionError("Blocked export changed the destination or left a temporary file")
                checks["reviewed_source_and_destination_guard"] = True
                from privacyguard.ocr.financial_candidates import collect_financial_candidates
                with fitz.open() as fields_pdf:
                    page = fields_pdf.new_page()
                    number = "１２３４ ５６７８-９０１２"
                    page.insert_text((30, 60), "银行账号：" + number, fontname="china-s")
                    page.insert_text((30, 90), "订单编号：" + number, fontname="china-s")
                    page.set_rotation(90)
                    hits, limited = collect_financial_candidates(page)
                    if limited or len(hits) != 1 or number in repr(hits):
                        raise AssertionError("Labeled finance field was not isolated")
                    x, y, width, height = hits[0]["geometry"]
                    area = fitz.Rect(x, y, x + width, y + height) * page.derotation_matrix
                    if page.get_textbox(area).strip() != number:
                        raise AssertionError("Finance candidate missed its original character geometry")
                checks["position_scoped_financial_candidates"] = True
                from privacyguard.ocr.pdf_keyword_hits import collect_pdf_keyword_hits
                from privacyguard.utils.literal_keywords import compile_keyword_patterns
                with fitz.open() as phrases:
                    page = phrases.new_page()
                    page.insert_text((30, 60), "2025 年预算与2026 年预算", fontname="china-s")
                    matches = list(collect_pdf_keyword_hits(page, compile_keyword_patterns(["2025年"])))
                    if len(matches) != 1 or page.get_textbox(matches[0][0]).strip() != "2025 年":
                        raise AssertionError("Full PDF keyword was split or wrong occurrence located")
                    area = matches[0][0]
                    masks = {0: {"manual": [QRectF(area.x0, area.y0, area.width, area.height)]}}
                    warned = root / "warned.pdf"
                    warned.write_bytes(b"previous output")
                    if save_verified_pdf(phrases, warned, {}, masks,
                                         confirm_text_warnings=lambda pages: pages != (1,)) is not None:
                        raise AssertionError("Returning to review published an export")
                    if warned.read_bytes() != b"previous output":
                        raise AssertionError("Warning choice changed the previous output")
                    if save_verified_pdf(phrases, warned, {}, masks,
                                         confirm_text_warnings=lambda pages: pages == (1,)) != 1:
                        raise AssertionError("Explicit warning confirmation did not publish")
                    with fitz.open(warned) as saved:
                        if "2026 年预算" not in saved[0].get_text():
                            raise AssertionError("Confirmed warning output failed reopen check")
                checks["literal_phrase_and_export_warning_choice"] = True
                img = np.full((180, 900, 3), 255, dtype=np.uint8)
                cv2.putText(img, "PHONE 13812345678", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.7, (0, 0, 0), 3)
                recognized = "".join(r.text for r in RapidOCREngine().recognize(img))
                if "13812345678" not in re.sub(r"\s+", "", recognized):
                    raise AssertionError("Real offline OCR inference did not recognize synthetic phone")
                checks["offline_ocr_real_inference"] = True
                checks["version_resource"] = (resource_root() / "version.txt").read_text().strip() == __version__
                if window_factory:
                    from PyQt6.QtWidgets import QMessageBox
                    def unexpected_dialog(*_args, **_kwargs):
                        raise AssertionError("Unexpected error dialog in GUI smoke check")
                    app = QApplication.instance() or QApplication(["PrivacyGuard-self-test"])
                    with patch.object(QMessageBox, "critical", side_effect=unexpected_dialog):
                        window = window_factory()
                        window._open_word_docx(str(path))
                        if not window.word_doc or "word_image_" not in window._word_base_html:
                            raise AssertionError("Application Word image preview was not built")
                        app.processEvents()
                        window.close()
                        app.processEvents()
                    checks["mainwindow_and_docx_open_close"] = True
        if not all(checks.values()):
            raise AssertionError("One or more smoke checks failed")
        report["status"] = "ok"
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        try:
            from privacyguard.ocr.rapidocr import RapidOCREngine
            if RapidOCREngine._shared_last_error:
                detail += "\n[engine] " + RapidOCREngine._shared_last_error[-3000:]
        except Exception:
            pass
        report["error"] = detail
    payload = json.dumps(report, ensure_ascii=False)
    if report_path is not None:
        Path(report_path).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return int(report["status"] != "ok")
