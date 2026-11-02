"""混合型 PDF 扫描辅助逻辑。"""

import re
import logging

import fitz
import numpy as np

from .text_pdf import _is_valid_luhn, _looks_like_idcard, _is_bank_card_pattern, verify_hit_by_pattern, _mask
from privacyguard.utils.exceptions import OCRInspectionError

# cp118: 统一日志（替代模块内散落的 print）
logger = logging.getLogger(__name__)


def compile_active_patterns(patterns):
    """编译启用的正则规则，跳过特殊标记和非法表达式。"""
    compiled = []
    for pattern in patterns or []:
        if not pattern or pattern in ("__SEAL_DETECTION__", "__SIGNATURE_DETECTION__"):
            continue
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            continue
    return compiled


def collect_embedded_image_clip_rects(page_dict, min_width=24, min_height=24, min_area=400):
    """从 page.get_text('dict') 中提取有效图片块区域。"""
    if not isinstance(page_dict, dict):
        return []

    clip_rects = []
    seen = set()
    for block in page_dict.get("blocks", []):
        if block.get("type") != 1:
            continue

        bbox = block.get("bbox")
        if not bbox or len(bbox) != 4:
            continue

        x0, y0, x1, y1 = (float(v) for v in bbox)
        width = x1 - x0
        height = y1 - y0
        if width < min_width or height < min_height or width * height < min_area:
            continue

        key = (round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2))
        if key in seen:
            continue
        seen.add(key)
        clip_rects.append((x0, y0, x1, y1))

    return clip_rects


def render_pdf_clip_to_bgr(page, clip_rect, scan_scale):
    """将 PDF 页面裁剪区域渲染为 OpenCV BGR 图像。

    v40.1.4（性能）：直接读 pixmap 原始 samples（RGB→BGR 视图拷贝），
    不再走 PNG 编码+解码往返——实测每页省约 31ms（快 5 倍+）。
    """
    clip = fitz.Rect(*clip_rect)
    pix = page.get_pixmap(
        matrix=fitz.Matrix(scan_scale, scan_scale),
        clip=clip,
        alpha=False,
    )
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return np.ascontiguousarray(arr[:, :, :3][:, :, ::-1])


def iter_ocr_lines(ocr_results):
    """统一遍历 OCR 结果，兼容 OCRResult 和 RapidOCR 原始结构。

    v37.7.18 cp50: v1.x 兼容分支说明
    - 主路径：当前 RapidOCREngine (v3.9.2) 返回 List[OCRResult]，命中第 68-70 行
    - 兼容路径：若用户按 rollback 约定退回 RapidOCR 1.2.3，且未经 RapidOCREngine
      封装直接传入 v1.x 原始结构 [[box, text, conf], ...]，命中第 72-73 行
      （参见 project_memory.md 中 RapidOCR 回退约定）
    """
    for result in ocr_results or []:
        if hasattr(result, "box") and hasattr(result, "text"):
            # v3.x 主路径：OCRResult 对象
            yield result.box, result.text
            continue

        if isinstance(result, (list, tuple)) and len(result) >= 2:
            # v1.x 兼容路径：[box, text, conf] 元组，仅回退时触发
            yield result[0], result[1]


