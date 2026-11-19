"""Conservative, optional character alignment; coordinates remain input-image pixels.

No text normalization is performed: every non-space source character must match
exactly, otherwise the entire line falls back to the established geometry path.
"""

import math

from .base import CharInfo


def _bounds(box):
    if len(box) != 4 or any(len(point) != 2 for point in box):
        raise ValueError("Invalid quadrilateral")
    points = [(float(x), float(y)) for x, y in box]
    if not all(math.isfinite(v) for point in points for v in point):
        raise ValueError("Non-finite coordinates")
    x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
    y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("Empty quadrilateral")
    return x0, y0, x1, y1


def align_characters(text, line_box, word_results):
    """Decode RapidOCR triples only when the complete line aligns safely.

    Missing spaces are explicitly mapped to source offsets. Grouped tokens,
    changed punctuation, invalid boxes and displaced rows reject the whole line.
    No word_results/shape error is allowed to discard its normal OCR text.
    """
    try:
        if not isinstance(text, str) or not word_results:
            return []
        indices = [i for i, char in enumerate(text) if not char.isspace()]
        tokens = [entry for entry in word_results if not entry[0].isspace()]
        if len(tokens) != len(indices):
            return []
        lx0, ly0, lx1, ly1 = _bounds(line_box)
        tolerance = max(2.0, min(lx1 - lx0, ly1 - ly0) * 0.25)
        result = []
        for index, entry in zip(indices, tokens):
            char, score, box = entry
            confidence = float(score)
            if char != text[index] or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                return []
            x0, y0, x1, y1 = _bounds(box)
            if (x0 < lx0 - tolerance or y0 < ly0 - tolerance
                    or x1 > lx1 + tolerance or y1 > ly1 + tolerance):
                return []
            result.append(CharInfo(char, [[float(x), float(y)] for x, y in box], confidence, index))
        return result
    except (ValueError, TypeError, IndexError, AttributeError, OverflowError):
        return []


def character_sub_rect(line_box, text, chars, span, scan_scale):
    """Return a padded (x,y,w,h) in PDF points, or None to request fallback.

    For now only near-horizontal left-to-right lines are eligible. Rotated or
    slanted lines retain the established path rather than guessing orientation.
    Full line height is retained. Horizontal padding also accounts for CTC
    alignment uncertainty (20% of the narrowest selected character width).
    """
    try:
        start, end = span
        if not (0 <= start < end <= len(text)) or not math.isfinite(scan_scale) or scan_scale <= 0:
            return None
        if not chars or len(chars) != sum(not c.isspace() for c in text):
            return None
        lx0, ly0, lx1, ly1 = _bounds(line_box)
        if lx1 - lx0 < ly1 - ly0:
            return None
        if abs(float(line_box[1][1]) - float(line_box[0][1])) > max(2, (ly1 - ly0) * 0.12):
            return None
        selected = []
        previous_center = None
        expected = [i for i, c in enumerate(text) if not c.isspace()]
        for char, index in zip(chars, expected):
            if (char.start != index or char.char != text[index]
                    or not math.isfinite(char.confidence) or not 0.75 <= char.confidence <= 1):
                return None
            x0, y0, x1, y1 = _bounds(char.box)
            if not (lx0 - 2 <= x0 < x1 <= lx1 + 2 and ly0 - 2 <= y0 < y1 <= ly1 + 2):
                return None
            center = (x0 + x1) / 2
            if previous_center is not None and center <= previous_center:
                return None
            previous_center = center
            if start <= index < end:
                selected.append((x0, y0, x1, y1))
        if not selected:
            return None
        x0, x1 = min(b[0] for b in selected), max(b[2] for b in selected)
        if x1 - x0 < 1:
            return None
        pad = max(scan_scale, min(b[2] - b[0] for b in selected) * 0.2) / scan_scale
        return (x0 / scan_scale - pad, min(ly0, min(b[1] for b in selected)) / scan_scale - 0.5,
                max(2.0, (x1 - x0) / scan_scale) + 2.0 * pad,
                (max(ly1, max(b[3] for b in selected)) - min(ly0, min(b[1] for b in selected))) / scan_scale + 1.0)
    except (ValueError, TypeError, IndexError, AttributeError, OverflowError):
        return None
