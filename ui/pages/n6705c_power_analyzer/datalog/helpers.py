#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from bisect import bisect_left, bisect_right
from instruments.power.keysight.n6705c_datalog_process import parse_channel_label, unit_for_label
from ui.pages.n6705c_power_analyzer.n6705c_settings_dialog import waveform_summary_params
from resource_path import get_resource_base

def _make_svg_icon(svg_file, color="#dfe8ff", size=18, zoom=1.0):
    """加载 resources/pages/n6705c_power_analyzer_SVGs 下的 SVG 并渲染为 QIcon。

    zoom > 1 时将 viewBox 放大 zoom 倍后居中裁剪，削掉 SVG 内建留白，
    使可见笔画在小尺寸按钮（如左侧 rail 图标）中填满绘制区。
    """
    svg_path = os.path.join(get_resource_base(), "resources", "pages", "n6705c_power_analyzer_SVGs", svg_file)
    with open(svg_path, "r", encoding="utf-8") as f:
        svg_data = f.read().replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    if zoom != 1.0:
        offset = (size - size * zoom) / 2.0
        painter.translate(offset, offset)
        painter.scale(zoom, zoom)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


CHANNEL_COLORS = [
    "#d4a514",
    "#18b67a",
    "#2f6fed",
    "#d14b72",
    "#00bcd4",
    "#ff9800",
    "#ab47bc",
    "#8bc34a",
]


CHANNEL_LABEL_COLORS = [
    "#ffe566",
    "#7fffcf",
    "#8cb8ff",
    "#ff9ab8",
    "#7ef5ff",
    "#ffc966",
    "#dda0ff",
    "#c8ff7e",
]


VOLTAGE_COLORS = [
    "#a88010",
    "#10946a",
    "#2558ba",
    "#a83a5a",
    "#009aad",
    "#cc7a00",
    "#883a96",
    "#6e9c3a",
]


POWER_COLORS = [
    "#e6a33c",
    "#b05ce6",
    "#3cb0e6",
    "#e63c6e",
    "#6ee63c",
    "#e6ce3c",
    "#3c6ee6",
    "#e63cb0",
]


EXTRA_MARKER_COLORS = [
    "#e6553c", "#3ce6b0",
    "#c73ce6", "#e6c73c",
    "#3c8be6", "#e63c8b",
    "#5ce63c", "#e63cd4",
    "#3ce6e6", "#b03ce6",
    "#e69a3c", "#3c4ae6",
]


_BAND_CEILING = 0.88


# 成对 Marker 区间注释（Δt/avg 文本框）：默认字号与可选字号
_ANN_DEFAULT_FONT = 10


_ANN_FONT_SIZES = (8, 10, 12, 14, 16, 18, 20, 24)


# Measurement 表 Avg 列高亮：琥珀金前景 + 提亮背景，与斑马纹行区分
_MEAS_AVG_FG = "#ffd166"


_MEAS_AVG_BG = "#1c2b4f"


# ---- 波形摘要导出（平直线段示意图 + 阶段汇总表，算法与 AI 摘要同源）----
_SUMMARY_STAGE_COLORS = {
    "baseline": "#64748b",
    "plateau": "#38bdf8",
    "spike": "#f87171",
    "valley": "#34d399",
    "ramp": "#eab308",
}


_SUMMARY_STAGE_NAMES = {
    "baseline": "基线",
    "plateau": "平台",
    "spike": "尖峰",
    "valley": "低谷",
    "ramp": "缓变",
}


def _parse_ch_label(label):
    return parse_channel_label(label)


def _display_label(key):
    raw = key.strip()
    file_prefix = ""
    fm = re.match(r'^(F\d+)-(.*)', raw)
    if fm:
        file_prefix = fm.group(1)
        raw = fm.group(2).strip()
    ch_num, mtype, is_b = _parse_ch_label(raw)
    if ch_num is None:
        return raw
    slot = "B" if is_b else "A"
    if file_prefix:
        return f"{file_prefix}-{slot}-{mtype}{ch_num}"
    return f"{slot}-{mtype}{ch_num}"


def _color_for_label(label):
    ch_num, mtype, is_b = _parse_ch_label(label)
    if ch_num is None:
        return CHANNEL_COLORS[0]
    base_idx = (ch_num - 1) + (4 if is_b else 0)
    if mtype == "V":
        return VOLTAGE_COLORS[base_idx % len(VOLTAGE_COLORS)]
    if mtype == "P":
        return POWER_COLORS[base_idx % len(POWER_COLORS)]
    return CHANNEL_COLORS[base_idx % len(CHANNEL_COLORS)]


