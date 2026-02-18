# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**PrivacyGuard 脱敏卫士** is a Python + PyQt6 desktop application for intelligent data redaction in PDF and Word documents.

**Current Version**: v37.0
**Primary Language**: Python 3.11
**Main File**: `main.py` (~2600 lines, monolithic architecture)
**Config System**: JSON-based configuration with `ConfigManager` class

**Key Capabilities**:
- PDF redaction (image-based and text-based) using OCR (RapidOCR) and text extraction (PyMuPDF)
- Word document redaction (.docx, .doc) via python-docx
- Manual redaction (precise mode for single selection, global mode for all occurrences)
- Batch undo functionality
- Web-based preview using QWebEngineView with JavaScript interaction

**Configuration System (v37.0)**:
- JSON-based configuration with `ConfigManager` singleton class
- Hot-reload support and backward compatibility
- Configuration categories: `app`, `redaction`, `ocr`, `security`, `ui`, `advanced`
- Path access via dot notation: `config.get("app.window.default_width")`

**Security Features (v36.2)**:
- Path validation (`validate_safe_path()`) to prevent command injection and path traversal
- Secure temp file management with `atexit` cleanup hooks (`TempFileManager`)
- Specific exception handling (replaced bare `except Exception` in 11 critical locations)
- Dependency security auditing with `pip-audit` (no known vulnerabilities)

---

## Development Commands

### Environment Setup
```bash
cd /Users/a49144/Desktop/临时coding/PrivacyApp
source venv/bin/activate
pip install -r requirements.txt
```

### Run Application
```bash
python main.py
# or
./start_app.sh
```

### Syntax Check
```bash
python -c "import ast; ast.parse(open('main.py').read()); print('✓ OK')"
```

### Run Tests
```bash
python tests/scripts/test_stability.py
python tests/scripts/verify_word_format.py
bash tests/scripts/quick_test.sh
```

### Build macOS App
```bash
bash build/build_macos_app.sh
```

### Version Verification
```bash
python -c "
import re
with open('main.py') as f:
    content = f.read()
    version = re.search(r'VERSION = \"([^\"]+)\"', content)
    if version:
        print(f'当前版本: {version.group(1)}')
"
```

---

## Architecture

### File Structure

```
PrivacyApp/
├── main.py                    # Monolithic main application (~2600 lines)
├── theme.py                   # Theme system (light/dark mode)
├── requirements.txt            # Dependencies
├── start_app.sh              # Quick launch script
├── docs/
│   ├── current/              # Active development docs
│   │   ├── STATUS.md        # ⭐ Current project status
│   │   ├── DEV_LOG.md      # ⭐ Development changelog
│   │   └── RECOVERY_GUIDE.md # ⭐ Recovery instructions
│   ├── security-hardening.md # Security hardening details (v36.2)
│   └── *.md                # Standards and compliance docs
├── backups/                 # Version backups (organized by version)
├── tests/
│   ├── scripts/            # Test scripts
│   ├── samples/            # Test sample files
│   └── reports/            # Test reports
├── build/                  # Build configuration
├── dist/                   # PyInstaller output
└── venv/                   # Python virtual environment
```

### Core Classes in main.py

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `MainWindow` | Main UI controller | `_open_pdf`, `_open_word`, `run_ocr_scan`, `save_pdf`, `_save_word` |
| `SinglePageCanvas` | PDF page rendering with manual redaction | `paintEvent`, `mousePressEvent`, `add_manual_redaction`, `pdf_to_screen` |
| `OCRWorker` | Background thread for PDF OCR scanning | `run`, `_scan_page_ocr`, `_scan_text_layer` |
| `WordWorker` | Background thread for Word document scanning | `run` |
| `WebViewBridge` | Python-JavaScript bridge for Word preview | `add_redaction`, `remove_redaction`, `get_scroll_position` |
| `SettingsDialog` | Configuration dialog for rules and settings | `save_settings` |
| `TempFileManager` | Temporary file lifecycle management | `create_temp_file`, `cleanup` |

### Key Data Flow

**PDF Processing**:
1. User opens PDF → `MainWindow._open_pdf()`
2. User clicks "智能脱敏" → `MainWindow.run_ocr_scan()`
3. `OCRWorker` scans pages (text layer + OCR for images)
4. Results stored in `self.page_data[page_num] = {'ocr': [], 'manual': []}`
5. Redaction boxes drawn on `SinglePageCanvas` via `paintEvent()`

