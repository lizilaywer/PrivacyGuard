# -*- coding: utf-8 -*-
"""电子卷宗 PDF 水印识别与去除（v37.7.11 cp40，v40.1.4 自 MainWindow 迁出为纯函数）。

针对律师卷宗常见的"律师证号+姓名"斜排文字层水印：
- detect_watermark_spans: rawdict 字符级 5 项评分制识别（用于确认对话框统计）
- remove_watermark_from_stream: 内容流级删除（q...Q 块三条件判定），
  真正移除绘制指令，不留白块、不影响与水印重叠的正文

纯逻辑不依赖 GUI/Qt（铁律规则 4），可独立单元测试。
"""
import re

__all__ = ["detect_watermark_spans", "parse_qq_blocks", "remove_watermark_from_stream"]

# 矩阵指令模式：a b c d e f cm / Tm（矩阵中 b≠0 或 c≠0 即有旋转/剪切分量）
_CM_PATTERN = re.compile(
    r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+cm'
)
_TM_PATTERN = re.compile(
    r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+Tm'
)
_EPSILON = 0.001  # 浮点容差


def detect_watermark_spans(page):
    """识别页面上的卷宗水印 span（律师证号+姓名，斜排文字层）。

    使用 rawdict 获取字符级信息，用于确认对话框统计。
    实际去除用内容流编辑（remove_watermark_from_stream），不依赖此处的 bbox。

    识别特征（5 项评分制，满足 ≥3 项判定为水印）：
      1. bbox 近似正方形且偏大：width > 50 且宽高比 0.4-2.5
         （旋转文字包围盒趋近正方形，正文 bbox 高度远小于宽度）
      2. 字体名含 CJK 关键词（NotoSansCJK / SourceHan / 思源 / SimSun / STSong 等
         任意 CJK 字体，不限定具体字体）
      3. 颜色非纯黑（color != 0，水印常用深灰/浅灰/浅红等，正文常纯黑）
      4. 文本含数字 + (含中文 或 长度≥6)
      5. 斜排检测：span 首末字符中心点连线斜率 |dy/dx| 在 0.1-10 之间
         （水平文字 dy≈0 斜率≈0，垂直文字 dx≈0 斜率∞，斜排水印斜率在中间）

    去重：以 (span_bbox, text) 为键去重，避免 PyMuPDF 双层文字重复返回。
    """
    CJK_FONT_KEYWORDS = (
        "NotoSansCJK", "SourceHan", "思源", "SimSun", "STSong",
        "SimHei", "STHeiti", "STKaiti", "STFangsong", "KaiTi",
        "FangSong", "Microsoft YaHei", "PingFang", "Heiti",
    )
    watermarks = []
    seen = set()
    try:
        d = page.get_text("rawdict")
    except Exception:
        return watermarks
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                chars = span.get("chars", [])
                if not chars:
                    continue
                text = "".join(c.get("c", "") for c in chars).strip()
                if not text:
                    continue
                bbox = span.get("bbox")
                if not bbox or len(bbox) != 4:
                    continue
                key = (
                    round(bbox[0], 1), round(bbox[1], 1),
                    round(bbox[2], 1), round(bbox[3], 1),
                    text,
                )
                if key in seen:
                    continue
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                font = span.get("font", "") or ""
                color = span.get("color", 0)

                # 特征1：近似正方形且偏大
                is_square_large = (
                    w > 50 and h > 50 and 0.4 < (w / h if h > 0 else 0) < 2.5
                )
                # 特征2：CJK 字体
                is_cjk_font = any(kw in font for kw in CJK_FONT_KEYWORDS)
                # 特征3：非纯黑
                is_not_black = color != 0
                # 特征4：水印文本模式
                has_digit = bool(re.search(r"\d", text))
                has_chinese = bool(re.search(r"[\u4e00-\u9fa5]", text))
                is_watermark_text = has_digit and (has_chinese or len(text) >= 6)
                # 特征5：斜排检测（首末字符中心点连线斜率）
                is_diagonal = False
                if len(chars) >= 2:
                    first_cb = chars[0].get("bbox")
                    last_cb = chars[-1].get("bbox")
                    if first_cb and last_cb and len(first_cb) == 4 and len(last_cb) == 4:
                        dx = (last_cb[0] + last_cb[2]) / 2 - (first_cb[0] + first_cb[2]) / 2
                        dy = (last_cb[1] + last_cb[3]) / 2 - (first_cb[1] + first_cb[3]) / 2
                        if abs(dx) > 1:
                            slope = abs(dy / dx)
                            # 水平文字 slope≈0，垂直文字 dx≈0，斜排 0.1-10
                            is_diagonal = 0.1 < slope < 10

                score = sum([
                    is_square_large, is_cjk_font, is_not_black,
                    is_watermark_text, is_diagonal,
                ])
                if score >= 3:
                    seen.add(key)
                    watermarks.append({"bbox": bbox, "text": text})
    return watermarks


