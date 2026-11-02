# 仓库审查与 GitHub 更新记录（2026-11-02）

## 结论与范围

当前源码版本仍为 **40.2.5**。项目定位明确：帮助法律文书和日常办公资料在对外分享、上传 AI 服务之前，在本机完成候选敏感信息识别、人工补充与结果复核。

本轮完成全仓文件清点、当前受跟踪文件完整字节读取/哈希、文本密钥模式检查、Python AST 解析、核心流程代码复核、Windows 回归与原生自检、实际 PDF/Word 界面操作及展示文档整理。**文件被程序读取、解析或哈希，不等于人工逐行审核**；没有声称逐行读完全部历史文档和每个第三方依赖，也没有宣称每个 UI 控件都完成手工验收。

初始 Git 跟踪 347 个文件；排除两份本地代理计划后，初次完整清单为 345 个文件、139 个 Python 文件、83,458 行文本。新增展示与审查文件后的最终清单见 `publication_inventory_20261102.json`（清单自身不参与自校验）。覆盖根目录、privacyguard、tests、packaging、scripts、assets、docs、user-guides 和 .github。历史说明保留历史语境，不把旧行数和旧测试数量当成当前状态。

虚拟环境、第三方库、打包输出、发布 ZIP、备份、日志、缓存、私人配置与代理工作区属于本地环境/数据，不进行第三方源码逐行审计，不加入本次公开快照。图标/图片/Office 样本的字节清点并不构成其内容匿名性证明；新展示图使用专门生成的虚构数据并目视复核。

## 功能检查矩阵

下表“回归通过”指本轮执行了仓库对应的自动化测试，不能外推为任意实际文档无漏脱。GUI 实拍范围只有首页、PDF 扫描与书签、Word 替换与双栏预览。

| 功能域 | 代码/测试入口 | 本轮证据与边界 |
| --- | --- | --- |
| 版本与配置 | main.SimpleConfig、utils/config、test_app_config | 动态版本读取与配置持久化回归通过；运行时仍用 SimpleConfig |
| PDF 文字规则 | ocr/text_pdf、test_pdf_text_hit_dedup、test_extended_rules | 去重、校验和及规则回归通过 |
| 扫描与混合 PDF | ocr/mixed_pdf、workers/ocr_worker、test_mixed_pdf_ocr | 块 OCR、坐标偏移与失败保守处理回归通过；真实本地 OCR 自检通过 |
| 印章/签名手印 | ocr/seal_detection、signature_detection | 合成样本回归通过；两项真实样本不公开故跳过 |
| 称谓人名与跨页传播 | ocr/person_name、test_person_name_pipelines | 规则与回填测试通过；默认关闭，非通用 NER，不宣传通用 100% 准确率 |
| 手动与全文遮罩 | test_manual_region_dialog、test_targeted_mask_scan | 规则生成与范围行为回归通过；不以搜索结果代替内容安全判断 |
| 页面网格与结构 | ui/mixins/page_view_mixin、test_page_view_ops | 缩放、旋转、插删页及遮罩转换回归通过；未完成所有 DPI/多屏手工验收 |
| 提取与截去 | utils/helpers_pdf、pdf_regions、test_extract_crop | 合成导出流中区域外原文移除测试通过；源遮罩不自动应用到提取结果 |
| 书签 | ui/mixins/bookmark_mixin、test_bookmark | 编辑、标题规则与字面替换回归通过；GUI 已打开真实面板 |
| PDF 加密 | test_pdf_encrypt、test_pdf_password | 打开/编辑权限与导出参数回归通过；不扩展为全面 PDF 净化保证 |
| 全文搜索 | workers/search_worker、test_doc_search | 文字页与扫描页回归通过；混合页有文字层时跳过图片 OCR 的边界仍存在 |
| 撤销/恢复 | test_undo_redo、test_session_store | 遮罩/结构快照与草稿读写回归通过；快照明文残留边界保留 |
| Word 正文/表格/页眉页脚 | helpers_word_doc、test_word_header_footer_redaction | 既有遍历范围回归通过；超链接和嵌套表格等未统一覆盖 |
| Word 预览与替换 | helpers_word_preview、assets/js、test_word_replace_rules | DOM/偏移/来源筛选等回归通过；实际虚构手机号替换与双栏展示通过 |
| 批量 Word | workers/batch_replace_worker、test_batch_word_replace | 规则统计、失败决策时序回归通过；仍是全文件共享规则 |
| Word 加密输入与 .doc | utils/word_crypto、doc_converter、test_word_crypto | 加密工具契约与临时目录回归通过；未穷举真实 Office 加密格式，.doc 依赖外部转换 |
| HTML/路径/日志 | utils/html_sanitize、security、test_html_sanitize、test_logger | 预览消毒、路径限制、日志掩码与现有安全测试通过；没有做第三方组件漏洞数据库扫描 |
| 清理与线程退出 | trace_cleaner、worker_lifecycle 及对应测试 | 路径白名单、生命周期回归通过；Windows 符号链接创建测试跳过 |
| 打包 | Windows portable builder、macOS checker 及测试 | 构建逻辑/合成 PE 检查回归通过；本轮没有重新构建或发布二进制 |

