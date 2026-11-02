"""
Word 文档处理 Worker

v36.5: 模块化拆分，从 main.py 提取
"""

import time
import copy
import re
from PyQt6.QtCore import QThread, pyqtSignal

from privacyguard.utils.logger import get_logger

logger = get_logger("word_worker")

# 常量定义
PROGRESS_UPDATE_INTERVAL = 0.05


class WordWorker(QThread):
    """Word 文档智能脱敏线程

    v36.5: 模块化拆分
    """
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int)

    def __init__(self, word_doc, word_data, rules, custom_keywords, replacement_text, default_rules=None, parent=None):
        super().__init__(parent)
        self.word_doc = word_doc
        self.word_data = word_data
        self.rules = list(rules or [])
        # 安全修复: custom_keywords 可能为 None（与 OCRWorker 一致的 None 守卫）
        raw_keywords = (custom_keywords or "").replace('\n', ' ').split()
        self.custom_keywords = [re.escape(k.strip()) for k in raw_keywords if k.strip()]
        self.replacement_text = replacement_text
        self.default_rules = default_rules or {}

    def run(self):
        """主处理流程 - 支持取消并保存进度（v36.3）

        W2: 通用遍历 word_data 全部文本条目（含页眉/页脚），而非仅 doc.paragraphs/tables，
            确保打开时纳入的页眉页脚键也会被智能扫描。
        W4: 子线程只写本地副本 output，绝不原地修改共享的 self.word_data，消除数据竞争。
        cp_person_name: 启用称谓人名规则时先做收集 pass（全文档收集人名集合），
            再在逐条匹配中对全部条目精确遮该人名（Word 字符偏移天然支持全文档级）。
        """
        processed = 0
        total = 0
        output = None
        error_type = None
        try:
            # W4: 先深拷贝一份本地副本，扫描结果只写入本地副本
            output = copy.deepcopy(self.word_data)
            # W2: 遍历所有含 'text' 的条目（段落 / 表格单元格 / 页眉页脚）
            keys = [
                k for k, v in output.items()
                if k != '__scan_meta__' and isinstance(v, dict) and 'text' in v
            ]
            total = len(keys)
            last_emit_time = 0

            # cp_person_name 收集 pass：全文档扫描称谓人名（仅当规则启用）
            person_names = self._collect_person_names(output, keys)

            for key in keys:
                if self.isInterruptionRequested():
                    break  # 保留已处理结果

                text = output[key].get('text', '')
                output[key]['ocr'] = self._find_matches(text, person_names)

                processed += 1
                # B1: last_emit_time 只在真正发射时才更新（由 _emit_progress 返回）
                last_emit_time = self._emit_progress(processed, total, last_emit_time)

        except Exception as e:
            # P1-4 安全加固：仅记异常类型，不记原始 message（可能含命中 PII）
            logger.error("Word 扫描错误: %s", type(e).__name__)
            error_type = type(e).__name__
        finally:
            # P1-4: 无论成功 / 取消 / 异常（含 deepcopy 失败），始终发射 finished_signal，
            # 避免 UI 永久卡死（对齐 OCRWorker try/except/finally gold-standard）。
            if output is None:
                output = {}
            output['__scan_meta__'] = {
                'processed_items': processed,
                'total_items': total,
                'cancelled': self.isInterruptionRequested(),
                'error_type': error_type,
            }
            self.finished_signal.emit(output)

    def _collect_person_names(self, output, keys):
        """cp_person_name: 收集 pass——遍历全部条目文本，用称谓 pattern 收集人名集合。

        规则未启用（rules 里无 lead 命名组 pattern）时直接返回空集，零开销。
        """
        person_patterns = [p for p in (self.rules or []) if "(?P<lead>" in p]
        if not person_patterns:
            return set()
        from privacyguard.ocr.person_name import find_person_names_by_pattern
        names = set()
        for key in keys:
            text = output[key].get('text', '')
            if not text:
                continue
            for p in person_patterns:
                for name, _s, _e in find_person_names_by_pattern(text, p):
                    names.add(name)
        return names

    def _emit_progress(self, processed, total, last_emit_time):
        """背压控制的进度更新

        B1: last_emit_time 只在真正发射时更新并返回，否则每轮循环都被刷新，
            导致快速处理时进度永不更新、节流完全失效。
        """
        current_progress = int(processed / total * 100)
        current_time = time.time()
        if current_time - last_emit_time > PROGRESS_UPDATE_INTERVAL or processed == total:
            self.progress_signal.emit(current_progress)
            return current_time
        return last_emit_time

    def _find_matches(self, text, person_names=None):
        """查找匹配的敏感信息

        v37.7.19 cp57: 银行卡号路径增加 Luhn 校验（与 text_pdf.py / mixed_pdf.py 一致），
        避免案件编号、日期串等 13-19 位数字被误匹配为银行卡号。
        v37.7.19 cp57: Luhn 校验限定为仅银行卡号 pattern 生效，避免过滤自定义正则。
        cp_person_name: 带 pgname 命名组的称谓 pattern 命中时取人名子串（refine
        修正 span 后），rule_name 直接为"称谓人名"；收集 pass 发现的人名集合
        对本条文本精确 finditer（全文档遮语义），与称谓处子串命中按 span 去重。
        """
        matches = []
        seen_spans = set()
        all_patterns = self.rules + self.custom_keywords

        # cp57: 延迟导入，避免循环依赖
        from privacyguard.ocr.text_pdf import _is_valid_luhn, _looks_like_idcard, _is_bank_card_pattern, verify_hit_by_pattern, _mask

        def _append_match(pattern, rule_name, start, end, matched_text):
            span_key = (start, end)
            if span_key in seen_spans:
                return
            seen_spans.add(span_key)
            matches.append({
                'pattern': pattern,
                'rule_name': rule_name,
                'start': start,
                'end': end,
                'text': matched_text,
                'replacement': self.replacement_text
            })

        for pattern in all_patterns:
            # cp_person_name: 称谓人名 pattern 分流——取人名子串，跳过 Luhn/校验位
            if "(?P<lead>" in pattern:
                from privacyguard.ocr.person_name import (
                    find_person_names_by_pattern, PERSON_NAME_RULE_NAME,
                )
                for _name, s, e in find_person_names_by_pattern(text, pattern):
                    _append_match(pattern, PERSON_NAME_RULE_NAME, s, e, text[s:e])
                continue
            try:
                # cp57: 仅对银行卡号 pattern 执行 Luhn 校验
                is_bank_card_pattern = _is_bank_card_pattern(pattern)
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matched_text = match.group()
                    # cp57: 13-19 位纯数字串增加 Luhn 校验（仅银行卡号 pattern，排除身份证号）
                    if is_bank_card_pattern and len(matched_text) >= 13 and len(matched_text) <= 19 and matched_text.isdigit():
                        if _looks_like_idcard(matched_text):
                            pass  # 身份证号，跳过 Luhn 校验
                        elif not _is_valid_luhn(matched_text):
                            logger.warning("[cp57 WARN] Word 数字串(len=%d %s) 不满足 Luhn 校验，跳过",
                                           len(matched_text), _mask(matched_text))
                            continue
                    # cp70: 统一社会信用代码/VIN 等带校验位 pattern 命中后二次校验
                    if not verify_hit_by_pattern(pattern, matched_text):
                        logger.warning("[cp70 WARN] Word 命中串(len=%d %s) 未通过校验位校验，跳过",
                                       len(matched_text), _mask(matched_text))
                        continue
                    _append_match(pattern, self._get_rule_name(pattern),
                                  match.start(), match.end(), matched_text)
            except re.error:
                # 忽略无效的正则表达式
                pass

        # cp_person_name: 收集 pass 发现的人名 → 本条文本内全部出现处精确遮
        if person_names:
            from privacyguard.ocr.person_name import PERSON_NAME_RULE_NAME
            pn_rule_pattern = next(
                (p for p in self.rules if "(?P<lead>" in p), None
            )
            for name in sorted(person_names):
                try:
                    for match in re.finditer(re.escape(name), text):
                        _append_match(pn_rule_pattern or name, PERSON_NAME_RULE_NAME,
                                      match.start(), match.end(), name)
                except re.error:
                    continue

        return matches

    def _get_rule_name(self, pattern):
        """根据模式获取规则名称"""
        for name, pat in self.default_rules.items():
            if pat == pattern:
                return name
        return "自定义"
