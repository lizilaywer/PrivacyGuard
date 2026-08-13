# Pitfalls Research

**Domain:** 中文 PII 自动识别引擎 + Excel/图片脱敏，嵌入 PyQt6 桌面应用
**Researched:** 2026-08-10
**Confidence:** MEDIUM（基于多源验证；具体格式校验算法为 HIGH，社区共识；部分掩码重识别风险为 MEDIUM）

## Critical Pitfalls

### Pitfall 1: 假脱敏（Fake Redaction）—— 文字可被复制粘贴还原

**What goes wrong:**
在 PDF 上"涂黑"或覆盖矩形但未真正删除底层文本对象。攻击者只需"复制"+"粘贴到记事本"或运行 `pdftotext`/`pdfminer` 即可还原所有原文。这是脱敏工具的**头号灾难性失败**——比漏识别还要危险，因为它给用户制造了"已脱敏"的错觉。

**Why it happens:**
工程师直觉地把"打黑色方块"等同于"删除文字"。`fitz.Page.draw_rect()`、`insert_text`、`add_highlight`/`add_text`、甚至 `add_redact_annot` 之后忘记调用 `apply_redactions()`，都会留下可提取的原文。PDF 规范允许任意图层叠加，视觉遮蔽不构成内容移除。

**How to avoid (按格式分)：**
| 格式 | 错误做法 | 正确做法 |
|------|---------|---------|
| **PDF** | `page.draw_rect(rect, fill=(0,0,0))` 或 `insert_text` 覆盖 | PyMuPDF：`page.add_redaction(rect, text="")` → `page.apply_redactions(keep_text=False)`；必须显式 `keep_text=False`，默认就是 False 但要避免被改成 True |
| **Word (DOCX)** | 把文字改成 `color: white` 或把段落 visibility 设为 hidden | 真删除文本节点；保留结构时使用 `<w:vanish/>` 也仍是隐藏——必须删除 run 内的 `<w:t>` 或整体替换为占位符 |
| **Excel** | 把单元格背景设黑色、字体设白色、隐藏行列、缩到 0 高度 | 删除 `cell.value`（注意 `cell._value` 是私有 API，应设 `cell.value = None`）并清理 `cell.font`/`cell.fill` 样式；隐藏行列需同时删除数据 |
| **图片 (JPG/PNG)** | 用 `cv2.rectangle` 画黑框覆盖人脸/号码 | 必须**像素级重绘**（mask + inpaint 或直接 overwrite 像素区域为邻域均值）；EXIF/GPS/XMP 必须另外清除 |

**Warning signs:**
- 代码里出现 `draw_rect`、`fill=(0,0,0)`、`insert_text` 出现在 redaction/sanitize 相关函数名附近
- 出现 `highlight=` 但缺少 `apply_redactions`
- 单元测试只验证"画框了"但不验证"复制后是否还能拿到原文"

**Phase to address:**
- **PII 引擎基础阶段**：在写第一行 redaction 代码前建立抽象层 `Redactor.redact(rect, format)`，内部分派到正确的真删除实现
- **格式扩展阶段 (Excel / 图片)**：每个新格式的 Redactor 必须有"reverse-test"——跑脱敏 → 提取 → 断言原文不存在

---

### Pitfall 2: Excel "全表散点扫描"漏掉 11 个隐藏数据通道

**What goes wrong:**
只扫描 `ws.iter_rows(values_only=True)` 拿到每个 cell 的显示值，**完全忽略** xlsx ZIP 包里那些不显示在主工作表的"幽灵数据"。即便每个显示 cell 都正确脱敏，原始信息仍通过以下通道泄露：

1. **隐藏工作表** (`sheet_state="hidden"` 或 `"veryHidden"`)
2. **隐藏行/列**（通过行高 0 或 `<row r="N" hidden="1"/>` 标记）
3. **批注/笔记** (`<comments>`、`threadedComments`、`legacyVBAThreadedComment`)
4. **定义名称** (`definedNames` —— 公式里引用 A1:A1000 这种命名范围)
5. **共享字符串表** (`sharedStrings.xml` —— 即便 cell 被删除，字符串索引仍在)
6. **公式字符串** (`<f>SUM(A1:A100)</f>` 引用了带数据的范围)
7. **数据透视表缓存** (`pivotCacheDefinition.xml` + `pivotCacheRecords.xml`)
8. **外部链接/嵌入对象** (`externalLinks/`, `OLEObjects`)
9. **文档属性** (`docProps/core.xml`, `app.xml`, `custom.xml`)
10. **修订历史** (`revisions/`, `revisions.xml` 包含所有 edit history)
11. **自动筛选缓存** (`autoFilter` 含隐藏行的过滤值)

**Why it happens:**
openpyxl 的 `load_workbook(..., data_only=False)` 默认加载主可见工作表的所有单元格，但 `data_only=True` 拿到的也是缓存计算结果，不覆盖隐藏工作表/批注/属性。开发者往往把"读取所有 cell"等同于"读取工作簿全部内容"，忘记 xlsx 是 ZIP+XML。

