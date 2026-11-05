# PrivacyGuard 当前状态（Single Source）

## v40.2.7 仅书签脱敏导出状态补齐（2026-11-05）

- 保留 v40.2.6 正文命中恢复导出的修复；扫描成功后以实际导出 TOC / 规则源检查书签是否发生替换，面板未打开也适用。
- 空结果、无变化、禁用规则、取消及错误路径不误启用；原 PDF 不被修改，既有导出权限/失败保护保持有效。
- 新增 15 项专项回归；完整回归 756 项，753 passed / 3 skipped（私人样本缺失 2 项、平台符号链接 1 项）；Ruff、编译、依赖和版本一致性检查通过。Windows 原生 Qt 真实后台扫描、导出 PDF 并重新打开核对通过，原文件书签不变，再次重置恢复禁用。
- 当前更新源码和版本资源，无新二进制发行包。GitHub 沿用公开分支为父提交发布，排除本地历史中的私人配置和临时文件。

## v40.2.6 重置→脱敏导出灰死修复（2026-11-03）

- 修复用户反馈 Bug：重置文档后执行智能脱敏/全文遮罩，导出按钮保持禁用（扫描结果路径
  从不启用导出；缺口仅在"重置禁用导出"后暴露）。扫描产生命中即启用导出，与手动框选
  行为对齐；零命中维持禁用。main.py 两处（_on_ocr_page_result / _on_targeted_page_result）

## 仓库审查与展示更新（2026-11-02）

- 版本保持 40.2.5；本轮以源码审查、隐私排除和 GitHub 展示更新为主，没有新增二进制发行包。
- Windows 本机全量回归：741 discovered / 738 passed / 3 skipped；Ruff、pip check、编译与原生离线自检通过。
- 修正一项审计测试的 UTF-8 读取；排除本地代理状态、发布环境和快照，公开源码快照不携带未推送开发历史中的私人配置/临时索引。
- 新版中英文 README、4 张实际界面截图、SVG 横幅/PNG 分享封面、安全反馈及 Issue/PR 模板已准备。
- 范围、证据与未解决项见 [REPOSITORY_AUDIT_20261102.md](REPOSITORY_AUDIT_20261102.md)。已知 Word XML/PDF 净化边界仍保留；未宣称每个功能逐一实机验收。
- GitHub 最终提交与仓库设置状态以本轮交付回复为准；About/Topics/分享封面文案与素材见 `docs/marketing/GITHUB_SHOWCASE.md`。

- **日期**: 2026-10-25
- **当前版本基线**: v40.2.5
- **版本标识**: `40.2.5`
- **当前状态**: macOS 便携包已交付；Windows 便携构建资料包准备与脚本校验完成，待用户在 Windows 执行原生构建；741 discovered / 739 passed / 2 skipped（macOS）；安全边界仍见审计报告
- **最后更新**: 2026-10-25
- **当前工作轨道**: `RELEASE_AUDIT_20261024.md` 为本轮接续入口；未提交或推送用户既有改动

## Windows 便携构建资料包（2026-10-25）

- 用户选择在自己的 Windows 电脑运行，不上传源码云端。Mac 无 Windows 运行环境，未生成/验证 Windows 可运行成品。
- 资料包入口：根目录 `BUILD_WINDOWS_PORTABLE.bat`；简明说明 `WINDOWS_BUILD_README.md`。
- `build_complete.bat` 改为 `build_portable.py` 编排，增加全量回归、x64 PE/版本/模型/VC++/隐私校验、冻结自检和 ZIP CRC；只清理 Windows 便携专用目标。
- 干净解压测试不依赖私人 config.json，配置测试回退出厂模板；路径断言适配 Windows 分隔符。
- `scripts/create_windows_buildkit.py` 显式清单打包，保留当前未提交修复，不含虚拟环境、配置、日志、用户文档和历史产物；每个输入记录 SHA256。
- 最终 `releases/windows/PrivacyGuard-40.2.5-Windows-BuildKit.zip`（1,293,013 字节）已独立解压复验，227 个输入哈希通过，完整回归 739 passed / 2 skipped；这是源码构建资料包，不是可运行便携成品。
- 版本保持 40.2.5（本轮无应用运行时代码变更）；旧安装器流程未实机验证，不与便携输出混用。
- 修改前备份：`backups/pre_windows_portable_20261025.tar.gz`。

## v40.2.5 发布前审查与 macOS 便携包（2026-10-24）

- 新增 `RELEASE_AUDIT_20261024.md`：现有架构/新增能力/确认问题/修复/剩余边界与验证证据。
- OCR 编辑后快照扫描、提取区域外内容物理移除、截去保留遮罩、扫描失败诚实状态、批量错误决策、书签规则、Word 页眉页脚变体与线程退出加固。
- 冻结应用配置/日志写用户目录，spec 不再带本地 config.json；离线模型显式本地路径。
- macOS 新入口 `packaging/macos/scripts/build_portable.sh`，独立发布环境 `venv_macos_release`；目标 macOS 14+ / Apple Silicon，395 Mach-O 校验通过，ad-hoc 签名，未公证。
- ZIP：`releases/macos/PrivacyGuard-40.2.5-macOS-arm64-portable.zip`。解压冻结应用原生自检（含图片 Word/真实 OCR/关闭）通过，正常启动后签名保持有效。
- 后续优先：Word 统一 XML 遍历（超链接/嵌套表格/隐藏部件）及 PDF 可配置净化；不是继续无边界扩充 UI。

## v40.2.4 打包致命修复 + v40.2.1-40.2.3 补记（2026-10-22）

- **pathex 同名劫持（致命）**：Windows spec pathex 违规含 privacyguard 子目录，
  `privacyguard/ocr/rapidocr.py` 被 ModuleGraph 注册为顶层模块 `rapidocr`，
  顶掉 pip 第三方 OCR 引擎包（第三方包+模型整个未进构建）；运行时
  `from rapidocr import RapidOCR` 以无父包身份二次执行自身 →
  ImportError: attempted relative import with no known parent package →
  打包版点"开始脱敏"即弹 OCREngineUnavailableError。修复：pathex 收敛为
  [project_root, current_dir]（对齐 mac spec 与 cp119 约定）
- **venv_win 复活**：基准解释器 49144 路径已不存在，pyvenv.cfg 重绑定 hal
  Python311（同 3.11.9，site-packages 零重装）
- **v40.2.3 补记**：称谓人名文档级传播（_pn_shared 跨页共享集）+ 收尾回填
  （_pn_backfill 文字层 search_for + OCR 行缓存子矩形）；_on_worker_finished
  worker 生命周期加固
- **v40.2.1**：混合 PDF OCR 空白渲染检测（max-min<8.0 保守整块覆盖）
- **v40.2.2**：spec _config_datas 守卫移至 Analysis() 之前

## v40.2.0 称谓人名识别（2026-09-06，cp_person_name）

智能扫描新增"称谓人名"规则（默认关闭）：识别称谓词后的诉讼人名并自动遮罩。

- 引擎 privacyguard/ocr/person_name.py（纯函数零依赖）：正向锚点（lookahead 不
  消费）+ 反向结构（姓名+作为/担任/系+称谓）+ 连接词截断/尾词裁剪/非人名否决
- 三管线接入：文字层 search_for 全页遮 / OCR 块内两遍法 / Word 收集 pass
- 命中携带规则名 override，脱敏报告归类"称谓人名"
- config redaction.person_name_titles 称谓词可扩展
- 渐进路线：阶段1 词表版实测 100% 准确 → 不引入 jieba/NER 模型
- 52 项新单测；scripts/eval_person_name_real.py 实测脚本

## v40.1.5 操作台视觉与交互大修（2026-08-18）

