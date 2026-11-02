"""Prepare a source-only Windows build kit from explicit, non-private inputs."""

import argparse
import ast
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path


ROOT_FILES = (
    "main.py", "theme.py", "version.txt", "config.json.template",
    "requirements.txt", "requirements-dev.txt", "LICENSE", "README.md", "README_EN.md",
    "BUILD_WINDOWS_PORTABLE.bat", "WINDOWS_BUILD_README.md", "ruff.toml",
    "tests/__init__.py", "scripts/run_regression.ps1", "scripts/create_windows_buildkit.py",
    "packaging/macos/config/PrivacyGuard.spec",
    "docs/packaging/windows-packaging-guide.md",
)


def collect_files(root):
    paths = {root / name for name in ROOT_FILES}
    for folder, suffix in (("privacyguard", ".py"), ("tests/unit", ".py"),
                           ("assets", None), ("packaging/windows", None)):
        base = root / folder
        for path in base.rglob("*"):
            relative = path.relative_to(root)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError(f"Symlink is not a build input: {relative}")
            if not path.is_file() or path.suffix == ".pyc":
                continue
            if suffix is None or path.suffix == suffix:
                paths.add(path)
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing or unsafe build input: {path.relative_to(root)}")
        if path.name == "config.json" or path.suffix.lower() in {
                ".log", ".pdf", ".docx", ".doc", ".pdfsnap", ".pgdraft"}:
            raise ValueError(f"Private document/runtime data is not allowed: {path.relative_to(root)}")
    return sorted(paths)


def verify_kit(root):
    manifest = json.loads((root / "BUILD_INPUTS.json").read_text(encoding="utf-8"))
    for name, expected in manifest["sha256"].items():
        path = root / name
        if root.resolve() not in path.resolve().parents or path.is_symlink():
            raise ValueError(f"Unsafe manifest path: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Build input changed or is incomplete: {name}")
    print(f"[OK] Verified {len(manifest['sha256'])} build inputs for {manifest['version']}")


def create_kit(root):
    version = (root / "version.txt").read_text(encoding="utf-8").strip()
    paths = collect_files(root)
    prefix = f"PrivacyGuard-{version}-Windows-BuildKit"
    destination = root / "releases/windows" / f"{prefix}.zip"
    if destination.exists():
        raise FileExistsError(f"Build kit already exists: {destination}")
    contents = {}
    for path in paths:
        data = path.read_bytes()
        if path.suffix == ".py":
            ast.parse(data, filename=str(path.relative_to(root)), feature_version=(3, 11))
        if path.suffix == ".bat":
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        contents[path.relative_to(root).as_posix()] = data
    manifest = {
        "kind": "source-build-kit-not-a-runnable-app", "version": version,
        "target": "Windows-x64-Python3.11", "entrypoint": "BUILD_WINDOWS_PORTABLE.bat",
        "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    contents["BUILD_INPUTS.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="pg_buildkit_", suffix=".zip", dir=destination.parent)
    os.close(fd)
    pending = Path(temp_name)
    try:
        with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, data in sorted(contents.items()):
                archive.writestr(f"{prefix}/{name}", data)
        with zipfile.ZipFile(pending) as archive:
            if archive.testzip() is not None:
                raise ValueError("Build kit ZIP failed CRC validation")
        pending.rename(destination)
    finally:
        pending.unlink(missing_ok=True)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(f"{digest}  {destination.name}\n", encoding="ascii")
    print(json.dumps({"path": str(destination), "files": len(contents),
                      "bytes": destination.stat().st_size, "sha256": digest}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify_kit(args.verify)
    else:
        create_kit(Path(__file__).resolve().parents[1])
