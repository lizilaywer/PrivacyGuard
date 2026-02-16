# Windows 打包超详细手册

**适用版本**: v35.0
**更新日期**: 2026-02-12
**难度**: ⭐ 简单（跟着做就行）

---

## 📖 前言：这份手册是做什么的？

**你在这里**：
- ✅ 在 Mac 上用 Claude Code 准备好了所有文件
- ✅ 想在 Windows 上打包成 .exe
- ✅ 但不太熟悉 Windows 命令行

**这份手册会**：
- ✅ 手把手教你每一步
- ✅ 用最简单的语言
- ✅ 包含所有可能的错误解决方案

---

## 🎯 准备工作检查清单

在开始前，确保你有：

- [ ] **PrivacyGuard 项目文件夹**
  - 可以是 U 盘、网盘下载、或者从 Mac 复制过来
  - 位置随意，比如桌面、文档等

- [ ] **Windows 电脑**
  - Windows 10 或 11
  - 有管理员权限

- [ ] **网络连接**
  - 需要下载 Python 和依赖包

---

## 第一步：安装 Python

### 1.1 下载 Python

**打开浏览器，访问**：
```
https://www.python.org/downloads/
```

**点击 "Download Python 3.11.x"**（或最新版本）

### 1.2 安装 Python

**重要！必须勾选这两个选项**：

```
☑ Add python.exe to PATH
☑ Install launcher for all users (recommended)
```

然后点击 "Install Now"

**等待 2-3 分钟**，看到 "Setup was successful" 即可。

### 1.3 验证安装

**打开命令提示符**：
- 按 `Win + R`
- 输入 `cmd`
- 回车

**输入以下命令**：
```cmd
python --version
```

**应该看到**：
```
Python 3.11.x
```

✅ 如果看到版本号，说明安装成功！
❌ 如果提示"不是内部或外部命令"，说明没勾选 "Add to PATH"，需要重新安装

---

## 第二步：复制项目文件夹

### 2.1 找到 PrivacyGuard 文件夹

**你应该有这些文件**：
```
PrivacyGuard/
├── main.py                          # 主程序
├── theme.py                         # 主题文件
├── requirements.txt                 # 依赖列表
├── build/                           # 打包脚本
│   ├── install_dependencies.bat     # ⭐ 一键安装依赖
│   ├── build_windows.bat            # ⭐ 一键打包
│   └── PrivacyGuard_windows.spec    # PyInstaller 配置
└── docs/
    └── WINDOWS_BUILD_GUIDE.md       # 本手册
```

### 2.2 复制到 Windows

**选择一个位置**（推荐）：
```
C:\Users\你的用户名\Documents\PrivacyGuard
或
D:\PrivacyGuard
或
桌面\PrivacyGuard
```

**只要记住这个路径**，后面会用到！

---

## 第三步：安装依赖包

### 3.1 打开项目文件夹

**方法 1：文件资源管理器**
```
1. 打开"此电脑"或"文件资源管理器"
2. 找到 PrivacyGuard 文件夹
3. 双击进入
```

**方法 2：从命令行**
```cmd
cd C:\Users\你的用户名\Documents\PrivacyGuard
```

### 3.2 一键安装依赖

**找到并双击**：
```
build/install_dependencies.bat
```

**会看到**：
```
========================================
PrivacyGuard Windows 依赖安装
========================================

[1/3] 检查 Python...
Python 3.11.x

[2/3] 升级 pip...
...

[3/3] 安装依赖包...
Collecting PyQt6
  Downloading PyQt6-...
...
Successfully installed PyQt6-...
...

========================================
安装完成！
========================================
按任意键继续...
```

**可能需要 3-5 分钟**，耐心等待！

### 3.3 常见问题

#### ❌ 问题 1：提示"不是内部或外部命令"

**原因**：Python 没有添加到 PATH

**解决**：
1. 重新安装 Python
2. **务必勾选** "Add python.exe to PATH"
3. 或手动添加到系统环境变量

#### ❌ 问题 2：提示"权限不足"

**原因**：需要管理员权限

**解决**：
1. 右键 `install_dependencies.bat`
2. 选择"以管理员身份运行"

#### ❌ 问题 3：下载速度慢

