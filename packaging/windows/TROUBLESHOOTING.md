# PrivacyGuard Windows 故障排除指南

## 常见错误及解决方案

### 错误: `ImportError: DLL load failed while importing onnxruntime_pybind11_state`

**完整错误信息:**
```
ImportError: DLL load failed while importing onnxruntime_pybind11_state: 动态链接库(DLL)初始化例程失败
```

**原因:**
此错误表示 Visual C++ Redistributable 运行时库缺失或版本过旧。`onnxruntime` (OCR 引擎) 需要以下 DLL 文件：
- `vcruntime140.dll`
- `vcruntime140_1.dll` ⭐ **关键 DLL，经常缺失**
- `msvcp140.dll`

**解决方案:**

1. **下载并安装最新版 VC++ Redistributable:**
   ```
   https://aka.ms/vs/17/release/vc_redist.x64.exe
   ```

2. **备用下载地址:**
   ```
   https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
   ```

3. **安装后重启应用**

**验证安装:**
运行 `packaging/windows/scripts/check_vcredist.bat` 检查是否所有 DLL 都已安装。

---

### 预防措施（打包时）

如果在打包后的机器上遇到此问题，可以采取以下措施：

1. **使用启动器包装器 (launcher_wrapper.bat)**
   - 在运行主程序前检查必需的 DLL
   - 如果缺失，显示友好的错误提示

2. **在安装程序中检测 (PrivacyGuard_Setup.iss)**
   - 安装前检查 VC++ Redistributable
   - 如果缺失，提示用户下载

3. **打包 VC++ DLL（不推荐，可能有许可证问题）**
   - 可以在 spec 文件中包含系统 DLL
   - 但最好让用户安装官方 Redistributable

---

### 其他常见错误

#### 应用启动后立即关闭
- **可能原因:** 缺少依赖 DLL
- **解决:** 运行 `check_vcredist.bat` 检查环境

#### OCR 扫描失败
- **可能原因:** `vcruntime140_1.dll` 缺失
- **解决:** 安装最新版 VC++ Redistributable

#### 图标显示异常
- **可能原因:** PyInstaller 资源打包问题
- **解决:** 重新运行打包脚本

---

## 联系支持

如果以上方法无法解决问题，请提供以下信息：
1. Windows 版本 (如: Windows 10 21H2, Windows 11 23H2)
2. 完整的错误信息截图
3. 运行 `check_vcredist.bat` 的输出结果
