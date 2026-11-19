"""Versioned bounded JSON templates, explicit file plans and placeholders."""
import copy
import json
import os

from .helpers_word_rules import normalize_word_replace_rules, validate_word_replace_rules

SCHEMA_VERSION = 2
MAX_BYTES = 1024 * 1024


def validate_template(data):
    if not isinstance(data, dict) or type(data.get("version", 1)) is not int or data.get("version", 1) not in (1, SCHEMA_VERSION):
        raise ValueError("不支持的模板版本，请使用版本 1 或 2。")
    if set(data) - {"version", "schema", "name", "default_replacement_text", "rules"}:
        raise ValueError("模板含不支持的字段。")
    if data.get("schema", "privacyguard.word-rules") != "privacyguard.word-rules":
        raise ValueError("这不是 Word 规则模板。")
    rules = data.get("rules")
    default = data.get("default_replacement_text", "[已脱敏]")
    if not isinstance(default, str) or len(default) > 2048 or not isinstance(rules, list) or len(rules) > 200:
        raise ValueError("模板最多 200 条规则，替换文字最多 2048 字。")
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) - {"enabled", "mode", "find", "replace"}:
            raise ValueError("规则结构不符合格式。")
        if type(rule.get("enabled", True)) is not bool or rule.get("mode", "exact") not in ("exact", "regex"):
            raise ValueError("启用状态或匹配模式无效。")
        for key, limit in (("find", 2048), ("replace", 2048)):
            if not isinstance(rule.get(key, ""), str) or len(rule.get(key, "")) > limit:
                raise ValueError("规则文本过长或类型无效。")
        if rule.get("enabled", True) and not rule.get("find", "").strip():
            raise ValueError("启用规则的查找词不能为空。")
    normalized = normalize_word_replace_rules(rules, default)
    if validate_word_replace_rules(normalized):
        raise ValueError("模板含无效正则，请修正后再导入。")
    return {"version": SCHEMA_VERSION, "schema": "privacyguard.word-rules",
            "default_replacement_text": default or "[已脱敏]", "rules": normalized}


def read_template(path):
    with open(path, "rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("模板文件不能超过 1 MB。")
    try:
        return validate_template(json.loads(raw.decode("utf-8-sig")))
    except (UnicodeError, RecursionError) as error:
        raise ValueError("模板编码或结构无效。") from error


def write_template(path, rules, default):
    from .export_transaction import AtomicExport
    payload = validate_template({"version": SCHEMA_VERSION, "rules": rules, "default_replacement_text": default})
    with AtomicExport(path) as output:
        output.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        output.commit()


def preset_rules(name):
    # No names or linked entities are guessed. Presets are editable starting
    # points, with deliberately bounded expressions and neutral replacements.
    phone = {"enabled": True, "mode": "regex", "find": r"(?<!\d)1[3-9]\d{9}(?!\d)", "replace": "[手机号]"}
    identity = {"enabled": True, "mode": "regex", "find": r"(?<!\d)[1-6]\d{5}(?:19|20)\d{2}[01]\d[0-3]\d{4}[\dXx](?!\d)", "replace": "[证件号]"}
    if name not in ("卷宗", "合同", "流水", "人事"):
        raise ValueError("未知模板。")
    return copy.deepcopy([phone] if name == "流水" else [phone, identity])


def consistent_rules(rules, prefix="当事人"):
    normalized = normalize_word_replace_rules(rules)
    output, identities = [], {}
    for rule in normalized:
        item = dict(rule)
        if item["enabled"] and item["mode"] == "exact":
            key = item["find"].casefold()
            if key not in identities:
                identities[key] = len(identities) + 1
            item["replace"] = prefix + str(identities[key])
        output.append(item)
    return output


def canonical_file(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def validate_file_plan(files, mapping, default_rules):
    allowed = {canonical_file(path) for path in files}
    if not isinstance(mapping, dict) or set(mapping) - allowed:
        raise ValueError("逐文件计划包含未选择的文件。")
    result = {}
    for path in files:
        key = canonical_file(path)
        rules = mapping.get(key, default_rules)
        result[key] = None if rules is None else validate_template({"rules": rules})["rules"]
    return result


def plan_has_rules(mapping, common):
    groups = mapping.values() if mapping is not None else [common]
    return any(rule.get("enabled", True) and rule.get("find") for rules in groups if rules for rule in rules)
