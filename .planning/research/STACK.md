# Stack Research — PII Detection, Excel, Image, Partial Masking

**Milestone:** PrivacyGuard v38.x — pure-local Chinese PII recognition engine + Excel/Image redaction
**Researched:** 2026-08-10
**Confidence:** MEDIUM-HIGH (web-verified library landscape; specific patch versions cross-checked against PyPI metadata but PyPI direct fetch was blocked, so confidence is HIGH for capability claims, MEDIUM for exact patch versions)
**Scope:** New Python libraries ONLY for the four additions. The existing PyQt6/PyMuPDF/RapidOCR/python-docx/mammoth stack is already validated and is NOT re-evaluated.

---

## 1. Executive Summary

Four pragmatic technology decisions:

1. **Excel read/write** — **`openpyxl` (single library)** for `.xlsx` round-tripping. Add **`xlrd==2.0.1`** ONLY if true legacy `.xls` (BIFF) support is needed; otherwise route `.xls` users through `libreoffice --headless --convert-to xlsx` (existing infrastructure already uses LibreOffice for `.doc` → `.docx`).
2. **Chinese PII detection** — **Hand-rolled ruleset, no Presidio, no spaCy**. The Presidio "package is small but spaCy model is huge" trap is real (~900 MB–1 GB with `en_core_web_lg`); Chinese support is community-contributed and unreliable. A `regex + checksum + dictionary + context-keyword` engine fits in <50 KB of Python.
3. **Checksum / validation** — Adopt a small **in-house `privacyguard/pii/validators/`** module that re-implements the four core algorithms (GB 11643 mod-11-2, Luhn, GB 32100 mod-31-3, simple date-of-birth extraction). The third-party `id-validator` PyPI package exists but is a single-maintainer project with weak typing; rolling our own is ~150 lines, fully testable, and removes a runtime dependency.
4. **Chinese dictionaries** — **Compile our own** from the public sources listed below. Static JSON files baked into the package (~100–500 KB total) replace the need for any dictionary dependency.
5. **Image file OCR redaction** — **Reuse existing `RapidOCR` + Pillow**. Add a thin worker (`privacyguard/workers/image_worker.py`) that loads JPG/PNG, runs RapidOCR, applies redaction either as (a) Pillow rectangle fill on the bitmap for irreversible "burn in", or (b) sidecar metadata XML for reversible marking. Two-pass verification: re-OCR the redacted output to confirm the sensitive token no longer surfaces.

This approach adds **one PyPI dependency** (`openpyxl`) and **one optional PyPI dependency** (`xlrd`) to the runtime. The PII engine, validators, and dictionaries are all in-tree. Estimated bundle-size delta: ~3 MB (openpyxl pure-Python) + ~1 MB (surnames/adcodes JSON) + ~0.5 MB (id-validator if adopted). Nothing in the existing OCR / ONNXRuntime / OpenCV toolchain changes.

---

## 2. Recommended Stack Additions

### 2.1 Core: Excel `.xlsx` Read/Write

| Library | Version | Purpose | Why Recommended |
|---|---|---|---|
| `openpyxl` | `>=3.1.5,<3.2` (latest stable line as of 2025) | `.xlsx` read + write with style/formula preservation | Only mainstream Python library that **reads AND writes existing `.xlsx` while preserving formulas, named styles, merged cells, and most conditional formatting**. Round-tripping is the core redaction use case — we modify specific cells in place and save back, not rebuild from scratch. Pure-Python (no compiled wheels needed). `data_only=False` keeps formulas as formulas, `data_only=True` gives us cached values for evaluation. |
| `xlrd` | `==2.0.1` (final release, **frozen** — do NOT upgrade to 2.0.2+) | Read legacy `.xls` (BIFF) files ONLY if needed | The last release that supports `.xls` in any form. xlrd 2.0+ **dropped `.xlsx` support** and the project is in maintenance mode. **Optional**: only add if we promise `.xls` round-trip; otherwise document the policy "convert via LibreOffice". |

