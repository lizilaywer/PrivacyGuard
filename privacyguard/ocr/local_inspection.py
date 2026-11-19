"""Optional bounded small-text/QR inspection, returning manual candidates only.

Uses the already-loaded Small OCR model and OpenCV. No new model, network,
persisted OCR text or automatic replacement; visible line boxes are candidates.
"""
import math
import time

import cv2
import fitz
import numpy as np

from privacyguard.utils.exceptions import OCRInspectionError


def inspect_page(page, engine, cancelled=lambda: False, max_seconds=20):
    started = time.monotonic()
    scale = min(3.0, math.sqrt(8000000 / max(1, page.rect.width * page.rect.height)))
    if scale < 1:
        raise OCRInspectionError("页面过大，请先截取需要复查的区域。")
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, annots=False)
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    image = np.ascontiguousarray(image[:, :, :3][:, :, ::-1])
    candidates = []
    seen = []

    def add(points, kind, confidence=None):
        bounds = np.asarray(points, dtype=float).reshape(-1, 2)
        if not np.isfinite(bounds).all():
            return
        x0, y0 = bounds.min(axis=0) / scale
        x1, y1 = bounds.max(axis=0) / scale
        rect = fitz.Rect(x0, y0, x1, y1) & page.rect
        if rect.is_empty or rect.width < 1 or rect.height < 1:
            return
        if any((rect & other).get_area() / max(1, min(rect.get_area(), other.get_area())) > .85 for other in seen):
            return
        seen.append(rect)
        candidates.append({"geometry": [rect.x0, rect.y0, rect.width, rect.height], "kind": kind, "confidence": confidence})

    # Two overlapping horizontal tiles keep a small page's letters large
    # without a second whole-document scan. Never shrink below original scale.
    height = image.shape[0]
    cuts = [(0, height)] if height <= 1800 else [(0, height//2+100), (height//2-100, height)]
    for top, bottom in cuts:
        if cancelled():
            return candidates, "已取消，保留已找到的候选"
        if time.monotonic() - started > max_seconds:
            return candidates, "达到时间上限，当前页补查未完成"
        for result in engine.recognize(image[top:bottom]):
            if result.confidence < .5:
                continue
            points = [[x, y+top] for x, y in result.box]
            add(points, "文字行候选", float(result.confidence))
            if len(candidates) >= 150:
                return candidates, "达到 150 项上限，当前页补查未完成"
    if not cancelled() and time.monotonic() - started <= max_seconds:
        # Detection only: never decode, store or visit QR payloads.
        detector = cv2.QRCodeDetector()
        found, points = detector.detectMulti(image)
        if found and points is not None:
            for box in points:
                add(box, "二维码图案候选")
    return candidates, "本页补查完成；候选仍需人工选择，不能保证识别所有敏感内容"
