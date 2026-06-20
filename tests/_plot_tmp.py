import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\test.csv"
out = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\test_waveform.png"

data = np.genfromtxt(path, delimiter=",", names=True)
names = data.dtype.names
t = data[names[0]]
i = data[names[1]]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), constrained_layout=True)

# ---- Top: full overview ----
ax1.plot(t, i, lw=0.4, color="#1f77b4")
ax1.set_title("Current Waveform Overview  (F1-A-I1, fs=50kHz, 5s)", fontsize=12, fontweight="bold")
ax1.set_xlabel("Time (s)")
ax1.set_ylabel("Current (A)")
ax1.grid(True, alpha=0.3)

# stage shading
ax1.axvspan(0.0, 0.36, color="#cccccc", alpha=0.25)
ax1.axvspan(0.41, 1.0, color="#ffcc80", alpha=0.30)
ax1.axvspan(1.07, t[-1], color="#a5d6a7", alpha=0.30)
ax1.text(0.18, 30, "(1) Idle\n~3mA", ha="center", fontsize=8)
ax1.text(0.70, 30, "(3) High-load init\n~2.7A", ha="center", fontsize=8)
ax1.text(3.0, 30, "(5) Steady state ~1.52A", ha="center", fontsize=8)

# inrush spikes
for ts, lbl in [(0.36, "(2) inrush ~24A"), (0.713, "(4) inrush 33.3A")]:
    idx = np.argmin(np.abs(t - ts))
    seg = i[max(0, idx-200):idx+200]
    pk_local = seg.max()
    pk_idx = max(0, idx-200) + int(np.argmax(seg))
    ax1.annotate(lbl, xy=(t[pk_idx], i[pk_idx]), xytext=(t[pk_idx]+0.4, i[pk_idx]),
                 fontsize=8, color="red",
                 arrowprops=dict(arrowstyle="->", color="red", lw=0.8))

# ---- Bottom: steady-state zoom ----
m = (t >= 1.2) & (t <= 1.4)
ax2.plot(t[m], i[m], lw=0.6, color="#2e7d32")
ax2.axhline(np.mean(i[m]), color="red", ls="--", lw=0.8,
            label=f"mean = {np.mean(i[m]):.3f} A")
ax2.set_title("Steady-State Zoom (1.2s - 1.4s)", fontsize=11, fontweight="bold")
ax2.set_xlabel("Time (s)")
ax2.set_ylabel("Current (A)")
ax2.grid(True, alpha=0.3)
ax2.legend(loc="upper right", fontsize=8)

fig.savefig(out, dpi=130)
print("saved:", out)
