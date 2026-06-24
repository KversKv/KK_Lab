"""SerialContextProvider：把当前活动串口会话状态 + 最近 RX 翻译成上下文文本。

串口会话由各页面（kk_serials / orchestrator / ...）的 SerialSessionManager 各自持有，
非全局单例。为保持 core 不反向依赖 ui，本类通过两个轻量回调消费：
  - status_getter() -> dict | None：当前活动会话只读状态快照
      {session_id, port, baudrate, connected, rx_bytes, tx_bytes}
  - SerialRxCache：UI 把 session_data_received 喂进来的接收行缓存。
"""
from __future__ import annotations

from typing import Any, Callable

from core.ai.providers.base import ContextProvider
from core.ai.serial_rx_cache import SerialRxCache
from log_config import get_logger

logger = get_logger(__name__)

StatusGetter = Callable[[], "dict[str, Any] | None"]


class SerialContextProvider(ContextProvider):
    def __init__(
        self,
        rx_cache: SerialRxCache,
        status_getter: StatusGetter | None = None,
        max_rx_lines: int = 200,
    ):
        self._rx_cache = rx_cache
        self._status_getter = status_getter
        self._max_rx = max_rx_lines

    def name(self) -> str:
        return "serial"

    def set_limit(self, max_rx_lines: int) -> None:
        self._max_rx = max(0, int(max_rx_lines))

    def status(self) -> dict[str, Any] | None:
        if self._status_getter is None:
            return None
        try:
            return self._status_getter()
        except Exception:  # noqa: BLE001 - 取串口状态失败不应影响上下文构建
            logger.warning("读取串口状态失败", exc_info=True)
            return None

    def recent_rx(self, lines: int | None = None) -> list[str]:
        status = self.status()
        session_id = status.get("session_id") if status else None
        return self._rx_cache.recent(
            session_id, lines if lines is not None else self._max_rx
        )

    def build_context(self, page_key: str | None) -> str:
        status = self.status()
        if not status:
            return ""
        port = status.get("port") or "未配置"
        baud = status.get("baudrate") or "-"
        connected = "已连接" if status.get("connected") else "未连接"
        rx_bytes = status.get("rx_bytes", 0)
        tx_bytes = status.get("tx_bytes", 0)
        head = (
            f"[活动串口] 端口={port} 波特率={baud} 状态={connected} "
            f"RX={rx_bytes}B TX={tx_bytes}B"
        )
        rx_lines = self.recent_rx()
        if rx_lines:
            return head + "\n[最近串口接收 %d 行]\n%s" % (
                len(rx_lines),
                "\n".join(rx_lines),
            )
        return head