**解决**：使用国内镜像源
```cmd
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 第四步：一键打包

### 4.1 运行打包脚本

**找到并双击**：
```
build/build_windows.bat
```

**会看到**：
```
========================================
PrivacyGuard Windows 打包脚本
========================================

正在打包，请稍候...
============================================================
  PrivacyGuard Windows 打包脚本
  版本: 35.0
============================================================

[步骤] 检查 Python 环境
[信息] Python 版本: 3.11.x
[信息] Python 路径: C:\Users\...\python.exe

[步骤] 检查依赖包
✓ PyInstaller
✓ PyQt6
✓ PyMuPDF
...

[步骤] 清理旧构建文件
已清理: build\build
已清理: dist

[步骤] 构建 Windows 可执行文件
INFO: PyInstaller: 6.18.0
INFO: Python: 3.11.x
INFO: Platform: Windows-10-10.0.19045-SP0
...
INFO: Building EXE from EXE-00.toc
...
INFO: Building COLLECT COLLECT-00.toc
INFO: Building COLLECT COLLECT-00.toc completed successfully.

[步骤] 创建安装程序（可选）
已创建: releases\PrivacyGuard-35.0-Windows.zip

========================================
打包完成！
========================================
按任意键继续...
```

**可能需要 5-10 分钟**，更长时间也很正常！

### 4.2 打包完成

**检查输出**：
```
dist/PrivacyGuard/
├── PrivacyGuard.exe          ⭐ 这是主程序！
├── _internal/                 # 依赖文件
│   ├── PyQt6/
│   ├── rapidocr_onnxruntime/
│   └── ...
└── 其他文件...
```

**大小**：大约 150-200 MB

### 4.3 常见问题

#### ❌ 问题 1：提示"找不到 spec 文件"

**原因**：spec 文件路径不对

**解决**：
1. 确保 `build/PrivacyGuard_windows.spec` 存在
2. 检查文件内容是否正确
3. 尝试修改 spec 文件中的路径

#### ❌ 问题 2：提示"缺少模块"

**原因**：某些依赖包没安装

**解决**：
```cmd
pip install 缺少的模块名
```

#### ❌ 问题 3：打包失败，提示错误

**解决**：
1. 查看错误信息
2. 复制错误信息搜索解决方案
3. 或查看手册的"故障排除"章节

---

## 第五步：测试打包结果

### 5.1 运行生成的 .exe

**找到并双击**：
```
dist/PrivacyGuard/PrivacyGuard.exe
```

**应该看到**：
```
PrivacyGuard 应用窗口启动
显示版本号: v35.0
```

### 5.2 功能测试

**基本功能**：
- [ ] 应用启动
- [ ] 打开 PDF 文件
- [ ] OCR 识别
- [ ] 手动脱敏
- [ ] 保存脱敏文件

**高级功能**（需要 LibreOffice）：
- [ ] 打开 Word 文档
- [ ] Word 预览
- [ ] Word 脱敏
- [ ] 保存 Word 文档

### 5.3 分发给其他用户

**方法 1：压缩整个文件夹**
```
1. 右键 dist/PrivacyGuard 文件夹
2. 选择"发送到" > "压缩(zipped)文件夹"
3. 得到 PrivacyGuard.zip
4. 发送给其他 Windows 用户
```

**方法 2：使用我生成的 zip**
```
releases/PrivacyGuard-35.0-Windows.zip
```

**用户使用方法**：
1. 解压 zip 文件
2. 双击 `PrivacyGuard.exe`
3. 完成！

---

## 🔧 故障排除

### 问题 1：双击 .exe 没反应

**可能原因 A**：被杀毒软件拦截

**解决**：
1. 暂时关闭杀毒软件
2. 或添加到白名单
3. 或从"以管理员身份运行"

**可能原因 B**：缺少运行库

**解决**：
- 安装 [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### 问题 2：应用启动后闪退

**解决**：
1. 从命令行运行，查看错误信息：
   ```cmd
   cd dist\PrivacyGuard
   PrivacyGuard.exe
   ```
2. 查看错误信息
3. 根据错误信息解决问题

### 问题 3：OCR 不工作

**解决**：
1. 检查 `_internal/rapidocr_onnxruntime/` 文件夹
2. 确保有 `.onnx` 模型文件
3. 如果没有，重新打包

### 问题 4：Word 功能不能用

**原因**：需要安装 LibreOffice

**解决**：
1. 下载 LibreOffice: https://www.libreoffice.org/download/
2. 安装到默认路径
3. 重启 PrivacyGuard

---

## 📊 性能优化

### 减小 .exe 体积

**当前大小**：150-200 MB

**优化方法**：
1. 使用 UPX 压缩（已在配置中启用）
2. 排除不需要的模块
3. 使用虚拟环境打包

### 提升启动速度

**优化方法**：
1. 减少启动时加载的模块
2. 延迟加载非关键功能
3. 使用 --one-file 模式（单文件）

---

## 🎓 进阶：手动命令行打包

如果你想自己控制打包过程：

### 打开命令提示符

```cmd
# 按 Win + R
# 输入 cmd
# 回车
```

### 导航到项目目录

```cmd
cd C:\Users\你的用户名\Documents\PrivacyGuard
```

### 手动打包

```cmd
# 激活虚拟环境（如果有）
venv\Scripts\activate

