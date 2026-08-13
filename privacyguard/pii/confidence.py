"""PII 命中置信度档位映射（ENGINE-03）。

HIGH: validator_passed == True 且符合 PII 引擎完整校验路径
MEDIUM: 正则匹配但 validator 未通过（如 OCR 误识导致校验位失败但长度对）
LOW: 仅模糊匹配（如纯正则命中但 entity_type 不在已知类型）
"""
from typing import Literal


ConfidenceTier = Literal["HIGH", "MEDIUM", "LOW"]


def classify_hit(validator_passed: bool, regex_matched: bool, source: str) -> ConfidenceTier:
    """分类置信度档位。"""
    if validator_passed and regex_matched:
        return "HIGH"
    if regex_matched:
        return "MEDIUM"
    return "LOW"


__all__ = ['ConfidenceTier', 'classify_hit']