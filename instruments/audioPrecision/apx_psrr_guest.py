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


def _connect_ap(ap):
    ap.connect()
    if bool(getattr(ap.apx, "IsDemoMode", False)):
        raise RuntimeError("APx500 is in Demo Mode; connect the APx525 USB device to the Guest")
    _guest_emit("log", message=f"Guest AP connected; version={ap.apx.Version}")


def _run_sweep(ap, config):
    success = False
    try:
        if config["project_path"]:
            ap.open_project(config["project_path"])
        measurement = ap.configure_psrr_measurement(
            config["signal_path"],
            config["measurement"],
            output_channel=config["output_channel"],
            amplitude_vrms=config["amplitude_vrms"],
            offset_v=config["offset_v"],
            bandwidth_hz=config["bandwidth_hz"],
            generator_on=None,
        )
        measurement = measurement or config["measurement"]
        _guest_emit("log", message=f"Guest AP measurement={measurement}")
        for index, frequency in enumerate(config["frequencies_hz"]):
            ap.set_psrr_generator_frequency(frequency)
            input_frequencies, input_levels = ap.get_signal_analyzer_fft_data(
                config["signal_path"], measurement,
                channel=config["vin_input_channel"] - 1, run=True,
                fft_length=config.get("fft_length", 48000),
                fft_window=config.get("fft_window", "Equiripple"),
                fft_averages=config.get("fft_averages", 5),
            )
            output_frequencies, output_levels = ap.get_signal_analyzer_fft_data(
                config["signal_path"], measurement,
                channel=config["vout_input_channel"] - 1, run=False,
            )
            input_bin_hz, input_dbv = spectrum_level_at_frequency(
                input_frequencies, input_levels, frequency
            )
            output_bin_hz, output_dbv = spectrum_level_at_frequency(
                output_frequencies, output_levels, frequency
            )
            dc_levels = ap.get_psrr_input_dc_levels(config["signal_path"])
            input_dc_v = dc_levels[config["vin_input_channel"] - 1]
            output_dc_v = dc_levels[config["vout_input_channel"] - 1]
            point = {
                "frequency_hz": frequency,
                "input_dbv": input_dbv,
                "output_dbv": output_dbv,
                "input_vrms": 10.0 ** (input_dbv / 20.0),
                "output_vrms": 10.0 ** (output_dbv / 20.0),
                "input_dc_v": input_dc_v,
                "output_dc_v": output_dc_v,
                "input_fft_frequency_hz": input_bin_hz,
                "output_fft_frequency_hz": output_bin_hz,
                "psrr_db": calculate_psrr_from_dbv(input_dbv, output_dbv),
            }
            _guest_emit("point", point=point, index=index)
        success = True
    except Exception as exc:
        _guest_emit("error", message=str(exc))
    if success:
        _guest_emit("complete")
    return success


def _set_output(ap, config, enabled):
    try:
        if enabled:
            if config["project_path"]:
                ap.open_project(config["project_path"])
            ap.configure_psrr_measurement(
                config["signal_path"],
                config["measurement"],
                output_channel=config["output_channel"],
                amplitude_vrms=config["amplitude_vrms"],
                offset_v=config["offset_v"],
                bandwidth_hz=config["bandwidth_hz"],
                generator_on=True,
            )
        else:
            ap.set_psrr_generator_off()
    except Exception as exc:
        _guest_emit("error", message=str(exc))
        return
    _guest_emit("output_complete", enabled=enabled)


def run_psrr_guest(ap_class, config_base64):
    config = json.loads(base64.b64decode(config_base64).decode("utf-8"))
    ap = ap_class()
    failed = False
    try:
        _connect_ap(ap)
        _run_sweep(ap, config)
    except Exception as exc:
        failed = True
        _guest_emit("error", message=str(exc))
    finally:
        try:
            ap.disconnect()
        except Exception as exc:
            if not failed:
                _guest_emit("log", message=f"AP disconnect warning: {exc}")


def run_psrr_guest_session(ap_class):
    ap = ap_class()
    connected = False
    try:
        _connect_ap(ap)
        connected = True
        _guest_emit("connected")
        for raw_line in sys.stdin:
            try:
                request = json.loads(base64.b64decode(raw_line.strip()).decode("utf-8"))
                command = request.get("command")
                if command == "disconnect":
                    ap.set_psrr_generator_off()
                    break
                if command == "output":
                    _set_output(ap, request["config"], bool(request["enabled"]))
                    continue
                if command != "sweep":
                    raise ValueError(f"Unsupported command: {command}")
                _run_sweep(ap, request["config"])
            except Exception as exc:
                _guest_emit("error", message=str(exc))
    except Exception as exc:
        _guest_emit("error", message=str(exc))
    finally:
        try:
            ap.disconnect()
        except Exception as exc:
            if connected:
                _guest_emit("log", message=f"AP disconnect warning: {exc}")
        _guest_emit("disconnected")
