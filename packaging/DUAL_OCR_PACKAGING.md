# PrivacyGuard v37.4.1 单 OCR 引擎打包说明

## 概述

v37.4.1 已完全移除 PaddleOCR，只保留 RapidOCR 单引擎架构。打包配置已相应简化。

## 变更记录

### v37.4.1 - 单引擎架构
- 移除 PaddleOCR 引擎及相关代码
- 移除 PaddleOCR 模型文件（约 100MB）
- 简化打包配置
- 修复 Windows 11 深色模式对话框显示问题

### v37.2.0 (历史) - 双 OCR 引擎
- 曾支持 RapidOCR + PaddleOCR 双引擎
- 因 PaddleOCR 3.4 Y 轴偏移问题无法解决，已完全移除

## 当前 OCR 架构

```
privacyguard/ocr/
├── __init__.py      # 模块导出
├── base.py          # 基类和数据结构
├── rapidocr.py      # RapidOCR 引擎（唯一引擎）
└── manager.py       # 引擎管理器（简化）
```

## PyInstaller 配置

### Windows

spec 文件: `packaging/windows/config/PrivacyGuard_windows.spec`

关键配置:
- 收集 `rapidocr_onnxruntime` 模块
- 排除 `paddleocr` 和 `paddlepaddle`
- 包含 VC++ 运行时 DLL

### macOS

spec 文件: `packaging/macos/config/PrivacyGuard.spec`

关键配置:
- 收集 `rapidocr_onnxruntime` 模块
- 排除 `paddleocr` 和 `paddlepaddle`
- 应用版本号: 37.4.1

## 打包步骤

### macOS

```bash
# 运行打包脚本
./packaging/macos/scripts/build_complete.sh

# 输出位置
# - 应用包: dist/PrivacyGuard.app
# - DMG 安装包: releases/macos/PrivacyGuard-v37.4.1-macOS.dmg
```

### Windows

```batch
# 完整打包（推荐）
packaging\windows\scripts\build_complete.bat

# 输出位置
# - 便携版: dist/PrivacyGuard/
# - 安装程序: releases/windows/PrivacyGuard-v37.4.1-Windows-Setup.exe
```

## 验证打包

启动应用后，检查日志输出：

```
[OCR] RapidOCR 已初始化
```

如果 OCR 未初始化，检查：
1. `rapidocr_onnxruntime` 是否正确安装
2. PyInstaller 是否正确收集模块

## 文件大小预估

- RapidOCR 模型: ~20MB
- 应用本身: ~150MB
- **总计**: ~170MB（压缩后约 80MB）

相比双引擎版本减少约 100MB（PaddleOCR 模型）。

## 注意事项

1. 确保 `requirements.txt` 中不包含 `paddleocr` 或 `paddlepaddle`
2. 打包前运行 `pip install -r requirements.txt` 安装最新依赖
3. Windows 打包需要安装 VC++ Redistributable 2015-2022

## 依赖检查

打包前请确认依赖：

```bash
# 检查 rapidocr 是否安装
python -c "import rapidocr_onnxruntime; print('OK')"

# 检查 paddleocr 是否已移除（应该报错）
python -c "import paddleocr" 2>&1 | grep "No module"
```

## 相关文档

- [Windows 打包指南](./windows/docs/WINDOWS_BUILD_GUIDE.md)
- [macOS 打包指南](./macos/docs/MACOS_BUILD_GUIDE.md)
- [项目 README](./README.md)
