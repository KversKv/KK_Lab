import numpy as np

path = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\test.csv"
data = np.genfromtxt(path, delimiter=",", names=True)
names = data.dtype.names
t = data[names[0]]
i = data[names[1]]
n = len(t)
dt = np.median(np.diff(t))
fs = 1.0 / dt

# Coarse profile: average current in 50ms windows over whole capture
win = int(0.05 * fs)
nb = n // win
prof_t = []
prof_m = []
prof_pk = []
for b in range(nb):
    seg = i[b*win:(b+1)*win]
    prof_t.append(t[b*win])
    prof_m.append(seg.mean())
    prof_pk.append(seg.max())
prof_t = np.array(prof_t); prof_m = np.array(prof_m); prof_pk = np.array(prof_pk)

print("=== 50ms-window profile (full 5s) ===")
print("t(s)   mean(A)  peak(A)")
for tt, mm, pk in zip(prof_t, prof_m, prof_pk):
    bar = "#" * int(mm * 8)
    print(f"{tt:5.2f}  {mm:6.3f}  {pk:7.3f} {bar}")

# Active region = mean window current well above quiet baseline
quiet = np.median(prof_m[prof_m < np.percentile(prof_m, 30)])
print(f"\nquiet baseline mean ~ {quiet:.4f} A")

# Count the >33A spike location
imax = np.argmax(i)
print(f"global max {i[imax]:.3f} A at t={t[imax]:.5f}s (single-sample spike check)")
print(f"neighbors: {i[imax-2:imax+3]}")
