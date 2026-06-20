import numpy as np

CSV = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\test.csv"


def load(path):
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    return data[:, 0], data[:, 1]


def main():
    t, v = load(CSV)
    dt = float(np.median(np.diff(t)))

    lo, hi = 0.4154, 0.4169
    m = (t >= lo) & (t <= hi)
    tw = t[m]
    vw = v[m]
    print(f"window {lo}~{hi}s  dt={dt*1e6:.1f}us  points={len(vw)}")
    print(f"min={vw.min():.3f} max={vw.max():.3f} mean={vw.mean():.3f} A")

    print("\n=== raw points ===")
    for ti, vi in zip(tw, vw):
        bar = "#" * int(vi / vw.max() * 50) if vw.max() > 0 else ""
        print(f"  {ti:.6f}  {vi:7.3f}  {bar}")

    print("\n=== local STA-LTA inside the window ===")
    char = vw * vw
    cum = np.concatenate(([0.0], np.cumsum(char)))
    sta_n = max(1, int(round(2e-5 / dt)))
    lta_n = max(2, int(round(2e-4 / dt)))

    def wm(n):
        s = cum[n:] - cum[:-n]
        out = np.full(vw.shape, np.nan)
        out[n - 1:] = s / n
        return out

    sta = wm(sta_n)
    lta = wm(lta_n)
    ratio = np.zeros_like(vw)
    valid = lta > 0
    ratio[valid] = np.nan_to_num(sta[valid]) / lta[valid]
    print(f"  sta_n={sta_n} lta_n={lta_n}")
    for ti, vi, ri in zip(tw, vw, ratio):
        print(f"  {ti:.6f}  v={vi:7.3f}  ratio={ri:7.2f}")


if __name__ == "__main__":
    main()
