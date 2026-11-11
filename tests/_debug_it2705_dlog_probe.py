#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IT2705 真机 DLOG/ELOG/SCOPe 采样能力探针（一次性调试）。

目标：确认 20us 级采样在真机上的可行路径：
1. DLOG:PER 实际范围 + FETC:DLOG 返回标量还是数组；
2. ELOG:PER 实际范围 + FETC:ELOG? 数据格式（记录数组）；
3. SCOPe 时基/记录长度/WAV:DATA? 格式。

安全：全程不开输出，仅测量记录功能；地址走 KK_LAB_IT2705_RESOURCE 环境变量。
"""
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


def q(instr, cmd, timeout_ms=None):
    old = None
    if timeout_ms is not None:
        old = instr.timeout
        instr.timeout = timeout_ms
    try:
        t0 = time.time()
        resp = instr.query(cmd)
        dt = time.time() - t0
    finally:
        if old is not None:
            instr.timeout = old
    text = resp.strip()
    preview = text if len(text) <= 200 else f"{text[:120]}...<{len(text)} chars>...{text[-40:]}"
    print(f"Q {cmd!r} -> ({dt * 1000:.0f} ms) {preview}")
    return text


def w(instr, cmd):
    print(f"W {cmd!r}")
    instr.write(cmd)


def drain_errors(instr, tag):
    for _ in range(8):
        err = q(instr, "SYST:ERR?")
        if err.startswith("0") or "no error" in err.lower():
            break
        print(f"  [{tag}] ERR: {err}")


def probe_dlog(instr):
    print("\n========== DLOG probe ==========")
    q(instr, "SENS:DLOG:PER? MIN")
    q(instr, "SENS:DLOG:PER? MAX")
    q(instr, "SENS:DLOG:TIME? MAX")
    try:
        q(instr, "SENS:DLOG:TINT?")
    except Exception as e:
        print(f"  TINT? failed: {e}")
    w(instr, "ABOR:DLOG")
    w(instr, "*CLS")
    w(instr, "SENS:DLOG:FUNC:CURR OFF,(@1:8)")
    w(instr, "SENS:DLOG:FUNC:VOLT OFF,(@1:8)")
    w(instr, "SENS:DLOG:FUNC:VOLT ON,(@1)")
    w(instr, "SENS:DLOG:FUNC:CURR ON,(@1)")
    period = 20e-6
    rectime = 0.2
    w(instr, f"SENS:DLOG:PER {period}")
    w(instr, f"SENS:DLOG:TIME {rectime}")
    q(instr, "SENS:DLOG:PER?")
    q(instr, "SENS:DLOG:TIME?")
    w(instr, "TRIG:DLOG:SOUR IMM")
    t0 = time.time()
    w(instr, 'INIT:DLOG "kk_probe"')
    print(f"  INIT:DLOG at {t0:.3f}, expect record {rectime}s")
    # 等待记录完成
    for _ in range(30):
        time.sleep(0.2)
        try:
            cond = q(instr, "STAT:OPER:COND? (@1)")
        except Exception as e:
            print(f"  STAT probe failed: {e}")
            break
        if (int(float(cond)) & 0x1000) == 0:
            print(f"  DLOG done after {time.time() - t0:.3f}s")
            break
    drain_errors(instr, "dlog")
    # 关键：FETC:DLOG 返回标量还是数组？
    q(instr, "FETC:DLOG:CURR? (@1)", timeout_ms=30000)
    q(instr, "FETC:DLOG:VOLT? (@1)", timeout_ms=30000)
    q(instr, "FETC:DLOG:CURR:MAX? (@1)")
    q(instr, "FETC:DLOG:ALL? (@1)", timeout_ms=30000)
    w(instr, "ABOR:DLOG")
    drain_errors(instr, "dlog-fetch")


def probe_elog(instr):
    print("\n========== ELOG probe ==========")
    q(instr, "SENS:ELOG:PER? MIN,(@1)")
    q(instr, "SENS:ELOG:PER? MAX,(@1)")
    w(instr, "ABOR:ELOG (@1:8)")
    w(instr, "*CLS")
    w(instr, "SENS:ELOG:FUNC:VOLT ON,(@1)")
    w(instr, "SENS:ELOG:FUNC:CURR ON,(@1)")
    w(instr, "SENS:ELOG:PER 0.0001,(@1)")
    q(instr, "SENS:ELOG:PER? (@1)")
    w(instr, "TRIG:ELOG:SOUR IMM,(@1)")
    w(instr, "INIT:ELOG (@1)")
    w(instr, "TRIG:ELOG (@1)")
    time.sleep(0.3)
    w(instr, "FORM ASC")
    q(instr, "FETC:ELOG? 50,(@1)", timeout_ms=15000)
    q(instr, "FETC:ELOG? 1000,(@1)", timeout_ms=15000)
    w(instr, "ABOR:ELOG (@1)")
    drain_errors(instr, "elog")


def probe_scope(instr):
    print("\n========== SCOPe probe ==========")
    try:
        q(instr, "SCOP:TIM:SCAL? MIN")
        q(instr, "SCOP:TIM:SCAL? MAX")
        q(instr, "SCOP:REC:LENG?")
        q(instr, "SCOP:STAT?")
        q(instr, "SCOP:RST?")
        w(instr, "SCOP:LINE:SEL 1,ON,U1")
        q(instr, "SCOP:LINE:SEL? 1")
        q(instr, "SCOP:DATA:TAG?")
        w(instr, "FORM ASC")
        q(instr, "SCOP:WAV:DATA?", timeout_ms=30000)
    except Exception as e:
        print(f"  SCOPe probe failed: {e}")
    drain_errors(instr, "scope")


def main():
    try:
        rm = pyvisa.ResourceManager()
    except Exception as e:
        print(f"system VISA unavailable ({e}), fallback to @py")
        rm = pyvisa.ResourceManager("@py")
    instr = rm.open_resource(RESOURCE)
    instr.timeout = 10000
    instr.encoding = "utf-8"
    instr.read_termination = "\n"
    instr.write_termination = "\n"
    try:
        q(instr, "*IDN?")
        q(instr, "SYST:CHAN:STAT? (@1:8)")
        probe_dlog(instr)
        probe_elog(instr)
        probe_scope(instr)
    finally:
        try:
            w(instr, "ABOR:DLOG")
            w(instr, "ABOR:ELOG (@1:8)")
        except Exception:
            pass
        instr.close()
        print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
