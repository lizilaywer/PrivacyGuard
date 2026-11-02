"""Generate a source/document inventory; virtualenvs and user documents are excluded."""

import ast
import hashlib
import json
from pathlib import Path


def build_inventory(root):
    roots = [root / p for p in ("privacyguard", "packaging", "scripts", "tests", "assets/js", "docs", "user-guides")]
    paths = {p for directory in roots for p in directory.rglob("*") if p.is_file()}
    paths.update(p for p in root.iterdir() if p.is_file())
    extensions = {".py", ".js", ".sh", ".ps1", ".bat", ".spec", ".iss", ".md", ".txt", ".json", ".template", ".yml", ".yaml", ".plist"}
    entries = []
    for path in sorted(paths):
        if path.suffix not in extensions or "__pycache__" in path.parts or path.name in {"config.json", "audit_inventory_20261024.json"}:
            continue
        data = path.read_bytes()
        source = data.decode("utf-8-sig", errors="replace")
        entry = {"path": str(path.relative_to(root)), "bytes": len(data),
                 "lines": len(source.splitlines()), "sha256": hashlib.sha256(data).hexdigest()}
        if path.suffix == ".py":
            try:
                tree = ast.parse(source)
                entry["functions"] = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
                entry["classes"] = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
            except SyntaxError as exc:
                entry["syntax_error"] = f"{exc.lineno}: {exc.msg}"
        entries.append(entry)
    return {"scope": "First-party source, tests, scripts, current and archived docs; not dependencies/user documents/backups",
            "file_count": len(entries), "files": entries}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    inventory = build_inventory(root)
    output = root / "docs/current/audit_inventory_20261024.json"
    output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": inventory["file_count"], "python_files": sum(p["path"].endswith(".py") for p in inventory["files"]),
                      "output": str(output)}, ensure_ascii=False))
