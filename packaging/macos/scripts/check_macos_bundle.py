"""Fail a release on incompatible Mach-O files, private config, or broken resources."""

import argparse
import json
import plistlib
from pathlib import Path

from macholib.MachO import MachO
from macholib.mach_o import LC_BUILD_VERSION, LC_VERSION_MIN_MACOSX


def version_tuple(value):
    return value >> 16, (value >> 8) & 255, value & 255


def inspect_bundle(app, expected_version):
    app = app.resolve()
    with (app / "Contents/Info.plist").open("rb") as handle:
        info = plistlib.load(handle)
    errors, binaries = [], []
    declared = tuple(int(x) for x in info["LSMinimumSystemVersion"].split("."))
    declared = (declared + (0, 0, 0))[:3]
    if info.get("CFBundleShortVersionString") != expected_version:
        errors.append("Bundle version differs from version.txt")
    required = ("Contents/MacOS/PrivacyGuard", "Contents/Resources/version.txt",
                "Contents/Resources/config.json.template", "Contents/Resources/AppIcon.icns",
                "Contents/Resources/assets/js/word_preview_interactive.js")
    for rel in required:
        if not (app / rel).is_file():
            errors.append(f"Missing resource: {rel}")
    actual_version = app / "Contents/Resources/version.txt"
    if actual_version.exists() and actual_version.read_text().strip() != expected_version:
        errors.append("Embedded version.txt differs from source")
    magic_values = {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}
    for path in app.rglob("*"):
        if path.is_symlink():
            if not path.exists() or not path.resolve().is_relative_to(app):
                errors.append(f"Broken or escaping symlink: {path.relative_to(app)}")
            continue
        if not path.is_file():
            continue
        if path.name in {"config.json", ".env"} or path.suffix in {".pgdraft", ".pdfsnap", ".log"}:
            errors.append(f"Private runtime data in bundle: {path.relative_to(app)}")
        with path.open("rb") as handle:
            magic = handle.read(4)
        if magic not in magic_values:
            continue
        macho = MachO(str(path))
        arm_headers = [h for h in macho.headers if h.header.cputype == 0x100000C]
        if not arm_headers:
            errors.append(f"Missing arm64 slice: {path.relative_to(app)}")
        min_os = (0, 0, 0)
        for header in arm_headers:
            for command, details, data in header.commands:
                if command.cmd == LC_BUILD_VERSION:
                    min_os = max(min_os, version_tuple(details.minos))
                elif command.cmd == LC_VERSION_MIN_MACOSX:
                    min_os = max(min_os, version_tuple(details.version))
            for _idx, _name, dependency in header.walkRelocatables():
                if dependency.startswith("/") and not dependency.startswith(("/usr/lib/", "/System/Library/")):
                    errors.append(f"External dependency: {path.relative_to(app)} -> {dependency}")
        if min_os > declared:
            errors.append(f"Requires {min_os}, exceeds plist {declared}: {path.relative_to(app)}")
        binaries.append({"path": str(path.relative_to(app)), "min_os": list(min_os)})
    for name in ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx", "ch_ppocr_mobile_v2.0_cls_mobile.onnx"):
        if not any(app.rglob(name)):
            errors.append(f"Missing offline model: {name}")
    return {"version": expected_version, "declared_min_os": list(declared),
            "architecture": "arm64", "binary_count": len(binaries),
            "highest_min_os": list(max((tuple(b["min_os"]) for b in binaries), default=(0, 0, 0))),
            "errors": errors, "binaries": binaries}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("app", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = inspect_bundle(args.app, args.version)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "binaries"}, indent=2))
    raise SystemExit(bool(report["errors"]))
