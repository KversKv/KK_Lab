"""SerialRxCache：活动串口会话接收数据的进程级环形缓存。

SerialSession 本身只 emit data_received（不保留解码后的文本缓存），
因此 AI 侧需要一份只读 RX 缓存供 SerialContextProvider 取用。

设计：
  - 线程安全（threading.Lock）；
  - 按 session_id 各保留一个定长 deque（按"行"存，零额外增长）；
  - UI 层把 SerialSessionManager.session_data_received 信号喂进 feed()；
  - 只读消费 recent(session_id, n) 返回最近 n 行文本快照。

本模块禁 import Qt（core 层铁律）。
"""
from __future__ import annotations

import threading
from collections import deque

_DEFAULT_LINES_PER_SESSION = 1000


class SerialRxCache:
    """按会话维护的串口接收行缓存。"""

    def __init__(self, max_lines: int = _DEFAULT_LINES_PER_SESSION):
        self._lock = threading.Lock()
        self._max_lines = max_lines
        self._buffers: dict[str, deque[str]] = {}
        self._partial: dict[str, str] = {}

    def feed(self, session_id: str, data: bytes) -> None:
        """喂入一段原始字节（UTF-8 容错解码后按行切分入缓存）。"""
        if not data:
            return
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - 解码兜底，绝不抛出影响串口
            text = repr(data)
        with self._lock:
            buf = self._buffers.get(session_id)
            if buf is None:
                buf = deque(maxlen=self._max_lines)
                self._buffers[session_id] = buf
            combined = self._partial.get(session_id, "") + text
            lines = combined.split("\n")
            self._partial[session_id] = lines.pop()
            for line in lines:
                buf.append(line.rstrip("\r"))

    def recent(self, session_id: str | None, lines: int = 200) -> list[str]:
        if not session_id or lines <= 0:
            return []
        with self._lock:
            buf = self._buffers.get(session_id)
            if buf is None:
                return []
            snapshot = list(buf)
            partial = self._partial.get(session_id, "")
        if partial:
            snapshot = snapshot + [partial]
        if lines >= len(snapshot):
            return snapshot
        return snapshot[-lines:]

    def clear(self, session_id: str | None = None) -> None:
        with self._lock:
            if session_id is None:
                self._buffers.clear()
                self._partial.clear()
            else:
                self._buffers.pop(session_id, None)
                self._partial.pop(session_id, None)
