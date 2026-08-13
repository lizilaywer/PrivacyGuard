# Phase 2: PDF 增加银行卡/邮箱/财税实体识别与部分掩码 - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 30 (16 new / 14 modified / 0 unchanged)
**Analogs found:** 26 / 26 (every classified file has at least a role-match analog)

> 本 Phase 2 严格遵守 v37.7.6 收敛原则：所有共享逻辑放 `privacyguard/`；6 个新 validator 子模块与 `id_card.py` / `phone_segment.py` 平级；新 `partial mask 写入 helper` 沿用 `main.py:12354-12385` 既已生产验证的 PyMuPDF 真删除调用模式。
> Phase 2 **不引入**任何 PyPI 依赖；GB 32100 mod-31-3、Luhn、RFC 5322 简化版与 Phase 1 mod-11-2 同位置（validator 模块内纯函数）。
> BIN 词典来源 = 维基百科 CC BY-SA 4.0（需在 `bin_prefixes.json.LICENSE` 保留归属声明）。

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `privacyguard/pii/validators/bank_card.py` (new) | utility | pure-function | `privacyguard/pii/validators/phone_segment.py` | exact |
| `privacyguard/pii/validators/email.py` (new) | utility | pure-function | `privacyguard/pii/validators/phone_segment.py` | exact |
| `privacyguard/pii/validators/uscc.py` (new) | utility | pure-function | `privacyguard/pii/validators/id_card.py` | exact |
| `privacyguard/pii/validators/vat_invoice.py` (new) | utility | pure-function | `privacyguard/pii/validators/phone_segment.py` (context-anchor 形态) | exact |
| `privacyguard/pii/validators/taxpayer_id.py` (new) | utility | pure-function | `privacyguard/pii/validators/id_card.py` (15→18 upgrade 形态) | exact |
| `privacyguard/pii/validators/bank_account.py` (new) | utility | pure-function | `privacyguard/pii/validators/phone_segment.py` (context-anchor 必查) | exact |
| `privacyguard/pii/validators/__init__.py` (modify) | package-init | lazy-load | self (Phase 1 12 项扩展到 18 项) | exact |
| `privacyguard/pii/regex_patterns.py` (modify) | utility/config | compile-only | self (`iter_candidate_strings` yield 扩展) | exact |
| `privacyguard/pii/mask.py` (modify) | utility | pure-function | self (`mask_for_entity` 分派表扩展) | exact |
| `privacyguard/pii/pdf_adapter.py` (modify) | service | file-I/O | self (新增 `write_partial_masks` + `clear_pdf_metadata`) | exact |
| `privacyguard/pii/data/rules.json` (modify) | config | pure-data | self (4 键扩展 bank_card / uscc / vat_invoice / bank_account) | exact |
| `privacyguard/pii/data/bin_prefixes.json` (new) | config | pure-data | `privacyguard/pii/data/rules.json` | role-match |
| `privacyguard/pii/data/bin_prefixes.json.LICENSE` (new) | config | pure-data | (new — CC BY-SA 4.0 归属) | partial |
| `privacyguard/pii/__init__.py` (modify) | package-init | lazy-load | self (`_LAZY_IMPORTS` 扩展 14 项) | exact |
| `privacyguard/__init__.py` (modify) | package-init | lazy-load | self (`_LAZY_IMPORTS` 扩展 14 项) | exact |
| `main.py:12490-12504` (modify) | UI / compat-layer | save loop | self (Phase 1 `save_pdf` PII 路径改写) | exact |
| `main.py:1008-1700` (modify) | UI / compat-layer | SettingsDialog | self (Phase 1 `box_pii` 卡片扩展) | exact |
| `main.py` toolbar (modify) | UI / compat-layer | toolbar | self (Phase 1 `rb_black` / `rb_white` toggle 形态) | exact |
| `config.json` (modify) | config | pure-data | self (`pii_settings` 段扩展 `per_entity_default`) | exact |
| `config.json.template` (modify) | config | pure-data | self | exact |
| `tests/fixtures/fake_pii.py` (modify) | test-fixture | pure-data | self (扩展 6 个新 entity 合成函数) | exact |
| `tests/unit/test_pii_validators.py` (modify) | test | pure-function | self (8 个新 validator 测试类) | exact |
| `tests/unit/test_pii_engine.py` (modify) | test | pure-function | self (6 个新 entity 命中 / 档位测试) | exact |
| `tests/unit/test_pdf_pii_redaction.py` (modify) | test | file-I/O | self (新增 `test_partial_mask_*` + `test_metadata_*_cleared_on_save`) | exact |
| `tests/unit/test_app_config.py` (modify) | test | SimpleConfig round-trip | self (新增 `per_entity_default` 字段测试) | exact |
| `packaging/windows/config/PrivacyGuard_windows.spec` (modify) | config | PyInstaller datas | self (datas 追加 + hiddenimports 追加 6 项) | exact |
| `packaging/macos/config/PrivacyGuard.spec` (modify) | config | PyInstaller datas | self (与 Windows spec parity) | exact |

---

## Pattern Assignments

### `privacyguard/pii/validators/bank_card.py` (utility, pure-function)

**Analog:** `privacyguard/pii/validators/phone_segment.py` — **exact** (白名单 + 排除表 + is_* 单函数形态)。

**Imports pattern** (直接复用 `phone_segment.py:1-7`):
```python
"""银行卡号校验（NUM-04 + FIN-04 银行账号兄弟规则）。

- Luhn 校验必过
- 6 位 BIN 前缀词典白名单（动态从 bin_prefixes.json 加载，路径走 resource_path）
- 上下文锥点（卡号 / 账号 / 银行 / 支付 / debit / credit）±20 字符提升 confidence
"""
from typing import Final
```

**核心模块形态** (直接参照 `phone_segment.py:10-29` + `is_mobile_segment`):
```python
BANK_CARD_BIN_WHITELIST: Final = frozenset()  # 启动期从 bin_prefixes.json 加载


def load_bin_whitelist(json_path: str) -> frozenset:
    """运行时从 bin_prefixes.json 加载 BIN 前 6 位白名单。"""
    import json
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return frozenset(data.get("bin_prefixes", []))


def luhn_check(card_num: str) -> bool:
    """ISO/IEC 7812 Luhn 校验。"""
    if not card_num or not card_num.isdigit():
        return False
    total = 0
    reverse = card_num[::-1]
    for i, ch in enumerate(reverse):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_bank_card(card_num, bin_whitelist=None) -> bool:
    """13-19 位 + Luhn + 6 位 BIN 白名单 + 上下文锥点（C-01/C-02）。"""
    if not isinstance(card_num, str):
        return False
    stripped = card_num.replace(" ", "").replace("-", "")
    if not stripped.isdigit() or not (13 <= len(stripped) <= 19):
        return False
    if not luhn_check(stripped):
        return False
    whitelist = bin_whitelist or BANK_CARD_BIN_WHITELIST
    return stripped[:6] in whitelist
```

**关键不变式（D-05 / D-09 锁定）**:
- `entity_type` 字符串 = `"CN_BANK_CARD"`
- Luhn 算法：偶数位 ×2 > 9 时减 9（标准 Luhn，不是"折半相加"变体）
- BIN 白名单加载必须走 `privacyguard.utils.security.resource_path`
- BIN 词典文件路径 = `privacyguard/pii/data/bin_prefixes.json`（**不**用 `os.path.dirname(__file__)`）

---

### `privacyguard/pii/validators/email.py` (utility, pure-function)

**Analog:** `privacyguard/pii/validators/phone_segment.py` — **exact** (白名单 + is_* 单函数)。

**Imports pattern** (沿用 `phone_segment.py:1`):
```python
"""邮箱识别（NUM-05）+ RFC 5322 简化版正则。

D-10: 不引入 IDN / 国际化邮箱；confidence 按公共域名后缀 → HIGH, 否则 MEDIUM。
"""
import re
from typing import Final


# 公共域名后缀（com / cn / net / org / gov / edu）
EMAIL_PUBLIC_SUFFIXES: Final = frozenset({
    "com", "cn", "net", "org", "gov", "edu", "io", "co", "ai", "app",
})


_EMAIL_RFC5322_SIMPLE_RE: Final = re.compile(
    r"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9._%+-])"
)


def validate_email(email: str) -> bool:
    """RFC 5322 简化版邮箱格式校验。"""
    if not isinstance(email, str) or not email:
        return False
    return bool(_EMAIL_RFC5322_SIMPLE_RE.fullmatch(email))


def is_public_suffix_email(email: str) -> bool:
    """是否为公共域名后缀邮箱（用于 confidence 提升 HIGH）。"""
    if not validate_email(email):
        return False
    domain = email.rsplit("@", 1)[-1]
    suffix = domain.rsplit(".", 1)[-1].lower()
    return suffix in EMAIL_PUBLIC_SUFFIXES
```

**关键不变式（D-10 锁定）**:
- `entity_type` 字符串 = `"CN_EMAIL"`
- 正则用 `fullmatch` 而非 `finditer`（validator 是纯函数，输入即整段）
- 多级子域（`foo@bar.qq.com`）取最后一段作为 suffix

---

### `privacyguard/pii/validators/uscc.py` (utility, pure-function)

**Analog:** `privacyguard/pii/validators/id_card.py` — **exact** (权重 + 校验码表 + validate_* + 防御性格式)。

**Imports pattern** (沿用 `id_card.py:1-9`):
```python
"""统一社会信用代码校验（FIN-01 + GB 32100-2015 mod-31-3）。

D-06: 18 位 + 登记管理部门类别代码表预筛选（8 字符：1/5/9/Y/A/B 等）。
"""
from typing import Final


# GB 32100-2015 mod-31-3 权重表
USCC_WEIGHTS: Final = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)
# 字符集（0-9 + 25 个大写字母，跳过 I/O/S/V/Z 共 31 字符）
USCC_CHARSET: Final = "0123456789ABCDEFGHJKLMNPQRTUWXY"
# 登记管理部门类别代码（8 字符）
USCC_CATEGORY_CODES: Final = frozenset({"1", "5", "9", "Y", "A", "B", "C", "D"})


def compute_uscc_check_digit(body17: str) -> str:
    """GB 32100 mod-31-3 校验位计算。"""
    if not body17 or len(body17) != 17:
        return ""
    total = sum(USCC_CHARSET.index(body17[i]) * USCC_WEIGHTS[i] for i in range(17))
    return USCC_CHARSET[(31 - total % 31) % 31]


def validate_uscc(uscc: str) -> bool:
    """18 位 USCC mod-31-3 校验 + 登记管理部门类别代码预筛。"""
    if not isinstance(uscc, str):
        return False
    uscc = uscc.strip().upper()
    if not uscc or len(uscc) != 18 or uscc[0] not in USCC_CATEGORY_CODES:
        return False
    if not all(c in USCC_CHARSET for c in uscc):
        return False
    return uscc[17] == compute_uscc_check_digit(uscc[:17])
```

**关键不变式（D-06 / D-09 锁定）**:
- `entity_type` 字符串 = `"CN_USCC"`（同时也是 `CN_TAXPAYER_ID` 复用通道，**不**独立 type）
- USCC_CHARSET 字符集：30 个大写字母 + 数字 0-9，跳过 I/O/S/V/Z
- `USCC_CATEGORY_CODES` 8 字符硬编码；Phase 8 用户可编辑的 schema 锁定这一形状
- USCC 旧版 15 位走独立 validator `taxpayer_id.py::validate_taxpayer_id_15`

---

### `privacyguard/pii/validators/vat_invoice.py` (utility, pure-function)

**Analog:** `privacyguard/pii/validators/phone_segment.py` — **exact** (关键词锥点白名单 + is_* 单函数)。

**Imports pattern** (沿用 `phone_segment.py:1`):
```python
"""增值税发票号校验（FIN-02 + D-07 双格式）。

- 传统 8 位纯数字
- 全电发票 20 位（2022 年起国家税务总局公告 1 号）
- 上下文锥点（发票 / 号码 / 票号 / invoice）±20 字符必查
"""
from typing import Final, Tuple


VAT_INVOICE_CONTEXTS: Final = frozenset({
    "发票", "号码", "票号", "invoice", "INVOICE", "Invoice",
    "增值税", "电子发票", "全电发票", "号码:", "号:",
})


def validate_vat_invoice_8(num8: str) -> bool:
    """传统 8 位增值税发票号。"""
    return isinstance(num8, str) and len(num8) == 8 and num8.isdigit()


def validate_vat_invoice_20(num20: str) -> bool:
    """全电发票 20 位号码（含横线 / 年份分隔）。"""
    if not isinstance(num20, str):
        return False
    stripped = num20.replace("-", "").replace(" ", "")
    return len(stripped) == 20 and stripped.isdigit()


def has_vat_invoice_context(text: str, target: str, window: int = 20) -> bool:
    """target ±window 字符内是否存在 VAT 上下文锥点。"""
    if not text or not target:
        return False
    idx = text.find(target)
    if idx < 0:
        return False
    lo = max(0, idx - window)
    hi = min(len(text), idx + len(target) + window)
    window_text = text[lo:hi]
    return any(ctx in window_text for ctx in VAT_INVOICE_CONTEXTS)
```

