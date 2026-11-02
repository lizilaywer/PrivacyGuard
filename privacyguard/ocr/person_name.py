# -*- coding: utf-8 -*-
"""cp_person_name: 诉讼文书"称谓人名"识别引擎（纯函数，零依赖）。

设计（上下文触发式识别，v2 算法）：
- 法律文书的人名几乎总出现在称谓词（被告人/原告/辩护人…）之后，有时中间
  隔 ":"/"："/空白。称谓词作为"人名发现的锚点"。
- v2 修正（首轮实测暴露的缺陷）：正则只消费"称谓+分隔符"，人名部分用
  lookahead 断言（不消费）——否则被否决的贪婪候选会"吃掉"后续称谓词
  （"被告人的辩护人王五"中人名锚点"辩护人"被上一轮候选吞没）。
- 候选提取三步（extract_from_run）：
  1. 连接词截断：连续汉字串中最早出现的连接词（及/到/的…）位置在 2-4 时
     取前缀（"李四及证人"→"李四"；"王小明到案"→"王小明"）
  2. 尾词裁剪：串尾的法律动词/后缀修剪（"张三到庭"→"张三"；"当庭供述"→
     "当庭"→"当庭"再剪→<2 否决）
  3. 词表验证：长度 2-4、首字非虚词、非称谓词本身
- 识别出的人名由调用方做"发现即全页遮"（同页其他位置同名一并遮罩）。

性能约束（用户决策）：规则未启用时本模块零初始化——所有函数仅在
调用方（三条管线）实际拿到含 lead 组的命中时才被执行。

渐进式验证路线：
- 阶段1（本文件）：词表规则
- 阶段2：jieba 词性标注（nr）验证（懒 import，见 validate_person_name）
- 阶段3（条件触发）：ONNX NER 小模型精修边界
"""
import re

__all__ = [
    "DEFAULT_TITLES",
    "build_person_name_pattern",
    "find_title_person_names",
    "find_person_names_by_pattern",
    "extract_person_name_from_run",
    "validate_person_name",
    "PERSON_NAME_RULE_NAME",
]

# 规则显示名（与 config default_rules 键一致；命中项的分类 override 用）
PERSON_NAME_RULE_NAME = "称谓人名"

# 内置诉讼称谓全集（用户提供的 15 个 + 法律文书常见扩展）。
# 顺序无关：build_person_name_pattern 会按长度降序排列（正则交替最长优先，
# 防"被告"吃掉"被告人"的前缀、"申请人"吃掉"被申请人"的后缀）。
DEFAULT_TITLES = [
    # 用户提供的核心称谓
    "被告人", "犯罪嫌疑人", "原告", "辩护人", "证人", "被害人", "被告",
    "上诉人", "被上诉人", "申请人", "被申请人", "异议人", "答辩人", "被答辩人",
    # 法律文书常见扩展
    "公诉人", "自诉人", "附带民事诉讼原告人", "附带民事原告人", "原告人",
    "原审被告人", "再审申请人", "执行申请人", "被执行人",
    "委托诉讼代理人", "委托代理人", "法定代理人", "诉讼代理人", "代理人",
    "第三人", "鉴定人", "翻译人员", "翻译人", "保证人", "勘验人",
]

# 标签类锚点（工商/合同/表格类文书，v40.2.2 实测驱动）：与称谓不同，
# 这类词在普通行文中也出现（"甲方违约""股东会决定"），必须后跟冒号才触发
# （"公司名称：池州市…" "人员姓名：彭幼林" "甲方：XXX"），从根上防误配。
LABEL_TITLES = [
    "公司名称", "人员姓名", "法定代表人", "姓名", "名称", "股东", "出资人",
    "甲方", "乙方", "丙方", "丁方",
    "出卖人", "买受人", "委托人", "受托人", "借款人", "贷款人",
    "抵押人", "抵押权人", "出租人", "承租人", "发包人", "承包人",
    "转让方", "受让方", "联系人", "经营者", "负责人", "买方", "卖方",
    "建设单位", "施工单位", "监理单位", "业主",
]

# 机构名后缀（机构名识别，v40.2.2）：称谓/标签后的连续串若以这些词结尾，
# 整串（4-25 字）识别为机构名——"公司名称：池州市久兴置业有限公司"整名命中。
_ORG_SUFFIXES = sorted(
    [
        "有限责任公司", "股份有限公司", "有限公司", "合伙企业", "事务所",
        "合作社", "研究中心", "研究院", "研究所", "公司", "工厂", "中心",
        "医院", "学校", "大学", "学院", "银行", "支行", "分局", "委员会",
        "协会", "商店", "门市部", "经营部", "服务部", "事务所",
    ],
    key=len, reverse=True,
)

