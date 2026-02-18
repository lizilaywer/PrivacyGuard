"""
图片合并 Worker

v36.5: 模块化拆分，从 main.py 提取
"""

import os
from PyQt6.QtCore import QThread, pyqtSignal
import fitz
from PIL import Image


class ImageMergeWorker(QThread):
    """图片合并为PDF的后台线程"""
    finished_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, image_paths, output_path):
        super().__init__()
        self.image_paths = image_paths
        self.output_path = output_path

    def run(self):
        """执行图片合并"""
        try:
            doc = fitz.open()  # 创建新PDF

            total = len(self.image_paths)
            for i, img_path in enumerate(self.image_paths):
                try:
                    # 1. 用Pillow打开图片（使用 with 确保资源释放）
                    with Image.open(img_path) as img:
                        # 2. 转换为RGB（如果需要）
                        if img.mode != 'RGB':
                            img = img.convert('RGB')

                        # 3. 创建PDF页面（保持原始尺寸）
                        page_rect = fitz.Rect(0, 0, img.width, img.height)
                        page = doc.new_page(width=img.width, height=img.height)

                        # 4. 将图片插入到页面（作为独立对象）
                        page.insert_image(page_rect, filename=img_path, overlay=True)

                    # 5. 进度更新
                    progress = int((i + 1) / total * 100)
                    self.progress_signal.emit(progress)

                except (IOError, OSError, ValueError) as e:
                    self.error_signal.emit(f"处理图片 {os.path.basename(img_path)} 失败: {str(e)}")
                    doc.close()
                    return

            # 6. 保存PDF
            doc.save(self.output_path)
            doc.close()
            self.finished_signal.emit(self.output_path)

        except (IOError, OSError, ValueError, RuntimeError) as e:
            self.error_signal.emit(f"合并失败: {str(e)}")
