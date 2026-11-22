"""Reopen checks for supported PDF output properties and marked text regions.

This is not a complete PDF sanitizer or an OCR guarantee. Attachments, metadata,
forms and images require their separately specified policies and test coverage.
"""

import math

import fitz

from .export_transaction import ExportValidationError
from .pdf_structure import reachable_pdf_xrefs


def _hit_rect(item):
    rect = item.get("rect") if isinstance(item, dict) else item
    if rect is None:
        raise ExportValidationError("遮罩坐标无效，未保存导出文件。")
    values = (rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
    if not all(math.isfinite(v) for v in values) or values[2] <= values[0] or values[3] <= values[1]:
        raise ExportValidationError("遮罩坐标无效，未保存导出文件。")
    return fitz.Rect(*values)


def _chars(page):
    flags = fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES
    for block in page.get_text("rawdict", flags=flags).get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    if char.get("c", "").strip():
                        yield char["c"], fitz.Rect(char["bbox"])


def verify_pdf_export(path, expected_document, page_data, save_kwargs, *, text_warning_pages=None):
    """Validate saved geometry, TOC, encryption and text in marked rectangles.

    Text explicitly requested as replacement is permitted. This does not claim
    to identify unknown PII outside the marked areas or hidden PDF components.
    No original or extracted text is ever included in error messages.
    """
    password = save_kwargs.get("owner_pw") or save_kwargs.get("user_pw") or ""
    try:
        with fitz.open(path) as saved:
            encryption = save_kwargs.get("encryption", fitz.PDF_ENCRYPT_NONE)
            encrypted = encryption not in (fitz.PDF_ENCRYPT_NONE, 0)
            if bool(saved.needs_pass) != bool(save_kwargs.get("user_pw")):
                raise ExportValidationError("导出打开密码状态验证未通过，未保存文件。")
            if password and saved.authenticate(password) <= 0:
                raise ExportValidationError("导出密码验证未通过，未保存文件。")
            # Encrypted metadata is unavailable before authentication.
            metadata = saved.metadata or {}
            if bool(metadata.get("encryption")) != encrypted:
                raise ExportValidationError("导出加密状态验证未通过，未保存文件。")
            # Re-authenticate even the empty user password: owner authentication
            # temporarily grants all permissions in PyMuPDF's runtime view.
            if encrypted and saved.authenticate(save_kwargs.get("user_pw", "")) <= 0:
                raise ExportValidationError("导出打开密码验证未通过，未保存文件。")
            reachable_pdf_xrefs(saved)
            if "permissions" in save_kwargs:
                known = (fitz.PDF_PERM_PRINT | fitz.PDF_PERM_MODIFY | fitz.PDF_PERM_COPY
                         | fitz.PDF_PERM_ANNOTATE | fitz.PDF_PERM_FORM | fitz.PDF_PERM_ASSEMBLE
                         | fitz.PDF_PERM_PRINT_HQ)
                if (saved.permissions & known) != (save_kwargs["permissions"] & known):
                    raise ExportValidationError("导出编辑权限验证未通过，未保存文件。")
            if len(saved) != len(expected_document) or saved.get_toc() != expected_document.get_toc():
                raise ExportValidationError("导出页数或书签验证未通过，未保存文件。")
            if any(not isinstance(index, int) or not 0 <= index < len(saved)
                   for index, entry in page_data.items()
                   if entry.get("ocr") or entry.get("manual")):
                raise ExportValidationError("遮罩页码与文档不一致，未保存文件。")
            checked = 0
            for index, expected in enumerate(expected_document):
                page = saved[index]
                if page.rotation != expected.rotation or any(
                    abs(a - b) > 0.01 for a, b in zip(
                        tuple(page.rect) + tuple(page.cropbox) + tuple(page.mediabox),
                        tuple(expected.rect) + tuple(expected.cropbox) + tuple(expected.mediabox))
                ):
                    raise ExportValidationError(f"第 {index + 1} 页结构验证未通过，未保存文件。")
                entry = page_data.get(index, {})
                hits = entry.get("ocr", []) + entry.get("manual", [])
                if not hits:
                    continue
                areas = []
                for hit in hits:
                    area = _hit_rect(hit)
                    if page.rotation:
                        area = (area * page.derotation_matrix).normalize()
                    replacement = hit.get("replace_text", "") if isinstance(hit, dict) else ""
                    areas.append((area, replacement))
                characters = list(_chars(page))
                page_has_warning = False
                for area, _replacement in areas:
                    allowed = "".join(str(text) for other, text in areas if other.intersects(area))
                    allowed = "".join(c for c in allowed if not c.isspace())
                    observed = "".join(c for c, bounds in characters if bounds.intersects(area))
                    # Order matters: an anagram of a replacement is not the
                    # requested replacement. Overlapping masks can expose only
                    # a portion of adjacent replacement runs, hence subsequence.
                    remaining = iter(allowed)
                    if any(not any(candidate == char for candidate in remaining) for char in observed):
                        if text_warning_pages is None:
                            raise ExportValidationError(
                                f"第 {index + 1} 页遮罩区域仍有未预期文字，导出已中止。")
                        page_has_warning = True
                    checked += 1
                if page_has_warning:
                    text_warning_pages.append(index + 1)
            return checked
    except ExportValidationError:
        raise
    except Exception as exc:
        raise ExportValidationError("导出文件无法完成复查，未保存结果；请重试或检查文档。") from exc


def verify_docx_export(path, expected_document):
    """Verify CRC, readable relationships and exact expected package part bytes."""
    import hashlib
    from zipfile import ZipFile
    from docx import Document

    try:
        with ZipFile(path) as package:
            if package.testzip() is not None:
                raise ExportValidationError("Word 导出完整性检查未通过，未保存文件。")
            expected_parts = expected_document.part.package.parts
            for part in expected_parts:
                saved_bytes = package.read(str(part.partname).lstrip('/'))
                if hashlib.sha256(saved_bytes).digest() != hashlib.sha256(part.blob).digest():
                    raise ExportValidationError("Word 导出内容检查未通过，未保存文件。")
                if part.rels:
                    rel_bytes = package.read(str(part.partname.rels_uri).lstrip('/'))
                    if rel_bytes != part.rels.xml:
                        raise ExportValidationError("Word 导出关系目标检查未通过，未保存文件。")
            if package.read("_rels/.rels") != expected_document.part.package.rels.xml:
                raise ExportValidationError("Word 主文档关系检查未通过，未保存文件。")
        restored = Document(path)
        if len(restored.part.package.parts) != len(expected_parts):
            raise ExportValidationError("Word 导出部件检查未通过，未保存文件。")
        return len(expected_parts)
    except ExportValidationError:
        raise
    except Exception as exc:
        raise ExportValidationError("Word 文件无法完成复查，未保存结果；请重试或检查文档。") from exc
