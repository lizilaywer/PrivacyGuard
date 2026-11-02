# 定版检查清单（RELEASE CHECKLIST）

cp89(D5): 每次定版（vX.Y.Z）按序执行，防漏步。

## 1. 回归锁基线

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_regression.ps1
```

- 必须 `OK`（允许既定 skip）；记录 `Ran N` 数字与上一基线对比，增减须能解释

## 2. 版本号（两处）

- `version.txt` → 新版本号（唯一来源）
- 运行 `python packaging/windows/scripts/generate_version_info.py` 自动生成 `version_info.txt`，禁止手工修改版本资源

## 3. 文档同步（7 份）

| 文件 | 更新内容 |
|---|---|
| CHANGELOG.md | 新版本段（cp 编号 + 功能/修复 + 质量 + 文件汇总） |
| docs/current/STATUS.md | 版本/状态行 + 发布概要段 |
| docs/current/DEV_LOG.md | 项目信息 + 日志段 |
| AGENTS.md | Status 行 + 能力清单 + 基线数字 |
| CLAUDE.md | Status 行 + 能力 + 基线数字 |
| docs/current/AGENT_CONTEXT.md | 能力详解 + 检查点条目 |

## 4. rollback_journal.md

- 本批次各 cp 条目：backup 位置 / changes / verification / rollback 步骤

## 5. 提交

```powershell
$env:PATH += ';C:\Program Files\Git\bin'
git add -A
git diff --cached --name-only   # 核验无杂物（测试产物/临时文件）
git commit -m "vX.Y.Z: ..."     # 消息含 cp 编号；被沙箱误判时用 git commit -F 消息文件
git tag vX.Y.Z                  # cp89 起每次定版打 tag（回滚锚点）
```

## 6. 提交后

- `git status` 干净
- 未推送远程（用户说 push 才 push）

## macOS 便携门禁（v40.2.5）

- 使用 `build_portable.sh` 的独立解释器，不能靠失效 activate 回退宿主 Python。
- 全包 Mach-O minOS <= Info.plist 声明，且无 /opt/homebrew、/Users 等外部私有绝对依赖。
- 不含 config.json、日志、草稿；正常启动之后签名仍有效。
- ZIP 必须解压复验签名并执行 `--self-test`；只通过源码单测不够。
- 报告明确已知扫描盲区、真机系统范围、是否公证；没有用户授权不为完成清单自动提交/推送。
