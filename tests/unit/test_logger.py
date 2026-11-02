"""v37.8.11 P0-3: 统一日志框架单元测试

验证 privacyguard.utils.logger 的核心行为：
- init_logging 幂等性（重复调用不重复叠加 handler）
- get_logger 返回命名 logger
- 日志级别从环境变量读取
- 文件 handler 在可写目录下正常创建并滚动
- 未初始化时不自动配置（import 阶段无副作用）
"""

import logging
import os
import shutil
import tempfile
import unittest

from privacyguard.utils import logger as logger_mod


class _HandlerSnapshot:
    """保存/恢复根 logger 的 handler 与级别，避免测试间污染。"""

    def __enter__(self):
        self._root = logging.getLogger()
        self._old_level = self._root.level
        self._old_handlers = list(self._root.handlers)
        # 重置模块初始化标志，允许测试重新初始化
        self._old_initialized = logger_mod._initialized
        logger_mod._initialized = False
        # 清空现有 handler，确保测试从干净状态开始
        for h in list(self._root.handlers):
            self._root.removeHandler(h)
        return self

    def __exit__(self, *exc):
        # 恢复原始状态：关闭测试期间创建的 handler（避免文件句柄泄漏）
        for h in list(self._root.handlers):
            self._root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass
        for h in self._old_handlers:
            self._root.addHandler(h)
        self._root.setLevel(self._old_level)
        logger_mod._initialized = self._old_initialized
        return False


class LoggerInitTest(unittest.TestCase):
    """init_logging 行为测试。"""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="pg_logger_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_init_logging_creates_file_and_console_handlers(self):
        with _HandlerSnapshot():
            root = logger_mod.init_logging(
                level=logging.DEBUG, log_dir=self.tmp_dir, console=True
            )
            self.assertTrue(logger_mod.is_initialized())
            handler_types = {type(h).__name__ for h in root.handlers}
            self.assertIn("RotatingFileHandler", handler_types)
            self.assertIn("StreamHandler", handler_types)
            # 日志文件应被创建
            self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "app.log")))

    def test_init_logging_idempotent_no_duplicate_handlers(self):
        with _HandlerSnapshot():
            logger_mod.init_logging(level=logging.INFO, log_dir=self.tmp_dir)
            count_after_first = len(logging.getLogger().handlers)
            logger_mod.init_logging(level=logging.INFO, log_dir=self.tmp_dir)
            count_after_second = len(logging.getLogger().handlers)
            # 幂等：第二次调用不新增 handler
            self.assertEqual(count_after_first, count_after_second)

    def test_init_logging_without_console(self):
        with _HandlerSnapshot():
            root = logger_mod.init_logging(
                level=logging.INFO, log_dir=self.tmp_dir, console=False
            )
            handler_types = {type(h).__name__ for h in root.handlers}
            self.assertIn("RotatingFileHandler", handler_types)
            self.assertNotIn("StreamHandler", handler_types)

    def test_init_logging_string_level(self):
        with _HandlerSnapshot():
            root = logger_mod.init_logging(
                level="WARNING", log_dir=self.tmp_dir, console=False
            )
            self.assertEqual(root.level, logging.WARNING)

    def test_init_logging_env_level(self):
        with _HandlerSnapshot():
            old = os.environ.get("PG_LOG_LEVEL")
            os.environ["PG_LOG_LEVEL"] = "DEBUG"
            try:
                root = logger_mod.init_logging(
                    log_dir=self.tmp_dir, console=False
                )
                self.assertEqual(root.level, logging.DEBUG)
            finally:
                if old is None:
                    os.environ.pop("PG_LOG_LEVEL", None)
                else:
                    os.environ["PG_LOG_LEVEL"] = old


class GetLoggerTest(unittest.TestCase):
    """get_logger 行为测试。"""

    def test_get_logger_returns_named_logger(self):
        lg = logger_mod.get_logger("test_named_logger")
        self.assertIsInstance(lg, logging.Logger)
        self.assertEqual(lg.name, "test_named_logger")

    def test_get_logger_default_name(self):
        lg = logger_mod.get_logger()
        self.assertEqual(lg.name, "privacyguard")

    def test_get_logger_no_side_effects_before_init(self):
        # 未初始化时调用 get_logger 不应自动配置根 logger
        with _HandlerSnapshot():
            logger_mod._initialized = False
            before = len(logging.getLogger().handlers)
            logger_mod.get_logger("uninit_check")
            after = len(logging.getLogger().handlers)
            self.assertEqual(before, after)


class FileOutputTest(unittest.TestCase):
    """日志文件写入测试。"""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="pg_logger_out_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_log_writes_to_file(self):
        with _HandlerSnapshot():
            logger_mod.init_logging(
                level=logging.DEBUG, log_dir=self.tmp_dir, console=False
            )
            lg = logger_mod.get_logger("file_output_test")
            lg.info("test_marker_line_42")
            # flush 所有 handler
            for h in logging.getLogger().handlers:
                h.flush()
            log_path = os.path.join(self.tmp_dir, "app.log")
            with open(log_path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("test_marker_line_42", content)
            self.assertIn("INFO", content)


if __name__ == "__main__":
    unittest.main()
