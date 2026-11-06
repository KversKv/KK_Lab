import sys
import time
from unittest.mock import patch

import pytest

from core.pmu_test.psrr.audio_precision_session import (
    _PERSISTENT_PYTHON_BOOTSTRAP,
    AudioPrecisionSSHSession,
    ssh_command,
)
from core.pmu_test.psrr.psrr_analysis import AudioPrecisionPSRRConfig
from core.pmu_test.psrr.psrr_worker import (
    AudioPrecisionOutputWorker,
    AudioPrecisionPSRRWorker,
)
from instruments.mock.mock_instruments import MockAudioPrecision


_GUEST_SCRIPT = """
import base64
import json
import sys


def emit(event_type, **payload):
    event = {"type": event_type, **payload}
    encoded = base64.b64encode(json.dumps(event).encode("utf-8")).decode("ascii")
    sys.stdout.write(f"KK_LAB_PSRR_EVENT:{encoded}\\n")
    sys.stdout.flush()


emit("connected")
for raw_line in sys.stdin:
    request = json.loads(base64.b64decode(raw_line.strip()).decode("utf-8"))
    if request["command"] == "disconnect":
        break
    if request["command"] == "output":
        emit("output_complete", enabled=request["enabled"])
    if request["command"] == "sweep":
        emit("point", point={"frequency_hz": 100.0}, index=0)
        emit("complete")
emit("disconnected")
"""


def test_persistent_ssh_command_uses_line_bootstrap():
    config = AudioPrecisionPSRRConfig()

    persistent = ssh_command(config, persistent=True)
    one_shot = ssh_command(config)

    assert persistent[-1] == f'py -3.12 -u -c "{_PERSISTENT_PYTHON_BOOTSTRAP}"'
    assert one_shot[-1] == "py -3.12 -u -"


def test_persistent_session_connect_sweep_and_disconnect_without_stdin_eof():
    config = AudioPrecisionPSRRConfig()
    local_command = [sys.executable, "-u", "-c", _PERSISTENT_PYTHON_BOOTSTRAP]
    session = AudioPrecisionSSHSession(config)
    connection_events = []
    output_events = []
    sweep_events = []

    with (
        patch(
            "core.pmu_test.psrr.audio_precision_session.ssh_command",
            return_value=local_command,
        ),
        patch(
            "core.pmu_test.psrr.audio_precision_session.build_remote_script",
            return_value=_GUEST_SCRIPT,
        ),
    ):
        session.connect(connection_events.append)
        assert session.connected
        assert [event["type"] for event in connection_events] == ["connected"]

        session.set_output(config, True, output_events.append)
        assert output_events == [{"type": "output_complete", "enabled": True}]

        session.run_sweep(config, sweep_events.append)
        assert [event["type"] for event in sweep_events] == ["point", "complete"]
        assert session.connected

        session.set_output(config, False, output_events.append)
        assert output_events[-1] == {"type": "output_complete", "enabled": False}

        session.disconnect()
        assert not session.connected


def test_local_output_stays_on_during_sweep_until_manual_off():
    config = AudioPrecisionPSRRConfig(
        connection_mode="local", frequencies_hz=(100.0, 1000.0)
    )
    ap = MockAudioPrecision()
    ap.connect()
    output_results = []
    sweep_results = []

    output_on = AudioPrecisionOutputWorker(config, True, audio_precision=ap)
    output_on.finished.connect(lambda *args: output_results.append(args))
    output_on.run()

    assert output_results == [(True, True, "Audio Precision OUTPUT ON")]
    assert ap.generator_on

    sweep = AudioPrecisionPSRRWorker(config, audio_precision=ap)
    sweep.finished.connect(lambda *args: sweep_results.append(args))
    sweep.start()

    assert sweep_results == [(True, "测试完成")]
    assert ap.run_count == len(config.frequencies_hz)
    assert ap.generator_on

    output_off = AudioPrecisionOutputWorker(config, False, audio_precision=ap)
    output_off.finished.connect(lambda *args: output_results.append(args))
    output_off.run()

    assert output_results[-1] == (True, False, "Audio Precision OUTPUT OFF")
    assert not ap.generator_on


def test_persistent_session_connect_failure_terminates_process():
    script = """
import base64
import json
import sys
payload = base64.b64encode(
    json.dumps({"type": "error", "message": "boom"}).encode()
).decode()
sys.stdout.write(f"KK_LAB_PSRR_EVENT:{payload}\\n")
sys.stdout.flush()
sys.stdin.readline()
"""
    session = AudioPrecisionSSHSession(AudioPrecisionPSRRConfig())
    local_command = [sys.executable, "-u", "-c", _PERSISTENT_PYTHON_BOOTSTRAP]

    with (
        patch(
            "core.pmu_test.psrr.audio_precision_session.ssh_command",
            return_value=local_command,
        ),
        patch(
            "core.pmu_test.psrr.audio_precision_session.build_remote_script",
            return_value=script,
        ),
        pytest.raises(RuntimeError, match="boom"),
    ):
        session.connect(lambda event: None)

    assert not session.connected
    assert session._process is None


