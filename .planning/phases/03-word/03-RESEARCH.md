# Phase 3: Word 文档接入识别引擎（双栏对比预览自动高亮） - Research

**Researched:** 2026-08-11
**Domain:** Word 文档路径接入 PII 引擎 + 双栏预览自动高亮 + .docx 真脱敏
**Confidence:** HIGH
**Researcher:** GSD Phase Researcher

## Summary

Phase 3 把 Phase 1/2 已建好的 PII 引擎（9 类实体识别 + 校验位 + partial mask）扩展到 Word 文档路径。核心是新建 `privacyguard/pii/word_adapter.py`（与 `pdf_adapter.py` 对称），在 `_ModularWordWorker.run()` 内对每段/每 cell 文本做 PII 扫描并写入 `word_data[key]["pii"]`，扩展 `merge_word_matches_with_priority` 把 PII 并入"ocr 层"分派，最终在双栏对比预览的左/右栏同时高亮、`.docx` 导出时按 `mask_strategy` 真脱敏。

项目既有代码已为这一阶段铺设了完整底盘：(1) `PIIEngine` 9 类实体 + 6 类校验位 + `mask_for_entity` 统一分派表已就位；(2) `word_data` 单字典形态 + `para.text` 字符串视图简化命中定位；(3) cp27 修复后的 `data-key` DOM patch 路径把高亮数据按 key 局部更新，避免右栏整块空白；(4) `replace_matches_in_paragraph` 已处理"按段合并 run 后 replace"，跨 run 命中已可正确处理。Phase 3 的"重复造轮子"风险极低，主要工作量在三处：① `word_adapter.py` 的三函数实现 + 懒加载注册；② `merge_word_matches_with_priority` 的"ocr ∪ pii"分支扩展；③ 4 类新单元测试覆盖（纯函数 + worker 接入 + reverse-extraction + DOM patch）。

**Primary recommendation:** 严格按 CONTEXT.md D-01..D-17 落地；不修改 PIIHit 字段、不 import python-docx 进 word_adapter、用 `paragraph.text.find()` 顺序扫描拿 char_offset，`paragraph._element.clear_content()` 后单 run 重建以保留段级样式。

## User Constraints (from 03-CONTEXT.md)

### Locked Decisions (Verbatim)

- **D-01:** PII 命中并入"ocr 层"——`merge_word_matches_with_priority` 的优先级扩展为 `rule > manual > (ocr ∪ pii)`。原"ocr"层做最小改动：把 PII 命中作为"自动扫描"成员并入，合并函数仅扩展源，不改既有 rule/manual 分支。
- **D-02:** 同层（ocr ∪ pii）内部 PII 优先于 OCR：同一文本片段同时被 OCR 与 PII 命中时，PII 胜出。合并函数对 `ocr_list + pii_list` 排序时按 `confidence_tier` 优先 + PII 来源加权。
- **D-03:** 重叠区 mask 文本走"分路径独立"：OCR 命中走纯黑框 `[已脱敏]`，PII 命中走 `partial_mask`（`110101********1234`），重叠区 PII partial_mask 胜出。
- **D-04:** Word 端保存 .docx 时**默认与 PDF 一致真脱敏**：PII 命中按 `mask_strategy` 实际写入产物。
- **D-05:** 掩码模式双层配置：默认走 `pii_settings.per_entity_default`（Phase 2 D-13 已锁字段），文档级 override 通过 `self.word_data[0]["mask_override_this_doc"] = "partial" | "blackout"` 临时反转。文档级 toggle 走主界面 toolbar，与 PDF 共用同一个 toggle 控件或紧邻摆放。
- **D-06:** Word 真脱敏实现走"生成文本 + 外部调 Python-docx"路径：PIIHit 经 `locate_pii_hits_in_paragraph(hits, paragraph_text)` 拿到 `(hit, char_offset_in_paragraph_text)` 列表，调用方拿 docx 文件 → 对其每一段按 G4-D 策略合并 run 后 `replace`。不在 `privacyguard/pii/word_adapter.py` 内 import python-docx。
- **D-07:** Python-docx 的 run 边界走"合并同段所有 run 后 replace"路径：`para.text` 是段内所有 run 字符串拼接的视图，`replace()` 默认按段内字符串匹配；PII 命中跨 run 时先调用 `paragraph._element.clear_content()` + 单 run 重建，保留段样式（`paragraph.style`）但不保留 run 内文字格式（粗体/斜体）。
- **D-08:** PIIHit 仅作"内容描述"使用，WordAdapter 现场用 `hit.text` 在 `word_data[key]["text"]` 内做精确子串定位。
- **D-09:** 同文本重复（`hit.text` 在同一段落出现多次）逐个展开为多个独立 PIIHit，每个 PIIHit 携带自己的 `char_offset`。
- **D-10:** Word 端 PIIHit.source 复用 `"text"`（与 PDF 文字层路径对齐）。
- **D-11:** 新建 `privacyguard/pii/word_adapter.py`（与 `pdf_adapter.py` 平级），提供对称三函数：`collect_pii_word_hits` / `locate_pii_hits_in_paragraph` / `apply_pii_replacements_to_docx`。
- **D-12:** PII 检测在 `_ModularWordWorker.run()` 内执行；批量 Word 替换入口在 Phase 3 显式跳过 PII 扫描。
- **D-13:** `privacyguard/pii/__init__.py` 的 `_LAZY_IMPORTS` 注册 `word_adapter` 模块的三个公开函数。
- **D-14:** 新增 `privacyguard/pii/word_adapter.py` 需同步验证 PyInstaller `hiddenimports`（Windows spec + macOS spec）。
- **D-15:** Phase 3 必须新增至少 4 类单元测试：`test_word_pii_adapter.py` / `test_word_worker_pii.py` / `test_word_pii_redaction.py` / `test_word_preview_highlight.py`。
- **D-16:** Phase 3 必须保持 282/282 既有测试基线全部通过；新增 4 个 PII word 测试在 Phase 3 完成后进入基线（基线从 282/282 升级约 295+/295+）。
- **D-17:** `_ModularWordWorker.run()` 改动后必须保持 `test_word_replace_rules.py` + `test_batch_word_replace.py` 全部通过。

### Claude's Discretion

- PII 命中在右栏预览中的**颜色**选择：复用 Phase 1 既有深红色系（建议 `#d63031`），不引入新色避免视觉杂乱。
- `collect_pii_word_hits` 是否在调用方做 `confidence_tier` 二次过滤（LOW 档候选仅高亮不进真脱敏）：建议复用 Phase 2 `classify_hit` 范式，HIGH/MEDIUM 真脱敏、LOW 仅高亮。
- `apply_pii_replacements_to_docx` 跨段命中处理：建议保持"按段合并 run"，跨段命中仅替换各段内对应子串。
- `_ModularWordWorker.run()` 接入 PII 后是否仍允许取消：保留现有 `isInterruptionRequested()` 检查点。

### Deferred Ideas (OUT OF SCOPE)

