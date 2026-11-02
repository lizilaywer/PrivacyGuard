"""cp81 回归测试：全文搜索（build_search_snippet / collect_text_hits / DocSearchWorker）

覆盖：
1. snippet：中间命中截取、开头/结尾命中省略号、上下文短于 context、换行替换、非法入参
2. collect_text_hits：多命中、大小写不敏感、无命中、单页上限
3. DocSearchWorker 文字层逻辑：合成 3 页文字 PDF → 页码/命中数正确；
   tobytes 快照页序（删页后搜索页码正确）；取消中断
"""
import unittest

from main import build_search_snippet, collect_text_hits

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


class TestBuildSearchSnippet(unittest.TestCase):
    def test_middle_hit_with_ellipsis(self):
        text = "A" * 30 + "关键词" + "B" * 30
        before, kw, after = build_search_snippet(text, 30, 3, context_chars=10)
        self.assertEqual(kw, "关键词")
        self.assertTrue(before.startswith("…"))
        self.assertTrue(after.endswith("…"))
        self.assertEqual(before, "…" + "A" * 10)
        self.assertEqual(after, "B" * 10 + "…")

    def test_head_hit_no_leading_ellipsis(self):
        text = "开头就是命中词" + "X" * 40
        before, kw, after = build_search_snippet(text, 0, 4, context_chars=10)
        self.assertEqual(before, "")
        self.assertEqual(kw, "开头就是")

    def test_tail_hit_no_trailing_ellipsis(self):
        text = "Y" * 5 + "结尾"
        before, kw, after = build_search_snippet(text, 5, 2, context_chars=10)
        self.assertEqual(kw, "结尾")
        self.assertEqual(after, "")
        self.assertEqual(before, "Y" * 5)  # 全文短于 context，无省略号

    def test_newline_replaced(self):
        text = "第一行\n关键\r第二行"
        before, kw, after = build_search_snippet(text, 4, 2, context_chars=10)
        self.assertNotIn("\n", before + kw + after)
        self.assertNotIn("\r", before + kw + after)

    def test_invalid_inputs(self):
        self.assertEqual(build_search_snippet("", 0, 1), ("", "", ""))
        self.assertEqual(build_search_snippet("abc", -1, 1), ("", "", ""))
        self.assertEqual(build_search_snippet("abc", 2, 5), ("", "", ""))


class TestCollectTextHits(unittest.TestCase):
    def test_multiple_hits(self):
        hits = collect_text_hits("张三和张三的朋友张三", "张三")
        self.assertEqual(len(hits), 3)
        self.assertEqual([h[0] for h in hits], [0, 3, 8])

    def test_case_insensitive_keeps_original(self):
        hits = collect_text_hits("Hello WORLD hello", "hello")
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0][2], "Hello")  # kw_text 保留原文大小写
        self.assertEqual(hits[1][2], "hello")

    def test_no_hit_and_empty(self):
        self.assertEqual(collect_text_hits("abc", "xyz"), [])
        self.assertEqual(collect_text_hits("", "x"), [])
        self.assertEqual(collect_text_hits("abc", ""), [])

    def test_per_page_cap(self):
        hits = collect_text_hits("好" * 200, "好", max_hits_per_page=50)
        self.assertEqual(len(hits), 50)


@unittest.skipUnless(HAS_FITZ, "fitz 未安装")
class TestDocSearchWorkerTextLayer(unittest.TestCase):
    """文字层搜索逻辑（QThread.run 同步调用，不真正起线程）。"""

    def _make_pdf_bytes(self, page_texts):
        doc = fitz.open()
        for t in page_texts:
            page = doc.new_page()
            page.insert_text(fitz.Point(72, 72), t)
        data = doc.tobytes()
        doc.close()
        return data

    def _run_search(self, pdf_bytes, keyword, cache=None):
        from main import DocSearchWorker
        worker = DocSearchWorker(pdf_bytes, keyword, cache if cache is not None else {})
        hits = []
        done = []
        # cp82: hit_signal 末位新增 rect 元组（或 None）
        worker.hit_signal.connect(lambda p, b, k, a, r: hits.append((p, b, k, a, r)))
        worker.finished_signal.connect(lambda n: done.append(n))
        worker.run()  # 同步执行
        return hits, (done[0] if done else None)

    def test_hits_with_page_numbers(self):
        pdf = self._make_pdf_bytes(["target here", "nothing", "another target line"])
        hits, total = self._run_search(pdf, "target")
        self.assertEqual(total, 2)
        self.assertEqual([h[0] for h in hits], [0, 2])
        self.assertEqual(hits[0][2].lower(), "target")
        # cp82: 文字层命中应携带 search_for 矩形（页内合理坐标）
        rect = hits[0][4]
        self.assertIsNotNone(rect)
        x, y, w, h = rect
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

    def test_no_hits(self):
        pdf = self._make_pdf_bytes(["alpha", "beta"])
        hits, total = self._run_search(pdf, "gamma")
        self.assertEqual(total, 0)
        self.assertEqual(hits, [])

    def test_snapshot_page_order_after_delete(self):
        # 3 页含标记 → 删中间页后 tobytes 快照，命中页码应为新页序
        doc = fitz.open()
        for t in ["keep-A mark", "delete-me", "keep-B mark"]:
            page = doc.new_page()
            page.insert_text(fitz.Point(72, 72), t)
        doc.delete_page(1)
        data = doc.tobytes()
        doc.close()
        hits, total = self._run_search(data, "mark")
        self.assertEqual(total, 2)
        self.assertEqual([h[0] for h in hits], [0, 1])  # 新页序 0/1

    def test_ocr_cache_hit_for_scan_page(self):
        """无文字层页（扫描页）：缓存有文本时直接命中，不触发 OCR 引擎加载。

        cp82: 缓存结构升级为 {'text','spans'}；命中应回查所在行矩形。
        """
        doc = fitz.open()
        doc.new_page()  # 空白页，无文字层
        data = doc.tobytes()
        doc.close()
        line = "这里有目标关键词存在"
        cache = {0: {"text": line, "spans": [(0, len(line), (10.0, 20.0, 100.0, 12.0))]}}
        hits, total = self._run_search(data, "目标关键词", cache=cache)
        self.assertEqual(total, 1)
        self.assertEqual(hits[0][0], 0)
        self.assertEqual(hits[0][2], "目标关键词")
        # 命中位置落在行区间内 → 携带该行矩形
        self.assertEqual(hits[0][4], (10.0, 20.0, 100.0, 12.0))
        # 缓存未被覆写
        self.assertEqual(cache[0]["text"], line)

    def test_legacy_str_cache_degrades_without_rect(self):
        """cp82: 旧纯文本缓存降级为无矩形命中（防御路径）。"""
        doc = fitz.open()
        doc.new_page()
        data = doc.tobytes()
        doc.close()
        cache = {0: "旧结构包含keyword文本"}
        hits, total = self._run_search(data, "keyword", cache=cache)
        self.assertEqual(total, 1)
        self.assertIsNone(hits[0][4])


if __name__ == "__main__":
    unittest.main()
