# PrivacyGuard 当前状态（Single Source）

- **日期**: 2026-03-18
- **当前版本基线**: v37.7.4
- **版本标识**: `37.7.4 - Release Audit and Final Polish`
- **当前状态**: ✅ 发布准备完成（代码、文档、打包方案与版本资源已同步）
- **最后更新**: 2026-03-18
- **当前工作轨道**: 正式发布前的真机截图驱动抛光

---

## 2026-03-18 发布审查、版本升级与文档同步

### 已完成

- 已将当前版本从 `v37.7.3` 升级到 `v37.7.4`
- 当前版本标识已统一为：`37.7.4 - Release Audit and Final Polish`
- `version.txt`、`main.py` 版本回退、Windows 安装器默认回退版本已全部同步
- active 文档已统一切换到当前发布准备口径：
  - `README.md`
  - `AGENTS.md`
  - `CLAUDE.md`
  - `PROJECT_INDEX.md`
  - `CHANGELOG.md`
  - `docs/current/STATUS.md`
  - `docs/current/DEV_LOG.md`
  - `docs/current/PROJECT_SUMMARY.md`
  - `docs/current/PROJECT_STRUCTURE.md`
  - `docs/current/V38_UI_REFACTOR_PLAN.md`
  - `docs/current/RECOVERY_GUIDE.md`
  - `docs/packaging/*`
  - `packaging/README.md`
- Windows 版本资源已重新生成并同步到 `37.7.4.0`
- 当前主回归基线已更新为 `52/52`

### 本轮代码与体验收口

