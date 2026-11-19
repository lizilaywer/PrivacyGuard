"""Show only actual unsupported Word parts, without original text."""
from PyQt6.QtWidgets import QMessageBox


def confirm_word_coverage(parent, notes):
    unsupported = {key: value for key, value in notes.items()
                   if key != "修订（已纳入文字扫描，保留修订结构）"}
    if not unsupported:
        return True
    box = QMessageBox(parent)
    box.setWindowTitle("Word 附加内容需要复核")
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText("以下内容未自动脱敏，会保留在输出文件中：\n" +
                "\n".join(f"{key}：{value}" for key, value in unsupported.items()) +
                "\n\n请确认已另行检查，再选择保留导出。")
    export = box.addButton("已检查，保留导出", QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() is export
