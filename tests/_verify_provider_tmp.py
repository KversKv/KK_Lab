"""端到端验证 waveform_provider 的 §9 事件感知双引擎实现（基于 tests/test.csv）。

校验：
  1) event_aware=False 与改造前一致（向后兼容）；
  2) event_aware=True 全局提取 4 浪涌 + 2 涌流 + 平台段（§9.7）；
  3) analyze_window_segments 对 E04 窗口 PELT drill-down 暴露三次 RX（§9.8）；
  4) to_dict() 可 JSON 序列化 + density_map 标注非均匀采样。
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.providers import waveform_provider as wp

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.csv")


def load():
    arr = np.genfromtxt(CSV, delimiter=",", skip_header=1)
    t = arr[:, 0].tolist()
    # Datalog 内存格式 = 真实值 × 1000（mA），与 provider 约定一致
    v = (arr[:, 1] * 1000.0).tolist()
    return {"F1-A-I1": {"time": t, "values": v}}


def main():
    all_data = load()
    n = len(all_data["F1-A-I1"]["values"])
    print(f"== 载入 test.csv：{n} 点 ==\n")

    # --- 1) 向后兼容：event_aware=False ---
    t0 = time.perf_counter()
    d_legacy = wp.build_digest(all_data, event_aware=False)
    dt_legacy = (time.perf_counter() - t0) * 1000
    s0 = d_legacy.stats[0]
    print(f"[1] 向后兼容 event_aware=False  ({dt_legacy:.0f} ms)")
    print(f"    unit={s0.unit} min={s0.minimum} max={s0.maximum} avg={s0.average}")
    print(f"    spike_events={len(s0.spike_events)} steady_segments={len(s0.steady_segments)}")
    print(f"    segments(应为空)={len(s0.segments)} density_map(应为空)={len(s0.density_map)}")
    assert s0.segments == [] and s0.density_map == [], "兼容模式不应产出新字段"
    print("    -> 兼容 OK\n")

    # --- 2) 事件感知全局 ---
    t0 = time.perf_counter()
    d = wp.build_digest(all_data, event_aware=True)
    dt_ea = (time.perf_counter() - t0) * 1000
    s = d.stats[0]
    print(f"[2] 事件感知 event_aware=True  ({dt_ea:.0f} ms)")
    print(f"    note={d.note}")
    print(f"    segments={len(s.segments)}  density_map={len(s.density_map)}")
    print("    --- segments (label/start~end/mean/peak/width_ms/charge_uAh) ---")
    for seg in s.segments:
        print(
            f"    [{seg['label']:7s}] {seg['start']:.4f}~{seg['end']:.4f}s "
            f"mean={seg['mean']:7.3f} peak={seg['peak']:7.3f} "
            f"w={seg['width_ms']:7.3f}ms q={seg['charge_uAh']:.4f}uAh"
        )
    print(f"    --- density_map ---")
    for dm in s.density_map[:8]:
        print(f"    {dm}")
    print()

    # --- 3) drill-down PELT @ E04 三次 RX ---
    print("[3] drill-down PELT @ E04 (0.4154~0.4169s) —— 三次 RX")
    t0 = time.perf_counter()
    win = wp.analyze_window_segments(all_data, "F1-A-I1", 0.4154, 0.4169)
    dt_pelt = (time.perf_counter() - t0) * 1000
    print(f"    engine={win.get('engine')}  segments={len(win['segments'])}  ({dt_pelt:.1f} ms)")
    rx = [g for g in win["segments"] if g["label"] in ("plateau", "ramp")]
    for g in win["segments"]:
        print(
            f"    [{g['label']:7s}] {g['start']:.5f}~{g['end']:.5f}s "
            f"mean={g['mean']:6.3f} peak={g['peak']:6.3f} "
            f"w={g['width_ms']:.4f}ms q={g['charge_uAh']:.4f}uAh pts={g['point_count']}"
        )
    print(f"    -> 中幅平台/缓变段(候选RX) 数量={len(rx)}\n")

    # --- 4) JSON 序列化 ---
    js = json.dumps(d.to_dict(), ensure_ascii=False)
    print(f"[4] to_dict() JSON 序列化 OK，长度={len(js)} 字符")
    win_js = json.dumps(win, ensure_ascii=False)
    print(f"    window JSON OK，长度={len(win_js)} 字符")


if __name__ == "__main__":
    main()
