#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import math
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QPushButton, QStackedWidget, QListWidget, QListWidgetItem,
    QMessageBox, QInputDialog, QSizePolicy, QRadioButton, QButtonGroup,
    QTableWidget, QTableWidgetItem, QMenu, QDialog, QDialogButtonBox,
    QFileDialog, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, QRectF
from PySide6.QtGui import QPainter, QPen, QColor

from log_config import get_logger
from resource_path import get_resource_base, get_user_data_dir
from ui.utils.icon_utils import tinted_svg_icon
from ui.widgets.dark_combobox import DarkComboBox
from ui.pages.power_analyzer.widgets import (
    ChannelTabBar, SlideToggle, SelectAllLineEdit, collapsible_header_style,
    is_it2705_instrument,
    CONTENT_BG, PANEL_BG, PANEL_BORDER, CARD_BG, CARD_BORDER,
    CONTAINER_RADIUS, WIDGET_RADIUS, MUTED_TEXT,
    DISABLED_TEXT, DISABLED_BTN_BG, DISABLED_BTN_BORDER,
    INACTIVE_TAB_BG, INACTIVE_TAB_HOVER_BG,
)

logger = get_logger(__name__)

_ARB_TYPES = [("VOLT", "Voltage"), ("CURR", "Current")]

# (shape_key, 显示名, 图标文件名) —— 顺序即下拉与 QStackedWidget 页序
_ARB_SHAPES = [
    ("none", "No Arb Configured", "arb_none.svg"),
    ("sine", "Sine", "arb_sine.svg"),
    ("step", "Step", "arb_step.svg"),
    ("ramp", "Ramp", "arb_ramp.svg"),
    ("staircase", "Staircase", "arb_staircase.svg"),
    ("pulse", "Pulse", "arb_pulse.svg"),
    ("trapezoid", "Trapezoid", "arb_trapezoid.svg"),
    ("exponential", "Exponential", "arb_exponential.svg"),
    ("cdwell", "Constant Dwell (CD)", "arb_cdwell.svg"),
    ("udef", "User Defined", "arb_udef.svg"),
    ("seq", "Sequence", "arb_sequence.svg"),
]

# SEQ 本阶段占位（编辑后续版本提供）；IT2705 无 CDW 指令、UDEF 为机内波形文件、SEQ 语法不同
_ARB_PLACEHOLDER_SHAPES = frozenset({"seq"})
_ARB_IT2705_UNSUPPORTED = frozenset({"cdwell", "udef", "seq"})

# 旧版预设（pulse_v/pulse_i 与旧字段名）兼容映射
_LEGACY_SHAPE_MAP = {"pulse_v": ("pulse", "VOLT"), "pulse_i": ("pulse", "CURR")}
_LEGACY_FIELD_MAP = {"i0": "v0", "i1": "v1", "offset_v": "offset", "ampl_vrms": "ampl"}

