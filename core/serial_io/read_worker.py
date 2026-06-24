from PySide6.QtCore import QObject, QThread, Signal


class SerialReadWorker(QObject):
    data_received = Signal(bytes)
    error = Signal(str)

    def __init__(self, serial_conn):
        super().__init__()
        self._serial_conn = serial_conn
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
                        self.data_received.emit(data)
                else:
                    QThread.msleep(50)
            except Exception as e:
                if self._running:
                    self.error.emit(str(e))
                break
