#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IT2705 ELOG FORM REAL 二进制块字节序/数值正确性验证（一次性调试）。"""
import os
import sys
import time

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pyvisa  # noqa: E402

RESOURCE = os.environ.get(
    "KK_LAB_IT2705_RESOURCE", "TCPIP0::10.31.71.168::30000::SOCKET"
)


def main():
    try:
        rm = pyvisa.ResourceManager()
    except Exception:
        rm = pyvisa.ResourceManager("@py")
    instr = rm.open_resource(RESOURCE)
    instr.timeout = 10000
    instr.encoding = "utf-8"
    instr.read_termination = "\n"
    instr.write_termination = "\n"
    try:
        instr.write("ABOR:ELOG (@1:8)")
        instr.write("*CLS")
        instr.write("SENS:ELOG:FUNC:VOLT ON,(@1)")
        instr.write("SENS:ELOG:FUNC:CURR ON,(@1)")
        instr.write("SENS:ELOG:PER 0.001,(@1)")
        instr.write("TRIG:ELOG:SOUR IMM,(@1)")
        instr.write("FORM ASC")
        instr.write("INIT:ELOG (@1)")
        instr.write("TRIG:ELOG (@1)")
        time.sleep(0.3)
        asc = instr.query("FETC:ELOG? 5,(@1)").strip()
        print(f"ASC: {asc}")
        instr.write("FORM REAL")
        instr.write("FORM:BORD NORM")  # MSB first
        vals_be = instr.query_binary_values(
            "FETC:ELOG? 5,(@1)", datatype="f", container=list, is_big_endian=True
        )
        print(f"REAL NORM as big-endian:    {vals_be}")
        vals_le = instr.query_binary_values(
            "FETC:ELOG? 5,(@1)", datatype="f", container=list, is_big_endian=False
        )
        print(f"REAL NORM as little-endian: {vals_le}")
        instr.write("FORM:BORD SWAP")  # LSB first
        vals_swap_le = instr.query_binary_values(
            "FETC:ELOG? 5,(@1)", datatype="f", container=list, is_big_endian=False
        )
        print(f"REAL SWAP as little-endian: {vals_swap_le}")
        instr.write("FORM ASC")
        instr.write("ABOR:ELOG (@1:8)")
        for _ in range(5):
            err = instr.query("SYST:ERR?").strip()
            if err.startswith("0"):
                break
            print(f"ERR: {err}")
    finally:
        try:
            instr.write("FORM ASC")
            instr.write("ABOR:ELOG (@1:8)")
        except Exception:
            pass
        instr.close()
        print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
