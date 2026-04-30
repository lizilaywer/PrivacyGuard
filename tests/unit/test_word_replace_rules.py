import unittest
from types import MethodType, SimpleNamespace

from main import (
    MainWindow,
    WebViewBridge,
    normalize_word_replace_rules,
    build_word_rule_matches,
    apply_word_rules_to_text,
    build_batch_result_rows,
    build_batch_filter_labels,
    build_batch_rule_summary_lines,
    filter_batch_result_rows,
    format_signed_percent,
    merge_word_matches_with_priority,
    build_settings_hero_tags,
    build_toolbar_mode_labels,
    build_workbench_guidance,
    resolve_workspace_density_mode,
    resolve_settings_density_mode,
    build_highlight_preview_segments,
    build_replaced_preview_segments,
    build_settings_nav_labels,
    summarize_batch_result_rows,
    build_word_panel_update_script,
    should_reload_word_panel,
    resolve_word_preview_image_suffix,
    WORD_PREVIEW_BLOCK_SELECTOR,
)


def build_word_preview_stub():
    stub = SimpleNamespace(
        word_data={
            "paragraph_0": {
                "text": "甲方 张三",
                "manual": [],
                "ocr": [],
            }
        },
        word_replace_rules=[
            {"enabled": True, "mode": "exact", "find": "张三", "replace": "[姓名]"}
        ],
        replacement_text="[已脱敏]",
        _word_base_html="<p>甲方 张三</p>",
    )
    stub._wrap_html_document = MethodType(MainWindow._wrap_html_document, stub)
    stub._build_word_text_blocks = MethodType(MainWindow._build_word_text_blocks, stub)
    stub._add_data_key_attributes = MethodType(MainWindow._add_data_key_attributes, stub)
    stub._add_data_key_regex_fallback = MethodType(MainWindow._add_data_key_regex_fallback, stub)
    stub._build_replaced_preview_fragment = MethodType(MainWindow._build_replaced_preview_fragment, stub)
    stub._inject_interactive_html = lambda html, scroll_restore='': html + scroll_restore
    stub._get_word_preview_scroll_restore_script = lambda: "<script>restoreScroll()</script>"
    return stub


