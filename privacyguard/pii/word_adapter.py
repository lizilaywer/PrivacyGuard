"""PII 边界适配 — Word 文档路径。

三函数 (D-11 + D-06 + D-07):
- collect_pii_word_hits: 复用 PIIEngine.detect 段级识别 (Phase 1 PIIHit 字段锁 D-05)
- locate_pii_hits_in_paragraph: 内容→位置 (char_offset_in_paragraph_text) 换算 (D-08 / D-09)
- apply_pii_replacements_to_docx: 按段合并 run + replace PII 命中 (D-06 / D-07)

约束: 保持 PII 引擎无 IO 原则——本模块不 import python-docx。
调用方持有 Document 句柄传入; Document 仅作为类型注解 (PEP 484 forward ref)。

D-13 / OPS-03 懒加载纪律: 本模块不应在 `import privacyguard` 时拉起。
新调用入口必须在 privacyguard.pii.__init__._LAZY_IMPORTS 注册。
"""
from typing import Dict, List, Literal, Tuple


# "Document" is the python-docx Document type (forward reference; PEP 484).
# We do NOT import it to keep the PII engine free of IO / external deps (D-11).


# Phase 1 PIIHit / TextUnit dataclass — 字段顺序锁 D-05, 本模块不扩展字段.
def _import_pii_hits():
    """延迟导入 PIIHit / TextUnit — 让 PII 子包在不调用 word_adapter 函数时不拉起 hits.py。"""
    from privacyguard.pii.hits import PIIHit, TextUnit  # noqa: F401
    return PIIHit, TextUnit


def collect_pii_word_hits(paragraph_text, engine) -> list:
    """对单段 Word 文本执行 PII 识别 (D-11)。

    复用 PIIEngine.detect, 构造 TextUnit(page_index=0, text=..., source='text')。
    空 / 全空白文本返回 []（与 PIIEngine.detect 行为一致）。

    Args:
        paragraph_text: 单段 / 单 cell 文本
        engine: PIIEngine 实例（调用方持有）

    Returns:
        PIIHit 列表 (D-05 字段锁; 不增字段不重载语义)
    """
    _, TextUnit = _import_pii_hits()
    if not paragraph_text or not str(paragraph_text).strip():
        return []
    unit = TextUnit(page_index=0, text=paragraph_text, source="text")
    return engine.detect(unit)


def locate_pii_hits_in_paragraph(hits, paragraph_text: str) -> list:
    """对 PIIHit 列表在段内做精确子串定位 (D-08), 同文本重复逐个展开 (D-09).

    顺序: 按 (len(hit.normalized or ""), hit.normalized or "") 排序 — 短 needle 优先,
    避免长 needle 吞噬短 needle; 每个 hit 用 paragraph_text.find(needle, search_from)
    顺序扫描, 搜不到的 break (当前 hit 不出现 → 不发射).

    注: PIIHit 字段锁 D-05 — 没有 .text 字段, 定位用 .normalized (字面匹配段内文本).
    Args:
        hits: PIIHit 列表 (D-05 字段锁; 仅消费 hit.normalized)
        paragraph_text: 段内视图 (与 python-docx Paragraph.text 视图一致)

    Returns:
        [(PIIHit, char_offset), ...] — 同文本重复逐个展开为多个独立元组 (D-09)
    """
    if not hits or not paragraph_text:
        return []

    locations = []
    sorted_hits = sorted(
        hits,
        key=lambda h: (len(getattr(h, "normalized", "") or ""), getattr(h, "normalized", "") or ""),
    )
    for hit in sorted_hits:
        needle = getattr(hit, "normalized", "") or ""
        if not needle:
            continue
        search_from = 0
        while True:
            idx = paragraph_text.find(needle, search_from)
            if idx < 0:
                break
            locations.append((hit, idx))
            search_from = idx + len(needle)
    return locations


def _walk_paragraphs(doc):
    """遍历 doc 的所有段落（含嵌套 tables）并 yield (key, paragraph) 元组。

    key 格式:
        paragraph_N                  第 N 段 (top-level)
        table_X_row_Y_cell_Z_p_W     第 X 个 table 第 Y 行第 Z 列第 W 个 cell 内段落

    Args:
        doc: python-docx Document (调用方持有; D-11 不 import python-docx)

    Yields:
        (key, paragraph) tuples
    """
    # 直接遍历 paragraphs (避免 import docx namespace)
    paragraphs = getattr(doc, "paragraphs", []) or []
    for idx, para in enumerate(paragraphs):
        yield f"paragraph_{idx}", para

    # 嵌套表格
    tables = getattr(doc, "tables", []) or []
    for tbl_idx, table in enumerate(tables):
        rows = getattr(table, "rows", []) or []
        for row_idx, row in enumerate(rows):
            cells = getattr(row, "cells", []) or []
            for cell_idx, cell in enumerate(cells):
                cell_paragraphs = getattr(cell, "paragraphs", []) or []
                for p_idx, para in enumerate(cell_paragraphs):
                    yield f"table_{tbl_idx}_row_{row_idx}_cell_{cell_idx}_p_{p_idx}", para


