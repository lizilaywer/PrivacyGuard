# PrivacyGuard macOS 打包指南

> 完整的 macOS 应用打包、签名和发布指南

---

## 目录

1. [快速开始](#快速开始)
2. [环境准备](#环境准备)
3. [打包流程](#打包流程)
4. [代码签名](#代码签名)
5. [公证（Notarization）](#公证notarization)
6. [DMG 制作](#dmg-制作)
7. [自动更新](#自动更新)
8. [故障排除](#故障排除)

---

## 快速开始

### 一键打包

```bash
cd /Users/a49144/Desktop/临时coding/PrivacyApp
bash packaging/macos/scripts/build_macos_app.sh
```

打包完成后，文件位于：
- 应用包：`dist/PrivacyGuard.app`
- DMG 安装包：`releases/macos/PrivacyGuard-{版本}-macOS.dmg`

---

## 环境准备

### 系统要求

| 项目 | 要求 |
|------|------|
| macOS 版本 | 10.15+（推荐 12.0+） |
| Xcode | 命令行工具 |
| Python | 3.11+ |
| 磁盘空间 | 至少 5GB 可用空间 |

### 安装依赖

```bash
# 1. 安装 Xcode 命令行工具
xcode-select --install

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. 安装打包工具
pip install pyinstaller

# 5. 安装 DMG 制作工具（可选，用于美化 DMG）
brew install create-dmg
```

### 项目结构检查

确保项目结构如下：

```
PrivacyApp/
├── main.py                 # 主程序
├── theme.py                # 主题文件
├── requirements.txt        # 依赖列表
├── packaging/
│   └── macos/
│       ├── scripts/        # 打包脚本
│       │   ├── build_macos_app.sh
│       │   ├── sign_macos_app.sh
│       │   └── notarize_macos_app.sh
│       ├── config/         # 配置文件
│       │   ├── PrivacyGuard.spec
│       │   └── entitlements.plist
│       └── assets/         # 资源文件
│           └── PrivacyGuard.icns
└── venv/                   # 虚拟环境
```

---

## 打包流程

### 步骤 1: 准备工作

```bash
# 激活虚拟环境
source venv/bin/activate

# 更新版本号（修改 main.py 中的 VERSION 变量）
# 同时更新 build/PrivacyGuard.spec 中的版本号

# 清理旧构建
rm -rf build/build dist/
```

### 步骤 2: 执行打包

```bash
# 方式一：使用打包脚本（推荐）
bash packaging/macos/scripts/build_macos_app.sh

# 方式二：手动打包
pyinstaller --clean --noconfirm packaging/macos/config/PrivacyGuard.spec
```

### 步骤 3: 验证应用

```bash
# 检查应用结构
ls -la dist/PrivacyGuard.app/Contents/MacOS/
ls -la dist/PrivacyGuard.app/Contents/Resources/

# 检查依赖库
otool -L dist/PrivacyGuard.app/Contents/MacOS/PrivacyGuard

# 运行测试
open dist/PrivacyGuard.app
```

---

## 代码签名

### 为什么需要签名

| 场景 | 未签名 | 已签名 |
|------|--------|--------|
| 本地运行 | ⚠️ 需要右键允许 | ✅ 正常打开 |
| 分发下载 | ❌ 被 Gatekeeper 阻止 | ✅ 正常打开 |
| 用户信任 | 低（安全警告） | 高（显示开发者） |

### 申请开发者证书

1. **加入 Apple Developer Program**
   - 个人开发者：$99/年
   - 访问：https://developer.apple.com/programs/

2. **生成证书**
   ```bash
   # 打开 Xcode -> Preferences -> Accounts
   # 下载证书到钥匙串
   ```

3. **查看证书**
   ```bash
   # 列出可用证书
   security find-identity -p codesigning -v

   # 输出示例：
   # 1) XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX "Developer ID Application: Your Name (TEAM_ID)"
   ```

### 签名应用

```bash
# 基本签名
 codesign --force --deep --sign "Developer ID Application: Your Name (TEAM_ID)" \
     dist/PrivacyGuard.app

# 验证签名
 codesign --verify --verbose dist/PrivacyGuard.app

# 显示签名信息
 codesign -dvv dist/PrivacyGuard.app
```

### 签名脚本

签名脚本位于 `packaging/macos/scripts/sign_macos_app.sh`：

```bash
#!/bin/bash

APP_NAME="PrivacyGuard"
APP_PATH="dist/${APP_NAME}.app"
IDENTITY="Developer ID Application: Your Name (TEAM_ID)"  # 替换为你的证书

echo "🔏 正在签名应用..."

# 清理旧的签名
 codesign --remove-signature "${APP_PATH}" 2>/dev/null || true

# 逐个签名动态库（确保所有库都正确签名）
find "${APP_PATH}/Contents/MacOS" -name "*.dylib" -o -name "*.so" | while read lib; do
    echo "签名库: $lib"
     codesign --force --sign "${IDENTITY}" "$lib"
done

# 签名主可执行文件
 codesign --force --sign "${IDENTITY}" \
    --entitlements packaging/macos/config/entitlements.plist \
    "${APP_PATH}/Contents/MacOS/${APP_NAME}"

# 签名整个应用包
 codesign --force --deep --sign "${IDENTITY}" \
    --entitlements packaging/macos/config/entitlements.plist \
    "${APP_PATH}"

echo "✅ 签名完成"
echo ""
echo "验证签名:"
 codesign --verify --verbose "${APP_PATH}"
```

### 权限配置文件

权限配置文件位于 `packaging/macos/config/entitlements.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- 允许执行 JIT 编译（某些依赖需要） -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>

    <!-- 允许加载未签名的库（某些 Python 依赖需要） -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>

    <!-- 允许调试（可选） -->
    <key>com.apple.security.cs.debugger</key>
    <true/>

    <!-- 文件访问权限 -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
</dict>
</plist>
```

---

## 公证（Notarization）

### 什么是公证

公证是 Apple 对应用程序的安全扫描，确保：
- 不包含恶意代码
- 符合 macOS 安全标准
- 允许在任何 Mac 上运行

### 配置公证

1. **生成 App 专用密码**
   - 访问：https://appleid.apple.com/
   - 生成 App 专用密码（用于命令行上传）

2. **公证脚本**

公证脚本位于 `packaging/macos/scripts/notarize_macos_app.sh`：

```bash
#!/bin/bash

APP_NAME="PrivacyGuard"
VERSION="36.4"
DMG_NAME="${APP_NAME}-${VERSION}-macOS.dmg"
DMG_PATH="releases/${DMG_NAME}"

# Apple ID 和团队 ID
APPLE_ID="your.email@example.com"  # 替换为你的 Apple ID
TEAM_ID="XXXXXXXXXX"               # 替换为你的 Team ID
APP_PASSWORD="xxxx-xxxx-xxxx-xxxx" # 替换为 App 专用密码

echo "📤 正在上传应用进行公证..."

# 提交公证
xcrun notarytool submit "${DMG_PATH}" \
    --apple-id "${APPLE_ID}" \
    --team-id "${TEAM_ID}" \
    --password "${APP_PASSWORD}" \
    --wait

echo ""
echo "✅ 公证完成"
echo ""
echo " staple 公证凭证到 DMG..."
xcrun stapler staple "${DMG_PATH}"

echo ""
echo "验证 staple:"
xcrun stapler validate "${DMG_PATH}"
```

### 公证流程

```bash
# 1. 创建 DMG（见下节）
bash packaging/macos/scripts/build_macos_app.sh

# 2. 签名应用
bash packaging/macos/scripts/sign_macos_app.sh

# 3. 公证
bash packaging/macos/scripts/notarize_macos_app.sh
```

---

## DMG 制作

### 基础 DMG（已包含在打包脚本中）

```bash
# 创建临时目录
mkdir -p dmg_temp
cp -R dist/PrivacyGuard.app dmg_temp/
ln -s /Applications dmg_temp/

# 创建 DMG
hdiutil create -volname "PrivacyGuard" \
    -srcfolder dmg_temp \
    -ov \
    -format UDZO \
    releases/PrivacyGuard-36.4-macOS.dmg

# 清理
rm -rf dmg_temp
```

### 美化 DMG（使用 create-dmg）

```bash
# 安装工具
brew install create-dmg

# 创建美化 DMG
create-dmg \
    --volname "PrivacyGuard 脱敏卫士" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "PrivacyGuard.app" 150 150 \
    --hide-extension "PrivacyGuard.app" \
    --app-drop-link 450 150 \
    --background "build/dmg_background.png" \
    --eula "LICENSE.txt" \
    releases/PrivacyGuard-36.4-macOS.dmg \
    dist/PrivacyGuard.app
```

### DMG 背景图制作

1. 尺寸：600x400 像素
2. 格式：PNG
3. 内容：
   - 左侧：应用图标位置指示
   - 右侧：Applications 文件夹位置指示
   - 中间：箭头或文字说明

---

## 自动更新

### 方案一：Sparkle 框架（推荐）

1. **集成 Sparkle**

```python
# 在 main.py 中添加
import objc
from Foundation import NSBundle

class AutoUpdater:
    def __init__(self):
        self.sparkle = objc.loadBundle('Sparkle',
            bundle_path='/Library/Frameworks/Sparkle.framework',
            module_globals=globals())

    def check_for_updates(self):
        self.sparkle.SUUpdater.sharedUpdater().checkForUpdates_(None)
```

2. **配置 AppCast**

创建 `appcast.xml`：

```xml
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
  <channel>
    <title>PrivacyGuard 脱敏卫士</title>
    <item>
      <title>Version 36.4</title>
      <pubDate>Mon, 17 Feb 2026 12:00:00 +0800</pubDate>
      <sparkle:version>36.4</sparkle:version>
      <sparkle:shortVersionString>36.4</sparkle:shortVersionString>
      <sparkle:minimumSystemVersion>10.13</sparkle:minimumSystemVersion>
      <description><![CDATA[
        <h2>PrivacyGuard v36.4 更新</h2>
        <ul>
          <li>代码重构与性能优化</li>
          <li>PDF 资源管理改进</li>
          <li>界面细节优化</li>
        </ul>
      ]]}></description>
      <enclosure url="https://your-domain.com/releases/PrivacyGuard-36.4-macOS.dmg"
               sparkle:version="36.4"
               sparkle:shortVersionString="36.4"
               length="0"
               type="application/octet-stream"
               sparkle:edSignature="your-signature-here" />
    </item>
  </channel>
</rss>
```

### 方案二：手动检查更新

```python
def check_update_manual():
    """手动检查更新"""
    import urllib.request
    import json

    try:
        with urllib.request.urlopen('https://api.github.com/repos/yourname/PrivacyGuard/releases/latest', timeout=5) as response:
            data = json.loads(response.read())
            latest_version = data['tag_name'].lstrip('v')

            if latest_version > CURRENT_VERSION:
                return {
                    'has_update': True,
                    'version': latest_version,
                    'url': data['html_url'],
                    'notes': data['body']
                }
    except Exception:
        pass

    return {'has_update': False}
```

---

## 故障排除

### 问题 1: "应用已损坏，无法打开"

**原因**: Gatekeeper 阻止未签名/未公证应用

**解决**:
```bash
# 临时允许（不推荐长期使用）
sudo spctl --master-disable

# 或针对单个应用
xattr -cr /Applications/PrivacyGuard.app
```

### 问题 2: 动态库加载失败

**原因**: 依赖库未正确打包

**解决**:
```bash
# 检查缺失的库
DYLD_PRINT_LIBRARIES=1 dist/PrivacyGuard.app/Contents/MacOS/PrivacyGuard

# 手动复制缺失库
# 编辑 build/PrivacyGuard.spec 添加:
# binaries=[('path/to/lib.dylib', 'lib')]
```

### 问题 3: 应用体积过大

**优化方案**:

```python
# 在 spec 文件中排除不需要的模块
excludes=[
    'matplotlib',
    'pandas',
    'scipy',
    'IPython',
    'tkinter',
    'PyQt6.Qt3D',
    'PyQt6.QtMultimedia',
]

# 使用 UPX 压缩
# 在 Analysis 中添加:
upx=True,
upx_exclude=['vcruntime140.dll'],
```

### 问题 4: 公证失败

**常见原因**:
- 包含未签名的二进制文件
- 使用了禁止的 API
- 含有恶意软件特征

**排查**:
```bash
# 查看公证日志
xcrun notarytool log \
    --apple-id "your@email.com" \
    --team-id "TEAMID" \
    --password "app-password" \
    submission-id
```

---

## 打包检查清单

### 发布前检查

- [ ] 版本号已更新（main.py、spec 文件、Info.plist）
- [ ] 所有依赖已安装
- [ ] 应用可以在干净环境运行
- [ ] 代码已签名（如使用开发者证书）
- [ ] 已公证（如需要分发）
- [ ] DMG 可以正常挂载和安装
- [ ] 校验和已生成
- [ ] 更新日志已编写

### 文件清单

```
releases/
├── PrivacyGuard-36.4-macOS.dmg
├── PrivacyGuard-36.4-macOS.dmg.sha256
├── appcast.xml
└── release-notes.md
```

---

## 相关资源

- [PyInstaller 文档](https://pyinstaller.readthedocs.io/)
- [Apple 代码签名指南](https://developer.apple.com/documentation/xcode/codesigning)
- [Apple 公证指南](https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution)
- [create-dmg 工具](https://github.com/create-dmg/create-dmg)
- [Sparkle 框架](https://sparkle-project.org/)

---

**最后更新**: 2026-02-17
**版本**: v36.4
**维护者**: 汪立
