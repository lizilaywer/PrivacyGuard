# PrivacyGuard Windows 平台迁移指南

## 📋 目录
1. [核心概念](#核心概念)
2. [代码兼容性分析](#代码兼容性分析)
3. [迁移步骤](#迁移步骤)
4. [Windows 打包配置](#windows-打包配置)
5. [测试方法](#测试方法)
6. [常见问题](#常见问题)

---

## 核心概念

### 🎯 跨平台开发是什么？

**通俗解释**：
> 就像用**通用的乐高积木**搭建不同风格的房子
> - 积木（Python代码 + PyQt6）= 通用的
> - 搭建方式（业务逻辑）= 通用的
> - 房子外观（GUI）= 自动适应系统风格

### ✅ 好消息

你的代码**已经非常接近跨平台**了！

**原因**：
1. ✅ 使用了 `os.path.join()` - 自动适配路径分隔符
2. ✅ 使用了标准库（os, sys, tempfile）- 跨平台兼容
3. ✅ 使用了 PyQt6 - 原生跨平台框架
4. ✅ 没有使用 macOS 特定 API

---

## 代码兼容性分析

### ✅ 无需修改的部分（95%）

```python
# 1. GUI 组件 - 完全兼容
from PyQt6.QtWidgets import QPushButton, QLabel
button = QPushButton("点击我")

# 2. PDF 处理 - 完全兼容
import fitz
doc = fitz.open("file.pdf")

# 3. OCR 识别 - 完全兼容
from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()

# 4. 文件路径 - 已经用 os.path（兼容！）
file_path = os.path.join("folder", "file.pdf")
# macOS: "folder/file.pdf"
# Windows: "folder\\file.pdf"
```

### ⚠️ 需要检查的部分（5%）

#### 1. Word 文档转换（LibreOffice）

**当前代码**（依赖 LibreOffice）：
```python
# macOS 的 LibreOffice 路径
LIBREOFFICE_PATH = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
```

**Windows 需要修改**：
```python
import sys
import shutil

def find_libreoffice():
    """查找 LibreOffice 可执行文件"""
    if sys.platform == "darwin":
        paths = [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/Applications/LibreOffice.app/Contents/program/soffice"
        ]
    elif sys.platform == "win32":
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\LibreOffice\program\soffice.exe")
        ]
    else:  # Linux
        paths = ["/usr/bin/libreoffice", "/usr/bin/soffice"]

    for path in paths:
        if os.path.exists(path):
            return path

    # 尝试通过系统 PATH 查找
    soffice = shutil.which("soffice")
    if soffice:
        return soffice

    return None
```

#### 2. 临时文件路径（已兼容，无需修改）

```python
# ✅ 当前代码已经正确使用 tempfile
import tempfile
temp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
# macOS: /var/folders/...
# Windows: C:\Users\...\AppData\Local\Temp\...
```

#### 3. 文件对话框（已兼容，无需修改）

```python
# ✅ QFileDialog 自动适应系统
file_path, _ = QFileDialog.getOpenFileName(
    self,
    "选择 PDF 文件",
    "",
    "PDF 文件 (*.pdf)"
)
```

---

## 迁移步骤

### 步骤 1：添加平台检测代码

修改 `_open_word` 方法中的 LibreOffice 路径查找逻辑。

### 步骤 2：创建 Windows 打包配置

创建 `build/PrivacyGuard_windows.spec` 文件。

### 步骤 3：创建 Windows 打包脚本

创建 `build/build_windows_app.py` 脚本。

### 步骤 4：测试

在 Windows 环境中测试应用。

### 步骤 5：构建发布包

生成 Windows .exe 安装程序。

---

## Windows 打包配置

### 1. .spec 文件配置

**文件**: `build/PrivacyGuard_windows.spec`

```python
# -*- mode: python ; coding: utf-8 -*-
"""
PrivacyGuard Windows 应用打包配置
PyInstaller Spec 文件
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(SPEC))
parent_dir = os.path.dirname(current_dir)

block_cipher = None

a = Analysis(
    [os.path.join(parent_dir, 'main.py')],
    pathex=[parent_dir, current_dir],
    binaries=[],
    datas=[
        # 包含主题文件
        (os.path.join(parent_dir, 'theme.py'), '.'),
        # 收集 RapidOCR 模型文件
        collect_data_files('rapidocr_onnxruntime'),
    ],
    hiddenimports=[
        # PyQt6 相关
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel',
        # 核心依赖
        'cv2',
        'fitz',  # PyMuPDF
        'numpy',
        'rapidocr_onnxruntime',
        # OCR 相关
        'onnxruntime',
        # 主题系统
        'theme',
        # 其他可能的隐藏导入
        'PIL',
        'PIL._imaging',
        'docx',
        'python-docx',
        # Windows 特定
        'win32com',
        'pywintypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'pandas',
        'scipy',
        'IPython',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

# 过滤掉不需要的共享库
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(current_dir, 'PrivacyGuard.ico'),  # Windows 图标
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PrivacyGuard',
)
```

### 2. 打包脚本

**文件**: `build/build_windows_app.py`

```python
#!/usr/bin/env python3
"""
PrivacyGuard Windows 应用打包脚本
在 macOS 或 Windows 上都可以运行
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# 项目配置
APP_NAME = "PrivacyGuard"
VERSION = "35.0"
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
BUILD_DIR = PROJECT_DIR / "build"
DIST_DIR = PROJECT_DIR / "dist"
RELEASE_DIR = PROJECT_DIR / "releases"

# 颜色输出（Windows 兼容）
def print_colored(text, color="white"):
    """跨平台的彩色输出"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "reset": "\033[0m",
    }
    color_code = colors.get(color, "")
    print(f"{color_code}{text}{colors['reset']}")

def print_step(text):
    print_colored(f"[步骤] {text}", "green")

def print_info(text):
    print_colored(f"[信息] {text}", "blue")

def print_error(text):
    print_colored(f"[错误] {text}", "red")

def check_python():
    """检查 Python 环境"""
    print_step("检查 Python 环境")
    print_info(f"Python 版本: {sys.version}")
    print_info(f"Python 路径: {sys.executable}")

def check_dependencies():
    """检查依赖"""
    print_step("检查依赖包")

    required = ["PyInstaller", "PyQt6", "PyMuPDF", "rapidocr_onnxruntime"]
    missing = []

    for package in required:
        try:
            __import__(package.replace("-", "_"))
            print_info(f"✓ {package}")
        except ImportError:
            print_info(f"✗ {package} (未安装)")
            missing.append(package)

    if missing:
        print_error(f"缺少依赖: {', '.join(missing)}")
        print_info("请运行: pip install " + " ".join(missing))
        return False

    return True

def clean_build():
    """清理旧构建"""
    print_step("清理旧构建文件")
    dirs_to_clean = [BUILD_DIR / "build", BUILD_DIR / "dist", DIST_DIR]

    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print_info(f"已清理: {dir_path}")

def build_exe():
    """构建 Windows 可执行文件"""
    print_step("构建 Windows 可执行文件")

    spec_file = BUILD_DIR / "PrivacyGuard_windows.spec"
    if not spec_file.exists():
        print_error(f"找不到 spec 文件: {spec_file}")
        return False

    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)],
            check=True,
            cwd=PROJECT_DIR
        )
        print_info("构建完成")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"构建失败: {e}")
        return False

def create_installer():
    """创建安装程序（可选）"""
    print_step("创建安装程序（可选）")

    # Windows 可以使用 NSIS 或 Inno Setup
    # 这里只复制文件到 releases 目录
    print_info("复制文件到发布目录")

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    # 复制整个 dist/PrivacyGuard 目录
    if (DIST_DIR / "PrivacyGuard").exists():
        import zipfile
        zip_path = RELEASE_DIR / f"{APP_NAME}-{VERSION}-Windows.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in (DIST_DIR / "PrivacyGuard").rglob('*'):
                if file.is_file():
                    arcname = file.relative_to(DIST_DIR)
                    zipf.write(file, arcname)

        print_info(f"已创建: {zip_path}")

def main():
    """主流程"""
    print_colored("=" * 60, "blue")
    print_colored(f"  PrivacyGuard Windows 打包脚本", "blue")
    print_colored(f"  版本: {VERSION}", "blue")
    print_colored("=" * 60, "blue")
    print()

    # 检查环境
    check_python()
    if not check_dependencies():
        return 1

    # 清理旧构建
    clean_build()

    # 构建
    if not build_exe():
        return 1

    # 创建发布包
    create_installer()

    print_colored("\n构建完成！", "green")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 3. Windows 图标

需要准备一个 `.ico` 格式的图标文件：

**文件**: `build/PrivacyGuard.ico`

- 可以从现有的 `.icns` 转换
- 在线工具: https://convertico.com/
- 或使用 ImageMagick: `convert PrivacyGuard.icns PrivacyGuard.ico`

---

## 测试方法

### 方法 1：虚拟机测试（推荐）

**在 macOS 上测试 Windows 应用**

#### 1. 安装虚拟机软件
- **Parallels Desktop** (付费，性能最好)
- **VMware Fusion** (付费)
- **VirtualBox** (免费)

#### 2. 安装 Windows
- 下载 Windows 10/11 ISO
- 在虚拟机中安装

#### 3. 在虚拟机中测试
```powershell
# 复制文件到虚拟机
# 在 Windows 虚拟机中：

# 1. 安装 Python
# 下载 python.org 的 Python 安装程序

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行应用
python main.py

# 4. 测试功能
- 打开 PDF
- OCR 识别
- 手动脱敏
- 保存文件
```

### 方法 2：在线 Windows 测试

**使用云端的 Windows 环境**

#### 1. BrowserStack (付费)
- https://www.browserstack.com/
- 提供云端 Windows 虚拟机
- 浏览器中远程操作

#### 2. AWS / Azure / 阿里云
- 租用 Windows 虚拟机
- 按小时付费
- 完全控制权

### 方法 3：找朋友测试

- 有 Windows 电脑的朋友
- 远程协助（TeamViewer、向日葵）
- 发送测试版本，收集反馈

### 方法 4：实际 Windows 机器

- 如果有双系统
- 或有 Windows 电脑
- 直接测试

---

## 完整迁移清单

### ✅ 在 macOS 上完成

```bash
# 1. 检查代码兼容性
cd /Users/a49144/Desktop/临时coding/PrivacyApp
python3 -m py_compile main.py

# 2. 创建 Windows 打包配置
# 创建 build/PrivacyGuard_windows.spec

# 3. 创建 Windows 打包脚本
# 创建 build/build_windows_app.py

# 4. 准备图标文件
# 转换 PrivacyGuard.icns -> PrivacyGuard.ico

# 5. 测试构建（在 macOS 上）
python3 build/build_windows_app.py
# 输出: dist/PrivacyGuard/PrivacyGuard.exe

# 6. 打包发布版本
cd dist/PrivacyGuard
zip -r ../../releases/PrivacyGuard-35.0-Windows.zip .
```

### ✅ 在 Windows 上测试

```powershell
# 1. 复制文件到 Windows
# - PrivacyGuard-35.0-Windows.zip
# - 或整个 dist/PrivacyGuard 目录

# 2. 解压并运行
# 双击 PrivacyGuard.exe

# 3. 测试功能
✓ 应用启动
✓ 打开 PDF 文件
✓ OCR 识别
✓ 手动脱敏
✓ 保存脱敏文件
✓ 打开 Word 文件（需要 LibreOffice）
✓ 保存 Word 文件

# 4. 记录问题
- 截图错误
- 记录日志
- 测试不同文件格式
```

---

## 常见问题

### Q1: 能在 macOS 上直接构建 .exe 吗？

**A**: 可以，但不推荐！

**原因**：
- PyInstaller 支持跨平台构建
- 但 macOS 构建的 .exe 可能有兼容性问题
- 某些 Windows 特定库可能打包不正确

**最佳实践**：
- macOS 上创建打包配置（`.spec` 文件）
- Windows 上执行实际构建
- 或使用虚拟机中的 Windows 构建

### Q2: 如何在 macOS 上测试 Windows 应用？

**A**: 使用虚拟机！

**推荐方案**：
1. **Parallels Desktop** - 性能最好，收费
2. **VirtualBox** - 免费，性能较差
3. **云端 Windows** - BrowserStack / 云服务器

### Q3: Word 文档转换在 Windows 上需要什么？

**A**: LibreOffice

**Windows 安装**：
1. 下载 LibreOffice: https://www.libreoffice.org/
2. 安装到默认路径
3. 代码会自动查找 `soffice.exe`

**替代方案**：
- 使用 `mammoth`（只支持 .docx，不支持 .doc）
- 代码已经支持，不需要 LibreOffice

### Q4: 应用体积太大怎么办？

**A**: 优化打包

**方法**：
1. 使用 UPX 压缩（已在配置中启用）
2. 排除不需要的模块
3. 使用虚拟环境打包纯净依赖

### Q5: 为什么不需要修改代码？

**A**: 因为你的代码已经很规范了！

**原因**：
- ✅ 使用了 `os.path.join()` 而不是硬编码路径
- ✅ 使用了 `tempfile` 而不是 `/tmp`
- ✅ 使用了标准库而不是系统 API
- ✅ 使用了 PyQt6 跨平台框架

**需要修改的唯一地方**：
- LibreOffice 路径查找（添加 Windows 路径）

---

## 快速开始

### 在 macOS 上准备 Windows 版本

```bash
# 1. 创建 Windows 打包文件
cd /Users/a49144/Desktop/临时coding/PrivacyApp

# 2. 告诉我
"我想创建 Windows 打包配置"
```

我会帮你：
1. 创建 `PrivacyGuard_windows.spec`
2. 创建 `build_windows_app.py`
3. 转换图标为 `.ico`
4. 测试构建（生成 .exe）

### 在 Windows 上测试

```powershell
# 下载生成的文件
PrivacyGuard-35.0-Windows.zip

# 解压
unzip PrivacyGuard-35.0-Windows.zip

# 运行
.\PrivacyGuard.exe
```

---

## 总结

### ✅ 好消息

1. **代码几乎不需要修改**（95%兼容）
2. **PyQt6 是跨平台的**（自动适应系统）
3. **可以在 macOS 上准备 Windows 版本**

### ⚠️ 需要注意

1. **测试是必须的**（虚拟机或真机）
2. **LibreOffice 路径需要适配**
3. **首次构建可能需要调试**

### 🎯 下一步

**告诉我你想做什么**：
- "我想创建 Windows 打包配置"
- "我想在虚拟机中测试"
- "我想优化代码兼容性"

我会帮你一步步完成！