def _sort_key_for_label(label):
    raw = label.strip()
    file_order = 0
    fm = re.match(r'^F(\d+)-(.*)', raw)
    if fm:
        file_order = int(fm.group(1))
    ch_num, mtype, is_b = _parse_ch_label(label)
    unit_order = 1 if is_b else 0
    ch_order = ch_num if ch_num else 0
    type_order = {"V": 0, "I": 1, "P": 2}.get(mtype, 3)
    return (file_order, unit_order, ch_order, type_order)


def _parse_value_with_unit(text, base_unit=None):
    text = text.strip()
    m = re.match(r'^([+-]?\d*\.?\d+)\s*([a-zA-Z\u00B5\u03BC]*)\s*$', text)
    if not m:
        try:
            return float(text)
        except ValueError:
            return None
    num = float(m.group(1))
    raw_unit = m.group(2).strip()

    if not raw_unit and base_unit:
        raw_unit = base_unit

    unit = raw_unit.lower().replace('\u00b5', 'u').replace('\u03bc', 'u')

    if unit in ("ua", "uv", "uw", "u"):
        return num * 1e-3
    elif unit in ("ma", "mv", "mw", "m"):
        return num
    elif unit in ("a", "v", "w"):
        return num * 1e3
    return num


def _unit_for_label(label):
    unit = unit_for_label(label)
    return unit or "mA"


def _format_value(value_mA):
    abs_v = abs(value_mA)
    if abs_v >= 1000:
        return f"{value_mA / 1000:.3f} A"
    elif abs_v >= 1:
        return f"{value_mA:.2f} mA"
    elif abs_v > 0:
        return f"{value_mA * 1000:.2f} \u00B5A"
    else:
        return f"0.00 mA"


def _format_time(seconds):
    abs_val = abs(seconds)
    if abs_val == 0:
        return "0 s"
    if abs_val < 1e-3:
        return f"{seconds * 1e6:.3f} us"
    if abs_val < 1.0:
        return f"{seconds * 1e3:.3f} ms"
    return f"{seconds:.6f} s"


def _auto_format(value, base_unit):
    UNIT_MAP = {
        "mA": ("\u00B5A", "mA", "A"),
        "mV": ("\u00B5V", "mV", "V"),
        "mW": ("\u00B5W", "mW", "W"),
        "mAh": ("\u00B5Ah", "mAh", "Ah"),
        "mWh": ("\u00B5Wh", "mWh", "Wh"),
        "C": ("mC", "C", "kC"),
        "J": ("mJ", "J", "kJ"),
    }
    units = UNIT_MAP.get(base_unit)
    if not units:
        return f"{value:.4f} {base_unit}"

    abs_v = abs(value)
    if base_unit in ("C", "J"):
        if abs_v < 1:
            return f"{value * 1000:.4f} {units[0]}"
        elif abs_v >= 1000:
            return f"{value / 1000:.4f} {units[2]}"
        else:
            return f"{value:.4f} {units[1]}"
    else:
        if abs_v >= 1000:
            return f"{value / 1000:.4f} {units[2]}"
        elif abs_v >= 1:
            return f"{value:.4f} {units[1]}"
        elif abs_v > 0:
            return f"{value * 1000:.4f} {units[0]}"
        else:
            return f"0.0000 {units[1]}"


def _summary_fmt_time(seconds):
    """摘要图时间/时长紧凑格式化（区别于 _format_time 的 6 位小数）。"""
    abs_v = abs(seconds)
    if abs_v == 0:
        return "0 s"
    if abs_v >= 1.0:
        return f"{seconds:.3f} s"
    if abs_v >= 1e-3:
        return f"{seconds * 1e3:.3f} ms"
    if abs_v >= 1e-6:
        return f"{seconds * 1e6:.2f} µs"
    return f"{seconds * 1e9:.1f} ns"


def _summary_unit_factor(unit):
    """AI 摘要展示单位 → 内存值（mA/mV/mW）换算到展示值的倍率（与 _pick_scale 互逆）。"""
    if not unit:
        return 1.0
    base = unit[-1]
    if base not in "AVW":
        return 1.0
    threshold = {"m": 1e-3, "u": 1e-6, "n": 1e-9}.get(unit[0], 1.0)
    return 1.0 / (1000.0 * threshold)


