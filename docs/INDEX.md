# PrivacyGuard 文档索引

本文档提供 PrivacyGuard 脱敏卫士项目所有文档的快速导航。

---

## 项目状态

- **当前版本**: v36.0
- **支持平台**: macOS 11.0+ (主要), Windows 10/11
- **最后更新**: 2026-02-14

---

## 快速导航

### 项目元信息 (.project/)

| 文档 | 说明 | 位置 |
|------|------|------|
| **项目状态** | 快速状态概览 | [../.project/STATUS.md](../.project/STATUS.md) |
| **下一步计划** | 待办事项 | [../.project/NEXT_STEPS.md](../.project/NEXT_STEPS.md) |
| **快速恢复** | 5分钟恢复开发 | [../.project/QUICK_RECOVERY.md](../.project/QUICK_RECOVERY.md) |

### 新手入门

| 文档 | 说明 | 位置 |
|------|------|------|
| **快速参考** | 常用命令和流程 | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |
| **项目概览** | 项目基本信息 | [../README.md](../README.md) |
| **开发环境设置** | 环境配置指南 | [../CLAUDE.md](../CLAUDE.md) |

### 开发文档

| 文档 | 说明 | 位置 |
|------|------|------|
| **开发日志** | 每日开发记录 | [current/DEV_LOG.md](current/DEV_LOG.md) |
| **开发流程** | 标准开发流程 | [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) |
| **路线图** | 长期规划 | [ROADMAP.md](ROADMAP.md) |
| **恢复指南** | 问题恢复步骤 | [current/RECOVERY_GUIDE.md](current/RECOVERY_GUIDE.md) |

### 指南文档

| 文档 | 说明 | 位置 |
|------|------|------|
| **Claude Code 技巧** | AI 辅助开发经验 | [guides/CLAUDE_CODE_TIPS.md](guides/CLAUDE_CODE_TIPS.md) |
| **测试指南** | 测试方法和流程 | [guides/TESTING_GUIDE.md](guides/TESTING_GUIDE.md) |
| **快速测试** | 快速验证清单 | [guides/QUICK_TEST.md](guides/QUICK_TEST.md) |

### 平台文档

#### macOS

| 文档 | 说明 | 位置 |
|------|------|------|
| **构建指南** | macOS 打包说明 | [../packaging/macos/docs/BUILD_GUIDE.md](../packaging/macos/docs/BUILD_GUIDE.md) |
| **平台说明** | macOS 平台概述 | [../packaging/macos/README.md](../packaging/macos/README.md) |

#### Windows

| 文档 | 说明 | 位置 |
|------|------|------|
| **构建指南** | Windows 打包说明 | [../packaging/windows/docs/BUILD_GUIDE.md](../packaging/windows/docs/BUILD_GUIDE.md) |
| **打包日志** | 打包问题和解决方案 | [../packaging/windows/docs/BUILD_LOG.md](../packaging/windows/docs/BUILD_LOG.md) |
| **故障排除** | 常见问题解答 | [../packaging/windows/docs/TROUBLESHOOTING.md](../packaging/windows/docs/TROUBLESHOOTING.md) |
| **测试指南** | Windows 测试方法 | [../packaging/windows/docs/TESTING_GUIDE.md](../packaging/windows/docs/TESTING_GUIDE.md) |
| **发布说明** | Windows 版本说明 | [../packaging/windows/docs/RELEASE_NOTES.md](../packaging/windows/docs/RELEASE_NOTES.md) |
| **平台说明** | Windows 平台概述 | [../packaging/windows/README.md](../packaging/windows/README.md) |

### 合规文档

| 文档 | 说明 | 位置 |
|------|------|------|
| **信息脱敏标准** | 中国标准规范 | [信息脱敏标准规范.md](信息脱敏标准规范.md) |
| **合规性评估** | 合规性分析报告 | [合规性评估报告.md](合规性评估报告.md) |

### 跨平台文档

| 文档 | 说明 | 位置 |
|------|------|------|
| **跨平台指南** | 双平台开发策略 | [CROSS_PLATFORM_GUIDE.md](CROSS_PLATFORM_GUIDE.md) |
| **平台实现总结** | 平台支持实现 | [../packaging/IMPLEMENTATION_SUMMARY.md](../packaging/IMPLEMENTATION_SUMMARY.md) |
| **Windows 构建指南** | 详细 Windows 构建 | [WINDOWS_BUILD_GUIDE.md](WINDOWS_BUILD_GUIDE.md) |

### 发布文档

