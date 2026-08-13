"""PII 真脱敏 apply 阶段（SAFE-01 / MASK-01 / SAFE-03）。

- apply_pii_redactions: 沿用 main.py:12354-12385 已生产验证的 PyMuPDF 真删除 API。
- write_partial_masks: Phase 2 MASK-01 — partial mask 写入（D-01 + D-02 + D-03 + D-21）。
- clear_pdf_metadata: Phase 2 SAFE-03 — PDF 元数据 5 字段清除（D-14 + D-15 + D-16）。

禁止使用 `page.draw_rect`（假脱敏，黑框覆盖但底层文本仍可还原）。

主要常量：
- fitz.PDF_REDACT_IMAGE_PIXELS = 2（**不是**默认 0；否则图像像素不被销毁）
- garbage=4 + deflate=True + clean=True 三个 save flag 联合清扫元数据 / 未引用对象。
"""
from typing import Callable, Dict, Iterable, List, Literal, Optional, Tuple, Union

import fitz

from privacyguard.pii.hits import PIIHit


Rect = Tuple[float, float, float, float]


# 02-04 (CR-01 fix): mixed item types accepted in a single write_partial_masks call.
#   - PIIHit dataclass: routed via global `mode` arg (02-01 backward-compat path)
#   - fitz.Rect: routed via global `mode` arg
#   - (x, y, w, h, mode) tuple: per-item mode (OCR / manual blackout + PII blackout)
#   - (PIIHit, mode) 2-tuple: per-item mode + PIIHit routing for mask_strategy
PartialMaskItem = Union[
    PIIHit,
    "fitz.Rect",
    Tuple[float, float, float, float, str],
    Tuple[PIIHit, str],
]


# PyMuPDF font name 映射表（page.get_text("dict") 返回的 font 名 → insert_text 支持的 fontname）
# D-02 锁定：文本层路径从 page.get_text("dict") 取最近 span 的 font + size 同步插入。
_FONT_NAME_MAP: Dict[str, str] = {
    "Helvetica": "helv",
    "Helvetica-Oblique": "heit",
    "Helvetica-Bold": "hebo",
    "Helvetica-BoldOblique": "hebi",
    "Times-Roman": "tiro",
    "Times-Bold": "tibo",
    "Courier": "cour",
    "Courier-Bold": "cobo",
}


def collect_pii_rects(page_data: Dict[int, dict]) -> Dict[int, list]:
    """从 MainWindow.page_data 提取每页 PII 命中 → fitz.Rect 列表。

    输入: page_data = {page_idx: {"ocr": [...], "manual": [...], "pii": [PIIHit, ...]}}
    输出: {page_idx: [fitz.Rect, ...]}
    """
    out: Dict[int, list] = {}
    for page_idx, data in page_data.items():
        rects = []
        for hit in data.get('pii', []):
            r = hit.page_rect  # (x, y, w, h)
            rects.append(fitz.Rect(r[0], r[1], r[0] + r[2], r[1] + r[3]))
        if rects:
            out[page_idx] = rects
    return out