四维并行深度审计（安全/稳定性/性能/可维护性）后按四批修复：A1 外链三件套（离线策略 sanitize + CSP + 导航白名单页）、0600/0700 权限收紧；S1 撤销栈混合态（mask 快照继承结构字节）、S2 提取越界守卫、S3 扫描中结构守卫、派生状态刷新；F1 Word 标注 82 倍提速、F2 快照 192MB 限量落盘、F3 框选 OCR 后台化、PNG 往返改 samples、OCR 引擎单例、双份 tobytes 复用、导出 garbage=2；水印/几何/摘要 413 行迁 utils + 40 项新测试（567 全绿）。

---

## v40.1.3 主页 idle workspace 视觉重设计（2026-08-14）

参照 `HOME_REDESIGN_PREVIEW.html` 原型对默认主页做整体视觉重设计（仅改 idle 主页，未触碰操作台/工具栏/按钮）：
- Hero 区精简（移除右上角盾牌圈，徽章移至标题下）
- 开始卡横向化（图标圈 + 标题/描述 + 放大主按钮，蓝色强调边框）
- 四大功能路由卡彩色图标容器（PDF/Word/批量/图片 四色，字母标识跨平台稳定）
- 推荐流程改 3 圆圈节点（导入→脱敏→导出）+ 箭头
- 推荐流程与四大功能位置调换（四大功能下移至最下方功能区）
- 卡片宽度自适应填满窗口（解除三层 maxWidth 锁 + 移除居中 stretch）
- 回归基线提升至 527 全绿（修复 2 项历史遗留失败）

---

## v40.1.2 全面安全审计加固（2026-08-11）

### 全面安全审计修复（commit 4cd32fd，4 P0 + 5 P1）
**P0**：日志写脱敏原文改掩码（text_pdf/mixed_pdf/word_worker/main.py）；pdfsnap 导出后删除草稿；10 处残留 print 改 logger；草稿指纹去绝对路径。
**P1**：clean_paths symlink 逃逸防护；build_targeted_keyword_rules 过滤 None；refresh_bookmark_preview 保留 targeted 规则（防导出泄漏）；提取截去 cp131/cp132/cp133/cp128 接线补回；helpers_pdf/widgets/mixins __init__ 误丢恢复。

### P2 加固（commit 73262fa，2 P2）
_ensure_edit_permission 异常保守失败（perms=0 走弹窗）；全局异常钩子 traceback 降 DEBUG。跳过 validate_safe_path 覆盖（ROI 低）+ Windows junction（威胁模型不成立）。

## cp134 前端-后端接线全面审计修复 + Worker parent 一致性（2026-08-11，v40.1.1）

对其他 AI 完成的提取/截去功能接线恢复与本次新发现的问题做统一修复。修复 ExtractSidePanel
未实例化（P0 不可用）、canvas.page_index 跨页错误（P0 作用错误页）、TraceCleanDialog 回调链
断裂、DocSearchWorker 无 parent 闪退风险、crop 双重快照、test_undo_redo import 错误；并把 cp132
的 parent 修复推广到 4 个兄弟 Worker（OCRWorker/WordWorker/ImageMergeWorker/WordBatchReplaceWorker）。
前端-后端匹配性深度审计（5 项检查）通过：ExtractSidePanel/CropMixin/TraceCleanDialog/
BookmarkSidePanel 等控件信号槽全部正确，main.py 66 处 `.connect` 无悬空。

---

## cp_bookmark PDF 书签（TOC）功能 + 安全审计（2026-08-08，v40.1.0）

新增 PDF 书签栏（左侧可展开/收缩面板），支持读取/编辑 PDF 目录、搜索跳转、
书签脱敏（复用关键词规则）。同时修复手动框选弹窗同步、替换文字字号偏小等问题，
并经全面安全审计修复 2 个 P0 + 4 个 P1。

### 新功能
- 工具栏书签图标（PDF 模式可见）切换左侧 280px 面板
- QTreeWidget 多层级树：单击跳转、搜索过滤（保留祖先链）、增删改、右键菜单
- 读取 fitz TOC，导出时回写用户编辑
- 书签脱敏：高级设置勾选"支持搜索识别书签栏"后，关键词规则应用到书签标题
- 软件内实时预览脱敏效果；全文遮罩的识别词也同步应用到书签
- 新文件：helpers_bookmark.py / bookmark_side_panel.py / bookmark_mixin.py / bookmark.svg / test_bookmark.py

### 安全审计修复（2 P0 + 4 P1）
- P0 导出漏脱敏（A1）：统一规则源 `_collect_active_toc_rules`，预览=导出
- P0 异常信息泄漏（B1）：print 改 logger，不记敏感 message
- P0 脱敏失败静默继续（A2）：改为中止导出 + 用户告警
- P0 崩溃（current_page None）：`_safe_current_page_0based` 防御
- P1 删除全部书签不生效（E1）：显式 `set_toc([])`
- P1 大小写不一致漏脱（A3）：改 `re.sub(escape, IGNORECASE)`
- P1 doc.is_closed 崩溃 + 标题字符注入校验（C1）

### 验证
- 回归 490 项（书签新增 23 项全绿）
- 端到端：248 条书签 PDF 读取/编辑/脱敏/回写全链路验证

---

## cp117 RapidOCR 打包依赖终结修复（2026-08-03）

cp116 修复 antlr4 后，诊断脚本发现 dist 中还缺 `tqdm` 和 `cobble`，导致打包后
RapidOCR 仍不可用。经源码与 metadata 双重验证后补全。

- **tqdm**：rapidocr 声明依赖，`download_file.py:11` `from tqdm import tqdm`，
  `RapidOCR()` 初始化时加载（校验/下载模型）→ 缺失则整条导入链失败。
  两平台 spec 新增 `collect_all('tqdm')`（34 datas + 31 hiddenimports）
- **cobble**：mammoth 声明依赖（`mammoth -> cobble<0.2,>=0.1.3`），Word→HTML 预览需要。
  两平台 spec 新增 `collect_all('cobble')`（3 datas + 2 hiddenimports）
- `requirements.txt` 新增 `tqdm==4.69.0`（此前作为传递依赖未显式 pin）
- `verify_dependencies.py` 新增 tqdm/cobble 检查（23 REQUIRED + 16 COLLECT_ALL 全通过）
- 新增 `_ocr_diagnostic.py` 诊断脚本（rapidocr 完整导入链验证 + dist 产物实地检查）

## cp116 RapidOCR 打包根因修复（2026-08-03）

cp115 重新打包后版本号已正确，但智能脱敏仍报 `OCREngineUnavailableError`。逐层剖析
RapidOCR v3.9.2 导入链，定位到两个互锁问题：

- **antlr4-python3-runtime 未收集**：`from rapidocr import RapidOCR` → omegaconf →
  `omegaconf.grammar.gen` 顶部 `from antlr4 import *`，但 `collect_all('omegaconf')`
  不含 antlr4 → `ModuleNotFoundError` → 整条导入链失败。两平台 spec 新增
  `collect_all('antlr4')`（57 datas + 56 hiddenimports）
- **OCR 错误透传**：`is_available()` 原 `except ImportError` 吞掉真实异常，改为
  `except Exception` 捕获所有异常并存入 `_last_error`（含 traceback），弹窗直接显示根因
- `requirements.txt` 新增 antlr4-python3-runtime/omegaconf/colorlog 显式 pin

## cp115 打包依赖收集补全（2026-08-03）

对照 `requirements.txt` 全量复核 Windows/macOS spec 文件，补全 3 项 collect_all 缺失 +
7 项传递依赖 hiddenimports 缺失，确保打包产物用户无需自行安装依赖。

