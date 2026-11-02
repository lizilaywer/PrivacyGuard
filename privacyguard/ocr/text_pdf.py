"""文本型 PDF 搜索结果提取共享逻辑。"""

import re

import fitz  # cp67: 旋转页坐标变换需要 Rect/rotation_matrix

# cp118: 统一日志（替代模块内散落的 print）
import logging
logger = logging.getLogger(__name__)

# v37.7.18 cp56: 身份证号正则（用于排除 Luhn 校验误伤身份证号）
# 18 位：省级前缀(11-15,21-23,31-37,41-46,50-54,61-65) + 出生年月日 + 顺序码 + 校验码
# 15 位：省级前缀 + 出生年月日(2位年) + 顺序码
_IDCARD_PATTERN = re.compile(
    r'^(?:1[1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4]|6[1-5])\d{4}'
    r'(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]$'
    r'|(?:1[1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4]|6[1-5])\d{4}'
    r'\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}$',
    re.IGNORECASE
)


def _mask(s, head=1, tail=1):
    """安全审计 v40.1: 脱敏命中串的日志掩码（不记录原文）。

    返回 head 位 + *** + tail 位；过短则全掩。
    """
    if not isinstance(s, str) or len(s) <= head + tail:
        return "***"
    return f"{s[:head]}***{s[-tail:]}"


def _is_valid_luhn(card_number):
    """v37.7.18 cp55: Luhn 算法校验银行卡号。

    银行卡号的最后一位是校验码，满足 Luhn 算法：
    1. 从右往左，偶数位数字乘以 2，如果乘积 > 9 则减 9
    2. 所有数字求和
    3. 和能被 10 整除则有效

    v37.7.19 cp58: 空输入安全返回 False（旧版空串返回 True，是 bug）。
    Luhn 算法对空串求和为 0，0 % 10 == 0 错误地返回 True。
    虽然调用方按长度过滤不会传入空串，但函数本身应保持防御性。

    Args:
        card_number: 纯数字字符串

    Returns:
        bool: 是否满足 Luhn 校验
    """
    try:
        digits = [int(d) for d in card_number]
        # cp58: 空输入防御（空串/空 list 求和为 0 会被错误判定为有效）
        if not digits:
            return False
        check_sum = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = d * 2
                check_sum += doubled - 9 if doubled > 9 else doubled
            else:
                check_sum += d
        return check_sum % 10 == 0
    except (ValueError, TypeError):
        return False


def _looks_like_idcard(number_str):
    """v37.7.18 cp56: 判断数字串是否为身份证号格式。

    用于在 Luhn 校验前排除身份证号，避免误伤。
    身份证号用 MOD 11-2 算法，不满足 Luhn 校验。

    Args:
        number_str: 纯数字或带 X 的字符串

    Returns:
        bool: 是否匹配身份证号格式（省级前缀 + 年月日结构）
    """
    return bool(_IDCARD_PATTERN.match(number_str))


# v37.7.19 cp57: 银行卡号 pattern 识别（用于限定 Luhn 校验作用域）
# 仅当 pattern 匹配 13-19 位数字串时才需要 Luhn 校验
# cp58 关键修复：移除 ^ 锚点，支持带前缀的 pattern（如 (?<!\d)([1-9]\d{12,18})(?!\d)）
# 旧版 ^\[1-9\]\\d\{12,18\} 要求 pattern 必须以 [1-9] 开头，
# 导致 config.json 默认 pattern (?<!\d)([1-9]\d{12,18})(?!\d) 不被识别，
# Luhn 校验失效，案件编号等长数字串被误匹配为银行卡号。
# 匹配核心特征 [1-9]\d{1N，其中 N∈[2-9]（即 {12-19}），允许任意前缀/后缀
_BANK_CARD_DIGIT_PATTERN = re.compile(r'\[1-9\]\\d\{1[2-9]')


