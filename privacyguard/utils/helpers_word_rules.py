# -*- coding: utf-8 -*-
"""PrivacyGuard Word 替换规则与目标遮罩关键词处理函数。

v37.8.11 重构 Phase 1: 从 main.py 提取，原位于 helpers.py。
本模块承载与 Word 多字段替换规则规范化、匹配、应用、校验、预览分段，
以及全文遮罩关键词拆分/构造相关的纯函数，均不依赖 MainWindow 状态。

包含:
- 规则规范化 (normalize_word_replace_rules / normalize_custom_keyword_rules
  / migrate_custom_keywords_to_rules)
- 区间重叠辅助 (_range_overlaps)
- 规则匹配与应用 (build_word_rule_matches / apply_rule_matches_to_text
  / apply_word_rules_to_text / validate_word_replace_rules)
- 预览分段 (build_replaced_preview_segments / build_highlight_preview_segments)
- 多源合并 (merge_word_matches_with_priority)
- 全文遮罩关键词 (split_targeted_search_terms / build_targeted_keyword_rules
  / format_targeted_terms_preview)
"""

import re

__all__ = [
    "build_batch_summary_text",
    "normalize_word_replace_rules",
    "normalize_custom_keyword_rules",
    "migrate_custom_keywords_to_rules",
    "_range_overlaps",
    "build_word_rule_matches",
    "apply_rule_matches_to_text",
    "apply_word_rules_to_text",
    "validate_word_replace_rules",
    "build_replaced_preview_segments",
    "build_highlight_preview_segments",
    "merge_word_matches_with_priority",
    "split_targeted_search_terms",
    "build_targeted_keyword_rules",
    "format_targeted_terms_preview",
]


def normalize_word_replace_rules(rules, default_replacement_text="[已脱敏]"):
    """规范化多字段替换规则（会话级规则，不自动持久化）。"""
    normalized = []
    if not isinstance(rules, list):
        return normalized

    fallback_text = default_replacement_text if isinstance(default_replacement_text, str) and default_replacement_text else "[已脱敏]"
    mode_alias = {
        "exact": "exact",
        "regex": "regex",
        "精确": "exact",
        "正则": "regex"
    }

    for item in rules:
        if not isinstance(item, dict):
            continue
        enabled = bool(item.get("enabled", True))
        raw_mode = str(item.get("mode", "exact")).strip().lower()
        mode = mode_alias.get(raw_mode, "exact")

        find_text = str(item.get("find", "")).strip()
        if not find_text:
            continue

        replace_text = item.get("replace")
        if replace_text is None or str(replace_text) == "":
            replace_text = fallback_text
        else:
            replace_text = str(replace_text)

        normalized.append({
            "enabled": enabled,
            "mode": mode,
            "find": find_text,
            "replace": replace_text
        })

    return normalized


def normalize_custom_keyword_rules(rules):
    """v37.7.13 cp43: 规范化自定义关键词规则列表（持久化到 config.json）。

    每条结构: {"enabled": bool, "find": str, "replace": str}
    - find 为空字符串的条目被丢弃（无效规则）
    - replace 为空字符串表示纯遮罩不叠加文本（明确区分两种模式）
    - 不自动回退到统一替换文本，由调用方决定是否填充

    Args:
        rules: 待规范化的列表，元素应为 dict

    Returns:
        规范化后的 list[dict]
    """
    normalized = []
    if not isinstance(rules, list):
        return normalized

    for item in rules:
        if not isinstance(item, dict):
            continue
        enabled = bool(item.get("enabled", True))
        find_text = str(item.get("find", "")).strip()
        if not find_text:
            continue
        replace_text = str(item.get("replace", "")).strip()
        normalized.append({
            "enabled": enabled,
            "find": find_text,
            "replace": replace_text
        })

    return normalized


def migrate_custom_keywords_to_rules(old_str):
    """v37.7.13 cp43: 把旧的 \\n 分隔字符串迁移为规则列表。

    Args:
        old_str: 旧格式字符串（每行一个关键词，\\n 分隔）

    Returns:
        list[dict]: 规则列表，每条 replace 留空（纯遮罩，由用户后续填入替换文本）
    """
    if not isinstance(old_str, str) or not old_str.strip():
        return []
    return [
        {"enabled": True, "find": kw.strip(), "replace": ""}
        for kw in old_str.splitlines()
        if kw.strip()
    ]


