# 2026年2月28日 - 打包方案更新记录

**版本**: v37.6.1
**更新内容**: 拖拽功能打包适配

---

## 更新摘要

今日实现的文件拖拽打开功能（v37.6.0/v37.6.1）**不需要修改打包配置**，因为：

1. **纯代码实现**：拖拽功能完全使用 PyQt6 原生 API，无新增依赖
2. **无资源文件**：不需要添加图标、图片或其他资源
3. **跨平台兼容**：macOS 和 Windows 使用相同的代码逻辑

---

## 已更新的打包文件

### 1. macOS 打包配置

**文件**: `packaging/macos/config/PrivacyGuard.spec`

**更新内容**:
```diff
- 'CFBundleVersion': '37.4.2',
- 'CFBundleShortVersionString': '37.4.2',
+ 'CFBundleVersion': '37.6.1',
+ 'CFBundleShortVersionString': '37.6.1',
```

### 2. Windows 打包配置

**文件**: `packaging/windows/config/PrivacyGuard_windows.spec`
**文件**: `packaging/windows/config/PrivacyGuard_windows_v2.spec`

**更新内容**: 无需修改

原因：Windows spec 文件使用动态版本号（从主程序读取），且拖拽功能无额外依赖。

### 3. 打包文档

**文件**: `packaging/README.md`

**更新内容**:
- 添加 v37.6.1 更新记录
- 记录拖拽功能的支持情况

---

## 打包测试建议

### macOS 测试项

- [ ] 拖拽 PDF 文件到应用图标打开
- [ ] 拖拽 Word 文件到预览区域打开
- [ ] 拖拽图片文件到预览区域打开
- [ ] Word 打开后继续拖拽其他文件

### Windows 测试项

- [ ] 从资源管理器拖拽文件到应用窗口
- [ ] 拖拽时边框颜色变化（绿色/红色）
- [ ] 多图片拖拽合并为 PDF
- [ ] Word 打开后继续拖拽其他文件

---

## 注意事项

1. **拖拽功能在打包后完全可用**，无需额外配置
2. **macOS 签名**：拖拽功能不受签名影响，未签名应用也可正常使用
3. **Windows 权限**：不需要管理员权限即可使用拖拽

---

*记录于 2026年2月28日*