- 候选审阅 UI 完整形态（按实体类型/来源筛选 + 分页）→ Phase 7
- 识别规则编辑 UI → Phase 8
- 审计报告（JSON）→ Phase 8
- 完整行政区划词典 ~70 万条 → Phase 6
- BIC（SWIFT Code）识别 → 仍 Deferred
- 批量 Word 替换入口的 PII 接入 → 后续 phase
- Word 端替换后预览按来源筛选高亮（rule / manual / ocr / pii）→ Phase 7

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **FMT-02** | Word 处理路径接入识别引擎，识别候选在双栏对比预览中高亮 | `word_adapter.collect_pii_word_hits` + `_ModularWordWorker.run()` 写入 `word_data[key]["pii"]` + `merge_word_matches_with_priority` 扩展 `ocr ∪ pii` 源 + 双栏预览 DOM patch 渲染 |
| **UX-01** | 用户可在候选审阅列表中查看所有待确认识别项 | Phase 3 仅做双栏高亮（最小可用形态），完整审阅 UI 推 Phase 7 |
| **UX-02** | 候选列表支持按实体类型与来源筛选 + 分页 | Phase 3 仅做双栏高亮，完整筛选 UI 推 Phase 7 |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 段落文本 PII 检测 | API/Backend（worker thread） | — | `_ModularWordWorker.run()` 中执行，扫描每段/每 cell 文本 |
| 段落内 char_offset 定位 | PII 引擎边界（adapter） | — | `word_adapter.locate_pii_hits_in_paragraph` 是"内容→位置"换算的边界 |
| 右栏合并优先级 | PII 引擎边界（adapter） | — | `merge_word_matches_with_priority` 扩展 `ocr ∪ pii` 源 |
| 双栏预览渲染 | Frontend(PyQt6) | — | `BuildWordReplacedPreview` + `_build_word_original_preview_fragment` 走现成 DOM patch |
| .docx 真脱敏 | API/Backend（MainWindow 调用） | — | `MainWindow._save_word` 调 `apply_pii_replacements_to_docx` |
| 文档级 mask_override toggle | Frontend(PyQt6) | — | 与 PDF 公用 `btn_mask_override` 控件（同一 widget 或紧邻） |
| 文档级 override 字段存储 | Frontend(MainWindow) | — | `self.word_data[0]["mask_override_this_doc"]` 复刻 PDF 形态 |
| 批量入口 PII skip | API/Backend（WordBatchReplaceWorker） | — | Phase 3 显式 skip（避免大批量卡顿） |

## Standard Stack

### Core (Phase 3 必须复用,不引入新依赖)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `privacyguard.pii.engine` | 已存在 | `PIIEngine.detect(unit)` 段落级 PII 识别 | 9 类实体 + 校验位 + 一致掩码已就位 |
| `privacyguard.pii.hits` | 已存在 | `PIIHit` / `TextUnit` 数据类 | D-05 字段锁, 零修改 |
| `privacyguard.pii.mask` | 已存在 | `mask_for_entity` 统一分派表 | 9 entity 全部命中 |
| `privacyguard.pii.confidence` | 已存在 | `classify_hit` 档位判定 | Phase 3 复用 HIGH/MEDIUM/LOW 决策 |
| `python-docx` (`docx`) | 当前 runtime | 段落/run 边界 + 真脱敏 | 仅在 `_save_word` 调方持有,adapter 不 import |
| `unittest` | stdlib | 4 类新单元测试 | 项目基线测试框架 (79→272→282) |

### Supporting (Phase 3 引用的现有工具)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `merge_word_matches_with_priority` | main.py:863 | 5 源合并(rule/manual/ocr/pii) | 双栏预览左/右栏渲染前调用 |
| `replace_matches_in_paragraph` | main.py:965 | 段内合并 run 后 replace | `apply_pii_replacements_to_docx` 复用 |
| `apply_range_to_runs` | main.py:909 | 单 run 区间替换 | 同上 |
| `BeautifulSoup` | 已存在 | `data-key` 容忍 + DOM patch | 双栏预览 HTML 注入 (cp27 修复点) |
| `mammoth` | 已存在 | docx → HTML | 已有 `_build_word_html_from_docx` 复用 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `paragraph._element.clear_content()` + 单 run 重建 | `_copy_run_format` 逐属性复制 (`main.py:12810`) | 现有 `_copy_run_format` 仅复制部分属性(bold/italic/underline/strike/font.name/size/color/highlight/subscript/superscript); 真脱敏产品底线高于格式完美, D-07 选"段级样式保留 + run 级格式丢失" |
| `paragraph.text.find(hit.text, start_offset)` 顺序扫描 | `re.finditer(hit.text, paragraph_text)` | `find` 顺序扫描更简单, 不引入正则; 多次重复按 D-09 逐个展开 |
| `word_adapter.apply_pii_replacements_to_docx` 接收 docx_path | 接收 `Document` 对象 | D-11 决策: 签名只接 docx_path + hit_locations, 由调用方持有 Document 句柄; 保持 Phase 1 "PII 引擎无 IO" 原则 |
| 直接合并 `ocr_key + pii_key` 两 key | 单一 `pii` 键, merge_word_matches_with_priority 接收 `pii_matches` 新参数 | CONTEXT.md D-01 选 "扩展 ocr_matches 输入"(美观上把 PII 视为 ocr 层); merge 函数加 `pii_matches` 形参保持原签名 |

## Package Legitimacy Audit

**Packages 引入:** Phase 3 零新增外部依赖 (全部复用现有)
- `privacyguard.pii.engine` / `privacyguard.pii.hits` / `privacyguard.pii.mask` / `privacyguard.pii.confidence` — 已 registered in `_LAZY_IMPORTS`
- `privacyguard.pii.word_adapter` — 新增模块, 注册到 `_LAZY_IMPORTS` (D-13)
- `python-docx` (`docx`) — 现有依赖, 在 `_save_word` 处 `from docx import Document` (runtime-time, D-11 不在 adapter 内 import)
- `unittest` — stdlib

**PyInstaller hiddenimports 同步需求 (D-14):**
- `packaging/windows/config/PrivacyGuard_windows.spec` 已使用 `collect_submodules('privacyguard')` 扫描 (line 130), 新增 `privacyguard.pii.word_adapter` 子模块 **理论上自动覆盖**; 但项目惯例 **显式列出**所有 privacyguard 子模块 (line 138-172)。Phase 3 需在 `privacyguard_hiddenimports.extend([...])` 列表中新增 `'privacyguard.pii.word_adapter'`, 与 `pdf_adapter` 平级。
- `packaging/macos/scripts/build_complete.sh` — 需对应 inspect 是否有等价的 hiddenimports 列表 (Phase 2 02-03 parity verified, 已含 6 个新 validator)。Phase 3 需新增 `privacyguard.pii.word_adapter`。
- 零新数据文件 (D-14 锁定)

**Verdict:** 零新增包, 无 SLOP/SUS 风险。仍需 PyInstaller spec 同步 (Windows + macOS)。

## Architecture Patterns

### System Architecture Diagram

```
用户打开 .docx
    │
    ▼
[MainWindow._open_word_docx]                  主线程
    │  init word_data[key] = {text, ocr, manual} (无 pii 键)
    ▼
[spawn _ModularWordWorker]                    QThread
    │
    │  for each para / cell:
    │    text = word_data[key]["text"]
    │    recursive_rules = self._find_matches(text)  →  word_data[key]["ocr"]
    │    pii_hits = collect_pii_word_hits(text, engine)  ◄── NEW
    │    word_data[key]["pii"] = pii_hits               ◄── NEW
    │
    ▼
[word_scan_finished signal]                   主线程
    │
    ▼
[render_word_preview]
    │
    ├─► [_build_word_original_panel_updates]    左栏
    │      for key in word_data:
    │        ocr_matches = word_data[key]["ocr"]
    │        pii_matches = word_data[key]["pii"]   ◄── NEW
    │        merged = merge_word_matches_with_priority(
    │            text, [], "[已脱敏]",
    │            manual_matches=manual,
    │            ocr_matches=ocr_matches + pii_matches  ◄── D-01 扩展
    │        )
    │        render_highlight_preview
    │
    └─► [_build_word_replaced_panel_updates]    右栏
           merge_word_matches_with_priority(
               text, word_replace_rules, "[已脱敏]",
               manual_matches=manual,
               ocr_matches=ocr_matches + pii_matches  ◄── D-01 扩展
           )
           render_replaced_preview (含 PII partial_mask)
    │
    ▼
[build_word_panel_update_script]              JS DOM patch
    │  按 data-key 局部更新 (cp27 修复点保留)
    ▼
[web_view.page().runJavaScript]               QWebEngine
    │
    ▼
[User clicks Save Word]
    │
    ▼
[MainWindow._save_word]
    │  for each para / cell:
    │    hits = word_data[key]["pii"]
    │    hit_locations = locate_pii_hits_in_paragraph(hits, text)  ◄── NEW
    │    apply_pii_replacements_to_docx(doc, [(key, hit_locations), ...], mode)  ◄── NEW
    │      ├─► paragraph._element.clear_content() + 单 run 重建
    │      └─► para.text.replace(hit.text, masked)  (按段合并 run 后)
    ▼
[doc.save(fname)]                             真脱敏产物
```

