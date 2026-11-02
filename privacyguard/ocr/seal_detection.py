"""印章检测算法（v37.8.11 P1-2 从 ocr_worker.py 外提）

多特征评分融合检测，应对变形/淡色/叠加场景：
- 颜色密度 + 圆形度 + 长宽比 + 五角星 + OCR 文字，多信号融合
- 双通道 CLOSE 核（小核清晰章 + 大核断环章）

历史版本：v37.7.18 cp52（坐标偏移修复 + 阈值放宽 + 评分融合）、
          v37.7.19 cp57（关键词收紧）、cp59（圆盘充实度 + 半径上限 150pt）
"""

import cv2
import numpy as np
from PyQt6.QtCore import QRectF

from privacyguard.utils.logger import get_logger

logger = get_logger("seal_detection")

# v37.7.18 cp53: 印章文字关键词（用于 OCR 文字验证）
# 匹配印章中常见文字，作为颜色+形状之外的第二/第三验证信号
# cp53 关键修复：去除单字关键词（"局"/"院"/"所"等在中文文档太常见，
#   红色标题"人民法院"的"院"会误命中，导致大面积误判）
# v37.7.19 cp57: 收紧 2 字关键词为 3 字以上组合，避免红色标题"法院""政府"误命中
SEAL_KEYWORDS = [
    # 印章类型（强信号，多字组合，误判率低）
    "公章", "专用章", "财务章", "合同章", "发票章", "人事章", "业务章", "法人",
    # 单位结尾（3 字以上组合，cp57 收紧：去除 2 字"法院""政府"等易误命中词）
    "有限公司", "集团公司", "股份有限", "委员会", "办公室", "办事处", "分所", "分会",
    "派出所", "人民法庭", "人民法院", "人民检察院", "税务局", "工商局",
    # 机构类型（3 字以上）
    "人民政府", "行政机构", "事业单位", "企业单位", "合作社", "联合会", "协会",
]
# cp53: 去除单字关键词（原 ["公","章","司","局","院","所","室","部","处","科"]）
# 原因：单字在中文文档中太常见，红色标题/正文中的"院""局""所"会误命中
# cp57: 去除 2 字关键词（"公司""集团""法院""政府"等）
# 原因：2 字红色标题（如"法院""政府"）aspect_ratio≈2.0 可通过评分，产生误判
# 印章 OCR 通常能识别出 2 字以上（如"法院""公章"），不需要单字兜底
SEAL_CHAR_KEYWORDS = []


