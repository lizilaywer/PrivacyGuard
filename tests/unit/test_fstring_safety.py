"""验证 f-string 内嵌 CSS/HTML 的花括号安全性。"""
import unittest
import re


class TestFStringCSSSafety(unittest.TestCase):
    """扫描 main.py 中 f-string 内的 CSS，确保花括号已用 {{ }} 转义。"""

    def test_fstring_css_braces_properly_escaped(self):
        """f-string 内的 CSS 花括号必须用 {{ }} 转义，否则会触发 NameError。

        检测策略：在 f-string（以 f\" 或 f' 开头的字符串）中查找
        未转义的单花括号 { } 内包含 CSS 属性的模式。
        合法转义为 {{ }}，因此只检测单个 { 后紧跟 CSS 属性名的情况。
        """
        with open("main.py", "r", encoding="utf-8") as f:
            lines = f.readlines()

        violations = []
        # 匹配 f-string 行中的未转义 CSS 花括号
        # 模式: { 后紧跟 CSS 属性名（如 display、color、border 等）
        css_property_pattern = re.compile(
            r'\{[ \t]*'
            r'(?:display|color|background|border|padding|margin|font-size|font-weight|font-family|width|height|position|overflow|text-align|vertical-align|white-space|cursor|opacity|z-index|top|left|right|bottom|box-shadow|outline|list-style|line-height|gap|flex|grid|align|justify|content|visibility|transform|transition|animation|max-width|min-width|max-height|min-height|float|clear)'
            r'[ \t]*:'
        )

        in_fstring = False
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            # 简化检测：包含 f\" 或 f' 且含 CSS 关键字的行
            if 'f"' in line or "f'" in line or 'f"""' in line or "f'''" in line:
                if css_property_pattern.search(line):
                    violations.append({
                        'line': lineno,
                        'snippet': stripped[:120]
                    })

        self.assertEqual(
            len(violations), 0,
            f"发现 {len(violations)} 处 f-string 中可能未转义的 CSS 花括号: "
            f"{violations[:5]}"
        )


if __name__ == "__main__":
    unittest.main()
