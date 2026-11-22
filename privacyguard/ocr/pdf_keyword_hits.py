"""Locate each full literal hit from its own PDF characters."""

import math

import fitz

from privacyguard.utils.literal_keywords import iter_keyword_matches


def collect_pdf_keyword_hits(page, patterns):
    if not patterns:
        return
    flags = fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES
    for block in page.get_text("rawdict", flags=flags)["blocks"]:
        for line in block.get("lines", ()):
            chars = [char for span in line["spans"] for char in span["chars"]]
            if any(len(char["c"]) != 1 for char in chars):
                continue
            text = "".join(char["c"] for char in chars)
            for start, end, term in iter_keyword_matches(text, patterns):
                boxes = [fitz.Rect(char["bbox"]) for char in chars[start:end] if not char["c"].isspace()]
                if not boxes or any(box.is_empty or not all(math.isfinite(n) for n in box) for box in boxes):
                    continue
                # Characters may sit in different font spans, including next to
                # a synthetic space. Wide gaps on a line can separate columns.
                dx, dy = line["dir"]
                mids = [(box.x0 + box.x1) / 2 * dx + (box.y0 + box.y1) / 2 * dy for box in boxes]
                widths = [abs(dx) * box.width + abs(dy) * box.height for box in boxes]
                heights = [abs(dy) * box.width + abs(dx) * box.height for box in boxes]
                if any(b < a or b - a > (wa + wb) / 2 + max(3, min(ha, hb) * .9)
                       for a, b, wa, wb, ha, hb in zip(mids, mids[1:], widths, widths[1:], heights, heights[1:])):
                    continue
                area = fitz.Rect()
                for box in boxes:
                    area |= box
                area = area * page.rotation_matrix
                if page.rect.contains(area):
                    yield area, term
