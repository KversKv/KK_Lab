"""进程级 logging 环形缓冲 Handler（供 LogContextProvider 读取最近运行日志）。

设计：
  - 线程安全（threading.Lock），各业务线程的 logger 都会写入；
  - 固定容量（collections.deque(maxlen)），自动丢弃最旧记录，零额外内存增长；
  - 在 setup_logging() 之后挂到 root logger 即可统一捕获所有 get_logger(__name__) 输出；
  - 只读消费：recent(n) 返回最近 n 行已格式化文本快照，不持有可变对象。
"""
from __future__ import annotations

import logging
import threading
from collections import deque

_DEFAULT_CAPACITY = 2000
_FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


class LogRingHandler(logging.Handler):
    """线程安全的环形缓冲日志 Handler。"""

    def __init__(self, capacity: int = _DEFAULT_CAPACITY, level: int = logging.DEBUG):
        super().__init__(level=level)
        self._lock = threading.Lock()
        self._buffer: deque[str] = deque(maxlen=capacity)
        self.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:
            self.handleError(record)
            return
        with self._lock:
            self._buffer.append(line)

    def recent(self, lines: int = 300) -> list[str]:
        if lines <= 0:
            return []
        with self._lock:
            if lines >= len(self._buffer):
                return list(self._buffer)
            return list(self._buffer)[-lines:]

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


_handler: LogRingHandler | None = None
_install_lock = threading.Lock()


def install_log_ring(capacity: int = _DEFAULT_CAPACITY) -> LogRingHandler:
    """把环形 Handler 挂到 root logger（幂等，重复调用返回同一实例）。"""
    global _handler
    with _install_lock:
        if _handler is None:
            _handler = LogRingHandler(capacity=capacity)
            logging.getLogger().addHandler(_handler)
        return _handler


def get_log_ring() -> LogRingHandler | None:
    return _handler