**How to avoid:**
```python
# 必须显式遍历所有这些位置
ws_list = [s for s in wb.worksheets]   # 包含 hidden 的所有 sheet
for ws in wb.worksheets:
    if ws.sheet_state != "visible":
        log.warn(f"hidden sheet: {ws.title}")  # 必须脱敏或显式删除
    for row in ws.iter_rows():  # 包含 hidden rows/cols
        for cell in row:
            ...
# 单独遍历：wb.defined_names, ws.comments, ws.tables
# ZIP 层：手动解包 docProps/*.xml、pivotCacheRecords、revisions
```

策略：扫描阶段输出**全量命中列表**（含来源），脱敏阶段按命中列表逐条处理；不要假设"扫描 cell 即可代表扫描工作簿"。

**Warning signs:**
- 脱敏后用 7-Zip 打开 xlsx 还能看到原始 PII
- `core.xml` 里 creator = 真实姓名
- `custom.xml` 存在 `ProjectID`、`ClientName` 等自定义属性
- 共享字符串索引指向已"删除"的 cell

**Phase to address:**
- **Excel 格式接入阶段**：必须建立"xlsx 11 通道扫描器"，每个通道独立测试
- **PII 引擎阶段**：识别引擎输出要能标注 `source: hidden_sheet|comment|defined_name|...`

---

### Pitfall 3: 身份证校验位算法错误 + X 大小写陷阱

**What goes wrong:**
1. **算法错误**：权重数组写错（必须 `[7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]`），mod 映射表错（必须 `[1,0,'X',9,8,7,6,5,4,3,2]`）
2. **X 大小写**：身份证校验位合法值只有**大写** `X`，小写 `x` 是无效字符串。但 OCR 极易输出小写 `x`，盲目通过会引入假阴性
3. **15 位与 18 位并存**：早期身份证（1999 年前）是 15 位格式 `6位区划 + 6位生日(YYMMDD) + 3位序`，无校验位；现在两者都在流通
4. **生日字段检查缺失**：mod 11 校验通过但 `MMDD` 是 `13月` 或 `2月30日` 仍合法（按字符规则）
5. **顺序码奇偶判断男女失效**：校验位通过但顺序码语义错误（如末位奇偶反）

**How to avoid:**
```python
WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
MAPPING = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')

def validate_18(s: str) -> bool:
    if len(s) != 18 or not s[:17].isdigit() or s[17] not in '0123456789Xx':
        return False
    try:
        checksum = sum(int(s[i]) * w for i, w in enumerate(WEIGHTS)) % 11
        expected = MAPPING[checksum]
        return s[17].upper() == expected  # 必须 .upper()，但 OCR 出的 'x' 视为可疑
    except (ValueError, IndexError):
        return False

def validate_15(s: str) -> bool:
    if len(s) != 15 or not s.isdigit():
        return False
    yy = int(s[6:8])
    mmdd = s[8:14]
    # 1900-1999 年范围的 15 位 → 升级为 18 位再校验
    expanded = s[:6] + '19' + s[6:] + '_'  # 占位
    return _date_valid(yy + 1900, mmdd)
```

**Warning signs:**
- 单元测试只测了 `110101199003078811` 这类已知样本
- 未测试末位为 `X` 的样本
- 未测试 OCR 输入的 `x`（小写）该被标记为"待确认"还是直接脱敏
- 未测试 15 位旧格式

**Phase to address:**
- **号码类识别阶段 (PII engine 第一阶段)**：身份证校验函数必须有 ≥ 20 条断言样本（含 X、小写 x、边界生日）

---

### Pitfall 4: 手机号段表静态化导致新号段被漏判

**What goes wrong:**
代码里写死 `1[3-9]\d{9}` 看似覆盖，但：
1. 2017 年 8 月工信部新批 **166（联通）、198（移动）、199（电信）**
2. 2019 年 12 月新批 5G 号段：**190（电信）、192（广电）、196（联通）、197（移动）**
3. 虚拟运营商：**162、165、167、170(0-9)、171**
4. 物联网专用：**1400、1410、1440、146、148、1740、1749**（**这些不应被识别为手机号**）

如果规则仍按"2010 年以前的号段"写死，新号段用户接到脱敏文档后会出现明显的合规盲区。

**How to avoid:**
- **正确的第二段规则**：`1[3-9]\d{9}` 实际在 2017 年后仍覆盖了 166/198/199（因为 `[3-9]` 包括 3-9，166 第二位 6 在范围内），关键是把 `0-9` 写对；新号段 190/192/196/197 同样在 `[3-9]` 范围内，**这条规则已经覆盖**
- **真正的陷阱是反过来**：误把"14X"全部当手机号，但 **140/141/144/146/148/149 是物联网/数据卡/卫星电话**，不应被识别为个人手机号
- 维护**双白名单**：个人号段（110-199）+ 排除列表（14X 物联网段、1740/1749 卫星段、1700/1701/1702 部分虚拟运营商段）