def _range_overlaps(start, end, ranges):
    """判断区间是否与已有区间重叠。"""
    for s, e in ranges:
        if not (end <= s or start >= e):
            return True
    return False


def build_word_rule_matches(text, rules, default_replacement_text="[已脱敏]"):
    """根据规则查找文本匹配，执行策略：exact 优先于 regex，重叠先到先得。"""
    if not isinstance(text, str) or not text:
        return []

    normalized_rules = normalize_word_replace_rules(rules, default_replacement_text)
    selected = []
    occupied_ranges = []

    for target_mode in ("exact", "regex"):
        for rule_index, rule in enumerate(normalized_rules):
            if not rule.get("enabled", True) or rule.get("mode") != target_mode:
                continue

            pattern = re.escape(rule["find"]) if target_mode == "exact" else rule["find"]
            try:
                # W3: 与 WordWorker._find_matches 保持一致，忽略大小写以避免英文敏感词漏脱
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error:
                continue

            for matched in compiled.finditer(text):
                start = matched.start()
                end = matched.end()
                if start >= end:
                    continue
                if _range_overlaps(start, end, occupied_ranges):
                    continue

                selected.append({
                    "start": start,
                    "end": end,
                    "text": matched.group(0),
                    "replacement": rule["replace"],
                    "mode": target_mode,
                    "rule_index": rule_index,
                    "source": "rule"
                })
                occupied_ranges.append((start, end))

    selected.sort(key=lambda item: item["start"])
    return selected


def apply_rule_matches_to_text(text, matches):
    """将匹配区间应用到文本（倒序替换避免索引偏移）。"""
    if not isinstance(text, str) or not matches:
        return text

    output = text
    for match in sorted(matches, key=lambda item: item.get("start", 0), reverse=True):
        start = match.get("start")
        end = match.get("end")
        replacement = match.get("replacement", "")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end > len(output) or start >= end:
            continue
        if replacement is None:
            replacement = ""
        if not isinstance(replacement, str):
            replacement = str(replacement)
        output = output[:start] + replacement + output[end:]
    return output


def apply_word_rules_to_text(text, rules, default_replacement_text="[已脱敏]"):
    """直接按规则替换文本并返回替换结果。"""
    matches = build_word_rule_matches(text, rules, default_replacement_text)
    return apply_rule_matches_to_text(text, matches)


def validate_word_replace_rules(rules):
    """W5: 校验启用的 regex 规则合法性，返回错误描述列表。

    非法正则在 build_word_rule_matches 中会被静默跳过（导致漏脱），
    本函数供 UI/配置导入路径提前提示用户，避免“规则无效但无感知”。
    返回：[{'index': int, 'find': str, 'error': str}, ...]
    """
    errors = []
    if not isinstance(rules, list):
        return errors
    for idx, item in enumerate(rules):
        if not isinstance(item, dict):
            continue
        if not bool(item.get("enabled", True)):
            continue
        mode = str(item.get("mode", "exact")).strip().lower()
        if mode not in ("regex", "正则"):
            continue
        find_text = str(item.get("find", "")).strip()
        if not find_text:
            continue
        try:
            re.compile(find_text)
        except re.error as exc:
            errors.append({"index": idx, "find": find_text, "error": str(exc)})
    return errors


