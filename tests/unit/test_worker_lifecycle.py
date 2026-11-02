# -*- coding: utf-8 -*-
"""v37.8.11 P2-3: Worker 线程生命周期与契约单元测试

验证 privacyguard.workers 下 5 个 QThread 子类的：
- 实例化契约（__init__ 参数能稳定构造，不依赖真实文件/OCR 引擎）
- 信号定义（必要的 pyqtSignal 类属性存在，供 MainWindow 接线）
- 中断机制（requestInterruption / isInterruptionRequested 标准 Qt 取消路径）
- WordBatchReplaceWorker 错误决策交互（provide_error_decision 跨线程通信）
- ImageMergeWorker 空输入边界（run() 同步执行不崩溃）
- WordWorker._find_matches 纯函数行为（Luhn/校验位门控）

全部用 offscreen Qt 平台，不实例化完整 MainWindow；
同步调用 run() 而非 start()，避免事件循环依赖。
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from PyQt6.QtWidgets import QApplication
    _APP = QApplication.instance() or QApplication([])  # 模块级持有，防 GC
    from privacyguard.workers import (
        OCRWorker,
        WordWorker,
        WordBatchReplaceWorker,
        DocSearchWorker,
        ImageMergeWorker,
    )
    HAS_DEPS = True
except Exception:  # noqa: BLE001 — 缺依赖时整体跳过，不阻断回归
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "PyQt6 / worker 依赖不可用")
class TestWorkerInstantiation(unittest.TestCase):
    """每个 Worker 必须能用最小合法参数稳定构造。"""

    def test_ocr_worker_instantiation(self):
        w = OCRWorker(
            pdf_path="<nonexistent>.pdf",
            rules=[r"\d{11}"],
            use_enhance=False,
            custom_keywords="",
            scan_scale=2.0,
            off_x=0,
            off_w=0,
        )
        self.assertFalse(w.isRunning())
        self.assertEqual(w.scan_scale, 2.0)
        self.assertEqual(w.rules, [r"\d{11}"])
        w.deleteLater()

    def test_ocr_worker_none_guards(self):
        """None 防御：rules/custom_keywords 为 None 不应崩溃。"""
        w = OCRWorker(
            pdf_path="x.pdf",
            rules=None,
            use_enhance=False,
            custom_keywords=None,
            scan_scale=1.0,
            off_x=0,
            off_w=0,
            custom_keyword_rules=None,
            rule_name_pairs=None,
        )
        self.assertEqual(w.rules, [])
        self.assertEqual(w.custom_keywords, [])
        self.assertEqual(w.rule_name_pairs, [])
        w.deleteLater()

    def test_word_worker_instantiation(self):
        w = WordWorker(
            word_doc=None,
            word_data={"p1": {"text": "张三 13812345678"}},
            rules=[r"1[3-9]\d{9}"],
            custom_keywords="张三",
            replacement_text="[已脱敏]",
        )
        self.assertEqual(w.replacement_text, "[已脱敏]")
        self.assertIn("张三", w.custom_keywords[0])  # re.escape 后仍含原文
        w.deleteLater()

    def test_word_worker_none_keywords_guard(self):
        w = WordWorker(
            word_doc=None,
            word_data={},
            rules=[],
            custom_keywords=None,
            replacement_text="[已脱敏]",
        )
        self.assertEqual(w.custom_keywords, [])
        w.deleteLater()

    def test_batch_replace_worker_instantiation(self):
        w = WordBatchReplaceWorker(
            file_paths=["a.docx", "b.doc"],
            rules=[{"enabled": True, "mode": "exact", "find": "x", "replace": "y"}],
            default_replacement_text="[默认]",
        )
        self.assertEqual(len(w.file_paths), 2)
        self.assertEqual(w.default_replacement_text, "[默认]")
        w.deleteLater()

    def test_batch_replace_worker_empty_input(self):
        w = WordBatchReplaceWorker(file_paths=None, rules=None, default_replacement_text="")
        self.assertEqual(w.file_paths, [])
        # 空替换文本兜底为 [已脱敏]
        self.assertEqual(w.default_replacement_text, "[已脱敏]")
        w.deleteLater()

    def test_doc_search_worker_instantiation(self):
        cache = {}
        w = DocSearchWorker(pdf_bytes=b"%PDF-1.4", keyword="合同", ocr_cache=cache)
        self.assertEqual(w.keyword, "合同")
        self.assertIs(w.ocr_cache, cache)
        w.deleteLater()

    def test_image_merge_worker_instantiation(self):
        w = ImageMergeWorker(image_paths=[], output_path="out.pdf")
        self.assertEqual(w.image_paths, [])
        self.assertEqual(w.output_path, "out.pdf")
        w.deleteLater()


@unittest.skipUnless(HAS_DEPS, "PyQt6 / worker 依赖不可用")
class TestWorkerSignalContracts(unittest.TestCase):
    """Worker 必须声明契约信号，MainWindow 依赖这些信号接线。"""

    def test_ocr_worker_signals(self):
        self.assertTrue(hasattr(OCRWorker, "finished_signal"))
        self.assertTrue(hasattr(OCRWorker, "progress_signal"))
        self.assertTrue(hasattr(OCRWorker, "page_result_signal"))
        self.assertTrue(hasattr(OCRWorker, "error_signal"))

    def test_word_worker_signals(self):
        self.assertTrue(hasattr(WordWorker, "finished_signal"))
        self.assertTrue(hasattr(WordWorker, "progress_signal"))

    def test_batch_replace_worker_signals(self):
        self.assertTrue(hasattr(WordBatchReplaceWorker, "progress_signal"))
        self.assertTrue(hasattr(WordBatchReplaceWorker, "file_done_signal"))
        self.assertTrue(hasattr(WordBatchReplaceWorker, "file_error_signal"))
        self.assertTrue(hasattr(WordBatchReplaceWorker, "finished_signal"))

    def test_doc_search_worker_signals(self):
        self.assertTrue(hasattr(DocSearchWorker, "progress_signal"))
        self.assertTrue(hasattr(DocSearchWorker, "hit_signal"))
        self.assertTrue(hasattr(DocSearchWorker, "finished_signal"))
        self.assertTrue(hasattr(DocSearchWorker, "error_signal"))

    def test_image_merge_worker_signals(self):
        self.assertTrue(hasattr(ImageMergeWorker, "finished_signal"))
        self.assertTrue(hasattr(ImageMergeWorker, "progress_signal"))
        self.assertTrue(hasattr(ImageMergeWorker, "error_signal"))


@unittest.skipUnless(HAS_DEPS, "PyQt6 / worker 依赖不可用")
class TestWorkerInterruption(unittest.TestCase):
    """所有 Worker 继承 QThread 标准中断路径，主线程通过 requestInterruption 取消。

    注：QThread.requestInterruption() 仅在线程运行时设置中断标志，
    未 start() 时 isInterruptionRequested() 恒为 False（Qt 行为）。
    因此这里验证方法契约存在性，而非在线程未启动时测试标志位翻转。
    """

    def test_ocr_worker_has_interruption_api(self):
        self.assertTrue(callable(getattr(OCRWorker, "requestInterruption", None)))
        self.assertTrue(callable(getattr(OCRWorker, "isInterruptionRequested", None)))

    def test_word_worker_has_interruption_api(self):
        self.assertTrue(callable(getattr(WordWorker, "requestInterruption", None)))
        self.assertTrue(callable(getattr(WordWorker, "isInterruptionRequested", None)))

    def test_image_merge_worker_has_interruption_api(self):
        self.assertTrue(callable(getattr(ImageMergeWorker, "requestInterruption", None)))
        self.assertTrue(callable(getattr(ImageMergeWorker, "isInterruptionRequested", None)))


@unittest.skipUnless(HAS_DEPS, "PyQt6 / worker 依赖不可用")
class TestBatchReplaceWorkerDecisions(unittest.TestCase):
    """WordBatchReplaceWorker 的跨线程错误决策交互（provide_error_decision）。"""

    def test_provide_error_decision_sets_skip(self):
        w = WordBatchReplaceWorker([], [], "[默认]")
        self.assertIsNone(w._error_decision)
        w.provide_error_decision("skip")
        self.assertEqual(w._error_decision, "skip")
        w.deleteLater()

    def test_provide_error_decision_sets_stop(self):
        w = WordBatchReplaceWorker([], [], "[默认]")
        w.provide_error_decision("stop")
        self.assertEqual(w._error_decision, "stop")
        w.deleteLater()

    def test_wait_for_error_decision_returns_skip_on_set(self):
        """_wait_for_error_decision 在 decision 被设置后应立即返回该 decision。"""
        import threading
        w = WordBatchReplaceWorker([], [], "[默认]")
        result = {}

        def _consumer():
            result["decision"] = w._wait_for_error_decision()

        t = threading.Thread(target=_consumer)
        t.start()
        # 让 consumer 进入 wait 状态
        import time
        time.sleep(0.05)
        w.provide_error_decision("skip")
        t.join(timeout=2.0)
        self.assertFalse(t.is_alive(), "consumer 线程应在 decision 设置后退出")
        self.assertEqual(result["decision"], "skip")
        w.deleteLater()


@unittest.skipUnless(HAS_DEPS, "PyQt6 / worker 依赖不可用")
class TestImageMergeWorkerEmptyRun(unittest.TestCase):
    """ImageMergeWorker 空输入边界：run() 同步执行不应崩溃。"""

    def test_run_empty_image_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "empty.pdf")
            w = ImageMergeWorker(image_paths=[], output_path=out)
            # 同步调用 run()（不经过 start/事件循环），验证空输入不抛
            w.run()
            w.deleteLater()


@unittest.skipUnless(HAS_DEPS, "PyQt6 / worker 依赖不可用")
class TestWordWorkerFindMatches(unittest.TestCase):
    """WordWorker._find_matches 纯函数行为（Luhn / 校验位门控）。"""

    def _make_worker(self, rules, custom_keywords=""):
        return WordWorker(
            word_doc=None,
            word_data={},
            rules=rules,
            custom_keywords=custom_keywords,
            replacement_text="[已脱敏]",
        )

    def test_phone_pattern_matched(self):
        w = self._make_worker([r"1[3-9]\d{9}"])
        matches = w._find_matches("联系电话 13812345678 请回拨")
        self.assertTrue(any(m["text"] == "13812345678" for m in matches))
        w.deleteLater()

    def test_custom_keyword_matched(self):
        w = self._make_worker([], custom_keywords="张三")
        matches = w._find_matches("原告张三与被告李四")
        self.assertTrue(any("张三" in m["text"] for m in matches))
        w.deleteLater()

    def test_invalid_luhn_bank_card_skipped(self):
        """被识别为银行卡 pattern 且 13-19 位纯数字不满足 Luhn 校验应被跳过（cp57）。

        注：_is_bank_card_pattern 要求 pattern 含 [1-9]\\d{N} 特征，
        故用 [1-9]\\d{15} 而非 \\d{16}（后者不触发 Luhn 校验）。
        """
        w = self._make_worker([r"[1-9]\d{15}"])
        # 1234567890123456 不满足 Luhn 校验（校验和 64 % 10 != 0）
        matches = w._find_matches("卡号 1234567890123456 结束")
        self.assertFalse(any(m["text"] == "1234567890123456" for m in matches))
        w.deleteLater()

    def test_no_match_returns_empty(self):
        w = self._make_worker([r"1[3-9]\d{9}"])
        matches = w._find_matches("这里没有敏感信息")
        self.assertEqual(matches, [])
        w.deleteLater()


if __name__ == "__main__":
    unittest.main()
