#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IT2705 ELOG 第三轮真机验证：缓冲容量 / 启动延迟 / FORM REAL 吞吐（一次性调试）。"""
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
    except Exception:
        try:
            instr.clear()
        except Exception:
            pass
        raise
    finally:
        if old is not None:
            instr.timeout = old
    text = resp.strip()
    if verbose:
        preview = text if len(text) <= 160 else f"{text[:100]}...<{len(text)} chars>"
        print(f"Q {cmd!r} -> ({dt * 1000:.0f} ms) {preview}")
    return text, dt


def w(instr, cmd):
    print(f"W {cmd!r}")
    instr.write(cmd)


def count_values(text):
    if not text or text.lower() == "nan":
        return 0
    return len([v for v in text.split(",") if v.strip()])


def setup_elog(instr, channels, period_s, use_real=False):
    w(instr, "ABOR:ELOG (@1:8)")
    w(instr, "*CLS")
    for ch in channels:
        w(instr, f"SENS:ELOG:FUNC:VOLT:MINM OFF,(@{ch})")
        w(instr, f"SENS:ELOG:FUNC:CURR:MINM OFF,(@{ch})")
        w(instr, f"SENS:ELOG:FUNC:VOLT ON,(@{ch})")
        w(instr, f"SENS:ELOG:FUNC:CURR ON,(@{ch})")
        w(instr, f"SENS:ELOG:PER {period_s},(@{ch})")
    chanlist = ",".join(str(c) for c in channels)
    w(instr, f"TRIG:ELOG:SOUR IMM,(@{chanlist})")
    w(instr, "FORM REAL" if use_real else "FORM ASC")
    w(instr, f"INIT:ELOG (@{chanlist})")
    w(instr, f"TRIG:ELOG (@{chanlist})")


def fetch_records_ascii(instr, ch, max_records, timeout_ms=30000):
    text, dt = q(instr, f"FETC:ELOG? {max_records},(@{ch})",
                 timeout_ms=timeout_ms, verbose=False)
    return count_values(text) // 2, dt


def drain(instr, ch, period_s, label, chunk=10000):
    total = 0
    t0 = time.time()
    empty = 0
    while time.time() - t0 < 15:
        n, _ = fetch_records_ascii(instr, ch, chunk)
        total += n
        if n == 0:
            empty += 1
            if empty >= 2:
                break
        else:
            empty = 0
    print(f"  [{label}] drained records={total}")
    return total


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

        print("\n== 0) maxrecords 上限二分 ==")
        setup_elog(instr, [1], 0.001)
        time.sleep(1.0)  # ~1000 records buffered
        for req in (1000, 5000, 10000, 12000, 15000, 20000, 30000, 50000):
            try:
                text, dt = q(instr, f"FETC:ELOG? {req},(@1)", timeout_ms=15000, verbose=False)
                print(f"  req={req}: OK values={count_values(text)} in {dt:.2f}s")
                setup_elog(instr, [1], 0.001)  # 复位缓冲
                time.sleep(1.0)
            except Exception as e:
                print(f"  req={req}: FAIL {type(e).__name__}")
                setup_elog(instr, [1], 0.001)
                time.sleep(1.0)
        w(instr, "ABOR:ELOG (@1)")

        print("\n== A) 1ms 记录 2.0s 的记录数准确性（结尾一次性排空） ==")
        setup_elog(instr, [1], 0.001)
        t0 = time.time()
        time.sleep(2.0)
        rec = drain(instr, 1, 0.001, "A")
        print(f"  elapsed {time.time() - t0:.3f}s, expect ~2000 rec, got {rec}")
        w(instr, "ABOR:ELOG (@1)")

        print("\n== B) 20us 缓冲容量：不取数跑 2.0s 再排空 ==")
        setup_elog(instr, [1], 2e-05)
        t0 = time.time()
        time.sleep(2.0)
        rec = drain(instr, 1, 2e-05, "B")
        print(f"  expect 100000 rec, got {rec} -> buffer ~= {rec} rec")
        w(instr, "ABOR:ELOG (@1)")

        print("\n== C) FORM REAL 双流式 20us (CH1+CH2, 3s, 每 0.2s 交替取) ==")
        w(instr, "FORM:BORD NORM")
        setup_elog(instr, [1, 2], 2e-05, use_real=True)
        t_start = time.time()
        counts = {1: 0, 2: 0}
        fetch_t = 0.0
        last = t_start
        while time.time() - t_start < 3.0:
            now = time.time()
            if now - last < 0.2:
                time.sleep(0.01)
                continue
            last = now
            for ch in (1, 2):
                tf = time.time()
                vals = instr.query_binary_values(
                    f"FETC:ELOG? 10000,(@{ch})", datatype="f", container=list,
                )
                fetch_t += time.time() - tf
                counts[ch] += len(vals) // 2
        elapsed = time.time() - t_start
        for ch in (1, 2):
            print(f"  CH{ch}: records={counts[ch]} / expect ~{int(elapsed / 2e-05)}, "
                  f"rate={counts[ch] / elapsed:.0f} rec/s")
        print(f"  fetch total {fetch_t:.2f}s / elapsed {elapsed:.2f}s")
        w(instr, "FORM ASC")
        w(instr, "ABOR:ELOG (@1:8)")

        print("\n== D) ABOR 后数据是否清空 ==")
        setup_elog(instr, [1], 0.001)
        time.sleep(0.3)
        w(instr, "ABOR:ELOG (@1)")
        text, _ = q(instr, "FETC:ELOG? 1000,(@1)", verbose=False)
        print(f"  after ABOR values={count_values(text)}")
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
