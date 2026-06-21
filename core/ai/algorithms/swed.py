"""SWED（Sliding-Window Event Detection）事件检测算法。

按 docs/user/algorithm/SlidingWindowEventDetection.md 实现：
    增量滑动均值(O(1)) + 单调双端队列极值(摊还O(1)) + 双判据状态机 + 睡眠门限闸门。

核心特性（双线驱动，均值线与极值线平权、各自独立开关事件）：
    均值线（level）—— 判据 A：窗口均值相对 BASE 突变 ≥ theta_avg_in（电平台阶，近 PELT）；
                      退出：均值回落到事件活跃水平 (1-theta_end) 以下或睡眠（与极值解耦）。
    极值线（spike/dip）—— 判据 B：窗口极值偏离均值 ≥ theta_ext（突发尖峰，近 STA-LTA）；
                      退出：极值平静 (up<theta_ext and dn<theta_ext) 持续 calm_hold 窗或睡眠。
    两线各开各的事件、各关各的，互不绑架——故一段 RX 台阶（均值不回落）能被 level 线完整
    覆盖的同时，台阶内部的尖峰簇仍被 spike 线逐个切出（解决宽窗下尖峰被台阶吞并的问题）。
    两线事件按 start 排序合并进同一 events 列表，靠 type 字段区分。
    睡眠门限 sleep_floor —— floor=sleep_floor 单一物理变量；< floor 视为睡眠态，
                            免疫所有判据（µA 级抖动不误触发）。

纯 Python 标量主循环（仅 dt 推断借用 numpy），零额外依赖；禁 import Qt。
"""
from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Any

from core.ai.algorithms.base import (
    Event,
    EventResult,
    Signal,
    WaveformAlgorithm,
)
from core.ai.algorithms.registry import register

_EPS = 1e-9


@dataclass
class SwedParams:
    """SWED 参数（默认值即推荐值，见规范 §9）。"""

    T: float = 2e-4
    theta_avg_in: float = 0.20
    theta_avg_out: float = 0.10
    theta_ext: float = 0.35
    theta_end: float = 0.50
    sleep_floor: float = 0.4
    merge_gap_s: float = 2e-4


