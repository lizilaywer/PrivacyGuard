# PrivacyGuard OCR 打包说明（RapidOCR 单引擎）

## 概述

当前项目固定为 **RapidOCR 单引擎**（v37.7.14 cp44 起从 `rapidocr-onnxruntime` 升级到 `rapidocr` v3.9.2，PP-OCRv6 模型）。Windows 与 macOS 的打包配置都按单 OCR 路径维护。

当前发布基线：`v40.1.1`（v40.1.1）
版本来源：项目根目录 `version.txt`

---

## 当前 OCR 架构

```text
privacyguard/ocr/
├── __init__.py
├── base.py
├── mixed_pdf.py      # 混合型 PDF 中的图片块 OCR
├── rapidocr.py       # RapidOCR 引擎封装（默认引擎）
├── seal_detection.py
├── signature_detection.py
└── text_pdf.py       # 文本型 PDF 命中
```

说明：
- `text_pdf.py` 处理文本型 PDF 命中（基于 PyMuPDF 文本层搜索）
- `mixed_pdf.py` 处理混合型 PDF 中的图片块 OCR（裁剪 → 渲染 → OCR → 坐标回投）
- `rapidocr.py` 封装 RapidOCR v3.x，`is_available()` 做导入探测，`recognize()` 适配 v3.x 的 `RapidOCROutput` 结构
- 不存在双引擎切换路径（`manager.py` 为历史遗留死代码，cp118 审计保留，打包 hook 仍收集但不调用）

---

## 关键打包文件

### Windows

- spec: `packaging/windows/config/PrivacyGuard_windows.spec`
- hook: `packaging/windows/config/hook-privacyguard.py`（收集 privacyguard + 防御性收集 rapidocr/onnxruntime/cv2 数据）
- runtime hook: `packaging/windows/config/runtime_hook_privacyguard.py`（cp119: 仅注入 app_dir，**不注入子包目录**——此前注入 privacyguard/ocr 等子包目录会破坏相对导入）
- 版本资源生成：`packaging/windows/scripts/generate_version_info.py`
- 依赖校验：`packaging/windows/scripts/verify_dependencies.py`（构建前守门，build_complete.bat Phase 3 强制调用）
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

## RapidOCR 完整导入链（打包易漏点）

`from rapidocr import RapidOCR` 触发的完整链路（任一环节缺依赖都会报 OCREngineUnavailableError）：

```text
rapidocr
  → rapidocr.main (RapidOCR 类)
    → inference_engine.base 类级 OmegaConf.load(default_models.yaml)
      → omegaconf
        → omegaconf.grammar.gen: from antlr4 import *  ← cp116 修复点
      → yaml (PyYAML)                                  ← cp115 修复点
    → rapidocr/utils/download_file.py: from tqdm import tqdm  ← cp117 修复点
  → onnxruntime (InferenceSession 加载 .onnx 模型)
    → flatbuffers / sympy / mpmath / packaging (传递依赖)
```

spec 中 `collect_all` 覆盖：rapidocr / onnxruntime / numpy(core+_core) / pyclipper / shapely / omegaconf / colorlog / six / requests / yaml / antlr4 / tqdm / cobble / mammoth / psutil / bs4 / soupsieve / lxml / msoffcrypto。

---

## 打包前检查

```bash
# Windows
.\venv_win\Scripts\python.exe packaging/windows/scripts/verify_dependencies.py

# 验证 rapidocr 完整导入链（开发环境）
.\venv_win\Scripts\python.exe -c "from rapidocr import RapidOCR; print('rapidocr ok')"
```

`verify_dependencies.py` 退出码 0 表示依赖完整可收集，非 0 会阻断 `build_complete.bat`。

---

## 注意事项

1. 依赖安装以 `requirements.txt` 为准（cp117 已显式 pin tqdm/cobble/antlr4/omegaconf/colorlog）。
2. **不要在 sys.path 注入 privacyguard 子包目录**（cp119 修复的根因）——会破坏相对导入，导致打包后 RapidOCR 不可用。
3. Windows 发布建议同时验证 `launcher_wrapper.bat` 启动路径（含 VC++ DLL 预检）。
4. macOS 若需签名与公证，用环境变量传入证书和 notary 凭据（`PRIVACYGUARD_CODESIGN_IDENTITY` / `PRIVACYGUARD_NOTARY_PROFILE`），避免手改脚本。
5. macOS 端 `venvmac` 当前仍用旧版 rapidocr-onnxruntime==1.2.3（PP-OCRv4），未升级到 v3.9.2；更换 macOS 系统后需同步升级。
6. 版本号统一维护在 `version.txt`，Windows EXE 版本资源由 `generate_version_info.py` 自动生成（禁止手改 `version_info.txt`）。

最后更新：2026-08-04（cp119）
