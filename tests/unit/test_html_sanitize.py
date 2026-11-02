"""P1-3 XSS 防御：白名单 HTML 消毒器单元测试。"""
import unittest

from privacyguard.utils.html_sanitize import sanitize_preview_html


class TestPreviewHtmlSanitizer(unittest.TestCase):
    """覆盖 Word 预览 HTML 消毒的关键攻击向量。"""

    def test_script_tag_removed(self):
        out = sanitize_preview_html('<p>正文</p><script>alert(1)</script>')
        self.assertNotIn("<script", out.lower())
        self.assertIn("正文", out)

    def test_on_event_handlers_removed(self):
        out = sanitize_preview_html('<p onclick="evil()">hi</p><img src="x.png" onerror="evil()">')
        low = out.lower()
        self.assertNotIn("onclick", low)
        self.assertNotIn("onerror", low)
        # 合法属性保留
        self.assertIn("x.png", out)

    def test_javascript_scheme_removed(self):
        out = sanitize_preview_html('<a href="javascript:evil()">click</a>')
        self.assertNotIn("javascript:", out.lower())

    def test_data_text_html_blocked_but_data_image_allowed(self):
        out = sanitize_preview_html('<a href="data:text/html,<script>alert(1)</script>">x</a>'
                                    '<img src="data:image/png;base64,AAAA">')
        low = out.lower()
        self.assertNotIn("data:text/html", low)
        self.assertIn("data:image/png", out)  # 图片 data URI 必须保留（broken-image 回退）

    def test_file_scheme_blocked(self):
        out = sanitize_preview_html('<a href="file:///etc/passwd">x</a>')
        self.assertNotIn("file://", out.lower())

    def test_dangerous_tags_removed_safe_tags_kept(self):
        out = sanitize_preview_html('<iframe src="x"></iframe><object></object>'
                                    '<p>段落</p><table><tr><td>单元格</td></tr></table>')
        low = out.lower()
        self.assertNotIn("<iframe", low)
        self.assertNotIn("<object", low)
        self.assertIn("<p>", out)
        self.assertIn("<td>", out)

    def test_style_expression_scrubbed(self):
        out = sanitize_preview_html('<p style="width:expression(alert(1))">x</p>')
        self.assertNotIn("expression(", out.lower())
        # 安全 style 保留
        out2 = sanitize_preview_html('<p style="color:red">x</p>')
        self.assertIn("color:red", out2.replace(" ", ""))

    def test_data_key_attributes_preserved(self):
        """下游 keyed-patching 用的 data-* 锚点必须保留。"""
        out = sanitize_preview_html('<p data-key="p_0" data-original-text="abc">x</p>')
        self.assertIn("data-key", out)
        self.assertIn("data-original-text", out)

    def test_empty_and_invalid_input_safe(self):
        self.assertEqual(sanitize_preview_html(""), "")
        self.assertEqual(sanitize_preview_html(None), "")
        # 非法/畸形输入不应抛异常
        sanitize_preview_html("<<<>><p>未闭合")
        sanitize_preview_html("<p>正常")

    def test_comments_removed(self):
        out = sanitize_preview_html('<p>x</p><!-- 条件注释 IE -->')
        self.assertNotIn("<!--", out)

    # --- 安全审计 v40.1.4（A1）：离线策略——外链与远程信标 ---

    def test_external_http_href_stripped_text_kept(self):
        """文档内嵌外链点击不得产生外联：href 剥离，链接文字保留。"""
        out = sanitize_preview_html('<a href="https://evil.example/x?a=1">点我</a>')
        low = out.lower()
        self.assertNotIn("href", low)
        self.assertNotIn("evil.example", low)
        self.assertIn("点我", out)

    def test_ftp_and_mailto_schemes_blocked(self):
        for url in ("ftp://evil.example/f", "mailto:a@evil.example", "//evil.example/x"):
            out = sanitize_preview_html(f'<a href="{url}">x</a>')
            self.assertNotIn("href", out.lower(), url)

    def test_relative_and_fragment_urls_kept(self):
        """相对路径与片段锚点允许（本地预览资源 + 文内跳转）。"""
        out = sanitize_preview_html('<a href="#sec1">跳</a><img src="images/a.png">')
        self.assertIn('#sec1', out)
        self.assertIn('images/a.png', out)

    def test_css_remote_url_beacon_scrubbed(self):
        out = sanitize_preview_html('<p style="background-image:url(http://evil.example/x.gif)">x</p>')
        self.assertNotIn("url(", out.lower())
        self.assertNotIn("evil.example", out.lower())

    def test_css_data_image_url_kept(self):
        out = sanitize_preview_html('<p style="background-image:url(data:image/png;base64,AAAA)">x</p>')
        self.assertIn("data:image/png", out)

    def test_css_relative_url_kept(self):
        out = sanitize_preview_html('<p style="background-image:url(images/b.png)">x</p>')
        self.assertIn("images/b.png", out)


if __name__ == "__main__":
    unittest.main()
