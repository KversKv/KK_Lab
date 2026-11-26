# -*- coding: utf-8 -*-
"""后台诊断日志（叶子模块，纯 stdlib，禁 Qt）。

用途：内测闪退排查。只落盘系统操作（[INFO]）、警告（[WARN]）、异常与 ERROR，
绝不写入原始 RX 数据。

落盘位置：与用户 JSON 同目录（_sc_user_config_dir()）。
轮转策略：serial_diag.log 单文件上限 1MB，写满后循环替换尾缀 .1 → .5
（RotatingFileHandler，最新备份恒为 .1，最旧 .5 被覆盖），总量约 6MB 封顶。

崩溃捕获：
- sys.excepthook / threading.excepthook 链式接管：未捕获 Python 异常先落盘再走原 hook；
- faulthandler → serial_crash.log：原生崩溃（segfault / abort）时写 C 级线程栈。
"""

import faulthandler
import logging
import logging.handlers
import os
import sys
import threading

_DIAG_LOGGER_NAME = "kk_serial_diag"
_DIAG_FILENAME = "serial_diag.log"
_CRASH_FILENAME = "serial_crash.log"
_MAX_BYTES = 1024 * 1024
_BACKUP_COUNT = 5
_CRASH_MAX_BYTES = 512 * 1024

# 这些 logger 子树的 WARNING+ 记录（含 exc_info 栈）同步进诊断日志
_WATCHED_LOGGERS = (
    "ui.modules.serialCom_module",
    "core.serial_io",
    "core.serial_script",
    "core.auto_baud_detector",
)

_enabled = False
_crash_handle = None
_logger = logging.getLogger(_DIAG_LOGGER_NAME)


class _DiagFilter(logging.Filter):
    """诊断 logger 自身 INFO+ 放行；其余被挂接 logger 只放行 WARNING+。"""

    def filter(self, record):
        return record.name == _DIAG_LOGGER_NAME or record.levelno >= logging.WARNING


def setup(config_dir: str, session_info: str = "") -> bool:
    """初始化诊断日志（幂等，多页面/多实例共享同一份）。失败不影响 UI。"""
    global _enabled
    if _enabled:
        return True
    try:
        os.makedirs(config_dir, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(config_dir, _DIAG_FILENAME),
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
            delay=True,
            errors="replace",
        )
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        handler.addFilter(_DiagFilter())
        _logger.setLevel(logging.INFO)
        _logger.propagate = False
        _logger.addHandler(handler)
        for name in _WATCHED_LOGGERS:
            logging.getLogger(name).addHandler(handler)
        _install_excepthooks()
        _enable_faulthandler(config_dir)
        _enabled = True
        _logger.info(
            "==== Session start (pid=%s%s) ====",
            os.getpid(), f", {session_info}" if session_info else "",
        )
        return True
    except Exception:
        logging.getLogger(__name__).warning(
            "serial diag log setup failed", exc_info=True
        )
        return False


def record_system(message: str) -> None:
    """系统消息入口（_sc_append_system / 浮窗系统行统一调用），按标签分级。"""
    if not _enabled:
        return
    if "[ERROR]" in message:
        _logger.error(message)
    elif "[WARN]" in message:
        _logger.warning(message)
    else:
        _logger.info(message)


def _install_excepthooks() -> None:
    prev_sys_hook = sys.excepthook

    def _sys_hook(exc_type, exc_value, exc_tb):
        try:
            _logger.critical(
                "Uncaught exception", exc_info=(exc_type, exc_value, exc_tb)
            )
        except Exception:
            pass
        if prev_sys_hook is not None:
            prev_sys_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _sys_hook

    prev_thread_hook = threading.excepthook

    def _thread_hook(args):
        try:
            thread_name = args.thread.name if args.thread is not None else "?"
            _logger.critical(
                "Uncaught thread exception (%s)", thread_name,
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )
        except Exception:
            pass
        if prev_thread_hook is not None:
            prev_thread_hook(args)

    threading.excepthook = _thread_hook


def _enable_faulthandler(config_dir: str) -> None:
    global _crash_handle
    try:
        path = os.path.join(config_dir, _CRASH_FILENAME)
        mode = "a"
        if os.path.isfile(path) and os.path.getsize(path) > _CRASH_MAX_BYTES:
            mode = "w"
        _crash_handle = open(path, mode, encoding="utf-8")
        _crash_handle.write(f"\n==== Session start pid={os.getpid()} ====\n")
        _crash_handle.flush()
        faulthandler.enable(file=_crash_handle, all_threads=True)
    except Exception:
        logging.getLogger(__name__).warning(
            "serial crash faulthandler setup failed", exc_info=True
        )