def _build_summary_stages(times, values, stat, max_stages=None):
    """把单通道波形压成全程覆盖的平直线段阶段序列。

    分段算法与 AI 摘要同源（core.ai PELT 均值变点 + classify_segment 形态标注）：
    先 LTTB 降采样再跑 PELT 变点（PELT 仅限 max_n 内），
    段均值用原始数据在该时间窗内的真实均值（换算 stat.unit 展示单位）。
    max_stages / LTTB 阈值 / PELT max_n 默认取设置对话框 Waveform Summary 页参数。
    """
    if not times or not values:
        return []
    from core.ai.algorithms import detect_change_points, lttb_downsample
    from core.ai.providers.waveform_provider import segment_features

    ws_params = waveform_summary_params()
    if max_stages is None:
        max_stages = ws_params["max_stages"]
    lttb_threshold = ws_params["lttb_threshold"]
    pelt_max_n = ws_params["pelt_max_n"]

    factor = _summary_unit_factor(getattr(stat, "unit", ""))
    fallback_mean = getattr(stat, "average", 0.0)

    def _window_mean(a, b):
        i0 = bisect_left(times, a)
        i1 = bisect_right(times, b)
        if i1 <= i0:
            return fallback_mean
        return (sum(values[i0:i1]) / (i1 - i0)) * factor

    if len(values) > lttb_threshold:
        ds_t, ds_v = lttb_downsample(list(times), list(values), lttb_threshold)
    else:
        ds_t, ds_v = list(times), list(values)
    cps = [c for c in detect_change_points(ds_v, max_n=pelt_max_n) if 0 < c < len(ds_v) - 1]
    if not cps:
        return [{
            "start": float(times[0]), "end": float(times[-1]),
            "mean": _window_mean(times[0], times[-1]), "label": "baseline",
        }]
    bounds = [0] + cps + [len(ds_v) - 1]
    ranges = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
    stages = []
    for seg in segment_features(ds_t, ds_v, ranges, factor=factor, max_report=max_stages):
        s = float(seg.get("start", times[0]))
        e = float(seg.get("end", times[-1]))
        if e <= s:
            continue
        stages.append({
            "start": s, "end": e,
            "mean": _window_mean(s, e),
            "label": str(seg.get("label", "ramp")),
        })
    # 静息层级命名后处理：最低电平带内的段归为基线（数值不变，仅阶段命名）
    if stages:
        means = [st["mean"] for st in stages]
        lo, hi = min(means), max(means)
        band = max((hi - lo) * 0.08, abs(fallback_mean) * 0.02, 1e-12)
        for st in stages:
            if st["mean"] <= lo + band:
                st["label"] = "baseline"
    return stages


