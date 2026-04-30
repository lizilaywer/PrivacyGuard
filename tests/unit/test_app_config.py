import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import SimpleConfig, read_app_version


class TestAppConfig(unittest.TestCase):

    def test_read_app_version_matches_version_file(self):
        expected = (Path(__file__).resolve().parents[2] / "version.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(read_app_version(), expected)

    def test_read_app_version_falls_back_to_current_release(self):
        with patch("main.Path.read_text", side_effect=OSError):
            self.assertEqual(read_app_version(), "37.7.4")

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
