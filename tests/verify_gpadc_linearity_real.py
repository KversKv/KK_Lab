#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GPADC Linearity Auto Best real-hardware verification.

Examples (run from the project root):
    python tests/verify_gpadc_linearity_real.py --dry-run
    python tests/verify_gpadc_linearity_real.py --strategy coarse_fine
    python tests/verify_gpadc_linearity_real.py --strategy unimodal --repeat 3

The saved page configuration is read-only. Only an explicit real run creates
instruments; --dry-run never creates an instrument or I2C object.
"""

import argparse
import hashlib
import json
import logging
import math
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import debug_config  # noqa: E402

debug_config.DEBUG_MOCK = False

from core.pmu_test.gpadc import (  # noqa: E402
    algorithm_length_divisor,
    normalize_linearity_auto_range,
)
from log_config import get_logger  # noqa: E402

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH = PROJECT_ROOT / "user_data" / "page_configs" / "pmu_test" / "gpadc.json"
VOLTAGE_COMPARE_ABS_TOL_V = 1e-3


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Run GPADC linearity Auto Best with the saved page configuration.",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="GPADC JSON path")
    parser.add_argument("--resource", help="N6705C VISA resource; default: n6705c.A preset")
    parser.add_argument(
        "--strategy",
        choices=("coarse_fine", "unimodal"),
        help="Auto Best strategy; default: JSON value or coarse_fine",
    )
    parser.add_argument("--start", help="Override shared Value Start (decimal or 0x hex)")
    parser.add_argument("--end", help="Override shared Value End (decimal or 0x hex)")
    parser.add_argument("--repeat", type=int, help="Override initial Auto Best Repeat (1-10)")
    parser.add_argument("--sample-count", type=int, help="Override final sample points per sweep point")
    parser.add_argument("--voltage-step", type=float, help="Override voltage sweep step in V")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the search estimate without creating instruments or I2C",
    )
    return parser.parse_args()


def _load_saved_config(path):
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8-sig"))
    config = payload.get("config") if isinstance(payload, dict) else None
    if not isinstance(config, dict):
        raise ValueError(f"Missing config object: {path}")
    return config, hashlib.sha256(raw).hexdigest()


def _parse_int(value, *, hex_default=False):
    if isinstance(value, bool):
        raise ValueError(f"Expected an integer, got {value!r}")
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("Integer value is required")
    base = 16 if hex_default or text.lower().startswith("0x") else 10
    return int(text, base)


def _parse_number(value):
    if isinstance(value, str) and value.strip().lower().startswith("0x"):
        number = float(int(value.strip(), 16))
    else:
        number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Expected a finite number, got {value!r}")
    return number


def _build_runner_config(saved, args, strategy):
    link_np = bool(saved["linearity_link_np"])
    auto_best = bool(saved.get("linearity_auto_best", False))
    repeat = args.repeat if args.repeat is not None else int(saved.get("linearity_auto_repeat", 3))
    points = (
        args.sample_count
        if args.sample_count is not None
        else int(saved["sample_count"])
    )
    if not 1 <= repeat <= 10:
        raise ValueError("Repeat must be between 1 and 10")
    if points <= 0:
        raise ValueError("Sample count must be positive")

    voltage_min = _parse_number(saved["voltage_min"])
    voltage_max = _parse_number(saved["voltage_max"])
    voltage_step = (
        args.voltage_step
        if args.voltage_step is not None
        else _parse_number(saved["voltage_step"])
    )
    if voltage_min > voltage_max:
        raise ValueError("Voltage Start must be less than or equal to End")
    if voltage_step <= 0:
        raise ValueError("Voltage step must be positive")

    value_start = args.start if args.start is not None else saved["linearity_value_start"]
    value_end = args.end if args.end is not None else saved["linearity_value_end"]
    normalize_linearity_auto_range(_parse_number(value_start), _parse_number(value_end))
    algorithm = saved.get("algorithm")
    sample_cnt = points * algorithm_length_divisor(algorithm)

    config = {
        "device_addr": _parse_int(saved["iic_device_address"], hex_default=True),
        "reg_addr": _parse_int(saved["iic_data_address"], hex_default=True),
        "iic_weight": _parse_int(saved["iic_width"]),
        "voltage_min": voltage_min,
        "voltage_max": voltage_max,
        "voltage_step": voltage_step,
        "voltage_channel": _parse_int(saved["voltage_channel"]),
        "sample_cnt": sample_cnt,
        "linearity_n_reg_addr": _parse_int(saved["linearity_n_reg_addr"], hex_default=True),
        "linearity_p_reg_addr": _parse_int(saved["linearity_p_reg_addr"], hex_default=True),
        "linearity_link_np": link_np,
        "linearity_auto_best": auto_best,
        "linearity_auto_repeat": repeat,
        "linearity_auto_strategy": strategy,
        "linearity_start": _parse_int(saved["linearity_start"]),
        "linearity_end": _parse_int(saved["linearity_end"]),
        "linearity_value_start": _parse_number(value_start),
        "linearity_value_end": _parse_number(value_end),
        "linearity_value_step": (
            None if link_np and auto_best else _parse_number(saved["linearity_value_step"])
        ),
    }
    for prefix in ("linearity_n", "linearity_p"):
        config[f"{prefix}_start"] = _parse_int(saved[f"{prefix}_start"])
        config[f"{prefix}_end"] = _parse_int(saved[f"{prefix}_end"])
        config[f"{prefix}_value_start"] = _parse_number(saved[f"{prefix}_value_start"])
        config[f"{prefix}_value_end"] = _parse_number(saved[f"{prefix}_value_end"])
        config[f"{prefix}_value_step"] = _parse_number(saved[f"{prefix}_value_step"])
    return config


def _parse_calib_points(saved):
    low_text = str(saved.get("calib_low") or "").strip()
    high_text = str(saved.get("calib_high") or "").strip()
    if not low_text or not high_text:
        return None
    low = _parse_number(low_text)
    high = _parse_number(high_text)
    if low == high:
        raise ValueError("Calibration points must be different")
    return (min(low, high), max(low, high))


def _acquisition_outlier_filter(saved):
    config = saved.get("outlier_filter")
    if not config or not config.get("enabled"):
        return None
    return {
        "pos": _parse_number(config["pos_offset"]),
        "neg": _parse_number(config["neg_offset"]),
    }


def _log_dry_run(config, strategy):
    low, high = normalize_linearity_auto_range(
        config["linearity_value_start"], config["linearity_value_end"],
    )
    integer_points = high - low + 1
    if integer_points > 33:
        coarse_values = list(range(low, high + 1, 0x10))
        if coarse_values[-1] != high:
            coarse_values.append(high)
        coarse_detail = "step=0x10, Start/End included"
    else:
        coarse_values = list(range(low, high + 1))
        coarse_detail = "full range, step=0x1"
    finalist_repeat = min(10, max(3, int(config["linearity_auto_repeat"]) + 2))

    logger.info("DRY-RUN only: no instrument or I2C object will be created")
    logger.info("Strategy: %s", strategy)
    logger.info(
        "Auto range: 0x%X ~ 0x%X; integer points=%d",
        low, high, integer_points,
    )
    logger.info("Coarse points: %d (%s)", len(coarse_values), coarse_detail)
    logger.info("Unique candidate upper bound: %d", integer_points)
    logger.info(
        "Finalist target total Repeat per finalist: %d%s",
        finalist_repeat,
        "" if strategy == "coarse_fine" else " (coarse_fine only)",
    )
    logger.info(
        "Voltage sweep: %.2f ~ %.2f V, step %.2f V, CH%d; raw samples/point=%d",
        config["voltage_min"], config["voltage_max"], config["voltage_step"],
        config["voltage_channel"], config["sample_cnt"],
    )


def _default_resource():
    path = PROJECT_ROOT / "resources" / "instrument_addresses.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    resource = str(payload["n6705c"]["A"]).strip()
    if not resource:
        raise ValueError("resources/instrument_addresses.json: n6705c.A is empty")
    return resource


def _log_status(message, is_error=False):
    logger.log(logging.ERROR if is_error else logging.INFO, "%s", message)


def _read_reg_stable(acquisition, device_addr, reg_addr, width):
    previous = int(acquisition.read_reg(device_addr, reg_addr, width))
    for _ in range(2):
        current = int(acquisition.read_reg(device_addr, reg_addr, width))
        if current == previous:
            return current
        previous = current
    raise RuntimeError(f"Unstable I2C register readback: dev=0x{device_addr:X}, reg=0x{reg_addr:X}")


def _read_state(acquisition, power, config):
    channel = config["voltage_channel"]
    device_addr = config["device_addr"]
    width = config["iic_weight"]
    return {
        "n": _read_reg_stable(
            acquisition, device_addr, config["linearity_n_reg_addr"], width,
        ),
        "p": _read_reg_stable(
            acquisition, device_addr, config["linearity_p_reg_addr"], width,
        ),
        "channel": channel,
        "voltage_v": float(power.measure_voltage(channel)),
        "mode": str(power.get_mode(channel)).strip(),
        "output_enabled": bool(power.get_channel_state(channel)),
    }


def _state_mismatches(before, after):
    mismatches = []
    for key in ("n", "p", "mode", "output_enabled"):
        if before[key] != after[key]:
            mismatches.append(f"{key}: before={before[key]!r}, after={after[key]!r}")
    if not math.isclose(
        before["voltage_v"], after["voltage_v"],
        rel_tol=0.0, abs_tol=VOLTAGE_COMPARE_ABS_TOL_V,
    ):
        mismatches.append(
            f"voltage_v: before={before['voltage_v']:.6f}, "
            f"after={after['voltage_v']:.6f}, "
            f"tolerance={VOLTAGE_COMPARE_ABS_TOL_V:.6f}"
        )
    return mismatches


def _result_status(runner_return, config):
    if not isinstance(runner_return, tuple) or len(runner_return) != 2:
        return False, None, "Runner did not return (kind, result)"
    kind, result = runner_return
    if kind != "linearity_traverse" or not isinstance(result, dict):
        return False, None, "Runner returned no linearity_traverse result"

    groups = result.get("groups") or []
    best_index = result.get("best_index")
    best = None
    if isinstance(best_index, int) and 0 <= best_index < len(groups):
        best = groups[best_index]

    if result.get("stopped"):
        return False, best, "Test was stopped"
    if not groups or best is None:
        return False, best, "No complete Best Evaluated group"
    auto_enabled = config["linearity_link_np"] and config["linearity_auto_best"]
    if auto_enabled:
        auto_search = result.get("auto_search")
        if not isinstance(auto_search, dict) or not auto_search.get("completed"):
            return False, best, "Auto search did not complete"
    return True, best, None


def _write_report(path, report):
    with path.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")


def _run_real(config_path, config_hash_before, saved, config, strategy, resource_override):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = PROJECT_ROOT / "Results"
    results_dir.mkdir(parents=True, exist_ok=True)
    log_path = results_dir / f"gpadc_linearity_real_{timestamp}.log"
    json_path = results_dir / f"gpadc_linearity_real_{timestamp}.json"

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logging.getLogger().addHandler(file_handler)

    power = None
    i2c = None
    acquisition = None
    runner_return = None
    original_state = None
    final_state = None
    mismatches = []
    run_error = None
    verification_error = None
    cleanup_errors = []
    config_hash_after = None
    resource = resource_override
    calib_points = None

    try:
        calib_points = _parse_calib_points(saved)
        logger.info("Configuration: %s", config_path)
        logger.info("Configuration SHA256 before run: %s", config_hash_before)
        logger.info("Strategy: %s", strategy)
        logger.info("Runner config: %s", config)
        logger.info("Calibration points: %s", calib_points)
        logger.info("Algorithm: %s", saved.get("algorithm"))
        logger.info("Outlier filter: %s", saved.get("outlier_filter"))
        if resource is None:
            resource = _default_resource()
        logger.info("N6705C resource: %s", resource)

        from instruments import factory
        from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
        from lib.i2c.i2c_interface_x64 import I2CInterface
        from core.pmu_test.gpadc import GPADCAcquisition, GPADCTestRunner

        power = factory.create_power_analyzer(resource, "auto")
        model = factory.get_power_analyzer_model(power)
        if "N6705" not in model.upper():
            raise RuntimeError(f"A real N6705C is required, detected: {model}")

        iic_speed = I2CSpeedMode(int(saved["iic_speed"]))
        i2c = I2CInterface(speed_mode=iic_speed)
        acquisition = GPADCAcquisition(
            mode="IIC",
            i2c=i2c,
            iic_speed=iic_speed,
            algorithm=saved.get("algorithm"),
            outlier_filter=_acquisition_outlier_filter(saved),
            log_fn=logger.info,
            status_fn=_log_status,
        )
        original_state = _read_state(acquisition, power, config)
        logger.info("Original N/P and power state: %s", original_state)

        runner = GPADCTestRunner(
            acquisition=acquisition,
            n6705c=power,
            n6705c_connected=True,
            mock_mode=False,
            calib_points=calib_points,
            log_fn=logger.info,
            status_fn=_log_status,
        )
        runner_return = runner.run("linearity_traverse", config)
    except (Exception, KeyboardInterrupt) as exc:
        run_error = f"{type(exc).__name__}: {exc}"
        logger.error("GPADC real verification failed: %s", exc, exc_info=True)

    restoration_ok = False
    if original_state is not None and acquisition is not None and power is not None:
        try:
            final_state = _read_state(acquisition, power, config)
            logger.info("Final N/P and power state: %s", final_state)
            mismatches = _state_mismatches(original_state, final_state)
            restoration_ok = not mismatches
            if mismatches:
                logger.error("State restoration mismatch: %s", "; ".join(mismatches))
            else:
                logger.info("Independent N/P and power restoration check passed")
        except Exception as exc:
            verification_error = f"{type(exc).__name__}: {exc}"
            logger.error("Independent state restoration check failed: %s", exc, exc_info=True)

    if power is not None:
        try:
            power.disconnect()
            logger.info("N6705C disconnected")
        except Exception as exc:
            cleanup_errors.append(f"N6705C disconnect: {type(exc).__name__}: {exc}")
            logger.error("N6705C disconnect failed: %s", exc, exc_info=True)
    if i2c is not None:
        try:
            i2c.close()
            logger.info("I2C closed")
        except Exception as exc:
            cleanup_errors.append(f"I2C close: {type(exc).__name__}: {exc}")
            logger.error("I2C close failed: %s", exc, exc_info=True)

    config_unchanged = False
    try:
        config_hash_after = hashlib.sha256(config_path.read_bytes()).hexdigest()
        config_unchanged = config_hash_after == config_hash_before
        logger.info("Configuration SHA256 after run: %s", config_hash_after)
        if not config_unchanged:
            logger.error("Configuration file changed during the run")
    except Exception as exc:
        cleanup_errors.append(f"Configuration hash: {type(exc).__name__}: {exc}")
        logger.error("Configuration final hash failed: %s", exc, exc_info=True)

    completed, best, completion_error = _result_status(runner_return, config)
    if best is not None:
        logger.info(
            "Best Evaluated: N=0x%X, P=0x%X, Max Abs=%s mV, RMS=%s mV",
            int(best["n_value"]), int(best["p_value"]),
            best.get("max_abs_mv"), best.get("rms_mv"),
        )
    if completion_error:
        logger.error("Completion check failed: %s", completion_error)

    report = {
        "timestamp": timestamp,
        "config_path": str(config_path),
        "config_sha256_before": config_hash_before,
        "config_sha256_after": config_hash_after,
        "config_unchanged": config_unchanged,
        "resource": resource,
        "strategy": strategy,
        "runner_config": config,
        "calib_points": calib_points,
        "algorithm": saved.get("algorithm"),
        "outlier_filter": saved.get("outlier_filter"),
        "original_state": original_state,
        "final_state": final_state,
        "restoration_ok": restoration_ok,
        "restoration_mismatches": mismatches,
        "verification_error": verification_error,
        "cleanup_errors": cleanup_errors,
        "run_error": run_error,
        "completed": completed,
        "completion_error": completion_error,
        "runner_return": runner_return,
    }
    report_written = False
    try:
        _write_report(json_path, report)
        report_written = True
        logger.info("Full result JSON: %s", json_path)
    except Exception as exc:
        logger.error("Failed to write result JSON: %s", exc, exc_info=True)

    success = (
        run_error is None
        and completed
        and restoration_ok
        and config_unchanged
        and not cleanup_errors
        and report_written
    )
    logger.info("Verification result: %s", "PASS" if success else "FAIL")
    logger.info("Run log: %s", log_path)
    logging.getLogger().removeHandler(file_handler)
    file_handler.close()
    return 0 if success else 1


def main():
    args = _parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        config_path = Path(args.config).expanduser().resolve()
        saved, config_hash_before = _load_saved_config(config_path)
        strategy = str(
            args.strategy or saved.get("linearity_auto_strategy") or "coarse_fine"
        ).strip().lower()
        if strategy not in ("coarse_fine", "unimodal"):
            raise ValueError(f"Unsupported linearity_auto_strategy: {strategy}")
        config = _build_runner_config(saved, args, strategy)
    except Exception as exc:
        logger.error("Failed to prepare GPADC verification: %s", exc, exc_info=True)
        return 2

    if args.dry_run:
        _log_dry_run(config, strategy)
        return 0
    return _run_real(
        config_path, config_hash_before, saved, config, strategy, args.resource,
    )


if __name__ == "__main__":
    sys.exit(main())
