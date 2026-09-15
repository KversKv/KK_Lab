"""Quiescent 外供 Vout = 首项前实测基准 V0 + 偏置 的 Mock 校验。

覆盖：
  A. ctx.vout_baseline_v 有值时，quiescent 外供 Vout = V0 + iq_vout_offset_mv；
  B. ctx.vout_baseline_v 为 None（基准读取失败）时回落标称 vout_nominal_mv；
  C. runner 全链路：ldo_quiescent 项 ctx 注入的 vout_baseline_v 等于
     _record_vout_baseline 测得的 V0（Mock Vout 通道电压）。

    python tests/check_iq_vout_supply.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import debug_config  # noqa: E402

debug_config.DEBUG_MOCK = True

import core.module_test._runner_base as runner_base  # noqa: E402

runner_base.DEBUG_MOCK = True  # runner 模块内 from-import 的副本同步打开

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.module_test._common import ItemContext  # noqa: E402
from core.module_test.dcdc.items import quiescent as dcdc_quiescent  # noqa: E402
from core.module_test.ldo.items import quiescent as ldo_quiescent  # noqa: E402
from core.module_test.ldo.ldo_runner import LDOTestRunner  # noqa: E402
from instruments.mock.mock_instruments import MockN6705C  # noqa: E402

_PASS = True


def check(name: str, ok: bool, extra: str = "") -> None:
    global _PASS
    _PASS = _PASS and ok
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {extra}" if extra else ""))


def _make_ctx(mock: MockN6705C, out_dir: str, baseline,
              vout_nominal_mv: float) -> ItemContext:
    return ItemContext(
        n6705c=mock,
        scope=None,
        chamber=None,
        config={
            "vbat_channel": "CH 1",
            "force_channel": "CH 4",
            "vout_channel": "CH 2",
            "iload_channel": "CH 3",
            "vin_v": 3.8,
            "vout_nominal_mv": vout_nominal_mv,
            "iq_vout_offset_mv": 20.0,
            "iq_en_addr": "0x31",
            "iq_en_dr_addr": "0x32",
        },
        out_dir=out_dir,
        is_mock=True,
        stop_flag_fn=lambda: False,
        log_fn=lambda _msg: None,
        progress_fn=lambda _pct, _label: None,
        vout_baseline_v=baseline,
    )


def _csv_vout(path: str) -> float:
    with open(path, encoding="utf-8-sig") as f:
        lines = f.read().strip().splitlines()
    return float(lines[1].split(",")[1])


def check_item_level() -> None:
    out_dir = os.path.join("Results", "_check_iq_vout_supply")
    os.makedirs(out_dir, exist_ok=True)

    # A. 有基准 V0：外供 = 1.78 + 0.02 = 1.80（标称 1800mV 仅作回落，不生效）
    mock = MockN6705C()
    ctx = _make_ctx(mock, out_dir, 1.78, 1800)
    res = ldo_quiescent(ctx)
    got = _csv_vout(res.raw_csv_path)
    check("A1 LDO 外供=V0+偏置", abs(got - 1.80) < 1e-9, f"got {got}")

    mock = MockN6705C()
    ctx = _make_ctx(mock, out_dir, 1.15, 1200)
    res = dcdc_quiescent(ctx)
    got = _csv_vout(res.raw_csv_path)
    check("A2 DCDC 外供=V0+偏置", abs(got - 1.17) < 1e-9, f"got {got}")

    # B. 基准缺失（None）：回落标称 + 偏置
    mock = MockN6705C()
    ctx = _make_ctx(mock, out_dir, None, 1800)
    res = ldo_quiescent(ctx)
    got = _csv_vout(res.raw_csv_path)
    check("B1 LDO 回落标称+偏置", abs(got - 1.82) < 1e-9, f"got {got}")

    mock = MockN6705C()
    ctx = _make_ctx(mock, out_dir, None, 1200)
    res = dcdc_quiescent(ctx)
    got = _csv_vout(res.raw_csv_path)
    check("B2 DCDC 回落标称+偏置", abs(got - 1.22) < 1e-9, f"got {got}")


def check_runner(app: QApplication) -> None:
    """runner 全链路：ctx 注入值 = _record_vout_baseline 实测 V0。"""
    mock = MockN6705C()
    # 让 Vout 通道（CH 2）有一个可区分于标称的电压：V0=1.75V（标称 1800mV）
    mock.set_voltage(2, 1.75)
    logs: list[str] = []
    cfg = {
        "chip_name": "MOCKCHIP",
        "module_name": "LDO_X",
        "operator": "",
        "selected_items": ["ldo_quiescent"],
        "vbat_channel": "CH 1",
        "vin_channel": "CH 2",
        "vout_channel": "CH 2",
        "force_channel": "CH 4",
        "iload_channel": "CH 3",
        "vout_nominal_mv": 1800,
        "iq_vout_offset_mv": 20.0,
        "iq_en_addr": "0x31",
        "iq_en_dr_addr": "0x32",
        "max_iload_ma": 400,
        "item_overrides": {},
    }
    runner = LDOTestRunner(config=cfg, n6705c=mock, scope=None)
    runner.log.connect(logs.append)
    done = {"ok": False, "result": None}

    def on_finished(result):
        done["ok"] = True
        done["result"] = result
        app.quit()

    def on_failed(msg):
        print(f"[RUNNER FAILED] {msg}")
        app.quit()

    runner.finished_result.connect(on_finished)
    runner.failed.connect(on_failed)
    runner.start()
    app.exec()

    check("C1 runner 跑完", done["ok"])
    if not done["ok"]:
        return
    item = next(i for i in done["result"].items if i.item_key == "ldo_quiescent")
    got = float(item.measured["Vout (V)"])
    # V0 = 1.75（Mock 有 ±2mV 高斯噪声，3 样本去极值均值），外供 = V0 + 0.02
    check("C2 外供=实测V0+偏置(≈1.77)", abs(got - 1.77) < 0.005, f"got {got}")
    check("C3 [VOUT] 基准日志", any("[VOUT] 基准电压 V0" in line for line in logs))


def main() -> int:
    app = QApplication(sys.argv)
    check_item_level()
    check_runner(app)
    print("\n全部通过" if _PASS else "\n存在失败项")
    return 0 if _PASS else 1


if __name__ == "__main__":
    sys.exit(main())
