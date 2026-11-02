"""白名单 HTML 消毒器（P1-3 XSS 防御纵深）。

威胁模型
--------
Word 预览把 mammoth 生成的 HTML 在 QWebEngineView（file:// 上下文）中渲染，并注册了
pyBridge（可调用 add/remove_manual_redaction）。若恶意文档经由 mammoth 反射未转义
内容（超链接目标 / alt 文本 / 域代码等），可能注入可执行脚本，进而经 pyBridge 移除
遮罩后导出 = 漏脱。

本模块对 mammoth 输出做白名单消毒：仅保留安全标签与属性，移除 <script>/<style>/
<iframe> 等危险标签、所有 on* 事件处理器、javascript:/vbscript:/data:text/html 等
危险 URL scheme，以及 CSS 中的 expression()/@import。

放置时机
--------
消毒发生在 mammoth 输出阶段（body 片段），可信的交互 JS（word_preview_interactive.js）
在更下游的 _inject_interactive_html 中作为 <script> 注入，故不受消毒影响。
"""
from __future__ import annotations

from bs4 import BeautifulSoup, Comment

__all__ = ["sanitize_preview_html"]

# 允许的标签白名单（mammoth 常见输出 + 预览所需排版标签）
ALLOWED_TAGS = frozenset({
    "p", "span", "div", "br", "b", "i", "u", "strong", "em", "s", "strike",
    "sub", "sup", "small", "mark", "abbr", "cite", "q", "time", "del", "ins",
    "ruby", "rt", "rp",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "code",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption",
    "colgroup", "col",
    "img", "a", "hr",
})

# 标签专属允许属性
_TAG_ATTRS = {
    "img": frozenset({"src", "alt", "title", "width", "height", "loading", "decoding"}),
    "a": frozenset({"href", "title", "name", "target"}),
    "td": frozenset({"colspan", "rowspan"}),
    "th": frozenset({"colspan", "rowspan"}),
    "col": frozenset({"span", "width"}),
    "colgroup": frozenset({"span"}),
}

# 所有标签通用的安全属性（含下游高亮/keyed-patching 用的 data-* 锚点）
_GLOBAL_ATTRS = frozenset({
    "class", "style", "id",
    "data-key", "data-original-text", "data-source", "data-hl-filtered",
    "data-pg-image-error",
})

# 安全审计 v40.1.4（A1）：离线应用策略——预览内一律禁止远程资源。
# href/src 仅允许：相对路径、片段锚点（#id）、data:image/*；
# 任何带 scheme 的绝对 URL（http/https/ftp/file/javascript/...）一律剥离，
# 防止文档内嵌链接点击后外联（泄露 IP/使用信号），或 img/CSS 触发网络信标。

# CSS 中需要剥离的危险子串（小写）
_CSS_DANGER_SUBSTRS = ("expression(", "javascript:", "vbscript:", "@import", "behavior:")


def _normalize_url(value):
    """归一化 URL 用于 scheme 检测（去空白/小写）。"""
    if not isinstance(value, str):
        value = " ".join(value) if isinstance(value, list) else str(value)
    return value.strip().lower().replace("\t", "").replace("\n", "").replace("\r", "")


def _is_safe_url(value):
    """离线策略：仅允许相对路径/片段锚点/data:image；任何带 scheme 的 URL 拒绝。

    scheme 判定：在首个 '/'、'?'、'#' 之前出现 ':' 即视为带 scheme
    （覆盖 http(s)://、ftp:、javascript:、data:text/html 等全部向量）。
    """
    norm = _normalize_url(value)
    if not norm:
        return True
    # data:image/* 允许（预览的 broken-image 回退用 data URI），其余 data: 拒绝
    if norm.startswith("data:image/"):
        return True
    # 协议相对 URL（//host/path）浏览器会解析为 http(s)，必须拒绝
    if norm.startswith("//"):
        return False
    for ch in norm:
        if ch == ":":
            return False
        if ch in "/?#":
            break
    return True


def _css_url_refs_safe(value):
    """CSS url(...) 引用逐一检查：仅允许相对路径与 data:image（防远程信标）。"""
    low = value.lower()
    idx = low.find("url(")
    while idx != -1:
        end = low.find(")", idx)
        if end == -1:
            return False  # 未闭合的 url(，保守拒绝
        ref = low[idx + 4:end].strip().strip("'\"")
        if not _is_safe_url(ref):
            return False
        idx = low.find("url(", end)
    return True


def _scrub_style(value):
    """若 style 含危险子串或远程 url() 引用则整体丢弃（保守）。"""
    if not isinstance(value, str):
        return None
    low = value.lower()
    if any(s in low for s in _CSS_DANGER_SUBSTRS):
        return None
    if "url(" in low and not _css_url_refs_safe(value):
        return None
    return value


def sanitize_preview_html(html):
    """白名单消毒 HTML 片段。

    Args:
        html: mammoth 输出的 HTML 字符串（通常为 body 片段）

    Returns:
        消毒后的 HTML 字符串；输入为空则原样返回；解析失败返回空串（fail-safe）。
    """
    if not html:
        return html or ""
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return ""

    for tag in soup.find_all(True):
        name = tag.name
        if name not in ALLOWED_TAGS:
            # script / style / iframe / object / embed / link / meta / form 等整体移除
            tag.decompose()
            continue

        allowed_for_tag = _TAG_ATTRS.get(name, frozenset()) | _GLOBAL_ATTRS
        for attr in list(tag.attrs.keys()):
            # 1. 所有 on* 事件处理器一律删除
            if attr.startswith("on"):
                del tag.attrs[attr]
                continue
            # 2. 非白名单属性删除
            if attr not in allowed_for_tag:
                del tag.attrs[attr]
                continue
            # 3. URL 属性做 scheme 校验
            if attr in ("href", "src"):
                val = tag.attrs[attr]
                if isinstance(val, list):
                    val = " ".join(val)
                if not _is_safe_url(val):
                    del tag.attrs[attr]
                    continue
            # 4. style 属性剥离危险子串
            if attr == "style":
                scrubbed = _scrub_style(tag.attrs[attr])
                if scrubbed is None:
                    del tag.attrs["style"]

    # 移除 HTML 注释（条件注释曾是 IE XSS 向量，Chromium 不执行但保守清除）
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()

    return str(soup)
