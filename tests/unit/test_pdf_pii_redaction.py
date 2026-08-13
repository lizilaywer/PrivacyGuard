"""Phase 1 反向提取真脱敏验证（SAFE-01 / SAFE-02）。

D-14 规定：反向提取优先 `fitz.open(out).get_text()` 路径，避免依赖
poppler-utils；pdftotext 仅作人工验证备用。

B3 scope decision：01-01 tracer 仅覆盖**文字层**路径的 reverse-extraction。
image-pixels-only 场景由 Plan 01-03 Task 3（collect_full_page_ocr_hits）
扩展后另行验证，因为 image-only PDF 的 page.get_text() 为空字符串，
会让零命中 reverse-extraction 平凡通过——这是 01-01 必须规避的真空绿色。
"""
import os
import tempfile
import unittest

import fitz

from privacyguard.pii.engine import PIIEngine, TextUnit
from privacyguard.pii.pdf_adapter import apply_pii_redactions
from tests.fixtures.fake_pii import fake_id_card, fake_phone
from tests.e2e.create_pii_test_pdf import (
    create_pii_test_pdf,
    create_pii_id_only_pdf,
    create_pii_phone_only_pdf,
)


class TestPdfPiiRedaction(unittest.TestCase):
    """SAFE-01 / SAFE-02：fitz.open(out).get_text() 反向断言敏感字符串不存在。"""

    def _build_pii_pdf(self, in_pdf: str) -> tuple:
        """构建一个含 18 位身份证 + 11 位手机号的文字层测试 PDF。

        返回 (secret_id, secret_phone)。
        """
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
        return secret_id, secret_phone

    def _detect_with_search_for(self, in_pdf):
        """detect + 用 page.search_for 取得精确坐标。

        引擎返回的 page_rect 在 text-layer path 是占位 (0, 0, w, h)，
        不能直接用于 redaction（会画到页面左上角）。这里基于 normalized
        文本二次查询 page.search_for 取真实坐标。
        """
        engine = PIIEngine()
        rects_per_page = {}
        all_hits = []
        with fitz.open(in_pdf) as src:
            for i, page in enumerate(src):
                unit = TextUnit(page_index=i, text=page.get_text(), source="text")
                page_hits = []
                for hit in engine.detect(unit):
                    all_hits.append(hit)
                    matches = page.search_for(hit.normalized)
                    if matches:
                        # 取第一个匹配；同一字符串多次匹配走 overlap.resolve
                        r = matches[0]
                        page_hits.append(fitz.Rect(r.x0, r.y0, r.x1, r.y1))
                    else:
                        # 兜底使用 hit 自带 rect（占位）
                        rp = hit.page_rect
                        page_hits.append(fitz.Rect(rp[0], rp[1], rp[0] + rp[2], rp[1] + rp[3]))
                if page_hits:
                    rects_per_page[i] = page_hits
        return rects_per_page, all_hits

    def test_redacted_text_not_extractable(self):
        """完整 spine：synth PDF -> PIIEngine.detect -> apply_pii_redactions ->
        fitz.open(out).get_text() -> 断言敏感前 10/7 位消失。
        """
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in.pdf")
            out_pdf = os.path.join(tmp, "out.pdf")
            secret_id, secret_phone = self._build_pii_pdf(in_pdf)

            # 1. detect + 二次定位
            rects_per_page, hits = self._detect_with_search_for(in_pdf)

            # Pre-condition: 引擎必须检测到至少一个 hit（否则测试无意义）。
            self.assertGreater(
                len(hits),
                0,
                "PIIEngine 未检测到任何命中；测试失败（不应平凡通过）",
            )

            # 2. apply 真脱敏
            apply_pii_redactions(in_pdf, out_pdf, rects_per_page)

            # 3. 反向提取并断言
            with fitz.open(out_pdf) as out_doc:
                out_text = "".join(p.get_text() for p in out_doc)
            self.assertNotIn(
                secret_id[:10],
                out_text,
                f"身份证前 10 位仍可提取: {secret_id[:10]} in {out_text!r}",
            )
            self.assertNotIn(
                secret_phone[:7],
                out_text,
                f"手机号前 7 位仍可提取: {secret_phone[:7]} in {out_text!r}",
            )

    def test_redacted_id_alone(self):
        """隔离测试：仅含 18 位身份证的 PDF 反向不应保留前 10 位。"""
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in_id.pdf")
            out_pdf = os.path.join(tmp, "out_id.pdf")
            secret_id = "53010219200508011X"  # GB 11643 标准样本

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 100), f"测试样本 身份证 {secret_id}", fontsize=14)
            doc.save(in_pdf)
            doc.close()

            rects_per_page, hits = self._detect_with_search_for(in_pdf)

            self.assertGreater(
                len(hits),
                0,
                "PIIEngine 未检测到 GB 11643 标准样本 53010219200508011X",
            )

            apply_pii_redactions(in_pdf, out_pdf, rects_per_page)

            with fitz.open(out_pdf) as out_doc:
                out_text = "".join(p.get_text() for p in out_doc)
            self.assertNotIn(
                secret_id[:10],
                out_text,
                f"GB 11643 标准样本前 10 位仍可提取: {secret_id[:10]}",
            )