def _replace_matches_in_paragraph_local(para, matches, fallback_replacement_text="[已脱敏]"):
    """按段合并 run + 在 paragraph_text 视图上做区间替换 (D-07)。

    参考 main.py:965 replace_matches_in_paragraph 既有实现 (跨 run 处理);
    本地 inline 是为了在 PII 子包内不依赖 main.py 跨层 import (v37.7.6 收敛原则)。

    Args:
        para: python-docx Paragraph
        matches: [{"start": int, "end": int, "replacement": str}, ...]
        fallback_replacement_text: 默认掩码文本
    """
    if not matches:
        return

    runs = list(getattr(para, "runs", []) or [])
    if not runs:
        return

    # 计算 paragraph_text 视图与每 run 的范围
    paragraph_text = "".join(getattr(run, "text", "") or "" for run in runs)
    text_len = len(paragraph_text)

    # 校验 + 去重 + 排序
    ranges = []
    seen = set()
    for match in matches:
        start = match.get("start")
        end = match.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        local_start = start
        local_end = end
        if local_start < 0 or local_end > text_len or local_start >= local_end:
            continue
        replacement = match.get("replacement")
        if replacement is None:
            replacement = fallback_replacement_text
        if not isinstance(replacement, str):
            replacement = str(replacement)
        key = (local_start, local_end, replacement)
        if key in seen:
            continue
        seen.add(key)
        ranges.append({
            "start": local_start,
            "end": local_end,
            "replacement": replacement,
        })

    if not ranges:
        return

    ranges.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))
    filtered = []
    last_end = -1
    for item in ranges:
        if item["start"] >= last_end:
            filtered.append(item)
            last_end = item["end"]

    if not filtered:
        return

    # 按倒序处理, 早索引不变
    for item in reversed(filtered):
        start = item["start"]
        end = item["end"]
        replacement = item["replacement"]
        _apply_range_to_runs_local(para, start, end, replacement)


def _apply_range_to_runs_local(para, start, end, replacement):
    """在段落 run 列表上应用一次区间替换 (D-07 段级样式保留).

    保留 paragraph.style; 不保留 run 级格式（粗体/斜体）— D-07 安全优先.
    """
    if start >= end:
        return

    runs = list(getattr(para, "runs", []) or [])
    if not runs:
        return

    run_ranges = []
    cursor = 0
    for idx, run in enumerate(runs):
        text = getattr(run, "text", "") or ""
        run_start = cursor
        run_end = cursor + len(text)
        run_ranges.append((idx, run_start, run_end))
        cursor = run_end

    total_len = cursor
    if start < 0 or end > total_len:
        return

    start_run_idx = None
    start_offset = 0
    for idx, run_start, run_end in run_ranges:
        if start < run_end:
            start_run_idx = idx
            start_offset = start - run_start
            break
    if start_run_idx is None:
        return

    end_run_idx = None
    end_offset = 0
    for idx, run_start, run_end in run_ranges:
        if end <= run_end:
            end_run_idx = idx
            end_offset = end - run_start
            break
    if end_run_idx is None:
        end_run_idx = run_ranges[-1][0]
        end_offset = len(getattr(runs[end_run_idx], "text", "") or "")

    start_run = runs[start_run_idx]
    end_run = runs[end_run_idx]
    start_text = getattr(start_run, "text", "") or ""
    end_text = getattr(end_run, "text", "") or ""

    prefix = start_text[:start_offset]
    suffix = end_text[end_offset:]
    try:
        start_run.text = prefix + replacement + suffix
    except Exception:
        # AttributeError 等 — 文档无写入权限, 静默忽略 (D-06 不抛错)
        return

    if end_run_idx > start_run_idx:
        for idx in range(start_run_idx + 1, end_run_idx + 1):
            try:
                runs[idx].text = ""
            except Exception:
                return


def apply_pii_replacements_to_docx(
    doc,
    hit_locations: Dict[str, List[Tuple]],
    mode: Literal["partial", "blackout"] = "partial",
) -> None:
    """对 docx 文档按段合并 run + replace PII 命中 (D-06 / D-07)。

    不 import python-docx: 调用方持有 Document 句柄传入 (D-11)。
    partial 模式: mask_for_entity(hit.entity_type, hit.normalized) → "110101********1234" 等
    blackout 模式: 写 "[已脱敏]" 占位字符串

    Args:
        doc: python-docx Document (Document 仅作为类型注解, 运行时通过 duck-typing 访问 attributes)
        hit_locations: key → [(PIIHit, char_offset), ...] 映射. key 由 _walk_paragraphs 产生.
        mode: "partial" (mask_for_entity) 或 "blackout" (固定 "[已脱敏]")
    """
    if not hit_locations:
        return

    # 延迟导入 mask_for_entity, 避免 word_adapter 顶层拉起 mask 子模块
    from privacyguard.pii.mask import mask_for_entity

    for key, para in _walk_paragraphs(doc):
        hits = hit_locations.get(key) or []
        if not hits:
            continue

        matches = []
        for entry in hits:
            if isinstance(entry, tuple) and len(entry) == 2:
                hit, offset = entry
            else:
                continue
            if offset is None:
                continue

            text = getattr(hit, "normalized", "") or ""
            if not text:
                continue

            end = offset + len(text)
            if offset < 0 or end <= offset:
                continue

            if mode == "partial":
                replacement = mask_for_entity(
                    getattr(hit, "entity_type", ""), text,
                )
            else:
                replacement = "[已脱敏]"

            matches.append({"start": offset, "end": end, "replacement": replacement})

        if matches:
            _replace_matches_in_paragraph_local(para, matches, fallback_replacement_text="[已脱敏]")


__all__ = [
    "collect_pii_word_hits",
    "locate_pii_hits_in_paragraph",
    "apply_pii_replacements_to_docx",
]
