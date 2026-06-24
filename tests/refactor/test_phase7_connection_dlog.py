# -*- coding: utf-8 -*-
"""
Phase 7 — connection_hub 信号聚合 + dlog 导出纯函数单测（无 pytest 也可独立运行）。

    python tests/refactor/test_phase7_connection_dlog.py
"""

import os
import sys
import struct

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal

from core.instruments.connection_hub import ConnectionHub
from instruments.power.keysight.n6705c_datalog_process import build_marker_dlog_bytes


def _ensure_qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeTop(QObject):
    connection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager_set = False

    def set_instrument_manager(self, manager):
        self.manager_set = True
        self._manager = manager


class _FakeManager(QObject):
    sessions_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.shutdown_called = False

    def shutdown(self):
        self.shutdown_called = True


def test_build_marker_dlog_bytes_valid():
    unit_channels = {
        1: {
            "V": {"times": [0.0, 0.001, 0.002], "values": [1000.0, 2000.0, 3000.0], "offset": 0.0},
            "I": {"times": [0.0, 0.001, 0.002], "values": [10.0, 20.0, 30.0], "offset": 0.0},
        }
    }
    blob = build_marker_dlog_bytes(unit_channels, 0.0, 0.005)
    assert blob is not None
    assert blob.startswith(b'<?xml')
    assert b'<dlog>' in blob
    assert b'<tint>0.001</tint>' in blob
    assert b'<points>3</points>' in blob
    assert b'<sense_volt>1</sense_volt>' in blob
    assert b'<sense_curr>1</sense_curr>' in blob
    header_end = blob.find(b'</dlog>') + len(b'</dlog>')
    header = blob[:header_end]
    expected_len = len(header) + 9 + 6 * 4
    assert len(blob) == expected_len
    floats = struct.unpack(">6f", blob[expected_len - 24:])
    assert abs(floats[0] - 1.0) < 1e-6
    assert abs(floats[1] - 0.01) < 1e-6
    assert abs(floats[4] - 3.0) < 1e-6


def test_build_marker_dlog_bytes_empty():
    assert build_marker_dlog_bytes({}, 0.0, 1.0) is None


def test_build_marker_dlog_bytes_no_window():
    unit_channels = {
        1: {
            "V": {"times": [0.0, 0.001, 0.002], "values": [1000.0, 2000.0, 3000.0], "offset": 0.0},
        }
    }
    assert build_marker_dlog_bytes(unit_channels, 100.0, 200.0) is None


def test_connection_hub_properties_and_wiring():
    _ensure_qapp()
    manager = _FakeManager()
    n6705c_top = _FakeTop()
    mso64b_top = _FakeTop()
    hub = ConnectionHub(manager, n6705c_top, mso64b_top)
    assert hub.instrument_manager is manager
    assert hub.n6705c_top is n6705c_top
    assert hub.mso64b_top is mso64b_top
    assert n6705c_top.manager_set is True
    assert mso64b_top.manager_set is True


def test_connection_hub_signal_aggregation():
    _ensure_qapp()
    manager = _FakeManager()
    n6705c_top = _FakeTop()
    mso64b_top = _FakeTop()
    hub = ConnectionHub(manager, n6705c_top, mso64b_top)
    count = {"n": 0}

    def _on_changed():
        count["n"] += 1

    hub.connection_changed.connect(_on_changed)
    n6705c_top.connection_changed.emit()
    mso64b_top.connection_changed.emit()
    manager.sessions_changed.emit()
    assert count["n"] == 3


def test_connection_hub_shutdown_delegates():
    _ensure_qapp()
    manager = _FakeManager()
    hub = ConnectionHub(manager, None, None)
    hub.shutdown()
    assert manager.shutdown_called is True


if __name__ == "__main__":
    _fails = 0
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            try:
                _fn()
                print(f"  PASS  {_name}")
            except Exception as _e:
                _fails += 1
                print(f"  FAIL  {_name}: {_e}")
    print(f"\n{'='*40}\nResult: {len([n for n in globals() if n.startswith('test_')]) - _fails} passed, {_fails} failed")
    sys.exit(1 if _fails else 0)
