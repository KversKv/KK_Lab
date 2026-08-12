import logging
import os
import sys


def setup_logging(level=logging.DEBUG):
    fmt = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)

    frozen = getattr(sys, "frozen", False)
    if frozen:
        # windowed 打包下 stdout/stderr fd 已被引导器关闭：
        # 1) 清掉任何在 setup_logging 之前被挂上的流式 handler；
        # 2) 关闭 raiseExceptions + lastResort，避免退出阶段再向坏 fd 报错。
        for h in list(root.handlers):
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
                root.removeHandler(h)
        logging.raiseExceptions = False
        logging.lastResort = None

    if not root.handlers:
        if not frozen:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)
            handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
            root.addHandler(handler)

        if frozen:
            try:
                _log_dir = os.path.join(
                    os.environ.get("APPDATA", os.path.expanduser("~")),
                    "KK_Lab", "logs"
                )
                os.makedirs(_log_dir, exist_ok=True)
                _log_file = os.path.join(_log_dir, "kk_lab.log")
                # delay=True 延迟打开；errors="replace" 防止编码问题
                fh = logging.FileHandler(_log_file, encoding="utf-8", delay=True, errors="replace")
                fh.setLevel(logging.DEBUG)
                fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
                root.addHandler(fh)
            except Exception:
                pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