### 2.2 Core: Chinese PII Detection Engine (in-tree, no new PyPI packages)

| Component | Module path | Purpose |
|---|---|---|
| Entity definitions registry | `privacyguard/pii/entities.py` | Declarative list of supported entity types, their regex + validator + dictionary anchors |
| Regex engine | `privacyguard/pii/regex_engine.py` | Pure-Python `re` module runner; produces `(start, end, entity_type, confidence)` tuples |
| Validators (in-tree) | `privacyguard/pii/validators/` | `id_card.py` (GB 11643 mod-11-2), `bank_card.py` (Luhn), `uscc.py` (GB 32100 mod-31-3), `luhn.py` (shared utility) |
| Dictionary lookup | `privacyguard/pii/dictionaries/` | Static `surnames.json`, `given_names.json`, `admin_divisions.json`, `org_keywords.json` |
| Context analyzer | `privacyguard/pii/context.py` | Sliding window — looks for context keywords (`公司`, `先生`, `女士`, `电话`, `身份证`, `地址`, `开户行`) within ±N chars of a candidate hit and bumps confidence |
| Pipeline orchestrator | `privacyguard/pii/engine.py` | Chains regex → validator → dictionary → context; returns deduplicated hit list with confidence tiers |
| Confidence model | `privacyguard/pii/confidence.py` | Three-tier: `HIGH` (checksum passes + format matches), `MEDIUM` (format matches only), `LOW` (context-only, name/address candidates) |

**Why in-house over Presidio:** see §3.2 — bundle weight, Chinese coverage, and the fact that we don't need NER for this domain (Chinese names can be dictionary-matched effectively given ~500 surnames and a corpus-derived stopword list of common given-name characters).

### 2.3 Supporting Libraries

| Library | Version | Purpose | When to Use |
|---|---|---|---|
| `pillow` | `>=12.1.1` (already pinned) | Image I/O for JPG/PNG OCR redaction; rectangle drawing for irreversible burn-in | Always — reuses the existing pin; no new dependency |
| `rapidocr-onnxruntime` | `==1.2.3` (already pinned) | OCR engine | Already imported; **must remain lazy-loaded** — call site moves into `privacyguard/workers/image_worker.py`, not into package `__init__.py` |
| `opencv-python` | `==4.13.0.92` (already pinned) | Optional — JPEG compression estimation, thresholding for redacted bitmap export | Already in requirements |

### 2.4 NOT Recommended (Avoid)

| Avoid | Why | Use Instead |
|---|---|---|
| `presidio-analyzer` | Pulls spaCy + `en_core_web_lg` = **~900 MB** model footprint; Chinese support is community regex packs; the framework's value is NER for free-form English text, which we are explicitly NOT solving | In-house regex + dictionary engine |
| `xlsxwriter` | **Write-only** — cannot read existing files. Round-tripping a user-supplied xlsx with formulas/styles is impossible | `openpyxl` |
| `pylightxl` | Zero deps but **drops all formatting**, no chart/image support, no formulas — wrong tool for redaction | `openpyxl` |
| `pandas.to_excel` (as primary writer) | Goes through openpyxl/xlsxwriter; convenient for DataFrames but **overwrites formulas** unless used very carefully; lazy evaluation kills precise cell-level redaction | `openpyxl` directly |
| `xlwt` | Last release 2017; write-only `.xls` | Convert to `.xlsx` and use `openpyxl` |
| `hanlp` / `lac` / `paddlenlp` | Heavyweight Chinese NER models (PyTorch/TensorFlow dependency, hundreds of MB) — violates "no heavy model" constraint | Dictionary + context approach |
| `pyexcel` / `pyexcel-xls` / `pyexcel-xlsx` | Wrapper libraries with stale maintenance and transitive dependency bloat | `openpyxl` + `xlrd` directly |

---

