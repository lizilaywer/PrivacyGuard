# Phase 1: PDF 自动识别身份证号与手机号并真脱敏 - Research

**Researched:** 2026-08-10
**Domain:** PDF 自动 PII 识别（身份证 / 手机号）+ 真脱敏（PyMuPDF add_redact_annot + apply_redactions）+ 反向提取验证
**Confidence:** HIGH（PyMuPDF 真删除 API、GB 11643-1999 算法、MIIT 号段白名单 / MEDIUM（个别号段清单的最新核对仍依赖用户复核）

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** OCR 三路径全纳入 Phase 1 — 文字层（PyMuPDF `page.get_text`）、混合型 PDF 嵌入图片块（`collect_image_block_ocr_hits`）、纯扫描型 PDF 的整页回退 OCR。三个路径汇入同一份 PII 引擎输出。
- **D-02:** 新增 `privacyguard/pii/` 子包作为独立子系统（与 `privacyguard/ocr/` 平级），包含 `engine.py` / `rules.py` / `validators.py` / `hits.py` / `__init__.py` 懒加载入口。引擎无 Qt、无线程、无格式 I/O；apply 阶段由各 PDF 适配器边界处理。
- **D-03:** 新增纯函数 `collect_full_page_ocr_hits(page, recognize_fn, calculate_rect_fn)`，与现有 `collect_text_pdf_hit_boxes` / `collect_image_block_ocr_hits` 保持同一种 dependency-injection 形态（参考 `privacyguard/ocr/mixed_pdf.py:76`）。
- **D-04:** PII 引擎独立维护，**不动** `config.json.default_rules` 中的现有正则，也不修改 `SimpleConfig` / `SettingsDialog` 已有的规则编辑 tab。两条规则集共存：现有 `default_rules` 仍由旧文本层 + 图片块 worker 消费；PII 引擎产出的命中通过新 `page_data[page]["pii"]` 键接入。
- **D-05:** PIIHit 定义为 `dataclass`：`entity_type: str`、`page_offset: int`、`page_length: int`、`page_rect: QRectF`、`confidence_tier: Literal["HIGH","MEDIUM","LOW"]`、`source: Literal["text","image_block","full_page_ocr"]`、`mask_strategy: str`。存进 `page_data[page_num]["pii"]`。
- **D-06:** 字符级 offset 采用「整页文本字符串偏移」（`page_offset` / `page_length`），而不是仅存 `QRectF`。OCR 路径通过 `iter_ocr_lines` + 文本字符串拼接得到；文本层路径直接使用 `page.get_text()` 的字符串索引。
- **D-07:** 默认自动真脱敏：HIGH 档命中直接以红色框显示在原位，用户点「保存」时一同真脱敏（沿用现有 `add_redact_annot + apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` 路径，`main.py:12364-12373`）。
- **D-08:** 新增 `config.json.pii_settings` 段（`engine_enabled / auto_redact / require_confirmation`），SettingsDialog 新增「隐私识别」tab。
- **D-09:** `pii_settings` 改动需同步 `config.json.template` 与 `tests/unit/test_app_config.py`；新增的 SettingsDialog tab 不动现有 4 个 tab 结构。
- **D-10:** PII 引擎内部规则（身份证 / 手机号正则、段号白名单、置信度档位边界）存放在外部 JSON 数据文件 `privacyguard/pii/data/rules.json`，通过 `privacyguard.utils.security.resource_path` 读取。
- **D-11:** 手机号段号白名单在 Phase 1 实施前需要查 MIIT 最新公告交叉验证（166/198/199、190/192/196/197、虚拟运营商段、14X 物联网排除），验证完成后写入 `rules.json`。
- **D-12:** Phase 1 必须新增至少 3 类单元测试：① 身份证 mod-11-2 校验（含大小写 X）与手机号段号白名单；② PII 引擎对合成 PDF 文本的命中 + 档位判定；③ 通过 `pdftotext` / `page.get_text()` 反向提取断言敏感字符串消失。
- **D-13:** 79/79 既有测试基线全部通过，包括 `test_pdf_text_hit_dedup` / `test_mixed_pdf_ocr` / `test_package_imports` / `test_convergence`。
- **D-14:** 反向提取测试使用 `pdftotext`（poppler-utils）或 `fitz.open().get_text()` 二选一；优先 `fitz` 路径以避免在 CI 上额外安装 poppler。

### Claude's Discretion

- PIIHit dataclass 字段顺序与默认值（`confidence_tier` 默认 `"HIGH"` 还是 `"MEDIUM"`，建议 `HIGH` 因 Phase 1 全部走校验位严格路径）。
- `iter_ocr_lines` 与 PII 引擎的对接函数命名（建议 `pii_engine.recognize_lines(text_or_image) -> List[PIIHit]`）。
- `collect_full_page_ocr_hits` 的扫描比例默认值（与现有 `mixed_pdf.py` 对齐，建议 `1.5`）。
- Phase 1 测试 PDF 生成器位置（建议 `tests/e2e/create_pii_test_pdf.py`，与现有 `tests/e2e/create_test_pdf.py` 对齐）。

### Deferred Ideas (OUT OF SCOPE)

- 每文件单独规则映射（PROJECT.md / STATE.md 已明确让位给 Phase 1）
- 批量 Word 替换的来源筛选高亮（属于 Word UI 抛光，归属 Phase 7 或 Phase 8）
- 候选审阅对话框的完整实现（Phase 7 主线；Phase 1 用最小可用确认框承载）
- 识别规则编辑 UI（Phase 8 UX-07）
- 审计报告（JSON）（Phase 8 OPS-01）
- 完整行政区划词典 ~70 万条（Phase 6 ADV-01）
- 本地 NER 深度学习模型（PROJECT.md 明确 Out of Scope）
- v38 UI 抛光（PROJECT.md 明确让位给本轮识别准确率）

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENGINE-01 | 文档打开后自动扫描全文并输出敏感项候选列表，无需关键词 | §Standard Stack / §Architecture Patterns：`privacyguard/pii/engine.py` 在 `_ModularOCRWorker.run` 现有 OCR 后追加 `Engine.detect(unit)` 调用；触发时机遵循 D-07 |
| ENGINE-02 | 每条识别结果携带实体类型、精确字符起止位置、置信度档位、来源与建议掩码 | §Standard Stack / §Code Examples：`PIIHit` dataclass 字段顺序在 D-05 中锁定；`page_offset / page_length / confidence_tier / source / mask_strategy` 全字段由引擎在 detect 阶段填齐 |
| ENGINE-03 | HIGH / MEDIUM / LOW 三档评级 | §Architecture Patterns §7：`confidence.py` 把 `validator_passed`（mod-11-2 通过、段号白名单命中）映射为 HIGH；格式正则匹配但无校验位的为 MEDIUM；其余为 LOW |
| ENGINE-04 | 同一实体的多次出现应用一致掩码 | §Don't Hand-Roll：引擎内部维护 `(entity_type, normalized_text)` 哈希表，确保 `suggested_mask` 字符串对同 normalized 值稳定 |
| ENGINE-05 | 匹配前统一归一化输入（全角转半角、剔除空格与分隔符），并把匹配位置映射回原始偏移 | §Code Examples §Normalization：实现 `normalize_digits`（全角→半角 + 移除 `- / 空格`）；offset 通过原始字符串的"段长度累加"回算 |
| ENGINE-06 | 识别被换行 / 分栏 / 单元格边界切断的实体 | §Common Pitfalls §6：现有 `collect_text_pdf_hit_boxes` 已合并跨块 hit；OCR 路径通过 `iter_ocr_lines` 拼接后再 `re.finditer`；测试用例覆盖跨行身份证样本 |
| ENGINE-07 | 正则匹配执行超时保护 | §Common Pitfalls §10：Python `re` 模块**没有**内置 `timeout` 参数（已在 Python 3.12 本机验证 `inspect.signature(re.finditer)` 不含 `timeout`）。Phase 1 采用两种替代：① 在 worker 线程里 `threading.Timer` + `threading.Event` 软超时；② 限制单页文本长度（截断到 N 字符）；③ 简单写法：依赖 PyMuPDF worker 自身的 `isInterruptionRequested()` 中断检查 |
| ENGINE-08 | 识别引擎为纯本地执行，运行期无任何网络请求 | §Common Pitfalls §9 / §Validation Architecture：测试 `tests/unit/test_pii_offline.py` 通过 monkey-patch `socket.socket` 拦截所有出站连接，扫描整个 500 页文档后断言 `socket.socket` 调用次数为 0 |
| NUM-01 | 18 位与 15 位居民身份证号，GB 11643 mod-11-2 校验 | §Standard Stack / §Code Examples：自研 `privacyguard/pii/validators/id_card.py` 实现 18 位权重 `[7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]` + 校验码表 `[1,0,X,9,8,7,6,5,4,3,2]`；15 位旧号升级为 18 位后再校验（D-11 升级算法见 §Architecture Patterns §3.3） |
| NUM-02 | 末位大写 X 与 OCR 小写 x | §Code Examples §ID validator：`validate_18` 对末位做 `s.upper()` 归一化；`PIIHit.mask_strategy` 仍输出原始大小写，避免改变用户原文 |
| NUM-03 | 中国大陆手机号，依据号段白名单，排除 14X 物联网 / 卫星 | §Standard Stack / §Code Examples：`is_mobile_segment(prefix)` 函数 + 双白名单（个人号段 110-199 减去 14X IoT 与卫星段号） |
| FMT-01 | PDF 文字层与 OCR 路径接入识别引擎 | §Architecture Patterns：保留 `collect_text_pdf_hit_boxes` / `collect_image_block_ocr_hits` / `collect_full_page_ocr_hits` 三个纯函数；在 `_ModularOCRWorker.run` 的现有 OCR 步骤之后追加 `Engine.detect(unit)`；命中并入 `page_data[page]["pii"]`（不替换 `ocr` 键） |
| SAFE-01 | PDF 真删除（PyMuPDF add_redact_annot + apply_redactions） | §Standard Stack / §Code Examples：`PdfAdapter.apply_redactions` 沿用 `main.py:12354-12385` 的完整模式：`add_redact_annot(rect)` + `set_colors(stroke=fill, fill=fill)` + `apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)` + 后续 `delete_annot` + `doc.save(garbage=4, deflate=True, clean=True)`。**严格禁止** `draw_rect` 替代 |
| SAFE-02 | 每种格式的脱敏实现都有反向提取测试 | §Standard Stack / §Validation Architecture：新增 `tests/unit/test_pdf_pii_redaction.py` 用 `fitz.open(out).get_text()` 断言脱敏区原文不存在；测试必须使用 `insert_text` 生成的合成 PDF（Faker 生成器 + Luhn 校验循环，见 §TDD Specifics） |
| OPS-03 | 识别引擎与词典数据保持懒加载，包导入期不初始化 OCR 引擎 | §Architecture Patterns §9：参照 `privacyguard/workers/__init__.py:15` 的 `_LAZY_IMPORTS` + `__getattr__` 模式；`privacyguard/pii/__init__.py` 仅暴露 `__version__` 与导出表；具体 `engine.py` / `validators.py` 在 `__getattr__` 中按需 import |
| OPS-07 | 79/79 测试基线在改动后保持通过 | §Validation Architecture：CLAUDE.md 列出的 10 个 unittest 模块必须在 Wave 0 后仍然 100% 通过；CI 报告作为 Phase 1 完成门禁 |

