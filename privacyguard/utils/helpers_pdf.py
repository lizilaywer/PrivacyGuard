# -*- coding: utf-8 -*-
"""PrivacyGuard PDF 命中 / 页面操作 / 撤销重做 共享工具函数。

v37.8.11 重构 Phase 1: 从 main.py 提取，原位于 helpers.py。
本模块承载与 PDF 命中矩形、页面结构重排、撤销快照、全文遮罩命中合并
相关的纯函数，均不依赖 MainWindow 状态。

包含:
- 命中项访问辅助 (_hit_rect / _hit_replace_text / _make_hit)
- 矩形几何 (rects_overlap_ratio, transform_hit_rect_for_rotation)
- PDF 加密 (build_encrypt_save_kwargs)
- 全文搜索命中 (build_search_snippet, collect_text_hits)
- 页面结构重排 (shift_page_data_*/shift_page_set_*/clamp_grid_columns)
- 全文遮罩命中合并 (merge_targeted_hits)
- 撤销/重做快照 (snapshot_page_data / restore_page_data / push_undo_snapshot)
"""

from PyQt6.QtCore import QRectF

__all__ = [
    "_hit_rect",
    "_hit_replace_text",
    "_make_hit",
    "compute_replace_text_fontsize",
    "rects_overlap_ratio",
    "transform_hit_rect_for_rotation",
    "is_overlapping",
    "rect_contains",
    "is_half_overlapping",
    "deduplicate_rects",
    "build_encrypt_save_kwargs",
    "detect_pdf_password_state",
    "build_search_snippet",
    "collect_text_hits",
    "shift_page_data_for_insert",
    "shift_page_data_for_delete",
    "shift_page_set_for_insert",
    "shift_page_set_for_delete",
    "clamp_grid_columns",
    "merge_targeted_hits",
    "snapshot_page_data",
    "restore_page_data",
    "push_undo_snapshot",
    "extract_vertical_region_to_page",
    "crop_vertical_region_from_page",
    "build_result_doc_from_segments",
    "build_extract_report",
]


# v37.7.13 cp43: page_data 命中项兼容访问辅助函数
def _hit_rect(item):
    """从命中项提取 QRectF（兼容 dict 和裸 QRectF）。"""
    if isinstance(item, dict):
        return item.get('rect')
    return item


def _hit_replace_text(item):
    """从命中项提取替换文本（兼容 dict 和裸 QRectF）。"""
    if isinstance(item, dict):
        return item.get('replace_text', '')
    return ''


def _make_hit(rect, replace_text=''):
    """构造命中项 dict。"""
    return {'rect': rect, 'replace_text': replace_text or ''}


def compute_replace_text_fontsize(rect_w, rect_h, text, text_length, min_size=6.0):
    """cp65 修复：计算替换文本在导出 PDF 中的字号，与屏幕预览对齐。

    根因：屏幕预览（widgets._draw_replace_text）用 pixelSize = rect.height()*0.75
    + 宽度自适配；导出路径（save_pdf）原把文本交给 fitz add_redact_annot 的默认
    fontsize=11，且 fitz 会把超 h*0.625 的请求自动压到 ~h*0.625，导致导出文字
    系统性偏小（用户反馈"替换文字太小，与原文不匹配"）。

    本函数复刻屏幕路径的字号算法，返回 PDF 点空间字号：
      1) base = rect.height * 0.75（留 25% 上下边距）
      2) 若 text 在该字号下的宽度超出 rect.width-4，按宽度比例缩小

    入参 text_length 由调用方通过 fitz.get_text_length(text, fontname, base)
    传入——之所以分两步是因为 get_text_length 依赖 fitz，本函数保持纯数学
    便于单测。调用约定：先按 base 算 text_length，再传入本函数做宽度自适配。

    返回值即最终字号（float，pt）。
    """
    if rect_h <= 0:
        return min_size
    base = max(min_size, rect_h * 0.75)
    if text_length <= 0:
        return base
    avail_w = max(1.0, float(rect_w) - 4.0)
    if text_length > avail_w:
        # 与屏幕公式一致：按宽度比例缩
        return max(min_size, base * avail_w / text_length)
    return base