**Warning signs:**
- 识别规则没有任何"号段分配"的元数据，只是一个大正则
- 新号段用户反馈"我的手机号没被脱敏"（说明规则范围反而过紧）
- 把 14001234567 这种物联网号当手机号脱敏（说明规则过松）

**Phase to address:**
- **号码类识别阶段**：规则文件必须包含 `is_mobile_segment(prefix)` 函数而非纯正则；可维护性 + 准确性双赢

---

### Pitfall 5: 银行卡号 Luhn 通过即信任 → 订单号误杀

**What goes wrong:**
订单号、产品编号、ISBN、机票号、增值税发票号等"看起来像 16-19 位数字"的字符串，在随机分布下也经常 Luhn 通过。结果：
1. **假阳性**：把 `ORDER1234567890123456` 这种业务号脱敏成 `[已脱敏]`，破坏文档可读性，用户失去信任
2. **假阴性**：真银行卡号但经过 OCR 错位（多一位/少一位）导致 Luhn 不通过，引擎放走

**Why it happens:**
单维度校验（只看 Luhn）缺少**上下文信号**——银行卡号往往伴随"银行卡""卡号""账户""银行""尾号XXXX""BIN 622126-622925"等关键词；订单号伴随"订单""单号""Order #""PO#""SKU"。

**How to avoid:**
- **多信号联合**：`confidence = w1*Luhn + w2*context_keyword + w3*BIN_prefix + w4*length_in_range`
- **BIN 前缀库**：中国境内银行卡 BIN 段（`62` 开头银联、`4` VISA、`5` MasterCard、`35` JCB、`6` Discover）维护成常量
- **分级处置**：高置信度（Luhn + 上下文 + BIN）→ 直接脱敏；中置信度（仅 Luhn 或仅上下文）→ 标"待确认"；低置信度 → 不脱敏
- **脱敏方式分级**：高置信度用部分掩码（如 `**** **** **** 1234`），中置信度用完全占位符 `[银行卡号]`

**Warning signs:**
- 用户投诉"我的合同编号被脱敏了"
- 测试集里 Luhn 校验通过率超过 70%（说明缺乏上下文筛选，正常场景下银行卡号密度远低于此）
- 识别引擎没有任何"上下文窗口"概念

**Phase to address:**
- **号码类识别阶段**：每个号码类实体类型必须支持"上下文增强"和"分级置信度"两个开关，不允许只跑纯正则

---

### Pitfall 6: 全角/半角数字 + OCR 字符混淆导致校验失败

**What goes wrong:**
1. **全角数字 `１２３` vs 半角 `123`**：身份证里的 `1` 是 ASCII `0x31` 还是全角 `0xEFBC8F`（UTF-8）？OCR 输出、Word 文档复制、不同输入法都可能导致混合
2. **0/O、1/l/I、8/B 混淆**：身份证末位是 `B` 还是 `8`？手机号第二位是 `0` 还是 `O`？银行卡第 5 位是 `1` 还是 `l`？OCR 极常见
3. **数字内嵌分隔符**：`110101-19900307-8811`（身份证加横杠）、`138-0013-8000`（手机号）、`6222 0202 0000 0000 0000`（银行卡空格）
4. **校验位算出来后错位**：OCR 多识别或少识别一个字符，整段校验失败 → 引擎认为"非身份证" → 漏判

**How to avoid:**
```python
def normalize_digits(text: str) -> str:
    """全角→半角 + 移除常见分隔符"""
    # 全角数字 0xFF10-0xFF19 → 0x30-0x39
    text = text.translate(str.maketrans(
        '０１２３４５６７８９', '0123456789'
    ))
    # 移除常见分隔符
    text = re.sub(r'[-\s ]', '', text)
    return text

# OCR 字符置信度加权
def char_is_digit_with_confidence(char: str, ocr_conf: float) -> bool:
    """低置信度的 O/l/I 应视为可疑，但不直接当数字"""
    if ocr_conf < 0.7 and char in 'OolI':
        return 'ambiguous'  # 标记为待人工确认
    return char.isdigit()
```

**Warning signs:**
- 真实文档里身份证号被显示为 `１１０１０１１９９００３０７８８１１`（全角）但引擎未匹配
- 校验位 OCR 错位导致 18 位验证全部失败
- 单元测试只用 ASCII 数字，未用真实文档的全角样本

**Phase to address:**
- **号码类识别阶段**：所有输入必须经 `normalize_digits` 预处理，引擎内有"ambiguous OCR"通道
- **OCR 后处理阶段**：与 RapidOCR 输出对接时拿 `confidence` 字段，做加权校验

---

### Pitfall 7: 跨边界实体（line break / page break / cell 边界）被切断

**What goes wrong:**
身份证号被表格换行拆成 `11010119900307\n8811`、手机号被 PDF 多栏拆成两段、银行账号被 Excel 单元格切断变成 `6222 0202 / 0000 0000 / 0000 0000`。
**结果**：每段都不满足正则，**整个实体全部漏判**。

