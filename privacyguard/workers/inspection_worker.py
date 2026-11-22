"""Optional current-page inspection; isolated document and lazy shared OCR."""
from PyQt6.QtCore import QThread, pyqtSignal


class InspectionWorker(QThread):
    result = pyqtSignal(int, list, str)
    failed = pyqtSignal(str)

    def __init__(self, pdf_bytes, page_index, parent=None):
        super().__init__(parent)
        self.pdf_bytes, self.page_index = pdf_bytes, page_index

    def run(self):
        try:
            import fitz
            from privacyguard.ocr.financial_candidates import collect_financial_candidates

            with fitz.open(stream=self.pdf_bytes, filetype="pdf") as doc:
                page = doc[self.page_index]
                financial, note = [], ""
                try:
                    financial, limited = collect_financial_candidates(page, self.isInterruptionRequested)
                    if limited:
                        note = "账票补查达到上限，部分文字未检查。"
                except Exception:
                    note = "账票文字补查未完成，请手工复核。"
                if self.isInterruptionRequested():
                    self.result.emit(self.page_index, financial, "已取消，保留已找到的候选")
                    return
                try:
                    from privacyguard.ocr.rapidocr import RapidOCREngine
                    from privacyguard.ocr.local_inspection import inspect_page

                    engine = RapidOCREngine()
                    if not engine.is_available():
                        raise RuntimeError("OCR unavailable")
                    candidates, status = inspect_page(page, engine, self.isInterruptionRequested)
                except Exception:
                    candidates, status = [], "小字和二维码补查未完成，请手工复核。"
                self.result.emit(self.page_index, financial + candidates, "\n".join(filter(None, (status, note))))
        except Exception as error:
            self.failed.emit("本页补查未完成（" + type(error).__name__ + "），请手工复核。")
