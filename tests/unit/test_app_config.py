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
        expected = (Path(__file__).resolve().parents[2] / "version.txt").read_text(encoding="utf-8").strip()
        with patch("main.Path.read_text", side_effect=OSError):
            self.assertEqual(read_app_version(), expected)

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

    def test_simple_config_pii_settings_default(self):
        """Phase 1: SimpleConfig 未设置 pii_settings.* 时 get() 返回 None（默认值由 MainWindow 提供）。"""
        fd, temp_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump({}, handle)

            config = SimpleConfig(temp_path)
            # 缺失时返回 None（MainWindow 应用自己的 fallback）
            self.assertIsNone(config.get("pii_settings.engine_enabled"))
            self.assertIsNone(config.get("pii_settings.auto_redact"))
            self.assertIsNone(config.get("pii_settings.require_confirmation"))
        finally:
            os.remove(temp_path)

    def test_simple_config_pii_settings_round_trip(self):
        """Phase 1: SimpleConfig pii_settings.* 三键 set + save + reload 完整往返。"""
        fd, temp_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump({}, handle)

            config = SimpleConfig(temp_path)
            config.set("pii_settings.engine_enabled", True, persist=False)
            config.set("pii_settings.auto_redact", False, persist=False)
            config.set("pii_settings.require_confirmation", True, persist=False)
            self.assertTrue(config.save())

            reloaded = SimpleConfig(temp_path)
            self.assertEqual(reloaded.get("pii_settings.engine_enabled"), True)
            self.assertEqual(reloaded.get("pii_settings.auto_redact"), False)
            self.assertEqual(reloaded.get("pii_settings.require_confirmation"), True)
        finally:
            os.remove(temp_path)

    # ----------------------------------------------------------------------
    # Phase 2 (02-03-main-py-settings-packaging) — per_entity_default 字段
    # ----------------------------------------------------------------------

    def test_simple_config_pii_settings_per_entity_default_round_trip(self):
        """Phase 2: pii_settings.per_entity_default 字典 9 键 set + save + reload 完整往返。"""
        fd, temp_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump({}, handle)

            config = SimpleConfig(temp_path)
            per_entity = {
                "CN_ID_CARD": "partial",
                "CN_PHONE": "partial",
                "CN_BANK_CARD": "blackout",  # 一项设为 blackout 测试混合值
                "CN_EMAIL": "partial",
                "CN_USCC": "partial",
                "CN_TAXPAYER_ID": "partial",
                "CN_TAXPAYER_ID_15": "partial",
                "CN_VAT_INVOICE": "partial",
                "CN_BANK_ACCOUNT": "partial",
            }
            config.set("pii_settings.per_entity_default", per_entity, persist=False)
            self.assertTrue(config.save())

            reloaded = SimpleConfig(temp_path)
            loaded = reloaded.get("pii_settings.per_entity_default")
            self.assertIsInstance(loaded, dict)
            self.assertEqual(len(loaded), 9, f"per_entity_default 应有 9 键；实际 {len(loaded)}")
            # 混合值断言
            self.assertEqual(loaded["CN_BANK_CARD"], "blackout", "CN_BANK_CARD 应保留 blackout 值")
            self.assertEqual(loaded["CN_ID_CARD"], "partial", "CN_ID_CARD 应保留 partial 值")
            # 9 键全列
            for key in ("CN_ID_CARD", "CN_PHONE", "CN_BANK_CARD", "CN_EMAIL", "CN_USCC",
                        "CN_TAXPAYER_ID", "CN_TAXPAYER_ID_15", "CN_VAT_INVOICE", "CN_BANK_ACCOUNT"):
                self.assertIn(key, loaded, f"per_entity_default 缺失 {key}")
        finally:
            os.remove(temp_path)

    def test_simple_config_pii_settings_per_entity_default_default(self):
        """Phase 2: per_entity_default 字段缺失时返回 None（无默认；调用方处理缺失）。"""
        fd, temp_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump({}, handle)

            config = SimpleConfig(temp_path)
            # 缺失时返回 None（MainWindow 应用自己的 fallback；与 Phase 1 D-08 行为一致）
            self.assertIsNone(config.get("pii_settings.per_entity_default"))
        finally:
            os.remove(temp_path)