- **PyYAML**：omegaconf（RapidOCR 依赖）运行时 `import yaml`，但 `collect_all('omegaconf')`
  返回的 22 个 hiddenimports 不含 yaml → 打包后 omegaconf 加载失败。显式 `collect_all('yaml')`
- **mammoth**：`main.py:904` 直接 import 用于 Word→HTML 预览；Windows spec hiddenimports 遗漏
  （macOS 已有），补全并两平台 `collect_all('mammoth')`
- **psutil**：`requirements.txt` 声明，含平台二进制扩展，`collect_all('psutil')`
- **传递依赖防御**：flatbuffers/sympy/mpmath/cobble/packaging/typing_extensions 均无
  PyInstaller 内置 hook，加入 hiddenimports（protobuf 未安装不需声明）
- `verify_dependencies.py` 同步新增 yaml/psutil/mammoth 检查项
- 验证：compileall 零错误 + verify_dependencies.py 全量通过（20 REQUIRED + 12 COLLECT_ALL）

## cp114 加密 PDF 脱敏修复（2026-08-02）

修复加密 PDF 在智能脱敏、全文遮罩、导出时因 OCRWorker 与 save_pdf 从磁盘重开未认证导致的
"document closed or encrypted" 错误，以及编辑权限检测弹窗。

- **根因**：cp113 实现加密文档打开时，`pdf_open_password` 同时承担"导出加密"和"磁盘重读认证"
  两个职责。用户选「解除密码」后 `pdf_open_password` 清空，但原文件仍加密，OCRWorker/save_pdf
  从磁盘 `fitz.open` 后未 `authenticate` → 无法读取页面内容 → 报错
- **修复**：新增 `_pdf_auth_password` 字段（专用于磁盘重读认证，与导出加密设置解耦），
  在 `_authenticate_pdf_on_open` 中无论何种动作均设置此字段
- OCRWorker 新增 `pdf_open_password` 参数，`run()` 中 `fitz.open` 后检测 `doc.needs_pass` 并
  `authenticate`，失败抛 `OCREngineUnavailableError` 走 error_signal 路径
- save_pdf 两个分支（`tobytes` 流 / 磁盘重开）均补 `doc.needs_pass` 守卫与认证
- `_insert_pdf_pages_at` 对加密外部 PDF 弹 `QInputDialog` 密码框，认证后插入；用户取消返回 0
- **包装层修复**：main.py `OCRWorker(_ModularOCRWorker)` 兼容包装层 `__init__` 漏声明/漏转发
  `pdf_open_password` 参数，导致 `_start_targeted_mask_scan` 传参时 `TypeError`——已补全声明
  与 `super().__init__` 转发
- **编辑权限弹窗**：新增 `_ensure_edit_permission()` 方法——脱敏/保存前检测 `permissions` 缺
  `PDF_PERM_MODIFY` 位时弹 `QInputDialog` 输入 owner 密码，认证成功且获编辑权限则更新
  `_pdf_auth_password`；接入 `start_ocr` / `_start_targeted_mask_scan` / `save_pdf` 三处入口，
  用户取消则中止操作
- 验证：compileall 零错误 + ruff 全绿 + 回归 431（429 passed + 2 skipped）

## cp113 加密文档打开与密码管理（2026-08-02）

支持打开受密码保护的 PDF 与 Word 文档，密码状态与 cp72 锁按钮共享，导出时统一写入。

- `privacyguard/utils/word_crypto.py`（新）：`is_encrypted_docx`（OLE2 魔数检测）+
  `decrypt_docx_to_temp`（msoffcrypto 懒导入解密，密码错误抛 ValueError）
- `privacyguard/utils/helpers_pdf.py` 新增 `detect_pdf_password_state(doc)`：
  返回 needs_user_pw / has_owner_restriction / permissions
- `privacyguard/ui/dialogs/password_open_dialog.py`（新）`PasswordOpenDialog`：密码框 +
  显示密码 + 三动作（打开 / 打开并解除密码 / 打开并修改密码）；Word"修改密码"禁用
- main.py：`_open_pdf_file` 替换拒绝为弹框验证 + 三动作设密码状态 + 同步锁按钮；
  `_open_word_docx` 前置加密检测 + 解密到 temp_manager 临时文件（保留原 basename）；
  新增 `word_open_password` 字段；except 扩充 `BadZipFile`
- 密码状态机：PDF「打开」保留原密码 /「解除」清空 /「修改」弹新密码框；Word 仅打开+解除
  （python-docx 不支持加密保存）；导出统一走 `build_encrypt_save_kwargs`
- 依赖新增 `msoffcrypto-tool==5.4.2`
- 验证：compileall 零错误 + ruff 全绿 + 回归 431（429 passed + 2 skipped，含 13 项新测试）

详见 `docs/current/DEV_LOG.md` cp113 段。

## cp112 导出弹窗新增"打开文档"按钮（2026-08-02）

PDF/Word 导出成功弹窗新增"打开文档"按钮，一键用系统默认程序打开导出的文件。

- `privacyguard/utils/helpers_ui.py` 新增 `open_path_in_system(path) -> (ok, error_msg)`：
  Windows `os.startfile` / macOS `open` / Linux `xdg-open`
- PDF 弹窗（main.py:9036）：在"导出报告"与"OK"之间加"打开文档"按钮；失败弹 warning
- Word 弹窗（main.py:9167）：原 `QMessageBox.information` 改为自定义 QMessageBox + "打开文档"按钮
- 按钮顺序：导出报告 | 打开文档 | OK（Show Details 在底部）
- 验证：compileall 零错误 + ruff 全绿 + 回归 418（416 passed + 2 skipped）

详见 `docs/current/DEV_LOG.md` cp112 段。

## cp111 页面视图插入文件（2026-08-02）

页面视图左侧工具栏"插入空白页"之后新增"插入文件"按钮（`btn_page_insert_file`），
在选中页之后插入 PDF（`doc.insert_pdf` 全部页）或图片（Pillow + `new_page` +
`insert_image`，页尺寸=图片像素）作为新页面。

- 复用 `_insert_blank_page_after_selected` 全链路：`shift_page_data_for_insert` /
  `shift_page_set_for_insert`（page_data / `_ocr_processed_pages` / `grid_selected_pages`）/
  `_search_ocr_cache.clear()` / `_rebuild_page_grid()` / `_capture_undo_state(structural=True)`
- 多文件按对话框顺序依次插入；单文件失败跳过继续，结束汇总提示成功 N 页 + 失败 M 个
- 支持 Ctrl+Z 恢复（与旋转/插入空白页/删除页同撤销语义）
- 验证：compileall 零错误 + ruff 全绿 + 回归 418（416 passed + 2 skipped）

详见 `docs/current/DEV_LOG.md` cp111 段。

## P0-3 统一日志框架（2026-08-01，cp95）

引入 `privacyguard/utils/logger.py`，替代全项目散落 print 调试输出：

- **main.py**：55 处 print → logger 调用（异常钩子 / 配置 / 清理 / 渲染 / OCR / 快照）
- **ocr_worker.py**：24 处 print → logger 调用（印章/签名检测 / OCR 引擎 / 页面命中）
- **特性**：控制台 + 文件双通道（2MB 滚动 ×3）、`PG_LOG_LEVEL` 环境变量、PyInstaller 兼容、幂等初始化
- **测试**：`tests/unit/test_logger.py`（9 项），回归基线 385 → **394**（392 passed + 2 skipped）
- 详见 `docs/current/DEV_LOG.md` cp95 段

## main.py 重构完成概要（2026-08-01）

渐进式拆分 Phase 1-4c 全部完成，每步 385 回归全绿，零行为变更：