---

## Summary

Phase 1 把"打开文档就自动列出所有敏感项"这条核心价值首次落到 PDF 格式。技术上分三层：(1) **引擎层** `privacyguard/pii/` 自研纯 Python 检测器，复用现有 `collect_text_pdf_hit_boxes` / `collect_image_block_ocr_hits` 与新增 `collect_full_page_ocr_hits` 三个 OCR 路径产出，命中以 `page_data[page]["pii"]: List[PIIHit]` 接入现有数据契约（D-04 / D-05 / D-06）；(2) **脱敏层** `privacyguard/pii/pdf_adapter.py` 沿用 `main.py:12354-12385` 既有的 `add_redact_annot + apply_redactions(images=PDF_REDACT_IMAGE_PIXELS) + garbage=4 + deflate=True + clean=True` 完整模式，**禁止**任何形式的 `draw_rect` 假脱敏；(3) **校验层** 反向提取测试用 `fitz.open(out).get_text()` 断言脱敏区敏感字符串彻底消失（SAFE-01/02）。

最高风险是假脱敏（黑框覆盖但底层文本仍可复制粘贴），规避路径已有：PyMuPDF `apply_redactions` 默认 `text=True` 会从内容流删除文字对象，配合 `images=PDF_REDACT_IMAGE_PIXELS` 处理扫描型 PDF 内的嵌入图片像素，配合 `garbage=4 + deflate=True + clean=True` 移除任何残留引用。次高风险是 PIIHit dataclass 与 `page_data` 字典结构漂移（v37.7.6 已收敛），规避路径已锁定字段顺序与命名（D-05）。零网络（OPS-07）通过 `socket.socket` monkey-patch 测试守护。500 页 UI 响应（Success Criteria #4）通过把 PII 检测追加到 `_ModularOCRWorker.run` 现有线程循环、并按页 `progress_signal` / `isInterruptionRequested()` 实现。

**Primary recommendation:** 严格沿用 `main.py:12354-12385` 的 PyMuPDF 真删除 API（已生产验证的 `add_redact_annot` + `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` + `delete_annot` 清理），新代码不发明"更快更短的写法"。新增 `privacyguard/pii/` 子包保持纯 Python、无 Qt 依赖、`__getattr__` 懒加载三件事。

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 校验位算法（GB 11643 mod-11-2、段号白名单） | `privacyguard/pii/validators/`（纯 Python 库） | — | 标准公开算法，无格式 / 无 Qt 依赖；必须可独立单元测试 |
| 正则引擎（身份证 / 手机号） | `privacyguard/pii/engine.py` | — | 同上；`re.compile` 一次性、worker 多次复用 |
| PIIHit dataclass | `privacyguard/pii/hits.py` | — | 跨格式共享结构（PDF → Word / Excel / Image 时复用） |
| PDF 文字层命中收集 | `privacyguard/ocr/text_pdf.py`（已有） | `collect_text_pdf_hit_boxes` 传入 `pii_engine` 而非 `patterns` | 不破坏 cp23 坐标换算；D-03 要求保持 dependency-injection 形态 |
| PDF 图片块 OCR 命中 | `privacyguard/ocr/mixed_pdf.py`（已有） | `collect_image_block_ocr_hits` 同样改为接受 PII 引擎 | 同上 |
| 纯扫描型 PDF 整页 OCR 回退 | 新增 `collect_full_page_ocr_hits`（在 `privacyguard/ocr/` 或 `privacyguard/pii/`） | — | D-03 锁定为独立纯函数；D-01 三个 OCR 路径必须全开 |
| 脱敏 apply 阶段 | `privacyguard/pii/pdf_adapter.py`（新增） | 沿用 `main.py:12354-12385` 现有 PyMuPDF 调用 | PyMuPDF 真删除不能由 `engine.py` 承担（format-aware） |
| Worker 线程编排 | `_ModularOCRWorker.run`（已存在） | 追加 `Engine.detect(unit)` 调用，不开新线程 | 复用现有 `page_result_signal / progress_signal / finished_signal / error_signal` 信号契约；OPS-03 守住单线程 |
| MainWindow 状态扩展 | `main.py:4908` (`self.page_data` init) | `pii: []` 默认键 | D-04 锁定为"现有 dict 加新键"模式 |
| Settings UI（"5 隐私识别" tab） | `main.py:1008` SettingsDialog | 复用 `settingsSectionCard` 样式 | D-08 / D-09 / UI-SPEC §SettingsDialog |
| 真脱敏写盘 | `main.py:12354` save loop | 把 `pii_list` 并入 `ocr_list + manual_list` | UI-SPEC 锁定 Phase 1 HIGH 自动真脱敏 |
| 反向提取测试 | `tests/unit/test_pdf_pii_redaction.py` | `fitz.open(...).get_text()` | D-14 优先 `fitz` 路径 |
| 懒加载契约 | `privacyguard/pii/__init__.py` + `privacyguard/workers/__init__.py` 的 `_LAZY_IMPORTS` | `privacyguard/__init__.py:61` 追加 PII 导出 | OPS-03 + cp30 历史教训 |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `PyMuPDF` (`fitz`) | `==1.27.1`（已固定） | PDF 真脱敏：`add_redact_annot` + `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` + `garbage=4` | 业界唯一能在内容流层真删除 PDF 文字的纯 Python 库；现有 `main.py:12354-12385` 已验证生产可用 |
| `re` (Python stdlib) | 3.12 | 身份证 / 手机号正则匹配 | 内置；无原生 `timeout`（详见 §Common Pitfalls §10） |
| `dataclasses` (stdlib) | 3.12 | `PIIHit`、`DocumentLocation` | 冻结 dataclass 便于跨线程 `asdict()` 序列化 |
| `enum` (`Literal`) | 3.12 | `ConfidenceTier`、`DocKind`、`Source` | 类型字面量在 Phase 2 跨格式扩展时复用 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `Faker` | 可选（若 `requirements.txt` 引入） | 生成测试用合成 18 位身份证号；不直接用 `Faker.ssn()`，需包一层 mod-11-2 生成循环 | 仅在 `tests/fixtures/fake_pii.py` 使用；不入运行时 |
| `privacyguard.utils.security.resource_path` | 已有 | 读取 `privacyguard/pii/data/rules.json` | PyInstaller 打包时走 `sys._MEIPASS`；开发态走 `os.path.abspath(".")` |
| `QMutex` | PyQt6 6.10.2 | `_pii_data_lock` 保护 `page_data` 写入 | 与现有 `_word_data_lock` 对齐 |
| `QSettings("PrivacyGuard", "App")` | PyQt6 | `pii_settings` 持久化 | 与现有 `SimpleConfig` 路径一致；不切换到 `ConfigManager` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `add_redact_annot + apply_redactions` | `page.draw_rect(fill=(0,0,0))` | **禁止**——这是 PITFALLS §1 的行业头号灾难，黑框覆盖但 `pdftotext` 仍可还原原文 |
| `re.finditer(..., timeout=0.5)`（据称 Python 3.11+ 内置） | 实际**不存在**——Python `re` 模块**没有** `timeout` 参数（已在本机 Python 3.12 用 `inspect.signature(re.finditer)` 验证：`(pattern, string, flags=0)`） | 退而求其次：(a) `threading.Timer` + `Event` 在 worker 线程里软超时；(b) 截断单页文本到 N 字符；(c) 复用 worker 自身的 `isInterruptionRequested()` |
| `id-validator` PyPI 包 | 自研 `validators/id_card.py` (~30 行) | `id-validator` 单维护者、弱类型、节奏慢；自研版本完全可控、可测试、不增加运行时依赖 |
| `presidio-analyzer` | 自研引擎 | Presidio 拖入 spaCy + `en_core_web_lg` 模型（~900 MB），中文支持薄弱；项目 `OUT OF SCOPE.md` 已明令排除 |
| `pdftotext`（poppler-utils）反向提取 | `fitz.open(out).get_text()` | D-14 优先 `fitz` 路径：避免 CI 额外装 poppler；`pdftotext` 仅作为人工 / 备用验证 |
| `rapidocr_onnxruntime` 在 worker 顶层 import | import 移入函数体内 | OPS-03 + cp30 教训；保持现有 `privacyguard/ocr/rapidocr.py` 模式 |

**Installation:**
无新增 PyPI 依赖。所有逻辑在 `privacyguard/pii/` 子包内实现。

**Version verification:**
```
pip show PyMuPDF==1.27.1    # 现有固定
python3 -c "import sys; assert sys.version_info >= (3, 11)"  # stdlib 行为
```
- Python `re.finditer` 在 3.11、3.12、3.13 均**不**带 `timeout` 参数；任何声称"Python 3.11+ 内置正则超时"的资料都应被质疑（详见 §Common Pitfalls §10）

---

## Package Legitimacy Audit

> Phase 1 不新增 PyPI 依赖；以下审计用于 Phase 2+ 预留。

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| 现有 `PyMuPDF==1.27.1` | PyPI | 稳定 | n/a | github.com/pymupdf/PyMuPDF | OK | Approved（项目已固定） |
| 现有 `rapidocr-onnxruntime==1.2.3` | PyPI | 稳定 | n/a | github.com/RapidAI/RapidOCR | OK | Approved（现有） |

**Packages removed due to [SLOP] verdict:** 无（Phase 1 无新增依赖）

**Packages flagged as suspicious [SUS]:** 无

---

## Architecture Patterns

### System Architecture Diagram

