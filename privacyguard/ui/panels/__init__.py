# -*- coding: utf-8 -*-
"""UI 面板模块（独立 QWidget 子类，按 AGENTS.md 铁律规则3）。"""
from .extract_side_panel import ExtractSidePanel
from .bookmark_side_panel import BookmarkSidePanel  # cp_bookmark: 书签栏面板

__all__ = ["ExtractSidePanel", "BookmarkSidePanel"]
