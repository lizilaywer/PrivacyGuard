# PrivacyGuard v37.0 Release Summary

## 📦 Release Information

- **Version**: 37.0 - Configuration System
- **Release Date**: 2026-02-17
- **Commit**: 16f3a8f
- **Status**: ✅ Released

---

## 🎯 What's New

### Configuration System (Major Feature)

PrivacyGuard now supports a JSON-based configuration system that allows users to customize application behavior without modifying code.

#### Key Features:
- **ConfigManager Singleton**: Thread-safe configuration management with RLock protection
- **Dot Notation Access**: `config.get("app.window.default_width")`
- **Hot Reload**: Configuration can be reloaded without restarting
- **Backward Compatibility**: Falls back to hardcoded defaults if config fails
- **Configuration Validation**: Built-in validation for configuration values

#### Configuration Categories:
- `app`: Application name, window dimensions, feedback URL
- `redaction`: Desensitization rules, replacement text, scan parameters
- `ocr`: OCR accuracy, zoom ranges
- `security`: Path validation, allowed file extensions
- `ui`: Theme, animations, tips
- `advanced`: Debug mode, temp file cleanup

---

## 📁 Files Changed

### New Files (11)
```
privacyguard/
├── __init__.py                    # Package exports
├── core/__init__.py               # Core module (placeholder)
├── ui/__init__.py                 # UI module (placeholder)
├── utils/
│   ├── __init__.py                # Utils exports (includes ConfigManager)
│   ├── config.py                  # Configuration manager (400+ lines)
│   ├── exceptions.py              # Custom exceptions
│   ├── security.py                # Security validation
│   └── temp_manager.py            # Temp file management
└── workers/
    ├── __init__.py                # Workers exports
    ├── image_merge.py             # Image merge worker
    ├── ocr_worker.py              # OCR processing worker
    └── word_worker.py             # Word document worker

config.json                        # User configuration (auto-generated)
config.json.template               # Configuration template
```

### Modified Files (14)
```
main.py                            # Integrated configuration system
version.txt                        # 37.0

packaging/macos/
├── config/PrivacyGuard.spec       # Added privacyguard package
└── scripts/build_macos_app.sh     # Version update

packaging/windows/
├── config/PrivacyGuard_windows.spec    # Added privacyguard package
├── config/PrivacyGuard_Setup.iss       # Version 37.0
├── config/version_info.txt             # Version 37.0
└── scripts/README.txt             # Version update

docs/current/
├── DEV_LOG.md                     # Added v37.0 changelog
└── STATUS.md                      # Added configuration system status

CHANGELOG.md                       # Added v37.0 release notes
CLAUDE.md                          # Updated version and configuration info
README.md                          # Added configuration system documentation
```

---

## ✅ Verification Checklist

### Code Quality
- [x] All 11 Python files pass syntax check
- [x] ConfigManager imports successfully
- [x] Configuration save/reload tested
- [x] Backward compatibility verified

### Build Verification
- [x] macOS build successful
  - .app size: 708MB
  - DMG size: 310MB
  - SHA256: e221f6613756993379d11cfa8514bc1e1d744ce5ceb008443831275b78f0cb8c
- [x] Windows packaging scripts verified
- [x] All version numbers updated to 37.0

### Configuration System
- [x] ConfigManager singleton works correctly
- [x] Configuration file created at `config.json`
- [x] Template file available at `config.json.template`
- [x] Settings dialog saves to configuration
- [x] Backward compatibility (fallback to defaults)

---

## 📦 Build Artifacts

### macOS
```
releases/macos/PrivacyGuard-37.0-macOS.dmg (310MB)
SHA256: e221f6613756993379d11cfa8514bc1e1d744ce5ceb008443831275b78f0cb8c
```

### Windows
```
scripts:
- packaging/windows/scripts/1_初始化环境.bat
- packaging/windows/scripts/2_一键打包.bat
- packaging/windows/scripts/3_完整打包带安装程序.bat
- packaging/windows/scripts/4_仅创建安装程序.bat
```

---

## 📝 Configuration Example

```json
{
  "version": "1.0",
  "app": {
    "name": "PrivacyGuard 脱敏卫士",
    "window": {
      "default_width": 1300,
      "default_height": 900,
      "min_width": 900,
      "min_height": 600
    }
  },
  "redaction": {
    "default_rules": {
      "身份证号": {
        "pattern": "(?<!\\d)([1-9]\\d{5}(19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]|\\d{15})(?!\\d)",
        "enabled": true
      }
    },
    "replacement_text": "[已脱敏]",
    "scan": {
      "default_level": 2.0
    }
  }
}
```

---

## 🔧 API Usage

```python
from privacyguard.utils import ConfigManager

# Get singleton instance
config = ConfigManager()

# Read configuration
width = config.get("app.window.default_width", 1300)
rules = config.get_redaction_rules()

# Update configuration
config.set("redaction.scan.default_level", 2.5, persist=True)

# Reload configuration
config.reload()
```

---

## 🔄 Migration Notes

### For Users
- Configuration is automatic - no action needed
- Settings are saved to `config.json` automatically
- If config is corrupted, delete `config.json` to reset to defaults

### For Developers
- All hardcoded constants still work as fallback
- Import `ConfigManager` from `privacyguard.utils`
- Use `config.get(path, default)` for safe access

---

## 📋 Backup Location

```
backups/v37.0_config_system_20260217_233617/
├── main.py
├── privacyguard/
├── config.json
└── config.json.template
```

---

## 🙏 Credits

**Developer**: li (汪立律师)
**Configuration System**: Implemented with Claude Code assistance
**Testing**: macOS build verified, Windows scripts validated

---

## 📄 License

See LICENSE.txt for details.

---

*Released: 2026-02-17*
*Version: 37.0 - Configuration System*
