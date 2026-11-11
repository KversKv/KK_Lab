#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：完整复刻 factory auto 序列，定位杀死 A session 的步骤。

运行：python tests\\_debug_visa_isolate2.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import pyvisa  # noqa: E402
from instruments.power.keysight.n6705c import N6705C  # noqa: E402
from instruments.power.itech.it2705 import IT2705  # noqa: E402

N6705C_RES = "TCPIP0::10.31.71.98::hislip0::INSTR"
IT2705_RES = "TCPIP0::10.31.71.168::30000::SOCKET"


def probe_a(inst, tag):
    try:
        print(f"[{tag}] A *IDN? ->", inst.instr.query("*IDN?").strip()[:40])
    except Exception as e:
        print(f"[{tag}] A *IDN? FAIL: {type(e).__name__}: {e}")


def main():
    print("=== 1. A = N6705C(98) ===")
    a = N6705C(N6705C_RES)
    probe_a(a, "A connected")

    print("\n=== 2. probe = N6705C(168)（factory auto 探测步） ===")
    probe = N6705C(IT2705_RES)
    print("probe IDN:", probe.instr.query("*IDN?").strip()[:40])
    probe_a(a, "after probe open")

    print("\n=== 3. probe.disconnect()（含 rm.close()） ===")
    probe.disconnect()
    probe_a(a, "after probe disconnect")

    print("\n=== 4. B = IT2705(168) ===")
    b = IT2705(IT2705_RES)
    print("B IDN:", b.instr.query("*IDN?").strip()[:40])
    probe_a(a, "after B connect")

    print("\n=== 5. 追加：裸 rm.close() 测试 ===")
    rm_x = pyvisa.ResourceManager("@py")
    c = rm_x.open_resource(IT2705_RES)
    c.close()
    rm_x.close()
    probe_a(a, "after unrelated rm close")

    a.disconnect()
    b.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
