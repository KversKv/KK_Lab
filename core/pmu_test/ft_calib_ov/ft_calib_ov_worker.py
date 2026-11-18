# -*- coding: utf-8 -*-
"""FT Calibration Check - Output Voltage Check Worker（仅依赖 QtCore）。

逐 rail 流程：读 EFUSE（脚本链路 / I2C 直读）→ 偏移/绝对双模式算校准码 →
写 Vbit 位域调压 → DMM / N6705C VMeter 测压 → 容差判定。
位域 read-modify-write 与 finally 兜底恢复范式同 output_voltage_worker。
"""

import time

from PySide6.QtCore import QObject, Signal

from instruments.mock.mock_instruments import MockI2C
from lib.i2c.i2c_interface_x64 import I2CInterface, I2CSpeedMode, I2CWidthFlag
from log_config import get_logger

from .ft_calib_ov_analysis import (
    clamp_code,
    compute_code,
    extract_bits,
    insert_bits,
    judge,
    parse_int_value,
    resolve_target_mv,
    summarize,
    validate_chip_config,
)

_logger = get_logger(__name__)

_SPEED_MAP = {
    20: I2CSpeedMode.SPEED_20K,
    100: I2CSpeedMode.SPEED_100K,
    400: I2CSpeedMode.SPEED_400K,
    750: I2CSpeedMode.SPEED_750K,
}
_WIDTH_MAP = {
    8: I2CWidthFlag.BIT_8,
    10: I2CWidthFlag.BIT_10,
    32: I2CWidthFlag.BIT_32,
}
_SETTLE_SLICE_S = 0.02
_VMETER_SAMPLES = 3


