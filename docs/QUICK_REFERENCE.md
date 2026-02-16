# PrivacyGuard 快速参考卡片

这是一个快速参考指南，包含常用的命令和工作流程。

---

## 项目状态

**当前版本**: v35.0
**支持平台**: macOS 11.0+, Windows 10/11
**最后更新**: 2026-02-13

---

## 🚀 快速启动

### macOS
```bash
# 启动应用
python main.py

# 或使用快速启动脚本
./start_app.sh
```

### Windows
```cmd
# 启动应用
python main.py
```

---

## 📦 版本信息

### 查看当前版本

```bash
# 方法一：查看代码
grep "VERSION" main.py

# 方法二：使用脚本
python scripts/check_progress.py

# 方法三：在应用中
帮助 → 关于
```

### 更新版本号

编辑 `main.py` 第 34 行：

```python
VERSION = "36.0 - 新功能描述"
```

---

## 🔄 标准开发流程

```
1. macOS 开发
   └─> python main.py

2. 本地测试
   └─> python tests/scripts/test_stability.py

3. 提交代码
   └─> git add . && git commit -m "描述"

4. 推送到远程
   └─> git push origin main

5. Windows 打包（在 Windows 上）
   └─> platforms\windows\build\build_windows.bat
```

---

## 🛠️ 常用命令

### Git 操作

```bash
# 查看状态
git status

# 创建开发分支
git checkout -b dev-v36

# 提交代码
git add .
git commit -m "v36.0: 新功能"

# 推送到远程
git push origin dev-v36

# 查看日志
git log --oneline -10

# 创建标签
git tag -a v36.0 -m "Release v36.0"
git push origin v36.0
```

### 测试命令

```bash
# 启动应用
python main.py

# 运行测试
python tests/scripts/test_stability.py

# 验证 Word 格式
python tests/scripts/verify_word_format.py

# 语法检查
python -c "import ast; ast.parse(open('main.py').read())"
```

### 打包命令

```bash
# macOS 打包
cd build
bash build_macos_app.sh

# Windows 打包（在 Windows 上）
cd platforms\windows\build
build_windows.bat

# 或使用 Python 脚本
python build_windows.py
```

### Windows 特定命令

```cmd
# 安装依赖
cd platforms\windows\build
install_dependencies.bat

# 检查编码
chcp 65001

# 验证构建
certutil -hashfile PrivacyGuard-35.0-Windows.zip SHA256
```

---

## 📂 关键文件位置

```
PrivacyApp/
├── main.py                      # 核心代码 (第 34 行: VERSION)
├── theme.py                     # 主题文件
├── requirements.txt             # 依赖列表
├── CHANGELOG.md                 # 更新日志
├── CLAUDE.md                    # Claude Code 上下文
├── docs/
│   ├── INDEX.md                # 文档索引
│   ├── QUICK_REFERENCE.md      # 快速参考（本文件）
│   ├── ROADMAP.md              # 路线图
│   ├── DEVELOPMENT_WORKFLOW.md # 开发流程
│   ├── current/
│   │   ├── DEV_LOG.md          # 开发日志
│   │   └── STATUS.md           # 项目状态
│   └── guides/
│       └── CLAUDE_CODE_TIPS.md # Claude Code 开发经验
├── build/
│   ├── build_macos_app.sh      # macOS 打包脚本
│   └── PrivacyGuard.spec       # PyInstaller 配置 (macOS)
├── platforms/
│   ├── macos/                  # macOS 平台
│   │   └── docs/
│   │       └── BUILD_GUIDE.md  # macOS 构建指南
│   └── windows/                # Windows 平台
│       ├── build/
│       │   ├── build_windows.bat      # Windows 打包脚本
│       │   ├── build_windows.py       # Python 打包脚本
│       │   └── PrivacyGuard_windows.spec  # PyInstaller 配置
│       └── docs/
│           ├── BUILD_GUIDE.md         # Windows 构建指南
│           ├── BUILD_LOG.md           # Windows 打包日志
│           └── TROUBLESHOOTING.md     # 故障排除
└── scripts/
    └── check_progress.py       # 进度查询
```

---

## 🎯 版本迭代检查清单

### 开发新版本时

- [ ] 查看路线图 `docs/ROADMAP.md`
- [ ] 创建开发分支 `git checkout -b dev-vXX`
- [ ] 更新版本号 `main.py`
- [ ] 开发和测试功能
- [ ] 更新开发日志 `docs/current/DEV_LOG.md`

### 发布新版本时