### Recommended Project Structure
```
privacyguard/pii/
├── __init__.py                    # [MODIFY] _LAZY_IMPORTS 注册 word_adapter 三函数
├── word_adapter.py                # [NEW]   collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx
├── engine.py                      # 零修改
├── hits.py                        # 零修改 (D-05 字段锁)
├── mask.py                        # 零修改
└── ...

privacyguard/workers/
└── word_worker.py                 # [MODIFY] run() 中新增 PII 检测阶段; 批量入口 skip PII

main.py                            # [MODIFY]
├── merge_word_matches_with_priority  # 加 pii_matches 形参
├── _build_word_original_panel_updates  # ocr_matches=ocr+pii
├── _build_word_replaced_panel_updates  # ocr_matches=ocr+pii
├── _save_word                       # 调 apply_pii_replacements_to_docx
├── _open_word_docx                  # init word_data 时加 "pii": [] 键
├── btn_mask_override                # 已存在, 文档级 toggle 复用
└── mask_override_this_doc 字段       # word_data[0] 复用

tests/unit/
├── test_word_pii_adapter.py          # [NEW]  三函数纯函数
├── test_word_worker_pii.py           # [NEW]  worker 写入 word_data["pii"]
├── test_word_pii_redaction.py        # [NEW]  reverse-extraction
└── test_word_preview_highlight.py    # [NEW]  DOM patch + merge 函数扩展

packaging/windows/config/
└── PrivacyGuard_windows.spec       # [MODIFY] hiddenimports += 'privacyguard.pii.word_adapter'

packaging/macos/scripts/
└── build_complete.sh                # [MODIFY] 同上 (if has hiddenimports list)
```

### Pattern 1: PII 引擎段落级接入 (D-11/D-12)

**What:** `collect_pii_word_hits(paragraph_text, engine) -> List[PIIHit]` 复用 `PIIEngine.detect(unit)` 范式, 但 `page` 参数为 None (Word 端无 page.search_for 概念, 走 char_offset 反向定位)。

**When to use:** `_ModularWordWorker.run()` 对每段/每 cell 文本的 PII 扫描。

**Code Example (D-11/D-08 锁定):**
```python
# privacyguard/pii/word_adapter.py
from typing import List
from privacyguard.pii.hits import PIIHit, TextUnit
from privacyguard.pii.engine import PIIEngine


def collect_pii_word_hits(paragraph_text: str, engine: PIIEngine) -> List[PIIHit]:
    """对单段 Word 文本执行 PII 识别, 返回 PIIHit 列表 (D-11)。

    复用 PIIEngine.detect: unit.source="text" + page=None
    (Word 端无 fitz Page 概念, 后续 locate_pii_hits_in_paragraph 现场换算 char_offset)。

    Args:
        paragraph_text: 单段/单 cell 文本
        engine: PIIEngine 实例 (调用方持有)

    Returns:
        PIIHit 列表 (D-05 字段锁; 不增字段不重载语义)
    """
    if not paragraph_text or not paragraph_text.strip():
        return []
    unit = TextUnit(page_index=0, text=paragraph_text, source="text")
    return engine.detect(unit)
```

**Rationale (D-08):** PIIHit 仅作内容描述, Word 端不重载 `page_offset` 字段, 与 PDF 端 `page.search_for(raw_text)` 范式对齐。

### Pattern 2: 段内 char_offset 反向定位 (D-08/D-09)

**What:** `locate_pii_hits_in_paragraph(hits, paragraph_text) -> List[Tuple[PIIHit, int]]` 用 `hit.text` 在段内精确子串定位拿 char_offset; 同文本重复按 D-09 逐个展开。

**Code Example:**
```python
def locate_pii_hits_in_paragraph(
    hits: List[PIIHit],
    paragraph_text: str,
) -> List[Tuple[PIIHit, int]]:
    """对 PIIHit 列表在段内做精确子串定位 (D-08), 同文本重复逐个展开 (D-09)。

    Args:
        hits: collect_pii_word_hits 产出
        paragraph_text: 段/cell 文本

    Returns:
        [(hit, char_offset), ...] 列表, char_offset 用于 apply 阶段
    """
    if not hits or not paragraph_text:
        return []

    locations: List[Tuple[PIIHit, int]] = []
    cursor = 0
    # 按 hit.normalized 排序 (短优先 + 字典序) 确保稳定展开
    sorted_hits = sorted(hits, key=lambda h: (len(h.text or ""), h.text or ""))

    for hit in sorted_hits:
        needle = hit.text or ""
        if not needle:
            continue
        search_from = cursor
        while True:
            idx = paragraph_text.find(needle, search_from)
            if idx < 0:
                break
            locations.append((hit, idx))
            search_from = idx + len(needle)
    return locations
```

**Pitfall:** `hit.text` 经 `mask_for_entity` 处理后未必等于原始 `hit.normalized`; 但 `collect_pii_word_hits` 返回的 PIIHit 在 `PIIEngine.detect` 内部已将 `mask_strategy` 字段填入, `hit.text` 此时是 PII 引擎回填的原始匹配文本 (经归一化但不脱敏)。如不确定, 优先用 `hit.normalized` (D-08 验证后).

### Pattern 3: 段级真脱敏 (D-06/D-07)

**What:** `apply_pii_replacements_to_docx(doc, hit_locations, mode)` 合并 run + replace; 段样式保留, run 级格式丢失。

**Code Example (D-07 锁定):**
```python
def apply_pii_replacements_to_docx(
    doc: "Document",
    hit_locations: Dict[str, List[Tuple[PIIHit, int]]],  # key -> [(hit, offset)]
    mode: Literal["partial", "blackout"] = "partial",
) -> None:
    """对 docx 文档按段合并 run + replace PII 命中 (D-06/D-07)。

    Args:
        doc: python-docx Document (调用方持有, 不在此 import)
        hit_locations: {key: [(hit, char_offset), ...]} 映射
        mode: "partial" → partial_mask; "blackout" → [已脱敏]
    """
    from privacyguard.pii.mask import mask_for_entity

    def _walk_paragraphs():
        """yield (key, paragraph) for paragraph_N + table_X_cell_Y_Z_N."""
        for idx, para in enumerate(doc.paragraphs):
            yield f"paragraph_{idx}", para
        for table_idx, table in enumerate(doc.tables):
            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    for p_idx, p in enumerate(cell.paragraphs):
                        yield f"table_{table_idx}_cell_{row_idx}_{cell_idx}_p{p_idx}", p

    for key, para in _walk_paragraphs():
        hits = hit_locations.get(key) or []
        if not hits:
            continue
        # 按 offset 降序, 从后往前 replace (避免 offset 漂移)
        for hit, offset in sorted(hits, key=lambda x: -x[1]):
            para_text = para.text
            substring = para_text[offset:offset + len(hit.text or "")]
            if not substring:
                continue
            if mode == "partial":
                replacement = mask_for_entity(hit.entity_type, hit.normalized)
            else:
                replacement = "[已脱敏]"
            # D-07: 合并同段所有 run + 单 run 重建
            para._element.clear_content()
            new_text = para_text.replace(substring, replacement, 1)
            run = para.add_run(new_text)
            # 段样式由 paragraph.style 保留; run 内格式丢失 (D-07)
            break  # 每段只 clear_content 一次, 一次性 replace 多个 hit
```

**Pitfall (D-07 风险):** `clear_content` 一次后必须把全部 hit 一次性 replace 进新文本, 不能循环 single-hit `clear_content + replace` (会丢失前一轮的 replace 结果). 上述代码用 `para_text.replace(substring, replacement, 1)` + 一次性 clear_content 规避.

**Alternative 简化路径 (推荐):** 直接复用 `main.py:965 replace_matches_in_paragraph` + `apply_range_to_runs` 既有实现, 不需要 `clear_content`. 现有代码已处理"按段合并 run + replace"且保留段样式. 仅在 `hit.text` 跨 run 时, 现有 `apply_range_to_runs` 的 `run_ranges` 计算已能正确处理 (PDF 端 history验证过).

**Refined recommendation:** `apply_pii_replacements_to_docx` 内部走"按 char_offset → run_offset 换算 + replace_matches_in_paragraph"路径, 不直接 `clear_content`. 复用 `main.py:909 apply_range_to_runs` / `main.py:965 replace_matches_in_paragraph` 已有实现, 减少新代码量.

