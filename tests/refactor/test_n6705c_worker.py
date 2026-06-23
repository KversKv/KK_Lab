# -*- coding: utf-8 -*-
"""
Phase 3 — n6705c Worker mock 单测（无 pytest 也可独立运行）。

    python tests/refactor/test_n6705c_worker.py
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.n6705c import ChannelSyncWorker, ConsumptionTestWorker
from instruments.mock.mock_instruments import MockN6705C


def test_channel_sync_worker_init():
    mock = MockN6705C()
    w = ChannelSyncWorker(mock, 1)
    assert w.n6705c is mock
    assert w.channel_num == 1


def test_consumption_worker_init():
    mock = MockN6705C()
    w = ConsumptionTestWorker(mock, "DEV1", [1, 2], 1.0, 0.01)
    assert w.n6705c is mock
    assert w.device_label == "DEV1"
    assert w.channels == [1, 2]
    assert w._is_stopped is False


def test_consumption_worker_stop():
    mock = MockN6705C()
    w = ConsumptionTestWorker(mock, "DEV1", [1], 1.0, 0.01)
    w.stop()
    assert w._is_stopped is True


def test_channel_sync_worker_run():
    mock = MockN6705C()
    w = ChannelSyncWorker(mock, 1)
    received = []
    w.result.connect(lambda d: received.append(d))
    w.run()
    assert len(received) == 1
    data = received[0]
    assert "channel_state" in data
    assert "mode" in data
    assert "voltage" in data
    assert "current" in data


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