- 已修复首次从空首页点击“选择文件”前先清理资源引起的首页抖动问题
- 已修复带嵌入图片的 Word 文档在预览时可能空白或打开失败的问题
- 已将 Word 嵌入图片预览改为落地临时资源目录，减少超大 `base64 data URI` 对首开性能的影响
- 批量 Word 结果摘要已补充“每条替换规则在每个文档中的成功替换条数”

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests packaging` ✅
- 主回归：`52/52` ✅
- `python3 packaging/windows/scripts/generate_version_info.py` ✅

---

## 2026-03-17 Windows 打包 NumPy 2.x 热修

### 已完成

- `packaging/windows/config/PrivacyGuard_windows.spec` 已补充完整的 `numpy` 收集链
- 已显式加入 `numpy.core / numpy._core` 兼容目录与关键 hiddenimports
- 已确认 Windows 主打包入口仍然是：
  - `packaging\\windows\\scripts\\build_complete.bat`
  - `packaging\\windows\\scripts\\3_build_with_setup.bat`

### 当前结论

- `No module named 'numpy.core._exceptions'` 属于 Windows 打包收集不完整问题
- 代码层已修复 active spec
- 需要在 Windows 真机重新打包验证修复结果

---

## 2026-03-17 Logo 图标资源已完成 + 全新设计

### 已完成

- `assets/logo/windows/app_icon.ico` - 已修复为包含 4 个尺寸（16/32/48/256）的正确 ICO 文件
- `assets/logo/generate_icons.py` - 已修复 ICO 生成逻辑（手动构建多尺寸 ICO 格式）
- `packaging/windows/config/PrivacyGuard_windows.spec` - 已更新图标路径
- `packaging/macos/config/PrivacyGuard.spec` - 已更新图标路径
- `packaging/windows/config/PrivacyGuard_Setup.iss` - 已更新图标路径
- `packaging/windows/scripts/build_complete.bat` - 已更新图标检查路径
- `main.py` - 已添加应用启动时加载图标逻辑
- `assets/logo/README.md` - 已更新打包检查清单
- 回归测试：`50/50` 通过

### 技术细节

- 修复了 Pillow `save()` 方法无法正确生成多尺寸 ICO 的问题，改为手动写入 ICO 文件格式
- ICO 文件现在包含：16x16（任务栏）、32x32（桌面）、48x48（控制面板）、256x256（高 DPI）
- 所有打包脚本和配置文件现在引用正确的图标路径

---

## 2026-03-17 Logo 全新设计

### 设计变更

- **旧设计**: 盾牌 + 文档 + 马赛克，较为复杂
- **新设计**: 蓝色圆角方块 + 大号白色 "PG" 字母，简洁现代

### 已更新文件

- `assets/logo/source/logo_master.svg` - 新设计主源文件
- `assets/logo/source/logo_dark.svg` - 新设计深色版
- `assets/logo/export/*` - 全部重新生成
- `assets/logo/windows/app_icon.ico` - 重新生成
- `assets/logo/macos/AppIcon.icns` - 重新生成
- `assets/logo/linux/*` - 重新生成
- `assets/logo/marketing/*` - 重新生成
- `assets/logo/LOGO_DESIGN_GUIDE.md` - 更新设计规范
- `assets/logo/README.md` - 更新设计描述

### 设计特点

- 极简扁平化风格
- 蓝色渐变背景 (#3B82F6 → #1D4ED8)
- 大号白色 "PG" 字母，各尺寸清晰可辨
- 圆角矩形（类似 iOS/macOS 应用图标风格）

---

## 2026-03-16 主文档与当前文档已同步

### 已完成

- `README.md`、`AGENTS.md`、`CLAUDE.md`、`PROJECT_INDEX.md`
- `docs/current/PROJECT_SUMMARY.md`、`docs/current/PROJECT_STRUCTURE.md`
- `docs/current/V38_UI_REFACTOR_PLAN.md`
- 已统一到 `v37.7.3` 运行基线不变、`v38 UI 改造代码层已完成`、`50/50` 当前验证基线

### 当前验证

- 主文档同步以当前 `STATUS.md` / `DEV_LOG.md` / 主回归结果为准

---

## 2026-03-16 packaging 链路已同步并复核

### 已完成

- Windows 安装器默认回退版本已同步到 `37.7.3`
- Windows / macOS 打包脚本已统一切换到当前虚拟环境中的 `PyInstaller`
- Windows / macOS 打包脚本已统一使用项目内 PyInstaller 缓存目录：
  - Windows：`build\.pyinstaller-cache`
  - macOS：`build/.pyinstaller-cache`
- macOS `build_complete.sh` 已修正 `create-dmg` 缺失时的提示，并在 DMG 失败时保底复制 `.app` 到 `releases/macos/`
- packaging 相关说明文档、目录索引、脚本说明已统一同步到本轮真实状态

### 当前验证

- `python3 packaging/windows/scripts/generate_version_info.py` ✅
- `python3 -m compileall -q packaging` ✅
- `bash -n packaging/macos/scripts/build_complete.sh packaging/macos/scripts/build_macos_app.sh packaging/macos/scripts/sign_macos_app.sh packaging/macos/scripts/notarize_macos_app.sh` ✅
- `bash packaging/macos/scripts/build_complete.sh` ✅
  - 已完成 `.app` 构建
  - 当前环境缺少 `create-dmg`，脚本按回退逻辑尝试 `hdiutil`
  - `hdiutil` 当前环境下未成功创建 DMG，脚本已按预期复制 `releases/macos/PrivacyGuard.app`
- Windows 打包链当前结论：
  - 已完成脚本链、spec、版本资源、Inno Setup 配置与文档一致性复核
  - `packaging/windows/scripts/` 已清理历史兼容与解除阻止脚本，仅保留正式主链与必要诊断工具
  - 当前机器为 macOS，未实际执行 `.bat` 与 Inno Setup
  - 对外发布前仍需在 Windows 真机执行 `packaging\windows\scripts\build_complete.bat`
  - 如需安装包，再执行 `packaging\windows\scripts\3_build_with_setup.bat`

---

## 2026-03-16 Windows 专项收尾代码层已完成

### 已完成

- `PDF / Word / 批量 / 图片 / 首页 / 高级设置` 已全部补齐超宽窗口 / 全屏额外一档布局策略
- 主工作区左右留白、壳层最大宽度、中心内容 stretch 已继续放开，不再停留在普通宽屏档
- 批量工作台主辅区比例已完成最终收口，右侧结果主区已进一步强化
- 高级设置顶部概览、右侧内容与底部操作区已继续提高超宽窗口下的桌面利用率
- 主工作区壳层、批量 / 图片主卡、Word 预览内壳、设置页 section 卡已再完成一轮视觉语言统一
- 当前 v38 UI 改造的代码层大步骤已基本收完，后续默认进入真机截图驱动的细节微调阶段

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（48/48）

---

## 2026-03-16 启动回归已热修复

### 已完成

- `MainWindow._refresh_windows_density_metrics()` 的 `current_mode` 初始化顺序已修复
- 主窗口启动阶段不再因 `UnboundLocalError` 崩溃
- 宽窗口 / 全屏收口代码保持不变，仅修正初始化顺序问题
- 当前崩溃与 `Skia Graphite backend ... falling back to Ganesh` 日志无关

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（48/48）

---

## 2026-03-15 高级设置模块标题已收进卡片内部

### 已完成

- Windows 专项收尾已继续推进：主工作区与高级设置现在都会按 `宽度 + 高度 + DPI` 联动收口
- 主窗口工具栏密度判断已改成纯规则函数，Windows `125% / 150%` 缩放下会更早切换合适档位
- 高级设置已补上跨屏 / DPI 切换监听，窗口换屏或缩放变化后会自动重算密度
- 高级设置顶部概览、左侧导航、右侧内容、底部操作区的宽度与高度策略已接入同一套响应式档位
- 高级设置快捷入口按钮和底部保存按钮已按 DPI 统一高度与宽度下限
- 高级设置标题、说明、导航、摘要、字段标签与快捷入口按钮已接入同一套高 DPI 字级规则
- 主工具栏文字按钮宽度下限已按 DPI 再次收口，Windows 高缩放下命中区更稳
- 宽窗口 / 全屏下，`首页 / PDF / Word / 批量 / 图片` 五类工作区已进一步放开壳层宽度与中心 stretch
- 真实工作区左右留白与桌面级利用率已继续统一，主内容区不再保守悬在中间
- Word 对比、PDF 预览、批量结果主区、图片合并主卡都已接入同一套超宽窗口收口策略
- 超宽窗口 / 全屏下，主工作区与高级设置都已加入额外一档“桌面端放开策略”
- 预览壳层、批量主卡、图片合并主卡、首页主卡、设置右侧内容区会继续缩边并放宽，不再停留在普通宽屏档
- 当前 v38 UI 改造的代码级主线已完成，剩余工作以真机目测和细节微调为主
- `1. 通用规则`、`2. 自定义关键词`、`3. 精度与微调`、`4. OCR 检测框调节`
- 已从卡片外沿标题改为卡片内部标题行
- 四个设置模块卡片内部 padding 与 spacing 已统一
- 设置模块标题、说明、摘要已进一步合并为同一内部头部区
- `Word 替换规则` 子卡已与左侧字段卡统一为同类卡片容器
- 左侧导航已补充轻提示与底部信息卡容器
- 底部操作栏按钮高度、宽度与节奏已继续统一
- 设置子卡内部表单标签、分隔线与 padding 已继续统一
- 设置页左侧导航宽度、内边距与整体比例已继续收口
- 导航提示与状态摘要之间已加入轻分隔，底部保存栏比例已继续稳定
- 设置页已加入按窗口宽度响应的比例策略
- 顶部概览卡、左侧导航、右侧内容与底部操作区会按窗口宽度自动收比例
- 顶部概览指标卡、快捷入口按钮、自定义关键词区与扫描微调区已改成响应式重排布局
- 批量工作台已加入断点重排：阶段卡 / 指标卡 / 动作区 / 结果区会按宽度自动切换桌面布局
- 左侧导航高亮、滚动同步、跳转逻辑保持不变

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（48/48）

---

## 2026-03-16 图片合并工作台已升级为桌面工作区

### 已完成

- 图片合并模式已从简化中置小卡升级为桌面工作区壳层
- 已新增 `整理顺序 / 合并 PDF / 进入工作台` 三段阶段卡
- 已新增 `待合并图片 / 当前状态 / 后续动作` 三张指标卡
- 图片合并工作台已接入真正的断点重排：阶段卡支持 3 列 / 2 列 / 1 列，指标卡支持 3 列 / 2 列 / 1 列
- 图片合并工作台已接入主密度刷新链，与 PDF / Word / 批量工作台共享工作区宽度、spacing 和容器节奏
- 真实工作区统一性继续推进，四类工作台的桌面级容器语言进一步靠拢
- 真实工作区最后一轮统一收口已完成：`PDF / Word / 批量 / 图片` 四类工作区已统一到同一套桌面级壳层语言
- 批量 / 图片工作台宽度利用率、阶段卡、指标卡、section 节奏已完成最终收口
- 图片合并工作台已升级为与批量页同级的桌面工作区卡片壳层
- 当前剩余主线已切换到 Windows 专项收尾

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 PDF / 图片工作台工具位已按场景重排

### 已完成

- `使用/反馈` 已移动到 PDF / 图片工作台顶部右侧
- `适应页面` 已固定回到 PDF 工具栏实位
- `更多` 不再承担 `适应页面` 的主要入口
- PDF 旧左侧 `适应` 按钮已停用，避免重复入口

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 已加入按窗口高度响应的桌面工作区策略

### 已完成

- 真实工作区已不再只按宽度响应
- 大窗口 / 全屏下，PDF / Word / 批量工作区会继续压缩外围边距并放开壳层利用率
- PDF / Word 在高窗口下的纵向比例已继续收口
- 批量页在高窗口下已允许继续纵向扩展，结果主区更明确

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 真实工作区利用率与批量结果主区已继续强化

### 已完成

- PDF / Word / 批量 / 图片工作区左右舞台边距已进一步缩小
- PDF / Word 预览壳层最大宽度已继续放开
- Word 头部到内容区的过渡已继续统一
- 批量页左侧辅助轨宽度已继续收紧
- 右侧 `结果清单` 主区最小宽度已继续提高

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 Word 双栏头部与批量页 section 头已进一步统一

### 已完成

- Word 双栏头部高度、圆角、内边距与中缝留白已继续收口
- `原文预览 / 替换后预览` 头部更接近桌面工作台标签语言
- 批量页 `本轮摘要 / 结果清单 / 处理动态` 标题字级已进一步拉齐
- 批量页主辅区与 Word / PDF 工作区的层级语言已更统一

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 批量页主辅区比例已继续向结果主区倾斜

### 已完成

- 宽窗口下，批量页左侧辅助轨列宽已继续收紧
- `本轮摘要 / 处理动态` 已更明确退居辅助区
- 右侧 `结果清单` 主区比例已继续提高
- 结果区最小宽度已提升，更适合桌面端与全屏场景

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 大窗口下真实工作区空间利用率已继续增强

### 已完成

- PDF / Word / 批量 / 图片工作区横向 stretch 已继续放开
- 大窗口与全屏下中心工作区已更能吃满可用空间
- 批量页三块内容已形成更明确的主次关系
- `结果清单` 已继续保持主区并允许纵向扩展
- Word 单栏 / 双栏状态下的空间分配已更明确

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 真实工作区宽度与高度利用率已继续放开

### 已完成

- PDF / Word / 批量 / 图片工作区左右舞台边距已继续缩小
- PDF / Word 预览壳层最大宽度已继续放开
- 批量 / 图片工作区卡片最大宽度已继续放开
- Word 双栏内部留白已继续压缩
- 批量页结果区与日志区已允许继续纵向扩展

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 批量页下半区已改成桌面式双区布局

### 已完成

- 宽窗口下，批量页下半区已切成 `左侧摘要/动态 + 右侧结果主区`
- 窄窗口下会自动收回单列布局
- 结果表格主区高度已继续放开
- 顶部工作台 `标题 / 副标题` 行距已继续统一

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 批量结果区结果头已并成同一行

### 已完成

- `结果清单` 标题已与 `结果计数 + 筛选按钮` 合并成同一条结果头
- 批量结果区第一眼层级已更接近正式工作台
- 结果头内 `标题 / 计数 / 筛选按钮` 已接入同一高度基线
- 顶部工作台标题区行距已继续轻量收口

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 PDF 工具栏底边遮挡已继续收口

### 已完成

- PDF / 图片模式工具栏底部留白已增加
- 工具栏分组容器高度已统一抬高
- `缩放 / 页码 / 翻页` 中部控件已并入同一高度基线
- 右侧功能组继续按同一垂直节奏收口

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 批量页动作区已改成响应式网格

### 已完成

- 批量页动作区已支持宽窗口横排、窄窗口两列重排
- 四枚批量动作按钮已统一宽度下限
- 批量动作区已并入现有密度系统

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 Word 联动顺滑度与批量页 section 头已继续统一

### 已完成

- Word 双栏联动已继续微调顺滑度
- Python 轮询兜底频率已适度放缓，减少干扰
- 批量页 `本轮摘要 / 结果清单 / 处理动态` 已统一成 section 头
- 批量结果筛选按钮已继续保持统一高度与宽度下限

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 Word 双栏顺滑度与批量工作区宽度已继续收口

### 已完成

- Word 双栏联动已继续提升顺滑度
- 前端滚动同步已接入 `requestAnimationFrame`
- 程序化滚动锁定时长已缩短
- 批量 Word / 图片合并页已并入桌面工作区宽度体系
- 批量结果筛选按钮已继续统一高度与宽度基线

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 Word 双栏滚动联动已补齐稳定性保护

### 已完成

- Word 双栏滚动联动已改成 `滚动事件 + 前端定时上报 + Python 轮询兜底`
- 程序化滚动已继续补强防回环，减少左右互推
- Word 预览 WebView 有效性检查已升级到对象销毁级保护
- 关闭应用时不再允许已销毁的 `QWebEngineView` 继续进入同步链
- 相关测试与测试桩已同步修正

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（45/45）

---

## 2026-03-15 Word 双栏对比预览已支持同步滚动

### 已完成

- Word 双栏对比预览已支持左右联动滚动
- 同步滚动已加入防回环处理，避免互相触发抖动
- 同步逻辑已接入现有 WebChannel 预览桥
- 已补充 Python 侧轮询兜底，提升双栏滚动同步稳定性
- 已补充相关回归测试

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（44/44）

---

## 2026-03-15 PDF 顶部衔接与批量结果区已继续统一

### 已完成

- PDF 顶部信息区与预览区过渡已继续收紧
- 批量结果摘要条已统一垂直基线
- 批量结果表头与关键列宽已更稳定

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 PDF 工具栏缩放与翻页组对齐已继续收口

### 已完成

- 工具栏缩放组、翻页组已统一垂直基线
- `35%` 与 `1/1` 状态框已统一宽度策略
- PDF 工具栏中部控制区整体对齐感已继续提升

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 工作区顶部冗余已继续做减法

### 已完成

- PDF / Word 工作区已不再同时保留两层模式标识
- PDF / Word 副标题文案已进一步压缩
- 批量结果筛选按钮已继续补齐可用态交互反馈

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 Word 单栏状态与预览宽度已继续收口

### 已完成

- Word 单栏状态下，双栏头部已不再保留
- Word 单栏预览宽度已放开，不再沿用双栏宽度上限
- PDF / Word 工作区宽度策略已开始按场景区分

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 真实工作区可见节奏已继续收口

### 已完成

- PDF / Word 预览顶部衔接已继续压顺
- Word 双栏内部比例与壳层边界已进一步轻量化
- 批量结果筛选条、结果表、日志区之间的节奏已继续统一

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 预览过渡与批量结果筛选条已继续收口

### 已完成

- PDF / Word 预览顶部过渡已再收紧一档
- 预览外壳与内部内容 padding 已继续减薄
- 批量结果筛选按钮已接入统一高度、宽度下限和稳定胶囊样式
- 批量摘要框、结果表、日志区高度已继续跟随密度联动

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 真实工作区间距体系已继续统一

### 已完成

- PDF / Word 预览壳层已接入同一套内边距和头部间距规则
- 批量页头部、阶段卡、指标卡、动作区、结果区、日志区的间距已开始统一
- 批量摘要框、结果表、日志区的高度已开始跟随密度联动

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 真实工作区内部层级已继续统一

### 已完成

- Word 双栏头部已从硬竖线分隔改成留白分隔
- 批量页步骤卡、指标卡、结果表、日志区、摘要区的边界语言已继续统一
- 首页、预览区、批量页的视觉风格已进一步向同一套桌面工作台靠拢

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 真实工作区内部层级已开始统一

### 已完成

- Word 双栏头部的生硬中缝已改成留白分隔
- 批量页步骤卡、指标卡、结果表、日志区已开始统一边界语言
- 批量页与首页 / 预览区的视觉风格已进一步靠拢

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 工具栏横向节奏已继续统一

### 已完成

- 工具栏按钮组内间距已继续压紧
- 工具栏分组之间的呼吸感已进一步拉开
- 文字按钮已按角色接入更稳定的宽度下限

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 预览外壳边线与工具栏高度已继续收口

### 已完成

- 预览区外围多余边线已删除
- 工具栏整体高度与按钮高度已同步上调
- 按钮左右宽度可变，但上下高度继续保持统一

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 主工具栏已按新操作顺序重排

### 已完成

- “替换规则”已从主工具栏移除
- “设置”已改为“高级设置”，并前置到主操作区
- “使用/反馈”已直接常驻工具栏
- “更多”已收回为仅在必要时出现的溢出菜单
- 首页欢迎区按钮命名已同步统一

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 预览区左右留白已进一步收紧

### 已完成

- Word / PDF 工作区左右留白已继续缩小
- 预览壳层横向占比已提高，桌面端不再保留过多侧边空白
- 预览区与工具栏之间的顶部空隙已再压一档

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 预览区间距与边框距离已继续统一

### 已完成

- Word / PDF 工作区与工具栏之间的顶部空隙已进一步压缩
- Word / PDF 预览壳层与左右边框之间的留白已继续收窄
- 预览壳层最大宽度与内部 padding 已同步收口，整体更接近桌面工作台

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 Word 过窄预览与 PDF 三重边框已收口

### 已完成

- Word 单栏预览的桌面端宽度已继续放开
- PDF 中间那层多余边框已删除
- 真实工作区的居中宽度占比已继续统一

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 真实工作区已开始统一壳层

### 已完成

- PDF 预览区已收进统一桌面卡片壳
- Word 对比预览已收进统一桌面卡片壳
- 批量 Word / 图片合并页已切到居中宽卡结构
- 工作区宽度和边距已接入统一密度逻辑

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 首页全屏留白已继续收口

### 已完成

- `idle` 首页主卡已允许随高窗口自然长高
- 四张首页入口卡已允许吸收额外垂直空间
- 首页主动作区和入口网格的行列 stretch 已补齐

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 首页欢迎页已切到桌面网格布局

### 已完成

- 首页主卡已继续拓宽，减少桌面端左右留白
- `选择文件 / 批量 Word` 已改成统一网格动作区
- 四张首页入口卡已切到严格 `2 x 2` 网格并统一高度

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 首页欢迎页已按桌面端骨架重构一轮

### 已完成

- `idle` 首页头部已重排成桌面端欢迎区结构
- `选择文件 / 批量 Word` 已统一为同宽同高主动作
- 首页主卡最大宽度、区块宽度和入口卡高度已整体收口
- 首页宽度判定已改为 Qt 逻辑宽度，不再因 Retina / 高缩放被误判成窄布局

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 首页欢迎页三处明显问题已直接修掉

### 已完成

- `idle` 模式下顶部工作台条和空状态顶栏已隐藏
- `选择文件 / 批量 Word` 已统一为同高度基线
- `设置 / 更多` 已移入欢迎卡标题区
- 首页底部额外模块已删除

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-15 空状态壳层做了一轮整组减法

### 已完成

- `idle` 模式下顶部工作台条已隐藏
- 空状态工具栏左侧 `打开` 已移除，避免和欢迎页主动作重复
- `idle` 模式下底部 0% 进度区已隐藏
- 欢迎页整套空状态舞台继续统一

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 首页下方补上轻量工作区过渡壳

### 已完成

- 欢迎页主卡下方已加入轻量工作区过渡壳
- 首页与后续 PDF / Word / 批量工作区的衔接更自然
- 过渡提示保持为短文本和模式标签，没有重新堆砌说明

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页改成顶部锚定舞台

### 已完成

- 欢迎页已从上下居中感改成更偏顶部锚定的布局
- 欢迎区、流程带、入口区宽度继续统一收窄
- 首页第一屏更像正式桌面软件首页

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 常用入口区也收进统一视觉轴线

### 已完成

- 常用入口标题和入口卡已收进独立容器
- 欢迎区、流程带、入口区开始统一走同一条视觉轴线
- 首页第一屏完整度继续提升

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 流程带与欢迎区收进同一视觉轴线

### 已完成

- 欢迎页流程带已与上方欢迎区对齐
- 首页上半屏比例继续收口，整体更像一个完整入口区
- 启动首页的视觉重心进一步集中

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 首页上半区收成完整欢迎区

### 已完成

- 欢迎页标题、副标题和主动作已收进统一欢迎区
- 首页上半区最大宽度开始单独控制
- 启动第一屏更接近完整入口舞台

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页入口卡接入真正响应式排布

### 已完成

- 欢迎页入口卡在窄窗口下已自动改单列
- 首页在半屏、小窗口和高缩放下的阅读与点击节奏继续改善
- 欢迎页响应式表现更接近正式桌面软件首页

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 首页主按钮切到欢迎页专用样式

### 已完成

- 欢迎页 `选择文件 / 批量 Word` 已切到专用按钮样式
- 首页主按钮高度、宽度和命中区继续优化
- 欢迎页动作区与入口卡之间的视觉节奏更清楚

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 首页欢迎卡进入成品感分色阶段

### 已完成

- 欢迎卡舞台继续收窄，首页第一屏更聚焦
- 四类入口卡已加入轻量分色和更短说明文案
- 欢迎页整体进一步接近正式产品首页观感

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 首页入口卡继续拉稳

### 已完成

- 主动作区外壳继续减弱
- 入口卡高度和内部比例继续统一
- 欢迎页整体更接近成品页观感

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页流程带继续减重

### 已完成

- 欢迎页流程带已继续减重
- 小窗口下辅助文字和标识会自动收口
- 欢迎页上半区的盒子感继续下降

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 入口卡文案与对齐精修

### 已完成

- 四张入口卡说明继续压短
- 入口卡标签宽度已统一
- 入口卡标题、标签、说明的对齐继续优化

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页标题区继续减法

### 已完成

- `idle` 模式顶部副标题已隐藏
- 欢迎页主卡片副标题和拖拽提示继续压短
- 首页第一屏文字密度继续降低

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页标题区补充信任标识

### 已完成

- 欢迎页标题区已新增 `本地离线` 和 `自动分流` 标识
- 首页第一眼的产品感和信任感更强
- 标题区比例继续优化

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页顶部默认更干净

### 已完成

- 启动首页默认已隐藏顶部说明栏
- 顶部欢迎语和主卡片副标题继续压短
- 欢迎页第一屏文字密度继续下降

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 常用入口分区头收口

### 已完成

- 常用入口已改成真正的分区头
- 四张入口卡已收进统一网格容器
- 入口卡高度、内边距和行距继续统一

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页主动作条继续收口

### 已完成

- 欢迎页主动作条已改成“按钮行在上、拖拽提示在下”
- 首页主按钮补了更稳定的最小宽度
- 欢迎页第一屏视觉节奏继续变顺

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页流程带收口

### 已完成

- 欢迎页 `推荐流程` 已改成一条轻量流程带
- 首页从“主动作条 -> 流程带 -> 常用入口”衔接更顺
- 首页纵向层级继续压缩

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页顶部去重

### 已完成

- `idle` 模式顶部已改成欢迎语，不再像功能状态栏
- 启动首页已隐藏顶部 badge，减少无效装饰
- 首页主卡片标题已改为 `选择一种开始方式`

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页入口卡更易扫描

### 已完成

- 四种入口卡已增加类型标签
- 卡片头部改成“标题 + 类型标签”，首页入口更好扫一眼
- 首页入口层级继续向正式产品首页靠拢

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页居中限宽

### 已完成

- 欢迎页主卡片已改为居中、有限宽显示
- 大窗口下首页不再横向铺满，第一眼更聚焦
- 首页主卡片宽度、入口卡高度和动作条间距已接入响应式收口

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页主动作前置

### 已完成

- 欢迎页主动作已前置到卡片上半区
- 底部重复按钮已移除，首页层级更清楚
- 四种入口卡统一了高度和节奏，拖拽提示已并入主动作条

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页首页继续精简

### 已完成

- 首页默认操作指引已改成一句话说明，减少“说明书感”
- 欢迎卡片主文案、流程步骤和入口卡描述进一步压缩
- 首页动作按钮收短为 `选择文件` 和 `批量 Word`
- 新增独立的“常用入口”轻标签，首页层级更清楚

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-14 欢迎页样式回归热修

### 已完成

- 已修复软件启动欢迎页中普通文本被细边框包住的问题
- 根因是最近几轮 UI 样式收口后，欢迎卡片内部分标签没有显式清掉边框表现
- 当前已对首页欢迎卡片标题、说明、流程提示、路线卡标题和描述做定点去边框处理

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-13 启动回归热修

### 已完成

- 已修复主工作台引导升级引入的启动回归：
  - `NameError: name 'QGridLayout' is not defined`
- 原因是新增引导标签后使用了 `QGridLayout()`，但 `PyQt6.QtWidgets` 导入列表漏掉了该类
- 当前已补回导入，属于启动层热修，不涉及业务逻辑调整

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

---

## 2026-03-13 v38 UI 重构启动（cp31）

### 当前策略

- 继续以 `v37.7.3` 为运行基线
- 采用“检查点 + 分阶段重构”方式推进 UI 改造
- 不切换技术栈，不牺牲现有 PDF / Word / 批量 Word 主功能

### 已完成

- `cp31` 检查点已创建：`backups/v38_ui_refactor_cp31_20260313_140645/`
- 回滚日志已更新：`rollback_journal.md`
- 执行方案已落地：`docs/current/V38_UI_REFACTOR_PLAN.md`
- 第一批 UI 基础改造已开始：
  - Windows-first 主题基线
  - 主界面模式标识
  - Word 工具栏中的 `替换规则`
  - Word 工具栏中的 `对比预览` 显隐控制
  - PDF / Word / idle / batch 模式下的工具显隐重构
  - 设置中心左侧导航与顶部说明区
  - 主工具栏分段层级增强
  - 主工作台状态区与 5 步流程提示
  - 首屏空状态工作台
  - 批量 Word 的规则模式 / 执行模式 / 结果模式工作台
  - 图片合并模式状态卡
  - 首屏结构减法：顶部摘要条压缩，流程与空状态合并为单张主卡片
  - 单一上下文条：顶部提示条与工作台摘要已整合为一个区域
  - 工具栏减法：模式徽标移出工具栏，按钮按高频/低频分区重排
  - 工具栏控件质感收口：PDF 切换控件、页码、缩放、图标按钮已统一风格
  - 响应式工具栏：窗口缩放时可自动短文案、隐藏低频动作并收进更多菜单
  - 工具栏控件稳定性修复：PDF 切换按钮和 `更多` 菜单按钮已按 Qt sizeHint 重新收口，修复文字重叠、截断和箭头跑位
  - Windows DPI 收口：工具栏密度判断已按有效宽度适配缩放，按钮/图标/状态片高度与命中区会随 `100% / 125% / 150%+` 自动调整
  - 工具栏分组化：主操作、PDF、缩放、翻页、系统动作已分组显示，空组会随模式一起隐藏，主界面层次更清楚
  - 回归热修复：移除工具栏分组阶段遗留的悬空分隔条，解决屏幕中间竖线和主窗口关闭后进程未退出的问题
  - 回归热修复：工具栏分组显隐已改为基于 `isHidden()` 判断，解决整条工具栏空白的问题
  - 设置中心整理：左侧导航标题与区块编号已对齐，底部操作区改成说明 + 取消 + 保存，更接近正式桌面软件
  - 设置区块摘要：四个设置分区都已显示当前状态摘要，规则数、替换文本、扫描模式和 OCR 调节值会实时更新
  - 设置导航联动：左侧导航会随右侧滚动自动高亮，区块用途说明已补齐，设置页方向感更强
  - 设置中心强化：顶部概览卡已支持快捷跳转，通用规则改成双列排版，设置页更像完整控制中心
  - 设置字段卡片化：关键词、Word 规则、扫描模式、覆盖微调、OCR 调节都已拆成更明确的内嵌字段卡片
  - 设置中心就地操作化：四个核心区块都已提供快捷操作，支持恢复推荐勾选、清空关键词、恢复默认替换词、恢复推荐扫描值和恢复 OCR 0%
  - 批量 Word 工作台升级：已新增 `规则确认 / 执行替换 / 查看结果` 流程轨道，以及 `已选文档 / 启用规则 / 当前进度 / 执行结果` 指标卡和“本轮摘要”面板
  - 批量 Word 结果态动作：已补齐 `仅重试失败文档` 和 `打开输出位置`，结果页不再只能查看摘要
  - 主工具栏减噪：`反馈` 已统一收进 `更多`，`设置` 在窄窗口时也会自动收进 `更多`，同时已补上首次显示和跨屏切换时的工具栏密度刷新
  - Windows DPI 收口：工具栏、上下文条、流程步骤、Word 对比头、批量摘要区、底部进度条和取消按钮都已按显示缩放动态调整字号、高度和命中区
  - Windows-first 细化：主按钮字体、padding、图标按钮比例已随 DPI 动态调整，Word 预览 / HTML 包装 / 文件对话框字体栈也已切到 Windows-first
  - 原生导航图标：PDF 翻页按钮已切到 Qt 原生标准图标，缩放按钮也改成更稳定的 `- / +`，减少 Windows 字体差异带来的观感漂移
  - 窄窗口响应式减噪：Word 的 `对比预览`、PDF 的 `适应页面` 已可在窄窗口自动收进 `更多`，顶部主栏会更聚焦高频动作
  - Word 预览运行时热修：修复 `f-string + CSS` 花括号未转义导致的 `.docx` 打开报错 `NameError: name 'display' is not defined`
  - 新增回归测试：覆盖 Word 预览文档样式、替换后预览样式、文件对话框样式，防止同类运行时异常再次出现
  - 设置侧栏状态化：左侧导航已开始显示规则启用数、关键词条数、扫描是否微调、OCR 百分比，侧栏底部新增常用区 / 高级区状态摘要
  - 批量结果表格化：批量 Word 工作台新增结果清单表格，支持双击成功行打开输出、双击失败行定位原文件，并在未开始 / 执行中显示占位提示
  - 新增纯逻辑测试：覆盖设置导航标签构建、批量结果行构建，降低 UI 辅助逻辑回归风险
  - 批量结果筛选：结果表格已支持 `全部 / 仅成功 / 仅失败` 过滤，并显示总条数、成功数、失败数；当筛选为空时会显示明确占位提示
  - 设置分层强化：设置页头部已新增“常用设置 / 高级微调”标签，进一步降低首次进入时的理解成本
  - 新增辅助逻辑测试：覆盖批量结果筛选、结果计数和百分比格式化，继续降低 UI 迭代回归风险
  - 主工作台引导增强：统一上下文条已新增模式专属引导标签，PDF / Word / 批量 / 图片合并都会直接显示当前建议动作和下一步提示
  - 新增辅助逻辑测试：覆盖主工作台引导 helper，锁住 PDF / Word / 批量不同阶段的提示文案
  - 设置页顶部动态摘要：顶部标签已不再是静态说明，会实时显示规则数、关键词数、Word 规则数，以及扫描/OCR 当前状态
  - 批量结果状态强化：结果表格状态列已补充底色区分，成功 / 失败 / 占位提示更容易一眼识别
  - 新增辅助逻辑测试：覆盖设置页顶部动态摘要 helper，继续降低设置中心联动回归风险
  - 批量结果筛选计数化：`全部 / 成功 / 失败` 按钮已开始显示本轮计数，用户不用先读表格也能看到结果分布
  - 新增辅助逻辑测试：覆盖批量筛选按钮文案 helper，继续降低批量结果区联动回归风险
  - 主工具栏语义收口：PDF 模式按钮已切到 `智能涂抹 / 导出 PDF`，Word 模式按钮已切到 `智能替换 / 导出 Word`，更直接体现两套处理逻辑
  - 新增辅助逻辑测试：覆盖工具栏模式文案 helper，锁住 PDF / Word 下的扫描与导出文案
  - 主工具栏结果态细化：PDF / Word 主按钮已开始识别“首次处理 / 重新处理”，Word 的 `替换规则` 按钮也会直接显示当前启用数量
  - Word 对比提示细化：对比预览按钮 tooltip 已按“未打开文档 / 暂无结果 / 显示中 / 已隐藏”切换，更容易理解当前状态
  - 新增辅助逻辑测试：覆盖工具栏结果态文案，继续降低 PDF / Word 主工具栏联动回归风险
  - 主工作台简化回退：顶部多标签引导已全部收掉，恢复为更简洁的单状态栏结构，避免信息拥挤
  - PDF 文案收口：运行时主标题、模式标识、主按钮和图片合并后续流程提示已统一改成 `PDF 脱敏` 语义，不再以“涂抹”作为主表达
  - 顶部密度继续收口：主工作台条的内边距与间距已进一步压缩，Word 双栏头也改成更轻的标签式头部，减少页面顶部的大块堆叠感
  - 主工具栏去外壳感：分组容器已改为更轻的排版容器，背景和边框基本收掉，工具栏第一眼更像轻量工作条而不是多层胶囊
  - 工具栏间距继续收口：整体间距、组内边距和组内间距已继续压缩，减少顶部块状堆叠感
  - 预览舞台继续收口：PDF 画布已改为按内容优先的承载策略，预览区外边距、页间距和 Word 双栏内容间距也继续缩小，减少大面积空白感
  - 文档舞台感继续收口：主滚动区、PDF 页面和 Word 预览壳层已补上更轻的承载边界，同时预览底色继续提亮，整体更像正式文档工作区

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_word_replace_rules -v` ✅（23/23）
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（42/42）

### 下一阶段

1. 在 Windows 真机上继续做 DPI / 字体 / 命中区专项走查
2. 继续压缩主工具栏视觉噪音并统一层级
3. 视 Windows 真机效果决定是否再收口设置中心与批量页细节

---

## 2026-03-11 PyInstaller 打包模块导入失败修复（cp30）

### 问题现象
- Windows 打包完成后，打开应用出现弹窗错误：
  ```
  ModuleNotFoundError: No module named 'privacyguard.utils.security'
  ```
- 文件 `security.py` 实际存在于 dist 目录中，但无法被导入

### 根因
- `privacyguard/utils/security.py` 第 56 行存在语法错误：
  ```python
  return False, f"路径包含危险字符: {repr('\\')}"
  ```
- Python 3.11 不允许在 f-string 的 `{}` 表达式中直接使用反斜杠
- 语法错误导致模块无法被导入，进而导致 `collect_submodules('privacyguard')` 返回空列表
- PyInstaller 无法检测到该包的任何子模块

### 修复方式
1. 修复 `privacyguard/utils/security.py` 中的 f-string 语法错误
2. 将反斜杠先赋值给变量，再在 f-string 中使用：
   ```python
   backslash_char = '\\'
   backslash_repr = repr(backslash_char)
   return False, f"路径包含危险字符: {backslash_repr}"
   ```
3. 将 `privacyguard/__init__.py`、`privacyguard/utils/__init__.py`、`privacyguard/ocr/__init__.py` 中的相对导入改为绝对导入
4. 优化 spec 文件中的 hiddenimports 配置
5. 添加 PyInstaller hook 文件和 runtime hook

### 本轮验证
- ✅ 打包成功
- ✅ 应用正常启动
- ✅ 无模块导入错误

---

---

## 2026-03-10 版本/文档/打包方案再次同步（cp28 / cp29）

### 本轮目标
- 定义新的补丁版本号
- 把 active 文档、恢复入口、协作说明、打包方案再次统一到当前代码基线
- 更新 Windows 安装器默认版本和 EXE 版本资源

### 本轮结果
- 版本升级到 `v37.7.2`
- 当前版本标识更新为 `37.7.2 - Word Preview Refresh Fix`
- `README.md`、`PROJECT_INDEX.md`、`CLAUDE.md`、`docs/current/*`、`docs/guides/*` 当前入口文档已同步
- `docs/packaging/*` 与 `packaging/*` 当前打包方案说明已同步
- Windows 默认安装器版本与 EXE 版本资源已同步到 `37.7.2`

### 本轮验证
- `python3 packaging/windows/scripts/generate_version_info.py` ✅
- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（28/28）

---

## 2026-03-10 Word 原文预览红色高亮串位修复（cp26 / cp27）

### 问题现象
- 打开 Word 文档后，进入“高级设置”修改自定义关键词并保存。
- 左侧“原文预览”会出现异常红色高亮区域。
- 红色高亮原本只应该在手动右键脱敏时出现。
- 点击“智能脱敏”后预览又恢复正常。

### 根因
- Word 预览采用增量更新时，JavaScript 使用 `[data-key]` 选择器刷新节点。
- 但手动 / OCR 高亮 `<mark>` 本身也带有 `data-key`。
- 保存设置后的二次刷新会把整段正文 HTML 再次写进旧高亮节点内部，造成高亮嵌套和红色串位。

### 修复方式
- 预览增量更新改为只更新正文块容器，不再更新高亮 `<mark>` 节点。
- 正文块统一增加 `data-word-block="1"` 标记。
- `BeautifulSoup` 路径和 regex fallback 路径都补齐正文块标记，避免 fallback 时再次失效。
- 新增针对选择器和 fallback 标记的回归测试。

### 本轮验证
- `python3 -m compileall -q main.py tests/unit/test_word_replace_rules.py` ✅
- `python3 -m unittest tests.unit.test_word_replace_rules tests.unit.test_app_config tests.unit.test_pdf_text_hit_dedup tests.unit.test_package_imports tests.test_path_validation tests.unit.test_batch_word_replace tests.unit.test_mixed_pdf_ocr tests.unit.test_ocr_api -v` ✅（28/28）

## 2026-03-09 发布同步（cp24 / cp25）

### 本轮目标
- 定义新的补丁版本号
- 统一 active 文档、日志、打包方案与默认打包版本
- 补齐今日日记，确保下次接手有完整上下文

### 本轮结果
- 版本升级到 `v37.7.1`
- 当前版本标识升级到 `37.7.1 - Mixed PDF OCR Hotfix`
- `README.md`、`PROJECT_INDEX.md`、`CLAUDE.md`、`docs/current/*`、`docs/guides/*` 当前入口文档已同步
- `docs/packaging/*` 与 `packaging/*` 当前打包方案说明已同步
- Windows 默认安装器版本与 EXE 版本资源已同步到 `37.7.1`
- 新增今日日记：`docs/diary/20260309_2338_release_sync_diary.md`

### 本轮验证
- `python3 packaging/windows/scripts/generate_version_info.py` ✅
- `python3 -m compileall -q main.py privacyguard tests` ✅
- `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（28/28）

---

## 2026-03-09 混合型 PDF OCR 热修复（cp22 / cp23）

### 问题现象
- 混合型 PDF 页面中，可选中文本层可以正常脱敏。
- 同页嵌入图片 / 扫描区域中的同一关键词不会被脱敏。
- 典型场景：上半部分是文字层，下半部分是图片嵌入内容，只有上半部分被命中。

### 根因
- PDF 扫描逻辑将页面粗分为“文本页”或“扫描页”二选一。
- 一旦页面存在文本层，就只执行文本搜索，不再对图片块做 OCR。
- 导致混合页中的图片区域完全漏扫。

### 修复方式
- 新增共享模块：`privacyguard/ocr/mixed_pdf.py`
- 每页统一改为：
  - 先扫文本层命中
  - 再扫嵌入图片块 OCR 命中
  - 纯扫描页无图片块信息时回退到整页 OCR
- 图片块 OCR 命中后，将裁剪区域坐标偏移加回页面坐标，避免脱敏框跑到左上角。
- `main.py` 与 `privacyguard/workers/ocr_worker.py` 同步复用该逻辑，避免再次漂移。

---

## 当前验证状态

- 语法检查：
  - `python3 -m compileall -q main.py privacyguard tests` ✅
- 测试回归：
  - `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace -v` ✅（28/28）

---

## 当前关键检查点

- `20260309_runtime_remediation_cp18_verified`
- `20260309_word_compare_bugfix_cp20_verified`
- `20260309_mixed_pdf_ocr_cp23_verified`
- `20260310_word_preview_highlight_cp27_verified`
- `20260310_release_sync_cp29_verified`

回滚入口：

- `rollback_journal.md`
- `ROLLBACK_GUIDE.md`
- `restore_checkpoint.sh`

---

## 当前下一步建议

1. 每文件单独规则模式（文件-规则映射）
2. 批量规则集模板管理（多规则集快速切换）
3. 替换后预览增加“按来源筛选高亮”（规则/手动/OCR）
