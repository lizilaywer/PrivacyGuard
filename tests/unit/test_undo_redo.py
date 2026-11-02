"""cp83 回归测试：撤销/恢复纯函数（snapshot_page_data / restore_page_data / push_undo_snapshot）

覆盖：
1. snapshot/restore 往返一致（含 replace_text、多页、空页、ocr+manual 混合）
2. QRectF→tuple→QRectF 精度
3. 深拷贝隔离（改原 page_data / 改恢复结果 互不影响快照）
4. push_undo_snapshot 超限弹出最早、返回同一 stack
"""
import unittest

try:
    from PyQt6.QtCore import QRectF
    from privacyguard.utils.helpers_pdf import (
        snapshot_page_data, restore_page_data, push_undo_snapshot, _make_hit,
    )
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "PyQt6 未安装")
class TestSnapshotRoundtrip(unittest.TestCase):
    def _sample(self):
        return {
            0: {"ocr": [_make_hit(QRectF(1, 2, 3, 4), "X")],
                "manual": [_make_hit(QRectF(5, 6, 7, 8), "")]},
            1: {"ocr": [], "manual": []},
            2: {"ocr": [_make_hit(QRectF(10, 20, 30, 40), "姓名"),
                        _make_hit(QRectF(11, 21, 31, 41), "")],
                "manual": []},
        }

    def test_roundtrip_equivalent(self):
        pd = self._sample()
        snap = snapshot_page_data(pd)
        restored = restore_page_data(snap)
        # 结构一致
        self.assertEqual(set(restored.keys()), {0, 1, 2})
        # 逐项 rect + replace 一致
        r0 = restored[0]["ocr"][0]
        self.assertEqual((r0["rect"].x(), r0["rect"].y(), r0["rect"].width(), r0["rect"].height()),
                         (1, 2, 3, 4))
        self.assertEqual(r0["replace_text"], "X")
        self.assertEqual(restored[0]["manual"][0]["replace_text"], "")
        self.assertEqual(restored[1]["ocr"], [])
        self.assertEqual(restored[2]["ocr"][0]["replace_text"], "姓名")
        self.assertEqual(len(restored[2]["ocr"]), 2)

    def test_snapshot_is_pure_tuples(self):
        snap = snapshot_page_data(self._sample())
        # 快照为纯数据（无 QRectF），可安全深拷贝/序列化
        t = snap[0]["ocr"][0]
        self.assertEqual(t, (1.0, 2.0, 3.0, 4.0, "X"))

    def test_deepcopy_isolation_modify_original(self):
        pd = self._sample()
        snap = snapshot_page_data(pd)
        # 改原 page_data 不影响已存快照
        pd[0]["ocr"].append(_make_hit(QRectF(99, 99, 9, 9), "Z"))
        pd[0]["manual"][0]["rect"].setX(999)
        self.assertEqual(len(snap[0]["ocr"]), 1)
        self.assertEqual(snap[0]["manual"][0][0], 5.0)  # x 未受污染

    def test_deepcopy_isolation_modify_restored(self):
        snap = snapshot_page_data(self._sample())
        r1 = restore_page_data(snap)
        r2 = restore_page_data(snap)
        # 两次 restore 产生独立对象
        r1[0]["ocr"][0]["rect"].setX(555)
        self.assertNotEqual(r2[0]["ocr"][0]["rect"].x(), 555)
        self.assertEqual(snap[0]["ocr"][0][0], 1.0)

    def test_empty_page_data(self):
        self.assertEqual(snapshot_page_data({}), {})
        self.assertEqual(restore_page_data({}), {})


class TestPushUndoSnapshot(unittest.TestCase):
    def test_push_within_limit(self):
        stack = []
        for i in range(3):
            push_undo_snapshot(stack, {"id": i}, 5)
        self.assertEqual([s["id"] for s in stack], [0, 1, 2])

    def test_push_over_limit_drops_oldest(self):
        stack = []
        for i in range(8):
            push_undo_snapshot(stack, {"id": i}, 5)
        self.assertEqual(len(stack), 5)
        self.assertEqual([s["id"] for s in stack], [3, 4, 5, 6, 7])

    def test_returns_same_stack(self):
        stack = []
        ret = push_undo_snapshot(stack, {"id": 0}, 5)
        self.assertIs(ret, stack)


