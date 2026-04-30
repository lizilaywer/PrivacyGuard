# PrivacyGuard Windows 打包指南（目录内索引）

此文档保留在 `packaging/windows/docs/` 仅用于就地导航。
Windows 打包完整指南统一维护在：

- `docs/packaging/windows-packaging-guide.md`

---

## 当前打包基线

- 当前版本：`v37.7.4`
- 版本来源：项目根目录 `version.txt`

---

## 常用脚本入口

- 初始化环境：`packaging/windows/scripts/1_init_environment.bat`
- 构建 EXE：`packaging/windows/scripts/2_build_exe.bat`
- 完整打包：`packaging/windows/scripts/build_complete.bat`
- 构建安装包：`packaging/windows/scripts/3_build_with_setup.bat`
- 依赖校验：`packaging/windows/scripts/verify_dependencies.py`

正式发布建议：

- 便携版只看：`packaging/windows/scripts/build_complete.bat`
- 安装版只看：`packaging/windows/scripts/3_build_with_setup.bat`

---

## 打包注意事项

### PyInstaller 打包常见问题

1. **模块导入失败**（2026-03-11 修复）
   - 症状：`ModuleNotFoundError: No module named 'privacyguard.utils.security'`
   - 原因：源代码存在语法错误，导致模块无法被导入
   - 解决：检查打包日志中的 WARNING，修复语法错误

2. **f-string 语法兼容性**
   - Python 3.11 不允许在 f-string 的 `{}` 表达式中直接使用反斜杠
   - 错误示例：`f"路径包含危险字符: {repr('\\')}"`
   - 正确写法：先将反斜杠赋值给变量，再在 f-string 中使用

---

## 说明

- 详细参数、签名策略、发布流程请以 `docs/packaging/windows-packaging-guide.md` 为准。
- 本文件只保留最小索引，避免与主文档重复维护。
- 当前默认安装器版本与 EXE 版本资源已经同步到 `v37.7.4`。
- 当前 Windows 打包脚本统一通过 `python -m PyInstaller` 执行，并使用 `build\.pyinstaller-cache`。
- `packaging/windows/scripts/` 已清理历史兼容与解除阻止脚本，仅保留当前正式主链与必要诊断工具。
- 2026-03-18 已完成脚本链、spec、版本资源与 Inno Setup 配置复核；最终发布前仍需 Windows 真机执行便携包与安装包链路。

最后同步：2026-03-18
