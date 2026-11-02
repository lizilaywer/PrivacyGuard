# -*- coding: utf-8 -*-
"""cp87: 脱敏报告纯逻辑模块（D1 铁律：纯函数不依赖 GUI）。

- classify_hit_rule: 命中文本事后反查所属规则名（正则规则 → 自定义关键词 → 兜底）
- build_redact_report: 由 page_data 生成人类可读的脱敏报告文本
"""
import re


def classify_hit_rule(matched_text, rule_name_pairs, custom_keywords=None):
    """反查命中文本所属规则名。

    Args:
        matched_text: 命中的原文字符串
        rule_name_pairs: [(规则名, 正则pattern)] 列表（可为 None/空）
        custom_keywords: 自定义关键词字符串列表（可为 None）

    Returns:
        规则名；正则不中再比对关键词（相等或包含）；均不中返回 "智能识别"。
    """
    text = (matched_text or "").strip()
    if not text:
        return "智能识别"
    for name, pattern in (rule_name_pairs or []):
        if not pattern:
            continue
        try:
            if re.search(pattern, text):
                return name
        except re.error:
            continue
    for kw in (custom_keywords or []):
        kw = (kw or "").strip()
        if kw and (kw == text or kw in text or text in kw):
            return "自定义关键词"
    return "智能识别"


def _hit_rule_label(item):
    """从命中项 dict 提取规则名；无 rule 字段视为手动遮罩（向后兼容）。"""
    if isinstance(item, dict):
        rule = item.get("rule")
        if rule:
            return str(rule)
    return None  # 由调用方按 ocr/manual 归类


def summarize_page_data(page_data):
    """按规则名汇总 page_data。

    Returns:
        (total, rule_pages)：total 总命中数；
        rule_pages = {规则名: {页码(0基): 数量}}，有序按首次出现。
    """
    total = 0
    rule_pages = {}
    for pn in sorted((page_data or {}).keys()):
        entry = page_data.get(pn) or {}
        if not isinstance(entry, dict):
            continue
        for key, fallback in (("ocr", "智能识别"), ("manual", "手动遮罩")):
            for item in entry.get(key, []) or []:
                label = _hit_rule_label(item) or fallback
                total += 1
                rule_pages.setdefault(label, {})
                rule_pages[label][pn] = rule_pages[label].get(pn, 0) + 1
    return total, rule_pages


def _format_page_list(pages, limit=12):
    """页码列表（0基 → 1基）截断展示。"""
    shown = [str(p + 1) for p in sorted(pages)[:limit]]
    suffix = "…" if len(pages) > limit else ""
    return "、".join(shown) + suffix


def build_redact_report(file_name, page_count, page_data, export_path,
                        encrypted=False, now_str=""):
    """生成脱敏报告文本（纯函数）。

    Args:
        file_name: 源文件名
        page_count: 总页数
        page_data: {页码: {"ocr": [...], "manual": [...]}}
        export_path: 导出文件路径
        encrypted: 是否加密导出
        now_str: 时间字符串（由调用方传入，保持纯函数）
    """
    total, rule_pages = summarize_page_data(page_data)
    lines = [
        "PrivacyGuard 脱敏报告",
        "─" * 26,
        f"源文件：{file_name}（{page_count} 页）",
        f"导出时间：{now_str}",
        f"导出文件：{export_path}",
        f"加密：{'已启用' if encrypted else '未启用'}",
        "",
        f"共遮罩 {total} 处：" if total else "本次导出未包含任何遮罩。",
    ]
    for label, pages in rule_pages.items():
        count = sum(pages.values())
        lines.append(f"  {label} {count} 处（第 {_format_page_list(pages)} 页）")

    if total:
        lines.append("")
        lines.append("逐页明细：")
        page_details = {}
        for label, pages in rule_pages.items():
            for pn, cnt in pages.items():
                page_details.setdefault(pn, []).append(f"{label}×{cnt}")
        for pn in sorted(page_details.keys()):
            lines.append(f"  第 {pn + 1} 页：" + "，".join(page_details[pn]))
    return "\n".join(lines)
