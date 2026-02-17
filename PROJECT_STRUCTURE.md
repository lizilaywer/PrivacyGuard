# PrivacyGuard 项目结构说明

> 整理后的项目目录结构，适合开源展示

---

## 目录结构

```
PrivacyApp/
│
├── 📄 核心文件
│   ├── main.py                 # 主程序（约4200行）
│   ├── theme.py                # 主题系统
│   └── requirements.txt        # Python依赖列表
│
├── 📁 packaging/               # 【NEW】打包配置（核心改进）
│   │
│   ├── windows/                # Windows打包方案（完全独立）
│   │   ├── scripts/            # 一键打包脚本
│   │   │   ├── 1_初始化环境.bat
│   │   │   ├── 2_一键打包.bat
│   │   │   ├── 3_完整打包带安装程序.bat
│   │   │   └── 4_仅创建安装程序.bat
│   │   ├── config/             # 配置文件
│   │   │   ├── PrivacyGuard_windows.spec
│   │   │   └── PrivacyGuard_Setup.iss
│   │   └── assets/             # 资源文件
│   │       └── icon.ico
│   │
│   └── macos/                  # macOS打包方案（完全独立）
│       ├── scripts/            # 打包脚本
│       │   ├── build_macos_app.sh
│       │   ├── sign_macos_app.sh
│       │   └── notarize_macos_app.sh
│       ├── config/             # 配置文件
│       │   ├── PrivacyGuard.spec
│       │   └── entitlements.plist
│       └── assets/             # 资源文件
│           └── PrivacyGuard.icns
│
├── 📁 build/                   # 【仅保留】构建缓存（.gitignore）
│
├── 📁 docs/                    # 文档目录
│   ├── README.md               # 项目主文档
│   ├── INDEX.md                # 文档索引
│   ├── CHANGELOG.md            # 版本历史
│   ├── CLAUDE.md               # Claude开发指南
│   ├── CROSS_PLATFORM_GUIDE.md # 跨平台指南
│   ├── DEVELOPMENT_WORKFLOW.md # 开发工作流
│   ├── FUTURE_ROADMAP.md       # 未来路线图
│   │
│   ├── archive/                # 归档文档
│   ├── current/                # 当前开发文档
│   ├── guides/                 # 使用指南
│   ├── legal/                  # 法律文档
│   ├── marketing/              # 营销推广
│   │   └── 开源宣传规划方案.md
│   └── packaging/              # 打包指南
│       ├── macos-packaging-guide.md
│       └── windows-packaging-guide.md
│
├── 📁 tests/                   # 测试目录
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   ├── e2e/                    # 端到端测试
│   ├── samples/                # 测试样本文件
│   └── reports/                # 测试报告
│
├── 📁 scripts/                 # 脚本工具
│   ├── build/                  # 构建脚本
│   ├── utils/                  # 实用工具
│   ├── check_progress.py       # 进度检查
│   └── quick_start.sh          # 快速启动
│
├── 📁 tools/                   # 开发工具
│   ├── icon/                   # 图标工具
│   └── docs/                   # 文档工具
│
├── 📁 releases/                # 发布包
│   ├── windows/                # Windows发布包
│   ├── macos/                  # macOS发布包
│   ├── v36.4/                  # 各版本发布
│   └── archive/                # 历史发布包
│
├── 📁 backups/                 # 开发备份
│   └── archive/                # 历史归档
│
├── 📁 dist/                    # 构建输出
│   ├── PrivacyGuard.app/       # macOS应用
│   └── PrivacyGuard/           # Windows应用
│
├── 📁 logs/                    # 日志文件
│
├── 📁 venv/                    # Python虚拟环境
│
└── 📄 配置文件
    ├── .gitignore              # Git忽略规则
    ├── LICENSE                 # 开源协议
    └── PROJECT_STRUCTURE.md    # 本文件
```

---

## 关键文件说明

### 核心代码

| 文件 | 行数 | 说明 |
|------|------|------|
| `main.py` | ~4,200 | 主程序，包含所有功能实现 |
| `theme.py` | ~90 | 主题系统，浅色/深色模式 |
| `requirements.txt` | ~30 | Python依赖包列表 |

### 文档

| 文档 | 受众 | 内容 |
|------|------|------|
| `README.md` | 用户 | 项目介绍、快速开始 |
| `CHANGELOG.md` | 开发者/用户 | 版本历史记录 |
| `CLAUDE.md` | 开发者 | Claude Code开发指南 |
| `docs/marketing/开源宣传规划方案.md` | 运营 | 完整推广策略 |
| `packaging/README.md` | 开发者 | 打包系统说明 |
| `packaging/windows/docs/` | 开发者 | Windows打包指南 |
| `packaging/macos/docs/` | 开发者 | macOS打包指南 |
| `docs/packaging/*.md` | 开发者 | 详细打包文档（旧） |

### 打包脚本

| 脚本 | 路径 | 用途 |
|------|------|------|
| `1_初始化环境.bat` | `packaging/windows/scripts/` | Windows环境初始化 |
| `2_一键打包.bat` | `packaging/windows/scripts/` | Windows仅打包exe |
| `3_完整打包带安装程序.bat` | `packaging/windows/scripts/` | Windows打包+安装程序 |
| `build_macos_app.sh` | `packaging/macos/scripts/` | macOS应用打包 |
| `sign_macos_app.sh` | `packaging/macos/scripts/` | macOS代码签名 |
| `notarize_macos_app.sh` | `packaging/macos/scripts/` | macOS应用公证 |

### 开发脚本

| 脚本 | 路径 | 用途 |
|------|------|------|
| `start_app.sh` | 根目录 | 开发环境启动 |
| `check_progress.py` | `scripts/` | 项目进度检查 |

---

## 快速导航

### 我是用户

1. [README.md](README.md) - 项目介绍
2. [docs/guides/使用指南.md](docs/guides/) - 使用教程
3. [releases/](releases/) - 下载页面

### 我是开发者

1. [CLAUDE.md](CLAUDE.md) - 开发指南
2. [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) - 工作流程
3. [packaging/](packaging/) - 打包配置和指南
4. [docs/packaging/](docs/packaging/) - 详细打包文档

### 我是贡献者

1. [LICENSE](LICENSE) - 开源协议
2. [CHANGELOG.md](CHANGELOG.md) - 版本历史
3. [tests/](tests/) - 测试用例

---

## 版本信息

- **当前版本**: v36.4
- **最后更新**: 2026-02-17
- **维护者**: 汪立

---

## 统计信息

| 项目 | 数量 |
|------|------|
| 核心代码行数 | ~4,300 |
| 文档数量 | 50+ |
| 测试脚本 | 9 |
| 支持平台 | macOS, Windows |
| 版本历史 | 37+ |

---

*整理时间: 2026-02-17*