class TestWordReplaceRules(unittest.TestCase):

    def test_normalize_rules_filters_invalid_rows(self):
        rules = [
            {"enabled": True, "mode": "exact", "find": "张三", "replace": "某某"},
            {"enabled": True, "mode": "regex", "find": "", "replace": "X"},
            {"enabled": True, "mode": "bad-mode", "find": "李四", "replace": ""},
            "invalid-row"
        ]
        normalized = normalize_word_replace_rules(rules, "[默认]")
        self.assertEqual(len(normalized), 2)
        self.assertEqual(normalized[0]["mode"], "exact")
        self.assertEqual(normalized[1]["mode"], "exact")
        self.assertEqual(normalized[1]["replace"], "[默认]")

    def test_exact_priority_over_regex(self):
        text = "abc123"
        rules = [
            {"enabled": True, "mode": "regex", "find": r"\w+", "replace": "[REGEX]"},
            {"enabled": True, "mode": "exact", "find": "123", "replace": "[EXACT]"},
        ]
        matches = build_word_rule_matches(text, rules, "[默认]")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["mode"], "exact")
        self.assertEqual(matches[0]["replacement"], "[EXACT]")

    def test_apply_rules_to_text(self):
        text = "姓名张三，电话13812345678"
        rules = [
            {"enabled": True, "mode": "exact", "find": "张三", "replace": "某某"},
            {"enabled": True, "mode": "regex", "find": r"1[3-9]\d{9}", "replace": "[手机号]"},
        ]
        result = apply_word_rules_to_text(text, rules, "[默认]")
        self.assertEqual(result, "姓名某某，电话[手机号]")

    def test_merge_priority_rule_manual_ocr(self):
        text = "13812345678"
        rules = [{"enabled": True, "mode": "exact", "find": "13812345678", "replace": "[规则]"}]
        manual = [{"start": 0, "end": 11, "replacement": "[手动]"}]
        ocr = [{"start": 0, "end": 11, "replacement": "[OCR]"}]

        merged = merge_word_matches_with_priority(text, rules, "[默认]", manual_matches=manual, ocr_matches=ocr)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["replacement"], "[规则]")
        self.assertEqual(merged[0]["source"], "rule")

    def test_replaced_preview_segments_merge_sources(self):
        text = "张三 13812345678"
        rules = [{"enabled": True, "mode": "exact", "find": "张三", "replace": "[姓名]"}]
        manual = [{"start": 3, "end": 14, "text": "13812345678", "replacement": "[手动]"}]

        merged = merge_word_matches_with_priority(
            text,
            rules,
            "[默认]",
            manual_matches=manual,
            ocr_matches=[]
        )
        segments = build_replaced_preview_segments(text, merged, "[默认]")

        replaced_text = "".join(seg.get("value", "") for seg in segments)
        self.assertEqual(replaced_text, "[姓名] [手动]")
        sources = [seg.get("source") for seg in segments if seg.get("type") == "replacement"]
        self.assertEqual(sources, ["rule", "manual"])

    def test_highlight_preview_segments_keep_original_text(self):
        text = "张三 13812345678"
        manual = [{"start": 0, "end": 2, "text": "张三", "replacement": "[手动]"}]
        ocr = [{"start": 3, "end": 14, "text": "13812345678", "replacement": "[OCR]"}]

        merged = merge_word_matches_with_priority(
            text,
            [],
            "[默认]",
            manual_matches=manual,
            ocr_matches=ocr
        )
        segments = build_highlight_preview_segments(text, merged)

        highlighted_text = "".join(seg.get("value", "") for seg in segments)
        self.assertEqual(highlighted_text, "张三 13812345678")
        sources = [seg.get("source") for seg in segments if seg.get("type") == "highlight"]
        self.assertEqual(sources, ["manual", "ocr"])

    def test_compare_panel_reload_required_after_blank_state(self):
        self.assertTrue(
            should_reload_word_panel(
                source_changed=False,
                loaded_source_path=None,
                current_file_path="/tmp/example.docx",
                panel_ready=True,
            )
        )
        self.assertFalse(
            should_reload_word_panel(
                source_changed=False,
                loaded_source_path="/tmp/example.docx",
                current_file_path="/tmp/example.docx",
                panel_ready=True,
            )
        )

    def test_word_panel_update_script_targets_only_word_blocks(self):
        script = build_word_panel_update_script({"paragraph_0": "hello"})
        self.assertIn(WORD_PREVIEW_BLOCK_SELECTOR, script)
        self.assertNotIn("querySelectorAll('[data-key]')", script)
        self.assertIn('"paragraph_0": "hello"', script)

    def test_regex_fallback_marks_word_preview_blocks(self):
        html = "<html><body><p>甲方 张三</p></body></html>"
        text_blocks = {"paragraph_0": {"text": "甲方 张三", "escaped": "甲方 张三"}}

        result = MainWindow._add_data_key_regex_fallback(object(), html, text_blocks)

        self.assertIn('data-key="paragraph_0"', result)
        self.assertIn('data-original-text="甲方 张三"', result)
        self.assertIn('data-word-block="1"', result)

    def test_word_preview_document_build_keeps_literal_css_blocks(self):
        stub = build_word_preview_stub()

        MainWindow._build_word_preview_documents(stub)

        self.assertIn("p:empty { display: none; margin: 0; }", stub._word_tagged_html)
        self.assertIn("mark.manual-highlight:hover {", stub._word_tagged_html)
        self.assertIn("restoreScroll()", stub._word_preview_document_html)
        self.assertIn("restoreScroll()", stub._word_replaced_document_html)

    def test_word_preview_scroll_restore_script_includes_compare_sync_hooks(self):
        script = MainWindow._get_word_preview_scroll_restore_script(object())

        self.assertIn("__setWordPreviewPanelId", script)
        self.assertIn("__applyExternalWordScrollRatio", script)
        self.assertIn("report_word_preview_scroll", script)

    def test_resolve_word_preview_image_suffix_supports_common_image_types(self):
        self.assertEqual(resolve_word_preview_image_suffix("image/png"), ".png")
        self.assertEqual(resolve_word_preview_image_suffix("image/jpeg"), ".jpg")
        self.assertEqual(resolve_word_preview_image_suffix("image/svg+xml"), ".svg")

    def test_resolve_word_preview_image_suffix_falls_back_for_unknown_types(self):
        self.assertEqual(resolve_word_preview_image_suffix("image/x-emf"), ".xemf")
        self.assertEqual(resolve_word_preview_image_suffix(None), ".img")

    def test_replaced_preview_html_keeps_literal_css_blocks(self):
        stub = build_word_preview_stub()

        replaced_html = MainWindow._build_word_replaced_preview_html(stub, stub._word_base_html)

        self.assertIn("p:empty { display: none; margin: 0; }", replaced_html)
        self.assertIn("mark.replace-preview-highlight {", replaced_html)
        self.assertIn("[姓名]", replaced_html)

    def test_file_dialog_style_keeps_literal_css_blocks(self):
        style = MainWindow._get_file_dialog_style(object())

        self.assertIn("QFileDialog {", style)
        self.assertIn("QFileDialog QLabel { color: #1D1D1F; }", style)

    def test_build_batch_result_rows_prioritizes_failed_items(self):
        summary = {
            "success": [{"input": "/tmp/a.docx", "output": "/tmp/a_replaced.docx"}],
            "failed": [{"input": "/tmp/b.docx", "error": "权限不足"}],
        }

        rows = build_batch_result_rows(summary)

        self.assertEqual(rows[0]["status"], "失败")
        self.assertEqual(rows[0]["action"], "双击定位原文件")
        self.assertEqual(rows[1]["status"], "成功")
        self.assertEqual(rows[1]["detail"], "a_replaced.docx")

    def test_filter_batch_result_rows_supports_success_and_failed(self):
        rows = [
            {"status_key": "failed", "document": "b.docx"},
            {"status_key": "success", "document": "a.docx"},
            {"status_key": "success", "document": "c.docx"},
        ]

        self.assertEqual(len(filter_batch_result_rows(rows, "all")), 3)
        self.assertEqual(len(filter_batch_result_rows(rows, "success")), 2)
        self.assertEqual(len(filter_batch_result_rows(rows, "failed")), 1)

    def test_summarize_batch_result_rows_counts_success_and_failed(self):
        rows = [
            {"status_key": "failed"},
            {"status_key": "success"},
            {"status_key": "success"},
        ]

        summary = summarize_batch_result_rows(rows)

        self.assertEqual(summary, {"total": 3, "success": 2, "failed": 1})

    def test_build_batch_filter_labels_supports_counts(self):
        labels = build_batch_filter_labels({"total": 3, "success": 2, "failed": 1}, show_counts=True)

        self.assertEqual(labels["all"], "全部 3")
        self.assertEqual(labels["success"], "成功 2")
        self.assertEqual(labels["failed"], "失败 1")

    def test_build_batch_rule_summary_lines_lists_rule_hits_per_document(self):
        rules = [
            {"enabled": True, "mode": "exact", "find": "张三", "replace": "某某"},
            {"enabled": True, "mode": "exact", "find": "李四", "replace": "匿名"},
        ]
        success_items = [
            {
                "input": "/tmp/a.docx",
                "rule_counts": [
                    {"rule_index": 0, "count": 2},
                    {"rule_index": 1, "count": 1},
                ],
            },
            {
                "input": "/tmp/b.docx",
                "rule_counts": [
                    {"rule_index": 0, "count": 3},
                ],
            },
        ]

        lines = build_batch_rule_summary_lines(rules, success_items, "[默认]")

        self.assertEqual(
            lines[0],
            "1、“张三”替换为“某某”，a.docx 成功替换 2 条，b.docx 成功替换 3 条；"
        )
        self.assertEqual(
            lines[1],
            "2、“李四”替换为“匿名”，a.docx 成功替换 1 条；"
        )

    def test_build_batch_rule_summary_lines_marks_rules_without_hits(self):
        rules = [{"enabled": True, "mode": "exact", "find": "张三", "replace": "某某"}]

        lines = build_batch_rule_summary_lines(rules, [], "[默认]")

        self.assertEqual(lines, ["1、“张三”替换为“某某”，本轮未命中；"])

    def test_build_settings_nav_labels_reflects_current_state(self):
        labels = build_settings_nav_labels(2, 5, False, 10)

        self.assertEqual(labels[0], "1 通用规则 · 2项启用")
        self.assertEqual(labels[1], "2 自定义关键词 · 5条")
        self.assertEqual(labels[2], "3 扫描与微调 · 已微调")
        self.assertEqual(labels[3], "4 OCR 检测框 · +10%")

    def test_build_settings_hero_tags_reflects_common_and_advanced_state(self):
        common_tag, advanced_tag = build_settings_hero_tags(2, 5, 3, False, 10, "标准 (1.5x 推荐)")

        self.assertEqual(common_tag, "常用：规则 2 项 · 关键词 5 条 · Word 3 条")
        self.assertIn("标准 (1.5x 推荐)", advanced_tag)
        self.assertIn("OCR +10%", advanced_tag)
        self.assertIn("已微调", advanced_tag)

    def test_build_toolbar_mode_labels_distinguishes_pdf_and_word(self):
        pdf_labels = build_toolbar_mode_labels("pdf", "wide", has_results=False)
        word_labels = build_toolbar_mode_labels("word", "wide", has_results=False, enabled_word_rules=3)

        self.assertEqual(pdf_labels["scan_text"], "智能脱敏")
        self.assertEqual(pdf_labels["save_text"], "导出 PDF")
        self.assertEqual(word_labels["scan_text"], "智能替换")
        self.assertEqual(word_labels["save_text"], "导出 Word")
        self.assertEqual(word_labels["word_rules_text"], "替换规则 3")

    def test_build_toolbar_mode_labels_reflects_existing_results(self):
        pdf_labels = build_toolbar_mode_labels("pdf", "wide", has_results=True)
        word_labels = build_toolbar_mode_labels("word", "compact", has_results=True)

        self.assertEqual(pdf_labels["scan_text"], "重新脱敏")
        self.assertEqual(word_labels["scan_text"], "重替")

    def test_resolve_workspace_density_mode_accounts_for_windows_scale(self):
        self.assertEqual(resolve_workspace_density_mode("pdf", 1500, 900, 1.0), "wide")
        self.assertEqual(resolve_workspace_density_mode("pdf", 1500, 900, 1.5), "compact")
        self.assertEqual(resolve_workspace_density_mode("pdf", 1550, 1000, 1.5), "wide")

    def test_resolve_settings_density_mode_accounts_for_scale_and_height(self):
        self.assertEqual(resolve_settings_density_mode(1700, 900, 1.0), "wide")
        self.assertEqual(resolve_settings_density_mode(1700, 900, 1.5), "roomy")
        self.assertEqual(resolve_settings_density_mode(1500, 1000, 1.5), "roomy")
        self.assertEqual(resolve_settings_density_mode(1280, 780, 1.5), "narrow")

    def test_format_signed_percent_handles_zero_and_positive(self):
        self.assertEqual(format_signed_percent(0), "0%")
        self.assertEqual(format_signed_percent(12), "+12%")

    def test_build_workbench_guidance_reflects_mode_specific_next_steps(self):
        idle = build_workbench_guidance("idle")
        pdf = build_workbench_guidance("pdf", has_results=False)
        word = build_workbench_guidance("word", has_results=True, compare_mode=False)

        self.assertIn("系统会自动分流", idle[0])
        self.assertIn("先点智能脱敏", pdf[0])
        self.assertIn("复核替换结果", word[0])
        self.assertIn("可打开对比预览", word[2])

    def test_build_workbench_guidance_handles_batch_stages(self):
        running = build_workbench_guidance("batch", batch_stage="running")
        finished = build_workbench_guidance("batch", batch_stage="finished")

        self.assertIn("正在批量替换文档", running[0])
        self.assertIn("仅重试失败文档", finished[1])

    def test_webview_bridge_reports_scroll_ratio_to_main_window(self):
        calls = []
        main_window = SimpleNamespace(
            _sync_word_compare_scroll=lambda panel, ratio: calls.append((panel, ratio))
        )
        bridge = WebViewBridge(main_window)

        bridge.report_word_preview_scroll("original", 0.5)

        self.assertEqual(calls, [("original", 0.5)])

    def test_invalidate_word_scroll_sync_resets_runtime_state(self):
        timer_state = {"stopped": False}
        stub = SimpleNamespace(
            _word_scroll_sync_timer=SimpleNamespace(stop=lambda: timer_state.__setitem__("stopped", True)),
            _word_scroll_sync_polling=True,
            _word_scroll_sync_pending_target="replaced",
            _word_scroll_sync_pending_ratio=0.42,
            _word_scroll_sync_last_ratios={"original": 0.1, "replaced": 0.2},
            _word_scroll_sync_generation=3,
        )

        MainWindow._invalidate_word_scroll_sync(stub)

        self.assertTrue(timer_state["stopped"])
        self.assertFalse(stub._word_scroll_sync_polling)
        self.assertIsNone(stub._word_scroll_sync_pending_target)
        self.assertIsNone(stub._word_scroll_sync_pending_ratio)
        self.assertEqual(stub._word_scroll_sync_last_ratios, {"original": None, "replaced": None})
        self.assertEqual(stub._word_scroll_sync_generation, 4)


if __name__ == "__main__":
    unittest.main()
