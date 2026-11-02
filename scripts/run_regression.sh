#!/bin/bash
# cp87(D3): 全量单元回归 —— 自动发现 tests/unit 下全部 test_*.py
# 用法: ./scripts/run_regression.sh （在项目根目录执行）
set -euo pipefail
cd "$(dirname "$0")/.."

PY="python3"
[ -x "venv_macos_release/bin/python3" ] && PY="venv_macos_release/bin/python3"
[ -x "venvmac/bin/python3" ] && PY="venvmac/bin/python3"

$PY -m compileall -q main.py theme.py privacyguard tests
$PY -m unittest discover -s tests/unit -t . -p "test_*.py" -v 2>&1 | \
    grep -E '^Ran |^OK|^FAILED|FAIL:|ERROR:'
