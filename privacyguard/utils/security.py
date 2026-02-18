"""
安全验证工具

v36.5: 模块化拆分，从 main.py 提取
"""

import os
import sys
import tempfile


def validate_safe_path(path, allowed_extensions=None):
    """验证文件路径安全（v36.5: 防止命令注入和路径遍历）

    安全特性:
    - 命令注入防护: 过滤危险字符 (; | & $ ` $( > < \n \r \ %00)
    - 路径遍历防护: 规范化路径并限制允许范围
    - 扩展名验证: 支持白名单机制

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

    # 检查危险字符 (v36.5: 添加反斜杠和空字节检查)
    dangerous_chars = [';', '|', '&', '$', '`', '$(', '>', '<', '\n', '\r', '\\', '%00', '%0a', '%0d']
    for char in dangerous_chars:
        if char in path:
            return False, f"路径包含危险字符: {repr(char)}"

    # 检查空字节注入 (v36.5: 防止空字节绕过)
    if '\x00' in path:
        return False, "路径包含空字节"

    # 规范化路径
    try:
        normalized = os.path.normpath(os.path.abspath(path))
    except (TypeError, ValueError, OSError) as e:
        return False, f"路径格式错误: {e}"

    # 检查路径遍历攻击
    # 获取系统临时目录和用户主目录作为允许范围
    temp_dir = os.path.normpath(os.path.abspath(os.path.expanduser("~")))
    if not normalized.startswith(temp_dir) and not any(
        normalized.startswith(os.path.normpath(os.path.abspath(p)))
        for p in [os.path.expanduser("~"), '/tmp', '/var/tmp', tempfile.gettempdir()]
    ):
        # 允许当前工作目录下的文件
        cwd = os.path.normpath(os.path.abspath('.'))
        if not normalized.startswith(cwd):
            return False, f"路径不在允许范围内: {normalized}"

    # 检查文件名部分
    basename = os.path.basename(normalized)
    if not basename or basename.startswith('.') or '..' in basename:
        return False, "无效的文件名"

    # 检查扩展名
    if allowed_extensions:
        ext = os.path.splitext(basename)[1].lower()
        if ext not in allowed_extensions:
            return False, f"不支持的文件类型: {ext}"

    return True, None


def resource_path(relative_path):
    """获取资源文件路径（支持 PyInstaller 打包）"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
