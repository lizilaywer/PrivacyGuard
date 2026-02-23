"""
PrivacyGuard OCR 模块
提供统一的 OCR 接口 - v37.4.0: 单引擎架构（RapidOCR）
"""

from .base import BaseOCREngine, OCRResult, CharInfo
from .rapidocr import RapidOCREngine
from .manager import OCREngineManager

__all__ = [
    'BaseOCREngine',
    'OCRResult',
    'CharInfo',
    'RapidOCREngine',
    'OCREngineManager',
]
