"""SWED（Sliding-Window Event Detection）原型，按
docs/user/algorithm/SlidingWindowEventDetection.md §6 实现，并用 test.csv 校验。

核心：增量滑动均值(O(1)) + 单调双端队列极值(摊还O(1)) + 双判据状态机 + 睡眠门限闸门。
零第三方依赖（numpy 仅用于载入；算法主循环为纯 Python 标量）。
"""
import collections
import os
import time

import numpy as np

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.csv")
EPS = 1e-9


def load():
    arr = np.genfromtxt(CSV, delimiter=",", skip_header=1)
    return arr[:, 0].tolist(), arr[:, 1].tolist()


def swed(
    times,
    values,
    *,
    T=2e-4,
    theta_avg_in=0.20,
    theta_avg_out=0.10,
    theta_ext=0.35,
    theta_end=0.50,
    sleep_floor=0.4,
    merge_gap_s=2e-4,
):
    n = len(values)
    if n < 4:
        return [], {}
    dt = float(np.median(np.diff(np.asarray(times[: min(n, 1000)]))))
    W = max(1, int(round(T / dt)))
    if W >= n:
        W = n // 2

    v = values
    floor = sleep_floor

    S = sum(v[:W])
    dmax = collections.deque()
    dmin = collections.deque()
    for i in range(W):
        while dmax and v[dmax[-1]] <= v[i]:
            dmax.pop()
        dmax.append(i)
        while dmin and v[dmin[-1]] >= v[i]:
            dmin.pop()
        dmin.append(i)

    AVG_prev = S / W
    BASE = AVG_prev
    state = "IDLE"
    cooldown = 0
    R = 1 << 16

    events = []
    cur = None
    n_windows = n - W + 1

    for win in range(n_windows):
        if win > 0:
            out_idx = win - 1
            in_idx = win + W - 1
            S += v[in_idx] - v[out_idx]
            while dmax and v[dmax[-1]] <= v[in_idx]:
                dmax.pop()
            dmax.append(in_idx)
            while dmin and v[dmin[-1]] >= v[in_idx]:
                dmin.pop()
            dmin.append(in_idx)
            while dmax and dmax[0] < win:
                dmax.popleft()
            while dmin and dmin[0] < win:
                dmin.popleft()

        if win % R == 0 and win > 0:
            S = sum(v[win : win + W])

        AVG = S / W
        Mx = v[dmax[0]]
        Mn = v[dmin[0]]

        denom_base = max(abs(BASE), floor, EPS)
        denom_avg = max(abs(AVG), floor, EPS)
        asleep = AVG < sleep_floor
        active = not asleep and (Mx >= floor or AVG >= floor)
        hitA = active and abs(AVG - BASE) / denom_base >= theta_avg_in
        up = (Mx - AVG) / denom_avg
        dn = (AVG - Mn) / denom_avg
        hitB_up = not asleep and up >= theta_ext and Mx >= floor
        hitB_dn = not asleep and dn >= theta_ext and Mx >= floor

        if state == "IDLE":
            if cooldown == 0 and (hitA or hitB_up or hitB_dn):
                etype = "level" if hitA and not (hitB_up or hitB_dn) else (
                    "spike" if hitB_up else "dip"
                )
                cur = {
                    "i0": win,
                    "start": times[win],
                    "type": etype,
                    "trigger": "A" if hitA else "B",
                    "_sum": 0.0,
                    "_cnt": 0,
                    "peak": Mx,
                    "min": Mn,
                    "_emax": max(AVG, BASE),
                }
                state = "IN_EVENT"
        if state == "IN_EVENT":
            cur["_sum"] += AVG
            cur["_cnt"] += 1
            cur["peak"] = max(cur["peak"], Mx)
            cur["min"] = min(cur["min"], Mn)
            cur["_emax"] = max(cur["_emax"], AVG)
            if (hitB_up or hitB_dn) and cur["type"] == "level":
                cur["type"] = "spike"
            ev_ref = max(cur["_emax"], BASE, floor)
            fell_back = AVG <= ev_ref * (1.0 - theta_end)
            slept = AVG < sleep_floor
            ext_calm = up < theta_ext and dn < theta_ext
            if (fell_back or slept) and ext_calm:
                cur["end"] = times[win]
                cur["avg"] = cur["_sum"] / max(cur["_cnt"], 1)
                cur["duration_ms"] = (cur["end"] - cur["start"]) * 1e3
                events.append(cur)
                BASE = AVG
                state = "IDLE"
                cooldown = W
                cur = None
        AVG_prev = AVG
        if cooldown > 0:
            cooldown -= 1

    if cur is not None:
        cur["end"] = times[-1]
        cur["avg"] = cur["_sum"] / max(cur["_cnt"], 1)
        cur["duration_ms"] = (cur["end"] - cur["start"]) * 1e3
        events.append(cur)

    merged = []
    gap = merge_gap_s
    for e in events:
        if merged and e["type"] in ("spike", "dip") and merged[-1]["type"] in (
            "spike", "dip"
        ) and (e["start"] - merged[-1]["end"]) <= gap:
            m = merged[-1]
            m["end"] = e["end"]
            m["peak"] = max(m["peak"], e["peak"])
            m["min"] = min(m["min"], e["min"])
            m["avg"] = (m["avg"] + e["avg"]) / 2.0
            m["duration_ms"] = (m["end"] - m["start"]) * 1e3
        else:
            merged.append(e)

    for e in merged:
        for k in ("_sum", "_cnt", "_emax", "i0"):
            e.pop(k, None)

    info = {
        "dt": dt,
        "W": W,
        "floor": floor,
        "sleep_floor": sleep_floor,
        "raw_events": len(events),
    }
    return merged, info