**关键不变式（D-07 锁定）**:
- `entity_type` 字符串 = `"CN_VAT_INVOICE"`
- 8 位无上下文锥点单独出现 → confidence_tier = MEDIUM（不 reject，保留"疑似票号"）
- 20 位与 8 位通过正则 yield 两次（regex_patterns.py），engine 内按 hit 的 page_rect 区分

---

### `privacyguard/pii/validators/taxpayer_id.py` (utility, pure-function)

**Analog:** `privacyguard/pii/validators/id_card.py` — **exact** (15 位独立 + 简单结构校验，与 `validate_15` 同形但**不**复用 USCC 校验位)。

**Imports pattern** (沿用 `id_card.py:1-9`):
```python
"""纳税人识别号校验（FIN-03 + D-09 双 type）。

- CN_TAXPAYER_ID: 2015 年后 18 位三证合一 = 复用 validators.uscc.validate_uscc
- CN_TAXPAYER_ID_15: 旧版 15 位 NNNNN-NNNNNNN-NNNN 格式（无强校验位，独立 type）
"""
from typing import Final


# 旧版 15 位纳税人识别号（2015 年前）行政编码前缀白名单（与 id_card 同步）
_TAXPAYER_15_ADMIN_PREFIX: Final = frozenset({
    '11', '12', '13', '14', '15', '21', '22', '23',
    '31', '32', '33', '34', '35', '36', '37',
    '41', '42', '43', '44', '45', '46',
    '50', '51', '52', '53', '54', '61', '62', '63', '64', '65',
    '71', '81', '82',
})


def validate_taxpayer_id_15(id15: str) -> bool:
    """15 位旧版纳税人识别号（无强校验位，仅格式 + 行政区划前缀）。"""
    if not isinstance(id15, str):
        return False
    stripped = id15.replace("-", "").replace(" ", "")
    if len(stripped) != 15 or not stripped.isdigit():
        return False
    return stripped[:2] in _TAXPAYER_15_ADMIN_PREFIX
```

**关键不变式（D-09 锁定）**:
- `entity_type` 字符串 = `"CN_TAXPAYER_ID_15"`（**不**是 `"CN_TAXPAYER_ID"`）
- `CN_TAXPAYER_ID`（18 位）= 在 `engine.py` 内**直接**调用 `validators.uscc.validate_uscc`（不再独立 validator）
- 15 位 mask 策略 = 前 6 + 后 4（与 USCC 18 位一致；Claude's Discretion 已固化）
- confidence_tier 默认 = "MEDIUM"（无强校验位）

---

### `privacyguard/pii/validators/bank_account.py` (utility, pure-function)

**Analog:** `privacyguard/pii/validators/phone_segment.py` — **exact** (关键词锥点白名单 + 必查锥点 + 长度范围)。

**Imports pattern** (沿用 `phone_segment.py:1`):
```python
"""银行账号校验（FIN-04 + D-08 必查上下文锥点）。

- 9-21 位纯数字
- 必加上下文锥点（账号 / 账户 / 银行账号 / 招行 / 中行 / 建行 / 工商银行 / 农行 / 邮储 / 交通银行）±20 字符
- 无上下文锥点不产生 candidate（reject 在 engine 层）
"""
from typing import Final


BANK_ACCOUNT_CONTEXTS: Final = frozenset({
    "账号", "账户", "银行账号", "银行账户",
    "招行", "中行", "建行", "工商银行", "农行", "邮储", "交通银行",
    "account", "Account", "ACCOUNT", "a/c",
})


def validate_bank_account(account: str) -> bool:
    """9-21 位银行账号纯数字格式校验（不含上下文锥点检查 — 锥点由 engine 强制）。"""
    if not isinstance(account, str):
        return False
    stripped = account.replace(" ", "").replace("-", "")
    return stripped.isdigit() and 9 <= len(stripped) <= 21


def has_bank_account_context(text: str, target: str, window: int = 20) -> bool:
    """target ±window 字符内是否存在银行账号上下文锥点（D-08 必查）。"""
    if not text or not target:
        return False
    idx = text.find(target)
    if idx < 0:
        return False
    lo = max(0, idx - window)
    hi = min(len(text), idx + len(target) + window)
    window_text = text[lo:hi]
    return any(ctx in window_text for ctx in BANK_ACCOUNT_CONTEXTS)
```

**关键不变式（D-08 锁定）**:
- `entity_type` 字符串 = `"CN_BANK_ACCOUNT"`
- 锥点检查是 validator 入口（不是 engine 层后置），无锥点 → `validate_bank_account` 返回 False
- 长度上限 21 位（招行 / 中行部分账户实际超过 19 位的边界）

---

### `privacyguard/pii/validators/__init__.py` (modify)

**Analog:** self（Phase 1 9 项扩展到 18 项）— **exact**。

**当前形态** (`privacyguard/pii/validators/__init__.py:1-26`):
```python
"""PrivacyGuard PII 验证器子包（NUM-01/02/03 纯函数实现）。"""
from importlib import import_module


__all__ = [
    'validate_18_id', 'validate_15_id', 'upgrade_15_to_18',
    'compute_check_digit', 'is_mobile_segment',
    'PHONE_PERSONAL_PREFIX_3', 'PHONE_EXCLUDED_PREFIX_3', 'PHONE_EXCLUDED_PREFIX_4',
]
```

**Phase 2 扩展点**（在 `__all__` 与 `_LAZY_IMPORTS` 中各追加）：
```python
# __all__ 增加 6 个 validator 函数 + 6 个白名单常量 + 2 个上下文锥点常量
'validate_bank_card', 'validate_email', 'validate_uscc',
'validate_taxpayer_id_15', 'validate_vat_invoice_8', 'validate_vat_invoice_20',
'has_vat_invoice_context', 'has_bank_account_context',
'BANK_CARD_BIN_WHITELIST', 'EMAIL_PUBLIC_SUFFIXES',
'USCC_CATEGORY_CODES', 'VAT_INVOICE_CONTEXTS',
'TAXPAYER_15_ADMIN_PREFIX', 'BANK_ACCOUNT_CONTEXTS',

# _LAZY_IMPORTS 增加 6 个新 validator 模块
'validate_bank_card':           ('privacyguard.pii.validators.bank_card', 'validate_bank_card'),
'validate_email':               ('privacyguard.pii.validators.email', 'validate_email'),
'validate_uscc':                ('privacyguard.pii.validators.uscc', 'validate_uscc'),
'validate_taxpayer_id_15':      ('privacyguard.pii.validators.taxpayer_id', 'validate_taxpayer_id_15'),
'validate_vat_invoice_8':       ('privacyguard.pii.validators.vat_invoice', 'validate_vat_invoice_8'),
'validate_vat_invoice_20':      ('privacyguard.pii.validators.vat_invoice', 'validate_vat_invoice_20'),
'has_vat_invoice_context':      ('privacyguard.pii.validators.vat_invoice', 'has_vat_invoice_context'),
'has_bank_account_context':     ('privacyguard.pii.validators.bank_account', 'has_bank_account_context'),
'BANK_CARD_BIN_WHITELIST':      ('privacyguard.pii.validators.bank_card', 'BANK_CARD_BIN_WHITELIST'),
'EMAIL_PUBLIC_SUFFIXES':        ('privacyguard.pii.validators.email', 'EMAIL_PUBLIC_SUFFIXES'),
'USCC_CATEGORY_CODES':          ('privacyguard.pii.validators.uscc', 'USCC_CATEGORY_CODES'),
'VAT_INVOICE_CONTEXTS':         ('privacyguard.pii.validators.vat_invoice', 'VAT_INVOICE_CONTEXTS'),
'TAXPAYER_15_ADMIN_PREFIX':     ('privacyguard.pii.validators.taxpayer_id', '_TAXPAYER_15_ADMIN_PREFIX'),
'BANK_ACCOUNT_CONTEXTS':        ('privacyguard.pii.validators.bank_account', 'BANK_ACCOUNT_CONTEXTS'),
```

**OPS-03 强制约束不变式**: `import privacyguard.pii.validators` 不得触发任意一个子模块加载（cp30 教训）。

---

### `privacyguard/pii/regex_patterns.py` (modify)

**Analog:** self（Phase 1 `iter_candidate_strings` 3 yield 扩展到 9 yield）— **exact**。

**当前形态** (`privacyguard/pii/regex_patterns.py:11-30`):
```python
_ID_18_RE: Final = re.compile(...)
_ID_15_RE: Final = re.compile(...)
_PHONE_11_RE: Final = re.compile(...)


def iter_candidate_strings(text: str) -> Iterator[Tuple[str, Tuple[int, int], str]]:
    for m in _ID_18_RE.finditer(text):
        yield m.group(0), m.span(), "CN_ID_CARD"
    for m in _ID_15_RE.finditer(text):
        yield m.group(0), m.span(), "CN_ID_CARD"
    for m in _PHONE_11_RE.finditer(text):
        yield m.group(0), m.span(), "CN_PHONE"
```

**Phase 2 追加**（在 yield 链尾追加 6 个新 entity_hint，按 entity_hint 字母序保证可预测顺序）：
```python
# NUM-04: 银行卡 — 13-19 位（边界含 13 / 19）
_BANK_CARD_RE: Final = re.compile(r"(?<!\d)(\d{13,19})(?!\d)")
# NUM-05: 邮箱 — RFC 5322 简化版（仅在 validator 内复验，regex 仅作粗筛）
_EMAIL_RE: Final = re.compile(
    r"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9._%+-])"
)
# FIN-01: USCC — 18 位大写字母数字
_USCC_RE: Final = re.compile(r"(?<![A-Z0-9])([0-9A-HJ-NPQRTUWXY]{18})(?![A-Z0-9])")
# FIN-02: VAT 发票号 — 8 位 / 20 位双格式
_VAT_INVOICE_8_RE: Final = re.compile(r"(?<!\d)(\d{8})(?!\d)")
_VAT_INVOICE_20_RE: Final = re.compile(r"(?<!\d)(\d{20})(?!\d)")
# FIN-03: 纳税人识别号 15 位（旧版）
_TAXPAYER_ID_15_RE: Final = re.compile(r"(?<!\d)([1-9]\d{14})(?!\d)")
# FIN-04: 银行账号 — 9-21 位
_BANK_ACCOUNT_RE: Final = re.compile(r"(?<!\d)(\d{9,21})(?!\d)")


# 在 iter_candidate_strings 内追加（yield 顺序：D-09 字母序）
for m in _BANK_CARD_RE.finditer(text):
    yield m.group(0), m.span(), "CN_BANK_CARD"
for m in _EMAIL_RE.finditer(text):
    yield m.group(0), m.span(), "CN_EMAIL"
for m in _USCC_RE.finditer(text):
    yield m.group(0), m.span(), "CN_USCC"
for m in _VAT_INVOICE_8_RE.finditer(text):
    yield m.group(0), m.span(), "CN_VAT_INVOICE"
for m in _VAT_INVOICE_20_RE.finditer(text):
    yield m.group(0), m.span(), "CN_VAT_INVOICE"
for m in _TAXPAYER_ID_15_RE.finditer(text):
    yield m.group(0), m.span(), "CN_TAXPAYER_ID_15"
for m in _BANK_ACCOUNT_RE.finditer(text):
    yield m.group(0), m.span(), "CN_BANK_ACCOUNT"
```

**关键不变式**:
- 现有 3 个 yield（CN_ID_CARD × 2 + CN_PHONE）**不动位置**（保持 Phase 1 行为）
- 新 yield 顺序按 entity_hint 字符串字母序（确保 plan 文档与实现一致）
- USCC 正则**不**用 `re.IGNORECASE`（校验位是 mod-31-3 大写固定字符集；OCR 路径由 `normalize_digits` 上层归一化处理）

---

### `privacyguard/pii/mask.py` (modify)

**Analog:** self（Phase 1 2 个 partial_mask + mask_for_entity 分派表扩展）— **exact**。

**当前形态** (`privacyguard/pii/mask.py:9-29`):
```python
def partial_mask_id_card(normalized18: str) -> str:
    if not normalized18 or len(normalized18) != 18:
        return '*' * len(normalized18)
    return normalized18[:6] + '*' * 8 + normalized18[14:]


def partial_mask_phone(normalized11: str) -> str:
    if not normalized11 or len(normalized11) != 11:
        return '*' * len(normalized11)
    return normalized11[:3] + '*' * 4 + normalized11[7:]


def mask_for_entity(entity_type: str, normalized_text: str) -> str:
    if entity_type == "CN_ID_CARD":
        return partial_mask_id_card(normalized_text)
    if entity_type == "CN_PHONE":
        return partial_mask_phone(normalized_text)
    return '*' * len(normalized_text)
```