def rects_overlap_ratio(rect_a, rect_b):
    """cp65: 两个 QRectF 的重叠面积 / 较小矩形面积（0~1），用于全文遮罩命中去重。"""
    if rect_a is None or rect_b is None:
        return 0.0
    inter = rect_a.intersected(rect_b)
    if inter.isEmpty():
        return 0.0
    inter_area = inter.width() * inter.height()
    min_area = min(rect_a.width() * rect_a.height(), rect_b.width() * rect_b.height())
    if min_area <= 0:
        return 0.0
    return inter_area / min_area


def transform_hit_rect_for_rotation(x, y, w, h, page_w, page_h, delta_deg):
    """cp67: 页面旋转后遮罩矩形的 display 坐标跟随变换。

    fitz 语义（已用真实渲染验证）：set_rotation 为顺时针，get_pixmap/画布坐标是
    旋转后的 display 坐标系。本函数把旋转前的 display 矩形映射到旋转后：
      +90（右转/CW）: (x,y,w,h) -> (H-y-h, x, h, w)
      -90（左转/CCW，即 270）: -> (y, W-x-w, h, w)
      180: -> (W-x-w, H-y-h, w, h)
    其中 W/H 为旋转前的 display 宽高。

    Args:
        x, y, w, h: 旋转前 display 坐标矩形
        page_w, page_h: 旋转前 display 页宽高
        delta_deg: 本次旋转增量（±90/180，任意整百十度取模）

    Returns:
        (x', y', w', h') 旋转后 display 坐标矩形
    """
    d = delta_deg % 360
    if d == 90:
        return (page_h - y - h, x, h, w)
    if d == 270:
        return (y, page_w - x - w, h, w)
    if d == 180:
        return (page_w - x - w, page_h - y - h, w, h)
    return (x, y, w, h)


def build_encrypt_save_kwargs(open_pw, edit_pw):
    """cp72: 根据打开密码/编辑密码构建 PyMuPDF save() 的加密参数。

    语义：
    - 两者均为空 → 返回空 dict（不加密，导出普通 PDF）
    - user_pw = 打开密码（空则打开无需密码）
    - owner_pw = 编辑密码，缺省回退到打开密码（保证有权限主）
    - 设了编辑密码 → 受限权限（禁止修改/复制/注释，保留打印+无障碍读取）；
      未设编辑密码 → 全权限

    依赖 fitz常量惰性引用；纯函数可单测（空入参不触发 fitz 导入）。

    Args:
        open_pw: 打开密码（user password）
        edit_pw: 编辑密码（owner password）

    Returns:
        dict: save() 的加密 kwargs；无密码时为空 dict
    """
    open_pw = (open_pw or "").strip()
    edit_pw = (edit_pw or "").strip()
    if not open_pw and not edit_pw:
        return {}

    import fitz
    if edit_pw:
        # 受限权限：允许打印 + 无障碍读取；禁止修改/复制/注释
        permissions = int(fitz.PDF_PERM_PRINT | fitz.PDF_PERM_ACCESSIBILITY)
    else:
        # 仅打开密码：全权限（打开后不限制操作）
        permissions = int(
            fitz.PDF_PERM_PRINT | fitz.PDF_PERM_MODIFY | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_ANNOTATE | fitz.PDF_PERM_ACCESSIBILITY
        )
    return {
        "encryption": fitz.PDF_ENCRYPT_AES_256,
        "owner_pw": edit_pw or open_pw,
        "user_pw": open_pw,
        "permissions": permissions,
    }


def detect_pdf_password_state(doc):
    """cp113: 检测 PDF 文档的密码保护状态。

    用于打开 PDF 时判断是否需要弹密码框：
    - needs_user_pw: 打开需密码（user password 设置）
    - has_owner_restriction: 打开无需密码但编辑/复制等受限（owner password 设置，
      permissions 缺 MODIFY/COPY 等）。这类文档可直接打开，但用户可输入 owner
      密码解除限制后导出无限制副本。

    Args:
        doc: fitz.Document 实例（已 fitz.open，未 authenticate）

    Returns:
        dict: {
            'needs_user_pw': bool,
            'has_owner_restriction': bool,
            'permissions': int,
        }
        doc 为 None 或异常时返回全 False 的安全默认。
    """
    safe = {"needs_user_pw": False, "has_owner_restriction": False, "permissions": 0}
    if doc is None:
        return safe
    try:
        import fitz
        needs_user_pw = bool(doc.needs_pass)
        perms = int(doc.permissions)
        # owner restriction: 打开无需密码但权限受限
        missing_modify = not (perms & fitz.PDF_PERM_MODIFY)
        missing_copy = not (perms & fitz.PDF_PERM_COPY)
        has_owner_restriction = (not needs_user_pw) and (missing_modify or missing_copy)
        return {
            "needs_user_pw": needs_user_pw,
            "has_owner_restriction": has_owner_restriction,
            "permissions": perms,
        }
    except Exception:
        return safe


