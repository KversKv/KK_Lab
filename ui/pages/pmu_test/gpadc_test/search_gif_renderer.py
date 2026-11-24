"""GPADC Auto Best 搜索 GIF 离屏帧渲染（仅 GUI 线程调用）。"""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter

from core.pmu_test.gpadc import build_linearity_auto_search_timeline


class SearchGifFrameRenderer:
    WIDTH = 1200
    HEIGHT = 760
    PALETTE = (
        "#5b9cf5", "#f0a040", "#a78bfa", "#34d399",
        "#fb923c", "#60a5fa", "#e05c5c", "#00d39a",
    )

    def __init__(self, result):
        self.result = result
        self.events = build_linearity_auto_search_timeline(result)
        self.group_by_value = {
            int(group["n_value"]): group for group in result.get("groups") or []
        }
        self.search_range = (
            int(result["auto_search"]["start"]), int(result["auto_search"]["end"]),
        )
        self.voltage_range = self._collect_voltage_range()
        self.error_range = self._collect_error_range()
        self.metric_range = self._collect_metric_range()

    def __len__(self):
        return len(self.events)

    @staticmethod
    def _padded_range(values, include_zero=False):
        values = [float(value) for value in values]
        if include_zero:
            values.append(0.0)
        low, high = min(values), max(values)
        padding = max(1e-6, (high - low) * 0.08 if high > low else max(1.0, abs(low) * 0.05))
        return low - padding, high + padding

    def _collect_voltage_range(self):
        values = []
        for group in self.group_by_value.values():
            values.extend((group.get("raw") or {}).get("voltage") or [])
        return self._padded_range(values or [0.0, 1.0])

    def _collect_error_range(self):
        values = []
        for group in self.group_by_value.values():
            values.extend(group.get("error_mv") or [])
        return self._padded_range(values or [0.0, 1.0], include_zero=True)

    def _collect_metric_range(self):
        return self._padded_range([
            group["max_abs_mv"] for group in self.group_by_value.values()
        ] or [0.0, 1.0], include_zero=True)

    def _new_plot(self, left_label, bottom_label):
        widget = pg.PlotWidget()
        widget.setBackground("#0a1735")
        widget.showGrid(x=True, y=True, alpha=0.15)
        widget.setLabel("left", left_label, color="#a0b4d8")
        widget.setLabel("bottom", bottom_label, color="#a0b4d8")
        widget.plotItem.vb.setMenuEnabled(False)
        for axis_name in ("left", "bottom"):
            axis = widget.getAxis(axis_name)
            axis.setTextPen(pg.mkPen("#a0b4d8"))
            axis.setPen(pg.mkPen("#3a4f7a"))
        return widget

    def _error_plot(self, event):
        widget = self._new_plot("Error (mV)", "Input Voltage (V)")
        widget.setXRange(*self.voltage_range, padding=0)
        widget.setYRange(*self.error_range, padding=0)
        widget.addLine(y=0, pen=pg.mkPen("#7e96bf", width=1, style=Qt.DashLine))
        current_value = event.get("value") if event["kind"] == "candidate" else None
        for index, value in enumerate(event["evaluated_values"]):
            group = self.group_by_value[value]
            raw = group.get("raw") or {}
            x = np.asarray(raw.get("voltage") or self.result.get("voltage") or [], dtype=float)
            y = np.asarray(group.get("error_mv") or [], dtype=float)
            count = min(len(x), len(y))
            if not count:
                continue
            is_best = value == event["best_value"]
            is_current = value == current_value
            color = QColor("#00d39a" if is_best else self.PALETTE[index % len(self.PALETTE)])
            if not is_best and not is_current:
                color.setAlpha(85)
            width = 3 if is_best else (2 if is_current else 1)
            widget.plot(
                x[:count], y[:count], pen=pg.mkPen(color, width=width),
                symbol="o" if is_best or is_current else None,
                symbolSize=6 if is_best else 4, symbolBrush=color, symbolPen=None,
            )
        return widget

    def _search_plot(self, event):
        widget = self._new_plot("Median Max Abs Error (mV)", "N/P Value (decimal)")
        low, high = self.search_range
        padding = max(0.5, (high - low) * 0.03)
        widget.setXRange(low - padding, high + padding, padding=0)
        widget.setYRange(*self.metric_range, padding=0)
        values = list(event["evaluated_values"])
        x = np.asarray(values, dtype=float)
        y = np.asarray([self.group_by_value[value]["max_abs_mv"] for value in values], dtype=float)
        widget.plot(
            x, y, pen=pg.mkPen("#5b9cf5", width=2),
            symbol="o", symbolSize=6, symbolBrush="#5b9cf5", symbolPen=None,
        )
        for boundary in event["interval"]:
            widget.addItem(pg.InfiniteLine(
                pos=boundary, angle=90, movable=False,
                pen=pg.mkPen("#00d39a", width=1, style=Qt.DashLine),
            ))
        if event["kind"] == "comparison":
            for boundary in event["previous_interval"]:
                widget.addItem(pg.InfiniteLine(
                    pos=boundary, angle=90, movable=False,
                    pen=pg.mkPen("#7e96bf", width=1, style=Qt.DotLine),
                ))
        best = event["best_value"]
        widget.addItem(pg.ScatterPlotItem(
            [best], [self.group_by_value[best]["max_abs_mv"]],
            symbol="o", size=14, brush="#00d39a", pen=pg.mkPen("#ffffff", width=1),
        ))
        if event["kind"] == "candidate":
            current = event["value"]
            widget.addItem(pg.ScatterPlotItem(
                [current], [self.group_by_value[current]["max_abs_mv"]],
                symbol="o", size=11, brush="#f0a040", pen=pg.mkPen("#f0a040", width=2),
            ))
        return widget

    @staticmethod
    def _export_plot(widget, width, height):
        widget.resize(width, height)
        exporter = ImageExporter(widget.plotItem)
        exporter.parameters()["width"] = width
        image = exporter.export(toBytes=True)
        if not isinstance(image, QImage):
            image = QImage.fromData(bytes(image))
        return image

    @staticmethod
    def _draw_text(painter, rect, text, color="#a0b4d8", bold=False, size=10, align=None):
        font = QFont("Segoe UI", size)
        font.setBold(bold)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(rect, align or (Qt.AlignLeft | Qt.AlignVCenter), text)

    def render_image(self, event, event_index=0):
        error_image = self._export_plot(self._error_plot(event), 1160, 370)
        search_image = self._export_plot(self._search_plot(event), 1160, 220)
        image = QImage(self.WIDTH, self.HEIGHT, QImage.Format_RGB888)
        image.fill(QColor("#071126"))
        painter = QPainter(image)
        try:
            self._draw_text(
                painter, QRect(20, 8, 850, 32), "GPADC Auto Best Search",
                color="#ffffff", bold=True, size=17,
            )
            self._draw_text(
                painter, QRect(900, 8, 280, 32), f"Frame {event_index + 1}/{len(self.events)}",
                bold=True, size=11, align=Qt.AlignRight | Qt.AlignVCenter,
            )
            if event["kind"] == "candidate":
                group = event["group"]
                status = (
                    f"Candidate N=P=0x{event['value']:X}  |  "
                    f"Representative Repeat {group.get('representative_repeat', 1)}/"
                    f"{group.get('repeat_count', 1)}  |  "
                    f"Median Max Abs {group['max_abs_mv']:.2f} mV  |  "
                    f"Median RMS {group['rms_mv']:.2f} mV"
                )
            else:
                comparison = event["comparison"]
                status = (
                    f"Keep [{event['interval'][0]:#X}, {event['interval'][1]:#X}]  |  "
                    f"Direction {comparison['direction'].upper()}  |  "
                    f"Noise tie: {'YES' if comparison.get('ambiguous') else 'NO'}"
                )
            if event.get("is_final"):
                best = self.group_by_value[event["best_value"]]
                status = (
                    f"BEST N=P=0x{event['best_value']:X}  |  "
                    f"Max Abs {best['max_abs_mv']:.2f} mV  |  RMS {best['rms_mv']:.2f} mV  |  "
                    + ("SEARCH COMPLETE" if event["completed"] else "BEST EVALUATED - SEARCH INCOMPLETE")
                )
            self._draw_text(painter, QRect(20, 42, 1160, 28), status, bold=True, size=10)
            low, high = event["interval"]
            interval = (
                f"Search interval: [{low:#X}, {high:#X}]  |  "
                f"Current best: N=P=0x{event['best_value']:X}"
            )
            self._draw_text(painter, QRect(20, 70, 1160, 26), interval, size=10)
            painter.drawImage(QRect(20, 100, 1160, 370), error_image)
            painter.drawImage(QRect(20, 480, 1160, 220), search_image)
            self._draw_text(
                painter, QRect(20, 710, 1160, 30),
                "Top: representative Repeat Error curves  |  Bottom: true candidate evaluation order",
                size=9, align=Qt.AlignCenter,
            )
        finally:
            painter.end()
        return image

    def render_event(self, event_index):
        event = self.events[event_index]
        image = self.render_image(event, event_index).convertToFormat(QImage.Format_RGB888)
        data = bytes(image.bits())[:image.sizeInBytes()]
        duration = 2800 if event.get("is_final") else (1000 if event["kind"] == "comparison" else 700)
        return data, image.width(), image.height(), image.bytesPerLine(), duration