# 候选首字停用集：这些字几乎不可能作为姓氏/人名首字（功能虚词/机构用字）。
# 实测驱动扩充（16 页真实卷宗）：知(被告知人)/被(被人民法院)/人(人民法院)/
# 提(保证人提供保证)/证(证人证言)——均非百家姓，零误伤。
# 反向结构左修剪扩充：由在将让就（前文粘连）+ 事同友邻亲哥姐弟妹母父妻夫战
# （关系词尾/首字："同事陈绕奇"窗口粘连"事"、"同事李四"循环剪"同"+"事"）。
# 注意：不要把真实姓氏（于/向/从/和/经等）放进这里。
_LEAD_STOP_CHARS = set(
    "的等之其该又亦即均及着了过吧吗呢地得或者知被人提证由在将让就"
    "事同友邻亲哥姐弟妹母父妻夫战认"
)

# 连接词（单字）：连续汉字串中出现位置在 [2,4] 时，取其前缀作为人名候选。
# 用于把"李四及证人""王小明到案""张某某的供述"正确切出人名。
# 注意"到/在/于/系"等同时也是真实姓氏——但人名前缀里出现在第 2-4 位
# 且后面还有汉字的场景，绝大多数是"人名+谓语"结构，姓氏场景（如"王在明"
# 整名出现在称谓后且无标点）由连接词截断优先级（最早位置）+ 尾词裁剪兜底。
_CONNECT_CHARS = set("及与和到在于系称供当均指的等又亦就便则")

# 尾部裁剪词表：候选以这些词/字结尾时修剪（"张三到庭"→"张三"）。
# 按长度降序参与修剪，循环修剪直到不再命中或长度不足。
_TAIL_STOP_TERMS = sorted(
    [
        "到庭", "当庭", "出庭", "及其", "又名", "曾用名", "供述", "辩称", "供述称",
        "陈述", "发言", "指认", "到案", "到案后", "出生于", "出生", "现住",
        "户籍", "身份证", "汉族", "回族", "满族", "藏族", "族",
        "共同", "一起", "于", "在", "向", "从", "因", "经", "由", "系",
        "称", "说", "问", "答", "供", "辩", "男", "女", "住", "和", "与",
        "及", "或", "后", "前", "时", "间", "日", "月", "年", "之", "的",
    ],
    key=len, reverse=True,
)

# 称谓词集合（用于否决"候选本身是称谓词"的场景，如"原告代理人到庭"裁边后剩"代理人"）
_TITLE_SET = set(DEFAULT_TITLES)

# 非人名词否决表：庭审高频副词/动词短语，称谓后紧跟时不是人名。
# 前缀否决（"当庭翻供"截断产出"当庭翻"也否决）——这些词开头的串不可能是
# 人名（当/如/自/分/共 均非姓氏，无误伤）。
_NOT_NAME = ("当庭", "如实", "自愿", "分别", "共同", "上述", "另案", "在案", "到案",
             "姓名", "名称")  # 实测：称谓后跟"申请人姓名"类标签词

# 已编译 pattern 缓存（按 titles 元组键缓存，避免每次重编译）
_pattern_cache = {}

_HAN_CHAR = r"\u4e00-\u9fa5"
_RE_HAN_RUN = re.compile(rf"[{_HAN_CHAR}]+")


