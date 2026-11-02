#!/usr/bin/env python3
"""RapidOCR API 冒烟测试（无硬编码路径）。

v37.7.14 cp44: 升级到 RapidOCR v3.x，导入路径从 rapidocr_onnxruntime 改为 rapidocr。
v37.7.7-cp33 增强：
旧版本第二条用例只断言 `len(public_methods) > 0`，
属于恒真断言（任何对象都至少有 1 个非下划线属性）。
本次改为：
  - 验证 RapidOCR 实例可调用（`__call__` 存在）
  - 验证至少暴露一个公共调用入口（`__call__` 或常见方法名）
  - 验证 `__call__` 接收至少一个位置参数（兼容旧调用约定）
"""

import inspect
import unittest


class TestRapidOCRAPI(unittest.TestCase):
    def test_import_and_init(self):
        try:
            from rapidocr import RapidOCR
        except ImportError:
            self.skipTest("rapidocr 未安装")

        ocr = RapidOCR()
        self.assertIsNotNone(ocr)
        self.assertTrue(callable(ocr))

    def test_public_methods_available(self):
        try:
            from rapidocr import RapidOCR
        except ImportError:
            self.skipTest("rapidocr 未安装")

        ocr = RapidOCR()
        public_methods = [m for m in dir(ocr) if not m.startswith("_")]
        # 必须暴露可调用入口：__call__ 或至少一个公共方法
        self.assertTrue(
            callable(ocr) or any(callable(getattr(ocr, m, None)) for m in public_methods),
            "RapidOCR 实例既不可调用，也未暴露任何公共方法",
        )

    def test_call_signature_accepts_image(self):
        """验证 RapidOCR 实例可调用且接受至少一个位置参数。"""
        try:
            from rapidocr import RapidOCR
        except ImportError:
            self.skipTest("rapidocr 未安装")

        ocr = RapidOCR()
        self.assertTrue(callable(ocr), "RapidOCR 实例应当可调用")
        try:
            sig = inspect.signature(ocr.__call__)
        except (TypeError, ValueError):
            # 某些版本的 RapidOCR 是 C 扩展，签名可能不可读，跳过参数检查
            self.skipTest("RapidOCR.__call__ 签名不可内省")
        params = list(sig.parameters.values())
        self.assertGreaterEqual(
            len(params), 1,
            f"RapidOCR.__call__ 应接受至少一个参数，实际签名: {sig}",
        )


if __name__ == "__main__":
    unittest.main()
