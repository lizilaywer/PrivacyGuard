"""
安全验证工具

v36.5: 模块化拆分，从 main.py 提取
v37.7.3: 修复 f-string 中的反斜杠语法错误
"""

import os
import sys
import tempfile
import platform


def validate_safe_path(path, allowed_extensions=None):
    """验证文件路径安全（v37.6: 跨平台兼容 + 路径范围校验）

    安全特性:
    - 命令注入防护: 过滤危险字符 (; | & $ ` $( > < \\n \\r)
    - 路径遍历防护: 规范化路径并限制允许范围
    - 扩展名验证: 支持白名单机制
    - 跨平台兼容: Windows 允许反斜杠路径分隔符

    Args:
        path: 要验证的路径
        allowed_extensions: 允许的扩展名列表，如 ['.pdf', '.doc']

    Returns:
        tuple: (is_safe: bool, error_msg: str or None)

    使用示例:
        is_safe, error_msg = validate_safe_path(file_path, allowed_extensions=['.doc'])
        if not is_safe:
            raise SecurityError("文件路径不安全", error_msg)
    """
    if not path:
        return False, "路径不能为空"

    # 检查路径长度
    if len(path) > 4096:
        return False, "路径过长"

    is_windows = platform.system() == "Windows"

    # shell 元字符（命令注入）
    shell_metacharacters = [';', '|', '&', '$', '`', '$(', '>', '<', '\n', '\r']
    for char in shell_metacharacters:
        if char in path:
            char_repr = repr(char)
            return False, f"路径包含危险字符: {char_repr}"

    # URL 编码危险序列
    for seq in ['%00', '%0a', '%0d']:
        if seq.lower() in path.lower():
            return False, f"路径包含危险序列: {seq}"

    # 非 Windows 下拒绝反斜杠（可疑转义）
    # v37.7.3: 修复 f-string 中不能使用反斜杠的语法错误
    backslash_char = '\\'
    if not is_windows and backslash_char in path:
        backslash_repr = repr(backslash_char)
        return False, f"路径包含危险字符: {backslash_repr}"

    # 检查空字节注入 (v36.5: 防止空字节绕过)
    if '\x00' in path:
        return False, "路径包含空字节"

    # 规范化路径
    try:
        normalized = os.path.normpath(os.path.abspath(path))
    except (TypeError, ValueError, OSError) as e:
        return False, f"路径格式错误: {e}"

    # 路径遍历攻击防护：限制在允许目录内
    allowed_base_dirs = [
        os.path.normpath(os.path.abspath(os.path.expanduser("~"))),
        os.path.normpath(os.path.abspath(tempfile.gettempdir())),
    ]
    if not is_windows:
        for unix_tmp in ['/tmp', '/var/tmp']:
            if os.path.isdir(unix_tmp):
                allowed_base_dirs.append(os.path.normpath(os.path.abspath(unix_tmp)))

    def _is_under(base_dir):
        try:
            return os.path.commonpath([normalized, base_dir]) == base_dir
        except ValueError:
            return False

    path_in_allowed = any(_is_under(base) for base in allowed_base_dirs)
    if not path_in_allowed:
        cwd = os.path.normpath(os.path.abspath('.'))
        if not _is_under(cwd):
            return False, f"路径不在允许范围内: {normalized}"

    # 检查文件名部分
    basename = os.path.basename(normalized)
    if not basename or basename.startswith('.') or '..' in basename:
        return False, "无效的文件名"

    # 检查扩展名
    if allowed_extensions:
        allowed_exts = {ext.lower() for ext in allowed_extensions}
        ext = os.path.splitext(basename)[1].lower()
        if ext not in allowed_exts:
            return False, f"不支持的文件类型: {ext}"

    return True, None


def resource_path(relative_path):
    """获取资源文件路径（支持 PyInstaller 打包）"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
