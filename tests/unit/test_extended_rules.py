"""cp70 回归测试：扩展预设脱敏规则（统一社会信用代码/车牌/固话/护照/港澳台/VIN/IP）

覆盖：
1. 统一社会信用代码 mod-31 校验（真实有效码通过，乱码/错校验位拒绝）
2. 车架号 VIN 校验（第 9 位校验位）
3. verify_hit_by_pattern 命中后校验分发（uscc/vin 校验失败丢弃，其余放行）
4. 各正则命中真实样本、拒绝明显噪声
"""
import re
import unittest

from privacyguard.ocr.text_pdf import (
    _is_valid_uscc,
    _is_valid_vin,
    verify_hit_by_pattern,
    apply_box_adjust_to_hit,
)
from main import DEFAULT_RULES


class TestApplyBoxAdjustToHit(unittest.TestCase):
    """cp71: 文本层命中框 box_adjust 中心缩放（修复死配置）。"""

    def test_zero_ratio_unchanged(self):
        self.assertEqual(apply_box_adjust_to_hit(10, 20, 100, 40, 0.0), (10, 20, 100, 40))

    def test_positive_ratio_shrinks_centered(self):
        # 正值收缩：宽变小、x 向内移，中心不变
        x, y, w, h = apply_box_adjust_to_hit(10, 20, 100, 40, 0.2)
        self.assertLess(w, 100)
        self.assertGreater(x, 10)
        # 中心 x 保持：原 10+50=60，新 x+w/2 仍≈ 60
        self.assertAlmostEqual(x + w / 2, 60, places=6)

    def test_negative_ratio_expands(self):
        # 负值扩大：宽变大、x 向外移
        x, y, w, h = apply_box_adjust_to_hit(10, 20, 100, 40, -0.2)
        self.assertGreater(w, 100)
        self.assertLess(x, 10)
        self.assertAlmostEqual(x + w / 2, 60, places=6)

    def test_y_shrink_smaller_than_x(self):
        # y 方向收缩系数 0.6×，收缩量小于 x
        _, _, w, h = apply_box_adjust_to_hit(0, 0, 100, 100, 0.2)
        w_shrink = 100 - w
        h_shrink = 100 - h
        self.assertGreater(w_shrink, h_shrink)

    def test_floor_width_height(self):
        # 极端收缩不低于 1.0pt 保底
        _, _, w, h = apply_box_adjust_to_hit(0, 0, 2, 2, 0.5)
        self.assertGreaterEqual(w, 1.0)
        self.assertGreaterEqual(h, 1.0)


class TestUSCCValidation(unittest.TestCase):
    def test_valid_uscc(self):
        # 真实结构有效码（企业样例，校验位正确）
        self.assertTrue(_is_valid_uscc("91350100M000100Y43"))
        self.assertTrue(_is_valid_uscc("92310000MA1FL8AC4Y"))

    def test_wrong_check_digit(self):
        # 末位校验位篡改 → 拒绝
        self.assertFalse(_is_valid_uscc("91350100M000100Y44"))

    def test_illegal_charset(self):
        # 含非法字符 I/O/Z/S/V → 拒绝
        self.assertFalse(_is_valid_uscc("91350100M000100YI3"))

    def test_wrong_length(self):
        self.assertFalse(_is_valid_uscc("91350100M000100Y4"))
        self.assertFalse(_is_valid_uscc(""))
        self.assertFalse(_is_valid_uscc(None))


class TestVINValidation(unittest.TestCase):
    def test_valid_vin(self):
        # 标准示例 VIN（第 9 位校验位正确）
        self.assertTrue(_is_valid_vin("1HGBH41JXMN109186"))
        self.assertTrue(_is_valid_vin("11111111111111111"))  # 全1，校验位1

    def test_wrong_check_digit(self):
        self.assertFalse(_is_valid_vin("1HGBH41J0MN109186"))  # 第9位篡改

    def test_illegal_charset(self):
        self.assertFalse(_is_valid_vin("1HGBH41JXMN1091I6"))  # 含 I
        self.assertFalse(_is_valid_vin("1HGBH41JXMN1091O6"))  # 含 O

    def test_wrong_length(self):
        self.assertFalse(_is_valid_vin("1HGBH41JXMN10918"))
        self.assertFalse(_is_valid_vin(""))


