"""UI 组件（从 main.py 提取）。

包含：_ScreenColorPickerOverlay, PageGridScrollArea, SinglePageCanvas。
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QLabel, QScrollArea, QApplication,
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QWheelEvent, QFont, QFontMetrics,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QPoint

from privacyguard.utils.helpers_pdf import _hit_rect, _hit_replace_text, _make_hit

# 模块级调试开关（main.py 启动后会用 config 值覆盖）
DEBUG_MODE = os.getenv('PRIVACYGUARD_DEBUG', 'False').lower() == 'true'


class _ScreenColorPickerOverlay(QWidget):
    """v37.7.10 cp39: 全屏取色覆盖层。

    工作流程：
      1. 构造时传入主屏截屏 QPixmap 与 on_picked 回调
      2. setGeometry(screen.geometry()) 全屏显示截图
      3. 鼠标移动 → 逻辑像素坐标按 DPI 缩放转物理像素 → 取色 → 重绘十字 + 预览
      4. 鼠标点击 → 调用 on_picked(QColor) → close()
      5. Esc 取消 → close()（不触发回调）

    v37.7.10 cp39-fix1: 修复高 DPI 屏取色不准
      - grabWindow 返回物理像素截图，QWidget 鼠标坐标是逻辑像素
      - 直接用鼠标坐标取 pixelColor 会错位（点蓝色取到白色）
      - 用 img.width()/self.width() 做坐标缩放转换
    """

    def __init__(self, screenshot, on_picked, parent=None):
        super().__init__(parent)
        self._screenshot = screenshot
        self._screenshot_img = screenshot.toImage()  # 缓存避免每次转换
        self._on_picked = on_picked
        self._current_color = QColor(0, 0, 0)
        self._mouse_pos = QPoint()
        # 无边框 + 始终置顶 + 工具提示
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

    def _pick_color_at(self, widget_pos):
        """从 QWidget 逻辑像素坐标 → QPixmap 物理像素坐标 → 取色。"""
        if widget_pos.isNull() or self.width() == 0 or self.height() == 0:
            return None
        img = self._screenshot_img
        # 关键：DPI 缩放转换（QPixmap 物理像素 / QWidget 逻辑像素）
        scale_x = img.width() / self.width()
        scale_y = img.height() / self.height()
        img_x = int(widget_pos.x() * scale_x)
        img_y = int(widget_pos.y() * scale_y)
        if 0 <= img_x < img.width() and 0 <= img_y < img.height():
            return img.pixelColor(img_x, img_y)
        return None

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._screenshot)
        if not self._mouse_pos.isNull():
            # 十字线（白色 1px + 黑色 1px 错位增强对比）
            pen = QPen(QColor(255, 255, 255, 200))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(self._mouse_pos.x(), 0, self._mouse_pos.x(), self.height())
            painter.drawLine(0, self._mouse_pos.y(), self.width(), self._mouse_pos.y())
            # 颜色预览框（30×30）显示在十字右侧
            preview_x = min(self._mouse_pos.x() + 12, self.width() - 36)
            preview_y = max(self._mouse_pos.y() - 42, 4)
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.setBrush(self._current_color)
            painter.drawRect(preview_x, preview_y, 30, 30)
            # HEX 文本
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.drawText(preview_x, preview_y + 44, self._current_color.name().upper())

    def mouseMoveEvent(self, event):
        self._mouse_pos = event.position().toPoint()
        color = self._pick_color_at(self._mouse_pos)
        if color is not None:
            self._current_color = color
        self.update()

    def mousePressEvent(self, _event):
        # 点击时再取一次色，确保最终取的是点击瞬间的颜色
        color = self._pick_color_at(self._mouse_pos)
        if color is not None:
            self._current_color = color
        if self._on_picked is not None:
            self._on_picked(QColor(self._current_color))
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


class PageGridScrollArea(QScrollArea):
    """cp67: 页面视图滚动区：Ctrl+滚轮发列数调节信号，普通滚轮正常滚动。"""

    ctrl_wheel = pyqtSignal(int)  # +1=放大（列数减），-1=缩小（列数增）

    def wheelEvent(self, event: QWheelEvent):
        # v40.1.4（用户反馈 #6）：macOS 用 ⌘(Meta)+滚轮 与 Windows Ctrl+滚轮 等效
        mods = QApplication.keyboardModifiers()
        if mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
            delta = event.angleDelta().y()
            if delta:
                self.ctrl_wheel.emit(1 if delta > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


# === 单页画布 (完全复制 v7.0 的 PDFCanvas 实现) ===
class SinglePageCanvas(QLabel):
    # 保留信号以兼容双页模式
    rect_added = pyqtSignal(int, QRectF)
    rect_removed = pyqtSignal(int, int, bool)
    zoom_request = pyqtSignal(float)
    page_change_request = pyqtSignal(int)  # 翻页请求信号：正值=下一页，负值=上一页
    # cp65: 手动框选替换开关开启时，框选完成交给主窗口处理（OCR 识别 + 弹窗 + 可选全文遮罩）
    manual_region_prompt = pyqtSignal(QRectF)
    # cp67: 页面视图网格模式下的单击选中（page_index, ctrl多选, shift范围选）与双击定位
    page_clicked = pyqtSignal(int, bool, bool)
    page_activated = pyqtSignal(int)
    # cp122: 纵向区域框选完成（提取/截去模式）：(page_index, y_min, y_max) PDF display 坐标
    vertical_region_selected = pyqtSignal(int, float, float)
    # cp123: 任意模式下左键单击（屏幕坐标），用于提取结果页片段选中
    canvas_clicked = pyqtSignal(QPointF)

    def __init__(self, page_index=0, parent=None):
        super().__init__(parent)
        # 完全复制 v7.0 的初始化
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setAutoFillBackground(True)

        self.page_index = page_index  # 新增：用于双页模式
        self.zoom_scale = 1.0
        self.rects_ocr = []
        self.rects_manual = []
        self.mask_color = QColor(0, 0, 0)
        # v37.7.13 cp43: 手动框选时是否弹窗输入替换文本
        self.manual_replace_prompt = False
        # cp82: 搜索命中闪烁高亮矩形（PDF display 坐标；None=不显示）
        self.flash_rect = None
        # cp67: 页面视图网格模式（page_index 为真实页码；滚轮交给外层滚动区）
        self.grid_mode = False
        # cp122: 纵向框选模式（提取/截去）：拖拽取 y_min/y_max，左右撑满页宽
        self.vertical_select_mode = False
        # cp129: 交互禁用（提取模式右侧用）：禁用左键框选遮罩，仅保留单击选中片段
        self.interaction_disabled = False

        self.drawing = False
        self.start_point = QPointF()
        self.current_rect = QRectF()

    def set_mask_color(self, color):
        """v7.0 方法"""
        self.mask_color = color
        self.update()

    def update_content(self, pixmap, scale, ocr_rects, manual_rects):
        """v7.0 方法 - 直接引用列表，不复制！"""
        self.setPixmap(pixmap)
        self.zoom_scale = scale
        self.rects_ocr = ocr_rects  # ← v7.0 直接引用，不复制
        self.rects_manual = manual_rects  # ← v7.0 直接引用，不复制
        self.update()

    # === v22.7: 完全回归 v7.0 - mousePressEvent 处理左右键 ===
    def mousePressEvent(self, event):
        """v7.0 风格：左键画框，右键删除"""
        if not self.pixmap():
            return
        # cp129: 交互禁用模式下禁用右键删除遮罩
        if getattr(self, "interaction_disabled", False):
            # cp123 修复：仍允许左键单击（提取模式片段选取）——设 drawing=True
            # 让 mouseReleaseEvent 能 emit canvas_clicked；mouseMoveEvent 的
            # interaction_disabled 守卫已阻止画框，不会产生橡皮筋矩形
            if event.button() == Qt.MouseButton.LeftButton:
                self.drawing = True
                self.start_point = event.position()
                self.current_rect = QRectF(self.start_point, self.start_point)
            event.accept()
            return

        # 左键画框
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_point = event.position()
            self.current_rect = QRectF(self.start_point, self.start_point)
            self.update()

        # 右键删除 (v7.0 风格)
        elif event.button() == Qt.MouseButton.RightButton:
            click_pos = event.position()
            if DEBUG_MODE:
                print(f"\n[DEBUG] === 右键点击 === 页面{self.page_index}, 位置({click_pos.x():.2f}, {click_pos.y():.2f})")
                print(f"[DEBUG] 手动框数量: {len(self.rects_manual)}, OCR框数量: {len(self.rects_ocr)}")

            deleted = False
            deleted_manual = False
            deleted_idx = -1

            # 先删手动框（从后往前，优先删除上层）
            for i in range(len(self.rects_manual) - 1, -1, -1):
                screen_rect = self.pdf_to_screen(_hit_rect(self.rects_manual[i]))
                if DEBUG_MODE:
                    print(f"[DEBUG] 检查手动框[{i}]: {screen_rect}, contains={screen_rect.contains(click_pos)}")
                if screen_rect.contains(click_pos):
                    del self.rects_manual[i]
                    deleted = True
                    deleted_manual = True
                    deleted_idx = i
                    if DEBUG_MODE:
                        print(f"[DEBUG] ✓ 删除手动框[{i}]")
                    break

            # 再删 OCR 框
            if not deleted:
                for i in range(len(self.rects_ocr) - 1, -1, -1):
                    screen_rect = self.pdf_to_screen(_hit_rect(self.rects_ocr[i]))
                    if DEBUG_MODE:
                        print(f"[DEBUG] 检查OCR框[{i}]: {screen_rect}, contains={screen_rect.contains(click_pos)}")
                    if screen_rect.contains(click_pos):
                        del self.rects_ocr[i]
                        deleted = True
                        deleted_manual = False
                        deleted_idx = i
                        if DEBUG_MODE:
                            print(f"[DEBUG] ✓ 删除OCR框[{i}]")
                        break

            if deleted:
                self.update()
                # cp83: 发信号通知主窗口（列表共享引用已同步，此处仅用于触发撤销快照）；
                # page_index 携带真实页码（单/双/网格 canvas 均适用）
                self.rect_removed.emit(self.page_index, deleted_idx, deleted_manual)
            else:
                if DEBUG_MODE:
                    print("[DEBUG] ✗ 未点击到任何矩形框")

    def pdf_to_screen(self, rect):
        """v7.0 实现 - 带小的容错范围"""
        base_rect = QRectF(rect.x()*self.zoom_scale, rect.y()*self.zoom_scale,
                           rect.width()*self.zoom_scale, rect.height()*self.zoom_scale)
        # 扩展 2 像素容错范围，处理点击边界的情况
        return base_rect.adjusted(-2, -2, 2, 2)

    def paintEvent(self, event):
        """v7.0 实现

        v37.7.13 cp43: 兼容 dict 元素 + 绘制替换文本叠加层
        cp43-fix: 每次 drawRect 前重置 NoPen，避免 _draw_replace_text 修改 pen 后
        下一个矩形带边框（黑遮白边/白遮黑边）
        """
        super().paintEvent(event)
        if not self.pixmap(): return

        painter = QPainter(self)

        # 使用当前选中的颜色 (黑或白)
        painter.setBrush(self.mask_color)

        # 1. 绘制 AI 框 + 叠加替换文本
        for item in self.rects_ocr:
            r = _hit_rect(item)
            sr = self.pdf_to_screen(r)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(sr)
            replace_text = _hit_replace_text(item)
            if replace_text:
                self._draw_replace_text(painter, sr, replace_text)

        # 2. 绘制 手动框 + 叠加替换文本
        for item in self.rects_manual:
            r = _hit_rect(item)
            sr = self.pdf_to_screen(r)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(sr)
            replace_text = _hit_replace_text(item)
            if replace_text:
                self._draw_replace_text(painter, sr, replace_text)

        # 3. 绘制 拖拽框 (始终红色边框，提示用)
        if self.drawing and not self.current_rect.isEmpty():
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.current_rect)

        # cp82: 搜索命中闪烁高亮（半透明黄底+橙色边框，主窗口定时清除）
        if self.flash_rect is not None and not self.flash_rect.isNull():
            sr = self.pdf_to_screen(self.flash_rect)
            painter.setPen(QPen(QColor(255, 160, 0), 2))
            painter.setBrush(QColor(255, 224, 102, 110))
            painter.drawRect(sr)

    def _draw_replace_text(self, painter, screen_rect, text):
        """v37.7.13 cp43: 在遮罩矩形上绘制替换文本（对比色 + 居中）。

        cp43-fix: 字号基于遮罩矩形高度（已含缩放），与原文字大小匹配。
        screen_rect.height() 反映被替换原文字的视觉高度，用 pixelSize
        直接匹配像素高度，放大/缩小时自动同步。
        """
        mask = self.mask_color
        # 判断遮罩色明度：黑遮罩用白字，其余用黑字
        lightness = (mask.red() + mask.green() + mask.blue()) / 3
        text_color = QColor(255, 255, 255) if lightness < 128 else QColor(0, 0, 0)
        painter.setPen(text_color)
        # cp43-fix: 字号 = 矩形高度 * 0.75（留 25% 上下边距），最小 6px
        pixel_size = max(6, int(screen_rect.height() * 0.75))
        # cp80: 字体回退栈（macOS 无雅黑 → 苹方），避免硬编码单字体
        font = QFont()
        font.setFamilies(["Microsoft YaHei", "PingFang SC", "Helvetica Neue", "Arial"])
        font.setPixelSize(pixel_size)
        # cp69: 宽度自适配——文本按高度定字号后若超出遮罩宽度（矮胖框/长文本），
        # 按宽度比例缩小字号，避免左右被截断显示不全
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(text)
        avail_width = max(1.0, float(screen_rect.width()) - 4.0)
        if text_width > avail_width:
            pixel_size = max(6, int(pixel_size * avail_width / text_width))
            font.setPixelSize(pixel_size)
        painter.setFont(font)
        painter.drawText(screen_rect, Qt.AlignmentFlag.AlignCenter, text)

    def mouseMoveEvent(self, event):
        """v7.0 实现

        cp122: 纵向框选模式下，x 约束到页面宽度（左右撑满），只让 y 跟随鼠标。
        cp129: interaction_disabled 模式下不更新框选矩形（禁用遮罩，仅保留单击选中）。
        """
        if getattr(self, "interaction_disabled", False):
            return
        if self.drawing and not self.start_point.isNull():
            current_pos = QPointF(event.position())
            if getattr(self, "vertical_select_mode", False):
                # 纵向：x 撑满 pixmap 宽度（屏幕坐标），y 跟随鼠标
                pw = self.pixmap().width() if self.pixmap() else self.width()
                y0 = min(self.start_point.y(), current_pos.y())
                y1 = max(self.start_point.y(), current_pos.y())
                self.current_rect = QRectF(0, y0, float(pw), y1 - y0)
            else:
                self.current_rect = QRectF(self.start_point, current_pos).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        """v7.0 实现

        v37.7.13 cp43: 手动框选支持输入替换文本（受 manual_replace_prompt 开关控制）
        cp65: 开关开启时改为发信号交给主窗口：OCR 识别框选文字 + 弹窗（可编辑/
        可全文遮罩/替换文本），主窗口通过共享列表 rects_manual 回写命中
        """
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            # cp122: 纵向框选模式（提取/截去）——优先处理，取 y_min/y_max，左右撑满
            if getattr(self, "vertical_select_mode", False):
                if self.current_rect.height() > 5:
                    _zs = self.zoom_scale
                    if _zs and abs(_zs) > 1e-9:
                        y_min = min(self.current_rect.top(), self.current_rect.bottom()) / _zs
                        y_max = max(self.current_rect.top(), self.current_rect.bottom()) / _zs
                        self.vertical_region_selected.emit(self.page_index, y_min, y_max)
                self.current_rect = QRectF()
                self.update()
                return
            if self.current_rect.width() > 5 and self.current_rect.height() > 5:
                # 安全修复: 防止 zoom_scale 为零时除零崩溃
                _zs = self.zoom_scale
                if not _zs or abs(_zs) < 1e-9:
                    self.current_rect = QRectF()
                    self.update()
                    return
                real_rect = QRectF(
                    self.current_rect.x()/_zs,
                    self.current_rect.y()/_zs,
                    self.current_rect.width()/_zs,
                    self.current_rect.height()/_zs
                )
                # cp65: 开关开启→主窗口接管（识别+弹窗+可选全文遮罩）；先清除橡皮筋框
                if getattr(self, "manual_replace_prompt", False):
                    self.current_rect = QRectF()
                    self.update()
                    self.manual_region_prompt.emit(real_rect)
                    return
                # 开关关闭：纯遮罩，v7.0 直接添加到列表（列表是共享引用）
                self.rects_manual.append(_make_hit(real_rect, ""))
                # cp118: 纯遮罩路径补发 rect_added，使主窗触发 render_view + 撤销快照
                # （此前仅 append 不 emit，导致手动框选无法撤销、双页对侧/保存按钮不刷新）
                self.rect_added.emit(self.page_index, real_rect)
            elif getattr(self, "grid_mode", False):
                # cp67: 网格模式下小于拖拽阈值的点击 = 选中该页（Ctrl 多选 / Shift 范围选）
                modifiers = QApplication.keyboardModifiers()
                ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
                shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
                self.page_clicked.emit(self.page_index, ctrl, shift)
            else:
                # cp123: 非网格模式下的左键单击（无效拖拽）→ 发 canvas_clicked 供片段选中
                self.canvas_clicked.emit(QPointF(event.position()))
            self.current_rect = QRectF()
            self.update()

    def mouseDoubleClickEvent(self, event):
        """cp67: 网格模式双击页面 → 发定位信号（回单页视图定位到该页）。"""
        if getattr(self, "grid_mode", False) and event.button() == Qt.MouseButton.LeftButton:
            self.page_activated.emit(self.page_index)
            return
        super().mouseDoubleClickEvent(event)

    # v35.1: 增强滚轮事件 - 支持缩放和翻页
    # v37.3.6: 添加滚动阈值，防止 macOS 双指轻触误触发翻页
    SCROLL_THRESHOLD = 10  # 滚动阈值（像素），忽略小于此值的小幅滚动

    def wheelEvent(self, event: QWheelEvent):
        # cp67: 网格模式下滚轮全部交给外层滚动区（Ctrl 调列数 / 普通滚动）
        if getattr(self, "grid_mode", False):
            event.ignore()
            return
        modifiers = QApplication.keyboardModifiers()
        delta = event.angleDelta().y()

        # v37.3.6: 忽略非常小的滚动量（macOS 双指轻触产生的噪声）
        if abs(delta) < self.SCROLL_THRESHOLD:
            # 小幅滚动只传递给父类处理正常滚动，不触发翻页
            super().wheelEvent(event)
            return

        # Ctrl/Cmd + 滚轮：缩放（保持原有功能）
        if modifiers == Qt.KeyboardModifier.ControlModifier or modifiers == Qt.KeyboardModifier.MetaModifier:
            event.accept()
            if delta > 0:
                self.zoom_request.emit(0.1)
            else:
                self.zoom_request.emit(-0.1)
        # Shift + 滚轮：快速翻页（一次2页）
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            event.accept()
            if delta < 0:  # 向下滚动 = 下一页
                self.page_change_request.emit(2)
            else:  # 向上滚动 = 上一页
                self.page_change_request.emit(-2)
        # 普通滚轮：触发翻页信号（由 MainWindow 判断滚动条位置）
        else:
            # 发送翻页请求信号，由 MainWindow 处理边缘检测
            if delta < 0:
                self.page_change_request.emit(1)
            else:
                self.page_change_request.emit(-1)
            # 同时传递给父类以支持正常滚动
            super().wheelEvent(event)
