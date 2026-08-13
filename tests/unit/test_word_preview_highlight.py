"""Phase 3 (03-word) — 双栏对比预览 PII 高亮 + merge function PII 接入测试 (D-01/D-02/D-15 #4).

锁:
- merge_word_matches_with_priority 扩展 pii_matches 形参 (D-01)
- PII 后追加在 ocr 之前, 同层重叠 PII 胜出 OCR (D-02 校验位质量 > OCR 文本层)
- 越界 PII (start<0 或 end>text_len) 由 _append_candidates 静默 drop (Pitfall 5 + cp27)
- _build_word_original_preview_fragment 渲染 source='pii' 时使用 'pii-highlight' css_class
  (UI-SPEC §Color) + title='[PII] {entity_type}' (UI-SPEC §Copywriting)
- rule / manual 在重叠区仍胜出 PII (优先级: rule > manual > ocr ∪ pii)
- _build_word_*_panel_updates 注入 pii_matches=word_data[key]['pii'] (D-01)

不变量 (D-17):
- tests.unit.test_word_replace_rules + test_batch_word_replace 不被破坏
- tests.unit.test_word_pii_adapter + test_word_worker_pii (Plan 1/2) 全部 PASS
- cp27 DOM patch 边界 (data-key/data-start/data-end 数值合法) 保持
"""
import unittest
from types import MethodType, SimpleNamespace

from main import (
    MainWindow,
    merge_word_matches_with_priority,
)
from privacyguard.pii.hits import PIIHit


# ----------------------------------------------------------------------
# Test factory helpers
# ----------------------------------------------------------------------
def _make_pii_hit(
    entity_type="CN_ID_CARD",
    char_offset=0,
    char_length=11,
    confidence_tier="HIGH",
    source="text",
    mask_strategy="138****5678",
    normalized="13812345678",
    validator_passed=True,
    text=None,
):
    """构造一个 PIIHit 用于 merge function 测试 (D-10: page_offset/page_length 在 Word 端复用)."""
    return PIIHit(
        entity_type=entity_type,
        page_offset=char_offset,                    # 复用 D-10: 存 char_offset
        page_length=char_length,                    # 复用 D-10: 存 char_length
        page_rect=(0.0, 0.0, 66.0, 12.0),
        confidence_tier=confidence_tier,
        source=source,
        mask_strategy=mask_strategy,
        normalized=normalized,
        validator_passed=validator_passed,
    ) if text is None else PIIHit(
        entity_type=entity_type,
        page_offset=char_offset,
        page_length=char_length,
        page_rect=(0.0, 0.0, 66.0, 12.0),
        confidence_tier=confidence_tier,
        source=source,
        mask_strategy=mask_strategy,
        normalized=normalized,
        validator_passed=validator_passed,
    )


def _build_pii_highlight_stub(pii_hits=None, ocr_hits=None, manual_hits=None, rules=None, replacement_text="[已脱敏]"):
    """构造一个用于 _build_word_original_preview_fragment 测试的 stub.

    沿用 test_word_replace_rules.build_word_preview_stub 的 SimpleNamespace 形态,
    补 pii 字段以验证 Task 2 接入.
    """
    stub = SimpleNamespace(
        word_data={
            "paragraph_0": {
                "text": "甲方 张三 13812345678",
                "manual": list(manual_hits or []),
                "ocr": list(ocr_hits or []),
                "pii": list(pii_hits or []),
            }
        },
        word_replace_rules=list(rules or []),
        replacement_text=replacement_text,
    )
    stub._build_word_original_preview_fragment = MethodType(
        MainWindow._build_word_original_preview_fragment, stub
    )
    stub._build_word_replaced_preview_html = MethodType(
        MainWindow._build_word_replaced_preview_html, stub
    )
    return stub


# ----------------------------------------------------------------------
# Test 1: merge function PII 接入
# ----------------------------------------------------------------------
class TestMergeWithPii(unittest.TestCase):
    """D-01/D-02: merge_word_matches_with_priority 接受 pii_matches 形参,
    PII 命中并入 'ocr ∪ pii' 层, 重叠区 PII 胜出 OCR (校验位质量).
    """

    def test_pii_added_to_merged_result(self):
        """D-01: PII 命中独立追加到 merged 结果 (source='pii')."""
        text = "前面 13812345678 后面"
        pii = [_make_pii_hit(char_offset=3, char_length=11, mask_strategy="138****5678")]

        merged = merge_word_matches_with_priority(
            text, [], "[默认]",
            pii_matches=pii,
        )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source"], "pii")
        self.assertEqual(merged[0]["start"], 3)
        self.assertEqual(merged[0]["end"], 14)
        self.assertEqual(merged[0]["replacement"], "138****5678")

    def test_pii_wins_over_ocr_on_overlap(self):
        """D-02: PII 校验位质量 > OCR 文本层, 重叠区 PII 胜出."""
        text = "13812345678"
        ocr = [{"start": 0, "end": 11, "text": "13812345678", "replacement": "[OCR]"}]
        pii = [_make_pii_hit(char_offset=0, char_length=11, mask_strategy="138****5678")]

        merged = merge_word_matches_with_priority(
            text, [], "[默认]",
            ocr_matches=ocr, pii_matches=pii,
        )

        # 期望: PII 占用区间, OCR 因重叠被 _append_candidates 跳过
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source"], "pii")
        self.assertEqual(merged[0]["replacement"], "138****5678")

    def test_pii_out_of_range_dropped_silently(self):
        """Pitfall 5 + cp27: 越界 PII (start<0 或 end>text_len 或 start>=end) 静默 drop."""
        text = "13812345678"
        # 全部 3 个越界场景
        pii = [
            _make_pii_hit(entity_type="CN_PHONE", char_offset=-1, char_length=11),
            _make_pii_hit(entity_type="CN_PHONE", char_offset=0, char_length=100),  # end > text_len
            _make_pii_hit(entity_type="CN_PHONE", char_offset=5, char_length=0),    # start >= end
        ]

        merged = merge_word_matches_with_priority(
            text, [], "[默认]",
            pii_matches=pii,
        )

        # 期望: merged 是空列表 (全部越界被 _append_candidates drop)
        self.assertEqual(merged, [])


