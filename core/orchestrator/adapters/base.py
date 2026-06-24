from __future__ import annotations

from typing import Any, Callable


class RuntimeInstrumentAdapter:
    """默认 passthrough adapter：保留现有节点调用面。"""

    def __init__(self, instance: object) -> None:
        self.instance = instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self.instance, name)

    @staticmethod
    def _is_stopped(stop_check: Callable[[], bool] | None = None) -> bool:
        if stop_check is None:
            return False
        try:
            return bool(stop_check())
        except Exception:
            return False


class I2CAdapter(RuntimeInstrumentAdapter):
    def read(
        self,
        device_addr: int,
        reg_addr: int,
        width: int,
        *,
        stop_check: Callable[[], bool] | None = None,
    ) -> Any:
        if self._is_stopped(stop_check):
            return None
        if hasattr(self.instance, "read"):
            value = self.instance.read(device_addr, reg_addr, width)
        elif hasattr(self.instance, "read_register"):
            value = self.instance.read_register(device_addr, reg_addr, width)
        else:
            raise RuntimeError("I2C adapter does not expose read()")
        if self._is_stopped(stop_check):
            return None
        return value

    def write(
        self,
        device_addr: int,
        reg_addr: int,
        data: int,
        width: int,
        *,
        stop_check: Callable[[], bool] | None = None,
    ) -> Any:
        if self._is_stopped(stop_check):
            return None
        if hasattr(self.instance, "write"):
            return self.instance.write(device_addr, reg_addr, data, width)
        if hasattr(self.instance, "write_register"):
            return self.instance.write_register(device_addr, reg_addr, data, width)
        raise RuntimeError("I2C adapter does not expose write()")


class UARTAdapter(RuntimeInstrumentAdapter):
    def serial_send(self, payload: bytes) -> bool:
        if hasattr(self.instance, "serial_send"):
            return bool(self.instance.serial_send(payload))
        if hasattr(self.instance, "send"):
            return bool(self.instance.send(payload))
        conn = self.get_serial_connection()
        if conn is None or not hasattr(conn, "write"):
            return False
        conn.write(payload)
        return True

    def write(self, payload: bytes) -> Any:
        conn = self.get_serial_connection()
        if conn is None or not hasattr(conn, "write"):
            raise RuntimeError("UART adapter does not expose write()")
        return conn.write(payload)

    def get_serial_connection(self) -> object | None:
        if hasattr(self.instance, "get_serial_connection"):
            return self.instance.get_serial_connection()
        if hasattr(self.instance, "serial_conn"):
            return self.instance.serial_conn
        return self.instance

    def read_available(
        self,
        max_bytes: int | None = None,
        *,
        stop_check: Callable[[], bool] | None = None,
    ) -> bytes:
        if self._is_stopped(stop_check):
            return b""
        conn = self.get_serial_connection()
        if conn is None or not hasattr(conn, "read"):
            return b""
        waiting = getattr(conn, "in_waiting", 0)
        if waiting <= 0:
            return b""
        size = int(waiting if max_bytes is None else min(waiting, max_bytes))
        return conn.read(size)
