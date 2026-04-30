#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""v37.1 Windows 路径验证修复测试"""

import os
import tempfile
import platform

def validate_safe_path(path, allowed_extensions=None):
    """验证文件路径安全（v37.1: 跨平台兼容修复）"""
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


if __name__ == "__main__":
    print("=" * 50)
    print("v37.1 Windows 路径验证修复测试")
    print("=" * 50)
    print(f"平台: {platform.system()}")
    print(f"临时目录: {tempfile.gettempdir()}")
    print()

    tests = [
        # (名称, 路径, 扩展名, 预期结果)
        ("Windows 正常路径", r"C:\Users\Admin\AppData\Local\Temp\test.doc", ['.doc'], True),
        ("命令注入攻击 (;)", r"C:\test;rm -rf.doc", ['.doc'], False),
        ("管道攻击 (|)", r"C:\test|cat.doc", ['.doc'], False),
        ("AND 攻击 (&)", r"C:\test&&ls.doc", ['.doc'], False),
        ("重定向攻击 (>)", r"C:\test>out.doc", ['.doc'], False),
        ("系统临时目录", os.path.join(tempfile.gettempdir(), "source.doc"), ['.doc'], True),
        ("用户主目录", os.path.join(os.path.expanduser("~"), "test.doc"), ['.doc'], True),
        ("空字节注入", r"C:\test\x00.doc", ['.doc'], False),
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
        print(f"       路径: {path}")
        print(f"       结果: ({result}, {msg})")
        print(f"       预期: {'通过' if expected_safe else '拒绝'}")
        print()

    print("=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    if failed == 0:
        print("所有测试通过! Windows 路径验证 Bug 已修复。")
    else:
        print("存在失败的测试，请检查代码。")
