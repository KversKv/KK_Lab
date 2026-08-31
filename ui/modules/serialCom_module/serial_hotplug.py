# -*- coding: utf-8 -*-
"""串口热插拔监控（Windows WM_DEVICECHANGE 事件驱动）。

系统串口插拔时自动感知：native event filter 捕获 WM_DEVICECHANGE
（DBT_DEVNODES_CHANGED），去抖后由后台 QThread 重扫 comports()，
端口集合发生变化才广播 ports_changed，避免 UI 线程阻塞 IO。

模块级单例：SerialComMixin 被多个页面混入，所有实例共享同一监控器。
非 Windows 平台 start() 为 no-op。
"""

import sys

import serial
import serial.tools.list_ports

from PySide6.QtCore import (
    QAbstractEventDispatcher, QAbstractNativeEventFilter, QObject,
    QThread, QTimer, Signal,
)

from log_config import get_logger

logger = get_logger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_WM_DEVICECHANGE = 0x0219
_DBT_DEVNODES_CHANGED = 0x0007
_WINDOWS_MSG_TYPE = b"windows_generic_MSG"
_DEBOUNCE_MS = 600


class _DeviceChangeNativeFilter(QAbstractNativeEventFilter):
    """App 级原生消息过滤器：捕获 Windows 设备变化广播。"""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, eventType, message):
        try:
            if eventType != _WINDOWS_MSG_TYPE:
                return False
            import ctypes
            import ctypes.wintypes as _wintypes
            msg = _wintypes.MSG.from_address(int(message))
            if msg.message == _WM_DEVICECHANGE and msg.wParam == _DBT_DEVNODES_CHANGED:
                self._callback()
        except Exception:
            logger.error("设备变化原生消息解析失败", exc_info=True)
        return False


class _PortScanWorker(QObject):
    """后台串口枚举 Worker（线程内运行）。"""

    finished = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            ports = serial.tools.list_ports.comports()
            self.finished.emit([(p.device, p.description) for p in ports])
        except Exception as e:
            self.failed.emit(str(e))


class SerialPortHotplugMonitor(QObject):
    """串口热插拔监控单例。

    - ``ports_changed(list)``：端口集合发生变化时发出，
      参数为 ``["COM3 - description", ...]``（与手动刷新的条目格式一致）；
      首次扫描建立基线时也会发出一次，可用于初始填充。
    - 扫描始终在 QThread 后台执行，不阻塞 UI。
    """

    ports_changed = Signal(list)

    _instance = None

    @classmethod
    def instance(cls) -> "SerialPortHotplugMonitor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter = None
        self._started = False
        self._last_devices = None  # None = 基线未建立
        self._scan_thread = None
        self._scan_worker = None
        self._rescan_pending = False
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(_DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._scan_ports_async)

    def start(self):
        if self._started:
            return
        if not _IS_WINDOWS:
            return
        dispatcher = QAbstractEventDispatcher.instance()
        if dispatcher is None:
            return
        native_filter = _DeviceChangeNativeFilter(self._on_device_event)
        try:
            dispatcher.installNativeEventFilter(native_filter)
        except Exception:
            logger.error("安装设备变化事件过滤器失败", exc_info=True)
            return
        self._filter = native_filter
        self._started = True
        self._scan_ports_async()  # 建立初始基线并广播一次

    def stop(self):
        if self._filter is not None:
            dispatcher = QAbstractEventDispatcher.instance()
            if dispatcher is not None:
                try:
                    dispatcher.removeNativeEventFilter(self._filter)
                except Exception:
                    logger.error("卸载设备变化事件过滤器失败", exc_info=True)
            self._filter = None
        self._debounce_timer.stop()
        self._started = False
        thread = self._scan_thread
        self._scan_thread = None
        self._scan_worker = None
        if thread is not None and thread.isRunning():
            thread.quit()
            if not thread.wait(2000):
                logger.warning("热插拔扫描线程未在超时内退出")

    def _on_device_event(self):
        # native filter 在主线程回调，仅重启去抖计时器
        self._debounce_timer.start()

    def _scan_ports_async(self):
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._rescan_pending = True
            return
        worker = _PortScanWorker()
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_scan_finished)
        worker.failed.connect(self._on_scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_scan_thread_finished)
        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    def _on_scan_thread_finished(self):
        self._scan_thread = None
        self._scan_worker = None
        if self._rescan_pending:
            self._rescan_pending = False
            QTimer.singleShot(0, self._scan_ports_async)

    def _on_scan_finished(self, entries):
        devices = {dev for dev, _desc in entries}
        if self._last_devices is not None and devices == self._last_devices:
            return
        self._last_devices = devices
        self.ports_changed.emit([f"{dev} - {desc}" for dev, desc in entries])

    def _on_scan_failed(self, err):
        logger.error("热插拔后台扫描串口失败: %s", err)