- **Phase 1**: 57 个自由函数 → `privacyguard/utils/helpers.py`（-1,372 行）
- **Phase 2**: 7 个 Dialog 类 → `privacyguard/ui/dialogs/`（-3,161 行）
- **Phase 3**: 514 行内联 JS → `assets/js/word_preview_interactive.js`（-508 行）
- **Phase 4a**: 7 个独立类 → workers/dialogs/widgets 模块（-995 行）
- **Phase 4b**: 27 个 Word 预览方法 → `WordPreviewMixin`（-794 行）
- **Phase 4c**: 22 个页面视图方法 → `PageViewMixin`（-585 行）
- **总计**: 16,702 → 9,287 行（-7,415 行，-44%）
- **回滚标签**: `pre-phase4`(6c63024) / `pre-phase4b`(90a3150)

详见 `docs/current/MAIN_PY_REFACTOR_PLAN.md`。

---

## 项目清理（2026-08-01）

移除 15MB+ 冗余文件，项目目录整洁化：

- 物理垃圾：3 个空 `_tmp_scrub_*` 目录、192KB 旧备份、11.9MB 测试合并 PDF、2.6MB 截图、.DS_Store、.pytest_cache
- Git 跟踪冗余（8 个文件）：.project_info、PrivacyGuard_AI_Revolution.html、ui_design_preview.html、产品介绍.html、用户使用手册_v37_0_10.html（v37.0.10 过时）、clean_project.bat/.sh、start_app.sh（路径失效）
- CLAUDE.md：9KB 过时副本替换为 AGENTS.md 指针
- .gitignore：新增 .pytest_cache/ 和 _tmp_scrub_*/

---

## v37.8.11 安全审计修复概要（2026-08-01）

全面代码审计后执行 13 项修复，编译检查零错误，回归 384→385 全绿（+1 安全测试）：

- **P0 安全**：trace_cleaner 路径注入白名单校验 / PDF 打开 validate_safe_path / config.json 原子写入
- **P1 稳定**：zoom_scale 零除守卫 / 水印循环迭代上限 / pop(0)→del 切片 / sip.isdeleted try 守卫 /
  冗余 import re / word_worker None 守卫 / doc_converter 悬空路径+antiword 消毒 / image_merge stream+取消
- **P2 质量**：移除 SettingsDialog 调试 print / 移除 OCRWorker 初始化 print

