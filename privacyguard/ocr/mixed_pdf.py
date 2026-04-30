"""混合型 PDF 扫描辅助逻辑。"""

import re

import cv2
import fitz
import numpy as np


def compile_active_patterns(patterns):
    """编译启用的正则规则，跳过特殊标记和非法表达式。"""
    compiled = []
    for pattern in patterns or []:
        if not pattern or pattern == "__SEAL_DETECTION__":
            continue
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            continue
    return compiled


def collect_embedded_image_clip_rects(page_dict, min_width=24, min_height=24, min_area=400):
    """从 page.get_text('dict') 中提取有效图片块区域。"""
    if not isinstance(page_dict, dict):
        return []

    clip_rects = []
    seen = set()
    for block in page_dict.get("blocks", []):
        if block.get("type") != 1:
            continue

        bbox = block.get("bbox")
        if not bbox or len(bbox) != 4:
            continue

        x0, y0, x1, y1 = (float(v) for v in bbox)
        width = x1 - x0
        height = y1 - y0
        if width < min_width or height < min_height or width * height < min_area:
            continue

        key = (round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2))
        if key in seen:
            continue
        seen.add(key)
        clip_rects.append((x0, y0, x1, y1))

    return clip_rects


def render_pdf_clip_to_bgr(page, clip_rect, scan_scale):
    """将 PDF 页面裁剪区域渲染为 OpenCV BGR 图像。"""
    clip = fitz.Rect(*clip_rect)
    pix = page.get_pixmap(
        matrix=fitz.Matrix(scan_scale, scan_scale),
        clip=clip,
        alpha=False,
    )
    img_data = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
    return cv2.imdecode(img_data, cv2.IMREAD_COLOR)


def iter_ocr_lines(ocr_results):
    """统一遍历 OCR 结果，兼容 OCRResult 和 RapidOCR 原始结构。"""
    for result in ocr_results or []:
        if hasattr(result, "box") and hasattr(result, "text"):
            yield result.box, result.text
            continue

        if isinstance(result, (list, tuple)) and len(result) >= 2:
            yield result[0], result[1]


def collect_image_block_ocr_hits(
    page,
    patterns,
    scan_scale,
    recognize_fn,
    calculate_rect_fn,
    clip_to_page_rect_fn,
    preprocess_fn=None,
    page_dict=None,
    render_clip_fn=None,
    image_clip_rects=None,
):
    """对嵌入图片区域执行 OCR，并返回页面坐标系下的命中矩形。"""
    compiled_patterns = compile_active_patterns(patterns)
    if not compiled_patterns:
        return []

    if image_clip_rects is None:
        if page_dict is None:
            page_dict = page.get_text("dict")
        image_clip_rects = collect_embedded_image_clip_rects(page_dict)

    render_clip = render_clip_fn or render_pdf_clip_to_bgr
    hit_rects = []

    for clip_rect in image_clip_rects or []:
        try:
            clip_img = render_clip(page, clip_rect, scan_scale)
        except Exception as exc:
            print(f"[OCR WARN] 裁剪图片区域失败: {type(exc).__name__}: {exc}")
            continue

        if clip_img is None or getattr(clip_img, "size", 0) == 0:
            continue

        scan_img = preprocess_fn(clip_img) if preprocess_fn else clip_img

        try:
            ocr_results = recognize_fn(scan_img)
        except Exception as exc:
            print(f"[OCR WARN] 图片区域 OCR 失败: {type(exc).__name__}: {exc}")
            continue

        for box, text in iter_ocr_lines(ocr_results):
            if not text:
                continue
            for pattern in compiled_patterns:
                for match in pattern.finditer(text):
                    local_rect = calculate_rect_fn(box, text, match.span(), scan_img)
                    if local_rect is None:
                        continue
                    page_rect = clip_to_page_rect_fn(local_rect, clip_rect)
                    if page_rect is not None:
                        hit_rects.append(page_rect)

    return hit_rects
