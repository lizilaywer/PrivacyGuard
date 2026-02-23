# PrivacyGuard 打包配置

本文档说明 PrivacyGuard 项目的打包系统结构。

## 目录结构

```
packaging/
├── windows/          # Windows 打包方案（完全独立）
│   ├── scripts/      # 一键打包脚本
│   ├── config/       # 配置文件
│   ├── assets/       # 资源文件
│   └── docs/         # 打包文档
│
└── macos/            # macOS 打包方案（完全独立）
    ├── scripts/      # 打包脚本
    ├── config/       # 配置文件
    ├── assets/       # 资源文件
    └── docs/         # 打包文档
```

## 设计原则

1. **完全独立**：每个平台有独立的目录，不共享配置
2. **路径清晰**：所有脚本使用相对路径，可在任何位置运行
3. **统一输出**：所有平台输出到 `releases/{platform}/` 目录
4. **保留缓存**：`build/` 目录仅用于 PyInstaller 构建缓存

## Windows 打包

### 快速开始

```batch
# 首次打包（按顺序执行）
packaging\windows\scripts\1_初始化环境.bat
packaging\windows\scripts\3_完整打包带安装程序.bat

# 后续打包
packaging\windows\scripts\3_完整打包带安装程序.bat
```

### 文件说明

| 文件 | 说明 |
|------|------|
| `scripts/1_初始化环境.bat` | 首次运行，安装依赖 |
| `scripts/2_一键打包.bat` | 仅生成 exe |
| `scripts/3_完整打包带安装程序.bat` | 生成 exe + 安装程序（推荐） |
| `scripts/4_仅创建安装程序.bat` | 从已有 exe 创建安装程序 |
| `config/PrivacyGuard_windows.spec` | PyInstaller 配置 |
| `config/PrivacyGuard_Setup.iss` | Inno Setup 安装脚本 |
| `assets/icon.ico` | 应用图标 |

### 输出位置

- 便携版：`dist/PrivacyGuard.exe`
- 安装程序：`releases/windows/PrivacyGuard-{version}-Setup.exe`

## macOS 打包

### 快速开始

```bash
# 打包应用
bash packaging/macos/scripts/build_macos_app.sh

# 签名（需要开发者证书）
bash packaging/macos/scripts/sign_macos_app.sh

# 公证（需要 Apple Developer 账号）
bash packaging/macos/scripts/notarize_macos_app.sh
```

### 文件说明

| 文件 | 说明 |
|------|------|
| `scripts/build_macos_app.sh` | 主打包脚本 |
| `scripts/sign_macos_app.sh` | 代码签名脚本 |
| `scripts/notarize_macos_app.sh` | 公证脚本 |
| `config/PrivacyGuard.spec` | PyInstaller 配置 |
| `config/entitlements.plist` | 签名权限配置 |
| `assets/PrivacyGuard.icns` | 应用图标 |

### 输出位置

- 应用包：`dist/PrivacyGuard.app`
- DMG 安装包：`releases/macos/PrivacyGuard-{version}-macOS.dmg`

## 注意事项

### Windows

- 需要安装 Inno Setup 6 才能创建安装程序
- 首次打包前必须运行 `1_初始化环境.bat`
- 打包后的 exe 可能被杀毒软件误报（PyInstaller 的已知问题）

### macOS

- 未签名的应用首次运行需要右键 > 打开 > 仍要打开
- 签名和公证需要 Apple Developer 账号（年费 $99）
- DMG 创建后建议进行公证以便用户正常打开

## 历史归档

旧的打包文件已归档到：
- `backups/archive/platforms_backup_20260217/` - 旧 platforms/ 目录

## 更新记录

- **2026-02-23**: v37.4.1 - 单 OCR 引擎架构，修复 Windows 深色模式问题
- **2026-02-17**: 重构打包系统，分离 Windows 和 macOS 配置
