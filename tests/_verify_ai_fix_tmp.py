import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instruments.power.keysight.n6705c_datalog_process import (
    import_csv_file, parse_channel_label, unit_for_label, base_unit_for_label,
)
from core.ai.providers.waveform_provider import build_digest
from core.ai.prompt_manager import format_waveform_digest

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_maker_export.csv")

print("=== label parse ===")
for lbl in ["F1-A-I1", "CH1 I", "F1-A CH2 V", "B CH3 P", "A-V2"]:
    print(f"{lbl!r:18} -> parse={parse_channel_label(lbl)}  unit={unit_for_label(lbl)!r}  base={base_unit_for_label(lbl)!r}")

print("\n=== import csv ===")
res = import_csv_file(CSV)
all_data = res[0]
print("channels:", list(all_data.keys()))

digest = build_digest(all_data, max_points=1500, anomaly_sigma=3.0)
for s in digest.stats:
    print(f"\nchannel={s.label} unit={s.unit}")
    print(f"  min={s.minimum} max={s.maximum} avg={s.average} pp={s.peak_to_peak} std={s.std}")
    print(f"  超阈点列表(anomalies)={len(s.anomalies)}  尖峰事件簇(spike_events)={len(s.spike_events)}")
    for i, e in enumerate(s.spike_events, 1):
        print(f"    事件{i}: [{e['start']}~{e['end']}]s 峰值={e['peak_value']}{s.unit} "
              f"({e['type']}) 簇内点={e['point_count']} 超阈总={e['over_threshold_total']}")

print("\n=== prompt text ===")
print(format_waveform_digest(digest, include_downsampled=False))
