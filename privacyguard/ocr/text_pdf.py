"""文本型 PDF 搜索结果提取共享逻辑。"""

import re


def iter_unique_text_matches(page_text, patterns):
    """按页面文本提取唯一匹配字符串，避免重复 search_for。"""
    if not isinstance(page_text, str) or not page_text.strip():
        return

    seen = set()
    for pattern in patterns or []:
        if not pattern or pattern == "__SEAL_DETECTION__":
            continue
        try:
            iterator = re.finditer(pattern, page_text, re.IGNORECASE)
        except re.error:
            continue

        for match in iterator:
            found = match.group(0)
            if not found or found in seen:
                continue
            seen.add(found)
            yield found


def collect_text_pdf_hit_boxes(page, patterns, page_text=None):
    """返回文本型 PDF 的唯一命中框坐标列表。"""
    if page_text is None:
        page_text = page.get_text()

    hit_boxes = []
    text_search_cache = {}
    for found_str in iter_unique_text_matches(page_text, patterns):
        try:
            if found_str not in text_search_cache:
                text_search_cache[found_str] = page.search_for(found_str)
            hits = text_search_cache[found_str]
        except RuntimeError as exc:
            print(f"搜索文本错误: {exc}")
            continue

        if not hits:
            continue

        for hit in hits:
            hit_boxes.append((hit.x0, hit.y0, hit.width, hit.height))

    return hit_boxes
