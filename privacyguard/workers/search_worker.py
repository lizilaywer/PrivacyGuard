"""全文搜索 Worker（从 main.py 提取）。

cp81: PDF 文字层 + 扫描页 OCR 全文搜索，支持取消与会话级 OCR 缓存。
"""

import fitz  # PyMuPDF
import numpy as np
import cv2

from PyQt6.QtCore import QThread, pyqtSignal

from privacyguard.utils.helpers_pdf import collect_text_hits
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

    def __init__(self, pdf_bytes, keyword, ocr_cache, parent=None):
        # v40.1.4 修复：补 parent 形参——main.py 调用点传 parent=self（防 GC 销毁
        # 运行中线程的微秒级竞态），此前模块层无此形参导致全文搜索构造即 TypeError。
        super().__init__(parent)
        self.pdf_bytes = pdf_bytes
        self.keyword = keyword
        # 会话级 OCR 文本缓存 dict 引用（页码 -> 识别文本）；GIL 下单键读写原子，
        # 主线程仅在 worker 结束后的下次搜索读取
        self.ocr_cache = ocr_cache

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
        doc = None
        total_hits = 0
        try:
            doc = fitz.open(stream=self.pdf_bytes, filetype="pdf")
            total = len(doc)
            engine = None  # 懒加载：全文字层文档不碰 OCR
            for i in range(total):
                if self.isInterruptionRequested():
                    break
                self.progress_signal.emit(i + 1, total)
                page = doc[i]
                text = (page.get_text() or "").strip()
                spans = None  # cp82: OCR 页行区间→矩形映射；文字层页用 search_for
                if text:
                    hits = collect_text_hits(text, self.keyword)
                    if not hits:
                        continue
                    # cp82: 文字层命中矩形：search_for 按页面顺序返回，与文本命中
                    # 顺序逐个配对；旋转页乘 rotation_matrix 转 display 坐标
                    rects = []
                    try:
                        found = page.search_for(self.keyword) or []
                        for rr in found:
                            rr = fitz.Rect(rr)
                            if getattr(page, "rotation", 0):
                                rr = (rr * page.rotation_matrix)
                                rr.normalize()
                            rects.append((rr.x0, rr.y0, rr.width, rr.height))
                    except Exception:
                        rects = []
                    for n, (_idx, before, kw_text, after) in enumerate(hits):
                        rect_t = rects[n] if n < len(rects) else None
                        self.hit_signal.emit(i, before, kw_text, after, rect_t)
                        total_hits += 1
                    continue
                # 扫描页：缓存 → OCR（cp82 缓存结构 {'text','spans'}）
                cached = self.ocr_cache.get(i)
                if cached is None:
                    if engine is None:
                        try:
                            from privacyguard.ocr.rapidocr import RapidOCREngine
                            eng = RapidOCREngine()
                            engine = eng if eng.is_available() else False
                        except Exception as e:
                            logger.warning("[cp81] OCR 引擎加载失败: %s: %s", type(e).__name__, e)
                            engine = False
                    if engine:
                        try:
                            ocr_text, ocr_spans = self._ocr_page_text(page, engine)
                        except Exception as e:
                            logger.warning("[cp81] 页 %s OCR 失败: %s: %s", i, type(e).__name__, e)
                            ocr_text, ocr_spans = "", []
                    else:
                        ocr_text, ocr_spans = "", []
                    cached = {"text": ocr_text, "spans": ocr_spans}
                    self.ocr_cache[i] = cached
                if isinstance(cached, dict):
                    text = cached.get("text", "")
                    spans = cached.get("spans") or []
                else:
                    text = str(cached)  # 防御：旧结构（纯文本）降级为无矩形
                    spans = []
                for _idx, before, kw_text, after in collect_text_hits(text, self.keyword):
                    rect_t = None
                    for s, e, r_t in spans:
                        if s <= _idx < e:
                            rect_t = r_t
                            break
                    self.hit_signal.emit(i, before, kw_text, after, rect_t)
                    total_hits += 1
        except Exception as e:
            self.error_signal.emit(f"{type(e).__name__}: {e}")
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass
        self.finished_signal.emit(total_hits)