```
                              ┌────────────────────────────────────────────┐
                              │  PyQt6 Main Thread (`main.py` ~12.6k LOC)  │
                              │                                            │
  drag/drop / Open menu       │   ▼                                        │
  ────────────────── ──      │  ┌─────────────────────────────────────┐  │
       │                     │  │  MainWindow (`main.py:4885`)         │  │
       ▼                     │  │  ├ self.page_data[i] = {             │  │
  ┌──────────┐               │  │  │     'ocr':    [QRectF, ...],      │  │
  │  File    │               │  │  │     'manual': [QRectF, ...],      │  │
  │  open    │────open_pdf──▶│  │  │     'pii':    [PIIHit, ...]   ◀────┼── D-04 / D-05
  └──────────┘               │  │  │   }                                 │  │
                              │  │  ├ self._pii_data_lock = QMutex()     │  │
                              │  │  ├ self.active_worker = OCRWorker(...) │  │
                              │  │  ├ self._pii_settings = SimpleConfig  │  │
                              │  │  │     .pii_settings                  │  │
                              │  │  └ SettingsDialog tab "5 隐私识别"    │  │
                              │  └──────────┬──────────────────────────┘  │
                              │             │ page_result_signal            │
                              │             ▼                                │
                              │  ┌─────────────────────────────────────┐  │
                              │  │  _ModularOCRWorker (QThread)         │  │
                              │  │  privacyguard/workers/ocr_worker.py  │  │
                              │  │  ──────────────────────────────────  │  │
                              │  │  for i in pages:                     │  │
                              │  │    page_text = page.get_text()       │  │
                              │  │    # ① 现有 OCR 路径                │  │
                              │  │    hits = collect_text_pdf_hit_boxes(│  │
                              │  │      page, all_patterns,             │  │
                              │  │      page_text=page_text)            │  │
                              │  │    if no text → 纯扫描 fallback     │  │
                              │  │    hits += collect_full_page_ocr_hits│  │
                              │  │      (page, recognize_fn,            │  │
                              │  │       calculate_rect_fn,             │  │
                              │  │       clip_to_page_rect_fn)          │  │
                              │  │    hits += collect_image_block_      │  │
                              │  │      ocr_hits(...)                   │  │
                              │  │    self.page_result_signal.emit(i,   │  │
                              │  │       rects)                         │  │
                              │  │                                     │  │
                              │  │    # ② 新增 PII 检测                │  │
                              │  │    pii_hits = pii_engine.detect(     │  │
                              │  │      unit_for(page, page_text))      │  │
                              │  │    # append to page_data[i]['pii']   │  │
                              │  │    # (via _on_ocr_page_result slot)  │  │
                              │  │    self.pii_signal.emit(i, pii_hits) │  │
                              │  └─────────────────────────────────────┘  │
                              │             │                              │
                              └─────────────┼──────────────────────────────┘
                                            │
                                  ┌─────────▼──────────┐
                                  │ privacyguard/pii/  │  ◀── 纯 Python, 无 Qt
                                  │ ────────────────  │
                                  │  hits.py          │  PIIHit / DocumentLocation
                                  │  validators/      │  id_card.py / phone_segment.py
                                  │  engine.py        │  pipeline orchestrator
                                  │  regex_patterns.py│  ID / phone compiled regex
                                  │  confidence.py    │  HIGH / MEDIUM / LOW 映射
                                  │  mask.py          │  partial masking per type
                                  │  overlap.py       │  dedup + conflict resolve
                                  │  normalize.py     │  全角→半角 + 跨行拼接
                                  │  data/rules.json  │  段号白名单 + 算法常量
                                  │  __init__.py     │  __getattr__ 懒加载
                                  └─────────┬──────────┘
                                            │
                                            ▼
                                  ┌─────────────────────┐
                                  │ privacyguard/       │
                                  │ pii/pdf_adapter.py  │  ◀── apply 阶段
                                  │ ──────────────────  │
                                  │ apply_redactions(   │
                                  │   pdf_in,           │
                                  │   page_rects,       │  fitz.Rect[] from PIIHit.page_rect
                                  │   pdf_out):         │
                                  │   doc = fitz.open() │
                                  │   for p in pages:   │
                                  │     for r in rects: │
                                  │       a = p.add_    │
                                  │        redact_annot(│
                                  │          rect=r)    │
                                  │       a.set_colors( │
                                  │         stroke=fill,│
                                  │         fill=fill)  │
                                  │     p.apply_       │
                                  │      redactions(   │
                                  │        images=     │
                                  │         PDF_REDACT_ │
                                  │         IMAGE_     │
                                  │         PIXELS)    │  ◀── 关键！销毁图像像素
                                  │     delete annots  │
                                  │   doc.save(        │
                                  │     garbage=4,     │  ◀── 移除残留对象
                                  │     deflate=True,  │
                                  │     clean=True)    │
                                  └─────────────────────┘
                                            │
                                            ▼
                                  ┌─────────────────────┐
                                  │ tests/unit/         │
                                  │ test_pdf_pii_       │  SAFE-02 反向提取
                                  │   redaction.py      │  fitz.open(out).get_text()
                                  │                     │  断言脱敏区敏感字串消失
                                  └─────────────────────┘
```

### Recommended Project Structure

```
privacyguard/pii/                       # NEW (D-02)
├── __init__.py                         # 懒加载 _LAZY_IMPORTS + re-export
├── hits.py                             # PIIHit / DocumentLocation dataclasses (D-05)
├── validators/
│   ├── __init__.py                     # 导出 validate_18_id / is_mobile_segment / upgrade_15_to_18
│   ├── id_card.py                      # GB 11643 mod-11-2 + 15→18 升级 (NUM-01 / NUM-02)
│   └── phone_segment.py                # 中国大陆号段白名单 + 14X 排除 (NUM-03)
├── engine.py                           # PIIEngine.detect(unit) → List[PIIHit]
├── regex_patterns.py                   # 编译好的 18/15 位身份证、11 位手机号正则
├── confidence.py                       # HIGH/MEDIUM/LOW 三档映射
├── mask.py                             # partial_mask(entity_type, text) → masked (D-05 mask_strategy 字段)
├── overlap.py                          # 跨 recognizer / 跨字符 span 去重
├── normalize.py                        # 全角→半角 + 跨行拼接 + offset 回算 (ENGINE-05)
├── data/
│   └── rules.json                      # 段号白名单 + 算法常量 (D-10 / D-11)
└── pdf_adapter.py                      # apply_redactions 包装 (SAFE-01)

tests/
├── unit/
│   ├── test_pii_validators.py          # NUM-01/02/03 (D-12 ①)
│   ├── test_pii_engine.py              # 合成文本命中 + 档位判定 (D-12 ②)
│   ├── test_pdf_pii_redaction.py       # 反向提取断言 (D-12 ③, SAFE-01/02)
│   ├── test_pii_offline.py             # socket.socket monkey-patch 零网络 (OPS-07, ENGINE-08)
│   └── test_pdf_pii_pipeline.py        # 端到端：合成 PDF → 检测 → apply → 反向提取
├── e2e/
│   └── create_pii_test_pdf.py          # Faker 合成 PII + PyMuPDF insert_text 生成 PDF (D-12)
└── fixtures/
    └── fake_pii.py                     # fake_id_card() / fake_phone() (OPS-05)

config.json.template                    # 新增 pii_settings 段 (D-09)
config.json                             # 新增 pii_settings 段 (D-09)

tests/unit/test_app_config.py           # 追加 pii_settings 字段默认值断言 (D-09)
tests/unit/test_convergence.py          # 断言 main.py 不在顶层 import privacyguard.pii.*
tests/unit/test_package_imports.py        # 断言 import privacyguard 不触发 RapidOCR / pii.* eager load
```

### Pattern 1: Dependency-Injection OCR 命中收集（沿用现有 `mixed_pdf.py` 范本）

**What:** `collect_full_page_ocr_hits` 与现有 `collect_text_pdf_hit_boxes` / `collect_image_block_ocr_hits` 保持同一形状（`recognize_fn` / `calculate_rect_fn` / `clip_to_page_rect_fn` 注入），使 worker 之外可纯函数单测。

**When to use:** 任何新增 PDF OCR 命中收集函数都必须沿用此形态（D-03）。

**Example (草案):**
```python
# privacyguard/ocr/full_page_ocr.py (NEW)
import cv2
import fitz
import numpy as np


def render_full_page_to_bgr(page, scan_scale):
    """整页渲染为 BGR。"""
    pix = page.get_pixmap(matrix=fitz.Matrix(scan_scale, scan_scale), alpha=False)
    return cv2.imdecode(np.frombuffer(pix.tobytes("png"), dtype=np.uint8), cv2.IMREAD_COLOR)


def collect_full_page_ocr_hits(
    page,
    scan_scale,
    recognize_fn,
    calculate_rect_fn,
    preprocess_fn=None,
    render_fn=None,
):
    """纯扫描型 PDF 整页 OCR 命中收集（D-03 新增纯函数）。"""
    render = render_fn or render_full_page_to_bgr
    try:
        img_bgr = render(page, scan_scale)
    except Exception:
        return []

    if img_bgr is None or getattr(img_bgr, "size", 0) == 0:
        return []

    scan_img = preprocess_fn(img_bgr) if preprocess_fn else img_bgr
    try:
        ocr_results = recognize_fn(scan_img)
    except Exception:
        return []

    page_rect = page.rect
    hits = []
    for box, text in iter_ocr_lines(ocr_results):
        if not text:
            continue
        local_rect = calculate_rect_fn(box, text, (0, len(text)), scan_img)
        if local_rect is None:
            continue
        # OCR 局部框 / 扫描缩放 → 页面坐标
        sx = (page_rect.x1 - page_rect.x0) / scan_img.shape[1]
        sy = (page_rect.y1 - page_rect.y0) / scan_img.shape[0]
        page_x0 = page_rect.x0 + local_rect[0] * sx
        page_y0 = page_rect.y0 + local_rect[1] * sy
        page_x1 = page_rect.x0 + (local_rect[0] + local_rect[2]) * sx
        page_y1 = page_rect.y0 + (local_rect[1] + local_rect[3]) * sy
        hits.append((page_x0, page_y0, page_x1 - page_x0, page_y1 - page_y0))
    return hits
```

### Pattern 2: PIIEngine.detect(unit) 与现有 OCR worker 集成

**What:** 在 `_ModularOCRWorker.run` 的现有 OCR 步骤之后（不替换），追加 `pii_engine.detect(TextUnit(page, page_text, location))` 调用；命中通过新 `pii_signal` 发送，由 `MainWindow._on_pii_page_result` slot 写入 `self.page_data[i]["pii"]`。

**When to use:** 任何"自动识别"通道在 Phase 1 都走此形态；Phase 2+ 的 Word / Excel / Image 同形复用。

**Example:**
```python
# privacyguard/workers/ocr_worker.py (扩展, 不替换)
from privacyguard.pii import PIIEngine, PIIHit
from privacyguard.pii.pdf_adapter import build_text_unit_from_page

class OCRWorker(QThread):
    # ... 既有 signals ...
    pii_signal = pyqtSignal(int, list)   # NEW: (page_idx, PIIHit as dict[])
    # ...

    def _detect_pii_for_page(self, page, page_idx, page_text):
        """Phase 1 新增：在 OCR 步骤之后调用 PII 引擎。"""
        if not self._pii_engine or not page_text.strip():
            return []
        unit = build_text_unit_from_page(page, page_idx, page_text)
        hits = self._pii_engine.detect(unit)
        # ENGINE-05 归一化 + offset 已经在 engine.py 内完成
        return [dataclasses.asdict(h) for h in hits]

    def run(self):
        # ... 现有循环 ...
        for i in range(batch_start, batch_end):
            if self.isInterruptionRequested():
                break
            page = doc[i]
            page_text = page.get_text()
            # ... 现有 OCR 步骤（保持不变）...
            self.page_result_signal.emit(i, rects)

            # NEW: 追加 PII 检测
            pii_hits = self._detect_pii_for_page(page, i, page_text)
            if pii_hits:
                self.pii_signal.emit(i, pii_hits)
            # ...
```

### Pattern 3: 真脱敏 apply（沿用 `main.py:12354-12385` 既有模式）

**What:** `privacyguard/pii/pdf_adapter.py::apply_redactions` 把 `PIIHit.page_rect` 列表写入 PDF，**严格使用** PyMuPDF 真删除 API，**禁止** `draw_rect`。

**Example:**
```python
# privacyguard/pii/pdf_adapter.py
import fitz
from typing import List, Tuple


def collect_pii_rects(page_data_for_doc) -> List[Tuple[int, fitz.Rect]]:
    """从 page_data 中提取 (page_idx, fitz.Rect) 列表。"""
    rects = []
    for page_idx, data in page_data_for_doc.items():
        for hit in data.get("pii", []):
            r = hit["page_rect"]
            # hit["page_rect"] 存为 (x, y, w, h)，与 QRectF 兼容
            rects.append((page_idx, fitz.Rect(r[0], r[1], r[0] + r[2], r[1] + r[3])))
    return rects


def apply_pii_redactions(pdf_in: str, pdf_out: str, rects_per_page: dict,
                          fill_color=(0, 0, 0)):
    """PyMuPDF 真删除：add_redact_annot + apply_redactions(IMAGE_PIXELS) + garbage=4。

    与 main.py:12354-12385 现有 save loop 模式完全一致；Phase 1 仅把
    pii_list 并入 ocr_list + manual_list，不修改 main.py 的循环结构。
    """
    doc = fitz.open(pdf_in)
    try:
        for i in range(len(doc)):
            page = doc[i]
            for r in rects_per_page.get(i, []):
                annot = page.add_redact_annot(r)
                annot.set_colors(stroke=fill_color, fill=fill_color)
                annot.update()
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
            # 防止 PDF 编辑器恢复（沿用 cp23 / cp30 既有做法）
            for annot in page.annots() or []:
                page.delete_annot(annot)
        doc.save(pdf_out, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()
```

