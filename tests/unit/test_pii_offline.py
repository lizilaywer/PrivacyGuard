"""tests/unit/test_pii_offline.py — ENGINE-08 零网络守护。

Phase 1: 强制 PII 引擎在扫描过程中不触发任何网络调用（socket / requests / httpx /
urllib 等）。这是隐私工具的硬契约 —— 用户的敏感文档绝不能离开本机。

两组测试：
1. TestPiiOffline.test_engine_makes_no_network_calls：
   monkey-patch socket.socket，记录 500 页扫描后的 socket 调用次数；必须为 0。
2. TestPrivacyGuardPiiNoTopLevelNetwork.test_no_requests_or_httpx_imports：
   静态扫描 privacyguard/pii/*.py + 子目录所有 .py，确认无网络库 import。
"""
import socket
import unittest
from pathlib import Path
from unittest.mock import patch


PII_DIR = Path(__file__).resolve().parents[2] / "privacyguard" / "pii"


class TestPiiOffline(unittest.TestCase):
    """ENGINE-08: 扫描完整 500 页文档后断言 socket.socket 调用次数为 0。"""

    def test_engine_makes_no_network_calls(self):
        """monkey-patch socket.socket，跑 500 页 detect，断言 socket 调用次数 == 0。"""
        from privacyguard.pii.engine import PIIEngine
        from privacyguard.pii.hits import TextUnit

        engine = PIIEngine()
        original_socket = socket.socket
        socket_calls = []

        def counting_socket(*args, **kwargs):
            socket_calls.append((args, kwargs))
            return original_socket(*args, **kwargs)

        with patch("socket.socket", side_effect=counting_socket):
            for i in range(500):
                unit = TextUnit(
                    page_index=i,
                    text=f"page {i} 13812345678 53010219200508011X",
                    source="text",
                )
                engine.detect(unit)

        self.assertEqual(
            len(socket_calls),
            0,
            f"PII 引擎在 500 页扫描中触发了 {len(socket_calls)} 次 socket 调用",
        )


class TestPrivacyGuardPiiNoTopLevelNetwork(unittest.TestCase):
    """ENGINE-08: privacyguard/pii/*.py 静态扫描 — 无网络库 import。"""

    def test_no_requests_or_httpx_imports(self):
        """扫描所有 privacyguard/pii/*.py 文件，确认无 requests/httpx/urllib 网络库 import。"""
        forbidden_patterns = (
            "import requests",
            "import httpx",
            "import urllib.request",
            "from requests import",
            "from httpx import",
            "from urllib.request import",
            "import aiohttp",
            "from aiohttp import",
        )
        self.assertTrue(PII_DIR.exists(), "privacyguard/pii/ 应存在")
        for py_file in PII_DIR.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            for line_no, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if not (stripped.startswith("import ") or stripped.startswith("from ")):
                    continue
                for pattern in forbidden_patterns:
                    if pattern in stripped:
                        rel = py_file.relative_to(PII_DIR.parent.parent)
                        self.fail(
                            f"{rel} 第 {line_no} 行含禁用的网络库导入 '{stripped}'"
                            f"（ENGINE-08 零网络契约）"
                        )


if __name__ == "__main__":
    unittest.main()