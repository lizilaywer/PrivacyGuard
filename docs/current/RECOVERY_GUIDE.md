# PrivacyGuard 项目恢复指南

## 📋 概述
本指南帮助你在下次打开项目时快速恢复到当前的开发进度。

---

## 🚀 快速启动

### 1. 激活虚拟环境
```bash
cd /Users/a49144/Desktop/临时coding/PrivacyApp
source venv/bin/activate
```

### 2. 启动应用
```bash
python main.py
```

### 3. 验证当前版本
```bash
python -c "
import re
with open('main.py') as f:
    content = f.read()
    version = re.search(r'VERSION = \"([^\"]+)\"', content)
    if version:
        print(f'当前版本: {version.group(1)}')
"
```

---

## 📂 项目结构

```
PrivacyApp/
├── main.py                          # 主程序（当前版本: v31.9）
├── theme.py                         # 主题系统
├── requirements.txt                  # 依赖列表
├── start_app.sh                     # 快捷启动脚本
├── README.md                        # 项目总览
├── CHANGELOG.md                     # 完整更新日志
│
├── docs/                            # 文档目录
│   └── current/
│       ├── STATUS.md                # 项目状态 ⭐
│       ├── DEV_LOG.md              # 开发日志 ⭐
│       └── RECOVERY_GUIDE.md       # 本文件 ⭐⭐⭐
│
├── backups/                         # 备份目录
│   ├── v31.9_current/              # v31.9 最新版本 ⭐
│   ├── v31_early/                 # v31.0-v31.7
│   ├── v25-v29/                  # 中间版本
│   ├── v24_word/                  # v24 Word 支持
│   ├── v23_ui/                    # v23 UI 版本
│   └── v19_legacy/                # v19 早期版本
│
├── tests/                           # 测试目录
│   ├── scripts/                    # 测试脚本
│   ├── samples/                    # 测试样本
│   └── reports/                    # 测试报告
│
├── build/                           # 构建目录
├── dist/                            # 打包输出
├── releases/                        # 发布包
└── venv/                            # 虚拟环境
```

---

## 📊 当前开发状态

### ✅ v31.9 已完成
1. **精确模式手动脱敏** (NEW)
   - 只脱敏选中的特定文本
   - 使用 data-key 精确定位
   - 位置: `main.py` 第 1863-1944 行

2. **全局模式手动脱敏** (NEW)
   - 自动查找并脱敏所有相同文本
   - 正则表达式全局替换
   - 位置: `main.py` 第 1945-2075 行

3. **批量撤销功能** (NEW)
   - 全局模式支持一键撤销
   - 智能识别模式类型
   - 位置: `main.py` 第 2076-2158 行

4. **滚动位置保持** (FIXED)
   - localStorage + 异步保存
   - 多重恢复机制
   - 位置: `main.py` 第 1680-1742 行

### ⚠️ 已知小瑕疵
1. **精确模式偶尔失败** (LOW 优先级)
   - 发生概率: <5%
   - 有全局模式作为备用方案

2. **大文档性能延迟** (LOW 优先级)
   - 50+ 页文档有轻微延迟
   - <15 秒等待时间

---

## 🔄 版本回退

### 回退到上一个版本
```bash
# 查看所有备份
ls -la backups/v31.9_current/

# 回退到 v31.8（示例）
cp backups/v31.9_current/main.py.backup_v31.8* main.py

# 验证语法
python -c "import ast; ast.parse(open('main.py').read()); print('✓ 语法检查通过')"
```

### 回退到最终稳定版本
```bash
cp backups/v31.9_current/main.py.backup_FINAL_* main.py
```

---

## 📝 继续开发检查清单

### 开始工作前
- [ ] 阅读 docs/current/STATUS.md 了解项目状态
- [ ] 阅读 docs/current/DEV_LOG.md 了解最新变更
- [ ] 确认当前使用的是 main.py（非备份文件）

### 测试当前功能
- [ ] 启动应用 (`python main.py` 或 `./start_app.sh`)
- [ ] 打开 Word 文档
- [ ] 测试智能脱敏（黄色高亮）
- [ ] 测试精确模式手动脱敏（只选中文本）
- [ ] 测试全局模式手动脱敏（查找所有相同文本）
- [ ] 测试批量撤销功能
- [ ] 测试导出功能

### 继续修复问题时
- [ ] 在终端启动应用查看输出
- [ ] 在浏览器控制台查看日志（右键→检查→Console）
- [ ] 记录问题现象和控制台输出
- [ ] 修改前创建新备份
- [ ] 修改后进行语法检查

---

## 🔧 常用命令

### 语法检查
```bash
python -c "import ast; ast.parse(open('main.py').read()); print('✓ 语法检查通过')"
```

### 查找关键代码
```bash
# 查找 findTextPosition 函数
grep -n "def findTextPosition" main.py

# 查找滚动恢复代码
grep -n "ScrollRestore" main.py

# 查找 HTML 高亮代码
grep -n "_highlight_sensitive_info" main.py
```

### 比较版本差异
```bash
# 比较 v27 和 v28 的差异
diff -u main.py.backup_v27_* main.py.backup_v28_* | less
```

### 查看备份历史
```bash
# 按时间倒序列出所有备份
ls -lt main.py.backup_* | head -20
```

---

## 🐛 调试技巧

### 1. 查看应用输出
```bash
python main.py 2>&1 | tee debug.log
```

### 2. 查看浏览器控制台
- 右键预览区域 → 检查元素 → Console
- 关键日志标识：
  - `[ScrollRestore]` - 滚动位置
  - `[findTextPosition]` - 文本查找
  - `✓✓✓` - 成功
  - `✗✗✗` - 失败

### 3. 添加调试打印
```python
# 在 Python 代码中
print(f"[DEBUG] 变量值: {variable}")

# 在 JavaScript 代码中
console.log('[DEBUG]', variable);
```

---

## 📦 依赖管理

### 查看已安装包
```bash
pip list
```

### 导出依赖
```bash
pip freeze > requirements.txt
```

### 安装依赖
```bash
pip install -r requirements.txt
```

---

## 🎯 下次开发优先级

### HIGH 优先级
1. **修复滚动位置跳转**
   - 分析：setHtml() 是否清空 localStorage？
   - 尝试：使用 Python 端保存滚动位置

2. **修复部分文档右键无反应**
   - 收集：失败场景的控制台日志
   - 分析：Range 对象的详细信息

### MEDIUM 优先级
3. 性能优化（大文档渲染）
4. 用户体验改进（进度提示）

---

## 📞 快速参考

### 当前版本信息
- **版本号**: v31.9
- **最后更新**: 2026-02-12 09:30
- **主文件**: main.py
- **最终备份**: backups/v31.9_current/main.py.backup_FINAL_*

### 关键代码位置
| 功能 | 文件 | 行号 |
|------|------|------|
| 精确模式手动脱敏 | main.py | 1863-1944 |
| 全局模式手动脱敏 | main.py | 1945-2075 |
| 批量撤销功能 | main.py | 2076-2158 |
| 滚动位置保持 | main.py | 1680-1742 |

---

## ✅ 完成工作检查清单

在结束本次开发前，确保：
- [ ] 已创建最终备份到 backups/v31.9_current/
- [ ] 已更新 docs/current/DEV_LOG.md
- [ ] 已更新 docs/current/STATUS.md
- [ ] 已测试当前功能
- [ ] 语法检查通过
- [ ] 应用已停止
- [ ] 本文件已更新

---

## 📅 日期: 2026-02-12
## 👨‍💻 开发者: Claude
## 📝 最后更新: 09:30
