# -*- coding: utf-8 -*-
"""cp90: 使用痕迹清理纯逻辑模块（D1 铁律：不依赖 GUI/Qt）。

- 目录大小统计与人类可读格式化
- 痕迹项汇总（草稿/临时文件/预览缓存/日志）
- 白名单校验删除（硬约束：只删应用自有目录，绝不越界触碰用户文档）
"""
import os
import shutil


# WebEngine 被占用时延迟到下次启动清除的标记文件名（写入 sessions 同级目录）
WEBENGINE_PENDING_MARKER = "webengine_clear_pending"


def write_pending_webengine(marker_path, dirs):
    """cp90: 写 WebEngine 延迟清除标记（每行一个待清目录）。失败返回 False。"""
    try:
        parent = os.path.dirname(marker_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write("\n".join(d for d in (dirs or []) if d))
        return True
    except OSError:
        return False


def clear_pending_webengine(marker_path, allowed_roots=None):
    """cp90: 读取标记并删除其中列出的目录，随后删除标记文件。

    在启动早期（WebEngine 未初始化、无占用）调用可安全清除。
    返回删除的目录数；标记不存在返回 0；全程异常安全。

    安全修复: allowed_roots 白名单校验——每个待删路径必须位于
    allowed_roots 之一，否则拒绝删除（防止标记文件被篡改后注入
    任意目录路径）。默认 allowed_roots 为标记文件父目录 + 系统 temp。
    """
    if not marker_path or not os.path.exists(marker_path):
        return 0
    # 默认白名单：标记文件父目录（sessions dir）+ 系统 temp
    if allowed_roots is None:
        _parent = os.path.dirname(marker_path)
        import tempfile as _tf
        allowed_roots = [_parent, _tf.gettempdir()]
    roots = [r for r in (allowed_roots or []) if r]
    removed = 0
    try:
        with open(marker_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return 0
    for line in lines:
        line = line.strip()
        if line and os.path.isdir(line):
            # 白名单校验：路径必须位于 allowed_roots 之一
            if roots and not any(_is_within(line, r) for r in roots):
                continue
            try:
                shutil.rmtree(line, ignore_errors=True)
                removed += 1
            except OSError:
                continue
    try:
        os.remove(marker_path)
    except OSError:
        pass
    return removed


def dir_size_bytes(path):
    """递归统计路径大小（字节）。文件直接取 size；目录累加；不存在/异常计 0。"""
    if not path or not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total


def format_size(n):
    """字节数 → 人类可读（B/KB/MB/GB）。"""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def collect_trace_items(sessions_dir=None, temp_entries=None,
                        web_cache_dirs=None, log_files=None):
    """汇总痕迹项。

    Returns:
        [{key, label, paths, size_bytes, default_checked}]。
        sessions/temp/webengine 默认勾选；logs 默认不勾（排障有用）。
        无有效路径（大小 0 且路径为空）的项仍返回，由 UI 决定是否隐藏。
    """
    def _paths_size(paths):
        return sum(dir_size_bytes(p) for p in paths)

    items = []
    sessions_paths = [sessions_dir] if sessions_dir else []
    items.append({
        "key": "sessions", "label": "脱敏进度草稿",
        "paths": sessions_paths, "size_bytes": _paths_size(sessions_paths),
        "default_checked": True,
    })
    temp_paths = list(temp_entries or [])
    items.append({
        "key": "temp", "label": "临时文件（含崩溃残留）",
        "paths": temp_paths, "size_bytes": _paths_size(temp_paths),
        "default_checked": True,
    })
    web_paths = [p for p in (web_cache_dirs or []) if p]
    items.append({
        "key": "webengine", "label": "预览渲染缓存",
        "paths": web_paths, "size_bytes": _paths_size(web_paths),
        "default_checked": True,
    })
    log_paths = list(log_files or [])
    items.append({
        "key": "logs", "label": "运行日志",
        "paths": log_paths, "size_bytes": _paths_size(log_paths),
        "default_checked": False,
    })
    return items


def _is_within(path, root):
    """path 是否位于 root 之内（含 root 自身）。用 realpath 归一，杜绝 .. 越界。"""
    try:
        rp = os.path.realpath(path)
        rr = os.path.realpath(root)
    except OSError:
        return False
    if rp == rr:
        return True
    return rp.startswith(rr + os.sep)


def clean_paths(paths, allowed_roots):
    """白名单校验删除。

    每个待删路径必须位于 allowed_roots 之一，否则拒绝并计入 errors（硬约束，
    防止配置错误或路径注入导致误删用户文档）。

    Returns: (deleted_count, freed_bytes, errors)
    """
    deleted = 0
    freed = 0
    errors = []
    roots = [r for r in (allowed_roots or []) if r]
    for path in (paths or []):
        if not path or not os.path.exists(path):
            continue
        if not any(_is_within(path, r) for r in roots):
            errors.append(f"拒绝删除白名单外路径: {path}")
            continue
        size = dir_size_bytes(path)
        try:
            # 安全审计 v40.1: symlink 逃逸防护——
            # shutil.rmtree 对 symlink 目录会跟随删除其指向的真实内容（经典坑）。
            # 先判断 islink，是链接则只删链接本身（os.unlink），不跟随。
            if os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            deleted += 1
            freed += size
        except OSError as e:
            # 被占用（Windows 常见）等：跳过并记录
            errors.append(f"{os.path.basename(path)}: {e}")
    return deleted, freed, errors