### Anti-Patterns to Avoid

- **假脱敏（`page.draw_rect(fill=(0,0,0))`）：** PITFALLS §1 头号灾难。`draw_rect` 只在内容流顶层画矩形，文字对象仍存在，`pdftotext` / `page.get_text()` 仍可读出。Facebook 2022、UK ICO 2021、Ghislaine Maxwell 2021 均有真实事故。
- **顶层 import RapidOCR / openpyxl：** 破坏 OPS-03 懒加载约束；cp30 修复过 `privacyguard.utils.security` 导入失败。新增 `privacyguard/pii/image_ocr.py` 等模块时必须把 `from rapidocr_onnxruntime import RapidOCR` 放函数体内。
- **`main.py` 写 PII 检测逻辑：** 违反 v37.7.6 收敛原则；D-04 明确禁止。所有 PII 逻辑必须在 `privacyguard/pii/`。
- **在 `page_data` 之外新建 `pii_hits` dict：** 违反 D-04；UI 与 apply 必须共享同一数据契约。
- **跨文档 / 跨页一致性问题（Phase 2 才相关）：** 同一身份证在不同页应保持同 `suggested_mask`；本次 Phase 1 单文件场景下只需保证单页内一致（`overlap.py` 内 `(entity_type, normalized)` 哈希）。
- **替换成 `1[3-9]\d{9}` 后声称"覆盖所有 2025 号段"：** 必须显式排除 14X 物联网段（见 §Standard Stack / §Code Examples），否则 `14001234567` 这种物联网号会被错识为个人手机号（PITFALLS §4）。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 身份证校验位 | 自实现 ISO 7064 mod-11-2 算法 | `privacyguard/pii/validators/id_card.py::validate_18`（约 30 行） | 已有 GB 11643 公开标准 + 多源测试向量；外加 `id-validator` PyPI 包（单维护者）；自研可完全测试 + 不增加依赖 |
| 中国大陆手机号段判定 | 静态 `1[3-9]\d{9}` 正则 | `privacyguard/pii/validators/phone_segment.py::is_mobile_segment(prefix)` + `rules.json` 数据文件 | 必须排除 14X 物联网 / 1740/1749 卫星；PITFALLS §4 |
| PDF 真脱敏 | `draw_rect` 或 `add_highlight` | PyMuPDF `add_redact_annot + apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` | `draw_rect` 是行业头号失败模式；PyMuPDF 真删除 API 已是事实标准 |
| 跨行实体识别 | 简单 `re.finditer(text)` | `privacyguard/pii/normalize.py::flatten_for_match(text)` + offset 回算 | PITFALLS §7；身份证跨行 / 手机号跨 cell 都会漏判 |
| 全角 / OCR 字符归一化 | 内联 `text.translate` | `normalize.normalize_digits(text)` 公共函数 | 全角数字 + 0/O/1/l 混淆，PITFALLS §6 |
| 反向提取验证 | 单元测试靠肉眼 | `fitz.open(out).get_text("text")` 后断言字符串不存在 | D-14 优先；`pdftotext` 仅作人工验证备用 |
| Worker 线程编排 | 在 `main.py` 直接 `QThread` | `_ModularOCRWorker.run` 扩展 | Bypassing 绕开 `box_adjust_ratio` 注入；D-04 收敛原则 |
| 测试用 18 位身份证 | `Faker().ssn()` | `tests/fixtures/fake_pii.py::fake_id_card()`（Faker + mod-11-2 校验循环） | Faker 默认 `ssn()` 不会通过 mod-11-2；OPS-05 禁止仓库夹带真实数据 |
| 词典 / 区划码（Phase 6 才用） | 打包完整 70 万条 | Phase 1 不引入词典；`rules.json` 仅含段号白名单 + 算法常量 | 行政区划词典打包策略属于 Phase 6；详见 `.planning/research/ARCHITECTURE.md` |

**Key insight:** Phase 1 的核心收益是"识别 + 真脱敏 + 反向验证"三件套，**不需要** NER 模型、不需要大型词典、不需要云端 API。所有自研代码量控制在 ~500 行（含注释、单元测试、文档）。任何"先打地基再说"的扩张倾向都应被推迟到 Phase 2+。

---

## Common Pitfalls

### Pitfall 1: 假脱敏（Fake Redaction）— 头号灾难

**What goes wrong:** `page.draw_rect(rect, fill=(0,0,0))` 或 `add_highlight` 替换为 `apply_redactions` 后忘了调用 `apply_redactions()`。黑框覆盖但底层文本在 PDF 内容流里仍可被 `pdftotext` / `page.get_text()` / 复制粘贴还原。

**Why it happens:** 工程师把"视觉遮蔽"等同于"内容移除"；PDF 规范允许任意图层叠加。

**How to avoid:**
- 严格沿用 `main.py:12354-12385` 既有模式：`add_redact_annot` + `set_colors(stroke=fill, fill=fill)` + `apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)` + `delete_annot` + `doc.save(garbage=4, deflate=True, clean=True)`
- 单元测试 `tests/unit/test_pdf_pii_redaction.py` 用 `fitz.open(out).get_text()` 反向提取，断言脱敏区敏感字符串**彻底不存在**
- Code Review 红线：在 `pdf_adapter.py` 中出现 `draw_rect / fill=` / `add_highlight` 字样立即拒绝

**Warning signs:**
- 单元测试只验证"画了框"而不验证"提取不到"
- 代码注释出现"用黑色矩形覆盖"
- 任何 `page.insert_text` 在脱敏上下文里出现

**Phase to address:** Phase 1（SAFE-01 / SAFE-02 直接绑定到本 phase）

### Pitfall 2: PIIHit dataclass 与 `page_data` 字典契约漂移

**What goes wrong:** PII 引擎把命中写进新的 `self.pii_hits` 全局列表，`main.py` UI 与 apply 仍读 `page_data[i]["pii"]`，两边数据分裂。

**Why it happens:** 重构时引入平行数据结构；违反 v37.7.6 收敛原则。

**How to avoid:**
- D-04 / D-05 锁定：`page_data[page_num]["pii"]: List[PIIHit]`（与现有 `"ocr" / "manual"` 键并列）
- `tests/unit/test_convergence.py` 追加断言：`main.py` 不在顶层 import `privacyguard.pii.*`
- PIIHit 字段顺序与命名在 D-05 锁定后不可重命名

**Warning signs:** `self.pii_hits = []` 在 `MainWindow` 出现；`page_data` 与并行 dict 共存

**Phase to address:** Phase 1

### Pitfall 3: 身份证校验位算法错误 + X 大小写陷阱

**What goes wrong:**
1. 权重数组写错：`WEIGHTS` 必须 `[7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]`
2. 校验码表写错：`MAPPING` 必须 `['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']`（remainder `0` → `'1'`，`1` → `'0'`，`2` → `'X'`，`10` → `'2'`，**反向 parity**）
3. OCR 输出小写 `x` 被判负

**Why it happens:** ISO 7064 mod-11-2 的映射表反向 parity 容易看错；OCR 字符归一化缺失

**How to avoid:**
```python
# privacyguard/pii/validators/id_card.py
WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
MAPPING = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')

def compute_check_digit(body17: str) -> str:
    total = sum(int(body17[i]) * WEIGHTS[i] for i in range(17))
    return MAPPING[total % 11]

def validate_18(id_str: str) -> bool:
    """NUM-01 / NUM-02 验证函数。"""
    if not id_str or len(id_str) != 18:
        return False
    if not id_str[:17].isdigit():
        return False
    last = id_str[17]
    if last not in '0123456789Xx':
        return False
    # OCR 小写 x 归一化（NUM-02）
    expected = compute_check_digit(id_str[:17])
    return last.upper() == expected

def upgrade_15_to_18(id15: str) -> str:
    """15 位旧号升级为 18 位（NUM-01 子路径）。"""
    if not id15 or len(id15) != 15 or not id15.isdigit():
        return ''
    body17 = id15[:6] + '19' + id15[6:]  # 加上世纪 '19'
    return body17 + compute_check_digit(body17)

def validate_15(id_str: str) -> bool:
    """15 位身份证验证（无 mod-11-2，按 D-11 升级后校验）。"""
    upgraded = upgrade_15_to_18(id_str)
    if not upgraded:
        return False
    # 再校验 18 位（生日 / 区划码 sanity 由 ENGINE-06 后续 anchor 处理）
    return validate_18(upgraded)
```

**Warning signs:** 单元测试只测了 1-2 个样本；没有测 X / 小写 x；mod 映射表错位（`MAPPING[0]` 不是 `'1'`）

**Phase to address:** Phase 1（D-12 ① 单元测试 ≥ 20 条样本）

### Pitfall 4: 14X 物联网段被错识为个人手机号

**What goes wrong:** 静态 `1[3-9]\d{9}` 正则把 `14001234567`（联通物联网）当作手机号脱敏；用户拿到脱敏版后实际丢失的可能是设备 ID，**不是个人隐私**——但脱敏反而破坏了物联网号的设备标识。

**Why it happens:** 把"长度对 + 正则匹配"当作"个人手机号"。

**How to avoid:**
```python
# privacyguard/pii/validators/phone_segment.py + privacyguard/pii/data/rules.json

# 个人号段白名单（截至 2026-Q1 最新 MIIT 公告核发）：
# 移动: 134(0-8)/135/136/137/138/139/147(数据卡)/150/151/152/157/158/159
#       /172/178/182/183/184/187/188/195/197/198
# 联通: 130/131/132/145(数据卡)/155/156/166/175/176/185/186/196
# 电信: 133/149(数据卡)/153/173/177/180/181/189/190/191/193/199
# 广电: 192
# 虚拟运营商: 162/165/167/170(0-9)/171

# 物联网/卫星/数据卡（**应排除**）:
# 140 联通 IoT / 141(0) 电信 IoT / 144 移动 IoT / 1440 移动 IoT
# 146 联通 IoT / 148 移动 IoT / 1349 卫星 / 1740 卫星
# 145 联通数据卡 / 147 移动数据卡 / 149 电信数据卡

PERSONAL_PREFIX_3 = frozenset({
    # 三大运营商 + 广电 + 虚拟运营商（用户手机）
    '130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
    '150', '151', '152', '153', '155', '156', '157', '158', '159',
    '162', '165', '166', '167', '170', '171', '172', '173', '175', '176',
    '177', '178', '180', '181', '182', '183', '184', '185', '186', '187',
    '188', '189',
    '190', '191', '192', '193', '195', '196', '197', '198', '199',
})

EXCLUDED_PREFIX_3 = frozenset({
    # 物联网 / 卫星 / 数据卡（**不是**个人手机号）
    '140', '141', '144', '145', '146', '147', '148', '149',
    # 1349 / 1740 在 4 位前缀层处理（见 EXCLUDED_PREFIX_4）
})

EXCLUDED_PREFIX_4 = frozenset({
    '1349', '1440', '1740', '1741',
})


def is_mobile_segment(phone11: str) -> bool:
    """NUM-03 中国大陆手机号判定。"""
    if not phone11 or len(phone11) != 11 or not phone11.isdigit():
        return False
    if not phone11.startswith('1'):
        return False
    if phone11[:4] in EXCLUDED_PREFIX_4:
        return False
    if phone11[:3] in EXCLUDED_PREFIX_3:
        return False
    return phone11[:3] in PERSONAL_PREFIX_3
```