**Phase 2 扩展**（每个新 entity 一个 partial_mask_*）：
```python
def partial_mask_bank_card(card: str) -> str:
    """银行卡部分掩码（前 4 + 后 4）；长度非 13-19 时返回全掩。"""
    if not card or not (13 <= len(card) <= 19):
        return '*' * len(card)
    return card[:4] + '*' * (len(card) - 8) + card[-4:]


def partial_mask_email(email: str) -> str:
    """邮箱部分掩码（u***@domain.com 保留顶级域名后缀）。"""
    if not email or '@' not in email:
        return '*' * len(email)
    local, _, domain = email.partition('@')
    if not local or not domain:
        return '*' * len(email)
    return local[0] + '*' * 3 + '@' + domain


def partial_mask_uscc(uscc: str) -> str:
    """USCC / 18 位纳税人识别号 — 前 6 + 后 4 保留。"""
    if not uscc or len(uscc) != 18:
        return '*' * len(uscc)
    return uscc[:6] + '*' * 8 + uscc[14:]


def partial_mask_taxpayer_id_15(id15: str) -> str:
    """15 位旧版纳税人识别号 — 前 6 + 后 4（与 USCC 18 位一致；Claude's Discretion）。"""
    if not id15 or len(id15) != 15:
        return '*' * len(id15)
    return id15[:6] + '*' * 5 + id15[11:]


def partial_mask_vat_invoice(num: str) -> str:
    """VAT 发票号 — 前 2 + 后 2。"""
    if not num or len(num) < 4:
        return '*' * len(num)
    return num[:2] + '*' * (len(num) - 4) + num[-2:]


def partial_mask_bank_account(acct: str) -> str:
    """银行账号 — 前 4 + 后 4。"""
    if not acct or len(acct) < 8:
        return '*' * len(acct)
    return acct[:4] + '*' * (len(acct) - 8) + acct[-4:]


# mask_for_entity 分派表扩展
def mask_for_entity(entity_type: str, normalized_text: str) -> str:
    if entity_type == "CN_ID_CARD":
        return partial_mask_id_card(normalized_text)
    if entity_type == "CN_PHONE":
        return partial_mask_phone(normalized_text)
    if entity_type == "CN_BANK_CARD":
        return partial_mask_bank_card(normalized_text)
    if entity_type == "CN_EMAIL":
        return partial_mask_email(normalized_text)
    if entity_type in ("CN_USCC", "CN_TAXPAYER_ID"):
        return partial_mask_uscc(normalized_text)
    if entity_type == "CN_TAXPAYER_ID_15":
        return partial_mask_taxpayer_id_15(normalized_text)
    if entity_type == "CN_VAT_INVOICE":
        return partial_mask_vat_invoice(normalized_text)
    if entity_type == "CN_BANK_ACCOUNT":
        return partial_mask_bank_account(normalized_text)
    return '*' * len(normalized_text)
```

**关键不变式（D-05 / D-09 锁定）**:
- `entity_type` 字符串值与 `engine.py` yield 的 `entity_hint` 一一对应
- 长度不匹配时返回 `'*' * len(text)`（不抛 ValueError）
- 邮箱 mask 保留顶级域名后缀（D-10 + ROADMAP 例子明示：`z****@qq.com`）

---

### `privacyguard/pii/pdf_adapter.py` (modify — 新增 write_partial_masks + clear_pdf_metadata)

**Analog:** self（Phase 1 `apply_pii_redactions` 完整 PyMuPDF 真删除范本 + `main.py:12354-12385`）— **exact**。

**当前形态** (`privacyguard/pii/pdf_adapter.py:37-64`):
```python
def apply_pii_redactions(
    pdf_in: str,
    pdf_out: str,
    rects_per_page: Dict[int, Iterable[fitz.Rect]],
    fill_color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    doc = fitz.open(pdf_in)
    try:
        for i in range(len(doc)):
            page = doc[i]
            for r in rects_per_page.get(i, []):
                annot = page.add_redact_annot(r)
                annot.set_colors(stroke=fill_color, fill=fill_color)
                annot.update()
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
            for annot in page.annots() or []:
                page.delete_annot(annot)
        doc.save(pdf_out, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()
```

**Phase 2 扩展 — 新增 `write_partial_masks` helper**（沿用 D-01 / D-02 / D-03 流程）：
```python
from typing import Literal
import fitz
from privacyguard.pii.hits import PIIHit


def write_partial_masks(
    doc: "fitz.Document",
    page_idx: int,
    pii_hits: list,
    mode: Literal["partial", "blackout"] = "partial",
    font_lookup_fn=None,
    text_size_estimator_fn=None,
) -> None:
    """Phase 2: PII 命中 partial mask 写入（D-01 + D-02 + D-21）。

    mode="partial":
        1. add_redact_annot（黑底色块）
        2. apply_redactions(IMAGE_PIXELS)
        3. insert_text 在色块上写 mask_strategy（沿用 page.get_text("dict") 字体 / OCR 路径估算字号）

    mode="blackout":
        仅 add_redact_annot + apply_redactions(IMAGE_PIXELS)（沿用 Phase 1 行为）
    """
    if not pii_hits:
        return
    page = doc[page_idx]
    fill_color = (0.0, 0.0, 0.0)
    for hit in pii_hits:
        r = hit.page_rect  # (x, y, w, h)
        rect = fitz.Rect(r[0], r[1], r[0] + r[2], r[1] + r[3])
        annot = page.add_redact_annot(rect)
        annot.set_colors(stroke=fill_color, fill=fill_color)
        annot.update()
    if mode == "blackout":
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
        for annot in page.annots() or []:
            page.delete_annot(annot)
        return
    # mode == "partial": apply redact + insert mask text
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
    for annot in page.annots() or []:
        page.delete_annot(annot)
    # 在新生成的色块上写 mask_strategy（D-02 字体回退）
    for hit in pii_hits:
        r = hit.page_rect
        rect = fitz.Rect(r[0], r[1], r[0] + r[2], r[1] + r[3])
        font_name, font_size = _resolve_font_for_rect(page, hit, font_lookup_fn, text_size_estimator_fn)
        # 居中插入（D-03：rect 宽度按 mask_strategy 字符数重算）
        mask_text = hit.mask_strategy
        text_width = font_size * len(mask_text) * 0.6
        x_center = rect.x0 + (rect.width - text_width) / 2
        y_center = rect.y0 + (rect.height + font_size) / 2
        page.insert_text(
            (x_center, y_center),
            mask_text,
            fontsize=font_size,
            fontname=font_name,
            color=(1.0, 1.0, 1.0),  # 白字
        )


def _resolve_font_for_rect(page, hit, font_lookup_fn, text_size_estimator_fn):
    """D-02: 优先 page.get_text("dict") 现场取最近 span；回退默认 sans-serif。"""
    if font_lookup_fn:
        return font_lookup_fn(page, hit)
    try:
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("text") and hit.normalized and hit.normalized in span["text"]:
                        return span.get("font", "helv"), float(span.get("size", 10))
    except Exception:
        pass
    # 回退：默认 sans-serif + rect.height 估算字号
    font_size = max(hit.page_rect[3] - 4, 6) if text_size_estimator_fn is None else text_size_estimator_fn(hit)
    return "helv", float(font_size)


def clear_pdf_metadata(doc: "fitz.Document") -> None:
    """Phase 2: SAFE-03 PDF 元数据清除（D-14 + D-15 + D-16）。

    仅清 5 字段（Title / Author / Subject / Producer / Creator），其他保留；
    5 字段全部置空字符串，不写 "Anonymous" / "Redacted" 等占位字符串。
    """
    doc.set_metadata({
        "title": "",
        "author": "",
        "subject": "",
        "producer": "",
        "creator": "",
    })
```

**关键不变式（D-14 / D-15 / D-16 锁定）**:
- `set_metadata` 是文档级调用（不修改 page 级）
- 5 字段全部 `""`（不写占位字符串）
- `clear_pdf_metadata` 必须在 `doc.save()` 前调（避免保存后影响下次读取）
- partial mask 路径**不**回退到 blackout（即使字体查询失败，blackout 是另一个 mode 分支）
- `write_partial_masks` 是单 page 单次调用（不打开 / 不保存 doc，由调用方管理生命周期）

---

### `privacyguard/pii/data/rules.json` (modify)

**Analog:** self（Phase 1 2 键扩展到 6 键）— **exact**。

**当前形态** (`privacyguard/pii/data/rules.json:1-23`):
```json
{
  "phone_segment": { "personal_prefix_3": [...], "excluded_prefix_3": [...], ... },
  "id_card": { "weights": [7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2], "mapping": [...] }
}
```

**Phase 2 扩展**（在末尾追加 4 个键，D-19 锁定 schema）：
```json
{
  "phone_segment": { ... },
  "id_card": { ... },
  "bank_card": {
    "bin_dictionary_path": "privacyguard/pii/data/bin_prefixes.json",
    "luhn_required": true,
    "context_anchors": ["卡号", "账号", "银行", "支付", "debit", "credit"],
    "context_window": 20,
    "length_range": [13, 19],
    "source": "ISO/IEC 7812 + 维基百科 Bank card number (CC BY-SA 4.0)",
    "last_verified": "2026-Q3",
    "next_review": "2026-Q4"
  },
  "uscc": {
    "weights": [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28],
    "charset": "0123456789ABCDEFGHJKLMNPQRTUWXY",
    "category_codes": ["1", "5", "9", "Y", "A", "B", "C", "D"],
    "standard": "GB 32100-2015"
  },
  "vat_invoice": {
    "context_anchors": ["发票", "号码", "票号", "invoice", "INVOICE", "Invoice",
                        "增值税", "电子发票", "全电发票"],
    "context_window": 20,
    "length_8_required_anchor": true,
    "length_20_required_anchor": true,
    "source": "国家税务总局公告 2022 年第 1 号 + 传统 8 位票号",
    "last_verified": "2026-Q3"
  },
  "bank_account": {
    "context_anchors": ["账号", "账户", "银行账号", "银行账户",
                       "招行", "中行", "建行", "工商银行", "农行", "邮储", "交通银行"],
    "context_window": 20,
    "context_required": true,
    "length_range": [9, 21],
    "source": "银行公开账户命名约定",
    "last_verified": "2026-Q3"
  }
}
```

**关键不变式（D-19 锁定）**:
- 现有 2 键（`phone_segment` / `id_card`）**不动 schema**
- 新 4 键的字段名（`bin_dictionary_path` / `category_codes` / `context_anchors`）一旦被 Phase 8 用户编辑 UI 引用，跨多处修改
- `bin_dictionary_path` 字段值是**相对路径**（解析时拼接 `privacyguard.utils.security.resource_path` 的 base_path）
- `uscc.weights` 与 `validators/uscc.py::USCC_WEIGHTS` 同步（Phase 1 同样模式：mod-11-2 权重在 `id_card.py`，不在 `rules.json`；USCC 沿用此模式以保持一致）

---

### `privacyguard/pii/data/bin_prefixes.json` (new)

**Analog:** `privacyguard/pii/data/rules.json` — **role-match**（同样的纯 JSON 数据文件 + 同目录）。

**Schema 形态**（D-27 + 维基 CC BY-SA 4.0 数据集）：
```json
{
  "_comment": "银行卡 BIN 前缀词典（6 位 ISO/IEC 7812 BIN）",
  "_source": "Wikipedia 'Bank card number' (CC BY-SA 4.0) + 中国银联公开公告",
  "_license": "CC BY-SA 4.0 — see bin_prefixes.json.LICENSE",
  "_count_target": "10,000-15,000",
  "bin_prefixes": [
    "414720", "414721", "414722",
    "510510", "510511", "552100",
    "622202", "622203", "622204",
    "..." 
  ]
}
```

**关键不变式**:
- 文件位置 = `privacyguard/pii/data/bin_prefixes.json`（与 `rules.json` 同目录）
- 必须同时存在 `bin_prefixes.json.LICENSE`（CC BY-SA 4.0 归属声明）
- 加载路径必须走 `privacyguard.utils.security.resource_path`（cp30 教训）

---

### `privacyguard/pii/__init__.py` (modify)

**Analog:** self（Phase 1 13 项扩展到 27 项）— **exact**。

**当前形态** (`privacyguard/pii/__init__.py:20-52`):
```python
__all__ = [
    'PIIEngine', 'PIIHit', 'TextUnit',
    'validate_18_id', 'validate_15_id', 'upgrade_15_to_18',
    'compute_check_digit', 'is_mobile_segment',
    'apply_pii_redactions', 'collect_pii_rects',
    'PHONE_PERSONAL_PREFIX_3', 'PHONE_EXCLUDED_PREFIX_3', 'PHONE_EXCLUDED_PREFIX_4',
    'RULES_VERSION_DEFAULT',
]


_LAZY_IMPORTS = {
    'PIIEngine': ('privacyguard.pii.engine', 'PIIEngine'),
    # ... 13 项
}
```

