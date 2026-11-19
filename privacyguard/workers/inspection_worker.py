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
            from privacyguard.ocr.rapidocr import RapidOCREngine
            from privacyguard.ocr.local_inspection import inspect_page
            engine = RapidOCREngine()
            if not engine.is_available():
                raise RuntimeError("OCR unavailable")
            with fitz.open(stream=self.pdf_bytes, filetype="pdf") as doc:
                candidates, status = inspect_page(doc[self.page_index], engine, self.isInterruptionRequested)
                self.result.emit(self.page_index, candidates, status)
        except Exception as error:
            self.failed.emit("本页补查未完成（" + type(error).__name__ + "），请手工复核。")
