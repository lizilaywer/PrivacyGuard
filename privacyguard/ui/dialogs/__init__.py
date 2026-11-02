"""privacyguard.ui.dialogs - Extracted dialog classes from main.py"""

from privacyguard.ui.dialogs.settings_dialog import SettingsDialog
from privacyguard.ui.dialogs.trace_clean_dialog import TraceCleanDialog, _TraceSizeWorker
from privacyguard.ui.dialogs.word_replace_rules_dialog import WordReplaceRulesDialog, WORD_RULE_SCHEMA_VERSION
from privacyguard.ui.dialogs.image_list_dialog import ImageListDialog
from privacyguard.ui.dialogs.feedback_dialog import FeedbackDialog
from privacyguard.ui.dialogs.donate_dialog import DonateDialog
from privacyguard.ui.dialogs.manual_region_dialog import ManualRegionRedactDialog
from privacyguard.ui.dialogs.encrypt_dialog import EncryptSettingsDialog
from privacyguard.ui.dialogs.password_open_dialog import PasswordOpenDialog

__all__ = [
    "SettingsDialog",
    "TraceCleanDialog",
    "_TraceSizeWorker",
    "WordReplaceRulesDialog",
    "WORD_RULE_SCHEMA_VERSION",
    "ImageListDialog",
    "FeedbackDialog",
    "DonateDialog",
    "ManualRegionRedactDialog",
    "EncryptSettingsDialog",
    "PasswordOpenDialog",
]
