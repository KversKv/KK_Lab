import numpy as np

path = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\test.csv"
data = np.genfromtxt(path, delimiter=",", names=True)
names = data.dtype.names
t = data[names[0]]
i = data[names[1]]
dt = np.median(np.diff(t))

m = (t >= 0.40) & (t <= 0.42)
tw = t[m]
iw = i[m]

# spike = points clearly above the ~2A plateau, e.g. > 5A
thr = 5.0
above = iw > thr
edges = np.diff(above.astype(int))
starts = np.where(edges == 1)[0] + 1
ends = np.where(edges == -1)[0] + 1
if above[0]:
    starts = np.insert(starts, 0, 0)
if above[-1]:
    ends = np.append(ends, len(iw) - 1)

print(f"window 0.40-0.42s, threshold {thr}A")
print(f"number of spike events: {len(starts)}\n")
centers = []
for k, (s, e) in enumerate(zip(starts, ends), 1):
    seg = iw[s:e + 1]
    c = (tw[s] + tw[e]) / 2
    centers.append(c)
    print(f"  spike #{k}: t={tw[s]:.6f}->{tw[e]:.6f}s  "
          f"width={(e-s+1)*dt*1e6:.0f}us  peak={seg.max():.3f}A  npts={e-s+1}")

if len(centers) >= 2:
    per = np.diff(centers)
    print(f"\nspike spacing (ms): {[round(p*1e3,3) for p in per]}")
    print(f"mean period {per.mean()*1e3:.3f} ms -> rep rate {1/per.mean():.1f} Hz")

# how many points before first spike are still 'quiet'
first = starts[0]
print(f"\nbefore first spike (0.40s..{tw[first]:.5f}s): "
      f"max I = {iw[:first].max():.4f} A (confirm no earlier pulse)")