class TestVerifyHitDispatch(unittest.TestCase):
    """verify_hit_by_pattern：按 pattern 特征分发校验，无关 pattern 放行。"""

    USCC_P = DEFAULT_RULES["统一社会信用代码"]
    VIN_P = DEFAULT_RULES["车架号"]
    PLATE_P = DEFAULT_RULES["车牌号"]

    def test_uscc_valid_kept(self):
        self.assertTrue(verify_hit_by_pattern(self.USCC_P, "91350100M000100Y43"))

    def test_uscc_invalid_dropped(self):
        self.assertFalse(verify_hit_by_pattern(self.USCC_P, "91350100M000100Y44"))

    def test_vin_valid_kept(self):
        self.assertTrue(verify_hit_by_pattern(self.VIN_P, "1HGBH41JXMN109186"))

    def test_vin_invalid_dropped(self):
        self.assertFalse(verify_hit_by_pattern(self.VIN_P, "1HGBH41J0MN109186"))

    def test_non_check_pattern_passthrough(self):
        # 车牌号无校验位 → 恒放行
        self.assertTrue(verify_hit_by_pattern(self.PLATE_P, "京A12345"))
        # 银行卡等旧 pattern 不归本函数管，也应放行（Luhn 在别处）
        self.assertTrue(verify_hit_by_pattern(DEFAULT_RULES["银行卡号"], "6222021234567890"))


class TestNewPatternMatching(unittest.TestCase):
    """新正则命中真实样本、拒绝明显噪声（正则层，不含校验）。"""

    def _search(self, name, text):
        return re.findall(DEFAULT_RULES[name], text)

    def test_plate_matches(self):
        self.assertTrue(re.search(DEFAULT_RULES["车牌号"], "肇事车辆京A12345当场"))
        self.assertTrue(re.search(DEFAULT_RULES["车牌号"], "新能源粤B12345D登记"))

    def test_landline_matches(self):
        self.assertTrue(re.search(DEFAULT_RULES["固定电话"], "电话010-88886666转"))
        self.assertTrue(re.search(DEFAULT_RULES["固定电话"], "0571-12345678"))

    def test_landline_not_match_mobile(self):
        # 手机号 13800138000 不以 0 开头，不应被固话正则整体误吞
        m = re.search(DEFAULT_RULES["固定电话"], "13800138000")
        self.assertIsNone(m)

    def test_passport_matches(self):
        self.assertTrue(re.search(DEFAULT_RULES["护照号"], "护照E12345678号"))

    def test_ip_matches(self):
        self.assertTrue(re.search(DEFAULT_RULES["IP地址"], "登录IP 192.168.1.1 记录"))

    def test_ip_reject_out_of_range(self):
        # 999.x 不是合法 IP 段
        self.assertIsNone(re.search(DEFAULT_RULES["IP地址"], "999.999.999.999"))

    def test_uscc_regex_matches_structure(self):
        # 正则层能命中结构（校验在 verify 层）
        self.assertTrue(re.search(DEFAULT_RULES["统一社会信用代码"], "统一社会信用代码91350100M000100Y43"))


class TestDefaultRulesIntegrity(unittest.TestCase):
    def test_new_rules_present(self):
        for name in ["统一社会信用代码", "车牌号", "固定电话", "护照号",
                     "港澳台通行证", "车架号", "IP地址"]:
            self.assertIn(name, DEFAULT_RULES, f"{name} 应在 DEFAULT_RULES")

    def test_all_regex_compile(self):
        for name, pat in DEFAULT_RULES.items():
            if pat.startswith("__"):
                continue  # 图像检测哨兵
            try:
                re.compile(pat)
            except re.error as e:
                self.fail(f"规则 {name} 正则无法编译: {e}")


if __name__ == "__main__":
    unittest.main()