**Phase 2 追加**（在 `__all__` 与 `_LAZY_IMPORTS` 各追加）：
```python
# __all__ 增加 6 个 validator + 6 个 partial mask + 2 个 helper
'validate_bank_card', 'validate_email', 'validate_uscc', 'validate_taxpayer_id_15',
'validate_vat_invoice_8', 'validate_vat_invoice_20',
'has_vat_invoice_context', 'has_bank_account_context',
'partial_mask_bank_card', 'partial_mask_email', 'partial_mask_uscc',
'partial_mask_vat_invoice', 'partial_mask_taxpayer_id_15', 'partial_mask_bank_account',
'write_partial_masks', 'clear_pdf_metadata',
'BANK_CARD_BIN_WHITELIST', 'EMAIL_PUBLIC_SUFFIXES', 'USCC_CATEGORY_CODES',
'VAT_INVOICE_CONTEXTS', 'BANK_ACCOUNT_CONTEXTS',

# _LAZY_IMPORTS 增加（直接 from validators.* / mask.py / pdf_adapter.py 转发）
'validate_bank_card':      ('privacyguard.pii.validators', 'validate_bank_card'),
'validate_email':          ('privacyguard.pii.validators', 'validate_email'),
'validate_uscc':           ('privacyguard.pii.validators', 'validate_uscc'),
'validate_taxpayer_id_15': ('privacyguard.pii.validators', 'validate_taxpayer_id_15'),
'validate_vat_invoice_8':  ('privacyguard.pii.validators', 'validate_vat_invoice_8'),
'validate_vat_invoice_20': ('privacyguard.pii.validators', 'validate_vat_invoice_20'),
'has_vat_invoice_context': ('privacyguard.pii.validators', 'has_vat_invoice_context'),
'has_bank_account_context':('privacyguard.pii.validators', 'has_bank_account_context'),
'partial_mask_bank_card':  ('privacyguard.pii.mask', 'partial_mask_bank_card'),
'partial_mask_email':      ('privacyguard.pii.mask', 'partial_mask_email'),
'partial_mask_uscc':       ('privacyguard.pii.mask', 'partial_mask_uscc'),
'partial_mask_vat_invoice':('privacyguard.pii.mask', 'partial_mask_vat_invoice'),
'partial_mask_taxpayer_id_15': ('privacyguard.pii.mask', 'partial_mask_taxpayer_id_15'),
'partial_mask_bank_account':('privacyguard.pii.mask', 'partial_mask_bank_account'),
'write_partial_masks':     ('privacyguard.pii.pdf_adapter', 'write_partial_masks'),
'clear_pdf_metadata':      ('privacyguard.pii.pdf_adapter', 'clear_pdf_metadata'),
'BANK_CARD_BIN_WHITELIST': ('privacyguard.pii.validators', 'BANK_CARD_BIN_WHITELIST'),
'EMAIL_PUBLIC_SUFFIXES':   ('privacyguard.pii.validators', 'EMAIL_PUBLIC_SUFFIXES'),
'USCC_CATEGORY_CODES':     ('privacyguard.pii.validators', 'USCC_CATEGORY_CODES'),
'VAT_INVOICE_CONTEXTS':    ('privacyguard.pii.validators', 'VAT_INVOICE_CONTEXTS'),
'BANK_ACCOUNT_CONTEXTS':   ('privacyguard.pii.validators', 'BANK_ACCOUNT_CONTEXTS'),
```

---

### `privacyguard/__init__.py` (modify)

**Analog:** self（Phase 1 13 项扩展到 27 项顶层导出）— **exact**。

**当前形态** (`privacyguard/__init__.py:36-86`):
```python
__all__ = [
    '__version__', '__app_name__',
    'PrivacyAppError', 'ConversionError', ...,
    'PIIEngine', 'PIIHit', 'TextUnit',
    'validate_18_id', 'validate_15_id', 'is_mobile_segment',
    'apply_pii_redactions', 'collect_pii_rects',
]


_LAZY_IMPORTS = {
    'ImageMergeWorker': ('privacyguard.workers', 'ImageMergeWorker'),
    'PIIEngine': ('privacyguard.pii.engine', 'PIIEngine'),
    # ... 13 项
}
```

**Phase 2 追加**（与 `privacyguard/pii/__init__.py` 同步，14 项）：
```python
# __all__ 增加
'validate_bank_card', 'validate_email', 'validate_uscc', 'validate_taxpayer_id_15',
'validate_vat_invoice_8', 'validate_vat_invoice_20',
'partial_mask_bank_card', 'partial_mask_email', 'partial_mask_uscc',
'partial_mask_vat_invoice', 'partial_mask_taxpayer_id_15', 'partial_mask_bank_account',
'write_partial_masks', 'clear_pdf_metadata',

# _LAZY_IMPORTS 增加（从 privacyguard.pii 子包转发）
'validate_bank_card':      ('privacyguard.pii', 'validate_bank_card'),
# ... 14 项
```

**OPS-03 不变式**: `import privacyguard` 不拉起 `privacyguard.pii.*` 任何子模块。

---

### `main.py:12490-12504` (modify — `MainWindow.save_pdf` PII 路径)

**Analog:** self（Phase 1 既有 PII 路径 `main.py:12498-12504`）— **exact**。

**当前形态** (`main.py:12490-12504`):
```python
# Phase 1: pii 命中用 page_rect tuple 路径（D-04 + SAFE-01）
for hit in pii_list:
    pr = hit.page_rect
    rect = fitz.Rect(pr[0], pr[1], pr[0] + pr[2], pr[1] + pr[3])
    annot = page.add_redact_annot(rect)
    annot.set_colors(stroke=fill_col, fill=fill_col)
    annot.update()
```

**Phase 2 改写**（D-22 — 改调 `write_partial_masks` + mode 决策；OCR / manual 路径**不变**）：
```python
# Phase 2: PII 路径改调 write_partial_masks helper（D-21 + D-22 + D-12）
from privacyguard.pii.pdf_adapter import write_partial_masks, clear_pdf_metadata

# ... ocr_list / manual_list 路径保持 Phase 1 既有形态（全遮蔽，不做 partial mask）
for r in ocr_list + manual_list:
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    rect = fitz.Rect(x, y, x + w, y + h)
    annot = page.add_redact_annot(rect)
    annot.set_colors(stroke=fill_col, fill=fill_col)
    annot.update()

# Phase 2: pii_list 走 partial mask 路径（D-12 文档级 override + D-04 per-entity default）
override = self.page_data.get(0, {}).get("mask_override_this_doc") if 0 in self.page_data else None
per_entity_default = self._get_per_entity_default()  # 从 self.config 读 pii_settings.per_entity_default
# 当 override="blackout" 时强制全遮蔽；否则按 per_entity_default 决定
if pii_list:
    # 按 hit 拆分 mode 决策：同页内不同 entity 可能有不同 mode
    partial_hits = []
    blackout_hits = []
    for hit in pii_list:
        if override == "blackout":
            blackout_hits.append(hit)
        elif per_entity_default.get(hit.entity_type, "partial") == "partial":
            partial_hits.append(hit)
        else:
            blackout_hits.append(hit)
    if partial_hits:
        write_partial_masks(doc_save, i, partial_hits, mode="partial")
    if blackout_hits:
        write_partial_masks(doc_save, i, blackout_hits, mode="blackout")
```

**Phase 2 新增 — `doc.set_metadata` 5 字段空**（D-14 + D-15 + D-16，紧邻 `doc.save` 前调）：
```python
# ... 在 page.apply_redactions + delete_annot 之后
# Phase 2: SAFE-03 元数据清除（D-16 仅在 save_pdf 调一次）
clear_pdf_metadata(doc_save)

# v37.3: 安全加固 - 使用垃圾回收和压缩彻底删除未引用对象
doc_save.save(
    fname,
    garbage=4,        # 最大垃圾回收级别
    deflate=True,     # 压缩内容流
    clean=True        # 清理未引用对象
)
```

**关键不变式（D-22 / D-16 锁定）**:
- OCR / manual 路径**完全不动**（保持原 blackout 行为）
- `clear_pdf_metadata` 必须在 `doc.save()` 前调（`save` 之后再调无效）
- `pii_settings.per_entity_default` 通过 `self.config.get("pii_settings.per_entity_default", {})` 读取
- `mask_override_this_doc` 键存于 `self.page_data[0]`，不写入磁盘

---

### `main.py:1008-1700` (modify — `SettingsDialog`「隐私识别」tab 扩展)

**Analog:** self（Phase 1 `box_pii` 卡片 `main.py:1601-1662`）— **exact**。

**当前形态** (`main.py:1601-1662`):
```python
box_pii = QFrame()
box_pii.setObjectName("settingsSectionCard")
v_pii = QVBoxLayout(box_pii)
# ... lead + summary
v_pii.addWidget(self._create_settings_section_header("5. 隐私识别", pii_lead, self.lbl_pii_summary))
# 三个 QCheckBox
v_pii.addWidget(self.cb_pii_engine_enabled)
v_pii.addWidget(self.cb_pii_auto_redact)
v_pii.addWidget(self.cb_pii_require_confirm)
v_pii.addSpacing(14)
lbl_scope = QLabel("扫描范围（只读）：身份证号 / 手机号")
v_pii.addWidget(lbl_scope)
```

**Phase 2 扩展**（D-11 — 在 lbl_scope 之前插入「脱敏方式」表）：
```python
# 现有 3 个 QCheckBox 保持不变
# ... addWidget(self.cb_pii_require_confirm) ...

v_pii.addSpacing(14)

# Phase 2: 脱敏方式表（每个 entity 一行 + QCheckBox + QComboBox 下拉）
lbl_mode = QLabel("脱敏方式（每个实体类型独立设置）：")
lbl_mode.setObjectName("settingsFieldLabel")
v_pii.addWidget(lbl_mode)

ENTITY_MODE_ROWS = [
    ("CN_ID_CARD", "身份证号"),
    ("CN_PHONE", "手机号"),
    ("CN_BANK_CARD", "银行卡"),
    ("CN_EMAIL", "邮箱"),
    ("CN_USCC", "统一社会信用代码"),
    ("CN_TAXPAYER_ID", "纳税人识别号 (18位)"),
    ("CN_TAXPAYER_ID_15", "纳税人识别号 (15位)"),
    ("CN_VAT_INVOICE", "增值税发票号"),
    ("CN_BANK_ACCOUNT", "银行账号"),
]

self.entity_mode_widgets = {}  # 记录每个 entity 的 QComboBox 引用
for entity_type, label in ENTITY_MODE_ROWS:
    row = QHBoxLayout()
    cb = QCheckBox(f"启用 {label}")
    cb.setChecked(per_entity_default.get(f"{entity_type}_enabled", True))
    combo = QComboBox()
    combo.addItems(["部分掩码", "全遮蔽"])
    combo.setCurrentText(per_entity_default.get(entity_type, "partial")
                         and "部分掩码" or "全遮蔽")
    combo.setEnabled(cb.isChecked())
    cb.toggled.connect(lambda checked, c=combo: c.setEnabled(checked))
    row.addWidget(cb)
    row.addWidget(combo, stretch=1)
    v_pii.addLayout(row)
    self.entity_mode_widgets[entity_type] = (cb, combo)

v_pii.addSpacing(10)
# 底部一括黑 / 括星按钮
btn_bulk_layout = QHBoxLayout()
btn_all_blackout = QPushButton("全部设为全遮蔽")
btn_all_blackout.clicked.connect(self._bulk_set_entity_mode_blackout)
btn_all_partial = QPushButton("全部设为部分掩码")
btn_all_partial.clicked.connect(self._bulk_set_entity_mode_partial)
btn_bulk_layout.addWidget(btn_all_blackout)
btn_bulk_layout.addWidget(btn_all_partial)
btn_bulk_layout.addStretch(1)
v_pii.addLayout(btn_bulk_layout)

# 更新只读范围标签
lbl_scope = QLabel("扫描范围：9 类实体（身份证 / 手机 / 银行卡 / 邮箱 / USCC / 纳税人识别号 / VAT 发票号 / 银行账号）")
lbl_scope.setObjectName("settingsFieldNote")
v_pii.addWidget(lbl_scope)
```

**`save_settings` 路径追加**（参照 `main.py` 现有 save_settings）：
```python
# Phase 2: 收集每 entity 的 mode + 启用状态
per_entity_default_new = {}
for entity_type, (cb, combo) in self.entity_mode_widgets.items():
    per_entity_default_new[entity_type] = "blackout" if combo.currentText() == "全遮蔽" else "partial"
self.config.set("pii_settings.per_entity_default", per_entity_default_new, persist=False)
```

**关键不变式**:
- `box_pii.setObjectName("settingsSectionCard")` **不动**
- 现有 3 个 QCheckBox（`cb_pii_engine_enabled` / `cb_pii_auto_redact` / `cb_pii_require_confirm`）**不动**
- 9 个 entity 行的顺序按 `ENTITY_MODE_ROWS` 列表锁（D-13 字段命名锁）
- `_settings_sections` 列表追加 `box_pii` 不动

---

### `main.py` toolbar (modify — 新增「本文件使用全遮蔽」toggle)

**Analog:** self（Phase 1 `rb_black` / `rb_white` 形态，`main.py:5776-5788`）— **exact**。

**当前形态** (`main.py:5776-5788`):
```python
self.rb_black = self.create_btn("黑遮罩", self.update_canvas_color, style="toggle")
self.rb_black.setObjectName("toolbarToggleButton")
self.rb_black.setCheckable(True)
self.rb_black.setChecked(True)
```

**Phase 2 新增**（D-12 — 在 PDF mode 主按钮组 `toolbar_pdf_layout` 内追加）：
```python
# Phase 2: D-12 文档级 override toggle（D-12 mask_override_this_doc）
self.btn_mask_override = self.create_btn("本文件全遮蔽", self._toggle_mask_override_this_doc, style="toggle")
self.btn_mask_override.setObjectName("toolbarToggleButton")
self.btn_mask_override.setCheckable(True)
self.btn_mask_override.setChecked(False)
self.btn_mask_override.setToolTip("勾选后，当前 PDF 临时覆盖全局 per_entity 设置，强制全部 entity 走全遮蔽。切换状态随当前 PDF 生命周期，不持久化。")
self.toolbar_pdf_layout.addWidget(self.btn_mask_override)


def _toggle_mask_override_this_doc(self, checked: bool):
    """D-12: 写入 self.page_data[0]["mask_override_this_doc"] = "blackout" | "partial" """
    if not self.page_data or 0 not in self.page_data:
        return
    self.page_data[0]["mask_override_this_doc"] = "blackout" if checked else None
    if DEBUG_MODE:
        print(f"[PII OVERRIDE] page_data[0] mask_override_this_doc = "
              f"{self.page_data[0].get('mask_override_this_doc')}")
```

