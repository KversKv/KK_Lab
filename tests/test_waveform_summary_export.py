#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""波形摘要导出（平直线段示意图 + 阶段汇总表）渲染冒烟测试。

合成电流波形 → 真实 build_digest(event_aware=True) → _build_summary_stages
→ _render_waveform_summary_image → tests/waveform_summary_demo.png。
"""
import os
import sys
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from core.ai.providers.waveform_provider import build_digest
from ui.pages.n6705c_power_analyzer.n6705c_datalog_ui import (
    _build_summary_stages,
    _render_waveform_summary_image,
    _summary_fmt_time,
)


def _synth_current():
    """内存值语义 mA：基线 5mA + 噪声；两段平台（50mA / 120mA）；一个窄尖峰。"""
    random.seed(7)
    dt = 1e-3
    times = []
    values = []
    t = 0.0
    for i in range(4000):
        if 1000 <= i < 1600:      # 平台 50 mA
            v = 50.0
        elif 2200 <= i < 2300:    # 窄尖峰 200 mA
            v = 200.0
        elif 2800 <= i < 3600:    # 平台 120 mA
            v = 120.0
        else:                     # 基线 5 mA
            v = 5.0
        values.append(v + random.uniform(-0.4, 0.4))
        times.append(t)
        t += dt
    return times, values


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    times, values = _synth_current()
    digest = build_digest(
        {"CH1 I": {"time": times, "values": values}},
        event_aware=True, algo="stalta",
    )
    assert digest.stats, "digest 无统计结果"
    stat = digest.stats[0]
    print(f"unit={stat.unit} avg={stat.average} segments={len(stat.segments)}")

    stages = _build_summary_stages(times, values, stat)
    assert stages, "阶段构建为空"
    names = {"baseline": "基线", "plateau": "平台", "spike": "尖峰",
             "valley": "低谷", "ramp": "缓变"}
    print(f"stages={len(stages)}")
    for i, st in enumerate(stages):
        print(f"  S{i + 1} [{names.get(st['label'], st['label'])}] "
              f"{st['start']:.3f}~{st['end']:.3f}s "
              f"dur={_summary_fmt_time(st['end'] - st['start'])} "
              f"avg={st['mean']:.4g} {stat.unit}")

    means = [s["mean"] for s in stages]
    section = {
        "label": stat.label, "unit": stat.unit, "is_current": True,
        "t0": times[0], "t1": times[-1],
        "vmin": min(means), "vmax": max(means), "stages": stages,
    }
    pixmap = _render_waveform_summary_image([section], 960)
    assert not pixmap.isNull(), "渲染 pixmap 为空"
    out = os.path.join(os.path.dirname(__file__), "waveform_summary_demo.png")
    assert pixmap.save(out), "PNG 保存失败"
    print(f"saved: {out} ({pixmap.width()}x{pixmap.height()})")


if __name__ == "__main__":
    main()
