import numpy as np

CSV = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\test.csv"


def load(path):
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    return data[:, 0], data[:, 1]


def pelt_mean(values, pen, min_size=3):
    n = len(values)
    cs = np.concatenate(([0.0], np.cumsum(values)))
    cs2 = np.concatenate(([0.0], np.cumsum(values * values)))

    def cost(a, b):
        m = b - a
        if m <= 0:
            return 0.0
        s = cs[b] - cs[a]
        s2 = cs2[b] - cs2[a]
        return s2 - s * s / m

    F = np.full(n + 1, np.inf)
    F[0] = -pen
    cp = [[] for _ in range(n + 1)]
    R = [0]
    for tau in range(min_size, n + 1):
        best, arg = np.inf, 0
        for s in R:
            if tau - s < min_size:
                continue
            c = F[s] + cost(s, tau) + pen
            if c < best:
                best, arg = c, s
        F[tau] = best
        cp[tau] = cp[arg] + [arg]
        R = [s for s in R if F[s] + cost(s, tau) <= F[tau]] + [tau]
    return [c for c in cp[n] if c > 0]


def classify(seg, baseline, width_ms):
    mean = float(seg.mean())
    peak = float(seg.max())
    p2m = peak / mean if mean > 1e-9 else 0.0
    if mean <= baseline * 1.5:
        return "idle/low"
    if width_ms < 0.08 and p2m > 2.0:
        return "spike"
    if p2m > 3.0:
        return "spike"
    return "plateau"


def main():
    t, v = load(CSV)
    dt = float(np.median(np.diff(t)))
    integ = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    n = len(v)
    baseline = float(np.median(v))
    print(f"points={n} dt={dt*1e6:.1f}us fs={1/dt/1e3:.0f}kHz dur={t[-1]:.3f}s baseline(median)={baseline:.3f}A")

    regions = [
        ("R1 startup-inrush", 0.36, 0.42),
        ("R2 RX-cluster zoom", 0.4154, 0.4169),
        ("R3 second-inrush", 0.705, 0.720),
    ]
    for name, lo, hi in regions:
        m = (t >= lo) & (t <= hi)
        tw, vw = t[m], v[m]
        if len(vw) < 6:
            continue
        cps = pelt_mean(vw, pen=6.0, min_size=3)
        bounds = [0] + cps + [len(vw)]
        print(f"\n### {name}  [{lo},{hi}]s  pts={len(vw)}  -> {len(bounds)-1} segments")
        for i in range(len(bounds) - 1):
            a, b = bounds[i], bounds[i + 1]
            seg = vw[a:b]
            w = (float(tw[b-1]) - float(tw[a])) * 1e3
            lab = classify(seg, baseline, w)
            q = float(integ(seg, dx=dt)) / 3.6 * 1e3
            print(f"  S{i+1:02d} {lab:9s} t=[{tw[a]:.6f},{tw[b-1]:.6f}] "
                  f"mean={seg.mean():6.2f} peak={seg.max():6.2f} p2m={seg.max()/max(seg.mean(),1e-9):4.1f} "
                  f"w={w:6.3f}ms q={q:7.3f}uAh pts={b-a}")


if __name__ == "__main__":
    main()
