"""
OCR 引擎管理器
- 简化版本：只保留 RapidOCR
"""

from typing import Optional
from .base import BaseOCREngine
from .rapidocr import RapidOCREngine


class OCREngineManager:
    """OCR 引擎管理器 - v37.4.0: 简化，只保留 RapidOCR"""

    def __init__(self):
        self._engine: Optional[BaseOCREngine] = None
        self._init_engine()

    def _init_engine(self):
        """初始化 RapidOCR 引擎"""
        rapid = RapidOCREngine()
        if rapid.is_available():
            self._engine = rapid
            print("[OCR] RapidOCR 已初始化")
        else:
            print("[WARN] RapidOCR 不可用")

    def get_engine(self) -> Optional[BaseOCREngine]:
        """
        获取 OCR 引擎

        Returns:
            BaseOCREngine: RapidOCR 引擎，如果不可用则返回 None
        """
        return self._engine

    def is_available(self) -> bool:
        """
        检查引擎是否可用

        Returns:
            bool: 引擎是否可用
        """
        return self._engine is not None
