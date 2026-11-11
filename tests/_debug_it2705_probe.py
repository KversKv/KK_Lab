#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IT2705 实机探针：VOLT? 钳位语义 / VMETer 开路基线 / PS2Q→VMETer 保持（一次性调试）。"""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from instruments.factory import create_power_analyzer

RESOURCE = "TCPIP0::10.31.71.168::30000::SOCKET"
CH = 1


def main():
    inst = create_power_analyzer(RESOURCE, analyzer_type="auto")
    try:
        # 1. VMETer 开路测量（重复 3 次看稳定性）
        inst.set_mode(CH, "VMETer")
        inst.channel_on(CH)
        time.sleep(0.5)
        for i in range(3):
            print(f"VMETer open measure #{i+1}: {float(inst.measure_voltage(CH)):+.4f} V")
        inst.channel_off(CH)

        # 2. PS2Q 输出 1.0V 驱动节点，切 VMETer 后测保持情况
        inst.set_mode(CH, "PS2Q")
        inst.set_current_limit(CH, 0.1)
        inst.set_voltage(CH, 1.0)
        inst.channel_on(CH)
        time.sleep(0.3)
        print(f"PS2Q ON VOLT?={inst.get_voltage_setpoint(CH)} meas={float(inst.measure_voltage(CH)):+.4f}")
        inst.set_mode(CH, "VMETer")
        inst.channel_on(CH)
        for i in range(4):
            time.sleep(0.25)
            print(f"after VMETer switch #{i+1}: {float(inst.measure_voltage(CH)):+.4f} V")
        inst.channel_off(CH)

        # 3. VOLT 写读回：正常值 / 负值 / 超量程
        inst.set_mode(CH, "PS2Q")
        for v in (1.2, -1.0, -20.2, 25.0):
            inst.set_voltage(CH, v)
            rb = inst.get_voltage_setpoint(CH)
            print(f"write VOLT {v:+.2f} -> VOLT?={rb}")
        inst.channel_off(CH)
    finally:
        inst.channel_off(CH)
        inst.disconnect()


if __name__ == "__main__":
    main()