**Warning signs:** 测试覆盖了 `19912345678` 但没覆盖 `14001234567`（物联网号应被排除）；没有 `13491234567`（卫星号应被排除）

**Phase to address:** Phase 1（D-11 / D-12 ① 测试 ≥ 30 段号样本）

> **Open: MIIT 最新号段核对（D-11 / STATE.md "Open Questions"）**
> 截至 2026-Q1 已查到的最新核发：199（电信）、198（移动）、197（移动）、196（联通）、195（移动）、193（电信）、192（广电）、191（电信）、190（电信）。虚拟运营商 162 / 165 / 167 / 170(0-9) / 171。物联网 / 卫星排除清单见上。
> **建议在 `rules.json` 中固化清单 + 在 `test_pii_validators.py` 中 ≥ 30 段号断言**，并对 Phase 2+ 加一条 `tests/unit/test_pii_validators.py` 单元测试去查最新 MIIT 公告（人工每季度核对一次）。
> 本清单标 `[ASSUMED]` 直到用户在 Phase 1 实施前最终签字。

### Pitfall 5: OCR 字符归一化缺失导致校验失败

**What goes wrong:** OCR 输出 `１１０１０１１９９００３０７８８１１`（全角数字）或 `11010119900307\n8811`（跨行），18 位 / mod-11-2 校验全失败 → 漏判。

**Why it happens:** 输入文本未做 `normalize_digits`（全角→半角、移除 `-` / 空格）+ 跨行 flatten。

**How to avoid:**
```python
# privacyguard/pii/normalize.py
import re

def normalize_digits(text: str) -> str:
    """ENGINE-05 全角→半角 + 移除常见分隔符。"""
    full_to_half = str.maketrans(
        '０１２３４５６７８９', '0123456789'
    )
    text = text.translate(full_to_half)
    text = re.sub(r'[-\s　]', '', text)
    return text

def flatten_for_match(text: str) -> str:
    """ENGINE-06 跨行实体识别：移除换行 / 制表 / 全角空白后拼接。"""
    return re.sub(r'[\s\n\r\t　]+', '', text)
```

**Warning signs:** 测试用例只用 ASCII 数字；没覆盖全角样本；没覆盖跨行身份证

**Phase to address:** Phase 1（ENGINE-05 / ENGINE-06）

### Pitfall 6: 500 页扫描时主线程卡死

**What goes wrong:** 在 `MainWindow.open_pdf` 同步调用 `pii_engine.detect(unit)`，500 页 × 3 OCR 路径 = 几千次正则 → Qt 主线程冻结。

**Why it happens:** 把检测内联到主线程。

**How to avoid:**
- **不**在 `main.py` 直接调用 `pii_engine.detect`；只在 `_ModularOCRWorker.run` 内部调用
- 沿用现有 `progress_signal / finished_signal / error_signal / page_result_signal` 信号契约
- 加 `isInterruptionRequested()` 检查以支持取消（D-07 + Success Criteria #4）
- 复用现有 `self.worker_lock = QMutex()` (main.py:4931) 串行 worker 生命周期

**Warning signs:** 主线程出现 `pii_engine.detect(...)` 调用；任何 `re.finditer` 不在 QThread 内运行

**Phase to address:** Phase 1

### Pitfall 7: 测试夹带真实个人信息

**What goes wrong:** 单元测试断言里直接写 `110101199003078811` 这种真实身份证号 → 仓库 git 历史永久保留 → CI runner 把这些数据上传到日志 / 工件 → 离职开发者本地仍有完整克隆。

**Why it happens:** "为了测得真实"随手复制一个例子。

**How to avoid:**
```python
# tests/fixtures/fake_pii.py
from faker import Faker
from privacyguard.pii.validators.id_card import (
    compute_check_digit, validate_18,
)


def fake_id_card() -> str:
    """OPS-05 Faker 合成：通过 mod-11-2 校验的伪身份证。"""
    fake = Faker('zh_CN')
    while True:
        body17 = fake.numerify('##########' + '#######')[:17]
        if body17.isdigit() and body17[0] != '0':
            full = body17 + compute_check_digit(body17)
            if validate_18(full):
                return full


def fake_phone(seg: str = '138') -> str:
    """OPS-05 Faker 合成：通过 is_mobile_segment 的伪手机号。"""
    fake = Faker('zh_CN')
    return fake.numerify(f'{seg}' + '########')  # 11 位，前 3 段号确定
```

**Warning signs:** 测试断言字符串是 18 位 / 11 位数字且没有 `fake_` 前缀；`tests/samples/` 含真实 PDF

**Phase to address:** Phase 1（D-12 单元测试 + OPS-05）

### Pitfall 8: PyInstaller 新增模块导入失败（cp30 重演）

**What goes wrong:** `privacyguard/pii/data/rules.json` 未在 spec 的 `datas` 中声明 → `FileNotFoundError: rules.json` 在 frozen 启动时炸。`privacyguard.pii.image_ocr` (Phase 3 才用) `from rapidocr_onnxruntime import RapidOCR` 顶层 import → `privacyguard/__init__.py` 加载时拉起 native OCR DLL。

**Why it happens:** cp30 修复过 `privacyguard.utils.security` 类似问题；新增模块必须重新验证。

**How to avoid:**
- `privacyguard/pii/data/rules.json` 通过 `resource_path` 读取（D-10），并在 `packaging/windows/config/PrivacyGuard_windows.spec` 的 `datas=[...]` 段追加：
  ```python
  (os.path.join(project_root, 'privacyguard', 'pii', 'data'), 'privacyguard/pii/data'),
  ```
- `privacyguard/pii/__init__.py` 用 `_LAZY_IMPORTS` + `__getattr__`（参照 `privacyguard/__init__.py:61`）
- `tests/unit/test_package_imports.py` 扩展断言：`import privacyguard` 不触发 `privacyguard.pii.engine` 模块加载
- Windows + macOS 双平台真机打包验证（CLAUDE.md 强制要求）

**Warning signs:** `compileall` 通过但 frozen 启动报 `ModuleNotFoundError` / `FileNotFoundError`；spec `datas` 不含新数据文件

**Phase to address:** Phase 1（OPS-03 + D-10）

### Pitfall 9: PyMuPDF redaction API 选错参数导致图像残留

**What goes wrong:** 对纯扫描型 PDF 调用 `page.apply_redactions()` 但**未指定** `images` 参数 → 默认 `PDF_REDACT_IMAGE_NONE` → 嵌入图像的敏感区域仍是原图，只是上层涂了黑色矩形 → 用户拿放大镜或重 OCR 仍能读到原数字。

**Why it happens:** PyMuPDF `apply_redactions` 默认 `images=0` (PDF_REDACT_IMAGE_NONE) — 多数教程不强调这一点。

**How to avoid:**
- 严格沿用 `main.py:12354-12373` 既有 `images=fitz.PDF_REDACT_IMAGE_PIXELS` 设置（不是默认值 `PDF_REDACT_IMAGE_NONE = 0`，也不是 `PDF_REDACT_IMAGE_REMOVE = 1`，而是 `PDF_REDACT_IMAGE_PIXELS = 2`，把图像像素区域直接涂黑）。
- PDF_REDACT_IMAGE_* 三档对照：
  - `PDF_REDACT_IMAGE_NONE = 0`（**默认**，仅在内容流顶层画黑框，不动图像）
  - `PDF_REDACT_IMAGE_REMOVE = 1`（删除整张图像）
  - `PDF_REDACT_IMAGE_PIXELS = 2`（仅修改图像中被红框覆盖的像素，**最常用**——保留图像其他部分）
- 测试覆盖：构造嵌入图片的扫描 PDF，OCR 识别一个号码，apply redaction 后再次 OCR 该图片区域 → 断言数字消失

**Warning signs:** `apply_redactions()` 不带 `images=` 参数；测试只验证文字层 PDF，忽略图片型 PDF

**Phase to address:** Phase 1（SAFE-01 / SAFE-02）

### Pitfall 10: 假设 Python `re` 模块支持超时（实际不支持）

**What goes wrong:** 写 `re.finditer(pattern, text, timeout=0.5)` 期望某个超长恶意输入能自动中断 → 实际 Python `re` 模块**不**带 `timeout` 参数（已在本机 Python 3.12 用 `inspect.signature(re.finditer)` 验证：`finditer(pattern, string, flags=0)`）→ `TypeError: finditer() got an unexpected keyword argument 'timeout'`。

**Why it happens:** PITFALLS.md 第 10 节误称 "Python `re` 3.11+ 支持 timeout"，未经验证。

**How to avoid:**
- **不**调用 `re.finditer(..., timeout=...)`
- 退而求其次（Phase 1 简化方案）：
  1. 截断单页文本到 N 字符（默认 200,000）后再 `re.finditer`
  2. `_ModularOCRWorker.run` 既有 `isInterruptionRequested()` 检查天然兜底——worker 退出时正则中断
- 若 Phase 2 之后需要更严格的 ReDoS 防护，考虑引入第三方 `regex` 库（PyPI 上有，但增加依赖）或 `re2` 绑定

**Warning signs:** 出现 `re.finditer(..., timeout=` 或 `re.match(..., timeout=` 字样

**Phase to address:** Phase 1（ENGINE-07，但**仅**通过截断文本 + worker 中断实现）

### Pitfall 11: Worker 资源泄漏 / 重复触发扫描

**What goes wrong:** PII 检测追加到 `_ModularOCRWorker.run` 后，因为新 `pii_signal` 与既有 `page_result_signal` 顺序不确定，UI 状态在不同信号间漂移；或在 `_on_ocr_page_result` slot 里同时更新 `ocr` 与 `pii` 两处但只对一处做去重。

**How to avoid:**
- 维持现有 `self.worker_lock = QMutex()` 串行 worker 生命周期（main.py:4931）
- 现有 `cancel_ocr_scan`（main.py:11154）天然支持中断；PII 检测作为 OCR worker 的子步骤，复用同一 `requestInterruption()`
- `_pii_data_lock = QMutex()` 保护 `page_data[page]["pii"]` 写入（D-04 + Word 的 `_word_data_lock` 范本 main.py:4918）

**Phase to address:** Phase 1

---

## Code Examples

Verified patterns from official sources:

### `add_redact_annot` + `apply_redactions` 真删除（PyMuPDF 1.27.1）

**Source:** 沿用项目内 `main.py:12354-12373` 已生产验证的调用模式

