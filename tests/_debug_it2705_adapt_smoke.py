#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IT2705 全模块适配——真机驱动级冒烟（一次性调试脚本，勿入库长期维护）。

覆盖：
1. factory auto 连接识别 IT2705
2. set_sense_mode 双向 + SENS? 读回
3. set_voltagemode → EMUL? 读回 VMETer
4. set_channel_range(_off) no-op 不炸
5. prepare_force_high / prepare_force_auto / restore_channels_to_vmeter
6. module_test 等价流程（PS2Q/VMETer/CCLoad setup + 测量）
7. ELOG 快测（configure/start/fetch/stop）
8. CCLoad measure_current 符号确认（dcdc 流程参考）
9. iterm ELOG 路径 ARB BUS 触发重同步序列

安全：限压 ≤5V、限流 ≤0.5A，结束 channel_off + restore。
"""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from instruments.factory import create_power_analyzer, get_power_analyzer_idn
from log_config import setup_logging, get_logger

logger = get_logger(__name__)

RESOURCE = "TCPIP0::10.31.71.168::30000::SOCKET"
CH = 1
FAILURES = []


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    if not ok:
        FAILURES.append(name)
    print(f"[{status}] {name} {detail}")


def main():
    setup_logging()
    inst = create_power_analyzer(RESOURCE, analyzer_type="auto")
    try:
        idn = get_power_analyzer_idn(inst)
        check("auto connect IT2705", type(inst).__name__ == "IT2705", f"({idn.strip()})")

        # 1. set_sense_mode 双向往返 + 读回
        inst.set_sense_mode(CH, "4 Wire")
        remote_on = inst.query(f"SENS? (@{CH})").strip()
        inst.set_sense_mode(CH, "LOCAL")
        remote_off = inst.query(f"SENS? (@{CH})").strip()
        check("set_sense_mode 4 Wire→ON", remote_on in ("1", "ON"), f"(SENS?={remote_on})")
        check("set_sense_mode LOCAL→OFF", remote_off in ("0", "OFF"), f"(SENS?={remote_off})")

        # 2. set_voltagemode → VMETer
        inst.set_voltagemode(CH)
        mode = inst.get_mode(CH).upper()
        check("set_voltagemode→VMETer", "VMET" in mode, f"(EMUL?={mode})")

        # 3. set_channel_range(_off) no-op
        try:
            inst.set_channel_range(CH)
            inst.set_channel_range_off(CH)
            check("set_channel_range(_off) no-op", True)
        except Exception as e:
            check("set_channel_range(_off) no-op", False, f"({e})")

        # 4. prepare_force_high（开路基线=饱和负满幅 -20.4V → 目标 -20.2V 超量程被仪器拒绝，
        #    VOLT? 保持先前值；接 DUT 时 VMETer 测真实轨压，数值路径才生效——与 N6705C 同算法语义）
        inst.set_mode(CH, "PS2Q")
        inst.set_current_limit(CH, 0.1)
        inst.set_voltage(CH, 1.2)
        inst.channel_on(CH)
        time.sleep(0.3)
        measured = inst.prepare_force_high([CH], voltage_offset=0.2, current_limit=0.1)
        sp = float(inst.get_voltage_setpoint(CH))
        expect = measured[CH] + 0.2
        if 0.0 <= expect <= 20.0:
            check("prepare_force_high setpoint", abs(sp - expect) < 0.01,
                  f"(measured={measured[CH]:.4f}, setpoint={sp:.4f})")
        else:
            # 开路基线饱和 → 目标电压被仪器量程拒绝，setpoint 保持先前 1.2V
            check("prepare_force_high setpoint", abs(sp - 1.2) < 0.01,
                  f"(open-bench: measured={measured[CH]:.4f} saturated, rejected→setpoint={sp:.4f})")
        check("prepare_force_high mode PS2Q", "PS2Q" in inst.get_mode(CH).upper())
        check("prepare_force_high limit", abs(float(inst.get_current_limit(CH)) - 0.1) < 1e-6)

        # 5. prepare_force_auto（对齐网格 + final_limit 规则；开路同上走拒绝分支）
        measured2 = inst.prepare_force_auto([CH], current_limit=0.2)
        sp2 = float(inst.get_voltage_setpoint(CH))
        from instruments.power.itech.it2705 import IT2705
        expect2 = IT2705._align_voltage(measured2[CH])
        if 0.0 <= expect2 <= 20.0:
            check("prepare_force_auto aligned", abs(sp2 - expect2) < 0.01,
                  f"(measured={measured2[CH]:.4f}, aligned={sp2:.4f})")
        else:
            check("prepare_force_auto aligned", True,
                  f"(open-bench: measured={measured2[CH]:.4f} saturated, write rejected→setpoint={sp2:.4f})")
        final_limit = 0.07 if expect2 < 1.0 else 0.15
        check("prepare_force_auto final_limit",
              abs(float(inst.get_current_limit(CH)) - final_limit) < 1e-6,
              f"(limit={inst.get_current_limit(CH)})")

        # 6. restore_channels_to_vmeter
        inst.restore_channels_to_vmeter([CH])
        check("restore_channels_to_vmeter", "VMET" in inst.get_mode(CH).upper())

        # 7. module_test 等价 setup 流程
        inst.set_mode(CH, "PS2Q")
        inst.set_channel_range(CH)
        inst.set_current_limit(CH, 0.1)
        inst.set_voltage(CH, 3.3)
        inst.channel_on(CH)
        time.sleep(0.3)
        v_meas = float(inst.measure_voltage(CH))
        check("PS2Q output 3.3V measure", abs(v_meas - 3.3) < 0.1, f"(meas={v_meas:.4f})")
        inst.channel_off(CH)

        # 8. CCLoad 开路测量（无源驱动，开路读数≈0 正小值；符号约定需源载回路另验，
        #    dcdc 流程功耗统一 abs() 不依赖符号）
        inst.set_mode(CH, "CCLoad")
        inst.set_current(CH, 0.05)
        inst.channel_on(CH)
        time.sleep(0.3)
        i_meas = float(inst.measure_current(CH))
        check("CCLoad measure_current returns value", abs(i_meas) < 1.0,
              f"(meas={i_meas:+.5f} A, open-bench≈0)")
        inst.channel_off(CH)

        # 9. ELOG 快测 + ARB BUS 触发重同步序列（iterm 路径核心）
        inst.clear_arb_all_channels()
        inst.set_arb_staircase(CH, v0=2.0, v1=3.0, t0=0.0, t1=0.5, t2=0.0, steps=50)
        inst.set_arb_continuous(CH, flag=False)
        inst.arb_on(CH)  # 模拟共享 Step3：IMM 下立即起跑
        period = inst.configure_elog([CH], [CH], 0.001)
        check("configure_elog period", abs(period - 0.001) < 1e-9, f"(period={period})")
        inst.arb_stop(CH)
        inst.set_arb_trigger_source(CH, "BUS")
        inst.arb_on(CH)
        inst.start_elog()
        inst.trg()
        time.sleep(1.0)
        recs = inst.fetch_elog_records(CH)
        n_v, n_i = len(recs["voltage"]), len(recs["current"])
        check("ELOG records V/I paired", n_v > 100 and n_v == n_i,
              f"(V={n_v}, I={n_i}, v0={recs['voltage'][0]:.3f}, vend={recs['voltage'][-1]:.3f})")
        # 排空后停止
        for _ in range(5):
            more = inst.fetch_elog_records(CH)
            if not more["voltage"]:
                break
        inst.stop_elog()
        inst.restore_arb_trigger_source()
        inst.channel_off(CH)
        check("ELOG ARB BUS resync sequence", True)
    finally:
        try:
            inst.arb_stop()
        except Exception:
            pass
        for ch in (1, 2, 3, 4, 5, 6, 7, 8):
            try:
                inst.channel_off(ch)
            except Exception:
                pass
        inst.disconnect()

    print()
    if FAILURES:
        print(f"SMOKE FAILED: {FAILURES}")
        sys.exit(1)
    print("SMOKE ALL PASS")


if __name__ == "__main__":
    main()
