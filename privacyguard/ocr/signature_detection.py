"""签名手印检测算法（v37.8.11 P1-2 从 ocr_worker.py 外提）

检测"手写签名 + 按手印"区域，返回遮罩矩形（PDF 坐标）。

锤点是按手印（紧实/凸/有脊线纹理的团块）：
- 红/粉色（常见）或黑色（复印件，保守处理）
- 形状特征：solidity≥0.62、extent≥0.40、aspect∈[0.4,2.5]、密度∈[0.35,0.85]

历史版本：cp60（签名手印检测）、cp62（回归测试）、cp69（暖色门控排除印刷字误报）
"""

import cv2
import numpy as np
from PyQt6.QtCore import QRectF

from privacyguard.utils.logger import get_logger

logger = get_logger("signature_detection")


def detect_signatures(img_np, scan_scale, page_origin=(0.0, 0.0)):
    """cp60: 检测"手写签名 + 按手印"区域，返回遮罩矩形（PDF 坐标）。

    锤点是按手印（紧实/凸/有脊线纹理的团块）：
    - 红/粉色（常见）或黑色（复印件，保守处理）
    - 形状特征（实测真实手印）：solidity≥0.62、extent≥0.40、aspect∈[0.4,2.5]、
      密度∈[0.35,0.85]（脊线留隙 → 非实心黑块；也非稀疏文字）
      → 可区分：手写笔画(solidity低)/印章细环(extent低)/实心黑块(密度≈1)/文字行(aspect大)
    检出手印后向外扩展（上方/四周）以覆盖相邻潦草签名。

    cp69: 黑色路径极易把楷体/仿宋印刷字（警/醒/嫌/解/翻等笔画密集字）与扫描污渍
    误判为手印。用户诉求：重点识别红/偏红色印泥，黑色拿捏不准宁可不识别。
    据此对黑色路径新增两道硬门控：
      ① 暖色门控：真手印印泥即使偏淡也偏红（R 通道 > B 通道）；黑色印刷字是中性
         灰（R≈G≈B）。要求 ROI 内暗像素平均 (R - B) ≥ 8 且不偏蓝。
      ② 提高形状/孔洞阈值：solidity/holes 收紧，进一步排除笔画型误报。

    Args:
        img_np: 扫描图像（BGR 格式）
        scan_scale: 扫描缩放比例
        page_origin: PDF 页面 MediaBox 原点 (x0, y0)，用于坐标补偿

    Returns:
        list[QRectF]: 签名手印区域列表（PDF 坐标系，已补偿 page_origin）
    """
    rects = []
    try:
        h, w = img_np.shape[:2]
        origin_x, origin_y = float(page_origin[0]), float(page_origin[1])

        hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)
        # 红/粉手印（比印章更宽：含低饱和粉色 S≥25）
        red1 = cv2.inRange(hsv, np.array([0, 25, 60]), np.array([15, 255, 255]))
        red2 = cv2.inRange(hsv, np.array([160, 25, 60]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(red1, red2)
        # 黑色手印（复印件）：脊线常为浅灰色（实测灰度 110-190），阈值 170 才能捕获
        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
        _, dark_mask = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY_INV)
        # cp69: 拆出 BGR 通道用于黑色路径暖色门控（真手印偏红，印刷字中性灰）
        b_ch, g_ch, r_ch = cv2.split(img_np)

        # 手印尺寸：半径 8-70pt（直径 ~0.5-5cm），比印章小
        min_r_pt, max_r_pt = 8, 70
        min_area = np.pi * (min_r_pt * scan_scale) ** 2
        max_area = np.pi * (max_r_pt * scan_scale) ** 2
        # 红/粉手印天然实心，小核即可（防对角红水印合并误报）；
        # 黑色脊线是细纹理，需较大核合并成实心 blob（实测 close≈7@1.5x 最佳，11+ 过度合并失效）
        k_red = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dark_close = max(5, int(round(4.5 * scan_scale)))
        k_dark = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dark_close, dark_close))

        def _scan(mask, is_dark, close_kernel, raw_mask=None):
            closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)
            # OPEN 断开薄桥（避免手印与相邻水印/噪声像素粘连→形成超大 blob→area超限被丢弃）
            open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            closed = cv2.morphologyEx(closed, cv2.MORPH_OPEN, open_k)
            cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                area = cv2.contourArea(c)
                if area < min_area or area > max_area:
                    continue
                x, y, ww, hh = cv2.boundingRect(c)
                aspect = float(ww) / hh if hh else 0
                # 黑色路径更保守（避免误涂文字块）
                if is_dark:
                    if aspect < 0.6 or aspect > 1.8:
                        continue
                elif aspect < 0.4 or aspect > 2.0:
                    continue  # 红路径收紧到 2.0（真实手印≤ 1.7，对角水印条片 2.1+）
                rect_area = ww * hh
                extent = area / rect_area if rect_area else 0
                if extent < 0.40:
                    continue  # 排除印章细环/细长笔画
                hull_area = cv2.contourArea(cv2.convexHull(c))
                solidity = area / hull_area if hull_area else 0
                solidity_min = 0.68 if is_dark else 0.62
                if solidity < solidity_min:
                    continue  # 排除散乱手写笔画/文字
                roi = closed[y:y + hh, x:x + ww]
                dens = float(np.sum(roi > 0)) / roi.size if roi.size else 0
                dens_hi = 0.80 if is_dark else 0.85
                if dens < 0.35 or dens > dens_hi:
                    continue  # 排除实心黑块(密度≈1)与稀疏区

                # 黑路径脊线纹理门控：手印脊线间隙形成大量封闭小孔（实测真手印
                # holes≥12：灰脊线型12/深黑实心型23）；手写字笔画不闭合（holes≤1）
                # cp69: holes 阈值 8→12 收紧，笔画密集的楷体/仿宋字（警/醒/嫌等）
                # 闭合后也能凑出 8-11 个孔，提高到 12 排除这类印刷字误报
                if is_dark and raw_mask is not None:
                    raw_roi = raw_mask[y:y + hh, x:x + ww]
                    inv = cv2.bitwise_not(raw_roi)
                    n_bg, _lb, bg_stats, _ct = cv2.connectedComponentsWithStats(
                        inv, connectivity=4)
                    holes = 0
                    for ci in range(1, n_bg):
                        bx, by = bg_stats[ci, 0], bg_stats[ci, 1]
                        bw_, bh_ = bg_stats[ci, 2], bg_stats[ci, 3]
                        touches_edge = (bx == 0 or by == 0
                                        or bx + bw_ >= ww or by + bh_ >= hh)
                        if not touches_edge and bg_stats[ci, cv2.CC_STAT_AREA] >= 3:
                            holes += 1
                    if holes < 12:
                        continue

                    # cp69: 暖色门控——真手印印泥偏红（R>B），黑色印刷字/污渍是
                    # 中性灰（R≈G≈B）。取 ROI 内暗像素（脊线本体）的平均 BGR，
                    # 要求 R 明显大于 B（暖色），否则判定为印刷字/污渍误报并排除。
                    ridge = raw_roi > 0  # 脊线像素掩码
                    ridge_count = int(np.sum(ridge))
                    if ridge_count < 10:
                        continue
                    r_roi = r_ch[y:y + hh, x:x + ww]
                    g_roi = g_ch[y:y + hh, x:x + ww]
                    b_roi = b_ch[y:y + hh, x:x + ww]
                    mean_r = float(np.mean(r_roi[ridge]))
                    mean_g = float(np.mean(g_roi[ridge]))
                    mean_b = float(np.mean(b_roi[ridge]))
                    # 暖色：红明显高于蓝；且不能偏冷（蓝高于红）。
                    # 印刷字/污渍 R-B≈0；淡红印泥 R-B 通常 ≥ 12。
                    if (mean_r - mean_b) < 10 or (mean_r - mean_g) < 3:
                        continue

                # 手印 → 向外扩展覆盖相邻签名（名字常写在手印上方/重叠）
                # 扩展适度，避免误覆盘相邻无关内容
                ex = ww * 0.15
                et = hh * 0.15
                eb = hh * 0.10
                bx0 = max(0, x - ex)
                by0 = max(0, y - et)
                bx1 = min(w, x + ww + ex)
                by1 = min(h, y + hh + eb)
                pdf_x = (bx0 / scan_scale) + origin_x
                pdf_y = (by0 / scan_scale) + origin_y
                pdf_w = (bx1 - bx0) / scan_scale
                pdf_h = (by1 - by0) / scan_scale
                rects.append((QRectF(pdf_x, pdf_y, pdf_w, pdf_h),
                              "红手印" if not is_dark else "黑手印",
                              ww, hh, solidity, extent, dens))

        _scan(red_mask, False, k_red)
        _scan(dark_mask, True, k_dark, raw_mask=dark_mask)

        # 去重（与已确认矩形重叠/较小框>0.5）
        kept = []
        for rect, tag, ww, hh, solidity, extent, dens in rects:
            dup = False
            for kr in kept:
                ix0 = max(rect.x(), kr.x())
                iy0 = max(rect.y(), kr.y())
                ix1 = min(rect.x() + rect.width(), kr.x() + kr.width())
                iy1 = min(rect.y() + rect.height(), kr.y() + kr.height())
                if ix1 > ix0 and iy1 > iy0:
                    inter = (ix1 - ix0) * (iy1 - iy0)
                    smaller = min(rect.width() * rect.height(), kr.width() * kr.height())
                    if smaller > 0 and inter / smaller > 0.5:
                        dup = True
                        break
            if dup:
                continue
            kept.append(rect)
            logger.debug("[Signature Detection] 确认签名手印: %s, size=%sx%spx, "
                         "solidity=%.2f, extent=%.2f, dens=%.2f, "
                         "pdf=(%.1f,%.1f,%.1f,%.1f)",
                         tag, ww, hh, solidity, extent, dens,
                         rect.x(), rect.y(), rect.width(), rect.height())
        return kept

    except Exception as e:
        logger.error("[Signature Detection] 检测失败: %s: %s", type(e).__name__, e)
        return []
