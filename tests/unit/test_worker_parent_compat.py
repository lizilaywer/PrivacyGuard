# -*- coding: utf-8 -*-
"""v40.1.4：Worker parent 构造契约回归。

背景：模块层 OCRWorker / WordBatchReplaceWorker 缺 parent 形参，而 main.py
包装器/调用点自 cp132 起传 parent= → 智能扫描/全文遮罩/批量替换构造即
TypeError（用户真机触发暴露的潜伏 Bug，且单元测试从未构造 worker 故不报警）。
本测试用最小参数构造全部 worker（不 start），锁死签名契约。
"""
import unittest

try:
    from PyQt6.QtCore import Qt, QCoreApplication
    # 与 main.py 启动一致：WebEngine 要求在 QCoreApplication 创建前设置共享 GL 上下文
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    from PyQt6.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication([])
    HAS_QT = True
except Exception:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 不可用")
class TestWorkerParentCompat(unittest.TestCase):
    def _dispose(self, worker):
        try:
            worker.deleteLater()
        except Exception:
            pass

    def test_modular_ocr_worker_accepts_parent(self):
        from privacyguard.workers.ocr_worker import OCRWorker
        w = OCRWorker("", [], False, "", 1.0, 0, 0, parent=None)
        self._dispose(w)

    def test_batch_replace_worker_accepts_parent(self):
        from privacyguard.workers.batch_replace_worker import WordBatchReplaceWorker
        w = WordBatchReplaceWorker([], [], "[已脱敏]", parent=None)
        self._dispose(w)

    def test_word_worker_accepts_parent(self):
        from privacyguard.workers.word_worker import WordWorker
        w = WordWorker(None, {}, [], "", "[已脱敏]", parent=None)
        self._dispose(w)

    def test_image_merge_worker_accepts_parent(self):
        from privacyguard.workers.image_merge import ImageMergeWorker
        w = ImageMergeWorker([], "/tmp/pg_test_merge_out.pdf", parent=None)
        self._dispose(w)

    def test_doc_search_worker_accepts_parent(self):
        from privacyguard.workers.search_worker import DocSearchWorker
        w = DocSearchWorker(b"", "词", {}, parent=None)
        self._dispose(w)

    def test_main_wrapper_ocr_worker_constructs(self):
        """main.py 兼容包装器（注入 box_adjust_ratio + 传 parent）整链构造。"""
        from main import OCRWorker as MainOCRWorker
        w = MainOCRWorker("", [], False, "", 1.0, 0, 0, parent=None)
        self._dispose(w)

    def test_settings_dialog_accepts_open_settings_kwargs(self):
        """open_settings 的完整 kwargs 必须可构造（防签名漂移再致设置打不开）。

        v40.1.4：cp_bookmark 起 open_settings 传 bookmark_redact_enabled= 而
        SettingsDialog 无此形参，设置对话框自 v40.1.0 起构造即 TypeError。
        """
        from privacyguard.ui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(
            None, [], False, "", 2.0, 0, 0, "[已脱敏]", [],
            config_manager=None,
            custom_keyword_rules=[],
            manual_replace_prompt=False,
            bookmark_redact_enabled=True,
            doc_context="pdf",
            default_rules={})
        # 开关值往返（open_settings 经 getattr 回读）
        self.assertTrue(dlg.bookmark_redact_enabled)
        # v40.1.4 恢复检查：勾选框控件存在且状态同步（08a2c51 曾误删）
        self.assertTrue(hasattr(dlg, "cb_bookmark_redact"))
        self.assertTrue(dlg.cb_bookmark_redact.isChecked())
        dlg.cb_bookmark_redact.setChecked(False)
        self.assertFalse(dlg.cb_bookmark_redact.isChecked())
        dlg.deleteLater()


if __name__ == "__main__":
    unittest.main()
