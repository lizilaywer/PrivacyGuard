# Legacy 测试归档

cp87(D3): unittest discover 接管全量回归时发现的陈旧失效测试，
针对已重构/已移除的旧算法（如 B 档宽度估算 cp46 已移除、dedup cp43/45 已重构）。
保留备考，不参与 discover（discover 仅扫描 tests/unit）。

- test_ocr_substring_precision_v2.py — cp35 时代 F 修复系列
- test_ocr_substring_precision_v3.py — cp36-38 时代 F 修复系列