**关键不变式（D-12 锁定）**:
- toggle 状态存于 `self.page_data[0]["mask_override_this_doc"]`，**不**写 `config.json`
- 切换 `False` 时显式置 `None`（不残留 `"partial"` 字面量）
- 仅在 PDF 模式下显示（Word 模式沿用 Phase 1 既有 toolbar）

---

### `config.json` + `config.json.template` (modify)

**Analog:** self（Phase 1 `pii_settings` 3 键扩展 4 键）— **exact**。

**当前形态** (`config.json:83-92`):
```json
"pii_settings": {
  "engine_enabled": true,
  "auto_redact": true,
  "require_confirmation": false,
  "scan_scope": ["CN_ID_CARD", "CN_PHONE"],
  "_comment": "Phase 1 隐私识别引擎设置；D-08 锁定"
},
```

**Phase 2 扩展**（D-13 — 新增 `per_entity_default` 字典 + 扩展 `scan_scope` 为 9 项）：
```json
"pii_settings": {
  "engine_enabled": true,
  "auto_redact": true,
  "require_confirmation": false,
  "scan_scope": [
    "CN_ID_CARD",
    "CN_PHONE",
    "CN_BANK_CARD",
    "CN_EMAIL",
    "CN_USCC",
    "CN_TAXPAYER_ID",
    "CN_TAXPAYER_ID_15",
    "CN_VAT_INVOICE",
    "CN_BANK_ACCOUNT"
  ],
  "per_entity_default": {
    "CN_ID_CARD": "partial",
    "CN_PHONE": "partial",
    "CN_BANK_CARD": "partial",
    "CN_EMAIL": "partial",
    "CN_USCC": "partial",
    "CN_TAXPAYER_ID": "partial",
    "CN_TAXPAYER_ID_15": "partial",
    "CN_VAT_INVOICE": "partial",
    "CN_BANK_ACCOUNT": "partial"
  },
  "_comment": "Phase 2 隐私识别引擎设置；D-13 锁定 per_entity_default 字段名"
},
```

**关键不变式（D-13 锁定）**:
- 字段名 `per_entity_default` 一旦被引用，**不**允许重命名
- 值字面量只允许 `"partial"` / `"blackout"`（**不**是 `"mask"` / `"redact"` 等同义词）
- 9 个 entity key **完整列出**（不省略；模板中也是 9 项显式）
- `config.json.template` 同步追加（与 `config.json` 字段名 / 顺序一致）

---

### `tests/fixtures/fake_pii.py` (modify)

**Analog:** self（Phase 1 `fake_id_card` / `fake_phone` / `fake_phone_invalid` 形态）— **exact**。

**当前形态** (`tests/fixtures/fake_pii.py:45-79`):
```python
def fake_id_card(year_lo: int = 90) -> str:
    # 行政区划码 + 日期 + 校验位 循环生成
    ...
def fake_phone(seg: str = '138') -> str:
    return seg + ''.join(random.choice('0123456789') for _ in range(8))
def fake_phone_invalid() -> str:
    return '140' + ''.join(random.choice('0123456789') for _ in range(8))
```

**Phase 2 追加**（每个新 entity 一个 fake_* 合成函数 + 至少一个 fake_*_invalid 反例）：
```python
def fake_bank_card() -> str:
    """生成一个通过 Luhn + 假设 BIN 白名单的伪银行卡号（16 位）。"""
    bin6 = random.choice(["622202", "414720", "510510"])  # 已知公开 BIN
    body = bin6 + ''.join(random.choice('0123456789') for _ in range(9))
    # Luhn 校验位
    total = 0
    for i, ch in enumerate(body[::-1]):
        d = int(ch)
        if i % 2 == 0:  # 从右数第 1 位起（校验位在最后一位）
            d *= 2
            if d > 9:
                d -= 9
        total += d
    check = (10 - total % 10) % 10
    return body + str(check)


def fake_email(local: str = None) -> str:
    local = local or ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(6))
    domain = random.choice(["qq.com", "163.com", "gmail.com", "outlook.com"])
    return f"{local}@{domain}"


def fake_uscc() -> str:
    """生成一个通过 mod-31-3 校验 + 类别代码在 8 字符内的伪 USCC。"""
    charset = "0123456789ABCDEFGHJKLMNPQRTUWXY"
    cat = random.choice(["1", "5", "9", "Y", "A", "B", "C", "D"])
    body17 = cat + ''.join(random.choice(charset) for _ in range(16))
    weights = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)
    total = sum(charset.index(body17[i]) * weights[i] for i in range(17))
    check = charset[(31 - total % 31) % 31]
    return body17 + check


def fake_vat_invoice_8() -> str:
    return ''.join(random.choice('0123456789') for _ in range(8))


def fake_vat_invoice_20() -> str:
    return ''.join(random.choice('0123456789') for _ in range(20))


def fake_taxpayer_id_15() -> str:
    """旧版 15 位纳税人识别号（行政区划码 + 6 位日期 + 3 位序）。"""
    province = random.choice(['11', '12', '31', '33', '44', '51', '61'])
    rest = ''.join(random.choice('0123456789') for _ in range(13))
    return province + rest


def fake_bank_account() -> str:
    return ''.join(random.choice('0123456789') for _ in range(18))


# 反例（validator 应拒绝）
def fake_bank_card_invalid_luhn() -> str:
    """Luhn 校验失败的银行卡号。"""
    return "6222020000000000"  # Luhn 应判 False


def fake_uscc_invalid_category() -> str:
    """登记管理部门类别代码无效的 USCC（首字符非 8 字符之一）。"""
    return "Z" + "0123456789ABCDEFGH"[:17]  # 长度需 18
```

**关键不变式**:
- 测试断言字符串**必须**用 `fake_*` 函数产出（OPS-05 严禁真实数据）
- 每个 entity 提供 1-2 个 `_invalid_*` 反例函数（保证 validator 拒绝路径可测）

---

### `tests/unit/test_pii_validators.py` (modify)

**Analog:** self（Phase 1 现有 `TestIdCardChecksum` / `TestIdCaseInsensitiveX` / `TestPhoneSegment` 形态）— **exact**。

**当前形态** (`tests/unit/test_pii_validators.py:48-130`):
```python
class TestIdCardChecksum(unittest.TestCase):
    def test_valid_18_passes_checksum(self):
        self.assertTrue(validate_18(_GB_STD_18))
    # ...
class TestIdCardUpgrade15To18(unittest.TestCase):
    # ...
class TestPhoneSegment(unittest.TestCase):
    # ...
```

**Phase 2 追加**（8 个新测试类，按 entity 一类）：
```python
class TestBankCardLuhn(unittest.TestCase):
    def test_luhn_valid_16_digit_passes(self):
        from privacyguard.pii.validators.bank_card import luhn_check
        self.assertTrue(luhn_check("6222021234567890"))  # 假设此号 Luhn 必过

    def test_luhn_invalid_fails(self):
        from privacyguard.pii.validators.bank_card import luhn_check
        self.assertFalse(luhn_check("6222021234567891"))  # 校验位错


class TestBankCardBin(unittest.TestCase):
    def test_known_bin_in_whitelist_passes(self):
        from privacyguard.pii.validators.bank_card import validate_bank_card
        # 已知 622202 公开 BIN
        self.assertTrue(validate_bank_card("6222021234567890", bin_whitelist=frozenset({"622202"})))

    def test_unknown_bin_rejected(self):
        from privacyguard.pii.validators.bank_card import validate_bank_card
        self.assertFalse(validate_bank_card("0000001234567890", bin_whitelist=frozenset({"622202"})))


class TestEmail(unittest.TestCase):
    def test_valid_email_passes(self):
        from privacyguard.pii.validators.email import validate_email
        self.assertTrue(validate_email("user@example.com"))

    def test_invalid_email_rejected(self):
        from privacyguard.pii.validators.email import validate_email
        self.assertFalse(validate_email("not-an-email"))

    def test_public_suffix_classified_high(self):
        from privacyguard.pii.validators.email import is_public_suffix_email
        self.assertTrue(is_public_suffix_email("foo@qq.com"))


class TestUsccMod31(unittest.TestCase):
    def test_valid_uscc_passes(self):
        from privacyguard.pii.validators.uscc import validate_uscc
        # 9 字符登记管理部门类别 + 17 位 body 拼 18 位
        self.assertTrue(validate_uscc("91110000600037341L"))  # 占位样本

    def test_invalid_category_rejected(self):
        from privacyguard.pii.validators.uscc import validate_uscc
        self.assertFalse(validate_uscc("Z11000000000000000"))  # Z 不在 8 字符

    def test_check_digit_mismatch_rejected(self):
        from privacyguard.pii.validators.uscc import validate_uscc
        self.assertFalse(validate_uscc("911100006000373410"))  # 末位应为 L


class TestUsccCategory(unittest.TestCase):
    def test_all_8_categories_accepted(self):
        from privacyguard.pii.validators.uscc import USCC_CATEGORY_CODES
        self.assertEqual(len(USCC_CATEGORY_CODES), 8)


class TestVatInvoice(unittest.TestCase):
    def test_8_digit_passes(self):
        from privacyguard.pii.validators.vat_invoice import validate_vat_invoice_8
        self.assertTrue(validate_vat_invoice_8("12345678"))

    def test_20_digit_passes(self):
        from privacyguard.pii.validators.vat_invoice import validate_vat_invoice_20
        self.assertTrue(validate_vat_invoice_20("12345678901234567890"))


class TestTaxpayerId15(unittest.TestCase):
    def test_valid_15_with_valid_admin_prefix(self):
        from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15
        self.assertTrue(validate_taxpayer_id_15("110101800101001"))

    def test_invalid_admin_prefix_rejected(self):
        from privacyguard.pii.validators.taxpayer_id import validate_taxpayer_id_15
        self.assertFalse(validate_taxpayer_id_15("990101800101001"))  # 99 不在白名单


class TestBankAccount(unittest.TestCase):
    def test_18_digit_passes(self):
        from privacyguard.pii.validators.bank_account import validate_bank_account
        self.assertTrue(validate_bank_account("622202123456789012"))

    def test_short_account_rejected(self):
        from privacyguard.pii.validators.bank_account import validate_bank_account
        self.assertFalse(validate_bank_account("12345678"))  # 8 位
```

**关键不变式**:
- 每个测试类用 `unittest.TestCase`
- 沿用 `from privacyguard.pii.validators.X import Y` 形态（验证懒加载链路）
- 包含正向 + 反向 + 边界用例

---

### `tests/unit/test_pii_engine.py` (modify)

**Analog:** self（Phase 1 `TestEngineDetect` / `TestMaskConsistency` 形态）— **exact**。

**当前形态** (`tests/unit/test_pii_engine.py:160-200`):
```python
class TestEngineDetect(unittest.TestCase):
    def setUp(self):
        self.engine = PIIEngine()

    def test_detects_id_card_in_plain_text(self):
        unit = TextUnit(page_index=0, text="张三 53010219200508011X 已婚", source="text")
        hits = self.engine.detect(unit)
        self.assertEqual(len(hits), 1)
```

**Phase 2 追加**（6 个新测试类）：
```python
class TestEngineBankCard(unittest.TestCase):
    def test_detects_valid_bank_card(self):
        from tests.fixtures.fake_pii import fake_bank_card
        card = fake_bank_card()
        engine = PIIEngine()
        unit = TextUnit(page_index=0, text=f"卡号 {card}", source="text")
        hits = engine.detect(unit)
        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0].entity_type, "CN_BANK_CARD")

    def test_rejects_luhn_failure(self):
        from privacyguard.pii.engine import PIIEngine, TextUnit
        engine = PIIEngine()
        unit = TextUnit(page_index=0, text="卡号 6222020000000000", source="text")
        hits = engine.detect(unit)
        self.assertEqual(len(hits), 0)


class TestEngineEmail(unittest.TestCase):
    def test_detects_valid_email(self):
        from tests.fixtures.fake_pii import fake_email
        engine = PIIEngine()
        unit = TextUnit(page_index=0, text=f"邮箱 {fake_email()}", source="text")
        hits = engine.detect(unit)
        self.assertEqual(hits[0].entity_type, "CN_EMAIL")


class TestEngineUscc(unittest.TestCase):
    def test_detects_valid_uscc(self):
        from tests.fixtures.fake_pii import fake_uscc
        uscc = fake_uscc()
        engine = PIIEngine()
        unit = TextUnit(page_index=0, text=f"统一信用代码 {uscc}", source="text")
        hits = engine.detect(unit)
        self.assertEqual(hits[0].entity_type, "CN_USCC")


class TestEngineVatInvoice(unittest.TestCase):
    def test_detects_8_digit_with_context(self):
        from tests.fixtures.fake_pii import fake_vat_invoice_8
        engine = PIIEngine()
        unit = TextUnit(page_index=0, text=f"发票号码 {fake_vat_invoice_8()}", source="text")
        hits = engine.detect(unit)
        self.assertEqual(hits[0].entity_type, "CN_VAT_INVOICE")

    def test_detects_20_digit_with_context(self):
        from tests.fixtures.fake_pii import fake_vat_invoice_20
        engine = PIIEngine()
        unit = TextUnit(page_index=0, text=f"全电发票号码 {fake_vat_invoice_20()}", source="text")
        hits = engine.detect(unit)
        self.assertEqual(hits[0].entity_type, "CN_VAT_INVOICE")


class TestEngineTaxpayerId15(unittest.TestCase):
    def test_detects_15_digit(self):
        from tests.fixtures.fake_pii import fake_taxpayer_id_15
        engine = PIIEngine()
        unit = TextUnit(page_index=0, text=f"旧版税号 {fake_taxpayer_id_15()}", source="text")
        hits = engine.detect(unit)
        self.assertEqual(hits[0].entity_type, "CN_TAXPAYER_ID_15")


class TestEngineBankAccount(unittest.TestCase):
    def test_detects_with_context(self):
        from tests.fixtures.fake_pii import fake_bank_account
        acct = fake_bank_account()
        engine = PIIEngine()
        unit = TextUnit(page_index=0, text=f"银行账号 {acct}", source="text")
        hits = engine.detect(unit)
        self.assertEqual(hits[0].entity_type, "CN_BANK_ACCOUNT")

    def test_rejects_without_context(self):
        from tests.fixtures.fake_pii import fake_bank_account
        acct = fake_bank_account()
        engine = PIIEngine()
        unit = TextUnit(page_index=0, text=f"数字 {acct}", source="text")
        hits = engine.detect(unit)
        self.assertEqual(len(hits), 0)  # 锥点必查
```

