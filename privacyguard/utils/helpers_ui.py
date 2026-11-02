# -*- coding: utf-8 -*-
"""PrivacyGuard 设置中心 / 工作台 / 密度 / 批量结果 UI 文案函数。

v37.8.11 重构 Phase 1: 从 main.py 提取，原位于 helpers.py。
本模块承载与设置页导航/摘要标签、批量替换结果表格与筛选、工作台引导、
工具栏模式文案、密度档位解析相关的纯函数，均不依赖 MainWindow 状态。

包含:
- 百分比格式化 (format_signed_percent)
- 设置中心文案 (build_settings_nav_labels / build_settings_hero_tags)
- 批量结果 (build_batch_result_rows / summarize_batch_result_rows
  / build_batch_filter_labels / filter_batch_result_rows
  / build_batch_rule_summary_lines)
- 工作台/工具栏文案 (build_workbench_guidance / build_toolbar_mode_labels)
- 密度档位 (_shift_density_mode / resolve_workspace_density_mode
  / resolve_settings_density_mode)
- 系统交互 (open_path_in_system: 跨平台用默认程序打开文件)
"""

import os

from privacyguard.utils.helpers_word_rules import normalize_word_replace_rules

__all__ = [
    "format_signed_percent",
    "build_settings_nav_labels",
    "build_settings_hero_tags",
    "build_batch_result_rows",
    "summarize_batch_result_rows",
    "build_batch_filter_labels",
    "filter_batch_result_rows",
    "build_batch_rule_summary_lines",
    "build_workbench_guidance",
    "build_toolbar_mode_labels",
    "_shift_density_mode",
    "resolve_workspace_density_mode",
    "resolve_settings_density_mode",
    "open_path_in_system",
]


