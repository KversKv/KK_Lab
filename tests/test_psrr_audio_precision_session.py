import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest

from core.pmu_test.psrr.audio_precision_session import (
    _PERSISTENT_PYTHON_BOOTSTRAP,
    AudioPrecisionSSHSession,
    remote_config,
    ssh_command,
)
from core.pmu_test.psrr.psrr_analysis import (
    AudioPrecisionPSRRConfig,
    audio_precision_config_from_dict,
)
from core.pmu_test.psrr.psrr_worker import (
    AudioPrecisionOutputWorker,
    AudioPrecisionPSRRWorker,
)
from instruments.audioPrecision import apx_psrr_guest
from instruments.audioPrecision.apx500_driver import APxConnection
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


def _local_transport(session, script):
    def open_transport():
        process = subprocess.Popen(
            [sys.executable, "-u", "-c", _PERSISTENT_PYTHON_BOOTSTRAP],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        session._process = process
        session._reader = process.stdout
        session._writer = process.stdin
        session._send_script(script)

    return open_transport


def test_persistent_ssh_command_uses_line_bootstrap():
    config = AudioPrecisionPSRRConfig()

    persistent = ssh_command(config, persistent=True)
    one_shot = ssh_command(config)

    assert persistent[-1] == f'py -3.12 -u -c "{_PERSISTENT_PYTHON_BOOTSTRAP}"'
    assert one_shot[-1] == "py -3.12 -u -"


def test_audio_precision_input_channel_config_and_remote_payload():
    config = audio_precision_config_from_dict({
        "ap_vin_input_channel": 2,
        "ap_vout_input_channel": 1,
    })

    assert config.vin_input_channel == 2
    assert config.vout_input_channel == 1
    payload = remote_config(config)
    assert payload["vin_input_channel"] == 2
    assert payload["vout_input_channel"] == 1

    with pytest.raises(ValueError, match="VIN 与 VOUT INPUT Channel 不能相同"):
        AudioPrecisionPSRRConfig(vin_input_channel=2, vout_input_channel=2).validate()
    with pytest.raises(ValueError, match="VIN INPUT Channel 必须为 1 或 2"):
        AudioPrecisionPSRRConfig(vin_input_channel=3).validate()


def test_persistent_session_connect_sweep_and_disconnect_without_stdin_eof():
    config = AudioPrecisionPSRRConfig()
    session = AudioPrecisionSSHSession(config)
    connection_events = []
    output_events = []
    sweep_events = []

    with patch.object(
        session, "_open_transport", new=_local_transport(session, _GUEST_SCRIPT)
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
    sweep_points = []
    sweep_logs = []
    sweep_payloads = []

    output_on = AudioPrecisionOutputWorker(config, True, audio_precision=ap)
    output_on.finished.connect(lambda *args: output_results.append(args))
    output_on.run()

    assert output_results == [(True, True, "Audio Precision OUTPUT ON")]
    assert ap.generator_on

    sweep = AudioPrecisionPSRRWorker(config, audio_precision=ap)
    sweep.finished.connect(lambda *args: sweep_results.append(args))
    sweep.point_ready.connect(sweep_points.append)
    sweep.log.connect(sweep_logs.append)
    sweep.result_ready.connect(sweep_payloads.append)
    sweep.start()

    assert sweep_results == [(True, "测试完成")]
    assert ap.run_count == len(config.frequencies_hz)
    assert ap.generator_on
    assert len(sweep_points) == len(config.frequencies_hz)
    for point in sweep_points:
        assert point["input_dc_v"] == pytest.approx(config.offset_v)
        assert point["output_dc_v"] == pytest.approx(1.8)
    assert sweep_payloads[0]["points"] == sweep_points
    data_logs = [line for line in sweep_logs if line.startswith("[DATA]")]
    assert len(data_logs) == len(config.frequencies_hz)
    assert all("VIN DC(INPUT1)=3.800000 V" in line for line in data_logs)
    assert all("VOUT DC(INPUT2)=1.800000 V" in line for line in data_logs)

    output_off = AudioPrecisionOutputWorker(config, False, audio_precision=ap)
    output_off.finished.connect(lambda *args: output_results.append(args))
    output_off.run()

    assert output_results[-1] == (True, False, "Audio Precision OUTPUT OFF")
    assert not ap.generator_on


def test_local_sweep_uses_selected_vin_vout_channels():
    config = AudioPrecisionPSRRConfig(
        connection_mode="local",
        vin_input_channel=2,
        vout_input_channel=1,
        frequencies_hz=(100.0,),
    )
    ap = MockAudioPrecision()
    ap.connect()
    fft_calls = []

    def get_fft_data(signal_path, measurement_name, channel=0, run=True):
        fft_calls.append((channel, run))
        level_dbv = -10.0 if channel == 0 else -40.0
        return [100.0], [level_dbv]

    ap.get_signal_analyzer_fft_data = get_fft_data
    ap.get_psrr_input_dc_levels = lambda signal_path: (3.8, 4.0)
    points = []
    logs = []
    results = []
    payloads = []
    sweep = AudioPrecisionPSRRWorker(config, audio_precision=ap)
    sweep.point_ready.connect(points.append)
    sweep.log.connect(logs.append)
    sweep.finished.connect(lambda *args: results.append(args))
    sweep.result_ready.connect(payloads.append)

    sweep.start()

    assert results == [(True, "测试完成")]
    assert fft_calls == [(1, True), (0, False)]
    assert len(points) == 1
    point = points[0]
    assert point["input_dbv"] == pytest.approx(-40.0)
    assert point["output_dbv"] == pytest.approx(-10.0)
    assert point["psrr_db"] == pytest.approx(-30.0)
    assert point["input_dc_v"] == pytest.approx(4.0)
    assert point["output_dc_v"] == pytest.approx(3.8)
    assert "VIN(INPUT2)=-40.0000 dBV" in logs[-1]
    assert "VOUT DC(INPUT1)=3.800000 V" in logs[-1]
    assert payloads[0]["config"]["ap_vin_input_channel"] == 2
    assert payloads[0]["config"]["ap_vout_input_channel"] == 1


def test_dc_level_reads_live_signal_meters_without_changing_generator():
    connection = APxConnection()
    meter = SimpleNamespace(Count=2, get_Item=Mock(side_effect=(3.8, 1.8)))
    generator = SimpleNamespace(On=True)
    connection.apx = SimpleNamespace(
        SignalMeters=SimpleNamespace(LevelMeter=meter),
        SignalPathSetup=SimpleNamespace(Generator=generator),
    )

    values = connection.get_psrr_input_dc_levels("Signal Path1")

    assert values == (3.8, 1.8)
    assert generator.On
    assert meter.get_Item.call_args_list == [call(0), call(1)]


@pytest.mark.parametrize(
    "vin_input_channel,vout_input_channel,expected_dc",
    ((1, 2, (3.8, 1.8)), (2, 1, (1.8, 3.8))),
)
def test_guest_sweep_records_selected_input_dc_for_each_point(
    monkeypatch, vin_input_channel, vout_input_channel, expected_dc
):
    ap = MockAudioPrecision()
    config = {
        "project_path": "",
        "signal_path": "Signal Path1",
        "measurement": "Signal Analyzer",
        "vin_input_channel": vin_input_channel,
        "vout_input_channel": vout_input_channel,
        "output_channel": 1,
        "amplitude_vrms": 0.1,
        "offset_v": 3.8,
        "bandwidth_hz": 250000,
        "frequencies_hz": [100.0, 1000.0],
    }
    events = []
    fft_calls = []
    original_fft_data = ap.get_signal_analyzer_fft_data

    def get_fft_data(*args, **kwargs):
        fft_calls.append((kwargs["channel"], kwargs["run"]))
        return original_fft_data(*args, **kwargs)

    monkeypatch.setattr(ap, "get_signal_analyzer_fft_data", get_fft_data)
    monkeypatch.setattr(
        apx_psrr_guest,
        "spectrum_level_at_frequency",
        lambda frequencies, levels, frequency: (frequency, levels[1]),
        raising=False,
    )
    monkeypatch.setattr(
        apx_psrr_guest,
        "calculate_psrr_from_dbv",
        lambda input_dbv, output_dbv: input_dbv - output_dbv,
        raising=False,
    )
    monkeypatch.setattr(
        apx_psrr_guest,
        "_guest_emit",
        lambda event_type, **payload: events.append(
            {"type": event_type, **payload}
        ),
    )

    assert apx_psrr_guest._run_sweep(ap, config)

    points = [event["point"] for event in events if event["type"] == "point"]
    assert len(points) == len(config["frequencies_hz"])
    assert ap.run_count == len(config["frequencies_hz"])
    assert fft_calls == [
        (vin_input_channel - 1, True), (vout_input_channel - 1, False)
    ] * len(config["frequencies_hz"])
    for point in points:
        assert point["input_dc_v"] == pytest.approx(expected_dc[0])
        assert point["output_dc_v"] == pytest.approx(expected_dc[1])


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

    with (
        patch.object(
            session, "_open_transport", new=_local_transport(session, script)
        ),
        pytest.raises(RuntimeError, match="boom"),
    ):
        session.connect(lambda event: None)

    assert not session.connected
    assert session._process is None


@pytest.mark.parametrize("output_channel", (1, 2))
def test_psrr_output_on_uses_unbalanced_signal_path_at_100hz(output_channel):
    class _Generator:
        def __init__(self, reject_on):
            self.level_writes = []
            self.Levels = SimpleNamespace(
                TrackFirstChannel=True,
                Unit="",
                OffsetUnit="",
                SetValue=lambda *args: self.level_writes.append(args),
                SetOffsetValue=lambda *args: None,
            )
            self.Frequency = SimpleNamespace(Value=None)
            self.on_writes = []
            self._reject_on = reject_on

        @property
        def On(self):
            return self.on_writes[-1] if self.on_writes else False

        @On.setter
        def On(self, value):
            if value and self._reject_on:
                raise RuntimeError("GeneratorOnNotAvailable")
            self.on_writes.append(value)

    signal_path_generator = _Generator(reject_on=False)
    eq_channels = [SimpleNamespace(Eq="") for _ in range(2)]
    setup = SimpleNamespace(
        OutputConnector=SimpleNamespace(Type=None),
        AnalogInput=SimpleNamespace(ChannelCount=0),
        AnalogOutput=SimpleNamespace(ChannelCount=0),
        AcousticOutput=True,
        OutputEq=SimpleNamespace(Eq=""),
        InputEqChannels=SimpleNamespace(
            TrackFirst=True, get_Item=lambda index: eq_channels[index]
        ),
        Generator=signal_path_generator,
    )
    connection = APxConnection()
    shown_measurements = []
    connection.apx = SimpleNamespace(
        ShowMeasurement=lambda *args: shown_measurements.append(args),
        SignalPathSetup=setup,
    )
    api = SimpleNamespace(
        HighpassFilterMode=SimpleNamespace(DC="DC"),
        InputBandwidthType=SimpleNamespace(Bw250k="Bw250k"),
        LowpassFilterModeAnalog=SimpleNamespace(AdcPassband="AdcPassband"),
        OutputChannelIndex=SimpleNamespace(Ch1="Ch1", Ch2="Ch2"),
        OutputConnectorType=SimpleNamespace(AnalogUnbalanced="AnalogUnbalanced"),
        SignalPathWeightingFilterType=SimpleNamespace(wt_None="None"),
    )

    with (
        patch.dict(
            sys.modules,
            {"AudioPrecision": SimpleNamespace(API=api), "AudioPrecision.API": api},
        ),
        patch.object(connection, "configure_psrr_signal_monitors"),
    ):
        resolved = connection.configure_psrr_measurement(
            "Signal Path1",
            "Signal Analyzer",
            output_channel=output_channel,
            generator_on=True,
        )
        assert signal_path_generator.Frequency.Value == 100.0

        signal_path_generator.Frequency.Value = 1000.0
        connection.configure_psrr_measurement(
            "Signal Path1",
            "Signal Analyzer",
            output_channel=output_channel,
            generator_on=None,
        )

    assert resolved == "Signal Analyzer"
    assert shown_measurements == [
        ("Signal Path1", "Signal Path Setup"),
        ("Signal Path1", "Signal Path Setup"),
    ]
    assert setup.OutputConnector.Type == "AnalogUnbalanced"
    assert setup.AnalogOutput.ChannelCount == 1
    assert not setup.AcousticOutput
    assert setup.OutputEq.Eq == "None"
    assert signal_path_generator.Frequency.Value == 1000.0
    expected_channel = f"Ch{output_channel}"
    assert signal_path_generator.level_writes == [(expected_channel, 0.1)] * 2
    assert signal_path_generator.on_writes == [True]


def test_fft_configuration_checks_spectrum_result():
    connection = APxConnection()
    spectrum = SimpleNamespace(Checked=False)
    analyzer = SimpleNamespace(FFTSpectrum=spectrum)
    connection.apx = SimpleNamespace(
        ActiveMeasurementName="Signal Analyzer",
        SignalAnalyzer=analyzer,
        ShowMeasurement=lambda *args: None,
    )
    api = SimpleNamespace(
        FFTLength=SimpleNamespace(FFT_48000="FFT_48000"),
        WindowType=SimpleNamespace(Equiripple="Equiripple"),
        AveragingType=SimpleNamespace(Power="Power"),
        TriggerType=SimpleNamespace(FreeRun="FreeRun"),
    )

    with (
        patch.dict(
            sys.modules,
            {"AudioPrecision": SimpleNamespace(API=api), "AudioPrecision.API": api},
        ),
        patch.object(
            connection, "resolve_measurement_name", return_value="Signal Analyzer"
        ),
        patch.object(connection, "set_spectrum_unit_dbv"),
    ):
        connection.configure_fft_settings("Signal Path1", "Signal Analyzer")

    assert spectrum.Checked
    assert analyzer.FFTLength == "FFT_48000"
    assert analyzer.WindowType == "Equiripple"
    assert analyzer.AveragingType == "Power"
    assert analyzer.Averages == 7
    assert analyzer.TriggerType == "FreeRun"
    assert analyzer.DelayTimeInSeconds == pytest.approx(0.250)
    assert analyzer.UseDelayTimeInSeconds


@pytest.mark.parametrize("initial_generator_on", [True, False])
def test_fft_monitor_reads_one_frame_without_changing_generator(initial_generator_on):
    connection = APxConnection()
    graph = SimpleNamespace(
        GetXValues=Mock(side_effect=lambda channel: [100.0, 1000.0]),
        GetValues=Mock(side_effect=(
            (
                [SimpleNamespace(X=100.0, Y=-20.0),
                 SimpleNamespace(X=1000.0, Y=-30.0)],
                [SimpleNamespace(X=100.0, Y=-40.0),
                 SimpleNamespace(X=1000.0, Y=-50.0)],
            )
        )),
    )
    monitor = SimpleNamespace(
        FFTSpectrum=graph,
        FFTLength=None,
        WindowType=None,
        Averages=0,
        ResetAverages=Mock(),
    )
    generator = SimpleNamespace(On=initial_generator_on)
    connection.apx = SimpleNamespace(
        SignalMonitorsEnabled=False,
        FftSpectrumSignalMonitor=monitor,
        SignalPathSetup=SimpleNamespace(Generator=generator),
    )
    api = SimpleNamespace(
        FFTLength=SimpleNamespace(FFT_48000="FFT_48000"),
        WindowType=SimpleNamespace(Equiripple="Equiripple"),
    )

    with (
        patch.dict(
            sys.modules,
            {"AudioPrecision": SimpleNamespace(API=api), "AudioPrecision.API": api},
        ),
        patch.object(connection, "set_spectrum_unit_dbv", return_value=[]),
        patch("instruments.audioPrecision.apx500_driver.time.sleep"),
    ):
        frequencies, levels = connection.get_signal_analyzer_fft_data(
            "Signal Path1", "Signal Analyzer", channel=0, run=True
        )
        assert generator.On == initial_generator_on
        second_frequencies, second_levels = connection.get_signal_analyzer_fft_data(
            "Signal Path1", "Signal Analyzer", channel=1, run=False
        )
        assert generator.On == initial_generator_on

    assert frequencies == second_frequencies == [100.0, 1000.0]
    assert levels == [-20.0, -30.0]
    assert second_levels == [-40.0, -50.0]
    assert connection.apx.SignalMonitorsEnabled
    assert monitor.FFTLength == "FFT_48000"
    assert monitor.WindowType == "Equiripple"
    assert monitor.Averages == 7
    monitor.ResetAverages.assert_called_once_with()
    assert graph.GetXValues.call_count == 2
    assert graph.GetValues.call_count == 2


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
    config = page.get_test_config()
    assert config["ap_project_path"] == ""
    assert config["ap_signal_path"] == "Signal Path1"
    assert config["ap_measurement"] == "Signal Analyzer"
    assert config["ap_vin_input_channel"] == 1
    assert config["ap_vout_input_channel"] == 2

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

        applied, _ = page.apply_config_to_controls(
            {"ap_vin_input_channel": 2, "ap_vout_input_channel": 1}, silent=True
        )
        assert applied
        assert page.ap_vin_input_channel_combo.currentData() == 2
        assert page.ap_vout_input_channel_combo.currentData() == 1
        assert page.get_test_config()["ap_vin_input_channel"] == 2
        assert page.get_test_config()["ap_vout_input_channel"] == 1

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
