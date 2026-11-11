#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IT2705 ELOG 流式读取第二轮真机验证（一次性调试）。

验证点：
1. ELOG:PER 20us 设置是否生效；
2. FETC:ELOG? 请求数超过缓冲量时的行为（阻塞/立即返回/返回数量）；
3. 多通道 chanlist 返回格式；
4. 20us 下缓冲容量与溢出行为（不取数跑 2s 后再取）；
5. 20us 流式取数吞吐（每 0.25s 取一次，统计记录数是否跟上 50k rec/s）；
6. FORM REAL 二进制格式可用性。
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


def q(instr, cmd, timeout_ms=None, verbose=True):
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
    if verbose:
        preview = text if len(text) <= 160 else f"{text[:100]}...<{len(text)} chars>...{text[-30:]}"
        print(f"Q {cmd!r} -> ({dt * 1000:.0f} ms) {preview}")
    return text, dt


def w(instr, cmd):
    print(f"W {cmd!r}")
    instr.write(cmd)


def drain_errors(instr, tag):
    for _ in range(10):
        err, _ = q(instr, "SYST:ERR?", verbose=False)
        if err.startswith("0"):
            break
        print(f"  [{tag}] ERR: {err}")


def count_values(text):
    if not text or text.lower() == "nan":
        return 0
    return len([v for v in text.split(",") if v.strip()])


def setup_elog(instr, channels, period_s):
    w(instr, "ABOR:ELOG (@1:8)")
    w(instr, "*CLS")
    for ch in channels:
        w(instr, f"SENS:ELOG:FUNC:VOLT:MINM OFF,(@{ch})")
        w(instr, f"SENS:ELOG:FUNC:CURR:MINM OFF,(@{ch})")
        w(instr, f"SENS:ELOG:FUNC:VOLT ON,(@{ch})")
        w(instr, f"SENS:ELOG:FUNC:CURR ON,(@{ch})")
        w(instr, f"SENS:ELOG:PER {period_s},(@{ch})")
        resp, _ = q(instr, f"SENS:ELOG:PER? (@{ch})")
        print(f"  CH{ch} ELOG:PER readback = {resp}")
    chanlist = ",".join(str(c) for c in channels)
    w(instr, f"TRIG:ELOG:SOUR IMM,(@{chanlist})")
    w(instr, "FORM ASC")
    w(instr, f"INIT:ELOG (@{chanlist})")
    w(instr, f"TRIG:ELOG (@{chanlist})")


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
        q(instr, "*IDN?", verbose=False)

        print("\n== 1) PER 20us 生效性 ==")
        setup_elog(instr, [1], 2e-05)
        time.sleep(0.5)
        text, dt = q(instr, "FETC:ELOG? 10000,(@1)", timeout_ms=30000)
        n = count_values(text)
        print(f"  fetched values={n} (records={n // 2}) in {dt:.3f}s after ~0.5s@20us (expect ~25000 rec)")
        w(instr, "ABOR:ELOG (@1)")
        drain_errors(instr, "p1")

        print("\n== 2) 请求数 > 缓冲量 的行为 ==")
        setup_elog(instr, [1], 0.001)
        time.sleep(0.3)  # ~300 records
        t0 = time.time()
        text, dt = q(instr, "FETC:ELOG? 5000,(@1)", timeout_ms=20000)
        n = count_values(text)
        print(f"  requested 5000 rec, got values={n} (records={n // 2}), blocked {time.time() - t0:.3f}s")
        w(instr, "ABOR:ELOG (@1)")
        drain_errors(instr, "p2")

        print("\n== 3) 多通道 chanlist 格式 (CH1,CH2 各 V+I, 1ms) ==")
        setup_elog(instr, [1, 2], 0.001)
        time.sleep(0.3)
        text, dt = q(instr, "FETC:ELOG? 20,(@1,2)", timeout_ms=15000)
        print(f"  values={count_values(text)}")
        text1, _ = q(instr, "FETC:ELOG? 20,(@1)", timeout_ms=15000)
        print(f"  CH1-only values={count_values(text1)}")
        text2, _ = q(instr, "FETC:ELOG? 20,(@2)", timeout_ms=15000)
        print(f"  CH2-only values={count_values(text2)}")
        w(instr, "ABOR:ELOG (@1:8)")
        drain_errors(instr, "p3")

        print("\n== 4) 20us 缓冲容量：不取数跑 2s 再取 ==")
        setup_elog(instr, [1], 2e-05)
        time.sleep(2.0)
        t0 = time.time()
        total = 0
        empty_rounds = 0
        while time.time() - t0 < 10:
            text, _ = q(instr, "FETC:ELOG? 20000,(@1)", timeout_ms=30000, verbose=False)
            n = count_values(text)
            total += n
            if n == 0:
                empty_rounds += 1
                if empty_rounds >= 2:
                    break
            else:
                empty_rounds = 0
        print(f"  drained values={total} (records={total // 2}) for 2.0s@20us (expect 100000 rec)")
        w(instr, "ABOR:ELOG (@1)")
        drain_errors(instr, "p4")

        print("\n== 5) 20us 流式取数吞吐 (CH1+CH2, 3s, 每 0.25s 取) ==")
        setup_elog(instr, [1, 2], 2e-05)
        t_start = time.time()
        counts = {1: 0, 2: 0}
        fetch_time = 0.0
        while time.time() - t_start < 3.0:
            time.sleep(0.25)
            for ch in (1, 2):
                tf = time.time()
                text, _ = q(instr, f"FETC:ELOG? 30000,(@{ch})", timeout_ms=30000, verbose=False)
                fetch_time += time.time() - tf
                counts[ch] += count_values(text) // 2
        elapsed = time.time() - t_start
        for ch in (1, 2):
            print(f"  CH{ch}: records={counts[ch]} over {elapsed:.2f}s "
                  f"(expect ~{int(elapsed / 2e-05)}), rate={counts[ch] / elapsed:.0f} rec/s")
        print(f"  total fetch time {fetch_time:.2f}s / elapsed {elapsed:.2f}s")
        w(instr, "ABOR:ELOG (@1:8)")
        drain_errors(instr, "p5")

        print("\n== 6) FORM REAL 二进制块 ==")
        setup_elog(instr, [1], 0.001)
        time.sleep(0.2)
        w(instr, "FORM REAL")
        w(instr, "FORM:BORD NORM")
        try:
            t0 = time.time()
            raw = instr.query_binary_values("FETC:ELOG? 100,(@1)", datatype="f",
                                            container=list, expect_ascii=False)
            print(f"  REAL/NORM: {len(raw)} floats in {time.time() - t0:.3f}s, head={raw[:6]}")
        except Exception as e:
            print(f"  REAL/NORM failed: {e}")
        w(instr, "FORM ASC")
        w(instr, "ABOR:ELOG (@1:8)")
        drain_errors(instr, "p6")
    finally:
        try:
            w(instr, "FORM ASC")
            w(instr, "ABOR:ELOG (@1:8)")
        except Exception:
            pass
        instr.close()
        print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
