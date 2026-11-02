# -*- coding: utf-8 -*-
"""cp_person_name 回归：诉讼文书"称谓人名"识别引擎。

覆盖：
- 用户提供的全部称谓词命中（含 4 字称谓"犯罪嫌疑人"）
- 冒号变体（半/全角 + 空白容忍）
- 最长优先（"被告人"不被"被告"截断；"被申请人"不被"申请人"截断）
- 嵌套称谓（"被告人的辩护人王五"）
- 误检否决（"被告人当庭供述"/"原告代理人到庭"/"犯罪嫌疑人的供述"）
- 人名长度 2/3/4（复姓"欧阳建国"）
- 尾部裁边（"张三到庭"→"张三"；"张某某的供述"→"张某某"）
- 偏移正确性（refine 后 span 换算）
- 自定义称谓词表
"""
import unittest

from privacyguard.ocr.person_name import (
    DEFAULT_TITLES,
    build_person_name_pattern,
    find_title_person_names,
    extract_person_name_from_run,
    validate_person_name,
)


def names_of(text, titles=None):
    """便捷：返回文本中识别出的人名列表（按出现顺序）。"""
    return [n for n, _s, _e in find_title_person_names(text, titles)]


class TestBasicTitleHits(unittest.TestCase):
    """用户提供的称谓词逐一命中。"""

    def test_user_provided_titles(self):
        titles = [
            "被告人", "犯罪嫌疑人", "原告", "辩护人", "证人", "被害人", "被告",
            "上诉人", "被上诉人", "申请人", "被申请人", "异议人", "答辩人", "被答辩人",
        ]
        for t in titles:
            with self.subTest(title=t):
                self.assertEqual(names_of(f"{t}张三，男，1990年出生。"), ["张三"])

    def test_extended_law_titles(self):
        for t in ["公诉人", "自诉人", "原审被告人", "再审申请人", "委托代理人",
                  "法定代理人", "第三人", "鉴定人", "保证人"]:
            with self.subTest(title=t):
                self.assertEqual(names_of(f"{t}李四到案。"), ["李四"])


class TestColonAndSpaceVariants(unittest.TestCase):
    """称谓后的冒号（半/全角）与空白容忍。"""

    def test_halfwidth_colon(self):
        self.assertEqual(names_of("被告人:张三，男。"), ["张三"])

    def test_fullwidth_colon(self):
        self.assertEqual(names_of("被告人：张三，男。"), ["张三"])

    def test_colon_with_spaces(self):
        self.assertEqual(names_of("被告人 : 张三"), ["张三"])

    def test_plain_space_separator(self):
        self.assertEqual(names_of("被告人 张三，男。"), ["张三"])

    def test_fullwidth_space_separator(self):
        # 全角空格 \u3000 在 re.UNICODE 下属于 \s
        self.assertEqual(names_of("被告人\u3000张三，男。"), ["张三"])


class TestLongestMatchPriority(unittest.TestCase):
    """正则交替最长优先：短称谓不得截断长称谓。"""

    def test_beigaoren_not_truncated(self):
        # "被告"不得吃掉"被告人"的前缀（否则人名会错位成"人张"）
        self.assertEqual(names_of("被告人张三"), ["张三"])

    def test_beishenqingren_prefix(self):
        # "被申请人"整体匹配（"申请人"是其后缀）
        self.assertEqual(names_of("被申请人李四，男。"), ["李四"])

    def test_fushiminnisu_yuangao_ren(self):
        # 最长称谓"附带民事诉讼原告人"
        self.assertEqual(names_of("附带民事诉讼原告人王芳，女。"), ["王芳"])


class TestNestedTitles(unittest.TestCase):
    """嵌套称谓："被告人的辩护人王五"应命中"王五"而非"人的辩护"。"""

    def test_de_plus_title(self):
        self.assertEqual(names_of("被告人的辩护人王五，某律师事务所律师。"), ["王五"])

    def test_plain_beiagoren_de(self):
        # "被告的辩护人"（无"人"字）：lead="被告"，候选首字"的"修剪后否决，
        # 后续"辩护人王五"由独立锚点命中
        self.assertEqual(names_of("被告的辩护人王五到庭。"), ["王五"])


class TestFalsePositiveRejection(unittest.TestCase):
    """误检否决：称谓后不是人名的场景。"""

    def test_dangting_gongshu(self):
        # "被告人当庭供述…"：贪婪吃"当庭供述"→剪"供述"→"当庭"→再剪→<2 否决
        self.assertEqual(names_of("被告人当庭供述，自愿认罪。"), [])

    def test_yuangao_dailiren_daoting(self):
        # "原告代理人到庭"：lead 最长优先匹配"原告代理人"？表中有"代理人"
        # （lead 交替从"原"字位置尝试：无"原告代理人"条目则匹配"原告"），
        # 候选"代理人到"→剪"到"→"代理人"∈称谓→否决
        self.assertEqual(names_of("原告代理人到庭参加诉讼。"), [])

    def test_fanzui_xianyiren_de(self):
        self.assertEqual(names_of("犯罪嫌疑人的供述与辩解。"), [])

    def test_chengwei_zhijie_weici(self):
        self.assertEqual(names_of("被告人及其辩护人均到庭。"), [])

    def test_not_name_words_rejected(self):
        # v2 否决表：庭审高频副词不得当人名（连接词截断产出"当庭"必须否决）
        self.assertEqual(names_of("被告人当庭翻供。"), [])
        self.assertEqual(names_of("犯罪嫌疑人如实供述。"), [])


