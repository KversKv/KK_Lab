#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：隔离测试——什么操作杀死了 N6705C(pyvisa-py HiSLIP) 的 session。

运行：python tests\\_debug_visa_isolate.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import pyvisa  # noqa: E402

N6705C_RES = "TCPIP0::10.31.71.98::hislip0::INSTR"
IT2705_RES = "TCPIP0::10.31.71.168::30000::SOCKET"


def probe(tag, instr):
    try:
        print(f"[{tag}] *IDN? ->", instr.query("*IDN?").strip()[:40])
    except Exception as e:
        print(f"[{tag}] *IDN? FAIL: {type(e).__name__}: {e}")


def main():
    rm1 = pyvisa.ResourceManager("@py")
    a = rm1.open_resource(N6705C_RES)
    a.timeout = 10000
    probe("A opened (rm1)", a)

    print("\n-- step1: 仅创建第二个 @py RM --")
    rm2 = pyvisa.ResourceManager("@py")
    probe("A after rm2 create", a)

    print("\n-- step2: rm2 打开 IT2705 socket --")
    b = rm2.open_resource(IT2705_RES)
    b.timeout = 10000
    b.write_termination = "\n"
    b.read_termination = "\n"
    probe("B opened (rm2)", b)
    probe("A after B open", a)

    print("\n-- step3: rm2 查询 IT2705 *IDN? --")
    probe("B query", b)
    probe("A after B query", a)

    print("\n-- step4: 关闭 B --")
    b.close()
    probe("A after B close", a)

    print("\n-- step5: rm1 重新查询 A --")
    probe("A final", a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
