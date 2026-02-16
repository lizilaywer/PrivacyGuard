# PrivacyGuard Windows 打包指南

> 完整的 Windows 应用打包、签名和发布指南

---

## 目录

1. [快速开始](#快速开始)
2. [环境准备](#环境准备)
3. [打包流程](#打包流程)
4. [单文件 vs 文件夹模式](#单文件-vs-文件夹模式)
5. [代码签名](#代码签名)
6. [安装程序制作](#安装程序制作)
7. [自动更新](#自动更新)
8. [故障排除](#故障排除)

---

## 快速开始

### 一键打包

```cmd
cd C:\Users\YourName\Desktop\PrivacyApp
build\build_windows_app.bat
```

打包完成后，文件位于：
- 文件夹模式：`dist\PrivacyGuard\`
- 单文件模式：`dist\PrivacyGuard.exe`
- 安装程序：`releases\PrivacyGuard-36.4-Setup.exe`

---

## 环境准备

### 系统要求

| 项目 | 要求 |
|------|------|
| Windows 版本 | Windows 10/11 (64位) |
| Python | 3.11+ |
| 磁盘空间 | 至少 5GB 可用空间 |
| 内存 | 至少 4GB |

### 安装依赖

```cmd
:: 1. 安装 Python（从 python.org 下载）
:: 确保勾选 "Add Python to PATH"

:: 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

:: 3. 安装 Python 依赖
pip install -r requirements.txt

:: 4. 安装打包工具
pip install pyinstaller

:: 5. 安装 Inno Setup（用于制作安装程序）
:: 从 https://jrsoftware.org/isdl.php 下载安装
```

### 项目结构检查

确保项目结构如下：

```
PrivacyApp/
├── main.py                      # 主程序
├── theme.py                     # 主题文件
├── requirements.txt             # 依赖列表
├── build/
│   ├── build_windows_app.bat    # 打包脚本
│   ├── PrivacyGuard_windows.spec # PyInstaller 配置
│   └── icon.ico                 # 应用图标（必需）
└── venv/                        # 虚拟环境
```

---

## 打包流程

### 步骤 1: 准备工作

```cmd
:: 激活虚拟环境
venv\Scripts\activate

:: 更新版本号（修改 main.py 中的 VERSION 变量）

:: 清理旧构建
rmdir /s /q build\build
del /q dist\*
```

### 步骤 2: 创建 Spec 文件

创建 `build/PrivacyGuard_windows.spec`：

```python
# -*- mode: python ; coding: utf-8 -*-
"""
PrivacyGuard Windows 应用打包配置
PyInstaller Spec 文件
"""

import os
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(SPEC))
parent_dir = os.path.dirname(current_dir)

block_cipher = None

# 收集所有依赖（处理 onnxruntime 等特殊依赖）
onnx_datas, onnx_binaries, onnx_hiddenimports = collect_all('onnxruntime')
rapid_datas, rapid_binaries, rapid_hiddenimports = collect_all('rapidocr_onnxruntime')

# 收集动态库
cv2_binaries = collect_dynamic_libs('cv2')

a = Analysis(
    [os.path.join(parent_dir, 'main.py')],
    pathex=[parent_dir, current_dir],
    binaries=onnx_binaries + rapid_binaries + cv2_binaries,
    datas=[
        # 包含主题文件
        (os.path.join(parent_dir, 'theme.py'), '.'),
    ] + onnx_datas + rapid_datas,
    hiddenimports=[
        # PyQt6 相关
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel',
        'PyQt6.sip',
        # 核心依赖
        'cv2',
        'fitz',  # PyMuPDF
        'numpy',
        'rapidocr_onnxruntime',
        'onnxruntime',
        # 主题系统
        'theme',
        # 其他隐藏导入
        'PIL',
        'PIL._imaging',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'docx',
        'docx.shared',
        'docx.enum',
        'python-docx',
        'mammoth',
        'beautifulsoup4',
        'bs4',
    ] + onnx_hiddenimports + rapid_hiddenimports,
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
        'unittest',
        'pydoc',
        'pdb',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 单文件模式配置
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PrivacyGuard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(current_dir, 'icon.ico'),  # 应用图标
    version=os.path.join(current_dir, 'version_info.txt'),  # 版本信息
)
```

### 步骤 3: 创建版本信息文件

创建 `build/version_info.txt`：

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(36, 4, 0, 0),
    prodvers=(36, 4, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'安徽始信律师事务所'),
         StringStruct(u'FileDescription', u'PrivacyGuard 脱敏卫士 - 文档隐私保护工具'),
         StringStruct(u'FileVersion', u'36.4.0.0'),
         StringStruct(u'InternalName', u'PrivacyGuard'),
         StringStruct(u'LegalCopyright', u'Copyright (C) 2026 汪立'),
         StringStruct(u'OriginalFilename', u'PrivacyGuard.exe'),
         StringStruct(u'ProductName', u'PrivacyGuard 脱敏卫士'),
         StringStruct(u'ProductVersion', u'36.4.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
```

### 步骤 4: 执行打包

#### 方式一：单文件模式（推荐）

```cmd
pyinstaller --clean --noconfirm build\PrivacyGuard_windows.spec
```

输出：`dist\PrivacyGuard.exe`

#### 方式二：文件夹模式

```cmd
pyinstaller --clean --noconfirm --onedir build\PrivacyGuard_windows_folder.spec
```

输出：`dist\PrivacyGuard\`

---

## 单文件 vs 文件夹模式

### 模式对比

| 特性 | 单文件模式 | 文件夹模式 |
|------|------------|------------|
| 文件数量 | 1个exe文件 | 多个文件 |
| 文件大小 | ~150-200MB | ~120-170MB（压缩后） |
| 启动速度 | 稍慢（需要解压） | 快 |
| 分发便捷性 | 极高（单文件） | 一般（需要压缩） |
| 更新便捷性 | 简单（替换单文件） | 较复杂 |
| 适合场景 | 个人使用、快速分享 | 企业部署、自动更新 |

### 推荐选择

- **开源发布**：单文件模式（用户体验好）
- **企业部署**：文件夹模式 + Inno Setup 安装程序

---

## 代码签名

### 为什么需要签名

| 场景 | 未签名 | 已签名 |
|------|--------|--------|
| 下载运行 | ⚠️ Windows SmartScreen 警告 | ✅ 正常打开 |
| 杀毒软件 | ❌ 可能误报 | ✅ 降低误报率 |
| 用户信任 | 低 | 高 |

### 申请代码签名证书

#### 方案一：标准代码签名证书（推荐）

| 提供商 | 价格 | 有效期 |
|--------|------|--------|
| DigiCert | ~$400/年 | 1-3年 |
| Sectigo | ~$200/年 | 1-3年 |
| Certum | ~$70/年 | 1年 |

申请流程：
1. 选择证书提供商购买
2. 提交身份验证材料
3. 下载证书并安装
4. 使用签名工具签名

#### 方案二：个人测试证书（免费）

```powershell
# 创建自签名证书（仅用于测试）
New-SelfSignedCertificate `
    -Subject "CN=PrivacyGuard Test" `
    -Type CodeSigning `
    -CertStoreLocation Cert:\CurrentUser\My

# 导出证书（用于签名）
$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like "*PrivacyGuard*" }
Export-Certificate -Cert $cert -FilePath test_cert.cer
```

### 签名应用

#### 使用 signtool（Windows SDK）

```cmd
:: 签名 exe 文件
signtool sign `
    /f "path\to\certificate.pfx" `
    /p "certificate_password" `
    /tr "http://timestamp.digicert.com" `
    /td sha256 `
    /fd sha256 `
    dist\PrivacyGuard.exe

:: 验证签名
signtool verify /pa dist\PrivacyGuard.exe
```

#### 批量签名脚本

创建 `build/sign_windows_app.bat`：

```batch
@echo off
chcp 65001 > nul
echo 🔏 正在签名 PrivacyGuard...

:: 配置
set CERT_PATH=C:\certs\code_signing.pfx
set CERT_PASS=your_password
set APP_PATH=dist\PrivacyGuard.exe

:: 检查文件
if not exist "%CERT_PATH%" (
    echo ❌ 错误: 未找到证书文件
    exit /b 1
)

if not exist "%APP_PATH%" (
    echo ❌ 错误: 未找到应用程序
    exit /b 1
)

:: 签名
signtool sign ^
    /f "%CERT_PATH%" ^
    /p "%CERT_PASS%" ^
    /tr "http://timestamp.digicert.com" ^
    /td sha256 ^
    /fd sha256 ^
    /d "PrivacyGuard 脱敏卫士" ^
    /du "https://github.com/yourname/PrivacyGuard" ^
    "%APP_PATH%"

if %ERRORLEVEL% == 0 (
    echo ✅ 签名成功
    signtool verify /pa "%APP_PATH%"
) else (
    echo ❌ 签名失败
    exit /b 1
)
```

---

## 安装程序制作

### 方案一：Inno Setup（推荐）

#### 1. 安装 Inno Setup

从 [jrsoftware.org](https://jrsoftware.org/isdl.php) 下载并安装

#### 2. 创建安装脚本

创建 `build/PrivacyGuard_Setup.iss`：

```pascal
; PrivacyGuard 安装程序脚本
; Inno Setup 6.x

#define MyAppName "PrivacyGuard 脱敏卫士"
#define MyAppVersion "36.4"
#define MyAppPublisher "汪立"
#define MyAppURL "https://github.com/yourname/PrivacyGuard"
#define MyAppExeName "PrivacyGuard.exe"

[Setup]
; 基本信息
AppId={{PRIVACYGUARD-APP-UUID}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; 安装程序设置
DefaultDirName={autopf}\PrivacyGuard
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
OutputDir=releases
OutputBaseFilename=PrivacyGuard-{#MyAppVersion}-Setup
SetupIconFile=build\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; 权限要求
PrivilegesRequiredOverridesAllowed=dialog
PrivilegesRequired=lowest

; 安装程序版本信息
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} 安装程序
VersionInfoCopyright=Copyright (C) 2026

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; 主程序（单文件模式）
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; 其他资源文件
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange({#MyAppName}, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
; 检查 .NET Framework（如果需要）
function InitializeSetup(): Boolean;
begin
  Result := true;
end;
```

#### 3. 编译安装程序

```cmd
:: 命令行编译
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\PrivacyGuard_Setup.iss

:: 或在 Inno Setup IDE 中打开 .iss 文件，点击 Build
```

#### 4. 签名安装程序

```cmd
signtool sign ^
    /f "path\to\certificate.pfx" ^
    /p "password" ^
    /tr "http://timestamp.digicert.com" ^
    /td sha256 ^
    /fd sha256 ^
    releases\PrivacyGuard-36.4-Setup.exe
```

### 方案二：NSIS（轻量级）

```nsis
; PrivacyGuard NSIS 安装脚本
Name "PrivacyGuard 脱敏卫士"
OutFile "releases\PrivacyGuard-36.4-Setup.exe"
InstallDir $PROGRAMFILES\PrivacyGuard
RequestExecutionLevel admin

Page directory
Page instfiles

Section "Install"
    SetOutPath $INSTDIR
    File "dist\PrivacyGuard.exe"
    File "LICENSE.txt"

    CreateDirectory "$SMPROGRAMS\PrivacyGuard"
    CreateShortcut "$SMPROGRAMS\PrivacyGuard\PrivacyGuard.lnk" "$INSTDIR\PrivacyGuard.exe"
    CreateShortcut "$DESKTOP\PrivacyGuard.lnk" "$INSTDIR\PrivacyGuard.exe"

    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\PrivacyGuard.exe"
    Delete "$INSTDIR\uninstall.exe"
    Delete "$SMPROGRAMS\PrivacyGuard\PrivacyGuard.lnk"
    Delete "$DESKTOP\PrivacyGuard.lnk"
    RMDir "$SMPROGRAMS\PrivacyGuard"
    RMDir "$INSTDIR"
SectionEnd
```

---

## 自动更新

### 方案一：GitHub Releases API

```python
import requests
import json
from packaging import version

CURRENT_VERSION = "36.4"
GITHUB_API = "https://api.github.com/repos/yourname/PrivacyGuard/releases/latest"

def check_update():
    """检查更新"""
    try:
        response = requests.get(GITHUB_API, timeout=5)
        data = response.json()

        latest_version = data['tag_name'].lstrip('v')
        download_url = None

        # 查找 Windows 版本
        for asset in data['assets']:
            if 'windows' in asset['name'].lower() or asset['name'].endswith('.exe'):
                download_url = asset['browser_download_url']
                break

        if version.parse(latest_version) > version.parse(CURRENT_VERSION):
            return {
                'has_update': True,
                'version': latest_version,
                'download_url': download_url,
                'release_notes': data['body']
            }
    except Exception as e:
        print(f"检查更新失败: {e}")

    return {'has_update': False}

def show_update_dialog(update_info):
    """显示更新对话框"""
    from PyQt6.QtWidgets import QMessageBox, QApplication
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QDesktopServices

    msg = QMessageBox()
    msg.setWindowTitle("发现新版本")
    msg.setText(f"发现新版本: {update_info['version']}\n\n{update_info['release_notes'][:200]}...")
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg.button(QMessageBox.StandardButton.Yes).setText("立即下载")
    msg.button(QMessageBox.StandardButton.No).setText("稍后提醒")

    if msg.exec() == QMessageBox.StandardButton.Yes:
        QDesktopServices.openUrl(QUrl(update_info['download_url']))
```

### 方案二：自动更新库

使用 `pyupdater` 或自定义更新机制：

```python
# 简化的自动更新逻辑
import os
import sys
import urllib.request
import subprocess

def auto_update():
    """自动下载并安装更新"""
    update_info = check_update()
    if not update_info['has_update']:
        return

    # 下载新版本
    temp_path = os.path.expanduser('~\\AppData\\Local\\Temp\\PrivacyGuard_new.exe')
    urllib.request.urlretrieve(update_info['download_url'], temp_path)

    # 创建更新脚本
    update_script = os.path.expanduser('~\\AppData\\Local\\Temp\\update.bat')
    with open(update_script, 'w') as f:
        f.write(f'''@echo off
timeout /t 2 /nobreak > nul
copy /y "{temp_path}" "{sys.executable}"
start "" "{sys.executable}"
del "{update_script}"
''')

    # 执行更新脚本并退出
    subprocess.Popen(['cmd', '/c', update_script], shell=True)
    sys.exit(0)
```

---

## 故障排除

### 问题 1: "找不到指定的模块"

**原因**: 依赖库未正确打包

**解决**:
```python
# 在 spec 文件中添加隐藏导入
hiddenimports=[
    'cv2',
    'onnxruntime',
    'rapidocr_onnxruntime',
    'PyQt6.sip',
]

# 或者使用 collect_all
datas, binaries, hiddenimports = collect_all('package_name')
```

### 问题 2: Windows Defender 误报

**原因**: PyInstaller 的 bootloader 可能被误报

**解决**:
1. 更新 PyInstaller 到最新版
2. 使用代码签名证书签名
3. 向微软提交误报申诉：https://www.microsoft.com/en-us/wdsi/filesubmission

### 问题 3: 应用启动慢

**原因**: 单文件模式需要解压

**解决**:
- 使用 `--onedir` 模式替代 `--onefile`
- 或使用安装程序分发

### 问题 4: PyQt6 WebEngine 无法加载

**原因**: WebEngine 需要额外的资源文件

**解决**:
```python
# 在 spec 文件中添加
datas=[
    (os.path.join(parent_dir, 'theme.py'), '.'),
    # PyQt6 WebEngine 资源
    (os.path.join(PyQt6_dir, 'Qt6', 'resources'), 'PyQt6/Qt6/resources'),
    (os.path.join(PyQt6_dir, 'Qt6', 'translations'), 'PyQt6/Qt6/translations'),
]
```

### 问题 5: 路径中包含中文导致失败

**解决**:
```python
# 在代码中使用 Unicode 路径
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

---

## 打包检查清单

### 发布前检查

- [ ] 版本号已更新（main.py、version_info.txt）
- [ ] 在干净虚拟机中测试运行
- [ ] 所有功能正常工作（打开、脱敏、保存）
- [ ] 图标正确显示
- [ ] 文件关联正常（可选）
- [ ] 代码已签名（如使用证书）
- [ ] 杀毒软件不误报
- [ ] 更新日志已编写

### 文件清单

```
releases/
├── PrivacyGuard-36.4-Setup.exe    # 安装程序
├── PrivacyGuard-36.4-Setup.exe.sha256
├── PrivacyGuard-36.4.exe          # 便携版（单文件）
├── PrivacyGuard-36.4.exe.sha256
└── release-notes.md
```

---

## 完整打包脚本

创建 `build/build_windows_app.bat`：

```batch
@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

:: 配置
set APP_NAME=PrivacyGuard
set VERSION=36.4
set BUILD_DIR=%~dp0
set PROJECT_DIR=%BUILD_DIR%..
set DIST_DIR=%PROJECT_DIR%\dist
set RELEASE_DIR=%PROJECT_DIR%\releases

echo ========================================
echo   PrivacyGuard Windows 打包脚本
echo   版本: %VERSION%
echo ========================================
echo.

:: 检查虚拟环境
if not exist "%PROJECT_DIR%\venv\Scripts\activate.bat" (
    echo 错误: 未找到虚拟环境
    exit /b 1
)

call "%PROJECT_DIR%\venv\Scripts\activate.bat"

:: 步骤 1: 清理
echo [步骤] 清理旧构建...
rmdir /s /q "%DIST_DIR%" 2>nul
rmdir /s /q "%PROJECT_DIR%\build\build" 2>nul
mkdir "%RELEASE_DIR%" 2>nul

:: 步骤 2: 打包
echo [步骤] 执行 PyInstaller 打包...
pyinstaller --clean --noconfirm "%BUILD_DIR%PrivacyGuard_windows.spec"

if errorlevel 1 (
    echo [错误] 打包失败
    exit /b 1
)

:: 步骤 3: 复制附加文件
echo [步骤] 复制附加文件...
copy "%PROJECT_DIR%\LICENSE.txt" "%DIST_DIR%\" 2>nul
copy "%PROJECT_DIR%\README.md" "%DIST_DIR%\" 2>nul

:: 步骤 4: 生成校验和
echo [步骤] 生成校验和...
certutil -hashfile "%DIST_DIR%\%APP_NAME%.exe" SHA256 > "%RELEASE_DIR%\%APP_NAME%-%VERSION%.exe.sha256"

:: 步骤 5: 创建安装程序（如果 Inno Setup 可用）
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    echo [步骤] 创建安装程序...
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "%BUILD_DIR%PrivacyGuard_Setup.iss"

    certutil -hashfile "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe" SHA256 > "%RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe.sha256"
)

:: 完成
echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 输出文件:
echo   - %DIST_DIR%\%APP_NAME%.exe
echo   - %RELEASE_DIR%\%APP_NAME%-%VERSION%-Setup.exe

:: 计算文件大小
for %%I in ("%DIST_DIR%\%APP_NAME%.exe") do (
    echo   大小: %%~zI 字节
)

echo.
pause
```

---

## 相关资源

- [PyInstaller Windows 文档](https://pyinstaller.readthedocs.io/en/stable/usage.html#windows-specific-options)
- [Inno Setup 文档](http://www.jrsoftware.org/ishelp/)
- [Microsoft 代码签名指南](https://docs.microsoft.com/en-us/windows-hardware/drivers/dashboard/code-signing-cert-manage)
- [Windows Defender 误报申诉](https://www.microsoft.com/en-us/wdsi/filesubmission)

---

**最后更新**: 2026-02-17
**版本**: v36.4
**维护者**: 汪立
