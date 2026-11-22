"""Find text-layer account and invoice fields for manual PDF review."""

import math
import re

import fitz

from privacyguard.utils.text_candidates import normalized_map


_FIELD = re.compile(
    r"(?:(?P<account>银行账号|银行帐号|银行账户|开户账号|开户帐号|收款账号|收款帐号)"
    r"|(?P<invoice>发票号码|发票号)) *: *"
)
_NUMBER = re.compile(r"[0-9]+")
_SOURCE_NUMBER = re.compile(r"[0-9０-９ \u3000\u00a0\-‐‑–—]+")
_DIGIT_GROUPS = re.compile(r"[ \u3000\u00a0\-‐‑–—]+")
_FIELD_END = frozenset(" ,，。;；、)）]】")
_VISIBLE_TEXT = (1 << 3) | (1 << 4)  # filled or stroked
_MAX_PAGE_CHARS = 50_000
_MAX_CANDIDATES = 40


def _line_chunks(line):
    """Keep nearby characters together and separate distant table columns."""
    chunk = []
    previous = None
    for span in line["spans"]:
        if not span.get("alpha", 255) or not span.get("char_flags", 0) & _VISIBLE_TEXT:
            if chunk:
                yield chunk
            chunk, previous = [], None
            continue
        for char in span["chars"]:
            value = char["c"]
            box = fitz.Rect(char["bbox"])
            if len(value) != 1 or not all(math.isfinite(n) for n in box) or box.is_empty:
                if chunk:
                    yield chunk
                chunk, previous = [], None
                continue
            if not value.isspace():
                if previous is not None:
                    gap_limit = max(3, min(box.height, previous.height) * .9)
                    if box.x0 - previous.x1 > gap_limit or box.x0 < previous.x0:
                        yield chunk
                        chunk = []
                previous = box
            chunk.append((value, box))
    if chunk:
        yield chunk


def _fields(chunk):
    text = "".join(char for char, _ in chunk)
    normalized, offsets = normalized_map(text)
    for label in _FIELD.finditer(normalized):
        match = _NUMBER.match(normalized, label.end())
        if match is None:
            continue
        span_end = match.end()
        if span_end < len(normalized) and normalized[span_end] not in _FIELD_END:
            continue
        count = span_end - match.start()
        is_account = label.lastgroup == "account"
        if not (9 <= count <= 21 if is_account else count in (8, 20)):
            continue
        start, end = offsets[match.start()], offsets[span_end - 1] + 1
        original = text[start:end]
        if not _SOURCE_NUMBER.fullmatch(original):
            continue
        groups = _DIGIT_GROUPS.split(original)
        if len(groups) > 1 and (any(len(group) != 4 for group in groups[:-1]) or len(groups[-1]) > 4):
            continue
        area = fitz.Rect()
        for _, box in chunk[start:end]:
            area |= box
        kind = "银行账号候选" if is_account else "发票号码候选"
        reason = "同一行的银行账号标签" if is_account else "同一行的发票号码标签"
        yield area, kind, reason


def collect_financial_candidates(page, cancelled=lambda: False):
    """Return candidate geometry and fixed reason labels, plus a limit flag.

    A PDF text line must contain its own field label and value. Never join
    rows, infer a missing label, or return the recognized digits.
    """
    if cancelled():
        return [], False
    flags = fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES
    blocks = page.get_text("rawdict", flags=flags)["blocks"]
    candidates, seen = [], set()
    inspected = 0
    for block in blocks:
        for line in block.get("lines", ()):
            if cancelled():
                return candidates, False
            inspected += sum(len(span["chars"]) for span in line["spans"])
            if inspected > _MAX_PAGE_CHARS:
                return candidates, True
            if line["wmode"] or tuple(line["dir"]) != (1.0, 0.0):
                continue
            for chunk in _line_chunks(line):
                for rect, kind, reason in _fields(chunk):
                    rect = rect * page.rotation_matrix
                    if rect.is_empty or not page.rect.contains(rect):
                        continue
                    geometry = (rect.x0, rect.y0, rect.width, rect.height)
                    key = tuple(round(n, 3) for n in geometry)
                    if key in seen:
                        continue
                    if len(candidates) == _MAX_CANDIDATES:
                        return candidates, True
                    seen.add(key)
                    candidates.append({"geometry": list(geometry), "kind": kind, "reason": reason})
    return candidates, False