详见 [CHANGELOG.md v37.8.11](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.10 发布概要（2026-07-27）

- **cp87** 脱敏报告：导出弹窗可展开报告+导出 txt，按规则名分类汇总
- **cp88** 会话恢复：遮罩进度自动存草稿，崩溃/误关重开可恢复（含页面结构）
- **cp89** 工程健康：仓库审计 + run_regression 脚本 + test_toolbar_layout + RELEASE_CHECKLIST
- **cp90** 清理使用痕迹：四类痕迹白名单安全清理，WebEngine 占用延迟启动清除
- 核心回归 319→384 项全绿

详见 [CHANGELOG.md v37.8.10](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.9 发布概要（2026-07-27）

- **cp83** 撤销/恢复：“页面”右侧 ↶↷ 图标按钮 + Ctrl+Z/Y；状态快照栈（深 20）
  覆盖遮罩增删与旋转/插入/删除页（字节流快照可真正还原删页）
- **cp84-86** 工具栏根治：双 stretch 布局（utility 贴右不被裁）+ 溢出强制 narrow 降档 +
  语义分组；取消 zoom/nav 强制同宽
- 核心回归 311→319 项全绿（+test_undo_redo 8）

详见 [CHANGELOG.md v37.8.9](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.8 发布概要（2026-07-27）

- **cp81** 全文搜索侧栏：工具栏放大镜按钮切换右侧面板；PDF 文字层秒搜/
  扫描件 OCR（会话缓存可取消）/Word 同步搜；结果黄色高亮片段+页码
- **cp82** 命中高亮定位：点击结果跳页+半透明黄色闪烁（文字层词级/OCR 行级）+
  自动滚动到命中行，2.4s 淡出
- 核心回归 297→311 项全绿（+test_doc_search 14）

详见 [CHANGELOG.md v37.8.8](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.7 发布概要（2026-07-27）

- **cp77** 主页卡内突兀方块修复（scroll 无选择器样式传播根治 + mainContainer 接管底色）
- **cp78** Windows 标题栏 DWM 配色 #EFF4F9→#F6F8FB（Win11 生效，Win10/macOS 静默兼容）
- **cp79** 全局默认字体（Segoe UI Variable/雅黑 UI 栈 10pt，根治 MS Shell Dlg 2 混杂）
- **cp80** 三平台兼容：字体 win32 守卫（macOS 保持系统字体）、QSS 栈补苹方、
  画布字体回退栈；既有平台分支全部复核
- 核心回归 297 项保持全绿

详见 [CHANGELOG.md v37.8.7](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.6 发布概要（2026-07-27）

- **cp75** 遮罩颜色切换实时生效：页面视图 overlay 刷新前同步 mask_color（黑/白/取色即切即变）
- **cp76** 首次进入页面视图零白屏：分帧渲染队列（每帧一页、骨架立现、逐张浮现、
  全程可响应），旧缓存先出过渡帧；退出/重建守卫清队
- 核心回归 297 项保持全绿

详见 [CHANGELOG.md v37.8.6](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.5 发布概要（2026-07-27）

### PDF 加密（cp72，新功能）

- 工具栏锁图标“加密”按钮（智能脱敏左侧，仅 PDF/图片）；单弹框双密码
  （打开/编辑）；导出时随 save 写入 AES-256；密码仅会话级不持久化

### 其它交付

- 7 条新预设规则（统一社会信用代码/车牌/固话默认启用；护照/港澳台/VIN/IP
  默认关），USCC mod31-3 与 VIN 校验位三链路二次校验
- 签名手印黑路径暖色门控 + holes 12（排除楷体/仿宋印刷字误报）
- 去水印页面视图实时刷新；替换文字宽度自适配；box_adjust 对文本层 PDF 生效
- 工具栏重合修复（动态最小窗口，基础 min_width 1120）；框选弹窗去空白/复制/
  取消不遮罩

### 质量

- **核心回归基线 297 项全绿**（258→297，+39 项）；PyMuPDF 加密端到端实测

详见 [CHANGELOG.md v37.8.5](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.4 发布概要（2026-07-27）

### 页面视图交互与性能打磨 cp68

- 移除“双页”按钮（页面视图覆盖其用途；dual_view 机制保留恒关闭）
- 缩放两段式渲染：缓存 pixmap 快速过渡帧 + 260ms 去抖高清；纵横比缓存
- 双向手势阻尼（>0.45s 新手势）：1 列/ZOOM_MIN 边界同手势停住，松手再滚才跨越；
  新增单页缩小进入页面视图通路
- ⛶ 适应页面跨视图统一：任意视图点击回单页自适应（退出延帧计算修尺寸时序）
- Shift 范围选择（锚点机制，Ctrl+Shift 并入选区）

### 质量

- **核心回归基线 258 项保持全绿**；手势/跨视图/范围选离屏冒烟 16 场景全过；
  备份 `backups/cp68_view_interaction_pre/`

详见 [CHANGELOG.md v37.8.4](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.3 发布概要（2026-07-27）

### 新功能：页面视图（多页网格总览 + 页面结构编辑）cp67

- 工具栏“页面”切换（与双页互斥）；Ctrl+滚轮调列数（1 列时继续放大自动退回单页）；
  懒渲染 + LRU 缓存；单击/Ctrl 多选/双击定位
- 左侧线条图标工具栏：左转/右转/插入空白页/删除选中页；遮罩跟随旋转变换，
  页码数据插入/删除自动重排；网格内可直接手动框选脱敏（含 cp65 弹窗流程）
- 旋转页坐标系全链路适配（save_pdf derotation / 文本命中 / 图片块 / 区域识别 clip），
  fitz 语义逐项实测验证

### 质量

- 新增 test_page_view_ops 21 项；**核心回归基线 237→258 项**；开工前备份
  `backups/cp67_multi_page_view_pre/`
- 待真机验收：模式进出、列数缩放、页面操作及导出、网格内框选（完整 MainWindow
  离屏实例化为既有环境限制，已用组件级冒烟 + 真实 fitz 链路断言覆盖）

详见 [CHANGELOG.md v37.8.3](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.2 发布概要（2026-07-27）

### 新功能：手动框选 OCR 识别 + 可选全文遮罩 cp65

- 开关勾选后手动框选：框选即识别（文字层优先，扫描件 3x 剪裁图 RapidOCR）→
  `ManualRegionRedactDialog` 弹窗（识别文字可编辑 + 全文遮罩复选框默认不勾 + 替换文本）
- 全文遮罩复用 OCRWorker 管线，命中进 manual 列表可单个撤销，重叠 >50% 去重，
  所有遮罩叠加同一替换文本

### 交互与 UI 修复 cp66

- 全文遮罩取消：进度条归零 + “⏹️ 扫描停止”提示（原停留在中断百分比）
- “取消”按钮文字截断：专用紧凑样式（上下 padding 归零、字号随高度收敛）
- 工具栏对调：去水印→左上主操作组；智能脱敏→右上工具组（更多与导出之间）

### 质量

- 新增 6 项单测；**核心回归基线 211→217 项全绿**

详见 [CHANGELOG.md v37.8.2](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.1 发布概要（2026-07-27）

### 新功能：Word 关键词行内替换（三级优先级）cp63

- 关键词列表 `find|replace` 行内替换扩展到 Word 链路：
  ① Word 替换规则设置（最高）→ ② 关键词行内替换（`原告|上诉人`）→ ③ 统一替换文本
- 纯函数 `resolve_word_ocr_replacements` 在预览右栏 + `_save_word` 四处合并前统一接入，预览与保存同源
- 顺带修复：统一替换文本合并时取实时值，设置变更后无需重新扫描即生效

### 高级设置按文档类型动态显示 cp62

- 图片/PDF：隐藏“统一替换文本 + Word 替换规则”右卡片；Word：隐藏“3.精度与微调”“4.OCR 检测框”与手动框选开关
- 关键词列表所有场景保留（Word 智能扫描同样匹配自定义关键词）；未打开文件全部显示；隐藏不丢配置

### 修复：手动框选替换开关立即生效 cp64

- 新增 `_sync_manual_replace_prompt_to_canvases`，保存设置后立即推送到左右画布，不再需翻页/重启

### 质量

- 新增 8 项单测；**核心回归基线 203→211 项全绿**；三种 doc_context 冒烟验证通过

详见 [CHANGELOG.md v37.8.1](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## v37.8.0 发布概要（2026-07-27）

### 新功能

1. **签名手印自动识别遮罩 cp60**：高级设置新增“签名手印”勾选（哨兵 `__SIGNATURE_DETECTION__`）。
   以按手印为锚点（红/粉主路径 + 黑色保守路径），形态学过滤
   （solidity/extent/密度/长宽比，基于 7 张真实样本标定），CLOSE+OPEN 防水印粘连，
   紧凑扩展（15%/15%/10%）覆盖相邻潦草签名。已知限制：黑色手印在纯文字 B&W 页可能误报。
2. **Word 预览高亮按来源筛选**：工具栏“高亮筛选”下拉（规则/手动/智能三源），
   data-source 统一 + CSS 过滤态 + 刷新后自动重应用。

### 公章检测增强 cp59（真实卷宗验证）

- max_radius_pt 90→150（实测卷宗公章半径 120-127pt 被旧上限误弃）
- 双通道 CLOSE（小核3 ∪ 大核 round(9×scan_scale)）桥接断环银行章 + 重叠去重
- disc_fill（圆盘充实度）>0.85 强信号，不依赖 OCR/五角星
- 真实样本 `提取自诉讼文书卷三.pdf` 8 页全检出（含双章页）；印章测试 25→31（含真实 PDF 端到端回归）

### UI 精致化 cp61

- 复选框全自绘（18px 圆角/悬停蓝框/选中蓝底白勾 assets/check_white.svg）
- 全局 `outline:none` 消除 Windows 焦点矩形“脏描边”
- 固定默认窗口 1300×900（屏幕 92% 收敛+居中，不再恢复上次几何）
- “适应页面”→ ⛶ 图标按钮（38px，修复与翻页重叠）；公众号名改“池州有个汪律师”

### 质量

- OCR 集成回归 +7（Luhn/身份证/印章哨兵/重叠框）；高亮筛选 +7
- config 对齐测试放宽 `scan.default_level`（运行时持久化的用户选择）
- **核心回归 203 项全绿**；编译检查 main.py/privacyguard/tests 干净

详见 [CHANGELOG.md v37.8.0](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## 全面稳定修复 cp58（v37.7.19）

代码审计发现的两个关键 bug 修复 + 测试覆盖增强：

1. **`_is_bank_card_pattern` 不能识别带前缀的 pattern**（关键 bug）→ 移除 `^` 锚点，支持 `(?<!\d)([1-9]\d{12,18})(?!\d)` 等 config.json 默认 pattern，避免 Luhn 校验失效
2. **`_is_valid_luhn("")` 返回 True**（防御性 bug）→ 增加空输入防御 `if not digits: return False`
3. **测试覆盖增强** → 新增 31 个单元测试（test_luhn_validation 18 个 + test_calculate_sub_rect_width_limit 13 个）
4. **v4 测试兼容性修复** → `TestF19RapidOCRConfidence` 适配 cp57 新增的 `_init_failed` 标志

### 验证

- 编译检查：`python -m compileall -q main.py privacyguard tests` → OK
- Luhn 校验测试：18 passed
- OCR box 宽度限制测试：13 passed
- 全量回归：193 tests，180 passed / 6 skipped / 3 pre-existing failures（v2/v3 OCR 精度测试，与本次修复无关）/ 4 import errors（PyQt6-WebEngine 环境缺失）

详见 [CHANGELOG.md cp58](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## 印章检测多特征融合 + 银行卡号 Luhn 校验 cp51-cp56（v37.7.19）

修复用户反馈的三类核心问题：

1. **印章检测误判严重**（cp51-cp53）→ 多特征融合检测（颜色+形状+五角星+OCR文字）；坐标补偿修复遮罩偏移；去除单字关键词避免红色标题误命中；整块覆盖面积限制
2. **银行卡号导致超大遮罩**（cp54-cp55）→ OCR box 宽度超过图像 80% 跳过；银行卡号 Luhn 校验过滤案件编号/日期等非银行卡号数字串
3. **身份证号被 Luhn 校验误伤**（cp56）→ Luhn 校验前先排除身份证号格式（省级前缀+年月日结构）

### 已知限制

- **公章识别准确率有待提高**：对标准红/蓝圆形印章识别良好，但对变形严重、颜色极淡、盖在复杂文字背景上的印章仍有漏检或误判。后续版本考虑引入深度学习模型。
- **macOS 端虚拟环境依赖待更新**：`venvmac` 内仍为 `rapidocr-onnxruntime==1.2.3`（PP-OCRv4），需在 macOS 环境下升级到 `rapidocr==3.9.2`（PP-OCRv6）后重新打包。后续更换 macOS 系统后更新。

详见 [CHANGELOG.md cp51-cp56](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## 身份证号正则收紧 cp49（v37.7.18）

修复用户反馈：身份证号自动识别脱敏时容易误识别，把横线或无关数字串识别为身份证号。

1. **根因** → config.json 中身份证号正则的 15 位分支 `\d{15}` 过于宽松，任何 15 位连续数字（案件号/统计号/电话拼接等）都被误匹配
2. **修复** → 18/15 位分支均加省级前缀白名单（11-65）+ 月(01-12)+日(01-31) 结构校验；3 处同步：config.json / main.py DEFAULT_RULES / privacyguard/utils/config.py DEFAULT_CONFIG
3. **自动迁移** → `_migrate_legacy_idcard_pattern(cfg)` 启动时检测旧宽松正则并自动升级，已部署用户下次启动即生效
4. **验证** → 13 个新增测试用例覆盖真实身份证号识别 + 各类误识别源排除

详见 [CHANGELOG.md cp49](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## 多字词一体化遮罩 + OCR 实时显示 cp47/cp48（v37.7.17）

修复用户反馈的两个问题：

1. **OCR 过程中遮罩未实时显示**（cp47）→ `_on_ocr_page_result` 原地更新 OCR list + `_maybe_refresh_visible_page` 300ms 节流刷新可见页 canvas
2. **多字词被拆分为多个 per-char 遮罩**（cp48）→ PyMuPDF `search_for` 在 needle 跨多 text span 时返回 per-span rect；新增 `_merge_adjacent_same_line_rects` 合并同 y 相邻 x 的 rect

以 `提取自诉讼证据卷.pdf` 3 页诊断验证：p0 7→5、p1 7→5、p2 3→1，与文本中"王小明"出现次数完全一致。

详见 [CHANGELOG.md cp47/cp48](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## 遮罩左右偏移根因修复 cp46（v37.7.16）

修复 cp45 之后仍存在的系统性左右偏移：部分遮罩向左偏移 30-60pt，或左右覆盖过多。

1. **根因** → `calculate_sub_rect` 的 B 档算法（段数近似但不等时的累计权重 + 线性插值）忽略段间间隙，sub_rect 系统性左偏
2. **修复** → 删除 B 档，C 档（像素收紧权重估算，用 seg_block_width 含间隙）作为默认兜底；A 档（段数严格等于文本长度）保留
3. **验证** → 以 `提取自诉讼证据卷.pdf` 自行测试 41 处命中，子串定位比例正确（15/18），跨页一致，偏移从 -60pt 降至 ±5pt 内

详见 [CHANGELOG.md cp46](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## 遮罩精准度修复 cp45（v37.7.15）

修复用户反馈的三个核心问题：

1. **遮罩不完整覆盖文字** → PDF 坐标系 padding（左右 1pt / 上下 0.5pt）吸收 OCR v3.x box 偏差
2. **多层叠加遮罩** → `_deduplicate_rects` IoU 0.7→0.5 + 新增半重叠取并集合并
3. **左右偏移** → `_detect_text_boundaries` mean>220 阈值 0.30→0.20，避免抗锯齿边缘误判

详见 [CHANGELOG.md cp45](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## OCR 引擎基线（升级后）

- **当前引擎**: RapidOCR
- **当前包**: `rapidocr==3.9.2`
- **当前模型**: PP-OCRv6
- **导入路径**: `from rapidocr import RapidOCR`
- **API 返回结构**: `RapidOCROutput` 对象（`output.boxes / output.txts / output.scores`）
- **回退备份**: `backups/pre_rapidocr_v3_upgrade_20260723/`（回退到 v1.2.3）
- **回退方法**: 见 [CHANGELOG.md cp44](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md)

---

## 2026-07-23 RapidOCR 引擎升级 cp44（v37.7.14）

将 OCR 引擎从 `rapidocr-onnxruntime==1.2.3`（PP-OCRv4）升级到 `rapidocr==3.9.2`（PP-OCRv6），提升中文识别精度。

- 包名变更: `rapidocr-onnxruntime` → `rapidocr`
- 导入路径: `from rapidocr_onnxruntime import RapidOCR` → `from rapidocr import RapidOCR`
- 模型升级: PP-OCRv4 → PP-OCRv6
- **API 返回结构变更（关键）**: v1.x `(result, elapse)` 二元组 → v3.x `RapidOCROutput` 对象（`boxes/txts/scores` 分离属性）
- onnxruntime 升级: 1.16.3 → 1.27.0（PP-OCRv6 用 ONNX IR v10，旧版仅支持 IR v9）
- numpy 升级: 1.26.4 → 2.4.6

### 配套优化

- `privacyguard/ocr/rapidocr.py` 重构 `recognize` 适配 v3.x `RapidOCROutput`，修复"整个文档被黑遮/白遮"（OCR 解包失败触发保守整块覆盖）
- `privacyguard/utils/config.py` DEFAULT_CONFIG 与 config.json 同步（cp43 遗漏的 custom_keyword_rules/manual_replace_prompt 字段、custom_keywords、default_level）
- 修正 3 处过期测试期望（fallback=`0.0.0`、default_level=`1.0`，对齐 cp41 版本号统一来源）

详见 [CHANGELOG.md cp44](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## 2026-07-23 RapidOCR 升级前备份 cp44-pre（v37.7.13）

为 RapidOCR 从 v1.2.3 升级到 v3.9.2 做准备。**未修改任何运行时代码**，仅完成备份与文档记录。

- 备份 16 个文件到 `backups/pre_rapidocr_v3_upgrade_20260723/`
- 记录当前导入路径、调用方式、API 返回结构
- 提供回退步骤（还原代码 + 还原依赖）

详见 [CHANGELOG.md cp44-pre](file:///c:/Users/49144/Desktop/ClaudeCodeHub/PrivacyGuardApp/CHANGELOG.md) 段。

---

## 2026-07-23 PDF 替换文本叠加层 cp43（v37.7.13）

新增 PDF 替换文本叠加层功能：遮罩后可在原位置叠加替换文本层，使遮罩区域从色块变为可读替换内容，类似 Word 替换预览。

### 改动

- **自定义关键词表格化**：高级设置中从单行文本框改为 3 列表格（启用 / 查找 / 替换为），每条关键词可独立填写替换文本（留空 = 纯遮罩）
- **OCR 命中文本透传**：`text_pdf` 返回 5 元组含 `found_str`；`mixed_pdf` 返回 `(rect, matched_text)` 元组；`OCRWorker._lookup_replace` 按映射查找替换文本
- **page_data dict 改造**：命中项改为 `{'rect': QRectF, 'replace_text': str}`，通过 `_hit_rect` / `_hit_replace_text` / `_make_hit` 兼容函数访问
- **预览叠加**：`paintEvent` 在遮罩矩形上用对比色居中绘制替换文本
- **导出叠加**：`save_pdf` 用 `add_redact_annot(text=..., fontname="china-s")` 原子叠加文本层
- **手动框选替换**：`manual_replace_prompt` 全局开关，开启后框选完成弹窗输入替换文本
- **配置持久化**：`config.json` 新增 `custom_keyword_rules` + `manual_replace_prompt` 字段；旧 `custom_keywords` 自动迁移

### 验证

- 编译检查 OK
- 回归测试：44 tests OK（唯一 ERROR 为已知 PyQt6.QtWebEngineWidgets 环境缺失）
- 单元测试：`test_custom_keyword_rules.py` 12/12 通过
- 待用户手动验证：高级设置关键词表格、遮罩预览叠加文本、导出 PDF 文本层、手动框选弹窗

### 注意事项

- 替换文本留空 = 纯遮罩（向后兼容）
- 手动框选替换默认开启，可关闭恢复纯遮罩
- 替换文本叠加依赖 PyMuPDF `china-s` 字体

---

## 2026-07-23 版本号统一来源 cp41（v37.7.12）

### 改动

- **版本号唯一来源**: `version.txt`（已是唯一动态来源）
- **消除硬编码失败后备值**: `main.py` 和 `privacyguard/__init__.py` 的失败后备从 `"37.7.6"` 改为 `"0.0.0"`，避免过期版本号误导
- **去掉 VERSION 描述后缀**: `VERSION = APP_VERSION`（不再附加 ` - Engineering Remediation`），界面/标题栏显示纯版本号
- **iss 默认值防呆**: `PrivacyGuard_Setup.iss` 默认值从 `"37.7.10"` 改为 `"0.0.0"`，直接编译 iss 会得到明显错误版本，提醒用打包脚本
- **文档版本号同步**: 11 处当前状态描述同步到 v37.7.12（历史段标题保留不改）

### 验证

- 编译检查 OK
- version_info.txt 重新生成（37.7.12.0）
- 待用户手动验证：标题栏显示 `PrivacyGuard 脱敏卫士 v37.7.12 - Powered by li (汪立律师)`，关于对话框显示 `版本 37.7.12`

---

## 2026-07-23 去卷宗水印功能 cp40（v37.7.11）

新增"去水印"按钮，自动识别并去除电子卷宗 PDF 中以文字层 span 形式嵌入的斜排水印（律师执业证号 + 姓名，如 `13417202010172812刘韧`）。

### 新增功能

- 工具栏 `toolbar_utility_layout` 在"导出"按钮前新增 `btn_remove_watermark`（仅 PDF 模式可见）
- **PDF 内容流编辑去除水印**（非遮罩覆盖，三条件判定）：
  - `_remove_watermark_from_stream(page)`：三条件判定删除水印 q...Q 块
    1. 块内含 cm 指令且变换矩阵有旋转/剪切分量（b≠0 或 c≠0，支持任意旋转角度）
    2. 块内含 Tf 指令（绘制文本）
    3. 块内不含 Do 指令（避免误删 Form XObject）
  - `_parse_qq_blocks(s)`：解析内容流 q...Q 嵌套结构
- 评分制识别 `_detect_watermark_spans`（5 项特征满足 ≥3 项，用于确认对话框统计）：
  1. bbox 近似正方形且偏大
  2. 字体含 CJK 关键词
  3. 颜色非纯黑
  4. 文本含数字 + (含中文 或 长度≥6)
  5. 斜排检测（首末字符中心点连线斜率 0.1-10）
- 入口方法 `remove_case_file_watermark`：扫描 → 确认 → 逐页内容流编辑 → 刷新预览 → 启用导出

### 关联改动

- `save_pdf` 增加 `_pdf_modified` 分支：去水印后用 `self.doc.tobytes()` 复用内存字节流
- 按钮显隐联动：`_cleanup_before_open` 隐藏 + 重置 `_pdf_modified=False`；`_open_pdf_file` 成功后 `show()`
- Density 文案同步：wide/compact/narrow 三档分别为"去水印/去水印/水印"
- `_refresh_toolbar_overflow_menu` narrow 模式收纳 + compact/wide 显式 show 兜底

### 验证

- 编译检查 OK
- 识别算法验证：对 `提取自诉讼文书卷.pdf` 识别到 28 处水印
- **内容流编辑验证**：删除 2 个顶层 q...Q 块，内容流 14919 → 35 字节
  - 正文完整性：10/10 关键正文全部保留
  - 水印残留：0
  - 不留白色块（非遮罩）
- 回归测试：21 tests ok

### 注意事项

- 仅针对文字层水印，扫描件图片层水印不适用
- 白色填充，匹配白底文字卷宗；非白底会留白块
- 不自动保存，需手动点"导出"写盘

---

## 2026-07-22 PDF 取色遮罩功能 cp39（v37.7.10）

在 PDF 工具栏"黑遮罩/白遮罩"右侧新增"取色遮罩"按钮，支持任意颜色作为遮罩色。

### 新增功能

- 工具栏新增 `rb_color` 按钮（位于白遮右侧、双页左侧），与黑/白遮加入 `QButtonGroup(exclusive=True)` 三选一互斥
- 色板面板内联展开（toolbar 与 scroll 之间）：8 常用色块 + 自定义 `#RRGGBB` 输入 + 全屏取色器
- 全屏取色器：截取主屏 → 全屏覆盖层 → 十字光标 + 实时颜色预览 + HEX 文本 → 点击取色 / Esc 取消

### 关键 bug 修复（cp39-fix1）

- **高 DPI 屏取色不准**：`grabWindow(0)` 返回物理像素 QPixmap，但 QWidget 鼠标坐标是逻辑像素，直接 `pixelColor(mouse_pos)` 会取到错误像素
- 修复：新增 `_pick_color_at` 做 DPI 缩放转换；用 `setGeometry(screen.geometry())` 替代 `showFullScreen()`；鼠标点击时再取一次色

### 关联 bug 修复

- `update_canvas_color` 重写兼容三态（原 `else` 分支强制设为白会覆盖取色）
- `save_pdf` 修复硬编码：原 `fill_col` 仅识别 #000000 为黑，其余按白(1,1,1)处理，改为按 RGB 归一化
- Density 文案同步 color_text：wide/compact/narrow 三档分别为"取色遮罩/取色/色"
- narrow 模式收纳：rb_color 移入"更多"菜单

### 验证

- 编译检查 `python -m compileall -q main.py` → OK
- 回归测试 64 tests / failures=0 / skipped=2（唯一 ERROR 为环境限制 `PyQt6.QtWebEngineWidgets` 缺失，与改动无关）
- `test_fstring_safety` 误报修复：f-string 中 `{{ border:` 被 regex 误判为未转义 CSS，改用 `%` 字符串格式化

---

## 2026-07-22 PDF 遮罩精准度修复 cp34-cp38（v37.7.9）

解决图片 PDF / 混合 PDF 的图片块 OCR 命中后 sub_rect 计算 bimodal 偏移问题（左右多遮半个到一个字符、宽度多出几个字符）。

### 根因

- G18: cp37 F20 用 INTER_CUBIC 2x 放大 ROI 导致抗锯齿填充字符间隙，段切分退化为单段
- G19: ROI 边界等于 OCR box，RapidOCR box 有 ±2-5px 偏差，字符可能略超 box 边界
- G20: gap_tolerance = max(2, min(median_gap*1.5, char_h/3))，char_h/3 > gap 时把 gap 当短间隙不切断
- G21: _calculate_from_line 坐标转换条件化，F23 外扩后 scale=1.0 但 offset>0 时跳过转换

### cp38 最终稳定化（F20-redesign + F23 + F24）

- F20-redesign: 放弃 2x 放大，只做 F23 外扩 8px，scale_factor=1.0
- F23: ROI 边界外扩 8px，容纳 RapidOCR box ±2-5px 偏差
- gap_tolerance 加 median_gap * 0.8 上限，确保 gap > gap_tolerance 能切断
- 坐标转换无条件化：删除 `if scale_factor != 1.0` 判断
- F24: _verify_sub_rect_width 宽度合理性检查兜底（sub_w 过窄回退权重估算 / 过宽用段块宽度收紧）

### 累计修复（cp34-cp37）

- cp34 R1-R5: 像素级字符切分 + y 方向边界检测 + margin PDF 点空间 + min 宽度 + 边界保护
- cp35 F1-F5: 三档混合算法（A/B/C 档）+ 形态学核宽 + 超宽段二次切分 + 阈值自适应
- cp36 F6-F15: B 档累计权重对齐 + C 档 seg_block_width + 自适应间隙 + 等分回退 + box_adjust_ratio 复活 + 阈值更严格 + margin 对称 + dedup 面积升序 + 二值化兼容
- cp37 F16-F20: B 档 _interp_pixel 不跨 gap + _detect_vertical_boundaries 收紧 y + 跨行 box 切单行 + RapidOCR 真实 confidence

### 验证

- v3 测试 28 个通过（2 skip 为 PyQt6.QtWebEngineWidgets 环境依赖）
- v4 测试 11 个全通过
- v5 测试 5 个全通过
- 核心回归套件（mixed_pdf / path_validation / ocr_api / package_imports / pdf_text_hit_dedup / fstring_safety）全部通过
- 编译检查 → OK

---

## 2026-07-21 第三轮代码审计修复（cp33）

在 cp32 基础上继续完成 6 项遗留修复与代码清理。

### 严重（功能阻断 / 漏脱）

- **项1** Windows 路径校验误拒 → Windows 下改黑名单模式（拒系统目录，其余放行），POSIX 保持原白名单
- **项2** W4 Word 扫描竞态 → `add_manual_redaction` / `add_manual_redaction_global` 入口扫描运行时拦截
- **项3** W2 页眉/页脚命中无提示 → `word_scan_finished` 新增 `header_*` / `footer_*` 命中统计

### 一致性（死代码 / 包结构）

- **项4** 死代码清理：
  - `main.py` 删除 ~293 行死代码（顶部 OCR 全局 / 未用 mixed_pdf 导入 / 6 个死函数 / PRIVACYGUARD_PRELOAD_OCR 启动预热块）
  - `privacyguard/ocr/__init__.py` 改懒加载模式
  - 删除空壳包 `privacyguard/core/` 与 `privacyguard/ui/`
  - `packaging/windows/config/hook-privacyguard.py` 移除已删除包引用

### 测试质量

- **项5** 过期测试修正：
  - `tests/unit/test_stability.py` 重写为 9 个真实 TestCase（直接 import 生产代码）
  - `tests/unit/test_ocr_api.py` 加强断言（`__call__` 可调用 + 签名检查）
  - `tests/scripts/test_word_processor.py` 改用 `paragraph_plain_text` / `cell_plain_text` 口径 + `skipUnless` 保护
  - `tests/test_path_validation.py` 修复 POSIX 模式用例 `expanduser` mock 缺失

### 配置系统

- **项6** 配置系统收敛：
  - 修正 `DEFAULT_CONFIG` 中 `印章.description` 与 `config.json` 漂移
  - `tests/unit/test_config_alignment.py` 新增 5 个对齐用例
  - 按 AGENTS.md 约定保留 SimpleConfig 作为运行时入口

### 当前验证

- `python -m compileall -q main.py privacyguard tests` ✅
- `python -c "import privacyguard; from privacyguard.ocr import OCREngineManager"` ✅
- `tests/unit/test_stability` 9/9 ✅
- `tests/test_path_validation` 13/13 ✅
- `tests/unit/test_ocr_api` 3 用例（rapidocr 未装时 skip）
- `tests/scripts/test_word_processor` 7 用例（fitz 未装时 skip）
- DEFAULT_CONFIG 与 config.json 深度对齐脚本 → 完全一致 ✅

### 仍待处理（下一轮）

- 真机截图驱动的最后一轮观感抛光
- 正式发布前的 Windows / macOS 产物验收
- Phase 2：批量替换每文件规则映射 / 规则模板 / 预览高亮按来源筛选

详见 `CHANGELOG.md` 与 `rollback_journal.md` cp33 条目。

---

## 2026-07-21 第二轮代码审计修复（cp32）

接手上一个 agent 中断的修复工作（W1-W5 / O1/O2/O8 共 8 项已完成），完成第二轮全量审计并修复 9 项遗留正确性/一致性问题。

### 严重（UI 卡死 / 数据污染）

- **S1** OCRWorker 引擎不可用时 early return 跳过 finished_signal → 改为 raise 后落入统一信号发射路径
- **S2** WordBatchReplaceWorker 单文件 except 过窄，损坏 docx 抛 PackageNotFoundError 逃出 run() → 兜底 `except Exception`
- **S3** `_cleanup_before_open` / `_app_exit_cleanup` 超时后直接丢弃线程，旧信号污染新文档 → 断开信号 + deleteLater

### 中等（异常盲区 / 漏脱风险）

- **M1** `_open_pdf_file` 无 try/except，损坏 PDF 异常直达全局 hook → 拦截并显式提示
- **M7** 加密 PDF 无认证流程 → `needs_pass` 时显式提示后拒绝打开
- **M7'** `_open_word_docx` / `_save_word` except 列表缺 PackageNotFoundError → 纳入捕获
- **M4** Word 保存缺 O1 等效保护 → 新增 `_word_scan_meta` + 保存前二次确认
- **L7** `collect_image_block_ocr_hits` 预处理异常中断整篇扫描 → 包进单块 try 保守覆盖

### 一致性

- **B1** WordWorker `_emit_progress` 节流失效 → 仅在真正发射时返回新时间戳
- **B2** `_check_doc_support` 与 `resolve_soffice_cmd` 双份 LibreOffice 探测口径不一致 → 统一委托共享模块

### 当前验证

- `python -m compileall -q main.py privacyguard tests` ✅
- 与本次改动相关的 7 个测试文件（59 用例）全过 ✅
- 完整回归套件 88/92 通过；4 个失败为修复前即已存在的跨平台路径测试（mock `platform.system` 但路径函数走真实 OS，在真 Windows 上必然失败），与本次改动无关

### 仍待处理（下一轮）

- Windows 路径校验 `validate_safe_path` 跨盘符/UNC 误拒（批量替换 D 盘文件会失败）+ 配套测试 mock 修正
- W4 残留竞态：扫描期间 WebView 手动脱敏未禁用
- W2 预览链路遗漏：页眉页脚 `header_*`/`footer_*` 键不可见/不可手动脱敏
- OCR 初始化双轨 + OCREngineManager 死代码清理
- 空壳包 `privacyguard/core/`、`privacyguard/ui/` 清理
- 过期测试 `test_stability.py`、`test_ocr_api.py` 恒真断言修正

详见 `CHANGELOG.md` 与 `rollback_journal.md` cp32 条目。

---

## 2026-05-16 全面重复实现收敛

### 已完成

- **OCRWorker**：main.py ~500 行内联实现 → 继承自模块版的 14 行兼容层
  - 模块版已上行：印章检测、像素级文本边界、CJK 智能字符权重、检测框收缩、error_signal、box_adjust_ratio
- **WordWorker**：main.py ~118 行内联实现 → 继承自模块版的 7 行兼容层
- **ImageMergeWorker**：main.py ~50 行完全相同的内联实现 → 模块导入
- **DOC 转换**：新增 `privacyguard/utils/doc_converter.py`，WordBatchReplaceWorker 和 MainWindow 均委托给共享模块
- **版本回退**：main.py 和 privacyguard/__init__.py 的版本回退值统一为 "37.7.6"
- 新增收敛回归测试 (`test_convergence.py`，10 项)
- main.py 从 ~13,530 行减至 12,611 行，净减少约 920 行重复代码

### 累计完成（v37.7.5 + v37.7.6）

- 配置漂移修复（5 处 DEFAULT_CONFIG 与 config.json 值不一致 + 4 个缺失键）
- persist 默认值统一为 True
- 代码去重：PrivacyAppError + 子类、TempFileManager、resource_path、ImageMergeWorker、WordWorker、OCRWorker、DOC 转换
- 新增测试：test_config_alignment.py、test_fstring_safety.py、test_convergence.py + 扩充 test_path_validation.py、test_app_config.py

### 当前验证

- `python3 -m compileall -q main.py privacyguard tests` ✅
- 全量回归：`69/69` 通过 ✅

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