def build_person_name_pattern(titles=None):
    """生成称谓锚点正则（带命名组 lead/lb，供管线识别与人名提取）。

    v2 结构：(?P<lead>称谓alt)\\s*[:：]?\\s* | (?P<lb>标签alt)\\s*[:：]\\s*
            后随 (?=[\\u4e00-\\u9fa5]{2}) lookahead

    - lead 交替按长度降序：任意位置优先匹配最长称谓（"被告人"不被"被告"截断）
    - 标签分支（lb，v40.2.2）强制冒号：标签词在普通行文也出现（"甲方违约"
      "股东会决定"），必须 "公司名称：X" 形态才触发，从根上防误配
    - 人名部分用 lookahead（不消费）：正则匹配只到分隔符为止——被否决的
      候选不会吞掉后续称谓锚点；后续连续汉字串由引擎提取
    - lookahead 要求至少 2 个汉字：纯标点/数字跟随时不产生锚点命中
    """
    key = tuple(titles) if titles else None
    if key in _pattern_cache:
        return _pattern_cache[key]
    use_titles = titles if titles else DEFAULT_TITLES
    lead_alt = "|".join(
        re.escape(t) for t in sorted((t for t in use_titles if t), key=len, reverse=True)
    )
    label_alt = "|".join(
        re.escape(t) for t in sorted((t for t in LABEL_TITLES if t), key=len, reverse=True)
    )
    pattern = (
        rf"(?:(?P<lead>{lead_alt})\s*[:：]?\s*"
        rf"|(?P<lb>{label_alt})\s*[:：]\s*)"
        rf"(?=[{_HAN_CHAR}]{{2}})"
    )
    _pattern_cache[key] = pattern
    return pattern


# 反向结构链接词："陈绕奇作为保证人"（姓名在前、称谓在后）
_REVERSE_LINK = r"(?:作为|担任|系)"


def _build_reverse_pattern(titles=None):
    """反向锚点正则：([\u4e00-\u9fa5]{2,4})(?:作为|担任|系)(?=称谓)。

    实测驱动（16 页真实卷宗漏检"陈绕奇作为保证人提供保证"）：法律文书中
    "姓名+作为/担任/系+称谓"结构高频。贪婪 4 字窗口向左扩展，提取时左修剪
    前文粘连功能字（"由陈绕奇"→"陈绕奇"）。内部使用（不进 config），
    find_person_names_by_pattern 双扫描自动生效，管线零改动。
    """
    use_titles = titles if titles else DEFAULT_TITLES
    lead_alt = "|".join(
        re.escape(t) for t in sorted((t for t in use_titles if t), key=len, reverse=True)
    )
    return rf"([{_HAN_CHAR}]{{2,4}}){_REVERSE_LINK}(?={lead_alt})"


def _trim_leading(name):
    """反向窗口左修剪：剪掉前文粘连的功能字（_LEAD_STOP_CHARS）直到 ≥2 字。"""
    s = name
    while len(s) > 2 and s[0] in _LEAD_STOP_CHARS:
        s = s[1:]
    return s if len(s) >= 2 else None


def extract_person_name_from_run(run):
    """从称谓后的连续汉字串中提取人名候选（run 内偏移由调用方计算）。

    策略（按优先级）：
      1. 连接词截断：最早出现在 [2,4] 位的连接词（及/到/的…）前缀
         —— "李四及证人"→"李四"、"王小明到案"→"王小明"、"张某某的供述"→"张某某"
      2. 尾词裁剪：法律动词/后缀循环修剪
         —— "张三到庭"→"张三"、"当庭供述"→"当庭"→"当庭"否决
      3. 整串（若 2-4 字）—— "张三"（串后是标点截断的干净场景）

    Returns:
        人名 str；None 表示否决（含 validate 失败）。
    """
    if not isinstance(run, str) or len(run) < 2:
        return None
    # 1. 连接词截断（最早位置优先；位置 0/1 无意义——前缀不足 2 字）
    for i in range(2, min(len(run), 5)):
        if run[i] in _CONNECT_CHARS:
            cand = run[:i]
            if validate_person_name(cand):
                return cand
            break  # 该连接词处截断被否决 → 落到尾词/整串策略
    # 2. 尾词裁剪（记录是否剪过——剪后无效则不再启用整串兜底，防"当庭供述"
    #    剪"供述"剩"当庭"被否后又被整串"当庭供述"救活）
    s = run
    trimmed = False
    while len(s) >= 3:
        cut = False
        for term in _TAIL_STOP_TERMS:
            if s.endswith(term) and len(s) - len(term) >= 2:
                s = s[: len(s) - len(term)]
                cut = True
                trimmed = True
                break
        if not cut:
            break
    if len(s) <= 4 and validate_person_name(s):
        return s
    # 3. 干净整串（2-4 字且尾词从未剪过——串后标点截断的干净场景）
    if not trimmed and len(run) <= 4 and validate_person_name(run):
        return run
    return None


def validate_person_name(name):
    """词表验证（阶段1）。阶段2 将在此叠加 jieba nr 词性验证（懒加载）。"""
    if not isinstance(name, str) or not (2 <= len(name) <= 4):
        return False
    if name in _TITLE_SET:
        return False
    if name.startswith(_NOT_NAME):
        return False
    if name[0] in _LEAD_STOP_CHARS:
        return False
    return True


