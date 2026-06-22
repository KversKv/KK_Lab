import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DengXian"]
matplotlib.rcParams["axes.unicode_minus"] = False
from matplotlib.patches import Rectangle
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    with open(os.path.join(HERE, "_swed_plot_data.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def build_segments(events, t0, t1, pad=0.004, merge_gap=0.01):
    spans = []
    for e in events:
        s = max(t0, e["start"] - pad)
        en = min(t1, e["end"] + pad)
        spans.append((s, en))
    spans.sort()
    merged = []
    for s, en in spans:
        if merged and s - merged[-1][1] <= merge_gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], en))
        else:
            merged.append((s, en))
    return merged


def make_axis_map(active, t0, t1, active_frac=0.78):
    quiet = []
    cur = t0
    for s, e in active:
        if s > cur:
            quiet.append((cur, s))
        cur = e
    if cur < t1:
        quiet.append((cur, t1))

    act_real = sum(e - s for s, e in active) or 1e-9
    qui_real = sum(e - s for s, e in quiet) or 1e-9
    quiet_frac = 1.0 - active_frac

    blocks = []
    for s, e in active:
        blocks.append((s, e, "active"))
    for s, e in quiet:
        blocks.append((s, e, "quiet"))
    blocks.sort()

    pos = 0.0
    seg_map = []
    for s, e, kind in blocks:
        real_w = e - s
        if kind == "active":
            disp_w = active_frac * (real_w / act_real)
        else:
            disp_w = quiet_frac * (real_w / qui_real)
        seg_map.append((s, e, pos, pos + disp_w, kind))
        pos += disp_w
    total = pos

    def to_disp(t):
        for s, e, p0, p1, kind in seg_map:
            if s <= t <= e:
                if e == s:
                    return p0 / total
                return (p0 + (t - s) / (e - s) * (p1 - p0)) / total
        return (t - t0) / (t1 - t0)

    return to_disp, seg_map, total


def main():
    d = load()
    events = d["events"]
    ds_t = np.asarray(d["ds_t"])
    ds_v = np.asarray(d["ds_v"])
    t0, t1 = float(ds_t[0]), float(ds_t[-1])

    active = build_segments(events, t0, t1)
    to_disp, seg_map, total = make_axis_map(active, t0, t1, active_frac=0.80)

    xs = np.array([to_disp(t) for t in ds_t])

    fig, ax = plt.subplots(figsize=(15, 6.2), dpi=140)
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")

    # 背景区块：活跃区淡蓝、平稳区灰
    for s, e, p0, p1, kind in seg_map:
        color = "#1d3a5f" if kind == "active" else "#181b22"
        ax.axvspan(p0 / total, p1 / total, color=color, zorder=0)

    ax.plot(xs, ds_v, color="#4fc3f7", lw=0.8, zorder=3)

    # 事件标注
    color_map = {"level": "#ffb74d", "spike": "#ff5252", "dip": "#69f0ae"}
    seen = set()
    for e in events:
        c = color_map.get(e["type"], "#ffffff")
        xm = to_disp((e["start"] + e["end"]) / 2.0)
        if e["type"] == "spike" or e["type"] == "dip":
            ax.plot([xm], [e["peak"]], marker="v", color=c, ms=6,
                    zorder=5, mec="#0f1117", mew=0.4)
        else:
            xa = to_disp(e["start"])
            xb = to_disp(e["end"])
            ax.hlines(e["avg"], xa, xb, color=c, lw=2.2, alpha=0.85, zorder=4)
        if e["type"] not in seen:
            seen.add(e["type"])

    # 时间刻度（真实秒），落在显示坐标
    tick_real = [0.0, 0.40, 0.409, 0.413, 0.711, 0.712, 1.0, 1.08, 2.0, 3.0, 4.0, 5.0]
    tick_real = [t for t in tick_real if t0 <= t <= t1]
    tick_pos = [to_disp(t) for t in tick_real]
    ax.set_xticks(tick_pos)
    ax.set_xticklabels([f"{t:.3f}" if t not in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
                        else f"{t:.0f}" for t in tick_real],
                       rotation=0, fontsize=8, color="#c8ccd4")

    ax.set_xlim(0, 1)
    ax.set_ylim(min(d["vmin"], 0) - 1, d["vmax"] * 1.08)
    ax.set_xlabel("时间 (s)  — 非线性轴：事件区放大 / 平稳区压缩", fontsize=10, color="#c8ccd4")
    ax.set_ylabel("电流 (A)", fontsize=10, color="#c8ccd4")
    ax.set_title(
        f"SWED 事件提取示意 · test.csv · {d['label']} · "
        f"{d['n']} 点 / {d['duration']:.2f}s / dt={d['dt']*1e6:.0f}µs · "
        f"事件 {len(events)}（level/spike/dip）",
        fontsize=11, color="#e8eaf0", pad=12,
    )
    ax.tick_params(colors="#c8ccd4")
    for spine in ax.spines.values():
        spine.set_color("#333842")
    ax.grid(True, axis="y", color="#262b34", lw=0.5)

    # 图例
    from matplotlib.lines import Line2D
    legend_el = [
        Line2D([0], [0], color="#ffb74d", lw=2.2, label="level 段均值 (判据A 均值线)"),
        Line2D([0], [0], marker="v", color="#ff5252", lw=0, ms=7, label="spike 峰值 (判据B 极值线)"),
        Line2D([0], [0], marker="v", color="#69f0ae", lw=0, ms=7, label="dip (下陷)"),
        Rectangle((0, 0), 1, 1, color="#1d3a5f", label="事件活跃区(放大)"),
        Rectangle((0, 0), 1, 1, color="#181b22", label="平稳区(压缩)"),
    ]
    ax.legend(handles=legend_el, loc="upper right", fontsize=8,
              facecolor="#171a21", edgecolor="#333842", labelcolor="#c8ccd4")

    # 活跃区分隔虚线 + 真实时间范围标注
    for s, e, p0, p1, kind in seg_map:
        if kind == "active":
            ax.axvline(p0 / total, color="#3a4252", lw=0.5, ls=":", zorder=1)
            ax.axvline(p1 / total, color="#3a4252", lw=0.5, ls=":", zorder=1)
            ax.text((p0 / total + p1 / total) / 2, d["vmax"] * 1.02,
                    f"{s:.3f}~{e:.3f}s", ha="center", va="top",
                    fontsize=6.5, color="#8aa0c0", zorder=6)

    plt.tight_layout()
    out = os.path.join(HERE, "swed_waveform.png")
    fig.savefig(out, facecolor=fig.get_facecolor())
    print("saved", out)


if __name__ == "__main__":
    main()
