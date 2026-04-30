"""
PrivacyGuard OCR 模块
提供统一的 OCR 接口 - v37.4.0: 单引擎架构（RapidOCR）
v37.7.3: 修复 PyInstaller 打包时的相对导入问题
"""

# 使用绝对导入（修复 PyInstaller 打包问题）
from privacyguard.ocr.base import BaseOCREngine, OCRResult, CharInfo
from privacyguard.ocr.rapidocr import RapidOCREngine
from privacyguard.ocr.manager import OCREngineManager

__all__ = [
    'BaseOCREngine',
    'OCRResult',
    'CharInfo',
    'RapidOCREngine',
    'OCREngineManager',
]