def _is_bank_card_pattern(pattern):
    r"""v37.7.19 cp57: 判断 pattern 是否为银行卡号正则。

    用于限定 Luhn 校验仅对银行卡号 pattern 生效，避免过滤用户自定义正则
    恰好匹配 13-19 位数字串的情况。

    v37.7.19 cp58 修复：移除 ^ 锚点，支持带 lookbehind/lookahead/字边界
    等前缀的 pattern。旧版要求 pattern 必须以 [1-9] 开头，导致 config.json
    默认 pattern (?<!\d)([1-9]\d{12,18})(?!\d) 不被识别，Luhn 校验失效。
    同时支持 {14,18} / {15,18} 等其他 13-19 位长度范围。

    Args:
        pattern: 正则表达式字符串

    Returns:
        bool: 是否为银行卡号 pattern
    """
    if not isinstance(pattern, str):
        return False
    # 匹配 config.json 中的银行卡号正则 (?<!\d)([1-9]\d{12,18})(?!\d)
    # 检查核心特征 [1-9]\d{1N（N∈[2-9]），允许带前缀/后缀
    return bool(_BANK_CARD_DIGIT_PATTERN.search(pattern))


# cp70: 统一社会信用代码校验（GB 32100-2015，mod 31-3 加权模式）
# 18 位：登记管理部门码(1) + 机构类别码(1) + 登记机关行政区划码(6) +
#        主体标识码/组织机构代码(9) + 校验码(1)；字符集不含 I O Z S V
_USCC_CHARSET = "0123456789ABCDEFGHJKLMNPQRTUWXY"  # 31 个字符（GB 32100）
_USCC_WEIGHTS = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)
_USCC_CHAR_INDEX = {c: i for i, c in enumerate(_USCC_CHARSET)}
_USCC_PATTERN = re.compile(r'^[0-9A-HJ-NP-RTUWXY]{2}\d{6}[0-9A-HJ-NP-RTUWXY]{10}$')


def _is_valid_uscc(code):
    """cp70: 校验统一社会信用代码（18 位，mod 31-3 校验码）。

    先做字符集/结构正则校验，再算加权和取模，比对第 18 位校验码。
    误报率极低（乱数字串几乎不可能同时满足字符集 + 校验位）。

    Args:
        code: 18 位统一社会信用代码字符串

    Returns:
        bool: 是否为合法统一社会信用代码
    """
    if not isinstance(code, str) or len(code) != 18:
        return False
    code = code.upper()
    if not _USCC_PATTERN.match(code):
        return False
    try:
        total = sum(_USCC_CHAR_INDEX[code[i]] * _USCC_WEIGHTS[i] for i in range(17))
    except KeyError:
        return False
    check = 31 - (total % 31)
    check = 0 if check == 31 else check
    return _USCC_CHARSET[check] == code[17]


# cp70: 车架号 VIN 校验（GB 16735 / ISO 3779，17 位，第 9 位为校验位）
_VIN_TRANSLIT = {
    **{str(d): d for d in range(10)},
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
    'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
    'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
}
_VIN_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)
_VIN_PATTERN = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')


def _is_valid_vin(vin):
    """cp70: 校验车架号 VIN（17 位，第 9 位校验位，加权模 11，10→X）。

    北美/国标 VIN 强制第 9 位校验；进口及国产合规车辆均满足。
    字符集不含 I O Q，加校验位后乱串几乎不可能通过，误报极低。
    """
    if not isinstance(vin, str) or len(vin) != 17:
        return False
    vin = vin.upper()
    if not _VIN_PATTERN.match(vin):
        return False
    try:
        total = sum(_VIN_TRANSLIT[vin[i]] * _VIN_WEIGHTS[i] for i in range(17))
    except KeyError:
        return False
    remainder = total % 11
    check_char = 'X' if remainder == 10 else str(remainder)
    return vin[8] == check_char


# cp70: 命中后校验分发——某些 pattern 命中后需二次校验（校验位/结构），
# 校验失败则丢弃该命中，降低误报。银行卡 Luhn 沿用旧独立分支不并入此处，
# 避免触碰已稳定的高风险逻辑。
_USCC_LEN = 18
_VIN_LEN = 17


