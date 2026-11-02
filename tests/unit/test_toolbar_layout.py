# -*- coding: utf-8 -*-
"""cp87(D2): 工具栏布局回归防护。

固化 cp84-86 修复的行为，防止"改一处挤一处"回归：
1. 溢出 → 强制 narrow 置位并触发重刷
2. 已置位再入 → 压 min 到屏幕上限
3. 跨屏（可用宽足够）→ 解除强制并重刷
4. 内容超窗口但屏幕够宽 → 抬 min + resize 拉宽兜底
全部用 QWidget stub + MethodType 绑定真实 MainWindow 方法（离屏可跑，
不实例化完整 MainWindow —— QtWebEngine 离屏实例化会崩，为既有限制）。
"""
import os
import sys
import unittest
from types import MethodType, SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton
    import main as app_main
    _APP = QApplication.instance() or QApplication([])  # 模块级持有，防 GC 后 QWidget 失效
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


def _make_stub(content_width_each=300, count=6, avail_width=1000):
    """构造带真实 QHBoxLayout 的工具栏 stub。"""
    stub = QWidget()
    lay = QHBoxLayout()
    for _ in range(count):
        b = QPushButton("X")
        b.setFixedSize(content_width_each, 30)
        lay.addWidget(b)
    stub.setLayout(lay)  # layout 必须挂 widget，否则 sizeHint=0
    stub.toolbar_layout = lay
    stub._base_min_window_width = 1100
    stub._refresh_calls = []
    stub._refresh_toolbar_responsiveness = lambda: stub._refresh_calls.append(1)
    stub.screen = lambda: SimpleNamespace(
        availableGeometry=lambda: SimpleNamespace(width=lambda: avail_width))
    stub._enforce = MethodType(app_main.MainWindow._enforce_toolbar_min_width, stub)
    return stub


@unittest.skipUnless(HAS_DEPS, "PyQt6/main 不可用")
class TestToolbarOverflow(unittest.TestCase):
    def test_overflow_forces_narrow_once(self):
        stub = _make_stub(avail_width=1000)  # 内容 ~1800 > 1000
        stub._enforce()
        self.assertTrue(getattr(stub, "_toolbar_forced_narrow", False))
        self.assertEqual(len(stub._refresh_calls), 1)
        stub.deleteLater()

    def test_forced_reentry_clamps_to_screen(self):
        stub = _make_stub(avail_width=1000)
        stub._enforce()  # 置位
        stub._refresh_calls.clear()
        stub._enforce()  # 再入：不重刷，压 min 到 avail-20
        self.assertEqual(stub._refresh_calls, [])
        self.assertEqual(stub.minimumWidth(), 980)
        stub.deleteLater()

    def test_wider_screen_releases_forced_narrow(self):
        stub = _make_stub(avail_width=1000)
        stub._enforce()
        stub.screen = lambda: SimpleNamespace(
            availableGeometry=lambda: SimpleNamespace(width=lambda: 2600))
        stub._refresh_calls.clear()
        stub._enforce()
        self.assertFalse(stub._toolbar_forced_narrow)
        self.assertEqual(len(stub._refresh_calls), 1)
        stub.deleteLater()

    def test_resize_fallback_when_screen_fits(self):
        stub = _make_stub(avail_width=2600)  # 屏幕够宽
        stub.resize(1300, 800)
        stub._enforce()
        self.assertFalse(getattr(stub, "_toolbar_forced_narrow", False))
        self.assertGreaterEqual(stub.minimumWidth(), 1800)  # 内容+边距
        self.assertGreaterEqual(stub.width(), stub.minimumWidth())  # 主动拉宽兜底
        stub.deleteLater()


@unittest.skipUnless(HAS_DEPS, "PyQt6/main 不可用")
class TestToolbarStructure(unittest.TestCase):
    """静态断言：cp84/86 的布局规则不被回退。"""

    def test_dual_stretch_in_source(self):
        # cp86: tb_layout 恰有 2 个 addStretch（左组后 / nav 组后）
        with open(os.path.join(os.path.dirname(app_main.__file__), "main.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertEqual(src.count("tb_layout.addStretch"), 2)
        # cp86: zoom/nav 强制同宽已移除
        self.assertNotIn("shared_group_width", src)

    def test_group_spacing_floor(self):
        # cp84: 组内间距下限 >= 6
        with open(os.path.join(os.path.dirname(app_main.__file__), "main.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn("group_spacing = max(6,", src)


if __name__ == "__main__":
    unittest.main()