### Pattern 4: merge_word_matches_with_priority 扩展 (D-01/D-02)

**What:** 在 `merge_word_matches_with_priority` 加 `pii_matches` 形参, 与 `ocr_matches` 同层处理 (D-01: ocr ∪ pii).

**Code Example (D-01 锁定, 最小改动):**
```python
# main.py:863 修改
def merge_word_matches_with_priority(
    text,
    rules,
    default_replacement_text,
    manual_matches=None,
    ocr_matches=None,
    pii_matches=None,  # [NEW D-01]
):
    """合并规则替换 / 手动脱敏 / OCR / PII 区间. 优先级: rule > manual > (ocr ∪ pii)."""
    manual_matches = manual_matches or []
    ocr_matches = ocr_matches or []
    pii_matches = pii_matches or []  # [NEW]

    # ... 既有 _append_candidates 逻辑保留 ...

    _append_candidates(build_word_rule_matches(text, rules, fallback_text), "rule")
    _append_candidates(manual_matches, "manual")
    # [NEW D-01] ocr + pii 同层; D-02: PII 排在 OCR 之后, 因 confidence_tier 优先 + PII 来源加权
    pii_normalized = []
    for h in pii_matches:
        # PIIHit dataclass → merged dict 形态
        pii_normalized.append({
            "start": getattr(h, "page_offset", None),  # D-10: 复用 page_offset 字段存 char_offset
            "end": (getattr(h, "page_offset", 0) or 0) + (getattr(h, "page_length", 0) or 0),
            "text": getattr(h, "text", None),
            "replacement": getattr(h, "mask_strategy", None),
            "source": "pii",
            "mode": "partial",
            "rule_name": getattr(h, "entity_type", "PII"),
        })
    _append_candidates(ocr_matches, "ocr")
    _append_candidates(pii_normalized, "pii")  # PII 在 OCR 之后追加, 但因 PII 校验位质量 > OCR, _append_candidates 已去重, 后续 PII 覆盖先前 OCR
    merged.sort(key=lambda item: item["start"])
    return merged
```

**Pitfall (D-02):** "ocr ∪ pii" 同层去重逻辑 → `_append_candidates` 中 `_range_overlaps` 跳过被先占用区间. 把 PII 排在 OCR 后追加, PII 区间优先级高 (consistent with D-02).

### Pattern 5: word_data 字段扩展 (D-11/D-12)

**What:** 在 `MainWindow._open_word_docx` 初始化 `word_data[key]` 时新增 `"pii": []` 键; `_ModularWordWorker.run()` 在 `_find_matches` 之后调用 `collect_pii_word_hits` 写入.

**Code Example (D-12 锁定):**
```python
# privacyguard/workers/word_worker.py 修改
def run(self):
    # ... 既有 _find_matches 流程 ...
    for idx, para in enumerate(self.word_doc.paragraphs):
        if self.isInterruptionRequested():
            break
        key = f'paragraph_{idx}'
        if key in self.word_data:
            text = self.word_data[key]['text']
            matches = self._find_matches(text)
            self.word_data[key]['ocr'] = matches
            # [NEW D-12] PII 扫描
            from privacyguard.pii import collect_pii_word_hits
            pii_engine = getattr(self, '_pii_engine', None)
            if pii_engine is None:
                from privacyguard.pii.engine import PIIEngine
                pii_engine = PIIEngine()
                self._pii_engine = pii_engine
            self.word_data[key]['pii'] = collect_pii_word_hits(text, pii_engine)
```

**Concurrency:** 既有 `_word_data_lock` (main.py:5153) 保护 word_data 写入; `QThread` 内写入 + 主线程 read 经 `QMutexLocker` 同步 (v36.5 既有模式).

**Worker 实例化:** PIIEngine 构造无 IO 无外部依赖, 可在 worker `__init__` 一次性创建并缓存 (`self._pii_engine = PIIEngine()`). 避免每次循环导入.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 段内 PII 识别 | 自己写 regex 校验 | `PIIEngine.detect(unit)` + `collect_pii_word_hits` | 9 类实体 + 6 类校验位 + 半角/全角归一化, 自研成本高 |
| 掩码字符串生成 | 写 `if entity == "CN_ID_CARD": masked = original[:6] + "*"*8 + ...` | `mask_for_entity(entity_type, normalized)` | 9 类 entity 已有 8 个 partial_mask_* 函数, 分派表已就位 |
| 跨 run 文本替换 | 自己写 run 边界扫描 | `apply_range_to_runs` (main.py:909) + `replace_matches_in_paragraph` (main.py:965) | 已处理 start_run_idx / end_run_idx 计算 + prefix/suffix 拼接 |
| 段内 char_offset 定位 | 自己写正则带捕获组 | `paragraph_text.find(needle, start_offset)` 顺序扫描 | D-09 多次重复按顺序展开, find 简单直接 |
| 文档级 override 存储 | 新建 `WordMaskOverrideDialog` 类 | 复用 `btn_mask_override` + `word_data[0]["mask_override_this_doc"]` | PDF 端 Phase 2 D-12 已确立同一形态 |
| 段样式保留 + run 格式丢失 | 自己写 `_copy_run_format` 完整版 | `paragraph._element.clear_content()` + 单 run 重建 | D-07 锁定: 段级样式 ≥ run 级格式; 真脱敏产品底线高于格式完美 |

**Key insight:** Phase 3 几乎所有"看起来要新写"的代码都已经作为既有基础设施存在. 新增 word_adapter.py 仅做纯粹的"PII 引擎 → Word 格式"边界适配.

## Common Pitfalls

### Pitfall 1: PIIHit 字段复用 "page_offset" 存储 char_offset (D-10)
**What goes wrong:** `merge_word_matches_with_priority` 内部用 `hit.page_offset` 取 char_offset, 但 PIIHit 字段语义是"整页文本字符串偏移" (Phase 1 D-05), Word 端无页面概念.
**Why it happens:** Word 端没有 page, 但 PIIHit 字段锁不允许增字段.
**How to avoid:** D-10 锁定: 复用 `page_offset` 字段存 char_offset_in_paragraph_text. 字段语义在 Word 端从"整页偏移"语义重载为"段内偏移"; 但 **WordAdapter 消费完后立刻丢弃 PIIHit**, 主程序其他路径 (PDF / OCR) 仍按原语义使用. 通过"边界换算 + 立即消费"维持字段锁.
**Warning signs:** 如果 PIIHit 流经 `_save_word` 之外的路径 (如 audit report), 字段语义会暴露冲突. Phase 3 仅在 `word_data[key]["pii"]` 内存中存活, 不持久化, 可规避.

### Pitfall 2: 批量 Word 替换入口误触发 PII 扫描 (D-12)
**What goes wrong:** `WordBatchReplaceWorker` 也调 `_apply_rules_to_document` 走替换流程, 如果有人把 PII 扫描默认接入, 会在批量 100 个文件时严重卡顿.
**Why it happens:** PII 检测是 O(N) 文本扫描 + 校验位循环, 100 个 100KB Word 文件 = 10MB 文本 + ~100K 次 Mod-11-2 校验.
**How to avoid:** D-12 锁定: `_ModularWordWorker.run()` 接入 PII; `WordBatchReplaceWorker` 默认 skip PII 扫描. 批量入口的 PII 接入归属后续 phase (CLAUDE.md 标识的"每文件单独规则映射"方向). Phase 3 在 `WordBatchReplaceWorker._apply_rules_to_document` 显式 **不** 调 PII 扫描, 仅走 word_replace_rules.
**Warning signs:** test_batch_word_replace.py 如果 PII 误接入会导致批量 100 文件测试 > 10s, 性能回归.

