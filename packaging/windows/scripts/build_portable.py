"""Native Windows x64 release builder. Never cross-compile or hide a failed gate."""

import hashlib
import importlib.util
from importlib.metadata import version as distribution_version
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def pe_machine(path):
    with Path(path).open("rb") as handle:
        header = handle.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise ValueError(f"Not a Windows PE file: {path}")
        offset = struct.unpack_from("<I", header, 60)[0]
        if not 64 <= offset <= 16 * 1024 * 1024:
            raise ValueError(f"Invalid PE header offset: {path}")
        handle.seek(offset)
        signature = handle.read(6)
        if len(signature) != 6 or signature[:4] != b"PE\0\0":
            raise ValueError(f"Invalid PE signature: {path}")
        return struct.unpack_from("<H", signature, 4)[0]


def validate_bundle(app_dir, version):
    errors, binaries = [], 0
    internal = app_dir / "_internal"
    for path in (app_dir / "PrivacyGuard.exe", internal / "version.txt",
                 internal / "config.json.template", internal / "assets/js/word_preview_interactive.js"):
        if not path.is_file():
            errors.append(f"Missing file: {path.relative_to(app_dir)}")
    if (internal / "version.txt").exists() and (internal / "version.txt").read_text().strip() != version:
        errors.append("Embedded version.txt differs from source")
    for path in app_dir.rglob("*"):
        if path.is_symlink():
            errors.append(f"Unexpected symlink: {path.relative_to(app_dir)}")
            continue
        if not path.is_file():
            continue
        if path.name.lower() in {"icu.dll", "icuin.dll", "icuuc.dll"}:
            errors.append(f"Bundled file shadows Windows system ICU: {path.relative_to(app_dir)}")
        if path.name == "config.json" or path.suffix in {".log", ".pdfsnap", ".pgdraft"}:
            errors.append(f"Private runtime data: {path.relative_to(app_dir)}")
        if path.suffix.lower() in {".exe", ".dll", ".pyd"}:
            try:
                if pe_machine(path) != 0x8664:
                    errors.append(f"Non-x64 binary: {path.relative_to(app_dir)}")
                binaries += 1
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
    for name in ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx",
                 "ch_ppocr_mobile_v2.0_cls_mobile.onnx"):
        if not any(p.is_file() and not p.is_symlink() and p.stat().st_size > 0 for p in internal.rglob(name)):
            errors.append(f"Missing offline model: {name}")
    for name in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"):
        if not (app_dir / name).is_file() and not (internal / name).is_file():
            errors.append(f"Missing portable VC++ runtime: {name}")
    return {"version": version, "target": "Windows-x64", "binary_count": binaries, "errors": errors}


def verify_onnx_binaries(source, bundled):
    """Reject missing or mixed-version native libraries before the smoke test."""
    def hashes(directory):
        result = {}
        for path in directory.iterdir():
            if path.is_file() and path.suffix.lower() in {".dll", ".pyd"}:
                with path.open("rb") as handle:
                    result[path.name] = hashlib.file_digest(handle, "sha256").hexdigest()
        return result

    expected = hashes(source)
    if not {"onnxruntime.dll", "onnxruntime_pybind11_state.pyd"}.issubset(expected):
        raise RuntimeError("Build interpreter lacks the required Windows ONNX Runtime libraries")
    if hashes(bundled) != expected:
        raise RuntimeError("Bundled ONNX Runtime libraries differ from the build interpreter")
    return expected


def archive_bundle(app_dir, destination):
    """Include _internal and hidden resource files, then CRC-check before publishing."""
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite release: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, pending_name = tempfile.mkstemp(prefix="pg_windows_", suffix=".zip", dir=destination.parent)
    os.close(fd)
    pending = Path(pending_name)
    try:
        with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(app_dir.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"Cannot archive symlink: {path}")
                if path.is_file():
                    archive.write(path, (Path(app_dir.name) / path.relative_to(app_dir)).as_posix())
        with zipfile.ZipFile(pending) as archive:
            corrupt = archive.testzip()
            if corrupt:
                raise ValueError(f"ZIP CRC failure: {corrupt}")
        pending.rename(destination)
    finally:
        pending.unlink(missing_ok=True)
    with destination.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    destination.with_suffix(destination.suffix + ".sha256").write_text(
        f"{digest}  {destination.name}\n", encoding="ascii")


