#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# run cmd:
# python ui\pages\n6705c_power_analyzer\n6705c_datalog_ui.py


import sys
import os

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from ui.resource_path import get_resource_base

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

sys.path.append(get_resource_base())

# 拆分后实现位于 datalog/ 子包；此处保留旧入口的导入面兼容 re-export。
from ui.pages.n6705c_power_analyzer.datalog.helpers import (
    _make_svg_icon,
    CHANNEL_COLORS,
    CHANNEL_LABEL_COLORS,
    VOLTAGE_COLORS,
    POWER_COLORS,
    EXTRA_MARKER_COLORS,
    _BAND_CEILING,
    _ANN_DEFAULT_FONT,
    _ANN_FONT_SIZES,
    _MEAS_AVG_FG,
    _MEAS_AVG_BG,
    _SUMMARY_STAGE_COLORS,
    _SUMMARY_STAGE_NAMES,
    _parse_ch_label,
    _display_label,
    _color_for_label,
    _sort_key_for_label,
    _parse_value_with_unit,
    _unit_for_label,
    _format_value,
    _format_time,
    _auto_format,
    _summary_fmt_time,
    _summary_unit_factor,
    _build_summary_stages,
    _render_waveform_summary_image,
)
from ui.pages.n6705c_power_analyzer.datalog.widgets import (
    PairAnnotationItem,
    ToggleLabel,
    ScaleOffsetEdit,
    ChannelNameLabel,
    ChannelConfigTabBar,
    CardFrame,
    ClickableHeader,
    FixedPopupComboBox,
)
from ui.pages.n6705c_power_analyzer.datalog.workers import (
    _ScanWorker,
    _ConnectWorker,
    _DatalogWorker,
)
from ui.pages.n6705c_power_analyzer.datalog.datalog_ui import N6705CDatalogUI
from ui.pages.n6705c_power_analyzer.datalog.standalone import _StandaloneTitleBar, _StandaloneDatalogWindow


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    from PySide6.QtGui import QIcon

    def _msg_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return

    qInstallMessageHandler(_msg_handler)
    app = QApplication(sys.argv)

    # Set application icon for taskbar and window
    _icon_path = os.path.join(get_resource_base(), "resources", "icons", "n6705c.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget {
            background-color: #030b23;
            color: #eaf1ff;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            font-size: 14px;
        }
        QPushButton {
            border: 1px solid #555;
            border-radius: 2px;
            padding: 6px 12px;
            background-color: #32353a;
            color: #c8c8c8;
        }
        QPushButton:hover { background-color: #3a3d43; }
        QPushButton:pressed { background-color: #2a2d32; }
        QPushButton:disabled { background-color: #2a2d32; color: #666; }
        QComboBox {
            border: 1px solid #555;
            border-radius: 2px;
            padding: 4px 20px 4px 8px;
            background-color: #32353a;
            color: #c8c8c8;
        }
        QComboBox QAbstractItemView {
            background-color: #32353a;
            color: #c8c8c8;
            border: 1px solid #555;
            selection-background-color: #4a4d52;
            outline: 0px;
        }
        QLineEdit {
            border: 1px solid #555;
            border-radius: 2px;
            padding: 4px 8px;
            background-color: #32353a;
            color: #c8c8c8;
        }
        QLabel { color: #c8c8c8; }
        QCheckBox { color: #c8c8c8; }
        QFrame {
            border: 1px solid #333;
            border-radius: 2px;
            background-color: #020618;
        }
    """)

    from core.instruments import InstrumentManager
    _standalone_manager = InstrumentManager()
    w = _StandaloneDatalogWindow(instrument_manager=_standalone_manager)
    w.setWindowTitle("N6705C Datalog")
    if os.path.exists(_icon_path):
        w.setWindowIcon(QIcon(_icon_path))
    w.apply_window_geometry()
    if getattr(w, "_restore_maximized", False):
        w.showMaximized()
    else:
        w.show()
    sys.exit(app.exec())
