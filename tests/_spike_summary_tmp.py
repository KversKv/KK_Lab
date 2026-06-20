import sys
sys.path.insert(0, ".")
from instruments.power.keysight.n6705c_datalog_process import import_csv_file
from core.ai.providers.waveform_provider import lttb_downsample

CSV = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\test_maker_export.csv"
res = import_csv_file(CSV)
all_data = res[0]
lbl = list(all_data.keys())[0]
t = all_data[lbl]["time"]
v = all_data[lbl]["values"]
n = len(v)
avg = sum(v) / n
std = (sum((x - avg) ** 2 for x in v) / n) ** 0.5
print("label=%s n=%d avg=%.4f std=%.4f max=%.4f" % (lbl, n, avg, std, max(v)))

thr = avg + 3 * std
print("threshold(avg+3sigma)=%.4f A" % thr)


def cluster(pts, gap_s=0.0005):
    pts = sorted(pts)
    groups = []
    cur = []
    for p in pts:
        if cur and p[0] - cur[-1][0] > gap_s:
            groups.append(cur)
            cur = []
        cur.append(p)
    if cur:
        groups.append(cur)
    return groups


raw = [(t[i], v[i]) for i in range(n) if v[i] > thr]
print("\n== RAW 原始数据 spike (>3sigma) 共 %d 个 ==" % len(raw))
g = cluster(raw)
for k, grp in enumerate(g, 1):
    pk = max(grp, key=lambda x: x[1])
    print(
        "  簇%d: %d点  时间[%.6f~%.6f]s  峰值=%.4f A @t=%.6f"
        % (k, len(grp), grp[0][0], grp[-1][0], pk[1], pk[0])
    )

dt, dv = lttb_downsample(t, v, 1500)
ravg = sum(dv) / len(dv)
rstd = (sum((x - ravg) ** 2 for x in dv) / len(dv)) ** 0.5
rthr = ravg + 3 * rstd
lraw = [(dt[i], dv[i]) for i in range(len(dv)) if dv[i] > rthr]
print(
    "\n== LTTB 1500点 spike(>3sigma=%.4f) 共 %d 个，分 %d 簇 =="
    % (rthr, len(lraw), len(cluster(lraw)))
)
for k, grp in enumerate(cluster(lraw), 1):
    pk = max(grp, key=lambda x: x[1])
    print(
        "  簇%d: %d点  时间[%.6f~%.6f]s  峰值=%.4f A @t=%.6f"
        % (k, len(grp), grp[0][0], grp[-1][0], pk[1], pk[0])
    )