```python
import fitz

doc = fitz.open(pdf_in)
try:
    for i in range(len(doc)):
        page = doc[i]
        # ① 添加脱敏注释（矩形 = PIIHit.page_rect 转 fitz.Rect）
        for rect in rects_per_page.get(i, []):
            annot = page.add_redact_annot(rect)             # 创建注释
            annot.set_colors(stroke=(0, 0, 0), fill=(0, 0, 0))  # 黑色填充
            annot.update()
        # ② 真正删除内容流中的文字（默认 text=True）
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_PIXELS,            # 关键：销毁图像像素
        )
        # ③ 防止 PDF 编辑器恢复注释
        for annot in page.annots() or []:
            page.delete_annot(annot)
    # ④ 保存时压缩 + 清残留
    doc.save(pdf_out, garbage=4, deflate=True, clean=True)
finally:
    doc.close()

# ⑤ 反向提取验证（SAFE-02）
out_doc = fitz.open(pdf_out)
try:
    out_text = ""
    for page in out_doc:
        out_text += page.get_text()
    assert "110101" not in out_text, f"反向提取失败：身份证未删除: {out_text}"
finally:
    out_doc.close()
```

**关键常量**（PyMuPDF 1.27.1 公开 API）：
- `fitz.PDF_REDACT_IMAGE_NONE = 0`（**默认**，仅顶层画框，图像像素不动 — 危险）
- `fitz.PDF_REDACT_IMAGE_REMOVE = 1`（删除整张图像）
- `fitz.PDF_REDACT_IMAGE_PIXELS = 2`（**项目用此**，仅修改被框住的像素，保留图像其他部分）
- `fitz.PDF_REDACT_LINE_ART_NONE = 0`
- `fitz.PDF_REDACT_LINE_ART_REMOVE = 1`

### GB 11643-1999 身份证校验（已 §Common Pitfalls §3 列出完整实现）

**Source:** GB 11643-1999 国标 + 多源 CSDN / 博客园实现交叉验证

```python
WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
MAPPING = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')

def compute_check_digit(body17: str) -> str:
    return MAPPING[sum(int(body17[i]) * WEIGHTS[i] for i in range(17)) % 11]

# 标准样本（GB 11643-1999）：53010219200508011X
# body17 = "53010219200508011", 加权 = 189, 189 % 11 = 2, MAPPING[2] = 'X' ✓
```

### 中国大陆手机号段判定（已 §Common Pitfalls §4 列出完整实现）

**Source:** 工信部 2017-08 号段核发公告（166/198/199）+ 2019-12 5G 号段（190/192/196/197）+ 物联网站段清单（MIIT 公开）

```python
# 项目内规则文件路径：privacyguard/pii/data/rules.json
{
  "phone_segment": {
    "personal_prefix_3": ["130","131","132","133","134","135","136","137","138","139",
                         "150","151","152","153","155","156","157","158","159",
                         "162","165","166","167","170","171","172","173","175","176",
                         "177","178","180","181","182","183","184","185","186","187",
                         "188","189","190","191","192","193","195","196","197","198","199"],
    "excluded_prefix_3": ["140","141","144","145","146","147","148","149"],
    "excluded_prefix_4": ["1349","1440","1740","1741"],
    "source": "MIIT 2017-08 / 2019-12 号段核发公告 + 工信部公开物联网号段清单",
    "last_verified": "2026-Q1",
    "next_review": "2026-Q3"
  }
}
```

### PIIHit dataclass（D-05 锁定）

```python
# privacyguard/pii/hits.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional, Tuple


class ConfidenceTier(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class PIIHit:
    entity_type: Literal["CN_ID_CARD", "CN_PHONE"]    # Phase 1 only
    page_offset: int                                    # 整页文本字符串偏移
    page_length: int                                    # 命中字符串长度
    page_rect: Tuple[float, float, float, float]        # (x, y, w, h) in PDF coords
    confidence_tier: ConfidenceTier                      # 默认 HIGH（Phase 1 全校验位严格）
    source: Literal["text", "image_block", "full_page_ocr"]
    mask_strategy: str                                  # partial mask 字符串（如 "110101********1234"）
    normalized: str = ""                                # 归一化后的字符串（用于跨实例一致掩码）
    validator_passed: bool = True                       # 是否通过校验位 / 段号白名单
```

### `Engine.detect(unit)` pipeline

```python
# privacyguard/pii/engine.py (伪代码骨架)
class PIIEngine:
    def __init__(self, rules_data):
        self._id_18_re = re.compile(r'(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)')
        self._id_15_re = re.compile(r'(?<!\d)([1-9]\d{14})(?!\d)')
        self._phone_re = re.compile(r'(?<!\d)(1\d{10})(?!\d)')
        self._phone_segment = rules_data["phone_segment"]

    def detect(self, unit: TextUnit) -> List[PIIHit]:
        text = unit.text
        flat = flatten_for_match(text)
        hits: List[PIIHit] = []
        # 身份证 18 位
        for m in self._id_18_re.finditer(flat):
            cand = m.group(0)
            if validate_18(cand):
                # 把 flat offset 映回原始 text offset
                orig_span = map_flat_to_original(flat, m.span(), text)
                hits.append(self._make_hit("CN_ID_CARD", unit, orig_span,
                                          ConfidenceTier.HIGH,
                                          "text" if unit.source == "text" else unit.source))
        # 身份证 15 位
        for m in self._id_15_re.finditer(flat):
            cand = m.group(0)
            if validate_15(cand):
                orig_span = map_flat_to_original(flat, m.span(), text)
                hits.append(self._make_hit("CN_ID_CARD", unit, orig_span,
                                          ConfidenceTier.HIGH, unit.source))
        # 手机号
        for m in self._phone_re.finditer(flat):
            cand = m.group(0)
            if is_mobile_segment(cand, self._phone_segment):
                orig_span = map_flat_to_original(flat, m.span(), text)
                hits.append(self._make_hit("CN_PHONE", unit, orig_span,
                                          ConfidenceTier.HIGH, unit.source))
        # DEDUP + consistency (ENGINE-04)
        return self._overlap.resolve(hits)
```

### 反向提取单元测试（D-12 ③ / SAFE-02）

```python
# tests/unit/test_pdf_pii_redaction.py
import fitz
import unittest
from tests.fixtures.fake_pii import fake_id_card, fake_phone


class TestPdfPiiRedaction(unittest.TestCase):
    def test_redacted_text_not_extractable(self):
        """SAFE-01/02: 脱敏后原文不可通过 page.get_text() 还原。"""
        secret_id = fake_id_card()
        secret_phone = fake_phone()
        src = fitz.open()
        page = src.new_page()
        page.insert_text((50, 100), f"测试样本 身份证 {secret_id} 手机 {secret_phone}", fontsize=14)
        tmp = "/tmp/_phase1_test.pdf"
        src.save(tmp)
        src.close()

        # PII 检测 + apply
        from privacyguard.pii.engine import PIIEngine
        from privacyguard.pii.pdf_adapter import apply_pii_redactions
        engine = PIIEngine.from_rules_file()
        doc = fitz.open(tmp)
        rects = {}
        for i, page in enumerate(doc):
            unit = build_text_unit_from_page(page, i, page.get_text())
            for hit in engine.detect(unit):
                r = hit.page_rect
                rects.setdefault(i, []).append(fitz.Rect(r[0], r[1], r[0]+r[2], r[1]+r[3]))
        doc.close()
        out = "/tmp/_phase1_test_redacted.pdf"
        apply_pii_redactions(tmp, out, rects)

        # 反向提取（SAFE-02 核心断言）
        out_doc = fitz.open(out)
        try:
            out_text = "".join(p.get_text() for p in out_doc)
            self.assertNotIn(secret_id[:10], out_text,   "身份证前 10 位仍可提取")
            self.assertNotIn(secret_phone[:7], out_text,  "手机号前 7 位仍可提取")
        finally:
            out_doc.close()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `page.draw_rect(fill=(0,0,0))` "redaction" | `page.add_redact_annot(rect)` + `page.apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` | PyMuPDF 1.18+ (2019) | 黑框覆盖但内容可还原 → 内容真删除；2019-2024 多起公开事故验证 `draw_rect` 不可信 |
| `re.compile` 然后 `finditer`，无超时 | `re.finditer(..., timeout=...)` 据称 Python 3.11+ 支持 | **不存在**（已在本机 Python 3.12 验证：`inspect.signature(re.finditer)` 为 `(pattern, string, flags=0)`） | 业界误信；必须改用 worker 中断或文本截断 |
| `pdf_text` poppler 反向提取 | `fitz.open(out).get_text()` | 项目 D-14 | 避免 CI 装 poppler；`pdftotext` 仅作人工验证 |
| 项目旧版：OCR 文本层 + 文字层 key 合并到 `page_data["ocr"]` | 新增 `page_data["pii"]` 键保留独立 PII 命中 | Phase 1 (D-04) | 守住 v37.7.6 收敛；OCR 路径与 PII 路径各司其职 |
| 静态号段正则 `1[3-9]\d{9}` | 双白名单（个人号段 − 14X 物联网 / 卫星） | PITFALLS §4 + Phase 1 D-11 | 物联网号不再被错识为个人手机号 |

**Deprecated/outdated:**
- **Python `re` `timeout=` keyword argument:** 不存在；任何教程 / 资料引用"Python 3.11+ `re.finditer(..., timeout=...)`"应被拒绝
- **Pure draw_rect as redaction:** PITFALLS §1；行业头号失败模式
- **`main.py` 内嵌 PII 检测:** 违反 D-04 / v37.7.6 收敛

---

## TDD Specifics

`config.json.workflow.tdd_mode = true` + `tdd_mode = true`：本 Phase 1 所有 ENGINE-* / NUM-* / SAFE-* 单元测试先于实现落地。

### Fixtures

- **Faker 合成 PII：** `tests/fixtures/fake_pii.py::fake_id_card()`（Faker + mod-11-2 校验循环）+ `fake_phone(seg)`（Faker `numerify`）；**严禁**在测试中写真实号码
- **合成 PDF 生成器：** `tests/e2e/create_pii_test_pdf.py`（与现有 `tests/e2e/create_test_pdf.py` 对齐），用 `page.insert_text((x, y), text, fontsize=N)` 把 `fake_id_card()` / `fake_phone()` 写到 PDF 文字层
- **合成扫描型 PDF：** 把文字渲染成像素图后用 `page.insert_image(rect, pixmap=...)` 嵌入，模拟扫描件
- **混合型 PDF：** 同时包含文字层（真实文本）+ 嵌入图片（`page.insert_image`），与现有 `test_mixed_pdf_ocr.py` 范本对齐

### Test-First Cycle 示例

| Requirement | Failing Test (FIRST) | 实现 (THEN) | Fixture |
|-------------|---------------------|-------------|---------|
| NUM-01 (18 位 mod-11-2) | `test_valid_18_passes_checksum()` 断言 `validate_18("53010219200508011X") == True` | `validators/id_card.py::validate_18` | 5+ 个标准样本（已知好 + 已知坏） |
| NUM-01 (15 位升级) | `test_15_digit_upgrades_to_valid_18()` 断言 `upgrade_15_to_18("420106960901234") == "420106199609012343"` | `validators/id_card.py::upgrade_15_to_18` + `validate_15` | 5+ 个 15 位样本 |
| NUM-02 (X 大小写) | `test_lowercase_x_accepted_via_upper()` 断言 `validate_18("53010219200508011x") == True` | `validate_18` 内 `last.upper() == expected` | 包含 `x` / `X` 边界 |
| NUM-03 (个人号段白名单) | `test_personal_segment_recognized()`：199/192/166/162/165/167 都 `is_mobile_segment == True` | `validators/phone_segment.py::is_mobile_segment` | 段号表 |
| NUM-03 (物联网排除) | `test_iot_segment_excluded()`：140/141/144/146/148/149/1349/1740 都 `is_mobile_segment == False` | 同上 | 物联网段表 |
| ENGINE-05 (归一化) | `test_fullwidth_digits_normalized()` 断言 `normalize_digits("１１０１０１...") == "110101..."` | `normalize.py::normalize_digits` | 全角样本 |
| ENGINE-06 (跨行) | `test_id_across_linebreak_recognized()` 断言文本 `"110101\n19900307\n8811"` 命中 `CN_ID_CARD` | `engine.py` flatten 路径 | 跨行身份证 |
| ENGINE-07 (ReDoS 防御) | `test_long_text_does_not_block()` 500KB 文本输入应在 1 秒内返回（worker 中断兜底） | 截断 + worker 中断 | 长字符串样本 |
| ENGINE-08 (零网络) | `test_engine_makes_no_network_calls()` 扫描整个 500 页文档后 `socket.socket()` 调用次数为 0 | `pii/` 子包零 IO 设计 + 测试 monkey-patch | monkey-patch `socket.socket` |
| SAFE-01 (真删除) | `test_redacted_text_unreadable()` 见 §Code Examples 末尾 | `pdf_adapter.py::apply_pii_redactions` | 合成 PDF |
| SAFE-02 (反向提取) | 同 SAFE-01 测试 | 同上 | 同上 |
| OPS-03 (懒加载) | `test_import_privacyguard_does_not_load_pii_engine()` 断言 `sys.modules` 不含 `privacyguard.pii.engine` | `pii/__init__.py` 懒加载表 | monkey-patch `import` |
| OPS-07 (基线 79/79) | CI 命令 `python3 -m unittest tests.unit.test_*` 全过 | 无（门禁） | CLAUDE.md 列出的 10 个 unittest 模块 |

### Reverse-Extraction Verification (Phase 1 mandatory)

```python
# tests/unit/test_pdf_pii_redaction.py（强制要求）
def test_full_pipeline_id_and_phone_redaction(self):
    """端到端：合成 PDF → PII 检测 → apply → 反向提取 → 断言敏感字串消失。"""
    secret_id = fake_id_card()
    secret_phone = fake_phone()
    # ... 构造 PDF、检测、apply、提取 ...
    out_text = "".join(p.get_text() for p in fitz.open(out_pdf))
    self.assertNotIn(secret_id, out_text)
    self.assertNotIn(secret_phone, out_text)