| 版本 | 说明 | 位置 |
|------|------|------|
| **v35.0** | 最新版本发布 | [../releases/v35.0-release/](../releases/v35.0-release/) |
| **v31.9** | 稳定版本发布 | [../releases/v31.9-release/](../releases/v31.9-release/) |

---

## 按用途分类

### 我要开始开发

1. 阅读 [../.project/STATUS.md](../.project/STATUS.md) 快速了解状态
2. 阅读 [CLAUDE.md](../CLAUDE.md) 了解项目
3. 参考 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) 获取常用命令
4. 查看 [guides/CLAUDE_CODE_TIPS.md](guides/CLAUDE_CODE_TIPS.md) 学习技巧

### 我要打包发布

1. macOS: 阅读 [packaging/macos/docs/BUILD_GUIDE.md](../packaging/macos/docs/BUILD_GUIDE.md)
2. Windows: 阅读 [packaging/windows/docs/BUILD_GUIDE.md](../packaging/windows/docs/BUILD_GUIDE.md)
3. 查看 [packaging/windows/docs/BUILD_LOG.md](../packaging/windows/docs/BUILD_LOG.md) 了解常见问题
4. 更新 [CHANGELOG.md](../CHANGELOG.md)

### 我遇到了问题

1. 查看 [current/RECOVERY_GUIDE.md](current/RECOVERY_GUIDE.md)
2. Windows 问题查看 [packaging/windows/docs/TROUBLESHOOTING.md](../packaging/windows/docs/TROUBLESHOOTING.md)
3. 查看开发日志 [current/DEV_LOG.md](current/DEV_LOG.md)

### 我要了解合规要求

1. 阅读 [信息脱敏标准规范.md](信息脱敏标准规范.md)
2. 查看 [合规性评估报告.md](合规性评估报告.md)

---

## 文件结构图

```
PrivacyApp/
├── README.md                    # 项目概览
├── CHANGELOG.md                 # 版本历史
├── CLAUDE.md                    # Claude Code 上下文
├── main.py                      # 主程序
├── theme.py                     # 主题系统
│
├── .project/                    # 项目元信息 (从这里开始)
│   ├── STATUS.md               # 快速状态
│   ├── NEXT_STEPS.md           # 下一步计划
│   └── QUICK_RECOVERY.md       # 快速恢复
│
├── docs/                        # 文档目录
│   ├── INDEX.md                 # 本文件 - 文档索引
│   ├── QUICK_REFERENCE.md       # 快速参考
│   ├── ROADMAP.md               # 路线图
│   ├── DEVELOPMENT_WORKFLOW.md  # 开发流程
│   ├── CROSS_PLATFORM_GUIDE.md  # 跨平台指南
│   ├── WINDOWS_BUILD_GUIDE.md   # Windows 构建详解
│   │
│   ├── current/                 # 当前开发文档
│   │   ├── DEV_LOG.md           # 开发日志
│   │   └── RECOVERY_GUIDE.md    # 恢复指南
│   │
│   ├── guides/                  # 指南文档
│   │   ├── CLAUDE_CODE_TIPS.md  # Claude Code 技巧
│   │   ├── TESTING_GUIDE.md     # 测试指南
│   │   └── QUICK_TEST.md        # 快速测试
│   │
│   └── archive/                 # 归档文档
│
├── backups/                     # 版本备份
│   ├── v36/                    # 当前版本
│   ├── v35.x/                  # 上个版本
│   └── _archive/               # 历史归档
│
├── packaging/                   # 打包配置
│   ├── macos/                   # macOS 打包配置
│   └── windows/                 # Windows 打包配置
│
├── releases/                    # 发布记录
│   └── v36.0-release/
│
├── build/                       # 构建脚本
├── dist/                        # 构建输出
├── tests/                       # 测试文件
└── venv/                        # Python 虚拟环境
```

---

## 版本历史

| 版本 | 日期 | 主要更新 | 状态 |
|------|------|----------|------|
| v36.0 | 2026-02-14 | Windows 深色模式优化 | 当前版本 |
| v35.x | 2026-02-13 | Windows 平台支持、图片批量选择 | 已发布 |
| v33.x | 2026-02-12 | 自适应视图系统 | 已发布 |
| v31.9 | 2026-02-12 | 双模式手动脱敏系统 | 稳定版 |
| v30.3 | 2026-02-11 | Ultra Compact Highlighting | 已发布 |
| v24.0 | 2026-02-11 | Word 文档支持 | 已发布 |

---

## 联系方式

- **项目仓库**: GitHub
- **问题反馈**: GitHub Issues
- **最后更新**: 2026-02-13

---

**提示**: 使用 Ctrl+F / Cmd+F 快速搜索关键词
