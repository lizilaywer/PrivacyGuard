"""Word 批量替换 Worker（从 main.py 提取）。

同一套规则应用全部文件，支持 .doc/.docx，错误交互决策（skip/stop）。
"""

import os
import time
import shutil
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from privacyguard.utils.security import validate_safe_path
from privacyguard.utils.exceptions import ConversionError
from privacyguard.utils.doc_converter import convert_doc_to_docx as _shared_convert_doc_to_docx
from privacyguard.utils.helpers_word_rules import (
    normalize_word_replace_rules,
)



class WordBatchReplaceWorker(QThread):
    """Word 批量替换线程（同一套规则应用全部文件）。"""

    progress_signal = pyqtSignal(int, int, str)      # processed, total, current_file
    file_done_signal = pyqtSignal(str, str)          # input_path, output_path
    file_error_signal = pyqtSignal(int, str, str)    # index, input_path, error_msg
    finished_signal = pyqtSignal(dict)               # summary

    def __init__(self, file_paths, rules, default_replacement_text, parent=None, file_plan=None, private_rule_mapping=False):
        # v40.1.4 修复：补 parent 形参——main.py 调用点（批量替换）传 parent=self，
        # 此前模块层无此形参导致构造即 TypeError（与 OCRWorker 同款潜伏 Bug）。
        super().__init__(parent)
        self.file_paths = list(file_paths or [])
        self.rules = normalize_word_replace_rules(rules or [], default_replacement_text)
        self.default_replacement_text = default_replacement_text if isinstance(default_replacement_text, str) and default_replacement_text else "[已脱敏]"
        self._error_decision = None
        self._decision_event = threading.Event()
        self._decision_lock = threading.Lock()
        self._temp_dirs = []
        from privacyguard.utils.rule_templates import validate_file_plan
        self.file_plan = validate_file_plan(self.file_paths, file_plan, self.rules) if file_plan is not None else None
        self.private_rule_mapping = private_rule_mapping or file_plan is not None

    def provide_error_decision(self, decision):
        """主线程调用：为当前错误设置决策（skip/stop）。"""
        with self._decision_lock:
            self._error_decision = decision
        self._decision_event.set()

    def _wait_for_error_decision(self):
        """等待主线程选择错误处理策略。"""
        while not self._decision_event.wait(0.1):
            if self.isInterruptionRequested():
                return "stop"
        with self._decision_lock:
            decision = self._error_decision or "skip"
            self._error_decision = None
            self._decision_event.clear()
        return decision

    def run(self):
        summary = {
            "total": len(self.file_paths),
            "processed": 0,
            "success": [],
            "failed": [],
            "stopped": False,
            "rules": [] if self.private_rule_mapping else list(self.rules),
            "skipped": [],
            "private_rule_mapping": self.private_rule_mapping,
        }

        try:
            total = len(self.file_paths)
            for idx, file_path in enumerate(self.file_paths):
                if self.isInterruptionRequested():
                    summary["stopped"] = True
                    break

                current_name = os.path.basename(file_path)
                self.progress_signal.emit(idx, total, current_name)
                from privacyguard.utils.rule_templates import canonical_file
                file_rules = self.file_plan.get(canonical_file(file_path)) if self.file_plan is not None else self.rules
                if file_rules is None:
                    summary["skipped"].append(file_path)
                    self.progress_signal.emit(idx + 1, total, current_name)
                    continue

                try:
                    output_path, replace_stats = (self._process_single_file(file_path, file_rules=file_rules)
                                                 if self.file_plan is not None else self._process_single_file(file_path))
                    summary["success"].append({
                        "input": file_path,
                        "output": output_path,
                        "total_replacements": max(0, int(replace_stats.get("total_replacements", 0) or 0))
                        if isinstance(replace_stats, dict) else 0,
                        "rule_counts": replace_stats.get("rule_counts", []) if isinstance(replace_stats, dict) else [],
                    })
                    self.file_done_signal.emit(file_path, output_path)
                except Exception as e:
                    # W6: 兜底捕获全部异常（含 PackageNotFoundError 等未显式列出的类型），
                    # 否则单文件异常会逃出 run()，finished_signal 永不发射，批量 UI 永久卡死
                    error_msg = str(e)
                    summary["failed"].append({
                        "input": file_path,
                        "error": error_msg
                    })
                    self.file_error_signal.emit(idx, file_path, error_msg)
                    decision = self._wait_for_error_decision()
                    if decision == "stop":
                        summary["stopped"] = True
                        break
                finally:
                    self.progress_signal.emit(idx + 1, total, current_name)

            summary["processed"] = len(summary["success"]) + len(summary["failed"]) + len(summary["skipped"])
            self.finished_signal.emit(summary)
        finally:
            self._cleanup_temp_dirs()

    def _process_single_file(self, file_path, file_rules=None):
        from docx import Document

        is_safe, error_msg = validate_safe_path(file_path, allowed_extensions=[".doc", ".docx"])
        if not is_safe:
            raise ConversionError("输入文件路径不安全", error_msg)

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".docx":
            source_docx = file_path
        elif ext == ".doc":
            source_docx = self._convert_doc_to_docx(file_path)
        else:
            raise ConversionError("不支持的文件格式", f"{file_path}")

        doc = Document(source_docx)
        replace_stats = self._apply_rules_to_document(doc, file_rules=file_rules)
        output_path = self._build_output_path(file_path)
        from privacyguard.utils.export_transaction import save_verified_docx
        save_verified_docx(doc, output_path, [file_path, source_docx])
        return output_path, replace_stats

    def _apply_rules_to_document(self, doc, file_rules=None):
        from privacyguard.utils.word_parts import apply_word_rules, map_word_content
        from privacyguard.utils.export_transaction import ExportValidationError
        risks = map_word_content(doc).risks
        unsupported = [key for key in risks if not key.startswith("\u4fee\u8ba2")]
        if unsupported:
            raise ExportValidationError("\u6279\u91cf\u6587\u4ef6\u542b\u672a\u8986\u76d6\u5185\u5bb9\uff0c\u8bf7\u5355\u72ec\u6253\u5f00\u590d\u6838\u3002")
        return apply_word_rules(doc, self.rules if file_rules is None else file_rules, self.default_replacement_text)

    def _build_output_path(self, file_path):
        base_path = os.path.splitext(file_path)[0]
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        candidate = f"{base_path}__replaced_{timestamp}.docx"
        if not os.path.exists(candidate):
            return candidate

        suffix = 1
        while suffix <= 9999:
            candidate_with_suffix = f"{base_path}__replaced_{timestamp}_{suffix}.docx"
            if not os.path.exists(candidate_with_suffix):
                return candidate_with_suffix
            suffix += 1
        # P2 防御：超过 9999 个同名文件（异常/恶意目录）时避免无界循环，直接返回带大后缀
        return f"{base_path}__replaced_{timestamp}_{suffix}.docx"

    def _convert_doc_to_docx(self, doc_path):
        """v37.7.6: 委托给共享转换模块。"""
        docx_path, temp_dir = _shared_convert_doc_to_docx(doc_path)
        self._temp_dirs.append(temp_dir)
        return docx_path

    def _cleanup_temp_dirs(self):
        for temp_dir in list(self._temp_dirs):
            try:
                if os.path.isdir(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except (OSError, IOError):
                pass
        self._temp_dirs.clear()
