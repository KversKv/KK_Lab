"""波形可见窗口切片冒烟测试（F1.7 / D14）。

验证 core/ai/providers/waveform_provider 的快速切片与窗口摘要：
  - slice_channel_fast 等步长（算术 O(1)）切片正确性；
  - 等步长 与 非等步长（bisect）路径结果一致；
  - build_window_digest 仅反映窗口内数据，且 window 字段正确；
  - marker_segment_stats 时长与区间统计；
  - 边界：窗口外 / 反向 / 空数据。

运行：
  .\\.venv\\Scripts\\python.exe scripts\\waveform_window_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ai.providers.waveform_provider import (  # noqa: E402
    build_window_digest,
    marker_segment_stats,
    slice_channel_fast,
)


def _uniform_data(n: int, period: float = 0.02):
    times = [i * period for i in range(n)]
    values = [float(i) for i in range(n)]
    return times, values


def test_slice_uniform_basic():
    times, values = _uniform_data(1000, period=0.02)
    sel_t, sel_v = slice_channel_fast(times, values, 1.0, 4.0)
    assert sel_t[0] >= 1.0 and sel_t[-1] <= 4.0, (sel_t[0], sel_t[-1])
    assert all(1.0 <= t <= 4.0 for t in sel_t)
    assert len(sel_t) == len(sel_v)
    naive = [(t, v) for t, v in zip(times, values) if 1.0 <= t <= 4.0]
    assert list(zip(sel_t, sel_v)) == naive
    print(f"  ok slice_uniform_basic -> {len(sel_v)} pts")


def test_uniform_vs_bisect_consistency():
    times, values = _uniform_data(500, period=0.05)
    jitter = [t + (1e-9 if i % 2 else 0.0) for i, t in enumerate(times)]
    a = slice_channel_fast(times, values, 3.3, 7.7)
    b = slice_channel_fast(jitter, values, 3.3, 7.7)
    assert a[1] == b[1], (len(a[1]), len(b[1]))
    print(f"  ok uniform_vs_bisect_consistency -> {len(a[1])} pts")


def test_edge_cases():
    times, values = _uniform_data(100, period=0.1)
    assert slice_channel_fast(times, values, 50.0, 60.0) == ([], [])
    fwd = slice_channel_fast(times, values, 2.0, 5.0)
    rev = slice_channel_fast(times, values, 5.0, 2.0)
    assert fwd == rev
    assert slice_channel_fast([], [], 0.0, 1.0) == ([], [])
    print("  ok edge_cases")


def test_build_window_digest():
    times, values = _uniform_data(2000, period=0.005)
    data = {"CH1 I": {"time": times, "values": values}}
    digest = build_window_digest(data, 1.0, 3.0)
    assert digest.window == {"x0": 1.0, "x1": 3.0, "full": False}, digest.window
    assert digest.stats, "window digest 应含统计"
    stat = digest.stats[0]
    assert stat.point_count < len(values), (stat.point_count, len(values))
    print(f"  ok build_window_digest -> {stat.point_count} pts, unit={stat.unit}")


def test_window_no_data():
    times, values = _uniform_data(100, period=0.1)
    data = {"CH1 I": {"time": times, "values": values}}
    digest = build_window_digest(data, 100.0, 200.0)
    assert not digest.stats
    assert digest.window == {"x0": 100.0, "x1": 200.0, "full": False}
    print("  ok window_no_data")


def test_marker_segment_stats():
    times, values = _uniform_data(1000, period=0.01)
    data = {"CH1 I": {"time": times, "values": values}}
    seg = marker_segment_stats(data, 2.0, 5.0)
    assert seg is not None
    assert abs(seg["duration_s"] - 3.0) < 1e-6, seg["duration_s"]
    assert seg["per_channel"], "marker 区间应有通道统计"
    ch = seg["per_channel"][0]
    assert ch["minimum"] <= ch["average"] <= ch["maximum"]
    assert marker_segment_stats(data, None, 5.0) is None
    print(f"  ok marker_segment_stats -> dur={seg['duration_s']}s, "
          f"avg={ch['average']}{ch['unit']}")


def main() -> int:
    tests = [
        test_slice_uniform_basic,
        test_uniform_vs_bisect_consistency,
        test_edge_cases,
        test_build_window_digest,
        test_window_no_data,
        test_marker_segment_stats,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL {t.__name__}: {exc}")
    if failed:
        print(f"\n{failed}/{len(tests)} 测试失败")
        return 1
    print(f"\n全部 {len(tests)} 项通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
