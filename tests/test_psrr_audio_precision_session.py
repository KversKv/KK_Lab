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

        session.run_sweep(config, sweep_events.append)
        assert [event["type"] for event in sweep_events] == ["point", "complete"]
        assert session.connected

        session.disconnect()
        assert not session.connected


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

    try:
        page.method_combo.setCurrentIndex(
            page.method_combo.findData("audio_precision")
        )
        page.ap_connect_btn.click()
        wait_for_connection()
        assert page.ap_connected
        assert page.audio_precision is not None
        assert page.audio_precision.connected
        ap = page.audio_precision

        page.ap_connect_btn.click()
        wait_for_connection()
        assert not page.ap_connected
        assert page.audio_precision is None
        assert not ap.connected
    finally:
        if page.ap_connected and not page._ap_connection_busy:
            page.ap_connect_btn.click()
            wait_for_connection()
        page.deleteLater()
        app.processEvents()
