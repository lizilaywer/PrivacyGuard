"""Full literal keywords shared by selection, settings, scan and bookmarks."""

import re


_HAN = re.compile(r"[\u3400-\u9fff]")
_SPACE = r"[^\S\r\n]"
KEYWORD_RULE = "自定义关键词"


def configured_keywords(legacy_text, rules):
    """Prefer explicit rows. The older string format stores one phrase per line."""
    if not isinstance(rules, list) or not rules:
        if not isinstance(legacy_text, str):
            return {}
        return dict.fromkeys(line.strip() for line in legacy_text.splitlines() if line.strip())
    result = {}
    for row in rules:
        if not isinstance(row, dict) or not row.get("enabled", True):
            continue
        find = row.get("find")
        if isinstance(find, str) and find.strip():
            replace = row.get("replace")
            result[find.strip()] = replace if isinstance(replace, str) else ""
    return result


def compile_keyword_patterns(terms):
    patterns = []
    for term in terms:
        if not term.strip():
            continue
        chars = re.findall(r"\S", term)
        if not chars:
            continue
        parts = []
        previous = None
        for match in re.finditer(r"\S", term):
            char = match.group()
            if previous is not None:
                if _HAN.fullmatch(previous.group()) or _HAN.fullmatch(char):
                    parts.append(_SPACE + "*")
                elif match.start() > previous.end():
                    parts.append(_SPACE + "+")
            parts.append(re.escape(char))
            previous = match
        if _HAN.search(term):
            if chars[0].isdecimal():
                parts.insert(0, r"(?<!\d)")
            if chars[-1].isdecimal():
                parts.append(r"(?!\d)")
        patterns.append((term, re.compile("".join(parts), re.IGNORECASE)))
    return patterns


def iter_keyword_matches(text, patterns):
    """Resolve overlapping literal rules against the original text once."""
    matches = [(m.start(), m.end(), term) for term, pattern in patterns for m in pattern.finditer(text)]
    end_of_previous = -1
    for start, end, term in sorted(matches, key=lambda value: (value[0], -value[1])):
        if start >= end_of_previous:
            yield start, end, term
            end_of_previous = end