```

### TDD Wave Plan 草图

1. **Wave 0:** 新增 `tests/fixtures/fake_pii.py` + `tests/e2e/create_pii_test_pdf.py`（生成器）— **先于**任何 PII 代码
2. **Wave 1:** `test_pii_validators.py` (NUM-01/02/03) → 实现 `validators/id_card.py` + `validators/phone_segment.py`
3. **Wave 2:** `test_pii_engine.py` (ENGINE-01..07) → 实现 `engine.py` + `hits.py` + `normalize.py` + `confidence.py` + `mask.py` + `overlap.py`
4. **Wave 3:** `test_pdf_pii_pipeline.py` + `test_pdf_pii_redaction.py` (SAFE-01/02) → 实现 `pdf_adapter.py` + 集成到 `_ModularOCRWorker.run`
5. **Wave 4:** `test_pii_offline.py` (ENGINE-08 / OPS-07) + `test_package_imports.py` 扩展 (OPS-03) → 验证懒加载 + 零网络
6. **Wave 5:** `test_app_config.py` + `test_convergence.py` 扩展 → `config.json.pii_settings` + `SettingsDialog` tab + `main.py` UI 集成

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MIIT 截至 2026-Q1 最新个人号段白名单（含 162/165/167/170(0-9)/171 虚拟运营商 + 190/192/196/197/198/199 5G 号段） | §Standard Stack / §Code Examples / §Common Pitfalls §4 | 若有 Phase 1 实施后的新号段被遗漏，新号段用户接到脱敏版后合规盲区；风险等级 MEDIUM |
| A2 | 物联网站段排除清单（140/141/144/145/146/147/148/149/1349/1440/1740/1741）覆盖 2026 全部在用 IoT / 卫星段 | §Standard Pitfalls §4 | 若新增 IoT 段被遗漏，错识为个人手机号；MEDIUM |
| A3 | PyMuPDF `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` 在 1.27.1 版本语义与早期一致 | §Code Examples / §Common Pitfalls §9 | 若 API 行为变化，真脱敏可能失效；LOW（项目自身有现网验证） |
| A4 | Python 3.11+ `re.finditer` 不带 `timeout` 参数（已在本机 Python 3.12 验证） | §Common Pitfalls §10 | 若 CPython 某天合并第三方 `regex` 库的 timeout API，现状会变；LOW |
| A5 | Faker `numerify` 能生成通过 mod-11-2 的 18 位身份证 | §TDD Specifics / §Common Pitfalls §7 | 若生成循环不收敛（极小概率），测试 fixture 不可用；LOW |
| A6 | 现有 `main.py:12354-12385` 的 PyMuPDF 调用模式（`add_redact_annot` + `apply_redactions(IMAGE_PIXELS)` + `garbage=4`）可安全复用，不需调整 | §Architecture Patterns §Pattern 3 | 若生产环境实际还有漏洞，需重写；LOW（v37.3 / v37.7.6 已多次验证） |
| A7 | 现有 `_ModularOCRWorker.run` 的 `isInterruptionRequested()` 检查频率足以在 500 页扫描中支持快速取消 | §Common Pitfalls §11 / Success Criteria #4 | 若检查点太稀（每 10 页检查），用户感觉取消延迟；LOW |
| A8 | `privacyguard.ocr.mixed_pdf.py:76` 的 `recognize_fn` / `calculate_rect_fn` / `clip_to_page_rect_fn` 注入形态可直接复用到 `collect_full_page_ocr_hits`（D-03） | §Architecture Patterns §Pattern 1 | 若 worker 内部调用形态不一致，需改 `_ModularOCRWorker.run`；LOW |
| A9 | `resource_path` 在 PyInstaller frozen 模式下正确解析 `privacyguard/pii/data/rules.json` | §Common Pitfalls §8 | 若 spec 的 `datas=[...]` 配置错误，frozen 启动崩溃；MEDIUM（cp30 已踩过坑） |

**If this table is empty:** 仍有非空；实施前必须对 A1 / A2 做最终签字。

---

## Open Questions

1. **MIIT 最新号段白名单（D-11 / STATE.md "Open Questions"）**
   - What we know: 截至 2026-Q1 已查到的最新核发：190/192/196/197/198/199 + 162/165/167/170/171 虚拟运营商
   - What's unclear: 是否有 2026-Q1 之后新核发的号段（用户需自行核对）
   - Recommendation: 在 `rules.json` 中固化清单 + `next_review: "2026-Q3"` 字段；Phase 1 实施前用户签字

2. **`PIIHit.mask_strategy` 字段语义（D-05）**
   - What we know: D-05 锁定字段名；`mask.py::partial_mask("CN_ID_CARD", "110101199003078811")` 输出 `"110101********8811"`（前 6 后 4）
   - What's unclear: Phase 1 默认 partial masking（不实现全 blackout），还是 HIGH 档走 partial / MEDIUM 档走 full？
   - Recommendation: Phase 1 统一 partial masking（行业默认）；全 blackout 推迟到 Phase 2（MASK-02）

3. **`overlap.py` 跨 recognizer 冲突解决（D-04 / ENGINE-04）**
   - What we know: Phase 1 单一 recognizer（regex + checksum）；Phase 2+ 多 recognizer 叠加需 `overlap.py`
   - What's unclear: Phase 1 是否需要 `overlap.py` 骨架（占位）？
   - Recommendation: 实现 `overlap.py::resolve(spans) -> List[PIIHit]`，但 Phase 1 仅去重同 recognizer 重复命中；跨 recognizer 优先级推迟

4. **`_pii_data_lock` 必要性**
   - What we know: 现有 `_word_data_lock` 保护 word_data；`page_data` 写入是否需要锁待定
   - What's unclear: PyQt 的 `pyqtSignal` 跨线程连接默认 `Qt.AutoConnection`（主线程 slot 串行执行），是否还需要 `QMutex`？
   - Recommendation: 引入 `_pii_data_lock = QMutex()` 作为防御性编程（与 `_word_data_lock` 对齐）；CLAUDE.md 强调 "Worker 写 page_data 必须串行"

5. **`page_offset / page_length` 与现有 `QRectF` 双轨**
   - What we know: D-05 / D-06 锁定 `page_offset / page_length / page_rect` 三字段并存
   - What's unclear: `page_rect` 是 `(x, y, w, h)` 还是 `fitz.Rect`？UI 用 `QRectF`，apply 阶段用 `fitz.Rect`
   - Recommendation: `page_rect` 存为 4 元 tuple `(x, y, w, h)`，与 `QRectF(x, y, w, h)` 互转（`QRectF(r[0], r[1], r[2], r[3])`）；apply 阶段再转 `fitz.Rect(r[0], r[1], r[0]+r[2], r[1]+r[3])`

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | `re.finditer` / `dataclasses` | ✓ | 3.12.13 | — |
| PyMuPDF (fitz) | PDF 真脱敏 | 项目 requirements.txt 固定 `==1.27.1` | 1.27.1 | — |
| PyQt6 | `QThread` / `pyqtSignal` / `QMutex` | 项目 requirements.txt 固定 `==6.10.2` | 6.10.2 | — |
| `pdftotext` (poppler-utils) | 反向提取备用 | ✗ | — | **优先 `fitz.open(out).get_text()`**（D-14） |
| RapidOCR | OCR 三路径之一 | 已固定 `==1.2.3`；项目内 `privacyguard/ocr/rapidocr.py` | 1.2.3 | — |
| Faker | 测试 fixture (`fake_id_card()`) | **未在 requirements.txt**，需评估是否新增 | — | **Phase 1 不新增**，手写生成循环 (`random.randint + mod-11-2`)，把 Faker 推迟到 Phase 2 测试统一引入 |
| GNU patch / git | rollback | ✓ | — | — |

**Missing dependencies with no fallback:**
- 无（核心栈全部已就绪）

**Missing dependencies with fallback:**
- `pdftotext`：D-14 明确用 `fitz` 路径，无需 poppler
- Faker：手写循环（`fake_id_card` 不依赖 Faker；只用 `random.randint`）

**Skip condition for environment probe:** 不适用（已逐项检查）

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `unittest` (Python stdlib) — 项目内 10 个 `tests/unit/test_*.py` 全部 `unittest.TestCase` |
| Config file | 无独立配置（`unittest` 自动发现） |
| Quick run command | `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction -v` |
| Full suite command | `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pii_offline -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NUM-01 | GB 11643 mod-11-2 校验位 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestIdCardChecksum -v` | ❌ Wave 0 |
| NUM-01 | 15 位 → 18 位升级 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestIdCardUpgrade15To18 -v` | ❌ Wave 0 |
| NUM-02 | 末位大写 X / OCR 小写 x | unit | `python3 -m unittest tests.unit.test_pii_validators.TestIdCaseInsensitiveX -v` | ❌ Wave 0 |
| NUM-03 | 手机号段号白名单 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestPhoneSegment -v` | ❌ Wave 0 |
| NUM-03 | 14X 物联网段排除 | unit | `python3 -m unittest tests.unit.test_pii_validators.TestIotExclusion -v` | ❌ Wave 0 |
| ENGINE-01 | 自动扫描全文输出候选 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestEngineDetect -v` | ❌ Wave 0 |
| ENGINE-02 | 实体类型 + 偏移 + 档位 + 来源 + 掩码 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestPIIHitSchema -v` | ❌ Wave 0 |
| ENGINE-03 | HIGH/MEDIUM/LOW 三档 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestConfidenceTiers -v` | ❌ Wave 0 |
| ENGINE-04 | 同一实体多实例一致掩码 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestMaskConsistency -v` | ❌ Wave 0 |
| ENGINE-05 | 全角转半角 + offset 回算 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestNormalization -v` | ❌ Wave 0 |
| ENGINE-06 | 跨行 / 分栏边界识别 | unit | `python3 -m unittest tests.unit.test_pii_engine.TestCrossBoundary -v` | ❌ Wave 0 |
| ENGINE-07 | 大文档不阻塞 | smoke | `python3 -m unittest tests.unit.test_pii_engine.TestLargeDocumentNoBlock -v` | ❌ Wave 0 |
| ENGINE-08 | 零网络 | unit (monkey-patch socket) | `python3 -m unittest tests.unit.test_pii_offline -v` | ❌ Wave 0 |
| FMT-01 | PDF 文字层 + OCR 接入识别 | integration | `python3 -m unittest tests.unit.test_pdf_pii_pipeline -v` | ❌ Wave 0 |
| SAFE-01 | PyMuPDF 真删除 | integration | `python3 -m unittest tests.unit.test_pdf_pii_redaction -v` | ❌ Wave 0 |
| SAFE-02 | 反向提取断言敏感字串消失 | integration | 同上 | ❌ Wave 0 |
| OPS-03 | 懒加载（`import privacyguard` 不触发 `privacyguard.pii.engine`） | unit | `python3 -m unittest tests.unit.test_package_imports -v` | ✅ 已有（需扩展） |
| OPS-07 | 79/79 既有基线通过 | regression | `python3 -m unittest tests.unit.test_mixed_pdf_ocr tests.test_path_validation tests.unit.test_ocr_api tests.unit.test_package_imports tests.unit.test_pdf_text_hit_dedup tests.unit.test_app_config tests.unit.test_word_replace_rules tests.unit.test_batch_word_replace tests.unit.test_config_alignment tests.unit.test_fstring_safety tests.unit.test_convergence -v` | ✅ 已有 |

