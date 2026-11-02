# -*- coding: utf-8 -*-
"""PrivacyGuard Word 预览面板与高亮筛选函数。

v37.8.11 重构 Phase 1: 从 main.py 提取，原位于 helpers.py。
本模块承载与 Word 预览面板增量刷新脚本、面板重载判定、高亮来源筛选、
OCR 命中关键词行内替换解析相关的纯函数与常量，均不依赖 MainWindow 状态。

包含:
- 常量 (WORD_PREVIEW_IMAGE_EXTENSION_MAP / WORD_PREVIEW_BLOCK_SELECTOR
  / HIGHLIGHT_FILTER_SOURCES)
- 图片后缀推导 (resolve_word_preview_image_suffix)
- 面板刷新脚本 (build_word_panel_update_script)
- 面板重载判定 (should_reload_word_panel)
- 高亮来源筛选 (resolve_enabled_highlight_sources
  / build_highlight_source_filter_script)
- OCR 命中替换解析 (resolve_word_ocr_replacements)
"""

import re
import json

__all__ = [
    "WORD_PREVIEW_IMAGE_EXTENSION_MAP",
    "WORD_PREVIEW_BLOCK_SELECTOR",
    "HIGHLIGHT_FILTER_SOURCES",
    "resolve_word_preview_image_suffix",
    "build_word_panel_update_script",
    "should_reload_word_panel",
    "resolve_enabled_highlight_sources",
    "build_highlight_source_filter_script",
    "resolve_word_ocr_replacements",
]


# === 常量（随函数提取） ===

WORD_PREVIEW_IMAGE_EXTENSION_MAP = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/tiff": ".tiff",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def resolve_word_preview_image_suffix(content_type):
    """根据 Mammoth 图片内容类型推导本地文件后缀。"""
    if not isinstance(content_type, str):
        return ".img"

    normalized = content_type.strip().lower()
    if normalized in WORD_PREVIEW_IMAGE_EXTENSION_MAP:
        return WORD_PREVIEW_IMAGE_EXTENSION_MAP[normalized]

    if "/" not in normalized:
        return ".img"

    subtype = normalized.split("/", 1)[1].split(";", 1)[0].strip()
    subtype = subtype.replace("+xml", "").replace("+zip", "")
    subtype = re.sub(r"[^a-z0-9]+", "", subtype)
    if not subtype:
        return ".img"
    return f".{subtype}"


WORD_PREVIEW_BLOCK_SELECTOR = '[data-word-block="1"][data-key]'


def build_word_panel_update_script(block_updates):
    """构建仅更新正文块的 Word 预览增量刷新脚本。"""
    payload = json.dumps(block_updates or {}, ensure_ascii=False)
    return f"""
        (function() {{
            const updates = {payload};
            const elements = document.querySelectorAll('{WORD_PREVIEW_BLOCK_SELECTOR}');
            elements.forEach(function(el) {{
                const key = el.dataset.key;
                if (Object.prototype.hasOwnProperty.call(updates, key)) {{
                    const nextHtml = updates[key];
                    if (el.innerHTML !== nextHtml) {{
                        el.innerHTML = nextHtml;
                    }}
                }}
            }});
        }})();
    """


def should_reload_word_panel(source_changed, loaded_source_path, current_file_path, panel_ready):
    """判断 Word 预览面板是否需要重新加载完整文档。"""
    if source_changed:
        return True
    if not panel_ready:
        return True
    return loaded_source_path != current_file_path


# 预览高亮的三类来源（与 merge_word_matches_with_priority 的 source 字段一致）
HIGHLIGHT_FILTER_SOURCES = ("rule", "manual", "ocr")


def resolve_enabled_highlight_sources(selected):
    """将任意来源选择归一化为合法、有序、去重的列表。

    - None 视为“全部启用”（默认不筛选）；
    - 非法/未知来源被忽略；
    - 输出顺序固定为 rule/manual/ocr，便于等值比较与测试。
    """
    if selected is None:
        return list(HIGHLIGHT_FILTER_SOURCES)
    if isinstance(selected, str):
        selected = [selected]
    try:
        selected_set = set(selected)
    except TypeError:
        return list(HIGHLIGHT_FILTER_SOURCES)
    return [source for source in HIGHLIGHT_FILTER_SOURCES if source in selected_set]


def build_highlight_source_filter_script(enabled_sources):
    """构建按来源筛选预览高亮的 JS：未启用来源的 <mark> 标记 data-hl-filtered（保留文字）。

    与 build_word_panel_update_script 一致采用纯函数 + querySelectorAll 方式，便于单测。
    筛选仅去除高亮背景（通过 CSS 对 data-hl-filtered 生效），不删除或改变文字内容。
    """
    enabled = resolve_enabled_highlight_sources(enabled_sources)
    payload = json.dumps(enabled, ensure_ascii=False)
    return f"""
        (function() {{
            const enabled = {payload};
            const marks = document.querySelectorAll('mark[data-source]');
            marks.forEach(function(m) {{
                const src = m.getAttribute('data-source');
                if (enabled.indexOf(src) === -1) {{
                    m.setAttribute('data-hl-filtered', '1');
                }} else {{
                    m.removeAttribute('data-hl-filtered');
                }}
            }});
        }})();
    """


def resolve_word_ocr_replacements(ocr_matches, custom_keyword_rules, default_replacement_text=None):
    """cp63: Word 扫描命中按关键词行内替换文本（"find|replace"）解析替换文本。

    Word 链路替换文本优先级：
      1. Word 替换规则设置（merge_word_matches_with_priority 中 rule 源先占位，天然最高）
      2. 关键词行内替换（本函数：命中文本与启用关键词 find 一致时覆盖 replacement）
      3. 统一替换文本（传入 default_replacement_text 时实时覆盖，避免扫描时
         烘焙的旧值在设置变更后不生效；为 None 则保留扫描时写入的值）

    Args:
        ocr_matches: WordWorker 扫描命中列表（含 text/replacement 字段）
        custom_keyword_rules: 规范化后的关键词规则列表
        default_replacement_text: 当前统一替换文本（可选）

    Returns:
        list: 新列表；被覆盖的条目为浅拷贝，不修改原始命中数据
    """
    if not ocr_matches:
        return []

    keyword_map = {}
    if isinstance(custom_keyword_rules, list):
        for rule in custom_keyword_rules:
            if not isinstance(rule, dict) or not rule.get("enabled", True):
                continue
            find_text = str(rule.get("find", "") or "").strip()
            replace_text = str(rule.get("replace", "") or "").strip()
            if find_text and replace_text:
                keyword_map.setdefault(find_text, replace_text)
                # 关键词匹配为 IGNORECASE，英文命中大小写可能与 find 不同
                keyword_map.setdefault(find_text.casefold(), replace_text)

    fallback_text = default_replacement_text if isinstance(default_replacement_text, str) and default_replacement_text else None

    resolved = []
    for item in ocr_matches:
        if isinstance(item, dict):
            hit_text = str(item.get("text", "") or "")
            inline_replace = keyword_map.get(hit_text) or keyword_map.get(hit_text.casefold())
            if inline_replace:
                item = dict(item, replacement=inline_replace)
            elif fallback_text is not None:
                item = dict(item, replacement=fallback_text)
        resolved.append(item)
    return resolved