**Why it happens:**
- 默认正则用 `\b` 单词边界，跨行不连续
- PDF 文字层按"块"返回（`page.get_text("dict")`），换行符在每块末尾存在
- Word `paragraph.text` 把段落作为一个字符串，但段落内 `\n` 不会拆，跨段才拆分
- Excel 每 cell 独立，但表格里多 cell 表示一个值时跨 cell 边界

**How to avoid:**
```python
def find_entities_with_line_break_tolerance(text: str, pattern: re.Pattern) -> List[Match]:
    """先把文本里所有 [\n\r\t ] 合并，再跑正则"""
    # 策略 1：先把换行/空白替换掉再匹配
    flat = re.sub(r'[\s 　]+', '', text)
    matches = []
    for m in pattern.finditer(flat):
        # 把 flat 偏移映射回原始 text 偏移
        orig_start = map_flat_to_original(flat_offset=m.start(), original=text)
        orig_end = map_flat_to_original(flat_offset=m.end(), original=text)
        matches.append(Match(orig_start, orig_end, m.group()))
    return matches

# 策略 2：分别匹配每行，再看跨行拼接是否满足校验
#   chunks = text.splitlines()
#   for i in range(len(chunks)-1):
#       concat = chunks[i] + chunks[i+1]
#       if validate(concat): ...
```

**Warning signs:**
- PDF 文档里看到完整身份证号但扫描结果漏报
- 文档来自发票打印件（每行宽度有限）
- Word 表格里同一行的多 cell 内容拼接

**Phase to address:**
- **PII 引擎设计阶段**：必须支持"跨行拼接匹配"模式，作为单独开关

---

### Pitfall 8: 部分掩码一致性 → 跨文档关联攻击

**What goes wrong:**
两个文档都脱敏同一个身份证 `110101199003078811`：
- 文档 A：`110101********811`（保留前 6 + 后 3）
- 文档 B：`11010119900307****`（保留前 14）

两个文档单独看都"已脱敏"，但**同一实体在两份文档里留下不同片段**，攻击者拼接即可还原。

更严重的：身份证**前 6 位**就是**行政区划代码**（GB/T 2260），**7-14 位**就是**出生日期**——保留这两段等于泄露"哪个城市的人 + 哪年出生"——本身就是强准标识符（quasi-identifier），Wang et al. (IEEE TrustCom 2023) 的研究显示这足够在外部人口统计上做高概率重识别。

**How to avoid:**
- **同实体一致性**：引擎内部维护 `(entity_type, normalized_value)` 哈希，确保同一文档内同一值用同一掩码模板
- **跨文档一致性（可选高级）**：提供"批次一致"开关，用户在批量脱敏时强制同号段用同掩码
- **避免高风险保留**：身份证掩码推荐 `***1990****811` 或仅保留末 4 位，避免暴露行政区划
- **银行卡 Luhn 上界**：保留末 4 位是 PCI DSS 合规上限，不要再多保留

**Warning signs:**
- 引擎没有 `entity_normalizer`（同一身份证前后空格/全角差异被当成不同实体）
- 单元测试只测"掩码格式"不测"同实体多实例一致性"
- 用户用同一引擎处理两个文档后能交叉还原

**Phase to address:**
- **部分掩码阶段**：必须先实现"实体规范化层"，再谈掩码规则
- **跨文档批处理阶段**：引入"实体指纹"和"批次掩码策略模板"

---

### Pitfall 9: PyInstaller 打包时新增数据文件 / 模块导入回归

**What goes wrong:**
新增 PII 引擎后引入：
- 字典文件（省份/城市/机构名/常见姓氏）
- 规则 YAML/JSON 文件
- 新依赖（如 `cpca`、`python-stdnum`、`faker`）
- 新的 `privacyguard.detection` 子包

打包后出现：
1. **`ModuleNotFoundError: No module named 'cpca'`**：未在 spec 的 `hiddenimports` 里声明
2. **`FileNotFoundError: province.json`**：数据文件未在 `datas` 里 `collect_data_files`
3. **`resource_path` 返回路径在 dev 和 frozen 不一致**：dev 下走 `os.path.abspath(".")`，frozen 下走 `sys._MEIPASS`，写错一处两个环境都崩
4. **PyInstaller 5.x 对 numpy 子包 `numpy._core._exceptions` 处理改变**：类似历史上 `privacyguard.utils.security` 导入失败（参考 `cp30` checkpoint）

**How to avoid:**
```python
# privacyguard/utils/resource.py —— 唯一允许的资源读取入口
import sys, os
def resource_path(rel: str) -> str:
    base = getattr(sys, '_MEIPASS', None)
    if base:
        return os.path.join(base, rel)
    # dev: 相对包根目录
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(pkg_root, rel)

# spec 文件里必须
# datas=[('privacyguard/data/provinces.json', 'privacyguard/data')],
# hiddenimports=['cpca', 'numpy._core._exceptions', 'privacyguard.detection.*'],
```

打包门禁：
- 在 `packaging/windows/scripts/build_complete.bat` 之后**真机启动一次**应用 + 跑一遍识别引擎
- 不能只信 `compileall` 通过
- README 警告："如果新加 `privacyguard/*` 子模块后 dev 环境 OK 但 frozen 启动失败，先检查 spec 的 hiddenimports"