def _render_waveform_summary_image(sections, width):
    """渲染波形摘要图：每通道一段平直线段示意图（标注 S1..Sn 阶段）+ 阶段汇总表。"""
    pad = 20
    title_h = 46
    sec_title_h = 24
    annot_h = 24
    plot_h = 140
    axis_h = 20
    head_h = 26
    row_h = 22
    sec_gap = 20

    height = pad + title_h
    for sec in sections:
        height += (sec_title_h + annot_h + plot_h + axis_h + head_h
                   + row_h * len(sec["stages"]) + sec_gap)
    height += pad - sec_gap

    text_color = QColor("#dfe8ff")
    dim_color = QColor("#8ea6cf")
    title_color = QColor("#e6eeff")
    grid_color = QColor("#12203f")
    frame_color = QColor("#1a2b52")
    header_bg = QColor("#0f1a33")
    zebra_bg = QColor("#0a1226")

    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#020817"))
    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)

        title_font = QFont("Microsoft YaHei", 13)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(title_color)
        painter.drawText(pad, pad, width - 2 * pad, 24,
                         Qt.AlignLeft | Qt.AlignVCenter, "Datalog 波形摘要")
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.setPen(dim_color)
        painter.drawText(pad, pad + 26, width - 2 * pad, 16,
                         Qt.AlignLeft | Qt.AlignVCenter,
                         time.strftime("生成时间 %Y-%m-%d %H:%M:%S"))
        y = pad + title_h

        label_font = QFont("Microsoft YaHei", 10)
        label_font.setBold(True)
        axis_font = QFont("Microsoft YaHei", 8)
        cell_font = QFont("Microsoft YaHei", 9)
        header_font = QFont("Microsoft YaHei", 9)
        header_font.setBold(True)

        for sec in sections:
            t0, t1 = sec["t0"], sec["t1"]
            stages = sec["stages"]
            unit = sec.get("unit") or ""
            painter.setFont(label_font)
            painter.setPen(QColor("#c6d4f2"))
            title_text = f"{sec['label']}  ({unit})" if unit else sec["label"]
            painter.drawText(pad, y, width - 2 * pad, sec_title_h,
                             Qt.AlignLeft | Qt.AlignVCenter, title_text)
            y += sec_title_h

            plot_left = pad + 72
            plot_right = width - pad - 8
            plot_top = y + annot_h
            plot_bottom = plot_top + plot_h
            plot_w = max(plot_right - plot_left, 10)
            t_span = max(t1 - t0, 1e-12)

            vmin = sec["vmin"]
            vmax = sec["vmax"]
            v_span = vmax - vmin
            pad_v = v_span * 0.15 if v_span > 0 else max(abs(vmax) * 0.1, 1e-9)
            vmin = max(0.0, vmin - pad_v) if vmin >= 0 else vmin - pad_v
            vmax += pad_v
            v_span = vmax - vmin

            def _tx(tv):
                return plot_left + (tv - t0) / t_span * plot_w

            def _ty(vv):
                return plot_bottom - (vv - vmin) / v_span * plot_h

            painter.setFont(axis_font)
            for gi in range(5):
                gv = vmin + v_span * gi / 4.0
                gy = _ty(gv)
                painter.setPen(QPen(grid_color, 1))
                painter.drawLine(int(plot_left), int(gy), int(plot_right), int(gy))
                painter.setPen(dim_color)
                painter.drawText(0, int(gy) - 7, int(plot_left - 6), 14,
                                 Qt.AlignRight | Qt.AlignVCenter, f"{gv:.4g}")

            prev_y = None
            for idx, st in enumerate(stages):
                color = QColor(_SUMMARY_STAGE_COLORS.get(st["label"], "#94a3b8"))
                xa = _tx(st["start"])
                xb = _tx(st["end"])
                yv = _ty(st["mean"])
                if prev_y is not None and abs(prev_y - yv) > 0.5:
                    painter.setPen(QPen(QColor("#94a3b8"), 1, Qt.DashLine))
                    painter.drawLine(int(xa), int(prev_y), int(xa), int(yv))
                painter.setPen(QPen(color, 3))
                painter.drawLine(int(xa), int(yv), int(xb), int(yv))
                prev_y = yv
                # 阶段标注 S{idx+1}：相邻段两级交错防重叠
                ann_top = plot_top - 13 if idx % 2 == 0 else plot_top - 23
                painter.setPen(color)
                painter.drawText(int((xa + xb) / 2.0 - 40), int(ann_top), 80, 11,
                                 Qt.AlignHCenter | Qt.AlignVCenter, f"S{idx + 1}")

            painter.setPen(dim_color)
            painter.drawText(int(plot_left), int(plot_bottom + 3), 120, 14,
                             Qt.AlignLeft | Qt.AlignVCenter, _summary_fmt_time(t0))
            painter.drawText(int(plot_right - 120), int(plot_bottom + 3), 120, 14,
                             Qt.AlignRight | Qt.AlignVCenter, _summary_fmt_time(t1))
            painter.setPen(QPen(frame_color, 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(int(plot_left), int(plot_top), int(plot_w), int(plot_h))
            y = plot_bottom + axis_h

            if sec.get("is_current"):
                mean_header = f"平均电流 ({unit})" if unit else "平均电流"
            else:
                mean_header = f"平均值 ({unit})" if unit else "平均值"
            headers = ["阶段", "类型", "持续时长", mean_header]
            col_ratios = (0.14, 0.16, 0.32, 0.38)
            table_w = plot_right - plot_left
            col_x = [plot_left]
            for ratio in col_ratios:
                col_x.append(col_x[-1] + table_w * ratio)

            table_top = y
            painter.fillRect(int(plot_left), int(y), int(table_w), head_h, header_bg)
            painter.setFont(header_font)
            painter.setPen(QColor("#c6d4f2"))
            for ci, htext in enumerate(headers):
                painter.drawText(int(col_x[ci] + 8), int(y),
                                 int(col_x[ci + 1] - col_x[ci] - 12), head_h,
                                 Qt.AlignLeft | Qt.AlignVCenter, htext)
            y += head_h
            painter.setFont(cell_font)
            for ri, st in enumerate(stages):
                if ri % 2 == 1:
                    painter.fillRect(int(plot_left), int(y), int(table_w), row_h, zebra_bg)
                color = QColor(_SUMMARY_STAGE_COLORS.get(st["label"], "#94a3b8"))
                cells = (
                    (f"S{ri + 1}", color),
                    (_SUMMARY_STAGE_NAMES.get(st["label"], st["label"]), text_color),
                    (_summary_fmt_time(st["end"] - st["start"]), text_color),
                    (f"{st['mean']:.4g}", text_color),
                )
                for ci, (ctext, ccolor) in enumerate(cells):
                    painter.setPen(ccolor)
                    painter.drawText(int(col_x[ci] + 8), int(y),
                                     int(col_x[ci + 1] - col_x[ci] - 12), row_h,
                                     Qt.AlignLeft | Qt.AlignVCenter, ctext)
                painter.setPen(QPen(frame_color, 1))
                painter.drawLine(int(plot_left), int(y + row_h),
                                 int(plot_right), int(y + row_h))
                y += row_h
            painter.setPen(QPen(frame_color, 1))
            painter.drawLine(int(plot_left), int(table_top), int(plot_left), int(y))
            painter.drawLine(int(plot_right), int(table_top), int(plot_right), int(y))
            y += sec_gap
    finally:
        painter.end()
    return pixmap
