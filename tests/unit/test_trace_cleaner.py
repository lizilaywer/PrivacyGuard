# -*- coding: utf-8 -*-
"""cp90 回归测试：使用痕迹清理（trace_cleaner + temp_manager 崩溃残留识别）。"""
import os
import shutil
import tempfile
import unittest

from privacyguard.trace_cleaner import (
    dir_size_bytes, format_size, collect_trace_items, clean_paths,
    write_pending_webengine, clear_pending_webengine,
)
from privacyguard.utils.temp_manager import TempFileManager, list_stale_temp_entries, TEMP_PREFIX


class TestSizeHelpers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pg_tc_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dir_size_nested(self):
        os.makedirs(os.path.join(self.tmp, "a", "b"))
        with open(os.path.join(self.tmp, "a", "f1"), "wb") as f:
            f.write(b"x" * 100)
        with open(os.path.join(self.tmp, "a", "b", "f2"), "wb") as f:
            f.write(b"y" * 50)
        self.assertEqual(dir_size_bytes(self.tmp), 150)

    def test_dir_size_single_file(self):
        p = os.path.join(self.tmp, "one")
        with open(p, "wb") as f:
            f.write(b"z" * 42)
        self.assertEqual(dir_size_bytes(p), 42)

    def test_dir_size_missing_is_zero(self):
        self.assertEqual(dir_size_bytes(os.path.join(self.tmp, "nope")), 0)
        self.assertEqual(dir_size_bytes(None), 0)

    def test_format_size(self):
        self.assertEqual(format_size(500), "500 B")
        self.assertEqual(format_size(1536), "1.5 KB")
        self.assertEqual(format_size(5 * 1024 * 1024), "5.0 MB")
        self.assertEqual(format_size(None), "0 B")


class TestCollectItems(unittest.TestCase):
    def test_structure_and_defaults(self):
        items = collect_trace_items(sessions_dir=None, temp_entries=[],
                                    web_cache_dirs=[], log_files=[])
        keys = [it["key"] for it in items]
        self.assertEqual(keys, ["sessions", "temp", "webengine", "logs"])
        by_key = {it["key"]: it for it in items}
        self.assertTrue(by_key["sessions"]["default_checked"])
        self.assertTrue(by_key["temp"]["default_checked"])
        self.assertTrue(by_key["webengine"]["default_checked"])
        self.assertFalse(by_key["logs"]["default_checked"])  # 日志默认不勾


