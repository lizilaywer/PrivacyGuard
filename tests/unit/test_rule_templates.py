"""Untrusted templates, per-file isolation, private mapping and regex timeout."""
import copy
import json
import re
import tempfile
import time
import unittest
from pathlib import Path

from docx import Document

from privacyguard.utils.rule_templates import (validate_template, read_template, write_template,
    canonical_file, validate_file_plan, consistent_rules, preset_rules, plan_has_rules)
from privacyguard.utils.guarded_regex import RegexService, RuleBudgetError
from privacyguard.workers.batch_replace_worker import WordBatchReplaceWorker


def rule(find="SECRET", replacement="[REMOVED]"):
    return {"enabled": True, "mode": "exact", "find": find, "replace": replacement}


class RuleTemplatesTests(unittest.TestCase):
    def test_old_schema_migrates_without_mutating_input(self):
        original = {"version": 1, "rules": [rule()]}
        saved = copy.deepcopy(original)
        self.assertEqual(validate_template(original)["version"], 2)
        self.assertEqual(original, saved)

    def test_bad_structure_future_version_and_limits_rejected(self):
        for value in ([rule()], {"version": 99, "rules": []}, {"rules": [dict(rule(), enabled="false")]},
                      {"rules": [dict(rule(), mode="python")]}, {"rules": [rule()]*201},
                      {"rules": [dict(rule(), find="x"*2049)]}, {"rules": [], "execute": "anything"}):
            with self.subTest(value=str(value)[:80]), self.assertRaises(ValueError):
                validate_template(value)

    def test_atomic_template_roundtrip_and_size_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            write_template(path, [rule()], "[DEFAULT]")
            self.assertEqual(read_template(path)["rules"], [rule()])
            path.write_bytes(b" " * (1024*1024+1))
            with self.assertRaises(ValueError):
                read_template(path)

    def test_consistent_numbering_is_explicit_exact_only(self):
        rules = [rule("Alpha"), rule("Beta"), rule("ALPHA"), dict(rule("\\d+"), mode="regex")]
        numbered = consistent_rules(rules)
        self.assertEqual(numbered[0]["replace"], numbered[2]["replace"])
        self.assertNotEqual(numbered[0]["replace"], numbered[1]["replace"])
        self.assertEqual(numbered[3], rules[3])
        self.assertEqual(rules[0]["replace"], "[REMOVED]")

    def test_unknown_file_rejected_no_inherited_previous_rules(self):
        plan = validate_file_plan(["first.docx", "second.docx"], {canonical_file("first.docx"): [rule("FIRST")]}, [rule("COMMON")])
        self.assertEqual(plan[canonical_file("second.docx")][0]["find"], "COMMON")
        with self.assertRaises(ValueError):
            validate_file_plan(["first.docx"], {canonical_file("other.docx"): []}, [])

    def test_plan_can_use_preset_with_empty_common_rules(self):
        self.assertTrue(plan_has_rules({"file": preset_rules("合同")}, []))
        self.assertFalse(plan_has_rules({"file": None}, []))

    def test_real_batch_per_file_skip_and_report_no_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f"file{i}.docx" for i in range(3)]
            for path in paths:
                doc = Document(); doc.add_paragraph("FIRST SECOND KEEP"); doc.save(path)
            mapping = {canonical_file(paths[0]): [rule("FIRST")], canonical_file(paths[1]): [rule("SECOND")], canonical_file(paths[2]): None}
            worker = WordBatchReplaceWorker([str(p) for p in paths], [], "[DEFAULT]", file_plan=mapping)
            summaries = []
            worker.finished_signal.connect(summaries.append)
            worker.run()
            summary = summaries[0]
            self.assertEqual(len(summary["success"]), 2)
            self.assertEqual(len(summary["skipped"]), 1)
            self.assertEqual(summary["rules"], [])
            self.assertNotIn("FIRST", json.dumps(summary))
            text0 = Document(summary["success"][0]["output"]).paragraphs[0].text
            text1 = Document(summary["success"][1]["output"]).paragraphs[0].text
            self.assertEqual(text0, "[REMOVED] SECOND KEEP")
            self.assertEqual(text1, "FIRST [REMOVED] KEEP")


class GuardedRegexTests(unittest.TestCase):
    def setUp(self):
        self.service = RegexService()
        self.addCleanup(self.service.close)

    def test_same_python_re_semantics(self):
        cases = [(r"(?<!\d)1[3-9]\d{9}(?!\d)", "a13800138000b"),
                 (r"(?P<name>[A-Z]+)\s+\1", "Ab Ab other"), (r"x|secret", "X secret SECRET"),
                 (r"[\u4e00-\u9fff]{2,4}", "测试文字 test")]
        for pattern, text in cases:
            self.assertEqual(self.service.spans(pattern, text), [[m.start(), m.end()] for m in re.finditer(pattern, text, re.I) if m.start()<m.end()])

    def test_catastrophic_backtracking_stops_and_service_recovers(self):
        self.service.spans("ok", "ok")
        start = time.monotonic()
        with self.assertRaises(RuleBudgetError):
            self.service.spans(r"(a+)+$", "a"*40+"!", timeout=.1)
        self.assertLess(time.monotonic()-start, 3)
        self.assertEqual(self.service.spans("ok", "ok"), [[0,2]])

    def test_oversize_text_fails_closed(self):
        with self.assertRaises(RuleBudgetError):
            self.service.spans("x", "x"*1000001)