def apply_pii_redactions(
    pdf_in: str,
    pdf_out: str,
    rects_per_page: Dict[int, Iterable[fitz.Rect]],
    fill_color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    """PyMuPDF 真删除：add_redact_annot + apply_redactions(IMAGE_PIXELS) + garbage=4。

    Pitfall 9：必须显式传 `images=fitz.PDF_REDACT_IMAGE_PIXELS`（=2），
    默认值 0（PDF_REDACT_IMAGE_NONE）不会销毁图像像素层。

    Pitfall 10：保存时同时 `garbage=4 + deflate=True + clean=True` 三件套，
    否则残留对象 / 元数据可能导致敏感信息泄漏。
    """
    doc = fitz.open(pdf_in)
    try:
        for i in range(len(doc)):
            page = doc[i]
            for r in rects_per_page.get(i, []):
                annot = page.add_redact_annot(r)
                annot.set_colors(stroke=fill_color, fill=fill_color)
                annot.update()
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
            for annot in page.annots() or []:
                page.delete_annot(annot)
        doc.save(pdf_out, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()


# ----------------------------------------------------------------------
# Phase 2 (02-01-tracer) — write_partial_masks + clear_pdf_metadata
# ----------------------------------------------------------------------

def write_partial_masks(
    doc: "fitz.Document",
    page_idx: int,
    items: List[PartialMaskItem],
    mode: Literal["partial", "blackout"] = "partial",
) -> None:
    """PII 命中 partial mask 写入（D-01 + D-02 + D-03 + D-21 + 02-04 CR-01 mixed dispatch）。

    02-04 CR-01: 接受 4 种混合 item 形态，单次调用即可处理 OCR / manual / PII 全部来源:
      - PIIHit dataclass: rect 从 page_rect 取，mask_text 从 mask_strategy 取，mode 走全局参数
      - fitz.Rect: rect 直接取，mask_text 为 None（黑框不写文字），mode 走全局参数
      - (x, y, w, h, mode) 5-tuple: rect 由坐标构造，mask_text 为 None（黑框），mode 按 item[4]
      - (PIIHit, mode) 2-tuple: rect 从 hit.page_rect 取，mask_text 从 hit.mask_strategy 取，mode 按 item[1]

    mode="partial":
        1. add_redact_annot（黑底色块，所有 item 不论 mode）
        2. apply_redactions(IMAGE_PIXELS)
        3. 对 mode=='partial' 且有 mask_text 的 item: insert_text 在色块上写 mask_strategy
            - 字体：优先 page.get_text("dict") 取最近 span 的 font + size
            - 字号：OCR / 占位 rect 路径用 rect.height - 4 估算（floor 6）
            - 颜色：白字 (1.0, 1.0, 1.0)
            - D-03: rect 宽度按 mask_strategy 字符数重算 + 居中

    mode="blackout":
        仅 add_redact_annot + apply_redactions(IMAGE_PIXELS)（沿用 Phase 1 行为）

    D-22 不变量：apply_redactions 每页仅调用一次（无论 item 数量或 mode 组合）。
    """
    if not items:
        return
    page = doc[page_idx]
    fill_color = (0.0, 0.0, 0.0)

    # ----- 阶段 1: 把所有 item 归一化为 (rect, mask_text_or_None, item_mode) -----
    normalized: List[Tuple[fitz.Rect, Optional[str], str]] = []
    for item in items:
        # 2-tuple (PIIHit, mode): per-item mode + mask_text from hit
        if (
            isinstance(item, tuple)
            and len(item) == 2
            and hasattr(item[0], "page_rect")
            and hasattr(item[0], "mask_strategy")
            and isinstance(item[1], str)
        ):
            hit = item[0]
            item_mode = item[1]
            r = hit.page_rect
            rect = fitz.Rect(r[0], r[1], r[0] + r[2], r[1] + r[3])
            mask_text = hit.mask_strategy or None
            normalized.append((rect, mask_text, item_mode))
            continue
        # 5-tuple (x, y, w, h, mode): per-item mode, no mask_text
        if (
            isinstance(item, tuple)
            and len(item) == 5
            and isinstance(item[4], str)
            and all(isinstance(v, (int, float)) for v in item[:4])
        ):
            x, y, w, h, item_mode = item
            rect = fitz.Rect(float(x), float(y), float(x) + float(w), float(y) + float(h))
            normalized.append((rect, None, item_mode))
            continue
        # fitz.Rect: global mode
        if isinstance(item, fitz.Rect):
            normalized.append((item, None, mode))
            continue
        # PIIHit dataclass: global mode + mask_text from hit
        if hasattr(item, "page_rect") and hasattr(item, "mask_strategy"):
            r = item.page_rect
            rect = fitz.Rect(r[0], r[1], r[0] + r[2], r[1] + r[3])
            mask_text = item.mask_strategy or None
            normalized.append((rect, mask_text, mode))
            continue
        # unknown type: skip defensively
        continue

    if not normalized:
        return

    # ----- 阶段 2: 一次性画所有黑底色块 + 销毁底层文本 + 清理 annot -----
    for rect, _mask_text, _item_mode in normalized:
        annot = page.add_redact_annot(rect)
        annot.set_colors(stroke=fill_color, fill=fill_color)
        annot.update()
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
    for annot in page.annots() or []:
        page.delete_annot(annot)

    # ----- 阶段 3: 对 mode=='partial' 且有 mask_text 的 item 写文字 -----
    for rect, mask_text, item_mode in normalized:
        if item_mode != "partial" or not mask_text:
            continue
        font_name, font_size = _resolve_font_for_rect_unified(page, rect, mask_text)
        resized_rect = _resize_rect_for_mask(rect, mask_text, font_size)
        text_width = font_size * len(mask_text) * 0.6
        x_center = resized_rect.x0 + (resized_rect.width - text_width) / 2
        y_center = resized_rect.y0 + (resized_rect.height + font_size) / 2 - 2
        page.insert_text(
            (x_center, y_center),
            mask_text,
            fontsize=font_size,
            fontname=font_name,
            color=(1.0, 1.0, 1.0),
        )


def _resolve_font_for_rect_unified(
    page: "fitz.Page",
    rect: fitz.Rect,
    mask_text: str,
) -> Tuple[str, float]:
    """02-04: rect + mask_text 直传版字体解析（替代 hit-耦合的 _resolve_font_for_rect）。

    优先 page.get_text("dict") 取最近 span 的 font + size（WR-02 fix #1: 使用 _FONT_NAME_MAP）。
    文本层路径：从 spans 中找含 mask_text（或 hit.normalized 子串）的 span，返回其 font + size。
    OCR / 占位 rect 路径：fallback 到 ("helv", max(rect.height - 4, 6))（WR-02 fix #2）。

    Args:
        page: PyMuPDF Page 对象
        rect: PII 命中区域
        mask_text: 即将写入的 mask_strategy 文本

    Returns:
        (font_name, font_size) — 可直接传 page.insert_text
    """
    fallback_size = max(float(rect.height) - 4.0, 6.0)
    try:
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    txt = span.get("text", "")
                    if txt and mask_text and (
                        mask_text in txt or txt in mask_text or txt == mask_text
                    ):
                        raw_font = span.get("font", "helv")
                        font_name = _FONT_NAME_MAP.get(raw_font, "helv")
                        raw_size = span.get("size", fallback_size)
                        try:
                            size = float(raw_size)
                        except (TypeError, ValueError):
                            size = fallback_size
                        return (font_name, max(size, 6.0))
    except Exception:
        return ("helv", 11.0)
    return ("helv", fallback_size)


def _resolve_font_for_rect(
    page: "fitz.Page",
    hit: PIIHit,
) -> Tuple[str, float]:
    """D-02: 优先 page.get_text("dict") 现场取最近 span 的 font + size。

    文本层路径（unit.source="text"）：从 page.get_text("dict") 的 spans 中
    找包含 hit.normalized 的 span，返回其 font + size。

    OCR / 占位 rect 路径（unit.source != "text" 或 span 未找到）：
    回退到默认 sans-serif ("helv") + 估算字号 max(rect.height - 4, 6)。

    Args:
        page: PyMuPDF Page 对象
        hit: PIIHit（提供 normalized + page_rect + source）

    Returns:
        (font_name, font_size) — 可直接传 page.insert_text
    """
    fallback_size = max(float(hit.page_rect[3]) - 4.0, 6.0)
    try:
        if hit.source and hit.source != 'text':
            # OCR / image_block / full_page_ocr 路径：直接估算字号
            return ("helv", fallback_size)
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    txt = span.get("text", "")
                    if txt and hit.normalized and hit.normalized in txt:
                        raw_font = span.get("font", "helv")
                        font_name = _FONT_NAME_MAP.get(raw_font, "helv")
                        raw_size = span.get("size", fallback_size)
                        try:
                            size = float(raw_size)
                        except (TypeError, ValueError):
                            size = fallback_size
                        # floor 6 防退化
                        return (font_name, max(size, 6.0))
    except Exception:
        # get_text 失败 → 紧急 fallback
        return ("helv", 11.0)
    # span 未找到（文字层路径但 OCR 命中）→ 估算字号
    return ("helv", fallback_size)


def _resize_rect_for_mask(
    rect: fitz.Rect,
    mask_text: str,
    fontsize: float,
) -> fitz.Rect:
    """D-03: 按 mask_text 字符数重算 rect 宽度，居中保持。

    avg_w = fontsize * 0.6；new_w = max(len(mask_text) * avg_w + 4, rect.width)
    居中：cx = (rect.x0 + rect.x1) / 2 → 新 rect x0 = cx - new_w/2
    """
    avg_w = float(fontsize) * 0.6
    new_w = max(len(mask_text) * avg_w + 4.0, float(rect.width))
    cx = (float(rect.x0) + float(rect.x1)) / 2.0
    return fitz.Rect(cx - new_w / 2.0, float(rect.y0), cx + new_w / 2.0, float(rect.y1))


def clear_pdf_metadata(doc: "fitz.Document") -> None:
    """Phase 2: SAFE-03 PDF 元数据清除（D-14 + D-15 + D-16）。

    仅清 5 字段（title / author / subject / producer / creator），其他保留：
    - CreationDate / ModDate 不动（D-14 锁定）
    - Keywords / XMP metadata 不动（D-14 锁定）
    - 5 字段全部置空字符串（D-15 锁定），不写 "Anonymous" / "Redacted" /
      "PyMuPDF" 等占位字符串

    调用位置：MainWindow.save_pdf 中 doc.save() 前调用一次（D-16 锁定）。
    """
    doc.set_metadata({
        "title": "",
        "author": "",
        "subject": "",
        "producer": "",
        "creator": "",
    })


__all__ = [
    'collect_pii_rects',
    'apply_pii_redactions',
    # Phase 2 (02-01-tracer)
    'write_partial_masks',
    'clear_pdf_metadata',
    # Phase 2 (02-04-gap-closure): mixed item dispatch
    'PartialMaskItem',
]
