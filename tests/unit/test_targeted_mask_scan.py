# -*- coding: utf-8 -*-
"""cp65 目标扫描/手动框选全文遮罩纯逻辑单元测试（脱离 GUI 运行）。

覆盖 _start_targeted_mask_scan / _on_targeted_page_result 抽取出的模块级函数：
- build_targeted_keyword_rules: 关键词规则构造（find→replace 逐词对齐）
- format_targeted_terms_preview: 信息栏预览文案
- merge_targeted_hits: 命中合并（重叠 >50% 跳过、已接纳命中参与后续判重）
"""
import unittest

from PyQt6.QtCore import QRectF

from main import (
    build_targeted_keyword_rules,
    format_targeted_terms_preview,
    merge_targeted_hits,
    rects_overlap_ratio,
    _make_hit,
)


class TestBuildTargetedKeywordRules(unittest.TestCase):
    def test_each_term_maps_to_replace_text(self):
        rules = build_targeted_keyword_rules(["张三", "李四"], "某人")
        self.assertEqual(rules, [
            {"enabled": True, "find": "张三", "replace": "某人"},
            {"enabled": True, "find": "李四", "replace": "某人"},
        ])

    def test_empty_terms_returns_empty(self):
        self.assertEqual(build_targeted_keyword_rules([], "某人"), [])

    def test_empty_replace_means_pure_mask(self):
        rules = build_targeted_keyword_rules(["张三"], "")
        self.assertEqual(rules[0]["replace"], "")
        self.assertTrue(rules[0]["enabled"])


class TestFormatTargetedTermsPreview(unittest.TestCase):
    def test_within_limit_no_ellipsis(self):
        self.assertEqual(format_targeted_terms_preview(["甲", "乙", "丙"]), "甲、乙、丙")

    def test_over_limit_truncated_with_ellipsis(self):
        self.assertEqual(format_targeted_terms_preview(["甲", "乙", "丙", "丁"]), "甲、乙、丙…")

    def test_single_term(self):
        self.assertEqual(format_targeted_terms_preview(["甲"]), "甲")

    def test_empty_terms(self):
        self.assertEqual(format_targeted_terms_preview([]), "")


class TestMergeTargetedHits(unittest.TestCase):
    def test_non_overlapping_all_accepted(self):
        candidates = [_make_hit(QRectF(0, 0, 10, 10), "A"),
                      _make_hit(QRectF(100, 100, 10, 10), "B")]
        accepted = merge_targeted_hits(candidates, [])
        self.assertEqual(len(accepted), 2)

    def test_overlap_with_existing_skipped(self):
        existing = [QRectF(0, 0, 10, 10)]
        # 与已有矩形完全重合（重叠比 1.0 > 0.5）→ 跳过
        candidates = [_make_hit(QRectF(0, 0, 10, 10), "A")]
        self.assertEqual(merge_targeted_hits(candidates, existing), [])

    def test_partial_overlap_below_threshold_accepted(self):
        existing = [QRectF(0, 0, 10, 10)]
        # 重叠区 4x10=40，较小面积 100 → 0.4 ≤ 0.5 → 接纳
        candidates = [_make_hit(QRectF(6, 0, 10, 10), "A")]
        self.assertEqual(len(merge_targeted_hits(candidates, existing)), 1)

    def test_accepted_hit_joins_dedup_set(self):
        # 两个互相重叠的候选：第一个被接纳后，第二个应因与其重叠被跳过
        candidates = [_make_hit(QRectF(0, 0, 10, 10), "A"),
                      _make_hit(QRectF(1, 1, 10, 10), "B")]
        accepted = merge_targeted_hits(candidates, [])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["replace_text"], "A")

    def test_none_rect_candidate_ignored(self):
        accepted = merge_targeted_hits([{"rect": None, "replace_text": "A"}], [])
        self.assertEqual(accepted, [])

    def test_none_in_existing_rects_ignored(self):
        candidates = [_make_hit(QRectF(0, 0, 10, 10), "A")]
        accepted = merge_targeted_hits(candidates, [None, QRectF(100, 100, 5, 5)])
        self.assertEqual(len(accepted), 1)

    def test_bare_qrectf_candidate_supported(self):
        # 兼容裸 QRectF 命中项（_hit_rect 双形态）
        accepted = merge_targeted_hits([QRectF(0, 0, 10, 10)], [])
        self.assertEqual(len(accepted), 1)
        self.assertIsInstance(accepted[0], QRectF)

    def test_custom_threshold_strictly_greater(self):
        existing = [QRectF(0, 0, 10, 10)]
        # 重叠比恰为 0.4：threshold=0.4 时不满足“严格大于”→ 接纳
        candidates = [_make_hit(QRectF(6, 0, 10, 10), "A")]
        self.assertEqual(
            len(merge_targeted_hits(candidates, existing, overlap_threshold=0.4)), 1)
        # threshold=0.39 时 0.4 > 0.39 → 跳过
        self.assertEqual(
            merge_targeted_hits(candidates, existing, overlap_threshold=0.39), [])

    def test_origin_rect_semantics(self):
        # 模拟 _on_targeted_page_result：原框选区域计入 existing，命中与其重合应跳过
        origin = QRectF(50, 50, 20, 10)
        candidates = [_make_hit(QRectF(50, 50, 20, 10), "A"),
                      _make_hit(QRectF(200, 200, 20, 10), "B")]
        accepted = merge_targeted_hits(candidates, [origin])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["replace_text"], "B")


class TestRectsOverlapRatioBoundary(unittest.TestCase):
    """merge_targeted_hits 依赖的重叠比在边界输入下应稳定。"""

    def test_zero_area_rect_returns_zero(self):
        self.assertEqual(rects_overlap_ratio(QRectF(0, 0, 0, 0), QRectF(0, 0, 10, 10)), 0.0)

    def test_none_returns_zero(self):
        self.assertEqual(rects_overlap_ratio(None, QRectF(0, 0, 10, 10)), 0.0)

    def test_identical_rects_ratio_one(self):
        r = QRectF(0, 0, 10, 10)
        self.assertAlmostEqual(rects_overlap_ratio(r, QRectF(r)), 1.0)


if __name__ == "__main__":
    unittest.main()