# ----------------------------------------------------------------------
# Test 2: merge function 优先级 — rule / manual 仍胜 PII
# ----------------------------------------------------------------------
class TestMergePriorityPiiOverOCR(unittest.TestCase):
    """D-01 锁定优先级: rule > manual > (ocr ∪ pii). PII 仅在同层与 OCR 竞争时胜出."""

    def test_rule_wins_over_pii_on_overlap(self):
        """rule 优先级高于 PII; 重叠区 rule 胜出."""
        text = "13812345678"
        rules = [{"enabled": True, "mode": "exact", "find": "13812345678", "replace": "[规则]"}]
        pii = [_make_pii_hit(char_offset=0, char_length=11, mask_strategy="138****5678")]

        merged = merge_word_matches_with_priority(
            text, rules, "[默认]",
            pii_matches=pii,
        )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source"], "rule")
        self.assertEqual(merged[0]["replacement"], "[规则]")

    def test_manual_wins_over_pii_on_overlap(self):
        """manual 优先级高于 PII; 重叠区 manual 胜出."""
        text = "13812345678"
        manual = [{"start": 0, "end": 11, "replacement": "[手动]"}]
        pii = [_make_pii_hit(char_offset=0, char_length=11, mask_strategy="138****5678")]

        merged = merge_word_matches_with_priority(
            text, [], "[默认]",
            manual_matches=manual, pii_matches=pii,
        )

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source"], "manual")
        self.assertEqual(merged[0]["replacement"], "[手动]")


# ----------------------------------------------------------------------
# Test 3: 双栏预览 pii-highlight css_class + title 契约
# ----------------------------------------------------------------------
class TestPiiHighlightMarkup(unittest.TestCase):
    """UI-SPEC §Color + §Copywriting 契约: source='pii' 渲染 'pii-highlight' + '[PII] {entity_type}' title."""

    def test_pii_highlight_className_is_emitted(self):
        """_build_word_original_preview_fragment 渲染 source='pii' 时使用 'pii-highlight' css_class."""
        pii = [_make_pii_hit(
            entity_type="CN_ID_CARD",
            char_offset=3,
            char_length=11,
            mask_strategy="138****5678",
        )]
        stub = _build_pii_highlight_stub(pii_hits=pii)

        fragment = stub._build_word_original_preview_fragment(
            "paragraph_0", "张三 13812345678",
            merge_word_matches_with_priority(
                "张三 13812345678", [], "[默认]",
                pii_matches=pii,
            ),
        )

        self.assertIn('class="pii-highlight"', fragment)
        self.assertNotIn('class="manual-highlight"', fragment)
        self.assertNotIn('class="ocr-highlight"', fragment)

    def test_pii_highlight_title_uses_entity_type(self):
        """title 属性按 UI-SPEC §Copywriting: '[PII] {entity_type}' 形态."""
        pii = [_make_pii_hit(
            entity_type="CN_ID_CARD",
            char_offset=3,
            char_length=11,
            mask_strategy="138****5678",
        )]
        stub = _build_pii_highlight_stub(pii_hits=pii)

        fragment = stub._build_word_original_preview_fragment(
            "paragraph_0", "张三 13812345678",
            merge_word_matches_with_priority(
                "张三 13812345678", [], "[默认]",
                pii_matches=pii,
            ),
        )

        self.assertIn('title="[PII] CN_ID_CARD"', fragment)


# ----------------------------------------------------------------------
# Test 4: 越界 PII 静默 drop 不破坏 cp27 DOM patch 边界
# ----------------------------------------------------------------------
class TestNoOverflowGuard(unittest.TestCase):
    """Pitfall 5: 越界 PII 由 _append_candidates 静默 drop, 不破坏 DOM patch 边界."""

    def test_pii_negative_offset_returns_empty_merged(self):
        """PIIHit.page_offset = -1 (越界) 时 merge 应返回空列表."""
        text = "13812345678"
        pii = [_make_pii_hit(char_offset=-1, char_length=11)]

        merged = merge_word_matches_with_priority(
            text, [], "[默认]",
            pii_matches=pii,
        )

        self.assertEqual(merged, [])


if __name__ == "__main__":
    unittest.main()