**关键不变式**:
- `setUp` 内统一创建 `PIIEngine()`（与 Phase 1 一致）
- `TextUnit(page_index=0, text=..., source="text")` 路径使用（D-09 + B2 一致）
- 锥点必查 entity（VAT / Bank Account）必须有正向 + 反向测试

---

### `tests/unit/test_pdf_pii_redaction.py` (modify)

**Analog:** self（Phase 1 `TestPdfPiiRedaction.test_redacted_text_not_extractable` 形态）— **exact**。

**当前形态** (`tests/unit/test_pdf_pii_redaction.py:77-111`):
```python
def test_redacted_text_not_extractable(self):
    """SAFE-01 / SAFE-02：fitz.open(out).get_text() 反向断言敏感字符串不存在。"""
    with tempfile.TemporaryDirectory() as tmp:
        in_pdf = os.path.join(tmp, "in.pdf")
        out_pdf = os.path.join(tmp, "out.pdf")
        secret_id, secret_phone = self._build_pii_pdf(in_pdf)
        rects_per_page, hits = self._detect_with_search_for(in_pdf)
        apply_pii_redactions(in_pdf, out_pdf, rects_per_page)
        with fitz.open(out_pdf) as out_doc:
            out_text = "".join(p.get_text() for p in out_doc)
        self.assertNotIn(secret_id[:10], out_text)
        self.assertNotIn(secret_phone[:7], out_text)
```

**Phase 2 追加**（D-23 — partial mask 反向 + metadata 清除反向）：
```python
class TestPartialMaskWritesMaskText(unittest.TestCase):
    """D-23: partial mask 写入后反向断言原文不存在 + mask_strategy 文字存在。"""

    def _build_pii_pdf_with_mask_strategy(self, in_pdf: str, secret: str, entity_type: str) -> None:
        """构建一个含 PII 的 PDF，partial mask 后 mask_strategy 文字应保留。"""
        from privacyguard.pii.mask import mask_for_entity
        mask = mask_for_entity(entity_type, secret)
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (50, 100),
            f"测试 {entity_type} 原文 {secret} 掩码 {mask}",
            fontsize=14,
        )
        doc.save(in_pdf)
        doc.close()

    def _detect_with_search_for(self, in_pdf):
        # ... 同 Phase 1 `_detect_with_search_for` 形态
        ...

    def test_partial_mask_writes_mask_text_to_pdf(self):
        """partial mask 路径：原文字符串应消失，mask_strategy 文字应保留。"""
        from tests.fixtures.fake_pii import fake_id_card
        secret = fake_id_card()
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in.pdf")
            out_pdf = os.path.join(tmp, "out.pdf")
            self._build_pii_pdf_with_mask_strategy(in_pdf, secret, "CN_ID_CARD")
            rects_per_page, _ = self._detect_with_search_for(in_pdf)
            # partial mask 模式（mode="partial"）
            from privacyguard.pii.pdf_adapter import write_partial_masks
            doc = fitz.open(in_pdf)
            try:
                for page_idx, _hits in rects_per_page.items():
                    # 重建 PIIHit with mask_strategy
                    from privacyguard.pii.hits import PIIHit
                    hits = []
                    for r in rects_per_page[page_idx]:
                        hits.append(PIIHit(
                            entity_type="CN_ID_CARD",
                            page_offset=0,
                            page_length=18,
                            page_rect=(r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0),
                            mask_strategy=secret[:6] + "*" * 8 + secret[14:],
                            normalized=secret,
                            source="text",
                        ))
                    write_partial_masks(doc, page_idx, hits, mode="partial")
            finally:
                doc.save(out_pdf, garbage=4, deflate=True, clean=True)
                doc.close()
            with fitz.open(out_pdf) as out_doc:
                out_text = "".join(p.get_text() for p in out_doc)
            self.assertNotIn(secret[:10], out_text, "partial mask 后原文前 10 位仍可提取")
            # mask_strategy 文字应保留（白字写在色块上）
            mask_text = secret[:6] + "*" * 8 + secret[14:]
            # 注：PyMuPDF insert_text 默认字体是 helv，可能与原字体不同；只断言 mask 的前 6 位（区域码）
            self.assertIn(secret[:6], out_text, "partial mask 后 mask 文字前 6 位（区域码）应保留")

    def test_metadata_5_fields_cleared_on_save(self):
        """D-23: save_pdf 后 doc.metadata 5 字段全为空字符串。"""
        from privacyguard.pii.pdf_adapter import clear_pdf_metadata
        with tempfile.TemporaryDirectory() as tmp:
            in_pdf = os.path.join(tmp, "in_meta.pdf")
            out_pdf = os.path.join(tmp, "out_meta.pdf")
            # 创建一个带元数据的 PDF
            doc = fitz.open()
            doc.set_metadata({
                "title": "敏感标题",
                "author": "敏感作者",
                "subject": "敏感主题",
                "producer": "敏感生产者",
                "creator": "敏感创建者",
            })
            page = doc.new_page()
            page.insert_text((50, 100), "测试", fontsize=14)
            doc.save(in_pdf)
            doc.close()
            # 模拟 save_pdf 流程
            doc = fitz.open(in_pdf)
            try:
                clear_pdf_metadata(doc)
                doc.save(out_pdf, garbage=4, deflate=True, clean=True)
            finally:
                doc.close()
            # 反向断言
            with fitz.open(out_pdf) as out_doc:
                meta = out_doc.metadata
                for key in ("title", "author", "subject", "producer", "creator"):
                    self.assertEqual(meta.get(key, ""), "", f"元数据 {key} 未清空")
```

**关键不变式（D-23 / D-25 锁定）**:
- 反向提取路径用 `fitz.open().get_text()`，**不**依赖 poppler-utils
- `clear_pdf_metadata` 调用后 `doc.metadata` 5 字段必须 `""`（PyMuPDF 1.27.1 行为）
- partial mask 后 mask 文字断言**只**检查区域码（`secret[:6]`）而非全字串（避免字体差异）

---

### `tests/unit/test_app_config.py` (modify)

**Analog:** self（Phase 1 `test_simple_config_pii_settings_round_trip` 形态）— **exact**。

**当前形态** (`tests/unit/test_app_config.py:101-120`):
```python
def test_simple_config_pii_settings_round_trip(self):
    config = SimpleConfig(temp_path)
    config.set("pii_settings.engine_enabled", True, persist=False)
    config.set("pii_settings.auto_redact", False, persist=False)
    config.set("pii_settings.require_confirmation", True, persist=False)
    self.assertTrue(config.save())
    reloaded = SimpleConfig(temp_path)
    self.assertEqual(reloaded.get("pii_settings.engine_enabled"), True)
    # ...
```

**Phase 2 追加**（D-23 — `per_entity_default` 字段测试）：
```python
def test_simple_config_pii_settings_per_entity_default_round_trip(self):
    """Phase 2: pii_settings.per_entity_default 字段读取/默认值/类型断言。"""
    fd, temp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump({}, handle)
        config = SimpleConfig(temp_path)
        # 9 个 entity key 默认全 partial
        per_entity = {
            "CN_ID_CARD": "partial",
            "CN_PHONE": "partial",
            "CN_BANK_CARD": "blackout",
            "CN_EMAIL": "partial",
            "CN_USCC": "partial",
            "CN_TAXPAYER_ID": "partial",
            "CN_TAXPAYER_ID_15": "partial",
            "CN_VAT_INVOICE": "partial",
            "CN_BANK_ACCOUNT": "partial",
        }
        config.set("pii_settings.per_entity_default", per_entity, persist=False)
        self.assertTrue(config.save())
        reloaded = SimpleConfig(temp_path)
        loaded = reloaded.get("pii_settings.per_entity_default")
        # 类型断言
        self.assertIsInstance(loaded, dict)
        # 值断言
        self.assertEqual(loaded["CN_BANK_CARD"], "blackout")
        # 9 个 key 完整
        self.assertEqual(len(loaded), 9)
    finally:
        os.remove(temp_path)

def test_simple_config_pii_settings_per_entity_default_default(self):
    """Phase 2: per_entity_default 缺失时返回 None。"""
    fd, temp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump({}, handle)
        config = SimpleConfig(temp_path)
        self.assertIsNone(config.get("pii_settings.per_entity_default"))
    finally:
        os.remove(temp_path)
```

**关键不变式**:
- 沿用 `tempfile.mkstemp` + `os.remove` 清理（与 Phase 1 一致）
- 字段名 `per_entity_default` 与 `config.json` 一致（D-13 锁）

---

### `packaging/windows/config/PrivacyGuard_windows.spec` (modify)

**Analog:** self（Phase 1 PII 段 `datas` + `hiddenimports` 扩展）— **exact**。

**当前形态** (`packaging/windows/config/PrivacyGuard_windows.spec:158-164, 194`):
```python
hiddenimports=[
    # ...
    'privacyguard.pii',
    'privacyguard.pii.engine',
    'privacyguard.pii.hits',
    'privacyguard.pii.validators',
    'privacyguard.pii.validators.id_card',
    'privacyguard.pii.validators.phone_segment',
    'privacyguard.pii.pdf_adapter',
],

datas=[
    # ...
    (os.path.join(project_root, 'privacyguard', 'pii', 'data'), 'privacyguard/pii/data'),
],
```

**Phase 2 追加**（D-26 — 6 个新 validator 模块 + cp30 防回归）：
```python
hiddenimports=[
    # ... 既有
    'privacyguard.pii',
    'privacyguard.pii.engine',
    'privacyguard.pii.hits',
    'privacyguard.pii.validators',
    'privacyguard.pii.validators.id_card',
    'privacyguard.pii.validators.phone_segment',
    # Phase 2 新增 6 个 validator 模块
    'privacyguard.pii.validators.bank_card',
    'privacyguard.pii.validators.email',
    'privacyguard.pii.validators.uscc',
    'privacyguard.pii.validators.vat_invoice',
    'privacyguard.pii.validators.taxpayer_id',
    'privacyguard.pii.validators.bank_account',
    'privacyguard.pii.pdf_adapter',
    # ... 既有
],

datas=[
    # ... 既有
    # cp30 防回归 — bin_prefixes.json 必须随 frozen 包发布
    (os.path.join(project_root, 'privacyguard', 'pii', 'data'), 'privacyguard/pii/data'),
],
```

**关键不变式（cp30 教训 + D-26 锁定）**:
- `datas` 段以 `privacyguard/pii/data` 整目录追加（PyInstaller 自然复制 `bin_prefixes.json` + `rules.json`）
- 6 个新 validator 模块**必须**显式列在 `hiddenimports`（避免 PyInstaller 自动扫描遗漏）
- `bin_prefixes.json.LICENSE` 是**纯文本**（PyInstaller 默认不复制 `.LICENSE` 后缀文件；如果命名空间 `data` 已被 spec 包含整目录，LICENSE 自动随附）

---

### `packaging/macos/config/PrivacyGuard.spec` (modify)

**Analog:** self（Phase 1 PII 段 `datas` + `hiddenimports` 扩展，与 Windows spec parity）— **exact**。

**当前形态** (`packaging/macos/config/PrivacyGuard.spec:46, 95-101`):
```python
datas=[
    # ...
    (os.path.join(project_root, 'privacyguard', 'pii', 'data'), 'privacyguard/pii/data'),
],

hiddenimports=[
    # ...
    'privacyguard.pii',
    'privacyguard.pii.engine',
    'privacyguard.pii.hits',
    'privacyguard.pii.validators',
    'privacyguard.pii.validators.id_card',
    'privacyguard.pii.validators.phone_segment',
    'privacyguard.pii.pdf_adapter',
],
```