def build_search_snippet(text, start, kw_len, context_chars=18):
    """cp81: 以命中位置为中心截取上下文片段。

    Args:
        text: 全文文本
        start: 命中起始位置
        kw_len: 关键词长度
        context_chars: 关键词前后各截取的字符数

    Returns:
        (before, keyword, after) 三段文本；前/后被截断时加省略号；
        换行替换为空格（结果行单行展示）。HTML 转义由渲染层负责。
    """
    if not text or start < 0 or kw_len <= 0 or start + kw_len > len(text):
        return ("", "", "")
    b0 = max(0, start - context_chars)
    a1 = min(len(text), start + kw_len + context_chars)
    before = text[b0:start].replace("\n", " ").replace("\r", " ")
    keyword = text[start:start + kw_len].replace("\n", " ")
    after = text[start + kw_len:a1].replace("\n", " ").replace("\r", " ")
    if b0 > 0:
        before = "…" + before
    if a1 < len(text):
        after = after + "…"
    return (before, keyword, after)


def collect_text_hits(page_text, keyword, context_chars=18, max_hits_per_page=50):
    """cp81: 在页文本中大小写不敏感查找关键词，返回命中片段列表。

    Returns:
        list[(start_pos, before, kw_text, after)]；kw_text 保留原文大小写。
        无命中/空入参返回空列表；单页命中数设上限防极端重复字页面刷屏。
    """
    hits = []
    if not page_text or not keyword:
        return hits
    lower_text = page_text.lower()
    lower_kw = keyword.lower()
    pos = 0
    while len(hits) < max_hits_per_page:
        idx = lower_text.find(lower_kw, pos)
        if idx < 0:
            break
        before, kw_text, after = build_search_snippet(
            page_text, idx, len(keyword), context_chars)
        hits.append((idx, before, kw_text, after))
        pos = idx + len(keyword)
    return hits


def shift_page_data_for_insert(page_data, insert_at):
    """cp67: 在 insert_at 位置插入新页后重排 page_data 页码键。

    ≥insert_at 的键整体 +1，新页插入空条目；条目对象保持原引用（共享列表不断）。

    Returns:
        dict: 重排后的新字典
    """
    new_data = {}
    for idx, entry in page_data.items():
        new_data[idx + 1 if idx >= insert_at else idx] = entry
    new_data[insert_at] = {'ocr': [], 'manual': []}
    return new_data


def shift_page_data_for_delete(page_data, indices):
    """cp67: 删除若干页后重排 page_data 页码键（被删页条目丢弃）。"""
    removed = set(indices)
    new_data = {}
    for idx in sorted(page_data):
        if idx in removed:
            continue
        shift = sum(1 for d in removed if d < idx)
        new_data[idx - shift] = page_data[idx]
    return new_data


def shift_page_set_for_insert(pages, insert_at):
    """cp67: 插页后重排页码集合（如 _ocr_processed_pages）；新页不自动加入。"""
    return {p + 1 if p >= insert_at else p for p in pages}


def shift_page_set_for_delete(pages, indices):
    """cp67: 删页后重排页码集合，被删页码移除。"""
    removed = set(indices)
    result = set()
    for p in pages:
        if p in removed:
            continue
        result.add(p - sum(1 for d in removed if d < p))
    return result


