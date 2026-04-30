# PrivacyGuard v37.0.4 版本发布说明

**发布日期**: 2026-02-19
**版本号**: v37.0.4
**代号**: 微信二维码更新版
**状态**: ✅ 正式发布

---

## 🎯 版本概述

v37.0.4 是 v37.0 配置系统版本的功能增强更新，主要包含：
1. **界面优化**: "吐槽"对话框关注开发者部分重新设计
2. **功能新增**: 微信公众号二维码展示功能
3. **打包完善**: 完整的 Windows/macOS 双平台一键打包方案
4. **问题修复**: Windows DLL 加载问题最终解决方案

---

## 📱 主要更新内容

### 1. 微信二维码功能 (UI-2026-02-19)

**变更前:**
```
微信公众号/抖音/小红书/B站（同号）: 池州汪律的Ai 进化论 [复制]
```

**变更后:**
```
微信公众号: 池州汪律的Ai进化论 [扫码关注]
抖音/小红书/B站（同号）: 池州有个汪律师 [复制]
```

**新增功能:**
- "扫码关注"按钮（蓝色主按钮样式）
- 点击弹出微信公众号二维码对话框
- 二维码显示尺寸: 280x280
- 友好提示: "微信扫一扫，关注公众号获取更多AI工具"

**代码位置:**
- `main.py:612-641` - FeedbackDialog 界面布局
- `main.py:837-920` - `_show_wx_qrcode()` 方法

### 2. 打包方案全面更新 (BUILD-2026-02-19)

#### 新增文件清单
| 文件 | 平台 | 用途 |
|------|------|------|
| `build_complete.bat` | Windows | 一键打包脚本（含DLL自动复制） |
| `build_complete.sh` | macOS | 一键打包脚本（含DMG创建） |
| `clean_project.bat` | Windows | 项目清理脚本（保留备份） |
| `clean_project.sh` | macOS | 项目清理脚本（保留备份） |
| `PACKAGING_GUIDE.md` | 双平台 | 完整打包指南 |

#### Windows DLL 问题解决方案
- 问题: `vcruntime140_1.dll` 未正确打包导致应用无法启动
- 方案: 构建后自动复制系统 DLL 到输出目录
- 关键代码:
  ```batch
  copy "C:\Windows\System32\vcruntime140_1.dll" "dist\PrivacyGuard\"
  copy "C:\Windows\System32\vcruntime140.dll" "dist\PrivacyGuard\"
  copy "C:\Windows\System32\msvcp140.dll" "dist\PrivacyGuard\"
  ```

#### 资源文件打包
- 所有 PyInstaller spec 文件已更新
- 包含 `assets/donate_qrcode.png` (打赏二维码)
- 包含 `assets/wx_qrcode.png` (微信公众号二维码)

---

## 📦 发布文件

### Windows 版本
```
releases/windows/
├── PrivacyGuard-v37.0.4-Windows-Portable.zip      (便携版)
└── PrivacyGuard-v37.0.4-Windows-Portable.zip.sha256 (校验和)
```

**特性:**
- 零依赖运行（VC++ DLL 已包含）
- 解压即用，无需安装
- 支持 Windows 10/11 64位

### macOS 版本
```
releases/macos/
├── PrivacyGuard-v37.0.4-macOS.dmg                 (安装包)
├── PrivacyGuard-v37.0.4-macOS.dmg.sha256          (校验和)
└── PrivacyGuard.app/                              (应用包)
```

**特性:**
- DMG 拖拽安装
- 支持 macOS 10.13+ (Intel/Apple Silicon)
- 已签名，可直接运行

---

## ✅ 验证清单

### 功能验证
- [x] 应用正常启动
- [x] PDF 打开与脱敏
- [x] Word 打开与脱敏
- [x] OCR 扫描功能
- [x] 手动脱敏（精确/全局模式）
- [x] **吐槽 → 打赏 → 显示二维码**
- [x] **吐槽 → 关注开发者 → 扫码关注 → 显示微信公众号二维码**

### 打包验证
- [x] Windows 打包测试通过
- [x] macOS 打包测试通过
- [x] 资源文件正确包含
- [x] Windows DLL 正确复制

---

## 📚 相关文档

- [PACKAGING_GUIDE.md](./PACKAGING_GUIDE.md) - 完整打包指南
- [CHANGELOG.md](./CHANGELOG.md) - 版本变更记录
- [docs/current/STATUS.md](./docs/current/STATUS.md) - 项目状态
- [docs/current/DEV_LOG.md](./docs/current/DEV_LOG.md) - 开发日志

---

## 🙏 致谢

感谢使用 PrivacyGuard 脱敏卫士！

如有问题或建议，欢迎通过以下方式联系：
- **微信公众号**: 池州汪律的Ai进化论
- **抖音/小红书/B站**: 池州有个汪律师
- **邮箱**: 491445490@qq.com

---

**PrivacyGuard 团队**
2026-02-19