**Word Processing**:
1. User opens Word → `MainWindow._open_word()`
2. Document converted to HTML via mammoth
3. HTML displayed in QWebEngineView
4. JavaScript bridge (`WebViewBridge`) handles interactions
5. Sensitive info highlighted using three-pass replacement (placeholder strategy)
6. Manual redaction via right-click context menu (precise/global modes)

---

## Critical Implementation Details

### HTML Highlighting Strategy (Word Preview)

Located in `main.py` ~1745-1862 lines. Uses **three-pass placeholder replacement** to avoid HTML tag corruption:

```python
# Pass 1: Generate unique placeholder
placeholder = f"__PLACEHOLDER_{key}__"

# Pass 2: Replace text with placeholder in HTML
html = html.replace(escaped_text, placeholder)

# Pass 3: Replace placeholder with highlighted content
html = html.replace(placeholder, highlighted_text)
```

**Why this matters**: Direct string replacement `html.replace(text, highlighted)` causes issues when:
- Same text appears multiple times (all get replaced)
- HTML entities don't match (&lt; vs <)
- Text spans multiple HTML elements

### Manual Redaction Modes (Word)

**Precise Mode** (精确模式): Only redacts the selected text occurrence
- Uses `data-key` attribute to target specific text block
- Undo only affects that specific occurrence

**Global Mode** (全局模式): Finds and redacts all occurrences of selected text
- Uses regex global replacement across entire HTML
- Undo removes all matching redactions

Code locations:
- Precise mode: `main.py` lines 1863-1944
- Global mode: `main.py` lines 1945-2075
- Batch undo: `main.py` lines 2076-2158

### Scroll Position Persistence (Word)

Issue: After redaction operations, view jumps to top.

Solution: Three-layer mechanism
1. JavaScript `saveScroll()` stores position in `localStorage`
2. Python `get_scroll_position()` retrieves via Qt WebChannel
3. Delayed `set_scroll_position()` restoration after HTML reload

Code location: `main.py` lines 1680-1742

### Debug Mode

Enable via environment variable:
```bash
export PRIVACYGUARD_DEBUG=True
python main.py
```

When enabled, adds debug rectangles and console logging for OCR detection boxes.

---

## Security Considerations (v36.2)

### Path Validation

