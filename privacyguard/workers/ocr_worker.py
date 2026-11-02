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
from privacyguard.ocr.text_pdf import collect_text_pdf_hit_boxes, apply_box_adjust_to_hit
# v37.8.11 P1-2: 印章/签名检测算法外提到 ocr/ 模块
from privacyguard.ocr.seal_detection import (
    detect_seals as _detect_seals_impl,
    detect_star_in_roi as _detect_star_in_roi_impl,
    ocr_seal_region as _ocr_seal_region_impl,
)
from privacyguard.ocr.signature_detection import detect_signatures as _detect_signatures_impl
from privacyguard.utils.logger import get_logger
from privacyguard.utils.exceptions import OCRInspectionError

logger = get_logger("ocr_worker")

# 常量定义
PROGRESS_UPDATE_INTERVAL = 0.05

# v37.8.11 P1-2: SEAL_KEYWORDS / SEAL_CHAR_KEYWORDS 已外提至
# privacyguard.ocr.seal_detection，此处通过 import 引入保持向后兼容


class OCREngineUnavailableError(RuntimeError):
    """OCR 引擎不可用（依赖缺失/初始化失败）。"""


def _rects_iou(a, b):
    """两个 QRectF 的交并比（无交集返回 0.0）。"""
    try:
        inter = a.intersected(b)
        if inter is None or inter.isEmpty():
            return 0.0
        inter_area = inter.width() * inter.height()
        union = a.width() * a.height() + b.width() * b.height() - inter_area
        if union <= 0:
            return 0.0
        return inter_area / union
    except Exception:
        return 0.0


