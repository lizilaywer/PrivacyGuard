"""cp90: 清理使用痕迹对话框（隐私功能：本机不留痕）"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class _TraceSizeWorker(QThread):
    """cp90: 后台计算各痕迹项大小，避免大缓存目录阻塞 UI。"""
    sizes_ready = pyqtSignal(list)  # [(key, size_bytes)]

    def __init__(self, items, parent=None):
        # cp118: 接受 parent，由 Qt 对话框持有，避免对话框关闭后线程被销毁
        super().__init__(parent)
        self._items = items

    def run(self):
        from privacyguard.trace_cleaner import dir_size_bytes
        out = []
        for it in self._items:
            total = 0
            for p in it.get("paths", []):
                total += dir_size_bytes(p)
            out.append((it["key"], total))
        self.sizes_ready.emit(out)


class TraceCleanDialog(QDialog):
    """cp90: 清理使用痕迹对话框（隐私功能：本机不留痕）。

    items: collect_trace_items 产出；无有效路径的项隐藏。
    allowed_roots: 白名单根目录（硬约束）。
    """

    def __init__(self, parent, items, allowed_roots, main_window=None):
        """cp118: 新增 main_window 参数，显式传入 MainWindow 引用用于回调，
        不再依赖 Qt parent 路由（从设置窗口进入时 parent 是 SettingsDialog，
        会导致 _mark_webengine_clear_pending / _on_traces_cleaned 静默跳过）。
        向后兼容：main_window 为 None 时回退到旧行为（从 parent 查找）。
        """
        super().__init__(parent)
        self.setWindowTitle("清理使用痕迹")
        self.resize(460, 340)
        self._items = items
        self._allowed_roots = allowed_roots
        self._rows = {}  # key -> (checkbox, size_label)
        self._size_worker = None
        # cp118: 显式 MainWindow 引用优先；None 时回退 parent()（保持旧行为）
        self._main_window = main_window if main_window is not None else parent

        from privacyguard.trace_cleaner import format_size
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(12)

        note = QLabel("清理本应用在本机留下的使用痕迹（仅限本应用自有数据，不会触碰你的文档）。")
        note.setWordWrap(True)
        layout.addWidget(note)

        for it in items:
            if not it.get("paths"):
                continue  # 无路径（如 WebEngine 未启用）隐藏
            row = QHBoxLayout()
            cb = QCheckBox(it["label"])
            cb.setChecked(bool(it.get("default_checked")))
            size_lbl = QLabel(format_size(it.get("size_bytes", 0)))
            size_lbl.setStyleSheet("color: #6B7280;")
            size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(cb, 1)
            row.addWidget(size_lbl, 0)
            layout.addLayout(row)
            self._rows[it["key"]] = (cb, size_lbl)

        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_cancel)
        btn_clean = QPushButton("清理所选")
        btn_clean.setObjectName("settingsPrimaryButton")
        btn_clean.clicked.connect(self._do_clean)
        actions.addWidget(btn_clean)
        layout.addLayout(actions)

        # 后台重算大小（首屏先用 collect 时的粗算值，线程回填精确值）
        # cp118: worker 以对话框为 parent，生命周期与对话框绑定
        self._size_worker = _TraceSizeWorker(items, parent=self)
        self._size_worker.sizes_ready.connect(self._on_sizes_ready)
        self._size_worker.start()

    def _on_sizes_ready(self, sizes):
        from privacyguard.trace_cleaner import format_size
        size_map = dict(sizes)
        for it in self._items:
            if it["key"] in size_map:
                it["size_bytes"] = size_map[it["key"]]
        for key, (_cb, lbl) in self._rows.items():
            if key in size_map:
                lbl.setText(format_size(size_map[key]))

    def _shutdown_worker(self):
        """cp118: 安全停止大小计算线程，避免对话框关闭时 QThread 运行中被销毁。

        worker 仅做只读目录遍历，无法中途取消；此处请求中断后等待其自然结束，
        超时 3s 后不再阻塞 UI（worker 以对话框为 parent，由 Qt 接管回收）。
        """
        worker = getattr(self, "_size_worker", None)
        if worker is None:
            return
        try:
            if worker.isRunning():
                worker.requestInterruption()
                worker.wait(3000)
        except Exception:
            pass

    def closeEvent(self, event):
        """cp118: 关闭前等待后台线程退出，防止运行中销毁导致 qFatal。"""
        self._shutdown_worker()
        super().closeEvent(event)

    def reject(self):
        """cp118: Esc/取消 关闭路径同样需等待线程。"""
        self._shutdown_worker()
        super().reject()

    def accept(self):
        """cp118: 确认关闭路径同样需等待线程。"""
        self._shutdown_worker()
        super().accept()

    def _do_clean(self):
        from privacyguard.trace_cleaner import clean_paths, format_size
        selected = [it for it in self._items
                    if it["key"] in self._rows and self._rows[it["key"]][0].isChecked()]
        if not selected:
            self.reject()
            return
        # 草稿项额外提醒（未完成进度丢失）
        extra = '\n\n⚠ "脱敏进度草稿"将被清除，未完成的脱敏进度将丢失。' \
            if any(it["key"] == "sessions" for it in selected) else ""
        reply = QMessageBox.question(
            self, "确认清理",
            "将清理所选使用痕迹（不影响你已导出/保存的文件）。\n确定继续？" + extra,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        total_deleted = 0
        total_freed = 0
        all_errors = []
        webengine_occupied = False
        for it in selected:
            deleted, freed, errors = clean_paths(it["paths"], self._allowed_roots)
            total_deleted += deleted
            total_freed += freed
            all_errors.extend(errors)
            if it["key"] == "webengine" and errors:
                webengine_occupied = True
        # 回调主窗处理 WebEngine 占用（写 pending 标记）+ 草稿清后刷新状态
        # cp118: 优先用显式传入的 _main_window（解决从设置窗口进入时 parent 是
        # SettingsDialog 导致回调方法找不到的问题）
        main_win = self._main_window
        if webengine_occupied and hasattr(main_win, "_mark_webengine_clear_pending"):
            main_win._mark_webengine_clear_pending()
        if hasattr(main_win, "_on_traces_cleaned"):
            main_win._on_traces_cleaned([it["key"] for it in selected])

        msg = f"已清理 {total_deleted} 项，释放 {format_size(total_freed)}。"
        if webengine_occupied:
            msg += "\n部分预览缓存正在使用，将在下次启动时清除。"
        elif all_errors:
            msg += f"\n{len(all_errors)} 项未能删除（可能正在使用）。"
        QMessageBox.information(self, "完成", msg)
        self.accept()
