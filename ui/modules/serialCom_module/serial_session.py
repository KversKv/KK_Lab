import time
import serial
import serial.tools.list_ports

from PySide6.QtCore import QObject, QThread, Signal

from debug_config import DEBUG_MOCK
from log_config import get_logger

logger = get_logger(__name__)


class SerialSession(QObject):
    connected_changed = Signal(str, bool)
    data_received = Signal(str, bytes)
    error_occurred = Signal(str, str)
    tx_done = Signal(str, int)

    def __init__(self, session_id: str, display_name: str = "", parent=None):
        super().__init__(parent)
        self._session_id = session_id
        self._display_name = display_name or session_id

        self._port = ""
        self._baudrate = 921600
        self._bytesize = 8
        self._stopbits = serial.STOPBITS_ONE
        self._parity = serial.PARITY_NONE
        self._xonxoff = False
        self._rtscts = False

        self._serial_conn = None
        self._connected = False
        self._read_thread: QThread | None = None
        self._read_worker: "_SessionReadWorker | None" = None

        self._rx_bytes = 0
        self._tx_bytes = 0

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def display_name(self) -> str:
        return self._display_name

    @display_name.setter
    def display_name(self, value: str):
        self._display_name = value

    @property
    def port(self) -> str:
        return self._port

    @port.setter
    def port(self, value: str):
        self._port = value

    @property
    def baudrate(self) -> int:
        return self._baudrate

    @baudrate.setter
    def baudrate(self, value: int):
        self._baudrate = value
        if self._serial_conn is not None and self._serial_conn.is_open:
            try:
                self._serial_conn.baudrate = value
            except Exception as e:
                self.error_occurred.emit(self._session_id, f"Set baudrate failed: {e}")

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def serial_conn(self):
        return self._serial_conn

    @property
    def rx_bytes(self) -> int:
        return self._rx_bytes

    @property
    def tx_bytes(self) -> int:
        return self._tx_bytes

    def configure(self, *, port: str = "", baudrate: int = 921600,
                  bytesize: int = 8, stopbits=serial.STOPBITS_ONE,
                  parity=serial.PARITY_NONE, xonxoff: bool = False,
                  rtscts: bool = False):
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._stopbits = stopbits
        self._parity = parity
        self._xonxoff = xonxoff
        self._rtscts = rtscts

    def connect_port(self) -> bool:
        if self._connected:
            return True

        if not self._port:
            self.error_occurred.emit(self._session_id, "No port configured")
            return False

        if DEBUG_MOCK:
            self._serial_conn = None
            self._connected = True
            self._rx_bytes = 0
            self._tx_bytes = 0
            self.connected_changed.emit(self._session_id, True)
            return True

        try:
            conn = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=self._bytesize,
                stopbits=self._stopbits,
                parity=self._parity,
                xonxoff=self._xonxoff,
                rtscts=self._rtscts,
                timeout=0.1,
            )
            self._serial_conn = conn
            self._connected = True
            self._rx_bytes = 0
            self._tx_bytes = 0
            self.connected_changed.emit(self._session_id, True)
            self._start_read()
            return True
        except Exception as e:
            self.error_occurred.emit(self._session_id, f"Connection failed: {e}")
            return False

    def disconnect_port(self):
        if not self._connected:
            return
        self._stop_read()
        try:
            if self._serial_conn is not None and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception as e:
            self.error_occurred.emit(self._session_id, f"Close error: {e}")
        self._serial_conn = None
        self._connected = False
        self.connected_changed.emit(self._session_id, False)

    def send(self, data) -> bool:
        if not self._connected:
            return False

        if DEBUG_MOCK:
            if isinstance(data, str):
                data = data.encode("utf-8")
            byte_count = len(data)
            self._tx_bytes += byte_count
            self.tx_done.emit(self._session_id, byte_count)
            return True

        if self._serial_conn is None or not self._serial_conn.is_open:
            return False
        try:
            if isinstance(data, str):
                data = data.encode("utf-8")
            self._serial_conn.write(data)
            byte_count = len(data)
            self._tx_bytes += byte_count
            self.tx_done.emit(self._session_id, byte_count)
            return True
        except Exception as e:
            self.error_occurred.emit(self._session_id, f"Send error: {e}")
            return False

    def reset_counters(self):
        self._rx_bytes = 0
        self._tx_bytes = 0

    def _start_read(self):
        if self._serial_conn is None or not self._serial_conn.is_open:
            return
        if self._read_thread is not None and self._read_thread.isRunning():
            return

        worker = _SessionReadWorker(self._serial_conn, self._session_id)
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.data_received.connect(self._on_data_received)
        worker.error.connect(self._on_read_error)

        self._read_thread = thread
        self._read_worker = worker
        thread.start()

    def _stop_read(self):
        if self._read_worker is not None:
            self._read_worker.stop()
        if self._read_thread is not None and self._read_thread.isRunning():
            self._read_thread.quit()
            self._read_thread.wait(2000)
        self._read_thread = None
        self._read_worker = None

    def _on_data_received(self, session_id: str, data: bytes):
        self._rx_bytes += len(data)
        self.data_received.emit(session_id, data)

    def _on_read_error(self, session_id: str, err: str):
        self.error_occurred.emit(session_id, f"Read error: {err}")

    def to_config(self) -> dict:
        stopbit_rmap = {
            serial.STOPBITS_ONE: "1",
            serial.STOPBITS_ONE_POINT_FIVE: "1.5",
            serial.STOPBITS_TWO: "2",
        }
        parity_rmap = {
            serial.PARITY_NONE: "None",
            serial.PARITY_EVEN: "Even",
            serial.PARITY_ODD: "Odd",
            serial.PARITY_MARK: "Mark",
            serial.PARITY_SPACE: "Space",
        }
        flow = "None"
        if self._rtscts:
            flow = "RTS/CTS"
        elif self._xonxoff:
            flow = "XON/XOFF"

        return {
            "session_id": self._session_id,
            "display_name": self._display_name,
            "port": self._port,
            "baudrate": self._baudrate,
            "databit": self._bytesize,
            "stopbit": stopbit_rmap.get(self._stopbits, "1"),
            "parity": parity_rmap.get(self._parity, "None"),
            "flow": flow,
        }

    @classmethod
    def from_config(cls, config: dict, parent=None) -> "SerialSession":
        session_id = config.get("session_id", "")
        display_name = config.get("display_name", session_id)
        session = cls(session_id, display_name, parent)

        port = config.get("port", "")
        baudrate = int(config.get("baudrate", 921600))
        bytesize = int(config.get("databit", 8))

        stopbit_map = {
            "1": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO,
        }
        stopbits = stopbit_map.get(str(config.get("stopbit", "1")), serial.STOPBITS_ONE)

        parity_map = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE,
        }
        parity = parity_map.get(config.get("parity", "None"), serial.PARITY_NONE)

        flow = config.get("flow", "None")
        xonxoff = flow == "XON/XOFF"
        rtscts = flow == "RTS/CTS"

        session.configure(
            port=port, baudrate=baudrate, bytesize=bytesize,
            stopbits=stopbits, parity=parity, xonxoff=xonxoff, rtscts=rtscts,
        )
        return session

    def cleanup(self):
        self.disconnect_port()


class _SessionReadWorker(QObject):
    data_received = Signal(str, bytes)
    error = Signal(str, str)

    def __init__(self, serial_conn, session_id: str):
        super().__init__()
        self._serial_conn = serial_conn
        self._session_id = session_id
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                if self._serial_conn is None or not self._serial_conn.is_open:
                    break
                if self._serial_conn.in_waiting > 0:
                    data = self._serial_conn.read(self._serial_conn.in_waiting)
                    if data:
                        self.data_received.emit(self._session_id, data)
                else:
                    QThread.msleep(50)
            except Exception as e:
                if self._running:
                    self.error.emit(self._session_id, str(e))
                break