def dedup_page_rects(rects, iou_threshold=0.5):
    """P2 跨源去重：合并页内重叠命中（文本层 vs 图块 OCR vs 印章/签名）。

    混合 PDF 中同一段敏感文字可能同时被文本层 search_for 和图片块 OCR 命中，
    产生重叠遮罩 + 报告计数虚高。按 IoU >= iou_threshold 抑制后到者，保留插入序
    （文本层命中通常先入），不改变非重复命中的相对顺序。
    """
    if len(rects) <= 1:
        return rects
    kept = []
    kept_rects = []
    for r in rects:
        rc = r.get('rect') if isinstance(r, dict) else None
        if rc is None:
            kept.append(r)
            continue
        dup = False
        for kr in kept_rects:
            if _rects_iou(rc, kr) >= iou_threshold:
                dup = True
                break
        if not dup:
            kept.append(r)
            kept_rects.append(rc)
    return kept


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
                 box_adjust_ratio: float = 0.0,
                 custom_keyword_rules: list = None,
                 signature_detection_enabled: bool = False,
                 rule_name_pairs: list = None,
                 pdf_open_password: str = "",
                 parent=None, pdf_bytes=None):
        # v40.1.4 修复：补 parent 形参——main.py 兼容包装器自 cp132 起向 super()
        # 传 parent=，此前模块层无此形参导致智能扫描/全文遮罩构造即 TypeError
        #（用户真机框选全文遮罩触发暴露的潜伏 Bug）。
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.pdf_bytes = pdf_bytes
        # cp114: 加密 PDF 重读认证密码（与导出加密设置解耦，由 MainWindow._pdf_auth_password 传入）
        self.pdf_open_password = pdf_open_password or ""
        # cp57: None 防御，避免 config 损坏时崩溃
        self.rules = list(rules) if rules else []
        self.use_enhance = use_enhance
        raw_keywords = (custom_keywords or "").replace('\n', ' ').split()
        self.custom_keywords = [re.escape(k.strip()) for k in raw_keywords if k.strip()]
        # cp87: 规则名反查表 [(规则名, pattern)]，命中项携带 'rule' 供脱敏报告分类
        self.rule_name_pairs = list(rule_name_pairs) if rule_name_pairs else []
        self._raw_custom_keywords = [k.strip() for k in raw_keywords if k.strip()]
        # v37.7.13 cp43: 构建查找→替换映射（用于命中后携带 replace_text）
        self.keyword_replace_map = {}
        if custom_keyword_rules:
            for rule in custom_keyword_rules:
                if not isinstance(rule, dict):
                    continue
                if rule.get("enabled", True) and rule.get("find"):
                    self.keyword_replace_map[rule["find"]] = rule.get("replace", "")
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
        # cp60: 签名手印检测功能
        self.signature_detection_enabled = signature_detection_enabled

    def _classify_rule(self, matched_text):
        """cp87: 命中文本反查规则名（供脱敏报告分类）。"""
        from privacyguard.report import classify_hit_rule
        return classify_hit_rule(matched_text, self.rule_name_pairs,
                                 self._raw_custom_keywords)

    def _lookup_replace(self, matched_text):
        """v37.7.13 cp43: 在 keyword_replace_map 中查找替换文本。

        匹配优先级：精确匹配 > 子串包含（find 是 matched_text 的子串）。
        未匹配返回空字符串（纯遮罩）。
        """
        if not matched_text or not self.keyword_replace_map:
            return ""
        # 精确匹配
        if matched_text in self.keyword_replace_map:
            return self.keyword_replace_map[matched_text]
        # 子串包含：matched_text 包含某个 find 关键词
        # cp118 修复：按 len(find_kw) 降序迭代，长词优先。
        # 否则按 dict 插入序，短词（如"张三"）会先于长词（如"张三丰"）命中，
        # 导致 matched_text="张三丰的事" 错误返回短词的替换词。
        for find_kw, replace_text in sorted(self.keyword_replace_map.items(),
                                            key=lambda kv: len(kv[0]), reverse=True):
            if find_kw in matched_text:
                return replace_text
        return ""

    def preprocess_image(self, img_np):
        """图像预处理"""
        try:
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = np.ones((2, 2), np.uint8)
            enhanced = cv2.erode(binary, kernel, iterations=1)
            return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        except cv2.error as e:
            logger.warning("图像处理错误: %s", e)
            return img_np

    def _make_block_failure_fn(self, page_rect):
        """v37.7.18 cp53: 创建整块覆盖回调，限制覆盖面积。

        大面积无法检视时中止扫描，既不误遮整页，也不伪装成成功零命中。

        Args:
            page_rect: fitz.Page 对象的 rect 属性

        Returns:
            callable: on_block_failure_fn(clip_rect) -> QRectF | None
        """
        page_area = (page_rect.x1 - page_rect.x0) * (page_rect.y1 - page_rect.y0)
        max_cover_ratio = 0.30  # 超过页面面积 30% 不覆盖

        def on_block_failure_fn(clip_rect):
            clip_w = clip_rect[2] - clip_rect[0]
            clip_h = clip_rect[3] - clip_rect[1]
            clip_area = clip_w * clip_h
            if page_area > 0 and clip_area / page_area > max_cover_ratio:
                logger.warning("[OCR WARN] 图片块面积 %.0f > 页面 %.0f 的 %.0f%%，中止不完整扫描",
                               clip_area, page_area, max_cover_ratio * 100)
                raise OCRInspectionError("大面积图片无法检视，扫描已中止；请检查该页后重试")
            return QRectF(clip_rect[0], clip_rect[1], clip_w, clip_h)

        return on_block_failure_fn

    def _detect_star_in_roi(self, roi_mask):
        """v37.8.11 P1-2: thin wrapper -> privacyguard.ocr.seal_detection."""
        return _detect_star_in_roi_impl(roi_mask)

    def _ocr_seal_region(self, roi_img, ocr_engine):
        """v37.8.11 P1-2: thin wrapper -> privacyguard.ocr.seal_detection."""
        return _ocr_seal_region_impl(roi_img, ocr_engine)

    def _detect_seals(self, img_np, scan_scale, ocr_engine=None, page_origin=(0.0, 0.0),
                      ring_close_px=None):
        """v37.8.11 P1-2: thin wrapper -> privacyguard.ocr.seal_detection.

        Preserved for test compatibility (test_seal_detection.py binds via
        types.MethodType). Algorithm in privacyguard/ocr/seal_detection.py.
        """
        return _detect_seals_impl(img_np, scan_scale, ocr_engine=ocr_engine,
                                  page_origin=page_origin, ring_close_px=ring_close_px)

    def _detect_signatures(self, img_np, scan_scale, page_origin=(0.0, 0.0)):
        """v37.8.11 P1-2: thin wrapper -> privacyguard.ocr.signature_detection.

        Preserved for test compatibility (test_signature_detection.py binds via
        types.MethodType). Algorithm in privacyguard/ocr/signature_detection.py.
        """
        return _detect_signatures_impl(img_np, scan_scale, page_origin=page_origin)

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
            # v37.7.8 cp34 R3: 阈值从 0.05 调到 0.15，避免把抗锯齿边缘/噪点也算文字列
            # v37.7.8 cp35 F5: 阈值自适应（基于对比度）
            #   - 高对比度扫描件（白底黑字 mean>200）：用 0.20，更严格地排除抗锯齿
            #   - 低对比度扫描件（mean<=200）：用 0.12，避免漏掉淡字符
            # v37.7.8 cp36 F11: 阈值更严格，高对比度 mean>220 用 0.30 排除抗锯齿边缘
            # v37.7.8 cp36 F14: use_enhance=True 时预处理已二值化（mean 接近 0/255），
            #   跳过 F5 自适应，用固定 0.20
            mean_val = float(np.mean(gray))
            is_binary = mean_val < 10 or mean_val > 245
            if is_binary:
                # 已二值化图像（use_enhance=True 预处理后），用固定 0.20
                threshold_ratio = 0.20
            elif mean_val > 220:
                # v37.7.15 cp45: 高对比度扫描件改用 0.20（原 0.30）
                # 0.30 过严格会把抗锯齿边缘当作文字列边界，导致 line_x_min 偏内
                # 整个 sub_rect 向右偏移，最终遮罩左露字
                threshold_ratio = 0.20
            elif mean_val > 200:
                # 中等对比度，用 0.20
                threshold_ratio = 0.20
            else:
                # 低对比度，用 0.12 避免漏掉淡字符
                threshold_ratio = 0.12
            threshold = max(2, binary.shape[0] * threshold_ratio)
            text_cols = np.where(h_projection > threshold)[0]

            if len(text_cols) == 0:
                return int(min(x_coords)), int(max(x_coords))

            actual_left = x_min + text_cols[0]
            actual_right = x_min + text_cols[-1]

            return actual_left, actual_right

        except Exception as e:
            logger.debug("[DEBUG] _detect_text_boundaries 错误: %s", e)
            x_coords = [p[0] for p in box]
            return int(min(x_coords)), int(max(x_coords))

    def _detect_vertical_boundaries(self, img_region, box):
        """v37.7.8 cp34 R2: y 方向像素边界检测

        避免因 OCR box y 范围过大把相邻行算进水平投影导致整行宽度被高估。

        Args:
            img_region: 扫描图像（BGR）
            box: OCR 检测框

        Returns:
            (actual_top, actual_bottom): 实际文字上下边界（扫描像素空间）
        """
        try:
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            x_min = int(max(0, min(x_coords)))
            x_max = int(min(img_region.shape[1], max(x_coords)))
            y_min = int(max(0, min(y_coords)))
            y_max = int(min(img_region.shape[0], max(y_coords)))

            if x_max <= x_min or y_max <= y_min:
                return int(min(y_coords)), int(max(y_coords))

            roi = img_region[y_min:y_max, x_min:x_max]
            if roi.size == 0:
                return int(min(y_coords)), int(max(y_coords))

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # 水平投影：按行求和黑色像素
            row_sum = np.sum(binary > 0, axis=1)
            row_threshold = max(2, binary.shape[1] * 0.15)

            text_rows = np.where(row_sum > row_threshold)[0]
            if len(text_rows) == 0:
                return int(min(y_coords)), int(max(y_coords))

            # v37.7.9 cp37 F18: 跨多行 box 切单行
            # 原 code 直接返回 [text_rows[0], text_rows[-1]],跨 2 行 box 时返回覆盖 2 行的整体范围
            # 改进:按行间断裂(连续 text_rows 间隔 >3px)切分为多个 row 段,取最接近 box 中心的那一段
            if len(text_rows) > 1:
                row_segments = []  # [(start_row, end_row)]
                seg_start = text_rows[0]
                prev = text_rows[0]
                for r in text_rows[1:]:
                    if r - prev > 3:  # 行间断裂 >3px 视为分界
                        row_segments.append((seg_start, prev))
                        seg_start = r
                    prev = r
                row_segments.append((seg_start, prev))

                if len(row_segments) > 1:
                    # 取最接近 box 中心的那一段
                    box_center_y = (y_min + y_max) // 2
                    best_seg = min(row_segments,
                                    key=lambda s: abs((s[0] + s[1]) // 2 - box_center_y))
                    return y_min + best_seg[0], y_min + best_seg[1] + 1

            return y_min + text_rows[0], y_min + text_rows[-1] + 1
        except Exception as e:
            logger.debug("[DEBUG] _detect_vertical_boundaries 错误: %s", e)
            y_coords = [p[1] for p in box]
            return int(min(y_coords)), int(max(y_coords))

    def _segment_text_columns(self, img_region, box):
        """v37.7.8 cp34 R1: 像素级字符切分

        在 OCR box 范围内做垂直投影找字符间隙，把整行切成字符块。
        用于精确估算子字符串在行内的 x 位置，替代字符权重比例估算。

        Args:
            img_region: 扫描图像（BGR）
            box: OCR 检测框（4 角点）

        Returns:
            list[tuple[int, int]]: 每个字符块的 (left, right) 像素坐标（扫描空间）；
                                   空列表表示切分失败
        """
        try:
            x_coords = [p[0] for p in box]
            x_min = int(max(0, min(x_coords)))
            x_max = int(min(img_region.shape[1], max(x_coords)))
            # v37.7.9 cp37 F17: 先用 _detect_vertical_boundaries 收紧 y 范围
            # 原代码直接用 box 角点 y_coords,跨行 box 会导致 col_sum 叠加、gap 被误判为文字列
            # 收紧后只对单行做垂直投影,段切分准确
            y_tight_min, y_tight_max = self._detect_vertical_boundaries(img_region, box)
            y_min = int(max(0, y_tight_min))
            y_max = int(min(img_region.shape[0], y_tight_max))

            if x_max <= x_min or y_max <= y_min:
                return []

            roi = img_region[y_min:y_max, x_min:x_max]
            if roi.size == 0:
                return []

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # 形态学闭运算：水平方向连接同一字符的笔画（避免笔画内部有洞被误切）
            # v37.7.8 cp35 F2: 核宽改用字符高度（与字号挂钩，比行宽更稳定）
            char_h = binary.shape[0]
            kernel_w = max(1, int(char_h / 6))
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1))
            closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            # 垂直投影：按列求和黑色像素
            col_sum = np.sum(closed > 0, axis=0)

            # 阈值：列内至少有一定比例的行有黑色像素，才算"文字列"
            col_threshold = max(2, binary.shape[0] * 0.15)

            # v37.7.8 cp36 F8: 自适应间隙检测
            # 先用宽松 gap_tolerance=2 做一次预切分，统计段间间隙宽度
            pre_segments = self._segment_with_tolerance(
                col_sum, col_threshold, gap_tolerance=2,
                x_min=x_min, x_max=x_max,
                min_seg_width=max(2, int(char_h / 8))
            )
            if len(pre_segments) >= 2:
                gaps = [pre_segments[i + 1][0] - pre_segments[i][1]
                        for i in range(len(pre_segments) - 1)]
                if gaps:
                    median_gap = sorted(gaps)[len(gaps) // 2]
                    # 自适应 gap_tolerance：中位数间隙的 1.5 倍，但不超过 char_h/3
                    # v37.7.9 cp38 F20-redesign: 加 median_gap * 0.8 上限
                    # 原代码 gap_tolerance = max(2, min(median_gap*1.5, char_h/3))
                    # 当 char_h/3 > gap 时(如 char_h=40,gap=10,char_h/3=13 > 10)
                    # 正式切分把 gap 当短间隙不切断,段切分失败
                    # 修复:gap_tolerance 不超过 median_gap * 0.8,确保 gap > gap_tolerance 能切断
                    gap_tolerance = max(2, min(int(median_gap * 1.5),
                                                 int(char_h / 3),
                                                 int(median_gap * 0.8)))
                else:
                    gap_tolerance = max(2, int(char_h / 3))
            else:
                gap_tolerance = max(2, int(char_h / 3))

            # 用自适应 gap_tolerance 做正式切分
            # v37.7.8 cp35 F2: 最小段宽用字符高度（约 1/4 字高）
            min_seg_width = max(2, int(char_h / 4))
            segments = self._segment_with_tolerance(
                col_sum, col_threshold, gap_tolerance=gap_tolerance,
                x_min=x_min, x_max=x_max,
                min_seg_width=min_seg_width
            )

            # v37.7.8 cp35 F3: 超宽段二次切分（处理 CJK 字符粘连）
            if len(segments) >= 2:
                widths = [r - l for l, r in segments]
                median_w = sorted(widths)[len(widths) // 2]
                refined = []
                for l, r in segments:
                    if (r - l) > median_w * 1.5:
                        sub_segs = self._split_wide_segment(img_region, l, r, y_min, y_max, char_h)
                        if sub_segs:
                            refined.extend(sub_segs)
                        else:
                            refined.append((l, r))
                    else:
                        refined.append((l, r))
                segments = refined

            return segments
        except Exception as e:
            logger.debug("[DEBUG] _segment_text_columns 错误: %s", e)
            return []

    def _segment_with_tolerance(self, col_sum, col_threshold, gap_tolerance,
                                  x_min, x_max, min_seg_width):
        """v37.7.8 cp36 F8: 用指定 gap_tolerance 切分字符段

        把切分循环抽成独立方法，便于 _segment_text_columns 多次切分复用。

        Args:
            col_sum: 列投影数组（np.ndarray）
            col_threshold: 列阈值（int）
            gap_tolerance: 间隙容忍宽度（int）- 小于此宽度的间隙不切断段
            x_min: ROI 左边界（图像像素空间，用于坐标偏移）
            x_max: ROI 右边界
            min_seg_width: 最小段宽（过滤过窄段）

        Returns:
            list[tuple[int, int]]: 切分出的段列表 (left, right) 像素坐标
        """
        segments = []
        in_seg = False
        seg_start = 0
        for i, v in enumerate(col_sum):
            if v > col_threshold:
                if not in_seg:
                    seg_start = i
                    in_seg = True
            else:
                if in_seg:
                    # 检查是否是短间隙还是真的段结束
                    look_ahead = col_sum[i:i + gap_tolerance]
                    if np.any(look_ahead > col_threshold):
                        # 间隙太短，继续当前段
                        continue
                    segments.append((x_min + seg_start, x_min + i))
                    in_seg = False

        # 收尾
        if in_seg:
            segments.append((x_min + seg_start, x_max))

        # 过滤过窄段
        segments = [(l, r) for l, r in segments if r - l >= min_seg_width]
        return segments

    def _split_wide_segment(self, img_region, seg_left, seg_right, y_min, y_max, char_h):
        """v37.7.8 cp35 F3: 超宽段二次切分

        在已识别的超宽段内做更细的垂直投影分析，找出密度低谷并切分。
        用于处理 CJK 字符粘连（多个字符贴在一起被识别为一个段）的情况。

        Args:
            img_region: 扫描图像（BGR）
            seg_left, seg_right: 段的左右像素坐标
            y_min, y_max: 段的上下像素坐标
            char_h: 字符高度（用于确定阈值）

        Returns:
            list[tuple[int, int]]: 切分后的子段列表；空列表表示无法切分
        """
        try:
            if seg_right <= seg_left or y_max <= y_min:
                return []
            roi = img_region[y_min:y_max, seg_left:seg_right]
            if roi.size == 0:
                return []

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            col_sum = np.sum(binary > 0, axis=0)
            # 用更低的阈值找密度低谷
            col_threshold = max(2, binary.shape[0] * 0.08)

            sub_segs = []
            in_seg = False
            seg_start = 0
            gap_tolerance = max(2, int(char_h / 4))

            for i, v in enumerate(col_sum):
                if v > col_threshold:
                    if not in_seg:
                        seg_start = i
                        in_seg = True
                else:
                    if in_seg:
                        look_ahead = col_sum[i:i + gap_tolerance]
                        if np.any(look_ahead > col_threshold):
                            continue
                        sub_segs.append((seg_left + seg_start, seg_left + i))
                        in_seg = False

            if in_seg:
                sub_segs.append((seg_left + seg_start, seg_right))

            # 过滤过窄的子段
            min_sub_w = max(2, int(char_h / 4))
            sub_segs = [(l, r) for l, r in sub_segs if r - l >= min_sub_w]

            # 必须切出 ≥2 段才有意义
            if len(sub_segs) < 2:
                # v37.7.8 cp36 F9: 等分回退策略
                # 当密度低谷切分失败（整段均匀粘连），按段宽 / 估算单字符宽 等分
                # 估算单字符宽 = char_h * 0.9（CJK 标准字宽约为字高的 0.9 倍）
                est_char_w = max(2, int(char_h * 0.9))
                seg_w = seg_right - seg_left
                n_chars = max(2, round(seg_w / est_char_w))
                if n_chars >= 2 and seg_w / n_chars >= max(2, int(char_h / 4)):
                    sub_w = seg_w / n_chars
                    return [(int(seg_left + i * sub_w), int(seg_left + (i + 1) * sub_w))
                            for i in range(n_chars)]
                return []
            return sub_segs
        except Exception as e:
            logger.debug("[DEBUG] _split_wide_segment 错误: %s", e)
            return []

    def _extract_roi_2x(self, img_region, box):
        """v37.7.9 cp38 F20-redesign + F23: 提取 ROI(外扩 8px,不放大)

        历史方案演进:
        - cp37 F20: ROI 2x 放大(INTER_CUBIC) → 抗锯齿填充 gap,段切分失败
        - cp38 F20-fix 尝试: INTER_NEAREST + 二值化 → 段切分恢复,但 char_h 翻倍
          导致 gap_tolerance 跟着放大,v3 测试 test_equal_split / test_b_tier_end_index
          等多个失败
        - cp38 F20-redesign (最终方案): 放弃 2x 放大,只做 F23 外扩 8px。
          理由: 段切分准确后走 A 档直接取段,sub_x 误差 = ±0.5px = ±0.33pt,
          与放大方案精度相同,但不破坏 char_h 依赖的所有逻辑。

        F23 (cp38): ROI 边界外扩 8px,让 _segment_text_columns 能看到完整字符块
            (RapidOCR box 本身有 ±2-5px 偏差,字符可能略超 box 边界)

        Args:
            img_region: 扫描图像(BGR)
            box: OCR 检测框(4 角点,基于 img_region 像素坐标)

        Returns:
            (roi, scale_factor, offset_x, offset_y):
                - roi: 外扩后的 ROI 图像(失败返回 None)
                - scale_factor: 固定 1.0(不放大)
                - offset_x, offset_y: ROI 在原图中的左上角偏移(原图像素坐标)
        """
        try:
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            # v37.7.9 cp38 F23: ROI 边界外扩 8px,容纳 OCR box 偏差
            EXPAND_PX = 8
            x_min = int(max(0, min(x_coords) - EXPAND_PX))
            x_max = int(min(img_region.shape[1], max(x_coords) + EXPAND_PX))
            y_min = int(max(0, min(y_coords) - EXPAND_PX))
            y_max = int(min(img_region.shape[0], max(y_coords) + EXPAND_PX))
            if x_max <= x_min or y_max <= y_min:
                return None, 1.0, 0, 0
            roi = img_region[y_min:y_max, x_min:x_max]
            if roi.size == 0:
                return None, 1.0, 0, 0
            # v37.7.9 cp38 F20-redesign: 不放大,直接返回 ROI
            return roi, 1.0, x_min, y_min
        except Exception as e:
            logger.debug("[DEBUG] _extract_roi_2x 错误: %s", e)
            return None, 1.0, 0, 0

    def calculate_sub_rect(self, box, text, match_span, img_region=None):
        """v37.4.0: 计算子字符串的矩形区域（行级计算 + 像素边界检测）

        v37.7.18 cp54: 新增 OCR box 宽度限制，避免跨整页的大框产生超大遮罩

        Args:
            box: 整行文本的检测框
            text: 整行文本
            match_span: 匹配位置 (start_idx, end_idx)
            img_region: 扫描图像区域，用于像素边界检测

        Returns:
            QRectF: 子字符串矩形区域（PDF坐标系）
        """
        try:
            # cp54: 限制 OCR box 宽度，避免跨整页的大框产生超大遮罩
            # 当 OCR 返回整页大框时，line_x_min/line_x_max 跨整页，
            # 即使只匹配几个字符，权重估算也会产生接近整行宽度的 sub_w
            if img_region is not None:
                img_w = img_region.shape[1]
                x_coords = [p[0] for p in box]
                box_w = max(x_coords) - min(x_coords)
                if box_w > img_w * 0.8:
                    # cp118 修复：超宽 box 不再静默返回 None（调用方 continue 会漏脱敏，
                    # 对脱敏工具而言漏脱 = 泄漏）。改为回退纯权重估算（img_region=None），
                    # 产出受限宽度的有界 rect，既避免跨整页超大遮罩，又不丢失敏感文字遮罩。
                    logger.warning("[cp118] OCR box 宽度 %.1fpx 超过图像 %.1fpx 的 80%%, 回退纯权重估算",
                                   box_w, img_w)
                    start_idx, end_idx = match_span
                    return self._calculate_from_line(box, text, start_idx, end_idx, img_region=None)

            start_idx, end_idx = match_span
            return self._calculate_from_line(box, text, start_idx, end_idx, img_region=img_region)
        except (ValueError, ZeroDivisionError, TypeError) as e:
            logger.warning("[WARN] calculate_sub_rect 错误: %s", e)
            return None

    def _calculate_from_line(self, box, text, start_idx, end_idx, img_region=None):
        """v37.7.8 cp35: 三档混合算法 - 始终利用像素信息

        v37.3.7: 原始权重比例估算（中文 1.0 / 英数 0.55）
        v37.7.8 cp34:
          - R1: 像素级字符切分（_segment_text_columns）
          - R2: y 方向边界检测
          - R4: margin PDF 点空间 0.3pt
          - R5: min 宽度 2.0pt
          - 边界保护
        v37.7.8 cp35 F1:
          - A 档：段数 == 文本长度 → 直接取段（cp34 路径，最精准）
          - B 档：段数差 ≤ max(2, 30%*len) 且 ≥2 段 → 累计权重对齐 + 线性插值
          - C 档：其他 → 用段块收紧 line_width 后做权重估算
          - 关键改进：B/C 档不再丢弃像素信息，避免 bimodal 行为
        v37.7.9 cp37 F20:
          - ROI 内部 2x 放大（等效 scan_scale=3.0）提升像素精度
          - 12pt 汉字原 18px,放大后 36px,sub_x ±1px 误差从 ±0.67pt 减为 ±0.33pt

        Returns:
            QRectF: 子字符串矩形区域（PDF坐标系）
        """
        try:
            # v37.7.9 cp37 F20: ROI 内部 2x 放大
            # 提取 OCR box ROI 区域并放大 2x,所有像素操作在放大版上做,最后转回原 scan_img 坐标
            # 避免提高 scan_scale 默认值(1.5)导致的整页渲染性能爆炸
            scale_factor = 1.0
            offset_x = 0
            offset_y = 0
            if img_region is not None:
                roi_2x, sf, ox, oy = self._extract_roi_2x(img_region, box)
                if roi_2x is not None:
                    # 转 box 到放大 ROI 局部坐标
                    effective_img = roi_2x
                    effective_box = [[(p[0] - ox) * sf, (p[1] - oy) * sf] for p in box]
                    scale_factor = sf
                    offset_x = ox
                    offset_y = oy
                else:
                    effective_img = img_region
                    effective_box = box
            else:
                effective_img = None
                effective_box = box

            # 1. 整行边界（x 方向）
            if effective_img is not None:
                # v37.7.15 cp45: 修复 RapidOCR v3.x 多行合并 box 导致 x 边界跨整页
                # 原代码：先 _detect_text_boundaries 再 _detect_vertical_boundaries
                #   问题：v3.x 把多行文字合并成 1 个 box,_detect_text_boundaries 在多行 ROI 上
                #         做水平投影,多行文字 x 范围合并 → line_x_min/line_x_max 跨整页
                #   修复：先 _detect_vertical_boundaries 切出单行 y,把 effective_box
                #         4 角点 y 钳到单行范围,再做 _detect_text_boundaries。
                #         同时收紧后的 effective_box 也会传给 _segment_text_columns,
                #         确保段切分也在单行 ROI 上做。
                line_y_min, line_y_max = self._detect_vertical_boundaries(effective_img, effective_box)

                # cp45: 用单行 y 钳制 effective_box 4 角点的 y 坐标
                # （所有点 y 取 [line_y_min, line_y_max] 范围,x 保持不变）
                if line_y_max > line_y_min:
                    effective_box = [
                        [p[0], max(line_y_min, min(line_y_max, p[1]))]
                        for p in effective_box
                    ]

                line_x_min, line_x_max = self._detect_text_boundaries(effective_img, effective_box)

                # v37.7.8 cp36 F10: 复活 box_adjust_ratio - 在像素边界检测后做 post-shrink
                if self.box_adjust_ratio != 0.0:
                    line_w = line_x_max - line_x_min
                    line_h = line_y_max - line_y_min
                    x_shrink = line_w * self.box_adjust_ratio / 2
                    y_shrink = line_h * self.box_adjust_ratio * 0.6 / 2  # y 方向收缩系数小一些
                    line_x_min += x_shrink
                    line_x_max -= x_shrink
                    line_y_min += y_shrink
                    line_y_max -= y_shrink
                # v37.7.9 cp37 F20 + cp38 F20-redesign: 像素边界转回原 scan_img 坐标
                # cp38 修复: scale_factor=1.0 但 offset > 0 (F23 外扩) 时也需要转换
                # 原代码 if scale_factor != 1.0 跳过转换,导致 effective_img 局部坐标
                # 未加 offset 就被当成 img_region 全局坐标使用
                line_x_min = line_x_min / scale_factor + offset_x
                line_x_max = line_x_max / scale_factor + offset_x
                line_y_min = line_y_min / scale_factor + offset_y
                line_y_max = line_y_max / scale_factor + offset_y
            else:
                shrunk_box = self._shrink_box(box, x_ratio=self.box_adjust_ratio,
                                               y_ratio=self.box_adjust_ratio * 0.6)
                line_x_min = min([p[0] for p in shrunk_box])
                line_x_max = max([p[0] for p in shrunk_box])
                line_y_min = min([p[1] for p in box])
                line_y_max = max([p[1] for p in box])

            line_width = line_x_max - line_x_min
            if len(text) == 0 or line_width <= 0:
                return None

            # 2. 像素级字符切分
            segments = []
            if effective_img is not None:
                segments = self._segment_text_columns(effective_img, effective_box)
                # v37.7.9 cp37 F20 + cp38 F20-redesign: segments 转回原 scan_img 坐标
                # cp38 修复: 无条件转换(scale_factor=1.0 但 offset > 0 时也需要加 offset)
                segments = [(l / scale_factor + offset_x, r / scale_factor + offset_x)
                             for l, r in segments]

            # 字符权重函数（B/C 档共用）
            def get_char_weight(char):
                if '\u4e00' <= char <= '\u9fff':  # CJK统一汉字
                    return 1.0
                elif '\u3400' <= char <= '\u4dbf':  # CJK扩展A
                    return 1.0
                elif '\uF900' <= char <= '\uFAFF':  # CJK兼容汉字
                    return 1.0
                elif '\u3000' <= char <= '\u303f':  # CJK符号
                    return 1.0
                elif char in '，。；：！？、':
                    return 1.0
                elif char == ' ':
                    return 0.3
                else:
                    return 0.55  # 数字、英文、符号等

            sub_x = None
            sub_w = None

            # A 档：段数 == 文本长度 → 直接取段
            if segments and len(segments) == len(text):
                seg_start = segments[start_idx][0]
                seg_end = segments[end_idx - 1][1]
                sub_x = float(seg_start)
                sub_w = float(seg_end - seg_start)

            # v37.7.16 cp46: 删除 B 档（段数近似但不等时的累计权重 + 线性插值）
            # 原因：段数 != 文本长度时（标点粘连、CJK 拆段等），段到字符的映射无法准确求解，
            #       导致同内容不同页偏移 -5pt 与 -60pt 并存（诊断脚本验证）。
            #       改用 C 档（按字符权重在收紧行宽上线性估算）更稳定，且整体偏移更小。
            #       A 档（段数严格等于文本长度）依然保留，因其精确度最高。

            # C 档：像素收紧权重估算（默认兜底，含原 B 档场景）
            if sub_x is None or sub_w is None or sub_w <= 0:
                refined_line_x_min = line_x_min
                refined_line_width = line_width
                if segments:
                    seg_block_left = min(l for l, r in segments)
                    seg_block_right = max(r for l, r in segments)
                    seg_block_width = seg_block_right - seg_block_left
                    # v37.7.8 cp36 F7: 用 seg_block_width 作为估算的文本宽度
                    # （实际可见文字范围，含段内字符 + 段间间隙）
                    # 避免 avg_seg_width * len(text) 在粘连段时的高估
                    estimated_text_width = seg_block_width
                    refined_line_width = min(line_width, estimated_text_width)
                    # 中心对齐到段块中心，但不能超出原 line_x_min/line_x_max
                    seg_block_center = (seg_block_left + seg_block_right) / 2
                    refined_line_x_min = seg_block_center - refined_line_width / 2
                    if refined_line_x_min < line_x_min:
                        refined_line_x_min = line_x_min
                    if refined_line_x_min + refined_line_width > line_x_max:
                        refined_line_width = line_x_max - refined_line_x_min
                else:
                    # cp54: segments 为空时（无像素切分），限制估算宽度不超过匹配字符的合理范围
                    # 避免 OCR box 过大时权重估算产生跨整行的 sub_w
                    match_char_count = end_idx - start_idx
                    if len(text) > 0:
                        # 匹配字符占整行的比例 × 2（允许适度扩展，但不超过 2 倍）
                        max_w_ratio = min(1.0, match_char_count / len(text) * 2)
                        refined_line_width = line_width * max_w_ratio

                total_weight = sum(get_char_weight(c) for c in text)
                prefix_weight = sum(get_char_weight(c) for c in text[:start_idx])
                match_weight = sum(get_char_weight(c) for c in text[start_idx:end_idx])

                if total_weight <= 0:
                    total_weight = len(text)
                    prefix_weight = start_idx
                    match_weight = end_idx - start_idx

                sub_x = refined_line_x_min + (prefix_weight / total_weight) * refined_line_width
                sub_w = (match_weight / total_weight) * refined_line_width

            # 3. R4 修复：margin 改为 PDF 点空间固定 0.3pt，转回像素空间保持单位一致
            # v37.7.8 cp36 F12: margin 改为双边对称（左右各收缩 margin/2，中心不变）
            # 原代码 sub_x += margin_px 把整个 rect 右移，造成固定向右偏移
            margin_pt = 0.3
            margin_px = margin_pt * self.scan_scale
            half_margin = margin_px / 2
            sub_x += half_margin  # 左边收缩
            # R5 修复：min 宽度从 5 改为 2.0（PDF 点空间等效）
            sub_w = max(2.0 * self.scan_scale, sub_w - margin_px)  # 总宽减 margin_px（左右各 margin/2）

            # 4. 边界保护（新增）：sub_rect 不能超出整行边界
            if sub_x < line_x_min:
                sub_x = line_x_min
            if sub_x + sub_w > line_x_max:
                sub_w = line_x_max - sub_x

            # v37.7.9 cp38 F24: sub_rect 宽度合理性检查
            # 在 margin 和边界保护后、坐标转换前做最后兜底：
            #   - sub_w 过窄（误切单字符）→ 回退权重估算
            #   - sub_w 过宽（退化为整行）→ 用段块宽度收紧
            sub_x, sub_w = self._verify_sub_rect_width(
                sub_x, sub_w, line_x_min, line_x_max,
                text, start_idx, end_idx, segments
            )

            # 5. 坐标转换：扫描坐标 -> PDF坐标
            pdf_x = sub_x / self.scan_scale
            pdf_y = line_y_min / self.scan_scale
            pdf_w = sub_w / self.scan_scale
            pdf_h = (line_y_max - line_y_min) / self.scan_scale

            # 6. 应用偏移（off_x/off_w 为 PDF 点空间）
            final_x = pdf_x - self.off_x
            final_w = max(2.0, pdf_w - self.off_w)

            # v37.7.15 cp45: PDF 坐标系 padding 吸收 OCR v3.x box ±2-5px 偏差
            # 解决"遮罩没完整覆盖文字"：左右各扩 1pt、上下各扩 0.5pt
            # 1pt ≈ 1.33px @96DPI，足以吸收 RapidOCR PP-OCRv6 行级 box 常见偏差
            PAD_X = 1.0  # 左右各 1pt
            PAD_Y = 0.5  # 上下各 0.5pt
            final_x -= PAD_X
            final_w += 2 * PAD_X
            pdf_y -= PAD_Y
            pdf_h += 2 * PAD_Y

            return QRectF(final_x, pdf_y, final_w, pdf_h)
        except (ValueError, ZeroDivisionError, TypeError) as e:
            logger.warning("[WARN] _calculate_from_line 错误: %s", e)
            return None

    def _verify_sub_rect_width(self, sub_x, sub_w, line_x_min, line_x_max,
                                text, start_idx, end_idx, segments):
        """v37.7.9 cp38 F24: sub_rect 宽度合理性检查（稳定性兜底）

        在 _calculate_from_line 返回前做最后兜底，检测段切分失败导致的两种异常：
          1. sub_w 过窄：误切单字符（A 档把多字节字符切成多段，sub_w 只覆盖部分）
          2. sub_w 过宽：退化为整行（段切分失败返回单段，A/B 档退化为 C 档整行宽度）

        合理范围：[match_char_count × avg_char_w × 0.5, match_char_count × avg_char_w × 1.5]
          - avg_char_w = line_width / len(text)（整行均摊字符宽度）
          - 下限 0.5：避免 sub_w 不足半个字符宽
          - 上限 1.5：避免 sub_w 超过 1.5 倍预期（覆盖过多相邻字符）

        触发回退时不抛异常，仅记录告警 + 用权重估算或段块宽度收紧。
        与现有 A/B/C 档逻辑解耦，作为最终稳定性扩展。

        Args:
            sub_x, sub_w: 当前 sub_rect 像素坐标（扫描空间）
            line_x_min, line_x_max: 整行边界（扫描空间）
            text: 整行文本
            start_idx, end_idx: 匹配位置
            segments: 段切分结果（扫描空间，已转回原坐标）

        Returns:
            (sub_x, sub_w): 校正后的坐标（可能未变，也可能回退到权重估算）
        """
        try:
            match_char_count = end_idx - start_idx
            if match_char_count <= 0 or sub_w <= 0:
                return sub_x, sub_w

            line_width = line_x_max - line_x_min
            if line_width <= 0 or len(text) == 0:
                return sub_x, sub_w

            avg_char_w = line_width / len(text)
            min_expected_w = match_char_count * avg_char_w * 0.5
            max_expected_w = match_char_count * avg_char_w * 1.5

            def _get_char_weight(char):
                """CJK 1.0 / 标点 1.0 / 空格 0.3 / 其他 0.55"""
                if '\u4e00' <= char <= '\u9fff':
                    return 1.0
                elif char in '，。；：！？、':
                    return 1.0
                elif char == ' ':
                    return 0.3
                else:
                    return 0.55

            if sub_w < min_expected_w:
                # sub_w 过窄：可能误切单字符，回退到权重估算
                logger.debug("[F24 WARN] sub_w=%.1fpx < min_expected=%.1fpx, "
                             "回退权重估算 (match=%s chars, avg_char_w=%.1fpx)",
                             sub_w, min_expected_w, match_char_count, avg_char_w)
                total_weight = sum(_get_char_weight(c) for c in text)
                prefix_weight = sum(_get_char_weight(c) for c in text[:start_idx])
                match_weight = sum(_get_char_weight(c) for c in text[start_idx:end_idx])
                if total_weight > 0:
                    sub_x = line_x_min + (prefix_weight / total_weight) * line_width
                    sub_w = (match_weight / total_weight) * line_width
            elif sub_w > max_expected_w and segments:
                # sub_w 过宽且段切分有结果：用段块宽度收紧
                seg_block_left = min(l for l, r in segments)
                seg_block_right = max(r for l, r in segments)
                seg_block_width = seg_block_right - seg_block_left
                if seg_block_width < sub_w * 0.8:
                    logger.debug("[F24 WARN] sub_w=%.1fpx > max_expected=%.1fpx, "
                                 "段块宽度 %.1fpx 更合理, 用段块估算收紧",
                                 sub_w, max_expected_w, seg_block_width)
                    total_weight = sum(_get_char_weight(c) for c in text)
                    prefix_weight = sum(_get_char_weight(c) for c in text[:start_idx])
                    match_weight = sum(_get_char_weight(c) for c in text[start_idx:end_idx])
                    if total_weight > 0:
                        seg_block_center = (seg_block_left + seg_block_right) / 2
                        refined_w = min(line_width, seg_block_width)
                        refined_x = seg_block_center - refined_w / 2
                        if refined_x < line_x_min:
                            refined_x = line_x_min
                        if refined_x + refined_w > line_x_max:
                            refined_w = line_x_max - refined_x
                        sub_x = refined_x + (prefix_weight / total_weight) * refined_w
                        sub_w = (match_weight / total_weight) * refined_w

            return sub_x, sub_w
        except Exception as e:
            logger.warning("[F24 WARN] _verify_sub_rect_width 错误: %s", e)
            return sub_x, sub_w

    def run(self):
        """执行 OCR 扫描

        v37.0.6: 重构信号发送顺序，确保资源清理后再发送信号
        v37.0.5: 增强异常处理
        v36.4: 使用信号槽机制替代共享字典
        """
        error_msg = None
        doc = None
        # cp_person_name v40.2.3: 跨页共享人名/机构名集合——任一页锚点发现后，
        # 后续所有页（含签名行等无锚点出现处）同名同遮（每次扫描重置）
        self._pn_shared = set()
        self._pn_first_rects = {}   # 页 → 首次结果（回填合并重发用）
        self._pn_text_cache = {}    # 页 → 文字层文本（回填 search_for 用）
        self._pn_lines_cache = {}   # 页 → [(clip_rect, box, text)]（回填行匹配用）
        try:
            # v37.4.0: 直接使用 RapidOCR
            from privacyguard.ocr.rapidocr import RapidOCREngine
            ocr_engine = RapidOCREngine()

            if not ocr_engine.is_available():
                # O3: 不 return，落入统一信号发射路径，否则主线程永远等不到
                # error_signal/finished_signal，扫描按钮永久禁用、UI 卡死
                # cp116: 拼入真实异常（is_available 现在捕获所有异常并存储），
                # 让用户/日志直接看到根因（缺哪个模块/数据文件/DLL），不再猜
                real_err = ocr_engine.get_last_error()
                if real_err:
                    error_msg = (
                        "RapidOCR 引擎不可用，请检查依赖安装\n"
                        f"—— 真实异常 ——\n{real_err}"
                    )
                else:
                    error_msg = "RapidOCR 引擎不可用，请检查依赖安装"
                logger.error("[OCR ERROR] %s", error_msg)
                raise OCREngineUnavailableError(error_msg)

            logger.info("[OCR] 使用引擎: %s", ocr_engine.name)

            doc = (fitz.open(stream=self.pdf_bytes, filetype="pdf")
                   if self.pdf_bytes is not None else fitz.open(self.pdf_path))
            # cp114: 加密 PDF 认证——fitz.open 成功但页面内容仍加密，
            # 需 authenticate 后才能 get_text / get_pixmap，否则报
            # "document closed or encrypted"
            if doc.needs_pass:
                if not self.pdf_open_password or doc.authenticate(self.pdf_open_password) <= 0:
                    error_msg = "文档已加密，密码错误或未提供，无法执行 OCR 扫描"
                    logger.error("[OCR ERROR] %s", error_msg)
                    raise OCREngineUnavailableError(error_msg)
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
                    # v40.2.3 门控：仅称谓人名规则启用时才构建回填缓存
                    # （行缓存每条 ~812B，248 页 ~10MB/1000 页最坏 ~62MB——
                    # 规则关闭时这些缓存无人消费，违背"关闭零开销"承诺）
                    pn_enabled = any("(?P<lead>" in p for p in all_patterns if isinstance(p, str))

                    page_text = page.get_text()
                    page_dict = page.get_text("dict")
                    # v40.2.3: 文字层文本缓存（回填 search_for 用）
                    if pn_enabled and page_text.strip():
                        self._pn_text_cache[i] = page_text
                    image_clip_rects = collect_embedded_image_clip_rects(page_dict)
                    # cp67: get_text('dict') 的 bbox 是未旋转坐标；旋转页需转为
                    # display 坐标（get_pixmap clip / 遮罩链路统一用 display）
                    if getattr(page, "rotation", 0) and image_clip_rects:
                        rotated_clips = []
                        for (cx0, cy0, cx1, cy1) in image_clip_rects:
                            disp = fitz.Rect(cx0, cy0, cx1, cy1) * page.rotation_matrix
                            disp.normalize()
                            rotated_clips.append((disp.x0, disp.y0, disp.x1, disp.y1))
                        image_clip_rects = rotated_clips

                    if page_text.strip():
                        hit_boxes = collect_text_pdf_hit_boxes(page, all_patterns, page_text=page_text,
                                                              shared_person_names=self._pn_shared)
                        # v37.7.13 cp43: hit_boxes 现为 6 元组 (x,y,w,h,found_str,rule_override)
                        # cp71: 文本层命中框也应用 box_adjust_ratio（与图像 OCR 路径一致，
                        # 修复“OCR 检测框调节”对文本型 PDF 无效的死配置）
                        # cp_person_name: rule_override 优先（人名子串不含称谓前缀，
                        # 内容反查 classify 会误落到"智能识别"）
                        for x, y, w, h, found_str, rule_override in hit_boxes:
                            if self.box_adjust_ratio:
                                x, y, w, h = apply_box_adjust_to_hit(x, y, w, h, self.box_adjust_ratio)
                            rects.append({'rect': QRectF(x, y, w, h),
                                          'replace_text': self._lookup_replace(found_str),
                                          'rule': rule_override or self._classify_rule(found_str)})

                    if not image_clip_rects and not page_text.strip() and page.get_contents():
                        image_clip_rects = [(page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1)]

                    image_hit_count = 0
                    if image_clip_rects:
                        # v37.7.9 cp37 F19-B: 过滤低置信度 OCR 行
                        # 原代码直接传 ocr_engine.recognize,无置信度过滤
                        # 现在读取真实 confidence 后,过滤 < MIN_OCR_CONFIDENCE 的噪声行
                        # 避免低质量 OCR 行进入 _calculate_from_line 产生错误 sub_rect
                        MIN_OCR_CONFIDENCE = 0.5

                        def _filtered_recognize(scan_img):
                            results = ocr_engine.recognize(scan_img)
                            return [r for r in results
                                    if getattr(r, 'confidence', 0.9) >= MIN_OCR_CONFIDENCE]

                        image_hit_rects = collect_image_block_ocr_hits(
                            page,
                            all_patterns,
                            SCAN_SCALE,
                            recognize_fn=_filtered_recognize,
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
                            # v37.7.18 cp53: 限制整块覆盖面积
                            # 原因：当 clip_rect 是整页（扫描件兜底）时，OCR 失败会生成
                            #   覆盖整页的大矩形，产生"一大块"遮罩遮挡正常内容
                            # 修复：超过页面面积 30% 的 clip_rect 不触发整块覆盖
                            on_block_failure_fn=self._make_block_failure_fn(page.rect),
                            is_cancelled_fn=self.isInterruptionRequested,
                            shared_person_names=self._pn_shared if pn_enabled else None,
                            # v40.2.3 门控：规则关闭时传 None，行缓存不构建（零开销）
                            ocr_lines_sink=self._pn_lines_cache.setdefault(i, []) if pn_enabled else None,
                        )
                        # v37.7.13 cp43: image_hit_rects 现为 [(rect, matched_text, rule_override)]
                        # cp_person_name: rule_override 优先（同文本层路径）
                        for rect_q, matched_text, rule_override in image_hit_rects:
                            rects.append({'rect': rect_q,
                                          'replace_text': self._lookup_replace(matched_text),
                                          'rule': rule_override or self._classify_rule(matched_text)})
                        image_hit_count = len(image_hit_rects)

                    if image_clip_rects or (page_text.strip() and rects):
                        logger.info("[OCR] 页面 %s: 文本命中 %s, 图片块 %s, 图片OCR命中 %s",
                                    i, len(rects) - image_hit_count,
                                    len(image_clip_rects), image_hit_count)

                    # v37.5.0/cp60: 印章 + 签名手印检测（共用整页渲染）
                    seal_on = self.seal_detection_enabled and "__SEAL_DETECTION__" in self.rules
                    sig_on = self.signature_detection_enabled and "__SIGNATURE_DETECTION__" in self.rules
                    if seal_on or sig_on:
                        try:
                            # v40.1.4（性能）：samples 直读替代 PNG 编码+解码往返（每页省约 31ms）
                            pix = page.get_pixmap(matrix=fitz.Matrix(SCAN_SCALE, SCAN_SCALE), alpha=False)
                            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                                pix.height, pix.width, pix.n)[:, :, :3][:, :, ::-1].copy()
                            # v37.7.18 cp51/cp52: 必须用原始彩色图 + 补偿 page_origin
                            page_origin = (page.rect.x0, page.rect.y0)
                            if seal_on:
                                seal_rects = self._detect_seals(
                                    img_np, SCAN_SCALE,
                                    ocr_engine=ocr_engine,
                                    page_origin=page_origin,
                                )
                                for seal_rect in seal_rects:
                                    rects.append({'rect': seal_rect, 'replace_text': '', 'rule': '印章'})
                                if seal_rects:
                                    logger.info("[Seal Detection] 页面 %s 检测到 %s 个印章 (page_origin=%s)",
                                                i, len(seal_rects), page_origin)
                            if sig_on:
                                sig_rects = self._detect_signatures(
                                    img_np, SCAN_SCALE, page_origin=page_origin,
                                )
                                for sig_rect in sig_rects:
                                    rects.append({'rect': sig_rect, 'replace_text': '', 'rule': '签名手印'})
                                if sig_rects:
                                    logger.info("[Signature Detection] 页面 %s 检测到 %s 个签名手印区域",
                                                i, len(sig_rects))
                        except Exception as e:
                            # P2 安全：仅记异常类型，详情降 DEBUG（避免 {e} 含命中 PII 落盘）
                            logger.error("[Seal/Signature Detection] 页面 %s 检测失败: %s",
                                         i, type(e).__name__)
                            logger.debug("[Seal/Signature Detection] 详情", exc_info=True)

                    # P2 跨源去重：文本层 / 图块 OCR / 印章 / 签名 可能命中同一区域，
                    # 合并后按 IoU>=0.5 抑制重复，避免重叠遮罩与报告计数虚高。
                    if len(rects) > 1:
                        rects = dedup_page_rects(rects)

                    # 逐页发送结果
                    self.page_result_signal.emit(i, rects)
                    # v40.2.3: 缓存首次结果供收尾回填合并（覆盖式消费需带全量重发）
                    self._pn_first_rects[i] = rects

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

            # v40.2.3: 扫描收尾回填——人名/机构名可能在后面的页才首次锚定发现，
            # 早期页（签名行等无锚点出现处）用最终人名集补匹配后整页重发
            try:
                self._pn_backfill(doc)
            except Exception:
                logger.debug("[cp_person_name] 回填失败", exc_info=True)

        except Exception as e:
            error_msg = f"OCR 处理错误: {type(e).__name__}: {e}"
            # P2 安全：ERROR 仅记异常类型（{e} 可能含命中 PII），完整 traceback 降 DEBUG
            logger.error("[OCR ERROR] %s", type(e).__name__)
            logger.debug("[OCR ERROR] 详情", exc_info=True)
        finally:
            if doc:
                doc.close()

        # 资源清理后发送信号
        if error_msg:
            self.error_signal.emit(error_msg)
        self.finished_signal.emit({})

    def _pn_backfill(self, doc):
        """v40.2.3: 扫描收尾回填——用最终人名/机构名集对早期页补匹配。

        根因：跨页共享集是"向后传播"的，人名在后页才首次锚定时，更早的页
        （签名行/证照页等无锚点出现处）无法被覆盖。本方法在全部页扫完后，
        用最终集合对每页缓存（文字层文本 / OCR 行）做精确匹配补发增量，
        与首次结果合并后整页重发（主线程覆盖式消费 + IoU 去重）。
        """
        if not self._pn_shared or self.isInterruptionRequested():
            return
        import re as _re
        from privacyguard.ocr.person_name import PERSON_NAME_RULE_NAME
        names = sorted(self._pn_shared)
        exact = [(n, _re.compile(_re.escape(n))) for n in names]
        total = len(doc)
        for pno, first in self._pn_first_rects.items():
            # v40.2.3: 回填期间也响应取消（大文档回填最长可达十几秒，
            # 不检查则取消按钮在此期间失效）
            if self.isInterruptionRequested():
                return
            if not (0 <= pno < total):
                continue
            page = doc[pno]
            extra = []
            # 文字层回填：search_for 精确定位（rotation → display 与主路径一致）
            text = self._pn_text_cache.get(pno)
            if text:
                for n in names:
                    if n not in text:
                        continue
                    try:
                        hits = page.search_for(n)
                    except RuntimeError:
                        continue
                    for hit in hits:
                        if getattr(page, "rotation", 0):
                            hit = fitz.Rect(hit) * page.rotation_matrix
                            hit.normalize()
                        extra.append({'rect': QRectF(hit.x0, hit.y0, hit.width, hit.height),
                                      'replace_text': self._lookup_replace(n),
                                      'rule': PERSON_NAME_RULE_NAME})
            # OCR 行回填：行文本精确匹配 + 权重路径子矩形（无 img_region 回退）
            for clip_rect, box, line_text in self._pn_lines_cache.get(pno, []):
                for n, pat in exact:
                    for m in pat.finditer(line_text):
                        local = self.calculate_sub_rect(box, line_text, m.span(), img_region=None)
                        if local is None:
                            continue
                        extra.append({'rect': QRectF(local.x() + clip_rect[0],
                                                      local.y() + clip_rect[1],
                                                      local.width(), local.height()),
                                      'replace_text': self._lookup_replace(n),
                                      'rule': PERSON_NAME_RULE_NAME})
            if extra:
                self.page_result_signal.emit(pno, list(first) + extra)
