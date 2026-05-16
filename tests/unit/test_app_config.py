import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import SimpleConfig, read_app_version
from privacyguard.utils.config import ConfigManager, DEFAULT_CONFIG


class TestAppConfig(unittest.TestCase):

    def test_read_app_version_matches_version_file(self):
        expected = (Path(__file__).resolve().parents[2] / "version.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(read_app_version(), expected)

    def test_read_app_version_falls_back_to_current_release(self):
        with patch("main.Path.read_text", side_effect=OSError):
            self.assertEqual(read_app_version(), "37.7.6")

    def test_simple_config_save_persists_multiple_values(self):
        fd, temp_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump({}, handle)

            config = SimpleConfig(temp_path)
            config.set("redaction.scan.default_level", 2.5, persist=False)
            config.set("redaction.custom_keywords", "甲方\n乙方", persist=False)
            config.set("redaction.replacement_text", "[已脱敏]", persist=False)
            self.assertTrue(config.save())

            reloaded = SimpleConfig(temp_path)
            self.assertEqual(reloaded.get("redaction.scan.default_level"), 2.5)
            self.assertEqual(reloaded.get("redaction.custom_keywords"), "甲方\n乙方")
            self.assertEqual(reloaded.get("redaction.replacement_text"), "[已脱敏]")
        finally:
            os.remove(temp_path)

    def test_config_manager_reads_same_config_json_as_simple_config(self):
        """ConfigManager 和 SimpleConfig 读取同一 config.json 时值应一致。"""
        simple = SimpleConfig()
        # 重置 ConfigManager 单例以确保加载最新配置
        ConfigManager._instance = None
        manager = ConfigManager()

        # 关键值一致性检查
        self.assertEqual(
            simple.get("redaction.replacement_text"),
            manager.get("redaction.replacement_text"),
            "replacement_text 在两套系统中不一致"
        )
        self.assertEqual(
            simple.get("redaction.scan.default_level"),
            manager.get("redaction.scan.default_level"),
            "scan.default_level 在两套系统中不一致"
        )

    def test_config_manager_persists_on_set(self):
        """ConfigManager.set(persist=True) 应立即写入文件。"""
        fd, temp_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(DEFAULT_CONFIG, handle)

            # 重置单例
            ConfigManager._instance = None
            manager = ConfigManager(temp_path)
            manager.set("redaction.scan.default_level", 2.0, persist=True)

            # 从文件直接读取验证
            with open(temp_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            self.assertEqual(
                file_config.get("redaction", {}).get("scan", {}).get("default_level"),
                2.0
            )
        finally:
            os.remove(temp_path)
