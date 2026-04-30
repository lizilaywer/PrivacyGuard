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
import re

from privacyguard.ocr.mixed_pdf import (
    collect_embedded_image_clip_rects,
    collect_image_block_ocr_hits,
)
from privacyguard.ocr.text_pdf import collect_text_pdf_hit_boxes

# 常量定义
PROGRESS_UPDATE_INTERVAL = 0.05


def create_rapidocr_engine():
    """延迟初始化 RapidOCR，避免模块导入阶段因依赖缺失崩溃。"""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError(f"RapidOCR 未安装: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"RapidOCR 动态库加载失败: {exc}") from exc
    return RapidOCR()


def create_rapidocr_results(engine, image):
    """统一 RapidOCR 原始结果结构，便于复用混合页辅助逻辑。"""
    result, _ = engine(image)
    return result or []


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
                    all_patterns = self.rules + self.custom_keywords

                    page_text = page.get_text()
                    page_dict = page.get_text("dict")
                    image_clip_rects = collect_embedded_image_clip_rects(page_dict)

                    if page_text.strip():
                        hit_boxes = collect_text_pdf_hit_boxes(page, all_patterns, page_text=page_text)
                        rects.extend(QRectF(x, y, w, h) for x, y, w, h in hit_boxes)

                    if not image_clip_rects and not page_text.strip():
                        image_clip_rects = [(page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1)]

                    if image_clip_rects:
                        if ocr_engine is None:
                            ocr_engine = create_rapidocr_engine()

                        image_hit_rects = collect_image_block_ocr_hits(
                            page,
                            all_patterns,
                            SCAN_SCALE,
                            recognize_fn=lambda scan_img: create_rapidocr_results(ocr_engine, scan_img),
                            calculate_rect_fn=lambda box, text, span, _scan_img: self.calculate_sub_rect(
                                box,
                                text,
                                span,
                            ),
                            clip_to_page_rect_fn=lambda local_rect, clip_rect: QRectF(
                                local_rect.x() / SCAN_SCALE + clip_rect[0],
                                local_rect.y() / SCAN_SCALE + clip_rect[1],
                                local_rect.width() / SCAN_SCALE,
                                local_rect.height() / SCAN_SCALE,
                            ),
                            preprocess_fn=self.preprocess_image if self.use_enhance else None,
                            page_dict=page_dict,
                            image_clip_rects=image_clip_rects,
                        )
                        rects.extend(image_hit_rects)

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
