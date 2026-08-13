---
phase: 01
artifact: api_coverage_checkpoint
created: 2026-08-10
status: sealed
---

# API Coverage Declaration — Phase 1

No external API integration: 本阶段为纯本地 PDF PII 检测与真脱敏，仅调用进程内库（PyMuPDF / RapidOCR / cv2 / numpy），无任何外部服务或网络调用（ENGINE-08 / OPS-07 明确禁止联网）。

## Scope Statement

Phase 1 (PDF 自动识别身份证号与手机号并真脱敏) is implemented entirely through in-process Python libraries already pinned in `requirements.txt`:

| Library | Version | Role | Network I/O |
|---------|---------|------|-------------|
| PyMuPDF (`fitz`) | 1.27.1 | PDF 真删除 / `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` | none |
| RapidOCR (`rapidocr_onnxruntime`) | 1.2.3 | OCR for image-block + full-page fallback | none |
| OpenCV (`cv2`) | system | image preprocessing | none |
| NumPy | system | BGR array manipulation | none |
| PyQt6 | 6.10.2 | UI events / signal slot | none |

## Why This Declaration Qualifies

- ENGINE-08: "识别引擎为纯本地执行，运行期无任何网络请求" — locked requirement, no API surface.
- OPS-07: 79/79 baseline gated by `python3 -m unittest` (no network required).
- D-08: `pii_settings.engine_enabled` defaults to ON; the engine code path contains no `requests` / `urllib` / `httpx` / `socket.connect` invocation.
- D-10: `privacyguard/pii/data/rules.json` is read via `privacyguard.utils.security.resource_path`, which resolves to `sys._MEIPASS` (frozen) or `os.path.abspath(".")` (dev) — local FS only.
- RESEARCH §Common Pitfalls §9 / §Code Examples: PyMuPDF + RapidOCR are both pure-Python-with-native-bindings, no telemetry.

## Test Gate

`tests/unit/test_pii_offline.py` monkey-patches `socket.socket` and asserts the PII engine makes zero outbound socket calls over a 500-page synthetic scan. This test enforces the declaration at runtime.

## Reason Field

Phase 1 has no external service integrations, no API keys, no OAuth flows, no cloud SDKs. The "API" appearing in `01-RESEARCH.md` / `01-CONTEXT.md` refers to PyMuPDF's *library* API (e.g., `page.get_text()`, `page.add_redact_annot()`) — these are in-process Python calls, not network APIs.

---

*Sealed: 2026-08-10 — Planner*
