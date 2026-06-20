import sys
sys.path.insert(0, ".")
from instruments.power.keysight.n6705c_datalog_process import import_csv_file
from core.ai.providers.waveform_provider import lttb_downsample

CSV = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\test_maker_export.csv"
OUT = r"d:\CodeProject\TRAE_Projects\KK_Lab\tests\lttb_preview.svg"

res = import_csv_file(CSV)
all_data = res[0]
lbl = list(all_data.keys())[0]
t = all_data[lbl]["time"]
v = all_data[lbl]["values"]
dt, dv = lttb_downsample(t, v, 1500)

W, H = 1180, 300
padL, padR, padT, padB = 70, 20, 34, 40
t0, t1 = min(t), max(t)
vmin, vmax = min(v), max(v)


def sx(x):
    return padL + (x - t0) / (t1 - t0) * (W - padL - padR)


def sy(y):
    return H - padB - (y - vmin) / (vmax - vmin) * (H - padT - padB)


def poly(ts, vs):
    return " ".join("{:.1f},{:.1f}".format(sx(a), sy(b)) for a, b in zip(ts, vs))


def panel(title, ts, vs, color):
    grid = ""
    for gy in [0.0, 1.129, 5.0, 10.0, 15.0, 20.0, 23.83]:
        if vmin <= gy <= vmax:
            yy = sy(gy)
            grid += (
                '<line x1="{l}" y1="{y:.1f}" x2="{r}" y2="{y:.1f}" '
                'stroke="#e8eaed" stroke-width="1"/>'
                '<text x="6" y="{ty:.1f}" font-size="10" fill="#5f6368">'
                "{g:.1f} A</text>"
            ).format(l=padL, r=W - padR, y=yy, ty=yy + 3, g=gy)
    return (
        '<text x="{l}" y="18" font-size="13" fill="#202124" '
        'font-family="Segoe UI,Arial">{title}</text>{grid}'
        '<polyline fill="none" stroke="{color}" stroke-width="1" '
        'points="{pts}"/>'
    ).format(l=padL, title=title, grid=grid, color=color, pts=poly(ts, vs))


svg = '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'.format(
    w=W, h=H * 2 + 10
)
svg += '<rect width="100%" height="100%" fill="white"/>'
svg += "<g>" + panel(
    "Original  {n} points  ({lbl})".format(n=len(v), lbl=lbl), t, v, "#9aa0a6"
) + "</g>"
svg += '<g transform="translate(0,{off})">'.format(off=H + 10) + panel(
    "After LTTB downsample -> {n} points  (shape points fed to AI)".format(n=len(dv)),
    dt,
    dv,
    "#1a73e8",
) + "</g>"
svg += "</svg>"

with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print("orig=", len(v), "lttb=", len(dv), "saved", OUT)
