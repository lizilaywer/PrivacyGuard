# PrivacyGuard

> Intelligent document redaction tool for PDF and Word files, built with Python + PyQt6

**Current Version**: v37.7.6
**Version Tag**: `37.7.6 - Full Convergence Remediation`
**Last Updated**: 2026-05-16
**Status**: Full remediation complete (P1-P4 all done); baseline tests 79/79 passing

[中文文档](README.md)

---

## Features

- **PDF Redaction**
  - Text-based PDF: full-text search via PyMuPDF
  - Image-based PDF: OCR via RapidOCR
  - Mixed PDF: text-layer search + embedded image/scan region OCR
- **Word Redaction**
  - `.docx` and `.doc` support
  - Intelligent scan
  - Manual precise/global redaction
  - Multi-field replacement rules (`exact` / `regex`)
  - Batch replace
- **Preview**
  - Left panel: original document with highlights
  - Right panel: redacted preview
  - Unified display of rule-based, manual, and OCR redaction
- **Interaction**
  - Drag & drop file opening
  - Advanced settings
  - Batch processing via open/drag

---

## Quick Start

### Prerequisites

- Python 3.10+
- macOS 11.0+ or Windows 10/11

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run

```bash
python3 main.py
```

### Syntax Check

```bash
python3 -m compileall -q main.py privacyguard tests
```

### Run Tests

```bash
python3 -m unittest \
  tests.unit.test_mixed_pdf_ocr \
  tests.test_path_validation \
  tests.unit.test_ocr_api \
  tests.unit.test_package_imports \
  tests.unit.test_pdf_text_hit_dedup \
  tests.unit.test_app_config \
  tests.unit.test_word_replace_rules \
  tests.unit.test_batch_word_replace \
  -v
```

Current baseline: **52/52** passing.

---

## Building

### macOS

```bash
./packaging/macos/scripts/build_complete.sh
```

### Windows

```bash
packaging\windows\scripts\build_complete.bat
```

See `docs/packaging/` for detailed guides.

---

## Project Structure

```
PrivacyGuardApp/
├── main.py                  # Application entry point (runtime)
├── theme.py                 # UI theme definitions (light/dark)
├── version.txt              # Single version source
├── config.json              # Runtime configuration
├── privacyguard/            # Modular package
│   ├── ocr/                 # OCR engine layer
│   │   ├── base.py          # Abstract base class
│   │   ├── rapidocr.py      # RapidOCR wrapper
│   │   ├── manager.py       # Engine manager
│   │   ├── mixed_pdf.py     # Mixed PDF image-block OCR
│   │   └── text_pdf.py      # Text PDF search
│   ├── utils/
│   │   ├── config.py        # ConfigManager singleton
│   │   ├── security.py      # Path security validation
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── temp_manager.py  # Temp file management
│   └── workers/
│       ├── ocr_worker.py    # OCR processing thread
│       ├── word_worker.py   # Word processing thread
│       └── image_merge.py   # Image merge thread
├── tests/                   # Unit tests
├── packaging/               # Build scripts (macOS + Windows)
├── assets/                  # Resources (logo, icons)
└── docs/                    # Documentation
```

---

## Key Dependencies

| Package | Purpose |
|---|---|
| PyQt6 | GUI framework |
| PyMuPDF | PDF rendering and text extraction |
| RapidOCR | OCR engine (ONNX Runtime) |
| python-docx | Word document manipulation |
| OpenCV | Image processing and seal detection |
| Pillow | Image handling |
| mammoth | DOCX to HTML conversion |
| BeautifulSoup4 | HTML parsing |

---

## Configuration

The application uses `config.json` for runtime configuration:

- `redaction.default_rules` - Built-in detection patterns (ID numbers, phone numbers, emails, bank cards, dates, seals)
- `redaction.replacement_text` - Default replacement text
- `redaction.scan` - OCR scan precision levels
- `security` - Path validation and file extension whitelist
- `ui` - Theme and animation settings

---

## Security

- Path validation against command injection and directory traversal
- File extension whitelist
- Temporary file cleanup on exit
- Lazy OCR engine initialization (no heavy imports at startup)

---

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

## Author

**汪立 (Wang Li)**
- Attorney at Anhui Shixin Law Firm
- Email: 491445490@qq.com

---

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
