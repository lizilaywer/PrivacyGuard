# PrivacyGuard v36.2 严重问题修复日志

**修复日期**: 2026-02-16
**修复版本**: v36.2
**备份位置**: `backups/v36.2_critical_fixes_20260216_205428/`

---

## 修复内容

### 1. 添加 atexit 导入 (行 9)
**问题**: 临时文件管理器依赖 `__del__` 进行清理，但 `__del__` 不保证执行
**修复**: 添加 `import atexit` 确保程序退出时清理临时文件

### 2. 修复 TempFileManager 类 (行 83-164)
**问题**: `__del__` 方法不保证执行，临时文件可能残留
**修复**:
- 添加类级别 `_instances` 列表跟踪所有实例
- 添加 `_register_atexit()` 类方法，使用 `atexit.register()` 注册清理函数
- 添加 `_cleanup_all()` 类方法，清理所有实例的临时文件
- 修改 `cleanup()` 方法，成功清理后从列表移除项目
- 保留 `__del__` 作为后备机制

**代码变更**:
```python
# 新增类变量和 atexit 支持
_instances = []

@classmethod
def _register_atexit(cls):
    if not hasattr(cls, '_atexit_registered'):
        atexit.register(cls._cleanup_all)
        cls._atexit_registered = True

@classmethod
def _cleanup_all(cls):
    for instance in list(cls._instances):
        try:
            instance.cleanup()
        except:
            pass
```

### 3. 添加路径验证函数 validate_safe_path (行 166-224)
**问题**: 文件路径直接传入 subprocess，存在命令注入和路径遍历风险
**修复**: 新增 `validate_safe_path()` 函数，验证:
- 路径非空
- 路径长度不超过 4096
- 不包含危险字符 (`;`, `|`, `&`, `$`, `` ` ``, 等)
- 规范化路径后检查路径遍历攻击
- 验证文件名有效性
- 验证文件扩展名（可选）

**函数签名**:
```python
def validate_safe_path(path, allowed_extensions=None):
    """验证文件路径安全（v36.2: 防止命令注入和路径遍历）"""
    return (is_safe: bool, error_msg: str or None)
```

### 4. 添加 tempfile 导入 (行 10)
**原因**: `validate_safe_path` 函数需要 `tempfile.gettempdir()`

---

## 验证步骤

### 1. 语法验证
```bash
python3 -c "import ast; ast.parse(open('main.py').read()); print('OK')"
# 结果: ✓ 语法检查通过
```

### 2. 功能验证（待执行）
- [ ] 应用正常启动
- [ ] 文件选择对话框正常工作
- [ ] PDF 文件可正常打开
- [ ] Word 文件可正常打开
- [ ] 临时文件正确创建和清理
- [ ] OCR 扫描正常工作
- [ ] 保存功能正常

### 3. 安全检查（待执行）
- [ ] 验证路径验证函数阻止危险路径
- [ ] 验证临时文件在程序退出时清理

---

## 回滚指南

如果修复导致问题，执行回滚:

```bash
# 1. 回滚到修复前版本
cp backups/v36.2_critical_fixes_20260216_205428/main.py.backup_before_critical_fixes main.py

# 2. 验证回滚后的语法
python3 -c "import ast; ast.parse(open('main.py').read()); print('OK')"

# 3. 测试应用启动
./start_app.sh
```

---

## 后续计划

本次修复完成后，如验证通过，下一步将处理：

1. **在 subprocess 调用中使用路径验证** - 在 `_convert_with_libreoffice` 等方法中调用 `validate_safe_path()`
2. **依赖安全审计** - 使用 `pip-audit` 检查依赖漏洞
3. **错误处理完善** - 替换裸 `except Exception`

---

## 修改统计

- 新增导入: 2 个 (`atexit`, `tempfile`)
- 修改类: 1 个 (`TempFileManager`)
- 新增函数: 1 个 (`validate_safe_path`)
- 修改行数: 约 90 行
- 新增行数: 约 60 行
