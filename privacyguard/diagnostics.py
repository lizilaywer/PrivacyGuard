"""Offline, synthetic-data smoke checks available in frozen builds."""

import json
import re
import socket
import tempfile
from pathlib import Path
from unittest.mock import patch


def run_self_test(window_factory=None):
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
        print(json.dumps({"status": "ok", "version": __version__, "checks": checks}, ensure_ascii=False))
        return 0
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        try:
            from privacyguard.ocr.rapidocr import RapidOCREngine
            if RapidOCREngine._shared_last_error:
                detail += "\n[engine] " + RapidOCREngine._shared_last_error[-3000:]
        except Exception:
            pass
        print(json.dumps({"status": "failed", "checks": checks, "error": detail}, ensure_ascii=False))
        return 1