def detect_star_in_roi(roi_mask):
    """v37.7.18 cp52: 检测 ROI 掩码中是否存在五角星图案。

    v52 改进（应对扫描变形/盖在文字上）：
    - 顶点数容忍 8-12（变形后可能不是严格 10 顶点）
    - 5-7 顶点凹形也判为星形
    - solidity < 0.5 作为强信号
    - 多 epsilon 尝试增加鲁棒性

    Args:
        roi_mask: ROI 区域的二值化颜色掩码

    Returns:
        bool: 是否检测到五角星
    """
    try:
        h, w = roi_mask.shape[:2]
        roi_area = h * w
        if roi_area == 0:
            return False

        # 五角星面积范围：占 ROI 的 0.3% - 30%（变形/扫描质量差时面积可能波动）
        min_star_area = roi_area * 0.003
        max_star_area = roi_area * 0.30

        contours, _ = cv2.findContours(
            roi_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_star_area or area > max_star_area:
                continue

            peri = cv2.arcLength(contour, True)
            if peri == 0:
                continue

            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = (area / hull_area) if hull_area > 0 else 1.0

            # 多 epsilon 尝试
            for eps_ratio in [0.02, 0.03, 0.05, 0.08, 0.10]:
                approx = cv2.approxPolyDP(contour, eps_ratio * peri, True)
                n = len(approx)

                # 五角星：10 顶点（5外+5内），容忍 8-12 顶点应对变形
                if 8 <= n <= 12 and solidity < 0.7:
                    return True
                # 5-7 顶点凹形（变形后顶点合并）
                if 5 <= n <= 7 and solidity < 0.55:
                    return True

        return False
    except Exception:
        return False


def ocr_seal_region(roi_img, ocr_engine):
    """v37.7.18 cp51: 对印章候选区域执行 OCR 文字识别。

    印章文字排列为弧形，OCR 可能只识别出部分字，
    只要命中关键词即认为是印章。

    Args:
        roi_img: ROI 区域图像（BGR）
        ocr_engine: OCR 引擎实例

    Returns:
        str: 识别到的文字（拼接）
    """
    if ocr_engine is None:
        return ""
    try:
        results = ocr_engine.recognize(roi_img)
        texts = []
        for r in results:
            if hasattr(r, "text"):
                texts.append(r.text)
            elif isinstance(r, (list, tuple)) and len(r) >= 2:
                texts.append(str(r[1]))
        return "".join(texts)
    except Exception:
        return ""


def detect_seals(img_np, scan_scale, ocr_engine=None, page_origin=(0.0, 0.0),
                 ring_close_px=None):
    """v37.7.18 cp52: 印章检测（多特征评分融合，应对变形/淡色/叠加场景）。

    v52 核心修复（针对用户反馈的三类问题）：
    1. **坐标偏移修复**：增加 page_origin 参数补偿 page.rect (x0, y0)
       旧版 `pdf_x = x / scan_scale` 未补偿 MediaBox 偏移，导致遮罩整体左/上偏移
    2. **放宽颜色阈值**：S/V 从 80 降到 40，覆盖半透明印章/扫描褪色/盖在文字上的淡色印章
    3. **放宽形状约束**：circularity 从 0.65 降到 0.5，长宽比从 [0.7,1.4] 放到 [0.5,2.0]
       应对扫描变形（圆形变椭圆）的印章
    4. **多特征评分**：颜色密度 + 圆形度 + 长宽比 + 五角星 + OCR 文字，多信号融合
    5. **遮罩扩大覆盖**：boundingRect 不收缩，并按 1.05 扩展，确保边缘完整覆盖
       旧版 shrink=0.05 反而让遮罩比实际印章更小

    评分逻辑（颜色阈值通过后，基础候选）：
    - 颜色密度 > 15% → +1
    - 圆形度 > 0.7 → +1
    - 长宽比 [0.8, 1.25] → +1
    - 五角星 → +3（强信号）
    - OCR 关键词命中 → +3（强信号）
    总分 ≥ 3 → 确认印章

    Args:
        img_np: 扫描图像（BGR 格式，必须为原始彩色图）
        scan_scale: 扫描缩放比例
        ocr_engine: OCR 引擎实例（可选）
        page_origin: PDF 页面 MediaBox 原点 (x0, y0)，用于坐标补偿
        ring_close_px: 大核 CLOSE 直径（可选，默认按 scan_scale 计算）

    Returns:
        list[QRectF]: 印章区域列表（PDF 坐标系，已补偿 page_origin）
    """
    seal_rects = []

    try:
        h, w = img_np.shape[:2]
        origin_x, origin_y = float(page_origin[0]), float(page_origin[1])

        # === 1. 颜色检测：红色 + 蓝色（放宽阈值应对淡色/扫描褪色）===
        hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)

        # 红色 HSV：S≥40 V≥40（v52 从 80 降到 40，覆盖半透明红章）
        red_mask1 = cv2.inRange(hsv, np.array([0, 40, 40]), np.array([15, 255, 255]))
        red_mask2 = cv2.inRange(hsv, np.array([165, 40, 40]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        # 蓝色 HSV：H 85-135 S≥40 V≥40
        blue_mask = cv2.inRange(hsv, np.array([85, 40, 40]), np.array([135, 255, 255]))

        base_mask = cv2.bitwise_or(red_mask, blue_mask)

        # === 面积阈值（按 scan_scale² 归一化）===
        # 典型公章半径 12-150pt（cp59：上限从 90 提到 150）。真实高 DPI 卷宗公章半径可达 120-130pt。
        min_radius_pt = 12
        max_radius_pt = 150
        min_area_px = np.pi * (min_radius_pt * scan_scale) ** 2
        max_area_px = np.pi * (max_radius_pt * scan_scale) ** 2
        open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))

        def _scan_close(close_px):
            """对 base_mask 施加指定 CLOSE 核，返回 [(QRectF, score, w, h, signals)]。"""
            found = []
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_px, close_px))
            cm = cv2.morphologyEx(base_mask, cv2.MORPH_CLOSE, k)
            cm = cv2.morphologyEx(cm, cv2.MORPH_OPEN, open_kernel)
            cnts, _ = cv2.findContours(cm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in cnts:
                area = cv2.contourArea(contour)
                if area < min_area_px or area > max_area_px:
                    continue
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue
                circularity = 4 * np.pi * area / (perimeter ** 2)
                if circularity < 0.5:
                    continue
                x, y, w_rect, h_rect = cv2.boundingRect(contour)
                aspect_ratio = float(w_rect) / h_rect if h_rect > 0 else 1
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                    continue
                roi = cm[y:y + h_rect, x:x + w_rect]
                if roi.size == 0:
                    continue
                color_ratio = float(np.sum(roi > 0)) / roi.size
                if color_ratio < 0.01 or color_ratio > 0.7:
                    continue
                # cp59: 圆盘充实度 = 轮廓面积 / 最小外接圆面积（比 perimeter 圆形度更稳）
                (_mcx, _mcy), min_circle_r = cv2.minEnclosingCircle(contour)
                min_circle_area = np.pi * (min_circle_r ** 2)
                disc_fill = float(area / min_circle_area) if min_circle_area > 0 else 0.0

                roi_img = img_np[y:y + h_rect, x:x + w_rect]
                has_star = detect_star_in_roi(roi)
                seal_text = ocr_seal_region(roi_img, ocr_engine)
                has_keyword = any(kw in seal_text for kw in SEAL_KEYWORDS)
                if not has_keyword:
                    has_keyword = any(ch in seal_text for ch in SEAL_CHAR_KEYWORDS)

                score = 0
                signals = []
                if color_ratio > 0.10:
                    score += 1
                    signals.append(f"密度:{color_ratio:.2f}")
                if circularity > 0.85:
                    score += 2
                    signals.append(f"高圆形度:{circularity:.2f}")
                elif disc_fill > 0.85 and 0.8 <= aspect_ratio <= 1.25:
                    # cp59: 真实扫描印章 perimeter 圆形度常 0.80-0.84（不足 0.85），
                    # 用更稳的圆盘充实度补充强信号（不依赖 OCR/五角星）
                    score += 2
                    signals.append(f"圆盘度:{disc_fill:.2f}")
                if 0.8 <= aspect_ratio <= 1.25:
                    score += 1
                    signals.append(f"长宽比:{aspect_ratio:.2f}")
                elif 0.5 <= aspect_ratio < 0.8 or 1.25 < aspect_ratio <= 2.0:
                    score += 1
                    signals.append(f"变形长宽比:{aspect_ratio:.2f}")
                if has_star:
                    score += 3
                    signals.append("五角星")
                if has_keyword:
                    if circularity > 0.5:
                        score += 3
                        signals.append(f"文字:{seal_text[:8]}")
                    else:
                        score += 1
                        signals.append(f"文字(低圆):{seal_text[:8]}")
                if score < 3:
                    continue

                expand = 0.05
                ex = w_rect * expand / 2
                ey = h_rect * expand / 2
                x0 = max(0, x - ex)
                y0 = max(0, y - ey)
                x1 = min(w, x + w_rect + ex)
                y1 = min(h, y + h_rect + ey)
                pdf_x = (x0 / scan_scale) + origin_x
                pdf_y = (y0 / scan_scale) + origin_y
                pdf_w = (x1 - x0) / scan_scale
                pdf_h = (y1 - y0) / scan_scale
                found.append((QRectF(pdf_x, pdf_y, pdf_w, pdf_h), score, w_rect, h_rect, signals))
            return found

        # cp59 双通道：小核（清晰/小/椭圆章，保持既有行为不回归）
        #            + 大核（断环大章，如墨迹不均的银行章）
        small_close = 3
        large_close = ring_close_px if ring_close_px is not None else max(3, int(round(9 * scan_scale)))
        all_found = _scan_close(small_close)
        if large_close != small_close:
            all_found += _scan_close(large_close)

        # 去重：与已确认矩形显著重叠（交集/较小框面积 > 0.5）则视为同一印章
        for rect, score, w_rect, h_rect, signals in all_found:
            dup = False
            for kept in seal_rects:
                ix0 = max(rect.x(), kept.x())
                iy0 = max(rect.y(), kept.y())
                ix1 = min(rect.x() + rect.width(), kept.x() + kept.width())
                iy1 = min(rect.y() + rect.height(), kept.y() + kept.height())
                if ix1 > ix0 and iy1 > iy0:
                    inter = (ix1 - ix0) * (iy1 - iy0)
                    smaller = min(rect.width() * rect.height(), kept.width() * kept.height())
                    if smaller > 0 and inter / smaller > 0.5:
                        dup = True
                        break
            if dup:
                continue
            seal_rects.append(rect)
            logger.debug("[Seal Detection] 确认印章: score=%s, "
                         "size=%sx%spx, "
                         "pdf=(%.1f,%.1f,%.1f,%.1f), "
                         "signals=[%s]",
                         score, w_rect, h_rect,
                         rect.x(), rect.y(), rect.width(), rect.height(),
                         ','.join(signals))

    except Exception as e:
        logger.error("[Seal Detection] 检测失败: %s: %s", type(e).__name__, e)

    return seal_rects