**Warning signs:**
- 新模块引入后 `compileall` 通过但 dev 启动报 `ModuleNotFoundError`
- `frozen` 启动报 `FileNotFoundError: privacyguard/data/...`
- 用户只跑 `python3 main.py` 从未测过打包产物

**Phase to address:**
- **打包门禁阶段**：本轮新增的所有依赖、数据文件、子模块在合并到 main 之前必须经过 Windows + macOS 双平台打包验证（参考 `cp30` 历史教训）

---

### Pitfall 10: 大文档扫描阻塞 Qt 主线程 + ReDoS 雪崩

**What goes wrong:**
1. **UI 卡死**：用户拖入 500 页 PDF 或 50 sheet Excel，PII 引擎在主线程同步跑正则 → Qt 事件循环阻塞 → 窗口冻结 → 用户强杀
2. **正则灾难性回溯（ReDoS）**：
   - 经典陷阱 `(a+)+$` 配合 `aaaaaaaaaaaaaaaaab` 在某些 NFA 引擎上指数级爆炸
   - 中文 PII 规则里看似无害的 `\d{0,18}` + 多个分支 + 嵌套量词会复合成二次项
   - Python `re` 3.11+ 支持 `re.compile(pattern, flags=re.ASCII)` + `match(pattern, string, timeout=1.0)`，但仍需主动写
3. **OCR 与识别复合耗时**：先 OCR 全文（每页 2-5 秒）再正则扫描 → 扫描成了二次代价

**How to avoid:**
```python
# 1. 强制 worker 线程模型（已存在 OCRWorker，新加 PiiWorker）
class PiiWorker(QThread):
    finished = pyqtSignal(list)  # 命中列表
    progress = pyqtSignal(int, int)  # page/total
    def run(self):
        for i, page_text in enumerate(pages):
            hits = scan_page_with_timeout(page_text, timeout_ms=500)
            self.progress.emit(i+1, len(pages))

def scan_page_with_timeout(text: str, timeout_ms: int = 500) -> List[Hit]:
    """每个正则带超时；超时则跳过该规则但继续"""
    hits = []
    for rule in rules:
        try:
            # Python 3.11+ 才支持 timeout
            for m in re.finditer(rule.pattern, text, timeout=timeout_ms/1000):
                hits.append(m)
        except TimeoutError:
            log.warn(f"rule {rule.name} timeout on {len(text)} chars")
    return hits
```

**Warning signs:**
- 引擎函数签名是 `def scan(document): -> List[Hit]` 同步返回（必须改为 worker）
- 正则出现 `\d*`、嵌套量词 `(a|b)+c?`、`.*` 贪婪 + 后续长量词
- 单条规则未带 `timeout` 参数

**Phase to address:**
- **PII 引擎基础阶段**：所有扫描函数必须在 worker 里跑；正则编译表带 `timeout`
- **性能验证阶段**：用 500 页 + 100 sheet 文档做 smoke test，UI 不卡死

---

### Pitfall 11: 测试语料里放真实个人数据 → 仓库变成数据泄漏源

**What goes wrong:**
开发为了"真实覆盖"随手把真实身份证/手机号放进 `tests/samples/` 或断言字符串里，结果：
1. 仓库变成 PII 二次泄漏源（git 历史永久保留）
2. CI runner 把这些数据上传到日志/工件
3. 离职开发者本地仍有完整克隆

**How to avoid:**
```python
# tests/conftest.py
import faker
from faker.providers.person.zh_CN import Provider as ZhPersonProvider

@pytest.fixture
def fake_id_card():
    f = faker.Faker('zh_CN')
    # Faker 不会生成合法的 Luhn 校验位，所以要包一层生成+校验
    while True:
        first17 = f.numerify('##########' + '##########')[:17]
        if first17.isdigit() and first17[0] != '0':
            full = first17 + compute_checksum(first17)
            if validate_18(full):
                return full

@pytest.fixture
def fake_phone():
    f = faker.Faker('zh_CN')
    return f.numerify('1##' + '########')  # 号段内随机
```

策略：
- 真实数据**永远不进仓库**；如需回归真实文档，文档哈希化或仅在本地维护
- CI 用 Faker 生成样本断言，断言用纯结构（"必须是 18 位"）而非具体值
- `.gitignore` 加 `tests/samples/real_*.{pdf,xlsx,docx}`
- 仓库扫描工具（如 `gitleaks`）跑定期审计

**Warning signs:**
- `tests/samples/` 里有真实姓名/号码的文件
- 单元测试断言用了固定真实数据
- `git log -p tests/` 里能 grep 到 18 位身份证模式

**Phase to address:**
- **PII 引擎基础阶段**：建立 `tests/fixtures/fake_pii.py`，所有测试只走假数据
- **仓库治理阶段**：CI 增加 `gitleaks` 或 `trufflehog` 扫描

---