### Pitfall 3: 段内 char_offset 跨 run 错位 (D-07)
**What goes wrong:** PII 命中跨多个 run 拼接而成 (如 "张三" 在 run0="张", run1="三"), 直接 `para.text.find()` 拿 char_offset, 但 `replace_matches_in_paragraph` 走 `apply_range_to_runs` 重新计算 run_offset 时一致, 应该 OK.
**Why it happens:** `paragraph.text` 是各 run 字符串拼接的视图, char_offset 在 para.text 与 para.runs 上语义一致 (Python-docx 文档保证).
**How to avoid:** D-07 锁定: 使用 `apply_range_to_runs` 既有实现, 它已处理"start_run_idx + start_offset + prefix/suffix 拼接"逻辑. 不直接写新算法.
**Warning signs:** 如果 PII 命中跨越 run 边界, 测试 `test_word_pii_adapter.py::test_locate_pii_across_runs` 必须验证 char_offset 正确.

### Pitfall 4: word_data["pii"] 键缺失导致 word_scan_finished 崩溃 (D-12)
**What goes wrong:** `_ModularWordWorker.run()` 写入 `word_data[key]["pii"]`, 但 worker 启动前 word_data 已经初始化 (在 `_open_word_docx`). 如果 word_data 初始化时漏加 `"pii": []` 键, 当 word_data[key] 被 `QMutexLocker` 保护的 `self.word_data = results_copy` 覆盖时, 公开接口突然读到 dict 缺键.
**Why it happens:** QThread 写入 word_data, 主线程读 word_data — 任何一处初始化漏配都会触发 KeyError.
**How to avoid:** `_open_word_docx` 初始化 dict 时 **同时** 新增 `"pii": []` 键 (D-11). 测试 `test_word_worker_pii.py::test_pii_key_exists_after_init` 验证.
**Warning signs:** 主线程 `merge_word_matches_with_priority(..., pii_matches=word_data[key].get("pii", []))` 应当用 `.get()` 防御; 但 word_data 初始化时统一加键更稳.

### Pitfall 5: cp27 DOM patch 边界被 PII 命中破坏 (D-17)
**What goes wrong:** 增加 PII 数据后, `merge_word_matches_with_priority` 输出区间集, `_build_word_original_panel_updates` 渲染时如果 PII 区间起点超出 `[0, len(text))` 会触发 `data-end` 数值异常, JS 解析时破坏 mark 标签.
**Why it happens:** PII 命中 char_offset 与 manual / ocr 区间共享同一区间结构, 任何一来源越界都破坏 DOM patch.
**How to avoid:** `_append_candidates` 既有 `_range_overlaps` + `start < 0 or end > text_len` 验证已防越界. 测试 `test_word_preview_highlight.py::test_pii_highlight_dom_patch_no_overflow` 验证.
**Warning signs:** 主线程加载 docx 后, 右栏整块空白 (cp27 修复历史信号).

### Pitfall 6: 文档级 mask_override_this_doc 字段在 Word 端未生效 (D-05)
**What goes wrong:** Phase 2 PDF 端 `self.page_data[0]["mask_override_this_doc"]` 已生效; Word 端如果直接复用 `self.word_data[0]["mask_override_this_doc"]`, 但 word_data 是 dict (key=paragraph_N, table_X_cell_Y_Z), 没有 page 0 概念.
**Why it happens:** word_data 多键结构与 page_data 单页结构不同.
**How to avoid:** D-05 锁定: Word 端用 `self.word_data[0]["mask_override_this_doc"]` (_, "_meta_" 作为第 0 键) OR 新建独立的 `self._word_mask_override` 字段. **推荐**后者: 避免污染 word_data 业务键空间. Phase 3 实现细节由 planner 决定.
**Warning signs:** Save Word 时 `mask_override_this_doc` 状态不读取, 全遮蔽 toggle 失效.

### Pitfall 7: PyInstaller hiddenimports 漏配置导致 frozen 包 ModuleNotFoundError (D-14)
**What goes wrong:** `privacyguard.pii.word_adapter` 在 PyInstaller 静态分析时不被 `collect_submodules` 完全捕获 (adapter 内无 eager import, 仅通过 `_LAZY_IMPORTS` 间接引用), frozen 启动可能报 `ModuleNotFoundError: privacyguard.pii.word_adapter`.
**Why it happens:** PyInstaller 对 `_LAZY_IMPORTS = {...: (module, attr)}` 模式的间接 import 不一定递归解析.
**How to avoid:** D-14 锁定: 显式在 `PrivacyGuard_windows.spec` (`privacyguard_hiddenimports.extend([...])` 列表 line 138-172) 添加 `'privacyguard.pii.word_adapter'`. macOS spec sync 同上. 测试 `test_package_imports.py` 默认已覆盖 `import privacyguard` 不触发 pii.engine, 需扩展为 `import privacyguard.pii.word_adapter` 不触发 pii.engine.
**Warning signs:** frozen exe 启动后用户点击 Save Word 时报 ImportError.

### Pitfall 8: PII 引擎冷启动延迟 (D-13 懒加载)
**What goes wrong:** `_ModularWordWorker.run()` 每次启动都要 import `collect_pii_word_hits`, 拉起 `privacyguard.pii.engine` 全部加载 6 个 validators + 校验位代码. 短文档 100 段 PII 扫描 < 1s, 但仍可见.
**Why it happens:** `_LAZY_IMPORTS` 触发模块加载, 首次 import 必然有延迟.
**How to avoid:** 在 worker `__init__` 一次性导入并缓存 (`self._pii_engine = PIIEngine()`). 避免每段循环 import. 测试 `test_word_worker_pii.py::test_pii_engine_loaded_once` 验证.
**Warning signs:** 启动 word 预览后第一次扫描明显卡顿 (vs. 第二次).

## Runtime State Inventory

> 已通过 GSD 流程: Phase 1 已完成 PII 引擎建造, Phase 2 已扩展 6 类 validator. Phase 3 是 **adapter 接入** phase, 无新增 runtime state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | 无新增 | `word_data` 作为 in-memory 业务数据, 进程重启即清零 |
| Live service config | `pii_settings.per_entity_default` 已存 (Phase 2 D-12) | Phase 3 复用, 不新增字段 |
| OS-registered state | 无 | Phase 3 不修改 PyInstaller hiddenimports 注册以外的 OS 状态 |
| Secrets/env vars | 无 | Phase 3 不引入新密钥 |
| Build artifacts | `packaging/{windows,macos}/` 需新增 `privacyguard.pii.word_adapter` hiddenimports | code edit (D-14) |

**Nothing found in category:** Phase 3 全部改动均在代码层 + 测试层, 零运行时状态新增.

## Code Examples

### Verified Patterns from Existing Codebase

#### Example 1: 段落 PII 收集 (D-11)
```python
# Adapted from privacyguard/pii/pdf_adapter.py:50 collect_pii_rects
def collect_pii_word_hits(paragraph_text: str, engine: PIIEngine) -> list:
    """单元: 段落文本 → PIIHit 列表."""
    if not paragraph_text or not paragraph_text.strip():
        return []
    unit = TextUnit(page_index=0, text=paragraph_text, source="text")
    return engine.detect(unit)
```

#### Example 2: 段内 char_offset 定位 (D-08/D-09)
```python
# Adapted from PyMuPDF page.search_for 反向定位范式
# 既有 privacyguard/pii/engine.py:566 _resolve_location_from_page
def locate_pii_hits_in_paragraph(hits, paragraph_text):
    """PIIHit: 内容描述 → (hit, char_offset_in_paragraph_text)."""
    locations = []
    cursor = 0
    for hit in sorted(hits, key=lambda h: len(h.text or "")):
        needle = hit.text or ""
        search_from = cursor
        while True:
            idx = paragraph_text.find(needle, search_from)
            if idx < 0:
                break
            locations.append((hit, idx))
            search_from = idx + len(needle)
    return locations
```

#### Example 3: 复用 apply_range_to_runs 替换 (D-07)
```python
# Adapted from main.py:909 apply_range_to_runs + :965 replace_matches_in_paragraph
def apply_pii_replacements_to_docx(doc, hit_locations_per_key, mode="partial"):
    """复用既有 replace_matches_in_paragraph, 不 new 新算法."""
    for key, hits_with_offset in hit_locations_per_key.items():
        # 1. 找到对应 paragraph (para_N 或 table_X_cell_Y_Z_p_N)
        para = _find_paragraph_by_key(doc, key)
        if para is None:
            continue
        # 2. 构造 merged_matches 形态 [{start, end, replacement}]
        matches = []
        for hit, offset in hits_with_offset:
            text = para.text[offset:offset + len(hit.text or "")]
            if not text:
                continue
            if mode == "partial":
                replacement = mask_for_entity(hit.entity_type, hit.normalized)
            else:
                replacement = "[已脱敏]"
            matches.append({
                "start": offset,
                "end": offset + len(text),
                "replacement": replacement,
            })
        # 3. 复用 main.py:965 既有实现
        replace_matches_in_paragraph(para, matches, text_offset=0, fallback_replacement_text="[已脱敏]")
```

