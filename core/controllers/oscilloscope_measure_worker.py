import threading

from PySide6.QtCore import QObject, QThread, Signal


class MeasurementPollingWorker(QObject):
    results_ready = Signal(list)
    finished = Signal()

    def __init__(self, controller, interval_s=0.5):
        super().__init__()
        self._controller = controller
        self._measurement_items = []
        self._interval_s = interval_s
        self._running = False
        self._lock = threading.Lock()

    def update_items(self, items):
        with self._lock:
            self._measurement_items = list(items)

    def set_interval(self, interval_s):
        self._interval_s = interval_s

    def start_polling(self):
        self._running = True
        while self._running:
            with self._lock:
                snapshot = list(self._measurement_items)
            if not snapshot:
                QThread.msleep(int(self._interval_s * 1000))
                continue
            results = []
            for item in snapshot:
                if not self._running:
                    break
                mtype = item["type"]
                channel = item["channel"]
                try:
                    value = self._query_measurement(channel, mtype)
                    results.append({"type": mtype, "channel": channel, "value": value, "error": None})
                except Exception as e:
                    results.append({"type": mtype, "channel": channel, "value": None, "error": str(e)})
            if self._running and results:
                self.results_ready.emit(results)
            if not self._running:
                break
            QThread.msleep(int(self._interval_s * 1000))
        self.finished.emit()

    def stop(self):
        self._running = False

    @property
    def is_running(self):
        return self._running

    def _query_measurement(self, channel, mtype):
        inst = self._controller.instrument
        if inst is None:
            raise RuntimeError("Instrument not connected")
        func_map = {
            "PK2PK": inst.get_channel_pk2pk,
            "FREQUENCY": inst.get_channel_frequency,
            "MEAN": inst.get_channel_mean,
            "VMAX": inst.get_channel_max,
            "VMIN": inst.get_channel_min,
            "RMS": inst.get_channel_rms,
        }
        func = func_map.get(mtype)
        if func is None:
            raise ValueError(f"Unknown measurement type: {mtype}")
        return func(channel)
