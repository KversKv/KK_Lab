#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐变量对照：找出可靠产生 ARB 连续脉冲（示波器可见）的配置。"""
import os
import time

from instruments.factory import create_oscilloscope, create_power_analyzer
from log_config import get_logger

logger = get_logger(__name__)

N6705C_ADDR = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
DSOX4034A_ADDR = "TCPIP0::10.31.30.181::inst0::INSTR"
CH = 3
SCH = 1
I0, I1, FREQ = -0.010, -0.100, 10.0
PERIOD = 1.0 / FREQ


def q(psu, cmd):
    return psu.instr.query(cmd).strip()


def setup_base(psu):
    psu.arb_stop()
    psu.clear_arb_all_channels()
    psu.set_mode(CH, "CCLoad")
    psu.channel_on(CH)
    psu.set_current_slew(CH, "MAX")
    psu.set_arb_current_pulse(CH, I0, I1, PERIOD / 2.0, 0.0, PERIOD / 2.0, FREQ)


def arm(psu):
    psu.restore_arb_trigger_source()
    psu.arb_on(CH)


def measure(scope, tag):
    scope.set_channel_display(SCH, True)
    scope.set_channel_scale(SCH, 0.1)
    scope.set_channel_offset(SCH, 0.8)
    scope.set_timebase_scale(PERIOD / 2.0)
    time.sleep(1.0)
    scope.stop()
    try:
        vmax = float(scope.query(f":MEASure:VMAX? CHANnel{SCH}"))
        vmin = float(scope.query(f":MEASure:VMIN? CHANnel{SCH}"))
        vpp = (vmax - vmin) * 1e3
        state = q(psu_for_stat, f"STAT:OPER:COND? (@{CH})")
        print(f"  [{tag}] STAT={state}, Vpp={vpp:.1f} mV, "
              f"VMAX={vmax * 1e3:.0f}mV, VMIN={vmin * 1e3:.0f}mV",
              flush=True)
        return vpp > 50
    finally:
        scope.run()


psu_for_stat = None


def main():
    global psu_for_stat
    psu = create_power_analyzer(N6705C_ADDR)
    psu_for_stat = psu
    scope = create_oscilloscope("dsox4034a", DSOX4034A_ADDR)

    print("=== V1: LIST:COUN INF + IMM + INIT（无 TERM:LAST）===", flush=True)
    setup_base(psu)
    psu.instr.write(f"SOUR:LIST:COUN INF,(@{CH})")
    arm(psu)
    r1 = measure(scope, "V1")

    print("=== V2: TERM:LAST ON + IMM + INIT（无 LIST:COUN）===", flush=True)
    setup_base(psu)
    psu.instr.write(f"ARB:TERM:LAST ON,(@{CH})")
    arm(psu)
    r2 = measure(scope, "V2")

    print("=== V3: LIST:COUN INF + TERM:LAST ON + IMM + INIT ===", flush=True)
    setup_base(psu)
    psu.instr.write(f"ARB:TERM:LAST ON,(@{CH})")
    psu.instr.write(f"SOUR:LIST:COUN INF,(@{CH})")
    arm(psu)
    r3 = measure(scope, "V3")

    print("=== V4: LIST:COUN INF + TERM:LAST ON + BUS + INIT + *TRG ===",
          flush=True)
    setup_base(psu)
    psu.instr.write(f"ARB:TERM:LAST ON,(@{CH})")
    psu.instr.write(f"SOUR:LIST:COUN INF,(@{CH})")
    psu.instr.write("TRIG:ARB:SOUR BUS")
    psu.arb_on(CH)
    psu.instr.write("*TRG")
    r4 = measure(scope, "V4")

    print(f"\n结论: V1={'Y' if r1 else 'N'} V2={'Y' if r2 else 'N'} "
          f"V3={'Y' if r3 else 'N'} V4={'Y' if r4 else 'N'}", flush=True)

    psu.arb_stop()
    psu.instr.write(f"ARB:TERM:LAST OFF,(@{CH})")
    psu.instr.write(f"SOUR:LIST:COUN 1,(@{CH})")
    psu.exit_arb_current(CH)
    psu.set_current(CH, 0)
    psu.channel_off(CH)


if __name__ == "__main__":
    main()