@pytest.mark.qt
def test_psrr_page_mock_connect_and_disconnect(monkeypatch):
    from PySide6.QtWidgets import QApplication

    import debug_config
    from ui.pages.pmu_test import pmu_psrr_ui

    class _ConfigMemoryStub:
        def __init__(self, *args):
            pass

        def bind_interface(self, *args):
            pass

        def watch(self, *args):
            pass

        def restore(self):
            pass

    monkeypatch.setattr(debug_config, "DEBUG_MOCK", True)
    monkeypatch.setattr(pmu_psrr_ui, "DEBUG_MOCK", True)
    monkeypatch.setattr(pmu_psrr_ui, "ConfigMemory", _ConfigMemoryStub)
    app = QApplication.instance() or QApplication([])
    page = pmu_psrr_ui.PMUPSRRUI()
    page.show()
    app.processEvents()

    def wait_for_connection():
        deadline = time.monotonic() + 5.0
        while (
            page._ap_connection_busy or page._ap_connection_thread is not None
        ) and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()
        assert not page._ap_connection_busy
        assert page._ap_connection_thread is None

    def wait_for_output():
        deadline = time.monotonic() + 5.0
        while (
            page._ap_output_busy or page._ap_output_thread is not None
        ) and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()
        assert not page._ap_output_busy
        assert page._ap_output_thread is None

    def wait_for_test():
        deadline = time.monotonic() + 5.0
        while (
            page.is_test_running or page.test_thread is not None
        ) and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()
        assert not page.is_test_running
        assert page.test_thread is None

    try:
        page.method_combo.setCurrentIndex(
            page.method_combo.findData("audio_precision")
        )
        page.ap_connect_btn.setFocus()
        page.ap_connect_btn.click()
        assert page.ap_connection_toggle_btn.hasFocus()
        assert not page.ap_project_edit.hasFocus()
        wait_for_connection()
        assert page.ap_connected
        assert page.audio_precision is not None
        assert page.audio_precision.connected
        assert page.ap_connection_content.isHidden()
        ap = page.audio_precision

        page.start_test_btn.click()
        assert not page.is_test_running
        assert page.test_thread is None

        page.ap_output_channel_combo.setCurrentIndex(1)
        page.ap_amplitude_spin.setValue(120.0)
        page.ap_offset_spin.setValue(4.0)
        page.ap_output_toggle_btn.click()
        wait_for_output()
        assert page._ap_output_on
        assert ap.generator_on
        assert ap.psrr_settings["output_channel"] == 2
        assert ap.psrr_settings["amplitude_vrms"] == pytest.approx(0.12)
        assert ap.psrr_settings["offset_v"] == pytest.approx(4.0)
        assert not page.ap_output_channel_combo.isEnabled()
        assert not page.ap_amplitude_spin.isEnabled()
        assert not page.ap_offset_spin.isEnabled()
        assert not page.method_combo.isEnabled()

        applied, _ = page.apply_config_to_controls(
            {"ap_amplitude_mvrms": 200.0}, silent=True
        )
        assert not applied
        assert page.ap_amplitude_spin.value() == pytest.approx(120.0)

        page.ap_frequency_points_spin.setValue(2)
        page.start_test_btn.click()
        wait_for_test()
        assert page.result_status_label.text() == "DONE"
        assert page._ap_output_on
        assert ap.generator_on
        assert page.ap_output_toggle_btn.isEnabled()

        page.ap_output_toggle_btn.click()
        wait_for_output()
        assert not page._ap_output_on
        assert not ap.generator_on
        assert page.ap_output_channel_combo.isEnabled()
        assert page.ap_amplitude_spin.isEnabled()
        assert page.ap_offset_spin.isEnabled()
        assert page.method_combo.isEnabled()

        page.ap_output_toggle_btn.click()
        wait_for_output()
        assert page._ap_output_on
        page.ap_connection_toggle_btn.click()
        assert not page.ap_connection_content.isHidden()
        page.ap_connection_toggle_btn.click()
        assert page.ap_connection_content.isHidden()

        page.ap_connect_btn.click()
        wait_for_connection()
        assert not page.ap_connected
        assert page.audio_precision is None
        assert not page._ap_output_on
        assert not ap.generator_on
        assert not ap.connected
        assert not page.ap_output_toggle_btn.isEnabled()
    finally:
        if page.is_test_running:
            page.stop_test()
            wait_for_test()
        if page._ap_output_busy or page._ap_output_thread is not None:
            wait_for_output()
        if page.ap_connected and not page._ap_connection_busy:
            page.ap_connect_btn.click()
            wait_for_connection()
        page.deleteLater()
        app.processEvents()
