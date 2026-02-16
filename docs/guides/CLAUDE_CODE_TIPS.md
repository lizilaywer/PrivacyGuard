# Claude Code 开发经验与技巧

本文档记录使用 Claude Code 进行 PrivacyGuard 项目开发的经验总结。

---

## 目录

1. [Claude Code 核心技巧](#claude-code-核心技巧)
2. [双平台开发策略](#双平台开发策略)
3. [高效开发流程](#高效开发流程)
4. [常见问题解决](#常见问题解决)
5. [最佳实践](#最佳实践)

---

## Claude Code 核心技巧

### 1. 项目上下文管理

**CLAUDE.md 的重要性**:
- 在项目根目录维护 `CLAUDE.md` 文件
- 包含项目概述、关键命令、架构说明
- 记录已知问题和开发注意事项

**示例结构**:
```markdown
# CLAUDE.md

## Project Overview
- 项目名称、版本、主要语言
- 核心功能说明

## Development Commands
- 启动命令
- 测试命令
- 构建命令

## Architecture
- 核心类和数据流
- 关键文件位置

## Known Issues
- 当前已知问题
- 临时解决方案
```

### 2. 分步骤开发

**原则**: 大任务拆分为小步骤

**方法**:
1. 先描述整体目标
2. Claude 会自动规划步骤
3. 逐步实现，每步验证
4. 遇到问题及时调整

**示例**:
```
❌ 不好的方式:
"帮我实现一个完整的用户认证系统"

✅ 好的方式:
"我需要添加用户认证功能，首先实现登录界面"
```

### 3. 上下文保持

**技巧**:
- 在同一个对话中完成相关任务
- 引用之前的代码和讨论
- 使用一致的术语和命名

**示例**:
```
"基于刚才实现的登录功能，现在添加密码重置"
```

### 4. 调试辅助

**让 Claude 帮助调试**:
1. 提供完整的错误信息
2. 说明期望行为
3. 提供相关代码上下文

**示例**:
```
"运行时出现这个错误：
[粘贴完整错误信息]

这是相关代码：
[粘贴代码]

期望的行为是..."
```

---

## 双平台开发策略

### 1. 路径处理

**统一使用 pathlib**:
```python
from pathlib import Path

# 好的方式
config_path = Path(__file__).parent / "config.json"

# 避免的方式
config_path = os.path.dirname(__file__) + "/config.json"
```

### 2. 编码处理

**统一使用 UTF-8**:
```python
# 文件读写指定编码
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Windows 控制台处理
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

### 3. 平台检测

**条件执行平台相关代码**:
```python
import sys
import platform

def get_platform():
    """获取当前平台信息"""
    return {
        'system': platform.system(),  # 'Darwin', 'Windows', 'Linux'
        'python': sys.version,
        'is_macos': sys.platform == 'darwin',
        'is_windows': sys.platform == 'win32',
    }
```

### 4. 打包配置

**macOS (PyInstaller)**:
```python
# PrivacyGuard.spec
exe = EXE(
    ...
    name='PrivacyGuard',
    icon='PrivacyGuard.icns',
    target_arch='universal2',  # 支持 Intel 和 Apple Silicon
)
```

**Windows (PyInstaller)**:
```python
# PrivacyGuard_windows.spec
exe = EXE(
    ...
    name='PrivacyGuard',
    icon='PrivacyGuard.ico',
    console=False,  # 不显示控制台窗口
)
```

---

## 高效开发流程

### 1. 每日开发流程

```
1. 拉取最新代码
   └─> git pull origin main

2. 查看项目状态
   └─> 阅读 docs/current/STATUS.md

3. 开始开发
   └─> 告诉 Claude 当前目标

4. 测试验证
   └─> python main.py
   └─> 运行测试脚本

5. 更新文档
   └─> 更新 DEV_LOG.md

6. 提交代码
   └─> git add . && git commit -m "描述"
```

### 2. 功能开发流程

```
1. 需求分析
   └─> 明确功能目标
   └─> 确定验收标准

2. 设计方案
   └─> 与 Claude 讨论实现方案
   └─> 评估技术可行性

3. 编码实现
   └─> 小步迭代
   └─> 及时测试

4. 代码审查
   └─> 让 Claude 检查代码
   └─> 处理警告和建议

5. 测试验证
   └─> 功能测试
   └─> 回归测试

6. 文档更新
   └─> 更新 CHANGELOG
   └─> 更新用户文档
```

### 3. Bug 修复流程

```
1. 复现问题
   └─> 记录复现步骤
   └─> 收集错误信息

2. 定位原因
   └─> 提供信息给 Claude
   └─> 分析根本原因

3. 实现修复
   └─> 最小化修改范围
   └─> 保持代码风格一致

4. 验证修复
   └─> 确认问题已解决
   └─> 检查是否引入新问题

5. 回归测试
   └─> 测试相关功能
   └─> 确保无副作用
```

---

## 常见问题解决

### 1. Claude 不理解上下文

**解决方案**:
- 在请求中明确引用之前的讨论
- 提供必要的代码片段
- 说明当前状态和目标

**示例**:
```
"继续之前的登录功能开发，当前已完成用户验证，
现在需要添加 session 管理。这是当前的代码：
[粘贴相关代码]"
```

### 2. 生成的代码不符合项目风格

**解决方案**:
- 在 CLAUDE.md 中说明代码风格
- 提供现有代码作为参考
- 明确指出命名约定

### 3. 复杂问题分解

**解决方案**:
```
1. 先让 Claude 分析问题
2. 讨论解决方案
3. 分步骤实现
4. 每步验证
```

### 4. 跨文件修改

**解决方案**:
- 明确列出需要修改的文件
- 说明每个文件的修改目的
- 让 Claude 确认修改范围

---

## 最佳实践

### 1. 文档同步

**保持文档更新**:
- 代码变更时同步更新文档
- 使用一致的术语
- 记录决策原因

### 2. 版本管理

**提交策略**:
- 频繁小提交优于大提交
- 写清晰的提交信息
- 关联 Issue 或任务

### 3. 测试习惯

**测试优先**:
- 新功能先写测试
- 修改后运行回归测试
- 保持测试覆盖率

### 4. 沟通技巧

**有效沟通**:
- 明确目标
- 提供上下文
- 验证理解
- 及时反馈

### 5. 问题记录

**记录问题**:
- 在 DEV_LOG.md 记录遇到的问题
- 记录解决方案
- 方便后续参考

---

## Claude Code 快捷命令

### 常用命令

```bash
# 查看帮助
/help

# 开始新会话
/clear

# 查看项目状态
/status

# 提交代码
/commit
```

### 开发技巧

```
# 让 Claude 分析代码
"分析这段代码的潜在问题"

# 让 Claude 重构代码
"重构这段代码，提高可读性"

# 让 Claude 添加文档
"为这个函数添加文档字符串"

# 让 Claude 写测试
"为这个函数编写单元测试"
```

---

## 项目特定经验

### PrivacyGuard 开发经验

1. **PDF 处理**: 使用 PyMuPDF，注意内存管理
2. **OCR 集成**: RapidOCR 效果好，但需要处理依赖
3. **跨平台 UI**: PyQt6 稳定，但打包体积大
4. **手动脱敏**: HTML 占位符替换策略关键
5. **双平台打包**: PyInstaller 配置需要注意差异

### 关键文件

| 文件 | 用途 | 更新频率 |
|------|------|----------|
| `main.py` | 核心代码 | 高 |
| `CLAUDE.md` | Claude 上下文 | 中 |
| `CHANGELOG.md` | 版本记录 | 每次发布 |
| `docs/current/DEV_LOG.md` | 开发日志 | 每日 |
| `docs/current/STATUS.md` | 项目状态 | 每周 |

---

## 总结

使用 Claude Code 开发的关键:

1. **保持上下文**: 维护好 CLAUDE.md
2. **小步迭代**: 大任务分解为小步骤
3. **及时验证**: 每步修改后测试
4. **文档同步**: 代码和文档同步更新
5. **记录经验**: 遇到的问题和解决方案

---

**文档创建**: 2026-02-13
**最后更新**: 2026-02-13
**版本**: 1.0