def format_signed_percent(value):
    """将百分比格式化为适合界面展示的文案。"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    return f"{number:+d}%" if number else "0%"


def build_settings_nav_labels(enabled_rules, keyword_count, precision_is_default, ocr_adjust_value):
    """构建设置中心左侧导航标签。"""
    return [
        f"1 通用规则 · {max(0, int(enabled_rules))}项启用",
        f"2 自定义关键词 · {max(0, int(keyword_count))}条",
        f"3 扫描与微调 · {'默认' if precision_is_default else '已微调'}",
        f"4 OCR 检测框 · {format_signed_percent(ocr_adjust_value)}",
    ]


def build_settings_hero_tags(enabled_rules, keyword_count, enabled_word_rules, precision_is_default, ocr_adjust_value, scan_label):
    """构建设置页顶部的动态摘要标签。"""
    common_tag = (
        f"常用：规则 {max(0, int(enabled_rules))} 项 · "
        f"关键词 {max(0, int(keyword_count))} 条 · "
        f"Word {max(0, int(enabled_word_rules))} 条"
    )
    if precision_is_default:
        advanced_tag = f"高级：扫描推荐值 · OCR {format_signed_percent(ocr_adjust_value)}"
    else:
        normalized_scan_label = str(scan_label or "-").strip() or "-"
        advanced_tag = (
            f"高级：{normalized_scan_label} · "
            f"OCR {format_signed_percent(ocr_adjust_value)} · 已微调"
        )
    return common_tag, advanced_tag


def build_batch_result_rows(summary):
    """将批量替换 summary 转成结果表格行。"""
    if not isinstance(summary, dict):
        return []

    rows = []
    failed_items = summary.get("failed", []) if isinstance(summary.get("failed", []), list) else []
    success_items = summary.get("success", []) if isinstance(summary.get("success", []), list) else []

    for item in failed_items:
        if not isinstance(item, dict):
            continue
        input_path = str(item.get("input", "") or "")
        rows.append({
            "status": "失败",
            "status_key": "failed",
            "document": os.path.basename(input_path) if input_path else "未知文档",
            "detail": str(item.get("error", "") or "处理失败"),
            "action": "双击定位原文件",
            "open_path": input_path,
            "fallback_dir": os.path.dirname(input_path) if input_path else "",
        })

    for item in success_items:
        if not isinstance(item, dict):
            continue
        input_path = str(item.get("input", "") or "")
        output_path = str(item.get("output", "") or "")
        rows.append({
            "status": "成功",
            "status_key": "success",
            "document": os.path.basename(input_path) if input_path else "未知文档",
            "detail": os.path.basename(output_path) if output_path else "已生成输出文件",
            "action": "双击打开输出",
            "open_path": output_path,
            "fallback_dir": os.path.dirname(output_path) if output_path else "",
        })

    return rows


def summarize_batch_result_rows(rows):
    """汇总批量结果行数量。"""
    summary = {"total": 0, "success": 0, "failed": 0}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        summary["total"] += 1
        status_key = row.get("status_key")
        if status_key == "success":
            summary["success"] += 1
        elif status_key == "failed":
            summary["failed"] += 1
    return summary


def build_batch_filter_labels(summary_counts, show_counts=False):
    """构建批量结果筛选按钮文案。"""
    counts = summary_counts if isinstance(summary_counts, dict) else {}
    total = max(0, int(counts.get("total", 0) or 0))
    success = max(0, int(counts.get("success", 0) or 0))
    failed = max(0, int(counts.get("failed", 0) or 0))
    if not show_counts:
        return {"all": "全部", "success": "成功", "failed": "失败"}
    return {
        "all": f"全部 {total}",
        "success": f"成功 {success}",
        "failed": f"失败 {failed}",
    }


def filter_batch_result_rows(rows, filter_mode):
    """按筛选模式过滤批量结果行。"""
    if filter_mode not in {"all", "success", "failed"}:
        filter_mode = "all"

    filtered = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if filter_mode == "all":
            filtered.append(row)
        elif row.get("status_key") == filter_mode:
            filtered.append(row)
    return filtered


def build_batch_rule_summary_lines(rules, success_items, default_replacement_text="[已脱敏]"):
    """按规则生成批量替换摘要明细。"""
    normalized_rules = normalize_word_replace_rules(rules, default_replacement_text)
    if not normalized_rules:
        return []

    def _extract_rule_count(item, target_rule_index):
        if not isinstance(item, dict):
            return 0

        counts = item.get("rule_counts", [])
        if isinstance(counts, dict):
            try:
                return max(0, int(counts.get(str(target_rule_index), counts.get(target_rule_index, 0)) or 0))
            except (TypeError, ValueError):
                return 0

        if not isinstance(counts, list):
            return 0

        for entry in counts:
            if not isinstance(entry, dict):
                continue
            try:
                rule_index = int(entry.get("rule_index", -1))
                count = int(entry.get("count", 0) or 0)
            except (TypeError, ValueError):
                continue
            if rule_index == target_rule_index:
                return max(0, count)
        return 0

    lines = []
    for rule_index, rule in enumerate(normalized_rules, start=1):
        doc_parts = []
        replacement_text = rule.get("replace") or default_replacement_text

        for item in success_items or []:
            count = _extract_rule_count(item, rule_index - 1)
            if count <= 0:
                continue
            input_name = os.path.basename(str(item.get("input", "") or "")) or "未知文档"
            doc_parts.append(f"{input_name} 成功替换 {count} 条")

        if doc_parts:
            lines.append(
                f"{rule_index}、“{rule.get('find', '')}”替换为“{replacement_text}”，"
                + "，".join(doc_parts)
                + "；"
            )
        else:
            lines.append(
                f"{rule_index}、“{rule.get('find', '')}”替换为“{replacement_text}”，本轮未命中；"
            )

    return lines


def build_workbench_guidance(mode, batch_stage="rule_setup", has_results=False, compare_mode=False):
    """按当前模式生成顶部工作台的下一步引导标签。"""
    if mode == "pdf":
        first_step = "下一步：人工复核并导出" if has_results else "下一步：先点智能脱敏"
        return [
            first_step,
            "黑 / 白遮罩可立即切换",
            "支持手动画框补充脱敏",
        ]
    if mode == "word":
        compare_tip = "当前可隐藏对比预览" if compare_mode else "需要时可打开对比预览"
        first_step = "下一步：先检查替换规则" if not has_results else "下一步：复核替换结果"
        return [
            first_step,
            "原文预览与替换预览分开显示",
            compare_tip,
        ]
    if mode == "batch":
        if batch_stage == "running":
            return [
                "当前：正在批量替换文档",
                "可随时停止并保留已完成结果",
                "完成后可筛选成功 / 失败清单",
            ]
        if batch_stage in ("finished", "stopped"):
            return [
                "下一步：先看失败文档和原因",
                "可仅重试失败文档",
                "双击结果可打开输出或定位原文件",
            ]
        return [
            "下一步：确认规则后再开始执行",
            "这一步不会改动任何原文件",
            "建议至少启用一条 Word 替换规则",
        ]
    if mode == "image_merge":
        return [
            "下一步：确认图片顺序后开始合并",
            "支持多张图片自动合成为 PDF",
            "合并完成后会直接进入 PDF 脱敏",
        ]
    return [
        "支持拖拽导入，系统会自动分流",
        "PDF 走脱敏，Word 走替换",
        "多个 Word 会先进入批量规则确认",
        "多张图片可直接合并为 PDF",
    ]


def build_toolbar_mode_labels(mode, density_mode, has_results=False, enabled_word_rules=0):
    """构建工具栏在不同模式下的主动作文案。"""
    compact = density_mode != "wide"

    if mode == "pdf":
        if has_results:
            scan_text = "重脱" if compact else "重新脱敏"
            scan_tooltip = "重新执行 PDF 智能脱敏扫描"
        else:
            scan_text = "脱敏" if compact else "智能脱敏"
            scan_tooltip = "执行 PDF 智能脱敏扫描"
        save_text = "导出" if compact else "导出 PDF"
        save_tooltip = "导出当前 PDF 脱敏结果"
    elif mode == "word":
        if has_results:
            scan_text = "重替" if compact else "重新替换"
            scan_tooltip = "重新执行 Word 智能替换扫描"
        else:
            scan_text = "替换" if compact else "智能替换"
            scan_tooltip = "执行 Word 智能替换扫描"
        save_text = "导出" if compact else "导出 Word"
        save_tooltip = "导出当前 Word 替换结果"
    else:
        scan_text = "脱敏" if compact else "智能脱敏"
        save_text = "导出"
        scan_tooltip = "执行智能脱敏扫描"
        save_tooltip = "导出处理结果"

    if enabled_word_rules > 0:
        word_rules_text = f"规则 {enabled_word_rules}" if compact else f"替换规则 {enabled_word_rules}"
        word_rules_tooltip = f"打开 Word 替换规则（当前启用 {enabled_word_rules} 条）"
    else:
        word_rules_text = "规则" if compact else "替换规则"
        word_rules_tooltip = "打开 Word 替换规则"

    return {
        "open_text": "打开",
        "open_tooltip": "打开 PDF、Word 或图片文件",
        "scan_text": scan_text,
        "scan_tooltip": scan_tooltip,
        "save_text": save_text,
        "save_tooltip": save_tooltip,
        "word_rules_text": word_rules_text,
        "word_rules_tooltip": word_rules_tooltip,
    }


def _shift_density_mode(mode, order, step):
    """在既定密度序列里前后移动一档。"""
    if mode not in order:
        return mode
    index = order.index(mode)
    target = max(0, min(len(order) - 1, index + step))
    return order[target]


def resolve_workspace_density_mode(mode, width, height=0, scale=1.0):
    """解析主工作区工具栏密度档位，兼顾 Windows DPI 与窗口高度。"""
    width = max(int(width or 0), 1)
    height = max(int(height or 0), 0)
    scale = max(1.0, float(scale or 1.0))

    if mode == "pdf":
        wide_threshold = 1500
        compact_threshold = 1260
    elif mode == "word":
        wide_threshold = 1220
        compact_threshold = 980
    else:
        wide_threshold = 1080
        compact_threshold = 860

    if scale >= 1.5:
        wide_threshold += 90
        compact_threshold += 60
    elif scale >= 1.25:
        wide_threshold += 50
        compact_threshold += 30

    if height:
        if height >= 980:
            wide_threshold -= 50
            compact_threshold -= 30
        elif height <= 760:
            wide_threshold += 70
            compact_threshold += 40

    wide_threshold = max(compact_threshold + 80, wide_threshold)
    compact_threshold = max(720, min(compact_threshold, wide_threshold - 80))

    if width >= wide_threshold:
        return "wide"
    if width >= compact_threshold:
        return "compact"
    return "narrow"


def resolve_settings_density_mode(width, height=0, scale=1.0):
    """解析高级设置页密度档位，优先为 Windows 高 DPI 和不同窗口高度收口。"""
    width = max(int(width or 0), 1)
    height = max(int(height or 0), 0)
    scale = max(1.0, float(scale or 1.0))
    order = ["narrow", "compact", "roomy", "wide"]

    if width >= 1700:
        density_mode = "wide"
    elif width >= 1450:
        density_mode = "roomy"
    elif width >= 1260:
        density_mode = "compact"
    else:
        density_mode = "narrow"

    if scale >= 1.5:
        density_mode = _shift_density_mode(density_mode, order, -1)
        if width < 1360:
            density_mode = "narrow"
    elif scale >= 1.25 and density_mode == "wide" and width < 1760:
        density_mode = "roomy"

    if height:
        if height <= 820:
            density_mode = _shift_density_mode(density_mode, order, -1)
        elif height >= 980:
            if density_mode == "compact" and width >= 1380:
                density_mode = "roomy"
            elif density_mode == "roomy" and width >= 1600:
                density_mode = "wide"

    return density_mode


def open_path_in_system(path):
    """用系统默认程序打开文件，返回 ``(ok, error_msg)``。

    跨平台：Windows ``os.startfile`` / macOS ``open`` / Linux ``xdg-open``。
    用于导出成功弹窗"打开文档"按钮，使用电脑默认打开方式打开导出的文件。
    """
    import sys
    import subprocess
    if not path or not os.path.exists(path):
        return False, f"文件不存在：{path}"
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
