import unittest
from types import MethodType, SimpleNamespace

from main import (
    MainWindow,
    WebViewBridge,
    normalize_word_replace_rules,
    build_word_rule_matches,
    apply_word_rules_to_text,
    validate_word_replace_rules,
    build_batch_result_rows,
    build_batch_filter_labels,
    build_batch_rule_summary_lines,
    filter_batch_result_rows,
    format_signed_percent,
    merge_word_matches_with_priority,
    resolve_word_ocr_replacements,
    split_targeted_search_terms,
    rects_overlap_ratio,
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
    resolve_enabled_highlight_sources,
    build_highlight_source_filter_script,
    HIGHLIGHT_FILTER_SOURCES,
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

    def test_exact_match_is_case_insensitive(self):
        """W3: exact 规则应忽略大小写，避免英文敏感词因大小写不同而漏脱。"""
        text = "Email: Admin@Example.COM"
        rules = [{"enabled": True, "mode": "exact", "find": "admin@example.com", "replace": "[邮箱]"}]
        matches = build_word_rule_matches(text, rules, "[默认]")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "Admin@Example.COM")

    def test_regex_match_is_case_insensitive(self):
        """W3: regex 规则应忽略大小写，与 WordWorker._find_matches 保持一致。"""
        text = "SECRET secret Secret"
        rules = [{"enabled": True, "mode": "regex", "find": r"secret", "replace": "[密]"}]
        matches = build_word_rule_matches(text, rules, "[默认]")
        self.assertEqual(len(matches), 3)

    def test_validate_reports_invalid_regex(self):
        """W5: 启用的非法 regex 规则应被报告，附带行号与原文。"""
        rules = [
            {"enabled": True, "mode": "regex", "find": r"[unclosed", "replace": "X"},
            {"enabled": True, "mode": "exact", "find": "[literal", "replace": "Y"},
        ]
        errors = validate_word_replace_rules(rules)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["index"], 0)
        self.assertEqual(errors[0]["find"], r"[unclosed")

    def test_validate_skips_disabled_and_valid_rules(self):
        """W5: 禁用规则、合法正则与 exact 规则不应报错。"""
        rules = [
            {"enabled": False, "mode": "regex", "find": r"[bad", "replace": "X"},
            {"enabled": True, "mode": "regex", "find": r"1[3-9]\d{9}", "replace": "Y"},
            {"enabled": True, "mode": "exact", "find": "(literal)", "replace": "Z"},
        ]
        self.assertEqual(validate_word_replace_rules(rules), [])

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


class TestHighlightSourceFilter(unittest.TestCase):
    """预览高亮按来源（rule/manual/ocr）筛选的纯逻辑。"""

    def test_resolve_none_means_all_enabled(self):
        """None 视为全部启用（默认不筛选）。"""
        self.assertEqual(resolve_enabled_highlight_sources(None),
                         list(HIGHLIGHT_FILTER_SOURCES))

    def test_resolve_normalizes_order_and_dedup(self):
        """输出顺序固定为 rule/manual/ocr，并去重。"""
        self.assertEqual(
            resolve_enabled_highlight_sources(["ocr", "rule", "ocr"]),
            ["rule", "ocr"],
        )

    def test_resolve_ignores_unknown_sources(self):
        """非法/未知来源被忽略。"""
        self.assertEqual(
            resolve_enabled_highlight_sources(["rule", "bogus", ""]),
            ["rule"],
        )

    def test_resolve_accepts_single_string(self):
        """传入单个字符串也能正确归一化。"""
        self.assertEqual(resolve_enabled_highlight_sources("manual"), ["manual"])

    def test_resolve_empty_means_none_enabled(self):
        """空选择意味着全部筛掉（与 None 区分）。"""
        self.assertEqual(resolve_enabled_highlight_sources([]), [])

    def test_filter_script_marks_disabled_sources(self):
        """未启用的来源应出现在 enabled 辇外，脚本包含目标属性名。"""
        script = build_highlight_source_filter_script(["rule"])
        self.assertIn('"rule"', script)
        self.assertNotIn('"ocr"', script)
        self.assertIn("data-hl-filtered", script)
        self.assertIn("mark[data-source]", script)

    def test_filter_script_all_enabled_contains_all(self):
        """全部启用时三个来源都在脚本中。"""
        script = build_highlight_source_filter_script(None)
        for source in HIGHLIGHT_FILTER_SOURCES:
            self.assertIn(f'"{source}"', script)