- [ ] 所有测试通过
- [ ] 更新 CHANGELOG.md
- [ ] 更新版本号
- [ ] macOS 打包测试
- [ ] Windows 打包测试
- [ ] 创建 Git 标签
- [ ] 推送到远程
- [ ] 创建 GitHub Release
- [ ] 双平台功能验证

### Windows 打包检查

- [ ] Python 环境正确 (3.11+)
- [ ] 依赖安装完成
- [ ] 图标文件存在 (PrivacyGuard.ico)
- [ ] spec 文件配置正确
- [ ] 编码设置为 UTF-8
- [ ] 路径处理跨平台兼容

---

## 📚 文档索引

| 文档 | 用途 | 位置 |
|------|------|------|
| **文档索引** | 所有文档导航 | `docs/INDEX.md` |
| **开发流程** | 如何开发和发布 | `docs/DEVELOPMENT_WORKFLOW.md` |
| **路线图** | 长期规划 | `docs/ROADMAP.md` |
| **开发日志** | 开发历史 | `docs/current/DEV_LOG.md` |
| **项目状态** | 当前状态 | `docs/current/STATUS.md` |
| **更新日志** | 版本历史 | `CHANGELOG.md` |
| **Claude Code 技巧** | AI 开发经验 | `docs/guides/CLAUDE_CODE_TIPS.md` |
| **Windows 构建** | Windows 打包 | `platforms/windows/docs/BUILD_GUIDE.md` |
| **Windows 打包日志** | 打包问题记录 | `platforms/windows/docs/BUILD_LOG.md` |
| **Windows 故障排除** | 常见问题 | `platforms/windows/docs/TROUBLESHOOTING.md` |
| **macOS 构建** | macOS 打包 | `platforms/macos/docs/BUILD_GUIDE.md` |

---

## 🔍 问题排查

### 应用无法启动

```bash
# 检查 Python 环境
python --version

# 检查依赖
pip list | grep PyQt6

# 重新安装依赖
pip install -r requirements.txt
```

### 打包失败

```bash
# 清理缓存
pip cache purge
rm -rf build dist __pycache__

# 重新安装 PyInstaller
pip install --force-reinstall pyinstaller
```

### Git 问题

```bash
# 查看远程仓库
git remote -v

# 同步远程
git fetch origin
git pull origin main
```

---

## 💡 最佳实践

### 开发习惯

1. **小步提交**: 频繁提交，每次提交一个功能点
2. **写好日志**: 每次更新 `docs/DEV_LOG.md`
3. **先测后发**: 本地测试通过后再发布
4. **版本规范**: 遵循语义化版本号

### 提交信息格式

```
<版本号>: <简短描述>

详细说明：
- 功能 A
- 修复 B
```

示例：
```
v36.0: 添加批量处理功能

- 支持选择多个文件
- 添加进度显示
- 优化内存占用
```

---

## ⚡ 快捷操作

### 一键命令

```bash
# 查看项目进度
python scripts/check_progress.py

# 快速启动菜单
./scripts/quick_start.sh

# 语法检查
python -c "import ast; ast.parse(open('main.py').read())"

# 统计代码行数
wc -l main.py
```

### 别名建议（添加到 ~/.bashrc 或 ~/.zshrc）

```bash
# PrivacyGuard 别名
alias pg-start='cd ~/Desktop/临时coding/PrivacyApp && python main.py'
alias pg-test='cd ~/Desktop/临时coding/PrivacyApp && python tests/scripts/test_stability.py'
alias pg-build='cd ~/Desktop/临时coding/PrivacyApp/build && bash build_macos_app.sh'
alias pg-status='cd ~/Desktop/临时coding/PrivacyApp && python scripts/check_progress.py'
alias pg-log='cd ~/Desktop/临时coding/PrivacyApp && cat docs/DEV_LOG.md'
```

---

## 📞 获取帮助

| 问题类型 | 查看文档 |
|----------|----------|
| 如何开发 | `docs/DEVELOPMENT_WORKFLOW.md` |
| 当前进度 | `docs/STATUS.md` |
| 未来规划 | `docs/ROADMAP.md` |
| Windows 打包 | `platforms/windows/docs/BUILD_GUIDE.md` |
| macOS 打包 | `platforms/macos/docs/BUILD_GUIDE.md` |
| 常见问题 | `platforms/windows/docs/TROUBLESHOOTING.md` |

---

**提示**: 将此文件加入书签，方便随时查阅！

**最后更新**: 2026-02-13
**当前版本**: v35.0 (双平台支持)