### Pitfall 12: 上下文型实体（姓名/机构/地址）识别缺乏锚点 → 大量假阳性

**What goes wrong:**
号码类有强校验位能兜底，但姓名/机构/地址**没有固定字符格式**——如果用纯正则 `[一-龥]{2,4}` 匹配"姓名"，会误命中：
- `昨日`、`今天`、`会议`、`制度`、`通知`、`国家`、`北京市`
- 所有 2-4 字中文短语

更糟的是**置信度无法量化**——没有"真姓名/假姓名"的二元判断标准，引擎只能输出"看起来像"，需要用户逐一确认。

**How to avoid:**
- **关键词锚点上下文**：姓名往往伴随 `先生/女士/同志/老师/经理/主任`；机构伴随 `有限公司/股份有限公司/集团/银行/医院/学校/委员会`；地址伴随 `省/市/区/县/路/街/号/室`
- **内置词典 + 双向扫描**：
  - 维护常用姓氏库（百家姓 + 常见复姓）、机构类型库（公司后缀）、行政区划库
  - 从文档上下文中**反向**构建"本地词典"（如果同一文档里出现了 `张先生` `张女士` `张总`，那后面单独的 `张` 也大概率是人名）
- **列级智能升级的扩展应用**：在表格里，"姓名""机构名称""地址"这类表头单元格提供了**列约束**——这一列的所有值都按"实体类型 X"扫
- **分级处置**：纯词典命中 = 低置信度（标"待确认"）；词典 + 上下文 = 中；词典 + 上下文 + 跨文档频次 = 高

**Warning signs:**
- 命中数远大于用户预期（"100 页报告找出 5000 个姓名"）
- 没有"上下文窗口"概念
- 词典是裸字符串列表，没有按行业/地域分类

**Phase to address:**
- **上下文型识别阶段**：必须在号码类识别通过后再做，依赖号码阶段产出的"已脱敏 anchor"作为种子
- **可扩展性阶段**：用户自定义词典的导入/导出格式必须明确，避免"装了 1MB 词典后引擎变慢 10 倍"

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| 用同一套正则扫所有格式 | 开发快 2-3 天 | PDF 文本层 / Word OOXML / Excel cell 文本提取差异巨大，跨格式错位 | 永远不 |
| 在 `main.py` 写 PII 识别逻辑 | 短期可见可调 | 重复实现回潮，违反 v37.7.6 收敛原则 | 永远不 |
| 把词典放代码里（硬编码 dict） | 不用打包数据文件 | 词典更新需要重装，无法用户自定义 | 仅 MVP 演示 |
| 默认全量脱敏不暴露"待确认" | 用户体验简单 | 假阳性雪崩，用户失去信任 | 永远不 |
| 不做跨文档实体一致性 | 实现简单 | 同实体不同文档掩码不一致可拼接还原 | 永远不 |
| 不做 PyInstaller 真机验证 | CI 通过 | 打包产物启动失败，到用户机器才暴露 | 永远不 |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **RapidOCR** | 拿 `.text` 字段直接识别 PII | 必须拿 `.chars`/`.confidence` 做加权校验，OCR conf < 0.7 的字符标 ambiguous |
| **PyMuPDF redact** | 调用 `add_redact_annot` 后没调 `apply_redactions` | 两个 API 必须成对出现；最好封装 `Redactor.redact_pdf(page, hits)` 单一入口 |
| **openpyxl** | 用 `data_only=True` 拿计算结果 | `data_only` 只能拿**已缓存**的值；公式引用了别的工作表/外部链接时仍漏；需访问 `wb.defined_names` 和 `external_links` 单独处理 |
| **python-docx** | 只 `paragraph.text` 取文本 | 表格 cell、文本框、页眉页脚、批注气泡、修订标记 `<w:ins>`/`<w:del>` 全部漏；需遍历 `document.element.body` 全文 |
| **mammoth (Word → HTML)** | 把 HTML 当纯文本再正则 | HTML 里 `<strong>` `<em>` `<a>` 拆分会破坏实体跨边界识别；需要解析 HTML AST |
| **PyInstaller** | `datas=[('file.json', '.')]` | 路径写错就 FileNotFoundError；应统一 `resource_path` 入口并在 spec 里 `collect_data_files('privacyguard.data')` |
| **faker** | 直接 `Faker().ssn()` 当断言 | faker 的 ssn 不会过 Luhn 校验；身份证这种**有格式校验**的必须包一层"生成+校验"循环 |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| 大文档（>200 页 PDF）同步扫描 | Qt 主线程卡死 | PiiWorker 异步 + 进度信号 | >50 页用户能感知 |
| ReDoS 正则无 timeout | 某个规则跑 30 秒 | 每条正则带 `timeout=0.5s`；超时则跳过该规则 | 任意含恶意长字符串的输入 |
| 词典全量加载到内存 | 启动慢 2-5 秒，内存 +50MB | 词典按需加载（首次使用时再加载子集）；Aho-Corasick 多模式匹配替代 N 个正则 | 词典 >10MB |
| OCR + 识别二次扫描 | 每页 2 次过文本 | 识别引擎直接消费 OCR 中间结果，跳过 `get_text()` 反序列化 | 大 PDF 严重拖慢 |
| 全 Excel 工作簿扫描 | 50 sheet × 100K 行 → 几小时 | 仅扫用户指定 sheet 范围；或先做"列头识别"再扫列 | >10 sheet |
| 同一文本重复跑 N 条正则 | N 条规则 × M 个文档 | 用 `regex.compile` 预编译 + `re.Scanner` 或 Aho-Corasick 单遍扫描 | >5 条规则 |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| 把脱敏后的原文日志打印到 stdout | 应用崩溃时日志可能被用户发到 GitHub issue，包含敏感信息 | 日志分级（DEBUG 才打印）+ 自动 scrub 字段（手机/身份证/银行卡正则替换为 `[REDACTED]`） |
| 把识别引擎的"待确认列表"序列化到 `config.json` | 配置文件可能被分享，云同步泄露 | 待确认列表只在内存/会话级，不持久化 |
| 临时目录里保留原始文档备份 | 临时目录被扫描工具扫描到 | `tempfile.TemporaryDirectory` 用完即删；额外加 `shutil.rmtree(..., ignore_errors=True)` in finally |
| PyInstaller 打包时 `--key=...` 试图加密字节码 | 反编译仍可还原（PyInstaller 本身不加密）；用户被虚假安全感误导 | 明确文档"打包产物可被逆向"，不做虚假承诺 |
| 词典文件未签名就加载 | 恶意用户替换词典植入匹配规则 | 词典文件 HMAC 签名 + 启动时校验；用户自定义词典走单独目录 |
| 输出文件名带原文件名 hash | 输出文件名也是信息泄露（攻击者知道输入是谁的） | 输出文件名固定为 `<原名>_redacted.<ext>`，或 UUID |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 一次性把全文档命中列表弹出 | 100+ 项无法逐项审查 | 分页 + 按来源筛选 (`rule / ocr / manual`) + 按实体类型筛选 |
| "高置信度直接脱敏"无 undo | 误伤无法恢复 | 所有自动脱敏可"撤销到上次手动状态"，提供 30 天本地备份 |
| 部分掩码格式不直观 | 用户看到 `110101********811` 不知道这是什么 | 部分掩码可在原位置 hover 显示"身份证号（已部分掩码）" |
| 批量脱敏每个文件单独确认 | 100 文件要确认 100 次 | 提供"全选/全不选/按置信度区间"快捷操作 |
| Excel 列级升级弹窗确认 | 用户每次拖入 Excel 都被问 | 提供"记住本次选择"开关，下次同列头自动应用 |
| 识别引擎升级后旧规则失效 | 老用户自定义规则突然不工作 | 引擎版本号 + 规则 schema 版本号；升级时做规则迁移 |
| 性能/精度参数藏太深 | 普通用户不知道有"高召回/高准确率"模式 | 在主面板露出"灵敏度"三档滑块（保守/平衡/激进） |

