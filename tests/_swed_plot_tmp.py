import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instruments.power.keysight.n6705c_datalog_process import import_csv_file
from core.ai.algorithms import Signal, get

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.csv")


def main():
    res = import_csv_file(CSV)
    all_data = res[0]
    label = list(all_data.keys())[0]
    ch = all_data[label]
    times = list(ch["time"])
    values = list(ch["values"])
    sig = Signal(times=times, values=values)

    result = get("swed").run(sig)
    events = [e.to_dict() for e in result.events]

    n = len(values)
    step = max(1, n // 4000)
    ds_t = times[::step]
    ds_v = values[::step]

    out = {
        "label": label,
        "n": n,
        "dt": sig.dt,
        "duration": times[-1] - times[0],
        "vmin": min(values),
        "vmax": max(values),
        "vavg": sum(values) / n,
        "info": result.info,
        "events": events,
        "ds_t": [round(x, 6) for x in ds_t],
        "ds_v": [round(x, 6) for x in ds_v],
    }
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_swed_plot_data.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f)

    print("events =", len(events))
    types = {}
    for e in events:
        types[e["type"]] = types.get(e["type"], 0) + 1
    print("types =", types)
    print("info =", result.info)
    for i, e in enumerate(events, 1):
        print(f"#{i:>2} {e['type']:<5} trig={e.get('trigger','')} "
              f"[{e['start']:.6f}~{e['end']:.6f}]s dur={e['duration_ms']:.3f}ms "
              f"peak={e['peak']:.4f} avg={e['avg']:.4f} min={e['minimum']:.4f}")
    print("wrote", dst)


if __name__ == "__main__":
    main()
