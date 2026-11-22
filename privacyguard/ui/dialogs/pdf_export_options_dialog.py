"""A single optional export choice with a text-free hidden-content inventory."""
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, QRadioButton,
                             QDialogButtonBox, QButtonGroup, QMessageBox)
from PyQt6.QtCore import Qt

from privacyguard.utils.pdf_inventory import inventory_pdf, inventory_summary


class PdfExportOptionsDialog(QDialog):
    def __init__(self, counts, parent=None):
        super().__init__(parent)
        from privacyguard.ui.office_style import apply_office_style
        apply_office_style(self)
        self.setWindowTitle("PDF 导出方式")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        label = QLabel("页面之外发现以下内容：\n" + inventory_summary(counts))
        label.setWordWrap(True)
        layout.addWidget(label)
        self.group = QButtonGroup(self)
        for i, (text, detail) in enumerate((
            ("保持版式（默认）", "保留附加内容；页面批注按既有流程移除。"),
            ("清理隐藏信息", "移除属性、链接、附件和自动动作，保留内部书签；复杂内容会阻止导出。"),
            ("纯图导出", "只保留遮罩后的可见页面，不能选字，体积可能增大。"),
        )):
            button = QRadioButton(text)
            button.setChecked(i == 0)
            self.group.addButton(button, i)
            layout.addWidget(button)
            description = QLabel(detail)
            description.setWordWrap(True)
            layout.addWidget(description)
        note = QLabel("纯图模式不保留书签、表单值、附件及签名。任何修改都可能使原数字签名失效。三种方式均不能代替人工检查是否漏选敏感内容。")
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def choose_pdf_export_policy(parent, document, selected_filter=""):
    counts = inventory_pdf(document)
    # Normal exports with no extra objects keep the familiar one-dialog flow.
    if not any(counts[k] for k in counts if k not in ("metadata", "xml")) and "更多" not in selected_filter:
        return "preserve", "隐藏部件清点（保持版式，未净化附加内容）：\n" + inventory_summary(counts)
    dialog = PdfExportOptionsDialog(counts, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None, ""
    policy = ("preserve", "sanitize", "raster")[dialog.group.checkedId()]
    if policy == "raster" and counts["forms"]:
        reply = QMessageBox.question(parent, "纯图输出不含表单值", "表单值未纳入原页面脱敏，纯图输出将不保留这些值。是否继续？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return None, ""
    return policy, "隐藏部件清点（导出前）：\n" + inventory_summary(counts) + "\n处理方式：" + {"preserve": "保持版式，附加内容未净化", "sanitize": "清理隐藏信息", "raster": "纯图重建，不复制原对象"}[policy]


def confirm_pdf_text_warnings(parent, pages, accepted_pages):
    """Ask once, before the verified temporary file replaces the destination."""
    shown = "、".join(str(page) for page in pages[:10])
    location = f"第 {shown} 页" if len(pages) <= 10 else f"第 {shown} 页等 {len(pages)} 页"
    dialog = QMessageBox(QMessageBox.Icon.Warning, "导出复查提醒",
                         f"{location}的遮罩区域检测到额外文字，可能仍有原文。"
                         "\n你可以返回复核，或保存当前结果。", parent=parent)
    go_back = dialog.addButton("返回复核", QMessageBox.ButtonRole.RejectRole)
    proceed = dialog.addButton("仍然导出", QMessageBox.ButtonRole.AcceptRole)
    dialog.setDefaultButton(go_back)
    dialog.setEscapeButton(go_back)
    QApplication.restoreOverrideCursor()
    try:
        dialog.exec()
    finally:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    if dialog.clickedButton() is proceed:
        accepted_pages.extend(pages)
        return True
    return False