# ----------------------------------------------------------------------
# Phase 2 (02-01-tracer) — partial mask + blackout mode 反向测试
# ----------------------------------------------------------------------

class TestPartialMaskWritesMaskText(unittest.TestCase):
    """MASK-01: partial mask 写入后反向断言原文不存在 + mask_strategy 文字存在。"""

    def _build_pii_pdf(self, in_pdf: str, secret: str) -> None:
        """构建一个含一段 PII 字符串的合成 PDF（文字层路径）。"""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (50, 100),
            f"测试 {secret}",
            fontsize=14,
        )
        doc.save(in_pdf)
        doc.close()

    # ------------------------------------------------------------------
    # Phase 2 (02-03-main-py-settings-packaging) — save_pdf 集成测试
    # ------------------------------------------------------------------

    def test_main_window_save_pdf_routes_pii_through_write_partial_masks_and_clears_metadata(self):
        """Phase 2 (02-04 WR-03 fix): 实际调用 write_partial_masks（不再内联 mirror）验证 CR-01 fix。

        WR-03 fix: 旧版测试虽然 import 了 write_partial_masks，但实际手动 inline 重写了
        add_redact_annot + apply_redactions + insert_text 全流程（即 main.py 的 WR-02 anti-pattern），
        因此即使 main.py 重新引入 inline 实现也能"通过"测试。新版直接调用 write_partial_masks，
        真正覆盖 production helper 路径。

        由于 MainWindow.save_pdf 依赖 QApplication / GUI，测试通过直接调用 write_partial_masks +
        clear_pdf_metadata 来模拟 save loop 路径，并反向断言：
        - 原始 ID 完整字符串不在输出中
        - mask_strategy 文字在输出中
        - 5 字段 metadata 全部清空
        """
        from privacyguard.pii.pdf_adapter import (
            write_partial_masks,
            clear_pdf_metadata,
        )
        from privacyguard.pii.mask import partial_mask_id_card
        from privacyguard.pii.hits import PIIHit
        from privacyguard.pii.engine import PIIEngine, TextUnit
        from tests.fixtures.fake_pii import fake_id_card

        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in_save.pdf")
            out_pdf = os.path.join(tmp, "out_save.pdf")
            secret_id = fake_id_card()
            mask_text = partial_mask_id_card(secret_id)

            # 1. 合成包含身份证 + 5 字段 metadata 的测试 PDF
            doc = fitz.open()
            doc.set_metadata({
                "title": "敏感标题",
                "author": "敏感作者",
                "subject": "敏感主题",
                "producer": "敏感生产者",
                "creator": "敏感创建者",
            })
            page = doc.new_page()
            page.insert_text((50, 100), f"测试 身份证 {secret_id}", fontsize=14)
            doc.save(in_pdf)
            doc.close()

            # 2. detect + page.search_for 二次定位 → 构造 PIIHit 列表
            engine = PIIEngine()
            with fitz.open(in_pdf) as src:
                page = src[0]
                unit = TextUnit(page_index=0, text=page.get_text(), source="text")
                hits = list(engine.detect(unit))
                self.assertGreater(len(hits), 0, "PIIEngine 未检测到 fake_id_card")
                matches = page.search_for(hits[0].normalized)
                self.assertGreater(len(matches), 0, "page.search_for 未找到 ID card")
                r = matches[0]
                page_rect = (r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0)

            # 3. 构造 PIIHit (page_rect 用 page.search_for 真实坐标)
            pii_hit = PIIHit(
                entity_type=hits[0].entity_type,
                page_offset=0,
                page_length=len(hits[0].normalized),
                page_rect=page_rect,
                confidence_tier=hits[0].confidence_tier,
                source="text",
                mask_strategy=mask_text,
                normalized=hits[0].normalized,
                validator_passed=True,
            )

            # 4. WR-03 fix: 实际调用 write_partial_masks（production helper）替代 inline mirror
            #    02-04 签名支持 (PIIHit, 'partial') 2-tuple 形式
            doc_save = fitz.open(in_pdf)
            try:
                write_partial_masks(doc_save, 0, [(pii_hit, 'partial')])
                clear_pdf_metadata(doc_save)
                doc_save.save(out_pdf, garbage=4, deflate=True, clean=True)
            finally:
                doc_save.close()

            # 5. 反向断言 — 原文不存在 + mask 文字存在 + 5 字段清空
            with fitz.open(out_pdf) as out_doc:
                out_text = "".join(p.get_text() for p in out_doc)
                meta = out_doc.metadata
            # (a) 完整 ID 字符串不在输出中（D-01 真删除）
            self.assertNotIn(
                secret_id, out_text,
                f"完整身份证字符串仍可提取: {secret_id}",
            )
            # (b) mask_strategy 在输出中（partial mask 保留前 6 + 后 4）
            self.assertIn(
                mask_text, out_text,
                f"mask_strategy {mask_text!r} 不在输出: {out_text!r}",
            )
            # (c) 5 字段 metadata 全部清空（D-14 + D-15）
            for key in ("title", "author", "subject", "producer", "creator"):
                self.assertEqual(
                    meta.get(key, ""), "",
                    f"元数据 {key} 未清空: {meta.get(key)!r}",
                )

    def _detect_and_get_rects(self, in_pdf: str, normalized: str):
        """detect + page.search_for 二次定位 → 返回 (rects_per_page_dict, hits_list)。

        用 page.search_for(normalized) 取精确坐标（text-layer 路径）。
        """
        from privacyguard.pii.engine import PIIEngine, TextUnit
        engine = PIIEngine()
        rects_per_page = {}
        all_hits = []
        with fitz.open(in_pdf) as src:
            for i, page in enumerate(src):
                unit = TextUnit(page_index=i, text=page.get_text(), source="text")
                page_hits = []
                for hit in engine.detect(unit):
                    all_hits.append(hit)
                    matches = page.search_for(hit.normalized)
                    if matches:
                        r = matches[0]
                        page_hits.append((r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0))
                    else:
                        rp = hit.page_rect
                        page_hits.append(rp)
                if page_hits:
                    rects_per_page[i] = page_hits
        return rects_per_page, all_hits

    def _build_hits(self, hits, rects_per_page, normalized, entity_type, mask_text):
        """把 detect 命中的 hit 转成 PIIHit 列表（page_rect 用 page.search_for 真实坐标）。"""
        from privacyguard.pii.hits import PIIHit
        out = []
        for page_idx, rect_list in rects_per_page.items():
            for rect in rect_list:
                if isinstance(rect, fitz.Rect):
                    x, y, w, h = rect.x0, rect.y0, rect.width, rect.height
                else:
                    x, y, w, h = rect
                out.append(PIIHit(
                    entity_type=entity_type,
                    page_offset=0,
                    page_length=len(normalized),
                    page_rect=(x, y, w, h),
                    confidence_tier="HIGH",
                    source="text",
                    mask_strategy=mask_text,
                    normalized=normalized,
                    validator_passed=True,
                ))
        return out

    def test_partial_mask_writes_mask_text_for_uscc(self):
        """MASK-01: partial mask 写入 USCC → 反向提取不含原文前 6 位 + 含 mask_strategy。"""
        from privacyguard.pii.mask import partial_mask_uscc
        from privacyguard.pii.pdf_adapter import write_partial_masks
        from tests.fixtures.fake_pii import fake_uscc
        uscc = fake_uscc()
        mask_text = partial_mask_uscc(uscc)
        self.assertEqual(len(mask_text), 18)
        self.assertTrue(mask_text.startswith(uscc[:6]))

        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in_uscc.pdf")
            out_pdf = os.path.join(tmp, "out_uscc.pdf")
            self._build_pii_pdf(in_pdf, uscc)

            # detect + page.search_for 二次定位
            rects_per_page, hits = self._detect_and_get_rects(in_pdf, uscc)
            self.assertGreater(len(hits), 0, "PIIEngine 未检测到 fake_uscc")

            hits_with_rect = self._build_hits(
                hits, rects_per_page, uscc, "CN_USCC", mask_text,
            )

            # partial mask 写入
            doc = fitz.open(in_pdf)
            try:
                for page_idx in rects_per_page.keys():
                    page_hits = [h for h in hits_with_rect if True]
                    write_partial_masks(doc, page_idx, page_hits, mode="partial")
                doc.save(out_pdf, garbage=4, deflate=True, clean=True)
            finally:
                doc.close()

            # 反向提取
            with fitz.open(out_pdf) as out_doc:
                out_text = "".join(p.get_text() for p in out_doc)
            # 原文完整 18 字符串应被销毁（D-01 真删除）
            self.assertNotIn(
                uscc,
                out_text,
                f"USCC 完整字符串仍可提取: {uscc} in {out_text!r}",
            )
            # mask_strategy 应保留（白字写在色块上 — PyMuPDF 可被 get_text 提取）
            self.assertIn(
                mask_text,
                out_text,
                f"mask_strategy {mask_text!r} 不在输出中: {out_text!r}",
            )

    def test_partial_mask_blackout_mode_destroys_only(self):
        """blackout mode: 仅销毁原文，不写 mask 文字。"""
        from privacyguard.pii.mask import partial_mask_uscc
        from privacyguard.pii.pdf_adapter import write_partial_masks
        from tests.fixtures.fake_pii import fake_uscc
        uscc = fake_uscc()
        mask_text = partial_mask_uscc(uscc)

        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in_blackout.pdf")
            out_pdf = os.path.join(tmp, "out_blackout.pdf")
            self._build_pii_pdf(in_pdf, uscc)

            rects_per_page, hits = self._detect_and_get_rects(in_pdf, uscc)
            self.assertGreater(len(hits), 0)
            hits_with_rect = self._build_hits(
                hits, rects_per_page, uscc, "CN_USCC", mask_text,
            )

            doc = fitz.open(in_pdf)
            try:
                for page_idx in rects_per_page.keys():
                    page_hits = list(hits_with_rect)
                    write_partial_masks(doc, page_idx, page_hits, mode="blackout")
                doc.save(out_pdf, garbage=4, deflate=True, clean=True)
            finally:
                doc.close()

            with fitz.open(out_pdf) as out_doc:
                out_text = "".join(p.get_text() for p in out_doc)
            # blackout 模式：完整原文 + mask 文字都不应在输出中
            self.assertNotIn(uscc, out_text, "blackout 模式未销毁原文")
            self.assertNotIn(mask_text, out_text, "blackout 模式不应写 mask 文字")

    def test_partial_mask_id_card_also_visible(self):
        """MASK-01: partial mask 写入 18 位身份证 → 反向提取不含原文前 6 位 + 含 mask。"""
        from privacyguard.pii.mask import partial_mask_id_card
        from privacyguard.pii.pdf_adapter import write_partial_masks
        from tests.fixtures.fake_pii import fake_id_card
        secret = fake_id_card()
        mask_text = partial_mask_id_card(secret)

        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in_id.pdf")
            out_pdf = os.path.join(tmp, "out_id.pdf")
            self._build_pii_pdf(in_pdf, secret)

            rects_per_page, hits = self._detect_and_get_rects(in_pdf, secret)
            self.assertGreater(len(hits), 0)
            hits_with_rect = self._build_hits(
                hits, rects_per_page, secret, "CN_ID_CARD", mask_text,
            )

            doc = fitz.open(in_pdf)
            try:
                for page_idx in rects_per_page.keys():
                    page_hits = list(hits_with_rect)
                    write_partial_masks(doc, page_idx, page_hits, mode="partial")
                doc.save(out_pdf, garbage=4, deflate=True, clean=True)
            finally:
                doc.close()

            with fitz.open(out_pdf) as out_doc:
                out_text = "".join(p.get_text() for p in out_doc)
            self.assertNotIn(secret[:10], out_text, "身份证前 10 位仍可提取")
            self.assertIn(mask_text, out_text, "mask_strategy 不在输出")


