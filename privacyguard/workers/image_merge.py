"""
图片合并 Worker

v36.5: 模块化拆分，从 main.py 提取
"""

import io
import os
from PyQt6.QtCore import QThread, pyqtSignal
import fitz
from PIL import Image


class ImageMergeWorker(QThread):
    """图片合并为PDF的后台线程"""
    finished_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, image_paths, output_path, parent=None):
        super().__init__(parent)
        self.image_paths = image_paths
        self.output_path = output_path

    def run(self):
        """执行图片合并"""
        doc = None
        try:
            doc = fitz.open()  # 创建新PDF

            total = len(self.image_paths)
            for i, img_path in enumerate(self.image_paths):
                # 安全修复: 支持取消（与 OCRWorker/WordWorker 一致）
                if self.isInterruptionRequested():
                    # P2: 取消时发 terminal signal（空路径），避免 UI 进度条/标志搁浅
                    self.finished_signal.emit("")
                    return

                try:
                    # 1. 用Pillow打开图片（使用 with 确保资源释放）
                    with Image.open(img_path) as img:
                        # 2. 转换为RGB（如果需要）
                        if img.mode != 'RGB':
                            img = img.convert('RGB')

                        # 3. 创建PDF页面（保持原始尺寸）
                        page_rect = fitz.Rect(0, 0, img.width, img.height)
                        page = doc.new_page(width=img.width, height=img.height)

                        # 4. 安全修复: 用 stream 传入已转换的图片字节，
                        #    而非 filename 重读原始文件（RGB 转换才会生效）
                        buf = io.BytesIO()
                        img.save(buf, format='PNG')
                        page.insert_image(page_rect, stream=buf.getvalue(), overlay=True)

                    # 5. 进度更新
                    progress = int((i + 1) / total * 100)
                    self.progress_signal.emit(progress)

                except (IOError, OSError, ValueError) as e:
                    self.error_signal.emit(f"处理图片 {os.path.basename(img_path)} 失败: {str(e)}")
                    return

            # 6. 保存PDF
            doc.save(self.output_path)
            self.finished_signal.emit(self.output_path)

        except Exception as e:
            # cp118: 扩大为 Exception 兜底——PyMuPDF save 失败抛 FzErrorSystem 等
            # 自有异常，不在原 (IOError, OSError, ValueError, RuntimeError) 范围内，
            # 会导致异常穿透且 finally 外无 error_signal 通知用户。
            self.error_signal.emit(f"合并失败: {type(e).__name__}: {str(e)}")
        finally:
            # cp118: 确保 PyMuPDF Document 在任何路径下都被释放（不靠 GC），
            # 修复 doc.save() 抛异常或取消时 doc.close() 被跳过的资源泄漏
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass
