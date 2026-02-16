# PrivacyApp 项目文档索引

**版本**: v23.3  
**更新**: 2026-02-11  
**状态**: ✅ 生产就绪

---

## 📚 文档导航

### 快速开始
- **[README.md](./README.md)** - 项目介绍和快速开始指南

### 开发文档
- **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - 快速参考，重要代码位置和常量
- **[PROJECT_STATUS.md](./PROJECT_STATUS.md)** - 项目进度、功能状态、待办事项
- **[CHANGELOG.md](./CHANGELOG.md)** - 详细版本更新日志

### 测试文档
- **[TEST_LOG.md](./TEST_LOG.md)** - 测试记录和测试清单
- **[TESTING_REPORT.md](./TESTING_REPORT.md)** - UI 测试报告

### 本文件
- **[INDEX.md](./INDEX.md)** - 文档索引（本文件）

---

## 📁 项目结构

```
PrivacyApp/
│
├── 📄 main.py                          # 主程序 (40KB)
│   ├── SettingsDialog                  # 设置对话框
│   ├── SinglePageCanvas                # 单页画布
│   ├── OCRWorker                       # OCR 线程
│   └── MainWindow                      # 主窗口
│
├── 📄 theme.py                         # 主题系统 (2.4KB)
│
├── 📝 文档/
│   ├── README.md                       # 项目介绍
│   ├── QUICK_REFERENCE.md              # 快速参考
│   ├── PROJECT_STATUS.md               # 项目进度
│   ├── CHANGELOG.md                    # 更新日志
│   ├── TEST_LOG.md                     # 测试记录
│   ├── TESTING_REPORT.md               # 测试报告
│   └── INDEX.md                        # 本文件
│
└── 💾 备份/
    ├── main.py.backup_v19.3_20260209_131607
    ├── main.py.backup_v19.4_20260209_215114
    ├── main.py.backup_v19.5_20260209_215756
    ├── main.py.backup_v23.2_ui_20260211_075010
    └── main.py.backup_v23.3_ui_20260211_081152  ← 最新
```

---

## 🚀 快速命令

```bash
# 进入项目目录
cd /Users/a49144/Desktop/临时coding/PrivacyApp

# 运行程序
python3 main.py

# 语法检查
python3 -m py_compile main.py

# 查看备份
ls -la main.py.backup_*

# 创建新备份
cp main.py main.py.backup_$(date +%Y%m%d_%H%M%S)
```

---

## 📊 项目状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 基础功能 | ✅ 完成 | PDF 脱敏核心功能 |
| UI 现代化 | ✅ 完成 | macOS BigSur 风格 |
| 主题系统 | ⚠️ 简化 | 仅保留浅色主题 |
| 性能优化 | 🔄 待办 | 大型文件处理 |
| 文档 | ✅ 完成 | 完整文档体系 |

---

## 🎯 当前版本亮点

### v23.3 (2026-02-11)
- ✨ 自适应视图默认改为 100%
- ✨ 进度条显示百分比，更醒目
- 🗑️ 移除深色主题，简化界面
- 📝 完善文档体系

---

## 📋 版本历史

| 版本 | 日期 | 主要改进 |
|------|------|----------|
| v23.3 | 2026-02-11 | UI 优化，移除深色主题 |
| v23.2 | 2026-02-11 | UI 现代化，主题系统 |
| v23.1 | 2026-02-08 | 矩形去重 |
| v19.x | 2026-02-09 | 基础功能 |

---

## 🔧 开发工具链

- **语言**: Python 3
- **GUI**: PyQt6
- **PDF**: PyMuPDF
- **OCR**: RapidOCR
- **图像**: OpenCV + NumPy

---

## 📞 项目信息

- **路径**: `/Users/a49144/Desktop/临时coding/PrivacyApp`
- **类型**: PDF 隐私信息脱敏工具
- **许可**: 私有项目
- **状态**: 活跃开发中

---

## 📖 阅读建议

### 新手入门
1. 先阅读 [README.md](./README.md) 了解项目
2. 运行程序体验功能
3. 查看 [TEST_LOG.md](./TEST_LOG.md) 了解测试情况

### 开发者
1. 阅读 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) 了解代码结构
2. 查看 [PROJECT_STATUS.md](./PROJECT_STATUS.md) 了解待办事项
3. 参考 [CHANGELOG.md](./CHANGELOG.md) 了解版本历史

### 下次继续开发
1. 查看 [INDEX.md](./INDEX.md) (本文件)
2. 阅读 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) 快速回忆
3. 查看 [TEST_LOG.md](./TEST_LOG.md) 了解上次测试情况
4. 开始编码！

---

## ✅ 检查清单

### 开发前
- [ ] 阅读本文档
- [ ] 查看最新备份
- [ ] 了解待办事项
- [ ] 创建新备份

### 开发后
- [ ] 语法检查
- [ ] 功能测试
- [ ] 创建备份
- [ ] 更新文档

---

**祝你开发顺利！** 🎉

---

**最后更新**: 2026-02-11 08:20
