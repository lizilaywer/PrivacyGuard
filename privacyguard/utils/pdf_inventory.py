"""Bounded, local PDF risk inventory. Counts never contain document text.

This is a conservative feature inventory, not a certificate that arbitrary PDF
objects contain no sensitive data. Pixel export is the object-isolation option.
"""
import re

from .export_transaction import ExportValidationError

LABELS = {
    "metadata": "文档属性", "xml": "XML 元数据", "attachments": "附件",
    "links": "链接", "annotations": "批注", "forms": "表单/签名域",
    "actions": "脚本或自动动作", "layers": "可选图层", "structure": "结构/替代文本",
    "objects": "多媒体/嵌入对象", "invisible": "不可见文字", "signatures": "数字签名",
}


def inventory_pdf(doc):
    counts = dict.fromkeys(LABELS, 0)
    if doc.xref_length() > 50000:
        raise ExportValidationError("PDF 对象过多，无法完成隐藏内容清点，请分册后重试。")
    counts["metadata"] = int(doc.xref_get_key(-1, "Info")[0] != "null")
    counts["xml"] = int(bool(doc.get_xml_metadata()))
    counts["attachments"] = doc.embfile_count()
    counts["signatures"] = int(doc.get_sigflags() > 0)
    for page in doc:
        counts["links"] += len(page.get_links())
        counts["annotations"] += sum(1 for _ in page.annots())
        counts["forms"] += sum(1 for _ in page.widgets())
        counts["invisible"] += sum(
            1 for span in page.get_texttrace()
            if span.get("type") == 3 or span.get("opacity", 1) == 0)
    object_bytes = 0
    for xref in range(1, doc.xref_length()):
        obj = doc.xref_object(xref)
        object_bytes += len(obj)
        if object_bytes > 32 * 1024 * 1024:
            raise ExportValidationError("PDF 对象信息超过复查上限，请分册后重试。")
        for key, pattern in (
            ("actions", r"/(?:JavaScript|JS|OpenAction|AA|Launch|SubmitForm|ImportData)\b"),
            ("layers", r"/(?:OCG|OCMD|OCProperties)\b"),
            ("structure", r"/(?:StructTreeRoot|ActualText|Alt)\b"),
            ("objects", r"/(?:RichMedia|Movie|Sound|3D|Collection|AF|XFA)\b"),
        ):
            counts[key] += int(bool(re.search(pattern, obj)))
    return counts


def inventory_summary(counts):
    return "\n".join(f"{LABELS[key]}：{count}" for key, count in counts.items() if count) or "未发现清单内的附加部件。"
