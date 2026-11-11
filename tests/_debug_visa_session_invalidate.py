#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：定位混合连接时 N6705C VISA session 失效的确切时刻。

运行：python tests\\_debug_visa_session_invalidate.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from instruments.factory import create_power_analyzer  # noqa: E402

N6705C_RES = "TCPIP0::10.31.71.98::hislip0::INSTR"
IT2705_RES = "TCPIP0::10.31.71.168::30000::SOCKET"


def probe(inst, tag):
    try:
        idn = inst.instr.query("*IDN?").strip()
        print(f"[{tag}] *IDN? OK: {idn[:50]}")
    except Exception as e:
        print(f"[{tag}] *IDN? FAIL: {type(e).__name__}: {e}")
    try:
        to = inst.instr.timeout
        print(f"[{tag}] timeout read OK: {to}")
    except Exception as e:
        print(f"[{tag}] timeout read FAIL: {type(e).__name__}: {e}")
    try:
        inst.instr.timeout = 600000
        print(f"[{tag}] timeout write OK")
    except Exception as e:
        print(f"[{tag}] timeout write FAIL: {type(e).__name__}: {e}")
    try:
        rm = inst.instr.resource_manager
        print(f"[{tag}] RM: {rm} | session: {inst.instr.session}")
    except Exception as e:
        print(f"[{tag}] RM inspect FAIL: {e}")


def main():
    print("=== 1. connect N6705C ===")
    a = create_power_analyzer(N6705C_RES, analyzer_type="auto")
    probe(a, "A after connect")

    print("\n=== 2. connect IT2705 ===")
    b = create_power_analyzer(IT2705_RES, analyzer_type="auto")
    probe(b, "B after connect")

    print("\n=== 3. re-probe A ===")
    probe(a, "A after B connect")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
