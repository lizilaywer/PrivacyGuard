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
        if not config_path.exists():
            config_path = config_path.with_name("config.json.template")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_replacement_text_is_valid(self):
        """替换词是用户偏好，模板/持久化值不必等于共享模块的回退值。"""
        config_json = self._get_config_json()
        json_val = config_json.get("redaction", {}).get("replacement_text")
        default_val = DEFAULT_CONFIG.get("redaction", {}).get("replacement_text")
        for value in (json_val, default_val):
            self.assertIsInstance(value, str)
            self.assertTrue(value.strip())

    def test_scan_default_level_matches(self):
        """扫描默认级别：config.json 为用户运行时可持久化的选择（如推荐的 1.5x），
        不应与 DEFAULT_CONFIG（出厂默认）强一致；改为验证其为合法级别。

        参照 cp45 对 custom_keywords 的放宽：SimpleConfig.set(persist=True) 会把
        用户在界面选择的扫描级别回写 config.json，导致与出厂默认值合法地不一致。

        cp120: DEFAULT_CONFIG 出厂默认从 1.0 提升到 1.5（1.0 下 OCR 文本检测模型
        会漏检小字/落款，实测扫描件落款处整行漏检）。
        """
        config_json = self._get_config_json()
        scan_json = config_json.get("redaction", {}).get("scan", {})
        json_val = scan_json.get("default_level")
        available_json = scan_json.get("available_levels", [])

        default_scan = DEFAULT_CONFIG.get("redaction", {}).get("scan", {})
        default_val = default_scan.get("default_level")
        available_default = default_scan.get("available_levels", [])

        # 两边都必须是合法数值
        self.assertIsInstance(json_val, (int, float),
            "config.json 缺少合法的 redaction.scan.default_level")
        self.assertIsInstance(default_val, (int, float),
            "DEFAULT_CONFIG 缺少合法的 redaction.scan.default_level")
        # config.json 的值（可能是用户持久化的选择）必须在可用级别列表内
        self.assertIn(json_val, available_json,
            f"config.json 的 scan.default_level={json_val} 不在 available_levels={available_json} 内")
        # DEFAULT_CONFIG 的出厂默认值也必须是其可用级别之一
        self.assertIn(default_val, available_default,
            f"DEFAULT_CONFIG 的 scan.default_level={default_val} 不在其 available_levels={available_default} 内")

    def test_scan_default_level_is_1_5(self):
        """cp120: DEFAULT_CONFIG 出厂默认 scan_level 应为 1.5（非 1.0）。

        1.0 渲染分辨率过低导致 OCR 漏检小字（实测扫描件落款"池州市"整行漏检），
        cp120 将默认提升到 1.5（与 UI "推荐" 标注一致）。此测试固化该决策防回退。
        """
        default_val = DEFAULT_CONFIG.get("redaction", {}).get("scan", {}).get("default_level")
        self.assertEqual(default_val, 1.5,
            f"DEFAULT_CONFIG scan.default_level 应为 1.5（cp120 OCR 漏检修复），实际 {default_val}")
        config_json = self._get_config_json()
        scan_json = config_json.get("redaction", {}).get("scan", {})
        json_val = scan_json.get("default_level")
        available_json = scan_json.get("available_levels", [])

        default_scan = DEFAULT_CONFIG.get("redaction", {}).get("scan", {})
        default_val = default_scan.get("default_level")
        available_default = default_scan.get("available_levels", [])

        # 两边都必须是合法数值
        self.assertIsInstance(json_val, (int, float),
            "config.json 缺少合法的 redaction.scan.default_level")
        self.assertIsInstance(default_val, (int, float),
            "DEFAULT_CONFIG 缺少合法的 redaction.scan.default_level")
        # config.json 的值（可能是用户持久化的选择）必须在可用级别列表内
        self.assertIn(json_val, available_json,
            f"config.json 的 scan.default_level={json_val} 不在 available_levels={available_json} 内")
        # DEFAULT_CONFIG 的出厂默认值也必须是其可用级别之一
        self.assertIn(default_val, available_default,
            f"DEFAULT_CONFIG 的 scan.default_level={default_val} 不在其 available_levels={available_default} 内")

    def test_scan_available_levels_match(self):
        """可用扫描级别列表必须一致。"""
        config_json = self._get_config_json()
        json_val = config_json.get("redaction", {}).get("scan", {}).get("available_levels")
        default_val = DEFAULT_CONFIG.get("redaction", {}).get("scan", {}).get("available_levels")
        self.assertEqual(json_val, default_val,
            f"scan.available_levels 不一致: config.json={json_val!r}, DEFAULT_CONFIG={default_val!r}")

    def test_custom_keywords_matches(self):
        """v37.7.15 cp45: custom_keywords 是用户运行时可改的配置，
        不应与 DEFAULT_CONFIG 强一致；改为只验证字段存在。
        原测试强一致要求在用户通过 GUI 修改并保存后即失效。
        """
        config_json = self._get_config_json()
        json_val = config_json.get("redaction", {}).get("custom_keywords")
        default_val = DEFAULT_CONFIG.get("redaction", {}).get("custom_keywords")
        # 两边都必须存在该字段（可为空字符串，但不能是 None）
        self.assertIsNotNone(json_val,
            "config.json 缺少 redaction.custom_keywords 字段")
        self.assertIsNotNone(default_val,
            "DEFAULT_CONFIG 缺少 redaction.custom_keywords 字段")
        # 类型必须是字符串
        self.assertIsInstance(json_val, str)
        self.assertIsInstance(default_val, str)

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

    def test_seal_rule_description_matches(self):
        """印章规则的 description 在 config.json 和 DEFAULT_CONFIG 中必须一致。"""
        config_json = self._get_config_json()
        json_seal = config_json.get("redaction", {}).get("default_rules", {}).get("印章", {})
        default_seal = DEFAULT_CONFIG.get("redaction", {}).get("default_rules", {}).get("印章", {})
        self.assertEqual(
            json_seal.get("description"),
            default_seal.get("description"),
            "印章规则 description 不一致",
        )

    def test_top_level_keys_match(self):
        """config.json 和 DEFAULT_CONFIG 的顶层键集合必须一致（忽略 _comment_* 注释字段）。"""
        config_json = self._get_config_json()
        json_keys = {k for k in config_json.keys() if not k.startswith("_")}
        default_keys = {k for k in DEFAULT_CONFIG.keys() if not k.startswith("_")}
        self.assertEqual(json_keys, default_keys,
            f"顶层键不一致: config.json 多出 {json_keys - default_keys}, "
            f"DEFAULT_CONFIG 多出 {default_keys - json_keys}")

    def test_redaction_section_keys_match(self):
        """排除注释和旧模板的未消费印章元数据，仍严格核对所有活动配置键。"""
        config_json = self._get_config_json()
        # 运行时从 default_rules["印章"] 启用检测；旧 seal_detection 不被读取。
        json_red = {k for k in config_json.get("redaction", {}).keys()
                    if not k.startswith("_") and k != "seal_detection"}
        default_red = {k for k in DEFAULT_CONFIG.get("redaction", {}).keys() if not k.startswith("_")}
        self.assertEqual(json_red, default_red,
            f"redaction 键不一致: config.json 多出 {json_red - default_red}, "
            f"DEFAULT_CONFIG 多出 {default_red - json_red}")

    def test_ocr_box_adjust_keys_match(self):
        """ocr.box_adjust_ratio 和 ocr.box_adjust_range 在两份配置中必须一致。"""
        config_json = self._get_config_json()
        json_ocr = config_json.get("ocr", {})
        default_ocr = DEFAULT_CONFIG.get("ocr", {})
        for key in ("box_adjust_ratio", "box_adjust_range"):
            self.assertEqual(json_ocr.get(key), default_ocr.get(key),
                f"ocr.{key} 不一致: config.json={json_ocr.get(key)!r}, "
                f"DEFAULT_CONFIG={default_ocr.get(key)!r}")

    def test_simple_config_and_config_manager_align_on_top_level(self):
        """SimpleConfig 与 ConfigManager 读取同一 config.json 时顶层键值应一致。"""
        simple = SimpleConfig()
        ConfigManager._instance = None
        manager = ConfigManager()
        config_json = self._get_config_json()
        for top_key in config_json.keys():
            if top_key.startswith("_"):
                continue
            self.assertEqual(simple.get(top_key), manager.get(top_key),
                f"顶层 {top_key} 在 SimpleConfig 与 ConfigManager 间不一致")

    def test_simple_config_reads_config_json_values(self):
        """SimpleConfig 应能正确读取 config.json 的值（以 config.json 实际内容为准）。"""
        config = SimpleConfig()
        config_json = self._get_config_json()
        redaction_json = config_json.get("redaction", {})
        self.assertEqual(config.get("redaction.replacement_text"),
                         redaction_json.get("replacement_text"))
        # scan.default_level 是用户运行时可持久化的值，验证 SimpleConfig 读到的与 config.json 一致即可
        self.assertEqual(config.get("redaction.scan.default_level"),
                         redaction_json.get("scan", {}).get("default_level"))

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
        # 验证版本号是 N.N.N 格式（数字.数字.数字），不绑定特定主版本号
        parts = version_from_file.split(".")
        self.assertTrue(len(parts) >= 2 and all(p.isdigit() for p in parts[:3]),
            f"版本号格式异常: {version_from_file}")
