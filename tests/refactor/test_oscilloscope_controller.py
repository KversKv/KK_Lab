# -*- coding: utf-8 -*-
"""
Phase 2 — oscilloscope_controller mock 单测（无 pytest 也可独立运行）。

    python tests/refactor/test_oscilloscope_controller.py
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.controllers import OscilloscopeControllerEx
from instruments.mock.mock_instruments import MockMSO64B


def test_controller_init():
    c = OscilloscopeControllerEx()
    assert c.is_connected is False
    assert c.instrument is None


def test_controller_set_channel_scale_offset():
    c = OscilloscopeControllerEx()
    c._instrument = MockMSO64B()
    logs = []
    c.set_log_callback(logs.append)
    c.set_channel_scale_offset(1, 0.5, 1.8)
    assert any("CH1" in l for l in logs)


def test_controller_set_channel_display():
    c = OscilloscopeControllerEx()
    c._instrument = MockMSO64B()
    logs = []
    c.set_log_callback(logs.append)
    c.set_channel_display(1, True)
    assert any("ON" in l for l in logs)


def test_controller_set_all_channels_default():
    c = OscilloscopeControllerEx()
    c._instrument = MockMSO64B()
    logs = []
    c.set_log_callback(logs.append)
    ok = c.set_all_channels_default(4)
    assert ok is False
    assert any("WARN" in l for l in logs)


def test_controller_run_ripple_test():
    c = OscilloscopeControllerEx()
    c._instrument = MockMSO64B()
    logs = []
    c.set_log_callback(logs.append)
    ok = c.run_ripple_test(1)
    assert ok is False
    assert any("WARN" in l for l in logs)


def test_controller_not_connected():
    c = OscilloscopeControllerEx()
    logs = []
    c.set_log_callback(logs.append)
    c.set_channel_scale_offset(1, 0.5, 1.8)
    assert any("WARN" in l for l in logs)
    ok = c.set_all_channels_default(4)
    assert ok is False


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