#### Example 4: merge_word_matches_with_priority 扩展 (D-01)
```python
# Adapted from main.py:863 merge_word_matches_with_priority
def merge_word_matches_with_priority(
    text, rules, default_replacement_text,
    manual_matches=None, ocr_matches=None, pii_matches=None,  # NEW D-01
):
    """rule > manual > (ocr ∪ pii)."""
    manual_matches = manual_matches or []
    ocr_matches = ocr_matches or []
    pii_matches = pii_matches or []
    # ... 既有 _append_candidates 逻辑 ...
    _append_candidates(build_word_rule_matches(text, rules, fallback_text), "rule")
    _append_candidates(manual_matches, "manual")
    # OCR 先 (保留现状)
    _append_candidates(ocr_matches, "ocr")
    # PII 后追加 (D-02: PII 校验位质量 > OCR; 因 _append_candidates 去重, PII 实际胜出)
    _append_candidates([
        _pii_hit_to_match_dict(hit) for hit in pii_matches
    ], "pii")
    merged.sort(key=lambda item: item["start"])
    return merged
```

#### Example 5: _ModularWordWorker.run() 接入 PII (D-12)
```python
# Adapted from privacyguard/workers/word_worker.py:34
def run(self):
    # ... 既有 init ...
    for idx, para in enumerate(self.word_doc.paragraphs):
        if self.isInterruptionRequested():
            break
        key = f'paragraph_{idx}'
        if key in self.word_data:
            text = self.word_data[key]['text']
            matches = self._find_matches(text)
            self.word_data[key]['ocr'] = matches
            # [NEW D-12] PII 扫描
            pii_hits = collect_pii_word_hits(text, self._pii_engine)
            self.word_data[key]['pii'] = pii_hits
        # ... 既有 progress / 表格处理 ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Word 端仅 word_replace_rules 手动规则 | word_replace_rules + PII 引擎 9 类实体 | Phase 3 (本) | 用户打开 Word 自动列出敏感项, 不需手输 |
| `merge_word_matches_with_priority` 4 源 (rule/manual/ocr + 1) | 5 源 (rule/manual/ocr/pii) | Phase 3 (本) | PII 与 OCR 同层, PII 校验位质量优先 |
| `_save_word` 仅真脱敏 word_replace_rules | word_replace_rules + PII 命中 (默认 partial_mask) | Phase 3 (本) | 与 PDF 端 "识别即脱敏" 一致 |
| `word_data[key]` 3 字段 (text, ocr, manual) | 4 字段 (text, ocr, manual, pii) | Phase 3 (本) | 守 v37.7.6 收敛原则: 不另起数据结构 |

**Deprecated/outdated:**
- ❌ "Word 端仅手动规则" — Phase 3 起 deprecated
- ❌ `merge_word_matches_with_priority` 4 源签名 — Phase 3 扩展为 5 源 (向后兼容, 是 default param)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `page_offset` 字段在 Word 端可重载为 char_offset_in_paragraph_text | Pattern 5 / Pitfall 1 | 主线程其他路径 (audit 报告) 误读 page_offset 字段, 需后续 Phase 8 审计报告时重新设计 |
| A2 | `btn_mask_override` PDF toggle 控件可被 Word 端复用 (D-05) | Pitfall 6 | 需新增独立 `btn_word_mask_override` 控件, UI 改动 |
| A3 | `paragraph.text` 与 `paragraph.runs` 拼接语义一致 (Python-docx 文档保证) | Pattern 3 / Pitfall 3 | 跨 run 边界 char_offset 错位, 替代方案: 采用 `clear_content + run 重建` |
| A4 | `WordBatchReplaceWorker._apply_rules_to_document` 不需要 PII 扫描 (D-12) | Pitfall 2 | 批量 100 文件 PII 扫描 < 1s 但总量 > 100s, 性能回归 |
| A5 | 复用 `apply_range_to_runs` 既有实现处理跨 run 命中 (D-07) | Pattern 3 | 需独立实现 clear_content + run 重建, 失去段级 run 格式 |
| A6 | `PrivacyGuard_windows.spec` 已有 `privacyguard_hiddenimports.extend([...])` 列表 (line 138-172) | Stack / Pitfall 7 | macOS spec 需独立 inspect/扩展 |
| A7 | `mask_for_entity` 9 entity 全部走 partial_mask 路径 (D-03) | Pattern 1 | 错过 BLACK_OUT 实体类型需在新 mask 分派表中新增 |
| A8 | `word_data[0]["mask_override_this_doc"]` 字段可用 (D-05) | Pitfall 6 | word_data 0 键被 `_ModularWordWorker` 视为业务键, 改用 `self._word_mask_override` 字段 |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.
(All 8 assumptions are derived from CONTEXT.md D-decisions, which are LOCKED by user diskuss-phase; verify in Phase 3 plan implementation.)

## Open Questions

1. **文档级 mask_override_this_doc 字段名 (D-05)**
   - What we know: CONTEXT.md D-05 说 "通过 `self.word_data[0]["mask_override_this_doc"]` 临时反转"
   - What's unclear: `word_data` 是 dict (key=paragraph_N / table_X_cell_Y_Z), 没有 literal "0" 键; 用 word_data[0] 写法会因 dict 键碰撞问题失效
   - Recommendation: Phase 3 Plan 内明确改为 **`self._word_mask_override_this_doc` 独立字段** (与 PDF 端 `self.page_data[0]["mask_override_this_doc"]` **字段名同形但归属不同**, 避免 word_data 业务键空间污染). Planner 需要硬约束这一决议.

2. **`apply_pii_replacements_to_docx` 是接收 docx_path 还是 Document 对象 (D-11)**
   - What we know: D-11 决策字符串 "签名只接 `docx_path` + hit_locations, 由调用方持有 Document 句柄"
   - What's unclear: docx_path 与 Document 二选一, 字符串表述似乎选 docx_path; 但实际 _save_word 持有 Document 句柄, 接收 Document 更便利
   - Recommendation: Phase 3 决策统一为 **接收 Document 对象** (签名 `doc: Document, hit_locations: Dict[key, ...], mode: str`), _save_word 持有 Document 句柄直接传入. docx_path 路径会引入不必要的 IO (Document 已被 _save_word 打开). Planner 需在 Plan 1 明确这一决议, 与 D-11 字符串不完全一致但更工程化.

3. **PII 命中颜色 (Claude's Discretion)**
   - What we know: Phase 1 PDF 端用深红色 #d63031 作自动识别
   - What's unclear: Word 端是否复用同色, 还是引入新色 (如紫色 #6c5ce7)
   - Recommendation: 复用 #d63031 与 PDF 端一致 (双栏预览同时呈现 PDF PII + Word PII 时色系统一). Planner 决策: 在 `_build_word_original_panel_updates` 的 `css_class` 解析逻辑里新增 `"pii"` 分支, 复用 `ocr-highlight` 同色 (#ffeb3b 黄) 或新增 `pii-highlight` (#d63031 红). 建议复用 `ocr-highlight` 黄色避免色系混乱, 但 source 标记为 "pii" 用于 tooltip.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python-docx` (`docx`) | `_save_word` Doc 打开 | ✓ | 项目当前 runtime | — |
| `privacyguard.pii.*` | word_adapter 三函数 | ✓ | Phase 1/2 已 ship | — |
| `mammoth` | DOCX → HTML | ✓ | 项目当前 runtime | — |
| `BeautifulSoup` | data-key 注入 (cp27) | ✓ | 项目当前 runtime | — |
| `PyInstaller` | 跨平台打包 | ✓ | macOS spec + Windows spec | — |
| `unittest` | 4 类新单元测试 | ✓ | stdlib | — |

