#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N6705CSuiteWindow 冒烟：建窗 → 切换两页 → 自动关闭。"""

import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from ui.pages.power_anaalyzer.power_anaalyzer_suite_ui import (
    N6705CSuiteWindow, N6705CTop,
)


@pytest.mark.qt
def test_it2705_eight_channel_ui_and_model(monkeypatch):
    from instruments.mock.mock_instruments import MockIT2705
    from ui.pages.power_anaalyzer.datalog.datalog_ui import N6705CDatalogUI

    monkeypatch.setattr(
        N6705CDatalogUI, "_auto_connect_enabled_cards", lambda self: None
    )
    app = QApplication.instance() or QApplication([])
    top = N6705CTop()
    top.connect_a("MOCK::IT2705", MockIT2705("MOCK::IT2705"))
    window = N6705CSuiteWindow(n6705c_top=top)

    analyser = window.analyser_page
    assert "IT2705" in analyser.conn_widgets["A"]["status"].text()
    assert analyser._channels_for_device("A") == tuple(range(1, 9))
    assert len(analyser.channel_tab_buttons) == 8
    assert len(analyser.batch_voltage_inputs["A"]) == 8
    assert len(analyser.batch_current_inputs["A"]) == 8
    assert len(analyser.ct_channel_cards) == 8

    datalog = window.datalog_page
    assert datalog.slot_frames["A"].property("assigned_model") == "IT2705"
    assert len(datalog.ch_current_cbs_a) == 8
    assert len(datalog.ch_voltage_cbs_a) == 8
    assert len(datalog.ch_power_cbs_a) == 8

    window.close()
    window.deleteLater()
    app.processEvents()


def main():
    app = QApplication(sys.argv)

    from core.instruments import InstrumentManager
    manager = InstrumentManager()
    top = N6705CTop()
    top.set_instrument_manager(manager)

    w = N6705CSuiteWindow(n6705c_top=top, instrument_manager=manager)
    w.setWindowTitle("Power Control")
    w.resize(1440, 900)
    w.show()

    assert w.current_page_key() == "analyser", w.current_page_key()

    def _check():
        w.switch_page("datalog")
        assert w.current_page_key() == "datalog"
        w.switch_page("analyser")
        assert w.current_page_key() == "analyser"
        print("SMOKE_OK")

    QTimer.singleShot(1500, _check)
    QTimer.singleShot(3000, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