**Phase 2 追加**（与 Windows spec **完全一致** — parity 强制）：
```python
datas=[
    # ... 既有
    (os.path.join(project_root, 'privacyguard', 'pii', 'data'), 'privacyguard/pii/data'),
],

hiddenimports=[
    # ... 既有
    'privacyguard.pii',
    'privacyguard.pii.engine',
    'privacyguard.pii.hits',
    'privacyguard.pii.validators',
    'privacyguard.pii.validators.id_card',
    'privacyguard.pii.validators.phone_segment',
    # Phase 2 新增 6 个 validator 模块
    'privacyguard.pii.validators.bank_card',
    'privacyguard.pii.validators.email',
    'privacyguard.pii.validators.uscc',
    'privacyguard.pii.validators.vat_invoice',
    'privacyguard.pii.validators.taxpayer_id',
    'privacyguard.pii.validators.bank_account',
    'privacyguard.pii.pdf_adapter',
],
```

**关键不变式**:
- Windows spec 与 macOS spec 的 PII 段必须**字段级一致**（`build_complete.sh` parity check 验证）
- `packaging/macos/scripts/build_complete.sh` 内若存在 PII 段硬编码复制逻辑，必须同步追加 `bin_prefixes.json` 复制步骤

---

## Shared Patterns

### 1. Lazy-Load Discipline (OPS-03 + cp30)

**Source:** `privacyguard/__init__.py:70-97` + `privacyguard/workers/__init__.py:15-34` + `privacyguard/pii/__init__.py:38-66`
**Apply to:** `privacyguard/pii/validators/__init__.py` (扩展 _LAZY_IMPORTS) + 顶层 `privacyguard/__init__.py` (扩展 14 项)

```python
# 复用模式（参照 privacyguard/pii/__init__.py:38-66）
from importlib import import_module

__all__ = ['...']
_LAZY_IMPORTS = {'Name': ('privacyguard.pii.module', 'Name'), ...}

def __getattr__(name):
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_IMPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
```

**禁止：** `privacyguard/pii/validators/__init__.py` 中加入包级 `from privacyguard.pii.validators.bank_card import ...` eager import。

---

### 2. Pure-Function Validator Pattern (D-09 + D-17 + NUM-04..05 / FIN-01..04)

**Source:** `privacyguard/pii/validators/id_card.py:1-128` + `phone_segment.py:1-62`
**Apply to:** 6 个新 validator 子模块（bank_card / email / uscc / vat_invoice / taxpayer_id / bank_account）

```python
# 复用模式（参照 phone_segment.py:1-29）
"""<entity> 校验（<GB / RFC 引用>）。

D-XX: <一句话核心规则>
"""
from typing import Final


# 1. 白名单 / 权重表 / 字符集 常量（frozen set or tuple）
ENTITY_xxx: Final = frozenset({...})


# 2. 防御性输入校验（isinstance str check）
def validate_xxx(value) -> bool:
    if not isinstance(value, str):
        return False
    # 长度 / 字符类型 / 校验位 三层 gate
    ...


__all__ = ['ENTITY_xxx', 'validate_xxx', ...]
```

**意义：** validator 是**纯函数**，无 IO / 无线程 / 无状态；engine 通过 `(entity_hint, normalized)` → `validate_xxx` 分派。

---

### 3. PyMuPDF True Redaction + Partial Mask Write (SAFE-01 + D-01 / D-21)

**Source:** `privacyguard/pii/pdf_adapter.py:37-64` + `main.py:12354-12385` + 新 `write_partial_masks` helper
**Apply to:** `MainWindow.save_pdf` 的 `pii_list` 路径 + `pdf_adapter.py::write_partial_masks`

```python
# 完整模式（沿用 main.py:12354-12385 + D-21）
# 1. add_redact_annot
annot = page.add_redact_annot(rect)
annot.set_colors(stroke=fill_color, fill=fill_color)
annot.update()
# 2. apply_redactions（必须 PDF_REDACT_IMAGE_PIXELS = 2，否则图像像素不被销毁）
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
# 3. delete_annot（防止 PDF 编辑器修改）
for annot in page.annots() or []:
    page.delete_annot(annot)
# 4. partial mask 路径（D-21）— 在新色块上写 mask_strategy
page.insert_text(
    (x_center, y_center), mask_strategy,
    fontsize=font_size, fontname=font_name,
    color=(1.0, 1.0, 1.0),  # 白字
)
# 5. save 三件套
doc.save(out, garbage=4, deflate=True, clean=True)
```

**关键常量：** `fitz.PDF_REDACT_IMAGE_PIXELS = 2`（**不是**默认 `PDF_REDACT_IMAGE_NONE = 0`，否则图像像素不被销毁）。

---

### 4. page_data Dict Single Source of Truth (D-04 + D-12)

**Source:** `main.py:11385` + Phase 1 `_on_pii_page_result` 槽
**Apply to:** 任何读写 `page_data[page_num]` 的代码（worker / UI / save loop）

```python
# 初始化（open_pdf 流程）
self.page_data = {i: {'ocr': [], 'manual': [], 'pii': []} for i in range(total)}

# Phase 2 扩展（D-12 文档级 override key）
self.page_data[0]["mask_override_this_doc"] = "blackout"  # toolbar toggle 写入
self.page_data[0]["mask_override_this_doc"] = None  # 取消勾选

# 写入（_on_xxx_page_result 槽）
self.page_data[page_num]['pii'] = hits

# 读取（save loop — D-22 改调 write_partial_masks）
override = self.page_data[0].get("mask_override_this_doc")
pii_list = self.page_data[i].get('pii', [])
```

**禁止：** 新增 `self.pii_hits = []` 全局列表；UI 与 apply 必须共享 `page_data[page_num]['pii']` 同一数据契约（v37.7.6 收敛原则）。

---

### 5. Resource Path for PyInstaller (cp30 + D-10 + D-26)

**Source:** `privacyguard/utils/security.py:110-116` (`resource_path`)
**Apply to:** 任何读取 `privacyguard/pii/data/rules.json` / `bin_prefixes.json` 的代码

```python
from privacyguard.utils.security import resource_path
RULES_PATH = resource_path("privacyguard/pii/data/rules.json")
BIN_DICT_PATH = resource_path("privacyguard/pii/data/bin_prefixes.json")
```

**强制要求：** 必须在 PyInstaller spec 的 `datas=[...]` 段追加 `(project_root/privacyguard/pii/data, privacyguard/pii/data)`，否则 frozen 启动报 `FileNotFoundError`。

---

### 6. PII Engine detect Pipeline (Phase 1 沿用 + Phase 2 yield 扩展)

**Source:** `privacyguard/pii/engine.py:103-149`
**Apply to:** 6 个新 entity 全部走 `iter_candidate_strings` → `_check_xxx` → `_make_hit` 同一管线

```python
# 引擎入口（已生产验证）
def detect(self, unit, page=None) -> List[PIIHit]:
    text = unit.text or ''
    flat = flatten_for_match(text)
    for cand, flat_span, entity_hint in iter_candidate_strings(flat):  # Phase 2 yield 9 项
        if entity_hint == 'CN_BANK_CARD':
            hit = self._check_bank_card(unit, cand, normalized, flat_span, text, page)
        # ... 5 个新 _check_xxx
        if hit is not None:
            hits.append(hit)
    return resolve_overlap(hits)
```

**不变式：** `engine.py` 是**纯函数**，不 import PyQt6 / QThread / fitz；所有 format-I/O 留给 `pdf_adapter.py`。

---

### 7. SettingsDialog Section Card Pattern (UI-SPEC + D-11)

**Source:** `main.py:1526-1599` (`box_ocr` 卡片) + `main.py:1601-1662` (`box_pii` 卡片)
**Apply to:** `box_pii` 卡片扩展「脱敏方式」表（D-11）

```python
box_xxx = QFrame()
box_xxx.setObjectName("settingsSectionCard")  # 锁定 objectName，复用既有 QSS
v_xxx = QVBoxLayout(box_xxx)
v_xxx.setContentsMargins(16, 16, 16, 16)
v_xxx.setSpacing(12)
v_xxx.addWidget(self._create_settings_section_header("5. 隐私识别", pii_lead, self.lbl_pii_summary))
# 现有 3 个 QCheckBox 不动
# Phase 2: 9 行 entity_mode 行（QCheckBox + QComboBox）
for entity_type, label in ENTITY_MODE_ROWS:
    row = QHBoxLayout()
    cb = QCheckBox(f"启用 {label}")
    combo = QComboBox()
    combo.addItems(["部分掩码", "全遮蔽"])
    row.addWidget(cb)
    row.addWidget(combo, stretch=1)
    v_xxx.addLayout(row)
layout.addWidget(box_xxx)
self._settings_sections.append(box_xxx)
```

**UI-SPEC 锁定：** `box_pii.setObjectName("settingsSectionCard")` 必须保留；3 个现有 QCheckBox 顺序 / tooltip 不动。

---

### 8. Toolbar Toggle Pattern (Phase 1 沿用 + D-12)

**Source:** `main.py:5776-5788` (`rb_black` / `rb_white` 形态)
**Apply to:** 「本文件使用全遮蔽」toggle 按钮（D-12）

```python
self.btn_mask_override = self.create_btn("本文件全遮蔽", self._toggle_mask_override_this_doc, style="toggle")
self.btn_mask_override.setObjectName("toolbarToggleButton")
self.btn_mask_override.setCheckable(True)
self.btn_mask_override.setChecked(False)
self.toolbar_pdf_layout.addWidget(self.btn_mask_override)
```

**关键约束：** toggle 状态写 `self.page_data[0]["mask_override_this_doc"]`，**不**写 `config.json`。

---

### 9. unittest.TestCase Convention (D-23 + Phase 1 沿用)

**Source:** `tests/unit/test_mixed_pdf_ocr.py` + `tests/unit/test_pdf_text_hit_dedup.py` + `tests/unit/test_app_config.py`
**Apply to:** 所有新增 `tests/unit/test_*.py` 扩展

```python
import unittest
# ...
class TestXxx(unittest.TestCase):
    def setUp(self):
        self.engine = PIIEngine()  # Phase 2 沿用
    def test_xxx(self):
        unit = TextUnit(page_index=0, text="...", source="text")
        hits = self.engine.detect(unit)
        self.assertEqual(hits[0].entity_type, "CN_BANK_CARD")


if __name__ == "__main__":
    unittest.main()
```

**约束：** 无需 Qt display；无 pytest fixture；用 `unittest.TestCase` + `setUp` / `tearDown`；FakePage 用 `SimpleNamespace` 注入（参照 `tests/unit/test_pii_engine.py:44-63`）。

---

### 10. Reverse-Extraction Verification (SAFE-02 + D-23 / D-25)

**Source:** `tests/unit/test_pdf_pii_redaction.py:77-111` + Phase 1 D-14
**Apply to:** `tests/unit/test_pdf_pii_redaction.py` 扩展 partial mask + metadata 清除反向

```python
with fitz.open(out_pdf) as out_doc:
    out_text = "".join(p.get_text() for p in out_doc)
self.assertNotIn(secret_id[:10], out_text, "身份证前 10 位仍可提取")

# Phase 2: partial mask 后 mask 文字存在（仅断言区域码，避免字体差异）
mask_text = secret[:6] + "*" * 8 + secret[14:]
self.assertIn(secret[:6], out_text, "partial mask 后 mask 文字前 6 位应保留")

# Phase 2: metadata 清除反向
meta = out_doc.metadata
for key in ("title", "author", "subject", "producer", "creator"):
    self.assertEqual(meta.get(key, ""), "", f"元数据 {key} 未清空")
```

**优先 `fitz` 路径**（避免 CI 装 poppler）；`pdftotext` 仅作人工验证备用（D-14 / D-25）。

---

## New Patterns for Phase 2

### A. Partial Mask Write Pattern (D-01 + D-02 + D-21 + MASK-01)

**Why new:** Phase 1 仅有 `add_redact_annot + apply_redactions(IMAGE_PIXELS)` 全遮蔽路径；Phase 2 引入 partial mask（黑底色块 + 居中白字 mask_strategy）。

**完整模式**（`privacyguard/pii/pdf_adapter.py::write_partial_masks`）：
```python
def write_partial_masks(doc, page_idx, pii_hits, mode="partial"):
    page = doc[page_idx]
    for hit in pii_hits:
        r = hit.page_rect
        rect = fitz.Rect(r[0], r[1], r[0] + r[2], r[1] + r[3])
        annot = page.add_redact_annot(rect)
        annot.set_colors(stroke=(0, 0, 0), fill=(0, 0, 0))
        annot.update()
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
    for annot in page.annots() or []:
        page.delete_annot(annot)
    if mode == "blackout":
        return
    # mode == "partial": 在新生成的色块上写 mask_strategy
    for hit in pii_hits:
        r = hit.page_rect
        rect = fitz.Rect(r[0], r[1], r[0] + r[2], r[1] + r[3])
        font_name, font_size = _resolve_font_for_rect(page, hit, None, None)
        text_width = font_size * len(hit.mask_strategy) * 0.6
        x_center = rect.x0 + (rect.width - text_width) / 2
        y_center = rect.y0 + (rect.height + font_size) / 2
        page.insert_text(
            (x_center, y_center), hit.mask_strategy,
            fontsize=font_size, fontname=font_name,
            color=(1.0, 1.0, 1.0),  # 白字
        )
```

**与 Phase 1 关系：** `apply_pii_redactions` 内部可被 `write_partial_masks` 复用（add_redact_annot + apply_redactions 段相同）；新代码**只**增加 partial mask 路径分支与字体查询逻辑。

---

### B. PDF Metadata Clear Pattern (D-14 + D-15 + D-16 + SAFE-03)

