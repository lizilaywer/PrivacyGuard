"""Small shared style for supplemental UI, matching the existing light app."""
from theme import Theme
import sys


def apply_office_style(widget):
    theme = Theme.LIGHT
    family = "'Microsoft YaHei UI', 'Microsoft YaHei', sans-serif" if sys.platform == "win32" else Theme.FONT_FAMILY
    widget.setStyleSheet(f"""
        QWidget {{ font-family: {family}; font-size: 12px; color: {theme['text']}; }}
        QDialog {{ background: {theme['surface']}; }}
        QPushButton {{ padding: 6px 10px; border: 1px solid {theme['border']}; border-radius: 6px; background: {theme['surface']}; }}
        QPushButton:hover {{ background: {theme['hover']}; }}
        QPushButton:disabled {{ color: {theme['text_secondary']}; }}
        QTreeWidget {{ background: {theme['surface']}; border: 1px solid {theme['border']}; border-radius: 6px; }}
        QComboBox {{ padding: 5px; }}
    """)
