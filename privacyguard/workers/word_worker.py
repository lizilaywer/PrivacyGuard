"""
Word 文档处理 Worker

v36.5: 模块化拆分，从 main.py 提取
"""

import time
import copy
import re
from PyQt6.QtCore import QThread, pyqtSignal

# 常量定义
PROGRESS_UPDATE_INTERVAL = 0.05


class WordWorker(QThread):
    """Word 文档智能脱敏线程

    v36.5: 模块化拆分
    """
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int)

    def __init__(self, word_doc, word_data, rules, custom_keywords, replacement_text, default_rules=None):
        super().__init__()
        self.word_doc = word_doc
        self.word_data = word_data
        self.rules = rules
        raw_keywords = custom_keywords.replace('\n', ' ').split()
        self.custom_keywords = [re.escape(k.strip()) for k in raw_keywords if k.strip()]
        self.replacement_text = replacement_text
        self.default_rules = default_rules or {}

    def run(self):
        """主处理流程 - 支持取消并保存进度（v36.3）"""
        try:
            # 统计总数（段落 + 表格单元格）
            total_paragraphs = len(self.word_doc.paragraphs)
            total_tables = len(self.word_doc.tables)
            total_cells = sum(len(table.rows) * len(table.columns) for table in self.word_doc.tables)
            total = total_paragraphs + total_cells
            processed = 0
            last_emit_time = 0

            # 处理段落
            for idx, para in enumerate(self.word_doc.paragraphs):
                if self.isInterruptionRequested():
                    break  # 保留已处理结果

                key = f'paragraph_{idx}'
                if key in self.word_data:
                    text = self.word_data[key]['text']
                    matches = self._find_matches(text)
                    self.word_data[key]['ocr'] = matches

                processed += 1
                self._emit_progress(processed, total, last_emit_time)
                last_emit_time = time.time()

            # 处理表格（仅在未取消时继续）
            if not self.isInterruptionRequested():
                for table_idx, table in enumerate(self.word_doc.tables):
                    if self.isInterruptionRequested():
                        break  # 保留已处理结果

                    for row_idx, row in enumerate(table.rows):
                        for cell_idx, cell in enumerate(row.cells):
                            key = f'table_{table_idx}_cell_{row_idx}_{cell_idx}'
                            if key in self.word_data:
                                text = self.word_data[key]['text']
                                matches = self._find_matches(text)
                                self.word_data[key]['ocr'] = matches

                            processed += 1
                            self._emit_progress(processed, total, last_emit_time)
                            last_emit_time = time.time()

            # 发射已扫描的结果（无论完成与否）
            # v36.5: 发送深拷贝避免数据竞争
            self.finished_signal.emit(copy.deepcopy(self.word_data))

        except (IOError, OSError, RuntimeError, ValueError,
                AttributeError, KeyError, IndexError) as e:
            print(f"Word扫描错误: {e}")
            # 出错时也返回已处理结果
            self.finished_signal.emit(copy.deepcopy(self.word_data))

    def _emit_progress(self, processed, total, last_emit_time):
        """背压控制的进度更新"""
        current_progress = int(processed / total * 100)
        current_time = time.time()
        if current_time - last_emit_time > PROGRESS_UPDATE_INTERVAL or processed == total:
            self.progress_signal.emit(current_progress)

    def _find_matches(self, text):
        """查找匹配的敏感信息"""
        matches = []
        all_patterns = self.rules + self.custom_keywords

        for pattern in all_patterns:
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    matches.append({
                        'pattern': pattern,
                        'rule_name': self._get_rule_name(pattern),
                        'start': match.start(),
                        'end': match.end(),
                        'text': match.group(),
                        'replacement': self.replacement_text
                    })
            except re.error:
                # 忽略无效的正则表达式
                pass

        return matches

    def _get_rule_name(self, pattern):
        """根据模式获取规则名称"""
        for name, pat in self.default_rules.items():
            if pat == pattern:
                return name
        return "自定义"
