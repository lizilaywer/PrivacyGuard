# GitHub 展示素材与可复制文案

本文件中的文案可直接复制。仓库首页完整内容是根目录 `README.md`，英文版是 `README_EN.md`。图片使用仓库相对路径，复制到其他仓库时请一起复制 `assets/showcase/`。

开发者账号：抖音、小红书、微信公众号统一名称为 **池州有个汪律师**。

## 仓库 About / Description

PrivacyGuard 脱敏卫士｜先脱敏，再上传。律师实务驱动的本地 PDF / Word 脱敏工具：离线 OCR、手动框选、双栏预览、批量替换与 PDF 加密导出。Local-first document redaction for Windows & macOS.

## Website

https://github.com/lizilaywer/PrivacyGuard#readme

## Topics

privacy, redaction, pdf, docx, ocr, offline, desktop, pyqt6, python, legaltech, document-processing, local-first

## 短介绍

先脱敏，再上传。PrivacyGuard 把 PDF / Word 智能扫描、手动补充、预览复核和导出放到自己的电脑上。它从一位基层律师的日常文书需求出发，借助 AI 持续开发，基于 GPL v3 开源。欢迎试用、反馈匿名样本，也欢迎用一个 Star 帮助更多人找到它。

## 本次源码更新说明

PrivacyGuard v40.2.5 源码同步与仓库展示更新：整理中英文首页，补充 Windows 实际运行截图、功能与已知边界说明、贡献入口和安全反馈指引；修复 Windows 中文环境下一项审计测试的 UTF-8 读取问题，并加强本地配置、草稿、环境和代理状态的上传排除。

本轮 Windows 回归：741 项发现，738 通过，3 跳过；规范、依赖一致性及原生离线 OCR / Word / PDF 自检通过。此次不新增二进制发行包，下载资产以各 Releases 的说明为准。

## 素材清单

| 文件 | 用途 |
| --- | --- |
| `assets/showcase/banner.svg` | 1280×640 仓库首页横幅，可编辑矢量源 |
| `assets/showcase/social-preview.png` | 1280×640 社交分享封面，适合 GitHub Social preview 上传 |
| `assets/showcase/home.png` | Windows 源码首页实拍 |
| `assets/showcase/pdf.png` | 虚构 PDF 智能扫描后遮罩预览 |
| `assets/showcase/bookmarks.png` | PDF 书签与页面导航 |
| `assets/showcase/word.png` | 虚构 Word 替换后双栏预览 |

截图：v40.2.5 / Windows / 2026-11-02。原始截屏未合成伪造功能。演示文档由 `scripts/create_showcase_samples.py` 创建，输出位于忽略的 `tests/output/showcase/`；使用独立演示配置，不含真实卷宗或私人规则。首页自带的开发者公开介绍与公众号属于已有品牌素材。

## 手动入口

- 仓库首页右侧齿轮：编辑 Description、Website、Topics。
- Settings → General → Social preview：可上传上述 PNG。若访问权限或 API 不支持自动设置，使用此入口。
- README 已包含 Star、反馈、下载、演示视频和贡献入口；没有虚构下载量或准确率。
