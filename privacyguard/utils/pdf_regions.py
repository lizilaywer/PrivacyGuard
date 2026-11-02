"""Vector region copying without retaining content hidden behind a clip path."""

import fitz
from PyQt6.QtCore import QRectF


def copy_visible_pdf_region(target_page, target_rect, source_doc, page_number, clip):
    """Remove excluded content in an isolated copy before grafting its resources.

    show_pdf_page(clip=...) alone hides, but does not remove, original streams.
    Compact and reopen before grafting so even unused image/text streams are gone.
    """
    with fitz.open() as isolated:
        isolated.insert_pdf(source_doc, from_page=page_number, to_page=page_number,
                            links=False, annots=False, widgets=False)
        page = isolated[0]
        bounds = page.rect * page.derotation_matrix
        keep = fitz.Rect(clip) & bounds
        if keep.is_empty:
            raise ValueError("Empty PDF region")
        excluded = (
            fitz.Rect(bounds.x0, bounds.y0, bounds.x1, keep.y0),
            fitz.Rect(bounds.x0, keep.y1, bounds.x1, bounds.y1),
            fitz.Rect(bounds.x0, keep.y0, keep.x0, keep.y1),
            fitz.Rect(keep.x1, keep.y0, bounds.x1, keep.y1),
        )
        for rect in excluded:
            if not rect.is_empty:
                page.add_redact_annot(rect, fill=False)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS,
                              graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED)
        with fitz.open(stream=isolated.tobytes(garbage=2, clean=True, deflate=True),
                       filetype="pdf") as clean:
            target_page.show_pdf_page(target_rect, clean, 0, clip=keep)


def crop_page_hits(entry, y_min, y_max, page_width, page_height):
    """Map existing display-coordinate masks onto the retained top/bottom strips."""
    y0 = max(0.0, min(float(y_min), page_height))
    y1 = max(0.0, min(float(y_max), page_height))
    strips = ((QRectF(0, 0, page_width, y0), 0.0),
              (QRectF(0, y1, page_width, page_height - y1), -(y1 - y0)))
    result = {"ocr": [], "manual": []}
    for kind in result:
        for item in (entry or {}).get(kind, []):
            rect = item.get("rect") if isinstance(item, dict) else item
            if rect is None:
                continue
            for strip, shift in strips:
                clipped = rect.intersected(strip)
                if clipped.isEmpty():
                    continue
                clipped.translate(0, shift)
                result[kind].append(dict(item, rect=clipped) if isinstance(item, dict) else clipped)
    return result
