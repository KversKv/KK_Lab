# -*- coding: utf-8 -*-
"""APx PSRR Guest 执行器；由 SSH Worker 与驱动源码组合后运行。"""
import base64
import json
import sys


def _guest_emit(event_type, **payload):
    event = {"type": event_type, **payload}
    encoded = base64.b64encode(
        json.dumps(event, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    sys.stdout.write(f"KK_LAB_PSRR_EVENT:{encoded}\n")
    sys.stdout.flush()


def run_psrr_guest(ap_class, config_base64):
    config = json.loads(base64.b64decode(config_base64).decode("utf-8"))
    ap = ap_class()
    generator_may_be_on = False
    failed = False
    try:
        ap.connect()
        if bool(getattr(ap.apx, "IsDemoMode", False)):
            raise RuntimeError("APx500 is in Demo Mode; connect the APx525 USB device to the Guest")
        if config["project_path"]:
            ap.open_project(config["project_path"])
        generator_may_be_on = True
        measurement = ap.configure_psrr_measurement(
            config["signal_path"],
            config["measurement"],
            output_channel=config["output_channel"],
            amplitude_vrms=config["amplitude_vrms"],
            offset_v=config["offset_v"],
            bandwidth_hz=config["bandwidth_hz"],
        )
        measurement = measurement or config["measurement"]
        _guest_emit("log", message=f"Guest AP connected; measurement={measurement}")
        for index, frequency in enumerate(config["frequencies_hz"]):
            ap.set_psrr_generator_frequency(frequency)
            input_frequencies, input_levels = ap.get_signal_analyzer_fft_data(
                config["signal_path"], measurement, channel=0, run=True
            )
            output_frequencies, output_levels = ap.get_signal_analyzer_fft_data(
                config["signal_path"], measurement, channel=1, run=False
            )
            input_bin_hz, input_dbv = spectrum_level_at_frequency(
                input_frequencies, input_levels, frequency
            )
            output_bin_hz, output_dbv = spectrum_level_at_frequency(
                output_frequencies, output_levels, frequency
            )
            point = {
                "frequency_hz": frequency,
                "input_dbv": input_dbv,
                "output_dbv": output_dbv,
                "input_vrms": 10.0 ** (input_dbv / 20.0),
                "output_vrms": 10.0 ** (output_dbv / 20.0),
                "input_fft_frequency_hz": input_bin_hz,
                "output_fft_frequency_hz": output_bin_hz,
                "psrr_db": calculate_psrr_from_dbv(input_dbv, output_dbv),
            }
            _guest_emit("point", point=point, index=index)
        _guest_emit("complete")
    except Exception as exc:
        failed = True
        _guest_emit("error", message=str(exc))
    finally:
        if generator_may_be_on:
            try:
                ap.set_psrr_generator_off()
            except Exception as exc:
                failed = True
                _guest_emit("error", message=f"Failed to turn off AP generator: {exc}")
        try:
            ap.disconnect()
        except Exception as exc:
            if not failed:
                _guest_emit("log", message=f"AP disconnect warning: {exc}")
