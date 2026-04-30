import os
import tempfile
import platform

def validate_safe_path(path, allowed_extensions=None):
    if not path:
        return False, "empty path"
    if len(path) > 4096:
        return False, "path too long"
    is_windows = platform.system() == 'Windows'
    shell_metacharacters = [';', '|', '&', '$', '`', '$(', '>', '<', '\n', '\r']
    for char in shell_metacharacters:
        if char in path:
            return False, f"dangerous char: {repr(char)}"
    if not is_windows and '\\' in path:
        return False, "backslash on non-Windows"
    if '\x00' in path:
        return False, "null byte"
    try:
        normalized = os.path.normpath(os.path.abspath(path))
    except Exception as e:
        return False, f"path error: {e}"
    allowed_base_dirs = [
        os.path.normpath(os.path.abspath(os.path.expanduser("~"))),
        os.path.normpath(os.path.abspath(tempfile.gettempdir())),
    ]
    path_in_allowed_dir = any(normalized.startswith(d) for d in allowed_base_dirs)
    if not path_in_allowed_dir:
        cwd = os.path.normpath(os.path.abspath('.'))
        if not normalized.startswith(cwd):
            return False, f"path not allowed: {normalized}"
    basename = os.path.basename(normalized)
    if not basename or basename.startswith('.'):
        return False, "invalid filename"
    if allowed_extensions:
        ext = os.path.splitext(basename)[1].lower()
        if ext not in allowed_extensions:
            return False, f"unsupported ext: {ext}"
    return True, None

# 测试并写入结果
results = []
results.append(f"Platform: {platform.system()}")
results.append(f"Temp dir: {tempfile.gettempdir()}")
results.append("")

passed = 0
failed = 0

tests = [
    ("Windows path", r"C:\Users\Admin\AppData\Local\Temp\test.doc", ['.doc'], True),
    ("Cmd injection", r"C:\test;rm.doc", ['.doc'], False),
    ("Pipe attack", r"C:\test|cat.doc", ['.doc'], False),
    ("Temp dir file", os.path.join(tempfile.gettempdir(), "source.doc"), ['.doc'], True),
]

for name, path, exts, expected in tests:
    result, msg = validate_safe_path(path, exts)
    ok = (result == expected)
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    results.append(f"[{status}] {name}")
    results.append(f"  Path: {path}")
    results.append(f"  Result: ({result}, {msg})")
    results.append(f"  Expected: {expected}")
    results.append("")

results.append(f"Total: {passed} passed, {failed} failed")

with open("C:/Users/Admin/Desktop/claudecodehub/PrivacyApp/test_output.txt", "w") as f:
    f.write("\n".join(results))
