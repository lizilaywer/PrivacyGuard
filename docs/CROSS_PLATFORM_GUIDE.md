# PrivacyGuard 跨平台开发与发布指南

> 本文档描述当前项目在 macOS / Windows 两个平台上的真实开发与打包策略。

---

## 当前结论

1. 核心业务代码是跨平台的
2. 主开发环境仍然是 macOS
3. Windows 主要用于打包与安装包验证
4. 版本统一来自 `version.txt`
5. 当前推荐打包链已经统一维护在 `packaging/` 和 `docs/packaging/`

---

## 当前平台分工

### macOS

- 主开发环境
- 主测试环境
- 负责 `.app` / `.dmg` 构建
- 可选执行 Developer ID 签名与 notarization

### Windows

- 负责 `.exe` / 安装包构建
- 验证 VC++ 运行库、onnxruntime、安装器行为
- 主要输出：
  - `PrivacyGuard-v<version>-Windows-Portable.zip`
  - `PrivacyGuard-<version>-Setup.exe`

---

## 代码兼容性现状

### 已经跨平台的部分

- PyQt6 GUI
- PyMuPDF PDF 处理
- RapidOCR OCR 识别
- `os.path` / `pathlib`
- `tempfile`
- `QFileDialog`

### 需要重点关注的部分

- `.doc` 转换链路依赖 LibreOffice / antiword 可用性
- Windows 机器需要正确的 VC++ 运行库
- 打包后的 OCR DLL 与 onnxruntime 兼容性要在 Windows 上实机验证

---

## 当前版本与打包策略

- 当前版本：`v37.7.4`
- 版本标识：`37.7.4 - Release Audit and Final Polish`
- 版本唯一来源：`version.txt`

### macOS 打包

```bash
bash packaging/macos/scripts/build_complete.sh
```

### Windows 打包

```cmd
packaging\windows\scripts\build_complete.bat
```

### Windows 安装包

```cmd
packaging\windows\scripts\3_build_with_setup.bat
```

---

## 关键原则

1. 不要再从 `main.py` 硬读版本号，统一读 `version.txt`
2. 不要在 macOS 上假定 Windows 运行库问题已经被覆盖
3. 不要让 `main.py` 和 `privacyguard/*` 的核心逻辑继续漂移
4. 打包文档优先阅读：
   - `docs/packaging/README.md`
   - `docs/packaging/windows-packaging-guide.md`
   - `docs/packaging/macos-packaging-guide.md`

---

## 当前建议验证

### 开发日常

```bash
python3 -m compileall -q main.py privacyguard tests
python3 -m unittest \
  tests.unit.test_mixed_pdf_ocr \
  tests.test_path_validation \
  tests.unit.test_ocr_api \
  tests.unit.test_package_imports \
  tests.unit.test_pdf_text_hit_dedup \
  tests.unit.test_app_config \
  tests.unit.test_word_replace_rules \
  tests.unit.test_batch_word_replace \
  -v
```

### 发布前

- macOS 至少验证 `.app` / `.dmg` 能打开
- Windows 至少验证便携版能启动、安装包能安装
- PDF / Word / OCR 主流程至少手测一次

---

## 当前结语

这个项目现在的跨平台策略不是“两个平台各写一套”，而是：

- 一套共享代码
- macOS 主开发
- Windows 主打包验证
- 文档、版本、打包方案统一围绕 `version.txt` 收敛

## 2026-03-18 本轮复核结果

- macOS：
  - 已在当前机器实际执行 `bash packaging/macos/scripts/build_complete.sh`
  - `.app` 构建成功
  - 当前环境缺少 `create-dmg`
  - `hdiutil` 本次未成功创建 DMG
  - 脚本已按回退逻辑复制 `releases/macos/PrivacyGuard.app`
- Windows：
  - 已完成脚本链、spec、版本资源、Inno Setup 配置与文档一致性复核
  - 当前机器为 macOS，未实际执行 `.bat` 与安装包链路
  - 对外发布前仍需在 Windows 真机执行：
    - `packaging\windows\scripts\build_complete.bat`
    - `packaging\windows\scripts\3_build_with_setup.bat`

最后更新：2026-03-18