## 3. Detailed Reasoning

### 3.1 Excel: Why `openpyxl` and Not the Alternatives

**The core redaction pattern** is: load the user's `.xlsx`, iterate cells, mask specific cell values, write back, save. This requires **read-and-write-the-same-file**, which immediately disqualifies xlsxwriter (write-only) and pylightxl (no formatting preservation).

| Capability needed | openpyxl | xlsxwriter | pylightxl | pandas.to_excel |
|---|---|---|---|---|
| Read existing xlsx | YES | NO | YES | YES |
| Write back to same file | YES | NO | NO | YES |
| Preserve formulas | YES (default `data_only=False`) | N/A | NO | NO (overwrites) |
| Preserve styles/fonts/borders | YES (most) | N/A | NO | partial |
| Preserve merged cells | YES | N/A | partial | NO |
| Preserve column widths / row heights | YES | N/A | NO | NO |
| Lazy-load large sheets (`read_only=True`) | YES | N/A | YES | partial |
| Pure-Python (no C deps) | YES | YES | YES | NO (depends on numpy) |

**openpyxl wins on every row except pure-Python.** pandas depends on numpy which we don't want to add a second copy of (already present via OCR stack, but adding `pandas` brings DataFrame semantics we don't need). **Decision: openpyxl directly.**

**For `.xls` (legacy BIFF) files:** xlrd 2.0.1 still reads them but the project is unmaintained. The pragmatic policy is "ask the user to open and re-save as `.xlsx`", but if we want silent support, **add `xlrd==2.0.1` as an optional import** (try-import pattern) and route `.xls` through it. Alternative: use the LibreOffice path that the app already uses for `.doc` → `.docx`. **Recommendation: ship LibreOffice conversion path first; add `xlrd` only if real-world usage shows `.xls` is a recurring request.**

**PyInstaller implications:**
- `openpyxl` — already has a community hook at `pyinstaller-hooks-contrib/hooks/std-noncontrib/hook-openpyxl.py`. **No manual hiddenimport needed.**
- `xlrd` — ships as pure-Python source; PyInstaller auto-detects. No hook needed.
- Bundle size: `openpyxl` ≈ 3 MB on disk (pure-Python, many small modules). `xlrd` ≈ 1 MB.
- **CRITICAL**: Do NOT add `pandas` — its bundle weight (numpy + pandas + bottleneck/numexpr extras) is ~50–80 MB.

### 3.2 Chinese PII Detection: Why In-House Ruleset Beats Presidio

Microsoft Presidio is excellent for English free-text where NER adds value over regex. For Chinese structured-document PII it is the wrong tool:

1. **Bundle weight**: `presidio-analyzer` itself is ~50–100 MB but the realistic production install is `presidio-analyzer + spaCy + en_core_web_lg = ~900 MB`. With the optional `[transformers]` extra it balloons to **3–5 GB**. This is incompatible with the "small package, PyInstaller-friendly" constraint.

2. **Chinese support is not first-class**: Presidio ships built-in recognizers for US, Spain, Italy, UK, Singapore, Australia, India, Korea, Canada, Japan — but **not China**. Community Chinese recognizers exist on GitHub forks but are unmaintained regex packs with no formal review. We would effectively still be writing our own regex, just inside Presidio's wrapper API.

3. **NER for Chinese names is worse than dictionary for our use case**: A Chinese person's name is 2–4 characters, no capitalization, ambiguous against any 2-character common noun. A 500-entry surname dictionary + ~3000 high-frequency given-name list + context keywords (`先生`, `女士`, `先生：`, `姓名：`, `员工`) gives high precision/recall on documents (vs. web text) without model overhead. The PROJECT.md scope explicitly says "上下文型实体识别（姓名、机构名、详细地址）——基于关键词锚点 + 内置词典" — the requirements already point at this approach.

