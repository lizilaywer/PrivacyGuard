"""DEAD CODE — Phase 1 library export. The _ModularOCRWorker.run loop does NOT
call collect_full_page_ocr_hits; the existing line 397-398 promotion through
collect_image_block_ocr_hits is the full-page OCR fallback path in Phase 1 (W2).
This module exists for Phase 2+ direct invocations and for tests. Do NOT wire it
into the worker run loop without a corresponding plan task.
"""
import cv2
import fitz
import numpy as np

from privacyguard.ocr.mixed_pdf import iter_ocr_lines


def render_full_page_to_bgr(page, scan_scale: float):
    """将整页 PDF 渲染为 OpenCV BGR ndarray；返回 None on error。

    默认 render_fn（collect_full_page_ocr_hits 的 DI 入口）。
    """
    try:
        pix = page.get_pixmap(
            matrix=fitz.Matrix(scan_scale, scan_scale), alpha=False,
        )
        img_data = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
        return cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def collect_full_page_ocr_hits(
    page,
    scan_scale: float,
    recognize_fn,
    calculate_rect_fn,
    clip_to_page_rect_fn=None,
    preprocess_fn=None,
    render_fn=None,
):
    """D-03 / D-01 纯函数式整页 OCR 命中收集（dependency-injection 形态）。

    与 collect_image_block_ocr_hits 形态一致；返回 [(x0, y0, w, h), ...] 元组列表。
    Library function —— Phase 1 worker run loop 不直接调用（W2 reconciliation）。
    """
    render = render_fn or render_full_page_to_bgr
    try:
        img_bgr = render(page, scan_scale)
    except Exception:
        return []
    if img_bgr is None or getattr(img_bgr, "size", 0) == 0:
        return []

    scan_img = preprocess_fn(img_bgr) if preprocess_fn else img_bgr

    try:
        ocr_results = recognize_fn(scan_img)
    except Exception:
        return []

    page_rect = page.rect
    sx = (page_rect.x1 - page_rect.x0) / scan_img.shape[1]
    sy = (page_rect.y1 - page_rect.y0) / scan_img.shape[0]

    hits = []
    for box, text in iter_ocr_lines(ocr_results):
        if not text:
            continue
        local_rect = calculate_rect_fn(box, text, (0, len(text)), scan_img)
        if local_rect is None:
            continue
        page_x0 = page_rect.x0 + local_rect[0] * sx
        page_y0 = page_rect.y0 + local_rect[1] * sy
        page_x1 = page_rect.x0 + (local_rect[0] + local_rect[2]) * sx
        page_y1 = page_rect.y0 + (local_rect[1] + local_rect[3]) * sy
        hits.append((page_x0, page_y0, page_x1 - page_x0, page_y1 - page_y0))

    return hits


__all__ = ["render_full_page_to_bgr", "collect_full_page_ocr_hits"]