def parse_qq_blocks(s):
    """解析内容流中的 q...Q 嵌套块，返回 [(start, end, content)] 顶层块列表。"""
    blocks = []
    depth = 0
    start = -1
    i = 0
    while i < len(s):
        if s[i] == 'q' and (i + 1 >= len(s) or s[i + 1] in ' \n\r\t'):
            if depth == 0:
                start = i
            depth += 1
            i += 1
            continue
        if s[i] == 'Q' and (i + 1 >= len(s) or s[i + 1] in ' \n\r\t'):
            depth -= 1
            if depth == 0 and start >= 0:
                blocks.append((start, i + 1, s[start:i + 1]))
                start = -1
            i += 1
            continue
        i += 1
    return blocks


def parse_bt_et_segments(s):
    """解析顶层 BT...ET 文本对象段，返回 [(start, end, content)]。

    带括号字符串深度守卫（正文文本括号内可能出现 "ET" 字样，不能误判边界）。
    """
    segs = []
    i = 0
    n = len(s)
    while i < n:
        if s.startswith("BT", i) and (i + 2 >= n or s[i + 2] in ' \n\r\t'):
            j = i + 2
            depth = 0
            seg_end = -1
            while j < n:
                ch = s[j]
                if ch == '(':
                    # 转义括号 \\( 不改变深度
                    if j > 0 and s[j - 1] == '\\':
                        pass
                    else:
                        depth += 1
                elif ch == ')':
                    if j > 0 and s[j - 1] == '\\':
                        pass
                    else:
                        depth = max(0, depth - 1)
                elif depth == 0 and s.startswith("ET", j) and (j + 2 >= n or s[j + 2] in ' \n\r\t'):
                    seg_end = j + 2
                    break
                j += 1
            if seg_end == -1:
                break  # 未闭合，放弃后续
            segs.append((i, seg_end, s[i:seg_end]))
            i = seg_end
        else:
            i += 1
    return segs


def _remove_watermark_text(text, xobject_mode=False):
    """在内容流文本上执行水印块删除，返回 (new_text, removed_count)。

    v40.1.4（用户反馈"检测到但无法去除"）扩展三类删除目标：
      1. q...Q 块：cm 或 Tm 矩阵旋转 + Tf + 无 Do（原有，Tm 为新增）
      2. 裸 BT...ET 段（不处于任何顶层 q...Q 内）：旋转 Tm + Tf + 无 Do
      3. xobject_mode=True 时为 Form XObject 内部清理——额外要求块内
         文本对象数 ≤3（水印通常 1-2 个 BT；正文块多 BT 不整块删除防误伤）
    """
    cm_pattern = _CM_PATTERN
    epsilon = _EPSILON

    def matrices_rotated(iterator):
        for m in iterator:
            b, c = float(m.group(2)), float(m.group(3))
            if abs(b) > epsilon or abs(c) > epsilon:
                return True
        return False

    def has_rotation(content):
        # v40.1.4：Tm 文本矩阵旋转与 cm 等价纳入（部分生成器只写 Tm 不写 cm）
        return (matrices_rotated(cm_pattern.finditer(content))
                or matrices_rotated(_TM_PATTERN.finditer(content)))

    def text_object_count(content):
        return content.count("BT")

    def is_watermark_block(content):
        has_text = "Tf" in content
        has_no_xobj = "Do" not in content
        if not (has_text and has_no_xobj and has_rotation(content)):
            return False
        if xobject_mode and text_object_count(content) > 3:
            return False  # 多文本对象=疑似正文，整块删除风险大
        return True

    def is_bare_text_watermark(content):
        return ("Tf" in content and "Do" not in content
                and matrices_rotated(_TM_PATTERN.finditer(content))
                and not matrices_rotated(cm_pattern.finditer(content)))

    removed = 0
    new_text = text
    changed = True
    _iter_guard = 0
    while changed and _iter_guard < 100:
        changed = False
        _iter_guard += 1
        blocks = parse_qq_blocks(new_text)
        qq_spans = [(s, e) for s, e, _ in blocks]
        for start, end, content in reversed(blocks):
            if is_watermark_block(content):
                new_text = new_text[:start] + new_text[end:]
                removed += 1
                changed = True
        if changed:
            continue
        # 裸 BT...ET（不在任何顶层 q...Q 内的旋转文本对象）
        for start, end, content in reversed(parse_bt_et_segments(new_text)):
            inside_qq = any(qs <= start < qe for qs, qe in qq_spans)
            if inside_qq:
                continue
            if is_bare_text_watermark(content):
                new_text = new_text[:start] + new_text[end:]
                removed += 1
                changed = True
    return new_text, removed


