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


def seg_feats(t, v, a, b, dt):
    seg = v[a:b]
    integ = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    return {
        "t0": float(t[a]),
        "t1": float(t[b - 1]),
        "mean": float(seg.mean()),
        "peak": float(seg.max()),
        "width_ms": (float(t[b - 1]) - float(t[a])) * 1e3,
        "charge_uAh": float(integ(seg, dx=dt)) / 3.6 * 1e3,
        "pts": b - a,
    }


def main():
    t, v = load(CSV)
    dt = float(np.median(np.diff(t)))
    lo, hi = 0.4154, 0.4169
    m = (t >= lo) & (t <= hi)
    tw, vw = t[m], v[m]
    print(f"window {lo}~{hi}s  points={len(vw)}  dt={dt*1e6:.1f}us")

    for pen in (3.0, 6.0, 10.0):
        cps = pelt_mean(vw, pen=pen, min_size=3)
        bounds = [0] + cps + [len(vw)]
        print(f"\n=== PELT pen={pen}  -> {len(bounds)-1} segments ===")
        for i in range(len(bounds) - 1):
            f = seg_feats(tw, vw, bounds[i], bounds[i + 1], dt)
            print(f"  S{i+1}: t=[{f['t0']:.6f},{f['t1']:.6f}] mean={f['mean']:5.2f}A "
                  f"peak={f['peak']:6.2f}A w={f['width_ms']:.3f}ms q={f['charge_uAh']:.3f}uAh pts={f['pts']}")

    print("\n=== RX-level summary (pen=6, plateaus mean>2.5A) ===")
    cps = pelt_mean(vw, pen=6.0, min_size=3)
    bounds = [0] + cps + [len(vw)]
    rx = 0
    for i in range(len(bounds) - 1):
        f = seg_feats(tw, vw, bounds[i], bounds[i + 1], dt)
        if f["mean"] > 2.5:
            rx += 1
            tag = " (+spike)" if f["peak"] > 8 else ""
            print(f"  RX{rx}: t=[{f['t0']:.6f},{f['t1']:.6f}] mean={f['mean']:.2f}A "
                  f"peak={f['peak']:.2f}A w={f['width_ms']:.3f}ms q={f['charge_uAh']:.3f}uAh{tag}")
    print(f"  total RX plateaus detected = {rx}")


if __name__ == "__main__":
    main()
