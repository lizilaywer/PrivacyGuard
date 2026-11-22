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
VERIFY="$(mktemp -d "$WORK/verify-archive.XXXXXX")"
trap 'rm -rf "$VERIFY"' EXIT
NAME="$(basename "$ZIP")"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$VERIFY/$NAME"
ditto -x -k "$VERIFY/$NAME" "$VERIFY/unpacked"
UNPACKED="$VERIFY/unpacked/PrivacyGuard.app"
codesign --verify --deep --strict "$UNPACKED"
mkdir "$VERIFY/profile"
(
    cd "$VERIFY"
    HOME="$VERIFY/profile" CFFIXED_USER_HOME="$VERIFY/profile" \
        QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu \
        "$UNPACKED/Contents/MacOS/PrivacyGuard" --self-test \
        "--self-test-report=$OUT/PrivacyGuard-$VERSION-macOS-arm64-self-test.json"
    shasum -a 256 "$NAME" > "$NAME.sha256"
)
mv "$VERIFY/$NAME.sha256" "$ZIP.sha256"
mv "$VERIFY/$NAME" "$ZIP"
echo "Portable archive: $ZIP"