def _clean_form_xobjects(doc, page):
    """清理 Form XObject 内部的水印绘制指令（水印常被封装成 /Fm0 Do）。

    仅处理 Subtype=/Form 的对象；二进制图像流跳过。返回删除块数。
    """
    removed = 0
    try:
        xobjects = page.get_xobjects()
    except Exception:
        return 0
    for item in xobjects:
        xref = item[0]
        try:
            subtype = doc.xref_get_key(xref, "Subtype")
            if not subtype or subtype[1] != "/Form":
                continue
            data = doc.xref_stream(xref)
        except Exception:
            continue
        try:
            text = data.decode("latin-1", "replace")
        except Exception:
            continue
        new_text, n = _remove_watermark_text(text, xobject_mode=True)
        if n:
            try:
                doc.update_stream(xref, new_text.encode("latin-1"))
                removed += n
            except Exception:
                pass
    return removed


def remove_watermark_from_stream(doc, page):
    """直接编辑 PDF 内容流删除斜排水印绘制指令。

    判定一个 q...Q 块是否为水印（三条件全部满足）：
      1. 块内含 cm/Tm 指令且变换矩阵有旋转/剪切分量
         （即 b≠0 或 c≠0，单位矩阵是 1 0 0 1，平移矩阵 b=c=0）
         —— 支持任意旋转角度，不只 45°
      2. 块内含 Tf 指令（绘制文本，区分于纯图形块）
      3. 块内不含 Do 指令（避免误删 Form XObject 引用，如正文 /Fm1 Do）

    满足三条件才删除整个 q...Q 块，正文绝不触发（正文不旋转）。

    v40.1.4（用户反馈"检测到水印但无法去除"）新增两类目标：
      - 裸 BT...ET 旋转文本段（Tm 旋转、不在 q...Q 内）
      - Form XObject 内部的水印绘制（/Fm0 Do 场景，仅清 /Form 内部指令）

    Args:
        doc: fitz.Document（update_stream 写回内容流）
        page: fitz.Page
    Returns:
        int: 删除的绘制块数量（页内容流 + Form XObject 内部合计）
    """
    try:
        contents = page.read_contents()
        text = contents.decode("latin-1")
    except Exception:
        return 0

    new_text, removed = _remove_watermark_text(text)

    if removed:
        # 写回内容流（v40.1.4：多段内容流合并写回首段并清空其余；
        # 写回失败如实返回 0——不能声称已删除实际未删的块）
        try:
            xref_list = page.get_contents()
            new_bytes = new_text.encode("latin-1")
            if xref_list:
                doc.update_stream(xref_list[0], new_bytes)
                for xref in xref_list[1:]:
                    doc.update_stream(xref, b"")
        except Exception:
            removed = 0

    # v40.1.4：Form XObject 内部的水印指令清理（/Fm0 Do 场景）
    removed += _clean_form_xobjects(doc, page)
    return removed