# 执行打包
python -m PyInstaller --clean build/PrivacyGuard_windows.spec

# 等待完成...
```

### 高级选项

```cmd
# 只生成 .exe（不打包依赖）
python -m PyInstaller --onefile main.py

# 调试模式（显示控制台）
python -m PyInstaller --console build/PrivacyGuard_windows.spec

# 添加图标
python -m PyInstaller --icon=build/PrivacyGuard.ico build/PrivacyGuard_windows.spec
```

---

## 📞 获取帮助

### 遇到问题？

1. **查看日志**
   - `build/PrivacyGuard/warn-PrivacyGuard.txt`
   - 打包过程的警告信息

2. **查看错误**
   - 命令行中的错误信息
   - 复制错误信息搜索

3. **社区求助**
   - PyInstaller GitHub Issues
   - Stack Overflow
   - PyQt6 官方论坛

---

## ✅ 检查清单

打包完成后，确认：

- [ ] .exe 文件已生成
- [ ] .exe 可以正常启动
- [ ] 基本功能测试通过
- [ ] 生成了发布包（zip）
- [ ] 文档已更新
- [ ] 备份了源代码

---

## 🎉 完成！

恭喜你完成了 Windows 版本的打包！

**现在你可以**：
1. 自己使用 PrivacyGuard for Windows
2. 分发给朋友
3. 发布到网上
4. 收集用户反馈

**下一步**：
- 收集用户反馈
- 修复发现的 bug
- 准备下一个版本

---

## 附录：文件结构

**完整的项目结构**：
```
PrivacyGuard/
├── main.py                          # 主程序（已修改，兼容 Windows）
├── theme.py                         # 主题文件
├── requirements.txt                 # 依赖列表
│
├── build/                           # 打包脚本和配置
│   ├── install_dependencies.bat     # ⭐ 一键安装依赖
│   ├── build_windows.bat            # ⭐ 一键打包
│   ├── build_windows_app.py         # Python 打包脚本
│   ├── PrivacyGuard_windows.spec    # PyInstaller 配置
│   ├── PrivacyGuard.ico             # Windows 图标
│   └── build_macos_app.sh           # macOS 打包脚本（Windows 不用）
│
├── dist/                            # 打包输出（自动生成）
│   └── PrivacyGuard/
│       ├── PrivacyGuard.exe         # ⭐⭐⭐ 这就是最终产品！
│       └── _internal/               # 依赖文件
│
├── releases/                        # 发布包（自动生成）
│   ├── PrivacyGuard-35.0-Windows.zip
│   └── PrivacyGuard-35.0-macOS.dmg
│
├── docs/                            # 文档
│   ├── WINDOWS_BUILD_GUIDE.md       # 本手册
│   ├── CROSS_PLATFORM_GUIDE.md      # 跨平台指南
│   └── ...
│
└── backups/                         # 版本备份
    └── v35.0/
```

---

**祝你好运！🍀**

有问题随时查阅本手册，或查阅 `CROSS_PLATFORM_GUIDE.md` 了解更多技术细节。
