"""PII 命中去重 + 跨 recognizer 优先级解析（ENGINE-04）。"""
from typing import Dict, List

from privacyguard.pii.hits import PIIHit


# D-09 双 type 契约：CN_USCC + CN_TAXPAYER_ID 共享同一个 (offset, length) 区域，
# 故意保留两份命中，使 UI 既展示「统一社会信用代码」也可展示「纳税人识别号(18位)」。
# 引擎层 mask_strategy 完全一致（mask_for_entity 联合分派）。
_D09_DUAL_TYPE_PAIRS: frozenset = frozenset({
    frozenset({"CN_USCC", "CN_TAXPAYER_ID"}),
})


def resolve(hits: List[PIIHit]) -> List[PIIHit]:
    """同 (page_offset, page_length) 范围内只保留一份。

    Phase 1 单 recognizer：同位置只可能来自同一正则路径；保留
    validator_passed=True 的命中（移除 validator_failed=False 的 MEDIUM 重复）。

    D-09 特殊豁免：CN_USCC + CN_TAXPAYER_ID 双 type 对故意保留两份（共用 18-位
    区域，但分别给 UI 展示两种业务语义）。其余同位置冲突按 validator_passed
    优先级裁决。

    返回按 (page_offset, page_length) 排序。
    """
    if not hits:
        return []
    by_pos: Dict[tuple, List[PIIHit]] = {}
    for hit in hits:
        key = (hit.page_offset, hit.page_length)
        by_pos.setdefault(key, []).append(hit)
    out: List[PIIHit] = []
    for key, group in by_pos.items():
        if len(group) == 1:
            out.append(group[0])
            continue
        # 多命中同位置：
        # 1. D-09 双 type 对直接全部保留
        types = {h.entity_type for h in group}
        if len(group) == 2 and frozenset(types) in _D09_DUAL_TYPE_PAIRS:
            out.extend(group)
        else:
            # 2. 其他冲突按 validator_passed=True 优先
            passed = [h for h in group if h.validator_passed]
            if passed:
                out.append(passed[0])
            else:
                out.append(group[0])
    return sorted(out, key=lambda h: (h.page_offset, h.page_length))


__all__ = ['resolve']
