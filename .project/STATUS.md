# PrivacyGuard 项目状态

> 快速查看当前项目状态，完整文档请参阅 `docs/` 目录

## 快速信息

| 项目 | 值 |
|------|-----|
| **版本** | v36.0 |
| **状态** | 正式发布 |
| **主平台** | macOS |
| **上次更新** | 2026-02-14 |
| **代码行数** | ~2600 行（main.py） |

## 核心文件

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序（单体架构） |
| `theme.py` | 主题系统（深色/浅色模式） |
| `requirements.txt` | Python 依赖 |
| `CLAUDE.md` | Claude 开发指南 |

## 快速命令

```bash
# 进入项目目录
cd /Users/a49144/Desktop/临时coding/PrivacyApp

# 激活虚拟环境并运行
source venv/bin/activate && python main.py

# 语法检查
python -c "import ast; ast.parse(open('main.py').read()); print('OK')"

# 构建 macOS 应用
bash build/build_macos_app.sh
```

## 主要功能

- PDF 智能脱敏（OCR + 文本层）
- Word 文档脱敏（.docx/.doc）
- 手动标记（精确模式 + 全局模式）
- 批量撤销
- 深色/浅色主题

## 版本历史摘要

| 版本 | 主要特性 |
|------|---------|
| v36.0 | Windows 深色模式优化 |
| v35.x | Windows 兼容性改进 |
| v33.x | 自适应视图、性能优化 |
| v31.9 | 稳定版：手动脱敏核心功能 |

## 下一步

参见 [.project/NEXT_STEPS.md](./NEXT_STEPS.md)

## 详细文档

- [开发日志](../docs/current/DEV_LOG.md)
- [恢复指南](../docs/current/RECOVERY_GUIDE.md)
- [文档索引](../docs/INDEX.md)
