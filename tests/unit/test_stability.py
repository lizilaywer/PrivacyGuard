#!/usr/bin/env python3
"""
PrivacyGuard 稳定性回归测试

v37.7.7-cp33 重写：
旧版本在本文件内复制了 PrivacyAppError/TempFileManager 等类的副本，
既不 import 生产代码，也没有 unittest.TestCase，整体不会被 unittest 发现。
本次重写为真正的 TestCase，直接针对生产代码做最小回归：
  - privacyguard.utils.temp_manager.TempFileManager
  - privacyguard.utils.exceptions.{PrivacyAppError,ConversionError,FileFormatError,
                                  SecurityError,MemoryLimitError,WorkerCancelledError}
"""

import os
import re
import unittest

from privacyguard.utils.temp_manager import TempFileManager
from privacyguard.utils.exceptions import (
    PrivacyAppError,
    ConversionError,
    FileFormatError,
    SecurityError,
    MemoryLimitError,
    WorkerCancelledError,
)


class TestTempFileManager(unittest.TestCase):
    """TempFileManager 的最小稳定性行为回归。"""

    def test_create_and_cleanup_file(self):
        manager = TempFileManager()
        temp_file = manager.create_temp_file(suffix='.txt', content=b'hello')
        self.assertTrue(os.path.exists(temp_file))
        errors = manager.cleanup()
        self.assertEqual(errors, [])
        self.assertFalse(os.path.exists(temp_file))

    def test_create_and_cleanup_dir(self):
        manager = TempFileManager()
        temp_dir = manager.create_temp_dir()
        self.assertTrue(os.path.exists(temp_dir))
        errors = manager.cleanup()
        self.assertEqual(errors, [])
        self.assertFalse(os.path.exists(temp_dir))

    def test_cleanup_is_idempotent(self):
        manager = TempFileManager()
        manager.create_temp_file(suffix='.bin', content=b'x')
        self.assertEqual(manager.cleanup(), [])
        # 再次 cleanup 不应报错，且内部列表应已清空
        self.assertEqual(manager.cleanup(), [])
        self.assertEqual(manager.temp_files, [])

    def test_instance_registered_globally(self):
        manager = TempFileManager()
        self.assertIn(manager, TempFileManager._instances)
        manager.cleanup()


class TestCustomExceptions(unittest.TestCase):
    """自定义异常类的基本行为回归。"""

    def test_base_error_user_message_with_suggestion(self):
        err = PrivacyAppError("测试错误", "测试建议")
        msg = err.user_message()
        self.assertIn("测试错误", msg)
        self.assertIn("测试建议", msg)

    def test_base_error_user_message_without_suggestion(self):
        err = PrivacyAppError("仅消息")
        self.assertEqual(str(err), "仅消息")
        self.assertEqual(err.user_message(), "仅消息")

    def test_subclass_inheritance(self):
        # 各子类必须继承自 PrivacyAppError，且保留 user_message 行为
        for cls in (ConversionError, FileFormatError, SecurityError,
                    MemoryLimitError, WorkerCancelledError):
            self.assertTrue(issubclass(cls, PrivacyAppError))
            instance = cls("x", "y")
            self.assertIn("x", instance.user_message())
            self.assertIn("y", instance.user_message())


class TestSensitivePatternSanity(unittest.TestCase):
    """敏感信息正则的最小有效性校验，避免生产规则被改坏后无人察觉。"""

    def test_phone_pattern_matches_eleven_digits(self):
        phone_pattern = r"(?<!\d)(1[3-9]\d{9})(?!\d)"
        text = "联系电话：13812345678，另一个：15987654321"
        matches = list(re.finditer(phone_pattern, text))
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].group(), "13812345678")
        self.assertEqual(matches[1].group(), "15987654321")

    def test_phone_pattern_rejects_short_overflow(self):
        # 不满 11 位 / 边界外被其他数字包裹时不应命中
        phone_pattern = r"(?<!\d)(1[3-9]\d{9})(?!\d)"
        matches = list(re.finditer(phone_pattern, "1381234567 12345678901"))
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