def clamp_grid_columns(desired_cols, viewport_width, min_thumb_width=160, spacing=14):
    """cp67: 页面视图列数钳制：1 <= 列数 <= 视口能容纳的最大列数。

    Returns:
        int: 钳制后的列数（视口过窄时至少 1 列）
    """
    usable = max(0, viewport_width - spacing)
    max_cols = max(1, usable // (min_thumb_width + spacing))
    return int(min(max(desired_cols, 1), max_cols))


def merge_targeted_hits(candidates, existing_rects, overlap_threshold=0.5):
    """cp65: 全文遮罩命中合并——与已有矩形重叠 > overlap_threshold 的跳过。

    已接纳的命中会加入现有矩形集，后续候选与其重叠同样被跳过
    （与原 _on_targeted_page_result 内联逻辑一致）。

    Args:
        candidates: 候选命中项列表（dict 或裸 QRectF，已去重）
        existing_rects: 已存在的 QRectF 列表（可含 None，自动忽略）
        overlap_threshold: 重叠判重阈值（严格大于才跳过）

    Returns:
        list: 被接纳的命中项（保持输入顺序）
    """
    accepted = []
    existing = [r for r in existing_rects if r is not None]
    for item in candidates:
        r = _hit_rect(item)
        if r is None:
            continue
        if any(rects_overlap_ratio(r, ex) > overlap_threshold for ex in existing):
            continue
        accepted.append(item)
        existing.append(r)
    return accepted


def snapshot_page_data(page_data):
    """cp83: 将 page_data 深拷贝为可快照的纯数据结构（QRectF→元组）。

    返回 {page_num: {"ocr": [(x,y,w,h,replace_text)], "manual": [...]}}；
    与 Qt 对象解耦，避免快照与活动状态跨状态别名。
    """
    snap = {}
    for pn, entry in (page_data or {}).items():
        if not isinstance(entry, dict):
            continue
        snap_entry = {}
        for key in ("ocr", "manual"):
            items = entry.get(key, []) or []
            tuples = []
            for it in items:
                rect = _hit_rect(it)
                replace = _hit_replace_text(it)
                tuples.append((float(rect.x()), float(rect.y()),
                               float(rect.width()), float(rect.height()), replace))
            snap_entry[key] = tuples
        snap[pn] = snap_entry
    return snap


def restore_page_data(snapshot_pd):
    """cp83: 将 snapshot_page_data 产出的纯数据结构重建回 page_data。

    元组 (x,y,w,h,replace) → {'rect': QRectF, 'replace_text': replace}。
    每次重建产生全新列表与 QRectF，与快照无引用共享。
    """
    result = {}
    for pn, snap_entry in (snapshot_pd or {}).items():
        entry = {"ocr": [], "manual": []}
        for key in ("ocr", "manual"):
            for t in (snap_entry.get(key, []) or []):
                x, y, w, h, replace = t
                entry[key].append({'rect': QRectF(x, y, w, h),
                                   'replace_text': replace or ''})
        result[pn] = entry
    return result


def push_undo_snapshot(stack, snap, max_n):
    """cp83: 将快照压入栈，超过 max_n 弹出最早项（原地修改并返回 stack）。"""
    stack.append(snap)
    # 安全修复: 用切片替代 pop(0) 循环，更高效
    if len(stack) > max_n:
        del stack[:len(stack) - max_n]
    return stack



def extract_vertical_region_to_page(result_doc, src_doc, src_pno, y_min, y_max):
    """cp122: 把 src_doc 第 src_pno 页的 [y_min, y_max] 纵向区域提取为新页追加到 result_doc。

    保持矢量/原始内容（show_pdf_page），不重新光栅化。
    新页尺寸 = 原页宽度 × (y_max - y_min)，左右撑满原页宽度。

    Args:
        result_doc: fitz.Document，提取结果累积文档（新页追加到末尾）
        src_doc: fitz.Document，源文档
        src_pno: int，源文档页码
        y_min: float，裁剪区域上边界（display 坐标，PDF 点）
        y_max: float，裁剪区域下边界（display 坐标，PDF 点）

    Returns:
        int，新页在 result_doc 中的页码（= len(result_doc)-1）

    Raises:
        ValueError: 裁剪高度 < 1pt 或 y_min/y_max 越界
    """
    import fitz
    clip_height = float(y_max) - float(y_min)
    if clip_height < 1.0:
        raise ValueError(f"提取区域高度 {clip_height:.1f}pt 过小（需 ≥1pt）")
    src_page = src_doc[src_pno]
    page_w = src_page.rect.width
    page_h = src_page.rect.height
    # 钳制到页面范围
    y0 = max(0.0, min(float(y_min), page_h))
    y1 = max(0.0, min(float(y_max), page_h))
    if y1 - y0 < 1.0:
        raise ValueError("提取区域经页面边界钳制后高度不足 1pt")
    # display 坐标 → 未旋转 clip（旋转页用 derotation_matrix）
    disp_clip = fitz.Rect(0, y0, page_w, y1)
    if getattr(src_page, "rotation", 0):
        clip = (disp_clip * src_page.derotation_matrix).normalize()
    else:
        clip = disp_clip
    new_page = result_doc.new_page(width=page_w, height=y1 - y0)
    from privacyguard.utils.pdf_regions import copy_visible_pdf_region
    copy_visible_pdf_region(new_page, new_page.rect, src_doc, src_pno, clip)
    return len(result_doc) - 1


def crop_vertical_region_from_page(doc, page_idx, y_min, y_max):
    """cp122: 从 doc[page_idx] 截去 [y_min, y_max] 纵向区域，上下部分拼接为新页替换原页。

    保持矢量/原始内容。新页高度 = 原高 - 截去高（上部分 + 下部分拼接）。
    用"在 page_idx 后插入重建页 → 删除原 page_idx 页"实现原地替换。

    Args:
        doc: fitz.Document（原地修改）
        page_idx: int，要截去的页码
        y_min: float，截去区域上边界（display 坐标，PDF 点）
        y_max: float，截去区域下边界（display 坐标，PDF 点）

    Returns:
        float，新页高度（供视图刷新）

    Raises:
        ValueError: 截去后剩余高度 < 1pt（上 + 下都不够）或 y_min/y_max 越界
    """
    import fitz
    page = doc[page_idx]
    page_w = page.rect.width
    page_h = page.rect.height
    y0 = max(0.0, min(float(y_min), page_h))
    y1 = max(0.0, min(float(y_max), page_h))
    if y1 - y0 < 1.0:
        raise ValueError("截去区域高度不足 1pt")
    top_h = y0              # 上半部分保留高度
    bottom_h = page_h - y1  # 下半部分保留高度
    new_h = top_h + bottom_h
    if new_h < 1.0:
        raise ValueError(f"截去后剩余高度 {new_h:.1f}pt 过小（需 ≥1pt）")

    rotation = getattr(page, "rotation", 0)
    from privacyguard.utils.pdf_regions import copy_visible_pdf_region
    # 重建页：上半部分 + 下半部分两次 show_pdf_page 贴入
    tmp = fitz.open()
    new_page = tmp.new_page(width=page_w, height=new_h)
    if top_h > 0:
        disp_top = fitz.Rect(0, 0, page_w, y0)
        if rotation:
            top_clip = (disp_top * page.derotation_matrix).normalize()
        else:
            top_clip = disp_top
        copy_visible_pdf_region(new_page, fitz.Rect(0, 0, page_w, top_h), doc, page_idx, top_clip)
    if bottom_h > 0:
        disp_bottom = fitz.Rect(0, y1, page_w, page_h)
        if rotation:
            bottom_clip = (disp_bottom * page.derotation_matrix).normalize()
        else:
            bottom_clip = disp_bottom
        copy_visible_pdf_region(new_page, fitz.Rect(0, top_h, page_w, new_h), doc, page_idx, bottom_clip)

    # 原地替换：在 page_idx 后插入重建页，再删除原 page_idx 页
    # cp133: try/finally 保证 tmp.close；insert 后 delete 失败则回滚 insert
    try:
        doc.insert_pdf(tmp, start_at=page_idx + 1)
        try:
            doc.delete_page(page_idx)
        except Exception:
            # delete 失败 → 回滚 insert（删除刚插入的重建页，保留原页）
            doc.delete_page(page_idx + 1)
            raise
    finally:
        tmp.close()
    return new_h


def build_result_doc_from_segments(src_doc, segments):
    """cp122-fix: 根据片段列表构建提取结果文档（支持同页多片段上下拼接）。

    segments 结构：list[list[dict]]，外层每个元素是一个"结果页"，
    内层 list 是该结果页包含的片段（按从上到下顺序拼接）。
    每个片段 dict: {"src_pno": int, "y_min": float, "y_max": float}

    同一结果页的多个片段按顺序上下拼接（页高度 = 各片段高度之和），
    保持矢量（show_pdf_page）。不同结果页各自独立成页。

    Returns:
        fitz.Document（新构建的结果文档）

    Raises:
        ValueError: 片段高度不足或 segments 结构错误
    """
    import fitz
    if not segments:
        return fitz.open()
    result = fitz.open()
    for page_segments in segments:
        if not page_segments:
            continue
        # cp133: 越界检查（crop 删页后 src_pno 可能失效）
        for seg in page_segments:
            pno = seg.get("src_pno", -1)
            if not isinstance(pno, int) or pno < 0 or pno >= len(src_doc):
                raise ValueError(f"片段源页码 {pno} 越界（文档共 {len(src_doc)} 页）")
        # 计算各片段尺寸（以第一个片段的源页宽度为结果页宽度）
        first_src = src_doc[page_segments[0]["src_pno"]]
        page_w = first_src.rect.width
        # 计算每片段高度（钳制到各自源页边界）
        seg_heights = []
        clips = []
        for seg in page_segments:
            sp = src_doc[seg["src_pno"]]
            sp_h = sp.rect.height
            y0 = max(0.0, min(float(seg["y_min"]), sp_h))
            y1 = max(0.0, min(float(seg["y_max"]), sp_h))
            if y1 - y0 < 1.0:
                raise ValueError("片段高度不足 1pt")
            disp_clip = fitz.Rect(0, y0, page_w, y1)
            if getattr(sp, "rotation", 0):
                clips.append((disp_clip * sp.derotation_matrix).normalize())
            else:
                clips.append(disp_clip)
            seg_heights.append(y1 - y0)
        total_h = sum(seg_heights)
        if total_h < 1.0:
            raise ValueError("结果页总高度不足 1pt")
        new_page = result.new_page(width=page_w, height=total_h)
        cur_y = 0.0
        for seg, clip, seg_h in zip(page_segments, clips, seg_heights):
            from privacyguard.utils.pdf_regions import copy_visible_pdf_region
            copy_visible_pdf_region(new_page, fitz.Rect(0, cur_y, page_w, cur_y + seg_h),
                                    src_doc, seg["src_pno"], clip)
            cur_y += seg_h
    return result


def build_extract_report(segments, src_doc=None):
    """cp123: 根据片段模型生成提取结果报告文本（纯函数，供导出弹窗显示/导出）。

    Args:
        segments: list[list[dict]]，与 build_result_doc_from_segments 同结构
        src_doc: 可选 fitz.Document，用于计算每片段实际高度（钳制到源页边界后的高度）。
                 为 None 时高度用 y_max-y_min 原始差值。

    Returns:
        str: 格式化报告文本
    """
    if not segments:
        return "提取结果报告\n============\n（无提取内容）"
    non_empty = [p for p in segments if p]
    total_segs = sum(len(p) for p in non_empty)
    lines = ["提取结果报告", "============"]
    for p_idx, page_segs in enumerate(non_empty):
        lines.append(f"结果页 {p_idx + 1}（共 {len(non_empty)} 页）：")
        for s_idx, seg in enumerate(page_segs):
            y0 = float(seg["y_min"])
            y1 = float(seg["y_max"])
            if src_doc is not None:
                sp = src_doc[seg["src_pno"]]
                sp_h = sp.rect.height
                y0 = max(0.0, min(y0, sp_h))
                y1 = max(0.0, min(y1, sp_h))
            height = y1 - y0
            lines.append(
                f"  片段 {s_idx + 1}：原文档第 {seg['src_pno'] + 1} 页，"
                f"纵向 {y0:.1f}–{y1:.1f}（高 {height:.1f}pt）")
    lines.append("-" * 15)
    lines.append(f"共 {len(non_empty)} 页，{total_segs} 个片段")
    return "\n".join(lines)



# =====================================================================
# v40.1.4：矩形去重与几何判定（自 MainWindow 迁出为纯函数，铁律规则 4）
# =====================================================================

def is_overlapping(rect1, rect2, threshold=0.5):
    """检查两个矩形是否高度重叠（兼容 dict 元素，经 _hit_rect 提取 QRectF）。

    v37.7.13 cp43: 兼容 dict 元素。v37.7.15 cp45: 默认 IoU 阈值 0.7 → 0.5。
    """
    r1 = _hit_rect(rect1)
    r2 = _hit_rect(rect2)
    x_left = max(r1.x(), r2.x())
    y_top = max(r1.y(), r2.y())
    x_right = min(r1.x() + r1.width(), r2.x() + r2.width())
    y_bottom = min(r1.y() + r1.height(), r2.y() + r2.height())

    if x_right < x_left or y_bottom < y_top:
        return False

    intersection = (x_right - x_left) * (y_bottom - y_top)
    area1 = r1.width() * r1.height()
    area2 = r2.width() * r2.height()

    # IoU > threshold 视为重复
    union = area1 + area2 - intersection
    iou = intersection / union if union > 0 else 0

    # 或者中心点距离 < 5 像素也视为重复
    center1_x = r1.x() + r1.width() / 2
    center1_y = r1.y() + r1.height() / 2
    center2_x = r2.x() + r2.width() / 2
    center2_y = r2.y() + r2.height() / 2
    distance = ((center1_x - center2_x)**2 + (center1_y - center2_y)**2)**0.5

    return iou > threshold or distance < 5


def rect_contains(outer, inner, tolerance=3.0):
    """cp43-fix: 判断 outer 是否包含 inner（兼容 dict 元素）。

    tolerance 容纳 OCR box 与文本层 rect 的像素级偏移。
    """
    r1 = _hit_rect(outer)
    r2 = _hit_rect(inner)
    return (r1.x() <= r2.x() + tolerance
            and r1.y() <= r2.y() + tolerance
            and r1.x() + r1.width() >= r2.x() + r2.width() - tolerance
            and r1.y() + r1.height() >= r2.y() + r2.height() - tolerance)


def is_half_overlapping(rect1, rect2):
    """v37.7.15 cp45: 两矩形是否"半重叠"——x 重叠 ≥ 50% 且 y 重叠 ≥ 50%。

    用于合并 RapidOCR v3.x 返回的部分重叠 box（同一文字行的多个识别框），
    取并集后形成单一遮罩，避免多层叠加。
    """
    r1 = _hit_rect(rect1)
    r2 = _hit_rect(rect2)
    x_left = max(r1.x(), r2.x())
    y_top = max(r1.y(), r2.y())
    x_right = min(r1.x() + r1.width(), r2.x() + r2.width())
    y_bottom = min(r1.y() + r1.height(), r2.y() + r2.height())

    if x_right < x_left or y_bottom < y_top:
        return False

    inter_w = x_right - x_left
    inter_h = y_bottom - y_top
    min_w = min(r1.width(), r2.width())
    min_h = min(r1.height(), r2.height())
    if min_w <= 0 or min_h <= 0:
        return False

    x_overlap_ratio = inter_w / min_w
    y_overlap_ratio = inter_h / min_h

    return x_overlap_ratio >= 0.5 and y_overlap_ratio >= 0.5


def deduplicate_rects(rects):
    """移除重复或高度重叠的矩形 - v37.7.8 cp36 F13: 保留最窄 rect。

    v37.7.13 cp43: 兼容 dict 元素 {'rect': QRectF, 'replace_text': str}，
    通过 _hit_rect() 提取 QRectF 进行比较，但保留原始 dict 元素。
    cp43-fix: 包含关系合并——大 rect 完全包含小 rect 时保留大 rect 并合并 replace_text。
    v37.7.15 cp45: 半重叠合并——x 重叠 ≥ 50% 且 y 重叠 ≥ 50% → 取并集。
    """
    if not rects:
        return rects

    # v37.7.8 cp36 F13: 按面积升序排序（小的先入列），重复时保留较精确的小 rect
    sorted_rects = sorted(rects, key=lambda r: (_hit_rect(r).width() * _hit_rect(r).height(), _hit_rect(r).x(), _hit_rect(r).y()))
    deduped = []

    for rect in sorted_rects:
        is_duplicate = False
        contained_indices = []
        half_overlap_indices = []
        for i, existing in enumerate(deduped):
            if is_overlapping(rect, existing, threshold=0.5):
                is_duplicate = True
                break
            if rect_contains(rect, existing, tolerance=3.0):
                contained_indices.append(i)
                continue
            if rect_contains(existing, rect, tolerance=3.0):
                is_duplicate = True
                break
            if is_half_overlapping(rect, existing):
                half_overlap_indices.append(i)
                continue

        if contained_indices:
            merged_text = _hit_replace_text(rect)
            for i in sorted(contained_indices, reverse=True):
                merged_text = merged_text or _hit_replace_text(deduped[i])
                del deduped[i]
            deduped.append(_make_hit(_hit_rect(rect), merged_text))
        elif half_overlap_indices:
            merged_text = _hit_replace_text(rect)
            union_rect = _hit_rect(rect)
            for i in sorted(half_overlap_indices, reverse=True):
                merged_text = merged_text or _hit_replace_text(deduped[i])
                union_rect = union_rect.united(_hit_rect(deduped[i]))
                del deduped[i]
            deduped.append(_make_hit(union_rect, merged_text))
        elif not is_duplicate:
            deduped.append(rect)

    return deduped