# shape_key -> [(label_tpl, field_key, default, wheel_step, kind), ...]
# label_tpl 中 {u} 随 Arb Type 替换为 V / A；kind: level/time/freq/steps/list_level/list_time
# 时间字段按时间流排序（start -> top -> end），field_key 与驱动参数对应
_ARB_FIELDS = {
    "none": [],
    "sine": [
        ("DC Offset ({u}):", "offset", "3.3", 0.1, "level"),
        ("Amplitude ({u}rms):", "ampl", "0.1", 0.01, "level"),
        ("Frequency (Hz):", "freq_hz", "1000", 1, "freq"),
    ],
    "step": [
        ("Start Level ({u}):", "v0", "3.3", 0.1, "level"),
        ("End Level ({u}):", "v1", "3.8", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.01", 0.001, "time"),
        ("End Hold (s):", "t1", "0.01", 0.001, "time"),
    ],
    "ramp": [
        ("Start Level ({u}):", "v0", "3.0", 0.1, "level"),
        ("End Level ({u}):", "v1", "4.0", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.005", 0.001, "time"),
        ("Rise Time (s):", "rt", "0.05", 0.001, "time"),
        ("End Hold (s):", "t1", "0.005", 0.001, "time"),
    ],
    "staircase": [
        ("Start Level ({u}):", "v0", "3.0", 0.1, "level"),
        ("End Level ({u}):", "v1", "4.0", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.005", 0.001, "time"),
        ("Stair Time (s):", "t1", "0.05", 0.001, "time"),
        ("End Hold (s):", "t2", "0.005", 0.001, "time"),
        ("Steps:", "steps", "10", 1, "steps"),
    ],
    "pulse": [
        ("Base Level ({u}):", "v0", "3.3", 0.1, "level"),
        ("Top Level ({u}):", "v1", "3.8", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.0005", 0.0001, "time"),
        ("Top Hold (s):", "t2", "0.0005", 0.0001, "time"),
        ("End Hold (s):", "t1", "0", 0.0001, "time"),
        ("Frequency (Hz):", "freq_hz", "100", 1, "freq"),
    ],
    "trapezoid": [
        ("Start Level ({u}):", "v0", "3.0", 0.1, "level"),
        ("Top Level ({u}):", "v1", "4.0", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.005", 0.001, "time"),
        ("Rise Time (s):", "rt", "0.01", 0.001, "time"),
        ("Top Hold (s):", "tt", "0.02", 0.001, "time"),
        ("Fall Time (s):", "ft", "0.01", 0.001, "time"),
        ("End Hold (s):", "t1", "0.005", 0.001, "time"),
    ],
    "exponential": [
        ("Start Level ({u}):", "v0", "3.0", 0.1, "level"),
        ("End Level ({u}):", "v1", "4.0", 0.1, "level"),
        ("Start Delay (s):", "t0", "0.005", 0.001, "time"),
        ("Time Constant (s):", "tc", "0.02", 0.001, "time"),
        ("Total Time (s):", "t1", "0.1", 0.001, "time"),
    ],
    "cdwell": [
        ("Levels ({u}, comma list):", "levels", "3.2, 3.4, 3.6, 3.8", None, "list_level"),
        ("Dwell (s):", "dwell", "0.01", 0.001, "time"),
    ],
    "udef": [],  # 点表编辑器（模型 _arb_udef_points），不走文本字段
    "seq": [],
}

_ARB_INPUT_STYLE = f"""
    QLineEdit {{
        background-color: #111d36; color: #dbe6ff;
        border: 1px solid #1e3050; border-radius: {WIDGET_RADIUS};
        padding: 4px 8px; font-size: 12px; font-weight: 600;
    }}
    QLineEdit:focus {{ border: 1px solid #3a5a90; color: #ffffff; }}
    QLineEdit:disabled {{ background-color: #0b1730; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
"""

_ARB_PRESETS_FILENAME = "arb_presets.json"

_ARB_ICON_COLOR = "#c8d5e2"


def _arb_presets_path() -> str:
    return os.path.join(get_user_data_dir("n6705c"), _ARB_PRESETS_FILENAME)


def _arb_icon_dir() -> str:
    return os.path.join(get_resource_base(), "resources", "icons")


class _ArbRunWorker(QObject):
    """Arb 下发 / 停止 worker（QThread 内执行，UI 不阻塞）。"""

    finished = Signal(str, int, str, bool, str)  # dev_label, channel, mode, success, message

    def __init__(self, instance, dev_label, channel, mode,
                 shape_key=None, values=None, arb_type="VOLT",
                 continuous=False, repeat_count=None, terminate_last=False,
                 io_lock=None):
        super().__init__()
        self._instance = instance
        self._dev_label = dev_label
        self._channel = channel
        self._mode = mode  # "apply" | "stop"
        self._shape_key = shape_key
        self._values = values or {}
        self._arb_type = arb_type
        self._continuous = continuous
        self._repeat_count = repeat_count
        self._terminate_last = terminate_last
        self._io_lock = io_lock

    def run(self):
        try:
            if self._io_lock is not None:
                self._io_lock.acquire()
            try:
                if self._mode == "apply":
                    self._apply()
                    message = f"{self._dev_label}-CH{self._channel} arb started"
                else:
                    self._instance.arb_stop(self._channel)
                    message = f"{self._dev_label}-CH{self._channel} arb stopped"
            finally:
                if self._io_lock is not None:
                    self._io_lock.release()
            logger.info("Arb %s ok: %s", self._mode, message)
            self.finished.emit(self._dev_label, self._channel, self._mode, True, message)
        except Exception as exc:
            logger.error("Arb %s failed: %s", self._mode, exc, exc_info=True)
            self.finished.emit(self._dev_label, self._channel, self._mode, False, str(exc))

    def _apply(self):
        inst = self._instance
        ch = self._channel
        v = self._values
        shape = self._shape_key
        tp = self._arb_type
        if shape == "none":
            inst.set_arb_none(ch, tp)
            return
        if shape == "sine":
            inst.set_arb_sine(ch, v["offset"], v["ampl"], v["freq_hz"], arb_type=tp)
        elif shape == "step":
            inst.set_arb_step(ch, v["v0"], v["v1"], v["t0"], v["t1"], arb_type=tp)
        elif shape == "ramp":
            inst.set_arb_ramp(ch, v["v0"], v["v1"], v["t0"], v["rt"], v["t1"], arb_type=tp)
        elif shape == "staircase":
            inst.set_arb_staircase(
                ch, v["v0"], v["v1"], v["t0"], v["t1"], v["t2"], int(v["steps"]), arb_type=tp
            )
        elif shape == "pulse":
            inst.set_arb_pulse(
                ch, v["v0"], v["v1"], v["t0"], v["t1"], v["t2"], v["freq_hz"], arb_type=tp
            )
        elif shape == "trapezoid":
            inst.set_arb_trapezoid(
                ch, v["v0"], v["v1"], v["t0"], v["rt"], v["tt"], v["ft"], v["t1"], arb_type=tp
            )
        elif shape == "exponential":
            inst.set_arb_exponential(
                ch, v["v0"], v["v1"], v["t0"], v["tc"], v["t1"], arb_type=tp
            )
        elif shape == "cdwell":
            inst.set_arb_constant_dwell(ch, v["levels"], v["dwell"], arb_type=tp)
        elif shape == "udef":
            inst.set_arb_user_defined(ch, v["levels"], v.get("dwells"), arb_type=tp)
        else:
            raise ValueError(f"Unknown arb shape: {shape}")
        # Continuous / Repeat Count 与结束方式须在形状配置完成后、触发前设置（驱动契约）
        if self._continuous:
            inst.set_arb_continuous(ch, True)
        elif self._repeat_count:
            inst.set_arb_repeat_count(ch, self._repeat_count)
        inst.set_arb_terminate_last(ch, self._terminate_last)
        inst.arb_on(ch)


class _ArbWaveformPreview(QWidget):
    """按当前 Arb 参数实时绘制的波形示意图（类仪器面板图示）。

    User Defined 形状下进入交互模式：每个点一个区域，可点选（Ctrl 多选）、
    拖拽改 level/dwell、右键弹参数编辑。
    """

    sig_udef_clicked = Signal(int, object)   # index, Qt.KeyboardModifiers
    sig_udef_changed = Signal(int, float, float)  # index, level, dwell
    sig_udef_edit = Signal(int)              # index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shape = "none"
        self._values = {}
        self._unit = "V"
        self._accent = QColor(_ARB_ICON_COLOR)
        self._interactive = False
        self._udef_points = []      # [[level, dwell], ...]（交互模式副本）
        self._udef_sel = set()
        self._udef_regions = []     # [(x0, x1, index)] 命中测试
        self._map_state = None      # (plot_rect, t_min, t_max, v_min, v_max)
        self._drag = None
        self.setMinimumSize(220, 130)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_config(self, shape, values, arb_type, accent):
        self._shape = shape
        self._values = values or {}
        self._unit = "V" if arb_type == "VOLT" else "A"
        self._accent = QColor(accent)
        self.update()

    def set_udef_interaction(self, enabled, points, selected):
        self._interactive = bool(enabled)
        self._udef_points = [list(p) for p in points] if enabled else []
        self._udef_sel = set(selected) if enabled else set()
        if not enabled:
            self._drag = None
        self.update()

    # ---------------------------------------------------------- wave compute
    def _wave_points(self):
        """返回 (points[(t, v)], level_marks[(value, name)])；t 单位任意仅用于比例。"""
        v = self._values
        shape = self._shape
        if shape == "seq":
            return None, []
        if shape == "none":
            return [(0.0, 0.0), (1.0, 0.0)], []
        if shape == "sine":
            freq = max(v.get("freq_hz", 0.0), 1e-9)
            period = 1.0 / freq
            offset = v.get("offset", 0.0)
            peak = math.sqrt(2.0) * v.get("ampl", 0.0)
            pts = [
                (2 * period * i / 100, offset + peak * math.sin(2 * math.pi * i / 100))
                for i in range(101)
            ]
            return pts, [(offset + peak, "Max"), (offset - peak, "Min")]
        if shape == "step":
            v0, v1 = v.get("v0", 0.0), v.get("v1", 0.0)
            t0 = max(v.get("t0", 0.0), 1e-9)
            t1 = v.get("t1", 0.0) if v.get("t1", 0.0) > 0 else t0
            return ([(0.0, v0), (t0, v0), (t0, v1), (t0 + t1, v1)],
                    [(v0, "V0"), (v1, "V1")])
        if shape == "ramp":
            v0, v1 = v.get("v0", 0.0), v.get("v1", 0.0)
            t0 = max(v.get("t0", 0.0), 1e-9)
            rt = max(v.get("rt", 0.0), 1e-9)
            t1 = v.get("t1", 0.0) if v.get("t1", 0.0) > 0 else t0
            return ([(0.0, v0), (t0, v0), (t0 + rt, v1), (t0 + rt + t1, v1)],
                    [(v0, "V0"), (v1, "V1")])
        if shape == "staircase":
            v0, v1 = v.get("v0", 0.0), v.get("v1", 0.0)
            t0 = max(v.get("t0", 0.0), 1e-9)
            t1 = max(v.get("t1", 0.0), 1e-9)
            t2 = v.get("t2", 0.0) if v.get("t2", 0.0) > 0 else t0
            steps = max(int(v.get("steps", 10)), 1)
            pts = [(0.0, v0), (t0, v0)]
            for i in range(1, steps + 1):
                ti = t0 + t1 * i / steps
                vi = v0 + (v1 - v0) * i / steps
                pts.append((ti, pts[-1][1]))
                pts.append((ti, vi))
            pts.append((t0 + t1 + t2, v1))
            return pts, [(v0, "V0"), (v1, "V1")]
        if shape == "pulse":
            v0, v1 = v.get("v0", 0.0), v.get("v1", 0.0)
            freq = max(v.get("freq_hz", 0.0), 1e-9)
            period = 1.0 / freq
            total = v.get("t0", 0.0) + v.get("t2", 0.0) + v.get("t1", 0.0)
            scale = period / total if total > 0 else 1.0
            t0 = v.get("t0", 0.0) * scale
            t2 = v.get("t2", 0.0) * scale
            t1 = v.get("t1", 0.0) * scale
            pts = [(0.0, v0), (t0, v0), (t0, v1), (t0 + t2, v1),
                   (t0 + t2, v0), (period, v0)]
            # 再画下一个周期开头，示意重复
            pts += [(period + t0, v0), (period + t0, v1), (period + t0 + t2, v1)]
            return pts, [(v0, "V0"), (v1, "V1")]
        if shape == "trapezoid":
            v0, v1 = v.get("v0", 0.0), v.get("v1", 0.0)
            t0 = max(v.get("t0", 0.0), 1e-9)
            rt = max(v.get("rt", 0.0), 1e-9)
            tt = v.get("tt", 0.0) if v.get("tt", 0.0) > 0 else rt
            ft = max(v.get("ft", 0.0), 1e-9)
            t1 = v.get("t1", 0.0) if v.get("t1", 0.0) > 0 else t0
            return ([(0.0, v0), (t0, v0), (t0 + rt, v1), (t0 + rt + tt, v1),
                     (t0 + rt + tt + ft, v0), (t0 + rt + tt + ft + t1, v0)],
                    [(v0, "V0"), (v1, "V1")])
        if shape == "exponential":
            v0, v1 = v.get("v0", 0.0), v.get("v1", 0.0)
            t0 = max(v.get("t0", 0.0), 1e-9)
            tc = max(v.get("tc", 0.0), 1e-9)
            t1 = max(v.get("t1", 0.0), tc)
            pts = [(0.0, v0), (t0, v0)]
            for i in range(1, 61):
                t = t1 * i / 60
                pts.append((t0 + t, v1 - (v1 - v0) * math.exp(-t / tc)))
            return pts, [(v0, "V0"), (v1, "V1")]
        if shape == "cdwell":
            levels = v.get("levels") or [0.0]
            dwell = max(v.get("dwell", 0.0), 1e-9)
            pts = []
            for i, lv in enumerate(levels):
                pts.append((dwell * i, lv))
                pts.append((dwell * (i + 1), lv))
            return pts, []
        if shape == "udef":
            levels = v.get("levels") or [0.0]
            dwells = v.get("dwells") or []
            if len(dwells) != len(levels):
                dwells = [1.0] * len(levels)
            pts = []
            t = 0.0
            for lv, dw in zip(levels, dwells):
                dw = max(float(dw), 1e-9)
                pts.append((t, lv))
                pts.append((t + dw, lv))
                t += dw
            return pts, []
        return [(0.0, 0.0), (1.0, 0.0)], []

    # --------------------------------------------------------------- painting
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(CARD_BORDER), 1))
        p.setBrush(QColor(CARD_BG))
        p.drawRoundedRect(rect, 8, 8)

        points, marks = self._wave_points()
        if points is None:
            p.setPen(QPen(QColor(MUTED_TEXT), 1))
            p.drawText(rect, Qt.AlignCenter, "Sequence")
            p.end()
            return

        t_vals = [pt[0] for pt in points]
        v_vals = [pt[1] for pt in points] + [m[0] for m in marks]
        t_min, t_max = min(t_vals), max(t_vals)
        v_min, v_max = min(v_vals), max(v_vals)
        if t_max <= t_min:
            t_max = t_min + 1.0
        if v_max <= v_min:
            v_max = v_min + 1.0
        v_pad = (v_max - v_min) * 0.12
        v_min -= v_pad
        v_max += v_pad

        plot = rect.adjusted(44, 8, -8, -14)
        self._map_state = (plot, t_min, t_max, v_min, v_max)

        def map_pt(t, val):
            x = plot.left() + (t - t_min) / (t_max - t_min) * plot.width()
            y = plot.bottom() - (val - v_min) / (v_max - v_min) * plot.height()
            return x, y

        font = p.font()
        font.setPixelSize(9)
        p.setFont(font)

        # UDEF 交互区域（每个点一列，选中高亮）
        self._udef_regions = []
        if self._interactive and self._shape == "udef" and self._udef_points:
            t_acc = 0.0
            for idx, (_lv, dw) in enumerate(self._udef_points):
                x0, _ = map_pt(t_acc, v_min)
                x1, _ = map_pt(t_acc + max(float(dw), 1e-9), v_min)
                self._udef_regions.append((x0, x1, idx))
                t_acc += max(float(dw), 1e-9)
            for x0, x1, idx in self._udef_regions:
                if idx in self._udef_sel:
                    fill = QColor(self._accent)
                    fill.setAlpha(60)
                else:
                    fill = QColor("#ffffff")
                    fill.setAlpha(10 if idx % 2 == 0 else 20)
                p.setPen(Qt.NoPen)
                p.setBrush(fill)
                p.drawRect(QRectF(x0, plot.top(), x1 - x0, plot.height()))
                p.setPen(QPen(QColor(MUTED_TEXT), 1))
                p.drawText(
                    QRectF(x0 + 2, plot.top() + 1, max(x1 - x0 - 4, 8), 12),
                    Qt.AlignLeft | Qt.AlignVCenter,
                    f"#{idx + 1}",
                )

        # 零基线
        if v_min < 0 < v_max:
            x0, y0 = map_pt(t_min, 0.0)
            x1, _y1 = map_pt(t_max, 0.0)
            pen = QPen(QColor("#3a5a90"), 1, Qt.DashLine)
            p.setPen(pen)
            p.drawLine(int(x0), int(y0), int(x1), int(y0))

        # 电平标注（虚线 + 数值）
        for value, name in marks:
            _x0, y = map_pt(t_min, value)
            _x1, _y = map_pt(t_max, value)
            p.setPen(QPen(QColor("#3a5a90"), 1, Qt.DotLine))
            p.drawLine(int(plot.left()), int(y), int(plot.right()), int(y))
            p.setPen(QPen(QColor(MUTED_TEXT), 1))
            p.drawText(
                QRectF(rect.left() + 2, y - 7, 42, 14),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"{name} {value:g}{self._unit}",
            )

        # 波形主线
        p.setPen(QPen(self._accent, 2))
        prev = None
        for t, val in points:
            x, y = map_pt(t, val)
            if prev is not None:
                p.drawLine(int(prev[0]), int(prev[1]), int(x), int(y))
            prev = (x, y)

        p.end()

    # ---------------------------------------------------------- interaction
    def _region_at(self, x):
        for x0, x1, idx in self._udef_regions:
            if x0 <= x <= x1:
                return idx
        return None

    def _y_to_level(self, y):
        if not self._map_state:
            return 0.0
        plot, _t0, _t1, v_min, v_max = self._map_state
        ratio = (plot.bottom() - y) / max(plot.height(), 1e-9)
        return v_min + ratio * (v_max - v_min)

    def _x_scale(self):
        """x 像素 -> 时间单位比例。"""
        if not self._map_state:
            return 1.0
        plot, t_min, t_max, _v0, _v1 = self._map_state
        return (t_max - t_min) / max(plot.width(), 1e-9)

    def mousePressEvent(self, event):
        if self._interactive and self._shape == "udef":
            idx = self._region_at(event.position().x())
            if idx is not None:
                if event.button() == Qt.LeftButton:
                    self.sig_udef_clicked.emit(idx, event.modifiers())
                    if idx < len(self._udef_points):
                        lv, dw = self._udef_points[idx]
                        self._drag = {
                            "idx": idx,
                            "start_x": event.position().x(),
                            "orig_dwell": float(dw),
                            "x_scale": self._x_scale(),
                        }
                elif event.button() == Qt.RightButton:
                    self.sig_udef_edit.emit(idx)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag is not None:
            idx = self._drag["idx"]
            if idx < len(self._udef_points):
                level = self._y_to_level(event.position().y())
                dx = event.position().x() - self._drag["start_x"]
                dwell = max(self._drag["orig_dwell"] + dx * self._drag["x_scale"], 1e-4)
                self.sig_udef_changed.emit(idx, level, dwell)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag is not None:
            self._drag = None
            return
        super().mouseReleaseEvent(event)


class _UdefPointDialog(QDialog):
    """UDEF 单点参数编辑对话框（示意图右键 / 表格右键 Edit...）。"""

    def __init__(self, level, dwell, unit, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Point")
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {CONTENT_BG}; }}
            QLabel {{ color: {MUTED_TEXT}; font-size: 11px; background: transparent; border: none; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)
        level_label = QLabel(f"Level ({unit}):")
        self.level_edit = SelectAllLineEdit(f"{level:g}")
        self.level_edit.setStyleSheet(_ARB_INPUT_STYLE)
        self.level_edit.setMinimumWidth(140)
        dwell_label = QLabel("Dwell (s):")
        self.dwell_edit = SelectAllLineEdit(f"{dwell:g}")
        self.dwell_edit.setStyleSheet(_ARB_INPUT_STYLE)
        self.dwell_edit.setMinimumWidth(140)
        form.addWidget(level_label, 0, 0)
        form.addWidget(self.level_edit, 0, 1)
        form.addWidget(dwell_label, 1, 0)
        form.addWidget(self.dwell_edit, 1, 1)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        try:
            level = float(self.level_edit.text().strip())
        except ValueError as exc:
            raise ValueError(f"Level invalid: '{self.level_edit.text().strip()}'") from exc
        try:
            dwell = float(self.dwell_edit.text().strip())
        except ValueError as exc:
            raise ValueError(f"Dwell invalid: '{self.dwell_edit.text().strip()}'") from exc
        if dwell <= 0:
            raise ValueError("Dwell must be > 0")
        return level, dwell


class ArbViewMixin:
    """Arb Set 面板：左侧通道 Arb 配置（独立 tab），右侧常用预设（JSON 持久化）。"""

    # ------------------------------------------------------------------ panel
    def _create_arb_panel(self):
        self.arb_collapsed = True
        self._arb_current_device = "A"
        self._arb_current_channel = 1
        self._arb_param_store = {}
        self._arb_loading = False
        self._arb_last_shape = "none"
        self._arb_threads = {}
        self._arb_workers = {}
        self._arb_running = set()  # (dev_label, channel) Arb 运行态
        self._arb_presets = []
        # UDEF 点模型（当前通道）：[[level, dwell], ...]
        self._arb_udef_points = [[3.0, 0.001], [3.5, 0.001], [4.0, 0.001], [3.5, 0.001]]
        self._arb_udef_selected = set()
        self._arb_udef_loading = False

        outer = QWidget()
        outer.setStyleSheet("QWidget { background: transparent; border: none; }")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.arb_toggle_btn = QPushButton("\u25b6  Arb Set")
        self.arb_toggle_btn.setStyleSheet(collapsible_header_style(True))
        self.arb_toggle_btn.clicked.connect(self._toggle_arb_panel)
        outer_layout.addWidget(self.arb_toggle_btn)

        self.arb_content = QFrame()
        self.arb_content.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG};
                border: 1px solid {PANEL_BORDER};
                border-top: none;
                border-bottom-left-radius: {CONTAINER_RADIUS};
                border-bottom-right-radius: {CONTAINER_RADIUS};
            }}
        """)
        self.arb_content.setVisible(False)

        content_layout = QHBoxLayout(self.arb_content)
        content_layout.setContentsMargins(16, 10, 16, 14)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._create_arb_channel_zone(), 3)
        content_layout.addWidget(self._create_arb_preset_zone(), 2)

        outer_layout.addWidget(self.arb_content)

        self._build_arb_tab_buttons()
        self._arb_load_channel_params()
        self._arb_load_presets()
        self._arb_refresh_action_state()
        return outer

    def _toggle_arb_panel(self):
        self.arb_collapsed = not self.arb_collapsed
        self.arb_content.setVisible(not self.arb_collapsed)
        self.arb_toggle_btn.setText(
            "\u25b6  Arb Set" if self.arb_collapsed else "\u25bc  Arb Set"
        )
        self.arb_toggle_btn.setStyleSheet(collapsible_header_style(self.arb_collapsed))
        if not self.arb_collapsed:
            # 折叠期 arb_content 隐藏、布局未激活，tab 按钮 geometry 为未排布值；
            # 展开后须重算活动 tab 的底线缺口（内部经 singleShot 待布局完成取几何）
            self._refresh_arb_tab_styles()

    # ----------------------------------------------------------- channel zone
    def _create_arb_channel_zone(self):
        zone = QWidget()
        zone.setStyleSheet("QWidget { background: transparent; border: none; }")
        zone_layout = QVBoxLayout(zone)
        zone_layout.setContentsMargins(0, 0, 0, 0)
        zone_layout.setSpacing(0)

        self._arb_tab_bar = ChannelTabBar()
        self._arb_tabs_layout = self._arb_tab_bar.layout()
        self.arb_tab_buttons = []
        self._arb_tab_separator = None
        zone_layout.addWidget(self._arb_tab_bar)

        self.arb_body = QFrame()
        self.arb_body.setObjectName("ArbContentFrame")
        zone_layout.addWidget(self.arb_body)

        body_layout = QVBoxLayout(self.arb_body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.arb_ch_title = QLabel("Channel 1")
        self.arb_ch_title.setStyleSheet(
            "QLabel { font-size: 14px; font-weight: 800; color: #ffffff; border: none; background: transparent; }"
        )
        title_row.addWidget(self.arb_ch_title)
        title_row.addStretch()
        repeat_label = QLabel("Repeat Count")
        repeat_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
        )
        title_row.addWidget(repeat_label)
        self.arb_repeat_input = SelectAllLineEdit("1")
        self.arb_repeat_input.set_wheel_step(1)
        self.arb_repeat_input.setFixedWidth(56)
        self.arb_repeat_input.setAlignment(Qt.AlignCenter)
        self.arb_repeat_input.setStyleSheet(_ARB_INPUT_STYLE)
        self.arb_repeat_input.setToolTip("Repeat count (used when Continuous is off)")
        title_row.addWidget(self.arb_repeat_input)
        cont_label = QLabel("Continuous")
        cont_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
        )
        title_row.addWidget(cont_label)
        self.arb_continuous_toggle = SlideToggle()
        self.arb_continuous_toggle.clicked.connect(self._arb_on_continuous_toggled)
        title_row.addWidget(self.arb_continuous_toggle)
        body_layout.addLayout(title_row)

        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        type_label = QLabel("Arb Type:")
        type_label.setFixedWidth(66)
        type_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
        )
        type_row.addWidget(type_label)
        self.arb_type_combo = DarkComboBox()
        for _key, label in _ARB_TYPES:
            self.arb_type_combo.addItem(label)
        self.arb_type_combo.currentIndexChanged.connect(self._arb_on_type_changed)
        type_row.addWidget(self.arb_type_combo, 1)

        shape_row = QHBoxLayout()
        shape_row.setSpacing(8)
        shape_label = QLabel("Waveform:")
        shape_label.setFixedWidth(66)
        shape_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
        )
        shape_row.addWidget(shape_label)
        self.arb_shape_combo = DarkComboBox()
        for _key, label, icon_file in _ARB_SHAPES:
            icon = tinted_svg_icon(
                os.path.join(_arb_icon_dir(), icon_file), _ARB_ICON_COLOR, 16
            )
            self.arb_shape_combo.addItem(icon, label)
        self.arb_shape_combo.currentIndexChanged.connect(self._arb_on_shape_changed)
        shape_row.addWidget(self.arb_shape_combo, 1)

        self.arb_wave_preview = _ArbWaveformPreview()
        self.arb_wave_preview.sig_udef_clicked.connect(self._arb_udef_on_region_clicked)
        self.arb_wave_preview.sig_udef_changed.connect(self._arb_udef_on_region_changed)
        self.arb_wave_preview.sig_udef_edit.connect(self._arb_udef_on_region_edit)

        self.arb_params_stack = QStackedWidget()
        self.arb_param_inputs = {}  # shape_key -> {field_key: SelectAllLineEdit}
        self.arb_param_labels = {}  # shape_key -> [(QLabel, label_tpl)]
        for shape_key, _label, _icon in _ARB_SHAPES:
            page, inputs, labels = self._create_arb_params_page(shape_key)
            self.arb_params_stack.addWidget(page)
            self.arb_param_inputs[shape_key] = inputs
            self.arb_param_labels[shape_key] = labels

        # 结束方式（Return to DC / Last Arb），Waveform 下方横排
        self.arb_term_group = QButtonGroup(self)
        self.arb_term_dc_radio = QRadioButton("Return to DC")
        self.arb_term_last_radio = QRadioButton("Last Arb")
        self.arb_term_dc_radio.setChecked(True)
        self.arb_term_dc_radio.setToolTip("Return to DC Value: output returns to the pre-Arb settings")
        self.arb_term_last_radio.setToolTip("Last Arb Value: output stays at the last Arb value")
        for idx, radio in enumerate((self.arb_term_dc_radio, self.arb_term_last_radio)):
            self.arb_term_group.addButton(radio, idx)
        self.arb_term_last_radio.toggled.connect(self._arb_on_terminate_toggled)
        self._arb_update_radio_style()

        # 三栏：左紧凑选择器（Arb Type / Waveform / 结束方式 + RUN/STOP），中参数区，右波形示意图
        config_row = QHBoxLayout()
        config_row.setSpacing(10)
        selector_col = QVBoxLayout()
        selector_col.setSpacing(8)
        selector_col.addLayout(type_row)
        selector_col.addLayout(shape_row)
        term_row = QHBoxLayout()
        term_row.setSpacing(12)
        term_row.addWidget(self.arb_term_dc_radio)
        term_row.addWidget(self.arb_term_last_radio)
        term_row.addStretch()
        selector_col.addLayout(term_row)
        selector_col.addStretch()

        self.arb_run_btn = QPushButton("\u25b6  RUN")
        self.arb_run_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.arb_run_btn.clicked.connect(self._arb_on_run_stop_clicked)
        selector_col.addWidget(self.arb_run_btn)

        config_row.addLayout(selector_col)
        config_row.addWidget(self.arb_params_stack, 3)
        config_row.addWidget(self.arb_wave_preview, 2)
        body_layout.addLayout(config_row, 1)

        self._arb_apply_channel_theme()
        self._arb_refresh_preview()
        return zone

    def _create_arb_params_page(self, shape_key):
        if shape_key == "udef":
            return self._create_udef_page()
        page = QFrame()
        page.setStyleSheet(
            f"QFrame {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: {CONTAINER_RADIUS}; }}"
        )
        grid = QGridLayout(page)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        inputs = {}
        labels = []
        fields = _ARB_FIELDS[shape_key]
        if not fields:
            hint = QLabel(
                "Sequence editing will be available in a future release."
                if shape_key == "seq"
                else "Clears the Arb configuration of this channel."
            )
            hint.setWordWrap(True)
            hint.setStyleSheet(
                f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
            )
            grid.addWidget(hint, 0, 0, 1, 4)
        for idx, (label_tpl, field_key, default_text, wheel_step, _kind) in enumerate(fields):
            row, col = divmod(idx, 2)
            label = QLabel(label_tpl.replace("{u}", "V"))
            label.setStyleSheet(
                f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
            )
            edit = SelectAllLineEdit(default_text)
            edit.set_wheel_step(wheel_step)
            edit.setAlignment(Qt.AlignCenter)
            edit.setStyleSheet(_ARB_INPUT_STYLE)
            edit.textChanged.connect(lambda _t: self._arb_refresh_preview())
            if _kind in ("list_level", "list_time"):
                edit.setMinimumWidth(200)
                edit.setAlignment(Qt.AlignLeft)
                grid.addWidget(label, row * 2, 0, 1, 4)
                grid.addWidget(edit, row * 2 + 1, 0, 1, 4)
            else:
                edit.setFixedWidth(100)
                grid.addWidget(label, row, col * 2)
                grid.addWidget(edit, row, col * 2 + 1)
            inputs[field_key] = edit
            labels.append((label, label_tpl))
        grid.setColumnStretch(4, 1)
        return page, inputs, labels

    # ------------------------------------------------------------- udef page
    def _create_udef_page(self):
        """User Defined 点表编辑器：上表格（直接编辑/Ctrl 多选同改/右键），下按钮行。"""
        page = QFrame()
        page.setStyleSheet(
            f"QFrame {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: {CONTAINER_RADIUS}; }}"
        )
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        self.arb_udef_table = QTableWidget(0, 3)
        self.arb_udef_table.setHorizontalHeaderLabels(["#", "Level (V)", "Dwell (s)"])
        header = self.arb_udef_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.arb_udef_table.verticalHeader().setVisible(False)
        self.arb_udef_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.arb_udef_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.arb_udef_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.arb_udef_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #091426; color: #dbe6ff;
                border: 1px solid {CARD_BORDER}; border-radius: {WIDGET_RADIUS};
                gridline-color: #12224a; font-size: 11px; outline: 0;
            }}
            QTableWidget::item {{ padding: 2px 6px; border: none; }}
            QTableWidget::item:selected {{ background-color: #1a2a50; color: #ffffff; }}
            QHeaderView::section {{
                background-color: #0b1b34; color: {MUTED_TEXT};
                border: none; border-bottom: 1px solid {CARD_BORDER};
                font-size: 10px; font-weight: 700; padding: 4px 6px;
            }}
        """)
        self.arb_udef_table.cellChanged.connect(self._arb_udef_on_cell_changed)
        self.arb_udef_table.itemSelectionChanged.connect(self._arb_udef_on_table_selection)
        self.arb_udef_table.customContextMenuRequested.connect(self._arb_udef_context_menu)
        layout.addWidget(self.arb_udef_table, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        udef_btn_style = f"""
            QPushButton {{
                background-color: #0b1730; color: #dbe6ff;
                border: 1px solid #23417a; border-radius: {WIDGET_RADIUS};
                font-size: 11px; padding: 3px 8px; min-height: 24px;
            }}
            QPushButton:hover {{ background-color: #10203e; }}
            QPushButton:disabled {{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
        """
        for text, slot in (
            ("Add", self._arb_udef_add_point),
            ("Delete", self._arb_udef_delete_selected),
            ("Clear", self._arb_udef_clear_points),
            ("Import", self._arb_udef_import_csv),
            ("Export", self._arb_udef_export_csv),
        ):
            btn = QPushButton(text)
            btn.setStyleSheet(udef_btn_style)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn, 1)
        layout.addLayout(btn_row)

        self._arb_udef_sync_table()
        return page, {}, []

    def _arb_udef_sync_table(self):
        """模型 -> 表格重建（保留选中行）。"""
        if not hasattr(self, "arb_udef_table"):
            return
        table = self.arb_udef_table
        prev_sel = set(self._arb_udef_selected)
        self._arb_udef_loading = True
        try:
            table.setRowCount(len(self._arb_udef_points))
            for row, (lv, dw) in enumerate(self._arb_udef_points):
                idx_item = QTableWidgetItem(str(row + 1))
                idx_item.setFlags(idx_item.flags() & ~Qt.ItemIsEditable)
                idx_item.setTextAlignment(Qt.AlignCenter)
                lv_item = QTableWidgetItem(f"{lv:g}")
                lv_item.setTextAlignment(Qt.AlignCenter)
                dw_item = QTableWidgetItem(f"{dw:g}")
                dw_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 0, idx_item)
                table.setItem(row, 1, lv_item)
                table.setItem(row, 2, dw_item)
            table.clearSelection()
            model = table.selectionModel()
            for row in sorted(prev_sel):
                if row < table.rowCount():
                    model.select(
                        table.model().index(row, 0),
                        model.SelectionFlag.Select | model.SelectionFlag.Rows,
                    )
        finally:
            self._arb_udef_loading = False

    def _arb_udef_selected_rows(self):
        return sorted({idx.row() for idx in self.arb_udef_table.selectionModel().selectedRows()})

    def _arb_udef_on_cell_changed(self, row, col):
        if self._arb_udef_loading or col == 0 or row >= len(self._arb_udef_points):
            return
        item = self.arb_udef_table.item(row, col)
        text = item.text().strip()
        try:
            value = float(text)
        except ValueError:
            value = None
        if value is None or (col == 2 and value <= 0):
            # 非法输入回退模型值
            self._arb_udef_loading = True
            item.setText(f"{self._arb_udef_points[row][col - 1]:g}")
            self._arb_udef_loading = False
            return
        self._arb_udef_loading = True
        try:
            self._arb_udef_points[row][col - 1] = value
            sel_rows = self._arb_udef_selected_rows()
            if row in sel_rows and len(sel_rows) > 1:
                # Ctrl 多选：同列同步到所有选中行
                for r in sel_rows:
                    if r != row and r < len(self._arb_udef_points):
                        self._arb_udef_points[r][col - 1] = value
                        self.arb_udef_table.item(r, col).setText(f"{value:g}")
        finally:
            self._arb_udef_loading = False
        self._arb_store_current_params()
        self._arb_refresh_preview()

    def _arb_udef_on_table_selection(self):
        if self._arb_udef_loading or not hasattr(self, "arb_udef_table"):
            return
        self._arb_udef_selected = set(self._arb_udef_selected_rows())
        self._arb_refresh_preview()

    def _arb_udef_context_menu(self, pos):
        table = self.arb_udef_table
        row = table.rowAt(pos.y())
        menu = QMenu(self)
        insert_above = menu.addAction("Insert Above")
        insert_below = menu.addAction("Insert Below")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        edit_action = menu.addAction("Edit...")
        insert_above.setEnabled(row >= 0)
        insert_below.setEnabled(row >= 0)
        delete_action.setEnabled(bool(self._arb_udef_selected_rows()))
        edit_action.setEnabled(row >= 0)
        action = menu.exec(table.viewport().mapToGlobal(pos))
        if action is insert_above and row >= 0:
            self._arb_udef_insert_point(row)
        elif action is insert_below and row >= 0:
            self._arb_udef_insert_point(row + 1)
        elif action is delete_action:
            self._arb_udef_delete_selected()
        elif action is edit_action and row >= 0:
            self._arb_udef_edit_point_dialog(row)

    def _arb_udef_insert_point(self, row):
        row = max(0, min(row, len(self._arb_udef_points)))
        if self._arb_udef_points:
            ref = self._arb_udef_points[min(row, len(self._arb_udef_points) - 1)]
            point = [ref[0], ref[1]]
        else:
            point = [3.3, 0.001]
        self._arb_udef_points.insert(row, point)
        self._arb_udef_selected = {row}
        self._arb_udef_sync_table()
        self._arb_store_current_params()
        self._arb_refresh_preview()

    def _arb_udef_add_point(self):
        row = self.arb_udef_table.currentRow()
        self._arb_udef_insert_point(row + 1 if row >= 0 else len(self._arb_udef_points))

    def _arb_udef_delete_selected(self):
        rows = self._arb_udef_selected_rows()
        if not rows:
            return
        for row in reversed(rows):
            if row < len(self._arb_udef_points):
                del self._arb_udef_points[row]
        self._arb_udef_selected = set()
        self._arb_udef_sync_table()
        self._arb_store_current_params()
        self._arb_refresh_preview()

    def _arb_udef_clear_points(self):
        if not self._arb_udef_points:
            return
        self._arb_udef_points = []
        self._arb_udef_selected = set()
        self._arb_udef_sync_table()
        self._arb_store_current_params()
        self._arb_refresh_preview()

    def _arb_udef_edit_point_dialog(self, row):
        if row >= len(self._arb_udef_points):
            return
        unit = "V" if self._arb_current_type() == "VOLT" else "A"
        lv, dw = self._arb_udef_points[row]
        dialog = _UdefPointDialog(lv, dw, unit, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            level, dwell = dialog.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Arb Set", str(exc))
            return
        self._arb_udef_points[row] = [level, dwell]
        self._arb_udef_sync_table()
        self._arb_store_current_params()
        self._arb_refresh_preview()

    def _arb_udef_import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import User Defined Points", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        points = []
        arb_type = None
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                for line_no, line in enumerate(f, start=1):
                    lowered = line.strip().lower()
                    if lowered.startswith("%arbtype="):
                        # N6705C 面板导出格式：arbuservolt / arbusercurr
                        if "curr" in lowered:
                            arb_type = "CURR"
                        elif "volt" in lowered:
                            arb_type = "VOLT"
                        continue
                    if "current waveform" in lowered:
                        arb_type = "CURR"
                        continue
                    if "voltage waveform" in lowered:
                        arb_type = "VOLT"
                        continue
                    parts = [p.strip() for p in line.split(",") if p.strip()]
                    if not parts:
                        continue
                    try:
                        level = float(parts[0])
                        dwell = float(parts[1]) if len(parts) > 1 else 0.001
                    except ValueError:
                        continue  # 标题 / VALUE,TIME,TRIGGER 表头行
                    if dwell <= 0:
                        raise ValueError(f"Line {line_no}: dwell must be > 0")
                    points.append([level, dwell])
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Arb Set", f"Import failed: {exc}")
            return
        if not points:
            QMessageBox.warning(self, "Arb Set", "Import failed: no valid points found")
            return
        self._arb_udef_points = points
        self._arb_udef_selected = set()
        if arb_type is not None and arb_type != self._arb_current_type():
            type_keys = [k for k, _label in _ARB_TYPES]
            self.arb_type_combo.setCurrentIndex(type_keys.index(arb_type))
        self._arb_udef_sync_table()
        self._arb_store_current_params()
        self._arb_refresh_preview()
        logger.info("UDEF points imported: %s (%d points, type=%s)", path, len(points), arb_type)

    @staticmethod
    def _arb_udef_fmt_time(dwell):
        text = f"{float(dwell):.9f}".rstrip("0").rstrip(".")
        return text or "0"

    def _arb_udef_export_csv(self):
        if not self._arb_udef_points:
            QMessageBox.warning(self, "Arb Set", "No points to export")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export User Defined Points", "", "N6705C Arb CSV (*.csv);;All Files (*)"
        )
        if not path:
            return
        is_curr = self._arb_current_type() == "CURR"
        title = (
            "Arb User Defined Current Waveform"
            if is_curr
            else "Arb User Defined Voltage Waveform"
        )
        arbtype = "arbusercurr" if is_curr else "arbuservolt"
        try:
            with open(path, "w", encoding="utf-8") as f:
                # 与 N6705C 面板导出格式一致，可直接导回仪器
                f.write(f"{title},,\n")
                f.write(f"%arbtype={arbtype},,\n")
                f.write("VALUE,TIME,TRIGGER\n")
                for lv, dw in self._arb_udef_points:
                    f.write(f"{lv:.6f},{self._arb_udef_fmt_time(dw)},0\n")
        except OSError as exc:
            QMessageBox.warning(self, "Arb Set", f"Export failed: {exc}")
            return
        logger.info("UDEF points exported: %s (%d points)", path, len(self._arb_udef_points))

    # ------------------------------------------------- udef preview <-> table
    def _arb_udef_on_region_clicked(self, index, modifiers):
        if index >= len(self._arb_udef_points):
            return
        if modifiers & Qt.ControlModifier:
            sel = set(self._arb_udef_selected)
            sel ^= {index}
        else:
            sel = {index}
        self._arb_udef_selected = sel
        self._arb_udef_sync_table()
        self._arb_refresh_preview()

    def _arb_udef_on_region_changed(self, index, level, dwell):
        if index >= len(self._arb_udef_points):
            return
        self._arb_udef_points[index] = [level, dwell]
        self._arb_udef_loading = True
        try:
            self.arb_udef_table.item(index, 1).setText(f"{level:g}")
            self.arb_udef_table.item(index, 2).setText(f"{dwell:g}")
        finally:
            self._arb_udef_loading = False
        self._arb_store_current_params()
        self._arb_refresh_preview()

    def _arb_udef_on_region_edit(self, index):
        self._arb_udef_edit_point_dialog(index)

    def _arb_udef_load_from_saved(self, saved):
        """从 store / 预设记录恢复 UDEF 点模型（兼容 points / levels+dwells 两种结构）。"""
        if not isinstance(saved, dict):
            return
        points = None
        raw_points = saved.get("points")
        if isinstance(raw_points, list) and raw_points:
            try:
                points = [[float(p[0]), float(p[1])] for p in raw_points]
            except (TypeError, ValueError, IndexError):
                points = None
        if points is None and "levels" in saved:
            levels = saved.get("levels")
            dwells = saved.get("dwells")
            if isinstance(levels, str):
                levels = [p.strip() for p in levels.split(",") if p.strip()]
            if isinstance(dwells, str):
                dwells = [p.strip() for p in dwells.split(",") if p.strip()]
            try:
                levels = [float(v) for v in (levels or [])]
            except (TypeError, ValueError):
                levels = []
            if levels:
                if not isinstance(dwells, (list, tuple)) or len(dwells) != len(levels):
                    dwells = [0.001] * len(levels)
                else:
                    dwells = [max(float(d), 1e-4) for d in dwells]
                points = [[lv, dw] for lv, dw in zip(levels, dwells)]
        if points is None:
            return
        self._arb_udef_points = points
        self._arb_udef_selected = set()
        self._arb_udef_sync_table()

    # ------------------------------------------------------------ preset zone
    def _create_arb_preset_zone(self):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: {CONTAINER_RADIUS}; }}"
        )
        card.setMinimumWidth(220)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        title = QLabel("QUICK PRESETS")
        title.setStyleSheet(
            f"QLabel {{ color: {MUTED_TEXT}; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; border: none; }}"
        )
        layout.addWidget(title)

        self.arb_preset_list = QListWidget()
        self.arb_preset_list.setStyleSheet(f"""
            QListWidget {{
                background-color: #091426; color: #dbe6ff;
                border: 1px solid {CARD_BORDER}; border-radius: {WIDGET_RADIUS};
                font-size: 12px; outline: 0;
            }}
            QListWidget::item {{ padding: 5px 8px; }}
            QListWidget::item:selected {{ background-color: #1a2a50; color: #ffffff; }}
            QListWidget::item:hover {{ background-color: #12213f; }}
        """)
        self.arb_preset_list.itemClicked.connect(self._arb_on_preset_clicked)
        layout.addWidget(self.arb_preset_list, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.arb_preset_save_btn = QPushButton("Save")
        self.arb_preset_delete_btn = QPushButton("Delete")
        for btn in (self.arb_preset_save_btn, self.arb_preset_delete_btn):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #0b1730; color: #dbe6ff;
                    border: 1px solid #23417a; border-radius: {WIDGET_RADIUS};
                    font-size: 11px; padding: 4px 10px; min-height: 26px;
                }}
                QPushButton:hover {{ background-color: #10203e; }}
                QPushButton:disabled {{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
            """)
        self.arb_preset_save_btn.clicked.connect(self._arb_on_save_preset)
        self.arb_preset_delete_btn.clicked.connect(self._arb_on_delete_preset)
        btn_row.addWidget(self.arb_preset_save_btn, 1)
        btn_row.addWidget(self.arb_preset_delete_btn, 1)
        layout.addLayout(btn_row)
        return card

    # -------------------------------------------------------------- tab logic
    def _build_arb_tab_buttons(self):
        if not hasattr(self, "_arb_tabs_layout"):
            return
        for btn in self.arb_tab_buttons:
            self._arb_tabs_layout.removeWidget(btn)
            btn.deleteLater()
        self.arb_tab_buttons.clear()

        if self._arb_tab_separator is not None:
            self._arb_tabs_layout.removeWidget(self._arb_tab_separator)
            self._arb_tab_separator.deleteLater()
            self._arb_tab_separator = None

        while self._arb_tabs_layout.count():
            item = self._arb_tabs_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._arb_tabs_layout.setContentsMargins(0, 4, 0, 0)
        self._arb_tabs_layout.setSpacing(2)

        # 当前通道不可用时回退到第一个可用通道（未连接保持默认）
        connected = self._connected_device_labels()
        if connected and (
            self._arb_current_device not in connected
            or not self._is_channel_supported(self._arb_current_device, self._arb_current_channel)
        ):
            selected = next(
                (
                    (label, ch)
                    for label in connected
                    for ch in self._supported_channels_for_device(label)
                ),
                None,
            )
            if selected is not None:
                self._arb_current_device, self._arb_current_channel = selected
            elif self._arb_current_device not in connected:
                self._arb_current_device = connected[0]

        dual = self._is_dual_mode()
        if dual:
            for dev_label in ["A", "B"]:
                for ch in self._channels_for_device(dev_label):
                    self._arb_tabs_layout.addWidget(
                        self._make_arb_tab_button(f"\u25cf {dev_label}-CH{ch}", dev_label, ch)
                    )
                if dev_label == "A":
                    sep = QFrame()
                    sep.setFixedWidth(2)
                    sep.setFixedHeight(24)
                    sep.setStyleSheet("QFrame { background: #1b2847; border: none; }")
                    self._arb_tab_separator = sep
                    self._arb_tabs_layout.addWidget(sep)
        else:
            single_label = self._get_single_device_label()
            for ch in self._channels_for_device(single_label):
                self._arb_tabs_layout.addWidget(
                    self._make_arb_tab_button(f"\u25cf CH{ch}", single_label, ch)
                )

        self._arb_tabs_layout.addStretch()
        self._arb_load_channel_params()
        self._arb_apply_channel_theme()

    def _make_arb_tab_button(self, text, dev_label, ch):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setProperty("device_label", dev_label)
        btn.setProperty("channel", ch)
        btn.setMinimumSize(90, 36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setEnabled(self._is_channel_supported(dev_label, ch))
        btn.setToolTip(self._channel_module_tooltip(dev_label, ch))
        btn.clicked.connect(
            lambda checked=False, d=dev_label, c=ch: self._arb_switch_channel(d, c)
        )
        self.arb_tab_buttons.append(btn)
        return btn

    def _arb_switch_channel(self, dev_label, ch):
        if not self._is_channel_supported(dev_label, ch):
            return
        if dev_label == self._arb_current_device and ch == self._arb_current_channel:
            return
        self._arb_store_current_params()
        self._arb_current_device = dev_label
        self._arb_current_channel = ch
        self._arb_load_channel_params()
        self._arb_apply_channel_theme()
        self._arb_refresh_action_state()

    def _arb_tab_style(self, dev_label, ch, checked=False):
        """复用电压区通道 tab 样式（效果对齐），仅底线色取 Arb 选中通道。"""
        theme = self._channel_theme(self._arb_current_device, self._arb_current_channel)
        return self._build_channel_tab_style(
            dev_label, ch, checked, bar_border_color=theme["accent_border"]
        )

    def _refresh_arb_tab_styles(self):
        active_btn = None
        for btn in getattr(self, "arb_tab_buttons", []):
            dev_label = btn.property("device_label")
            ch = int(btn.property("channel"))
            is_active = (
                dev_label == self._arb_current_device
                and ch == self._arb_current_channel
                and self._is_channel_supported(dev_label, ch)
            )
            btn.setStyleSheet(self._arb_tab_style(dev_label, ch, is_active))
            btn.setChecked(is_active)
            if is_active:
                active_btn = btn
        QTimer.singleShot(0, lambda: self._update_arb_tab_bar_active_rect(active_btn))

    def _update_arb_tab_bar_active_rect(self, active_btn):
        if not hasattr(self, "_arb_tab_bar"):
            return
        if active_btn:
            self._arb_tab_bar.set_active_tab_rect(active_btn.geometry())
        else:
            self._arb_tab_bar.set_active_tab_rect(None)

    def _arb_apply_channel_theme(self):
        if not hasattr(self, "arb_body"):
            return
        theme = self._channel_theme(self._arb_current_device, self._arb_current_channel)
        accent_border = theme["accent_border"]

        if self._is_dual_mode():
            self.arb_ch_title.setText(
                f"{self._arb_current_device} - Channel {self._arb_current_channel}"
            )
        else:
            self.arb_ch_title.setText(f"Channel {self._arb_current_channel}")

        self.arb_body.setStyleSheet(f"""
            QFrame#ArbContentFrame {{
                background-color: {CONTENT_BG};
                border: 1px solid {accent_border};
                border-top: none;
                border-bottom-left-radius: {CONTAINER_RADIUS};
                border-bottom-right-radius: {CONTAINER_RADIUS};
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}
        """)
        self._arb_tab_bar.set_border_color(accent_border)
        self.arb_continuous_toggle.setAccentColor(theme["accent"])
        self._arb_update_radio_style()
        self._arb_update_run_btn()
        self._arb_refresh_shape_availability()
        self._arb_refresh_preview()
        self._refresh_arb_tab_styles()

    def _arb_update_radio_style(self):
        """结束方式单选指示器：未选中深色底+可见描边，选中通道 accent 填充。"""
        if not hasattr(self, "arb_term_dc_radio"):
            return
        theme = self._channel_theme(self._arb_current_device, self._arb_current_channel)
        accent = theme["accent"]
        qss = f"""
            QRadioButton {{ color: #dbe6ff; font-size: 11px; spacing: 6px; background: transparent; border: none; }}
            QRadioButton::indicator {{
                width: 13px; height: 13px;
                border: 1.5px solid #4a6aa0;
                border-radius: 8px;
                background-color: #0b1730;
            }}
            QRadioButton::indicator:hover {{ border: 1.5px solid {accent}; }}
            QRadioButton::indicator:checked {{
                border: 1.5px solid {accent};
                background-color: {accent};
            }}
            QRadioButton:disabled {{ color: {DISABLED_TEXT}; }}
            QRadioButton::indicator:disabled {{
                border: 1.5px solid #22304f; background-color: #0a1224;
            }}
        """
        self.arb_term_dc_radio.setStyleSheet(qss)
        self.arb_term_last_radio.setStyleSheet(qss)

    def _arb_update_run_btn(self):
        """按当前通道 Arb 运行态刷新合并按钮（RUN=主题色 / STOP=红）。"""
        if not hasattr(self, "arb_run_btn"):
            return
        running = (self._arb_current_device, self._arb_current_channel) in self._arb_running
        if running:
            self.arb_run_btn.setText("\u25a0  STOP")
            self.arb_run_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2a0a1c; color: #ff4fa3;
                    border: 1px solid #d63384; border-radius: {WIDGET_RADIUS};
                    font-size: 12px; min-height: 32px; font-weight: 700;
                }}
                QPushButton:hover {{ background-color: #3a1028; }}
                QPushButton:disabled {{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
            """)
        else:
            theme = self._channel_theme(self._arb_current_device, self._arb_current_channel)
            self.arb_run_btn.setText("\u25b6  RUN")
            self.arb_run_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #0c1a38; color: {theme['accent']};
                    border: 1px solid {theme['accent']}; border-radius: {WIDGET_RADIUS};
                    font-size: 12px; min-height: 32px; font-weight: 700;
                }}
                QPushButton:hover {{ background-color: #12213f; color: {theme['accent_hover']}; border: 1px solid {theme['accent_hover']}; }}
                QPushButton:disabled {{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
            """)

    # --------------------------------------------------- type / shape / units
    def _arb_current_type(self):
        return _ARB_TYPES[self.arb_type_combo.currentIndex()][0]

    def _arb_current_shape_key(self):
        idx = self.arb_shape_combo.currentIndex()
        return _ARB_SHAPES[idx][0]

    def _arb_on_type_changed(self, _index):
        if self._arb_loading:
            return
        self._arb_update_unit_labels()
        self._arb_store_current_params()
        self._arb_refresh_preview()

    def _arb_on_shape_changed(self, index):
        new_shape = _ARB_SHAPES[index][0]
        old_shape = self._arb_last_shape
        self._arb_last_shape = new_shape
        if old_shape != new_shape:
            # 滚轮调值走 setText（仅 textChanged），切走前全量保存旧页
            self._arb_store_shape_params(old_shape)
        self.arb_params_stack.setCurrentIndex(index)
        if not self._arb_loading:
            self._arb_load_shape_params(new_shape)
            self._arb_store_current_params()
        self._arb_refresh_preview()

    def _arb_update_unit_labels(self):
        unit = "V" if self._arb_current_type() == "VOLT" else "A"
        for shape_labels in self.arb_param_labels.values():
            for label, tpl in shape_labels:
                label.setText(tpl.replace("{u}", unit))
        if hasattr(self, "arb_udef_table"):
            self.arb_udef_table.setHorizontalHeaderLabels(
                ["#", f"Level ({unit})", "Dwell (s)"]
            )

    def _arb_refresh_preview(self):
        """按当前参数刷新波形示意图；No Arb 时隐藏，非法输入保留上一有效图形。"""
        if not hasattr(self, "arb_wave_preview"):
            return
        shape = self._arb_current_shape_key()
        self.arb_wave_preview.setVisible(shape != "none")
        if shape == "udef":
            self.arb_wave_preview.set_udef_interaction(
                True, self._arb_udef_points, self._arb_udef_selected
            )
        else:
            self.arb_wave_preview.set_udef_interaction(False, [], set())
        try:
            values = self._arb_collect_values()
        except ValueError:
            return
        theme = self._channel_theme(self._arb_current_device, self._arb_current_channel)
        self.arb_wave_preview.set_config(
            shape, values, self._arb_current_type(), theme["accent"]
        )

    def _arb_refresh_shape_availability(self):
        """按当前通道仪器型号禁用不支持的波形（SEQ 全局占位禁用）。"""
        if not hasattr(self, "arb_shape_combo"):
            return
        instance = self.devices.get(self._arb_current_device, {}).get("n6705c")
        is_it2705 = bool(instance is not None and is_it2705_instrument(instance))
        model = self.arb_shape_combo.model()
        current_key = self._arb_current_shape_key()
        need_fallback = False
        for idx, (key, _label, _icon) in enumerate(_ARB_SHAPES):
            item = model.item(idx)
            if item is None:
                continue
            disabled = key in _ARB_PLACEHOLDER_SHAPES or (
                is_it2705 and key in _ARB_IT2705_UNSUPPORTED
            )
            item.setEnabled(not disabled)
            if disabled:
                reason = (
                    "Sequence editing will be available in a future release"
                    if key == "seq"
                    else "Not supported by IT2705"
                )
                item.setToolTip(reason)
            else:
                item.setToolTip("")
            if disabled and key == current_key:
                need_fallback = True
        if need_fallback:
            self._arb_loading = True
            try:
                self.arb_shape_combo.setCurrentIndex(0)  # none
                self.arb_params_stack.setCurrentIndex(0)
                self._arb_last_shape = "none"
            finally:
                self._arb_loading = False
            self._arb_refresh_preview()

    # --------------------------------------------------------- params memory
    def _arb_on_continuous_toggled(self, checked):
        self.arb_repeat_input.setEnabled(not checked)
        self._arb_store_current_params()

    def _arb_on_terminate_toggled(self, _checked):
        self._arb_store_current_params()

    def _arb_store_shape_params(self, shape):
        if self._arb_loading or not hasattr(self, "arb_shape_combo"):
            return
        if shape == "udef":
            params = {"points": [list(p) for p in self._arb_udef_points]}
        else:
            params = {
                field_key: edit.text()
                for field_key, edit in self.arb_param_inputs[shape].items()
            }
        key = (self._arb_current_device, self._arb_current_channel)
        entry = self._arb_param_store.setdefault(key, {"params": {}})
        entry["arb_type"] = self._arb_current_type()
        entry["shape"] = self._arb_current_shape_key()
        entry["continuous"] = self.arb_continuous_toggle.isChecked()
        entry["repeat_count"] = self.arb_repeat_input.text()
        entry["terminate_last"] = self.arb_term_last_radio.isChecked()
        entry["params"][shape] = params

    def _arb_store_current_params(self):
        self._arb_store_shape_params(self._arb_current_shape_key())

    def _arb_load_shape_params(self, shape):
        """从当前通道 store 恢复指定波形页的已存值（无记录则保留默认）。"""
        key = (self._arb_current_device, self._arb_current_channel)
        saved = self._arb_param_store.get(key, {}).get("params", {}).get(shape, {})
        if not saved:
            return
        if shape == "udef":
            self._arb_udef_load_from_saved(saved)
            return
        prev = self._arb_loading
        self._arb_loading = True
        try:
            for field_key, edit in self.arb_param_inputs[shape].items():
                if field_key in saved:
                    edit.setText(str(saved[field_key]))
        finally:
            self._arb_loading = prev

    def _arb_load_channel_params(self):
        if not hasattr(self, "arb_shape_combo"):
            return
        self._arb_loading = True
        try:
            key = (self._arb_current_device, self._arb_current_channel)
            entry = self._arb_param_store.get(key, {})
            arb_type = entry.get("arb_type", "VOLT")
            type_keys = [k for k, _label in _ARB_TYPES]
            if arb_type not in type_keys:
                arb_type = "VOLT"
            self.arb_type_combo.setCurrentIndex(type_keys.index(arb_type))
            shape = entry.get("shape", "none")
            shape_keys = [k for k, _label, _icon in _ARB_SHAPES]
            if shape not in shape_keys:
                shape = "none"
            self.arb_shape_combo.setCurrentIndex(shape_keys.index(shape))
            self.arb_params_stack.setCurrentIndex(shape_keys.index(shape))
            self.arb_continuous_toggle.setChecked(bool(entry.get("continuous", False)))
            self.arb_repeat_input.setText(str(entry.get("repeat_count", "1")))
            self.arb_repeat_input.setEnabled(not self.arb_continuous_toggle.isChecked())
            self.arb_term_last_radio.setChecked(bool(entry.get("terminate_last", False)))
            saved = entry.get("params", {}).get(shape, {})
            if shape == "udef":
                self._arb_udef_load_from_saved(saved)
            else:
                for field_key, edit in self.arb_param_inputs[shape].items():
                    if field_key in saved:
                        edit.setText(str(saved[field_key]))
            self._arb_last_shape = shape
        finally:
            self._arb_loading = False
        self._arb_update_unit_labels()
        self._arb_refresh_shape_availability()
        self._arb_refresh_preview()

    def _arb_collect_values(self):
        """解析当前波形参数为数值；非法输入抛 ValueError。"""
        shape = self._arb_current_shape_key()
        if shape == "udef":
            if not self._arb_udef_points:
                raise ValueError("User Defined requires at least one point")
            return {
                "levels": [p[0] for p in self._arb_udef_points],
                "dwells": [p[1] for p in self._arb_udef_points],
            }
        values = {}
        for label_tpl, field_key, _default, _step, kind in _ARB_FIELDS[shape]:
            text = self.arb_param_inputs[shape][field_key].text().strip()
            unit = "V" if self._arb_current_type() == "VOLT" else "A"
            label = label_tpl.replace("{u}", unit)
            if kind in ("list_level", "list_time"):
                if not text:
                    if kind == "list_time":
                        values[field_key] = None
                        continue
                    raise ValueError(f"{label.rstrip(':')} requires at least one value")
                try:
                    values[field_key] = [
                        float(part) for part in text.split(",") if part.strip()
                    ]
                except ValueError as exc:
                    raise ValueError(f"{label.rstrip(':')} invalid list: '{text}'") from exc
                if not values[field_key]:
                    if kind == "list_time":
                        values[field_key] = None
                        continue
                    raise ValueError(f"{label.rstrip(':')} requires at least one value")
            else:
                try:
                    values[field_key] = float(text)
                except ValueError as exc:
                    raise ValueError(f"{label.rstrip(':')} invalid: '{text}'") from exc
        if shape == "staircase":
            values["steps"] = int(values["steps"])
        return values

    # ------------------------------------------------------------ apply/stop
    def _arb_io_lock(self, dev_label):
        if not self._instrument_manager:
            return None
        getter = getattr(self._instrument_manager, "io_lock", None)
        if not callable(getter):
            return None
        return getter(f"n6705c:{dev_label}")

    def _arb_on_run_stop_clicked(self):
        key = (self._arb_current_device, self._arb_current_channel)
        if key in self._arb_running:
            self._arb_stop()
        else:
            self._arb_apply()

    def _arb_apply(self):
        dev_label = self._arb_current_device
        ch = self._arb_current_channel
        dev = self.devices.get(dev_label, {})
        instance = dev.get("n6705c")
        if not dev.get("is_connected") or instance is None:
            return
        if not self._is_channel_supported(dev_label, ch) or dev_label in self._arb_threads:
            return
        shape = self._arb_current_shape_key()
        if shape in _ARB_PLACEHOLDER_SHAPES:
            return
        try:
            values = self._arb_collect_values()
            continuous = self.arb_continuous_toggle.isChecked()
            repeat_count = None
            if not continuous:
                repeat_count = int(float(self.arb_repeat_input.text().strip()))
                if repeat_count < 1:
                    raise ValueError("Repeat Count must be >= 1")
        except ValueError as exc:
            QMessageBox.warning(self, "Arb Set", str(exc))
            return
        self._arb_store_current_params()
        self._arb_start_worker(dev_label, instance, ch, "apply",
                               shape_key=shape,
                               values=values,
                               arb_type=self._arb_current_type(),
                               continuous=continuous,
                               repeat_count=repeat_count,
                               terminate_last=self.arb_term_last_radio.isChecked())

    def _arb_stop(self):
        dev_label = self._arb_current_device
        ch = self._arb_current_channel
        dev = self.devices.get(dev_label, {})
        instance = dev.get("n6705c")
        if not dev.get("is_connected") or instance is None or dev_label in self._arb_threads:
            return
        self._arb_start_worker(dev_label, instance, ch, "stop")

    def _arb_start_worker(self, dev_label, instance, ch, mode, **kwargs):
        worker = _ArbRunWorker(
            instance, dev_label, ch, mode, io_lock=self._arb_io_lock(dev_label), **kwargs
        )
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._arb_on_run_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(
            lambda lb=dev_label: self._arb_on_thread_cleaned(lb)
        )
        self._arb_threads[dev_label] = thread
        self._arb_workers[dev_label] = worker
        self._arb_refresh_action_state()
        thread.start()

    def _arb_on_thread_cleaned(self, dev_label):
        self._arb_workers.pop(dev_label, None)
        self._arb_threads.pop(dev_label, None)
        self._arb_refresh_action_state()

    def _arb_on_run_finished(self, dev_label, channel, mode, success, message):
        if success:
            key = (dev_label, channel)
            if mode == "apply":
                self._arb_running.add(key)
            else:
                self._arb_running.discard(key)
        else:
            QMessageBox.warning(self, "Arb Set", message)
        self._arb_refresh_action_state()

    def _arb_refresh_action_state(self):
        if not hasattr(self, "arb_run_btn"):
            return
        dev = self.devices.get(self._arb_current_device, {})
        connected = bool(dev.get("is_connected"))
        if not connected:
            # 断连即失效的本地运行态记录
            self._arb_running = {
                key for key in self._arb_running if key[0] != self._arb_current_device
            }
        supported = self._is_channel_supported(self._arb_current_device, self._arb_current_channel)
        busy = self._arb_current_device in self._arb_threads
        self.arb_run_btn.setEnabled(connected and supported and not busy)
        self._arb_update_run_btn()

    # ---------------------------------------------------------------- presets
    def _arb_load_presets(self):
        path = _arb_presets_path()
        presets = []
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f) or {}
                if isinstance(raw.get("presets"), list):
                    presets = [p for p in raw["presets"] if isinstance(p, dict) and p.get("name")]
            except (OSError, json.JSONDecodeError):
                logger.error("读取 arb_presets.json 失败: %s", path, exc_info=True)
        self._arb_presets = [self._arb_normalize_preset(p) for p in presets]
        self._arb_refresh_preset_list()

    @staticmethod
    def _arb_normalize_preset(preset):
        """旧版 pulse_v/pulse_i 与旧字段名映射到新结构。"""
        preset = dict(preset)
        shape = preset.get("shape", "none")
        if shape in _LEGACY_SHAPE_MAP:
            shape, arb_type = _LEGACY_SHAPE_MAP[shape]
            preset.setdefault("arb_type", arb_type)
        preset["shape"] = shape
        preset.setdefault("arb_type", "VOLT")
        params = preset.get("params")
        if isinstance(params, dict):
            preset["params"] = {
                _LEGACY_FIELD_MAP.get(k, k): v for k, v in params.items()
            }
        return preset

    def _arb_save_presets(self):
        path = _arb_presets_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"presets": self._arb_presets}, f, ensure_ascii=False, indent=2)
        except OSError:
            logger.error("写入 arb_presets.json 失败: %s", path, exc_info=True)

    def _arb_refresh_preset_list(self):
        if not hasattr(self, "arb_preset_list"):
            return
        self.arb_preset_list.clear()
        for preset in self._arb_presets:
            item = QListWidgetItem(str(preset.get("name", "")))
            item.setToolTip(self._arb_preset_summary(preset))
            self.arb_preset_list.addItem(item)

    def _arb_preset_summary(self, preset):
        shape = preset.get("shape", "")
        shape_label = {k: lbl for k, lbl, _i in _ARB_SHAPES}.get(shape, shape)
        type_label = dict(_ARB_TYPES).get(preset.get("arb_type", "VOLT"), "Voltage")
        params = preset.get("params", {})
        parts = [f"{k}={v}" for k, v in params.items()]
        cont = "continuous" if preset.get("continuous") else "single"
        return f"{shape_label} | {type_label} | {cont} | {', '.join(parts)}"

    def _arb_on_save_preset(self):
        try:
            values = self._arb_collect_values()
        except ValueError as exc:
            QMessageBox.warning(self, "Arb Set", str(exc))
            return
        name, ok = QInputDialog.getText(self, "Save Arb Preset", "Preset name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        preset = {
            "name": name,
            "arb_type": self._arb_current_type(),
            "shape": self._arb_current_shape_key(),
            "continuous": self.arb_continuous_toggle.isChecked(),
            "repeat_count": self.arb_repeat_input.text(),
            "terminate_last": self.arb_term_last_radio.isChecked(),
            "params": values,
        }
        self._arb_presets = [p for p in self._arb_presets if p.get("name") != name]
        self._arb_presets.append(preset)
        self._arb_save_presets()
        self._arb_refresh_preset_list()
        logger.info("Arb preset saved: %s", name)

    def _arb_on_delete_preset(self):
        row = self.arb_preset_list.currentRow()
        if row < 0 or row >= len(self._arb_presets):
            return
        name = self._arb_presets[row].get("name", "")
        del self._arb_presets[row]
        self._arb_save_presets()
        self._arb_refresh_preset_list()
        logger.info("Arb preset deleted: %s", name)

    def _arb_on_preset_clicked(self, item):
        row = self.arb_preset_list.row(item)
        if row < 0 or row >= len(self._arb_presets):
            return
        preset = self._arb_presets[row]
        shape = preset.get("shape", "none")
        shape_keys = [k for k, _label, _icon in _ARB_SHAPES]
        if shape not in shape_keys:
            return
        self._arb_loading = True
        try:
            arb_type = preset.get("arb_type", "VOLT")
            type_keys = [k for k, _label in _ARB_TYPES]
            self.arb_type_combo.setCurrentIndex(
                type_keys.index(arb_type) if arb_type in type_keys else 0
            )
            self.arb_shape_combo.setCurrentIndex(shape_keys.index(shape))
            self.arb_params_stack.setCurrentIndex(shape_keys.index(shape))
            self.arb_continuous_toggle.setChecked(bool(preset.get("continuous", False)))
            self.arb_repeat_input.setText(str(preset.get("repeat_count", "1")))
            self.arb_repeat_input.setEnabled(not self.arb_continuous_toggle.isChecked())
            self.arb_term_last_radio.setChecked(bool(preset.get("terminate_last", False)))
            params = preset.get("params", {})
            if shape == "udef":
                self._arb_udef_load_from_saved(params)
            else:
                for field_key, edit in self.arb_param_inputs[shape].items():
                    if field_key in params and params[field_key] is not None:
                        value = params[field_key]
                        if isinstance(value, list):
                            edit.setText(", ".join(str(v) for v in value))
                        else:
                            edit.setText(str(value))
            self._arb_last_shape = shape
        finally:
            self._arb_loading = False
        self._arb_update_unit_labels()
        self._arb_refresh_preview()
        self._arb_store_current_params()
