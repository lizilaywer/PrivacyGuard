# PrivacyGuard Logo 图标使用指南

> 本目录包含 PrivacyGuard 脱敏卫士的完整图标资源
> 生成日期: 2026-03-17

---

## 📁 目录结构

```
assets/logo/
├── source/                    # SVG 矢量源文件
│   ├── logo_master.svg       # 标准版主源文件
│   └── logo_dark.svg         # 深色版源文件
├── export/                    # PNG 导出（各尺寸）
│   ├── 16/                   # 16x16 像素
│   ├── 24/                   # 24x24 像素
│   ├── 32/                   # 32x32 像素
│   ├── 48/                   # 48x48 像素
│   ├── 64/                   # 64x64 像素
│   ├── 128/                  # 128x128 像素
│   ├── 256/                  # 256x256 像素
│   ├── 512/                  # 512x512 像素
│   └── 1024/                 # 1024x1024 像素
├── windows/                   # Windows 专用
│   └── app_icon.ico          # Windows 应用程序图标
├── macos/                     # macOS 专用
│   └── AppIcon.icns          # macOS 应用程序图标
├── linux/                     # Linux 专用
│   ├── privacyguard.png      # 默认图标 (256x256)
│   └── privacyguard_{size}x{size}.png  # 各尺寸图标
├── marketing/                 # 营销物料
│   ├── app_store_icon.png    # App Store 图标 (1024x1024)
│   └── banner_basic.png      # 基础横幅 (1200x400)
├── generate_icons.py          # 图标生成脚本
├── LOGO_DESIGN_GUIDE.md      # 设计规范文档
└── README.md                 # 本文件
```

---

## 🚀 快速使用

### 在 PyInstaller 打包中使用

#### Windows
```python
# packaging/windows/config/PrivacyGuard_windows.spec
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PrivacyGuard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='../../assets/logo/windows/app_icon.ico',  # <-- 使用此路径
)
```

#### macOS
```python
# packaging/macos/config/PrivacyGuard.spec
app = BUNDLE(
    coll,
    name='PrivacyGuard.app',
    icon='../../assets/logo/macos/AppIcon.icns',  # <-- 使用此路径
    bundle_identifier='com.privacyguard.app',
)
```

### 在应用代码中使用

```python
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QDir

# 加载应用图标
icon_path = QDir.current().filePath('assets/logo/export/256/logo_default_256.png')
app.setWindowIcon(QIcon(icon_path))
```

### 在窗口中使用

```python
# 设置窗口图标
self.setWindowIcon(QIcon('assets/logo/export/128/logo_default_128.png'))

# 设置托盘图标（使用较小尺寸）
tray_icon = QIcon('assets/logo/export/32/logo_default_32.png')
```

---

## 📐 图标规格速查

### Windows 图标 (app_icon.ico)
| 尺寸 | 用途 |
|------|------|
| 16x16 | 任务栏、标题栏 |
| 32x32 | 桌面快捷方式 |
| 48x48 | 控制面板 |
| 256x256 | 高 DPI 显示 |

### macOS 图标 (AppIcon.icns)
| 尺寸 | 用途 |
|------|------|
| 16x16 / 32x32 | 列表视图、工具栏 |
| 32x32 / 64x64 | 工具栏 Retina |
| 128x128 / 256x256 | 访达 |
| 256x256 / 512x512 | 快速查看 |
| 512x512 / 1024x1024 | App Store |

### Linux 图标
| 尺寸 | 用途 |
|------|------|
| 16x16 | 工具栏 |
| 24x24 / 32x32 | 应用程序菜单 |
| 48x48 | 应用程序 |
| 128x128 / 256x256 | 应用程序 |
| 512x512 | 应用程序 |

---

## 🔄 重新生成图标

如需修改设计并重新生成所有图标：

```bash
# 1. 编辑 source/logo_master.svg 或 source/logo_dark.svg

# 2. 运行生成脚本
cd assets/logo
python3 generate_icons.py

# 3. 检查生成的文件
ls -la windows/ macos/ linux/
```

---

## 🎨 设计规范

### 色彩
- **主色**: 信任蓝渐变 (#3B82F6 → #1D4ED8)
- **辅助色**: 安全绿 (#10B981)、警示橙 (#F59E0B)
- **图标元素**: 白色 (#FFFFFF)

### 图形元素
- **PG 字母**: PrivacyGuard 的缩写，大号白色文字
- **蓝色圆角方块**: 简洁现代的背景，象征信任与安全

### 风格
- 极简扁平化设计
- 圆角矩形背景（类似 iOS/macOS 应用图标）
- 蓝色渐变背景
- 大号白色字母，各尺寸清晰可辨

详细设计规范请参阅: [LOGO_DESIGN_GUIDE.md](LOGO_DESIGN_GUIDE.md)

---

## 📦 打包检查清单

发布前确认以下文件已更新：

- [x] `assets/logo/windows/app_icon.ico` - Windows 图标（已修复：包含 16/32/48/256 多尺寸）
- [x] `assets/logo/macos/AppIcon.icns` - macOS 图标
- [x] `packaging/windows/config/*.spec` - Windows spec 文件引用正确
- [x] `packaging/macos/config/*.spec` - macOS spec 文件引用正确
- [x] `packaging/windows/config/PrivacyGuard_Setup.iss` - Windows 安装器图标路径正确
- [x] `packaging/windows/scripts/build_complete.bat` - 构建脚本图标检查路径正确
- [x] `main.py` - 应用启动时加载图标（已添加）

---

## 📝 版权与许可

PrivacyGuard 脱敏卫士 Logo 是项目的专有标识。

---

## 🆘 常见问题

### Q: 图标在 Windows 上显示模糊？
A: 确保 ICO 文件包含 256x256 尺寸，Windows 会在高 DPI 屏幕上使用大尺寸图标。

### Q: macOS 上图标显示不正确？
A: 检查 ICNS 文件是否包含所有必要尺寸（16-1024），并确保 spec 文件中的路径正确。

### Q: 如何修改图标颜色？
A: 编辑 `source/logo_master.svg` 中的渐变定义，然后重新运行 `generate_icons.py`。

### Q: 需要添加更多尺寸？
A: 修改 `generate_icons.py` 中的 `SIZES` 列表，添加所需尺寸后重新运行脚本。

---

*最后更新: 2026-03-17*
