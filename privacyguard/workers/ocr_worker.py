"""
OCR 处理 Worker

v36.5: 模块化拆分，从 main.py 提取
"""

import time
import gc
import numpy as np
import cv2
import fitz
from PyQt6.QtCore import QThread, pyqtSignal, QRectF
from rapidocr_onnxruntime import RapidOCR
import re

# 常量定义
PROGRESS_UPDATE_INTERVAL = 0.05


class OCRWorker(QThread):
    """OCR 处理线程（保持 v13 的防崩核心）

    v36.4: 使用信号槽机制替代共享字典，解决线程安全问题
    v36.5: 模块化拆分
    """
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int)
    page_result_signal = pyqtSignal(int, list)  # v36.4: 线程安全 - 逐页发送结果 (页码, 矩形列表)

    def __init__(self, pdf_path, rules, use_enhance, custom_keywords, scan_scale, off_x, off_w):
        super().__init__()
        # 不再加载整个文件到内存，只保存路径（v24 内存优化）
        self.pdf_path = pdf_path
        self.rules = rules
        self.use_enhance = use_enhance
        raw_keywords = custom_keywords.replace('\n', ' ').split()
        self.custom_keywords = [re.escape(k.strip()) for k in raw_keywords if k.strip()]
        self.scan_scale = scan_scale
        self.off_x = off_x
        self.off_w = off_w

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

    def calculate_sub_rect(self, box, text, match_span):
        """计算子矩形区域"""
        try:
            line_x_min = min([p[0] for p in box])
            line_x_max = max([p[0] for p in box])
            line_y_min = min([p[1] for p in box])
            line_y_max = max([p[1] for p in box])

            if len(text) == 0 or line_x_max <= line_x_min:
                return None
            avg_char_width = (line_x_max - line_x_min) / len(text)
            start_idx, end_idx = match_span

            sub_x = line_x_min + (start_idx * avg_char_width)
            sub_w = (end_idx - start_idx) * avg_char_width

            final_x = sub_x - self.off_x * self.scan_scale
            final_w = sub_w - self.off_w * self.scan_scale

            return QRectF(final_x, line_y_min, final_w, (line_y_max - line_y_min))
        except (ValueError, ZeroDivisionError, TypeError):
            return None

    def run(self):
        """执行 OCR 扫描"""
        doc = None
        try:
            doc = fitz.open(self.pdf_path)
            ocr_engine = None
            total = len(doc)
            SCAN_SCALE = self.scan_scale
            last_emit_time = 0

            # 分批处理：每 10 页一批，批次间释放资源（v24 批处理优化）
            batch_size = 10

            for batch_start in range(0, total, batch_size):
                if self.isInterruptionRequested():
                    break  # 退出循环，但保留已扫描结果

                batch_end = min(batch_start + batch_size, total)

                for i in range(batch_start, batch_end):
                    if self.isInterruptionRequested():
                        break  # 退出循环，但保留已扫描结果

                    page = doc[i]
                    rects = []

                    page_text = page.get_text()
                    is_text_pdf = len(page_text.strip()) > 20

                    if is_text_pdf:
                        all_patterns = self.rules + self.custom_keywords
                        for pat in all_patterns:
                            for match in re.finditer(pat, page_text, re.IGNORECASE):
                                found_str = match.group()
                                try:
                                    hits = page.search_for(found_str)
                                    if hits:
                                        for h in hits:
                                            safe_rect = QRectF(h.x0, h.y0, h.width, h.height)
                                            rects.append(safe_rect)
                                except RuntimeError as e:
                                    print(f"搜索文本错误: {e}")
                                    pass
                    else:
                        if ocr_engine is None:
                            ocr_engine = RapidOCR()

                        pix = page.get_pixmap(matrix=fitz.Matrix(SCAN_SCALE, SCAN_SCALE))
                        img_data = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
                        img_np = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

                        scan_img = self.preprocess_image(img_np) if self.use_enhance else img_np
                        ocr_result, _ = ocr_engine(scan_img)

                        if ocr_result:
                            for line in ocr_result:
                                box, text = line[0], line[1]
                                all_patterns = self.rules + self.custom_keywords
                                for pat in all_patterns:
                                    for match in re.finditer(pat, text, re.IGNORECASE):
                                        sub_rect = self.calculate_sub_rect(box, text, match.span())
                                        if sub_rect:
                                            rects.append(QRectF(
                                                sub_rect.x()/SCAN_SCALE,
                                                sub_rect.y()/SCAN_SCALE,
                                                sub_rect.width()/SCAN_SCALE,
                                                sub_rect.height()/SCAN_SCALE
                                            ))

                    # v36.4: 通过信号发送单页结果（线程安全）
                    self.page_result_signal.emit(i, rects)

                    # 背压控制 (防止 UI 线程崩溃)
                    current_progress = int((i+1)/total * 100)
                    current_time = time.time()
                    if current_time - last_emit_time > PROGRESS_UPDATE_INTERVAL or i == total - 1:
                        self.progress_signal.emit(current_progress)
                        last_emit_time = current_time

                # 批次间检查中断
                if self.isInterruptionRequested():
                    break  # 退出循环，但保留已扫描结果

                # 批次间清理：释放 OCR 引擎资源（v24 内存优化）
                if ocr_engine and batch_end < total:
                    del ocr_engine
                    ocr_engine = None
                    gc.collect()

            # v36.4: 发射空字典作为完成信号，实际结果已通过 page_result_signal 发送
            self.finished_signal.emit({})

        except (IOError, OSError, RuntimeError, ValueError) as e:
            print(f"OCR处理错误: {e}")
            self.finished_signal.emit({})
        finally:
            if doc:
                doc.close()
