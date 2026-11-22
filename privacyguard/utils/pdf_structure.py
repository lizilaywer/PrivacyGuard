"""Inspect current PDF references without enumerating unused xref slots."""

import fitz

from .export_transaction import ExportValidationError


PDF_ENGINE_ERRORS = (RuntimeError, fitz.mupdf.FzErrorBase)
_REFERENCE_ERROR = (
    "PDF 的结构引用了一个无法读取的对象，无法确认脱敏结果完整。\n"
    "导出已停止。请从原始来源重新获取一份 PDF，再打开并检查遮罩。"
)


def reachable_pdf_xrefs(document):
    """Walk indirect references from the current trailer using MuPDF's parser.

    The xref length is a number range, not a list of allocated objects. A gap
    outside this graph is harmless. An unreadable referenced object is not.
    Stream dictionaries are inspected without decoding their payloads here.
    """
    try:
        return _walk_references(document)
    except ExportValidationError as error:
        message = str(error)
    except (ValueError, *PDF_ENGINE_ERRORS):
        message = _REFERENCE_ERROR
    # Discard the native traceback before raising: it can retain a PDF handle
    # and stop Windows from cleaning up a rejected temporary export.
    raise ExportValidationError(message)


def _walk_references(document):
    mupdf = fitz.mupdf
    pdf = mupdf.PdfDocument(document.this)
    xref_length = document.xref_length()
    pending = [mupdf.pdf_trailer(pdf)]
    seen = set()
    inspected = 0
    while pending:
        value = pending.pop()
        inspected += 1
        if mupdf.pdf_is_indirect(value):
            number = mupdf.pdf_to_num(value)
            if number in seen:
                continue
            if not 0 < number < xref_length:
                raise ExportValidationError(_REFERENCE_ERROR)
            loaded = mupdf.pdf_load_object(pdf, number)
            if not mupdf.pdf_is_indirect(loaded) and mupdf.pdf_is_null(loaded):
                raise ExportValidationError(_REFERENCE_ERROR)
            seen.add(number)
            if len(seen) > 50000:
                raise ExportValidationError("PDF 对象过多，超过导出检查上限。请分册后重试。")
            pending.append(loaded)
            continue
        if mupdf.pdf_is_dict(value):
            length, get_child = mupdf.pdf_dict_len(value), mupdf.pdf_dict_get_val
        elif mupdf.pdf_is_array(value):
            length, get_child = mupdf.pdf_array_len(value), mupdf.pdf_array_get
        else:
            continue
        if inspected + len(pending) + length > 500000:
            raise ExportValidationError("PDF 结构过于复杂，超过导出检查上限。请分册后重试。")
        pending.extend(get_child(value, index) for index in range(length))
    return sorted(seen)


def pdf_export_error_message(error):
    """Report PDF engine failures without exposing raw document diagnostics."""
    if isinstance(error, ExportValidationError):
        return str(error)
    if "cannot find object in xref" in str(error):
        return _REFERENCE_ERROR
    if isinstance(error, fitz.mupdf.FzErrorBase):
        return "PDF 解析或写出失败，导出已停止。请检查文档能否完整打开后重试。"
    return str(error)
