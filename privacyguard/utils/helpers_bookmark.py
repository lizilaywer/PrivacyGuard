# -*- coding: utf-8 -*-
"""PrivacyGuard PDF 书签（TOC）脱敏与数据转换纯函数。

cp_bookmark: 为新增"书签栏"功能提供无 UI 依赖的核心逻辑：
- 关键词规则应用到书签标题（替换/删除子串）
- 书签栏搜索匹配
- fitz TOC ↔ 面板数据模型的转换

设计原则：本模块全部为纯函数，不依赖 fitz / Qt / MainWindow 状态，
便于单元测试与跨场景复用。fitz 的 TOC 格式为
[[level, title, page], ...]（simple 模式），level>=1，page 从 1 起。
"""
from privacyguard.utils.helpers_word_rules import normalize_custom_keyword_rules
from privacyguard.utils.literal_keywords import compile_keyword_patterns, iter_keyword_matches

__all__ = [
    "redact_toc_titles",
    "find_bookmark_matches",
    "toc_to_tree_nodes",
    "tree_nodes_to_toc",
]


def redact_toc_titles(toc, rules):
    """把关键词脱敏规则应用到书签标题。

    规则复用高级设置的 custom_keyword_rules（[{"enabled","find","replace"}, ...]）：
    - find 命中标题中的子串 → 用 replace 替换该子串
    - replace 为空字符串 → 删除该子串（即"纯遮罩/删除"语义）
    - 未命中 → 标题原样保留

    Args:
        toc: fitz simple 格式 [[level, title, page], ...]；可为 None/空
        rules: custom_keyword_rules 列表；可为 None/空

    Returns:
        新的 toc 列表（不修改入参），结构与层级保持不变，仅标题文本被改写。
        入参为空时返回 []。
    """
    if not toc:
        return []
    normalized = normalize_custom_keyword_rules(rules)
    enabled = [r for r in normalized if r.get("enabled", True) and r.get("find")]
    if not enabled:
        # 无可应用规则 → 原样返回副本
        return [list(entry) for entry in toc]

    new_toc = []
    for entry in toc:
        if not entry or len(entry) < 3:
            # 异常条目原样保留（防御）
            new_toc.append(list(entry) if isinstance(entry, list) else entry)
            continue
        level, title, page = entry[0], entry[1], entry[2]
        new_title = _apply_rules_to_title(title if isinstance(title, str) else str(title), enabled)
        new_toc.append([level, new_title, page])
    return new_toc


def _apply_rules_to_title(title, enabled_rules):
    """Apply whole keywords to the original title in one pass."""
    replacements = {rule["find"]: rule.get("replace") for rule in enabled_rules if rule.get("find")}
    parts = []
    cursor = 0
    for start, end, term in iter_keyword_matches(title, compile_keyword_patterns(replacements)):
        value = replacements[term]
        parts.extend((title[cursor:start], value if isinstance(value, str) else ""))
        cursor = end
    parts.append(title[cursor:])
    return "".join(parts)


def find_bookmark_matches(toc, query):
    """书签栏搜索：大小写不敏感子串匹配。

    Args:
        toc: [[level, title, page], ...]
        query: 搜索词（可为空）

    Returns:
        命中项列表 [(index, title), ...]，index 为在 toc 中的位置。
        query 为空或 toc 为空时返回 []。
    """
    if not toc or not query:
        return []
    q = str(query).strip().lower()
    if not q:
        return []
    matches = []
    for idx, entry in enumerate(toc):
        if not entry or len(entry) < 3:
            continue
        title = entry[1]
        if not isinstance(title, str):
            title = str(title)
        if q in title.lower():
            matches.append((idx, title))
    return matches


def toc_to_tree_nodes(toc):
    """fitz TOC → 嵌套树节点列表（供 QTreeWidget 构建）。

    fitz TOC 用 level 数字表示层级（1=根，2=子，3=孙...），
    本函数把它转成嵌套结构，便于递归构建 QTreeWidgetItem。

    Returns:
        [{"title": str, "page": int, "level": int, "children": [...]}, ...]
        入参为空返回 []。level 异常（如非单调递增）时按相对关系尽量构建。
    """
    if not toc:
        return []
    root_nodes = []
    # stack 存当前各级父节点：stack[i] 是 level=i+1 的最近一个节点
    stack = []
    for entry in toc:
        if not entry or len(entry) < 3:
            continue
        level, title, page = entry[0], entry[1], entry[2]
        if not isinstance(level, int) or level < 1:
            level = 1
        node = {
            "title": title if isinstance(title, str) else str(title),
            "page": page if isinstance(page, int) else int(page) if _is_int(page) else 1,
            "level": level,
            "children": [],
        }
        # 弹栈到当前节点的父层级（level-1）
        while len(stack) >= level:
            if stack:
                stack.pop()
            else:
                break
        if stack:
            stack[-1]["children"].append(node)
        else:
            root_nodes.append(node)
        stack.append(node)
    return root_nodes


def _is_int(v):
    try:
        int(v)
        return True
    except (TypeError, ValueError):
        return False


def tree_nodes_to_toc(nodes):
    """嵌套树节点 → fitz TOC（collect_toc 用，导出时回写）。

    与 toc_to_tree_nodes 互逆。深度优先遍历，保留层级与顺序。

    Returns:
        [[level, title, page], ...]
    """
    toc = []

    def _walk(node_list, depth):
        for node in node_list:
            toc.append([depth, node.get("title", ""), node.get("page", 1)])
            children = node.get("children", [])
            if children:
                _walk(children, depth + 1)

    _walk(nodes or [], 1)
    return toc