## "Looks Done But Isn't" Checklist

- [ ] **PDF 脱敏：** 跑过 `pdftotext` 反向提取测试 → 验证已脱敏区域原文不存在
- [ ] **Word 脱敏：** 用 `unzip -p file.docx word/document.xml | grep "<w:t>原值</w:t>"` 检查字符串已物理删除
- [ ] **Excel 脱敏：** 7-Zip 打开 xlsx → 检查 `docProps/custom.xml`、`pivotCacheRecords.xml`、`revisions/`、`sharedStrings.xml`、所有 hidden sheet 是否仍有原始数据
- [ ] **图片脱敏：** `exiftool` 验证 GPS/MakerNote/serial number 已清；像素级抽查脱敏区域为不可还原邻域
- [ ] **OCR 后处理：** 用 RapidOCR 跑真实扫描件 → 抽查含身份证/手机号图片 → 验证识别 + 校验位通过
- [ ] **跨边界匹配：** 准备一份"身份证跨行"的发票样本 → 验证引擎能拼接还原并识别
- [ ] **部分掩码一致性：** 同一文档同一身份证多次出现 → 验证掩码字符串完全一致
- [ ] **PyInstaller 打包：** Windows 真机启动 + 跑完整 PII 引擎一遍 + Excel 列级升级一遍 + 打包文档无 FileNotFoundError
- [ ] **ReDoS 防护：** 用 `regexploit` 或自构造 `a` * 50 输入跑全套规则 → 验证无超时
- [ ] **测试语料无真实 PII：** `gitleaks`/`trufflehog` 跑一遍仓库 → 0 命中
- [ ] **号码号段时效：** 抽查 `199XXXXXXXX`、`192XXXXXXXX` 真实样本 → 验证可识别
- [ ] **上下文型实体：** 抽查 `张先生`、`北京市朝阳区` 这种带锚点样本 → 验证命中且置信度 >0.7

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| 发现 PDF 假脱敏 | HIGH | 重写 Redactor → 全量回测 → 用户公开致歉并提供重脱敏工具 |
| Excel 共享字符串/属性残留 PII | MEDIUM | 改写扫描逻辑覆盖 ZIP 内所有 XML → 单元测试覆盖所有 11 通道 |
| 身份证校验算法错 | LOW | 修 `validate_18` → 用 ≥ 20 条样本断言（含 X/边界/历史）→ 灰度发布 |
| ReDoS 致 UI 卡死 | MEDIUM | 给所有正则加 timeout → 引入 Aho-Corasick → 性能基准测试 |
| 测试集出现真实 PII | HIGH | `git filter-branch` 或 BFG 重写历史 → 强制 `gitleaks` 接入 CI → 重新发布 |
| 上下文型识别假阳性雪崩 | MEDIUM | 降低默认阈值 + 强制要求锚点 + 增加"全文档命中率上限"告警 |
| PyInstaller 模块导入失败 | MEDIUM | 检查 spec `hiddenimports` + `collect_data_files` → Windows + macOS 双真机验证 |
| 跨文档关联攻击被利用 | CRITICAL | 立即通知用户 → 提供重脱敏 → 加固一致性 + 加 BIN/区划混淆层 |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1 假脱敏 (PDF/Word/Excel/Image) | PII 引擎基础 + 格式扩展 (各格式一阶段) | 每格式实现"reverse-test"：脱敏 → 提取 → 断言原文不存在 |
| 2 Excel 11 通道漏扫 | Excel 格式接入 | 7-Zip 解包全工作簿扫描；CI 加 "xlsx 通道完整性" 单元测试 |
| 3 身份证校验位错 | 号码类识别 (PII 第一阶段) | ≥ 20 断言样本（含 X、15/18 位、边界生日）；mutmut 突变测试 |
| 4 手机号段漏判 | 号码类识别 | Faker 生成覆盖所有号段样本 → 验证可识别 |
| 5 Luhn 假阳性 | 号码类识别 | 维护订单号/产品号对抗样本集 → 验证不被误杀 |
| 6 全角/OCR 字符混淆 | 号码类识别 + OCR 后处理 | 真实扫描件回归集；ambiguous 通道单独断言 |
| 7 跨边界漏判 | PII 引擎设计 (在第一阶段就考虑) | 跨行身份证 + 跨 cell 银行卡 + 跨页手机号 各 ≥ 3 样本 |
| 8 部分掩码不一致 | 部分掩码阶段 | 单元测试断言"同一实体多实例掩码字节相等" |
| 9 PyInstaller 数据文件/导入 | 打包门禁 (本轮每阶段收尾时跑) | Windows + macOS 真机启动 + 跑识别引擎 + 跑打包文档 |
| 10 ReDoS + UI 卡死 | PII 引擎基础 | `regexploit` CI 扫描 + 大文档 smoke test 不卡死 |
| 11 测试集真实 PII | PII 引擎基础 | `gitleaks` CI 接入 + `tests/fixtures/fake_pii.py` 全覆盖 |
| 12 上下文型假阳性 | 上下文型识别 (PII 第二阶段) | 锚点强制 + 命中率上限告警 + 用户自定义词典 schema |

