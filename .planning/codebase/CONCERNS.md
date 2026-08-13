# Codebase Concerns

**Analysis Date:** 2026-08-10

## Tech Debt

**单体运行时入口：**
- Issue: `main.py` 仍承载 12,611 行代码，包含 Qt UI、配置、Word 预览、批量处理、PDF 导出、线程编排和兼容层。共享模块已经存在，但主程序仍是主要变更面，任何 UI 或业务修改都可能影响启动、线程生命周期和文档处理。
- Files: `main.py`, `privacyguard/workers/ocr_worker.py`, `privacyguard/workers/word_worker.py`, `privacyguard/utils/doc_converter.py`
- Impact: 审查困难、回归范围大、主程序与模块边界容易再次漂移；错误通常只能通过整套 GUI/打包验收发现。
- Fix approach: 保持 `main.py` 只做 UI 与编排；新增共享算法优先放入 `privacyguard/`，再用兼容层委托；每次迁移都增加“唯一实现/委托关系”测试，避免恢复平行实现。

**双配置路径：**
- Issue: 活跃运行时使用 `main.py` 中的 `SimpleConfig`，而 `privacyguard/utils/config.py` 提供另一套单例、默认值合并、校验、回调和热重载实现。`tests/unit/test_config_alignment.py` 只能验证部分静态值一致，不能阻止两套运行时语义继续分叉。
- Files: `main.py`, `privacyguard/utils/config.py`, `config.json`, `config.json.template`, `tests/unit/test_config_alignment.py`
- Impact: 设置可能读写不同对象或不同默认值；模块调用者可能误以为 `ConfigManager` 是真实配置入口；新增配置字段需要多处同步。
- Fix approach: 选择一个运行时唯一入口，迁移前列出 `SimpleConfig` 的所有调用点和持久化行为；保留兼容 API 时明确其只委托到唯一实现，并增加读写、默认合并、错误恢复和重启持久化测试。

**兼容层与历史代码共存：**
- Issue: `main.py` 中的 `OCRWorker`、`WordWorker` 已缩减为模块 worker 的兼容子类，但主文件仍包含大量历史版本注释、旧辅助流程和 UI/业务耦合；`tests/unit/test_stability.py` 还复制了旧版异常和临时文件管理器实现，而不是测试实际模块。
- Files: `main.py`, `tests/unit/test_stability.py`, `privacyguard/utils/exceptions.py`, `privacyguard/utils/temp_manager.py`
- Impact: 复制测试可能继续通过而实际实现回归；历史代码和版本注释增加维护噪声，降低删除死代码的信心。
- Fix approach: 将稳定性测试改为直接导入 `privacyguard.utils.exceptions` 和 `privacyguard.utils.temp_manager`；逐步删除未被调用的旧实现和过时测试脚本，并以覆盖率或调用图确认安全删除。

## Known Bugs

**发布版本资料与代码基线不一致：**
- Symptoms: 当前状态和 `version.txt` 基线为 v37.7.6，但多个 active packaging 文档、安装器默认值和 Windows 版本资源仍写着 v37.7.4；`CHANGELOG.md` 的最后更新也停留在 2026-03-18。
- Files: `version.txt`, `packaging/windows/config/PrivacyGuard_Setup.iss`, `packaging/windows/config/version_info.txt`, `packaging/README.md`, `docs/packaging/README.md`, `docs/current/DEV_LOG.md`, `docs/current/PROJECT_SUMMARY.md`
- Trigger: 按当前 v37.7.6 代码执行安装器或阅读打包说明。
- Workaround: 构建前运行 `packaging/windows/scripts/generate_version_info.py`，并人工核对安装器回退值及 active 文档；该流程不能消除文档本身的漂移。

**Windows 产物缺少真机闭环验证：**
- Symptoms: `docs/current/STATUS.md` 记录 NumPy 2.x、onnxruntime DLL、PyInstaller hidden import 等 Windows 打包修复，但当前环境没有实际执行 `.bat` 和 Inno Setup；修复结论主要停留在 spec/脚本层。
- Files: `packaging/windows/config/PrivacyGuard_windows.spec`, `packaging/windows/config/PrivacyGuard_windows_v2.spec`, `packaging/windows/config/hook-privacyguard.py`, `packaging/windows/config/runtime_hook_privacyguard.py`, `packaging/windows/scripts/build_complete.bat`, `docs/current/STATUS.md`
- Trigger: 在干净 Windows 环境打包并启动 OCR、Word 预览或 `.doc` 转换功能。
- Workaround: 在 Windows 真机执行 `packaging\\windows\\scripts\\build_complete.bat`，再执行 OCR、NumPy、WebEngine、LibreOffice 和安装/卸载验收。

