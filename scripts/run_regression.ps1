# cp87(D3): 全量单元回归 —— 自动发现 tests/unit 下全部 test_*.py
# 用法: .\scripts\run_regression.ps1  （在项目根目录执行）
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root "venv_win\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

# 经 cmd 合并 stderr（unittest 摘要输出在 stderr，直接 2>&1 会被 PS 包装成错误记录）
cmd /c "`"$py`" -m compileall -q main.py theme.py privacyguard tests 2>&1"
if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] compileall"; exit 1 }

cmd /c "`"$py`" -m unittest discover -s tests/unit -t . -p test_*.py 2>&1" |
    Select-String -Pattern '^Ran |^OK|^FAILED|FAIL:|ERROR:'
exit $LASTEXITCODE
