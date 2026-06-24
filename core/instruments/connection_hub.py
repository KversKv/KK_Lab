from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QObject, Signal

from log_config import get_logger

if TYPE_CHECKING:
    from core.instruments.instrument_manager import InstrumentManager

logger = get_logger(__name__)


class ConnectionHub(QObject):
    """连接状态共享中枢。

    聚合三类连接源——双 N6705C（``N6705CTop``）、示波器（``MSO64BTop``）与
    通用 ``InstrumentManager``（温箱等）——对外暴露统一的 ``connection_changed``
    信号，供 ``MainWindow`` / 状态栏单点订阅，避免上层分别连线三处信号。

    仅依赖 ``QtCore``，不引入 ``QtWidgets``，符合 ``core/`` 分层铁律。
    两个 top 由 ``ui`` 层注入（它们本身也是 ``QObject``），hub 不反向 import
    ``ui``，保持 ``core`` 不依赖 ``ui`` 的方向。
    """

    connection_changed = Signal()

    def __init__(
        self,
        instrument_manager: "InstrumentManager",
        n6705c_top: Optional[QObject] = None,
        mso64b_top: Optional[QObject] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._manager = instrument_manager
        self._n6705c_top = n6705c_top
        self._mso64b_top = mso64b_top

        if n6705c_top is not None and hasattr(n6705c_top, "set_instrument_manager"):
            n6705c_top.set_instrument_manager(instrument_manager)
        if mso64b_top is not None and hasattr(mso64b_top, "set_instrument_manager"):
            mso64b_top.set_instrument_manager(instrument_manager)

        if n6705c_top is not None:
            n6705c_top.connection_changed.connect(self.connection_changed)
        if mso64b_top is not None:
            mso64b_top.connection_changed.connect(self.connection_changed)
        if instrument_manager is not None:
            instrument_manager.sessions_changed.connect(self.connection_changed)

    @property
    def instrument_manager(self) -> "InstrumentManager":
        return self._manager

    @property
    def n6705c_top(self) -> Optional[QObject]:
        return self._n6705c_top

    @property
    def mso64b_top(self) -> Optional[QObject]:
        return self._mso64b_top

    def shutdown(self) -> None:
        if self._manager is not None:
            self._manager.shutdown()