def _pattern_needs_check(pattern):
    """cp70: 判断 pattern 是否为需命中后校验的类型，返回校验器名或 None。

    以正则特征串识别（与 _is_bank_card_pattern 同思路，不依赖规则名，
    兼容 config.json 自定义与内置默认）。
    """
    if not isinstance(pattern, str):
        return None
    # 统一社会信用代码：含 [0-9A-HJ-NP-RTUWXY] 字符集特征
    if '0-9A-HJ-NP-RTUWXY' in pattern:
        return 'uscc'
    # 车架号 VIN：含 [A-HJ-NPR-Z0-9]{17} 特征
    if 'A-HJ-NPR-Z0-9' in pattern and '17' in pattern:
        return 'vin'
    return None


def verify_hit_by_pattern(pattern, matched_text):
    """cp70: 对带校验位的 pattern 命中做二次校验。

    Args:
        pattern: 命中所用正则
        matched_text: 命中的文本

    Returns:
        bool: True=校验通过（保留），False=校验失败（应丢弃）；
              无需校验的 pattern 恒返回 True
    """
    kind = _pattern_needs_check(pattern)
    if kind == 'uscc':
        if len(matched_text) == _USCC_LEN and not _is_valid_uscc(matched_text):
            return False
    elif kind == 'vin':
        if len(matched_text) == _VIN_LEN and not _is_valid_vin(matched_text):
            return False
    return True


def iter_unique_text_matches(page_text, patterns):
    """按页面文本提取唯一匹配字符串，避免重复 search_for。

    v37.7.18 cp55: 增加银行卡号 Luhn 校验，避免误匹配案件编号、日期等长数字串。
    v37.7.19 cp57: Luhn 校验限定为仅银行卡号 pattern 生效，避免过滤自定义正则。
    """
    if not isinstance(page_text, str) or not page_text.strip():
        return

    seen = set()
    for pattern in patterns or []:
        if not pattern or pattern in ("__SEAL_DETECTION__", "__SIGNATURE_DETECTION__"):
            continue
        try:
            iterator = re.finditer(pattern, page_text, re.IGNORECASE)
        except re.error:
            continue

        # cp57: 仅对银行卡号 pattern 执行 Luhn 校验
        is_bank_card_pattern = _is_bank_card_pattern(pattern)

        for match in iterator:
            found = match.group(0)
            if not found or found in seen:
                continue

            # cp55: 银行卡号正则匹配后增加 Luhn 校验
            # cp56 关键修复：先排除身份证号，避免误伤
            #   身份证号 15 位/18 位（纯数字）也在 13-19 位范围，但用 MOD 11-2 校验，
            #   不满足 Luhn 校验会被错误跳过
            # cp57: 仅对银行卡号 pattern 生效，避免过滤自定义正则
            if is_bank_card_pattern and len(found) >= 13 and len(found) <= 19 and found.isdigit():
                if _looks_like_idcard(found):
                    # 身份证号，跳过 Luhn 校验
                    pass
                elif not _is_valid_luhn(found):
                    # 安全审计 v40.1: 不记录命中原文，改打长度+首尾掩码
                    logger.info("[cp55] 数字串(len=%d %s) 不满足 Luhn 校验，跳过（非银行卡号）",
                                len(found), _mask(found))
                    continue

            # cp70: 统一社会信用代码/VIN 等带校验位 pattern 命中后二次校验
            if not verify_hit_by_pattern(pattern, found):
                logger.info("[cp70] 命中串(len=%d %s) 未通过校验位校验，跳过",
                            len(found), _mask(found))
                continue

            seen.add(found)
            yield found


