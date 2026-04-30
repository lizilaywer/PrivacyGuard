# PrivacyGuard OCR 打包说明（RapidOCR 单引擎）

## 概述

历史文件名沿用 `DUAL_OCR_PACKAGING.md`，但当前项目已固定为 **RapidOCR 单引擎**。  
Windows 与 macOS 的 active 打包配置都按单 OCR 路径维护，不再包含 PaddleOCR 依赖。

当前发布基线：`v37.7.4`  
版本来源：项目根目录 `version.txt`

---

## 当前 OCR 架构

```text
privacyguard/ocr/
├── __init__.py
├── base.py
├── manager.py
├── mixed_pdf.py
├── rapidocr.py
└── text_pdf.py
```

说明：
- `text_pdf.py` 处理文本型 PDF 命中
- `mixed_pdf.py` 处理混合型 PDF 中的图片块 OCR
- 当前不存在双引擎切换发布路径

---

## 关键打包文件

### Windows

- spec: `packaging/windows/config/PrivacyGuard_windows.spec`
- 历史增强 spec: `packaging/windows/config/PrivacyGuard_windows_v2.spec`（保留归档，不作为当前正式主链）
- 版本资源生成：`packaging/windows/scripts/generate_version_info.py`
- 推荐脚本：
  - 便携版：`packaging/windows/scripts/build_complete.bat`
  - 安装版：`packaging/windows/scripts/3_build_with_setup.bat`
- 产物：
  - `releases/windows/PrivacyGuard-v<version>-Windows-Portable.zip`
  - `releases/windows/PrivacyGuard-<version>-Setup.exe`

### macOS

- spec: `packaging/macos/config/PrivacyGuard.spec`
- 推荐脚本：`packaging/macos/scripts/build_complete.sh`
- 产物：
  - `releases/macos/PrivacyGuard-<version>-macOS.dmg`
  - `releases/macos/PrivacyGuard-<version>-macOS.dmg.sha256`

---

## 打包前检查

```bash
python3 -c "import rapidocr_onnxruntime; print('rapidocr ok')"
```

```bash
python3 -c "import paddleocr" 2>&1 | grep -E "No module named|ModuleNotFoundError"
```

第二条命令应显示未安装 PaddleOCR，说明当前环境仍然是单 OCR 打包基线。

---

## 注意事项

1. 依赖安装请以 `requirements.txt` 为准。
2. Windows 发布建议同时验证 `launcher_wrapper.bat` 启动路径。
3. macOS 若需要签名与公证，请使用环境变量传入证书和 notary 凭据，避免手改脚本。
4. 版本号统一维护在 `version.txt`，Windows EXE 版本资源由构建脚本自动同步。
5. Windows / macOS 打包脚本已统一改为使用当前环境中的 PyInstaller，并使用项目内缓存目录，避免依赖全局缓存。
6. PyInstaller 打包模块导入失败修复属于 Windows 打包可导入性修复，不改变 OCR 单引擎结构。

最后更新：2026-03-18
