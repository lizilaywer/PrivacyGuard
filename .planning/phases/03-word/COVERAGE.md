---
phase: 3
slug: word
type: api-coverage-declaration
created: 2026-08-11
---

# Phase 3 API Coverage Declaration

## External API Surface Audit

Phase 3 (Word 文档接入识别引擎 — 双栏对比预览自动高亮) introduces **zero new external APIs, webhooks, or third-party service integrations**.

The phase works entirely with the existing internal stack:

| Component | Role | Already present? |
|-----------|------|------------------|
| `privacyguard.pii.engine.PIIEngine` | 9-entity PII detection (Phase 1 + Phase 2) | yes |
| `privacyguard.pii.hits.PIIHit` | Hit data class (D-05 field lock) | yes |
| `privacyguard.pii.mask.mask_for_entity` | 9-entity mask dispatch | yes |
| `python-docx` (`docx.Document`) | Word read/write | yes (runtime) |
| `mammoth` | DOCX → HTML for preview | yes |
| `PyInstaller` | Windows/macOS packaging | yes |

The new `privacyguard.pii.word_adapter` module is a **local** Python adapter that wraps existing internal functions (`PIIEngine.detect`, `mask_for_entity`, `replace_matches_in_paragraph`) into three format-specific helpers — no network, no cloud, no SaaS.

## Conclusion

`api-coverage plan-pre contribution:` **No external API integration: PrivacyGuard 3 复用既有 PII 引擎 + python-docx, 零新增外部 SDK / 云端 API / webhook.**
