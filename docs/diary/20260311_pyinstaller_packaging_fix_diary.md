# 打包问题排查日记 - PyInstaller 模块导入失败

**日期**: 2026-03-11
**作者**: 开发者
**版本**: v37.7.3 (待发布)
**关键词**: PyInstaller, ModuleNotFoundError, f-string, 反斜杠, hiddenimports

---

## 早上：打包后的噩梦

今天本该是个轻松的日子——版本 v37.7.2 已经准备好了，打包脚本也运行得很顺利。我信心满满地打开打包好的应用，结果弹出了一个让我心凉半截的错误窗口：

```
Traceback (most recent call last):
  File "main.py", line 17, in <module>
  File "pyimod02_importers.py", line 457, in exec_module
  File "privacyguard\__init__.py", line 23, in <module>
  File "pyimod02_importers.py", line 457, in exec_module
  File "privacyguard\utils\__init__.py", line 19, in <module>
ModuleNotFoundError: No module named 'privacyguard.utils.security'
```

**内心OS**: "什么？security.py 明明存在啊！我亲眼看到它躺在 dist 目录里的！"

---

## 第一轮尝试：怀疑 PyInstaller 的 hiddenimports

我的第一反应是 PyInstaller 没有正确检测到 `privacyguard` 包的子模块。毕竟这是一个本地包，不是通过 pip 安装的。

于是我开始修改 spec 文件：

```python
# 添加了 collect_submodules
privacyguard_hiddenimports = collect_submodules('privacyguard')

# 手动添加所有子模块
privacyguard_hiddenimports.extend([
    'privacyguard',
    'privacyguard.utils',
    'privacyguard.utils.security',
    # ... 更多模块
])
```

重新打包，结果：**还是同样的错误**。

---

## 第二轮尝试：怀疑相对导入

我开始怀疑是相对导入的问题。PyInstaller 在处理相对导入时可能有些问题。

于是我修改了三个 `__init__.py` 文件，把相对导入改成绝对导入：

```python
# 修改前
from .security import validate_safe_path, resource_path

# 修改后
from privacyguard.utils.security import validate_safe_path, resource_path
```

重新打包，结果：**还是同样的错误**。

---

## 第三轮尝试：怀疑数据文件冲突

我在网上看到有人说，如果同一个模块既作为 hiddenimports 又作为 datas 被包含，会导致问题。于是我检查了 spec 文件，发现我确实用了 `collect_all('privacyguard')` 把 .py 文件作为数据文件复制了。

我移除了 `privacyguard_datas_all`，只保留 hiddenimports。

重新打包，结果：**还是同样的错误**。

---

## 第四轮尝试：创建 Hook 文件

我创建了一个 PyInstaller hook 文件 `hook-privacyguard.py`，试图强制包含所有子模块：

```python
hiddenimports = collect_submodules('privacyguard')
if not hiddenimports:
    hiddenimports = [
        'privacyguard',
        'privacyguard.utils',
        'privacyguard.utils.security',
        # ...
    ]
```

重新打包，结果：**还是同样的错误**。

---

## 第五轮尝试：创建 Runtime Hook

我又创建了一个 runtime hook，试图在运行时把 privacyguard 目录添加到 sys.path：

```python
# runtime_hook_privacyguard.py
import sys
import os

if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
    # 添加各种路径到 sys.path
```

重新打包，结果：**还是同样的错误**。

---

## 真相大白：打包日志中的关键线索

就在我快要放弃的时候，我仔细查看了打包日志，发现了一行之前忽略的警告：

```
78 WARNING: Failed to collect submodules for 'privacyguard' because importing 'privacyguard' raised:
File "C:\...\privacyguard\utils\security.py", line 56
    return False, f"路径包含危险字符: {repr('\\')}"
                                             ^
SyntaxError: f-string expression part cannot include a backslash
```

**原来问题不在 PyInstaller，而在代码本身！**

---

## 根因分析

Python 3.11 引入了更严格的 f-string 语法检查。在 f-string 的 `{}` 表达式中，**不能直接使用反斜杠**。

```python
# 错误写法（Python 3.11 会报 SyntaxError）
f"路径包含危险字符: {repr('\\')}"

# 正确写法
backslash_repr = repr('\\')  # 先在 f-string 外部处理
f"路径包含危险字符: {backslash_repr}"
```

这个语法错误导致 `privacyguard` 包无法被导入，进而导致 `collect_submodules('privacyguard')` 返回空列表，最终导致打包后的应用找不到这个模块。

---

## 最终修复

修改 `privacyguard/utils/security.py`：

```python
# 非 Windows 下拒绝反斜杠（可疑转义）
# v37.7.3: 修复 f-string 中不能使用反斜杠的语法错误
backslash_char = '\\'
if not is_windows and backslash_char in path:
    backslash_repr = repr(backslash_char)
    return False, f"路径包含危险字符: {backslash_repr}"
```

同时也修复了另一处类似问题：

```python
for char in shell_metacharacters:
    if char in path:
        char_repr = repr(char)  # 先提取 repr
        return False, f"路径包含危险字符: {char_repr}"
```

---

## 经验教训

1. **仔细阅读打包日志**：不要忽略任何 WARNING，它们可能包含关键信息。

2. **Python 版本兼容性**：Python 3.11 对 f-string 的语法检查更严格了，不能在 `{}` 内直接使用反斜杠。

3. **问题定位要准确**：我花了很多时间在 PyInstaller 配置上，但真正的问题在源代码的语法错误。

4. **SyntaxError 是致命的**：即使文件存在，如果有语法错误，Python 也无法导入它，PyInstaller 自然也检测不到。

5. **本地包的特殊性**：`collect_submodules()` 对于本地未安装的包可能返回空，但这不是唯一的原因。

---

## 技术细节记录

### PyInstaller 打包流程中的关键点

1. **Analysis 阶段**：分析模块依赖，此时如果源文件有语法错误，会导致模块无法被分析。

2. **hiddenimports**：手动指定的隐藏导入，但如果模块本身有语法错误，指定了也没用。

3. **Hook 文件**：可以在打包时动态添加模块，但同样受限于源文件语法正确性。

4. **Runtime Hook**：在运行时修改 sys.path，但如果模块语法错误，还是无法导入。

### 本次修改的文件清单

1. `privacyguard/__init__.py` - 相对导入改为绝对导入
2. `privacyguard/utils/__init__.py` - 相对导入改为绝对导入
3. `privacyguard/ocr/__init__.py` - 相对导入改为绝对导入
4. `privacyguard/utils/security.py` - **关键修复**：f-string 反斜杠语法错误
5. `packaging/windows/config/PrivacyGuard_windows.spec` - 多次调整 hiddenimports 配置
6. `packaging/windows/config/hook-privacyguard.py` - 新增 hook 文件
7. `packaging/windows/config/runtime_hook_privacyguard.py` - 新增 runtime hook

---

## 下一步

1. 重新打包验证修复是否生效
2. 更新版本号到 v37.7.3
3. 更新相关文档

---

*写于 2026-03-11，一个被 f-string 反斜杠折磨的下午。*
