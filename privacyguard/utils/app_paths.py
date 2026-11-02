"""Runtime paths: immutable bundle resources and writable per-user settings."""

import os
import sys
from pathlib import Path


def resource_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def default_config_path():
    if not getattr(sys, "frozen", False):
        return str(resource_root() / "config.json")
    if sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        root = Path(os.environ.get("APPDATA") or Path.home())
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return str(root / "PrivacyGuard" / "config.json")
