# -*- coding: utf-8 -*-
"""PrivacyGuard Word docx 段落/单元格操作函数。

v37.8.11 重构 Phase 1: 从 main.py 提取，原位于 helpers.py。
本模块承载与 python-docx 段落 run 级区间替换、纯文本抽取、页眉页脚遍历
相关的纯函数，均不依赖 MainWindow 状态。

包含:
- run 级区间替换 (apply_range_to_runs)
- 纯文本抽取 (paragraph_plain_text / cell_plain_text)
- 页眉页脚遍历 (iter_word_header_footer_paragraphs / iter_word_header_footer_cells)
- 匹配应用 (replace_matches_in_paragraph / replace_matches_in_cell)
"""


__all__ = [
    "apply_range_to_runs",
    "paragraph_plain_text",
    "cell_plain_text",
    "iter_word_header_footer_paragraphs",
    "iter_word_header_footer_cells",
    "replace_matches_in_paragraph",
    "replace_matches_in_cell",
]


def apply_range_to_runs(para, start, end, replacement):
    """在段落 run 列表上应用一次区间替换。"""
    if start >= end:
        return
    if not para.runs:
        return

    run_ranges = []
    cursor = 0
    for idx, run in enumerate(para.runs):
        text = run.text or ''
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
        start_run_idx = run_ranges[-1][0]
        start_offset = len(para.runs[start_run_idx].text or '')

    end_run_idx = None
    end_offset = 0
    for idx, run_start, run_end in run_ranges:
        if end <= run_end:
            end_run_idx = idx
            end_offset = end - run_start
            break
    if end_run_idx is None:
        end_run_idx = run_ranges[-1][0]
        end_offset = len(para.runs[end_run_idx].text or '')

    start_run = para.runs[start_run_idx]
    end_run = para.runs[end_run_idx]
    start_text = start_run.text or ''
    end_text = end_run.text or ''

    prefix = start_text[:start_offset]
    suffix = end_text[end_offset:]
    start_run.text = prefix + replacement + suffix

    if end_run_idx > start_run_idx:
        for idx in range(start_run_idx + 1, end_run_idx + 1):
            para.runs[idx].text = ''


def paragraph_plain_text(para):
    """段落纯文本：与 run 级替换保持同源（仅顶层 <w:r>，与 replace_matches_in_paragraph 一致）。

    注意：python-docx 的 para.text 会包含超链接可见文字，但 para.runs 不含超链接内 run。
    脱敏匹配的 offset 必须与替换所用文本源一致，否则含超链接段落会错位或漏脱。
    """
    try:
        return ''.join(run.text for run in para.runs)
    except AttributeError:
        return ''


def cell_plain_text(cell):
    """单元格纯文本：按 python-docx 的换行拼接，与 run 级替换的 para_offset 累加保持一致。"""
    try:
        return '\n'.join(paragraph_plain_text(p) for p in cell.paragraphs)
    except AttributeError:
        return ''


def iter_word_header_footer_paragraphs(doc):
    """W2: 遍历页眉/页脚中的段落，产出 (key, para)。

    仅处理非继承（非 link-to-previous）的页眉页脚，避免跨 section 重复处理。
    key 方案在打开/保存/批量三处共用本生成器，保证一致。
    """
    for section_idx, hf_type, hf in _iter_unique_header_footers(doc):
        for p_idx, para in enumerate(hf.paragraphs):
            yield f"{hf_type}_{section_idx}_paragraph_{p_idx}", para


def iter_word_header_footer_cells(doc):
    """W2: 遍历页眉/页脚表格单元格，产出 (key, cell)。"""
    for section_idx, hf_type, hf in _iter_unique_header_footers(doc):
        for t_idx, table in enumerate(hf.tables):
            seen_cells = set()
            for r_idx, row in enumerate(table.rows):
                for c_idx, cell in enumerate(row.cells):
                    if cell._tc in seen_cells:
                        continue
                    seen_cells.add(cell._tc)
                    yield f"{hf_type}_{section_idx}_table_{t_idx}_cell_{r_idx}_{c_idx}", cell


def _iter_unique_header_footers(doc):
    """Include first/even-page variants without creating missing header parts."""
    try:
        sections = list(doc.sections)
    except (AttributeError, ValueError):
        return
    seen_parts = set()
    for section_idx, section in enumerate(sections):
        for hf_type in ("header", "footer", "first_page_header", "first_page_footer",
                        "even_page_header", "even_page_footer"):
            hf = getattr(section, hf_type, None)
            if hf is None:
                continue
            if getattr(hf, "is_linked_to_previous", False):
                continue
            part = hf.part.partname
            if part in seen_parts:
                continue
            seen_parts.add(part)
            yield section_idx, hf_type, hf


def replace_matches_in_paragraph(para, matches, text_offset=0, fallback_replacement_text="[已脱敏]"):
    """按匹配区间替换段落文本，避免同词误替换和跨 run 漏替换。"""
    if not matches or not para.runs:
        return

    paragraph_text = ''.join(run.text for run in para.runs)
    if not paragraph_text:
        return

    text_len = len(paragraph_text)
    ranges = []
    seen = set()

    for match in matches:
        start = match.get('start')
        end = match.get('end')
        if not isinstance(start, int) or not isinstance(end, int):
            continue

        local_start = start - text_offset
        local_end = end - text_offset
        if local_start < 0 or local_end > text_len or local_start >= local_end:
            continue

        replacement = match.get('replacement', fallback_replacement_text)
        if replacement is None:
            replacement = fallback_replacement_text
        if not isinstance(replacement, str):
            replacement = str(replacement)

        key = (local_start, local_end, replacement)
        if key in seen:
            continue
        seen.add(key)
        ranges.append({
            'start': local_start,
            'end': local_end,
            'replacement': replacement
        })

    if not ranges:
        return

    ranges.sort(key=lambda item: (item['start'], -(item['end'] - item['start'])))
    filtered = []
    last_end = -1
    for item in ranges:
        if item['start'] < last_end:
            continue
        filtered.append(item)
        last_end = item['end']

    for item in reversed(filtered):
        apply_range_to_runs(para, item['start'], item['end'], item['replacement'])


def replace_matches_in_cell(cell, matches, fallback_replacement_text="[已脱敏]"):
    """在单元格的所有段落上应用匹配（按 cell 文本换行拼接的偏移映射）。

    统一 _save_word、批量替换、页眉页脚三处的单元格替换逻辑，避免重复与漂移。
    """
    if not matches:
        return
    para_offset = 0
    paragraphs = list(cell.paragraphs)
    for idx, para in enumerate(paragraphs):
        original_para_len = len(''.join(run.text for run in para.runs))
        replace_matches_in_paragraph(
            para,
            matches,
            text_offset=para_offset,
            fallback_replacement_text=fallback_replacement_text
        )
        para_offset += original_para_len
        if idx < len(paragraphs) - 1:
            # python-docx 的 cell 文本使用换行拼接段落
            para_offset += 1