**DOC 转换直接 API 的临时目录生命周期错误：**
- Symptoms: `convert_with_libreoffice()` 和 `convert_with_antiword()` 在 `temp_dir=None` 时创建临时目录，并在 `finally` 中删除它后才返回输出路径；直接调用这些函数会得到指向已删除文件的路径。
- Files: `privacyguard/utils/doc_converter.py`
- Trigger: 直接调用 `convert_with_libreoffice(doc_path)` 或 `convert_with_antiword(doc_path)`，而不是通过 `convert_doc_to_docx()` 提供共享目录。
- Workaround: 当前批量流程通过 `convert_doc_to_docx()` 调用并自行登记目录；外部调用者必须显式传入生命周期由调用方管理的 `temp_dir`。

## Security Considerations

**路径安全校验未解析符号链接：**
- Risk: `validate_safe_path()` 使用 `abspath()`、`normpath()` 和 `commonpath()` 做范围判断，但没有对现有文件或父目录执行 `realpath()`；允许目录内的符号链接可能把读取/写入导向允许范围外。
- Files: `privacyguard/utils/security.py`, `privacyguard/utils/doc_converter.py`, `main.py`
- Current mitigation: 禁止 shell 元字符、空字节、部分 URL 编码序列和路径遍历，并限制到用户目录、临时目录或当前目录。
- Recommendations: 对输入文件和输出目录分别执行 `resolve(strict=...)`/`realpath` 校验；明确是否允许符号链接；在 Windows 覆盖 junction、UNC、驱动器切换和大小写规范化场景，并增加对应测试。

**用户敏感文本进入标准输出：**
- Risk: 手动撤销日志会打印被处理的完整文本，设置日志会打印规则对象；若应用从终端、IDE 或收集 stdout 的启动器运行，敏感内容可能留在日志或诊断记录中。
- Files: `main.py`（约 2604、4326 行附近）
- Current mitigation: OCR worker 主要打印错误和计数，未检测到统一脱敏日志策略。
- Recommendations: 默认不记录原文、关键词或完整路径；使用结构化日志并做字段级掩码；仅在显式 debug 模式下记录哈希或截断值。

**外部转换进程的信任边界不完整：**
- Risk: `.doc` 转换会把用户文件交给 LibreOffice 或 antiword 子进程处理；虽然命令使用参数列表且有超时，但没有资源限制、进程树终止或输出目录隔离的完整策略。
- Files: `privacyguard/utils/doc_converter.py`, `packaging/windows/scripts/launcher_wrapper.bat`
- Current mitigation: 路径校验、临时目录、LibreOffice 超时和失败回退。
- Recommendations: 为转换任务设置独立临时目录、限制输出文件、超时后终止进程树，避免残留子进程；对第三方转换器版本和输入格式进行安全审计。

## Performance Bottlenecks

**OCR 页面级渲染和图像块扫描开销高：**
- Problem: `OCRWorker.run()` 对每页读取文本字典，并对嵌入图片块单独渲染和 OCR；印章检测启用时还会再次以扫描比例渲染整页。
- Files: `privacyguard/workers/ocr_worker.py`, `privacyguard/ocr/mixed_pdf.py`
- Cause: 图片块、整页 OCR 和印章检测之间没有共享渲染结果或缓存；每页处理还会产生 NumPy/OpenCV 中间对象。
- Improvement path: 明确页面扫描计划，复用同一 pixmap/图像；限制重复覆盖区域；按页或批次测量峰值内存与耗时，再决定缓存和并发策略。

**Word 双栏 WebEngine 仍存在全量加载边界：**
- Problem: 活跃路径已经按 `data-word-block` 做局部 patch，但首次加载、源文档变化和 compare 模式重新进入时仍调用 `QWebEngineView.setHtml()`；关闭 compare 时右栏清空，重新开启需要整页重新载入。
- Files: `main.py`（`render_word_preview()`、`_build_word_preview_documents()`、WebEngine 清理逻辑）
- Cause: 预览缓存、左右面板 ready 状态和临时图片资源目录由单体窗口管理，状态切换复杂。
- Improvement path: 将预览状态模型、面板生命周期和 DOM patch 封装成独立组件；对 50+ 页、嵌入大图、连续设置保存和反复 compare 切换做基准测试。