def _extract_org_name_from_run(run):
    """机构名识别（v40.2.2 后缀锚定）：run 的某前缀以机构后缀结尾 → 该前缀。

    "池州市久兴置业有限公司股东于…" → 找到最早的后缀结束点 →
    "池州市久兴置业有限公司"（"股东于"丢弃）。
    长度约束 4-25 字（"XX公司"最短 4 字）。仅在人称提取失败后调用，
    避免"王小明到市中心医院"先误判机构（人名优先命中即不进此分支）。
    """
    if not isinstance(run, str) or len(run) < 4:
        return None
    limit = min(len(run), 25)
    for i in range(4, limit + 1):
        prefix = run[:i]
        for suf in _ORG_SUFFIXES:
            if prefix.endswith(suf) and len(prefix) >= 4:
                # 机构名首字不应是虚词（防"的…公司"类粘连）
                if prefix[0] not in _LEAD_STOP_CHARS:
                    return prefix
    return None


def find_person_names_by_pattern(text, pattern, titles=None):
    """按称谓 pattern（含 lead/lb 命名组）找人名/机构名（管线统一入口）。

    双扫描：
      正向：称谓/标签+分隔符匹配（lookahead 不消费）→ 提取后续连续汉字串 →
            人名三策略切分；人名未命中时尝试机构名后缀锚定
            （"公司名称：池州市久兴置业有限公司"整名识别）
      反向：(?P<名窗口>2-4字)(作为|担任|系)(?=称谓) → 左修剪前文粘连字
            （"由陈绕奇作为保证人"→"陈绕奇"）

    同一个锚点最多产出一个人名或机构名；否决的锚点不阻止后续锚点。
    引擎内自动完成全部扫描，管线（text_pdf/mixed_pdf/word_worker）零改动。

    Yields:
        (名称, start, end)：人名或机构名及在 text 中的偏移。
    """
    if not isinstance(text, str) or not text or not pattern:
        return
    try:
        compiled = re.compile(pattern)
    except re.error:
        return
    if "lead" not in compiled.groupindex:
        return
    # 正向扫描（称谓+标签）
    for m in compiled.finditer(text):
        run_start = m.end()
        # 提取从 run_start 开始的连续汉字串
        run_m = _RE_HAN_RUN.match(text, run_start)
        if run_m is None:
            continue
        run = run_m.group(0)
        name = extract_person_name_from_run(run)
        if name:
            yield name, run_start, run_start + len(name)
            continue
        # 人名未命中 → 机构名后缀锚定（v40.2.2）
        org = _extract_org_name_from_run(run)
        if org:
            yield org, run_start, run_start + len(org)
    # 反向扫描（姓名+作为/担任/系+称谓）
    try:
        rev = re.compile(_build_reverse_pattern(titles))
    except re.error:
        return
    for m in rev.finditer(text):
        pre = m.group(1)
        name = _trim_leading(pre)
        if name and validate_person_name(name):
            offset = len(pre) - len(name)
            yield name, m.start(1) + offset, m.end(1)
    # 动词锚点（v40.2.2 章程/出资句式）："由X出资"右侧边界由"出资"锁定无需裁剪；
    # "设立X"取 run 做机构后缀锚定（"设立池州市…有限公司"）
    try:
        for m in re.finditer(rf"由([{_HAN_CHAR}]{{2,4}})出资", text):
            if validate_person_name(m.group(1)):
                yield m.group(1), m.start(1), m.end(1)
        for m in re.finditer(rf"设立(?=[{_HAN_CHAR}]{{4}})", text):
            run_m = _RE_HAN_RUN.match(text, m.end())
            if run_m is None:
                continue
            org = _extract_org_name_from_run(run_m.group(0))
            if org:
                yield org, m.end(), m.end() + len(org)
    except re.error:
        return


def find_title_person_names(text, titles=None):
    """在文本中找出全部"称谓词+人名"，返回 [(人名, start, end)]。

    供 Word 收集 pass、测试与将来模型层使用；管线走
    find_person_names_by_pattern（管线持有 pattern 字符串）。
    """
    if not isinstance(text, str) or not text:
        return []
    return list(find_person_names_by_pattern(text, build_person_name_pattern(titles)))
