#!/usr/bin/env python3
"""RapidOCR API 冒烟测试（无硬编码路径）。"""

import unittest


class TestRapidOCRAPI(unittest.TestCase):
    def test_import_and_init(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            self.skipTest("rapidocr_onnxruntime 未安装")

        ocr = RapidOCR()
        self.assertIsNotNone(ocr)
        self.assertTrue(callable(ocr))

    def test_public_methods_available(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            self.skipTest("rapidocr_onnxruntime 未安装")

        ocr = RapidOCR()
        public_methods = [m for m in dir(ocr) if not m.startswith("_")]
        # 至少应该暴露可调用接口
        self.assertGreater(len(public_methods), 0)


if __name__ == "__main__":
    unittest.main()