def _merge_adjacent_same_line_rects(hits, y_tolerance=2.0, gap_ratio=0.5):
    """v37.7.17 cp48: 合并同一行上相邻的 rect（修复多字词被拆分为多个遮罩）。

    PyMuPDF 的 page.search_for(needle) 在 needle 跨越多个 text span 时
    （例如每个字符是独立 span），会为每个 span 返回一个 Rect。这导致
    多字关键词（如"王小明"）被错误地拆分为 3 个独立遮罩，替换时每个
    遮罩各替换一次，产生"华子 华子 华子"重复替换 bug。

    本函数将同一行（y0/height 相近）且 x 相邻（gap 小于较短 rect 宽度
    的 gap_ratio 倍）的 rect 合并为单个 rect。

    Args:
        hits: list[fitz.Rect] - 待合并的 rect 列表
        y_tolerance: y0 与 height 的容差（pt）
        gap_ratio: 相邻 rect 之间的 x 间隙阈值（相对较短 rect 宽度的比例）

    Returns:
        list[fitz.Rect] - 合并后的 rect 列表
    """
    if not hits:
        return []
    if len(hits) <= 1:
        return list(hits)

    # 提取 (x0, y0, x1, y1) 元组并按 (y0, x0) 排序
    # 兼容多种输入：fitz.Rect（有 x0/y0/x1/y1）、SimpleNamespace（只有 x0/y0/width/height）、
    # 4 元组 (x0, y0, x1, y1)
    rect_tuples = []
    for h in hits:
        if hasattr(h, "x0") and hasattr(h, "x1"):
            rect_tuples.append((float(h.x0), float(h.y0), float(h.x1), float(h.y1)))
        elif hasattr(h, "x0") and hasattr(h, "width"):
            rect_tuples.append((float(h.x0), float(h.y0),
                                 float(h.x0) + float(h.width),
                                 float(h.y0) + float(h.height)))
        else:
            x0, y0, x1, y1 = (float(v) for v in h)
            rect_tuples.append((x0, y0, x1, y1))

    rect_tuples.sort(key=lambda r: (r[1], r[0]))

    merged = []
    for x0, y0, x1, y1 in rect_tuples:
        if not merged:
            merged.append([x0, y0, x1, y1])
            continue

        prev = merged[-1]
        prev_x0, prev_y0, prev_x1, prev_y1 = prev
        prev_h = prev_y1 - prev_y0
        curr_h = y1 - y0

        # 同一行：y0 相近、height 相近
        same_line = (
            abs(y0 - prev_y0) <= y_tolerance
            and abs(curr_h - prev_h) <= y_tolerance
        )
        if not same_line:
            merged.append([x0, y0, x1, y1])
            continue

        # x 相邻：gap < 较短 rect 宽度 * gap_ratio（且不重叠）
        gap = x0 - prev_x1
        prev_w = prev_x1 - prev_x0
        curr_w = x1 - x0
        min_w = min(prev_w, curr_w)
        if min_w <= 0 or gap < 0 or gap > min_w * gap_ratio:
            # 间隙为负（重叠）或过大，视为不同匹配
            # 注：重叠情况应由下游 _deduplicate_rects 处理，这里只负责合并相邻
            merged.append([x0, y0, x1, y1])
            continue

        # 合并：扩展 prev 的 x1 到 curr 的 x1
        prev[2] = x1
        # height 取较大值（应对 OCR 微小偏差）
        if curr_h > prev_h:
            prev[3] = prev_y0 + curr_h

    # 转回与输入兼容的对象（保留 x0/y0/x1/y1/width/height 属性）
    try:
        import fitz
        return [fitz.Rect(r[0], r[1], r[2], r[3]) for r in merged]
    except ImportError:
        from types import SimpleNamespace
        return [SimpleNamespace(x0=r[0], y0=r[1], x1=r[2], y1=r[3],
                                width=r[2] - r[0], height=r[3] - r[1])
                for r in merged]


def apply_box_adjust_to_hit(x, y, w, h, ratio):
    """cp71: 对文本层 PDF 命中框按中心缩放（与图像 OCR 路径 box_adjust 语义一致）。

    正值收缩、负值扩大、零保持（与高级设置“OCR 检测框调节”提示一致）。
    y 方向收缩系数较小（0.6×），与图像路径 calculate_sub_rect 保持一致，
    避免上下过度收缩导致漏遵。保底宽/高不低于 1.0pt。

    Args:
        x, y, w, h: 命中框 PDF 坐标（左上角 + 宽高）
        ratio: box_adjust_ratio（-0.3 ~ 0.5）

    Returns:
        (x', y', w', h') 调整后 PDF 坐标
    """
    if not ratio:
        return (x, y, w, h)
    x_shrink = w * ratio / 2.0
    y_shrink = h * ratio * 0.6 / 2.0
    new_x = x + x_shrink
    new_y = y + y_shrink
    new_w = max(1.0, w - x_shrink * 2.0)
    new_h = max(1.0, h - y_shrink * 2.0)
    return (new_x, new_y, new_w, new_h)


