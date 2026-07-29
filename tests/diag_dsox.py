#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实测 DSOX4034A CH1 窗口与信号位置，确认是否削底。"""
import time

from instruments.factory import create_oscilloscope
from log_config import get_logger

logger = get_logger(__name__)

DSOX4034A_ADDR = "TCPIP0::10.31.30.181::inst0::INSTR"


def main():
    scope = create_oscilloscope("dsox4034a", DSOX4034A_ADDR)
    scope.run()
    time.sleep(1.0)
    scale = float(scope.query(":CHANnel1:SCALe?"))
    offset = float(scope.query(":CHANnel1:OFFSet?"))
    tb = float(scope.query(":TIMebase:SCALe?"))
    print(f"CH1 SCALe={scale * 1e3:.3f} mV/div, OFFSet={offset * 1e3:.3f} mV, "
          f"TIMebase={tb * 1e3:.3f} ms/div", flush=True)
    top = offset + 4 * scale
    bot = offset - 4 * scale
    print(f"窗口: 顶={top * 1e3:.1f} mV, 底={bot * 1e3:.1f} mV "
          f"(信号应为 800mV 附近脉冲)", flush=True)
    vmax = float(scope.query(":MEASure:VMAX? CHANnel1"))
    vmin = float(scope.query(":MEASure:VMIN? CHANnel1"))
    vavg = float(scope.query(":MEASure:VAVerage? DISPlay,CHANnel1"))
    print(f"VMAX={vmax * 1e3:.2f} mV, VMIN={vmin * 1e3:.2f} mV, "
          f"VAVG={vavg * 1e3:.2f} mV", flush=True)
    # 判断 VMIN 是否恰好压在下边界（削波特征）
    clipped = vmin <= (bot + 0.02 * scale)
    print(f"VMIN{'≈下边界，疑似削底' if clipped else '在窗口内'}", flush=True)


if __name__ == "__main__":
    main()