## Fragile Areas

**Word HTML/JavaScript 增量预览：**
- Files: `main.py`, `tests/unit/test_word_replace_rules.py`, `tests/unit/test_fstring_safety.py`
- Why fragile: Python f-string 内嵌 CSS/JavaScript，HTML 通过 BeautifulSoup 与 regex fallback 两条路径标记 block；`data-key`、高亮 `<mark>`、左右面板 ready 状态和滚动同步互相依赖，历史上已出现花括号语法崩溃、空白右栏和高亮串位。
- Safe modification: 只更新带 `data-word-block="1"` 的正文容器；不要对全 HTML 做纯文本全局替换；修改后同时运行 Word 规则、f-string、批量替换测试，并在真实 QWebEngineView 中验证首次 compare 和撤回。
- Test coverage: 现有测试偏向字符串/helper 断言，未覆盖完整 GUI WebEngine 生命周期、嵌入图片、不同 Qt/WebEngine 平台行为。

**OCR 坐标换算与混合 PDF 合并：**
- Files: `privacyguard/workers/ocr_worker.py`, `privacyguard/ocr/mixed_pdf.py`, `privacyguard/ocr/text_pdf.py`
- Why fragile: 文本层、图片块 OCR、整页回退、扫描缩放、裁剪偏移和检测框调节共同决定最终 `QRectF`；不同 OCR 返回结构由 `iter_ocr_lines()` 兼容，错误或重复结果可能在合并后产生过宽、错位或重复框。
- Safe modification: 遵循“文本层 -> 图片块 -> 无文本整页回退”的顺序；所有局部框必须在同一处转换到页面坐标；新增逻辑同时覆盖 CJK、英文数字、多个图片块、空文本和重复命中。
- Test coverage: 单元测试覆盖坐标和去重逻辑，但没有真实 RapidOCR 模型、真实混合 PDF、大旋转页面和多 DPI 导出组合。

**线程与退出清理：**
- Files: `main.py`, `privacyguard/workers/ocr_worker.py`, `privacyguard/utils/temp_manager.py`
- Why fragile: 应用退出只等待活动 worker 最多 2 秒；批量 worker、WebEngine、转换子进程和临时资源由不同清理路径管理。`TempFileManager` 以类级实例列表和 `atexit` 兜底，实例生命周期不会主动注销。
- Safe modification: 新增 worker 时统一实现取消、finished、wait、子进程终止和临时目录归属；不要依赖 `__del__` 处理资源；为异常退出、关闭窗口时正在转换和重复打开文件增加测试。
- Test coverage: 有独立稳定性脚本和部分 worker 单元测试，但没有系统性退出竞态测试。

**响应式 UI 与平台差异：**
- Files: `main.py`, `theme.py`, `packaging/windows/config/PrivacyGuard_windows.spec`, `docs/current/V38_UI_REFACTOR_PLAN.md`
- Why fragile: 大量固定高度、DPI 档位、`isHidden()` 判断、Qt sizeHint 和 QWebEngine 字体栈逻辑集中在一个窗口；Windows/macOS 尚未拥有同等的真机截图验收基线。
- Safe modification: 先在目标 DPI/窗口尺寸建立截图基线，再改动单一工作区；保持工具栏显隐与布局刷新幂等，并执行启动、缩放、跨屏、窄窗口和全屏验收。
- Test coverage: 主要是 compileall 和纯逻辑回归，缺少自动 GUI 像素/交互回归。

## Scaling Limits

**大文档 OCR：**
- Current capacity: `OCRWorker.run()` 以 10 页为批次，并在批次间调用 `gc.collect()`；Word 历史记录显示 50+ 页预览可能产生明显延迟。
- Limit: 页面渲染、OCR 模型和 WebEngine DOM 都受单机 CPU/内存限制；没有可验证的页数、图片尺寸或并发上限。
- Scaling path: 引入页级耗时/峰值内存指标，限制单页渲染尺寸和嵌入图片总量，必要时采用可取消的任务队列和磁盘缓存。