## Sources

- PyMuPDF 官方文档 — `add_redaction` / `apply_redactions(keep_text=False)` 的真删除语义
- GitHub `pymupdf/PyMuPDF` issues #3257、#3863、#3375 — `apply_redactions` 行为边界
- `frogcmj/ChineseIDValidator` — 18 位 mod11 算法权威实现
- `gangannini` CSDN 博客 — 身份证校验位权重 + parity 表权威复述
- `telphone.cn/prefix/`、`blog.csdn.net/flyweak` — 中国手机号段分配完整历史
- 工信部 2017-08 号段核发公告（166/198/199）、2019-12 5G 号段（190/192/196/197）
- `lib.cnblogs.com/yumingzhao/p/10149017.html` — 标准 18 位校验位算法
- Wang et al., IEEE TrustCom 2023 — 部分掩码 PII 在 CDR 数据上的重识别风险
- OWASP ReDoS Guide、`fset.in` Catastrophic Backtracking — ReDoS 防御
- `docs.python.org/3/library/re.html` — Python 3.11+ `re` timeout 参数
- Semgrep 博客 — ReDoS 检测与防御
- Microsoft Office — "Remove personal info from workbook" 官方流程
- `support.microsoft.com/en-us/office/remove-personal-info-from-workbook`
- StackOverflow `58555732` — openpyxl 移除 custom properties 需 ZIP 层操作
- `exceldemy.com/excel-hidden-data-leak` — Excel 11 隐藏数据通道列表
- Pillow 7.0+ 默认 strip EXIF；`piexif` 库 GPS 选择性清除
- Faker 库（`zh_CN` locale）— 假数据生成基础，但**需要包一层 Luhn 校验**才能生成合法假身份证
- `cpca` Python 库（chinese_province_city_area_mapper）— 行政区划词典 + 锚点提取

---
*Pitfalls research for: 中文 PII 自动识别引擎 + Excel/图片脱敏扩展*
*Researched: 2026-08-10*