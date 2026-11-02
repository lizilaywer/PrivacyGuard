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
        else:
            # cp116: 真实异常存在 RapidOCREngine._last_error 里供诊断（is_available 时已存），
            # 安全审计 v40.1: 不打印/不记录 real_err（含完整 traceback+绝对路径）。
            import logging as _lg
            _lg.getLogger(__name__).warning("[OCR] 引擎不可用，详情见 RapidOCREngine._last_error")
            print("[WARN] OCR 引擎不可用: RapidOCR 初始化失败，扫描功能将不可用")

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
