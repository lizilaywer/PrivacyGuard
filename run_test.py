import os
import sys
import tempfile
import platform

# 重定向输出到文件
output_file = open('test_results.txt', 'w', encoding='utf-8')
sys.stdout = output_file
sys.stderr = output_file

def validate_safe_path(path, allowed_extensions=None):
    if not path:
        return False, "路径不能为空"
    if len(path) > 4096:
        return False, "路径过长"
    is_windows = platform.system() == 'Windows'
    shell_metacharacters = [';', '|', '&', '$', '`', '$(', '>', '<', '\n', '\r']
    url_encoded_dangerous = ['%00', '%0a', '%0d']
    for char in shell_metacharacters:
        if char in path:
            return False, f"路径包含危险字符: {repr(char)}"
    if not is_windows and '\\' in path:
        return False, f"路径包含危险字符: {repr('\\')}"
    for seq in url_encoded_dangerous:
        if seq.lower() in path.lower():
            return False, f"路径包含危险序列: {seq}"
    if '\x00' in path:
        return False, "路径包含空字节"
    try:
        normalized = os.path.normpath(os.path.abspath(path))
    except (TypeError, ValueError, OSError) as e:
        return False, f"路径格式错误: {e}"
    allowed_base_dirs = [
        os.path.normpath(os.path.abspath(os.path.expanduser("~"))),
        os.path.normpath(os.path.abspath(tempfile.gettempdir())),
    ]
    if not is_windows:
        for unix_tmp in ['/tmp', '/var/tmp']:
            if os.path.isdir(unix_tmp):
                allowed_base_dirs.append(os.path.normpath(os.path.abspath(unix_tmp)))
    path_in_allowed_dir = any(normalized.startswith(allowed_dir) for allowed_dir in allowed_base_dirs)
    if not path_in_allowed_dir:
        cwd = os.path.normpath(os.path.abspath('.'))
        if not normalized.startswith(cwd):
            return False, f"路径不在允许范围内: {normalized}"
    basename = os.path.basename(normalized)
    if not basename or basename.startswith('.') or '..' in basename:
        return False, "无效的文件名"
    if allowed_extensions:
        ext = os.path.splitext(basename)[1].lower()
        if ext not in allowed_extensions:
            return False, f"不支持的文件类型: {ext}"
    return True, None

print("=" * 50)
print("v37.1 Windows Path Validation Fix Test")
print("=" * 50)
print(f"Platform: {platform.system()}")
print(f"Temp dir: {tempfile.gettempdir()}")
print()

tests = [
    ("Windows normal path", r"C:\Users\Admin\AppData\Local\Temp\test.doc", ['.doc'], True),
    ("Command injection (;)", r"C:\test;rm -rf.doc", ['.doc'], False),
    ("Pipe attack (|)", r"C:\test|cat.doc", ['.doc'], False),
    ("AND attack (&)", r"C:\test&&ls.doc", ['.doc'], False),
    ("Redirect attack (>)", r"C:\test>out.doc", ['.doc'], False),
    ("System temp dir", os.path.join(tempfile.gettempdir(), "source.doc"), ['.doc'], True),
    ("User home dir", os.path.join(os.path.expanduser("~"), "test.doc"), ['.doc'], True),
]

passed = 0
failed = 0

for name, path, exts, expected_safe in tests:
    result, msg = validate_safe_path(path, exts)
    is_safe = result
    status = "PASS" if (is_safe == expected_safe) else "FAIL"

    if is_safe == expected_safe:
        passed += 1
    else:
        failed += 1

    print(f"[{status}] {name}")
    print(f"       Path: {path}")
    print(f"       Result: ({result}, {msg})")
    print(f"       Expected: {'PASS' if expected_safe else 'REJECT'}")
    print()

print("=" * 50)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 50)

if failed == 0:
    print("All tests passed! Windows path validation bug is fixed.")
else:
    print("Some tests failed, please check the code.")

output_file.close()