def build():
    if sys.platform != "win32":
        raise RuntimeError("A native Windows x64 Python is required. This is not a cross-compiler.")
    if pe_machine(sys.executable) != 0x8664:
        raise RuntimeError("Use Windows x64 Python, not 32-bit or native ARM64 Python.")
    root = Path(__file__).resolve().parents[3]
    version = (root / "version.txt").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid version.txt")
    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    pinned_ort = re.search(r"^onnxruntime==([^\s]+)$", requirements, re.MULTILINE)
    if not pinned_ort or distribution_version("onnxruntime") != pinned_ort.group(1):
        raise RuntimeError("Build with the ONNX Runtime version pinned in requirements.txt")
    ort_spec = importlib.util.find_spec("onnxruntime")
    if ort_spec is None or ort_spec.origin is None:
        raise RuntimeError("ONNX Runtime package path is unavailable")
    ort_source = Path(ort_spec.origin).parent / "capi"
    work = root / "build/windows-portable"
    dist = root / "dist/windows-portable"
    app = dist / "PrivacyGuard"
    release = root / "releases/windows"
    destination = release / f"PrivacyGuard-v{version}-Windows-Portable.zip"
    if destination.exists():
        raise FileExistsError(f"Release already exists: {destination}")
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONUTF8="1", PYINSTALLER_CONFIG_DIR=str(work / "pyinstaller-cache"))
    # Avoid collecting a same-named DLL from an unrelated desktop program.
    windows_dir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    env["PATH"] = os.pathsep.join(str(path) for path in (
        Path(sys.executable).parent, Path(sys.base_prefix), windows_dir / "System32", windows_dir,
    ))

    def run(args, timeout=None, test=False):
        print("[RUN] " + subprocess.list2cmdline([str(a) for a in args]), flush=True)
        process_env = dict(env)
        if test:
            process_env.update(QT_QPA_PLATFORM="offscreen", QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu")
        subprocess.run([str(a) for a in args], cwd=root, env=process_env, check=True, timeout=timeout)

    py = sys.executable
    run([py, "-m", "pip", "check"])
    run([py, "-c", "import PyInstaller"])
    run([py, "-m", "compileall", "-q", "main.py", "privacyguard", "tests"])
    run([py, "-m", "unittest", "discover", "-s", "tests/unit", "-t", ".", "-p", "test_*.py"], test=True)
    run([py, "packaging/windows/scripts/verify_dependencies.py"])
    run([py, "packaging/windows/scripts/generate_version_info.py"])
    # Only this target is cleaned; macOS and installer outputs remain untouched.
    if app.exists():
        shutil.rmtree(app)
    run([py, "-m", "PyInstaller", "--noconfirm", "--workpath", work,
         "--distpath", dist, "packaging/windows/config/PrivacyGuard_windows.spec"])
    for name in ("LICENSE", "README.md"):
        shutil.copy2(root / name, app / name)
    shutil.copy2(root / "packaging/windows/scripts/launcher_wrapper.bat", app / "launcher_wrapper.bat")
    system = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    for name in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"):
        if not (app / "_internal" / name).exists() and not (app / name).exists() and (system / name).exists():
            shutil.copy2(system / name, app / name)
    report = validate_bundle(app, version)
    (work / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["errors"]:
        raise RuntimeError("Bundle validation failed:\n" + "\n".join(report["errors"]))
    ort_hashes = verify_onnx_binaries(ort_source, app / "_internal" / "onnxruntime" / "capi")
    with tempfile.TemporaryDirectory(prefix="isolated-self-test-", dir=work) as profile:
        self_test_env = dict(env, APPDATA=profile, LOCALAPPDATA=profile,
                             QT_QPA_PLATFORM="windows", QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu")
        self_test_report = Path(profile) / "result.json"
        result = subprocess.run([app / "PrivacyGuard.exe", "--self-test", f"--self-test-report={self_test_report}"],
                                cwd=root, env=self_test_env, timeout=180, check=False)
        if not self_test_report.is_file():
            raise RuntimeError(f"Frozen self-test stopped before recording results (exit {result.returncode})")
        smoke = json.loads(self_test_report.read_text(encoding="utf-8"))
        print(json.dumps(smoke, ensure_ascii=False), flush=True)
        if result.returncode or smoke.get("status") != "ok" or smoke.get("version") != version:
            raise RuntimeError("Frozen self-test failed; no release archive created")
    report = validate_bundle(app, version)
    if report["errors"]:
        raise RuntimeError("Post-launch validation failed:\n" + "\n".join(report["errors"]))
    archive_bundle(app, destination)
    release_report = destination.with_suffix(".validation.json")
    release_report.write_text(json.dumps(dict(report, frozen_self_test="passed", onnxruntime=pinned_ort.group(1),
                                              onnx_binaries_sha256=ort_hashes), indent=2), encoding="utf-8")
    print(f"[OK] Validated Windows portable release: {destination}", flush=True)


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