## 本轮实际修正

1. `tests/unit/test_release_audit.py` 读取 spec 时显式使用 UTF-8，修复 Windows 中文默认 GBK 环境中的 UnicodeDecodeError。没有通过修改生产逻辑掩盖测试失败。
2. `.gitignore` 增补 macOS 发布环境、代理状态、缓存、环境变量文件、草稿快照和私钥扩展名。两份 `.zcode` 计划从索引移除，本地文件保留。
3. 尚未推送的 100 次提交中存在已删的 `config.json` 和 `_tmp_idx_test`。直接推原分支会把它们带进历史。公开更新采用以远端当前提交为父提交的干净源码快照；本地原 main 与开发历史保留，不强推、不重写远端已有历史。已公开旧历史不在本轮清除范围。
4. README 中旧版本、旧回归数量、失效启动环境和已完成却仍列为待办的描述改写为当前能力；不把 macOS 验证结果冒充 Windows 验证。
5. 补充中英文展示页、安全反馈说明、Issue/PR 模板、仓库介绍/Topics 文案、原创矢量横幅及 4 张实际软件截图与 PNG 社交封面。

## 验证结果

- 首次受限环境测试：741 项，5 失败、6 错误、3 跳过。其中一项为编码问题，其余涉及受限临时目录中的原子替换权限。日志留本地，不公开本机路径。
- 修正 UTF-8 读取后，在正常 Windows 权限环境重跑：**741 discovered / 738 passed / 3 skipped**。
- 跳过：两项未提供的真实印章/手印 PDF；一项 Windows 平台显式跳过的符号链接创建测试。没有把 skip 记作 pass。
- Ruff 和 `pip check` 通过；最终交付前另执行编译与文档/资源检查。
- `main.py --self-test`：XML、Decimal、含图片 DOCX 转 HTML 与替换保存、安全 PDF 矢量提取、禁止 socket.connect 下的真实离线 OCR、版本资源、主窗口打开 Word/关闭均通过。
- GUI：以出厂模板创建独立演示配置，打开虚构 3 页 PDF，智能扫描并看到手机号遮罩，打开书签面板；打开虚构 DOCX，完成 1 处手机号替换并显示双栏。素材无真实案件内容。

## 尚未解决的重点

| 优先级 | 事项 | 对当前使用的影响 |
| --- | --- | --- |
| P1 | Word 统一 OOXML 文本节点映射与递归遍历 | 超链接可见文本、嵌套表格及特殊部件可能漏处理，需要跨预览/扫描/导出设计，不能简单改 para.text |
| P1 | PDF 元数据/附件/表单/动作净化策略 | 已选区域处理不等同文件全体敏感信息清除 |
| P2 | 混合页全文搜索覆盖与错误状态 | 搜不到图片文字不能判定其不存在；搜索的 OCR 失败可降级为空结果，与脱敏扫描失败策略不同 |
| P2 | 正向/反向称谓扩展表契约 | 自定义称谓在不同语法路径的覆盖不完全一致 |
| P2 | 大 Word 主线程准备、网格卡片虚拟化与正则超时 | 超大文件或复杂正则仍可能影响响应 |
| P2 | 明文草稿与解密临时文件 | 权限限制无法替代磁盘加密与使用后清理 |
| P2 | Windows 符号链接、macOS 14、Intel 与冻结包矩阵 | 本轮未覆盖，不能凭单测或静态二进制门禁宣布全部平台兼容 |

上述事项为排查结果，未在本次展示更新中擅自开展跨模块功能重写；README 已明确披露。建议先完善 Word XML 覆盖，再增加 PDF 净化策略，随后做平台与大文档矩阵。

## 复现与后续

- 全量回归：`scripts/run_regression.ps1`。
- 原生自检：平台虚拟环境的 Python 执行 `main.py --self-test`。
- 发布前暂存清点：`python scripts/audit_publication.py`；启发式密钥模式只报告路径/行号，不打印匹配值，不等于全面 DLP 或漏洞审计。
- 虚构素材：`python scripts/create_showcase_samples.py`，仅生成测试输出。
- 展示文案与素材索引：`docs/marketing/GITHUB_SHOWCASE.md`。
- GitHub 连接器可写 Git 对象；本地无现成 GitHub HTTPS 写入凭据。仓库 About/Topics 与 Social preview 的自动更新能力独立于源码推送，未完成的设置应明确报告，不能冒充已设置。

历史增量检查：916 个历史 blob 完成启发式密钥模式扫描，未命中所检查的密钥模式；发现的配置/临时索引路径风险仍按快照发布策略隔离。最终公开文件清单以 Git 索引的规范字节计算 SHA256，避免跨平台 CRLF 转换导致校验漂移。
