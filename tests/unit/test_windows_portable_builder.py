"""Cross-platform checks for Windows packaging gates, using synthetic PE headers."""

import hashlib
import importlib.util
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "pg_windows_builder", ROOT / "packaging/windows/scripts/build_portable.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def write_pe(path, machine=0x8664):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = bytearray(64)
    header[:2] = b"MZ"
    struct.pack_into("<I", header, 60, 64)
    path.write_bytes(header + b"PE\0\0" + struct.pack("<H", machine))


class TestWindowsPortableBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = self.root / "PrivacyGuard"
        self.internal = self.app / "_internal"
        self.internal.mkdir(parents=True)
        write_pe(self.app / "PrivacyGuard.exe")
        for name in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"):
            write_pe(self.internal / name)
        (self.internal / "version.txt").write_text("40.2.5", encoding="utf-8")
        (self.internal / "config.json.template").write_text("{}", encoding="utf-8")
        js = self.internal / "assets/js/word_preview_interactive.js"
        js.parent.mkdir(parents=True)
        js.write_text("// synthetic", encoding="utf-8")
        for name in ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx",
                     "ch_ppocr_mobile_v2.0_cls_mobile.onnx"):
            (self.internal / name).write_bytes(b"synthetic model")

    def test_complete_x64_bundle_passes(self):
        report = builder.validate_bundle(self.app, "40.2.5")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["binary_count"], 4)

    def test_rejects_non_x64_dll(self):
        write_pe(self.internal / "bad.dll", 0x14C)
        self.assertTrue(any("Non-x64" in e for e in builder.validate_bundle(self.app, "40.2.5")["errors"]))

    def test_rejects_truncated_pe(self):
        (self.app / "PrivacyGuard.exe").write_bytes(b"MZ")
        with self.assertRaises(ValueError):
            builder.pe_machine(self.app / "PrivacyGuard.exe")

    def test_rejects_wrong_version(self):
        self.assertIn("Embedded version.txt differs from source",
                      builder.validate_bundle(self.app, "0.0.0")["errors"])

    def test_rejects_private_config(self):
        (self.internal / "config.json").write_text("{}", encoding="utf-8")
        self.assertTrue(any("Private runtime data" in e
                            for e in builder.validate_bundle(self.app, "40.2.5")["errors"]))

    def test_rejects_empty_model(self):
        (self.internal / "PP-OCRv6_det_small.onnx").write_bytes(b"")
        self.assertTrue(any("Missing offline model" in e
                            for e in builder.validate_bundle(self.app, "40.2.5")["errors"]))

    def test_rejects_missing_runtime(self):
        (self.internal / "msvcp140.dll").unlink()
        self.assertTrue(any("Missing portable VC++" in e
                            for e in builder.validate_bundle(self.app, "40.2.5")["errors"]))

    def test_archive_keeps_internal_and_hidden_files_and_correct_hash(self):
        (self.internal / ".resource").write_bytes(b"hidden")
        dest = self.root / "release.zip"
        builder.archive_bundle(self.app, dest)
        with zipfile.ZipFile(dest) as archive:
            self.assertIn("PrivacyGuard/_internal/.resource", archive.namelist())
            self.assertIsNone(archive.testzip())
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        self.assertEqual(dest.with_suffix(".zip.sha256").read_text().split()[0], digest)

    def test_archive_does_not_overwrite_release(self):
        dest = self.root / "release.zip"
        dest.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            builder.archive_bundle(self.app, dest)
        self.assertEqual(dest.read_bytes(), b"existing")

    @unittest.skipIf(sys.platform == "win32", "Symlink creation may require Windows elevation")
    def test_symlink_is_rejected_without_publishing_archive(self):
        (self.app / "linked").symlink_to(self.internal, target_is_directory=True)
        self.assertTrue(any("Unexpected symlink" in e
                            for e in builder.validate_bundle(self.app, "40.2.5")["errors"]))
        dest = self.root / "release.zip"
        with self.assertRaises(ValueError):
            builder.archive_bundle(self.app, dest)
        self.assertFalse(dest.exists())
        self.assertEqual(list(self.root.glob("pg_windows_*")), [])

    def test_non_windows_fails_before_running_tools(self):
        with patch.object(builder.sys, "platform", "darwin"), patch.object(builder.subprocess, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "native Windows"):
                builder.build()
            run.assert_not_called()