class FtCalibOvWorker(QObject):
    log_message = Signal(str)
    rail_result = Signal(dict)
    result_update = Signal(dict)
    test_finished = Signal(bool, str)

    def __init__(
            self, chip_cfg, options, n6705c=None, dmm=None, debug_flag=False, *,
            i2c_factory=None, mock_i2c_factory=None, time_module=None):
        super().__init__()
        self._chip = chip_cfg
        self._options = options
        self._n6705c = n6705c
        self._dmm = dmm
        self._debug = debug_flag
        self._stop_flag = False
        self._i2c_factory = I2CInterface if i2c_factory is None else i2c_factory
        self._mock_i2c_factory = MockI2C if mock_i2c_factory is None else mock_i2c_factory
        self._time = time if time_module is None else time_module

    def request_stop(self):
        self._stop_flag = True

    def _sleep_settle(self, settle_ms):
        """分片 sleep（每片 ≤20ms）逐片查 stop，避免整段阻塞无法响应停止。"""
        remaining = max(0.0, float(settle_ms) / 1000.0)
        while remaining > 0 and not self._stop_flag:
            slice_s = min(_SETTLE_SLICE_S, remaining)
            self._time.sleep(slice_s)
            remaining -= slice_s

    def _read_efuse(self, i2c, caller, efuse_cfg, rail):
        """EFUSE 双链路读取，返回 (原始值, 提取值)。脚本失败抛异常中止整轮。"""
        field = rail["efuse_field"]
        reg = parse_int_value(field["reg_addr"])
        dev = parse_int_value(efuse_cfg["device_addr"])
        width = int(efuse_cfg["width_flag"])
        if caller is not None:
            ok, raw = caller.read_efuse(
                dev, reg, _WIDTH_MAP[width],
                _SPEED_MAP[int(efuse_cfg["speed_khz"])],
                efuse_cfg["script_filename"], efuse_cfg.get("chip_name", ""),
            )
            if not ok or not isinstance(raw, int):
                raise RuntimeError(
                    f"EFUSE script read failed @0x{reg:X} ({efuse_cfg['script_filename']})"
                )
        else:
            raw = i2c.read(dev, reg, width)
        value = extract_bits(raw, field["msb"], field["lsb"],
                             signed=bool(field.get("signed", False)))
        return raw, value

    def _measure(self, options):
        """按仪器选择测压，返回 (电压 V, 统计 dict 或 None)。"""
        if options["instrument"] == "vmeter":
            ch = int(options["vmeter_channel"])
            readings = [self._n6705c.measure_voltage(ch) for _ in range(_VMETER_SAMPLES)]
            return sum(readings) / len(readings), None
        stats = self._dmm.measure_average(
            "VOLTage:DC", int(options["dmm_samples"]),
            range_value=options.get("dmm_range"),
        )
        return float(stats["average"]), stats

    def run(self):
        i2c = None
        restore_ctxs = []  # [(dev, reg, orig, width)] 按寄存器去重，保留首次原值
        restore_keys = set()
        results = []
        success = False
        finish_reason = "Test incomplete"
        try:
            chip = self._chip
            options = self._options
            validate_chip_config(chip)
            selected = set(options.get("selected_rails") or [])
            rails = [r for r in chip["rails"]
                     if r.get("enabled", True) and r["name"] in selected]
            if not rails:
                raise ValueError("No rails selected for check")

            chip_i2c = chip["i2c"]
            efuse_cfg = dict(chip.get("efuse") or {})
            efuse_cfg.setdefault("device_addr", chip_i2c["device_addr"])
            efuse_cfg.setdefault("width_flag", chip_i2c["width_flag"])
            efuse_cfg.setdefault("speed_khz", chip_i2c["speed_khz"])

            if self._debug:
                i2c = self._mock_i2c_factory()
                self.log_message.emit("[DEBUG] Using Mock I2C interface.")
            else:
                i2c = self._i2c_factory()
            if hasattr(i2c, "speed_mode"):
                i2c.speed_mode = _SPEED_MAP[int(chip_i2c["speed_khz"])]

            caller = None
            if efuse_cfg.get("link") == "script":
                if self._debug or not hasattr(i2c, "raw"):
                    self.log_message.emit(
                        "[MOCK] EFUSE script link degraded to direct I2C read "
                        "(mock interface has no raw access)."
                    )
                else:
                    from lib.i2c.efuse_script_caller import EFuseScriptCaller
                    caller = EFuseScriptCaller(i2c.raw)

            instrument = options["instrument"]
            if instrument == "vmeter":
                ch = int(options["vmeter_channel"])
                self._n6705c.set_mode(ch, "VMETer")
                self._n6705c.channel_on(ch)
                self.log_message.emit(
                    f"[TEST] CH{ch}=VMETer (voltage only), channel ON"
                )
            else:
                self._dmm.configure_voltage_dc(range_value=options.get("dmm_range"))
                self._dmm.set_nplc("VOLTage:DC", float(options.get("dmm_nplc", 1)))
                self.log_message.emit(
                    f"[TEST] DMM DCV configured: samples={options['dmm_samples']}, "
                    f"NPLC={options.get('dmm_nplc', 1)}"
                )

            self.log_message.emit(
                f"[TEST] Chip={chip['name']}, rails={len(rails)}, "
                f"EFUSE link={efuse_cfg.get('link')}, instrument={instrument}"
            )
            self.log_message.emit(
                "[TEST] Rail\tEFUSE (LSB)\tCode\tTarget (mV)\tMeasured (mV)\t"
                "Error (mV)\tTol (mV)\tVerdict"
            )

            total = len(rails)
            stopped_on_fail = False
            for idx, rail in enumerate(rails):
                if self._stop_flag:
                    finish_reason = "Stopped by user"
                    break
                name = rail["name"]
                vbit = rail["vbit"]
                dev = parse_int_value(chip_i2c["device_addr"])
                reg = parse_int_value(vbit["reg_addr"])
                width = int(vbit.get("width_flag") or chip_i2c["width_flag"])
                msb, lsb = int(vbit["msb"]), int(vbit["lsb"])

                efuse_raw, efuse_val = self._read_efuse(i2c, caller, efuse_cfg, rail)
                code = compute_code(
                    rail["mode"], parse_int_value(rail.get("base_code", 0)),
                    efuse_val, int(rail.get("offset_lsb", 0)),
                )
                code, clamped = clamp_code(code, msb, lsb)
                if clamped:
                    self.log_message.emit(
                        f"[WARN] {name}: calibration code clamped to 0x{code:X} "
                        f"(field 0x{msb:X}:0x{lsb:X} range exceeded)"
                    )

                orig = i2c.read(dev, reg, width)
                key = (dev, reg, width)
                if options.get("restore_registers", True) and key not in restore_keys:
                    restore_keys.add(key)
                    restore_ctxs.append((dev, reg, orig, width))
                i2c.write(dev, reg, insert_bits(orig, code, msb, lsb), width)
                readback = extract_bits(i2c.read(dev, reg, width), msb, lsb)
                readback_ok = readback == code
                if not readback_ok:
                    self.log_message.emit(
                        f"[WARN] {name}: Vbit readback 0x{readback:X} != "
                        f"written 0x{code:X}"
                    )

                self._sleep_settle(rail.get("settle_ms", 0))
                if self._stop_flag:
                    finish_reason = "Stopped by user"
                    break

                measured_v, stats = self._measure(options)
                target_mv = resolve_target_mv(rail, code)
                err_mv, passed = judge(measured_v, target_mv, rail["tolerance_mv"])

                rec = {
                    "rail": name,
                    "type": rail["type"],
                    "efuse_raw": efuse_raw,
                    "efuse_value": efuse_val,
                    "code": code,
                    "clamped": clamped,
                    "target_mv": target_mv,
                    "measured_mv": measured_v * 1000.0,
                    "err_mv": err_mv,
                    "tolerance_mv": float(rail["tolerance_mv"]),
                    "passed": passed,
                    "readback_ok": readback_ok,
                }
                if stats is not None:
                    rec["meas_min_mv"] = float(stats["min"]) * 1000.0
                    rec["meas_max_mv"] = float(stats["max"]) * 1000.0
                    rec["meas_stddev_mv"] = float(stats["stddev"]) * 1000.0
                results.append(rec)
                self.rail_result.emit(rec)

                verdict = "PASS" if passed else "FAIL"
                self.log_message.emit(
                    f"[MEAS] {name}\t{efuse_val}\t0x{code:X}\t{target_mv:.1f}\t"
                    f"{measured_v * 1000.0:.1f}\t{err_mv:+.1f}\t"
                    f"{rail['tolerance_mv']:.1f}\t{verdict}"
                )
                summary = summarize(results)
                summary["progress"] = int((idx + 1) / total * 100)
                self.result_update.emit(summary)

                if options.get("stop_on_fail", False) and not passed:
                    stopped_on_fail = True
                    finish_reason = "Stopped on FAIL"
                    self.log_message.emit(
                        f"[TEST] Stop on FAIL enabled: aborting after {name}."
                    )
                    break
            else:
                success = True
                finish_reason = "Test completed"

            if stopped_on_fail:
                success = True
            if finish_reason == "Stopped by user":
                self.log_message.emit("[TEST] Stopped by user.")

        except Exception as e:
            finish_reason = f"Test failed: {e}"
            self.log_message.emit(f"[ERROR] {finish_reason}")
            _logger.error("FT calib output voltage check failed", exc_info=True)
        finally:
            if restore_ctxs and i2c is not None:
                for dev, reg, orig, width in reversed(restore_ctxs):
                    try:
                        i2c.write(dev, reg, orig, width)
                    except Exception as e:
                        success = False
                        finish_reason = f"Test failed: register restore error ({e})"
                        self.log_message.emit(
                            f"[ERROR] Failed to restore reg 0x{reg:X} @0x{dev:X}: {e}"
                        )
                        _logger.error("Failed to restore register", exc_info=True)
                self.log_message.emit(
                    f"[TEST] {len(restore_ctxs)} register(s) restored to original values."
                )
            if i2c is not None and hasattr(i2c, "close"):
                try:
                    i2c.close()
                except Exception:
                    _logger.error("Failed to close I2C interface", exc_info=True)
            self.result_update.emit(summarize(results))
            self.test_finished.emit(success, finish_reason)
