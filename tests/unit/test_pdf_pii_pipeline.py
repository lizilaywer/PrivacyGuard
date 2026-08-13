"""tests/unit/test_pdf_pii_pipeline.py — FMT-01 PDF 端到端 PII 真脱敏 pipeline。

Plan 01-01 tracer 仅覆盖**文字层**路径的 reverse-extraction（B3 deferred scope）。
本文件覆盖：
1. text_layer_pdf_full_pipeline — 文字层 + 真脱敏 + 反向提取（与 01-01 同等覆盖，作为兜底）。
2. image_block_pdf_full_pipeline — image-block OCR 路径的 engine 端到端：
   用真实 OCR 文字注入 TextUnit(source='image_block')，验证 PIIEngine 在 source='image_block'
   下也能 detect（即便 engine 内部对 OCR 路径走 placeholder rect，至少命中要被识别）。
3. save_loop_piilist_included_in_redaction — 模拟 save loop 中 pii_list 合并路径，验证
   add_redact_annot + apply_redactions(IMAGE_PIXELS) 后敏感字符串消失。

I3 防平凡绿色：每个测试都有 pre-condition `assert len(hits) >= N` 确保引擎真的检测到了。
"""
import os
import tempfile
import unittest

import fitz

from privacyguard.pii.engine import PIIEngine, TextUnit
from privacyguard.pii.pdf_adapter import apply_pii_redactions
from tests.fixtures.fake_pii import fake_id_card, fake_phone


class TestPiiPipelineEndToEnd(unittest.TestCase):
    """FMT-01: PDF text-layer / image-block / save-loop 三路径端到端。"""

    # ---------------- text layer path ----------------
    def test_text_layer_pdf_full_pipeline(self):
        """文字层 PDF：synth -> detect -> apply -> reverse-extract -> 断言敏感字段消失。"""
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in.pdf")
            out_pdf = os.path.join(tmp, "out.pdf")
            secret_id = fake_id_card()
            secret_phone = fake_phone()

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(
                (50, 100),
                f"测试样本 身份证 {secret_id} 手机 {secret_phone}",
                fontsize=14,
            )
            doc.save(in_pdf)
            doc.close()

            engine = PIIEngine()
            rects_per_page = {}
            all_hits = []
            with fitz.open(in_pdf) as src:
                for i, p in enumerate(src):
                    unit = TextUnit(
                        page_index=i, text=p.get_text(), source="text",
                    )
                    page_hits = []
                    for hit in engine.detect(unit, page=p):
                        all_hits.append(hit)
                        # engine 接收 page 后会自动 page.search_for 取真实坐标
                        pr = hit.page_rect
                        page_hits.append(fitz.Rect(pr[0], pr[1], pr[0] + pr[2], pr[1] + pr[3]))
                    if page_hits:
                        rects_per_page[i] = page_hits

            # I3 pre-condition: 必须检测到至少 2 个 hit（1 ID + 1 phone）
            self.assertGreaterEqual(
                len(all_hits),
                2,
                f"text-layer 路径检测命中数 {len(all_hits)} < 2；测试无意义，不应平凡通过",
            )

            apply_pii_redactions(in_pdf, out_pdf, rects_per_page)

            with fitz.open(out_pdf) as out_doc:
                out_text = "".join(p.get_text() for p in out_doc)
            self.assertNotIn(
                secret_id[:10], out_text,
                f"身份证前 10 位仍可提取: {secret_id[:10]} in {out_text!r}",
            )
            self.assertNotIn(
                secret_phone[:7], out_text,
                f"手机号前 7 位仍可提取: {secret_phone[:7]} in {out_text!r}",
            )

    # ---------------- image-block OCR path ----------------
    def test_image_block_pdf_full_pipeline(self):
        """image-block OCR 路径：将 OCR 文字以 TextUnit(source='image_block') 注入引擎，
        engine 应能识别（OCR 路径 placeholder rect，但命中应被识别并触发后续 pipeline）。
        """
        secret_id = fake_id_card()
        secret_phone = fake_phone()
        # OCR 文字层（模拟 RapidOCR 输出）
        ocr_text = f"测试样本 身份证 {secret_id} 手机 {secret_phone}"

        engine = PIIEngine()
        unit = TextUnit(page_index=0, text=ocr_text, source="image_block")
        hits = engine.detect(unit)

        # I3 pre-condition: image-block OCR 路径必须产生 ≥ 1 个 PIIHit
        # （即使 engine 内部对 source!='text' 走 placeholder rect，识别逻辑不能变）
        self.assertGreaterEqual(
            len(hits),
            1,
            f"image-block OCR 路径检测命中数 {len(hits)} < 1；引擎必须能在 image_block 源下识别敏感字段",
        )

        # 验证命中类型
        entity_types = {h.entity_type for h in hits}
        self.assertTrue(
            entity_types & {"CN_ID_CARD", "CN_PHONE"},
            f"image-block 路径命中类型未覆盖 ID/Phone: {entity_types}",
        )

        # 验证 normalized 字段 — 必须包含原始 ID / phone 的有效前缀
        normalized_texts = {h.normalized for h in hits}
        self.assertTrue(
            any(secret_id[:10] in n or n in secret_id[:10] for n in normalized_texts),
            f"image-block 路径未识别身份证 normalized (expected: {secret_id[:10]} in {normalized_texts})",
        )
        self.assertTrue(
            any(secret_phone[:7] in n or n in secret_phone[:7] for n in normalized_texts),
            f"image-block 路径未识别手机号 normalized (expected: {secret_phone[:7]} in {normalized_texts})",
        )

    # ---------------- save-loop pii_list merge path ----------------
    def test_save_loop_piilist_included_in_redaction(self):
        """模拟 main.py:12354 save loop 中 pii_list 合并到 add_redact_annot + apply_redactions。

        使用 text-layer 路径产出真实 page_rect，把 PIIHit 直接喂给 apply_pii_redactions，
        验证整段 pipeline 端到端不会泄漏敏感字符串。
        """
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in.pdf")
            out_pdf = os.path.join(tmp, "out.pdf")
            secret_id = fake_id_card()
            secret_phone = fake_phone()

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(
                (50, 100),
                f"测试样本 身份证 {secret_id} 手机 {secret_phone}",
                fontsize=14,
            )
            doc.save(in_pdf)
            doc.close()

            engine = PIIEngine()
            rects_per_page = {}
            with fitz.open(in_pdf) as src:
                for i, p in enumerate(src):
                    unit = TextUnit(page_index=i, text=p.get_text(), source="text")
                    page_rects = []
                    for hit in engine.detect(unit, page=p):
                        pr = hit.page_rect
                        page_rects.append(fitz.Rect(pr[0], pr[1], pr[0] + pr[2], pr[1] + pr[3]))
                    if page_rects:
                        rects_per_page[i] = page_rects

            # pii_list 模拟 — 与 save loop 相同方式传入 apply_pii_redactions
            self.assertGreater(
                sum(len(v) for v in rects_per_page.values()),
                0,
                "pii_list 为空；测试无意义",
            )

            apply_pii_redactions(in_pdf, out_pdf, rects_per_page)

            with fitz.open(out_pdf) as out_doc:
                out_text = "".join(p.get_text() for p in out_doc)
            self.assertNotIn(secret_id[:10], out_text)
            self.assertNotIn(secret_phone[:7], out_text)


if __name__ == "__main__":
    unittest.main()