The `validate_safe_path()` function (main.py lines 167-219) validates file paths before use:
- **Command injection protection**: Blocks dangerous characters (`;`, `|`, `&`, `$`, `` ` ``, `$(`, `>`, `<`)
- **Path traversal protection**: Normalizes paths and checks they remain within allowed directories
- **Extension validation**: Optional whitelist for file extensions

Usage:
```python
is_safe, error_msg = validate_safe_path(file_path, allowed_extensions=['.doc', '.docx'])
if not is_safe:
    raise ConversionError("文件路径不安全", error_msg)
```

### TempFileManager

Secure temporary file handling (main.py lines 126-164):
- Uses `atexit` to register cleanup hooks
- Ensures temp files are cleaned up even if program crashes
- Tracks all created temp files and directories

Usage:
```python
self.temp_manager = TempFileManager()
temp_file = self.temp_manager.create_temp_file(suffix='.pdf')
temp_dir = self.temp_manager.create_temp_dir()
# Cleanup happens automatically on program exit
```

### Exception Handling

Replaced bare `except Exception` with specific exception types:
- File operations: `OSError`, `IOError`
- Image processing: `IOError`, `OSError`, `ValueError`
- OCR operations: `IOError`, `OSError`, `RuntimeError`, `ValueError`
- Subprocess calls: `subprocess.CalledProcessError`, `subprocess.TimeoutExpired`

This prevents accidentally catching unexpected errors and improves security by not masking system-level exceptions.

### Dependency Security

Run `pip-audit` regularly to check for vulnerabilities:
```bash
pip install pip-audit
pip-audit --local
```

Current status: No known vulnerabilities in dependencies.

---

## Important Constants

```python
# Located at top of main.py
APP_NAME = "PrivacyGuard 脱敏卫士"
VERSION = "36.5 - Security Fix"
MIN_RECT_WIDTH = 5           # Minimum rectangle width (pixels)
ZOOM_MIN = 0.5               # Minimum zoom level
ZOOM_MAX = 4.0               # Maximum zoom level

# Default regex patterns for sensitive data
DEFAULT_RULES = {
    "身份证号": r"(?<!\d)([1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]|\d{15})(?!\d)",
    "手机号码": r"(?<!\d)(1[3-9]\d{9})(?!\d)",
    "日期时间": r"\d{4}[年\-\.]\d{1,2}[月\-\.]\d{1,2}[日]?",
    "电子邮箱": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "银行卡号": r"(?<!\d)([1-9]\d{12,18})(?!\d)"
}
```

---

## Known Issues

### Low Priority (Acceptable)
1. **Precise mode occasional failure**: <5% of selections fail to highlight (use global mode as fallback)
2. **Large document performance**: 50+ page documents have <15s delay
3. **.doc format conversion**: Requires LibreOffice or antiword (may lose formatting)

### Development Context
- Version v31.9 marked last major stable release with manual redaction features
- Current working directory: `/Users/a49144/Desktop/临时coding/PrivacyApp`
- Virtual environment: `venv/bin/python`

---

## Dependencies

Key libraries:
- `PyQt6` / `PyQt6-WebEngine` - GUI framework
- `PyMuPDF` (fitz) - PDF processing
- `python-docx` - Word .docx processing
- `mammoth` - Word to HTML conversion
- `rapidocr_onnxruntime` - OCR engine
- `opencv-python`, `numpy` - Image processing for OCR
- `PyInstaller` - macOS app packaging

---

## Version Control & Backups

### Backup Strategy
Backups are organized in `backups/` directory:
- `backups/v31.9_current/` - Latest stable version backups
- `backups/v31_early/` - Early v31 versions
- `backups/v25-v29/` - Intermediate versions
- `backups/v24_word/` - v24 Word support
- `backups/v23_ui/` - v23 UI version
- `backups/v19_legacy/` - Early versions

### Creating Backups
Before making significant changes:
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp main.py "backups/v31.9_current/main.py.backup_${TIMESTAMP}"
```

### Rollback
```bash
# List available backups
ls -la backups/v31.9_current/

# Restore specific backup
cp backups/v31.9_current/main.py.backup_FINAL_* main.py
```

---

## Debugging

### Browser Console Logs (Word Preview)
Right-click preview area → Inspect Element → Console tab

Key log prefixes:
- `[ScrollRestore]` - Scroll position save/restore
- `[findTextPosition]` - Text location lookup
- `✓✓✓` - Success
- `✗✗✗` - Failure

### Python Output
```bash
python main.py 2>&1 | tee debug.log
```

---

## Documentation Reference

**Essential Reading** (in `docs/current/`):
1. `STATUS.md` - Current project status and quick reference
2. `DEV_LOG.md` - Detailed development changelog
3. `RECOVERY_GUIDE.md` - Step-by-step recovery instructions

**Compliance Documents**:
- `docs/信息脱敏标准规范.md` - Chinese standards (GB/T) and legal requirements
- `docs/合规性评估报告.md` - Compliance assessment report

---

## Development Notes

### Code Style
- Single-file architecture (main.py is monolithic)
- Mix of English and Chinese comments (Chinese preferred for user-facing strings)
- PyQt6 signal-slot pattern for async operations
- QThread for background OCR processing

### Thread Safety
- OCR operations run in `OCRWorker` (QThread)
- Word processing runs in `WordWorker` (QThread)
- UI updates via Qt signals (thread-safe)
- Mutex locks used for critical sections

### Memory Management
- `TempFileManager` handles temporary file cleanup
- PDF documents not fully loaded into memory (streaming for large files)
- `cv2.setNumThreads(0)` for thread pool limit

---

## Change Summary (Recent Versions)

### v31.9 (2026-02-12)
- Precise mode manual redaction (single selection)
- Global mode manual redaction (all occurrences)
- Batch undo functionality
- Scroll position persistence fix

### v30.3
- Ultra Compact Highlighting for Word preview
- Manual redaction for Word (basic)

### v24.0
- Word document support (.docx, .doc)

See `CHANGELOG.md` for full version history.