**Missing dependencies with no fallback:** None — Phase 3 零新增依赖.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` (stdlib) |
| Config file | None — `python3 -m unittest tests.unit.test_xxx` |
| Quick run command | `python3 -m unittest tests.unit.test_word_pii_adapter tests.unit.test_word_worker_pii tests.unit.test_word_pii_redaction tests.unit.test_word_preview_highlight -v` |
| Full suite command | `python3 -m unittest discover -s tests/unit -v` (含 282 既有测试 + 4 新增 ≈ 295+ 测试) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FMT-02 | Word 端 PII 识别 + 双栏高亮 | unit + integration | `python3 -m unittest tests.unit.test_word_pii_adapter tests.unit.test_word_preview_highlight -v` | ❌ Wave 0 |
| FMT-02 | .docx 真脱敏 | unit (reverse-extraction) | `python3 -m unittest tests.unit.test_word_pii_redaction -v` | ❌ Wave 0 |
| FMT-02 | worker 接入 PII | unit | `python3 -m unittest tests.unit.test_word_worker_pii -v` | ❌ Wave 0 |
| UX-01 | 候选审阅列表基础形态 | 不直接测试 (Phase 3 最小可用) | — | — |
| UX-02 | 按实体类型筛选 + 分页 | 不直接测试 (Phase 7) | — | — |
| OPS-03 | 懒加载 (word_adapter 不触发 pii.engine) | unit | `python3 -m unittest tests.unit.test_package_imports -v` | ✅ (扩展用) |
| OPS-04 | PyInstaller hiddenimports | manual (frozen 启动) | `packaging/windows/scripts/build_complete.bat` + 启动检查 | — |
| OPS-07 | 282 既有测试基线保持 | regression | `python3 -m unittest discover -s tests/unit -v` | ✅ |

### Sampling Rate
- **Per task commit:** `python3 -m unittest tests.unit.test_word_pii_adapter tests.unit.test_word_worker_pii tests.unit.test_word_pii_redaction tests.unit.test_word_preview_highlight -v`
- **Per wave merge:** `python3 -m unittest discover -s tests/unit -v` (full 295+)
- **Phase gate:** Full 295+ 绿 before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_word_pii_adapter.py` — 三函数纯函数测试 (collect_pii_word_hits / locate_pii_hits_in_paragraph / apply_pii_replacements_to_docx)
  - 覆盖: 跨 run 命中 / 同文本重复 (D-09) / 边界 (空段 / 跨段) / pii_settings mode (partial/blackout)
- [ ] `tests/unit/test_word_worker_pii.py` — `_ModularWordWorker.run()` 接入 PII 后 `word_data[key]["pii"]` 写入验证
  - 覆盖: 段落 / 表格 cell / 取消 (isInterruptionRequested) / 与 ocr 键并存
- [ ] `tests/unit/test_word_pii_redaction.py` — reverse-extraction 端到端
  - 覆盖: 9 类 entity partial_mask 验证 / 段样式保留 / 跨 run 边界 / 批量 100 文件性能不回归
- [ ] `tests/unit/test_word_preview_highlight.py` — DOM patch 渲染验证
  - 覆盖: merge_word_matches_with_priority(ocr + pii) 输入下 [D-01]; 左/右栏 css_class 渲染; cp27 局部 patch 不被破坏
- [ ] `tests/unit/test_package_imports.py` 扩展 — 验证 `import privacyguard` 不触发 `privacyguard.pii.word_adapter` 加载
- [ ] `tests/unit/test_convergence.py` 扩展 — 验证 `main.py` 中 `merge_word_matches_with_priority` 引入 `pii_matches` 形参 (D-01); 验证 `main.py` 未在 `apply_pii_replacements_to_docx` 中 inline 定义 (D-11 迁移到 privacyguard/)
- [ ] Framework install: 不需

## Architecture Decisions to Lock