class TestResolveWordOcrReplacements(unittest.TestCase):
    """cp63: 关键词行内替换（find|replace）优先于统一替换文本。"""

    def _keyword_rules(self):
        return [
            {"enabled": True, "find": "原告", "replace": "上诉人"},
            {"enabled": True, "find": "李四", "replace": ""},
            {"enabled": False, "find": "王五", "replace": "王某"},
        ]

    def test_inline_replace_overrides_default(self):
        """带 | 的关键词行：命中后使用该行替换文本。"""
        ocr = [{"start": 0, "end": 2, "text": "原告", "replacement": "[已脱敏]"}]
        resolved = resolve_word_ocr_replacements(ocr, self._keyword_rules(), "[已脱敏]")
        self.assertEqual(resolved[0]["replacement"], "上诉人")

    def test_no_pipe_falls_back_to_unified_text(self):
        """不带 | 的关键词行：使用当前统一替换文本（实时值，非扫描时烘焙值）。"""
        ocr = [{"start": 0, "end": 2, "text": "李四", "replacement": "[扫描时旧值]"}]
        resolved = resolve_word_ocr_replacements(ocr, self._keyword_rules(), "[新统一]")
        self.assertEqual(resolved[0]["replacement"], "[新统一]")

    def test_disabled_rule_not_applied(self):
        """未启用的关键词规则不参与行内替换。"""
        ocr = [{"start": 0, "end": 2, "text": "王五", "replacement": "[已脱敏]"}]
        resolved = resolve_word_ocr_replacements(ocr, self._keyword_rules(), "[已脱敏]")
        self.assertEqual(resolved[0]["replacement"], "[已脱敏]")

    def test_case_insensitive_english_keyword(self):
        """英文关键词 IGNORECASE 命中时也能匹配行内替换。"""
        rules = [{"enabled": True, "find": "Acme", "replace": "某公司"}]
        ocr = [{"start": 0, "end": 4, "text": "ACME", "replacement": "[已脱敏]"}]
        resolved = resolve_word_ocr_replacements(ocr, rules, "[已脱敏]")
        self.assertEqual(resolved[0]["replacement"], "某公司")

    def test_original_matches_not_mutated(self):
        """原始扫描命中列表不被原地修改。"""
        ocr = [{"start": 0, "end": 2, "text": "原告", "replacement": "[已脱敏]"}]
        resolve_word_ocr_replacements(ocr, self._keyword_rules(), "[已脱敏]")
        self.assertEqual(ocr[0]["replacement"], "[已脱敏]")

    def test_empty_inputs(self):
        """空命中/空规则的防御行为。"""
        self.assertEqual(resolve_word_ocr_replacements([], self._keyword_rules(), "[x]"), [])
        ocr = [{"start": 0, "end": 2, "text": "原告", "replacement": "[已脱敏]"}]
        resolved = resolve_word_ocr_replacements(ocr, None, "[新统一]")
        self.assertEqual(resolved[0]["replacement"], "[新统一]")

    def test_word_rule_has_highest_priority_after_merge(self):
        """同一段文本同时命中 Word 替换规则与关键词时，rule 源优先占位。"""
        text = "原告张三"
        word_rules = [{"enabled": True, "mode": "exact", "find": "原告", "replace": "[当事人]"}]
        ocr = resolve_word_ocr_replacements(
            [{"start": 0, "end": 2, "text": "原告", "replacement": "[已脱敏]"}],
            self._keyword_rules(), "[已脱敏]"
        )
        merged = merge_word_matches_with_priority(text, word_rules, "[已脱敏]", ocr_matches=ocr)
        first = [m for m in merged if m["start"] == 0][0]
        self.assertEqual(first["source"], "rule")
        self.assertEqual(first["replacement"], "[当事人]")

    def test_inline_replace_survives_merge_without_word_rule(self):
        """无 Word 替换规则时，行内替换文本随 ocr 源进入合并结果。"""
        text = "原告张三"
        ocr = resolve_word_ocr_replacements(
            [{"start": 0, "end": 2, "text": "原告", "replacement": "[已脱敏]"}],
            self._keyword_rules(), "[已脱敏]"
        )
        merged = merge_word_matches_with_priority(text, [], "[已脱敏]", ocr_matches=ocr)
        first = [m for m in merged if m["start"] == 0][0]
        self.assertEqual(first["source"], "ocr")
        self.assertEqual(first["replacement"], "上诉人")


class TestTargetedMaskHelpers(unittest.TestCase):
    """cp65: 手动框选全文遮罩的纯函数辅助。"""

    def test_split_terms_basic(self):
        """按空白/换行拆分、去重、去空。"""
        self.assertEqual(
            split_targeted_search_terms("原告 被告\n原告  张三\n\n"),
            ["原告", "被告", "张三"],
        )

    def test_split_terms_empty_and_invalid(self):
        """空输入/非字符串返回空列表。"""
        self.assertEqual(split_targeted_search_terms(""), [])
        self.assertEqual(split_targeted_search_terms("   \n  "), [])
        self.assertEqual(split_targeted_search_terms(None), [])

    def test_overlap_ratio_identical(self):
        """完全重叠 → 1.0。"""
        from PyQt6.QtCore import QRectF
        r = QRectF(10, 10, 100, 20)
        self.assertAlmostEqual(rects_overlap_ratio(r, QRectF(r)), 1.0)

    def test_overlap_ratio_disjoint(self):
        """不相交 → 0.0。"""
        from PyQt6.QtCore import QRectF
        self.assertEqual(rects_overlap_ratio(QRectF(0, 0, 10, 10), QRectF(50, 50, 10, 10)), 0.0)

    def test_overlap_ratio_partial_uses_smaller_area(self):
        """部分重叠按较小矩形面积归一化。"""
        from PyQt6.QtCore import QRectF
        big = QRectF(0, 0, 100, 100)
        small = QRectF(90, 0, 20, 10)  # 与 big 重叠 10x10=100，small 面积 200
        self.assertAlmostEqual(rects_overlap_ratio(big, small), 0.5)

    def test_overlap_ratio_none_defensive(self):
        """None 入参防御返回 0.0。"""
        from PyQt6.QtCore import QRectF
        self.assertEqual(rects_overlap_ratio(None, QRectF(0, 0, 1, 1)), 0.0)
        self.assertEqual(rects_overlap_ratio(QRectF(0, 0, 1, 1), None), 0.0)


if __name__ == "__main__":
    unittest.main()
