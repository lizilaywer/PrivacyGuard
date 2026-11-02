"""PrivacyGuard 统一日志模块

提供应用级 logging 配置：控制台 + 文件（logs/app.log，按大小滚动）。
替代散落的 print 调试输出，支持日志级别与环境变量控制。

设计要点：
- `init_logging()` 显式初始化根 logger（console + RotatingFileHandler）。
  应在应用入口（`main.py` 的 `__main__`）尽早调用一次。
- `get_logger(name)` 返回命名 logger；未初始化时不自动配置，回退到
  logging 默认行为（WARNING+ 输出到 stderr），保证 import 阶段无副作用。
- 线程安全：logging 模块本身线程安全，OCR worker 子线程可直接使用。
- PyInstaller 兼容：打包后日志目录回退到可执行文件同级 `logs/`。

v37.8.11 P0-3: 引入统一日志框架，替代 main.py / ocr_worker.py 的 print 调试输出。
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

_LOG_DIR_NAME = "logs"
_LOG_FILE_NAME = "app.log"
_LOG_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_LOG_BACKUP_COUNT = 3
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def _resolve_log_dir(base_dir=None):
    """解析日志目录。

    优先级：传入 base_dir > 项目根目录（version.txt 标记）/logs >
    打包环境可执行文件目录/logs。
    """
    if base_dir:
        return Path(base_dir) / _LOG_DIR_NAME
    if getattr(sys, "frozen", False):
        from privacyguard.utils.app_paths import default_config_path
        return Path(default_config_path()).parent / _LOG_DIR_NAME
    here = Path(__file__).resolve().parent  # privacyguard/utils/
    root = here.parent.parent  # 项目根
    if (root / "version.txt").exists():
        return root / _LOG_DIR_NAME
    return root / _LOG_DIR_NAME


def init_logging(level=None, log_dir=None, console=True):
    """初始化应用根日志配置（幂等，重复调用直接返回）。

    Args:
        level: 日志级别；字符串（"DEBUG"/"INFO"/...）或 logging 常量。
               默认从环境变量 ``PG_LOG_LEVEL`` 读取，否则 INFO。
        log_dir: 日志目录；默认自动解析。
        console: 是否启用控制台输出；默认 True。

    Returns:
        logging.Logger: 配置后的根 logger。
    """
    global _initialized
    if _initialized:
        return logging.getLogger()

    if level is None:
        env_level = os.environ.get("PG_LOG_LEVEL", "").upper()
        level = getattr(logging, env_level, logging.INFO) if env_level else logging.INFO
    elif isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    # 清空既有 handler，避免重复叠加
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # 文件 handler（按大小滚动）
    try:
        target_dir = Path(log_dir) if log_dir else _resolve_log_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / _LOG_FILE_NAME
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root.addHandler(file_handler)
        # 安全审计 v40.1.4：日志文件收紧为 0600（含路径/文档片段掩码等信息）
        try:
            os.chmod(file_path, 0o600)
        except OSError:
            pass
    except OSError:
        # 日志目录不可写（只读环境 / 权限不足），降级为仅控制台
        pass

    # 控制台 handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root.addHandler(console_handler)

    _initialized = True
    return root


def get_logger(name="privacyguard"):
    """获取命名 logger。

    未初始化时不自动配置，回退到 logging 默认行为，保证 import 阶段无副作用。
    """
    return logging.getLogger(name)


def is_initialized():
    """返回 logging 是否已显式初始化（便于测试与诊断）。"""
    return _initialized
