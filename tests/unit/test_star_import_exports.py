# -*- coding: utf-8 -*-
"""v40.1.4：star-import 导出一致性守卫。

背景：v40.1.4 曾把 build_batch_summary_text 加入 helpers_word_rules 却漏更
__all__（列表格式与追加脚本的正则不匹配），导致 main.py 的 star import 拿不到
该函数、启动即 NameError——单元测试直连导入无法暴露此类漂移。本测试兑付两层：
1. 各 helpers 模块 __all__ 内的名字真实存在（防拼写漂移）；
2. main.py 运行时依赖的关键迁移函数在 star-import 命名空间可见（防漏导出）。
"""
import importlib
import unittest

_HELPER_MODULES = (
    "privacyguard.utils.helpers_pdf",
    "privacyguard.utils.helpers_word_rules",
    "privacyguard.utils.helpers_word_doc",
    "privacyguard.utils.helpers_word_preview",
    "privacyguard.utils.helpers_ui",
    "privacyguard.utils.helpers_bookmark",
)

# main.py 经 star import 使用、曾发生/易发生导出漂移的关键名字
_STAR_NAMES = [
    "deduplicate_rects", "is_overlapping", "rect_contains", "is_half_overlapping",
    "build_batch_summary_text",
]


class TestStarImportExports(unittest.TestCase):
    def test_all_names_exist_in_modules(self):
        for mod_name in _HELPER_MODULES:
            mod = importlib.import_module(mod_name)
            all_names = getattr(mod, "__all__", [])
            for name in all_names:
                self.assertTrue(hasattr(mod, name),
                                f"{mod_name}.__all__ 声明了不存在的名字: {name}")

    def test_runtime_names_visible_via_star_import(self):
        ns = {}
        for mod_name in _HELPER_MODULES:
            exec(f"from {mod_name} import *", ns)
        for name in _STAR_NAMES:
            self.assertIn(name, ns, f"star import 命名空间缺少 {name}（__all__ 漏导出？）")


if __name__ == "__main__":
    unittest.main()