def collect_image_block_ocr_hits(
    page,
    patterns,
    scan_scale,
    recognize_fn,
    calculate_rect_fn,
    clip_to_page_rect_fn,
    preprocess_fn=None,
    page_dict=None,
    render_clip_fn=None,
    image_clip_rects=None,
    on_block_failure_fn=None,
    is_cancelled_fn=None,
    shared_person_names=None,
    ocr_lines_sink=None,
):
    """对嵌入图片区域执行 OCR，并返回页面坐标系下的命中矩形。

    O2 保守脱敏：当某个图片块渲染/解码/OCR 失败（无法检视其内容）时，
    调用 on_block_failure_fn(clip_rect) 生成“整块覆盖”矩形并纳入结果，
    避免该区域因静默跳过而漏脱。回调返回 None 时表示不覆盖。

    v37.7.13 cp43: 返回值改为 list[(page_rect, matched_text)]，
    matched_text 为命中原文（失败覆盖块 matched_text 为空字符串）。
    cp_person_name: 返回值追加第 3 元素 rule_override（称谓人名块内两遍法
    发现的人名精确命中时为 "称谓人名"，其余 None）——消费方直接用其分类。

    cp_person_name 块内两遍法：带 pgname 命名组的称谓 pattern 先在该图片块
    全部 OCR 行上收集人名集合（第 1 遍），再把人名作为精确 pattern 逐行
    finditer（第 2 遍）——OCR 行级文本没有 search_for 全页搜索能力，两遍法
    实现"块内全文遮同名"（诉讼卷宗多为整页单块，块内≈页内）。

    P2: is_cancelled_fn 可选取消谓词；每个图片块 OCR 前检查，密集混合页可及时响应取消。
    """
    compiled_all = compile_active_patterns(patterns)
    if not compiled_all:
        return []

    # cp_person_name: 分流称谓人名 pattern（编译后 groupindex 含 lead；
    # v2 正则只消费称谓+分隔符，人名由引擎 lookahead 提取）
    pn_patterns = [p for p in compiled_all if "lead" in p.groupindex]
    compiled_patterns = [p for p in compiled_all if "lead" not in p.groupindex]

    if image_clip_rects is None:
        if page_dict is None:
            page_dict = page.get_text("dict")
        image_clip_rects = collect_embedded_image_clip_rects(page_dict)

    render_clip = render_clip_fn or render_pdf_clip_to_bgr
    hit_rects = []

    def _cover_failed_block(clip_rect, reason):
        logger.warning("[OCR] 图片区域无法检视，保守整块覆盖（%s）: %s", reason, clip_rect)
        if on_block_failure_fn is None:
            return
        fallback_rect = on_block_failure_fn(clip_rect)
        if fallback_rect is not None:
            # v37.7.13 cp43: 失败覆盖块 matched_text 为空字符串
            hit_rects.append((fallback_rect, "", None))

    for clip_rect in image_clip_rects or []:
        # P2: 每个图片块 OCR 前检查取消（密集混合页 OCR 耗时，及时响应取消避免感知卡顿）
        if is_cancelled_fn is not None and is_cancelled_fn():
            break
        try:
            clip_img = render_clip(page, clip_rect, scan_scale)
        except Exception as exc:
            _cover_failed_block(clip_rect, f"裁剪失败 {type(exc).__name__}: {exc}")
            continue

        if clip_img is None or getattr(clip_img, "size", 0) == 0:
            _cover_failed_block(clip_rect, "渲染结果为空")
            continue

        # v40.2.1: 空白渲染检测——损坏的 XObject 引用（如 "cannot find XObject 'n3'"）
        # 会让 MuPDF 渲染出纯色图且不抛异常，OCR 无文本后静默 0 命中 → 潜在漏检。
        # 灰度动态范围 < 8 的图不可能是正常文档扫描，按 O2 保守脱敏整块覆盖
        # （受调用方 30% 页面面积上限约束，不会大面积误遮）。
        try:
            if float(clip_img.max()) - float(clip_img.min()) < 8.0:
                _cover_failed_block(clip_rect, "渲染结果疑似空白（损坏资源）")
                continue
        except Exception:
            pass  # 数值检查失败不阻断主流程

        # 预处理失败同样意味着该图片块无法检视，保守整块覆盖而非中断整篇扫描
        try:
            scan_img = preprocess_fn(clip_img) if preprocess_fn else clip_img
        except Exception as exc:
            _cover_failed_block(clip_rect, f"预处理失败 {type(exc).__name__}: {exc}")
            continue

        try:
            ocr_results = recognize_fn(scan_img)
        except OCRInspectionError:
            raise
        except Exception as exc:
            _cover_failed_block(clip_rect, f"OCR 失败 {type(exc).__name__}: {exc}")
            continue

        lines = [(box, text) for box, text in iter_ocr_lines(ocr_results) if text]
        # v40.2.3: 行缓存——供 worker 扫描收尾用人名集回填早期页（clip 原点
        # 一并存，补偿时局部 rect → 页面坐标换算用）
        if ocr_lines_sink is not None:
            ocr_lines_sink.extend((clip_rect, box, text) for box, text in lines)

        # cp_person_name 第 1 遍：本块全部行收集称谓人名/机构名
        # v40.2.3: shared_person_names 为 worker 持有的跨页共享集合——本块
        # 新发现 union 进去，前页已发现的名称在本块第 2 遍同样精确遮罩
        # （"发现即全文档遮"：签名行等无锚点出现处靠此传播覆盖）
        block_name_patterns = []
        if pn_patterns:
            from privacyguard.ocr.person_name import (
                find_person_names_by_pattern, PERSON_NAME_RULE_NAME,
            )
            block_names = set()
            for _box, text in lines:
                for p in pn_patterns:
                    for name, _s, _e in find_person_names_by_pattern(text, p.pattern):
                        block_names.add(name)
            if block_names and shared_person_names is not None:
                shared_person_names |= block_names
            if shared_person_names:
                block_names = block_names | set(shared_person_names)
            if block_names:
                # 第 2 遍用的人名精确 pattern（re.escape 防正则元字符）
                block_name_patterns = [
                    (re.compile(re.escape(n)), PERSON_NAME_RULE_NAME)
                    for n in block_names
                ]

        # 命中发射统一走这里（含称谓人名的 rule_override）
        scan_patterns = [(p, None) for p in compiled_patterns] + block_name_patterns
        for box, text in lines:
            for pattern, rule_override in scan_patterns:
                # cp57: 仅对银行卡号 pattern 执行 Luhn 校验
                pattern_str = pattern.pattern if hasattr(pattern, 'pattern') else str(pattern)
                is_bank_card_pattern = _is_bank_card_pattern(pattern_str)
                for match in pattern.finditer(text):
                    matched_text = match.group(0)
                    # v37.7.18 cp55: 图片 OCR 路径同样增加银行卡号 Luhn 校验
                    # v37.7.18 cp56: 先排除身份证号，避免误伤
                    # v37.7.19 cp57: 仅对银行卡号 pattern 生效，避免过滤自定义正则
                    if is_bank_card_pattern and len(matched_text) >= 13 and len(matched_text) <= 19 and matched_text.isdigit():
                        if _looks_like_idcard(matched_text):
                            pass  # 身份证号，跳过 Luhn 校验
                        elif not _is_valid_luhn(matched_text):
                            logger.info("[cp55] OCR 数字串(len=%d %s) 不满足 Luhn 校验，跳过",
                                        len(matched_text), _mask(matched_text))
                            continue
                    # cp70: 统一社会信用代码/VIN 等带校验位 pattern 命中后二次校验
                    if not verify_hit_by_pattern(pattern_str, matched_text):
                        logger.info("[cp70] OCR 命中串(len=%d %s) 未通过校验位校验，跳过",
                                    len(matched_text), _mask(matched_text))
                        continue
                    local_rect = calculate_rect_fn(box, text, match.span(), scan_img)
                    if local_rect is None:
                        continue
                    page_rect = clip_to_page_rect_fn(local_rect, clip_rect)
                    if page_rect is not None:
                        # v37.7.13 cp43: 携带命中原文，用于后续查找替换文本
                        hit_rects.append((page_rect, matched_text, rule_override))

    return hit_rects