class TestCleanPaths(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pg_tc_root_")
        self.outside = tempfile.mkdtemp(prefix="pg_tc_out_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.outside, ignore_errors=True)

    def _mk(self, base, name, is_dir=False, size=10):
        p = os.path.join(base, name)
        if is_dir:
            os.makedirs(p, exist_ok=True)
            with open(os.path.join(p, "inner"), "wb") as f:
                f.write(b"x" * size)
        else:
            with open(p, "wb") as f:
                f.write(b"x" * size)
        return p

    def test_delete_within_root(self):
        f = self._mk(self.root, "f.tmp", size=20)
        d = self._mk(self.root, "sub", is_dir=True, size=30)
        deleted, freed, errors = clean_paths([f, d], [self.root])
        self.assertEqual(deleted, 2)
        self.assertEqual(freed, 50)
        self.assertEqual(errors, [])
        self.assertFalse(os.path.exists(f))
        self.assertFalse(os.path.exists(d))

    def test_reject_outside_root(self):
        outside_file = self._mk(self.outside, "user_doc.pdf", size=99)
        deleted, freed, errors = clean_paths([outside_file], [self.root])
        self.assertEqual(deleted, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("白名单外", errors[0])
        self.assertTrue(os.path.exists(outside_file))  # 未被删除

    def test_missing_path_skipped(self):
        deleted, freed, errors = clean_paths(
            [os.path.join(self.root, "ghost")], [self.root])
        self.assertEqual(deleted, 0)
        self.assertEqual(errors, [])


class TestStaleTempEntries(unittest.TestCase):
    def setUp(self):
        # 用真实系统 temp 造 pgud_ 条目，测完清掉
        self.made = []

    def tearDown(self):
        for p in self.made:
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                elif os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass

    def test_prefixed_stale_detected_and_active_excluded(self):
        tmp_root = tempfile.gettempdir()
        # 伪残留（前缀匹配、未被任何实例追踪）
        stale = os.path.join(tmp_root, TEMP_PREFIX + "stale_test_x")
        with open(stale, "wb") as f:
            f.write(b"1")
        self.made.append(stale)
        # 非前缀文件不应纳入
        other = os.path.join(tmp_root, "other_test_no_prefix_x")
        with open(other, "wb") as f:
            f.write(b"1")
        self.made.append(other)
        # 活跃实例追踪的条目应被排除
        mgr = TempFileManager()
        active = mgr.create_temp_file(suffix=".tmp")
        self.made.append(active)

        found = list_stale_temp_entries()
        self.assertIn(os.path.abspath(stale), found)
        self.assertNotIn(os.path.abspath(other), found)
        self.assertNotIn(os.path.abspath(active), found)  # 活跃被排除
        mgr.cleanup()


class TestPendingWebengineMarker(unittest.TestCase):
    """cp90: WebEngine 延迟清除标记 —— 写入 + 启动清除分支往返（Spec Test Plan）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pg_pending_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_then_clear_roundtrip(self):
        # 造两个待清缓存目录
        cache_a = os.path.join(self.tmp, "cacheA")
        cache_b = os.path.join(self.tmp, "cacheB")
        for c in (cache_a, cache_b):
            os.makedirs(c)
            with open(os.path.join(c, "f"), "wb") as f:
                f.write(b"x" * 10)
        marker = os.path.join(self.tmp, "sessions", "webengine_clear_pending")

        self.assertTrue(write_pending_webengine(marker, [cache_a, cache_b]))
        self.assertTrue(os.path.exists(marker))

        # 启动清除：删两目录 + 删标记（传入白名单覆盖 cache 路径）
        cleared = clear_pending_webengine(marker, allowed_roots=[self.tmp])
        self.assertEqual(cleared, 2)
        self.assertFalse(os.path.exists(cache_a))
        self.assertFalse(os.path.exists(cache_b))
        self.assertFalse(os.path.exists(marker))

    def test_clear_missing_marker_returns_zero(self):
        self.assertEqual(clear_pending_webengine(os.path.join(self.tmp, "nope")), 0)

    def test_clear_skips_missing_dirs_but_removes_marker(self):
        marker = os.path.join(self.tmp, "m")
        write_pending_webengine(marker, [os.path.join(self.tmp, "ghost_dir")])
        cleared = clear_pending_webengine(marker)
        self.assertEqual(cleared, 0)  # 目录不存在不计数
        self.assertFalse(os.path.exists(marker))  # 标记仍被清除

    def test_clear_rejects_outside_allowed_roots(self):
        """安全修复: 白名单外的路径不得删除。"""
        # 造一个在白名单内的目录和一个在白名单外的目录
        inside_dir = os.path.join(self.tmp, "inside_cache")
        outside_dir = os.path.join(self.tmp, "outside_cache")
        os.makedirs(inside_dir)
        os.makedirs(outside_dir)
        marker = os.path.join(self.tmp, "sessions", "marker")
        # 只把 inside_dir 的父目录加入白名单
        write_pending_webengine(marker, [inside_dir, outside_dir])
        cleared = clear_pending_webengine(marker, allowed_roots=[os.path.join(self.tmp, "inside_cache")])
        self.assertEqual(cleared, 1)  # 只有 inside_dir 被删
        self.assertFalse(os.path.exists(inside_dir))
        self.assertTrue(os.path.exists(outside_dir))  # 白名单外保留


class TestTraceCleanDialogRouting(unittest.TestCase):
    """cp118: 验证 TraceCleanDialog 的回调路由（A2）与线程生命周期（A3）。

    A2: 从设置窗口进入时，parent 是 SettingsDialog，但 _main_window 应指向
        MainWindow，使 _mark_webengine_clear_pending/_on_traces_cleaned 能被调用。
    A3: 对话框关闭时应安全等待 _TraceSizeWorker 退出，避免运行中销毁。
    """

    @classmethod
    def setUpClass(cls):
        # Dialog 实例化需要 QApplication（与其他 widget 测试一致的模块级持有模式）
        try:
            from PyQt6.QtWidgets import QApplication
            cls._app = QApplication.instance() or QApplication([])
        except Exception:
            cls._app = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pg_dlg_")
        self._dlgs = []  # 持有引用，统一清理

    def tearDown(self):
        # 统一等待 worker 退出 + 清理对话框，避免运行中销毁
        for dlg in self._dlgs:
            try:
                dlg._shutdown_worker()
            except Exception:
                pass
            try:
                dlg.deleteLater()
            except Exception:
                pass
        self._dlgs = []
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_items(self):
        """构造无 paths 的 items（隐藏对应行，且让 size worker 立即完成）。"""
        return collect_trace_items(
            sessions_dir=None, temp_entries=[], web_cache_dirs=[], log_files=[]
        )

    def _new_dlg(self, parent, main_window):
        from privacyguard.ui.dialogs.trace_clean_dialog import TraceCleanDialog
        dlg = TraceCleanDialog(parent, self._make_items(), [self.tmp],
                               main_window=main_window)
        self._dlgs.append(dlg)
        # 等待 size worker 跑完（items 无 paths，几乎瞬间完成），
        # 避免跨线程信号在测试无事件循环时积压导致后续卡顿
        dlg._size_worker.wait(5000)
        return dlg

    def test_main_window_explicit_takes_priority_over_parent(self):
        """A2: 显式传入 main_window 时，_main_window 应为该引用而非 parent。"""
        if self._app is None:
            self.skipTest("PyQt6 不可用")
        from PyQt6.QtWidgets import QWidget

        class _FakeMainWindow:
            """模拟 MainWindow，带回调方法标记。"""
            def __init__(self):
                self.pending_marked = False
                self.cleaned_keys = None

            def _mark_webengine_clear_pending(self):
                self.pending_marked = True

            def _on_traces_cleaned(self, keys):
                self.cleaned_keys = keys

        # 用真实 QWidget 作为 Qt parent（模拟 SettingsDialog 的窗口层级）
        settings_widget = QWidget()
        main_win = _FakeMainWindow()
        dlg = self._new_dlg(settings_widget, main_window=main_win)
        # 显式 main_window 优先于 parent（settings_widget）
        self.assertIs(dlg._main_window, main_win)

    def test_main_window_defaults_to_parent_when_none(self):
        """A2 向后兼容：未传 main_window 时回退到 parent（旧行为）。"""
        if self._app is None:
            self.skipTest("PyQt6 不可用")
        from PyQt6.QtWidgets import QWidget
        from privacyguard.ui.dialogs.trace_clean_dialog import TraceCleanDialog

        class _FakeMainWindow:
            def _mark_webengine_clear_pending(self):
                pass

            def _on_traces_cleaned(self, keys):
                pass

        # parent 是 QWidget 且实现了回调方法（模拟 MainWindow 直接路径）
        main_win_widget = QWidget()
        main_win_widget._mark_webengine_clear_pending = lambda: None
        main_win_widget._on_traces_cleaned = lambda keys: None
        dlg = TraceCleanDialog(main_win_widget, self._make_items(), [self.tmp])
        self._dlgs.append(dlg)
        dlg._size_worker.wait(5000)  # 等 worker 跑完，避免信号积压
        # 未传 main_window -> 回退 parent（main_win_widget）
        self.assertIs(dlg._main_window, main_win_widget)

    def test_callback_routes_to_main_window_not_parent(self):
        """A2 端到端：模拟 _do_clean 的回调分支，确认命中 _main_window。"""
        if self._app is None:
            self.skipTest("PyQt6 不可用")
        from PyQt6.QtWidgets import QWidget

        class _FakeMainWindow:
            def __init__(self):
                self.cleaned_keys = None

            def _mark_webengine_clear_pending(self):
                pass  # 命中此处即正确

            def _on_traces_cleaned(self, keys):
                self.cleaned_keys = keys

        main_win = _FakeMainWindow()
        dlg = self._new_dlg(QWidget(), main_window=main_win)
        # 直接调用回调（绕过弹窗），验证路由目标
        self.assertTrue(hasattr(dlg._main_window, "_on_traces_cleaned"))
        dlg._main_window._on_traces_cleaned(["sessions"])
        self.assertEqual(main_win.cleaned_keys, ["sessions"])

    def test_shutdown_worker_stops_thread(self):
        """A3: _shutdown_worker 后 worker 线程应已停止（isRunning False）。"""
        if self._app is None:
            self.skipTest("PyQt6 不可用")

        class _FakeMainWindow:
            def _mark_webengine_clear_pending(self):
                pass

            def _on_traces_cleaned(self, keys):
                pass

        dlg = self._new_dlg(None, main_window=_FakeMainWindow())
        dlg._shutdown_worker()
        # 关闭后 worker 应不再运行
        self.assertFalse(dlg._size_worker.isRunning())


if __name__ == "__main__":
    unittest.main()