def main():
    times, values = load()
    print(f"== test.csv: {len(values)} 点 ==")
    t0 = time.perf_counter()
    events, info = swed(times, values)
    elapsed = (time.perf_counter() - t0) * 1e3
    print(
        f"dt={info['dt']*1e6:.1f}us  W={info['W']}pt  "
        f"floor={info['floor']:.4f}mA (sleep_floor={info['sleep_floor']*1e3:.0f}uA)  "
        f"raw={info['raw_events']} -> merged={len(events)}  ({elapsed:.0f} ms)\n"
    )
    print(f"{'type':6s} {'trig':4s} {'start(s)':>10s} {'end(s)':>10s} "
          f"{'dur_ms':>8s} {'avg(mA)':>8s} {'peak(mA)':>8s} {'min(mA)':>8s}")
    for e in events:
        print(
            f"{e['type']:6s} {e['trigger']:4s} {e['start']:10.5f} {e['end']:10.5f} "
            f"{e['duration_ms']:8.3f} {e['avg']:8.3f} {e['peak']:8.3f} {e['min']:8.3f}"
        )

    print("\n-- 校验：4 浪涌簇(0.409~0.416s) + 2 涌流(0.710/0.713s) --")
    spikes = [e for e in events if e["type"] in ("spike", "dip")]
    region1 = [e for e in spikes if 0.405 <= e["start"] <= 0.418]
    region2 = [e for e in spikes if 0.705 <= e["start"] <= 0.716]
    print(f"  0.40~0.42s 簇事件数 = {len(region1)}")
    print(f"  0.70~0.72s 涌流事件数 = {len(region2)}")
    print(f"  全程峰值最大 = {max((e['peak'] for e in events), default=0):.2f} mA")

    synth_sleep_test()


def synth_sleep_test():
    """合成睡眠场景（单位 mA，与 test.csv 一致）：验证 sleep_floor 压制睡眠抖动、不漏真实唤醒。"""
    print("\n== 合成 MCU 睡眠场景（mA）：50uA 基线 + 重尾毛刺 + 两次唤醒 ==")
    rng = np.random.default_rng(42)
    fs = 50000
    dur = 0.5
    n = int(fs * dur)
    t = (np.arange(n) / fs).tolist()
    # 睡眠基线 0.05mA(50uA)，叠加重尾抖动：多数 ±0.003mA，偶发 ±0.3mA 毛刺
    base = 0.05 + rng.normal(0, 0.003, n)
    spk = rng.random(n) < 0.003
    base[spk] += np.abs(rng.normal(0, 0.3, int(spk.sum())))
    v = np.clip(base, 0, None)
    # 唤醒 1：0.20s 处 8mA 平台，持续 2ms
    w1 = (t >= np.float64(0.20)) & (np.asarray(t) <= 0.202)
    v[w1] = 8.0 + rng.normal(0, 0.2, int(w1.sum()))
    # 唤醒 2：0.35s 处 30mA 尖峰，持续 0.2ms
    w2 = (np.asarray(t) >= 0.35) & (np.asarray(t) <= 0.3502)
    v[w2] = 30.0 + rng.normal(0, 1.0, int(w2.sum()))
    vv = v.tolist()

    for sf in (0.0, 0.4):
        ev, info = swed(t, vv, T=4e-4, sleep_floor=sf)
        tag = "关闭睡眠门限" if sf == 0.0 else f"sleep_floor={sf*1e3:.0f}uA"
        real = [e for e in ev if e["peak"] >= 2.0]
        print(
            f"  [{tag:18s}] floor={info['floor']*1e3:7.1f}uA  "
            f"事件={len(ev):3d}  真实唤醒(peak>=2mA)={len(real)}"
        )
        for e in real:
            print(
                f"      {e['type']:6s} {e['start']:.4f}s "
                f"avg={e['avg']:6.2f}mA peak={e['peak']:6.2f}mA"
            )


if __name__ == "__main__":
    main()
