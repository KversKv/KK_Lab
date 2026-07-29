#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证：打开 CH1 显示后 MEASU:IMMED 是否恢复有效。"""
import time

from instruments.factory import create_oscilloscope
from log_config import get_logger

logger = get_logger(__name__)

MSO64B_ADDR = "TCPIP0::10.31.31.202::inst0::INSTR"
CH = 1


def try_imm(scope, tag):
    for mtype in ("MAXIMUM", "MEAN", "MINIMUM", "PK2PK"):
        scope.instrument.write(f"MEASUrement:IMMed:SOURCE1 CH{CH}")
        scope.instrument.write(f"MEASUrement:IMMed:TYPe {mtype}")
        val = scope.instrument.query("MEASUrement:IMMed:VALUe?").strip()
        print(f"  [{tag}] {mtype}: {val}", flush=True)


def main():
    scope = create_oscilloscope("mso64b", MSO64B_ADDR)
    scope.set_channel_display(CH, True)
    print(f"SELect:CH1? = {scope.instrument.query('SELect:CH1?').strip()}",
          flush=True)
    scope.run()
    time.sleep(1.5)
    print("[running] 显示打开后测:", flush=True)
    try_imm(scope, "running")
    scope.stop()
    time.sleep(0.3)
    print("[stopped] 停采后测:", flush=True)
    try_imm(scope, "stopped")
    scope.run()


if __name__ == "__main__":
    main()