def collect_text_pdf_hit_boxes(page, patterns, page_text=None, shared_person_names=None):
    """返回文本型 PDF 的唯一命中框坐标列表（含命中原文）。

    v37.7.13 cp43: 返回值追加第 5 元素 found_str，用于后续查找替换文本。
    v37.7.17 cp48: 调用 _merge_adjacent_same_line_rects 合并多字词被
        PyMuPDF 拆分为多个 per-char rect 的情况，避免多字词生成多个
        独立遮罩导致替换重复。
    cp67: 旋转页（page.rotation 非 0）上 search_for 返回未旋转坐标，
        而消费方（画布/导出）统一用 display 坐标，此处乘 rotation_matrix
        转为 display 坐标后再返回。
    cp_person_name: 带 lead 命名组的称谓人名 pattern 分流独立处理——
        人名/机构名后 search_for(名称) 天然返回该页所有同名位置。
    v40.2.3 文档级传播：shared_person_names（worker 持有的跨页共享集合）
        传入后，本页锚点发现的名称 union 进去，之前页已发现的名称在本页
        也遮——"发现即全文档遮"（签名行等无锚点出现处靠此传播覆盖）。
    返回 list[(x0, y0, w, h, found_str, rule_override)]；
    rule_override 非 None（= "称谓人名"）时消费方应直接用其分类。
    """
    if page_text is None:
        page_text = page.get_text()

    rotation = getattr(page, "rotation", 0)
    hit_boxes = []

    def _append_hits(found_str, rule_override=None):
        try:
            hits = page.search_for(found_str)
        except RuntimeError as exc:
            logger.warning("[cp118] 搜索文本错误: %s", exc)
            return
        if not hits:
            return
        # v37.7.17 cp48: 合并同一匹配被 PyMuPDF 拆分为多个 per-span rect 的情况
        merged_hits = _merge_adjacent_same_line_rects(hits)
        for hit in merged_hits:
            if rotation:
                # cp67: 未旋转坐标 -> display 坐标（与渲染/遮罩链路一致）
                hit = fitz.Rect(hit) * page.rotation_matrix
                hit.normalize()
            hit_boxes.append((hit.x0, hit.y0, hit.width, hit.height,
                              found_str, rule_override))

    # cp_person_name: 分流称谓人名 pattern（识别 lead 命名组语法；
    # v2 正则只消费称谓+分隔符，人名由引擎 lookahead 提取）
    person_patterns = set(
        p for p in (patterns or [])
        if isinstance(p, str) and "(?P<lead>" in p
    )
    regular_patterns = [p for p in (patterns or []) if p not in person_patterns]

    if person_patterns:
        from privacyguard.ocr.person_name import (
            find_person_names_by_pattern, PERSON_NAME_RULE_NAME,
        )
        # v40.2.3: 本页新发现 → 共享集合；搜索目标 = 新发现 ∪ 前页已发现
        new_names = set()
        for p in person_patterns:
            for name, _s, _e in find_person_names_by_pattern(page_text, p):
                if name:
                    new_names.add(name)
        if shared_person_names is not None:
            new_names |= set(shared_person_names)
            shared_person_names |= new_names
        seen_names = set()
        for name in new_names:
            if name in seen_names:
                continue
            # v40.2.3 性能守卫：子串预筛比 search_for 便宜 1-2 个数量级——
            # 大文档（100+ 人名 × 248 页）无守卫时主循环多耗 ~18s
            # （本页锚点新发现的名字天然在 page_text 中，守卫只挡前页传播名）
            if name not in page_text:
                continue
            seen_names.add(name)
            _append_hits(name, PERSON_NAME_RULE_NAME)

    # cp118: 删除 text_search_cache —— iter_unique_text_matches 的 seen 集合已保证
    # 每个 found_str 只 yield 一次，缓存恒不命中，属无效开销。
    for found_str in iter_unique_text_matches(page_text, regular_patterns):
        _append_hits(found_str)

    return hit_boxes
