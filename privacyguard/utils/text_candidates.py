"""Traceable optional width/digit-separator search; never automatic redaction."""
import unicodedata


def normalized_map(text):
    expanded, offsets = [], []
    for index, char in enumerate(text):
        for value in unicodedata.normalize("NFKC", char).casefold():
            expanded.append(value)
            offsets.append(index)
    output, mapping = [], []
    index = 0
    while index < len(expanded):
        char = expanded[index]
        end = index+1
        if char.isspace() or char in "-‐‑–—":
            while end < len(expanded) and (expanded[end].isspace() or expanded[end] in "-‐‑–—"):
                end += 1
            if index > 0 and end < len(expanded) and expanded[index-1].isdigit() and expanded[end].isdigit():
                index = end
                continue
        output.extend(expanded[index:end])
        mapping.extend(offsets[index:end])
        index = end
    return "".join(output), mapping


def collect_search_hits(text, keyword, normalize=False):
    from .helpers_pdf import collect_text_hits, build_search_snippet
    if not normalize:
        return collect_text_hits(text, keyword)
    source, offsets = normalized_map(text)
    target, _ = normalized_map(keyword)
    if not target:
        return []
    hits = []
    cursor = 0
    while len(hits) < 200:
        found = source.find(target, cursor)
        if found < 0:
            break
        start, end = offsets[found], offsets[found+len(target)-1]+1
        before, value, after = build_search_snippet(text, start, end-start)
        hits.append((start, before, value, after))
        cursor = found + len(target)
    return hits
