"""GPADC Band 子图冒烟测试：验证主图 + Band 子图绘制与快照合成链路。

临时调试脚本：离屏渲染 _plot_voltage_adc_curve 的核心 pyqtgraph 调用，
验证 setXLink / FillBetweenItem / ImageExporter / QImage 纵向合成。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

app = QApplication.instance() or QApplication(sys.argv)

import io
import numpy as np
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter, QColor

# 模拟数据：0~5V 宽测试范围，band 宽度 ~3mV（旧实现叠加在主图上几乎不可见）
x = np.linspace(0.0, 5.0, 51)
y = x + 0.002 * np.sin(x * 3.0)
y_max = y + 0.0015
y_min = y - 0.0015

dev_hi = (y_max - y) * 1000.0
dev_lo = (y_min - y) * 1000.0

container = QWidget()
layout = QVBoxLayout(container)

pw = pg.PlotWidget()
pw.setBackground("#0a1735")
pw.showGrid(x=True, y=True, alpha=0.15)
pw.setLabel("left", "Calibrated Voltage (V)", color="#a0b4d8")
pw.setLabel("bottom", "Input Voltage (V)", color="#a0b4d8")
pw.plot(x, x, pen=pg.mkPen(color="#7e96bf", width=1, style=pg.QtCore.Qt.DashLine))
pw.plot(x, y, pen=pg.mkPen(color="#00d39a", width=2), symbol="o", symbolSize=5,
        symbolBrush="#00d39a", symbolPen=None)

pw_band = pg.PlotWidget()
pw_band.setBackground("#0a1735")
pw_band.showGrid(x=True, y=True, alpha=0.15)
pw_band.setLabel("left", "Max/Min Deviation (mV)", color="#f0a040")
pw_band.plotItem.setXLink(pw.plotItem)
pw_band.addLine(y=0, pen=pg.mkPen("#7e96bf", width=1, style=pg.QtCore.Qt.DashLine))
pw_band.addItem(pg.FillBetweenItem(
    pg.PlotDataItem(x, dev_hi),
    pg.PlotDataItem(x, dev_lo),
    brush=pg.mkBrush(240, 160, 64, 50),
))
pw_band.plot(x, dev_hi, pen=pg.mkPen(color="#f0a040", width=1, style=pg.QtCore.Qt.DashLine))
pw_band.plot(x, dev_lo, pen=pg.mkPen(color="#f0a040", width=1, style=pg.QtCore.Qt.DashLine))

layout.addWidget(pw, 3)
layout.addWidget(pw_band, 1)
container.resize(900, 500)
container.show()


def _snapshot(item, width=1200):
    exporter = ImageExporter(item)
    exporter.parameters()['width'] = width
    snap = exporter.export(toBytes=True)
    if not isinstance(snap, QImage):
        snap = QImage.fromData(bytes(snap))
    return snap


img_main = _snapshot(pw.plotItem)
img_band = _snapshot(pw_band.plotItem)
combined = QImage(img_main.width(), img_main.height() + img_band.height(), QImage.Format_ARGB32)
combined.fill(QColor(10, 23, 53))
painter = QPainter(combined)
painter.drawImage(0, 0, img_main)
painter.drawImage(0, img_main.height(), img_band)
painter.end()

qbuf = QBuffer()
qbuf.open(QIODevice.WriteOnly)
assert combined.save(qbuf, "PNG")
raw = bytes(qbuf.data())
qbuf.close()
buf = io.BytesIO(raw)

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpadc_band_chart_preview.png")
with open(out_path, "wb") as f:
    f.write(buf.getvalue())

print(f"OK: main={img_main.width()}x{img_main.height()}, "
      f"band={img_band.width()}x{img_band.height()}, "
      f"combined={combined.width()}x{combined.height()}, png={len(raw)} bytes")
print(f"preview saved: {out_path}")