def build_replaced_preview_segments(text, matches, default_replacement_text="[已脱敏]"):
    """根据匹配区间生成替换后文本分段（用于右侧预览高亮）。"""
    if not isinstance(text, str):
        return [{"type": "text", "value": ""}]
    if not matches:
        return [{"type": "text", "value": text}]

    fallback_text = default_replacement_text if isinstance(default_replacement_text, str) and default_replacement_text else "[已脱敏]"
    segments = []
    cursor = 0

    for match in sorted(matches, key=lambda item: item.get("start", 0)):
        start = match.get("start")
        end = match.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < cursor or start < 0 or end > len(text) or start >= end:
            continue

        if start > cursor:
            segments.append({
                "type": "text",
                "value": text[cursor:start]
            })

        replacement = match.get("replacement", fallback_text)
        if replacement is None:
            replacement = fallback_text
        if not isinstance(replacement, str):
            replacement = str(replacement)

        segments.append({
            "type": "replacement",
            "value": replacement,
            "source": match.get("source", "rule"),
            "mode": match.get("mode", ""),
            "rule_name": match.get("rule_name", "")
        })
        cursor = end

    if cursor < len(text):
        segments.append({
            "type": "text",
            "value": text[cursor:]
        })

    if not segments:
        return [{"type": "text", "value": text}]
    return segments


def build_highlight_preview_segments(text, matches):
    """根据匹配区间生成原文高亮分段（用于左侧预览）。"""
    if not isinstance(text, str):
        return [{"type": "text", "value": ""}]
    if not matches:
        return [{"type": "text", "value": text}]

    segments = []
    cursor = 0
    for match in sorted(matches, key=lambda item: item.get("start", 0)):
        start = match.get("start")
        end = match.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < cursor or start < 0 or end > len(text) or start >= end:
            continue

        if start > cursor:
            segments.append({"type": "text", "value": text[cursor:start]})

        segments.append({
            "type": "highlight",
            "value": text[start:end],
            "source": match.get("source", "manual"),
            "mode": match.get("mode", ""),
            "rule_name": match.get("rule_name", ""),
            "start": start,
            "end": end,
        })
        cursor = end

    if cursor < len(text):
        segments.append({"type": "text", "value": text[cursor:]})

    if not segments:
        return [{"type": "text", "value": text}]
    return segments


def merge_word_matches_with_priority(text, rules, default_replacement_text,
                                     manual_matches=None, ocr_matches=None):
    """合并规则替换、手动脱敏、OCR 脱敏区间，优先级：规则 > 手动 > OCR。"""
    manual_matches = manual_matches or []
    ocr_matches = ocr_matches or []
    text_len = len(text) if isinstance(text, str) else 0
    fallback_text = default_replacement_text if isinstance(default_replacement_text, str) and default_replacement_text else "[已脱敏]"

    merged = []
    occupied_ranges = []

    def _append_candidates(candidates, source_name):
        for item in candidates:
            start = item.get("start")
            end = item.get("end")
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            if start < 0 or end > text_len or start >= end:
                continue
            if _range_overlaps(start, end, occupied_ranges):
                continue

            replacement = item.get("replacement", fallback_text)
            if replacement is None:
                replacement = fallback_text
            if not isinstance(replacement, str):
                replacement = str(replacement)

            merged.append({
                "start": start,
                "end": end,
                "text": item.get("text", text[start:end] if isinstance(text, str) else ""),
                "replacement": replacement,
                "source": source_name,
                "mode": item.get("mode", "global"),
                "rule_name": item.get("rule_name", "")
            })
            occupied_ranges.append((start, end))

    _append_candidates(build_word_rule_matches(text, rules, fallback_text), "rule")
    _append_candidates(manual_matches, "manual")
    _append_candidates(ocr_matches, "ocr")
    merged.sort(key=lambda item: item["start"])
    return merged


def split_targeted_search_terms(text):
    """cp65: 把识别/编辑后的文字拆成全文查找关键词列表。

    按任意空白（含换行）拆分、去重、去空；OCRWorker 内部同样按空白切分关键词，
    这里先行拆分保证 find→replace 映射逐词对齐。
    """
    if not isinstance(text, str):
        return []
    terms = []
    seen = set()
    for token in text.split():
        token = token.strip()
        if token and token not in seen:
            seen.add(token)
            terms.append(token)
    return terms