@unittest.skipUnless(HAS_DEPS, "PyQt6 未安装")
class TestMaskSnapshotInheritsStructure(unittest.TestCase):
    """安全审计 v40.1.4（S1）：mask-only 快照必须继承结构字节流。

    场景：扫描完成（mask-only 快照）→ 删页（结构快照）→ Ctrl+Z。
    修复前：doc 保持删页后结构、page_data 回到删页前 → 页数不齐/遮罩错位。
    修复后：undo 恢复到 mask-only 快照时 doc 也回到对应结构（页数一致）。
    """

    def _make_stub(self):
        import fitz
        from types import SimpleNamespace
        doc = fitz.open()
        for _ in range(3):
            doc.new_page(width=200, height=300)
        stub = SimpleNamespace(
            doc=doc, page_data={}, current_page=0, _pdf_modified=False,
            _undo_stack=[], _redo_stack=[], _restoring_snapshot=False,
            _UNDO_MAX=20, page_view_mode=False,
            _ocr_processed_pages=set(),
            _search_ocr_cache={},
            _draft_timer=SimpleNamespace(stop=lambda: None, start=lambda: None,
                                         isActive=lambda: False),
            _flush_session_draft=lambda *a, **k: None,
            _spill_oversized_undo_bytes=lambda: None,
            _sweep_undo_spill_files=lambda: None,
            _refresh_undo_redo_buttons=lambda: None,
            _invalidate_grid_cache=lambda: None,
            render_view=lambda: None,
            _set_info_bar_message=lambda *a, **k: None,
        )
        # 绑定 MainWindow 的撤销方法（内部经 self.xxx 互调）
        from main import MainWindow
        stub._build_undo_snapshot = lambda structural=True: MainWindow._build_undo_snapshot(stub, structural)
        stub._capture_undo_state = lambda structural=False: MainWindow._capture_undo_state(stub, structural)
        stub._apply_snapshot = lambda snap: MainWindow._apply_snapshot(stub, snap)
        stub._refresh_derived_state_after_restore = lambda: MainWindow._refresh_derived_state_after_restore(stub)
        return stub

    def test_mask_snapshot_carries_structural_bytes(self):
        from main import MainWindow
        stub = self._make_stub()
        MainWindow._seed_undo_baseline(stub)
        baseline_bytes = stub._undo_stack[0]["pdf_bytes"]
        self.assertIsNotNone(baseline_bytes)

        # 模拟扫描完成：加遮罩后压 mask-only 快照
        stub.page_data[0] = {"ocr": [], "manual": []}
        stub.page_data[0]["ocr"].append(_make_hit(QRectF(1, 2, 3, 4), "X"))
        MainWindow._capture_undo_state(stub, structural=False)
        mask_snap = stub._undo_stack[-1]
        # S1 修复核心断言：mask-only 快照带结构字节引用（且与基线同对象，零拷贝）
        self.assertIsNotNone(mask_snap["pdf_bytes"])
        self.assertIs(mask_snap["pdf_bytes"], baseline_bytes)

    def test_scan_delete_undo_restores_page_count(self):
        from main import MainWindow
        stub = self._make_stub()
        MainWindow._seed_undo_baseline(stub)
        # 扫描（mask-only 快照）
        stub.page_data[0] = {"ocr": [_make_hit(QRectF(1, 2, 3, 4), "X")], "manual": []}
        MainWindow._capture_undo_state(stub, structural=False)
        # 删页（结构快照）：删第 2 页，页码数据同步收缩
        stub.doc.delete_page(1)
        stub.page_data = {k: v for k, v in stub.page_data.items() if k != 1}
        MainWindow._capture_undo_state(stub, structural=True)
        self.assertEqual(len(stub.doc), 2)
        # Ctrl+Z：应恢复到"扫描后、删页前"——3 页 + 遮罩仍在
        MainWindow.undo(stub)
        self.assertEqual(len(stub.doc), 3)
        self.assertIn(0, stub.page_data)
        self.assertEqual(len(stub.page_data[0]["ocr"]), 1)


if __name__ == "__main__":
    unittest.main()
