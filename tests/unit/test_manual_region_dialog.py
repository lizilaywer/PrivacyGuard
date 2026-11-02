# -*- coding: utf-8 -*-
"""cp65 回归：手动框选脱敏弹窗的新增按钮行为。

覆盖：
- "清空"按钮：清空识别文字框
- "纯遮罩"按钮：强制 pure_mask_only=True、清空替换文本、取消全文遮罩、accept
- 调用方语义：pure_mask_only 时应跳过全文遮罩、使用空替换文本
"""
import unittest

try:
    from PyQt6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 未安装")
class TestManualRegionDialogButtons(unittest.TestCase):
    """cp65: 弹窗新增"清空"与"纯遮罩"按钮的行为。"""

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def _make_dlg(self, recognized="张三 12345", replace="默认替换", search_all=True):
        from privacyguard.ui.dialogs.manual_region_dialog import ManualRegionRedactDialog
        dlg = ManualRegionRedactDialog(parent=None, recognized_text=recognized)
        # 模拟用户预先填了替换文本和勾选了全文遮罩
        if replace:
            dlg.input_replace.setText(replace)
        if search_all:
            dlg.cb_search_all.setChecked(True)
        return dlg

    def test_clear_button_empties_recognized_text(self):
        """点"清空"按钮应清空识别文字框。"""
        dlg = self._make_dlg(recognized="待清空的文字")
        self.assertNotEqual(dlg.txt_recognized.toPlainText(), "")
        dlg._clear_text()
        self.assertEqual(dlg.txt_recognized.toPlainText(), "")

    def test_pure_mask_button_sets_flag_and_accepts(self):
        """点"纯遮罩"按钮应：置 pure_mask_only=True、清空替换文本、取消全文遮罩、accept。"""
        dlg = self._make_dlg(recognized="张三", replace="替换X", search_all=True)
        self.assertFalse(dlg.pure_mask_only)
        self.assertNotEqual(dlg.input_replace.text(), "")
        self.assertTrue(dlg.cb_search_all.isChecked())

        # 触发"纯遮罩"按钮（不真正 exec 事件循环，直接调槽）
        dlg._accept_pure_mask()

        # 标志与字段都被强制重置
        self.assertTrue(dlg.pure_mask_only)
        self.assertEqual(dlg.input_replace.text(), "")
        self.assertFalse(dlg.cb_search_all.isChecked())
        # 对话框进入 Accepted 状态（调用方靠 exec()==Accepted 进入处理分支）
        self.assertEqual(dlg.result(), dlg.DialogCode.Accepted)

    def test_pure_mask_only_property_overrides_search_and_replace(self):
        """pure_mask_only=True 时，search_whole_doc/replacement_text 应反映纯遮罩语义。"""
        dlg = self._make_dlg(recognized="张三", replace="替换X", search_all=True)
        dlg._accept_pure_mask()
        # 即使原本勾选了全文遮罩、填了替换文本，纯遮罩后都应无效化
        self.assertFalse(dlg.search_whole_doc)
        self.assertEqual(dlg.replacement_text, "")

    def test_normal_accept_keeps_user_choices(self):
        """对照测试：普通 accept（确定按钮）不影响用户填的替换文本/全文遮罩。"""
        dlg = self._make_dlg(recognized="张三", replace="替换Y", search_all=True)
        dlg.accept()
        self.assertFalse(dlg.pure_mask_only)
        self.assertTrue(dlg.search_whole_doc)
        self.assertEqual(dlg.replacement_text, "替换Y")


if __name__ == "__main__":
    unittest.main()
