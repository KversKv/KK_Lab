import logging
import sys


def setup_logging(level=logging.DEBUG):
    fmt = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
