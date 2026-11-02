#!/bin/bash
# Build a self-contained arm64 app, with no activation or global-Python fallback.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
PY="${PRIVACYGUARD_PYTHON:-$ROOT/venv_macos_release/bin/python3}"
if [ ! -x "$PY" ]; then
    echo "Missing release interpreter: $PY" >&2
    exit 1
fi
VERSION="$(tr -d '[:space:]' < version.txt)"
ARCH="$(uname -m)"
if [ "$ARCH" != arm64 ]; then
    echo "This release target is Apple Silicon arm64; use a matching build host." >&2
    exit 1
fi
OUT="$ROOT/releases/macos"
WORK="$ROOT/build/macos-portable"
DIST="$ROOT/dist/macos-portable"
APP="$DIST/PrivacyGuard.app"
mkdir -p "$OUT" "$WORK"
export PYINSTALLER_CONFIG_DIR="$WORK/pyinstaller-cache"
"$PY" -m pip check
"$PY" -m compileall -q main.py privacyguard
QT_QPA_PLATFORM=offscreen "$PY" -m unittest discover -s tests/unit -t . -p 'test_*.py'
"$PY" -m PyInstaller --clean --noconfirm --workpath "$WORK" --distpath "$DIST" \
    "$ROOT/packaging/macos/config/PrivacyGuard.spec"
"$PY" packaging/macos/scripts/check_macos_bundle.py "$APP" --version "$VERSION" \
    --report "$OUT/PrivacyGuard-$VERSION-macOS-arm64-validation.json"
# PyInstaller already signs nested Mach-O binaries; seal the final immutable bundle.
codesign --force --sign - "$APP"
codesign --verify --deep --strict "$APP"
ZIP="$OUT/PrivacyGuard-$VERSION-macOS-arm64-portable.zip"
if [ -e "$ZIP" ]; then
    echo "Release already exists, refusing to overwrite: $ZIP" >&2
    exit 1
fi
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
(cd "$OUT" && shasum -a 256 "$(basename "$ZIP")" > "$(basename "$ZIP").sha256")
echo "Portable archive: $ZIP"
