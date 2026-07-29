#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 set_channel_range / clear_arb_all_channels 是否破坏 ARB:COUN INF 连续触发。"""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


def vpp(scope):
    scope.set_channel_display(SCH, True)
    scope.set_channel_scale(SCH, 0.1)
    scope.set_channel_offset(SCH, 0.8)
    scope.set_timebase_scale(PERIOD / 2.0)
    time.sleep(1.0)
    scope.stop()
    vmax = float(scope.query(f":MEASure:VMAX? CHANnel{SCH}"))
    vmin = float(scope.query(f":MEASure:VMIN? CHANnel{SCH}"))
    scope.run()
    return (vmax - vmin) * 1e3


def case(psu, scope, tag, with_clear, with_range):
    psu.arb_stop()
    if with_clear:
        psu.clear_arb_all_channels()
    psu.set_mode(CH, "CCLoad")
    if with_range:
        psu.set_channel_range(CH)
    psu.channel_on(CH)
    psu.set_current_slew(CH, "MAX")
    psu.set_arb_current_pulse(CH, I0, I1, PERIOD / 2.0, 0.0, PERIOD / 2.0, FREQ)
    psu.instr.write(f"ARB:COUN INF,(@{CH})")
    psu.restore_arb_trigger_source()
    psu.arb_on(CH)
    st = q(psu, f"STAT:OPER:COND? (@{CH})")
    cn = q(psu, f"ARB:COUN? (@{CH})")
    print(f"  [{tag}] STAT={st}, ARB:COUN={cn}, Vpp={vpp(scope):.1f} mV",
          flush=True)


def main():
    psu = create_power_analyzer(N6705C_ADDR)
    scope = create_oscilloscope("dsox4034a", DSOX4034A_ADDR)
    case(psu, scope, "基线(无clear/range)", False, False)
    case(psu, scope, "+clear_arb_all_channels", True, False)
    case(psu, scope, "+set_channel_range", False, True)
    case(psu, scope, "+clear+range(完整核心)", True, True)
    psu.arb_stop()
    psu.instr.write(f"ARB:COUN 1,(@{CH})")
    psu.exit_arb_current(CH)
    psu.set_current(CH, 0)
    psu.channel_off(CH)


if __name__ == "__main__":
    main()