**发布包体积与依赖链：**
- Current capacity: PyInstaller spec 收集 NumPy、onnxruntime、RapidOCR、PyQt6 WebEngine、bs4/lxml 及动态库，发布包包含大型原生依赖。
- Limit: 平台 DLL、NumPy 兼容目录、OCR 模型和 WebEngine 资源容易导致包体积大、构建慢或启动失败。
- Scaling path: 固定并验证 Python/依赖矩阵，生成依赖清单和构建 smoke test；避免无必要的 `collect_submodules('numpy')` 全量收集，除非有运行时证据支持。

## Dependencies at Risk

**NumPy / onnxruntime / RapidOCR 原生链：**
- Risk: 当前 `requirements.txt` 使用较新的 NumPy、onnxruntime 和 OpenCV 版本，Windows spec 需要显式收集 `numpy.core`、`numpy._core`、多个 DLL 与 hidden imports；历史上已经出现 `numpy.core._exceptions` 和 `privacyguard.utils.security` 打包导入失败。
- Impact: 开发环境可运行但打包产物启动或 OCR 执行失败，且错误可能只在目标平台出现。
- Migration plan: 建立 Windows/macOS 锁定矩阵和干净环境构建验证；把依赖版本、spec hidden imports 与真实 smoke test 结果作为同一发布门禁，必要时保守固定已验证组合。

**LibreOffice / antiword 系统工具：**
- Risk: `.doc` 支持依赖用户机器上的外部可执行文件；PATH、安装位置、权限和格式兼容性不同。
- Impact: 单文档或批量替换失败，输出文档可能丢失复杂排版；当前 antiword 是文本抽取回退，不等价于保留原格式转换。
- Migration plan: 启动或首次 `.doc` 操作时明确探测能力，报告使用的转换器；为表格、图片、中文文本、嵌入对象和失败回退建立真实样本验收。

## Missing Critical Features

**每文件单独规则映射：**
- Problem: 当前批量 Word worker 对全部输入文件应用同一套会话规则，无法按文件选择规则集。
- Blocks: 复杂批量任务的差异化脱敏和可复用规则模板。
- Files: `main.py`, `tests/unit/test_batch_word_replace.py`, `docs/current/STATUS.md`

**替换来源筛选高亮：**
- Problem: 右侧预览融合规则替换、手动脱敏和 OCR 结果，但尚未提供按 `rule/manual/ocr` 来源筛选高亮的产品能力。
- Blocks: 用户审查不同处理来源、定位误报并进行精细撤回。
- Files: `main.py`, `tests/unit/test_word_replace_rules.py`, `docs/current/STATUS.md`

## Test Coverage Gaps

**完整 GUI 和平台验收：**
- What's not tested: 主窗口启动、拖拽、QWebEngine 双栏、DPI/跨屏、PDF 导出、真实 OCR 模型加载、Windows 安装器和 macOS notarization。
- Files: `main.py`, `packaging/windows/scripts/build_complete.bat`, `packaging/macos/scripts/build_complete.sh`, `tests/`
- Risk: 纯逻辑测试和 `compileall` 通过仍可能存在运行时导入、渲染、DLL 或事件循环问题。
- Priority: High

**真实文档回归：**
- What's not tested: 旋转/加密/超大 PDF、混合 PDF 多图块、复杂 DOCX 表格与嵌入对象、`.doc` 格式保真度和批量部分失败后的资源清理。
- Files: `privacyguard/ocr/mixed_pdf.py`, `privacyguard/workers/ocr_worker.py`, `privacyguard/utils/doc_converter.py`, `tests/samples/`
- Risk: 坐标错误、漏脱敏、重复框、排版损失或临时文件泄漏可能在单元测试之外发生。
- Priority: High

**安全回归：**
- What's not tested: 符号链接、Windows junction/UNC 路径、大小写与驱动器边界、恶意/畸形 DOCX、转换器超时后的子进程残留。
- Files: `privacyguard/utils/security.py`, `privacyguard/utils/doc_converter.py`, `tests/test_path_validation.py`
- Risk: 路径边界绕过或外部转换器资源失控。
- Priority: High

**测试基础设施一致性：**
- What's not tested: `tests/unit/test_stability.py` 是否真正覆盖当前模块实现；独立脚本 `test_fix.py`、`run_test.py`、`simple_test.py` 与主回归的关系和失败门禁。
- Files: `tests/unit/test_stability.py`, `test_fix.py`, `run_test.py`, `simple_test.py`, `tests/scripts/test.sh`
- Risk: 历史测试显示“通过”但没有保护当前运行时路径，增加错误安全感。
- Priority: Medium

---

*Concerns audit: 2026-08-10*