class TestNameLengths(unittest.TestCase):
    """人名长度 2-4 字。"""

    def test_two_char_name(self):
        self.assertEqual(names_of("被告人李四，男。"), ["李四"])

    def test_three_char_name(self):
        self.assertEqual(names_of("被告人王小明，男。"), ["王小明"])

    def test_four_char_compound_surname(self):
        self.assertEqual(names_of("被告人欧阳建国，男。"), ["欧阳建国"])


class TestTailTrimming(unittest.TestCase):
    """尾部裁边：贪婪 4 字命中的尾巴修剪。"""

    def test_daoting_trim(self):
        # 贪婪吃"张三到庭"→剪"到庭"→"张三"
        self.assertEqual(names_of("被告人张三到庭。"), ["张三"])

    def test_de_gongshu_trim(self):
        # 贪婪吃"张某某的"→剪"的"→"张某某"
        self.assertEqual(names_of("被告人张某某的供述。"), ["张某某"])

    def test_nu_trim(self):
        # 贪婪吃"李四梅女"→剪"女"→"李四梅"
        self.assertEqual(names_of("被害人李四梅女，1995年生。"), ["李四梅"])


class TestOffsets(unittest.TestCase):
    """refine 后的 span 换算（供管线精确遮罩人名子串）。"""

    def test_span_points_to_name_only(self):
        text = "被告人张三，男，1990年3月5日出生。"
        result = find_title_person_names(text)
        self.assertEqual(len(result), 1)
        name, start, end = result[0]
        self.assertEqual(name, "张三")
        self.assertEqual(text[start:end], "张三")

    def test_span_after_trim(self):
        text = "被告人张三到庭。"
        name, start, end = find_title_person_names(text)[0]
        self.assertEqual((name, text[start:end]), ("张三", "张三"))
        # 人名后紧跟"到庭"，确认裁边后 span 精确
        self.assertEqual(text[end:end + 2], "到庭")

    def test_refine_returns_cut_counts(self):
        # v2: extract_person_name_from_run 从连续汉字串提取（"张三到庭"连接词截断）
        self.assertEqual(extract_person_name_from_run("张三到庭"), "张三")


class TestMultipleAndRepeated(unittest.TestCase):
    """多人与同名多次发现。"""

    def test_multiple_persons(self):
        text = "被告人张三、被害人李四及证人王五到庭。"
        self.assertEqual(names_of(text), ["张三", "李四", "王五"])

    def test_same_name_multiple_anchors(self):
        # 同名由不同锚点发现，多次返回；全页去重由管线 seen 处理
        text = "被告人张三到庭，被害人张三陈述。"
        self.assertEqual(names_of(text), ["张三", "张三"])

    def test_discovery_semantics_example(self):
        # 用户决策"发现即全页遮"的发现源：不带称谓的第二次出现不在本函数职责
        text = "被告人张三，男。张三于2024年到案。"
        self.assertEqual(names_of(text), ["张三"])


class TestCustomTitles(unittest.TestCase):
    """自定义称谓词表（config redaction.person_name_titles）。"""

    def test_custom_title_hits(self):
        self.assertEqual(names_of("对方当事人赵六发言。", titles=["对方当事人"]), ["赵六"])

    def test_custom_title_replaces_defaults(self):
        # 自定义表生效时内置表不参与（覆盖语义）
        self.assertEqual(names_of("被告人张三", titles=["对方当事人"]), [])


class TestPatternBuilding(unittest.TestCase):
    """build_person_name_pattern 的结构保证。"""

    def test_pattern_has_named_groups(self):
        import re
        pat = build_person_name_pattern()
        compiled = re.compile(pat)
        # v2: 只有 lead 组（人名部分为 lookahead 断言，不消费）
        self.assertIn("lead", compiled.groupindex)

    def test_longest_first_in_alternation(self):
        # 行为验证：正则交替最长优先——"被告人张三"的 lead 应整体匹配"被告人"
        # （若"被告"先匹配，人名锚点会错位成人名"人张"）
        import re
        compiled = re.compile(build_person_name_pattern())
        m = compiled.search("被告人张三，男。")
        self.assertEqual(m.group("lead"), "被告人")

    def test_default_titles_complete(self):
        for t in ["被告人", "犯罪嫌疑人", "原告", "辩护人", "证人", "被害人",
                  "被告", "上诉人", "被上诉人", "申请人", "被申请人", "异议人",
                  "答辩人", "被答辩人"]:
            self.assertIn(t, DEFAULT_TITLES)