def build_targeted_keyword_rules(terms, replace_text):
    """cp65: 构造全文遮罩的关键词规则列表（逐词 find→replace 对齐）。

    安全审计 v40.1: 过滤 None/空/非 str 词项，防止 OCR 边界返回 None 被
    normalize_custom_keyword_rules 转成字符串 "None" 后误脱敏标题里的 "None"。
    """
    safe_terms = [t for t in (terms or []) if isinstance(t, str) and t.strip()]
    return [{"enabled": True, "find": t, "replace": replace_text} for t in safe_terms]


def format_targeted_terms_preview(terms, limit=3):
    """cp65: 信息栏预览文案：最多显示前 limit 个词，超出加省略号。"""
    return "、".join(terms[:limit]) + ("…" if len(terms) > limit else "")


def build_batch_summary_text(stage, total_selected, replacement_preview, *,
                             rule_count=0, processed=0, current_file="",
                             success_count=0, failed_count=0,
                             last_summary=None, default_rules=None):
    """v40.1.4（自 MainWindow 迁出）：构建批量 Word 工作台摘要文本（纯函数）。

    Args:
        stage: batch_stage（rule_setup / running / finished / stopped / 其他=初始）
        total_selected: 本轮文档总数
        replacement_preview: 统一替换文本预览
        rule_count: 启用 Word 规则数
        processed: 已处理数
        current_file: 当前文件名（running 阶段）
        success_count / failed_count: 成功/失败计数
        last_summary: 上一轮汇总 dict（含 success/failed/rules）
        default_rules: 无 last_summary 时用于规则明细的规则表
    """
    import os
    status_text = "已停止" if stage == "stopped" else "已完成"

    if stage == "rule_setup":
        lines = [
            "当前还在规则确认阶段，这一步不会改动任何原文件。",
            f"已载入文档：{total_selected} 个",
            f"当前启用 Word 规则：{rule_count} 条",
            f"统一替换文本：{replacement_preview}",
            "",
            "建议先确认：",
            "1. 文档数量是否正确",
            "2. 统一替换文本是否符合当前案卷习惯",
            "3. 是否至少启用了一条 Word 替换规则",
        ]
        return "\n".join(lines)

    if stage == "running":
        current_file = current_file or "正在准备下一个文档"
        lines = [
            "系统正在逐个处理 Word 文档。",
            f"当前进度：{processed}/{total_selected}",
            f"当前文件：{current_file}",
            f"已成功：{success_count} 个",
            f"已失败：{failed_count} 个",
            "",
            "如果遇到异常文件，可以在弹窗里选择跳过当前文件，或停止本轮任务。",
        ]
        return "\n".join(lines)

    if stage in ("finished", "stopped"):
        lines = [
            f"本轮批量替换{status_text}。",
            f"总文档数：{total_selected}",
            f"成功：{success_count} 个",
            f"失败：{failed_count} 个",
            f"统一替换文本：{replacement_preview}",
        ]

        summary = last_summary or {}
        success_items = summary.get("success", []) if isinstance(summary, dict) else []
        failed_items = summary.get("failed", []) if isinstance(summary, dict) else []
        summary_rules = summary.get("rules", default_rules) if isinstance(summary, dict) else default_rules

        from privacyguard.utils.helpers_ui import build_batch_rule_summary_lines
        rule_lines = build_batch_rule_summary_lines(summary_rules, success_items, replacement_preview)
        if rule_lines:
            lines.append("")
            lines.append("本次替换规则：")
            lines.extend(rule_lines)

        if success_items:
            lines.append("")
            lines.append("最近成功输出（最多 5 条）：")
            for item in success_items[:5]:
                output_path = item.get("output", "")
                lines.append(f"- {os.path.basename(output_path) if output_path else '已生成输出文件'}")

        if failed_items:
            lines.append("")
            lines.append("失败详情（最多 5 条）：")
            for item in failed_items[:5]:
                input_name = os.path.basename(item.get("input", ""))
                error_text = item.get("error", "")
                lines.append(f"- {input_name}: {error_text}")

        return "\n".join(lines)

    lines = [
        "批量 Word 工作台适合把同一套替换规则一次应用到多个 Word 文档。",
        "系统会先进入规则确认，再开始批量执行，最后集中展示结果。",
        f"统一替换文本：{replacement_preview}",
    ]
    return "\n".join(lines)