### Sampling Rate

- **Per task commit:** `python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine -v`（快速反馈 validators + engine）
- **Per wave merge:** `python3 -m compileall -q main.py privacyguard tests && python3 -m unittest tests.unit.test_pii_validators tests.unit.test_pii_engine tests.unit.test_pdf_pii_redaction tests.unit.test_pdf_pii_pipeline tests.unit.test_pii_offline tests.unit.test_package_imports tests.unit.test_convergence -v`
- **Phase gate:** Full suite 绿色（含 79/79 既有基线）→ `/gsd-verify-work` → `git tag`

### Wave 0 Gaps

- [ ] `tests/fixtures/fake_pii.py` — `fake_id_card()` / `fake_phone()` 合成 fixture（OPS-05）
- [ ] `tests/e2e/create_pii_test_pdf.py` — PyMuPDF `insert_text` 生成测试 PDF（含文字层 + 嵌入图片 + 跨行）
- [ ] `tests/unit/test_pii_validators.py` — NUM-01/02/03（≥ 20 断言样本）
- [ ] `tests/unit/test_pii_engine.py` — ENGINE-01..07
- [ ] `tests/unit/test_pdf_pii_pipeline.py` — 端到端：合成 PDF → 检测 → apply
- [ ] `tests/unit/test_pdf_pii_redaction.py` — SAFE-01/02 反向提取
- [ ] `tests/unit/test_pii_offline.py` — ENGINE-08 / OPS-07 零网络 monkey-patch
- [ ] `tests/unit/test_package_imports.py` 扩展 — OPS-03 懒加载断言
- [ ] `tests/unit/test_convergence.py` 扩展 — `main.py` 不顶层 import `privacyguard.pii.*`
- [ ] `tests/unit/test_app_config.py` 扩展 — `pii_settings` 字段默认值

*(If no gaps: 仍需 Wave 0 — Phase 1 全部为新测试)*

---

## Security Domain

> Required by `config.json.workflow.security_enforcement = true` (default). ASVS Level 1 per `security_asvs_level: 1`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | 应用无用户账号、无 token、无远程端点 |
| V3 Session Management | no | 单进程桌面应用，会话即进程生命周期 |
| V4 Access Control | partial | 文件路径安全由 `privacyguard/utils/security.py::validate_safe_path` (cp30 已加固) 守护；新增 `pii_settings` 走 `SimpleConfig`（不切换到 `ConfigManager`） |
| V5 Input Validation | yes | PDF 输入路径校验（既有）+ 文本输入经 `normalize_digits` / `flatten_for_match` 归一化；正则表达式来源固定（无用户自定义 regex，避免 ReDoS） |
| V6 Cryptography | no | 无加密需求；Faker 合成 PII 不构成"个人数据"保护范围（OPS-05） |
| V7 Error Handling | partial | Worker 异常经 `error_signal` 暴露；PII 引擎内部异常不暴露敏感原文（`str(exc)` 截断） |
| V9 Logging | partial | 项目用 `print()` 而非日志框架；新增 PII 模块必须遵守"不在 stdout 打印原文"原则（V9.2.1） |
| V12 Files and Resources | yes | 临时目录走 `TempFileManager`；新增 `pii/data/rules.json` 经 `resource_path` 读取；PyInstaller `datas` 同步声明（cp30 教训） |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| ReDoS（恶意长字符串导致正则灾难性回溯） | Denial of Service | 截断单页文本到 N=200,000 字符 + worker `isInterruptionRequested()` 中断；**不**依赖 Python `re` 的 `timeout=`（不存在） |
| PyInstaller 数据文件丢失 | Denial of Service | `datas=[...]` 在 spec 显式声明 + `resource_path` 唯一入口 + Windows / macOS 双平台真机验证 |
| 测试夹带真实 PII（git 历史永久保留） | Information Disclosure | `tests/fixtures/fake_pii.py` 合成；CI 加 `.gitignore tests/samples/real_*`（Phase 1 不引入真实样本） |
| OCR 字符归一化失效导致校验失败（漏报） | Tampering | `normalize_digits` 强制全角→半角 + `flatten_for_match` 跨行拼接；单元测试覆盖全角样本 |
| 段号白名单静态化（新号段漏判） | Tampering | `rules.json` 外部 JSON 数据文件 + `next_review` 字段；Phase 1 用户签字 + Phase 2 起季度复核 |
| PyMuPDF `draw_rect` 替代 `add_redact_annot`（假脱敏） | Information Disclosure | `pdf_adapter.py` 单一入口 + code review 红线字样检查 + 反向提取单元测试 |
| `socket.socket` 在 PII 引擎里意外触发 | Information Disclosure | `tests/unit/test_pii_offline.py` monkey-patch 拦截所有出站 socket 调用，扫描 500 页文档后断言调用次数为 0（ENGINE-08 / OPS-07） |
| 用户原文进入 stdout / stderr（日志泄漏） | Information Disclosure | PII 引擎模块不打印命中原文；仅打印 `[PII] 页面 X 命中 N 项敏感内容`（命中数，不打印内容） |

---

## Sources

### Primary (HIGH confidence)

- [GB 11643-1999 公民身份号码 规则说明（webmasterhome.cn）](http://tool.webmasterhome.cn/idcardguize.asp) — 权重数组 + 校验码表官方复述
- [CSDN — 计算身份证校验码 GB 11643-1999](https://blog.csdn.net/weixin_30632089/article/details/97043127) — 算法权重与映射表交叉验证
- [博客园 — php 验证身份证有效性 GB 11643-1999](https://www.cnblogs.com/bossikill/p/3679926.html) — 15→18 位升级算法
- [CSDN — 身份证15位转18位算法](https://blog.csdn.net/sinat_37774909/article/details/131597773) — 15 位升级步骤完整示例
- [MIIT 2017-08 号段核发公告（166/198/199）via 海外网](http://news.haiwainet.cn/n/2017/0809/c3541839-31061208.html) — 三大运营商新号段公告
- [MIIT 2019-12 5G 号段（190/192/196/197）via 中华网](https://news.china.com/socialgd/10000169/20191225/37572867.html) — 5G 号段公告
- [CSDN — 史上最全最新手机号码号段大全](https://blog.csdn.net/xiaobatian_/article/details/102454778) — 物联网站段 + 虚拟运营商段清单
- [PyMuPDF `apply_redactions` 参数详解 via WebSearch](https://pymupdf.readthedocs.io) — `PDF_REDACT_IMAGE_*` 三档常量 + `text=True` 默认 + `garbage` / `deflate` / `clean` 参数语义
- [项目内 `main.py:12354-12385` 现有 PyMuPDF 真删除调用](file:///mnt/g/Project/PrivacyGuard/main.py) — 已生产验证的调用模式
- [Python stdlib `re.finditer` 签名 (本机 Python 3.12 `inspect.signature` 验证)](https://docs.python.org/3/library/re.html) — 确认 `finditer(pattern, string, flags=0)` 无 `timeout` 参数

### Secondary (MEDIUM confidence)

- 项目内 `.planning/research/STACK.md` — 自研 PII 引擎 vs Presidio 决策已多源验证
- 项目内 `.planning/research/PITFALLS.md` — Pitfall 1/4/6/7/8 等已多源验证；§10 关于 `re.finditer timeout=` 的描述**已在本研究中修正**
- 项目内 `.planning/codebase/CONCERNS.md` — 性能瓶颈 + PyInstaller 风险已知
- [PITFALLS.md §10 原始描述（需修正）](file:///mnt/g/Project/PrivacyGuard/.planning/research/PITFALLS.md) — 关于 Python `re` 内置 `timeout=` 的描述不准确

### Tertiary (LOW confidence)

- [WebSearch — PyMuPDF apply_redactions images text garbage parameters](https://duckduckgo.com) — 二级聚合，需直接读 PyMuPDF docs
- [WebSearch — Faker generate valid Chinese ID card ssn checksum loop](https://duckduckgo.com) — Ruby Faker 实现，与 Python Faker 行为类似
- [WebSearch — MIIT 工信部 中国大陆手机号段 2025 最新](https://duckduckgo.com) — 二级聚合网站，号段清单与工信部原始公告交叉核对

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyMuPDF 真删除 API / GB 11643 / MIIT 号段白名单均有官方/权威来源
- Architecture: HIGH — 沿用 `main.py:12354-12385` 已生产验证的 PyMuPDF 调用；新增 `privacyguard/pii/` 子包按 CONTEXT.md D-04 / D-05 严格锁定
- Pitfalls: HIGH — PITFALLS.md 已多源验证；§10 关于 Python `re` `timeout=` 的描述**已在研究中修正**（实际不存在该参数）
- TDD specifics: HIGH — Faker 合成 PII + PyMuPDF `insert_text` 合成 PDF 是已知标准做法

**Research date:** 2026-08-10
**Valid until:** 30 days (PyMuPDF API stable; MIIT 号段白名单可能随新公告变化)

---

*Phase 1 Research complete. Planner can now create PLAN.md files.*