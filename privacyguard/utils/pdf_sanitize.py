"""Explicit PDF export policies; operate only on the redacted export copy."""
import math

import fitz

from .export_transaction import ExportValidationError
from .pdf_inventory import inventory_pdf

POLICIES = ("preserve", "sanitize", "raster")


def prepare_pdf_output(doc, policy="preserve", dpi=180):
    if policy not in POLICIES:
        raise ExportValidationError("未知的 PDF 导出方式。")
    if policy == "preserve":
        return doc
    if policy == "raster":
        result = fitz.open()
        try:
            for page in doc:
                scale = dpi / 72
                if not 72 <= dpi <= 240 or math.ceil(page.rect.width * scale) * math.ceil(page.rect.height * scale) > 24000000:
                    raise ExportValidationError("页面超出纯图导出像素上限，请先拆分或裁剪页面。")
                # Widgets/annotations are excluded: existing masks were applied
                # to content already. Do not reintroduce unscanned form values.
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, annots=False)
                output = result.new_page(width=page.rect.width, height=page.rect.height)
                output.insert_image(output.rect, stream=pix.tobytes("png"))
            return result
        except BaseException:
            result.close()
            raise
    counts = inventory_pdf(doc)
    if any(counts[k] for k in ("forms", "layers", "structure", "objects", "invisible", "signatures")):
        raise ExportValidationError("存在表单、图层、隐藏文字、结构或签名等复杂内容，无法可靠执行保留文字净化。请选择纯图导出，或保留版式后自行复核附加内容。")
    toc = doc.get_toc(simple=True)
    doc.scrub(attached_files=True, clean_pages=False, embedded_files=True,
              hidden_text=False, javascript=True, metadata=True, redactions=False,
              remove_links=True, reset_fields=False, reset_responses=False,
              thumbnails=False, xml_metadata=True)
    doc.xref_set_key(-1, "Info", "null")
    for xref in range(1, doc.xref_length()):
        if not doc.xref_object(xref).startswith("<<"):
            continue
        for key in ("A", "AA", "OpenAction", "JS", "Thumb", "PieceInfo"):
            if doc.xref_get_key(xref, key)[0] != "null":
                doc.xref_set_key(xref, key, "null")
    catalog = doc.pdf_catalog()
    for key in ("JavaScript", "EmbeddedFiles"):
        if doc.xref_get_key(catalog, "Names/" + key)[0] != "null":
            doc.xref_set_key(catalog, "Names/" + key, "null")
    if toc:
        doc.set_toc(toc)  # rebuild internal page destinations, never external actions
    return doc


def verify_pdf_policy(doc, policy):
    if policy == "preserve":
        return
    counts = inventory_pdf(doc)
    if any(counts.values()):
        raise ExportValidationError("隐藏内容处理后仍发现附加部件，导出已中止。")
    if policy == "raster" and any(page.get_text().strip() for page in doc):
        raise ExportValidationError("纯图输出仍包含文字层，导出已中止。")