class TestRealCaseRegression(unittest.TestCase):
    """16 页真实卷宗实测发现的误检/漏检回归（阶段2 实测驱动）。"""

    def test_real_correct_hits(self):
        # 实测正确命中的真实样本
        self.assertIn("刘少芳", names_of("决定对犯罪嫌疑人刘少芳（性别男，出生日"))
        self.assertIn("孙志华", names_of("案由被害人孙志华于2026年3月"))

    def test_real_false_positives_fixed(self):
        # 实测误检修复：知人(被告知人)/被人民(被人民法院)/提供保证/证言
        self.assertEqual(names_of("被告知人："), [])
        self.assertEqual(names_of("因犯罪嫌疑人被人民法院决定逮捕"), [])
        self.assertEqual(names_of("保证人提供保证。"), [])
        self.assertEqual(names_of("证人证言、"), [])
        # 二轮实测（4页样本）：认罪认罚/认罪阶段（"认"非姓氏）
        self.assertEqual(names_of("犯罪嫌疑人认罪认罚的条件，向人民检察院"), [])
        self.assertEqual(names_of("根据犯罪嫌疑人认罪阶段、程度等情节"), [])

    def test_real_reverse_structure(self):
        # 实测漏检修复："陈绕奇作为保证人提供保证"（姓名+作为+称谓 反向结构）
        self.assertIn("陈绕奇", names_of("陈绕奇作为保证人提供保证。"))
        # 前文粘连场景："由刘少芳担任辩护人"
        self.assertIn("刘少芳", names_of("由刘少芳担任辩护人。"))
        # 实测二轮：关系词粘连（"…的同事陈绕奇作为保证人"→窗口"事陈绕奇"）
        names = names_of("由刘少芳的同事陈绕奇作为保证人提供保证。")
        self.assertIn("陈绕奇", names)
        self.assertNotIn("事陈绕奇", names)
        # 关系词双字粘连："同事李四作为保证人"→循环剪"同"+"事"
        names = names_of("的同事李四作为保证人。")
        self.assertIn("李四", names)
        self.assertNotIn("同事李四", names)

    def test_reverse_link_words(self):
        # 反向链接词三种变体
        self.assertIn("张三", names_of("张三作为辩护人出庭。"))
        self.assertIn("李四", names_of("李四担任保证人。"))
        self.assertIn("王五", names_of("王五系被害人。"))


class TestContractDocumentCase(unittest.TestCase):
    """v40.2.2 公司变更/章程类文书实测驱动（17 页"变更"文书）：

    标签式锚点（强制冒号防"甲方违约"误配）+ 机构名后缀识别 + 动词锚点。
    """

    def test_label_anchors_with_colon(self):
        # 实测句式："公司名称：池州市久兴置业有限公司" / "人员姓名：彭幼林"
        self.assertIn("彭幼林", names_of("人员姓名：彭幼林"))
        self.assertIn("吴良富", names_of("股东：吴良富"))
        self.assertIn("王某", names_of("甲方：王某"))
        self.assertIn("李某", names_of("法定代表人：李某"))

    def test_label_requires_colon(self):
        # 标签词在普通行文出现（无冒号）不触发
        self.assertEqual(names_of("甲方违约应承担责任。"), [])
        self.assertEqual(names_of("股东会作出决定如下。"), [])
        self.assertEqual(names_of("负责人签字确认。"), [])

    def test_org_name_by_suffix(self):
        # 机构名整名识别（后缀锚定，人名未命中时兜底）
        names = names_of("公司名称：池州市久兴置业有限公司")
        self.assertIn("池州市久兴置业有限公司", names)
        # 机构名后跟谓语（"…有限公司股东于…"）——后缀结束即止
        names = names_of("公司名称：池州市久兴置业有限公司股东于2026年")
        self.assertIn("池州市久兴置业有限公司", names)

    def test_person_name_priority_over_org(self):
        # 人名优先：2-4 字人名命中时不再做机构识别（"王小明到市中心医院"）
        names = names_of("证人王小明到市中心医院")
        self.assertIn("王小明", names)
        self.assertNotIn("王小明到市中心医院", names)

    def test_verb_anchors(self):
        # 动词锚点：章程句式"由吴良富出资，设立池州市久兴置业有限公司"
        text = "法规的规定，由吴良富出资，设立池州市久兴置业有限公司（以下简称公司）"
        names = names_of(text)
        self.assertIn("吴良富", names)
        self.assertIn("池州市久兴置业有限公司", names)

    def test_verb_anchor_no_false_positive(self):
        # "设立"后无机构结构不命中："设立规章制度"
        self.assertEqual(names_of("公司决定设立规章制度。"), [])


class TestValidatePersonName(unittest.TestCase):
    """词表验证器（阶段1）。"""

    def test_valid_names(self):
        for n in ["张三", "王小明", "欧阳建国"]:
            self.assertTrue(validate_person_name(n))

    def test_reject_title_words(self):
        self.assertFalse(validate_person_name("代理人"))
        self.assertFalse(validate_person_name("被告人"))

    def test_reject_lead_function_char(self):
        self.assertFalse(validate_person_name("的某某"))

    def test_reject_bad_length(self):
        self.assertFalse(validate_person_name("张"))
        self.assertFalse(validate_person_name("张三丰四五"))


if __name__ == "__main__":
    unittest.main()
