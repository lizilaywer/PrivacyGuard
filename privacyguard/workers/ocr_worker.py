"""
OCR 处理 Worker

v36.5: 模块化拆分，从 main.py 提取
v37.7.6: 全面上行 main.py 的高级特性：
  - 印章检测 (_detect_seals)
  - 像素级文本边界 (_detect_text_boundaries)
  - CJK 智能字符权重 (_calculate_from_line)
  - 检测框收缩 (_shrink_box)
  - box_adjust_ratio 参数
  - error_signal
  - RapidOCREngine 统一引擎接口
  - 坐标转换统一（在 calculate_sub_rect 内除以 scan_scale）
"""

import time
import traceback
import gc
import numpy as np
import cv2
import fitz
from PyQt6.QtCore import QThread, pyqtSignal, QRectF
import re

from privacyguard.ocr.mixed_pdf import (
    collect_embedded_image_clip_rects,
    collect_image_block_ocr_hits,
)
from privacyguard.ocr.text_pdf import collect_text_pdf_hit_boxes

# 常量定义
PROGRESS_UPDATE_INTERVAL = 0.05


class OCRWorker(QThread):
    """OCR 处理线程

    v36.4: 使用信号槽机制替代共享字典，解决线程安全问题
    v36.5: 模块化拆分
    v37.7.6: 全面上行高级特性
    """
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int)
    page_result_signal = pyqtSignal(int, list)  # v36.4: 逐页发送结果 (页码, 矩形列表)
    error_signal = pyqtSignal(str)  # v37.0.5: 错误信号

    def __init__(self, pdf_path, rules, use_enhance, custom_keywords, scan_scale, off_x, off_w,
                 use_char_level_ocr: bool = False, seal_detection_enabled: bool = False,
                 box_adjust_ratio: float = 0.0):
        super().__init__()
        self.pdf_path = pdf_path
        self.rules = rules
        self.use_enhance = use_enhance
        raw_keywords = custom_keywords.replace('\n', ' ').split()
        self.custom_keywords = [re.escape(k.strip()) for k in raw_keywords if k.strip()]
        self.scan_scale = scan_scale
        self.off_x = off_x
        self.off_w = off_w

        # v37.4.0: 只使用 RapidOCR，不再使用字符级 OCR
        self.use_char_level_ocr = False

        # v37.3.5: 检测框调节比例（支持负值扩大、正值收缩）
        self.box_adjust_ratio = box_adjust_ratio

        # v37.5.0: 印章检测功能
        self.seal_detection_enabled = seal_detection_enabled
        self._seal_detector = None  # 延迟加载
        print(f"[OCRWorker] 初始化, seal_detection_enabled={seal_detection_enabled}")

    def preprocess_image(self, img_np):
        """图像预处理"""
        try:
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = np.ones((2, 2), np.uint8)
            enhanced = cv2.erode(binary, kernel, iterations=1)
            return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        except cv2.error as e:
            print(f"图像处理错误: {e}")
            return img_np

    def _get_seal_detector(self):
        """v37.5.0: 印章检测器（使用 OpenCV，无需额外依赖）"""
        if self._seal_detector is not None:
            return self._seal_detector
        self._seal_detector = True
        return self._seal_detector

    def _detect_seals(self, img_np, scan_scale):
        """v37.5.0: 使用 OpenCV 检测印章区域

        检测策略：
        1. 颜色过滤：检测红色区域
        2. 形状分析：筛选圆形/椭圆形区域
        3. 尺寸过滤：排除过大或过小的区域

        Args:
            img_np: 扫描图像（BGR 格式）
            scan_scale: 扫描缩放比例

        Returns:
            list[QRectF]: 印章区域列表（PDF 坐标系）
        """
        seal_rects = []

        if not self._get_seal_detector():
            return seal_rects

        try:
            h, w = img_np.shape[:2]
            print(f"[Seal Detection] 开始检测，图像尺寸: {w}x{h}")

            hsv = cv2.cvtColor(img_np, cv2.COLOR_BGR2HSV)

            red_lower1 = np.array([0, 30, 30])
            red_upper1 = np.array([20, 255, 255])
            red_lower2 = np.array([160, 30, 30])
            red_upper2 = np.array([180, 255, 255])

            mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
            mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
            red_mask = cv2.bitwise_or(mask1, mask2)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
            red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"[Seal Detection] 红色轮廓数: {len(contours)}")

            for contour in contours:
                area = cv2.contourArea(contour)
                min_area = 100 * 100
                max_area = (h * w) * 0.5
                if area < min_area or area > max_area:
                    continue

                x, y, w_rect, h_rect = cv2.boundingRect(contour)

                roi = red_mask[y:y+h_rect, x:x+w_rect]
                if roi.size == 0:
                    continue
                red_ratio = np.sum(roi > 0) / roi.size
                if red_ratio < 0.3:
                    continue

                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = float(area) / hull_area if hull_area > 0 else 0
                if solidity < 0.7:
                    continue

                aspect_ratio = float(w_rect) / h_rect if h_rect > 0 else 1
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                    continue

                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    if circularity < 0.5:
                        continue

                pdf_x = x / scan_scale
                pdf_y = y / scan_scale
                pdf_w = w_rect / scan_scale
                pdf_h = h_rect / scan_scale

                seal_rects.append(QRectF(pdf_x, pdf_y, pdf_w, pdf_h))
                print(f"[Seal Detection] 检测到印章: red_ratio={red_ratio:.2f}, "
                       f"aspect={aspect_ratio:.2f}, circularity={circularity:.2f}")

        except Exception as e:
            print(f"[Seal Detection] 检测失败: {type(e).__name__}: {e}")

        return seal_rects

    def _shrink_box(self, box, x_ratio=0.15, y_ratio=0.1):
        """v37.3.3: 收缩检测框边距

        Args:
            box: OCR 检测框 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            x_ratio: 水平方向收缩比例
            y_ratio: 垂直方向收缩比例

        Returns:
            收缩后的检测框
        """
        x_coords = [p[0] for p in box]
        y_coords = [p[1] for p in box]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)

        width = x_max - x_min
        height = y_max - y_min

        x_shrink = width * x_ratio / 2
        y_shrink = height * y_ratio / 2

        new_x_min = x_min + x_shrink
        new_x_max = x_max - x_shrink
        new_y_min = y_min + y_shrink
        new_y_max = y_max - y_shrink

        if new_x_min >= new_x_max:
            new_x_min = x_min
            new_x_max = x_max
        if new_y_min >= new_y_max:
            new_y_min = y_min
            new_y_max = y_max

        return [[new_x_min, new_y_min], [new_x_max, new_y_min],
                [new_x_max, new_y_max], [new_x_min, new_y_max]]

    def _detect_text_boundaries(self, img_region, box):
        """v37.3.7: 像素级文本边界检测

        通过水平投影分析找到检测框内实际文字的左右边界。

        Args:
            img_region: 扫描图像（BGR格式）
            box: OCR 检测框

        Returns:
            (actual_left, actual_right): 实际文字左右边界
        """
        try:
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            x_min = int(max(0, min(x_coords)))
            x_max = int(min(img_region.shape[1], max(x_coords)))
            y_min = int(max(0, min(y_coords)))
            y_max = int(min(img_region.shape[0], max(y_coords)))

            if x_max <= x_min or y_max <= y_min:
                return int(min(x_coords)), int(max(x_coords))

            roi = img_region[y_min:y_max, x_min:x_max]
            if roi.size == 0:
                return int(min(x_coords)), int(max(x_coords))

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            h_projection = np.sum(binary, axis=0)
            threshold = max(1, binary.shape[0] * 0.05)
            text_cols = np.where(h_projection > threshold)[0]

            if len(text_cols) == 0:
                return int(min(x_coords)), int(max(x_coords))

            actual_left = x_min + text_cols[0]
            actual_right = x_min + text_cols[-1]

            return actual_left, actual_right

        except Exception as e:
            print(f"[DEBUG] _detect_text_boundaries 错误: {e}")
            x_coords = [p[0] for p in box]
            return int(min(x_coords)), int(max(x_coords))

    def calculate_sub_rect(self, box, text, match_span, img_region=None):
        """v37.4.0: 计算子字符串的矩形区域（行级计算 + 像素边界检测）

        Args:
            box: 整行文本的检测框
            text: 整行文本
            match_span: 匹配位置 (start_idx, end_idx)
            img_region: 扫描图像区域，用于像素边界检测

        Returns:
            QRectF: 子字符串矩形区域（PDF坐标系）
        """
        try:
            start_idx, end_idx = match_span
            return self._calculate_from_line(box, text, start_idx, end_idx, img_region=img_region)
        except (ValueError, ZeroDivisionError, TypeError) as e:
            print(f"[WARN] calculate_sub_rect 错误: {e}")
            return None

    def _calculate_from_line(self, box, text, start_idx, end_idx, img_region=None):
        """v37.3.7: 行级坐标估算 + 像素边界检测 + CJK 智能字符权重

        Returns:
            QRectF: 子字符串矩形区域（PDF坐标系）
        """
        try:
            # 优先使用像素边界检测
            if img_region is not None:
                line_x_min, line_x_max = self._detect_text_boundaries(img_region, box)
            else:
                shrunk_box = self._shrink_box(box, x_ratio=self.box_adjust_ratio,
                                               y_ratio=self.box_adjust_ratio * 0.6)
                line_x_min = min([p[0] for p in shrunk_box])
                line_x_max = max([p[0] for p in shrunk_box])

            line_y_min = min([p[1] for p in box])
            line_y_max = max([p[1] for p in box])

            if len(text) == 0 or line_x_max <= line_x_min:
                return None

            # 智能字符宽度估算（区分中文/数字/英文）
            def get_char_weight(char):
                if '\u4e00' <= char <= '\u9fff':  # CJK统一汉字
                    return 1.0
                elif '\u3400' <= char <= '\u4dbf':  # CJK扩展A
                    return 1.0
                elif '\uF900' <= char <= '\uFAFF':  # CJK兼容汉字
                    return 1.0
                else:
                    return 0.55  # 数字、英文、符号等

            total_weight = sum(get_char_weight(c) for c in text)
            prefix_weight = sum(get_char_weight(c) for c in text[:start_idx])
            match_weight = sum(get_char_weight(c) for c in text[start_idx:end_idx])

            if total_weight <= 0:
                total_weight = len(text)
                prefix_weight = start_idx
                match_weight = end_idx - start_idx

            line_width = line_x_max - line_x_min
            sub_x = line_x_min + (prefix_weight / total_weight) * line_width
            sub_w = (match_weight / total_weight) * line_width

            # 小边距
            margin = 1.0
            sub_x += margin
            sub_w = max(5, sub_w - margin * 2)

            # 坐标转换：扫描坐标 -> PDF坐标
            pdf_x = sub_x / self.scan_scale
            pdf_y = line_y_min / self.scan_scale
            pdf_w = sub_w / self.scan_scale
            pdf_h = (line_y_max - line_y_min) / self.scan_scale

            # PDF坐标系下应用偏移
            final_x = pdf_x - self.off_x
            final_w = max(5, pdf_w - self.off_w)

            return QRectF(final_x, pdf_y, final_w, pdf_h)
        except (ValueError, ZeroDivisionError, TypeError) as e:
            print(f"[WARN] _calculate_from_line 错误: {e}")
            return None

    def run(self):
        """执行 OCR 扫描

        v37.0.6: 重构信号发送顺序，确保资源清理后再发送信号
        v37.0.5: 增强异常处理
        v36.4: 使用信号槽机制替代共享字典
        """
        error_msg = None
        doc = None
        try:
            # v37.4.0: 直接使用 RapidOCR
            from privacyguard.ocr.rapidocr import RapidOCREngine
            ocr_engine = RapidOCREngine()

            if not ocr_engine.is_available():
                error_msg = "RapidOCR 引擎不可用，请检查依赖安装"
                print(f"[OCR ERROR] {error_msg}")
                return

            print(f"[OCR] 使用引擎: {ocr_engine.name}")

            doc = fitz.open(self.pdf_path)
            total = len(doc)
            SCAN_SCALE = self.scan_scale
            last_emit_time = 0

            batch_size = 10

            for batch_start in range(0, total, batch_size):
                if self.isInterruptionRequested():
                    break

                batch_end = min(batch_start + batch_size, total)

                for i in range(batch_start, batch_end):
                    if self.isInterruptionRequested():
                        break

                    page = doc[i]
                    rects = []
                    all_patterns = self.rules + self.custom_keywords

                    page_text = page.get_text()
                    page_dict = page.get_text("dict")
                    image_clip_rects = collect_embedded_image_clip_rects(page_dict)

                    if page_text.strip():
                        hit_boxes = collect_text_pdf_hit_boxes(page, all_patterns, page_text=page_text)
                        rects.extend(QRectF(x, y, w, h) for x, y, w, h in hit_boxes)

                    if not image_clip_rects and not page_text.strip():
                        image_clip_rects = [(page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1)]

                    image_hit_count = 0
                    if image_clip_rects:
                        image_hit_rects = collect_image_block_ocr_hits(
                            page,
                            all_patterns,
                            SCAN_SCALE,
                            recognize_fn=lambda scan_img: ocr_engine.recognize(scan_img),
                            calculate_rect_fn=lambda box, text, span, scan_img: self.calculate_sub_rect(
                                box,
                                text,
                                span,
                                img_region=scan_img,
                            ),
                            clip_to_page_rect_fn=lambda local_rect, clip_rect: QRectF(
                                local_rect.x() + clip_rect[0],
                                local_rect.y() + clip_rect[1],
                                local_rect.width(),
                                local_rect.height(),
                            ),
                            preprocess_fn=self.preprocess_image if self.use_enhance else None,
                            page_dict=page_dict,
                            image_clip_rects=image_clip_rects,
                        )
                        rects.extend(image_hit_rects)
                        image_hit_count = len(image_hit_rects)

                    if image_clip_rects or (page_text.strip() and rects):
                        print(
                            f"[OCR] 页面 {i}: 文本命中 {len(rects) - image_hit_count}, "
                            f"图片块 {len(image_clip_rects)}, 图片OCR命中 {image_hit_count}"
                        )

                    # v37.5.0: 印章检测
                    if self.seal_detection_enabled and "__SEAL_DETECTION__" in self.rules:
                        try:
                            pix = page.get_pixmap(matrix=fitz.Matrix(SCAN_SCALE, SCAN_SCALE))
                            img_data = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
                            img_np = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                            scan_img = self.preprocess_image(img_np) if self.use_enhance else img_np
                            seal_rects = self._detect_seals(scan_img, SCAN_SCALE)
                            rects.extend(seal_rects)
                            if seal_rects:
                                print(f"[Seal Detection] 页面 {i} 检测到 {len(seal_rects)} 个印章")
                        except Exception as e:
                            print(f"[Seal Detection] 页面 {i} 检测失败: {type(e).__name__}: {e}")

                    # 逐页发送结果
                    self.page_result_signal.emit(i, rects)

                    # 背压控制
                    current_progress = int((i+1)/total * 100)
                    current_time = time.time()
                    if current_time - last_emit_time > PROGRESS_UPDATE_INTERVAL or i == total - 1:
                        self.progress_signal.emit(current_progress)
                        last_emit_time = current_time

                if self.isInterruptionRequested():
                    break

                # 批次间垃圾回收
                if batch_end < total:
                    gc.collect()

        except Exception as e:
            error_msg = f"OCR 处理错误: {type(e).__name__}: {e}"
            print(f"[OCR ERROR] {error_msg}")
            traceback.print_exc()
        finally:
            if doc:
                doc.close()

        # 资源清理后发送信号
        if error_msg:
            self.error_signal.emit(error_msg)
        self.finished_signal.emit({})