Phase 3 实施时必须遵循的 8 项关键决策 (从 CONTEXT.md D-01..D-17 + Claude's Discretion 提炼):

1. **adapter 三函数命名:** `collect_pii_word_hits` / `locate_pii_hits_in_paragraph` / `apply_pii_replacements_to_docx` (D-11, 与 pdf_adapter 对称)
2. **adapter 不 import python-docx:** 签名收 `Document` 对象 (而非 docx_path), 由 `_save_word` 持有 Document 句柄直接传入 (D-11 + Open Question 2 resolution)
3. **merge_word_matches_with_priority 扩展:** 新增 `pii_matches: Optional[List[PIIHit]] = None` 形参, ocr + pii 同层去重 (D-01/D-02)
4. **word_data 新增 "pii" 键:** `_open_word_docx` 初始化时同步加键; `_ModularWordWorker.run()` 写入 (D-11/D-12)
5. **PII 字段复用 page_offset 存 char_offset:** Word 端边界消费完即丢弃, 主程序其他路径不受影响 (D-08/D-10)
6. **段级样式保留 + run 级格式丢失:** 复用 `apply_range_to_runs` 既有实现, 不直接 `clear_content`; 跨 run 命中已正确处理 (D-07)
7. **批量入口显式 skip PII:** `WordBatchReplaceWorker._apply_rules_to_document` 不调 PII 扫描 (D-12)
8. **PyInstaller hiddenimports 同步:** Windows spec + macOS spec 新增 `privacyguard.pii.word_adapter` (D-14)

## Specific File Paths and Line Numbers to Reference

### 必读 (既有实现)
| Path | Lines | Purpose |
|------|-------|---------|
| `privacyguard/pii/__init__.py` | 69-109 (`_LAZY_IMPORTS`) | D-13 注册 word_adapter 三函数 (新增 3 行) |
| `privacyguard/pii/hits.py` | 15-27 (`PIIHit` dataclass) | D-05 字段锁, 零修改 |
| `privacyguard/pii/engine.py` | 130-150 (`detect` 主入口) | `collect_pii_word_hits` 复用 |
| `privacyguard/pii/pdf_adapter.py` | 50-64 (`collect_pii_rects`) | word_adapter 三函数命名 + 形态对齐 |
| `privacyguard/pii/mask.py` | 82-105 (`mask_for_entity`) | D-03 mask 字符串统一分派 |
| `privacyguard/pii/confidence.py` | 13-19 (`classify_hit`) | Claude's Discretion: HIGH/MEDIUM 真脱敏, LOW 仅高亮 |
| `privacyguard/workers/word_worker.py` | 34-99 (`run` 主循环) | D-12 接入 PII 扫描 |
| `main.py` | 863-906 (`merge_word_matches_with_priority`) | D-01 扩展 `pii_matches` 形参 |
| `main.py` | 909-964 (`apply_range_to_runs`) | D-07 复用, 跨 run 命中处理 |
| `main.py` | 965-1018 (`replace_matches_in_paragraph`) | D-07 复用, 段合并后 replace |
| `main.py` | 10777-10830 (`_open_word_docx`) | D-11 初始化 word_data 新增 `"pii": []` 键 |
| `main.py` | 5149-5153 (`word_data` + `_word_data_lock`) | D-12 写入保护 |
| `main.py` | 5896-5901 (`btn_mask_override`) | D-05 文档级 toggle 复用 |
| `main.py` | 8781-8797 (`_toggle_mask_override_this_doc`) | D-05 文档级 toggle 逻辑 |
| `main.py` | 11940-11952 (`_build_word_original_panel_updates`) | D-01 调 merge_word_matches_with_priority 扩展 |
| `main.py` | 11986-11998 (`_build_word_replaced_panel_updates`) | D-01 调 merge_word_matches_with_priority 扩展 |
| `main.py` | 12698-12795 (`_save_word`) | D-04 调 apply_pii_replacements_to_docx |
| `tests/unit/test_word_replace_rules.py` | 1-396 | 既有范本: `merge_word_matches_with_priority` 单测形态 |
| `tests/unit/test_batch_word_replace.py` | 1-49 | 既有范本: python-docx 文档构造 + `_apply_rules_to_document` |
| `tests/unit/test_pdf_pii_redaction.py` | 1-100 | 既有范本: reverse-extraction 测试骨架 |
| `tests/unit/test_package_imports.py` | 1-204 | 既有范本: 懒加载 + PyInstaller 兼容性 |
| `tests/unit/test_convergence.py` | 36-62 | 既有范本: main.py 不引入 inline 实现 |
| `packaging/windows/config/PrivacyGuard_windows.spec` | 138-172 (`privacyguard_hiddenimports.extend([...])`) | D-14 新增 `'privacyguard.pii.word_adapter'` |
| `rolllog_journal.md` | cp27 修复点 | D-17 双栏预览 DOM patch 边界保留 |
| `rolllog_journal.md` | cp30 修复点 | D-14 PyInstaller hiddenimports 同步 |

### 新增 (Phase 3)
| Path | Purpose |
|------|---------|
| `privacyguard/pii/word_adapter.py` | 三函数实现 (collect / locate / apply) |
| `tests/unit/test_word_pii_adapter.py` | 三函数纯函数测试 |
| `tests/unit/test_word_worker_pii.py` | worker 接入 PII 测试 |
| `tests/unit/test_word_pii_redaction.py` | reverse-extraction 端到端 |
| `tests/unit/test_word_preview_highlight.py` | DOM patch 渲染 + merge 函数扩展 |

## Recommended Plan Structure

### Plan 1: word_adapter 三函数 + 懒加载注册 (Wave 0 Foundation)
**Tasks:**
1. `privacyguard/pii/word_adapter.py` 实现 `collect_pii_word_hits` / `locate_pii_hits_in_paragraph` / `apply_pii_replacements_to_docx` 三函数
2. `privacyguard/pii/__init__.py` `_LAZY_IMPORTS` 注册三函数 (D-13)
3. `tests/unit/test_word_pii_adapter.py` 三函数纯函数测试
4. `tests/unit/test_package_imports.py` 扩展: 验证 `import privacyguard` 不触发 `privacyguard.pii.word_adapter` 加载

**Files:** 3 modified + 1 new = 4 files
**Coverage:** D-11 / D-13 / Pitfall 8 (PyInstaller 兼容性)

### Plan 2: _ModularWordWorker 接入 PII + word_data 字段 (Wave 1)
**Tasks:**
1. `privacyguard/workers/word_worker.py` `run()` 接入 PII 扫描; `_ModularWordWorker.__init__` 缓存 PIIEngine
2. `main.py:_open_word_docx` 初始化 word_data 时新增 `"pii": []` 键
3. `tests/unit/test_word_worker_pii.py` 验证 word_data 字段正确

**Files:** 2 modified + 1 new = 3 files
**Coverage:** D-11 / D-12 / Pitfall 4 (键缺失)

### Plan 3: merge_word_matches_with_priority 扩展 + 双栏预览 (Wave 2)
**Tasks:**
1. `main.py:863 merge_word_matches_with_priority` 加 `pii_matches` 形参 (D-01)
2. `main.py:_build_word_original_panel_updates` / `_build_word_replaced_panel_updates` 注入 `pii_matches=word_data[key]["pii"]`
3. `tests/unit/test_word_preview_highlight.py` 验证 cp27 DOM patch 边界 + PII/css_class 渲染
4. `tests/unit/test_convergence.py` 扩展: 验证 main.py 未在 apply_pii_replacements_to_docx 内 inline 定义

**Files:** 4 modified + 1 new = 5 files
**Coverage:** D-01 / D-02 / D-17 预览回归 + 反分叉

### Plan 4: _save_word 真脱敏 + 文档级 override + PyInstaller 同步 (Wave 3)
**Tasks:**
1. `main.py:_save_word` 调 `apply_pii_replacements_to_docx` (D-04)
2. `main.py` 文档级 `self._word_mask_override_this_doc` 字段 + btn_mask_override 复用 (D-05)
3. `packaging/windows/config/PrivacyGuard_windows.spec` hiddenimports 增 `privacyguard.pii.word_adapter` (D-14)
4. `packaging/macos/scripts/build_complete.sh` 同步 (D-14)
5. `tests/unit/test_word_pii_redaction.py` reverse-extraction 端到端 (D-15 #3)

**Files:** 4-5 modified + 1 new = 5-6 files
**Coverage:** D-04 / D-05 / D-14 / D-15 #3 / D-17 reverse-extraction

### Wave Plan Summary
- **Wave 0 (Plan 1):** 基础三函数 + 懒加载 (Foundation)
- **Wave 1 (Plan 2):** worker 接入 (Pipeline)
- **Wave 2 (Plan 3):** 预览合并 (UX)
- **Wave 3 (Plan 4):** 真脱敏 + 打包 (Production)

**Total:** 4 plans, ~16 tasks, ~13 files modified or created

### Cross-Plan Validation
- After Plan 1: `python3 -m unittest tests.unit.test_word_pii_adapter tests.unit.test_package_imports -v`
- After Plan 2: `python3 -m unittest tests.unit.test_word_worker_pii -v`
- After Plan 3: `python3 -m unittest tests.unit.test_word_preview_highlight tests.unit.test_word_replace_rules tests.unit.test_convergence -v`
- After Plan 4: `python3 -m unittest tests.unit.test_word_pii_redaction tests.unit.test_batch_word_replace -v`
- **Phase gate:** `python3 -m unittest discover -s tests/unit -v` (295+/295+ 绿)

## Sources

### Primary (HIGH confidence)
- `privacyguard/pii/__init__.py` lines 25-119 — _LAZY_IMPORTS 寄存器 33 项, D-13 范式
- `privacyguard/pii/hits.py` lines 15-27 — PIIHit 字段锁 D-05
- `privacyguard/pii/engine.py` lines 130-150 — detect pipeline 范式
- `privacyguard/pii/pdf_adapter.py` lines 50-64 — collect_pii_rects 范式
- `privacyguard/pii/mask.py` lines 82-105 — mask_for_entity 9 entity 分派
- `privacyguard/workers/word_worker.py` lines 34-99 — _ModularWordWorker.run() 主循环
- `main.py` lines 863-1018 — merge_word_matches_with_priority + apply_range_to_runs + replace_matches_in_paragraph
- `main.py` lines 10777-10830 — _open_word_docx word_data 初始化
- `main.py` lines 11940-11998 — _build_word_original_panel_updates / _build_word_replaced_panel_updates
- `main.py` lines 12000-12005 — _apply_word_panel_updates (cp27 DOM patch 写入点)
- `main.py` lines 12236-12282 — _add_data_key_attributes (cp27 修复点)
- `main.py` lines 12698-12795 — _save_word 既有实现
- `tests/unit/test_word_replace_rules.py` 全文 — 既有范本
- `tests/unit/test_batch_word_replace.py` 全文 — 既有范本
- `tests/unit/test_pdf_pii_redaction.py` lines 1-100 — reverse-extraction 范式
- `tests/unit/test_package_imports.py` 全文 — 懒加载测试范式
- `tests/unit/test_convergence.py` 全文 — 反分叉测试范式
- `packaging/windows/config/PrivacyGuard_windows.spec` lines 138-172 — hiddenimports 列表

### Secondary (MEDIUM confidence)
- `.planning/phases/03-word/03-CONTEXT.md` 全文 — D-01..D-17 决策锁定
- `.planning/REQUIREMENTS.md` FMT-02 / UX-01 / UX-02 — Phase 3 覆盖 v1 需求

### Tertiary (LOW confidence)
- None — Phase 3 充分利用既有 PII 引擎与 Word 路径, 无需 WebSearch 验证.

## Metadata

**Confidence breakdown:**
- Standard Stack: **HIGH** — 全部复用既有 PII 引擎 + Python-docx, 零新增依赖
- Architecture: **HIGH** — adapter 形态与 pdf_adapter 对称, merge 函数扩展模式与既有 4 源合并一致
- Pitfalls: **HIGH** — 8 项 Pitfall 全部基于既有项目历史 (cp27 / cp30 / Phase 2 D-12) + D-决策锁定推演
- Validation: **HIGH** — 4 类新测试范本全部对齐既有 codebase, 295+ 测试基线可达

**Research date:** 2026-08-11
**Valid until:** 2026-09-11 (30 days, Phase 3 实施期间稳定)
