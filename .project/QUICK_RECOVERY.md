# PrivacyGuard 快速恢复指南

> 5 分钟快速恢复开发状态

## 第一步：读取状态

```bash
cd /Users/a49144/Desktop/临时coding/PrivacyApp

# 查看当前状态
cat .project/STATUS.md

# 查看待办事项
cat .project/NEXT_STEPS.md

# 查看开发日志
cat docs/current/DEV_LOG.md
```

## 第二步：启动环境

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行应用
python main.py

# 或使用启动脚本
./start_app.sh
```

## 第三步：验证环境

```bash
# 语法检查
python -c "import ast; ast.parse(open('main.py').read()); print('OK')"

# 查看版本
python -c "
import re
with open('main.py') as f:
    m = re.search(r'VERSION = \"([^\"]+)\"', f.read())
    print(f'版本: {m.group(1)}' if m else '版本未找到')
"

# 检查依赖
pip list | grep -E "PyQt6|PyMuPDF|python-docx"
```

## 核心代码位置

| 功能 | 文件位置 |
|------|---------|
| 版本号 | `main.py` 第 28 行 |
| 默认规则 | `main.py` 第 40-50 行 |
| PDF 导入 | `main.py` `_open_pdf()` |
| OCR 扫描 | `main.py` `OCRWorker.run()` |
| Word 处理 | `main.py` `_open_word()` |
| 手动脱敏 | `main.py` `add_manual_redaction()` |
| 主题切换 | `theme.py` |

## 常见操作

### 创建备份
```bash
cp main.py "backups/v36/main.py.backup_$(date +%Y%m%d_%H%M%S)"
```

### 回滚代码
```bash
# 查看备份
ls -la backups/v36/

# 恢复
cp backups/v36/main.py.backup_xxx main.py
```

### 构建应用
```bash
# macOS
bash build/build_macos_app.sh

# 输出位置
ls -la dist/
```

### 调试模式
```bash
export PRIVACYGUARD_DEBUG=True
python main.py
```

## 项目结构速览

```
PrivacyApp/
├── main.py              # 主程序
├── theme.py             # 主题系统
├── .project/            # 项目状态（从这里开始）
├── docs/                # 文档
│   └── current/         # 当前开发文档
├── backups/             # 版本备份
├── build/               # 构建脚本
├── dist/                # 构建输出
├── tests/               # 测试文件
└── venv/                # Python 虚拟环境
```

## 相关文档

- [项目状态](./STATUS.md)
- [下一步计划](./NEXT_STEPS.md)
- [Claude 开发指南](../CLAUDE.md)
- [详细恢复指南](../docs/current/RECOVERY_GUIDE.md)