4. **Validation-driven confidence scoring is simpler than model probabilities**: An ID card number that passes the mod-11-2 checksum is a hard-true PII. A name in dictionary + context keyword is a soft-true. Model confidence scores don't add information on top of these two signals for our domain.

5. **Auditability**: A regex rule is debuggable in 30 seconds; a spaCy NER misfire requires checking model version, doc alignment, custom NER training. For a privacy tool whose failure mode is "leaks a phone number", deterministic rules win.

**Decision: pure in-tree engine.**

The engine architecture (see §2.2) is small enough to implement in one phase. The four validators are the only piece with subtle correctness concerns — GB 11643 mod-11-2 and GB 32100 mod-31-3 each fit in ~30 lines of tested Python.

**Optional third-party validation package for consideration**: `id-validator` on PyPI (jokamjohn/id-validator) implements ID card, bank card Luhn, and USCC validation. **However**: single-maintainer, weak typing, last release cadence is slow. We would write ~150 lines of validated Python and own the code forever; or we would take a soft dependency that could break in two years. **Recommendation: in-house**, but document `id-validator` as a "considered and rejected" alternative with the rationale above.

### 3.3 Checksum / Validation Algorithms

| Standard | Algorithm | Implementation Notes |
|---|---|---|
| GB 11643-1999 (居民身份证) | ISO 7064 MOD 11-2 (weighted sum + mapping to char table) | 17 body digits + 1 check char; weights 7-9-10-5-8-4-2-1-6-3-7-9-10-5-8-4-2; check char = `1 0 X 9 8 7 6 5 4 3 2`[sum mod 11] |
| Bank card (Luhn) | ISO/IEC 7812-1 Luhn | Standard implementation, ~10 lines |
| GB 32100-2015 (统一社会信用代码) | ISO 7064 MOD 31-3 | 18-char alphanumeric; 31-char check alphabet; weighted sum mod 31 |
| Phone number | 11 digits, known prefix list (13x/14x/15x/16x/17x/18x/19x, excluding 140/141/144/149 IoT prefixes) | Regex + prefix whitelist |
| Email | RFC 5322 lite regex | Standard |
| Date of birth extraction (from ID card) | Bytes 6–13 of 18-digit ID, parsed as YYYYMMDD | Optional — used to verify ID card is not from year > current |
| License plate (车牌) | Province char + letter + 5 alphanumerics | Optional, lower priority |

All four core algorithms are ~30 lines each and have public test vectors. **Roll in-house, add unit tests with known-good and known-bad fixtures.**

### 3.4 Chinese Surname and Place-Name Dictionaries

Compact open-data sources (chosen for PyInstaller bundle compatibility — small JSON files, not databases or CSV indexes):

| Dataset | Source | Size on disk | Format | License | Use |
|---|---|---|---|---|---|
| 百家姓 (single-char surnames) | GitHub `HALOSTAR/chinese_surnames`, supplemented with `wanghaisheng/Chinese-Names-Corpus` (~500 single + ~100 double-char surnames) | ~30 KB | JSON | MIT/CC-BY | Name detection, surname bank |
| 高频名 (given names) | Derived from `Chinese-Names-Corpus` filtered by frequency > threshold | ~50 KB | JSON | MIT | Name candidate scoring |
| 行政区划 (province/city/district) | GitHub `sysloser/adcode` (CSV, updated 2024-11-25) — we **subset to province + city + district only** (~3500 entries) | ~150 KB | JSON | MIT | Address detection |
| 组织机构关键词 | Hand-curated `公司/集团/银行/医院/学校/委员会/有限/股份` etc. + common abbreviations | ~10 KB | JSON | n/a | Organization candidate detection |
| 敏感关键词库 (context anchors) | Curated: `身份证/手机号/电话/地址/姓名/先生/女士/账号/卡号/密码/税号/开户行/身份证号/护照` | ~20 KB | JSON | n/a | Context scoring |

**Total dictionary bundle weight: ~260 KB.** Acceptable for PyInstaller.

