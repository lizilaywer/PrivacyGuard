"""cp67: 页面视图页面操作纯函数测试（旋转变换/插入删除重排/列数钳制）。

从 main 导入纯函数（不实例化 QApplication）。
"""

import unittest

from main import (
    transform_hit_rect_for_rotation,
    shift_page_data_for_insert,
    shift_page_data_for_delete,
    shift_page_set_for_insert,
    shift_page_set_for_delete,
    clamp_grid_columns,
)


class TestTransformHitRectForRotation(unittest.TestCase):
    """旋转坐标变换（W=200,H=100 便于分辨宽高互换）。"""

    def test_cw90(self):
        # (x=10,y=20,w=30,h=10) 右转 90 -> (H-y-h, x, h, w) = (70,10,10,30)
        self.assertEqual(
            transform_hit_rect_for_rotation(10, 20, 30, 10, 200, 100, 90),
            (70, 10, 10, 30),
        )

    def test_ccw90(self):
        # 左转 90（270）-> (y, W-x-w, h, w) = (20,160,10,30)
        self.assertEqual(
            transform_hit_rect_for_rotation(10, 20, 30, 10, 200, 100, 270),
            (20, 160, 10, 30),
        )

    def test_180(self):
        # (W-x-w, H-y-h, w, h) = (160,70,30,10)
        self.assertEqual(
            transform_hit_rect_for_rotation(10, 20, 30, 10, 200, 100, 180),
            (160, 70, 30, 10),
        )

    def test_zero_and_360_identity(self):
        r = (10, 20, 30, 10)
        self.assertEqual(transform_hit_rect_for_rotation(*r, 200, 100, 0), r)
        self.assertEqual(transform_hit_rect_for_rotation(*r, 200, 100, 360), r)

    def test_cw90_then_ccw90_roundtrip(self):
        """右转 90 后再左转 90（此时页宽高已互换）应回到原位。"""
        W, H = 200, 100
        x, y, w, h = 10, 20, 30, 10
        nx, ny, nw, nh = transform_hit_rect_for_rotation(x, y, w, h, W, H, 90)
        # 旋转后页尺寸互换为 (H, W)=(100,200)
        bx, by, bw, bh = transform_hit_rect_for_rotation(nx, ny, nw, nh, H, W, 270)
        self.assertEqual((bx, by, bw, bh), (x, y, w, h))

    def test_180_is_involution(self):
        """180 变换两次回到原位。"""
        W, H = 200, 100
        r = (10, 20, 30, 10)
        once = transform_hit_rect_for_rotation(*r, W, H, 180)
        twice = transform_hit_rect_for_rotation(*once, W, H, 180)
        self.assertEqual(twice, r)


class TestShiftPageData(unittest.TestCase):
    def _sample(self):
        # 用可辨识对象，验证引用保持
        return {
            0: {'ocr': ['a'], 'manual': []},
            1: {'ocr': ['b'], 'manual': []},
            2: {'ocr': ['c'], 'manual': []},
        }

    def test_insert_middle(self):
        data = self._sample()
        new = shift_page_data_for_insert(data, 1)
        self.assertEqual(sorted(new), [0, 1, 2, 3])
        self.assertEqual(new[0]['ocr'], ['a'])       # 前段不动
        self.assertEqual(new[1], {'ocr': [], 'manual': []})  # 新空页
        self.assertEqual(new[2]['ocr'], ['b'])       # 原 1 -> 2
        self.assertEqual(new[3]['ocr'], ['c'])       # 原 2 -> 3

    def test_insert_at_end(self):
        data = self._sample()
        new = shift_page_data_for_insert(data, 3)
        self.assertEqual(sorted(new), [0, 1, 2, 3])
        self.assertEqual(new[3], {'ocr': [], 'manual': []})

    def test_insert_preserves_reference(self):
        data = self._sample()
        ref = data[1]
        new = shift_page_data_for_insert(data, 0)
        self.assertIs(new[2], ref)  # 原 1 -> 2，仍是同一对象

    def test_delete_single(self):
        data = self._sample()
        new = shift_page_data_for_delete(data, [1])
        self.assertEqual(sorted(new), [0, 1])
        self.assertEqual(new[0]['ocr'], ['a'])
        self.assertEqual(new[1]['ocr'], ['c'])  # 原 2 -> 1

    def test_delete_multiple(self):
        data = self._sample()
        new = shift_page_data_for_delete(data, [0, 2])
        self.assertEqual(sorted(new), [0])
        self.assertEqual(new[0]['ocr'], ['b'])

    def test_delete_first_and_last(self):
        data = self._sample()
        new = shift_page_data_for_delete(data, [0])
        self.assertEqual(new[0]['ocr'], ['b'])
        self.assertEqual(new[1]['ocr'], ['c'])


class TestShiftPageSet(unittest.TestCase):
    def test_insert_shifts_scanned_pages(self):
        self.assertEqual(shift_page_set_for_insert({0, 1, 2}, 1), {0, 2, 3})

    def test_insert_new_page_not_added(self):
        # 新页 1 不在结果里（未扫描）
        self.assertNotIn(1, shift_page_set_for_insert({0, 2}, 1))

    def test_delete_shifts_scanned_pages(self):
        self.assertEqual(shift_page_set_for_delete({0, 1, 2}, [1]), {0, 1})

    def test_delete_removes_target(self):
        self.assertEqual(shift_page_set_for_delete({0, 1, 2}, [0, 2]), {0})

    def test_empty_set(self):
        self.assertEqual(shift_page_set_for_insert(set(), 0), set())
        self.assertEqual(shift_page_set_for_delete(set(), [0]), set())


class TestClampGridColumns(unittest.TestCase):
    def test_wide_viewport_allows_many(self):
        # 1000px / (160+14) ≈ 5 列上限
        self.assertEqual(clamp_grid_columns(3, 1000), 3)

    def test_desired_exceeds_max_clamped(self):
        cols = clamp_grid_columns(99, 1000)
        self.assertLessEqual(cols, 6)
        self.assertGreaterEqual(cols, 1)

    def test_narrow_viewport_at_least_one(self):
        self.assertEqual(clamp_grid_columns(4, 100), 1)

    def test_desired_below_one_clamped_to_one(self):
        self.assertEqual(clamp_grid_columns(0, 1000), 1)
        self.assertEqual(clamp_grid_columns(-5, 1000), 1)


if __name__ == "__main__":
    unittest.main()
