# PrivacyGuard macOS 打包指南

> 当前 active macOS 打包流程说明。本文档以 `packaging/macos/` 下现有脚本和配置为准。

## v40.2.5 当前便携流程（2026-10-24）

本节取代下方旧 DMG 环境/版本说明；旧章节仅保留作历史参考。

```bash
bash packaging/macos/scripts/build_portable.sh
```

- 使用 `venv_macos_release/bin/python3`；可通过 `PRIVACYGUARD_PYTHON` 指定另一套独立发布解释器。
- 本轮采用 CPython 3.13.2（构建 target 13.0）及 requirements.txt 锁定运行依赖；实际包要求 macOS 14+ / Apple Silicon。
- 输出 `releases/macos/PrivacyGuard-<version>-macOS-arm64-portable.zip`、SHA256、全包二进制验证 JSON。
- 新入口不依赖 activate，不删除跨平台 dist/build，不自动下载依赖，不剥除包内运行代码，不夹带个人 config.json。
- 配置和日志写 `~/Library/Application Support/PrivacyGuard/`；应用包保持不可变。
- 必须检查全部 Mach-O 的 minOS 与外部链接，不能仅看 pyexpat 或改 Info.plist。可选 Tk/readline/_decimal 的宿主库已排除，Decimal 使用标准库纯 Python 回退。
- ad-hoc 签名不是 Developer ID/Apple 公证。旧 sign/notarize 路径需单独在有证书环境中验证，不属于本次交付。
- 原生自检：`PrivacyGuard.app/Contents/MacOS/PrivacyGuard --self-test`（仅合成数据，禁止网络连接）。
- 完整审计记录：`docs/current/RELEASE_AUDIT_20261024.md`。

---

## 当前发布基线

- 当前版本：`v37.7.19`
- 版本标识：`37.7.19`
- 版本唯一来源：项目根目录 `version.txt`

---

## 快速开始

### 推荐完整流程

```bash
cd /Users/a49144/Desktop/codexhub/PrivacyGuardApp
bash packaging/macos/scripts/build_complete.sh
```

输出：

- 优先：`releases/macos/PrivacyGuard-<version>-macOS.dmg`
- 优先：`releases/macos/PrivacyGuard-<version>-macOS.dmg.sha256`
- 回退：`releases/macos/PrivacyGuard.app`

这是当前 **macOS 正式发布默认入口**。

### 简化构建

```bash
bash packaging/macos/scripts/build_macos_app.sh
```

输出：

- `dist/PrivacyGuard.app`
- `releases/macos/PrivacyGuard-<version>-macOS.dmg`

---

## 当前脚本分工

| 脚本 | 作用 |
|------|------|
| `build_complete.sh` | 完整发布流程，优先 `create-dmg`，缺失时回退到 `hdiutil` |
| `build_macos_app.sh` | 最小化打包流程，直接生成 `.app` 和标准 DMG |
| `sign_macos_app.sh` | 对 `.app` 做 Developer ID 签名 |
| `notarize_macos_app.sh` | 对 DMG 执行 notarization 并 stapler |

---

## 构建前要求

- macOS 10.15+
- Xcode Command Line Tools
- Python 3.11+
- 推荐虚拟环境：`venvmac`，兼容 `venv`

常用准备命令：

```bash
xcode-select --install
python3 -m venv venvmac
source venvmac/bin/activate
pip install -r requirements.txt
pip install pyinstaller
brew install create-dmg
```

`create-dmg` 不是必须项；缺失时 `build_complete.sh` 会回退到 `hdiutil`。

## 当前打包执行约定

- 先激活 `venvmac` / `venv`，再通过 `python3 -m PyInstaller` 执行打包
- PyInstaller 缓存固定到项目内：

```text
build/.pyinstaller-cache
```

- 这样可以避免依赖用户目录下的全局 PyInstaller 缓存

---

## 版本来源

- `version.txt` 是唯一版本源
- `packaging/macos/config/PrivacyGuard.spec` 从 `version.txt` 动态读取：
  - `CFBundleVersion`
  - `CFBundleShortVersionString`

因此发布前不再需要手动同步 spec 内部版本号。

---

## 推荐发布流程

### 1. 生成 DMG

```bash
bash packaging/macos/scripts/build_complete.sh
```

### 2. 可选：开发者签名

```bash
export PRIVACYGUARD_CODESIGN_IDENTITY="Developer ID Application: Example Corp (TEAMID)"
bash packaging/macos/scripts/sign_macos_app.sh
```

### 3. 可选：Apple 公证

方式一，优先推荐 keychain profile：

```bash
export PRIVACYGUARD_NOTARY_PROFILE="privacyguard-notary"
bash packaging/macos/scripts/notarize_macos_app.sh
```

方式二，直接用环境变量：

```bash
export PRIVACYGUARD_APPLE_ID="you@example.com"
export PRIVACYGUARD_APP_SPECIFIC_PASSWORD="app-specific-password"
export PRIVACYGUARD_TEAM_ID="TEAMID"
bash packaging/macos/scripts/notarize_macos_app.sh
```

---

## 本轮说明

- macOS 打包脚本现在统一绑定当前虚拟环境中的 PyInstaller
- `build_complete.sh` 缺少 `create-dmg` 时会回退到 `hdiutil`，若 DMG 仍失败则保底复制 `.app` 到 `releases/macos/`
- 本轮已验证完整脚本执行到 `.app` 产物生成和发布目录落盘
- 当前默认正式入口已收口为：`bash packaging/macos/scripts/build_complete.sh`
- 当前机器上的真实结果：
  - `build_complete.sh` 已成功生成 `dist/PrivacyGuard.app`
  - 当前环境缺少 `create-dmg`
  - `hdiutil: create failed - 设备未配置`
  - 脚本已按预期保底复制 `releases/macos/PrivacyGuard.app`
- 如果要对外正式分发，仍建议做 Developer ID 签名与公证

---

## 发布前检查清单

- `version.txt` 已更新
- `build_complete.sh` 已成功执行
- `releases/macos/PrivacyGuard-<version>-macOS.dmg` 已生成，或已按回退逻辑生成 `releases/macos/PrivacyGuard.app`
- 若 `.dmg` 已生成，对应 `.sha256` 已生成
- 本机至少成功打开一次 `.app` 或挂载一次 `.dmg`
- 若用于外发，签名与公证流程已跑通

最后更新：2026-03-18
