#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：二分定位 probe.disconnect() 中哪一步杀死 A 的 session。

运行：python tests\\_debug_visa_isolate3.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import pyvisa  # noqa: E402

N6705C_RES = "TCPIP0::10.31.71.98::hislip0::INSTR"
IT2705_RES = "TCPIP0::10.31.71.168::30000::SOCKET"


def probe_a(instr, tag):
    try:
        print(f"[{tag}] A *IDN? ->", instr.query("*IDN?").strip()[:40])
    except Exception as e:
        print(f"[{tag}] A *IDN? FAIL: {type(e).__name__}")


def main():
    rm_a = pyvisa.ResourceManager("@py")
    a = rm_a.open_resource(N6705C_RES)
    a.timeout = 10000
    probe_a(a, "A open")

    # --- 分支1：只 probe.instr.close()，不关 rm ---
    rm_p = pyvisa.ResourceManager("@py")
    p = rm_p.open_resource(IT2705_RES)
    p.timeout = 10000
    p.read_termination = "\n"
    p.write_termination = "\n"
    print("probe IDN:", p.query("*IDN?").strip()[:40])
    p.close()
    probe_a(a, "after probe.instr.close only")

    # --- 恢复测试：A 是否真死 ---
    try:
        a.close()
        a = rm_a.open_resource(N6705C_RES)
        a.timeout = 10000
        probe_a(a, "A reopened")
    except Exception as e:
        print("A reopen FAIL:", type(e).__name__, e)
        return 1

    # --- 分支2：只 rm.close()（先关 probe instr）---
    rm_p2 = pyvisa.ResourceManager("@py")
    p2 = rm_p2.open_resource(IT2705_RES)
    p2.timeout = 10000
    p2.read_termination = "\n"
    p2.write_termination = "\n"
    p2.close()
    probe_a(a, "after probe2 instr close")
    rm_p2.close()
    probe_a(a, "after probe2 rm.close")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
