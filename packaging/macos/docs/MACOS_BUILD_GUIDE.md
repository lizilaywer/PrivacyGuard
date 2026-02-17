# PrivacyGuard macOS 打包指南

## 快速开始

### 基础打包（无签名）

```bash
bash packaging/macos/scripts/build_macos_app.sh
```

输出：
- 应用：`dist/PrivacyGuard.app`
- DMG：`releases/macos/PrivacyGuard-36.4-macOS.dmg`

### 完整流程（签名 + 公证）

```bash
# 1. 打包
bash packaging/macos/scripts/build_macos_app.sh

# 2. 签名（修改脚本中的证书信息）
bash packaging/macos/scripts/sign_macos_app.sh

# 3. 重新打包 DMG（签名后的应用）
bash packaging/macos/scripts/build_macos_app.sh

# 4. 公证（修改脚本中的 Apple ID）
bash packaging/macos/scripts/notarize_macos_app.sh
```

## 目录结构

```
packaging/macos/
├── scripts/                    # 打包脚本
│   ├── build_macos_app.sh      # 主打包脚本
│   ├── sign_macos_app.sh       # 代码签名
│   ├── notarize_macos_app.sh   # 公证
│   └── README.txt
├── config/                     # 配置文件
│   ├── PrivacyGuard.spec       # PyInstaller 配置
│   └── entitlements.plist      # 签名权限
└── assets/                     # 资源文件
    └── PrivacyGuard.icns       # 应用图标
```

## 先决条件

- macOS 10.13 或更高版本
- Python 3.11 或更高版本
- Xcode Command Line Tools

安装 Xcode 工具：
```bash
xcode-select --install
```

## 打包选项

| 脚本 | 用途 | 输出 |
|------|------|------|
| `build_macos_app.sh` | 打包应用和 DMG | `.app` + `.dmg` |
| `sign_macos_app.sh` | 代码签名 | 签名后的 `.app` |
| `notarize_macos_app.sh` | 提交 Apple 公证 | 公证后的 `.dmg` |

## 自定义配置

### 修改版本号

编辑：
1. `packaging/macos/config/PrivacyGuard.spec`（CFBundleVersion）
2. `packaging/macos/scripts/build_macos_app.sh`（VERSION 变量）

### 修改应用图标

替换文件：`packaging/macos/assets/PrivacyGuard.icns`

创建 ICNS 文件：
```bash
# 从 iconset 创建
iconutil -c icns icon.iconset -o PrivacyGuard.icns
```

### 修改 Info.plist

编辑 `packaging/macos/config/PrivacyGuard.spec` 中的 `info_plist` 字典。

## 输出文件

### 应用包

- **位置**：`dist/PrivacyGuard.app`
- **用途**：可直接运行或复制到 Applications
- **注意**：未签名版本首次运行需要右键打开

### DMG 安装包

- **位置**：`releases/macos/PrivacyGuard-{version}-macOS.dmg`
- **用途**：标准 macOS 安装包
- **内容**：应用 + Applications 快捷方式

## 代码签名

### 准备工作

1. 注册 [Apple Developer](https://developer.apple.com)（年费 $99）
2. 在 Xcode 中配置签名证书
3. 查看可用证书：
   ```bash
   security find-identity -v -p codesigning
   ```

### 配置签名脚本

编辑 `packaging/macos/scripts/sign_macos_app.sh`：

```bash
# 将证书名称替换为你的实际证书
CODESIGN_ID="Developer ID Application: Your Name (XXXXXXXXXX)"
```

### 执行签名

```bash
bash packaging/macos/scripts/sign_macos_app.sh
```

签名后的应用可以在任何 Mac 上打开，不会显示"无法验证开发者"警告。

## 公证（Notarization）

### 准备工作

1. 生成应用专用密码：
   - 访问 https://appleid.apple.com
   - 登录后选择"App 专用密码"
   - 生成新密码（格式：xxxx-xxxx-xxxx-xxxx）

2. 获取团队 ID：
   ```bash
   xcrun notarytool list-credentials
   ```

### 配置公证脚本

编辑 `packaging/macos/scripts/notarize_macos_app.sh`：

```bash
APPLE_ID="your-email@example.com"
APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
TEAM_ID="XXXXXXXXXX"
```

### 执行公证

```bash
bash packaging/macos/scripts/notarize_macos_app.sh
```

公证后的应用可以通过 Gatekeeper 检查，用户无需手动允许。

## 常见问题

### 应用无法打开，提示"无法验证开发者"

**原因**：应用未签名

**解决方法**：
- 临时：右键点击应用 > 打开 > 仍要打开
- 永久：对应用进行代码签名

### 签名失败

**检查**：
1. 是否已安装有效的开发者证书
2. 证书是否已过期
3. 证书名称是否正确

### 公证失败

**常见原因**：
- 应用专用密码错误
- Team ID 错误
- 网络连接问题

**查看详细日志**：
```bash
xcrun notarytool log <submission-id> \
    --apple-id "your-email@example.com" \
    --password "xxxx-xxxx-xxxx-xxxx" \
    --team-id "XXXXXXXXXX"
```

### DMG 创建失败

**检查**：
1. 磁盘空间是否充足（需要 2-3GB 空闲空间）
2. 是否有其他程序正在访问临时目录
3. 尝试手动清理临时目录：
   ```bash
   rm -rf ~/dmg_temp
   ```

### 打包后的应用太大

正常现象，包含：
- Python 运行时
- PyQt6 框架
- OCR 引擎

已启用 UPX 压缩减小体积。

## 技术细节

### PyInstaller 配置

- **单文件夹模式**：生成 `.app`  bundle
- **UPX 压缩**：已启用
- **代码签名**：在 BUNDLE 阶段支持

### Info.plist 配置

已配置：
- 应用名称和版本
- 文档类型（PDF, DOCX, DOC, 图片）
- 高分辨率支持
- 权限描述

### 签名权限

`entitlements.plist` 配置：
- 允许用户选择文件的读写访问
- 允许下载文件夹访问
- 允许调试（开发时）

## 故障排除

### 手动验证签名

```bash
codesign --verify --verbose dist/PrivacyGuard.app
```

### 查看签名详情

```bash
codesign --display --verbose=2 dist/PrivacyGuard.app
```

### 手动验证公证

```bash
spctl -a -t open --context context:primary-signature -v dist/PrivacyGuard.app
```

### 清理构建缓存

```bash
rm -rf build dist __pycache__
```

## 参考

- [Apple 代码签名指南](https://developer.apple.com/support/code-signing/)
- [Apple 公证指南](https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution)
- [PyInstaller macOS 文档](https://pyinstaller.org/en/stable/usage.html#building-mac-os-x-apps)