**Maintenance policy**: ship a `privacyguard/pii/dictionaries/_refresh.py` script that pulls from upstream sources on demand (developer-only, not packaged into runtime). Dictionaries themselves are checked into the repo at known versions.

### 3.5 Image File OCR Redaction

**Reuse existing toolchain:**

1. **OCR**: `rapidocr-onnxruntime` already in the stack. Add a new wrapper `privacyguard/ocr/image_ocr.py` that takes a Pillow `Image` and returns the same `(text, bbox, confidence)` tuple the existing PDF image-block path returns. The lazy-loading rule applies — RapidOCR must NOT be imported at module top.

2. **Redaction output options**:
   - **Irreversible burn-in (recommended for "shared/distributed" use case)**: Pillow `ImageDraw.rectangle` with black fill, then **flatten** the JPEG/PNG. Pure Pillow, no extra deps.
   - **Reversible sidecar (recommended for "review before commit" use case)**: write a `.redaction.json` next to the image with bounding boxes + entity types. User opens the original image + sidecar in the app to review; on commit, the app renders the burn-in to a new image.

3. **Verification pass (critical)**: after burn-in, re-OCR the redacted output. If any of the previously detected sensitive tokens still appear in OCR text, **fail the operation** with an error and do NOT return the redacted file. This is the lesson from the well-documented "black box over text but underlying text remains extractable" PDF redaction failure mode — apply the same paranoia to image redaction.

4. **Multi-page TIFF/BMP**: out of scope for v38.x.

5. **PyInstaller implications**: zero new dependencies — `pillow`, `rapidocr-onnxruntime`, `opencv-python` are all already pinned and already have hooks.

---

## 4. Architecture Patterns (Stack-Level)

### 4.1 Entity Hit Schema (the canonical output of the engine)

```python
# privacyguard/pii/types.py
@dataclass(frozen=True)
class PIIHit:
    entity_type: str         # e.g. "CN_ID_CARD", "CN_PHONE", "CN_NAME"
    start: int               # char offset in source text
    end: int                 # exclusive
    text: str                # original matched text
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    validator_passed: bool   # whether the checksum/dictionary matched
    source: Literal["regex", "validator", "dictionary", "context"]
    suggested_mask: str      # e.g. "110101********1234"
```

This is the single data structure that the Excel worker, the image worker, and the new "auto-detect on PDF" path will all consume. Defining it once in `privacyguard/pii/` prevents the per-format reinvention that v37.7.6 just finished converging.

### 4.2 Confidence → Action Mapping

```
HIGH confidence  → auto-redact on apply; user can override per hit
MEDIUM confidence  → marked by default; user must confirm
LOW confidence  → flagged as candidate; user reviews manually
```

This three-tier model directly mirrors Adobe Acrobat Pro's "Mark then Apply with confidence levels" workflow and Microsoft Purview's "review queue at confidence threshold" pattern. Industry-validated pattern.

### 4.3 Masking Conventions (Chinese standard)

These are the de-facto industry conventions from GB/T 35273-2020 and common practice in finance / telecom / government:

| Entity | Keep | Mask | Example |
|---|---|---|---|
| 身份证 | 前6 + 后4 | middle 8 chars | `110101********1234` |
| 手机号 | 前3 + 后4 | middle 4 | `138****5678` |
| 银行卡 | 前6 + 后4 | middle | `622848********1234` |
| 邮箱 | 第1字符 + 域名 | middle | `z****@qq.com` |
| 姓名 | 姓 | 名 | `王*` |
| 地址 | 省/市 | 余下 | `北京市朝阳区****` |
| 车牌 | 省 + 首字母 | 余下 | `京A*****` |

**Implementation**: a small `mask.py` module that takes `(entity_type, original_text) -> masked_text` and applies the per-type rule. The engine pre-computes `suggested_mask` on each hit so the worker can write the masked value directly without re-implementing the convention.

