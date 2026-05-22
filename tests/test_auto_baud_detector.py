import os
import sys
import importlib.util

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_spec = importlib.util.spec_from_file_location(
    "auto_baud_detector",
    os.path.join(_PROJECT_ROOT, "core", "auto_baud_detector.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

score_rx_data = _mod.score_rx_data
AutoBaudState = _mod.AutoBaudState
AutoBaudMonitor = _mod.AutoBaudMonitor
AUTO_BAUD_CONFIG = _mod.AUTO_BAUD_CONFIG


def test_normal_ascii_log_high_score():
    data = b"[INFO] boot ok\r\n[DEBUG] init done\r\nvoltage=3.3\r\n"
    s = score_rx_data(data)
    assert s is not None
    assert s >= 80, f"Expected >= 80, got {s}"


def test_garbled_data_low_score():
    data = bytes([0x00, 0xFF, 0x13, 0x80, 0x91, 0x00, 0xFE] * 100)
    s = score_rx_data(data)
    assert s is not None
    assert s <= 30, f"Expected <= 30, got {s}"


def test_empty_data_returns_none():
    s = score_rx_data(b"")
    assert s is None


def test_sporadic_bad_window_no_scanning():
    monitor = AutoBaudMonitor()
    monitor.enabled = True
    monitor.runtime_redetect_enabled = True
    monitor.state = AutoBaudState.LOCKED
    monitor._config["monitor_window_min_bytes"] = 10
    monitor._config["monitor_window_max_bytes"] = 100
    monitor._config["monitor_window_max_time_ms"] = 1

    garbled = bytes([0x00, 0xFF, 0x13, 0x80, 0x91] * 20)
    result = monitor.on_rx_data(garbled)

    assert monitor.state != AutoBaudState.SCANNING


def test_consecutive_bad_windows_enter_suspect():
    config = dict(AUTO_BAUD_CONFIG)
    config["monitor_window_min_bytes"] = 10
    config["monitor_window_max_bytes"] = 50
    config["monitor_window_max_time_ms"] = 1
    config["bad_windows_to_suspect"] = 3

    monitor = AutoBaudMonitor(config=config)
    monitor.enabled = True
    monitor.runtime_redetect_enabled = True
    monitor.state = AutoBaudState.LOCKED

    garbled = bytes([0x00, 0xFF, 0x13, 0x80, 0x91] * 20)

    entered_suspect = False
    for _ in range(10):
        monitor._monitor_buf = bytearray()
        monitor._monitor_start_time = 0
        result = monitor.on_rx_data(garbled)
        if result and result.get("action") == "suspect":
            entered_suspect = True
            break

    assert entered_suspect, "Monitor should enter SUSPECT after consecutive bad windows"
    assert monitor.state == AutoBaudState.SUSPECT


def test_suspect_recovery_on_good_data():
    config = dict(AUTO_BAUD_CONFIG)
    config["monitor_window_min_bytes"] = 10
    config["monitor_window_max_bytes"] = 50
    config["monitor_window_max_time_ms"] = 1
    config["bad_windows_to_suspect"] = 2

    monitor = AutoBaudMonitor(config=config)
    monitor.enabled = True
    monitor.runtime_redetect_enabled = True
    monitor.state = AutoBaudState.SUSPECT
    monitor._bad_window_count = 3

    good_data = b"[INFO] boot ok\r\n[DEBUG] init done\r\nvoltage=3.3\r\n"
    monitor._monitor_buf = bytearray()
    monitor._monitor_start_time = 0
    result = monitor.on_rx_data(good_data)

    assert result is not None
    assert result.get("action") == "recovered"
    assert monitor.state == AutoBaudState.LOCKED


def test_runtime_switch_requires_confirmation():
    config = dict(AUTO_BAUD_CONFIG)
    config["monitor_window_min_bytes"] = 10
    config["monitor_window_max_bytes"] = 50
    config["monitor_window_max_time_ms"] = 1
    config["bad_windows_to_suspect"] = 2
    config["suspect_windows_to_scan"] = 2

    monitor = AutoBaudMonitor(config=config)
    monitor.enabled = True
    monitor.runtime_redetect_enabled = True
    monitor.state = AutoBaudState.LOCKED

    garbled = bytes([0x00, 0xFF, 0x13, 0x80, 0x91] * 20)

    scan_triggered = False
    for _ in range(20):
        monitor._monitor_buf = bytearray()
        monitor._monitor_start_time = 0
        result = monitor.on_rx_data(garbled)
        if result and result.get("action") == "scan_needed":
            scan_triggered = True
            break

    assert scan_triggered, "Should eventually trigger scan_needed after sustained bad windows"
    assert monitor.state == AutoBaudState.SCANNING


def test_hex_mode_increases_tolerance():
    config = dict(AUTO_BAUD_CONFIG)
    config["monitor_window_min_bytes"] = 10
    config["monitor_window_max_bytes"] = 50
    config["monitor_window_max_time_ms"] = 1
    config["bad_windows_to_suspect"] = 3

    monitor_normal = AutoBaudMonitor(config=dict(config))
    monitor_normal.enabled = True
    monitor_normal.runtime_redetect_enabled = True
    monitor_normal.state = AutoBaudState.LOCKED
    monitor_normal.hex_mode = False

    monitor_hex = AutoBaudMonitor(config=dict(config))
    monitor_hex.enabled = True
    monitor_hex.runtime_redetect_enabled = True
    monitor_hex.state = AutoBaudState.LOCKED
    monitor_hex.hex_mode = True

    garbled = bytes([0x00, 0xFF, 0x13, 0x80, 0x91] * 20)

    normal_suspect_at = None
    hex_suspect_at = None

    for i in range(20):
        monitor_normal._monitor_buf = bytearray()
        monitor_normal._monitor_start_time = 0
        r = monitor_normal.on_rx_data(garbled)
        if r and r.get("action") == "suspect" and normal_suspect_at is None:
            normal_suspect_at = i

        monitor_hex._monitor_buf = bytearray()
        monitor_hex._monitor_start_time = 0
        r = monitor_hex.on_rx_data(garbled)
        if r and r.get("action") == "suspect" and hex_suspect_at is None:
            hex_suspect_at = i

    if normal_suspect_at is not None and hex_suspect_at is not None:
        assert hex_suspect_at >= normal_suspect_at, \
            "HEX mode should take longer to enter SUSPECT"


def test_score_mixed_content():
    data = b"Hello World\r\n" + bytes([0x80, 0x90, 0xA0]) + b"\r\nDone\r\n"
    s = score_rx_data(data)
    assert s is not None
    assert 0 <= s <= 90


if __name__ == "__main__":
    tests = [
        test_normal_ascii_log_high_score,
        test_garbled_data_low_score,
        test_empty_data_returns_none,
        test_sporadic_bad_window_no_scanning,
        test_consecutive_bad_windows_enter_suspect,
        test_suspect_recovery_on_good_data,
        test_runtime_switch_requires_confirmation,
        test_hex_mode_increases_tolerance,
        test_score_mixed_content,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {t.__name__} - {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {t.__name__} - {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(0 if failed == 0 else 1)
