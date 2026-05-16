"""验证 SimpleConfig 与 ConfigManager 的配置值一致性。"""
import json
import inspect
import unittest
from pathlib import Path

from main import SimpleConfig, read_app_version
from privacyguard.utils.config import ConfigManager, DEFAULT_CONFIG


class TestConfigAlignment(unittest.TestCase):
    """确保两套配置系统不发生漂移。"""

    def _get_config_json(self):
        config_path = Path(__file__).resolve().parents[2] / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_replacement_text_matches(self):
        """replacement_text 在 config.json 和 DEFAULT_CONFIG 中必须一致。"""
        config_json = self._get_config_json()
        json_val = config_json.get("redaction", {}).get("replacement_text")
        default_val = DEFAULT_CONFIG.get("redaction", {}).get("replacement_text")
        self.assertEqual(json_val, default_val,
            f"replacement_text 不一致: config.json={json_val!r}, DEFAULT_CONFIG={default_val!r}")

    def test_scan_default_level_matches(self):
        """扫描默认级别必须一致。"""
        config_json = self._get_config_json()
        json_val = config_json.get("redaction", {}).get("scan", {}).get("default_level")
        default_val = DEFAULT_CONFIG.get("redaction", {}).get("scan", {}).get("default_level")
        self.assertEqual(json_val, default_val,
            f"scan.default_level 不一致: config.json={json_val!r}, DEFAULT_CONFIG={default_val!r}")

    def test_scan_available_levels_match(self):
        """可用扫描级别列表必须一致。"""
        config_json = self._get_config_json()
        json_val = config_json.get("redaction", {}).get("scan", {}).get("available_levels")
        default_val = DEFAULT_CONFIG.get("redaction", {}).get("scan", {}).get("available_levels")
        self.assertEqual(json_val, default_val,
            f"scan.available_levels 不一致: config.json={json_val!r}, DEFAULT_CONFIG={default_val!r}")

    def test_custom_keywords_matches(self):
        """自定义关键词默认值必须一致。"""
        config_json = self._get_config_json()
        json_val = config_json.get("redaction", {}).get("custom_keywords")
        default_val = DEFAULT_CONFIG.get("redaction", {}).get("custom_keywords")
        self.assertEqual(json_val, default_val,
            f"custom_keywords 不一致: config.json={json_val!r}, DEFAULT_CONFIG={default_val!r}")

    def test_default_rules_names_match(self):
        """默认规则名称集合必须一致。"""
        config_json = self._get_config_json()
        json_rules = set(config_json.get("redaction", {}).get("default_rules", {}).keys())
        default_rules = set(DEFAULT_CONFIG.get("redaction", {}).get("default_rules", {}).keys())
        self.assertEqual(json_rules, default_rules,
            f"规则名称不一致: config.json 多出 {json_rules - default_rules}, "
            f"DEFAULT_CONFIG 多出 {default_rules - json_rules}")

    def test_ocr_box_adjust_keys_present(self):
        """DEFAULT_CONFIG 必须包含 ocr.box_adjust_ratio 和 ocr.box_adjust_range。"""
        ocr = DEFAULT_CONFIG.get("ocr", {})
        self.assertIn("box_adjust_ratio", ocr,
            "DEFAULT_CONFIG 缺少 ocr.box_adjust_ratio")
        self.assertIn("box_adjust_range", ocr,
            "DEFAULT_CONFIG 缺少 ocr.box_adjust_range")

    def test_precise_locator_present(self):
        """DEFAULT_CONFIG 必须包含 redaction.precise_locator。"""
        redaction = DEFAULT_CONFIG.get("redaction", {})
        self.assertIn("precise_locator", redaction,
            "DEFAULT_CONFIG 缺少 redaction.precise_locator")

    def test_seal_rule_present(self):
        """DEFAULT_CONFIG 必须包含印章规则。"""
        rules = DEFAULT_CONFIG.get("redaction", {}).get("default_rules", {})
        self.assertIn("印章", rules, "DEFAULT_CONFIG 缺少印章规则")

    def test_simple_config_reads_config_json_values(self):
        """SimpleConfig 应能正确读取 config.json 的值。"""
        config = SimpleConfig()
        self.assertEqual(config.get("redaction.replacement_text"), "*")
        self.assertEqual(config.get("redaction.scan.default_level"), 1.5)

    def test_config_manager_persist_default_is_true(self):
        """ConfigManager.set() 的 persist 默认值应为 True。"""
        sig = inspect.signature(ConfigManager.set)
        persist_param = sig.parameters.get("persist")
        self.assertIsNotNone(persist_param)
        self.assertEqual(persist_param.default, True,
            "ConfigManager.set() persist 应默认为 True，防止配置静默丢失")

    def test_simple_config_persist_default_is_true(self):
        """SimpleConfig.set() 的 persist 默认值应为 True。"""
        sig = inspect.signature(SimpleConfig.set)
        persist_param = sig.parameters.get("persist")
        self.assertIsNotNone(persist_param)
        self.assertEqual(persist_param.default, True,
            "SimpleConfig.set() persist 应默认为 True")


class TestVersionSource(unittest.TestCase):
    """验证版本来源唯一性。"""

    def test_version_txt_is_single_source(self):
        """version.txt 应为唯一版本源。"""
        version_from_file = read_app_version()
        version_txt = (Path(__file__).resolve().parents[2] / "version.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(version_from_file, version_txt)
        self.assertTrue(version_from_file.startswith("37."),
            f"版本号格式异常: {version_from_file}")
