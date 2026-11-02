"""Inventory staged files and scan publishable text without printing secrets.

This is a heuristic pre-publication check, not a proof that data is anonymous.
Run from any directory; output defaults to stdout (redirect locally as needed).
"""
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "credential_url": re.compile(r"https?://[^\s/:]+:[^\s/@]+@"),
}
PRIVATE_PARTS = {".mimosa", ".zcode", ".claude", ".trae", ".workbuddy",
                 "venv_win", "venvmac", "venv_macos_release", "backups", "logs", "dist", "build"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def inspect_bytes(data):
    if b"\0" in data:
        return None, []
    try:
        source = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, []
    findings = [{"kind": name, "line": source.count("\n", 0, m.start()) + 1}
                for name, pattern in SECRET_PATTERNS.items() for m in pattern.finditer(source)]
    return source, findings


def build_report():
    entries, findings = [], []
    paths = git("ls-files", "-z").decode("utf-8").split("\0")
    for rel in sorted(filter(None, paths)):
        # A manifest cannot include its own changing checksum.
        if rel == "docs/current/publication_inventory_20261102.json":
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        # Inspect canonical Git bytes: CRLF conversion must not invalidate the
        # checksums when a collaborator clones the published repository.
        data = git("show", f":{rel}")
        source, hits = inspect_bytes(data)
        entry = {"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                 "kind": "text" if source is not None else "binary"}
        if source is not None:
            entry["lines"] = len(source.splitlines())
        if path.suffix == ".py" and source is not None:
            tree = ast.parse(source, filename=rel)
            entry["classes"] = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
            entry["functions"] = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
        if set(Path(rel).parts) & PRIVATE_PARTS or path.name in {"config.json", ".env", "_tmp_idx_test"}:
            hits.append({"kind": "private_path"})
        findings.extend({"path": rel, **hit} for hit in hits)
        entries.append(entry)
    return {"scope": "Tracked Git index files: complete byte read, SHA256, UTF-8 scan and Python AST; manifest excludes itself. Not a line-by-line human audit or dependency audit.",
            "files": entries, "file_count": len(entries), "findings": findings}


if __name__ == "__main__":
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
