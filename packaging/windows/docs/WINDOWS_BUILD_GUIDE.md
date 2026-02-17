# PrivacyGuard Windows 打包指南

## 快速开始

### 第一次打包

1. **初始化环境**（只需执行一次）
   ```batch
   packaging\windows\scripts\1_初始化环境.bat
   ```

2. **完整打包**（exe + 安装程序）
   ```batch
   packaging\windows\scripts\3_完整打包带安装程序.bat
   ```

3. **获取安装程序**
   - 位置：`releases/windows/PrivacyGuard-36.4-Setup.exe`

### 日常打包

```batch
packaging\windows\scripts\3_完整打包带安装程序.bat
```

## 打包选项

| 脚本 | 用途 | 输出 |
|------|------|------|
| `1_初始化环境.bat` | 首次设置，安装依赖 | 虚拟环境 venv/ |
| `2_一键打包.bat` | 仅生成便携版 exe | `dist/PrivacyGuard.exe` |
| `3_完整打包带安装程序.bat` | 生成 exe + 安装程序（推荐） | exe + Setup.exe |
| `4_仅创建安装程序.bat` | 从已有 exe 创建安装程序 | Setup.exe |

## 目录结构

```
packaging/windows/
├── scripts/                    # 打包脚本
│   ├── 1_初始化环境.bat
│   ├── 2_一键打包.bat
│   ├── 3_完整打包带安装程序.bat
│   ├── 4_仅创建安装程序.bat
│   └── README.txt
├── config/                     # 配置文件
│   ├── PrivacyGuard_windows.spec    # PyInstaller 配置
│   ├── PrivacyGuard_Setup.iss       # Inno Setup 脚本
│   └── version_info.txt             # 版本信息
└── assets/                     # 资源文件
    └── icon.ico                # 应用图标
```

## 先决条件

### 必需

- Python 3.11 或更高版本
- Windows 10/11

### 创建安装程序需要

- [Inno Setup 6](https://jrsoftware.org/isdl.php)

## 自定义配置

### 修改版本号

编辑以下文件：
1. `packaging/windows/config/version_info.txt`
2. `packaging/windows/scripts/*.bat`（所有批处理文件中的 VERSION 变量）

### 修改应用图标

替换文件：`packaging/windows/assets/icon.ico`

图标规格：
- 格式：ICO（多尺寸）
- 推荐尺寸：16x16, 32x32, 48x48, 256x256

### 修改安装程序配置

编辑：`packaging/windows/config/PrivacyGuard_Setup.iss`

## 输出文件

### 便携版

- **位置**：`dist/PrivacyGuard.exe`
- **用途**：直接运行，无需安装
- **适合**：快速测试、U盘携带

### 安装版

- **位置**：`releases/windows/PrivacyGuard-{version}-Setup.exe`
- **用途**：标准安装程序
- **适合**：正式发布、分发给用户

## 常见问题

### 打包失败，提示"找不到模块"

1. 确保已运行 `1_初始化环境.bat`
2. 检查 `requirements.txt` 是否完整
3. 尝试删除 `venv/` 目录重新初始化

### 打包后的 exe 太大（几百MB）

这是正常的！包含：
- Python 运行时
- PyQt6 GUI 框架
- OCR 引擎（onnxruntime + RapidOCR）
- 其他依赖库

### Windows Defender 报毒

PyInstaller 打包的程序有时会被误报：
- 可以提交到微软申诉：https://www.microsoft.com/en-us/wdsi/filesubmission
- 或者购买代码签名证书签名

### 打包时间太长

正常现象：
- 机械硬盘：10-15 分钟
- SSD：5-8 分钟

### 无法创建安装程序

确保已安装 Inno Setup 6：
- 默认安装路径：`C:\Program Files (x86)\Inno Setup 6\ISCC.exe`

## 技术细节

### PyInstaller 配置

- **配置文件**：`packaging/windows/config/PrivacyGuard_windows.spec`
- **打包模式**：单文件夹模式（非单文件）
- **UPX 压缩**：已禁用（避免 DLL 加载失败）

### 依赖收集

自动收集：
- `onnxruntime` 及其所有依赖
- `rapidocr_onnxruntime` 及其所有依赖
- PyQt6 相关模块

### 隐藏导入

已配置：
- PyQt6 所有子模块
- OpenCV (cv2)
- PyMuPDF (fitz)
- Python-docx
- PIL

## 故障排除

### 查看详细日志

编辑批处理脚本，将以下行：
```batch
pyinstaller --clean --noconfirm ...
```

改为：
```batch
pyinstaller --clean --noconfirm -v ...
```

### 手动测试打包

```batch
# 激活虚拟环境
venv\Scripts\activate.bat

# 手动运行 PyInstaller
pyinstaller --clean --noconfirm packaging\windows\config\PrivacyGuard_windows.spec
```

## 参考

- [PyInstaller 文档](https://pyinstaller.org/en/stable/)
- [Inno Setup 文档](https://jrsoftware.org/ishelp/)