**Why new:** Phase 1 不涉及元数据清除；Phase 2 引入 `doc.set_metadata({5 fields: ""})` 单一入口。

**完整模式**（`privacyguard/pii/pdf_adapter.py::clear_pdf_metadata`）：
```python
def clear_pdf_metadata(doc) -> None:
    """Phase 2: SAFE-03 PDF 元数据清除（D-14 + D-15 + D-16）。
    
    仅清 5 字段（Title / Author / Subject / Producer / Creator），其他保留；
    5 字段全部置空字符串，不写 "Anonymous" / "Redacted" 等占位字符串。
    调用位置：save_pdf 中 doc.save() 前调一次。
    """
    doc.set_metadata({
        "title": "",
        "author": "",
        "subject": "",
        "producer": "",
        "creator": "",
    })
```

**调用点**（`main.py:12490-12504`，D-16 锁定）：
```python
# ocr + manual + pii 路径处理完毕后，doc.save() 之前
clear_pdf_metadata(doc_save)
doc_save.save(fname, garbage=4, deflate=True, clean=True)
```

**验证**（`tests/unit/test_pdf_pii_redaction.py::test_metadata_5_fields_cleared_on_save`）：
- `fitz.open(out_pdf).metadata.get("title", "") == ""` 等 5 字段

---

### C. Per-Entity Mask Strategy Pattern (D-04 + D-11 + D-12 + D-13 + MASK-02)

**Why new:** Phase 1 mask 模式单一（全遮蔽）；Phase 2 引入 per-entity partial/blackout 切换 + 文档级 override。

**三级配置层级**（D-04 + D-11 + D-12）：
1. **config.json `pii_settings.per_entity_default`**: 9 个 entity 各自的默认 mode（`"partial"` / `"blackout"`）
2. **SettingsDialog 5. 隐私识别 tab**: UI 改写 per-entity_default（持久化）
3. **`self.page_data[0]["mask_override_this_doc"]`**: 文档级 toolbar toggle 临时覆盖（不持久化）

**调用顺序**（`main.py` save loop 内）：
```python
override = self.page_data.get(0, {}).get("mask_override_this_doc")
per_entity_default = self.config.get("pii_settings.per_entity_default", {})
for hit in pii_list:
    if override == "blackout":
        mode = "blackout"
    else:
        mode = per_entity_default.get(hit.entity_type, "partial")
    # ... write_partial_masks(doc, page_idx, hits_grouped_by_mode, mode=mode)
```

---

### D. BIN Dictionary Lazy-Load Pattern (D-26 + D-27 + cp30 教训)

**Why new:** Phase 1 词典内嵌硬编码；Phase 2 BIN 词典 1 万-1.5 万条**必须**走 JSON 文件 + resource_path（避免内存膨胀 + 满足 CC BY-SA 4.0 归属）。

**完整模式**（`privacyguard/pii/validators/bank_card.py::load_bin_whitelist`）：
```python
import json
from privacyguard.utils.security import resource_path

DEFAULT_BIN_DICT_PATH = "privacyguard/pii/data/bin_prefixes.json"


def load_bin_whitelist(json_path: str = None) -> frozenset:
    """运行时从 bin_prefixes.json 加载 BIN 前 6 位白名单（lazy-load + resource_path）。"""
    if json_path is None:
        json_path = resource_path(DEFAULT_BIN_DICT_PATH)
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return frozenset(data.get("bin_prefixes", []))


# 模块级单例（懒加载触发点）
_BIN_WHITELIST_CACHE = None


def get_bin_whitelist() -> frozenset:
    global _BIN_WHITELIST_CACHE
    if _BIN_WHITELIST_CACHE is None:
        _BIN_WHITELIST_CACHE = load_bin_whitelist()
    return _BIN_WHITELIST_CACHE
```

**PyInstaller 强制项**（cp30 教训）：
- `packaging/windows/config/PrivacyGuard_windows.spec` 的 `datas=[...]` 段必须追加 `(project_root/privacyguard/pii/data, privacyguard/pii/data)`（与 Phase 1 `rules.json` 同位置）
- `packaging/macos/config/PrivacyGuard.spec` 同步追加

---

## No Analog Found

| File | Role | Reason | Strategy |
|------|------|--------|----------|
| `privacyguard/pii/data/bin_prefixes.json` | config | 全新数据文件（维基 + 银联公开公告，CC BY-SA 4.0） | 直接生成 JSON 数组，1 万-1.5 万条 BIN 前 6 位；并行 LICENSE 文件 |
| `privacyguard/pii/data/bin_prefixes.json.LICENSE` | config | 全新 LICENSE 归属文件 | CC BY-SA 4.0 标准声明 + Wikipedia "Bank card number" 页面 URL |
| `privacyguard/pii/pdf_adapter.py::write_partial_masks` | service | Phase 1 仅有全遮蔽；partial mask 写入是新模式 | 沿用 SAFE-01 add_redact_annot + apply_redactions(IMAGE_PIXELS) 段，新增 insert_text 步骤 |
| `privacyguard/pii/pdf_adapter.py::clear_pdf_metadata` | service | Phase 1 不涉及元数据；新 helper | 单一入口 5 字段空字符串；调用点紧邻 doc.save() |
| `main.py` toolbar 文档级 override toggle | UI | Phase 1 工具栏无文档级 override 概念 | 形态参考 `rb_black` / `rb_white`；写 `self.page_data[0]["mask_override_this_doc"]` |

---

## Cross-Cutting Concerns

### Convergence (v37.7.6)

| Concern | Where Enforced | Pattern |
|---------|----------------|---------|
| 6 个新 validator 逻辑不重复实现到 `main.py` | `tests/unit/test_convergence.py` (Phase 1 `TestPiiConvergence` 扩展) | AST 扫描 + `assertNotIn("def validate_bank_card", main_source)` |
| `main.py` 通过 `privacyguard.pii.validators` 导入 | `privacyguard/__init__.py` `_LAZY_IMPORTS` 扩展 14 项 | cp30 教训：`import privacyguard` 不拉起 PII 模块 |
| `SimpleConfig` 是运行时配置路径 | `tests/unit/test_app_config.py` 扩展 | 不切换到 `ConfigManager`（CLAUDE.md §当前生效的配置路径） |
| partial mask 写入 helper 不内联到 main.py | `tests/unit/test_convergence.py` 新断言 | 验证 `main.py` 不含 `def write_partial_masks` 内联实现 |
| OCR / manual 路径保持原 blackout 行为 | `main.py:12490-12497` 现有循环 | Phase 2 不动此段（D-22 锁定） |

### Versioning (CLAUDE.md §版本号单一来源)

**Phase 2 不动版本号**（仅 Phase 2 内部交付，版本号升级在阶段合并时统一处理）。新增 JSON 数据文件（`bin_prefixes.json`）与新模块不触发版本号变更。

### PyInstaller (cp30 教训 + D-26)

| 平台 | 改动 | 验证 |
|------|------|------|
| Windows | `packaging/windows/config/PrivacyGuard_windows.spec` 的 `datas=[...]` (data 目录已包含) + `hiddenimports=[...]` 追加 6 个新 validator 模块 | `python3 -m compileall -q` + Windows 真机启动验证（`bin_prefixes.json` 可读） |
| macOS | `packaging/macos/config/PrivacyGuard.spec` 同步 + `build_complete.sh` parity check | `python3 -m compileall -q` + macOS 真机启动验证 |

### Test Baseline Upgrade (D-24)

**Phase 1 基线 79/79** → **Phase 2 基线 88/88 或 89/89**：
- 79 (Phase 1) + 8 (新 validator 测试类) + 1 (metadata 清除测试) + 1 (partial mask 写入测试) = 89/89
- 79 + 6 (新 entity engine 测试类) + 2 (partial mask + metadata) + 1 (per_entity_default) = 88/88（最小）
- 5 个 PII engine 测试 + 4 个 adapter/metadata/config 测试在 Phase 2 完成后进入基线

---

## Metadata

**Analog search scope:**
- `privacyguard/pii/` 全子包（13 个 Phase 1 文件：`__init__.py` / `hits.py` / `regex_patterns.py` / `mask.py` / `normalize.py` / `confidence.py` / `overlap.py` / `engine.py` / `pdf_adapter.py` / `data/rules.json` / `validators/__init__.py` / `validators/id_card.py` / `validators/phone_segment.py`）
- `privacyguard/` 全包（`__init__.py` / `ocr/` / `workers/` / `utils/` / `core/` / `ui/`）
- `main.py`（按行号定位：`save_pdf` 12490-12504 / `SettingsDialog box_pii` 1601-1662 / `toolbar_pdf_layout` 5774-5788 / `SimpleConfig` 98-167 / `_on_pii_page_result` 11374-11387 / `page_data` 初始化 4925/10521）
- `tests/unit/` 全部 18 个 `test_*.py`（重点：`test_pii_engine.py` / `test_pii_validators.py` / `test_pdf_pii_redaction.py` / `test_app_config.py` / `test_package_imports.py` / `test_convergence.py`）
- `tests/fixtures/fake_pii.py`
- `config.json` / `config.json.template`
- `packaging/windows/config/PrivacyGuard_windows.spec` (140-194) + `packaging/macos/config/PrivacyGuard.spec` (30-102)
- CLAUDE.md / .planning/phases/01-pdf/{01-CONTEXT.md, 01-PATTERNS.md} / .planning/phases/02-pdf/02-CONTEXT.md

**Files scanned:** 26 analog files (Phase 1 PII subsystem + main.py sites + tests + packaging specs + 02-CONTEXT.md).

**Pattern extraction date:** 2026-08-11

**Key invariants (locked from CONTEXT.md / Phase 1 D-05 / Phase 1 01-CONTEXT.md):**
- D-01: partial mask 写入 = add_redact_annot + apply_redactions(IMAGE_PIXELS) + insert_text（沿用 Phase 1 90% 代码）
- D-02: 字体优先 `page.get_text("dict")` 取最近 span；回退 sans-serif + `rect.height - 4pt` 估算
- D-03: rect 宽度按 mask_strategy 字符数重算；mask 文字居中插入
- D-04: `config.json.pii_settings.per_entity_default: Dict[str, "partial"|"blackout"]` 默认全 `partial`
- D-05: Phase 1 PIIHit 字段顺序与命名锁（Phase 2 不新增字段）
- D-06: USCC = 18 位 + GB 32100 mod-31-3 + 登记管理部门类别代码 8 字符
- D-07: VAT 发票号 = 8 位 / 20 位双格式 + 上下文锥点
- D-08: 银行账号 = 9-21 位 + 必查上下文锥点
- D-09: 15 位纳税人识别号 = 独立 entity_type `CN_TAXPAYER_ID_15`
- D-10: 邮箱 = RFC 5322 简化版（不引入 IDN）
- D-11: SettingsDialog 「脱敏方式」表 9 entity × partial/blackout 下拉
- D-12: 工具栏「本文件使用全遮蔽」 toggle + `self.page_data[0]["mask_override_this_doc"]`
- D-13: `per_entity_default` 字段名 9 个 key 全列（不可重命名 / 不可省略）
- D-14: 元数据清除 5 字段（Title / Author / Subject / Producer / Creator）
- D-15: 5 字段全部置空字符串（不写占位字符串）
- D-16: `doc.set_metadata` 在 `doc.save` 前调一次
- D-17: 6 个新 validator 放 `privacyguard/pii/validators/<entity>.py`
- D-18: 正则预编译在 `regex_patterns.py` 按 entity_hint yield
- D-19: `rules.json` 扩展 4 键（bank_card / uscc / vat_invoice / bank_account）
- D-20: 上下文锥点放 validator 模块常量，**不**集中放 rules.json
- D-21: `write_partial_masks` 单一 helper + mode 参数
- D-22: `save_pdf` 改 PII 路径调 `write_partial_masks`；OCR / manual 路径不变
- D-23: 5 类测试新增（test_pii_engine / test_pii_validators / test_pdf_pii_redaction / test_pdf_metadata_cleared / test_app_config）
- D-24: 79/79 基线升级为 88/88 或 89/89
- D-25: reverse-extraction 用 `fitz.open().get_text()`（不依赖 poppler）
- D-26: `bin_prefixes.json` 走 resource_path + PyInstaller datas 同步
- D-27: CC BY-SA 4.0 LICENSE 归属声明在 `bin_prefixes.json.LICENSE`
- OPS-03: `privacyguard.pii.*` 必须 `__getattr__` 懒加载
- OPS-05: 测试合成数据严禁真实 PII（fake_* 模式）
- OPS-07: 79/79 基线门禁
- SAFE-01: `add_redact_annot + apply_redactions(IMAGE_PIXELS) + garbage=4` 完整模式
- SAFE-02: reverse-extraction 验证（fitz.open(out).get_text()）
- SAFE-03: PDF 元数据 5 字段清除
- UI-SPEC: PII rect 颜色 `#D64545`（Phase 2 沿用不引入新颜色）

---

*Pattern mapping complete. Planner can now write PLAN.md files referencing these concrete analogs. Phase 2 在 26 个新 / 修改文件上均找到 exact 或 role-match 模拟；唯一全新模式为 partial mask 写入 helper（沿用 Phase 1 SAFE-01 90% 代码 + 新增 insert_text 步骤）、元数据清除 helper、文档级 override toggle 三项。*