class TestWritePartialMasksMixedItemDispatch(unittest.TestCase):
    """02-04: write_partial_masks must accept mixed item types in one call (PIIHit | fitz.Rect | tuple)."""

    def test_pii_hit_branch_signature_still_importable(self):
        """PIIHit dataclass routed via global mode (02-01 backward-compat path)."""
        from privacyguard.pii.pdf_adapter import write_partial_masks
        from privacyguard.pii.hits import PIIHit
        from privacyguard.pii.mask import partial_mask_id_card
        from tests.fixtures.fake_pii import fake_id_card
        hit = PIIHit(
            entity_type='CN_ID_CARD',
            page_offset=0,
            page_length=18,
            page_rect=(50.0, 100.0, 200.0, 20.0),
            source='text',
            mask_strategy=partial_mask_id_card(fake_id_card()),
            normalized='11010119800101001X',
            validator_passed=True,
        )
        self.assertEqual(hit.entity_type, 'CN_ID_CARD')
        # write_partial_masks must still accept [PIIHit] + mode= kwarg (02-01 contract)
        self.assertTrue(callable(write_partial_masks))

    def test_tuple_form_partial_mask_item_exported(self):
        """PartialMaskItem type alias exported for 02-04 mixed dispatch."""
        from privacyguard.pii import pdf_adapter
        self.assertTrue(hasattr(pdf_adapter, 'PartialMaskItem'))

    def test_mixed_5tuple_dispatches_correctly(self):
        """02-04: (x, y, w, h, mode) 5-tuple dispatched by per-item mode — blackout rect removes text."""
        import fitz, tempfile, os
        from privacyguard.pii.pdf_adapter import write_partial_masks
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, 'in_5tuple.pdf')
            out_pdf = os.path.join(tmp, 'out_5tuple.pdf')
            secret_token = 'SECRET_BLACKOUT_TARGET_42'
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((60, 115), secret_token, fontsize=12)
            doc.save(in_pdf)
            doc.close()
            doc = fitz.open(in_pdf)
            try:
                write_partial_masks(doc, 0, [(50, 100, 200, 20, 'blackout')], mode='partial')
                doc.save(out_pdf)
            finally:
                doc.close()
            with fitz.open(out_pdf) as out_doc:
                out_text = ''.join(p.get_text() for p in out_doc)
            self.assertNotIn(secret_token, out_text, f'5-tuple blackout failed: secret still extractable: {out_text!r}')

    def test_mixed_2tuple_partial_writes_mask_text(self):
        """02-04: (PIIHit, mode) 2-tuple dispatched — partial mode writes mask_strategy text."""
        import fitz, tempfile, os
        from privacyguard.pii.pdf_adapter import write_partial_masks
        from privacyguard.pii.hits import PIIHit
        from privacyguard.pii.mask import partial_mask_id_card
        from tests.fixtures.fake_pii import fake_id_card
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, 'in_2tuple.pdf')
            out_pdf = os.path.join(tmp, 'out_2tuple.pdf')
            secret_id = fake_id_card()
            mask_text = partial_mask_id_card(secret_id)
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((60, 115), f'测试 身份证 {secret_id}', fontsize=14)
            doc.save(in_pdf)
            doc.close()
            hit = PIIHit(
                entity_type='CN_ID_CARD',
                page_offset=0,
                page_length=len(secret_id),
                page_rect=(50.0, 100.0, 250.0, 25.0),
                source='text',
                mask_strategy=mask_text,
                normalized=secret_id,
                validator_passed=True,
            )
            doc = fitz.open(in_pdf)
            try:
                write_partial_masks(doc, 0, [(hit, 'partial')])
                doc.save(out_pdf)
            finally:
                doc.close()
            with fitz.open(out_pdf) as out_doc:
                out_text = ''.join(p.get_text() for p in out_doc)
            self.assertNotIn(secret_id, out_text, f'2-tuple partial failed: original still extractable: {out_text!r}')
            self.assertIn(mask_text, out_text, f'2-tuple partial failed: mask text missing: {out_text!r}')

    def test_mixed_partial_and_blackout_in_one_call(self):
        """02-04: single call mixing (PIIHit, 'partial') + (x, y, w, h, 'blackout') — D-22 single-pass invariant."""
        import fitz, tempfile, os
        from privacyguard.pii.pdf_adapter import write_partial_masks
        from privacyguard.pii.hits import PIIHit
        from privacyguard.pii.mask import partial_mask_id_card
        from tests.fixtures.fake_pii import fake_id_card
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, 'in_mixed.pdf')
            out_pdf = os.path.join(tmp, 'out_mixed.pdf')
            secret_id = fake_id_card()
            mask_text = partial_mask_id_card(secret_id)
            secret_token = 'SECRET_BLACKOUT_REGION_99'
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((60, 115), f'身份证 {secret_id}', fontsize=14)
            page.insert_text((60, 215), secret_token, fontsize=14)
            doc.save(in_pdf)
            doc.close()
            hit = PIIHit(
                entity_type='CN_ID_CARD',
                page_offset=0,
                page_length=len(secret_id),
                page_rect=(50.0, 100.0, 250.0, 25.0),
                source='text',
                mask_strategy=mask_text,
                normalized=secret_id,
                validator_passed=True,
            )
            doc = fitz.open(in_pdf)
            try:
                write_partial_masks(doc, 0, [(hit, 'partial'), (50, 200, 300, 25, 'blackout')])
                doc.save(out_pdf)
            finally:
                doc.close()
            with fitz.open(out_pdf) as out_doc:
                out_text = ''.join(p.get_text() for p in out_doc)
            # Partial: mask text extractable, original secret not
            self.assertNotIn(secret_id, out_text, f'partial branch failed: original still extractable: {out_text!r}')
            self.assertIn(mask_text, out_text, f'partial branch failed: mask text missing: {out_text!r}')
            # Blackout: token removed
            self.assertNotIn(secret_token, out_text, f'blackout branch failed: token still extractable: {out_text!r}')


if __name__ == "__main__":
    unittest.main()