@register
class SwedAlgorithm(WaveformAlgorithm):
    name = "swed"
    kind = "event"
    params_cls = SwedParams

    def run(self, signal: Signal, params: SwedParams | None = None) -> EventResult:
        params = params or SwedParams()
        times = signal.times
        v = signal.values
        n = len(v)
        if n < 4:
            return EventResult(events=[], info={})

        dt = signal.dt
        if dt <= 0.0:
            return EventResult(events=[], info={})
        W = max(1, int(round(params.T / dt)))
        if W >= n:
            W = n // 2

        floor = params.sleep_floor
        sleep_floor = params.sleep_floor
        theta_avg_in = params.theta_avg_in
        theta_ext = params.theta_ext
        theta_end = params.theta_end

        S = sum(v[:W])
        dmax: collections.deque[int] = collections.deque()
        dmin: collections.deque[int] = collections.deque()
        for i in range(W):
            while dmax and v[dmax[-1]] <= v[i]:
                dmax.pop()
            dmax.append(i)
            while dmin and v[dmin[-1]] >= v[i]:
                dmin.pop()
            dmin.append(i)

        BASE = S / W
        R = 1 << 16
        calm_hold = max(1, W // 2)

        lvl_state = "IDLE"
        lvl_cur: dict[str, Any] | None = None
        lvl_cd = 0
        spk_state = "IDLE"
        spk_cur: dict[str, Any] | None = None
        spk_calm = 0
        spk_cd = 0

        raw: list[dict[str, Any]] = []
        n_windows = n - W + 1

        for win in range(n_windows):
            if win > 0:
                out_idx = win - 1
                in_idx = win + W - 1
                S += v[in_idx] - v[out_idx]
                while dmax and v[dmax[-1]] <= v[in_idx]:
                    dmax.pop()
                dmax.append(in_idx)
                while dmin and v[dmin[-1]] >= v[in_idx]:
                    dmin.pop()
                dmin.append(in_idx)
                while dmax and dmax[0] < win:
                    dmax.popleft()
                while dmin and dmin[0] < win:
                    dmin.popleft()

            if win % R == 0 and win > 0:
                S = sum(v[win : win + W])

            AVG = S / W
            Mx = v[dmax[0]]
            Mn = v[dmin[0]]

            denom_base = max(abs(BASE), floor, _EPS)
            denom_avg = max(abs(AVG), floor, _EPS)
            asleep = AVG < sleep_floor
            active = not asleep and (Mx >= floor or AVG >= floor)
            hitA = active and abs(AVG - BASE) / denom_base >= theta_avg_in
            up = (Mx - AVG) / denom_avg
            dn = (AVG - Mn) / denom_avg
            hitB_up = not asleep and up >= theta_ext and Mx >= floor
            hitB_dn = not asleep and dn >= theta_ext and Mx >= floor
            ext_calm = up < theta_ext and dn < theta_ext

            # ---- 均值线（level）：进入靠 hitA，退出靠均值回落/睡眠（与极值解耦）----
            if lvl_state == "IDLE":
                if lvl_cd == 0 and hitA:
                    lvl_cur = {
                        "i0": win,
                        "start": times[win],
                        "type": "level",
                        "trigger": "A",
                        "_sum": 0.0,
                        "_cnt": 0,
                        "peak": Mx,
                        "min": Mn,
                        "_emax": max(AVG, BASE),
                    }
                    lvl_state = "IN_EVENT"
            if lvl_state == "IN_EVENT":
                lvl_cur["_sum"] += AVG
                lvl_cur["_cnt"] += 1
                lvl_cur["peak"] = max(lvl_cur["peak"], Mx)
                lvl_cur["min"] = min(lvl_cur["min"], Mn)
                lvl_cur["_emax"] = max(lvl_cur["_emax"], AVG)
                ev_ref = max(lvl_cur["_emax"], BASE, floor)
                fell_back = AVG <= ev_ref * (1.0 - theta_end)
                if fell_back or asleep:
                    lvl_cur["i1"] = win
                    lvl_cur["end"] = times[win]
                    lvl_cur["avg"] = lvl_cur["_sum"] / max(lvl_cur["_cnt"], 1)
                    lvl_cur["duration_ms"] = (
                        lvl_cur["end"] - lvl_cur["start"]
                    ) * 1e3
                    raw.append(lvl_cur)
                    BASE = AVG
                    lvl_state = "IDLE"
                    lvl_cd = W
                    lvl_cur = None
            if lvl_cd > 0:
                lvl_cd -= 1

            # ---- 极值线（spike/dip）：进入靠 hitB，退出靠极值平静持续（与均值解耦）----
            if spk_state == "IDLE":
                if spk_cd == 0 and (hitB_up or hitB_dn):
                    spk_cur = {
                        "i0": win,
                        "start": times[win],
                        "type": "spike" if hitB_up else "dip",
                        "trigger": "B",
                        "_sum": 0.0,
                        "_cnt": 0,
                        "peak": Mx,
                        "min": Mn,
                        "_emax": max(AVG, BASE),
                    }
                    spk_state = "IN_EVENT"
                    spk_calm = 0
            if spk_state == "IN_EVENT":
                spk_cur["_sum"] += AVG
                spk_cur["_cnt"] += 1
                spk_cur["peak"] = max(spk_cur["peak"], Mx)
                spk_cur["min"] = min(spk_cur["min"], Mn)
                spk_cur["_emax"] = max(spk_cur["_emax"], AVG)
                if ext_calm:
                    spk_calm += 1
                else:
                    spk_calm = 0
                if spk_calm >= calm_hold or asleep:
                    spk_cur["i1"] = win
                    spk_cur["end"] = times[win]
                    spk_cur["avg"] = spk_cur["_sum"] / max(spk_cur["_cnt"], 1)
                    spk_cur["duration_ms"] = (
                        spk_cur["end"] - spk_cur["start"]
                    ) * 1e3
                    raw.append(spk_cur)
                    spk_state = "IDLE"
                    spk_cd = W
                    spk_cur = None
            if spk_cd > 0:
                spk_cd -= 1

        for tail in (lvl_cur, spk_cur):
            if tail is not None:
                tail["i1"] = n - 1
                tail["end"] = times[-1]
                tail["avg"] = tail["_sum"] / max(tail["_cnt"], 1)
                tail["duration_ms"] = (tail["end"] - tail["start"]) * 1e3
                raw.append(tail)

        raw.sort(key=lambda e: e["start"])
        merged = self._merge(raw, params.merge_gap_s)

        events = [
            Event(
                start=e["start"],
                end=e["end"],
                type=e["type"],
                trigger=e.get("trigger", ""),
                avg=e["avg"],
                peak=e["peak"],
                minimum=e["min"],
                duration_ms=e["duration_ms"],
                i0=e.get("i0", -1),
                i1=e.get("i1", -1),
            )
            for e in merged
        ]
        info = {
            "algorithm": self.name,
            "dt": dt,
            "W": W,
            "floor": floor,
            "sleep_floor": sleep_floor,
            "raw_events": len(raw),
        }
        return EventResult(events=events, info=info)

    @staticmethod
    def _merge(raw: list[dict], gap: float) -> list[dict]:
        merged: list[dict] = []
        for e in raw:
            if (
                merged
                and e["type"] in ("spike", "dip")
                and merged[-1]["type"] in ("spike", "dip")
                and (e["start"] - merged[-1]["end"]) <= gap
            ):
                m = merged[-1]
                m["end"] = e["end"]
                m["i1"] = e.get("i1", m.get("i1", -1))
                m["peak"] = max(m["peak"], e["peak"])
                m["min"] = min(m["min"], e["min"])
                m["avg"] = (m["avg"] + e["avg"]) / 2.0
                m["duration_ms"] = (m["end"] - m["start"]) * 1e3
            else:
                merged.append(e)
        for e in merged:
            for k in ("_sum", "_cnt", "_emax"):
                e.pop(k, None)
        return merged
