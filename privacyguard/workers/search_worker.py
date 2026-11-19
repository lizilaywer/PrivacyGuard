"""全文搜索 Worker（从 main.py 提取）。

cp81: PDF 文字层 + 扫描页 OCR 全文搜索，支持取消与会话级 OCR 缓存。
"""

import fitz  # PyMuPDF
import numpy as np
import cv2

from PyQt6.QtCore import QThread, pyqtSignal

from privacyguard.utils.logger import get_logger

logger = get_logger("search_worker")


class DocSearchWorker(QThread):
    """cp81: 全文搜索 worker（PDF 文字层 + 扫描页 OCR）。

    - 输入 pdf_bytes 快照（doc.tobytes()）：与旋转/删页/去水印后的当前状态
      及页序一致，worker 内 fitz.open(stream=...) 与主线程 doc 隔离
    - 文字层页直接搜；无文字层（扫描页）查 ocr_cache，缺失才 RapidOCR 全页
      识别并回写缓存（会话级，二次搜索免重复识别）
    - 支持 requestInterruption() 取消
    """

    progress_signal = pyqtSignal(int, int)   # (当前页序, 总页数)
    # cp82: 命中信号末位携带高亮矩形 (x, y, w, h) display 坐标元组或 None
    hit_signal = pyqtSignal(int, str, str, str, object)  # (页码, 前段, 关键词, 后段, rect)
    finished_signal = pyqtSignal(int)        # 总命中数（取消时为已找到数）
    error_signal = pyqtSignal(str)

    def __init__(self, pdf_bytes, keyword, ocr_cache, parent=None, normalize=False):
        # v40.1.4 修复：补 parent 形参——main.py 调用点传 parent=self（防 GC 销毁
        # 运行中线程的微秒级竞态），此前模块层无此形参导致全文搜索构造即 TypeError。
        super().__init__(parent)
        self.pdf_bytes = pdf_bytes
        self.keyword = keyword
        # 会话级 OCR 文本缓存 dict 引用（页码 -> 识别文本）；GIL 下单键读写原子，
        # 主线程仅在 worker 结束后的下次搜索读取
        self.ocr_cache = ocr_cache
        self.normalize = normalize

    def _ocr_page_text(self, page, engine):
        """全页 2x 渲染后 OCR，按阅读顺序拼接行文本。

        cp82: 返回 (joined_text, spans)；spans 为 [(start, end, rect_tuple)]，
        记录每行在拼接文本中的区间与其 PDF display 坐标矩形（2x 像素/2），
        供命中位置回查所在行矩形做高亮定位。
        """
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        # P2 reshape 通道守卫：仅 3/4 通道可安全 reshape+cvtColor，其余跳过该页 OCR
        if pix.n not in (3, 4):
            return "", []
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n >= 4:
            img = img[:, :, :3]
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        results = engine.recognize(img_bgr) or []

        def _reading_order(res):
            try:
                xs = [p[0] for p in res.box]
                ys = [p[1] for p in res.box]
                return (min(ys), min(xs))
            except (TypeError, ValueError, IndexError):
                return (0.0, 0.0)

        parts = []
        spans = []
        offset = 0
        # P2: 与 OCRWorker 一致的置信度门，避免低置信噪声行污染全文搜索结果与 OCR 缓存
        _MIN_OCR_CONFIDENCE = 0.5
        for r in sorted(results, key=_reading_order):
            if getattr(r, "confidence", 1.0) < _MIN_OCR_CONFIDENCE:
                continue
            line = getattr(r, "text", "") or ""
            if not line:
                continue
            rect_t = None
            try:
                xs = [p[0] for p in r.box]
                ys = [p[1] for p in r.box]
                # 2x 渲染像素 → PDF display 点坐标
                rect_t = (min(xs) / 2.0, min(ys) / 2.0,
                          (max(xs) - min(xs)) / 2.0, (max(ys) - min(ys)) / 2.0)
            except (TypeError, ValueError, IndexError):
                pass
            spans.append((offset, offset + len(line), rect_t))
            parts.append(line)
            offset += len(line) + 1  # +1 为换行符
        # 不做 strip：spans 偏移与 join 结果严格对齐（parts 已滤空行）
        return "\n".join(parts), spans

    def run(self):
        from privacyguard.ocr.search_content import (bind_document_cache, bind_model_cache,
                                                     cache_result, ocr_search_regions)
        from privacyguard.ocr.mixed_pdf import collect_embedded_image_clip_rects
        from privacyguard.utils.text_candidates import collect_search_hits
        doc = None
        total_hits = 0
        success = True
        try:
            bind_document_cache(self.ocr_cache, self.pdf_bytes)
            doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
            engine = None
            model_bound = False
            for i, page in enumerate(doc):
                if self.isInterruptionRequested():
                    break
                self.progress_signal.emit(i+1, len(doc))
                text = page.get_text() or ""
                if text.strip():
                    used = {}
                    for _idx, before, value, after in collect_search_hits(text, self.keyword, self.normalize):
                        found = page.search_for(value) or []
                        occurrence = used.get(value.casefold(), 0)
                        used[value.casefold()] = occurrence+1
                        rect = found[occurrence] if occurrence < len(found) else None
                        if rect is not None and page.rotation:
                            rect = (rect * page.rotation_matrix).normalize()
                        bounds = (rect.x0, rect.y0, rect.width, rect.height) if rect is not None else None
                        self.hit_signal.emit(i, before, value, after, bounds)
                        total_hits += 1
                image_clips = collect_embedded_image_clip_rects(page.get_text("dict"))
                mixed = bool(text.strip())
                if mixed and not image_clips:
                    continue
                if not mixed and i not in self.ocr_cache and not image_clips and not page.get_drawings():
                    continue
                if not model_bound:
                    bind_model_cache(self.ocr_cache)
                    model_bound = True
                cached = self.ocr_cache.get(i)
                if cached is None:
                    if engine is None:
                        from privacyguard.ocr.rapidocr import RapidOCREngine
                        engine = RapidOCREngine()
                        if not engine.is_available():
                            raise RuntimeError("OCR unavailable")
                    ocr_text, spans = ocr_search_regions(page, engine, mixed, self.isInterruptionRequested)
                    cached = {"text": ocr_text, "spans": spans, "mixed": mixed}
                    cache_result(self.ocr_cache, i, cached)
                text = cached.get("text", "") if isinstance(cached, dict) else str(cached)
                spans = cached.get("spans", []) if isinstance(cached, dict) else []
                for index, before, value, after in collect_search_hits(text, self.keyword, self.normalize):
                    bounds = next((r for start, end, r in spans if start <= index < end), None)
                    self.hit_signal.emit(i, before, value, after, bounds)
                    total_hits += 1
        except InterruptedError:
            pass
        except Exception as error:
            success = False
            self.error_signal.emit("搜索未完成（" + type(error).__name__ + "），请复核未检视的图片区域。")
        finally:
            if doc is not None:
                doc.close()
        if success:
            self.finished_signal.emit(total_hits)
