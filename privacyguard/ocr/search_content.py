"""Bounded mixed-page search OCR and document/model-bound session cache."""
import hashlib
from functools import lru_cache
from pathlib import Path

import fitz
import cv2
import numpy as np

from .mixed_pdf import collect_embedded_image_clip_rects
from privacyguard.utils.exceptions import OCRInspectionError


@lru_cache(maxsize=12)
def _model_hash(path, size, modified):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model_signature():
    from .model_paths import local_model_params
    from importlib.metadata import version
    values = [version("rapidocr"), version("onnxruntime"), "search-v3:scale2:raw-bgr"]
    for path in local_model_params().values():
        info = Path(path).stat()
        values.append(_model_hash(path, info.st_size, info.st_mtime_ns))
    return hashlib.sha256("|".join(values).encode()).hexdigest()


def bind_document_cache(cache, pdf_bytes):
    fingerprint = hashlib.sha256(pdf_bytes).hexdigest()
    if cache.get("_document") not in (None, fingerprint):
        cache.clear()
    cache["_document"] = fingerprint


def bind_model_cache(cache):
    signature = model_signature()
    if cache.get("_model") not in (None, signature):
        for key in list(cache):
            if isinstance(key, int):
                del cache[key]
    cache["_model"] = signature


def cache_result(cache, page_index, record):
    def size(value):
        return len(value.get("text", ""))*2 + len(value.get("spans", []))*96 if isinstance(value, dict) else len(str(value))*2
    # Estimated text/coordinate budget, not a whole-process memory guarantee.
    if size(record) > 8*1024*1024:
        return
    cache[page_index] = record
    while sum(size(value) for key, value in cache.items() if isinstance(key, int)) > 8*1024*1024:
        oldest = next(key for key in cache if isinstance(key, int))
        del cache[oldest]


def ocr_search_regions(page, engine, mixed=False, cancelled=lambda: False):
    if mixed:
        clips = [fitz.Rect(*bounds) for bounds in collect_embedded_image_clip_rects(page.get_text("dict"))]
        clips = [(clip * page.rotation_matrix).normalize() if page.rotation else clip for clip in clips]
    else:
        clips = [page.rect]
    if len(clips) > 100:
        raise OCRInspectionError("图片块过多，搜索未完成。")
    parts, spans, offset, total_pixels = [], [], 0, 0
    for clip in clips:
        if cancelled():
            raise InterruptedError()
        clip &= page.rect
        total_pixels += int(clip.width*2+1)*int(clip.height*2+1)
        if total_pixels > 24000000:
            raise OCRInspectionError("搜索图片像素超出上限，请拆分页面。")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False, annots=False)
        array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        image = cv2.cvtColor(array[:, :, :3], cv2.COLOR_RGB2BGR)
        results = engine.recognize(image) or []
        for result in sorted(results, key=lambda r: (min(p[1] for p in r.box), min(p[0] for p in r.box))):
            if result.confidence < .5 or not result.text:
                continue
            xs, ys = [p[0] for p in result.box], [p[1] for p in result.box]
            # Pixmap integer origin includes rounding at the clip boundary.
            rect = ((min(xs)+pix.x)/2, (min(ys)+pix.y)/2,
                    (max(xs)-min(xs))/2, (max(ys)-min(ys))/2)
            parts.append(result.text)
            spans.append((offset, offset+len(result.text), rect))
            offset += len(result.text)+1
    return "\n".join(parts), spans
