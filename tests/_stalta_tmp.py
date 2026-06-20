import numpy as np

CSV = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\test.csv"


def load(path):
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    t = data[:, 0]
    v = data[:, 1]
    return t, v


def sta_lta(values, sta_n, lta_n):
    char = values * values
    cum = np.concatenate(([0.0], np.cumsum(char)))

    def win_mean(n):
        s = cum[n:] - cum[:-n]
        out = np.full(values.shape, np.nan)
        out[n - 1:] = s / n
        return out

    sta = win_mean(sta_n)
    lta = win_mean(lta_n)
    ratio = np.full(values.shape, 0.0)
    valid = lta > 0
    ratio[valid] = np.nan_to_num(sta[valid]) / lta[valid]
    return ratio


def trigger(ratio, on, off):
    events = []
    active = False
    start = 0
    for i, r in enumerate(ratio):
        if not active and r >= on:
            active = True
            start = i
        elif active and r <= off:
            active = False
            events.append((start, i))
    if active:
        events.append((start, len(ratio) - 1))
    return events


def merge(events, gap):
    if not events:
        return []
    merged = [list(events[0])]
    for s, e in events[1:]:
        if s - merged[-1][1] <= gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def mad_gate(values, events, k):
    med = float(np.median(values))
    mad = float(np.median(np.abs(values - med)))
    floor = med + k * mad * 1.4826
    kept = []
    for i0, i1 in events:
        if float(values[i0:i1 + 1].max()) >= floor:
            kept.append((i0, i1))
    return kept, med, mad, floor


def seg_features(t, v, i0, i1, dt):
    seg = v[i0:i1 + 1]
    pk = float(seg.max())
    width_ms = (t[i1] - t[i0]) * 1e3
    integ = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    charge_mAh = float(integ(seg, dx=dt)) / 3.6
    return pk, width_ms, charge_mAh, i1 - i0 + 1


def main():
    t, v = load(CSV)
    n = len(v)
    dt = float(np.median(np.diff(t)))
    fs = 1.0 / dt
    print(f"points={n}  dt={dt*1e6:.1f}us  fs={fs/1000:.1f}kHz  dur={t[-1]:.3f}s")

    sta_s, lta_s = 1e-4, 5e-3
    sta_n = max(1, int(round(sta_s / dt)))
    lta_n = max(2, int(round(lta_s / dt)))
    on, off = 4.0, 1.5
    print(f"STA={sta_n}pt({sta_s*1e3:.2f}ms) LTA={lta_n}pt({lta_s*1e3:.2f}ms) on={on} off={off}")

    ratio = sta_lta(v, sta_n, lta_n)
    raw = trigger(ratio, on, off)
    merge_gap = int(round(2e-4 / dt))
    events = merge(raw, merge_gap)
    print(f"\nstep1 STA-LTA raw triggers={len(raw)}  merged={len(events)}")

    kept, med, mad, floor = mad_gate(v, events, k=6.0)
    print(f"step2 MAD gate: median={med:.4f}A mad={mad:.4f}A floor={floor:.3f}A  -> kept={len(kept)}")

    print("\n=== effective events (whole 5s, no manual window/threshold) ===")
    for k, (i0, i1) in enumerate(kept, 1):
        pk, w, q, pts = seg_features(t, v, i0, i1, dt)
        print(f"  E{k:02d}  t=[{t[i0]:.6f},{t[i1]:.6f}]  peak={pk:6.2f}A  width={w:6.3f}ms  charge={q*1e3:6.3f}uAh  pts={pts}")

    lo, hi = 0.40, 0.42
    win = [(i0, i1) for (i0, i1) in kept if t[i1] >= lo and t[i0] <= hi]
    print(f"\n=== events within 0.40~0.42s : {len(win)} ===")
    for k, (i0, i1) in enumerate(win, 1):
        pk, w, q, pts = seg_features(t, v, i0, i1, dt)
        print(f"  #{k}  start={t[i0]:.6f}s  peak={pk:.2f}A  width={w:.3f}ms  pts={pts}")


if __name__ == "__main__":
    main()
