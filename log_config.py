import logging
import os
import sys


def setup_logging(level=logging.DEBUG):
    fmt = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        stream = sys.stdout if sys.stdout is not None else open(os.devnull, "w")
        handler = logging.StreamHandler(stream)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        root.addHandler(handler)

        if getattr(sys, "frozen", False):
            try:
                _log_dir = os.path.join(
                    os.environ.get("APPDATA", os.path.expanduser("~")),
                    "KK_Lab", "logs"
                )
                os.makedirs(_log_dir, exist_ok=True)
                _log_file = os.path.join(_log_dir, "kk_lab.log")
                fh = logging.FileHandler(_log_file, encoding="utf-8", delay=True)
                fh.setLevel(logging.DEBUG)
                fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
                root.addHandler(fh)
            except Exception:
                pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