### 4.4 Lazy Loading Contract (carry forward)

The v37.7.6 contract — RapidOCR is not initialized until the first OCR call — extends to the new engine:
- `privacyguard/pii/dictionaries/__init__.py` loads the JSON at import time (this is fine; it's just JSON parsing, no model init).
- `privacyguard/pii/regex_engine.py` uses `re.compile` at module level (fine, fast, no IO).
- `privacyguard/ocr/image_ocr.py` does **NOT** import `rapidocr` at top level — only inside the `recognize()` function, mirroring the existing pattern in `privacyguard/ocr/rapidocr.py`.

---

## 5. Version Compatibility

| Package | Compatible With | Notes |
|---|---|---|
| `openpyxl>=3.1.5` | Python 3.10–3.13 | Pure-Python; PyQt6 6.10.2 has no interaction |
| `openpyxl>=3.1.5` | `lxml==6.0.2` (already pinned) | openpyxl uses lxml for XML read; this combo is tested in the existing PyMuPDF path |
| `openpyxl>=3.1.5` | PyInstaller 6.18.0 | `pyinstaller-hooks-contrib` has `hook-openpyxl.py`; no custom hook needed |
| `openpyxl` | `python-docx==1.2.0` | Both libraries coexist on the same `lxml` backend, no conflict |
| `xlrd==2.0.1` | Python 3.10–3.13 | Last release supports Python 3; not a runtime pin risk |
| Pillow (already pinned) | openpyxl image embedding | Compatible; can read/write JPEG/PNG natively |
| RapidOCR (already pinned) | Pillow Image input | Already accepts numpy arrays; converting Pillow→numpy is one line |

**No version conflicts with the existing stack.**

---

## 6. PyInstaller Bundle Impact Summary

| New dependency | Bundle delta | Hook required | Risk |
|---|---|---|---|
| `openpyxl` | +~3 MB (pure-Python modules) | `pyinstaller-hooks-contrib` ships `hook-openpyxl.py` | LOW |
| `xlrd` (optional) | +~1 MB (pure-Python) | None | LOW |
| In-house PII engine | +~150 KB Python source | None | NONE |
| Dictionary JSON files | +~260 KB | Add via `datas=[...]` in spec | LOW |
| New `image_ocr.py` worker | +~5 KB | None (reuses RapidOCR hook already configured) | NONE |

**Total bundle delta: ~4–5 MB** (compared to current bundle). No new native dependencies. No new model files. No new C extensions.

---

## 7. Installation

```bash
# Core (Excel read/write)
pip install "openpyxl>=3.1.5,<3.2"

# Optional: legacy .xls support (only if we promise it)
pip install "xlrd==2.0.1"

# Everything else is in-tree:
# - privacyguard/pii/* (engine, validators, dictionaries)
# - privacyguard/ocr/image_ocr.py (thin wrapper, reuses rapidocr)
# - privacyguard/workers/image_worker.py (new worker)
```

No new system libraries. No new native wheels. **The PyInstaller Windows/macOS builds do not change their fundamental shape** — only add two small Python packages + a `datas=[...]` entry for the dictionary JSON files.

---

## 8. Sources

- [openpyxl documentation — read/write with formatting](https://openpyxl.readthedocs.io/en/stable/tutorial.html) — MEDIUM (direct doc)
- [openpyxl 3.1.5 release notes — March 2025](https://pypi.org/project/openpyxl/) — MEDIUM (PyPI blocked; metadata cross-checked via GitHub release log)
- [Why xlrd won't open .xlsx files anymore — pyxll](https://www.pyxll.com/blog/why-xlrd-wont-open-xlsx-files/) — HIGH (definitive explanation)
- [xlrd PyPI status](https://pypi.org/project/xlrd/) — MEDIUM (last release 2.0.1, in maintenance mode)
- [pylightxl GitHub — does NOT preserve formatting](https://github.com/PydPiper/pylightxl) — HIGH
- [PyInstaller hook-openpyxl](https://github.com/pyinstaller/pyinstaller-hooks-contrib/blob/master/hooks/std-noncontrib/hook-openpyxl.py) — HIGH (official contrib repo)
- [Microsoft Presidio supported entities](https://microsoft.github.io/presidio/supported_entities/) — HIGH
- [Presidio Analyzer package footprint analysis](https://microsoft.github.io/presidio/analyzer/) — HIGH (with note: spaCy model adds 700+ MB)
- [Chinese 行政区划 GitHub dataset — sysloser/adcode (updated 2024-11-25)](https://github.com/sysloser/adcode) — HIGH
- [Chinese 百家姓 GitHub dataset — HALOSTAR/chinese_surnames](https://github.com/HALOSTAR/chinese_surnames) — MEDIUM (single commit repo; verify content)
- [Adobe Acrobat redaction — marking vs applying two-phase workflow](https://www.adobe.com/acrobat/hub/business/audit-trail-redaction-software.html) — HIGH
- [Microsoft Purview DLP — sensitive information types + confidence](https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp) — HIGH
- [iText pdfSweep RedactionStrategy pattern](https://itextpdf.com/products/itext-7/pdfsweep) — HIGH
- [Adobe redaction audit trails — GDPR Article 30 + HIPAA §164.312(b)](https://www.adobe.com/government/reports/government-redaction-guide.html) — HIGH
- [GDPR Article 17 — redaction for right-to-be-forgotten](https://digitalguardian.com/blogs/expert-guide/redaction-software) — HIGH
- [Chinese data masking conventions — 前3后4 / 前6后4 (GB/T 35273-2020)](https://blog.csdn.net/HHQHHQ/article/details/115769505) — MEDIUM (industry convention references)
- [PDF redaction failure mode — black box over text does NOT remove underlying text](https://www.digitalguardian.com/blogs/expert-guide/manual-document-redaction-risks) — HIGH
- [DLP false-positive rate benchmarks — <5% production, <1% mature](https://learn.microsoft.com/en-us/purview/dlp-tune-policy) — MEDIUM (industry guidance)

---

## 9. Confidence Assessment

| Area | Confidence | Reason |
|---|---|---|
| openpyxl choice | HIGH | No alternative meets the round-trip-with-formulas requirement |
| xlrd for .xls | MEDIUM | Working but unmaintained; the recommended path is "convert via LibreOffice" |
| In-house PII engine vs Presidio | HIGH | Bundle weight + Chinese coverage gap are decisive; PROJECT.md requirements explicitly endorse this approach |
| Validator algorithms in-house | HIGH | Standards are public, test vectors exist, ~30 lines each |
| Dictionary sources | MEDIUM | Found good GitHub candidates; need to verify licensing on the actual JSON content before bundling |
| Image OCR redaction pattern | HIGH | Reuses existing toolchain; verification pass via re-OCR is a well-known safety pattern |
| PyInstaller implications | HIGH | All additions are pure-Python or data files; existing hooks cover the case |

## 10. Open Questions / Phase-Specific Research Flags

These should be researched in the per-phase plan, NOT in this stack document:

- Exact dictionary licensing — needs legal review before bundling `Chinese-Names-Corpus` or `sysloser/adcode`.
- Whether to ship `.xls` support in v38.x or defer to v39 (user impact survey needed).
- Whether the "reversible sidecar" image redaction mode is actually used by real users, or whether the irreversible burn-in alone suffices.
- Whether the existing `pdf_doc/page_data` state structure can be extended to carry `pii_hits[]` without breaking the v37.7.6 convergence (architecture, not stack).
- Whether `id-validator` PyPI package should be re-evaluated in a year if it gains an active maintainer.

---

*Stack research for: PrivacyGuard v38.x — pure-local Chinese PII recognition + Excel/Image redaction*
*Researched: 2026-08-10*
*Hand-off to: roadmap creation*